## Product Requirement Document

# Declarative Path Router Engine - Pattern Matching, State Machine & Selectors

## Project Goal

Build a small, framework-agnostic routing engine that allows developers to describe an application's navigable areas declaratively and let a central store decide which area is active. The engine answers three questions for any moment in time: does a given route pattern match the current location, what named parameters did it capture, and which registered routes are currently active. It is the headless core that a UI layer can connect to without re-implementing path matching or navigation bookkeeping.

---

## Background & Problem

Without this engine, developers wiring client-side navigation into a state container are forced to hand-roll route-pattern parsing (named parameters, optional segments, trailing wildcards), manually strip query strings and hashes before matching, and keep a table of "which routes are active right now" in sync on every location change. This leads to repetitive, error-prone boilerplate scattered across components, and subtle inconsistencies between how a route is registered and how it is later queried.

With this engine, a route pattern is matched against a location in one call, navigation is reduced to dispatching plain command objects through a single reducer that re-evaluates the whole route table, and components ask simple selector questions ("is this route active?", "what are its params?") against the resulting state. The engine owns the matching rules and the active-route bookkeeping so the rest of the app does not have to.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain has several distinct responsibilities — pattern matching, action/command creation, the reduction state machine, and read-only selectors — so it MUST be organized into clearly separated modules rather than a single "god file", while not being over-engineered beyond those responsibilities.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in the "Core Features" section define a **black-box contract** for an execution adapter, NOT the internal data model. The core routing logic must remain decoupled from stdin/stdout and JSON parsing. A thin execution adapter is solely responsible for translating JSON commands into idiomatic calls on the core engine and rendering results as the line-based text contract below.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Keep parsing/matching, command creation, reduction, and selection as distinct units.
   - **Open/Closed Principle (OCP):** New command kinds or selectors should extend the engine without rewriting the matcher.
   - **Liskov Substitution Principle (LSP):** Command objects of different kinds must be interchangeable wherever a generic command is accepted.
   - **Interface Segregation Principle (ISP):** Read-only selectors must not force callers to depend on mutation APIs.
   - **Dependency Inversion Principle (DIP):** The browser-history side effect must sit behind an abstraction, not be baked into core matching.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public surface must be elegant and idiomatic to the target language, hiding pattern-compilation details.
   - **Resilience:** Edge cases (absent state, missing route entries, optional parameters without values, query/hash suffixes) must be handled gracefully and produce well-defined output rather than faults. Errors must be modeled as neutral, language-independent categories.

---

## Core Features

### Feature 1: Route Pattern Matching

**As a developer**, I want to test a URL path against a route pattern and extract its named parameters, so I can decide which area of the app should render for the current location.

**Expected Behavior / Usage:**

The input is a route **pattern** and an **active location**. The matcher reports `active=true` or `active=false` on the first line. When the pattern matches, each captured named parameter is reported on its own following line as `param.<name>=<value>`, with parameters ordered by name. A pattern matches only when it covers the entire location path — a single named segment (`/product/:id`) does not match a deeper path (`/product/1/edit`), but a pattern with a trailing literal (`/product/:id/edit`) does. Optional parameters (suffix `?`) match whether or not a value is present; when absent the parameter is still reported with an empty value (`param.id=`). Before matching, any query string (`?...`) or hash (`#...`) suffix is stripped from the location, so `/product/1?asdf=123` matches `/product/:id` and captures `id=1`. Captured values are taken verbatim and are **not** URL-decoded, so `%2F` is preserved in the captured value.

**Test Cases:** `rcb_tests/public_test_cases/feature1_route_matching.json`

```json
{
    "description": "Match a URL path against a route pattern. Output reports whether the pattern matches and, when it does, the captured named parameters. Covers static segments, single and multiple named parameters, trailing literal segments, optional parameters with and without values, query/hash stripping, and that values are not URL-decoded.",
    "cases": [
        {"input": {"op": "match_route", "route": "/contact", "active_route": "/contact"}, "expected_output": "active=true"},
        {"input": {"op": "match_route", "route": "/product/:id", "active_route": "/product/1"}, "expected_output": "active=true\nparam.id=1"},
        {"input": {"op": "match_route", "route": "/product/:id", "active_route": "/other/1"}, "expected_output": "active=false"},
        {"input": {"op": "match_route", "route": "/product/:id/edit", "active_route": "/product/1/edit"}, "expected_output": "active=true\nparam.id=1"},
        {"input": {"op": "match_route", "route": "/product/:id?", "active_route": "/product"}, "expected_output": "active=true\nparam.id="},
        {"input": {"op": "match_route", "route": "/product/:id", "active_route": "/product/1?asdf=123"}, "expected_output": "active=true\nparam.id=1"},
        {"input": {"op": "match_route", "route": "/product/:id", "active_route": "/product/before%2Fafter"}, "expected_output": "active=true\nparam.id=before%2Fafter"}
    ]
}
```

