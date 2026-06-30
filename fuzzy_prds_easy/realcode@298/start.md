## Product Requirement Document

# Authentication & Authorization Toolkit - Password Hashing, Permission Resolution, and Login Throttling

## Project Goal

Build a backend authentication and authorization toolkit that gives developers a set of small, composable building blocks for securing user accounts: pluggable password hashing, a permission-resolution engine that answers "is this actor allowed to do X?", per-entity permission management, and brute-force login throttling with account-activation gating. Developers get correct, well-tested security primitives so they do not have to hand-roll cryptographic verification, permission-matching rules, or lockout math in every application.

---

## Background & Problem

Without a toolkit like this, every application re-implements the same security-sensitive plumbing by hand: choosing a hashing scheme and wiring up constant-time verification, writing ad-hoc permission checks scattered through controllers, and inventing lockout logic to slow down password-guessing attacks. This hand-rolled code is repetitive, easy to get subtly wrong (timing leaks, off-by-one lockout windows, permission rules that silently grant too much), and painful to maintain as requirements evolve.

With this toolkit, hashing is a single pluggable interface (swap schemes without touching call sites), permissions are declared as data and resolved by a documented rule set (lenient vs. strict, wildcards, grouped class/method keys), entity permissions are managed through a small mutation API, and login throttling is expressed as tunable interval/threshold policies that compute exactly how long an actor must wait. The application code shrinks to declaring intent and reading back yes/no answers.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain has several distinct responsibilities (hashing strategies, permission resolution, entity permission management, throttling/activation gates, delay computation) and therefore MUST be organized as a multi-file, multi-module repository with clear separation between the core domain and the execution adapter. Do not collapse it into a single "god file"; equally, do not over-engineer the simpler pieces.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in "Core Features" are a **black-box contract for the execution adapter**, NOT the internal data model. The core security logic must remain completely decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls into the core domain and rendering results to the line-oriented stdout contract.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility:** Keep hashing, permission resolution, permission management, throttling decisions, and delay computation in separate units; keep parsing/routing/formatting in the adapter.
   - **Open/Closed:** New hashing strategies and new permission policies must be addable without modifying the resolution engine or the gate logic.
   - **Liskov Substitution:** Every hashing strategy must be interchangeable behind one hashing interface; every permission policy must be interchangeable behind one resolution interface.
   - **Interface Segregation:** Keep the hashing, permission, throttle, and activation interfaces small and cohesive.
   - **Dependency Inversion:** Gates depend on abstract delay/activation providers, not concrete storage.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public surface (hash/check, hasAccess/hasAnyAccess, add/update/remove/set permission, gate checks) must read naturally in the target language.
   - **Resilience:** Domain failures (a blocked login, an unactivated account) MUST be modeled as explicit, typed error conditions carrying structured data (which source tripped, the user reference), not generic faults. The execution adapter renders these as the neutral error contract lines defined below and MUST NOT leak host-language runtime details.

---

## Core Features

### Feature 1: Pluggable Password Hashing

**As a developer**, I want to hash passwords and verify them through a single interchangeable interface, so I can choose or swap a hashing scheme without changing the code that calls it.

**Expected Behavior / Usage:**

A hashing strategy turns a plaintext password into an opaque digest and can later check whether a candidate plaintext matches a digest. The input names which strategy to use (`bcrypt` for an adaptive salted scheme, `native` for the platform default scheme, `sha256` and `whirlpool` for salted digest schemes, and `reverse` for a trivial custom callback strategy that exists only to prove strategies are pluggable), the `password` to hash, and a list of `verify` candidates. The output reports the strategy name, asserts the digest is not equal to the plaintext (`hash_differs_from_input=true`), and for each candidate prints `verify[<candidate>]=true|false` — true only when the candidate equals the original password. Passwords may contain short strings, UTF-8 letters, and arbitrary punctuation; all must hash and verify correctly. Because most schemes salt randomly, the digest itself is non-deterministic and is never printed — only the stable verification outcomes are.

**Test Cases:** `rcb_tests/public_test_cases/feature1_password_hashing.json`

