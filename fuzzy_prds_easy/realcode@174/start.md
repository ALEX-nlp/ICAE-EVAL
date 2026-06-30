## Product Requirement Document

# Feature Flag Engine — Scoped, Resolver-Backed Feature Toggles with Caching and Request Gating

## Project Goal

Build a lightweight feature-flag engine that lets developers define named feature flags, resolve their value on demand (optionally per-scope), override them at runtime, and gate behavior on them — so an application can roll features out to specific entities and toggle them without redeploying or scattering ad-hoc conditionals through the codebase.

---

## Background & Problem

Applications constantly need to turn behavior on or off for some audience: everyone, a single account, a class of users, or nobody yet. Without a dedicated engine, teams hard-code booleans, sprinkle environment checks everywhere, and have no consistent story for "is this on for *this* entity?", for caching the answer, or for cleanly removing a flag once it ships.

This engine centralizes that. A flag is **defined** with a *resolver* that computes its initial value (a constant, a value derived from the scope it is checked against, or a probabilistic draw). The value for a given (flag, scope) pair is computed at most once and cached. Callers can ask whether a flag is **active** (anything other than boolean `false` is active), read its concrete **value**, override it by **activating/deactivating** it, branch on it, gate an HTTP request on it, and **forget/purge** stored values to force recomputation.

A central idea is the **scope**: the entity a flag is evaluated for. A scope may be absent (the global/unscoped value), an empty string, a string identifier, a number, or a domain object. Object scopes are reduced to a stable string key; an object may also advertise its own identifier so distinct instances that represent the same thing collapse to one scope.

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

Each feature is exercised through the execution adapter, which reads one JSON request `{ "operations": [ ... ] }` from stdin and prints one line per *query* operation to stdout (mutating operations print nothing). The operation vocabulary, scope encoding, resolver specifications, and exact output line formats are defined in the **Deliverables** section; read it alongside these features.

### Feature 1: Defining Flags and the Active/Inactive Contract

**As a developer**, I want to register a flag with a resolver and ask whether it is active, so I can branch on a feature without caring how its value was produced.

**Expected Behavior / Usage:**

A flag is defined by name together with a resolver that yields its initial value. Querying `active` for an undefined flag returns inactive. For a defined flag, the flag is **active** unless its resolved value is exactly boolean `false`; every other value — including `0`, `""`, `null`, and structured values — is **active**. The `inactive` query is the exact logical negation of `active`. Reading the concrete value is also supported (see Feature 4).

**Test Cases:** `rcb_tests/public_test_cases/feature1_defining_and_truthiness.json`

```json
{
    "description": "Define feature flags by attaching a resolver that produces an initial value, then query whether a feature is active. A feature with no registered resolver is treated as inactive. A registered resolver makes the feature active unless the resolved value is exactly boolean false: every other value (including zero, an empty string, null, and structured values) counts as active. The inactive check is the logical inverse of the active check.",
    "cases": [
        {
            "input": {"operations": [
                {"op": "define", "feature": "on", "resolver": {"type": "const", "value": true}},
                {"op": "define", "feature": "off", "resolver": {"type": "const", "value": false}},
                {"op": "active", "feature": "on"},
                {"op": "active", "feature": "off"}
            ]},
            "expected_output": "active on = true\nactive off = false\n"
        }
    ]
}
```

---

### Feature 2: Runtime Overrides

**As a developer**, I want to force flags on or off at runtime, so I can change behavior without touching the resolver.

**Expected Behavior / Usage:**

*2.1 Activate / Deactivate — toggle one or many flags*

Activating a flag stores a truthy value so later checks report it active; deactivating stores `false` so later checks report it inactive. The action accepts either a single flag name or a list of names, applying to all of them. Toggling is idempotent and may be re-applied freely.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_activate_deactivate.json`

```json
{
    "description": "Programmatically turn feature flags on and off at runtime, overriding any resolver. Activating a feature stores a truthy value so subsequent checks report it active; deactivating stores false so checks report it inactive. The same action may be applied to several features at once by supplying a list of feature names. Toggling is idempotent and re-applies cleanly.",
    "cases": [
        {
            "input": {"operations": [
                {"op": "activate", "feature": "foo"},
                {"op": "active", "feature": "foo"},
                {"op": "deactivate", "feature": "foo"},
                {"op": "active", "feature": "foo"},
                {"op": "activate", "feature": "foo"},
                {"op": "active", "feature": "foo"}
            ]},
            "expected_output": "active foo = true\nactive foo = false\nactive foo = true\n"
        }
    ]
}
```

*2.2 Activate / Deactivate For Everyone — bulk apply across known scopes*

A flag's value can be forced for every scope that already has a stored value. After some scopes have been given values, deactivating-for-everyone forces the flag off for all of them and activating-for-everyone forces it on for all of them. The operation affects the scopes already present in storage.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_for_everyone.json`

