## Product Requirement Document

# Generic Resource Pool — Bounded, Thread-Safe Sharing of Reusable Resources

## Project Goal

Build a reusable, thread-safe pool that lets many threads share a bounded set of expensive-to-create resources (such as network or database connections), so developers can cap how many live resources exist at once and hand them out on demand without each caller having to create, track, and tear down its own resource.

---

## Background & Problem

Some resources are expensive to create and limited in number — opening a fresh network connection per request is slow, and an unbounded number of simultaneous connections can overwhelm a server. Without a shared pool, developers hand-roll their own bookkeeping: allocating a fixed set of resources up front, guarding them with locks, lending them out one at a time, reclaiming them when callers finish, and making waiters block (or fail) when none are free. This boilerplate is repetitive and easy to get wrong, especially around timeouts, re-entrancy, and returning a resource exactly once.

With this library, a developer constructs a pool of a fixed size from a factory that builds one resource, then borrows a resource for the duration of a block; the resource is automatically returned when the block finishes. A transparent wrapper variant forwards ordinary method calls straight through to a pooled resource. Borrowing blocks until a resource is free or a configured timeout elapses, re-entrant borrowing inside the same thread reuses the resource already held, and an unsaturated pool keeps reusing the same instance instead of churning new ones.

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

### Feature 1: Block-Scoped Borrowing Returns The Block's Value

**As a developer**, I want to borrow a resource for the duration of a block and get my block's own result back, so I can use a pooled resource inline and have it returned automatically when I am done.

**Expected Behavior / Usage:**

A pool is built with a fixed `size` and a factory that produces one resource. Borrowing for the scope of a block runs the caller's block with a live resource and returns whatever the block returns; the resource is released back to the pool when the block finishes (normally or via an error). In this scenario the pooled resource holds an integer counter starting at zero, and the borrowed block invokes an operation that adds a supplied `increment` to that counter and returns the new total. The output is a single line `value=<n>`, where `<n>` is the value the block returned. Because each resource starts at zero, borrowing once and adding `increment` yields exactly `increment`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_block_return.json`

```json
{
    "description": "A pooled resource is borrowed for the duration of a block, and the value produced by the block becomes the result of the borrow operation. The pooled resource exposes an operation that adds a given amount to its internal counter and returns the new counter total. The output reports the value the block returned.",
    "cases": [
        {
            "input": {"action": "with_return", "size": 1, "increment": 1},
            "expected_output": "value=1[a single newline character string]"
        }
    ]
}
```

---

### Feature 2: Same-Instance Reuse On An Unsaturated Pool

**As a developer**, I want repeated borrow/release cycles on a pool that is never fully in use to keep handing back the same resource, so I am not paying to create and discard resources when there is no contention.

**Expected Behavior / Usage:**

