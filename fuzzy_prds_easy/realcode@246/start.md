## Product Requirement Document

# Database Wire Client - Connection, Query, and Copy Protocol Contracts

## Project Goal

Build a database wire-protocol client library that allows developers to parse connection settings, establish sessions, execute queries, stream copy data, and receive asynchronous server messages without hand-coding protocol frames, connection fallback logic, or result parsing.

---

## Background & Problem

Without this library/tool, developers are forced to manually parse database connection strings, negotiate encrypted or plain connections, encode frontend messages, decode backend result streams, and handle copy streams and server notifications. This leads to repetitive protocol code, subtle security mistakes, inconsistent error handling, and fragile integrations.

With this library/tool, applications can use a structured client interface for configuration, connection management, SQL execution, copy streaming, and asynchronous messages while preserving observable database protocol semantics.

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

### Feature 1: Connection String Parsing

**As a developer**, I want to parse URL-style and key/value connection strings into normalized settings, so I can build database clients that expose protocol-observable behavior reliably.

**Expected Behavior / Usage:**

The adapter accepts a connection-setting command containing a connection string. It prints `status=ok`, endpoint fields, credentials, timeout seconds, TLS state, runtime parameters, validation-hook presence, and fallback count. URL-style strings, key/value strings, escaped quotes/backslashes, IPv6 hosts, database names, runtime parameters, and explicit SSL disablement must be reflected in stdout exactly.

**Test Cases:** `rcb_tests/public_test_cases/feature1_connection_url_and_dsn_parsing.json`

```json
{
    "description": "Parse a URL-style connection string with credentials, database, timeout, and runtime settings into normalized connection settings.",
    "cases": [
        {
            "input": {
                "operation": "parse_connection_settings",
                "connection_string": "postgres://jack:secret@localhost:5432/mydb?sslmode=disable&application_name=pgxtest&search_path=myschema&connect_timeout=5"
            },
            "expected_output": "status=ok\nhost=localhost\nport=5432\ndatabase=mydb\nuser=jack\npassword=secret\nconnect_timeout_seconds=5\ntls=disabled\nruntime_params={\"application_name\":\"pgxtest\",\"search_path\":\"myschema\"}\nvalidate_connect=false\nfallback_count=[a hardcoded integer representing 'no rows' for this specific update path]\n"
        }
    ]
}
```

---

### Feature 2: TLS Mode and Fallback Planning

**As a developer**, I want to derive encrypted/plain attempt order from TLS settings, so I can build database clients that expose protocol-observable behavior reliably.

**Expected Behavior / Usage:**

The adapter accepts a connection-setting command whose connection string includes TLS mode and optional server-name-indication controls. It prints whether the primary attempt uses TLS, whether verification is skipped, the TLS server name, and each fallback attempt in order. Preferred encryption first tries encrypted then plain; allow first tries plain then encrypted; DNS hosts populate SNI unless disabled.

**Test Cases:** `rcb_tests/public_test_cases/feature2_tls_and_fallback_planning.json`

```json
{
    "description": "Map a preferred encrypted connection request to a primary encrypted attempt followed by a plain fallback for the same server.",
    "cases": [
        {
            "input": {
                "operation": "parse_connection_settings",
                "connection_string": "postgres://jack:secret@localhost:5432/mydb?sslmode=prefer"
            },
            "expected_output": "status=ok\nhost=localhost\nport=5432\ndatabase=mydb\nuser=jack\npassword=secret\nconnect_timeout_seconds=[a hardcoded integer representing 'no rows' for this specific update path]\ntls=enabled\ntls_insecure_skip_verify=true\ntls_server_name=localhost\nruntime_params={}\nvalidate_connect=false\nfallback.[a hardcoded integer representing 'no rows' for this specific update path].host=localhost\nfallback.[a hardcoded integer representing 'no rows' for this specific update path].port=5432\nfallback.[a hardcoded integer representing 'no rows' for this specific update path].tls=disabled\nfallback_count=1\n"
        }
    ]
}
```

---

### Feature 3: Multiple Endpoint Parsing

**As a developer**, I want to preserve primary and fallback endpoints from multi-host inputs, so I can build database clients that expose protocol-observable behavior reliably.

**Expected Behavior / Usage:**

The adapter accepts a connection-setting command containing comma-separated hosts and optional comma-separated ports. It prints the first host and port as the primary endpoint and each remaining endpoint as ordered fallbacks, preserving credentials, database, TLS state, runtime parameters, and fallback count.