```json
{
    "description": "Password hashing and verification across interchangeable hashing strategies. Each case hashes a plaintext password with the named strategy, confirms the produced digest is not equal to the original plaintext, then verifies the digest against a set of candidate strings (the correct password must verify true; wrong candidates must verify false).",
    "cases": [
        {
            "input": {"op": "hash", "algo": "bcrypt", "password": "password", "verify": ["password", "fail"]},
            "expected_output": "algorithm=bcrypt\nhash_differs_from_input=true\nverify[password]=true\nverify[fail]=false\n"
        },
        {
            "input": {"op": "hash", "algo": "sha256", "password": "fÄÓñ", "verify": ["fÄÓñ"]},
            "expected_output": "algorithm=sha256\nhash_differs_from_input=true\nverify[fÄÓñ]=true\n"
        },
        {
            "input": {"op": "hash", "algo": "reverse", "password": "abc", "verify": ["abc", "wrong"]},
            "expected_output": "algorithm=reverse\nhash_differs_from_input=true\nverify[abc]=true\nverify[wrong]=false\n"
        }
    ]
}
```

---

### Feature 2: Lenient Permission Resolution

**As a developer**, I want to ask whether an actor is allowed to perform one or more actions, with role/group grants layered beneath the actor's own grants, so I can answer access questions from declarative permission data.

**Expected Behavior / Usage:**

A permission set maps string keys to boolean grants. An optional ordered list of secondary sets (think group or role grants) is provided alongside. Under the **lenient** policy the secondary sets are accumulated first, then the actor's primary set is merged on top so that the actor's own explicit grants win. A key that appears nowhere defaults to denied. Two query forms are evaluated: an `all` query (the actor must be granted EVERY listed key) and an `any` query (the actor must be granted AT LEAST ONE listed key). The output echoes the policy mode and, for each query, prints `all[k1,k2,...]=true|false` or `any[k1,k2,...]=true|false`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_lenient_inheritance.json`

```json
{
    "description": "Lenient access resolution. A permission set maps permission keys to boolean grants. An optional list of secondary permission sets (e.g. group/role grants) is merged underneath the primary set. Under the lenient policy a primary set that contains at least one explicit grant wins by being merged on top of the accumulated secondary grants; a key absent everywhere defaults to denied. hasAccess (all) returns granted only when EVERY queried key resolves to true; hasAnyAccess (any) returns granted when AT LEAST ONE queried key resolves to true.",
    "cases": [
        {
            "input": {"op": "permissions", "mode": "lenient", "permissions": {"user.create": true, "user.update": false, "user.delete": true}, "secondary": [{"user.update": true}, {"user.view": true}, {"user.delete": false}], "queries": [{"all": ["user.create"]}, {"all": ["user.view"]}, {"all": ["user.delete"]}, {"all": ["user.update"]}, {"all": ["user.create", "user.update"]}, {"any": ["user.create", "user.update"]}, {"any": ["user.update", "user.delete"]}]},
            "expected_output": "mode=lenient\nall[user.create]=true\nall[user.view]=true\nall[user.delete]=true\nall[user.update]=false\nall[user.create,user.update]=false\nany[user.create,user.update]=true\nany[user.update,user.delete]=true\n"
        }
    ]
}
```

---

### Feature 3: Permission Matching Semantics

**As a developer**, I want fine-grained control over how permission keys combine and match, so I can express strict-deny policies, wildcard coverage, and grouped class/method permissions declaratively.

**Expected Behavior / Usage:**

*3.1 Strict Permission Resolution — denials propagate across all sets*

Under the **strict** policy every contributing set (secondary sets first, then the primary set) is folded into one prepared map, and within that fold an explicit denial for a key always overrides any earlier grant for the same key. The consequence, contrasted with the lenient policy, is that a key denied by ANY contributing set stays denied even if the actor's primary set granted it. Query semantics are unchanged: `all` requires every listed key granted; `any` requires at least one. The output echoes `mode=strict` and one line per query.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_strict_inheritance.json`

