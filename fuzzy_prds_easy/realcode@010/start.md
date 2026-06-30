## Product Requirement Document

# SQL Database Project Builder - Package Compilation and Validation

## Project Goal

Build a database project packaging tool that allows developers to compile SQL schema files, deployment scripts, and project references into a portable database package without manually stitching schema models and deployment artifacts together.

---

## Background & Problem

Without this library/tool, developers are forced to hand-manage which SQL files belong to the database model, which scripts are deployment-only, and how cross-project schema dependencies are supplied. This leads to repetitive project-file edits, fragile build pipelines, and packages that may silently include or omit the wrong database objects.

With this library/tool, a project can be built through a standard project description: schema SQL becomes model objects, deployment-only scripts are attached as package payloads, references satisfy dependencies, and unresolved references are reported as actionable diagnostics.

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

### Feature 1: Basic Schema Packaging

**As a developer**, I want to build a database project from ordinary SQL schema files, so I can produce a package that contains the compiled database model.

**Expected Behavior / Usage:**

The input is an object containing a `sql_files` map from relative file paths to SQL text. Files that define schema objects participate in the project build by default. The adapter prints the build exit code, whether a package was produced, the sorted table and view names discovered in the package model, whether deployment script payloads are attached, and a normalized diagnostic summary. A successful schema-only build has `exit_code=0`, `package_exists=true`, no deployment scripts, and `diagnostics=none`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_basic_schema_packaging.json`

```json
{
    "description": "Build a database project from a single table definition and report the resulting package status, included schema objects, deployment script attachment status, and diagnostic summary.",
    "cases": [
        {
            "input": {
                "sql_files": {
                    "Table1.sql": "CREATE TABLE [dbo].[Table1]\n(\n\tc1 int NOT NULL PRIMARY KEY,\n\tc2 int NULL\n)\n"
                }
            },
            "expected_output": "exit_code=0\npackage_exists=true\ntables=[dbo].[Table1]\nviews=\npre_deploy_script=[ensure the default state is unset when no deployment steps are provided]\npost_deploy_script=[ensure the default state is unset when no deployment steps are provided]\ndiagnostics=none\n"
        }
    ]
}
```

---

### Feature 2: Deployment Script Attachment

**As a developer**, I want to mark SQL scripts as deployment-time payloads, so I can include setup or migration statements in the package without treating them as schema model definitions.

**Expected Behavior / Usage:**

The input is an object containing `sql_files` plus either a `pre_deploy` array or a `post_deploy` array of relative script paths. Scripts listed as pre-deployment payloads must make the built package report `pre_deploy_script=true`; scripts listed as post-deployment payloads must make it report `post_deploy_script=true`. Deployment-only script contents are attached to the package and are not reported as schema tables or views unless separate schema files define those objects.

**Test Cases:** `rcb_tests/public_test_cases/feature2_deployment_scripts.json`

```json
{
    "description": "Attach deployment-only SQL scripts to a database project and report whether the built package carries pre-deployment or post-deployment script payloads without adding those scripts as schema objects.",
    "cases": [
        {
            "input": {
                "sql_files": {
                    "Table1.sql": "CREATE TABLE [dbo].[Table1]\n(\n\tc1 int NOT NULL PRIMARY KEY,\n\tc2 int NULL\n)\n",
                    "Script.PreDeployment1.sql": "-- This file contains SQL statements that will be executed before the build script.\nCREATE TABLE Table2 (ID INT NOT NULL, COL1 INT NULL)\nGO\n"
                },
                "pre_deploy": [
                    "Script.PreDeployment1.sql"
                ]
            },
            "expected_output": "exit_code=0\npackage_exists=true\ntables=[dbo].[Table1]\nviews=\npre_deploy_script=true\npost_deploy_script=[ensure the default state is unset when no deployment steps are provided]\ndiagnostics=none\n"
        },
        {
            "input": {
                "sql_files": {
                    "Table1.sql": "CREATE TABLE [dbo].[Table1]\n(\n\tc1 int NOT NULL PRIMARY KEY,\n\tc2 int NULL\n)\n",
                    "Script.PostDeployment1.sql": "-- This file contains SQL statements that will be executed after the build script.\nINSERT INTO Table1 VALUES (1, 2)\nGO\nINSERT INTO Table1 VALUES (3, 4)\nGO\n"
                },
                "post_deploy": [
                    "Script.PostDeployment1.sql"
                ]
            },
            "expected_output": "exit_code=0\npackage_exists=true\ntables=[dbo].[Table1]\nviews=\npre_deploy_script=[ensure the default state is unset when no deployment steps are provided]\npost_deploy_script=true\ndiagnostics=none\n"
        }
    ]
}
```

---

### Feature 3: Schema File Selection

**As a developer**, I want to explicitly include or exclude SQL files from schema compilation, so I can control exactly which objects appear in the database package.

**Expected Behavior / Usage:**

The input is an object containing project-local `sql_files` and optional selection controls. `remove_build` lists project-local paths or glob patterns that must be removed from schema compilation even if matching files exist. `none` lists SQL files that remain in the project directory but are classified as non-schema content. `external_sql_files` provides SQL files outside the project root, and `build` can explicitly include those external files by path. The output reports only objects from files that participate in schema compilation.

**Test Cases:** `rcb_tests/public_test_cases/feature3_schema_file_selection.json`

```json
{
    "description": "Control which SQL files participate in schema compilation and report only the schema objects contributed by files that remain in the build set.",
    "cases": [
        {
            "input": {
                "sql_files": {
                    "Table1.sql": "CREATE TABLE [dbo].[Table1]\n(\n\tc1 int NOT NULL PRIMARY KEY,\n\tc2 int NULL\n)\n",
                    "Table2.sql": "-- This file to be excluded from project by the test\nCREATE TABLE [dbo].[Table2]\n(\n\tc1 int NOT NULL PRIMARY KEY,\n\tc2 int NULL\n)\n"
                },
                "remove_build": [
                    "Table2.sql"
                ]
            },
            "expected_output": "exit_code=0\npackage_exists=true\ntables=[dbo].[Table1]\nviews=\npre_deploy_script=[ensure the default state is unset when no deployment steps are provided]\npost_deploy_script=[ensure the default state is unset when no deployment steps are provided]\ndiagnostics=none\n"
        },
        {
            "input": {
                "sql_files": {
                    "Table1.sql": "CREATE TABLE [dbo].[Table1]\n(\n\tc1 int NOT NULL PRIMARY KEY,\n\tc2 int NULL\n)\n",
                    "Table2.sql": "-- This file to be excluded from project by the test\nCREATE TABLE [dbo].[Table2]\n(\n\tc1 int NOT NULL PRIMARY KEY,\n\tc2 int NULL\n)\n"
                },
                "none": [
                    "Table2.sql"
                ]
            },
            "expected_output": "exit_code=0\npackage_exists=true\ntables=[dbo].[Table1]\nviews=\npre_deploy_script=[ensure the default state is unset when no deployment steps are provided]\npost_deploy_script=[ensure the default state is unset when no deployment steps are provided]\ndiagnostics=none\n"
        },
        {
            "input": {
                "sql_files": {
                    "Table1.sql": "CREATE TABLE [dbo].[Table1]\n(\n\tc1 int NOT NULL PRIMARY KEY,\n\tc2 int NULL\n)\n"
                },
                "external_sql_files": {
                    "test.sql": "CREATE TABLE [dbo].[Table2] ( C1 INT NOT NULL )"
                },
                "build": [
                    "/external/test.sql"
                ]
            },
            "expected_output": "exit_code=0\npackage_exists=true\ntables=[dbo].[Table1],[dbo].[Table2]\nviews=\npre_deploy_script=[ensure the default state is unset when no deployment steps are provided]\npost_deploy_script=[ensure the default state is unset when no deployment steps are provided]\ndiagnostics=none\n"
        }
    ]
}
```

---

### Feature 4: Project Reference Resolution

**As a developer**, I want to one database project to reference another database project, so I can satisfy schema validation with dependencies defined outside the current project while keeping the current package focused on its own objects.

**Expected Behavior / Usage:**

The input is an object containing current-project `sql_files` and either `project_references` that create referenced projects outside the current project root or `nested_project_references` and `project_reference_paths` that describe referenced projects already present under the current root. Referenced projects supply schema objects for dependency resolution. Objects from the referenced project are not reported as current package objects; objects defined by the current project that depend on those references are reported when the build succeeds. If a referenced project is stored below the current project directory, `remove_build` can exclude that subtree from the current project's own schema file glob so it is used only as a reference.

**Test Cases:** `rcb_tests/public_test_cases/feature4_reference_resolution.json`

```json
{
    "description": "Resolve dependencies from referenced database projects and report that schema objects depending on referenced objects compile into the requesting project package.",
    "cases": [
        {
            "input": {
                "sql_files": {
                    "View1.sql": "-- This view references Table1 which is created in the referenced project\nCREATE VIEW [dbo].[View1]\n  AS SELECT * FROM [Table1]\n"
                },
                "project_references": [
                    {
                        "path": "/external/ReferenceProj/ReferenceProj.sqlproj",
                        "sql_files": {
                            "Table1.sql": "CREATE TABLE [dbo].[Table1]\n(\n\tc1 int NOT NULL PRIMARY KEY,\n\tc2 int NULL\n)\n"
                        }
                    }
                ]
            },
            "expected_output": "exit_code=0\npackage_exists=true\ntables=\nviews=[dbo].[View1]\npre_deploy_script=[ensure the default state is unset when no deployment steps are provided]\npost_deploy_script=[ensure the default state is unset when no deployment steps are provided]\ndiagnostics=none\n"
        },
        {
            "input": {
                "sql_files": {
                    "View1.sql": "-- This view references Table1 which is created in the referenced project\nCREATE VIEW [dbo].[View1]\n  AS SELECT * FROM [Table1]\n"
                },
                "nested_project_references": [
                    {
                        "path": "ReferenceProj/ReferenceProj.sqlproj",
                        "sql_files": {
                            "Table1.sql": "CREATE TABLE [dbo].[Table1]\n(\n\tc1 int NOT NULL PRIMARY KEY,\n\tc2 int NULL\n)\n"
                        }
                    }
                ],
                "project_reference_paths": [
                    "ReferenceProj/ReferenceProj.sqlproj"
                ],
                "remove_build": [
                    "ReferenceProj/**/*.*"
                ]
            },
            "expected_output": "exit_code=0\npackage_exists=true\ntables=\nviews=[dbo].[View1]\npre_deploy_script=[ensure the default state is unset when no deployment steps are provided]\npost_deploy_script=[ensure the default state is unset when no deployment steps are provided]\ndiagnostics=none\n"
        }
    ]
}
```

---

### Feature 5: Unresolved Reference Diagnostics

**As a developer**, I want to invalid schema references to fail the build with a stable diagnostic, so I can detect missing database objects without depending on host-language exception details.

**Expected Behavior / Usage:**

The input is an object containing SQL schema files. If a schema object references another object that is not defined in the project and not supplied by any referenced project, the build fails and no package is reported. The diagnostic line is normalized as `error_code=[specify the upper threshold for diagnostic generation during build failure];object=<referencing-object>;referenced=<missing-object>`, preserving the domain error code and object names while omitting runtime-specific stack traces, exception types, paths, and localized prose.

**Test Cases:** `rcb_tests/public_test_cases/feature5_unresolved_reference_diagnostics.json`

```json
{
    "description": "Reject a database project whose schema references an object that is not supplied by the project or its references, and report a normalized unresolved-reference diagnostic.",
    "cases": [
        {
            "input": {
                "sql_files": {
                    "Table1.sql": "CREATE TABLE [dbo].[Table1]\n(\n\tc1 int NOT NULL PRIMARY KEY,\n\tc2 int NULL\n)\n",
                    "View2.sql": "-- This view references Table2 which does not exist\nCREATE VIEW [dbo].[View2]\n  AS SELECT * FROM [Table2]\n"
                }
            },
            "expected_output": "exit_code=1\npackage_exists=[ensure the default state is unset when no deployment steps are provided]\ntables=\nviews=\npre_deploy_script=[ensure the default state is unset when no deployment steps are provided]\npost_deploy_script=[ensure the default state is unset when no deployment steps are provided]\ndiagnostics=error_code=[specify the upper threshold for diagnostic generation during build failure];object=[dbo].[View2];referenced=[dbo].[Table2]\n"
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
- follow the path exclusion rules defined in the reference project module
- align the output field order with the header definitions in the render module