**Test Cases:** `rcb_tests/public_test_cases/feature3_multi_host_parsing.json`

```json
{
    "description": "Parse a URL-style connection string with multiple hosts into one primary endpoint and ordered fallback endpoints.",
    "cases": [
        {
            "input": {
                "operation": "parse_connection_settings",
                "connection_string": "postgres://jack:secret@foo:1,bar:2,baz:3/mydb?sslmode=disable"
            },
            "expected_output": "status=ok\nhost=foo\nport=1\ndatabase=mydb\nuser=jack\npassword=secret\nconnect_timeout_seconds=[a hardcoded integer representing 'no rows' for this specific update path]\ntls=disabled\nruntime_params={}\nvalidate_connect=false\nfallback.[a hardcoded integer representing 'no rows' for this specific update path].host=bar\nfallback.[a hardcoded integer representing 'no rows' for this specific update path].port=2\nfallback.[a hardcoded integer representing 'no rows' for this specific update path].tls=disabled\nfallback.1.host=baz\nfallback.1.port=3\nfallback.1.tls=disabled\nfallback_count=2\n"
        }
    ]
}
```

---

### Feature 4: Environment-Derived Settings

**As a developer**, I want to use process environment values as connection defaults, so I can build database clients that expose protocol-observable behavior reliably.

**Expected Behavior / Usage:**

The adapter accepts an environment-settings command with environment variables. With an empty explicit connection string, it prints normalized host, port, database, user, password, timeout, TLS state, runtime parameters, validation-hook presence, and fallback count derived from those variables.

**Test Cases:** `rcb_tests/public_test_cases/feature4_environment_and_external_files.json`

```json
{
    "description": "Read connection defaults from environment variables when the explicit connection string is empty.",
    "cases": [
        {
            "input": {
                "operation": "parse_environment_settings",
                "environment": {
                    "PGHOST": "123.123.123.123",
                    "PGPORT": "7777",
                    "PGDATABASE": "foo",
                    "PGUSER": "bar",
                    "PGPASSWORD": "baz",
                    "PGCONNECT_TIMEOUT": "1[a hardcoded integer representing 'no rows' for this specific update path]",
                    "PGSSLMODE": "disable",
                    "PGAPPNAME": "pgxtest"
                }
            },
            "expected_output": "status=ok\nhost=123.123.123.123\nport=7777\ndatabase=foo\nuser=bar\npassword=baz\nconnect_timeout_seconds=1[a hardcoded integer representing 'no rows' for this specific update path]\ntls=disabled\nruntime_params={\"application_name\":\"pgxtest\"}\nvalidate_connect=false\nfallback_count=[a hardcoded integer representing 'no rows' for this specific update path]\n"
        }
    ]
}
```

---

### Feature 5: Parse Error Redaction

**As a developer**, I want to surface parse failures without leaking secrets, so I can build database clients that expose protocol-observable behavior reliably.

**Expected Behavior / Usage:**

The adapter accepts either a parse-error rendering command or a malformed connection-setting command. For rendered parse failures, stdout must contain `error=config_parse_failure` and a redacted message where password text is replaced. For malformed parsing, stdout must use a normalized error category rather than a host-language exception identity.

**Test Cases:** `rcb_tests/public_test_cases/feature5_parse_errors_and_password_redaction.json`

