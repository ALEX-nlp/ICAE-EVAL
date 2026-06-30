## Product Requirement Document

# Cluster Observation Contract - Namespace and API Resource Discovery Behavior

## Project Goal

Build a cluster observation library that keeps an operator-facing view of namespaces and API resources synchronized with discovery data and watch events, allowing developers to react only to available, permitted, and unambiguous targets without writing repetitive discovery bookkeeping.

---

## Background & Problem

Without this library, developers are forced to manually list namespaces, interpret namespace watch events, scan API groups and versions, match declared reactions against discovered resources, and remove stale targets when resources dis[a vague domain identifier mentioned in the PRD]ear. This leads to fragile boilerplate, race-prone state updates, and handlers that may run for resources that are ambiguous, unavailable, or missing required API capabilities.

With this library, discovery inputs and watch events are translated into a concise observable state: matching namespaces, served resources, readiness of core resources, notification signals, and normalized warning categories for resource-selection problems.

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
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled [a vague domain identifier mentioned in the PRD]ropriately to the project's size):
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

### Feature 1: Namespace Refresh

**As a developer**, I want namespace discovery data to update the current namespace set, so I can run work only in namespaces that match the configured patterns.

**Expected Behavior / Usage:**

*1.1 Refresh from Listed Namespace Objects — Populate namespace state from list results*

A refresh input contains `action=refresh_namespaces`, a `patterns` array of namespace glob patterns, and ordered `steps` whose source is `bodies`. Each body supplies namespace metadata. Names matching at least one pattern are added to the observable namespace set. If a matching name is later seen with a deletion timestamp, it is removed. Names outside the patterns do not [a vague domain identifier mentioned in the PRD]ear in output. The adapter prints exactly one line, `namespaces=<comma-separated names>`, with an empty value when no namespace is selected.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_namespace_refresh_from_lists.json`

```json
{
    "description": "Refresh namespace membership from listed namespace objects, adding matching names, preserving prior matches across incremental refreshes, removing deletion-marked names, and ignoring names outside configured patterns.",
    "cases": [
        {
            "input": {
                "action": "refresh_namespaces",
                "patterns": [
                    "ns*"
                ],
                "steps": [
                    {
                        "source": "bodies",
                        "items": [
                            {
                                "metadata": {
                                    "name": "ns1"
                                }
                            }
                        ]
                    }
                ]
            },
            "expected_output": "namespaces=ns1\n"
        },
        {
            "input": {
                "action": "refresh_namespaces",
                "patterns": [
                    "ns*"
                ],
                "steps": [
                    {
                        "source": "bodies",
                        "items": [
                            {
                                "metadata": {
                                    "name": "ns1"
                                }
                            }
                        ]
                    },
                    {
                        "source": "bodies",
                        "items": [
                            {
                                "metadata": {
                                    "name": "ns2"
                                }
                            }
                        ]
                    }
                ]
            },
            "expected_output": "namespaces=ns1,ns2\n"
        },
        {
            "input": {
                "action": "refresh_namespaces",
                "patterns": [
                    "ns*"
                ],
                "steps": [
                    {
                        "source": "bodies",
                        "items": [
                            {
                                "metadata": {
                                    "name": "ns1"
                                }
                            }
                        ]
                    },
                    {
                        "source": "bodies",
                        "items": [
                            {
                                "metadata": {
                                    "name": "ns1",
                                    "deletionTimestamp": "..."
                                }
                            }
                        ]
                    }
                ]
            },
            "expected_output": "namespaces=\n"
        },
        {
            "input": {
                "action": "refresh_namespaces",
                "patterns": [
                    "ns*"
                ],
                "steps": [
                    {
                        "source": "bodies",
                        "items": [
                            {
                                "metadata": {
                                    "name": "def1"
                                }
                            }
                        ]
                    }
                ]
            },
            "expected_output": "namespaces=\n"
        }
    ]
}
```

*1.2 Refresh from Namespace Events — Populate namespace state from event objects*

A refresh input contains `action=refresh_namespaces`, a `patterns` array, and ordered `steps` whose source is `events`. Each event supplies a type and namespace metadata. Non-deletion events add matching names; events with deletion timestamps or deletion event types remove the name. Names that do not match the configured patterns remain absent. The adapter prints `namespaces=<comma-separated names>` as the complete stdout contract.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_namespace_refresh_from_events.json`

