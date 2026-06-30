## Product Requirement Document

# Array Field Binding Toolkit for Reactive Forms - Behavioral Specification

## Project Goal

Build a reactive-form array-field binding that lets developers render and edit a variable-length list of values (or structured objects) inside a form, exposing the list as an addressable, iterable collection of named child fields. Each item is bound to its own input by a stable, index-derived name, and the surrounding form's value tree stays in sync as items are added, edited, or reordered — without the developer hand-writing index bookkeeping or wiring re-subscription logic.

---

## Background & Problem

Without this binding, developers wiring an editable list into a form must manually fabricate a unique field name for every element (`people[0].firstName`, `people[1].firstName`, …), keep that naming in lockstep with the underlying array as items are inserted or removed, and re-register the list with the form engine whenever the bound name changes. This leads to repetitive, error-prone boilerplate: off-by-one bugs in generated names, stale subscriptions after a rename, lists whose length silently drifts from the form state, and validators that never see the array as a whole.

With this binding, the developer declares a single array field by name, picks a render strategy, and receives a ready-made field bundle: the current item count, the live array value, helpers to iterate or project over the items (each yielding a correctly indexed child-field name), and mutation helpers to grow or shrink the list. The binding handles name generation, length tracking, re-subscription on rename, and array-level validation, so the developer focuses only on what each row looks like.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain has several distinct responsibilities (subscription-difference logic, the array-field view/binding, a render-strategy resolver, and the execution adapter). It MUST NOT be a single "god file": separate the pure predicate logic, the field-binding component, the render dispatch, and the adapter into distinct units. Do not over-engineer, but avoid a monolith.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in "Core Features" are a **black-box contract** for the execution adapter, NOT the internal data model. The core binding logic must remain completely decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls against the core binding and rendering observed results to stdout.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Keep subscription diffing, render-strategy resolution, field-bundle construction, validation handling, and output formatting in distinct logical units.
   - **Open/Closed Principle (OCP):** New render strategies or mutation helpers should be addable without rewriting the core binding.
   - **Liskov Substitution Principle (LSP):** Any supported render strategy must be substitutable for another wherever a renderable is accepted.
   - **Interface Segregation Principle (ISP):** The field bundle's iteration, mutation, and metadata surfaces should be cohesive and not force consumers to depend on parts they do not use.
   - **Dependency Inversion Principle (DIP):** The binding depends on an abstract form context, not on a concrete I/O implementation.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface must be elegant and idiomatic to the target language, hiding internal subscription and indexing complexity.
   - **Resilience:** Misuse (no form context, no render strategy, missing mutation helpers) must be reported through clear, normalized developer-facing signals rather than crashing or silently doing nothing.

---

## Core Features

### Feature 1: Subscription Difference Predicate

**As a developer**, I want a predicate that decides whether two optional subscription descriptors differ over a chosen set of keys, so I can avoid re-registering a field with the form engine unless something it actually cares about changed.

**Expected Behavior / Usage:**

