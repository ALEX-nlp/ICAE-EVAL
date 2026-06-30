## Product Requirement Document

# Supplemental Utility Toolkit — Array, Function, Math, and Object Helpers

## Project Goal

Build a small, dependency-free collection of general-purpose helper functions that smooth over common rough edges in everyday programming — normalizing signed list offsets, splicing list ranges, capturing the outcome of a risky call, comparing decimals with a tolerance, and selectively copying or extending object properties — so developers can reuse these well-defined primitives instead of re-deriving them in every project.

---

## Background & Problem

Without a shared toolkit, developers repeatedly hand-roll the same fiddly primitives: translating negative indices, conditionally appending sub-ranges of one list to another, wrapping calls in try/catch just to branch on success vs. failure, comparing floating-point numbers without exact equality, and picking or merging object properties while carefully skipping absent values. Each re-implementation is a chance to introduce off-by-one bugs, lose falsy-but-valid values, or leak runtime error details.

With this toolkit, each of those concerns is captured once as a precise, well-tested function with a clear input/output contract: offsets resolve predictably, range splicing handles the empty and missing cases, risky calls return a uniform two-slot success-or-error outcome, decimal comparison takes an explicit tolerance, and property selection/extension treats falsy-but-defined values correctly while ignoring truly absent ones.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains. Here, the natural split is one cohesive module per concern (array helpers, function helpers, math helpers, object/property helpers).

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic function calls to the core domain.

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

Throughout this document, the JSON value `null` denotes a present, explicit empty value (which is treated as a defined value), while a property that is simply omitted from the input denotes the language's "no value" (the absent marker). In rendered output, a returned value that is the absent marker is written literally as `undefined`; all other returned values are rendered in compact JSON form.

### Feature 1: Signed Offset To Array Index

**As a developer**, I want to convert a possibly-negative positional offset into a concrete array index, so I can address elements from either end of a list with one consistent rule.

**Expected Behavior / Usage:**

The input supplies a list and an integer offset. A zero or positive offset maps to itself and is returned unchanged, even when it is larger than the list length (no clamping). A negative offset is interpreted relative to the end of the list and resolves to the list length plus the offset; when the magnitude of the negative offset exceeds the list length, the resolved index is itself negative. The output reports the resolved index as `index=<value>` followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_array_index.json`

```json
{
    "description": "Convert a signed positional offset into a non-negative array index, given an array and an offset. A zero or positive offset is returned unchanged (even when it exceeds the array length). A negative offset counts backward from the end and is resolved to the array length plus the offset, which may itself be negative when the magnitude exceeds the length. The output reports the resolved index value.",
    "cases": [
        {"input": {"op": "to_index", "array": ["a", "b", "c"], "offset": 2}, "expected_output": "index=2\n"},
        {"input": {"op": "to_index", "array": ["a", "b", "c"], "offset": -1}, "expected_output": "index=2\n"}
    ]
}
```

---

### Feature 2: Append List Range

**As a developer**, I want to append the elements of one list onto another (optionally only a sub-range), so I can concatenate lists with consistent handling of the empty and missing cases.

**Expected Behavior / Usage:**

The input supplies an optional destination list (`to`), an optional source list (`from`), and optional integer `start`/`end` bounds. If the source is absent or empty, the destination is returned unchanged. If the destination is absent, a brand-new list containing the selected slice of the source is returned. Otherwise the selected range of source elements is appended onto the destination, and the destination is returned. The `start` and `end` bounds select the half-open sub-range `[start, end)` of the source; either bound may be negative, in which case it counts backward from the end of the source. When `start` is omitted it defaults to the beginning, and when `end` is omitted it defaults to the source length. The output reports the resulting list as `result=<list>`, or `result=undefined` when there is no list to return, followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature2_array_addrange.json`

```json
{
    "description": "Append the elements of a source list onto a destination list within an optional range, and report the resulting list. When the source is absent or empty, the destination is returned unchanged. When the destination is absent, a fresh list holding the selected slice of the source is returned instead. The optional start and end bounds select a sub-range of the source; a negative bound counts backward from the end of the source. The output reports the resulting list, or the neutral absent marker when there is no list to return.",
    "cases": [
        {"input": {"op": "add_range", "to": [1, 2]}, "expected_output": "result=[1,2]\n"},
        {"input": {"op": "add_range", "to": [1, 2], "from": [7, 8, 9]}, "expected_output": "result=[1,2,7,8,9]\n"},
        {"input": {"op": "add_range", "from": [7, 8, 9]}, "expected_output": "result=[7,8,9]\n"}
    ]
}
```

---

### Feature 3: Capture Result Or Error

**As a developer**, I want to run a risky operation and uniformly capture either its produced value or the error it raised, so I can branch on outcome without scattering try/catch everywhere.

**Expected Behavior / Usage:**

