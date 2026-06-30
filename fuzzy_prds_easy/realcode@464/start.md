## Product Requirement Document

# Annotation Box Placement Engine — Deterministic Layout of Axis And Side Callouts In A Bounded Viewport

## Project Goal

Build a deterministic 2D layout engine that places rectangular annotation boxes ("callouts") inside a bounded rectangular viewport. Each box points at a target location and belongs to a placement family (an axis callout pinned to a chart edge, or a side callout floating next to a data point). Given a set of boxes and a viewport, the engine decides the final top-left position of every box and the position of its connector anchor ("stem"), so that callouts stay inside the viewport, line up against the correct edges, avoid the active pointer where required, and do not overlap one another.

---

## Background & Problem

Interactive charts frequently need to show several callouts at once: one tied to the horizontal axis, one tied to the vertical axis, and one or more floating next to plotted points. Positioning each of these by hand leads to callouts that spill outside the drawing area, collide with each other, cover the very point they describe, or drift far away from the axis they belong to. The rules for "which side of the target", "how far from the target", "what to do when it does not fit" differ per family and interact with each other (a side callout must dodge an axis callout, an axis callout must give up space to make room for others).

This engine centralizes those rules. Callers describe each box abstractly — its family, the target point it refers to, the object radius around that point, and the box's measured size — plus the viewport and the current pointer location. The engine returns, for each box, a final placement coordinate and a stem anchor coordinate, applying a fixed, well-defined geometry so every caller gets identical, predictable results.

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

## Domain Model (shared by all features)

The coordinate system has its origin at the top-left; x grows to the right and y grows downward. The viewport is the axis-aligned rectangle `[0,0,500,500]` for every case below (left=0, top=0, right=500, bottom=500, center=(250,250)).

Each request is a scene: an optional pointer location (`cursor`, default `(0,0)`) and a list of `tooltips` (annotation boxes). Every box has: a string `key` identifier; a placement family `kind`; a `coord` target point it refers to; an `objectRadius` (the radius of the object around the target, used to offset the stem); and a measured `size` `[width,height]`. The families used here are `side` (a floating callout that attaches to the left or right of its target), `x_axis` (a callout pinned to the horizontal axis, placed below/above its target), and `y_axis` (a callout pinned to the vertical axis, placed left/right of its target).

Two stem lengths govern the gap between a box and its target: side callouts use a normal stem length of `12`; axis callouts use an axis stem length of `0`. A box is centered on its target along the free axis and offset by `stem + radius` along the attachment axis. Side callouts prefer the left of their target when that placement fits inside the viewport and does not intersect a restriction; otherwise they flip to the right.

The engine returns, for each placed box, three things rendered as text: the box `key`, its final top-left placement coordinate `tooltip=<x>,<y>`, and its stem anchor coordinate `stem=<x>,<y>`. All numbers are rounded to two decimals. The first output line is always `count=<number of placed boxes>`. Boxes are emitted in placement order: pinned families (axis, cursor) first, then side callouts.

---

## Core Features

### Feature 1: Horizontal-Axis Callout Placement

**As a developer**, I want callouts that belong to the horizontal axis to anchor against the axis line and reshape the space left for other callouts, so axis information stays attached to the axis while data callouts adapt around it.

**Expected Behavior / Usage:**

A horizontal-axis callout is centered horizontally over its target and attached along the vertical direction with the axis stem length. The relevant chart geometry for the cases below is: the axis line sits at y=470 (an axis-origin 30 units above the viewport bottom), the viewport bottom is at y=500. After the axis callout is placed, the vertical room available to other callouts is shrunk to the band above the axis callout, so a floating side callout pointing below the axis is lifted to rest just above it.

*1.1 Side callout lifted above a fitting axis callout — a small axis callout fits under the axis; the overlapping side callout is pushed up to sit above it.*

