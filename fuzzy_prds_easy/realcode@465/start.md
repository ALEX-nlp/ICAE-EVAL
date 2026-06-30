## Product Requirement Document

# Document Database Client Adapter - Path, Value, Query, Snapshot, and Write Contracts

## Project Goal

Build a document-database client library and execution adapter that allows developers to construct resource paths, map typed document values, inspect snapshots, build structured queries, and plan write batches without manually assembling low-level wire requests.

---

## Background & Problem

Without this library/tool, developers are forced to hand-build nested resource names, field masks, typed value envelopes, query objects, cursor encodings, and mutation requests. This leads to repetitive code, subtle path bugs, incorrect type conversion, and brittle tests that cannot distinguish correct database-client behavior from superficial return values.

With this library/tool, developers use a stable high-level model while the adapter exposes black-box input/output contracts that show the exact externally observable database requests and decoded values.

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

### Feature 1: Resource Name Handling

**As a developer**, I want to compose and inspect database resource names, so I can build stable document and database paths without hand-written string manipulation.

**Expected Behavior / Usage:**

The input is an adapter command for resource path handling with an operation name and positional string arguments. Outputs are JSON objects containing the requested operation and the resulting string or boolean. Document paths are even-length relative paths below the documents root; collection paths are odd-length relative paths. Absolute paths keep the wire prefix `projects/<project>/databases/<database>/documents/`, and relative-path extraction removes that prefix.

**Test Cases:** `rcb_tests/public_test_cases/feature1_resource_names.json`

```json
{
    "description": "Resource names can be composed, decomposed, classified, and compared using database-relative and absolute document paths.",
    "cases": [
        {
            "input": {
                "feature": "resource_paths",
                "operation": "compose_document_name",
                "arguments": [
                    "project",
                    "database",
                    "a/b"
                ]
            },
            "expected_output": "{\n    \"operation\": \"compose_document_name\",\n    \"result\": \"projects/project/databases/database/documents/a/b\"\n}\n"
        },
        {
            "input": {
                "feature": "resource_paths",
                "operation": "compose_database_name",
                "arguments": [
                    "project",
                    "database"
                ]
            },
            "expected_output": "{\n    \"operation\": \"compose_database_name\",\n    \"result\": \"projects/project/databases/database\"\n}\n"
        },
        {
            "input": {
                "feature": "resource_paths",
                "operation": "append_to_database",
                "arguments": [
                    "projects/project/databases/database",
                    "foo/bar"
                ]
            },
            "expected_output": "{\n    \"operation\": \"append_to_database\",\n    \"result\": \"projects/project/databases/database/documents/foo/bar\"\n}\n"
        }
    ]
}
```

---

### Feature 2: Field Path Encoding

**As a developer**, I want to represent nested field paths safely, so I can address nested fields and fields containing special characters without ambiguous dotted strings.

**Expected Behavior / Usage:**

The input is an adapter command for field path handling. Segment arrays remain ordered path components, dotted strings split into ordered segments, and field paths used in wire masks are escaped only when a segment requires quoting. Invalid textual paths such as empty segments or unsupported path characters must be reported as normalized errors in hidden cases.

**Test Cases:** `rcb_tests/public_test_cases/feature2_field_path_encoding.json`

```json
{
    "description": "Field paths can be constructed from path segments, parsed from dotted text, escaped for wire masks, and rejected when invalid.",
    "cases": [
        {
            "input": {
                "feature": "field_paths",
                "operation": "segments_to_path",
                "segments": [
                    "foo",
                    "bar",
                    "hello",
                    "world"
                ]
            },
            "expected_output": "{\n    \"segments\": [\n        \"foo\",\n        \"bar\",\n        \"hello\",\n        \"world\"\n    ],\n    \"path\": [\n        \"foo\",\n        \"bar\",\n        \"hello\",\n        \"world\"\n    ]\n}\n"
        },
        {
            "input": {
                "feature": "field_paths",
                "operation": "string_to_segments",
                "path": "foo.bar.hello.world"
            },
            "expected_output": "{\n    \"path\": \"foo.bar.hello.world\",\n    \"segments\": [\n        \"foo\",\n        \"bar\",\n        \"hello\",\n        \"world\"\n    ]\n}\n"
        }
    ]
}
```