The operation is invoked and its outcome captured as a two-slot result. On success, the first slot holds the produced value and the second slot is the absent marker. On failure, the first slot is the absent marker and the second slot carries the raised error's human-readable message. The input selects the behavior: an action of returning yields a supplied value; an action of raising produces an error carrying a supplied message. The error must be surfaced only as its domain message text — never as any runtime-specific type name, stack trace, or object rendering. The output reports the two slots on separate lines: `result[0]=<first slot>` then `result[1]=<second slot>`, each followed by a newline, where an absent slot is written as `undefined`, a produced value is rendered in compact JSON form, and a captured error is rendered as its plain message text.

**Test Cases:** `rcb_tests/public_test_cases/feature3_try_invoke.json`

```json
{
    "description": "Invoke a zero-argument operation and capture either its result or the error it raised, returning a two-slot outcome. The first slot holds the produced value and the second is the absent marker when the operation completes normally; on failure the first slot is the absent marker and the second carries the raised error's message. The request selects whether the operation returns a value or raises an error carrying a given message. The output reports both slots on separate lines, in order.",
    "cases": [
        {"input": {"op": "try_invoke", "action": "return", "value": 123}, "expected_output": "result[0]=123\nresult[1]=undefined\n"},
        {"input": {"op": "try_invoke", "action": "throw", "message": "failed"}, "expected_output": "result[0]=undefined\nresult[1]=failed\n"}
    ]
}
```

---

### Feature 4: Approximate Numeric Equality

**As a developer**, I want to compare two numbers within a tolerance, so I can treat decimals that are "close enough" as equal without relying on exact floating-point equality.

**Expected Behavior / Usage:**

The input supplies two numbers and a non-negative tolerance. The two numbers are considered equal when the absolute value of their difference is strictly less than the tolerance, and not equal otherwise (a difference exactly equal to the tolerance counts as not equal). The output reports the decision as `equal=true` or `equal=false`, followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature4_approx_equal.json`

```json
{
    "description": "Decide whether two numbers are close enough to be treated as equal, given a non-negative tolerance. They are considered equal when the absolute difference between them is strictly less than the tolerance, and not equal otherwise. This is useful for comparing decimal values that cannot be compared with exact equality. The output reports the equality decision.",
    "cases": [
        {"input": {"op": "approx_equal", "f1": 1.25, "f2": 1.2499, "tolerance": 0.001}, "expected_output": "equal=true\n"},
        {"input": {"op": "approx_equal", "f1": 10, "f2": 11, "tolerance": 0.5}, "expected_output": "equal=false\n"}
    ]
}
```

---

### Feature 5: Selective Property Picking

**As a developer**, I want to copy chosen properties out of an object into a fresh object, optionally renaming them, so I can build slim projections while correctly keeping falsy-but-defined values and dropping truly absent ones.

**Expected Behavior / Usage:**

*5.1 Pick A Single Property — copy one named property into a new one-property object*

The input supplies a source object, the key to pick, and an optional alternate output name. The value is picked only when the property is present and its value is not the absent marker; defined falsy values (the boolean `false`, the number `0`, the explicit `null`, and the empty string) are still picked. When an alternate name is supplied, the returned object uses that name as its single key; otherwise it uses the original key. When nothing is picked, the absent marker is returned. The output reports `result=<object>`, or `result=undefined` when nothing was picked, followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_pick_value.json`

```json
{
    "description": "Pick a single property's value from a source object and return it wrapped in a brand-new single-property object, optionally renaming the property. The picked value is included only when the property is present and its value is not the absent marker; defined falsy values (such as the boolean false, the number zero, the explicit null, and the empty string) are still picked. When an alternate output name is supplied, the returned object uses that name as its key. When nothing is picked, the absent marker is reported instead.",
    "cases": [
        {"input": {"op": "pick_value", "obj": {}, "key": "x"}, "expected_output": "result=undefined\n"},
        {"input": {"op": "pick_value", "obj": {"x": 123}, "key": "x"}, "expected_output": "result={\"x\":123}\n"},
        {"input": {"op": "pick_value", "obj": {"x": 0}, "key": "x", "name": "y"}, "expected_output": "result={\"y\":0}\n"}
    ]
}
```

*5.2 Pick Multiple Properties — copy several named properties into one new object, renaming positionally*

