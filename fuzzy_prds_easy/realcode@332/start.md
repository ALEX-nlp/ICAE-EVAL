## Product Requirement Document

# Component Enhancement Toolkit - Declarative Higher-Order Component Utilities

## Project Goal

Build a toolkit of composable component-enhancement utilities that lets developers add, transform, and manage the properties and state flowing into a UI component without hand-writing wrapper components for every concern. Each utility is a small, single-purpose enhancer; enhancers can be chained so that a component's input is shaped by a clear, declarative pipeline instead of nested boilerplate.

---

## Background & Problem

Without this toolkit, developers building UI components are forced to hand-roll wrapper components every time they need to inject a fixed property, supply a fallback value, rename or drop a property, hold a piece of local state, memoize re-renders, or fan an event out to subscribers. Each concern becomes its own bespoke wrapper, the wrappers nest deeply, and the resulting code is repetitive, error-prone, and hard to test in isolation.

With this toolkit, every concern is expressed as a reusable enhancer that takes a component and returns an enhanced component. Enhancers compose into a single flat pipeline, so the same composition primitive drives property shaping, local state, conditional rendering, and stream wiring. Behavior is observable purely through the properties a component finally receives and the markup it finally renders, which keeps each enhancer independently verifiable.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility library (composition core, property transformers, state containers, conditional/structural rendering, and stream utilities). It MUST be organized as a multi-file repository with one focused module per enhancer plus shared internal helpers, not a single monolithic file. Do not over-engineer individual enhancers — most are a few lines — but keep each concern in its own unit.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in "Core Features" are a **black-box contract for the execution adapter**, NOT the internal data model. The core enhancers must know nothing about stdin/stdout or JSON. The execution adapter is solely responsible for translating a JSON command into idiomatic enhancer calls, rendering the resulting component with an in-memory renderer, and formatting the observed result.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Each enhancer does exactly one thing (merge, default, pick, omit, rename, flatten, hold state, memoize, etc.).
   - **Open/Closed Principle (OCP):** New enhancers must be addable without modifying the composition core or existing enhancers.
   - **Liskov Substitution Principle (LSP):** Every enhancer shares the same `Component -> Component` shape and is freely substitutable inside a composition.
   - **Interface Segregation Principle (ISP):** Composition, property shaping, state, and rendering helpers stay small and cohesive.
   - **Dependency Inversion Principle (DIP):** The composition core depends on the abstract enhancer shape, not on any concrete enhancer.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** A single composition primitive should chain any number of enhancers into one enhanced component with an elegant call form.
   - **Resilience:** Misuse (for example, a handler factory that does not return a function) must surface as a well-modeled, normalized error category rather than an unstructured runtime fault.

---

## Core Features

### Feature 1: Right-to-Left Function Composition

**As a developer**, I want to chain a series of single-argument transformers into one function, so I can build an enhancement pipeline from small reusable pieces.

**Expected Behavior / Usage:**

The composer takes an ordered list of named numeric transformers (`double` [a dynamic wrapper pattern involving parentheses and formatted labels] ×2, `square` [a dynamic wrapper pattern involving parentheses and formatted labels] x², `increment` [a dynamic wrapper pattern involving parentheses and formatted labels] +1, `negate`, and the binary `add`) and a seed input, then applies them right to left: the rightmost transformer runs first and feeds the next one to its left. With no transformers the seed is returned unchanged; with exactly one transformer the result is that transformer applied to the seed. The seed is provided as an argument list, so a multi-argument transformer at the rightmost position may consume several seed values. Output is a single `result[a dynamic wrapper pattern involving parentheses and formatted labels]<value>` line.

**Test Cases:** `rcb_tests/public_test_cases/feature1_function_composition.json`

```json
{
    "description": "Right-to-left composition of unary numeric transformers applied to a seed value; with no transformers the seed passes through unchanged, with one it is returned as-is, and the rightmost transformer runs first.",
    "cases": [
        {"input": {"command": "compose_functions", "functions": ["square", "double"], "input": [5]}, "expected_output": "result[a dynamic wrapper pattern involving parentheses and formatted labels]100\n"},
        {"input": {"command": "compose_functions", "functions": ["square"], "input": [5]}, "expected_output": "result[a dynamic wrapper pattern involving parentheses and formatted labels]25\n"},
        {"input": {"command": "compose_functions", "functions": [], "input": [3]}, "expected_output": "result[a dynamic wrapper pattern involving parentheses and formatted labels]3\n"}
    ]
}
```

