## Product Requirement Document

# Markdown to HTML Conversion Engine — Configurable Block & Inline Rendering

## Project Goal

Build a reusable text-transformation engine that turns Markdown source into an HTML document fragment, so developers can render user-authored content as structured HTML without hand-writing a parser or hand-escaping markup for every document.

---

## Background & Problem

Authors write content in Markdown — a plain-text shorthand for headings, lists, [a feature whitelist explicitly defined in the config — verify against raw config object], links, code, quotes, tables, and more — but browsers and templates need HTML. Without a conversion engine, every application re-implements ad-hoc string replacement that is fragile, inconsistent across constructs, and unable to handle nesting (a list inside a quote, [a feature whitelist explicitly defined in the config — verify against raw config object] inside a heading, code that must protect its own contents from further markup).

With this engine, a single call converts a whole Markdown document into the corresponding HTML fragment. Block-level structure (headings, paragraphs, lists, fenced code, quotes, tables, thematic breaks) and inline structure (bold, [a feature whitelist explicitly defined in the config — verify against raw config object], italic, strikethrough, inline code, links, images, line breaks) are each handled by a dedicated, composable rule, and the active rule set is configurable so a caller can enable, disable, or restrict features for a given document.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains. This domain has many independent block and inline rules and a configurable pipeline, so a multi-rule, multi-file decomposition is expected.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units. Each block or inline rule should own exactly one construct.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension (adding a new construct rule) but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully (malformed constructs degrade to plain paragraph text rather than crashing). Errors should be modeled properly rather than relying on generic faults.

---

## Core Features

The engine converts a Markdown source string into an HTML fragment. The execution adapter reads a single JSON request object from stdin with a required `markdown` field (the source text) and an optional `config` object, and writes the resulting HTML fragment to stdout.

The optional `config` object selects which construct handlers are active:
- `only`: an array of feature names; when present the active set starts empty and contains exactly these features.
- `enable`: an array of feature names to turn on (added on top of the base set).
- `disable`: an array of feature names to turn off.
- `headline_inline_parsing`: a boolean (default true) controlling whether inline markup inside headings is processed.

When `config` is absent, a default feature set is used: every construct below is active EXCEPT raw HTML pass-through (Feature 12) and the math block (Feature 13), which are off unless explicitly enabled. Valid feature names are: `break_line`, `checklist`, `code_block`, `[a feature whitelist explicitly defined in the config — verify against raw config object]`, `headline`, `horizontal_line`, `html`, `image`, `inline_code`, `italic`, `link`, `ordered_list`, `paragraph`, `quote`, `strikethrough`, `[a feature whitelist explicitly defined in the config — verify against raw config object]`, `table`, `unordered_list`, `latex_block`.

A general rendering note observed across features: a block of running text accumulates a single trailing space before its closing tag, and adjacent text lines within one block are joined by a single space.

---

### Feature 1: Headings

**As a developer**, I want hash-prefixed lines turned into ranked HTML headings, so document section titles render with correct semantic level.

**Expected Behavior / Usage:**

A line that begins with one through six hash marks followed by a space and text becomes an HTML heading element of the matching rank (one hash → rank 1, up to six hashes → rank 6) wrapping the trailing text. A run of more than six hash marks is not a valid heading; such a line falls through to ordinary paragraph rendering.

**Test Cases:** `rcb_tests/public_test_cases/feature1_headings.json`

```json
{
    "description": "Convert ATX-style heading lines into HTML heading elements. A line beginning with one through six hash marks followed by a space and text becomes the correspondingly ranked heading element wrapping that text; a run of more than six hash marks is not a valid heading and the line is rendered as ordinary paragraph text instead.",
    "cases": [
        {"input": {"markdown": "# a\n## a\n### a\n#### a\n##### a\n###### a\n"}, "expected_output": "<h1>a</h1><h2>a</h2><h3>a</h3><h4>a</h4><h5>a</h5><h6>a</h6>"},
        {"input": {"markdown": "####### a\n"}, "expected_output": "<p>####### a </p>"}
    ]
}
```

---

### Feature 2: Paragraphs

**As a developer**, I want loose lines of text grouped into paragraphs, so prose renders as paragraph elements.

**Expected Behavior / Usage:**

Consecutive non-blank lines that do not start any other block are joined into one paragraph element, with a single space between joined lines and a trailing space before the closing tag. A blank line ends the paragraph.

**Test Cases:** `rcb_tests/public_test_cases/feature2_paragraphs.json`

```json
{
    "description": "Group consecutive non-blank text lines into a single paragraph element. Successive lines that are not part of any other block are joined with a single space between them and wrapped as one paragraph; the joined text carries a trailing space before the closing tag.",
    "cases": [
        {"input": {"markdown": "Some text\nand some other text\n"}, "expected_output": "<p>Some text and some other text </p>"}
    ]
}
```

