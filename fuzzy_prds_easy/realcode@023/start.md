## Product Requirement Document

# Action Parameter Injection — Auto-Binding Action Arguments from a Request Parameter Bag

## Project Goal

Build a controller-side helper that, for an action whose method declares named formal parameters, automatically supplies each parameter from a request parameter bag by matching names. Developers write actions with ordinary, self-documenting parameter lists (required, optional-with-default, and by-name/keyword parameters) and let the helper resolve every argument from the incoming request, instead of manually reaching into a global parameter bag inside every action body.

---

## Background & Problem

Without this helper, every action body has to manually pull each value it needs out of a request parameter bag, repeating lookups, default handling, and presence checks by hand. This produces repetitive boilerplate, hides each action's real input contract inside its body, and makes "this input is required" or "this input defaults to X" invisible from the signature.

With this helper, the action's formal parameter list *is* the contract: the resolver inspects the declared parameters and fills them from the request bag by name. Required parameters that are absent are rejected with a clear, categorized error; optional and by-name parameters fall back to their declared defaults; and parameters are bound respecting positional vs. by-name semantics.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. For micro-utilities a well-organized single-file solution is acceptable; for a multi-responsibility system (signature inspection, name matching, default/keyword resolution, error categorization, output rendering) you MUST NOT collapse everything into one "god file" — use a clear, multi-file tree. Do not over-engineer, but avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core resolution logic must remain fully decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating each JSON command into idiomatic calls to the core resolver.

3. **Adherence to SOLID Design Principles:** Separate signature inspection, name-to-value resolution, validation/error categorization, and output formatting into distinct units (SRP). The resolver must be open for extension but closed for modification (OCP). Keep interfaces small and cohesive (ISP), and depend on abstractions rather than concrete I/O (DIP).

4. **Robustness & Interface Design:** The public interface must be elegant and idiomatic to the target language. Edge cases must be handled gracefully, and error conditions modeled explicitly (a categorized error result rather than a generic fault).

---

## Core Features

Across all features, the input is a single JSON object with two fields. `signature` is the ordered list of the action's formal parameters; each entry has a `name` and a `kind`, one of:

- `required` — positional, must be present in the bag;
- `optional` — positional, carries a `default`;
- `required_keyword` — by-name, must be present in the bag;
- `optional_keyword` — by-name, carries a `default`.

`params` is the request parameter bag, mapping names to string values.

For a successful resolution the adapter prints one line per declared parameter, **sorted by parameter name**:

```
arg=<name> kind=<kind> source=<injected|default> value=<rendered>
```

`source=injected` means the resolver supplied a value for that parameter (taken from the bag, or an explicit empty placeholder); `source=default` means the parameter kept its declared default. `value` renders a string as `"..."`, an explicit empty value as `<nil>`. When a required parameter is absent, the adapter instead prints a normalized error block (see Feature 2).

---

### Feature 1: Required positional binding

**As a developer**, I want each required positional parameter filled from the request bag by name, so I can declare an action's mandatory inputs directly in its signature.

**Expected Behavior / Usage:**

Every `required` positional parameter is matched by name against the bag and bound to that value. Parameters are reported sorted by name. An action that declares no parameters at all receives no injected arguments and produces no binding lines.

**Test Cases:** `rcb_tests/public_test_cases/feature1_required_positional.json`

```json
{
    "description": "An action declaring only required positional parameters has each one filled, in order, from the request bag by matching parameter name; an action declaring no parameters receives no injected arguments.",
    "cases": [
        {
            "input": {"signature": [{"name": "a", "kind": "required"}], "params": {"a": "1", "b": "2"}},
            "expected_output": "arg=a kind=required source=injected value=\"1\"\n"
        },
        {
            "input": {"signature": [{"name": "a", "kind": "required"}, {"name": "b", "kind": "required"}], "params": {"a": "1", "b": "2"}},
            "expected_output": "arg=a kind=required source=injected value=\"1\"\narg=b kind=required source=injected value=\"2\"\n"
        }
    ]
}
```

---

### Feature 2: Missing required parameter raises a categorized error

**As a developer**, I want a clear, normalized error when a required input is missing, so a malformed request is rejected instead of silently binding a wrong value.