```json
{
    "description": "Apply a single value to a feature across every scope that already has a stored value. After individual scopes have been given values, deactivating-for-everyone forces the feature off for all of them, and activating-for-everyone forces it on for all of them. This bulk operation affects the scopes already known to storage.",
    "cases": [
        {
            "input": {"operations": [
                {"op": "define", "feature": "foo", "resolver": {"type": "const", "value": false}},
                {"op": "activate", "feature": "foo", "scope": "tim"},
                {"op": "activate", "feature": "foo", "scope": "taylor"},
                {"op": "value", "feature": "foo", "scope": "tim"},
                {"op": "value", "feature": "foo", "scope": "taylor"},
                {"op": "deactivateForEveryone", "feature": "foo"},
                {"op": "value", "feature": "foo", "scope": "tim"},
                {"op": "value", "feature": "foo", "scope": "taylor"},
                {"op": "activateForEveryone", "feature": "foo"},
                {"op": "value", "feature": "foo", "scope": "tim"},
                {"op": "value", "feature": "foo", "scope": "taylor"}
            ]},
            "expected_output": "value foo = true\nvalue foo = true\nvalue foo = false\nvalue foo = false\nvalue foo = true\nvalue foo = true\n"
        }
    ]
}
```

---

### Feature 3: Scopes

**As a developer**, I want to evaluate and store flag values per entity, so a feature can be on for one audience and off for another.

**Expected Behavior / Usage:**

*3.1 Scope Isolation & Identity*

A flag may be checked against a specific scope, and a resolver may inspect that scope to decide the value. Values stored for one scope never leak to another. A scope object may declare its own stable string identifier; two scope objects that map to the same identifier are treated as the same scope. When no scope is supplied, the default (global) scope applies (see 3.4).

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_scope_isolation.json`

```json
{
    "description": "Evaluate a feature against a specific scope (the entity a flag is being checked for, such as an account, a string identifier like an email address, a number, or a domain object). A resolver may inspect the scope to decide the value. Values stored for one scope do not leak to another, so a feature can be active for one scope and inactive for another. A scope object may also declare its own stable string identifier, in which case two scopes that map to the same identifier are treated as the same scope.",
    "cases": [
        {
            "input": {"operations": [
                {"op": "define", "feature": "foo", "resolver": {"type": "scopeIdEquals", "id": 1}},
                {"op": "active", "feature": "foo"},
                {"op": "active", "feature": "foo", "scope": {"user": 1}},
                {"op": "active", "feature": "foo", "scope": {"user": 2}}
            ]},
            "expected_output": "active foo = false\nactive foo = true\nactive foo = false\n"
        }
    ]
}
```

*3.2 Null vs. Empty-String Scope*

The absent/null scope represents the global, unscoped value: a globally stored value is visible under an explicit null scope and vice versa. The empty string is a *distinct* scope: a value stored under the empty-string scope is invisible globally and under null, and a global value is invisible under the empty-string scope.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_null_and_empty_scope.json`

```json
{
    "description": "Distinguish the absence of a scope from an empty-string scope. The null scope represents the global, unscoped value, so a value set globally is visible when checking with an explicit null scope and vice versa. The empty string is a distinct scope from null: a value stored under the empty-string scope is not visible globally or under null, and a global value is not visible under the empty-string scope.",
    "cases": [
        {
            "input": {"operations": [
                {"op": "activate", "feature": "foo"},
                {"op": "active", "feature": "foo", "scope": ""},
                {"op": "active", "feature": "foo", "scope": null},
                {"op": "active", "feature": "foo"},
                {"op": "activate", "feature": "bar", "scope": ""},
                {"op": "active", "feature": "bar", "scope": ""},
                {"op": "active", "feature": "bar", "scope": null},
                {"op": "active", "feature": "bar"}
            ]},
            "expected_output": "active foo = false\nactive foo = true\nactive foo = true\nactive bar = true\nactive bar = false\nactive bar = false\n"
        }
    ]
}
```

*3.3 Multiple Scopes At Once*

