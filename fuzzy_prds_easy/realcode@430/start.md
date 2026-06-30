## Product Requirement Document

# Markdown Rendering and Document Tree Toolkit - Convert, Inspect, and Transform Markdown Documents

## Project Goal

Build a Markdown processing toolkit that allows developers to render Markdown to HTML, extract plain text, inspect parsed document structure, and apply controlled tree transformations without manually parsing Markdown syntax or hand-maintaining HTML output.

---

## Background & Problem

Without this library/tool, developers are forced to combine ad hoc regular expressions, handwritten HTML generation, and custom tree bookkeeping to support Markdown content. This leads to incorrect rendering, inconsistent extension handling, fragile source mapping, and repetitive transformation code.

With this library/tool, developers can treat Markdown parsing, rendering, inspection, and mutation as a consistent black-box capability with predictable input and output contracts.

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

### Feature 1: Basic Markdown to HTML Rendering

**As a developer**, I want to convert ordinary Markdown text into HTML, so I can display formatted content without hand-writing HTML.

**Expected Behavior / Usage:**

Plain text containing Markdown inline emphasis is accepted as the input value. The adapter prints the rendered HTML document exactly, including the trailing newline emitted by the renderer. Paragraphs are wrapped in paragraph tags and inline emphasis becomes emphasis markup.

**Test Cases:** `rcb_tests/public_test_cases/feature1_basic_html.json`

```json
{
  "description": "Markdown inline emphasis is rendered as HTML while preserving paragraph structure.",
  "cases": [
    {
      "input": "Hi *there*",
      "expected_output": "<p>Hi <em>there</em></p>\n"
    }
  ]
}
```

---

### Feature 2: Hard Line Break Rendering

**As a developer**, I want to request hard line breaks inside paragraphs, so I can preserve author-intended line breaks in rendered HTML.

**Expected Behavior / Usage:**

The input value is Markdown text containing an internal newline. The adapter renders it as HTML with hard-break behavior enabled, so a newline inside a paragraph becomes a break element followed by the next line of text. The printed output is the complete HTML fragment.

**Test Cases:** `rcb_tests/public_test_cases/feature2_hardbreak_html.json`

```json
{
  "description": "Line breaks inside a paragraph are rendered as hard HTML breaks when hard-break rendering is requested.",
  "cases": [
    {
      "input": "foo\nbaz",
      "expected_output": "<p>foo<br />\nbaz</p>\n"
    }
  ]
}
```

---

### Feature 3: Smart Punctuation Rendering

**As a developer**, I want to convert straight punctuation into typographic punctuation, so I can produce publication-friendly text while preserving Markdown structure.

**Expected Behavior / Usage:**

The input object contains Markdown text and may request hard-break HTML rendering. Smart punctuation parsing converts matched straight quotes, nested quotes, and apostrophes into typographic characters. The output is the rendered HTML fragment with the converted punctuation visible in text nodes.

**Test Cases:** `rcb_tests/public_test_cases/feature3_smart_punctuation.json`

```json
{
  "description": "Smart punctuation rendering converts straight quotes and apostrophes to typographic punctuation.",
  "cases": [
    {
      "input": {
        "markdown": "\"Hello,\" said the spider.\n\"'Shelob' is my name.\""
      },
      "expected_output": "<p>“Hello,” said the spider.\n“‘Shelob’ is my name.”</p>\n"
    },
    {
      "input": {
        "markdown": "'A', 'B', and 'C' are letters."
      },
      "expected_output": "<p>‘A’, ‘B’, and ‘C’ are letters.</p>\n"
    }
  ]
}
```

---

### Feature 4: Optional Markdown Extension Rendering

**As a developer**, I want to enable or omit individual Markdown extensions, so I can control which extended syntaxes are interpreted.

**Expected Behavior / Usage:**

The input is an object with Markdown text and a list of extension names. With no extension selected, table and deletion syntax remain ordinary paragraph text while standard inline formatting still applies. With selected extensions, only the selected syntaxes are converted. Optional rendering and parsing flags may be included when they describe externally visible rendering behavior, such as table alignment output form or double-tilde deletion recognition.

**Test Cases:** `rcb_tests/public_test_cases/feature4_extension_html.json`

