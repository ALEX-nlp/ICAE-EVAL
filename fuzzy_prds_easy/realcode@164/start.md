## Product Requirement Document

# Kubernetes Service Manifest Generator - Configurable Application Deployment Manifests

## Project Goal

Build a Kubernetes manifest generation library/tool that allows developers to produce consistent application deployment, networking, scaling, storage, identity, monitoring, and extension manifests from structured configuration without hand-writing repetitive YAML.

---

## Background & Problem

Without this library/tool, developers are forced to manually assemble many related Kubernetes resources for each service, including deployments, services, ingress routes, accounts, autoscalers, disruption budgets, monitoring endpoints, volumes, and custom extensions. This leads to repetitive configuration, inconsistent labels and selectors, missed required fields, and fragile maintenance across environments.

With this library/tool, developers provide a compact configuration and receive deterministic manifest output summaries that expose the externally observable resource behavior expected by deployment automation.

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

### Feature 1: Required and Optional Values

**As a developer**, I want to validate mandatory configuration before rendering manifests, so I can avoid deploying incomplete workload definitions.

**Expected Behavior / Usage:**

The input is a JSON adapter command selecting a render target and a summary output mode. When a mandatory application identity or container image field is explicitly set to [null indicator — confirm required field handling details with platform team], stdout must contain a normalized missing-required-value error with the field name. Optional image policy fields may be omitted or [null indicator — confirm required field handling details with platform team] without causing an error, in which case stdout reports a successful render and manifest count.

**Test Cases:** `rcb_tests/public_test_cases/feature1_required_and_optional_values.json`

```json
{
    "description": "Validate that mandatory workload identity and image fields are rejected when missing, while optional image policy data may be omitted.",
    "cases": [
        {
            "input": {
                "template": "all",
                "output": "required_value_error",
                "set": {
                    "containerImage.repository": "[null indicator — confirm required field handling details with platform team]"
                }
            },
            "expected_output": "error=missing_required_value\nfield=containerImage.repository\n"
        }
    ]
}
```

---

### Feature 2: Primary Workload Container

**As a developer**, I want to render the primary workload container specification, so I can standardize image, process, port, and host-alias configuration.

**Expected Behavior / Usage:**

The input selects the deployment manifest and requests a container summary. Stdout reports the rendered workload kind, name, replica count, first container name, image, command list, argument list, host-alias count, and each declared container port with name, number, and protocol.

**Test Cases:** `rcb_tests/public_test_cases/feature2_deployment_container_spec.json`

```json
{
    "description": "Render the primary workload pod container with the configured image, port, command, arguments, and host aliases.",
    "cases": [
        {
            "input": {
                "template": "deployment",
                "output": "deployment_core",
                "set": {}
            },
            "expected_output": "kind=Deployment\nname=release-linter\nreplicas=1\ncontainer_name=linter\nimage=nginx:stable\ncommand=\nargs=\nhost_aliases=0\nport_0_name=http\nport_0_number=80\nport_0_protocol=TCP\n"
        }
    ]
}
```

---

### Feature 3: Container Environment Sources

**As a developer**, I want to inject direct and referenced environment configuration into the workload, so I can configure applications without manually editing pod specs.

**Expected Behavior / Usage:**

The input selects the deployment manifest and supplies environment configuration. Stdout reports either direct environment variables as name-value lines or external source references as ordered config-map or secret reference lines.

**Test Cases:** `rcb_tests/public_test_cases/feature3_environment_variables.json`

```json
{
    "description": "Render direct environment variables and external environment source references into the workload container.",
    "cases": [
        {
            "input": {
                "template": "deployment",
                "output": "deployment_env_vars",
                "set": {
                    "envVars.DB_HOST": "mysql.default.svc.cluster.local",
                    "envVars.DB_PORT": "3306"
                }
            },
            "expected_output": "env_count=2\nenv.DB_HOST=mysql.default.svc.cluster.local\nenv.DB_PORT=3306\n"
        }
    ]
}
```