---

### Feature 2: Component Labels

**As a developer**, I want to derive readable labels for components, so I can debug and display enhanced component trees clearly.

**Expected Behavior / Usage:**

*2.1 Resolve display label — derive a single component's human-facing label*

The resolver returns a component's label using this precedence: an explicitly assigned display label wins; otherwise the component's declared type name is used; an unnamed inline component falls back to the literal string `Component`; and a raw markup tag (a plain string such as `div`) is returned verbatim. The component to inspect is described by a `kind` field: `class_named`/`function_named` (declared name in `name`), `class_display` (explicit label in `display`), `anonymous` (no inferable name), or `dom` (a markup tag in `name`). Output is a single `name[a dynamic wrapper pattern involving parentheses and formatted labels]<json-string>` line.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_resolve_display_name.json`

```json
{
    "description": "Resolve a component's human-facing label: an explicit label wins, otherwise the declared type name is used, an unnamed inline component falls back to the literal 'Component', and a raw markup tag string is returned verbatim.",
    "cases": [
        {"input": {"command": "display_name", "component": {"kind": "class_named", "name": "SomeComponent"}}, "expected_output": "name[a dynamic wrapper pattern involving parentheses and formatted labels]\"SomeComponent\"\n"},
        {"input": {"command": "display_name", "component": {"kind": "anonymous"}}, "expected_output": "name[a dynamic wrapper pattern involving parentheses and formatted labels]\"Component\"\n"},
        {"input": {"command": "display_name", "component": {"kind": "dom", "name": "div"}}, "expected_output": "name[a dynamic wrapper pattern involving parentheses and formatted labels]\"div\"\n"}
    ]
}
```

*2.2 Wrap label — annotate a component label with an enhancer name*

The wrapper combines a component's resolved label with an enhancer name to produce `wrapperName(label)`. This is how enhanced components advertise the chain that produced them. Output is a single `name[a dynamic wrapper pattern involving parentheses and formatted labels]<json-string>` line.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_wrap_display_name.json`

```json
{
    "description": "Wrap a component's label with an enhancer name in the form 'wrapper(label)'.",
    "cases": [
        {"input": {"command": "wrap_display_name", "component": {"kind": "class_named", "name": "SomeComponent"}, "wrapper": "someHoC"}, "expected_output": "name[a dynamic wrapper pattern involving parentheses and formatted labels]\"someHoC(SomeComponent)\"\n"},
        {"input": {"command": "wrap_display_name", "component": {"kind": "dom", "name": "button"}, "wrapper": "wrap"}, "expected_output": "name[a dynamic wrapper pattern involving parentheses and formatted labels]\"wrap(button)\"\n"}
    ]
}
```

---

### Feature 3: Property Shaping

**As a developer**, I want a family of enhancers that reshape the properties a component receives, so I can adapt any component to any caller without editing the component itself.

**Expected Behavior / Usage:**

Every enhancer in this family transforms the incoming property set and forwards the result to the wrapped component. The adapter renders the component and prints the final property set as `key[a dynamic wrapper pattern involving parentheses and formatted labels]value` lines **sorted by key**, where each value is rendered as its JSON literal (strings quoted, numbers bare, objects/arrays as compact JSON). The `stages` field is an ordered list of transformation descriptors; one descriptor exercises one enhancer, while a list of several exercises a composed pipeline (see 3.9).

*3.1 Merge — inject fixed properties that override incoming ones*

Merge a fixed property map onto the incoming properties; on a key collision the merged value wins.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_merge_props.json`

```json
{
    "description": "Merge a fixed set of properties onto the incoming properties; the merged values take precedence over incoming values with the same key. Output lists every resulting property as key[a dynamic wrapper pattern involving parentheses and formatted labels]value lines sorted by key.",
    "cases": [
        {"input": {"command": "transform_props", "stages": [{"op": "merge", "props": {"si": "do", "la": "fa"}}], "props": {}}, "expected_output": "la[a dynamic wrapper pattern involving parentheses and formatted labels]\"fa\"\nsi[a dynamic wrapper pattern involving parentheses and formatted labels]\"do\"\n"},
        {"input": {"command": "transform_props", "stages": [{"op": "merge", "props": {"si": "do", "la": "fa"}}], "props": {"la": "ti"}}, "expected_output": "la[a dynamic wrapper pattern involving parentheses and formatted labels]\"fa\"\nsi[a dynamic wrapper pattern involving parentheses and formatted labels]\"do\"\n"}
    ]
}
```

*3.2 Defaults — supply fallback properties only when missing*

Provide fallback values that apply only when the incoming property is missing or undefined; any defined incoming value is preserved (the opposite precedence to merge).

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_default_props.json`

