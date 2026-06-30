## Product Requirement Document

# Project Scaffold Generator - Template-Based Starter Project Creation

## Project Goal

Build a project scaffold generator that allows developers to create ready-to-edit starter projects from curated templates without hand-copying boilerplate files, metadata, and entrypoints.

---

## Background & Problem

Without this tool, developers are forced to assemble starter project directories manually: choosing a layout, writing manifest metadata, adding ignored-file rules, creating an entrypoint, and remembering follow-up install or run commands. This leads to repetitive setup work, inconsistent generated structures, and easy-to-miss metadata mistakes.

With this tool, a developer or automation client selects a starter template, supplies project context, and receives a deterministic set of generated files plus machine-verifiable output describing what was created.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain. 
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository. 
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: Project Name Normalization

**As a developer**, I want to normalize a directory-style project name into package metadata, so I can create valid generated projects from common folder names.

**Expected Behavior / Usage:**

A project name is derived from a user-provided directory name. Hyphens and spaces are converted to underscores, and a file-style extension is removed at the first period. The adapter input provides a scenario selector and a raw directory name; stdout contains one `name=` line with the normalized result.

**Test Cases:** `rcb[a specific sentinel value — ask the PM for the exact string]tests/public[a specific sentinel value — ask the PM for the exact string]test[a specific sentinel value — ask the PM for the exact string]cases/feature1[a specific sentinel value — ask the PM for the exact string]project[a specific sentinel value — ask the PM for the exact string]name[a specific sentinel value — ask the PM for the exact string]normalization.json`

```json
{
    "description": "Directory names are converted into package-safe project names before being used in generated package metadata.",
    "cases": [
        {
            "input": {
                "scenario": "project[a specific sentinel value — ask the PM for the exact string]name[a specific sentinel value — ask the PM for the exact string]from[a specific sentinel value — ask the PM for the exact string]directory",
                "directory[a specific sentinel value — ask the PM for the exact string]name": "foo.dart"
            },
            "expected[a specific sentinel value — ask the PM for the exact string]output": "name=foo\n"
        },
        {
            "input": {
                "scenario": "project[a specific sentinel value — ask the PM for the exact string]name[a specific sentinel value — ask the PM for the exact string]from[a specific sentinel value — ask the PM for the exact string]directory",
                "directory[a specific sentinel value — ask the PM for the exact string]name": "foo-bar"
            },
            "expected[a specific sentinel value — ask the PM for the exact string]output": "name=foo[a specific sentinel value — ask the PM for the exact string]bar\n"
        }
    ]
}
```

---

### Feature 2: Template Placeholder Rendering

**As a developer**, I want to render text templates with caller-provided values, so I can generate project files without manually editing placeholders.

**Expected Behavior / Usage:**

Text templates may contain placeholders delimited by double underscores around an ASCII-letter key. Keys supplied in the variables object must contain letters only. Matching placeholders are replaced once with their provided value, unknown placeholders remain unchanged, and replacement values are not recursively expanded. If a supplied key contains whitespace, digits, underscores, or symbols, stdout reports `error=invalid[a specific sentinel value — ask the PM for the exact string]placeholder[a specific sentinel value — ask the PM for the exact string]key` and the offending `key=` without exposing host-language exception details.

**Test Cases:** `rcb[a specific sentinel value — ask the PM for the exact string]tests/public[a specific sentinel value — ask the PM for the exact string]test[a specific sentinel value — ask the PM for the exact string]cases/feature2[a specific sentinel value — ask the PM for the exact string]template[a specific sentinel value — ask the PM for the exact string]placeholder[a specific sentinel value — ask the PM for the exact string]rendering.json`

