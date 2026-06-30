## Product Requirement Document

# Workspace Navigator — Compute the Previous/Next Workspace From the Current Desktop State

## Project Goal

Build a small, pure-logic library that, given a snapshot of the current multi-monitor desktop state and a few navigation options, computes which workspace a user should move to when they ask to go to the *previous* or the *next* workspace. The library performs only index arithmetic over workspace ids — it never talks to a window manager, a display server, or any external process. It simply answers the question: "given where I am now and what exists, which workspace id should I land on?"

---

## Background & Problem

On a tiling, multi-monitor desktop, workspaces are identified by positive integer ids. At any moment:

- one workspace is **active** (the one the user is currently on);
- the **focused monitor** hosts an ordered subset of those workspaces;
- some workspace ids are **occupied** (in use) across *all* monitors, while others are empty/unused.

Users want GNOME-style switching: pressing "next"/"previous" should move along the workspaces of the *focused monitor*, and when they fall off either end of that monitor's list, a fresh empty workspace should be created in that direction (skipping over ids that are already occupied by *other* monitors, so a brand-new empty one is reached rather than wrapping onto someone else's workspace). Several options modify this behavior: suppressing empty-workspace creation in a direction, or wrapping (cycling) within the focused monitor instead of creating new workspaces.

The core challenge is purely arithmetic and fully deterministic: from `(current id, the focused monitor's workspace ids, the globally occupied ids, options)`, compute the target id. This library isolates that computation so it can be tested in complete isolation from any live desktop.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities, it MUST NOT be a single "god file"; output a clear, multi-file directory tree that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core navigation logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating a JSON request into idiomatic calls to the core domain and rendering the result.

3. **Adherence to SOLID Design Principles:** scaled appropriately to the project's size — separate parsing, validation, core computation, and output formatting into distinct logical units; keep the core engine open for extension but closed for modification; keep public interfaces small and cohesive; and have high-level logic depend on abstractions rather than on I/O details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases (boundary ids, fully-occupied ranges, single-workspace monitors) gracefully and deterministically.

---

## The Computation Contract (shared by all features)

Every feature is exercised through the same request shape. A single request describes the desktop state plus the navigation options:

| Field | Type | Meaning |
|-------|------|---------|
| `current_id` | integer | The id of the currently active workspace. |
| `monitor_ids` | array of integers | The ids of the workspaces that exist on the **focused monitor**. Order does not matter; the library treats them as a sorted set. |
| `occupied_ids` | array of integers | The ids that are occupied/in use across **all** monitors. Order does not matter. |
| `previous` | boolean (default `false`) | Direction selector: `true` asks for the previous workspace, `false` asks for the next workspace. |
| `no_empty_before` | boolean (default `false`) | When going to the previous workspace, do not create a new empty workspace behind the focused monitor's first workspace. |
| `no_empty_after` | boolean (default `false`) | When going to the next workspace, do not create a new empty workspace ahead of the focused monitor's last workspace. |
| `cycle` | boolean (default `false`) | Wrap within the focused monitor instead of creating new workspaces. |

**Result:** a single workspace id — the id the user should move to. The execution adapter prints it as one line of the form `id=<integer>`.

**General rules:**

- Workspace ids are positive integers. The lowest valid id is `1`; the highest is the largest representable signed 32-bit integer (`2147483647`).
- "Next"/"previous" first try to move **within the focused monitor's own ordered list**. Only when the active workspace sits at the relevant end of that list do the empty-creation / cycling rules come into play.
- When creating an empty workspace in a direction, the chosen id is the nearest id in that direction that is **not** in `occupied_ids` (so occupied ids belonging to other monitors are skipped).
- When the requested move is impossible (no room left, or disabled), the active id is returned unchanged.

---

## Core Features

### Feature 1: Next Workspace On The Same Monitor

**As a user**, I want pressing "next" to move to the following workspace on my focused monitor when one exists, so I navigate my own monitor's workspaces in order.

**Expected Behavior / Usage:** When the active workspace is not the highest-id workspace on the focused monitor, the result is the next-higher id drawn from the focused monitor's own list. Ids belonging to other monitors that happen to lie numerically in between are ignored.

**Test Cases:** `rcb_tests/public_test_cases/feature1_next_adjacent_on_monitor.json`

```json
{
    "cases": [
        {
            "input": {"current_id": 500, "monitor_ids": [500, 502], "occupied_ids": [500, 502], "previous": false},
            "expected_output": "id=502\n"
        },
        {
            "input": {"current_id": 500, "monitor_ids": [500, 504], "occupied_ids": [500, 502, 504], "previous": false},
            "expected_output": "id=504\n"
        }
    ]
}
```

---

### Feature 2: Next Creates The Nearest Empty Workspace

