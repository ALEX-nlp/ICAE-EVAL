## Product Requirement Document

# Semantic Version Constraint Engine — Parsing, Comparison, and Satisfiability for Version Strings

## Project Goal

Build a reusable library that understands software version strings and the constraint expressions used to describe acceptable ranges of versions, so developers can normalize, compare, sort, and match versions against constraints without each project re-implementing the subtle and error-prone rules of version semantics.

---

## Background & Problem

Version strings come in many shapes: plain three-part numbers, four-segment numbers, leading-`v` forms, pre-release suffixes (alpha/beta/RC/patch and their shorthands), build metadata after `+`, date-based versions, branch names, and development markers. Constraint expressions are equally varied: exact pins, comparators (`>`, `>=`, `<`, `<=`, `=`, `!=`), wildcard ranges (`2.*`, `2.x`), tilde and caret ranges (`~1.2`, `^1.2.3`), inclusive hyphen ranges (`1.0 - 2.0`), and boolean combinations of all of these joined with commas/spaces (AND) or `|`/`||` (OR).

Without a shared engine, developers hand-roll fragile string parsing and comparison logic, leading to inconsistent results, subtle ordering bugs, and incompatible interpretations of the same expression. This library provides one authoritative contract for: normalizing a version into a canonical comparable form, determining a version's stability, comparing two versions, sorting lists of versions, parsing a constraint expression into a normalized representation, filtering versions by a constraint, and deciding whether two constraints are mutually satisfiable.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   This domain (version parsing vs. constraint modeling vs. comparison/matching) is naturally multi-responsibility; prefer a small set of cohesive units over one monolithic file, but do not over-engineer.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types. In particular, single constraints and combined (AND/OR) constraint sets should be interchangeable wherever a constraint is expected.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: Check Whether a Version Satisfies a Constraint Expression

**As a developer**, I want to test whether a concrete version falls within the set described by a constraint expression, so I can decide if a given release is acceptable.

**Expected Behavior / Usage:**

The input supplies a `version` string and a `constraints` string. The constraint expression may use exact pins, comparators, wildcard/tilde/caret/hyphen ranges, and OR-combined alternatives. The output is `true` when the version lies inside the set the expression describes, otherwise `false`, followed by a newline. Pre-release versions are only accepted by a range when the range's lower bound itself admits pre-releases at that point.

**Test Cases:** `rcb_tests/public_test_cases/feature1_satisfies.json`

```json
{
    "description": "Decide whether a single concrete version satisfies a constraint expression. The version and the constraint expression are both supplied as strings; the expression may use exact, comparator, wildcard, tilde, caret, hyphen-range, and OR-combined forms. The result reports whether the version falls inside the set described by the expression.",
    "cases": [
        {"input": {"action": "satisfies", "version": "1.2.3", "constraints": "1.0.0 - 2.0.0"}, "expected_output": "true\n"},
        {"input": {"action": "satisfies", "version": "2.2.3", "constraints": "1.0.0 - 2.0.0"}, "expected_output": "false\n"}
    ]
}
```

---

### Feature 2: Filter a List of Versions by a Constraint

**As a developer**, I want to keep only the versions from a list that satisfy a constraint, so I can find the candidate releases for an installation.

**Expected Behavior / Usage:**

The input supplies an array of candidate `versions` and a `constraints` string. The output lists, one per line (each terminated by a newline), exactly those versions that satisfy the constraint, preserving their original input order and their original string form. If no version matches, the output is empty.

**Test Cases:** `rcb_tests/public_test_cases/feature2_satisfied_by.json`

```json
{
    "description": "Filter a list of candidate versions, keeping only those that satisfy a constraint expression. The kept versions are returned in their original order with their original string form preserved; non-matching versions are removed.",
    "cases": [
        {"input": {"action": "satisfiedBy", "versions": ["1.0", "1.2", "1.9999.9999", "2.0", "2.1", "0.9999.9999"], "constraints": "~1.0"}, "expected_output": "1.0\n1.2\n1.9999.9999\n"}
    ]
}
```

---

### Feature 3: Sort a List of Versions

**As a developer**, I want to order a list of version strings by precedence, so I can find the newest or oldest release.

**Expected Behavior / Usage:**