---

### Feature 3: Value Mapping

**As a developer**, I want to convert between user values and document-database wire values, so I can send and receive strongly typed document data without manual wire-format construction.

**Expected Behavior / Usage:**

The input is an adapter command for value mapping. Wire values decode into JSON-compatible primitives, typed descriptor objects for bytes, timestamps, geographic points, and document references, or nested arrays/maps. Client-side values encode back to wire objects such as `stringValue`, `integerValue`, `arrayValue`, `mapValue`, `bytesValue`, `timestampValue`, `geoPointValue`, and `referenceValue`. Sentinel markers are removed from field payloads and returned as independent server-timestamp and delete path lists.

**Test Cases:** `rcb_tests/public_test_cases/feature3_value_mapping.json`

```json
{
    "description": "Client values and wire values are converted bidirectionally, including nested containers, binary data, timestamps, geographic points, references, and sentinel values.",
    "cases": [
        {
            "input": {
                "feature": "value_mapping",
                "operation": "decode",
                "wire": {
                    "stringValue": "foobar"
                }
            },
            "expected_output": "{\n    \"decoded\": \"foobar\"\n}\n"
        },
        {
            "input": {
                "feature": "value_mapping",
                "operation": "decode",
                "wire": {
                    "arrayValue": {
                        "values": [
                            {
                                "stringValue": "foo"
                            },
                            {
                                "stringValue": "bar"
                            }
                        ]
                    }
                }
            },
            "expected_output": "{\n    \"decoded\": [\n        \"foo\",\n        \"bar\"\n    ]\n}\n"
        },
        {
            "input": {
                "feature": "value_mapping",
                "operation": "decode",
                "wire": {
                    "mapValue": {
                        "fields": {
                            "foo": {
                                "stringValue": "bar"
                            },
                            "hello": {
                                "stringValue": "world"
                            }
                        }
                    }
                }
            },
            "expected_output": "{\n    \"decoded\": {\n        \"foo\": \"bar\",\n        \"hello\": \"world\"\n    }\n}\n"
        },
        {
            "input": {
                "feature": "value_mapping",
                "operation": "decode",
                "wire": {
                    "referenceValue": "[a specific parent path pattern derived from the snapshot name - ask the spec for the exact delimiter usage]/b"
                }
            },
            "expected_output": "{\n    \"decoded\": {\n        \"type\": \"document_reference\",\n        \"name\": \"[a specific parent path pattern derived from the snapshot name - ask the spec for the exact delimiter usage]/b\",\n        \"path\": \"a/b\",\n        \"id\": \"b\",\n        \"parent\": \"[a specific parent path pattern derived from the snapshot name - ask the spec for the exact delimiter usage]\"\n    }\n}\n"
        }
    ]
}
```

---

### Feature 4: Document Snapshot Access

**As a developer**, I want to read immutable document snapshots, so I can inspect retrieved document data consistently without mutating snapshots.

**Expected Behavior / Usage:**

The input is an adapter command containing a snapshot object with an absolute document name, existence flag, optional timestamp descriptors, and field data. Outputs expose identity fields, timestamp descriptors, full fields, or a selected nested value. Textual field paths use dot separators; segmented field paths address exact segments. Missing paths, invalid path types, and attempted writes are normalized as errors in hidden cases.

**Test Cases:** `rcb_tests/public_test_cases/feature4_document_snapshots.json`

