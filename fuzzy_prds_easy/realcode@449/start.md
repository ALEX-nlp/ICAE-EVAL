## Product Requirement Document

# Retry Scheduling & Eligibility Engine — Exponential Back-off Timing and Retry-Decision Rules for Failed Executions

## Project Goal

Build a small, deterministic retry-scheduling engine that, given a retry policy and the current state of a failed execution, computes *when* the next attempt should happen and decides *whether* another attempt is allowed, so that systems recovering from transient failures can schedule retries consistently without each component re-deriving its own back-off math and eligibility rules.

---

## Background & Problem

When an operation fails and is eligible to be retried, two questions must be answered the same way everywhere: how long to wait before the next attempt, and whether the operation is still allowed to be retried at all. Hand-rolling this logic per call site leads to inconsistent back-off curves, off-by-one mistakes in attempt counting, and retry storms when the "should I retry now?" check disagrees across components.

This engine centralizes that logic. It exposes a pure exponential back-off calculation (how the wait grows with each attempt), a way to assemble a full retry-state snapshot (attempt count, timeout deadline, next-attempt time point) from a policy, and a set of eligibility decisions (is the record retry-able at all, can it be retried given its lifecycle status, and is it due to be retried right now). All time points are expressed in epoch milliseconds and all durations in the policy are expressed in seconds.

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

### Feature 1: Exponential Back-off Next-Retry Time Point

**As a developer**, I want the next-retry time point computed by an exponential back-off rule, so each successive attempt waits progressively longer and retries spread out automatically.

**Expected Behavior / Usage:**

The input is a request that supplies a base back-off interval (`minBackoff`, in seconds), the number of attempts already made (`retries`, zero-based), and a reference time point (`currentRetryAt`, in epoch milliseconds). The engine returns the next-retry time point as `currentRetryAt + minBackoff × 2^retries × 1000`, i.e. the reference time plus the base interval (converted from seconds to milliseconds) scaled by two raised to the power of the attempt count. With a reference time of zero, the result equals the base interval in milliseconds for the first attempt (`retries = 0`) and doubles for each subsequent attempt. The output is a single line reporting the computed time point as `[a specific sentinel value — ask the PM for the exact string]<value>` followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_next_retry_at.json`

```json
{
    "description": "Compute the absolute time point of the next retry attempt using exponential back-off. Given a base back-off interval (in seconds), the number of attempts already made, and a reference time point (in epoch milliseconds), the next-retry time point is the reference time plus the base interval scaled by two raised to the power of the attempt count, expressed in milliseconds. With a reference time of zero, the result therefore equals the base interval in milliseconds for the first attempt and doubles with every subsequent attempt.",
    "cases": [
        {
            "input": {"action": "next_retry_at", "minBackoff": 180, "retries": 0, "currentRetryAt": 0},
            "expected_output": "[a specific sentinel value — ask the PM for the exact string]180000\n"
        },
        {
            "input": {"action": "next_retry_at", "minBackoff": 180, "retries": 1, "currentRetryAt": 0},
            "expected_output": "[a specific sentinel value — ask the PM for the exact string]360000\n"
        }
    ]
}
```

---

### Feature 2: Retry-State Snapshot From A Policy

**As a developer**, I want a single snapshot that bundles the attempt count, the timeout deadline, and the next-retry time point derived from a retry policy, so downstream scheduling has every timing value it needs in one consistent object.

**Expected Behavior / Usage:**

The input is a request that supplies a retry policy — a maximum retry count (`maxRetries`), a base back-off interval (`minBackoff`, seconds) and an execution-timeout (`executionTimeout`, seconds) — together with the attempt count (`retries`) and a reference time point (`retryAt`, epoch milliseconds). The engine produces a snapshot with four values: the attempt count echoed back unchanged; the reference time point echoed back unchanged; the timeout deadline, computed as `retryAt + executionTimeout × 1000`; and the next-retry time point, computed by the same exponential back-off rule as Feature 1 (`retryAt + minBackoff × 2^retries × 1000`). The output is four lines, in order: `retries=<n>`, `retryAt=<value>`, `[a specific sentinel value — ask the PM for the exact string]<value>`, `[a specific sentinel value — ask the PM for the exact string]<value>`, each followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature2_next_retry_state.json`

