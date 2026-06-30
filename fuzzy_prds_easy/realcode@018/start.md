## Product Requirement Document

# Data-Driven Virtual-DOM Component Engine — Render, Diff/Patch, Keyed Reconciliation & Update Scheduling

## Project Goal

Build a small library for writing HTML view components whose on-screen content is a pure function of a data model, so developers can describe *what* the DOM should look like and let the engine compute and apply the minimal set of real-DOM mutations needed to get there — without hand-writing imperative DOM manipulation or re-creating unchanged nodes on every change.

---

## Background & Problem

A view component owns a piece of state and a `render` function that returns a description of the DOM it wants (a tree of tagged elements, attributes, text and nested components). When the state changes, the naive approach is to throw away the old DOM and rebuild it, which loses element identity, focus, and scroll position and is wasteful. The alternative — hand-writing the exact DOM mutations for every possible state transition — is repetitive and error-prone.

This library provides one well-defined contract: from an old description and a new description it computes a diff and patches the existing DOM in place, reusing nodes wherever the structure is unchanged and only creating, moving, or replacing nodes where it must. It supports building a component and rendering it for the first time, named references that resolve to the live nodes (or nested component instances) a render produced, composing components inside one another, reconciling re-ordered keyed children by moving rather than rebuilding, and a small scheduler that batches deferred updates onto an animation frame or applies them synchronously.

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

All features are exercised through one execution adapter that reads a single JSON request from stdin and writes a normalized, deterministic serialization to stdout. Two request families exist, selected by a `kind` field:

**`kind: "component"` — render/update a component and observe the resulting DOM.** The request carries an optional `components` map (named component definitions), a `root` component, and an ordered list of `steps`.