```json
{
    "description": "Text templates replace placeholders whose names are made only of letters, leave unknown placeholders unchanged, do not recursively expand replacement values, and report invalid placeholder keys neutrally.",
    "cases": [
        {
            "input": {
                "scenario": "template[a specific sentinel value — ask the PM for the exact string]placeholder[a specific sentinel value — ask the PM for the exact string]rendering",
                "text": "foo [a specific sentinel value — ask the PM for the exact string][a specific sentinel value — ask the PM for the exact string]bar[a specific sentinel value — ask the PM for the exact string][a specific sentinel value — ask the PM for the exact string] baz",
                "variables": {
                    "bar": "baz"
                }
            },
            "expected[a specific sentinel value — ask the PM for the exact string]output": "text=foo baz baz\n"
        },
        {
            "input": {
                "scenario": "template[a specific sentinel value — ask the PM for the exact string]placeholder[a specific sentinel value — ask the PM for the exact string]rendering",
                "text": "foo [a specific sentinel value — ask the PM for the exact string][a specific sentinel value — ask the PM for the exact string]bar[a specific sentinel value — ask the PM for the exact string][a specific sentinel value — ask the PM for the exact string] baz",
                "variables": {
                    "aaa": "bbb"
                }
            },
            "expected[a specific sentinel value — ask the PM for the exact string]output": "text=foo [a specific sentinel value — ask the PM for the exact string][a specific sentinel value — ask the PM for the exact string]bar[a specific sentinel value — ask the PM for the exact string][a specific sentinel value — ask the PM for the exact string] baz\n"
        },
        {
            "input": {
                "scenario": "template[a specific sentinel value — ask the PM for the exact string]placeholder[a specific sentinel value — ask the PM for the exact string]rendering",
                "text": "foo [a specific sentinel value — ask the PM for the exact string][a specific sentinel value — ask the PM for the exact string]bar[a specific sentinel value — ask the PM for the exact string][a specific sentinel value — ask the PM for the exact string] baz",
                "variables": {
                    "bar": "[a specific sentinel value — ask the PM for the exact string][a specific sentinel value — ask the PM for the exact string]baz[a specific sentinel value — ask the PM for the exact string][a specific sentinel value — ask the PM for the exact string]",
                    "baz": "foo"
                }
            },
            "expected[a specific sentinel value — ask the PM for the exact string]output": "text=foo [a specific sentinel value — ask the PM for the exact string][a specific sentinel value — ask the PM for the exact string]baz[a specific sentinel value — ask the PM for the exact string][a specific sentinel value — ask the PM for the exact string] baz\n"
        },
        {
            "input": {
                "scenario": "template[a specific sentinel value — ask the PM for the exact string]placeholder[a specific sentinel value — ask the PM for the exact string]rendering",
                "text": "str",
                "variables": {
                    "with space": "noop"
                }
            },
            "expected[a specific sentinel value — ask the PM for the exact string]output": "error=invalid[a specific sentinel value — ask the PM for the exact string]placeholder[a specific sentinel value — ask the PM for the exact string]key\nkey=with space\n"
        }
    ]
}
```

---

### Feature 3: Plain Text Wrapping

**As a developer**, I want to wrap long prose at word boundaries, so generated metadata remains readable.

**Expected Behavior / Usage:**

The adapter input provides text and optionally a maximum column width. Text whose length does not exceed the width stays on one line. Longer text is split at spaces without keeping leading or trailing whitespace on produced lines. Stdout reports `line[a specific sentinel value — ask the PM for the exact string]count=` followed by one `line[a specific sentinel value — ask the PM for the exact string]N=` line for each wrapped line in order.

**Test Cases:** `rcb[a specific sentinel value — ask the PM for the exact string]tests/public[a specific sentinel value — ask the PM for the exact string]test[a specific sentinel value — ask the PM for the exact string]cases/feature3[a specific sentinel value — ask the PM for the exact string]plain[a specific sentinel value — ask the PM for the exact string]text[a specific sentinel value — ask the PM for the exact string]wrapping.json`

