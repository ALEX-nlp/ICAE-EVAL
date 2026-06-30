## Product Requirement Document

# Semantic Version Engine — Parsing, Ordering, and Range Satisfaction

## Project Goal

Build a reusable semantic-version engine that turns textual version identifiers and range expressions into well-defined comparisons and membership decisions, so developers can answer "is this version valid?", "which of two versions is newer?", and "does this version satisfy this constraint?" without each tool re-implementing fragile version math.

---

## Background & Problem

Software ecosystems describe releases with version identifiers such as `1.2.3`, `2.0.0-rc.1`, or `1.4.0+build.7`, and they describe acceptable releases with range expressions such as `>=1.2.0 <2.0.0`, `^1.2.3`, `~1.2`, or `1.0.0 - 2.0.0`. Doing this by hand — splitting on dots, comparing pre-release tags, expanding wildcards — is repetitive and easy to get subtly wrong, especially around pre-release precedence and wildcard boundaries.

This engine centralizes that logic behind a small contract: parse and normalize a version, order two versions, normalize a range, and test whether a version falls inside a range. Every spelling that denotes the same thing normalizes to one canonical form, so equivalent inputs are indistinguishable downstream.

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

### Feature 1: Parse And Canonicalize A Version

**As a developer**, I want to validate a version identifier and get back its canonical form, so I can normalize user-supplied versions before storing or comparing them.

**Expected Behavior / Usage:**

A version identifier consists of up to three dot-separated non-negative integer components — major, then optionally minor, then optionally patch — where omitted trailing components default to zero. After the patch it may carry a pre-release segment introduced by a hyphen (a dot-separated list of alphanumeric/hyphen identifiers) and/or a build-metadata segment introduced by a plus sign (also a dot-separated list). The adapter parses the identifier and prints its canonical rendering on a single `[a specific format prefix — verify with the 'output_rule' field in this constraint]<value>` line followed by a newline. The canonical rendering always shows all three numeric components, re-joins any pre-release identifiers with dots after a hyphen, and re-joins any build identifiers with dots after a plus, so a well-formed identifier round-trips to itself.

**Test Cases:** `rcb_tests/public_test_cases/feature1_parse_version.json`

```json
{
    "description": "Parse a textual version identifier and emit its canonical normalized form. The identifier has up to three dot-separated numeric components plus an optional hyphen-introduced pre-release segment and an optional plus-introduced build-metadata segment. The adapter parses the identifier and prints back the canonical rendering of the parsed value, so a well-formed identifier round-trips to itself.",
    "cases": [
        {
            "input": {"action": "parse", "version": "1.2.3-pre.4+build.5"},
            "expected_output": "[a specific format prefix — verify with the 'output_rule' field in this constraint]1.2.3-pre.4+build.5\n"
        },
        {
            "input": {"action": "parse", "version": "1.2.3"},
            "expected_output": "[a specific format prefix — verify with the 'output_rule' field in this constraint]1.2.3\n"
        }
    ]
}
```

---

### Feature 2: Compare Two Versions

**As a developer**, I want to know the precedence ordering of two versions, so I can sort releases or pick the newest.

**Expected Behavior / Usage:**

The adapter parses two version identifiers (`left` and `right`) and reports their relative ordering. Precedence is determined component by component: numeric major, minor, and patch are compared numerically and the first difference decides. When those are equal, a version that carries a pre-release segment has lower precedence than the otherwise-equal version that does not. Two pre-release segments are compared identifier by identifier from left to right: identifiers made only of digits are compared numerically, identifiers containing letters or hyphens are compared in ASCII order, a numeric identifier ranks below a non-numeric one, and if all shared identifiers are equal the segment with more identifiers ranks higher. Build metadata never affects precedence. The adapter prints three lines: `left=<canonical left>`, `right=<canonical right>`, and `order=<less|equal|greater>`, each followed by a newline, where the order word names the placement of the first operand relative to the second.

**Test Cases:** `rcb_tests/public_test_cases/feature2_compare_versions.json`

```json
{
    "description": "Compare two version identifiers for precedence and report their relative ordering. Numeric major, minor and patch components are compared first; a pre-release segment lowers precedence relative to the otherwise-equal release; pre-release identifiers are compared field by field with numeric fields ordered numerically and alphanumeric fields ordered lexically; build metadata does not affect precedence. The adapter prints both operands in canonical form and a word naming the ordering of the first relative to the second.",
    "cases": [
        {
            "input": {"action": "compare", "left": "1.0.0", "right": "2.0.0"},
            "expected_output": "left=1.0.0\nright=2.0.0\norder=less\n"
        },
        {
            "input": {"action": "compare", "left": "1.0.0", "right": "1.0.0"},
            "expected_output": "left=1.0.0\nright=1.0.0\norder=equal\n"
        },
        {
            "input": {"action": "compare", "left": "1.0.0-pre", "right": "1.0.0"},
            "expected_output": "left=1.0.0-pre\nright=1.0.0\norder=less\n"
        }
    ]
}
```

---

### Feature 3: Canonicalize A Version Range

