## Product Requirement Document

# Dependency Audit Assistant - Command-Line Verification and Review Planning

## Project Goal

Build a command-line dependency audit assistant that allows developers to verify whether a project's third-party dependency graph has sufficient review coverage, inspect review gaps, export graph data, and compare package revisions without manually reconciling dependency metadata, review records, and source diffs.

---

## Background & Problem

Without this tool, developers are forced to manually inspect dependency manifests, review records, exemptions, publisher trust, and source changes to decide whether each dependency is acceptable for use. This leads to repetitive review bookkeeping, inconsistent decisions, missed transitive dependencies, and change histories that are difficult to audit.

With this tool, developers can run a single verification workflow that evaluates the project graph, reports audit coverage, recommends concrete review work, exports machine-readable graph or status data, and surfaces domain-specific command errors in a predictable, language-neutral format.

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

### Feature 1: Tool Version Reporting

**As a developer**, I want to query the assistant's own version banner, so I can confirm which build is in use before relying on its reports.

**Expected Behavior / Usage:**

The input requests the version banner with no project-specific parameters. The program prints a single line of the form `<name> <version>` to standard output, where `<version>` is exactly three dot-separated numeric components (each in the byte range 0–255), exits successfully, and writes nothing to the diagnostic stream. The output MUST report the successful exit code, the number of diagnostic bytes (zero), whether a name token is present, the count of version components, and whether every version component is numeric. The contract is deliberately name- and value-agnostic so any conforming build satisfies it.

**Test Cases:** `rcb_tests/public_test_cases/feature1_version_reporting.json`

```json
{
    "description": "Reports the tool's own version banner without diagnostic output: a name token followed by a three-part numeric version, a clean exit, and an empty diagnostic stream.",
    "cases": [
        {
            "input": {
                "scenario": "version reporting"
            },
            "expected_output": "exit_code=0\nstderr_bytes=0\nhas_name=true\nversion_component_count=3\nversion_components_all_numeric=true\n"
        }
    ]
}
```

---

### Feature 2: Audit Coverage Status

**As a developer**, I want to check whether the dependency graph is sufficiently reviewed, so I can decide whether the project is acceptable to build or release.

**Expected Behavior / Usage:**

The tool evaluates the project's resolved dependency graph against its recorded reviews and exemptions and classifies each third-party package as fully reviewed, partially reviewed, or accepted via an exemption. The two leaf features below render the same evaluation in two output formats. Sample counts and package names below are derived from the bundled fixture project; a conforming implementation reproduces the same classification behavior for that input.

*2.1 Human Audit Status — Summarize successful audit coverage in concise human-readable form.*

The input requests audit status with text formatting. The output MUST include the process exit code, the selected format, the success conclusion word, the counts of fully reviewed, partially reviewed, and exempted dependencies, and the number of diagnostic lines emitted (zero on success).

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_human_audit_status.json`

```json
{
    "description": "Summarizes whether the dependency audit is satisfied in human-readable mode, including fully audited, partially audited, and exempted counts.",
    "cases": [
        {
            "input": {
                "scenario": "audit status",
                "format": "text"
            },
            "expected_output": "exit_code=0\nformat=text\nconclusion=succeeded\nfully_audited=7\npartially_audited=2\nexempted=97\nstderr_lines=0\n"
        }
    ]
}
```

*2.2 JSON Audit Status — Summarize successful audit coverage for downstream automation.*

The input requests audit status with JSON formatting. The output MUST include the exit code, the selected format, the success conclusion, the size of each classification list, and the first and last `<name> <version>` entries of each list so consumers can validate both aggregate totals and stable boundary ordering.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_json_audit_status.json`

```json
{
    "description": "Summarizes a successful dependency audit in machine-readable mode with conclusion, category counts, and boundary package entries.",
    "cases": [
        {
            "input": {
                "scenario": "audit status",
                "format": "json"
            },
            "expected_output": "exit_code=0\nformat=json\nconclusion=success\nvetted_fully_count=7\nvetted_partially_count=2\nvetted_with_exemptions_count=97\nvetted_fully_first=atty 0.2.14\nvetted_fully_last=tracing 0.1.33\nvetted_partially_first=cfg-if 1.0.0\nvetted_partially_last=unicode-bidi 0.3.7\nvetted_with_exemptions_first=bumpalo 3.9.1\nvetted_with_exemptions_last=winreg 0.10.1\n"
        }
    ]
}
```