```json
{
    "description": "Refresh namespace membership from namespace event objects, treating ordinary events as additions, deletion timestamps or deletion event types as removals, and ignoring names outside configured patterns.",
    "cases": [
        {
            "input": {
                "action": "refresh_namespaces",
                "patterns": [
                    "ns*"
                ],
                "steps": [
                    {
                        "source": "events",
                        "items": [
                            {
                                "type": null,
                                "metadata": {
                                    "name": "ns1"
                                }
                            }
                        ]
                    }
                ]
            },
            "expected_output": "namespaces=ns1\n"
        },
        {
            "input": {
                "action": "refresh_namespaces",
                "patterns": [
                    "ns*"
                ],
                "steps": [
                    {
                        "source": "events",
                        "items": [
                            {
                                "type": null,
                                "metadata": {
                                    "name": "ns1"
                                }
                            }
                        ]
                    },
                    {
                        "source": "events",
                        "items": [
                            {
                                "type": null,
                                "metadata": {
                                    "name": "ns2"
                                }
                            }
                        ]
                    }
                ]
            },
            "expected_output": "namespaces=ns1,ns2\n"
        },
        {
            "input": {
                "action": "refresh_namespaces",
                "patterns": [
                    "ns*"
                ],
                "steps": [
                    {
                        "source": "events",
                        "items": [
                            {
                                "type": null,
                                "metadata": {
                                    "name": "ns1"
                                }
                            }
                        ]
                    },
                    {
                        "source": "events",
                        "items": [
                            {
                                "type": null,
                                "metadata": {
                                    "name": "ns1",
                                    "deletionTimestamp": "..."
                                }
                            }
                        ]
                    }
                ]
            },
            "expected_output": "namespaces=\n"
        },
        {
            "input": {
                "action": "refresh_namespaces",
                "patterns": [
                    "ns*"
                ],
                "steps": [
                    {
                        "source": "events",
                        "items": [
                            {
                                "type": null,
                                "metadata": {
                                    "name": "ns1"
                                }
                            }
                        ]
                    },
                    {
                        "source": "events",
                        "items": [
                            {
                                "type": "DELETED",
                                "metadata": {
                                    "name": "ns1"
                                }
                            }
                        ]
                    }
                ]
            },
            "expected_output": "namespaces=\n"
        },
        {
            "input": {
                "action": "refresh_namespaces",
                "patterns": [
                    "ns*"
                ],
                "steps": [
                    {
                        "source": "events",
                        "items": [
                            {
                                "type": null,
                                "metadata": {
                                    "name": "def1"
                                }
                            }
                        ]
                    }
                ]
            },
            "expected_output": "namespaces=\n"
        }
    ]
}
```

---

### Feature 2: Namespace Watch Event Processing

**As a developer**, I want namespace watch events to signal only real follow-up changes, so startup list events do not trigger unnecessary downstream work.

**Expected Behavior / Usage:**

A watch-event input contains `action=[a vague domain identifier mentioned in the PRD]ly_namespace_event`, configured namespace `patterns`, an optional `initial_namespaces` set, and one event with type and metadata. Events whose type is absent represent the initial list and must be ignored: they do not notify waiters and do not update the namespace set. Follow-up addition or modification events notify waiters and add matching namespaces. Follow-up deletion events notify waiters and remove the namespace. Stdout contains `notified=yes|no` followed by `namespaces=<comma-separated names>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_namespace_watch_event_processing.json`

