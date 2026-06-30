## Product Requirement Document

# Container Image Redirection Webhook — Input/Output Contract

## Project Goal

Build a Kubernetes admission-time library that automatically redirects every container image reference in a pod toward a private, account-scoped registry mirror. It lets platform developers transparently pull all workloads through their own registry — for resilience, caching, and supply-chain control — **without** asking every team to manually rewrite image names in their manifests.

---

## Background & Problem

Without this library, teams that want all workloads served from a private registry mirror must hand-edit every pod spec to prefix each image with the mirror's host, keep those prefixes correct as images change, and ensure the corresponding repositories and pull credentials exist. This is repetitive, error-prone boilerplate that drifts out of sync and breaks deployments when an image is missed or mistyped.

With this library, a cluster-side admission component inspects each incoming pod, decides which container images should be redirected (driven by configurable selection rules and operating modes), computes the rewritten references that point at the private mirror while preserving the original image coordinates, and resolves the pull credentials needed to mirror those images. The developer keeps writing ordinary manifests; the redirection happens automatically.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain has several distinct responsibilities (operating-mode parsing, configuration parsing, a selection-expression evaluator, credential resolution/merging, and the admission rewrite engine), so it MUST NOT be a single "god file". Provide a clear multi-file directory tree (core domain modules, an execution adapter, and tests) that reflects a production-grade repository. Do not over-engineer the smaller pure-function pieces.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic MUST remain decoupled from stdin/stdout and JSON parsing. The execution adapter alone translates JSON commands into idiomatic calls to the core domain and renders results.

3. **Adherence to SOLID Design Principles** (scaled to project size):
   - **SRP:** Separate parsing, selection evaluation, credential resolution, the rewrite engine, and output formatting into distinct units.
   - **OCP:** The rewrite engine must be open for extension (new operating modes, new selection rules) but closed for modification.
   - **LSP:** Alternative credential resolvers (e.g. a cluster-backed resolver vs. a no-op resolver) must be perfectly substitutable behind one abstraction.
   - **ISP:** Keep the registry-client and resolver interfaces small and cohesive.
   - **DIP:** The rewrite engine depends on registry-client and credential-resolver abstractions, not on concrete cloud or I/O implementations.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface must be elegant and idiomatic to the target language.
   - **Resilience:** Unknown operating-mode keywords degrade to a safe default while still reporting the error; malformed selection expressions never crash the evaluation and resolve to a non-match. Errors are modeled as neutral categories, never as leaked host-language runtime faults.

---

## Core Features

### Feature 1: Image-Swap Operating Mode Resolution

**As a developer**, I want to turn a swap-mode keyword into a validated, canonical mode, so I can configure when image references get redirected and get a clear signal when a misconfigured keyword is supplied.

**Expected Behavior / Usage:**

The system recognizes two swap modes: one that always redirects matching references, and one that only redirects when the mirrored image already exists. Input is a single keyword string. For a recognized keyword the output reports the canonical mode name (`always` or `exists`). For an unrecognized keyword the system does not fail hard: it falls back to the safe default mode (`exists`) and additionally emits an `error=unknown_swap_policy` line together with the offending `input` value. Output is line-oriented `key=value` text.

**Test Cases:** `rcb_tests/public_test_cases/feature1_swap_policy.json`

```json
{
    "description": "Resolve an image-swap mode keyword into its canonical mode name. Recognized keywords echo back their canonical name. An unrecognized keyword falls back to the safe default mode and is additionally reported as an error together with the offending input.",
    "cases": [
        {"input": {"op": "swap_policy", "value": "always"}, "expected_output": "policy=always\n"},
        {"input": {"op": "swap_policy", "value": "exists"}, "expected_output": "policy=exists\n"},
        {"input": {"op": "swap_policy", "value": "random-non-existent"}, "expected_output": "policy=exists\nerror=unknown_swap_policy\ninput=random-non-existent\n"}
    ]
}
```

---

### Feature 2: Image-Copy Timing Mode Resolution

