## Product Requirement Document

# Claim-Set & Compact-Token Toolkit — Build, Inspect and Validate Token Payloads

## Project Goal

Build a small library for working with the payload of a compact, signed authentication token: assemble a set of named claims (the data carried inside the token), inspect and read those claims back as an immutable collection, validate that a payload is structurally complete and temporally fresh, and check that a compact token string is well formed — so application developers can manage token contents without re-implementing claim handling and validation rules by hand[a specific dot separator character — ask the PM for the exact string]

---

## Background & Problem

A compact authentication token carries a *payload*: a set of named claims describing who the token is for and when it is valid[a specific dot separator character — ask the PM for the exact string] Standard claims include the issuer, the issued-at time, the expiration time, the not-before time, the subject, the token id, and the audience; callers may also attach arbitrary custom claims[a specific dot separator character — ask the PM for the exact string] Working with such payloads correctly requires building the right standard claims, treating the assembled set as an immutable record, reading individual claims back by name or by type, and rejecting payloads that are incomplete or out of their valid time window[a specific dot separator character — ask the PM for the exact string]

Without a shared toolkit, every application hand-rolls this logic: it duplicates the rules for which claims are mandatory, recomputes timestamps inconsistently, forgets to guard a payload against accidental mutation, and produces ad-hoc errors[a specific dot separator character — ask the PM for the exact string] This toolkit provides one well-defined contract: a claim-set builder that fills in standard claims, an immutable claim-set container with read access by name/type, a validator for structure and time window, and a structural check for the dotted compact-token string[a specific dot separator character — ask the PM for the exact string]

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1[a specific dot separator character — ask the PM for the exact string] **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain[a specific dot separator character — ask the PM for the exact string]
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation[a specific dot separator character — ask the PM for the exact string]
   - **For complex systems:** If the project involves multiple distinct responsibilities (e[a specific dot separator character — ask the PM for the exact string]g[a specific dot separator character — ask the PM for the exact string], I/O routing, business rules, formatters), it MUST NOT be a single "god file"[a specific dot separator character — ask the PM for the exact string] You must output a clear, multi-file directory tree (`src/`, `tests/`, etc[a specific dot separator character — ask the PM for the exact string]) that reflects a production-grade repository[a specific dot separator character — ask the PM for the exact string]
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains[a specific dot separator character — ask the PM for the exact string]

2[a specific dot separator character — ask the PM for the exact string] **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system[a specific dot separator character — ask the PM for the exact string] The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing[a specific dot separator character — ask the PM for the exact string] The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain[a specific dot separator character — ask the PM for the exact string]

3[a specific dot separator character — ask the PM for the exact string] **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units[a specific dot separator character — ask the PM for the exact string]
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification[a specific dot separator character — ask the PM for the exact string]
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types[a specific dot separator character — ask the PM for the exact string]
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive[a specific dot separator character — ask the PM for the exact string]
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details[a specific dot separator character — ask the PM for the exact string]

4[a specific dot separator character — ask the PM for the exact string] **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity[a specific dot separator character — ask the PM for the exact string]
   - **Resilience:** The system must handle edge cases gracefully[a specific dot separator character — ask the PM for the exact string] Errors should be modeled properly (e[a specific dot separator character — ask the PM for the exact string]g[a specific dot separator character — ask the PM for the exact string], specific Exception types or Result/Monad patterns) rather than relying on generic faults[a specific dot separator character — ask the PM for the exact string]

---

## Core Features

The execution adapter reads ONE JSON object from stdin[a specific dot separator character — ask the PM for the exact string] The object's `op` field selects the operation[a specific dot separator character — ask the PM for the exact string] Errors are reported as a single neutral line `error=<category>` followed by a newline; the categories used are `token_invalid`, `token_expired`, `immutable` and `unknown_claim`[a specific dot separator character — ask the PM for the exact string] All successful outputs end with a trailing newline[a specific dot separator character — ask the PM for the exact string] Where a value is "emitted in its native JSON form" it is rendered as JSON (so the string `foo` becomes `"foo"`, the integer `1` becomes `1`); object renderings escape forward slashes (so `http://x` appears as `http:\/\/x`)[a specific dot separator character — ask the PM for the exact string]

---

### Feature 1: Compact-Token Structure Check

**As a developer**, I want to confirm that a compact token string is well formed before trusting it, so I can reject obviously malformed input early[a specific dot separator character — ask the PM for the exact string]