---

### Feature 2: Browser History Navigation

**As a developer**, I want a navigation primitive that pushes a target URL onto the browser history stack, so the address bar reflects programmatic navigation without a full page reload.

**Expected Behavior / Usage:**

The input is a target URL. The engine pushes that URL onto the browser history stack as a new entry, and the output echoes the URL that was pushed as `history_pushState=<url>`. The full URL is pushed verbatim, including any query string and hash, so `/products/42?ref=home#top` is preserved exactly.

**Test Cases:** `rcb_tests/public_test_cases/feature2_history_navigation.json`

```json
{
    "description": "Navigate the browser to a path. The navigation service pushes the target URL onto the browser history stack; output echoes the URL that was pushed.",
    "cases": [
        {"input": {"op": "navigate_history", "route": "/about"}, "expected_output": "history_pushState=/about"},
        {"input": {"op": "navigate_history", "route": "/products/42?ref=home#top"}, "expected_output": "history_pushState=/products/42?ref=home#top"}
    ]
}
```

---

### Feature 3: Navigation Command Creation

**As a developer**, I want factory functions that produce well-typed navigation command objects, so I can dispatch intent through the store without constructing plain literals by hand.

**Expected Behavior / Usage:**

Each command carries a discriminator (`type`) and a `path`. The output renders `type=<discriminator>` followed by `path=<path>`.

*3.1 Register-Route Command — produces a command that requests a route pattern be registered.*

The discriminator is `ADD_ROUTE`. The given path is carried through unchanged, including the root path `/`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_add_route_action.json`

```json
{
    "description": "Create an add-route command object for a given path. Output reports the command discriminator and the path it carries.",
    "cases": [
        {"input": {"op": "action", "kind": "add_route", "path": "/"}, "expected_output": "type=ADD_ROUTE\npath=/"},
        {"input": {"op": "action", "kind": "add_route", "path": "/about"}, "expected_output": "type=ADD_ROUTE\npath=/about"}
    ]
}
```

*3.2 Set-Active-Route Command — produces a command that requests the active location be changed.*

The discriminator is `SET_ACTIVE_ROUTE`. The given path is carried through unchanged, including the empty path.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_set_active_route_action.json`

```json
{
    "description": "Create a set-active-route command object for a given path. Output reports the command discriminator and the path it carries.",
    "cases": [
        {"input": {"op": "action", "kind": "set_active_route", "path": ""}, "expected_output": "type=SET_ACTIVE_ROUTE\npath="},
        {"input": {"op": "action", "kind": "set_active_route", "path": "/about"}, "expected_output": "type=SET_ACTIVE_ROUTE\npath=/about"}
    ]
}
```

*3.3 Navigate Command — produces a navigate command and performs the navigation side effect.*

The discriminator is `NAVIGATE` and the path is carried through unchanged. Creating this command also pushes the path onto the browser history stack (see Feature 2) as a side effect, so the output additionally reports `history_pushState=<path>`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_navigate_action.json`

```json
{
    "description": "Create a navigate command object for a given path. Building this command also pushes the path onto the browser history stack as a side effect. Output reports the command discriminator, the path it carries, and the URL pushed to history.",
    "cases": [
        {"input": {"op": "action", "kind": "navigate", "path": "/about"}, "expected_output": "type=NAVIGATE\npath=/about\nhistory_pushState=/about"}
    ]
}
```

---

### Feature 4: Routing State Machine (Reducer)

**As a developer**, I want a pure reducer that folds navigation commands into an immutable routing state, so the set of active routes is always a deterministic function of the registered routes and the active location.

**Expected Behavior / Usage:**

The state has an `activeRoute` (the current location) and a `routes` table mapping each registered pattern to its `{active, params}`. The output renders `activeRoute=<location>` first, then for each route in the table (ordered by pattern) `route[<pattern>].active=<bool>` followed by `route[<pattern>].param.<name>=<value>` lines for any captured parameters.

*4.1 Default & Pass-Through — absent state yields the initial state; unrecognized input leaves state unchanged.*

When no state is supplied, the engine starts from an initial state whose active route is `/` and whose route table is empty. Reducing with no command returns the supplied state unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_default_state.json`