**As a developer**, I want to turn a copy-timing keyword into a validated, canonical mode, so I can control whether mirroring of an image happens lazily, synchronously, or unconditionally, with a clear signal for bad input.

**Expected Behavior / Usage:**

The system recognizes three copy-timing modes: a deferred mode (mirror in the background), an inline mode (mirror and wait), and a forced mode (mirror unconditionally, bypassing existence short-circuits). Input is a single keyword string. For a recognized keyword the output reports the canonical mode name (`delayed`, `immediate`, or `force`). For an unrecognized keyword the system falls back to the safe default mode (`delayed`) and additionally emits an `error=unknown_copy_policy` line together with the offending `input` value.

**Test Cases:** `rcb_tests/public_test_cases/feature2_copy_policy.json`

```json
{
    "description": "Resolve an image-copy timing mode keyword into its canonical mode name. Recognized keywords echo back their canonical name. An unrecognized keyword falls back to the safe default mode and is additionally reported as an error together with the offending input.",
    "cases": [
        {"input": {"op": "copy_policy", "value": "delayed"}, "expected_output": "policy=delayed\n"},
        {"input": {"op": "copy_policy", "value": "immediate"}, "expected_output": "policy=immediate\n"},
        {"input": {"op": "copy_policy", "value": "force"}, "expected_output": "policy=force\n"},
        {"input": {"op": "copy_policy", "value": "random-non-existent"}, "expected_output": "policy=delayed\nerror=unknown_copy_policy\ninput=random-non-existent\n"}
    ]
}
```

---

### Feature 3: Configuration Document Parsing (Source Filters)

**As a developer**, I want to declare container-selection rules in a YAML configuration document and have them parsed into an ordered list, so I can control which images are eligible for redirection without code changes.

**Expected Behavior / Usage:**

The configuration document is YAML. Under a `source.filters` section it carries an ordered list of selection expressions, each given as a `jmespath` string. The system parses the document and reports the number of declared filters followed by each filter's expression text in declaration order. An empty document yields zero filters. Unrelated configuration keys are ignored for this output. Output is line-oriented text: a `filters=<count>` line, then one `filter[<index>].jmespath=<expr>` line per filter.

**Test Cases:** `rcb_tests/public_test_cases/feature3_config_filters.json`

```json
{
    "description": "Parse a YAML configuration document and report the ordered list of container-selection expressions declared under the source filters section. An empty document yields zero filters.",
    "cases": [
        {"input": {"op": "parse_config", "yaml": ""}, "expected_output": "filters=0\n"},
        {"input": {"op": "parse_config", "yaml": "source:\n  filters:\n    - jmespath: \"obj.metadata.namespace == 'kube-system'\"\n    - jmespath: \"obj.metadata.namespace != 'playground'\"\n"}, "expected_output": "filters=2\nfilter[0].jmespath=obj.metadata.namespace == 'kube-system'\nfilter[1].jmespath=obj.metadata.namespace != 'playground'\n"}
    ]
}
```

---

### Feature 4: Container Selection Predicate

**As a developer**, I want to evaluate a single selection expression against the pod and the container currently under consideration, so I can decide whether that container's image should be skipped from redirection.

**Expected Behavior / Usage:**

A selection context is assembled from the pod (exposing `obj.metadata.namespace`) and the current container (exposing `container.name` and `container.image`). The expression is evaluated against this context. The result is rendered as a `match` boolean: when the expression returns boolean true it matches (`match=true`); when it returns boolean false it does not match (`match=false`). Two non-match degradations are reported via a neutral `reason` field rather than crashing: an expression whose result is not a boolean reports `reason=non_boolean_result`, and an expression that cannot be evaluated at all reports `reason=evaluation_error`. The output echoes the input `namespace`, `container` name, and `expression` for traceability, followed by the `match` line and (when applicable) the `reason` line.

**Test Cases:** `rcb_tests/public_test_cases/feature4_selection_predicate.json`

