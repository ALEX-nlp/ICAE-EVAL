## Product Requirement Document

# Microservice Sidecar Runtime CLI — Local & Cluster Lifecycle Toolkit

## Project Goal

Build the decision and rendering core of a command-line tool that manages a microservice "sidecar" runtime both on a developer's local machine and inside a container-orchestration cluster. The tool lets developers run an application with a co-located sidecar, publish events, invoke methods between applications, install/upgrade the cluster control plane, and inspect its health — without hand-writing container image references, command-line flag vectors, annotation maps, or status tables. The core is a set of pure functions that turn structured inputs (a run configuration, an option set, a release listing, a pod inventory) into deterministic, wire-ready outputs (flag lists, environment variables, URLs, YAML/JSON documents, status rows).

---

## Background & Problem

Without this tool, developers wiring a sidecar alongside their application must, by hand: normalize container-runtime names, assemble fully-qualified image references for each public or private registry, translate dozens of tuning knobs into exactly-ordered command-line flags and environment variables, build the correct HTTP routes for service invocation and event publishing, hand-edit workload manifests to add opt-in annotations, parse release feeds to discover the latest stable version, and read raw pod listings to judge cluster health. Each of these is repetitive, easy to get subtly wrong (a misordered flag, a wrong registry namespace, a release-candidate mistaken for a stable release), and painful to keep consistent across local and cluster modes.

With this tool, every one of those translations is a single, well-specified function with a stable contract: given the same structured input it always produces the same wire output, errors are reported as neutral categories instead of crashes, and the same logic backs both the local-developer commands and the cluster lifecycle commands.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility system (local run/launch, registry/image resolution, event routing, release discovery, cluster annotation, cluster status). It MUST NOT be a single "god file". Organize the code into clear modules that mirror the domains (e.g. local-run helpers, image/registry resolution, event/invocation routing, release resolution, cluster annotation, cluster status/serialization), with the execution adapter kept physically separate from the core logic.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in "Core Features" are a **black-box testing contract** for the execution adapter, NOT the internal data model of the core. The core business logic must remain completely decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating each JSON command into idiomatic calls into the core and rendering the result.

3. **Adherence to SOLID Design Principles:** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units (SRP). The core engine must be open for extension but closed for modification (OCP). Keep interfaces small and cohesive (ISP), and have high-level modules depend on abstractions rather than I/O details (DIP).

4. **Robustness & Interface Design:** The public interface of the core must be elegant and idiomatic to the target language. The system must handle edge cases gracefully and model errors explicitly (specific error types or Result/Monad patterns), never leaking host-language runtime identity into the externally observable contract.

---

## Core Features

### Feature 1: Container Runtime Normalization

**As a developer**, I want to normalize a requested container-runtime name into the executable the tool will actually invoke and learn whether my request was recognized, so I can fail fast on typos and rely on a sensible default otherwise.

**Expected Behavior / Usage:**

Given a free-form runtime name, trim surrounding whitespace and report two things: the runtime command to invoke and whether the (trimmed) request named a recognized runtime. Exactly two runtimes are recognized. Any unrecognized value — including the empty string — is reported as not valid, and the runtime command falls back to the default runtime. Output is two lines: `runtime_cmd=<command>` and `valid=<true|false>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_container_runtime.json`

```json
{
    "description": "Normalize a requested container runtime name into the command the tool will invoke, and report whether the request was a recognized runtime. Leading/trailing whitespace is trimmed. Only two runtimes are recognized; any unrecognized or empty value is reported as invalid and falls back to the default runtime command.",
    "cases": [
        {
            "input": {
                "action": "container_runtime",
                "runtime": "podman"
            },
            "expected_output": "runtime_cmd=podman\nvalid=true\n"
        },
        {
            "input": {
                "action": "container_runtime",
                "runtime": ""
            },
            "expected_output": "runtime_cmd=docker\nvalid=false\n"
        },
        {
            "input": {
                "action": "container_runtime",
                "runtime": "invalid"
            },
            "expected_output": "runtime_cmd=docker\nvalid=false\n"
        }
    ]
}
```

---

### Feature 2: List Membership Test

**As a developer**, I want a simple membership check over a list of strings, so I can branch on whether a value is already present without rewriting the loop each time.

**Expected Behavior / Usage:**

Given a list of strings and a candidate value, report whether the value appears in the list. An empty list never contains anything. Output is a single line `contains=<true|false>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_contains.json`

```json
{
    "description": "Membership test over a list of strings: report whether a given value is present. An empty list never contains anything.",
    "cases": [
        {
            "input": {
                "action": "contains",
                "list": [],
                "value": "foo"
            },
            "expected_output": "contains=false\n"
        },
        {
            "input": {
                "action": "contains",
                "list": [
                    "foo",
                    "bar",
                    "baz"
                ],
                "value": "foo"
            },
            "expected_output": "contains=true\n"
        },
        {
            "input": {
                "action": "contains",
                "list": [
                    "foo",
                    "bar",
                    "baz"
                ],
                "value": "qux"
            },
            "expected_output": "contains=false\n"
        }
    ]
}
```

---

### Feature 3: Container Image Reference Resolution

**As a developer**, I want logical component names resolved into fully-qualified container image references according to my registry choice, so I never have to remember each registry's naming convention or hand-build image paths.

**Expected Behavior / Usage:**

*3.1 Successful Resolution — resolve a logical component into a fully-qualified image reference*

Three logical components are supported: a cache, a tracing collector, and the runtime itself. Resolution depends on a default-registry selector and an optional private-registry URL. When a private-registry URL is supplied, the reference is built under that registry's namespace (`<registry-url>/dapr/3rdparty/<cache>:<tag>`, `<registry-url>/dapr/3rdparty/<tracing>`, `<registry-url>/dapr/dapr`). When no private URL is supplied, the default selector chooses between two public registries, each with its own naming convention for the same logical component: the GitHub-style registry uses a `dapr/3rdparty` namespace, while the Docker-Hub-style registry uses the upstream vendor names (e.g. the cache keeps its bare `:<tag>` name, the tracing collector uses its vendor org). Output is a single line `uri=<image reference>`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_resolve_image_success.json`

```json
{
    "description": "Resolve the fully-qualified container image reference for a logical component (cache, tracing, or runtime). Resolution depends on a default registry selector and an optional private registry URL. When a private registry URL is provided, the reference is built under that registry's namespace. Otherwise the default selector picks between two public registries, each of which has its own naming convention for the same logical component.",
    "cases": [
        {
            "input": {
                "action": "resolve_image",
                "image": "redis",
                "registry_name": "ghcr"
            },
            "expected_output": "uri=ghcr.io/dapr/3rdparty/redis:6\n"
        },
        {
            "input": {
                "action": "resolve_image",
                "image": "redis",
                "registry_name": "dockerhub"
            },
            "expected_output": "uri=redis:6\n"
        },
        {
            "input": {
                "action": "resolve_image",
                "image": "redis",
                "registry_url": "docker.io/username"
            },
            "expected_output": "uri=docker.io/username/dapr/3rdparty/redis:6\n"
        }
    ]
}
```

*3.2 Invalid Configuration — reject misconfigured registry inputs*

