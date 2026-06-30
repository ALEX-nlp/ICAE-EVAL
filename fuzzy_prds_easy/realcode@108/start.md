## Product Requirement Document

# Project Scaffolding Toolkit Core — Path Rewriting, Manifest Parsing & Parameter Resolution

## Project Goal

Build the deterministic core of a project-scaffolding toolkit that turns reusable module templates into a generated project. This core provides the pure, side-effect-light building blocks that the rest of such a tool relies on: rewriting relative output paths, deciding whether a referenced module lives locally or must be fetched, reading module and project manifests into structured data, and resolving the final value of a configuration parameter. Developers get one well-specified contract for these primitives so the surrounding tool does not have to reinvent them.

---

## Background & Problem

A scaffolding tool assembles a project from a set of reusable modules. Each module ships a manifest describing its name and the parameters it needs; a project ships its own manifest naming the modules it composes and where each one's files should land. To generate output the tool must repeatedly: relocate template file paths into an output tree, distinguish module sources that are already on disk from ones that must be pulled from a remote location, parse those manifests, and compute concrete parameter values (some literal, some produced by running a small command).

Without a shared core, every part of the tool hand-rolls these primitives, producing inconsistent path handling, ad-hoc manifest parsing, and duplicated parameter logic. This project specifies the primitives once as black-box input/output contracts so they behave predictably and can be tested in isolation.

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

### Feature 1: Relative Path Rewriting

**As a developer**, I want small, predictable helpers for relocating relative file paths, so I can map template file locations into an output tree without mishandling parent-directory references.

**Expected Behavior / Usage:**

*1.1 Substring Path Replacement — replace the first occurrence of a leading path segment, then normalize.*

The input supplies a relative path, a search substring, and a replacement substring. The helper replaces only the first occurrence of the search substring within the path and then normalizes the result (collapsing redundant separators and resolving `.`/`..` references where possible). The output is the single rewritten path. This is used to move a file discovered under a template directory into the corresponding location under an output directory.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_replace_path.json`

```json
{
    "description": "Rewrite a relative file path by substituting the first occurrence of a leading directory segment with a replacement segment, then normalizing the result so that redundant separators and references are collapsed. The input supplies the original path, the substring to look for, and the replacement substring. The output is the single rewritten, cleaned path. Only the first match of the search substring is replaced.",
    "cases": [
        {
            "input": {"action": "replace_path", "path": "../../dir/file.ext", "old": "../../dir", "new": "output"},
            "expected_output": "output/file.ext\n"
        }
    ]
}
```

*1.2 Prefix Insertion Preserving Parent-Directory References — insert a prefix after any leading run of `..` hops.*

The input supplies a relative path and a prefix. The path is first normalized. If the normalized path begins with one or more consecutive parent-directory hops (`../`), the prefix is inserted immediately after that leading run of hops; otherwise the prefix is placed at the very front. An empty prefix leaves the normalized path unchanged. The output is the single resulting path. This keeps a relocation prefix from accidentally being buried beneath `..` segments that must stay at the front.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_prepend_path.json`

```json
{
    "description": "Insert a prefix directory into a relative file path while preserving any leading parent-directory references that climb above the current directory. The path is first normalized. If it begins with one or more parent-directory hops, the prefix is inserted immediately after that leading run of hops; otherwise the prefix is simply placed at the front. An empty prefix leaves the normalized path unchanged. The output is the single resulting path.",
    "cases": [
        {
            "input": {"action": "prepend_path", "path": "../../dir/file.ext", "prefix": "prefix"},
            "expected_output": "../../prefix/dir/file.ext\n"
        },
        {
            "input": {"action": "prepend_path", "path": "dir/file.ext", "prefix": "prefix"},
            "expected_output": "prefix/dir/file.ext\n"
        }
    ]
}
```

---

### Feature 2: Module Source Locality Resolution

**As a developer**, I want to classify a module's source reference as local or remote and know whether resolving it relocates it, so the tool knows when it can use files directly versus when it must fetch them into a cache.

**Expected Behavior / Usage:**

The input supplies a single module source reference string. A reference that names a local filesystem location — including one that explicitly begins from the current directory — is classified as `local`; resolving it yields the same location, so it is not relocated. A reference that names a remote repository — whether written with or without an explicit URL scheme — is classified as `remote`; resolving it maps the reference into a separate cache directory distinct from the original reference, so it is relocated. The output reports the locality classification and whether relocation occurred. (The concrete cache path is an internal detail and is not part of the contract; only the local/remote classification and the relocated/not-relocated outcome are.)

**Test Cases:** `rcb_tests/public_test_cases/feature2_source_locality.json`

```json
{
    "description": "Classify a module source reference as either a local filesystem location or a remote location, and report whether resolving it to a working directory relocates it. A source that names a local path (including one that explicitly starts from the current directory) is treated as local and is used as-is, so it is not relocated. A source that names a remote repository (whether given with or without an explicit scheme) is treated as remote and is mapped to a separate cache directory, so it is relocated. The output reports the locality and whether relocation occurred.",
    "cases": [
        {
            "input": {"action": "resolve_source", "source": "templates/base"},
            "expected_output": "locality=local\nrelocated=false\n"
        },
        {
            "input": {"action": "resolve_source", "source": "github.com/acme/widgets"},
            "expected_output": "locality=remote\nrelocated=true\n"
        }
    ]
}
```

---

### Feature 3: Module Manifest Parsing

**As a developer**, I want to read a module's manifest into a structured description, so the tool can discover a module's name and the parameters it expects from end users.