```json
{
    "description": "Strict access resolution. Identical query semantics to the lenient policy, but the merge rule differs: every set (secondary first, then primary) is folded into one prepared map where an explicit denial always overrides a prior grant for the same key, so a key denied by any contributing set stays denied. hasAccess (all) requires all queried keys true; hasAnyAccess (any) requires at least one queried key true.",
    "cases": [
        {
            "input": {"op": "permissions", "mode": "strict", "permissions": {"foo": true, "bar": false, "fred": true}, "secondary": [{"bar": true}, {"qux": true}, {"fred": false}], "queries": [{"all": ["foo"]}, {"all": ["qux"]}, {"all": ["bar"]}, {"all": ["fred"]}, {"all": ["foo", "bar"]}, {"any": ["foo", "bar"]}, {"any": ["bar", "fred"]}]},
            "expected_output": "mode=strict\nall[foo]=true\nall[qux]=true\nall[bar]=false\nall[fred]=false\nall[foo,bar]=false\nany[foo,bar]=true\nany[bar,fred]=false\n"
        }
    ]
}
```

*3.2 Wildcard Matching — patterns cover concrete keys and vice-versa*

Permission keys may contain an asterisk acting as a glob. A query is granted when it matches a stored granted key by pattern in either direction: a stored pattern key (e.g. `user.*`) covers a concrete queried key (`user.create`), and a queried pattern (`user*`) is satisfied by a stored concrete grant. A query that is merely a bare prefix segment with no asterisk (e.g. `user`) does NOT match dotted keys. Wildcard behavior is policy-independent.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_wildcard_matching.json`

```json
{
    "description": "Wildcard pattern matching of permission keys. A queried key containing an asterisk is matched against stored keys (and stored wildcard keys are matched against queried keys) so a grant on a pattern covers concrete keys and vice-versa. A bare prefix segment with no wildcard does not match dotted keys.",
    "cases": [
        {
            "input": {"op": "permissions", "mode": "lenient", "permissions": {"user.create": true, "user.update": false}, "queries": [{"all": ["user*"]}, {"all": ["user"]}]},
            "expected_output": "mode=lenient\nall[user*]=true\nall[user]=false\n"
        },
        {
            "input": {"op": "permissions", "mode": "lenient", "permissions": {"user.*": true}, "queries": [{"all": ["user.create"]}, {"all": ["user.update"]}]},
            "expected_output": "mode=lenient\nall[user.create]=true\nall[user.update]=true\n"
        }
    ]
}
```

*3.3 Class/Method Keys and Exact-Key Priority — grouped keys expand; explicit keys beat patterns*

A permission key of the form `Class@method1,method2` is shorthand: it expands into one grant per comma-separated method (`Class@method1`, `Class@method2`), each sharing the key's boolean value, so individual `Class@method` queries resolve against the expansion. Independently, an exact key match always takes priority over a covering wildcard pattern, so an explicit denial on a concrete key (e.g. `user.delete=false`) holds even when a broader pattern (`user.*=true`) would otherwise grant it.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_class_method_keys.json`

```json
{
    "description": "Class-and-method permission keys. A key of the form Class@method1,method2 is expanded into one grant per comma-separated method (Class@method1, Class@method2) sharing the key's boolean value, and an individual Class@method query resolves against the expansion. Also covers personal-key priority: an exact key match wins over a covering wildcard pattern, so an explicit denial on a concrete key holds even when a covering pattern is granted.",
    "cases": [
        {
            "input": {"op": "permissions", "mode": "strict", "permissions": {"Class@method1,method2": true}, "queries": [{"all": ["Class@method1"]}, {"all": ["Class@method2"]}]},
            "expected_output": "mode=strict\nall[Class@method1]=true\nall[Class@method2]=true\n"
        },
        {
            "input": {"op": "permissions", "mode": "lenient", "permissions": {"user.*": true, "user.delete": false}, "queries": [{"all": ["user.*"]}, {"all": ["user.test"]}, {"all": ["user.delete"]}]},
            "expected_output": "mode=lenient\nall[user.*]=true\nall[user.test]=true\nall[user.delete]=false\n"
        }
    ]
}
```

---

### Feature 4: Entity Permission Management

**As a developer**, I want to mutate an entity's own permission map with small explicit operations, so I can build up or adjust an actor's grants programmatically and read the result back.

