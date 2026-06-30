## Product Requirement Document

# Deferred HTML Rendering Toolkit - Lazy placeholders that resolve over a realtime channel

## Project Goal

Build a server-side rendering toolkit that lets developers emit lightweight placeholder elements in a page and have their real content rendered later and delivered over a realtime channel, without forcing the slow or expensive parts of a page to block the initial response.

---

## Background & Problem

Without this toolkit, developers who want part of a page to load lazily must hand-roll an endpoint, serialize exactly which template and which data to render, sign that payload so a client cannot tamper with it, and wire up a realtime channel to push the rendered markup back. This is repetitive, easy to get wrong, and a frequent source of security mistakes (unsigned render instructions let a client render arbitrary templates or controllers).

With this toolkit, a developer marks a region with a single helper call. The helper emits a placeholder element that embeds a tamper-proof, signed description of what should eventually be rendered. A realtime channel later reads that signed description, renders the real content through the correct controller, and streams it back to replace the placeholder.

This document specifies the externally observable behavior of the toolkit's core building blocks: library configuration, controller resolution, the placeholder element builder, the out-of-band renderer, and the channel stream-name builder.

---

## Program / Dispatcher Contract

All features are exercised through one program that reads a single JSON command object from standard input and writes the result as raw text to standard output. Every command has an `op` field selecting the operation; the remaining fields are the operation's arguments. Unless stated otherwise, output lines are terminated by a newline and contain no test-runner metadata.

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

### Feature 1: Library configuration defaults

**As a developer**, I want stable, inspectable defaults for the library's top-level configuration, so I can rely on a known starting state.

**Expected Behavior / Usage:**

The library's top-level namespace is exposed as a module. It also exposes a boolean configuration flag (selected here by the field name `skip_in_test`) that controls whether rendering is short-circuited in a test environment; its default value is false. The `config` operation takes a `field` selecting which fact to report: `field="module"` prints `kind=Module`; `field="skip_in_test"` prints `skip_in_test=false`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_library_defaults.json`

```json
{
    "description": "Reports whether the library's top-level namespace is exposed as a module and the default value of its test-skip configuration flag. Each case selects a single configuration field to inspect.",
    "cases": [
        {"input": {"op": "config", "field": "module"}, "expected_output": "kind=Module\n"},
        {"input": {"op": "config", "field": "skip_in_test"}, "expected_output": "skip_in_test=false\n"}
    ]
}
```

---

### Feature 2: Configurable default controller

**As a developer**, I want a configurable default controller that the toolkit uses when no specific controller is requested, so deferred rendering runs in a sensible context out of the box.

**Expected Behavior / Usage:**

The toolkit keeps a configurable default controller. When nothing is configured it resolves to the application's conventional base controller (named `ApplicationController`). The `set` field assigns an override by class name (a string); the override is resolved by looking the named class up. A null `set` means no override is configured. The `default_controller` operation prints `default_controller=<resolved class name>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_default_controller.json`

```json
{
    "description": "Resolves the configurable default controller. When no override is set the resolver falls back to the framework's conventional base application controller; when an override name is assigned the resolver resolves that named class. The override is supplied as the 'set' field; a null value means no override.",
    "cases": [
        {"input": {"op": "default_controller", "set": null}, "expected_output": "[a resolved controller class]\n"},
        {"input": {"op": "default_controller", "set": "ActionController::Base"}, "expected_output": "default_[a resolved controller class]\n"}
    ]
}
```

---

### Feature 3: Controller resolution from a signed identifier

**As a developer**, I want to resolve which controller renders a deferred fragment from a tamper-proof identifier, so a client cannot trick the server into rendering through an arbitrary controller.

**Expected Behavior / Usage:**