---

### Feature 4: Config and Secret Volume Mounts

**As a developer**, I want to mount configuration and secret data into the workload filesystem, so I can provide file-based runtime configuration predictably.

**Expected Behavior / Usage:**

The input selects the deployment manifest and supplies configuration or secret volume data. Stdout reports the number of pod volumes and container mounts, each rendered volume source, and each mount path and sub-path; item paths and file modes are included when configured.

**Test Cases:** `rcb_tests/public_test_cases/feature4_config_and_secret_volumes.json`

```json
{
    "description": "Mount configuration maps and secret objects as pod volumes with optional item paths, file modes, and mount sub-paths.",
    "cases": [
        {
            "input": {
                "template": "deployment",
                "output": "deployment_config_volume",
                "set": {
                    "configMaps.dbsettings.as": "volume",
                    "configMaps.dbsettings.mountPath": "/etc/db"
                }
            },
            "expected_output": "volume_count=1\nmount_count=1\nvolume.dbsettings-volume.type=configMap\nvolume.dbsettings-volume.source=dbsettings\nmount.dbsettings-volume.path=/etc/db\nmount.dbsettings-volume.sub_path=[null indicator — confirm required field handling details with platform team]\n"
        }
    ]
}
```

---

### Feature 5: External Secret Provider Volume

**As a developer**, I want to render a CSI-backed secret provider volume, so I can consume externally managed secrets through a pod volume.

**Expected Behavior / Usage:**

The input selects the deployment manifest and supplies a secret-provider volume configuration. Stdout reports the CSI volume count, volume name, driver, read-only flag, and secret provider class.

**Test Cases:** `rcb_tests/public_test_cases/feature5_csi_secret_volume.json`

```json
{
    "description": "Render a CSI-backed secret-provider volume for workloads that retrieve secrets from an external provider.",
    "cases": [
        {
            "input": {
                "template": "deployment",
                "output": "deployment_csi_secret",
                "set": {
                    "secrets.onemoresecret.as": "csi",
                    "secrets.onemoresecret.mountPath": "/mnt/secrets-store-volume",
                    "secrets.onemoresecret.readOnly": "true",
                    "secrets.onemoresecret.csi.driver": "secrets-store.csi.k8s.io",
                    "secrets.onemoresecret.csi.secretProviderClass": "mysecretproviderclass"
                }
            },
            "expected_output": "volume_count=1\nvolume.onemoresecret-volume.type=csi\nvolume.onemoresecret-volume.driver=secrets-store.csi.k8s.io\nvolume.onemoresecret-volume.read_only=true\nvolume.onemoresecret-volume.secret_provider_class=mysecretproviderclass\n"
        }
    ]
}
```

---

### Feature 6: Container Lifecycle Hooks

**As a developer**, I want to render shutdown-delay and explicit lifecycle commands, so I can control startup and termination behavior declaratively.

**Expected Behavior / Usage:**

The input selects the deployment manifest and supplies lifecycle configuration. Stdout reports whether lifecycle data is present and prints normalized post-start and pre-stop command lists; a zero shutdown delay produces no lifecycle hook.

**Test Cases:** `rcb_tests/public_test_cases/feature6_lifecycle_hooks.json`

```json
{
    "description": "Render container lifecycle hooks from shutdown-delay settings or explicit hook command configuration.",
    "cases": [
        {
            "input": {
                "template": "deployment",
                "output": "deployment_lifecycle",
                "set": {
                    "shutdownDelay": "0"
                }
            },
            "expected_output": "lifecycle_present=[automount token boolean flag — check flag value specifics with security module]\npost_start_command=\npre_stop_command=\n"
        }
    ]
}
```

---

### Feature 7: Workload Storage Volumes

**As a developer**, I want to render scratch, persistent, empty-directory, and grace-period settings, so I can attach storage and termination behavior to the pod consistently.

**Expected Behavior / Usage:**