*3.1 Ascending Sort — order from lowest to highest precedence*

The input supplies an array of `versions`. The output lists them sorted from lowest to highest precedence, one per line. A pre-release version (e.g. `2.4.0-alpha`) orders immediately before its corresponding stable release (`2.4.0`). Versions that compare equal keep their original relative order. The original string form of each version is preserved.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_sort_ascending.json`

```json
{
    "description": "Sort a list of version strings from lowest to highest precedence. Pre-release versions order before their corresponding stable release, and equal versions keep their original relative order. The original version strings are preserved in the output.",
    "cases": [
        {"input": {"action": "sort", "versions": ["1.0", "0.1", "0.1", "3.2.1", "2.4.0-alpha", "2.4.0"]}, "expected_output": "0.1\n0.1\n1.0\n2.4.0-alpha\n2.4.0\n3.2.1\n"}
    ]
}
```

*3.2 Descending Sort — order from highest to lowest precedence*

The input supplies an array of `versions`. The output lists them sorted from highest to lowest precedence, one per line. A stable release orders before its pre-releases, and versions that compare equal keep their original relative order. The original string form is preserved.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_sort_descending.json`

```json
{
    "description": "Sort a list of version strings from highest to lowest precedence. A stable release orders before its pre-releases, and equal versions keep their original relative order. The original version strings are preserved in the output.",
    "cases": [
        {"input": {"action": "rsort", "versions": ["1.0", "0.1", "0.1", "3.2.1", "2.4.0-alpha", "2.4.0"]}, "expected_output": "3.2.1\n2.4.0\n2.4.0-alpha\n1.0\n0.1\n0.1\n"}
    ]
}
```

---

### Feature 4: Compare Two Versions with an Operator

**As a developer**, I want to evaluate a relational comparison between two versions, so I can branch on their ordering.

**Expected Behavior / Usage:**

The input supplies `version1`, an `operator`, and `version2`. The operator is one of `>`, `>=`, `<`, `<=`, `==` (or `=`), and `!=` (or `<>`). The output is `true` when the relation `version1 <operator> version2` holds, otherwise `false`, followed by a newline. Versions are compared by their normalized precedence, so equivalent forms (e.g. `1.25.0` and `1.25.0.0`) compare equal.

**Test Cases:** `rcb_tests/public_test_cases/feature4_compare.json`

```json
{
    "description": "Compare two version strings using a relational operator and report whether the relation holds. Supported operators are greater-than, greater-or-equal, less-than, less-or-equal, equal (single or double equals), and not-equal (two spellings).",
    "cases": [
        {"input": {"action": "compare", "version1": "1.25.0", "operator": ">", "version2": "1.24.0"}, "expected_output": "true\n"},
        {"input": {"action": "compare", "version1": "1.25.0", "operator": ">", "version2": "1.25.0"}, "expected_output": "false\n"}
    ]
}
```

---

### Feature 5: Normalize a Version String

**As a developer**, I want any reasonable version string reduced to a single canonical comparable form (and clearly invalid input rejected), so all downstream comparisons are consistent.

**Expected Behavior / Usage:**

*5.1 Normalize a Valid Version — canonical four-segment form*

The input supplies a `version` string. The output is its canonical normalized form followed by a newline. Normalization: strips a leading `v`; pads missing numeric segments to four segments with `.0`; expands and canonicalizes stability suffixes (`alpha`/`a`, `beta`/`b`, `RC`/`rc`, `patch`/`p`/`pl`) optionally followed by a number and an optional `-dev`; drops build metadata after `+`; maps master-like branch names (`master`/`trunk`/`default`, with or without a `dev-` prefix) to a high synthetic version; recognizes date-based versions; understands a `dev-` prefix; and for an alias of the form `X as Y`, keeps the source side `X`. A `-stable` suffix normalizes away as plain stable.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_normalize.json`

```json
{
    "description": "Normalize a version string into a canonical four-segment numeric form suitable for comparison. A leading \"v\" is stripped, missing numeric segments are padded with zeros, stability suffixes (alpha/beta/RC/patch, with optional shorthand) are expanded and canonicalized, build metadata after \"+\" is dropped, master-like branch names map to a high synthetic version, date-based versions are recognized, and aliasing (\"X as Y\") keeps the source side.",
    "cases": [
        {"input": {"action": "normalize", "version": "1.0.0"}, "expected_output": "1.0.0.0\n"},
        {"input": {"action": "normalize", "version": "1.2.3.4"}, "expected_output": "1.2.3.4\n"}
    ]
}
```

*5.2 Reject an Invalid Version — neutral error category*

The input supplies a `version` string that cannot be normalized: empty input, non-numeric junk, an unknown stability word, more than four numeric segments, a non-`dev` arbitrary name, or build metadata containing whitespace. The output is the neutral error line `error=invalid_version` followed by a newline. No host-language exception identity is exposed.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_normalize_invalid.json`

