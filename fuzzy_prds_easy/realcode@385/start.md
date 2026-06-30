## Product Requirement Document

# Feature-Based Node Customization Engine — Declarative Expression Matching & Rule Evaluation

## Project Goal

Build a reusable engine that evaluates declarative rules against a collection of discovered system features and produces derived outputs (labels and variables), so platform tooling can describe *what* should be derived from a machine's capabilities without hand-writing imperative matching code for every condition.

---

## Background & Problem

Systems are described by a collection of **features** organized by **domain** (for example a hardware domain, a kernel domain, a system domain). Within a domain a feature set takes one of three shapes: a **name set** (bare attribute names with no value), a **key-value set** (attribute names mapped to a single string value), or an **instance set** (a list of instances, each carrying its own map of attributes). Tooling needs to ask structured questions against these features ("does attribute X exist?", "is value Y greater than 10?", "which instances have attribute Z matching a pattern?") and, when the answers line up, emit derived labels and variables.

Without a shared engine, every consumer re-implements ad-hoc matching, integer parsing, regular-expression handling, and string templating, producing inconsistent and error-prone behavior. This engine provides one well-defined contract: a small algebra of **match operators**, composed into **expression sets** (logical AND of several named expressions) and **rules** (which combine an AND-matcher, an OR-of-matchers, static outputs, and templated outputs). The engine is decision logic only; it performs no I/O.

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

### Feature 1: Match-Expression Validation

**As a developer**, I want to validate an operator/value pair before using it, so misconfigured expressions are rejected up front instead of producing wrong results later.

**Expected Behavior / Usage:**

A match expression is an operator together with a list of comparison values. Validation enforces each operator's arity and value-type rules:

- Presence operators — `Any` (the empty operator string `""`), `Exists`, `DoesNotExist`, `IsTrue`, `IsFalse` — require an **empty** value list.
- Membership / regex operators — `In`, `NotIn`, `InRegexp` — require a **non-empty** value list; for `InRegexp` every value must be a compilable regular expression.
- Single-bound numeric operators — `Gt`, `Lt` — require **exactly one** value that parses as an integer.
- Range operator — `GtLt` — requires **exactly two** values that both parse as integers, with the first strictly less than the second.

A valid definition emits `valid=true`. An invalid one emits `valid=false` on the first line and a neutral reason category on the second line as `reason=<category>`. Categories are: `value_must_be_empty`, `value_must_be_nonempty`, `value_count_invalid`, `value_not_integer`, `value_out_of_order`, `[a specific regex compilation error code]`, `unknown_operator`. Each line is newline-terminated.

**Test Cases:** `rcb_tests/public_test_cases/feature1_expression_validation.json`

```json
{
    "description": "Validate a match-expression definition consisting of an operator and a list of comparison values. Construction succeeds only when the value list satisfies the operator's arity and type rules: presence operators (Any, Exists, DoesNotExist, IsTrue, IsFalse) require an empty value list; membership/regex operators (In, NotIn, InRegexp) require a non-empty list; the single-bound numeric operators (Gt, Lt) require exactly one integer value; the range operator (GtLt) requires exactly two integer values with the first strictly less than the second; InRegexp additionally requires every value to be a compilable regular expression. A valid definition reports success; an invalid one reports failure together with a neutral reason category.",
    "cases": [
        {"input": {"action": "validate", "op": "", "values": []}, "expected_output": "valid=true\n"},
        {"input": {"action": "validate", "op": "In", "values": ["1"]}, "expected_output": "valid=true\n"},
        {"input": {"action": "validate", "op": "InRegexp", "values": ["("]}, "expected_output": "valid=false\nreason=[a specific regex compilation error code]\n"},
        {"input": {"action": "validate", "op": "Gt", "values": ["1", "2"]}, "expected_output": "valid=false\nreason=value_count_invalid\n"},
        {"input": {"action": "validate", "op": "GtLt", "values": ["2", "1"]}, "expected_output": "valid=false\nreason=value_out_of_order\n"}
    ]
}
```

---

### Feature 2: Evaluating a Single Match Expression

**As a developer**, I want to evaluate one expression against different shapes of feature data, so I can express a precise condition over a single attribute.

**Expected Behavior / Usage:**

*2.1 Scalar evaluation — match one operator against a single input value*

