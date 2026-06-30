## Product Requirement Document

# Feature Flags for Web Applications — Conditional Behavior Toggling

## Project Goal

Build a feature-flag system that allows web-application developers to switch behavior on or off at runtime — per request, per user, per URL, or globally — without redeploying code or scattering hand-written `if` checks throughout the codebase. A flag's state is decided by one or more named *conditions*, each evaluated against runtime context, and the system exposes that decision uniformly to view guards, URL routing, templates, and plain code.

---

## Background & Problem

Without this system, developers hard-code branches like "if the current user is X" or "if today is after date Y" directly into views, templates, and routing tables. Rolling a behavior out to a subset of traffic, scheduling it for a future date, or turning it off in an incident all require code edits and a deploy. The toggling logic is duplicated across layers (server code, templates, URL maps) and drifts out of sync; there is no single place to ask "is this behavior on right now, given this request?".

With this system, each behavior is named by a flag whose on/off decision is computed from declarative conditions. Flags are defined in static configuration and/or stored records, merged from multiple providers, and queried through one consistent interface. The same flag can gate a view (returning not-found or a fallback when off), select between URL targets, branch a template, or be checked inline — all reading the same evaluated state.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This is a multi-responsibility system (condition evaluation, flag-state resolution, multi-source aggregation, request/response guarding, URL routing, template integration, configuration validation). It MUST NOT be a single "god file"; use a clear multi-directory tree separating the core domain from the I/O adapter. Do not over-engineer, but do not collapse distinct responsibilities together.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box contract for the execution adapter**, NOT the internal data model. The core logic must be decoupled from stdin/stdout and JSON parsing. The adapter is solely responsible for translating JSON commands into idiomatic calls to the core and rendering results to stdout.

3. **Adherence to SOLID Design Principles:**
   - **SRP:** Separate condition evaluation, flag-state resolution, source aggregation, guarding, routing, and output formatting.
   - **OCP:** New condition types and new flag-source providers must be addable without modifying the resolution engine.
   - **LSP:** All flag-source providers must be interchangeable behind one provider interface.
   - **ISP:** Keep the condition interface and the provider interface small and cohesive.
   - **DIP:** The resolution engine depends on the provider/condition abstractions, not on concrete configuration or storage details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface (checking a flag, guarding a view, declaring a flagged route, registering a condition) must be elegant and idiomatic to the target language.
   - **Resilience:** Edge cases must be handled gracefully — unknown flags, missing required context, failing providers, invalid route targets, and misconfiguration must be modeled as well-defined outcomes, not generic crashes.

---

## Core Features

### Feature 1: Condition Evaluation

**As a developer**, I want named conditions that each decide on/off from runtime context, so I can compose flag behavior from small reusable predicates.

**Expected Behavior / Usage:**

A condition takes a configured value plus optional runtime context (a request) and returns a definite boolean. Several built-in condition types exist. Conditions that need request context but are evaluated without one must fail with a *normalized* error contract — `error=missing_required_argument`, the missing `argument`, and the offending `condition` — never a raw host-language exception. Each condition type below is an independent leaf.

*1.1 Boolean condition — constant on/off from a literal or its string spelling.*

Evaluates a literal boolean, or the case-insensitive string `true`/`false`, to a definite result. The literal `true` and any casing of the string `"true"` evaluate on; every other value (including `"False"`, `"false"`, literal `false`) evaluates off.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_boolean_condition.json`

```json
{
    "description": "Boolean condition: evaluate a literal boolean or its case-insensitive string spelling to a definite on/off result. The string 'true' (any casing) and the literal true evaluate on; everything else evaluates off.",
    "cases": [
        {"input": {"op": "check_condition", "condition": "boolean", "value": "true"}, "expected_output": "result=true\n"},
        {"input": {"op": "check_condition", "condition": "boolean", "value": "False"}, "expected_output": "result=false\n"}
    ]
}
```

*1.2 User condition — match the request's user against an expected username.*

Passes when the current request's user has the expected username, off otherwise. Requires request context; without a request it returns the normalized missing-required-argument error.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_user_condition.json`

