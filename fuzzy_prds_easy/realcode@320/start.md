## Product Requirement Document

# Remote AI Service Client - HTTP Resource Adapter

## Project Goal

Build a client library and execution adapter for a remote AI service that allows developers to check service status, discover text-generation providers, request completions, manage datasets, create and inspect jobs, and retrieve model suggestions without hand-writing repetitive HTTP request and response parsing code.

---

## Background & Problem

Without this library/tool, developers are forced to manually construct endpoint URLs, encode request payloads, parse structured responses, and translate HTTP failures for each service resource. This leads to repetitive code, inconsistent error handling, and fragile integrations.

With this library/tool, developers use a stable client interface while the execution adapter exposes a deterministic stdin/stdout contract for black-box validation.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls to the core domain.

3. **Adherence to SOLID Design Principles:** The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly and rendered by the adapter as language-neutral categories rather than host-language runtime exception names.

---

## Core Features

### Feature 1: Service Status

**As a developer**, I want to check the service availability endpoint, so I can confirm that the remote service is alive before using dependent operations.

**Expected Behavior / Usage:**

The input names a status-check operation and supplies the service response scenario to exercise. A successful response must perform an HTTP GET to `/api/v1/health` and print the method, routed path, status code, service status, and deployment type; if the response omits deployment type, the output keeps the field with an empty value. HTTP failures are rendered as language-neutral `error=http_status` lines with the status code.

**Test Cases:** `rcb_tests/public_test_cases/feature1_service_status.json`

```json
{
    "description": "Checks service status responses and normalized failures from the status endpoint.",
    "cases": [
        {
            "input": {
                "feature": "service_status",
                "scenario": "available_full",
                "response": {
                    "status": "ok",
                    "deployment_type": "local"
                }
            },
            "expected_output": "http_method=GET\npath=/api/v1/health\nstatus_code=200\nstatus=ok\ndeployment_type=local\n"
        },
        {
            "input": {
                "feature": "service_status",
                "scenario": "available_without_deployment_type",
                "response": {
                    "status": "ok"
                }
            },
            "expected_output": "http_method=GET\npath=/api/v1/health\nstatus_code=200\nstatus=ok\ndeployment_type=\n"
        }
    ]
}
```

---

### Feature 2: Text Generation

**As a developer**, I want to request provider-backed text generation, so I can discover providers and retrieve generated text through the service API.

**Expected Behavior / Usage:**

*2.1 Provider Discovery — Retrieve available text-generation providers.*

The input names a provider-discovery operation and supplies the provider list returned by the service. The output must show an HTTP GET to `/api/v1/completions`, the status code, the provider count, and the comma-separated provider names; an empty provider list must produce count zero and an empty provider field.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_completion_vendors.json`

```json
{
    "description": "Retrieves the list of available completion providers, including the empty-list case.",
    "cases": [
        {
            "input": {
                "feature": "completion_vendors",
                "vendors": [
                    "openai",
                    "mistral"
                ]
            },
            "expected_output": "http_method=GET\npath=/api/v1/completions\nstatus_code=200\ncount=2\nvendors=[a specific list of vendor names]\n"
        },
        {
            "input": {
                "feature": "completion_vendors",
                "vendors": []
            },
            "expected_output": "http_method=GET\npath=/api/v1/completions\nstatus_code=200\ncount=0\nvendors=\n"
        }
    ]
}
```

*2.2 Provider Completion — Generate text through a supported provider.*

The input names a text-completion operation, identifies the available providers, the selected provider, and the prompt text. A supported provider with non-blank text must POST to `/api/v1/completions/{provider}/` and print the generated text. Unsupported providers are normalized to `error=unsupported_vendor`; empty or whitespace-only prompts are normalized to `error=empty_prompt`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_text_completion.json`