The predicate takes two optional subscription maps (`a` and `b`, each either absent/null or an object of key→flag) and a list of keys to compare. It answers a single boolean "do these differ?" question under these rules: if exactly one of the two maps is present and the other is absent, they differ; if both are absent, they do not differ; if both are present, they differ only when at least one of the listed keys holds a non-identical value between the two maps (keys not in the list are ignored). The contract also surfaces, for transparency, whether each side was present. Output lines: `a_present`, `b_present`, then `differs`, each `true`/`false`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_subscription_diff.json`

```json
{
    "description": "Compares two optional field-subscription maps over a fixed key set to decide whether a re-subscription is needed. Reports whether each side is present and whether the selected keys differ. A present map versus an absent one always differs; two absent maps do not differ; two present maps differ only when at least one listed key holds a different value.",
    "cases": [
        {
            "input": {"op": "subscription_diff", "a": null, "b": {}, "keys": ["foo"]},
            "expected_output": "a_present=false\nb_present=true\ndiffers=true\n"
        },
        {
            "input": {"op": "subscription_diff", "a": {}, "b": null, "keys": ["foo"]},
            "expected_output": "a_present=true\nb_present=false\ndiffers=true\n"
        },
        {
            "input": {"op": "subscription_diff", "a": {"foo": 2, "bar": 5}, "b": {"foo": 2, "bar": 5}, "keys": ["foo", "bar"]},
            "expected_output": "a_present=true\nb_present=true\ndiffers=false\n"
        },
        {
            "input": {"op": "subscription_diff", "a": {"foo": 2, "bar": 5}, "b": {"foo": 2, "bar": 4}, "keys": ["foo", "bar"]},
            "expected_output": "a_present=true\nb_present=true\ndiffers=true\n"
        }
    ]
}
```

---

### Feature 2: Render Strategy Resolution

**As a developer**, I want to supply the row/list view through any one of three interchangeable strategies — a component, a render function passed as a dedicated prop, or a render function passed as children — so I can use whichever style fits my codebase, all receiving the same field bundle.

**Expected Behavior / Usage:**

The array field accepts exactly one render strategy and invokes it with the field bundle (which carries the current item count among other things). For a static initial list the strategy is invoked, and the bundle's reported item count equals the number of items in the initial list (including zero for an empty list). All three strategies are mutually substitutable and produce the same observable result for the same input. Output lines: `rendered` (`true`/`false`) and `length` (the item count).

**Test Cases:** `rcb_tests/public_test_cases/feature2_render_strategy.json`

```json
{
    "description": "Renders the array field through any one of the supported render strategies (a component prop, a render-function prop, or a function passed as children). Each strategy receives the same field bundle and is invoked exactly once for a static initial array; the reported length reflects the number of items in the initial array.",
    "cases": [
        {
            "input": {"op": "render_strategy", "name": "foo", "strategy": "component", "initialValues": {"foo": ["x", "y"]}},
            "expected_output": "rendered=true\nlength=2\n"
        },
        {
            "input": {"op": "render_strategy", "name": "foo", "strategy": "render", "initialValues": {"foo": ["x"]}},
            "expected_output": "rendered=true\nlength=1\n"
        },
        {
            "input": {"op": "render_strategy", "name": "foo", "strategy": "children", "initialValues": {"foo": []}},
            "expected_output": "rendered=true\nlength=0\n"
        }
    ]
}
```

---

### Feature 3: Misuse Diagnostics

**As a developer**, I want clear, normalized diagnostics when I wire the array field incorrectly, so I can immediately tell which precondition I violated instead of debugging a silent failure.

**Expected Behavior / Usage:**

The binding detects three distinct misuse conditions and, for each, emits exactly one diagnostic whose category is a stable, language-neutral identifier. The contract reports the number of diagnostics emitted (`warnings=<n>`) followed by one `warning=<category>` line per diagnostic.

*3.1 Missing Form Context — the field is used with no surrounding form*

When the array field is mounted with no enclosing form context to register against, it emits one diagnostic categorized as `[a specific missing context key string — verify against implementation constants]`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_warn_no_form.json`

```json
{
    "description": "When the array field is mounted outside of any surrounding form context, it emits exactly one developer warning whose normalized category signals that a form context is required. The warning count and category are reported.",
    "cases": [
        {
            "input": {"op": "warnings", "scenario": "no_form"},
            "expected_output": "warnings=1\nwarning=[a specific missing context key string — verify against implementation constants]\n"
        }
    ]
}
```

*3.2 Missing Render Strategy — no component, render prop, or children function supplied*

When the array field is inside a form but no render strategy is provided, it emits one diagnostic categorized as `[the specific category code for missing render strategy — check constants file]`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_warn_no_render.json`

```json
{
    "description": "When the array field is mounted inside a form but no render strategy (component, render prop, or children function) is supplied, it emits exactly one developer warning whose normalized category signals that a render strategy is missing.",
    "cases": [
        {
            "input": {"op": "warnings", "scenario": "no_render"},
            "expected_output": "warnings=1\nwarning=[the specific category code for missing render strategy — check constants file]\n"
        }
    ]
}
```

*3.3 Missing Array Mutators — the form was configured without the array-mutation helpers*

When the array field is inside a form whose configuration lacks the array-mutation helpers, it emits one diagnostic categorized as `missing_array_mutators`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_warn_no_mutators.json`