```json
{
    "description": "Reduce with no action (or an unrecognized action) returns the current state unchanged; an absent state yields the initial state whose active route is '/' and whose route table is empty.",
    "cases": [
        {"input": {"op": "reduce"}, "expected_output": "activeRoute=/"},
        {"input": {"op": "reduce", "state": {"activeRoute": "/about", "routes": {}}}, "expected_output": "activeRoute=/about"}
    ]
}
```

*4.2 Register-Route Reduction — inserts a pattern into the table and computes its active flag at insertion time.*

An `ADD_ROUTE` command adds the path to the route table. The new entry's active flag is evaluated against the **current** active route at the moment of insertion, so a route equal to the active location is registered as active.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_add_route_reduction.json`

```json
{
    "description": "Reduce an add-route command: the path is inserted into the route table, and its active flag is computed against the current active route at insertion time.",
    "cases": [
        {"input": {"op": "reduce", "action": {"path": "/contact", "type": "ADD_ROUTE"}}, "expected_output": "activeRoute=/\nroute[/contact].active=false"},
        {"input": {"op": "reduce", "state": {"activeRoute": "/contact", "routes": {}}, "action": {"path": "/contact", "type": "ADD_ROUTE"}}, "expected_output": "activeRoute=/contact\nroute[/contact].active=true"}
    ]
}
```

*4.3 Set-Active-Route Reduction — changes the active location and re-evaluates the whole table.*

A `SET_ACTIVE_ROUTE` command sets `activeRoute` to the command path and re-evaluates **every** registered route against the new location, updating each route's active flag and captured parameters. A parameterized pattern that matches the new location becomes active and exposes its parameters; one that does not match becomes inactive.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_set_active_route_reduction.json`

```json
{
    "description": "Reduce a set-active-route command: the active route becomes the command path and every route in the table is re-evaluated for match and parameters against the new active route.",
    "cases": [
        {"input": {"op": "reduce", "state": {"activeRoute": "/", "routes": {"/about": {"active": false, "params": {}}, "/contact": {"active": false, "params": {}}, "/home": {"active": false, "params": {}}}}, "action": {"path": "/contact", "type": "SET_ACTIVE_ROUTE"}}, "expected_output": "activeRoute=/contact\nroute[/about].active=false\nroute[/contact].active=true\nroute[/home].active=false"},
        {"input": {"op": "reduce", "state": {"activeRoute": "/", "routes": {"/about": {"active": false, "params": {}}, "/products/:id": {"active": false, "params": {}}}}, "action": {"path": "/products/shirt", "type": "SET_ACTIVE_ROUTE"}}, "expected_output": "activeRoute=/products/shirt\nroute[/about].active=false\nroute[/products/:id].active=true\nroute[/products/:id].param.id=shirt"},
        {"input": {"op": "reduce", "state": {"activeRoute": "/", "routes": {"/about": {"active": false, "params": {}}, "/products/:id": {"active": false, "params": {}}}}, "action": {"path": "/about", "type": "SET_ACTIVE_ROUTE"}}, "expected_output": "activeRoute=/about\nroute[/about].active=true\nroute[/products/:id].active=false"}
    ]
}
```

*4.4 Navigate Reduction — same active-location update as set-active-route.*

A `NAVIGATE` command updates the active location and re-evaluates the route table identically to set-active-route.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_navigate_reduction.json`

```json
{
    "description": "Reduce a navigate command: like set-active-route, the active route becomes the command path and every route in the table is re-evaluated for match and parameters against the new active route.",
    "cases": [
        {"input": {"op": "reduce", "action": {"path": "/contact", "type": "NAVIGATE"}}, "expected_output": "activeRoute=/contact"},
        {"input": {"op": "reduce", "state": {"activeRoute": "/", "routes": {"/about": {"active": false, "params": {}}, "/products/:id": {"active": false, "params": {}}}}, "action": {"path": "/products/shirt", "type": "NAVIGATE"}}, "expected_output": "activeRoute=/products/shirt\nroute[/about].active=false\nroute[/products/:id].active=true\nroute[/products/:id].param.id=shirt"}
    ]
}
```

---

### Feature 5: Routing State Selectors

**As a developer**, I want read-only query functions over the routing state, so components can ask targeted questions without knowing the state's internal shape.

**Expected Behavior / Usage:**

Selectors operate on a state object containing the routing sub-state (active route plus a `routes` table of `{active, params}` entries).

*5.1 Get Route — look up a single route entry by pattern.*

Reports `found=true` and the entry's `active` flag plus parameters when the pattern is registered, otherwise `found=false`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_get_route.json`