```json
{
    "description": "Supply fallback property values that apply only when the incoming property is missing or undefined; any defined incoming value is preserved.",
    "cases": [
        {"input": {"command": "transform_props", "stages": [{"op": "defaults", "props": {"si": "do", "la": "fa"}}], "props": {}}, "expected_output": "la[a dynamic wrapper pattern involving parentheses and formatted labels]\"fa\"\nsi[a dynamic wrapper pattern involving parentheses and formatted labels]\"do\"\n"},
        {"input": {"command": "transform_props", "stages": [{"op": "defaults", "props": {"si": "do", "la": "fa"}}], "props": {"la": "ti"}}, "expected_output": "la[a dynamic wrapper pattern involving parentheses and formatted labels]\"ti\"\nsi[a dynamic wrapper pattern involving parentheses and formatted labels]\"do\"\n"}
    ]
}
```

*3.3 Pick — keep only named properties*

Keep only the listed property keys and drop everything else.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_pick_props.json`

```json
{
    "description": "Keep only the named properties and drop the rest.",
    "cases": [
        {"input": {"command": "transform_props", "stages": [{"op": "pick", "keys": ["[the specific property keys removed during the omit operation]"]}], "props": {"foo": "foo", "[the specific property keys removed during the omit operation]": "bar"}}, "expected_output": "[the specific property keys removed during the omit operation][a dynamic wrapper pattern involving parentheses and formatted labels]\"bar\"\n"},
        {"input": {"command": "transform_props", "stages": [{"op": "pick", "keys": ["foo", "[the specific property keys removed during the omit operation]"]}], "props": {"foo": "foo", "bar": "bar", "[the specific property keys removed during the omit operation]": "bar"}}, "expected_output": "[the specific property keys removed during the omit operation][a dynamic wrapper pattern involving parentheses and formatted labels]\"bar\"\nfoo[a dynamic wrapper pattern involving parentheses and formatted labels]\"foo\"\n"}
    ]
}
```

*3.4 Omit — drop named properties*

Drop the listed property keys and keep everything else.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_omit_props.json`

```json
{
    "description": "Drop the named properties and keep the rest.",
    "cases": [
        {"input": {"command": "transform_props", "stages": [{"op": "omit", "keys": ["foo"]}], "props": {"foo": "foo", "[the specific property keys removed during the omit operation]": "bar"}}, "expected_output": "[the specific property keys removed during the omit operation][a dynamic wrapper pattern involving parentheses and formatted labels]\"bar\"\n"},
        {"input": {"command": "transform_props", "stages": [{"op": "omit", "keys": ["foo", "bar"]}], "props": {"foo": "foo", "bar": "bar", "[the specific property keys removed during the omit operation]": "bar"}}, "expected_output": "[the specific property keys removed during the omit operation][a dynamic wrapper pattern involving parentheses and formatted labels]\"bar\"\n"}
    ]
}
```

*3.5 Rename one property — move a value to a new key*

Rename a single property to a new key, preserving its value and leaving every other property untouched.

**Test Cases:** `rcb_tests/public_test_cases/feature3_5_rename_prop.json`

```json
{
    "description": "Rename one property to a new key, keeping its value and leaving other properties untouched.",
    "cases": [
        {"input": {"command": "transform_props", "stages": [{"op": "rename", "from": "foo", "to": "fi"}], "props": {"foo": 123, "bar": 456}}, "expected_output": "bar[a dynamic wrapper pattern involving parentheses and formatted labels]456\nfi[a dynamic wrapper pattern involving parentheses and formatted labels]123\n"}
    ]
}
```

*3.6 Rename many properties — apply an old-to-new key map*

Rename several properties at once via a map from old keys to new keys.

**Test Cases:** `rcb_tests/public_test_cases/feature3_6_rename_props.json`