```json
{
  "description": "Optional Markdown extensions alter HTML rendering only when selected.",
  "cases": [
    {
      "input": {
        "markdown": "One extension:\n\n| a   | b   |\n| --- | --- |\n| c   | d   |\n| **x** | |\n\nAnother extension:\n\n~~hi~~\n",
        "extensions": []
      },
      "expected_output": "<p>One extension:</p>\n<p>| a   | b   |\n| --- | --- |\n| c   | d   |\n| <strong>x</strong> | |</p>\n<p>Another extension:</p>\n<p>~~hi~~</p>\n"
    },
    {
      "input": {
        "markdown": "One extension:\n\n| a   | b   |\n| --- | --- |\n| c   | d   |\n| **x** | |\n\nAnother extension:\n\n~~hi~~\n",
        "extensions": [
          "table"
        ]
      },
      "expected_output": "<p>One extension:</p>\n<table>\n<thead>\n<tr>\n<th>a</th>\n<th>b</th>\n</tr>\n</thead>\n<tbody>\n<tr>\n<td>c</td>\n<td>d</td>\n</tr>\n<tr>\n<td><strong>x</strong></td>\n<td></td>\n</tr>\n</tbody>\n</table>\n<p>Another extension:</p>\n<p>~~hi~~</p>\n"
    }
  ]
}
```

---

### Feature 5: Fenced Code Info Metadata Rendering

**As a developer**, I want to render fenced code block information, so I can preserve language and metadata attached to code blocks.

**Expected Behavior / Usage:**

The input object contains Markdown with a fenced code block. The output is HTML for the code block. The first word of the fence info string becomes the language class. Additional info string content becomes metadata when present, and invalid null bytes are rendered using the Unicode replacement character.

**Test Cases:** `rcb_tests/public_test_cases/feature5_fenced_code_metadata.json`

```json
{
  "description": "Fenced code block info strings are rendered as language class and optional metadata when requested.",
  "cases": [
    {
      "input": {
        "markdown": "```ruby\nmodule Foo\n```\n"
      },
      "expected_output": "<pre><code class=\"[metadata prefix format]ruby\">module Foo\n</code></pre>\n"
    },
    {
      "input": {
        "markdown": "```ruby my info string\nmodule Foo\n```\n"
      },
      "expected_output": "<pre><code class=\"[metadata prefix format]ruby\" [metadata prefix format]=\"my info string\">module Foo\n</code></pre>\n"
    }
  ]
}
```

---

### Feature 6: Footnote Rendering

**As a developer**, I want to render footnote references and definitions, so I can turn note-style Markdown into linked document annotations.

**Expected Behavior / Usage:**

The input value is Markdown containing a footnote reference and a matching definition. The output is HTML containing the main content with a superscript reference link plus a footnotes section with the numbered note and a backlink.

**Test Cases:** `rcb_tests/public_test_cases/feature6_footnote_html.json`

```json
{
  "description": "Footnote references and definitions render as linked superscript references and a footnotes section.",
  "cases": [
    {
      "input": "Hello[^hi].\n\n[^hi]: Hey!\n",
      "expected_output": "<p>Hello<sup class=\"footnote-ref\"><a href=\"#fn1\" id=\"fnref1\">1</a></sup>.</p>\n<section class=\"footnotes\">\n<ol>\n<li id=\"fn1\">\n<p>Hey! <a href=\"#fnref1\" class=\"footnote-backref\">↩</a></p>\n</li>\n</ol>\n</section>\n"
    }
  ]
}
```

---

### Feature 7: Task List Rendering and State

**As a developer**, I want to render task-list items and read their checked state, so I can display checklist-style Markdown and inspect item completion.

**Expected Behavior / Usage:**

The input object contains task-list Markdown and a requested view. The HTML view prints a list with disabled checkbox inputs for checked and unchecked items. State views print comma-separated checked-state labels, and a toggle view changes the first two task items before printing their resulting states.

**Test Cases:** `rcb_tests/public_test_cases/feature7_task_list.json`

```json
{
  "description": "Task-list items render disabled checkbox inputs and expose checked states.",
  "cases": [
    {
      "input": {
        "markdown": "- [x] Add task list\n- [ ] Define task list\n",
        "view": "html"
      },
      "expected_output": "<ul>\n<li><input type=\"checkbox\" checked=\"\" disabled=\"\" /> Add task list</li>\n<li><input type=\"checkbox\" disabled=\"\" /> Define task list</li>\n</ul>\n"
    },
    {
      "input": {
        "markdown": "- [x] Add task list\n- [ ] Define task list\n",
        "view": "states"
      },
      "expected_output": "checked,unchecked\n"
    }
  ]
}
```

