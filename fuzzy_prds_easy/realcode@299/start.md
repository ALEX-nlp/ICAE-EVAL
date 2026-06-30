## Product Requirement Document

# Object Pool Configuration & Validity-Policy Toolkit — Durations, Age-Based Expiration, and Pool Settings

## Project Goal

Build a small, dependency-free toolkit that gives an object-pooling system its non-concurrent core building blocks: a unit-independent duration value, a family of age-based validity (expiration) policies that decide when a pooled item should be retired, and a configuration holder that captures a pool's target size and behavioral toggles. The goal is to let a pool implementation express "how long to wait", "when is a pooled item too old to reuse", and "how should the pool be set up" through clean, well-validated value objects, without re-deriving unit conversions or policy-composition logic in every call site.

---

## Background & Problem

A resource pool repeatedly has to answer a few small but error-prone questions. How long is the caller willing to wait? When converting that wait into the system clock's base unit, the math must be exact and independent of whichever unit the caller happened to use. When is a borrowed item stale enough to throw away and replace? That decision depends on the item's age and on a configurable policy. And how is the pool itself parameterized — its size and a couple of behavioral switches?

Without a shared toolkit, each of these gets hand-rolled, leading to subtle bugs: durations that compare unequal despite representing the same span, off-by-one age boundaries, validation that silently accepts nonsense bounds, and configuration objects whose defaults drift. This toolkit provides one well-defined contract for each piece: a duration value that is equal to any other duration of the same absolute length; age policies with precise boundary semantics and up-front validation of their parameters; a way to combine two policies; and a configuration holder with documented defaults.

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
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification. New validity policies should be addable without editing existing ones.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types; every validity policy must be usable wherever a policy is expected.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: Unit-Independent Duration Value

**As a developer**, I want a duration value built from a magnitude and a named time unit that can also report itself in the system's finest base unit, so I can express waiting periods once and convert them exactly when needed.

**Expected Behavior / Usage:**

The input is a request with action `duration`, carrying a numeric `value` (magnitude) and a `unit` (a named time unit such as `NANOSECONDS`, `MILLISECONDS`, `SECONDS`, `DAYS`). The duration reports four facts: its original `value` and `unit` unchanged, the system's base unit (which is always `NANOSECONDS`), and the magnitude re-expressed in that base unit via an exact conversion (`base_value`). The magnitude is unrestricted — it may be zero or negative, which conventionally means "no waiting at all" — and such values are accepted and round-tripped faithfully (a magnitude already given in the base unit is reproduced as-is, with no conversion artifact). The `unit`, however, is mandatory: if it is absent (null), construction is rejected and a neutral error line is emitted as `error=null_argument` followed by `param=unit`, each on its own line.

**Test Cases:** `rcb_tests/public_test_cases/feature1_duration_value.json`

```json
{
    "description": "Describe a duration value built from a numeric magnitude and a named time unit. The duration reports back its original magnitude and unit unchanged, plus the magnitude re-expressed in the system's finest base unit (nanoseconds) via an exact unit conversion. The magnitude may be zero or negative (meaning no waiting), which is accepted. If the time unit is absent (null), construction is rejected with a neutral null-argument error naming the unit parameter.",
    "cases": [
        {"input": {"action": "duration", "value": 13, "unit": "MILLISECONDS"}, "expected_output": "value=13\nunit=MILLISECONDS\nbase_unit=NANOSECONDS\nbase_value=13000000\n"},
        {"input": {"action": "duration", "value": 1, "unit": null}, "expected_output": "error=null_argument\nparam=unit\n"}
    ]
}
```

---

### Feature 2: Duration Equivalence & Hash Consistency

**As a developer**, I want two durations of the same absolute length to be treated as equal regardless of the units they were written in, so I can compare and key on durations safely.

**Expected Behavior / Usage:**

The input is a request with action `duration_compare`, carrying two durations `a` and `b`, each a `value`/`unit` pair. Two durations are equivalent if and only if they represent the same absolute span of time once both are converted to the common base unit; the units they were originally written in are irrelevant. The result reports `equal` (whether the two are equivalent) and `hash_equal` (whether their hashes agree). Equivalent durations must always agree on their hash. Durations of different absolute lengths are not equivalent.

**Test Cases:** `rcb_tests/public_test_cases/feature2_duration_equivalence.json`

