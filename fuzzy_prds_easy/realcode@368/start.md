## Product Requirement Document

# Time-Series Client Adapter - Line Protocol, Query Construction, HTTP Writes, and Logging Contracts

## Project Goal

Build a time-series database client library that allows developers to serialize measurement samples, compose safe query strings, send write requests over HTTP, and route diagnostic logs without hand-writing protocol formatting or transport boilerplate.

---

## Background & Problem

Without this library/tool, developers are forced to manually escape line protocol, merge tags, convert timestamps, quote query values, construct write URLs, compress request bodies, classify HTTP write failures, and wire logging callbacks. This leads to repetitive code, subtle protocol bugs, inconsistent error handling, and difficult-to-test integrations.

With this library/tool, developers provide structured samples, query values, write configuration, and logging callbacks, and the system produces deterministic protocol strings, observable HTTP behavior, and normalized adapter output.

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

### Feature 1: Measurement Line Protocol Serialization

**As a developer**, I want to serialize structured measurement samples into protocol text, so I can persist time-series data without manual escaping or timestamp conversion.

**Expected Behavior / Usage:**

*1.1 Field Encoding and Escaping — Serialize a measurement sample into line protocol by requiring a measurement name and at least one valid field.*

Serialize a measurement sample into line protocol by requiring a measurement name and at least one valid field. The output must place tags before fields, sort tag and field keys consistently, escape spaces, commas, and quotes according to line protocol rules, omit empty field keys and null-like string fields, render booleans as `T` or `F`, truncate integer-like numeric values, suffix signed integers with `i`, and omit the timestamp when the input timestamp is empty.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_line_protocol_fields.json`

```json
{
    "description": "Serializes measurement samples with typed fields, sorted fields, escaped names, escaped tags, omitted empty values, and empty timestamps.",
    "cases": [
        {
            "input": {
                "domain": "line_protocol",
                "measurement": "m0",
                "fields": [
                    {
                        "key": "a",
                        "type": "float",
                        "value": 9.2
                    },
                    {
                        "key": "b",
                        "type": "integer",
                        "value": 9.2
                    },
                    {
                        "key": "",
                        "type": "string",
                        "value": 9.2
                    },
                    {
                        "key": "d",
                        "type": "string",
                        "value": null
                    },
                    {
                        "key": "e",
                        "type": "string"
                    },
                    {
                        "key": "f",
                        "type": "string",
                        "value": "9"
                    }
                ],
                "timestamp": ""
            },
            "expected_output": "line_protocol=m0 a=9.2,b=9i,f=\"9\"\n"
        },
        {
            "input": {
                "domain": "line_protocol",
                "measurement": "meas, 2",
                "tags": [
                    {
                        "key": "tag3",
                        "value": "a"
                    },
                    {
                        "key": "tag2",
                        "value": "b"
                    },
                    {
                        "key": "tag1",
                        "value": "c"
                    }
                ],
                "fields": [
                    {
                        "key": "f9",
                        "type": "float",
                        "value": 9.2
                    },
                    {
                        "key": "f8",
                        "type": "string",
                        "value": 8.2
                    },
                    {
                        "key": "f7",
                        "type": "boolean",
                        "value": 7.2
                    },
                    {
                        "key": "f6",
                        "type": "integer",
                        "value": 6.2
                    }
                ],
                "timestamp": "12345"
            },
            "expected_output": "line_protocol=meas\\,\\ 2,tag1=c,tag2=b,tag3=a f6=6i,f7=T,f8=\"8.2\",f9=9.2 12345\n"
        },
        {
            "input": {
                "domain": "line_protocol",
                "measurement": "m3",
                "fields": [
                    {
                        "key": "a",
                        "type": "integer",
                        "value": "9.2"
                    },
                    {
                        "key": "b",
                        "type": "float",
                        "value": "8.2"
                    },
                    {
                        "key": "c",
                        "type": "boolean",
                        "value": ""
                    },
                    {
                        "key": "",
                        "type": "boolean",
                        "value": ""
                    }
                ],
                "timestamp": ""
            },
            "expected_output": "line_protocol=m3 a=9i,b=8.2,c=F\n"
        },
        {
            "input": {
                "domain": "line_protocol",
                "measurement": "m11",
                "fields": [
                    {
                        "key": "f",
                        "type": "string",
                        "value": "\\\""
                    }
                ],
                "timestamp": ""
            },
            "expected_output": "line_protocol=m11 f=\"\\\\\\\"\"\n"
        }
    ]
}
```

*1.2 Default Tags and Timestamp Conversion — Serialize a measurement sample while applying caller-provided default tags.*

Serialize a measurement sample while applying caller-provided default tags. Default tags must be merged with explicit tags, explicit tags must override default values for the same key, and the final tag set must be sorted in the line protocol output. When a timestamp converter is supplied and the sample has no explicit timestamp, the converted timestamp must be appended as the final token.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_line_protocol_defaults.json`