**As a user**, I want pressing "next" at the end of my monitor to drop me onto a fresh empty workspace, so I can spread my work out without colliding with workspaces used elsewhere.

**Expected Behavior / Usage:** When the active workspace is the highest-id workspace on the focused monitor and empty-creation is allowed, the result is the smallest id strictly greater than the active id that is not occupied on any monitor. Occupied ids immediately above are skipped until the first free id is found.

**Test Cases:** `rcb_tests/public_test_cases/feature2_next_create_empty.json`

```json
{
    "cases": [
        {
            "input": {"current_id": 502, "monitor_ids": [500, 502], "occupied_ids": [500, 502], "previous": false},
            "expected_output": "id=503\n"
        },
        {
            "input": {"current_id": 4, "monitor_ids": [3, 4], "occupied_ids": [3, 4, 6], "previous": false},
            "expected_output": "id=5\n"
        }
    ]
}
```

---

### Feature 3: Next With Empty-Creation Disabled

**As a user**, I want an option that stops "next" from creating new empty workspaces, so I never accidentally open workspaces beyond what already exists on my monitor.

**Expected Behavior / Usage:** When the active workspace is the highest-id workspace on the focused monitor and creating empty workspaces ahead is disabled, the active id is returned unchanged. This holds whether the monitor has several workspaces or just one.

**Test Cases:** `rcb_tests/public_test_cases/feature3_next_no_empty.json`

```json
{
    "cases": [
        {
            "input": {"current_id": 502, "monitor_ids": [500, 502], "occupied_ids": [500, 502], "previous": false, "no_empty_after": true},
            "expected_output": "id=502\n"
        },
        {
            "input": {"current_id": 498, "monitor_ids": [498], "occupied_ids": [498], "previous": false, "no_empty_after": true},
            "expected_output": "id=498\n"
        }
    ]
}
```

---

### Feature 4: Next Wraps When Cycling

**As a user**, I want an option to cycle, so that pressing "next" at the end of my monitor jumps back to the beginning of my monitor instead of creating a new workspace.

**Expected Behavior / Usage:** When the active workspace is the highest-id workspace on the focused monitor and cycling is enabled, the result is the lowest-id workspace on the focused monitor. Cycling takes precedence over the disable-empty option, and a single-workspace monitor wraps onto itself.

**Test Cases:** `rcb_tests/public_test_cases/feature4_next_cycle.json`

```json
{
    "cases": [
        {
            "input": {"current_id": 504, "monitor_ids": [500, 502, 504], "occupied_ids": [498, 500, 502, 504, 506], "previous": false, "cycle": true},
            "expected_output": "id=500\n"
        },
        {
            "input": {"current_id": 502, "monitor_ids": [500, 502], "occupied_ids": [500, 502], "previous": false, "cycle": true},
            "expected_output": "id=500\n"
        }
    ]
}
```

---

### Feature 5: Next Has No Room (Upper Boundary)

**As a user**, I want "next" to be safe at the very top of the id range, so the desktop never tries to move past the largest possible workspace.