```json
{
    "description": "Compare two duration values for equivalence and hash consistency. Two durations are equivalent when they represent the same absolute span of time after converting both to the common base unit, regardless of the units they were originally expressed in; equivalent durations must also share the same hash. Durations representing different absolute spans are not equivalent. Each input supplies two durations, each as a magnitude plus a named time unit, and the result reports whether they are equivalent and whether their hashes agree.",
    "cases": [
        {"input": {"action": "duration_compare", "a": {"value": 1, "unit": "SECONDS"}, "b": {"value": 1000, "unit": "MILLISECONDS"}}, "expected_output": "equal=true\nhash_equal=true\n"},
        {"input": {"action": "duration_compare", "a": {"value": 1, "unit": "SECONDS"}, "b": {"value": 2, "unit": "SECONDS"}}, "expected_output": "equal=false\nhash_equal=false\n"}
    ]
}
```

---

### Feature 3: Single-Threshold Age Validity Policy

**As a developer**, I want a policy that retires a pooled item once it is older than a fixed maximum age, so stale items are replaced after a clear cutoff.

**Expected Behavior / Usage:**

The input is a request with action `max_age`, carrying a `max_age` magnitude, a named `unit`, and the item's `age_millis` (age in milliseconds). The policy reports the maximum age in milliseconds (`max_age_millis`), echoes the `age_millis`, and reports whether the item has expired. The boundary is strict-greater: an item whose age is at or below the threshold is still valid (`expired=false`), and only an item strictly older than the threshold is expired (`expired=true`). The threshold magnitude must be at least one; a magnitude below one is rejected with `error=illegal_argument` / `param=max_age`. The `unit` is mandatory; an absent (null) unit is rejected with `error=null_argument` / `param=unit`. (Validation of the threshold is checked before the unit.)

**Test Cases:** `rcb_tests/public_test_cases/feature3_max_age_validity.json`

```json
{
    "description": "A single-threshold age validity policy: a pooled item is invalid once its age strictly exceeds a maximum permitted age. The policy is built from a maximum age magnitude plus a named time unit, and the maximum age is reported in milliseconds. Given an item's age in milliseconds, the policy reports whether the item has expired: ages at or below the threshold are valid (not expired), ages strictly above it are expired. The threshold magnitude must be at least one, otherwise construction is rejected with a neutral illegal-argument error naming the max-age parameter; if the time unit is absent (null), construction is rejected with a neutral null-argument error naming the unit parameter.",
    "cases": [
        {"input": {"action": "max_age", "max_age": 2, "unit": "MILLISECONDS", "age_millis": 1}, "expected_output": "max_age_millis=2\nage_millis=1\nexpired=false\n"},
        {"input": {"action": "max_age", "max_age": 0, "unit": "MILLISECONDS", "age_millis": 0}, "expected_output": "error=illegal_argument\nparam=max_age\n"}
    ]
}
```

---

### Feature 4: Windowed (Lower/Upper Bound) Age Validity Policy

**As a developer**, I want a policy with a lower and an upper age bound, where items stay valid below the lower bound and are always retired at or beyond the upper bound, so that retirements can be spread across a window instead of all happening at one instant.

**Expected Behavior / Usage:**

The input is a request with action `spread`, carrying a `lower` magnitude, an `upper` magnitude, a named `unit`, and the item's `age_millis`. The policy reports both bounds in milliseconds (`lower_millis`, `upper_millis`), echoes the `age_millis`, and reports `expired`. The two deterministic regions are contractually fixed: an item younger than the lower bound is never expired (`expired=false`), and an item whose age is at or beyond the upper bound is always expired (`expired=true`). (Between the bounds the verdict varies and is out of scope here.) The `lower` magnitude must be at least one; otherwise `error=illegal_argument` / `param=lower`. The `upper` magnitude must be strictly greater than `lower`; otherwise `error=illegal_argument` / `[invalid constraint range check]`. The `unit` is mandatory; an absent (null) unit yields `error=null_argument` / `param=unit`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_spread_validity.json`