```json
{
    "description": "Evaluate a single selection expression against a context built from a pod (namespace) and the container currently under consideration. A boolean-true result matches; a boolean-false result does not match; an expression that errors or yields a non-boolean value does not match and reports the neutral reason category.",
    "cases": [
        {"input": {"op": "filter_match", "namespace": "kube-system", "container": {"name": "nginx", "image": "nginx:latest"}, "expression": "obj.metadata.namespace == 'kube-system'"}, "expected_output": "namespace=kube-system\ncontainer=nginx\nexpression=obj.metadata.namespace == 'kube-system'\nmatch=true\n"},
        {"input": {"op": "filter_match", "namespace": "kube-system", "container": {"name": "nginx", "image": "nginx:latest"}, "expression": "obj.metadata.namespace != 'kube-system'"}, "expected_output": "namespace=kube-system\ncontainer=nginx\nexpression=obj.metadata.namespace != 'kube-system'\nmatch=false\n"},
        {"input": {"op": "filter_match", "namespace": "kube-system", "container": {"name": "nginx", "image": "nginx:latest"}, "expression": "container.name == 'nginx'"}, "expected_output": "namespace=kube-system\ncontainer=nginx\nexpression=container.name == 'nginx'\nmatch=true\n"},
        {"input": {"op": "filter_match", "namespace": "kube-system", "container": {"name": "nginx", "image": "nginx:latest"}, "expression": "obj"}, "expected_output": "namespace=kube-system\ncontainer=nginx\nexpression=obj\nmatch=false\nreason=non_boolean_result\n"},
        {"input": {"op": "filter_match", "namespace": "kube-system", "container": {"name": "nginx", "image": "nginx:latest"}, "expression": "."}, "expected_output": "namespace=kube-system\ncontainer=nginx\nexpression=.\nmatch=false\nreason=evaluation_error\n"},
        {"input": {"op": "filter_match", "namespace": "kube-system", "container": {"name": "nginx", "image": "nginx:latest"}, "expression": "contains(container.image, '.dkr.ecr.') && contains(container.image, '.amazonaws.com')"}, "expected_output": "namespace=kube-system\ncontainer=nginx\nexpression=contains(container.image, '.dkr.ecr.') && contains(container.image, '.amazonaws.com')\nmatch=false\n"}
    ]
}
```

---

### Feature 5: Pull-Credential Handling

**As a developer**, I want the system to gather and merge the registry pull credentials a pod needs, so mirroring can authenticate to source registries on the pod's behalf.

**Expected Behavior / Usage:**

*5.1 Credential Aggregation — merging named docker-config credential documents into one*

Given a set of named credential documents, each in docker-config JSON form (`{"auths":{...}}` or any JSON object), the system retains every named document verbatim and produces a single merged aggregate document combining all top-level keys. The output reports the number of retained secrets, each secret's verbatim content keyed by its name (emitted in sorted name order), and the merged `aggregate` JSON. Merging is a JSON merge: keys from later documents combine with earlier ones; object values may be re-serialized with sorted keys.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_secret_aggregation.json`

```json
{
    "description": "Aggregate a set of named docker-config credential documents into a single merged JSON document. Each named secret is retained verbatim and the merged aggregate combines all keys.",
    "cases": [
        {"input": {"op": "aggregate_secrets", "secrets": [{"name": "foo", "data": "{\"foo\":\"123\"}"}, {"name": "bar", "data": "{\"bar\":\"456\"}"}]}, "expected_output": "secret_count=2\nsecret[bar]={\"bar\":\"456\"}\nsecret[foo]={\"foo\":\"123\"}\naggregate={\"bar\":\"456\",\"foo\":\"123\"}\n"}
    ]
}
```

*5.2 Credential Resolution — collecting the credentials that apply to a pod*

