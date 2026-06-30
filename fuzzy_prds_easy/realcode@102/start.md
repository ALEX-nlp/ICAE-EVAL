## Product Requirement Document

# Batched Relationship Loader — Query Coalescing and Caching for Many-to-Many Data Access

## Project Goal

Build a transparent data-access layer that, given an existing relational mapping, batches and caches the loading of many-to-many relationships, so developers can fetch the linked records for many owner records at once with a single underlying query instead of one query per owner, without changing the call sites that request those relationships.

---

## Background & Problem

A relational application frequently needs, for a set of owner records, the collection of peer records linked to each owner through an intermediate join table (a classic many-to-many relationship). The naive approach calls the relationship getter once per owner, producing one database round-trip per owner — the well-known N+1 query problem. As the number of owners grows, this becomes the dominant cost of a request.

With this layer, the relationship getters are wrapped so that any getter calls issued within the same execution tick are coalesced: the layer collects the owner keys, issues one batched query whose filter carries the whole set of keys, then de-multiplexes the returned rows back to the owner that asked for them. It additionally offers an explicit loading context that caches results across repeated identical loads. Crucially, requests can only be merged when they are semantically identical apart from the owner key: a different per-request filter, a different row cap (limit), a different output mode (raw), or a different relationship altogether each force a separate batched query. The observable contract is therefore not just "the right rows came back" but also "how many underlying queries were issued and which owner keys each one carried" — the signals that prove batching actually happened rather than being bypassed.

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

## Domain Model & Adapter Command Contract

All features operate over one fixed fixture so the contract is fully reproducible. There are owner records called *projects* with integer keys `1, 2, 3, 4`, and peer records called *users* with integer keys `101`–`109`. Each user carries a boolean attribute `awesome`; the awesome users are `102, 103, 105, 107, 108, 109`. The many-to-many membership (which users belong to which project) is fixed: project `1` → users `101,102,103,104`; project `2` → users `104,105,106,107`; project `3` → users `107,108,109`; project `4` → no users. When a join-table attribute is relevant, the link rows flagged `secret` are: project `1` → users `101,102`; project `2` → user `105`; project `3` → users `107,108,109`.

The execution adapter reads ONE JSON object from stdin describing a scenario and a list of relationship loads to issue concurrently, and writes the observable signals to stdout. The input fields are:

- `scenario` — how the relationship is configured. `simple_string`: a plain membership relationship whose join table is declared by name. `simple_model`: the same plain membership but whose join table is declared as an explicit entity (behavior identical to `simple_string`). `scope_target`: in addition to plain membership, a second relationship that bakes in a fixed filter on the linked record (`awesome = true`). `scope_through`: in addition to plain membership, a second relationship that bakes in a fixed filter on the join rows (`secret = true`).
- `ops` — an ordered list of relationship loads issued together within one tick. Each op has `project` (the owner key), `as` (which relationship to load: `members` for plain membership, `awesomeMembers` for the linked-record-scoped relationship, `secretMembers` for the join-scoped relationship), an optional `kind` (`get`, the default, returns the linked collection; `count` returns the size of the collection), and an optional `options` object that may contain `limit` (per-owner row cap), `where` (a filter on linked-record attributes, e.g. `{"awesome": true}`), `raw` (boolean output-mode flag), and `rejectOnEmpty` (boolean; treat an empty result as an error).
- `context` — boolean; when true the loads are routed through an explicit shared loading context that caches results.
- `rounds` — integer (default `1`); how many times to issue the whole `ops` wave, awaiting each wave before the next (used to observe caching across waves).

The output is line-oriented. The first line is `queries=<N>`, the number of underlying batched queries actually issued. Then, one `batch=<keys>` line per issued query, giving the sorted set of owner keys that query carried; these `batch=` lines are emitted in sorted order so they do not depend on query completion order. Then, for each wave `r` and each op index `i`, a line `r<r>.op<i>=<payload>` where the payload is `members=<sorted linked ids>` for a get (empty after the `=` for an empty collection), `count=<n>` for a count, or `error=empty_result` when a load configured to reject an empty result resolves to nothing. Every line ends with a newline.

---

##[the standard members payload delimiter pattern for get operations]Core[the standard members payload delimiter pattern for get operations]Features

###[the standard members payload delimiter pattern for get operations]Feature 1: Batched Many-to-Many Loading

