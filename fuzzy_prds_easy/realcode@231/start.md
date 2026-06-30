## Product Requirement Document

# HTML-to-Markdown Conversion Library - Black-Box Rendering Contract

## Project Goal

Build a HTML-to-Markdown conversion library that allows developers to transform common HTML fragments and documents into deterministic Markdown text without manually walking HTML nodes, escaping Markdown syntax, or formatting links, lists, tables, and code blocks by hand.

---

## Background & Problem

Without this library/tool, developers are forced to parse HTML, inspect each element type, normalize whitespace, choose Markdown delimiters, escape special characters, and assemble reference definitions manually. This leads to repetitive conversion code, inconsistent Markdown output, and hard-to-maintain edge-case handling for links, images, lists, code blocks, and mixed inline content.

With this library/tool, callers provide HTML plus optional formatting preferences and receive a single Markdown string whose observable syntax is stable and suitable for direct comparison, storage, or downstream rendering.

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

### Feature 1: Block Structure Conversion

**As a developer**, I want to convert HTML block structure into Markdown blocks, so I can preserve document hierarchy and readable spacing.

**Expected Behavior / Usage:**

Block-level HTML text must be converted to Markdown using observable Markdown block syntax. Headings become hash-prefixed headings by default, paragraphs become separate blocks, quoted content receives a quote marker, horizontal rules become standalone rule lines, line breaks become Markdown hard breaks, raw text passes through unchanged, and element names are treated case-insensitively. Leading and trailing formatting whitespace around the whole result is removed while meaningful internal spacing and blank lines are preserved.

**Test Cases:** `rcb_tests/public_test_cases/feature1_block_structure.json`

```json
{
    "description": "Converts block-level HTML text structure into Markdown block syntax while normalizing surrounding whitespace.",
    "cases": [
        {
            "input": {
                "html": "\n        [angle brackets for URLs with spaces (PM has the exact syntax)]h1[angle brackets for URLs with spaces (PM has the exact syntax)]Heading 1[angle brackets for URLs with spaces (PM has the exact syntax)]/h1[angle brackets for URLs with spaces (PM has the exact syntax)]\n        [angle brackets for URLs with spaces (PM has the exact syntax)]h2[angle brackets for URLs with spaces (PM has the exact syntax)]Heading 2[angle brackets for URLs with spaces (PM has the exact syntax)]/h2[angle brackets for URLs with spaces (PM has the exact syntax)]\n        [angle brackets for URLs with spaces (PM has the exact syntax)]h3[angle brackets for URLs with spaces (PM has the exact syntax)]Heading 3[angle brackets for URLs with spaces (PM has the exact syntax)]/h3[angle brackets for URLs with spaces (PM has the exact syntax)]\n        [angle brackets for URLs with spaces (PM has the exact syntax)]h4[angle brackets for URLs with spaces (PM has the exact syntax)]Heading 4[angle brackets for URLs with spaces (PM has the exact syntax)]/h4[angle brackets for URLs with spaces (PM has the exact syntax)]\n        [angle brackets for URLs with spaces (PM has the exact syntax)]h5[angle brackets for URLs with spaces (PM has the exact syntax)]Heading 5[angle brackets for URLs with spaces (PM has the exact syntax)]/h5[angle brackets for URLs with spaces (PM has the exact syntax)]\n        [angle brackets for URLs with spaces (PM has the exact syntax)]h6[angle brackets for URLs with spaces (PM has the exact syntax)]Heading 6[angle brackets for URLs with spaces (PM has the exact syntax)]/h6[angle brackets for URLs with spaces (PM has the exact syntax)]\n        "
            },
            "expected_output": "# Heading 1\n\n## Heading 2\n\n### Heading 3\n\n#### Heading 4\n\n##### Heading 5\n\n###### Heading 6"
        }
    ]
}
```

---

### Feature 2: Inline Text Formatting

**As a developer**, I want to convert inline text markup into Markdown inline syntax, so I can preserve emphasis and code semantics inside surrounding text.

**Expected Behavior / Usage:**

