## Product Requirement Document

# Dependency Patch Management Toolkit - Declarative Patching for Installed Packages

## Project Goal

Build a library and plugin that lets developers declare source-code patches for the third-party packages their project depends on, and have those patches resolved, de-duplicated, downloaded, verified, and applied automatically as part of the normal dependency install/update workflow. Developers declare *what* to patch and *where the patch lives*; the toolkit handles the bookkeeping of *how* it is collected, fetched, hashed, and rolled out.

---

## Background & Problem

Third-party dependencies frequently contain bugs or missing features that a project needs fixed *before* an upstream release is available. Without a patching toolkit, developers are forced to fork the dependency, vendor a modified copy, or manually re-apply hand-maintained diffs after every install/update — all of which are error-prone, easy to forget, and painful to keep in sync across a team and across CI.

With this toolkit, a project lists its patches declaratively (either inline in the project configuration or in a dedicated patches file). The toolkit gathers every declaration from all sources into a single collection keyed by target package, removes duplicates, fetches each patch from its source (local path or remote URL), verifies the downloaded content against an expected hash, decides the correct strip depth for applying the diff, and records everything in a lock file so the exact same patches are reproduced on every machine. This turns a fragile manual ritual into a repeatable, verifiable, declarative step.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This is a multi-responsibility system (patch records, collections, source resolvers, downloaders, depth resolution, patchers, lock-file naming), so it MUST be organized as a clear multi-file tree (e.g. core domain types, source resolvers, downloaders, patchers, and a thin execution adapter) rather than a single "god file". Do not over-engineer, but do not collapse distinct responsibilities together.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in "Core Features" are a **black-box contract for the execution adapter**, NOT the internal data model. The core domain (patch records, collections, resolvers, depth logic, downloaders, patchers) must be completely decoupled from stdin/stdout and JSON parsing. A separate execution adapter is solely responsible for translating JSON commands into idiomatic calls into the core and for rendering results (and normalized errors) to stdout.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Keep parsing, source resolution, downloading, depth resolution, patch application, and output formatting in distinct units.
   - **Open/Closed Principle (OCP):** New patch sources, downloaders, and patchers must be addable without modifying the core engine.
   - **Liskov Substitution Principle (LSP):** Every concrete resolver / downloader / patcher must be substitutable for its abstraction.
   - **Interface Segregation Principle (ISP):** Keep the resolver / downloader / patcher contracts small and cohesive.
   - **Dependency Inversion Principle (DIP):** High-level orchestration depends on abstractions for sources, downloaders, and patchers — not on concrete I/O.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public API of the core must be elegant and idiomatic to the target language.
   - **Resilience:** Edge cases must be handled gracefully. Failures (malformed declarations, missing patch keys, content-hash mismatches, unavailable tooling) must be modeled as explicit, typed error conditions rather than generic faults.

---

## Core Features

### Feature 1: Patch Records

**As a developer**, I want each patch to be a self-describing record that survives a serialization round trip, so I can persist patches to a lock file and reload them with no loss of information.

**Expected Behavior / Usage:**

A patch record carries a target package name, a human-readable description, and a source URL (which may be a local path or a remote address). It also carries optional fields: a content hash (sha256), an apply depth, and an `extra` metadata map. Serializing a record to its wire form and parsing that wire form back must reproduce an identical record. Optional fields that were never set appear as `null` in the wire form and remain unset after the round trip; the `extra` map defaults to an empty object when absent. The command echoes each field of a record that was reconstructed from its own serialized wire form.

**Test Cases:** `rcb_tests/public_test_cases/feature1_patch_serialization.json`

```json
{
    "description": "A patch record carries a target package name, a human description, a source URL, and optional fields (content hash, apply depth, and an extra metadata map). Serializing a record to its wire form and parsing it back yields an identical record. Unset optional fields appear as null in the wire form and remain unset after a round trip; the extra map defaults to an empty object. The output lists each field of the record reconstructed from its own serialized wire form.",
    "cases": [
        {
            "input": {
                "op": "patch_wire",
                "patch": {
                    "package": "drupal/drupal",
                    "url": "https://google.com",
                    "description": "Test description",
                    "depth": 0,
                    "sha256": "asdf",
                    "extra": []
                }
            },
            "expected_output": "package=drupal/drupal\ndescription=Test description\nurl=https://google.com\nsha256=asdf\ndepth=0\nextra=[]\n"
        },
        {
            "input": {
                "op": "patch_wire",
                "patch": {
                    "package": "some/package",
                    "url": "https://example.com/x.patch",
                    "description": "only required fields"
                }
            },
            "expected_output": "package=some/package\ndescription=only required fields\nurl=https://example.com/x.patch\nsha256=null\ndepth=null\nextra=[]\n"
        }
    ]
}
```

