## Product Requirement Document

# Translation Catalog Runtime - Locale Catalog Loading and Text Resolution

## Project Goal

Build a translation catalog runtime that allows developers to load localized text resources, resolve nested and plural translation keys, and render translated text without hand-writing repetitive catalog parsing and lookup code.

---

## Background & Problem

Without this library/tool, developers are forced to manually choose locale files, decode multiple text formats, merge fallback translations, traverse nested maps, implement plural-key selection, and keep UI text synchronized with locale refreshes. This leads to repetitive code, inconsistent fallback behavior, and difficult-to-test localization defects.

With this library/tool, applications can use a single catalog-loading and text-resolution layer that accepts locale-oriented inputs and produces predictable decoded maps or visible translated text.

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
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project size):
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

### Feature 1: Single Catalog Loading

**As a developer**, I want to load a single locale catalog from supported text formats and locale identifiers, so I can display translated content from one catalog without manual file selection.

**Expected Behavior / Usage:**

The input names a flat catalog operation, a source format, and optionally a locale or country-code preference. The output is the decoded catalog as `map=<pretty JSON>` with stable keys that reveal the selected catalog identifier, the decoder format used, and nested translation entries. If the active locale cannot be loaded, the configured fallback catalog is used; if both active and fallback catalogs are unavailable, the output map is empty.

**Test Cases:** `rcb_tests/public_test_cases/feature1_flat_catalog_loading.json`

```json
{
    "description": "Loads a single translation catalog and reports the selected catalog identifier, parsed format, and nested entries.",
    "cases": [
        {
            "input": {
                "feature": "flat_catalog",
                "format": "json"
            },
            "expected_output": "map={\n  \"keySingle\": \"valueSingle\",\n  \"keyPlural-1\": \"valuePlural-1\",\n  \"keyPlural-2\": \"valuePlural-2\",\n  \"fileName\": \"en\",\n  \"extension\": \"json\",\n  \"object\": {\n    \"key1\": \"Key1Value\",\n    \"key2\": \"Key2Value\"\n  }\n}\n"
        },
        {
            "input": {
                "feature": "flat_catalog",
                "format": "yaml"
            },
            "expected_output": "map={\n  \"keySingle\": \"valueSingle\",\n  \"keyPlural-1\": \"valuePlural-1\",\n  \"keyPlural-2\": \"valuePlural-2\",\n  \"fileName\": \"en\",\n  \"extension\": \"yaml\",\n  \"object\": {\n    \"key1\": \"Key1Value\",\n    \"key2\": \"Key2Value\"\n  }\n}\n"
        },
        {
            "input": {
                "feature": "flat_catalog",
                "format": "json",
                "includeCountry": true
            },
            "expected_output": "map={\n  \"keySingle\": \"valueSingle\",\n  \"keyPlural-1\": \"valuePlural-1\",\n  \"keyPlural-2\": \"valuePlural-2\",\n  \"fileName\": \"en_US\",\n  \"extension\": \"json\",\n  \"object\": {\n    \"key1\": \"Key1Value\",\n    \"key2\": \"Key2Value\"\n  }\n}\n"
        },
        {
            "input": {
                "feature": "flat_catalog",
                "format": "json",
                "locale": "_en"
            },
            "expected_output": "map={\n  \"keySingle\": \"valueSingle\",\n  \"keyPlural-1\": \"valuePlural-1\",\n  \"keyPlural-2\": \"valuePlural-2\",\n  \"fileName\": \"en\",\n  \"extension\": \"json\",\n  \"object\": {\n    \"key1\": \"Key1Value\",\n    \"key2\": \"Key2Value\"\n  }\n}\n"
        }
    ]
}
```

---

### Feature 2: Fallback Deep Merge

**As a developer**, I want to combine an active catalog with fallback content, so I can keep localized overrides while preserving untranslated fallback values.

**Expected Behavior / Usage:**

The input names an active locale and a fallback locale for one catalog. The output is a merged map: active values replace fallback values at the same leaf, nested maps are merged recursively, and fallback-only leaves remain present.

**Test Cases:** `rcb_tests/public_test_cases/feature2_fallback_deep_merge.json`