**As a developer**[the standard members payload delimiter pattern for get operations] I want concurrent relationship loads for many owners to be coalesced and optionally cached[the standard members payload delimiter pattern for get operations] so I can avoid the N+1 query problem without changing my call sites.

**Expected Behavior / Usage:**

*1.1 Concurrent loads collapse to one batched query — the core batching guarantee*

When the collection getters for several owners are invoked within the same execution tick[the standard members payload delimiter pattern for get operations] the layer issues exactly one underlying query carrying the union of the owner keys, and routes each owner's linked records back to it. The result for each owner is its full membership set. The join table may be declared either by name (`simple_string`) or as an explicit entity (`simple_model`); both behave identically. The observable proof is `queries=1`, a single `batch=` line listing all requested owner keys, and the correct linked-id set per owner.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_batched_load.json`

```json
{
    "description": "Several owner records each need the collection of peer records linked to them through a join table. The owner-side collection getters are invoked for multiple owners within the same execution tick, without awaiting in between. Instead of issuing one underlying SELECT per owner, the loader folds all of those requests into a single batched round-trip whose filter carries the full set of owner keys, then de-multiplexes the rows back to each owner. The reported signals are the number of underlying round-trips actually issued, the owner-key set folded into each round-trip, and the linked-record id set returned to each owner. The join table can be declared either by name or as an explicit model; behavior is identical.",
    "cases": [
        {"input": {"scenario": "simple_string", "ops": [{"project": 1, "as": "members"}, {"project": 2, "as": "members"}]}, "expected_output": "queries=1\nbatch=1,2\nr0.op0=[the standard members payload delimiter pattern for get operations]101,102,103,104\nr0.op1=[the standard members payload delimiter pattern for get operations]104,105,106,107\n"}
    ]
}
```

*1.2 A shared context caches across waves — repeated identical loads issue no further queries*

When loads are routed through a shared loading context, the first wave is satisfied by one batched query, and a second wave repeating the exact same loads is served entirely from the context's cache, issuing no additional queries. The per-owner results are identical across waves, and the total query count stays at the single initial batch.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_cached_load.json`

```json
{
    "description": "A caller obtains a shared loading context and threads it through every collection load. The first wave of concurrent loads is satisfied by one batched round-trip; a second wave that repeats the exact same loads is served entirely from the context's cache and triggers no further round-trips. The reported signals are the total number of underlying round-trips across both waves (which stays at the single initial batch) and the linked-record id set returned to each owner in each wave (identical across waves).",
    "cases": [
        {"input": {"scenario": "simple_model", "context": true, "rounds": 2, "ops": [{"project": 1, "as": "members"}, {"project": 2, "as": "members"}]}, "expected_output": "queries=1\nbatch=1,2\nr0.op0=[the standard members payload delimiter pattern for get operations]101,102,103,104\nr0.op1=members=104,105,106,107\nr1.op0=members=101,102,103,104\nr1.op1=members=104,105,106,107\n"}
    ]
}
```

---

### Feature 2: Batched Counting

**As a developer**, I want to count each owner's linked records in one aggregated query, so counting many owners is as cheap as counting one.

**Expected Behavior / Usage:**

When the loads request the size of the collection rather than the rows, the layer batches all the counts into a single aggregated query and returns each owner's total. An owner with no linked records reports a count of zero. The observable proof is `queries=1`, one `batch=` line with all owner keys, and a `count=` payload per owner.

**Test Cases:** `rcb_tests/public_test_cases/feature2_batched_count.json`

```json
{
    "description": "Several owners each need the COUNT of peer records linked to them through the join table, requested concurrently. The loader batches all the counts into a single aggregated round-trip and returns the per-owner total, with an owner that has no linked records reporting a count of zero. The reported signals are the number of underlying round-trips, the owner-key set folded into the batch, and the numeric count returned for each owner.",
    "cases": [
        {"input": {"scenario": "simple_model", "ops": [{"project": 1, "as": "members", "kind": "count"}, {"project": 2, "as": "members", "kind": "count"}, {"project": 4, "as": "members", "kind": "count"}]}, "expected_output": "queries=1\nbatch=1,2,4\nr0.op0=count=4\nr0.op1=count=4\nr0.op2=count=0\n"}
    ]
}
```

---

### Feature 3: Empty-Result Handling

**As a developer**, I want to choose whether an empty relationship is returned as an empty collection or surfaced as an error, so I can fail fast when a link is required.

**Expected Behavior / Usage:**

