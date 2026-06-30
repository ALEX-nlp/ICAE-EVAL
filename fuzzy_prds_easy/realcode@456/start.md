## Product Requirement Document

# Parameter Binding Disambiguation Utility - PRD

## Project Goal

Build a small validation utility that lets a framework safely bind external named values onto the parameters of a developer-declared method. It guarantees that a method's parameter list can be bound **unambiguously**, and it resolves the **effective binding name** for any single parameter. This lets developers wire data into their methods by type and/or by name without silently mis-ordering values when two parameters happen to share a type.

---

## Background & Problem

When a framework injects values into a method by inspecting its parameters, parameters are usually matched by their declared type. This works perfectly as long as every parameter has a distinct type. The moment two parameters share the same type, the framework can no longer tell which incoming value belongs to which parameter — the order becomes ambiguous, and the developer may not notice until values are silently swapped at runtime.

The accepted way out is to let the developer **opt in to name-based matching** on the parameters that need it: a per-parameter marker says "bind me by my name, not just by my type." But this only removes the ambiguity if it is applied *consistently*. If a developer marks one of two same-typed parameters and forgets the other, the list is still ambiguous and arguably worse, because the intent is now half-expressed.

Without this utility, developers would have to hand-audit every method for these half-annotated, same-typed parameter groups, and separately re-derive each parameter's binding name from scattered rules. With this utility, a single validation call rejects any inconsistently-marked parameter list with a precise, structured description of the conflict, and a single resolution call returns the exact name a value will be bound under.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a focused, two-function domain. A small, well-factored module (core validation/resolution logic separated from the I/O adapter) is appropriate. Do not inflate it into a sprawling framework, but keep the core logic free of any stdin/stdout or JSON concerns.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a **black-box contract** for an execution adapter, not the internal shape of the core logic. The core validation/resolution functions must operate on ordinary in-memory method/parameter descriptions and must not know about JSON, stdin, or the wire format. A thin adapter translates each JSON command into a core call and renders the result.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Keep parsing, validation, name-resolution, and output formatting in distinct units.
   - **Open/Closed Principle (OCP):** Adding a new binding rule must not require rewriting the ambiguity check.
   - **Liskov Substitution Principle (LSP):** Any parameter/marker abstraction must be uniformly substitutable.
   - **Interface Segregation Principle (ISP):** The validation surface and the resolution surface are independent and small.
   - **Dependency Inversion Principle (DIP):** The core depends on parameter/marker abstractions, not on the adapter's I/O.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The core should expose elegant, idiomatic calls (a validate call and a resolve call).
   - **Resilience:** Ambiguity must be reported through a dedicated, typed error carrying structured conflict data — never a generic failure and never a swallowed warning.

---

## Core Features

### Feature 1: Parameter List Ambiguity Validation

**As a developer**, I want a method's parameter list checked for unbindable ambiguity before it is used, so I can catch half-marked same-typed parameters at wiring time instead of debugging silently swapped values later.

**Expected Behavior / Usage:**

The input is an ordered list of parameters. Each parameter carries a positional `name`, a `type` label (two parameters with the same label are considered to have the same declared type), and a boolean `name_match` flag indicating whether that parameter opts in to name-based binding.

The list is grouped by type. A type group is only a problem when it contains **more than one** parameter AND those parameters are **inconsistently** marked — that is, *some but not all* of them have `name_match` set. A group is fine when all its members are marked, when none of its members are marked, or when the group has a single member. If every type label is distinct, the list is trivially accepted.

An accepted list outputs `[accept with zero conflicts]` followed by `[accept with zero conflicts]`. A rejected list outputs `result=rejected`, then `error=duplicate_parameter_type`, then `conflict_count=<number of offending type groups>`, and then one `conflict=` line per offending group. Each conflict line names the group's type label, the zero-based positions of every parameter in that group (in declaration order, comma-separated), and those parameters' names (comma-separated). Note that the positions include *all* members of the ambiguous group, even ones that were individually marked, because the whole group is what is ambiguous.

**Test Cases:** `rcb_tests/public_test_cases/feature1_validate_parameter_binding.json`

