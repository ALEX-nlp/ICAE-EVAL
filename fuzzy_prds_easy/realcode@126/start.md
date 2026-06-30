## Product Requirement Document

# Retry Control Utility - Policy-Based Operation Retry and Status Reporting

## Project Goal

Build a retry-control library that allows developers to execute operations with configurable retry policies, backoff timing, exception filtering, return-value retry triggers, lifecycle listeners, and asynchronous execution without duplicating fragile retry loops throughout application code.

---

## Background & Problem

Without this library, developers are forced to manually wrap every unreliable operation in loops, counters, delay calculations, exception checks, and status tracking. This leads to repetitive code, inconsistent failure behavior, missed edge cases, and retry logic that is difficult to test and maintain.

With this library, retry behavior is expressed as a policy and the execution engine consistently applies that policy while returning observable status and lifecycle signals.

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

### Feature 1: Backoff Delay Calculation

**As a developer**, I want to select a wait-time strategy for retries, so I can avoid hand-writing timing formulas.

**Expected Behavior / Usage:**

The input names a backoff rule, a count of failed tries, and a base delay in milliseconds. The output reports either the exact computed wait in milliseconds or, for intentionally random rules, a deterministic property of the produced wait. Fixed waits return the base delay, no-wait returns zero, exponential waits double by failed-try position, and Fibonacci waits scale by the Fibonacci number at the failed-try position.

**Test Cases:** `rcb_tests/public_test_cases/feature1_backoff_delay.json`

```json
{
    "description": "Compute the wait duration for a retry attempt using the selected backoff rule and base delay.",
    "cases": [
        {
            "input": {
                "backoff": "fixed",
                "failed_tries": 5,
                "base_delay_ms": 100
            },
            "expected_output": "wait_ms=100\n"
        },
        {
            "input": {
                "backoff": "exponential",
                "failed_tries": 5,
                "base_delay_ms": 100
            },
            "expected_output": "[a specific calculated wait time based on exponential backoff factors]\n"
        },
        {
            "input": {
                "backoff": "fibonacci",
                "failed_tries": 4,
                "base_delay_ms": 5000
            },
            "expected_output": "[a specific derived value from the first Fibonacci number multiplied by base_delay_ms]\n"
        }
    ]
}
```

---

### Feature 2: Retry Policy Value Storage

**As a developer**, I want to construct retry policies from independent options, so I can pass consistent retry behavior to execution code.

**Expected Behavior / Usage:**

The input disables validation and supplies a list of settings to store. The output reports the value retained by the policy for the setting under inspection: exception retry mode, specific retryable categories, maximum tries, delay in milliseconds, or chosen backoff family. Validation is disabled so isolated policy fields can be inspected without requiring a complete executable policy.

**Test Cases:** `rcb_tests/public_test_cases/feature2_configuration_values.json`

```json
{
    "description": "Build a retry policy with validation disabled and report the stored policy values.",
    "cases": [
        {
            "input": {
                "validation_enabled": false,
                "settings": [
                    {
                        "retry_on": "any_exception"
                    }
                ]
            },
            "expected_output": "retry_on_any_exception=true\n"
        },
        {
            "input": {
                "validation_enabled": false,
                "settings": [
                    {
                        "max_tries": 99
                    }
                ]
            },
            "expected_output": "max_tries=99\n"
        },
        {
            "input": {
                "validation_enabled": false,
                "settings": [
                    {
                        "delay": {
                            "amount": 5,
                            "unit": "seconds"
                        }
                    }
                ]
            },
            "expected_output": "delay_ms=5000\n"
        },
        {
            "input": {
                "validation_enabled": false,
                "settings": [
                    {
                        "backoff": "fixed"
                    }
                ]
            },
            "expected_output": "backoff=fixed\n"
        }
    ]
}
```

---

### Feature 3: Retry Policy Validation

**As a developer**, I want to receive clear configuration errors, so I can detect invalid retry setup before execution.

**Expected Behavior / Usage:**

