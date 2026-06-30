## Product Requirement Document

# Scheduler Scaling Configuration Toolkit - Standardized Runtime and Policy Contracts

## Project Goal

Build a configuration and scaling-policy processing toolkit that allows developers to load runtime settings and scheduler-provided scaling policies into stable autoscaling records without writing repetitive parsing, merging, defaulting, and validation logic.

---

## Background & Problem

Without this library/tool, developers are forced to manually combine layered configuration files, parse nested scheduler policy documents, fill defaults, normalize target identifiers, and validate policy shape before a scaling engine can safely use the data. This leads to repetitive code, inconsistent defaults, fragile error handling, and policy records that can fail late in the scaling pipeline.

With this library/tool, configuration and scaling policy documents can be accepted through a small execution adapter and converted into deterministic stdout contracts that clearly show the loaded settings, translated policy fields, canonical defaults, and normalized validation errors.

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

### Feature 1: Default Runtime Configuration

**As a developer**, I want to receive a complete baseline configuration when no settings are supplied, so I can start the system with predictable logging, connection, health endpoint, timing, and built-in plugin defaults.

**Expected Behavior / Usage:**

The input is an empty configuration request. The output is newline-delimited stdout showing the default logging mode, log level, plugin directory suffix, default evaluation interval in nanoseconds, scheduler API address, health endpoint binding, and the built-in metric-source and scaling-target plugin registrations.

**Test Cases:** `rcb_tests/public_test_cases/feature1_default_runtime_configuration.json`

```json
{
    "description": "The default configuration supplies stable runtime, connection, health endpoint, timing, and built-in plugin values when no user configuration is provided.",
    "cases": [
        {
            "input": {},
            "expected_output": "log_json=false\nlog_level=info\nplugin_dir_suffix=/plugins\ndefault_evaluation_interval_ns=10000000000\nnomad_address=http://127.0.0.1:4646\nhttp_bind_address=127.0.0.1\nhttp_bind_port=8080\napm_plugins=nomad-apm:nomad-apm\ntarget_plugins=nomad-target:nomad-target\n"
        }
    ]
}
```

---
### Feature 2: Layered Configuration Merge

**As a developer**, I want to combine multiple configuration layers deterministically, so I can apply environment-specific overrides without losing unrelated defaults or earlier nested settings.

**Expected Behavior / Usage:**

The input is an ordered array of configuration layers. Each layer may contain scalar settings, nested HTTP or scheduler connection settings, and plugin declarations. Later non-empty scalar values override earlier values, nested connection objects merge by field, plugin entries with the same name are replaced by the later declaration, and plugin entries with distinct names are retained. The output is newline-delimited stdout containing the merged scalar fields, nested fields, and sorted plugin summaries.

**Test Cases:** `rcb_tests/public_test_cases/feature2_layered_configuration_merge.json`

```json
{
    "description": "Later configuration layers override scalar values, nested endpoint fields merge field-by-field, and plugin declarations with the same name are replaced while distinct plugins are retained.",
    "cases": [
        {
            "input": [
                {
                    "PluginDir": "/opt/nomad-autoscaler/plugins",
                    "DefaultEvaluationInterval": 5000000000,
                    "HTTP": {
                        "BindAddress": "scaler.nomad"
                    },
                    "Nomad": {
                        "Address": "http://nomad.systems:4646"
                    },
                    "APMs": [
                        {
                            "Name": "prometheus",
                            "Driver": "prometheus",
                            "Config": {
                                "address": "http://prometheus.systems:9090"
                            }
                        }
                    ]
                },
                {
                    "LogLevel": "trace",
                    "LogJson": true,
                    "PluginDir": "/var/lib/nomad-autoscaler/plugins",
                    "DefaultEvaluationInterval": 10000000000,
                    "HTTP": {
                        "BindPort": 4646
                    },
                    "Nomad": {
                        "Address": "https://nomad-new.systems:4646",
                        "Region": "moon-base-1",
                        "Namespace": "fra-mauro",
                        "Token": "super-secret-tokeny-thing",
                        "HTTPAuth": "admin:admin",
                        "CACert": "/etc/nomad.d/ca.crt",
                        "CAPath": "/etc/nomad.d/ca/",
                        "ClientCert": "/etc/nomad.d/client.crt",
                        "ClientKey": "/etc/nomad.d/client-key.crt",
                        "TLSServerName": "cows-or-pets",
                        "SkipVerify": true
                    },
                    "APMs": [
                        {
                            "Name": "influx-db",
                            "Driver": "influx-db"
                        },
                        {
                            "Name": "prometheus",
                            "Driver": "prometheus",
                            "Args": [
                                "all-the-encryption"
                            ],
                            "Config": {
                                "address": "http://prometheus-new.systems:9090"
                            }
                        }
                    ],
                    "Strategies": [
                        {
                            "Name": "target-value",
                            "Driver": "target-value"
                        }
                    ]
                }
            ],
            "expected_output": "log_json=true\nlog_level=trace\nplugin_dir=/var/lib/nomad-autoscaler/plugins\ndefault_evaluation_interval_ns=10000000000\nhttp_bind_address=scaler.nomad\nhttp_bind_port=4646\nnomad_address=https://nomad-new.systems:4646\nnomad_region=moon-base-1\nnomad_namespace=fra-mauro\nnomad_token=super-secret-tokeny-thing\nnomad_http_auth=admin:admin\nnomad_ca_cert=/etc/nomad.d/ca.crt\nnomad_ca_path=/etc/nomad.d/ca/\nnomad_client_cert=/etc/nomad.d/client.crt\nnomad_client_key=/etc/nomad.d/client-key.crt\nnomad_tls_server_name=cows-or-pets\nnomad_skip_verify=true\napm_plugins=influx-db:influx-db,nomad-apm:nomad-apm,prometheus:prometheus args=[all-the-encryption] config={address=http://prometheus-new.systems:9090}\ntarget_plugins=nomad-target:nomad-target\nstrategy_plugins=target-value:target-value\n"
        }
    ]
}
```