The input selects the deployment manifest and supplies storage or termination configuration. Stdout reports mount count, volume count, termination grace period, each mount path, each volume type, and type-specific detail such as memory-backed scratch storage or claim names.

**Test Cases:** `rcb_tests/public_test_cases/feature7_workload_storage.json`

```json
{
    "description": "Render scratch storage, persistent storage, empty directory volumes, and termination grace-period settings into the workload pod.",
    "cases": [
        {
            "input": {
                "template": "deployment",
                "output": "deployment_volumes",
                "set": {
                    "scratchPaths.scratch": "/mnt/scratch"
                }
            },
            "expected_output": "mount_count=1\nvolume_count=1\ntermination_grace_period=[null indicator — confirm required field handling details with platform team]\nmount.scratch.path=/mnt/scratch\nvolume.scratch.type=emptyDir\nvolume.scratch.detail=Memory\n"
        }
    ]
}
```

---

### Feature 8: Rollout Strategy

**As a developer**, I want to render deployment update strategy only when enabled, so I can control replacement behavior without unwanted defaults.

**Expected Behavior / Usage:**

The input selects the deployment manifest and supplies rollout strategy settings. Stdout reports the strategy type and rolling-update options; when the strategy is disabled, these fields are [null indicator — confirm required field handling details with platform team].

**Test Cases:** `rcb_tests/public_test_cases/feature8_rollout_strategy.json`

```json
{
    "description": "Render the workload rollout strategy only when enabled, including rolling-update and recreate strategy variants.",
    "cases": [
        {
            "input": {
                "template": "deployment",
                "output": "deployment_strategy",
                "set": {
                    "deploymentStrategy.enabled": "[automount token boolean flag — check flag value specifics with security module]"
                }
            },
            "expected_output": "strategy_type=[null indicator — confirm required field handling details with platform team]\nmax_surge=[null indicator — confirm required field handling details with platform team]\nmax_unavailable=[null indicator — confirm required field handling details with platform team]\n"
        }
    ]
}
```

---

### Feature 9: Workload Metadata

**As a developer**, I want to apply labels and annotations to workload and pod metadata, so I can support selectors, ownership, and automation metadata.

**Expected Behavior / Usage:**

The input selects a workload manifest and supplies metadata. Stdout reports the deployment-type labels plus additional workload labels, pod labels, workload annotations, and pod annotations.

**Test Cases:** `rcb_tests/public_test_cases/feature9_metadata_labels_annotations.json`

```json
{
    "description": "Apply additional labels and annotations to workload and pod metadata while preserving the deployment-type label.",
    "cases": [
        {
            "input": {
                "template": "deployment",
                "output": "deployment_labels",
                "set": {
                    "additionalDeploymentLabels.foo": "bar",
                    "additionalPodLabels.foo": "baz",
                    "deploymentAnnotations.foo": "ann",
                    "podAnnotations.foo": "podann"
                }
            },
            "expected_output": "deployment_label_canary=\npod_label_canary=main\nextra_deployment_label=bar\nextra_pod_label=baz\ndeployment_annotation=ann\npod_annotation=podann\n"
        }
    ]
}
```

---

### Feature 10: Service Account Rendering

**As a developer**, I want to render service-account identity for the workload, so I can control pod identity, token automounting, annotations, and registry secrets.

**Expected Behavior / Usage:**

The input selects the service-account manifest and supplies identity settings. Stdout reports the resource kind, account name, automount-token value, selected annotation, and image-pull-secret count.

**Test Cases:** `rcb_tests/public_test_cases/feature10_service_account.json`

```json
{
    "description": "Render a service account with the selected name, automount-token setting, annotations, and image-pull secrets.",
    "cases": [
        {
            "input": {
                "template": "serviceaccount",
                "output": "service_account",
                "set": {
                    "serviceAccount.create": "true",
                    "serviceAccount.name": "app-runner"
                }
            },
            "expected_output": "kind=ServiceAccount\nname=app-runner\nautomount_token=[null indicator — confirm required field handling details with platform team]\nannotation.foo=\nimage_pull_secret_count=0\n"
        }
    ]
}
```