A private-registry URL that equals a reserved public-registry host is a misconfiguration and is rejected with `[a specific error code indicating the registry is invalid — ask the PM for the exact string]`. A default-registry selector that is neither of the two recognized values is rejected with `error=unknown_registry_name`. Errors are reported as neutral category lines only.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_resolve_image_errors.json`

```json
{
    "description": "Image reference resolution rejects invalid configuration. A private registry URL that equals a reserved public registry host is rejected as a misconfiguration. A default registry selector that is neither of the two recognized values is rejected as an unknown registry name. Errors are reported as neutral categories.",
    "cases": [
        {
            "input": {
                "action": "resolve_image",
                "image": "redis",
                "registry_url": "docker.io"
            },
            "expected_output": "[a specific error code indicating the registry is invalid — ask the PM for the exact string]\n"
        },
        {
            "input": {
                "action": "resolve_image",
                "image": "dapr",
                "registry_name": "value_other_than_dockerhub_or_ghcr"
            },
            "expected_output": "error=unknown_registry_name\n"
        }
    ]
}
```

*3.3 Default Public Registry Selection — decide whether the GitHub-style registry should be used*

Decide whether the default GitHub-style public registry should be used for pulling images. It is used only when the default-registry selector names that registry AND neither a private-registry URL nor an offline source directory is provided. Any private-registry URL, or any non-empty offline source directory, disables it. Output is a single line `use_ghcr=<true|false>`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_default_registry_selection.json`

```json
{
    "description": "Decide whether the default public registry (the GitHub-style one) should be used for pulling images. It is used only when the default registry selector names that registry AND neither a private registry URL nor an offline source directory is provided. Any private registry URL or offline source directory disables it.",
    "cases": [
        {
            "input": {
                "action": "use_ghcr",
                "image": "dapr",
                "registry_url": "",
                "registry_name": "ghcr",
                "from_dir": ""
            },
            "expected_output": "use_ghcr=true\n"
        },
        {
            "input": {
                "action": "use_ghcr",
                "image": "dapr",
                "registry_url": "",
                "registry_name": "ghcr",
                "from_dir": "testDir"
            },
            "expected_output": "use_ghcr=false\n"
        },
        {
            "input": {
                "action": "use_ghcr",
                "image": "dapr",
                "registry_url": "",
                "registry_name": "dockerhub",
                "from_dir": ""
            },
            "expected_output": "use_ghcr=false\n"
        }
    ]
}
```

---

### Feature 4: Air-Gap (Offline) Mode Detection

**As a developer**, I want the tool to detect offline (air-gapped) install mode from a source-directory input, so installs from a local bundle automatically skip network registries.

**Expected Behavior / Usage:**

Given a source-directory path, report whether offline mode is active. A non-blank path enables offline mode; an empty string or a whitespace-only string does not. Output is a single line `airgap=<true|false>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_airgap_mode.json`

```json
{
    "description": "Detect offline (air-gap) installation mode from a source-directory input. A non-blank directory path enables offline mode; an empty string or whitespace-only string does not.",
    "cases": [
        {
            "input": {
                "action": "airgap_mode",
                "from_dir": ""
            },
            "expected_output": "airgap=false\n"
        },
        {
            "input": {
                "action": "airgap_mode",
                "from_dir": "./local-dir"
            },
            "expected_output": "airgap=true\n"
        }
    ]
}
```

---

### Feature 5: Default Runtime Configuration Document

**As a developer**, I want a ready-to-use default runtime configuration document generated for a local install, so I get correct tracing wiring without writing YAML by hand.

**Expected Behavior / Usage:**

Produce the default runtime configuration as a YAML document. When a tracing-collector host is supplied, the document enables tracing with full sampling (`samplingRate: "1"`) and a collector endpoint derived from the host (`http://<host>:9411/api/v2/spans`). When no host is supplied, a minimal document with an empty spec (`spec: {}`) is produced. The document always carries the fixed API version, kind, and metadata name. Output is the raw YAML document.

**Test Cases:** `rcb_tests/public_test_cases/feature5_default_configuration.json`

```json
{
    "description": "Generate the default runtime configuration document (YAML) for a local install. When a tracing collector host is supplied, the document enables tracing with full sampling and a collector endpoint derived from the host. When no host is supplied, a minimal configuration with an empty spec is produced.",
    "cases": [
        {
            "input": {
                "action": "default_config",
                "zipkin_host": "test_zipkin_host"
            },
            "expected_output": "apiVersion: dapr.io/v1alpha1\nkind: Configuration\nmetadata:\n  name: daprConfig\nspec:\n  tracing:\n    samplingRate: \"1\"\n    zipkin:\n      endpointAddress: http://test_zipkin_host:9411/api/v2/spans\n"
        },
        {
            "input": {
                "action": "default_config",
                "zipkin_host": ""
            },
            "expected_output": "apiVersion: dapr.io/v1alpha1\nkind: Configuration\nmetadata:\n  name: daprConfig\nspec: {}\n"
        }
    ]
}
```

---

### Feature 6: Sidecar Launch Specification

**As a developer**, I want my run configuration translated into the exact command-line flag vector and environment variables the runtime expects, so launching a sidecar is deterministic and I never misorder a flag.

**Expected Behavior / Usage:**

*6.1 Core Flag Vector — map a run configuration to an ordered flag list*

Translate a sidecar run configuration into the ordered command-line flag vector passed to the runtime binary. Each populated field maps to a `--flag` token followed by its value token; boolean fields become bare presence flags when true (and are omitted when false). An optional config-file field, when set, inserts its `--config <path>` flag in declaration order. Numeric fields carrying the sentinel value `-1` are still emitted (they instruct the runtime to auto-pick a value). Output is the flag vector, one token per line, in declaration order.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_launch_flags_common.json`

```json
{
    "description": "Translate a sidecar run configuration into the ordered command-line flag vector passed to the runtime binary. Each populated field maps to a '--flag' followed by its value (booleans become bare presence flags when true). Numeric fields with sentinel value -1 are still emitted (they tell the runtime to auto-pick). The output is the flag list, one token per line, in declaration order.",
    "cases": [
        {
            "input": {
                "action": "launch_flags",
                "config": {
                    "app_id": "MyID",
                    "app_port": 3000,
                    "http_port": 8000,
                    "grpc_port": 50001,
                    "log_level": "WARN",
                    "protocol": "http",
                    "components_path": "/tmp/components",
                    "app_ssl": true,
                    "metrics_port": 9001,
                    "max_request_body_size": -1,
                    "internal_grpc_port": 5050,
                    "http_read_buffer_size": -1,
                    "max_concurrency": -1,
                    "enable_api_logging": true
                }
            },
            "expected_output": "--app-id\nMyID\n--app-port\n3000\n--dapr-http-port\n8000\n--dapr-grpc-port\n50001\n--app-protocol\nhttp\n--profile-port\n0\n--log-level\nWARN\n--app-max-concurrency\n-1\n--components-path\n/tmp/components\n--app-ssl\n--metrics-port\n9001\n--dapr-http-max-request-size\n-1\n--dapr-http-read-buffer-size\n-1\n--dapr-internal-grpc-port\n5050\n--enable-api-logging\n"
        },
        {
            "input": {
                "action": "launch_flags",
                "config": {
                    "app_id": "MyID",
                    "app_port": 3000,
                    "http_port": 8000,
                    "grpc_port": 50001,
                    "log_level": "INFO",
                    "protocol": "http",
                    "components_path": "/tmp/components",
                    "config_file": "/tmp/config.yaml",
                    "app_ssl": true,
                    "metrics_port": 9001,
                    "max_request_body_size": -1,
                    "internal_grpc_port": 5050,
                    "http_read_buffer_size": -1,
                    "max_concurrency": -1,
                    "enable_api_logging": true
                }
            },
            "expected_output": "--app-id\nMyID\n--app-port\n3000\n--dapr-http-port\n8000\n--dapr-grpc-port\n50001\n--config\n/tmp/config.yaml\n--app-protocol\nhttp\n--profile-port\n0\n--log-level\nINFO\n--app-max-concurrency\n-1\n--components-path\n/tmp/components\n--app-ssl\n--metrics-port\n9001\n--dapr-http-max-request-size\n-1\n--dapr-http-read-buffer-size\n-1\n--dapr-internal-grpc-port\n5050\n--enable-api-logging\n"
        }
    ]
}
```

*6.2 Application Health-Check Flags — emit health flags only when enabled*

Application health-check flags are emitted into the flag vector only when health checking is enabled. When disabled, none of the health-related flags appear. When enabled without explicit tuning values, only the bare enable flag (`--enable-app-health-check`) appears, letting the runtime keep its own defaults. When enabled with explicit interval, timeout, threshold, and path values, each corresponding flag is also emitted in declaration order. Output is the flag vector, one token per line.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_launch_flags_health.json`

