## Product Requirement Document

# Metrics Collection and Exposition Library - Observable Metric Recording and Serving

## Project Goal

Build a metrics collection and exposition library that allows developers to record counters, gauges, histograms, summaries, and grouped metric registries, then expose those metrics as text or HTTP responses without hand-writing aggregation, validation, serialization, and serving logic.

---

## Background & Problem

Without this library/tool, developers are forced to manually track numeric samples, maintain cumulative distribution buckets, validate metric identifiers, format wire-compatible metric text, and implement HTTP scrape endpoints. This leads to repetitive code, subtle incompatibilities, error-prone escaping, and maintenance issues across services.

With this library/tool, developers use a focused metrics API and a separate execution adapter can exercise the observable behavior through JSON input and deterministic stdout output.

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

### Feature 1: Counter Accumulation

**As a developer**, I want to record monotonically accumulated event totals, so I can report exact totals after default and explicit increments.

**Expected Behavior / Usage:**

A counter starts at zero and exposes a single numeric total. Each increment without an amount adds one. Each increment with an amount adds that amount only when the operation is accepted by the underlying metric rules; inputs that attempt to reduce a counter must not lower the observed total.

**Test Cases:** `rcb_tests/public_test_cases/feature1_counter_accumulation.json`

```json
{
    "description": "Counter samples expose the accumulated non-negative increment total after a sequence of observations.",
    "cases": [
        {
            "input": {
                "feature": "counter",
                "operations": []
            },
            "expected_output": "value=0\n"
        },
        {
            "input": {
                "feature": "counter",
                "operations": [
                    {
                        "action": "increment"
                    }
                ]
            },
            "expected_output": "value=1\n"
        },
        {
            "input": {
                "feature": "counter",
                "operations": [
                    {
                        "action": "increment"
                    },
                    {
                        "action": "increment"
                    },
                    {
                        "action": "increment",
                        "value": 5
                    }
                ]
            },
            "expected_output": "value=7\n"
        },
        {
            "input": {
                "feature": "counter",
                "operations": [
                    {
                        "action": "increment",
                        "value": 5
                    },
                    {
                        "action": "increment",
                        "value": -5
                    }
                ]
            },
            "expected_output": "value=5\n"
        }
    ]
}
```

---

### Feature 2: Gauge Value Updates

**As a developer**, I want to track a numeric level that can move up, down, or be assigned directly, so I can represent current state such as resource levels.

**Expected Behavior / Usage:**

A gauge starts at zero and exposes a single numeric current value. Increment operations add to the current value, decrement operations subtract from it, and set operations replace it. Negative amounts are interpreted arithmetically, so adding a negative lowers the value and subtracting a negative raises it.

**Test Cases:** `rcb_tests/public_test_cases/feature2_gauge_value_updates.json`

```json
{
    "description": "Gauge samples expose the latest numeric value after increments, decrements, and direct assignments.",
    "cases": [
        {
            "input": {
                "feature": "gauge",
                "operations": []
            },
            "expected_output": "value=0\n"
        },
        {
            "input": {
                "feature": "gauge",
                "operations": [
                    {
                        "action": "increment"
                    },
                    {
                        "action": "increment"
                    },
                    {
                        "action": "increment",
                        "value": 5
                    }
                ]
            },
            "expected_output": "value=7\n"
        },
        {
            "input": {
                "feature": "gauge",
                "operations": [
                    {
                        "action": "increment",
                        "value": -1
                    }
                ]
            },
            "expected_output": "value=-1\n"
        },
        {
            "input": {
                "feature": "gauge",
                "operations": [
                    {
                        "action": "set",
                        "value": 5
                    },
                    {
                        "action": "decrement"
                    }
                ]
            },
            "expected_output": "value=4\n"
        },
        {
            "input": {
                "feature": "gauge",
                "operations": [
                    {
                        "action": "decrement",
                        "value": -1
                    }
                ]
            },
            "expected_output": "value=1\n"
        },
        {
            "input": {
                "feature": "gauge",
                "operations": [
                    {
                        "action": "set",
                        "value": 3
                    },
                    {
                        "action": "set",
                        "value": 8
                    },
                    {
                        "action": "set",
                        "value": 1
                    }
                ]
            },
            "expected_output": "value=1\n"
        }
    ]
}
```

