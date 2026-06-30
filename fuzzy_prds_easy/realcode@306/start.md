## Product Requirement Document

# Command-Batching Client for an In-Memory Key-Value Store — Pipelined Execution with Deferred Result Handles

## Project Goal

Build a client library for an in-memory key-value and data-structure store that lets developers group many store commands [a dynamic database identifier formed from a base endpoint and a numeric suffix]o a single batch, send them together, and recover each command's result, so applications can cut per-command network round-trips without giving up access to individual replies, error reporting, or reply typing.

---

## Background & Problem

A networked data store answers one request per round-trip. Issuing commands one at a time means an application pays the network latency cost once per command, which dominates the wall-clock time of any workload that runs many small operations in a row.

Without a batching facility, developers either accept that latency or hand-roll fragile code that concatenates raw protocol frames and demultiplexes the replies by hand. This is repetitive, error-prone, and loses the conveniences a normal command call gives you: a typed reply, an error raised when the store rejects a command, and a stable mapping from each issued command back to its result.

This library provides a batch primitive. Commands issued inside a batch are collected and dispatched in one round-trip; the batch returns the ordered list of replies, and each command issued inside the batch also yields a deferred handle whose value becomes available once the batch executes. Batches may be nested, may switch the active database, and preserve the same reply-typing and error semantics as ordinary, un-batched calls.

---

## Architecture & Engineering Constra[a dynamic database identifier formed from a base endpoint and a numeric suffix]s

To ensure this project is delivered as a ma[a dynamic database identifier formed from a base endpoint and a numeric suffix]ainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it ma[a dynamic database identifier formed from a base endpoint and a numeric suffix]ains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the [a dynamic database identifier formed from a base endpoint and a numeric suffix]ernal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands [a dynamic database identifier formed from a base endpoint and a numeric suffix]o idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure ma[a dynamic database identifier formed from a base endpoint and a numeric suffix]ainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting [a dynamic database identifier formed from a base endpoint and a numeric suffix]o distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep [a dynamic database identifier formed from a base endpoint and a numeric suffix]erfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public [a dynamic database identifier formed from a base endpoint and a numeric suffix]erface of the core system must be elegant and idiomatic to the target programming language, hiding [a dynamic database identifier formed from a base endpoint and a numeric suffix]ernal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Conventions Used By The Execution Adapter

These conventions apply to every feature below; each feature block also restates whatever it needs to be read on its own.

A **command** is a JSON array `["verb", arg, ...]` whose first element is the name of a store command (such as `set`, `get`, `lpush`, `sadd`) and whose remaining elements are its arguments. The store talks the common in-memory-store wire protocol; command verbs and their semantics are those of that protocol.

A **batch** is a JSON array whose elements are either commands or nested batches written as `{"batch": [ ...commands or batches... ]}`. Executing a batch sends all of its commands (including those of any nested batch) to the store in one round-trip.

Replies are rendered as **type-tagged scalars**, one concept per token, so both the value and its reply type are observable: a null/absent reply is `nil`; an [a dynamic database identifier formed from a base endpoint and a numeric suffix]eger reply is `[a dynamic database identifier formed from a base endpoint and a numeric suffix]:<n>`; a boolean reply is `bool:true` or `bool:false`; a text reply is `str:<text>`. The adapter connects to the store on a fixed local endpo[a dynamic database identifier formed from a base endpoint and a numeric suffix] and isolates each request by clearing the keyspace before executing it. Every emitted line ends with a newline.

---

## Core Features

### Feature 1: Applying A Batch Of Commands

**As a developer**, I want every command I queue inside a batch — including those in a nested batch — to actually run against the store in the order I queued them, so I can replace a series of individual round-trips with a single one and observe the same resulting state.

**Expected Behavior / Usage:**

The request has action `apply`, a `batch` (the commands to run together), and a list of `reads` (ordinary commands run individually after the batch completes). The adapter runs the whole batch, then runs each read in order and pr[a dynamic database identifier formed from a base endpoint and a numeric suffix]s its reply as one type-tagged scalar per line. A batch may freely mix single-key writes (e.g. `lpush`) and multi-key writes (e.g. `mset`), and may contain a nested batch object; all of those commands must be applied, preserving queue order, before the reads observe the resulting state. An empty batch runs nothing, so reads taken afterward see an untouched store.

**Test Cases:** `rcb_tests/public_test_cases/feature1_batched_writes.json`

