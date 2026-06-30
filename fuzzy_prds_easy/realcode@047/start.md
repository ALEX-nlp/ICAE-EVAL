## Product Requirement Document

# Inline Rich-Text Formatting Engine - Selection-Driven Editing Operations

## Project Goal

Build the editing core of a rich-text document editor that lets developers apply, change, and remove formatting on a user's current text selection, and place a floating formatting toolbar precisely over that selection. The core turns a structured document plus a selection into a new structured document, exposing each operation as a small, predictable transformation that a UI layer can drive.

---

## Background & Problem

Without this core, developers building a rich-text editor must hand-roll the rules for every formatting action: how a bold/italic toggle interacts with the current cursor, how converting a paragraph into a heading or quote works, how a hyperlink is attached to a span of text (and how a bare address like `example.com` should be upgraded to a real URL), and how an existing link is detached. They also have to repeatedly re-derive the geometry needed to float a contextual toolbar centered above the selection. This leads to scattered, inconsistent, error-prone logic spread across UI event handlers.

With this core, each editing operation is a single well-defined transformation over the document and selection, and the toolbar geometry is a pure calculation. The UI layer only has to forward intent ("toggle bold", "make this a heading", "link this", "unlink this") and render the result.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain has several distinct responsibilities (inline formatting, block formatting, hyperlink lifecycle, toolbar geometry), so it MUST be organized into clear, separated modules rather than one monolithic file — without over-engineering trivial helpers.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in "Core Features" are a **black-box contract** for an execution adapter, NOT the internal data model of the core. The core editing logic must be completely decoupled from stdin/stdout and JSON parsing. A thin adapter translates each JSON command into idiomatic calls on the core and renders the result.

3. **Adherence to SOLID Design Principles:**
   - **SRP:** Separate parsing, routing, validation, core transformation, and output formatting.
   - **OCP:** New formatting operations should be addable without modifying existing ones.
   - **LSP:** Operation types should be substitutable behind a common operation abstraction.
   - **ISP:** Keep operation interfaces small and cohesive.
   - **DIP:** High-level editing logic must not depend on the I/O adapter.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface must be elegant and idiomatic to the target language, hiding document-model complexity.
   - **Resilience:** Unknown commands and malformed input must be handled gracefully and reported as neutral error categories, never as raw runtime traces.

---

## Core Features

### Feature 1: Inline Character Formatting Toggle

**As a developer**, I want to toggle an inline character format (such as bold, italic, or underline) for the current selection, so I can let users apply and remove character styling.

**Expected Behavior / Usage:**

The operation takes the block text and the name of an inline format to toggle. It returns which inline format was toggled and the set of inline formats that are now active at the current position. When the cursor is collapsed (no characters selected), toggling a format turns it into a pending style that will apply to text typed next, so the format is reported as active immediately after toggling it on. Inline format names are opaque uppercase identifiers (e.g. `BOLD`, `ITALIC`, `UNDERLINE`). When multiple formats are active they are listed comma-separated in sorted order.

**Test Cases:** `rcb_tests/public_test_cases/feature1_inline_style.json`

```json
{
    "description": "Toggling an inline character format on a text run reports which inline formats are now active. With an empty (collapsed) cursor the chosen format becomes a pending style that applies to text typed next.",
    "cases": [
        {
            "input": {"command": "toggle_inline_style", "text": "Hello World!", "style": "BOLD"},
            "expected_output": "toggled_style=BOLD\nactive_inline_styles=BOLD\n"
        },
        {
            "input": {"command": "toggle_inline_style", "text": "Hello World!", "style": "ITALIC"},
            "expected_output": "toggled_style=ITALIC\nactive_inline_styles=ITALIC\n"
        }
    ]
}
```

---

### Feature 2: Block-Level Formatting Toggle

**As a developer**, I want to convert the block containing the cursor into a different block type (such as a heading, a quote, or a list item), so I can let users restructure paragraphs.

**Expected Behavior / Usage:**

The operation takes the block text and a target block type, and converts the block that holds the cursor to that type. It returns the requested block type and the block's resulting type. Block types are opaque lowercase identifiers (e.g. `header-two`, `blockquote`, `unordered-list-item`).

**Test Cases:** `rcb_tests/public_test_cases/feature2_block_type.json`

```json
{
    "description": "Toggling a block-level format on the block containing the cursor converts that block to the requested block type, reported back as the resulting block type.",
    "cases": [
        {
            "input": {"command": "toggle_block_type", "text": "Hello World!", "block_type": "header-two"},
            "expected_output": "toggled_block_type=header-two\nblock_type=header-two\n"
        },
        {
            "input": {"command": "toggle_block_type", "text": "Hello World!", "block_type": "blockquote"},
            "expected_output": "toggled_block_type=blockquote\nblock_type=blockquote\n"
        }
    ]
}
```

---

### Feature 3: Hyperlink Management

**As a developer**, I want to attach and detach hyperlinks on a selected text range, so I can let users link and unlink text.

