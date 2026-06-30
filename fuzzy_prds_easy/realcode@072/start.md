## Product Requirement Document

# Mobile Autocomplete Field - Configurable Search and Selection Overlay

## Project Goal

Build a mobile-friendly autocomplete field component that allows developers to present searchable single-selection and multiple-selection inputs with configurable display text, asynchronous search data, custom overlay content, and predictable open/close behavior without hand-building modal search UI and selection synchronization for each form.

---

## Background & Problem

Without this library/tool, developers are forced to manually wire a read-only form field, an overlay search input, result rendering, selected-item rendering, callbacks, and lifecycle cleanup. This leads to repetitive UI glue code, inconsistent empty-state handling, fragile asynchronous result handling, and duplicated logic for single-selection versus multiple-selection forms.

With this library/tool, developers configure a field declaratively and receive a generated search overlay whose visible state, labels, selected values, search results, templates, and teardown behavior follow a stable black-box contract.

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

### Feature 1: Single-Selection Field Rendering and Text Configuration

**As a developer**, I want a generated autocomplete field and overlay to have predictable default chrome and configurable prompt text, so I can place a consistent search-and-select control into forms without recreating its UI shell.

**Expected Behavior / Usage:**

*1.1 Default field chrome — The component must render an outer text field in read-only mode, create an initially closed search overlay, create a search input inside that overlay, include a search placeholder icon, and include a clear-style close button. With no caller-supplied prompt or close text, the outer prompt is empty, the overlay search prompt uses the built-in instruction text, and the close button uses the built-in completion label. The output reports observable field attributes, search-field attributes, icon identity, button classes, button text, and overlay state.*

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_default_field_chrome.json`

```json
{
    "description": "Render a single-selection autocomplete field without optional configuration and expose the default outer field, search field, icon, button, and closed overlay state.",
    "cases": [
        {
            "input": {
                "scenario": "default_single_field"
            },
            "expected_output": "outer_type=text\nouter_readonly=true\nouter_has_widget_class=true\nouter_placeholder=\nsearch_type=search\nsearch_has_widget_search_class=true\nsearch_placeholder=Click to enter a value...\nplaceholder_icon=search\ncancel_has_button_class=true\ncancel_has_clear_class=true\ncancel_label=Done\ncontainer_state=closed\n"
        }
    ]
}
```

*1.2 Custom prompt and close text — The component must apply caller-supplied prompt text to both the outer field and the overlay search input. It must also render caller-supplied close-button text in the overlay. The output reports the visible text on each affected UI element.*

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_custom_prompt_and_cancel_text.json`

```json
{
    "description": "Render caller-provided prompt text on both the closed field and the overlay search field, and render caller-provided text on the overlay close button.",
    "cases": [
        {
            "input": {
                "scenario": "custom_placeholder_and_cancel"
            },
            "expected_output": "outer_placeholder=placeholder value\nsearch_placeholder=placeholder value\ncancel_label=Cancel Button\n"
        }
    ]
}
```

---

### Feature 2: Selection Value Display and Projection

**As a developer**, I want selected data to be displayed through stable value projection rules, so I can bind primitive or object selections and show the correct user-facing value.

**Expected Behavior / Usage:**

*2.1 Initial and cleared model display — Before the overlay is opened, the outer field must render an empty string when no selection exists, render a converted value when a preloaded external selection is resolved, render nested object fields when a field path is configured, support dynamically supplied field paths, and clear the visible text when the bound selection is cleared. The output reports the outer field value before and after these model states.*

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_initial_and_cleared_model_display.json`

```json
{
    "description": "Render the closed field from absent, preloaded, nested, dynamically addressed, and cleared selection data without requiring the user to open the overlay.",
    "cases": [
        {
            "input": {
                "scenario": "empty_model_display"
            },
            "expected_output": "[the initial empty state value]\n"
        },
        {
            "input": {
                "scenario": "external_model_display"
            },
            "expected_output": "[the initial empty state value]Model 123\n"
        },
        {
            "input": {
                "scenario": "nested_model_display"
            },
            "expected_output": "[the initial empty state value]value1\n"
        },
        {
            "input": {
                "scenario": "dynamic_nested_model_display"
            },
            "expected_output": "[the initial empty state value]value1\n"
        },
        {
            "input": {
                "scenario": "cleared_model_display"
            },
            "expected_output": "before_clear_[the initial empty state value]value1\nafter_clear_[the initial empty state value]\n"
        }
    ]
}
```

*2.2 Item value projection — When asked to project a value from an item, the component must return primitive items unchanged, extract a direct field from an object when a field path is supplied, return the whole object when no field path is supplied, and extract nested fields from nested objects. The output reports each projected value as raw stdout lines.*

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_item_value_projection.json`