**Expected Behavior / Usage:**

An entity owns a permission map. Four operations mutate it, applied in order: `add` inserts a key with a grant (default true) but is a no-op when the key already exists; `update` changes the grant of an existing key and, unless an explicit create flag is passed, is a no-op when the key is absent (with the create flag it inserts the key); `remove` deletes a key if present; `set` replaces the entire map. After all operations the final map is printed as `key=true|false` lines in insertion order (or the single token `permissions=empty` if no keys remain).

**Test Cases:** `rcb_tests/public_test_cases/feature4_permission_management.json`

```json
{
    "description": "Mutating an entity's own permission map through discrete operations, then reading back the final map as key=grant lines in insertion order. add inserts a key with a grant (default true) but is a no-op if the key already exists; update changes an existing key's grant and, unless a create flag is passed, is a no-op when the key is absent; remove deletes a key if present; set replaces the entire map. Output lists every surviving key with its boolean grant.",
    "cases": [
        {
            "input": {"op": "permissible", "actions": [{"op": "add", "args": ["test"]}, {"op": "add", "args": ["test1"]}, {"op": "update", "args": ["test1", false]}]},
            "expected_output": "test=true\ntest1=false\n"
        },
        {
            "input": {"op": "permissible", "actions": [{"op": "add", "args": ["test1"]}, {"op": "update", "args": ["test2", false]}]},
            "expected_output": "test1=true\n"
        },
        {
            "input": {"op": "permissible", "actions": [{"op": "add", "args": ["test1"]}, {"op": "update", "args": ["test2", false, true]}]},
            "expected_output": "test1=true\ntest2=false\n"
        },
        {
            "input": {"op": "permissible", "actions": [{"op": "add", "args": ["test"]}, {"op": "add", "args": ["test1"]}, {"op": "remove", "args": ["test1"]}]},
            "expected_output": "test=true\n"
        }
    ]
}
```

---

### Feature 5: Pluggable Access Policy on an Entity

**As a developer**, I want an entity to carry a configurable access policy that decides how its own grants combine with inherited grants, so I can switch between permissive and restrictive behavior without rewriting the entity.

**Expected Behavior / Usage:**

An entity exposes a selectable policy (`lenient` or `strict`) that governs how its primary permissions combine with secondary (inherited) sets when an access query is resolved through the entity itself. Given identical primary and secondary data, the two policies can disagree about a key granted in one set and denied in another: lenient lets the entity's primary grant win, strict lets any denial stand. The output echoes the active policy and the resolved `all[...]` answers.

**Test Cases:** `rcb_tests/public_test_cases/feature5_pluggable_policy.json`

```json
{
    "description": "Configurable access policy on a permissible entity. The entity has a pluggable policy (lenient or strict) selecting how primary and secondary permission sets combine when an access query is evaluated through the entity. The same data is evaluated under each policy to show the policy choice changes the resolved grant for a key granted in one set and denied in another.",
    "cases": [
        {
            "input": {"op": "permissible_policy", "policy": "lenient", "permissions": {"user.update": false}, "secondary": [{"user.update": true}], "queries": [{"all": ["user.update"]}]},
            "expected_output": "policy=lenient\nall[user.update]=false\n"
        },
        {
            "input": {"op": "permissible_policy", "policy": "strict", "permissions": {"foo": true, "bar": false}, "secondary": [{"bar": true}, {"qux": true}], "queries": [{"all": ["foo"]}, {"all": ["qux"]}, {"all": ["bar"]}]},
            "expected_output": "policy=strict\nall[foo]=true\nall[qux]=true\nall[bar]=false\n"
        }
    ]
}
```

---

### Feature 6: Login Throttling Gate

**As a developer**, I want a gate that blocks login attempts when too many recent failures have piled up, so I can defend accounts against brute-force password guessing.

**Expected Behavior / Usage:**

