## Product Requirement Document

# Cloud Data Warehouse Client Adapter - Request Formatting and Typed Value Contracts

## Project Goal

Build a cloud data warehouse client adapter that allows developers to construct typed literals, resource references, query parameters, table metadata, jobs, row inserts, and access-policy requests without manually assembling low-level REST request bodies.

---

## Background & Problem

Without this library/tool, developers are forced to hand-format endpoint strings, typed values, schema definitions, query parameters, row payloads, and job request bodies. This leads to repetitive code, precision loss for large integers, inconsistent regional targeting, and subtle request-shape bugs.

With this library/tool, callers provide ordinary values and concise option objects, and the client adapter produces deterministic wire-format values and request objects suitable for the backing service.

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

### Feature 1: Endpoint Normalization

**As a developer**, I want to normalize endpoint strings before making service requests, so I can accept user-supplied service host strings without fragile manual cleanup.

**Expected Behavior / Usage:**

The input is an endpoint string. The output is the normalized endpoint string followed by a newline. Missing protocols are treated as secure endpoints, explicit protocols are preserved, and trailing slash characters are removed.

**Test Cases:** `rcb_tests/public_test_cases/feature1_endpoint_normalization.json`

```json
{
    "description": "Endpoint normalization adds a secure protocol when missing, preserves an explicit protocol, and removes trailing slash characters.",
    "cases": [
        {
            "input": {
                "operation": "sanitize_endpoint",
                "endpoint": "warehouse.example.com/"
            },
            "expected_output": "https://warehouse.example.com\n"
        },
        {
            "input": {
                "operation": "sanitize_endpoint",
                "endpoint": "http://localhost:9050///"
            },
            "expected_output": "http://localhost:9050\n"
        }
    ]
}
```

---

### Feature 2.1: Temporal Literal Construction

**As a developer**, I want to construct date, datetime, time, and timestamp literals from strings or structured parts, so I can send typed temporal values in request bodies without losing their wire value.

**Expected Behavior / Usage:**

The input identifies a temporal literal kind and supplies either a raw string, structured date/time parts, or a timestamp-compatible instant. The output is a JSON object containing a neutral literal type, the literal wire value, and its JSON representation. Missing minute and second parts for a time default to zero.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_temporal_literals.json`

```json
{
    "description": "Temporal literal wrappers preserve date, datetime, time, and timestamp inputs in the wire value shape used for query parameters and row data.",
    "cases": [
        {
            "input": {
                "operation": "create_temporal_value",
                "kind": "date",
                "value": "2019-01-01"
            },
            "expected_output": "{\n  \"type\": \"date_literal\",\n  \"value\": \"2019-01-01\",\n  \"json\": {\n    \"value\": \"2019-01-01\"\n  }\n}\n"
        },
        {
            "input": {
                "operation": "create_temporal_value",
                "kind": "date",
                "value": {
                    "year": 2019,
                    "month": 1,
                    "day": 2
                }
            },
            "expected_output": "{\n  \"type\": \"date_literal\",\n  \"value\": \"[a specific date format]\",\n  \"json\": {\n    \"value\": \"[a specific date format]\"\n  }\n}\n"
        }
    ]
}
```

---

### Feature 2.2: Geography and Integer Literal Construction

**As a developer**, I want to construct geography and integer literals, so I can send spatial and 64-bit integer values without accidental precision loss.

**Expected Behavior / Usage:**

The input supplies either a geography wire string or an integer value with optional casting behavior. The output is a JSON object containing a neutral literal type, the stored wire value, the JSON representation, and, for integers, the value returned by value conversion. An integer value outside the safe range produces a normalized out-of-bounds error category carrying the offending value, and if integer casting is requested without a cast function, the output is a normalized invalid-cast error category.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_geography_integer_literals.json`

```json
{
    "description": "Geography and integer literal wrappers preserve their wire values, including JSON representation and integer value conversion behavior.",
    "cases": [
        {
            "input": {
                "operation": "create_geography_value",
                "value": "POINT(1 2)"
            },
            "expected_output": "{\n  \"type\": \"geography_literal\",\n  \"value\": \"POINT(1 2)\",\n  \"json\": {\n    \"value\": \"POINT(1 2)\"\n  }\n}\n"
        },
        {
            "input": {
                "operation": "create_integer_value",
                "value": "9007199254740993"
            },
            "expected_output": "[the maximum safe integer error message]\nvalue=9007199254740993\n"
        }
    ]
}
```