---

### Feature 3: Review Suggestion Reporting

**As a developer**, I want to see prioritized dependency review suggestions, so I can pick low-effort reviews that reduce future backlog.

**Expected Behavior / Usage:**

The tool computes the set of unreviewed packages, ranks the recommended review actions by estimated effort (smallest first), and reports each action together with the package, the revision(s) involved, the publisher (or an explicit unknown-publisher marker), the usage context, and an estimated review size. When a prior reviewed revision exists, the recommended action is a revision-to-revision comparison; otherwise it is a from-scratch inspection. The two leaf features render the same ranking in two formats. Network-sourced registry suggestions are suppressed so the result is deterministic. Sample values below come from the bundled fixture project.

*3.1 Human Review Suggestions — Present ranked review actions in readable form.*

The input requests review suggestions with text formatting and registry suggestions suppressed. The output MUST include the exit code, the selected format, the total count of recommended actions, the leading ranked action entries (each with action kind, package, revision(s), publisher or unknown marker, usage context, and review-size estimate), and the count of trust-note lines.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_human_review_suggestions.json`

```json
{
    "description": "Lists low-effort review recommendations in ranked human-readable order after temporarily ignoring exemptions.",
    "cases": [
        {
            "input": {
                "scenario": "review suggestions",
                "format": "text"
            },
            "expected_output": "exit_code=0\nformat=text\nrecommended_action_count=97\naction_0=diff proc-macro2 1.0.37 1.0.37@git:4445659b0f753a928059244c875a58bb12f791e9\naction_1=inspect tinyvec_macros 0.1.0 Soveu tinyvec 81 lines\naction_2=inspect matches 0.1.9 SimonSapin url, idna, and form_urlencoded 210 lines\naction_3=inspect foreign-types-shared 0.1.1 UNKNOWN foreign-types 302 lines\naction_4=inspect try-lock 0.2.3 seanmonstar want 380 lines\nnote_count=5\n"
        }
    ]
}
```

*3.2 JSON Review Suggestions — Present review backlog data for automation.*

The input requests review suggestions with JSON formatting. The output MUST include the exit code, the selected format, the sorted top-level section names of the machine-readable payload, and boolean presence checks proving that package and criteria signals appear while publisher-only display tokens (used only in the human view) do not appear in the structured payload.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_json_review_suggestions.json`

```json
{
    "description": "Emits machine-readable review suggestions with grouped suggestion data and package references.",
    "cases": [
        {
            "input": {
                "scenario": "review suggestions",
                "format": "json"
            },
            "expected_output": "exit_code=0\nformat=json\ntop_level_keys=conclusion,failures,suggest\ncontains_proc_macro2=true\ncontains_tinyvec_macros=true\ncontains_safe_to_deploy=true\ncontains_UNKNOWN=false\ncontains_Soveu=false\n"
        }
    ]
}
```

---

### Feature 4: Dependency Graph Export

**As a developer**, I want to export the resolved dependency graph, so I can inspect package relationships and roles outside the interactive report.

**Expected Behavior / Usage:**

The input requests a full-depth graph export and names the packages whose summaries should be rendered. The tool resolves the complete graph and emits, per package, its version, the number of normal/build/development dependency edges, the number of reverse dependencies, and role flags (workspace member, root). The aggregate output MUST include the exit code, the depth, the total package count, the root package name(s), the workspace-member count, the third-party count, and the dev-only count. Sample values below come from the bundled fixture project.

**Test Cases:** `rcb_tests/public_test_cases/feature4_dependency_graph.json`

