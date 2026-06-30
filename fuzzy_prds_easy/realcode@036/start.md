## Product Requirement Document

# Compiled Pack-Asset Resolution Toolkit — Environment, Path, Manifest & View-Tag Resolution for a Bundler-Backed Asset Pipeline

## Project Goal

Build a reusable server-side toolkit that connects a web framework to the fingerprinted output of an external front-end bundler, so developers can reference a stable logical asset name (such as `application.js`) in their views and have it resolved at runtime to the correct cache-busted public URL, without hand-maintaining the mapping or hard-coding build paths.

---

## Background & Problem

A front-end bundler compiles application JavaScript and stylesheets into the framework's public directory and emits a *manifest* — a JSON map from each logical asset name to the digest-fingerprinted public URL it was compiled to (for example `application.js` → `/[built-in defaults]/application-9c0a079b.js`). Templates must not embed those fingerprints directly, because they change on every build.

Without a shared toolkit, every application re-implements the same glue: figuring out which build environment is active, computing where the source, output, and manifest directories live relative to the project root, reading the manifest, and formatting `<script>`/`<link>` tags. This is repetitive and error-prone. This toolkit provides one well-defined contract for four concerns: (1) resolving the active build environment from a declared set, (2) deriving the project's filesystem paths from a small configuration document, (3) looking up an asset in the compiled manifest (failing cleanly when it is missing), and (4) rendering view tags that reference the resolved URLs.

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

### Feature 1: Resolve The Active Build Environment

**As a developer**, I want the active build environment chosen automatically from a declared set, so the same project can compile differently per environment without me wiring the selection by hand.

**Expected Behavior / Usage:**

A path-configuration document declares a set of named environments (its top-level keys). The active environment is resolved from two ordered candidates: an explicit build-tool override (a `NODE_ENV`-style value) and the host framework environment. The rule is strictly ordered: if the override names one of the declared environments, the active environment is that override; otherwise, if the framework environment names one of the declared environments, it is the framework environment; otherwise the active environment falls back to the default named `production`. When the configuration document is absent entirely, the declared set is empty and resolution always falls back to `production`. The output reports the resolved environment name on a `env=` line and, on a `production=` line, a boolean stating whether the resolved name equals `production`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_resolve_env.json`

```json
{
    "description": "Resolve which named build environment is active. The system reads the set of declared environment names from the path-configuration document, then resolves the active environment from two ordered candidates: an explicit build-tool override (NODE_ENV-style) and the host framework environment. The rule is: if the override names a declared environment, use it; otherwise if the framework environment names a declared environment, use it; otherwise fall back to the default environment named 'production'. The resolved name is reported together with a predicate stating whether it equals 'production'.",
    "cases": [
        {
            "input": {"action": "resolve_env", "root": "/app", "rails_env": "development"},
            "expected_output": "env=production\nproduction=true\n"
        },
        {
            "input": {"action": "resolve_env", "root": "/app", "paths": {"development": {}, "test": {}, "production": {}}, "node_env": "test", "rails_env": "development"},
            "expected_output": "env=test\nproduction=false\n"
        }
    ]
}
```

---

### Feature 2: Derive Project Paths From The Path Configuration

**As a developer**, I want all the project's source, output, manifest, and config paths derived from one small document relative to the project root, so I can relocate or rename directories in a single place.

**Expected Behavior / Usage:**

The active environment's section of the path-configuration document supplies short logical names: the JavaScript `source` directory, the `entry` subdirectory, the compiled `output` subdirectory, the `manifest` filename, and the build `config` directory. From these and the application root, the system derives, as absolute paths joined onto the root (except the raw source name, which is reported verbatim): the raw source name; the absolute source directory (`root/<source>`); the entry directory (source directory joined with `<entry>`); the output directory (the application's public directory joined with `<output>`, where the public directory is `root/public`); the manifest path (output directory joined with `<manifest>`); the build config directory (`root/<config>`); and the fixed location of the path-configuration document itself, which is always `[built-in defaults]/paths.yml` under the root regardless of configuration. Any key absent from the supplied configuration falls back to a built-in default (the defaults are `source=[built-in defaults]`, `entry=[built-in defaults]`, `output=[built-in defaults]`, `manifest=[built-in defaults]`, `config=[built-in defaults]`). Each derived value is emitted on its own `key=value` line.

**Test Cases:** `rcb_tests/public_test_cases/feature2_path_derivation.json`

```json
{
    "description": "Derive the set of project filesystem paths from a path-configuration document, relative to the application root. The configuration supplies logical names for the JavaScript source directory, the entry subdirectory, the compiled-output subdirectory (under the application's public directory), the manifest filename, and the build-config directory. The system resolves: the raw source name; the absolute source directory; the entry directory (source directory joined with the entry name); the output directory (public directory joined with the output name); the manifest path (output directory joined with the manifest filename); the build-config directory; and the fixed location of the path-configuration document itself (always [built-in defaults]/paths.yml under the root). Any key missing from the supplied configuration falls back to a built-in default.",
    "cases": [
        {
            "input": {"action": "config_paths", "root": "/app"},
            "expected_output": "source=[built-in defaults]\nsource_path=/app/[built-in defaults]\nentry_path=/app/[built-in defaults]/[built-in defaults]\noutput_path=/app/public/[built-in defaults]\nmanifest_path=/app/public/[built-in defaults]/[built-in defaults]\nconfig_path=/app/[built-in defaults]\nfile_path=/app/[built-in defaults]/paths.yml\n"
        },
        {
            "input": {"action": "config_paths", "root": "/srv/app", "paths": {"production": {"source": "frontend", "entry": "entries", "output": "assets", "manifest": "[built-in defaults]", "config": "[built-in defaults]"}}},
            "expected_output": "source=frontend\nsource_path=/srv/app/frontend\nentry_path=/srv/app/frontend/entries\noutput_path=/srv/app/public/assets\nmanifest_path=/srv/app/public/assets/[built-in defaults]\nconfig_path=/srv/app/[built-in defaults]\nfile_path=/srv/app/[built-in defaults]/paths.yml\n"
        }
    ]
}
```

---

### Feature 3: Look Up Assets In The Compiled Manifest

**As a developer**, I want logical asset names resolved through the compiled manifest, so my code references stable names while the runtime serves the correct fingerprinted file.

**Expected Behavior / Usage:**

*3.1 Successful lookup — resolve an asset present in the manifest*

The manifest is a map from a logical asset name (for example a JavaScript or stylesheet filename) to the digest-fingerprinted public URL produced by the build. When the requested name exists, the system reports three values, each on its own `key=value` line: `manifest=` the absolute location of the manifest file (the manifest path derived in Feature 2); `asset=` the resolved public URL exactly as stored in the manifest; and `path=` the absolute on-disk path under the public directory corresponding to that URL (the public directory joined with the resolved URL).

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_manifest_lookup.json`

