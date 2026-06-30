## Product Requirement Document

# Web Application Cache Adapter - Keyed Data, Function, HTTP, and Template Fragment Caching

## Project Goal

Build a web application caching utility that allows developers to store reusable values, cache function results, cache HTTP route responses, and cache template fragments without writing repetitive storage, invalidation, and request-key normalization code by hand.

---

## Background & Problem

Without this library/tool, developers are forced to manually keep per-key state, decide when values expire, normalize function arguments, distinguish equivalent HTTP query strings, and manage template fragment entries. This leads to repetitive code, inconsistent invalidation, stale responses, and subtle bugs when the same logical input is expressed in different orders.

With this library/tool, developers use one consistent caching layer for direct key/value storage, decorated computations, HTTP response caching, and template fragments, while the adapter exposes observable input/output behavior for black-box validation.

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

### Feature 1: Keyed Value Storage

**As a developer**, I want to store values under string keys and read them later, so I can reuse computed data without recomputing it.

**Expected Behavior / Usage:**

The input describes entries to store and keys to read. Each stored value must be returned exactly for its key, including scalar and structured values. A read for a missing key must render `value=none`. The output contains one line per requested key in read order using `key=<key> value=<rendered-value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_key_value_storage.json`

```json
{
    "description": "Stores values under string keys and returns the exact stored values for later reads.",
    "cases": [
        {
            "input": {
                "scenario": "store and read keyed values",
                "entries": [
                    {
                        "key": "0",
                        "value": 0
                    },
                    {
                        "key": "1",
                        "value": 1
                    },
                    {
                        "key": "2",
                        "value": 4
                    }
                ],
                "read_keys": [
                    "0",
                    "1",
                    "2"
                ]
            },
            "expected_output": "key=0 value=0\nkey=1 value=1\nkey=2 value=4\n"
        }
    ]
}
```

---

### Feature 2: Bulk Reads

**As a developer**, I want to retrieve several keys in one operation, so I can keep the requested order and avoid repeated individual reads.

**Expected Behavior / Usage:**

The input provides stored entries and an ordered list of keys. The output must contain a single `values=` line whose value is the JSON-rendered list of retrieved values in the exact same order as the requested keys.

**Test Cases:** `rcb_tests/public_test_cases/feature2_bulk_read.json`

```json
{
    "description": "Reads multiple stored keys in request order and renders the resulting value list.",
    "cases": [
        {
            "input": {
                "scenario": "read multiple keyed values",
                "entries": [
                    {
                        "key": "foo",
                        "value": [
                            "bar"
                        ]
                    },
                    {
                        "key": "spam",
                        "value": "eggs"
                    }
                ],
                "read_keys": [
                    "foo",
                    "spam"
                ]
            },
            "expected_output": "values=[[\"bar\"],\"eggs\"]\n"
        }
    ]
}
```

---

### Feature 3: Add Without Overwrite

**As a developer**, I want an add operation that only stores absent keys, so accidental duplicate writes do not overwrite existing cached data.

**Expected Behavior / Usage:**

The input is a sequence of add attempts. For each attempt, output whether a new entry was created and what value is stored after the attempt. If the key already exists, creation must be `false` and the original value must remain stored.

**Test Cases:** `rcb_tests/public_test_cases/feature3_add_semantics.json`

```json
{
    "description": "Adds a key only when it is absent and preserves the first stored value on duplicate add attempts.",
    "cases": [
        {
            "input": {
                "scenario": "add without overwriting",
                "add_attempts": [
                    {
                        "key": "foo",
                        "value": "bar"
                    },
                    {
                        "key": "foo",
                        "value": "qux"
                    }
                ]
            },
            "expected_output": "add_key=foo created=true stored=bar\nadd_key=foo created=false stored=bar\n"
        }
    ]
}
```

---

### Feature 4: Delete Semantics

**As a developer**, I want to delete multiple cached keys and verify their absence, so stale data can be invalidated in a batch.

**Expected Behavior / Usage:**

The input includes entries, keys to delete, and keys to read after deletion. The output first reports whether the batch deletion completed, then reports `value=none` for each deleted key that is read afterward.

**Test Cases:** `rcb_tests/public_test_cases/feature4_delete_semantics.json`

```json
{
    "description": "Deletes one or more keys and subsequent reads report no value for deleted keys.",
    "cases": [
        {
            "input": {
                "scenario": "delete keyed values",
                "entries": [
                    {
                        "key": "foo",
                        "value": "bar"
                    },
                    {
                        "key": "spam",
                        "value": "eggs"
                    }
                ],
                "delete_keys": [
                    "foo",
                    "spam"
                ],
                "read_keys": [
                    "foo",
                    "spam"
                ]
            },
            "expected_output": "delete_many_result=true\nkey=foo value=none\nkey=spam value=none\n"
        }
    ]
}
```