```json
{
    "description": "Application health-check flags are emitted into the runtime flag vector only when health checking is enabled. When disabled, none of the health-related flags appear. When enabled without explicit tuning values, only the bare enable flag appears (the runtime keeps its own defaults). When enabled with explicit interval, timeout, threshold, and path values, each of those flags is also emitted. Output is the flag list, one token per line, in declaration order.",
    "cases": [
        {
            "input": {
                "action": "launch_flags",
                "config": {
                    "app_id": "MyID",
                    "http_port": 8000,
                    "grpc_port": 50001,
                    "log_level": "INFO",
                    "protocol": "http",
                    "components_path": "/tmp/components",
                    "metrics_port": 9001,
                    "max_request_body_size": -1,
                    "internal_grpc_port": 5050,
                    "http_read_buffer_size": -1,
                    "max_concurrency": -1,
                    "enable_app_health": false
                }
            },
            "expected_output": "--app-id\nMyID\n--app-port\n0\n--dapr-http-port\n8000\n--dapr-grpc-port\n50001\n--app-protocol\nhttp\n--profile-port\n0\n--log-level\nINFO\n--app-max-concurrency\n-1\n--components-path\n/tmp/components\n--metrics-port\n9001\n--dapr-http-max-request-size\n-1\n--dapr-http-read-buffer-size\n-1\n--dapr-internal-grpc-port\n5050\n"
        },
        {
            "input": {
                "action": "launch_flags",
                "config": {
                    "app_id": "MyID",
                    "http_port": 8000,
                    "grpc_port": 50001,
                    "log_level": "INFO",
                    "protocol": "http",
                    "components_path": "/tmp/components",
                    "metrics_port": 9001,
                    "max_request_body_size": -1,
                    "internal_grpc_port": 5050,
                    "http_read_buffer_size": -1,
                    "max_concurrency": -1,
                    "enable_app_health": true
                }
            },
            "expected_output": "--app-id\nMyID\n--app-port\n0\n--dapr-http-port\n8000\n--dapr-grpc-port\n50001\n--app-protocol\nhttp\n--profile-port\n0\n--log-level\nINFO\n--app-max-concurrency\n-1\n--components-path\n/tmp/components\n--metrics-port\n9001\n--dapr-http-max-request-size\n-1\n--dapr-http-read-buffer-size\n-1\n--dapr-internal-grpc-port\n5050\n--enable-app-health-check\n"
        },
        {
            "input": {
                "action": "launch_flags",
                "config": {
                    "app_id": "MyID",
                    "http_port": 8000,
                    "grpc_port": 50001,
                    "log_level": "INFO",
                    "protocol": "http",
                    "components_path": "/tmp/components",
                    "metrics_port": 9001,
                    "max_request_body_size": -1,
                    "internal_grpc_port": 5050,
                    "http_read_buffer_size": -1,
                    "max_concurrency": -1,
                    "enable_app_health": true,
                    "app_health_interval": 2,
                    "app_health_timeout": 200,
                    "app_health_threshold": 1,
                    "app_health_path": "/foo"
                }
            },
            "expected_output": "--app-id\nMyID\n--app-port\n0\n--dapr-http-port\n8000\n--dapr-grpc-port\n50001\n--app-protocol\nhttp\n--profile-port\n0\n--log-level\nINFO\n--app-max-concurrency\n-1\n--components-path\n/tmp/components\n--metrics-port\n9001\n--dapr-http-max-request-size\n-1\n--dapr-http-read-buffer-size\n-1\n--dapr-internal-grpc-port\n5050\n--enable-app-health-check\n--app-health-check-path\n/foo\n--app-health-probe-interval\n2\n--app-health-probe-timeout\n200\n--app-health-threshold\n1\n"
        }
    ]
}
```

*6.3 Application Environment Variables — derive the env vars passed to the launched app*

Derive the environment variables propagated to the launched application process. Four variables are always emitted in declaration order: the app id (`APP_ID`), the runtime HTTP port (`DAPR_HTTP_PORT`), the runtime gRPC port (`DAPR_GRPC_PORT`), and the metrics port (`DAPR_METRICS_PORT`). The application port (`APP_PORT`) is emitted only when it is a positive value; a non-positive app port is omitted. Output is the variable list, one `KEY=value` per line.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_launch_env.json`

```json
{
    "description": "Derive the environment variables propagated to the launched application process from the run configuration. Four core variables are always emitted: the runtime gRPC port, the runtime HTTP port, the metrics port, and the app ID. The app port is emitted only when it is a positive value; a non-positive app port is omitted. Output is the variable list, one 'KEY=value' per line, in declaration order.",
    "cases": [
        {
            "input": {
                "action": "launch_env",
                "config": {
                    "app_id": "MyID",
                    "app_port": 3000,
                    "http_port": 8000,
                    "grpc_port": 50001,
                    "metrics_port": 9001
                }
            },
            "expected_output": "APP_ID=MyID\nAPP_PORT=3000\nDAPR_HTTP_PORT=8000\nDAPR_GRPC_PORT=50001\nDAPR_METRICS_PORT=9001\n"
        },
        {
            "input": {
                "action": "launch_env",
                "config": {
                    "app_id": "MyID",
                    "app_port": 0,
                    "http_port": 8000,
                    "grpc_port": 50001,
                    "metrics_port": 9001
                }
            },
            "expected_output": "APP_ID=MyID\nDAPR_HTTP_PORT=8000\nDAPR_GRPC_PORT=50001\nDAPR_METRICS_PORT=9001\n"
        }
    ]
}
```

---

### Feature 7: Service Invocation Routing

**As a developer**, I want to invoke a method on another locally running application through its sidecar over HTTP, so I can call services by id and method name instead of constructing URLs.

**Expected Behavior / Usage:**

Given a target application id, a method name, an HTTP verb, and a payload, route the call through the sidecar of the running target. The set of running applications is provided. If the target id is present, the request is routed to its service-invocation URL — the path is `/v<api>/invoke/<appId>/method/<method>` — and the response body is returned; output is two lines `path=<routed path>` and `response=<body>`. The same routing applies across verbs (GET/POST/PUT/DELETE); a verb whose handler returns no body yields an empty response value. If the target id is not among the running applications, output is `error=app_not_found`. If enumerating the running applications fails, output is `error=list_failed`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_invoke.json`