The axis callout (size `[27,27]`) fits in the 30-unit gap between the axis and the viewport bottom and is centered on its target. A side callout pointing at the bottom border is then constrained to the band above the axis callout, so its placement is lifted accordingly while its stem still anchors at the original target.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_x_axis_side_above_axis.json`

```json
{
    "description": "A side (horizontal) annotation box and a single horizontal-axis annotation are placed together. The horizontal-axis annotation points at a location on the bottom axis; the side box points at a target on the lower viewport border with a non-zero object radius. The axis box centers itself horizontally over its target and sits on the axis line, while the available vertical room for the side box is capped by the axis box, so the side box is lifted to rest just above the axis. The engine reports the count of placed boxes, then for each box its identifier, its top-left placement coordinate, and its stem anchor coordinate (all coordinates rounded to two decimals).",
    "cases": [
        {
            "input": {"tooltips": [
                {"key": "side", "kind": "side", "coord": [250, 500], "objectRadius": 40, "size": [80, 40]},
                {"key": "axis_x", "kind": "x_axis", "coord": [250, 470], "objectRadius": 0, "size": [27, 27]}
            ]},
            "expected_output": "count=2\nkey=axis_x\ntooltip=236.50,470.00\nstem=250.00,470.00\nkey=side\ntooltip=118.00,430.00\nstem=210.00,500.00\n"
        }
    ]
}
```

*1.2 Axis callout pinned to the border when it does not fit — an oversized axis callout cannot fit under the axis, so it is pinned to the bottom border and the side callout sits above its top edge.*

When the axis callout (size `[33,33]`) is too tall to fit in the gap between the axis and the viewport bottom, it is moved so its bottom rests on the lower border, and a side callout overlapping it is lifted to sit just above the callout's top edge.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_x_axis_pinned_to_border.json`

```json
{
    "description": "A side (horizontal) annotation box and a horizontal-axis annotation are placed together, but the axis box is sized too large to fit in the gap between the axis line and the lower viewport border. Because it cannot fit under the axis, the axis box is pinned so its bottom rests on the lower border, and the side box is then lifted to sit just above the top edge of the axis box. The engine reports the count of placed boxes, then for each box its identifier, its top-left placement coordinate, and its stem anchor coordinate (rounded to two decimals).",
    "cases": [
        {
            "input": {"tooltips": [
                {"key": "side", "kind": "side", "coord": [250, 450], "objectRadius": 40, "size": [80, 40]},
                {"key": "axis_x", "kind": "x_axis", "coord": [250, 470], "objectRadius": 0, "size": [33, 33]}
            ]},
            "expected_output": "count=2\nkey=axis_x\ntooltip=233.50,467.00\nstem=250.00,470.00\nkey=side\ntooltip=118.00,427.00\nstem=210.00,450.00\n"
        }
    ]
}
```

*1.3 At most one horizontal-axis callout — duplicate axis callouts are dropped, only the first survives.*

If more than one horizontal-axis callout is supplied, only the first is placed; any further horizontal-axis callouts are discarded. A side callout whose target is far from the axis is placed normally above its target.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_single_x_axis_only.json`

```json
{
    "description": "Two horizontal-axis annotations that point at the same axis location are supplied along with one side (horizontal) box. At most one horizontal-axis annotation may be shown, so the duplicate is dropped and only the first axis box survives. The side box, whose target is well away from the axis, is placed normally above its target. The engine reports the count of placed boxes (two, not three), then for each box its identifier, top-left placement coordinate, and stem anchor coordinate (rounded to two decimals).",
    "cases": [
        {
            "input": {"tooltips": [
                {"key": "side", "kind": "side", "coord": [150, 150], "objectRadius": 40, "size": [80, 40]},
                {"key": "axis_x", "kind": "x_axis", "coord": [250, 470], "objectRadius": 0, "size": [27, 27]},
                {"key": "axis_x", "kind": "x_axis", "coord": [250, 470], "objectRadius": 0, "size": [27, 27]}
            ]},
            "expected_output": "count=2\nkey=axis_x\ntooltip=236.50,470.00\nstem=250.00,470.00\nkey=side\ntooltip=18.00,130.00\nstem=110.00,150.00\n"
        }
    ]
}
```

*1.4 Horizontal-axis callout ignores the pointer — cursor avoidance does not apply to axis callouts.*

A horizontal-axis callout stays anchored on the axis below its target even when the pointer lies directly over it; unlike data callouts, it is not nudged away from the pointer.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_x_axis_ignores_cursor.json`