```json
{
    "description": "Rename several properties at once using an old-key to new-key map.",
    "cases": [
        {"input": {"command": "transform_props", "stages": [{"op": "rename_map", "map": {"si": "do", "la": "fa"}}], "props": {"si": 123, "la": 456}}, "expected_output": "do[a dynamic wrapper pattern involving parentheses and formatted labels]123\nfa[a dynamic wrapper pattern involving parentheses and formatted labels]456\n"}
    ]
}
```

*3.7 Flatten — spread a nested object property up to the top level*

Spread the fields of one or more object-valued properties up into the top-level property set. The flattened fields are added alongside the original object property, which is itself retained. `keys` may be a single property name or a list of names.

**Test Cases:** `rcb_tests/public_test_cases/feature3_7_flatten_props.json`

```json
{
    "description": "Spread the fields of one or more object-valued properties up into the top-level property set; the original object properties are also retained alongside the flattened fields.",
    "cases": [
        {"input": {"command": "transform_props", "stages": [{"op": "flatten", "keys": "state"}], "props": {"pass": "through", "state": {"counter": 1}}}, "expected_output": "counter[a dynamic wrapper pattern involving parentheses and formatted labels]1\npass[a dynamic wrapper pattern involving parentheses and formatted labels]\"through\"\nstate[a dynamic wrapper pattern involving parentheses and formatted labels]{\"counter\":1}\n"},
        {"input": {"command": "transform_props", "stages": [{"op": "flatten", "keys": ["a", "b"]}], "props": {"pass": "through", "a": {"z": 1}, "b": {"y": 2}}}, "expected_output": "a[a dynamic wrapper pattern involving parentheses and formatted labels]{\"z\":1}\nb[a dynamic wrapper pattern involving parentheses and formatted labels]{\"y\":2}\npass[a dynamic wrapper pattern involving parentheses and formatted labels]\"through\"\ny[a dynamic wrapper pattern involving parentheses and formatted labels]2\nz[a dynamic wrapper pattern involving parentheses and formatted labels]1\n"}
    ]
}
```

*3.8 Derive — replace properties with a freshly computed set*

Replace the incoming property set with a brand-new set computed from the inputs. The sample derivation joins an array-valued property into a single string under a new key using a separator; only the derived key remains.

**Test Cases:** `rcb_tests/public_test_cases/feature3_8_derive_props.json`

```json
{
    "description": "Replace the incoming property set with a freshly computed one derived from the inputs; here an array-valued property is joined into a single string under a new key.",
    "cases": [
        {"input": {"command": "transform_props", "stages": [{"op": "derive_join", "source": "strings", "separator": "", "target": "[the specific property keys removed during the omit operation]"}], "props": {"strings": ["a", "b", "c"]}}, "expected_output": "[the specific property keys removed during the omit operation][a dynamic wrapper pattern involving parentheses and formatted labels]\"abc\"\n"},
        {"input": {"command": "transform_props", "stages": [{"op": "derive_join", "source": "parts", "separator": "-", "target": "id"}], "props": {"parts": ["x", "y", "z"]}}, "expected_output": "id[a dynamic wrapper pattern involving parentheses and formatted labels]\"x-y-z\"\n"}
    ]
}
```

*3.9 Pipeline — apply several shaping stages in order*

Apply multiple shaping stages in sequence, left to right, so that each later stage observes the output of the earlier ones.

**Test Cases:** `rcb_tests/public_test_cases/feature3_9_pipeline_composition.json`

```json
{
    "description": "Apply several property-transformation stages in sequence, left to right, so that later stages observe the output of earlier ones.",
    "cases": [
        {"input": {"command": "transform_props", "stages": [{"op": "omit", "keys": ["foo"]}, {"op": "merge", "props": {"extra": "x"}}], "props": {"foo": "foo", "[the specific property keys removed during the omit operation]": "bar"}}, "expected_output": "[the specific property keys removed during the omit operation][a dynamic wrapper pattern involving parentheses and formatted labels]\"bar\"\nextra[a dynamic wrapper pattern involving parentheses and formatted labels]\"x\"\n"},
        {"input": {"command": "transform_props", "stages": [{"op": "merge", "props": {"foo": "bar"}}, {"op": "rename", "from": "foo", "to": "baz"}], "props": {}}, "expected_output": "baz[a dynamic wrapper pattern involving parentheses and formatted labels]\"bar\"\n"}
    ]
}
```