```json
{
    "description": "Invoke a method on a locally running application through its sidecar over HTTP. The caller supplies a target application id, a method name, an HTTP verb, and a payload. The set of running applications is provided; if the target id is present, the request is routed to that application's service-invocation URL and the response body is returned. The routed path follows '/v<api>/invoke/<appId>/method/<method>'. If the target id is not among the running applications, a neutral not-found error is returned; if listing the running applications fails, a neutral list-failure error is returned. The same routing applies across verbs (GET/POST/PUT/DELETE).",
    "cases": [
        {
            "input": {
                "action": "invoke",
                "app_id": "testapp",
                "method": "test",
                "verb": "GET",
                "list_app_id": "testapp",
                "expected_path": "/v1.0/invoke/testapp/method/test",
                "server_resp": "successful invoke"
            },
            "expected_output": "path=/v1.0/invoke/testapp/method/test\nresponse=successful invoke\n"
        },
        {
            "input": {
                "action": "invoke",
                "app_id": "invalid",
                "method": "test",
                "verb": "GET",
                "list_app_id": "testapp"
            },
            "expected_output": "error=app_not_found\n"
        },
        {
            "input": {
                "action": "invoke",
                "app_id": "testapp",
                "method": "test",
                "verb": "GET",
                "list_err": true
            },
            "expected_output": "error=list_failed\n"
        }
    ]
}
```

---

### Feature 8: Event Publishing

**As a developer**, I want to publish an event to a topic on a named pub/sub component through a running application's sidecar, so I can emit events by naming the component, topic, and payload.

**Expected Behavior / Usage:**

*8.1 Validation & Routing — validate required inputs and route the event*

Required inputs are the publishing application id, the pub/sub component name, and the topic. Each missing required input is reported as a neutral missing-field error naming the offending field, checked in the fixed order app id → pub/sub name → topic; output is `error=missing_field` followed by `field=<app_id|pubsub_name|topic>`. When enumerating running applications fails, output is `error=list_failed`. When the publishing application is not among the running applications, output is `error=instance_not_found`. On success the event is routed to `/v<api>/publish/<pubsub>/<topic>` with content type `application/json`; output is `path=<routed path>` and `content_type=application/json`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_publish_routing.json`

```json
{
    "description": "Publish an event to a topic on a named pub/sub component through a running application's sidecar. Required inputs are the publishing application id, the pub/sub component name, and the topic; each missing required input is reported as a neutral missing-field error naming the offending field (checked in the order app id, pub/sub name, topic). When listing running applications fails, a neutral list-failure error is returned. When the publishing application is not among the running applications, a neutral instance-not-found error is returned. On success the event is routed to '/v<api>/publish/<pubsub>/<topic>' with content type 'application/json'.",
    "cases": [
        {
            "input": {
                "action": "publish",
                "app_id": "",
                "pubsub": "test",
                "payload": "test"
            },
            "expected_output": "error=missing_field\nfield=app_id\n"
        },
        {
            "input": {
                "action": "publish",
                "app_id": "myAppID",
                "pubsub": "testPubsubName",
                "topic": "testTopic",
                "payload": "test payload",
                "list_app_id": "not my myAppID"
            },
            "expected_output": "error=instance_not_found\n"
        },
        {
            "input": {
                "action": "publish",
                "app_id": "myAppID",
                "pubsub": "testPubsubName",
                "topic": "testTopic",
                "payload": "test payload",
                "list_app_id": "myAppID"
            },
            "expected_output": "path=/v1.0/publish/testPubsubName/testTopic\ncontent_type=application/json\n"
        }
    ]
}
```

*8.2 CloudEvents Envelope — advertise the CloudEvents content type for pre-formed envelopes*

When the payload is already a complete CloudEvents envelope (it contains the id, source, specversion, type, and data fields), the publish request advertises the CloudEvents content type `application/cloudevents+json` instead of plain JSON, so the receiving sidecar treats the body as a pre-formed envelope. The event is still routed to `/v<api>/publish/<pubsub>/<topic>`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_publish_cloudevent.json`

```json
{
    "description": "When the payload is a complete CloudEvents envelope (it contains the id, source, specversion, type, and data fields), the publish request advertises the CloudEvents content type 'application/cloudevents+json' instead of plain JSON, so the receiving sidecar treats the body as a pre-formed envelope. The event is still routed to '/v<api>/publish/<pubsub>/<topic>'.",
    "cases": [
        {
            "input": {
                "action": "publish",
                "app_id": "myAppID",
                "pubsub": "testPubsubName",
                "topic": "testTopic",
                "payload": "{\"id\": \"1234\", \"source\": \"test\", \"specversion\": \"1.0\", \"type\": \"product.v1\", \"datacontenttype\": \"application/json\", \"data\": {\"id\": \"test\", \"description\": \"Testing 12345\"}}",
                "list_app_id": "myAppID",
                "cloudevent": true
            },
            "expected_output": "path=/v1.0/publish/testPubsubName/testTopic\ncontent_type=application/cloudevents+json\n"
        }
    ]
}
```

*8.3 Metadata Query String — build the publish metadata query string*

Build an HTTP query string from a metadata map for publish requests. Each key is prefixed with `metadata.` and rendered as `metadata.<key>=<value>`. A non-empty map yields a string starting with `?`; an empty or absent map yields an empty string. Output is a single line `query=<query string>`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_3_publish_query_params.json`

```json
{
    "description": "Build an HTTP query string from a metadata map for publish requests. Each key is prefixed with 'metadata.' and rendered as 'metadata.<key>=<value>'. A non-empty map yields a string starting with '?'; an empty or absent map yields an empty string.",
    "cases": [
        {
            "input": {
                "action": "query_params",
                "metadata": {}
            },
            "expected_output": "query=\n"
        },
        {
            "input": {
                "action": "query_params",
                "metadata": {
                    "rawPayload": "true"
                }
            },
            "expected_output": "query=?metadata.rawPayload=true\n"
        }
    ]
}
```

---

### Feature 9: Offline Bundle Manifest Parsing

**As a developer**, I want an offline install bundle's manifest parsed and validated, so an air-gapped install knows exactly which versions, sub-directories, and image files to use.

**Expected Behavior / Usage:**

Parse the bundle's details document (JSON) and expose the extracted fields: runtime version, dashboard version, binary sub-directory, image sub-directory, image name, and image file name. A well-formed document with all required fields present and non-blank yields those values, one `key=value` per line. A document with malformed JSON yields `error=malformed_details`. A document that is valid JSON but missing or blanking any required field yields `error=missing_required_fields`. A missing manifest file yields `error=file_not_found`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_parse_bundle_details.json`

```json
{
    "description": "Parse an offline install bundle's details document (JSON) and expose the extracted fields. A well-formed document with all required fields (runtime version, dashboard version, binary sub-directory, image sub-directory, image name, image file name) yields those values. A document with malformed JSON, a document missing or blanking any required field, or a missing file each yields a distinct neutral error category.",
    "cases": [
        {
            "input": {
                "action": "parse_bundle",
                "content": "{\n\"daprd\": \"1.7.0\",\n\"dashboard\": \"0.10.0\",\n\"cli\": \"1.7.0\",\n\"daprBinarySubDir\": \"dist\",\n\"dockerImageSubDir\": \"docker\",\n\"daprImageName\": \"daprio/dapr:1.7.2\",\n\"daprImageFileName\": \"daprio-dapr-1.7.2.tar.gz\"\n}"
            },
            "expected_output": "runtime_version=1.7.0\ndashboard_version=0.10.0\nbinary_subdir=dist\nimage_subdir=docker\nimage_name=daprio/dapr:1.7.2\nimage_file_name=daprio-dapr-1.7.2.tar.gz\n"
        },
        {
            "input": {
                "action": "parse_bundle",
                "content": "{\n\"daprd\": \"1.7.0\",\n\"dashboard\": \"0.10.0\",\n\"cli\": \"1.7.0\",\n\"daprImageName\": \"daprio/dapr:1.7.2\"\n\"daprImageFileName\": \"daprio-dapr-1.7.2.tar.gz\"\n}"
            },
            "expected_output": "error=malformed_details\n"
        },
        {
            "input": {
                "action": "parse_bundle",
                "content": "{\n\"daprd\": \"\",\n\"dashboard\": \"\",\n\"cli\": \"1.7.0\",\n\"daprBinarySubDir\": \"dist\",\n\"dockerImageSubDir\": \"docker\",\n\"daprImageName\": \"daprio/dapr:1.7.2\",\n\"daprImageFileName\": \"daprio-dapr-1.7.2.tar.gz\"\n}"
            },
            "expected_output": "error=missing_required_fields\n"
        },
        {
            "input": {
                "action": "parse_bundle",
                "file_missing": true
            },
            "expected_output": "error=file_not_found\n"
        }
    ]
}
```

