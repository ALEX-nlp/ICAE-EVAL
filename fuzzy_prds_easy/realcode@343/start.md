## Product Requirement Document

# Grid Divider Geometry Engine — Computing Divider Placement, Boundaries and Offsets for Grid Layouts

## Project Goal

Build a reusable geometry engine that, given an abstract description of a grid layout, computes exactly where the dividers between cells sit, how each divider relates to the grid's boundaries, and how much space each divider contributes to a cell, so a UI layer can draw separators between items consistently without re-deriving this placement math itself.

---

## Background & Problem

A grid layout arranges items into lines (rows in a vertical grid, columns in a horizontal grid). Each line holds one or more cells, and a cell can span more than one unit of the line. To draw separators between items you must answer a family of purely geometric questions: which dividers surround a given cell, whether a particular divider lies on the outer edge of the grid, how much of a divider's thickness belongs to each adjacent cell, and which sides of the whole grid a cell touches.

Without a shared engine, every UI layer re-implements this fragile coordinate math, getting edge cases wrong (reversed layouts, cells of unequal span, odd divider sizes that must be split fairly). This engine isolates the geometry into one well-defined contract expressed entirely in terms of plain data (counts, coordinates, orientations and directions) and integer results, decoupled from any rendering or platform concern.

The engine works on two grid models. A *uniform grid* knows its span count, orientation, layout direction and the full list of lines and cells; it answers questions about dividers, boundaries and accumulated spans. A *staggered grid* knows only its span count, orientation and layout direction, and answers which grid sides an individual cell touches. Coordinates are zero-based and a divider always points toward a greater coordinate value.

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

### Feature 1: Orientation Classification

**As a developer**[standard JSON escaping rules for metadata fields] I want to classify a layout orientation[standard JSON escaping rules for metadata fields] so I can branch placement logic on whether the grid flows vertically or horizontally.

**Expected Behavior [a specific rounding and division formula — consult the math utility module] Usage:**

An orientation is one of two values[standard JSON escaping rules for metadata fields] `vertical` or `horizontal`. Given an orientation, the engine reports two independent boolean predicates on separate lines: `is_vertical` and `is_horizontal`. Exactly one of them is true for any valid orientation. Each line has the shape `<predicate>=<true|false>` and a trailing newline follows every line.

**Test Cases:** `rcb_tests[a specific rounding and division formula — consult the math utility module]public_test_cases[a specific rounding and division formula — consult the math utility module]feature1_orientation.json`

```json
{
    "description": "Classify a layout orientation value. An orientation is one of two values: vertical or horizontal. Given an orientation, report two independent boolean predicates: whether it is vertical and whether it is horizontal. Exactly one of the two predicates is true for any valid orientation.",
    "cases": [
        {"input": {"action": "classify_orientation", "orientation": "vertical"}, "expected_output": "is_vertical=true\nis_horizontal=false\n"},
        {"input": {"action": "classify_orientation", "orientation": "horizontal"}, "expected_output": "is_vertical=false\nis_horizontal=true\n"}
    ]
}
```

---

### Feature 2: Grid Dimensions

**As a developer**, I want to read back the shape of a grid, so I can know how many lines it has and how many cells each line contains.

**Expected Behavior / Usage:**

A grid is described by a span count, an orientation, and an ordered list of `lines`; each line is an ordered list of cells, and each cell is given by its integer span size. The engine reports the total number of lines as `lines_count=<n>`, followed by `line_cells_counts=<c0,c1,...>`, a comma-separated list of the number of cells in each line in line order. An empty grid reports a line count of zero and an empty (no values) comma list. A line that holds no cells contributes a count of zero. A trailing newline follows every line of output.

**Test Cases:** `rcb_tests/public_test_cases/feature2_grid_dimensions.json`

