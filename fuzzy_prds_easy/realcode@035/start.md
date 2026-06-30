## Product Requirement Document

# Static Export Internationalization Toolkit - Client-Side Language Selection and Routing

## Project Goal

Build a client-side internationalization toolkit for statically exported web applications that allows developers to validate language catalogs, select the current language, resolve localized values, and update route query parameters without server-side locale negotiation.

---

## Background & Problem

Without this library/tool, developers are forced to hand-code language catalog validation, route-query preservation, active-language checks, template interpolation, and accessible language-switch controls throughout the application. This leads to repetitive code, inconsistent fallback behavior, broken links, and error-prone localization boilerplate.

With this library/tool, developers define a translation catalog and default language once, then use a consistent runtime contract for resolving the active language, reading translations, and navigating between language-specific routes.

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

### Feature 1: Configuration Resolution

**As a developer**, I want to validate and resolve a language catalog at startup, so I can catch catalog problems before localized rendering begins.

**Expected Behavior / Usage:**

A configuration input contains a translation dictionary keyed by language code, a default language code, a browser-default flag, and an optional browser language. The output reports the resolved default language and catalog signals. If browser-default selection is enabled, a browser language with a regional suffix is reduced to its primary subtag and used only when that subtag exists in the translation dictionary; otherwise the configured default remains. Missing translations, a missing default language, and a default language absent from the catalog are normalized to language-neutral error categories.

**Test Cases:** `rcb_tests/public_test_cases/feature1_configuration_resolution.json`

```json
{
    "description": "Resolves and validates a supplied language catalog before any localized output is requested.",
    "cases": [
        {
            "input": {
                "translations": {
                    "mock": {
                        "title": "mock"
                    },
                    "foo": {
                        "title": "bar"
                    }
                },
                "default_language": "mock",
                "use_browser_default": true,
                "browser_language": "es"
            },
            "expected_output": "config_default_language=mock\navailable_languages=foo,mock\ntranslation.foo.title=bar\ntranslation.mock.title=mock\n"
        },
        {
            "input": {
                "translations": {
                    "mock": {
                        "title": "mock"
                    },
                    "foo": {
                        "title": "bar"
                    }
                },
                "default_language": "mock",
                "use_browser_default": true,
                "browser_language": "invalid"
            },
            "expected_output": "default_language=mock\nbrowser_language=invalid\nbrowser_default_enabled=true\navailable_languages=foo,mock\n"
        },
        {
            "input": {
                "translations": {
                    "mock": {
                        "title": "mock"
                    },
                    "foo": {
                        "title": "bar"
                    }
                },
                "default_language": "mock",
                "use_browser_default": true,
                "browser_language": "foo-US"
            },
            "expected_output": "default_language=foo\nbrowser_language=foo-US\nbrowser_default_enabled=true\navailable_languages=foo,mock\n"
        },
        {
            "input": {
                "translations": {
                    "mock": {
                        "title": "mock"
                    },
                    "foo": {
                        "title": "bar"
                    }
                },
                "default_language": "mock",
                "use_browser_default": false,
                "browser_language": "foo-US"
            },
            "expected_output": "default_language=mock\nbrowser_language=foo-US\nbrowser_default_enabled=false\navailable_languages=foo,mock\n"
        },
        {
            "input": {
                "translations": {},
                "default_language": "mock",
                "use_browser_default": true,
                "browser_language": "es"
            },
            "expected_output": "error=missing_translations\n"
        },
        {
            "input": {
                "translations": {
                    "mock": {
                        "title": "mock"
                    },
                    "foo": {
                        "title": "bar"
                    }
                },
                "default_language": "invalid",
                "use_browser_default": true,
                "browser_language": "es"
            },
            "expected_output": "error=invalid_default_language\ndefault_language=invalid\n"
        },
        {
            "input": {
                "translations": {
                    "mock": {
                        "title": "mock"
                    },
                    "foo": {
                        "title": "bar"
                    }
                },
                "default_language": "",
                "use_browser_default": true,
                "browser_language": "es"
            },
            "expected_output": "error=missing_default_language\n"
        }
    ]
}
```

---

### Feature 2: Selected Language

**As a developer**, I want to derive the active language from route state, so I can render pages in a supported language while ignoring unsupported route values.

**Expected Behavior / Usage:**

The input contains the available translations, the configured default language, and either one route query object or a sequence of route query objects. When the query contains a supported language, that language becomes selected. When the query is empty or names an unsupported language, the selected language is the configured default. For a sequence, the output reports the first selected language and the selected language after the changed route input.

