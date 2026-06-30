## Product Requirement Document

# Indentation-Based HTML Template Engine — Compile Concise Outlines into HTML

## Project Goal

Build a template engine that turns a terse, whitespace-significant outline into HTML, so developers can author markup as an indentation tree (one element per line, with shortcuts for ids/classes and inline expressions) instead of hand-writing verbose, easy-to-mismatch angle-bracket tags.

---

## Background & Problem

Writing HTML by hand is repetitive and error-prone: every element needs an opening and a matching closing tag, nesting depth is only implied by manual indentation, and embedding dynamic values means interleaving markup with escaping logic. Small mistakes (a missing `</div>`, an unescaped user string) are easy to make and hard to spot.

This engine replaces the angle-bracket syntax with an indentation-based outline. Each line names one element; nesting is expressed purely by indentation, so closing tags are inferred automatically. Attributes, ids, and classes have compact shortcut forms; dynamic values are produced by dedicated output indicators that escape by default; and malformed input is rejected up front with a precise, position-aware diagnostic instead of silently producing broken markup. The result is a compact source language that compiles to exactly the HTML the author intended.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains. This is a non-trivial domain (lexing an indentation-sensitive grammar, an attribute/value model, output formatting, and error reporting): prefer a clear multi-module layout.

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

## Adapter Input Contract

Every case feeds the execution adapter ONE JSON object on stdin and expects the rendered document (or a normalized error record) on stdout. The object has these fields:

- `template` (string, required): the source outline to compile and render.
- `options` (object, optional): rendering configuration flags (e.g. an output-`format` selector, a `pretty` flag, a `disable_escape` flag, an attribute join `merge_attrs` map). Absent keys take their defaults.
- `locals` (object, optional): named values made available to expressions inside the template; a name used in the template resolves to the matching local.
- `yield` (string, optional): the content returned when the template asks for a yielded block.

Output is the raw rendered string with no added metadata. Elements render with no whitespace between them unless pretty-printing is enabled. Errors are rendered as a neutral, line-oriented record (see the error features).

---

## Core Features

### Feature 1: Element Structure From Indentation

**As a developer**, I want nesting to come from indentation alone, so I can write markup as an outline and never manage closing tags.

**Expected Behavior / Usage:**

A line that is indented more deeply than the previous line becomes that line's child; lines at the same indentation are siblings; a child block ends where the indentation returns. The leading word of a line is an element name and maps to an HTML tag of the same name; remaining text on the line becomes the element's inline content. A leading blank line is ignored, and a blank line between two siblings does not merge them. A tag name may contain a namespace separator (a colon), preserved verbatim. Output concatenates elements with no separating whitespace.

**Test Cases:** `rcb_tests/public_test_cases/feature1_tag_nesting.json`

```json
{
  "description": "Templates are written as an indentation-based outline. A line that is indented deeper than the previous line becomes that line's child element; siblings share the same indentation. Each bare word at the start of a line is an element name and maps directly to an HTML tag of the same name. A leading blank line is ignored, and a blank line between two siblings does not merge them. A tag name may contain a namespace separator (a colon), which is preserved verbatim. Elements are concatenated with no whitespace between them.",
  "cases": [
    {
      "input": { "template": "\n[a specific open element tag — verify with the HTML schema]\n  head\n    title Simple Test Title\n  body \n    p Hello World, meet Slim.\n" },
      "expected_output": "<[a specific open element tag — verify with the HTML schema]><head><title>Simple Test Title</title></head><body><p>Hello World, meet Slim.</p></body></[a specific open element tag — verify with the HTML schema]>"
    },
    {
      "input": { "template": "\np Hello\n\np World\n" },
      "expected_output": "<p>Hello</p><p>World</p>"
    }
  ]
}
```

---

### Feature 2: Id & Class Shortcuts

**As a developer**, I want compact prefixes for ids and classes, so I can attach the most common attributes without writing them out.

**Expected Behavior / Usage:**

A token beginning with `#` sets the element's id; a token beginning with `.` adds a class, and several class shortcuts accumulate into a space-separated class list. When a shortcut appears with no explicit tag name in front of it, the element defaults to `div`. A trailing colon on an element performs inline block expansion: the element written after the colon, on the same line, becomes its single nested child.

**Test Cases:** `rcb_tests/public_test_cases/feature2_shortcuts.json`

