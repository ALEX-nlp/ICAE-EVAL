## Product Requirement Document

# Build Manifest Emitter - Asset Manifest Generation for Bundled Applications

## Project Goal

Build a build-system extension that records emitted asset metadata in a JSON manifest so developers can connect server-rendered applications or deployment tooling to bundled JavaScript and CSS outputs without hand-maintaining file lists, public URLs, or dependency ordering.

---

## Background & Problem

Without this library/tool, developers are forced to inspect build output directories, reconstruct which emitted files belong to each entry point, and manually keep public URLs, compressed variants, and error states in sync with each build. This leads to repetitive glue code, stale manifests, brittle deployment templates, and failures that are hard to diagnose when build outputs change.

With this library/tool, each build writes a deterministic JSON manifest describing status, entry-to-file mappings, asset metadata, public URLs, optional timing information, optional integrity metadata, compressed variants, and normalized build failure signals.

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

### Feature 1: Terminal Control Sequence Text Cleanup

**As a developer**, I want to sanitize terminal-formatted text, so I can store or display plain text without embedded control bytes.

**Expected Behavior / Usage:**

The input is a JSON object containing a text value. The output is a JSON object whose text field contains the same user-visible characters after removing terminal styling, color, reset, and hyperlink escape sequences. Empty text remains empty, and text with no control sequences is unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature1_terminal_control_sequence_text.json`

```json
{
    "description": "Text containing terminal control sequences is rendered as plain text with the control sequences removed.",
    "cases": [
        {
            "input": {
                "text": ""
            },
            "expected_output": "{\n  \"text\": \"\"\n}\n"
        },
        {
            "input": {
                "text": "Hello"
            },
            "expected_output": "{\n  \"text\": \"Hello\"\n}\n"
        }
    ]
}
```

---

### Feature 2: Single Entry Build Manifest

**As a developer**, I want to obtain a machine-readable manifest for a simple successful build, so I can map a named entry point to its emitted file and public URL.

**Expected Behavior / Usage:**

The input selects a simple one-entry build scenario and a compatible bundler generation. The output is raw JSON text containing a done status, the configured public base URL, a chunks object mapping the entry name to its emitted file list, and an assets object describing each emitted file name, filesystem path marker, and public URL.

**Test Cases:** `rcb_tests/public_test_cases/feature2_single_entry_manifest.json`

```json
{
    "description": "A successful single-entry build emits a manifest with done status, a public base URL, an entry-to-file list, and asset metadata.",
    "cases": [
        {
            "input": {
                "bundler": "legacy",
                "build": "single_entry_manifest"
            },
            "expected_output": "{\n  \"status\": \"done\",\n  \"publicPath\": \"http://localhost:3000/assets/\",\n  \"chunks\": {\n    \"main\": [\n      \"[a specific locally emitted file path that will be relative]\"\n    ]\n  },\n  \"assets\": {\n    \"[a specific locally emitted file path that will be relative]\": {\n      \"name\": \"[a specific locally emitted file path that will be relative]\",\n      \"path\": \"OUTPUT_DIR/[a specific locally emitted file path that will be relative]\",\n      \"publicPath\": \"http://localhost:3000/assets/[a specific locally emitted file path that will be relative]\"\n    }\n  }\n}\n"
        }
    ]
}
```

---

### Feature 3: Build Timing Metadata

**As a developer**, I want to request timing metadata for a successful build, so I can confirm when the manifest-producing build started and ended.

**Expected Behavior / Usage:**

The input selects a successful one-entry build with timing enabled. The output is raw JSON text containing done status and timing signals showing that start and end timestamps were present, positive, and ordered so the end is not before the start.

**Test Cases:** `rcb_tests/public_test_cases/feature3_timing_fields.json`

```json
{
    "description": "When timing is requested, a successful build manifest includes positive start and end timestamps in chronological order.",
    "cases": [
        {
            "input": {
                "bundler": "legacy",
                "build": "timed_single_entry_manifest"
            },
            "expected_output": "{\n  \"status\": \"done\",\n  \"timing\": {\n    \"startTime\": \"positive_number\",\n    \"endTime\": \"positive_number\",\n    \"order\": \"end_not_before_start\"\n  }\n}\n"
        }
    ]
}
```

---

### Feature 4: Custom Public URL Override

**As a developer**, I want to override the public URL written to the manifest, so I can serve generated assets from a different externally visible location.

**Expected Behavior / Usage:**

The input selects a successful one-entry build with an explicit public URL override. The output is raw JSON text whose manifest-level public base URL and asset-level public URL use the override rather than the bundler output default.

**Test Cases:** `rcb_tests/public_test_cases/feature4_custom_public_url.json`

```json
{
    "description": "A build-level public URL override replaces the emitted public base URL and each asset URL in the manifest.",
    "cases": [
        {
            "input": {
                "bundler": "legacy",
                "build": "custom_public_url_manifest"
            },
            "expected_output": "{\n  \"status\": \"done\",\n  \"publicPath\": \"https://test.org/statics/\",\n  \"chunks\": {\n    \"main\": [\n      \"[a specific locally emitted file path that will be relative]\"\n    ]\n  },\n  \"assets\": {\n    \"[a specific locally emitted file path that will be relative]\": {\n      \"name\": \"[a specific locally emitted file path that will be relative]\",\n      \"path\": \"OUTPUT_DIR/[a specific locally emitted file path that will be relative]\",\n      \"publicPath\": \"https://test.org/statics/[a specific locally emitted file path that will be relative]\"\n    }\n  }\n}\n"
        }
    ]
}
```

---

### Feature 5: Manifest File Placement

**As a developer**, I want to choose where the build manifest is written, so I can integrate the manifest with deployment layouts that expect a particular file name or nested directory.

**Expected Behavior / Usage:**

The input selects a successful one-entry build and a manifest location mode. The output is raw JSON text that reports the manifest file path used by the adapter and the manifest contents. A renamed file is written at the build output root, and a nested file is written inside an intermediate directory that is created when needed.

**Test Cases:** `rcb_tests/public_test_cases/feature5_manifest_file_location.json`

```json
{
    "description": "The manifest can be written to a custom file name or to a file inside a newly created nested output directory.",
    "cases": [
        {
            "input": {
                "bundler": "legacy",
                "build": "custom_manifest_location",
                "location": "renamed"
            },
            "expected_output": "{\n  \"manifest_file\": \"new-stats.json\",\n  \"status\": \"done\",\n  \"chunks\": {\n    \"main\": [\n      \"[a specific locally emitted file path that will be relative]\"\n    ]\n  },\n  \"assets\": {\n    \"[a specific locally emitted file path that will be relative]\": {\n      \"name\": \"[a specific locally emitted file path that will be relative]\",\n      \"path\": \"OUTPUT_DIR/[a specific locally emitted file path that will be relative]\",\n      \"publicPath\": \"http://localhost:3000/assets/[a specific locally emitted file path that will be relative]\"\n    }\n  }\n}\n"
        },
        {
            "input": {
                "bundler": "legacy",
                "build": "custom_manifest_location",
                "location": "nested"
            },
            "expected_output": "{\n  \"manifest_file\": \"data/stats.json\",\n  \"status\": \"done\",\n  \"chunks\": {\n    \"main\": [\n      \"[a specific locally emitted file path that will be relative]\"\n    ]\n  },\n  \"assets\": {\n    \"[a specific locally emitted file path that will be relative]\": {\n      \"name\": \"[a specific locally emitted file path that will be relative]\",\n      \"path\": \"OUTPUT_DIR/[a specific locally emitted file path that will be relative]\",\n      \"publicPath\": \"http://localhost:3000/assets/[a specific locally emitted file path that will be relative]\"\n    }\n  }\n}\n"
        }
    ]
}
```

---

### Feature 6: Relative Asset Path Reporting

**As a developer**, I want to request relative filesystem paths in the manifest, so I can move build outputs without embedding absolute local paths.

**Expected Behavior / Usage:**

The input selects a successful one-entry build whose assets are emitted below a nested output root and whose manifest requests relative paths. The output is raw JSON text where each asset path is relative to the emitted asset root while public URLs remain fully formed.

**Test Cases:** `rcb_tests/public_test_cases/feature6_relative_asset_paths.json`

```json
{
    "description": "When relative asset paths are requested, manifest asset path fields are relative to the emitted asset root while URLs remain absolute.",
    "cases": [
        {
            "input": {
                "bundler": "legacy",
                "build": "relative_asset_paths"
            },
            "expected_output": "{\n  \"status\": \"done\",\n  \"chunks\": {\n    \"main\": [\n      \"[a specific locally emitted file path that will be relative]\"\n    ]\n  },\n  \"assets\": {\n    \"[a specific locally emitted file path that will be relative]\": {\n      \"name\": \"[a specific locally emitted file path that will be relative]\",\n      \"path\": \"[a specific locally emitted file path that will be relative]\",\n      \"publicPath\": \"http://localhost:3000/assets/[a specific locally emitted file path that will be relative]\"\n    }\n  }\n}\n"
        }
    ]
}
```

---

### Feature 7: Compilation Error Manifest

**As a developer**, I want to receive a structured manifest when a build canno[the exact substring appearing in the missing module request log]an input dependency, so I can surface build failure details without parsing host-runtime exception text.

**Expected Behavior / Usage:**

The input selects a build whose entry imports a missing dependency. The output is raw JSON text with error status, a language-neutral missing-module error category, and the unresolved request name as a separate field.

**Test Cases:** `rcb_tests/public_test_cases/feature7_compilation_error_manifest.json`

```json
{
    "description": "When the build canno[the exact substring appearing in the missing module request log]an imported module, the manifest reports an error status with a normalized missing-module signal.",
    "cases": [
        {
            "input": {
                "bundler": "legacy",
                "build": "missing_entry_dependency"
            },
            "expected_output": "{\n  \"status\": \"error\",\n  \"error\": \"missing_module\",\n  \"missing_request\": \"[the exact substring appearing in the missing module request log]\"\n}\n"
        }
    ]
}
```

---

### Feature 8: Shared Chunk Membership

**As a developer**, I want to list the files each initial entry needs when entries share modules, so I can load shared files before entry-specific files.

**Expected Behavior / Usage:**

The input selects a multi-entry build in which both initial entries depend on a shared module. The output is raw JSON text with done status, per-entry file lists that include the shared file before each entry file, and asset metadata for each emitted JavaScript file.

**Test Cases:** `rcb_tests/public_test_cases/feature8_split_entry_chunks.json`

```json
{
    "description": "For multiple initial entry points sharing a common module, each entry lists its required shared file before its own entry file and each asset is described.",
    "cases": [
        {
            "input": {
                "bundler": "legacy",
                "build": "split_entry_chunks"
            },
            "expected_output": "{\n  \"status\": \"done\",\n  \"chunks\": {\n    \"app1\": [\n      \"js/commons.js\",\n      \"js/app1.js\"\n    ],\n    \"app2\": [\n      \"js/commons.js\",\n      \"js/app2.js\"\n    ]\n  },\n  \"assets\": {\n    \"js/1.js\": {\n      \"name\": \"js/1.js\",\n      \"path\": \"js/1.js\",\n      \"publicPath\": \"http://localhost:3000/assets/js/1.js\"\n    },\n    \"js/app1.js\": {\n      \"name\": \"js/app1.js\",\n      \"path\": \"js/app1.js\",\n      \"publicPath\": \"http://localhost:3000/assets/js/app1.js\"\n    },\n    \"js/app2.js\": {\n      \"name\": \"js/app2.js\",\n      \"path\": \"js/app2.js\",\n      \"publicPath\": \"http://localhost:3000/assets/js/app2.js\"\n    },\n    \"js/commons.js\": {\n      \"name\": \"js/commons.js\",\n      \"path\": \"js/commons.js\",\n      \"publicPath\": \"http://localhost:3000/assets/js/commons.js\"\n    }\n  }\n}\n"
        }
    ]
}
```

---

### Feature 9: Asset Integrity Metadata

**As a developer**, I want to request integrity data for emitted assets, so I can attach subresource integrity information to every generated file.

**Expected Behavior / Usage:**

The input selects a multi-entry build that emits JavaScript and CSS assets with integrity metadata enabled. The output is raw JSON text containing done status, public base URL, chunk membership, and asset metadata whose integrity field is represented by the ordered set of hash algorithms available for each asset.

**Test Cases:** `rcb_tests/public_test_cases/feature9_integrity_metadata.json`

```json
{
    "description": "When integrity metadata is requested, each emitted asset records the hash algorithm set available for subresource integrity.",
    "cases": [
        {
            "input": {
                "bundler": "legacy",
                "build": "integrity_metadata"
            },
            "expected_output": "{\n  \"status\": \"done\",\n  \"publicPath\": \"http://localhost:3000/assets/\",\n  \"chunks\": {\n    \"app1\": [\n      \"js/commons.js\",\n      \"js/app1.js\"\n    ],\n    \"appWithAssets\": [\n      \"js/commons.js\",\n      \"styles.css\",\n      \"js/appWithAssets.js\"\n    ]\n  },\n  \"assets\": {\n    \"js/1.js\": {\n      \"name\": \"js/1.js\",\n      \"path\": \"js/1.js\",\n      \"publicPath\": \"http://localhost:3000/assets/js/1.js\",\n      \"integrity_algorithms\": [\n        \"sha256\",\n        \"sha384\",\n        \"sha512\"\n      ]\n    },\n    \"js/app1.js\": {\n      \"name\": \"js/app1.js\",\n      \"path\": \"js/app1.js\",\n      \"publicPath\": \"http://localhost:3000/assets/js/app1.js\",\n      \"integrity_algorithms\": [\n        \"sha256\",\n        \"sha384\",\n        \"sha512\"\n      ]\n    },\n    \"js/appWithAssets.js\": {\n      \"name\": \"js/appWithAssets.js\",\n      \"path\": \"js/appWithAssets.js\",\n      \"publicPath\": \"http://localhost:3000/assets/js/appWithAssets.js\",\n      \"integrity_algorithms\": [\n        \"sha256\",\n        \"sha384\",\n        \"sha512\"\n      ]\n    },\n    \"js/commons.js\": {\n      \"name\": \"js/commons.js\",\n      \"path\": \"js/commons.js\",\n      \"publicPath\": \"http://localhost:3000/assets/js/commons.js\",\n      \"integrity_algorithms\": [\n        \"sha256\",\n        \"sha384\",\n        \"sha512\"\n      ]\n    },\n    \"styles.css\": {\n      \"name\": \"styles.css\",\n      \"path\": \"styles.css\",\n      \"publicPath\": \"http://localhost:3000/assets/styles.css\",\n      \"integrity_algorithms\": [\n        \"sha256\",\n        \"sha384\",\n        \"sha512\"\n      ]\n    }\n  }\n}\n"
        }
    ]
}
```

---

### Feature 10: Compressed Asset Variants

**As a developer**, I want to include compressed asset variants in the manifest, so I can serve precompressed JavaScript and CSS files alongside originals.

**Expected Behavior / Usage:**

The input selects a multi-entry build that emits original JavaScript and CSS files plus gzip and Brotli variants. The output is raw JSON text containing done status, entry chunk membership for original files, and asset metadata for each original and compressed emitted file including its public URL.

**Test Cases:** `rcb_tests/public_test_cases/feature10_compressed_assets.json`

```json
{
    "description": "When compressed variants are emitted alongside original files, the manifest includes the original and compressed JavaScript and CSS assets with their public URLs.",
    "cases": [
        {
            "input": {
                "bundler": "legacy",
                "build": "compressed_assets"
            },
            "expected_output": "{\n  \"status\": \"done\",\n  \"chunks\": {\n    \"app1\": [\n      \"js/commons.js\",\n      \"js/app1.js\"\n    ],\n    \"appWithAssets\": [\n      \"js/commons.js\",\n      \"css/appWithAssets.css\",\n      \"js/appWithAssets.js\"\n    ]\n  },\n  \"assets\": {\n    \"css/appWithAssets.css\": {\n      \"name\": \"css/appWithAssets.css\",\n      \"path\": \"css/appWithAssets.css\",\n      \"publicPath\": \"http://localhost:3000/assets/css/appWithAssets.css\"\n    },\n    \"css/appWithAssets.css.br\": {\n      \"name\": \"css/appWithAssets.css.br\",\n      \"path\": \"css/appWithAssets.css.br\",\n      \"publicPath\": \"http://localhost:3000/assets/css/appWithAssets.css.br\"\n    },\n    \"css/appWithAssets.css.gz\": {\n      \"name\": \"css/appWithAssets.css.gz\",\n      \"path\": \"css/appWithAssets.css.gz\",\n      \"publicPath\": \"http://localhost:3000/assets/css/appWithAssets.css.gz\"\n    },\n    \"js/1.js\": {\n      \"name\": \"js/1.js\",\n      \"path\": \"js/1.js\",\n      \"publicPath\": \"http://localhost:3000/assets/js/1.js\"\n    },\n    \"js/1.js.br\": {\n      \"name\": \"js/1.js.br\",\n      \"path\": \"js/1.js.br\",\n      \"publicPath\": \"http://localhost:3000/assets/js/1.js.br\"\n    },\n    \"js/1.js.gz\": {\n      \"name\": \"js/1.js.gz\",\n      \"path\": \"js/1.js.gz\",\n      \"publicPath\": \"http://localhost:3000/assets/js/1.js.gz\"\n    },\n    \"js/app1.js\": {\n      \"name\": \"js/app1.js\",\n      \"path\": \"js/app1.js\",\n      \"publicPath\": \"http://localhost:3000/assets/js/app1.js\"\n    },\n    \"js/app1.js.br\": {\n      \"name\": \"js/app1.js.br\",\n      \"path\": \"js/app1.js.br\",\n      \"publicPath\": \"http://localhost:3000/assets/js/app1.js.br\"\n    },\n    \"js/app1.js.gz\": {\n      \"name\": \"js/app1.js.gz\",\n      \"path\": \"js/app1.js.gz\",\n      \"publicPath\": \"http://localhost:3000/assets/js/app1.js.gz\"\n    },\n    \"js/appWithAssets.js\": {\n      \"name\": \"js/appWithAssets.js\",\n      \"path\": \"js/appWithAssets.js\",\n      \"publicPath\": \"http://localhost:3000/assets/js/appWithAssets.js\"\n    },\n    \"js/appWithAssets.js.br\": {\n      \"name\": \"js/appWithAssets.js.br\",\n      \"path\": \"js/appWithAssets.js.br\",\n      \"publicPath\": \"http://localhost:3000/assets/js/appWithAssets.js.br\"\n    },\n    \"js/appWithAssets.js.gz\": {\n      \"name\": \"js/appWithAssets.js.gz\",\n      \"path\": \"js/appWithAssets.js.gz\",\n      \"publicPath\": \"http://localhost:3000/assets/js/appWithAssets.js.gz\"\n    },\n    \"js/commons.js\": {\n      \"name\": \"js/commons.js\",\n      \"path\": \"js/commons.js\",\n      \"publicPath\": \"http://localhost:3000/assets/js/commons.js\"\n    },\n    \"js/commons.js.br\": {\n      \"name\": \"js/commons.js.br\",\n      \"path\": \"js/commons.js.br\",\n      \"publicPath\": \"http://localhost:3000/assets/js/commons.js.br\"\n    },\n    \"js/commons.js.gz\": {\n      \"name\": \"js/commons.js.gz\",\n      \"path\": \"js/commons.js.gz\",\n      \"publicPath\": \"http://localhost:3000/assets/js/commons.js.gz\"\n    }\n  }\n}\n"
        }
    ]
}
```

---

### Feature 11: Repeated Build Chunk Refresh

**As a developer**, I want to refresh manifest chunk membership after consecutive builds, so I can avoid stale shared-file references when source dependencies change.

**Expected Behavior / Usage:**

The input selects a repeated build where the first run has one entry depending on a shared module and a second run removes that dependency. The output is raw JSON text showing done status and the refreshed chunks object after the second run, with the changed entry no longer listing the shared file.

**Test Cases:** `rcb_tests/public_test_cases/feature11_repeated_build_chunk_refresh.json`

```json
{
    "description": "After a repeated build changes one entry so it no longer imports the shared module, the manifest refreshes chunk membership instead of retaining stale shared files.",
    "cases": [
        {
            "input": {
                "bundler": "legacy",
                "build": "repeat_build_updates_chunks"
            },
            "expected_output": "{\n  \"status\": \"compile\",\n  \"chunks\": {}\n}\n"
        }
    ]
}
```

---

### Feature 12: Deterministic Manifest Key Order

**As a developer**, I want to emit manifest object keys in alphabetical order, so I can produce stable manifest diffs and deterministic downstream processing.

**Expected Behavior / Usage:**

The input selects a multi-entry build that emits multiple assets and entry chunk groups. The output is raw JSON text listing the observed asset key order and chunk key order; both lists are alphabetically ordered according to the generated manifest.

**Test Cases:** `rcb_tests/public_test_cases/feature12_alphabetical_manifest_order.json`

```json
{
    "description": "Manifest object keys for assets and entry chunks are emitted in alphabetical order.",
    "cases": [
        {
            "input": {
                "bundler": "legacy",
                "build": "alphabetical_manifest_order"
            },
            "expected_output": "{\n  \"asset_key_order\": [\n    \"css/appA.css\",\n    \"js/1.js\",\n    \"js/appA.js\",\n    \"js/appZ.js\",\n    \"js/commons.js\"\n  ],\n  \"chunk_key_order\": [\n    \"appA\",\n    \"appZ\"\n  ]\n}\n"
        }
    ]
}
```

---

### Feature 13: Automatic Public URL Preservation

**As a developer**, I want to preserve an automatic public URL mode in the manifest, so I can let the runtime decide asset loading paths while still exposing manifest metadata.

**Expected Behavior / Usage:**

The input selects a successful one-entry build whose public URL mode is automatic. The output is raw JSON text with done status, an automatic marker as the manifest-level public path, and the same automatic marker for the asset public URL.

**Test Cases:** `rcb_tests/public_test_cases/feature13_automatic_public_url.json`

```json
{
    "description": "When the bundler public URL mode is automatic, the manifest preserves the automatic marker for the manifest base and asset URL.",
    "cases": [
        {
            "input": {
                "bundler": "legacy",
                "build": "automatic_public_url_manifest"
            },
            "expected_output": "{\n  \"status\": \"done\",\n  \"publicPath\": \"auto\",\n  \"chunks\": {\n    \"main\": [\n      \"[a specific locally emitted file path that will be relative]\"\n    ]\n  },\n  \"assets\": {\n    \"[a specific locally emitted file path that will be relative]\": {\n      \"name\": \"[a specific locally emitted file path that will be relative]\",\n      \"path\": \"OUTPUT_DIR/[a specific locally emitted file path that will be relative]\",\n      \"publicPath\": \"auto\"\n    }\n  }\n}\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- emit the same relative path as the entry point generated by the legacy bundler configuration
- use the exact unformatted prefix found in the parser logs when resolving missing imports