```json
{
    "description": "A single horizontal-axis annotation is placed while a cursor sits exactly on the axis line directly over the annotation's target. The axis box is anchored on the axis below its target and, unlike data boxes, must not be nudged upward to dodge the cursor: cursor avoidance is ignored for axis annotations. The engine reports the count of placed boxes, then the box identifier, its top-left placement coordinate, and its stem anchor coordinate (rounded to two decimals).",
    "cases": [
        {
            "input": {"cursor": [250, 470], "tooltips": [
                {"key": "axis_x", "kind": "x_axis", "coord": [250, 470], "objectRadius": 0, "size": [27, 27]}
            ]},
            "expected_output": "count=1\nkey=axis_x\ntooltip=236.50,470.00\nstem=250.00,470.00\n"
        }
    ]
}
```

---

### Feature 2: Vertical-Axis Callout Placement And Side-Callout Avoidance

**As a developer**, I want callouts that belong to the vertical axis to anchor against the left edge and act as obstacles that side callouts must route around, so axis information stays attached to the axis while floating callouts never overlap it.

**Expected Behavior / Usage:**

A vertical-axis callout is centered vertically on its target and attached along the horizontal direction with the axis stem length. For the cases below, the axis-origin x is 30. When the axis callout fits in the gap to the left of the axis it is aligned to the left of its target; when it does not fit it is pinned to the left viewport border. A side callout prefers the left of its own target, but if that left placement would intersect the placed vertical-axis callout it flips to the right of its target; if it does not intersect, it keeps its left placement.

*2.1 Oversized axis callout pinned to the border; overlapping side callout flips right.*

The vertical-axis callout (size `[33,33]`) does not fit to the left of the axis, so it is pinned to the left viewport border. A side callout whose vertical extent overlaps it would prefer the left of its target, but that intersects the axis callout, so it flips to the right.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_y_axis_not_fit_side_to_right.json`

```json
{
    "description": "A vertical-axis annotation that is too wide to fit between the axis line and the left viewport border is placed together with a side (horizontal) box whose vertical extent overlaps the axis box. Because the axis box does not fit on the preferred (left) side, it is pinned to the left viewport border. The side box, which would otherwise be placed to the left of its target, intersects the pinned axis box, so it is flipped to the right side of its target instead. The engine reports the count of placed boxes, then for each box its identifier, top-left placement coordinate, and stem anchor coordinate (rounded to two decimals).",
    "cases": [
        {
            "input": {"tooltips": [
                {"key": "side", "kind": "side", "coord": [150, 250], "objectRadius": 40, "size": [80, 40]},
                {"key": "axis_y", "kind": "y_axis", "coord": [30, 250], "objectRadius": 0, "size": [33, 33]}
            ]},
            "expected_output": "count=2\nkey=axis_y\ntooltip=0.00,233.50\nstem=30.00,250.00\nkey=side\ntooltip=202.00,230.00\nstem=190.00,250.00\n"
        }
    ]
}
```

*2.2 Fitting axis callout aligned to the left.*

A vertical-axis callout (size `[27,27]`) that fits in the gap is aligned to the left of its target, its right edge separated from the target by the axis stem, and centered vertically on the target.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_y_axis_fit_to_left.json`