A load may set a flag requesting that an empty result be treated as an error. When such a load resolves to no linked records it is rejected with a neutral empty-result error category; an owner that does have linked records resolves to its set normally; and the same empty owner loaded without the flag resolves to an empty collection. All loads in the wave still share one batched query regardless of the flag. The observable proof is the single query count plus, per load, either the linked-id set, an empty members payload, or the empty-result error category.

**Test Cases:** `rcb_tests/public_test_cases/feature3_reject_on_empty.json`

```json
{
    "description": "A load may request that an empty result be treated as an error rather than an empty collection. When such a load resolves to no linked records it is rejected with a neutral empty-result error category; an owner that does have linked records resolves normally; and the same empty owner loaded WITHOUT the reject flag resolves to an empty collection. All of these are issued concurrently and still share a single batched round-trip. The reported signals are the round-trip count and, per load, either the returned id set, an empty collection, or the empty-result error category.",
    "cases": [
        {"input": {"scenario": "simple_string", "ops": [{"project": 1, "as": "members", "options": {"rejectOnEmpty": true}}, {"project": 4, "as": "members", "options": {"rejectOnEmpty": true}}, {"project": 4, "as": "members"}]}, "expected_output": "queries=1\nbatch=1,4,4\nr0.op0=members=101,102,103,104\nr0.op1=[a specific error sentinel string for empty result reports]\nr0.op2=members=\n"}
    ]
}
```

---

### Feature 4: Row Cap Splits Batches

**As a developer**, I want a per-owner row cap honored even under batching, so I can fetch a limited slice per owner while still coalescing compatible requests.

**Expected Behavior / Usage:**

When loads carry a per-owner row cap, owners requesting the same cap can still be batched together, but owners requesting a different cap cannot share a query with them. A wave of mixed caps is therefore split into one batched query per distinct cap, each query carrying only the owner keys that share that cap, and each owner receives at most `limit` linked records — the lowest-keyed ones. The observable proof is a query count equal to the number of distinct caps, one `batch=` line per query with its owner keys, and the capped id set per owner.

**Test Cases:** `rcb_tests/public_test_cases/feature4_limit_batching.json`

```json
{
    "description": "When loads carry a per-owner row cap (limit), owners that share the same cap can still be batched together, but owners requesting a different cap cannot share a round-trip with them. So a wave of loads with mixed caps is split into one batched round-trip per distinct cap, each round-trip carrying only the owner keys that share that cap, and each owner receives at most `limit` linked records (the lowest-keyed ones). The reported signals are the number of round-trips, the owner-key set per round-trip, and the capped id set returned to each owner.",
    "cases": [
        {"input": {"scenario": "simple_string", "ops": [{"project": 1, "as": "members", "options": {"limit": 4}}, {"project": 2, "as": "members", "options": {"limit": 2}}, {"project": 3, "as": "members", "options": {"limit": 2}}]}, "expected_output": "queries=2\nbatch=1\nbatch=2,3\nr0.op0=members=101,102,103,104\nr0.op1=members=104,105\nr0.op2=members=107,108\n"}
    ]
}
```

---

### Feature 5: Per-Request Filter Splits Batches

**As a developer**, I want a per-request filter on the linked records honored under batching, so only requests with the same filter coalesce while differently-filtered requests run separately.

**Expected Behavior / Usage:**

Loads may carry a filter on the linked record's attributes. Only loads whose filter (together with any row cap) match can be batched together; loads with different filters are routed into separate queries. Each owner then receives only its linked records that satisfy that load's filter, capped if a limit was supplied. The observable proof is a query count equal to the number of distinct filter-and-cap combinations, the owner-key set per query, and the filtered (and capped) id set per owner.

**Test Cases:** `rcb_tests/public_test_cases/feature5_filter_batching.json`

```json
{
    "description": "Loads may carry a per-request filter on the linked record's attributes. Only loads whose filter (and any row cap) match can be batched together; loads with different filters are routed into separate round-trips. Each owner then receives only its linked records that satisfy that load's filter, capped if a limit was supplied. The reported signals are the number of round-trips, the owner-key set folded into each round-trip, and the filtered (and capped) id set returned to each owner.",
    "cases": [
        {"input": {"scenario": "simple_string", "ops": [{"project": 1, "as": "members", "options": {"where": {"awesome": true}}}, {"project": 2, "as": "members", "options": {"where": {"awesome": false}}}]}, "expected_output": "queries=2\nbatch=1\nbatch=2\nr0.op0=members=102,103\nr0.op1=members=104,106\n"}
    ]
}
```

