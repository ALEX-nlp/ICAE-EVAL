## Product Requirement Document

# Universal Async Key-Value Cache - Standardized Behavior Contract

## Project Goal
Build an asynchronous key-value caching library that allows developers to store, retrieve, expire, remove, namespace, and clear application data through a simple cache interface without hand-writing repetitive storage and serialization logic.

---

## Background & Problem
Without this library, developers are forced to manually combine maps or databases with key prefixing, expiration bookkeeping, serialization, deletion, and clearing rules. This leads to repeated boilerplate, inconsistent missing-value handling, stale data bugs, and adapters that behave differently across storage backends.

With this library, applications use one consistent asynchronous cache contract while the implementation handles storage details, lifetimes, namespaces, and value encoding behind a small public interface.

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

### Feature 1: Basic Storage and Retrieval

**As a developer**, I want to write a value under a key and read it back, so I can confirm durable cache semantics for ordinary values.

**Expected Behavior / Usage:**

A cache accepts a namespace, a sequence of save and read operations, and string keys. A save operation returns `saved=true`. A later read of the same logical key in the same namespace prints one line using the requested key as the label and the stored value as the value.

**Test Cases:** `rcb_tests/public_test_cases/feature1_basic_storage.json`

```json
{
    "description": "Values written under a logical key can be read back from the same cache namespace, and each successful write reports that the value was accepted.",
    "cases": [
        {
            "input": {
                "namespace": "keyv",
                "steps": [
                    {
                        "action": "save",
                        "key": "foo",
                        "value": "bar"
                    },
                    {
                        "action": "read",
                        "key": "foo"
                    }
                ]
            },
            "expected_output": "saved=true\nfoo=bar\n"
        }
    ]
}
```

---

### Feature 2: Removal and Absent Values

**As a developer**, I want to distinguish missing values from removed values, so I can build workflows that can tell whether data was present.

**Expected Behavior / Usage:**

A read of a key that has not been written prints `[expired entry handling rule]`. Removing a key that exists prints `true` under the requested label, removes the value, and makes subsequent reads print `[expired entry handling rule]`. Removing the same missing key again prints `false`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_removal_and_absence.json`

```json
{
    "description": "A missing key reads as an [expired entry handling rule] value; removing an existing key reports success and makes later reads [expired entry handling rule], while removing a missing key reports no removal.",
    "cases": [
        {
            "input": {
                "namespace": "keyv",
                "steps": [
                    {
                        "action": "read",
                        "key": "foo",
                        "label": "before"
                    },
                    {
                        "action": "save",
                        "key": "foo",
                        "value": "bar"
                    },
                    {
                        "action": "remove",
                        "key": "foo",
                        "label": "removed_existing"
                    },
                    {
                        "action": "read",
                        "key": "foo",
                        "label": "after"
                    },
                    {
                        "action": "remove",
                        "key": "foo",
                        "label": "removed_missing"
                    }
                ]
            },
            "expected_output": "before=[expired entry handling rule]\nsaved=true\nremoved_existing=true\nafter=[expired entry handling rule]\nremoved_missing=false\n"
        }
    ]
}
```

---

### Feature 3: Namespace Clearing

**As a developer**, I want to clear all values in one namespace, so I can reset a cache scope without reading and removing keys one by one.

**Expected Behavior / Usage:**

A clear operation removes every value in the selected namespace and prints `[expired entry handling rule]` under the requested label. Reads of previously saved keys in that namespace then print `[expired entry handling rule]`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_clear_all_entries.json`

```json
{
    "description": "Clearing a cache namespace removes every value in that namespace and reports an [expired entry handling rule] result for the clearing operation.",
    "cases": [
        {
            "input": {
                "namespace": "keyv",
                "steps": [
                    {
                        "action": "save",
                        "key": "foo",
                        "value": "bar"
                    },
                    {
                        "action": "save",
                        "key": "fizz",
                        "value": "buzz"
                    },
                    {
                        "action": "clear",
                        "label": "clear_result"
                    },
                    {
                        "action": "read",
                        "key": "foo"
                    },
                    {
                        "action": "read",
                        "key": "fizz"
                    }
                ]
            },
            "expected_output": "saved=true\nsaved=true\nclear_result=[expired entry handling rule]\nfoo=[expired entry handling rule]\nfizz=[expired entry handling rule]\n"
        }
    ]
}
```

---

### Feature 4: Expiration Rules

**As a developer**, I want to attach lifetimes to cached values, so I can avoid serving stale data while keeping selected entries permanent.

