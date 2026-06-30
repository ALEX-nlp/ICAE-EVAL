## Product Requirement Document

# Deterministic Front-End Utility Toolkit — Version, Layout, Placement & Data Helpers

## Project Goal

Build a small, dependency-light toolkit of pure utility functions that a desktop/web application can reuse for everyday chores: normalizing and sorting release identifiers, indexing release records, reading and writing nested object values by path, building and flattening split-pane layout trees, computing on-screen placement for floating UI, and ordering dialog buttons by platform convention. Each function takes plain data in and returns plain data out, so developers can compose them freely without pulling in heavyweight frameworks.

---

## Background & Problem

Applications repeatedly need the same handful of deterministic helpers: trimming a leading prefix letter from a version string, ordering versions newest-first while tolerating non-version labels, turning a list into a keyed lookup, navigating nested configuration objects, arranging a set of editor/preview panes into a balanced split layout, deciding where a tooltip should sit so it stays on screen, and respecting the platform-specific position of a dialog's cancel button.

Without a shared toolkit, every screen re-implements these rules slightly differently, producing inconsistent ordering, off-screen popovers, and platform-incorrect dialogs. This toolkit fixes the contracts once: each helper has a precise, testable input→output behavior that is independent of any UI framework, so the same logic can be unit-tested in isolation and reused everywhere.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

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

### Feature 1: Normalize A Version Identifier

**As a developer**, I want to strip an optional leading prefix letter from a version string, so I can compare and key versions consistently regardless of how they were written.

**Expected Behavior / Usage:**

The input carries a `version` string. If the string starts with the lowercase prefix letter `v`, the function returns the string with that first character removed; otherwise it returns the string unchanged. The result is printed followed by a trailing newline. A missing version is treated as an empty string.

**Test Cases:** `rcb_tests/public_test_cases/feature1_normalize_version.json`

```json
{
    "description": "Strip an optional single leading lowercase version-prefix letter from a release identifier. If the identifier begins with that prefix letter, the function returns the identifier with that first character removed; otherwise it returns the identifier unchanged. The output is the resulting string followed by a trailing newline.",
    "cases": [
        {"input": {"op": "normalize_version", "version": "v3.0.0"}, "expected_output": "3.0.0[a specific trailing character]"},
        {"input": {"op": "normalize_version", "version": "3.0.0"}, "expected_output": "3.0.0[a specific trailing character]"}
    ]
}
```

---

### Feature 2: Conditionally Pluralize A Word

**As a developer**, I want a word pluralized only when a collection has more than one item, so my UI text reads naturally for both singular and plural counts.

**Expected Behavior / Usage:**

The input carries a `word` and an `items` collection. When the collection holds more than one item, the word is returned with a trailing plural suffix `s` appended; for an empty collection or a single item, the word is returned unchanged. The result is printed followed by a trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature2_pluralize.json`

```json
{
    "description": "Given a base word and a collection of items, return the word made plural by appending the plural suffix only when the collection holds more than one item; for an empty collection or a single item the base word is returned unchanged. The output is the resulting word followed by a trailing newline.",
    "cases": [
        {"input": {"op": "pluralize", "word": "version", "items": [true, true]}, "expected_output": "versions[a specific trailing character]"},
        {"input": {"op": "pluralize", "word": "version", "items": [true]}, "expected_output": "version[a specific trailing character]"}
    ]
}
```

---

### Feature 3: Index Release Records By Normalized Version

**As a developer**, I want to turn a list of release records into a map keyed by normalized version, so I can look up any release in constant time.

**Expected Behavior / Usage:**

The input carries a `versions` list, where each element is a record containing at least a `version` field. The function produces an object whose keys are the normalized version strings (see Feature 1) and whose values are the original, unmodified records. Keys are inserted in the order the records were supplied. The result is serialized as compact JSON (no extra whitespace) and printed followed by a trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature3_index_versions.json`

```json
{
    "description": "Convert a list of release records into a lookup object keyed by each record's normalized version string (the version with any single leading prefix letter removed). Each entry maps the normalized key to the original, unmodified record. Keys appear in the order the records were supplied. The output is the resulting object serialized as compact JSON followed by a trailing newline.",
    "cases": [
        {"input": {"op": "index_versions", "versions": [{"version": "v1.0.0"}, {"version": "v2.0.0"}, {"version": "3.0.0"}]}, "expected_output": "{\"1.0.0\":{\"version\":\"v1.0.0\"},\"2.0.0\":{\"version\":\"v2.0.0\"},\"3.0.0\":{\"version\":\"3.0.0\"}}[a specific trailing character]"}
    ]
}
```

