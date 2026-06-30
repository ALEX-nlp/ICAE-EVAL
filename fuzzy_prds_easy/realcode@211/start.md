## Product Requirement Document

# Convention-Driven RESTful Resource Controller — Standard CRUD Behavior For Web Resources

## Project Goal

Build a controller framework that gives any web resource a complete set of standard create/read/update/delete actions by convention, so developers can expose a resource over HTTP without hand-writing the same lookup, persistence, redirect, flash, and view-rendering boilerplate for every resource they add.

---

## Background & Problem

A typical web application exposes many resources, and for each one a developer writes the same seven request handlers: list the collection, show one member, render a blank member for a creation form, render an existing member for an edit form, persist a newly built member, apply changes to an existing member, and delete a member. Each handler repeats the same shape: talk to the backing data store, expose the loaded object(s) to the view under a conventional name, render the right template, and — for writes — either redirect on success (with a confirmation flash message) or re-render the form on validation failure.

Without a framework, this boilerplate is copied per resource, drifts out of sync, and is easy to get subtly wrong (wrong redirect target, missing flash, wrong status). With this framework, a controller bound to a resource inherits all seven actions and their conventional behavior automatically, while still allowing per-controller configuration of naming, lookup strategy, supported representations, and which actions are enabled.

This specification defines the externally-observable contract of those actions: which data-store interaction each action performs, what object it exposes and under what name, the resulting HTTP status, the rendered view or redirect target, and any flash message — independent of any particular implementation language.

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

Every request is a single JSON object. Common fields: `action` (one of `index`, `show`, `new`, `edit`, `create`, `update`, `destroy`); `id` (the member identifier, for member-scoped actions); `attributes` (a flat map of submitted field values, for writes); `format` (the requested representation, default `html`); `config` (per-controller settings, see features 3–5); and `data` (a description of how the backing data store should behave for this request: `list` is the collection a query returns, `record` is the member a lookup or build returns and carries its `id`, `persist` says whether a write succeeds, and `errors` is the validation-error map present on failure).

Every response is a stable, line-based transcript of `key=value` lines in a fixed order. Data-store interactions are reported first as `store=...` lines (`store=list_all`, `store=find id=[a dynamic placeholder for a lookup identifier]`, `store=find_by <field>=<value>`, `store=build attrs={...}`, `store=save ok=<bool>`, `store=update attrs={...} ok=<bool>`, `store=destroy ok=<bool>`). Then `assign=<name>` reports the conventional name the loaded object(s) are exposed under (with `size=<n>` for a collection). Then `status=<http-code>`. Then exactly one of `redirect=<url>` (for a 302) or `body=<rendered view text>` (otherwise). Finally any flash message as `flash.notice=<text>` or `flash.alert=<text>`. The `attrs={...}` rendering lists submitted fields as `key=value` pairs sorted by key, comma-separated, inside braces (`{}` when empty). The example resource throughout is named `article` (plural `articles`), so its canonical member URL is `http://test.host/articles/[a dynamic placeholder for a lookup identifier]` and its collection URL is `http://test.host/articles`.

### Feature 1: Read Actions (Collection & Member Loading)

**As a developer**, I want list/show/new/edit handled by convention, so I can read and present resources without writing lookup-and-render boilerplate.

**Expected Behavior / Usage:**

*1.1 List the collection — query every record and expose it under the plural name*

For an `index` request the controller queries the backing store for the whole collection (`store=list_all`), exposes the returned records under the resource's plural name, and renders the collection view with status 200. The `assign` line reports the plural name and the number of records exposed.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_list_collection.json`

```json
{
    "description": "Issue a read request for the whole collection of a resource. The controller queries the backing data store for every record and exposes the result under the resource's plural name, then renders the collection view with a success status. The transcript reports the data-store query that was made, the name of the exposed collection together with how many records it holds, the HTTP status, and the rendered view body.",
    "cases": [
        {
            "input": {"action": "index", "data": {"list": [{"id": 1}, {"id": 2}, {"id": 3}]}},
            "expected_output": "store=list_all\nassign=articles size=3\nstatus=200\nbody=Index HTML\n"
        }
    ]
}
```