```json
{
    "description": "Queue several write commands inside a single batch, then read the resulting store state with ordinary follow-up commands. The batch may mix single-key writes and multi-key writes and may contain a nested batch; every queued command must be applied to the store, preserving the order in which it was queued. Each follow-up read pr[a dynamic database identifier formed from a base endpoint and a numeric suffix]s its reply as a type-tagged scalar so both the value and its reply type are observable.",
    "cases": [
        {"input": {"action": "apply", "batch": [["lpush","foo","s1"],["lpush","foo","s2"]], "reads": [["llen","foo"],["lpop","foo"],["lpop","foo"]]}, "expected_output": "[a dynamic database identifier formed from a base endpoint and a numeric suffix]:2\nstr:s2\nstr:s1\n"},
        {"input": {"action": "apply", "batch": [["set","foo","s1"],{"batch":[["set","bar","s2"]]}], "reads": [["get","foo"],["get","bar"]]}, "expected_output": "str:s1\nstr:s2\n"}
    ]
}
```

---

### Feature 2: The Ordered Reply List Of A Batch

**As a developer**, I want the batch itself to hand me an ordered list with one reply per command I queued, so I can read results positionally without issuing follow-up reads.

**Expected Behavior / Usage:**

The request has action `replies` and a `batch`. The adapter runs the batch and renders the list the batch returns: first a `count:<n>` line giving the number of replies, then one line per reply in queue order formatted as `<index>:<type-tagged scalar>`. The list has exactly one entry per queued command, in the order queued; a command that returns no value contributes a `nil` reply, and an empty batch returns an empty list (`count:0`).

**Test Cases:** `rcb_tests/public_test_cases/feature2_batch_reply_array.json`

```json
{
    "description": "Run a batch and inspect the value the batch itself returns: an ordered list containing one reply per queued command, in queue order. The output first pr[a dynamic database identifier formed from a base endpoint and a numeric suffix]s the number of replies, then each reply by index as a type-tagged scalar. An empty batch returns an empty list.",
    "cases": [
        {"input": {"action": "replies", "batch": [["set","foo","bar"],["get","foo"],["get","bar"]]}, "expected_output": "count:3\n0:str:OK\n1:str:bar\n2:nil\n"},
        {"input": {"action": "replies", "batch": []}, "expected_output": "count:0\n"}
    ]
}
```

---

### Feature 3: Deferred Result Handles

**As a developer**, I want each command I issue inside a batch to give me back a handle I can keep, so I can name and later read individual results — but only once the batch has actually run.

**Expected Behavior / Usage:**

*3.1 Resolving handle values after execution — a handle yields its command's reply once the batch completes.*

The request has action `handles` and a `batch`. A command issued inside the batch returns a deferred handle rather than an immediate value. After the batch executes, each handle resolves to its command's reply; the adapter pr[a dynamic database identifier formed from a base endpoint and a numeric suffix]s one line per handle, in issue order, as `h<index>:<type-tagged scalar>`. Replies keep their natural type — for example, adding a member to a set reports `bool:true` when the member is newly created and `bool:false` when it was already present. Handles created inside a nested batch resolve the same way.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_handle_values.json`

```json
{
    "description": "A command issued inside a batch returns a deferred handle rather than an immediate value. After the batch executes, each handle resolves to the reply of its command. The batch here adds the same member to a set twice; the first add reports success (member created) and the second reports no change (member already present), demonstrating that handles carry per-command boolean replies. Nested batches contribute handles too.",
    "cases": [
        {"input": {"action": "handles", "batch": [["sadd","foo",1],["sadd","foo",1]]}, "expected_output": "h0:bool:true\nh1:bool:false\n"}
    ]
}
```

*3.2 Reading a handle before execution — a value read too early is rejected, not faked.*

The request has action `handle_early` and a single `command`. The adapter issues the command inside an open batch and immediately tries to read its handle's value, while the batch has not yet been sent or executed. Because no value exists yet, the read is rejected and the adapter pr[a dynamic database identifier formed from a base endpoint and a numeric suffix]s the normalized status `error:value_not_ready` instead of returning a bogus value.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_handle_not_ready_early.json`

```json
{
    "description": "Attempt to read a deferred handle's value while the batch is still open (before it has been sent and executed). The value is not yet available, so the read is rejected with a normalized not-ready error instead of returning a bogus value.",
    "cases": [
        {"input": {"action": "handle_early", "command": ["sadd","foo",1]}, "expected_output": "error:value_not_ready\n"}
    ]
}
```