The input enables validation and supplies policy settings. The output is either config_valid=true for a complete valid policy or a normalized error category. A valid retry policy must specify exactly one backoff strategy, a maximum try count or indefinite retry mode, required delays for delay-based backoffs, and no conflicting exception decision strategies. No-wait policies do not require a delay. Negative delays and maximum try counts below one are rejected.

**Test Cases:** `rcb_tests/public_test_cases/feature3_configuration_validation.json`

```json
{
    "description": "Validate policy construction rules and report either a valid policy or a normalized configuration error.",
    "cases": [
        {
            "input": {
                "validation_enabled": true,
                "settings": [
                    {
                        "max_tries": 1
                    },
                    {
                        "delay": {
                            "amount": 1,
                            "unit": "seconds"
                        }
                    }
                ]
            },
            "expected_output": "error=missing_backoff\n"
        },
        {
            "input": {
                "validation_enabled": true,
                "settings": [
                    {
                        "max_tries": 1
                    },
                    {
                        "delay": {
                            "amount": 1,
                            "unit": "seconds"
                        }
                    },
                    {
                        "backoff": "exponential"
                    },
                    {
                        "backoff": "fibonacci"
                    }
                ]
            },
            "expected_output": "error=multiple_backoff_strategies\n"
        },
        {
            "input": {
                "validation_enabled": true,
                "settings": [
                    {
                        "max_tries": 1
                    },
                    {
                        "backoff": "no_wait"
                    }
                ]
            },
            "expected_output": "config_valid=true\n"
        },
        {
            "input": {
                "validation_enabled": true,
                "settings": [
                    {
                        "max_tries": 1
                    },
                    {
                        "delay": {
                            "amount": 1,
                            "unit": "seconds"
                        }
                    },
                    {
                        "backoff": "exponential"
                    },
                    {
                        "retry_on": "fail_any_exception"
                    },
                    {
                        "retry_on": "specific_exceptions",
                        "exceptions": [
                            "connect_error"
                        ]
                    }
                ]
            },
            "expected_output": "error=multiple_exception_strategies\n"
        },
        {
            "input": {
                "validation_enabled": true,
                "settings": [
                    {
                        "backoff": "fixed"
                    },
                    {
                        "retry_indefinitely": true
                    },
                    {
                        "delay": {
                            "amount": -1,
                            "unit": "seconds"
                        }
                    }
                ]
            },
            "expected_output": "error=negative_delay\n"
        }
    ]
}
```

---

### Feature 4: Synchronous Retry Execution

**As a developer**, I want to run an operation under a retry policy, so I can receive a final status or normalized retry failure.

**Expected Behavior / Usage:**

The input contains a retry policy, an optional call name, and a sequence of operation outcomes. Each attempt consumes the next outcome, and once the sequence is exhausted the final outcome repeats. The output reports the returned result, success flag, call name, and total tries for success, or a normalized retries_exhausted error with status fields and the last retry-causing exception category when all attempts are consumed.

**Test Cases:** `rcb_tests/public_test_cases/feature4_synchronous_execution.json`

```json
{
    "description": "Run a synchronous operation under a retry policy and report the final status or normalized failure.",
    "cases": [
        {
            "input": {
                "policy": {
                    "max_tries": 5,
                    "backoff": "fixed",
                    "delay_ms": 0
                },
                "operation": {
                    "outcomes": [
                        {
                            "return": true
                        }
                    ]
                }
            },
            "expected_output": "result=true\nsuccessful=true\ncall_name=\ntotal_tries=1\n"
        },
        {
            "input": {
                "policy": {
                    "max_tries": 5,
                    "backoff": "fixed",
                    "delay_ms": 0,
                    "retry_on": "any_exception"
                },
                "call_name": "TestCall",
                "operation": {
                    "outcomes": [
                        {
                            "throw": "file_not_found"
                        }
                    ]
                }
            },
            "expected_output": "error=retries_exhausted\nsuccessful=false\ncall_name=TestCall\ntotal_tries=5\nlast_exception=file_not_found\n"
        },
        {
            "input": {
                "policy": {
                    "max_tries": 1,
                    "delay_ms": 0
                },
                "operation": {
                    "outcomes": [
                        {
                            "return": null
                        }
                    ]
                }
            },
            "expected_output": "result=null\nsuccessful=true\ncall_name=\ntotal_tries=1\n"
        }
    ]
}
```