---

### Feature 3.1: Parameter Type Inference

**As a developer**, I want to infer query parameter type descriptors from input values, so I can build typed query requests without manually describing every primitive or nested value.

**Expected Behavior / Usage:**

The input is a value to be used as a query parameter. The output is the inferred parameter type descriptor as formatted JSON. Primitive booleans, floating point numbers, arrays, typed literals, and structured objects are supported. Empty arrays and null values cannot be inferred and produce normalized missing-type error output.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_parameter_type_inference.json`

```json
{
    "description": "Query parameter type inference maps primitive, custom, array, and structured values into the expected query parameter type descriptors and reports neutral errors when a type cannot be inferred.",
    "cases": [
        {
            "input": {
                "operation": "infer_parameter_type",
                "value": true
            },
            "expected_output": "{\n  \"type\": \"BOOL\"\n}\n"
        },
        {
            "input": {
                "operation": "infer_parameter_type",
                "value": 1.5
            },
            "expected_output": "{\n  \"type\": \"FLOAT64\"\n}\n"
        }
    ]
}
```

---

### Feature 3.2: Provided Parameter Type Descriptors

**As a developer**, I want to convert explicit parameter type declarations into request descriptors, so I can override inference when a query parameter needs a declared type.

**Expected Behavior / Usage:**

The input is an explicit parameter type declaration, including array and structured declarations. The output is the corresponding parameter type descriptor as formatted JSON. Invalid declarations produce a normalized invalid-type error output.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_provided_parameter_types.json`

```json
{
    "description": "Explicit parameter type declarations for arrays and structures are converted into query parameter descriptors, while invalid declarations produce a neutral error category.",
    "cases": [
        {
            "input": {
                "operation": "provided_parameter_type",
                "type": [
                    "INT64"
                ]
            },
            "expected_output": "{\n  \"type\": \"ARRAY\",\n  \"arrayType\": {\n    \"type\": \"INT64\"\n  }\n}\n"
        },
        {
            "input": {
                "operation": "provided_parameter_type",
                "type": {
                    "prop": "INT64"
                }
            },
            "expected_output": "{\n  \"type\": \"STRUCT\",\n  \"structTypes\": [\n    {\n      \"name\": \"prop\",\n      \"type\": {\n        \"type\": \"INT64\"\n      }\n    }\n  ]\n}\n"
        }
    ]
}
```

---

### Feature 3.3: Query Parameter Serialization

**As a developer**, I want to serialize query parameter values with their type descriptors, so I can send named, positional, array, and structured query parameters in the service request format.

**Expected Behavior / Usage:**