```json
{
    "description": "Serializes measurement samples while applying default tags, allowing explicit tags to override defaults, and using a provided timestamp converter when no timestamp is embedded in the sample.",
    "cases": [
        {
            "input": {
                "domain": "line_protocol",
                "measurement": "m8",
                "fields": [
                    {
                        "key": "a",
                        "type": "boolean",
                        "value": true
                    }
                ],
                "timestamp": "",
                "settings": {
                    "default_tags": {
                        "tag3": "a",
                        "tag2": "b",
                        "tag1": "c"
                    }
                }
            },
            "expected_output": "line_protocol=m8,tag1=c,tag2=b,tag3=a a=T\n"
        },
        {
            "input": {
                "domain": "line_protocol",
                "measurement": "m9",
                "tags": [
                    {
                        "key": "tag2",
                        "value": "x"
                    }
                ],
                "fields": [
                    {
                        "key": "a",
                        "type": "boolean",
                        "value": true
                    }
                ],
                "timestamp": "",
                "settings": {
                    "default_tags": {
                        "tag3": "a",
                        "tag2": "b",
                        "tag1": "c"
                    }
                }
            },
            "expected_output": "line_protocol=m9,tag1=c,tag2=x,tag3=a a=T\n"
        },
        {
            "input": {
                "domain": "line_protocol",
                "measurement": "m10",
                "tags": [
                    {
                        "key": "tag1",
                        "value": "x"
                    }
                ],
                "fields": [
                    {
                        "key": "a",
                        "type": "boolean",
                        "value": true
                    }
                ],
                "settings": {
                    "default_tags": {
                        "tag3": "a",
                        "tag2": "b",
                        "tag1": "c"
                    },
                    "converted_timestamp": "11111"
                }
            },
            "expected_output": "line_protocol=m10,tag1=x,tag2=b,tag3=a a=T 11111\n"
        }
    ]
}
```

*1.3 Explicit Timestamp Handling — Serialize explicit timestamp inputs in line protocol.*