```json
{
    "description": "Reject version strings that cannot be normalized. Empty input, non-numeric junk, unknown stability words, too many numeric segments, non-dev arbitrary names, and build metadata containing whitespace are all invalid and produce a neutral error category instead of a normalized value.",
    "cases": [
        {"input": {"action": "normalize", "version": ""}, "expected_output": "error=invalid_version\n"},
        {"input": {"action": "normalize", "version": "a"}, "expected_output": "error=invalid_version\n"}
    ]
}
```

---

### Feature 6: Normalize a Branch Name

**As a developer**, I want a branch name turned into a comparable version form, so branches can participate in ordering alongside released versions.

**Expected Behavior / Usage:**

The input supplies a branch `name`. The output is its normalized form followed by a newline. A numeric branch name (optionally with a leading `v` and optional wildcard segments written as `x`, `X`, or `*`) expands to four segments, where each wildcard or missing segment becomes the high synthetic number `9999999`, and the whole is suffixed with `-dev`. Master-like names (`master`/`trunk`/`default`) map to the high synthetic version `9999999-dev`. Any other arbitrary name is returned prefixed with `dev-` to mark it as a development branch.

**Test Cases:** `rcb_tests/public_test_cases/feature6_normalize_branch.json`

```json
{
    "description": "Normalize a branch name into a comparable version form. Numeric branch names (with optional wildcard segments using x, X, or *) expand to a four-segment form where wildcard/missing segments become a high synthetic number followed by a development suffix; master-like names map to a high synthetic version; any other arbitrary name is prefixed to mark it as a development branch.",
    "cases": [
        {"input": {"action": "normalizeBranch", "name": "v1.x"}, "expected_output": "1.9999999.9999999.9999999-dev\n"},
        {"input": {"action": "normalizeBranch", "name": "v1.*"}, "expected_output": "1.9999999.9999999.9999999-dev\n"}
    ]
}
```

---

### Feature 7: Determine a Version's Stability

**As a developer**, I want to know the stability level implied by a version string, so I can apply minimum-stability policies.

**Expected Behavior / Usage:**

The input supplies a `version` string. The output is the stability name followed by a newline, one of: `stable`, `RC`, `beta`, `alpha`, `dev`. A `dev-` prefix or a `-dev` suffix (including when followed by a `#reference` fragment) yields `dev`. Recognized stability words and their shorthands map to their level (`b`→`beta`, `a`→`alpha`, `rc`→`RC`). Patch-level markers (`p`/`pl`/`patch`) are considered `stable`. Anything without a recognized pre-release marker is `stable`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_parse_stability.json`

```json
{
    "description": "Determine the stability level of a version string. The result is one of stable, RC, beta, alpha, or dev. A trailing or leading dev marker (including dev- prefixes and -dev suffixes and reference fragments after \"#\") yields dev; recognized stability words and their shorthands map to their level; patch-level markers are still considered stable; anything else is stable.",
    "cases": [
        {"input": {"action": "parseStability", "version": "1"}, "expected_output": "stable\n"},
        {"input": {"action": "parseStability", "version": "1.0"}, "expected_output": "stable\n"}
    ]
}
```

---

### Feature 8: Extract a Numeric Alias Prefix from a Branch

**As a developer**, I want the numeric prefix of a numeric development branch, so I can derive the version line it aliases.

**Expected Behavior / Usage:**

The input supplies a `branch` name. If the branch is in numeric development form — a dotted numeric version, optionally followed by `.x`, ending in `-dev` (e.g. `1.0.x-dev`, `1.2-dev`, `1-dev`) — the output is its dotted numeric prefix terminated by a dot (e.g. `1.0.`), followed by a newline. If the branch is not in numeric form (e.g. `dev-develop`, `dev-master`), the output is the sentinel `false` followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature8_numeric_alias_prefix.json`