---

### Feature 3: Histogram Bucket Aggregation

**As a developer**, I want to record observations into cumulative buckets, so I can summarize distributions with counts and sums.

**Expected Behavior / Usage:**

A histogram is configured with finite bucket upper bounds and always reports an additional positive-infinity bucket. Observations update the total sample count, total sample sum, and every cumulative bucket whose upper bound includes the observed value. Batch bucket updates accept one increment per reported bucket and a total sum; if the number of increments does not match the number of reported buckets, output a neutral invalid bucket-increment error.

**Test Cases:** `rcb_tests/public_test_cases/feature3_histogram_buckets.json`

```json
{
    "description": "Histogram samples expose total count, total sum, and cumulative bucket counts for configured upper bounds plus an infinity bucket.",
    "cases": [
        {
            "input": {
                "feature": "histogram",
                "buckets": [],
                "operations": []
            },
            "expected_output": "sample_count=0\nsample_sum=0\nbucket_le=+Inf count=0\n"
        },
        {
            "input": {
                "feature": "histogram",
                "buckets": [
                    1,
                    2
                ],
                "operations": []
            },
            "expected_output": "sample_count=0\nsample_sum=0\nbucket_le=1 count=0\nbucket_le=2 count=0\nbucket_le=+Inf count=0\n"
        },
        {
            "input": {
                "feature": "histogram",
                "buckets": [
                    1,
                    2
                ],
                "operations": [
                    {
                        "action": "observe",
                        "value": 0
                    },
                    {
                        "action": "observe",
                        "value": 0.5
                    },
                    {
                        "action": "observe",
                        "value": 1
                    },
                    {
                        "action": "observe",
                        "value": 1.5
                    },
                    {
                        "action": "observe",
                        "value": 1.5
                    },
                    {
                        "action": "observe",
                        "value": 2
                    },
                    {
                        "action": "observe",
                        "value": 3
                    }
                ]
            },
            "expected_output": "sample_count=7\nsample_sum=9.5\nbucket_le=1 count=3\nbucket_le=2 count=6\nbucket_le=+Inf count=7\n"
        },
        {
            "input": {
                "feature": "histogram",
                "buckets": [
                    1,
                    2
                ],
                "operations": [
                    {
                        "action": "observe_multiple",
                        "bucket_increments": [
                            5,
                            9,
                            3
                        ],
                        "sum_of_observations": 20
                    },
                    {
                        "action": "observe_multiple",
                        "bucket_increments": [
                            0,
                            20,
                            6
                        ],
                        "sum_of_observations": 34
                    }
                ]
            },
            "expected_output": "sample_count=43\nsample_sum=54\nbucket_le=1 count=5\nbucket_le=2 count=34\nbucket_le=+Inf count=43\n"
        },
        {
            "input": {
                "feature": "histogram",
                "buckets": [
                    1,
                    2
                ],
                "operations": [
                    {
                        "action": "observe_multiple",
                        "bucket_increments": [
                            5,
                            9
                        ],
                        "sum_of_observations": 20
                    }
                ]
            },
            "expected_output": "[invalid bucket increment count configuration]\nexpected_buckets=3\n"
        },
        {
            "input": {
                "feature": "histogram",
                "buckets": [
                    1
                ],
                "operations": [
                    {
                        "action": "observe",
                        "value": -10
                    }
                ]
            },
            "expected_output": "sample_count=1\nsample_sum=-10\nbucket_le=1 count=1\nbucket_le=+Inf count=1\n"
        },
        {
            "input": {
                "feature": "histogram",
                "buckets": [
                    1,
                    2
                ],
                "operations": [
                    {
                        "action": "observe",
                        "value": 1.5
                    },
                    {
                        "action": "collect"
                    },
                    {
                        "action": "observe",
                        "value": 1.5
                    }
                ]
            },
            "expected_output": "sample_count=2\nsample_sum=3\nbucket_le=1 count=0\nbucket_le=2 count=2\nbucket_le=+Inf count=2\n"
        }
    ]
}
```

---

### Feature 4: Summary Quantile Reporting

**As a developer**, I want to collect observations and expose configured quantile estimates, so I can summarize streams with count, sum, and percentile-like values.

**Expected Behavior / Usage:**

