## Product Requirement Document

# Secret Mount Adapter - Configuration, Retrieval, and Response Contracts

## Project Goal

Build a secret mount adapter that allows developers to translate driver mount requests into validated configuration, authenticated secret retrieval requests, mounted file responses, and version metadata without hand-writing repetitive parsing, request construction, and response formatting code.

---

## Background & Problem

Without this library/tool, developers are forced to manually decode driver-supplied parameter maps, normalize secret service paths, choose request methods, encode request bodies, extract values from nested secret payloads, calculate returned object versions, and reconcile layered connection settings. This leads to duplicated parsing logic, inconsistent file permissions, fragile error handling, and difficult-to-debug integration behavior.

With this library/tool, a mount request can be processed through a single consistent contract: inputs describe configuration, secret descriptors, and runtime metadata; outputs expose only externally observable fields such as normalized paths, request method and body, mounted files, object versions, request traces, and language-neutral error categories.

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

### Feature 1: Mount Configuration Parsing

**As a developer**, I want to parse mount request attributes into normalized configuration fields, so I can inspect target location, permissions, connection options, pod identity, and secret descriptors without re-parsing provider-specific input.

**Expected Behavior / Usage:**

The adapter accepts a JSON command containing a target path, a default file permission, and a parameter map. It must parse the embedded object list into ordered secret descriptors, preserve connection and pod metadata fields, convert octal per-object permissions to decimal output, and render every resulting field as `key=value` lines.

**Test Cases:** `rcb_tests/public_test_cases/feature1_parse_mount_configuration.json`

```json
{
    "description": "Parses mount request parameters into normalized connection, pod, permission, and secret descriptor fields.",
    "cases": [
        {
            "input": {
                "action": "parse_mount_configuration",
                "target_path": "/some/path",
                "default_file_permission": 420,
                "parameters": {
                    "roleName": "example-role",
                    "vaultSkipTLSVerify": "true",
                    "objects": "-\n  secretPath: \"v1/secret/foo1\"\n  objectName: \"bar1\"\n  filePermission: 0600"
                }
            },
            "expected_output": "target_path=/some/path\nfile_permission_decimal=420\nrole=example-role\nvault_address=\nvault_namespace=\nauth_mount_path=\ntls_insecure=true\ntls_ca_cert=\ntls_ca_directory=\ntls_server_name=\ntls_client_cert=\ntls_client_key=\npod_name=\npod_uid=\npod_namespace=\npod_service_account=\naudience=\nsecrets_count=1\nsecret[0].object_name=bar1\nsecret[0].secret_path=v1/secret/foo1\nsecret[0].secret_key=\nsecret[0].method=\nsecret[0].file_permission_decimal=384\nsecret[0].args_json=null\n"
        },
        {
            "input": {
                "action": "parse_mount_configuration",
                "target_path": "/some/path",
                "default_file_permission": 420,
                "parameters": {
                    "roleName": "example-role",
                    "vaultSkipTLSVerify": "true",
                    "vaultAddress": "my-vault-address",
                    "vaultNamespace": "my-vault-namespace",
                    "vaultKubernetesMountPath": "my-mount-path",
                    "vaultCACertPath": "my-ca-cert-path",
                    "vaultCADirectory": "my-ca-directory",
                    "vaultTLSServerName": "mytls-server-name",
                    "vaultTLSClientCertPath": "my-tls-client-cert-path",
                    "vaultTLSClientKeyPath": "my-tls-client-key-path",
                    "csi.storage.k8s.io/pod.name": "my-pod-name",
                    "csi.storage.k8s.io/pod.uid": "my-pod-uid",
                    "csi.storage.k8s.io/pod.namespace": "my-pod-namespace",
                    "csi.storage.k8s.io/serviceAccount.name": "my-pod-sa-name",
                    "objects": "-\n  secretPath: \"v1/secret/foo1\"\n  objectName: \"bar1\"\n  filePermission: 0600",
                    "audience": "my-aud"
                }
            },
            "expected_output": "target_path=/some/path\nfile_permission_decimal=420\nrole=example-role\nvault_address=my-vault-address\nvault_namespace=my-vault-namespace\nauth_mount_path=my-mount-path\ntls_insecure=true\ntls_ca_cert=my-ca-cert-path\ntls_ca_directory=my-ca-directory\ntls_server_name=mytls-server-name\ntls_client_cert=my-tls-client-cert-path\ntls_client_key=my-tls-client-key-path\npod_name=my-pod-name\npod_uid=my-pod-uid\npod_namespace=my-pod-namespace\npod_service_account=my-pod-sa-name\naudience=my-aud\nsecrets_count=1\nsecret[0].object_name=bar1\nsecret[0].secret_path=v1/secret/foo1\nsecret[0].secret_key=\nsecret[0].method=\nsecret[0].file_permission_decimal=384\nsecret[0].args_json=null\n"
        }
    ]
}
```