Serialize explicit timestamp inputs in line protocol. An empty timestamp produces no timestamp token, a numeric timestamp is truncated to a whole unit and emitted as-is, a date-like timestamp is converted using the selected precision, and an unknown timestamp-like value is emitted from its textual representation rather than rejected.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_line_protocol_timestamps.json`

```json
{
    "description": "Serializes explicit timestamps by omitting an empty timestamp, truncating numeric timestamps to whole units, converting dates to the selected precision, and passing unknown timestamp values through as text.",
    "cases": [
        {
            "input": {
                "domain": "line_protocol",
                "measurement": "a",
                "fields": [
                    {
                        "key": "b",
                        "type": "float",
                        "value": 1
                    }
                ],
                "timestamp": ""
            },
            "expected_output": "line_protocol=a b=1\n"
        },
        {
            "input": {
                "domain": "line_protocol",
                "measurement": "a",
                "fields": [
                    {
                        "key": "b",
                        "type": "float",
                        "value": 1
                    }
                ],
                "timestamp": 1.2
            },
            "expected_output": "line_protocol=a b=1 1\n"
        },
        {
            "input": {
                "domain": "line_protocol",
                "measurement": "test",
                "fields": [
                    {
                        "key": "value",
                        "type": "float",
                        "value": 6
                    }
                ],
                "timestamp": {
                    "encoded": "date",
                    "value": 3
                },
                "settings": {
                    "default_tags": {
                        "xtra": "1"
                    },
                    "converted_timestamp": "3000000"
                }
            },
            "expected_output": "line_protocol=test,xtra=1 value=6 3000000\n"
        },
        {
            "input": {
                "domain": "line_protocol",
                "measurement": "tst",
                "fields": [
                    {
                        "key": "a",
                        "type": "float",
                        "value": 1
                    }
                ],
                "timestamp": {
                    "encoded": "object_to_string",
                    "value": "any"
                }
            },
            "expected_output": "line_protocol=tst a=1 any\n"
        }
    ]
}
```

*1.4 Numeric Field Validation Errors — Reject invalid numeric fields before line protocol is emitted.*

Reject invalid numeric fields before line protocol is emitted. Invalid signed integer, float, and unsigned integer values must produce language-neutral validation output naming the field type and field key, without exposing host runtime exception names or runtime-generated error messages.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_line_protocol_invalid_values.json`

```json
{
    "description": "Rejects invalid numeric field values using language-neutral field validation errors that identify the field type and field name rather than a runtime exception string.",
    "cases": [
        {
            "input": {
                "domain": "line_protocol",
                "measurement": "m6",
                "fields": [
                    {
                        "key": "a",
                        "type": "integer"
                    }
                ],
                "timestamp": ""
            },
            "expected_output": "error=invalid_field_value\nfield_type=integer\nfield=a\n"
        },
        {
            "input": {
                "domain": "line_protocol",
                "measurement": "m7",
                "fields": [
                    {
                        "key": "a",
                        "type": "float"
                    }
                ],
                "timestamp": ""
            },
            "expected_output": "error=invalid_field_value\nfield_type=float\nfield=a\n"
        },
        {
            "input": {
                "domain": "line_protocol",
                "measurement": "uintNegativeNumber",
                "fields": [
                    {
                        "key": "f",
                        "type": "unsigned_integer",
                        "value": -1
                    }
                ],
                "timestamp": ""
            },
            "expected_output": "error=invalid_field_value\nfield_type=unsigned_integer\nfield=f\n"
        },
        {
            "input": {
                "domain": "line_protocol",
                "measurement": "uintTooLargeString",
                "fields": [
                    {
                        "key": "f",
                        "type": "unsigned_integer",
                        "value": "18446744073709551616"
                    }
                ],
                "timestamp": ""
            },
            "expected_output": "error=invalid_field_value\nfield_type=unsigned_integer\nfield=f\n"
        }
    ]
}
```

---

### Feature 2: Query Fragment and Template Construction

**As a developer**, I want to construct safe query fragments and complete query strings, so I can avoid injection-prone string concatenation while preserving query syntax.

**Expected Behavior / Usage:**

*2.1 Explicit Query Literal Rendering — Render explicitly typed values into query-language fragments.*

