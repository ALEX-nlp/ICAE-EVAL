## Product Requirement Document

# Cross-Origin HTTP Policy Middleware - Request and Response Header Control

## Project Goal

Build a cross-origin HTTP policy component that allows developers to apply route-aware CORS behavior to server applications without manually writing repetitive preflight handling, response header mutation, and configuration selection code.

---

## Background & Problem

Without this library/tool, developers are forced to inspect Origin and preflight headers in every relevant HTTP endpoint, decide which configured policy applies to each URL and host, and emit the correct CORS response headers by hand. This leads to repetitive middleware code, inconsistent browser behavior, and fragile policy changes when routes or hosts evolve.

With this library/tool, developers define reusable cross-origin policies and let a request/response integration layer decide when to short-circuit preflight requests, when to let regular requests continue, and which response headers to add.

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

### Feature 1: Successful Preflight Response

**As a developer**, I want matching preflight HTTP requests to be answered by the policy layer, so I can satisfy browser CORS negotiation before the application endpoint runs.

**Expected Behavior / Usage:**

The adapter receives a `cors_exchange` input with `exchange` set to `request`, a policy containing allowed origins, allowed methods, and optionally allowed request headers, plus an HTTP request with method `OPTIONS`, an `Origin` header, and an `Access-Control-Request-Method` header. When the origin is allowed and the requested method is accepted, output must describe an immediate request-phase HTTP response. The response includes `status=200`, the request URL and method, `Access-Control-Allow-Origin` equal to the incoming origin, `Access-Control-Allow-Methods` listing configured methods, `Vary` containing `Origin`, and `Access-Control-Allow-Headers` when configured. If the requested method has the same letters but a different case than the configured method, the response preserves the client-sent method form by appending it to the allowed-methods header.

**Test Cases:** `rcb_tests/public_test_cases/feature1_preflight_success.json`

```json
{
    "description": "Preflight requests that match the configured cross-origin policy return an immediate HTTP response with the allowed origin, allowed methods, allowed request headers, and Origin in Vary.",
    "cases": [
        {
            "input": {
                "interaction": "cors_exchange",
                "exchange": "request",
                "policy": {
                    "allowed_origins": "*",
                    "allowed_headers": [
                        "foo",
                        "bar"
                    ],
                    "allowed_methods": [
                        "[a list of predefined HTTP methods]",
                        "[a list of predefined HTTP methods]"
                    ]
                },
                "request": {
                    "path": "/foo",
                    "method": "OPTIONS",
                    "headers": {
                        "Origin": "http://example.com",
                        "Access-Control-Request-Method": "[a list of predefined HTTP methods]",
                        "Access-Control-Request-Headers": "Foo, BAR"
                    }
                }
            },
            "expected_output": "phase=request\nurl=/foo\nmethod=OPTIONS\nresponse_created=yes\nstatus=200\nheader:Access-Control-Allow-Origin=http://example.com\nheader:Access-Control-Allow-Methods=[a list of predefined HTTP methods], [a list of predefined HTTP methods]\nheader:Access-Control-Allow-Headers=foo, bar\nheader:Access-Control-Allow-Credentials=\nheader:Access-Control-Expose-Headers=\nheader:Access-Control-Max-Age=\nvary=Origin\nbody=\n"
        },
        {
            "input": {
                "interaction": "cors_exchange",
                "exchange": "request",
                "policy": {
                    "allowed_origins": "*",
                    "allowed_methods": [
                        "[a specific set of uppercase method strings]",
                        "[a list of predefined HTTP methods]"
                    ]
                },
                "request": {
                    "path": "/foo",
                    "method": "OPTIONS",
                    "headers": {
                        "Origin": "http://example.com",
                        "Access-Control-Request-Method": "[a specific set of uppercase method strings]"
                    }
                }
            },
            "expected_output": "phase=request\nurl=/foo\nmethod=OPTIONS\nresponse_created=yes\nstatus=200\nheader:Access-Control-Allow-Origin=http://example.com\nheader:Access-Control-Allow-Methods=[a specific set of uppercase method strings], [a list of predefined HTTP methods], [a specific set of uppercase method strings]\nheader:Access-Control-Allow-Headers=\nheader:Access-Control-Allow-Credentials=\nheader:Access-Control-Expose-Headers=\nheader:Access-Control-Max-Age=\nvary=Origin\nbody=\n"
        }
    ]
}
```

