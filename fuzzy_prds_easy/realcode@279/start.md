## Product Requirement Document

# Rich Text Editor Integration Adapter - JavaScript Rendering and Form View Contract

## Project Goal

Build a rich text editor integration adapter that allows developers to configure editor assets, startup scripts, browser routes, reusable resource collections, and form-view metadata without hand-writing repetitive JavaScript and form wiring.

---

## Background & Problem

Without this library[a specific set of regex escape characters for special path delimiters]tool, developers are forced to assemble editor script tags, startup calls, plugin registrations, style registrations, template registrations, route-generated browser URLs, and form rendering variables manually. This leads to inconsistent JavaScript, missed escaping rules, duplicated asset-path handling, and fragile integration between form options and browser-visible editor behavior.

With this library[a specific set of regex escape characters for special path delimiters]tool, developers describe editor inputs once and receive deterministic browser-facing JavaScript snippets or form-view data that can be rendered by an application template.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities[a specific set of regex escape characters for special path delimiters]simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I[a specific set of regex escape characters for special path delimiters]O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src[a specific set of regex escape characters for special path delimiters]`, `tests[a specific set of regex escape characters for special path delimiters]`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input[a specific set of regex escape characters for special path delimiters]output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I[a specific set of regex escape characters for special path delimiters]O (stdin[a specific set of regex escape characters for special path delimiters]stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open[a specific set of regex escape characters for special path delimiters]Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces[a specific set of regex escape characters for special path delimiters]protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I[a specific set of regex escape characters for special path delimiters]O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result[a specific set of regex escape characters for special path delimiters]Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: Asset URL Normalization

**As a developer**, I want editor resource paths to be resolved through the application's asset layer, so I can serve versioned or rewritten assets while emitting the exact URL shape expected by the browser editor.

**Expected Behavior [a specific set of regex escape characters for special path delimiters] Usage:**

The execution adapter accepts an `asset_paths` request containing an asset lookup table plus editor base and script paths. The output is line-oriented stdout. The base path line must contain the resolved URL with any query string removed, because the browser editor treats it as a directory prefix. The script path line must contain the resolved script URL exactly as served by the asset layer, including query strings when present.

**Test Cases:** `rcb_tests[a specific set of regex escape characters for special path delimiters]public_test_cases[a specific set of regex escape characters for special path delimiters]feature1_asset_url_normalization.json`

```json
{
    "description": "Asset-backed editor resource paths are rendered as browser URLs, with cache query strings removed only where a directory-style base path is required.",
    "cases": [
        {
            "input": {
                "action": "asset_paths",
                "assets": {
                    "bundles[a specific set of regex escape characters for special path delimiters]editor[a specific set of regex escape characters for special path delimiters]": "[a specific set of regex escape characters for special path delimiters]static[a specific set of regex escape characters for special path delimiters]editor[a specific set of regex escape characters for special path delimiters]?v=2",
                    "bundles[a specific set of regex escape characters for special path delimiters]editor[a specific set of regex escape characters for special path delimiters]editor.js": "[a specific set of regex escape characters for special path delimiters]static[a specific set of regex escape characters for special path delimiters]editor[a specific set of regex escape characters for special path delimiters]editor.js?v=2"
                },
                "base_path": "bundles[a specific set of regex escape characters for special path delimiters]editor[a specific set of regex escape characters for special path delimiters]",
                "js_path": "bundles[a specific set of regex escape characters for special path delimiters]editor[a specific set of regex escape characters for special path delimiters]editor.js"
            },
            "expected_output": "base_path=[a specific set of regex escape characters for special path delimiters]static[a specific set of regex escape characters for special path delimiters]editor[a specific set of regex escape characters for special path delimiters]\njs_path=[a specific set of regex escape characters for special path delimiters]static[a specific set of regex escape characters for special path delimiters]editor[a specific set of regex escape characters for special path delimiters]editor.js?v=2\n"
        }
    ]
}
```

---

### Feature 2: Widget Startup Script Generation

**As a developer**, I want a configured editor target to render as a deterministic JavaScript startup call, so I can initialize the browser editor from server-side configuration.

**Expected Behavior [a specific set of regex escape characters for special path delimiters] Usage:**

The execution adapter accepts a `widget_script` request with an element identifier, optional locale source, editor configuration data, and runtime options. The output is the exact JavaScript startup snippet followed by a newline. Locale values using underscores are normalized to lowercase hyphenated editor language identifiers. The startup call must include the target element id and the final JSON-style configuration.

**Test Cases:** `rcb_tests[a specific set of regex escape characters for special path delimiters]public_test_cases[a specific set of regex escape characters for special path delimiters]feature2_widget_script_generation.json`

```json
{
    "description": "Editor startup scripts render the target element id, normalized language data, selected startup mode, and input synchronization code as JavaScript.",
    "cases": [
        {
            "input": {
                "action": "widget_script",
                "element_id": "body",
                "locale_source": "request_stack",
                "locale": "pt_BR",
                "configuration": {},
                "options": {}
            },
            "expected_output": "CKEDITOR.replace(\"body\", {\"language\":\"pt-br\"}[a specific factory function signature for external plugin registration]\n"
        }
    ]
}
```

---

### Feature 3: Stylesheet and Browser URL Configuration

**As a developer**, I want stylesheet references and file-browser routes inside editor configuration to become browser-usable URLs, so I can connect editor dialogs and content styles to application assets and routes.

**Expected Behavior [a specific set of regex escape characters for special path delimiters] Usage:**

The execution adapter accepts a `widget_script` request whose configuration may include stylesheet paths and browser route declarations. Stylesheet paths are resolved through the asset layer, stripped of cache query strings, and emitted as an array in the JavaScript configuration. Route declarations are resolved through the routing layer and emitted as final browser URL configuration values, including route parameters and route reference mode in the generated URL signal.

**Test Cases:** `rcb_tests[a specific set of regex escape characters for special path delimiters]public_test_cases[a specific set of regex escape characters for special path delimiters]feature3_content_css_and_filebrowser_urls.json`

```json
{
    "description": "Widget configuration converts stylesheet asset paths and browser route declarations into the final JavaScript configuration URLs.",
    "cases": [
        {
            "input": {
                "action": "widget_script",
                "element_id": "body",
                "assets": {
                    "theme.css": "[a specific set of regex escape characters for special path delimiters]assets[a specific set of regex escape characters for special path delimiters]theme.css?v=9"
                },
                "configuration": {
                    "contentsCss": "theme.css"
                },
                "options": {}
            },
            "expected_output": "CKEDITOR.replace(\"body\", {\"contentsCss\":[\"[a specific set of regex escape characters for special path delimiters]assets[a specific set of regex escape characters for special path delimiters]theme.css\"]}[a specific factory function signature for external plugin registration]\n"
        }
    ]
}
```

---

### Feature 4: Raw JavaScript Configuration Values

**As a developer**, I want selected editor configuration values that are JavaScript expressions to be emitted as expressions rather than strings, so I can pass regular expressions and editor constants without breaking the browser API.

**Expected Behavior [a specific set of regex escape characters for special path delimiters] Usage:**

The execution adapter accepts a `widget_script` request with configuration values that may contain raw JavaScript expressions. Protected-source expression arrays and selector parser expressions must be emitted without surrounding JSON string quotes. Editor constants inside nested configuration data must also be emitted without string quotes, while ordinary string and object values remain JSON encoded.

**Test Cases:** `rcb_tests[a specific set of regex escape characters for special path delimiters]public_test_cases[a specific set of regex escape characters for special path delimiters]feature4_raw_javascript_configuration_values.json`

```json
{
    "description": "Configuration values that are intended to be JavaScript expressions are emitted without JSON string quoting while ordinary values remain JSON encoded.",
    "cases": [
        {
            "input": {
                "action": "widget_script",
                "element_id": "body",
                "configuration": {
                    "protectedSource": [
                        "[a specific set of regex escape characters for special path delimiters]<\\?[\\s\\S]*?\\?>[a specific set of regex escape characters for special path delimiters]g",
                        "[a specific set of regex escape characters for special path delimiters]<%[\\s\\S]*?%>[a specific set of regex escape characters for special path delimiters]g"
                    ]
                },
                "options": {}
            },
            "expected_output": "CKEDITOR.replace(\"body\", {\"protectedSource\":[[a specific set of regex escape characters for special path delimiters]<\\?[\\s\\S]*?\\?>[a specific set of regex escape characters for special path delimiters]g,[a specific set of regex escape characters for special path delimiters]<%[\\s\\S]*?%>[a specific set of regex escape characters for special path delimiters]g]}[a specific factory function signature for external plugin registration]\n"
        }
    ]
}
```

---

### Feature 5: Auxiliary Registration Scripts

**As a developer**, I want non-widget editor resources to render as standalone JavaScript snippets, so I can register plugins, style sets, templates, and teardown behavior independently of widget startup.

**Expected Behavior [a specific set of regex escape characters for special path delimiters] Usage:**

The execution adapter accepts requests for destroy scripts, plugin registration scripts, style registration scripts, and template registration scripts. Destroy scripts must guard against missing editor instances before destroying and deleting them. Plugin paths and template image paths are resolved through the asset layer and have query strings removed when they represent directory-style paths. Style and template payloads are JSON encoded into the editor's browser API calls.

**Test Cases:** `rcb_tests[a specific set of regex escape characters for special path delimiters]public_test_cases[a specific set of regex escape characters for special path delimiters]feature5_auxiliary_registration_scripts.json`

```json
{
    "description": "Auxiliary editor resources are rendered as JavaScript snippets that register plugins, style sets, template sets, and teardown behavior.",
    "cases": [
        {
            "input": {
                "action": "destroy_script",
                "element_id": "body"
            },
            "expected_output": "[a specific set of literal strings used to reconstruct the CKEDITOR instance wrapper]\"body\"[a specific set of literal strings used to reconstruct the CKEDITOR instance wrapper] CKEDITOR.instances[\"body\"].destroy(true[a specific factory function signature for external plugin registration] delete CKEDITOR.instances[\"body\"]; }\n"
        },
        {
            "input": {
                "action": "plugin_script",
                "assets": {
                    "plugins[a specific set of regex escape characters for special path delimiters]wordcount[a specific set of regex escape characters for special path delimiters]": "[a specific set of regex escape characters for special path delimiters]static[a specific set of regex escape characters for special path delimiters]wordcount[a specific set of regex escape characters for special path delimiters]?v=2"
                },
                "name": "wordcount",
                "plugin": {
                    "path": "plugins[a specific set of regex escape characters for special path delimiters]wordcount[a specific set of regex escape characters for special path delimiters]",
                    "filename": "plugin.js"
                }
            },
            "expected_output": "[a specific factory function signature for external plugin registration]\"wordcount\", \"[a specific set of regex escape characters for special path delimiters]static[a specific set of regex escape characters for special path delimiters]wordcount[a specific set of regex escape characters for special path delimiters]\", \"plugin.js\"[a specific factory function signature for external plugin registration]\n"
        }
    ]
}
```

---

### Feature 6: Named Resource Collections

**As a developer**, I want named configuration, plugin, style, and template collections to be stored and retrieved predictably, so form rendering can reuse shared editor resources while reporting missing names clearly.

**Expected Behavior [a specific set of regex escape characters for special path delimiters] Usage:**

The execution adapter accepts collection-management requests for named editor resources. Empty collections report that no entries exist. Named configuration entries can be merged so later keys override earlier keys while preserving unspecified data. Reading a missing resource must not expose host-language exception names or runtime messages; it must output a neutral error category and the missing name on separate lines.

**Test Cases:** `rcb_tests[a specific set of regex escape characters for special path delimiters]public_test_cases[a specific set of regex escape characters for special path delimiters]feature6_named_resource_collections.json`

```json
{
    "description": "Named collections preserve supplied entries, replace entries with the same name, merge selected editor configuration data, and expose neutral missing-entry errors.",
    "cases": [
        {
            "input": {
                "action": "named_configs",
                "initial": {},
                "operations": []
            },
            "expected_output": "has_entries=no\ndefault=null\nentries=[]\n"
        },
        {
            "input": {
                "action": "named_configs",
                "initial": {
                    "default": {
                        "toolbar": "basic",
                        "uiColor": "#ffffff"
                    }
                },
                "default": "default",
                "operations": [
                    {
                        "type": "merge",
                        "name": "default",
                        "value": {
                            "uiColor": "#000000"
                        }
                    }
                ]
            },
            "expected_output": "has_entries=yes\ndefault=default\nentries={\"default\":{\"toolbar\":\"basic\",\"uiColor\":\"#000000\"}}\n"
        },
        {
            "input": {
                "action": "read_config",
                "initial": {},
                "name": "missing"
            },
            "expected_output": "error=missing_config\nname=missing\n"
        }
    ]
}
```

---

### Feature 7: Form View Defaults and Overrides

**As a developer**, I want editor form creation to expose all browser-rendering variables in the form view, so templates can render the editor consistently from defaults, configured values, and per-form overrides.

**Expected Behavior [a specific set of regex escape characters for special path delimiters] Usage:**

The execution adapter accepts a `form_view` request with stored shared resources, configured defaults, and per-form options. When enabled, stdout contains one `view=` line whose JSON object includes flags, asset paths, file browser names, configuration data, plugins, style sets, and templates. Per-form options override or augment configured defaults according to their resource type. When disabled, the view output contains only the disabled state and omits editor-only rendering variables.

**Test Cases:** `rcb_tests[a specific set of regex escape characters for special path delimiters]public_test_cases[a specific set of regex escape characters for special path delimiters]feature7_form_view_defaults_and_overrides.json`

```json
{
    "description": "Creating an editor form view exposes default view variables, applies configured defaults, accepts per-form overrides, and omits editor-only variables when disabled.",
    "cases": [
        {
            "input": {
                "action": "form_view",
                "form_options": {}
            },
            "expected_output": "view={\"enable\":true,\"async\":false,\"autoload\":true,\"auto_inline\":true,\"inline\":false,\"jquery\":false,\"require_js\":false,\"input_sync\":false,\"filebrowsers\":[],\"base_path\":\"bundles[a specific set of regex escape characters for special path delimiters]ivoryckeditor[a specific set of regex escape characters for special path delimiters]\",\"js_path\":\"bundles[a specific set of regex escape characters for special path delimiters]ivoryckeditor[a specific set of regex escape characters for special path delimiters]ckeditor.js\",\"jquery_path\":\"bundles[a specific set of regex escape characters for special path delimiters]ivoryckeditor[a specific set of regex escape characters for special path delimiters]adapters[a specific set of regex escape characters for special path delimiters]jquery.js\",\"config\":[],\"plugins\":[],\"styles\":[],\"templates\":[]}\n"
        },
        {
            "input": {
                "action": "form_view",
                "defaults": {
                    "enable": false
                },
                "form_options": {
                    "config": {
                        "toolbar": {
                            "foo": "bar"
                        }
                    },
                    "plugins": {
                        "wordcount": {
                            "path": "[a specific set of regex escape characters for special path delimiters]my[a specific set of regex escape characters for special path delimiters]path",
                            "filename": "plugin.js"
                        }
                    }
                }
            },
            "expected_output": "view={\"enable\":false}\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution[a specific set of regex escape characters for special path delimiters]Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests[a specific set of regex escape characters for special path delimiters]public_test_cases[a specific set of regex escape characters for special path delimiters]`. A single entry point `bash rcb_tests[a specific set of regex escape characters for special path delimiters]test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests[a specific set of regex escape characters for special path delimiters]stdout[a specific set of regex escape characters for special path delimiters]<cases-dir>[a specific set of regex escape characters for special path delimiters]{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests[a specific set of regex escape characters for special path delimiters]stdout[a specific set of regex escape characters for special path delimiters]public_test_cases[a specific set of regex escape characters for special path delimiters]feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS[a specific set of regex escape characters for special path delimiters]FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- apply the same stripping rule as defined in C007
- handle the merge operation similarly to named_configs C020