The expression is evaluated against one scalar `input` plus a boolean `valid` flag that states whether the queried attribute is present at all. `Any` matches unconditionally. `Exists` returns the `valid` flag; `DoesNotExist` returns its negation. When `valid` is true the value is compared: `In`/`NotIn` test set membership; `InRegexp` returns true when any value (treated as a regular expression) matches; `Gt`/`Lt`/`GtLt` parse the value as an integer and compare against the bound(s); `IsTrue`/`IsFalse` test whether the value equals the literal string `true`/`false`. The result is reported as `match=true` or `match=false`. If a numeric operator receives a non-integer (either as the input or as a bound) the result is the neutral line `error=not_a_number`; an unknown operator yields `error=unsupported_operator`. Output is newline-terminated.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_scalar_match.json`

```json
{
    "description": "Evaluate a single match expression against one scalar input together with a validity flag indicating whether the queried attribute is present. Any matches unconditionally. Exists/DoesNotExist depend only on the validity flag. For a present value: In/NotIn test set membership; InRegexp tests whether any value (as a regular expression) matches; Gt/Lt/GtLt compare the input as an integer against the bound(s), reporting a neutral numeric error when either side is not an integer; IsTrue/IsFalse test whether the value equals the literal true/false. An unknown operator reports a neutral error.",
    "cases": [
        {"input": {"action": "match", "op": "In", "values": ["1", "2", "3"], "valid": true, "input": "2"}, "expected_output": "match=true\n"},
        {"input": {"action": "match", "op": "InRegexp", "values": ["val-[0-9]$"], "valid": true, "input": "val-1"}, "expected_output": "match=true\n"},
        {"input": {"action": "match", "op": "Gt", "values": ["2"], "valid": true, "input": 3}, "expected_output": "match=true\n"},
        {"input": {"action": "match", "op": "Gt", "values": ["2"], "valid": true, "input": "3a"}, "expected_output": "error=not_a_number\n"},
        {"input": {"action": "match", "op": "IsTrue", "values": [], "valid": false, "input": true}, "expected_output": "match=false\n"}
    ]
}
```

*2.2 Name-set evaluation — test presence of a named attribute*

The expression is evaluated against a **set of present attribute names** (`keys`), asking whether the attribute `name` satisfies it. Only presence-style operators are meaningful: `Any` always matches; `Exists` matches when `name` is in the set; `DoesNotExist` matches when it is absent. The result is `match=true`/`match=false`. Any value-based operator (`In`, `NotIn`, `InRegexp`, `Gt`, `Lt`, `GtLt`, `IsTrue`, `IsFalse`) is not applicable to a bare name set and yields the neutral line `error=operator_not_supported_for_keys`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_match_key_presence.json`

```json
{
    "description": "Evaluate a single match expression against a set of present attribute names, asking whether a named attribute satisfies the expression. Only presence-style operators are meaningful here: Any always matches; Exists matches when the named attribute is in the set; DoesNotExist matches when it is absent. Any value-based operator (In, NotIn, InRegexp, Gt, Lt, GtLt, IsTrue, IsFalse) is not applicable to a bare name set and reports a neutral error.",
    "cases": [
        {"input": {"action": "match_keys", "op": "Exists", "values": [], "name": "foo", "keys": ["bar", "foo"]}, "expected_output": "match=true\n"},
        {"input": {"action": "match_keys", "op": "DoesNotExist", "values": [], "name": "foo", "keys": ["bar", "foo"]}, "expected_output": "match=false\n"},
        {"input": {"action": "match_keys", "op": "In", "values": ["foo"], "name": "foo", "keys": []}, "expected_output": "error=operator_not_supported_for_keys\n"}
    ]
}
```

*2.3 Key-value evaluation — test a named attribute's value*

The expression is evaluated against a **map of attribute names to string values** (`input`), asking whether the attribute `name`'s value satisfies it. The named value (when present) is fed to the operator using the same per-operator semantics as 2.1: `In`/`NotIn` membership, `InRegexp` regular-expression match, `Gt`/`Lt`/`GtLt` numeric comparison (non-integers yield `error=not_a_number`), `IsTrue`/`IsFalse` literal tests, and `Exists`/`DoesNotExist` presence tests; `Any` always matches. The result is `match=true`/`match=false`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_match_key_value.json`