When borrows are strictly sequential — each resource released before the next is requested — a pool whose `size` exceeds the demand returns the very same resource instance every time, rather than rotating through freshly created ones. The scenario performs `iterations` sequential borrow/release cycles against a pool of the given `size`, recording the identity of the resource handed out on each cycle. The output is two lines: `count=<k>` (how many borrows were performed, equal to `iterations`) and `unique=<u>` (how many distinct resource identities were observed). For purely sequential, non-overlapping borrows, `unique` is always `1`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_reuse_identity.json`

```json
{
    "description": "On a pool that is never saturated, borrowing one resource at a time and releasing it before the next borrow always hands back the same underlying resource instance. The scenario performs a number of sequential borrow/release cycles and observes the identity of the resource each time. The output reports how many borrows occurred and how many distinct resource identities were seen across them.",
    "cases": [
        {
            "input": {"action": "reuse", "size": 5, "iterations": 10},
            "expected_output": "count=10[a single newline character string]unique=1[a single newline character string]"
        }
    ]
}
```

---

### Feature 3: Transparent Wrapper Forwards Calls To The Pooled Resource

**As a developer**, I want a wrapper that I can call as if it were the resource itself, transparently borrowing and releasing behind each call, so I can drop a pooled resource into code that expects a plain object.

**Expected Behavior / Usage:**

A transparent wrapper is created over a pool that holds a single resource. Any method call made on the wrapper is forwarded to a borrowed resource, the call is executed against it, the resource is released, and the resource's own return value is passed back to the caller. Because the pool holds one resource and the calls are sequential, every forwarded call lands on the same instance, so its internal state accumulates across the sequence. In this scenario the resource holds an integer counter starting at zero, and each forwarded call adds the supplied `by` amount and returns the new running total. The input lists the calls to forward in order via `ops`; the output is one line `value=<n>` per call, in order, showing the accumulating totals.

**Test Cases:** `rcb_tests/public_test_cases/feature3_wrapper_passthru.json`

```json
{
    "description": "A transparent wrapper around a single-resource pool forwards arbitrary method calls to the pooled resource and returns the resource's own return value. Each forwarded call borrows the resource, invokes the method, and releases it; because the pool holds a single resource, its internal state accumulates across the sequence of calls. Each call supplies an amount to add to the resource's counter, and the output lists the value returned by each forwarded call in order.",
    "cases": [
        {
            "input": {"action": "passthru", "size": 1, "timeout": 0.1, "ops": [{"by": 1}, {"by": 1}, {"by": 3}, {"by": 1}]},
            "expected_output": "value=1[a single newline character string]value=2[a single newline character string]value=5[a single newline character string]value=6[a single newline character string]"
        }
    ]
}
```

---

### Feature 4: Transparent Wrapper Capability Queries

**As a developer**, I want to ask the transparent wrapper whether it can handle a given call, so feature-detection code keeps working even though calls are really being forwarded to a pooled resource.

**Expected Behavior / Usage:**

A capability query asks the transparent wrapper, for each candidate name, whether it will respond to that call. The wrapper answers `true` for its own block-scoped borrowing operation (named `with`), and for every other name it answers based on whether the pooled resource itself responds to that name — borrowing a resource and asking it. This means real methods of the resource report `true`, and a virtual method that the resource chooses to acknowledge through its own custom capability check also reports `true`, while a name that neither the wrapper nor the resource recognizes reports `false`. The input is the list of `names` to query. In this scenario the pooled resource has a real method `work` and additionally acknowledges the virtual name `do_magic`. The output is one line `<name>=<bool>` per queried name, in input order.

**Test Cases:** `rcb_tests/public_test_cases/feature4_wrapper_respond_to.json`

```json
{
    "description": "A capability query against the transparent wrapper. For each queried name the wrapper reports whether it can respond to that call. It answers true for its own block-scoped borrowing operation, true for any method the pooled resource itself responds to (including a virtual method the resource recognizes through a custom capability check), and false for a name that neither the wrapper nor the resource recognizes. The input is the list of names to query; the output reports each name with its boolean answer.",
    "cases": [
        {
            "input": {"action": "respond_to", "names": ["with", "work", "do_magic", "do_lots_of_magic"]},
            "expected_output": "with=true[a single newline character string]work=true[a single newline character string]do_magic=true[a single newline character string]do_lots_of_magic=false[a single newline character string]"
        }
    ]
}
```

---

### Feature 5: Exhaustion Timeout And Recovery

**As a developer**, I want a borrow attempt to fail with a timeout when no resource frees up in time, so my code degrades gracefully under contention instead of hanging forever, and I want borrowing to succeed again once a resource is returned.

**Expected Behavior / Usage:**

A pool is created with a fixed `size` and a `timeout` (in seconds). When all resources are currently held elsewhere, a new borrow attempt waits at most `timeout` seconds for one to be released; if none becomes available within that window, the attempt fails with a timeout error rather than blocking indefinitely. In this scenario background holders occupy all `size` resources for `hold` seconds (with `hold` chosen comfortably larger than `timeout`), so the first borrow reliably times out. After the holders release their resources, a subsequent borrow succeeds and yields a usable, non-nil resource. The timeout error is reported as the normalized line `error=timeout` (it must NOT leak any host-language exception type or message). The output is `error=timeout` followed by `recovered=true`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_timeout.json`

