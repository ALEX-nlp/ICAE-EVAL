## Product Requirement Document

# Container-Manager REST Client - Request Builder & Response Projector

## Project Goal

Build a client library for a container-manager daemon's HTTP REST API that allows developers to drive the daemon through small, typed method calls without hand-building request URLs, serializing request bodies, or parsing and validating raw HTTP responses by hand.

---

## Background & Problem

A container-manager daemon exposes its functionality over an HTTP REST API: hosts, networks, operations, containers, images, aliases, certificates and configuration profiles each live under their own URL space, are read with HTTP verbs, and return JSON documents wrapped in a standard envelope. Without a client library, every caller must assemble endpoint URLs by hand, remember which verb each action uses, serialize request payloads to JSON, and re-implement the same response-parsing and error-classification logic for every call.

With this library, the caller invokes a domain method (for example, "list networks" or "start this container"); the library builds the correct request (verb, URL, query string, body and headers), and projects the daemon's response into a convenient typed value -- a list of short resource names, a small summary object, a boolean, or a raw response pair -- while translating transport and daemon failures into a small set of well-defined error categories.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain. This is a multi-resource client and MUST NOT be a single "god file": separate the transport/response layer, the per-resource request builders and projectors, and the execution adapter into distinct units that reflect a production-grade repository.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core logic must be decoupled from standard I/O and JSON parsing; the adapter alone translates JSON commands into idiomatic calls.

3. **Adherence to SOLID Design Principles:** Separate transport, request building, response projection, validation and output formatting into cohesive units; depend on abstractions for the transport so the core is testable without real network I/O.

4. **Robustness & Interface Design:** The public interface must be idiomatic and hide transport details. Failures must be modeled as well-defined error categories rather than leaking host-language runtime artifacts.

### Wire & Output Contract (applies to every feature)

The execution adapter reads one JSON request from stdin and prints lines to stdout. A request names a neutral `op` (a `resource.verb` token), an optional `params` object with the operation's domain inputs, and an optional `response` object describing what the daemon transport yields for this call: `{"status": <state>, "document": <parsed body>}` for a document read, `{"ok": <bool>}` for a status probe, `{"raw": <string>}` for a raw read, or `{"error": {"kind": ...}}` to make the transport fail. For the transport-level features the request instead supplies the raw `status` and `body` directly under `params`.

The adapter prints, in order: one `request=<HTTP-METHOD> <URL>` line per outgoing daemon call; a `body=<...>` line when a request body was sent; one `header.<name>=<value>` line per request header sent (sorted by name); and then either `result=<canonical-json>` with the projected return value (objects rendered with sorted keys; the raw response pair rendered as a two-element `[state, document]` array) or, on failure, a normalized `error=<category>` line. Error categories are language-neutral: `api_error` (with a `status_code=<code>` line), `invalid_image_size`, `missing_field` (with a `field=<name>` line) and `daemon_error`. Each line ends with a newline.

---

## Core Features


### Feature 1: Host Environment Introspection

**As a developer**, I want to query the daemon for its environment so I can learn its capabilities and configuration.

**Expected Behavior / Usage:**

Each operation issues a single read request to the daemon root endpoint and projects the returned environment document into a small, typed view. The daemon document carries a `metadata` object describing the daemon (an API-compatibility integer, an authentication state, and an `environment` sub-object with the storage backend, the driver, kernel/runtime versions). The version number that names the daemon release is converted to a floating-point number; the trust state is converted to a boolean (`true` only when the authentication state equals `trusted`); all other fields are returned as-is.

*1.1 Aggregate host summary — Reads the daemon root and returns one combined object containing the API-compatibility level (integer), the trust flag (boolean, true only when authenticated as trusted), the storage backend, the driver, the daemon release as a floating-point number, the runtime version string, and the kernel version string. Exactly one read request is issued to the root endpoint.*

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_host_info.json`

```json
{
    "cases": [
        {
            "input": {
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": {
                            "environment": {
                                "kernel_version": "3.19.0-22-generic", 
                                "backing_fs": "ext4", 
                                "driver": "lxc", 
                                "lxc_version": "1.1.2", 
                                "lxd_version": "0.12"
                            }, 
                            "config": {}, 
                            "auth": "trusted", 
                            "api_compat": 1
                        }
                    }
                }, 
                "op": "host.info"
            }, 
            "expected_output": "request=GET /1.0\nresult={\"kernel_version\": \"3.19.0-22-generic\", \"lxc_version\": \"1.1.2\", \"lxd_api_compat_level\": 1, \"lxd_backing_fs\": \"ext4\", \"lxd_driver\": \"lxc\", \"lxd_trusted_host\": true, \"lxd_version\": 0.12}\n"
        }
    ], 
    "description": "Project the daemon root environment document into a single summary object holding the API compatibility level, host trust flag, backing filesystem, driver, daemon version (as a number), runtime version and kernel version."
}
```

*1.2 Individual environment fields — Each field accessor re-reads the daemon root (one request) and returns just that field. Supported fields: the API-compatibility level (integer), the trust flag (boolean), the backing filesystem, the driver, the runtime version (string), the daemon release (floating-point number) and the kernel version. The field to read is named by a neutral `field` selector.*

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_host_field.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "field": "api_compat"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": {
                            "environment": {
                                "kernel_version": "3.19.0-22-generic", 
                                "backing_fs": "ext4", 
                                "driver": "lxc", 
                                "lxc_version": "1.1.2", 
                                "lxd_version": "0.12"
                            }, 
                            "config": {}, 
                            "auth": "trusted", 
                            "api_compat": 1
                        }
                    }
                }, 
                "op": "host.field"
            }, 
            "expected_output": "request=GET /1.0\nresult=1\n"
        }, 
        {
            "input": {
                "params": {
                    "field": "lxd_version"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": {
                            "environment": {
                                "kernel_version": "3.19.0-22-generic", 
                                "backing_fs": "ext4", 
                                "driver": "lxc", 
                                "lxc_version": "1.1.2", 
                                "lxd_version": "0.12"
                            }, 
                            "config": {}, 
                            "auth": "trusted", 
                            "api_compat": 1
                        }
                    }
                }, 
                "op": "host.field"
            }, 
            "expected_output": "request=GET /1.0\nresult=0.12\n"
        }
    ], 
    "description": "Read a single named environment field from the daemon root; the daemon version field is returned as a floating-point number and the trust field as a boolean."
}
```

*1.3 Graceful handling when the daemon is unreachable — When the read request fails with a daemon error, a single-field accessor does not propagate the failure; it returns a null value instead (the request is still attempted exactly once).*

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_host_unavailable.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "field": "api_compat"
                }, 
                "response": {
                    "error": {
                        "kind": "daemon_error"
                    }
                }, 
                "op": "host.field"
            }, 
            "expected_output": "request=GET /1.0\nresult=null\n"
        }
    ], 
    "description": "When the daemon read fails, a single-field accessor swallows the error and yields a null result rather than raising."
}
```

---

### Feature 2: Network Inventory

**As a developer**, I want to enumerate and inspect the daemon's managed networks.

**Expected Behavior / Usage:**

The collection endpoint returns a `metadata` array of network resource URLs; only the trailing network name of each URL is kept. A single network document carries a `metadata` object with the network name, its type, and a `members` array of attached resource URLs (again reduced to their trailing names for membership).

*2.1 List networks — Reads the networks collection endpoint and returns the list of network names, each derived from the trailing segment of its resource URL.*

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_network_list.json`

