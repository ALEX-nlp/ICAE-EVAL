## Product Requirement Document

# Wikitext Expansion Engine — Template, Argument & Parser-Function Renderer for MediaWiki-Style Markup

## Project Goal

Build a text-processing engine that takes a fragment of MediaWiki-style wikitext together with a set of named pages (templates) and produces the fully *expanded* text: every template call is replaced by its rendered body, every template argument is substituted, and every built-in parser function and magic word is evaluated. This lets downstream tools work with the final, resolved text of a page instead of re-implementing the intricate expansion rules themselves.

---

## Background & Problem

MediaWiki markup is not just static text: a page can transclude other pages ("templates"), pass them positional and named arguments, reference those arguments (with defaults and even computed names), and call dozens of built-in "parser functions" and "magic words" that compute strings, evaluate arithmetic, branch on conditions, manipulate substrings, format numbers and dates, encode URLs, and report parts of the current page title. The rules interact: arguments are expanded in the caller's scope, conditionals choose which branch to expand, and special punctuation templates inject characters (like the pipe) that would otherwise be syntactically meaningful.

Without an engine that implements these rules faithfully, every consumer of wiki content has to reinvent a fragile parser. This project specifies that engine purely in terms of input wikitext (plus supporting pages) and the exact expanded output string it must produce.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain. This is a non-trivial domain (a tokenizer/expander plus a family of independent built-in functions), so it MUST NOT be a single "god file": separate the expansion core, the argument/scope model, and the built-in function implementations into clear modules (e.g. `src/`, `tests/`). Do not over-engineer, but avoid a monolith.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core engine. The core expansion logic must be completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating a JSON request into idiomatic calls on the core engine and rendering the resulting string.

3. **Adherence to SOLID Design Principles:** Separate parsing/tokenizing, scope/argument resolution, the dispatch of built-in functions, and the individual function implementations into distinct, cohesive units. The set of built-in functions must be open for extension (new functions) but closed for modification of the core expander. High-level expansion logic must depend on abstractions, not on the I/O layer.

4. **Robustness & Interface Design:** The public interface of the engine must be elegant and idiomatic to the target language. The engine must handle edge cases gracefully: undefined arguments, undefined templates, malformed expressions, recursion, and unparseable dates all have well-defined outputs (described per feature) rather than crashes. Domain-level problems are rendered into the output text (e.g. an inline error marker), not raised as host exceptions that leak through stdout.

---

## Core Features

The engine is exercised through a single operation: **expand** a piece of wikitext. A request supplies the `wikitext` to expand, an optional `title` naming the page the text belongs to (default `Tt`), and an optional `pages` list registering supporting pages. Each entry in `pages` has a `title` and a `body`; a page whose title begins with `Template:` is a template that can be transcluded by the name after the prefix. The expanded text is the entire program output.

The expansion syntax used throughout: `{{Name|...}}` transcludes a template (or, for a `#`-prefixed name or a known magic word, calls a parser function); `{{{n|default}}}` references argument `n` with an optional default; `[[ ... ]]` is internal-link markup that is passed through unchanged by the expander.

---

### Feature 1: Literal Passthrough & Undefined References

**As a developer**, I want text without expandable calls (and references that cannot be resolved) to come back unchanged, so I can rely on the engine to only transform what it actually understands.

**Expected Behavior / Usage:**

Plain text is returned verbatim. Internal-link markup written as bracketed segments (`[[...]]`, including the `[[target|label]]` form) is passed through unchanged. A triple-brace reference to an argument that is not defined in the current scope is left as its literal text. A call to a template that has not been registered is replaced inline by an error marker of the form `<strong class="error">Template:NAME</strong>`, where `NAME` is the requested template name; any arguments passed to the unknown template are discarded.

**Test Cases:** `rcb_tests/public_test_cases/feature1_literal_passthrough.json`

```json
{
    "description": "Expand wikitext that contains no expandable template or parser-function calls. Plain text, internal-link markup written as bracketed segments, and references to arguments that are not defined in the current scope are all returned verbatim. A call to a template that has not been registered is replaced inline by an error marker that names the missing template and discards any arguments passed to it.",
    "cases": [
        {"input": {"wikitext": "Some text"}, "expected_output": "Some text"},
        {"input": {"wikitext": "Some [[link]] x"}, "expected_output": "Some [[link]] x"},
        {"input": {"wikitext": "Some [[link|text]] x"}, "expected_output": "Some [[link|text]] x"}
    ]
}
```