---

### Feature 3: Inline Text Markup

**As a developer**, I want inline spans inside running text converted to their HTML equivalents, so authors can mark up [a feature whitelist explicitly defined in the config — verify against raw config object], strength, strike, and code within a line.

**Expected Behavior / Usage:**

*3.1 Italic — single-asterisk spans*

Text enclosed in single asterisks becomes an italic element wrapping the enclosed text; surrounding text is untouched and multiple spans per line are each converted.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_italic.json`

```json
{
    "description": "Render single-asterisk spans as italic. Text enclosed in single asterisks within a line becomes an italic element around the enclosed text, leaving surrounding text untouched. Multiple such spans on one line are each converted.",
    "cases": [
        {"input": {"markdown": "some text *bla* text testing *it* out\n"}, "expected_output": "<p>some text <i>bla</i> text testing <i>it</i> out </p>"}
    ]
}
```

*3.2 Emphasis — single-underscore spans*

Text enclosed in single underscores becomes an [a feature whitelist explicitly defined in the config — verify against raw config object] element. A span located inside an inline-code region is protected and left verbatim.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_[a feature whitelist explicitly defined in the config — verify against raw config object].json`

```json
{
    "description": "Render single-underscore spans as [a feature whitelist explicitly defined in the config — verify against raw config object]. Text enclosed in single underscores within a line becomes an [a feature whitelist explicitly defined in the config — verify against raw config object] element around the enclosed text. Spans located inside an inline-code region are protected and left verbatim rather than being converted.",
    "cases": [
        {"input": {"markdown": "some text _bla_ text testing _it_ out\n"}, "expected_output": "<p>some text <em>bla</em> text testing <em>it</em> out </p>"},
        {"input": {"markdown": "some text `*bla*` `/**text*/` testing _it_ out\n"}, "expected_output": "<p>some text <code>*bla*</code> <code>/**text*/</code> testing <em>it</em> out </p>"}
    ]
}
```

*3.3 Strong — doubled-marker spans*

A span wrapped in a doubled marker (two asterisks or two underscores) becomes a [a feature whitelist explicitly defined in the config — verify against raw config object] element, while a span wrapped in only a single marker is left for the lighter italic/[a feature whitelist explicitly defined in the config — verify against raw config object] handling and not promoted to [a feature whitelist explicitly defined in the config — verify against raw config object]. When a line also contains an inline-code region, [a feature whitelist explicitly defined in the config — verify against raw config object] promotion on that line is suppressed so the code spans keep their literal markers.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_[a feature whitelist explicitly defined in the config — verify against raw config object].json`

```json
{
    "description": "Render double-asterisk or double-underscore spans as [a feature whitelist explicitly defined in the config — verify against raw config object]. A span wrapped in a doubled marker becomes a [a feature whitelist explicitly defined in the config — verify against raw config object] element, while a span wrapped in only a single marker is left for the lighter [a feature whitelist explicitly defined in the config — verify against raw config object]/italic handling and not promoted to [a feature whitelist explicitly defined in the config — verify against raw config object]. When a line also contains an inline-code region, [a feature whitelist explicitly defined in the config — verify against raw config object] promotion on that line is suppressed so code spans keep their literal markers.",
    "cases": [
        {"input": {"markdown": "some text **bla** text testing **it** out\n"}, "expected_output": "<p>some text <[a feature whitelist explicitly defined in the config — verify against raw config object]>bla</[a feature whitelist explicitly defined in the config — verify against raw config object]> text testing <[a feature whitelist explicitly defined in the config — verify against raw config object]>it</[a feature whitelist explicitly defined in the config — verify against raw config object]> out </p>"},
        {"input": {"markdown": "some text *bla* text testing **it** out\n"}, "expected_output": "<p>some text <i>bla</i> text testing <[a feature whitelist explicitly defined in the config — verify against raw config object]>it</[a feature whitelist explicitly defined in the config — verify against raw config object]> out </p>"}
    ]
}
```

*3.4 Strikethrough — doubled-tilde spans*

Text enclosed in doubled tildes becomes a strikethrough element. A span inside an inline-code region is protected and left verbatim.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_strikethrough.json`

```json
{
    "description": "Render double-tilde spans as struck-through text. Text enclosed in doubled tildes within a line becomes a strikethrough element around the enclosed text. Spans inside an inline-code region are protected and left verbatim.",
    "cases": [
        {"input": {"markdown": "some text ~~bla~~ text testing ~~it~~ out\n"}, "expected_output": "<p>some text <s>bla</s> text testing <s>it</s> out </p>"}
    ]
}
```