```json
{
    "description": "Exports the full dependency graph as package summaries including dependency edge counts and package role flags.",
    "cases": [
        {
            "input": {
                "scenario": "dependency graph",
                "depth": "full",
                "packages": [
                    "test-project",
                    "proc-macro2",
                    "syn"
                ]
            },
            "expected_output": "exit_code=0\ndepth=full\npackage_count=107\nroot_packages=test-project\nworkspace_member_count=1\nthird_party_count=105\ndev_only_count=0\npackage=test-project 0.1.0 normal=6 build=0 dev=0 reverse=0 workspace=true root=true\npackage=proc-macro2 1.0.37@git:4445659b0f753a928059244c875a58bb12f791e9 normal=1 build=0 dev=0 reverse=1 workspace=false root=false\npackage=syn 1.0.91 normal=3 build=0 dev=0 reverse=3 workspace=false root=false\n"
        }
    ]
}
```

---

### Feature 5: Certification Command Error Normalization

**As a developer**, I want invalid certification requests to produce predictable domain errors, so automation can distinguish a command failure from a host-language runtime failure.

**Expected Behavior / Usage:**

A certification request names a selector that must identify one of the project's eligible foreign packages. When the selector does not match any eligible package, the command fails with a nonzero exit code and reports a normalized, language-neutral error category (`not_a_foreign_package`), the rejected selector, the domain message, and remediation help. The two leaf features render the same error in two formats. The output MUST NOT contain host-language exception class names, stack traces, object representations, or runtime-generated message suffixes.

*5.1 JSON Certification Error — Machine-readable domain error.*

The input requests certification of an ineligible selector with JSON formatting. The output MUST include the nonzero exit code, the selected format, the rejected selector, the normalized error category, the domain message, and the remediation help string.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_json_certification_error.json`

```json
{
    "description": "Normalizes an invalid certification request into a machine-readable domain error preserving the rejected selector, the domain message, and remediation help.",
    "cases": [
        {
            "input": {
                "scenario": "certification error",
                "selector": "asdfsdfs",
                "format": "json"
            },
            "expected_output": "[a specific error code and help text — ask the PM for the exact string]\nformat=json\nselector=asdfsdfs\n[a specific error code and help text — ask the PM for the exact string]\n[a specific error code and help text — ask the PM for the exact string]\n[a specific error code and help text — ask the PM for the exact string]\n"
        }
    ]
}
```

*5.2 Human Certification Error — Human-readable domain error.*

The input requests certification of an ineligible selector with text formatting. The output MUST carry the same normalized fields (exit code, format, selector, error category, domain message, remediation help) extracted from the human-readable diagnostic stream.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_human_certification_error.json`

```json
{
    "description": "Normalizes an invalid certification request into a human-readable domain error preserving the rejected selector, the domain message, and remediation help.",
    "cases": [
        {
            "input": {
                "scenario": "certification error",
                "selector": "asdfsdfs",
                "format": "text"
            },
            "expected_output": "[a specific error code and help text — ask the PM for the exact string]\nformat=text\nselector=asdfsdfs\n[a specific error code and help text — ask the PM for the exact string]\n[a specific error code and help text — ask the PM for the exact string]\n[a specific error code and help text — ask the PM for the exact string]\n"
        }
    ]
}
```

---

### Feature 6: Source Revision Comparison

**As a developer**, I want to compare two package revisions, so I can estimate review effort and see which files changed before reviewing a dependency update.

**Expected Behavior / Usage:**

The input names a package, a comparison mode, a starting revision, and an ending revision. A revision is either a plain semantic version (e.g. `1.0.90`) or a version pinned to a source-control revision using the `<semver>@git:<40-hex-digit-hash>` form. The tool produces a unified diff of the two extracted source trees, filtering out packaging-metadata files, and the output MUST summarize the exit code, the package and revision identifiers, the changed-file count, the diff-hunk count, the added-line count, the removed-line count, and the leading changed-filename pairs (`old->new`). Both plain-version and git-pinned comparisons are supported. Sample values below come from the bundled fixture cache.

**Test Cases:** `rcb_tests/public_test_cases/feature6_source_comparison.json`