A summary is configured with requested quantiles and tolerated error values. It reports total sample count, total sample sum, and one line per configured quantile. With no quantiles or observations it reports zero count and zero sum. Quantile estimates are the externally visible estimates produced by the metric engine for the supplied observations.

**Test Cases:** `rcb_tests/public_test_cases/feature4_summary_quantiles.json`

```json
{
    "description": "Summary samples expose total count, total sum, and configured quantile estimates after observations.",
    "cases": [
        {
            "input": {
                "feature": "summary",
                "quantiles": [],
                "observations": []
            },
            "expected_output": "sample_count=0\nsample_sum=0\n"
        },
        {
            "input": {
                "feature": "summary",
                "quantiles": [
                    {
                        "quantile": 0.5,
                        "error": 0.05
                    }
                ],
                "observations": [
                    0,
                    200
                ]
            },
            "expected_output": "sample_count=2\nsample_sum=200\nquantile=0.5 value=0\n"
        },
        {
            "input": {
                "feature": "summary",
                "quantiles": [
                    {
                        "quantile": 0.5,
                        "error": 0.05
                    }
                ],
                "observations": [
                    0,
                    1,
                    101
                ]
            },
            "expected_output": "sample_count=3\nsample_sum=102\nquantile=0.5 value=0\n"
        }
    ]
}
```

---

### Feature 5: Metric and Label Name Validation

**As a developer**, I want to validate externally supplied metric and label identifiers, so I can reject names that cannot be exposed safely.

**Expected Behavior / Usage:**

Name validation receives a kind and a raw name. Metric names and label names must be non-empty, must use the permitted identifier characters, and must not use reserved prefixes. The output states the requested kind, the raw name, and whether it is valid.

**Test Cases:** `rcb_tests/public_test_cases/feature5_name_validation.json`

```json
{
    "description": "Metric and label names are accepted only when they are non-empty, unreserved, and use the permitted identifier characters.",
    "cases": [
        {
            "input": {
                "feature": "name_validation",
                "kind": "metric",
                "name": ""
            },
            "expected_output": "kind=metric\nname=\nvalid=no\n"
        },
        {
            "input": {
                "feature": "name_validation",
                "kind": "metric",
                "name": "prometheus_notifications_total"
            },
            "expected_output": "kind=metric\nname=prometheus_notifications_total\nvalid=yes\n"
        },
        {
            "input": {
                "feature": "name_validation",
                "kind": "metric",
                "name": "__some_reserved_metric"
            },
            "expected_output": "kind=metric\nname=__some_reserved_metric\nvalid=no\n"
        },
        {
            "input": {
                "feature": "name_validation",
                "kind": "metric",
                "name": "fa mi ly with space in name or |"
            },
            "expected_output": "kind=metric\nname=fa mi ly with space in name or |\nvalid=no\n"
        },
        {
            "input": {
                "feature": "name_validation",
                "kind": "label",
                "name": "type"
            },
            "expected_output": "kind=label\nname=type\nvalid=yes\n"
        },
        {
            "input": {
                "feature": "name_validation",
                "kind": "label",
                "name": "log-level"
            },
            "expected_output": "kind=label\nname=log-level\nvalid=no\n"
        },
        {
            "input": {
                "feature": "name_validation",
                "kind": "label",
                "name": "-abcd"
            },
            "expected_output": "kind=label\nname=-abcd\nvalid=no\n"
        }
    ]
}
```

---

### Feature 6: Metric Family Membership

**As a developer**, I want to group samples under shared metadata and labels, so I can collect related metrics consistently.

**Expected Behavior / Usage:**

A metric family has a name, help text, constant labels, and zero or more metric members with per-member labels. Collection emits no families when no members exist. For collected members, constant labels and member labels are both exposed. Removing a member excludes it from later collection. Querying labels reports whether a matching member exists. Duplicate label keys across constant and member labels or invalid family definitions are reported as neutral domain errors.

**Test Cases:** `rcb_tests/public_test_cases/feature6_metric_family_membership.json`