---

### Feature 2: Actual Cross-Origin Response Headers

**As a developer**, I want accepted actual cross-origin requests to continue to the application and receive CORS headers on the final response, so normal endpoint processing is preserved.

**Expected Behavior / Usage:**

The adapter receives a `cors_exchange` input with `exchange` set to `response`, a cross-origin non-OPTIONS HTTP request, and a policy that allows the request origin. The request phase must not create a separate preflight response; instead, the final response is rendered with `phase=response`, `status=200`, and `Access-Control-Allow-Origin` equal to the incoming origin. Preflight-only response headers such as `Access-Control-Allow-Methods` and `Access-Control-Allow-Headers` must remain empty for actual requests.

**Test Cases:** `rcb_tests/public_test_cases/feature2_actual_response_headers.json`

```json
{
    "description": "Actual cross-origin requests that pass the policy do not receive a request-phase response, then the final HTTP response receives only actual-response CORS headers, not preflight-only headers.",
    "cases": [
        {
            "input": {
                "interaction": "cors_exchange",
                "exchange": "response",
                "policy": {
                    "allowed_origins": "*",
                    "allowed_headers": [
                        "foo",
                        "bar"
                    ],
                    "allowed_methods": [
                        "[a list of predefined HTTP methods]",
                        "[a list of predefined HTTP methods]"
                    ]
                },
                "request": {
                    "path": "/foo",
                    "method": "[a list of predefined HTTP methods]",
                    "headers": {
                        "Origin": "http://example.com",
                        "Foo": "huh",
                        "BAR": "lala"
                    }
                }
            },
            "expected_output": "phase=response\nurl=/foo\nmethod=[a list of predefined HTTP methods]\nresponse_created=yes\nstatus=200\nheader:Access-Control-Allow-Origin=http://example.com\nheader:Access-Control-Allow-Methods=\nheader:Access-Control-Allow-Headers=\nheader:Access-Control-Allow-Credentials=\nheader:Access-Control-Expose-Headers=\nheader:Access-Control-Max-Age=\nvary=\nbody=\n"
        }
    ]
}
```

---

### Feature 3: Forced Allow-Origin Override

**As a developer**, I want to configure a fixed allow-origin response value, so deployments that require a canonical header value can override the reflected origin.

**Expected Behavior / Usage:**

The adapter receives a `cors_exchange` input with a policy field `override_allow_origin`. During response rendering, `Access-Control-Allow-Origin` must be set to this configured override value. This applies to successful preflight requests, preflight requests whose origin would otherwise be rejected, accepted actual requests, and requests without an `Origin` header. For preflight requests, the output still includes request URL, method, status, preflight headers, and `Vary` where the request-phase preflight response was created.

**Test Cases:** `rcb_tests/public_test_cases/feature3_forced_origin_override.json`