The input is a parameter value and may include an explicit parameter type declaration. The output is a JSON object containing the parameter type and parameter value exactly as they should appear in a query request body, including nested struct values and array values.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_query_parameter_serialization.json`

```json
{
    "description": "Query parameter serialization combines inferred or provided type descriptors with values, including nested structures, arrays, and typed literals.",
    "cases": [
        {
            "input": {
                "operation": "query_parameter",
                "value": {
                    "name": "a",
                    "scores": [
                        1,
                        2
                    ],
                    "when": {
                        "__custom": "date",
                        "value": "2020-01-02"
                    }
                }
            },
            "expected_output": "{\n  \"parameterType\": {\n    \"type\": \"STRUCT\",\n    \"structTypes\": [\n      {\n        \"name\": \"name\",\n        \"type\": {\n          \"type\": \"STRING\"\n        }\n      },\n      {\n        \"name\": \"scores\",\n        \"type\": {\n          \"type\": \"ARRAY\",\n          \"arrayType\": {\n            \"type\": \"INT64\"\n          }\n        }\n      },\n      {\n        \"name\": \"when\",\n        \"type\": {\n          \"type\": \"DATE\"\n        }\n      }\n    ]\n  },\n  \"parameterValue\": {\n    \"structValues\": {\n      \"name\": {\n        \"value\": \"a\"\n      },\n      \"scores\": {\n        \"[string representation of array values]\": [\n          {\n            \"value\": 1\n          },\n          {\n            \"value\": 2\n          }\n        ]\n      },\n      \"when\": {\n        \"value\": \"2020-01-02\"\n      }\n    }\n  }\n}\n"
        },
        {
            "input": {
                "operation": "query_parameter",
                "value": [
                    1,
                    2
                ],
                "type": [
                    "INT64"
                ]
            },
            "expected_output": "{\n  \"parameterType\": {\n    \"type\": \"ARRAY\",\n    \"arrayType\": {\n      \"type\": \"INT64\"\n    }\n  },\n  \"parameterValue\": {\n    \"[string representation of array values]\": [\n      {\n        \"value\": 1\n      },\n      {\n        \"value\": 2\n      }\n    ]\n  }\n}\n"
        }
    ]
}
```

---

### Feature 4: Schema-Guided Row Decoding

**As a developer**, I want to decode tabular API rows using schema fields, so I can consume service row responses as named objects rather than positional cells.

**Expected Behavior / Usage:**

The input contains a schema and rows in cell-array response form. The output is a JSON array of decoded row objects. Field names come from the schema, booleans are converted to booleans, records become nested objects, repeated fields become arrays, and integer wrapping errors are normalized when configured incorrectly.

**Test Cases:** `rcb_tests/public_test_cases/feature4_schema_row_merge.json`

```json
{
    "description": "Schema-guided row decoding converts API row cells into named objects, preserving nested records and repeated fields with domain type conversions.",
    "cases": [
        {
            "input": {
                "operation": "merge_rows",
                "schema": {
                    "fields": [
                        {
                            "name": "name",
                            "type": "STRING"
                        },
                        {
                            "name": "flag",
                            "type": "BOOLEAN"
                        },
                        {
                            "name": "nested",
                            "type": "RECORD",
                            "fields": [
                                {
                                    "name": "ok",
                                    "type": "BOOLEAN"
                                }
                            ]
                        },
                        {
                            "name": "arr",
                            "type": "STRING",
                            "mode": "REPEATED"
                        }
                    ]
                },
                "rows": [
                    {
                        "f": [
                            {
                                "v": "cat"
                            },
                            {
                                "v": "true"
                            },
                            {
                                "v": {
                                    "f": [
                                        {
                                            "v": "false"
                                        }
                                    ]
                                }
                            },
                            {
                                "v": [
                                    {
                                        "v": "a"
                                    },
                                    {
                                        "v": "b"
                                    }
                                ]
                            }
                        ]
                    }
                ]
            },
            "expected_output": "[\n  {\n    \"name\": \"cat\",\n    \"flag\": true,\n    \"nested\": {\n      \"ok\": false\n    },\n    \"arr\": [\n      \"a\",\n      \"b\"\n    ]\n  }\n]\n"
        },
        {
            "input": {
                "operation": "merge_rows",
                "schema": {
                    "fields": [
                        {
                            "name": "id",
                            "type": "INTEGER"
                        },
                        {
                            "name": "label",
                            "type": "STRING"
                        }
                    ]
                },
                "rows": [
                    {
                        "f": [
                            {
                                "v": "123"
                            },
                            {
                                "v": "kitten"
                            }
                        ]
                    }
                ],
                "options": {
                    "wrapIntegers": true
                }
            },
            "expected_output": "error=invalid_integer_cast\n"
        }
    ]
}
```

---

### Feature 5.1: Schema String Parsing

**As a developer**, I want to parse compact schema strings into field definitions, so I can let callers describe simple table schemas concisely.

**Expected Behavior / Usage:**

The input is a comma-separated schema string whose entries contain field names and types separated by colons. The output is a JSON object with a fields array. Field names and types are trimmed, and types are uppercased.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_schema_string_parsing.json`

```json
{
    "description": "Comma-separated schema strings are parsed into field definitions with trimmed names and uppercased types.",
    "cases": [
        {
            "input": {
                "operation": "parse_schema",
                "schema": "name:string, age: integer, active:bool"
            },
            "expected_output": "{\n  \"fields\": [\n    {\n      \"name\": \"name\",\n      \"type\": \"STRING\"\n    },\n    {\n      \"name\": \"age\",\n      \"type\": \"INTEGER\"\n    },\n    {\n      \"name\": \"active\",\n      \"type\": \"BOOL\"\n    }\n  ]\n}\n"
        },
        {
            "input": {
                "operation": "parse_schema",
                "schema": " first : string , second:float "
            },
            "expected_output": "{\n  \"fields\": [\n    {\n      \"name\": \"first\",\n      \"type\": \"STRING\"\n    },\n    {\n      \"name\": \"second\",\n      \"type\": \"FLOAT\"\n    }\n  ]\n}\n"
        }
    ]
}
```

