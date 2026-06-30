## Product Requirement Document

# Text Templating Engine — String-Driven Rendering with Filters, Tags, and Partials

## Project Goal

Build a text templating engine that turns a template string plus a set of named data values into a fully rendered output string, so developers can keep presentation text separate from program data and produce dynamic documents without hand-writing string concatenation.

---

## Background & Problem

Applications constantly need to weave runtime data into text: web pages, emails, configuration files, code generation. Without a templating engine, developers concatenate strings by hand, sprinkle conditionals and loops through their code, and re-implement formatting helpers (case conversion, escaping, list joining) over and over. The result is brittle, hard to read, and easy to get wrong — especially around edge cases like missing values, whitespace, and HTML-unsafe characters.

With this engine, a template is authored once as ordinary text containing two kinds of placeholders: *output markers* that substitute a value, and *tags* that drive logic such as conditionals, loops, assignment, and inclusion of reusable fragments. Values flow in as a structured data object. The engine parses the template into a reusable compiled form and then renders it against the data to produce the final string. A library of standard filters lets authors transform values inline. Malformed templates are rejected up front, and references that cannot be resolved are reported rather than silently ignored.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains. This domain (lexing/parsing, an expression and filter model, control-flow tags, and rendering) is non-trivial and warrants a multi-file design separating parsing, the value/data model, the filter and tag plugins, and rendering.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls to the core engine.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, the value model, filter implementations, control-flow tags, rendering, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The set of filters and tags must be open for extension (new filters/tags can be added) without modifying the core engine.
   - **Liskov Substitution Principle (LSP):** Every filter and every tag must be substitutable through its common abstraction.
   - **Interface Segregation Principle (ISP):** Keep the filter and tag interfaces small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level rendering should depend on abstractions (a value view, a filter/tag registry), not low-level I/O.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core engine must be elegant and idiomatic to the target programming language, hiding internal complexity behind a small "build a parser, parse a template, render with data" surface.
   - **Resilience:** The system must handle edge cases gracefully. Compile-time and evaluation-time failures should be modeled properly (e.g., specific error types or Result/Either patterns) rather than relying on generic faults or producing partial/incorrect output.

---

## Core Features

All features share one black-box contract enforced by the execution adapter: the adapter reads a single JSON request from stdin with a `template` (the template source string), an optional `globals` object (the named data values), and an optional `partials` object (a map from partial name to partial source). It builds the engine with the standard tag/filter library, registers any partials, parses the template, and renders it against the globals, printing the **raw rendered string** to stdout. If the template cannot be compiled, it prints the single line `error=parse`; if it compiles but rendering fails, it prints `error=render`. These neutral error categories carry no host-language details.

### Feature 1: Variable Output & Data Lookup

**As a developer**, I want to drop a data value into surrounding text by naming it, so I can interleave dynamic content with static text.

**Expected Behavior / Usage:**

Text outside any marker is reproduced exactly, including all of its spaces and punctuation. An output marker `{{ ... }}` emits the textual form of the named binding resolved from the supplied data; member access with a dot reaches into nested objects. Whitespace immediately inside the marker braces is insignificant (the name is trimmed), whereas whitespace in the literal text around the marker is preserved. A boolean value (whether supplied as a binding or written as a literal) renders as its lowercase word; a [a specific list of allowed scalar types]/absent-literal value renders as the empty string. A marker may span multiple lines between its braces.

**Test Cases:** `rcb_tests/public_test_cases/feature1_variables.json`

```json
{
    "description": "Substitute variable references and literal text into output. An output marker emits the textual form of a named binding resolved from the supplied data, supporting nested member access. Literal text outside markers is reproduced exactly, including its spaces, while spaces immediately inside a marker are insignificant. A boolean binding or boolean literal renders as its lowercase word, and a [a specific list of allowed scalar types] binding renders as the empty string. A marker may span multiple lines.",
    "cases": [
        {"input": {"template": "{{test}}", "globals": {"test": "worked"}}, "expected_output": "worked"},
        {"input": {"template": "{{ test.test }}", "globals": {"test": {"test": "worked"}}}, "expected_output": "worked"}
    ]
}
```

---

### Feature 2: Standard Filter Library

**As a developer**, I want to transform a value inline with a pipe, so I can format and manipulate data right in the template without helper code.

**Expected Behavior / Usage:**

A value is piped through one or more filters with `|`, and each filter may take positional arguments after a `:`. Filters chain left to right, the output of one feeding the next.

*2.1 String Filters — case conversion, substitution, trimming, slicing*