```json
{
  "description": "Shortcut prefixes attach attributes to an element. A token beginning with \"#\" sets the id; a token beginning with \".\" adds a class (multiple class shortcuts accumulate, space-separated). When a shortcut is not preceded by an explicit tag name, the element defaults to a div. A trailing colon on an element performs inline block expansion: the element after the colon (on the same line) becomes the single nested child.",
  "cases": [
    {
      "input": { "template": "\nh1#title This is my title\n" },
      "expected_output": "<h1 id=\"title\">This is my title</h1>"
    },
    {
      "input": { "template": "\n#notice.hello.world Text\n" },
      "expected_output": "<div class=\"hello world\" id=\"notice\">Text</div>"
    }
  ]
}
```

---

### Feature 3: Attributes

**As a developer**, I want a rich, predictable attribute model, so element configuration is concise yet unambiguous.

**Expected Behavior / Usage:**

*3.1 Static attributes & delimiters — name/value pairs with optional wrapping and stable ordering*

Static attributes follow the tag as `name="value"` or `name='value'` pairs. The whole list may optionally be wrapped in a delimiter pair — parentheses or square brackets. Attribute names may contain dashes, and runs of extra spaces between attributes are tolerated. Whatever order attributes are written in, they are emitted sorted alphabetically by name.

**Test Cases:** `rcb_tests/public_test_cases/feature3_static_attributes.json`

```json
{
  "description": "Static attributes are written after the tag as name=\"value\" or name='value' pairs. The whole attribute list may optionally be wrapped in a delimiter pair: parentheses or square brackets. Attribute names may contain dashes. Several spaces between attributes are tolerated. No matter what order attributes are supplied, they are emitted sorted alphabetically by name.",
  "cases": [
    {
      "input": { "template": "\np(id=\"marvin\" class=\"martian\" data-info=\"Illudium Q-36\") Text\n" },
      "expected_output": "<p class=\"martian\" data-info=\"Illudium Q-36\" id=\"marvin\">Text</p>"
    },
    {
      "input": { "template": "\np data-info=\"Illudium Q-36\" Text\n" },
      "expected_output": "<p data-info=\"Illudium Q-36\">Text</p>"
    }
  ]
}
```

*3.2 Boolean attribute semantics — true/false/nil/string handling*