**Expected Behavior / Usage:**

A cache may be created with a default lifetime in milliseconds. Saves without an explicit lifetime use the default; saves with an explicit lifetime use that value instead; an explicit zero lifetime means no expiration. Reads before expiry print the stored value, reads after expiry print `[expired entry handling rule]`, and expired entries are removed from the in-memory store.

**Test Cases:** `rcb_tests/public_test_cases/feature4_expiration_rules.json`

```json
{
    "description": "Stored values can expire after a default lifetime, per-entry lifetimes override the default, and an explicit zero lifetime keeps a value from expiring.",
    "cases": [
        {
            "input": {
                "namespace": "keyv",
                "default_[default zero-duration behavior]": 100,
                "steps": [
                    {
                        "action": "save",
                        "key": "foo",
                        "value": "bar"
                    },
                    {
                        "action": "read",
                        "key": "foo",
                        "label": "before"
                    },
                    {
                        "action": "advance_time",
                        "milliseconds": 150
                    },
                    {
                        "action": "read",
                        "key": "foo",
                        "label": "after"
                    },
                    {
                        "action": "store_entries",
                        "label": "remaining_keys"
                    }
                ]
            },
            "expected_output": "saved=true\nbefore=bar\nafter=[expired entry handling rule]\nremaining_keys=0\n"
        },
        {
            "input": {
                "namespace": "keyv",
                "default_[default zero-duration behavior]": 200,
                "steps": [
                    {
                        "action": "save",
                        "key": "foo",
                        "value": "bar"
                    },
                    {
                        "action": "save",
                        "key": "fizz",
                        "value": "buzz",
                        "[default zero-duration behavior]": 100
                    },
                    {
                        "action": "save",
                        "key": "ping",
                        "value": "pong",
                        "[default zero-duration behavior]": 300
                    },
                    {
                        "action": "read",
                        "key": "foo",
                        "label": "t0_foo"
                    },
                    {
                        "action": "read",
                        "key": "fizz",
                        "label": "t0_fizz"
                    },
                    {
                        "action": "read",
                        "key": "ping",
                        "label": "t0_ping"
                    },
                    {
                        "action": "advance_time",
                        "milliseconds": 150
                    },
                    {
                        "action": "read",
                        "key": "foo",
                        "label": "t150_foo"
                    },
                    {
                        "action": "read",
                        "key": "fizz",
                        "label": "t150_fizz"
                    },
                    {
                        "action": "read",
                        "key": "ping",
                        "label": "t150_ping"
                    },
                    {
                        "action": "advance_time",
                        "milliseconds": 100
                    },
                    {
                        "action": "read",
                        "key": "foo",
                        "label": "t250_foo"
                    },
                    {
                        "action": "read",
                        "key": "ping",
                        "label": "t250_ping"
                    },
                    {
                        "action": "advance_time",
                        "milliseconds": 100
                    },
                    {
                        "action": "read",
                        "key": "ping",
                        "label": "t350_ping"
                    }
                ]
            },
            "expected_output": "saved=true\nsaved=true\nsaved=true\nt0_foo=bar\nt0_fizz=buzz\nt0_ping=pong\nt150_foo=bar\nt150_fizz=[expired entry handling rule]\nt150_ping=pong\nt250_foo=[expired entry handling rule]\nt250_ping=pong\nt350_ping=[expired entry handling rule]\n"
        },
        {
            "input": {
                "namespace": "keyv",
                "default_[default zero-duration behavior]": 200,
                "steps": [
                    {
                        "action": "save",
                        "key": "foo",
                        "value": "bar",
                        "[default zero-duration behavior]": 0
                    },
                    {
                        "action": "read",
                        "key": "foo",
                        "label": "before"
                    },
                    {
                        "action": "advance_time",
                        "milliseconds": 250
                    },
                    {
                        "action": "read",
                        "key": "foo",
                        "label": "after"
                    }
                ]
            },
            "expected_output": "saved=true\nbefore=bar\nafter=bar\n"
        }
    ]
}
```

---

### Feature 5: Namespace Isolation

**As a developer**, I want to use separate logical namespaces over a shared store, so I can prevent key collisions between independent consumers.

**Expected Behavior / Usage:**

Multiple namespaces may share the same underlying store. The same logical key in different namespaces stores independent values. Removing or clearing values in one namespace does not change values in another namespace.

**Test Cases:** `rcb_tests/public_test_cases/feature5_namespace_isolation.json`