---

### Feature 2: Patch Collection

**As a developer**, I want patches gathered into a single collection keyed by target package, with duplicates removed and the whole collection serializable, so the same patch is never applied twice and the full set can be persisted and reloaded.

**Expected Behavior / Usage:**

*2.1 Grouping & Lifecycle — adding, counting, listing, and removing patches by package*

Patches added to a collection are grouped by their target package. Querying a package returns the number of patches stored for it; the collection can list every package that currently has at least one patch, in the order packages were first seen. Removing a package drops all of its patches at once and leaves other packages untouched. The command reports per-package counts and the list of patched packages both before and after a removal.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_collection_grouping.json`

```json
{
    "description": "Patches are added to a collection and grouped by their target package. Querying a package returns the count of patches stored for it, and the collection can list every package that currently has patches in insertion order. Removing a package drops all of its patches at once, leaving other packages untouched. The output reports per-package counts and the list of patched packages before and after a removal.",
    "cases": [
        {
            "input": {
                "op": "collection_lifecycle",
                "add": [
                    {"package": "some/package", "description": "patch1", "url": "1"},
                    {"package": "some/package", "description": "patch2", "url": "2"},
                    {"package": "other/package", "description": "patch3", "url": "3"},
                    {"package": "other/package", "description": "patch4", "url": "4"}
                ],
                "clear": ["other/package"]
            },
            "expected_output": "some/package patches=2\nother/package patches=2\npatched_packages=some/package,other/package\ncleared=other/package\nother/package patches=0\npatched_packages=some/package\n"
        }
    ]
}
```

*2.2 De-duplication — collapsing colliding patches, earliest wins*

When two patches for the same package would collide, the collection keeps only the first one and discards later duplicates. Two patches collide when they share the same source URL, **or** when they share the same content hash even if their URLs differ (for example, one URL carries a fragment suffix). The command reports the surviving patch count for the package and the descriptions that remain, demonstrating that the earliest-added patch wins.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_collection_deduplication.json`

```json
{
    "description": "When two patches for the same package would collide, the collection keeps only the first and discards later duplicates. Two patches collide when they share the same source URL, or when they share the same content hash even if their URLs differ (for example one carries a URL fragment). The output shows the surviving patch count for the package and the descriptions that remain, demonstrating that the earliest-added patch wins.",
    "cases": [
        {
            "input": {
                "op": "collection_dedupe",
                "add": [
                    {"package": "some/package", "description": "patch1", "url": "https://example.com"},
                    {"package": "some/package", "description": "patch2", "url": "https://example.com"}
                ]
            },
            "expected_output": "some/package patches=1\nsome/package descriptions=patch1\n"
        },
        {
            "input": {
                "op": "collection_dedupe",
                "add": [
                    {"package": "some/package", "description": "patch1", "url": "https://example.com", "sha256": "asdf"},
                    {"package": "some/package", "description": "patch2", "url": "https://example.com#something-different", "sha256": "asdf"}
                ]
            },
            "expected_output": "some/package patches=1\nsome/package descriptions=patch1\n"
        }
    ]
}
```

*2.3 Collection Serialization — round trip of the full collection*