---

### Feature 5: Exception Matching Rules

**As a developer**, I want to retry only failures that match configured categories, so I can avoid retrying unexpected failure types.

**Expected Behavior / Usage:**

The input configures retryable exception categories, optionally matching through the causal chain instead of only the top-level failure. The output reports retries_exhausted when a thrown failure or its configured cause matches and the attempt limit is reached. It reports unexpected_exception with the top-level exception category when the thrown failure is not retryable.

**Test Cases:** `rcb_tests/public_test_cases/feature5_exception_matching.json`

```json
{
    "description": "Apply exception retry rules to thrown failures and report whether the failure is retried until exhaustion or rejected as unexpected.",
    "cases": [
        {
            "input": {
                "policy": {
                    "max_tries": 1,
                    "backoff": "fixed",
                    "delay_ms": 0,
                    "retry_on": "caused_by",
                    "exceptions": [
                        "custom_error"
                    ]
                },
                "operation": {
                    "outcomes": [
                        {
                            "throw": "wrapper_error",
                            "cause": {
                                "throw": "custom_error"
                            }
                        }
                    ]
                }
            },
            "expected_output": "error=retries_exhausted\nsuccessful=false\ntotal_tries=1\nlast_exception=wrapper_error\n"
        },
        {
            "input": {
                "policy": {
                    "max_tries": 1,
                    "backoff": "fixed",
                    "delay_ms": 0,
                    "retry_on": "caused_by",
                    "exceptions": [
                        "io_error"
                    ]
                },
                "operation": {
                    "outcomes": [
                        {
                            "throw": "wrapper_error",
                            "cause": {
                                "throw": "custom_error"
                            }
                        }
                    ]
                }
            },
            "expected_output": "error=unexpected_exception\nexception=wrapper_error\n"
        },
        {
            "input": {
                "policy": {
                    "max_tries": 1,
                    "backoff": "fixed",
                    "delay_ms": 0,
                    "retry_on": "specific_exceptions",
                    "exceptions": [
                        "general_error"
                    ]
                },
                "operation": {
                    "outcomes": [
                        {
                            "throw": "io_error"
                        }
                    ]
                }
            },
            "expected_output": "error=retries_exhausted\nsuccessful=false\ntotal_tries=1\nlast_exception=io_error\n"
        }
    ]
}
```

---

### Feature 6: Exception Exclusion Rules

**As a developer**, I want to retry broad failures while excluding selected categories, so I can stop immediately for known non-retryable failures.

**Expected Behavior / Usage:**

The input configures retry-on-any-exception except for excluded categories. Category matching is inheritance-aware: excluding a broader category excludes its narrower subcategories, while excluding a narrower category does not exclude its broader parent. The output reports unexpected_exception for excluded failures and retries_exhausted for non-excluded failures after the configured attempt limit.

**Test Cases:** `rcb_tests/public_test_cases/feature6_exclusion_matching.json`

```json
{
    "description": "Retry all failures except configured excluded categories, using inheritance-aware matching for excluded categories.",
    "cases": [
        {
            "input": {
                "policy": {
                    "max_tries": 1,
                    "backoff": "fixed",
                    "delay_ms": 0,
                    "retry_on": "any_exception_excluding",
                    "exceptions": [
                        "unsupported_operation"
                    ]
                },
                "operation": {
                    "outcomes": [
                        {
                            "throw": "unsupported_operation"
                        }
                    ]
                }
            },
            "expected_output": "error=unexpected_exception\nexception=unsupported_operation\n"
        },
        {
            "input": {
                "policy": {
                    "max_tries": 1,
                    "backoff": "fixed",
                    "delay_ms": 0,
                    "retry_on": "any_exception_excluding",
                    "exceptions": [
                        "io_error"
                    ]
                },
                "operation": {
                    "outcomes": [
                        {
                            "throw": "file_not_found"
                        }
                    ]
                }
            },
            "expected_output": "error=unexpected_exception\nexception=file_not_found\n"
        },
        {
            "input": {
                "policy": {
                    "max_tries": 5,
                    "backoff": "no_wait",
                    "retry_on": "any_exception_excluding",
                    "exceptions": [
                        "argument_error",
                        "unsupported_operation"
                    ]
                },
                "operation": {
                    "outcomes": [
                        {
                            "throw": "null_reference"
                        }
                    ]
                }
            },
            "expected_output": "error=retries_exhausted\nsuccessful=false\ntotal_tries=5\nlast_exception=null_reference\n"
        }
    ]
}
```