```json
{
    "description": "User condition: passes when the current request's user has the expected username. Requires request context; when the request is absent the evaluation reports a normalized missing-required-argument error naming the missing argument and the condition.",
    "cases": [
        {"input": {"op": "check_condition", "condition": "user", "value": "testuser", "request": {"username": "testuser"}}, "expected_output": "result=true\n"},
        {"input": {"op": "check_condition", "condition": "user", "value": "testuser"}, "expected_output": "error=missing_required_argument\nargument=request\ncondition=user\n"}
    ]
}
```

*1.3 Anonymous condition — match user anonymity against an expected boolean.*

Passes when whether the request's user is anonymous equals the expected boolean. Requires request context; without a request it returns the normalized missing-required-argument error.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_anonymous_condition.json`

```json
{
    "description": "Anonymous condition: compares whether the request's user is anonymous against an expected boolean. Passes when the anonymity of the user matches the expected boolean. Requires request context; without a request it reports a normalized missing-required-argument error.",
    "cases": [
        {"input": {"op": "check_condition", "condition": "anonymous", "value": true, "request": {"anonymous": true}}, "expected_output": "result=true\n"},
        {"input": {"op": "check_condition", "condition": "anonymous", "value": true, "request": {"anonymous": false}}, "expected_output": "result=false\n"}
    ]
}
```

*1.4 Parameter condition — presence of a query-string parameter set to True.*

Passes when a named query-string parameter on the request equals the exact string `True`; any other value or an absent parameter evaluates off. Requires request context; without a request it returns the normalized missing-required-argument error.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_parameter_condition.json`

```json
{
    "description": "Parameter condition: passes when a named query-string parameter on the request equals the exact string 'True'. Any other value, or an absent parameter, evaluates off. Requires request context; without a request it reports a normalized missing-required-argument error.",
    "cases": [
        {"input": {"op": "check_condition", "condition": "parameter", "value": "query_flag", "request": {"get": {"query_flag": "True"}}}, "expected_output": "result=true\n"},
        {"input": {"op": "check_condition", "condition": "parameter", "value": "query_flag", "request": {"get": {"not_query_flag": "True"}}}, "expected_output": "result=false\n"}
    ]
}
```

*1.5 Path-matches condition — request path matches a regular expression.*

Passes when the request path contains a match for the given regular expression anywhere within it (regex search, not anchored to the start). Requires request context; without a request it returns the normalized missing-required-argument error.

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_path_condition.json`

```json
{
    "description": "Path-matches condition: passes when the request path contains a match for the given regular expression anywhere within it (substring/regex search, not anchored). Requires request context; without a request it reports a normalized missing-required-argument error.",
    "cases": [
        {"input": {"op": "check_condition", "condition": "path matches", "value": "/my/path", "request": {"path": "/my/path/to/somewhere"}}, "expected_output": "result=true\n"},
        {"input": {"op": "check_condition", "condition": "path matches", "value": "/my/path", "request": {"path": "/your/path"}}, "expected_output": "result=false\n"}
    ]
}
```

*1.6 After-date condition — current moment is at or after a target datetime.*

Passes when the current moment is at or after the given ISO 8601 datetime. A datetime far in the past evaluates on; far in the future evaluates off. A string that is not a valid datetime must evaluate off rather than raising.

**Test Cases:** `rcb_tests/public_test_cases/feature1_6_date_condition.json`

```json
{
    "description": "After-date condition: passes when the current moment is at or after the given ISO 8601 datetime. A datetime far in the past evaluates on; a datetime far in the future evaluates off; a string that is not a valid datetime evaluates off rather than failing.",
    "cases": [
        {"input": {"op": "check_condition", "condition": "after date", "value": "2000-01-01T00:00:00"}, "expected_output": "result=true\n"},
        {"input": {"op": "check_condition", "condition": "after date", "value": "2999-01-01T00:00:00"}, "expected_output": "result=false\n"},
        {"input": {"op": "check_condition", "condition": "after date", "value": "I am not a valid date"}, "expected_output": "result=false\n"}
    ]
}
```

---

### Feature 2: Condition Registry

**As a developer**, I want to register custom conditions by name and look them up, so the set of available conditions is extensible without changing the engine.

**Expected Behavior / Usage:**

*2.1 Registration — add a new named condition, reject duplicates.*