**Test Cases:** `rcb_tests/public_test_cases/feature2_selected_language.json`

```json
{
    "description": "Selects the active language from route data while falling back to the configured default when the route is absent or unsupported.",
    "cases": [
        {
            "input": {
                "translations": {
                    "mock": {
                        "title": "mock"
                    },
                    "foo": {
                        "title": "bar"
                    }
                },
                "default_language": "mock",
                "router_query": {}
            },
            "expected_output": "selected_language=mock\nsource=default\n"
        },
        {
            "input": {
                "translations": {
                    "mock": {
                        "title": "mock"
                    },
                    "foo": {
                        "title": "bar"
                    }
                },
                "default_language": "mock",
                "router_query": {
                    "lang": "foo"
                }
            },
            "expected_output": "selected_language=foo\nsource=query\n"
        },
        {
            "input": {
                "translations": {
                    "mock": {
                        "title": "mock"
                    },
                    "foo": {
                        "title": "bar"
                    }
                },
                "default_language": "mock",
                "router_query_sequence": [
                    {
                        "lang": "foo"
                    },
                    {
                        "lang": "bar"
                    }
                ]
            },
            "expected_output": "initial_selected_language=foo\nupdated_selected_language=mock\n[a specific invalid language code observed in runtime]\n"
        }
    ]
}
```

---

### Feature 3: Language Query Composition

**As a developer**, I want to compose a route query for language navigation, so I can preserve unrelated route parameters while changing language.

**Expected Behavior / Usage:**

The input contains an existing route query, the currently selected language, and optionally a forced target language. The output is the route query object that should be used for navigation. Existing query keys are preserved. The language value is chosen by precedence: forced target language first, then selected language when non-empty, then the existing query language when present. If no query data or language value is available, the output is an empty query object.

**Test Cases:** `rcb_tests/public_test_cases/feature3_language_query_composition.json`

```json
{
    "description": "Builds a navigation query object that preserves existing query fields and chooses the language value using the documented precedence.",
    "cases": [
        {
            "input": {
                "router_query": {
                    "bar": "baz",
                    "lang": "foo"
                },
                "selected_language": "bar",
                "forced_language": "forced"
            },
            "expected_output": "query_json={\"bar\":\"baz\",\"lang\":\"forced\"}\n"
        },
        {
            "input": {
                "router_query": {
                    "bar": "baz",
                    "lang": "foo"
                },
                "selected_language": "bar"
            },
            "expected_output": "query_json={\"bar\":\"baz\",\"lang\":\"bar\"}\n"
        },
        {
            "input": {
                "router_query": {
                    "bar": "baz",
                    "lang": "foo"
                },
                "selected_language": ""
            },
            "expected_output": "query_json={\"bar\":\"baz\",\"lang\":\"foo\"}\n"
        },
        {
            "input": {
                "router_query": null,
                "selected_language": ""
            },
            "expected_output": "query_json={}\n"
        }
    ]
}
```

---

### Feature 4: Language Switcher Active State

**As a developer**, I want to know whether a language switch target is currently active, so I can style or disable the active language option consistently.

**Expected Behavior / Usage:**

The input contains available translations, the configured default language, route query data, and a target language. The output reports the target language, the route language signal, the default language, and whether the target is active. If the route contains a language, active state is determined by equality with that route language. If the route is missing or has no language field, active state is determined by equality with the default language.

**Test Cases:** `rcb_tests/public_test_cases/feature4_language_switcher_active_state.json`