```json
{
    "description": "When every resource in the pool is already held elsewhere, a fresh borrow attempt waits only up to the pool's configured timeout and then fails with a timeout error instead of blocking forever. The scenario starts background holders that occupy all resources for a fixed duration, attempts a borrow with a short timeout (which fails), then waits for the holders to release and borrows again successfully, yielding a usable non-nil resource. Timing is fixed so the first borrow always times out and the second always succeeds. The output reports the normalized timeout error followed by the successful recovery.",
    "cases": [
        {
            "input": {"action": "timeout", "size": 1, "timeout": 0.05, "hold": 0.3},
            "expected_output": "error=timeout[a single newline character string]recovered=true[a single newline character string]"
        }
    ]
}
```

---

### Feature 6: Re-Entrant Borrowing And Fair Handoff To Waiters

**As a developer**, I want a borrow nested inside another borrow on the same thread to reuse the resource I already hold, and a different thread waiting for a resource to proceed only once I release it, so re-entrant code does not deadlock and waiting threads are served in turn.

**Expected Behavior / Usage:**

Borrowing is re-entrant per thread: if a thread that already holds a resource borrows again, it receives the same resource it is already holding instead of waiting for a separate one — so even a single-resource pool does not deadlock when one borrow is nested inside another on the same thread. A resource is only returned to the pool when the outermost borrow on that thread completes. Meanwhile, a different thread that tries to borrow while the resource is held must wait until the holding thread fully releases it, and then proceeds. In this scenario a single shared resource records the order in which work is performed: while the outer borrow is held, (a) a second thread starts and blocks trying to borrow, (b) a nested borrow on the holding thread runs and records `inner`, (c) the holding thread records `outer` and then releases, and (d) the previously blocked thread now obtains the resource and records `other`. The output is a single line `calls=<labels>` listing the recorded labels in execution order, comma-separated.

**Test Cases:** `rcb_tests/public_test_cases/feature6_nested_reentrant.json`

```json
{
    "description": "Re-entrant borrowing within a single thread reuses the resource already held by that thread rather than waiting for a new one, so a one-resource pool does not deadlock when a borrow is nested inside another borrow. Meanwhile, a separate thread that attempts to borrow while the resource is held must wait until the holding thread fully releases it. Work is recorded in the order it executes: the nested inner borrow runs first (reusing the held resource), then the outer holder performs its own work, and finally the previously blocked thread runs once the resource becomes available. The output reports the recorded order of work.",
    "cases": [
        {
            "input": {"action": "nested", "size": 1},
            "expected_output": "calls=[the previously pending thread adds itself last in the acquisition sequence][a single newline character string]"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the bounded, thread-safe resource pool described above — fixed-size construction from a resource factory, block-scoped borrowing that always returns the resource, blocking-with-timeout acquisition, per-thread re-entrant borrowing, same-instance reuse when uncontended, and a transparent wrapper that forwards calls to a pooled resource. Its physical structure (single-file vs. multi-file) MUST align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the resulting signals to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `with_return` (borrow once and report the block's value), `reuse` (sequential borrows and distinct-identity count), `passthru` (forward a list of calls through the transparent wrapper), `respond_to` (query wrapper capabilities for a list of names), `timeout` (exhaust the pool, observe the timeout, then recover), and `nested` (re-entrant borrowing plus cross-thread handoff ordering). Any timeout or other host-language exception MUST be normalized in this adapter into a neutral `error=<category>` line; the core domain may raise idiomatic exceptions, but their language identity MUST NOT appear in stdout.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- Resolve false for unrecognized names
- Execute block-scoped borrow, run supplied block, return block result as 'value=...'