An attribute value is interpreted by its type. A literal `true` renders the attribute with an empty value (`name=""`). A `false` or `nil` value omits the attribute entirely. A string value is emitted verbatim. Inside a delimiter group, a bare attribute name with no value is treated as `true`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_boolean_attributes.json`

```json
{
  "description": "Attribute values are interpreted by type. A literal true renders the attribute with an empty value (name=\"\"). A false or nil value omits the attribute entirely. A string value is rendered verbatim. Inside a delimiter group a bare attribute name (with no value) is treated as true.",
  "cases": [
    {
      "input": { "template": "\n- cond=true\noption selected=true Text\noption selected=cond Text2\n" },
      "expected_output": "<option selected=\"\">Text</option><option selected=\"\">Text2</option>"
    },
    {
      "input": { "template": "\n- cond=false\noption selected=false Text\noption selected=cond Text2\n" },
      "expected_output": "<option>Text</option><option>Text2</option>"
    }
  ]
}
```

*3.3 Class merging — multiple sources collapse into one class list*

When several class values target the same element they merge into a single space-separated class attribute, preserving appearance order. A `nil` class value and an empty-string class value are dropped. An array value is flattened (including nested arrays) and each element stringified; a comma-separated list of values merges the same way.

**Test Cases:** `rcb_tests/public_test_cases/feature5_class_merging.json`

```json
{
  "description": "When several class values target the same element they are merged into one space-separated class attribute, preserving the order they appear. A nil class value and an empty-string class value are dropped. An array value is flattened (including nested arrays) and each element stringified; a comma-separated list of values is merged the same way.",
  "cases": [
    {
      "input": { "template": "\n.alpha class=\"beta\" class=nil class=\"gamma\" Test it\n" },
      "expected_output": "<div class=\"alpha beta gamma\">Test it</div>"
    }
  ]
}
```

*3.4 Identifier merging — a configurable join map combines repeated ids*

Repeated attribute values can be combined according to a join map supplied in `options`. When that map declares a separator for the id attribute, an id coming from a shortcut and an explicit id attribute on the same element are concatenated into one value joined by that separator.

**Test Cases:** `rcb_tests/public_test_cases/feature6_id_merging.json`

```json
{
  "description": "Repeated attribute values can be combined according to a configurable join map supplied in the options. When the map declares a separator for the id attribute, an id coming from a shortcut and an explicit id attribute on the same element are concatenated into a single value joined by that separator.",
  "cases": [
    {
      "input": {
        "template": "\n#alpha id=\"beta\" Test it\n",
        "options": { "merge_attrs": { "class": " ", "id": "_" } }
      },
      "expected_output": "<div id=\"alpha_beta\">Test it</div>"
    }
  ]
}
```

*3.5 Hash-valued data attributes — nested maps flatten into dashed names*

A hash-valued attribute expands into multiple flattened attributes. Each leaf entry becomes a separate attribute named `<prefix>-<key>`; a nested hash deepens the dash-joined name one level per nesting. By default underscores inside keys are kept as-is; an option can additionally rewrite key underscores to dashes. The expanded attributes are emitted in sorted order alongside any others.

**Test Cases:** `rcb_tests/public_test_cases/feature7_data_attributes.json`

```json
{
  "description": "A hash-valued attribute expands into multiple flattened attributes. Each leaf entry becomes a separate attribute named \"<prefix>-<key>\"; a nested hash deepens the dash-joined name one level per nesting. By default underscores inside keys are kept as-is; an option can additionally rewrite underscores in keys to dashes. The expanded attributes are emitted in sorted order alongside any other attributes.",
  "cases": [
    {
      "input": { "template": "\n.alpha data={a: 'alpha', b: 'beta', c_d: 'gamma', c: {e: 'epsilon'}}\n" },
      "expected_output": "<div class=\"alpha\" data-a=\"alpha\" data-b=\"beta\" data-c-e=\"epsilon\" data-c_d=\"gamma\"></div>"
    }
  ]
}
```

*3.6 Splat attributes — expand a key/value collection inline*

A `*` followed by an expression that evaluates to a collection of key/value pairs injects each pair as an attribute on the element. Splat attributes merge with explicit attributes and with id/class shortcuts, and the complete set is emitted in sorted order. Boolean and empty values among the splatted pairs follow the same rendering rules as ordinary attributes. The splat expression may reference variables supplied in `locals`.

**Test Cases:** `rcb_tests/public_test_cases/feature15_splat.json`

```json
{
  "description": "A \"*\" followed by an expression that evaluates to a collection of key/value pairs injects each pair as an attribute on the element. Splat attributes merge with explicit attributes and with id/class shortcuts, and the complete attribute set is emitted in sorted order. Boolean and empty values among the splatted pairs follow the same rendering rules as ordinary attributes. The splat expression may reference variables supplied to the template.",
  "cases": [
    {
      "input": {
        "template": "\n*h\np*h\n",
        "locals": { "h": { "a": "The letter a", "b": "The letter b" } }
      },
      "expected_output": "<div a=\"The letter a\" b=\"The letter b\"></div><p a=\"The letter a\" b=\"The letter b\"></p>"
    },
    {
      "input": { "template": "\n*{disabled: true, empty1: false, nonempty: '', empty2: nil} This is my title\n" },
      "expected_output": "<div disabled=\"\" nonempty=\"\">This is my title</div>"
    }
  ]
}
```

---

### Feature 4: Verbatim Text Blocks

**As a developer**, I want to drop in literal multi-line text, so I can include prose and pre-shaped content without per-line markup.

**Expected Behavior / Usage:**

A line whose first non-space character is `|` begins a verbatim text block: the following more-indented lines are emitted literally, with their relative indentation preserved and successive lines joined by a newline. A line beginning with `'` behaves identically but appends a single trailing space, so adjacent inline markup flows naturally. HTML special characters inside a text block are emitted unescaped.

**Test Cases:** `rcb_tests/public_test_cases/feature8_text_blocks.json`

