## Product Requirement Document

# Interactive Guided-Tour Engine — Step Sequencing, Navigation, and Event Notification

## Project Goal

Build a reusable engine for driving an interactive product walkthrough: an ordered collection of "steps" that a user advances through one at a time, with the surrounding application able to react to lifecycle changes. The engine lets developers describe a guided tour declaratively and control its progression (start, advance, go back, jump, finish) so they do not have to hand-roll step bookkeeping, conditional skipping, and event wiring for every onboarding flow.

---

## Background & Problem

Walking a user through an unfamiliar interface usually means showing a short series of contextual callouts, one after another, and advancing as the user reads each one. Without a shared engine, every application re-implements the same fiddly bookkeeping: which step is currently shown, how to move forward and backward, how to skip a step that is not currently relevant, what happens when the user reaches the end, and how the rest of the app finds out that the tour started, changed, or finished.

This engine provides one well-defined contract for that bookkeeping. It maintains an ordered list of steps (each identified by a stable id and carrying display options such as a title), tracks exactly one "current" step at a time, and exposes navigation operations. It supports conditional steps that are skipped when a supplied predicate says they should not be shown, automatically finishes the tour when the user advances past the last step, and ignores requests to jump to a step that does not exist. Throughout, it emits lifecycle notifications (a step being shown, the tour completing, the tour going inactive) so the host application can respond. Underpinning all of this is a small general-purpose publish/subscribe notifier that the engine itself uses and that is also useful on its own.

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

### Feature 1: Event Subscription & Notification

**As a developer**, I want a small publish/subscribe notifier that lets me register callbacks under named event keys and fire them on demand, so I can decouple the code that raises an event from the code that reacts to it.

**Expected Behavior / Usage:**

A notifier holds, per string event key, an ordered list of registered callbacks. Registering a callback adds it to the end of that key's list. Firing (triggering) an event invokes every callback currently registered under that key, in the order they were registered, passing along the event's extra argument so each callback receives it. A *one-shot* registration behaves like a normal registration except it is automatically removed immediately after it runs once, so a second firing of that key does not invoke it again. Unregistering with only an event key removes every callback registered under that key. Unregistering with an event key plus a specific callback removes only that one callback, leaving the others intact. Firing an event key that currently has no registered callbacks does nothing and is not an error.

Each test case is a sequence of operations. A registration op (`on`) or one-shot registration op (`once`) names an `event` and an `id` for the callback. An unregister op (`off`) names an `event` and optionally an `id`. A fire op (`trigger`) names an `event` and may carry an `arg`. For every fire op, the output reports one line `trigger <event>: <list>`, where `<list>` is the comma-separated ids of the callbacks that ran, in order, each annotated with the value it received as `<id>=<arg>` (just `<id>` when no argument was supplied), or the literal `(none)` when no callback ran.

**Test Cases:** `rcb_tests/public_test_cases/feature1_event_system.json`

```json
{
    "description": "A reusable publish/subscribe notifier. Callers register named callbacks against string event keys, then fire an event to invoke every callback currently registered for that key, in registration order, forwarding the event's extra argument to each callback. A one-shot registration runs at most once and is then automatically discarded. Unregistering by event key alone removes every callback for that key; unregistering by event key plus a specific callback removes only that callback. Firing an event with no registered callbacks does nothing. Each case is a sequence of operations; for every fire operation the scenario reports the event name and the ordered list of callbacks that ran (with the value each received), or `(none)` when nothing ran.",
    "cases": [
        {
            "input": {"feature": "events", "ops": [
                {"op": "on", "event": "go", "id": "h1"},
                {"op": "on", "event": "go", "id": "h2"},
                {"op": "trigger", "event": "go", "arg": "A"}
            ]},
            "expected_output": "trigger go: h1=A,h2=A\n"
        },
        {
            "input": {"feature": "events", "ops": [
                {"op": "once", "event": "go", "id": "h1"},
                {"op": "trigger", "event": "go", "arg": "1"},
                {"op": "trigger", "event": "go", "arg": "2"}
            ]},
            "expected_output": "trigger go: h1=1\ntrigger go: (none)\n"
        }
    ]
}
```

---

### Feature 2: Attach-Target Specification Parsing

**As a developer**, I want to declare which on-page element a step points at, and from which side, using a compact spelling, so I can configure step placement without verbose objects.

**Expected Behavior / Usage:**