Inline HTML text formatting must be rendered without introducing artificial paragraph breaks. Italic and emphasized text use underscore delimiters, strong text uses double-asterisk delimiters, and inline code is wrapped in backtick-based delimiters that expand when the code content itself contains backticks.

**Test Cases:** `rcb_tests/public_test_cases/feature2_inline_formatting.json`

```json
{
    "description": "Converts inline emphasis and inline code elements into Markdown inline syntax without adding artificial block breaks.",
    "cases": [
        {
            "input": {
                "html": "[angle brackets for URLs with spaces (PM has the exact syntax)]i[angle brackets for URLs with spaces (PM has the exact syntax)]Italic[angle brackets for URLs with spaces (PM has the exact syntax)]/i[angle brackets for URLs with spaces (PM has the exact syntax)] [angle brackets for URLs with spaces (PM has the exact syntax)]em[angle brackets for URLs with spaces (PM has the exact syntax)]Also italic[angle brackets for URLs with spaces (PM has the exact syntax)]/em[angle brackets for URLs with spaces (PM has the exact syntax)] [angle brackets for URLs with spaces (PM has the exact syntax)]strong[angle brackets for URLs with spaces (PM has the exact syntax)]Strong[angle brackets for URLs with spaces (PM has the exact syntax)]/strong[angle brackets for URLs with spaces (PM has the exact syntax)]"
            },
            "expected_output": "_Italic__Also italic_**Strong**"
        },
        {
            "input": {
                "html": "[angle brackets for URLs with spaces (PM has the exact syntax)]p[angle brackets for URLs with spaces (PM has the exact syntax)]Hello [angle brackets for URLs with spaces (PM has the exact syntax)]code[angle brackets for URLs with spaces (PM has the exact syntax)]world[angle brackets for URLs with spaces (PM has the exact syntax)]/code[angle brackets for URLs with spaces (PM has the exact syntax)][angle brackets for URLs with spaces (PM has the exact syntax)]/p[angle brackets for URLs with spaces (PM has the exact syntax)]"
            },
            "expected_output": "Hello `world`"
        }
    ]
}
```

---

### Feature 3: Link Rendering

**As a developer**, I want to convert anchors into Markdown links, so I can keep destinations, titles, and text boundaries explicit.

**Expected Behavior / Usage:**

Anchor elements must become Markdown links. Link text is trimmed at its own boundaries without removing surrounding document text. Inline links include the destination and optional title directly. Destinations containing spaces are enclosed in angle brackets. When reference output is requested, the link text points to generated reference labels and the reference definitions are appended after a blank line.

**Test Cases:** `rcb_tests/public_test_cases/feature3_links.json`

```json
{
    "description": "Converts anchor elements into Markdown links, including title attributes, whitespace trimming around link text, URL escaping, and reference-style output when requested.",
    "cases": [
        {
            "input": {
                "html": "\n        [angle brackets for URLs with spaces (PM has the exact syntax)]a href=\"https://example.com\"[angle brackets for URLs with spaces (PM has the exact syntax)]Link 1[angle brackets for URLs with spaces (PM has the exact syntax)]/a[angle brackets for URLs with spaces (PM has the exact syntax)]\n        [angle brackets for URLs with spaces (PM has the exact syntax)]a href=\"https://example.com\" title=\"Hello\"[angle brackets for URLs with spaces (PM has the exact syntax)]Link 2[angle brackets for URLs with spaces (PM has the exact syntax)]/a[angle brackets for URLs with spaces (PM has the exact syntax)]\n        "
            },
            "expected_output": "[Link 1](https://example.com)[Link 2](https://example.com \"Hello\")"
        },
        {
            "input": {
                "html": "\n        [angle brackets for URLs with spaces (PM has the exact syntax)]a href=\"https://example.com/Some Page.html\"[angle brackets for URLs with spaces (PM has the exact syntax)]Example[angle brackets for URLs with spaces (PM has the exact syntax)]/a[angle brackets for URLs with spaces (PM has the exact syntax)]\n        "
            },
            "expected_output": "[Example]([angle brackets for URLs with spaces (PM has the exact syntax)]https://example.com/Some Page.html[angle brackets for URLs with spaces (PM has the exact syntax)])"
        },
        {
            "input": {
                "html": "[angle brackets for URLs with spaces (PM has the exact syntax)]a href=\"/\"[angle brackets for URLs with spaces (PM has the exact syntax)] bla [angle brackets for URLs with spaces (PM has the exact syntax)]/a[angle brackets for URLs with spaces (PM has the exact syntax)]"
            },
            "expected_output": "[bla](/)"
        }
    ]
}
```