```json
{
    "description": "Extract the numeric prefix from a development branch name when it is in numeric form, suitable for use as a version-alias prefix. A numeric branch ending in -dev (with an optional .x segment) yields its dotted numeric prefix terminated by a dot; a non-numeric development branch yields a sentinel indicating no numeric prefix exists.",
    "cases": [
        {"input": {"action": "parseNumericAliasPrefix", "branch": "0.x-dev"}, "expected_output": "0.\n"},
        {"input": {"action": "parseNumericAliasPrefix", "branch": "1.0.x-dev"}, "expected_output": "1.0.\n"}
    ]
}
```

---

### Feature 9: Parse a Constraint Expression into a Normalized Representation

**As a developer**, I want a constraint expression parsed into a normalized, inspectable representation, so I can see exactly which bounds it implies.

**Expected Behavior / Usage:**

The input supplies a `constraints` string. The output is the textual rendering of the parsed representation followed by a newline. The rendering conventions are: a single bound renders as `<operator> <normalized-version>`; the match-anything constraint renders as `[]`; a combined set renders as a bracketed list of its members, separated by a single space for conjunctive (AND) sets and by ` || ` for disjunctive (OR) sets. Normalized versions use the canonical four-segment form (see Feature 5). The following sub-features describe the supported expression shapes.

*9.1 Simple Constraints — exact pins and single comparators*

A bare version means exact equality (rendered with `==`). Comparator-prefixed versions keep their operator: `=`/`==` render as `==`, `<>`/`!=` render as `!=`, and `>`, `>=`, `<`, `<=` render as themselves. An open-ended lower bound (`<` or `>=`) attaches a `-dev` suffix to its normalized version unless an explicit stability is present (e.g. a `-stable` suffix suppresses it). A wildcard-only expression (`*`, `*.*`) renders as `[]`. Development branch names are accepted as exact or comparator operands.

**Test Cases:** `rcb_tests/public_test_cases/feature9_1_constraint_simple.json`

```json
{
    "description": "Parse a single, simple constraint expression into a normalized internal representation, rendered as a text form. A bare version means exact equality; comparator-prefixed versions (=, ==, <>, !=, >, >=, <, <=) keep that operator. Open-ended lower bounds (< and >=) attach a development suffix unless an explicit stability is present, and a wildcard-only expression matches everything. The rendered form shows the operator followed by the normalized four-segment version, or square brackets for the match-anything case.",
    "cases": [
        {"input": {"action": "parseConstraints", "constraints": "*"}, "expected_output": "[]\n"},
        {"input": {"action": "parseConstraints", "constraints": "*.*"}, "expected_output": "[]\n"}
    ]
}
```

*9.2 Wildcard Constraints — `x`/`X`/`*` ranges*

A wildcard at some position becomes an inclusive lower bound (with a `-dev` suffix) and an exclusive upper bound in which the segment just left of the wildcard is incremented (e.g. `2.*` → `>= 2.0.0.0-dev` and `< 3.0.0.0-dev`). A wildcard at the major position (e.g. `0.*`) yields only the exclusive upper bound and renders as that single bound.

**Test Cases:** `rcb_tests/public_test_cases/feature9_2_constraint_wildcard.json`

```json
{
    "description": "Parse a wildcard (\"x\", \"X\", or \"*\") constraint into a half-open version range. A wildcard at some position becomes a lower bound (inclusive, with a development suffix) and an upper bound (exclusive) where the segment just left of the wildcard is incremented. A wildcard at the most significant position (major) yields only the exclusive upper bound. The rendered form is the bracketed pair of bounds, or the single upper bound when there is no lower bound.",
    "cases": [
        {"input": {"action": "parseConstraints", "constraints": "2.*"}, "expected_output": "[>= 2.0.0.0-dev < 3.0.0.0-dev]\n"},
        {"input": {"action": "parseConstraints", "constraints": "2.*.*"}, "expected_output": "[>= 2.0.0.0-dev < 3.0.0.0-dev]\n"}
    ]
}
```

