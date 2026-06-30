## Product Requirement Document

# Static Package Repository Generator - Package Indexing, Metadata, Catalog, and Archive Contracts

## Project Goal

Build a static package repository generator that allows developers to turn package definitions and repository configuration into publishable package metadata, browsable catalog pages, and optional archive policies without hand-writing index files or manually pruning unsafe download links.

---

## Background & Problem

Without this tool, developers are forced to manually select package versions, follow dependency rules, write repository metadata JSON, maintain browser-facing package pages, and remove download sources that must not be published. This leads to repetitive indexing work, stale metadata, broken dependency visibility, unsafe source URLs, and inconsistent repository pages.

With this tool, a developer provides package repository configuration and package objects, and the system consistently selects the correct packages, emits machine-readable metadata, preserves or removes existing package data as needed, renders an HTML catalog, and applies archive inclusion rules.

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

### Feature 1: Package Selection

**As a developer**, I want to select packages from configured repositories using package requirements and filtering options, so I can publish exactly the package set intended for a static repository.

**Expected Behavior / Usage:**

The execution adapter accepts `action=select_packages`, a repository fixture or explicit repository list, and a `selection` object. The selection object can request all packages, name constrained packages, minimum stability, package-specific stability, dependency traversal, development dependency traversal, dependency-only output, type inclusion, type exclusion, and blacklist constraints. The output is newline-delimited stdout with `selected_count=<number>` followed by one `package=<name-version>` line per selected package sorted by package identifier. Dependency traversal and filtering are externally visible through the resulting package list.

**Test Cases:** `rcb_tests/public_test_cases/feature1_package_selection.json`

```json
{
    "description": "Select packages from configured repositories using requested package names, dependency traversal, stability, type, and blacklist options.",
    "cases": [
        {
            "input": {
                "action": "select_packages",
                "fixture": "rich",
                "selection": {
                    "required_packages": {
                        "vendor/project-alpha": ">=1",
                        "vendor/project-gamma": ">=1"
                    },
                    "minimum_stability": "stable"
                }
            },
            "expected_output": "selected_count=2\npackage=vendor/project-alpha-1.2.3.0\npackage=vendor/project-gamma-1.2.3.0\n"
        },
        {
            "input": {
                "action": "select_packages",
                "fixture": "rich",
                "selection": {
                    "required_packages": {
                        "vendor/project-delta": ">=1"
                    },
                    "minimum_stability": "stable",
                    "include_dependencies": true
                }
            },
            "expected_output": "selected_count=1\npackage=vendor/project-delta-1.2.3.0\n"
        },
        {
            "input": {
                "action": "select_packages",
                "fixture": "rich",
                "selection": {
                    "mode": "all",
                    "include_types": [
                        "library"
                    ]
                }
            },
            "expected_output": "selected_count=6\npackage=vendor/project-alpha-1.2.3.0\npackage=vendor/project-alpha-dev-main\npackage=vendor/project-beta-1.2.3.0\npackage=vendor/project-beta-dev-main\npackage=vendor/project-gamma-3.4.5.0\npackage=vendor/project-gamma-4.5.6.0\n"
        }
    ]
}
```

---

### Feature 2: Download Source Cleaning

**As a developer**, I want to strip package source or distribution URLs whose hosts are not safe to publish, so I can emit repository metadata without exposing local, private, or disallowed endpoints.

**Expected Behavior / Usage:**

The execution adapter accepts `action=clean_download_sources`, a package list with distribution and source URLs, and a `config` object containing host stripping rules. Rules may remove local paths, local hosts, private address ranges, specific CIDR ranges, IPv6 addresses, or domains. The output begins with `remaining_count=<number>` and then emits one line for each remaining package in input order using `package=<name> dist=<url-or-[a configurable list of network patterns to strip]> source=<url-or-[a configurable list of network patterns to strip]>`. If both usable download sources are stripped from a package, that package is removed from the output.

**Test Cases:** `rcb_tests/public_test_cases/feature2_download_source_cleaning.json`