Render explicitly typed values into query-language fragments. Raw expressions pass through unchanged, integers and floats render as numeric text, booleans render as `true` or `false`, strings are quoted, durations and date-times use constructor-style fragments, and regular expressions use a compiled regular-expression fragment.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_query_literals.json`

```json
{
    "description": "Renders primitive and wrapped query values as query-language fragments with appropriate quoting, escaping, and constructor syntax.",
    "cases": [
        {
            "input": {
                "domain": "query_literal",
                "value_type": "raw_expression",
                "value": "12345"
            },
            "expected_output": "query_fragment=12345\n"
        },
        {
            "input": {
                "domain": "query_literal",
                "value_type": "integer",
                "value": 123
            },
            "expected_output": "query_fragment=123\n"
        },
        {
            "input": {
                "domain": "query_literal",
                "value_type": "boolean",
                "value": 1
            },
            "expected_output": "query_fragment=true\n"
        },
        {
            "input": {
                "domain": "query_literal",
                "value_type": "duration",
                "value": "1ms"
            },
            "expected_output": "query_fragment=duration(v: \"1ms\")\n"
        },
        {
            "input": {
                "domain": "query_literal",
                "value_type": "date_time",
                "value": "2020-06-06T21:56:00.000Z"
            },
            "expected_output": "query_fragment=time(v: \"2020-06-06T21:56:00.000Z\")\n"
        },
        {
            "input": {
                "domain": "query_literal",
                "value_type": "regular_expression",
                "value": "/abc/"
            },
            "expected_output": "query_fragment=regexp.compile(v: \"/abc/\")\n"
        },
        {
            "input": {
                "domain": "query_literal",
                "value_type": "string",
                "value": "abc"
            },
            "expected_output": "query_fragment=\"abc\"\n"
        }
    ]
}
```

*2.2 Automatic Query Value Conversion — Convert mixed values into query-language fragments automatically.*

Convert mixed values into query-language fragments automatically. Null-like values, undefined-like values, strings with control characters, dates, regular expressions, arrays, and pre-wrapped query fragments must each render to the query text shown by the contract, with strings escaped so interpolation cannot break the query syntax.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_query_value_conversion.json`

```json
{
    "description": "Automatically converts mixed runtime values into query-language fragments, including null-like values, numbers, dates, regular expressions, arrays, escaped strings, symbols, and values that are already query fragments.",
    "cases": [
        {
            "input": {
                "domain": "query_literal",
                "value_type": "automatic",
                "value": {
                    "encoded": "null"
                }
            },
            "expected_output": "query_fragment=null\n"
        },
        {
            "input": {
                "domain": "query_literal",
                "value_type": "automatic",
                "value": {
                    "encoded": "undefined"
                }
            },
            "expected_output": "query_fragment=\n"
        },
        {
            "input": {
                "domain": "query_literal",
                "value_type": "automatic",
                "value": "abc\n\r\t\\\"def"
            },
            "expected_output": "query_fragment=\"abc\\n\\r\\t\\\\\\\"def\"\n"
        },
        {
            "input": {
                "domain": "query_literal",
                "value_type": "automatic",
                "value": {
                    "encoded": "date",
                    "value": 1589521447471
                }
            },
            "expected_output": "query_fragment=2020-05-15T05:44:07.471Z\n"
        },
        {
            "input": {
                "domain": "query_literal",
                "value_type": "automatic",
                "value": {
                    "encoded": "regexp",
                    "pattern": "abc"
                }
            },
            "expected_output": "query_fragment=regexp.compile(v: \"/abc/\")\n"
        },
        {
            "input": {
                "domain": "query_literal",
                "value_type": "automatic",
                "value": [
                    "a\"$d"
                ]
            },
            "expected_output": "query_fragment=[\"a\\\"$d\"]\n"
        },
        {
            "input": {
                "domain": "query_literal",
                "value_type": "automatic",
                "value": {
                    "encoded": "expression",
                    "value": "1ms"
                }
            },
            "expected_output": "query_fragment=1ms\n"
        }
    ]
}
```

*2.3 Query Template Interpolation — Build complete query strings from literal segments and interpolation values.*