A new condition can be registered under a name and then becomes discoverable. Registering a name that is already taken is rejected with a normalized `error=duplicate_condition` naming the condition.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_register_condition.json`

```json
{
    "description": "Condition registry registration: a new condition can be registered under a name and is then discoverable in the registry. Registering a name that is already taken is rejected with a normalized duplicate-condition error naming the condition.",
    "cases": [
        {"input": {"op": "register_condition", "name": "decorated"}, "expected_output": "registered=decorated\nfound=true\n"},
        {"input": {"op": "register_condition", "name": "boolean"}, "expected_output": "error=duplicate_condition\ncondition=boolean\n"}
    ]
}
```

*2.2 Lookup — report whether a condition name is registered.*

Looking up a registered condition name reports it found; an unregistered name reports not found.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_lookup_condition.json`

```json
{
    "description": "Condition registry lookup: looking up a built-in condition name reports it as found, while looking up a name that was never registered reports it as not found.",
    "cases": [
        {"input": {"op": "lookup_condition", "name": "boolean"}, "expected_output": "condition=boolean\nfound=true\n"},
        {"input": {"op": "lookup_condition", "name": "notgettable"}, "expected_output": "condition=notgettable\nfound=false\n"}
    ]
}
```

---

### Feature 3: Flag State Resolution

**As a developer**, I want to ask whether a flag is on, off, or undefined for given context, so all layers read one consistent decision.

**Expected Behavior / Usage:**

A flag's state is the disjunction of its conditions: it is on when **any** condition passes, off when all conditions are present but none pass, and a distinct undefined/`none` value when the flag is not configured at all (so callers can tell "explicitly off" from "unknown"). Context such as a request may be supplied and is forwarded to the conditions.

*3.1 State query — on / off / undefined.*

Returns on for a satisfied flag, off for an unsatisfied one, and `none` for an unconfigured flag (even when a request is supplied).

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_flag_state.json`

```json
{
    "description": "Flag state resolution: resolving a flag returns its combined condition result. A flag whose conditions are all satisfied resolves on; a flag whose conditions are unsatisfied resolves off; a flag that is not configured resolves to a distinct none/undefined value (not the same as off).",
    "cases": [
        {"input": {"op": "resolve_flag", "flag": "FLAG_ENABLED", "mode": "state"}, "expected_output": "flag=FLAG_ENABLED\nstate=true\n"},
        {"input": {"op": "resolve_flag", "flag": "FLAG_DISABLED", "mode": "state"}, "expected_output": "flag=FLAG_DISABLED\nstate=false\n"},
        {"input": {"op": "resolve_flag", "flag": "FLAG_DOES_NOT_EXIST", "mode": "state"}, "expected_output": "flag=FLAG_DOES_NOT_EXIST\n[state=none]\n"}
    ]
}
```

*3.2 Enabled helper — boolean "is this on".*

A convenience query reporting on/off (an undefined flag reads off here).

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_flag_enabled.json`

```json
{
    "description": "Enabled helper: a convenience query that reports whether a flag is currently on. An enabled flag reports on; a disabled flag reports off.",
    "cases": [
        {"input": {"op": "resolve_flag", "flag": "FLAG_ENABLED", "mode": "enabled"}, "expected_output": "flag=FLAG_ENABLED\nenabled=true\n"},
        {"input": {"op": "resolve_flag", "flag": "FLAG_DISABLED", "mode": "enabled"}, "expected_output": "flag=FLAG_DISABLED\nenabled=false\n"}
    ]
}
```

*3.3 Disabled helper — boolean negation.*

A convenience query reporting the negation of the state (an off or undefined flag reads on here).

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_flag_disabled.json`

```json
{
    "description": "Disabled helper: a convenience query that reports the negation of a flag's state. A disabled flag reports on; an enabled flag reports off.",
    "cases": [
        {"input": {"op": "resolve_flag", "flag": "FLAG_DISABLED", "mode": "disabled"}, "expected_output": "flag=FLAG_DISABLED\ndisabled=true\n"},
        {"input": {"op": "resolve_flag", "flag": "FLAG_ENABLED", "mode": "disabled"}, "expected_output": "flag=FLAG_ENABLED\ndisabled=false\n"}
    ]
}
```

---

### Feature 4: Multi-Source Flag Aggregation

**As a developer**, I want flags drawn from several providers and merged, so static configuration and stored records (and custom providers) contribute to one flag collection.

**Expected Behavior / Usage:**

Each provider exposes a flag collection. The aggregator merges providers in order into a single set of flags, each flag carrying its conditions (name + value). The listing output reports the total flag count and, per flag, its condition count and each condition's name and value. Flags are listed in a stable order.

*4.1 Static-configuration provider — flags from a configuration mapping.*

Reads flag definitions from the static configuration mapping; each flag exposes its conditions.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_settings_source.json`