A whole collection can be serialized to a wire form that nests, under each target package, the full record of every patch (including `null` placeholders for unset optional fields and an empty `extra` map). Parsing that wire form back reproduces an equivalent collection. The command outputs the canonical wire form of a collection rebuilt from its own serialization, grouping patches under their package names.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_collection_serialization.json`

```json
{
    "description": "A whole collection can be serialized to a wire form that nests, under each target package, the full record of every patch (including null placeholders for unset optional fields and an empty extra map). Parsing that wire form back reproduces an equivalent collection. The output is the canonical wire form of a collection rebuilt from its own serialization, grouping patches under their package names.",
    "cases": [
        {
            "input": {
                "op": "collection_wire",
                "add": [
                    {"package": "some/package", "description": "patch1", "url": "https://example.com/test.patch", "extra": []},
                    {"package": "another/package", "description": "patch2", "url": "https://example.com/test2.patch", "extra": []}
                ]
            },
            "expected_output": "{\n    \"patches\": {\n        \"some/package\": [\n            {\n                \"package\": \"some/package\",\n                \"description\": \"patch1\",\n                \"url\": \"https://example.com/test.patch\",\n                \"sha256\": null,\n                \"depth\": null,\n                \"extra\": []\n            }\n        ],\n        \"another/package\": [\n            {\n                \"package\": \"another/package\",\n                \"description\": \"patch2\",\n                \"url\": \"https://example.com/test2.patch\",\n                \"sha256\": null,\n                \"depth\": null,\n                \"extra\": []\n            }\n        ]\n    }\n}\n"
        }
    ]
}
```

---

### Feature 3: Patch Depth Resolution

**As a developer**, I want the toolkit to determine the correct strip depth for each patch automatically, so most patches apply correctly without me having to specify a depth by hand.

**Expected Behavior / Usage:**

*3.1 Built-in Default Depths — per-package known defaults*

Certain well-known packages have a built-in default apply depth that is used when a patch does not specify its own depth. Looking up a package returns its known default depth, or a `null` result for any package that is not in the built-in list. The command echoes the queried package and the resolved default depth.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_default_depth.json`

```json
{
    "description": "Certain well-known packages have a built-in default apply depth that is used when a patch does not specify its own depth. Looking up a package returns its known default depth, or a null result for any package that is not in the built-in list. The output echoes the queried package and the resolved default depth.",
    "cases": [
        {
            "input": {"op": "default_depth", "package": "drupal/core"},
            "expected_output": "package=drupal/core\ndepth=2\n"
        },
        {
            "input": {"op": "default_depth", "package": "not-a-real-package"},
            "expected_output": "package=not-a-real-package\ndepth=null\n"
        }
    ]
}
```

*3.2 Depth Precedence — resolving the effective depth through a chain*

The effective apply depth for a patch is resolved through a precedence chain: an explicit depth set on the patch itself wins first; otherwise a per-package override declared in the project configuration is used; otherwise the built-in default for well-known packages applies; otherwise the global default depth of `1` is used. The command echoes the patch's target package (or `null` when the patch names no package) together with the resolved depth.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_depth_precedence.json`

```json
{
    "description": "The effective apply depth for a patch is resolved through a precedence chain: an explicit depth on the patch itself wins first; otherwise a per-package override from the project configuration is used; otherwise a built-in default for well-known packages applies; otherwise the global default depth of 1 is used. The output echoes the patch's target package (or null when the patch names no package) and the resolved depth.",
    "cases": [
        {
            "input": {"op": "guess_depth", "patch": {"package": "some/package"}},
            "expected_output": "package=some/package\ndepth=1\n"
        },
        {
            "input": {"op": "guess_depth", "patch": {"depth": 123}},
            "expected_output": "package=null\ndepth=123\n"
        },
        {
            "input": {"op": "guess_depth", "patch": {"package": "drupal/core"}},
            "expected_output": "package=drupal/core\ndepth=2\n"
        },
        {
            "input": {"op": "guess_depth", "patch": {"package": "some/package"}, "project_config": {"package-depths": {"some/package": 234}}},
            "expected_output": "package=some/package\ndepth=234\n"
        }
    ]
}
```

---

### Feature 4: Patch Source Resolution

**As a developer**, I want to declare patches either inline in my project configuration or in a dedicated patches file, so I can choose the style that fits my project and still get one unified collection.

**Expected Behavior / Usage:**

*4.1 Root Configuration Source — patches declared inline*

