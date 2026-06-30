## Product Requirement Document

# SDK Version Manager — Resolve, Catalog, Verify and Fetch Pinned Toolchain Versions

## Project Goal

Build a command-line version manager for a third-party SDK (the Flutter SDK) that lets developers reference SDK versions by a friendly name, verify what is available upstream, validate what is cached locally, and fetch new versions on demand, so a team can pin and switch between exact toolchain versions per project without manually juggling SDK checkouts.

---

## Background & Problem

A developer working with the Flutter SDK often needs several different SDK versions side by side — a stable release for one project, a development pre-release for another, a moving channel for experiments. Without a manager, they hand-clone the SDK at specific tags, remember which directory holds which version, and have no quick way to tell whether a cached copy is intact or corrupted.

This tool centralizes those concerns. It accepts a version reference in whatever everyday form the developer typed, resolves it to the one canonical identifier the upstream catalog actually uses, can answer whether a given reference is published upstream at all, can inspect a locally cached version directory and tell whether it is a healthy install, fetches versions from the upstream source repository (rejecting references that do not exist), and exposes its own version. Every externally observable outcome — including failures — is rendered as a small, language-neutral, line-oriented contract.

The domain has a few fixed conventions that the contract depends on:
- The upstream catalog publishes most numbered releases under a tag with a leading `v` (e.g. the bare number `1.8.0` is published as the tag `v1.8.0`), while development/pre-release tags (e.g. `1.17.0-dev.3.1`) are published without that prefix.
- There are four moving release channels named `master`, `stable`, `dev`, and `beta`.
- A correctly installed cached version directory always contains both an upstream project-metadata folder (named `.github`) and an executables folder (named `bin`).

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

### Feature 1: Resolve A Version Reference To Its Canonical Identifier

**As a developer**, I want to type a version in whatever form is natural to me and have the tool resolve it to the one identifier the upstream catalog actually uses, so I never have to remember the exact tag spelling.

**Expected Behavior / Usage:**

The input names a single version reference. Resolution is case-insensitive. The reference is resolved against the set of version tags published upstream: if the reference exactly matches a published tag it is returned unchanged; otherwise, if prefixing it with a leading `v` matches a published tag, that prefixed form is returned (this is how bare numbered releases map to their `v`-prefixed tags). Channel names and pre-release/development tags that are published without a `v` prefix therefore resolve to themselves. If neither the reference as given nor its `v`-prefixed form is a published tag, the reference is invalid: the tool emits a neutral `error=invalid_version` line followed by a `version=<the rejected reference>` line. A successful resolution emits a single `reference=<canonical identifier>` line. Every emitted line ends with a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_resolve_version.json`

```json
{
    "description": "Normalize a user-supplied SDK version reference into the canonical identifier used by the manager. The input is matched case-insensitively. A bare release number that is published only under a leading-'v' tag is resolved to that prefixed tag; a reference that is already a known tag (with or without the 'v' prefix, including pre-release/development tags that are published without a prefix) is returned unchanged. A reference that matches no known release tag in either its given or 'v'-prefixed form is rejected as an invalid version, and the rejected reference is echoed back in a neutral error.",
    "cases": [
        {"input": {"action": "resolve_version", "version": "1.8.0"}, "expected_output": "[a specific prefixed tag string (ask PM)]1.8.0\n"},
        {"input": {"action": "resolve_version", "version": "1.8.0.2"}, "expected_output": "error=invalid_version\nversion=1.8.0.2\n"}
    ]
}
```

---

### Feature 2: Report Membership In The Upstream Release Catalog

**As a developer**, I want to ask whether specific version references are published upstream, so I can confirm a version exists before trying to pin or install it.

**Expected Behavior / Usage:**

The input supplies an ordered list of references to look up. The tool retrieves the full catalog of versions published by the upstream source and, for each queried reference, emits one line of the form `<reference>=present` if the reference appears verbatim in the catalog, or `<reference>=absent` if it does not. Lines are emitted in the same order the references were queried, each terminated by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature2_release_catalog.json`

```json
{
    "description": "Query the catalog of all SDK versions published by the upstream source and report, for each reference asked about, whether it appears in that catalog. The input supplies a list of references to look up; for every reference the manager emits a line stating whether it is present in or absent from the published catalog, preserving the order of the queried references.",
    "cases": [
        {
            "input": {"action": "catalog_contains", "versions": ["v1.8.0", "v1.9.6", "v1.10.5", "v1.9.1+hotfix.4"]},
            "expected_output": "v1.8.0=present\nv1.9.6=present\nv1.10.5=present\nv1.9.1+hotfix.4=present\n"
        },
        {
            "input": {"action": "catalog_contains", "versions": ["v0.0.0-nonexistent"]},
            "expected_output": "v0.0.0-nonexistent=absent\n"
        }
    ]
}
```

---

### Feature 3: Verify Integrity Of A Cached Version Directory

