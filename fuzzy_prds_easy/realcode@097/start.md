## Product Requirement Document

# Request Rate-Limit Policy Engine — Per-Route Quota Accounting and Enforcement

## Project Goal

Build a request rate-limiting engine that lets an API gateway cap how many requests each route may serve within a refresh window, so operators can protect upstream services from overload without hand-rolling counting, bucketing, and rejection logic at every entry point.

---

## Background & Problem

A gateway receives incoming HTTP requests and forwards each one to an upstream route. Some routes must be protected by a quota: only a fixed number of requests may pass within a rolling time window before further requests are rejected. Without a shared engine, every gateway deployment re-implements the same fragile machinery — figuring out which route a request belongs to, deciding whether that route is even governed by a quota, bucketing requests so that distinct callers are counted independently, counting down the remaining allowance, and finally rejecting the overflow with the right HTTP status.

This engine packages that machinery behind one contract. Given a configuration that declares the known routes and the per-route quota policies, it answers three questions for any incoming request: does a policy apply to it, how much allowance is left after counting it, and — once the allowance is gone — is it rejected with the standard "too many requests" response. Quota state is held in an in-memory store keyed per caller-identity so that independent callers do not share a bucket.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., route resolution, policy lookup, quota accounting, enforcement), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate route resolution, policy matching, quota accounting, enforcement, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The accounting engine must be open for extension (e.g., alternative quota stores) but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions (e.g., a quota-store abstraction), not low-level implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully (e.g., a request whose route is not governed by any policy). Errors should be modeled properly rather than relying on generic faults.

---

## Core Features

### Feature 1: Rate-Limit Applicability

**As a developer**, I want to know whether an incoming request is governed by a quota policy, so I can short-circuit requests that need no limiting and apply quota accounting only where a policy exists.

**Expected Behavior / Usage:**

The configuration declares an `enabled` flag, a list of known `routes` (each a `{id, path}` pair where `path` is a URL prefix), and a map of `policies` keyed by route id. A policy carries a `limit` (allowed requests per window), a `refreshInterval` (window length in seconds), and a list of identity `types` used to bucket callers. For an incoming `request` (which supplies a `uri`), the engine first resolves the matching route by scanning the declared routes in order and selecting the first whose `path` is a prefix of the request `uri`. If a route matches, the engine looks up a policy by that route's id. Rate limiting applies only when the feature is `enabled` AND a policy governs the resolved route. The output is two lines: `route_matched=<true|false>` reporting whether any route prefix matched the URI, then `should_limit=<true|false>` reporting whether the request will be subject to quota accounting. A request whose URI matches no declared route reports `route_matched=false`; a request whose route matches but has no associated policy reports `route_matched=true` with `should_limit=false`. Use `runs=0` to request applicability only, with no quota accounting.

**Test Cases:** `rcb_tests/public_test_cases/feature1_policy_applicability.json`

```json
{
    "description": "Decide whether an incoming request to a given route is subject to rate limiting. The configuration declares a set of named routes (each with an id and a path prefix) and a map of rate-limit policies keyed by route id. For a request URI, the system first resolves the matching route by longest path-prefix; if a route matches, it looks up a policy by that route's id. Rate limiting applies only when the feature is enabled AND a policy governs the resolved route. The output reports whether a route matched the URI and whether the request will be rate limited.",
    "cases": [
        {
            "input": {
                "config": {"enabled": true, "behindProxy": true, "keyPrefix": "rate-limit-application",
                    "policies": {"serviceA": {"limit": 2, "refreshInterval": 2, "types": ["ORIGIN", "URL", "USER"]}},
                    "routes": [{"id": "serviceA", "path": "/serviceA"}, {"id": "serviceB", "path": "/serviceB"}]},
                "request": {"uri": "/serviceA", "remoteAddr": "10.0.0.100"},
                "runs": 0
            },
            "expected_output": "route_matched=true\nshould_limit=true\n"
        },
        {
            "input": {
                "config": {"enabled": true,
                    "policies": {"serviceA": {"limit": 2, "refreshInterval": 2, "types": ["ORIGIN", "URL", "USER"]}},
                    "routes": [{"id": "serviceA", "path": "/serviceA"}, {"id": "serviceB", "path": "/serviceB"}]},
                "request": {"uri": "/serviceB", "remoteAddr": "127.0.0.1"},
                "runs": 0
            },
            "expected_output": "route_matched=true\nshould_limit=false\n"
        },
        {
            "input": {
                "config": {"enabled": true,
                    "policies": {"serviceA": {"limit": 2, "refreshInterval": 2, "types": ["ORIGIN", "URL", "USER"]}},
                    "routes": [{"id": "serviceA", "path": "/serviceA"}, {"id": "serviceB", "path": "/serviceB"}]},
                "request": {"uri": "/serviceZ", "remoteAddr": "10.0.0.100"},
                "runs": 0
            },
            "expected_output": "route_matched=false\nshould_limit=false\n"
        }
    ]
}
```