---

### Feature 2: Configuration Validation Errors

**As a developer**, I want to receive language-neutral validation errors for invalid mount configuration, so I can surface actionable failures without leaking runtime exception types.

**Expected Behavior / Usage:**

The adapter must reject configurations that cannot produce an unambiguous mount operation. Missing target path, missing role name, an empty object list, or duplicated output object names must render as neutral `error=<category>` lines. The output must not include host-language exception class names or runtime-generated messages.

**Test Cases:** `rcb_tests/public_test_cases/feature2_configuration_validation_errors.json`

```json
{
    "description": "Rejects mount configurations that are missing required fields or contain ambiguous duplicate output object names.",
    "cases": [
        {
            "input": {
                "action": "parse_mount_configuration",
                "target_path": "/some/path",
                "default_file_permission": 420,
                "parameters": {
                    "vaultSkipTLSVerify": "true",
                    "objects": "-\n  secretPath: \"v1/secret/foo1\"\n  objectName: \"bar1\"\n  filePermission: 0600"
                }
            },
            "expected_output": "error=missing_role_name\n"
        },
        {
            "input": {
                "action": "parse_mount_configuration",
                "target_path": "/some/path",
                "default_file_permission": 420,
                "parameters": {
                    "roleName": "example-role",
                    "vaultSkipTLSVerify": "true",
                    "objects": ""
                }
            },
            "expected_output": "error=no_secrets_configured\n"
        }
    ]
}
```

---

### Feature 3: Secret API Request Rendering

**As a developer**, I want to turn a secret descriptor into an observable HTTP-style request, so I can verify path normalization, query handling, method selection, body encoding, and returned file metadata.

**Expected Behavior / Usage:**

The adapter accepts a secret path plus optional method and JSON arguments. It must ensure the API path has a `/v1/` prefix, split query parameters from the path, default the method to GET when omitted, render request body arguments as compact JSON when present, and include the mounted file signal returned by the request path.

**Test Cases:** `rcb_tests/public_test_cases/feature3_secret_api_request_rendering.json`

```json
{
    "description": "Builds a secret retrieval HTTP request from a requested secret path, optional query string, optional method, and optional JSON body arguments.",
    "cases": [
        {
            "input": {
                "action": "build_secret_request",
                "secret_path": "secret/foo"
            },
            "expected_output": "method=GET\npath=/v1/secret/foo\nquery=\nbody=\nfile_path=requested-object\nfile_mode=420\nfile_contents=ok\n"
        },
        {
            "input": {
                "action": "build_secret_request",
                "secret_path": "secret/foo?"
            },
            "expected_output": "method=GET\npath=/v1/secret/foo\nquery=\nbody=\nfile_path=requested-object\nfile_mode=420\nfile_contents=ok\n"
        }
    ]
}
```

---

### Feature 4: Secret Value Extraction

**As a developer**, I want to extract a named value from returned secret data, so I can mount plain strings directly and structured values as compact JSON while reporting missing keys predictably.

**Expected Behavior / Usage:**

The adapter accepts a secret response object and a requested key. If the response contains a nested `data` object, key lookup occurs inside that object; otherwise lookup occurs at the top level. String values are printed plainly, while numbers, arrays, and objects are printed as compact JSON. Missing keys render a neutral missing-key error and the requested key on its own line.

**Test Cases:** `rcb_tests/public_test_cases/feature4_secret_value_extraction.json`