---

### Feature 8: Plain Text Extraction

**As a developer**, I want to extract readable text from a parsed Markdown document, so I can reuse Markdown content in non-HTML contexts.

**Expected Behavior / Usage:**

The input object contains Markdown and optional extensions. The output is the plain-text rendering of the parsed document. Inline formatting markers are removed, lists are normalized into readable list text, and table content is represented in a plain textual table layout.

**Test Cases:** `rcb_tests/public_test_cases/feature8_plaintext.json`

```json
{
  "description": "Rendered documents can be converted to plain text while preserving list and table text layout.",
  "cases": [
    {
      "input": {
        "markdown": "Hi *there*!\n\n1. I am a numeric list.\n2. I continue the list.\n* Suddenly, an unordered list!\n* What fun!\n\nOkay, _enough_.\n\n| a   | b   |\n| --- | --- |\n| c   | d   |\n",
        "extensions": [
          "table"
        ]
      },
      "expected_output": "Hi there!\n\n1.  I am a numeric list.\n2.  I continue the list.\n\n  - Suddenly, an unordered list!\n  - What fun!\n\nOkay, enough.\n\n| a | b |\n| --- | --- |\n| c | d |\n"
    }
  ]
}
```

---

### Feature 9: Markdown Serialization Round Trip

**As a developer**, I want to serialize a parsed document back to Markdown, so I can preserve equivalent rendered structure across parse and serialization.

**Expected Behavior / Usage:**

The input value is Markdown text. The adapter parses it, serializes the document back to Markdown, reparses the serialized text, and prints a JSON object containing the original HTML, serialized Markdown, and reparsed HTML. This verifies that serialization preserves the document structure visible through rendering.

**Test Cases:** `rcb_tests/public_test_cases/feature9_commonmark_roundtrip.json`

```json
{
  "description": "Serializing a parsed document back to Markdown preserves equivalent HTML when parsed again.",
  "cases": [
    {
      "input": "Hi *there*!\n\n1. I am a numeric list.\n2. I continue the list.\n* Suddenly, an unordered list!\n* What fun!\n\nOkay, _enough_.\n\n| a   | b   |\n| --- | --- |\n| c   | d   |\n",
      "expected_output": "{\"original_html\":\"<p>Hi <em>there</em>!</p>\\n<ol>\\n<li>I am a numeric list.</li>\\n<li>I continue the list.</li>\\n</ol>\\n<ul>\\n<li>Suddenly, an unordered list!</li>\\n<li>What fun!</li>\\n</ul>\\n<p>Okay, <em>enough</em>.</p>\\n<table>\\n<thead>\\n<tr>\\n<th>a</th>\\n<th>b</th>\\n</tr>\\n</thead>\\n<tbody>\\n<tr>\\n<td>c</td>\\n<td>d</td>\\n</tr>\\n</tbody>\\n</table>\\n\",\"serialized_markdown\":\"Hi *there*\\\\!\\n\\n1.  I am a numeric list.\\n2.  I continue the list.\\n\\n<!-- end list -->\\n\\n  - Suddenly, an unordered list\\\\!\\n  - What fun\\\\!\\n\\nOkay, *enough*.\\n\\n| a | b |\\n| --- | --- |\\n| c | d |\\n\",\"reparsed_html\":\"<p>Hi <em>there</em>!</p>\\n<ol>\\n<li>I am a numeric list.</li>\\n<li>I continue the list.</li>\\n</ol>\\n<!-- raw HTML omitted -->\\n<ul>\\n<li>Suddenly, an unordered list!</li>\\n<li>What fun!</li>\\n</ul>\\n<p>Okay, <em>enough</em>.</p>\\n<table>\\n<thead>\\n<tr>\\n<th>a</th>\\n<th>b</th>\\n</tr>\\n</thead>\\n<tbody>\\n<tr>\\n<td>c</td>\\n<td>d</td>\\n</tr>\\n</tbody>\\n</table>\\n\"}\n"
    }
  ]
}
```

---

### Feature 10: Document Tree Traversal

**As a developer**, I want to traverse and navigate the parsed document tree, so I can inspect document structure in a predictable order.

**Expected Behavior / Usage:**

The input object contains Markdown and a requested tree view. Traversal views print comma-separated node type names in depth-first or direct-child order. Navigation views print labeled relationships such as first child, previous sibling, next sibling, parent, and last child for the parsed structure.

