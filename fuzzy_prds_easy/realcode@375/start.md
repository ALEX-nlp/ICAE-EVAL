## Product Requirement Document

# Wall-Clock Time Renderer - Deterministic 12/24-Hour Formatting

## Project Goal

Build a small time-formatting component that turns a moment in time into a fixed-width wall-clock string (`HH:MM`) in either 24-hour or 12-hour presentation, so a home-screen clock widget can display the current time consistently without each call site re-implementing padding and AM/PM folding rules.

---

## Background & Problem

Without this component, every place that needs to show a clock has to repeat the same fiddly logic: extract the hour and minute from an instant, decide whether to keep the hour as-is (24-hour) or fold it into a 12-hour range, and zero-pad single-digit values so the display does not jump between widths like `9:5` and `09:54`. Scattering that logic leads to inconsistent output, off-by-one mistakes around noon/midnight, and brittle string handling.

With this component, a caller passes the instant fields plus a single rendering mode and gets back a stable, two-segment `HH:MM` string that is always two digits per segment and follows one well-defined folding rule. The presentation choice (24-hour vs 12-hour) is the only knob, and the same instant always renders identically for a given mode.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a focused micro-utility. A small, well-organized solution is appropriate: keep the pure time-rendering rule in its own logical unit and keep the input/output adapter separate from it. Do not inflate it into a multi-layered framework, but do not collapse parsing, rendering, and I/O into one tangled blob either.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below describe a **black-box contract** for an execution adapter, not the internal data model of the renderer. The core rendering rule must take ordinary in-memory values (an instant and a mode flag) and return a string; it must know nothing about JSON, stdin, or stdout. The adapter alone parses the JSON command, calls the renderer, and prints the contract lines.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Separate input parsing, mode resolution, the pure rendering rule, and output formatting into distinct units.
   - **Open/Closed Principle (OCP):** Adding a new rendering mode should not require rewriting the existing rendering rule.
   - **Liskov Substitution Principle (LSP):** Any abstraction over rendering modes must be substitutable without changing caller behavior.
   - **Interface Segregation Principle (ISP):** Keep the renderer's public surface minimal — an instant plus a mode in, a string out.
   - **Dependency Inversion Principle (DIP):** The adapter depends on the renderer's abstraction, not on concrete I/O details bleeding into the core.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The renderer's public call should read naturally in the target language and hide padding/folding details.
   - **Resilience:** Malformed or incomplete commands must be reported as normalized, language-neutral error categories (see the adapter contract), never as raw runtime faults or host-language exception text.

---

## Core Features

### Feature 1: 24-Hour Wall-Clock Rendering

**As a developer**, I want to render an instant as a 24-hour `HH:MM` string, so I can show a stable, full-day clock that never needs an AM/PM marker.

**Expected Behavior / Usage:**

The adapter receives a command object describing a moment in time and a rendering mode. The relevant fields are `hour` (the hour of day, 0–23), `minute` (0–59), and `mode` set to `"24h"`. In 24-hour mode the hour is presented exactly as given. Both the hour and the minute are independently zero-padded to two digits (so `9` becomes `09`) and joined with a single colon to form the `HH:MM` string. The instant is interpreted in a fixed reference time zone so the result is deterministic across hosts. The output is two lines: a `time=` line carrying the rendered string, and a `mode=` line echoing the resolved rendering mode so a caller can confirm which path was taken. Midnight (`[a specific 24-hour midnight sentinel — ask the PM for the exact formatted string]`) and any single-digit hour or minute exercise the padding rule; noon (`12:30`) confirms the hour is left untouched in this mode.

**Test Cases:** `rcb_tests/public_test_cases/feature1_clock_24_hour.json`

```json
{
    "description": "Render an instant as a 24-hour wall-clock string. The adapter receives the hour-of-day (0-23) and minute together with the rendering mode '24h'. The hour is shown as-is and both hour and minute are zero-padded to two digits, joined by a colon. The output echoes the resolved mode so a caller can confirm which rendering path was taken.",
    "cases": [
        {
            "input": {"mode": "24h", "hour": 23, "minute": 4},
            "expected_output": "time=23:04\nmode=24h\n"
        },
        {
            "input": {"mode": "24h", "hour": 9, "minute": 54},
            "expected_output": "time=09:54\nmode=24h\n"
        }
    ]
}
```

---

### Feature 2: 12-Hour Wall-Clock Rendering

**As a developer**, I want to render an instant as a 12-hour `HH:MM` string, so I can show a clock in the familiar 12-hour presentation for users who prefer it.

**Expected Behavior / Usage:**

The adapter receives the same shape of command, but with `mode` set to `"12h"`. In 12-hour mode the folding rule is applied to the hour before rendering: if the hour is at or after noon (12 through 23), twelve is subtracted from it; if the hour is before noon (0 through [a specific 12-hour evening sentinel — ask the PM for the exact formatted string]), it is left unchanged. The resulting hour and the minute are each zero-padded to two digits and joined with a colon. As in 24-hour mode, the instant is interpreted in a fixed reference time zone, and the output is a `time=` line followed by a `mode=` line echoing the resolved mode. Note the boundary behavior this folding produces: an afternoon hour such as 23 renders as `[a specific 12-hour evening sentinel — ask the PM for the exact formatted string]`, noon (hour 12) folds to `00`, and pre-noon hours such as 9 or 0 render unchanged. This rule is a pure numeric fold and does not append any AM/PM marker.

**Test Cases:** `rcb_tests/public_test_cases/feature2_clock_12_hour.json`

```json
{
    "description": "Render an instant as a 12-hour wall-clock string. The adapter receives the hour-of-day (0-23) and minute together with the rendering mode '12h'. Any hour at or after noon has 12 subtracted from it before rendering, while hours before noon are shown unchanged; both hour and minute are zero-padded to two digits and joined by a colon. The output echoes the resolved mode.",
    "cases": [
        {
            "input": {"mode": "12h", "hour": 23, "minute": 4},
            "expected_output": "time=[a specific 12-hour evening sentinel — ask the PM for the exact formatted string]:04\nmode=12h\n"
        },
        {
            "input": {"mode": "12h", "hour": 9, "minute": 54},
            "expected_output": "time=09:54\nmode=12h\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured renderer implementing the two rendering modes described above. Its physical structure should stay small (a focused micro-utility), keeping the pure rendering rule decoupled from any input/output concerns.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the renderer. It reads a single JSON command object from stdin, resolves the rendering mode and instant fields, invokes the renderer, and prints the result to stdout exactly matching the per-feature contracts above (`time=<HH:MM>` then `mode=<mode>`). Malformed or incomplete commands are reported as normalized, language-neutral error categories (for example a missing required field or an unknown mode), never as raw host-language runtime text. This adapter is logically and physically separated from the core renderer.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_clock_24_hour.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_clock_24_hour@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- render the noon hour using the same mapping logic as defined for self-time
- prefix every output line with the standard timestamp key in snake_case
