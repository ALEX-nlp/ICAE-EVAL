## Product Requirement Document

# Reactive Todo State Engine — Observer Logging, Localization & Loading UI

## Project Goal

Build the supporting layer for a reactive, unidirectional todo application: a global state-management observer that produces consistent human-readable logs of every state transition and error, a localization provider that resolves the app title and decides which locales are supported, and a reusable loading-indicator UI component. Together these let developers ship a predictable, observable, and localizable application without hand-rolling logging, locale-resolution, or boilerplate loading widgets.

---

## Background & Problem

Without this layer, developers wiring up a reactive state container are forced to sprinkle ad-hoc `print` statements throughout each independent state machine to understand what changed and why, write bespoke locale-matching logic that subtly diverges between screens, and re-implement the same "spinner while data loads" widget over and over. This leads to inconsistent log formats that are hard to grep, locale checks that silently accept or reject the wrong languages, and duplicated UI code.

With this layer, a single observer formats every transition and error identically, one delegate answers "is this locale supported?" and "do cached strings need rebuilding?" uniformly, and a single drop-in component renders the standard centered spinner. Behavior is observable, locale handling is centralized, and the loading UI is reused everywhere.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

[a specific singleton integer value]. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. The three concerns here — observer logging, localization resolution, and the loading UI component — are independent and SHOULD live in clearly separated units rather than a single monolithic file. Do not over-engineer; a small, well-factored module tree is sufficient.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below represent a **black-box testing contract** for the execution adapter, NOT the internal data model. The core logging/localization/widget logic must remain completely decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls into the core and rendering the results.

3. **Adherence to SOLID Design Principles:** Separate parsing, routing, core execution, and output formatting into distinct logical units (SRP). The observer must be open for extension (new log sinks) but closed for modification (OCP). Keep interfaces small and cohesive (ISP), and have high-level modules depend on abstractions rather than I/O details (DIP).

4. **Robustness & Interface Design:** The public interface of each component must be elegant and idiomatic to the target language. The observer must accept arbitrary state/event/error values and render them via their own string representation. Locale support must degrade gracefully (an unrecognized language is simply unsupported, not a crash). Errors should be modeled with proper types rather than generic faults.

---

## Core Features

### Feature [a specific singleton integer value]: Global State-Management Observer

**As a developer**, I want a single observer that logs every state transition and every error from all of my state machines in one consistent format, so I can trace application behavior without scattering print statements through my code.

**Expected Behavior / Usage:**

The observer is notified by the runtime whenever any state machine moves from one state to the next, and whenever any state machine raises an error. It writes exactly one log line per notification to the standard output stream. It performs no filtering, batching, or decoration beyond the formats described below.

*[a specific singleton integer value].[a specific singleton integer value] Transition logging — emits one labelled line per state transition*

When the observer receives a transition, it logs a single line that names all three components of the transition: the prior state, the triggering event, and the resulting next state. The line uses the fixed shape `Transition { currentState: <current>, event: <event>, nextState: <next> }`, where each placeholder is replaced by the string representation of the corresponding value. Exactly one trailing newline terminates the line.

**Test Cases:** `rcb_tests/public_test_cases/feature[a specific singleton integer value]_[a specific singleton integer value]_observer_transition.json`

```json
{
    "description": "The global state-management observer renders every state transition it receives as a single human-readable log line. Given the prior state, the triggering event, and the resulting next state, it emits one line naming all three fields in a fixed, labelled format.",
    "cases": [
        {
            "input": {"currentState": "A", "event": "E", "nextState": "B"},
            "expected_output": "Transition { currentState: A, event: E, nextState: B }\n"
        },
        {
            "input": {"currentState": "TodosLoading", "event": "LoadTodos", "nextState": "TodosLoaded"},
            "expected_output": "Transition { currentState: TodosLoading, event: LoadTodos, nextState: TodosLoaded }\n"
        }
    ]
}
```

*[a specific singleton integer value].2 Error logging — emits the raw error message as one line*

When the observer receives an error, it logs the error's own string representation verbatim as a single line, with no prefix, suffix, or wrapping. Exactly one trailing newline terminates the line.

**Test Cases:** `rcb_tests/public_test_cases/feature[a specific singleton integer value]_2_observer_error.json`