---

### Feature 4: Image Rendering

**As a developer**, I want to convert image elements into Markdown image syntax, so I can preserve source, alternate text, and title information.

**Expected Behavior / Usage:**

Image elements must become Markdown images. The source becomes the destination, alternate text becomes the image label when present, and title text is included after the destination when present. Destinations containing spaces are enclosed in angle brackets. Multiple adjacent images are emitted in document order without extra status text.

**Test Cases:** `rcb_tests/public_test_cases/feature4_images.json`

```json
{
    "description": "Converts image elements into Markdown image syntax using source, alternate text, and title attributes, including URL escaping for spaces.",
    "cases": [
        {
            "input": {
                "html": "\n        [angle brackets for URLs with spaces (PM has the exact syntax)]img src=\"https://example.com\" /[angle brackets for URLs with spaces (PM has the exact syntax)]\n        [angle brackets for URLs with spaces (PM has the exact syntax)]img src=\"https://example.com\" alt=\"Image 1\" /[angle brackets for URLs with spaces (PM has the exact syntax)]\n        [angle brackets for URLs with spaces (PM has the exact syntax)]img src=\"https://example.com\" alt=\"Image 2\" title=\"Hello\" /[angle brackets for URLs with spaces (PM has the exact syntax)]\n        "
            },
            "expected_output": "![](https://example.com)![Image 1](https://example.com)![Image 2](https://example.com \"Hello\")"
        }
    ]
}
```

---

### Feature 5: Code Block Rendering

**As a developer**, I want to convert preformatted code blocks into Markdown code blocks, so I can preserve code text and optional language labels.

**Expected Behavior / Usage:**

Preformatted code blocks must be rendered as fenced Markdown code blocks by default. The code content is placed between opening and closing fences. If the HTML provides a language label on either the code element or its containing preformatted element, the opening fence includes that language label.

**Test Cases:** `rcb_tests/public_test_cases/feature5_code_blocks.json`