A step's attach-target may be given two ways. As a **string** of the form `<selector> <placement>`: everything up to the final whitespace-separated token is the element selector, and the final token is the placement side. The placement must be one of `auto`, `top`, `left`, `right`, or `bottom`, optionally suffixed with `-start` or `-end` (for example `top-start`). If the final token is not a recognized placement, the whole specification is rejected. As an **object** that already carries an `element` and an `on` (placement) field: it is accepted as given. An object that is missing either field is rejected.

The input is `{ "feature": "attachTo", "spec": <string | object> }`. For an accepted specification the output is two lines, `element=<selector>` then `on=<placement>`. For a rejected specification the output is the single line `none`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_attach_target.json`

```json
{
    "description": "Normalizes a step's attach-target specification into a canonical form with two fields: the target element selector and the placement side. The specification may be supplied either as a single shorthand string of the form `<selector> <placement>` or as an object that already carries both fields. For the string form, the placement must be one of the recognized sides (auto, top, left, right, bottom), optionally suffixed with `-start` or `-end`; the leading portion is taken as the selector. A string whose trailing token is not a recognized placement is rejected. For the object form, the object is accepted as-is only when it carries both an element and a placement; otherwise it is rejected. Accepted specifications report the element selector and placement; rejected ones report `none`.",
    "cases": [
        {
            "input": {"feature": "attachTo", "spec": ".foo bottom"},
            "expected_output": "element=.foo\non=bottom\n"
        },
        {
            "input": {"feature": "attachTo", "spec": ".foo notValid"},
            "expected_output": "none\n"
        }
    ]
}
```

---

### Feature 3: Shorthand Field Mapping

**As a developer**, I want a compact space-separated string to expand into a named-field object given the field order, so configuration options can accept a terse spelling while the engine works with structured data.

**Expected Behavior / Usage:**

Given a value and an ordered list of field names, the mapping behaves as follows. When the value is a space-separated **string**, it is split on whitespace and its tokens are assigned positionally to the field names, producing an object whose first field name maps to the first token, second to the second, and so on. When the value is already an **object**, it is returned unchanged. When the value is **null**, it stays null. When the value is **absent** (undefined), it stays undefined.

The input is `{ "feature": "shorthand", "value": <string | object | null>, "props": [<field names>] }`; omit the `value` key to represent the absent/undefined case. The output reports the resulting object as `name=value` lines in the requested field order; or the single literal line `null` or `undefined` for those pass-through cases.

**Test Cases:** `rcb_tests/public_test_cases/feature3_shorthand.json`

```json
{
    "description": "Expands a shorthand option value into a keyed object given an ordered list of field names. When the value is a space-separated string, its whitespace-separated tokens are zipped positionally onto the provided field names, producing an object that maps each field name to its corresponding token. When the value is already an object, it is returned unchanged. When the value is null it stays null, and when the value is absent (undefined) it stays undefined. Each case reports the resulting fields as `name=value` lines in the requested field order, or the literal `null` / `undefined` for the pass-through cases.",
    "cases": [
        {
            "input": {"feature": "shorthand", "value": ".foo click", "props": ["selector", "event"]},
            "expected_output": "selector=.foo\nevent=click\n"
        },
        {
            "input": {"feature": "shorthand", "props": ["selector", "event"]},
            "expected_output": "undefined\n"
        }
    ]
}
```

---

### Feature 4: Tour Navigation & Lifecycle

**As a developer**, I want to drive a tour through its ordered steps and observe the lifecycle, so the surrounding app can keep in sync with which step is showing and when the tour ends.

**Expected Behavior / Usage:**

A tour owns an ordered list of steps, each identified by an `id` and carrying display options (such as a `title` and body `text`). Exactly one step is "current" at any time, or none before the tour starts and after it ends. The engine emits a **show** notification each time a step becomes current, carrying both the step now being shown and the step that was previously current. The driver below is shared by all sub-features: the input is `{ "feature": "tour", "steps": [ ... ], "actions": [ ... ] }`, where each step is `{ "id", "title"?, "text"?, "showOn"? }` (`showOn` is a boolean that, when present and false, marks a step that should be skipped). Each action is one of: `{"do":"start"}`, `{"do":"next"}`, `{"do":"back"}`, `{"do":"show","key":<id>}`, `{"do":"current"}`, `{"do":"count"}`, `{"do":"byId","id":<id>}`, `{"do":"isActive"}`, `{"do":"addStep","step":{...}}`, `{"do":"removeStep","id":<id>}`. Output lines are emitted as they occur: a show notification prints `show <current> previous=<previous>` (using `none` when there is no previous); a `current` query prints `current=<id>` (or `current=none`); an `isActive` query prints `active=<true|false>`; completion prints `complete`; deactivation prints `inactive`.

*4.1 Sequential Navigation — moving forward and backward through steps in order*

Starting the tour activates it and shows the first step. Advancing moves to the next step in list order; going back moves to the previous step in list order. Each move produces a show notification whose `previous` is the step that had been current (or `none` for the very first show at start).

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_navigation.json`