```json
{
    "description": "Apply a single namespace watch event, ignoring initial-list events without notification and notifying when follow-up events add or remove a matching namespace.",
    "cases": [
        {
            "input": {
                "action": "[a vague domain identifier mentioned in the PRD]ly_namespace_event",
                "patterns": [
                    "ns*"
                ],
                "initial_namespaces": [],
                "event": {
                    "type": null,
                    "metadata": {
                        "name": "ns1"
                    }
                }
            },
            "expected_output": "notified=no\nnamespaces=\n"
        },
        {
            "input": {
                "action": "[a vague domain identifier mentioned in the PRD]ly_namespace_event",
                "patterns": [
                    "ns*"
                ],
                "initial_namespaces": [],
                "event": {
                    "type": "ADDED",
                    "metadata": {
                        "name": "ns1"
                    }
                }
            },
            "expected_output": "notified=yes\nnamespaces=ns1\n"
        },
        {
            "input": {
                "action": "[a vague domain identifier mentioned in the PRD]ly_namespace_event",
                "patterns": [
                    "ns*"
                ],
                "initial_namespaces": [],
                "event": {
                    "type": "MODIFIED",
                    "metadata": {
                        "name": "ns1"
                    }
                }
            },
            "expected_output": "notified=yes\nnamespaces=ns1\n"
        },
        {
            "input": {
                "action": "[a vague domain identifier mentioned in the PRD]ly_namespace_event",
                "patterns": [
                    "ns*"
                ],
                "initial_namespaces": [
                    "ns1"
                ],
                "event": {
                    "type": "DELETED",
                    "metadata": {
                        "name": "ns1"
                    }
                }
            },
            "expected_output": "notified=yes\nnamespaces=\n"
        }
    ]
}
```

---

### Feature 3: API Resource Refresh

**As a developer**, I want resource discovery to maintain the set of served API resources, so handlers are attached only to resources that are discoverable, unambiguous, and usable.

**Expected Behavior / Usage:**

*3.1 Selector-Based Resource Refresh — Match configured reactions to discovered resources*