---

### Feature 2: Quota Consumption Accounting

**As a developer**, I want each accounted request to count against its route's quota and report how much allowance remains, so clients can see their dwindling budget within the current window.

**Expected Behavior / Usage:**

When a policy applies, the engine accounts the request against an in-memory quota bucket for the caller. A freshly opened window starts with the policy's `limit` as its allowance; each accounted request decrements the remaining allowance by one. Replaying the same request within the same window therefore counts the remaining allowance down from `limit - 1` toward zero. The `runs` field specifies how many times the same request is replayed. The output begins with the applicability lines (`route_matched`, `should_limit`), then emits one line per replay of the form `run=<n> limit=<L> remaining=<R>`, where `<n>` is the 1-based replay index, `<L>` is the policy limit, and `<R>` is the allowance left after that replay. With a limit of 2 and two replays, the remaining values are `1` then `0`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_quota_consumption.json`

```json
{
    "description": "Account a request against its rate-limit policy and report the remaining quota. A policy grants a fixed number of allowed requests (its limit) per refresh window. Each accounted request decrements the remaining allowance by one. When the request is replayed within the same window the remaining count counts down from limit-minus-one toward zero. The output reports, for each replay, the configured limit and the remaining allowance after that request.",
    "cases": [
        {
            "input": {
                "config": {"enabled": true, "behindProxy": true,
                    "policies": {"serviceA": {"limit": 2, "refreshInterval": 2, "types": ["ORIGIN", "URL", "USER"]}},
                    "routes": [{"id": "serviceA", "path": "/serviceA"}]},
                "request": {"uri": "/serviceA", "remoteAddr": "10.0.0.100"},
                "runs": 2
            },
            "expected_output": "route_matched=true\nshould_limit=true\nrun=1 limit=2 remaining=1\nrun=2 limit=2 remaining=0\n"
        }
    ]
}
```

---

### Feature 3: Quota Exhaustion Enforcement

**As a developer**, I want the request that overruns the quota to be rejected with the standard "too many requests" response, so upstream services are shielded once a caller exceeds its budget.

**Expected Behavior / Usage:**

The engine enforces the quota once it is exhausted. While allowance remains, replayed requests behave exactly as in Feature 2 — each prints `run=<n> limit=<L> remaining=<R>`. The replay that pushes consumption past the configured `limit` is rejected: the remaining allowance reported to the client is clamped at zero (never negative), the request is flagged as having exceeded its quota, and it is answered with the HTTP status for Too Many Requests (`429`). For the rejected replay the output line is extended with two extra fields: `run=<n> limit=<L> remaining=0 exceeded=true [a specific HTTP error code reserved for rate limiting]`. With a limit of 2 and three replays, the first two replays report remaining `1` then `0`, and the third is the rejection line.

**Test Cases:** `rcb_tests/public_test_cases/feature3_limit_enforcement.json`

```json
{
    "description": "Enforce the rate-limit policy once its quota is exhausted. While allowance remains, replayed requests simply decrement the remaining count. The request that pushes consumption past the configured limit is rejected: the remaining allowance reported to the client is clamped at zero, the request is flagged as having exceeded its quota, and it is answered with the Too Many Requests HTTP status (429). The output reports the limit and remaining allowance for each replay, and on the rejected replay additionally reports the exceeded flag and the assigned status code.",
    "cases": [
        {
            "input": {
                "config": {"enabled": true, "behindProxy": true,
                    "policies": {"serviceA": {"limit": 2, "refreshInterval": 2, "types": ["ORIGIN", "URL", "USER"]}},
                    "routes": [{"id": "serviceA", "path": "/serviceA"}]},
                "request": {"uri": "/serviceA", "remoteAddr": "10.0.0.100", "headers": {"X-FORWARDED-FOR": "10.0.0.1"}},
                "runs": 3
            },
            "expected_output": "route_matched=true\nshould_limit=true\nrun=1 limit=2 remaining=1\nrun=2 limit=2 remaining=0\nrun=3 limit=2 remaining=0 exceeded=true [a specific HTTP error code reserved for rate limiting]\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing route resolution, per-route policy matching, in-memory quota accounting, and enforcement, following the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the resulting lines to stdout, matching the per-feature contracts above. The request supplies a `config` (the `enabled` flag, declared `routes`, and per-route `policies`), an incoming `request` (at minimum a `uri`; optionally a `remoteAddr` and request `headers`), and a `runs` count. The adapter resolves applicability, then — when applicable and `runs > 0` — accounts the request `runs` times, printing the per-replay quota lines and, on the rejected replay, the `exceeded=true [a specific HTTP error code reserved for rate limiting]` fields. A `runs` of `0` requests applicability output only.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- check the reset logic in the timestamp_handler module