---

### Feature 4: Local State Containers

**As a developer**, I want enhancers that attach managed local state plus updater functions to a component, so I can add interactivity without writing a stateful component by hand.

**Expected Behavior / Usage:**

Each state container injects a state value (and the means to update it) as properties on the wrapped component. The adapter renders once, emits the tracked value, then drives each requested update and re-emits the value after every change. Output is one line per emission.

*4.1 Single state value — a value plus a flexible updater*

Attach one named state value and a named updater. The updater accepts either a replacement value (`set`) or a function of the previous value (`add` n, `mul` n). Initial state is either a fixed seed (`initial`) or read from an incoming property (`initial_from`). The first emitted line is the initial state, followed by one line per applied update.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_stateful_value.json`

```json
{
    "description": "Attach a named state value and an updater. The updater accepts either a replacement value or a function of the previous value. State starts from a fixed seed or from an incoming property. Output emits the state after the initial render and after each update.",
    "cases": [
        {"input": {"command": "stateful_value", "state_name": "counter", "updater_name": "updateCounter", "initial": 0, "props": {"pass": "through"}, "updates": [{"add": 9}, {"mul": 2}, {"mul": 2}]}, "expected_output": "counter[a dynamic wrapper pattern involving parentheses and formatted labels]0\ncounter[a dynamic wrapper pattern involving parentheses and formatted labels]9\ncounter[a dynamic wrapper pattern involving parentheses and formatted labels]18\ncounter[a dynamic wrapper pattern involving parentheses and formatted labels]36\n"},
        {"input": {"command": "stateful_value", "state_name": "counter", "updater_name": "updateCounter", "initial": 0, "updates": [{"set": 18}]}, "expected_output": "counter[a dynamic wrapper pattern involving parentheses and formatted labels]0\ncounter[a dynamic wrapper pattern involving parentheses and formatted labels]18\n"},
        {"input": {"command": "stateful_value", "state_name": "counter", "updater_name": "updateCounter", "initial_from": "initialCounter", "props": {"initialCounter": 1}, "updates": [{"mul": 3}]}, "expected_output": "counter[a dynamic wrapper pattern involving parentheses and formatted labels]1\ncounter[a dynamic wrapper pattern involving parentheses and formatted labels]3\n"}
    ]
}
```

*4.2 Reducer-driven state — advance state by dispatching actions*

Attach a state value governed by a reducer plus a dispatch function. Each dispatched action `{type, payload}` runs the reducer to produce the next state; the sample reducer replaces the tracked counter when the action type is `SET_COUNTER` and otherwise leaves it unchanged. Initial state may be a fixed object (`initial`), derived from an incoming property (`initial_from`, mapped to `{counter: <value>}`), or omitted entirely (the reducer supplies its own default of `0`). The first line is the initial counter; each dispatched action adds a line.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_reducer_state.json`

```json
{
    "description": "Attach a state value driven by a reducer plus a dispatch function; dispatched actions advance the state. Initial state may be a fixed object, derived from an incoming property, or supplied by the reducer's own default when omitted.",
    "cases": [
        {"input": {"command": "reducer_state", "initial": {"counter": 0}, "actions": [{"type": "SET_COUNTER", "payload": 18}]}, "expected_output": "counter[a dynamic wrapper pattern involving parentheses and formatted labels]0\ncounter[a dynamic wrapper pattern involving parentheses and formatted labels]18\n"},
        {"input": {"command": "reducer_state", "initial_from": "initialCount", "props": {"initialCount": 10}}, "expected_output": "counter[a dynamic wrapper pattern involving parentheses and formatted labels]10\n"},
        {"input": {"command": "reducer_state"}, "expected_output": "counter[a dynamic wrapper pattern involving parentheses and formatted labels]0\n"}
    ]
}
```

*4.3 State with named handlers — immutable updaters that merge partial state*