```json
{
    "description": "Settings-backed flag provider: reads flag definitions from the static configuration mapping and exposes each flag with its conditions. The output lists the total flag count and, per flag, each condition's name and value.",
    "cases": [
        {"input": {"op": "list_flags", "flags": {"MY_FLAG": {"boolean": true}}, "sources": ["flags.sources.SettingsFlagsSource"]}, "expected_output": "flags=1\nflag=MY_FLAG conditions=1\ncondition flag=MY_FLAG name=boolean value=True\n"}
    ]
}
```

*4.2 Stored-record provider — flags from persisted records.*

Reads persisted flag records, exposing each as a flag with one condition carrying the stored condition name and value.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_database_source.json`

```json
{
    "description": "Database-backed flag provider: reads persisted flag records and exposes each as a flag with one condition carrying the stored condition name and value. The output lists the total flag count and the per-flag condition detail.",
    "cases": [
        {"input": {"op": "list_flags", "sources": ["flags.sources.DatabaseFlagsSource"], "db": [{"name": "MY_FLAG", "condition": "boolean", "value": "False"}]}, "expected_output": "flags=1\nflag=MY_FLAG conditions=1\ncondition flag=MY_FLAG name=boolean value=False\n"}
    ]
}
```

*4.3 Provider merge — combine multiple providers.*

Flags from several providers combine into one collection: a configured flag with no conditions coexists with provider-supplied flags, and a flag only an extra provider defines is included.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_merge_sources.json`

```json
{
    "description": "Multi-provider merge: flags from several providers are combined into one collection. A flag defined in the static configuration with no conditions appears alongside flags supplied by an additional provider, and a flag only the extra provider defines is included. The output lists the merged flag count with each flag's condition count and detail.",
    "cases": [
        {"input": {"op": "list_flags", "flags": {"SOURCED_FLAG": {}, "OTHER_FLAG": {}}, "sources": ["flags.sources.SettingsFlagsSource", "dispatcher.source_fixture.CustomFlagsSource"]}, "expected_output": "flags=3\nflag=NOT_IN_SETTINGS_FLAG conditions=1\ncondition flag=NOT_IN_SETTINGS_FLAG name=boolean value=False\nflag=OTHER_FLAG conditions=0\nflag=SOURCED_FLAG conditions=1\ncondition flag=SOURCED_FLAG name=boolean value=True\n"}
    ]
}
```

*4.4 Provider error handling — fail, ignore, or not found.*

A provider that fails surfaces a normalized `error=source_failed` by default; when errors are explicitly ignored the failing provider is skipped and the remaining collection (possibly empty) is returned; a provider path that cannot be located surfaces a normalized `[normalized source-not-found error]`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_source_errors.json`

```json
{
    "description": "Provider error handling: when a provider fails while producing flags, the default behavior surfaces a normalized source-failure error. When errors are explicitly ignored, the failing provider is skipped and an empty collection is returned. A provider path that cannot be located surfaces a normalized source-not-found error.",
    "cases": [
        {"input": {"op": "list_flags", "sources": ["dispatcher.source_fixture.ExceptionalFlagsSource"]}, "expected_output": "error=source_failed\n"},
        {"input": {"op": "list_flags", "sources": ["dispatcher.source_fixture.ExceptionalFlagsSource"], "ignore_errors": true}, "expected_output": "flags=0\n"},
        {"input": {"op": "list_flags", "sources": ["non.existent.module"]}, "expected_output": "[normalized source-not-found error]\n"}
    ]
}
```

---

### Feature 5: View Access Guard

**As a developer**, I want to gate a request handler on a flag, so a behavior is served only when the flag matches a required state and otherwise yields not-found or a fallback.

**Expected Behavior / Usage:**

A handler is wrapped with a flag and a required state. When the flag matches the required state, the primary handler runs (status 200). When it does not match, the request yields not-found (status 404) unless a fallback handler is configured, in which case the fallback runs (status 200). The required state may be off, which inverts the polarity. Outputs carry the framework-observable HTTP status and the response body so a stub that bypasses the guard cannot pass.

*5.1 Function handler guard.*

A plain handler function is guarded. The `body` line shows which handler ran (`ok` = primary, `fallback` = fallback).

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_function_view_guard.json`