---
### Feature 3: Configuration File Loading

**As a developer**, I want to load configuration from either a single file or a directory, so I can support operational deployments that split settings across files while ignoring editor scratch files.

**Expected Behavior / Usage:**

The input describes either a missing path, a single configuration file, or a directory containing named files and their contents. A missing path emits a normalized path error. A single valid file emits the parsed timing and plugin directory fields. A directory load considers only configuration files, ignores editor temporary files and unrelated extensions, sorts eligible files by name, merges them in that order, and emits the resulting timing and plugin directory fields. A malformed eligible configuration file emits a normalized parse error.

**Test Cases:** `rcb_tests/public_test_cases/feature3_configuration_file_loading.json`

```json
{
    "description": "Configuration loading accepts a single file or a directory of configuration files, merges directory files in name order, ignores editor temporary files, and reports missing or malformed inputs as normalized errors.",
    "cases": [
        {
            "input": {
                "path": "missing"
            },
            "expected_output": "error=path_not_found\n"
        },
        {
            "input": {
                "path": "file",
                "files": [
                    {
                        "name": "main.hcl",
                        "content": "default_evaluation_interval = \"10s\""
                    }
                ]
            },
            "expected_output": "default_evaluation_interval_ns=10000000000\nplugin_dir=\n"
        },
        {
            "input": {
                "path": "dir",
                "files": [
                    {
                        "name": "config1.hcl",
                        "content": "default_evaluation_interval = \"10s\""
                    },
                    {
                        "name": "config2.hcl",
                        "content": "plugin_dir = \"/opt/nomad-autoscaler/plugins\""
                    }
                ]
            },
            "expected_output": "default_evaluation_interval_ns=10000000000\nplugin_dir=/opt/nomad-autoscaler/plugins\n"
        }
    ]
}
```

---
### Feature 4: Scaling Policy Translation

**As a developer**, I want to translate a scheduler scaling document into an autoscaling policy record, so I can feed downstream scaling engines with a consistent policy representation.

**Expected Behavior / Usage:**

The input is a scheduler scaling policy document containing identifiers, min/max bounds, enabled state, target attributes, and a nested policy object with source, query, interval, target block, and strategy block data. Translation is best-effort: valid typed values are copied, duration strings become nanoseconds, nested config values are rendered as strings, target attributes are merged into target config, and malformed optional blocks are omitted instead of causing an error. The output is newline-delimited stdout containing the translated policy fields and nested target/strategy summaries.

**Test Cases:** `rcb_tests/public_test_cases/feature4_scaling_policy_translation.json`

```json
{
    "description": "A scheduler scaling policy document is translated into the internal autoscaling policy shape using best-effort conversion of durations, booleans, limits, target settings, and strategy settings.",
    "cases": [
        {
            "input": {
                "id": "id",
                "min": 1,
                "max": 5,
                "policy": {
                    "source": "source",
                    "query": "query",
                    "evaluation_interval": "5s",
                    "target": [
                        {
                            "name": "target",
                            "config": [
                                {
                                    "int_config": 2
                                }
                            ]
                        }
                    ],
                    "strategy": [
                        {
                            "name": "strategy",
                            "config": [
                                {
                                    "bool_config": true
                                }
                            ]
                        }
                    ]
                },
                "target": {
                    "Namespace": "namespace",
                    "Job": "example",
                    "Group": "cache"
                },
                "enabled": true,
                "namespace": "default"
            },
            "expected_output": "id=id\nmin=1\nmax=5\nenabled=true\nsource=source\nquery=query\nevaluation_interval_ns=5000000000\ntarget_name=target\ntarget_config={Group=cache,Job=example,Namespace=namespace,int_config=2}\nstrategy_name=strategy\nstrategy_config={bool_config=true}\n"
        },
        {
            "input": {},
            "expected_output": "id=\nmin=0\nmax=0\nenabled=true\nsource=\nquery=\nevaluation_interval_ns=0\n[a specific sentinel string indicating null or missing nested structures]\n[a specific sentinel string indicating null or missing nested structures]\n"
        }
    ]
}
```

---
### Feature 5: Scaling Policy Canonicalization