```json
{
    "cases": [
        {
            "input": {
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": [
                            "/1.0/networks/lxcbr0"
                        ]
                    }
                }, 
                "op": "networks.list"
            }, 
            "expected_output": "request=GET /1.0/networks\nresult=[\"lxcbr0\"]\n"
        }
    ], 
    "description": "List managed networks, returning only the short name of each from its resource URL."
}
```

*2.2 Network summary — Reads a single network endpoint and returns a combined object with the network name, its type, and the list of member names (each member reduced to the trailing segment of its URL).*

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_network_show.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "network": "lxcbr0"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "OK", 
                        "status_code": 100, 
                        "operation": "/1.0/operation/1234", 
                        "type": "async", 
                        "metadata": {
                            "type": "bridge", 
                            "name": "lxcbr0", 
                            "members": [
                                "/1.0/containers/trusty-1"
                            ]
                        }
                    }
                }, 
                "op": "networks.show"
            }, 
            "expected_output": "request=GET /1.0/networks/lxcbr0\nresult={\"network_members\": [\"/1.0/containers/trusty-1\"], \"network_name\": \"lxcbr0\", \"network_type\": \"bridge\"}\n"
        }
    ], 
    "description": "Project a single network document into a summary with its name, type and member short-names."
}
```

*2.3 Individual network fields — Each accessor reads the network endpoint (one request) and returns a single field: the network name, the network type, or the members list (member URLs reduced to trailing names).*

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_network_field.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "field": "name", 
                    "network": "lxcbr0"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "OK", 
                        "status_code": 100, 
                        "operation": "/1.0/operation/1234", 
                        "type": "async", 
                        "metadata": {
                            "type": "bridge", 
                            "name": "lxcbr0", 
                            "members": [
                                "/1.0/containers/trusty-1"
                            ]
                        }
                    }
                }, 
                "op": "networks.field"
            }, 
            "expected_output": "request=GET /1.0/networks/lxcbr0\nresult=\"lxcbr0\"\n"
        }, 
        {
            "input": {
                "params": {
                    "field": "members", 
                    "network": "lxcbr0"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "OK", 
                        "status_code": 100, 
                        "operation": "/1.0/operation/1234", 
                        "type": "async", 
                        "metadata": {
                            "type": "bridge", 
                            "name": "lxcbr0", 
                            "members": [
                                "/1.0/containers/trusty-1"
                            ]
                        }
                    }
                }, 
                "op": "networks.field"
            }, 
            "expected_output": "request=GET /1.0/networks/lxcbr0\nresult=[\"/1.0/containers/trusty-1\"]\n"
        }
    ], 
    "description": "Read one named field (name, type or members) of a single network."
}
```

---

### Feature 3: Asynchronous Operations

**As a developer**, I want to track and control the daemon's long-running operations.

**Expected Behavior / Usage:**

The operations collection endpoint returns a `metadata` array of operation URLs (returned verbatim). A single operation document carries timestamps in ISO-8601 form and a status string under `metadata`; the timestamps are reformatted to `[a specific feature flag or input parameter that must be explicitly designed]`. Control actions (delete, wait) return a boolean success flag and the wait action encodes its target status code and timeout into the request URL query string.

*3.1 List operations — Reads the operations collection endpoint and returns the array of operation URLs unchanged.*

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_operation_list.json`

```json
{
    "cases": [
        {
            "input": {
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": [
                            "/1.0/operations/1234"
                        ]
                    }
                }, 
                "op": "operations.list"
            }, 
            "expected_output": "request=GET /1.0/operations\nresult=[\"/1.0/operations/1234\"]\n"
        }
    ], 
    "description": "List the daemon's current operation URLs."
}
```

*3.2 Fetch a raw operation — Reads a single operation endpoint and returns the raw response pair (the response state and the full operation document) without projection.*

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_operation_info.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "operation": "/1.0/operations/1234"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "OK", 
                        "status_code": 100, 
                        "operation": "/1.0/operation/1234", 
                        "type": "async", 
                        "metadata": {
                            "status": "Running", 
                            "status_code": 103, 
                            "created_at": "2015-06-09T19:07:24.379615253-06:00", 
                            "updated_at": "2015-06-09T19:07:23.379615253-06:00", 
                            "may_cancel": true, 
                            "resources": {
                                "containers": [
                                    "/1.0/containers/1"
                                ]
                            }, 
                            "metadata": {}
                        }
                    }
                }, 
                "op": "operations.info"
            }, 
            "expected_output": "request=GET /1.0/operations/1234\nresult=[\"200\", {\"metadata\": {\"created_at\": \"2015-06-09T19:07:24.379615253-06:00\", \"may_cancel\": true, \"metadata\": {}, \"resources\": {\"containers\": [\"/1.0/containers/1\"]}, \"status\": \"Running\", \"status_code\": 103, \"updated_at\": \"2015-06-09T19:07:23.379615253-06:00\"}, \"operation\": \"/1.0/operation/1234\", \"status\": \"OK\", \"status_code\": 100, \"type\": \"async\"}]\n"
        }
    ], 
    "description": "Fetch a single operation and return the raw state/document pair."
}
```

