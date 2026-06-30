## Product Requirement Document

# Quota-Based Rate Limiter — Deterministic Admission Control over a Virtual Clock

## Project Goal

Build a reusable rate-limiting library that decides, at any moment, whether an incoming unit of work may proceed under a configured budget, so developers can throttle traffic to a fixed average rate while still tolerating short bursts — all without hand-rolling token accounting or timing logic. To make decisions reproducible and testable, the library's notion of "now" is supplied by an injectable clock; a virtual clock that only advances when explicitly told lets callers exercise every timing edge deterministically.

---

## Background & Problem

Without a shared rate limiter, developers re-implement the same fragile token bookkeeping in every service: counters that must be decremented and refilled, timestamps that must be compared, and off-by-one errors at the moment budget runs out. This leads to throttling that is either too strict (rejecting traffic that should pass) or too loose (allowing spikes that overwhelm a downstream), and to code that is impossible to test because it depends on wall-clock time.

With this library, a developer expresses an allowance as a **quota** (how many units per unit of time, plus how large a one-time burst may be), constructs a limiter over that quota, and simply asks the limiter to admit each unit. The limiter answers yes or no and, on a no, says exactly how long to wait. Because the limiter reads time from an injected clock, the same logic that runs against the real clock in production can be driven against a virtual clock in tests, producing byte-for-byte reproducible decisions.

The underlying algorithm is a continuous token-bucket / virtual-scheduling scheme: instead of storing a discrete token count, the limiter stores a single "theoretical arrival time" and derives the admit/reject decision (and the exact wait) from the gap between that time and the current clock reading. Each admitted unit pushes the theoretical arrival time forward by one replenishment interval; the burst allowance is the maximum amount the clock may lag behind that time.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., quota math, the core decision engine, per-key storage, time sources), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls to the core domain. In particular, the time source MUST be an injectable abstraction so a deterministic virtual clock can be substituted for the real one.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate quota definition, the decision engine, per-key state storage, the time source, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core decision engine must be open for extension (e.g. swapping what extra information a decision returns) but closed for modification.
   - **Liskov Substitution Principle (LSP):** Any conforming time source or state store must be perfectly substitutable.
   - **Interface Segregation Principle (ISP):** Keep abstractions (time source, state store) small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level decision logic should depend on abstractions (a clock, a store), not on concrete I/O.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface must be elegant and idiomatic to the target language, hiding internal time bookkeeping.
   - **Resilience:** The system must handle edge cases gracefully — a zero replenishment period, a batch larger than the burst capacity, draining and replenishment at exact boundaries — modeling failures explicitly rather than via generic faults.

---

## Core Features

The execution adapter reads ONE JSON request from stdin and prints raw text to stdout. The request's `action` selects behavior:

- `quota_info` — build a quota from `quota` and report its derived properties.
- `quota_build` — attempt to build a quota from `spec`, reporting either its properties or a neutral rejection.
- `simulate` — build a limiter over `quota` (optionally `limiter: "keyed"` and/or `middleware: "state"`) and run an ordered list of `ops` against a virtual clock that starts at zero, printing one line per op.

A **quota spec** is one of: `{"per_second": N}`, `{"per_minute": N}`, `{"per_hour": N}`, `{"with_period_ms": N}` (replenish one unit every N ms), or `{"new": {"burst": B, "all_per_ms": T}}` (replenish a burst of B over T ms); any of these may carry an optional `"allow_burst": M` that overrides the maximum burst. Durations in all output are reported in **nanoseconds**.

The `simulate` op vocabulary and their one-line outputs: `{"check": {}}` → `check allow` (or `check allow remaining=<n>` under the state-reporting mode) / `check deny wait_ns=<n>`; `{"check_n": N}` → the same with an `check_n n=<N> ...` prefix, plus `check_n n=<N> error=insufficient_capacity max=<m>` when the batch can never fit; `{"check_key": "K"}` and `{"check_key_n": {"key":"K","n":N}}` → keyed equivalents prefixed `check_key key=<K> ...`; `{"advance_ms": N}` → `advance now_ns=<total>`; `{"retain_recent": {}}` → `retain_recent ok`; `{"shrink_to_fit": {}}` → `shrink_to_fit ok`; `{"len": {}}` → `len count=<n> empty=<bool>`; `{"keys": {}}` → `keys <comma-separated-sorted>`.

---

### Feature 1: Quota Definition & Derived Properties