*1.2 Show a member — look it up by id and expose it under the singular name*

For a `show` request the controller looks the record up by `id` (`store=find id=[a dynamic placeholder for a lookup identifier]`), exposes it under the singular name, and renders the member view with status 200.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_show_member.json`

```json
{
    "description": "Issue a read request for a single member of a resource identified by its id. The controller looks the record up in the data store by that id, exposes it under the resource's singular name, and renders the member view with a success status. The transcript reports the lookup performed (with the id used), the exposed name, the status, and the rendered body.",
    "cases": [
        {
            "input": {"action": "show", "id": "42", "data": {"record": {"id": "42"}}},
            "expected_output": "store=find id=42\nassign=article\nstatus=200\nbody=Show HTML\n"
        }
    ]
}
```

*1.3 New member form — build a fresh unsaved record*

For a `new` request the controller asks the store to build a fresh, unsaved record with no submitted attributes (`store=build attrs={}`), exposes it under the singular name, and renders the new-member view with status 200.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_new_form.json`

```json
{
    "description": "Issue a read request for a blank member used to back a creation form. The controller asks the data store to build a fresh, unsaved record (with no submitted attributes), exposes it under the resource's singular name, and renders the new-member view with a success status.",
    "cases": [
        {
            "input": {"action": "new"},
            "expected_output": "store=build attrs={}\nassign=article\nstatus=200\nbody=New HTML\n"
        }
    ]
}
```

*1.4 Edit member form — look an existing member up by id*

For an `edit` request the controller looks the record up by `id`, exposes it under the singular name, and renders the edit-member view with status 200.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_edit_form.json`

```json
{
    "description": "Issue a read request for an existing member used to back an edit form. The controller looks the record up by id, exposes it under the singular name, and renders the edit-member view with a success status.",
    "cases": [
        {
            "input": {"action": "edit", "id": "42", "data": {"record": {"id": "42"}}},
            "expected_output": "store=find id=42\nassign=article\nstatus=200\nbody=Edit HTML\n"
        }
    ]
}
```

---

### Feature 2: Write Actions (Persistence, Redirect & Flash)

**As a developer**, I want create/update/destroy handled by convention, so a write either confirms and redirects on success or re-presents the form on failure, with the right flash message, automatically.

**Expected Behavior / Usage:**

*2.1 Create a member — build from submitted attributes, then persist*

For a `create` request the controller builds a record from the submitted `attributes` (`store=build attrs={...}`) and asks the store to persist it (`store=save ok=<bool>`). On success (status 302) the response redirects to the new member's canonical URL and sets a success notice naming the resource. On failure the controller re-renders the new-member view with status 200 and sets no flash.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_create_member.json`

```json
{
    "description": "Submit attributes to create a new member. The controller builds a record from the submitted attributes and asks the data store to persist it. On successful persistence the response is a redirect to the canonical URL of the newly created member and a success flash notice naming the resource. When persistence fails (the record reports validation errors) the controller re-renders the new-member view with a success status and sets no flash.",
    "cases": [
        {
            "input": {"action": "create", "attributes": {"title": "Hello"}, "data": {"record": {"id": "42"}, "persist": true}},
            "expected_output": "store=build attrs={title=Hello}\nstore=save ok=true\nassign=article\nstatus=302\nredirect=http://test.host/articles/42\nflash.notice=Article was successfully created.\n"
        },
        {
            "input": {"action": "create", "attributes": {"title": "Hello"}, "data": {"persist": false, "errors": {"title": "is blank"}}},
            "expected_output": "store=build attrs={title=Hello}\nstore=save ok=false\nassign=article\nstatus=200\nbody=New HTML\n"
        }
    ]
}
```

*2.2 Update a member — look up by id, then apply submitted attributes*

For an `update` request the controller looks the record up by `id` and asks it to apply the submitted `attributes` (`store=update attrs={...} ok=<bool>`). On success it redirects (302) to the member's canonical URL with a success notice; on failure it re-renders the edit-member view with status 200 and no flash.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_update_member.json`