A refresh input contains `action=refresh_resources`, a reaction category in `handler_mode`, one or more resource selectors, a refresh `group` scope, optional `initial_resources`, and the newly discovered `resources`. Admission-only reactions do not create served resources. Workload reactions select resources matching their group, version, and plural name. A refresh with `group` absent replaces the whole served set; a refresh with a group value replaces only resources from that API group, preserving resources from other groups. Stdout is `resources=<comma-separated group/version/plural entries>`, empty when nothing is served.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_resource_refresh_by_selectors.json`

```json
{
    "description": "Refresh served resources for configured workload reactions, ignoring admission-only reactions, adding matching watchable resources, and replacing either the whole catalog or one API group depending on the refresh scope.",
    "cases": [
        {
            "input": {
                "action": "refresh_resources",
                "handler_mode": "admission_validation",
                "selector": {
                    "group": "group1",
                    "version": "version1",
                    "plural": "plural1"
                },
                "group": null,
                "resources": [
                    {
                        "group": "group1",
                        "version": "version1",
                        "plural": "plural1",
                        "kind": "kind1",
                        "singular": "singular1",
                        "namespaced": true,
                        "categories": [
                            "category1a",
                            "category1b"
                        ],
                        "shortcuts": [
                            "shortname1a",
                            "shortname1b"
                        ],
                        "verbs": [
                            "list",
                            "watch",
                            "patch"
                        ]
                    },
                    {
                        "group": "group2",
                        "version": "version2",
                        "plural": "plural2",
                        "verbs": [
                            "list",
                            "watch",
                            "patch"
                        ]
                    }
                ]
            },
            "expected_output": "resources=\n"
        },
        {
            "input": {
                "action": "refresh_resources",
                "handler_mode": "watch_event",
                "selector": [
                    {
                        "group": "group1",
                        "version": "version1",
                        "plural": "plural1"
                    },
                    {
                        "group": "group2",
                        "version": "version2",
                        "plural": "plural2"
                    }
                ],
                "group": null,
                "resources": [
                    {
                        "group": "group1",
                        "version": "version1",
                        "plural": "plural1",
                        "kind": "kind1",
                        "singular": "singular1",
                        "namespaced": true,
                        "categories": [
                            "category1a",
                            "category1b"
                        ],
                        "shortcuts": [
                            "shortname1a",
                            "shortname1b"
                        ],
                        "verbs": [
                            "list",
                            "watch",
                            "patch"
                        ]
                    }
                ]
            },
            "expected_output": "resources=group1/version1/plural1\n"
        },
        {
            "input": {
                "action": "refresh_resources",
                "handler_mode": "watch_event",
                "selector": [
                    {
                        "group": "group1",
                        "version": "version1",
                        "plural": "plural1"
                    },
                    {
                        "group": "group2",
                        "version": "version2",
                        "plural": "plural2"
                    }
                ],
                "group": null,
                "initial_resources": [
                    {
                        "group": "group1",
                        "version": "version1",
                        "plural": "plural1",
                        "kind": "kind1",
                        "singular": "singular1",
                        "namespaced": true,
                        "categories": [
                            "category1a",
                            "category1b"
                        ],
                        "shortcuts": [
                            "shortname1a",
                            "shortname1b"
                        ],
                        "verbs": [
                            "list",
                            "watch",
                            "patch"
                        ]
                    }
                ],
                "resources": [
                    {
                        "group": "group2",
                        "version": "version2",
                        "plural": "plural2",
                        "verbs": [
                            "list",
                            "watch",
                            "patch"
                        ]
                    }
                ]
            },
            "expected_output": "resources=group2/version2/plural2\n"
        },
        {
            "input": {
                "action": "refresh_resources",
                "handler_mode": "watch_event",
                "selector": [
                    {
                        "group": "group1",
                        "version": "version1",
                        "plural": "plural1"
                    },
                    {
                        "group": "group2",
                        "version": "version2",
                        "plural": "plural2"
                    }
                ],
                "group": "group1",
                "initial_resources": [
                    {
                        "group": "group1",
                        "version": "version1",
                        "plural": "plural1",
                        "kind": "kind1",
                        "singular": "singular1",
                        "namespaced": true,
                        "categories": [
                            "category1a",
                            "category1b"
                        ],
                        "shortcuts": [
                            "shortname1a",
                            "shortname1b"
                        ],
                        "verbs": [
                            "list",
                            "watch",
                            "patch"
                        ]
                    }
                ],
                "resources": [
                    {
                        "group": "group2",
                        "version": "version2",
                        "plural": "plural2",
                        "verbs": [
                            "list",
                            "watch",
                            "patch"
                        ]
                    }
                ]
            },
            "expected_output": "resources=group2/version2/plural2\n"
        },
        {
            "input": {
                "action": "refresh_resources",
                "handler_mode": "watch_event",
                "selector": [
                    {
                        "group": "group1",
                        "version": "version1",
                        "plural": "plural1"
                    },
                    {
                        "group": "group2",
                        "version": "version2",
                        "plural": "plural2"
                    }
                ],
                "group": "group2",
                "initial_resources": [
                    {
                        "group": "group1",
                        "version": "version1",
                        "plural": "plural1",
                        "kind": "kind1",
                        "singular": "singular1",
                        "namespaced": true,
                        "categories": [
                            "category1a",
                            "category1b"
                        ],
                        "shortcuts": [
                            "shortname1a",
                            "shortname1b"
                        ],
                        "verbs": [
                            "list",
                            "watch",
                            "patch"
                        ]
                    }
                ],
                "resources": [
                    {
                        "group": "group2",
                        "version": "version2",
                        "plural": "plural2",
                        "verbs": [
                            "list",
                            "watch",
                            "patch"
                        ]
                    }
                ]
            },
            "expected_output": "resources=group1/version1/plural1,group2/version2/plural2\n"
        }
    ]
}
```

*3.2 Ambiguous and Unresolved Resource Selection — Report selector problems without serving unsafe targets*

A refresh input may use broad selectors such as a plural name or an explicit catch-all. If a specific broad selector matches multiple non-core API resources with the same name, the resources are excluded and stdout reports `warnings=ambiguous_resource`. If the same plain name exists in the core API and an extension API, the core API resource is selected and no warning is emitted. An explicit catch-all selector serves all matching non-event resources. If a selector matches no discovered resource, no resource is served and `warnings=unresolved_resource` is printed. Stdout contains `resources=...` and `warnings=<comma-separated warning categories>`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_resource_refresh_ambiguous_and_unresolved.json`