**As a developer**, I want a range expression normalized to a canonical bounded form, so that equivalent spellings become directly comparable as strings.

**Expected Behavior / Usage:**

A range may specify fewer than three components, or use a wildcard placeholder (`*`, `x`, or `X`, case-insensitive) in a position, to mean "any value is acceptable there". The adapter expands such a range into the equivalent canonical form composed of explicit lower/upper comparator bounds and prints it on a single `[a specific format prefix — verify with the 'output_rule' field in this constraint]<value>` line followed by a newline. An entirely unrestricted range (empty text or a top-level wildcard) renders as the single universal-match token `*`. Wildcard expansion introduces a zero pre-release on the synthesized bounds so the bound's intent (include or exclude pre-releases at the boundary) is preserved. Because normalization is canonical, every spelling that denotes the same version set produces an identical rendering.

**Test Cases:** `rcb_tests/public_test_cases/feature3_canonicalize_range.json`

```json
{
    "description": "Parse a version-range expression and emit its canonical normalized form. A range may use omitted trailing components or explicit wildcard placeholders to mean 'any value' for a position. The adapter expands such a range into the equivalent bounded form, so that every spelling denoting the same set of versions produces an identical canonical rendering; an unrestricted range renders as the universal-match token.",
    "cases": [
        {
            "input": {"action": "canonicalize_range", "range": ""},
            "expected_output": "[a specific format prefix — verify with the 'output_rule' field in this constraint]*\n"
        },
        {
            "input": {"action": "canonicalize_range", "range": "1"},
            "expected_output": "[a specific format prefix — verify with the 'output_rule' field in this constraint]>=1.0.0-0 <2.0.0-0\n"
        }
    ]
}
```

---

### Feature 4: Test Whether A Version Satisfies A Range

**As a developer**, I want to test a concrete version against a range expression, so I can decide whether a candidate release is acceptable.

**Expected Behavior / Usage:**

Every form of this feature takes a `range` and a `version` and prints exactly three lines — `range=<canonical range>`, `version=<canonical version>`, and `satisfied=<true|false>`, each followed by a newline. The canonical range echoes the normalization from Feature 3, and the version echoes the canonical form from Feature 1, so the output makes the parsed inputs observable in addition to the decision. The sub-features below describe each supported range syntax.

*4.1 Primitive comparators and partial/wildcard operands*

A range can be a single comparator applied to a (possibly partial) version: `<`, `<=`, `>`, `>=`, `=`, or a bare version meaning exact match. An unrestricted range (empty or wildcard) matches everything; a `>`-style wildcard major matches nothing while a `<`-style wildcard major also matches nothing, and `<=`/`>=` wildcard majors match everything. A partial operand (omitted or wildcard minor/patch) is expanded to the corresponding bounded interval. A key boundary rule: a pre-release candidate satisfies a bound only when the bound itself targets a pre-release at the same major/minor/patch, reflecting that a pre-release ranks below its release; this is why, for example, a version like `4.9.0-beta` is accepted by `>4.8` (which expands to include pre-releases of `4.9.0`) but rejected by `<4.9`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_primitive_ranges.json`

```json
{
    "description": "Decide whether a version satisfies a range built from a single primitive comparator or a partial/wildcard version. Supported forms include an unrestricted range, an exact match, an explicit equality, and strictly-less, less-or-equal, strictly-greater, and greater-or-equal bounds, each possibly using a partial (wildcard) operand. Pre-release versions only satisfy a bound when that bound itself targets a pre-release at the same release, reflecting that a pre-release ranks below its release. The adapter prints the canonical range, the canonical version, and whether the version is contained.",
    "cases": [
        {
            "input": {"action": "test_range", "range": "", "version": "2.0.0"},
            "expected_output": "range=*\nversion=2.0.0\nsatisfied=true\n"
        },
        {
            "input": {"action": "test_range", "range": ">=1.0.0", "version": "1.0.0"},
            "expected_output": "range=>=1.0.0\nversion=1.0.0\nsatisfied=true\n"
        },
        {
            "input": {"action": "test_range", "range": ">4.8", "version": "4.9.0-beta"},
            "expected_output": "range=>=4.9.0-0\nversion=4.9.0-beta\nsatisfied=true\n"
        }
    ]
}
```

*4.2 Conjunctions (all comparators must hold)*

Several comparators separated by spaces form a conjunction; the version is contained only when it independently satisfies every comparator.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_conjunction_ranges.json`

```json
{
    "description": "Decide whether a version satisfies a conjunction of comparators written side by side and separated by spaces. A version is contained only when it independently satisfies every comparator in the conjunction. The adapter prints the canonical range, the canonical version, and whether the version is contained.",
    "cases": [
        {
            "input": {"action": "test_range", "range": ">1.0.0 <2.0.0", "version": "1.0.1"},
            "expected_output": "range=>1.0.0 <2.0.0\nversion=1.0.1\nsatisfied=true\n"
        },
        {
            "input": {"action": "test_range", "range": ">1.0.0 <2.0.0", "version": "2.0.0"},
            "expected_output": "range=>1.0.0 <2.0.0\nversion=2.0.0\nsatisfied=false\n"
        }
    ]
}
```