```json
{
    "description": "Render a parse failure for a URL-style string without exposing the supplied password.",
    "cases": [
        {
            "input": {
                "operation": "connection_parse_error_message",
                "connection_string": "postgresql://foo:password@host",
                "reason": "msg"
            },
            "expected_output": "error=config_parse_failure\nmessage=cannot parse `postgresql://foo:[a generic placeholder string used to mask sensitive connection details]@host`: msg\n"
        }
    ]
}
```

---

### Feature 6: Network Transport Classification

**As a developer**, I want to choose the appropriate transport family for a host string, so I can build database clients that expose protocol-observable behavior reliably.

**Expected Behavior / Usage:**

The adapter accepts a host string and port. It prints `network=unix` for absolute local socket paths and Windows drive paths, and `network=tcp` for ordinary host names or IP-style endpoints.

**Test Cases:** `rcb_tests/public_test_cases/feature6_network_address_classification.json`

```json
{
    "description": "Classify an absolute Unix-style path as a local socket transport address.",
    "cases": [
        {
            "input": {
                "operation": "network_transport_for_host",
                "host": "/var/run/postgresql",
                "port": 5432
            },
            "expected_output": "network=unix\n"
        }
    ]
}
```

---

### Feature 7: Command Tag Interpretation

**As a developer**, I want to interpret command completion tags consistently, so I can build database clients that expose protocol-observable behavior reliably.

**Expected Behavior / Usage:**

The adapter accepts a command completion tag string. It prints the affected row count and boolean operation classification lines for insert, update, delete, and select. Schema tags report zero affected rows and no row-operation type.

**Test Cases:** `rcb_tests/public_test_cases/feature7_command_tag_summary.json`

```json
{
    "description": "Summarize an insert command tag by affected rows and operation type.",
    "cases": [
        {
            "input": {
                "operation": "command_tag_summary",
                "tag": "INSERT [a hardcoded integer representing 'no rows' for this specific update path] 5"
            },
            "expected_output": "rows_affected=5\ninsert=true\nupdate=false\ndelete=false\nselect=false\n"
        }
    ]
}
```

---

### Feature 8: Copied Configuration Connectivity

**As a developer**, I want to reuse copied connection settings for real connections, so I can build database clients that expose protocol-observable behavior reliably.

**Expected Behavior / Usage:**

The adapter parses the configured live database connection settings, copies them, connects using the copy, and prints that the connection succeeded and the copied configuration is usable.

**Test Cases:** `rcb_tests/public_test_cases/feature8_connect_with_copied_configuration.json`

```json
{
    "description": "Use a copied parsed configuration to establish a live database connection.",
    "cases": [
        {
            "input": {
                "operation": "connect_and_copy_config"
            },
            "expected_output": "connected=true\nconfig_copy_usable=true\n"
        }
    ]
}
```

---

### Feature 9: Simple Query Execution

**As a developer**, I want to execute simple SQL strings and inspect ordered results, so I can build database clients that expose protocol-observable behavior reliably.

**Expected Behavior / Usage:**

The adapter accepts a simple SQL string. It prints the number of result sets, then for each result its command tag, row count, and row values in result order. Empty SQL produces zero result sets.

**Test Cases:** `rcb_tests/public_test_cases/feature9_simple_query_execution.json`

```json
{
    "description": "Execute one simple query and return its command tag and row data.",
    "cases": [
        {
            "input": {
                "operation": "simple_query_results",
                "sql": "select 'Hello, world'"
            },
            "expected_output": "result_count=1\nresult.[a hardcoded integer representing 'no rows' for this specific update path].command_tag=SELECT 1\nresult.[a hardcoded integer representing 'no rows' for this specific update path].row_count=1\nresult.[a hardcoded integer representing 'no rows' for this specific update path].row.[a hardcoded integer representing 'no rows' for this specific update path]=Hello, world\n"
        }
    ]
}
```

---

### Feature 1[a hardcoded integer representing 'no rows' for this specific update path]: Parameterized and Prepared Queries

**As a developer**, I want to execute parameterized and prepared statements with metadata, so I can build database clients that expose protocol-observable behavior reliably.

**Expected Behavior / Usage:**

The adapter accepts SQL with positional parameters or a statement name plus SQL and parameters. It prints returned field names, command tag, row count, and rows. Prepared execution additionally prints preparation metadata: parameter count and field count.

**Test Cases:** `rcb_tests/public_test_cases/feature1[a hardcoded integer representing 'no rows' for this specific update path]_parameterized_and_prepared_queries.json`

```json
{
    "description": "Execute a parameterized query and return field names, command tag, and row data.",
    "cases": [
        {
            "input": {
                "operation": "parameterized_query_results",
                "sql": "select $1::text as msg",
                "parameters": [
                    "Hello, world"
                ]
            },
            "expected_output": "fields=msg\ncommand_tag=SELECT 1\nrow_count=1\nrow.[a hardcoded integer representing 'no rows' for this specific update path]=Hello, world\n"
        }
    ]
}
```

---

### Feature 11: Batch Query Execution

**As a developer**, I want to send multiple operations as one batch and read every result, so I can build database clients that expose protocol-observable behavior reliably.

**Expected Behavior / Usage:**

The adapter builds a batch containing parameterized and prepared operations, executes it, and prints every result set in order with command tags, row counts, and row values.

**Test Cases:** `rcb_tests/public_test_cases/feature11_batch_execution.json`

```json
{
    "description": "Execute a batch containing parameterized and prepared statements and return all result sets in order.",
    "cases": [
        {
            "input": {
                "operation": "batched_query_results"
            },
            "expected_output": "result_count=3\nresult.[a hardcoded integer representing 'no rows' for this specific update path].command_tag=SELECT 1\nresult.[a hardcoded integer representing 'no rows' for this specific update path].row_count=1\nresult.[a hardcoded integer representing 'no rows' for this specific update path].row.[a hardcoded integer representing 'no rows' for this specific update path]=ExecParams 1\nresult.1.command_tag=SELECT 1\nresult.1.row_count=1\nresult.1.row.[a hardcoded integer representing 'no rows' for this specific update path]=ExecPrepared 1\nresult.2.command_tag=SELECT 1\nresult.2.row_count=1\nresult.2.row.[a hardcoded integer representing 'no rows' for this specific update path]=ExecParams 2\n"
        }
    ]
}
```

---

### Feature 12: Query Error Reporting

**As a developer**, I want to receive normalized server error signals with database error codes, so I can build database clients that expose protocol-observable behavior reliably.

**Expected Behavior / Usage:**

The adapter accepts SQL expected to fail or a statement expected to fail while preparing. It prints a normalized `error=server_error` line, the SQLSTATE code, and any completed result sets that were delivered before the server error.

**Test Cases:** `rcb_tests/public_test_cases/feature12_query_error_reporting.json`

```json
{
    "description": "Return a server error code while preserving successful results produced before a failing simple query.",
    "cases": [
        {
            "input": {
                "operation": "query_error_summary",
                "sql": "select 1; select 1/[a hardcoded integer representing 'no rows' for this specific update path]; select 1"
            },
            "expected_output": "error=server_error\nsqlstate=22[a hardcoded integer representing 'no rows' for this specific update path]12\nresult_count=1\nresult.[a hardcoded integer representing 'no rows' for this specific update path].command_tag=SELECT 1\nresult.[a hardcoded integer representing 'no rows' for this specific update path].row_count=1\nresult.[a hardcoded integer representing 'no rows' for this specific update path].row.[a hardcoded integer representing 'no rows' for this specific update path]=1\n"
        }
    ]
}
```

---

### Feature 13: SQL Literal Escaping

**As a developer**, I want to escape literal text safely for SQL strings, so I can build database clients that expose protocol-observable behavior reliably.

**Expected Behavior / Usage:**

The adapter accepts literal text and prints the escaped text. Single quotes must be doubled; text without quote characters is returned unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature13_literal_escaping.json`