**Expected Behavior / Usage:** When the active workspace is the highest-id workspace on the focused monitor, empty-creation is allowed, but no higher free id exists — either because the active id is already the maximum representable id, or because every id above it is occupied up to that maximum — the active id is returned unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature5_next_upper_boundary.json`

```json
{
    "cases": [
        {
            "input": {"current_id": 2147483647, "monitor_ids": [500, 2147483647], "occupied_ids": [500, 2147483647], "previous": false},
            "expected_output": "id=2147483647\n"
        },
        {
            "input": {"current_id": 2147483645, "monitor_ids": [2147483645], "occupied_ids": [2147483645, 2147483646, 2147483647], "previous": false},
            "expected_output": "id=2147483645\n"
        }
    ]
}
```

---

### Feature 6: Previous Workspace On The Same Monitor

**As a user**, I want pressing "previous" to move to the preceding workspace on my focused monitor when one exists, so I navigate my own monitor's workspaces in order.

**Expected Behavior / Usage:** When the active workspace is not the lowest-id workspace on the focused monitor, the result is the next-lower id drawn from the focused monitor's own list. Ids belonging to other monitors that happen to lie numerically in between are ignored.

**Test Cases:** `rcb_tests/public_test_cases/feature6_previous_adjacent_on_monitor.json`

```json
{
    "cases": [
        {
            "input": {"current_id": 502, "monitor_ids": [500, 502], "occupied_ids": [500, 502], "previous": true},
            "expected_output": "id=500\n"
        },
        {
            "input": {"current_id": 504, "monitor_ids": [500, 504], "occupied_ids": [500, 502, 504], "previous": true},
            "expected_output": "id=500\n"
        }
    ]
}
```

---

### Feature 7: Previous Creates The Nearest Empty Workspace

**As a user**, I want pressing "previous" at the start of my monitor to drop me onto a fresh empty workspace below, so I can extend my workspaces backward without colliding with workspaces used elsewhere.

**Expected Behavior / Usage:** When the active workspace is the lowest-id workspace on the focused monitor and empty-creation is allowed, the result is the largest id strictly smaller than the active id that is not occupied on any monitor. Occupied ids immediately below are skipped until the first free id is found; the search never goes below the lowest valid id.

**Test Cases:** `rcb_tests/public_test_cases/feature7_previous_create_empty.json`

```json
{
    "cases": [
        {
            "input": {"current_id": 500, "monitor_ids": [500, 501], "occupied_ids": [500, 501], "previous": true},
            "expected_output": "id=499\n"
        },
        {
            "input": {"current_id": 3, "monitor_ids": [3, 4], "occupied_ids": [1, 3, 4], "previous": true},
            "expected_output": "id=2\n"
        }
    ]
}
```

---

### Feature 8: Previous With Empty-Creation Disabled

**As a user**, I want an option that stops "previous" from creating new empty workspaces, so I never accidentally open workspaces below what already exists on my monitor.

**Expected Behavior / Usage:** When the active workspace is the lowest-id workspace on the focused monitor and creating empty workspaces behind is disabled, the active id is returned unchanged. This holds whether the monitor has several workspaces or just one.

**Test Cases:** `rcb_tests/public_test_cases/feature8_previous_no_empty.json`

```json
{
    "cases": [
        {
            "input": {"current_id": 500, "monitor_ids": [500, 502], "occupied_ids": [500, 502], "previous": true, "no_empty_before": true},
            "expected_output": "id=500\n"
        },
        {
            "input": {"current_id": 500, "monitor_ids": [500], "occupied_ids": [500], "previous": true, "no_empty_before": true},
            "expected_output": "id=500\n"
        }
    ]
}
```

---

### Feature 9: Previous Wraps When Cycling

**As a user**, I want an option to cycle, so that pressing "previous" at the start of my monitor jumps to the end of my monitor instead of creating a new workspace.

**Expected Behavior / Usage:** When the active workspace is the lowest-id workspace on the focused monitor and cycling is enabled, the result is the highest-id workspace on the focused monitor. Cycling takes precedence over the disable-empty option, and a single-workspace monitor wraps onto itself.

**Test Cases:** `rcb_tests/public_test_cases/feature9_previous_cycle.json`

```json
{
    "cases": [
        {
            "input": {"current_id": 500, "monitor_ids": [500, 502, 504], "occupied_ids": [498, 500, 502, 504], "previous": true, "cycle": true},
            "expected_output": "id=504\n"
        },
        {
            "input": {"current_id": 500, "monitor_ids": [500, 502], "occupied_ids": [500, 502], "previous": true, "cycle": true},
            "expected_output": "id=502\n"
        }
    ]
}
```

---

### Feature 10: Previous Has No Room (Lower Boundary)

**As a user**, I want "previous" to be safe at the very bottom of the id range, so the desktop never tries to move below the lowest possible workspace.

**Expected Behavior / Usage:** When the active workspace is the lowest-id workspace on the focused monitor, empty-creation is allowed, but no lower free id exists — either because the active id is already the lowest valid id, or because every id below it is occupied down to the minimum — the active id is returned unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature10_previous_lower_boundary.json`

```json
{
    "cases": [
        {
            "input": {"current_id": 1, "monitor_ids": [1, 2], "occupied_ids": [1, 2], "previous": true},
            "expected_output": "id=1\n"
        },
        {
            "input": {"current_id": 3, "monitor_ids": [3, 4], "occupied_ids": [1, 2, 3, 4], "previous": true},
            "expected_output": "id=3\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the workspace-navigation computation described above. Its physical structure (single-file vs. multi-file) MUST align with the "Scale-Driven Code Organization" constraint. The core index logic must be decoupled from standard I/O and JSON parsing, and must expose, in an idiomatic way, the ability to compute the target workspace id from `(current_id, monitor_ids, occupied_ids)` together with the `previous`, `no_empty_before`, `no_empty_after`, and `cycle` options.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request object from standard input (fields as defined in "The Computation Contract"), invokes the core computation, and prints exactly one line, `id=<integer>`, to standard output. The adapter writes only this raw program output; any adapter-level failure (unreadable input, malformed JSON, or an inconsistent state) is rendered as a single neutral line of the form `error=<category>` rather than leaking runtime details.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory of case files (default `test_cases`). For each case it pipes the case's `input` object to the adapter and writes one file to `rcb_tests/stdout/<cases-dir-basename>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by the case-directory basename so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- apply the same deduplication and normalization rules used in the core ID parser
- use the standard test output convention for this directory