```json
{
    "description": "When the array field is mounted inside a form whose configuration lacks the array-mutation helpers, it emits exactly one developer warning whose normalized category signals that the array mutators were not provided.",
    "cases": [
        {
            "input": {"op": "warnings", "scenario": "no_mutators"},
            "expected_output": "warnings=1\nwarning=missing_array_mutators\n"
        }
    ]
}
```

---

### Feature 4: Always-Available Item Count

**As a developer**, I want the current item count to be available on the field bundle even when I subscribe only to unrelated metadata, so I can render the right number of rows without having to subscribe to the whole value.

**Expected Behavior / Usage:**

The item count is always present on the field bundle regardless of how narrow the field's subscription is. With a subscription limited to a single unrelated metadata flag, the bundle still reports `length` equal to the number of items in the initial array, and the subscribed flag is also reported. For a freshly initialized, untouched array the `dirty` flag is `false`. Output lines: `length` then the requested metadata flag.

**Test Cases:** `rcb_tests/public_test_cases/feature4_length_always_present.json`

```json
{
    "description": "The current item count of the array is always available on the field bundle even when the field subscribes only to an unrelated metadata flag (here a 'dirty' subscription). The reported length equals the number of items in the initial array, and the subscribed metadata flag is reported alongside it (a pristine, untouched array is not dirty).",
    "cases": [
        {
            "input": {"op": "array_state", "name": "foo", "subscription": {"dirty": true}, "initialValues": {"foo": ["a", "b"]}, "report": ["length", "dirty"]},
            "expected_output": "length=2\ndirty=false\n"
        },
        {
            "input": {"op": "array_state", "name": "foo", "subscription": {"dirty": true}, "initialValues": {"foo": ["a", "b", "c", "d"]}, "report": ["length", "dirty"]},
            "expected_output": "length=4\ndirty=false\n"
        }
    ]
}
```

---

### Feature 5: Item Iteration Helper

**As a developer**, I want a helper that visits every item in order and hands me each item's generated field name and position, so I can render or process rows without computing index-based names myself.

**Expected Behavior / Usage:**

The field bundle exposes an iteration helper that invokes a callback once per item, in order, passing two arguments: the item's field name (the array's name followed by a bracketed zero-based index) and the numeric index. The helper returns no value. The contract emits one `name=index` line per visited item followed by a `return` line reporting the (absent) return value.

**Test Cases:** `rcb_tests/public_test_cases/feature5_for_each.json`

```json
{
    "description": "The field bundle exposes an iteration helper that invokes a callback once per array item, in order, passing the indexed field name (parent name with a bracketed index suffix) and the zero-based position. The helper returns no value. Each emitted line records one visited name and its index; the final line reports the (absent) return value.",
    "cases": [
        {
            "input": {"op": "for_each", "name": "foo", "initialValues": {"foo": ["a", "b", "c"]}},
            "expected_output": "foo[0]=0\nfoo[1]=1\nfoo[2]=2\nreturn=undefined\n"
        },
        {
            "input": {"op": "for_each", "name": "foo", "initialValues": {"foo": ["x"]}},
            "expected_output": "foo[0]=0\nreturn=undefined\n"
        }
    ]
}
```

---

### Feature 6: Item Projection Helper

**As a developer**, I want a helper that maps every item to a value and collects the results in order, so I can build a list of rendered rows keyed by each item's generated field name.

**Expected Behavior / Usage:**

The field bundle exposes a mapping helper that invokes a callback once per item, in order, passing the item's field name (array name with bracketed zero-based index) and the numeric index, and collects each callback's return value into a new ordered array. The contract emits one `name=index` line per visited item, then a `result` line carrying the JSON-encoded array of collected results (here the upper-cased field names).

**Test Cases:** `rcb_tests/public_test_cases/feature6_map.json`