---

### Feature 2: Template Transclusion & Arguments

**As a developer**, I want template calls to be replaced by their rendered bodies with arguments substituted, so reusable wiki components compose correctly.

**Expected Behavior / Usage:**

*2.1 Basic Transclusion — body insertion and positional arguments*

Calling a registered template inserts its body in place of the call. Positional arguments are referenced inside the body by their one-based number in triple braces (`{{{1}}}`) and substituted from the call. Whitespace and leading list markup in the body are preserved exactly. An argument supplied as empty substitutes the empty string; a positional reference for which no argument was passed and which carries no default is left as its literal triple-brace text.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_template_basic.json`

```json
{
    "description": "Transclude a registered template by name. The template body is inserted in place of the call, with positional arguments (referenced inside the body by their one-based number in triple braces) substituted from the call. Whitespace and leading list markup in the body are preserved exactly; an argument supplied as empty substitutes the empty string, while a positional reference for which no argument was passed is left as its literal triple-brace text.",
    "cases": [
        {"input": {"wikitext": "a{{testmod}}b", "pages": [{"title": "Template:testmod", "body": "test content"}]}, "expected_output": "atest contentb"},
        {"input": {"wikitext": "a{{testmod}}b", "pages": [{"title": "Template:testmod", "body": " test content "}]}, "expected_output": "a test content b"}
    ]
}
```

*2.2 Argument Model — defaults, named, and computed names*

A triple-brace reference may carry a default value after a pipe (`{{{1|default}}}`) used when the argument is absent. Arguments may be passed by name as `key=value` or by position. A named default may fall back to a positional reference (`{{{foo|{{{1}}}}}}`). An argument name may itself be computed by nesting another reference inside the braces (`{{{{{{1}}}}}}`), so the selected argument index is dynamic. Named arguments may contain spaces.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_template_args.json`

```json
{
    "description": "Resolve template arguments with the full argument model: a triple-brace reference may carry a default value used when the argument is absent; arguments may be passed by name as key=value or by position; a named default can fall back to a positional reference; and an argument name may itself be computed by nesting another reference inside the braces so the selected argument index is dynamic. Named arguments may contain spaces.",
    "cases": [
        {"input": {"wikitext": "{{testmod}}", "pages": [{"title": "Template:testmod", "body": "test {{{1|}}} content"}]}, "expected_output": "test  content"},
        {"input": {"wikitext": "{{testmod}}", "pages": [{"title": "Template:testmod", "body": "test {{{1|def}}} content"}]}, "expected_output": "test def content"},
        {"input": {"wikitext": "{{testmod|foo}}", "pages": [{"title": "Template:testmod", "body": "test {{{1|def}}} content"}]}, "expected_output": "test foo content"}
    ]
}
```

*2.3 Nested Transclusion — templates calling templates*

Templates may call other templates, passing arguments through each level. Arguments are expanded in the calling scope before being handed to the inner template, and inner parser functions see the propagated values. When an argument is not supplied at the outermost call, an innermost reference that has no default remains as literal triple-brace text.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_template_nested.json`

```json
{
    "description": "Expand templates that call other templates, passing arguments through each level. Arguments are expanded in the calling scope before being handed to the inner template, and inner parser functions see the propagated values. When an argument is not supplied at the outermost call, the innermost reference that has no default remains as literal triple-brace text.",
    "cases": [
        {"input": {"wikitext": "{{testmod|zz}}", "pages": [{"title": "Template:testmod", "body": "a{{testmod2|{{{1}}}}}b"}, {"title": "Template:testmod2", "body": "x{{{1}}}y"}]}, "expected_output": "axzzyb"},
        {"input": {"wikitext": "{{testmod|zz}}", "pages": [{"title": "Template:testmod", "body": "a{{testmod2|{{{1}}}}}b"}, {"title": "Template:testmod2", "body": "{{#if:{{{1}}}|x|y}}"}]}, "expected_output": "axb"}
    ]
}
```

*2.4 Punctuation Templates — injecting syntactic characters*

A small set of magic punctuation templates lets a call inject characters that would otherwise be interpreted as wikitext syntax. The pipe template `{{!}}` yields a literal vertical bar inside an argument. The brace templates `{{((}}` and `{{))}}` yield literal braces, which are emitted as HTML entities (`&lbrace;` / `&rbrace;`) rather than reopening template syntax. A user-defined template may itself expand to such punctuation. These resolve correctly even when produced from inside a conditional.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_template_special_chars.json`