```json
{
    "description": "Remove package download sources whose hosts match configured stripping rules while preserving sources that remain allowed.",
    "cases": [
        {
            "input": {
                "action": "clean_download_sources",
                "config": {
                    "strip-hosts": [
                        "/local"
                    ]
                }
            },
            "expected_output": "remaining_count=4\npackage=beta dist=http://192.168.0.2/output/dist/beta.zip source=[a configurable list of network patterns to strip]\npackage=gamma dist=http://192.168.0.1/output/dist/gamma.zip source=http://192.168.1.1/gamma.git\npackage=delta dist=http://example.org/output/dist/delta.zip source=http://source.example.org/delta.git\npackage=epsilon dist=http://[abcd::]/output/dist/epsilon.zip source=[a configurable list of network patterns to strip]\n"
        },
        {
            "input": {
                "action": "clean_download_sources",
                "config": {
                    "strip-hosts": [
                        "192.168.0.0/24"
                    ]
                }
            },
            "expected_output": "remaining_count=5\npackage=alpha dist=http://127.0.0.1/output/dist/alpha.zip source=[a configurable list of network patterns to strip]\npackage=beta dist=[a configurable list of network patterns to strip] source=http://localhost/beta.git\npackage=gamma dist=[a configurable list of network patterns to strip] source=http://192.168.1.1/gamma.git\npackage=delta dist=http://example.org/output/dist/delta.zip source=http://source.example.org/delta.git\npackage=epsilon dist=http://[abcd::]/output/dist/epsilon.zip source=http://[::1]/epsilon.git\n"
        }
    ]
}
```

---

### Feature 3: Repository Metadata Generation

**As a developer**, I want to generate package repository metadata files, so package clients can discover available packages, includes, provider indexes, and compact version metadata.

**Expected Behavior / Usage:**

The execution adapter accepts `action=generate_metadata`, configuration for metadata generation, and packages containing names and versions. The generator writes a root metadata document, include metadata, and per-package version metadata. Stdout summarizes the observable repository structure: `metadata_url`, `available`, optional `providers_url`, optional `providers`, optional `notify_batch`, the generated `include_file`, `include_packages`, `p2_versions`, and optional `p2_minified`. When a homepage path is supplied, metadata and provider URL templates are rooted at that path. When minification is enabled, compact per-package metadata advertises `composer/2.0` as its minification algorithm.

**Test Cases:** `rcb_tests/public_test_cases/feature3_metadata_generation.json`

```json
{
    "description": "Generate repository metadata files with include files, provider entries, notification endpoints, homepage-relative URLs, and compact version metadata.",
    "cases": [
        {
            "input": {
                "action": "generate_metadata",
                "config": {},
                "packages": [
                    {
                        "name": "vendor/name",
                        "version": "1.0"
                    }
                ]
            },
            "expected_output": "metadata_url=p2/%package%.json\navailable=vendor/name\ninclude_file=include/all$82aa8b329f93e0204b3dc0dd52891a59b81a3196.json\ninclude_packages=vendor/name\np2_versions=1.0\n"
        },
        {
            "input": {
                "action": "generate_metadata",
                "config": {
                    "providers": true,
                    "homepage": "http://localhost:1234/sub-dir"
                },
                "packages": [
                    {
                        "name": "vendor/name",
                        "version": "1.0"
                    }
                ]
            },
            "expected_output": "metadata_url=/sub-dir/p2/%package%.json\navailable=vendor/name\nproviders_url=/sub-dir/p/%package%$%hash%.json\nproviders=vendor/name\ninclude_file=include/all$eaa1fa7a7e4fad7c7937d4aafcf6c68fc72f0e13.json\ninclude_packages=vendor/name\np2_versions=1.0\n"
        }
    ]
}
```

---

### Feature 4: Existing Metadata Loading

**As a developer**, I want to load reusable packages from a previously generated metadata directory, so incremental repository builds can keep packages that are not being regenerated.

**Expected Behavior / Usage:**

The execution adapter accepts `action=load_existing_metadata`, a `metadata_state` describing whether the previous metadata root or include files are present, and a `package_filter` listing package names currently being regenerated. If the root metadata file is missing or its include files are missing, no packages are loaded. If metadata is complete, packages whose names are in `package_filter` are omitted; packages outside the filter are loaded and emitted. The stdout format is `loaded_count=<number>` followed by `package=<name> version=<pretty-version> dev=<true-or-false>` for each loaded package.