*3.5 Inline code — single-backtick spans*

Text enclosed in single backticks becomes an inline code element wrapping the enclosed text; multiple spans per line are each converted.

**Test Cases:** `rcb_tests/public_test_cases/feature3_5_inline_code.json`

```json
{
    "description": "Render single-backtick spans as inline code. Text enclosed in single backticks within a line becomes an inline code element around the enclosed text; multiple such spans on one line are each converted.",
    "cases": [
        {"input": {"markdown": "some text `bla` text testing `it` out\n"}, "expected_output": "<p>some text <code>bla</code> text testing <code>it</code> out </p>"}
    ]
}
```

---

### Feature 4: Links

**As a developer**, I want bracketed link syntax turned into anchor elements, so references render as clickable links.

**Expected Behavior / Usage:**

A bracketed label immediately followed by a parenthesized target becomes an anchor whose visible text is the label and whose target is the parenthesized value. Several links may appear on one line, and a target value may itself contain spaces and parentheses without prematurely terminating the link.

**Test Cases:** `rcb_tests/public_test_cases/feature4_links.json`

```json
{
    "description": "Convert inline link syntax into anchor elements. A bracketed label immediately followed by a parenthesized target becomes an anchor whose visible text is the label and whose target is the parenthesized value. Several links may appear on one line, and a target value may itself contain spaces and parentheses without prematurely terminating the link.",
    "cases": [
        {"input": {"markdown": "Some text [Link Title](http://example.com)\n"}, "expected_output": "<p>Some text <a href=\"http://example.com\">Link Title</a> </p>"},
        {"input": {"markdown": "(This is a [link](/ABC/some file) (the URL will include this).)\n"}, "expected_output": "<p>(This is a <a href=\"/ABC/some file\">link</a> (the URL will include this).) </p>"}
    ]
}
```

---

### Feature 5: Images

**As a developer**, I want exclamation-prefixed link syntax turned into image elements, so embedded images render with a source and alternate text.

**Expected Behavior / Usage:**

A bracketed label preceded by an exclamation mark and immediately followed by a parenthesized target becomes an image element whose source is the parenthesized value and whose alternate text is the label. Several images may appear on one line and are each converted. (Bracketed text without a leading exclamation mark is handled as a link, see Feature 4.)

**Test Cases:** `rcb_tests/public_test_cases/feature5_images.json`

```json
{
    "description": "Convert inline image syntax into image elements. A bracketed label preceded by an exclamation mark and immediately followed by a parenthesized target becomes an image element whose source is the parenthesized value and whose alternate text is the label. Several images may appear on one line and are each converted.",
    "cases": [
        {"input": {"markdown": "Some text ![Image Title](http://example.com/a.png)\n"}, "expected_output": "<p>Some text <img src=\"http://example.com/a.png\" alt=\"Image Title\"/> </p>"}
    ]
}
```

---

### Feature 6: Lists

**As a developer**, I want list syntax converted into nested HTML list markup, so itemized content renders as bullet, numbered, or task lists.

**Expected Behavior / Usage:**

*6.1 Unordered lists*

Consecutive lines beginning with a bullet marker (dash, asterisk, or plus) become list items inside an unordered list. Deeper indentation opens a nested unordered list inside the current item, and items at the same indentation continue the same list regardless of which bullet character was used.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_unordered_list.json`

```json
{
    "description": "Convert bullet lists into unordered list markup. Consecutive lines that begin with a bullet marker (any of the common dash, asterisk, or plus markers) become list items inside an unordered list. Deeper indentation opens a nested unordered list inside the current item, and items at the same indentation continue the same list regardless of which bullet character was used.",
    "cases": [
        {"input": {"markdown": "* a\n* b\n- c\n- d\n+ e\n+ f\n* g\n\n"}, "expected_output": "<ul><li>a</li><li>b</li><li>c</li><li>d</li><li>e</li><li>f</li><li>g</li></ul>"},
        {"input": {"markdown": "* a\n  * d\n  * e\n* b\n  * c\n  + x\n  + y\n  - z\n\n"}, "expected_output": "<ul><li>a<ul><li>d</li><li>e</li></ul></li><li>b<ul><li>c</li><li>x</li><li>y</li><li>z</li></ul></li></ul>"}
    ]
}
```

*6.2 Ordered lists*

Consecutive lines beginning with a number, a period, and a space become items of an ordered list. The actual numeric values are not preserved (only the ordering matters). Deeper indentation opens a nested list, and a continuation line that switches bullet style still extends the current list.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_ordered_list.json`