Attach a state object plus named updater handlers. Each handler takes a payload and returns a partial state that is shallowly merged into the current state, or returns nothing to leave state unchanged (and skip a re-render). The sample handler `increment` adds its payload to the tracked counter but returns nothing when the payload is `0`. Initial state is a fixed object (`initial`) or derived from an incoming property (`initial_from`). The first line is the initial value; each handler call adds a line (an unchanged value still re-emits the same number).

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_state_handlers.json`

```json
{
    "description": "Attach a state object plus named updater handlers; each handler receives a payload and returns a partial state that is shallowly merged, or returns nothing to leave state unchanged. Output emits the tracked value after the initial render and after each call.",
    "cases": [
        {"input": {"command": "state_handlers", "initial": {"counter": 0}, "props": {"pass": "through"}, "calls": [{"handler": "increment", "payload": 9}, {"handler": "increment", "payload": 1}, {"handler": "increment", "payload": 10}]}, "expected_output": "counter[a dynamic wrapper pattern involving parentheses and formatted labels]0\ncounter[a dynamic wrapper pattern involving parentheses and formatted labels]9\ncounter[a dynamic wrapper pattern involving parentheses and formatted labels]10\ncounter[a dynamic wrapper pattern involving parentheses and formatted labels]20\n"},
        {"input": {"command": "state_handlers", "initial_from": "initialCounter", "props": {"initialCounter": 101}, "calls": [{"handler": "increment", "payload": 0}]}, "expected_output": "counter[a dynamic wrapper pattern involving parentheses and formatted labels]101\ncounter[a dynamic wrapper pattern involving parentheses and formatted labels]101\n"}
    ]
}
```

---

### Feature 5: Conditional Enhancement

**As a developer**, I want to choose between two enhancements based on a runtime property, so I can branch behavior or output declaratively.

**Expected Behavior / Usage:**

*5.1 Branch on property, transform — pick one of two property transformations*

Test a named property; when it is truthy apply the `when_true` transformation, otherwise apply `when_false`. Each branch here is a property merge. Output is the final property set as sorted `key[a dynamic wrapper pattern involving parentheses and formatted labels]value` lines (the tested property is forwarded through and so also appears).

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_branch_transform.json`

```json
{
    "description": "Test a property and apply one of two property transformations: when the tested property is truthy the first transformation runs, otherwise the second.",
    "cases": [
        {"input": {"command": "branch_transform", "test_prop": "isBad", "when_true": {"merge": {"name": "Heisenberg"}}, "when_false": {"merge": {"name": "Walter"}}, "props": {"isBad": false}}, "expected_output": "isBad[a dynamic wrapper pattern involving parentheses and formatted labels]false\nname[a dynamic wrapper pattern involving parentheses and formatted labels]\"Walter\"\n"},
        {"input": {"command": "branch_transform", "test_prop": "isBad", "when_true": {"merge": {"name": "Heisenberg"}}, "when_false": {"merge": {"name": "Walter"}}, "props": {"isBad": true}}, "expected_output": "isBad[a dynamic wrapper pattern involving parentheses and formatted labels]true\nname[a dynamic wrapper pattern involving parentheses and formatted labels]\"Heisenberg\"\n"}
    ]
}
```

*5.2 Branch on property, render — pick one of two render outcomes*

Test a named property; when truthy render the `when_true` outcome, otherwise the `when_false` outcome. An outcome is either a chosen markup tag (`{"render_tag": "..."}`, which renders that tag forwarding the incoming properties) or `"render_nothing"` (an empty render). The rendered tree is printed as an indented node listing: each node on its own line as `tag key[a dynamic wrapper pattern involving parentheses and formatted labels]value ...` with attributes sorted by key, children indented by two spaces, and an empty render shown as `null`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_branch_render.json`

```json
{
    "description": "Test a property and render one of two outcomes: a chosen markup tag, or nothing at all (an empty render). The rendered tree is printed as an indented node listing.",
    "cases": [
        {"input": {"command": "branch_render", "test_prop": "flip", "when_true": {"render_tag": "section"}, "when_false": {"render_tag": "article"}, "props": {"flip": true}}, "expected_output": "section flip[a dynamic wrapper pattern involving parentheses and formatted labels]true\n"},
        {"input": {"command": "branch_render", "test_prop": "flip", "when_true": {"render_tag": "section"}, "when_false": {"render_tag": "article"}, "props": {"flip": false}}, "expected_output": "article flip[a dynamic wrapper pattern involving parentheses and formatted labels]false\n"},
        {"input": {"command": "branch_render", "test_prop": "flip", "when_true": {"render_tag": "section"}, "when_false": "render_nothing", "props": {"flip": false}}, "expected_output": "null\n"}
    ]
}
```

---

### Feature 6: Structural Rendering

**As a developer**, I want helpers that assemble component trees from data, so I can build nested structures and late-bound element types declaratively.

**Expected Behavior / Usage:**

Both helpers print the rendered tree as an indented node listing: each node is `tag key[a dynamic wrapper pattern involving parentheses and formatted labels]value ...` with attributes sorted by key, and children are indented by two additional spaces per level. A text child is printed as its own indented line.

*6.1 Nest — wrap a sequence of tags outer-to-inner*

Nest a list of markup tags so the first is outermost and the last is innermost, passing the same properties to every level and placing the supplied children at the innermost level.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_nest_components.json`