**Test Cases:** `rcb_tests/public_test_cases/feature10_node_tree.json`

```json
{
  "description": "Parsed documents expose stable node traversal and navigation order.",
  "cases": [
    {
      "input": {
        "markdown": "Hi *there*, I am mostly text!",
        "view": "walk_types"
      },
      "expected_output": "document,paragraph,text,emph,text,text\n"
    },
    {
      "input": {
        "markdown": "Hi *there*, I am mostly text!",
        "view": "child_types"
      },
      "expected_output": "text,emph,text\n"
    }
  ]
}
```

---

### Feature 11: Structured Node Attributes

**As a developer**, I want to read and update attributes of specific Markdown constructs, so I can modify document metadata before rendering or inspection.

**Expected Behavior / Usage:**

The input object identifies a construct kind, Markdown that creates that construct, and optional replacement values. The adapter prints the original attribute values and any updated values. Covered attributes include link destinations, image titles, heading levels, list type/start/tightness, and fenced-code info strings.

**Test Cases:** `rcb_tests/public_test_cases/feature11_node_attributes.json`

```json
{
  "description": "Structured document nodes expose and update attributes appropriate to their Markdown construct.",
  "cases": [
    {
      "input": {
        "kind": "link",
        "markdown": "[Link](https://www.github.com)",
        "new_url": "https://www.mozilla.org"
      },
      "expected_output": "url=https://www.github.com\nupdated_url=https://www.mozilla.org\n"
    },
    {
      "input": {
        "kind": "image",
        "markdown": "![alt text](https://github.com/favicon.ico \"Favicon\")",
        "new_title": "Octocat"
      },
      "expected_output": "title=Favicon\nupdated_title=Octocat\n"
    }
  ]
}
```

---

### Feature 12: Document Tree Mutation

**As a developer**, I want to edit the parsed document tree, so I can programmatically transform Markdown before rendering.

**Expected Behavior / Usage:**

The input object contains Markdown and a requested edit. The adapter applies the edit to the parsed tree and prints the resulting HTML. Supported externally visible edits include inserting empty paragraphs, prepending or appending inline nodes, replacing text inside emphasis, and unwrapping emphasis while preserving its text.

**Test Cases:** `rcb_tests/public_test_cases/feature12_node_mutation.json`

```json
{
  "description": "Structured document nodes can be inserted, appended, edited, unwrapped, and rendered back to HTML.",
  "cases": [
    {
      "input": {
        "markdown": "Hi *there*. This has __many nodes__!",
        "edit": "insert_empty_paragraph_before"
      },
      "expected_output": "<p></p>\n<p>Hi <em>there</em>. This has <strong>many nodes</strong>!</p>\n"
    },
    {
      "input": {
        "markdown": "Hi *there*. This has __many nodes__!",
        "edit": "insert_empty_paragraph_after"
      },
      "expected_output": "<p>Hi <em>there</em>. This has <strong>many nodes</strong>!</p>\n<p></p>\n"
    }
  ]
}
```

---

### Feature 13: Normalized Error Reporting

**As a developer**, I want to receive stable error output for invalid inputs and operations, so I can handle failures without depending on a host language runtime.

**Expected Behavior / Usage:**

The input object selects an invalid operation attempt. The adapter catches native failures from the underlying implementation and prints [metadata prefix format]neutral lines containing an error category, context, and selector. Output must not include host-language exception class names, runtime object renderings, or generated message suffixes.

**Test Cases:** `rcb_tests/public_test_cases/feature13_normalized_errors.json`

```json
{
  "description": "Invalid input, unsupported options, and invalid document operations are reported with [metadata prefix format]neutral error categories.",
  "cases": [
    {
      "input": {
        "attempt": "non_text_document"
      },
      "expected_output": "error=invalid_input_type\ncontext=normalized_errors\nselector=non_text_document\n"
    },
    {
      "input": {
        "attempt": "bad_html_render_flag_type"
      },
      "expected_output": "error=invalid_input_type\ncontext=normalized_errors\nselector=bad_html_render_flag_type\n"
    },
    {
      "input": {
        "attempt": "html_parse_flag_not_allowed"
      },
      "expected_output": "error=invalid_input_type\ncontext=normalized_errors\nselector=html_parse_flag_not_allowed\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_basic_html.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_basic_html@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.

---
**Implementation notes:**
- list of default extensions in the spec
- hierarchy of direct text nodes