```json
{
    "description": "Document snapshots expose immutable identity, existence, timestamps, full field data, and nested field lookup by textual or segmented field paths.",
    "cases": [
        {
            "input": {
                "feature": "snapshots",
                "operation": "identity",
                "snapshot": {
                    "name": "[a specific parent path pattern derived from the snapshot name - ask the spec for the exact delimiter usage]/b",
                    "exists": true,
                    "info": {
                        "readTime": {
                            "kind": "timestamp",
                            "seconds": 100,
                            "nanos": 0
                        },
                        "updateTime": {
                            "kind": "timestamp",
                            "seconds": 200,
                            "nanos": 0
                        },
                        "createTime": {
                            "kind": "timestamp",
                            "seconds": 50,
                            "nanos": 0
                        }
                    },
                    "fields": {
                        "foo": "bar",
                        "a": {
                            "b": "c",
                            "d": {
                                "e": "f"
                            }
                        }
                    }
                }
            },
            "expected_output": "{\n    \"name\": \"[a specific parent path pattern derived from the snapshot name - ask the spec for the exact delimiter usage]/b\",\n    \"path\": \"a/b\",\n    \"id\": \"b\",\n    \"exists\": true\n}\n"
        },
        {
            "input": {
                "feature": "snapshots",
                "operation": "timestamps",
                "snapshot": {
                    "name": "[a specific parent path pattern derived from the snapshot name - ask the spec for the exact delimiter usage]/b",
                    "exists": true,
                    "info": {
                        "readTime": {
                            "kind": "timestamp",
                            "seconds": 100,
                            "nanos": 0
                        },
                        "updateTime": {
                            "kind": "timestamp",
                            "seconds": 200,
                            "nanos": 0
                        },
                        "createTime": {
                            "kind": "timestamp",
                            "seconds": 50,
                            "nanos": 0
                        }
                    },
                    "fields": {
                        "foo": "bar",
                        "a": {
                            "b": "c",
                            "d": {
                                "e": "f"
                            }
                        }
                    }
                }
            },
            "expected_output": "{\n    \"readTime\": {\n        \"kind\": \"timestamp\",\n        \"seconds\": 100,\n        \"nanos\": 0\n    },\n    \"updateTime\": {\n        \"kind\": \"timestamp\",\n        \"seconds\": 200,\n        \"nanos\": 0\n    },\n    \"createTime\": {\n        \"kind\": \"timestamp\",\n        \"seconds\": 50,\n        \"nanos\": 0\n    }\n}\n"
        },
        {
            "input": {
                "feature": "snapshots",
                "operation": "fields",
                "snapshot": {
                    "name": "[a specific parent path pattern derived from the snapshot name - ask the spec for the exact delimiter usage]/b",
                    "exists": true,
                    "info": {
                        "readTime": {
                            "kind": "timestamp",
                            "seconds": 100,
                            "nanos": 0
                        },
                        "updateTime": {
                            "kind": "timestamp",
                            "seconds": 200,
                            "nanos": 0
                        },
                        "createTime": {
                            "kind": "timestamp",
                            "seconds": 50,
                            "nanos": 0
                        }
                    },
                    "fields": {
                        "foo": "bar",
                        "a": {
                            "b": "c",
                            "d": {
                                "e": "f"
                            }
                        }
                    }
                }
            },
            "expected_output": "{\n    \"fields\": {\n        \"foo\": \"bar\",\n        \"a\": {\n            \"b\": \"c\",\n            \"d\": {\n                \"e\": \"f\"\n            }\n        }\n    }\n}\n"
        }
    ]
}
```

---

### Feature 5: Reference and Collection Navigation

**As a developer**, I want to navigate document and collection references, so I can derive child resources and enumerate subcollections without manually concatenating paths.

**Expected Behavior / Usage:**

The input is an adapter command containing an absolute collection or document name, child identifiers, or paged collection-id responses. Outputs describe reference identity with type, name, relative path, id, and parent where applicable. Listing child collections must include both the returned collection references and the observable paged connection calls.

**Test Cases:** `rcb_tests/public_test_cases/feature5_references_and_collections.json`

```json
{
    "description": "Collection and document references expose stable identities, create child references, and list child collections through paged connection calls.",
    "cases": [
        {
            "input": {
                "feature": "references",
                "operation": "collection_identity",
                "name": "[a specific parent path pattern derived from the snapshot name - ask the spec for the exact delimiter usage]/b"
            },
            "expected_output": "{\n    \"type\": \"collection_reference\",\n    \"name\": \"[a specific parent path pattern derived from the snapshot name - ask the spec for the exact delimiter usage]/b\",\n    \"path\": \"a/b\",\n    \"id\": \"b\"\n}\n"
        },
        {
            "input": {
                "feature": "references",
                "operation": "document_identity",
                "name": "[a specific parent path pattern derived from the snapshot name - ask the spec for the exact delimiter usage]/b"
            },
            "expected_output": "{\n    \"type\": \"document_reference\",\n    \"name\": \"[a specific parent path pattern derived from the snapshot name - ask the spec for the exact delimiter usage]/b\",\n    \"path\": \"a/b\",\n    \"id\": \"b\",\n    \"parent\": \"[a specific parent path pattern derived from the snapshot name - ask the spec for the exact delimiter usage]\"\n}\n"
        }
    ]
}
```