```json
{
    "description": "Validate that a method-style parameter list is unambiguous for value binding. A parameter list is ambiguous when two or more parameters share the same declared type but only SOME (not all, and not none) of those same-typed parameters are flagged to be bound by name. A list is accepted when every group of same-typed parameters is either fully name-flagged or fully unflagged, or when all parameter types are distinct. Each input is an ordered list of parameters; each parameter has a positional name, a type label (parameters sharing a label share a type), and a boolean name_match flag. Accepted lists report [accept with zero conflicts]. Rejected lists report the normalized error category and one conflict line per offending type, listing that type's label, the zero-based positions of the conflicting parameters, and their names.",
    "cases": [
        {
            "input": {"op": "validate_parameter_binding", "parameters": [{"name": "a", "type": "String", "name_match": false}, {"name": "b", "type": "Int", "name_match": false}]},
            "expected_output": "[accept with zero conflicts]\n[accept with zero conflicts]\n"
        },
        {
            "input": {"op": "validate_parameter_binding", "parameters": [{"name": "a", "type": "String", "name_match": true}, {"name": "b", "type": "String", "name_match": true}]},
            "expected_output": "[accept with zero conflicts]\n[accept with zero conflicts]\n"
        },
        {
            "input": {"op": "validate_parameter_binding", "parameters": [{"name": "a", "type": "String", "name_match": true}, {"name": "b", "type": "String", "name_match": false}]},
            "expected_output": "result=rejected\nerror=duplicate_parameter_type\nconflict_count=1\nconflict=type:String positions:0,1 names:a,b\n"
        },
        {
            "input": {"op": "validate_parameter_binding", "parameters": [{"name": "a", "type": "String", "name_match": true}, {"name": "b", "type": "String", "name_match": false}, {"name": "c", "type": "String", "name_match": false}]},
            "expected_output": "result=rejected\nerror=duplicate_parameter_type\nconflict_count=1\nconflict=type:String positions:0,1,2 names:a,b,c\n"
        },
        {
            "input": {"op": "validate_parameter_binding", "parameters": [{"name": "a", "type": "String", "name_match": true}, {"name": "b", "type": "String", "name_match": true}, {"name": "c", "type": "String", "name_match": true}]},
            "expected_output": "[accept with zero conflicts]\n[accept with zero conflicts]\n"
        }
    ]
}
```

---

### Feature 2: Effective Binding Name Resolution

**As a developer**, I want a deterministic rule that tells me the exact name a single parameter's value will be bound under, so I can predict and control how external values flow into my method.

**Expected Behavior / Usage:**

The input describes one parameter: an optional `parameter_name` (its declared name, which may be absent/`null`) and an optional `name_match` marker. The marker, when present, carries a `value` — an explicit binding name the developer chose, which may be the empty string.

Resolution follows a fixed precedence. If there is **no marker at all**, the parameter is bound under the default binding name `it`, irrespective of its declared name. If there **is a marker** and its `value` is **non-blank**, that explicit value is the binding name. If there is a marker but its `value` is **blank**, the binding name falls back to the parameter's own declared name — and if that declared name is itself absent (`null`), the resolution yields nothing, rendered as the placeholder `<null>`.

Output is a single line: `binding=<name>`, where a null result is shown as `[binding placeholder for missing names]`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_resolve_binding_name.json`

```json
{
    "description": "Resolve the effective binding name for a single parameter from its declared parameter name and an optional name-match marker. Rules: if no marker is present, the binding falls back to the default binding name 'it', regardless of the parameter name. If a marker is present and carries a non-blank explicit value, that explicit value becomes the binding name. If a marker is present but its value is blank, the binding name is the parameter's own name; and if the parameter name itself is absent (null), the binding resolves to null. The input carries an optional parameter_name (null when absent) and an optional name_match object holding the marker's value (omitted entirely when there is no marker). Output is a single binding line; a null result is rendered as the literal placeholder <null>.",
    "cases": [
        {
            "input": {"op": "resolve_binding_name", "parameter_name": "a", "name_match": {"value": "bindingX"}},
            "expected_output": "binding=bindingX\n"
        },
        {
            "input": {"op": "resolve_binding_name", "parameter_name": "a", "name_match": {"value": ""}},
            "expected_output": "binding=a\n"
        },
        {
            "input": {"op": "resolve_binding_name", "parameter_name": null, "name_match": {"value": ""}},
            "expected_output": "[binding placeholder for missing names]\n"
        },
        {
            "input": {"op": "resolve_binding_name", "parameter_name": "a"},
            "expected_output": "binding=it\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured module implementing the two functional points above — parameter-list ambiguity validation and effective binding-name resolution — with the core logic decoupled from any I/O or JSON parsing.

2. **The Execution/Test Adapter:** A runnable entry point that reads a single JSON command from stdin, dispatches on its `op` field to the appropriate core call, and prints the language-neutral result to stdout exactly as specified per feature. Errors are reported as normalized category lines (e.g. `error=duplicate_parameter_type`) with structured fields, never as host-language exception text.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`, namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout of the program under test, so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same logic pattern used for type grouping in the validate module
- fallback to parameter declaration or void