Covered string transforms: convert to upper or lower case; capitalize the first character (lowercasing the rest); replace every occurrence or only the first occurrence of a substring; append or prepend a fixed string; remove every occurrence or only the first occurrence of a substring; strip HTML tags and comments leaving only the text content; truncate to a given number of words and append a supplied ellipsis string; and take a substring slice from a start offset (a negative offset counts from the end) for an optional length, where an out-of-range length is clamped to the available characters and an empty input yields empty output.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_string_filters.json`

```json
{
    "description": "Transform a string value through the standard string filters. Filters are applied with a pipe and may take positional arguments after a colon. Covered transforms: convert to upper or lower case; capitalize the first character; replace every occurrence or only the first occurrence of a substring; append or prepend a fixed string; remove every occurrence or only the first occurrence of a substring; strip HTML tags and comments leaving the text content; truncate to a given number of words appending a supplied ellipsis; and take a substring slice from a start offset (negative counts from the end) for an optional length (clamped to the available characters, empty input yields empty output).",
    "cases": [
        {"input": {"template": "{{ text | upcase}}", "globals": {"text": "hello"}}, "expected_output": "HELLO"},
        {"input": {"template": "{{ text | replace: 'bar', 'foo' }}", "globals": {"text": "bar2bar"}}, "expected_output": "foo2foo"},
        {"input": {"template": "{{ '6543210' | slice: -4, 3 }}"}, "expected_output": "321"}
    ]
}
```

*2.2 Numeric Filters — arithmetic on numbers*

The addition and subtraction filters each take a numeric operand and produce the sum or difference. The modulo filter returns the remainder of dividing the input by its operand; when both are integers the result is integer-formatted, while a fractional operand produces a full-precision decimal result.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_numeric_filters.json`

```json
{
    "description": "Apply arithmetic filters to a numeric value. The addition and subtraction filters take a numeric operand and produce the sum or difference. The modulo filter returns the remainder; integer operands produce an integer-formatted result, while a fractional operand produces a full-precision decimal result.",
    "cases": [
        {"input": {"template": "{{ num | plus : 2 }}", "globals": {"num": 4}}, "expected_output": "6"},
        {"input": {"template": "{{ num | modulo: 2 }}", "globals": {"num": 5.1}}, "expected_output": "1.0999999999999996"}
    ]
}
```

*2.3 Collection Filters — list access, ordering, projection, defaults*

The first and last filters return the first or last element of a list, and for a plain string return its first or last character. The split filter divides a string into a list on a separator; join concatenates a list into a string with a separator; sort orders a list of strings; and split/sort/join combine to reorder the parts of a delimited string. Given a property name, the compact filter drops list entries whose named property is [a specific list of allowed scalar types] and map projects each entry to its named property. The default filter substitutes a fallback value when the input is falsy and otherwise passes the input through unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_array_filters.json`

```json
{
    "description": "Operate on collections. The first and last filters return the first or last element of a list, and for a plain string return its first or last character. The split filter divides a string into a list on a separator; join concatenates a list into a string with a separator; sort orders a list of strings; and the combination of split/sort/join reorders the parts. The compact filter, given a property name, drops list entries whose named property is [a specific list of allowed scalar types], map projects each entry to its named property, and a default filter substitutes a fallback when the value is falsy and otherwise passes the value through.",
    "cases": [
        {"input": {"template": "{{ 'a~b~c' | split:'~' | join:', ' }}"}, "expected_output": "a, b, c"},
        {"input": {"template": "{{ text | default: 'bar' }}", "globals": {"text": [a specific list of allowed scalar types]}}, "expected_output": "bar"}
    ]
}
```

*2.4 HTML Escaping Filters — entity encoding*

The escape filter replaces the markup-significant characters (ampersand, both angle brackets, single quote, double quote) with their HTML entity equivalents on every occurrence. The escape_once filter performs the same replacement but recognizes substrings that are already valid entities and leaves them intact, so applying it to already-escaped text is idempotent while bare markup characters are still escaped.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_escaping_filters.json`

```json
{
    "description": "HTML-escape text. The escape filter replaces the markup-significant characters (ampersand, angle brackets, single and double quotes) with their HTML entity equivalents on every occurrence. The escape_once filter performs the same replacement but recognizes substrings that are already valid entities and leaves them untouched, so applying it to already-escaped text is idempotent while still escaping bare markup characters.",
    "cases": [
        {"input": {"template": "{{ var | escape }}", "globals": {"var": "<>&'\""}}, "expected_output": "&lt;&gt;&amp;&#39;&quot;"},
        {"input": {"template": "{{ var | escape_once }}", "globals": {"var": "1 &lt; 2 &amp; 3"}}, "expected_output": "1 &lt; 2 &amp; 3"}
    ]
}
```

---

### Feature 3: Conditional Tags

**As a developer**, I want to include or omit a section of the template based on a condition, so the same template adapts to different data.

**Expected Behavior / Usage:**