```json
{
    "description": "A windowed age validity policy defined by a lower and an upper age bound. Items younger than the lower bound are never expired; items at or beyond the upper bound are always expired; between the two bounds the verdict varies. The policy is built from a lower magnitude, an upper magnitude and a named time unit, and both bounds are reported in milliseconds. Given an item's age in milliseconds, the policy reports whether the item has expired for the deterministic regions (below the lower bound, and at or above the upper bound). The lower bound must be at least one and the upper bound must be strictly greater than the lower bound, otherwise construction is rejected with a neutral illegal-argument error naming the offending bound; if the time unit is absent (null), construction is rejected with a neutral null-argument error naming the unit parameter.",
    "cases": [
        {"input": {"action": "spread", "lower": 1, "upper": 2, "unit": "SECONDS", "age_millis": 999}, "expected_output": "lower_millis=1000\nupper_millis=2000\nage_millis=999\nexpired=false\n"},
        {"input": {"action": "spread", "lower": 1, "upper": 2, "unit": null, "age_millis": 0}, "expected_output": "error=null_argument\nparam=unit\n"}
    ]
}
```

---

### Feature 5: Composite (Any-Expires) Validity Policy

**As a developer**, I want to combine two validity policies so that an item is retired if either policy considers it stale, so I can layer multiple expiration criteria together.

**Expected Behavior / Usage:**

The input is a request with action `composite`, carrying the fixed verdict of a `first` and a `second` underlying policy, each given as either `expired` or `fresh`. The composite applies OR semantics: the item is expired if either underlying policy reports it expired, and is valid only when both report it fresh. The result echoes both underlying verdicts and reports the combined outcome.

**Test Cases:** `rcb_tests/public_test_cases/feature5_composite_validity.json`

```json
{
    "description": "A composite validity policy that combines two underlying policies with OR semantics: an item is considered expired if either of the two underlying policies considers it expired, and only valid when both consider it valid. Each input fixes the verdict of the first and second underlying policy (each either expired or fresh), and the result reports both underlying verdicts together with the combined outcome.",
    "cases": [
        {"input": {"action": "composite", "first": "fresh", "second": "fresh"}, "expected_output": "first=fresh\nsecond=fresh\nexpired=false\n"},
        {"input": {"action": "composite", "first": "expired", "second": "fresh"}, "expected_output": "first=expired\nsecond=fresh\nexpired=true\n"}
    ]
}
```

---

### Feature 6: Pool Configuration Holder

**As a developer**, I want a configuration holder that captures the pool's target size and a couple of behavioral toggles with sensible defaults, so the pool can be parameterized through one clear object.

**Expected Behavior / Usage:**

The input is a request with action `config` and an `op`. A freshly-initialized holder has a target `size` of 10, has precise leak detection enabled, and has background expiration disabled. The `op` selects what to do: `defaults` reads the freshly-initialized holder; `set_size` sets the target size to the supplied integer `value`; `set_precise_leak_detection` sets the precise-leak-detection toggle to the supplied boolean `value`; `set_background_expiration` sets the background-expiration toggle to the supplied boolean `value`. After the operation, the result reports the full configuration snapshot — `size`, `precise_leak_detection`, and `background_expiration` — so the targeted field reflects the change while untouched fields keep their defaults.

**Test Cases:** `rcb_tests/public_test_cases/feature6_pool_configuration.json`

```json
{
    "description": "The pool configuration holder exposes a target pool size plus two boolean toggles: precise leak detection (enabled by default) and background expiration (disabled by default). Each input names an operation: either reading the freshly-initialized defaults, or applying a single setter (set the size, toggle precise leak detection, or toggle background expiration). The result reports the full configuration snapshot after the operation, so that the targeted field reflects the change while the untouched fields retain their default values.",
    "cases": [
        {"input": {"action": "config", "op": "defaults"}, "expected_output": "size=10\nprecise_leak_detection=true\nbackground_expiration=false\n"},
        {"input": {"action": "config", "op": "set_size", "value": 123}, "expected_output": "size=123\nprecise_leak_detection=true\nbackground_expiration=false\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above: a unit-independent duration value type, a family of age-based validity policies (single-threshold, windowed lower/upper-bound, and a composite combinator) behind a common policy abstraction, and a pool configuration holder with documented defaults. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, dispatches on `action`, invokes the appropriate core logic, and prints the resulting snapshot (or a neutral error) to stdout, matching the per-feature contracts above. All invalid-argument conditions must be rendered as neutral category lines (`error=null_argument` / `error=illegal_argument` with a `param=<name>` line) and must NOT leak any host-language runtime exception identity. Named time units include at least `NANOSECONDS`, `MILLISECONDS`, `SECONDS`, and `DAYS`; the base unit is always `NANOSECONDS`.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- refer to the standard duration conversion rate defined in utils/constants.js
- compare durations using the same hashing algorithm as in the time_utils module