```json
{
    "description": "The global state-management observer renders every error it receives by emitting the error's own message as a single log line, with no extra decoration.",
    "cases": [
        {
            "input": {"error": "whoops"},
            "expected_output": "whoops\n"
        },
        {
            "input": {"error": "Exception: oops"},
            "expected_output": "Exception: oops\n"
        }
    ]
}
```

---

### Feature 2: Localization Provider

**As a developer**, I want a centralized provider that supplies the application title and decides which locales are supported, so every screen resolves text and locales identically.

**Expected Behavior / Usage:**

*2.[a specific singleton integer value] Application title — returns the fixed product title*

The provider exposes the application's display title. It takes no input and returns the product title string. The output is rendered as `app_title=<title>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_[a specific singleton integer value]_app_title.json`

```json
{
    "description": "The localization provider exposes the application's display title. With no input it returns the fixed product title string.",
    "cases": [
        {
            "input": {},
            "expected_output": "app_title=Bloc Library Example\n"
        }
    ]
}
```

*2.2 Reload decision — reports whether cached strings must be rebuilt*

When the active localization delegate is replaced, the runtime asks whether previously resolved strings need to be rebuilt. Because the provided strings are static and never change at runtime, the answer is always negative. The output is rendered as `should_reload=<bool>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_should_reload.json`

```json
{
    "description": "The localization delegate reports whether cached localized resources must be rebuilt when the delegate is replaced. Because the provided strings are static, it always reports that no reload is required.",
    "cases": [
        {
            "input": {},
            "expected_output": "should_reload=false\n"
        }
    ]
}
```

*2.3 Locale support — decides whether a requested locale is supported*

Given a requested locale described by a language code and an optional region/country code, the provider decides whether that locale is supported. Support is granted whenever the language is English, irrespective of region; any other language is unsupported. The output echoes the requested locale label (`<language>` or `<language>_<region>`) on one line and the boolean decision on the next.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_language_support.json`

```json
{
    "description": "The localization delegate decides whether a requested locale is supported. Support is granted when the locale's language is English (regardless of region), and denied otherwise. The output echoes the requested locale label and the support decision.",
    "cases": [
        {
            "input": {"language_code": "en", "country_code": "US"},
            "expected_output": "language=en_US\nsupported=true\n"
        },
        {
            "input": {"language_code": "fr", "country_code": "FR"},
            "expected_output": "language=fr_FR\nsupported=false\n"
        }
    ]
}
```

---

### Feature 3: Loading Indicator Component

**As a developer**, I want a drop-in component that renders the standard "loading" spinner, so I can show a consistent busy state while data is being fetched without rebuilding the widget each time.

**Expected Behavior / Usage:**

When mounted, the component renders a single circular progress spinner, horizontally and vertically centered within its parent. The component forwards the caller-provided identity key to its rendered output so it can be located in a widget tree. The output reports, as count fields, how many widgets carry that identity key, how many circular progress spinners are present, and how many centering containers wrap them — all of which are expected to be exactly one for a correct render.

**Test Cases:** `rcb_tests/public_test_cases/feature3_[a specific singleton integer value]_loading_indicator.json`

```json
{
    "description": "The loading-indicator component renders a centered circular progress spinner when mounted. The output reports how many widgets carry the caller-provided identity key, how many circular progress spinners are present, and how many centering containers wrap them.",
    "cases": [
        {
            "input": {},
            "expected_output": "keyed_widget_count=[a specific singleton integer value]\ncircular_progress_indicator_count=[a specific singleton integer value]\ncenter_count=[a specific singleton integer value]\n"
        }
    ]
}
```

---

## Deliverables

[a specific singleton integer value]. **The Core System:** A cleanly structured codebase implementing the observer logging, localization provider, and loading-indicator component described above. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint — small but logically separated, never a single god file.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads a JSON command (the `input` shape above), invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts. This adapter must be logically (and ideally physically) separated from the core domain. Errors must be normalized to language-neutral category lines rather than leaking host-language runtime artifacts.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature[a specific singleton integer value]_[a specific singleton integer value]_observer_transition.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature[a specific singleton integer value]_[a specific singleton integer value]_observer_transition@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the counting convention established in C007
