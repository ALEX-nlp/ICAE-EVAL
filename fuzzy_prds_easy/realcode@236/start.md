## Product Requirement Document

# Geometry & Record Toolkit — Rectangle Text Serialization and Immutable Value Records

## Project Goal

Build a small domain toolkit that lets an application persist screen-rectangle geometry as plain text and model its running-process/window entities as immutable value records, so developers can save/restore window placement and derive modified entity snapshots without hand-writing serialization or defensive copying.

---

## Background & Problem

Desktop applications routinely need to (a) remember where a window was last placed and restore it on next launch, and (b) keep a consistent in-memory picture of the running processes and on-screen windows they manage. Both needs share a recurring pain: geometry must survive a round trip through a plain-text settings store, and entity snapshots must be cheap to copy with only a few fields changed while everything else is preserved and value-equality stays well-defined.

Without a shared toolkit, developers hand-roll ad-hoc geometry serialization (easy to get number formatting subtly wrong) and mutate shared objects in place (causing aliasing bugs and brittle equality checks). This toolkit provides one well-defined contract: a reversible rectangle text codec, and immutable process/window records that support copy-with-overrides and value equality.

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

### Feature 1: Rectangle Text Serialization

**As a developer**, I want to convert a screen rectangle to and from a plain-text record, so I can persist window geometry in a string-only settings store and restore it later without loss.

**Expected Behavior / Usage:**

A rectangle is described by four numbers: its `left` and `top` origin coordinates and its `width` and `height` extent. The serialized text form is a single-line object mapping the four field names `left`, `top`, `width`, `height` to their numeric values, in that field order. All four values are emitted in fractional (decimal) form — a whole number such as `100` is written as `100.0`, while a value with a fractional part such as `640.25` is preserved exactly. Negative coordinates are permitted. Decoding reverses this exactly: parsing a serialized record reconstructs the same four coordinates. The two directions are mutual inverses (a value encoded and then decoded yields the original coordinates).

*1.1 Encode a rectangle to its text record — produce the serialized single-line form*

The input supplies the four numeric fields of a rectangle. The output is the serialized record exactly as the encoder produces it: a single line containing the four named fields in `left`, `top`, `width`, `height` order, each value rendered in decimal/fractional form, followed by a trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_encode_rect.json`

```json
{
    "description": "Serialize a rectangular region, described by its left/top origin and its width/height extent, into a compact textual record so the geometry can be persisted as plain text. The output is the serialized record exactly as produced by the encoder; every coordinate is emitted in its fractional form.",
    "cases": [
        {
            "input": {"action": "encode_rect", "left": 0, "top": 0, "width": 100, "height": 100},
            "expected_output": "{\"left\":0.0,\"top\":0.0,\"width\":100.0,\"height\":100.0}\n"
        }
    ]
}
```

*1.2 Decode a text record back to a rectangle — recover the four coordinates*

The input supplies a serialized rectangle record (the exact text form produced by the encoder). The output lists each recovered coordinate on its own line as `left=<value>`, `top=<value>`, `width=<value>`, `height=<value>` (in that order, each value in decimal/fractional form), so the round trip with the encoder is observable.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_decode_rect.json`

```json
{
    "description": "Reconstruct a rectangular region from its serialized textual record, recovering the original left/top origin and width/height extent. The output lists each recovered coordinate so the round trip with the encoder is observable.",
    "cases": [
        {
            "input": {"action": "decode_rect", "json": "{\"left\":0.0,\"top\":0.0,\"width\":100.0,\"height\":100.0}"},
            "expected_output": "left=0.0\ntop=0.0\nwidth=100.0\nheight=100.0\n"
        }
    ]
}
```

---

### Feature 2: Immutable Process Record With Copy-On-Write And Value Equality

**As a developer**, I want an immutable record of a running process that I can cheaply copy while overriding only selected fields, so I can produce updated snapshots without mutating shared state and still compare records by value.

**Expected Behavior / Usage:**

