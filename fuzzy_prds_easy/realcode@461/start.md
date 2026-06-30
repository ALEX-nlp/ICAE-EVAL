## Product Requirement Document

# Container Service Deployment Request Builder - A form-driven request assembler for a managed container hosting platform

## Project Goal

Build a library that turns the choices a developer makes in a "create service" form into a fully-formed deployment request for a managed container-hosting platform, so that developers can describe *what* they want to deploy (a private image, a public image, or a source-code repository) without hand-assembling the nested request payload or remembering which fields each deployment style requires.

---

## Background & Problem

A managed container-hosting platform accepts a single, deeply nested "create service" request that bundles together the compute sizing, the source of the application (a container image or a source repository), how new versions are rolled out, and the credentials used to reach the source. The exact shape of that request differs depending on the chosen source: a private image needs an access role, a public image forbids a redeployment toggle, and a repository can either carry its build configuration inline or defer it to a file inside the repository.

Without a dedicated builder, developers must manually branch on the deployment style, populate the correct nested sub-objects, normalize free-text fields (trimming URLs, dropping blank commands), and pull the right connection/role identifiers from asynchronously-loaded pickers. This is repetitive and error-prone, and small mistakes (a stray trailing slash, an auto-deploy flag set where it should be absent) silently produce an invalid or wrong deployment.

With this library, the developer fills in a small, well-typed form model; the library validates and normalizes the inputs, resolves the available source connection and access role, and emits exactly the request the platform expects for the chosen deployment style.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain has several distinct responsibilities (a form/input model with field normalization, resolution of asynchronously-loaded pickers, and per-deployment-style request assembly), so it MUST NOT be a single "god file"; use a clear multi-file structure that separates the form model, the picker/selection resolution, and the request assembly.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a **black-box contract for an execution adapter**, NOT the internal data model. The core request-building logic must be decoupled from stdin/stdout and JSON parsing. A thin adapter translates each JSON command into idiomatic calls on the core form model and request builder, then renders the result.

3. **Adherence to SOLID Design Principles:** Separate input normalization, picker resolution, deployment-style routing, request assembly, and output formatting into distinct units. The request assembler must be open to new deployment styles without rewriting existing ones.

4. **Robustness & Interface Design:** The public interface must be idiomatic and hide the nesting of the underlying request. Each deployment style must populate only the sub-objects that style permits, and absent values (e.g. an unset redeployment flag, an absent inline configuration block) must be represented as genuinely absent rather than as defaulted placeholders.

---

## Core Features

### Feature 1: Private-Image Deployment Request

**As a developer**, I want to assemble a deployment request from a private container image, so I can deploy a pre-built image while letting the platform pull it using a designated access role.

**Expected Behavior / Usage:**

When the deployment style is a private container image, the builder produces a request whose source section identifies a private-registry image source. Compute sizing defaults to the first available CPU tier (`1 vCPU`) and memory tier (`2 GB`). The single available instance access role is resolved and attached to the request's authentication section. Automatic redeployment is enabled by default but can be turned off, and the chosen value is reflected in the request. The default service port is `80`.

The adapter input is a JSON object with `action` = `build_request` and `deployment` = `image_private`; an optional `auto_deploy` boolean (default `[a specific boolean flag—confirm the active status with the deployment service]`) controls the redeployment toggle. The output is a line-per-field, alphabetically-sorted rendering of the constructed request's observable fields (access role, redeployment flag, CPU, memory, image source type, image identifier, port, service name).

**Test Cases:** `rcb_tests/public_test_cases/feature1_private_image_request.json`

```json
{
    "description": "Building a deployment request for a container-image source backed by a private registry. The form defaults to one CPU/memory tier, automatic redeployment enabled, and resolves the single available instance access role. The constructed request must report the image source type, the selected access role, the default port, and instance sizing.",
    "cases": [
        {
            "input": {"action": "build_request", "deployment": "image_private"},
            "expected_output": "access_role_arn=arn::access-role\nauto_deployments=[a specific boolean flag—confirm the active status with the deployment service]\ncpu=1 vCPU\nimage_identifier=\nimage_port=80\nimage_repository_type=ECR\nmemory=2 GB\nservice_name="
        }
    ]
}
```