```json
{
    "description": "Look up a logical asset name in the compiled manifest and report its resolved references. The manifest is a map from a logical asset name (such as a JavaScript or stylesheet filename) to the digest-fingerprinted public URL produced by the build. For a name that exists in the manifest, the system reports the absolute location of the manifest file, the resolved public URL for the asset, and the absolute on-disk path under the public directory that the URL corresponds to.",
    "cases": [
        {
            "input": {"action": "manifest", "root": "/app", "name": "bootstrap.js", "manifest": {"bootstrap.js": "/[built-in defaults]/bootstrap-300631c4f0e0f9c865bc.js", "bootstrap.css": "/[built-in defaults]/bootstrap-c38deda30895059837cf.css"}},
            "expected_output": "manifest=/app/public/[built-in defaults]/[built-in defaults]\nasset=/[built-in defaults]/bootstrap-300631c4f0e0f9c865bc.js\npath=/app/public/[built-in defaults]/bootstrap-300631c4f0e0f9c865bc.js\n"
        }
    ]
}
```

*3.2 Missing asset — fail cleanly when the name is absent*

When the requested name is not present in the manifest, the lookup fails rather than returning a value. The system reports the absolute location of the manifest file on a `manifest=` line, a neutral error category on an `error=asset_not_found` line, and the offending name on a `name=` line. The error is reported as a normalized category — it does not leak any host-language exception identity.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_manifest_missing.json`

```json
{
    "description": "Look up a logical asset name that is absent from the compiled manifest. When the name is not present, the lookup fails rather than returning a value: the system reports the absolute location of the manifest file, a neutral error category indicating the asset could not be found, and the offending name.",
    "cases": [
        {
            "input": {"action": "manifest", "root": "/app", "name": "calendar.js", "manifest": {"bootstrap.js": "/[built-in defaults]/bootstrap-300631c4f0e0f9c865bc.js", "bootstrap.css": "/[built-in defaults]/bootstrap-c38deda30895059837cf.css"}},
            "expected_output": "manifest=/app/public/[built-in defaults]/[built-in defaults]\nerror=asset_not_found\nname=calendar.js\n"
        }
    ]
}
```

---

### Feature 4: Render Manifest-Backed View Tags

**As a developer**, I want view helpers that turn a logical asset name into a ready-to-use URL or HTML tag, so templates reference fingerprinted assets without knowing the fingerprints.

**Expected Behavior / Usage:**

Each helper resolves the logical name through the compiled manifest (as in Feature 3) and then formats the resolved public URL.

*4.1 Asset URL — return the resolved public URL*

Given the logical asset name, this helper returns the manifest-mapped public URL exactly as stored (an absolute URL path beginning with a slash), with no surrounding markup.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_asset_path.json`