Build complete query strings from literal segments and interpolation values. Literal query text must be preserved, numeric values must be inserted as numeric fragments, ordinary strings must be quoted unless they are interpolated inside an already quoted literal region, and nested query fragments must be inserted without double-quoting.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_query_template_interpolation.json`

```json
{
    "description": "Builds full query strings by preserving literal query text while safely interpolating numbers, strings, nested query fragments, empty fragments, and wrapped string positions.",
    "cases": [
        {
            "input": {
                "domain": "query_template",
                "segments": [
                    "from(bucket:\"my-bucket\") |> range(start: 0) |> filter(fn: (r) => r._measurement == \"temperature\")"
                ],
                "interpolations": []
            },
            "expected_output": "query=from(bucket:\"my-bucket\") |> range(start: 0) |> filter(fn: (r) => r._measurement == \"temperature\")\n"
        },
        {
            "input": {
                "domain": "query_template",
                "segments": [
                    "from(bucket:\"my-bucket\") |> range(start: ",
                    ") |> filter(fn: (r) => r._measurement == ",
                    ")"
                ],
                "interpolations": [
                    0,
                    "temperature"
                ]
            },
            "expected_output": "query=from(bucket:\"my-bucket\") |> range(start: 0) |> filter(fn: (r) => r._measurement == \"temperature\")\n"
        },
        {
            "input": {
                "domain": "query_template",
                "segments": [
                    "from(bucket:\"",
                    "\")"
                ],
                "interpolations": [
                    "my-bucket"
                ]
            },
            "expected_output": "query=from(bucket:\"my-bucket\")\n"
        },
        {
            "input": {
                "domain": "query_template",
                "segments": [
                    "",
                    " |> range(start: ",
                    ")\""
                ],
                "interpolations": [
                    {
                        "encoded": "expression",
                        "value": "from(bucket:\"my-bucket\")"
                    },
                    0
                ]
            },
            "expected_output": "query=from(bucket:\"my-bucket\") |> range(start: 0)\"\n"
        }
    ]
}
```

*2.4 Query Template Error Normalization — Report query-construction errors in language-neutral form.*

Report query-construction errors in language-neutral form. A missing interpolation value must produce a missing-value category, and a mismatch between literal segments and interpolation count must produce an invalid-template-shape category.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_query_template_errors.json`

```json
{
    "description": "Reports language-neutral query-construction errors when a template interpolation is missing or the template shape is invalid.",
    "cases": [
        {
            "input": {
                "domain": "query_template",
                "segments": [
                    "",
                    ""
                ],
                "interpolations": [
                    {
                        "encoded": "undefined"
                    }
                ]
            },
            "expected_output": "error=missing_interpolation_value\n"
        },
        {
            "input": {
                "domain": "query_template",
                "segments": [
                    "1",
                    "2"
                ],
                "interpolations": []
            },
            "expected_output": "error=invalid_template_shape\n"
        }
    ]
}
```

---

### Feature 3: HTTP Write Client Behavior

**As a developer**, I want to send line protocol through an HTTP write interface with observable transport semantics, so I can verify request routing, headers, compression, and failure handling through black-box signals.

**Expected Behavior / Usage:**

*3.1 HTTP Write Request Success — Send encoded line protocol to the configured HTTP write route for the target organization, bucket, and precision.*

Send encoded line protocol to the configured HTTP write route for the target organization, bucket, and precision. A successful no-content response must report the route, authorization header, content encoding, request count, accepted line count, failed line count, and exact request body observed by the server.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_write_success_and_retry.json`

```json
{
    "description": "Writes line protocol to the configured HTTP write route, retries a retryable response once, then reports the accepted body, authorization header, route, request count, and successful line count.",
    "cases": [
        {
            "input": {
                "domain": "write_request",
                "destination": {
                    "org": "org",
                    "bucket": "bucket",
                    "precision": "ns"
                },
                "server": {
                    "url": "http://fake:8086",
                    "token": "a",
                    "responses": [
                        204
                    ]
                },
                "write": {
                    "flush_interval_ms": 5,
                    "batch_size": 10,
                    "max_retries": 1,
                    "default_tags": {
                        "xtra": "1"
                    }
                },
                "points": [
                    {
                        "measurement": "test",
                        "tags": [
                            {
                                "key": "t",
                                "value": " "
                            }
                        ],
                        "fields": [
                            {
                                "key": "value",
                                "type": "float",
                                "value": 1
                            }
                        ],
                        "timestamp": ""
                    }
                ],
                "expected_observed_lines": 1
            },
            "expected_output": "route=/api/v2/write?org=org&bucket=bucket&precision=ns\nauthorization=Token a\ncontent_encoding=identity\nrequest_count=1\nsuccess_lines=1\nfailed_lines=0\nbody_000=test,t=\\ ,xtra=1 value=1\n"
        }
    ]
}
```

*3.2 Compressed HTTP Write Body — When compression is enabled by the configured threshold, the write request must use gzip content encoding.*

When compression is enabled by the configured threshold, the write request must use gzip content encoding. The observable contract reports the route, authorization header, content encoding, request count, accepted and failed line counts, and the decompressed line protocol body received by the server.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_write_gzip.json`