```json
{
    "description": "Plain text is split at spaces when it exceeds the configured column width, preserving short text as a single line.",
    "cases": [
        {
            "input": {
                "scenario": "plain[a specific sentinel value — ask the PM for the exact string]text[a specific sentinel value — ask the PM for the exact string]wrapping",
                "text": "foo barbar baz"
            },
            "expected[a specific sentinel value — ask the PM for the exact string]output": "line[a specific sentinel value — ask the PM for the exact string]count=1\nline[a specific sentinel value — ask the PM for the exact string]0=foo barbar baz\n"
        },
        {
            "input": {
                "scenario": "plain[a specific sentinel value — ask the PM for the exact string]text[a specific sentinel value — ask the PM for the exact string]wrapping",
                "text": "foo barbar baz",
                "column": 10
            },
            "expected[a specific sentinel value — ask the PM for the exact string]output": "line[a specific sentinel value — ask the PM for the exact string]count=2\nline[a specific sentinel value — ask the PM for the exact string]0=foo barbar\nline[a specific sentinel value — ask the PM for the exact string]1=baz\n"
        }
    ]
}
```

---

### Feature 4: YAML Block Text Formatting

**As a developer**, I want to format long description text for YAML fields, so generated manifests have stable wrapped indentation.

**Expected Behavior / Usage:**

The adapter input provides a single prose string. The output wraps it to the standard YAML-description width and prefixes each generated line with two spaces. Stdout is the formatted block text itself, including line breaks, so it can be embedded directly under a YAML key.

**Test Cases:** `rcb[a specific sentinel value — ask the PM for the exact string]tests/public[a specific sentinel value — ask the PM for the exact string]test[a specific sentinel value — ask the PM for the exact string]cases/feature4[a specific sentinel value — ask the PM for the exact string]yaml[a specific sentinel value — ask the PM for the exact string]block[a specific sentinel value — ask the PM for the exact string]text.json`

```json
{
    "description": "Long description text rendered for YAML block fields is wrapped to the standard line width and each produced line is indented by two spaces.",
    "cases": [
        {
            "input": {
                "scenario": "yaml[a specific sentinel value — ask the PM for the exact string]block[a specific sentinel value — ask the PM for the exact string]text",
                "text": "one two three four five size seven eight nine ten eleven twelve thirteen fourteen fifteen"
            },
            "expected[a specific sentinel value — ask the PM for the exact string]output": "  one two three four five size seven eight nine ten eleven twelve thirteen\n  fourteen fifteen\n"
        }
    ]
}
```

---

### Feature 5: Project Template Catalog

**As a developer**, I want to list the available project templates, so tools can discover what kinds of projects can be generated.

**Expected Behavior / Usage:**

The adapter input requests the catalog. Stdout begins with `template[a specific sentinel value — ask the PM for the exact string]count=` and then emits, in sorted order, each template selector, label, description, entrypoint path, and install instruction summary. The catalog must include command-line, package/library, server, and web project starters with stable metadata.

**Test Cases:** `rcb[a specific sentinel value — ask the PM for the exact string]tests/public[a specific sentinel value — ask the PM for the exact string]test[a specific sentinel value — ask the PM for the exact string]cases/feature5[a specific sentinel value — ask the PM for the exact string]template[a specific sentinel value — ask the PM for the exact string]catalog.json`