```json
{
    "description": "A metric family combines constant and per-sample labels, reports collected members, supports removal, and rejects conflicting label keys.",
    "cases": [
        {
            "input": {
                "feature": "family",
                "action": "collect_counter_family",
                "name": "total_requests",
                "help": "Counts all requests",
                "constant_labels": {
                    "component": "test"
                },
                "metrics": [
                    {
                        "labels": {
                            "status": "200"
                        },
                        "operations": []
                    }
                ],
                "remove_indexes": []
            },
            "expected_output": "family_count=1\nname=total_requests\nhelp=Counts all requests\nmetric_count=1\nmetric=0\ncomponent=test\nstatus=200\ncounter_value=0\n"
        },
        {
            "input": {
                "feature": "family",
                "action": "collect_counter_family",
                "name": "total_requests",
                "help": "Counts all requests",
                "constant_labels": {},
                "metrics": [
                    {
                        "labels": {},
                        "operations": [
                            {
                                "action": "increment"
                            }
                        ]
                    }
                ],
                "remove_indexes": []
            },
            "expected_output": "family_count=1\nname=total_requests\nhelp=Counts all requests\nmetric_count=1\nmetric=0\ncounter_value=1\n"
        },
        {
            "input": {
                "feature": "family",
                "action": "collect_counter_family",
                "name": "total_requests",
                "help": "Counts all requests",
                "constant_labels": {},
                "metrics": [
                    {
                        "labels": {
                            "name": "counter1"
                        },
                        "operations": []
                    },
                    {
                        "labels": {
                            "name": "counter2"
                        },
                        "operations": []
                    }
                ],
                "remove_indexes": [
                    0
                ]
            },
            "expected_output": "family_count=1\nname=total_requests\nhelp=Counts all requests\nmetric_count=1\nmetric=0\nname=counter2\ncounter_value=0\n"
        },
        {
            "input": {
                "feature": "family",
                "action": "collect_counter_family",
                "name": "total_requests",
                "help": "Counts all requests",
                "constant_labels": {},
                "metrics": [],
                "remove_indexes": []
            },
            "expected_output": "family_count=0\n"
        },
        {
            "input": {
                "feature": "family",
                "action": "has_counter",
                "name": "total_rquests",
                "help": "Counts all requests",
                "constant_labels": {},
                "metrics": [
                    {
                        "labels": {
                            "name": "counter1"
                        }
                    }
                ],
                "query_labels": {
                    "name": "counter1"
                }
            },
            "expected_output": "exists=yes\n"
        },
        {
            "input": {
                "feature": "family",
                "action": "has_counter",
                "name": "total_rquests",
                "help": "Counts all requests",
                "constant_labels": {},
                "metrics": [
                    {
                        "labels": {
                            "name": "counter1"
                        }
                    }
                ],
                "query_labels": {
                    "name": "couner2"
                }
            },
            "expected_output": "exists=no\n"
        },
        {
            "input": {
                "feature": "family",
                "action": "duplicate_labels",
                "name": "total_requests",
                "help": "Counts all requests",
                "constant_labels": {
                    "component": "test"
                },
                "metric_labels": {
                    "component": "test"
                }
            },
            "expected_output": "error=duplicate_label_name\n"
        },
        {
            "input": {
                "feature": "family",
                "action": "collect_counter_family",
                "name": "",
                "help": "empty name",
                "constant_labels": {},
                "metrics": [],
                "remove_indexes": []
            },
            "expected_output": "error=invalid_metric_family_definition\n"
        }
    ]
}
```

---

### Feature 7: Registry Collection Rules

**As a developer**, I want to register metric families for collection, so I can expose a coherent set of metric families.

**Expected Behavior / Usage:**

A registry collects registered metric families and reports their metadata and member labels. In merge mode, repeated compatible registrations of the same family are merged into a single collected family. Removing a family permits a later compatible registration. Registering incompatible metric kinds under the same name is rejected with a neutral type-conflict error.

**Test Cases:** `rcb_tests/public_test_cases/feature7_registry_collection_rules.json`