**As a developer**, I want to express an allowance as a quota and read back its derived timing properties, so I can reason about throughput, burst, and replenishment time before wiring up any limiter.

**Expected Behavior / Usage:**

*1.1 Time-based construction — equivalent rates across time bases*

A quota built from a count against a fixed time base (per second, per minute, or per hour) exposes three derived properties: the **replenish interval** (time to restore one consumed unit), the **burst size** (units admissible back-to-back from full before any replenishment is required; equal to the supplied count for these constructors), and the **full-burst replenish time** (time to restore an entirely drained burst). Equivalent average rates expressed against different bases produce proportional replenish intervals: the per-hour interval is sixty times the per-minute interval, which is sixty times the per-second interval. All durations are in nanoseconds.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_time_based_quota.json`

```json
{
    "description": "Construct a rate-limiting quota from a human-friendly rate expressed against a fixed time base (a count of allowed units per second, per minute, or per hour). For each construction the system reports three derived properties: the time interval after which a single consumed unit is replenished, the maximum burst (the count of units that may be consumed back-to-back before any replenishment is required), and the total time required to replenish a fully-drained burst budget. Equivalent rates expressed against different time bases yield proportional replenishment intervals (an hourly base divides into the minutely base by sixty, which divides into the per-second base by sixty). Durations are reported in nanoseconds.",
    "cases": [
        {"input": {"action": "quota_info", "quota": {"per_minute": 1}}, "expected_output": "replenish_interval_ns=60000000000\n[dynamic state variable based on formula involving burst and age]=1\nburst_replenish_all_ns=60000000000\n"},
        {"input": {"action": "quota_info", "quota": {"per_second": 50}}, "expected_output": "replenish_interval_ns=20000000\n[dynamic state variable based on formula involving burst and age]=50\nburst_replenish_all_ns=1000000000\n"}
    ]
}
```

*1.2 Independent burst sizing*

The maximum burst can be raised independently of the average rate, decoupling "how fast on average" from "how big a single spike". Overriding the burst leaves the per-unit replenish interval unchanged but scales the full-burst replenish time in proportion to the larger burst.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_burst_capacity.json`

```json
{
    "description": "Start from a rate expressed against a time base and then independently raise the maximum burst budget to a larger value, decoupling the long-run average rate from the amount that may be consumed in a single spike. The reported maximum burst reflects the overridden value, the per-unit replenishment interval is unchanged from the base rate, and the time to replenish a fully-drained burst grows in proportion to the larger burst. Durations are reported in nanoseconds.",
    "cases": [
        {"input": {"action": "quota_info", "quota": {"per_hour": 2, "allow_burst": 90}}, "expected_output": "replenish_interval_ns=1800000000000\n[dynamic state variable based on formula involving burst and age]=90\nburst_replenish_all_ns=162000000000000\n"}
    ]
}
```

*1.3 Custom replenishment period and rejection of degenerate input*

A quota may instead be built directly from a replenishment period (the time to restore one unit), optionally with a raised burst. A strictly positive period yields a valid quota whose properties follow the same rules. A zero period — directly, or as a zero total replenishment time accompanying a burst — cannot describe a meaningful rate and is rejected; rejection is reported as a single neutral error category line rather than a quota.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_custom_period.json`

```json
{
    "description": "Construct a quota directly from a replenishment period (the time to restore one unit) instead of a named time base, optionally raising the maximum burst. A strictly positive period yields a valid quota whose reported properties follow the same rules as time-based quotas. A zero period cannot describe a meaningful rate and is rejected; the equivalent rejection occurs when supplying a burst together with a zero total replenishment time. A rejected construction reports a single neutral error category line rather than a quota.",
    "cases": [
        {"input": {"action": "quota_build", "spec": {"with_period_ms": 86400000, "allow_burst": 10}}, "expected_output": "replenish_interval_ns=86400000000000\n[dynamic state variable based on formula involving burst and age]=10\nburst_replenish_all_ns=864000000000000\n"},
        {"input": {"action": "quota_build", "spec": {"with_period_ms": 0}}, "expected_output": "error=invalid_period\n"}
    ]
}
```

---

### Feature 2: Single-Unit Admission Control

**As a developer**, I want to ask a limiter to admit one unit at a time and be told exactly when to retry on a rejection, so I can pace work precisely against a budget.

**Expected Behavior / Usage:**

*2.1 Admit, drain, and replenish over time*

A fresh limiter admits the first request. While burst budget remains, requests are admitted; once it is drained, a request is rejected and reports the wait (nanoseconds) until the next admission becomes possible. Advancing the virtual clock far enough restores budget so admissions resume, and the cycle repeats once the restored budget is consumed. Each clock advance reports the new absolute virtual time in nanoseconds.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_single_cell.json`