```json
{
    "description": "Project item display or stored values by returning primitives unchanged, extracting direct object fields, returning whole objects when no field path is supplied, and extracting nested object fields.",
    "cases": [
        {
            "input": {
                "scenario": "value_projection"
            },
            "expected_output": "[a specific null projection string]\nobject_key_value=value\nobject_without_key={\"key\":\"value\"}\nnested_key_value=value1\n"
        }
    ]
}
```

---

### Feature 3: Search Provider Integration

**As a developer**, I want the search overlay to call my result provider consistently for synchronous and asynchronous data, so I can plug in local arrays or remote response flows without changing the component contract.

**Expected Behavior / Usage:**

*3.1 Synchronous search provider — The component must not call the provider for an undefined query. It must call the provider for an empty query and for a non-empty query, passing the query through unchanged. When a component identifier is configured, that identifier must be passed with the query. The returned items must become the visible search item list. The output reports provider call counts, provider inputs, and resulting search items.*

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_sync_search_provider.json`

```json
{
    "description": "Invoke the search provider only for defined queries, pass empty and non-empty queries through unchanged, optionally include a component identifier, and render the returned search items.",
    "cases": [
        {
            "input": {
                "scenario": "search_undefined_query"
            },
            "expected_output": "provider_calls=0\nsearch_items=[]\n"
        },
        {
            "input": {
                "scenario": "search_empty_query"
            },
            "expected_output": "provider_calls=1\nreceived_queries=[\"\"]\nsearch_items=[\"item\"]\n"
        },
        {
            "input": {
                "scenario": "search_valid_query"
            },
            "expected_output": "provider_calls=1\nreceived_queries=[\"asd\"]\nsearch_items=[\"asd\",\"item2\"]\n"
        },
        {
            "input": {
                "scenario": "search_valid_query_with_component"
            },
            "expected_output": "provider_calls=1\nreceived=[{\"query\":\"asd\",\"componentId\":\"compId\"}]\nsearch_items=[\"asd\",\"compId\",\"item2\"]\n"
        }
    ]
}
```

*3.2 Asynchronous search provider — The component must accept asynchronous provider results, keep the item list empty before the result settles, populate the item list after successful resolution, unwrap a response object that contains a data payload, and preserve rejection propagation to the original asynchronous chain. The output reports call counts, inputs, before/after item lists, response-data item counts, and rejection callback counts.*

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_async_search_provider.json`

```json
{
    "description": "Accept asynchronous search results, keep the search list empty until the asynchronous operation settles, read response-wrapper data payloads, and forward rejection notifications to the original promise chain.",
    "cases": [
        {
            "input": {
                "scenario": "search_promise_resolution"
            },
            "expected_output": "provider_calls_before_resolution=1\nreceived_queries=[\"asd\"]\nitems_before_resolution=[]\nitems_after_resolution=[\"asd\",\"item2\"]\n"
        },
        {
            "input": {
                "scenario": "search_http_response_data"
            },
            "expected_output": "provider_calls_before_resolution=1\nitems_before_resolution=[]\nitems_after_resolution_count=2\nitems_after_resolution=[{\"name\":\"name\",\"view\":\"view\"},{\"name\":\"name1\",\"view\":\"view1\"}]\n"
        },
        {
            "input": {
                "scenario": "search_rejection_forwarded"
            },
            "expected_output": "provider_calls=1\nitems_before_rejection=[]\nrejection_callbacks=1\n"
        }
    ]
}
```

---

### Feature 4: Overlay State and Lifecycle

**As a developer**, I want the generated overlay to open, close, expose customizable state classes, and clean itself up reliably, so I can integrate it into screens without stale DOM or incorrect modal state.

**Expected Behavior / Usage:**

*4.1 Normal open and close — With automatic opening enabled, activating the outer field must move the overlay from closed to open. Activating the overlay close button must move it back to closed. The output reports the overlay state before activation, after field activation, and after close-button activation.*

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_overlay_open_close.json`

```json
{
    "description": "Toggle the search overlay between closed and open states through normal field activation and close-button activation.",
    "cases": [
        {
            "input": {
                "scenario": "click_opens_and_cancel_closes"
            },
            "expected_output": "initial_container_state=closed\nafter_click_container_state=open\nafter_cancel_container_state=closed\n"
        }
    ]
}
```

*4.2 External overlay control — When automatic opening is disabled, activating the outer field must leave the overlay closed. Explicit open and close calls must still move the overlay to open and closed states. The output reports state after field activation, after explicit open, and after explicit close.*

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_external_overlay_control.json`

```json
{
    "description": "When automatic opening is disabled, keep the overlay closed on field activation while still allowing explicit open and close commands to control it.",
    "cases": [
        {
            "input": {
                "scenario": "external_modal_control"
            },
            "expected_output": "after_click_container_state=closed\nafter_external_open_state=open\nafter_external_close_state=closed\n"
        }
    ]
}
```

