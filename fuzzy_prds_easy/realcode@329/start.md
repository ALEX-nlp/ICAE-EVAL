## Product Requirement Document

# Service Mesh Proxy Configuration Engine — Control-Plane Configuration Builder

## Project Goal

Build a configuration engine for a service-mesh control plane that translates per-instance proxy metadata and server-side policy settings into deterministic proxy configuration artifacts (routing tags, dependency descriptors, traffic groups, route configurations, and change-detection versions), so platform teams can drive sidecar proxies from declarative input without hand-writing low-level proxy config.

---

## Background & Problem

Without such an engine, operators of a service mesh must hand-assemble low-level proxy configuration (route tables, cluster references, retry policies, header rules) for every service instance and keep it consistent with server-side policy. This is repetitive, error-prone, and hard to evolve: a small policy change forces wide manual edits, and there is no principled way to tell connected proxies that their configuration changed.

With this engine, an instance advertises a small structured metadata document (its dependencies, incoming permissions, timeouts, health check), the server supplies global policy (which modes and permissions are enabled, retry defaults, tag-routing rules), and the engine deterministically derives the routing tags, validated dependency descriptors, the traffic group the instance belongs to, the egress/ingress route configurations, and stable version identifiers used for change detection.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility domain (metadata parsing, validation, group assignment, route building, versioning). It MUST be organized as a clear multi-file tree (e.g. parsing/model, policy/validation, routing, versioning, and a thin execution adapter) rather than a single monolithic file. Do not over-engineer, but do not collapse distinct responsibilities together.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a black-box contract for the execution adapter, NOT the internal data model. Core logic must be decoupled from stdin/stdout and JSON parsing. The adapter alone translates a JSON request into idiomatic calls on the core domain and renders results back to the line-based stdout contract.

3. **Adherence to SOLID Design Principles:** Separate parsing, policy validation, group assignment, route construction, version tracking, and output formatting into distinct cohesive units. The core builders must be open for extension (new policy fields, new route kinds) but closed for modification, depend on abstractions, and keep interfaces small.

4. **Robustness & Interface Design:** The public interface must be idiomatic to the target language and hide internal complexity. Invalid input must be modeled with explicit domain error types (not generic faults). Every error surfaced through the adapter MUST be rendered as a neutral category line (see contracts), never as a host-language runtime artifact.

---

## Core Features

### Feature 1: Routing Tag Derivation

**As a** mesh operator, **I want** raw instance tags transformed into the set of tags usable for request routing, **so that** I can route by meaningful attributes and attribute combinations while suppressing noisy or sensitive tags.

**Expected Behavior / Usage:**

The input is a service name, the set of raw tags on an instance, a blacklist of tag patterns (full-match regular expressions), and a list of per-service "allowed combination" rules (each a service name plus 2 or 3 tag patterns). First, every raw tag matching any blacklist pattern is discarded. If nothing survives, emit the single line `tags=none`. Otherwise the surviving single tags are always kept. For a service that has two-tag combination rules, additionally emit a joined value `a,b` for every surviving pair of tags that matches an allowed pair of patterns; the two members inside a joined value are ordered ascending. For a service that has three-tag combination rules, additionally emit the joined two-tag values for every matching sub-pair and the joined three-tag value for each matching triple. Output is one `tag=<value>` line per resulting tag, sorted ascending.

**Test Cases:** `rcb_tests/public_test_cases/feature1_tag_routing.json`