A controller is resolved from an optional signed identifier. When no signed identifier is supplied, the resolver returns the configured default controller (which may itself be overridden via a `default` field, otherwise the conventional base controller). When a signed identifier is supplied, the resolver verifies the signature and resolves the controller class named by the verified, trusted string. In this operation the `signed_name` field carries the plain controller name; the program signs it with the toolkit's verifier before passing it through resolution, so the round trip exercises real signing and verification. The `resolve_controller` operation prints `controller=<resolved class name>`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_controller_resolution.json`

```json
{
    "description": "Resolves a controller class for deferred rendering. With no signed identifier it returns the configured default controller (optionally overridden via 'default'); with a signed identifier ('signed_name', which the harness signs before passing it through the verifier) it returns the controller class named by that verified, trusted string.",
    "cases": [
        {"input": {"op": "resolve_controller", "signed_name": null}, "expected_output": "controller=ApplicationController\n"},
        {"input": {"op": "resolve_controller", "signed_name": null, "default": "ActionController::Base"}, "expected_output": "[a resolved controller class]\n"},
        {"input": {"op": "resolve_controller", "signed_name": "ActionController::Base"}, "expected_output": "[a resolved controller class]\n"}
    ]
}
```

---

### Feature 4: Placeholder element builder

**As a developer**, I want a single helper that emits a placeholder element carrying a tamper-proof description of what to render later, so I can defer rendering with one call and trust the embedded instructions.

**Expected Behavior / Usage:**

The `futurize` operation builds one or more placeholder elements. The build inputs are: `extends` (the element shape; `"div"` produces a custom element tag, shown in the examples), an optional `partial` (a template identifier) with `locals` (a map of local variables), or a `collection` (a list of items) to fan out over, plus optional `html_options`, `eager`, `broadcast_each`, and a `block` selector. The toolkit signs a description of the render request and embeds it as a tamper-proof data attribute on the element.

For each element produced, the program prints a fixed block of `key=value` lines in this exact order: `tag`, `class`, `data-action`, `data-sgid`, `eager`, `broadcast_each`, `placeholder`, `params`. The literal token `_none_` is printed for any absent value. The `params` value is the signed payload after it has been verified and decoded back to its original structure, re-encoded as compact JSON with all object keys sorted alphabetically. When more than one element is produced, a line containing only `---` separates consecutive element blocks.

*4.1 Signed payload round-trip and HTML option merge — a single placeholder from a template id plus locals*

The element embeds a signed payload that, once verified, reproduces exactly the supplied render description (template identifier and locals). Supplied HTML attributes are merged onto the element: a CSS class appears as the element's `class`, and arbitrary `data` attributes both appear on the element and are folded into the signed payload. The `block` selector `"empty"` attaches an empty placeholder block (so no automatic eager flag is added).

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_signed_payload.json`

```json
{
    "description": "Builds a deferred-render custom element from a template identifier and a set of local variables, then reports the element's tag plus the cryptographically signed payload after it has been verified and decoded back to its original structure. Supplied HTML attributes (a CSS class and arbitrary data-* attributes) are merged onto the element and the data attributes are also folded into the signed payload.",
    "cases": [
        {"input": {"op": "futurize", "extends": "div", "partial": "widgets/card", "locals": {"title": "Hello", "count": 3}, "block": "empty"}, "expected_output": "tag=futurism-element\nclass=_none_\ndata-action=_none_\ndata-sgid=_none_\neager=_none_\nbroadcast_each=_none_\nplaceholder=_none_\nparams={\"locals\":{\"count\":3,\"title\":\"Hello\"},\"partial\":\"widgets/card\"}\n"},
        {"input": {"op": "futurize", "extends": "div", "partial": "widgets/card", "locals": {"title": "Hello"}, "html_options": {"class": "flex justify-center", "data": {"action": "reveal#toggle"}}, "block": "empty"}, "expected_output": "tag=futurism-element\nclass=flex justify-center\ndata-action=reveal#toggle\ndata-sgid=_none_\neager=_none_\nbroadcast_each=_none_\nplaceholder=_none_\nparams={\"data\":{\"action\":\"reveal#toggle\"},\"locals\":{\"title\":\"Hello\"},\"partial\":\"widgets/card\"}\n"}
    ]
}
```

*4.2 Reserved attribute protection — forged signed attributes are stripped*

Two data attributes are reserved by the toolkit: the one carrying the signed payload and the one carrying a signed record identifier. If a caller tries to supply either reserved key through `html_options.data`, it is dropped so it cannot be forged; any other supplied data attribute is preserved on the element and in the signed payload.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_attribute_protection.json`