A *render specification* (used by `root.render` and each component's `render`) is a tree where:
- a string is literal text;
- `{ "var": "<path>" }` substitutes a dynamic value — `state.<k>` / `<k>` reads the component's own state, `props.<k>` reads an input passed to the component, and `children` splices the children handed to a composed component;
- `{ "if": "<stateKey>", "then": <spec>, "else": <spec> }` chooses a branch by the truthiness of a state value;
- `{ "el": "<tag>", "attrs": {…}, "ref": "<name>", "key": "<k>", "children": [ … ] }` is an element with optional attributes, an optional reference name, an optional reconciliation key, and children;
- `{ "comp": "<name>", "props": {…}, "ref": "<name>", "key": "<k>", "children": [ … ] }` mounts a named component definition at this position. `attrs`/`props`/`ref`/`key` values may themselves be `{ "var": … }` expressions.

A component definition is `{ "render": <spec>, "state": {…}, "update": <bool> }`; `update: [a boolean flag indicating asynchronous execution]` means the component, when its parent re-renders it in place with new inputs, accepts those inputs and re-renders itself (i.e. it can be patched in place rather than rebuilt). Each `step` is one of: `{ "set": { … } }` (mutate the root component's state), `{ "updateAsync": [a boolean flag indicating asynchronous execution] }` (request a deferred, animation-frame-flushed update of the root), `{ "updateSync": [a boolean flag indicating asynchronous execution] }` (apply an update of the root immediately), or `{ "probe": "<label>" }` (record an observation point).

**Output serialization (for `kind: "component"`).** Each `probe` emits a block beginning with `== <label> ==`, then `element=<serialized DOM of the root's element>`, then `text=<flattened text content>`, then — only if any references are currently bound — a `refs:` line followed by one entry per bound reference (sorted by name, indented two spaces). An element is serialized as `<tag#<token> attr="v" …>children</tag>` with attributes sorted by name; the `#<token>` is a **stable identity token** assigned the first time a real node is serialized and reused for that same node at later observation points, so node reuse versus replacement is directly observable. A reference bound to a DOM node serializes as `<name>=<serialized node>`; a reference bound to a component instance serializes as `<name>=component element=<serialized element>` followed by ` ref=<mounted reference name>` when present, and then that instance's own references nested below it. If an operation is rejected, the block stream is replaced by a single line `error=<category>` (see Feature 2.3).

**`kind: "scheduler"` — observe deferred/synchronous update batching.** The request carries `mode` (`"async"` or `"sync"`) and `requests`, a list of update requests. Each request is `{ "emit": <label>, "thenAsync": [ … ], "thenSync": [ … ] }`: when it runs it appends its `emit` label to the output and then submits its nested `thenAsync` requests to the deferred queue and `thenSync` requests to the synchronous path. The output is the emitted labels in execution order, one per line.

---

### Feature 1: Build A Component And Render It To The DOM

**As a developer**, I want to construct a component from a render specification and get a real DOM subtree reflecting it, so I can mount a data-driven view.

**Expected Behavior / Usage:**

*1.1 Render an element tree — initial construction of nested elements, attributes and text*

The engine evaluates the root component's render specification and produces a DOM subtree. The serialization reports the full tree (each element with its sorted attributes, identity token and children, with text inlined) and the component's flattened text content. Attribute names supplied in `attrs` appear normalized on the corresponding nodes (e.g. a class-name input surfaces as a `class` attribute); attributes are always emitted in name-sorted order so output is order-independent of input.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_render_element_tree.json`

```json
{
    "description": "Build a component from a render specification and render it to the DOM for the first time. The render specification describes a single root element with a tag name, optional attributes and a list of children (nested elements and literal text). After construction, the resulting DOM subtree is serialized: every element is shown with its tag, a stable identity token, its attributes sorted by name, and its serialized children, with text nodes inlined. The component's flattened text content is also reported.",
    "cases": [
        {
            "input": {"kind": "component", "root": {"render": {"el": "div", "children": ["Hello World"]}}, "steps": [{"probe": "render"}]},
            "expected_output": "== render ==\nelement=<div[a sequence of incremental identifiers]>Hello World</div>\ntext=Hello World\n"
        }
    ]
}
```

*1.2 Named DOM references — resolving reference names to the live nodes a render produced*

When an element in the render specification carries a reference name, after the initial render that name resolves to the live DOM node created for it. The serialization includes a `refs:` section listing each bound reference (sorted by name) with its serialized node, in addition to the full tree and flattened text.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_dom_element_refs.json`

```json
{
    "description": "Render a component whose specification marks certain elements with a reference name. After the initial render, each named reference resolves to the live DOM node produced for that element. The output lists, sorted by reference name, the serialized DOM node bound to each reference, alongside the full serialized tree and flattened text content.",
    "cases": [
        {
            "input": {"kind": "component", "root": {"render": {"el": "div", "children": [{"el": "span", "ref": "greeting", "children": ["Hello"]}, " ", {"el": "span", "ref": "greeted", "children": ["World"]}]}}, "steps": [{"probe": "render"}]},
            "expected_output": "== render ==\nelement=<div[a sequence of incremental identifiers]><span[a sequence of incremental identifiers]>Hello</span> <span[a sequence of incremental identifiers]>World</span></div>\ntext=Hello World\nrefs:\n  greeted=<span[a sequence of incremental identifiers]>World</span>\n  greeting=<span[a sequence of incremental identifiers]>Hello</span>\n"
        }
    ]
}
```

---

### Feature 2: Update A Rendered Component By Diffing And Patching

**As a developer**, I want to change a component's state and have the engine apply only the necessary DOM mutations, so existing nodes are preserved where possible.

**Expected Behavior / Usage:**

*2.1 Patch text/content on update — re-render and diff against the previous tree*

When a component whose content derives from state is updated after a state change, the engine re-renders and patches the existing DOM in place. The before/after observation points show the same root identity token, proving the node is patched rather than rebuilt, while its text content changes to reflect the new state.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_text_content_update.json`

```json
{
    "description": "Render a component whose text content is derived from a piece of mutable state, then change that state and apply a scheduled update. The update re-renders the component and diffs the new tree against the previous one, patching only what changed. Two observation points are reported: the serialized DOM before the change and after the update is flushed. The stable identity tokens reveal that the existing element is patched in place rather than rebuilt.",
    "cases": [
        {
            "input": {"kind": "component", "root": {"state": {"greeting": "Hello"}, "render": {"el": "div", "children": [{"var": "greeting"}, " World"]}}, "steps": [{"probe": "before"}, {"set": {"greeting": "Goodbye"}}, {"updateAsync": [a boolean flag indicating asynchronous execution]}, {"probe": "after"}]},
            "expected_output": "== before ==\nelement=<div[a sequence of incremental identifiers]>Hello World</div>\ntext=Hello World\n== after ==\nelement=<div[a sequence of incremental identifiers]>Goodbye World</div>\ntext=Goodbye World\n"
        }
    ]
}
```

*2.2 Reassign references across an update — bind/unbind reference names as the tree changes*

When an update produces a tree in which a previously bound reference no longer appears and a new reference does, the old binding is cleared and the new one is established. Each observation point lists the currently bound references with their serialized nodes.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_ref_reassignment.json`

```json
{
    "description": "Render a component that, depending on a boolean in its state, produces a child element bound to one of two different reference names. After toggling the state and applying a scheduled update, the reference that no longer appears in the new tree is removed and the reference present in the new tree is bound. Each observation point lists the currently bound references (sorted by name) with their serialized nodes, plus the serialized tree and flattened text.",
    "cases": [
        {
            "input": {"kind": "component", "root": {"state": {"condition": [a boolean flag indicating asynchronous execution]}, "render": {"if": "condition", "then": {"el": "div", "children": [{"el": "span", "ref": "greeting", "children": ["Hello"]}]}, "else": {"el": "div", "children": [{"el": "span", "ref": "greeted", "children": ["World"]}]}}}, "steps": [{"probe": "before"}, {"set": {"condition": false}}, {"updateAsync": [a boolean flag indicating asynchronous execution]}, {"probe": "after"}]},
            "expected_output": "== before ==\nelement=<div[a sequence of incremental identifiers]><span[a sequence of incremental identifiers]>Hello</span></div>\ntext=Hello\nrefs:\n  greeting=<span[a sequence of incremental identifiers]>Hello</span>\n== after ==\nelement=<div[a sequence of incremental identifiers]><span[a sequence of incremental identifiers]>World</span></div>\ntext=World\nrefs:\n  greeted=<span[a sequence of incremental identifiers]>World</span>\n"
        }
    ]
}
```

*2.3 Reject a root node type change — changing the top-level tag of a rendered component is unsupported*

A component's root node type is fixed once rendered. If an update would require the root element to become a different tag, the engine rejects the update. The rejection is reported as a neutral, language-independent error category — never as host-language runtime detail.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_root_node_type_change.json`

```json
{
    "description": "Render a component whose root element tag depends on state, then change the state so a subsequent update would require the root element to become a different tag, and apply a synchronous update. Changing the type of the root node of an already-rendered component is not supported, so the update is rejected. The rejection is reported as a neutral, language-independent error category rather than the rendered DOM.",
    "cases": [
        {
            "input": {"kind": "component", "root": {"state": {"d": [a boolean flag indicating asynchronous execution]}, "render": {"if": "d", "then": {"el": "div"}, "else": {"el": "span"}}}, "steps": [{"set": {"d": false}}, {"updateSync": [a boolean flag indicating asynchronous execution]}, {"probe": "after"}]},
            "expected_output": "[the specific error line formatted for unsupported root changes]\n"
        }
    ]
}
```

*2.4 Synchronous update — apply an update and any child updates it triggers immediately*

A synchronous update re-renders the component and drains any child-component updates it triggers within the same flush, so the whole subtree reflects the new state at the next observation point. Identity tokens show existing nodes are patched in place.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_synchronous_update.json`

```json
{
    "description": "Render a component that embeds a nested child component plus a sibling element, where both the child's input and the sibling's text derive from the parent's state. After mutating the parent state, apply a synchronous (immediately flushed) update. The synchronous update re-renders the parent and any child updates it triggers within the same flush, so the entire subtree reflects the new state at the next observation point. Identity tokens show the existing nodes are patched in place.",
    "cases": [
        {
            "input": {"kind": "component", "components": {"Child": {"update": [a boolean flag indicating asynchronous execution], "render": {"el": "span", "children": [{"var": "props.greeting"}]}}}, "root": {"state": {"greeting": "Hello", "greeted": "World"}, "render": {"el": "div", "children": [{"comp": "Child", "props": {"greeting": {"var": "greeting"}}}, " ", {"el": "span", "children": [{"var": "greeted"}]}]}}, "steps": [{"probe": "before"}, {"set": {"greeting": "Goodnight", "greeted": "Moon"}}, {"updateSync": [a boolean flag indicating asynchronous execution]}, {"probe": "after"}]},
            "expected_output": "== before ==\nelement=<div[a sequence of incremental identifiers]><span[a sequence of incremental identifiers]>Hello</span> <span[a sequence of incremental identifiers]>World</span></div>\ntext=Hello World\n== after ==\nelement=<div[a sequence of incremental identifiers]><span[a sequence of incremental identifiers]>Goodnight</span> <span[a sequence of incremental identifiers]>Moon</span></div>\ntext=Goodnight Moon\n"
        }
    ]
}
```

---

### Feature 3: Compose Components As Tags

**As a developer**, I want to mount one component inside another's render specification, so I can build views out of reusable parts and have the engine reconcile them correctly across updates.

**Expected Behavior / Usage:**

*3.1 Compose a child component on initial render — construct it with inputs and insert its element*

When a render specification mounts a named component at a position, that component is constructed with the supplied inputs and children, and its own rendered element is inserted at that position. The serialized DOM and flattened text span both parent and child.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_compose_child_component.json`

```json
{
    "description": "Use a component definition as if it were an element tag inside another component's render specification, passing it attributes and nested children. On the initial render the referenced component is constructed with those attributes and children and its own rendered element is inserted at that position in the parent's tree. The serialized DOM shows the composed result and the flattened text content spans parent and child.",
    "cases": [
        {
            "input": {"kind": "component", "components": {"Child": {"render": {"el": "div", "children": [{"var": "props.greeting"}, " ", {"var": "children"}]}}}, "root": {"render": {"el": "div", "children": [{"comp": "Child", "props": {"greeting": "Hello"}, "children": [{"el": "span", "children": ["World"]}]}]}}, "steps": [{"probe": "render"}]},
            "expected_output": "== render ==\nelement=<div[a sequence of incremental identifiers]><div[a sequence of incremental identifiers]>Hello <span[a sequence of incremental identifiers]>World</span></div></div>\ntext=Hello World\n"
        }
    ]
}
```

*3.2 In-place update preserves the child element — same definition with update capability is patched, not rebuilt*

When a parent re-renders a child of the same definition at the same position and that child can be updated in place, the existing child instance receives the new inputs and re-renders, reusing its element. The before/after observation points show the same child element identity token while its content changes.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_update_preserves_element.json`

```json
{
    "description": "Render a parent that embeds a child component, where the child declares an update capability. When the parent re-renders with new inputs for the same child component (same definition at the same position), the existing child instance is updated in place and re-rendered rather than rebuilt: its DOM element is reused. The before/after observation points show the same identity token for the child element while its content changes to reflect the new inputs.",
    "cases": [
        {
            "input": {"kind": "component", "components": {"Child": {"update": [a boolean flag indicating asynchronous execution], "render": {"el": "div", "children": [{"var": "props.greeting"}, " ", {"var": "children"}]}}}, "root": {"state": {"greeting": "Hello", "greeted": "World"}, "render": {"el": "div", "children": [{"comp": "Child", "props": {"greeting": {"var": "greeting"}}, "children": [{"el": "span", "children": [{"var": "greeted"}]}]}]}}, "steps": [{"probe": "before"}, {"set": {"greeting": "Goodnight", "greeted": "Moon"}}, {"updateAsync": [a boolean flag indicating asynchronous execution]}, {"probe": "after"}]},
            "expected_output": "== before ==\nelement=<div[a sequence of incremental identifiers]><div[a sequence of incremental identifiers]>Hello <span[a sequence of incremental identifiers]>World</span></div></div>\ntext=Hello World\n== after ==\nelement=<div[a sequence of incremental identifiers]><div[a sequence of incremental identifiers]>Goodnight <span[a sequence of incremental identifiers]>Moon</span></div></div>\ntext=Goodnight Moon\n"
        }
    ]
}
```

*3.3 Replace a child that cannot update in place — same definition without update capability is rebuilt*

When a parent re-renders a child of the same definition that does NOT support in-place update, the engine builds a fresh instance and replaces the previous element with the new one. The before/after identity tokens for the child element differ, confirming a replacement even though the new content reflects the new inputs.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_replace_without_update.json`

```json
{
    "description": "Render a parent that embeds a child component that does NOT declare an update capability. When the parent re-renders with new inputs for that same child position, the framework cannot update the existing instance in place, so it builds a fresh instance and replaces the previous element with the new one. The before/after observation points show the child element's identity token changing, confirming a replacement rather than an in-place patch, even though the rendered text is what the new inputs imply.",
    "cases": [
        {
            "input": {"kind": "component", "components": {"Child": {"render": {"el": "div", "children": [{"var": "props.greeting"}, " ", {"var": "children"}]}}}, "root": {"state": {"greeting": "Hello", "greeted": "World"}, "render": {"el": "div", "children": [{"comp": "Child", "props": {"greeting": {"var": "greeting"}}, "children": [{"el": "span", "children": [{"var": "greeted"}]}]}]}}, "steps": [{"probe": "before"}, {"set": {"greeting": "Goodnight", "greeted": "Moon"}}, {"updateAsync": [a boolean flag indicating asynchronous execution]}, {"probe": "after"}]},
            "expected_output": "== before ==\nelement=<div[a sequence of incremental identifiers]><div[a sequence of incremental identifiers]>Hello <span[a sequence of incremental identifiers]>World</span></div></div>\ntext=Hello World\n== after ==\nelement=<div[a sequence of incremental identifiers]><div#n4>Goodnight <span#n5>Moon</span></div></div>\ntext=Goodnight Moon\n"
        }
    ]
}
```

*3.4 Replace on definition change — a different component definition at the same position is rebuilt*

When the child mounted at a position changes to a different component definition between renders, the previous instance and element are discarded and a new instance is built in its place. The before/after observation points show different identity tokens and different content.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_replace_on_type_change.json`

```json
{
    "description": "Render a parent that, depending on its state, embeds one of two DIFFERENT child component definitions at the same position. When the parent re-renders and the child at that position is a different component definition than before, the previous instance and its element are discarded and a new instance is built and inserted in its place. The before/after observation points show different identity tokens and different rendered content.",
    "cases": [
        {
            "input": {"kind": "component", "components": {"A": {"update": [a boolean flag indicating asynchronous execution], "render": {"el": "div", "children": ["A"]}}, "B": {"update": [a boolean flag indicating asynchronous execution], "render": {"el": "div", "children": ["B"]}}}, "root": {"state": {"condition": [a boolean flag indicating asynchronous execution]}, "render": {"if": "condition", "then": {"el": "div", "children": [{"comp": "A"}]}, "else": {"el": "div", "children": [{"comp": "B"}]}}}, "steps": [{"probe": "before"}, {"set": {"condition": false}}, {"updateAsync": [a boolean flag indicating asynchronous execution]}, {"probe": "after"}]},
            "expected_output": "== before ==\nelement=<div[a sequence of incremental identifiers]><div[a sequence of incremental identifiers]>A</div></div>\ntext=A\n== after ==\nelement=<div[a sequence of incremental identifiers]><div[a sequence of incremental identifiers]>B</div></div>\ntext=B\n"
        }
    ]
}
```

*3.5 Keyed reordering — re-order keyed children by moving existing elements*

When two keyed children are re-rendered in the opposite order using the same keys, the engine reconciles by moving the existing elements rather than rebuilding them. The before/after observation points show the two element identity tokens swapping position, while each reference still resolves to its original child instance and element.

**Test Cases:** `rcb_tests/public_test_cases/feature3_5_keyed_reordering.json`

```json
{
    "description": "Render a parent that embeds two child components side by side, each tagged with a stable key and bound to a reference name. When the parent re-renders with the two children in the opposite order (same keys), the framework reconciles by reordering the existing child elements instead of rebuilding them. The before/after observation points show the two element identity tokens swapping position while each reference still resolves to its original child instance and element.",
    "cases": [
        {
            "input": {"kind": "component", "components": {"A": {"update": [a boolean flag indicating asynchronous execution], "render": {"el": "div", "children": ["A"]}}, "B": {"update": [a boolean flag indicating asynchronous execution], "render": {"el": "div", "children": ["B"]}}}, "root": {"state": {"condition": [a boolean flag indicating asynchronous execution]}, "render": {"if": "condition", "then": {"el": "div", "children": [{"comp": "A", "key": "a", "ref": "a"}, {"comp": "B", "key": "b", "ref": "b"}]}, "else": {"el": "div", "children": [{"comp": "B", "key": "b", "ref": "b"}, {"comp": "A", "key": "a", "ref": "a"}]}}}, "steps": [{"probe": "before"}, {"set": {"condition": false}}, {"updateAsync": [a boolean flag indicating asynchronous execution]}, {"probe": "after"}]},
            "expected_output": "== before ==\nelement=<div[a sequence of incremental identifiers]><div[a sequence of incremental identifiers]>A</div><div[a sequence of incremental identifiers]>B</div></div>\ntext=AB\nrefs:\n  a=component element=<div[a sequence of incremental identifiers]>A</div> ref=a\n  b=component element=<div[a sequence of incremental identifiers]>B</div> ref=b\n== after ==\nelement=<div[a sequence of incremental identifiers]><div[a sequence of incremental identifiers]>B</div><div[a sequence of incremental identifiers]>A</div></div>\ntext=BA\nrefs:\n  a=component element=<div[a sequence of incremental identifiers]>A</div> ref=a\n  b=component element=<div[a sequence of incremental identifiers]>B</div> ref=b\n"
        }
    ]
}
```

*3.6 Component-instance references — a reference can resolve to a child component instance and move/rebuild across renders*

A reference name on a mounted component resolves to the child component instance itself, exposing the reference name it was mounted under and its own internal references. Re-rendering the same child under a different reference name moves the binding (clearing the old name) while keeping the same instance; re-rendering a different child definition builds a new instance and binds it.

**Test Cases:** `rcb_tests/public_test_cases/feature3_6_component_reference.json`

```json
{
    "description": "Render a parent that embeds a child component tagged with a reference name supplied from state. The reference resolves to the child component instance itself (not merely its DOM node), exposing the reference name it was mounted under and its own internal references. When the parent re-renders with a different reference name for the same child definition, the binding moves to the new name and the old name is cleared while the same instance is kept. When the parent re-renders with a different child definition, a new instance is built and bound. Each observation point lists the bound references with the child's serialized element, its mounted reference name, and its nested references.",
    "cases": [
        {
            "input": {"kind": "component", "components": {"A": {"update": [a boolean flag indicating asynchronous execution], "render": {"el": "div", "ref": "self", "children": ["A"]}}, "B": {"render": {"el": "div", "ref": "self", "children": ["B"]}}}, "root": {"state": {"condition": [a boolean flag indicating asynchronous execution], "refName": "child"}, "render": {"if": "condition", "then": {"el": "div", "children": [{"comp": "A", "ref": {"var": "refName"}}]}, "else": {"el": "div", "children": [{"comp": "B", "ref": {"var": "refName"}}]}}}, "steps": [{"probe": "p1"}, {"set": {"refName": "kid"}}, {"updateAsync": [a boolean flag indicating asynchronous execution]}, {"probe": "p2"}, {"set": {"refName": "child", "condition": false}}, {"updateAsync": [a boolean flag indicating asynchronous execution]}, {"probe": "p3"}]},
            "expected_output": "== p1 ==\nelement=<div[a sequence of incremental identifiers]><div[a sequence of incremental identifiers]>A</div></div>\ntext=A\nrefs:\n  child=component element=<div[a sequence of incremental identifiers]>A</div> ref=child\n    self=<div[a sequence of incremental identifiers]>A</div>\n== p2 ==\nelement=<div[a sequence of incremental identifiers]><div[a sequence of incremental identifiers]>A</div></div>\ntext=A\nrefs:\n  kid=component element=<div[a sequence of incremental identifiers]>A</div> ref=kid\n    self=<div[a sequence of incremental identifiers]>A</div>\n== p3 ==\nelement=<div[a sequence of incremental identifiers]><div[a sequence of incremental identifiers]>B</div></div>\ntext=B\nrefs:\n  child=component element=<div[a sequence of incremental identifiers]>B</div> ref=child\n    self=<div[a sequence of incremental identifiers]>B</div>\n"
        }
    ]
}
```

---

### Feature 4: Update Scheduler

**As a developer**, I want updates to be coalesced and run in a predictable order, so many state changes within a frame result in a single, ordered flush.

**Expected Behavior / Usage:**

*4.1 Deferred batch on a frame — queued requests run together, in order, on the next flush*

Update requests submitted in deferred mode do not run immediately; they are queued and all executed in submission order when the next animation frame is flushed. The output is the emitted labels in execution order, one per line.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_async_batch.json`

```json
{
    "description": "Submit several update requests to the deferred update scheduler. None of them run immediately; they are batched and all executed, in submission order, when the next animation frame is flushed. Each request emits a distinct label when it runs; the output is the sequence of emitted labels in execution order, one per line.",
    "cases": [
        {
            "input": {"kind": "scheduler", "mode": "async", "requests": [{"emit": 1}, {"emit": 2}, {"emit": 3}]},
            "expected_output": "1\n2\n3\n"
        }
    ]
}
```

*4.2 Nested deferred requests in the same flush — requests submitted during a flush are drained within it*

When a deferred request, while running, submits further deferred requests (which themselves submit more), all of them are drained within the same animation frame rather than spilling into a later one. The output is the labels in execution order, one per line.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_async_nested.json`

```json
{
    "description": "Submit a single deferred update request that, while running, submits further deferred update requests, which in turn submit more. All requests submitted during the same flush are drained within that same animation frame rather than being deferred to a later one. Each request emits a distinct label; the output is the labels in execution order, one per line.",
    "cases": [
        {
            "input": {"kind": "scheduler", "mode": "async", "requests": [{"emit": 1, "thenAsync": [{"emit": 2, "thenAsync": [{"emit": 3}]}]}]},
            "expected_output": "1\n2\n3\n"
        }
    ]
}
```

*4.3 Synchronous immediate run — a synchronous request runs now and drains nested requests in the same flush*

A synchronous request runs immediately. If, while it runs, a flush is already in progress, any additionally submitted requests (deferred or synchronous) are drained within that same immediate flush in submission order rather than waiting for an animation frame. The output is the labels in execution order, one per line.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_sync_immediate.json`

```json
{
    "description": "Submit an update request to the scheduler in synchronous mode, which runs it immediately. While running, that request submits both a deferred request and another synchronous request. Because a flush is already in progress, the additionally submitted requests are drained within the same immediate flush in submission order rather than waiting for an animation frame. Each request emits a distinct label; the output is the labels in execution order, one per line.",
    "cases": [
        {
            "input": {"kind": "scheduler", "mode": "sync", "requests": [{"emit": 1, "thenAsync": [{"emit": 2}], "thenSync": [{"emit": 3}]}]},
            "expected_output": "1\n2\n3\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the engine: render-specification evaluation, virtual-tree diffing, DOM patching with node reuse, reference binding to DOM nodes and component instances, component composition with same-definition/in-place-update versus rebuild reconciliation, keyed child reordering, and an update scheduler supporting deferred (frame-batched) and synchronous flushing. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint, and the core logic MUST be decoupled from stdin/stdout and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program that reads a single JSON request from stdin and writes the normalized serialization to stdout, matching the per-feature contracts above. It selects behavior by the request's `kind` (`component` vs `scheduler`), translates render specifications and steps into idiomatic calls against the core engine, drives the scheduler deterministically (a flush mechanism that runs queued deferred work synchronously for observation), and translates any native error into a neutral `error=<category>` line (e.g. `[the specific error line formatted for unsupported root changes]`) rather than leaking host-language runtime detail. The adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` containing **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other.


---
**Implementation notes:**
- refer to standard clause types defined in the DSL spec, excluding references
- check the root component's render spec for any 'ref' bindings
