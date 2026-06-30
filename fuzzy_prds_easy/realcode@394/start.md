## Product Requirement Document

# Text Layout Engine - Rich Unicode Shaping and Measurement

## Project Goal

Build a rich text layout library that allows developers to shape Unicode text, place inline replacement objects, measure intrinsic content widths, wrap paragraphs, align lines, inspect clusters, and control line metrics without hand-writing font selection, bidirectional ordering, glyph clustering, or line-breaking logic.

---

## Background & Problem

Without this library/tool, developers are forced to combine font discovery, Unicode segmentation, bidirectional ordering, glyph shaping, inline object placement, wrapping, alignment, and metric calculations manually. This leads to inconsistent text rendering, fragile cursor behavior, incorrect handling of mixed-direction text, and repetitive layout code.

With this library/tool, applications can submit styled text and embedded boxes to a single layout engine, then inspect deterministic line, run, cluster, and metric data for rendering, editing, hit testing, and responsive layout decisions.

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

### Feature 1: Line Layout Summary

**As a developer**, I want to shape plain Unicode text into line boxes, so I can inspect paragraph direction, dimensions, line ranges, break reasons, and run direction after explicit or implicit line breaking.

**Expected Behavior / Usage:**

The adapter input is a JSON object with `action` set to `layout_summary`, a `text` string, and optional `width`, `alignment`, and line-height fields. The output begins with paragraph direction, line count, layout width, full width, and height, followed by one line record per shaped line and one run record per text run. Explicit newline characters create `break:Explicit` records; the final line uses `break:None` unless a wrapping rule creates another break.

**Test Cases:** `rcb_tests/public_test_cases/feature1_multiline_layout.json`

```json
{
    "description": "These cases exercise an externally observable text layout behavior derived from the original tests.",
    "cases": [
        {
            "input": {
                "action": "layout_summary",
                "text": "Hello world!\nLine 2\nLine 4",
                "alignment": "start"
            },
            "expected_output": "direction=ltr\nline_count=3\nwidth=84.32\nfull_width=84.32\nheight=48.00\nline[0]=range:0..13 advance:84.32 trailing:0.00 offset:0.00 baseline:13.00 break:Explicit items:1\nrun[0.0]=range:0..13 dir:ltr clusters:13 advance:84.32\nline[1]=range:13..20 advance:42.74 trailing:0.00 offset:0.00 baseline:29.00 break:Explicit items:1\nrun[1.0]=range:13..20 dir:ltr clusters:7 advance:42.74\nline[2]=range:20..26 advance:42.74 trailing:0.00 offset:0.00 baseline:45.00 break:None items:1\nrun[2.0]=range:20..26 dir:ltr clusters:6 advance:42.74\n"
        }
    ]
}
```

---

### Feature 2: Inline Replacement Boxes

**As a developer**, I want to place non-text rectangular items inside flowing text, so I can reserve space for embedded objects while preserving normal line layout.

**Expected Behavior / Usage:**

The adapter input is a JSON object with `action` set to `inline_boxes`, a `text` string, and an `inline_boxes` array. Each box contains an id, byte index, width, and height. The output reports the total line count and then emits glyph-run and box records in visual line order. Box records include line index, id, x/y position, width, and height, proving that replacement boxes are laid out by the text engine rather than returned independently.

**Test Cases:** `rcb_tests/public_test_cases/feature2_inline_boxes.json`

```json
{
    "description": "These cases exercise an externally observable text layout behavior derived from the original tests.",
    "cases": [
        {
            "input": {
                "action": "inline_boxes",
                "text": "ABC",
                "inline_boxes": [
                    {
                        "id": 0,
                        "index": 1,
                        "width": 10.0,
                        "height": 10.0
                    },
                    {
                        "id": 1,
                        "index": 1,
                        "width": 100.0,
                        "height": 10.0
                    },
                    {
                        "id": 2,
                        "index": 2,
                        "width": 100.0,
                        "height": 10.0
                    }
                ],
                "width": 100.0,
                "alignment": "start"
            },
            "expected_output": "line_count=5\nglyph_run[line=0]=range:0..1 dir:ltr offset:0.00 baseline:13.00 advance:10.44 glyphs:1\nbox[line=0]=id:0 x:10.44 y:3.00 width:10.00 height:10.00\nbox[line=1]=id:1 x:0.00 y:16.00 width:100.00 height:10.00\nglyph_run[line=2]=range:1..2 dir:ltr offset:0.00 baseline:39.00 advance:9.96 glyphs:1\nbox[line=3]=id:2 x:0.00 y:42.00 width:100.00 height:10.00\nglyph_run[line=4]=range:2..3 dir:ltr offset:0.00 baseline:65.00 advance:10.41 glyphs:1\n"
        }
    ]
}
```