---

### Feature 10: Dashboard Launch Command

**As a developer**, I want the exact command vector to launch the local dashboard on a chosen port, so I can start the UI without remembering its binary name or flags.

**Expected Behavior / Usage:**

Given a port, build the command vector that launches the dashboard process: the program is the dashboard binary, followed by a `--port` flag and the requested port value. Output names the program and each argument: `binary=<name>` then one `arg=<token>` line per argument.

**Test Cases:** `rcb_tests/public_test_cases/feature10_dashboard_command.json`

```json
{
    "description": "Build the command vector used to launch the local dashboard process on a chosen port. The command's program is the dashboard binary, followed by a '--port' flag and the requested port value.",
    "cases": [
        {
            "input": {
                "action": "dashboard_cmd",
                "port": 9090
            },
            "expected_output": "binary=dashboard\narg=--port\narg=9090\n"
        },
        {
            "input": {
                "action": "dashboard_cmd",
                "port": 8080
            },
            "expected_output": "binary=dashboard\narg=--port\narg=8080\n"
        }
    ]
}
```

---

### Feature 11: Sidecar Metadata Endpoint URL

**As a developer**, I want the sidecar metadata endpoint URL constructed for a local HTTP port, so I can query a running sidecar's metadata without hand-building the loopback URL.

**Expected Behavior / Usage:**

Given a local HTTP port, construct the metadata collection GET URL of the form `http://127.0.0.1:<port>/v<api>/metadata`. Output is a single line `url=<endpoint URL>`.

**Test Cases:** `rcb_tests/public_test_cases/feature11_metadata_endpoint.json`

```json
{
    "description": "Construct the sidecar metadata GET endpoint URL for a given local HTTP port. A positive port produces a loopback URL of the form 'http://127.0.0.1:<port>/v<api>/metadata' targeting the metadata collection.",
    "cases": [
        {
            "input": {
                "action": "metadata_endpoint",
                "op": "get",
                "port": 9999
            },
            "expected_output": "url=http://127.0.0.1:9999/v1.0/metadata\n"
        }
    ]
}
```

---

### Feature 12: Latest Release Resolution

**As a developer**, I want the latest stable runtime release discovered from a release feed, so installs and upgrades pick a real stable version and never a release candidate.

**Expected Behavior / Usage:**

*12.1 From a Releases Listing — pick the highest stable version from a JSON release array*

Resolve the latest stable runtime release from a releases listing (a JSON array of release objects). Release-candidate tags (those containing `-rc`) are skipped; among the remaining stable tags the highest semantic version is selected and returned without its leading `v`; output is `version=<x.y.z>`. An empty listing, or a listing containing only release candidates, yields `error=no_releases`. A non-200 HTTP response yields `error=http_status` followed by `status=<code>`. A body that is not valid JSON yields `error=parse_error`.

**Test Cases:** `rcb_tests/public_test_cases/feature12_1_version_github.json`

```json
{
    "description": "Resolve the latest stable runtime release version from a GitHub-style releases listing (a JSON array of release objects). Release candidate tags (those containing '-rc') are skipped; among the remaining stable tags the highest semantic version is selected and returned without its leading 'v'. An empty listing, or a listing containing only release candidates, yields a neutral no-releases error. A non-200 HTTP response yields a neutral http-status error carrying the status code. A body that is not valid JSON yields a neutral parse error.",
    "cases": [
        {
            "input": {
                "action": "version_github",
                "body": "[{\"url\": \"https://api.example/x\", \"html_url\": \"https://example/tag/v1.4.4\", \"id\": 1, \"tag_name\": \"v1.4.4\", \"target_commitish\": \"master\", \"name\": \"Runtime v1.4.4\", \"draft\": false, \"prerelease\": false}, {\"url\": \"https://api.example/x\", \"html_url\": \"https://example/tag/v1.5.1\", \"id\": 1, \"tag_name\": \"v1.5.1\", \"target_commitish\": \"master\", \"name\": \"Runtime v1.5.1\", \"draft\": false, \"prerelease\": false}]"
            },
            "expected_output": "version=1.5.1\n"
        },
        {
            "input": {
                "action": "version_github",
                "body": "[]"
            },
            "expected_output": "error=no_releases\n"
        },
        {
            "input": {
                "action": "version_github",
                "body": "x",
                "status": 404
            },
            "expected_output": "error=http_status\nstatus=404\n"
        }
    ]
}
```

*12.2 From a Chart Index — pick the first stable app version from a chart index*

Resolve the latest stable runtime release from a chart index document (YAML). The first chart entry whose app version is a stable release (does not contain `-rc`) is returned as `version=<x.y.z>`. An empty document, or a document whose entries are all release candidates, yields `error=no_releases`. A body that is not valid YAML yields `error=parse_error`.

**Test Cases:** `rcb_tests/public_test_cases/feature12_2_version_helm.json`

```json
{
    "description": "Resolve the latest stable runtime release version from a chart index document (YAML). The first chart entry whose app version is a stable release (does not contain '-rc') is returned. An empty document, or a document whose entries are all release candidates, yields a neutral no-releases error. A body that is not valid YAML yields a neutral parse error.",
    "cases": [
        {
            "input": {
                "action": "version_helm",
                "body": "apiVersion: v1\nentries:\n  dapr:\n  - apiVersion: v1\n    appVersion: 1.2.3-rc.1\n    name: dapr\n    version: 1.2.3-rc.1\n  - apiVersion: v1\n    appVersion: 1.2.2\n    name: dapr\n    version: 1.2.2      "
            },
            "expected_output": "version=1.2.2\n"
        },
        {
            "input": {
                "action": "version_helm",
                "body": "["
            },
            "expected_output": "error=parse_error\n"
        },
        {
            "input": {
                "action": "version_helm",
                "body": ""
            },
            "expected_output": "error=no_releases\n"
        }
    ]
}
```

---

### Feature 13: Workload Annotation Injection

**As a developer**, I want sidecar opt-in annotations injected into a targeted workload manifest, so I can enable the sidecar on an existing resource without hand-editing YAML.

**Expected Behavior / Usage:**

Locate the workload resource in the document by name and inject sidecar annotations: always an `dapr.io/enabled: "true"` marker, plus any annotations derived from the supplied option set (for example an application id, a custom sidecar image, a log level, or a profiling flag). The rest of the document is preserved. When no application id is supplied, a default application id is synthesized from the resource name (`default-pod-<name>`). Annotation keys are emitted in sorted order within the document's metadata. Output is the rewritten YAML document.

**Test Cases:** `rcb_tests/public_test_cases/feature13_annotate_pod.json`