**As a developer**, I want the tool to tell me whether a locally cached version is a complete, healthy install, so a half-downloaded or corrupted copy is detected and cleaned up rather than silently used.

**Expected Behavior / Usage:**

The input describes a cached version by name together with the layout of its directory: whether the directory exists, whether it contains the upstream project-metadata folder, and whether it contains the executables (`bin`) folder. A version is judged correctly installed only when its directory exists and contains BOTH marker folders; in that case the tool reports `installed_correctly=true`. If the directory does not exist at all, the tool simply reports `installed_correctly=false` with no other output. If the directory exists but is missing either marker folder, it is treated as a corrupted partial install: the tool first prints a notice line `<version> exists but was not setup correctly. Doing cleanup...`, removes the broken directory, and then reports `installed_correctly=false`. Every emitted line ends with a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature3_install_check.json`

```json
{
    "description": "Judge whether a locally cached SDK version directory is a healthy, fully set-up installation. A cached version is considered correctly installed only when its directory exists and contains both the upstream project-metadata folder and the executables (bin) folder. If the directory does not exist, it is simply reported as not correctly installed. If the directory exists but is missing either required marker folder, it is treated as a corrupted partial install: a notice naming the version is printed, the broken directory is cleaned up (removed), and it is reported as not correctly installed. The input describes the version's name and the layout of its cached directory (whether it exists, whether the metadata folder is present, whether the bin folder is present).",
    "cases": [
        {
            "input": {"action": "check_install", "version": "[a specific version string with leading 'v' (ask PM)]", "layout": {"exists": true, "has_metadata": true, "has_bin": true}},
            "expected_output": "installed_correctly=true\n"
        },
        {
            "input": {"action": "check_install", "version": "[a specific version string with leading 'v' (ask PM)]", "layout": {"exists": true, "has_metadata": false, "has_bin": false}},
            "expected_output": "[a specific version string with leading 'v' (ask PM)] exists but was not setup correctly. Doing cleanup...\ninstalled_correctly=false\n"
        }
    ]
}
```

---

### Feature 4: Reject Fetching An Unknown Version Reference

**As a developer**, I want a clear failure when I ask to fetch a version that does not exist upstream, so a typo or stale reference does not leave me with a broken or empty install.

**Expected Behavior / Usage:**

The input names a version reference to fetch from the upstream source repository. When the requested reference does not correspond to any real branch or tag upstream, the fetch operation fails and the tool reports a neutral `error=could_not_clone` line followed by a `version=<the requested reference>` line. The error contract must be language-neutral: it must not leak any host-runtime or process exception details. Each emitted line ends with a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature4_fetch_unknown.json`

```json
{
    "description": "Attempt to fetch (clone) an SDK version reference from the upstream source repository. When the requested reference does not correspond to any real branch or tag upstream, the fetch fails and the manager reports a neutral could-not-clone error that echoes back the requested reference rather than leaking any host-runtime fetch details.",
    "cases": [
        {
            "input": {"action": "fetch_version", "version": "INVALID_VERSION"},
            "expected_output": "error=could_not_clone\nversion=INVALID_VERSION\n"
        }
    ]
}
```

---

### Feature 5: Require A Version Reference For Installation

**As a developer**, I want the install action to refuse to run when I have given it nothing to install, so it fails fast instead of guessing.

**Expected Behavior / Usage:**

The input triggers the install action with no version reference supplied and with no project-level pinned version configured (there is nothing to fall back to). Because there is nothing to resolve, the install action must not attempt any fetch; it reports a neutral `error=missing_version` line, terminated by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature5_install_requires_version.json`

```json
{
    "description": "Invoke the install action without supplying any version reference and with no project-level pinned version configured. With nothing to resolve, the install action must refuse to proceed and surface a neutral missing-version error instead of attempting any download.",
    "cases": [
        {
            "input": {"action": "install_requires_version"},
            "expected_output": "error=missing_version\n"
        }
    ]
}
```

---

### Feature 6: Report The Tool's Own Version

**As a developer**, I want a version action that prints the tool's own version, so I can confirm which build of the manager I am running.

**Expected Behavior / Usage:**

The input triggers the version action. The tool prints its own semantic version string on a single line terminated by a newline, and produces no other output.

**Test Cases:** `rcb_tests/public_test_cases/feature6_tool_version.json`

```json
{
    "description": "Invoke the version action of the command-line tool, which prints the manager's own semantic version string on a single line.",
    "cases": [
        {
            "input": {"action": "tool_version"},
            "expected_output": "0.8.2\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request object from stdin, selects behavior by the request's `action`, invokes the appropriate core logic, and prints the resulting lines (or normalized error) to stdout, strictly matching the per-feature contracts above. The recognized actions are `resolve_version`, `catalog_contains`, `check_install`, `fetch_version`, `install_requires_version`, and `tool_version`. All error normalization (translating any native failure into a neutral `error=<category>` line plus accompanying field lines) is the adapter's responsibility.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- ensure all result lines follow the newlines module format
- align with the generic line ending standard