```json
{
    "description": "Drive a single global rate limiter against a virtual clock and submit single-unit admission requests interleaved with explicit clock advances. The limiter admits requests while burst budget remains, then rejects further requests until enough time passes to replenish budget. A fresh limiter admits the very first request. Once the burst budget is drained a request is rejected and reports the wait time (in nanoseconds) until the next admission is possible; after enough time elapses the burst is restored and requests are admitted again, then rejected once the restored budget is consumed. Each clock advance reports the new absolute virtual time in nanoseconds.",
    "cases": [
        {"input": {"action": "simulate", "quota": {"per_second": 5}, "ops": [{"check": {}}]}, "expected_output": "check allow\n"},
        {"input": {"action": "simulate", "quota": {"per_second": 2}, "ops": [{"check": {}}, {"advance_ms": 1}, {"check": {}}, {"advance_ms": 1}, {"check": {}}, {"advance_ms": 1000}, {"check": {}}, {"advance_ms": 1}, {"check": {}}, {"advance_ms": 1}, {"check": {}}]}, "expected_output": "check allow\nadvance now_ns=1000000\ncheck allow\nadvance now_ns=2000000\ncheck deny wait_ns=498000000\nadvance now_ns=1002000000\ncheck allow\nadvance now_ns=1003000000\ncheck allow\nadvance now_ns=1004000000\ncheck deny wait_ns=496000000\n"}
    ]
}
```

*2.2 Exact reported wait time*

The wait reported on a rejection is exact: advancing the clock by precisely that wait makes the next request succeed, while advancing by strictly less leaves the limiter rejecting and reports the smaller remaining wait. Waits and clock readings are in nanoseconds.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_wait_time.json`

```json
{
    "description": "Verify that the wait time reported on a rejected admission is exact. After draining the burst budget, a further request is rejected and reports the precise remaining wait time. Advancing the virtual clock by exactly that reported wait time makes the next request succeed. Advancing by strictly less than the reported wait time leaves the limiter still rejecting, and the new rejection reports the smaller remaining wait. Wait times and absolute clock readings are reported in nanoseconds.",
    "cases": [
        {"input": {"action": "simulate", "quota": {"per_second": 5}, "ops": [{"check": {}}, {"check": {}}, {"check": {}}, {"check": {}}, {"check": {}}, {"check": {}}, {"advance_ms": 200}, {"check": {}}]}, "expected_output": "check allow\ncheck allow\ncheck allow\ncheck allow\ncheck allow\ncheck deny wait_ns=200000000\nadvance now_ns=200000000\ncheck allow\n"},
        {"input": {"action": "simulate", "quota": {"per_second": 5}, "ops": [{"check": {}}, {"check": {}}, {"check": {}}, {"check": {}}, {"check": {}}, {"check": {}}, {"advance_ms": 199}, {"check": {}}]}, "expected_output": "check allow\ncheck allow\ncheck allow\ncheck allow\ncheck allow\ncheck deny wait_ns=200000000\nadvance now_ns=199000000\ncheck deny wait_ns=1000000\n"}
    ]
}
```

---

### Feature 3: Batched (Multi-Unit) Admission Control

**As a developer**, I want to admit several units atomically in one decision, so I can account for variable-cost operations and reject impossible requests up front.

**Expected Behavior / Usage:**

*3.1 All-or-nothing batches*

A batch requests a specific number of units admitted together. A batch of one behaves identically to a single-unit request. A batch is admitted only if the whole batch fits within currently available budget; otherwise it is rejected and reports the wait (nanoseconds) until the entire batch could be admitted. Budget replenishes over time exactly as for single units.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_batch_check.json`