```json
{
    "description": "Submit attributes to update an existing member identified by id. The controller looks the record up by id and asks it to apply the submitted attributes. On success the response redirects to the member's canonical URL with a success flash notice naming the resource. On failure (validation errors) the controller re-renders the edit-member view with a success status and no flash.",
    "cases": [
        {
            "input": {"action": "update", "id": "42", "attributes": {"title": "New"}, "data": {"record": {"id": "42"}, "persist": true}},
            "expected_output": "store=find id=42\nstore=update attrs={title=New} ok=true\nassign=article\nstatus=302\nredirect=http://test.host/articles/42\nflash.notice=Article was successfully updated.\n"
        },
        {
            "input": {"action": "update", "id": "42", "attributes": {"title": "New"}, "data": {"record": {"id": "42"}, "persist": false, "errors": {"title": "is blank"}}},
            "expected_output": "store=find id=42\nstore=update attrs={title=New} ok=false\nassign=article\nstatus=200\nbody=Edit HTML\n"
        }
    ]
}
```

*2.3 Destroy a member — look up by id, delete, redirect to collection*

For a `destroy` request the controller looks the record up by `id` and asks it to delete itself (`store=destroy ok=<bool>`), then redirects (302) to the collection URL. On success the flash carries a notice naming the resource; on failure it carries an alert naming the resource. The redirect target is the collection either way.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_destroy_member.json`

```json
{
    "description": "Request deletion of an existing member identified by id. The controller looks the record up by id and asks it to delete itself, then redirects to the collection URL. On success the flash carries a notice naming the resource; on failure the flash carries an alert naming the resource. Either way the response is a redirect to the collection.",
    "cases": [
        {
            "input": {"action": "destroy", "id": "42", "data": {"record": {"id": "42"}, "persist": true}},
            "expected_output": "store=find id=42\nstore=destroy ok=true\nassign=article\nstatus=302\nredirect=http://test.host/articles\nflash.notice=Article was successfully destroyed.\n"
        },
        {
            "input": {"action": "destroy", "id": "42", "data": {"record": {"id": "42"}, "persist": false, "errors": {"base": "locked"}}},
            "expected_output": "store=find id=42\nstore=destroy ok=false\nassign=article\nstatus=302\nredirect=http://test.host/articles\nflash.alert=Article could not be destroyed.\n"
        }
    ]
}
```

---

### Feature 3: Response Format Negotiation

**As a developer**, I want the controller to honor the requested representation and fail cleanly on unsupported ones, so write actions can drive a scripted client and unknown formats produce a predictable, neutral error.

**Expected Behavior / Usage:**

A controller declares which representations it supports. When a supported script representation is requested (`format: "js"`), a successful write renders the action's script view with status 200 instead of redirecting, while still setting the success notice. When a representation the controller does not support is requested, the request fails; the failure is reported as a single neutral category line `error=unsupported_format` — no host runtime type, message, or stack detail may appear.

**Test Cases:** `rcb_tests/public_test_cases/feature3_format_negotiation.json`

```json
{
    "description": "Drive write actions while requesting a non-default representation, and request an unsupported representation. When a script representation is requested and supported, a successful create or update renders the action's script view with a success status (instead of redirecting) while still setting the success flash notice. When a representation that the controller does not support is requested, the request fails and the error is reported as a neutral category rather than leaking any runtime detail.",
    "cases": [
        {
            "input": {"action": "create", "attributes": {"title": "Hello"}, "format": "js", "config": {"formats": ["html", "js"]}, "data": {"record": {"id": "42"}, "persist": true}},
            "expected_output": "store=build attrs={title=Hello}\nstore=save ok=true\nassign=article\nstatus=200\nbody=Create JS\nflash.notice=Article was successfully created.\n"
        },
        {
            "input": {"action": "show", "id": "42", "format": "js", "data": {"record": {"id": "42"}}},
            "expected_output": "error=unsupported_format\n"
        }
    ]
}
```

---

### Feature 4: Per-Controller Configuration

**As a developer**, I want to override the conventional names and the member-lookup strategy, so a controller can fit an existing data model without abandoning the conventions.

**Expected Behavior / Usage:**

*4.1 Custom exposed names — override the singular and plural exposure names*

A controller may configure custom singular and plural names (`config.entity_name`, `config.collection_name`). Those chosen names then appear as the `assign` name in read responses, while routing and rendering are unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_custom_names.json`