---

### Feature 5.2: Table Metadata Formatting

**As a developer**, I want to format table metadata shortcuts into request bodies, so I can send table creation and update metadata using concise caller-facing options.

**Expected Behavior / Usage:**

The input is a table metadata object that may contain a friendly-name shortcut, schema shortcut, partitioning shortcut, or view SQL. The output is the formatted metadata request object. Schema strings become field arrays, a friendly-name shortcut becomes a friendlyName field, view SQL becomes a view object using standard SQL by default, and preformatted view objects are preserved.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_table_metadata_formatting.json`

```json
{
    "description": "Table metadata formatting converts friendly names, schema shortcuts, partitioning shortcuts, and view SQL into the API request body shape.",
    "cases": [
        {
            "input": {
                "operation": "format_table_metadata",
                "metadata": {
                    "name": "friendly",
                    "schema": "name:string, age:integer",
                    "timePartitioning": "DAY",
                    "view": "select 1"
                }
            },
            "expected_output": "{\n  \"schema\": {\n    \"fields\": [\n      {\n        \"name\": \"name\",\n        \"type\": \"STRING\"\n      },\n      {\n        \"name\": \"age\",\n        \"type\": \"INTEGER\"\n      }\n    ]\n  },\n  \"timePartitioning\": \"DAY\",\n  \"view\": {\n    \"query\": \"select 1\",\n    \"useLegacySql\": false\n  },\n  \"friendlyName\": \"friendly\"\n}\n"
        },
        {
            "input": {
                "operation": "format_table_metadata",
                "metadata": {
                    "schema": [
                        {
                            "name": "id",
                            "type": "INTEGER"
                        }
                    ],
                    "view": {
                        "query": "select 2",
                        "useLegacySql": true
                    }
                }
            },
            "expected_output": "{\n  \"schema\": {\n    \"fields\": [\n      {\n        \"name\": \"id\",\n        \"type\": \"INTEGER\"\n      }\n    ]\n  },\n  \"view\": {\n    \"query\": \"select 2\",\n    \"useLegacySql\": true\n  }\n}\n"
        }
    ]
}
```

---

### Feature 5.3: Insert Value Encoding

**As a developer**, I want to encode inserted row values recursively, so I can send typed literals inside row data using their wire values.

**Expected Behavior / Usage:**

The input is any row value, including nested objects, arrays, null, and typed literals. The output is the encoded JSON value. Typed literals are replaced by their stored wire values while ordinary objects and arrays retain their structure.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_insert_value_encoding.json`

```json
{
    "description": "Inserted row values are recursively encoded so typed literals become wire values while arrays and objects keep their original structure.",
    "cases": [
        {
            "input": {
                "operation": "encode_insert_value",
                "value": {
                    "id": {
                        "__custom": "integer",
                        "value": "123"
                    },
                    "day": {
                        "__custom": "date",
                        "value": "2020-01-02"
                    },
                    "items": [
                        1,
                        {
                            "__custom": "time",
                            "value": "01:02:03"
                        }
                    ]
                }
            },
            "expected_output": "{\n  \"id\": \"123\",\n  \"day\": \"2020-01-02\",\n  \"items\": [\n    1,\n    \"01:02:03\"\n  ]\n}\n"
        },
        {
            "input": {
                "operation": "encode_insert_value",
                "value": null
            },
            "expected_output": "null\n"
        }
    ]
}
```

---

### Feature 6: Resource Reference Construction

**As a developer**, I want to construct dataset and table references with locations, so I can target datasets and tables consistently across regional deployments.

**Expected Behavior / Usage:**

The input supplies project, dataset, table, and optional location data. The output is a JSON object showing the resulting reference identifiers and location. Dataset references inherit a client default location, table references inherit their dataset location, and an explicit table location overrides the inherited one.

**Test Cases:** `rcb_tests/public_test_cases/feature6_resource_references.json`

```json
{
    "description": "Dataset and table reference factories retain identifiers and propagate default locations unless an explicit child location is supplied.",
    "cases": [
        {
            "input": {
                "operation": "dataset_reference",
                "projectId": "project-a",
                "datasetId": "analytics",
                "clientLocation": "EU"
            },
            "expected_output": "{\n  \"id\": \"analytics\",\n  \"location\": \"EU\",\n  \"parentProjectId\": \"project-a\"\n}\n"
        },
        {
            "input": {
                "operation": "table_reference",
                "datasetId": "analytics",
                "tableId": "events",
                "datasetLocation": "EU"
            },
            "expected_output": "{\n  \"id\": \"events\",\n  \"location\": \"EU\",\n  \"datasetId\": \"analytics\"\n}\n"
        }
    ]
}
```