Patches may be declared inline in the root project configuration as a per-package map. Each package may use the **expanded form** (a list of objects, each with `url` and `description`) or the **compact form** (a description-to-url map). Resolving the configuration produces a collection grouping the declared patches by package; an empty declaration yields no patches. The command reports per-package patch counts and the list of patched packages.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_root_config_patches.json`

```json
{
    "description": "Patches can be declared directly in the root project configuration under a per-package map. Each package may use the expanded form (a list of objects with url and description) or the compact form (a description-to-url map). Resolving the configuration produces a collection grouping the declared patches by package. An empty declaration yields no patches. The output reports per-package patch counts and the list of patched packages.",
    "cases": [
        {
            "input": {"op": "resolve_root", "patches": []},
            "expected_output": "patched_packages=\n"
        },
        {
            "input": {"op": "resolve_root", "patches": {"test/package": [{"url": "https://drupal.org", "description": "Test patch"}]}},
            "expected_output": "test/package patches=1\npatched_packages=test/package\n"
        },
        {
            "input": {"op": "resolve_root", "patches": {"test/package": {"Test patch": "https://drupal.org"}}},
            "expected_output": "test/package patches=1\npatched_packages=test/package\n"
        }
    ]
}
```

*4.2 Patches File Source — patches declared in an external file, with error handling*

Patches may also be declared in an external patches file referenced by the project. A valid file groups patches by package under a top-level `patches` key and resolves to a collection with the expected per-package counts. A file whose JSON parses but contains no `patches` key is rejected with a normalized `no_patches_found` error; a file with malformed JSON is rejected with a normalized `invalid_json` error. A path that does not exist, or an unconfigured (empty) path, is silently ignored and adds nothing (no error). The command reports either the normalized error category, or the per-package counts and patched-package list.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_patches_file.json`

```json
{
    "description": "Patches can also be declared in an external patches file referenced by the project. A valid file groups patches by package and resolves to a collection with the expected per-package counts. A file whose JSON parses but contains no patches key is rejected with a no_patches_found error; a file with malformed JSON is rejected with an invalid_json error. A file path that does not exist, or an unconfigured (empty) path, is silently ignored and adds nothing. The output reports either the normalized error category or the per-package counts and patched-package list.",
    "cases": [
        {
            "input": {"op": "resolve_file", "patches_file_content": "{\"patches\":{\"test/package\":[{\"url\":\"https://drupal.org\",\"description\":\"Test patch\"},{\"url\":\"https://drupal.org/foo\",\"description\":\"Test patch\"}],\"test/package2\":[{\"url\":\"https://drupal.org/bar\",\"description\":\"Test patch\"},{\"url\":\"https://drupal.org/baz\",\"description\":\"Test patch\"}]}}"},
            "expected_output": "test/package patches=2\ntest/package2 patches=2\npatched_packages=test/package,test/package2\n"
        },
        {
            "input": {"op": "resolve_file", "patches_file_content": "{}"},
            "expected_output": "error=no_patches_found\n"
        },
        {
            "input": {"op": "resolve_file", "patches_file_content": "{\"patches\":{\"test/package\":[{\"url\":\"x\"}],}}"},
            "expected_output": "error=invalid_json\n"
        },
        {
            "input": {"op": "resolve_file", "patches_file_missing": true},
            "expected_output": "patched_packages=\n"
        },
        {
            "input": {"op": "resolve_file"},
            "expected_output": "patched_packages=\n"
        }
    ]
}
```

---

### Feature 5: Lock File Naming

**As a developer**, I want the patches lock file to be named after my active project manifest, so projects that use a custom manifest name get a correspondingly named lock file and never clash.

**Expected Behavior / Usage:**

The patches lock file is named after the active project manifest. With the default manifest the lock file is named `patches.lock.json`. When the active manifest is overridden to a custom name, the lock file name is derived by taking that manifest's base name and appending `-patches.lock.json`. The command reports the resolved lock file name.

**Test Cases:** `rcb_tests/public_test_cases/feature5_lock_file_name.json`

```json
{
    "description": "The patches lock file is named after the active project manifest. With the default manifest the lock file is named patches.lock.json; when the active manifest is overridden to a custom name, the lock file name is derived by appending -patches.lock.json to that manifest's base name. The output reports the resolved lock file name.",
    "cases": [
        {
            "input": {"op": "lock_file_path"},
            "expected_output": "lock_file=patches.lock.json\n"
        },
        {
            "input": {"op": "lock_file_path", "manifest_env": "mycomposer.json"},
            "expected_output": "lock_file=mycomposer-patches.lock.json\n"
        }
    ]
}
```

---

### Feature 6: Patch Download & Hash Verification

**As a developer**, I want each patch fetched into a working location and verified against an expected content hash, so a tampered or wrong patch is rejected before it can be applied.

