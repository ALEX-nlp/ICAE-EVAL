## Product Requirement Document

# Build-Time Constants Generator - Compile-Time Source Generation for Project Metadata

## Project Goal

Build a build-tool extension that generates source files containing project constants so developers can expose stable metadata and configuration values to application code without manually maintaining repetitive constants classes.

---

## Background & Problem

Without this library/tool, developers are forced to hand-write constants source files for project names, feature flags, generated timestamps, resource identifiers, and test-only metadata. This leads to duplicated boilerplate, stale values, and mistakes when the same constants must be available across production and test source groups.

With this library/tool, developers describe constants once in build configuration and receive compile-ready generated source files in the appropriate source group, language style, namespace, and cacheable build task.

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

### Feature 1: Main Java Constants Source

**As a developer**, I want to generate a primary constants source file from configured values, so I can use project metadata and build-time values from application code.

**Expected Behavior / Usage:**

The input describes a project using Java output, an optional group, an explicit namespace, and a list of constants. The adapter must run the build generation task and print `build_status=success`, the task name, the generated file path, and the full source text. Text values are emitted as text constants, boolean values as boolean constants, and long numeric values as long constants. Long epoch-like values may be normalized to `<not_future_epoch_ms>L` in stdout so the contract checks that the generated timestamp-like value is not in the future rather than binding to wall-clock time.

**Test Cases:** `rcb_tests/public_test_cases/feature1_main_java_constants.json`

```json
{
    "description": "Generating primary Java constants creates a compile-ready source file containing all configured primitive and text constants in declaration order.",
    "cases": [
        {
            "input": {
                "language": "java",
                "project_name": "test-project",
                "group": "gs.test",
                "namespace": "gs.test",
                "fields": [
                    {
                        "type": "String",
                        "name": "APP_NAME",
                        "value": "\"test-project\""
                    },
                    {
                        "type": "String",
                        "name": "APP_SECRET",
                        "value": "\"Z3JhZGxlLWphdmEtYnVpbGRjb25maWctcGx1Z2lu\""
                    },
                    {
                        "type": "long",
                        "name": "BUILD_TIME",
                        "value": "1234567890000L"
                    },
                    {
                        "type": "boolean",
                        "name": "FEATURE_ENABLED",
                        "value": "true"
                    }
                ]
            },
            "expected_output": "build_status=success\ntask=generateBuildConfig\nfile=build/generated/sources/buildConfig/main/gs/test/BuildConfig.java\n--- source ---\npackage gs.test;\n\nimport java.lang.String;\n\npublic final class BuildConfig {\n  public static final String APP_NAME = \"test-project\";\n\n  public static final String APP_SECRET = \"Z3JhZGxlLWphdmEtYnVpbGRjb25maWctcGx1Z2lu\";\n\n  public static final long BUILD_TIME = <not_future_epoch_ms>L;\n\n  public static final boolean FEATURE_ENABLED = true;\n\n  private BuildConfig() {\n  }\n}\n--- end source ---\n"
        }
    ]
}
```

---

### Feature 2: Default Namespace Derivation

**As a developer**, I want to generate source under a safe namespace when no namespace is supplied, so I can avoid requiring users to configure a namespace for simple projects.

**Expected Behavior / Usage:**

The input describes Java output with a project identity and no explicit namespace. The generated file must be placed under a sanitized namespace derived from the project identity, replacing characters that are not valid namespace characters with underscores. Stdout must include the generated path and source so the namespace can be verified directly.

**Test Cases:** `rcb_tests/public_test_cases/feature2_default_namespace.json`

```json
{
    "description": "When no namespace is explicitly provided, the generated source is placed under a sanitized namespace derived from the project identity.",
    "cases": [
        {
            "input": {
                "language": "java",
                "project_name": "test-project",
                "fields": [
                    {
                        "type": "String",
                        "name": "APP_NAME",
                        "value": "\"test-project\""
                    }
                ]
            },
            "expected_output": "build_status=success\ntask=generateBuildConfig\nfile=build/generated/sources/buildConfig/main/test_project/BuildConfig.java\n--- source ---\npackage test_project;\n\nimport java.lang.String;\n\npublic final class BuildConfig {\n  public static final String APP_NAME = \"test-project\";\n\n  private BuildConfig() {\n  }\n}\n--- end source ---\n"
        }
    ]
}
```

---

### Feature 3: Additional Constants Type

**As a developer**, I want to generate more than one constants type in the same source group, so I can separate unrelated constants without creating another project.

**Expected Behavior / Usage:**

The input describes a primary constants type and an additional type with its own constant list. The generation task must emit both compile-ready files. Stdout must list each generated file and source body, showing that the primary type keeps its own fields and the additional type contains the secondary fields.

**Test Cases:** `rcb_tests/public_test_cases/feature3_additional_constants_type.json`