```json
{
    "description": "Look up a single route entry by path. Output reports whether the entry exists and, when present, its active flag and parameters.",
    "cases": [
        {"input": {"op": "select", "select": "get_route", "route": "/about", "state": {"router": {"activeRoute": "/", "routes": {"/about": {"active": true, "params": {"id": "1"}}}}}}, "expected_output": "found=true\nactive=true\nparam.id=1"},
        {"input": {"op": "select", "select": "get_route", "route": "/about", "state": {"router": {"activeRoute": "/", "routes": {}}}}, "expected_output": "found=false"}
    ]
}
```

*5.2 No Route Active — test whether the table has zero active routes.*

Reports `no_route_active=true` only when no entry is active.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_no_route_active.json`

```json
{
    "description": "Determine whether the route table has zero active routes. Output is a single boolean signal.",
    "cases": [
        {"input": {"op": "select", "select": "no_route_active", "state": {"router": {"activeRoute": "/", "routes": {"/about": {"active": false}, "/contact": {"active": false}}}}}, "expected_output": "no_route_active=true"},
        {"input": {"op": "select", "select": "no_route_active", "state": {"router": {"activeRoute": "/", "routes": {"/": {"active": true}, "/about": {"active": false}}}}}, "expected_output": "no_route_active=false"}
    ]
}
```

*5.3 Is Route Active — test activeness of a specific route, or of the whole table.*

When a pattern is supplied, reports `active=true` only when that registered entry is active, and `active=false` when the entry is absent. When no pattern is supplied, reports `active=true` when no route at all is active (the whole-table negation).

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_is_route_active.json`

```json
{
    "description": "Determine whether a given route is active. When a path is supplied, the result reflects that route entry (false when the entry is absent). When no path is supplied, the result reflects whether no route at all is active.",
    "cases": [
        {"input": {"op": "select", "select": "is_route_active", "route": "/about", "state": {"router": {"activeRoute": "/", "routes": {"/about": {"active": true}}}}}, "expected_output": "active=true"},
        {"input": {"op": "select", "select": "is_route_active", "state": {"router": {"activeRoute": "/", "routes": {"/about": {"active": false}, "/contact": {"active": false}}}}}, "expected_output": "active=true"},
        {"input": {"op": "select", "select": "is_route_active", "route": "/about", "state": {"router": {"activeRoute": "/", "routes": {"/about": {"active": false}}}}}, "expected_output": "active=false"},
        {"input": {"op": "select", "select": "is_route_active", "route": "/about", "state": {"router": {"activeRoute": "/", "routes": {}}}}, "expected_output": "active=false"}
    ]
}
```

*5.4 Get Route Params — retrieve captured parameters for a route.*

Reports `param_count=<n>` followed by a `param.<name>=<value>` line per parameter. An absent route yields an empty parameter set (`param_count=0`).

**Test Cases:** `rcb_tests/public_test_cases/feature5_4_get_route_params.json`

```json
{
    "description": "Retrieve the captured parameters for a given route. Output reports the parameter count and each parameter; an absent route yields an empty parameter set.",
    "cases": [
        {"input": {"op": "select", "select": "get_route_params", "route": "/about", "state": {"router": {"activeRoute": "/", "routes": {}}}}, "expected_output": "param_count=0"},
        {"input": {"op": "select", "select": "get_route_params", "route": "/about", "state": {"router": {"activeRoute": "/", "routes": {"/about": {"active": true, "params": {"id": "1"}}}}}}, "expected_output": "param_count=1\nparam.id=1"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above, with pattern matching, command creation, the reduction state machine, and selectors organized into clearly separated modules. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable entry point that reads a single JSON command from stdin, invokes the appropriate core logic, and prints the line-based text result to stdout, strictly matching the per-leaf-feature contracts above. The adapter is responsible for normalizing any error into a neutral category line (e.g. `error=<category>`) and must never leak host-language runtime identity. It must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_route_matching.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_route_matching@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout of the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the '-.' prefix convention used in route_add_parameter
- applying the same '.output' typo logic as route_add_parameter