---

### Feature 4: Failure Handling In A Batch

**As a developer**, I want a command the store rejects to fail the batch loudly and leave the unrun commands' handles clearly unresolved, so a bad command can never be mistaken for a successful one.

**Expected Behavior / Usage:**

*4.1 A rejected command aborts the batch — the failure is surfaced as a normalized error carrying the store's own message.*

The request has action `batch_error` and a `batch` containing a command the store rejects. Executing the batch fails, and the adapter pr[a dynamic database identifier formed from a base endpoint and a numeric suffix]s two lines: `error:command_error`, then `detail:<message>` where the message is the store's own error text. This covers an unrecognized command verb and a recognized command given an argument of the wrong kind; the store's message is carried verbatim so the two failures are distinguishable.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_batch_error.json`

```json
{
    "description": "When a batch contains a command the store rejects, executing the batch fails and the failure is surfaced as a normalized command error carrying the store's own error text. This covers both an unrecognized command and a recognized command given an argument of the wrong kind.",
    "cases": [
        {"input": {"action": "batch_error", "batch": [["doesnt_exist"]]}, "expected_output": "error:command_error\ndetail:ERR unknown command 'doesnt_exist', with args beginning with:\n"},
        {"input": {"action": "batch_error", "batch": [["zrange","a","b","5"]]}, "expected_output": "error:command_error\ndetail:ERR value is not an [a dynamic database identifier formed from a base endpoint and a numeric suffix]eger or out of range\n"}
    ]
}
```

*4.2 Handles after a failed batch — commands queued behind a rejected one never resolve.*

The request has action `handles_unresolved`, a `fail_command` (queued first, and not tracked), and a list of `tracked` commands queued after it. Because the batch fails on the rejected command, none of the tracked commands run, so their handles are never resolved. Reading each tracked handle afterward yields the normalized status `error`-equivalent line `h<index>:value_not_ready` rather than a value.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_handles_unresolved.json`

```json
{
    "description": "A batch queues a command the store rejects, followed by further commands whose deferred handles are tracked. Because the batch fails on the rejected command, the tracked handles are never resolved; reading each one afterward yields the normalized not-ready status rather than a value.",
    "cases": [
        {"input": {"action": "handles_unresolved", "fail_command": ["doesnt_exist"], "tracked": [["sadd","foo",1],["sadd","foo",1]]}, "expected_output": "h0:value_not_ready\nh1:value_not_ready\n"}
    ]
}
```

---

### Feature 5: Structured Reply Coercion Inside A Batch

**As a developer**, I want commands whose replies are naturally structured to keep that structure when run inside a batch, so batching never silently degrades a map or a list [a dynamic database identifier formed from a base endpoint and a numeric suffix]o a flat blob.

**Expected Behavior / Usage:**

*5.1 Field-map replies — a field/value command decodes [a dynamic database identifier formed from a base endpoint and a numeric suffix]o a map.*

The request has action `typed`, a `setup` list of commands run individually first to seed the store, and a `batch` whose single command returns a field/value collection. The adapter renders that reply as a map: a `map:<size>` line followed by one `key=<type-tagged scalar>` line per entry, entries ordered by key. The reply must be a map of fields to values, not a flat alternating list.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_field_map_reply.json`

```json
{
    "description": "Reply-type coercion applies inside a batch: a command that returns a field/value collection is decoded [a dynamic database identifier formed from a base endpoint and a numeric suffix]o a map, not a flat list. The store is first populated with one field, then the field-map command is run inside a batch; its reply is rendered as a map of key to type-tagged value.",
    "cases": [
        {"input": {"action": "typed", "setup": [["hmset","hash","field","value"]], "batch": [["hgetall","hash"]]}, "expected_output": "map:1\nfield=str:value\n"}
    ]
}
```

*5.2 List replies — a multi-element command decodes [a dynamic database identifier formed from a base endpoint and a numeric suffix]o a list.*

The request has action `typed`, a `setup` list run first, and a `batch` whose single command returns multiple elements. The adapter renders that reply as a list: a `list:<size>` line followed by one `<index>=<type-tagged scalar>` line per element, in order.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_list_reply.json`