```json
{
    "description": "Compresses write request bodies when the compression threshold requires it while preserving the decompressed line protocol payload and normal write route semantics.",
    "cases": [
        {
            "input": {
                "domain": "write_request",
                "destination": {
                    "org": "org",
                    "bucket": "bucket",
                    "precision": "ns"
                },
                "server": {
                    "url": "http://fake:8086",
                    "token": "a",
                    "responses": [
                        204
                    ]
                },
                "write": {
                    "flush_interval_ms": 5,
                    "batch_size": 10,
                    "max_retries": 1,
                    "default_tags": {
                        "xtra": "1"
                    },
                    "gzip_threshold": 0
                },
                "points": [
                    {
                        "measurement": "test",
                        "tags": [
                            {
                                "key": "t",
                                "value": " "
                            }
                        ],
                        "fields": [
                            {
                                "key": "value",
                                "type": "float",
                                "value": 1
                            }
                        ],
                        "timestamp": ""
                    }
                ],
                "expected_observed_lines": 1
            },
            "expected_output": "route=/api/v2/write?org=org&bucket=bucket&precision=ns\nauthorization=Token a\ncontent_encoding=gzip\nrequest_count=1\nsuccess_lines=1\nfailed_lines=0\nbody_000=test,t=\\ ,xtra=1 value=1\n"
        }
    ]
}
```

*3.3 HTTP Write Rejection — Treat any HTTP write response status other than the no-content success status as a rejected write.*

Treat any HTTP write response status other than the no-content success status as a rejected write. The output must include a neutral write-rejected error, the returned status code, route, authorization header, content encoding, request count, failed line count, successful line count, and submitted body.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_write_rejection.json`

```json
{
    "description": "Treats any HTTP write status other than the no-content success status as a rejected write and reports the route, status code, authorization header, failed line count, and submitted body.",
    "cases": [
        {
            "input": {
                "domain": "write_request",
                "destination": {
                    "org": "org",
                    "bucket": "bucket",
                    "precision": "ns"
                },
                "server": {
                    "url": "http://fake:8086",
                    "token": "a",
                    "responses": [
                        200
                    ]
                },
                "write": {
                    "flush_interval_ms": 2,
                    "batch_size": 10,
                    "max_retries": 0,
                    "default_tags": {
                        "xtra": "1"
                    }
                },
                "points": [
                    {
                        "measurement": "test",
                        "fields": [
                            {
                                "key": "value",
                                "type": "float",
                                "value": 1
                            }
                        ]
                    }
                ],
                "expected_observed_lines": 1
            },
            "expected_output": "error=write_rejected\nstatus_code=200\nroute=/api/v2/write?org=org&bucket=bucket&precision=ns\nauthorization=Token a\ncontent_encoding=identity\nrequest_count=1\nsuccess_lines=0\nfailed_lines=1\nbody_000=test,xtra=1 value=1\n"
        }
    ]
}
```

*3.4 Custom Write Headers — Allow caller-supplied write headers to override default request headers.*

Allow caller-supplied write headers to override default request headers. The observable output must show that the custom authorization header reached the HTTP server while preserving the configured route, body format, and line-count accounting.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_write_headers.json`