```json
{
    "description": "A secondary constants type can be generated beside the primary type and contains only the constants configured for that secondary output.",
    "cases": [
        {
            "input": {
                "language": "java",
                "project_name": "test-project",
                "group": "gs.test",
                "namespace": "gs.test",
                "fields": [
                    {
                        "type": "String",
                        "name": "APP_NAME",
                        "value": "\"test-project\""
                    }
                ],
                "extra_types": [
                    {
                        "type_name": "BuildResources",
                        "fields": [
                            {
                                "type": "String",
                                "name": "A_CONSTANT",
                                "value": "\"aConstant\""
                            }
                        ]
                    }
                ]
            },
            "expected_output": "build_status=success\ntask=generateBuildConfig\nfile=build/generated/sources/buildConfig/main/gs/test/BuildConfig.java\n--- source ---\npackage gs.test;\n\nimport java.lang.String;\n\npublic final class BuildConfig {\n  public static final String APP_NAME = \"test-project\";\n\n  private BuildConfig() {\n  }\n}\n--- end source ---\nfile=build/generated/sources/buildConfig/main/gs/test/BuildResources.java\n--- source ---\npackage gs.test;\n\nimport java.lang.String;\n\npublic final class BuildResources {\n  public static final String A_CONSTANT = \"aConstant\";\n\n  private BuildResources() {\n  }\n}\n--- end source ---\n"
        }
    ]
}
```

---

### Feature 4: Test Source Group Constants

**As a developer**, I want to generate constants for a test source group, so I can use test-only values without mixing them into production output.

**Expected Behavior / Usage:**

The input describes production constants plus test-only constants and selects the test source group. The adapter must run the test constants generation task and print the generated test output path and source. The source must use the test-specific type name and contain only the test-only constants for that generated file.

**Test Cases:** `rcb_tests/public_test_cases/feature4_test_source_set_constants.json`

```json
{
    "description": "Constants configured for the test source group are generated in the test output location with the test-specific type name and values.",
    "cases": [
        {
            "input": {
                "language": "java",
                "project_name": "test-project",
                "group": "gs.test",
                "namespace": "gs.test",
                "fields": [
                    {
                        "type": "String",
                        "name": "APP_NAME",
                        "value": "\"test-project\""
                    }
                ],
                "test_fields": [
                    {
                        "type": "String",
                        "name": "TEST_CONSTANT",
                        "value": "\"aTestValue\""
                    }
                ],
                "source_set": "test"
            },
            "expected_output": "build_status=success\ntask=generateTestBuildConfig\nfile=build/generated/sources/buildConfig/test/gs/test/TestBuildConfig.java\n--- source ---\npackage gs.test;\n\nimport java.lang.String;\n\npublic final class TestBuildConfig {\n  public static final String TEST_CONSTANT = \"aTestValue\";\n\n  private TestBuildConfig() {\n  }\n}\n--- end source ---\n"
        }
    ]
}
```

---

### Feature 5: Kotlin Object Constants

**As a developer**, I want to generate Kotlin constants in an object container, so I can use generated constants idiomatically from Kotlin application code.

**Expected Behavior / Usage:**

The input describes Kotlin output with scalar constants. The generated file must contain a namespace declaration, required imports, an object container, and const properties for supported scalar values. Stdout must include the generated path and full source text.

**Test Cases:** `rcb_tests/public_test_cases/feature5_kotlin_object_constants.json`

```json
{
    "description": "Kotlin output generates an object-style constants source with const properties for supported scalar values.",
    "cases": [
        {
            "input": {
                "language": "kotlin",
                "project_name": "test-project",
                "group": "gs.test",
                "namespace": "gs.test",
                "fields": [
                    {
                        "type": "String",
                        "name": "APP_NAME",
                        "value": "\"test-project\""
                    },
                    {
                        "type": "boolean",
                        "name": "FEATURE_ENABLED",
                        "value": "true"
                    }
                ]
            },
            "expected_output": "build_status=success\ntask=generateBuildConfig\nfile=build/generated/sources/buildConfig/main/gs/test/BuildConfig.kt\n--- source ---\npackage gs.test\n\nimport kotlin.Boolean\nimport kotlin.String\n\ninternal object BuildConfig {\n  internal const val APP_NAME: String = \"test-project\"\n\n  internal const val FEATURE_ENABLED: Boolean = true\n}\n--- end source ---\n"
        }
    ]
}
```

---

### Feature 6: Kotlin Top-Level Constants

**As a developer**, I want to generate Kotlin constants at file scope, so I can use constants without an object container when that output style is requested.

**Expected Behavior / Usage:**

The input describes Kotlin output with the top-level constants style selected. The generated file must contain namespace and import declarations followed by file-scope const properties, with no enclosing object container. Stdout must include the generated path and full source text.

**Test Cases:** `rcb_tests/public_test_cases/feature6_kotlin_top_level_constants.json`