```json
{
    "description": "A single vertical-axis annotation that fits in the gap between the axis line and the left viewport border is placed. With the preferred horizontal side being the left, the axis box is aligned to the left of its target (its right edge separated from the target by the axis stem), and it is centered vertically on its target. The engine reports the count of placed boxes, then the box identifier, its top-left placement coordinate, and its stem anchor coordinate (rounded to two decimals).",
    "cases": [
        {
            "input": {"tooltips": [
                {"key": "axis_y", "kind": "y_axis", "coord": [30, 250], "objectRadius": 0, "size": [27, 27]}
            ]},
            "expected_output": "count=1\nkey=axis_y\ntooltip=3.00,236.50\nstem=30.00,250.00\n"
        }
    ]
}
```

*2.3 Side callout overlapping a fitting axis callout flips right.*

When a fitting left-aligned vertical-axis callout is present and a side callout's vertical extent overlaps it, the side callout's preferred left placement intersects the axis callout, so it flips to the right of its target.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_side_intersects_y_axis_to_right.json`

```json
{
    "description": "A vertical-axis annotation that fits to the left of the axis is placed together with a side (horizontal) box whose vertical extent overlaps the axis box. The axis box is aligned to the left of its target as usual. The side box would prefer the left of its target, but that placement intersects the axis box, so it is flipped to the right side of its target. The engine reports the count of placed boxes, then for each box its identifier, top-left placement coordinate, and stem anchor coordinate (rounded to two decimals).",
    "cases": [
        {
            "input": {"tooltips": [
                {"key": "side", "kind": "side", "coord": [150, 250], "objectRadius": 40, "size": [80, 40]},
                {"key": "axis_y", "kind": "y_axis", "coord": [30, 250], "objectRadius": 0, "size": [27, 27]}
            ]},
            "expected_output": "count=2\nkey=axis_y\ntooltip=3.00,236.50\nstem=30.00,250.00\nkey=side\ntooltip=202.00,230.00\nstem=190.00,250.00\n"
        }
    ]
}
```

*2.4 Non-overlapping side callout keeps its left placement.*

When the side callout's target is far enough from the axis callout that their vertical extents do not overlap, the side callout keeps its preferred left placement relative to its own target.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_side_not_intersect_y_axis_to_left.json`

```json
{
    "description": "A vertical-axis annotation that fits to the left of the axis is placed together with a side (horizontal) box whose target sits near the top of the viewport, so the side box's vertical extent does NOT overlap the axis box. The axis box is aligned to the left of its target. Because there is no intersection, the side box keeps its preferred left placement relative to its own target. The engine reports the count of placed boxes, then for each box its identifier, top-left placement coordinate, and stem anchor coordinate (rounded to two decimals).",
    "cases": [
        {
            "input": {"tooltips": [
                {"key": "side", "kind": "side", "coord": [150, 0], "objectRadius": 40, "size": [80, 40]},
                {"key": "axis_y", "kind": "y_axis", "coord": [30, 250], "objectRadius": 0, "size": [27, 27]}
            ]},
            "expected_output": "count=2\nkey=axis_y\ntooltip=3.00,236.50\nstem=30.00,250.00\nkey=side\ntooltip=18.00,0.00\nstem=110.00,0.00\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the placement geometry: centering along the free axis, offsetting by stem plus object radius along the attachment axis, fitting/pinning axis callouts against viewport edges, shrinking the available band after an axis callout is placed, dropping duplicate axis callouts, ignoring the pointer for axis callouts, and flipping side callouts from left to right when they would intersect an axis callout. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON scene from stdin and prints the result to stdout, matching the per-feature contracts above. The scene carries an optional `cursor` and a list of `tooltips`, each with `key`, `kind` (`side`, `x_axis`, `y_axis`, `vertical`, or `cursor`), `coord`, `objectRadius`, and `size`. The output begins with `count=<n>` and then, per placed box in placement order, three lines `key=<id>`, `tooltip=<x>,<y>`, `stem=<x>,<y>` with all numbers rounded to two decimals.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- apply the same sizing convention used in the vertical_axis_calc module
- format each coordinate block following the template from the coordinate_encoder utility