---

### Feature 7: Return Value Retry Triggers

**As a developer**, I want to treat selected return values as failed attempts, so I can retry undesirable results as well as exceptions.

**Expected Behavior / Usage:**

The input configures a return value that should trigger retry and provides operation outcomes. If an attempt returns a value equal to the configured retry value, that attempt is treated as unsuccessful and retries continue until a different value is returned or tries are exhausted. The output reports the successful non-matching result or a retries_exhausted status whose last exception field is empty when exhaustion was caused only by return values.

**Test Cases:** `rcb_tests/public_test_cases/feature7_return_value_retry.json`

```json
{
    "description": "Treat selected returned values as retry-triggering failures and continue until the attempt limit is reached or a non-matching value is returned.",
    "cases": [
        {
            "input": {
                "policy": {
                    "max_tries": 3,
                    "backoff": "fixed",
                    "delay_ms": 0,
                    "retry_on": "any_exception",
                    "retry_on_value": "should retry!"
                },
                "operation": {
                    "outcomes": [
                        {
                            "return": "should retry!"
                        }
                    ]
                }
            },
            "expected_output": "error=retries_exhausted\nsuccessful=false\ntotal_tries=3\nlast_exception=\n"
        },
        {
            "input": {
                "policy": {
                    "max_tries": 3,
                    "backoff": "fixed",
                    "delay_ms": 0,
                    "retry_on": "any_exception",
                    "retry_on_value": false
                },
                "operation": {
                    "outcomes": [
                        {
                            "return": true
                        }
                    ]
                }
            },
            "expected_output": "result=true\nsuccessful=true\ncall_name=\ntotal_tries=1\n"
        },
        {
            "input": {
                "policy": {
                    "max_tries": 3,
                    "backoff": "fixed",
                    "delay_ms": 0,
                    "retry_on": "any_exception",
                    "retry_on_value": {
                        "label": "should retry on this value!"
                    }
                },
                "operation": {
                    "outcomes": [
                        {
                            "return": {
                                "label": "should NOT retry on this value!"
                            }
                        }
                    ]
                }
            },
            "expected_output": "result=object(label=should NOT retry on this value!)\nsuccessful=true\ncall_name=\ntotal_tries=1\n"
        }
    ]
}
```

---

### Feature 8: Custom Exception Predicate

**As a developer**, I want to decide retryability with a custom predicate, so I can model domain-specific retry rules.

**Expected Behavior / Usage:**

The input selects a custom predicate and provides thrown failures. A message-based predicate retries failures whose message contains the retry marker. A custom-value predicate retries custom failures whose numeric value is positive. The output reports retries_exhausted when the predicate accepts the failure through the attempt limit and unexpected_exception when it rejects the failure.

**Test Cases:** `rcb_tests/public_test_cases/feature8_custom_exception_logic.json`