```json
{
    "description": "Resolve broad resource selectors against discovered resources, excluding ambiguous specific matches, preferring the core API when a plain name collides with an extension API, allowing explicit catch-all selection, and warning when no resource matches.",
    "cases": [
        {
            "input": {
                "action": "refresh_resources",
                "handler_mode": "watch_event",
                "selector": {
                    "plural": "plural"
                },
                "group": null,
                "resources": [
                    {
                        "group": "g1",
                        "version": "v1",
                        "plural": "plural",
                        "verbs": [
                            "list",
                            "watch",
                            "patch"
                        ]
                    },
                    {
                        "group": "g2",
                        "version": "v2",
                        "plural": "plural",
                        "verbs": [
                            "list",
                            "watch",
                            "patch"
                        ]
                    }
                ],
                "report_warnings": true
            },
            "expected_output": "resources=\nwarnings=ambiguous_resource\n"
        },
        {
            "input": {
                "action": "refresh_resources",
                "handler_mode": "watch_event",
                "selector": {
                    "plural": "pods"
                },
                "group": null,
                "resources": [
                    {
                        "group": "",
                        "version": "v1",
                        "plural": "pods",
                        "verbs": [
                            "list",
                            "watch",
                            "patch"
                        ]
                    },
                    {
                        "group": "metrics.k8s.io",
                        "version": "v1",
                        "plural": "pods",
                        "verbs": [
                            "list",
                            "watch",
                            "patch"
                        ]
                    }
                ],
                "report_warnings": true
            },
            "expected_output": "resources=/v1/pods\nwarnings=\n"
        },
        {
            "input": {
                "action": "refresh_resources",
                "handler_mode": "watch_event",
                "selector": "all",
                "group": null,
                "resources": [
                    {
                        "group": "g1",
                        "version": "v1",
                        "plural": "plural",
                        "verbs": [
                            "list",
                            "watch",
                            "patch"
                        ]
                    },
                    {
                        "group": "g2",
                        "version": "v2",
                        "plural": "plural",
                        "verbs": [
                            "list",
                            "watch",
                            "patch"
                        ]
                    }
                ],
                "report_warnings": true
            },
            "expected_output": "resources=g1/v1/plural,g2/v2/plural\nwarnings=\n"
        },
        {
            "input": {
                "action": "refresh_resources",
                "handler_mode": "watch_event",
                "selector": {
                    "plural": "plural3"
                },
                "group": null,
                "resources": [
                    {
                        "group": "group1",
                        "version": "version1",
                        "plural": "plural1",
                        "kind": "kind1",
                        "singular": "singular1",
                        "namespaced": true,
                        "categories": [
                            "category1a",
                            "category1b"
                        ],
                        "shortcuts": [
                            "shortname1a",
                            "shortname1b"
                        ],
                        "verbs": [
                            "list",
                            "watch",
                            "patch"
                        ]
                    },
                    {
                        "group": "group2",
                        "version": "version2",
                        "plural": "plural2",
                        "verbs": [
                            "list",
                            "watch",
                            "patch"
                        ]
                    }
                ],
                "report_warnings": true
            },
            "expected_output": "resources=\nwarnings=unresolved_resource\n"
        }
    ]
}
```