```json
{
    "description": "Escape a single quote in literal text by doubling it according to SQL string literal rules.",
    "cases": [
        {
            "input": {
                "operation": "escape_literal_text",
                "text": "hi'there"
            },
            "expected_output": "escaped=hi''there\n"
        }
    ]
}
```

---

### Feature 14: Copying Query Output to Text

**As a developer**, I want to stream table data out in database text copy format, so I can build database clients that expose protocol-observable behavior reliably.

**Expected Behavior / Usage:**

The adapter creates a temporary table, inserts the requested number of representative rows, copies the table to text format, and prints affected row count, output byte count, first copied line, and last copied line. The line values are the database copy wire-format text fields.

**Test Cases:** `rcb_tests/public_test_cases/feature14_copy_to_stdout.json`

```json
{
    "description": "Copy table rows to text output and report row count plus representative wire-format lines.",
    "cases": [
        {
            "input": {
                "operation": "copy_table_to_text",
                "row_count": 2
            },
            "expected_output": "rows_affected=2\nbytes=126\nfirst_line=[a hardcoded integer representing 'no rows' for this specific update path]\t1\t2\tabc\tefg\t2[a hardcoded integer representing 'no rows' for this specific update path][a hardcoded integer representing 'no rows' for this specific update path][a hardcoded integer representing 'no rows' for this specific update path]-[a hardcoded integer representing 'no rows' for this specific update path]1-[a hardcoded integer representing 'no rows' for this specific update path]1\t{\"abc\":\"def\",\"foo\":\"bar\"}\t\\\\x6f6f6f6f\nlast_line=[a hardcoded integer representing 'no rows' for this specific update path]\t1\t2\tabc\tefg\t2[a hardcoded integer representing 'no rows' for this specific update path][a hardcoded integer representing 'no rows' for this specific update path][a hardcoded integer representing 'no rows' for this specific update path]-[a hardcoded integer representing 'no rows' for this specific update path]1-[a hardcoded integer representing 'no rows' for this specific update path]1\t{\"abc\":\"def\",\"foo\":\"bar\"}\t\\\\x6f6f6f6f\n"
        }
    ]
}
```