---

### Feature 4: Sort Version Keys Newest-First

**As a developer**, I want a set of version keys sorted from newest to oldest while still tolerating non-version labels, so my release picker always shows the latest first without crashing on odd entries.

**Expected Behavior / Usage:**

The input carries a `versions` record (an object whose keys are version strings). The function returns those keys sorted by the following rule: keys that are valid semantic versions are ordered from highest to lowest; any key that is not a valid semantic version is treated as lower than every valid version and is grouped ahead of the valid ones, with such invalid keys ordered among themselves alphabetically (ascending). The sorted keys are printed one per line, each line terminated by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature4_sort_versions.json`

```json
{
    "description": "Sort the keys of a record of release entries and return them in order. Keys that are valid semantic versions are ordered from highest to lowest. Keys that are not valid semantic versions are considered lower than any valid version and are placed first, ordered among themselves alphabetically. The output is the sorted keys, one per line, each terminated by a newline.",
    "cases": [
        {"input": {"op": "sort_versions", "versions": {"1.0.0": {"version": "v1.0.0"}, "3.0.0": {"version": "v3.0.0"}, "2.0.0": {"version": "v2.0.0"}}}, "expected_output": "3.0.0[a specific trailing character]2.0.0[a specific trailing character]1.0.0[a specific trailing character]"},
        {"input": {"op": "sort_versions", "versions": {"moreGarbage": {"version": "moreGarbage"}, "1.0.0": {"version": "v1.0.0"}, "3.0.0": {"version": "v3.0.0"}, "garbage": {"version": "garbage"}}}, "expected_output": "garbage[a specific trailing character]moreGarbage[a specific trailing character]3.0.0[a specific trailing character]1.0.0[a specific trailing character]"}
    ]
}
```

---

### Feature 5: Navigate Nested Objects By Dot-Path

**As a developer**, I want to read and write deeply nested object values using a single dotted string, so I can manipulate configuration without hand-writing nested accessors.

**Expected Behavior / Usage:**

*5.1 Read A Value At A Path — return the value found at a dot-delimited path*

The input carries a `path` string and an `object`. The path is split on the dot character and each segment is followed in turn, descending one level per segment; the value located at the end of the path is returned. The result is serialized as compact JSON and printed followed by a trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_get_at_path.json`

```json
{
    "description": "Read a nested value out of an object using a dot-delimited path. The path is split on dots and each segment is followed in turn, descending one level per segment, and the value found at the end of the path is returned. The output is that value serialized as compact JSON followed by a trailing newline.",
    "cases": [
        {"input": {"op": "get_at_path", "path": "a.b.c", "object": {"a": {"b": {"c": true}}}}, "expected_output": "true[a specific trailing character]"},
        {"input": {"op": "get_at_path", "path": "a", "object": {"a": 3}}, "expected_output": "3[a specific trailing character]"}
    ]
}
```

*5.2 Write A Value At A Path — assign a value at a dot-delimited path, mutating the object in place*

The input carries a `path` string, an `object`, and a `value`. The path is split on the dot character; every segment except the last is followed to descend into the object, and the supplied value is assigned at the final segment, mutating the existing object in place. The whole mutated object is serialized as compact JSON and printed followed by a trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_set_at_path.json`

```json
{
    "description": "Write a value into a nested object at a location named by a dot-delimited path. The path is split on dots; all but the final segment are followed to descend into the object, and the supplied value is assigned at the final segment, mutating the existing object in place. The output is the whole mutated object serialized as compact JSON followed by a trailing newline.",
    "cases": [
        {"input": {"op": "set_at_path", "path": "a.b.c", "object": {"a": {"b": {"c": true}}}, "value": 3}, "expected_output": "{\"a\":{\"b\":{\"c\":3}}}[a specific trailing character]"}
    ]
}
```

---

### Feature 6: Split-Pane Layout Trees

**As a developer**, I want to build a balanced split-pane layout from a list of panes and later recover the panes from such a layout, so I can lay out an arbitrary number of panes and serialize/restore the arrangement.

**Expected Behavior / Usage:**

*6.1 Build A Layout Tree — turn an ordered list of pane identifiers into a balanced split tree*

The input carries a `panes` list of pane identifiers (strings). With exactly one pane, the result is just that pane identifier as a bare leaf (a string). With more than one pane, the list is split into a first group of the first half of the panes (rounding the count down) and a second group of the remaining panes; the result is a node object with a `direction`, a `first` child, and a `second` child, where each child is built recursively from its group. The topmost node uses the `row` direction; every nested node uses the `column` direction. An optional `direction` field overrides the topmost node's direction. The tree is serialized as compact JSON and printed followed by a trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_create_layout.json`