```json
{
    "description": "Inject sidecar opt-in annotations into a single targeted workload document (a pod). The annotator locates the resource by name and adds an 'enabled=true' annotation plus any annotations derived from the supplied option set (for example an application id, a custom sidecar image, a log level, or a profiling flag), while preserving the rest of the document. When no application id is supplied, only the enabled marker is added.",
    "cases": [
        {
            "input": {
                "action": "annotate",
                "yaml": "apiVersion: v1\nkind: Pod\nmetadata:\n  name: mypod\n  labels:\n    name: nginx\nspec:\n  containers:\n  - name: nginx\n  image: nginx\n  ports:\n  - containerPort: 80",
                "target_resource": "mypod",
                "options": {
                    "app_id": "test-app"
                }
            },
            "expected_output": "apiVersion: v1\nkind: Pod\nmetadata:\n  annotations:\n    dapr.io/app-id: test-app\n    dapr.io/enabled: \"true\"\n  labels:\n    name: nginx\n  name: mypod\nspec:\n  containers:\n  - name: nginx\n  image: nginx\n  ports:\n  - containerPort: 80\n"
        },
        {
            "input": {
                "action": "annotate",
                "yaml": "apiVersion: v1\nkind: Pod\nmetadata:\n  name: mypod\n  labels:\n    name: nginx\nspec:\n  containers:\n  - name: nginx\n  image: nginx\n  ports:\n  - containerPort: 80",
                "target_resource": "mypod",
                "options": {
                    "app_id": "test-app",
                    "profile_enabled": true,
                    "log_level": "info",
                    "dapr_image": "custom-image"
                }
            },
            "expected_output": "apiVersion: v1\nkind: Pod\nmetadata:\n  annotations:\n    dapr.io/app-id: test-app\n    dapr.io/enable-profiling: \"true\"\n    dapr.io/enabled: \"true\"\n    dapr.io/log-level: info\n    dapr.io/sidecar-image: custom-image\n  labels:\n    name: nginx\n  name: mypod\nspec:\n  containers:\n  - name: nginx\n  image: nginx\n  ports:\n  - containerPort: 80\n"
        },
        {
            "input": {
                "action": "annotate",
                "yaml": "apiVersion: v1\nkind: Pod\nmetadata:\n  name: mypod\n  labels:\n    name: nginx\nspec:\n  containers:\n  - name: nginx\n  image: nginx\n  ports:\n  - containerPort: 80",
                "target_resource": "mypod",
                "options": {}
            },
            "expected_output": "apiVersion: v1\nkind: Pod\nmetadata:\n  annotations:\n    dapr.io/app-id: default-pod-mypod\n    dapr.io/enabled: \"true\"\n  labels:\n    name: nginx\n  name: mypod\nspec:\n  containers:\n  - name: nginx\n  image: nginx\n  ports:\n  - containerPort: 80\n"
        }
    ]
}
```

---

### Feature 14: Sidecar Annotation Pair Rendering

**As a developer**, I want the full set of sidecar annotation key/value pairs rendered from an option set, so I can see exactly which annotations a given configuration produces.

**Expected Behavior / Usage:**

Given a populated option set, resolve the complete set of sidecar annotation key/value pairs and render them one `key=value` per line, sorted by key. Boolean feature toggles render as `true`, numeric options render as their decimal value, and string options render verbatim. Each annotation key carries the `dapr.io/` prefix.

**Test Cases:** `rcb_tests/public_test_cases/feature14_annotation_pairs.json`

```json
{
    "description": "Resolve the full set of sidecar annotation key/value pairs from a populated option set, rendered one 'key=value' per line and sorted by key. Boolean feature toggles render as 'true', numeric options render as their decimal value, and string options render verbatim.",
    "cases": [
        {
            "input": {
                "action": "annotation_pairs",
                "options": {
                    "app_id": "test-app",
                    "metrics_enabled": true,
                    "metrics_port": 9090,
                    "api_token_secret": "test-api-token-secret",
                    "app_token_secret": "test-app-token-secret",
                    "app_max_concurrency": 2,
                    "app_port": 8080,
                    "app_protocol": "http",
                    "app_ssl": true,
                    "cpu_limit": "0.5",
                    "memory_limit": "512Mi",
                    "cpu_request": "0.1",
                    "memory_request": "256Mi",
                    "config": "appconfig",
                    "debug_enabled": true,
                    "debug_port": 9091,
                    "env": "key=value key1=value1",
                    "log_as_json": true,
                    "listen_addresses": "0.0.0.0",
                    "dapr_image": "test-iamge",
                    "profile_enabled": true,
                    "max_request_body_size": 8,
                    "read_buffer_size": 4,
                    "readiness_probe_delay": 40,
                    "readiness_probe_period": 50,
                    "readiness_probe_threshold": 6,
                    "readiness_probe_timeout": 60,
                    "liveness_probe_delay": 10,
                    "liveness_probe_period": 20,
                    "liveness_probe_threshold": 3,
                    "liveness_probe_timeout": 30,
                    "log_level": "debug",
                    "http_stream_request_body": true,
                    "graceful_shutdown_seconds": 10,
                    "enable_api_logging": true,
                    "unix_domain_socket_path": "/tmp/dapr.sock",
                    "volume_mounts_read_only": "vm1:/tmp/path1,vm2:/tmp/path2",
                    "volume_mounts_read_write": "vm3:/tmp/path3",
                    "disable_builtin_k8s_secret_store": true,
                    "placement_host_address": "127.0.0.1:50057,127.0.0.1:50058"
                }
            },
            "expected_output": "dapr.io/api-token-secret=test-api-token-secret\ndapr.io/app-id=test-app\ndapr.io/app-max-concurrency=2\ndapr.io/app-port=8080\ndapr.io/app-protocol=http\ndapr.io/app-ssl=true\ndapr.io/app-token-secret=test-app-token-secret\ndapr.io/config=appconfig\ndapr.io/debug-port=9091\ndapr.io/disable-builtin-k8s-secret-store=true\ndapr.io/enable-api-logging=true\ndapr.io/enable-debug=true\ndapr.io/enable-metrics=true\ndapr.io/enable-profiling=true\ndapr.io/enabled=true\ndapr.io/env=key=value key1=value1\ndapr.io/graceful-shutdown-seconds=10\ndapr.io/http-max-request-size=8\ndapr.io/http-read-buffer-size=4\ndapr.io/http-stream-request-body=true\ndapr.io/log-as-json=true\ndapr.io/log-level=debug\ndapr.io/metrics-port=9090\ndapr.io/placement-host-address=127.0.0.1:50057,127.0.0.1:50058\ndapr.io/sidecar-cpu-limit=0.5\ndapr.io/sidecar-cpu-request=0.1\ndapr.io/sidecar-image=test-iamge\ndapr.io/sidecar-listen-addresses=0.0.0.0\ndapr.io/sidecar-liveness-probe-delay-seconds=10\ndapr.io/sidecar-liveness-probe-period-seconds=20\ndapr.io/sidecar-liveness-probe-threshold=3\ndapr.io/sidecar-liveness-probe-timeout-seconds=30\ndapr.io/sidecar-memory-limit=512Mi\ndapr.io/sidecar-memory-request=256Mi\ndapr.io/sidecar-readiness-probe-delay-seconds=40\ndapr.io/sidecar-readiness-probe-period-seconds=50\ndapr.io/sidecar-readiness-probe-threshold=6\ndapr.io/sidecar-readiness-probe-timeout-seconds=60\ndapr.io/unix-domain-socket-path=/tmp/dapr.sock\ndapr.io/volume-mounts-rw=vm3:/tmp/path3\ndapr.io/volume-mounts=vm1:/tmp/path1,vm2:/tmp/path2\n"
        }
    ]
}
```

---