```json
{
    "description": "Tag routing transformation: blacklist filtering of raw tags, plus per-service two/three-tag combination expansion; emits sorted 'tag=<value>' lines or 'tags=none' when nothing survives.",
    "cases": [
        {"input": {"op": "tag_routing", "serviceName": "regular-service", "excludedTags": [".*id.*", "port:.*", "envoy"], "allowedCombinations": [], "tags": ["id:332", "hardware:c32", "stage:dev", "version:v0.9", "env12", "port:1244", "gport:1245", "envoy", "envoy-test"]}, "expected_output": "tag=env12\ntag=envoy-test\ntag=gport:1245\ntag=hardware:c32\ntag=stage:dev\ntag=version:v0.9\n"},
        {"input": {"op": "tag_routing", "serviceName": "two-tags-allowed-service", "excludedTags": [".*id.*", "port:.*", "envoy"], "allowedCombinations": [{"serviceName": "two-tags-allowed-service", "tags": ["hardware:.*", "version:.*"]}, {"serviceName": "two-tags-allowed-service", "tags": ["stage:.*", "version:.*"]}, {"serviceName": "three-tags-allowed-service", "tags": ["stage:.*", "version:.*", "hardware:.*"]}], "tags": ["service-id:332", "hardware:c32", "stage:dev", "version:v0.9", "env12"]}, "expected_output": "tag=env12\ntag=hardware:c32\ntag=hardware:c32,version:v0.9\ntag=stage:dev\ntag=stage:dev,version:v0.9\ntag=version:v0.9\n"}
    ]
}
```

---

### Feature 2: Outgoing Dependency Descriptors

**As a** service owner, **I want** my declared outgoing dependencies parsed and validated into typed descriptors, **so that** the mesh can route my egress traffic to other services or external domains with correct defaults.

**Expected Behavior / Usage:**

*2.1 Service dependency parsing — a dependency that targets another service by name.*

A service dependency carries the target service name, an internal-redirect flag (default false), and a timeout policy with idle and request timeouts supplied as duration strings such as `10s`. Any omitted timeout falls back to a default duration. Output reports `[a specific set of default timeout configurations referenced in the error handling module]` and the resolved service name, redirect flag, and effective idle/request timeouts.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_outgoing_service_dependency.json`

```json
{
    "description": "Parse an outgoing service dependency into name + redirect flag + idle/request timeouts (omitted timeouts fall back to a default).",
    "cases": [
        {"input": {"op": "outgoing_dependency", "service": "my-service"}, "expected_output": "[a specific set of default timeout configurations referenced in the error handling module]\nservice=my-service\n[a specific set of default timeout configurations referenced in the error handling module]\n[a fallback default timeout value defined elsewhere in the configuration specs]\n[a fallback default timeout value defined elsewhere in the configuration specs]\n"},
        {"input": {"op": "outgoing_dependency", "service": "service-1", "idleTimeout": "10s"}, "expected_output": "[a specific set of default timeout configurations referenced in the error handling module]\nservice=service-1\n[a specific set of default timeout configurations referenced in the error handling module]\nidleTimeout=10s\n[a fallback default timeout value defined elsewhere in the configuration specs]\n"}
    ]
}
```

*2.2 Domain dependency parsing — a dependency that targets an absolute URL.*

Only `http` and `https` schemes are accepted. The engine derives the host, the effective port (explicit port if present, otherwise the scheme default), a cluster name made by joining host and port and replacing every dot and colon with an underscore, and a route domain that includes the port only when it was given explicitly. Output reports `type=domain` and the derived host/port/cluster/route-domain.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_outgoing_domain_dependency.json`

```json
{
    "description": "Parse an outgoing domain dependency into host, effective port, underscore-joined cluster name, and route domain (port shown only if explicit).",
    "cases": [
        {"input": {"op": "outgoing_dependency", "domain": "http://domain.pl"}, "expected_output": "type=domain\ndomain=http://domain.pl\nhost=domain.pl\nport=80\ncluster=domain_pl_80\nrouteDomain=domain.pl\n[a specific set of default timeout configurations referenced in the error handling module]\n"},
        {"input": {"op": "outgoing_dependency", "domain": "http://domain.pl:80"}, "expected_output": "type=domain\ndomain=http://domain.pl:80\nhost=domain.pl\nport=80\ncluster=domain_pl_80\nrouteDomain=domain.pl:80\n[a specific set of default timeout configurations referenced in the error handling module]\n"}
    ]
}
```

*2.3 Dependency validation errors — exactly one valid target is required.*