---

### Feature 5: Numeric Mutation

**As a developer**, I want cached integer values to support increment and decrement operations, so counters can be updated through the cache API.

**Expected Behavior / Usage:**

The input provides a key and initial integer. The adapter increments the value once, decrements it once, and reads the stored result. The output must show the new value after each mutation and the final stored value.

**Test Cases:** `rcb_tests/public_test_cases/feature5_numeric_mutation.json`

```json
{
    "description": "Updates an integer value atomically by incrementing and decrementing it while preserving the stored result.",
    "cases": [
        {
            "input": {
                "scenario": "increment and decrement numeric value",
                "key": "foo",
                "initial": 1
            },
            "expected_output": "after_increment=2\nafter_decrement=1\nstored=1\n"
        }
    ]
}
```

---

### Feature 6: Presence Checks

**As a developer**, I want to check whether a key exists without reading its value, so I can make control-flow decisions cheaply.

**Expected Behavior / Usage:**

The input names keys to probe before storage, after storage, and after deletion. The output must report `present=true` only while a key is stored and not deleted, and `present=false` otherwise.

**Test Cases:** `rcb_tests/public_test_cases/feature6_presence_checks.json`

```json
{
    "description": "Reports whether keys are present before storage, after storage, and after deletion.",
    "cases": [
        {
            "input": {
                "scenario": "check key presence",
                "probe_before": [
                    "foo",
                    "spam"
                ],
                "entries": [
                    {
                        "key": "foo",
                        "value": "bar"
                    }
                ],
                "probe_after_store": [
                    "foo",
                    "spam"
                ],
                "delete_keys": [
                    "foo"
                ],
                "probe_after_delete": [
                    "foo",
                    "spam"
                ]
            },
            "expected_output": "before key=foo present=false\nbefore key=spam present=false\nafter_store key=foo present=true\nafter_store key=spam present=false\nafter_delete key=foo present=false\nafter_delete key=spam present=false\n"
        }
    ]
}
```

---

### Feature 7: Entry Expiration

**As a developer**, I want entries to expire after a configured lifetime while non-expiring entries remain available, so cached data freshness can be controlled.

**Expected Behavior / Usage:**

The input stores entries with per-entry lifetimes and waits before reading again. A lifetime of zero means the entry does not expire. A short positive lifetime must make the entry unavailable after the wait. The output includes values before and after the wait.

**Test Cases:** `rcb_tests/public_test_cases/feature7_expiration.json`

```json
{
    "description": "Keeps entries with no expiration while entries with a short lifetime disappear after their lifetime passes.",
    "cases": [
        {
            "input": {
                "scenario": "expire keyed values",
                "entries": [
                    {
                        "key": "foo",
                        "value": "bar",
                        "ttl_seconds": 0
                    },
                    {
                        "key": "baz",
                        "value": "qux",
                        "ttl_seconds": 1
                    }
                ],
                "wait_seconds": 2
            },
            "expected_output": "before_wait key=foo [a specific literal value for a key that is not expired]\nbefore_wait key=baz value=qux\nafter_wait key=foo [a specific literal value for a key that is not expired]\nafter_wait key=baz value=none\n"
        }
    ]
}
```

---

### Feature 8: Configuration Initialization

**As a developer**, I want initialization-time settings to choose the active backend and attach the cache to an application, so application setup can override earlier defaults.

**Expected Behavior / Usage:**

The input describes a constructor-time backend kind and an optional initialization-time backend kind. If an initialization kind is provided, it determines the active backend. The output reports both input kinds, the active backend category, and whether the cache is attached to the application.

**Test Cases:** `rcb_tests/public_test_cases/feature8_configuration_initialization.json`

```json
{
    "description": "Initializes the cache from construction-time and initialization-time configuration, with initialization settings taking precedence.",
    "cases": [
        {
            "input": {
                "scenario": "initialize cache configuration",
                "constructor_kind": "disabled",
                "init_kind": "memory"
            },
            "expected_output": "constructor_kind=disabled\ninit_kind=memory\nactive_backend=memory\napp_attached=true\n"
        }
    ]
}
```

---

### Feature 9: Decorated Function Result Caching

**As a developer**, I want a decorated producer function to reuse its first result for the same cache slot, so repeated calls avoid recomputation.

**Expected Behavior / Usage:**

The input describes a cache slot, a lifetime, and repeated calls. The output must show the same call value for repeated calls within the lifetime and a producer call count of one, proving the second value came from the cache rather than executing the producer again.

**Test Cases:** `rcb_tests/public_test_cases/feature9_decorated_function_cache.json`