```json
{
    "description": "Convert numbered lists into ordered list markup. Consecutive lines that begin with a number followed by a period and a space become items of an ordered list; the actual numeric values are not preserved, only the ordering. Deeper indentation opens a nested list, and a mixed continuation that switches bullet style still extends the current list.",
    "cases": [
        {"input": {"markdown": "1. a\n* b\n\n"}, "expected_output": "<ol><li>a</li><li>b</li></ol>"},
        {"input": {"markdown": "1. a\n94. b\n103. c\n\n"}, "expected_output": "<ol><li>a</li><li>b</li><li>c</li></ol>"}
    ]
}
```

*6.3 Task lists (checkboxes)*

Lines beginning with a bullet marker followed by a bracketed flag become list items rendered with a checkbox input inside a label; an empty bracket yields an unchecked box and a filled bracket yields a checked box. The enclosing list carries a `checklist` class, and deeper indentation nests a further checklist inside the parent item.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_checklist.json`

```json
{
    "description": "Convert task-list lines into a checkbox list. Lines beginning with a bullet marker followed by a bracketed flag become list items rendered with a checkbox input inside a label; an empty bracket yields an unchecked box and a filled bracket yields a checked box. The enclosing list carries a checklist class, and deeper indentation nests a further checklist inside the parent item.",
    "cases": [
        {"input": {"markdown": "- [ ] a\n- [x] b\n\n"}, "expected_output": "<ul class=\"checklist\"><li><label><input type=\"checkbox\"/> a</label></li><li><label><input type=\"checkbox\" checked=\"checked\"/> b</label></li></ul>"},
        {"input": {"markdown": "- [ ] a\n  - [ ] d\n  - [ ] e\n- [ ] b\n  - [x] c\n\n"}, "expected_output": "<ul class=\"checklist\"><li><label><input type=\"checkbox\"/> a<ul class=\"checklist\"><li><label><input type=\"checkbox\"/> d</label></li><li><label><input type=\"checkbox\"/> e</label></li></ul></label></li><li><label><input type=\"checkbox\"/> b<ul class=\"checklist\"><li><label><input type=\"checkbox\" checked=\"checked\"/> c</label></li></ul></label></li></ul>"}
    ]
}
```

---

### Feature 7: Fenced Code Block

**As a developer**, I want triple-fence code blocks rendered verbatim, so source snippets keep their exact formatting.

**Expected Behavior / Usage:**

A run of lines delimited by triple-backtick fences becomes a preformatted code block whose inner text is preserved exactly, including its line breaks. Any text following the opening fence on the same line is treated as a language label and emitted as a class on the preformatted element. Inline markup is NOT applied inside a code block.

**Test Cases:** `rcb_tests/public_test_cases/feature7_code_block.json`

```json
{
    "description": "Render fenced code blocks verbatim. A run of lines delimited by triple-backtick fences becomes a preformatted code block whose inner text is preserved exactly, including line breaks. Any text following the opening fence on the same line is treated as a language label and emitted as a class on the preformatted element.",
    "cases": [
        {"input": {"markdown": "```\nsome code\nsome other code\n```\n"}, "expected_output": "<pre><code>\nsome code\nsome other code\n</code></pre>"},
        {"input": {"markdown": "```cpp\nsome code\nsome other code\n```\n"}, "expected_output": "<pre class=\"cpp\"><code>\nsome code\nsome other code\n</code></pre>"}
    ]
}
```

---

### Feature 8: Block Quote

**As a developer**, I want quoted lines rendered as a block quote, so cited content is visually grouped.

**Expected Behavior / Usage:**

Consecutive lines beginning with a greater-than marker form a block quote. A marker-only line acts as a blank separator that splits the quoted content into separate paragraphs inside the quote. Inline markup within the quoted text is still applied, and nested constructs (such as a list) inside the quote are rendered.

**Test Cases:** `rcb_tests/public_test_cases/feature8_block_quote.json`

```json
{
    "description": "Render quoted lines as a block quote. Consecutive lines beginning with a greater-than marker form a block quote; a marker-only line acts as a blank separator that splits the quoted content into separate paragraphs inside the quote. Inline markup within the quoted text is still applied.",
    "cases": [
        {"input": {"markdown": "> a\n> b\n>\n> c\n\n"}, "expected_output": "<blockquote><p>a  b  </p><p>c  </p></blockquote>"}
    ]
}
```

---

### Feature 9: Horizontal Rule

**As a developer**, I want a dashes-only line rendered as a thematic break, so sections can be separated by a rule.

**Expected Behavior / Usage:**

A line consisting of exactly three dashes becomes a thematic-break element. A line that contains three dashes plus extra characters (for example a trailing space) is not a rule and falls through to ordinary paragraph rendering.

**Test Cases:** `rcb_tests/public_test_cases/feature9_horizontal_rule.json`

```json
{
    "description": "Render a horizontal rule from a dashes-only line. A line consisting of exactly three dashes becomes a thematic-break element. A line that contains three dashes but also extra characters such as a trailing space is not a rule and is rendered as ordinary paragraph text.",
    "cases": [
        {"input": {"markdown": "---\n"}, "expected_output": "<hr/>"},
        {"input": {"markdown": "--- \n"}, "expected_output": "<p>---  </p>"}
    ]
}
```

---

### Feature 10: Table

**As a developer**, I want a delimited table block converted to HTML table markup, so tabular data renders with head, body, and footer sections.

**Expected Behavior / Usage:**

A region opened and closed by table fence markers contains row groups whose cells are separated by a vertical bar, with row groups separated by a dash-only divider row. The first row group becomes the table head (header cells), the next becomes the body, and a final group becomes the footer. Inline markup inside cells is still applied.

**Test Cases:** `rcb_tests/public_test_cases/feature10_table.json`

```json
{
    "description": "Render a delimited table into table markup. A region opened and closed by table fence markers contains a header row, a body, and optionally a footer, with cells separated by a vertical bar and row groups separated by a dash-only divider row. The first row group becomes the table head, the next becomes the body, and a final group becomes the footer; inline markup inside cells is still applied.",
    "cases": [
        {"input": {"markdown": "|table>\nLeft header|middle header|last header\n- | - | -\ncell 1|cell 2|cell 3\ncell 4|cell 5|cell 6\n- | - | -\nfoot a|foot b|foot c\n|<table\n"}, "expected_output": "<table><thead><tr><th>Left header</th><th>middle header</th><th>last header</th></tr></thead><tbody><tr><td>cell 1</td><td>cell 2</td><td>cell 3</td></tr><tr><td>cell 4</td><td>cell 5</td><td>cell 6</td></tr></tbody><tfoot><tr><td>foot a</td><td>foot b</td><td>foot c</td></tr></tfoot></table>"}
    ]
}
```

---

### Feature 11: Configurable Pipeline & Whole-Document Conversion

**As a developer**, I want to convert a whole document and to control which construct handlers are active, so I can tailor the output to a use case.

**Expected Behavior / Usage:**

*11.1 Default whole-document conversion*

With the default feature set, a complete document mixing every block and inline construct is converted block by block; the output is the concatenation of each block's HTML in document order.

**Test Cases:** `rcb_tests/public_test_cases/feature11_1_full_document.json`

```json
{
    "description": "Convert a complete multi-feature document with the default feature set enabled. The input mixes headings, paragraphs, nested lists, fenced code, a block quote containing a list, inline markup, a link, an image, a thematic break, a checklist, and a table; the output is the concatenation of each block's HTML in document order.",
    "cases": [
        {"input": {"markdown": "# This is a test\n\nThis should result in a praragraph\nit's that simple.\n\n* an *unordered* list\n  * with some **hierarchy**\n    1. and an _ordered_\n    * list\n    * directly\n  * inside\n\n```\nvar c = 'blub';\n```\n\n> A Quote\n>\n> With some ~~text~~  blocks inside\n>\n> * even a list\n> * should be\n> * possible\n>\n\nAnd well `inline code` should also work.\n\n## Another Headline\n\nAnd not to forget [link to progsource](http://progsource.de) should work.\nAnd well - let's see how an image would be shown:\n\n![an image](http://progsource.de/img/progsource.png)\n\n---\n\n<a name=\"to top\"></a>\n\n### and more headlines\n\n- [ ] how\n- [ ] about\n  - [ ] a\n  - [x] nice\n- [x] check\n- [ ] list\n\n#### even a table\n\n|table>\nLeft header|middle header|last header\n- | - | -\ncell 1|cell **2**|cell 3\ncell 4|cell 5|cell 6\n- | - | -\nfoot a|foot b|foot c\n|<table\n\n##### h5\n###### h6\n\n"}, "expected_output": "<h1>This is a test</h1><p>This should result in a praragraph it's that simple. </p><ul><li>an <i>unordered</i> list<ul><li>with some <[a feature whitelist explicitly defined in the config — verify against raw config object]>hierarchy</[a feature whitelist explicitly defined in the config — verify against raw config object]><ol><li>and an <em>ordered</em></li><li>list</li><li>directly</li></ol></li><li>inside</li></ul></li></ul><pre><code>\nvar c = 'blub';\n</code></pre><blockquote><p>A Quote  </p><p>With some <s>text</s>  blocks inside  </p><ul><li>even a list </li><li>should be </li><li>possible </li></ul></blockquote><p>And well <code>inline code</code> should also work. </p><h2>Another Headline</h2><p>And not to forget <a href=\"http://progsource.de\">link to progsource</a> should work. And well - let's see how an image would be shown: </p><p><img src=\"http://progsource.de/img/progsource.png\" alt=\"an image\"/> </p><hr/><p><a name=\"to top\"></a> </p><h3>and more headlines</h3><ul class=\"checklist\"><li><label><input type=\"checkbox\"/> how</label></li><li><label><input type=\"checkbox\"/> about<ul class=\"checklist\"><li><label><input type=\"checkbox\"/> a</label></li><li><label><input type=\"checkbox\" checked=\"checked\"/> nice</label></li></ul></label></li><li><label><input type=\"checkbox\" checked=\"checked\"/> check</label></li><li><label><input type=\"checkbox\"/> list</label></li></ul><h4>even a table</h4><table><thead><tr><th>Left header</th><th>middle header</th><th>last header</th></tr></thead><tbody><tr><td>cell 1</td><td>cell <[a feature whitelist explicitly defined in the config — verify against raw config object]>2</[a feature whitelist explicitly defined in the config — verify against raw config object]></td><td>cell 3</td></tr><tr><td>cell 4</td><td>cell 5</td><td>cell 6</td></tr></tbody><tfoot><tr><td>foot a</td><td>foot b</td><td>foot c</td></tr></tfoot></table><h5>h5</h5><h6>h6</h6>"}
    ]
}
```

*11.2 Disabling and enabling features*

Disabling a feature leaves its construct as literal text, and enabling raw HTML pass-through (Feature 12) changes how standalone HTML lines are emitted. Disabling single-underscore [a feature whitelist explicitly defined in the config — verify against raw config object] leaves underscore spans literal; enabling HTML pass-through emits a standalone HTML line as-is rather than wrapping it in a paragraph.

**Test Cases:** `rcb_tests/public_test_cases/feature11_2_disabled_features.json`

```json
{
    "description": "Convert the same complete document but with the single-underscore [a feature whitelist explicitly defined in the config — verify against raw config object] handling turned off and raw inline HTML pass-through turned on. With [a feature whitelist explicitly defined in the config — verify against raw config object] disabled, underscore spans are left as literal text; with HTML pass-through enabled, a standalone HTML line is emitted as-is instead of being wrapped in a paragraph.",
    "cases": [
        {"input": {"markdown": "# This is a test\n\nThis should result in a praragraph\nit's that simple.\n\n* an *unordered* list\n  * with some **hierarchy**\n    1. and an _ordered_\n    * list\n    * directly\n  * inside\n\n```\nvar c = 'blub';\n```\n\n> A Quote\n>\n> With some ~~text~~  blocks inside\n>\n> * even a list\n> * should be\n> * possible\n>\n\nAnd well `inline code` should also work.\n\n## Another Headline\n\nAnd not to forget [link to progsource](http://progsource.de) should work.\nAnd well - let's see how an image would be shown:\n\n![an image](http://progsource.de/img/progsource.png)\n\n---\n\n<a name=\"to top\"></a>\n\n### and more headlines\n\n- [ ] how\n- [ ] about\n  - [ ] a\n  - [x] nice\n- [x] check\n- [ ] list\n\n#### even a table\n\n|table>\nLeft header|middle header|last header\n- | - | -\ncell 1|cell **2**|cell 3\ncell 4|cell 5|cell 6\n- | - | -\nfoot a|foot b|foot c\n|<table\n\n##### h5\n###### h6\n\n", "config": {"disable": ["[a feature whitelist explicitly defined in the config — verify against raw config object]"], "enable": ["html"]}}, "expected_output": "<h1>This is a test</h1><p>This should result in a praragraph it's that simple. </p><ul><li>an <i>unordered</i> list<ul><li>with some <[a feature whitelist explicitly defined in the config — verify against raw config object]>hierarchy</[a feature whitelist explicitly defined in the config — verify against raw config object]><ol><li>and an _ordered_</li><li>list</li><li>directly</li></ol></li><li>inside</li></ul></li></ul><pre><code>\nvar c = 'blub';\n</code></pre><blockquote><p>A Quote  </p><p>With some <s>text</s>  blocks inside  </p><ul><li>even a list </li><li>should be </li><li>possible </li></ul></blockquote><p>And well <code>inline code</code> should also work. </p><h2>Another Headline</h2><p>And not to forget <a href=\"http://progsource.de\">link to progsource</a> should work. And well - let's see how an image would be shown: </p><p><img src=\"http://progsource.de/img/progsource.png\" alt=\"an image\"/> </p><hr/><a name=\"to top\"></a><h3>and more headlines</h3><ul class=\"checklist\"><li><label><input type=\"checkbox\"/> how</label></li><li><label><input type=\"checkbox\"/> about<ul class=\"checklist\"><li><label><input type=\"checkbox\"/> a</label></li><li><label><input type=\"checkbox\" checked=\"checked\"/> nice</label></li></ul></label></li><li><label><input type=\"checkbox\" checked=\"checked\"/> check</label></li><li><label><input type=\"checkbox\"/> list</label></li></ul><h4>even a table</h4><table><thead><tr><th>Left header</th><th>middle header</th><th>last header</th></tr></thead><tbody><tr><td>cell 1</td><td>cell <[a feature whitelist explicitly defined in the config — verify against raw config object]>2</[a feature whitelist explicitly defined in the config — verify against raw config object]></td><td>cell 3</td></tr><tr><td>cell 4</td><td>cell 5</td><td>cell 6</td></tr></tbody><tfoot><tr><td>foot a</td><td>foot b</td><td>foot c</td></tr></tfoot></table><h5>h5</h5><h6>h6</h6>"}
    ]
}
```

*11.3 Restricting to a minimal feature set*

With `only` naming just the bold and [a feature whitelist explicitly defined in the config — verify against raw config object] inline handlers and every block-level handler disabled, no block structure is produced: the document is flattened so each source line is separated by a line-break element, while doubled-marker spans still become bold and single-underscore spans still become [a feature whitelist explicitly defined in the config — verify against raw config object].

**Test Cases:** `rcb_tests/public_test_cases/feature11_3_minimal_feature_set.json`

```json
{
    "description": "Convert the same complete document but with only the bold and [a feature whitelist explicitly defined in the config — verify against raw config object] inline handlers enabled and every block-level handler disabled. No block structure is produced; the document is flattened so each source line is separated by a line-break element, while doubled-marker spans still become bold and single-underscore spans still become [a feature whitelist explicitly defined in the config — verify against raw config object].",
    "cases": [
        {"input": {"markdown": "# This is a test\n\nThis should result in a praragraph\nit's that simple.\n\n* an *unordered* list\n  * with some **hierarchy**\n    1. and an _ordered_\n    * list\n    * directly\n  * inside\n\n```\nvar c = 'blub';\n```\n\n> A Quote\n>\n> With some ~~text~~  blocks inside\n>\n> * even a list\n> * should be\n> * possible\n>\n\nAnd well `inline code` should also work.\n\n## Another Headline\n\nAnd not to forget [link to progsource](http://progsource.de) should work.\nAnd well - let's see how an image would be shown:\n\n![an image](http://progsource.de/img/progsource.png)\n\n---\n\n<a name=\"to top\"></a>\n\n### and more headlines\n\n- [ ] how\n- [ ] about\n  - [ ] a\n  - [x] nice\n- [x] check\n- [ ] list\n\n#### even a table\n\n|table>\nLeft header|middle header|last header\n- | - | -\ncell 1|cell **2**|cell 3\ncell 4|cell 5|cell 6\n- | - | -\nfoot a|foot b|foot c\n|<table\n\n##### h5\n###### h6\n\n", "config": {"only": ["[a feature whitelist explicitly defined in the config — verify against raw config object]", "[a feature whitelist explicitly defined in the config — verify against raw config object]"]}}, "expected_output": "# This is a test <br/>This should result in a praragraph it's that simple. <br/>* an *unordered* list   * with some <[a feature whitelist explicitly defined in the config — verify against raw config object]>hierarchy</[a feature whitelist explicitly defined in the config — verify against raw config object]>     1. and an <em>ordered</em>     * list     * directly   * inside <br/>``` var c = 'blub'; ``` <br/>> A Quote > > With some ~~text~~  blocks inside > > * even a list > * should be > * possible > <br/>And well `inline code` should also work. <br/>## Another Headline <br/>And not to forget [link to progsource](http://progsource.de) should work. And well - let's see how an image would be shown: <br/>![an image](http://progsource.de/img/progsource.png) <br/>--- <br/><a name=\"to top\"></a> <br/>### and more headlines <br/>- [ ] how - [ ] about   - [ ] a   - [x] nice - [x] check - [ ] list <br/>#### even a table <br/>|table> Left header|middle header|last header - | - | - cell 1|cell <[a feature whitelist explicitly defined in the config — verify against raw config object]>2</[a feature whitelist explicitly defined in the config — verify against raw config object]>|cell 3 cell 4|cell 5|cell 6 - | - | - foot a|foot b|foot c |<table <br/>##### h5 ###### h6 <br/>"}
    ]
}
```

*11.4 Inline markup inside headings*

By default a heading's text is run through inline handling, so a doubled-marker span inside a heading becomes bold. When `headline_inline_parsing` is false, the heading text is emitted literally with its markers intact.

**Test Cases:** `rcb_tests/public_test_cases/feature11_4_headline_inline.json`

```json
{
    "description": "Control whether inline markup inside a heading is processed. By default a heading's text is run through inline handling, so a doubled-marker span inside the heading becomes bold; when inline processing inside headings is turned off, the heading text is emitted literally with its markers intact.",
    "cases": [
        {"input": {"markdown": "# Some **test** markdown\n"}, "expected_output": "<h1>Some <[a feature whitelist explicitly defined in the config — verify against raw config object]>test</[a feature whitelist explicitly defined in the config — verify against raw config object]> markdown</h1>"},
        {"input": {"markdown": "# Some **test** markdown\n", "config": {"headline_inline_parsing": false}}, "expected_output": "<h1>Some **test** markdown</h1>"}
    ]
}
```

---

### Feature 12: Raw HTML Pass-Through

**As a developer**, I want lines that already contain HTML emitted verbatim when this handler is enabled, so authors can drop raw markup into a document.

**Expected Behavior / Usage:**

This handler is off in the default feature set and must be enabled via `enable: ["html"]`. When enabled, a line that begins with an HTML tag starts a raw block whose lines are passed through verbatim (multiple lines joined with a single space), while ordinary text outside such blocks is still wrapped as a paragraph.

**Test Cases:** `rcb_tests/public_test_cases/feature12_html_passthrough.json`

```json
{
    "description": "Emit raw HTML blocks unchanged when HTML pass-through is enabled. With this handler enabled, a line that begins with an HTML tag starts a raw block whose lines are passed through verbatim (joined with spaces across multiple lines), while ordinary text outside such blocks is still wrapped as a paragraph.",
    "cases": [
        {"input": {"markdown": "some text in a paragraph\n\n<div> some HTML</div>\n\n<div>more\nHTML\n</div>\n", "config": {"enable": ["html"]}}, "expected_output": "<p>some text in a paragraph </p><div> some HTML</div><div>more HTML </div>"}
    ]
}
```

---

### Feature 13: Math Block Pass-Through

**As a developer**, I want math blocks emitted verbatim when this handler is enabled, so a downstream math renderer can process them.

**Expected Behavior / Usage:**

This handler is off in the default feature set and must be enabled via `enable: ["latex_block"]`. When enabled, a line opened and closed with a doubled dollar delimiter on the same line is emitted exactly as written (including the delimiters), followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature13_latex_block.json`