*3.3 Operation timestamps and status — Each accessor reads the operation endpoint and returns one field: the creation time or update time (each reformatted from ISO-8601 to `[a specific feature flag or input parameter that must be explicitly designed]`), or the operation status string.*

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_operation_fields.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "operation": "/1.0/operations/1234"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "OK", 
                        "status_code": 100, 
                        "operation": "/1.0/operation/1234", 
                        "type": "async", 
                        "metadata": {
                            "status": "Running", 
                            "status_code": 103, 
                            "created_at": "2015-06-09T19:07:24.379615253-06:00", 
                            "updated_at": "2015-06-09T19:07:23.379615253-06:00", 
                            "may_cancel": true, 
                            "resources": {
                                "containers": [
                                    "/1.0/containers/1"
                                ]
                            }, 
                            "metadata": {}
                        }
                    }
                }, 
                "op": "[a specific feature flag or input parameter that must be explicitly designed]"
            }, 
            "expected_output": "request=GET /1.0/operations/1234\nresult=\"2015-06-09 19:07:24\"\n"
        }, 
        {
            "input": {
                "params": {
                    "operation": "/1.0/operations/1234"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "OK", 
                        "status_code": 100, 
                        "operation": "/1.0/operation/1234", 
                        "type": "async", 
                        "metadata": {
                            "status": "Running", 
                            "status_code": 103, 
                            "created_at": "2015-06-09T19:07:24.379615253-06:00", 
                            "updated_at": "2015-06-09T19:07:23.379615253-06:00", 
                            "may_cancel": true, 
                            "resources": {
                                "containers": [
                                    "/1.0/containers/1"
                                ]
                            }, 
                            "metadata": {}
                        }
                    }
                }, 
                "op": "[a specific feature flag or input parameter that must be explicitly designed]"
            }, 
            "expected_output": "request=GET /1.0/operations/1234\nresult=\"Running\"\n"
        }
    ], 
    "description": "Read one projected field of an operation: a reformatted create/update timestamp, or the status string."
}
```

*3.4 Delete and wait — The delete action issues a delete request to the operation URL and returns a boolean success flag. The wait action issues a read to the operation URL with `/wait?status_code=<code>&timeout=<seconds>` appended and returns a boolean success flag.*

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_operation_actions.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "operation": "/1.0/operations/1234"
                }, 
                "response": {
                    "status": "200", 
                    "document": null
                }, 
                "op": "operations.delete"
            }, 
            "expected_output": "request=DELETE /1.0/operations/1234\nresult=true\n"
        }, 
        {
            "input": {
                "params": {
                    "status_code": "200", 
                    "operation": "/1.0/operations/1234", 
                    "timeout": "30"
                }, 
                "response": {
                    "status": "200", 
                    "document": null
                }, 
                "op": "operations.wait"
            }, 
            "expected_output": "request=GET /1.0/operations/1234/wait?status_code=200&timeout=30\nresult=true\n"
        }
    ], 
    "description": "Delete an operation, or wait on it until a target status code or timeout; both return a boolean success flag, and wait encodes its parameters into the request URL."
}
```

---

### Feature 4: Container Management

**As a developer**, I want to create, inspect, control and snapshot containers.

**Expected Behavior / Usage:**

Container operations target the containers endpoint and its sub-resources. Collection reads reduce resource URLs to short names. Lifecycle actions send a state-change document (an action verb, a force flag, and a timeout) as the request body. Bodies derived from caller-supplied values are serialized as JSON. State-change and creation calls return the raw response pair; projection accessors extract specific metadata. Existence checks return a boolean.

*4.1 List containers — Reads the containers collection endpoint and returns container short names from their resource URLs.*

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_container_list.json`

```json
{
    "cases": [
        {
            "input": {
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": [
                            "/1.0/containers/trusty-1"
                        ]
                    }
                }, 
                "op": "containers.list"
            }, 
            "expected_output": "request=GET /1.0/containers\nresult=[\"trusty-1\"]\n"
        }
    ], 
    "description": "List containers by short name."
}
```

*4.2 Running-state predicate — Reads a container's state endpoint and returns a boolean: true when the reported status is one of the active states (running, starting, freezing, frozen, thawed) and false otherwise (e.g. stopped, stopping, aborting).*

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_container_running.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "container": "trusty-1"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": {
                            "status": "STOPPED"
                        }
                    }
                }, 
                "op": "containers.running"
            }, 
            "expected_output": "request=GET /1.0/containers/trusty-1/state\nresult=false\n"
        }, 
        {
            "input": {
                "params": {
                    "container": "trusty-1"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": {
                            "status": "RUNNING"
                        }
                    }
                }, 
                "op": "containers.running"
            }, 
            "expected_output": "request=GET /1.0/containers/trusty-1/state\nresult=true\n"
        }
    ], 
    "description": "Decide whether a container is in an active state from its reported status string."
}
```

*4.3 Lifecycle actions — Each lifecycle action sends a state-change request to the container's state endpoint with a JSON body of `{action, force, timeout}` and returns the raw response pair. The action verb is: start, stop, freeze (suspend), unfreeze (resume) or restart (reboot); the force flag is always true and the timeout is the caller's value.*

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_container_lifecycle.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "action": "start", 
                    "container": "trusty-1", 
                    "timeout": 30
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": {}
                    }
                }, 
                "op": "containers.action"
            }, 
            "expected_output": "request=PUT /1.0/containers/trusty-1/state\nbody={\"action\": \"start\", \"force\": true, \"timeout\": 30}\nresult=[\"200\", {\"metadata\": {}, \"status\": \"Success\", \"status_code\": 200, \"type\": \"sync\"}]\n"
        }, 
        {
            "input": {
                "params": {
                    "action": "stop", 
                    "container": "trusty-1", 
                    "timeout": 30
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": {}
                    }
                }, 
                "op": "containers.action"
            }, 
            "expected_output": "request=PUT /1.0/containers/trusty-1/state\nbody={\"action\": \"stop\", \"force\": true, \"timeout\": 30}\nresult=[\"200\", {\"metadata\": {}, \"status\": \"Success\", \"status_code\": 200, \"type\": \"sync\"}]\n"
        }
    ], 
    "description": "Drive a container lifecycle transition; the request body carries the action verb, a force flag and a timeout."
}
```

*4.4 Create, update, destroy, fetch state — Create sends a creation request to the collection endpoint with the JSON-serialized spec as body. Update sends a replace request to the container endpoint with the JSON-serialized config as body. Destroy sends a delete request to the container endpoint. Fetch-state reads the container state endpoint. All four return the raw response pair.*

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_container_crud.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "spec": "fake"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": {}
                    }
                }, 
                "op": "containers.init"
            }, 
            "expected_output": "request=POST /1.0/containers\nbody=\"fake\"\nresult=[\"200\", {\"metadata\": {}, \"status\": \"Success\", \"status_code\": 200, \"type\": \"sync\"}]\n"
        }, 
        {
            "input": {
                "params": {
                    "container": "trusty-1"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": {}
                    }
                }, 
                "op": "containers.destroy"
            }, 
            "expected_output": "request=DELETE /1.0/containers/trusty-1\nresult=[\"200\", {\"metadata\": {}, \"status\": \"Success\", \"status_code\": 200, \"type\": \"sync\"}]\n"
        }
    ], 
    "description": "Create, replace, destroy or read a container; the supplied spec/config is sent as a JSON body."
}
```

*4.5 Metadata views — Info reads the state endpoint and returns its metadata object. Log reads the container endpoint with `?log=true` and returns the metadata log string. Config reads the container endpoint with `?log=false` and returns the metadata object.*

**Test Cases:** `rcb_tests/public_test_cases/feature4_5_container_views.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "container": "trusty-1"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": {
                            "status": "fake"
                        }
                    }
                }, 
                "op": "containers.info"
            }, 
            "expected_output": "request=GET /1.0/containers/trusty-1/state\nresult={\"status\": \"fake\"}\n"
        }, 
        {
            "input": {
                "params": {
                    "container": "trusty-1"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": {
                            "log": "fake log"
                        }
                    }
                }, 
                "op": "containers.log"
            }, 
            "expected_output": "request=GET /1.0/containers/trusty-1?log=true\nresult=\"fake log\"\n"
        }
    ], 
    "description": "Read a container's state metadata, its log text, or its full config metadata; the request URL carries the appropriate log query flag."
}
```