```json
{
    "description": "Function view access guard: a view is wrapped so it is served only when a flag matches a required state. With required-state on: an enabled flag serves the view (status 200, body 'ok'); a disabled or missing flag is blocked (status 404) unless a fallback view is supplied, in which case the fallback is served (status 200, body 'fallback'). With required-state off, the polarity inverts: a disabled or missing flag serves the view while an enabled flag is blocked or routed to the fallback.",
    "cases": [
        {"input": {"op": "guarded_view", "flag": "FLAG_ENABLED", "state": true}, "expected_output": "status=200\nbody=ok\n"},
        {"input": {"op": "guarded_view", "flag": "FLAG_DISABLED", "state": true}, "expected_output": "status=404\n"},
        {"input": {"op": "guarded_view", "flag": "FLAG_DISABLED", "state": true, "fallback": true}, "expected_output": "status=200\nbody=fallback\n"},
        {"input": {"op": "guarded_view", "flag": "FLAG_DISABLED", "state": false}, "expected_output": "status=200\nbody=ok\n"}
    ]
}
```

*5.2 Class handler guard.*

A class-based handler is gated identically. Configuring the guard without naming a flag at all yields a normalized `error=misconfigured` with `reason=flag_name_required`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_class_view_guard.json`

```json
{
    "description": "Class-based view access guard: a class view is gated on a flag the same way. When the gating flag is enabled the view responds (status 200, body 'ok'); when disabled or missing it is blocked (status 404) unless a fallback view is configured, in which case the fallback responds. If the view is configured without naming a flag at all, it reports a normalized misconfiguration error.",
    "cases": [
        {"input": {"op": "guarded_view", "flag": "FLAGGED_VIEW_MIXIN", "kind": "class", "state": true, "flags": {"FLAGGED_VIEW_MIXIN": {"boolean": true}}}, "expected_output": "status=200\nbody=ok\n"},
        {"input": {"op": "guarded_view", "flag": "FLAGGED_VIEW_MIXIN", "kind": "class", "state": true}, "expected_output": "status=404\n"},
        {"input": {"op": "guarded_view", "flag": "FLAGGED_VIEW_MIXIN", "kind": "class", "omit_flag_name": true}, "expected_output": "error=misconfigured\nreason=flag_name_required\n"}
    ]
}
```

---

### Feature 6: URL Routing Guard

**As a developer**, I want a flag to choose which target serves a URL, so I can route traffic to a new behavior, a fallback, or not-found based on flag state — including for whole groups of routes.

**Expected Behavior / Usage:**

A route is declared with a flag and a required state, optionally with a fallback target. Resolving the path and invoking it serves the primary target (status 200, body `view`) when the flag matches the required state; otherwise it serves the fallback target (status 200, body `fallback`) when one exists, or yields not-found (status 404). Output carries the resolved path, the HTTP status, and the served body — framework-observable signals that distinguish real routing from a stub.

*6.1 Single guarded route.*

One route bound to a flag and required state, with optional fallback; required state may be off.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_single_route.json`

```json
{
    "description": "Single flag-guarded route: a route is bound to a flag and a required state. Resolving and invoking the route returns the primary view (status 200, body 'view') when the flag matches the required state; otherwise it returns not-found (status 404) when no fallback is registered, or the fallback view (status 200, body 'fallback') when one is. Required-state may be off, inverting the polarity.",
    "cases": [
        {"input": {"op": "route", "path": "/url-true-no-fallback", "flags": {"FLAGGED_URL": {"boolean": true}}}, "expected_output": "path=/url-true-no-fallback\nstatus=200\nbody=view\n"},
        {"input": {"op": "route", "path": "/url-true-no-fallback", "flags": {"FLAGGED_URL": {"boolean": false}}}, "expected_output": "path=/url-true-no-fallback\nstatus=404\n"},
        {"input": {"op": "route", "path": "/url-true-fallback", "flags": {"FLAGGED_URL": {"boolean": false}}}, "expected_output": "path=/url-true-fallback\nstatus=200\nbody=fallback\n"},
        {"input": {"op": "route", "path": "/url-false-no-fallback", "flags": {"FLAGGED_URL": {"boolean": false}}}, "expected_output": "path=/url-false-no-fallback\nstatus=200\nbody=view\n"}
    ]
}
```