```json
{
    "description": "Pass a math block through verbatim when the math handler is enabled. A line opened and closed with a doubled dollar delimiter on the same line is emitted exactly as written (including the delimiters) followed by a newline, so a downstream math renderer can process it; the handler is off in the default feature set and must be explicitly enabled.",
    "cases": [
        {"input": {"markdown": "$$x = {-b \\pm \\sqrt{b^2-4ac} \\over 2a}.$$\n", "config": {"enable": ["latex_block"]}}, "expected_output": "$$x = {-b \\pm \\sqrt{b^2-4ac} \\over 2a}.$$\n"}
    ]
}
```

---

### Feature 14: Hard Line Break

**As a developer**, I want an embedded carriage return turned into a line-break element, so text can wrap to a new visual line within a block.

**Expected Behavior / Usage:**

Within a single logical line, a carriage-return character is replaced by a line-break element so the surrounding text is split across visual lines inside the same block.

**Test Cases:** `rcb_tests/public_test_cases/feature14_line_break.json`

```json
{
    "description": "Convert an embedded carriage return into a line-break element. Within a single logical line, a carriage-return character is replaced by a line-break element so the surrounding text is split across visual lines inside the same block.",
    "cases": [
        {"input": {"markdown": "Test the text\rtest text to check\rcheck testing to text.\n"}, "expected_output": "<p>Test the text<br>test text to check<br>check testing to text. </p>"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-rule codebase implementing the Markdown-to-HTML conversion above. Each block and inline construct should be its own cohesive rule, composed by a pipeline that the configuration can enable, disable, or restrict. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request object from stdin (a required `markdown` source string plus an optional `config` object) and prints the resulting HTML fragment to stdout, matching the per-feature contracts above. The `config` object supports `only`, `enable`, `disable` (arrays of the feature names listed under "Core Features") and a boolean `headline_inline_parsing`. When `config` is absent the default feature set is used (all constructs except raw HTML pass-through and the math block). On a malformed request the adapter prints a single neutral line `error=invalid_request`.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- check the checkbox helper path or board folder for list types
- grep for 'no trailing' or check the pattern validator logic