```json
{
  "description": "A line whose first non-space character is \"|\" begins a verbatim text block: the following more-indented lines are emitted literally, with their relative indentation preserved and successive lines joined by a newline. A line beginning with \"'\" behaves identically but appends a single trailing space so adjacent inline markup flows naturally. HTML special characters inside a text block are emitted unescaped.",
  "cases": [
    {
      "input": { "template": "\np\n  |\n   Lorem ipsum dolor sit amet, consectetur adipiscing elit.\n" },
      "expected_output": "<p>Lorem ipsum dolor sit amet, consectetur adipiscing elit.</p>"
    },
    {
      "input": { "template": "\np\n |\n  This is line one.\n   This is line two.\n    This is line three.\n     This is line four.\np This is a new paragraph.\n" },
      "expected_output": "<p>This is line one.\n This is line two.\n  This is line three.\n   This is line four.</p><p>This is a new paragraph.</p>"
    }
  ]
}
```

---

### Feature 5: Dynamic Output

**As a developer**, I want to emit evaluated expressions with safe defaults, so dynamic content is escaped unless I explicitly opt out.

**Expected Behavior / Usage:**

An output segment is introduced by `=` (evaluate the trailing expression and emit its result HTML-escaped) or `==` (emit without escaping). Appending `>` to the indicator (`=>` or `==>`) emits a single trailing space after the value. A configuration flag can globally turn off escaping for `=`. The expression to the right is ordinary host-language code and may reference variables supplied in `locals`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_dynamic_output.json`

```json
{
  "description": "An output line is introduced by \"=\" (evaluate the trailing expression and emit it HTML-escaped) or \"==\" (emit it without escaping). Appending \">\" to the indicator (\"=>\" or \"==>\") emits a single trailing space after the value. A configuration flag can globally turn off escaping for \"=\". The expression to the right is ordinary host-language code and may reference variables supplied to the template.",
  "cases": [
    {
      "input": { "template": "\n= \"<p>Hello</p>\"\n== \"<p>World</p>\"\n" },
      "expected_output": "&lt;p&gt;Hello&lt;/p&gt;<p>World</p>"
    },
    {
      "input": { "template": "\np\n  => \"Hi\"\n" },
      "expected_output": "<p>Hi </p>"
    }
  ]
}
```

---

### Feature 6: Inline Interpolation

**As a developer**, I want to splice expressions into text and attribute values, so I can build strings without breaking out of a line.

**Expected Behavior / Usage:**

Interpolation embeds an evaluated expression inside text or quoted attribute values. `#{...}` inserts the result HTML-escaped; `#{{...}}` inserts it without escaping. A backslash before the construct (`\#{...}`) suppresses evaluation and emits the literal characters. The embedded expression may reference variables supplied in `locals`.

**Test Cases:** `rcb_tests/public_test_cases/feature10_interpolation.json`

```json
{
  "description": "Interpolation embeds an evaluated expression inside text or quoted attribute values. \"#{...}\" inserts the result HTML-escaped; \"#{{...}}\" inserts it without escaping. A backslash before the construct (\"\\#{...}\") suppresses evaluation and emits the literal characters. The embedded expression may reference variables supplied to the template.",
  "cases": [
    {
      "input": {
        "template": "\n| #{value}\n",
        "locals": { "value": "<script>do_something_evil();</script>" }
      },
      "expected_output": "&lt;script&gt;do_something_evil();&lt;/script&gt;"
    },
    {
      "input": {
        "template": "\n| #{{value}}\n",
        "locals": { "value": "<script>do_something_evil();</script>" }
      },
      "expected_output": "<script>do_something_evil();</script>"
    }
  ]
}
```

---

### Feature 7: Embedded Control Flow

**As a developer**, I want conditionals, selection, and loops to drive which nested content renders, so the template can react to data.

**Expected Behavior / Usage:**

A line beginning with `-` carries control code that emits nothing itself but governs the nested block beneath it. Supported forms include conditional branches (`if` / `else` / `unless`), `case`/`when` selection, and loops that repeat their nested content. A variable assigned on a `-` line can be emitted later with `=`. As everywhere else, block extents come from indentation.

**Test Cases:** `rcb_tests/public_test_cases/feature11_control_flow.json`

```json
{
  "description": "Lines beginning with \"-\" carry control code that emits nothing itself but governs the nested block beneath it. Supported forms include conditional branches (if / else / unless), case/when selection, and loops that repeat their nested content. A variable assigned on a \"-\" line can be emitted later with \"=\". Block extents are taken from indentation.",
  "cases": [
    {
      "input": { "template": "\ndiv\n  - if false\n      p The first paragraph\n  - else\n      p The second paragraph\n" },
      "expected_output": "<div><p>The second paragraph</p></div>"
    },
    {
      "input": { "template": "\np\n  - 3.times do\n    | Hey!\n" },
      "expected_output": "<p>Hey!Hey!Hey!</p>"
    }
  ]
}
```

