## Product Requirement Document

# Standard-Library Backport Catalog - Compatibility Metadata Service

## Project Goal

Build a backport catalog service that allows developers to look up which standard-library modules have a third-party backport distribution, on which runtime version lines each backport becomes available, and where to obtain it — without hard-coding that compatibility knowledge into every tool that needs it.

---

## Background & Problem

Some functionality that ships inside the standard library of newer runtime releases is also published as a standalone distribution so that it can be installed on older runtimes that predate it. Without a shared catalog, every analysis or packaging tool that wants to recommend "install this backport to keep running on an older runtime" must independently maintain its own table of which names are backportable, what the published distribution is called, and from which runtime version each one is natively available. This leads to duplicated, drifting, error-prone compatibility tables.

With this catalog service, that knowledge lives in one place behind a small, stable query interface: callers can enumerate the known backportable identifiers, test membership, normalize version-pinned identifiers down to a bare name, expand a bare name into all of its pinned variants, and render the whole catalog as an aligned human-readable listing.

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
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification — adding a new catalog entry must not require changing query logic.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

A catalog entry consists of three parts: an **identifier**, one or more **distribution URLs**, and an **availability range**. The availability range is a pair `(line2_min, line3_min)` describing the earliest version of the 2.x line and the earliest version of the 3.x line on which the functionality is natively present (i.e. on or after which the backport is no longer needed). When a value is rendered, a known version is shown as `major.minor` (e.g. `3.6`), and a line on which the functionality never became natively available is shown as an exclamation-prefixed line marker (`!2` for the 2.x line, `!3` for the 3.x line). An identifier may be **bare** (e.g. `typing_extensions`) or **version-pinned** with a trailing `==<version>` suffix (e.g. `typing_extensions==4.0`); a bare identifier and each of its pins are independent catalog entries that may carry different URLs and ranges.

### Feature 1: Enumerate Catalog Identifiers

**As a developer**, I want to list every identifier the catalog knows about, so I can discover which names are backportable and drive a help listing or validation set from a single source of truth.

**Expected Behavior / Usage:**

Given a request with `op = "list_identifiers"` and no further parameters, emit every distinct catalog identifier, one `identifier=<name>` line per entry, in ascending lexical order. Both bare identifiers and version-pinned variants appear as separate lines. The set is exactly the catalog's membership and contains no duplicates.

**Test Cases:** `rcb_tests/public_test_cases/feature1_list_identifiers.json`

```json
{
  "description": "Enumerate every distinct catalog identifier (module entry, including version-pinned variants) known to the backport catalog. Output lists one identifier per line in ascending lexical order.",
  "cases": [
    {
      "input": {
        "op": "list_identifiers"
      },
      "expected_output": "identifier=argparse\nidentifier=asyncio\nidentifier=configparser\nidentifier=contextvars\nidentifier=dataclasses\nidentifier=enum\nidentifier=faulthandler\nidentifier=importlib\nidentifier=ipaddress\nidentifier=mock\nidentifier=statistics\nidentifier=typing\nidentifier=typing_extensions\nidentifier=typing_extensions==4.0\nidentifier=typing_extensions==4.3\n"
    }
  ]
}
```

---

### Feature 2: Membership Check

**As a developer**, I want to ask whether a specific identifier belongs to the catalog, so I can decide whether a backport recommendation applies to a given imported name.

**Expected Behavior / Usage:**

Given `op = "is_backport"` and a `module` string, emit the echoed `identifier=<module>` line followed by `is_backport=<true|false>`. A name is a member only if it appears verbatim as a catalog identifier; version-pinned variants are members in their pinned form, while arbitrary standard-library or third-party names (and near-miss spellings) are not. The membership flag is a normalized lowercase boolean (`true` / `false`).

**Test Cases:** `rcb_tests/public_test_cases/feature2_membership_check.json`