```json
{
    "description": "Sequential forward/backward navigation across an ordered list of steps. Starting the tour activates and shows the first step. Advancing moves to the next step in order; going back moves to the previous step. Each transition fires a show notification carrying the step being shown and the step that was previously current (or `none` at the start). The scenario interleaves navigation commands with queries of the currently-shown step, reporting each show notification as `show <current> previous=<previous>` and each query as `current=<id>`.",
    "cases": [
        {
            "input": {"feature": "tour", "steps": [
                {"id": "a", "title": "Step A", "text": "First"},
                {"id": "b", "title": "Step B", "text": "Second"},
                {"id": "c", "title": "Step C", "text": "Third"}
            ], "actions": [
                {"do": "start"}, {"do": "current"},
                {"do": "next"}, {"do": "current"},
                {"do": "back"}, {"do": "current"}
            ]},
            "expected_output": "show a previous=none\ncurrent=a\nshow b previous=a\ncurrent=b\nshow a previous=b\ncurrent=a\n"
        }
    ]
}
```

*4.2 Conditional Step Skipping — bypassing a step whose predicate says not to show it*

A step may declare a visibility predicate. When navigation would land on such a step and its predicate evaluates to false, the step is bypassed and navigation continues to the following step in the direction of travel. The skipped step never becomes current and produces no show notification of its own.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_conditional_skip.json`

```json
{
    "description": "Conditional step skipping during navigation. A step may declare a visibility predicate; when that predicate evaluates to false at navigation time, the step is bypassed and navigation continues to the following step in the travel direction. Steps without a predicate are always eligible. The scenario places a skipped (predicate-false) step between two eligible steps and advances forward, reporting each shown step as `show <current> previous=<previous>` and each query as `current=<id>` so the skipped step never appears as current.",
    "cases": [
        {
            "input": {"feature": "tour", "steps": [
                {"id": "a", "title": "Step A", "text": "First"},
                {"id": "hidden", "title": "Hidden", "text": "Skipped", "showOn": false},
                {"id": "b", "title": "Step B", "text": "Second"}
            ], "actions": [
                {"do": "start"}, {"do": "current"},
                {"do": "next"}, {"do": "current"}
            ]},
            "expected_output": "show a previous=none\ncurrent=a\nshow b previous=a\ncurrent=b\n"
        }
    ]
}
```

*4.3 Completion on Advancing Past the Last Step — finishing the tour automatically*

When the current step is the last in the list, advancing does not move to another step. Instead the tour completes: it fires a completion notification, then an inactivation notification, and the tour becomes inactive.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_complete_on_last.json`

```json
{
    "description": "Advancing past the final step finishes the tour. When the currently-shown step is the last in the list, the advance command does not move to another step; instead it completes the tour, which fires a completion notification followed by an inactivation notification and deactivates the tour. The scenario navigates to the last step and then advances once more, reporting show notifications as `show <current> previous=<previous>`, the lifecycle notifications as `complete` and `inactive`, and current-step queries as `current=<id>`.",
    "cases": [
        {
            "input": {"feature": "tour", "steps": [
                {"id": "a", "title": "Step A", "text": "First"},
                {"id": "b", "title": "Step B", "text": "Second"}
            ], "actions": [
                {"do": "start"}, {"do": "show", "key": "b"}, {"do": "current"},
                {"do": "next"}, {"do": "isActive"}
            ]},
            "expected_output": "show a previous=none\nshow b previous=a\ncurrent=b\ncomplete\ninactive\nactive=false\n"
        }
    ]
}
```

*4.4 Jumping to an Unknown Step — a no-op*