```json
{
    "description": "Merges a fallback catalog with the active catalog so active leaf values override fallback leaves while missing fallback leaves remain available.",
    "cases": [
        {
            "input": {
                "feature": "flat_catalog",
                "source": "fallback_merge_asset",
                "locale": "fr",
                "fallback": "en"
            },
            "expected_output": "map={\n  \"title\": \"flutter_18n_fr\",\n  \"sub_title\": \"Hello World\",\n  \"block\": {\n    \"label1\": \"This is my app\",\n    \"label2\": \"Bonjour\"\n  }\n}\n"
        }
    ]
}
```

---

### Feature 3: Namespaced Catalog Loading

**As a developer**, I want to load independent catalog groups by namespace, so I can organize translations into separate domains without losing group boundaries.

**Expected Behavior / Usage:**

The input provides a non-empty namespace list plus optional locale and country-code settings. The output is a top-level map with one entry per namespace. Each namespace value is the decoded catalog for that namespace and includes observable catalog identifier and decoder-format fields, proving that each namespace was loaded independently.

**Test Cases:** `rcb_tests/public_test_cases/feature3_namespaced_catalog_loading.json`

```json
{
    "description": "Loads one or more named catalog groups and preserves each group under its own top-level namespace.",
    "cases": [
        {
            "input": {
                "feature": "namespaced_catalog",
                "namespaces": [
                    "common"
                ]
            },
            "expected_output": "map={\n  \"common\": {\n    \"keySingle\": \"valueSingle\",\n    \"keyPlural-1\": \"valuePlural-1\",\n    \"keyPlural-2\": \"valuePlural-2\",\n    \"fileName\": \"en/common\",\n    \"extension\": \"json\",\n    \"object\": {\n      \"key1\": \"Key1Value\",\n      \"key2\": \"Key2Value\"\n    }\n  }\n}\n"
        },
        {
            "input": {
                "feature": "namespaced_catalog",
                "namespaces": [
                    "common"
                ],
                "includeCountry": true
            },
            "expected_output": "map={\n  \"common\": {\n    \"keySingle\": \"valueSingle\",\n    \"keyPlural-1\": \"valuePlural-1\",\n    \"keyPlural-2\": \"valuePlural-2\",\n    \"fileName\": \"en_US/common\",\n    \"extension\": \"json\",\n    \"object\": {\n      \"key1\": \"Key1Value\",\n      \"key2\": \"Key2Value\"\n    }\n  }\n}\n"
        },
        {
            "input": {
                "feature": "namespaced_catalog",
                "namespaces": [
                    "ns1",
                    "ns2"
                ]
            },
            "expected_output": "map={\n  \"ns1\": {\n    \"keySingle\": \"valueSingle\",\n    \"keyPlural-1\": \"valuePlural-1\",\n    \"keyPlural-2\": \"valuePlural-2\",\n    \"fileName\": \"en/ns1\",\n    \"extension\": \"json\",\n    \"object\": {\n      \"key1\": \"Key1Value\",\n      \"key2\": \"Key2Value\"\n    }\n  },\n  \"ns2\": {\n    \"keySingle\": \"valueSingle\",\n    \"keyPlural-1\": \"valuePlural-1\",\n    \"keyPlural-2\": \"valuePlural-2\",\n    \"fileName\": \"en/ns2\",\n    \"extension\": \"json\",\n    \"object\": {\n      \"key1\": \"Key1Value\",\n      \"key2\": \"Key2Value\"\n    }\n  }\n}\n"
        }
    ]
}
```

---

### Feature 4: Namespace Input Validation

**As a developer**, I want to reject absent or empty namespace selections, so I can fail fast before attempting a grouped catalog load.

**Expected Behavior / Usage:**

The input names a grouped-catalog operation with an invalid namespace list. The output is the normalized error `error=invalid_namespaces`, with no host-language assertion or runtime exception text.

**Test Cases:** `rcb_tests/public_test_cases/feature4_namespace_validation.json`

```json
{
    "description": "Rejects missing or empty namespace lists before attempting to load grouped catalogs.",
    "cases": [
        {
            "input": {
                "feature": "namespaced_catalog",
                "namespaces": []
            },
            "expected_output": "error=invalid_namespaces\n"
        }
    ]
}
```

---

### Feature 5: Remote Catalog Loading

**As a developer**, I want to load translation content from a remote source abstraction, so I can use externally provided catalog content through the same decode path as local files.

**Expected Behavior / Usage:**

The input requests a remote-source catalog. The output is the decoded catalog map from the remote content, using the same `map=<pretty JSON>` stdout shape as local catalog loading.