```json
{
    "description": "A registry exposes registered metric families, removes them when requested, merges matching families in merge mode, and rejects name/type conflicts.",
    "cases": [
        {
            "input": {
                "feature": "registry",
                "action": "collect_two_counters",
                "name": "test",
                "help": "a test",
                "metrics": [
                    {
                        "labels": {
                            "name": "counter1"
                        }
                    },
                    {
                        "labels": {
                            "name": "counter2"
                        }
                    }
                ]
            },
            "expected_output": "family_count=1\nname=test\nhelp=a test\nmetric_count=2\nname=counter2\nname=counter1\n"
        },
        {
            "input": {
                "feature": "registry",
                "action": "merge_same_counter_family",
                "name": "counter",
                "help": "Test Counter",
                "metric_labels": {
                    "name": "test_counter"
                },
                "repetitions": 4
            },
            "expected_output": "family_count=1\n"
        },
        {
            "input": {
                "feature": "registry",
                "action": "reject_type_conflict",
                "name": "same_name"
            },
            "expected_output": "[metric family name type conflict]\nname=same_name\n"
        },
        {
            "input": {
                "feature": "registry",
                "action": "remove_and_readd",
                "name": "name"
            },
            "expected_output": "removed=yes\nreadd=accepted\n"
        }
    ]
}
```

---

### Feature 8: Text Exposition Formatting

**As a developer**, I want to serialize metric families into a line-oriented exposition format, so I can serve metrics to text-format clients.

**Expected Behavior / Usage:**

Serialization emits HELP and TYPE header lines followed by sample lines. It renders special floating-point values as Nan, -Inf, and +Inf. Label values escape backslashes, newlines, and double quotes. Counters may include timestamps. Histograms and summaries emit their compound count, sum, bucket, or quantile lines in the externally observed order.

**Test Cases:** `rcb_tests/public_test_cases/feature8_text_exposition_format.json`

```json
{
    "description": "Metric families serialize to the text exposition format with HELP/TYPE headers, escaped label values, special floating-point values, timestamps, and compound sample lines.",
    "cases": [
        {
            "input": {
                "feature": "serialize",
                "metric_type": "gauge",
                "name": "my_metric",
                "help": "my metric help text",
                "special_value": "nan",
                "labels": {}
            },
            "expected_output": "# HELP my_metric my metric help text\n# TYPE my_metric gauge\nmy_metric Nan\n"
        },
        {
            "input": {
                "feature": "serialize",
                "metric_type": "gauge",
                "name": "my_metric",
                "help": "my metric help text",
                "special_value": "-inf",
                "labels": {}
            },
            "expected_output": "# HELP my_metric my metric help text\n# TYPE my_metric gauge\nmy_metric -Inf\n"
        },
        {
            "input": {
                "feature": "serialize",
                "metric_type": "gauge",
                "name": "my_metric",
                "help": "my metric help text",
                "special_value": "+inf",
                "labels": {}
            },
            "expected_output": "# HELP my_metric my metric help text\n# TYPE my_metric gauge\nmy_metric +Inf\n"
        },
        {
            "input": {
                "feature": "serialize",
                "metric_type": "gauge",
                "name": "my_metric",
                "help": "my metric help text",
                "value": 0,
                "labels": {
                    "k": "v\\v"
                }
            },
            "expected_output": "# HELP my_metric my metric help text\n# TYPE my_metric gauge\nmy_metric{k=\"v\\\\v\"} 0\n"
        },
        {
            "input": {
                "feature": "serialize",
                "metric_type": "gauge",
                "name": "my_metric",
                "help": "my metric help text",
                "value": 0,
                "labels": {
                    "k": "v\nv"
                }
            },
            "expected_output": "# HELP my_metric my metric help text\n# TYPE my_metric gauge\nmy_metric{k=\"v\\nv\"} 0\n"
        },
        {
            "input": {
                "feature": "serialize",
                "metric_type": "gauge",
                "name": "my_metric",
                "help": "my metric help text",
                "value": 0,
                "labels": {
                    "k": "v\"v"
                }
            },
            "expected_output": "# HELP my_metric my metric help text\n# TYPE my_metric gauge\nmy_metric{k=\"v\\\"v\"} 0\n"
        },
        {
            "input": {
                "feature": "serialize",
                "metric_type": "untyped",
                "name": "my_metric",
                "help": "my metric help text",
                "value": 64,
                "labels": {}
            },
            "expected_output": "# HELP my_metric my metric help text\n# TYPE my_metric untyped\nmy_metric 64\n"
        },
        {
            "input": {
                "feature": "serialize",
                "metric_type": "counter",
                "name": "my_metric",
                "help": "my metric help text",
                "value": 64,
                "timestamp_ms": 1234,
                "labels": {}
            },
            "expected_output": "# HELP my_metric my metric help text\n# TYPE my_metric counter\nmy_metric 64 1234\n"
        },
        {
            "input": {
                "feature": "serialize",
                "metric_type": "histogram",
                "name": "my_metric",
                "help": "my metric help text",
                "buckets": [
                    1
                ],
                "observations": [
                    0,
                    200
                ],
                "labels": {}
            },
            "expected_output": "# HELP my_metric my metric help text\n# TYPE my_metric histogram\nmy_metric_count 2\nmy_metric_sum 200\nmy_metric_bucket{le=\"1\"} 1\nmy_metric_bucket{le=\"+Inf\"} 2\n"
        },
        {
            "input": {
                "feature": "serialize",
                "metric_type": "summary",
                "name": "my_metric",
                "help": "my metric help text",
                "quantiles": [
                    {
                        "quantile": 0.5,
                        "error": 0.05
                    }
                ],
                "observations": [
                    0,
                    200
                ],
                "labels": {}
            },
            "expected_output": "# HELP my_metric my metric help text\n# TYPE my_metric summary\nmy_metric_count 2\nmy_metric_sum 200\nmy_metric{quantile=\"0.5\"} 0\n"
        }
    ]
}
```