*4.6 Begin migration — Sends a migration request to the container endpoint with body `{"migration": true}`, then returns the operation's metadata merged with an `operation` key holding the short operation id taken from the trailing segment of the response operation URL.*

**Test Cases:** `rcb_tests/public_test_cases/feature4_6_container_migrate.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "container": "trusty-1"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "operation": "/1.0/operations/1234", 
                        "type": "sync", 
                        "metadata": {
                            "control": "fake_control", 
                            "criu": "fake_criu", 
                            "fs": "fake_fs"
                        }
                    }
                }, 
                "op": "containers.migrate"
            }, 
            "expected_output": "request=POST /1.0/containers/trusty-1\nbody={\"migration\": true}\nresult={\"control\": \"fake_control\", \"criu\": \"fake_criu\", \"fs\": \"fake_fs\", \"operation\": \"1234\"}\n"
        }
    ], 
    "description": "Initiate a container migration and return the migration metadata plus the short operation id."
}
```

*4.7 Existence check — Reads the container state endpoint and returns a boolean indicating whether the container is defined.*

**Test Cases:** `rcb_tests/public_test_cases/feature4_7_container_defined.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "container": "trusty-1"
                }, 
                "response": {
                    "ok": true
                }, 
                "op": "containers.defined"
            }, 
            "expected_output": "request=GET /1.0/containers/trusty-1/state\nresult=true\n"
        }, 
        {
            "input": {
                "params": {
                    "container": "trusty-1"
                }, 
                "response": {
                    "ok": false
                }, 
                "op": "containers.defined"
            }, 
            "expected_output": "request=GET /1.0/containers/trusty-1/state\nresult=false\n"
        }
    ], 
    "description": "Check whether a container exists, returning a boolean."
}
```

*4.8 Publish as image — Sends a creation request to the images endpoint with the JSON-serialized container reference as body and returns the raw response pair.*

**Test Cases:** `rcb_tests/public_test_cases/feature4_8_container_publish.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "container": "trusty-1"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "OK", 
                        "status_code": 100, 
                        "operation": "/1.0/operation/1234", 
                        "type": "async", 
                        "metadata": {
                            "status": "Running", 
                            "status_code": 103, 
                            "created_at": "2015-06-09T19:07:24.379615253-06:00", 
                            "updated_at": "2015-06-09T19:07:23.379615253-06:00", 
                            "may_cancel": true, 
                            "resources": {
                                "containers": [
                                    "/1.0/containers/1"
                                ]
                            }, 
                            "metadata": {}
                        }
                    }
                }, 
                "op": "containers.publish"
            }, 
            "expected_output": "request=POST /1.0/images\nbody=\"trusty-1\"\nresult=[\"200\", {\"metadata\": {\"created_at\": \"2015-06-09T19:07:24.379615253-06:00\", \"may_cancel\": true, \"metadata\": {}, \"resources\": {\"containers\": [\"/1.0/containers/1\"]}, \"status\": \"Running\", \"status_code\": 103, \"updated_at\": \"2015-06-09T19:07:23.379615253-06:00\"}, \"operation\": \"/1.0/operation/1234\", \"status\": \"OK\", \"status_code\": 100, \"type\": \"async\"}]\n"
        }
    ], 
    "description": "Publish a container as a new image; the container reference is sent as a JSON body."
}
```

*4.9 List snapshots — Reads a container's snapshots endpoint and returns the snapshot URL list.*

**Test Cases:** `rcb_tests/public_test_cases/feature4_9_snapshot_list.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "container": "trusty-1"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": [
                            "/1.0/containers/trusty-1/snapshots/first"
                        ]
                    }
                }, 
                "op": "containers.snapshots.list"
            }, 
            "expected_output": "request=GET /1.0/containers/trusty-1/snapshots\nresult=[\"/1.0/containers/trusty-1/snapshots/first\"]\n"
        }
    ], 
    "description": "List a container's snapshots."
}
```

*4.10 Snapshot create/info/rename/delete — Create sends a creation request to the snapshots endpoint with the JSON config body. Info reads a single snapshot endpoint. Rename sends a creation request to the snapshot endpoint with the JSON config body. Delete sends a delete request to the snapshot endpoint. All return the raw response pair.*

**Test Cases:** `rcb_tests/public_test_cases/feature4_10_snapshot_ops.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "action": "create", 
                    "config": "fake config", 
                    "container": "trusty-1"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "OK", 
                        "status_code": 100, 
                        "operation": "/1.0/operation/1234", 
                        "type": "async", 
                        "metadata": {
                            "status": "Running", 
                            "status_code": 103, 
                            "created_at": "2015-06-09T19:07:24.379615253-06:00", 
                            "updated_at": "2015-06-09T19:07:23.379615253-06:00", 
                            "may_cancel": true, 
                            "resources": {
                                "containers": [
                                    "/1.0/containers/1"
                                ]
                            }, 
                            "metadata": {}
                        }
                    }
                }, 
                "op": "containers.snapshots.op"
            }, 
            "expected_output": "request=POST /1.0/containers/trusty-1/snapshots\nbody=\"fake config\"\nresult=[\"200\", {\"metadata\": {\"created_at\": \"2015-06-09T19:07:24.379615253-06:00\", \"may_cancel\": true, \"metadata\": {}, \"resources\": {\"containers\": [\"/1.0/containers/1\"]}, \"status\": \"Running\", \"status_code\": 103, \"updated_at\": \"2015-06-09T19:07:23.379615253-06:00\"}, \"operation\": \"/1.0/operation/1234\", \"status\": \"OK\", \"status_code\": 100, \"type\": \"async\"}]\n"
        }, 
        {
            "input": {
                "params": {
                    "action": "info", 
                    "snapshot": "first", 
                    "container": "trusty-1"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "OK", 
                        "status_code": 100, 
                        "operation": "/1.0/operation/1234", 
                        "type": "async", 
                        "metadata": {
                            "status": "Running", 
                            "status_code": 103, 
                            "created_at": "2015-06-09T19:07:24.379615253-06:00", 
                            "updated_at": "2015-06-09T19:07:23.379615253-06:00", 
                            "may_cancel": true, 
                            "resources": {
                                "containers": [
                                    "/1.0/containers/1"
                                ]
                            }, 
                            "metadata": {}
                        }
                    }
                }, 
                "op": "containers.snapshots.op"
            }, 
            "expected_output": "request=GET /1.0/containers/trusty-1/snapshots/first\nresult=[\"200\", {\"metadata\": {\"created_at\": \"2015-06-09T19:07:24.379615253-06:00\", \"may_cancel\": true, \"metadata\": {}, \"resources\": {\"containers\": [\"/1.0/containers/1\"]}, \"status\": \"Running\", \"status_code\": 103, \"updated_at\": \"2015-06-09T19:07:23.379615253-06:00\"}, \"operation\": \"/1.0/operation/1234\", \"status\": \"OK\", \"status_code\": 100, \"type\": \"async\"}]\n"
        }
    ], 
    "description": "Create, read, rename or delete a container snapshot; config payloads are sent as JSON bodies."
}
```