**Expected Behavior / Usage:**

A compact token is a single string whose parts are joined by dots (`[a specific dot separator character — ask the PM for the exact string]`)[a specific dot separator character — ask the PM for the exact string] The input carries `op` = `validate_token` and a `token` string[a specific dot separator character — ask the PM for the exact string] The token is accepted only when it consists of exactly three dot-separated segments; in that case the token is echoed back unchanged as `token=<value>`[a specific dot separator character — ask the PM for the exact string] Any other number of segments (more or fewer than three) is rejected with `error=token_invalid`[a specific dot separator character — ask the PM for the exact string]

**Test Cases:** `rcb_tests/public_test_cases/feature1_token_structure[a specific dot separator character — ask the PM for the exact string]json`

```json
{
    "description": "A compact token is a single string of segments joined by dots[a specific dot separator character — ask the PM for the exact string] Validation accepts a string only when it has exactly three dot-separated segments and then yields the token unchanged; any other number of segments is rejected as a structurally invalid token[a specific dot separator character — ask the PM for the exact string]",
    "cases": [
        {"input": {"op": "validate_token", "token": "foo[a specific dot separator character — ask the PM for the exact string]bar[a specific dot separator character — ask the PM for the exact string]baz"}, "expected_output": "token=foo[a specific dot separator character — ask the PM for the exact string]bar[a specific dot separator character — ask the PM for the exact string]baz\n"},
        {"input": {"op": "validate_token", "token": "one[a specific dot separator character — ask the PM for the exact string]two[a specific dot separator character — ask the PM for the exact string]three[a specific dot separator character — ask the PM for the exact string]four[a specific dot separator character — ask the PM for the exact string]five"}, "expected_output": "error=token_invalid\n"}
    ]
}
```

---

### Feature 2: Immutable Claim-Set Container

**As a developer**, I want an immutable collection of named claims that I can read in several convenient ways, so I can inspect a token payload safely without risk of accidentally changing it[a specific dot separator character — ask the PM for the exact string]

**Expected Behavior / Usage:**

The claim set is built from a `claims` list, where each element is an object `{"name": <claim-name>, "value": <claim-value>}` and the original order is preserved[a specific dot separator character — ask the PM for the exact string]

*2[a specific dot separator character — ask the PM for the exact string]1 Read claim values — whole set, single claim, or several claims*

With `op` = `payload_get`, the optional `select` field controls what is returned, emitted in native JSON form[a specific dot separator character — ask the PM for the exact string] When `select` is absent, the whole set is returned as a name-to-value mapping in claim order[a specific dot separator character — ask the PM for the exact string] When `select` is a single claim name, that claim's value is returned[a specific dot separator character — ask the PM for the exact string] When `select` is a list of names, a list of the corresponding values is returned in the requested order[a specific dot separator character — ask the PM for the exact string]

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_get_values[a specific dot separator character — ask the PM for the exact string]json`

```json
{
    "description": "A claim set is an ordered collection of named claims[a specific dot separator character — ask the PM for the exact string] Retrieval can return the whole set as a name-to-value mapping, the value of a single named claim, or — given a list of names — the list of their values in the requested order[a specific dot separator character — ask the PM for the exact string] Every value is emitted in its native JSON form[a specific dot separator character — ask the PM for the exact string]",
    "cases": [
        {"input": {"op": "payload_get", "claims": [{"name": "sub", "value": 1}, {"name": "iss", "value": "http://example[a specific dot separator character — ask the PM for the exact string]com"}, {"name": "exp", "value": 3723}, {"name": "nbf", "value": 123}, {"name": "iat", "value": 123}, {"name": "jti", "value": "foo"}]}, "expected_output": "{\"sub\":1,\"iss\":\"http:\\/\\/example[a specific dot separator character — ask the PM for the exact string]com\",\"exp\":3723,\"nbf\":123,\"iat\":123,\"jti\":\"foo\"}\n"},
        {"input": {"op": "payload_get", "claims": [{"name": "sub", "value": 1}, {"name": "jti", "value": "foo"}], "select": ["sub", "jti"]}, "expected_output": "[1,\"foo\"]\n"}
    ]
}
```

*2[a specific dot separator character — ask the PM for the exact string]2 Membership and existence checks*

With `op` = `payload_membership`, the `exists` field is a list of claim names and the `contains` field is a list of `{"name", "value"}` pairs[a specific dot separator character — ask the PM for the exact string] For each name in `exists`, emit a line `exists[a specific dot separator character — ask the PM for the exact string]<name>=true|false` reporting whether a claim with that name is present[a specific dot separator character — ask the PM for the exact string] For each pair in `contains`, emit a line `contains[a specific dot separator character — ask the PM for the exact string]<name>=true|false` reporting whether a claim equal in BOTH name and value belongs to the set[a specific dot separator character — ask the PM for the exact string] Lines are emitted in the order queried (all `exists` lines first, then all `contains` lines)[a specific dot separator character — ask the PM for the exact string]

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_membership[a specific dot separator character — ask the PM for the exact string]json`