---

### Feature 9: Base64 Decoding

**As a developer**, I want to decode base64 text credentials or payload fragments, so I can interpret encoded transport values safely.

**Expected Behavior / Usage:**

Base64 decoding receives an encoded text value and outputs the decoded byte string. Empty input decodes to an empty string. Inputs with invalid alphabet symbols, invalid length, or invalid padding are reported with a neutral invalid-base64 error and the raw encoded input.

**Test Cases:** `rcb_tests/public_test_cases/feature9_base64_decoding.json`

```json
{
    "description": "Base64 encoded input decodes to its byte string, while malformed alphabet, size, or padding input yields a neutral invalid-input error.",
    "cases": [
        {
            "input": {
                "feature": "base64",
                "encoded": ""
            },
            "expected_output": "decoded=\n"
        },
        {
            "input": {
                "feature": "base64",
                "encoded": "Zg=="
            },
            "expected_output": "decoded=f\n"
        },
        {
            "input": {
                "feature": "base64",
                "encoded": "Zm8="
            },
            "expected_output": "decoded=fo\n"
        },
        {
            "input": {
                "feature": "base64",
                "encoded": "Zm9v"
            },
            "expected_output": "decoded=foo\n"
        },
        {
            "input": {
                "feature": "base64",
                "encoded": "Zm9vYg=="
            },
            "expected_output": "decoded=foob\n"
        },
        {
            "input": {
                "feature": "base64",
                "encoded": "Zm9vYmE="
            },
            "expected_output": "decoded=fooba\n"
        },
        {
            "input": {
                "feature": "base64",
                "encoded": "Zm9vYmFy"
            },
            "expected_output": "decoded=foobar\n"
        },
        {
            "input": {
                "feature": "base64",
                "encoded": "...."
            },
            "expected_output": "[padding or padding plus empty characters error]\nencoded=....\n"
        },
        {
            "input": {
                "feature": "base64",
                "encoded": "ABC"
            },
            "expected_output": "[padding or padding plus empty characters error]\nencoded=ABC\n"
        },
        {
            "input": {
                "feature": "base64",
                "encoded": "A==="
            },
            "expected_output": "[padding or padding plus empty characters error]\nencoded=A===\n"
        }
    ]
}
```

---

### Feature 10: HTTP Metrics Endpoint

**As a developer**, I want to serve registered metric registries over HTTP paths, so I can let clients scrape metrics through network requests.

**Expected Behavior / Usage:**

The HTTP endpoint binds to an available port, maps registries to configured URL paths, and returns request-observable status, content type, and body-membership signals. Unregistered paths return a not-found status. Registered paths return a success status and UTF-8 text content. Different paths isolate their registered metrics. Removing a registry or allowing a registry reference to expire excludes its metrics. Requests that advertise compression support and requests with valid basic credentials still receive the registered metrics.

**Test Cases:** `rcb_tests/public_test_cases/feature10_http_metrics_endpoint.json`