*4.11 Read a file — Reads the container files endpoint with `?path=<path>` appended and returns the raw file contents.*

**Test Cases:** `rcb_tests/public_test_cases/feature4_11_container_file_get.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "path": "/file/name", 
                    "container": "trusty-1"
                }, 
                "response": {
                    "raw": "fake contents"
                }, 
                "op": "containers.file.get"
            }, 
            "expected_output": "request=GET /1.0/containers/trusty-1/files?path=/file/name\nresult=\"fake contents\"\n"
        }
    ], 
    "description": "Read a file out of a container; the path is carried in the request URL query string."
}
```

*4.12 Write a file — Sends a creation request to the container files endpoint with `?path=<dst>` appended, the file bytes as the request body, and three headers carrying the owner uid, group gid and file mode. Returns the raw response pair.*

**Test Cases:** `rcb_tests/public_test_cases/feature4_12_container_file_put.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "container": "trusty-1", 
                    "uid": 0, 
                    "dst": "dst_file", 
                    "gid": 0, 
                    "mode": 420, 
                    "src_content": ""
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": {}
                    }
                }, 
                "op": "containers.file.put"
            }, 
            "expected_output": "request=POST /1.0/containers/trusty-1/files?path=dst_file\nbody=\nheader.X-LXD-gid=0\nheader.X-LXD-mode=420\nheader.X-LXD-uid=0\nresult=[\"200\", {\"metadata\": {}, \"status\": \"Success\", \"status_code\": 200, \"type\": \"sync\"}]\n"
        }
    ], 
    "description": "Write a file into a container; the destination path is in the URL, the file bytes are the body, and uid/gid/mode are sent as headers."
}
```

*4.13 Run a command — Sends a creation request to the container exec endpoint with a JSON body of `{command, interactive, wait-for-websocket, environment}` and returns the raw response pair.*

**Test Cases:** `rcb_tests/public_test_cases/feature4_13_container_exec.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "web_sockets": false, 
                    "args": [
                        "/fake/command"
                    ], 
                    "container": "trusty-1", 
                    "env": {
                        "FAKE_ENV": "fake"
                    }, 
                    "interactive": false
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "OK", 
                        "status_code": 100, 
                        "operation": "/1.0/operation/1234", 
                        "type": "async", 
                        "metadata": {
                            "status": "Running", 
                            "status_code": 103, 
                            "created_at": "2015-06-09T19:07:24.379615253-06:00", 
                            "updated_at": "2015-06-09T19:07:23.379615253-06:00", 
                            "may_cancel": true, 
                            "resources": {
                                "containers": [
                                    "/1.0/containers/1"
                                ]
                            }, 
                            "metadata": {}
                        }
                    }
                }, 
                "op": "containers.exec"
            }, 
            "expected_output": "request=POST /1.0/containers/trusty-1/exec\nbody={\"environment\": {\"FAKE_ENV\": \"fake\"}, \"command\": [\"/fake/command\"], \"wait-for-websocket\": false, \"interactive\": false}\nresult=[\"200\", {\"metadata\": {\"created_at\": \"2015-06-09T19:07:24.379615253-06:00\", \"may_cancel\": true, \"metadata\": {}, \"resources\": {\"containers\": [\"/1.0/containers/1\"]}, \"status\": \"Running\", \"status_code\": 103, \"updated_at\": \"2015-06-09T19:07:23.379615253-06:00\"}, \"operation\": \"/1.0/operation/1234\", \"status\": \"OK\", \"status_code\": 100, \"type\": \"async\"}]\n"
        }
    ], 
    "description": "Execute a command in a container; the command, interactivity flags and environment are sent as a JSON body."
}
```

---

### Feature 5: Image Catalog

**As a developer**, I want to list, inspect and manage stored images.

**Expected Behavior / Usage:**

Image reads target the images endpoint. Collection reads reduce resource URLs to short fingerprints/names. A single image document carries timestamps (epoch seconds; zero means unknown), a public flag, a size in bytes, a fingerprint and a numeric architecture code mapped to an architecture name. Field accessors may be given the metadata directly (no request) or fetch it themselves. Mutating operations return a boolean success flag.

*5.1 List and search images — List reads the images collection endpoint and returns image short fingerprints. Search reads the same endpoint with the caller's query parameters URL-encoded into a query string sent alongside the request, and returns the matching short fingerprints.*

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_image_list.json`

```json
{
    "cases": [
        {
            "input": {
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": [
                            "/1.0/images/trusty"
                        ]
                    }
                }, 
                "op": "images.list"
            }, 
            "expected_output": "request=GET /1.0/images\nresult=[\"trusty\"]\n"
        }, 
        {
            "input": {
                "params": {
                    "query": {
                        "foo": "bar"
                    }
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": [
                            "/1.0/images/trusty"
                        ]
                    }
                }, 
                "op": "images.search"
            }, 
            "expected_output": "request=GET /1.0/images\nbody=foo=bar\nresult=[\"trusty\"]\n"
        }
    ], 
    "description": "List images, or search them with URL-encoded query parameters; both return short fingerprints."
}
```

*5.2 Existence check — Reads a single image endpoint. Returns true when the image exists; returns false when the daemon reports a not-found (status 404) error; re-raises (normalized) for any other daemon error or status code.*

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_image_defined.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "image": "test-image"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": {
                            "size": 67043148, 
                            "public": 0, 
                            "uploaded_at": 1435669853, 
                            "architecture": 2, 
                            "fingerprint": "04aac4257341478b49c25d22cea8a6ce0489dc6c42d835367945e7596368a37f", 
                            "created_at": 0, 
                            "filename": "", 
                            "properties": {}, 
                            "expires_at": 0, 
                            "aliases": [
                                {
                                    "target": "ubuntu", 
                                    "description": "ubuntu"
                                }
                            ]
                        }
                    }
                }, 
                "op": "images.defined"
            }, 
            "expected_output": "request=GET /1.0/images/test-image\nresult=true\n"
        }, 
        {
            "input": {
                "params": {
                    "image": "test-image"
                }, 
                "response": {
                    "error": {
                        "status_code": 404, 
                        "kind": "api_error", 
                        "detail": "not found"
                    }
                }, 
                "op": "images.defined"
            }, 
            "expected_output": "request=GET /1.0/images/test-image\nresult=false\n"
        }
    ], 
    "description": "Check whether an image exists: true if found, false on a 404, and a normalized error for any other failure."
}
```