Two resolver behaviors exist behind one abstraction. The **cluster-backed resolver** collects pull-credential references attached directly to the pod and those attached to the pod's service account, then fetches each referenced secret (of docker-config type) from the cluster exactly once (a name referenced more than once is fetched a single time), retaining each and producing the merged aggregate as in 5.1. The **no-op resolver** ignores all references and always yields an empty set with an empty (`{}`) aggregate. Input names the resolver `mode` (`kubernetes` or `noop`), the pod (its namespace, service-account name, and directly-referenced secret names), the service account (its name and referenced secret names), and the available secrets (name + docker-config JSON content). Output reports `secret_count`, each retained `secret[<name>]=<content>` in sorted name order, and the merged `aggregate`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_secret_resolution.json`

```json
{
    "description": "Resolve the set of docker-config pull-credential documents that apply to a pod. The cluster-backed resolver collects credentials referenced directly by the pod and by its service account, fetching each named secret once and producing the merged aggregate. The no-op resolver always yields an empty set.",
    "cases": [
        {"input": {"op": "resolve_pull_secrets", "mode": "noop", "namespace": "test-ns", "pod": {"name": "my-pod", "service_account_name": "my-service-account", "image_pull_secrets": ["my-pod-secret"]}}, "expected_output": "secret_count=0\naggregate={}\n"},
        {"input": {"op": "resolve_pull_secrets", "mode": "kubernetes", "namespace": "test-ns", "pod": {"name": "my-pod", "service_account_name": "my-service-account", "image_pull_secrets": ["my-pod-secret"]}, "service_account": {"name": "my-service-account", "image_pull_secrets": ["my-sa-secret"]}, "secrets": [{"name": "my-sa-secret", "data": "{\"auths\":{\"my-sa-secret.registry.example.com\":{\"username\":\"my-sa-secret\",\"password\":\"xxxxxxxxxxx\",\"email\":\"jdoe@example.com\",\"auth\":\"c3R...zE2\"}}}"}, {"name": "my-pod-secret", "data": "{\"auths\":{\"my-pod-secret.registry.example.com\":{\"username\":\"my-sa-secret\",\"password\":\"xxxxxxxxxxx\",\"email\":\"jdoe@example.com\",\"auth\":\"c3R...zE2\"}}}"}]}, "expected_output": "secret_count=2\nsecret[my-pod-secret]={\"auths\":{\"my-pod-secret.registry.example.com\":{\"username\":\"my-sa-secret\",\"password\":\"xxxxxxxxxxx\",\"email\":\"jdoe@example.com\",\"auth\":\"c3R...zE2\"}}}\nsecret[my-sa-secret]={\"auths\":{\"my-sa-secret.registry.example.com\":{\"username\":\"my-sa-secret\",\"password\":\"xxxxxxxxxxx\",\"email\":\"jdoe@example.com\",\"auth\":\"c3R...zE2\"}}}\naggregate={\"auths\":{\"my-pod-secret.registry.example.com\":{\"auth\":\"c3R...zE2\",\"email\":\"jdoe@example.com\",\"password\":\"xxxxxxxxxxx\",\"username\":\"my-sa-secret\"},\"my-sa-secret.registry.example.com\":{\"auth\":\"c3R...zE2\",\"email\":\"jdoe@example.com\",\"password\":\"xxxxxxxxxxx\",\"username\":\"my-sa-secret\"}}}\n"}
    ]
}
```

---

### Feature 6: Admission Image Rewriting

**As a developer**, I want the system to process an incoming pod admission request and produce the ordered set of image-reference rewrites that redirect every container and init-container to the private registry mirror, so workloads are transparently served from the mirror without manual manifest edits.

**Expected Behavior / Usage:**

Input is a pod admission request (the standard admission-review envelope carrying the pod under `request.object`) plus the target registry host. The system walks every container and every init-container and, for each image that does not already point at the target registry, computes a rewritten reference of the form `<target-registry>/<normalized-source-reference>`. Normalization canonicalizes bare image names to their fully-qualified path (e.g. `nginx` → `docker.io/library/nginx:latest`, `init-container` → `docker.io/library/init-container:latest`) and preserves digest pinning: an image carrying both a tag and a digest is rewritten keeping the digest (the redundant tag is dropped). The result is expressed as a list of replace operations addressing each image by its container path. The output reports the `target_registry`, the number of rewrite operations (`patch_ops`), one `replace <path> <new-reference>` line per rewrite ordered by path, and a `warnings` line (`warnings=none` when no warnings were produced). Operating in the always-redirect swap mode, every eligible image yields a rewrite regardless of whether the mirror already holds it.