```json
{
    "description": "Given a claim set, report for each queried name whether a claim with that name is present, and for each queried name/value pair whether an equal claim belongs to the set[a specific dot separator character — ask the PM for the exact string] A pair matches only when both its name and its value match a member of the set[a specific dot separator character — ask the PM for the exact string]",
    "cases": [
        {"input": {"op": "payload_membership", "claims": [{"name": "sub", "value": 1}, {"name": "iss", "value": "http://example[a specific dot separator character — ask the PM for the exact string]com"}, {"name": "exp", "value": 3723}, {"name": "nbf", "value": 123}, {"name": "iat", "value": 123}, {"name": "jti", "value": "foo"}], "exists": ["iat", "exp", "aud"], "contains": [{"name": "sub", "value": 1}, {"name": "aud", "value": 1}]}, "expected_output": "exists[a specific dot separator character — ask the PM for the exact string]iat=true\nexists[a specific dot separator character — ask the PM for the exact string]exp=true\nexists[a specific dot separator character — ask the PM for the exact string]aud=false\ncontains[a specific dot separator character — ask the PM for the exact string]sub=true\ncontains[a specific dot separator character — ask the PM for the exact string]aud=false\n"}
    ]
}
```

*2[a specific dot separator character — ask the PM for the exact string]3 Read a claim value by its type*

With `op` = `payload_get_typed`, the `type` field names a well-known claim type and the matching claim's value is returned as `value=<json>`[a specific dot separator character — ask the PM for the exact string] Supported type names are `subject`, `issuer`, `expiration`, `not-before`, `issued-at`, `audience` and `jwt-id`, each corresponding to its standard claim[a specific dot separator character — ask the PM for the exact string] Requesting a type that is not present in the set is reported as `error=unknown_claim`[a specific dot separator character — ask the PM for the exact string]

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_get_by_type[a specific dot separator character — ask the PM for the exact string]json`

```json
{
    "description": "Each claim carries a well-known type (such as subject, issuer or token id)[a specific dot separator character — ask the PM for the exact string] A value can be fetched by naming the claim's type, returning the matching claim's value in its native JSON form[a specific dot separator character — ask the PM for the exact string] Naming a type that is not part of the claim set is an error[a specific dot separator character — ask the PM for the exact string]",
    "cases": [
        {"input": {"op": "payload_get_typed", "claims": [{"name": "sub", "value": 1}, {"name": "iss", "value": "http://example[a specific dot separator character — ask the PM for the exact string]com"}, {"name": "jti", "value": "foo"}], "type": "subject"}, "expected_output": "value=1\n"},
        {"input": {"op": "payload_get_typed", "claims": [{"name": "sub", "value": 1}], "type": "favourite"}, "expected_output": "error=unknown_claim\n"}
    ]
}
```

*2[a specific dot separator character — ask the PM for the exact string]4 Immutability — mutating operations are rejected*

With `op` = `payload_mutate`, the request asks to change the set: a `set` field `{"key", "value"}` requests assigning a value to a key, and an `unset` field (a key name) requests removing a key[a specific dot separator character — ask the PM for the exact string] Both are rejected: the set is immutable, so the operation produces `error=immutable` and leaves the set unchanged[a specific dot separator character — ask the PM for the exact string]

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_immutability[a specific dot separator character — ask the PM for the exact string]json`

```json
{
    "description": "A claim set is immutable[a specific dot separator character — ask the PM for the exact string] Any attempt to assign a value to a key or to remove a key is rejected with an immutability error and leaves the set unchanged[a specific dot separator character — ask the PM for the exact string]",
    "cases": [
        {"input": {"op": "payload_mutate", "claims": [{"name": "sub", "value": 1}], "set": {"key": "foo", "value": "bar"}}, "expected_output": "error=immutable\n"},
        {"input": {"op": "payload_mutate", "claims": [{"name": "sub", "value": 1}], "unset": "foo"}, "expected_output": "error=immutable\n"}
    ]
}
```