```json
{
    "description": "Evaluate a single match expression against a map of attribute names to string values, asking whether a named attribute's value satisfies the expression. The named attribute's value (if present) is fed to the operator: In/NotIn test membership, InRegexp tests regular-expression match, Gt/Lt/GtLt compare numerically (reporting a neutral numeric error for non-integers), IsTrue/IsFalse test the literal true/false, and Exists/DoesNotExist test presence. Any always matches.",
    "cases": [
        {"input": {"action": "match_values", "op": "In", "values": ["1", "2"], "name": "foo", "input": {"foo": "2"}}, "expected_output": "match=true\n"},
        {"input": {"action": "match_values", "op": "Gt", "values": ["2"], "name": "foo", "input": {"bar": "3", "foo": "3"}}, "expected_output": "match=true\n"},
        {"input": {"action": "match_values", "op": "IsFalse", "values": [], "name": "foo", "input": {"foo": "true"}}, "expected_output": "match=false\n"}
    ]
}
```

---

### Feature 3: Expression-Set Evaluation (Logical AND)

**As a developer**, I want to combine several named expressions that must all hold, so I can express a compound condition and learn exactly what matched.

**Expected Behavior / Usage:**

An expression set is a map of attribute name → expression `{op, value}`. The set matches only when **every** named expression matches (logical AND). An **empty** expression set matches any input.

*3.1 Against a name set — report matched names*

Each named expression is checked against a set of present attribute names. On a match the engine emits `match=true` followed by `matched=<names>`, where `<names>` is the comma-separated matched attribute names in **sorted** order (empty string when the set was empty). On no match it emits `match=false`. An operator not applicable to a name set yields `error=operator_not_supported_for_keys`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_set_match_keys.json`

```json
{
    "description": "Evaluate a set of named match expressions (logical AND of all of them) against a set of present attribute names. The set matches only when every named expression matches; on success the matched attribute names are reported in sorted order. An empty expression set matches any input and reports an empty matched list. If any expression uses an operator that is not applicable to a bare name set, a neutral error is reported.",
    "cases": [
        {"input": {"action": "mes_keys", "keys": ["bar", "baz", "buzz"], "expressions": {"foo": {"op": "DoesNotExist"}, "bar": {"op": "Exists"}}}, "expected_output": "match=true\nmatched=bar,foo\n"},
        {"input": {"action": "mes_keys", "keys": ["foo", "bar", "baz"], "expressions": {"foo": {"op": "DoesNotExist"}, "bar": {"op": "Exists"}}}, "expected_output": "match=false\n"}
    ]
}
```

*3.2 Against a key-value map — report matched name=value pairs*

Each named expression is checked against a map of attribute names to values. On a match the engine emits `match=true` followed by `matched=<pairs>`, where `<pairs>` is the comma-separated `name=value` of each matched attribute in **sorted order by name**. On no match it emits `match=false`. A numeric comparison against a non-integer value yields `error=not_a_number`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_set_match_values.json`

```json
{
    "description": "Evaluate a set of named match expressions (logical AND) against a map of attribute names to values. The set matches only when every named expression matches its corresponding value; on success the matched name=value pairs are reported in sorted order by name. An empty expression set matches any input and reports an empty matched list. A numeric comparison against a non-integer value reports a neutral error.",
    "cases": [
        {"input": {"action": "mes_values", "input": {"foo": "1", "bar": "val", "baz": "123", "buzz": "light"}, "expressions": {"foo": {"op": "Exists"}, "bar": {"op": "In", "value": ["val", "wal"]}, "baz": {"op": "Gt", "value": ["10"]}}}, "expected_output": "match=true\nmatched=bar=val,baz=123,foo=1\n"},
        {"input": {"action": "mes_values", "input": {"bar": "val"}, "expressions": {"foo": {"op": "Exists"}, "bar": {"op": "In", "value": ["val", "wal"]}, "baz": {"op": "Gt", "value": ["10"]}}}, "expected_output": "match=false\n"}
    ]
}
```

*3.3 Against an instance set — report matching instances*

Each instance is its own map of attributes; an instance matches when its attributes satisfy all expressions. The engine emits `matched=<N>` (the count of matching instances) followed by one line per matching instance, in **input order**, each line being that instance's attributes rendered as comma-separated `name=value` pairs **sorted by name** (an empty line for an instance with no attributes). An empty expression set matches every instance (so a single empty instance still matches). A numeric comparison against a non-integer attribute yields `error=not_a_number`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_set_match_instances.json`