```json
{
    "description": "Caches a decorated producer function result so repeated calls within the same slot reuse the first computed value.",
    "cases": [
        {
            "input": {
                "scenario": "cache decorated function result",
                "ttl_seconds": 60,
                "cache_slot": "MyBits",
                "calls": [
                    1,
                    2
                ]
            },
            "expected_output": "[the specific computed value returned by a cached computation for this input]\n[the specific computed value returned by a cached computation for this input]\n[the specific computed value returned by a cached computation for this input]\n"
        }
    ]
}
```

---

### Feature 10: Memoized Argument Matching

**As a developer**, I want memoization to normalize positional and named arguments, so equivalent calls share a cached result while different arguments compute independently.

**Expected Behavior / Usage:**

The input is an ordered list of calls, each with a label, positional arguments, and named arguments. Calls that are semantically equivalent must produce the same cached value and not increase the producer call count. Calls with different argument values must produce a new value. A call missing required data must render the neutral error category `missing_required_argument` instead of a host-language exception name.

**Test Cases:** `rcb_tests/public_test_cases/feature10_memoized_argument_matching.json`

```json
{
    "description": "Memoizes function results by normalized arguments so equivalent positional and named forms share a cached value, while different arguments compute separately.",
    "cases": [
        {
            "input": {
                "scenario": "memoize by normalized arguments",
                "calls": [
                    {
                        "label": "positional",
                        "args": [
                            1,
                            2
                        ],
                        "kwargs": {}
                    },
                    {
                        "label": "explicit_default",
                        "args": [
                            1,
                            2,
                            1
                        ],
                        "kwargs": {}
                    },
                    {
                        "label": "named_default",
                        "args": [
                            1
                        ],
                        "kwargs": {
                            "b": 2,
                            "c": 1
                        }
                    },
                    {
                        "label": "different",
                        "args": [
                            1,
                            2,
                            3
                        ],
                        "kwargs": {}
                    },
                    {
                        "label": "unordered_keywords",
                        "args": [
                            1,
                            2
                        ],
                        "kwargs": {
                            "e": 8,
                            "d": 5
                        }
                    },
                    {
                        "label": "same_keywords_other_order",
                        "args": [
                            1
                        ],
                        "kwargs": {
                            "b": 2,
                            "d": 5,
                            "e": 8,
                            "c": 1
                        }
                    },
                    {
                        "label": "missing",
                        "args": [
                            1
                        ],
                        "kwargs": {}
                    }
                ]
            },
            "expected_output": "call=positional value=calc-4-1\ncall=explicit_default value=calc-4-1\ncall=named_default value=calc-4-1\ncall=different value=calc-6-2\ncall=unordered_keywords value=calc-17-3\ncall=same_keywords_other_order value=calc-17-3\ncall=missing error=missing_required_argument\nproducer_calls=3\n"
        }
    ]
}
```

---

### Feature 11: Memoized Result Deletion

**As a developer**, I want to invalidate memoized results by argument set or for all argument sets, so changed source data can force recomputation only where needed.

**Expected Behavior / Usage:**

The input chooses a deletion scope. Before deletion, repeated calls for the same arguments must return the original cached value. After deleting one argument set, only that argument set recomputes while other argument sets remain cached. After deleting all entries, every previously cached argument set recomputes. The output includes original values, post-delete values, and producer call count.

**Test Cases:** `rcb_tests/public_test_cases/feature11_memoized_deletion.json`

```json
{
    "description": "Deletes memoized results either for one argument set or for all argument sets, causing affected calls to recompute.",
    "cases": [
        {
            "input": {
                "scenario": "delete memoized results",
                "delete_scope": "one_argument_set"
            },
            "expected_output": "initial_target=total-7-1\ninitial_other=total-8-2\ntarget_before_delete=total-7-1\ntarget_after_delete=total-7-3\nother_after_delete=total-8-2\nproducer_calls=3\n"
        }
    ]
}
```

---

### Feature 12: HTTP Route Response Caching

**As a developer**, I want HTTP route responses to be cached, bypassed, or refreshed according to policy, so web responses can reuse generated bodies while still supporting dynamic invalidation.

**Expected Behavior / Usage:**

The input defines an HTTP route, a cache policy, and a sequence of requests. The output must include framework-observable signals: request label, status code, requested URL, response body, and final handler call count. Normal caching reuses the first body for the second request. A bypass policy must execute the handler for every request. A forced-refresh policy must replace the cached body when the force flag is true and reuse the refreshed body afterward.

**Test Cases:** `rcb_tests/public_test_cases/feature12_http_route_caching.json`