```json
{
  "description": "Report whether a given identifier is a member of the catalog. Echoes the queried identifier and a boolean membership flag. Version-pinned variants are members; arbitrary standard-library or third-party names are not.",
  "cases": [
    {
      "input": {
        "op": "is_backport",
        "module": "typing"
      },
      "expected_output": "identifier=typing\nis_backport=true\n"
    },
    {
      "input": {
        "op": "is_backport",
        "module": "enum"
      },
      "expected_output": "identifier=enum\nis_backport=true\n"
    },
    {
      "input": {
        "op": "is_backport",
        "module": "os"
      },
      "expected_output": "identifier=os\nis_backport=false\n"
    },
    {
      "input": {
        "op": "is_backport",
        "module": "requests"
      },
      "expected_output": "identifier=requests\nis_backport=false\n"
    }
  ]
}
```

---

### Feature 3: Render Aligned Catalog Listing

**As a developer**, I want the full catalog rendered as an aligned, indented, human-readable block, so I can present it directly in a tool's help output.

**Expected Behavior / Usage:**

Given `op = "render"` and an integer `indent`, produce one line per catalog entry. Every line begins with `indent` leading spaces, then the identifier left-padded to a common width so the ` - ` separators align across all rows, then the distribution URL, then the availability range in parentheses rendered as `(line2, line3)`. Within the parentheses a known version is shown as `major.minor` and a line on which the functionality never became natively available is shown as `!2` / `!3`. Row order matches the catalog's own declaration order (not lexical order), so version-pinned variants are grouped next to their bare identifier. The common padding width is driven by the longest identifier present.

**Test Cases:** `rcb_tests/public_test_cases/feature3_render_listing.json`

```json
{
  "description": "Render the full catalog as an aligned human-readable listing indented by a caller-supplied number of leading spaces. Each line shows the identifier, the distribution URL, and the (py2, py3) availability range in parentheses; a missing major-line bound is shown as an exclamation-prefixed marker.",
  "cases": [
    {
      "input": {
        "op": "render",
        "indent": 3
      },
      "expected_output": "   argparse               - https://pypi.org/project/argparse/ (2.3, 3.1)\n   asyncio                - https://pypi.org/project/asyncio/ (!2, 3.3)\n   configparser           - https://pypi.org/project/configparser/ (2.6, 3.0)\n   contextvars            - https://pypi.org/project/contextvars/ (!2, 3.5)\n   dataclasses            - https://pypi.org/project/dataclasses/ (!2, 3.6)\n   enum                   - https://pypi.org/project/enum34/ (2.4, 3.3)\n   faulthandler           - https://pypi.org/project/faulthandler/ (2.6, 3.0)\n   importlib              - https://pypi.org/project/importlib/ (2.3, 3.0)\n   ipaddress              - https://pypi.org/project/ipaddress/ (2.6, 3.2)\n   mock                   - https://pypi.org/project/mock/ (!2, 3.6)\n   statistics             - https://pypi.org/project/statistics/ (2.6, 3.4)\n   typing                 - https://pypi.org/project/typing/ (2.7, 3.2)\n   typing_extensions==4.0 - https://pypi.org/project/typing-extensions/4.0.0/ (!2, 3.6)\n   typing_extensions==4.3 - https://pypi.org/project/typing-extensions/4.3.0/ (!2, 3.7)\n   typing_extensions      - https://pypi.org/project/typing-extensions/4.3.0/ (!2, 3.7)\n"
    }
  ]
}
```

---

### Feature 4: Strip Version Pin

**As a developer**, I want to reduce a possibly version-pinned identifier to its bare name, so I can match a pinned request against catalog membership and grouping logic.

**Expected Behavior / Usage:**