The input supplies a source object, a list of keys to pick, and an optional list of alternate output names. Each requested key contributes to the result only when it is present and its value is not the absent marker; missing keys are silently skipped. When alternate names are supplied, they are applied positionally (the n-th name renames the n-th key), and the result preserves the order in which the keys were requested. When no requested key yields a value — including when the list of keys is empty — the absent marker is returned. The output reports `result=<object>`, or `result=undefined`, followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_pick_values.json`

```json
{
    "description": "Pick the values for several requested properties from a source object and return them collected into one new object, optionally renaming each property. A property contributes to the result only when it is present in the source and its value is not the absent marker; requested properties that are missing are silently skipped. When alternate output names are supplied, they are used positionally as the keys of the picked values, preserving the order in which the properties were requested. When no requested property yields a value (including when no properties are requested), the absent marker is reported instead.",
    "cases": [
        {"input": {"op": "pick_values", "obj": {}, "keys": ["x"]}, "expected_output": "result=undefined\n"},
        {"input": {"op": "pick_values", "obj": {"x": 123, "y": "test", "z": true}, "keys": ["x", "y", "z"]}, "expected_output": "result={\"x\":123,\"y\":\"test\",\"z\":true}\n"},
        {"input": {"op": "pick_values", "obj": {"x": 123, "y": "test", "z": true}, "keys": ["x", "z"], "names": ["a", "b-b"]}, "expected_output": "result={\"a\":123,\"b-b\":true}\n"}
    ]
}
```

---

### Feature 6: In-Place Object Extension

**As a developer**, I want to merge additional properties into an existing object (or into every object in a list), so I can enrich data in place without allocating new containers.

**Expected Behavior / Usage:**

*6.1 Extend One Object — merge additional properties into a single object*

The input supplies a source object and a set of additional properties. Every additional property is added to the source object in place, and the same object is returned. When no additional properties are supplied, the object is returned unchanged. The output reports `result=<object>` followed by a newline, with the original properties appearing first and any added properties after.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_extend_object.json`

```json
{
    "description": "Merge a set of additional properties into a single existing object in place, and report the resulting object. Every supplied additional property is added to the original object, and the same (now-extended) object is returned. When no additional properties are supplied, the object is reported unchanged. The output reports the resulting object with the original properties first, followed by any added properties.",
    "cases": [
        {"input": {"op": "extend_object", "obj": {"base": "base object"}, "props": {"extended": 12345}}, "expected_output": "result={\"base\":\"base object\",\"extended\":12345}\n"},
        {"input": {"op": "extend_object", "obj": {"base": "base object"}, "props": {}}, "expected_output": "result={\"base\":\"base object\"}\n"}
    ]
}
```

*6.2 Extend Every Object In A List — merge additional properties into each element*

The input supplies a list of objects and a set of additional properties. Each element of the list receives all the additional properties in place, and the same list is returned. When no additional properties are supplied, every element is returned unchanged. The output reports `result=<list>` followed by a newline, with each element's original properties first and any added properties after.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_extend_object_array.json`

```json
{
    "description": "Merge a set of additional properties into every object of a list in place, and report the resulting list. Each element of the list receives all supplied additional properties, and the same (now-extended) list is returned. When no additional properties are supplied, every element is reported unchanged. The output reports the resulting list with each element's original properties first, followed by any added properties.",
    "cases": [
        {"input": {"op": "extend_object_array", "arr": [{"base": "base object"}], "props": {"extended": 12345}}, "expected_output": "result=[{\"base\":\"base object\",\"extended\":12345}]\n"},
        {"input": {"op": "extend_object_array", "arr": [{"base": "base object"}, {"base": "another base object"}], "props": {"extended": 12345}}, "expected_output": "result=[{\"base\":\"base object\",\"extended\":12345},{\"base\":\"another base object\",\"extended\":12345}]\n"}
    ]
}
```

---

### Feature 7: Property Existence Check

**As a developer**, I want to test whether a subject actually contains a given property, so I can safely narrow an unknown value before accessing it.

**Expected Behavior / Usage:**

The input supplies a subject and a list of property names to check. A property is reported as existing only when the subject is a non-null object that contains that property; for any subject that is not a non-null object — text, a number, a boolean, the explicit `null`, or the absent marker (when no subject is provided) — every requested property is reported as not existing. The output reports one line per requested property, in the order requested, formatted as `<property>=true` or `<property>=false`, each followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature7_has_property.json`

```json
{
    "description": "Determine, for each requested property name, whether that property exists on a given subject. A property exists only when the subject is a non-null object that contains the property; any non-object subject (text, number, boolean, the explicit null, or the absent marker when no subject is provided) yields a negative result for every requested property. The output reports one line per requested property, in the order requested, naming the property and its existence decision.",
    "cases": [
        {"input": {"op": "has_property", "obj": {"message": "code", "code": 0}, "properties": ["code", "message", "stack"]}, "expected_output": "code=true\nmessage=true\nstack=false\n"},
        {"input": {"op": "has_property", "obj": "string", "properties": ["0"]}, "expected_output": "0=false\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above, organized as cohesive per-concern modules (array helpers, function helpers, math helpers, object/property helpers). The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request object from stdin, selects the operation via the request's `op` field, invokes the matching core function, and prints the rendered result to stdout, matching the per-feature contracts above. The adapter is also responsible for normalizing any raised error down to its plain domain message (never leaking runtime-specific type names, stack traces, or object renderings).

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- default key binding similar to C022
- empty object handling logic