```json
{
    "description": "Use a custom exception predicate to decide which failures are retryable.",
    "cases": [
        {
            "input": {
                "policy": {
                    "max_tries": 3,
                    "backoff": "fixed",
                    "delay_ms": 1,
                    "custom_exception_rule": "message_contains_retry"
                },
                "operation": {
                    "outcomes": [
                        {
                            "throw": "runtime_error",
                            "message": "should retry!"
                        }
                    ]
                }
            },
            "expected_output": "error=retries_exhausted\nsuccessful=false\ntotal_tries=3\nlast_exception=runtime_error\n"
        },
        {
            "input": {
                "policy": {
                    "max_tries": 3,
                    "backoff": "fixed",
                    "delay_ms": 1,
                    "custom_exception_rule": "message_contains_retry"
                },
                "operation": {
                    "outcomes": [
                        {
                            "throw": "runtime_error",
                            "message": "should NOT retry!"
                        }
                    ]
                }
            },
            "expected_output": "error=unexpected_exception\nexception=runtime_error\n"
        },
        {
            "input": {
                "policy": {
                    "max_tries": 3,
                    "backoff": "fixed",
                    "delay_ms": 1,
                    "custom_exception_rule": "custom_value_positive"
                },
                "operation": {
                    "outcomes": [
                        {
                            "throw": "custom_error",
                            "message": "should retry!",
                            "value": 100
                        }
                    ]
                }
            },
            "expected_output": "error=retries_exhausted\nsuccessful=false\ntotal_tries=3\nlast_exception=custom_error\n"
        },
        {
            "input": {
                "policy": {
                    "max_tries": 3,
                    "backoff": "fixed",
                    "delay_ms": 1,
                    "custom_exception_rule": "custom_value_positive"
                },
                "operation": {
                    "outcomes": [
                        {
                            "throw": "custom_error",
                            "message": "test message",
                            "value": -100
                        }
                    ]
                }
            },
            "expected_output": "error=unexpected_exception\nexception=custom_error\n"
        }
    ]
}
```

---

### Feature 9: Synchronous Lifecycle Listeners

**As a developer**, I want to observe retry lifecycle events, so I can record side effects around attempts and completion.

**Expected Behavior / Usage:**

The input attaches named lifecycle listeners to a synchronous execution. The output reports the final result/status plus invocation counts for after-failed-try, before-next-try, success, failure, and completion listeners. Failed-attempt listeners run once for every retry-causing failed attempt. Before-next-try runs only before an actual retry, not after the final failure. Success and completion listeners run on successful completion; a configured failure listener runs instead of throwing on exhausted retries.

**Test Cases:** `rcb_tests/public_test_cases/feature9_listener_events.json`

```json
{
    "description": "Attach lifecycle listeners to a synchronous execution and report listener invocation counts and final status signals.",
    "cases": [
        {
            "input": {
                "policy": {
                    "max_tries": 5,
                    "backoff": "fixed",
                    "delay_ms": 0,
                    "retry_on": "any_exception"
                },
                "listeners": [
                    "after_failed_try"
                ],
                "operation": {
                    "outcomes": [
                        {
                            "throw": "runtime_error"
                        },
                        {
                            "throw": "runtime_error"
                        },
                        {
                            "return": "success!"
                        }
                    ]
                }
            },
            "expected_output": "result=success!\nsuccessful=true\ntotal_tries=3\nafter_failed_try=2\nbefore_next_try=0\non_success=0\non_failure=0\non_completion=0\n"
        },
        {
            "input": {
                "policy": {
                    "max_tries": 5,
                    "backoff": "fixed",
                    "delay_ms": 0,
                    "retry_on": "any_exception"
                },
                "listeners": [
                    "before_next_try"
                ],
                "operation": {
                    "outcomes": [
                        {
                            "throw": "runtime_error"
                        },
                        {
                            "throw": "runtime_error"
                        },
                        {
                            "return": "success!"
                        }
                    ]
                }
            },
            "expected_output": "result=success!\nsuccessful=true\ntotal_tries=3\nafter_failed_try=0\nbefore_next_try=2\non_success=0\non_failure=0\non_completion=0\n"
        },
        {
            "input": {
                "policy": {
                    "max_tries": 5,
                    "backoff": "fixed",
                    "delay_ms": 0,
                    "retry_on": "any_exception"
                },
                "listeners": [
                    "on_success",
                    "on_failure",
                    "on_completion",
                    "after_failed_try",
                    "before_next_try"
                ],
                "operation": {
                    "outcomes": [
                        {
                            "return": "success!"
                        }
                    ]
                }
            },
            "expected_output": "result=success!\nsuccessful=true\ntotal_tries=1\nafter_failed_try=0\nbefore_next_try=0\non_success=1\non_failure=0\non_completion=1\n"
        },
        {
            "input": {
                "policy": {
                    "max_tries": 5,
                    "backoff": "fixed",
                    "delay_ms": 0,
                    "retry_on": "any_exception"
                },
                "listeners": [
                    "on_success",
                    "on_failure",
                    "on_completion",
                    "after_failed_try",
                    "before_next_try"
                ],
                "operation": {
                    "outcomes": [
                        {
                            "throw": "runtime_error"
                        },
                        {
                            "throw": "runtime_error"
                        },
                        {
                            "throw": "runtime_error"
                        },
                        {
                            "return": "success!"
                        }
                    ]
                }
            },
            "expected_output": "result=success!\nsuccessful=true\ntotal_tries=4\nafter_failed_try=3\nbefore_next_try=3\non_success=1\non_failure=0\non_completion=1\n"
        }
    ]
}
```