```json
{
    "description": "Requests generated text from a supported provider and reports normalized validation errors for unsupported providers or blank prompts.",
    "cases": [
        {
            "input": {
                "feature": "text_completion",
                "scenario": "success",
                "vendors": [
                    "openai",
                    "mistral"
                ],
                "vendor": "openai",
                "prompt": "please",
                "completion_text": "thanks"
            },
            "expected_output": "http_method=POST\npath=/api/v1/completions/openai/\nstatus_code=200\ntext=thanks\n"
        },
        {
            "input": {
                "feature": "text_completion",
                "scenario": "success",
                "vendors": [
                    "openai",
                    "mistral"
                ],
                "vendor": "mistral",
                "prompt": "please",
                "completion_text": "thanks"
            },
            "expected_output": "http_method=POST\npath=/api/v1/completions/mistral/\nstatus_code=200\ntext=thanks\n"
        },
        {
            "input": {
                "feature": "text_completion",
                "scenario": "invalid_vendor",
                "vendors": [
                    "openai",
                    "mistral"
                ],
                "vendor": "foo",
                "prompt": "juan?"
            },
            "expected_output": "error=unsupported_vendor\n"
        }
    ]
}
```

---

### Feature 3: Dataset Records

**As a developer**, I want to manage dataset metadata records over HTTP, so I can list, inspect, create, and delete dataset records without hand-writing request handling.

**Expected Behavior / Usage:**

*3.1 Dataset Reading — List datasets and fetch one dataset record.*

The input names a dataset-read operation and selects either a collection response or one record response. Listing must perform an HTTP GET to `/api/v1/datasets` and print total count, item count, and representative first-item metadata when present. Fetching a single dataset must perform an HTTP GET to `/api/v1/datasets/{id}` and print the id, filename, format, size, and ground-truth flag. Empty listings must preserve the total and item count as zero.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_dataset_read.json`

```json
{
    "description": "Reads dataset listings and individual dataset metadata through HTTP endpoints.",
    "cases": [
        {
            "input": {
                "feature": "dataset_read",
                "scenario": "list_full"
            },
            "expected_output": "http_method=GET\npath=/api/v1/datasets\nstatus_code=200\ntotal=3\nitem_count=3\nfirst_id=daab39ac-be9f-4de9-87c0-c4c94b297a97\nfirst_filename=ds1.hf\nfirst_format=job\n"
        },
        {
            "input": {
                "feature": "dataset_read",
                "scenario": "list_empty"
            },
            "expected_output": "http_method=GET\npath=/api/v1/datasets\nstatus_code=200\ntotal=0\nitem_count=0\n"
        }
    ]
}
```

*3.2 Dataset Writing — Create and delete dataset records.*

The input names a dataset-write operation and selects create, delete, or missing-delete behavior. Creating a dataset must POST to `/api/v1/datasets` with file metadata and print the returned id, filename, and format. Deleting must issue DELETE to `/api/v1/datasets/{id}` and print the deleted id. A missing record delete is normalized to `error=http_status` with status code 404.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_dataset_write.json`

```json
{
    "description": "Creates and deletes dataset records, including normalized not-found delete failures.",
    "cases": [
        {
            "input": {
                "feature": "dataset_write",
                "scenario": "create",
                "filename": "test.hf",
                "file_size": 20
            },
            "expected_output": "http_method=POST\npath=/api/v1/datasets\nstatus_code=201\nfilename=test.hf\nformat=job\nid=daab39ac-be9f-4de9-87c0-c4c94b297a97\n"
        },
        {
            "input": {
                "feature": "dataset_write",
                "scenario": "delete"
            },
            "expected_output": "http_method=DELETE\npath=/api/v1/datasets/daab39ac-be9f-4de9-87c0-c4c94b297a97\nstatus_code=200\ndeleted_id=daab39ac-be9f-4de9-87c0-c4c94b297a97\n"
        }
    ]
}
```

---

### Feature 4: Job Records

**As a developer**, I want to create jobs and inspect job state, so I can submit work and observe recorded status consistently.

**Expected Behavior / Usage:**

*4.1 Job Creation — Submit accepted job specifications.*