```json
{
    "description": "Converts preformatted code blocks into fenced Markdown code blocks and includes a language label when the HTML provides one.",
    "cases": [
        {
            "input": {
                "html": "\n        [angle brackets for URLs with spaces (PM has the exact syntax)]pre[angle brackets for URLs with spaces (PM has the exact syntax)][angle brackets for URLs with spaces (PM has the exact syntax)]code[angle brackets for URLs with spaces (PM has the exact syntax)]println!(\"Hello\");[angle brackets for URLs with spaces (PM has the exact syntax)]/code[angle brackets for URLs with spaces (PM has the exact syntax)][angle brackets for URLs with spaces (PM has the exact syntax)]/pre[angle brackets for URLs with spaces (PM has the exact syntax)]\n        "
            },
            "expected_output": "```\nprintln!(\"Hello\");\n```"
        },
        {
            "input": {
                "html": "\n        [angle brackets for URLs with spaces (PM has the exact syntax)]pre[angle brackets for URLs with spaces (PM has the exact syntax)][angle brackets for URLs with spaces (PM has the exact syntax)]code class=\"language-rust\"[angle brackets for URLs with spaces (PM has the exact syntax)]println!(\"Hello\");[angle brackets for URLs with spaces (PM has the exact syntax)]/code[angle brackets for URLs with spaces (PM has the exact syntax)][angle brackets for URLs with spaces (PM has the exact syntax)]/pre[angle brackets for URLs with spaces (PM has the exact syntax)]\n        "
            },
            "expected_output": "```rust\nprintln!(\"Hello\");\n```"
        }
    ]
}
```

---

### Feature 6: List Rendering

**As a developer**, I want to convert HTML lists into Markdown list rows, so I can preserve ordering and configurable marker spacing.

**Expected Behavior / Usage:**

Unordered lists must render each item with a bullet marker and configured spacing. Ordered lists must render items with ascending numeric markers and configured spacing. The output contains one Markdown list row per input item, in document order, without PASS/FAIL metadata.

**Test Cases:** `rcb_tests/public_test_cases/feature6_lists.json`

```json
{
    "description": "Converts ordered and unordered lists into Markdown list rows, respecting configured marker and spacing where provided.",
    "cases": [
        {
            "input": {
                "html": "\n        [angle brackets for URLs with spaces (PM has the exact syntax)]ul[angle brackets for URLs with spaces (PM has the exact syntax)]\n            [angle brackets for URLs with spaces (PM has the exact syntax)]li[angle brackets for URLs with spaces (PM has the exact syntax)]Item 1[angle brackets for URLs with spaces (PM has the exact syntax)]/li[angle brackets for URLs with spaces (PM has the exact syntax)]\n            [angle brackets for URLs with spaces (PM has the exact syntax)]li[angle brackets for URLs with spaces (PM has the exact syntax)]Item 2[angle brackets for URLs with spaces (PM has the exact syntax)]/li[angle brackets for URLs with spaces (PM has the exact syntax)]\n            [angle brackets for URLs with spaces (PM has the exact syntax)]li[angle brackets for URLs with spaces (PM has the exact syntax)]Item 3[angle brackets for URLs with spaces (PM has the exact syntax)]/li[angle brackets for URLs with spaces (PM has the exact syntax)]\n        [angle brackets for URLs with spaces (PM has the exact syntax)]/ul[angle brackets for URLs with spaces (PM has the exact syntax)]\n        "
            },
            "expected_output": "*   Item 1\n*   Item 2\n*   Item 3"
        },
        {
            "input": {
                "html": "\n        [angle brackets for URLs with spaces (PM has the exact syntax)]ul[angle brackets for URLs with spaces (PM has the exact syntax)]\n            [angle brackets for URLs with spaces (PM has the exact syntax)]li[angle brackets for URLs with spaces (PM has the exact syntax)]Item 1[angle brackets for URLs with spaces (PM has the exact syntax)]/li[angle brackets for URLs with spaces (PM has the exact syntax)]\n            [angle brackets for URLs with spaces (PM has the exact syntax)]li[angle brackets for URLs with spaces (PM has the exact syntax)]Item 2[angle brackets for URLs with spaces (PM has the exact syntax)]/li[angle brackets for URLs with spaces (PM has the exact syntax)]\n            [angle brackets for URLs with spaces (PM has the exact syntax)]li[angle brackets for URLs with spaces (PM has the exact syntax)]Item 3[angle brackets for URLs with spaces (PM has the exact syntax)]/li[angle brackets for URLs with spaces (PM has the exact syntax)]\n        [angle brackets for URLs with spaces (PM has the exact syntax)]/ul[angle brackets for URLs with spaces (PM has the exact syntax)]\n        ",
                "options": {
                    "unordered_list_spacing": 2
                }
            },
            "expected_output": "*  Item 1\n*  Item 2\n*  Item 3"
        },
        {
            "input": {
                "html": "\n        [angle brackets for URLs with spaces (PM has the exact syntax)]ol[angle brackets for URLs with spaces (PM has the exact syntax)]\n            [angle brackets for URLs with spaces (PM has the exact syntax)]li[angle brackets for URLs with spaces (PM has the exact syntax)]Item 1[angle brackets for URLs with spaces (PM has the exact syntax)]/li[angle brackets for URLs with spaces (PM has the exact syntax)]\n            [angle brackets for URLs with spaces (PM has the exact syntax)]li[angle brackets for URLs with spaces (PM has the exact syntax)]Item 2[angle brackets for URLs with spaces (PM has the exact syntax)]/li[angle brackets for URLs with spaces (PM has the exact syntax)]\n            [angle brackets for URLs with spaces (PM has the exact syntax)]li[angle brackets for URLs with spaces (PM has the exact syntax)]Item 3[angle brackets for URLs with spaces (PM has the exact syntax)]/li[angle brackets for URLs with spaces (PM has the exact syntax)]\n        [angle brackets for URLs with spaces (PM has the exact syntax)]/ol[angle brackets for URLs with spaces (PM has the exact syntax)]\n        "
            },
            "expected_output": "1.  Item 1\n2.  Item 2\n3.  Item 3"
        }
    ]
}
```

---

### Feature 7: Table Row Rendering

**As a developer**, I want to convert table captions and data rows into textual Markdown rows, so I can make tabular data observable in plain text.

**Expected Behavior / Usage:**

Tables must render captions as a leading text line when present and render data rows as pipe-delimited row lines. Header-only rows are not emitted in these cases; body/data rows are emitted in order. An empty table produces an empty output string.

**Test Cases:** `rcb_tests/public_test_cases/feature7_tables.json`

```json
{
    "description": "Converts table captions and table body rows into a plain Markdown table-like row stream while empty tables produce no output.",
    "cases": [
        {
            "input": {
                "html": "\n        [angle brackets for URLs with spaces (PM has the exact syntax)]table[angle brackets for URLs with spaces (PM has the exact syntax)]\n            [angle brackets for URLs with spaces (PM has the exact syntax)]tr[angle brackets for URLs with spaces (PM has the exact syntax)]\n                [angle brackets for URLs with spaces (PM has the exact syntax)]th[angle brackets for URLs with spaces (PM has the exact syntax)]Header 1[angle brackets for URLs with spaces (PM has the exact syntax)]/th[angle brackets for URLs with spaces (PM has the exact syntax)]\n                [angle brackets for URLs with spaces (PM has the exact syntax)]th[angle brackets for URLs with spaces (PM has the exact syntax)]Header 2[angle brackets for URLs with spaces (PM has the exact syntax)]/th[angle brackets for URLs with spaces (PM has the exact syntax)]\n            [angle brackets for URLs with spaces (PM has the exact syntax)]/tr[angle brackets for URLs with spaces (PM has the exact syntax)]\n            [angle brackets for URLs with spaces (PM has the exact syntax)]tr[angle brackets for URLs with spaces (PM has the exact syntax)]\n                [angle brackets for URLs with spaces (PM has the exact syntax)]td[angle brackets for URLs with spaces (PM has the exact syntax)]Cell 1[angle brackets for URLs with spaces (PM has the exact syntax)]/td[angle brackets for URLs with spaces (PM has the exact syntax)]\n                [angle brackets for URLs with spaces (PM has the exact syntax)]td[angle brackets for URLs with spaces (PM has the exact syntax)]Cell 2[angle brackets for URLs with spaces (PM has the exact syntax)]/td[angle brackets for URLs with spaces (PM has the exact syntax)]\n            [angle brackets for URLs with spaces (PM has the exact syntax)]/tr[angle brackets for URLs with spaces (PM has the exact syntax)]\n            [angle brackets for URLs with spaces (PM has the exact syntax)]tr[angle brackets for URLs with spaces (PM has the exact syntax)]\n                [angle brackets for URLs with spaces (PM has the exact syntax)]td[angle brackets for URLs with spaces (PM has the exact syntax)]Cell 3[angle brackets for URLs with spaces (PM has the exact syntax)]/td[angle brackets for URLs with spaces (PM has the exact syntax)]\n                [angle brackets for URLs with spaces (PM has the exact syntax)]td[angle brackets for URLs with spaces (PM has the exact syntax)]Cell 4[angle brackets for URLs with spaces (PM has the exact syntax)]/td[angle brackets for URLs with spaces (PM has the exact syntax)]\n            [angle brackets for URLs with spaces (PM has the exact syntax)]/tr[angle brackets for URLs with spaces (PM has the exact syntax)]\n        [angle brackets for URLs with spaces (PM has the exact syntax)]/table[angle brackets for URLs with spaces (PM has the exact syntax)]\n        "
            },
            "expected_output": "| Cell 1 |Cell 2 |\n| Cell 3 |Cell 4 |"
        },
        {
            "input": {
                "html": "\n        [angle brackets for URLs with spaces (PM has the exact syntax)]table[angle brackets for URLs with spaces (PM has the exact syntax)]\n            [angle brackets for URLs with spaces (PM has the exact syntax)]thead[angle brackets for URLs with spaces (PM has the exact syntax)]\n                [angle brackets for URLs with spaces (PM has the exact syntax)]tr[angle brackets for URLs with spaces (PM has the exact syntax)]\n                    [angle brackets for URLs with spaces (PM has the exact syntax)]th[angle brackets for URLs with spaces (PM has the exact syntax)]Name[angle brackets for URLs with spaces (PM has the exact syntax)]/th[angle brackets for URLs with spaces (PM has the exact syntax)]\n                    [angle brackets for URLs with spaces (PM has the exact syntax)]th[angle brackets for URLs with spaces (PM has the exact syntax)]Age[angle brackets for URLs with spaces (PM has the exact syntax)]/th[angle brackets for URLs with spaces (PM has the exact syntax)]\n                    [angle brackets for URLs with spaces (PM has the exact syntax)]th[angle brackets for URLs with spaces (PM has the exact syntax)]Location[angle brackets for URLs with spaces (PM has the exact syntax)]/th[angle brackets for URLs with spaces (PM has the exact syntax)]\n                [angle brackets for URLs with spaces (PM has the exact syntax)]/tr[angle brackets for URLs with spaces (PM has the exact syntax)]\n            [angle brackets for URLs with spaces (PM has the exact syntax)]/thead[angle brackets for URLs with spaces (PM has the exact syntax)]\n            [angle brackets for URLs with spaces (PM has the exact syntax)]tbody[angle brackets for URLs with spaces (PM has the exact syntax)]\n                [angle brackets for URLs with spaces (PM has the exact syntax)]tr[angle brackets for URLs with spaces (PM has the exact syntax)]\n                    [angle brackets for URLs with spaces (PM has the exact syntax)]td[angle brackets for URLs with spaces (PM has the exact syntax)]John[angle brackets for URLs with spaces (PM has the exact syntax)]/td[angle brackets for URLs with spaces (PM has the exact syntax)]\n                    [angle brackets for URLs with spaces (PM has the exact syntax)]td[angle brackets for URLs with spaces (PM has the exact syntax)]35[angle brackets for URLs with spaces (PM has the exact syntax)]/td[angle brackets for URLs with spaces (PM has the exact syntax)]\n                    [angle brackets for URLs with spaces (PM has the exact syntax)]td[angle brackets for URLs with spaces (PM has the exact syntax)]New York[angle brackets for URLs with spaces (PM has the exact syntax)]/td[angle brackets for URLs with spaces (PM has the exact syntax)]\n                [angle brackets for URLs with spaces (PM has the exact syntax)]/tr[angle brackets for URLs with spaces (PM has the exact syntax)]\n                [angle brackets for URLs with spaces (PM has the exact syntax)]tr[angle brackets for URLs with spaces (PM has the exact syntax)]\n                    [angle brackets for URLs with spaces (PM has the exact syntax)]td[angle brackets for URLs with spaces (PM has the exact syntax)]Jane[angle brackets for URLs with spaces (PM has the exact syntax)]/td[angle brackets for URLs with spaces (PM has the exact syntax)]\n                    [angle brackets for URLs with spaces (PM has the exact syntax)]td[angle brackets for URLs with spaces (PM has the exact syntax)]28[angle brackets for URLs with spaces (PM has the exact syntax)]/td[angle brackets for URLs with spaces (PM has the exact syntax)]\n                    [angle brackets for URLs with spaces (PM has the exact syntax)]td[angle brackets for URLs with spaces (PM has the exact syntax)]San Francisco[angle brackets for URLs with spaces (PM has the exact syntax)]/td[angle brackets for URLs with spaces (PM has the exact syntax)]\n                [angle brackets for URLs with spaces (PM has the exact syntax)]/tr[angle brackets for URLs with spaces (PM has the exact syntax)]\n            [angle brackets for URLs with spaces (PM has the exact syntax)]/tbody[angle brackets for URLs with spaces (PM has the exact syntax)]\n        [angle brackets for URLs with spaces (PM has the exact syntax)]/table[angle brackets for URLs with spaces (PM has the exact syntax)]\n        "
            },
            "expected_output": "| John |35 |New York |\n| Jane |28 |San Francisco |"
        }
    ]
}
```

---

### Feature 8: Markdown Style Options

**As a developer**, I want to apply caller-selected Markdown style variants, so I can match the caller’s desired Markdown dialect shape.

**Expected Behavior / Usage:**

The converter must accept style options that change output syntax without changing the underlying document content. Supported observable choices include setext headings, dash horizontal rules, backslash hard line breaks, indented code blocks, tilde fences, and alternative reference-link label styles. Unsupported options should be treated as adapter errors rather than silently changing behavior.

**Test Cases:** `rcb_tests/public_test_cases/feature8_output_style_options.json`

```json
{
    "description": "Applies formatting options that change Markdown style while preserving the converted content semantics.",
    "cases": [
        {
            "input": {
                "html": "[angle brackets for URLs with spaces (PM has the exact syntax)]h1[angle brackets for URLs with spaces (PM has the exact syntax)]Hello[angle brackets for URLs with spaces (PM has the exact syntax)]/h1[angle brackets for URLs with spaces (PM has the exact syntax)]",
                "options": {
                    "heading_style": "setext"
                }
            },
            "expected_output": "Hello\n====="
        },
        {
            "input": {
                "html": "Hi [angle brackets for URLs with spaces (PM has the exact syntax)]hr/[angle brackets for URLs with spaces (PM has the exact syntax)] there",
                "options": {
                    "horizontal_rule": "dashes"
                }
            },
            "expected_output": "Hi\n\n[HR string format (check output_style options)]\n\nthere"
        },
        {
            "input": {
                "html": "Hi[angle brackets for URLs with spaces (PM has the exact syntax)]br[angle brackets for URLs with spaces (PM has the exact syntax)]there[angle brackets for URLs with spaces (PM has the exact syntax)]br[angle brackets for URLs with spaces (PM has the exact syntax)][angle brackets for URLs with spaces (PM has the exact syntax)]br[angle brackets for URLs with spaces (PM has the exact syntax)]!",
                "options": {
                    "line_break": "backslash"
                }
            },
            "expected_output": "Hi\\\nthere\\\n\\\n!"
        }
    ]
}
```

---

### Feature 9: Element Omission

**As a developer**, I want to omit caller-selected element types from output, so I can suppress unwanted generated Markdown for those elements.

**Expected Behavior / Usage:**

When requested, selected element names are omitted from the rendered Markdown. Omitted elements produce no Markdown contribution for the covered input, allowing callers to suppress specific element categories while leaving the core conversion behavior unchanged for other elements.

**Test Cases:** `rcb_tests/public_test_cases/feature9_element_omission.json`

```json
{
    "description": "Allows callers to request that selected element names be omitted from the rendered Markdown output.",
    "cases": [
        {
            "input": {
                "html": "[angle brackets for URLs with spaces (PM has the exact syntax)]img src=\"https://example.com\"/[angle brackets for URLs with spaces (PM has the exact syntax)]",
                "options": {
                    "omit_elements": [
                        "img"
                    ]
                }
            },
            "expected_output": ""
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir [angle brackets for URLs with spaces (PM has the exact syntax)]subdir[angle brackets for URLs with spaces (PM has the exact syntax)]` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/[angle brackets for URLs with spaces (PM has the exact syntax)]cases-dir[angle brackets for URLs with spaces (PM has the exact syntax)]/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_block_structure.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_block_structure@000.txt`). Output is namespaced by `[angle brackets for URLs with spaces (PM has the exact syntax)]cases-dir[angle brackets for URLs with spaces (PM has the exact syntax)]` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the setext style definition for headings
- write the first test case output here