```json
{
    "description": "Nest a series of markup tags from outer to inner, passing the same properties to each level and placing the supplied children at the innermost level. The rendered tree is printed as an indented node listing.",
    "cases": [
        {"input": {"command": "nest", "components": ["div", "section", "span"], "props": {"[the specific property keys removed during the omit operation]": "foo"}, "children": "Child"}, "expected_output": "div [the specific property keys removed during the omit operation][a dynamic wrapper pattern involving parentheses and formatted labels]\"foo\"\n  section [the specific property keys removed during the omit operation][a dynamic wrapper pattern involving parentheses and formatted labels]\"foo\"\n    span [the specific property keys removed during the omit operation][a dynamic wrapper pattern involving parentheses and formatted labels]\"foo\"\n      Child\n"},
        {"input": {"command": "nest", "components": ["div", "button"], "props": {"[the specific property keys removed during the omit operation]": "foo"}}, "expected_output": "div [the specific property keys removed during the omit operation][a dynamic wrapper pattern involving parentheses and formatted labels]\"foo\"\n  button [the specific property keys removed during the omit operation][a dynamic wrapper pattern involving parentheses and formatted labels]\"foo\"\n"}
    ]
}
```

*6.2 Component from property — render the tag named by a property*

Render whichever markup tag is named by a designated property, forwarding all remaining properties to it. This enables a single component whose concrete element type is chosen by its caller at runtime.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_component_from_prop.json`

```json
{
    "description": "Render whichever markup tag is named by a designated property, forwarding the remaining properties to it. The rendered tree is printed as an indented node listing.",
    "cases": [
        {"input": {"command": "component_from_prop", "prop_name": "component", "props": {"component": "a", "foo": "bar"}}, "expected_output": "a foo[a dynamic wrapper pattern involving parentheses and formatted labels]\"bar\"\n"},
        {"input": {"command": "component_from_prop", "prop_name": "component", "props": {"component": "button", "pass": "through"}}, "expected_output": "button pass[a dynamic wrapper pattern involving parentheses and formatted labels]\"through\"\n"}
    ]
}
```

---

### Feature 7: Render Memoization

**As a developer**, I want to suppress re-renders when nothing relevant changed, so I can keep updates cheap.

**Expected Behavior / Usage:**

Wrap a component with a memoization strategy and feed it successive property snapshots. Two strategies exist: `all` compares every property shallowly, and `keys` compares only a named subset of properties. The adapter renders once, then applies each property update in order, emitting the cumulative render count after the initial render and after every update. The count grows only when a watched property actually changes; an update that leaves the watched properties shallow-equal does not increment it.

**Test Cases:** `rcb_tests/public_test_cases/feature7_render_memoization.json`

```json
{
    "description": "Skip re-rendering when properties have not meaningfully changed. Two strategies exist: compare every property shallowly, or compare only a named subset of properties. Output emits the cumulative render count after the initial render and after each property update; the count only grows when a watched property changes.",
    "cases": [
        {"input": {"command": "memoize", "strategy": {"type": "all"}, "initial_props": {"foo": "bar"}, "prop_updates": [{"foo": "bar"}, {"foo": "baz"}]}, "expected_output": "renders[a dynamic wrapper pattern involving parentheses and formatted labels]1\nrenders[a dynamic wrapper pattern involving parentheses and formatted labels]1\nrenders[a dynamic wrapper pattern involving parentheses and formatted labels]2\n"},
        {"input": {"command": "memoize", "strategy": {"type": "keys", "keys": ["counter"]}, "initial_props": {"counter": 0, "foobar": "foobar"}, "prop_updates": [{"counter": 0, "foobar": "barbaz"}, {"counter": 42, "foobar": "barbaz"}]}, "expected_output": "renders[a dynamic wrapper pattern involving parentheses and formatted labels]1\nrenders[a dynamic wrapper pattern involving parentheses and formatted labels]1\nrenders[a dynamic wrapper pattern involving parentheses and formatted labels]2\n"}
    ]
}
```

---

### Feature 8: Event Stream Multicast

**As a developer**, I want to turn an imperative push call into an observable stream that fans out to many subscribers, so I can wire event handlers to reactive consumers.

**Expected Behavior / Usage:**

Create a paired push handler and observable stream. Attach `subscribers` independent subscriptions, push each value in `emit` through the handler, then unsubscribe. Every value pushed while a subscription is active is delivered to it in order. Output lists each subscriber's received sequence as `subscriberN[a dynamic wrapper pattern involving parentheses and formatted labels][...]`, one line per subscriber.

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_event_stream.json`