---

### Feature 3: Intrinsic Content Widths

**As a developer**, I want to measure the minimum and maximum widths required by text and inline objects, so I can choose wrapping constraints before final layout.

**Expected Behavior / Usage:**

The adapter input is a JSON object with `action` set to `content_widths`, a `text` string, and optional inline boxes or wrapping controls. The output contains `min_width` and `max_width` numeric fields rounded to two decimals. Long unbroken words, ordinary word separators, explicit line breaks, and replacement boxes all contribute to these intrinsic width values.

**Test Cases:** `rcb_tests/public_test_cases/feature3_content_widths.json`

```json
{
    "description": "These cases exercise an externally observable text layout behavior derived from the original tests.",
    "cases": [
        {
            "input": {
                "action": "content_widths",
                "text": "Hello world!\nLonger line with a looooooooong word."
            },
            "expected_output": "min_width=103.81\nmax_width=276.41\n"
        }
    ]
}
```

---

### Feature 4: Wrapping Controls

**As a developer**, I want to control soft wrapping, emergency wrapping, and character-level word breaking, so I can match different text wrapping policies under a fixed width.

**Expected Behavior / Usage:**

The adapter input is a JSON object with `action` set to `wrap_summary`, a `text` string, a numeric `width`, and optional `text_wrap_mode`, `overflow_wrap`, or `word_break` fields. The output contains the line count followed by one record per line with the source text byte range, advance, and break reason. Normal wrapping uses regular soft opportunities; disabling soft wrapping keeps overflowing text on one line; emergency and character-level policies introduce additional break opportunities.

**Test Cases:** `rcb_tests/public_test_cases/feature4_wrapping_controls.json`

```json
{
    "description": "These cases exercise an externally observable text layout behavior derived from the original tests.",
    "cases": [
        {
            "input": {
                "action": "wrap_summary",
                "text": "Most words are short. But Antidisestablishmentarianism is long and needs to wrap.",
                "width": 120.0
            },
            "expected_output": "line_count=5\nline[0]=range:0..15 advance:114.59 break:Regular\nline[1]=range:15..26 advance:73.36 break:Regular\nline[2]=range:26..55 advance:216.20 break:Regular\nline[3]=range:55..67 advance:81.38 break:Regular\nline[4]=range:67..81 advance:104.19 break:None\n"
        }
    ]
}
```

---

### Feature 5: Line Alignment

**As a developer**, I want to align shaped lines inside a supplied container, so I can position start, end, center, and justified text consistently with paragraph direction.

**Expected Behavior / Usage:**

The adapter input is a JSON object with `action` set to `layout_summary`, a `text` string, a numeric `width`, and an `alignment` value. The output uses the same layout summary format as the base line-layout feature, and the per-line `offset` field is the observable alignment result. Center alignment offsets each line by half the remaining width, direction-aware end alignment respects paragraph direction, and justification can expand eligible spaces on non-final lines.

**Test Cases:** `rcb_tests/public_test_cases/feature5_alignment.json`

```json
{
    "description": "These cases exercise an externally observable text layout behavior derived from the original tests.",
    "cases": [
        {
            "input": {
                "action": "layout_summary",
                "text": "Hello world!\nLine 2\nLine 4",
                "width": 200.0,
                "alignment": "center"
            },
            "expected_output": "direction=ltr\nline_count=3\nwidth=84.32\nfull_width=84.32\nheight=48.00\nline[0]=range:0..13 advance:84.32 trailing:0.00 offset:57.84 baseline:13.00 break:Explicit items:1\nrun[0.0]=range:0..13 dir:ltr clusters:13 advance:84.32\nline[1]=range:13..20 advance:42.74 trailing:0.00 offset:78.63 baseline:29.00 break:Explicit items:1\nrun[1.0]=range:13..20 dir:ltr clusters:7 advance:42.74\nline[2]=range:20..26 advance:42.74 trailing:0.00 offset:78.63 baseline:45.00 break:None items:1\nrun[2.0]=range:20..26 dir:ltr clusters:6 advance:42.74\n"
        }
    ]
}
```