*4.3 Disjunctions (any alternative may hold)*

Alternatives separated by a double-pipe token form a disjunction; each alternative is itself a conjunction, and the version is contained when it satisfies at least one alternative.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_disjunction_ranges.json`

```json
{
    "description": "Decide whether a version satisfies a disjunction of alternatives separated by a double-pipe token. Each alternative is itself a conjunction of comparators; the version is contained when it satisfies at least one alternative. The adapter prints the canonical range, the canonical version, and whether the version is contained.",
    "cases": [
        {
            "input": {"action": "test_range", "range": ">1.0.0 || <1.0.0", "version": "1.0.1"},
            "expected_output": "range=>1.0.0 || <1.0.0\nversion=1.0.1\nsatisfied=true\n"
        },
        {
            "input": {"action": "test_range", "range": ">=1.0.0 <2.0.0 || >=3.0.0 <4.0.0", "version": "1.0.0"},
            "expected_output": "range=>=1.0.0 <2.0.0 || >=3.0.0 <4.0.0\nversion=1.0.0\nsatisfied=true\n"
        }
    ]
}
```

*4.4 Hyphen ranges (inclusive interval)*

A lower bound, a spaced hyphen, and an upper bound form an inclusive interval `>=lower <=upper`; both endpoints are included.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_hyphen_ranges.json`

```json
{
    "description": "Decide whether a version satisfies an inclusive interval written as a lower bound, a spaced hyphen, and an upper bound. Both endpoints are inclusive, so a version is contained when it is at least the lower bound and at most the upper bound. The adapter prints the canonical range, the canonical version, and whether the version is contained.",
    "cases": [
        {
            "input": {"action": "test_range", "range": "1.0.0 - 2.0.0", "version": "1.0.0"},
            "expected_output": "range=>=1.0.0 <=2.0.0\nversion=1.0.0\nsatisfied=true\n"
        },
        {
            "input": {"action": "test_range", "range": "1.0.0 - 2.0.0", "version": "2.0.1"},
            "expected_output": "range=>=1.0.0 <=2.0.0\nversion=2.0.1\nsatisfied=false\n"
        }
    ]
}
```

*4.5 Tilde ranges (least-significant-component flexibility)*

A tilde prefix permits increases only in the least significant component that was specified: with a minor given, only patch-level increases are allowed; with only a major given, minor-level increases within that major are allowed.

**Test Cases:** `rcb_tests/public_test_cases/feature4_5_tilde_ranges.json`

```json
{
    "description": "Decide whether a version satisfies a tilde range, which permits changes only in the least significant component that was specified. When a minor component is given, only patch-level increases are allowed; when only a major component is given, minor-level increases within that major are allowed. The adapter prints the canonical range, the canonical version, and whether the version is contained.",
    "cases": [
        {
            "input": {"action": "test_range", "range": "~0", "version": "0.0.0"},
            "expected_output": "range=>=0.0.0 <1.0.0\nversion=0.0.0\nsatisfied=true\n"
        },
        {
            "input": {"action": "test_range", "range": "~0", "version": "1.0.0"},
            "expected_output": "range=>=0.0.0 <1.0.0\nversion=1.0.0\nsatisfied=false\n"
        }
    ]
}
```

*4.6 Caret ranges (leftmost-non-zero-component flexibility)*

A caret prefix permits changes that do not modify the leftmost non-zero component: with a non-zero major, any higher minor or patch within that major is allowed; when the major is zero, the first non-zero component (minor, else patch) is held fixed instead.

**Test Cases:** `rcb_tests/public_test_cases/feature4_6_caret_ranges.json`

```json
{
    "description": "Decide whether a version satisfies a caret range, which permits changes that do not modify the leftmost non-zero component. For a release whose major is non-zero, any higher minor or patch within the same major is allowed; when the major is zero, the first non-zero component (minor, else patch) is the one held fixed. The adapter prints the canonical range, the canonical version, and whether the version is contained.",
    "cases": [
        {
            "input": {"action": "test_range", "range": "^0", "version": "0.0.0"},
            "expected_output": "range=>=0.0.0 <1.0.0\nversion=0.0.0\nsatisfied=true\n"
        },
        {
            "input": {"action": "test_range", "range": "^0", "version": "1.0.0"},
            "expected_output": "range=>=0.0.0 <1.0.0\nversion=1.0.0\nsatisfied=false\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing version parsing, canonical rendering, precedence comparison, range parsing/normalization, and range-membership testing. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the result to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `parse` (field `version`) prints `[a specific format prefix — verify with the 'output_rule' field in this constraint]<value>`; `compare` (fields `left`, `right`) prints `left=`, `right=`, `order=`; `canonicalize_range` (field `range`) prints `[a specific format prefix — verify with the 'output_rule' field in this constraint]<value>`; `test_range` (fields `range`, `version`) prints `range=`, `version=`, `satisfied=`. The order word is one of `less|equal|greater`; the satisfaction word is one of `true|false`. Failures are surfaced as a neutral `error=<category>` line rather than any host-language fault rendering.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