---

### Feature 3: Payload Validation

**As a developer**, I want a payload checked for completeness and freshness, so I can refuse incomplete or out-of-window payloads[a specific dot separator character — ask the PM for the exact string]

**Expected Behavior / Usage:**

With `op` = `validate_payload`, the `payload` field is a name-to-value mapping of claims and `now` is the reference current time as a Unix timestamp[a specific dot separator character — ask the PM for the exact string] When the payload passes all checks the result is `status=valid`[a specific dot separator character — ask the PM for the exact string]

*3[a specific dot separator character — ask the PM for the exact string]1 Structural validation — mandatory claims must be present*

The payload must contain all mandatory claims: issuer (`iss`), issued-at (`iat`), expiration (`exp`), not-before (`nbf`), subject (`sub`) and token id (`jti`)[a specific dot separator character — ask the PM for the exact string] A payload that contains every mandatory claim passes structural validation; a payload missing one or more of them is rejected with `error=token_invalid`[a specific dot separator character — ask the PM for the exact string]

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_structure[a specific dot separator character — ask the PM for the exact string]json`

```json
{
    "description": "Structural validation requires that all mandatory claims are present: issuer, issued-at, expiration, not-before, subject and token id[a specific dot separator character — ask the PM for the exact string] A set that contains every mandatory claim passes structural validation; a set missing one or more mandatory claims is rejected as invalid[a specific dot separator character — ask the PM for the exact string]",
    "cases": [
        {"input": {"op": "validate_payload", "now": 123, "payload": {"iss": "http://example[a specific dot separator character — ask the PM for the exact string]com", "iat": 100, "nbf": 100, "exp": 3700, "sub": 1, "jti": "foo"}}, "expected_output": "status=valid\n"},
        {"input": {"op": "validate_payload", "now": 123, "payload": {"iss": "http://example[a specific dot separator character — ask the PM for the exact string]com", "sub": 1}}, "expected_output": "error=token_invalid\n"}
    ]
}
```

*3[a specific dot separator character — ask the PM for the exact string]2 Time-window validation — expiration and future timestamps*

For a structurally complete payload, the temporal claims (Unix timestamps) are checked against `now`[a specific dot separator character — ask the PM for the exact string] If the expiration time is in the past, the payload is rejected with `error=token_expired`[a specific dot separator character — ask the PM for the exact string] If the not-before time is in the future, or the issued-at time is in the future, the payload is rejected with `error=token_invalid`[a specific dot separator character — ask the PM for the exact string]

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_timestamps[a specific dot separator character — ask the PM for the exact string]json`

```json
{
    "description": "Given a reference current time (a Unix timestamp) and a claim set whose temporal claims are Unix timestamps, validation enforces the time window: an expiration in the past rejects the set as expired, while a not-before time or an issued-at time in the future rejects the set as invalid[a specific dot separator character — ask the PM for the exact string]",
    "cases": [
        {"input": {"op": "validate_payload", "now": 123, "payload": {"iss": "http://example[a specific dot separator character — ask the PM for the exact string]com", "iat": 20, "nbf": 20, "exp": 120, "sub": 1, "jti": "foo"}}, "expected_output": "error=token_expired\n"},
        {"input": {"op": "validate_payload", "now": 123, "payload": {"iss": "http://example[a specific dot separator character — ask the PM for the exact string]com", "iat": 100, "nbf": 150, "exp": 3750, "sub": 1, "jti": "foo"}}, "expected_output": "error=token_invalid\n"}
    ]
}
```

---

### Feature 4: Assemble a Payload From Custom and Standard Claims

**As a developer**, I want to build a complete payload from just the claims I care about and have the standard claims filled in for me, so I don't have to assemble issuer/timestamps/id by hand every time[a specific dot separator character — ask the PM for the exact string]

**Expected Behavior / Usage:**

