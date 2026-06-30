## Product Requirement Document

# Graceful Task Orchestrator with Dependency-Ordered Shutdown

## Project Goal

Build a task-orchestration library that lets a long-running service register many background workers under a fixed set of named nodes and then shut all of them down **gracefully and in a guaranteed order**. When the process is asked to stop, every worker is cancelled and allowed to finish, but only in an order that respects the dependencies between nodes: a node is torn down only after everything that depends on it has already stopped. Developers get correct, deterministic shutdown without hand-writing teardown ordering logic.

---

## Background & Problem

Without this library, developers wiring up a service with many concurrent background tasks (request handlers, flushers, metrics servers, RPC servers, write-back loops) have to manually track which task must stop before which other task. Stopping a producer before its consumers, or a consumer before its producer, leads to lost data, panics on closed channels, or hangs. The teardown logic is repetitive, fragile, and easy to get wrong as the set of tasks grows.

With this library, the dependency relationships between node types are declared once as a fixed graph. Each background worker is registered under a node. A single shutdown trigger — either an explicit call or an OS termination signal — cancels everything and drains it in the correct topological order automatically. The same mechanism also rejects late work submitted after shutdown has begun, and provides a batching mode for nodes that manage large numbers of short-lived tasks.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain has several distinct responsibilities (the dependency-graph model, the node/worker registry, the shutdown driver, the batching collector, and the signal hook). It MUST NOT be a single "god file"; use a clear multi-module layout that separates these concerns. Do not over-engineer, but do not collapse distinct responsibilities together either.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box testing contract** for the execution adapter, NOT the internal data model. The core orchestration logic must be completely decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls into the core library and rendering the results.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Separate graph definition, registration, shutdown sequencing, batch collection, and output formatting into distinct units.
   - **Open/Closed Principle (OCP):** The shutdown engine must be open to new node types via the graph definition without modifying the sequencing algorithm.
   - **Liskov Substitution Principle (LSP):** A batching node handle must be usable wherever a plain registration handle is expected.
   - **Interface Segregation Principle (ISP):** Keep the public registration/shutdown interface small and cohesive.
   - **Dependency Inversion Principle (DIP):** The shutdown driver depends on the abstract graph, not on concrete I/O.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface must be elegant and idiomatic to the target language, hiding the internal graph bookkeeping.
   - **Resilience:** Submitting work after shutdown must be modeled as a typed, recoverable failure (e.g. an error value carrying the rejected node), never a panic or a silent drop. Batched tasks that never make progress must be bounded by a timeout rather than hanging forever.

---

## Core Features

### Feature 1: Dependency-Ordered Graceful Shutdown

**As a developer**, I want to register background workers under named nodes and trigger one graceful shutdown, so I can stop the whole system in dependency order without writing teardown sequencing by hand.

**Expected Behavior / Usage:**

There is a fixed dependency graph over a closed set of node names: `Root`, `Metrics`, `BlockFlush`, `FuseRequest`, `AsyncFuse`, `Rpc`, `WriteBack`, `SchedulerExtender`. The dependency edges are: `Root` depends on `Metrics`, `BlockFlush`, `SchedulerExtender`; `BlockFlush` depends on `AsyncFuse` and `FuseRequest`; `FuseRequest` depends on `AsyncFuse` and `WriteBack`; `AsyncFuse` depends on `Rpc` and `WriteBack`. Each registered worker carries an integer `marker`. The input is an `[a specific set of enumerated action strings]` command with a list of `spawns`, each naming a `node` and a `marker`. Every named worker is registered, then a graceful shutdown is requested. On shutdown, each worker is cancelled and emits one line `node=<NodeName> marker=<marker>`. The lines appear in the graph's shutdown order: teardown starts at `Root` and a node is only torn down after every node that depends on it has already been torn down. For the full set, the resulting order is the three first-tier nodes `Metrics`, `BlockFlush`, `SchedulerExtender` (markers `0,0,0`), then `FuseRequest` (marker `1`), then `AsyncFuse` (marker `2`), then the two leaf consumers `Rpc`, `WriteBack` (markers `3,3`). When only a subset of nodes is registered, only those nodes' lines appear, still in the same relative shutdown order. Output is deterministic across runs.

**Test Cases:** `rcb_tests/public_test_cases/feature1_[a specific set of enumerated action strings].json`

```json
{
    "description": "Background workers are registered against named nodes of a fixed dependency graph, each carrying an integer marker. When a graceful shutdown is requested, every worker is cancelled and reports its marker. The reports are emitted strictly in the graph's shutdown order: a node is only torn down after every node that depends on it has already been torn down, so upstream producers stop before the consumers they feed.",
    "cases": [
        {
            "input": {"action": "[a specific set of enumerated action strings]", "spawns": [{"node": "Metrics", "marker": 0}, {"node": "BlockFlush", "marker": 0}, {"node": "SchedulerExtender", "marker": 0}, {"node": "FuseRequest", "marker": 1}, {"node": "AsyncFuse", "marker": 2}, {"node": "Rpc", "marker": 3}, {"node": "WriteBack", "marker": 3}]},
            "expected_output": "node=Metrics marker=0\nnode=BlockFlush marker=0\nnode=SchedulerExtender marker=0\nnode=FuseRequest marker=1\nnode=AsyncFuse marker=2\nnode=Rpc marker=3\nnode=WriteBack marker=3\n"
        },
        {
            "input": {"action": "[a specific set of enumerated action strings]", "spawns": [{"node": "BlockFlush", "marker": 10}, {"node": "AsyncFuse", "marker": 20}, {"node": "Rpc", "marker": 30}]},
            "expected_output": "node=BlockFlush marker=10\nnode=AsyncFuse marker=20\nnode=Rpc marker=30\n"
        }
    ]
}
```