```json
{
    "description": "Extracts one named value from a secret response, unwrapping embedded data objects and rendering strings plainly while rendering structured values as compact JSON.",
    "cases": [
        {
            "input": {
                "action": "extract_secret_value",
                "key": "foo",
                "secret_data": {
                    "foo": "bar",
                    "baz": "zap"
                }
            },
            "expected_output": "file_path=extracted-object\nfile_mode=420\nfile_contents=bar\nobject_version_id=extracted-object\nobject_version=w6uP8Tcg6K2QR905Rms8iXTlksL6OD1KOWBxTK7wxPI=\n"
        },
        {
            "input": {
                "action": "extract_secret_value",
                "key": "foo",
                "secret_data": {
                    "data": {
                        "foo": {
                            "bar": "hop",
                            "baz": "zap",
                            "cheeses": {
                                "brie": 9,
                                "cheddar": "8"
                            }
                        },
                        "baz": "zap"
                    }
                }
            },
            "expected_output": "file_path=extracted-object\nfile_mode=420\nfile_contents={\"bar\":\"hop\",\"baz\":\"zap\",\"cheeses\":{\"brie\":9,\"cheddar\":\"8\"}}\nobject_version_id=extracted-object\nobject_version=F24I8o-ZRw_747ySFVMToo96klDTZ7Gqz2oiThcDs8k=\n"
        },
        {
            "input": {
                "action": "extract_secret_value",
                "key": "non-existing",
                "secret_data": {
                    "foo": "bar",
                    "baz": "zap"
                }
            },
            "expected_output": "error=missing_secret_key\nkey=non-existing\n"
        }
    ]
}
```

---

### Feature 5: Mount Response and Cache Behavior

**As a developer**, I want to mount multiple secret objects through external API calls, so I can receive file contents, modes, object versions, and request traces that demonstrate cached reads and fresh-provider refresh behavior.

**Expected Behavior / Usage:**

The adapter accepts multiple secret descriptors and simulates mount processing through observable API traffic. Output must include each run, mounted file path, file mode, file contents, object version id and value, plus request traces with method, URL path, query, and body. Repeated mounts through the same provider instance must reuse cached secret contents; a fresh provider instance must read updated secret contents and produce different object versions.

**Test Cases:** `rcb_tests/public_test_cases/feature5_mount_response_and_cache_behavior.json`

```json
{
    "description": "Mounts multiple secret descriptors through mocked external APIs and returns files, permissions, object versions, and observable API request traffic including cache reuse.",
    "cases": [
        {
            "input": {
                "action": "mount_secrets",
                "default_file_permission": 0,
                "repeats": 3,
                "secrets": [
                    {
                        "object_name": "object-one",
                        "secret_path": "path/one",
                        "secret_key": "the-key"
                    },
                    {
                        "object_name": "object-two",
                        "secret_path": "path/two"
                    }
                ]
            },
            "expected_output": "run[0].files_count=2\nrun[0].file[0].path=object-one\nrun[0].file[0].mode=0\nrun[0].file[0].contents=secret v1 from: /v1/path/one\nrun[0].version[0].id=object-one\nrun[0].version[0].value=DJ0rHQqoExENU7dnd2SM0l3Y0nw0AfaipQfTaMzrEOw=\nrun[0].file[1].path=object-two\nrun[0].file[1].mode=0\nrun[0].file[1].contents={\"request_id\":\"\",\"lease_id\":\"\",\"lease_duration\":0,\"renewable\":false,\"data\":{\"the-key\":\"secret v1 from: /v1/path/two\"},\"warnings\":null}\nrun[0].version[1].id=object-two\nrun[0].version[1].value=nKQ7YCpTMKWSBTFmbZ4ei8Xp5nWOohJkWlV_YrvhwV4=\nrun[1].files_count=2\nrun[1].file[0].path=object-one\nrun[1].file[0].mode=0\nrun[1].file[0].contents=secret v1 from: /v1/path/one\nrun[1].version[0].id=object-one\nrun[1].version[0].value=DJ0rHQqoExENU7dnd2SM0l3Y0nw0AfaipQfTaMzrEOw=\nrun[1].file[1].path=object-two\nrun[1].file[1].mode=0\nrun[1].file[1].contents={\"request_id\":\"\",\"lease_id\":\"\",\"lease_duration\":0,\"renewable\":false,\"data\":{\"the-key\":\"secret v1 from: /v1/path/two\"},\"warnings\":null}\nrun[1].version[1].id=object-two\nrun[1].version[1].value=nKQ7YCpTMKWSBTFmbZ4ei8Xp5nWOohJkWlV_YrvhwV4=\nrun[2].files_count=2\nrun[2].file[0].path=object-one\nrun[2].file[0].mode=0\nrun[2].file[0].contents=secret v1 from: /v1/path/one\nrun[2].version[0].id=object-one\nrun[2].version[0].value=DJ0rHQqoExENU7dnd2SM0l3Y0nw0AfaipQfTaMzrEOw=\nrun[2].file[1].path=object-two\nrun[2].file[1].mode=0\nrun[2].file[1].contents={\"request_id\":\"\",\"lease_id\":\"\",\"lease_duration\":0,\"renewable\":false,\"data\":{\"the-key\":\"secret v1 from: /v1/path/two\"},\"warnings\":null}\nrun[2].version[1].id=object-two\nrun[2].version[1].value=nKQ7YCpTMKWSBTFmbZ4ei8Xp5nWOohJkWlV_YrvhwV4=\nrun[3].files_count=2\nrun[3].file[0].path=object-one\nrun[3].file[0].mode=0\nrun[3].file[0].contents=secret v2 from: /v1/path/one\nrun[3].version[0].id=object-one\nrun[3].version[0].value=9g66dQt1d5cGocIWFQltLOXvDbeYYyBgfRl62mKCoJY=\nrun[3].file[1].path=object-two\nrun[3].file[1].mode=0\nrun[3].file[1].contents={\"request_id\":\"\",\"lease_id\":\"\",\"lease_duration\":0,\"renewable\":false,\"data\":{\"the-key\":\"secret v2 from: /v1/path/two\"},\"warnings\":null}\nrun[3].version[1].id=object-two\nrun[3].version[1].value=EryArWoZ1Ok1kgS-4r5-iWfbVYgmXyU6kKZfBOM8OFE=\nrequest[0].method=POST\nrequest[0].path=/v1/auth//login\nrequest[0].query=\nrequest[0].body={\"jwt\":\"\",\"role\":\"mount-role\"}\nrequest[1].method=GET\nrequest[1].path=/v1/path/one\nrequest[1].query=\nrequest[1].body=\nrequest[2].method=GET\nrequest[2].path=/v1/path/two\nrequest[2].query=\nrequest[2].body=\nrequest[3].method=POST\nrequest[3].path=/v1/auth//login\nrequest[3].query=\nrequest[3].body={\"jwt\":\"\",\"role\":\"mount-role\"}\nrequest[4].method=GET\nrequest[4].path=/v1/path/one\nrequest[4].query=\nrequest[4].body=\nrequest[5].method=GET\nrequest[5].path=/v1/path/two\nrequest[5].query=\nrequest[5].body=\n"
        }
    ]
}
```