Supplying a list of scopes applies an action to each. Activating for a list of scopes makes the flag active for every listed scope and leaves others untouched. A multi-scope aggregate check reports active only when the flag is active for *every* scope in the list.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_multiple_scopes.json`

```json
{
    "description": "Apply an action to several scopes at once by supplying a list of scopes. Activating a feature for a list of scopes makes it active for each listed scope and leaves other scopes unaffected. A multi-scope aggregate check reports active only when the feature is active for every scope in the list.",
    "cases": [
        {
            "input": {"operations": [
                {"op": "activate", "feature": "foo", "scope": [{"user": 1}, {"user": 2}]},
                {"op": "active", "feature": "foo"},
                {"op": "active", "feature": "foo", "scope": {"user": 1}},
                {"op": "active", "feature": "foo", "scope": {"user": 2}},
                {"op": "active", "feature": "foo", "scope": {"user": 3}}
            ]},
            "expected_output": "active foo = false\nactive foo = true\nactive foo = true\nactive foo = false\n"
        }
    ]
}
```

*3.4 Default Scope Resolution*

When no scope is given, the engine resolves one automatically. By default it uses the currently authenticated entity, so after authenticating, an unscoped check matches a check made explicitly for that same entity while a different scope is unaffected. The default-scope strategy can also be replaced, after which unscoped checks use the value the replacement produces.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_default_scope.json`

```json
{
    "description": "Resolve the scope automatically when no scope is supplied. By default the unscoped value uses the currently authenticated entity as the scope, so after authenticating, an unscoped check matches a check made explicitly for that same entity, while a different scope is unaffected. The default-scope strategy can also be replaced, after which unscoped checks use the value produced by the replacement strategy.",
    "cases": [
        {
            "input": {"operations": [
                {"op": "loginUser", "id": 2},
                {"op": "activate", "feature": "foo"},
                {"op": "active", "feature": "foo", "scope": "misc"},
                {"op": "active", "feature": "foo"},
                {"op": "active", "feature": "foo", "scope": {"user": 2}}
            ]},
            "expected_output": "active foo = false\nactive foo = true\nactive foo = true\n"
        }
    ]
}
```

*3.5 Null-Scope Handling for Scope-Dependent Resolvers*

A resolver that does not require a particular scope evaluates normally against a null scope and yields its value. A resolver that *requires* a concrete (non-null) scope cannot run against a null scope; in that case the flag resolves to inactive rather than failing, while still resolving normally when a concrete scope is provided.

**Test Cases:** `rcb_tests/public_test_cases/feature3_5_null_scope_handling.json`

```json
{
    "description": "Control how a feature behaves when checked with a null scope. A resolver that does not require a particular scope is evaluated normally for a null scope and produces its value. A resolver that requires a concrete (non-null) scope cannot run against a null scope; in that situation the feature resolves to inactive instead of failing, while still resolving normally when a concrete scope is provided.",
    "cases": [
        {
            "input": {"operations": [
                {"op": "define", "feature": "bar", "resolver": {"type": "requiresUserScope", "value": true}},
                {"op": "active", "feature": "bar", "scope": null},
                {"op": "active", "feature": "bar", "scope": {"user": 1}}
            ]},
            "expected_output": "active bar = false\nactive bar = true\n"
        }
    ]
}
```

---

### Feature 4: Reading Values

**As a developer**, I want to read a flag's concrete value (not just its on/off state), so flags can carry configuration payloads.

**Expected Behavior / Usage:**

A single `value` query returns one flag's value for a scope. A batch `values` query returns a map from each requested flag name to its value for a scope. The `all` query returns a map of every defined flag to its value, in definition order. A flag activated with an explicit value stores that value, which is returned verbatim.

**Test Cases:** `rcb_tests/public_test_cases/feature4_reading_values.json`

```json
{
    "description": "Read the concrete value of a feature rather than just its active/inactive state. A single query returns one feature's value for a scope; a batch query returns a map from each requested feature name to its value for a scope; and the all-query returns a map of every defined feature to its value. Activating a feature with an explicit value stores that value, which is then returned verbatim.",
    "cases": [
        {
            "input": {"operations": [
                {"op": "define", "feature": "a", "resolver": {"type": "const", "value": true}},
                {"op": "define", "feature": "b", "resolver": {"type": "const", "value": false}},
                {"op": "all"}
            ]},
            "expected_output": "all = {\"a\":true,\"b\":false}\n"
        }
    ]
}
```

---

### Feature 5: Resolution Caching and Loading

**As a developer**, I want resolved values cached so resolvers don't run repeatedly, and I want to pre-load values, so I can control when resolution work happens.