```json
{
    "description": "The template catalog exposes the complete sorted set of available project templates with user-facing labels, descriptions, entrypoint paths, and install instructions.",
    "cases": [
        {
            "input": {
                "scenario": "template[a specific sentinel value — ask the PM for the exact string]catalog"
            },
            "expected[a specific sentinel value — ask the PM for the exact string]output": "template[a specific sentinel value — ask the PM for the exact string]count=[a hard-coded number of templates — ask the PM for the exact integer]\ntemplate=console-full\nlabel=Console Application\ndescription=A larger command-line application sample.\nentrypoint=bin/main.dart\ninstall=to provision required packages, run 'pub get' | run your app using 'dart bin/main.dart'\ntemplate=console-simple\nlabel=Simple Console Application\ndescription=A simple command-line application.\nentrypoint=bin/main.dart\ninstall=run your app using 'dart bin/main.dart'\ntemplate=package-simple\nlabel=Dart Package\ndescription=A starting point for Dart libraries or applications.\nentrypoint=lib/[a specific sentinel value — ask the PM for the exact string][a specific sentinel value — ask the PM for the exact string]projectName[a specific sentinel value — ask the PM for the exact string][a specific sentinel value — ask the PM for the exact string].dart\ninstall=to provision required packages, run 'pub get'\ntemplate=server-shelf\nlabel=Shelf Web Server\ndescription=A web server built using the shelf package.\nentrypoint=bin/server.dart\ninstall=to provision required packages, run 'pub get' | run your app via 'dart bin/server.dart'\ntemplate=web-angular\nlabel=Angular Web Application\ndescription=A web app built using the latest stable version of Angular.\nentrypoint=web/index.html\ninstall=to provision required packages, run 'pub get' | to run your app, use 'pub serve'\ntemplate=web-angular-simple\nlabel=Simple Angular Example\ndescription=A minimalist example app used in docs.\nentrypoint=web/index.html\ninstall=to provision required packages, run 'pub get' | to run your app, use 'pub serve'\ntemplate=web-simple\nlabel=Simple Web Application\ndescription=An absolute bare-bones web app.\nentrypoint=web/index.html\ninstall=to provision required packages, run 'pub get'\n"
        }
    ]
}
```

---

### Feature 6: Project Generation Summary

**As a developer**, I want to generate a selected starter project and inspect its observable file set, so I can verify the scaffold was created correctly.

**Expected Behavior / Usage:**

The adapter input supplies a template selector, project name, and author value. For a valid selector, the system renders the scaffold into a recording target and stdout reports the selector, project name, file count, entrypoint path, common metadata-file presence, package name/version/runtime constraint from the generated manifest, and first/last generated relative paths. For an unknown selector, stdout reports `error=unknown[a specific sentinel value — ask the PM for the exact string]template` and the raw `template[a specific sentinel value — ask the PM for the exact string]selector=`.

**Test Cases:** `rcb[a specific sentinel value — ask the PM for the exact string]tests/public[a specific sentinel value — ask the PM for the exact string]test[a specific sentinel value — ask the PM for the exact string]cases/feature6[a specific sentinel value — ask the PM for the exact string]project[a specific sentinel value — ask the PM for the exact string]generation[a specific sentinel value — ask the PM for the exact string]summary.json`