```json
{
    "description": "Reports whether a language switch target is active from the route language when present, otherwise from the configured default language.",
    "cases": [
        {
            "input": {
                "translations": {
                    "mock": {
                        "title": "mock"
                    },
                    "foo": {
                        "title": "bar"
                    }
                },
                "default_language": "mock",
                "router_query": null,
                "target_language": "mock"
            },
            "expected_output": "target_language=mock\nrouter_lang=\ndefault_language=mock\nis_active=true\n"
        },
        {
            "input": {
                "translations": {
                    "mock": {
                        "title": "mock"
                    },
                    "foo": {
                        "title": "bar"
                    }
                },
                "default_language": "mock",
                "router_query": null,
                "target_language": "foo"
            },
            "expected_output": "target_language=foo\nrouter_lang=\ndefault_language=mock\nis_active=false\n"
        },
        {
            "input": {
                "translations": {
                    "mock": {
                        "title": "mock"
                    },
                    "foo": {
                        "title": "bar"
                    }
                },
                "default_language": "mock",
                "router_query": {},
                "target_language": "mock"
            },
            "expected_output": "target_language=mock\nrouter_lang=\ndefault_language=mock\nis_active=true\n"
        },
        {
            "input": {
                "translations": {
                    "mock": {
                        "title": "mock"
                    },
                    "foo": {
                        "title": "bar"
                    }
                },
                "default_language": "mock",
                "router_query": {},
                "target_language": "foo"
            },
            "expected_output": "target_language=foo\nrouter_lang=\ndefault_language=mock\nis_active=false\n"
        },
        {
            "input": {
                "translations": {
                    "mock": {
                        "title": "mock"
                    },
                    "foo": {
                        "title": "bar"
                    }
                },
                "default_language": "mock",
                "router_query": {
                    "lang": "foo"
                },
                "target_language": "foo"
            },
            "expected_output": "target_language=foo\nrouter_lang=foo\ndefault_language=mock\nis_active=true\n"
        },
        {
            "input": {
                "translations": {
                    "mock": {
                        "title": "mock"
                    },
                    "foo": {
                        "title": "bar"
                    }
                },
                "default_language": "mock",
                "router_query": {
                    "lang": "foo"
                },
                "target_language": "bar"
            },
            "expected_output": "target_language=bar\nrouter_lang=foo\ndefault_language=mock\nis_active=false\n"
        }
    ]
}
```

---

### Feature 5: Translation Lookup

**As a developer**, I want to retrieve localized values with nested-key and template support, so I can render localized strings and structured translation data from one catalog.

**Expected Behavior / Usage:**

The input contains translations, the configured and selected language, a lookup key, and optional template data. Keys may address top-level values or nested values with dot-separated path segments. String templates are rendered with the supplied data. Arrays and objects are returned as structured JSON values. When a key path cannot be resolved, the output returns the original requested key as the fallback value.

**Test Cases:** `rcb_tests/public_test_cases/feature5_translation_lookup.json`

```json
{
    "description": "Looks up localized values by key path, renders template strings with provided data, and returns the requested key when no value exists.",
    "cases": [
        {
            "input": {
                "translations": {
                    "mock": {
                        "template": "{{count}} times",
                        "string": "mock",
                        "arr": [
                            1,
                            2,
                            3
                        ],
                        "obj": {
                            "key": "valueMock"
                        },
                        "levelOne": {
                            "levelOneString": "levelOneMock"
                        }
                    }
                },
                "default_language": "mock",
                "selected_language": "mock",
                "lookup_key": "template",
                "template_data": {
                    "count": 2
                }
            },
            "expected_output": "translation_json=\"2 times\"\n"
        },
        {
            "input": {
                "translations": {
                    "mock": {
                        "template": "{{count}} times",
                        "string": "mock",
                        "arr": [
                            1,
                            2,
                            3
                        ],
                        "obj": {
                            "key": "valueMock"
                        },
                        "levelOne": {
                            "levelOneString": "levelOneMock"
                        }
                    }
                },
                "default_language": "mock",
                "selected_language": "mock",
                "lookup_key": "string"
            },
            "expected_output": "translation_json=\"mock\"\n"
        },
        {
            "input": {
                "translations": {
                    "mock": {
                        "template": "{{count}} times",
                        "string": "mock",
                        "arr": [
                            1,
                            2,
                            3
                        ],
                        "obj": {
                            "key": "valueMock"
                        },
                        "levelOne": {
                            "levelOneString": "levelOneMock"
                        }
                    }
                },
                "default_language": "mock",
                "selected_language": "mock",
                "lookup_key": "levelOne.levelOneString"
            },
            "expected_output": "translation_json=\"levelOneMock\"\n"
        },
        {
            "input": {
                "translations": {
                    "mock": {
                        "template": "{{count}} times",
                        "string": "mock",
                        "arr": [
                            1,
                            2,
                            3
                        ],
                        "obj": {
                            "key": "valueMock"
                        },
                        "levelOne": {
                            "levelOneString": "levelOneMock"
                        }
                    }
                },
                "default_language": "mock",
                "selected_language": "mock",
                "lookup_key": "arr"
            },
            "expected_output": "translation_json=[1,2,3]\n"
        },
        {
            "input": {
                "translations": {
                    "mock": {
                        "template": "{{count}} times",
                        "string": "mock",
                        "arr": [
                            1,
                            2,
                            3
                        ],
                        "obj": {
                            "key": "valueMock"
                        },
                        "levelOne": {
                            "levelOneString": "levelOneMock"
                        }
                    }
                },
                "default_language": "mock",
                "selected_language": "mock",
                "lookup_key": "obj"
            },
            "expected_output": "translation_json={\"key\":\"valueMock\"}\n"
        },
        {
            "input": {
                "translations": {
                    "mock": {
                        "template": "{{count}} times",
                        "string": "mock",
                        "arr": [
                            1,
                            2,
                            3
                        ],
                        "obj": {
                            "key": "valueMock"
                        },
                        "levelOne": {
                            "levelOneString": "levelOneMock"
                        }
                    }
                },
                "default_language": "mock",
                "selected_language": "mock",
                "lookup_key": "invalid.key"
            },
            "expected_output": "translation_json=\"invalid.key\"\n"
        }
    ]
}
```