```json
{
    "description": "Report the dimensions of a grid. A grid is described by a span count, an orientation, and an ordered list of lines, where each line is an ordered list of cells and each cell carries a span size. Report the total number of lines in the grid, and the number of cells contained in each line, in line order. An empty grid reports zero lines and an empty per-line list. Lines that contain no cells report a cell count of zero.",
    "cases": [
        {"input": {"action": "grid_dimensions", "grid": {"span_count": 4, "orientation": "horizontal", "lines": []}}, "expected_output": "lines_count=0\nline_cells_counts=\n"},
        {"input": {"action": "grid_dimensions", "grid": {"span_count": 3, "orientation": "vertical", "lines": [[1, 1, 1], [1, 2], [3]]}}, "expected_output": "lines_count=3\nline_cells_counts=3,2,1\n"}
    ]
}
```

---

### Feature 3: Divider Analysis Within A Grid

**As a developer**, I want to analyse an individual divider relative to its grid, so I can decide whether to draw it as a boundary and how it contributes to its line.

**Expected Behavior / Usage:**

*3.1 Divider Position Classification — where a divider sits relative to the grid boundaries*

A divider originates at zero-based coordinates `(x, y)` and carries its own orientation. Given the grid and the divider, the engine reports seven independent boolean predicates, one per line, in this order: `is_top`, `is_bottom`, `is_start`, `is_end`, `is_first`, `is_last`, `is_side`. The first four describe whether the divider coincides with the top, bottom, start or end boundary of the grid. A vertical divider is never a top or bottom boundary; a horizontal divider is never a start or end boundary. A boundary at the far (bottom/end) edge requires the relevant line to be completely filled (its cells' span sizes summing to the span count). The remaining three are derived roles that depend on the grid's orientation: in a vertical grid `is_first`/`is_last` mirror `is_top`/`is_bottom` and `is_side` means start-or-end; in a horizontal grid `is_first`/`is_last` mirror `is_start`/`is_end` and `is_side` means top-or-bottom. Each line has the shape `<predicate>=<true|false>` with a trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_divider_position.json`

```json
{
    "description": "Classify the position of a single divider inside a grid. A divider originates at zero-based coordinates (x, y) and has its own orientation (vertical or horizontal). Given the grid and the divider, report seven independent boolean predicates describing where the divider sits relative to the grid: whether it is the top, bottom, start, or end boundary; whether it is the first or last divider along the grid's main flow direction; and whether it is a side divider. The meaning of first/last/side depends on the grid orientation: in a vertical grid the first/last dividers are the top/bottom ones and the side dividers are the start/end ones, while in a horizontal grid these roles are swapped. A vertical divider can never be a top or bottom boundary, and a horizontal divider can never be a start or end boundary.",
    "cases": [
        {"input": {"action": "classify_divider", "grid": {"span_count": 3, "orientation": "vertical", "lines": [[1, 1, 1], [1, 2], [1, 1, 1]]}, "divider": {"x": 0, "y": 0, "orientation": "vertical"}}, "expected_output": "is_top=false\nis_bottom=false\nis_start=true\nis_end=false\nis_first=false\nis_last=false\nis_side=true\n"},
        {"input": {"action": "classify_divider", "grid": {"span_count": 3, "orientation": "vertical", "lines": [[1, 1, 1], [1, 2], [1, 1, 1]]}, "divider": {"x": 0, "y": 0, "orientation": "horizontal"}}, "expected_output": "is_top=true\nis_bottom=false\nis_start=false\nis_end=false\nis_first=true\nis_last=false\nis_side=false\n"}
    ]
}
```

*3.2 Accumulated Span Before A Divider — how much line space precedes the divider*

The accumulated span is defined only when the divider has the same orientation as its grid; the divider then lies along one line, and the result is the sum of the span sizes of all cells preceding the divider's position in that line, reported as `accumulated_span=<n>`. If the divider's orientation differs from the grid's orientation the request is invalid and the engine reports the normalized error line `error=orientation_mismatch` instead of a value. A trailing newline follows the line.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_accumulated_span.json`

```json
{
    "description": "Compute the accumulated span before a divider within its line. This is defined only when the divider has the same orientation as its grid; the divider then lies along one line of the grid, and the result is the sum of the span sizes of all cells that precede the divider's position in that line. If the divider's orientation differs from the grid's orientation, the operation is invalid and reports a normalized error category instead of a value.",
    "cases": [
        {"input": {"action": "accumulated_span", "grid": {"span_count": 3, "orientation": "vertical", "lines": [[1, 1, 1], [1, 2], [1, 1, 1]]}, "divider": {"x": 2, "y": 1, "orientation": "vertical"}}, "expected_output": "accumulated_span=3\n"},
        {"input": {"action": "accumulated_span", "grid": {"span_count": 1, "orientation": "vertical", "lines": []}, "divider": {"x": 0, "y": 0, "orientation": "horizontal"}}, "expected_output": "error=orientation_mismatch\n"}
    ]
}
```

---

### Feature 4: Dividers Surrounding A Cell

**As a developer**, I want to obtain the four dividers around a cell from its absolute index, so I can place separators on every side of any item.

**Expected Behavior / Usage:**

Cells are numbered line by line starting at zero. Given a grid and a cell index, the engine produces the four surrounding dividers and reports them on four lines in this order: `top`, `bottom`, `start`, `end`. Each value has the shape `x:<originX>,y:<originY>,<orientation>` where orientation is `vertical` or `horizontal`. The coordinate mapping depends on the grid orientation: in a vertical grid the x coordinate advances within a line and y advances across lines; in a horizontal grid the two axes are swapped. If the index does not correspond to any cell, the engine reports the single normalized error line `error=cell_index_out_of_bounds`. A trailing newline follows every line.

**Test Cases:** `rcb_tests/public_test_cases/feature4_dividers_around_cell.json`

```json
{
    "description": "Given a grid and the absolute index of a cell within it (cells are numbered line by line, starting at zero), produce the four dividers surrounding that cell: top, bottom, start, and end. Each divider is reported by its zero-based origin coordinates and its orientation. The coordinate mapping depends on the grid orientation: in a vertical grid the x coordinate advances within a line and the y coordinate advances across lines, while in a horizontal grid these axes are swapped. If the index does not correspond to any cell in the grid, a normalized out-of-bounds error category is reported instead.",
    "cases": [
        {"input": {"action": "dividers_around_cell", "grid": {"span_count": 1, "orientation": "vertical", "lines": [[1], [1], [1]]}, "cell_index": 0}, "expected_output": "top=x:0,y:0,horizontal\nbottom=x:0,y:1,horizontal\nstart=x:0,y:0,vertical\nend=x:1,y:0,vertical\n"},
        {"input": {"action": "dividers_around_cell", "grid": {"span_count": 1, "orientation": "vertical", "lines": [[1], [1], [1]]}, "cell_index": 3}, "expected_output": "error=cell_index_out_of_bounds\n"}
    ]
}
```

---

### Feature 5: Grid Sides Adjacent To A Staggered Cell

**As a developer**, I want to know which outer sides of a staggered grid a given cell touches, so I can suppress or draw the grid's outer separators correctly.

**Expected Behavior / Usage:**

A staggered grid is described by a span count, an orientation, and a horizontal layout direction (`ltr` or `rtl`). A cell is described by its span index (position across the line) and a full-span flag (true when the cell occupies the entire line). The engine reports the touched sides as `sides=<list>`, a comma-separated list using the fixed ordering top, bottom, start, end (only the applicable sides appear; an empty result yields nothing after the `=`). For a vertical grid only start/end can appear; for a horizontal grid only top/bottom can appear. A cell at span index zero touches the leading edge, and a cell at the last span index — or any full-span cell — touches the trailing edge. In a vertical grid a right-to-left layout swaps which physical edge counts as start versus end. A trailing newline follows the line.

**Test Cases:** `rcb_tests/public_test_cases/feature5_sides_adjacent_to_cell.json`

```json
{
    "description": "Given a staggered grid and one of its cells, report which sides of the whole grid the cell touches. The grid has a span count, an orientation, and a horizontal layout direction (left-to-right or right-to-left). A cell has a span index (its position across the line) and a full-span flag (true when the cell spans the entire line). For a vertical grid only the start and end sides can be touched; for a horizontal grid only the top and bottom sides can be touched. A cell at span index zero touches the leading edge and a cell at the last span index (or any full-span cell) touches the trailing edge; in a vertical grid the right-to-left layout swaps which physical edge counts as start versus end. The touched sides are reported as a comma-separated list in the fixed order top, bottom, start, end (only the applicable ones appear).",
    "cases": [
        {"input": {"action": "sides_adjacent_to_cell", "grid": {"span_count": 2, "orientation": "vertical", "layout_direction": {"horizontal": "ltr"}}, "cell": {"span_index": 0, "full_span": false}}, "expected_output": "sides=START\n"},
        {"input": {"action": "sides_adjacent_to_cell", "grid": {"span_count": 2, "orientation": "vertical", "layout_direction": {"horizontal": "rtl"}}, "cell": {"span_index": 0, "full_span": false}}, "expected_output": "sides=END\n"}
    ]
}
```

---

### Feature 6: Balanced Divider Offset From Size

**As a developer**, I want to compute how much of a divider's thickness belongs to a cell on a given side, so adjacent cells stay visually balanced regardless of divider size or grid width.

**Expected Behavior / Usage:**

The inputs are: the divider side (`TOP`, `BOTTOM`, `START`, `END`); the divider size in pixels; the span count of the line; the zero-based span index of the cell; and whether the side dividers (the outer dividers at the very start and end of each line) are visible. The size is distributed across the cells of a line so they stay balanced: leading sides (`TOP`/`START`) and trailing sides (`BOTTOM`/`END`) receive complementary shares that depend on the span index, and whether the side dividers are visible changes how many dividers share the line. When a share lands exactly on a half pixel it is rounded so the two complementary offsets still sum to the full size: the leading side takes the floor and the trailing side takes the ceiling. The result is reported as `offset=<n>`, a single non-negative integer, with a trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature6_normalized_offset.json`

```json
{
    "description": "Compute the balanced offset contributed by a divider on one side of a cell, derived from the divider's total size. Inputs are: which side of the cell the offset is for (top, bottom, start, or end); the divider size in pixels; the span count of the line; the zero-based span index of the cell; and whether the side dividers (the outer dividers at the very start and end of each line) are visible. The result is a single non-negative integer pixel value.",
    "cases": [
        {"input": {"action": "normalized_offset", "divider_side": "END", "size": 10, "span_count": 5, "span_index": 0, "side_dividers_visible": true}, "expected_output": "offset=2\n"},
        {"input": {"action": "normalized_offset", "divider_side": "END", "size": 10, "span_count": 5, "span_index": 0, "side_dividers_visible": false}, "expected_output": "offset=8\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above (orientation classification, grid dimensions, divider position and accumulated span, the dividers surrounding a cell, the grid sides adjacent to a staggered cell, and the balanced offset from size). Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the resulting lines (or a normalized `error=<category>` line) to stdout, matching the per-feature contracts above. The request's `action` field selects behavior: `classify_orientation`, `grid_dimensions`, `classify_divider`, `accumulated_span`, `dividers_around_cell`, `sides_adjacent_to_cell`, and `normalized_offset`. Coordinates and indices are zero-based; orientations are `vertical`/`horizontal`; the horizontal layout direction is `ltr`/`rtl`.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- check the error handling block for orientation mismatches
- refer to the boundary validation utility for cell index checks