```json
{
    "description": "An HTTP endpoint exposes registered metric registries at configured paths with status, content-type, optional compression, authentication, removal, and expired-registry behavior observable through requests.",
    "cases": [
        {
            "input": {
                "feature": "http",
                "registries": [],
                "requests": [
                    {
                        "path": "/metrics",
                        "contains": []
                    }
                ]
            },
            "expected_output": "request_path=/metrics\nstatus=404\ncontent_type=text/plain; charset=utf-8\n"
        },
        {
            "input": {
                "feature": "http",
                "registries": [
                    {
                        "path": "/metrics",
                        "counter_name": "example_total"
                    }
                ],
                "requests": [
                    {
                        "path": "/metrics",
                        "contains": [
                            "example_total"
                        ]
                    }
                ]
            },
            "expected_output": "request_path=/metrics\nstatus=200\ncontent_type=text/plain; charset=utf-8\ncontains_example_total=yes\n"
        },
        {
            "input": {
                "feature": "http",
                "registries": [
                    {
                        "path": "/first",
                        "counter_name": "first_total"
                    },
                    {
                        "path": "/second",
                        "counter_name": "second_total"
                    }
                ],
                "requests": [
                    {
                        "path": "/first",
                        "contains": [
                            "first_total",
                            "second_total"
                        ]
                    },
                    {
                        "path": "/second",
                        "contains": [
                            "second_total",
                            "first_total"
                        ]
                    }
                ]
            },
            "expected_output": "request_path=/first\nstatus=200\ncontent_type=text/plain; charset=utf-8\ncontains_first_total=yes\ncontains_second_total=no\nrequest_path=/second\nstatus=200\ncontent_type=text/plain; charset=utf-8\ncontains_second_total=yes\ncontains_first_total=no\n"
        },
        {
            "input": {
                "feature": "http",
                "registries": [
                    {
                        "path": "/metrics",
                        "counter_name": "some_counter_total"
                    }
                ],
                "remove_registry_indexes": [
                    {
                        "index": 0,
                        "path": "/metrics"
                    }
                ],
                "requests": [
                    {
                        "path": "/metrics",
                        "contains": [
                            "some_counter_total"
                        ]
                    }
                ]
            },
            "expected_output": "request_path=/metrics\nstatus=200\ncontent_type=text/plain; charset=utf-8\ncontains_some_counter_total=no\n"
        },
        {
            "input": {
                "feature": "http",
                "registries": [
                    {
                        "path": "/metrics",
                        "counter_name": "example_total"
                    }
                ],
                "requests": [
                    {
                        "path": "/metrics",
                        "accept_compression": true,
                        "contains": [
                            "example_total"
                        ]
                    }
                ]
            },
            "expected_output": "request_path=/metrics\nstatus=200\ncontent_type=text/plain; charset=utf-8\ncontains_example_total=yes\n"
        },
        {
            "input": {
                "feature": "http",
                "registries": [
                    {
                        "path": "/metrics",
                        "counter_name": "example_total"
                    }
                ],
                "auth": [
                    {
                        "path": "/metrics",
                        "username": "test_user",
                        "password": "test_password",
                        "realm": "Some Auth Realm"
                    }
                ],
                "requests": [
                    {
                        "path": "/metrics",
                        "username": "test_user",
                        "password": "test_password",
                        "contains": [
                            "example_total"
                        ]
                    }
                ]
            },
            "expected_output": "request_path=/metrics\nstatus=200\ncontent_type=text/plain; charset=utf-8\ncontains_example_total=yes\n"
        },
        {
            "input": {
                "feature": "http",
                "registries": [
                    {
                        "path": "/metrics",
                        "counter_name": "first_total"
                    },
                    {
                        "path": "/metrics",
                        "counter_name": "second_total"
                    }
                ],
                "drop_registry_indexes": [
                    1
                ],
                "requests": [
                    {
                        "path": "/metrics",
                        "contains": [
                            "first_total",
                            "second_total"
                        ]
                    }
                ]
            },
            "expected_output": "request_path=/metrics\nstatus=200\ncontent_type=text/plain; charset=utf-8\ncontains_first_total=yes\ncontains_second_total=no\n"
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
- standard prometheus metric registration logic
- same metric family serialization format used in exporters.go