---

### Feature 6: Query Planning and Result Decoding

**As a developer**, I want to build structured query requests and decode result rows, so I can express projections, filters, ordering, limits, offsets, cursors, and result decoding through a stable request contract.

**Expected Behavior / Usage:**

The input is an adapter command with a parent documents root, collection id, ordered query steps, optional execution flag, and optional returned rows. Outputs include the observable `run_query` call with its structured request, decoded row summaries, result size, and empty-state flag. Filters distinguish field filters from unary null/NaN filters, ordering directions are rendered as wire enum numbers, and cursor values for document identity fields become reference values.

**Test Cases:** `rcb_tests/public_test_cases/feature6_query_planning_and_results.json`

```json
{
    "description": "Queries build structured requests for selection, filtering, ordering, limits, offsets, cursors, and decode returned document rows into snapshots.",
    "cases": [
        {
            "input": {
                "feature": "queries",
                "parent": "projects/example_project/databases/(default)/documents",
                "collection": "foo",
                "steps": [
                    {
                        "type": "select",
                        "fields": [
                            "users.john",
                            "users.dave"
                        ]
                    },
                    {
                        "type": "select",
                        "fields": [
                            "users.dan"
                        ]
                    }
                ]
            },
            "expected_output": "{\n    \"calls\": [\n        {\n            \"operation\": \"run_query\",\n            \"request\": {\n                \"parent\": \"projects/example_project/databases/(default)/documents\",\n                \"structuredQuery\": {\n                    \"from\": [\n                        {\n                            \"collectionId\": \"foo\"\n                        }\n                    ],\n                    \"select\": {\n                        \"fields\": [\n                            {\n                                \"fieldPath\": \"users.john\"\n                            },\n                            {\n                                \"fieldPath\": \"users.dave\"\n                            },\n                            {\n                                \"fieldPath\": \"users.dan\"\n                            }\n                        ]\n                    }\n                },\n                \"retries\": 0\n            }\n        }\n    ],\n    \"rows\": [],\n    \"size\": 0,\n    \"is_empty\": true\n}\n"
        },
        {
            "input": {
                "feature": "queries",
                "parent": "projects/example_project/databases/(default)/documents",
                "collection": "foo",
                "steps": [
                    {
                        "type": "where",
                        "field": "user.name",
                        "operator": "=",
                        "value": "John"
                    },
                    {
                        "type": "where",
                        "field": "user.age",
                        "operator": "=",
                        "value": 30
                    },
                    {
                        "type": "where",
                        "field": "user.coolness",
                        "operator": "=",
                        "value": null
                    }
                ]
            },
            "expected_output": "{\n    \"calls\": [\n        {\n            \"operation\": \"run_query\",\n            \"request\": {\n                \"parent\": \"projects/example_project/databases/(default)/documents\",\n                \"structuredQuery\": {\n                    \"from\": [\n                        {\n                            \"collectionId\": \"foo\"\n                        }\n                    ],\n                    \"where\": {\n                        \"compositeFilter\": {\n                            \"op\": 1,\n                            \"filters\": [\n                                {\n                                    \"fieldFilter\": {\n                                        \"field\": {\n                                            \"fieldPath\": \"user.name\"\n                                        },\n                                        \"op\": 5,\n                                        \"value\": {\n                                            \"stringValue\": \"John\"\n                                        }\n                                    }\n                                },\n                                {\n                                    \"fieldFilter\": {\n                                        \"field\": {\n                                            \"fieldPath\": \"user.age\"\n                                        },\n                                        \"op\": 5,\n                                        \"value\": {\n                                            \"integerValue\": 30\n                                        }\n                                    }\n                                },\n                                {\n                                    \"unaryFilter\": {\n                                        \"field\": {\n                                            \"fieldPath\": \"user.coolness\"\n                                        },\n                                        \"op\": 3\n                                    }\n                                }\n                            ]\n                        }\n                    }\n                },\n                \"retries\": 0\n            }\n        }\n    ],\n    \"rows\": [],\n    \"size\": 0,\n    \"is_empty\": true\n}\n"
        },
        {
            "input": {
                "feature": "queries",
                "parent": "projects/example_project/databases/(default)/documents",
                "collection": "foo",
                "steps": [
                    {
                        "type": "order",
                        "field": "user.name",
                        "direction": "DESC"
                    },
                    {
                        "type": "order",
                        "field": "user.age",
                        "direction": "ASC"
                    },
                    {
                        "type": "limit",
                        "value": 50
                    },
                    {
                        "type": "offset",
                        "value": 50
                    }
                ]
            },
            "expected_output": "{\n    \"calls\": [\n        {\n            \"operation\": \"run_query\",\n            \"request\": {\n                \"parent\": \"projects/example_project/databases/(default)/documents\",\n                \"structuredQuery\": {\n                    \"from\": [\n                        {\n                            \"collectionId\": \"foo\"\n                        }\n                    ],\n                    \"orderBy\": [\n                        {\n                            \"field\": {\n                                \"fieldPath\": \"user.name\"\n                            },\n                            \"direction\": 2\n                        },\n                        {\n                            \"field\": {\n                                \"fieldPath\": \"user.age\"\n                            },\n                            \"direction\": 1\n                        }\n                    ],\n                    \"limit\": {\n                        \"value\": 50\n                    },\n                    \"offset\": 50\n                },\n                \"retries\": 0\n            }\n        }\n    ],\n    \"rows\": [],\n    \"size\": 0,\n    \"is_empty\": true\n}\n"
        }
    ]
}
```