An if block delimits a body that is rendered only when its condition is truthy; an optional else clause supplies an alternate body rendered otherwise. Conditions may compare a binding to a literal for equality, or compare two numeric bindings with relational operators (less-than, greater-than). The literal text inside the chosen branch — including any surrounding spaces — is emitted verbatim, and the branch that is not chosen produces nothing.

**Test Cases:** `rcb_tests/public_test_cases/feature3_conditionals.json`

```json
{
    "description": "Conditionally include sections of the template. An if block with an optional else renders its primary body when the condition is truthy and the alternate body otherwise. Conditions may compare a binding to a literal for equality or compare two numeric bindings with relational operators. Literal text inside the chosen branch (including surrounding spaces) is emitted verbatim.",
    "cases": [
        {"input": {"template": "{% if containsallshipments == [a specific list of allowed scalar types] %} YES {% endif %}", "globals": {"containsallshipments": [a specific list of allowed scalar types]}}, "expected_output": " YES "},
        {"input": {"template": "{% if num > numTwo %}wat{% else %}wot{% endif %}", "globals": {"num": 5, "numTwo": 6}}, "expected_output": "wot"}
    ]
}
```

---

### Feature 4: Iteration

**As a developer**, I want to repeat a section of the template once per element of a sequence, so I can render lists of data.

**Expected Behavior / Usage:**

A for block binds a loop variable to each element of a sequence in turn and renders its body once per element. The sequence may be a list produced by a filter (e.g. splitting a string) or an inclusive integer range written as two bounds. The body's literal text and output markers are rendered on every pass, so separators and trailing characters accumulate across iterations; an empty sequence renders nothing.

**Test Cases:** `rcb_tests/public_test_cases/feature4_iteration.json`

```json
{
    "description": "Iterate over a sequence with a for block, emitting the body once per element with the loop variable bound to the current element. The sequence may be a list produced by a filter or an inclusive integer range written as two bounds. Body text and output markers are rendered on each pass, so repeated separators and trailing characters accumulate across iterations.",
    "cases": [
        {"input": {"template": "{% assign beatles = \"John, Paul, George, Ringo\" | split: \", \" %}{% for member in beatles %}{{ member }}\n{% endfor %}"}, "expected_output": "John\nPaul\nGeorge\nRingo\n"},
        {"input": {"template": "{% for i in (1..10) %}{{ foobar }}{% endfor %}", "globals": {"foobar": " "}}, "expected_output": "          "}
    ]
}
```

---

### Feature 5: Variable Assignment & Capture

**As a developer**, I want to compute and name intermediate values inside a template, so I can reuse them without recomputing or cluttering the data.

**Expected Behavior / Usage:**

*5.1 Assign — bind an expression to a name*

An assign tag binds the result of an expression to a name; the expression may be a direct binding or a binding passed through a filter (for instance one that produces a list). The bound name can then be read like any variable later in the template, including positional indexing into an assigned list with bracket notation.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_assign.json`

```json
{
    "description": "Bind a value to a name with an assign tag and reference it later in the template. The assigned expression may be a direct binding or a binding passed through a filter (for example one that produces a list). Once assigned, the name can be read like any variable, including positional indexing into an assigned list.",
    "cases": [
        {"input": {"template": "{% assign foo = values %}.{{ foo[0] }}.", "globals": {"values": ["foo", "bar", "baz"]}}, "expected_output": ".foo."},
        {"input": {"template": "{% assign foo = values | split: \",\" %}.{{ foo[1] }}.", "globals": {"values": "foo,bar,baz"}}, "expected_output": ".bar."}
    ]
}
```

*5.2 Capture — bind the rendered output of a block*

A capture/endcapture block renders its inner body and binds the resulting text to a name instead of emitting it. The captured text becomes the value of that name and may be re-read, reassigned, or copied to another variable later. A capture placed inside a conditional or loop updates the variable in the surrounding scope, and the final observed value reflects the last capture that executed.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_capture.json`

```json
{
    "description": "Capture the rendered output of a block into a named variable with a capture/endcapture tag. The captured text becomes the value of the name and can be re-read, reassigned, or copied to another variable later in the template. A capture inside a conditional or loop updates the outer-scope variable, and the final value reflects the last capture executed.",
    "cases": [
        {"input": {"template": "\n    {% assign var = '' %}\n    {% if [a specific list of allowed scalar types] %}\n    {% capture var %}first-block-string{% endcapture %}\n    {% endif %}\n    {% if [a specific list of allowed scalar types] %}\n    {% capture var %}test-string{% endcapture %}\n    {% endif %}\n    {{var}}\n"}, "expected_output": "\n    \n    \n    \n    \n    \n    \n    \n    test-string\n"}
    ]
}
```

---

### Feature 6: Whitespace Control

**As a developer**, I want to trim the whitespace that surrounds tags and markers, so generated output is not cluttered with the indentation and newlines of the template source.

**Expected Behavior / Usage:**