```json
{
    "description": "Configure the controller to expose its records under custom singular and plural names instead of the names derived from the resource. The chosen names appear as the exposed-variable names in read responses, while routing and rendering are unaffected.",
    "cases": [
        {
            "input": {"action": "index", "config": {"entity_name": "writer", "collection_name": "writings"}, "data": {"list": [{"id": 1}, {"id": 2}]}},
            "expected_output": "store=list_all\nassign=writings size=2\nstatus=200\nbody=Index HTML\n"
        },
        {
            "input": {"action": "show", "id": "9", "config": {"entity_name": "writer", "collection_name": "writings"}, "data": {"record": {"id": "9"}}},
            "expected_output": "store=find id=9\nassign=writer\nstatus=200\nbody=Show HTML\n"
        }
    ]
}
```

*4.2 Custom member lookup — resolve members by a chosen attribute*

A controller may configure a custom lookup attribute (`config.[the specific configuration key for lookup field matching]`). Member-scoped actions then resolve the record through that attribute, reported as `store=find_by <field>=<value>` instead of `store=find id=<value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_custom_lookup.json`

```json
{
    "description": "Configure the controller to look members up by a custom attribute instead of the default id-based lookup. Member-scoped read and write actions then resolve the record through that attribute, which is visible in the data-store interaction reported in the transcript.",
    "cases": [
        {
            "input": {"action": "show", "id": "forty-two", "config": {"[the specific configuration key for lookup field matching]": "slug"}, "data": {"record": {"id": "forty-two"}}},
            "expected_output": "store=find_by slug=forty-two\nassign=article\nstatus=200\nbody=Show HTML\n"
        }
    ]
}
```

---

### Feature 5: Post-Write Redirect Target Resolution

**As a developer**, I want the post-write redirect to adapt to which actions the controller actually exposes, so a write redirects somewhere sensible even when the member page does not exist.

**Expected Behavior / Usage:**

After a successful write the controller redirects to the most specific URL available. By default a successful create redirects to the created member's canonical URL. When the member (show) action is disabled for the controller (`config.disabled_actions` includes `show`), there is no member URL to target, so the controller falls back to the collection URL. The success notice is unaffected by the fallback.

**Test Cases:** `rcb_tests/public_test_cases/feature5_redirect_fallback.json`

```json
{
    "description": "Show how the post-write redirect target is resolved. By default a successful create redirects to the canonical URL of the created member. When the member (show) action is disabled for the controller, there is no member URL to redirect to, so the controller falls back to redirecting to the collection URL instead. The flash notice is unaffected.",
    "cases": [
        {
            "input": {"action": "create", "attributes": {"title": "Hello"}, "data": {"record": {"id": "42"}, "persist": true}},
            "expected_output": "store=build attrs={title=Hello}\nstore=save ok=true\nassign=article\nstatus=302\nredirect=http://test.host/articles/42\nflash.notice=Article was successfully created.\n"
        },
        {
            "input": {"action": "create", "attributes": {"title": "Hello"}, "config": {"disabled_actions": ["show"]}, "data": {"record": {"id": "42"}, "persist": true}},
            "expected_output": "store=build attrs={title=Hello}\nstore=save ok=true\nassign=article\nstatus=302\nredirect=http://test.host/articles\nflash.notice=Article was successfully created.\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the convention-driven resource-controller framework described above (action set, data-store interaction, conventional exposure naming, view rendering, redirect-target resolution, flash messaging, format negotiation, and per-controller configuration). Its physical structure MUST align with the "Scale-Driven Code Organization" constraint. The core controller behavior must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, drives the appropriate controller action against a backing data store whose behavior is described by the request's `data` block, and prints the resulting transcript (or a neutral `error=<category>` line) to stdout, matching the per-feature contracts above. The adapter is solely responsible for translating JSON into idiomatic calls and for normalizing any native errors into the neutral wire categories; the core controller code must never deal in JSON or stdout.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the same resource identifier substitution pattern as seen in C029
- follow the view naming convention established in the view mapping table