```json
{
    "description": "Submit batched admission requests that ask to admit a specific number of units atomically (all-or-nothing). A batch of one behaves identically to a single-unit request. A batch is admitted only if the whole batch fits within the currently available budget; otherwise the batch is rejected and reports the wait time (in nanoseconds) until the whole batch could be admitted. Over time the budget replenishes and previously rejected batches become admissible, then are rejected again once the restored budget is consumed. Each clock advance reports the new absolute virtual time in nanoseconds.",
    "cases": [
        {"input": {"action": "simulate", "quota": {"per_second": 2}, "ops": [{"check_n": 1}, {"advance_ms": 1}, {"check_n": 1}, {"advance_ms": 1}, {"check_n": 1}, {"advance_ms": 1000}, {"check_n": 1}, {"advance_ms": 1}, {"check_n": 1}, {"advance_ms": 1}, {"check_n": 1}]}, "expected_output": "check_n n=1 allow\nadvance now_ns=1000000\ncheck_n n=1 allow\nadvance now_ns=2000000\ncheck_n n=1 deny wait_ns=498000000\nadvance now_ns=1002000000\ncheck_n n=1 allow\nadvance now_ns=1003000000\ncheck_n n=1 allow\nadvance now_ns=1004000000\ncheck_n n=1 deny wait_ns=496000000\n"},
        {"input": {"action": "simulate", "quota": {"per_second": 4}, "ops": [{"check_n": 2}, {"check_n": 2}, {"advance_ms": 1}, {"check_n": 2}, {"advance_ms": 1000}, {"check_n": 2}, {"advance_ms": 1}, {"check_n": 2}, {"advance_ms": 1}, {"check_n": 2}]}, "expected_output": "check_n n=2 allow\ncheck_n n=2 allow\nadvance now_ns=1000000\ncheck_n n=2 deny wait_ns=499000000\nadvance now_ns=1001000000\ncheck_n n=2 allow\nadvance now_ns=1002000000\ncheck_n n=2 allow\nadvance now_ns=1003000000\ncheck_n n=2 deny wait_ns=497000000\n"}
    ]
}
```

*3.2 Batches larger than capacity are impossible*

A batch larger than the maximum burst can never be admitted, no matter how much time passes. This is reported as a distinct neutral error category along with the largest batch size that could ever conform, and is independent of the clock.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_insufficient_capacity.json`

```json
{
    "description": "Submit batched admission requests whose size exceeds the limiter's maximum burst capacity. Such a batch can never be admitted, regardless of how much time has elapsed, because it is larger than the most the limiter could ever hold at once. The limiter reports a distinct neutral error category indicating insufficient capacity, together with the maximum batch size that could ever conform. This outcome is independent of the virtual clock: advancing time does not make an over-capacity batch admissible.",
    "cases": [
        {"input": {"action": "simulate", "quota": {"per_second": 5}, "ops": [{"check_n": 15}, {"check_n": 6}, {"check_n": 7}]}, "expected_output": "check_n n=15 error=insufficient_capacity max=5\ncheck_n n=6 error=insufficient_capacity max=5\ncheck_n n=7 error=insufficient_capacity max=5\n"}
    ]
}
```

---

### Feature 4: Keyed Rate Limiting (One Budget Per Key)

**As a developer**, I want one quota applied independently per key, so I can enforce, say, a separate budget per client identifier, and reclaim memory for keys that have gone idle.

**Expected Behavior / Usage:**

*4.1 Per-key independence*

Each distinct key carries its own budget under one shared quota; one key's decisions never consume another key's budget. A fresh limiter admits the first request for every key. Draining one key's burst rejects that key's further requests (reporting a wait) and later re-admits as its budget replenishes, while a different key seen for the first time still receives its full burst regardless of how far the clock has advanced.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_per_key.json`

```json
{
    "description": "Drive a keyed rate limiter against a virtual clock, where each distinct key carries its own independent budget under one shared quota. Admission decisions for one key never consume another key's budget. A fresh limiter admits the first request for every key. Draining one key's burst causes that key's subsequent requests to be rejected (with a reported wait time in nanoseconds) and later re-admitted as time replenishes its budget, while a different key, seen for the first time, still receives its full burst regardless of how much the clock has advanced. Each clock advance reports the new absolute virtual time in nanoseconds.",
    "cases": [
        {"input": {"action": "simulate", "limiter": "keyed", "quota": {"per_second": 5}, "ops": [{"check_key": "alpha"}, {"check_key": "beta"}]}, "expected_output": "check_key key=alpha allow\ncheck_key key=beta allow\n"},
        {"input": {"action": "simulate", "limiter": "keyed", "quota": {"per_second": 2}, "ops": [{"check_key": "alpha"}, {"advance_ms": 1}, {"check_key": "alpha"}, {"advance_ms": 1}, {"check_key": "alpha"}, {"advance_ms": 1000}, {"check_key": "alpha"}, {"advance_ms": 1}, {"check_key": "alpha"}, {"advance_ms": 1}, {"check_key": "alpha"}, {"check_key": "beta"}, {"advance_ms": 1}, {"check_key": "beta"}, {"advance_ms": 1}, {"check_key": "beta"}]}, "expected_output": "check_key key=alpha allow\nadvance now_ns=1000000\ncheck_key key=alpha allow\nadvance now_ns=2000000\ncheck_key key=alpha deny wait_ns=498000000\nadvance now_ns=1002000000\ncheck_key key=alpha allow\nadvance now_ns=1003000000\ncheck_key key=alpha allow\nadvance now_ns=1004000000\ncheck_key key=alpha deny wait_ns=496000000\ncheck_key key=beta allow\nadvance now_ns=1005000000\ncheck_key key=beta allow\nadvance now_ns=1006000000\ncheck_key key=beta deny wait_ns=498000000\n"}
    ]
}
```