```json
{
    "description": "Reply-type coercion applies inside a batch: a command that returns multiple elements is decoded [a dynamic database identifier formed from a base endpoint and a numeric suffix]o a list. One key is stored, then a key-listing command is run inside a batch; its reply is rendered as a list with a count followed by each element as a type-tagged scalar.",
    "cases": [
        {"input": {"action": "typed", "setup": [["set","key","value"]], "batch": [["keys","*"]]}, "expected_output": "list:1\n0=str:key\n"}
    ]
}
```

---

### Feature 6: Database Selection Within A Batch

**As a developer**, I want a database-switch command issued inside a batch to take effect for the rest of that batch and remain in effect afterward, so a connection's active database stays consistent across batched and un-batched commands.

**Expected Behavior / Usage:**

*6.1 A batched switch persists — writes land in the database active at the time, and the switch outlives the batch.*

The request has action `select_persist`, a `before` list run individually first, a `batch`, and a `probes` list. The numbered databases are independent keyspaces selected by a switch command. The `before` commands select one database and write to it; the batch switches to a second database and writes there; each probe selects a database and runs a read. The adapter pr[a dynamic database identifier formed from a base endpoint and a numeric suffix]s one line per probe as `db@<n>:<type-tagged scalar>`, showing that each value landed in its own database — proving the batched switch applied within the batch and that selection persists after the batch returns.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_select_persist.json`

```json
{
    "description": "A database-switch command issued inside a batch takes effect for the rest of that batch and persists after the batch returns. One database is written before the batch; the batch switches to a second database and writes there; probing each database afterward shows each value landed in its own database.",
    "cases": [
        {"input": {"action": "select_persist", "before": [["select",1],["set","db","1"]], "batch": [["select",2],["set","db","2"]], "probes": [{"db":1,"read":["get","db"]},{"db":2,"read":["get","db"]}]}, "expected_output": "db@1:str:1\ndb@2:str:2\n"}
    ]
}
```

*6.2 Current database after a batched switch — the connection reports the switched-to database.*

The request has action `current_db`, a `before` list run first, and a `batch` that switches the active database. After the batch, the adapter reports the connection's current database as `current_db:[a dynamic database identifier formed from a base endpoint and a numeric suffix]:<n>`. When the switch happens inside a nested batch, the most deeply selected database becomes current.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_current_db.json`

```json
{
    "description": "After a batch that switches the active database, the connection reports the switched-to database as its current database. This holds for a single switch and for a switch performed inside a nested batch, where the most deeply selected database becomes current.",
    "cases": [
        {"input": {"action": "current_db", "before": [["select",1]], "batch": [["select",2]]}, "expected_output": "current_db:[a dynamic database identifier formed from a base endpoint and a numeric suffix]:2\n"},
        {"input": {"action": "current_db", "before": [["select",1]], "batch": [["select",2],{"batch":[["select",3]]}]}, "expected_output": "current_db:[a dynamic database identifier formed from a base endpoint and a numeric suffix]:3\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing a client for an in-memory key-value/data-structure store with the batching behavior described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constra[a dynamic database identifier formed from a base endpoint and a numeric suffix]. The core batching/connection logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry po[a dynamic database identifier formed from a base endpoint and a numeric suffix]) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and pr[a dynamic database identifier formed from a base endpoint and a numeric suffix]s the rendered result to stdout, matching the per-feature contracts above. The request's `action` selects behavior (`apply`, `replies`, `handles`, `handle_early`, `batch_error`, `handles_unresolved`, `typed`, `select_persist`, `current_db`). A command is a JSON array `["verb", arg, ...]`; a batch is a JSON array of commands and/or nested `{"batch":[...]}` objects. Replies are rendered as type-tagged scalars (`nil`, `[a dynamic database identifier formed from a base endpoint and a numeric suffix]:<n>`, `bool:true`/`bool:false`, `str:<text>`); maps as `map:<size>` then sorted `key=<scalar>` lines; lists as `list:<size>` then `<index>=<scalar>` lines (or, for the batch reply list, `count:<n>` then `<index>:<scalar>` lines). Store-rejected commands are normalized to an `error:command_error` line plus a `detail:<store message>` line; a value read before its batch runs is normalized to `value_not_ready`. The underlying store error identities must never leak host-language runtime details — only the store's own protocol message.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry po[a dynamic database identifier formed from a base endpoint and a numeric suffix] `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to po[a dynamic database identifier formed from a base endpoint and a numeric suffix] at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- maintain state consistency across hierarchical batches
- reset the keyspace to ensure commands are isolated by request