This case redirects a pod with two containers (a bare `nginx` image and a tag+digest pinned ingress controller) and one init-container, producing three rewrites ordered by path, against target registry `123456789.dkr.ecr.ap-southeast-2.amazonaws.com`. The bare `nginx` becomes `docker.io/library/nginx:latest`, the init-container `init-container` becomes `docker.io/library/init-container:latest`, and the tag+digest image keeps only its digest. The hidden test set additionally exercises a single-container pod (one rewrite) and pods that already reference the target registry.

**Test Cases:** `rcb_tests/public_test_cases/feature6_image_rewriting.json`

```json
{
    "description": "Process a pod admission request and emit the ordered set of image-reference rewrite operations needed to point every container and init-container at the target registry. Each rewrite preserves the original image coordinates (including digest pinning) under a registry-prefixed path. The output reports the target registry, the rewrite operations, and whether any warnings were produced.",
    "cases": [
        {
            "input": {
                "op": "swap_images",
                "admission_review": {
                    "apiVersion": "admission.k8s.io/v1",
                    "kind": "AdmissionReview",
                    "request": {
                        "uid": "c78e0c58-7389-4838-b4f5-28d6005c1cc3",
                        "name": "nginx28",
                        "namespace": "default",
                        "operation": "CREATE",
                        "kind": {"group": "", "kind": "Pod", "version": "v1"},
                        "resource": {"group": "", "resource": "pods", "version": "v1"},
                        "object": {
                            "apiVersion": "v1",
                            "kind": "Pod",
                            "metadata": {"creationTimestamp": null, "name": "nginx28", "namespace": "default"},
                            "spec": {
                                "containers": [
                                    {"name": "nginx28", "image": "nginx", "imagePullPolicy": "Always", "resources": {}},
                                    {"name": "ingress-nginx28", "image": "k8s.gcr.io/ingress-nginx/controller:v0.43.0@sha256:9bba603b99bf25f6d117cf1235b6598c16033ad027b143c90fa5b3cc583c5713", "imagePullPolicy": "Always", "resources": {}}
                                ],
                                "initContainers": [
                                    {"name": "init-container28", "image": "init-container", "imagePullPolicy": "Always", "resources": {}}
                                ]
                            },
                            "status": {}
                        }
                    }
                }
            },
            "expected_output": "target_registry=123456789.dkr.ecr.ap-southeast-2.amazonaws.com\npatch_ops=3\nreplace /spec/containers/0/image 123456789.dkr.ecr.ap-southeast-2.amazonaws.com/docker.io/library/nginx:latest\nreplace /spec/containers/1/image 123456789.dkr.ecr.ap-southeast-2.amazonaws.com/k8s.gcr.io/ingress-nginx/controller@sha256:9bba603b99bf25f6d117cf1235b6598c16033ad027b143c90fa5b3cc583c5713\nreplace /spec/initContainers/0/image 123456789.dkr.ecr.ap-southeast-2.amazonaws.com/docker.io/library/init-container:latest\nwarnings=none\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing operating-mode resolution, configuration parsing, the selection-predicate evaluator, credential aggregation/resolution behind a substitutable resolver abstraction, and the admission rewrite engine. Physical structure must follow the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads a single JSON command object from stdin (routed by a neutral `op` discriminator), invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-feature line-oriented contracts above. Native runtime errors raised by the core are translated by the adapter into the neutral error categories shown here (e.g. `error=unknown_swap_policy`, `reason=evaluation_error`) — no host-language exception class names or runtime message suffixes ever appear in stdout. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_swap_policy.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_swap_policy@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the same canonicalization logic as seen in the hashing_utils module