```json
{
    "description": "Guards the reserved data attributes that carry the signed payload and the signed record identifier: if the caller tries to supply those reserved keys through the element's data attributes, they are dropped so they cannot be forged, while any other supplied data attribute is preserved on the element and inside the signed payload.",
    "cases": [
        {"input": {"op": "futurize", "extends": "div", "partial": "widgets/card", "locals": {"title": "Hello"}, "html_options": {"data": {"controller": "reveal", "sgid": "forged", "signed_params": "forged"}}, "block": "empty"}, "expected_output": "tag=futurism-element\nclass=_none_\ndata-action=_none_\ndata-sgid=_none_\neager=_none_\nbroadcast_each=_none_\nplaceholder=_none_\nparams={\"data\":{\"controller\":\"reveal\"},\"locals\":{\"title\":\"Hello\"},\"partial\":\"widgets/card\"}\n"}
    ]
}
```

*4.3 Eager-loading marker*

An eager-loading marker is emitted as a data attribute when the caller explicitly requests eager loading (`eager: true`), and it is also added automatically when the element is built without a placeholder block (because there is nothing to show while waiting). In both cases the marker value is the string `true`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_eager_flag.json`

```json
{
    "description": "Controls the eager-loading marker emitted as a data attribute on the element. The marker is present when the caller explicitly requests eager loading, and it is also added automatically when the element is built without a placeholder block (because there is nothing to show while waiting).",
    "cases": [
        {"input": {"op": "futurize", "extends": "div", "partial": "widgets/card", "locals": {"title": "Hello"}, "eager": true, "block": "empty"}, "expected_output": "tag=futurism-element\nclass=_none_\ndata-action=_none_\ndata-sgid=_none_\neager=true\nbroadcast_each=_none_\nplaceholder=_none_\nparams={\"locals\":{\"title\":\"Hello\"},\"partial\":\"widgets/card\"}\n"},
        {"input": {"op": "futurize", "extends": "div", "partial": "widgets/card", "locals": {"title": "Hello"}}, "expected_output": "tag=futurism-element\nclass=_none_\ndata-action=_none_\ndata-sgid=_none_\neager=true\nbroadcast_each=_none_\nplaceholder=_none_\nparams={\"locals\":{\"title\":\"Hello\"},\"partial\":\"widgets/card\"}\n"}
    ]
}
```

*4.4 Collection fan-out and indexed locals*

Given a `collection`, the builder produces one element per item. Each element's signed payload carries a pair of locals: the item itself under a name derived from the item's type, and a zero-based counter for that item under `<name>_counter`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_collection_locals.json`

```json
{
    "description": "Builds one element per item when given a collection. For each item the signed payload carries a pair of locals: the item itself under a name derived from the item's type, and a zero-based counter for that item under '<name>_counter'.",
    "cases": [
        {"input": {"op": "futurize", "extends": "div", "collection": ["alpha", "beta"], "block": "empty"}, "expected_output": "tag=futurism-element\nclass=_none_\ndata-action=_none_\ndata-sgid=_none_\neager=_none_\nbroadcast_each=_none_\nplaceholder=_none_\nparams={\"locals\":{\"string\":\"alpha\",\"string_counter\":0}}\n---\ntag=futurism-element\nclass=_none_\ndata-action=_none_\ndata-sgid=_none_\neager=_none_\nbroadcast_each=_none_\nplaceholder=_none_\nparams={\"locals\":{\"string\":\"beta\",\"string_counter\":1}}\n"}
    ]
}
```