*4.2 Live key count*

The limiter reports how many distinct keys it is currently tracking. A newly created limiter holds none and reports empty; each first-time admission under a new key adds exactly one tracked key and flips the empty flag false.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_key_count.json`

```json
{
    "description": "Track how many distinct keys the keyed limiter is currently holding state for. A newly created limiter holds no keys and reports as empty. Each first-time admission request under a new key adds exactly one tracked key; repeated reporting shows the live key count growing by one per newly seen key and the empty flag turning false once at least one key is present.",
    "cases": [
        {"input": {"action": "simulate", "limiter": "keyed", "quota": {"per_second": 1}, "ops": [{"len": {}}, {"check_key": "foo"}, {"len": {}}, {"check_key": "bar"}, {"len": {}}, {"check_key": "baz"}, {"len": {}}]}, "expected_output": "len count=0 empty=true\ncheck_key key=foo allow\nlen count=1 empty=false\ncheck_key key=bar allow\nlen count=2 empty=false\ncheck_key key=baz allow\nlen count=3 empty=false\n"}
    ]
}
```

*4.3 Reclaiming idle keys*

A reclamation pass evicts keys whose state has become indistinguishable from a never-seen key — i.e. whose budget has fully replenished back to the starting state. Keys admitted at staggered times survive while still "fresh"; advancing the clock further drops them out oldest-first until none remain. After reclamation the surviving keys are reported in sorted order.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_retain_recent.json`

```json
{
    "description": "Reclaim memory in a keyed limiter by evicting keys whose state has become indistinguishable from a never-seen key. Three keys are admitted at staggered virtual times, then the clock is advanced by a varying amount before a reclamation pass is requested; a key is retained only while its state remains fresher than a brand-new key would be (i.e. its budget has not fully replenished back to the starting state). After reclamation, the surviving keys are reported in sorted order. With no extra advance all keys survive; as the clock advances further, keys drop out oldest-first until none remain.",
    "cases": [
        {"input": {"action": "simulate", "limiter": "keyed", "quota": {"per_second": 1}, "ops": [{"check_key": "foo"}, {"advance_ms": 200}, {"check_key": "bar"}, {"advance_ms": 600}, {"check_key": "baz"}, {"retain_recent": {}}, {"keys": {}}]}, "expected_output": "check_key key=foo allow\nadvance now_ns=200000000\ncheck_key key=bar allow\nadvance now_ns=800000000\ncheck_key key=baz allow\nretain_recent ok\nkeys bar,baz,foo\n"},
        {"input": {"action": "simulate", "limiter": "keyed", "quota": {"per_second": 1}, "ops": [{"check_key": "foo"}, {"advance_ms": 200}, {"check_key": "bar"}, {"advance_ms": 600}, {"check_key": "baz"}, {"advance_ms": 1200}, {"retain_recent": {}}, {"keys": {}}]}, "expected_output": "check_key key=foo allow\nadvance now_ns=200000000\ncheck_key key=bar allow\nadvance now_ns=800000000\ncheck_key key=baz allow\nadvance now_ns=2000000000\nretain_recent ok\nkeys bar,baz\n"}
    ]
}
```

*4.4 Compacting storage after reclamation*