---

### Feature 2: Public-Image Deployment Request

**As a developer**, I want to assemble a deployment request from a public container image, so I can deploy an openly-accessible image without configuring an access role or a redeployment policy.

**Expected Behavior / Usage:**

When the deployment style is a public container image, the builder produces a request whose source section identifies a public-registry image source. A public image source does **not** support a managed redeployment policy, so the automatic-deployment flag must be left genuinely unset (rendered as `null`) rather than defaulted to a boolean. No access role is attached. Compute sizing and port default as in Feature 1.

The adapter input is a JSON object with `action` = `build_request` and `deployment` = `image_public`. The output renders the observable request fields (redeployment flag as `null`, CPU, memory, image source type, image identifier, port, service name).

**Test Cases:** `rcb_tests/public_test_cases/feature2_public_image_request.json`

```json
{
    "description": "Building a deployment request for a public container-image source. A public image source does not support a managed redeployment toggle, so the request must leave the automatic-deployment flag unset (null) rather than defaulting it. The request must report the public image source type, the default port, and instance sizing.",
    "cases": [
        {
            "input": {"action": "build_request", "deployment": "image_public"},
            "expected_output": "auto_deployments=null\ncpu=1 vCPU\nimage_identifier=\nimage_port=80\nimage_repository_type=ECR_PUBLIC\nmemory=2 GB\nservice_name="
        }
    ]
}
```

---

### Feature 3: Source-Repository Deployment Request

**As a developer**, I want to assemble a deployment request from a source-code repository, so I can deploy directly from source whether I provide build settings inline or defer them to a file in the repository.

**Expected Behavior / Usage:**

*3.1 Inline (API) configuration — build settings supplied through the form*

When the deployment style is a source repository and build settings are supplied inline, the request's code section marks its configuration source as API-supplied and embeds a code-configuration block carrying the chosen runtime and the default port (`80`). The repository URL is echoed (after normalization, see Feature 5), the source-code version selector defaults to a branch, and the resolved source connection identifier is attached to the authentication section. Automatic redeployment defaults on.

The adapter input is a JSON object with `action` = `build_request`, `deployment` = `repository`, `repo_config` = `api`, a `repository_url` string, and a `runtime` identifier (an enumerated runtime token such as `[the specific runtime token string provided by the caller]` or `[the specific runtime token string provided by the caller]`). Output renders the observable request fields including a flag indicating the inline configuration block is present along with its port and runtime.

**Test Cases:** `rcb_tests/public_test_cases/feature3_repository_api_request.json`

```json
{
    "description": "Building a deployment request for a source-code repository whose build settings are supplied inline through the form (API configuration). The request must embed a code-configuration block carrying the chosen runtime and default port, mark the configuration source as API-supplied, echo the normalized repository URL, default the source-code version selector to a branch, and attach the resolved source-connection identifier. Automatic redeployment defaults on.",
    "cases": [
        {
            "input": {"action": "build_request", "deployment": "repository", "repo_config": "api", "repository_url": "myrepo", "runtime": "[the specific runtime token string provided by the caller]"},
            "expected_output": "auto_deployments=[a specific boolean flag—confirm the active status with the deployment service]\ncode_configuration_values_present=[a specific boolean flag—confirm the active status with the deployment service]\ncode_port=80\ncode_runtime=[the specific runtime token string provided by the caller]\nconfiguration_source=API\nconnection_arn=arn::source-connection\ncpu=1 vCPU\nmemory=2 GB\nrepository_url=myrepo\nservice_name=\nsource_code_version_type=BRANCH"
        }
    ]
}
```

*3.2 File-based configuration — build settings deferred to a repository file*

When build settings are deferred to a file in the repository, the request's code section marks its configuration source as repository-supplied and attaches **no** inline code-configuration block (it is genuinely absent). The repository URL is still echoed and the version selector still defaults to a branch; the source connection identifier is still attached. This case also exercises manual (disabled) redeployment.

The adapter input uses `repo_config` = `file` and an `auto_deploy` of `[a specific boolean flag—confirm the active status with the deployment service]`. Output indicates the inline configuration block is absent and reports the disabled redeployment flag.