*4.3 Custom overlay state classes — When custom open and closed class names are supplied, the overlay must use those custom state classes and must not retain the default state classes. Opening the overlay must remove the custom closed class and add the custom open class. The output reports custom and default class presence before and after opening.*

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_custom_overlay_classes.json`

```json
{
    "description": "Use caller-provided CSS state classes instead of the default open and closed classes when changing overlay state.",
    "cases": [
        {
            "input": {
                "scenario": "custom_modal_classes"
            },
            "expected_output": "initial_has_custom_closed=true\ninitial_has_custom_open=false\ninitial_has_default_closed=false\ninitial_has_default_open=false\nafter_click_has_custom_closed=false\nafter_click_has_custom_open=true\nafter_click_has_default_closed=false\nafter_click_has_default_open=false\n"
        }
    ]
}
```

*4.4 Overlay lifecycle cleanup — Destroying the owning field context must remove the generated overlay element from the document. The output reports overlay element counts before and after destruction.*

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_overlay_lifecycle_cleanup.json`

```json
{
    "description": "Remove the generated overlay element from the document when the owning field scope is destroyed.",
    "cases": [
        {
            "input": {
                "scenario": "destroy_removes_modal"
            },
            "expected_output": "container_count_before_destroy=1\ncontainer_count_after_destroy=0\n"
        }
    ]
}
```

---

### Feature 5: Generated Search Input and Custom Overlay Templates

**As a developer**, I want generated overlay internals to receive configured input behavior and optionally use custom template content, so I can match form timing and screen-specific presentation needs.

**Expected Behavior / Usage:**

*5.1 Search input options — Model update options configured on the outer field must be forwarded to the generated search input inside the overlay. The output reports the forwarded debounce duration visible on the generated search input controller.*

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_search_input_options.json`

```json
{
    "description": "Forward model update options configured on the closed field to the generated search input inside the overlay.",
    "cases": [
        {
            "input": {
                "scenario": "model_options_forwarding"
            },
            "expected_output": "[the standard debounce duration]\n"
        }
    ]
}
```

*5.2 Custom templates — The overlay must be able to render caller-supplied template content from a static template location or a dynamically bound template location. Template content must be able to bind to the field prompt and to caller-provided template data. The output reports the rendered template visibility and rendered text where the original tests observe it.*

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_custom_templates.json`

```json
{
    "description": "Render a caller-supplied overlay template from a static or dynamic URL and bind template text to field prompt data or caller-provided template data.",
    "cases": [
        {
            "input": {
                "scenario": "static_template"
            },
            "expected_output": "template_visible=block\ntemplate_text=placeholder text\n"
        },
        {
            "input": {
                "scenario": "dynamic_template_url"
            },
            "expected_output": "template_visible=block\n"
        },
        {
            "input": {
                "scenario": "template_data"
            },
            "expected_output": "template_visible=block\ntemplate_text=test-data\n"
        }
    ]
}
```

---

### Feature 6: Multiple-Selection Overlay Behavior

**As a developer**, I want multiple-selection overlays to label selected and available sections correctly and close predictably, so I can support selecting more than one result without changing the user interaction model.

**Expected Behavior / Usage:**

*6.1 Multiple-selection labels — In multiple-selection mode, the selected-items section must render caller-provided selected-section text. Once search results exist, the available-items section must render caller-provided available-section text. The output reports both visible section labels.*

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_multiple_selection_labels.json`

```json
{
    "description": "In multiple-selection mode, render caller-provided labels for the selected-items section and for the available-items section once search results exist.",
    "cases": [
        {
            "input": {
                "scenario": "multiple_labels"
            },
            "expected_output": "selected_items_label=selected-items\nselect_items_label=select-item\n"
        }
    ]
}
```

*6.2 Multiple-selection available-items divider — In multiple-selection mode, the overlay must not render the available-items divider before any search results are present. After search results are added, the divider must become visible. The output reports overlay state and divider visibility before and after items are present.*

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_multiple_selection_available_items_divider.json`

```json
{
    "description": "In multiple-selection mode, omit the available-items divider when there are no search results and show it after results are added.",
    "cases": [
        {
            "input": {
                "scenario": "multiple_items_divider_visibility"
            },
            "expected_output": "initial_container_state=closed\nafter_click_container_state=open\ndivider_before_items=absent\ndivider_after_items=visible\n"
        }
    ]
}
```

*6.3 Multiple-selection close behavior — In multiple-selection mode, activating the outer field must open the overlay and activating the close button must close it. The output reports the overlay state before activation, after opening, and after close-button activation.*

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_multiple_selection_cancel.json`

```json
{
    "description": "In multiple-selection mode, close the overlay when the close button is activated.",
    "cases": [
        {
            "input": {
                "scenario": "multiple_cancel_closes"
            },
            "expected_output": "initial_container_state=closed\nafter_click_container_state=open\nafter_cancel_container_state=closed\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_default_field_chrome.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_default_field_chrome@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the standard widget predicate pattern for outer read-only states
- check the CSS class inheritance logic for modal overlays