```json
{
    "description": "When an override allow-origin value is configured, the emitted Access-Control-Allow-Origin response header uses that override value for matching preflight requests, non-matching preflight requests, accepted actual requests, and requests without an Origin header.",
    "cases": [
        {
            "input": {
                "interaction": "cors_exchange",
                "exchange": "response",
                "policy": {
                    "allowed_origins": "*",
                    "allowed_methods": [
                        "[a list of predefined HTTP methods]"
                    ],
                    "override_allow_origin": "*"
                },
                "request": {
                    "path": "/foo",
                    "method": "OPTIONS",
                    "headers": {
                        "Origin": "http://example.com",
                        "Access-Control-Request-Method": "[a list of predefined HTTP methods]"
                    }
                }
            },
            "expected_output": "phase=response\nurl=/foo\nmethod=OPTIONS\nresponse_created=yes\nstatus=200\nheader:Access-Control-Allow-Origin=*\nheader:Access-Control-Allow-Methods=[a list of predefined HTTP methods]\nheader:Access-Control-Allow-Headers=\nheader:Access-Control-Allow-Credentials=\nheader:Access-Control-Expose-Headers=\nheader:Access-Control-Max-Age=\nvary=Origin\nbody=\n"
        },
        {
            "input": {
                "interaction": "cors_exchange",
                "exchange": "response",
                "policy": {
                    "allowed_origins": [
                        "http://example.com"
                    ],
                    "allowed_methods": [
                        "[a list of predefined HTTP methods]"
                    ],
                    "override_allow_origin": "http://example.com http://huh-lala.foobar"
                },
                "request": {
                    "path": "/foo",
                    "method": "[a list of predefined HTTP methods]",
                    "headers": {
                        "Origin": "http://example.com"
                    }
                }
            },
            "expected_output": "phase=response\nurl=/foo\nmethod=[a list of predefined HTTP methods]\nresponse_created=yes\nstatus=200\nheader:Access-Control-Allow-Origin=http://example.com http://huh-lala.foobar\nheader:Access-Control-Allow-Methods=\nheader:Access-Control-Allow-Headers=\nheader:Access-Control-Allow-Credentials=\nheader:Access-Control-Expose-Headers=\nheader:Access-Control-Max-Age=\nvary=\nbody=\n"
        }
    ]
}
```

---

### Feature 4: Requests That Do Not Produce Request-Phase Responses

**As a developer**, I want same-origin traffic and rejected non-preflight origins to pass through request processing without a synthetic response, so the policy layer does not block unrelated application behavior.

**Expected Behavior / Usage:**

The adapter receives a `cors_exchange` input with `exchange` set to `request`. If the request origin matches the request host, the output must show `response_created=no`. If the request has a different origin but the policy does not allow it and the request is not a preflight request, the output must also show `response_created=no`. The output includes the phase, URL, and HTTP method so the behavior is observable as request processing rather than a direct stubbed result.

**Test Cases:** `rcb_tests/public_test_cases/feature4_non_cors_and_unmatched_origin.json`

```json
{
    "description": "Requests that are same-origin or whose Origin is not allowed by the policy continue without an immediate HTTP response during request processing.",
    "cases": [
        {
            "input": {
                "interaction": "cors_exchange",
                "exchange": "request",
                "policy": {
                    "allowed_origins": [],
                    "allowed_headers": [
                        "foo",
                        "bar"
                    ],
                    "allowed_methods": [
                        "[a list of predefined HTTP methods]",
                        "[a list of predefined HTTP methods]"
                    ]
                },
                "request": {
                    "path": "/foo",
                    "method": "[a list of predefined HTTP methods]",
                    "host": "example.com",
                    "headers": {
                        "Origin": "http://example.com"
                    }
                }
            },
            "expected_output": "phase=request\nurl=/foo\nmethod=[a list of predefined HTTP methods]\nresponse_created=no\n"
        },
        {
            "input": {
                "interaction": "cors_exchange",
                "exchange": "request",
                "policy": {
                    "allowed_origins": []
                },
                "request": {
                    "path": "/foo",
                    "method": "[a list of predefined HTTP methods]",
                    "host": "example.com",
                    "headers": {
                        "Origin": "http://evil.com"
                    }
                }
            },
            "expected_output": "phase=request\nurl=/foo\nmethod=[a list of predefined HTTP methods]\nresponse_created=no\n"
        }
    ]
}
```

---

### Feature 5: Path-Based Policy Selection

**As a developer**, I want cross-origin policies to be selected by request path, so different URL areas can use different origins, methods, headers, and cache durations.

**Expected Behavior / Usage:**

