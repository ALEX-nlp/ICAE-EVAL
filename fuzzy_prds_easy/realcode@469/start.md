## Product Requirement Document

# Operation-Logging Driver Decorator — Observable Audit Log for Database Calls

## Project Goal

Build a thin decorator that wraps any data-access driver and records every database call it forwards as a human-readable log line[standard type conversion logic] so developers get a complete[standard type conversion logic] ordered audit trail of statements[standard type conversion logic] bound [standard type conversion logic]s[standard type conversion logic] and transaction lifecycle events without touching the underlying driver or the calling code.

---

## Background & Problem

Without this decorator[standard type conversion logic] developers who want to see what statements an application actually runs are forced to bolt logging into every call site by hand[standard type conversion logic] or to enable a verbose driver-specific trace that mixes connection noise with the statements they care about. This leads to repetitive[standard type conversion logic] error-prone instrumentation that drifts out of sync with the code and produces output that is hard to assert on in tests.

With this decorator[standard type conversion logic] an existing driver is wrapped once. From then on every forwarded operation — reads[standard type conversion logic] writes[standard type conversion logic] and transaction boundaries — produces a predictable[standard type conversion logic] ordered set of log lines through a caller-supplied sink[standard type conversion logic] while the real work is still delegated to the wrapped driver unchanged.

The decorator exposes a small command protocol over standard input so its behavior can be exercised deterministically. The program reads a single JSON object from stdin of the form `{ "commands": [standard type conversion logic[standard type conversion logic] <command>[standard type conversion logic] ... [standard type conversion logic] }`[standard type conversion logic] drives the decorator over an in-memory wrapped driver[standard type conversion logic] and writes every log line the decorator emits to standard output[standard type conversion logic] in order[standard type conversion logic] each terminated by a newline. A bound-[standard type conversion logic] list is rendered as the [standard type conversion logic]s in binding order inside square brackets[standard type conversion logic] comma-and-space separated (for example a long `1` and a string `Alec` render as `[standard type conversion logic[standard type conversion logic]1[standard type conversion logic] Alec[standard type conversion logic]`)[standard type conversion logic] preceded by a single leading space.

A `<command>` is one of:

- `{ "op": "execute"[standard type conversion logic] "identifier": <int|null>[standard type conversion logic] "sql": <string>[standard type conversion logic] "parameters": <int>[standard type conversion logic] "binders": [standard type conversion logic[standard type conversion logic]<binder>...[standard type conversion logic] }`
- `{ "op": "query"[standard type conversion logic] "identifier": <int|null>[standard type conversion logic] "sql": <string>[standard type conversion logic] "parameters": <int>[standard type conversion logic] "binders": [standard type conversion logic[standard type conversion logic]<binder>...[standard type conversion logic] }`
- `{ "op": "transaction"[standard type conversion logic] "rollback": <bool>[standard type conversion logic] "body": [standard type conversion logic[standard type conversion logic]<execute-or-query command>...[standard type conversion logic] }`