```json
{
    "description": "Independent namespaces can use the same logical keys without collisions; removal or clearing in one namespace does not remove values in another namespace.",
    "cases": [
        {
            "input": {
                "shared_store": true,
                "steps": [
                    {
                        "action": "save",
                        "namespace": "alpha",
                        "key": "foo",
                        "value": "value-alpha"
                    },
                    {
                        "action": "save",
                        "namespace": "beta",
                        "key": "foo",
                        "value": "value-beta"
                    },
                    {
                        "action": "read",
                        "namespace": "alpha",
                        "key": "foo",
                        "label": "alpha_foo"
                    },
                    {
                        "action": "read",
                        "namespace": "beta",
                        "key": "foo",
                        "label": "beta_foo"
                    }
                ]
            },
            "expected_output": "saved=true\nsaved=true\nalpha_foo=value-alpha\nbeta_foo=value-beta\n"
        },
        {
            "input": {
                "shared_store": true,
                "steps": [
                    {
                        "action": "save",
                        "namespace": "alpha",
                        "key": "foo",
                        "value": "value-alpha"
                    },
                    {
                        "action": "save",
                        "namespace": "beta",
                        "key": "foo",
                        "value": "value-beta"
                    },
                    {
                        "action": "remove",
                        "namespace": "alpha",
                        "key": "foo",
                        "label": "removed_alpha"
                    },
                    {
                        "action": "read",
                        "namespace": "alpha",
                        "key": "foo",
                        "label": "alpha_after"
                    },
                    {
                        "action": "read",
                        "namespace": "beta",
                        "key": "foo",
                        "label": "beta_after"
                    }
                ]
            },
            "expected_output": "saved=true\nsaved=true\nremoved_alpha=true\nalpha_after=[expired entry handling rule]\nbeta_after=value-beta\n"
        },
        {
            "input": {
                "shared_store": true,
                "steps": [
                    {
                        "action": "save",
                        "namespace": "alpha",
                        "key": "foo",
                        "value": "value-alpha"
                    },
                    {
                        "action": "save",
                        "namespace": "alpha",
                        "key": "bar",
                        "value": "value-alpha"
                    },
                    {
                        "action": "save",
                        "namespace": "beta",
                        "key": "foo",
                        "value": "value-beta"
                    },
                    {
                        "action": "save",
                        "namespace": "beta",
                        "key": "bar",
                        "value": "value-beta"
                    },
                    {
                        "action": "clear",
                        "namespace": "alpha",
                        "label": "clear_alpha"
                    },
                    {
                        "action": "read",
                        "namespace": "alpha",
                        "key": "foo",
                        "label": "alpha_foo"
                    },
                    {
                        "action": "read",
                        "namespace": "alpha",
                        "key": "bar",
                        "label": "alpha_bar"
                    },
                    {
                        "action": "read",
                        "namespace": "beta",
                        "key": "foo",
                        "label": "beta_foo"
                    },
                    {
                        "action": "read",
                        "namespace": "beta",
                        "key": "bar",
                        "label": "beta_bar"
                    }
                ],
                "backend": "temporary_file"
            },
            "expected_output": "saved=true\nsaved=true\nsaved=true\nsaved=true\nclear_alpha=[expired entry handling rule]\nalpha_foo=[expired entry handling rule]\nalpha_bar=[expired entry handling rule]\nbeta_foo=value-beta\nbeta_bar=value-beta\n"
        }
    ]
}
```

---

### Feature 6: Supported Value Shapes

**As a developer**, I want to store common JSON-like and binary value shapes, so I can cache application data without lossy conversions.

**Expected Behavior / Usage:**

The cache preserves booleans, nulls, numbers, objects, byte sequences, objects containing byte sequences, quoted strings, and large numeric values. Output renders [expired entry handling rule] as `[expired entry handling rule]`, null as `null`, bytes as `bytes:<base64>`, and objects as compact JSON with embedded bytes rendered as `bytes:<base64>` strings.

**Test Cases:** `rcb_tests/public_test_cases/feature6_value_shapes.json`