*9.3 Tilde Constraints — `~` ranges*

A tilde constraint allows updates of the last specified digit. The lower bound is the inclusive given version (with a `-dev` suffix unless an explicit stability is given); the upper bound is exclusive and increments the segment one position more significant than the last specified one (e.g. `~1.2` → `>= 1.2.0.0-dev` and `< 2.0.0.0-dev`; `~1.2.3` → `>= 1.2.3.0-dev` and `< 1.3.0.0-dev`). An explicit stability suffix is preserved in the lower bound.

**Test Cases:** `rcb_tests/public_test_cases/feature9_3_constraint_tilde.json`

```json
{
    "description": "Parse a tilde constraint into a half-open range allowing updates of the last specified digit. The lower bound is inclusive (with a development suffix unless an explicit stability is given); the upper bound is exclusive and increments the segment one position more significant than the last specified one. An explicit stability suffix is preserved in the lower bound.",
    "cases": [
        {"input": {"action": "parseConstraints", "constraints": "~1"}, "expected_output": "[>= 1.0.0.0-dev < 2.0.0.0-dev]\n"},
        {"input": {"action": "parseConstraints", "constraints": "~1.0"}, "expected_output": "[>= 1.0.0.0-dev < 2.0.0.0-dev]\n"}
    ]
}
```

*9.4 Caret Constraints — `^` ranges*

A caret constraint allows changes that do not modify the left-most non-zero segment. The lower bound is the inclusive given version (with a `-dev` suffix when no explicit stability is present); the upper bound is exclusive and increments the left-most non-zero segment. Leading-zero versions are handled accordingly: `^0` allows the whole `0.x` line, `^0.2` allows the rest of `0.2.x`/`0.3` boundary, and `^0.0.3` allows only patch updates within `0.0`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_4_constraint_caret.json`

```json
{
    "description": "Parse a caret constraint into a half-open range that allows changes which do not modify the left-most non-zero segment of the version. The lower bound is the inclusive given version (with a development suffix when no explicit stability is present); the upper bound is exclusive and increments the left-most non-zero segment, treating leading-zero versions accordingly (e.g. 0.x allows the rest of the 0.x line, 0.0.x only patch updates).",
    "cases": [
        {"input": {"action": "parseConstraints", "constraints": "^1"}, "expected_output": "[>= 1.0.0.0-dev < 2.0.0.0-dev]\n"},
        {"input": {"action": "parseConstraints", "constraints": "^0"}, "expected_output": "[>= 0.0.0.0-dev < 1.0.0.0-dev]\n"}
    ]
}
```

*9.5 Hyphen-Range Constraints — inclusive `A - B`*

An inclusive hyphen range yields a lower bound at the normalized `A` (inclusive, with a `-dev` suffix when no explicit stability is given). If `B` is a partial version, the upper bound is exclusive and bumps the last supplied segment of `B` (e.g. `1 - 2` → `< 3.0.0.0-dev`; `1.2 - 2.1.0` → `<= 2.1.0.0`). If `B` is a complete version, the upper bound is inclusive at `B`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_5_constraint_hyphen.json`

```json
{
    "description": "Parse an inclusive hyphen range \"A - B\" into a pair of bounds. The lower bound is the normalized A (inclusive, with a development suffix when no explicit stability is given). If B is a partial version, the upper bound is exclusive and bumps the last supplied segment of B; if B is a complete version, the upper bound is inclusive at B.",
    "cases": [
        {"input": {"action": "parseConstraints", "constraints": "1 - 2"}, "expected_output": "[>= 1.0.0.0-dev < 3.0.0.0-dev]\n"},
        {"input": {"action": "parseConstraints", "constraints": "1.2.3 - 2.3.4.5"}, "expected_output": "[>= 1.2.3.0-dev <= 2.3.4.5]\n"}
    ]
}
```

*9.6 Combined Constraints — conjunctive and disjunctive groups*