*5.3 Aggregate image summary — Reads a single image endpoint and returns a summary object: upload/create/expire dates (each an epoch second reformatted to `[a specific feature flag or input parameter that must be explicitly designed]`, or the literal `Unknown` when the stored value is zero), a public boolean, a size string suffixed with `MB` (bytes divided down to whole megabytes), the fingerprint, and the architecture name.*

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_image_info.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "image": "test-image"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": {
                            "size": 67043148, 
                            "public": 0, 
                            "uploaded_at": 1435669853, 
                            "architecture": 2, 
                            "fingerprint": "04aac4257341478b49c25d22cea8a6ce0489dc6c42d835367945e7596368a37f", 
                            "created_at": 0, 
                            "filename": "", 
                            "properties": {}, 
                            "expires_at": 0, 
                            "aliases": [
                                {
                                    "target": "ubuntu", 
                                    "description": "ubuntu"
                                }
                            ]
                        }
                    }
                }, 
                "op": "images.info"
            }, 
            "expected_output": "request=GET /1.0/images/test-image\nresult={\"image_architecture\": \"x86_64\", \"image_created_date\": \"Unknown\", \"image_expires_date\": \"Unknown\", \"image_fingerprint\": \"04aac4257341478b49c25d22cea8a6ce0489dc6c42d835367945e7596368a37f\", \"image_public\": false, \"image_size\": \"63MB\", \"image_upload_date\": \"2015-06-30 13:10:53\"}\n"
        }
    ], 
    "description": "Project an image document into a summary of dates, public flag, size in MB, fingerprint and architecture name."
}
```

*5.4 Date fields — Each date accessor (upload, create, expire) reads the image metadata (fetching it when not provided) and returns the chosen timestamp reformatted to `[a specific feature flag or input parameter that must be explicitly designed]`, or the literal `Unknown` when the stored epoch value is zero.*

**Test Cases:** `rcb_tests/public_test_cases/feature5_4_image_dates.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "image": "test-image", 
                    "key": "uploaded_at"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": {
                            "size": 67043148, 
                            "public": 0, 
                            "uploaded_at": 1435669853, 
                            "architecture": 2, 
                            "fingerprint": "04aac4257341478b49c25d22cea8a6ce0489dc6c42d835367945e7596368a37f", 
                            "created_at": 0, 
                            "filename": "", 
                            "properties": {}, 
                            "expires_at": 0, 
                            "aliases": [
                                {
                                    "target": "ubuntu", 
                                    "description": "ubuntu"
                                }
                            ]
                        }
                    }
                }, 
                "op": "images.date"
            }, 
            "expected_output": "request=GET /1.0/images/test-image\nresult=\"2015-06-30 13:10:53\"\n"
        }, 
        {
            "input": {
                "params": {
                    "image": "test-image", 
                    "key": "created_at"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": {
                            "size": 67043148, 
                            "public": 0, 
                            "uploaded_at": 1435669853, 
                            "architecture": 2, 
                            "fingerprint": "04aac4257341478b49c25d22cea8a6ce0489dc6c42d835367945e7596368a37f", 
                            "created_at": 0, 
                            "filename": "", 
                            "properties": {}, 
                            "expires_at": 0, 
                            "aliases": [
                                {
                                    "target": "ubuntu", 
                                    "description": "ubuntu"
                                }
                            ]
                        }
                    }
                }, 
                "op": "images.date"
            }, 
            "expected_output": "request=GET /1.0/images/test-image\nresult=\"Unknown\"\n"
        }
    ], 
    "description": "Read a single image date (upload/create/expire), reformatting non-zero epoch values and reporting zero as Unknown."
}
```

*5.5 Scalar fields and validation — Field accessors (public flag, size, fingerprint, architecture) return the projected value. When metadata is supplied directly no request is issued; otherwise the metadata is fetched first. The public flag is a boolean (true only when the stored flag equals 1). The size is whole megabytes (bytes divided down); a non-positive byte size is rejected as an invalid-size error. The architecture is the name mapped from the numeric code; an unknown code is a missing-field error. A missing required key is a missing-field error naming the absent key.*

**Test Cases:** `rcb_tests/public_test_cases/feature5_5_image_fields.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "field": "permission", 
                    "image": "test-image"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": {
                            "size": 67043148, 
                            "public": 0, 
                            "uploaded_at": 1435669853, 
                            "architecture": 2, 
                            "fingerprint": "04aac4257341478b49c25d22cea8a6ce0489dc6c42d835367945e7596368a37f", 
                            "created_at": 0, 
                            "filename": "", 
                            "properties": {}, 
                            "expires_at": 0, 
                            "aliases": [
                                {
                                    "target": "ubuntu", 
                                    "description": "ubuntu"
                                }
                            ]
                        }
                    }
                }, 
                "op": "images.field"
            }, 
            "expected_output": "request=GET /1.0/images/test-image\nresult=false\n"
        }, 
        {
            "input": {
                "params": {
                    "field": "size", 
                    "image": "test-image", 
                    "data": {
                        "size": 52428800
                    }
                }, 
                "op": "images.field"
            }, 
            "expected_output": "result=50\n"
        }, 
        {
            "input": {
                "params": {
                    "field": "size", 
                    "image": "test-image", 
                    "data": {
                        "size": 0
                    }
                }, 
                "op": "images.field"
            }, 
            "expected_output": "error=invalid_image_size\n"
        }
    ], 
    "description": "Project a scalar image field (public/size/fingerprint/architecture), fetching metadata when not supplied, and report invalid-size or missing-field errors for bad input."
}
```

*5.6 Delete, update, rename — Delete sends a delete request to the image endpoint. Update sends a replace request to the image endpoint with the JSON-serialized data body. Rename sends a creation request to the image endpoint with the JSON-serialized data body. All three return a boolean success flag.*

**Test Cases:** `rcb_tests/public_test_cases/feature5_6_image_ops.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "image": "test-image"
                }, 
                "response": {
                    "ok": true
                }, 
                "op": "images.delete"
            }, 
            "expected_output": "request=DELETE /1.0/images/test-image\nresult=true\n"
        }, 
        {
            "input": {
                "params": {
                    "image": "test-image", 
                    "data": "fake"
                }, 
                "response": {
                    "ok": true
                }, 
                "op": "images.update"
            }, 
            "expected_output": "request=PUT /1.0/images/test-image\nbody=\"fake\"\nresult=true\n"
        }
    ], 
    "description": "Delete, replace or rename an image; payloads are sent as JSON bodies and the result is a boolean flag."
}
```

*5.7 Export image bytes — Reads the image export endpoint and returns the raw exported bytes.*

**Test Cases:** `rcb_tests/public_test_cases/feature5_7_image_export.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "image": "fake"
                }, 
                "response": {
                    "raw": "fake contents"
                }, 
                "op": "images.export"
            }, 
            "expected_output": "request=GET /1.0/images/fake/export\nresult=\"fake contents\"\n"
        }
    ], 
    "description": "Export an image, returning its raw bytes."
}
```

*5.8 Upload image bytes — Sends a creation request to the images endpoint with the supplied bytes as body and returns the raw response pair.*

**Test Cases:** `rcb_tests/public_test_cases/feature5_8_image_upload.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "data": "fake"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": {
                            "size": 67043148, 
                            "public": 0, 
                            "uploaded_at": 1435669853, 
                            "architecture": 2, 
                            "fingerprint": "04aac4257341478b49c25d22cea8a6ce0489dc6c42d835367945e7596368a37f", 
                            "created_at": 0, 
                            "filename": "", 
                            "properties": {}, 
                            "expires_at": 0, 
                            "aliases": [
                                {
                                    "target": "ubuntu", 
                                    "description": "ubuntu"
                                }
                            ]
                        }
                    }
                }, 
                "op": "images.upload"
            }, 
            "expected_output": "request=POST /1.0/images\nbody=fake\nresult=[\"200\", {\"metadata\": {\"aliases\": [{\"description\": \"ubuntu\", \"target\": \"ubuntu\"}], \"architecture\": 2, \"created_at\": 0, \"expires_at\": 0, \"filename\": \"\", \"fingerprint\": \"04aac4257341478b49c25d22cea8a6ce0489dc6c42d835367945e7596368a37f\", \"properties\": {}, \"public\": 0, \"size\": 67043148, \"uploaded_at\": 1435669853}, \"status\": \"Success\", \"status_code\": 200, \"type\": \"sync\"}]\n"
        }
    ], 
    "description": "Upload image bytes to the catalog."
}
```

---

### Feature 6: Image Aliases

**As a developer**, I want to manage human-friendly aliases that point at images.

**Expected Behavior / Usage:**

Alias operations target the image aliases endpoint. Listing reduces alias URLs to short names; a single alias is fetched as a raw response pair. Existence checks and mutations return a boolean success flag, and payloads are JSON-serialized into the request body.

*6.1 List and fetch aliases — List reads the aliases endpoint and returns alias short names. Fetch reads a single alias endpoint and returns the raw response pair.*

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_alias_list.json`