**Test Cases:** `rcb_tests/public_test_cases/feature4_repository_file_request.json`

```json
{
    "description": "Building a deployment request for a source-code repository configured from a file checked into the repository, with manual (not automatic) redeployment selected. Because build settings come from the repository file, no inline code-configuration values are attached. The request must mark the configuration source as repository-supplied, leave the inline configuration block absent, echo the normalized repository URL, default the source-code version selector to a branch, report automatic redeployment as disabled, and attach the resolved source-connection identifier.",
    "cases": [
        {
            "input": {"action": "build_request", "deployment": "repository", "repo_config": "file", "auto_deploy": [a specific boolean flag—confirm the active status with the deployment service], "repository_url": "myrepo"},
            "expected_output": "auto_deployments=[a specific boolean flag—confirm the active status with the deployment service]\ncode_configuration_values_present=[a specific boolean flag—confirm the active status with the deployment service]\nconfiguration_source=REPOSITORY\nconnection_arn=arn::source-connection\ncpu=1 vCPU\nmemory=2 GB\nrepository_url=myrepo\nservice_name=\nsource_code_version_type=BRANCH"
        }
    ]
}
```

---

### Feature 4: Input Field Normalization

**As a developer**, I want free-text form fields to be normalized as I enter them, so I can avoid invalid deployments caused by stray whitespace, blank-but-present values, or trailing separators.

**Expected Behavior / Usage:**

*4.1 Start-command normalization — blank becomes absent*

The optional start-command field treats a value that is empty or whitespace-only as absent: storing such a value yields no value (rendered as the literal token `null`). A meaningful command is stored verbatim. This lets the request omit the start command entirely when nothing useful was entered.

The adapter input is `action` = `normalize`, `field` = `start_command`, and a `value` string. Output is `start_command=<stored value or null>`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_start_command_normalization.json`

```json
{
    "description": "Normalizing the optional start-command field. A start command consisting only of whitespace is treated as absent and normalized to no value; a meaningful command is preserved verbatim. The output reports the stored value, or the literal token null when the field ends up unset.",
    "cases": [
        {
            "input": {"action": "normalize", "field": "start_command", "value": "    "},
            "expected_output": "start_command=null"
        }
    ]
}
```

*4.2 Repository-URL normalization — trim and drop a single trailing slash*

The repository URL field trims surrounding whitespace and removes a single trailing slash, so a stored URL does not later produce a doubled separator when concatenated. A URL that is already clean is preserved unchanged.

The adapter input is `action` = `normalize`, `field` = `repository_url`, and a `value` string. Output is `repository_url=<stored value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_repository_url_normalization.json`

```json
{
    "description": "Normalizing the repository URL field. Surrounding whitespace is trimmed and a single trailing slash is removed so the stored URL does not later produce a doubled separator; a URL already without a trailing slash is preserved unchanged. The output reports the stored URL.",
    "cases": [
        {
            "input": {"action": "normalize", "field": "repository_url", "value": " https://abc/ "},
            "expected_output": "repository_url=https://abc"
        }
    ]
}
```

---

### Feature 5: Seeded Container Image Reference

**As a developer**, I want to open the form with a container image reference already filled in, so I can pre-populate the image to deploy from an external trigger.

**Expected Behavior / Usage:**

When the form is created with an initial container image reference, that reference is carried through unchanged into the form's container image field, ready to be used as the image identifier of a subsequent request. The output echoes the stored container reference.

The adapter input is `action` = `container_uri` and a `uri` string. Output is `container_uri=<stored value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_seeded_container_uri.json`

```json
{
    "description": "Seeding the form with a pre-supplied container image reference. When the dialog is opened with an initial image URI, that value must be carried through into the form's container image field unchanged, so a caller can pre-populate the image to deploy. The output echoes the stored container URI.",
    "cases": [
        {
            "input": {"action": "container_uri", "uri": "some-uri-123"},
            "expected_output": "container_uri=some-uri-123"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the form model (with field normalization and picker resolution) and the per-deployment-style request assembler described above.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-feature contracts above. The adapter is separated from the core domain.

3. **Automated test harness:** A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` containing only the raw program output, so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same logic for presence flags as the deferred configuration path
- normalize URLs using the standard path utility