```json
{
    "description": "Build a binary split-pane layout tree from an ordered list of pane identifiers. A single pane yields just that pane identifier as a bare leaf. For more than one pane, the list is divided into a first group containing the first half of the panes (rounding down) and a second group containing the remaining panes, and a node is produced with a split direction and two child slots, each child built recursively from its group. The topmost node uses the row direction; every nested node uses the column direction. The output is the resulting tree serialized as compact JSON followed by a trailing newline.",
    "cases": [
        {"input": {"op": "create_layout", "panes": ["main"]}, "expected_output": "\"main\"[a specific trailing character]"},
        {"input": {"op": "create_layout", "panes": ["main", "renderer", "html"]}, "expected_output": "{\"direction\":\"row\",\"first\":\"main\",\"second\":{\"direction\":\"column\",\"first\":\"renderer\",\"second\":\"html\"}}[a specific trailing character]"}
    ]
}
```

*6.2 Flatten A Layout Tree — list the visible panes in left-to-right order*

The input carries an `arrangement` that is either null, a bare leaf (a single pane identifier string), or a split node with `first` and `second` children. The function returns the panes contained in the tree as an ordered list: a null tree yields an empty list, a bare leaf yields a single-element list, and a split node is traversed first-child-before-second-child, recursively, so panes come out in left-to-right order. The list is serialized as a compact JSON array and printed followed by a trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_visible_panes.json`

```json
{
    "description": "Flatten a split-pane layout tree into the ordered list of visible pane identifiers it contains. A null tree yields an empty list. A bare leaf (a single pane identifier) yields a one-element list. A split node is traversed by visiting its first child before its second child, descending recursively, so the panes come out in left-to-right order. The output is the resulting list serialized as a compact JSON array followed by a trailing newline.",
    "cases": [
        {"input": {"op": "visible_panes", "arrangement": null}, "expected_output": "[][a specific trailing character]"},
        {"input": {"op": "visible_panes", "arrangement": {"direction": "row", "first": {"direction": "column", "first": "main", "second": "renderer"}, "second": "html"}}, "expected_output": "[\"main\",\"renderer\",\"html\"][a specific trailing character]"}
    ]
}
```

---

### Feature 7: On-Screen Placement Helpers

**As a developer**, I want to invert a directional placement and to compute a viewport-aware placement for a floating element, so my tooltips and popovers point the right way and stay on screen.

**Expected Behavior / Usage:**

*7.1 Invert A Direction — return the opposite of a placement direction*

The input carries a `position` that is one of four directions. The directions form two opposite pairs — `left`/`right` and `top`/`bottom` — and the function returns the opposite of the given direction. Any unrecognized value falls back to `top`. The result is printed followed by a trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_invert_position.json`

```json
{
    "description": "Invert a directional placement. The four directions form two opposite pairs: left and right are opposites, and top and bottom are opposites. Given one of these four directions, the function returns its opposite. Any unrecognized value falls back to the top direction. The output is the resulting direction name followed by a trailing newline.",
    "cases": [
        {"input": {"op": "invert_position", "position": "right"}, "expected_output": "left[a specific trailing character]"},
        {"input": {"op": "invert_position", "position": "xyz"}, "expected_output": "top[a specific trailing character]"}
    ]
}
```

*7.2 Place A Floating Element Near A Target — choose the first on-screen placement among candidates*

The input carries a `target` rectangle (`left`, `top`, `width`, `height`), the floating element's `size` (`width`, `height`), an optional `margin` (default 10), the current `viewport` (`innerWidth`, `innerHeight`), and a `platform` identifier. The function evaluates candidate placements in order and returns the first one that fits within the viewport, otherwise a final fallback. Candidate 1 (to the right): `left = target.left + target.width + margin`, `top = target.top`, type `right`. Candidate 2 (to the left): `left = target.left - margin - size.width`, `top = target.top`, type `left`. Candidate 3 (centered below): `left = target.left + target.width/2 - size.width/2`, `top = target.top + target.height + margin`, type `bottom`. Fallback: the same centered `left`, `top = target.top + size.height - margin`, type `bottom`. A candidate fits when `left >= 0`, `top >= 0`, `left + size.width` does not exceed `viewport.innerWidth` plus a horizontal tolerance of [a specific percentage tolerance used in boundary calculations] of `size.width`, and `top + size.height` does not exceed `viewport.innerHeight` plus a vertical tolerance of [a specific percentage tolerance used in boundary calculations] of `size.height`. On the macOS platform only, the `top` of the right and left candidates is additionally raised (decreased) by one and a half margins. The chosen placement — an object with `left`, `top`, and `type` — is serialized as compact JSON and printed followed by a trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_position_for_rect.json`