**Expected Behavior / Usage:**

Each (flag, scope) pair is resolved at most once and cached; subsequent reads do not re-run the resolver (observed here via a per-flag invocation counter). Explicitly *loading* a flag pre-resolves and caches it. *Load-missing* resolves only flags not already cached. *Flushing* the cache forces the next read to resolve again.

**Test Cases:** `rcb_tests/public_test_cases/feature5_caching_and_loading.json`

```json
{
    "description": "Resolve each feature's value at most once per scope and keep it cached, so a resolver's side effects (counted here as the number of times it runs) are not repeated on later reads of the same feature and scope. Explicitly loading a feature pre-resolves and caches it; load-missing only resolves features that are not already cached. Flushing the cache forces the next read to resolve the feature again.",
    "cases": [
        {
            "input": {"operations": [
                {"op": "define", "feature": "foo", "resolver": {"type": "counter", "value": true}},
                {"op": "calls", "feature": "foo"},
                {"op": "active", "feature": "foo"},
                {"op": "calls", "feature": "foo"},
                {"op": "active", "feature": "foo"},
                {"op": "calls", "feature": "foo"}
            ]},
            "expected_output": "calls foo = 0\nactive foo = true\ncalls foo = 1\nactive foo = true\ncalls foo = 1\n"
        }
    ]
}
```

---

### Feature 6: Multi-Flag Aggregate Checks

**As a developer**, I want to check several flags in one call, so I can express "all of these" and "any of these" conditions.

**Expected Behavior / Usage:**

`allAreActive` is true only when every listed flag is active. `someAreActive` is true when at least one listed flag is active. `allAreInactive` is true only when every listed flag is inactive. `someAreInactive` is true when at least one listed flag is inactive.

**Test Cases:** `rcb_tests/public_test_cases/feature6_multi_feature_checks.json`

```json
{
    "description": "Check several features in one call. The all-active check is true only when every listed feature is active. The some-active check is true when at least one listed feature is active. The all-inactive check is true only when every listed feature is inactive, and the some-inactive check is true when at least one listed feature is inactive.",
    "cases": [
        {
            "input": {"operations": [
                {"op": "activate", "feature": ["foo", "bar"]},
                {"op": "allAreActive", "features": ["foo"]},
                {"op": "allAreActive", "features": ["foo", "bar"]},
                {"op": "allAreActive", "features": ["foo", "bar", "baz"]},
                {"op": "someAreActive", "features": ["foo", "baz"]},
                {"op": "someAreActive", "features": ["baz", "qux"]}
            ]},
            "expected_output": "allAreActive = true\nallAreActive = true\nallAreActive = false\nsomeAreActive = true\nsomeAreActive = false\n"
        }
    ]
}
```

---

### Feature 7: Conditional Execution

**As a developer**, I want to run one of two branches depending on a flag, so I can express feature-gated logic concisely.

**Expected Behavior / Usage:**