```json
{
    "cases": [
        {
            "input": {
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": [
                            "/1.0/images/aliases/ubuntu"
                        ]
                    }
                }, 
                "op": "aliases.list"
            }, 
            "expected_output": "request=GET /1.0/images/aliases\nresult=[\"ubuntu\"]\n"
        }, 
        {
            "input": {
                "params": {
                    "alias": "fake"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": {
                            "target": "ubuntu", 
                            "description": "ubuntu"
                        }
                    }
                }, 
                "op": "aliases.show"
            }, 
            "expected_output": "request=GET /1.0/images/aliases/fake\nresult=[\"200\", {\"metadata\": {\"description\": \"ubuntu\", \"target\": \"ubuntu\"}, \"status\": \"Success\", \"status_code\": 200, \"type\": \"sync\"}]\n"
        }
    ], 
    "description": "List aliases by short name, or fetch a single alias as a raw response pair."
}
```

*6.2 Existence check — Reads a single alias endpoint and returns a boolean indicating whether the alias is defined.*

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_alias_defined.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "alias": "fake"
                }, 
                "response": {
                    "ok": true
                }, 
                "op": "aliases.defined"
            }, 
            "expected_output": "request=GET /1.0/images/aliases/fake\nresult=true\n"
        }, 
        {
            "input": {
                "params": {
                    "alias": "fake"
                }, 
                "response": {
                    "ok": false
                }, 
                "op": "aliases.defined"
            }, 
            "expected_output": "request=GET /1.0/images/aliases/fake\nresult=false\n"
        }
    ], 
    "description": "Check whether an alias exists, returning a boolean."
}
```

*6.3 Create, update, rename, delete — Create sends a creation request to the aliases endpoint with a JSON body. Update sends a replace request to a single alias endpoint with a JSON body. Rename sends a creation request to a single alias endpoint with a JSON body. Delete sends a delete request to a single alias endpoint. All return a boolean success flag.*

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_alias_ops.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "data": "fake"
                }, 
                "response": {
                    "ok": true
                }, 
                "op": "aliases.create"
            }, 
            "expected_output": "request=POST /1.0/images/aliases\nbody=\"fake\"\nresult=true\n"
        }, 
        {
            "input": {
                "params": {
                    "alias": "test-alias", 
                    "data": "fake"
                }, 
                "response": {
                    "ok": true
                }, 
                "op": "aliases.update"
            }, 
            "expected_output": "request=PUT /1.0/images/aliases/test-alias\nbody=\"fake\"\nresult=true\n"
        }
    ], 
    "description": "Create, update, rename or delete an alias; payloads are JSON bodies and the result is a boolean flag."
}
```

---

### Feature 7: Trusted Certificates

**As a developer**, I want to list and manage the daemon's trusted client certificates.

**Expected Behavior / Usage:**

Certificate operations target the certificates endpoint. Listing reduces certificate URLs to short fingerprints; a single certificate is fetched as a raw response pair. Mutations return a boolean success flag, and the create payload is JSON-serialized into the body.

*7.1 List and fetch certificates — List reads the certificates endpoint and returns certificate short fingerprints. Fetch reads a single certificate endpoint and returns the raw response pair.*

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_certificate_list.json`

```json
{
    "cases": [
        {
            "input": {
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": [
                            "/1.0/certificates/ABCDEF01"
                        ]
                    }
                }, 
                "op": "certificates.list"
            }, 
            "expected_output": "request=GET /1.0/certificates\nresult=[\"ABCDEF01\"]\n"
        }, 
        {
            "input": {
                "params": {
                    "fingerprint": "ABCDEF01"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": {
                            "type": "client", 
                            "certificate": "ABCDEF01"
                        }
                    }
                }, 
                "op": "certificates.show"
            }, 
            "expected_output": "request=GET /1.0/certificates/ABCDEF01\nresult=[\"200\", {\"metadata\": {\"certificate\": \"ABCDEF01\", \"type\": \"client\"}, \"status\": \"Success\", \"status_code\": 200, \"type\": \"sync\"}]\n"
        }
    ], 
    "description": "List certificates by short fingerprint, or fetch a single certificate as a raw response pair."
}
```

*7.2 Create and delete — Create sends a creation request to the certificates endpoint with the JSON-serialized certificate body. Delete sends a delete request to a single certificate endpoint. Both return a boolean success flag.*

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_certificate_ops.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "fingerprint": "ABCDEF01"
                }, 
                "response": {
                    "ok": true
                }, 
                "op": "certificates.delete"
            }, 
            "expected_output": "request=DELETE /1.0/certificates/ABCDEF01\nresult=true\n"
        }, 
        {
            "input": {
                "params": {
                    "certificate": "ABCDEF01"
                }, 
                "response": {
                    "ok": true
                }, 
                "op": "certificates.create"
            }, 
            "expected_output": "request=POST /1.0/certificates\nbody=\"ABCDEF01\"\nresult=true\n"
        }
    ], 
    "description": "Add or remove a trusted certificate; the create payload is a JSON body and the result is a boolean flag."
}
```

---

### Feature 8: Configuration Profiles

**As a developer**, I want to list and manage reusable configuration profiles.

**Expected Behavior / Usage:**

Profile operations target the profiles endpoint. Listing reduces profile URLs to short names; a single profile is fetched as a raw response pair. Existence checks and mutations return a boolean success flag, and payloads are JSON-serialized into the body.