```json
{
    "description": "The field bundle exposes a mapping helper that invokes a callback once per array item, in order, passing the indexed field name (parent name with a bracketed index suffix) and the zero-based position, and collects the callback's return values into a new array preserving order. Each emitted line records one visited name and its index; the final line reports the JSON-encoded array of results (here the upper-cased indexed names).",
    "cases": [
        {
            "input": {"op": "map", "name": "foo", "initialValues": {"foo": ["a", "b", "c"]}},
            "expected_output": "foo[0]=0\nfoo[1]=1\nfoo[2]=2\nresult=[\"FOO[0]\",\"FOO[1]\",\"FOO[2]\"]\n"
        },
        {
            "input": {"op": "map", "name": "foo", "initialValues": {"foo": ["a", "b"]}},
            "expected_output": "foo[0]=0\nfoo[1]=1\nresult=[\"FOO[0]\",\"FOO[1]\"]\n"
        }
    ]
}
```

---

### Feature 7: Array-Level Validation

**As a developer**, I want to attach a validator that sees the whole array value and can flag the list as invalid with a message, so I can enforce constraints (like a maximum number of items) on the collection as a unit.

**Expected Behavior / Usage:**

A validator may be attached that receives the entire array value and returns an error message when the array violates a constraint, or nothing when it is valid. The result surfaces on the array's metadata: a valid array reports a valid flag of `true` and no error; once a mutation pushes the array past the constraint, it reports valid `false` and the validator's message. If the array already satisfies the constraint and no mutation occurs, it stays valid with no error. Output lines: `valid_initial`, `error_initial`, then `valid_final`, `error_final`. Error values are reported as the validator's own message string (JSON-encoded), or `undefined` when there is none.

**Test Cases:** `rcb_tests/public_test_cases/feature7_array_validation.json`

```json
{
    "description": "An array-level validator may be attached that receives the whole array value and returns an error message when the array violates a constraint (here a maximum length), or no message when it is valid. The validator result surfaces on the array's metadata: a valid array reports a valid flag of true and no error; after an item is appended that exceeds the limit, the array reports valid false and the validator's error message. When the array already satisfies the constraint and no mutation occurs, it stays valid with no error.",
    "cases": [
        {
            "input": {"op": "validate", "name": "foo", "initialValues": {"foo": ["a", "b"]}, "validateMaxLength": 2, "validateError": "Too long", "actions": [{"type": "push", "value": "c"}]},
            "expected_output": "valid_initial=true\nerror_initial=undefined\nvalid_final=false\nerror_final=\"Too long\"\n"
        },
        {
            "input": {"op": "validate", "name": "foo", "initialValues": {"foo": []}, "validateMaxLength": 2, "validateError": "Too long", "actions": []},
            "expected_output": "valid_initial=true\nerror_initial=undefined\nvalid_final=true\nerror_final=undefined\n"
        }
    ]
}
```

---

### Feature 8: Item Mutation & Per-Item Input Binding

**As a developer**, I want to append items to the list and have each item bind to its own input(s) by a generated name, so editing one row updates only that row and the form value stays consistent.

**Expected Behavior / Usage:**

Appending an item grows the list length by one and produces a new addressable child field bound to a fresh input. Editing an existing item's input changes only that item; later-appended items remain empty. Item field names follow the parent-name-with-bracketed-index convention, and structured (object) items expose one input per sub-property, each named with the item path followed by a dotted sub-property name.

*8.1 Scalar Items — append scalar values and edit them independently*