**Expected Behavior / Usage:**

If any `required` or `required_keyword` parameter has no matching name in the bag, resolution fails. The adapter emits a normalized, language-neutral error: a first line `[Capture specific error lines using a known error prefix]` and a second line `missing=<names>` listing the absent required names, comma-joined and sorted. No partial bindings are printed.

**Test Cases:** `rcb_tests/public_test_cases/feature2_missing_required.json`

```json
{
    "description": "When a required parameter (positional or by-name) is absent from the request bag, injection fails with a normalized missing-required error listing the absent parameter names.",
    "cases": [
        {
            "input": {"signature": [{"name": "x", "kind": "required"}], "params": {"a": "1", "b": "2"}},
            "expected_output": "[Capture specific error lines using a known error prefix]\nmissing=x\n"
        },
        {
            "input": {"signature": [{"name": "a", "kind": "required_keyword"}, {"name": "x", "kind": "required_keyword"}], "params": {"a": "1", "b": "2"}},
            "expected_output": "[Capture specific error lines using a known error prefix]\nmissing=x\n"
        }
    ]
}
```

---

### Feature 3: Optional positional binding with defaults

**As a developer**, I want an optional positional parameter to use the bag value when present and otherwise keep its declared default, so optional inputs need no manual presence checks.

**Expected Behavior / Usage:**

A single `optional` positional parameter is bound to the bag value when its name is present (`source=injected`). When its name is absent it is omitted from the resolved arguments and keeps its declared default (`source=default`).

**Test Cases:** `rcb_tests/public_test_cases/feature3_optional_positional.json`

```json
{
    "description": "A single optional positional parameter takes the bag value when its name is present, otherwise it keeps its declared default and is omitted from injection.",
    "cases": [
        {
            "input": {"signature": [{"name": "a", "kind": "optional", "default": "a"}], "params": {"a": "1", "b": "2"}},
            "expected_output": "arg=a kind=optional source=injected value=\"1\"\n"
        },
        {
            "input": {"signature": [{"name": "x", "kind": "optional", "default": "x"}], "params": {"a": "1", "b": "2"}},
            "expected_output": "arg=x kind=optional source=default value=\"x\"\n"
        }
    ]
}
```

---

### Feature 4: Required parameter followed by an optional one

**As a developer**, I want a leading required parameter and a trailing optional parameter to resolve together correctly, so common "one mandatory, one optional" actions just work.

**Expected Behavior / Usage:**

The leading `required` parameter is filled from the bag. The trailing `optional` parameter takes its bag value when present (`source=injected`) or its declared default when absent (`source=default`).

**Test Cases:** `rcb_tests/public_test_cases/feature4_required_then_optional.json`

```json
{
    "description": "An action with a leading required parameter followed by a trailing optional one: the required parameter is filled from the bag, and the optional one takes its bag value when present or its declared default when absent.",
    "cases": [
        {
            "input": {"signature": [{"name": "a", "kind": "required"}, {"name": "b", "kind": "optional", "default": "b"}], "params": {"a": "1", "b": "2"}},
            "expected_output": "arg=a kind=required source=injected value=\"1\"\narg=b kind=optional source=injected value=\"2\"\n"
        },
        {
            "input": {"signature": [{"name": "a", "kind": "required"}, {"name": "x", "kind": "optional", "default": "x"}], "params": {"a": "1", "b": "2"}},
            "expected_output": "arg=a kind=required source=injected value=\"1\"\narg=x kind=optional source=default value=\"x\"\n"
        }
    ]
}
```

---

### Feature 5: Consecutive optional positionals

**As a developer**, I want two adjacent optional positional parameters resolved independently, so each one follows its own present/absent rule.

**Expected Behavior / Usage:**

Each `optional` positional is resolved against the bag on its own. A present name is injected and overrides the default; an absent name keeps its declared default. Note the ordering effect: when an absent optional sits **before** a present one, it must still occupy its position, so it is injected as an explicit empty placeholder (`value=<nil>`) rather than taking its default — whereas a trailing absent optional simply keeps its default.

**Test Cases:** `rcb_tests/public_test_cases/feature5_consecutive_optionals.json`