```json
{
    "description": "Kotlin output can be configured to emit constants at file scope instead of wrapping them in an object container.",
    "cases": [
        {
            "input": {
                "language": "kotlin",
                "project_name": "test-project",
                "group": "gs.test",
                "namespace": "gs.test",
                "output_style": "top_level_constants",
                "fields": [
                    {
                        "type": "String",
                        "name": "APP_NAME",
                        "value": "\"test-project\""
                    },
                    {
                        "type": "boolean",
                        "name": "FEATURE_ENABLED",
                        "value": "true"
                    }
                ]
            },
            "expected_output": "build_status=success\ntask=generateBuildConfig\nfile=build/generated/sources/buildConfig/main/gs/test/BuildConfig.kt\n--- source ---\npackage gs.test\n\nimport kotlin.Boolean\nimport kotlin.String\n\ninternal const val APP_NAME: String = \"test-project\"\n\ninternal const val FEATURE_ENABLED: Boolean = true\n--- end source ---\n"
        }
    ]
}
```

---

### Feature 7: Field Declaration Ordering

**As a developer**, I want to preserve user-declared constant order, so I can make generated source predictable and stable.

**Expected Behavior / Usage:**

The input describes multiple constants in a deliberate sequence. The generated source must declare constants in the same sequence, and stdout must include the full source so the order can be verified from the field declarations rather than a summary flag.

**Test Cases:** `rcb_tests/public_test_cases/feature7_field_ordering.json`

```json
{
    "description": "Constants appear in the generated source in the same order they are declared by the user.",
    "cases": [
        {
            "input": {
                "language": "java",
                "project_name": "ordered-project",
                "namespace": "ordered_project",
                "fields": [
                    {
                        "type": "int",
                        "name": "FIRST",
                        "value": "1"
                    },
                    {
                        "type": "int",
                        "name": "SECOND",
                        "value": "2"
                    },
                    {
                        "type": "int",
                        "name": "THIRD",
                        "value": "3"
                    },
                    {
                        "type": "int",
                        "name": "LAST",
                        "value": "9"
                    }
                ]
            },
            "expected_output": "build_status=success\ntask=generateBuildConfig\nfile=build/generated/sources/buildConfig/main/ordered_project/BuildConfig.java\n--- source ---\npackage ordered_project;\n\npublic final class BuildConfig {\n  public static final int FIRST = 1;\n\n  public static final int SECOND = 2;\n\n  public static final int THIRD = 3;\n\n  public static final int LAST = 9;\n\n  private BuildConfig() {\n  }\n}\n--- end source ---\n"
        }
    ]
}
```

---

### Feature 8: Java Generation Cacheability

**As a developer**, I want to reuse Java generation outputs from the build cache, so I can avoid repeated generation work when inputs are unchanged.

**Expected Behavior / Usage:**

The input describes a Java constants project and asks for a cache check. The adapter must run a clean build twice with the same inputs and print the build status and generation task outcome for each run. The first run should execute successfully and the second run should restore the generation task from cache.

**Test Cases:** `rcb_tests/public_test_cases/feature8_java_cacheability.json`

```json
{
    "description": "A Java constants generation task is reusable from the build cache when the inputs are unchanged across clean builds.",
    "cases": [
        {
            "input": {
                "mode": "cache_check",
                "language": "java",
                "project_name": "cache-project",
                "namespace": "cache_project",
                "fields": [
                    {
                        "type": "String",
                        "name": "SOME_FIELD",
                        "value": "\"aValue\""
                    }
                ]
            },
            "expected_output": "first_build_status=success\nfirst_generate_outcome=SUCCESS\nsecond_build_status=success\nsecond_generate_outcome=FROM_CACHE\n"
        }
    ]
}
```

---

### Feature 9: Kotlin Generation Cacheability and Option Changes

**As a developer**, I want to reuse unchanged Kotlin generation outputs while invalidating cache when the output shape changes, so I can get fast builds without serving stale generated source after configuration changes.

**Expected Behavior / Usage:**

The input describes a Kotlin constants project and asks for a cache check followed by an output-style change. The adapter must run two clean builds with unchanged inputs and then a third clean build after changing the output style. Stdout must show that the unchanged second run uses the cache and the changed third run executes successfully rather than reusing stale output.

**Test Cases:** `rcb_tests/public_test_cases/feature9_kotlin_cacheability_and_option_change.json`

```json
{
    "description": "A Kotlin constants generation task is reusable from cache for unchanged inputs, and changing the output shape invalidates the cached result.",
    "cases": [
        {
            "input": {
                "mode": "cache_check",
                "language": "kotlin",
                "project_name": "cache-project-kotlin",
                "namespace": "cache_project_kotlin",
                "fields": [
                    {
                        "type": "String",
                        "name": "SOME_FIELD",
                        "value": "\"aValue\""
                    }
                ],
                "output_style_after_second_build": "top_level_constants"
            },
            "expected_output": "first_build_status=success\nfirst_generate_outcome=SUCCESS\nsecond_build_status=success\nsecond_generate_outcome=FROM_CACHE\nthird_build_status=success\nthird_generate_outcome=SUCCESS\n"
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
- follow the property naming convention used in the top-level module
- match the constructor signature defined in the DocStrings module