---

### Feature 6: Language Switch Control

**As a developer**, I want to render an accessible language switch control that updates routing, so I can let users change language while preserving router-observable navigation behavior.

**Expected Behavior / Usage:**

The input contains translations, default language, current route query data, a target language, a shallow-routing flag, and whether custom child content is present. The output includes DOM accessibility signals and the route update emitted after activation. The rendered control must expose button semantics and an accessible label naming the target language. When activated, it must send a route update whose query contains the target language and whose shallow-routing option matches the input. If custom child content has its own click behavior, that behavior is preserved before the route update is sent.

**Test Cases:** `rcb_tests/public_test_cases/feature6_language_switch_control.json`

```json
{
    "description": "Renders an accessible language switch control and, when activated, sends a route update containing the target language and requested shallow-routing flag.",
    "cases": [
        {
            "input": {
                "translations": {
                    "mock": {
                        "string": "mock"
                    }
                },
                "default_language": "mock",
                "router_query": {},
                "target_language": "languageKey",
                "shallow": false,
                "child_mode": "none"
            },
            "expected_output": "role=button\naria_label=set language to languageKey\ncontains_child=false\nchild_click_handler_called=false\nrouter_push.pathname=undefined\nrouter_push.query_json={\"lang\":\"languageKey\"}\nrouter_push.shallow=false\n"
        },
        {
            "input": {
                "translations": {
                    "mock": {
                        "string": "mock"
                    }
                },
                "default_language": "mock",
                "router_query": {},
                "target_language": "languageKeyShallow",
                "shallow": true,
                "child_mode": "none"
            },
            "expected_output": "role=button\naria_label=set language to languageKeyShallow\ncontains_child=false\nchild_click_handler_called=false\nrouter_push.pathname=undefined\nrouter_push.query_json={\"lang\":\"languageKeyShallow\"}\nrouter_push.shallow=true\n"
        },
        {
            "input": {
                "translations": {
                    "mock": {
                        "string": "mock"
                    }
                },
                "default_language": "mock",
                "router_query": {},
                "target_language": "languageKey",
                "shallow": false,
                "child_mode": "nested"
            },
            "expected_output": "role=button\naria_label=set language to languageKey\ncontains_child=true\nchild_click_handler_called=false\nrouter_push.pathname=undefined\nrouter_push.query_json={\"lang\":\"languageKey\"}\nrouter_push.shallow=false\n"
        },
        {
            "input": {
                "translations": {
                    "mock": {
                        "string": "mock"
                    }
                },
                "default_language": "mock",
                "router_query": {},
                "target_language": "languageKey",
                "shallow": false,
                "child_mode": "nested_with_handler"
            },
            "expected_output": "role=button\naria_label=set language to languageKey\ncontains_child=true\nchild_click_handler_called=true\nrouter_push.pathname=undefined\nrouter_push.query_json={\"lang\":\"languageKey\"}\nrouter_push.shallow=false\n"
        },
        {
            "input": {
                "translations": {
                    "mock": {
                        "string": "mock"
                    }
                },
                "default_language": "mock",
                "router_query": {},
                "target_language": "languageKeyShallow",
                "shallow": true,
                "child_mode": "nested"
            },
            "expected_output": "role=button\naria_label=set language to languageKeyShallow\ncontains_child=true\nchild_click_handler_called=false\nrouter_push.pathname=undefined\nrouter_push.query_json={\"lang\":\"languageKeyShallow\"}\nrouter_push.shallow=true\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_configuration_resolution.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_configuration_resolution@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- regarding tokens in the region suffix
- in sync with the initial loader