---

### Feature 7.1: Create Table Request Construction

**As a developer**, I want to build table creation API requests, so I can create tables while preserving formatted metadata and regional placement.

**Expected Behavior / Usage:**

The input supplies a dataset identifier, table identifier, optional dataset location, and table metadata. The output is the API request object. The request uses the collection path for tables, includes a tableReference with the table identifier, formats metadata shortcuts, and includes the inherited location when supplied.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_create_table_requests.json`

```json
{
    "description": "Creating a table produces an API request with the table identifier, formatted metadata, and inherited location when available.",
    "cases": [
        {
            "input": {
                "operation": "dataset_create_table_request",
                "datasetId": "analytics",
                "tableId": "events",
                "datasetLocation": "EU",
                "options": {
                    "schema": "name:string, age:integer",
                    "name": "Events"
                }
            },
            "expected_output": "{\n  \"method\": \"POST\",\n  \"uri\": \"/tables\",\n  \"json\": {\n    \"schema\": {\n      \"fields\": [\n        {\n          \"name\": \"name\",\n          \"type\": \"STRING\"\n        },\n        {\n          \"name\": \"age\",\n          \"type\": \"INTEGER\"\n        }\n      ]\n    },\n    \"friendlyName\": \"Events\",\n    \"tableReference\": {\n      \"datasetId\": \"analytics\",\n      \"projectId\": \"project-id\",\n      \"tableId\": \"events\"\n    }\n  }\n}\n"
        },
        {
            "input": {
                "operation": "dataset_create_table_request",
                "datasetId": "analytics",
                "tableId": "events",
                "options": {
                    "schema": [
                        {
                            "name": "id",
                            "type": "INTEGER"
                        }
                    ]
                }
            },
            "expected_output": "{\n  \"method\": \"POST\",\n  \"uri\": \"/tables\",\n  \"json\": {\n    \"schema\": {\n      \"fields\": [\n        {\n          \"name\": \"id\",\n          \"type\": \"INTEGER\"\n        }\n      ]\n    },\n    \"tableReference\": {\n      \"datasetId\": \"analytics\",\n      \"projectId\": \"project-id\",\n      \"tableId\": \"events\"\n    }\n  }\n}\n"
        }
    ]
}
```

---

### Feature 7.2: Query Job Request Construction

**As a developer**, I want to build query job configurations, so I can run queries with parameters and job-level controls.

**Expected Behavior / Usage:**

The input supplies query job options such as SQL text, named or positional parameters, explicit parameter types, dry-run flag, labels, timeout, job identifier or prefix, destination table, and client location. The output is the job creation request object. The query configuration uses standard SQL by default, serializes parameters, separates job-level fields from query configuration fields, and includes location when supplied.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_query_job_requests.json`

```json
{
    "description": "Creating a query job produces a job configuration with standard SQL, parameter mode, serialized parameters, dry-run settings, labels, timeout, job id or prefix, destination tables, and location where supplied.",
    "cases": [
        {
            "input": {
                "operation": "query_job_request",
                "options": {
                    "query": "SELECT @name AS name",
                    "params": {
                        "name": "Ada"
                    },
                    "types": {
                        "name": "STRING"
                    },
                    "dryRun": true,
                    "labels": {
                        "purpose": "test"
                    }
                }
            },
            "expected_output": "{\n  \"configuration\": {\n    \"query\": {\n      \"useLegacySql\": false,\n      \"query\": \"SELECT @name AS name\",\n      \"types\": {\n        \"name\": \"STRING\"\n      },\n      \"parameterMode\": \"named\",\n      \"queryParameters\": [\n        {\n          \"parameterType\": {\n            \"type\": \"STRING\"\n          },\n          \"parameterValue\": {\n            \"value\": \"Ada\"\n          },\n          \"name\": \"name\"\n        }\n      ]\n    },\n    \"dryRun\": true,\n    \"labels\": {\n      \"purpose\": \"test\"\n    }\n  }\n}\n"
        },
        {
            "input": {
                "operation": "query_job_request",
                "clientLocation": "EU",
                "options": {
                    "query": "SELECT ? AS value",
                    "params": [
                        1
                    ],
                    "types": [
                        "INT64"
                    ],
                    "jobPrefix": "pre-",
                    "jobTimeoutMs": 1000
                }
            },
            "expected_output": "{\n  \"configuration\": {\n    \"query\": {\n      \"useLegacySql\": false,\n      \"query\": \"SELECT ? AS value\",\n      \"types\": [\n        \"INT64\"\n      ],\n      \"parameterMode\": \"positional\",\n      \"queryParameters\": [\n        {\n          \"parameterType\": {\n            \"type\": \"INT64\"\n          },\n          \"parameterValue\": {\n            \"value\": 1\n          }\n        }\n      ]\n    },\n    \"jobTimeoutMs\": 1000\n  },\n  \"jobPrefix\": \"pre-\"\n}\n"
        }
    ]
}
```