---

### Feature 8: Comments

**As a developer**, I want a few comment forms, so I can leave notes, ship real HTML comments, or guard markup with conditional comments.

**Expected Behavior / Usage:**

A line beginning with `/` is a code comment: it and its nested block produce no output. `/!` begins an HTML comment whose body — nested lines joined by newlines — is wrapped in `<!-- ... -->`. `/[ condition ]` begins a conditional comment that wraps its nested markup in `<!--[condition]> ... <![endif]-->`.

**Test Cases:** `rcb_tests/public_test_cases/feature12_comments.json`

```json
{
  "description": "Comment lines control whether content reaches the output. A line beginning with \"/\" is a code comment: it and its nested block are dropped entirely. \"/!\" begins an HTML comment whose body (nested lines joined by newlines) is wrapped in <!-- ... -->. \"/[ condition ]\" begins a conditional comment that wraps its nested markup in <!--[condition]> ... <![endif]-->.",
  "cases": [
    {
      "input": { "template": "\np Hello\n/ This is a comment\n  Another comment\np World\n" },
      "expected_output": "<p>Hello</p><p>World</p>"
    },
    {
      "input": { "template": "\np Hello\n/! This is a comment\n\n   Another comment\np World\n" },
      "expected_output": "<p>Hello</p><!--This is a comment\n\nAnother comment--><p>World</p>"
    }
  ]
}
```

---

### Feature 9: Doctype Declarations

**As a developer**, I want a short doctype keyword that expands to the correct declaration, so I do not have to memorize long doctype strings.

**Expected Behavior / Usage:**

A `doctype` line maps a short identifier to a full document type declaration. The active output `format` selects between the HTML and XHTML serializations. The identifiers `5` and `[a specific open element tag — verify with the HTML schema]` both yield the HTML5 doctype, while numeric variants such as `1.1` yield the matching XHTML public identifier string.

**Test Cases:** `rcb_tests/public_test_cases/feature13_doctype.json`

```json
{
  "description": "A \"doctype\" line maps a short identifier to a full document type declaration. The active output format selects between the HTML and XHTML serializations. The identifiers \"5\" and \"[a specific open element tag — verify with the HTML schema]\" both yield the HTML5 doctype, while numeric variants such as \"1.1\" yield the matching XHTML public identifier string.",
  "cases": [
    {
      "input": {
        "template": "\ndoctype 1.1\n[a specific open element tag — verify with the HTML schema]\n",
        "options": { "format": "x[a specific open element tag — verify with the HTML schema]" }
      },
      "expected_output": "<!DOCTYPE [a specific open element tag — verify with the HTML schema] PUBLIC \"-//W3C//DTD XHTML 1.1//EN\" \"http://www.w3.org/TR/x[a specific open element tag — verify with the HTML schema]11/DTD/x[a specific open element tag — verify with the HTML schema]11.dtd\"><[a specific open element tag — verify with the HTML schema]></[a specific open element tag — verify with the HTML schema]>"
    },
    {
      "input": {
        "template": "\ndoctype 5\n[a specific open element tag — verify with the HTML schema]\n",
        "options": { "format": "x[a specific open element tag — verify with the HTML schema]" }
      },
      "expected_output": "<!DOCTYPE [a specific open element tag — verify with the HTML schema]><[a specific open element tag — verify with the HTML schema]></[a specific open element tag — verify with the HTML schema]>"
    }
  ]
}
```

---

### Feature 10: Pretty-Printed Output

**As a developer**, I want an optional readable layout, so generated HTML can be inspected by humans during development.

**Expected Behavior / Usage:**

When the `pretty` flag is enabled in `options`, block-level elements are placed on their own lines and their nested content is indented, producing a human-readable document; inline elements stay on a single line. Pre-formatted multi-line content emitted into the document is re-indented to match its surrounding depth.

**Test Cases:** `rcb_tests/public_test_cases/feature14_pretty.json`