The adapter receives a `configuration_match` input with default policy values, ordered path-pattern policies, and a request path. It outputs the resolved policy fields as normalized lines. When no path pattern matches, default values are returned. When a path pattern matches, that policy is merged with defaults and returned. Earlier matching path patterns take precedence over later ones, allowing a more specific pattern to select regex-style origin matching before a broader path rule.

**Test Cases:** `rcb_tests/public_test_cases/feature5_path_policy_selection.json`

```json
{
    "description": "Path-based policy selection returns the first configured path pattern that matches the request URL, falls back to defaults when no path matches, and can select regex-origin policies.",
    "cases": [
        {
            "input": {
                "interaction": "configuration_match",
                "defaults": {
                    "allowed_origins": [
                        "http://one.example.com"
                    ],
                    "allowed_headers": [],
                    "allowed_methods": [
                        "[a list of predefined HTTP methods]"
                    ]
                },
                "path_policies": {
                    "^/test/regex": {
                        "credentials": true,
                        "allowed_origins": [
                            "^http://(.*)\\.example\\.com"
                        ],
                        "origin_pattern_matching": true,
                        "allowed_headers": "*",
                        "allowed_methods": [
                            "[a list of predefined HTTP methods]",
                            "[a list of predefined HTTP methods]"
                        ]
                    },
                    "^/test/": {
                        "credentials": true,
                        "allowed_origins": [
                            "http://two.example.com"
                        ],
                        "allowed_headers": "*",
                        "allowed_methods": [
                            "[a list of predefined HTTP methods]",
                            "[a list of predefined HTTP methods]"
                        ],
                        "exposed_headers": [
                            "X-CorsTest"
                        ],
                        "cache_seconds": 120
                    }
                },
                "request": {
                    "path": "/default/path"
                }
            },
            "expected_output": "allowed_origins=http://one.example.com\ncredentials=no\nallowed_headers=\nallowed_methods=[a list of predefined HTTP methods]\nexposed_headers=\ncache_seconds=0\nhost_patterns=\norigin_pattern_matching=no\noverride_allow_origin=\n"
        },
        {
            "input": {
                "interaction": "configuration_match",
                "defaults": {
                    "allowed_origins": [
                        "http://one.example.com"
                    ],
                    "allowed_headers": [],
                    "allowed_methods": [
                        "[a list of predefined HTTP methods]"
                    ]
                },
                "path_policies": {
                    "^/test/regex": {
                        "credentials": true,
                        "allowed_origins": [
                            "^http://(.*)\\.example\\.com"
                        ],
                        "origin_pattern_matching": true,
                        "allowed_headers": "*",
                        "allowed_methods": [
                            "[a list of predefined HTTP methods]",
                            "[a list of predefined HTTP methods]"
                        ]
                    },
                    "^/test/": {
                        "credentials": true,
                        "allowed_origins": [
                            "http://two.example.com"
                        ],
                        "allowed_headers": "*",
                        "allowed_methods": [
                            "[a list of predefined HTTP methods]",
                            "[a list of predefined HTTP methods]"
                        ],
                        "exposed_headers": [
                            "X-CorsTest"
                        ],
                        "cache_seconds": 120
                    }
                },
                "request": {
                    "path": "/test/abc"
                }
            },
            "expected_output": "allowed_origins=http://two.example.com\ncredentials=yes\nallowed_headers=*\nallowed_methods=[a list of predefined HTTP methods], [a list of predefined HTTP methods]\nexposed_headers=X-CorsTest\ncache_seconds=120\nhost_patterns=\norigin_pattern_matching=no\noverride_allow_origin=\n"
        }
    ]
}
```

---

### Feature 6: Host-Restricted Policy Selection

**As a developer**, I want a path policy to apply only to selected hosts, so identical URL paths can have different CORS behavior depending on the requested domain.

**Expected Behavior / Usage:**