---

### Feature 6: Cluster Inspection

**As a developer**, I want to inspect grapheme clusters and line-boundary flags, so I can implement hit testing, cursor movement, and text selection on top of shaped text.

**Expected Behavior / Usage:**

The adapter input is a JSON object with `action` set to `cluster_flags`, a `text` string, and optional width or style controls. The output emits one record per cluster in logical order with the source slice, byte range, direction, word-boundary flag, soft and hard line-break flags, final line-break reason when applicable, start/end-of-line flags, ligature flags, glyph count, and advance. This makes Unicode boundaries, bidirectional clusters, explicit newlines, and ligature decomposition externally observable.

**Test Cases:** `rcb_tests/public_test_cases/feature6_cluster_flags.json`

```json
{
    "description": "These cases exercise an externally observable text layout behavior derived from the original tests.",
    "cases": [
        {
            "input": {
                "action": "cluster_flags",
                "text": "AB\nC",
                "width": 200.0
            },
            "expected_output": "cluster[0.0.0]=text:\"A\" range:0..1 dir:ltr word_boundary:true soft_break:false hard_break:false line_break:None start:true end:false ligature_start:false ligature_continuation:false glyphs:1 advance:10.44\ncluster[0.0.1]=text:\"B\" range:1..2 dir:ltr word_boundary:false soft_break:false hard_break:false line_break:None start:false end:false ligature_start:false ligature_continuation:false glyphs:1 advance:9.96\ncluster[0.0.2]=text:\"\\n\" range:2..3 dir:ltr word_boundary:true soft_break:false hard_break:true line_break:Some(Explicit) start:false end:true ligature_start:false ligature_continuation:false glyphs:0 advance:0.00\ncluster[1.0.0]=text:\"C\" range:3..4 dir:ltr word_boundary:true soft_break:false hard_break:false line_break:Some(None) start:true end:true ligature_start:false ligature_continuation:false glyphs:1 advance:10.41\n"
        }
    ]
}
```

---

### Feature 7: Line Height Policies

**As a developer**, I want to choose how line boxes are sized, so multi-line text can use absolute, font-size-relative, or font-metric-relative spacing.

**Expected Behavior / Usage:**

The adapter input is a JSON object with `action` set to `layout_summary`, a `text` string, and a `line_height` object containing a `mode` and numeric `value`. The output reports total height and each line’s baseline and metrics through the standard layout summary. Absolute values produce fixed line boxes, font-size-relative values scale from the active font size, and metric-relative values use the selected font metrics.

**Test Cases:** `rcb_tests/public_test_cases/feature7_line_height.json`

```json
{
    "description": "These cases exercise an externally observable text layout behavior derived from the original tests.",
    "cases": [
        {
            "input": {
                "action": "layout_summary",
                "text": "Hello\nWorld",
                "line_height": {
                    "mode": "absolute",
                    "value": 20.0
                }
            },
            "expected_output": "direction=ltr\nline_count=2\nwidth=41.40\nfull_width=41.40\nheight=40.00\nline[0]=range:0..6 advance:36.77 trailing:0.00 offset:0.00 baseline:15.00 break:Explicit items:1\nrun[0.0]=range:0..6 dir:ltr clusters:6 advance:36.77\nline[1]=range:6..11 advance:41.40 trailing:0.00 offset:0.00 baseline:35.00 break:None items:1\nrun[1.0]=range:6..11 dir:ltr clusters:5 advance:41.40\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_multiline_layout.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_multiline_layout@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.

---
**Implementation notes:**
- matches the same ligature flag sequence as defined in the core cluster serialization spec
- aligns with the dry_run field configuration in the layout engine logs