**Expected Behavior / Usage:**

The input supplies a module manifest as a YAML document. The manifest declares a human-readable module name and an ordered list of input parameters; each parameter declares a `field` key, an optional display `label`, and an optional list of selectable `options`. (The manifest may also carry additional sections such as templating settings; those are not part of this contract.) The output reports the module name, the number of parameters, and one line per parameter — in declaration order — giving its field, its label, and its options joined by commas (empty when no options are declared). The reader does not invent defaults for absent labels or options; an absent label or option list yields an empty value in the output.

**Test Cases:** `rcb_tests/public_test_cases/feature3_module_manifest.json`

```json
{
    "description": "Parse a module manifest document (YAML) into a structured description. The manifest declares a human-readable module name and a list of input parameters; each parameter declares a field key, an optional display label, and an optional list of selectable options. The output reports the module name, the number of parameters, and one line per parameter giving its field, label, and comma-joined options (empty when none are declared), in declaration order.",
    "cases": [
        {
            "input": {"action": "parse_module_manifest", "manifest": "name: \"CI templates\"\ndescription: \"\"\nauthor: \"\"\ntemplate:\n  delimiters:\n    - \"<%\"\n    - \"%>\"\n  output: \"github/test\"\nparameters:\n  - field: platform\n    label: CI Platform\n    options:\n      - github\n      - circlci\n"},
            "expected_output": "name=CI templates\nparameter_count=1\nparameter field=platform label=CI Platform options=github,circlci\n"
        }
    ]
}
```

---

### Feature 4: Project Manifest Parsing

**As a developer**, I want to read a project's manifest into a structured description, so the tool knows which modules compose the project, where each one's files belong, and what parameter values each one carries.

**Expected Behavior / Usage:**

The input supplies a project manifest as a YAML document. The manifest declares a project name and a set of named modules. Each module may declare a files block — a destination directory and a source repository — and an optional map of parameter key/value pairs. The output reports the project name, the number of modules, and one line per module. Modules are listed in ascending name order for stable output. Each module line gives the module's name, its directory, its repository, and its parameters rendered as comma-joined `key=value` pairs sorted in ascending key order (empty when the module declares no parameters). Absent directory or repository values render as empty.

**Test Cases:** `rcb_tests/public_test_cases/feature4_project_manifest.json`

```json
{
    "description": "Parse a project manifest document (YAML) into a structured project description. The manifest declares a project name and a set of named modules; each module may declare a files block (a destination directory and a source repository) and an optional map of parameter key/value pairs. The output reports the project name, the number of modules, and one line per module (modules listed in ascending name order) giving the module name, its directory, its repository, and its parameters as comma-joined key=value pairs in ascending key order (empty when none).",
    "cases": [
        {
            "input": {"action": "load_project_manifest", "manifest": "name: acme-app\nmodules:\n    infrastructure:\n        parameters:\n            repoName: infrastructure\n            region: us-east-1\n            accountId: 12345\n            productionHost: something.com\n        files:\n            dir: infrastructure\n            repo: https://github.com/acme/infrastructure\n    backend:\n        files:\n            dir: app-backend\n            repo: github.com/acme/app-backend\n"},
            "expected_output": "name=acme-app\nmodule_count=2\nmodule=backend dir=app-backend repo=github.com/acme/app-backend params=\nmodule=infrastructure dir=infrastructure repo=https://github.com/acme/infrastructure params=accountId=12345,productionHost=something.com,region=us-east-1,repoName=infrastructure\n"
        }
    ]
}
```

---

### Feature 5: Parameter Value Resolution

**As a developer**, I want to resolve a single configuration parameter down to its concrete value, so the tool can fill templates with either literal values or values computed at run time.

**Expected Behavior / Usage:**

The input supplies a single parameter definition. A parameter may carry a static literal value, or a shell command to execute whose captured standard output becomes the value, alongside an optional map of contextual key/value pairs that are injected into the command's environment. When a command is provided it takes precedence over any static value: the command is run, its standard output is captured, and any embedded newline characters are stripped from the captured text to yield the final value. When only a static value is provided, that value is used directly. The contextual key/value pairs are exposed to the command as environment variables, so a command may reference them. The output reports the resolved value.

**Test Cases:** `rcb_tests/public_test_cases/feature5_parameter_resolution.json`

```json
{
    "description": "Resolve the final value of a single configuration parameter. A parameter may carry a static literal value, or a shell command to execute whose captured standard output becomes the value, or both kinds of inputs alongside a map of contextual key/value pairs that are injected into the command's environment. When a command is provided it takes precedence over a static value; the executed command's output is captured and any embedded newline characters are stripped from it. The output reports the resolved value.",
    "cases": [
        {
            "input": {"action": "resolve_parameter", "field": "placeholder", "value": "lorem-ipsum"},
            "expected_output": "value=lorem-ipsum\n"
        },
        {
            "input": {"action": "resolve_parameter", "field": "myEnv", "execute": "echo $INJECTEDENV", "project_params": {"INJECTEDENV": "SOME_ENV_VAR_VALUE"}},
            "expected_output": "value=SOME_ENV_VAR_VALUE\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the resulting output to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `replace_path` and `prepend_path` invoke the path helpers; `resolve_source` classifies a module source reference; `parse_module_manifest` parses a module manifest document; `load_project_manifest` parses a project manifest document; `resolve_parameter` resolves a parameter definition to its concrete value. Map/dictionary outputs MUST be emitted in a deterministic (sorted) order as specified per feature.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- execute with 'project_params' set environment vars