```json
{
    "description": "Two consecutive optional positional parameters are each resolved against the bag independently; a present name is injected (overriding the default) while an absent name keeps its declared default.",
    "cases": [
        {
            "input": {"signature": [{"name": "x", "kind": "optional", "default": "x"}, {"name": "a", "kind": "optional", "default": "a"}], "params": {"a": "1", "b": "2"}},
            "expected_output": "arg=a kind=optional source=injected value=\"1\"\narg=x kind=optional source=injected value=<nil>\n"
        },
        {
            "input": {"signature": [{"name": "a", "kind": "optional", "default": "a"}, {"name": "x", "kind": "optional", "default": "x"}], "params": {"a": "1", "b": "2"}},
            "expected_output": "arg=a kind=optional source=injected value=\"1\"\narg=x kind=optional source=default value=\"x\"\n"
        }
    ]
}
```

---

### Feature 6: Optional positionals preceding a required positional

**As a developer**, I want optional parameters declared before a trailing required parameter to resolve without stealing the required parameter's value, so I can place a mandatory input last in the list.

**Expected Behavior / Usage:**

When one or more `optional` positionals precede a trailing `required` positional, the leading optionals must be filled positionally so the required one still receives its value. A leading optional that is absent but sits before a supplied parameter is injected as an explicit empty placeholder (`value=<nil>`); a leading optional that is absent and not forced into position keeps its declared default.

**Test Cases:** `rcb_tests/public_test_cases/feature6_optional_before_required.json`

```json
{
    "description": "When optional positional parameters precede a trailing required parameter, the leading optionals must be filled positionally so the required one keeps its value; an absent leading optional that sits before a supplied parameter is injected as an explicit empty placeholder rather than taking its default.",
    "cases": [
        {
            "input": {"signature": [{"name": "x", "kind": "optional", "default": "x"}, {"name": "a", "kind": "required"}], "params": {"a": "1", "b": "2"}},
            "expected_output": "arg=a kind=required source=injected value=\"1\"\narg=x kind=optional source=default value=\"x\"\n"
        },
        {
            "input": {"signature": [{"name": "x", "kind": "optional", "default": "x"}, {"name": "b", "kind": "optional", "default": "b"}, {"name": "a", "kind": "required"}], "params": {"a": "1", "b": "2"}},
            "expected_output": "arg=a kind=required source=injected value=\"1\"\narg=b kind=optional source=injected value=\"2\"\narg=x kind=optional source=injected value=<nil>\n"
        }
    ]
}
```

---

### Feature 7: By-name (keyword) parameter binding

**As a developer**, I want by-name parameters bound from the bag by matching name, so I can declare keyword inputs with required and optional semantics.

**Expected Behavior / Usage:**

`optional_keyword` and `required_keyword` parameters are matched by name. A present optional keyword is injected; an absent optional keyword keeps its declared default; a present required keyword is injected. (An absent required keyword triggers the missing-required error of Feature 2.)

**Test Cases:** `rcb_tests/public_test_cases/feature7_keyword_arguments.json`

```json
{
    "description": "By-name keyword parameters are bound from the bag by matching name; a present optional keyword is injected, an absent optional keyword keeps its declared default, and a present required keyword is injected.",
    "cases": [
        {
            "input": {"signature": [{"name": "a", "kind": "optional_keyword", "default": null}, {"name": "x", "kind": "optional_keyword", "default": "x"}], "params": {"a": "1", "b": "2"}},
            "expected_output": "arg=a kind=optional_keyword source=injected value=\"1\"\narg=x kind=optional_keyword source=default value=\"x\"\n"
        },
        {
            "input": {"signature": [{"name": "a", "kind": "required_keyword"}], "params": {"a": "1", "b": "2"}},
            "expected_output": "arg=a kind=required_keyword source=injected value=\"1\"\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the resolution behavior above, with its physical structure aligned to the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable entry point that reads a single JSON object from stdin, invokes the core resolver, and prints the result to stdout, strictly matching the per-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `test_cases`) to choose the directory of case files. For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{stem}@{index:03}.txt` containing **only** the raw stdout of the program under test (no PASS/FAIL or metadata), so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the pre-injection priority rule
- respect the defined sequence for mixed types
