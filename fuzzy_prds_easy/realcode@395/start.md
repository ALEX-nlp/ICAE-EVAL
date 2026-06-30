## Product Requirement Document

# Relational Database Adapter Contract - Database Metadata, SQL Service, and Record Mapping Behavior

## Project Goal

Build a relational database adapter and execution adapter that allows developers to use high-level schema, transaction, SQL-service, and record-mapping behavior against a distributed SQL database without hand-writing low-level request construction, metadata parsing, transaction bookkeeping, or wire-format conversions.

---

## Background & Problem

Without this library/tool, developers are forced to manually construct database service requests, encode parameters, parse metadata tables, track transaction state, batch schema updates, and translate high-level record operations into SQL or commit mutations. This leads to repetitive code, subtle request-shape bugs, inconsistent error handling, and brittle schema introspection.

With this library/tool, developers can describe schema objects and high-level database operations while the adapter emits correct SQL, service requests, metadata summaries, mutation payloads, and neutral error categories.

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

### Feature 1: Column Type Formatting

**As a developer**, I want to format database column metadata into canonical database type declarations, so I can emit schema definitions and verify metadata without manually handling per-type edge cases.

**Expected Behavior / Usage:**

The adapter receives one or more column descriptors with a name, database scalar type, optional size limit, nullability, and primary-key flag. It prints one block per column containing the original type, normalized limit, final database type declaration, nullability, and primary-key status. Variable-length text and binary columns default to MAX when no limit is supplied; fixed scalar types ignore supplied limits.

**Test Cases:** `rcb_tests/public_test_cases/feature1_column_type_format.json`

```json
{
    "description": "Formats database column metadata into the concrete type declaration used by generated schema and query metadata.",
    "cases": [
        {
            "input": {
                "feature": "column_type_format",
                "columns": [
                    {
                        "name": "title",
                        "type": "STRING"
                    },
                    {
                        "name": "body",
                        "type": "STRING",
                        "limit": 1024
                    },
                    {
                        "name": "payload",
                        "type": "BYTES"
                    },
                    {
                        "name": "attachment",
                        "type": "BYTES",
                        "limit": 1024
                    }
                ]
            },
            "expected_output": "column=title\ntype=STRING\nlimit=null\ndb_type=STRING(MAX)\nnullable=true\nprimary_key=false\ncolumn=body\ntype=STRING\nlimit=1024\ndb_type=STRING(1024)\nnullable=true\nprimary_key=false\ncolumn=payload\ntype=BYTES\nlimit=null\ndb_type=BYTES(MAX)\nnullable=true\nprimary_key=false\ncolumn=attachment\ntype=BYTES\nlimit=1024\ndb_type=BYTES(1024)\nnullable=true\nprimary_key=false\n"
        }
    ]
}
```

---

### Feature 2: Schema Relationship Metadata

**As a developer**, I want to represent database schema objects with stable observable fields, so I can reason about tables, indexes, index columns, and foreign-key relationships.

**Expected Behavior / Usage:**

The adapter receives a schema-object descriptor. For a table, it prints the table name, parent table, delete action, cascade status, column order, and primary-key list. For an index, it prints target table, uniqueness, whether it is a primary index, columns sorted by ordinal position, per-column sort direction, and stored columns. For index-column and foreign-key descriptors, it prints the relationship fields and direction flags.

**Test Cases:** `rcb_tests/public_test_cases/feature2_schema_models.json`

```json
{
    "description": "Represents table, index, index-column, and foreign-key metadata with observable names, ordering, direction, and relationship fields.",
    "cases": [
        {
            "input": {
                "feature": "schema_models",
                "kind": "table",
                "name": "test-table",
                "parent_table": "test-parent-table",
                "on_delete": "CASCADE",
                "columns": [
                    {
                        "name": "id",
                        "type": "STRING",
                        "limit": 36,
                        "primary_key": true
                    },
                    {
                        "name": "DESC",
                        "type": "STRING",
                        "limit": "MAX"
                    }
                ]
            },
            "expected_output": "table=test-table\nparent=test-parent-table\non_delete=CASCADE\ncascade=true\ncolumns=id,DESC\nprimary_keys=id\n"
        },
        {
            "input": {
                "feature": "schema_models",
                "kind": "index",
                "table": "test-table",
                "name": "test-index",
                "unique": true,
                "storing": [
                    "col1"
                ],
                "columns": [
                    {
                        "name": "col1",
                        "order": "DESC",
                        "ordinal_position": 1
                    },
                    {
                        "name": "col2",
                        "order": "ASC",
                        "ordinal_position": 0
                    }
                ]
            },
            "expected_output": "index=test-index\ntable=test-table\nunique=true\nprimary=false\ncolumns_by_position=col2,col1\norders=col2:asc,col1:desc\nstoring=col1\n"
        }
    ]
}
```