```json
{
  "description": "When the pretty-printing flag is enabled in the options, block-level elements are placed on their own lines and their nested content is indented, producing a human-readable document. Inline elements are kept on a single line. Pre-formatted multi-line content emitted into the document is re-indented to match its surrounding depth.",
  "cases": [
    {
      "input": {
        "template": "\n[a specific open element tag — verify with the HTML schema]\n  body == \"  <div>\\n    <a>link</a>\\n  </div>\"\n",
        "options": { "pretty": true }
      },
      "expected_output": "<[a specific open element tag — verify with the HTML schema]>\n  <body>\n    <div>\n      <a>link</a>\n    </div>\n  </body>\n</[a specific open element tag — verify with the HTML schema]>"
    }
  ]
}
```

---

### Feature 11: Error Handling

**As a developer**, I want malformed or forbidden input rejected with a precise, neutral diagnostic, so problems fail fast and the wire contract never leaks host-language details.

**Expected Behavior / Usage:**

*11.1 Syntax errors — position-aware parse diagnostics*

A malformed template is rejected before any document is produced. The failure is rendered as a neutral, line-oriented record: a category line `error=syntax`, a `reason` line carrying a human-readable diagnostic, and `line`/`column` lines giving the one-based position where parsing failed (each on its own line, trailing newline included). Triggers include indentation deeper than allowed, indentation that lines up with no enclosing block, an unrecognized line-leading indicator, an illegal combination of shortcuts, text following a self-closed tag, and an attribute group missing its closing delimiter.

**Test Cases:** `rcb_tests/public_test_cases/feature16_syntax_errors.json`

```json
{
  "description": "A malformed template is rejected before producing any document. The failure is reported as a neutral, line-oriented record: a category line \"error=syntax\", a \"reason\" line giving a human-readable diagnostic, and \"line\"/\"column\" lines giving the one-based position where parsing failed. Triggers include indentation that is deeper than allowed, indentation that does not line up with any enclosing block, an unrecognized line-leading indicator, an illegal combination of shortcuts, text following a self-closed tag, and an attribute group missing its closing delimiter.",
  "cases": [
    {
      "input": { "template": "\ndoctype 5\n  div Invalid\n" },
      "expected_output": "error=syntax\nreason=Unexpected indentation\nline=3\ncolumn=2\n"
    },
    {
      "input": { "template": "\np\n  div Valid\n  .valid\n  #valid\n  ?invalid\n" },
      "expected_output": "error=syntax\nreason=Unknown line indicator\nline=6\ncolumn=2\n"
    }
  ]
}
```

*11.2 Forbidden constructs — rules enforced at build time*

Some constructs parse but are forbidden by the engine's rules; they are rejected with a neutral record: a category line `error=runtime` followed by a `reason` line carrying a human-readable diagnostic (trailing newline included). Writing an explicit block terminator is forbidden because block ends are inferred from indentation. Supplying the id attribute more than once for one element — whether via shortcut plus explicit attribute, or via a splatted pair — is also forbidden.

**Test Cases:** `rcb_tests/public_test_cases/feature17_forbidden_constructs.json`

```json
{
  "description": "Some constructs are accepted by the grammar but forbidden by the engine's rules, and are rejected with a neutral record: a category line \"error=runtime\" followed by a \"reason\" line carrying a human-readable diagnostic. Writing an explicit block terminator is forbidden because block ends are inferred from indentation. Supplying the id attribute more than once for one element (whether via shortcut plus explicit attribute, or via a splatted pair) is also forbidden.",
  "cases": [
    {
      "input": { "template": "\ndiv\n  - if true\n      p A\n  - end\n" },
      "expected_output": "error=runtime\nreason=Explicit end statements are forbidden\n"
    },
    {
      "input": { "template": "\n#alpha id=\"beta\" Test it\n" },
      "expected_output": "error=runtime\nreason=Multiple id attributes specified\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above (lexing the indentation-sensitive grammar, an attribute/value model with merging and boolean/array/hash handling, output formatting with optional pretty-printing, and precise error reporting). Its physical structure MUST align with the "Scale-Driven Code Organization" constraint, and the core business logic must be decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin (`template`, optional `options`, optional `locals`, optional `yield`) and prints the rendered document to stdout, matching the per-feature contracts above. Native parse/build exceptions raised by the core must be translated, in the adapter's render layer only, into the neutral `error=<category>` records defined in Feature 11 — the core may raise idiomatic exceptions, but their language identity must never appear in stdout.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