A hyphen placed just inside the opening delimiter of a tag or marker trims the whitespace immediately preceding it; a hyphen just inside the closing delimiter trims the whitespace immediately following it. Without a hyphen, the adjacent whitespace and newlines are preserved verbatim in the output. With hyphens on both sides, the surrounding whitespace collapses so that the text on either side joins directly.

**Test Cases:** `rcb_tests/public_test_cases/feature6_whitespace.json`

```json
{
    "description": "Control surrounding whitespace around tags and markers. A hyphen placed just inside the opening delimiter trims whitespace immediately before the tag/marker, and a hyphen just inside the closing delimiter trims whitespace immediately after it. Without a hyphen the adjacent whitespace and newlines are preserved in the output; with hyphens on both sides the surrounding whitespace collapses, letting adjacent text join directly.",
    "cases": [
        {"input": {"template": "\ntopic1\n  {%- assign foo = \"bar\" -%}\n  -  {{- foo -}}  \n\n"}, "expected_output": "\ntopic1-bar"}
    ]
}
```

---

### Feature 7: Template Partials (Include)

**As a developer**, I want to pull in a named reusable template fragment, so I can compose larger templates out of shared pieces.

**Expected Behavior / Usage:**

An include tag names a partial that is looked up from a registered set of named sources. The partial is rendered in the current data context — so it can read the same bindings as the surrounding template — and its rendered output is spliced in place of the include tag. A partial may itself contain output markers, filters, and control-flow tags.

**Test Cases:** `rcb_tests/public_test_cases/feature7_partials.json`

```json
{
    "description": "Embed the rendered output of a named partial template with an include tag. The partial is looked up by name from a registered set of named sources, rendered in the current data context (so it can read the same bindings), and its output is spliced in place of the include tag. A partial may itself contain markers, filters, and conditional logic.",
    "cases": [
        {"input": {"template": "{% include 'inc' %}", "globals": {"content": "hello, world!"}, "partials": {"inc": "{{content}}\n"}}, "expected_output": "hello, world!\n"}
    ]
}
```

---

### Feature 8: Error Reporting

**As a developer**, I want malformed templates and unresolved references to fail clearly, so mistakes surface instead of producing silently wrong output.

**Expected Behavior / Usage:**

*8.1 Compile-time rejection*

Compilation fails when output or tag delimiters are unbalanced or unterminated, when an unknown or stray tag delimiter appears, when a block opener has no matching closer, when an unrecognized comparison operator is used in a condition, when an output marker has an empty filter position, or when a filter is invoked without a required argument. A compile failure produces no rendered output; the adapter reports it as the neutral category line `error=parse`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_parse_errors.json`

```json
{
    "description": "Reject a malformed template at compile time. The engine fails to compile when output or tag delimiters are unbalanced or unterminated, when an unknown or stray tag delimiter is used, when a block opener has no matching closer, when an unrecognized comparison operator appears in a condition, when an output marker has an empty filter position, or when a filter is invoked without a required argument. A compile failure is reported as a neutral parse-error category rather than producing output.",
    "cases": [
        {"input": {"template": "text {{method} oh nos!"}, "expected_output": "error=parse"},
        {"input": {"template": "{% if 1 =! 2 %}ok{% endif %}"}, "expected_output": "error=parse"}
    ]
}
```

*8.2 Render-time rejection*

A template that compiled successfully can still fail while rendering. Referencing a name that is not present in the supplied data is treated as an evaluation error rather than silently producing empty text, so reading an undefined binding fails at render time. The adapter reports this as the neutral category line `error=render` and emits no partial output.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_render_errors.json`

```json
{
    "description": "Report a failure that occurs while rendering a successfully compiled template. Referencing a name that is not present in the supplied data is treated as an evaluation error rather than silently producing empty text, so a template that reads an undefined binding fails at render time. The failure is reported as a neutral render-error category rather than producing partial output.",
    "cases": [
        {"input": {"template": "{{ test }}", "globals": {}}, "expected_output": "error=render"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the templating engine: lexing/parsing of templates, a value/data model, a registry of filters and control-flow tags (open for extension), and a renderer. The core must be decoupled from standard I/O and JSON parsing. The public surface should be a small "build a parser (with the standard library of tags/filters), parse a template, render it against a data object" flow, with errors modeled as proper compile-time and render-time failures.

2. **The Execution/Test Adapter:** A runnable program — logically (and ideally physically) separated from the core — that reads a single JSON request from stdin with fields `template` (string), optional `globals` (data object), and optional `partials` (map of partial name to source). It builds the engine with the standard tag/filter library, registers any partials, parses the template, and renders it against the globals, printing the raw rendered string to stdout. On a compile failure it prints exactly `error=parse`; on a render failure it prints exactly `error=render`. These neutral categories must not leak any host-language runtime detail.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same error chaining logic as the number filter family