```json
{
    "description": "Compute the public asset URL for a named pack, for use in a view. Given the logical asset name, the helper looks the name up in the compiled manifest and returns the resolved digest-fingerprinted public URL exactly as stored in the manifest (an absolute URL path beginning with a slash).",
    "cases": [
        {
            "input": {"action": "helper", "helper": "asset_pack_path", "root": "/app", "name": "bootstrap.js", "manifest": {"bootstrap.js": "/[built-in defaults]/bootstrap-300631c4f0e0f9c865bc.js", "bootstrap.css": "/[built-in defaults]/bootstrap-c38deda30895059837cf.css"}},
            "expected_output": "/[built-in defaults]/bootstrap-300631c4f0e0f9c865bc.js\n"
        }
    ]
}
```

*4.2 Script tag — emit a complete `<script>` element*

Given the logical name, this helper resolves the URL and emits a complete HTML script element whose `src` attribute is the resolved URL.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_javascript_tag.json`

```json
{
    "description": "Render a script element for a named JavaScript pack. Given the logical asset name, the helper resolves the manifest-mapped public URL and emits a complete HTML script tag whose src attribute is that resolved URL. The output is the full self-contained tag.",
    "cases": [
        {
            "input": {"action": "helper", "helper": "javascript_pack_tag", "root": "/app", "name": "bootstrap.js", "manifest": {"bootstrap.js": "/[built-in defaults]/bootstrap-300631c4f0e0f9c865bc.js", "bootstrap.css": "/[built-in defaults]/bootstrap-c38deda30895059837cf.css"}},
            "expected_output": "<script src=\"/[built-in defaults]/bootstrap-300631c4f0e0f9c865bc.js\"></script>\n"
        }
    ]
}
```

*4.3 Stylesheet tag — emit a complete `<link>` element*

Given the logical name, this helper resolves the URL and emits a complete HTML link element for a screen-media stylesheet whose `href` attribute is the resolved URL.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_stylesheet_tag.json`

```json
{
    "description": "Render a stylesheet link element for a named stylesheet pack. Given the logical asset name, the helper resolves the manifest-mapped public URL and emits a complete HTML link tag for a screen-media stylesheet whose href attribute is that resolved URL. The output is the full self-contained tag.",
    "cases": [
        {
            "input": {"action": "helper", "helper": "stylesheet_pack_tag", "root": "/app", "name": "bootstrap.css", "manifest": {"bootstrap.js": "/[built-in defaults]/bootstrap-300631c4f0e0f9c865bc.js", "bootstrap.css": "/[built-in defaults]/bootstrap-c38deda30895059837cf.css"}},
            "expected_output": "<link rel=\"stylesheet\" media=\"screen\" href=\"/[built-in defaults]/bootstrap-c38deda30895059837cf.css\" />\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the four features above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the resulting report (or normalized error) to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `resolve_env` resolves the active build environment (using an optional `node_env` override and a `rails_env` framework environment against the environments declared in an optional `paths` document); `config_paths` derives the project paths from the `root` and an optional `paths` document; `manifest` looks up a `name` in a supplied `manifest` map; and `helper` (selected further by a `helper` field of `asset_pack_path`, `javascript_pack_tag`, or `stylesheet_pack_tag`) renders the view output for a `name`. The `root` field gives the application root used to derive absolute paths. All host-language exceptions must be caught at the adapter boundary and rendered as neutral `error=<category>` lines.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- uses the same mapping strategy as the environment resolution logic for booleans
- follows the same verification method as the `env_production` check