---

### Feature 7.3: Extract Job Request Construction

**As a developer**, I want to build extract job configurations for models and tables, so I can export resources to object storage using the expected service request shape.

**Expected Behavior / Usage:**

The input supplies a source resource, destination URI or file reference, export format, compression flag, and job-level options. The output is the job creation request object with source resource reference, destinationUris, destinationFormat, compression, job id or prefix, and location where applicable. Unknown export formats or invalid destination kinds produce normalized error output.

**Test Cases:** `rcb_tests/public_test_cases/feature7_3_extract_job_requests.json`

```json
{
    "description": "Extracting models or tables produces job configurations that identify the source resource, destination URIs, destination format, compression, job id or prefix, and location where applicable.",
    "cases": [
        {
            "input": {
                "operation": "model_extract_job_request",
                "destination": "gs://bucket-name/model-export",
                "options": {
                    "format": "ml_tf_saved_model",
                    "jobPrefix": "abc-"
                }
            },
            "expected_output": "{\n  \"configuration\": {\n    \"extract\": {\n      \"destinationUris\": [\n        \"gs://bucket-name/model-export\"\n      ],\n      \"destinationFormat\": \"ML_TF_SAVED_MODEL\",\n      \"sourceModel\": {\n        \"datasetId\": \"dataset-id\",\n        \"projectId\": \"project-id\",\n        \"modelId\": \"model-id\"\n      }\n    }\n  },\n  \"jobPrefix\": \"abc-\"\n}\n"
        },
        {
            "input": {
                "operation": "model_extract_job_request",
                "destination": "gs://bucket-name/model-export",
                "options": {
                    "format": "interpretive_dance"
                }
            },
            "expected_output": "error=invalid_destination_format\n"
        }
    ]
}
```

---

### Feature 7.4: Copy Job Request Construction

**As a developer**, I want to build table copy job configurations, so I can copy table data between table references without hand-writing request bodies.

**Expected Behavior / Usage:**

The input supplies source and destination table references plus optional job-level settings. The output is the job creation request object containing sourceTable, destinationTable, and job id or prefix. Location is included when the source table is regional.

**Test Cases:** `rcb_tests/public_test_cases/feature7_4_copy_job_requests.json`

```json
{
    "description": "Copying table data produces a job configuration that points to source and destination table references and carries job-level options.",
    "cases": [
        {
            "input": {
                "operation": "table_copy_job_request",
                "sourceDatasetId": "ds1",
                "sourceTableId": "src",
                "destDatasetId": "ds2",
                "destTableId": "dst",
                "options": {
                    "jobId": "copy-job"
                }
            },
            "expected_output": "{\n  \"configuration\": {\n    \"copy\": {\n      \"destinationTable\": {\n        \"datasetId\": \"ds2\",\n        \"projectId\": \"project-id\",\n        \"tableId\": \"dst\"\n      },\n      \"sourceTable\": {\n        \"datasetId\": \"ds1\",\n        \"projectId\": \"project-id\",\n        \"tableId\": \"src\"\n      }\n    }\n  },\n  \"jobId\": \"copy-job\"\n}\n"
        },
        {
            "input": {
                "operation": "table_copy_job_request",
                "sourceProjectId": "p1",
                "sourceDatasetId": "ds1",
                "sourceTableId": "src",
                "destProjectId": "p2",
                "destDatasetId": "ds2",
                "destTableId": "dst",
                "location": "EU",
                "options": {
                    "jobPrefix": "copy-"
                }
            },
            "expected_output": "{\n  \"configuration\": {\n    \"copy\": {\n      \"destinationTable\": {\n        \"datasetId\": \"ds2\",\n        \"projectId\": \"p2\",\n        \"tableId\": \"dst\"\n      },\n      \"sourceTable\": {\n        \"datasetId\": \"ds1\",\n        \"projectId\": \"p1\",\n        \"tableId\": \"src\"\n      }\n    }\n  },\n  \"jobPrefix\": \"copy-\",\n  \"location\": \"EU\"\n}\n"
        }
    ]
}
```