---

### Feature 3: Connection Lifecycle and Direct Execution

**As a developer**, I want to create and check database connections and execute raw query or DDL text, so I can surface client-visible results and emitted statements.

**Expected Behavior / Usage:**

The adapter receives a connection operation. It can create a database, report active status, return inactive when the underlying service reports an availability problem, execute a query and print the SQL plus returned rows, or execute a DDL statement and print the result plus the exact statement sent to the schema-update API.

**Test Cases:** `rcb_tests/public_test_cases/feature3_connection_lifecycle.json`

```json
{
    "description": "Manages a database connection, reports availability, executes query text against a configured client, and sends DDL text unchanged.",
    "cases": [
        {
            "input": {
                "feature": "connection_lifecycle",
                "operation": "create_database"
            },
            "expected_output": "database=test-instance/test-database\n"
        },
        {
            "input": {
                "feature": "connection_lifecycle",
                "operation": "execute_query",
                "sql": "SELECT * FROM users",
                "rows": [
                    "test-user"
                ]
            },
            "expected_output": "sql=SELECT * FROM users\nrows=test-user\n"
        }
    ]
}
```

---

### Feature 4: DDL Batch Control

**As a developer**, I want to buffer schema-change statements until a batch is completed, so I can send related DDL as one database update and avoid partial schema changes.

**Expected Behavior / Usage:**