```json
{
    "description": "Compute a placement for a floating element (such as a tooltip or popover) relative to a target rectangle, keeping it within the visible viewport. Inputs are the target rectangle (its left, top, width, height), the floating element's size (width, height), an optional margin (default 10), the current viewport (its inner width and height), and the platform identifier. The function tries candidate placements in order and returns the first that fits, otherwise a fallback. Candidate 1 (to the right): left = target.left + target.width + margin, top = target.top, type 'right'. Candidate 2 (to the left): left = target.left - margin - size.width, top = target.top, type 'left'. Candidate 3 (centered below): left = target.left + target.width/2 - size.width/2, top = target.top + target.height + margin, type 'bottom'. Fallback: same centered left, top = target.top + size.height - margin, type 'bottom'. A candidate fits when left >= 0, top >= 0, left + size.width does not exceed the viewport inner width plus a horizontal tolerance of [a specific percentage tolerance used in boundary calculations] of size.width, and top + size.height does not exceed the viewport inner height plus a vertical tolerance of [a specific percentage tolerance used in boundary calculations] of size.height. On the macOS platform only, the top of the right and left candidates is additionally raised by one and a half margins. The output is the chosen placement, an object with left, top and type, serialized as compact JSON followed by a trailing newline.",
    "cases": [
        {"input": {"op": "position_for_rect", "platform": "win32", "viewport": {"innerWidth": 1024, "innerHeight": 768}, "target": {"left": 50, "top": 100, "width": 175, "height": 50}, "size": {"width": 200, "height": 150}}, "expected_output": "{\"left\":235,\"top\":100,\"type\":\"right\"}[a specific trailing character]"},
        {"input": {"op": "position_for_rect", "platform": "darwin", "viewport": {"innerWidth": 1024, "innerHeight": 768}, "target": {"left": 50, "top": 100, "width": 175, "height": 50}, "size": {"width": 200, "height": 150}}, "expected_output": "{\"left\":235,\"top\":85,\"type\":\"right\"}[a specific trailing character]"}
    ]
}
```

---

### Feature 8: Order Dialog Buttons By Platform Convention

**As a developer**, I want a dialog's buttons reordered to match the host platform's convention, so the cancel button lands where users expect it on each operating system.

**Expected Behavior / Usage:**

The input carries a `buttons` list (the first entry is treated as the [the specific first button title that is moved] button) and a `platform` identifier. On the macOS platform, when there is more than one button, the dismiss button is moved from the front to the end while the remaining buttons keep their relative order. On every other platform, and whenever there is at most one button, the list is returned unchanged. The resulting list is serialized as compact JSON and printed followed by a trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature8_sort_buttons.json`

```json
{
    "description": "Order a list of dialog buttons according to the host platform's convention, where the first button in the input is treated as the [the specific first button title that is moved] button. On the macOS platform, when there is more than one button, the dismiss button is moved from the front to the end while the remaining buttons keep their relative order; on every other platform, and whenever there is at most one button, the list is returned unchanged. The output is the resulting list of buttons serialized as compact JSON followed by a trailing newline.",
    "cases": [
        {"input": {"op": "sort_buttons", "platform": "win32", "buttons": [{"type": "close"}, {"type": "confirm"}]}, "expected_output": "[{\"type\":\"close\"},{\"type\":\"confirm\"}][a specific trailing character]"},
        {"input": {"op": "sort_buttons", "platform": "darwin", "buttons": [{"type": "close"}, {"type": "confirm"}]}, "expected_output": "[{\"type\":\"confirm\"},{\"type\":\"close\"}][a specific trailing character]"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the utility functions described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, selects the operation via the request's `op` field, invokes the appropriate core function, and prints the result to stdout, matching the per-feature contracts above. Supported `op` values are: `normalize_version`, `pluralize`, `index_versions`, `sort_versions`, `get_at_path`, `set_at_path`, `create_layout`, `visible_panes`, `invert_position`, `position_for_rect`, and `sort_buttons`. Object and array results are rendered as compact JSON (no inserted whitespace, keys in insertion order). An unrecognized `op` prints a neutral error line `error=unknown_op`.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- format output as a newline-serialized list