**As a developer**, I want to fill in defaults and normalize translated scaling policies, so I can ensure downstream scaling engines receive a complete and consistently addressed policy.

**Expected Behavior / Usage:**

The input is either a translated policy record, null, or a translated policy with an optional default evaluation interval supplied by the runtime. Null input remains null. Non-null policies receive a default evaluation interval when absent, empty target and strategy records when absent, a built-in target name when target name is empty, empty config maps where needed, copied scheduler target fields under plugin-facing keys when those keys are absent, and a built-in metric source when source is empty. If the built-in metric source is active and the query is a short operation-metric form without slashes, the query is expanded to include group and job identifiers from target config. The output is newline-delimited stdout containing the canonical policy fields and nested summaries.

**Test Cases:** `rcb_tests/public_test_cases/feature5_scaling_policy_canonicalization.json`

```json
{
    "description": "A translated autoscaling policy is canonicalized by adding defaults, mapping scheduler target fields into plugin target fields, and expanding short built-in metric queries when applicable.",
    "cases": [
        {
            "input": {
                "policy": {
                    "id": "string",
                    "min": 1,
                    "max": 5,
                    "source": "source",
                    "query": "query",
                    "enabled": true,
                    "evaluation_interval_ns": 1000000000,
                    "target": {
                        "name": "target",
                        "config": {
                            "target_config": "yes",
                            "target_config2": "no",
                            "Job": "job",
                            "Group": "group"
                        }
                    },
                    "strategy": {
                        "name": "strategy",
                        "config": {
                            "strategy_config1": "yes",
                            "strategy_config2": "no"
                        }
                    }
                }
            },
            "expected_output": "id=string\nmin=1\nmax=5\nenabled=true\nsource=source\nquery=query\nevaluation_interval_ns=1000000000\ntarget_name=target\ntarget_config={Group=group,Job=job,group=group,job_id=job,target_config=yes,target_config2=no}\nstrategy_name=strategy\nstrategy_config={strategy_config1=yes,strategy_config2=no}\n"
        },
        {
            "input": {
                "policy": {}
            },
            "expected_output": "id=\nmin=0\nmax=0\nenabled=false\nsource=nomad-apm\nquery=\nevaluation_interval_ns=10000000000\ntarget_name=nomad-target\ntarget_config={}\nstrategy_name=\nstrategy_config={}\n"
        },
        {
            "input": null,
            "expected_output": "[a specific sentinel indicating no policy was provided]\n"
        }
    ]
}
```

---
### Feature 6: Scaling Policy Validation

**As a developer**, I want to validate scheduler scaling policy documents before translation, so I can reject incomplete or malformed scaling definitions with stable domain errors.

**Expected Behavior / Usage:**

The input is a scheduler scaling policy document or null. Valid documents must include an ID, target attributes, a non-negative min pointer, a non-negative max, min not greater than max, a policy object, a non-empty string query, an optional string source, an optional duration string in duration format, a required single strategy block with a non-empty string name, and optional target/config blocks with valid shapes. Accepted policies emit key identifying fields. Invalid policies emit one or more normalized error category lines without runtime-specific type names or exception text.

**Test Cases:** `rcb_tests/public_test_cases/feature6_scaling_policy_validation.json`

```json
{
    "description": "A scheduler scaling policy document is accepted only when required top-level fields, numeric bounds, query fields, duration strings, and nested block shapes are valid.",
    "cases": [
        {
            "input": {
                "id": "id",
                "min": 1,
                "max": 5,
                "policy": {
                    "source": "source",
                    "query": "query",
                    "evaluation_interval": "5s",
                    "strategy": [
                        {
                            "name": "strategy",
                            "config": [
                                {
                                    "key": "value"
                                }
                            ]
                        }
                    ],
                    "target": [
                        {
                            "name": "target",
                            "config": [
                                {
                                    "key": "value"
                                }
                            ]
                        }
                    ]
                },
                "target": {
                    "key": "value"
                },
                "enabled": true,
                "namespace": "default"
            },
            "expected_output": "validation=accepted\nid=id\nmin=1\nmax=5\nquery=query\nstrategy=strategy\n"
        },
        {
            "input": {
                "id": "id",
                "min": 1,
                "max": 5,
                "policy": {
                    "query": "query",
                    "strategy": [
                        {
                            "name": "strategy"
                        }
                    ]
                },
                "target": {
                    "key": "value"
                }
            },
            "expected_output": "validation=accepted\nid=id\nmin=1\nmax=5\nquery=query\nstrategy=strategy\n"
        },
        {
            "input": null,
            "expected_output": "error=policy_missing\n"
        },
        {
            "input": {},
            "expected_output": "error=id_missing\nerror=min_missing\nerror=target_missing\nerror=policy_missing\n"
        },
        {
            "input": {
                "id": "",
                "min": 1,
                "max": 5,
                "policy": {
                    "query": "query",
                    "strategy": [
                        {
                            "name": "strategy"
                        }
                    ]
                },
                "target": {
                    "key": "value"
                }
            },
            "expected_output": "error=id_missing\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the same default directory prefix as the plugin discovery module
- check how the duplicater logic orders unique plugins