The `when` construct runs its active branch (receiving the flag's value) if the flag is active, otherwise its inactive branch. The `unless` construct is the mirror: it runs its inactive branch when the flag is inactive, otherwise its active branch (receiving the value). Branch selection honors the scope used for the check. The output reports which branch was taken and, for the active branch, the flag's value.

**Test Cases:** `rcb_tests/public_test_cases/feature7_conditional_execution.json`

```json
{
    "description": "Branch on a feature's state and run one of two callbacks. The when-construct runs its first callback (receiving the feature's value) if the feature is active, otherwise its second callback. The unless-construct is the mirror image: it runs its inactive callback when the feature is inactive, otherwise its active callback. Branch selection honors the scope used for the check.",
    "cases": [
        {
            "input": {"operations": [
                {"op": "activate", "feature": "foo", "value": {"hello": "world"}},
                {"op": "when", "feature": "foo"}
            ]},
            "expected_output": "when foo = active {\"hello\":\"world\"}\n"
        }
    ]
}
```

---

### Feature 8: Forgetting and Purging

**As a developer**, I want to discard stored values so they are recomputed, so I can reset a flag for a scope or remove it entirely.

**Expected Behavior / Usage:**

Forgetting a flag for a scope removes only that scope's stored value; the next read falls back to the resolver. Purging removes stored values for the named flags across all scopes; purging with no names removes stored values for every flag. After either, reads fall back to the resolver again.

**Test Cases:** `rcb_tests/public_test_cases/feature8_forget_and_purge.json`

```json
{
    "description": "Discard stored feature values so they are recomputed from their resolver. Forgetting a feature for a scope removes only that scope's stored value, so the next read falls back to the resolver. Purging removes stored values for the named features across all scopes, and purging with no names removes stored values for every feature; after purging, reads fall back to the resolver again.",
    "cases": [
        {
            "input": {"operations": [
                {"op": "define", "feature": "foo", "resolver": {"type": "const", "value": false}},
                {"op": "activate", "feature": "foo", "scope": "tim"},
                {"op": "active", "feature": "foo", "scope": "tim"},
                {"op": "purge", "features": ["foo"]},
                {"op": "active", "feature": "foo", "scope": "tim"}
            ]},
            "expected_output": "active foo = true\nactive foo = false\n"
        }
    ]
}
```

---

### Feature 9: Probabilistic Resolution

**As a developer**, I want a flag whose value is decided by odds, so I can roll a feature out to a fraction of resolutions.

**Expected Behavior / Usage:**

A flag may be defined with a draw expressed as winning odds out of a total. When the winning count equals the total, the draw always succeeds and the flag resolves to true; when the winning count is zero, the draw always fails and resolves to false. The drawn value is what is stored and reported.

**Test Cases:** `rcb_tests/public_test_cases/feature9_lottery.json`

```json
{
    "description": "Define a feature whose value is decided by a probabilistic draw expressed as winning odds out of a total. When the winning count equals the total, the draw always succeeds and the feature resolves to true; when the winning count is zero, the draw always fails and the feature resolves to false. The drawn value is what is stored and reported.",
    "cases": [
        {
            "input": {"operations": [
                {"op": "define", "feature": "always", "resolver": {"type": "lottery", "wins": 1, "out": 1}},
                {"op": "define", "feature": "never", "resolver": {"type": "lottery", "wins": 0, "out": 1}},
                {"op": "value", "feature": "always"},
                {"op": "value", "feature": "never"}
            ]},
            "expected_output": "value always = true\nvalue never = false\n"
        }
    ]
}
```

---

### Feature 10: HTTP Request Gating

**As a developer**, I want to guard an HTTP request so it only proceeds when required flags are active, so feature-gated endpoints reject traffic when the feature is off.

**Expected Behavior / Usage:**

A request guard is given one or more required flag names. When every required flag is active, the guarded request passes through and produces a successful HTTP 200 outcome. When any required flag is missing or inactive, the request is rejected with an HTTP 400 (bad request) outcome instead of reaching the handler.

**Test Cases:** `rcb_tests/public_test_cases/feature10_http_middleware.json`

```json
{
    "description": "Guard an HTTP request so it only proceeds when all required features are active. When every required feature is active, the guarded request passes through and yields a successful HTTP 200 response. When any required feature is missing or inactive, the request is rejected with an HTTP 400 (bad request) outcome instead of reaching the handler.",
    "cases": [
        {
            "input": {"operations": [
                {"op": "ensureActive", "features": "missing"}
            ]},
            "expected_output": "middleware = blocked status=400\n"
        }
    ]
}
```

---

### Feature 11: Listing Defined Flags

**As a developer**, I want to list every defined flag, so I can introspect what the engine knows about.

**Expected Behavior / Usage:**

The `defined` query returns the names of all currently defined flags, in the order they were defined.

**Test Cases:** `rcb_tests/public_test_cases/feature11_defined_list.json`

```json
{
    "description": "List the names of all currently defined features, in the order they were defined.",
    "cases": [
        {
            "input": {"operations": [
                {"op": "define", "feature": "foo", "resolver": {"type": "const", "value": true}},
                {"op": "define", "feature": "bar", "resolver": {"type": "const", "value": false}},
                {"op": "define", "feature": "baz", "resolver": {"type": "const", "value": false}},
                {"op": "defined"}
            ]},
            "expected_output": "defined = [\"foo\",\"bar\",\"baz\"]\n"
        }
    ]
}
```

---

### Feature 12: Neutral Error Categories

**As a developer**, I want misuse reported as stable, language-independent error categories, so callers can react to failures without depending on runtime internals.

**Expected Behavior / Usage:**

Requesting the value for more than one scope at once is not supported and yields the error category `multiple_scope_values`. Using a scope that cannot be reduced to a stable string identifier yields the error category `unserializable_scope`. Errors are reported as a single line `error=<category>` and never leak host-language type names or messages.

**Test Cases:** `rcb_tests/public_test_cases/feature12_errors.json`

```json
{
    "description": "Report misuse through neutral, language-independent error categories rather than leaking runtime details. Requesting the value for more than one scope at once is not supported and yields a multiple-scope error category. Using a scope that cannot be reduced to a stable string identifier yields an unserializable-scope error category.",
    "cases": [
        {
            "input": {"operations": [
                {"op": "value", "feature": "foo", "scope": [1, 2, 3]}
            ]},
            "expected_output": "error=multiple_scope_values\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the feature-flag engine described above (definition + resolvers, scoped storage with caching, runtime overrides, aggregate checks, conditional execution, forget/purge, probabilistic resolution, request gating, introspection). Its physical structure must align with the "Scale-Driven Code Organization" constraint, and the core logic must be decoupled from stdin/stdout and JSON parsing.

2. **The Execution/Test Adapter:** A runnable entry point that reads a single JSON request `{ "operations": [ ... ] }` from stdin, applies each operation in order against the core engine, and prints the result of each *query* operation to stdout. Mutating operations print nothing. The adapter is the only component aware of JSON and stdout, and it is responsible for normalizing native failures into the neutral `error=<category>` lines (Feature 12) without changing core behavior.

   **Scope encoding** (the value of a `"scope"` field; absent means "use the default scope"):
   - `null` → the global/unscoped scope; a JSON string → a string scope; a JSON number → a numeric scope.
   - `{"user": <id>}` → a domain object scope carrying an integer identity field `id` (use `{"user": null}` for an identity-less object). Two such objects with the same id are the same scope; a resolver can read the object's `id`.
   - `{"scopeable": "<identifier>"}` → an object scope that advertises the given string identifier; it collapses to the same scope as a plain string equal to that identifier.
   - `{"unserializable": true}` → an object scope that cannot be reduced to a string (used to trigger `unserializable_scope`).
   - A JSON array of any of the above → multiple scopes at once.

   **Resolver specifications** (the value of a `"resolver"` field on `define`):
   - `{"type": "const", "value": <v>}` → always resolves to `<v>`; accepts a null scope.
   - `{"type": "shorthand", "value": <v>}` → registers `<v>` directly as the value.
   - `{"type": "counter", "value": <v>}` → resolves to `<v>` and increments this flag's invocation counter each time it runs (counter readable via the `calls` query).
   - `{"type": "echoScope"}` → resolves to the scope it is given.
   - `{"type": "scopeIdEquals", "id": <n>}` → resolves to `true` when the scope object's `id` equals `<n>`, else `false`.
   - `{"type": "requiresUserScope", "value": <v>}` → requires a concrete object scope; resolves to `<v>` for such a scope, and (per Feature 3.5) to inactive when given a null scope.
   - `{"type": "lottery", "wins": <w>, "out": <t>}` → a probabilistic draw of `<w>` out of `<t>` (see Feature 9).

   **Operations.** Mutating (no output): `define` (`feature`, `resolver`), `activate` (`feature` string|list, optional `value`, optional `scope`), `deactivate` (`feature`, optional `scope`), `activateForEveryone` (`feature`, optional `value`), `deactivateForEveryone` (`feature`), `forget` (`feature`, optional `scope`), `purge` (optional `features` list; absent = all), `flushCache`, `load` (`features`, optional `scope`), `loadMissing` (`features`, optional `scope`), `loginUser` (`id`), `resolveScopeUsing` (`scope`).
   Query (one stdout line each, in operation order):
   - `active`/`inactive` (`feature`, optional `scope`) → `active <feature> = <true|false>` / `inactive <feature> = <true|false>`.
   - `value` (`feature`, optional `scope`) → `value <feature> = <json>` (the value rendered as compact JSON).
   - `values` (`features`, optional `scope`) → `values = <json-object>`.
   - `all` (optional `scope`) → `all = <json-object>`.
   - `defined` → `defined = <json-array>`.
   - `allAreActive`/`someAreActive`/`allAreInactive`/`someAreInactive` (`features`, optional `scope`) → `<op> = <true|false>`.
   - `calls` (`feature`) → `calls <feature> = <integer>`.
   - `when`/`unless` (`feature`, optional `scope`) → `when <feature> = active <json-value>` or `when <feature> = inactive` (and likewise for `unless`).
   - `ensureActive` (`features` string|list, optional `uri`) → `middleware = passed status=200` or `middleware = blocked status=400`.

   All JSON in output is compact (no spaces after `:` or `,`), with `/` and non-ASCII characters left unescaped. Every emitted line ends with a newline.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the same pattern as the event emitter's type handling