With `op` = `make_payload`, the `claims` map holds caller-supplied claims, `now` is the reference current time (Unix timestamp) and `url` is the issuer URL[a specific dot separator character — ask the PM for the exact string] Any standard claim the caller omits is generated automatically: issuer = the given `url`; issued-at and not-before = `now`; expiration = `now` plus the configured lifetime in minutes, where the lifetime defaults to 60 and may be overridden by an optional `ttl` field; and a token id derived deterministically from the subject and not-before values[a specific dot separator character — ask the PM for the exact string] The result is the assembled claim set rendered as a name-to-value mapping (native JSON form, with forward slashes escaped)[a specific dot separator character — ask the PM for the exact string] Caller-supplied claims keep their given values and appear first in the order supplied, followed by the generated standard claims[a specific dot separator character — ask the PM for the exact string]

**Test Cases:** `rcb_tests/public_test_cases/feature4_assemble[a specific dot separator character — ask the PM for the exact string]json`

```json
{
    "description": "Assemble a complete claim set from a map of caller-supplied claims plus automatically filled standard claims, evaluated against a reference current time and an issuer URL[a specific dot separator character — ask the PM for the exact string] Any standard claim the caller omits is generated: the issuer is the given URL, issued-at and not-before are the reference time, the expiration is the reference time plus the configured lifetime (in minutes, default sixty), and a token id is derived deterministically[a specific dot separator character — ask the PM for the exact string] The result is the assembled claim set as a name-to-value mapping in which caller-supplied claims keep their given values and ordering[a specific dot separator character — ask the PM for the exact string]",
    "cases": [
        {"input": {"op": "make_payload", "now": 123, "url": "http://example[a specific dot separator character — ask the PM for the exact string]com/foo", "claims": {"sub": 1, "jti": "foo", "iat": 123}}, "expected_output": "{\"sub\":1,\"jti\":\"foo\",\"iat\":123,\"iss\":\"http:\\/\\/example[a specific dot separator character — ask the PM for the exact string]com\\/foo\",\"exp\":3723,\"nbf\":123}\n"},
        {"input": {"op": "make_payload", "now": 123, "url": "http://example[a specific dot separator character — ask the PM for the exact string]com/foo", "claims": {"sub": 1, "foo": "baz"}}, "expected_output": "{\"sub\":1,\"foo\":\"baz\",\"iss\":\"http:\\/\\/example[a specific dot separator character — ask the PM for the exact string]com\\/foo\",\"iat\":123,\"exp\":3723,\"nbf\":123,\"jti\":\"d1f6bff329cfc64b2503d2fc3e259583\"}\n"}
    ]
}
```

---

## Deliverables

1[a specific dot separator character — ask the PM for the exact string] **The Core System:** A cleanly structured codebase implementing the features described above (claim modelling, an immutable claim-set container, structural and time-window validation, the claim-set builder, and the compact-token structure check)[a specific dot separator character — ask the PM for the exact string] Its physical structure MUST strictly align with the "Scale-Driven Code Organization" constraint[a specific dot separator character — ask the PM for the exact string] The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing[a specific dot separator character — ask the PM for the exact string]

2[a specific dot separator character — ask the PM for the exact string] **The Execution/Test Adapter:** A runnable program that acts as a client to your core system — logically (and ideally physically) separated from the core domain[a specific dot separator character — ask the PM for the exact string] It reads a single JSON request from stdin, dispatches on the `op` field (`validate_token`, `payload_get`, `payload_membership`, `payload_get_typed`, `payload_mutate`, `validate_payload`, `make_payload`), invokes the appropriate core logic, and prints the result (or a neutral `error=<category>` line) to stdout, matching the per-feature contracts above[a specific dot separator character — ask the PM for the exact string] Native errors raised by the core are translated into the neutral error categories in this adapter layer[a specific dot separator character — ask the PM for the exact string]

3[a specific dot separator character — ask the PM for the exact string] **Automated test harness**[a specific dot separator character — ask the PM for the exact string] The cases embedded in this PRD live under `rcb_tests/public_test_cases/`[a specific dot separator character — ask the PM for the exact string] A single entry point `bash rcb_tests/test[a specific dot separator character — ask the PM for the exact string]sh` reads every `*[a specific dot separator character — ask the PM for the exact string]json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`)[a specific dot separator character — ask the PM for the exact string] For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename[a specific dot separator character — ask the PM for the exact string]stem}@{case_index[a specific dot separator character — ask the PM for the exact string]zfill(3)}[a specific dot separator character — ask the PM for the exact string]txt`[a specific dot separator character — ask the PM for the exact string] Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other[a specific dot separator character — ask the PM for the exact string] Each `[a specific dot separator character — ask the PM for the exact string]txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`[a specific dot separator character — ask the PM for the exact string]