*6.2 Guarded route groups.*

A whole group of routes mounted under a prefix is guarded by one flag. When the flag does not match and a mirroring fallback group is supplied, member paths and fallback-only members serve the fallback, while paths in neither yield not-found.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_included_routes.json`

```json
{
    "description": "Flag-guarded included route groups: an entire group of routes can be mounted under a prefix and guarded by a single flag. When the flag matches, requests to a member route serve the primary view; when it does not match, they return not-found. A group mounted with required-state off serves its members when the flag is off. When the guard has a fallback group whose members mirror the primary routes, a non-matching flag serves the corresponding fallback for matching member paths and for members that exist only in the fallback group, while paths absent from both yield not-found.",
    "cases": [
        {"input": {"op": "route", "path": "/include/included-url", "flags": {"FLAGGED_URL": {"boolean": true}}}, "expected_output": "path=/include/included-url\nstatus=200\nbody=view\n"},
        {"input": {"op": "route", "path": "/include/included-url", "flags": {"FLAGGED_URL": {"boolean": false}}}, "expected_output": "path=/include/included-url\nstatus=404\n"},
        {"input": {"op": "route", "path": "/include-fallback-include/other-included-url", "flags": {"FLAGGED_URL": {"boolean": false}}}, "expected_output": "path=/include-fallback-include/other-included-url\nstatus=200\nbody=fallback\n"}
    ]
}
```

*6.3 Bulk route declaration via shared context.*

Multiple routes declared together inherit one flag, required state, and optional fallback, each behaving like a single guarded route.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_bulk_routes.json`

```json
{
    "description": "Bulk route guarding via a shared context: multiple routes declared together inherit one flag, required-state, and optional fallback. Members behave like single guarded routes: a route declared with required-state on serves the primary view when the flag is on and is not-found when off; a route declared with required-state off serves the primary view when the flag is off; a route declared with a shared fallback serves the fallback when the flag does not match the required state.",
    "cases": [
        {"input": {"op": "route", "path": "/patterns-true-no-fallback", "flags": {"FLAGGED_URL": {"boolean": true}}}, "expected_output": "path=/patterns-true-no-fallback\nstatus=200\nbody=view\n"},
        {"input": {"op": "route", "path": "/patterns-false-no-fallback", "flags": {"FLAGGED_URL": {"boolean": false}}}, "expected_output": "path=/patterns-false-no-fallback\nstatus=200\nbody=view\n"},
        {"input": {"op": "route", "path": "/patterns-true-fallback", "flags": {"FLAGGED_URL": {"boolean": false}}}, "expected_output": "path=/patterns-true-fallback\nstatus=200\nbody=fallback\n"}
    ]
}
```

*6.4 Invalid route target rejection.*

Building a guarded route whose target is neither a callable nor a route group is rejected with a normalized `error=invalid_view`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_4_invalid_view.json`

```json
{
    "description": "Invalid route target rejection: attempting to build a flag-guarded route whose target view is neither a callable nor a route group is rejected with a normalized invalid-view error.",
    "cases": [
        {"input": {"op": "route", "invalid_view": true}, "expected_output": "error=invalid_view\n"}
    ]
}
```

---

### Feature 7: Request-Scoped Flag Caching

**As a developer**, I want flags resolved once per request and reused, so repeated checks within a request are consistent and cheap even if configuration changes mid-request.

**Expected Behavior / Usage:**

A request-processing step resolves the flag collection once and attaches it to the request. A request that has not passed through this step carries no cached attribute; after it runs, the attribute is present and lists the configured flag names (in stable order). A flag check against a request with the cached snapshot keeps using that snapshot even if the live configuration is emptied afterward; a request without the snapshot reflects the now-empty configuration instead.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_request_cache.json`