After idle keys are evicted, a compaction request shrinks internal storage while keeping the genuinely active keys. A long-lived key whose large batch keeps its state fresh survives a reclamation-plus-compaction even after a short-lived key has lapsed, leaving a live key count of one.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_shrink_to_fit.json`

```json
{
    "description": "Compact the keyed limiter's internal storage after stale keys are evicted, keeping only the genuinely active keys. A long-lived key consumes a large batch (keeping its state fresh well into the future) while a short-lived key is admitted once. After the clock advances far enough that the short-lived key's state lapses, a reclamation pass followed by a storage-compaction request leaves only the long-lived key, and the reported live key count is one.",
    "cases": [
        {"input": {"action": "simulate", "limiter": "keyed", "quota": {"per_second": 20}, "ops": [{"check_key_n": {"key": "long-lived", "n": 10}}, {"check_key": "short-lived"}, {"advance_ms": 300}, {"retain_recent": {}}, {"shrink_to_fit": {}}, {"len": {}}]}, "expected_output": "check_key_n key=long-lived n=10 allow\ncheck_key key=short-lived allow\nadvance now_ns=300000000\nretain_recent ok\nshrink_to_fit ok\nlen count=1 empty=false\n"}
    ]
}
```

---

### Feature 5: State-Reporting Decisions

**As a developer**, I want each admitted decision to optionally carry how much burst capacity remains, so I can surface budget headroom (e.g. as response metadata) without a second query.

**Expected Behavior / Usage:**

*5.1 Remaining burst capacity on each admission*

Under the state-reporting mode, each admission additionally reports the remaining burst capacity — how many further units could still be admitted right now without any replenishment. Starting from a full burst, successive admissions decrease the reported remaining value by one down to zero; the next request is rejected and reports the wait (nanoseconds) until capacity returns.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_remaining_capacity.json`

```json
{
    "description": "Use a state-reporting mode in which every admitted request additionally reveals the remaining burst capacity (how many further units could still be admitted right now without replenishment). Starting from a full burst, each successive admission decreases the reported remaining capacity by one down to zero; the next request is rejected and reports the wait time (in nanoseconds) until capacity is available again.",
    "cases": [
        {"input": {"action": "simulate", "middleware": "state", "quota": {"per_second": 4}, "ops": [{"check": {}}, {"check": {}}, {"check": {}}, {"check": {}}, {"check": {}}]}, "expected_output": "check allow remaining=3\ncheck allow remaining=2\ncheck allow remaining=1\ncheck allow remaining=0\ncheck deny wait_ns=250000000\n"}
    ]
}
```

*5.2 Accurate replenishment of reported capacity*

The reported remaining capacity replenishes accurately over time, including for a quota built from a custom period and explicit burst. After draining to zero and being rejected, advancing the clock well beyond a full replenishment window restores the reported capacity to the full burst, which then decreases by one per admission again.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_replenishment.json`

```json
{
    "description": "Use the state-reporting mode to observe that remaining burst capacity replenishes accurately over time for a quota built from a custom replenishment period and an explicit burst. Admissions decrease the reported remaining capacity to zero and then are rejected (reporting the wait time in nanoseconds). After advancing the virtual clock well beyond a full replenishment window, the reported remaining capacity is fully restored to the burst size and again decreases by one per admission down to zero before the next request is rejected.",
    "cases": [
        {"input": {"action": "simulate", "middleware": "state", "quota": {"with_period_ms": 90, "allow_burst": 2}, "ops": [{"check": {}}, {"check": {}}, {"check": {}}, {"advance_ms": 120000}, {"check": {}}, {"check": {}}, {"check": {}}, {"check": {}}]}, "expected_output": "check allow remaining=1\ncheck allow remaining=0\ncheck deny wait_ns=90000000\nadvance now_ns=120000000000\ncheck allow remaining=2\ncheck allow remaining=1\ncheck allow remaining=0\ncheck deny wait_ns=90000000\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above — quota definition and math, the continuous token-bucket decision engine, direct and per-key state storage with reclamation, an injectable time source (including a virtual clock that advances only on demand), and an optional state-reporting decision mode. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint, and the core logic must be decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program that reads a single JSON request from stdin and prints raw text to stdout, matching the per-feature contracts above. It builds quotas and limiters from the request and drives them against a virtual clock, translating each op into a call to the core domain and rendering one output line per op. Any core-level failure (e.g. an invalid quota period, an over-capacity batch) MUST be rendered as a neutral, language-independent line (`error=<category>` with parameters in separate fields) — never leaking host runtime type names or messages.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- refer to the denial wait table for nanosecond granularity
- consult the global scheduler config for burst cap defaults