```json
{
    "description": "Evaluate a set of named match expressions (logical AND) against a list of instances, each instance being its own map of attributes. Every instance whose attributes satisfy all expressions is collected; the result reports the count of matching instances followed by each matching instance's attributes (sorted by name) in input order. An empty expression set matches every instance, so a single empty instance still matches. A numeric comparison against a non-integer attribute reports a neutral error.",
    "cases": [
        {"input": {"action": "mes_instances", "expressions": {"foo": {"op": "Exists"}, "bar": {"op": "Lt", "value": ["10"]}}, "instances": [{"foo": "1"}, {"foo": "2", "bar": "1"}]}, "expected_output": "matched=1\nbar=1,foo=2\n"},
        {"input": {"action": "mes_instances", "instances": [{}]}, "expected_output": "matched=1\n\n"}
    ]
}
```

---

### Feature 4: Rule Evaluation

**As a developer**, I want to run a complete rule against all features and obtain its derived labels and variables, so I can drive node customization declaratively.

**Expected Behavior / Usage:**

A rule is evaluated against a `features` collection keyed by domain; each domain provides up to three feature sets: `keys` (name sets), `values` (key-value sets), and `instances` (instance sets). A rule carries optional static `labels` and `vars` (string maps) plus optional matchers:

- `matchFeatures` — a list of per-feature-set requirements, ALL of which must match (logical AND). Each entry references a feature set as `"<domain>.<featureset>"` and supplies an expression set evaluated against that feature set (matching the feature-set shape as in Feature 3). Feature-set name matching is case-insensitive.
- `matchAny` — a list of groups, ANY of which matching satisfies the matcher (logical OR); each group is itself a `matchFeatures`-style list.

When the rule matches, the engine produces its `labels` and `vars` and prints them as two sections: a `labels:` header line followed by the label entries, then a `vars:` header line followed by the var entries; within each section entries are `key=value`, one per line, **sorted by key**. When the rule does not match, both sections are present but empty. Referencing a domain that is not in `features` yields `error=unknown_domain`; referencing a feature set that the domain does not provide yields `error=unknown_feature`; a reference not of the form `<domain>.<featureset>` yields `error=invalid_feature_reference`.

*4.1 Static labels and variables*

This leaf covers matching logic with static outputs (no templates). See the contract above for matching and output rules.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_rule_evaluation.json`

```json
{
    "description": "Execute a customization rule against a collection of features grouped by domain. A rule carries static labels/vars plus optional matchers. matchFeatures is a logical AND of per-feature-set requirements; matchAny is a logical OR of such groups. A feature reference is '<domain>.<featureset>'; the feature set may be a name set, a key-value set, or an instance set. When the rule matches, its static labels and vars are produced (reported as sorted key=value lines under labels: and vars: sections); when it does not match, both sections are empty. Referencing an unknown domain, an unknown feature set, or a malformed reference reports a neutral error.",
    "cases": [
        {"input": {"action": "execute_rule", "rule": {"labels": {"label-1": "label-val-1"}, "vars": {"var-1": "var-val-1"}, "matchFeatures": [{"feature": "domain-1.kf-1", "matchExpressions": {"key-1": {"op": "Exists"}}}]}, "features": {"domain-1": {"keys": {"kf-1": ["key-1", "key-x"]}, "values": {"vf-1": {"key-1": "val-1"}}, "instances": {"if-1": [{"attr-1": "val-1"}]}}}}, "expected_output": "labels:\nlabel-1=label-val-1\nvars:\nvar-1=var-val-1\n"},
        {"input": {"action": "execute_rule", "rule": {"labels": {"label-1": "", "label-2": "true"}}, "features": {}}, "expected_output": "labels:\nlabel-1=\nlabel-2=true\nvars:\n"},
        {"input": {"action": "execute_rule", "rule": {"labels": {"label-1": "label-val-1"}, "vars": {"var-1": "var-val-1"}, "matchFeatures": [{"feature": "domain-1.kf-1", "matchExpressions": {"key-1": {"op": "Exists"}}}]}, "features": {}}, "expected_output": "error=unknown_domain\n"}
    ]
}
```

*4.2 Templated labels and variables*

In addition to static outputs, a rule may carry a `labelsTemplate` and a `varsTemplate` that are expanded **after** the rule matches. A template is rendered over the matched features and must produce newline-separated `<key>=<value>` entries; blank lines are ignored. The template output is merged with the static `labels`/`vars`, and the **static entries take precedence** on key collisions. When iterating a matched feature set, a name set exposes each element's `Name`; a key-value set exposes `Name` and `Value`; an instance set exposes its attributes by name (indexed by attribute name). A template that fails to parse, or whose expansion yields a line without a `=` value, yields `error=template_error`. Successful output uses the same sorted two-section rendering as 4.1.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_rule_templating.json`