Starting from an empty list, appending an item, editing its input, then appending another yields a length of 2 with the first input holding the edited value and the second input empty. Output lines: `length`, `inputs=<count>`, then one `name=value` line per input (sorted by name).

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_push_scalar.json`

```json
{
    "description": "Appending an item to the array grows its length by one and renders a corresponding input bound to the new indexed field. Editing the value of an existing item's input updates only that item and leaves later appended items empty. After appending one item, editing it, then appending a second, the array length is 2 and the two inputs hold the edited value and an empty string respectively. The input names follow the parent-name-with-bracketed-index convention.",
    "cases": [
        {
            "input": {"op": "array_state", "name": "foo", "subscription": {}, "initialValues": {"foo": []}, "itemFields": [""], "actions": [{"type": "push", "value": null}, {"type": "change", "name": "foo[0]", "value": "dog"}, {"type": "push", "value": null}], "report": ["length", "inputs"]},
            "expected_output": "length=2\ninputs=2\nfoo[0]=dog\nfoo[1]=\n"
        }
    ]
}
```

*8.2 Object Items — append structured items with independent sub-field inputs*

Appending an empty object item renders one input per declared sub-property, each named with the item path plus a dotted sub-property name; editing one sub-field updates only that sub-field. After appending one object item and editing its first sub-field, the length is 1 and the two nested inputs hold the edited value and an empty string. Output lines: `length`, `inputs=<count>`, then one `name=value` line per input (sorted by name).

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_push_object.json`

```json
{
    "description": "Items may be objects whose sub-properties are bound to independent nested inputs. Appending an empty object renders one input per declared sub-field, each named with the parent item path followed by a dotted sub-property name. Editing one sub-field updates only that sub-field and leaves the sibling sub-field empty. After appending one object item and editing its first sub-field, the array length is 1 and the two nested inputs hold the edited value and an empty string.",
    "cases": [
        {
            "input": {"op": "array_state", "name": "foo", "subscription": {}, "initialValues": {"foo": []}, "itemFields": ["firstName", "lastName"], "actions": [{"type": "push", "value": {}}, {"type": "change", "name": "foo[0].firstName", "value": "Erik"}], "report": ["length", "inputs"]},
            "expected_output": "length=1\ninputs=2\nfoo[0].firstName=Erik\nfoo[0].lastName=\n"
        }
    ]
}
```

---

### Feature 9: Re-subscription on Name Change

**As a developer**, I want the array field to follow a new target array when I change its bound name, so I can repoint the same field at a different list and immediately see that list's value.

**Expected Behavior / Usage:**

When the array field's target name changes, it re-registers against the newly named array and its reported value switches to that array's value. Given a form holding two named arrays, the field bound to the first name reports the first array's value; after the bound name is switched to the second array, the field reports the second array's value. Output line: `value` carrying the JSON-encoded array value.

**Test Cases:** `rcb_tests/public_test_cases/feature9_resubscribe_on_name_change.json`

```json
{
    "description": "The array field re-subscribes to a different array when its target name changes, so its reported value follows the named array. With one form holding two named arrays, the field bound to the first name reports that array's value; after the field's name is switched to the second array, it reports the second array's value.",
    "cases": [
        {
            "input": {"op": "array_state", "name": "dogs", "formSubscription": {}, "initialValues": {"dogs": ["Odie"], "cats": ["Garfield"]}, "report": ["value"]},
            "expected_output": "value=[\"Odie\"]\n"
        },
        {
            "input": {"op": "array_state", "name": "dogs", "formSubscription": {}, "initialValues": {"dogs": ["Odie"], "cats": ["Garfield"]}, "actions": [{"type": "set_name", "name": "cats"}], "report": ["value"]},
            "expected_output": "value=[\"Garfield\"]\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above — the subscription-difference predicate, the array-field binding (item count, value, iteration, projection, mutation, validation, re-subscription), the render-strategy resolver, and the misuse diagnostics. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint: multiple cohesive units, no god file, no over-engineering.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client of the core binding. It reads a single JSON command from stdin, drives the appropriate core logic (mounting the field, performing the listed actions, reading back the requested state), and prints the result to stdout, strictly matching the per-leaf-feature contracts above. The adapter must be logically (and ideally physically) separated from the core domain, and it owns all error normalization — translating any native runtime failure into the neutral category lines defined here (e.g. `error=unknown_op`), never leaking host-language exception identities into stdout.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_subscription_diff.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_subscription_diff@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- matches the 'report' array structure as defined in the array state module
- uses the same naming convention as the for_each loop iteration