---

### Feature 10: Asynchronous Retry Execution

**As a developer**, I want to run retry-controlled operations asynchronously, so I can observe future completion without blocking the caller thread permanently.

**Expected Behavior / Usage:**

The input provides a retry policy, an executor selection, and one or more asynchronous calls. The output reports completed futures and successful completions for multiple calls, or the single future success/error signal for one call. Failed asynchronous calls complete their futures with normalized retry errors, and provided executors are reported as the execution source when selected.

**Test Cases:** `rcb_tests/public_test_cases/feature10_asynchronous_execution.json`

```json
{
    "description": "Run operations asynchronously and report future completion signals for success and failure paths.",
    "cases": [
        {
            "input": {
                "policy": {
                    "max_tries": 1,
                    "backoff": "fixed",
                    "delay_ms": 0,
                    "retry_on": "any_exception"
                },
                "executor": "default",
                "calls": [
                    {
                        "outcomes": [
                            {
                                "return": true
                            }
                        ]
                    },
                    {
                        "outcomes": [
                            {
                                "return": true
                            }
                        ]
                    },
                    {
                        "outcomes": [
                            {
                                "return": true
                            }
                        ]
                    }
                ]
            },
            "expected_output": "futures_done=3\ncompleted_successfully=3\n"
        },
        {
            "input": {
                "policy": {
                    "max_tries": 1,
                    "backoff": "fixed",
                    "delay_ms": 0,
                    "retry_on": "any_exception"
                },
                "executor": "default",
                "calls": [
                    {
                        "outcomes": [
                            {
                                "throw": "runtime_error"
                            }
                        ]
                    }
                ]
            },
            "expected_output": "future_error=retries_exhausted\n"
        },
        {
            "input": {
                "policy": {
                    "max_tries": 1,
                    "backoff": "fixed",
                    "delay_ms": 0,
                    "retry_on": "any_exception"
                },
                "executor": "provided",
                "calls": [
                    {
                        "outcomes": [
                            {
                                "return": true
                            }
                        ]
                    },
                    {
                        "outcomes": [
                            {
                                "return": true
                            }
                        ]
                    },
                    {
                        "outcomes": [
                            {
                                "return": true
                            }
                        ]
                    }
                ]
            },
            "expected_output": "futures_done=3\ncompleted_successfully=3\nexecutor=provided\n"
        },
        {
            "input": {
                "policy": {
                    "max_tries": 1,
                    "backoff": "fixed",
                    "delay_ms": 0,
                    "retry_on": "fail_any_exception"
                },
                "executor": "provided",
                "calls": [
                    {
                        "outcomes": [
                            {
                                "throw": "runtime_error"
                            }
                        ]
                    }
                ]
            },
            "expected_output": "future_error=unexpected_exception\nexecutor=provided\n"
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
- report missing backoff strategy
- Report success with result, flag, call_name, and total_tries