```json
{
    "description": "Magic punctuation templates let a call inject characters that would otherwise be interpreted as wikitext syntax. The pipe template yields a literal vertical bar inside an argument; brace templates yield literal braces that are emitted as HTML entities rather than reopening template syntax; and a user-defined template may itself expand to such punctuation. These resolve correctly even when produced from inside a conditional.",
    "cases": [
        {"input": {"wikitext": "{{testmod|{{!}}}}", "pages": [{"title": "Template:testmod", "body": "a{{{1}}}b"}]}, "expected_output": "a|b"},
        {"input": {"wikitext": "{{testmod|{{((}}!{{))}}}}", "pages": [{"title": "Template:testmod", "body": "a{{{1}}}b"}]}, "expected_output": "a&lbrace;&lbrace;!&rbrace;&rbrace;b"}
    ]
}
```

---

### Feature 3: Conditional Parser Functions

**As a developer**, I want conditionals that select text based on emptiness, equality, switch matching, or an expression, so templates can produce different output for different inputs.

**Expected Behavior / Usage:**

*3.1 Non-empty test — `{{#if:test|then|else}}`*

Branches on whether the test string has any non-whitespace content: non-empty selects the then-branch, empty selects the else-branch. When the else-branch is omitted, an empty test yields the empty string.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_if.json`

```json
{
    "description": "The conditional that branches on whether a test string is non-empty. The first argument is the test value; if it has any non-whitespace content the then-branch is produced, otherwise the else-branch. When the else-branch is omitted an empty test yields the empty string.",
    "cases": [
        {"input": {"wikitext": "{{#if:|T|F}}"}, "expected_output": "F"},
        {"input": {"wikitext": "{{#if:x|T|F}}"}, "expected_output": "T"}
    ]
}
```

*3.2 Equality test — `{{#ifeq:a|b|then|else}}`*

Compares two operands for equality after trimming surrounding whitespace; two empty operands count as equal. With the else-branch omitted, an unequal comparison yields the empty string.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_ifeq.json`

```json
{
    "description": "The conditional that compares two operands for equality and chooses the then- or else-branch accordingly. Operands are compared after trimming surrounding whitespace, and two empty operands count as equal. With the else-branch omitted, an unequal comparison yields the empty string.",
    "cases": [
        {"input": {"wikitext": "{{#ifeq:a|b|T|F}}"}, "expected_output": "F"},
        {"input": {"wikitext": "{{#ifeq:a|a|T|F}}"}, "expected_output": "T"}
    ]
}
```

*3.3 Multi-way switch — `{{#switch:value|case=result|...|default}}`*

Matches the first argument against `case=value` pairs and produces the value of the first matching case. A bare case (no equals sign) falls through to the value of the next case that has one. A trailing bare value, or an explicit `#default=` case, supplies the result when nothing matches; with no default and no match the result is empty. An explicit empty-string case (`=value`) can be matched.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_switch.json`

```json
{
    "description": "The multi-way selector. The first argument is matched against a list of case=value pairs and the value of the first matching case is produced. A bare case with no equals sign falls through to the value of the next case that has one. A trailing bare value, or an explicit default case, supplies the result when nothing matches; if no default is present and nothing matches the result is empty. An explicit empty-string case can be matched.",
    "cases": [
        {"input": {"wikitext": "{{#switch:a|a=one|b=two|three}}"}, "expected_output": "one"},
        {"input": {"wikitext": "{{#switch:c|a=one|b=two|three}}"}, "expected_output": "three"},
        {"input": {"wikitext": "{{#switch:|a=one|#default=three|b=two}}"}, "expected_output": "three"}
    ]
}
```

*3.4 Expression test — `{{#ifexpr:expr|then|else}}`*

Evaluates a numeric/boolean expression (same syntax as Feature 5) and branches on whether the result is true (non-zero).

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_ifexpr.json`

```json
{
    "description": "The conditional that evaluates a numeric/boolean expression and branches on whether the result is true (non-zero). The expression supports the same arithmetic, comparison and function syntax as the arithmetic evaluator.",
    "cases": [
        {"input": {"wikitext": "a{{#ifexpr:1+3>2|T|F}}b"}, "expected_output": "aTb"},
        {"input": {"wikitext": "a{{#ifexpr:1-4>sin(pi/2)|T|F}}b"}, "expected_output": "aFb"}
    ]
}
```

---

### Feature 4: Error Detection — `{{#iferror:input|then|else}}`

**As a developer**, I want to detect whether an expanded value carries an error marker, so templates can fall back gracefully when a sub-computation fails.

**Expected Behavior / Usage:**

An error is recognised by the presence of an error-class HTML marker in the first argument (a tag carrying `class="error"`, such as the inline marker produced by a failed expression). Ordinary markup that merely mentions the word "error" or contains unrelated tags is NOT treated as an error. If the argument is in error the then-branch is produced; otherwise the else-branch is produced, defaulting to the argument's own value when the else-branch is omitted. This composes with the arithmetic evaluator (Feature 5), whose own inline error output is detected here as an error.

**Test Cases:** `rcb_tests/public_test_cases/feature4_iferror.json`

```json
{
    "description": "The conditional that detects whether its first argument contains an error. An error is recognised by the presence of an error-class HTML marker (such as a tag carrying class=\"error\"); ordinary markup that merely mentions the word error or contains unrelated tags is NOT treated as an error. If the argument is in error the then-branch is produced; otherwise the else-branch is produced, defaulting to the argument's own value when the else-branch is omitted. This composes with the arithmetic evaluator, whose own error output is detected as an error.",
    "cases": [
        {"input": {"wikitext": "{{#iferror:|T|F}}"}, "expected_output": "F"},
        {"input": {"wikitext": "{{#iferror:foo<div>bar</div>bar|T|F}}"}, "expected_output": "F"},
        {"input": {"wikitext": "{{#iferror:<span class=\"error\">foo</foo>|T|F}}"}, "expected_output": "T"}
    ]
}
```

---

### Feature 5: Arithmetic Expression Evaluation — `{{#expr:...}}`

**As a developer**, I want a self-contained arithmetic evaluator, so templates can compute numeric results inline.

**Expected Behavior / Usage:**

Evaluate an arithmetic expression and produce its numeric result as text. Supported: addition, subtraction, multiplication, division, integer division (`div`), modulo (`mod`), exponentiation (`^`); correct operator precedence and parentheses; unary plus/minus; scientific e-notation; the constants `pi` and `e`; unary functions including `trunc`, `floor`, `ceil`, `round`, `abs`, `sqrt`, `exp`, `ln`, and the trigonometric functions; the boolean negation `not`; and the comparison operators `=`, `!=` / `<>`, `<`, `>`, `<=`, `>=`, which yield `1` or `0`. An integral result prints with no decimal point; a non-integral result prints in full floating form. An empty or malformed expression yields the inline error marker `<strong class="error">Expression error near ...</strong>`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_expr.json`

```json
{
    "description": "Evaluate an arithmetic expression and produce its numeric result as text. Supports addition, subtraction, multiplication, division, integer division (div), modulo (mod) and exponentiation; correct operator precedence and parentheses; unary plus/minus; scientific e-notation; the constants pi and e; unary functions including trunc, floor, ceil, round, abs, sqrt, exp, ln and the trigonometric functions; the boolean negation not; and the comparison operators =, != / <>, <, >, <=, >= which yield 1 or 0. Integral results print without a decimal point. An empty or malformed expression yields an inline error marker.",
    "cases": [
        {"input": {"wikitext": "{{#expr|1 + 2.34}}"}, "expected_output": "3.34"},
        {"input": {"wikitext": "{{#expr|-12}}"}, "expected_output": "-12"},
        {"input": {"wikitext": "{{#expr|2e3}}"}, "expected_output": "2000"}
    ]
}
```

---

### Feature 6: String Manipulation Functions

**As a developer**, I want substring, search, length, replace, split and pad helpers, so templates can transform text without external tooling.

**Expected Behavior / Usage:**

*6.1 Substring — `{{#sub:str|start|len}}`*

Extract a substring. The start offset is zero-based; a negative offset counts from the end. A positive length returns that many characters; an omitted or zero length returns the remainder from the start; a negative length stops that many characters before the end (empty if that would be non-positive). The source is trimmed of surrounding whitespace first.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_string_substring.json`

```json
{
    "description": "Extract a substring. The function takes a source string, a start offset and an optional length. The start offset is zero-based; a negative offset counts from the end of the string. A positive length returns that many characters; an omitted or zero length returns the remainder from the start; a negative length stops that many characters before the end (empty if that would be non-positive). Surrounding whitespace in the source is trimmed first.",
    "cases": [
        {"input": {"wikitext": "{{#sub: xyzayz |3}}"}, "expected_output": "ayz"},
        {"input": {"wikitext": "{{#sub:Icecream|3}}"}, "expected_output": "cream"},
        {"input": {"wikitext": "{{#sub:Icecream|0|3}}"}, "expected_output": "Ice"}
    ]
}
```

*6.2 Search & Length — `{{#len:str}}`, `{{#pos:str|needle}}`, `{{#rpos:str|needle}}`*

The length helper returns the number of characters after trimming. The forward-search helper returns the zero-based index of the first occurrence of a needle, or the empty string when absent. The reverse-search helper returns the zero-based index of the last occurrence, or `-1` when absent. Inputs are trimmed before searching.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_string_search_length.json`

```json
{
    "description": "String search and length helpers. The length helper returns the number of characters after trimming. The forward-search helper returns the zero-based index of the first occurrence of a needle, or the empty string when absent. The reverse-search helper returns the zero-based index of the last occurrence, or -1 when absent. Inputs are trimmed of surrounding whitespace before searching.",
    "cases": [
        {"input": {"wikitext": "{{#len: xyz }}"}, "expected_output": "3"},
        {"input": {"wikitext": "{{#pos: xyzayz |yz}}"}, "expected_output": "1"},
        {"input": {"wikitext": "{{#pos: xyzayz |zz}}"}, "expected_output": ""}
    ]
}
```

*6.3 Replace & Split — `{{#replace:str|search|repl}}`, `{{#explode:str|delim|pos|limit}}`*

The replace helper substitutes every occurrence of a search string with a replacement (which may be empty, deleting it). The split helper divides the source on a delimiter and returns the piece at a zero-based position; a negative position counts from the end; an optional limit makes the selected piece include the remainder joined back together.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_string_replace_split.json`

```json
{
    "description": "String replace and split helpers. The replace helper substitutes every occurrence of a search string with a replacement (which may be empty, deleting the search string). The split helper divides the source on a delimiter and returns the piece at a given zero-based position; a negative position counts from the end; an optional limit argument makes the selected piece include the remainder of the string joined back together.",
    "cases": [
        {"input": {"wikitext": "{{#replace:Icecream|e|E}}"}, "expected_output": "IcEcrEam"},
        {"input": {"wikitext": "{{#replace:Icecream|e|}}"}, "expected_output": "Iccram"}
    ]
}
```

*6.4 Pad — `{{#pad:str|len|padstr|direction}}`*

Pad a string to a target length using a padding string that is repeated (and truncated as needed) to fill the gap. A direction argument selects `left`, `right` or `center`; the default direction pads on the left.

**Test Cases:** `rcb_tests/public_test_cases/feature6_4_string_pad.json`

```json
{
    "description": "Pad a string to a target length using a padding string. The padding string is repeated (and truncated as needed) to fill the gap. A direction argument selects left, right or center padding; the default direction pads on the left.",
    "cases": [
        {"input": {"wikitext": "{{#pad:Ice|10|xX}}"}, "expected_output": "xXxXxXxIce"},
        {"input": {"wikitext": "{{#pad:Ice|5|x|left}}"}, "expected_output": "xxIce"}
    ]
}
```

---

### Feature 7: Text & Number Formatting

**As a developer**, I want case conversion, grouped number formatting, and width padding, so templates can present values consistently.

**Expected Behavior / Usage:**

*7.1 Case conversion — `{{uc:}}`, `{{lc:}}`, `{{ucfirst:}}`, `{{lcfirst:}}`*

Convert the whole argument to upper case, the whole argument to lower case, only the first character to upper case, or only the first character to lower case.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_case.json`

```json
{
    "description": "Letter-case transforms: convert the whole argument to upper case, the whole argument to lower case, only the first character to upper case, or only the first character to lower case.",
    "cases": [
        {"input": {"wikitext": "{{uc:foo}}"}, "expected_output": "FOO"},
        {"input": {"wikitext": "{{lc:FOO}}"}, "expected_output": "foo"}
    ]
}
```

*7.2 Grouped numbers — `{{formatnum:number|flag}}`*

By default digits left of the decimal point are grouped into threes with commas and the fractional part is left unchanged. A `NOSEP` flag formats without inserting separators. An `R` flag runs in reverse, stripping existing grouping separators to recover a plain number.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_formatnum.json`

```json
{
    "description": "Format a number with grouping separators. By default digits left of the decimal point are grouped into threes with commas and the fractional part is left unchanged. A NOSEP flag formats without inserting separators. An R flag runs in reverse, stripping existing grouping separators to recover a plain number.",
    "cases": [
        {"input": {"wikitext": "{{formatnum:987654321.654321}}"}, "expected_output": "987,654,321.654321"},
        {"input": {"wikitext": "{{formatnum:1234}}"}, "expected_output": "1,234"},
        {"input": {"wikitext": "{{formatnum:123}}"}, "expected_output": "123"}
    ]
}
```

*7.3 Width padding — `{{padleft:str|width|fill}}`, `{{padright:str|width|fill}}`*

Pad a string to a minimum width by adding fill characters on the left or right. The fill defaults to the digit zero; a fill string longer than one character is used cyclically. A string already at or above the requested width is returned unchanged. When the string is empty the fill provides the characters.

**Test Cases:** `rcb_tests/public_test_cases/feature7_3_padleft_padright.json`

```json
{
    "description": "Pad a string to a minimum width by adding fill characters on the left or on the right. The fill defaults to the digit zero; a supplied fill string longer than one character is used cyclically. If the string already meets or exceeds the requested width it is returned unchanged. When the string is empty the fill provides the characters.",
    "cases": [
        {"input": {"wikitext": "{{padleft:xyz|5}}"}, "expected_output": "00xyz"},
        {"input": {"wikitext": "{{padleft:xyz|5|_}}"}, "expected_output": "__xyz"},
        {"input": {"wikitext": "{{padleft:xyz|5|abc}}"}, "expected_output": "abxyz"}
    ]
}
```

---

### Feature 8: URL & Anchor Encoding

**As a developer**, I want to percent-encode text for URLs (and decode it back), so templates can build links safely.

**Expected Behavior / Usage:**

The encoder percent-encodes a string for use in a URL; a mode argument selects the variant: the query variant (`QUERY`, the default) encodes spaces as plus signs, the wiki variant (`WIKI`) turns spaces into underscores and leaves page-title-safe punctuation intact, and the path variant (`PATH`) encodes spaces as `%20`. The anchor encoder produces a fragment identifier (spaces become underscores, most characters preserved). A decoder reverses query-style percent-encoding back to the original text.

**Test Cases:** `rcb_tests/public_test_cases/feature8_urlencode.json`

```json
{
    "description": "URL and anchor encoding. The encoder percent-encodes a string for use in a URL; a mode argument selects the variant: the query variant encodes spaces as plus signs, the wiki variant turns spaces into underscores and leaves page-title-safe punctuation intact, and the path variant encodes spaces as %20. The anchor encoder produces a fragment identifier (spaces become underscores, most characters preserved). A decoder reverses query-style percent-encoding back to the original text.",
    "cases": [
        {"input": {"wikitext": "{{urlencode:x:y/z k}}"}, "expected_output": "x%3Ay%2Fz+k"},
        {"input": {"wikitext": "{{urlencode:x:y/z kä|QUERY}}"}, "expected_output": "x%3Ay%2Fz+k%C3%A4"},
        {"input": {"wikitext": "{{urlencode:x:y/z kä|WIKI}}"}, "expected_output": "x:y/z_k%C3%A4"}
    ]
}
```

---

### Feature 9: Title Path & Namespace Resolution

**As a developer**, I want to slice page-title paths and resolve namespace identifiers, so templates can reason about title structure.

**Expected Behavior / Usage:**

*9.1 Title path slicing — `{{#titleparts:title|count|first}}`*

Split a title on slashes and return a slice of the resulting path segments. With no slice arguments the whole title is returned. The second argument limits how many segments to keep counting from a starting point; the third argument is the one-based starting segment, where a negative value counts from the end. A namespace prefix before a colon is kept as part of the first segment.

**Test Cases:** `rcb_tests/public_test_cases/feature9_1_titleparts.json`

```json
{
    "description": "Split a page title on slashes and return a slice of the resulting path segments. With no slice arguments the whole title is returned. The second argument limits how many segments to keep counting from a starting point; the third argument is the one-based starting segment, where a negative value counts from the end. A namespace prefix before a colon is kept as part of the first segment.",
    "cases": [
        {"input": {"wikitext": "{{#titleparts:foo}}"}, "expected_output": "foo"},
        {"input": {"wikitext": "{{#titleparts:foo/bar/baz}}"}, "expected_output": "foo/bar/baz"},
        {"input": {"wikitext": "{{#titleparts:Help:foo/bar/baz}}"}, "expected_output": "Help:foo/bar/baz"}
    ]
}
```

*9.2 Namespace name — `{{ns:id}}`*

Resolve a namespace identifier to its canonical namespace name. The argument may be a namespace number or any recognised alias of the namespace (including legacy aliases that map to the modern name). An unrecognised namespace yields the empty string.

**Test Cases:** `rcb_tests/public_test_cases/feature9_2_namespace_name.json`

```json
{
    "description": "Resolve a namespace identifier to its canonical namespace name. The argument may be a namespace number or any recognised alias of the namespace (including legacy aliases that map to the modern name). An unrecognised namespace yields the empty string.",
    "cases": [
        {"input": {"wikitext": "{{ns:6}}"}, "expected_output": "File"},
        {"input": {"wikitext": "{{ns:File}}"}, "expected_output": "File"}
    ]
}
```

---

### Feature 10: Page-Name Magic Words

**As a developer**, I want magic words that report parts of the current page's title, so templates can adapt to where they are used.

**Expected Behavior / Usage:**

These magic words report parts of the title of the page being rendered (taken from the request's `title`), or of an explicit page given as an argument (`{{PAGENAME:Some:Title/x}}`). They derive: the full title (`FULLPAGENAME`), the title without its namespace (`PAGENAME`), the base title dropping the last slash segment (`BASEPAGENAME`), the root title — the first slash segment (`ROOTPAGENAME`), the final sub-page segment (`SUBPAGENAME`), the namespace name (`NAMESPACE`), the associated talk-page title (`TALKPAGENAME`), and the subject/talk namespace names (`SUBJECTSPACE`/`TALKSPACE`). The double-`E` variants (e.g. `FULLPAGENAMEE`, `ROOTPAGENAMEE`) additionally apply title encoding, replacing spaces with underscores.

**Test Cases:** `rcb_tests/public_test_cases/feature10_pagename.json`

```json
{
    "description": "Magic words that report parts of the title of the page being rendered (or, when given an explicit page argument, of that page). These derive the full title, the title without its namespace, the base title (dropping the last slash segment), the root title (the first slash segment), the final sub-page segment, the namespace name, the associated talk-page title and subject/talk namespace names. The double-E variants additionally apply title encoding, replacing spaces with underscores.",
    "cases": [
        {"input": {"title": "Tt", "wikitext": "{{FULLPAGENAME}}"}, "expected_output": "Tt"},
        {"input": {"title": "Help:Tt/doc", "wikitext": "{{FULLPAGENAME}}"}, "expected_output": "Help:Tt/doc"},
        {"input": {"title": "Help:Tt/doc", "wikitext": "{{PAGENAME}}"}, "expected_output": "Tt/doc"}
    ]
}
```

---

### Feature 11: Date & Time Formatting

**As a developer**, I want to parse and reformat dates and times, so templates can present temporal values in any required style.

**Expected Behavior / Usage:**

*11.1 Time formatting — `{{#time:format|date|lang}}`*

Parse a date/time expression and format it according to a format string of single-character codes. Supported codes include calendar fields (`Y`/`y` year, `o` ISO-week-year, `n`/`m` month number, `M`/`F` month name, `j`/`d` day, `D`/`l` weekday name, `N`/`w` weekday number, `W` ISO week, `z` day-of-year, `t` days-in-month, `L` leap-year flag), clock fields (`g`/`h`/`G`/`H` hours, `i` minutes, `s` seconds, `A` AM/PM), the time-zone name (`e`), and combined ISO (`c`) and RFC (`r`) stamps. An optional language argument localises names; literal text may be quoted with double quotes. The input date is interpreted in UTC.

**Test Cases:** `rcb_tests/public_test_cases/feature11_1_time.json`

```json
{
    "description": "Parse a date/time expression and format it according to a format string of single-character codes. Supported codes include calendar fields (Y/y year, o ISO-week-year, n/m month number, M/F month name, j/d day, D/l weekday name, N/w weekday number, W ISO week, z day-of-year, t days-in-month, L leap-year flag), clock fields (g/h/G/H hours, i minutes, s seconds, A AM/PM), the time-zone name (e) and combined ISO (c) and RFC (r) stamps. An optional language argument localises names; literal text may be quoted. The input date is interpreted in UTC.",
    "cases": [
        {"input": {"wikitext": "{{#time:Y|January 3, 1999}}"}, "expected_output": "1999"},
        {"input": {"wikitext": "{{#time:y|January 3, 1999}}"}, "expected_output": "99"},
        {"input": {"wikitext": "{{#time:L|January 3, 2004}}"}, "expected_output": "1"}
    ]
}
```

*11.2 Date reformatting — `{{#dateformat:date|style}}` / `{{#formatdate:date|style}}`*

Reformat a date written in any recognised form into a requested style: `ymd`, `mdy`, `dmy`, or `ISO 8601` (also the default). A date missing its day or year is reformatted with the parts it has. Text that does not parse as a date is returned unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature11_2_dateformat.json`

```json
{
    "description": "Reformat a date written in any recognised form into a requested style: ymd, mdy, dmy, or ISO 8601 (also the default). A date missing its day or year is reformatted with the parts it has. Text that does not parse as a date is returned unchanged.",
    "cases": [
        {"input": {"wikitext": "{{#dateformat:25 dec 2009|ymd}}"}, "expected_output": "2009 Dec 25"},
        {"input": {"wikitext": "{{#dateformat:25 dec 2009|mdy}}"}, "expected_output": "Dec 25, 2009"},
        {"input": {"wikitext": "{{#dateformat:25 dec 2009|ISO 8601}}"}, "expected_output": "2009-12-25"}
    ]
}
```

---

### Feature 12: HTML Tag Construction — `{{#tag:name|content|attr=value...}}`

**As a developer**, I want to build an HTML element from a tag name, content and attributes, so templates can emit safe markup.

**Expected Behavior / Usage:**

Construct an HTML element from a tag name, optional inner content and optional named attributes. An element with no content is emitted as a self-closing tag (`<br />`); otherwise an open/close pair wraps the content. Attribute values are HTML-escaped (quotes and other sensitive characters become entities). The special `nowiki` name is not a real element: it returns its content without surrounding tags.

**Test Cases:** `rcb_tests/public_test_cases/feature12_tag.json`

```json
{
    "description": "Construct an HTML element from a tag name, optional inner content and optional named attributes. An element with no content is emitted as a self-closing tag; otherwise an open/close pair wraps the content. Attribute values are HTML-escaped (quotes and other sensitive characters become entities). The special nowiki tag is not a real element: it returns its content without surrounding tags.",
    "cases": [
        {"input": {"wikitext": "{{#tag:br}}"}, "expected_output": "<br />"},
        {"input": {"wikitext": "{{#tag:div|foo bar}}"}, "expected_output": "<div>foo bar</div>"},
        {"input": {"wikitext": "{{#tag:div|foo bar|class=foo|id=me}}"}, "expected_output": "<div class=\"foo\" id=\"me\">foo bar</div>"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the expansion engine and its built-in functions, with the expansion core, scope/argument model, and individual functions in separate modules. The core logic must be decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (entry point) that acts as a client to the core engine — logically (and ideally physically) separated from it. It reads a single JSON request from stdin (`{"title"?, "wikitext", "pages"?}`), registers the supplied pages (a `Template:` prefix marks a transcludable template), expands the `wikitext` against the page named by `title` (default `Tt`), and prints the raw expanded string to stdout, matching the per-feature contracts above. Domain errors (unknown templates, malformed expressions, etc.) are rendered into the output text as specified; native host exceptions must never leak to stdout.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same default convention as the single-bar argument list
- follow the entity encoding pattern used for control characters