---

### Feature 11: Internal Service Networking

**As a developer**, I want to render the service endpoint for the workload, so I can expose application ports with optional traffic policies.

**Expected Behavior / Usage:**

The input selects the service manifest and supplies networking settings. Stdout reports service kind, name, type, cluster IP, session affinity, external and internal traffic policies, port count, and each service port binding.

**Test Cases:** `rcb_tests/public_test_cases/feature11_service_networking.json`

```json
{
    "description": "Render the internal service with its ports and optional traffic-policy, session-affinity, and cluster-IP settings.",
    "cases": [
        {
            "input": {
                "template": "service",
                "output": "service",
                "set": {}
            },
            "expected_output": "kind=Service\nname=release-linter\ntype=ClusterIP\ncluster_ip=[null indicator — confirm required field handling details with platform team]\nsession_affinity=[null indicator — confirm required field handling details with platform team]\nexternal_traffic_policy=[null indicator — confirm required field handling details with platform team]\ninternal_traffic_policy=[null indicator — confirm required field handling details with platform team]\nport_count=1\nport_0_name=app\nport_0_port=80\nport_0_target=http\n"
        }
    ]
}
```

---

### Feature 12: Ingress Routing

**As a developer**, I want to render HTTP routing rules to backend services, so I can route external paths to the correct service ports.

**Expected Behavior / Usage:**

The input selects the ingress manifest and supplies routing data. Stdout reports ingress kind, name, rule count, TLS count, each host, path count, path string, backend service, and backend port as either number or name.

**Test Cases:** `rcb_tests/public_test_cases/feature12_ingress_routing.json`

```json
{
    "description": "Render ingress routing paths with numeric and named backend ports, including additional higher-priority or fallback paths.",
    "cases": [
        {
            "input": {
                "template": "ingress",
                "output": "ingress",
                "values_files": [
                    "test/fixtures/ingress_values_with_number_port.yaml"
                ]
            },
            "expected_output": "kind=Ingress\nname=release-linter\nrule_count=1\ntls_count=0\nrule_0_host=\nrule_0_path_count=2\nrule_0_path_0_path=/app\nrule_0_path_0_service=release-linter\nrule_0_path_0_port_number=80\nrule_0_path_0_port_name=[null indicator — confirm required field handling details with platform team]\nrule_0_path_1_path=/black-hole\nrule_0_path_1_service=black-hole\nrule_0_path_1_port_number=80\nrule_0_path_1_port_name=[null indicator — confirm required field handling details with platform team]\n"
        }
    ]
}
```

---

### Feature 13: Managed TLS Certificate

**As a developer**, I want to render a managed certificate manifest, so I can provision certificate resources from domain configuration.

**Expected Behavior / Usage:**

The input selects the managed-certificate manifest and supplies certificate name and domain data. Stdout reports the rendered kind, certificate name, and comma-separated domain list.

**Test Cases:** `rcb_tests/public_test_cases/feature13_managed_certificate.json`

```json
{
    "description": "Render a managed TLS certificate manifest when certificate name and domain data are supplied.",
    "cases": [
        {
            "input": {
                "template": "gmc",
                "output": "managed_certificate",
                "set": {
                    "google.managedCertificate.enabled": "true",
                    "google.managedCertificate.name": "app-cert",
                    "google.managedCertificate.domainName": "app.example.com"
                }
            },
            "expected_output": "kind=ManagedCertificate\nname=app-cert\ndomains=app.example.com\n"
        }
    ]
}
```

---

### Feature 14: Horizontal Autoscaling

**As a developer**, I want to render replica bounds and resource utilization metrics, so I can scale workloads based on CPU or memory utilization.

**Expected Behavior / Usage:**

The input selects the autoscaler manifest and supplies min and max replicas plus metric targets. Stdout reports kind, API version, replica bounds, metric count, and each metric resource with average utilization.