### Feature 15: High-Availability Mode Detection

**As a developer**, I want to know whether the control plane is running in high-availability mode from its observed replica counts, so status and upgrade flows behave correctly for HA clusters.

**Expected Behavior / Usage:**

Given the observed replica counts of the control-plane services, report whether the deployment is in high-availability mode. A replica count greater than one indicates high availability; a single replica does not. Output is a single line `high_availability=<true|false>`.

**Test Cases:** `rcb_tests/public_test_cases/feature15_ha_mode.json`

```json
{
    "description": "Determine whether a control-plane deployment is running in high-availability mode from the observed replica counts of its services. A replica count greater than one indicates high availability; a single replica does not.",
    "cases": [
        {
            "input": {
                "action": "ha_mode",
                "replicas": [
                    3
                ]
            },
            "expected_output": "high_availability=true\n"
        },
        {
            "input": {
                "action": "ha_mode",
                "replicas": [
                    1
                ]
            },
            "expected_output": "high_availability=false\n"
        }
    ]
}
```

---

### Feature 16: Upgrade Chart Value Counting

**As a developer**, I want to know how many leaf chart values an upgrade configuration produces, so I can verify that mutual-TLS material and extra overrides are all accounted for.

**Expected Behavior / Usage:**

Count the leaf chart values produced when assembling the control-plane upgrade configuration with mutual TLS enabled. With no extra set arguments the configuration contributes a fixed pair of values; each additional `key=value` upgrade argument contributes one more leaf value. Output is a single line `value_count=<n>`.

**Test Cases:** `rcb_tests/public_test_cases/feature16_chart_values.json`

```json
{
    "description": "Count the leaf chart values produced when assembling the control-plane upgrade configuration with mutual TLS enabled. With no extra set arguments the configuration contributes a fixed pair of values; each additional 'key=value' upgrade argument contributes one more leaf value.",
    "cases": [
        {
            "input": {
                "action": "chart_values",
                "args": [],
                "mtls": true,
                "ca": "1",
                "issuer_cert": "2",
                "issuer_key": "3"
            },
            "expected_output": "value_count=2\n"
        },
        {
            "input": {
                "action": "chart_values",
                "args": [
                    "a=b",
                    "c=d"
                ],
                "mtls": true,
                "ca": "1",
                "issuer_cert": "2",
                "issuer_key": "3"
            },
            "expected_output": "value_count=4\n"
        }
    ]
}
```

---

### Feature 17: Version Downgrade Detection

**As a developer**, I want to know whether moving from the installed version to a target version is a downgrade, so upgrade tooling can warn before stepping backwards.

**Expected Behavior / Usage:**

Decide whether moving from an existing runtime version to a target version constitutes a downgrade, using semantic-version ordering. Moving to a strictly lower version is a downgrade — even when the existing version is a pre-release of a higher version. Moving to an equal or higher version is not. Output is a single line `downgrade=<true|false>`.

**Test Cases:** `rcb_tests/public_test_cases/feature17_is_downgrade.json`

```json
{
    "description": "Decide whether moving from an existing runtime version to a target version constitutes a downgrade, using semantic-version ordering. Moving to a lower version is a downgrade even when the existing version is a pre-release of a higher version; moving to an equal or higher version is not.",
    "cases": [
        {
            "input": {
                "action": "is_downgrade",
                "target_version": "1.3.0",
                "existing_version": "1.4.0-rc.5"
            },
            "expected_output": "downgrade=true\n"
        },
        {
            "input": {
                "action": "is_downgrade",
                "target_version": "1.4.0-rc.5",
                "existing_version": "1.3.0"
            },
            "expected_output": "downgrade=false\n"
        }
    ]
}
```

---

### Feature 18: Component Definition Serialization

**As a developer**, I want stored component definitions serialized into machine-readable output, so I can list cluster components in YAML or JSON.

**Expected Behavior / Usage:**

Serialize stored component definitions into the requested output format (`yaml` or `json`). A single definition serializes as one object; multiple definitions serialize as a sequence/array. Each definition renders its name, namespace, and a spec carrying the component type, version, and the default spec fields. When the upstream lookup fails, output is `error=fetch_failed`. Output is the raw serialized document.

**Test Cases:** `rcb_tests/public_test_cases/feature18_component_serialization.json`

```json
{
    "description": "Serialize stored component definitions into the requested machine-readable output format (yaml or json). A single definition serializes as one object; multiple definitions serialize as a sequence/array. The reserved system component is filtered out, and an optional name filter narrows the set. When the upstream lookup fails, a neutral fetch error is reported.",
    "cases": [
        {
            "input": {
                "action": "render_components",
                "format": "yaml",
                "components": [
                    {
                        "name": "appConfig",
                        "namespace": "",
                        "type": "state.redis",
                        "version": "v1"
                    }
                ]
            },
            "expected_output": "name: appConfig\nnamespace: \"\"\nspec:\n  type: state.redis\n  version: v1\n  ignoreerrors: false\n  metadata: []\n  inittimeout: \"\"\n"
        },
        {
            "input": {
                "action": "render_components",
                "format": "json",
                "components": [
                    {
                        "name": "appConfig",
                        "namespace": "",
                        "type": "state.redis",
                        "version": "v1"
                    }
                ]
            },
            "expected_output": "{\n  \"name\": \"appConfig\",\n  \"namespace\": \"\",\n  \"spec\": {\n    \"type\": \"state.redis\",\n    \"version\": \"v1\",\n    \"ignoreErrors\": false,\n    \"metadata\": null,\n    \"initTimeout\": \"\"\n  }\n}"
        },
        {
            "input": {
                "action": "render_components",
                "format": "yaml",
                "fetch_error": true
            },
            "expected_output": "error=fetch_failed\n"
        }
    ]
}
```

---

### Feature 19: Configuration Definition Serialization

**As a developer**, I want stored configuration definitions serialized into machine-readable output, so I can list cluster configurations in YAML or JSON with all default sections rendered.

**Expected Behavior / Usage:**

Serialize stored configuration definitions into the requested output format (`yaml` or `json`). A single definition serializes as one object; multiple definitions serialize as a sequence/array. Each definition renders its name, namespace, and the full configuration spec with all nested default sections (tracing, metrics, mTLS, secrets, access control, name resolution, API, components, and pipelines). When the upstream lookup fails, output is `error=fetch_failed`. Output is the raw serialized document.

**Test Cases:** `rcb_tests/public_test_cases/feature19_configuration_serialization.json`