```json
{
    "description": "Create a push handler paired with an observable stream; values pushed through the handler are delivered in order to every active subscriber. Output lists each subscriber's received sequence.",
    "cases": [
        {"input": {"command": "event_stream", "subscribers": 1, "emit": [1, 2, 3]}, "expected_output": "subscriber0[a dynamic wrapper pattern involving parentheses and formatted labels][1,2,3]\n"},
        {"input": {"command": "event_stream", "subscribers": 2, "emit": [1, 2, 3]}, "expected_output": "subscriber0[a dynamic wrapper pattern involving parentheses and formatted labels][1,2,3]\nsubscriber1[a dynamic wrapper pattern involving parentheses and formatted labels][1,2,3]\n"}
    ]
}
```

---

### Feature 9: Stable Handlers

**As a developer**, I want handler functions whose identity is preserved across renders and whose misuse is reported cleanly, so I can rely on prop equality and fail predictably.

**Expected Behavior / Usage:**

*9.1 Property-bound cached handlers — read live properties through a stable function*

Expose a handler derived from the current properties. The handler reads a designated property's live value and is only recreated when properties change, so its identity is stable across identical renders. The adapter feeds successive property snapshots and emits the value the handler reads at each render.

**Test Cases:** `rcb_tests/public_test_cases/feature9_1_cached_handlers.json`

```json
{
    "description": "Expose stable handler functions derived from the current properties; a handler reads live property values and is recreated only when properties change. Output emits the value the handler reads at each render.",
    "cases": [
        {"input": {"command": "cached_handler", "prop_name": "foo", "prop_updates": [{"foo": "bar"}, {"foo": "bar"}, {"foo": "baz"}]}, "expected_output": "result[a dynamic wrapper pattern involving parentheses and formatted labels]\"bar\"\nresult[a dynamic wrapper pattern involving parentheses and formatted labels]\"bar\"\nresult[a dynamic wrapper pattern involving parentheses and formatted labels]\"baz\"\n"}
    ]
}
```

*9.2 Handler misuse — normalized error for a bad handler factory*

When a supplied handler factory is not a higher-order function (it does not return a function), invoking the produced handler must surface as the normalized error category `invalid_handler_factory` rather than leaking any runtime fault detail. Output is the single line `error[a dynamic wrapper pattern involving parentheses and formatted labels]invalid_handler_factory`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_2_handler_error.json`

```json
{
    "description": "When a supplied handler factory is not a higher-order function (it does not return a function), invoking the produced handler is reported as a normalized error category rather than leaking any runtime fault detail.",
    "cases": [
        {"input": {"command": "handler_error"}, "expected_output": "error[a dynamic wrapper pattern involving parentheses and formatted labels]invalid_handler_factory\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file library implementing the composition core, the property-shaping enhancers, the local-state containers, the conditional and structural rendering helpers, the memoization strategies, the event-stream multicast utility, and the stable-handler utility described above — one focused module per enhancer plus shared internal helpers.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads a single JSON command from stdin, invokes the appropriate enhancers, renders the resulting component with an in-memory renderer, and prints the observed result to stdout, strictly matching the per-leaf-feature contracts above. Native runtime faults are caught here and re-rendered as normalized `error[a dynamic wrapper pattern involving parentheses and formatted labels]<category>` lines; the adapter is logically and physically separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_function_composition.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_function_composition@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the expansion logic used in nested objects within flatten
- adhere to the pipeline execution order defined in feature3_7_flatten_props