*8.1 List and fetch profiles — List reads the profiles endpoint and returns profile short names. Fetch reads a single profile endpoint and returns the raw response pair.*

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_profile_list.json`

```json
{
    "cases": [
        {
            "input": {
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": [
                            "/1.0/profiles/fake-profile"
                        ]
                    }
                }, 
                "op": "profiles.list"
            }, 
            "expected_output": "request=GET /1.0/profiles\nresult=[\"fake-profile\"]\n"
        }, 
        {
            "input": {
                "params": {
                    "profile": "fake-profile"
                }, 
                "response": {
                    "status": "200", 
                    "document": {
                        "status": "Success", 
                        "status_code": 200, 
                        "type": "sync", 
                        "metadata": {
                            "config": {
                                "network.0.bridge": "lxcbr0", 
                                "resources.memory": "2GB"
                            }, 
                            "name": "fake-profile"
                        }
                    }
                }, 
                "op": "profiles.show"
            }, 
            "expected_output": "request=GET /1.0/profiles/fake-profile\nresult=[\"200\", {\"metadata\": {\"config\": {\"network.0.bridge\": \"lxcbr0\", \"resources.memory\": \"2GB\"}, \"name\": \"fake-profile\"}, \"status\": \"Success\", \"status_code\": 200, \"type\": \"sync\"}]\n"
        }
    ], 
    "description": "List profiles by short name, or fetch a single profile as a raw response pair."
}
```

*8.2 Existence check — Reads a single profile endpoint and returns a boolean indicating whether the profile is defined.*

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_profile_defined.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "profile": "fake-profile"
                }, 
                "response": {
                    "ok": true
                }, 
                "op": "profiles.defined"
            }, 
            "expected_output": "request=GET /1.0/profiles/fake-profile\nresult=true\n"
        }, 
        {
            "input": {
                "params": {
                    "profile": "fake-profile"
                }, 
                "response": {
                    "ok": false
                }, 
                "op": "profiles.defined"
            }, 
            "expected_output": "request=GET /1.0/profiles/fake-profile\nresult=false\n"
        }
    ], 
    "description": "Check whether a profile exists, returning a boolean."
}
```

*8.3 Create, update, rename, delete — Create sends a creation request to the profiles endpoint with a JSON body. Update sends a replace request to a single profile endpoint with a JSON body. Rename sends a creation request to a single profile endpoint with a JSON body. Delete sends a delete request to a single profile endpoint. All return a boolean success flag.*

**Test Cases:** `rcb_tests/public_test_cases/feature8_3_profile_ops.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "profile": "fake config"
                }, 
                "response": {
                    "ok": true
                }, 
                "op": "profiles.create"
            }, 
            "expected_output": "request=POST /1.0/profiles\nbody=\"fake config\"\nresult=true\n"
        }, 
        {
            "input": {
                "params": {
                    "profile": "fake-profile", 
                    "config": "fake config"
                }, 
                "response": {
                    "ok": true
                }, 
                "op": "profiles.update"
            }, 
            "expected_output": "request=PUT /1.0/profiles/fake-profile\nbody=\"fake config\"\nresult=true\n"
        }
    ], 
    "description": "Create, update, rename or delete a profile; payloads are JSON bodies and the result is a boolean flag."
}
```

---

### Feature 9: Transport Response Handling

**As a developer**, I want to rely on consistent translation of raw daemon HTTP responses into results or normalized errors.

**Expected Behavior / Usage:**

The transport layer parses each raw HTTP response (a numeric status and a body). An empty/`null` body is always a transport error. For document reads, a 200 status, or a 202 status whose body declares an in-progress status code of 100, yields the parsed (status, document) pair; any other status is a normalized API error. For status probes, the same success conditions yield true, a body carrying an `error` field is a normalized API error regardless of status, and any other status yields false. For raw reads, a 200 status yields the raw body and any other status is a transport error.

*9.1 Document responses — A null/empty parsed body is a transport error. A 200 status returns the parsed (status, document) pair. A 202 status whose body declares an in-progress status code of 100 also returns the pair. Any other status (e.g. 500) is a normalized API error.*

**Test Cases:** `rcb_tests/public_test_cases/feature9_1_response_object.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "status": 200, 
                    "body": "{\"foo\": \"bar\"}"
                }, 
                "op": "conn.object"
            }, 
            "expected_output": "result=[200, {\"foo\": \"bar\"}]\n"
        }, 
        {
            "input": {
                "params": {
                    "status": 500, 
                    "body": "{\"foo\": \"bar\"}"
                }, 
                "op": "conn.object"
            }, 
            "expected_output": "error=api_error\nstatus_code=null\n"
        }
    ], 
    "description": "Translate a raw document response: success pairs for 200 and in-progress 202, a transport error for empty bodies, and an API error for other statuses."
}
```

*9.2 Status probe responses — A null/empty body is a transport error. A 200 status, or an in-progress 202, yields true. A body carrying an `error` field yields a normalized API error even at status 200. Any other status (e.g. 500) yields false.*

**Test Cases:** `rcb_tests/public_test_cases/feature9_2_response_status.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "status": 200, 
                    "body": "{\"foo\": \"bar\"}"
                }, 
                "op": "conn.status"
            }, 
            "expected_output": "result=true\n"
        }, 
        {
            "input": {
                "params": {
                    "status": 500, 
                    "body": "{\"foo\": \"bar\"}"
                }, 
                "op": "conn.status"
            }, 
            "expected_output": "result=false\n"
        }
    ], 
    "description": "Translate a raw status-probe response into a boolean, with empty bodies and error-bearing bodies surfaced as errors."
}
```

*9.3 Raw responses — An empty body is a transport error. A 200 status returns the raw body string. Any other status (e.g. 500) is a transport error.*

**Test Cases:** `rcb_tests/public_test_cases/feature9_3_response_raw.json`

```json
{
    "cases": [
        {
            "input": {
                "params": {
                    "status": 200, 
                    "body": ""
                }, 
                "op": "conn.raw"
            }, 
            "expected_output": "error=daemon_error\n"
        }, 
        {
            "input": {
                "params": {
                    "status": 200, 
                    "body": "{\"foo\": \"bar\"}"
                }, 
                "op": "conn.raw"
            }, 
            "expected_output": "result=\"{\\\"foo\\\": \\\"bar\\\"}\"\n"
        }
    ], 
    "description": "Translate a raw byte response: the body on 200, otherwise a transport error."
}
```

---

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file client library implementing the features above: a transport/response layer that classifies raw HTTP responses, per-resource request builders and response projectors, and well-defined error categories. The core must be decoupled from stdin/stdout and JSON parsing.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON request from stdin, invokes the appropriate core logic, and prints the request/body/header/result/error lines exactly as specified in the Wire & Output Contract above. It must be logically separated from the core domain and must translate native errors into the neutral error categories.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` containing **only** the raw stdout of the program under test, so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same mapping pattern as the Host Field request
- reformat timestamps to the same convention used in the Network Field view