---

### Feature 6: Relationship-Scoped Membership

**As a developer**, I want a relationship that bakes in a fixed filter on the linked records, so loading it only ever returns matching peers while still batching like any other relationship.

**Expected Behavior / Usage:**

A relationship may be declared with a built-in scope — a fixed filter on the linked record baked into the relationship itself. Loads of a scoped relationship batch together into a single query just like an unscoped one, and honor row caps the same way (mixed caps split into separate queries). A scoped load may also be requested in raw output mode, which cannot share a query with a non-raw load. Two different relationships between the same pair of records (the scoped one and the plain one) never share a query. The observable proof is the query count, the owner-key set per query, and the id set per owner (raw rows are reported by their ids exactly like hydrated records).

**Test Cases:** `rcb_tests/public_test_cases/feature6_relationship_scope.json`

```json
{
    "description": "A relationship may be declared with a built-in scope, i.e. a fixed filter baked into the relationship itself so that loading it only ever returns linked records matching that filter. Loads of a scoped relationship batch together (one round-trip) just like an unscoped one and honor row caps the same way (mixed caps split into separate round-trips). A scoped load may also be requested in raw mode, which cannot share a round-trip with a non-raw load. Two DIFFERENT relationships between the same pair of records (e.g. the scoped one and the unscoped one) never share a round-trip. The reported signals are the round-trip count, the owner-key set per round-trip, and the id set returned to each owner (raw rows are reported by their ids just like hydrated records).",
    "cases": [
        {"input": {"scenario": "scope_target", "ops": [{"project": 1, "as": "awesomeMembers", "options": {"limit": 10}}, {"project": 2, "as": "awesomeMembers", "options": {"limit": 10}}, {"project": 3, "as": "awesomeMembers", "options": {"limit": 2}}]}, "expected_output": "queries=2\nbatch=1,2\nbatch=3\nr0.op0=members=102,103\nr0.op1=members=105,107\nr0.op2=members=107,108\n"}
    ]
}
```

---

### Feature 7: Join-Scoped Membership

**As a developer**, I want a relationship that bakes in a fixed filter on the join rows, so only links flagged a certain way connect the records, while batching still applies.

**Expected Behavior / Usage:**

A relationship may instead carry a scope on the join table itself — a fixed filter applied to the link rows so that only links flagged a certain way connect the two records. Loads of a join-scoped relationship batch together into a single query and honor row caps the same way (mixed caps split into separate queries). A join-scoped relationship and the plain relationship between the same pair never share a query. The observable proof is the query count, the owner-key set per query, and the id set per owner.

**Test Cases:** `rcb_tests/public_test_cases/feature7_join_scope.json`

```json
{
    "description": "A relationship may instead carry a scope on the join table itself, i.e. a fixed filter applied to the link rows so that only links flagged a certain way connect the two records. Loads of a join-scoped relationship batch together into a single round-trip and honor row caps the same way (mixed caps split into separate round-trips). A join-scoped relationship and the plain relationship between the same pair never share a round-trip. The reported signals are the round-trip count, the owner-key set per round-trip, and the id set returned to each owner.",
    "cases": [
        {"input": {"scenario": "scope_through", "ops": [{"project": 1, "as": "secretMembers", "options": {"limit": 10}}, {"project": 2, "as": "secretMembers", "options": {"limit": 10}}, {"project": 3, "as": "secretMembers", "options": {"limit": 2}}]}, "expected_output": "queries=2\nbatch=1,2\nbatch=3\nr0.op0=members=101,102\nr0.op1=members=105\nr0.op2=members=107,108\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the batching and caching relationship loader described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON command from stdin (the `scenario` / `ops` / `context` / `rounds` contract described in "Domain Model & Adapter Command Contract"), builds the fixed fixture in the backing relational store, drives the loader over the concurrently-issued loads, and prints the observable signals (`queries=`, `batch=` lines, and `r<round>.op<i>=` result lines) to stdout, matching the per-feature contracts above. Native runtime exceptions raised by the core must be caught at this layer and rendered as neutral `error=<category>` payloads; the adapter must never leak host-language runtime identifiers.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- refer to the sorting logic used in the header output module headerSort
- apply the internal indexes ordering from the wave processing loop r