The adapter receives a `configuration_match` input whose path policies may include `host_patterns`. A path policy with host restrictions is selected only when the request host matches at least one host pattern. If the path matches but the host does not, selection continues to later path policies. Output must show the final resolved policy fields, including the selected origin list, allowed methods, exposed headers, cache seconds, and host patterns.

**Test Cases:** `rcb_tests/public_test_cases/feature6_host_restricted_policy_selection.json`

```json
{
    "description": "A path policy with host restrictions is used only when the request host matches one of its host patterns; otherwise matching continues to the next eligible path policy.",
    "cases": [
        {
            "input": {
                "interaction": "configuration_match",
                "defaults": {
                    "allowed_origins": [
                        "http://one.example.com"
                    ],
                    "allowed_headers": [],
                    "allowed_methods": [
                        "[a list of predefined HTTP methods]"
                    ]
                },
                "path_policies": {
                    "^/test/match": {
                        "credentials": true,
                        "allowed_origins": [
                            "http://domainmatch.example.com"
                        ],
                        "allowed_headers": "*",
                        "allowed_methods": [
                            "[a list of predefined HTTP methods]",
                            "[a list of predefined HTTP methods]"
                        ],
                        "cache_seconds": 160,
                        "host_patterns": [
                            "^test\\.",
                            "\\.example\\.org$"
                        ]
                    },
                    "^/test/nomatch": {
                        "credentials": true,
                        "allowed_origins": [
                            "http://nomatch.example.com"
                        ],
                        "allowed_headers": "*",
                        "allowed_methods": [
                            "[a list of predefined HTTP methods]",
                            "[a list of predefined HTTP methods]"
                        ],
                        "exposed_headers": [
                            "X-CorsTest"
                        ],
                        "cache_seconds": 180,
                        "host_patterns": [
                            "^nomatch\\."
                        ]
                    },
                    "^/test/": {
                        "credentials": true,
                        "allowed_origins": [
                            "http://two.example.com"
                        ],
                        "allowed_headers": "*",
                        "allowed_methods": [
                            "[a list of predefined HTTP methods]",
                            "[a list of predefined HTTP methods]"
                        ],
                        "exposed_headers": [
                            "X-CorsTest"
                        ],
                        "cache_seconds": 120
                    }
                },
                "request": {
                    "path": "/test/match",
                    "method": "OPTIONS",
                    "host": "test.example.com"
                }
            },
            "expected_output": "allowed_origins=http://domainmatch.example.com\ncredentials=yes\nallowed_headers=*\nallowed_methods=[a list of predefined HTTP methods], [a list of predefined HTTP methods]\nexposed_headers=\ncache_seconds=160\nhost_patterns=^test\\., \\.example\\.org$\norigin_pattern_matching=no\noverride_allow_origin=\n"
        },
        {
            "input": {
                "interaction": "configuration_match",
                "defaults": {
                    "allowed_origins": [
                        "http://one.example.com"
                    ],
                    "allowed_headers": [],
                    "allowed_methods": [
                        "[a list of predefined HTTP methods]"
                    ]
                },
                "path_policies": {
                    "^/test/match": {
                        "credentials": true,
                        "allowed_origins": [
                            "http://domainmatch.example.com"
                        ],
                        "allowed_headers": "*",
                        "allowed_methods": [
                            "[a list of predefined HTTP methods]",
                            "[a list of predefined HTTP methods]"
                        ],
                        "cache_seconds": 160,
                        "host_patterns": [
                            "^test\\.",
                            "\\.example\\.org$"
                        ]
                    },
                    "^/test/nomatch": {
                        "credentials": true,
                        "allowed_origins": [
                            "http://nomatch.example.com"
                        ],
                        "allowed_headers": "*",
                        "allowed_methods": [
                            "[a list of predefined HTTP methods]",
                            "[a list of predefined HTTP methods]"
                        ],
                        "exposed_headers": [
                            "X-CorsTest"
                        ],
                        "cache_seconds": 180,
                        "host_patterns": [
                            "^nomatch\\."
                        ]
                    },
                    "^/test/": {
                        "credentials": true,
                        "allowed_origins": [
                            "http://two.example.com"
                        ],
                        "allowed_headers": "*",
                        "allowed_methods": [
                            "[a list of predefined HTTP methods]",
                            "[a list of predefined HTTP methods]"
                        ],
                        "exposed_headers": [
                            "X-CorsTest"
                        ],
                        "cache_seconds": 120
                    }
                },
                "request": {
                    "path": "/test/nomatch",
                    "method": "OPTIONS",
                    "host": "example.com"
                }
            },
            "expected_output": "allowed_origins=http://two.example.com\ncredentials=yes\nallowed_headers=*\nallowed_methods=[a list of predefined HTTP methods], [a list of predefined HTTP methods]\nexposed_headers=X-CorsTest\ncache_seconds=120\nhost_patterns=\norigin_pattern_matching=no\noverride_allow_origin=\n"
        }
    ]
}
```