**Test Cases:** `rcb_tests/public_test_cases/feature5_remote_catalog_loading.json`

```json
{
    "description": "Loads a catalog through a remote-source loader and decodes the returned content into the same map output shape as local catalogs.",
    "cases": [
        {
            "input": {
                "feature": "remote_catalog"
            },
            "expected_output": "map={}\n"
        }
    ]
}
```

---

### Feature 6: Nested Key Lookup

**As a developer**, I want to resolve dotted translation keys against a decoded catalog, so I can retrieve string translations and observe missing-key behavior.

**Expected Behavior / Usage:**

The input provides a decoded catalog, a lookup key, and a key separator. The output prints `translation=<value>` followed by `missing_keys=<JSON array>`. String leaves return their value. Missing keys or keys that resolve to non-string values return the requested key and report the missing key in the callback array.

**Test Cases:** `rcb_tests/public_test_cases/feature6_key_lookup.json`

```json
{
    "description": "Looks up dotted keys in a decoded catalog, returns string leaves, and reports missing-key callbacks without replacing missing values with booleans.",
    "cases": [
        {
            "input": {
                "feature": "lookup",
                "catalog": {
                    "object": {
                        "key1": "value1"
                    }
                },
                "key": "object.key1",
                "separator": "."
            },
            "expected_output": "translation=value1\nmissing_keys=[]\n"
        }
    ]
}
```

---

### Feature 7: Parent Submap Calculation

**As a developer**, I want to calculate the parent map used by nested key resolution, so I can reason about where a leaf lookup is performed.

**Expected Behavior / Usage:**

The input provides a decoded catalog, a lookup path, and a separator. The output prints `submap=<pretty JSON>` for the parent object of the final key segment. Empty paths and paths that cross a non-map value produce an empty map.

**Test Cases:** `rcb_tests/public_test_cases/feature7_submap_calculation.json`

```json
{
    "description": "Calculates the parent map used for a nested lookup and returns an empty map when the path is empty or crosses a non-map value.",
    "cases": [
        {
            "input": {
                "feature": "submap",
                "catalog": {
                    "object": {
                        "key1": "value1"
                    }
                },
                "key": "object.key1",
                "path": "object.key1",
                "separator": "."
            },
            "expected_output": "submap={\n  \"key1\": \"value1\"\n}\n"
        }
    ]
}
```

---

### Feature 8: Plural Key Resolution

**As a developer**, I want to select plural translations from numeric suffixes, so I can show count-specific text without manual branching.

**Expected Behavior / Usage:**

The input provides a catalog with pluralized key variants, a base key, a count, and a separator. The output prints the selected translation and a missing-key callback array. The selected variant is the suffix appropriate for the requested count as exercised by the original rendering behavior.

**Test Cases:** `rcb_tests/public_test_cases/feature8_plural_lookup.json`

```json
{
    "description": "Selects the pluralized translation key whose numeric suffix matches the requested count as exercised by translated text rendering.",
    "cases": [
        {
            "input": {
                "feature": "plural",
                "catalog": {
                    "keyPlural-1": "valuePlural-1",
                    "keyPlural-2": "valuePlural-2"
                },
                "key": "keyPlural",
                "count": 1,
                "separator": "."
            },
            "expected_output": "translation=valuePlural-1\nmissing_keys=[]\n"
        }
    ]
}
```

---

### Feature 9: Translated Text Rendering

**As a developer**, I want to render visible text from loaded translations, so I can verify integration between catalog loading, key lookup, plural lookup, fallback keys, and UI text output.

**Expected Behavior / Usage:**

The input requests a rendered text snapshot, optionally after triggering a refresh with the current locale. The output is `visible_texts=<JSON array>` containing only the observable texts that appear after translation. It includes simple translations, plural translations, nested string translations, and key/fallback text for object-valued lookups.

**Test Cases:** `rcb_tests/public_test_cases/feature9_widget_text_rendering.json`

```json
{
    "description": "Renders translated text widgets using loaded catalog values and leaves object-valued keys visible as their requested key or fallback key.",
    "cases": [
        {
            "input": {
                "feature": "widget_texts"
            },
            "expected_output": "visible_texts=[\"Key1Value\",\"en\",\"object\",\"valuePlural-1\",\"valuePlural-2\",\"valueSingle\"]\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin or an equivalent harness-provided input channel, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_flat_catalog_loading.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_flat_catalog_loading@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- merge active and fallback keys with active overriding and nested merging