Given `op = "strip_version"` and a `module` string, echo `input=<module>` then `identifier=<bare>`. The bare name is the identifier portion that precedes a `==<version>` suffix; the version portion may be any text. The identifier portion may legitimately contain word characters, underscores, and dots, all of which are preserved. A string that carries no `==` pin is returned unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature4_strip_version.json`

```json
{
  "description": "Strip a trailing version-pin suffix (an identifier followed by == and any text) and return the bare identifier. Names containing word characters, underscores, and dots are preserved; a name without a version pin is returned unchanged.",
  "cases": [
    {
      "input": {
        "op": "strip_version",
        "module": "somemodule==1.2"
      },
      "expected_output": "input=somemodule==1.2\nidentifier=somemodule\n"
    },
    {
      "input": {
        "op": "strip_version",
        "module": "some.module==1.2"
      },
      "expected_output": "input=some.module==1.2\nidentifier=some.module\n"
    },
    {
      "input": {
        "op": "strip_version",
        "module": "somemodule"
      },
      "expected_output": "input=somemodule\nidentifier=somemodule\n"
    }
  ]
}
```

---

### Feature 5: Collapse to Unversioned Set

**As a developer**, I want to collapse a collection of identifiers into the de-duplicated set of bare names, so I can treat all pinned variants of one backport as a single logical entry.

**Expected Behavior / Usage:**

Given `op = "unversioned"` and a `modules` array, strip the version pin from each element (per Feature 4 semantics), de-duplicate, and emit `identifier=<name>` lines in ascending lexical order. Multiple pinned variants that share a bare name collapse to exactly one output line, and a bare name already present collapses together with its pins.

**Test Cases:** `rcb_tests/public_test_cases/feature5_unversioned_set.json`

```json
{
  "description": "Collapse a collection of identifiers into the set of bare identifiers by stripping every version pin and de-duplicating. Output lists the resulting identifiers one per line in ascending lexical order; version-pinned variants of the same base collapse to a single entry.",
  "cases": [
    {
      "input": {
        "op": "unversioned",
        "modules": [
          "typing_extensions==4.0",
          "typing_extensions==4.3",
          "typing_extensions",
          "enum"
        ]
      },
      "expected_output": "identifier=enum\nidentifier=typing_extensions\n"
    }
  ]
}
```

---

### Feature 6: Expand Identifier Into All Variants

**As a developer**, I want to expand a bare identifier into every catalog entry that shares it, so I can offer the user a choice of pinned versions together with each one's distribution URL and availability range.

**Expected Behavior / Usage:**

Given `op = "expand"` and a bare `module`, gather every catalog entry whose bare name matches and emit them ordered with the unversioned entry first, followed by the version-pinned variants from newest to oldest. The output begins with `entries=<count>`; then, for each entry in order, a positional header `[<n>]` (1-based), an `identifier=<name>` line, one `url=<link>` line per distribution URL, and a `versions=<line2, line3>` line. A bare name with no pinned variants yields a single entry.

**Test Cases:** `rcb_tests/public_test_cases/feature6_expand_versions.json`

```json
{
  "description": "Expand a bare identifier into all its catalog entries (the unversioned entry plus every version-pinned variant), ordered with the unversioned entry first and version-pinned variants from newest to oldest. Each entry lists its identifier, distribution URL(s), and (py2, py3) availability range.",
  "cases": [
    {
      "input": {
        "op": "expand",
        "module": "typing_extensions"
      },
      "expected_output": "entries=3\n[1]\nidentifier=typing_extensions\nurl=https://pypi.org/project/typing-extensions/4.3.0/\nversions=!2, 3.7\n[2]\nidentifier=typing_extensions==4.3\nurl=https://pypi.org/project/typing-extensions/4.3.0/\nversions=!2, 3.7\n[3]\nidentifier=typing_extensions==4.0\nurl=https://pypi.org/project/typing-extensions/4.0.0/\nversions=!2, 3.6\n"
    },
    {
      "input": {
        "op": "expand",
        "module": "enum"
      },
      "expected_output": "entries=1\n[1]\nidentifier=enum\nurl=https://pypi.org/project/enum34/\nversions=2.4, 3.3\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the catalog and the six query behaviors described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The catalog data (identifiers, distribution URLs, availability ranges) must be decoupled from query and formatting logic so new entries can be added without touching the query engine.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a single JSON command from stdin, invokes the appropriate core query, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. Any failure must be rendered as a neutral `error=<category>` line (e.g. `error=unknown_op`), never as a host-language runtime artifact. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_list_identifiers.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_list_identifiers@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- entries show the same ascending pattern as seen in the standard output examples