*4.5 Per-item broadcast marker*

When a collection is rendered with the per-item broadcast option enabled (`broadcast_each: true`), every generated element carries a data attribute (value `true`) marking it for individual broadcast.

**Test Cases:** `rcb_tests/public_test_cases/feature4_5_broadcast_each.json`

```json
{
    "description": "When a collection is rendered with the per-item broadcast option enabled, every generated element carries a data attribute marking it for individual broadcast.",
    "cases": [
        {"input": {"op": "futurize", "extends": "div", "collection": ["alpha", "beta"], "broadcast_each": true, "block": "empty"}, "expected_output": "tag=futurism-element\nclass=_none_\ndata-action=_none_\ndata-sgid=_none_\neager=_none_\nbroadcast_each=true\nplaceholder=_none_\nparams={\"locals\":{\"string\":\"alpha\",\"string_counter\":0}}\n---\ntag=futurism-element\nclass=_none_\ndata-action=_none_\ndata-sgid=_none_\neager=_none_\nbroadcast_each=true\nplaceholder=_none_\nparams={\"locals\":{\"string\":\"beta\",\"string_counter\":1}}\n"}
    ]
}
```

*4.6 Contextual placeholder block*

When a collection is rendered with a placeholder block, the block is invoked once per item and receives the item together with its zero-based index. The text the block returns becomes the visible placeholder content of the corresponding element, while the signed payload still carries the indexed locals. The `block` selector `"index_item"` denotes a block that returns the one-based position followed by the item (for example, `1. alpha`).

**Test Cases:** `rcb_tests/public_test_cases/feature4_6_collection_placeholder.json`

```json
{
    "description": "When a collection is rendered with a placeholder block, the block is invoked once per item and receives the item together with its zero-based index; the text it returns becomes the visible placeholder content of the corresponding element, while the signed payload still carries the indexed locals.",
    "cases": [
        {"input": {"op": "futurize", "extends": "div", "collection": ["alpha", "beta"], "block": "index_item"}, "expected_output": "tag=futurism-element\nclass=_none_\ndata-action=_none_\ndata-sgid=_none_\neager=_none_\nbroadcast_each=_none_\nplaceholder=1. alpha\nparams={\"locals\":{\"string\":\"alpha\",\"string_counter\":0}}\n---\ntag=futurism-element\nclass=_none_\ndata-action=_none_\ndata-sgid=_none_\neager=_none_\nbroadcast_each=_none_\nplaceholder=2. beta\nparams={\"locals\":{\"string\":\"beta\",\"string_counter\":1}}\n"}
    ]
}
```

---

### Feature 5: Out-of-band inline renderer

**As a developer**, I want to render a template outside the normal request cycle while still giving it a faithful request context, so deferred content renders exactly as it would inside a real request.

**Expected Behavior / Usage:**

The `render_inline` operation configures a renderer from a target `url`, a `connection_env` (a map of environment values copied from the originating connection), and an explicit `params` map, then evaluates the supplied inline `template` through it. The `controller` field selects the rendering controller: an empty object uses the default base controller, and a `helpers` map defines named helper methods on the controller, each returning the given fixed string. The rendered template text is printed followed by a single newline.

*5.1 Request context: environment, query, and explicit params*