A dependency must declare exactly one of service or domain. Declaring neither or both fails with `error=invalid_dependency_target`. A domain with an unsupported scheme fails with `error=unsupported_domain_protocol` and echoes the offending domain on its own `domain=` field. Errors are neutral category lines.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_outgoing_dependency_validation.json`

```json
{
    "description": "Reject dependencies that declare neither/both target kinds, or a domain with an unsupported scheme; emit neutral error category lines.",
    "cases": [
        {"input": {"op": "outgoing_dependency"}, "expected_output": "error=invalid_dependency_target\n"},
        {"input": {"op": "outgoing_dependency", "domain": "ftp://domain"}, "expected_output": "error=unsupported_domain_protocol\ndomain=ftp://domain\n"}
    ]
}
```

*2.4 Dependency membership lookup — does a dependency exist for a given service?*

Given a set of declared service dependencies, the model answers whether a dependency for a particular service name is present. Output reports one `<name>=<true|false>` line per query.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_dependency_membership.json`

```json
{
    "description": "Report presence/absence of a service dependency by name over the declared dependency set.",
    "cases": [
        {"input": {"op": "contains_dependency", "dependencies": [{"service": "service-first", "handleInternalRedirect": true}], "queries": ["service-first", "service-second"]}, "expected_output": "service-first=true\nservice-second=false\n"}
    ]
}
```

---

### Feature 3: Incoming Endpoint Path Parsing

**As a** service owner, **I want** my incoming endpoint declarations validated for path matching, **so that** ingress routing has an unambiguous match rule per endpoint.

**Expected Behavior / Usage:**

An incoming endpoint declares either an exact `path` or a `pathPrefix`, but exactly one. Declaring both fails with `error=path_conflict`; declaring neither fails with `error=path_missing`. A field present with an explicit null value is treated as absent, so a real path with a null prefix is valid (matches by exact path) and a null path with a real prefix is valid (matches by prefix). On success, output reports the resolved path value and the matching type (`PATH` or `PATH_PREFIX`).

**Test Cases:** `rcb_tests/public_test_cases/feature3_incoming_endpoint_path.json`

```json
{
    "description": "Validate incoming endpoint path vs pathPrefix (exactly one required; explicit null treated as absent); report resolved path and matching type or a neutral error.",
    "cases": [
        {"input": {"op": "incoming_endpoint", "path": "/path", "pathPrefix": "/prefix"}, "expected_output": "error=path_conflict\n"},
        {"input": {"op": "incoming_endpoint", "pathPrefix": "/prefix", "includeNullFields": true}, "expected_output": "path=/prefix\nmatchingType=PATH_PREFIX\n"}
    ]
}
```

---

### Feature 4: Incoming Health-Check Settings

**As a** service owner, **I want** my incoming health-check definition parsed with sensible defaults, **so that** the mesh can route health probes to the right local cluster.

**Expected Behavior / Usage:**

The incoming settings may carry a health-check path and cluster name. The cluster name defaults to a fixed local value when not supplied. A health check counts as custom only when a non-blank path is configured; an absent or empty path yields an empty path and a non-custom health check. Output reports the resolved cluster name, the path, and whether the health check is custom.

**Test Cases:** `rcb_tests/public_test_cases/feature4_health_check_settings.json`

```json
{
    "description": "Parse incoming health-check path + cluster (cluster name defaulted); 'custom' is true only for a non-blank path.",
    "cases": [
        {"input": {"op": "health_check", "path": "/path", "healthCheckPath": "/status/ping", "healthCheckClusterName": "local_service_health_check"}, "expected_output": "clusterName=local_service_health_check\npath=/status/ping\ncustom=true\n"},
        {"input": {"op": "health_check", "path": "/path"}, "expected_output": "clusterName=local_service_health_check\npath=\ncustom=false\n"}
    ]
}
```

---

### Feature 5: Traffic Group Assignment

**As a** control-plane operator, **I want** each connecting instance assigned to a traffic group derived from its metadata and the active policy, **so that** instances sharing the same effective configuration are grouped consistently.

**Expected Behavior / Usage:**

A node advertises its outgoing service dependencies, whether it uses the aggregated stream mode (`ads` true) or separate streams (`ads` false), optionally a service name and incoming settings (endpoints, timeouts, health check). The output of grouping is summarized as: group type (all-services vs listed-services), communication mode (`ADS`/`XDS`), service name, the sorted retained service dependencies, and the incoming-section summary (permissions flag, endpoints, health-check path/cluster, response/idle timeouts). Endpoints in the summary are rendered as `path|matchingType|methods=[...]|clients=[...]` and sorted.