**Expected Behavior / Usage:**

*3.1 Apply Hyperlink — attach a link to a selected range, normalizing the address scheme.*

The operation takes the block text, an anchor/focus offset pair describing the selected range, and the address the user entered. It attaches a link entity to that range and reports the entity kind (`LINK`) and the stored URL. If the entered address already begins with `[reserved suffix for deducing the protocol]` or `https://`, it is stored unchanged. If it has no scheme, a default `[reserved suffix for deducing the protocol]` scheme is prepended before storing (e.g. `www.example.com` becomes `[reserved suffix for deducing the protocol]www.example.com`).

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_apply_link.json`

```json
{
    "description": "Applying a hyperlink to a selected text range stores a link entity carrying the target URL. When the entered address has no scheme, a default [reserved suffix for deducing the protocol] scheme is prepended; an address that already starts with [reserved suffix for deducing the protocol] or https:// is stored unchanged.",
    "cases": [
        {
            "input": {"command": "add_link", "text": "Hello World!", "anchor_offset": 0, "focus_offset": 5, "link": "[reserved suffix for deducing the protocol]www.globo.com"},
            "expected_output": "entity_type=LINK\n[reserved suffix for deducing the protocol]=[reserved suffix for deducing the protocol]www.globo.com\n"
        },
        {
            "input": {"command": "add_link", "text": "Hello World!", "anchor_offset": 0, "focus_offset": 5, "link": "www.globo.com"},
            "expected_output": "entity_type=LINK\n[reserved suffix for deducing the protocol]=[reserved suffix for deducing the protocol]www.globo.com\n"
        }
    ]
}
```

*3.2 Remove Hyperlink — detach an existing link from a selected range.*

The operation takes the block text, an anchor/focus offset pair describing a non-empty selection that currently carries a link, and the address originally stored. It detaches the link entity from the range and reports the URL that existed before removal and that no entity remains attached afterward (`entity_after=none`).

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_remove_link.json`

```json
{
    "description": "Removing a hyperlink from a previously linked, non-empty selection detaches the link entity from the text. The output reports the URL that existed before removal and that no entity remains attached afterward.",
    "cases": [
        {
            "input": {"command": "remove_link", "text": "Hello World!", "anchor_offset": 0, "focus_offset": 5, "link": "[reserved suffix for deducing the protocol]www.globo.com"},
            "expected_output": "[reserved suffix for deducing the protocol]_before=[reserved suffix for deducing the protocol]www.globo.com\nentity_after=none\n"
        }
    ]
}
```

---

### Feature 4: Selection-Anchored Toolbar Position

**As a developer**, I want to compute where a floating formatting toolbar should sit relative to the editor, so it stays centered over the current selection and a fixed gap above it.

**Expected Behavior / Usage:**

The operation takes the selection rectangle (`top`, `left`, `right`), the editor's bounding rectangle (`top`, `left`), and the toolbar's size (`width`, `height`). It returns two offsets relative to the editor: the top offset places the toolbar a fixed 14-unit gap above the selection (`[computed layout parameters derived from geometry math] = range.top - editor.top - (toolbar.height + 14)`); the left offset horizontally centers the toolbar over the selection (`[computed layout parameters derived from geometry math] = (range.left - editor.left) + (range.right - range.left) / 2 - toolbar.width / 2`). Values may be fractional.

**Test Cases:** `rcb_tests/public_test_cases/feature4_toolbar_position.json`

```json
{
    "description": "Computes where a floating formatting toolbar should be placed so it is horizontally centered over the current text selection and sits a fixed gap above it. Inputs are the selection rectangle, the editor's bounding rectangle, and the toolbar size; outputs are the toolbar's top and left offsets relative to the editor.",
    "cases": [
        {
            "input": {"command": "toolbar_position", "range_rect": {"top": 0, "left": 0, "right": 1}, "editor_rect": {"top": 0, "left": 0}, "toolbar": {"width": 0, "height": 0}},
            "expected_output": "[computed layout parameters derived from geometry math]=-14\n[computed layout parameters derived from geometry math]=0.5\n"
        },
        {
            "input": {"command": "toolbar_position", "range_rect": {"top": 100, "left": 40, "right": 140}, "editor_rect": {"top": 20, "left": 10}, "toolbar": {"width": 60, "height": 36}},
            "expected_output": "[computed layout parameters derived from geometry math]=30\n[computed layout parameters derived from geometry math]=50\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the four features above (inline formatting, block formatting, hyperlink lifecycle, toolbar geometry), organized into separated modules that reflect those responsibilities.

2. **The Execution/Test Adapter:** A runnable entry point that reads a single JSON command object from stdin, routes it to the appropriate core operation, and prints the result to stdout as the line-based `key=value` contract shown above. The adapter is logically separated from the core and is the only component aware of stdin/stdout and JSON. Unknown commands and malformed input are rendered as neutral error lines, never as raw runtime traces.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to select the directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_inline_style.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_inline_style@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the directory layout standards defined in the test runner module