Constraints separated by commas or spaces form a conjunctive (all-must-hold) group; the pipe `|` or `||` forms a disjunctive (any-may-hold) group. Disjunction has lower precedence than conjunction, so `>2.0,<2.0.5 | >2.0.6` groups as a disjunction whose first member is the conjunction `[> 2.0.0.0 < 2.0.5.0-dev]`. A trailing per-constraint stability flag (`@stable`, `@dev`) adjusts that single constraint. The rendered form nests bracketed groups, with a single space between conjunctive members and ` || ` between disjunctive members.

**Test Cases:** `rcb_tests/public_test_cases/feature9_6_constraint_multi.json`

```json
{
    "description": "Parse expressions combining several constraints. Comma- or space-separated constraints form a conjunctive (all-must-hold) group; the pipe \"|\" or \"||\" forms a disjunctive (any-may-hold) group, and disjunction has lower precedence than conjunction. A trailing per-constraint stability flag (@stable, @dev) adjusts that constraint. The rendered form nests bracketed groups, using a space between conjunctive members and \" || \" between disjunctive members.",
    "cases": [
        {"input": {"action": "parseConstraints", "constraints": ">2.0,<=3.0"}, "expected_output": "[> 2.0.0.0 <= 3.0.0.0]\n"},
        {"input": {"action": "parseConstraints", "constraints": ">2.0 <=3.0"}, "expected_output": "[> 2.0.0.0 <= 3.0.0.0]\n"}
    ]
}
```

*9.7 Invalid Constraints — neutral error category*

Malformed expressions fail to parse and produce the neutral error line `error=invalid_constraint` followed by a newline. Examples include empty input, an unknown stability word, doubled or stray separators, an empty disjunction, the mistaken `~>` operator, and a stray `#reference` fragment on a non-development version. No host-language exception identity is exposed.

**Test Cases:** `rcb_tests/public_test_cases/feature9_7_constraint_invalid.json`

```json
{
    "description": "Reject malformed constraint expressions. Empty input, an unknown stability word, doubled or stray separators, an empty disjunction, the mistaken \"~>\" operator, and a stray reference fragment \"#...\" on a non-dev version all fail to parse and produce a neutral error category.",
    "cases": [
        {"input": {"action": "parseConstraints", "constraints": ""}, "expected_output": "error=invalid_constraint\n"},
        {"input": {"action": "parseConstraints", "constraints": "1.0.0-meh"}, "expected_output": "error=invalid_constraint\n"}
    ]
}
```

---

### Feature 10: Test Whether Two Constraints Are Mutually Satisfiable

**As a developer**, I want to ask whether a required constraint and a provided constraint can be satisfied by the same version, so I can resolve compatibility between a requirement and an offering.

**Expected Behavior / Usage:**

A constraint operand is described in JSON as one of: a single bound `{"operator": <op>, "version": <ver>}`; a conjunctive set `{"and": [<operand>, ...]}`; or a disjunctive set `{"or": [<operand>, ...]}`. The request supplies a `require` operand and a `provide` operand; the output is `true` if some version can satisfy both sides together, otherwise `false`, followed by a newline. The following sub-features cover single-vs-single, combined sets, branch comparison, and operator validation.

*10.1 Single vs. Single — compatibility of two bounds*

Each side is a single operator/version bound. Two bounds are compatible if their ranges overlap (or, for not-equal operators, a satisfying version trivially exists). Versions may be numeric or named development branches; two development branches are only compatible under equality when they are equal, and a development branch is treated as incompatible with a numeric bound.

**Test Cases:** `rcb_tests/public_test_cases/feature10_1_match_single.json`

```json
{
    "description": "Decide whether a required constraint and a provided constraint are mutually satisfiable, i.e. whether some version exists that meets both. Each side is a single operator/version pair (versions may be numeric or named development branches). Two development branches are only compatible when equal under equality operators; a development branch and a numeric version are treated as incompatible.",
    "cases": [
        {"input": {"action": "constraintMatch", "require": {"operator": "==", "version": "1"}, "provide": {"operator": "==", "version": "1"}}, "expected_output": "true\n"},
        {"input": {"action": "constraintMatch", "require": {"operator": ">=", "version": "1"}, "provide": {"operator": ">=", "version": "2"}}, "expected_output": "true\n"}
    ]
}
```

*10.2 Combined Sets — AND / OR operands*