*3.3 Resource Capability Filtering — Exclude resources that cannot support required operations*

A refresh input contains a selected resource and the API verbs advertised for that resource. If a selected resource lacks both list and watch support, it is excluded and stdout reports `warnings=[a specific warning string for resources lacking watch capabilities]`. If a selected resource supports list/watch but lacks patch support while the configured reaction requires persisted state updates, it is excluded and stdout reports `warnings=non_patchable_resource`. Stdout contains `resources=...` and `warnings=...`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_resource_capability_filtering.json`

```json
{
    "description": "Filter selected resources by required API capabilities, rejecting resources without list/watch support and rejecting non-patchable resources when the configured reaction needs persistent state updates.",
    "cases": [
        {
            "input": {
                "action": "refresh_resources",
                "handler_mode": "background_task",
                "selector": {
                    "group": "group1",
                    "version": "version1",
                    "plural": "plural1"
                },
                "group": null,
                "resources": [
                    {
                        "group": "group1",
                        "version": "version1",
                        "plural": "plural1",
                        "verbs": []
                    }
                ],
                "report_warnings": true
            },
            "expected_output": "resources=\nwarnings=[a specific warning string for resources lacking watch capabilities]\n"
        },
        {
            "input": {
                "action": "refresh_resources",
                "handler_mode": "background_task",
                "selector": {
                    "group": "group1",
                    "version": "version1",
                    "plural": "plural1"
                },
                "group": null,
                "resources": [
                    {
                        "group": "group1",
                        "version": "version1",
                        "plural": "plural1",
                        "verbs": [
                            "watch",
                            "list"
                        ]
                    }
                ],
                "report_warnings": true
            },
            "expected_output": "resources=\nwarnings=non_patchable_resource\n"
        }
    ]
}
```

---

### Feature 4: Resource Definition Watch Event Processing

**As a developer**, I want resource-definition watch events to trigger API rediscovery, so served resources and core readiness follow the cluster API surface.

**Expected Behavior / Usage:**

A resource-definition event input contains `action=[a vague domain identifier mentioned in the PRD]ly_resource_definition_event`, an event type and affected API group, selectors, optional initial served resources, and mocked API discovery responses. Initial-list events are ignored: no notification, no API calls, and no resource updates. Follow-up addition, modification, or deletion events notify waiters and rediscover the affected API group through the discovery URLs shown in `api_calls`. If rediscovery returns resources, matching served resources are updated. If rediscovery returns an empty resource list or a not-found response for the group/version endpoint, previously served resources from that group are removed. When the affected group is the core API group, discovery also fills readiness for core namespaces, reported by `core_namespaces_ready=yes`. Stdout contains notification state, served resources, core namespace readiness, and the sorted discovery URLs actually called.

**Test Cases:** `rcb_tests/public_test_cases/feature4_resource_definition_event_processing.json`

```json
{
    "description": "Apply one resource-definition watch event, ignoring initial-list events, rescanning the affected API group for follow-up changes, updating served resources from API discovery, handling dis[a vague domain identifier mentioned in the PRD]eared groups as empty, and filling core backbone resources from core API discovery.",
    "cases": [
        {
            "input": {
                "action": "[a vague domain identifier mentioned in the PRD]ly_resource_definition_event",
                "handler_mode": "watch_event",
                "selector": {
                    "group": "group1",
                    "version": "version1",
                    "plural": "plural1"
                },
                "initial_resources": [],
                "event": {
                    "type": null,
                    "spec": {
                        "group": "group1"
                    }
                },
                "apis": {
                    "/apis": {
                        "body": {
                            "groups": [
                                {
                                    "name": "group1",
                                    "preferredVersion": {
                                        "version": "version1"
                                    },
                                    "versions": [
                                        {
                                            "version": "version1"
                                        }
                                    ]
                                }
                            ]
                        }
                    },
                    "/apis/group1/version1": {
                        "body": {
                            "resources": [
                                {
                                    "kind": "kind1",
                                    "name": "plural1",
                                    "singularName": "singular1",
                                    "namespaced": true,
                                    "categories": [
                                        "category1a",
                                        "category1b"
                                    ],
                                    "shortNames": [
                                        "shortname1a",
                                        "shortname1b"
                                    ],
                                    "verbs": [
                                        "list",
                                        "watch",
                                        "patch"
                                    ]
                                }
                            ]
                        }
                    }
                }
            },
            "expected_output": "notified=no\nresources=\ncore_namespaces_ready=no\napi_calls=\n"
        },
        {
            "input": {
                "action": "[a vague domain identifier mentioned in the PRD]ly_resource_definition_event",
                "handler_mode": "watch_event",
                "selector": {
                    "group": "group1",
                    "version": "version1",
                    "plural": "plural1"
                },
                "initial_resources": [],
                "event": {
                    "type": "ADDED",
                    "spec": {
                        "group": "group1"
                    }
                },
                "apis": {
                    "/apis": {
                        "body": {
                            "groups": [
                                {
                                    "name": "group1",
                                    "preferredVersion": {
                                        "version": "version1"
                                    },
                                    "versions": [
                                        {
                                            "version": "version1"
                                        }
                                    ]
                                }
                            ]
                        }
                    },
                    "/apis/group1/version1": {
                        "body": {
                            "resources": [
                                {
                                    "kind": "kind1",
                                    "name": "plural1",
                                    "singularName": "singular1",
                                    "namespaced": true,
                                    "categories": [
                                        "category1a",
                                        "category1b"
                                    ],
                                    "shortNames": [
                                        "shortname1a",
                                        "shortname1b"
                                    ],
                                    "verbs": [
                                        "list",
                                        "watch",
                                        "patch"
                                    ]
                                }
                            ]
                        }
                    }
                }
            },
            "expected_output": "notified=yes\nresources=group1/version1/plural1\ncore_namespaces_ready=no\napi_calls=/apis,/apis/group1/version1\n"
        },
        {
            "input": {
                "action": "[a vague domain identifier mentioned in the PRD]ly_resource_definition_event",
                "handler_mode": "watch_event",
                "selector": {
                    "group": "group1",
                    "version": "version1",
                    "plural": "plural1"
                },
                "initial_resources": [],
                "event": {
                    "type": "MODIFIED",
                    "spec": {
                        "group": "group1"
                    }
                },
                "apis": {
                    "/apis": {
                        "body": {
                            "groups": [
                                {
                                    "name": "group1",
                                    "preferredVersion": {
                                        "version": "version1"
                                    },
                                    "versions": [
                                        {
                                            "version": "version1"
                                        }
                                    ]
                                }
                            ]
                        }
                    },
                    "/apis/group1/version1": {
                        "body": {
                            "resources": [
                                {
                                    "kind": "kind1",
                                    "name": "plural1",
                                    "singularName": "singular1",
                                    "namespaced": true,
                                    "categories": [
                                        "category1a",
                                        "category1b"
                                    ],
                                    "shortNames": [
                                        "shortname1a",
                                        "shortname1b"
                                    ],
                                    "verbs": [
                                        "list",
                                        "watch",
                                        "patch"
                                    ]
                                }
                            ]
                        }
                    }
                }
            },
            "expected_output": "notified=yes\nresources=group1/version1/plural1\ncore_namespaces_ready=no\napi_calls=/apis,/apis/group1/version1\n"
        },
        {
            "input": {
                "action": "[a vague domain identifier mentioned in the PRD]ly_resource_definition_event",
                "handler_mode": "watch_event",
                "selector": {
                    "group": "group1",
                    "version": "version1",
                    "plural": "plural1"
                },
                "initial_resources": [
                    {
                        "group": "group1",
                        "version": "version1",
                        "plural": "plural1",
                        "kind": "kind1",
                        "singular": "singular1",
                        "namespaced": true,
                        "categories": [
                            "category1a",
                            "category1b"
                        ],
                        "shortcuts": [
                            "shortname1a",
                            "shortname1b"
                        ],
                        "verbs": [
                            "list",
                            "watch",
                            "patch"
                        ]
                    }
                ],
                "event": {
                    "type": "DELETED",
                    "spec": {
                        "group": "group1"
                    }
                },
                "apis": {
                    "/apis": {
                        "body": {
                            "groups": [
                                {
                                    "name": "group1",
                                    "preferredVersion": {
                                        "version": "version1"
                                    },
                                    "versions": [
                                        {
                                            "version": "version1"
                                        }
                                    ]
                                }
                            ]
                        }
                    },
                    "/apis/group1/version1": {
                        "body": {
                            "resources": []
                        }
                    }
                }
            },
            "expected_output": "notified=yes\nresources=\ncore_namespaces_ready=no\napi_calls=/apis,/apis/group1/version1\n"
        },
        {
            "input": {
                "action": "[a vague domain identifier mentioned in the PRD]ly_resource_definition_event",
                "handler_mode": "watch_event",
                "selector": {
                    "group": "group1",
                    "version": "version1",
                    "plural": "plural1"
                },
                "initial_resources": [
                    {
                        "group": "group1",
                        "version": "version1",
                        "plural": "plural1",
                        "kind": "kind1",
                        "singular": "singular1",
                        "namespaced": true,
                        "categories": [
                            "category1a",
                            "category1b"
                        ],
                        "shortcuts": [
                            "shortname1a",
                            "shortname1b"
                        ],
                        "verbs": [
                            "list",
                            "watch",
                            "patch"
                        ]
                    }
                ],
                "event": {
                    "type": "DELETED",
                    "spec": {
                        "group": "group1"
                    }
                },
                "apis": {
                    "/apis": {
                        "body": {
                            "groups": [
                                {
                                    "name": "group1",
                                    "preferredVersion": {
                                        "version": "version1"
                                    },
                                    "versions": [
                                        {
                                            "version": "version1"
                                        }
                                    ]
                                }
                            ]
                        }
                    },
                    "/apis/group1/version1": {
                        "status": 404
                    }
                }
            },
            "expected_output": "notified=yes\nresources=\ncore_namespaces_ready=no\napi_calls=/apis,/apis/group1/version1\n"
        },
        {
            "input": {
                "action": "[a vague domain identifier mentioned in the PRD]ly_resource_definition_event",
                "handler_mode": null,
                "selector": null,
                "initial_resources": [],
                "event": {
                    "type": "DELETED",
                    "spec": {
                        "group": ""
                    }
                },
                "apis": {
                    "/api": {
                        "body": {
                            "versions": [
                                "v1"
                            ]
                        }
                    },
                    "/api/v1": {
                        "body": {
                            "resources": [
                                {
                                    "kind": "Namespace",
                                    "name": "namespaces",
                                    "singularName": "namespace",
                                    "namespaced": false,
                                    "categories": [],
                                    "shortNames": [],
                                    "verbs": [
                                        "list",
                                        "watch",
                                        "patch"
                                    ]
                                }
                            ]
                        }
                    }
                }
            },
            "expected_output": "notified=yes\nresources=\ncore_namespaces_ready=yes\napi_calls=/api,/api/v1\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the [a vague domain identifier mentioned in the PRD]ropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the metadata extraction pattern from the namespace filter module
- use the sentinel value defined in the core group constants file