A process record carries three fields: an `executable` name, an integer `pid`, and a lifecycle `status` that is one of `normal`, `suspended`, or `unknown`. The record is immutable. A copy operation accepts a set of optional field overrides; any field named in the overrides is replaced with the supplied value, and every field not named is carried over unchanged from the original. Records compare by value: two process records are equal exactly when all three fields are equal. Therefore copying with no overrides yields a record equal to the original, while copying that changes any field yields a record that is not equal to the original. The output reports each field of the resulting record — `executable=<value>`, `pid=<value>`, `status=<value>` — followed by `equals_base=<true|[a specific boolean literal indicating override success]>` indicating whether the resulting record is value-equal to the original, each on its own line.

**Test Cases:** `rcb_tests/public_test_cases/feature2_process_copy.json`

```json
{
    "description": "Produce a derived copy of an immutable process record, where only the explicitly supplied fields are replaced and all other fields are carried over unchanged. The output reports every field of the resulting record plus whether the derived record is value-equal to the original.",
    "cases": [
        {
            "input": {"action": "process_copy", "base": {"executable": "code-insiders", "pid": 45686, "status": "normal"}},
            "expected_output": "executable=code-insiders\npid=45686\nstatus=normal\nequals_base=true\n"
        },
        {
            "input": {"action": "process_copy", "base": {"executable": "code-insiders", "pid": 45686, "status": "normal"}, "overrides": {"executable": "explorer.exe"}},
            "expected_output": "executable=explorer.exe\npid=45686\nstatus=normal\nequals_base=[a specific boolean literal indicating override success]\n"
        }
    ]
}
```

---

### Feature 3: Immutable Window Record With Nested Process, Copy-On-Write And Value Equality

**As a developer**, I want an immutable record of an on-screen window that nests a process record and supports the same copy-with-overrides and value-equality semantics, so I can swap out a window's whole process snapshot or rename it without touching the original.

**Expected Behavior / Usage:**

A window record carries three fields: an integer `id`, a nested `process` record (the same kind of record described in Feature 2), and a `title` string. The record is immutable. A copy operation accepts optional overrides for `id`, `title`, and/or `process`; any field named is replaced (the `process` override replaces the entire nested record), and any field not named is carried over unchanged. Records compare by value: two window records are equal exactly when their `id`, `title`, and nested `process` (compared by value) are all equal. The output reports each field of the resulting record — `id=<value>`, `title=<value>`, then the nested fields `process.executable=<value>`, `process.pid=<value>`, `process.status=<value>` — followed by `equals_base=<true|[a specific boolean literal indicating override success]>` indicating whether the resulting record is value-equal to the original, each on its own line.

**Test Cases:** `rcb_tests/public_test_cases/feature3_window_copy.json`

```json
{
    "description": "Produce a derived copy of an immutable window record, where only the explicitly supplied fields (including a wholly replaced nested process record) are substituted and all other fields are carried over unchanged. The output reports every field of the resulting record, including the nested process fields, plus whether the derived record is value-equal to the original.",
    "cases": [
        {
            "input": {"action": "window_copy", "base": {"id": 130023427, "process": {"executable": "code-insiders", "pid": 45686, "status": "normal"}, "title": "Untitled-2 - Visual Studio Code - Insiders"}, "overrides": {"process": {"executable": "code-insiders", "pid": 45686, "status": "suspended"}}},
            "expected_output": "id=130023427\ntitle=Untitled-2 - Visual Studio Code - Insiders\nprocess.executable=code-insiders\nprocess.pid=45686\nprocess.status=suspended\nequals_base=[a specific boolean literal indicating override success]\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic (the rectangle codec and the immutable records) must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON command and prints the resulting record (or a neutral error) to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `encode_rect` serializes a rectangle from its four numeric fields; `decode_rect` reconstructs a rectangle from a serialized record string; `process_copy` derives a copy of a process record from a `base` and optional `overrides`; `window_copy` derives a copy of a window record from a `base` and optional `overrides`. Numeric coordinates are always rendered in decimal/fractional form. Any malformed input or unsupported action must be reported as a neutral, language-independent error line rather than leaking host-runtime details.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- recursive deep copy logic applied to nested records
- copy-on-write semantics for process copying