```json
{
    "description": "Request-scoped flag caching: middleware attaches the resolved flag collection to the request so later checks reuse it. A request that has not passed through the middleware carries no cached attribute; after the middleware runs, the attribute is present and lists the configured flag names. Once cached, a flag check against that request keeps using the cached snapshot even if the live configuration is emptied afterward; a request without the cached snapshot reflects the now-empty configuration instead.",
    "cases": [
        {"input": {"op": "request_cache", "scenario": "no_middleware_attr", "flag_sources": ["flags.sources.SettingsFlagsSource"]}, "expected_output": "cached=false\n"},
        {"input": {"op": "request_cache", "scenario": "with_middleware", "flag_sources": ["flags.sources.SettingsFlagsSource"]}, "expected_output": "cached=true\nflags=DB_FLAG,FLAG_DISABLED,FLAG_ENABLED,FLAG_ENABLED_WITH_KWARG\n"},
        {"input": {"op": "request_cache", "scenario": "cached_after_change"}, "expected_output": "state=true\n"},
        {"input": {"op": "request_cache", "scenario": "no_cache_after_change"}, "expected_output": "state=false\n"}
    ]
}
```

---

### Feature 8: Template Integration

**As a developer**, I want to branch templates on flag state, so presentation can toggle without server-side branching.

**Expected Behavior / Usage:**

Templates expose an enabled check and a disabled check for a flag; the disabled check is the inverse of the enabled one, and a missing flag reads as disabled. An extra keyword argument passed at the call site is forwarded to the flag's condition so value-matching conditions can pass.

*8.1 Primary template engine — branch on flag state.*

An enabled tag and a disabled tag assign a boolean into a template variable; rendering shows the branch taken (`on`/`off`).

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_template_tags.json`

```json
{
    "description": "Server-side template flag tags: a template can branch on flag state using an enabled tag and a disabled tag, each assigning a boolean into a template variable. The enabled tag yields a truthy value for an on flag and falsy for an off or missing flag; the disabled tag is its inverse. An extra keyword argument supplied at the tag call is forwarded to the flag's condition so value-matching conditions can pass. Rendering 'on' or 'off' shows the branch taken.",
    "cases": [
        {"input": {"op": "render_django", "tag": "flag_enabled", "flag": "FLAG_ENABLED"}, "expected_output": "rendered=on\n"},
        {"input": {"op": "render_django", "tag": "flag_enabled", "flag": "FLAG_DISABLED"}, "expected_output": "rendered=off\n"},
        {"input": {"op": "render_django", "tag": "flag_enabled", "flag": "FLAG_ENABLED_WITH_KWARG", "passed_value": 4}, "expected_output": "rendered=on\n"},
        {"input": {"op": "render_django", "tag": "flag_disabled", "flag": "FLAG_ENABLED"}, "expected_output": "rendered=off\n"}
    ]
}
```

*8.2 Alternative template engine — flag check globals.*

A second template engine exposes enabled and disabled flag functions returning a rendered boolean (`True`/`False`), with the same keyword-forwarding behavior.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_jinja_tags.json`

```json
{
    "description": "Alternative template-engine flag globals: a second template engine exposes enabled and disabled flag functions that return a rendered boolean. The enabled function renders 'True' for an on flag and 'False' for an off flag; the disabled function is its inverse. A keyword argument passed in the call is forwarded to the flag's condition so value-matching conditions can pass.",
    "cases": [
        {"input": {"op": "render_jinja", "tag": "flag_enabled", "flag": "FLAG_ENABLED"}, "expected_output": "[renders 'True' if flag is on, 'False' if flag is off/undefined]\n"},
        {"input": {"op": "render_jinja", "tag": "flag_disabled", "flag": "FLAG_ENABLED"}, "expected_output": "[renders 'True' if flag is on, 'False' if flag is off/undefined]\n"},
        {"input": {"op": "render_jinja", "tag": "flag_enabled", "flag": "FLAG_ENABLED_WITH_KWARG", "passed_value": 4}, "expected_output": "[renders 'True' if flag is on, 'False' if flag is off/undefined]\n"}
    ]
}
```

---

### Feature 9: Flag Administration Form

**As a developer / administrator**, I want a form to create stored flag records and to choose from the currently available conditions, so flags can be managed at runtime.

**Expected Behavior / Usage:**

*9.1 Form validation and persistence.*