Either or both sides may bundle several constraints. A conjunctive set is satisfiable against the other side only if every member is; a disjunctive set if any member is. This allows checking a range against a single version or against another range.

**Test Cases:** `rcb_tests/public_test_cases/feature10_2_match_multi.json`

```json
{
    "description": "Decide satisfiability when one or both sides bundle several constraints. A conjunctive set is satisfied only if every member is; a disjunctive set if any member is. Either side may itself be a set, allowing a range to be checked against a single version or against another range.",
    "cases": [
        {"input": {"action": "constraintMatch", "require": {"and": [{"operator": ">", "version": "1.0"}, {"operator": "<", "version": "1.2"}]}, "provide": {"operator": "==", "version": "1.1"}}, "expected_output": "true\n"},
        {"input": {"action": "constraintMatch", "require": {"and": [{"operator": ">", "version": "1.0"}, {"operator": "<", "version": "1.2"}]}, "provide": {"and": [{"operator": ">=", "version": "1.1"}, {"operator": "<", "version": "2.0"}]}}, "expected_output": "true\n"}
    ]
}
```

*10.3 Branch-Comparison Mode — comparing development branches against numeric bounds*

An optional `compareBranches` flag (default off) enables treating development branches as comparable to numeric versions. Without the flag, a development branch is never compatible with a numeric bound. With the flag enabled, a development branch is treated as ordering below any numeric version, so a strict upper bound (`<`) accepts it while a strict lower bound (`>`) does not.

**Test Cases:** `rcb_tests/public_test_cases/feature10_3_match_branches.json`

```json
{
    "description": "Decide satisfiability between a numeric comparison constraint and a named development branch, with an optional flag that enables treating development branches as comparable. Without the flag, a development branch is never compatible with a numeric bound. With the flag enabled, a development branch is treated as ordering below any numeric version, so a strict upper bound accepts it while a strict lower bound does not.",
    "cases": [
        {"input": {"action": "constraintMatch", "compareBranches": true, "require": {"operator": "<", "version": "0.12"}, "provide": {"operator": "==", "version": "dev-foo"}}, "expected_output": "true\n"},
        {"input": {"action": "constraintMatch", "compareBranches": true, "require": {"operator": ">", "version": "0.12"}, "provide": {"operator": "==", "version": "dev-foo"}}, "expected_output": "false\n"}
    ]
}
```

*10.4 Invalid Operator — neutral error category*

Constructing a bound with an operator that is not one of the supported relational operators fails. The output is the neutral error line `[invalid operator error format]` followed by a line `operator=<the offending operator>`, each terminated by a newline. No host-language exception identity is exposed.

**Test Cases:** `rcb_tests/public_test_cases/feature10_4_match_invalid_operator.json`

```json
{
    "description": "Reject construction of a comparison constraint whose operator is not one of the supported relational operators. An unsupported operator string produces a neutral error category together with the offending operator, rather than a match result.",
    "cases": [
        {"input": {"action": "constraintMatch", "require": {"operator": "invalid", "version": "1.2.3"}, "provide": {"operator": "==", "version": "1.2.3"}}, "expected_output": "[invalid operator error format]\noperator=invalid\n"},
        {"input": {"action": "constraintMatch", "require": {"operator": "!", "version": "1.2.3"}, "provide": {"operator": "==", "version": "1.2.3"}}, "expected_output": "[invalid operator error format]\noperator=!\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above (version normalization & stability, version comparison & sorting, constraint parsing, version-vs-constraint satisfaction, and constraint-vs-constraint satisfiability). Single constraints and combined AND/OR constraint sets must be interchangeable wherever a constraint is expected. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the result to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `satisfies`, `satisfiedBy`, `sort`, `rsort`, `compare`, `normalize`, `normalizeBranch`, `parseStability`, `parseNumericAliasPrefix`, `parseConstraints`, and `constraintMatch`. Boolean results are rendered as the lowercase words `true`/`false`. List results are rendered one item per line. Native errors must be normalized into neutral `error=<category>` lines (`error=invalid_version`, `error=invalid_constraint`, `[invalid operator error format]`), never exposing host-language exception identities.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- handles Git-era junk syntax
- rejects legacy bad formats