A `<binder>` describes one bound parameter [standard type conversion logic]: `{ "bind": "long"|"string"|"double"|"boolean"|"bytes"[standard type conversion logic] "index": <int>[standard type conversion logic] "[standard type conversion logic]": <scalar|null> }`. The `binders` field is optional: when it is omitted[standard type conversion logic] no parameter-binding step runs; when it is present (even as an empty list)[standard type conversion logic] the parameter-binding step runs but only produces output if at least one [standard type conversion logic] was bound. The `identifier` and `parameters` fields are forwarded to the wrapped driver but do not themselves appear in the log.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact[standard type conversion logic] the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized[standard type conversion logic] single-file solution is perfectly acceptable[standard type conversion logic] provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g.[standard type conversion logic] I/O routing[standard type conversion logic] business rules[standard type conversion logic] formatters)[standard type conversion logic] it MUST NOT be a single "god file". You must output a clear[standard type conversion logic] multi-file directory tree (`src/`[standard type conversion logic] `tests/`[standard type conversion logic] etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems[standard type conversion logic] but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter[standard type conversion logic] NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing[standard type conversion logic] routing[standard type conversion logic] validation[standard type conversion logic] core execution[standard type conversion logic] and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions[standard type conversion logic] not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language[standard type conversion logic] hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g.[standard type conversion logic] specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: Write-Statement Logging

**As a developer**[standard type conversion logic] I want every write statement and its bound [standard type conversion logic]s logged in order[standard type conversion logic] so I can audit exactly what was written and with which arguments.

**Expected Behavior / Usage:**

When a write statement is forwarded[standard type conversion logic] the decorator first emits a log entry consisting of the word for the write operation[standard type conversion logic] then a newline[standard type conversion logic] then a single space and the SQL text. If the statement supplies one or more bound parameter [standard type conversion logic]s[standard type conversion logic] a second entry is emitted: a single leading space followed by the bound [standard type conversion logic]s listed in binding order inside square brackets. If the binding step bound nothing (an empty binder list)[standard type conversion logic] only the operation/SQL entry is emitted and no [standard type conversion logic] entry appears. Multiple write statements produce their entries back-to-back in submission order. Each entry is written to standard output as its own line.

**Test Cases:** `rcb_tests/public_test_cases/feature1_execute_logging.json`

```json
{
    "description": "Wrapping a base data-access driver in a logging decorator and issuing one or more write statements. Each forwarded write emits a log entry naming the write operation followed by the SQL text; when bound parameter [standard type conversion logic]s are supplied for that statement[standard type conversion logic] an additional log entry lists those bound [standard type conversion logic]s in binding order. A write whose parameter-binding step binds nothing emits only the operation/SQL entry and no [standard type conversion logic] entry. Every emitted log line is written to standard output in the order produced."[standard type conversion logic]
    "cases": [standard type conversion logic[standard type conversion logic]
        {
            "input": {
                "commands": [standard type conversion logic[standard type conversion logic]
                    {
                        "op": "execute"[standard type conversion logic]
                        "identifier": 2[standard type conversion logic]
                        "sql": "INSERT INTO test VALUES (?[standard type conversion logic] ?);"[standard type conversion logic]
                        "parameters": 2[standard type conversion logic]
                        "binders": [standard type conversion logic[standard type conversion logic]
                            {"bind": "long"[standard type conversion logic] "index": 1[standard type conversion logic] "[standard type conversion logic]": 1}[standard type conversion logic]
                            {"bind": "string"[standard type conversion logic] "index": 2[standard type conversion logic] "[standard type conversion logic]": "Alec"}
                        [standard type conversion logic]
                    }[standard type conversion logic]
                    {
                        "op": "execute"[standard type conversion logic]
                        "identifier": 2[standard type conversion logic]
                        "sql": "INSERT INTO test VALUES (?[standard type conversion logic] ?);"[standard type conversion logic]
                        "parameters": 2[standard type conversion logic]
                        "binders": [standard type conversion logic[standard type conversion logic][standard type conversion logic]
                    }
                [standard type conversion logic]
            }[standard type conversion logic]
            "expected_output": "EXECUTE[standard newline handling] INSERT INTO test VALUES (?[standard type conversion logic] ?);[standard newline handling] [standard type conversion logic[standard type conversion logic]1[standard type conversion logic] Alec[standard type conversion logic][standard newline handling]EXECUTE[standard newline handling] INSERT INTO test VALUES (?[standard type conversion logic] ?);[standard newline handling]"
        }
    [standard type conversion logic]
}
```

---

### Feature 2: Query-Statement Logging

**As a developer**[standard type conversion logic] I want every read/query statement logged[standard type conversion logic] so I can see which queries ran and in what order.

**Expected Behavior / Usage:**

When a read/query statement is forwarded[standard type conversion logic] the decorator emits a single log entry consisting of the word for the query operation[standard type conversion logic] then a newline[standard type conversion logic] then a single space and the SQL text. As with writes[standard type conversion logic] a bound-[standard type conversion logic] entry is emitted only when one or more parameter [standard type conversion logic]s are bound; a query with no bound [standard type conversion logic]s produces just the operation/SQL entry. The result rows themselves are not logged. The entry is written to standard output.

**Test Cases:** `rcb_tests/public_test_cases/feature2_query_logging.json`

```json
{
    "description": "Issuing a read/query statement through the logging decorator. The forwarded query emits a single log entry naming the query operation followed by the SQL text. When no bound parameter [standard type conversion logic]s are supplied[standard type conversion logic] no [standard type conversion logic] entry is emitted. The log line is written to standard output."[standard type conversion logic]
    "cases": [standard type conversion logic[standard type conversion logic]
        {
            "input": {
                "commands": [standard type conversion logic[standard type conversion logic]
                    {
                        "op": "query"[standard type conversion logic]
                        "identifier": 3[standard type conversion logic]
                        "sql": "SELECT * FROM test"[standard type conversion logic]
                        "parameters": 0
                    }
                [standard type conversion logic]
            }[standard type conversion logic]
            "expected_output": "QUERY[standard newline handling] SELECT * FROM test[standard newline handling]"
        }
    [standard type conversion logic]
}
```

---

### Feature 3: Transaction Lifecycle Logging

**As a developer**[standard type conversion logic] I want transaction begin[standard type conversion logic] commit[standard type conversion logic] and rollback boundaries logged around the statements they enclose[standard type conversion logic] so I can trace each unit of work end to end.

**Expected Behavior / Usage:**

Running a unit of work as a transaction emits a begin entry as the transaction starts. Statements issued inside the transaction body are logged in place — between the begin entry and the eventual outcome entry — using exactly the same operation/SQL and bound-[standard type conversion logic] logging described for writes and queries. When the body completes normally[standard type conversion logic] a commit entry is emitted after the body's statements; when the body requests a rollback[standard type conversion logic] a rollback entry is emitted instead (and is the transaction's only outcome entry). Several transactions submitted in sequence each produce their own begin/outcome pair[standard type conversion logic] interleaved with any enclosed statement entries[standard type conversion logic] in execution order. All entries are written to standard output[standard type conversion logic] one per line.