```json
{
    "description": "Compares two package revisions and summarizes the observable patch size, hunk count, and changed filenames for both plain and git-pinned revisions.",
    "cases": [
        {
            "input": {
                "scenario": "source comparison",
                "mode": "local",
                "package": "syn",
                "from": "1.0.90",
                "to": "1.0.91"
            },
            "expected_output": "exit_code=0\npackage=syn\nfrom=1.0.90\nto=1.0.91\nchanged_file_count=6\nhunk_count=9\nadded_lines=67\nremoved_lines=47\nfile_0=Cargo.toml->Cargo.toml\nfile_1=Cargo.toml.orig->Cargo.toml.orig\nfile_2=expr.rs->expr.rs\nfile_3=lib.rs->lib.rs\nfile_4=lookahead.rs->lookahead.rs\n"
        },
        {
            "input": {
                "scenario": "source comparison",
                "mode": "local",
                "package": "proc-macro2",
                "from": "1.0.37",
                "to": "1.0.37@git:4445659b0f753a928059244c875a58bb12f791e9"
            },
            "expected_output": "exit_code=0\npackage=proc-macro2\nfrom=1.0.37\nto=1.0.37@git:4445659b0f753a928059244c875a58bb12f791e9\nchanged_file_count=3\nhunk_count=8\nadded_lines=63\nremoved_lines=7\nfile_0=ci.yml->ci.yml\nfile_1=fallback.rs->fallback.rs\nfile_2=test.rs->test.rs\n"
        }
    ]
}
```

---

### Feature 7: Version Revision String Validation

**As a developer**, I want malformed revision strings to be rejected with a clear, language-neutral category, so I can detect input mistakes without parsing host-language errors.

**Expected Behavior / Usage:**

A revision string is either a plain semantic version (`<major>.<minor>.<patch>`) or a semantic version pinned to a source revision via the `<semver>@git:<hash>` form, where `<hash>` must be exactly 40 hexadecimal digits. When a revision string is supplied (for example as a comparison endpoint) the tool validates it before doing any work and, on failure, reports a usage-error exit code together with a normalized error category and a domain reason. The categories are: `invalid_git_hash` when the `git:` hash is not exactly 40 hex digits; `unknown_revision` when a revision prefix other than `git:` is used; and `invalid_version` when the semantic-version portion itself cannot be parsed. The output MUST include the exit code, the raw input string, the normalized category, and the domain reason, and MUST NOT include host-language exception class names or object representations.

**Test Cases:** `rcb_tests/public_test_cases/feature7_version_validation.json`

```json
{
    "description": "Validates a revision string and rejects malformed inputs with a language-neutral error category and domain reason.",
    "cases": [
        {
            "input": {
                "scenario": "version validation",
                "revision": "1.0.1@git:00112233445566778899aabbccddeeff0011223g"
            },
            "expected_output": "exit_code=2\ninput=1.0.1@git:00112233445566778899aabbccddeeff0011223g\nerror=invalid_git_hash\nreason=unrecognized git hash, expected 40 hex digits\n"
        },
        {
            "input": {
                "scenario": "version validation",
                "revision": "1.0.1@git:00112233"
            },
            "expected_output": "exit_code=2\ninput=1.0.1@git:00112233\nerror=invalid_git_hash\nreason=unrecognized git hash, expected 40 hex digits\n"
        },
        {
            "input": {
                "scenario": "version validation",
                "revision": "1.0.1@pijul:00112233"
            },
            "expected_output": "exit_code=2\ninput=1.0.1@pijul:00112233\nerror=unknown_revision\nreason=unrecognized revision type, expected 'git:' prefix\n"
        },
        {
            "input": {
                "scenario": "version validation",
                "revision": "notaversion"
            },
            "expected_output": "exit_code=2\ninput=notaversion\nerror=invalid_version\nreason=unexpected character 'n' while parsing major version number\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain, and it is the sole layer responsible for normalizing native runtime errors into the language-neutral categories described above.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_version_reporting.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_version_reporting@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same error category used for invalid inputs in the versioning submodule