```json
{
    "description": "Execute a rule that dynamically generates labels/vars from templates over the matched features. After a rule matches, its labelsTemplate and varsTemplate are expanded; the expansion must yield newline-separated '<key>=<value>' entries (blank lines ignored). Template output is merged with the rule's static labels/vars, with the static entries taking precedence on key collisions. Iterating a name set exposes each element's Name; a key-value set exposes Name and Value; an instance set exposes its attributes by name. A template that fails to parse, or whose expansion produces a line lacking a value, reports a neutral error.",
    "cases": [
        {"input": {"action": "execute_rule", "rule": {"labels": {"label-1": "label-val-1"}, "labelsTemplate": "\nlabel-1=will-be-overridden\nlabel-2=\n{{range .domain_1.kf_1}}kf-{{.Name}}=present\n{{end}}\n{{range .domain_1.vf_1}}vf-{{.Name}}=vf-{{.Value}}\n{{end}}\n{{range .domain_1.if_1}}if-{{index . \"attr-1\"}}_{{index . \"attr-2\"}}=present\n{{end}}", "vars": {"var-1": "var-val-1"}, "varsTemplate": "\nvar-1=value-will-be-overridden-by-vars\nvar-2=\n{{range .domain_1.kf_1}}kf-{{.Name}}=true\n{{end}}", "matchFeatures": [{"feature": "domain_1.kf_1", "matchExpressions": {"key-a": {"op": "Exists"}, "key-c": {"op": "Exists"}, "foo": {"op": "DoesNotExist"}}}, {"feature": "domain_1.vf_1", "matchExpressions": {"key-1": {"op": "In", "value": ["val-1", "val-2"]}, "bar": {"op": "DoesNotExist"}}}, {"feature": "domain_1.if_1", "matchExpressions": {"attr-1": {"op": "Lt", "value": ["100"]}}}]}, "features": {"domain_1": {"keys": {"kf_1": ["key-a", "key-b", "key-c"]}, "values": {"vf_1": {"key-1": "val-1", "keu-2": "val-2", "key-3": "val-3"}}, "instances": {"if_1": [{"attr-1": "1", "attr-2": "val-2"}, {"attr-1": "10", "attr-2": "val-20"}, {"attr-1": "100", "attr-2": "val-200"}]}}}}, "expected_output": "labels:\nif-10_val-20=present\nif-1_val-2=present\nkf-foo=present\nkf-key-a=present\nkf-key-c=present\nlabel-1=label-val-1\nlabel-2=\nvf-bar=vf-\nvf-key-1=vf-val-1\nvars:\nkf-foo=true\nkf-key-a=true\nkf-key-c=true\nvar-1=var-val-1\nvar-2=\n"},
        {"input": {"action": "execute_rule", "rule": {"matchFeatures": [{"feature": "domain_1.kf_1", "matchExpressions": {"key-a": {"op": "Exists"}}}], "labelsTemplate": "foo"}, "features": {"domain_1": {"keys": {"kf_1": ["key-a"]}}}}, "expected_output": "error=template_error\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the operator algebra, expression-set composition, and rule evaluation described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the resulting report (or neutral `error=<category>` line) to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `validate`, `match`, `match_keys`, `match_values`, `mes_keys`, `mes_values`, `mes_instances`, and `execute_rule`. All error reporting must be a neutral `error=<category>` (or, for validation, `valid=false` plus `reason=<category>`) line; native runtime error types/messages must never appear in stdout.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the exact static label format defined in C029
- handle numeric conversion errors similar to C013