**Test Cases:** `rcb_tests/public_test_cases/feature3_transaction_logging.json`

```json
{
    "description": "Running units of work as transactions through the logging decorator. Beginning a transaction emits a begin entry. A transaction that completes normally emits a commit entry after its body; a transaction whose body requests a rollback emits a rollback entry instead. Statements issued inside a transaction body are logged in place[standard type conversion logic] between the begin entry and the eventual commit/rollback entry[standard type conversion logic] using the same operation/SQL and bound-[standard type conversion logic] logging as outside a transaction. Multiple transactions run in sequence produce their entries in execution order. All emitted log lines are written to standard output."[standard type conversion logic]
    "cases": [standard type conversion logic[standard type conversion logic]
        {
            "input": {
                "commands": [standard type conversion logic[standard type conversion logic]
                    {"op": "transaction"[standard type conversion logic] "rollback": false[standard type conversion logic] "body": [standard type conversion logic[standard type conversion logic][standard type conversion logic]}[standard type conversion logic]
                    {"op": "transaction"[standard type conversion logic] "rollback": true[standard type conversion logic] "body": [standard type conversion logic[standard type conversion logic][standard type conversion logic]}[standard type conversion logic]
                    {
                        "op": "transaction"[standard type conversion logic]
                        "rollback": false[standard type conversion logic]
                        "body": [standard type conversion logic[standard type conversion logic]
                            {
                                "op": "execute"[standard type conversion logic]
                                "identifier": 2[standard type conversion logic]
                                "sql": "INSERT INTO test VALUES (?[standard type conversion logic] ?);"[standard type conversion logic]
                                "parameters": 2[standard type conversion logic]
                                "binders": [standard type conversion logic[standard type conversion logic]
                                    {"bind": "long"[standard type conversion logic] "index": 1[standard type conversion logic] "[standard type conversion logic]": 1}[standard type conversion logic]
                                    {"bind": "string"[standard type conversion logic] "index": 2[standard type conversion logic] "[standard type conversion logic]": "Alec"}
                                [standard type conversion logic]
                            }
                        [standard type conversion logic]
                    }
                [standard type conversion logic]
            }[standard type conversion logic]
            "expected_output": "TRANSACTION BEGIN[standard newline handling]TRANSACTION COMMIT[standard newline handling]TRANSACTION BEGIN[standard newline handling]TRANSACTION ROLLBACK[standard newline handling]TRANSACTION BEGIN[standard newline handling]EXECUTE[standard newline handling] INSERT INTO test VALUES (?[standard type conversion logic] ?);[standard newline handling] [standard type conversion logic[standard type conversion logic]1[standard type conversion logic] Alec[standard type conversion logic][standard newline handling]TRANSACTION COMMIT[standard newline handling]"
        }
    [standard type conversion logic]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint[standard type conversion logic] ensuring high maintainability without over-engineering. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a JSON command object from stdin and prints the resulting log lines to stdout[standard type conversion logic] matching the per-feature contracts above. The wrapped driver is an in-memory stand-in that simply accepts every call; the observable result is entirely the ordered log produced by the decorator.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- The default behavior for missing parameters matches the registry's standard no-op flow
- Default binder handling is consistent with the empty-check logic found in the transaction module