```json
{
    "description": "Serialize stored configuration definitions into the requested machine-readable output format (yaml or json). A single definition serializes as one object; multiple definitions serialize as a sequence/array of the full configuration spec with all nested default sections rendered. When the upstream lookup fails, a neutral fetch error is reported.",
    "cases": [
        {
            "input": {
                "action": "render_configurations",
                "format": "yaml",
                "configurations": [
                    {
                        "name": "appConfig",
                        "namespace": "default"
                    }
                ]
            },
            "expected_output": "name: appConfig\nnamespace: default\nspec:\n  apphttppipelinespec:\n    handlers: []\n  httppipelinespec:\n    handlers: []\n  tracingspec:\n    samplingrate: \"\"\n    stdout: false\n    zipkin:\n      endpointaddresss: \"\"\n    otel:\n      protocol: \"\"\n      endpointAddress: \"\"\n      isSecure: false\n  metricspec:\n    enabled: false\n  mtlsspec:\n    enabled: false\n    workloadcertttl: \"\"\n    allowedclockskew: \"\"\n  secrets:\n    scopes: []\n  accesscontrolspec:\n    defaultAction: \"\"\n    trustDomain: \"\"\n    policies: []\n  nameresolutionspec:\n    component: \"\"\n    version: \"\"\n    configuration:\n      json:\n        raw: []\n  features: []\n  apispec:\n    allowed: []\n  componentsspec: {}\n"
        },
        {
            "input": {
                "action": "render_configurations",
                "format": "json",
                "configurations": [
                    {
                        "name": "appConfig",
                        "namespace": "default"
                    }
                ]
            },
            "expected_output": "{\n  \"name\": \"appConfig\",\n  \"namespace\": \"default\",\n  \"spec\": {\n    \"appHttpPipeline\": {\n      \"handlers\": null\n    },\n    \"httpPipeline\": {\n      \"handlers\": null\n    },\n    \"tracing\": {\n      \"samplingRate\": \"\",\n      \"stdout\": false,\n      \"zipkin\": {\n        \"endpointAddress\": \"\"\n      },\n      \"otel\": {\n        \"protocol\": \"\",\n        \"endpointAddress\": \"\",\n        \"isSecure\": false\n      }\n    },\n    \"metric\": {\n      \"enabled\": false\n    },\n    \"mtls\": {\n      \"enabled\": false,\n      \"workloadCertTTL\": \"\",\n      \"allowedClockSkew\": \"\"\n    },\n    \"secrets\": {\n      \"scopes\": null\n    },\n    \"accessControl\": {\n      \"defaultAction\": \"\",\n      \"trustDomain\": \"\",\n      \"policies\": null\n    },\n    \"nameResolution\": {\n      \"component\": \"\",\n      \"version\": \"\",\n      \"configuration\": null\n    },\n    \"api\": {},\n    \"components\": {}\n  }\n}"
        },
        {
            "input": {
                "action": "render_configurations",
                "format": "yaml",
                "fetch_error": true
            },
            "expected_output": "error=fetch_failed\n"
        }
    ]
}
```

---

### Feature 20: Control-Plane Status Reporting

**As a developer**, I want the health of the control-plane services reported as a compact table, so I can see at a glance whether the cluster runtime is healthy.

**Expected Behavior / Usage:**

Report the health status of the control-plane services. Pods are grouped by their service identity; replicas of the same service are aggregated into a single row carrying a replica count. Each row reports the service name, the control-plane namespace, readiness (`healthy=True|False`), lifecycle status (`Running`, `Pending`, `Terminated`, or `Waiting (<reason>)`), the replica count, the running image version, and a human-readable age (e.g. `20m`, `0s`). Each field is emitted as a `key=value` line; multiple rows are concatenated. Querying through an uninitialized client yields `error=client_not_initialized`.

**Test Cases:** `rcb_tests/public_test_cases/feature20_control_plane_status.json`

```json
{
    "description": "Report the health status of the control-plane services running in the cluster. Pods are grouped by their service identity; replicas of the same service are aggregated into a single row with a replica count. Each row reports readiness (healthy True/False), lifecycle status (Running, Pending, Terminated, or Waiting with its reason), the running image version, and a human-readable age. Querying through an uninitialized client surfaces a neutral error category.",
    "cases": [
        {
            "input": {
                "action": "control_plane_status",
                "pods": [
                    {
                        "name": "dapr-dashboard-58877dbc9d-n8qg2",
                        "app": "dapr-dashboard",
                        "age_minutes": 20,
                        "state": "running",
                        "ready": true
                    }
                ]
            },
            "expected_output": "name=dapr-dashboard\nnamespace=dapr-system\nhealthy=True\nstatus=Running\nreplicas=1\nversion=0.0.1\nage=20m\n"
        },
        {
            "input": {
                "action": "control_plane_status",
                "pods": [
                    {
                        "name": "dapr-dashboard-58877dbc9d-n8qg2",
                        "app": "dapr-dashboard",
                        "age_minutes": 0,
                        "state": "waiting",
                        "reason": "test",
                        "ready": false
                    }
                ]
            },
            "expected_output": "name=dapr-dashboard\nnamespace=dapr-system\nhealthy=False\nstatus=Waiting (test)\nreplicas=1\nversion=0.0.1\nage=0s\n"
        },
        {
            "input": {
                "action": "control_plane_status",
                "pods": [
                    {
                        "name": "dapr-operator-67d7d7bb6c-7h96c",
                        "app": "dapr-operator",
                        "age_minutes": 20,
                        "state": "running",
                        "ready": true
                    },
                    {
                        "name": "dapr-operator-67d7d7bb6c-2h96d",
                        "app": "dapr-operator",
                        "age_minutes": 20,
                        "state": "running",
                        "ready": true
                    },
                    {
                        "name": "dapr-operator-67d7d7bb6c-3h96c",
                        "app": "dapr-operator",
                        "age_minutes": 20,
                        "state": "running",
                        "ready": true
                    },
                    {
                        "name": "dapr-sentry-647759cd46-9ptks",
                        "app": "dapr-sentry",
                        "age_minutes": 20,
                        "state": "running",
                        "ready": true
                    }
                ]
            },
            "expected_output": "name=dapr-operator\nnamespace=dapr-system\nhealthy=True\nstatus=Running\nreplicas=3\nversion=0.0.1\nage=20m\nname=dapr-sentry\nnamespace=dapr-system\nhealthy=True\nstatus=Running\nreplicas=1\nversion=0.0.1\nage=20m\n"
        },
        {
            "input": {
                "action": "control_plane_status",
                "empty_client": true
            },
            "expected_output": "error=client_not_initialized\n"
        }
    ]
}
```

---

### Feature 21: Label-Selector Pod Listing

**As a developer**, I want pods filtered by a label selector, so the tool can find exactly the workloads that carry a given set of labels.

**Expected Behavior / Usage:**

List the pods whose labels match a given label selector. Only pods carrying every key/value pair of the selector are returned. Output is a `matched=<n>` count line followed by one `pod=<name>\t<namespace>` line per match. An empty cluster, or no matches, yields `matched=0` with no further lines.

**Test Cases:** `rcb_tests/public_test_cases/feature21_pod_listing.json`

```json
{
    "description": "List the pods in the cluster whose labels match a given label selector. Only pods carrying every key/value pair of the selector are returned; each match is reported as a name/namespace pair. An empty cluster (or no matches) yields a zero match count.",
    "cases": [
        {
            "input": {
                "action": "list_pods",
                "pods": [],
                "selector": {
                    "test": "test"
                }
            },
            "expected_output": "matched=0\n"
        },
        {
            "input": {
                "action": "list_pods",
                "pods": [
                    {
                        "name": "test",
                        "namespace": "test",
                        "labels": {
                            "test": "test"
                        }
                    }
                ],
                "selector": {
                    "test": "test"
                }
            },
            "expected_output": "matched=1\npod=test\ttest\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-module codebase implementing the features above, with the local-run, image/registry, event/invocation, release-resolution, cluster-annotation, and cluster-status/serialization domains kept in distinct logical units. The structure must align with the "Scale-Driven Code Organization" constraint — no monolithic file.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core. It reads one JSON command object from stdin, dispatches on its `action` field, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. All errors are rendered as neutral category lines (e.g. `error=app_not_found`, `error=parse_error`, `error=missing_field` with a `field=` line) — never host-language exception identities. This adapter must be logically and physically separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory of case files (default `test_cases`). For each case it feeds the `input` to the adapter on stdin and writes the raw program stdout to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_container_runtime.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_container_runtime@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout of the program under test (no PASS/FAIL summaries or metadata), so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the standard format pattern from the control_plane_status rows
- return the error format defined at the top of C063