The adapter receives DDL batch control instructions. In block or manual-run mode it buffers all supplied statements and sends them together when the batch completes. Aborting a batch clears the buffer; attempting to run afterward prints `error=no_active_batch`. Starting a block-style batch without a block prints `error=missing_block`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_ddl_batching.json`

```json
{
    "description": "Buffers DDL statements while a schema-change batch is active, sends them together on completion, and reports invalid batch control operations as neutral errors.",
    "cases": [
        {
            "input": {
                "feature": "ddl_batch",
                "mode": "block",
                "statements": [
                    "CREATE TABLE users ( id STRING(36) NOT NULL ) PRIMARY KEY (id)",
                    "CREATE TABLE sessions ( id STRING(36) NOT NULL ) PRIMARY KEY (id)"
                ]
            },
            "expected_output": "executed_count=1\nstatements=CREATE TABLE users ( id STRING(36) NOT NULL ) PRIMARY KEY (id)|CREATE TABLE sessions ( id STRING(36) NOT NULL ) PRIMARY KEY (id)\n"
        },
        {
            "input": {
                "feature": "ddl_batch",
                "mode": "abort_then_run",
                "statements": [
                    "CREATE TABLE users ( id STRING(36) NOT NULL ) PRIMARY KEY (id)",
                    "CREATE TABLE sessions ( id STRING(36) NOT NULL ) PRIMARY KEY (id)"
                ]
            },
            "expected_output": "error=no_active_batch\nexecuted_count=0\n"
        }
    ]
}
```

---

### Feature 5: Transaction State Management

**As a developer**, I want to track transaction state transitions and normalize invalid operations, so I can avoid leaking runtime exception details while preserving domain errors.

**Expected Behavior / Usage:**

The adapter receives a target transaction scope and an ordered list of actions. It prints state after successful transitions. A transaction moves from initialized to started, then committed or rolled back. Connection-level actions report active, inactive, or none. Invalid nested begins, missing transactions, inactive transactions, and DDL attempted during an active transaction are rendered as neutral error categories.

**Test Cases:** `rcb_tests/public_test_cases/feature5_transaction_state.json`

```json
{
    "description": "Tracks transaction state transitions and returns neutral error categories for nested, missing, inactive, and DDL-during-transaction operations.",
    "cases": [
        {
            "input": {
                "feature": "transaction_state",
                "target": "transaction",
                "actions": [
                    "begin",
                    "commit"
                ]
            },
            "expected_output": "initial_state=initialized\nafter_begin=started\nafter_commit=committed\n"
        },
        {
            "input": {
                "feature": "transaction_state",
                "target": "transaction",
                "actions": [
                    "begin",
                    "begin"
                ]
            },
            "expected_output": "initial_state=initialized\nafter_begin=started\nerror=nested_transaction\n"
        },
        {
            "input": {
                "feature": "transaction_state",
                "target": "connection",
                "actions": [
                    "commit"
                ]
            },
            "expected_output": "error=no_transaction\n"
        },
        {
            "input": {
                "feature": "transaction_state",
                "target": "connection",
                "actions": [
                    "begin",
                    "ddl"
                ]
            },
            "expected_output": "after_begin=active\nerror=ddl_during_transaction\n"
        }
    ]
}
```

---

### Feature 6: Metadata Query Parsing

**As a developer**, I want to query database metadata tables and convert rows into schema summaries, so I can inspect database structure through stable SQL and parsed results.

**Expected Behavior / Usage:**

The adapter receives a metadata operation. It prints the number of metadata SQL statements, each normalized SQL string, and the parsed result summary. Table discovery returns table names. Column discovery returns column names, concrete type declarations, and nullability. Index discovery returns index names, indexed columns, and uniqueness. Check-constraint discovery returns constraint names and expressions.

**Test Cases:** `rcb_tests/public_test_cases/feature6_metadata_queries.json`

```json
{
    "description": "Queries database metadata views for tables, columns, indexes, and check constraints, returning both issued SQL and parsed metadata summaries.",
    "cases": [
        {
            "input": {
                "feature": "metadata_query",
                "operation": "tables"
            },
            "expected_output": "operation=tables\nexecuted_sql_count=1\nsql1=SELECT TABLE_CATALOG, TABLE_SCHEMA, TABLE_NAME, PARENT_TABLE_NAME, ON_DELETE_ACTION FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA=''\ntables=accounts\n"
        },
        {
            "input": {
                "feature": "metadata_query",
                "operation": "table_columns"
            },
            "expected_output": "operation=table_columns\nexecuted_sql_count=3\nsql1=WITH TABLE_PK_COLS AS ( SELECT C.TABLE_CATALOG, C.TABLE_SCHEMA, C.TABLE_NAME, C.COLUMN_NAME, C.INDEX_NAME, C.COLUMN_ORDERING, C.ORDINAL_POSITION FROM INFORMATION_SCHEMA.INDEX_COLUMNS C WHERE C.INDEX_TYPE = 'PRIMARY_KEY' AND TABLE_CATALOG = '' AND TABLE_SCHEMA = '') SELECT INDEX_NAME, COLUMN_NAME, COLUMN_ORDERING, ORDINAL_POSITION FROM TABLE_PK_COLS INNER JOIN INFORMATION_SCHEMA.TABLES T USING (TABLE_CATALOG, TABLE_SCHEMA, TABLE_NAME) WHERE TABLE_NAME = 'accounts' AND TABLE_CATALOG = '' AND TABLE_SCHEMA = '' ORDER BY ORDINAL_POSITION\nsql2=SELECT COLUMN_NAME, OPTION_NAME, OPTION_TYPE, OPTION_VALUE FROM INFORMATION_SCHEMA.COLUMN_OPTIONS WHERE TABLE_NAME='accounts' AND TABLE_SCHEMA=''\nsql3=SELECT COLUMN_NAME, SPANNER_TYPE, IS_NULLABLE, GENERATION_EXPRESSION, CAST(COLUMN_DEFAULT AS STRING) AS COLUMN_DEFAULT, ORDINAL_POSITION, IS_IDENTITY FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='accounts' AND TABLE_SCHEMA='' ORDER BY ORDINAL_POSITION ASC\ncolumns=account_id:INT64:nullable=false,name:STRING(32):nullable=true\n"
        },
        {
            "input": {
                "feature": "metadata_query",
                "operation": "indexes"
            },
            "expected_output": "operation=indexes\nexecuted_sql_count=2\nsql1=SELECT INDEX_NAME, COLUMN_NAME, COLUMN_ORDERING, ORDINAL_POSITION FROM INFORMATION_SCHEMA.INDEX_COLUMNS WHERE TABLE_NAME='orders' AND TABLE_CATALOG = '' AND TABLE_SCHEMA = '' ORDER BY ORDINAL_POSITION ASC\nsql2=SELECT INDEX_NAME, INDEX_TYPE, IS_UNIQUE, IS_NULL_FILTERED, PARENT_TABLE_NAME, INDEX_STATE FROM INFORMATION_SCHEMA.INDEXES WHERE TABLE_NAME='orders' AND TABLE_CATALOG = '' AND TABLE_SCHEMA = '' AND SPANNER_IS_MANAGED=FALSE\nindexes=index_orders_on_user_id:columns=user_id:unique=false\n"
        },
        {
            "input": {
                "feature": "metadata_query",
                "operation": "check_constraints"
            },
            "expected_output": "operation=check_constraints\nexecuted_sql_count=1\nsql1=SELECT tc.TABLE_NAME, tc.CONSTRAINT_NAME, cc.CHECK_CLAUSE FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc INNER JOIN INFORMATION_SCHEMA.CHECK_CONSTRAINTS cc ON tc.CONSTRAINT_CATALOG = cc.CONSTRAINT_CATALOG AND tc.CONSTRAINT_SCHEMA = cc.CONSTRAINT_SCHEMA AND tc.CONSTRAINT_NAME = cc.CONSTRAINT_NAME WHERE tc.TABLE_NAME = 'accounts' AND tc.CONSTRAINT_SCHEMA = '' AND tc.CONSTRAINT_TYPE = 'CHECK' AND NOT (tc.CONSTRAINT_NAME LIKE 'CK_IS_NOT_NULL_%' AND cc.CHECK_CLAUSE LIKE '%IS NOT NULL')\nconstraints=chk_accounts_name:name IN ('bob')\n"
        }
    ]
}
```

---

### Feature 7: SQL Literal Decoding

**As a developer**, I want to decode SQL string literal syntax, so I can turn metadata expressions into application strings.

**Expected Behavior / Usage:**

The adapter receives SQL literal strings and prints each original literal followed by the decoded content. It supports quoted strings, triple-quoted strings, raw literals, multi-line literals, and backslash escape forms according to the SQL literal behavior covered by the original tests.

**Test Cases:** `rcb_tests/public_test_cases/feature7_sql_literal_unquote.json`

```json
{
    "description": "Decodes SQL string literal text including single quotes, double quotes, triple quotes, raw literals, and escape sequences.",
    "cases": [
        {
            "input": {
                "feature": "sql_literal_unquote",
                "literals": [
                    "\"abc\"",
                    "'it\\\\'s'",
                    "'''two\nlines'''",
                    "r'f\\\\(abc,\n(.*),def\\\\)'",
                    "\"\"\"\\[a unicode escape sequence pattern requiring code inspection]30eb\\[a unicode escape sequence pattern requiring code inspection]30d3\\[a unicode escape sequence pattern requiring code inspection]30fc\"\"\""
                ]
            },
            "expected_output": "literal=\"abc\"\nunquoted=abc\nliteral='it\\\\'s'\nunquoted=it\\'s\nliteral='''two\nlines'''\nunquoted=two\nlines\nliteral=r'f\\\\(abc,\n(.*),def\\\\)'\nunquoted=f\\\\(abc,\n(.*),def\\\\)\nliteral=\"\"\"\\[a unicode escape sequence pattern requiring code inspection]30eb\\[a unicode escape sequence pattern requiring code inspection]30d3\\[a unicode escape sequence pattern requiring code inspection]30fc\"\"\"\nunquoted=[a unicode escape sequence pattern requiring code inspection]30eb[a unicode escape sequence pattern requiring code inspection]30d3[a unicode escape sequence pattern requiring code inspection]30fc\n"
        }
    ]
}
```

---

### Feature 8: Database Session Service

**As a developer**, I want to create and manage database sessions through the service interface, so I can validate client integration against resource-shaped session names.

**Expected Behavior / Usage:**

The adapter receives a session-service operation and database resource path. It can create one session, create a requested batch of sessions, or delete a created session and confirm it no longer appears in listing results. Output includes database resource path, count signals, and resource-prefix matching rather than random session identifiers.

**Test Cases:** `rcb_tests/public_test_cases/feature8_mock_service_sessions.json`

```json
{
    "description": "Implements a database session service that can create, batch-create, list, retrieve, and delete sessions with resource names scoped to the requested database.",
    "cases": [
        {
            "input": {
                "feature": "grpc_sessions",
                "operation": "create",
                "database": "projects/p/instances/i/databases/d"
            },
            "expected_output": "database=projects/p/instances/i/databases/d\nsession_prefix=matched\n"
        },
        {
            "input": {
                "feature": "grpc_sessions",
                "operation": "batch_create",
                "database": "projects/p/instances/i/databases/d",
                "count": 2
            },
            "expected_output": "database=projects/p/instances/i/databases/d\nsession_count=2\nall_prefix_match=true\n"
        },
        {
            "input": {
                "feature": "grpc_sessions",
                "operation": "delete",
                "database": "projects/p/instances/i/databases/d"
            },
            "expected_output": "database=projects/p/instances/i/databases/d\ndeleted_visible=false\nremaining_sessions=0\n"
        }
    ]
}
```

---

### Feature 9: Database SQL Service

**As a developer**, I want to execute registered SQL statements through the service interface, so I can observe result sets, update counts, streams, and normalized service errors.

**Expected Behavior / Usage:**

The adapter receives a SQL-service operation. A scalar query prints row count, column count, and value. An update statement prints exact row count. A streaming query prints streamed values. A missing-table statement prints the SQL, `error=not_found`, and the missing resource name without exposing host-language exception classes.

**Test Cases:** `rcb_tests/public_test_cases/feature9_mock_service_sql.json`

```json
{
    "description": "Executes SQL through the database service, returning scalar result sets, update counts, streaming values, and normalized not-found errors for registered statements.",
    "cases": [
        {
            "input": {
                "feature": "grpc_sql",
                "operation": "select_one",
                "sql": "SELECT 1"
            },
            "expected_output": "sql=SELECT 1\nrows=1\ncolumns=1\nvalue=1\n"
        },
        {
            "input": {
                "feature": "grpc_sql",
                "operation": "update_count",
                "sql": "UPDATE TestTable SET Value=1 WHERE TRUE",
                "count": 100
            },
            "expected_output": "sql=UPDATE TestTable SET Value=1 WHERE TRUE\nrow_count_exact=100\n"
        },
        {
            "input": {
                "feature": "grpc_sql",
                "operation": "missing_table",
                "sql": "SELECT * FROM NonExistingTable",
                "table": "NonExistingTable"
            },
            "expected_output": "sql=SELECT * FROM NonExistingTable\nerror=not_found\nresource=NonExistingTable\n"
        }
    ]
}
```

---

### Feature 10: Record Write Mapping

**As a developer**, I want to map high-level record writes to database SQL or commit mutations, so I can verify framework-visible request behavior instead of direct value stubbing.

**Expected Behavior / Usage:**

The adapter receives a record-write operation and attributes. SQL-style insert prints the emitted SQL plus execute and commit request counts. Mutation-style insert prints mutation operation, target table, ordered columns, values with the generated integer identifier normalized, and checks that the generated identifier is numeric and matches the returned identifier.

**Test Cases:** `rcb_tests/public_test_cases/feature10_orm_writes.json`

```json
{
    "description": "Maps record insert and upsert operations to the database client, preserving SQL execution, commit request counts, generated ids, mutation operation, table name, columns, and values.",
    "cases": [
        {
            "input": {
                "feature": "orm_write",
                "operation": "insert",
                "sql": "INSERT OR IGNORE INTO `singers` (`first_name`,`last_name`) VALUES ('Alice', 'Ecila')",
                "attributes": {
                    "first_name": "Alice",
                    "last_name": "Ecila"
                }
            },
            "expected_output": "sql=INSERT OR IGNORE INTO `singers` (`first_name`,`last_name`) VALUES ('Alice', 'Ecila')\nexecute_requests=1\ncommit_requests=1\ncommit_mutations=0\n"
        },
        {
            "input": {
                "feature": "orm_write",
                "operation": "insert_returning_mutation",
                "attributes": {
                    "first_name": "Alice",
                    "last_name": "Ecila"
                }
            },
            "expected_output": "operation=insert\ntable=singers\ncolumns=first_name,last_name,id\nvalues=Alice,Ecila,<generated-int64>\ngenerated_id_numeric=true\ngenerated_id_matches_returned=true\n"
        }
    ]
}
```

---

### Feature 11: Record Read Mapping

**As a developer**, I want to map high-level record reads to SQL requests with typed parameters, so I can verify query generation, transaction behavior, and bound parameter encoding.

**Expected Behavior / Usage:**

The adapter receives a record-read operation. Reading all records prints the generated SQL, number of records materialized, whether a transaction selector was used, and the number of begin-transaction requests. Finding one record prints the generated SQL, record-found signal, encoded parameter values, parameter database types, and begin-transaction request count.

**Test Cases:** `rcb_tests/public_test_cases/feature11_orm_reads.json`

```json
{
    "description": "Maps record read operations to SQL requests, keeps simple reads outside transactions, and encodes bound parameters with database type information.",
    "cases": [
        {
            "input": {
                "feature": "orm_read",
                "operation": "all_singers",
                "sql": "SELECT `singers`.* FROM `singers`",
                "rows": 4
            },
            "expected_output": "sql=SELECT `singers`.* FROM `singers`\nrecords=4\ntransaction_used=false\nbegin_requests=0\n"
        },
        {
            "input": {
                "feature": "orm_read",
                "operation": "find_singer",
                "sql": "SELECT `singers`.* FROM `singers` WHERE `singers`.`id` = @p1 LIMIT @p2",
                "id": 1
            },
            "expected_output": "sql=SELECT `singers`.* FROM `singers` WHERE `singers`.`id` = @p1 LIMIT @p2\nrecord_found=true\nparams=p1:1:INT64,p2:1:INT64\nbegin_requests=0\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- check the abort handling flag in the global session map
- apply the binding order used in C001