```json
{
    "description": "Generating a selected project template writes the expected number of relative files, identifies the intended entrypoint, includes common metadata files, and substitutes the project name into package metadata.",
    "cases": [
        {
            "input": {
                "scenario": "project[a specific sentinel value — ask the PM for the exact string]generation[a specific sentinel value — ask the PM for the exact string]summary",
                "template[a specific sentinel value — ask the PM for the exact string]selector": "console-full",
                "project[a specific sentinel value — ask the PM for the exact string]name": "foo",
                "author": "Ada Lovelace"
            },
            "expected[a specific sentinel value — ask the PM for the exact string]output": "template=console-full\nproject[a specific sentinel value — ask the PM for the exact string]name=foo\nfile[a specific sentinel value — ask the PM for the exact string]count=9\nentrypoint=bin/main.dart\nhas[a specific sentinel value — ask the PM for the exact string]gitignore=present\nhas[a specific sentinel value — ask the PM for the exact string]pubspec=present\npubspec[a specific sentinel value — ask the PM for the exact string]name=foo\npubspec[a specific sentinel value — ask the PM for the exact string]version=0.0.1\npubspec[a specific sentinel value — ask the PM for the exact string]sdk='>=1.20.1 <2.0.0'\nfirst[a specific sentinel value — ask the PM for the exact string]file=.gitignore\nlast[a specific sentinel value — ask the PM for the exact string]file=test/foo[a specific sentinel value — ask the PM for the exact string]test.dart\n"
        },
        {
            "input": {
                "scenario": "project[a specific sentinel value — ask the PM for the exact string]generation[a specific sentinel value — ask the PM for the exact string]summary",
                "template[a specific sentinel value — ask the PM for the exact string]selector": "web-angular",
                "project[a specific sentinel value — ask the PM for the exact string]name": "foo",
                "author": "Ada Lovelace"
            },
            "expected[a specific sentinel value — ask the PM for the exact string]output": "template=web-angular\nproject[a specific sentinel value — ask the PM for the exact string]name=foo\nfile[a specific sentinel value — ask the PM for the exact string]count=15\nentrypoint=web/index.html\nhas[a specific sentinel value — ask the PM for the exact string]gitignore=present\nhas[a specific sentinel value — ask the PM for the exact string]pubspec=present\npubspec[a specific sentinel value — ask the PM for the exact string]name=foo\npubspec[a specific sentinel value — ask the PM for the exact string]version=0.0.1\npubspec[a specific sentinel value — ask the PM for the exact string]sdk='>=1.20.1 <2.0.0'\nfirst[a specific sentinel value — ask the PM for the exact string]file=.gitignore\nlast[a specific sentinel value — ask the PM for the exact string]file=web/styles.css\n"
        },
        {
            "input": {
                "scenario": "project[a specific sentinel value — ask the PM for the exact string]generation[a specific sentinel value — ask the PM for the exact string]summary",
                "template[a specific sentinel value — ask the PM for the exact string]selector": "bad-template",
                "project[a specific sentinel value — ask the PM for the exact string]name": "foo",
                "author": "Ada Lovelace"
            },
            "expected[a specific sentinel value — ask the PM for the exact string]output": "error=unknown[a specific sentinel value — ask the PM for the exact string]template\ntemplate[a specific sentinel value — ask the PM for the exact string]selector=bad-template\n"
        }
    ]
}
```

---

### Feature [a hard-coded number of templates — ask the PM for the exact integer]: Command-Line Interface Behavior

**As a developer**, I want to invoke the generator through a CLI-style adapter, so end users and tools receive stable observable command results.

**Expected Behavior / Usage:**

The adapter input supplies an argument array. With no arguments, stdout indicates a successful help/usage display. With a valid template selector, stdout indicates successful creation and the number of files routed through the generation target. With invalid selectors or too many positional arguments, stdout reports a neutral error category and observable stdout/stderr signals. With machine-readable catalog or version flags, stdout reports the corresponding signal and summary values rather than leaking runtime-specific details.

**Test Cases:** `rcb[a specific sentinel value — ask the PM for the exact string]tests/public[a specific sentinel value — ask the PM for the exact string]test[a specific sentinel value — ask the PM for the exact string]cases/feature[a hard-coded number of templates — ask the PM for the exact integer][a specific sentinel value — ask the PM for the exact string]command[a specific sentinel value — ask the PM for the exact string]line[a specific sentinel value — ask the PM for the exact string]behavior.json`