---

### Feature 2: Signal-Triggered Shutdown

**As a developer**, I want an OS termination signal to drive the same graceful shutdown, so the service stops cleanly when the platform asks it to terminate.

**Expected Behavior / Usage:**

Workers are registered exactly as in Feature 1, but instead of an explicit shutdown call a process termination signal is armed and then raised. The input is a `[a specific set of enumerated action strings]` command carrying a `signal` label and the same `spawns` list. When the signal fires, the system first emits one line `signal=<label>` reporting the signal it observed, then performs the identical dependency-ordered teardown, emitting `node=<NodeName> marker=<marker>` lines in the same shutdown order as Feature 1. The signal line always precedes all node lines.

**Test Cases:** `rcb_tests/public_test_cases/feature2_[a specific set of enumerated action strings].json`

```json
{
    "description": "Instead of an explicit shutdown call, a process-level termination signal initiates the graceful shutdown. After registering workers and arming the signal handler, a termination signal is raised. The handler reports the signal it observed and then drives the exact same dependency-ordered teardown, so every worker reports its marker in graph order following the signal line.",
    "cases": [
        {
            "input": {"action": "[a specific set of enumerated action strings]", "signal": "SIGTERM", "spawns": [{"node": "Metrics", "marker": 0}, {"node": "BlockFlush", "marker": 0}, {"node": "SchedulerExtender", "marker": 0}, {"node": "FuseRequest", "marker": 1}, {"node": "AsyncFuse", "marker": 2}, {"node": "Rpc", "marker": 3}, {"node": "WriteBack", "marker": 3}]},
            "expected_output": "signal=SIGTERM\nnode=Metrics marker=0\nnode=BlockFlush marker=0\nnode=SchedulerExtender marker=0\nnode=FuseRequest marker=1\nnode=AsyncFuse marker=2\nnode=Rpc marker=3\nnode=WriteBack marker=3\n"
        }
    ]
}
```

---

### Feature 3: Rejecting Work After Shutdown

**As a developer**, I want registrations submitted after shutdown has begun to fail explicitly, so late work cannot silently leak into a system that is already stopping.

**Expected Behavior / Usage:**

The input is a `[a specific set of enumerated action strings]` command naming a single `node`. The system is shut down first, then a new worker registration is attempted on that node. The registration is refused and reported as a normalized error: the output is two lines — `error=[a specific set of enumerated action strings]` followed by `node=<NodeName>` echoing the node that was rejected. No worker is started and there is no success line. The error is a domain-level category; it must not leak any host-language exception identity or runtime message.

**Test Cases:** `rcb_tests/public_test_cases/feature3_[a specific set of enumerated action strings].json`

```json
{
    "description": "Once a graceful shutdown has been initiated, the registry refuses to accept any further work. Attempting to register a new worker on any node after shutdown is rejected, and the rejection reports the node that was refused rather than silently succeeding.",
    "cases": [
        {
            "input": {"action": "[a specific set of enumerated action strings]", "node": "Root"},
            "expected_output": "error=[a specific set of enumerated action strings]\nnode=Root\n"
        }
    ]
}
```

---

### Feature 4: Batched Collection on Garbage-Collected Nodes

**As a developer**, I want certain nodes to absorb large numbers of short-lived tasks through a single batching handle, so I can fire many fire-and-forget tasks and still have them all drained correctly on shutdown.

**Expected Behavior / Usage:**

Some node names (`BlockFlush`, `FuseRequest`) are garbage-collected nodes: rather than holding workers directly, they expose a lightweight handle that funnels many tasks into one background collector. The input is a `[a specific set of enumerated action strings]` command whose `spawns` entries name a garbage-collected `node`, a `marker`, and a `count` of tasks to enqueue on that node. All `count` tasks are enqueued per node; on shutdown the collector drains every enqueued task and each emits `node=<NodeName> marker=<marker>`. All tasks belonging to one garbage-collected node are drained together (one line per enqueued task) before moving on to the next node. The total number of output lines equals the sum of the `count` values.

**Test Cases:** `rcb_tests/public_test_cases/feature4_[a specific set of enumerated action strings].json`

```json
{
    "description": "Certain nodes are garbage-collected nodes: instead of holding workers directly, they hand out a lightweight handle that batches many short-lived tasks into a single background collector. Multiple tasks are enqueued per garbage-collected node; on shutdown the collector drains every enqueued task and each reports its marker. All tasks belonging to one garbage-collected node are drained together before moving to the next node.",
    "cases": [
        {
            "input": {"action": "[a specific set of enumerated action strings]", "spawns": [{"node": "BlockFlush", "marker": 0, "count": 5}, {"node": "FuseRequest", "marker": 1, "count": 5}]},
            "expected_output": "node=BlockFlush marker=0\nnode=BlockFlush marker=0\nnode=BlockFlush marker=0\nnode=BlockFlush marker=0\nnode=BlockFlush marker=0\nnode=FuseRequest marker=1\nnode=FuseRequest marker=1\nnode=FuseRequest marker=1\nnode=FuseRequest marker=1\nnode=FuseRequest marker=1\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured task-orchestration library implementing the features above — a fixed node dependency graph, a node/worker registry, a dependency-ordered shutdown driver, a batching collector for garbage-collected nodes, and a termination-signal hook. Its physical structure MUST follow the "Scale-Driven Code Organization" constraint (a multi-module layout separating these concerns), without over-engineering.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core library. It reads a single JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-feature contracts above. It translates any native failure (such as a rejected post-shutdown registration) into the normalized, language-neutral error lines specified above. This adapter must be logically and physically separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[a specific set of enumerated action strings].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[a specific set of enumerated action strings]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- emitted consecutively without interleaving unless the batching handle defines them as distinct groups