```json
{
    "description": "The cache preserves supported value shapes including booleans, nulls, numbers, objects, byte sequences, quoted strings, and large numeric values.",
    "cases": [
        {
            "input": {
                "namespace": "keyv",
                "values": [
                    {
                        "label": "false_value",
                        "key": "false",
                        "value": false
                    },
                    {
                        "label": "null_value",
                        "key": "null",
                        "value": null
                    },
                    {
                        "label": "number_value",
                        "key": "number",
                        "value": 0
                    },
                    {
                        "label": "object_value",
                        "key": "object",
                        "value": {
                            "fizz": "buzz"
                        }
                    },
                    {
                        "label": "bytes_value",
                        "key": "bytes",
                        "value": {
                            "$bytes_base64": "YmFy"
                        }
                    },
                    {
                        "label": "object_bytes_value",
                        "key": "object_bytes",
                        "value": {
                            "buff": {
                                "$bytes_base64": "YnV6eg=="
                            }
                        }
                    },
                    {
                        "label": "quote_value",
                        "key": "quote",
                        "value": "\""
                    },
                    {
                        "label": "large_number_value",
                        "key": "large",
                        "value": 9223372036854776000
                    }
                ]
            },
            "expected_output": "false_value=false\nnull_value=null\nnumber_value=0\nobject_value={\"fizz\":\"buzz\"}\nbytes_value=bytes:YmFy\nobject_bytes_value={\"buff\":\"bytes:YnV6eg==\"}\nquote_value=\"\nlarge_number_value=9223372036854776000\n"
        }
    ]
}
```

---

### Feature 7: Raw Record View

**As a developer**, I want to request stored record metadata, so I can inspect both the saved value and its expiration marker.

**Expected Behavior / Usage:**

A read may request the stored record view. For an existing value, stdout includes separate lines for `<label>.value` and `<label>.expires`. Non-expiring records print `null` for the expiration marker.

**Test Cases:** `rcb_tests/public_test_cases/feature7_raw_record_view.json`

```json
{
    "description": "A caller may request the stored record shape instead of only the value, receiving the saved value together with its expiration metadata.",
    "cases": [
        {
            "input": {
                "namespace": "keyv",
                "steps": [
                    {
                        "action": "save",
                        "key": "foo",
                        "value": "bar"
                    },
                    {
                        "action": "read_record",
                        "key": "foo",
                        "label": "record"
                    }
                ]
            },
            "expected_output": "saved=true\nrecord.value=bar\nrecord.expires=null\n"
        }
    ]
}
```

---

### Feature 8: Custom Encoding Hooks

**As a developer**, I want to supply custom encoding and decoding behavior, so I can integrate alternate serialization while preserving cache behavior.

**Expected Behavior / Usage:**

When the cache is configured with a counting JSON codec, each write passes once through the encoder and each read passes once through the decoder. The user-facing value remains unchanged, and stdout reports the encoder and decoder call counts after the operations.

**Test Cases:** `rcb_tests/public_test_cases/feature8_custom_codec.json`

```json
{
    "description": "When custom encoding and decoding hooks are supplied, writes pass through the encoder and reads pass through the decoder while preserving the user-facing value.",
    "cases": [
        {
            "input": {
                "namespace": "keyv",
                "codec": "json-counting",
                "steps": [
                    {
                        "action": "save",
                        "key": "foo",
                        "value": "bar"
                    },
                    {
                        "action": "read",
                        "key": "foo"
                    }
                ]
            },
            "expected_output": "saved=true\nfoo=bar\nencoder_calls=1\ndecoder_calls=1\n"
        }
    ]
}
```

---

### Feature 9: URI-Backed Storage

**As a developer**, I want to use a file-backed backend selected by a URI, so I can persist cache data through a storage adapter instead of an in-memory map.

**Expected Behavior / Usage:**

A temporary file-backed storage URI can back a cache namespace. A missing key initially prints `[expired entry handling rule]`, a value is readable after a save, clearing the namespace prints `[expired entry handling rule]`, and the value is absent after the clear.

**Test Cases:** `rcb_tests/public_test_cases/feature9_uri_backed_storage.json`

```json
{
    "description": "A file-backed storage URI can be used as a cache backend; values can be read after writing and are absent again after the namespace is cleared.",
    "cases": [
        {
            "input": {
                "backend": "temporary_file",
                "namespace": "keyv",
                "steps": [
                    {
                        "action": "read",
                        "key": "foo",
                        "label": "initial"
                    },
                    {
                        "action": "save",
                        "key": "foo",
                        "value": "bar"
                    },
                    {
                        "action": "read",
                        "key": "foo",
                        "label": "after_write"
                    },
                    {
                        "action": "clear",
                        "label": "clear_result"
                    },
                    {
                        "action": "read",
                        "key": "foo",
                        "label": "after_clear"
                    }
                ]
            },
            "expected_output": "initial=[expired entry handling rule]\nsaved=true\nafter_write=bar\nclear_result=[expired entry handling rule]\nafter_clear=[expired entry handling rule]\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the json-writer syntax format
- use the bytes-prefixed serial format