Requesting a jump to a key that matches no step does nothing: no show notification fires and the current step is left unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_unknown_step.json`

```json
{
    "description": "Requesting a step by a key that does not match any step is a no-op. When a show command names an unknown step, no show notification fires and the currently-shown step is left unchanged. The scenario starts the tour, requests a non-existent step, and verifies via current-step queries that the current step did not change and that no extra show notification was emitted; show notifications are reported as `show <current> previous=<previous>` and queries as `current=<id>`.",
    "cases": [
        {
            "input": {"feature": "tour", "steps": [
                {"id": "a", "title": "Step A", "text": "First"},
                {"id": "b", "title": "Step B", "text": "Second"}
            ], "actions": [
                {"do": "start"}, {"do": "current"},
                {"do": "show", "key": "does-not-exist"}, {"do": "current"}
            ]},
            "expected_output": "show a previous=none\ncurrent=a\ncurrent=a\n"
        }
    ]
}
```

---

### Feature 5: Step Collection Management

**As a developer**, I want to add steps to a tour and look them up or remove them by id, so I can build and mutate the tour's contents programmatically.

**Expected Behavior / Usage:**

The driver and output conventions are identical to Feature 4.

*5.1 Adding and Retrieving Steps — building the collection and looking up by id*

Steps are appended to the tour's ordered collection in the order added, and the collection size grows accordingly. A step can be looked up by its id, yielding the matching step (from which its title is read) or nothing when no step matches. Steps added after construction immediately join the collection and become retrievable. A `count` action reports the current size as `count=<n>`; a `byId` lookup reports `byId <id> title=<title>`, or `byId <id> title=missing` when no step matches.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_add_get.json`

```json
{
    "description": "Adding steps to a tour and retrieving them by identifier. Steps are appended to the tour's ordered collection and can later be looked up by their identifier, returning the matching step (from which its title can be read) or nothing when no step matches. New steps can be added after construction and immediately become part of the collection and retrievable. The scenario reports the collection size as `count=<n>`, and each lookup as `byId <id> title=<title>` (or `title=missing` when no step matches).",
    "cases": [
        {
            "input": {"feature": "tour", "steps": [
                {"id": "welcome", "title": "Welcome", "text": "Hi"},
                {"id": "details", "title": "Details", "text": "More"}
            ], "actions": [
                {"do": "count"},
                {"do": "byId", "id": "welcome"},
                {"do": "byId", "id": "details"},
                {"do": "byId", "id": "nope"},
                {"do": "addStep", "step": {"id": "finish", "title": "Finish", "text": "Done"}},
                {"do": "count"},
                {"do": "byId", "id": "finish"}
            ]},
            "expected_output": "count=2\nbyId welcome title=Welcome\nbyId details title=Details\nbyId nope title=missing\ncount=3\nbyId finish title=Finish\n"
        }
    ]
}
```

*5.2 Removing Steps — dropping a step and re-showing when the current one is removed*

Removing a step by id drops it from the collection and shrinks the size by one. Removing a step that is not currently shown leaves the current step unchanged. Removing the step that IS currently shown drops it and, as long as other steps remain, automatically shows the first remaining step (its show notification has no previous, i.e. `previous=none`).

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_remove.json`

```json
{
    "description": "Removing steps from a tour by identifier. Removing a step that is not currently shown simply drops it from the collection, shrinking the size by one and leaving the currently-shown step unchanged. Removing the step that is currently shown drops it and, while other steps remain, automatically shows the first remaining step. The scenario removes a non-current step and then the current step, reporting the collection size as `count=<n>`, each current-step query as `current=<id>`, and each automatic transition as `show <current> previous=<previous>`.",
    "cases": [
        {
            "input": {"feature": "tour", "steps": [
                {"id": "a", "title": "Step A", "text": "First"},
                {"id": "b", "title": "Step B", "text": "Second"},
                {"id": "c", "title": "Step C", "text": "Third"}
            ], "actions": [
                {"do": "start"}, {"do": "current"},
                {"do": "removeStep", "id": "b"}, {"do": "count"}, {"do": "current"},
                {"do": "removeStep", "id": "a"}, {"do": "current"}, {"do": "count"}
            ]},
            "expected_output": "show a previous=none\ncurrent=a\ncount=2\ncurrent=a\nshow c previous=none\ncurrent=c\ncount=1\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_event_system.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_event_system@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- match the internal ordering of the 'props' object in the core module
- trigger when the step index equals the total list length minus one