*5.1 Assignment by declared dependencies.*

The node is assigned to an all-services group when it requests the wildcard "all dependencies" value, or when outgoing permissions are disabled (in which case all explicitly listed dependencies are still retained); otherwise it is assigned to a listed-services group. The communication mode is preserved. Even when the wildcard is present, every explicitly listed dependency is retained. With incoming settings not enabled, the incoming summary is empty.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_group_assignment_by_dependencies.json`

```json
{
    "description": "Assign node to all-services vs listed-services group from its dependencies and the outgoing-permissions policy; preserve mode and retain all listed dependencies.",
    "cases": [
        {"input": {"op": "node_group", "outgoingPermissions": true, "serviceDependencies": ["*", "a", "b", "c"], "ads": false}, "expected_output": "type=AllServicesGroup\nmode=XDS\nserviceName=\ndeps=[*,a,b,c]\nincoming.permissionsEnabled=false\nincoming.endpoints=[]\nincoming.healthCheck.path=\nincoming.healthCheck.cluster=local_service_health_check\nincoming.timeout.response=none\nincoming.timeout.idle=none\n"},
        {"input": {"op": "node_group", "outgoingPermissions": true, "serviceDependencies": ["a", "b", "c"], "ads": false}, "expected_output": "type=ServicesGroup\nmode=XDS\nserviceName=\ndeps=[a,b,c]\nincoming.permissionsEnabled=false\nincoming.endpoints=[]\nincoming.healthCheck.path=\nincoming.healthCheck.cluster=local_service_health_check\nincoming.timeout.response=none\nincoming.timeout.idle=none\n"}
    ]
}
```

*5.2 Incoming settings gated by permissions.*

Incoming settings are included in the resolved group only when incoming permissions are enabled. When disabled, the service name is cleared and the incoming section is stripped to its empty default even if the node supplied endpoints. When enabled, the service name and incoming endpoints are retained.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_group_incoming_permissions_gating.json`

```json
{
    "description": "Include incoming settings (service name, endpoints) only when incoming permissions are enabled; otherwise strip them to defaults.",
    "cases": [
        {"input": {"op": "node_group", "outgoingPermissions": true, "serviceDependencies": ["a", "b", "c"], "ads": false, "serviceName": "app1", "incomingSettings": true}, "expected_output": "type=ServicesGroup\nmode=XDS\nserviceName=\ndeps=[a,b,c]\nincoming.permissionsEnabled=false\nincoming.endpoints=[]\nincoming.healthCheck.path=\nincoming.healthCheck.cluster=local_service_health_check\nincoming.timeout.response=none\nincoming.timeout.idle=none\n"},
        {"input": {"op": "node_group", "outgoingPermissions": true, "incomingPermissions": true, "serviceDependencies": ["a", "b"], "ads": true, "serviceName": "app1", "incomingSettings": true}, "expected_output": "type=ServicesGroup\nmode=ADS\nserviceName=app1\ndeps=[a,b]\nincoming.permissionsEnabled=true\nincoming.endpoints=[/endpoint|PATH|methods=[]|clients=[client1]]\nincoming.healthCheck.path=\nincoming.healthCheck.cluster=local_service_health_check\nincoming.timeout.response=none\nincoming.timeout.idle=none\n"}
    ]
}
```

*5.3 Timeout policy and custom health-check parsing during grouping.*