---

### Feature 7: Write Batch Mutation Planning

**As a developer**, I want to enqueue and commit document mutations, so I can verify create, set, update, delete, transform, precondition, commit, and rollback behavior through observable database requests.

**Expected Behavior / Usage:**

The input is an adapter command containing a database name, optional transaction id, ordered write operations, and optional simulated commit response. Outputs include the normalized commit result and the observable connection calls. Creates include an exists-false precondition, merge sets include update masks, updates include sorted masks and exists-true preconditions, delete sentinels remove fields from payloads, server timestamp sentinels become transform writes, and rollback emits a rollback call when a transaction id is present.

**Test Cases:** `rcb_tests/public_test_cases/feature7_write_batches.json`

```json
{
    "description": "Write batches enqueue creates, sets, updates, deletes, transforms, preconditions, commits, and rollback requests as structured database mutations.",
    "cases": [
        {
            "input": {
                "feature": "writes",
                "database": "projects/example_project/databases/(default)",
                "operations": [
                    {
                        "type": "create",
                        "document": "[a specific parent path pattern derived from the snapshot name - ask the spec for the exact delimiter usage]/b",
                        "fields": {
                            "hello": "world"
                        }
                    }
                ]
            },
            "expected_output": "{\n    \"commit_result\": [\n        []\n    ],\n    \"calls\": [\n        {\n            \"operation\": \"commit\",\n            \"request\": {\n                \"database\": \"projects/example_project/databases/(default)\",\n                \"writes\": [\n                    {\n                        \"currentDocument\": {\n                            \"exists\": false\n                        },\n                        \"update\": {\n                            \"name\": \"[a specific parent path pattern derived from the snapshot name - ask the spec for the exact delimiter usage]/b\",\n                            \"fields\": {\n                                \"hello\": {\n                                    \"stringValue\": \"world\"\n                                }\n                            }\n                        }\n                    }\n                ]\n            }\n        }\n    ]\n}\n"
        },
        {
            "input": {
                "feature": "writes",
                "database": "projects/example_project/databases/(default)",
                "operations": [
                    {
                        "type": "set",
                        "document": "[a specific parent path pattern derived from the snapshot name - ask the spec for the exact delimiter usage]/b",
                        "fields": {
                            "hello": "world"
                        },
                        "options": {
                            "merge": true
                        }
                    }
                ]
            },
            "expected_output": "{\n    \"commit_result\": [\n        []\n    ],\n    \"calls\": [\n        {\n            \"operation\": \"commit\",\n            \"request\": {\n                \"database\": \"projects/example_project/databases/(default)\",\n                \"writes\": [\n                    {\n                        \"[the required mask field name for merge requests - verify with the write protocol spec]\": {\n                            \"fieldPaths\": [\n                                \"hello\"\n                            ]\n                        },\n                        \"update\": {\n                            \"name\": \"[a specific parent path pattern derived from the snapshot name - ask the spec for the exact delimiter usage]/b\",\n                            \"fields\": {\n                                \"hello\": {\n                                    \"stringValue\": \"world\"\n                                }\n                            }\n                        }\n                    }\n                ]\n            }\n        }\n    ]\n}\n"
        },
        {
            "input": {
                "feature": "writes",
                "database": "projects/example_project/databases/(default)",
                "operations": [
                    {
                        "type": "update",
                        "document": "[a specific parent path pattern derived from the snapshot name - ask the spec for the exact delimiter usage]/b",
                        "data": [
                            {
                                "path": "hello",
                                "value": "world"
                            },
                            {
                                "path": "foo.bar",
                                "value": "val"
                            },
                            {
                                "path": {
                                    "kind": "field_path",
                                    "segments": [
                                        "foo",
                                        "baz"
                                    ]
                                },
                                "value": "val"
                            }
                        ]
                    }
                ]
            },
            "expected_output": "{\n    \"commit_result\": [\n        []\n    ],\n    \"calls\": [\n        {\n            \"operation\": \"commit\",\n            \"request\": {\n                \"database\": \"projects/example_project/databases/(default)\",\n                \"writes\": [\n                    {\n                        \"[the required mask field name for merge requests - verify with the write protocol spec]\": {\n                            \"fieldPaths\": [\n                                \"foo.bar\",\n                                \"foo.baz\",\n                                \"hello\"\n                            ]\n                        },\n                        \"currentDocument\": {\n                            \"exists\": true\n                        },\n                        \"update\": {\n                            \"name\": \"[a specific parent path pattern derived from the snapshot name - ask the spec for the exact delimiter usage]/b\",\n                            \"fields\": {\n                                \"hello\": {\n                                    \"stringValue\": \"world\"\n                                },\n                                \"foo\": {\n                                    \"mapValue\": {\n                                        \"fields\": {\n                                            \"bar\": {\n                                                \"stringValue\": \"val\"\n                                            },\n                                            \"baz\": {\n                                                \"stringValue\": \"val\"\n                                            }\n                                        }\n                                    }\n                                }\n                            }\n                        }\n                    }\n                ]\n            }\n        }\n    ]\n}\n"
        },
        {
            "input": {
                "feature": "writes",
                "database": "projects/example_project/databases/(default)",
                "operations": [
                    {
                        "type": "update",
                        "document": "[a specific parent path pattern derived from the snapshot name - ask the spec for the exact delimiter usage]/b",
                        "data": [
                            {
                                "path": "country",
                                "value": {
                                    "kind": "delete_field"
                                }
                            },
                            {
                                "path": "lastLogin",
                                "value": {
                                    "kind": "server_timestamp"
                                }
                            }
                        ]
                    }
                ]
            },
            "expected_output": "{\n    \"commit_result\": [\n        []\n    ],\n    \"calls\": [\n        {\n            \"operation\": \"commit\",\n            \"request\": {\n                \"database\": \"projects/example_project/databases/(default)\",\n                \"writes\": [\n                    {\n                        \"[the required mask field name for merge requests - verify with the write protocol spec]\": {\n                            \"fieldPaths\": [\n                                \"country\"\n                            ]\n                        },\n                        \"currentDocument\": {\n                            \"exists\": true\n                        },\n                        \"update\": {\n                            \"name\": \"[a specific parent path pattern derived from the snapshot name - ask the spec for the exact delimiter usage]/b\",\n                            \"fields\": []\n                        }\n                    },\n                    {\n                        \"transform\": {\n                            \"document\": \"[a specific parent path pattern derived from the snapshot name - ask the spec for the exact delimiter usage]/b\",\n                            \"fieldTransforms\": [\n                                {\n                                    \"fieldPath\": \"lastLogin\",\n                                    \"setToServerValue\": 1\n                                }\n                            ]\n                        }\n                    }\n                ]\n            }\n        }\n    ]\n}\n"
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
- extract the final two path segments using standard directory separation logic
- take the trailing identifier from the hierarchical reference string