The gate consults three independent delay sources, each reporting a remaining lock duration in seconds: a `global` source (across all accounts), an optional `ip` source (consulted only when an IP address is supplied), and a per-`user` source. The requested `action` selects which sources apply: a `login` attempt consults global, then ip, then user; a session `check` (re-validating an already-authenticated actor) consults only ip; a `fail` (recording a failed attempt) first re-runs the login checks and, if clear, logs the attempt. The FIRST source with a positive delay, in the fixed precedence order global > ip > user, trips a throttling error reporting `throttle_type`, the remaining `delay_seconds`, and `unlock_in_seconds` (time until the lock lifts). When no consulted source reports a positive delay, a login/check yields `outcome=allowed` and a fail yields `outcome=attempt_logged`. Errors are emitted as the neutral contract below — no host-language exception identity appears in stdout.

**Test Cases:** `rcb_tests/public_test_cases/feature6_throttle_gate.json`

```json
{
    "description": "Brute-force login gate consulting three independent delay sources, each reporting a remaining lock duration in seconds: global, an optional IP source, and per-user. A login attempt checks global then ip then user; a session check checks only ip; recording a failed attempt re-runs the login checks then logs. The first positive source in order global > ip > user trips a throttling error reporting the source, the remaining delay, and seconds until unlock; if none are positive the action is permitted.",
    "cases": [
        {
            "input": {"op": "throttle_gate", "action": "login", "delays": {"global": 0, "user": 0}},
            "expected_output": "outcome=allowed\n"
        },
        {
            "input": {"op": "throttle_gate", "action": "login", "delays": {"global": 10}},
            "expected_output": "error=throttling\nthrottle_type=global\ndelay_seconds=10\nunlock_in_seconds=10\n"
        },
        {
            "input": {"op": "throttle_gate", "action": "fail", "ip": "127.0.0.1", "delays": {"global": 0, "ip": 0, "user": 10}},
            "expected_output": "error=throttling\nthrottle_type=user\ndelay_seconds=10\nunlock_in_seconds=10\n"
        },
        {
            "input": {"op": "throttle_gate", "action": "fail", "ip": "127.0.0.1", "delays": {"global": 0, "ip": 0, "user": 0}},
            "expected_output": "outcome=attempt_logged\n"
        }
    ]
}
```

---

### Feature 7: Account Activation Gate

**As a developer**, I want a gate that refuses to log in accounts whose activation is not complete, so I can require email/confirmation before granting access.

**Expected Behavior / Usage:**

Before a `login` or session `check` proceeds, the gate asks an activation provider whether the account's activation has been completed. When completed, the gate permits (`outcome=allowed`). When not completed, the gate denies with a not-activated error; the denied user reference is attached to the error so a caller can identify which account was blocked, surfaced in the contract as `user_attached=true`. Both actions enforce the gate identically. The error is rendered in the neutral contract form, never leaking host-language runtime details.

**Test Cases:** `rcb_tests/public_test_cases/feature7_activation_gate.json`

```json
{
    "description": "Account-activation gate. Before a login or session check proceeds the gate asks whether the account's activation has been completed. When completed it permits. When not completed it denies with a not-activated error, and the denied user reference is attached so callers can identify the blocked account.",
    "cases": [
        {
            "input": {"op": "activation_gate", "action": "login", "completed": true},
            "expected_output": "outcome=allowed\n"
        },
        {
            "input": {"op": "activation_gate", "action": "check", "completed": false},
            "expected_output": "error=not_activated\nuser_attached=true\n"
        }
    ]
}
```

---

### Feature 8: Brute-Force Delay Computation

**As a developer**, I want to compute exactly how long an actor must wait given their recent failed attempts and a configured policy, so the throttling gate has a precise, tunable lock duration.

**Expected Behavior / Usage:**

Given a window of recent failed attempts (each expressed as how many seconds ago it happened, all already inside the configured lookback window) and a per-source threshold policy, compute the remaining lock in seconds. Two threshold shapes are supported. A **fixed** integer threshold: if the number of attempts in the window is at least the threshold, the lock lasts one full interval measured from the OLDEST attempt; otherwise the delay is zero. A **tiered** map `{attempt_count: delay}`: scanning tiers from the highest attempt-count downward, the first tier whose attempt-count is strictly below the current count selects that tier's delay, and the remaining lock is that delay measured from the MOST RECENT attempt (zero if that delay has already elapsed). The computation is identical for the global, ip, and user sources. The output reports the source `type`, the `attempt_count`, the `threshold_kind` (`fixed` or `tiered`), and the resulting `delay_seconds`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_brute_force_delay.json`

