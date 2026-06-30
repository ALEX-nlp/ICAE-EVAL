#!/usr/bin/env python3
"""ICAE-Bench objective analyzer.

Owns `analysis/<model>/<lang>/<repo>/objective.json`. Per repo it:

  1. Resolves the in-scope original source paths under <orig-root>
     (override / cache / extract-from-docker fallback chain).
  2. Resolves the in-scope generated paths under
     generate_code_all/<model>/<repo>/.
  3. Walks files via a language-specific regex extractor producing
     (classes, modules/objects/interfaces, namespaces,
      class_methods, instance_methods, file_count, line_count).
  4. Computes class/method/namespace match rates vs. the original.
  5. Reads test pass counts from either an explicit `--*-counts` flag
     or a per-repo `rcb_tests/.results.txt` summary.
  6. Writes the canonical objective JSON; seeds a sibling
     `subjective.json` placeholder iff none exists.

Objective field reference (single source of truth)
==================================================

scale
-----
  generated_src_files / generated_src_loc / orig_src_files /
  orig_src_loc / loc_coverage_ratio (= gen_loc / orig_loc).

objective.class_match_rate
  matched_classes / total_orig_classes. Class-like includes
  class | interface | object | module | struct | enum (matched on
  simple name, namespace stripped). Vacuously 1.0 if the original
  has zero classes in scope.

objective.method_match_rate
  matched_methods / total_orig_methods. Each method is recorded as
  "Owner.name" (static / class-level) or "Owner#name" (instance).
  companion-object / module_function / class << self / `static`
  modifier all promote to the static bucket. Vacuously 1.0 if the
  original has zero methods.

objective.namespace_match_rate
  matched_namespace_paths / total_orig_namespace_paths. Exact
  string match on the namespace path. Vacuously 1.0 if the original
  has zero namespaces.

objective.public_visible_pass / hidden_test_pass / enhanced_test_pass
  Each is a {passed, total, rate} triple. Source dirs:
    public_visible_pass    rcb_tests/public_test_cases/  (visible to agent)
    hidden_test_pass       rcb_tests/test_cases/         (hidden 1:1 set)
    enhanced_test_pass     rcb_tests/enhanced_test_cases/(hidden boundary)
  rate = passed/total rounded to 4 decimals; null if total is 0
  or counts were not supplied.

objective.drop_in_replaceable (deterministic, lives in objective)
  TRUE iff
    class_match_rate >= 0.9 AND
    method_match_rate >= 0.9 AND
    namespace_match_rate >= 0.9 AND
    hidden_test_pass.rate >= 0.9 AND
    enhanced_test_pass.rate >= 0.9
  Otherwise FALSE. public_visible is NOT included by design — that
  rate is only a lower-bound (the agent saw the cases).

Original sources resolution
---------------------------
By default we look for the original tree at one of:

  $RCB_ORIG_ROOT/<username>__<repo>/                  (per-repo subdir)
  agent_env/repos/<username>__<repo>/orig_cache/       (cache from prior run)
  ~/.cache/rcb-orig/<username>__<repo>/               (default cache root)

If none exist, pass --extract-from-docker to pull the in-scope subset
out of the tarball into a fresh cache dir.

Pass-rate sources
-----------------
Highest priority: `--public-pass-counts P/T --full-pass-counts P/T
--public-visible-counts P/T` flags. Otherwise the script reads
`rcb_tests/<suite>/.results.txt` produced by test.sh. Otherwise the
triple is written as {passed: null, total: null, rate: null}.

Read-modify-write
-----------------
By default analyze.py reads the existing objective.json (if present)
and merges new fields in, preserving any keys it does not touch.
Pass --no-merge to overwrite cleanly. The sibling subjective.json is
ONLY seeded if missing — never modified afterwards by analyze.py.

Subjective fields (NOT computed here; lives in subjective.json)
---------------------------------------------------------------
  scope_language / original_language / scope_rationale /
  api_similarity / api_similarity_rationale /
  implementation_quality_notes
See `prompt_template/task_5.md` for the review prompt that generates
those fields.

Usage
-----
  python3 analyze.py --model Opus-4.7 --repo dotnet/maui
  python3 analyze.py --model Sonnet-4.6 --repo dotnet/maui \
      --public-pass-counts 10/10 --public-pass-counts 72/72 \
      --full-pass-counts 45/45
  python3 analyze.py --model Opus-4.7 --all
  python3 analyze.py --all --extract-from-docker  # populate orig_cache
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


# ============================================================
# Per-language source extractors
# ============================================================

@dataclass
class Extracted:
    files: int = 0
    loc: int = 0
    classes: set = field(default_factory=set)        # class_name only (no namespace)
    modules: set = field(default_factory=set)        # interface/object/module/struct/enum
    class_methods: set = field(default_factory=set)  # "Owner.name" or "<top>.name"
    instance_methods: set = field(default_factory=set)  # "Owner#name"
    namespaces: set = field(default_factory=set)


def extract_ruby(files: list[Path]) -> Extracted:
    """
    Ruby extractor — handles `module M`, `class C`, `def x`, `def self.x`,
    `module_function` (which promotes subsequent `def x` to class-level),
    and `class << self` (same effect, scoped to the block).

    Methods are recorded as Owner.name (class-level) or Owner#name
    (instance), where Owner is the dotted ::-joined namespace stack
    excluding any synthetic `class << self` empty-frame.
    """
    out = Extracted()
    for f in files:
        src = f.read_text(encoding="utf-8", errors="replace")
        out.loc += len(src.splitlines())
        out.files += 1
        ns_stack: list[str] = []
        kind_stack: list[str] = []   # 'class' | 'module' | 'sclass' (class << self)
        mfa_stack: list[bool] = []   # module_function active per scope

        for line in src.splitlines():
            m = re.match(r'^\s*module\s+([A-Z][\w:]*)', line)
            if m:
                ns_stack.append(m.group(1))
                kind_stack.append('module')
                mfa_stack.append(False)
                out.modules.add(m.group(1))
                out.namespaces.add('::'.join(ns_stack))
                continue
            m = re.match(r'^\s*class\s+([A-Z][\w:]*)\s*(<<\s*self)?', line)
            if m:
                if m.group(2):
                    # class << self — synthetic frame, methods become class-level
                    ns_stack.append('')
                    kind_stack.append('sclass')
                    mfa_stack.append(mfa_stack[-1] if mfa_stack else False)
                else:
                    ns_stack.append(m.group(1))
                    kind_stack.append('class')
                    mfa_stack.append(False)
                    out.classes.add(m.group(1))
                    out.namespaces.add('::'.join(ns_stack))
                continue
            if re.match(r'^\s*module_function\s*$', line):
                if mfa_stack:
                    mfa_stack[-1] = True
                continue
            if re.match(r'^\s*end\b', line):
                if ns_stack: ns_stack.pop()
                if kind_stack: kind_stack.pop()
                if mfa_stack: mfa_stack.pop()
                continue
            m = re.match(r'^\s*def\s+self\.([\w!?=<>+\-\*\/\[\]]+)', line)
            if m:
                owner = '::'.join(n for n in ns_stack if n)
                out.class_methods.add(f'{owner}.{m.group(1)}' if owner else f'<top>.{m.group(1)}')
                continue
            m = re.match(r'^\s*def\s+([\w!?=<>+\-\*\/\[\]]+)', line)
            if m:
                owner = '::'.join(n for n in ns_stack if n)
                is_class = (mfa_stack and mfa_stack[-1]) or (kind_stack and kind_stack[-1] == 'sclass')
                if is_class:
                    out.class_methods.add(f'{owner}.{m.group(1)}' if owner else f'<top>.{m.group(1)}')
                else:
                    out.instance_methods.add(f'{owner}#{m.group(1)}' if owner else f'<top>#{m.group(1)}')
    return out


def extract_kotlin(files: list[Path]) -> Extracted:
    """
    Kotlin extractor — recognizes `class`, `interface`, `object`,
    `companion object` (treated as static frame), `package <name>`, and
    `fun <name>(...)` (top-level → class-level; inside companion → class;
    otherwise → instance).
    """
    out = Extracted()
    for f in files:
        src = f.read_text(encoding="utf-8", errors="replace")
        out.loc += len(src.splitlines())
        out.files += 1

        m_pkg = re.search(r'^\s*package\s+([\w.]+)', src, re.M)
        pkg = m_pkg.group(1) if m_pkg else ''
        if pkg: out.namespaces.add(pkg)

        ns_stack: list[str] = []
        is_companion: list[bool] = []  # parallel to ns_stack

        for line in src.splitlines():
            m = re.match(
                r'^\s*(?:public\s+|internal\s+|private\s+|abstract\s+|open\s+|data\s+|sealed\s+|enum\s+|inner\s+)*class\s+(\w+)',
                line)
            if m:
                out.classes.add(m.group(1))
                ns_stack.append(m.group(1))
                is_companion.append(False)
                continue
            m = re.match(r'^\s*(?:public\s+|internal\s+|private\s+|fun\s+)?interface\s+(\w+)', line)
            if m:
                out.modules.add(m.group(1))
                ns_stack.append(m.group(1))
                is_companion.append(False)
                continue
            m = re.match(r'^\s*(?:public\s+|internal\s+|private\s+)?object\s+(\w+)', line)
            if m:
                out.modules.add(m.group(1))
                ns_stack.append(m.group(1))
                is_companion.append(False)
                continue
            if re.match(r'^\s*companion\s+object', line):
                ns_stack.append('Companion')
                is_companion.append(True)
                continue
            # Crude scope-pop on lines that are just `}`
            if line.strip() == '}':
                if ns_stack: ns_stack.pop()
                if is_companion: is_companion.pop()
                continue
            m = re.match(
                r'^\s*(?:public\s+|internal\s+|private\s+|protected\s+|override\s+|operator\s+|inline\s+|infix\s+|tailrec\s+|suspend\s+|abstract\s+|open\s+)*fun\s+(?:<[^>]+>\s+)?(?:\w+\.)?(\w+)\s*\(',
                line)
            if m:
                name = m.group(1)
                owner = '.'.join(n for n in ns_stack if n)
                static = bool(is_companion and is_companion[-1])
                if static or not owner:
                    out.class_methods.add(f'{owner}.{name}' if owner else f'<top>.{name}')
                else:
                    out.instance_methods.add(f'{owner}#{name}')
    return out


def extract_csharp(files: list[Path]) -> Extracted:
    """
    C# extractor — recognizes `class`, `struct`, `interface`, `enum`,
    `namespace` (block-style and file-scoped), and method declarations.
    Constructors (where the method name equals the enclosing type) are
    skipped. Static methods are detected by a leading
    `<visibility> static` modifier.
    """
    out = Extracted()
    for f in files:
        src = f.read_text(encoding="utf-8", errors="replace")
        out.loc += len(src.splitlines())
        out.files += 1

        for m in re.finditer(r'^\s*namespace\s+([\w\.]+)', src, re.M):
            out.namespaces.add(m.group(1))

        scope: list[str] = []
        for line in src.splitlines():
            m = re.match(
                r'^\s*(?:public|private|internal|protected|static|abstract|sealed|partial|\s)+class\s+(\w+)',
                line)
            if m:
                out.classes.add(m.group(1)); scope.append(m.group(1)); continue
            m = re.match(
                r'^\s*(?:public|private|internal|protected|static|abstract|partial|readonly|\s)+struct\s+(\w+)',
                line)
            if m:
                out.modules.add(m.group(1)); scope.append(m.group(1)); continue
            m = re.match(
                r'^\s*(?:public|private|internal|protected|\s)+interface\s+(\w+)', line)
            if m:
                out.modules.add(m.group(1)); scope.append(m.group(1)); continue
            m = re.match(r'^\s*(?:public|private|internal|protected|\s)+enum\s+(\w+)', line)
            if m:
                out.modules.add(m.group(1)); continue  # don't push — enums don't nest
            m = re.match(
                r'^\s*(public|private|internal|protected)\s+'
                r'(?:static\s+|virtual\s+|override\s+|abstract\s+|sealed\s+|async\s+|partial\s+|new\s+)*'
                r'(?:[\w<>\?,\.\[\]\s]+?)\s+(\w+)\s*\(', line)
            if m:
                name = m.group(2)
                owner = '.'.join(scope)
                if scope and name == scope[-1]:
                    continue  # constructor
                is_static = bool(re.match(
                    r'^\s*(public|private|internal|protected)\s+static', line))
                if is_static:
                    out.class_methods.add(f'{owner}.{name}' if owner else f'<top>.{name}')
                else:
                    out.instance_methods.add(f'{owner}#{name}' if owner else f'<top>#{name}')
    return out


def extract_python(files: list[Path]) -> Extracted:
    """Python: `class C:` and `def f` / `async def f` (`def self.x` is impossible
    in Python; class methods detected by being inside a class block — tracked
    by indentation depth and `def` indent vs class indent)."""
    out = Extracted()
    for f in files:
        src = f.read_text(encoding="utf-8", errors="replace")
        out.loc += len(src.splitlines())
        out.files += 1
        # Module name = relative path with dots (best-effort namespace)
        out.namespaces.add(str(f.parent).replace('/', '.').strip('.') or '<root>')
        # Track class scope by indentation
        scope: list[tuple[int, str]] = []  # (indent, name)
        for line in src.splitlines():
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            # Pop scopes deeper than current indent
            while scope and scope[-1][0] >= indent:
                scope.pop()
            m = re.match(r'class\s+(\w+)', stripped)
            if m:
                out.classes.add(m.group(1))
                scope.append((indent, m.group(1)))
                continue
            m = re.match(r'(?:async\s+)?def\s+(\w+)\s*\(', stripped)
            if m:
                name = m.group(1)
                if scope:
                    owner = '.'.join(s[1] for s in scope)
                    # __init__ is constructor -> skip
                    if name == '__init__': continue
                    # Convention: starts with @classmethod/@staticmethod handled below
                    out.instance_methods.add(f'{owner}#{name}')
                else:
                    out.class_methods.add(f'<top>.{name}')
    return out


def extract_javascript(files: list[Path]) -> Extracted:
    """JavaScript / TypeScript: `class C`, `interface I`, `function f`,
    `const f = () =>`, methods inside class. namespace: file path."""
    out = Extracted()
    for f in files:
        src = f.read_text(encoding="utf-8", errors="replace")
        out.loc += len(src.splitlines())
        out.files += 1
        out.namespaces.add(str(f.parent).replace('/', '.').strip('.') or '<root>')
        # Top-level functions and classes
        for m in re.finditer(r'^\s*(?:export\s+)?(?:default\s+)?class\s+(\w+)', src, re.M):
            out.classes.add(m.group(1))
        for m in re.finditer(r'^\s*(?:export\s+)?(?:default\s+)?interface\s+(\w+)', src, re.M):
            out.modules.add(m.group(1))
        for m in re.finditer(r'^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)\s*[<(]', src, re.M):
            out.class_methods.add(f'<top>.{m.group(1)}')
        for m in re.finditer(r'^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*[:=].*?(?:\([^)]*\)|=>)', src, re.M):
            out.class_methods.add(f'<top>.{m.group(1)}')
        # Methods inside classes — detect by being on a line that looks like
        # `<name>(...) {` or `<name>(...): <type> {` not preceded by function/const
        for m in re.finditer(
            r'^\s+(?:public|private|protected|static|async|readonly|\s)*\s*(\w+)\s*[<(]',
            src, re.M):
            name = m.group(1)
            if name in ('if', 'for', 'while', 'switch', 'return', 'function', 'const', 'let', 'var', 'class', 'new'):
                continue
            out.instance_methods.add(f'<class>#{name}')
    return out


extract_typescript = extract_javascript


def extract_go(files: list[Path]) -> Extracted:
    """Go: `package P`, `type N struct/interface`, `func (recv) Name(...)`."""
    out = Extracted()
    for f in files:
        src = f.read_text(encoding="utf-8", errors="replace")
        out.loc += len(src.splitlines())
        out.files += 1
        for m in re.finditer(r'^package\s+(\w+)', src, re.M):
            out.namespaces.add(m.group(1))
        for m in re.finditer(r'^type\s+(\w+)\s+struct\b', src, re.M):
            out.classes.add(m.group(1))
        for m in re.finditer(r'^type\s+(\w+)\s+interface\b', src, re.M):
            out.modules.add(m.group(1))
        # Methods with receiver: func (r *Recv) Name(...)
        for m in re.finditer(r'^func\s+\((\w+\s+)?\*?(\w+)\)\s+(\w+)\s*\(', src, re.M):
            recv, name = m.group(2), m.group(3)
            out.instance_methods.add(f'{recv}#{name}')
        # Top-level functions
        for m in re.finditer(r'^func\s+(\w+)\s*\(', src, re.M):
            out.class_methods.add(f'<top>.{m.group(1)}')
    return out


def extract_java(files: list[Path]) -> Extracted:
    """Java: `package p.q`, `class C`, `interface I`, `enum E`, methods."""
    out = Extracted()
    for f in files:
        src = f.read_text(encoding="utf-8", errors="replace")
        out.loc += len(src.splitlines())
        out.files += 1
        for m in re.finditer(r'^\s*package\s+([\w\.]+)\s*;', src, re.M):
            out.namespaces.add(m.group(1))
        # class / interface / enum / record
        for kw, bucket in [
            ('class', out.classes),
            ('interface', out.modules),
            ('enum', out.modules),
            ('record', out.classes),
        ]:
            for m in re.finditer(
                rf'^\s*(?:public|private|protected|static|abstract|final|sealed|\s)+{kw}\s+(\w+)',
                src, re.M):
                bucket.add(m.group(1))
        # Methods: <vis> [static] [<generics>] <RetType> name(...
        for m in re.finditer(
            r'^\s+(?:public|private|protected)\s+'
            r'(?:static\s+|final\s+|abstract\s+|synchronized\s+|native\s+|<[^>]+>\s+)*'
            r'(?:[\w\<\>\[\],\.\?\s]+?)\s+(\w+)\s*\(',
            src, re.M):
            name = m.group(1)
            is_static = bool(re.match(r'^\s+(?:public|private|protected)\s+(?:final\s+)?static', m.group(0)))
            if is_static:
                out.class_methods.add(f'<class>.{name}')
            else:
                out.instance_methods.add(f'<class>#{name}')
    return out


def extract_cpp(files: list[Path]) -> Extracted:
    """C++: `namespace N`, `class C`, `struct S`, `Type Class::method(...)`."""
    out = Extracted()
    for f in files:
        src = f.read_text(encoding="utf-8", errors="replace")
        out.loc += len(src.splitlines())
        out.files += 1
        for m in re.finditer(r'^namespace\s+(\w+)', src, re.M):
            out.namespaces.add(m.group(1))
        for m in re.finditer(r'^\s*class\s+(\w+)\s*[:{]?', src, re.M):
            out.classes.add(m.group(1))
        for m in re.finditer(r'^\s*struct\s+(\w+)\s*[:{]?', src, re.M):
            out.modules.add(m.group(1))
        # Methods defined out-of-class: Type Class::name(...
        for m in re.finditer(r'(\w+)::(\w+)\s*\(', src):
            cls, name = m.group(1), m.group(2)
            if name in ('if', 'while', 'for', 'switch'): continue
            if name == cls: continue  # ctor
            out.instance_methods.add(f'{cls}#{name}')
        # Inline methods inside class declaration — best-effort
        for m in re.finditer(r'^\s+(?:virtual\s+|static\s+|inline\s+|constexpr\s+|\s)*(?:[\w\<\>\&\*\:,\s]+?)\s+(\w+)\s*\([^)]*\)\s*(?:const\s*)?[{;]', src, re.M):
            name = m.group(1)
            if name in ('if', 'while', 'for', 'return', 'switch', 'sizeof'): continue
            out.instance_methods.add(f'<class>#{name}')
    return out


def extract_rust(files: list[Path]) -> Extracted:
    """Rust: `mod m`, `struct S`, `enum E`, `trait T`, `impl S { fn name() }`."""
    out = Extracted()
    for f in files:
        src = f.read_text(encoding="utf-8", errors="replace")
        out.loc += len(src.splitlines())
        out.files += 1
        for m in re.finditer(r'^\s*(?:pub\s+)?mod\s+(\w+)', src, re.M):
            out.namespaces.add(m.group(1))
        for m in re.finditer(r'^\s*(?:pub(?:\([^)]*\))?\s+)?struct\s+(\w+)', src, re.M):
            out.classes.add(m.group(1))
        for m in re.finditer(r'^\s*(?:pub(?:\([^)]*\))?\s+)?enum\s+(\w+)', src, re.M):
            out.modules.add(m.group(1))
        for m in re.finditer(r'^\s*(?:pub(?:\([^)]*\))?\s+)?trait\s+(\w+)', src, re.M):
            out.modules.add(m.group(1))
        # impl Block: impl <generics>? <Trait> for? <Type> { ... fn name(...) ... }
        for impl_m in re.finditer(
            r'impl(?:<[^>]*>)?\s+(?:(\w+)\s+for\s+)?(\w+)(?:<[^>]*>)?\s*\{',
            src):
            impl_owner = impl_m.group(2)
            impl_start = impl_m.end()
            depth, i = 1, impl_start
            while i < len(src) and depth > 0:
                if src[i] == '{': depth += 1
                elif src[i] == '}': depth -= 1
                i += 1
            block = src[impl_start:i-1]
            for fn_m in re.finditer(r'\bfn\s+(\w+)\s*[<(]', block):
                name = fn_m.group(1)
                # Detect &self / &mut self / self -> instance, else static
                # Look at the (...) part following
                tail = block[fn_m.end():]
                paren_close = tail.find(')')
                args = tail[:paren_close] if paren_close >= 0 else ''
                if re.match(r'\s*&?\s*(?:mut\s+)?self\b', args):
                    out.instance_methods.add(f'{impl_owner}#{name}')
                else:
                    out.class_methods.add(f'{impl_owner}.{name}')
        # Free functions
        for m in re.finditer(r'^\s*(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?fn\s+(\w+)\s*[<(]', src, re.M):
            out.class_methods.add(f'<top>.{m.group(1)}')
    return out


def extract_dart(files: list[Path]) -> Extracted:
    """Dart: `library l`, `class C`, `mixin M`, methods."""
    out = Extracted()
    for f in files:
        src = f.read_text(encoding="utf-8", errors="replace")
        out.loc += len(src.splitlines())
        out.files += 1
        # library directive (rare) or use file path
        added = False
        for m in re.finditer(r'^library\s+([\w\.]+)\s*;', src, re.M):
            out.namespaces.add(m.group(1)); added = True
        if not added:
            out.namespaces.add(str(f.parent).replace('/', '.').strip('.') or '<root>')
        for m in re.finditer(r'^\s*(?:abstract\s+)?(?:base\s+)?(?:final\s+)?(?:sealed\s+)?(?:interface\s+)?class\s+(\w+)', src, re.M):
            out.classes.add(m.group(1))
        for m in re.finditer(r'^\s*mixin\s+(\w+)', src, re.M):
            out.modules.add(m.group(1))
        for m in re.finditer(r'^\s*enum\s+(\w+)', src, re.M):
            out.modules.add(m.group(1))
        # Top-level functions: <Type>? <name>(...) { or =>
        for m in re.finditer(r'^([\w<>\?,\s]+?)\s+(\w+)\s*\([^)]*\)\s*[{=]', src, re.M):
            ret, name = m.group(1).strip(), m.group(2)
            if name in ('if', 'while', 'for', 'switch'): continue
            if ret in ('class', 'mixin', 'enum'): continue
            out.class_methods.add(f'<top>.{name}')
    return out


def extract_php(files: list[Path]) -> Extracted:
    """PHP: `namespace N;`, `class C`, `interface I`, `trait T`, `function f`."""
    out = Extracted()
    for f in files:
        src = f.read_text(encoding="utf-8", errors="replace")
        out.loc += len(src.splitlines())
        out.files += 1
        for m in re.finditer(r'^namespace\s+([\w\\]+)\s*;', src, re.M):
            out.namespaces.add(m.group(1).replace('\\', '.'))
        for m in re.finditer(r'^\s*(?:abstract\s+|final\s+)*class\s+(\w+)', src, re.M):
            out.classes.add(m.group(1))
        for m in re.finditer(r'^\s*interface\s+(\w+)', src, re.M):
            out.modules.add(m.group(1))
        for m in re.finditer(r'^\s*trait\s+(\w+)', src, re.M):
            out.modules.add(m.group(1))
        # Methods: public/private/protected [static] function name(...)
        for m in re.finditer(
            r'^\s*(public|private|protected)\s+(?:static\s+)?function\s+(\w+)\s*\(',
            src, re.M):
            name = m.group(2)
            is_static = bool(re.match(r'^\s*(?:public|private|protected)\s+static', m.group(0)))
            if is_static:
                out.class_methods.add(f'<class>.{name}')
            else:
                out.instance_methods.add(f'<class>#{name}')
        # Top-level functions
        for m in re.finditer(r'^\s*function\s+(\w+)\s*\(', src, re.M):
            out.class_methods.add(f'<top>.{m.group(1)}')
    return out


# Directories that never hold in-scope source. Used to prune both the
# original whole-tree scan and the generated whole-tree fallback so vendored
# deps / build artifacts / test harnesses don't pollute similarity (and so a
# dependency dir whose name happens to match *.<ext>, e.g. node_modules/decimal.js,
# is never fed to read_text()).
NON_SOURCE_DIRS = {
    'bin', 'obj', 'target', 'vendor', '.gradle', '.build', 'build', 'dist',
    'rcb_tests', 'RcbDispatcher', 'rcb_runner', 'test', 'tests',
    'spec', 'specs', '__pycache__', '.git', 'node_modules',
    'jvmTest', 'commonTest', '.idea', '.dart_tool', 'Pods', '.next',
}


EXTRACTORS = {
    'Ruby':       ('rb', extract_ruby),
    'Kotlin':     ('kt', extract_kotlin),
    'CSharp':     ('cs', extract_csharp),
    'Python':     ('py', extract_python),
    'JavaScript': ('js', extract_javascript),
    'TypeScript': ('ts', extract_typescript),
    'Go':         ('go', extract_go),
    'Java':       ('java', extract_java),
    'Cpp':        ('cpp', extract_cpp),  # also need .cc/.cxx/.h handling — see collect_files
    'Rust':       ('rs', extract_rust),
    'Dart':       ('dart', extract_dart),
    'PHP':        ('php', extract_php),
}


def collect_files(root: Path, in_scope: dict, ext: str, key_prefix: str) -> list[Path]:
    """
    Resolve in_scope spec to a concrete list of files under `root`.

    Recognized keys (with `key_prefix` ∈ {'original', 'generated'}):
      <prefix>_files: list of explicit file paths (relative to root)
      <prefix>:       list of directories to recursively glob for *.<ext>
    """
    files: list[Path] = []
    if f"{key_prefix}_files" in in_scope:
        for rel in in_scope[f"{key_prefix}_files"]:
            p = root / rel
            if p.is_file():
                files.append(p)
            else:
                print(f"  [warn] {key_prefix} file missing: {p}", file=sys.stderr)
    if key_prefix in in_scope:
        for rel in in_scope[key_prefix]:
            d = root / rel
            if d.is_dir():
                for p in sorted(d.rglob(f"*.{ext}")):
                    # rglob matches directories named *.<ext> too (e.g.
                    # node_modules/decimal.js); read_text() on those raises
                    # IsADirectoryError and aborts the whole repo's analysis.
                    if not p.is_file():
                        continue
                    if any(part in NON_SOURCE_DIRS for part in p.relative_to(d).parts):
                        continue
                    files.append(p)
            else:
                print(f"  [warn] {key_prefix} dir missing: {d}", file=sys.stderr)
    return files


# ============================================================
# Original-source resolution
# ============================================================

def resolve_orig_root(entry: dict, override: Path | None) -> Path:
    """Resolve where the original tree lives.

    Search order:
      1. --orig-root override (if given)
      2. $RCB_ORIG_ROOT/<username>__<repo>/
      3. agent_env/repos/<username>__<repo>/orig_cache/
      4. ~/.cache/rcb-orig/<username>__<repo>/

    Raises FileNotFoundError if none exist.
    """
    name = f"{entry['username']}__{entry['repo']}"
    candidates: list[Path] = []
    if override:
        candidates.append(override / name)
    if (env := os.environ.get('RCB_ORIG_ROOT')):
        candidates.append(Path(env) / name)
    candidates.append(
        Path(f'agent_env/repos/{name}/orig_cache')
    )
    candidates.append(Path.home() / '.cache' / 'rcb-orig' / name)

    for c in candidates:
        if c.is_dir():
            return c
    raise FileNotFoundError(
        f"No original-source cache for {name} found. Tried:\n"
        + '\n'.join(f"  {c}" for c in candidates)
        + "\nRe-run with --extract-from-docker to populate one of these."
    )


def extract_from_docker(entry: dict, dest_root: Path) -> Path:
    """
    Pull the in-scope original source out of the docker tar into
    <dest_root>/<username>__<repo>/. Idempotent: skips if already populated.

    Uses `docker load` + `docker create` + `docker cp` per file/dir in
    the in-scope spec. Cleans up the temp container at the end.
    """
    name = f"{entry['username']}__{entry['repo']}"
    dest = dest_root / name
    if dest.exists() and any(dest.rglob('*')):
        print(f"  [cache] {dest} already populated", file=sys.stderr)
        return dest

    tar = Path(f'docker_imgs/{name}.tar')
    if not tar.exists():
        raise FileNotFoundError(f"docker tar missing: {tar}")

    image = f'local/{name.lower()}:patched'
    print(f"  [docker] loading {tar} → {image}", file=sys.stderr)
    subprocess.run(['docker', 'load', '-i', str(tar)],
                   check=True, capture_output=True)

    container = f'rcb-extract-{name}'
    subprocess.run(['docker', 'rm', '-f', container],
                   check=False, capture_output=True)
    cid = subprocess.check_output(
        ['docker', 'create', '--name', container, image, 'sleep', '60']).decode().strip()
    print(f"  [docker] created {cid[:12]}", file=sys.stderr)
    try:
        dest.mkdir(parents=True, exist_ok=True)
        in_scope = entry['in_scope']
        for rel in in_scope.get('original_files', []) + in_scope.get('original', []):
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            src_in_container = f'{container}:/testbed/{rel}'
            try:
                subprocess.run(['docker', 'cp', src_in_container, str(target)],
                               check=True, capture_output=True)
                print(f"  [docker cp] {rel}", file=sys.stderr)
            except subprocess.CalledProcessError as e:
                print(f"  [docker cp] FAILED {rel}: {e.stderr.decode()[:200]}",
                      file=sys.stderr)
    finally:
        subprocess.run(['docker', 'rm', '-f', container],
                       check=False, capture_output=True)
    return dest


# ============================================================
# Pass-rate inference
# ============================================================

def count_cases(json_dir: Path) -> int:
    n = 0
    for p in json_dir.glob('*.json'):
        n += len(json.loads(p.read_text())['cases'])
    return n


def infer_pass_counts(test_cases_dir: Path | None) -> tuple[int, int] | None:
    """
    Read the per-case results from <repo>/rcb_tests/.results.txt produced
    by test.sh — every line starts with PASS or FAIL. Return (passed, total)
    or None if the file does not exist.
    """
    if test_cases_dir is None: return None
    results = test_cases_dir.parent / '.results.txt'
    if not results.is_file(): return None
    text = results.read_text()
    pas = text.count('\nPASS ') + (1 if text.startswith('PASS ') else 0)
    fai = text.count('\nFAIL ') + (1 if text.startswith('FAIL ') else 0)
    total = pas + fai
    return (pas, total) if total > 0 else None


def make_rate_block(passed: int | None, total: int | None) -> dict:
    """
    Standard pass-rate triple: {passed, total, rate}.
    Rate is null if total is 0 or undefined.
    """
    if passed is None or total is None or total == 0:
        return {'passed': passed, 'total': total, 'rate': None}
    return {'passed': passed, 'total': total, 'rate': round(passed / total, 4)}


# ============================================================
# Per-repo pipeline
# ============================================================

def merge_into_existing(existing: dict, new_payload: dict) -> dict:
    """
    Read-modify-write semantics: preserve any keys/sub-keys in `existing`
    that the new payload does not touch (e.g. agent-supplied subjective
    notes, manual scope_rationale, custom annotations).

    Strategy: deep-merge dicts, but for primitive values the new payload
    wins iff its value is not None. This means a re-run that only computes
    structural rates won't clobber pass-rates from a previous run.
    """
    if not isinstance(existing, dict) or not isinstance(new_payload, dict):
        return new_payload if new_payload is not None else existing

    out = dict(existing)  # start from existing
    for k, v in new_payload.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge_into_existing(out[k], v)
        elif v is None and k in out:
            # don't clobber existing non-null with explicit null
            continue
        else:
            out[k] = v
    return out


def analyze_repo(entry: dict, args, repos_root: Path, gen_root_base: Path,
                 model: str) -> dict:
    """
    Compute the OBJECTIVE half of the analysis JSON for one repo.
    Subjective fields (scope_language, api_similarity narrative, etc.)
    live in a sibling subjective.json owned by a different agent/process.

    Returns the dict that will be written to
    analysis/<model>/<lang>/<repo>/objective.json.
    """
    name = f"{entry['username']}__{entry['repo']}"
    language = entry['language']  # scope_language (decides extractor)
    if language not in EXTRACTORS:
        # repos.yaml may carry a lowercase label (auto-appended entries); map it
        # to the canonical EXTRACTORS key before giving up.
        _canon = {k.lower(): k for k in EXTRACTORS}
        language = _canon.get(language.strip().lower(), language)
    if language not in EXTRACTORS:
        raise ValueError(f"unknown language {language!r} for {name}")
    ext, extractor = EXTRACTORS[language]

    print(f"=== {entry['repo_id']} ({language} | model={model}) ===",
          file=sys.stderr)

    # 1. Resolve and extract orig
    if args.extract_from_docker:
        cache_root = Path(args.cache_root or Path.home() / '.cache' / 'rcb-orig')
        orig_root = extract_from_docker(entry, cache_root)
    else:
        orig_root = resolve_orig_root(entry, args.orig_root)
    print(f"  orig_root = {orig_root}", file=sys.stderr)

    gen_root = gen_root_base / name
    gen_present = gen_root.is_dir() and any(gen_root.iterdir())
    if not gen_present:
        print(f"  [warn] generated tree missing or empty: {gen_root}", file=sys.stderr)

    # 2. Walk
    orig_files = collect_files(orig_root, entry['in_scope'], ext, 'original')
    if not orig_files:
        raise RuntimeError(f"no in-scope original files found under {orig_root}")

    if gen_present:
        gen_files = collect_files(gen_root, entry['in_scope'], ext, 'generated')
        # Fallback: agent may organize files differently from the original
        # (e.g. flat layout vs original's nested dirs). If the configured
        # generated paths yielded zero files, scan the whole gen_root for
        # *.{ext} files, excluding obvious non-source dirs (tests, build
        # artifacts, dispatcher, the agent's own rcb_tests harness).
        if not gen_files:
            print(f"  [warn] in_scope.generated paths matched 0 files under {gen_root};"
                  f" falling back to whole-tree scan", file=sys.stderr)
            EXCLUDE_DIRS = NON_SOURCE_DIRS
            for p in gen_root.rglob(f'*.{ext}'):
                if not p.is_file():
                    continue
                # Skip obvious non-source dirs at any depth
                if any(part in EXCLUDE_DIRS for part in p.relative_to(gen_root).parts):
                    continue
                # Skip obvious test files
                name = p.name.lower()
                if name.endswith(f'test.{ext}') or name.endswith(f'tests.{ext}') \
                        or name.endswith(f'_test.{ext}') or name.endswith(f'_spec.{ext}') \
                        or name.endswith(f'spec.{ext}'):
                    continue
                gen_files.append(p)
            print(f"  [warn] fallback found {len(gen_files)} files", file=sys.stderr)
    else:
        gen_files = []

    orig = extractor(orig_files)
    gen  = extractor(gen_files) if gen_files else Extracted()

    # 3. Match rates (class-like AND module-like collapsed into one bucket).
    orig_class_like = orig.classes | orig.modules
    gen_class_like  = gen.classes  | gen.modules
    orig_methods = orig.class_methods | orig.instance_methods
    gen_methods  = gen.class_methods  | gen.instance_methods

    def rate(matched: int, total: int) -> float:
        # When the original has no items in this category, rate is
        # vacuously 1.0 (nothing to fail to match).
        return round(matched / total, 4) if total else 1.0

    cmr = rate(len(orig_class_like & gen_class_like), len(orig_class_like))
    mmr = rate(len(orig_methods & gen_methods), len(orig_methods))
    nmr = rate(len(orig.namespaces & gen.namespaces), len(orig.namespaces))

    # 4. Pass rates — store as {passed, total, rate} triples.
    repo_dir = repos_root / name
    # Visible / hidden / enhanced
    visible_block = make_rate_block(
        *(args.public_visible_counts or
          infer_pass_counts(repo_dir / 'rcb_tests' / 'public_test_cases') or
          (None, None))
    )
    hidden_block = make_rate_block(
        *(args.public_pass_counts or
          infer_pass_counts(repo_dir / 'rcb_tests' / 'test_cases') or
          (None, None))
    )
    enhanced_block = make_rate_block(
        *(args.full_pass_counts or
          infer_pass_counts(repo_dir / 'rcb_tests' / 'enhanced_test_cases') or
          (None, None))
    )

    # If override flags only gave a rate (legacy --public-pass-rate), use that.
    if args.public_pass_rate is not None and hidden_block['rate'] is None:
        hidden_block = {'passed': None, 'total': None, 'rate': args.public_pass_rate}
    if args.full_pass_rate is not None and enhanced_block['rate'] is None:
        enhanced_block = {'passed': None, 'total': None, 'rate': args.full_pass_rate}
    if args.public_visible_rate is not None and visible_block['rate'] is None:
        visible_block = {'passed': None, 'total': None, 'rate': args.public_visible_rate}

    ptr = hidden_block['rate']
    ftr = enhanced_block['rate']

    # 5. drop_in_replaceable is deterministic — lives under objective.
    drop_in = (
        cmr >= 0.9 and mmr >= 0.9 and nmr >= 0.9
        and ptr is not None and ftr is not None
        and ptr >= 0.9 and ftr >= 0.9
    )

    return {
        'repo_id': entry['repo_id'],
        'model': model,
        'language': language,
        'scale': {
            'generated_src_files': gen.files if gen_present else None,
            'generated_src_loc':   gen.loc   if gen_present else None,
            'orig_src_files':      orig.files,
            'orig_src_loc':        orig.loc,
            'loc_coverage_ratio':  round(gen.loc / orig.loc, 4) if (gen_present and orig.loc) else None,
        },
        'objective': {
            'class_match_rate':       cmr,
            'method_match_rate':      mmr,
            'namespace_match_rate':   nmr,
            'public_visible_pass':    visible_block,
            'hidden_test_pass':       hidden_block,
            'enhanced_test_pass':     enhanced_block,
            'drop_in_replaceable':    drop_in,
        },
        'notes': {
            'matched_class_like':      len(orig_class_like & gen_class_like),
            'orig_class_like':         len(orig_class_like),
            'matched_methods':         len(orig_methods & gen_methods),
            'orig_methods':            len(orig_methods),
            'matched_namespaces':      len(orig.namespaces & gen.namespaces),
            'orig_namespaces':         len(orig.namespaces),
            'missing_class_like':      sorted(orig_class_like - gen_class_like),
            'missing_methods':         sorted(orig_methods - gen_methods),
            'methodology':             (
                f"Per-language regex extractor in analyze.py "
                f"(Ruby/Kotlin/CSharp). Class-like (class|interface|"
                f"object|module|struct|enum) is matched on simple name. "
                f"Methods are recorded as Owner.name (static) or Owner#name "
                f"(instance), with companion-object / module_function / "
                f"class << self / `static` modifier promoted to static. "
                f"Subjective fields (scope_language, original_language, "
                f"scope rationale, api_similarity narrative) live in the "
                f"sibling subjective.json."
            ),
            'scoring': [
                'drop_in_replaceable requires class/method/namespace match >= 0.9 AND hidden+enhanced pass rates >= 0.9.',
                'public_visible_pass is over rcb_tests/public_test_cases (lower-bound signal: agent saw these in start.md).',
                'hidden_test_pass is over rcb_tests/test_cases (1:1 reconstruction of original tests; agent did NOT see these).',
                'enhanced_test_pass is over rcb_tests/enhanced_test_cases (evaluator-only boundary cases).',
                'A pass-rate `rate: null` means analyze.py could not infer it and no override was supplied.',
            ],
        },
    }


def build_subjective_template(entry: dict, model: str) -> dict:
    """
    Initial subjective.json content. analyze.py only writes this if
    no subjective.json exists yet — never overwrites a real one.
    """
    return {
        'repo_id': entry['repo_id'],
        'model': model,
        'subjective': {
            'scope_language':           entry['language'],
            'original_language':        entry.get('original_language', entry['language']),
            'scope_rationale':          entry['scope'].strip(),
            'api_similarity':           None,
            'api_similarity_rationale': None,
            'design_principles_score':     None,
            'design_principles_rationale': None,
            'implementation_quality_notes': None,
        },
        'notes': {
            'authority': (
                "Subjective fields are intended for human or LLM-judge review. "
                "scope_language is the language of the in-scope subset, which "
                "may differ from original_language (e.g. anypackage is a "
                "PowerShell module on GitHub but the in-scope subset is C#). "
                "api_similarity is a 0..1 score reflecting the gap between "
                "structural similarity and behavioral correctness; suggested "
                "weighting: half from public+hidden+enhanced pass agreement, "
                "half from API surface coverage. analyze.py never overwrites "
                "this file — it only seeds it if missing."
            ),
        },
    }


# ============================================================
# CLI
# ============================================================

def main(argv: list[str]) -> int:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--config', default=str(here / 'repos.yaml'),
                        help='Path to repos.yaml (default: alongside script)')
    parser.add_argument('--repo',
                        help='Run only this repo_id (e.g. dotnet/maui)')
    parser.add_argument('--all', action='store_true',
                        help='Run every repo in the config')
    parser.add_argument('--orig-root',
                        help='Override the per-repo original-source root')
    parser.add_argument('--cache-root',
                        help='Override the docker-extraction cache root '
                             '(default: ~/.cache/rcb-orig)')
    parser.add_argument('--extract-from-docker', action='store_true',
                        help='Extract in-scope original source from the '
                             'docker tar into the cache root before analysis')
    parser.add_argument('--model', default='Opus-4.7',
                        help='Sub-folder name for the agent under evaluation '
                             '(default: Opus-4.7). Drives both --gen-root '
                             '(generate_code_all/<model>/) and the output path '
                             '(analysis/<model>/<lang>/<repo>.json).')
    parser.add_argument('--gen-root',
                        help='Override generate_code root '
                             '(default: generate_code_all/<model>/)')
    parser.add_argument('--public-pass-rate', type=float,
                        help='Override the hidden test_cases pass rate (0..1, legacy)')
    parser.add_argument('--full-pass-rate', type=float,
                        help='Override the enhanced_test_cases pass rate (0..1, legacy)')
    parser.add_argument('--public-visible-rate', type=float,
                        help='Override the public_test_cases pass rate (0..1)')
    parser.add_argument('--public-pass-counts', type=str,
                        help='Override hidden test_cases counts as "P/T" (e.g. "17/24")')
    parser.add_argument('--full-pass-counts', type=str,
                        help='Override enhanced_test_cases counts as "P/T"')
    parser.add_argument('--public-visible-counts', type=str,
                        help='Override public_test_cases counts as "P/T"')
    parser.add_argument('--out-root', default=str(here),
                        help='Where to write analysis/<model>/<Lang>/<repo>.json '
                             '(default: alongside this script)')
    parser.add_argument('--repos-root',
                        default='agent_env/repos',
                        help='Root of repos/<username>__<repo>/ (for pass-rate inference)')
    parser.add_argument('--no-merge', action='store_true',
                        help='Do not merge with existing JSON; overwrite cleanly')
    args = parser.parse_args(argv[1:])

    if not (args.repo or args.all):
        parser.error('one of --repo or --all required')

    if args.orig_root:
        args.orig_root = Path(args.orig_root).resolve()

    # Parse "P/T" counts strings into tuples
    def parse_counts(s):
        if not s: return None
        try:
            p, t = s.split('/')
            return (int(p), int(t))
        except (ValueError, AttributeError):
            parser.error(f"invalid counts format {s!r}; want 'P/T' like '17/24'")
    args.public_pass_counts    = parse_counts(args.public_pass_counts)
    args.full_pass_counts      = parse_counts(args.full_pass_counts)
    args.public_visible_counts = parse_counts(args.public_visible_counts)

    config = yaml.safe_load(Path(args.config).read_text())
    entries = config['repos']
    if args.repo:
        entries = [e for e in entries if e['repo_id'] == args.repo]
        if not entries:
            print(f"no entry for {args.repo!r} in {args.config}",
                  file=sys.stderr)
            return 1

    out_root = Path(args.out_root)
    repos_root = Path(args.repos_root)
    gen_root_base = Path(args.gen_root) if args.gen_root else Path(
        f'agent_env/generate_code_all/{args.model}'
    )

    failures: list[str] = []
    for entry in entries:
        try:
            result = analyze_repo(entry, args, repos_root, gen_root_base, args.model)
            repo_name = f"{entry['username']}__{entry['repo']}"
            # Use the canonical language recorded by analyze_repo (entry's label
            # may be lowercase) so the dir matches EXTRACTORS / dataset convention.
            out_lang = result.get('language', entry['language'])
            repo_out_dir = (out_root / args.model / out_lang
                            / repo_name)
            repo_out_dir.mkdir(parents=True, exist_ok=True)

            # Write objective.json (read-modify-write)
            obj_path = repo_out_dir / 'objective.json'
            if obj_path.exists() and not args.no_merge:
                try:
                    existing = json.loads(obj_path.read_text())
                    result = merge_into_existing(existing, result)
                except json.JSONDecodeError:
                    print(f"  [warn] existing {obj_path} is not valid JSON; overwriting",
                          file=sys.stderr)
            obj_path.write_text(json.dumps(result, indent=2) + '\n')
            print(f"  wrote {obj_path}", file=sys.stderr)

            # Seed subjective.json if missing — never overwrite
            subj_path = repo_out_dir / 'subjective.json'
            if not subj_path.exists():
                subj = build_subjective_template(entry, args.model)
                subj_path.write_text(json.dumps(subj, indent=2) + '\n')
                print(f"  seeded {subj_path}", file=sys.stderr)
            else:
                print(f"  preserved {subj_path}", file=sys.stderr)

            print(json.dumps({k: v for k, v in result.items()
                              if k not in ('notes',)}, indent=2))
        except Exception as e:
            failures.append(f"{entry['repo_id']}: {e}")
            print(f"  [error] {e}", file=sys.stderr)
            import traceback; traceback.print_exc(file=sys.stderr)

    if failures:
        print(f"\n{len(failures)} failure(s):", file=sys.stderr)
        for f in failures: print(f"  {f}", file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