```json
{
    "description": "Build a complete retry-state snapshot from a retry policy, an attempt count, and a reference time point (epoch milliseconds). The policy supplies a maximum retry count, a base back-off interval in seconds, and an execution-timeout in seconds. The resulting snapshot reports: the attempt count as given; the reference time point as given; the timeout deadline, computed as the reference time plus the execution-timeout converted to milliseconds; and the next-retry time point, computed by the exponential back-off rule (reference time plus base interval times two-to-the-power-of-attempts, in milliseconds).",
    "cases": [
        {
            "input": {"action": "next_retry_state", "maxRetries": 10, "minBackoff": 180, "executionTimeout": 120, "retries": 1, "retryAt": 0},
            "expected_output": "retries=1\nretryAt=0\n[a specific sentinel value — ask the PM for the exact string]120000\n[a specific sentinel value — ask the PM for the exact string]360000\n"
        }
    ]
}
```

---

### Feature 3: Retry-Eligibility Decisions

**As a developer**, I want the engine to decide whether a failed-execution record may be retried and whether it is due right now, so the scheduler enforces lifecycle and timing rules uniformly instead of each caller guessing.

**Expected Behavior / Usage:**

The input is a request describing a failed-execution record: its lifecycle `status` (one of `FAILED`, `PREPARED`, `SUCCEEDED`), its retry-state snapshot fields (`retries`, plus `timoutAt` and `nextRetryAt` as epoch-millisecond time points) and its policy's maximum retry count (`maxRetries`). The engine reports three boolean decisions, each on its own line:

- `isRetryable` is true exactly when the attempt count is strictly below the maximum (`retries < maxRetries`).
- `canRetry` is true only when `isRetryable` holds AND the lifecycle status permits another attempt: a `FAILED` status permits it; a `SUCCEEDED` status never permits it; a `PREPARED` status permits it only once its timeout deadline (`timoutAt`) has elapsed relative to the current wall-clock time (i.e. now is past `timoutAt`).
- `shouldToRetry` is true only when `canRetry` holds AND the current wall-clock time has reached the next-retry time point (`nextRetryAt`).

Because the last two decisions compare against the live wall-clock, a `timoutAt` or `nextRetryAt` set far in the future evaluates as not-yet-timed-out and not-yet-due respectively. The output is three lines, in order: `isRetryable=<bool>`, `canRetry=<bool>`, `shouldToRetry=<bool>`, each followed by a newline, where `<bool>` is the lowercase word `true` or `false`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_retry_decision.json`

```json
{
    "description": "Evaluate the retry-eligibility decisions for a failed-execution record given its current lifecycle status, its retry-state snapshot (attempt count, timeout deadline and next-retry time point, all in epoch milliseconds) and its retry policy (maximum retry count). Three derived signals are reported. The first, retry-able, is true when the attempt count is strictly below the maximum. The second, can-retry, is true only when retry-able AND the status permits another attempt: a failed status permits it, a succeeded status never does, and a prepared status permits it only after its timeout deadline has elapsed relative to the current wall-clock time. The third, should-retry-now, is true only when can-retry holds AND the current wall-clock time has reached the next-retry time point. Timeout deadlines and next-retry time points set far in the future therefore evaluate as not-yet-timed-out and not-yet-due.",
    "cases": [
        {
            "input": {"action": "retry_decision", "status": "FAILED", "retries": 0, "maxRetries": 10, "timoutAt": 99999999999999, "nextRetryAt": 99999999999999},
            "expected_output": "isRetryable=true\ncanRetry=true\nshouldToRetry=false\n"
        },
        {
            "input": {"action": "retry_decision", "status": "SUCCEEDED", "retries": 1, "maxRetries": 10, "timoutAt": 99999999999999, "nextRetryAt": 99999999999999},
            "expected_output": "isRetryable=true\ncanRetry=false\nshouldToRetry=false\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the back-off calculation, the retry-state snapshot assembly, and the eligibility decisions described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the result to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `next_retry_at` computes a single back-off time point; `next_retry_state` assembles a retry-state snapshot from a policy; `retry_decision` reports the three eligibility booleans for a record. All durations in policy inputs are seconds; all time points are epoch milliseconds.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the standard single-line output pattern used in the response encoder