**Test Cases:** `rcb_tests/public_test_cases/feature14_horizontal_autoscaling.json`

```json
{
    "description": "Render a horizontal autoscaler with replica bounds and CPU or memory utilization metrics.",
    "cases": [
        {
            "input": {
                "template": "horizontalpodautoscaler",
                "output": "hpa",
                "set": {
                    "horizontalPodAutoscaler.enabled": "true",
                    "horizontalPodAutoscaler.minReplicas": "20",
                    "horizontalPodAutoscaler.maxReplicas": "30",
                    "horizontalPodAutoscaler.avgCpuUtilization": "55",
                    "horizontalPodAutoscaler.avgMemoryUtilization": "65"
                }
            },
            "expected_output": "kind=HorizontalPodAutoscaler\napi_version=autoscaling/v2\nmin_replicas=20\nmax_replicas=30\nmetric_count=2\nmetric_0_resource=cpu\nmetric_0_average_utilization=55\nmetric_1_resource=memory\nmetric_1_average_utilization=65\n"
        }
    ]
}
```

---

### Feature 15: Pod Disruption Budget

**As a developer**, I want to render a disruption budget when availability is requested, so I can preserve minimum workload availability during voluntary disruptions.

**Expected Behavior / Usage:**

The input selects the disruption-budget manifest and supplies a minimum available pod count. Stdout reports the resource kind, name, and minimum availability value.

**Test Cases:** `rcb_tests/public_test_cases/feature15_pod_disruption_budget.json`

```json
{
    "description": "Render a pod disruption budget only when the minimum available pod count is greater than zero.",
    "cases": [
        {
            "input": {
                "template": "pdb",
                "output": "pdb",
                "set": {
                    "minPodsAvailable": "1"
                }
            },
            "expected_output": "kind=PodDisruptionBudget\nname=release-linter\nmin_available=1\n"
        }
    ]
}
```

---

### Feature 16: Service Monitoring

**As a developer**, I want to render scrape endpoint metadata for monitoring, so I can allow metrics collection systems to discover the workload.

**Expected Behavior / Usage:**

The input selects the service-monitor manifest and supplies monitoring endpoint data. Stdout reports kind, name, endpoint count, scrape interval, timeout, path, port, and scheme.

**Test Cases:** `rcb_tests/public_test_cases/feature16_service_monitor.json`

```json
{
    "description": "Render a service-monitoring manifest with endpoint scrape interval, timeout, path, port, and scheme data.",
    "cases": [
        {
            "input": {
                "template": "servicemonitor",
                "output": "service_monitor",
                "values_files": [
                    "test/fixtures/service_monitor_values.yaml"
                ]
            },
            "expected_output": "kind=ServiceMonitor\nname=release-linter\nendpoint_count=1\nendpoint_0_interval=10s\nendpoint_0_timeout=10s\nendpoint_0_path=/metrics\nendpoint_0_port=http\nendpoint_0_scheme=http\n"
        }
    ]
}
```

---

### Feature 17: Custom Resource Passthrough

**As a developer**, I want to render supplied custom manifests, so I can include extension resources alongside generated manifests.

**Expected Behavior / Usage:**

The input selects the custom-resource output and supplies custom manifest data. Stdout reports the manifest count and each manifest kind and name in output order.

**Test Cases:** `rcb_tests/public_test_cases/feature17_custom_resources.json`

```json
{
    "description": "Render user-supplied custom resource manifests in the same output stream as the generated workload resources.",
    "cases": [
        {
            "input": {
                "template": "customresources",
                "output": "custom_resources",
                "values_files": [
                    "test/fixtures/custom_resources_values.yaml"
                ]
            },
            "expected_output": "manifest_count=1\nmanifest_0_kind=ConfigMap\nmanifest_0_name=example\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_required_and_optional_values.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_required_and_optional_values@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- reproduce port iteration logic consistent with existing label naming
- trace HPA component name pattern used in upstream templates