The input names a job-create operation, provides a job type, and supplies job fields. Accepted evaluation and inference specifications must POST to `/api/v1/jobs/{type}/` and print the returned id, name, and status. Unknown request fields must not be silently accepted; they are normalized to `error=schema_validation` with the failing field and validation category.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_job_create.json`

```json
{
    "description": "Creates evaluation or inference jobs from accepted request fields and reports schema validation for unknown fields.",
    "cases": [
        {
            "input": {
                "feature": "job_create",
                "job_type": "EVALUATION",
                "job": {
                    "name": "test-job-001",
                    "description": "This is a test job",
                    "model": "some_model",
                    "dataset": "6f6487ac-7170-4a11-af7a-0f6db1ec9a74",
                    "max_samples": 5,
                    "model_url": "https://huggingface.co/facebook/bart-large-cnn",
                    "system_prompt": "some prompt"
                }
            },
            "expected_output": "http_method=POST\npath=/api/v1/jobs/evaluate/\nstatus_code=200\nid=daab39ac-be9f-4de9-87c0-c4c94b297a97\nname=test-job-001\nstatus=created\n"
        },
        {
            "input": {
                "feature": "job_create",
                "job_type": "INFERENCE",
                "job": {
                    "name": "test-job-001",
                    "description": "This is a test job",
                    "model": "some_model",
                    "dataset": "6f6487ac-7170-4a11-af7a-0f6db1ec9a74"
                }
            },
            "expected_output": "http_method=POST\npath=/api/v1/jobs/inference/\nstatus_code=200\nid=daab39ac-be9f-4de9-87c0-c4c94b297a97\nname=test-job-001\nstatus=created\n"
        }
    ]
}
```

*4.2 Job Reading — List jobs and inspect worker submission status.*

The input names a job-read operation and selects collection listing, empty listing, submission lookup, or missing-submission lookup. Job listing must GET `/api/v1/jobs` and print totals plus representative first-item status when present. Submission lookup must GET `/api/v1/health/jobs/{submission_id}` and print type, status, and submission id. Missing submissions are normalized to `error=http_status`, status code 404, and the response body when one is provided.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_job_read.json`

```json
{
    "description": "Reads job collections and worker submission status, including normalized missing-submission failures.",
    "cases": [
        {
            "input": {
                "feature": "job_read",
                "scenario": "list_full"
            },
            "expected_output": "http_method=GET\npath=/api/v1/jobs\nstatus_code=200\ntotal=3\nitem_count=3\nfirst_id=daab39ac-be9f-4de9-87c0-c4c94b297a97\nfirst_status=created\n"
        },
        {
            "input": {
                "feature": "job_read",
                "scenario": "list_empty"
            },
            "expected_output": "http_method=GET\npath=/api/v1/jobs\nstatus_code=200\ntotal=0\nitem_count=0\n"
        },
        {
            "input": {
                "feature": "job_read",
                "scenario": "submission_status"
            },
            "expected_output": "http_method=GET\npath=/api/v1/health/jobs/6f6487ac-7170-4a11-af7a-0f6db1ec9a74\nstatus_code=200\ntype=SUBMISSION\nstatus=PENDING\nsubmission_id=6f6487ac-7170-4a11-af7a-0f6db1ec9a74\n"
        }
    ]
}
```

---

### Feature 5: Model Suggestions

**As a developer**, I want to retrieve model recommendations for a task, so I can select candidate model identifiers and metadata from a service response.

**Expected Behavior / Usage:**

The input names a model-suggestion operation and supplies the task name. A valid task must GET `/api/v1/models/{task}` and print total count, item count, and representative first model name and URI. An invalid task is normalized to `error=http_status` with status code 400.

**Test Cases:** `rcb_tests/public_test_cases/feature5_model_suggestions.json`

```json
{
    "description": "Retrieves suggested model metadata for a task and normalizes invalid-task HTTP failures.",
    "cases": [
        {
            "input": {
                "feature": "model_suggestions",
                "scenario": "success",
                "task": "summarization"
            },
            "expected_output": "http_method=GET\npath=/api/v1/models/summarization\nstatus_code=200\ntotal=9\nitem_count=9\nfirst_name=facebook/bart-large-cnn\nfirst_uri=hf://facebook/bart-large-cnn\n"
        },
        {
            "input": {
                "feature": "model_suggestions",
                "scenario": "invalid_task",
                "task": "invalid_task"
            },
            "expected_output": "error=http_status\nstatus_code=400\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_service_status.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_service_status@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the pattern for unsupported vendor errors as defined in the utility layer
- align with the sampling convention used in the model_suggestions module