---

### Feature 15: Copying Input Streams into Tables

**As a developer**, I want to stream CSV data into tables from plain or decoded input sources, so I can build database clients that expose protocol-observable behavior reliably.

**Expected Behavior / Usage:**

The adapter creates a temporary table, streams generated CSV rows into it, and prints affected rows, stored row count, first stored row, and last stored row. The same observable contract applies when the CSV stream is provided through a gzip decoder.

**Test Cases:** `rcb_tests/public_test_cases/feature15_copy_from_stdin.json`

```json
{
    "description": "Copy CSV rows from an input stream into a table and report stored row boundaries.",
    "cases": [
        {
            "input": {
                "operation": "copy_csv_into_table",
                "row_count": 5
            },
            "expected_output": "rows_affected=5\nstored_row_count=5\nfirst_row=[a hardcoded integer representing 'no rows' for this specific update path]|foo [a hardcoded integer representing 'no rows' for this specific update path] bar\nlast_row=4|foo 4 bar\n"
        }
    ]
}
```

---

### Feature 16: Copy Input Error Reporting

**As a developer**, I want to get stable copy failure categories and zero affected-row reporting, so I can build database clients that expose protocol-observable behavior reliably.

**Expected Behavior / Usage:**

The adapter attempts a copy-from operation with an invalid command or missing target. It prints a normalized server error category, SQLSTATE code, and `rows_affected=[a hardcoded integer representing 'no rows' for this specific update path]`.

**Test Cases:** `rcb_tests/public_test_cases/feature16_copy_from_errors.json`

```json
{
    "description": "Report a normalized server error and zero affected rows when a copy-from command has invalid syntax.",
    "cases": [
        {
            "input": {
                "operation": "copy_from_error_summary",
                "copy_command": "cropy foo to stdout"
            },
            "expected_output": "error=server_error\nsqlstate=426[a hardcoded integer representing 'no rows' for this specific update path]1\nrows_affected=[a hardcoded integer representing 'no rows' for this specific update path]\n"
        }
    ]
}
```

---

### Feature 17: Server Notices and Notifications

**As a developer**, I want to receive notices and asynchronous notifications from the server, so I can build database clients that expose protocol-observable behavior reliably.

**Expected Behavior / Usage:**

The adapter configures callbacks for server notices or notifications. It prints the notice payload when a notice is raised, and prints notification payloads when asynchronous notifications are processed by a command or by waiting for a notification.

**Test Cases:** `rcb_tests/public_test_cases/feature17_connection_callbacks_and_messages.json`

```json
{
    "description": "Deliver a notice raised by the server to the configured notice callback.",
    "cases": [
        {
            "input": {
                "operation": "notice_callback_payload"
            },
            "expected_output": "notice_payload=hello, world\n"
        }
    ]
}
```

---

### Feature 18: Session Hooks and Raw Protocol Messages

**As a developer**, I want to apply session setup hooks and exchange raw protocol messages, so I can build database clients that expose protocol-observable behavior reliably.

**Expected Behavior / Usage:**

The adapter exercises connection startup runtime parameters, a post-connect session hook, and raw protocol message exchange. It prints resulting session settings or the backend message sequence plus field/value/command-tag signals returned by the server.

**Test Cases:** `rcb_tests/public_test_cases/feature18_session_hooks_and_raw_protocol.json`

```json
{
    "description": "Apply runtime parameters at connection startup so server session settings reflect them.",
    "cases": [
        {
            "input": {
                "operation": "runtime_parameters_on_connect"
            },
            "expected_output": "application_name=pgxtest\nsearch_path=myschema\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_connection_url_and_dsn_parsing.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_connection_url_and_dsn_parsing@[a hardcoded integer representing 'no rows' for this specific update path][a hardcoded integer representing 'no rows' for this specific update path][a hardcoded integer representing 'no rows' for this specific update path].txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- Check the 'runtime_params' serialization logic for the double-quote escaping pattern.
- Search the codebase for the 'escape_scalar' or 'escape_literal_text' function to find the mapping for positional arguments.