**Test Cases:** `rcb_tests/public_test_cases/feature4_existing_metadata_loading.json`

```json
{
    "description": "Load packages from an existing generated metadata directory and omit packages that are scheduled to be regenerated.",
    "cases": [
        {
            "input": {
                "action": "load_existing_metadata",
                "metadata_state": "missing_root",
                "package_filter": [
                    "vendor/name"
                ]
            },
            "expected_output": "loaded_count=0\n"
        },
        {
            "input": {
                "action": "load_existing_metadata",
                "metadata_state": "complete",
                "package_filter": [
                    "othervendor/othername"
                ]
            },
            "expected_output": "loaded_count=2\npackage=vendor/name version=1.0 dev=false\npackage=vendor/name version=dev-master dev=true\n"
        }
    ]
}
```

---

### Feature 5: Catalog Rendering

**As a developer**, I want to render a browsable package catalog page, so users can inspect repository title, package links, dependency links, and abandonment information in HTML.

**Expected Behavior / Usage:**

The execution adapter accepts `action=render_catalog`, a catalog display name, a package, optional dependency links, and optional abandonment information. The rendered catalog must expose its page title, a package anchor for the package name, dependency anchors when dependency links exist, and an abandonment notice when a package is marked abandoned. Stdout summarizes the framework-observable HTML signals using `title`, `package_anchor`, `dependency_anchor`, `abandoned_notice`, and `abandoned_detail`. A replacement package is reported as `abandoned_detail=[a specific replacement string format or default fallback]<name>`; an abandoned package without replacement is reported as `abandoned_detail=[a specific replacement string format or default fallback]`; otherwise it is `abandoned_detail=none`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_catalog_rendering.json`

```json
{
    "description": "Render a browseable package catalog page containing title, package links, dependency links, and abandoned package notices.",
    "cases": [
        {
            "input": {
                "action": "render_catalog",
                "catalog_name": "dummy root package",
                "package": {
                    "name": "vendor/name",
                    "version": "1.0"
                }
            },
            "expected_output": "title=dummy root package\npackage_anchor=present\ndependency_anchor=absent\nabandoned_notice=absent\nabandoned_detail=none\n"
        },
        {
            "input": {
                "action": "render_catalog",
                "catalog_name": "dummy root package",
                "package": {
                    "name": "vendor/name",
                    "version": "1.0"
                },
                "abandoned": "othervendor/othername"
            },
            "expected_output": "title=dummy root package\npackage_anchor=present\ndependency_anchor=absent\nabandoned_notice=present\nabandoned_detail=[a specific replacement string format or default fallback]othervendor/othername\n"
        }
    ]
}
```

---

### Feature 6: Archive Policy

**As a developer**, I want to resolve archive storage settings and skip packages that should not be archived, so archive generation can write to the correct location and avoid invalid or excluded packages.

**Expected Behavior / Usage:**

The execution adapter accepts `action=archive_policy`. For `query=storage_path`, it combines output directory and archive configuration and prints `path=<resolved-path>`, preferring an explicitly configured absolute archive directory when present. For package skip decisions, it accepts a package, optional provided virtual package names, and archive filtering configuration, then prints `skip=true` or `skip=false`. Packages are skipped when they are metadata-only packages, development versions with development skipping enabled, outside a whitelist, inside a blacklist, or providing a virtual package that is blacklisted.

**Test Cases:** `rcb_tests/public_test_cases/feature6_archive_policy.json`

```json
{
    "description": "Resolve archive storage paths and decide whether a package should be skipped during archive creation.",
    "cases": [
        {
            "input": {
                "action": "archive_policy",
                "query": "storage_path",
                "output_dir": ".",
                "config": {
                    "absolute-directory": "/home/satis/build/dist"
                }
            },
            "expected_output": "path=/home/satis/build/dist\n"
        },
        {
            "input": {
                "action": "archive_policy",
                "package": {
                    "name": "vendor/name",
                    "version": "dev-master",
                    "normalized": "dev-master"
                },
                "config": {
                    "skip-dev": 1
                }
            },
            "expected_output": "skip=true\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- ensure the output order matches the internal sorting convention used in the package_selector module
- apply the boolean flag for development versions using the same logic as seen in the version_utils aggregator