When incoming permissions are enabled and the node supplies incoming settings, the resolved group carries the parsed incoming timeout policy (response/idle timeouts from duration strings such as `777s`, `13.33s`) and the parsed health-check (path and cluster).

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_group_timeout_and_healthcheck_parsing.json`

```json
{
    "description": "Parse incoming response/idle timeouts (duration strings) during group resolution.",
    "cases": [
        {"input": {"op": "node_group", "outgoingPermissions": true, "serviceDependencies": ["*"], "ads": true, "incomingSettings": true, "responseTimeout": "777s", "idleTimeout": "13.33s"}, "expected_output": "type=AllServicesGroup\nmode=ADS\nserviceName=\ndeps=[*]\nincoming.permissionsEnabled=false\nincoming.endpoints=[]\nincoming.healthCheck.path=\nincoming.healthCheck.cluster=local_service_health_check\nincoming.timeout.response=777s\nincoming.timeout.idle=13.330s\n"}
    ]
}
```

---

### Feature 6: Wildcard Dependency Authorization

**As a** platform security owner, **I want** the "all dependencies" wildcard restricted to an allow-list of services, **so that** only sanctioned services may depend on everything.

**Expected Behavior / Usage:**

When outgoing permissions are enabled, a request that asks for the wildcard "all dependencies" value from a service NOT on the allow-list is rejected with `error=wildcard_not_allowed` and the offending service name. An allow-listed service is accepted. When outgoing permissions are disabled the check is skipped and the request is accepted. Decisions are emitted as `result=accepted` or the neutral error line.

**Test Cases:** `rcb_tests/public_test_cases/feature6_wildcard_authorization.json`

```json
{
    "description": "Allow the all-dependencies wildcard only for allow-listed services when outgoing permissions are enabled; emit neutral accept/reject decisions.",
    "cases": [
        {"input": {"op": "wildcard_auth", "outgoingPermissions": true, "servicesAllowedToUseWildcard": ["vis-1", "vis-2"], "serviceDependencies": ["*", "a", "b", "c"], "serviceName": "regular-1"}, "expected_output": "error=wildcard_not_allowed\nservice=regular-1\n"},
        {"input": {"op": "wildcard_auth", "outgoingPermissions": true, "servicesAllowedToUseWildcard": ["vis-1", "vis-2"], "serviceDependencies": ["*", "a", "b", "c"], "serviceName": "vis-1"}, "expected_output": "result=accepted\n"}
    ]
}
```

---

### Feature 7: Communication-Mode Compatibility Validation

**As a** control-plane operator, **I want** a connecting instance rejected if it requests a streaming mode the server does not support, **so that** mismatched clients fail fast with a clear reason.

**Expected Behavior / Usage:**

The server advertises which modes it supports: aggregated (`ads`) and/or separate (`xds`). An instance requests the aggregated mode when `ads` is true and the separate mode otherwise. If the requested mode is unsupported, reject with `error=mode_not_supported` and the mode name (`ADS` or `XDS`); otherwise accept. Decisions are emitted as `result=accepted` or the neutral error line.

**Test Cases:** `rcb_tests/public_test_cases/feature7_communication_mode_validation.json`

```json
{
    "description": "Reject an instance requesting a streaming mode not supported by the server, naming the mode; accept otherwise.",
    "cases": [
        {"input": {"op": "communication_mode", "adsSupported": false, "xdsSupported": true, "ads": true, "serviceDependencies": ["a", "b", "c"], "serviceName": "regular-1"}, "expected_output": "error=mode_not_supported\nmode=ADS\n"},
        {"input": {"op": "communication_mode", "adsSupported": true, "xdsSupported": false, "ads": false, "serviceDependencies": ["a", "b", "c"], "serviceName": "regular-1"}, "expected_output": "error=mode_not_supported\nmode=XDS\n"}
    ]
}
```

---

### Feature 8: Configuration Change Versioning

**As a** control-plane operator, **I want** stable opaque version identifiers for the cluster set and endpoint set of each group, **so that** connected proxies can detect exactly what changed.

**Expected Behavior / Usage:**

A versioning component assigns a cluster-version and an endpoint-version per group identity. The same group with unchanged clusters and endpoints keeps the same versions; changing only the endpoints produces a new endpoint version but the same cluster version; changing the clusters produces a new cluster version and also a new endpoint version. A group is identified by its full identity, so two different groups never share versions, and forgetting a group (retaining an empty set) forces fresh versions next time. Because the raw identifiers are random, the output abstracts each distinct cluster-version value seen, in order, into labels `c0, c1, ...` and each distinct endpoint-version value into `e0, e1, ...`. Each version step prints `step=<n> clusters=<label> endpoints=<label>`, so equality/inequality across steps is observable without leaking the random values.

**Test Cases:** `rcb_tests/public_test_cases/feature8_snapshot_versions.json`

```json
{
    "description": "Per-group cluster/endpoint version tracking: endpoint-only change bumps endpoints; same group unchanged keeps both; abstracted to stable labels c*/e*.",
    "cases": [
        {"input": {"op": "snapshot_versions", "steps": [{"action": "version", "group": {"kind": "all"}, "clusters": ["service1"], "endpoints": [{"cluster": "service1", "instances": 1}]}, {"action": "version", "group": {"kind": "all"}, "clusters": ["service1"], "endpoints": [{"cluster": "service1", "instances": 2}]}]}, "expected_output": "step=0 clusters=c0 endpoints=e0\nstep=1 clusters=c0 endpoints=e1\n"},
        {"input": {"op": "snapshot_versions", "steps": [{"action": "version", "group": {"kind": "path", "path": "/path"}, "clusters": ["service1"], "endpoints": [{"cluster": "service1", "instances": 1}]}, {"action": "version", "group": {"kind": "path", "path": "/path"}, "clusters": ["service1"], "endpoints": [{"cluster": "service1", "instances": 1}]}]}, "expected_output": "step=0 clusters=c0 endpoints=e0\nstep=1 clusters=c0 endpoints=e0\n"}
    ]
}
```

---

### Feature 9: Egress Route Configuration

**As a** service owner, **I want** an egress route configuration built for my outgoing calls, **so that** caller identity and upstream-address exposure are applied according to policy.

**Expected Behavior / Usage:**

For a calling service and a set of upstream route specifications (cluster name, route domain, redirect flag, optional idle/request timeouts), the engine builds a route configuration. When incoming permissions are enabled, a request header carrying the caller's identity (`x-service-name=<caller>`) is added; when disabled it is omitted. When the upstream-remote-address flag is set, a response header `x-envoy-upstream-remote-address=%UPSTREAM_REMOTE_ADDRESS%` is added; otherwise omitted. The first generated virtual host's first route targets the given cluster and carries the configured idle and request timeouts. Output reports the sorted request headers, sorted response headers, and the first route's cluster and timeouts.

**Test Cases:** `rcb_tests/public_test_cases/feature9_egress_route_headers.json`

```json
{
    "description": "Build egress route config: add caller-identity request header only when incoming permissions enabled; add upstream-address response header only when requested; first route carries cluster + timeouts.",
    "cases": [
        {"input": {"op": "egress_routes", "incomingPermissionsEnabled": true, "serviceName": "client1", "addUpstreamAddressHeader": false, "clusters": [{"clusterName": "srv1", "routeDomain": "srv1", "handleInternalRedirect": true, "idleTimeout": "10s", "requestTimeout": "10s"}]}, "expected_output": "requestHeaders=[x-service-name=client1]\nresponseHeaders=[]\nroute0.cluster=srv1\nroute0.idleTimeout=10s\nroute0.requestTimeout=10s\n"},
        {"input": {"op": "egress_routes", "incomingPermissionsEnabled": false, "serviceName": "client1", "addUpstreamAddressHeader": true, "clusters": [{"clusterName": "srv1", "routeDomain": "srv1", "handleInternalRedirect": true, "idleTimeout": "10s", "requestTimeout": "10s"}]}, "expected_output": "requestHeaders=[]\nresponseHeaders=[x-envoy-upstream-remote-address=%UPSTREAM_REMOTE_ADDRESS%]\nroute0.cluster=srv1\nroute0.idleTimeout=10s\nroute0.requestTimeout=10s\n"}
    ]
}
```

---

### Feature 10: Secured Ingress Route Configuration

**As a** service owner, **I want** a secured ingress route configuration built from status/admin policy and retry policy, **so that** local-service traffic, admin endpoints, and health checks are routed and protected consistently.

**Expected Behavior / Usage:**

Inputs are: whether the status route and its virtual cluster are enabled, whether public admin access is enabled together with an admin token and a list of secured admin sub-paths (path prefix + method), the per-incoming timeout policy and health-check, a default retry policy, and a map of per-method retry policies. The single virtual host matches all domains; when status virtual clusters are enabled it exposes `status` and `endpoints` virtual clusters. When the default retry policy is enabled it is attached to the virtual host with its retry-on conditions joined by commas and its retry count. Generated routes appear in this order: for each secured admin sub-path, an authorized route gated on the token followed by an unauthorized fallback returning status 401; then (when public admin access is enabled) the admin POST authorized/unauthorized routes, the admin catch-all route, and the admin redirect route; then one local-service route per enabled per-method retry policy (each matching that method and carrying a retry policy); and finally a catch-all local-service route without a retry policy. Output reports the route-config name, virtual-host name, sorted domains, virtual-cluster names, the virtual-host retry-on string and retry count, the route count, and per route: the path prefix, matched method(s), the action (cluster target, direct-response status, or redirect), and whether it carries a retry policy.

**Test Cases:** `rcb_tests/public_test_cases/feature10_ingress_route_config.json`

```json
{
    "description": "Build secured ingress route config: status virtual clusters, token-gated admin routes with 401 fallbacks, public admin routes, per-method retry routes, and a catch-all local route, in a fixed order.",
    "cases": [
        {"input": {"op": "ingress_routes", "statusEnabled": true, "createVirtualCluster": true, "adminPublicAccess": true, "adminToken": "test_token", "securedPaths": [{"pathPrefix": "/config_dump", "method": "GET"}], "healthCheckPath": "", "healthCheckCluster": "health_check_cluster", "responseTimeout": "777s", "idleTimeout": "61s", "connectionIdleTimeout": "120s", "defaultRetryPolicy": {"enabled": true, "retryOn": ["connection-failure"], "numRetries": 3}, "perHttpMethod": {"GET": {"enabled": true, "retryOn": ["reset", "connection-failure"], "numRetries": 1, "perTryTimeoutSeconds": 1, "hostSelectionRetryMaxAttempts": 3}, "HEAD": {"enabled": true, "retryOn": ["connection-failure"], "numRetries": 6}, "POST": {"enabled": false, "retryOn": ["connection-failure"], "numRetries": 6}}}, "expected_output": "routeConfigName=ingress_secured_routes\nvhost.name=secured_local_service\nvhost.domains=[*]\nvhost.virtualClusters=[status,endpoints]\nvhost.retryPolicy.retryOn=connection-failure\nvhost.retryPolicy.numRetries=3\nroutes=9\nroute[0] prefix=/status/envoy/config_dump method=[GET] cluster=this_admin retry=false\nroute[1] prefix=/status/envoy/config_dump method=[GET] [a specific HTTP status code indicating unauthorized access] retry=false\nroute[2] prefix=/status/envoy/ method=[POST] cluster=this_admin retry=false\nroute[3] prefix=/status/envoy/ method=[POST] [a specific HTTP status code indicating unauthorized access] retry=false\nroute[4] prefix=/status/envoy/ method=[] cluster=this_admin retry=false\nroute[5] prefix=/status/envoy method=[GET] redirect retry=false\nroute[6] prefix=/ method=[GET] cluster=local_service retry=true\nroute[7] prefix=/ method=[HEAD] cluster=local_service retry=true\nroute[8] prefix=/ method=[] cluster=local_service retry=false\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the ten features above — metadata/model parsing, policy validation, group assignment, route construction, and change versioning — decoupled from any I/O concern.

2. **The Execution/Test Adapter:** A runnable entry point that reads a single JSON request object from stdin, dispatches on its `op` field to the appropriate core logic, and prints the result to stdout, exactly matching the per-feature line-based contracts above (including neutral `error=<category>` rendering for all failures).

3. **Automated test harness:** The embedded cases live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the whole suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file `rcb_tests/stdout/<cases-dir>/{stem}@{index:03}.txt` containing only the raw program stdout, directly comparable to `expected_output`.


---
**Implementation notes:**
- follow the same pattern as the tag combination sorting utility
- populate these fields with the same sentinel values used when outgoing permissions are disabled