```json
{
    "description": "The command-line interface reports help when invoked without a template, creates files for a valid template selector, reports invalid argument errors neutrally, emits a machine-readable catalog, and reports its version.",
    "cases": [
        {
            "input": {
                "scenario": "command[a specific sentinel value — ask the PM for the exact string]line[a specific sentinel value — ask the PM for the exact string]result",
                "arguments": []
            },
            "expected[a specific sentinel value — ask the PM for the exact string]output": "status=success\nstdout[a specific sentinel value — ask the PM for the exact string]length=[a precise byte count — ask the PM for the exact integer]\nstderr[a specific sentinel value — ask the PM for the exact string]length=0\ncreated[a specific sentinel value — ask the PM for the exact string]files=0\nstdout[a specific sentinel value — ask the PM for the exact string]signal=usage\n"
        },
        {
            "input": {
                "scenario": "command[a specific sentinel value — ask the PM for the exact string]line[a specific sentinel value — ask the PM for the exact string]result",
                "arguments": [
                    "console-full"
                ]
            },
            "expected[a specific sentinel value — ask the PM for the exact string]output": "status=success\nstdout[a specific sentinel value — ask the PM for the exact string]length=151\nstderr[a specific sentinel value — ask the PM for the exact string]length=0\ncreated[a specific sentinel value — ask the PM for the exact string]files=9\n"
        },
        {
            "input": {
                "scenario": "command[a specific sentinel value — ask the PM for the exact string]line[a specific sentinel value — ask the PM for the exact string]result",
                "arguments": [
                    "bad[a specific sentinel value — ask the PM for the exact string]generator"
                ]
            },
            "expected[a specific sentinel value — ask the PM for the exact string]output": "status=error\nerror=invalid[a specific sentinel value — ask the PM for the exact string]template[a specific sentinel value — ask the PM for the exact string]selector\nstdout[a specific sentinel value — ask the PM for the exact string]length=[a precise byte count — ask the PM for the exact integer]\nstderr[a specific sentinel value — ask the PM for the exact string]length=42\ncreated[a specific sentinel value — ask the PM for the exact string]files=0\nstdout[a specific sentinel value — ask the PM for the exact string]signal=usage\nstderr[a specific sentinel value — ask the PM for the exact string]signal=invalid[a specific sentinel value — ask the PM for the exact string]template[a specific sentinel value — ask the PM for the exact string]selector\n"
        },
        {
            "input": {
                "scenario": "command[a specific sentinel value — ask the PM for the exact string]line[a specific sentinel value — ask the PM for the exact string]result",
                "arguments": [
                    "--machine"
                ]
            },
            "expected[a specific sentinel value — ask the PM for the exact string]output": "status=success\nstdout[a specific sentinel value — ask the PM for the exact string]length=1029\nstderr[a specific sentinel value — ask the PM for the exact string]length=0\ncreated[a specific sentinel value — ask the PM for the exact string]files=0\nmachine[a specific sentinel value — ask the PM for the exact string]count=[a hard-coded number of templates — ask the PM for the exact integer]\nmachine[a specific sentinel value — ask the PM for the exact string]first=console-full\nmachine[a specific sentinel value — ask the PM for the exact string]last=web-simple\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb[a specific sentinel value — ask the PM for the exact string]tests/public[a specific sentinel value — ask the PM for the exact string]test[a specific sentinel value — ask the PM for the exact string]cases/`. A single entry point `bash rcb[a specific sentinel value — ask the PM for the exact string]tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test[a specific sentinel value — ask the PM for the exact string]cases`). For each case it writes one file to `rcb[a specific sentinel value — ask the PM for the exact string]tests/stdout/<cases-dir>/{filename.stem}@{case[a specific sentinel value — ask the PM for the exact string]index.zfill(3)}.txt` (e.g. the first case in `feature1[a specific sentinel value — ask the PM for the exact string]project[a specific sentinel value — ask the PM for the exact string]name[a specific sentinel value — ask the PM for the exact string]normalization.json` run with `--cases-dir public[a specific sentinel value — ask the PM for the exact string]test[a specific sentinel value — ask the PM for the exact string]cases` → `rcb[a specific sentinel value — ask the PM for the exact string]tests/stdout/public[a specific sentinel value — ask the PM for the exact string]test[a specific sentinel value — ask the PM for the exact string]cases/feature1[a specific sentinel value — ask the PM for the exact string]project[a specific sentinel value — ask the PM for the exact string]name[a specific sentinel value — ask the PM for the exact string]normalization@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected[a specific sentinel value — ask the PM for the exact string]output`.


---
**Implementation notes:**
- follow the same whitespace preservation rules as the YAML formatter
- use the same path patterns found in the project manifest generator