```json
{
    "description": "Brute-force delay computation from a window of recent failed attempts (each given as seconds-ago, all inside the lookback window). Fixed threshold: if attempts in the window are at least the threshold, the lock lasts a full interval measured from the OLDEST attempt; otherwise zero. Tiered threshold {attempts: delay}: scanning tiers from highest attempt-count downward, the first tier whose attempt-count is below the current count selects that tier's delay, and the remaining lock is that delay measured from the MOST RECENT attempt (zero if already elapsed).",
    "cases": [
        {
            "input": {"op": "throttle_delay", "type": "global", "interval": 10, "thresholds": 5, "attempts": [0, 0, 0, 0, 0, 0]},
            "expected_output": "type=global\nattempt_count=6\nthreshold_kind=fixed\ndelay_seconds=10\n"
        },
        {
            "input": {"op": "throttle_delay", "type": "global", "interval": 10, "thresholds": 200, "attempts": [0, 0, 0, 0, 0, 0]},
            "expected_output": "type=global\nattempt_count=6\nthreshold_kind=fixed\ndelay_seconds=0\n"
        },
        {
            "input": {"op": "throttle_delay", "type": "global", "interval": 10, "thresholds": {"5": 3, "10": 10}, "attempts": [0, 0, 0, 0, 0, 0]},
            "expected_output": "type=global\nattempt_count=6\nthreshold_kind=tiered\ndelay_seconds=3\n"
        },
        {
            "input": {"op": "throttle_delay", "type": "global", "interval": 10, "thresholds": {"5": 33, "10": 100}, "attempts": [200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 200]},
            "expected_output": "type=global\nattempt_count=11\nthreshold_kind=tiered\ndelay_seconds=0\n"
        }
    ]
}
```

---

### Feature 9: Throttle Policy Configuration

**As a developer**, I want to configure the interval and threshold for each throttling source independently and read the settings back, so I can tune lockout aggressiveness per source.

**Expected Behavior / Usage:**

The throttle policy is constructed with an interval (lookback window in seconds) and a threshold for each of the three sources (global, ip, user). Each configured value must be stored on the source it names and be independently retrievable. The output prints the six settings back in a fixed order, establishing the tunable knobs that the delay computation (Feature 8) consumes.

**Test Cases:** `rcb_tests/public_test_cases/feature9_throttle_configuration.json`

```json
{
    "description": "Constructing the throttle policy with explicit interval and threshold settings for each of the three sources (global, ip, user) and reading them straight back, confirming each configured value is stored on the source it names and is independently retrievable.",
    "cases": [
        {
            "input": {"op": "throttle_config", "global_interval": 1, "global_thresholds": 2, "ip_interval": 3, "ip_thresholds": 4, "user_interval": 5, "user_thresholds": 6},
            "expected_output": "global_interval=1\nglobal_thresholds=2\nip_interval=3\nip_thresholds=4\nuser_interval=5\nuser_thresholds=6\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-module codebase implementing pluggable hashing, the permission-resolution engine (lenient/strict policies, wildcard and class/method matching), entity permission management, the login-throttling and activation gates, and the brute-force delay computation. Physical structure must follow the "Scale-Driven Code Organization" constraint: distinct modules for distinct responsibilities, with the core domain decoupled from I/O.

2. **The Execution/Test Adapter:** A runnable entry point that reads ONE JSON command object from stdin, invokes the appropriate core logic, and prints the line-oriented result to stdout, strictly matching the per-feature contracts above. It must normalize domain errors into the neutral contract lines (`error=throttling ...`, `error=not_activated ...`) and never emit host-language exception class names, runtime message suffixes, or object-repr renderings. This adapter must be logically and physically separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_password_hashing.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_password_hashing@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains ONLY the raw stdout of the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same hashing convention as the auth_helper module
- auditable field per the ledger schema