```json
{
    "description": "Allows caller-supplied write headers to override the default authorization header while still using the configured write route and body format.",
    "cases": [
        {
            "input": {
                "domain": "write_request",
                "destination": {
                    "org": "org",
                    "bucket": "bucket",
                    "precision": "ns"
                },
                "server": {
                    "url": "http://fake:8086",
                    "token": "a",
                    "responses": [
                        204
                    ]
                },
                "write": {
                    "flush_interval_ms": 0,
                    "batch_size": 10,
                    "max_retries": 0,
                    "headers": {
                        "authorization": "Token customToken"
                    }
                },
                "points": [
                    {
                        "measurement": "test",
                        "fields": [
                            {
                                "key": "value",
                                "type": "float",
                                "value": 1
                            }
                        ]
                    }
                ],
                "expected_observed_lines": 1
            },
            "expected_output": "route=/api/v2/write?org=org&bucket=bucket&precision=ns\nauthorization=Token customToken\ncontent_encoding=identity\nrequest_count=1\nsuccess_lines=1\nfailed_lines=0\nbody_000=test value=1\n"
        }
    ]
}
```

*3.5 Closed Writer State — Reject attempts to enqueue records or points after the writer has been closed.*

Reject attempts to enqueue records or points after the writer has been closed. Each rejected enqueue attempt must produce a neutral closed-writer error and name the attempted operation, without exposing a host-runtime error identity or implementation-specific error sentence.

**Test Cases:** `rcb_tests/public_test_cases/feature3_5_writer_closed_state.json`

```json
{
    "description": "Rejects attempts to enqueue additional records or points after a writer has been closed, using a neutral closed-writer error that names the attempted operation.",
    "cases": [
        {
            "input": {
                "domain": "writer_state",
                "after_close": "single_record",
                "record": "text value=1"
            },
            "expected_output": "error=writer_closed\noperation=single_record\n"
        },
        {
            "input": {
                "domain": "writer_state",
                "after_close": "multiple_records",
                "records": [
                    "text value=1",
                    "text value=2"
                ]
            },
            "expected_output": "error=writer_closed\noperation=multiple_records\n"
        },
        {
            "input": {
                "domain": "writer_state",
                "after_close": "single_point",
                "point": {
                    "measurement": "test",
                    "fields": [
                        {
                            "key": "value",
                            "type": "float",
                            "value": 1
                        }
                    ],
                    "timestamp": ""
                }
            },
            "expected_output": "error=writer_closed\noperation=single_point\n"
        }
    ]
}
```

---

### Feature 4: Diagnostic Logging

**As a developer**, I want to route diagnostic events through caller-provided logging callbacks, so I can integrate diagnostics into application-specific logging systems.

**Expected Behavior / Usage:**

*4.1 Logger Delegation — Forward warning and error log events to a caller-supplied logger without changing the message text, optional error payload, or argument count.*

Forward warning and error log events to a caller-supplied logger without changing the message text, optional error payload, or argument count. The output must identify the level invoked and the exact payload observed by the supplied logger.

**Test Cases:** `rcb_tests/public_test_cases/feature4_logger_delegation.json`

```json
{
    "description": "Delegates warning and error log events to a caller-supplied logger without changing the message, optional error payload, or argument count.",
    "cases": [
        {
            "input": {
                "domain": "logger",
                "level": "error",
                "message": "    hey",
                "error": "you"
            },
            "expected_output": "level=error\nmessage=    hey\nerror=you\nargument_count=2\n"
        },
        {
            "input": {
                "domain": "logger",
                "level": "warn",
                "message": "    hey"
            },
            "expected_output": "level=warn\nmessage=    hey\nerror=\nargument_count=2\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_line_protocol_fields.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_line_protocol_fields@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- trunc to nearest whole unit
- raw value logic (see C014)