```json
{
    "description": "Caches HTTP route responses with framework-observable status, URL, body reuse, bypass, and forced-refresh behavior.",
    "cases": [
        {
            "input": {
                "scenario": "cache http route responses",
                "route": "/resource",
                "cache_policy": "normal",
                "requests": [
                    {
                        "label": "first",
                        "url": "/resource"
                    },
                    {
                        "label": "second",
                        "url": "/resource"
                    }
                ]
            },
            "expected_output": "request=first status=200 url=/resource body=body-1\nrequest=second status=200 url=/resource body=body-1\nhandler_calls=1\n"
        }
    ]
}
```

---

### Feature 13: HTTP Query String Cache Keys

**As a developer**, I want HTTP response caching to normalize query parameters, so equivalent query strings in different orders share a cached response and different values do not collide.

**Expected Behavior / Usage:**

The input is a sequence of HTTP GET URLs. The output must include status code, URL, response body, and handler call count. Requests with the same query parameter keys and values in different order must reuse the cached body. Requests with changed parameter values must produce a new body. Repeated query parameters with the same value set in different order must also share a body.

**Test Cases:** `rcb_tests/public_test_cases/feature13_http_query_caching.json`

```json
{
    "description": "Caches HTTP responses by normalized query parameters so reordered equivalent queries share a response and changed values use a separate response.",
    "cases": [
        {
            "input": {
                "scenario": "cache http query responses",
                "requests": [
                    {
                        "label": "first",
                        "url": "/works?mock=true&offset=20&limit=15"
                    },
                    {
                        "label": "same_reordered",
                        "url": "/works?limit=15&mock=true&offset=20"
                    },
                    {
                        "label": "different",
                        "url": "/works?limit=20&mock=true&offset=60"
                    }
                ]
            },
            "expected_output": "request=first status=200 url=/works?mock=true&offset=20&limit=15 body=count-1\nrequest=same_reordered status=200 url=/works?limit=15&mock=true&offset=20 body=count-1\nrequest=different status=200 url=/works?limit=20&mock=true&offset=60 body=count-2\nhandler_calls=2\n"
        }
    ]
}
```

---

### Feature 14: Template Fragment Caching

**As a developer**, I want rendered template fragments to be stored under deterministic fragment keys, so repeated template rendering can reuse stable fragment content.

**Expected Behavior / Usage:**

The input provides a fragment identifier and body text. Rendering the fragment must return the body and store the same body under a deterministic fragment key. The output reports the rendered body, the fragment key, and the stored value.

**Test Cases:** `rcb_tests/public_test_cases/feature14_template_fragment_caching.json`

```json
{
    "description": "Caches rendered template fragments under deterministic fragment keys and returns the rendered body.",
    "cases": [
        {
            "input": {
                "scenario": "cache template fragment",
                "fragment": "fragment3",
                "body": "visible-fragment"
            },
            "expected_output": "rendered=visible-fragment\nfragment_key=_template_fragment_cache_fragment3\nstored=visible-fragment\n"
        }
    ]
}
```

---

### Feature 15: Template Fragment Deletion

**As a developer**, I want templates to request deletion of a named fragment, so stale fragment content can be invalidated from template rendering flow.

**Expected Behavior / Usage:**

The input provides a fragment identifier and body text. The fragment is first cached, then a template deletion request is rendered for the same identifier. The output must show the value before deletion, the deterministic fragment key, and `after_delete=none` after deletion.

**Test Cases:** `rcb_tests/public_test_cases/feature15_template_fragment_deletion.json`

```json
{
    "description": "Deletes a named template fragment when the template requests deletion, leaving no cached value for that fragment key.",
    "cases": [
        {
            "input": {
                "scenario": "delete template fragment",
                "fragment": "fragment2",
                "body": "delete-me"
            },
            "expected_output": "before_delete=delete-me\nfragment_key=_template_fragment_cache_fragment2\nafter_delete=none\n"
        }
    ]
}
```

---

### Feature 16: Invalid Backend Configuration Errors

**As a developer**, I want invalid backend arguments to produce a normalized error contract, so callers can handle setup errors without depending on host-language exception names.

**Expected Behavior / Usage:**

The input requests a backend configuration that lacks a required host value. The adapter must catch the native setup failure and render only language-neutral fields: `error=argument_null` and `param=host`. The output must not include host-language exception class names, stack traces, or runtime-generated message suffixes.

**Test Cases:** `rcb_tests/public_test_cases/feature16_invalid_backend_configuration.json`

```json
{
    "description": "Rejects a network cache backend configuration with a missing host and renders a language-neutral argument error.",
    "cases": [
        {
            "input": {
                "scenario": "reject invalid backend argument",
                "backend_kind": "network_cache_host"
            },
            "expected_output": "error=argument_null\nparam=host\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. The complete hidden evaluation subset lives under `rcb_tests/test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_key_value_storage.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_key_value_storage@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- treat ordered and unordered keyword arguments as semantically identical
- demonstrate that specific memoized argument sets behave independently during deletion