The form accepts a flag name, a condition name, and a value. Valid submissions persist a record and echo the saved fields; blank submissions are rejected, reporting which required fields are invalid (in stable order).

**Test Cases:** `rcb_tests/public_test_cases/feature9_1_form_validation.json`

```json
{
    "description": "Flag-state form validation and persistence: a form accepts a flag name, a condition name, and a value. Valid submissions persist a flag record and echo the saved name, condition, and value. Blank submissions are rejected, reporting which required fields are invalid.",
    "cases": [
        {"input": {"op": "submit_form", "data": {"name": "FLAG_ENABLED", "condition": "boolean", "value": "True"}}, "expected_output": "valid=true\nname=FLAG_ENABLED\ncondition=boolean\nvalue=True\n"},
        {"input": {"op": "submit_form", "data": {}}, "expected_output": "valid=false\ninvalid_fields=condition,name,value\n"}
    ]
}
```

*9.2 Late-bound condition choices.*

The form's condition choices are computed when the form is built, not when it is defined, so a condition registered after definition is still offered.

**Test Cases:** `rcb_tests/public_test_cases/feature9_2_form_choices.json`

```json
{
    "description": "Late-bound condition choices: the form's condition choices are computed when the form is built, not when it is defined, so a condition registered after import is still offered. Querying a freshly registered condition reports it as present among the choices.",
    "cases": [
        {"input": {"op": "form_choices", "condition": "fake_condition", "register": true}, "expected_output": "condition=fake_condition\npresent=true\n"}
    ]
}
```

---

### Feature 10: Configuration Validation

**As a developer**, I want configured flags checked for conditions that name a non-existent condition type, so misconfiguration is caught early with a stable diagnostic.

**Expected Behavior / Usage:**

Flags are scanned: a configuration referencing only known conditions produces no warnings; a flag referencing an unregistered condition produces exactly one warning carrying a stable diagnostic id (`flags.E001`).

**Test Cases:** `rcb_tests/public_test_cases/feature10_1_config_check.json`

```json
{
    "description": "Configuration validation check: flags are scanned for conditions that name a non-existent condition type. A configuration whose flags reference only known conditions produces no warnings; a flag that references an unregistered condition produces exactly one warning carrying a stable diagnostic id.",
    "cases": [
        {"input": {"op": "validate_config", "flags": {"FLAG_TO_CHECK": {"boolean": true}}}, "expected_output": "warnings=0\n"},
        {"input": {"op": "validate_config", "flags": {"FLAG_TO_CHECK": {"nonexistent": "value"}}}, "expected_output": "warnings=1\nwarning id=flags.E001\n"}
    ]
}
```

---

### Feature 11: Flag Record Description

**As a developer**, I want a stored flag record to render to a readable sentence, so records are legible in listings and admin screens.

**Expected Behavior / Usage:**

A persisted record renders to a sentence naming the flag, the condition that enables it, and the value it is enabled at.

**Test Cases:** `rcb_tests/public_test_cases/feature11_1_record_description.json`

```json
{
    "description": "Flag record human-readable description: a persisted flag record renders to a sentence describing the flag, the condition that enables it, and the value it is enabled at.",
    "cases": [
        {"input": {"op": "describe_record", "name": "MY_FLAG", "condition": "boolean", "value": "True"}, "expected_output": "description=MY_FLAG is enabled when boolean is True\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-directory codebase implementing the features above — condition evaluation and registry, flag-state resolution, multi-source aggregation, view/route guarding, request-scoped caching, template integration, the administration form, configuration validation, and record description — with the core domain decoupled from I/O.

2. **The Execution/Test Adapter:** A runnable entry point that reads a single JSON command from stdin, invokes the appropriate core logic, and prints the language-neutral stdout contract above. The adapter is the sole owner of JSON parsing and stdout formatting, and it translates any host-language or framework exception into the normalized `error=<category>` contract; the core never prints. Inputs carry an `op` selecting the behavior plus its parameters (e.g. `flags`, `flag_sources`, `request`); outputs are the exact byte strings shown in the cases.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_1_boolean_condition.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_boolean_condition@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout of the program under test (no PASS/FAIL or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follows the undefined-handling logic used in the state resolver helper
- check the fallback group logic in the bulk routing container