---

### Feature 7: Provider Policy Merge

**As a developer**, I want multiple policy providers to contribute options in order, so broad defaults can be overridden by later, higher-specificity providers.

**Expected Behavior / Usage:**

The adapter receives a `provider_merge` input with an ordered list of provider policy objects and a request. It outputs the merged policy fields. Providers are applied in list order; when a later provider supplies the same field, its value replaces the earlier value, and fields omitted by later providers keep the earlier value. The output must include enough resolved fields to show both replacement and preservation behavior.

**Test Cases:** `rcb_tests/public_test_cases/feature7_provider_merge.json`

```json
{
    "description": "When multiple policy providers apply to a request, later providers override earlier providers key by key; omitted keys from later providers keep the earlier value.",
    "cases": [
        {
            "input": {
                "interaction": "provider_merge",
                "request": {
                    "path": "/any"
                },
                "providers": [
                    {
                        "policy": {
                            "allowed_origins": [
                                "a"
                            ],
                            "exposed_headers": [
                                "c",
                                "d"
                            ],
                            "allowed_headers": [
                                "a",
                                "b"
                            ]
                        }
                    },
                    {
                        "policy": {
                            "allowed_origins": [
                                "c"
                            ],
                            "allowed_headers": [
                                "e"
                            ],
                            "override_allow_origin": "x"
                        }
                    }
                ]
            },
            "expected_output": "allowed_origins=c\ncredentials=no\nallowed_headers=e\nallowed_methods=\nexposed_headers=c, d\ncache_seconds=0\nhost_patterns=\norigin_pattern_matching=no\noverride_allow_origin=x\n"
        }
    ]
}
```

---

### Feature 8: Provider Priority Ordering

**As a developer**, I want externally registered policy providers to be collected in deterministic priority order, so policy merging is predictable across deployments.

**Expected Behavior / Usage:**

The adapter receives a `provider_order` input with provider labels and optional numeric priorities. It outputs the total provider count and the ordered provider labels used by the resolver. Providers are ordered by ascending numeric priority. Providers with equal priority keep registration order. The built-in path-configuration provider is present as the lowest-priority provider and appears before unprioritized and positive-priority providers.

**Test Cases:** `rcb_tests/public_test_cases/feature8_provider_priority_order.json`

```json
{
    "description": "Tagged policy providers are collected into the runtime resolver in ascending numeric priority order, with the built-in path-configuration provider included at the lowest priority.",
    "cases": [
        {
            "input": {
                "interaction": "provider_order",
                "providers": [
                    {
                        "label": "test1"
                    },
                    {
                        "label": "test2",
                        "priority": 10
                    },
                    {
                        "label": "test3",
                        "priority": 5
                    },
                    {
                        "label": "test4",
                        "priority": 5
                    }
                ]
            },
            "expected_output": "provider_count=4\nprovider_0=path_configuration\nprovider_1=test3\nprovider_2=test4\nprovider_3=test2\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_preflight_success.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_preflight_success@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same host validation strategy used in the server_resource matching module