The template can read values injected from the connection environment, query-string parameters parsed from the URL, and the explicitly supplied parameters. This holds for the default controller and for any other controller passed in.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_request_context.json`

```json
{
    "description": "Configures an out-of-band renderer from a target URL, a connection environment, and an explicit parameter hash, then evaluates an inline template through it. The template can read values injected from the connection environment, query-string parameters parsed from the URL, and the explicitly supplied parameters. The behaviour holds for the default controller and for any other controller passed in.",
    "cases": [
        {"input": {"op": "render_inline", "controller": {}, "connection_env": {"HTTP_VAR": "[a literal string from connection_env]"}, "url": "http://www.example.org?someParam=1234", "params": {"SOME": "SOME_VALUE"}, "template": "env=<%= request.env['HTTP_VAR'] %> q=<%= params['someParam'] %> p=<%= params['SOME'] %>"}, "expected_output": "env=[a literal string from connection_env] q=1234 p=SOME_VALUE\n"},
        {"input": {"op": "render_inline", "controller": {"helpers": {"feature_flag": "on"}}, "connection_env": {"HTTP_VAR": "[a literal string from connection_env]"}, "url": "http://www.example.org?someParam=1234", "params": {"SOME": "SOME_VALUE"}, "template": "env=<%= request.env['HTTP_VAR'] %> q=<%= params['someParam'] %> p=<%= params['SOME'] %>"}, "expected_output": "env=[a literal string from connection_env] q=1234 p=SOME_VALUE\n"}
    ]
}
```

*5.2 Controller helper methods are callable from the template*

Helper methods exposed by the resolving controller are callable from the inline template. The controller is configured with a named helper returning a fixed string, and the template invokes that helper by name.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_controller_helper.json`

```json
{
    "description": "Helper methods exposed by the resolving controller are callable from the inline template rendered through the out-of-band renderer. The controller is configured with a named helper returning a fixed string, and the template invokes that helper by name.",
    "cases": [
        {"input": {"op": "render_inline", "controller": {"helpers": {"greeting": "FUTURISM"}}, "connection_env": {"HTTP_VAR": "v"}, "url": "http://www.example.org", "params": {}, "template": "Hi <%= greeting %>"}, "expected_output": "Hi FUTURISM\n"}
    ]
}
```

*5.3 Reconstructed request URL and tolerant routing*

The renderer reconstructs the request from the supplied URL so the template can observe the full request URL. This works for URLs whose path matches a registered route under any HTTP verb. An unmatched path still renders without raising an error; only a warning is emitted to standard error, and the reconstructed URL is still produced on standard output.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_request_url.json`

```json
{
    "description": "The renderer reconstructs the request from the supplied URL so that the template can observe the full request URL. This works for URLs whose path matches a registered route under any HTTP verb, and an unmatched path still renders without raising an error (a warning is emitted to standard error only).",
    "cases": [
        {"input": {"op": "render_inline", "controller": {}, "connection_env": {"HTTP_VAR": "v"}, "url": "[the full computed URL string]", "params": {}, "template": "<%= request.url %>"}, "expected_output": "[the full computed URL string]\n"}
    ]
}
```

---

### Feature 6: Channel stream-name builder

**As a developer**, I want a deterministic broadcast stream name derived from the subscription's channel and identity, so deferred content is delivered only to the right subscribers.

**Expected Behavior / Usage:**

The stream name is computed by joining the requested channel name with the present connection identifier values. Each identifier contributes a value; an identifier object that exposes an id contributes its id. Present (non-blank) identifier values are joined by a semicolon, and the channel name is joined to that with a colon. The `stream_name` operation takes a `channel` name and an `identifiers` map (each value is either a scalar or an object with an `id`) and prints `stream_name=<value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_stream_name.json`

```json
{
    "description": "Computes the broadcast stream name for a subscription by joining the requested channel name with the present connection identifier values. An identifier object that exposes an id contributes its id; the result is the channel name and the identifier value joined by a colon.",
    "cases": [
        {"input": {"op": "stream_name", "channel": "ChatRoom", "identifiers": {"current_user": {"id": 1}}}, "expected_output": "stream_name=ChatRoom:1\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON command from standard input and prints the result to standard output, matching the per-leaf-feature contracts above.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- check the standard fallback behavior for unresolved controllers
- inspect the collection indexing mechanism in futurize