**Expected Behavior / Usage:**

A patch is fetched from its source (here a local source) into a working location, and its content hash (sha256) is computed. When no expected hash is supplied, the computed hash is recorded and the local copy is reported as available. When an expected hash is supplied and matches the actual content, the fetch succeeds. When the expected hash does **not** match the actual content, the operation fails with a normalized `hash_mismatch` error that reports both the expected and the actual hash on separate fields. The command outputs either the computed hash plus a local-file-availability line, or the normalized mismatch error with both hashes.

**Test Cases:** `rcb_tests/public_test_cases/feature6_download_and_verify.json`

```json
{
    "description": "A patch is fetched from a local source into a working location, and its content hash (sha256) is computed. When no expected hash is supplied, the computed hash is recorded and the local copy is available. When an expected hash is supplied and matches, the fetch succeeds. When the expected hash does not match the actual content, the operation fails with a normalized hash_mismatch error reporting the expected and actual hashes. The output reports either the computed hash and local-file availability, or the normalized mismatch error with both hashes.",
    "cases": [
        {
            "input": {"op": "download_local", "file_content": "patch contents for testing\n"},
            "expected_output": "sha256=cff1242bc66dfa824db407ff0c08ec1fe13c7065b9e83ea27e1a7a821d9db58c\nlocal_file=present\n"
        },
        {
            "input": {"op": "download_local", "file_content": "patch contents for testing\n", "expected_sha256": "cff1242bc66dfa824db407ff0c08ec1fe13c7065b9e83ea27e1a7a821d9db58c"},
            "expected_output": "sha256=cff1242bc66dfa824db407ff0c08ec1fe13c7065b9e83ea27e1a7a821d9db58c\nlocal_file=present\n"
        },
        {
            "input": {"op": "download_local", "file_content": "patch contents for testing\n", "expected_sha256": "an incorrect hash"},
            "expected_output": "error=hash_mismatch\nexpected=an incorrect hash\nactual=cff1242bc66dfa824db407ff0c08ec1fe13c7065b9e83ea27e1a7a821d9db58c\n"
        }
    ]
}
```

---

### Feature 7: Patcher Availability

**As a developer**, I want each patch-applying backend to report whether it can run in the current environment, so the toolkit can skip backends whose required tooling is missing or broken and only attempt ones that work.

**Expected Behavior / Usage:**

A patcher reports whether it can be used in the current environment by probing its backing command-line tool. The patcher is available only when the tool is present and runs successfully; it is unavailable when the configured tool path points to a missing executable or to a tool that exits with a failure. The command reports the tool name and whether it is available.

**Test Cases:** `rcb_tests/public_test_cases/feature7_patcher_availability.json`

```json
{
    "description": "A patcher reports whether it can be used in the current environment by probing its backing tool. The patcher is available only when the tool is present and runs successfully; it is unavailable when the configured tool path points to a missing executable or to a tool that exits with a failure. The output reports the tool name and whether it is available.",
    "cases": [
        {
            "input": {"op": "patcher_availability", "tool_state": "working"},
            "expected_output": "tool=git\navailable=true\n"
        },
        {
            "input": {"op": "patcher_availability", "tool_state": "broken"},
            "expected_output": "tool=git\navailable=false\n"
        },
        {
            "input": {"op": "patcher_availability", "tool_state": "missing"},
            "expected_output": "tool=git\navailable=false\n"
        },
        {
            "input": {"op": "patcher_availability", "tool_state": "system_default"},
            "expected_output": "tool=git\navailable=true\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the features above — patch records, the collection with grouping/de-duplication/serialization, depth resolution, the inline and file-based source resolvers, lock-file naming, the downloader with hash verification, and the availability-probing patcher abstraction. The core domain must be decoupled from stdin/stdout and JSON.

2. **The Execution/Test Adapter:** A runnable entry point that reads a single JSON command from stdin, dispatches it to the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. The adapter is the only place where native errors are caught and translated into the normalized, language-neutral `error=<category>` lines (e.g. `no_patches_found`, `invalid_json`, `hash_mismatch`); the core may raise idiomatic typed errors, but their language identity must never reach stdout. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to select the directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_patch_serialization.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_patch_serialization@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the sequence returned by the collector_aggregator utility before the sort step