---

### Feature 6: Connection Settings Precedence

**As a developer**, I want to resolve service connection settings from layered sources, so I can honor the intended precedence across environment, runtime flags, and per-mount parameters.

**Expected Behavior / Usage:**

The adapter accepts connection settings from environment-like input, runtime flag-like input, and per-mount parameter input. Per-mount address and namespace override runtime flags, runtime flags override environment address, and omitted values fall back to the default service address. Certificate trust material may be supplied as either a file or directory mode and is reported as the selected mode.

**Test Cases:** `rcb_tests/public_test_cases/feature6_connection_settings_precedence.json`

```json
{
    "description": "Resolves connection settings from environment, runtime flags, and mount parameters using the documented precedence and accepts certificate trust material supplied as either file or directory.",
    "cases": [
        {
            "input": {
                "action": "resolve_connection_settings",
                "env_address": "from-env"
            },
            "expected_output": "address=from-env\nnamespace=\ntls_mode=\n"
        },
        {
            "input": {
                "action": "resolve_connection_settings",
                "env_address": "from-env",
                "flag_address": "from-flags"
            },
            "expected_output": "address=from-flags\nnamespace=\ntls_mode=\n"
        }
    ]
}
```

---

### Feature 7: Version Metadata Rendering

**As a developer**, I want to render build metadata in a stable machine-readable format, so I can report the executable version, build date, runtime version, and minimum compatible driver version.

**Expected Behavior / Usage:**

The adapter accepts build version, build date, and runtime version strings. It must render exactly one compact JSON line with those values and the minimum supported driver version field.

**Test Cases:** `rcb_tests/public_test_cases/feature7_version_metadata_rendering.json`

```json
{
    "description": "Renders provider version metadata as a single compact JSON line containing binary version, build date, runtime version, and supported driver floor.",
    "cases": [
        {
            "input": {
                "action": "render_version_metadata",
                "version": "version",
                "build_date": "Now",
                "runtime_version": "go version x.y.z"
            },
            "expected_output": "{\"version\":\"version\",\"buildDate\":\"Now\",\"goVersion\":\"go version x.y.z\",\"minDriverVersion\":\"v0.0.21\"}\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