---

### Feature 8.1: Insert-All Request Construction

**As a developer**, I want to build row insertion API requests, so I can insert one or more rows with encoded JSON and caller-controlled insert options.

**Expected Behavior / Usage:**

The input supplies row data and insertion options. The output is the insert-all API request object. Non-raw rows are wrapped in json objects, typed values are encoded, insert identifiers are included unless disabled, raw rows pass through as supplied, and empty row input produces a normalized error output.

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_insert_requests.json`

```json
{
    "description": "Inserting rows produces an insert-all API request that encodes row JSON, adds insert identifiers by default, supports raw rows, and reports empty input as a neutral error.",
    "cases": [
        {
            "input": {
                "operation": "table_insert_request",
                "rows": {
                    "name": "Ada",
                    "day": {
                        "__custom": "date",
                        "value": "2020-01-02"
                    }
                },
                "options": {
                    "createInsertId": false
                }
            },
            "expected_output": "{\n  \"method\": \"POST\",\n  \"uri\": \"/insertAll\",\n  \"json\": {\n    \"rows\": [\n      {\n        \"json\": {\n          \"name\": \"Ada\",\n          \"day\": \"2020-01-02\"\n        }\n      }\n    ]\n  }\n}\n"
        },
        {
            "input": {
                "operation": "table_insert_request",
                "rows": [
                    {
                        "insertId": "1",
                        "json": {
                            "name": "Ada"
                        }
                    }
                ],
                "options": {
                    "raw": true,
                    "skipInvalidRows": true
                }
            },
            "expected_output": "{\n  \"method\": \"POST\",\n  \"uri\": \"/insertAll\",\n  \"json\": {\n    \"skipInvalidRows\": true,\n    \"rows\": [\n      {\n        \"insertId\": \"1\",\n        \"json\": {\n          \"name\": \"Ada\"\n        }\n      }\n    ]\n  }\n}\n"
        }
    ]
}
```

---

### Feature 8.2: Table IAM Request Construction

**As a developer**, I want to build table policy and permission API requests, so I can manage access policy calls with predictable request bodies.

**Expected Behavior / Usage:**

The input supplies an IAM action and its policy, option, or permission data. The output is the API request object for getting a policy, setting a policy, or testing permissions. Only policy version 1 is supported; unsupported policy versions produce a normalized error output.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_iam_requests.json`

```json
{
    "description": "Table IAM operations produce policy and permission request bodies, and unsupported policy versions are reported as a neutral error category.",
    "cases": [
        {
            "input": {
                "operation": "table_iam_request",
                "action": "get",
                "options": {
                    "requestedPolicyVersion": 1
                }
            },
            "expected_output": "{\n  \"method\": \"POST\",\n  \"uri\": \"/:getIamPolicy\",\n  \"json\": {\n    \"options\": {\n      \"requestedPolicyVersion\": 1\n    }\n  }\n}\n"
        },
        {
            "input": {
                "operation": "table_iam_request",
                "action": "set",
                "policy": {
                    "version": 1,
                    "bindings": [
                        {
                            "role": "reader",
                            "members": [
                                "user:a@example.com"
                            ]
                        }
                    ]
                },
                "options": {
                    "etag": "abc"
                }
            },
            "expected_output": "{\n  \"method\": \"POST\",\n  \"uri\": \"/:setIamPolicy\",\n  \"json\": {\n    \"etag\": \"abc\",\n    \"policy\": {\n      \"version\": 1,\n      \"bindings\": [\n        {\n          \"role\": \"reader\",\n          \"members\": [\n            \"user:a@example.com\"\n          ]\n        }\n      ]\n    }\n  }\n}\n"
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
- conforms to standard array type inference rules used elsewhere
- maps nested structure definitions to their deep types
