## Product Requirement Document

# Symbolic Expression Engine - Reader, Identifier Normalizer, and Evaluator

## Project Goal

Build a small language toolkit that turns parenthesized, prefix-notation source text into structured data, normalizes program identifiers into a portable ASCII form (and back), evaluates a core set of prefix operators, and renders runtime values into a canonical, re-readable text form. The toolkit lets developers embed a compact symbolic-expression language — read it, inspect its structure, evaluate it, and print its results — without hand-rolling a tokenizer, an identifier escaper, or a value printer.

---

## Background & Problem

Without this toolkit, a developer who wants to host a small Lisp-like surface syntax must write a reader that balances brackets and classifies number/string/symbol tokens, invent an escaping scheme so that names containing hyphens, trailing question marks, operator glyphs, or non-ASCII characters can live as plain identifiers in a host runtime, and write a printer that turns results back into source the reader can re-consume. Each of these is fiddly, easy to get subtly wrong (digit-group separators, discard markers, chained comparisons, round-tripping of collections), and tedious to keep consistent.

With this toolkit, the four concerns are provided as cohesive, well-defined behaviors: a **reader** that produces a typed syntax tree, a reversible **identifier normalizer**, a small **evaluator** for prefix operators, and a canonical **value representation** that round-trips. Each behavior is exercised through a single neutral command interface so it can be validated as a black box.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This project has several distinct responsibilities (reading/tokenizing, identifier normalization, evaluation, value rendering, plus an I/O adapter). It MUST NOT be a single "god file"; separate the reader, the normalizer, the evaluator, the value printer, and the I/O adapter into distinct logical units. Do not over-engineer, but avoid a monolith.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases in "Core Features" are a **black-box contract** for the execution adapter, NOT the internal data model. The core reader/evaluator/printer must remain decoupled from stdin/stdout and JSON parsing. The adapter alone translates JSON commands into idiomatic core calls and renders results.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility:** Keep tokenizing, structural parsing, normalization, evaluation, and output formatting in separate units.
   - **Open/Closed:** Adding a new operator or a new renderable value type must not require rewriting the dispatch core.
   - **Liskov Substitution:** All node/value types must be uniformly substitutable wherever a node/value is expected.
   - **Interface Segregation:** Keep the reader, evaluator, and printer interfaces small and cohesive.
   - **Dependency Inversion:** The adapter depends on abstract core operations, not on low-level I/O details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The core API must be elegant and idiomatic to the target language, hiding internal complexity.
   - **Resilience:** Edge cases (unbalanced brackets, premature end of input, unsupported operator arity, invalid names) must be modeled as explicit, typed error categories rather than generic faults, and rendered to the contract as normalized `error=<category>` lines.

---

## Core Features

### Feature 1: Reversible Identifier Normalization

**As a developer**, I want to convert arbitrary source-level names into portable ASCII identifiers and recover the originals, so I can store names containing hyphens, question marks, operator glyphs, or non-ASCII characters in any host runtime that only accepts conventional identifiers.

**Expected Behavior / Usage:**

*1.1 Normalize a name — convert a source-level name to a portable ASCII identifier*

Given a name string, produce a valid ASCII identifier. The rules: a hyphen between two word characters becomes an underscore; a trailing `?` is removed and an `is_` prefix is added to the core of the name; any character that cannot appear in an identifier (a leading or standalone hyphen, an operator glyph, a space, a non-ASCII letter or symbol) is replaced by a reversible escape of the form `hyx_...X<charname>X...`, where `<charname>` is the Unicode name of the character (lowercased, spaces→underscores, `-`→`H`) or, if unnamed, its code point as `U<hex>`. Names that are already valid identifiers — including leading/trailing double underscores (dunders) — pass through unchanged. The output is the resulting identifier string.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_mangle.json`

```json
{
    "description": "Normalize an arbitrary source-level name (which may contain hyphens, a trailing question mark, operator glyphs, spaces, or non-ASCII characters) into a portable ASCII identifier. Hyphens between word characters become underscores; a trailing '?' becomes an 'is_' prefix on the core name; leading/standalone hyphens and any other non-identifier characters are escaped into a reversible 'hyx_...X...X' encoding using the Unicode character name (or code point). Strings that are already valid identifiers (including dunders) pass through unchanged.",
    "cases": [
        {"input": {"op": "mangle", "name": "-"}, "expected_output": "hyx_XhyphenHminusX"},
        {"input": {"op": "mangle", "name": "__dunder-name__"}, "expected_output": "__dunder_name__"},
        {"input": {"op": "mangle", "name": "--?"}, "expected_output": "[specific mangling prefix for named test cases]"},
        {"input": {"op": "mangle", "name": "if"}, "expected_output": "if"},
        {"input": {"op": "mangle", "name": " "}, "expected_output": "hyx_XspaceX"},
        {"input": {"op": "mangle", "name": "___ab-cd?"}, "expected_output": "___is_ab_cd"}
    ]
}
```

*1.2 Recover a name — invert the normalization back to the source-level name*

Given a normalized identifier, reconstruct the original name: each `hyx_...X<charname>X...` escape is decoded back to its character, an `is_` prefix becomes a trailing `?`, and underscores that were produced from hyphens are restored to hyphens. Identifiers that contain no escapes (including bare underscores and dunders) are returned unchanged. The output is the recovered name string.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_unmangle.json`

```json
{
    "description": "Recover a source-level name from a portable ASCII identifier, inverting the normalization: 'hyx_...X...X' escapes are decoded back to their original characters, an 'is_' prefix becomes a trailing '?', and underscores that originated from hyphens are restored to hyphens. Identifiers with no special encoding (including plain underscores and dunders) are returned unchanged.",
    "cases": [
        {"input": {"op": "unmangle", "identifier": "hyx_XhyphenHminusX"}, "expected_output": "-"},
        {"input": {"op": "unmangle", "identifier": "__dunder_name__"}, "expected_output": "__dunder-name__"},
        {"input": {"op": "unmangle", "identifier": "___is_ab_cd"}, "expected_output": "___ab-cd?"},
        {"input": {"op": "unmangle", "identifier": "_"}, "expected_output": "_"}
    ]
}
```

---

### Feature 2: Reading Source into a Typed Syntax Tree

**As a developer**, I want to read parenthesized prefix-notation source text into a structured, typed tree, so I can inspect and process program structure without writing a tokenizer or bracket matcher.

**Expected Behavior / Usage:**

Each top-level form is rendered as a node of the form `Type(...)`. Atomic nodes are `Integer(n)`, `Float(x)`, `Complex(z)`, `String(text)`, `Bytes(text)`, `Keyword(name)`, and `Symbol(text)`. Compound nodes list their children space-separated inside the parentheses: `Expression(...)` for round-paren forms, `[a common collection type in the data model]`, `Set(...)`, and `Dict(...)`. Multiple top-level forms are each printed on their own line. Malformed input does not yield a node; it yields a normalized error line (see 2.4).

*2.1 Atomic literals — classify a single token into its typed node*

A token of digits (optionally with `_` or `,` digit-group separators, or a `0x`/`0b`/`0o` radix prefix) is an `Integer`. A numeric token with a trailing dot or an exponent is a `Float`. The bare tokens `NaN`, `Inf`, and `-Inf` are floating-point specials, but their all-lowercase spellings (`nan`, `inf`) are ordinary symbols. A double-quoted literal is a `String`; a `b`-prefixed quoted literal is `Bytes`; a token beginning with `:` is a `Keyword`; any other bare token is a `Symbol`. A `Float` value is printed with a decimal point or `nan`/`inf`/`-inf` for specials.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_atoms.json`

```json
{
    "description": "Read source text and report the atomic literals it produces, each rendered as a typed node 'Type(value)'. Integers accept '_' and ',' as digit-group separators and 0x/0b/0o radix prefixes; a trailing dot or exponent yields a floating-point number; the bare tokens NaN/Inf/-Inf are floating-point specials while their lowercase forms remain ordinary symbols. Double-quoted text becomes a string node, a 'b'-prefixed literal becomes a bytes node, a leading-colon token becomes a keyword node, and any other bare token becomes a symbol node. Each top-level form is rendered on its own line.",
    "cases": [
        {"input": {"op": "parse", "source": "(foo bar)"}, "expected_output": "Expression(Symbol(foo) Symbol(bar))"},
        {"input": {"op": "parse", "source": "(foo 2.)"}, "expected_output": "Expression(Symbol(foo) Float(2.0))"},
        {"input": {"op": "parse", "source": "1,000_000"}, "expected_output": "Integer(1000000)"},
        {"input": {"op": "parse", "source": "NaN"}, "expected_output": "Float(nan)"},
        {"input": {"op": "parse", "source": "nan"}, "expected_output": "Symbol(nan)"},
        {"input": {"op": "parse", "source": "b\"hello\""}, "expected_output": "Bytes(hello)"},
        {"input": {"op": "parse", "source": ":kw"}, "expected_output": "Keyword(kw)"}
    ]
}
```

*2.2 Bracketed collections — read the four collection forms and nest them*

Round parentheses read as an ordered expression node; square brackets as a list node; curly braces as a mapping node whose body is a flat sequence of alternating keys and values; and a `#{...}` form as a set node that **preserves duplicate items in order** (it is a syntactic collection, not a deduplicated runtime set). All four forms nest arbitrarily; an empty form yields a childless node such as `List()` or `Expression()`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_collections.json`

```json
{
    "description": "Read source text containing the four bracketed collection forms and report the parsed structure as nested typed nodes. Round parentheses produce an ordered call/expression node, square brackets a list node, curly braces a mapping node whose contents are a flat sequence of alternating keys and values, and a '#{...}' form a set node that preserves duplicate items in order. Collections nest arbitrarily.",
    "cases": [
        {"input": {"op": "parse", "source": "{foo bar bar baz}"}, "expected_output": "Dict(Symbol(foo) Symbol(bar) Symbol(bar) Symbol(baz))"},
        {"input": {"op": "parse", "source": "#{1 2 1 1 2 1}"}, "expected_output": "Set(Integer(1) Integer(2) Integer(1) Integer(1) Integer(2) Integer(1))"},
        {"input": {"op": "parse", "source": "(bar #{foo bar baz})"}, "expected_output": "Expression(Symbol(bar) Set(Symbol(foo) Symbol(bar) Symbol(baz)))"},
        {"input": {"op": "parse", "source": "[]"}, "expected_output": "List()"}
    ]
}
```

*2.3 Discard marker — drop the next form during reading*

A `#_` marker discards exactly the single form that immediately follows it, contributing nothing to the result. Markers may be stacked (`#_ #_1 2` discards two forms), may be nested, and apply identically at top level and inside any collection. A discarded form is removed even when it is itself a large nested structure.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_discard.json`

```json
{
    "description": "Read source text containing discard markers and report the surviving structure. A '#_' marker discards exactly the single form that follows it; markers may be stacked to skip several forms in a row, may be nested, and apply equally at top level and inside any collection. Discarded forms contribute nothing to the result, even when they themselves are large nested structures.",
    "cases": [
        {"input": {"op": "parse", "source": "#_1 #_2 #_3"}, "expected_output": ""},
        {"input": {"op": "parse", "source": "0 #_1 2"}, "expected_output": "Integer(0)\nInteger(2)"},
        {"input": {"op": "parse", "source": "{#_0 1 2}"}, "expected_output": "Dict(Integer(1) Integer(2))"},
        {"input": {"op": "parse", "source": "[1 2 #_[a b c [d e [f g] h]] 3 4]"}, "expected_output": "List(Integer(1) Integer(2) Integer(3) Integer(4))"}
    ]
}
```

*2.4 Reader error categories — normalize malformed input*

Malformed source yields one of two normalized error lines instead of a node. When input opens a collection or a string but the text ends before the matching close, the result is `error=premature_end_of_input`. When the input is structurally invalid in a way that cannot be a prefix of any valid input — an unmatched closing bracket, a lone quote introducing nothing, or an attribute access on something that is not a name — the result is `error=lex_error`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_parse_errors.json`

```json
{
    "description": "Reading malformed source surfaces one of two normalized error categories instead of a value. An input that opens a collection or string but reaches end-of-text before the matching close is reported as a premature-end-of-input condition; an input that is structurally invalid (an unmatched closing bracket, a lone quote that introduces nothing, or an attempt to take an attribute on something that is not a name) is reported as a generic lex error.",
    "cases": [
        {"input": {"op": "parse", "source": "(foo"}, "expected_output": "error=premature_end_of_input"},
        {"input": {"op": "parse", "source": "(foo \"bar"}, "expected_output": "error=premature_end_of_input"},
        {"input": {"op": "parse", "source": "(bar))"}, "expected_output": "error=lex_error"},
        {"input": {"op": "parse", "source": "1.foo"}, "expected_output": "error=lex_error"}
    ]
}
```

---

### Feature 3: Name Admissibility Checks

**As a developer**, I want to ask whether a given string may serve as a bare identifier or as a keyword, so I can validate names before constructing program elements from them.

**Expected Behavior / Usage:**

*3.1 Symbol admissibility — validate a bare identifier name*

A bare identifier may contain word characters, hyphens, underscores, or arbitrary printable non-ASCII letters, but no surrounding punctuation. An empty string, a purely numeric token, a token that begins with `:`, or any token containing whitespace or bracket/paren punctuation is **not** a valid identifier. A valid name is echoed back as `name=<name>`; an invalid one yields `[standard 404 or unexpected error response]`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_symbol.json`

```json
{
    "description": "Validate whether a given name is admissible as a bare identifier (symbol). A valid name (containing word characters, hyphens, underscores, or arbitrary printable non-ASCII letters, with no spaces and no surrounding punctuation) is accepted and echoed back. An empty string, a purely numeric token, a colon-prefixed token, or any name containing whitespace or bracket/paren punctuation is rejected as an invalid symbol.",
    "cases": [
        {"input": {"op": "check_symbol", "name": "foo-bar"}, "expected_output": "name=foo-bar"},
        {"input": {"op": "check_symbol", "name": "✈é😂⁂"}, "expected_output": "name=✈é😂⁂"},
        {"input": {"op": "check_symbol", "name": "5"}, "expected_output": "[standard 404 or unexpected error response]"},
        {"input": {"op": "check_symbol", "name": "foo bar"}, "expected_output": "[standard 404 or unexpected error response]"}
    ]
}
```

*3.2 Keyword admissibility — validate a keyword name*

Keyword names are more permissive than bare identifiers: the empty string, a purely numeric token, and a token beginning with `:` are all admissible, and the stored name is the input verbatim. Only names containing whitespace or bracket/paren punctuation are rejected. A valid name yields `name=<name>` (so the empty name yields `name=`); an invalid one yields `error=invalid_keyword`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_keyword.json`

```json
{
    "description": "Validate whether a given name is admissible as a keyword and report its stored name. Keywords are more permissive than bare symbols: the empty string, a purely numeric token, and a colon-prefixed token are all accepted (the stored name is the input verbatim). Only names containing whitespace or bracket/paren punctuation are rejected as invalid keywords.",
    "cases": [
        {"input": {"op": "check_keyword", "name": ""}, "expected_output": "name="},
        {"input": {"op": "check_keyword", "name": ":foo"}, "expected_output": "name=:foo"},
        {"input": {"op": "check_keyword", "name": "5"}, "expected_output": "name=5"},
        {"input": {"op": "check_keyword", "name": "foo bar"}, "expected_output": "error=invalid_keyword"}
    ]
}
```

---

### Feature 4: Evaluating Prefix Operator Expressions

**As a developer**, I want to evaluate a prefix-notation expression of built-in operators and get the resulting value, so I can run small computations expressed in the surface syntax. The result is rendered with the canonical value representation of Feature 5. When an operator is applied with an arity it does not support, the result is the normalized line `error=invalid_operation`.

**Expected Behavior / Usage:**

*4.1 Arithmetic operators — variadic numeric and sequence arithmetic*

`+` and `*` are variadic with identity results for zero arguments (`0` and `1`); `+` also concatenates strings/lists and `*` repeats them. `-` and `/` require at least one argument; unary `-` negates and unary `/` reciprocates. Division `/` always yields a floating-point result. `//` (integer division), `%` (modulo), and `**` (exponentiation) combine operands pairwise from the left. Unsupported arity (e.g. `(-)`, `(/)`, `(**)` with too few operands) yields `error=invalid_operation`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_arithmetic.json`

```json
{
    "description": "Evaluate a prefix arithmetic expression and report the resulting value. The operators are variadic. '+' and '*' have identity results when called with no arguments (0 and 1 respectively) and also concatenate/repeat strings and lists; '-' and '/' require at least one argument; division always yields a floating-point result; integer-division '//', modulo '%', and exponentiation '**' apply pairwise left to right. Calling an operator with an arity it does not support is reported as a normalized invalid-operation error.",
    "cases": [
        {"input": {"op": "evaluate", "source": "(+)"}, "expected_output": "0"},
        {"input": {"op": "evaluate", "source": "(+ 1 2 3 4)"}, "expected_output": "10"},
        {"input": {"op": "evaluate", "source": "(* \"ke\" 4)"}, "expected_output": "\"kekekeke\""},
        {"input": {"op": "evaluate", "source": "(/ 8 2)"}, "expected_output": "4.0"},
        {"input": {"op": "evaluate", "source": "(// 16 5)"}, "expected_output": "3"},
        {"input": {"op": "evaluate", "source": "(-)"}, "expected_output": "error=invalid_operation"}
    ]
}
```

*4.2 Comparison and boolean operators — chained relations and short-circuit logic*

Comparison operators `<`, `>`, `<=`, `>=`, `=`, `!=` accept two or more operands and are **chained**: every adjacent pair must satisfy the relation for the overall result to be true. Boolean `and` returns its last operand when all are truthy (otherwise the first falsy one), `or` returns its first truthy operand (otherwise the last), and `not` negates the truthiness of its single operand. Empty `and` yields `True`; empty `or` yields `None`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_comparison.json`

```json
{
    "description": "Evaluate a prefix comparison or boolean expression and report the resulting value. Comparison operators (< > <= >= = !=) accept two or more operands and are chained: each adjacent pair must satisfy the relation for the overall result to be true. The boolean 'and' returns its last operand when all are truthy (and the first falsy one otherwise), 'or' returns its first truthy operand (or the last otherwise), and 'not' negates the truthiness of its single operand. Empty 'and' yields true and empty 'or' yields none.",
    "cases": [
        {"input": {"op": "evaluate", "source": "(< 1 2 3)"}, "expected_output": "True"},
        {"input": {"op": "evaluate", "source": "(< 1 3 2)"}, "expected_output": "False"},
        {"input": {"op": "evaluate", "source": "(and 1 0 3)"}, "expected_output": "0"},
        {"input": {"op": "evaluate", "source": "(or 0 False 5)"}, "expected_output": "5"},
        {"input": {"op": "evaluate", "source": "(not 0)"}, "expected_output": "True"}
    ]
}
```

*4.3 Bitwise operators — bit combination, shifting, and complement*

`&`, `|`, `^` combine integer operands bit by bit; `|` has identity result `0` for zero arguments. `<<` and `>>` shift left and right, accepting extra operands as successive shift amounts. `~` takes the bitwise complement of its single operand. Some operators forbid certain arities (`^` with three operands, or a shift with fewer than two operands); an unsupported arity yields `error=invalid_operation`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_bitwise.json`

```json
{
    "description": "Evaluate a prefix bitwise expression and report the resulting value. '&', '|', and '^' combine integer operands bit by bit; '<<' and '>>' shift left and right and accept extra operands as successive shift amounts; '~' takes the bitwise complement of its single operand. '|' has an identity result of 0 when called with no arguments. An arity an operator does not support (for example unary '&', or '^' with three operands) is reported as a normalized invalid-operation error.",
    "cases": [
        {"input": {"op": "evaluate", "source": "(| 3 5)"}, "expected_output": "7"},
        {"input": {"op": "evaluate", "source": "(^ 3 5)"}, "expected_output": "6"},
        {"input": {"op": "evaluate", "source": "(<< 5 2 3)"}, "expected_output": "160"},
        {"input": {"op": "evaluate", "source": "(^ 7 6 4)"}, "expected_output": "error=invalid_operation"}
    ]
}
```

*4.4 Membership and indexing operators — element tests and nested lookup*

`in` reports whether the first operand is an element of the second, and `not-in` reports the negation; both require exactly two operands. `get` indexes into a collection and accepts additional indices to descend through nested collections in a single call (e.g. indexing a string returns the character at that position; a chain of keys walks a nested mapping).

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_membership.json`

```json
{
    "description": "Evaluate a prefix membership or indexing expression and report the resulting value. 'in' reports whether the first operand is an element of the second, and 'not-in' reports the negation; both require two operands. 'get' indexes into a collection and accepts additional indices to descend through nested collections in one call.",
    "cases": [
        {"input": {"op": "evaluate", "source": "(in 2 [1 2])"}, "expected_output": "True"},
        {"input": {"op": "evaluate", "source": "(not-in 3 [1 2])"}, "expected_output": "True"},
        {"input": {"op": "evaluate", "source": "(get \"hello\" 1)"}, "expected_output": "\"e\""},
        {"input": {"op": "evaluate", "source": "(get {\"x\" {\"y\" {\"z\" 12}}} \"x\" \"y\" \"z\")"}, "expected_output": "12"}
    ]
}
```

---

### Feature 5: Canonical Value Representation

**As a developer**, I want runtime values printed in a canonical, re-readable text form, so I can display results, log them, or feed them back into the reader and obtain an equivalent value.

**Expected Behavior / Usage:**

A value is rendered into the same surface syntax that would produce it. Numbers, keywords, strings, and byte strings render as their literals (keywords with a leading `:`, byte strings with a `b` prefix). Lists render as `[...]`, tuples as `#(...)`, sets as `#{...}`, and mappings as `{key value  key value}` with **two spaces** separating consecutive entries. Common standard-library values render as a call-like form naming the constructor followed by its arguments: a fixed-precision fraction as `(Fraction n d)`, a double-ended queue as `(deque [...])`, a multiset counter as `(Counter {...})`, a frozen set as `(frozenset #{...})`, a numeric range as `(range start stop step)`, a slice object as `(slice ...)`, a compiled regular expression as `(re.compile "...")`, and a date as `(datetime.date y m d)`. The representation round-trips: reading the rendered text reproduces an equivalent value.

**Test Cases:** `rcb_tests/public_test_cases/feature5_representation.json`

```json
{
    "description": "Evaluate a value-producing expression and report its canonical, re-readable text representation. The representation round-trips: numbers, keywords, strings and byte strings, lists, tuples, sets, and mappings render back into the same surface syntax that would produce them, with mapping entries separated by a double space. Common standard-library values (fixed-precision fractions, double-ended queues, multiset counters, frozen sets, numeric ranges, slice objects, compiled regular expressions, and dates/times) render as a call-like form naming the constructor and its arguments.",
    "cases": [
        {"input": {"op": "evaluate", "source": ":mykeyword"}, "expected_output": ":mykeyword"},
        {"input": {"op": "evaluate", "source": "#(1 2 3)"}, "expected_output": "#(1 2 3)"},
        {"input": {"op": "evaluate", "source": "{\"a\" 1  \"b\" 2}"}, "expected_output": "{\"a\" 1  \"b\" 2}"},
        {"input": {"op": "evaluate", "source": "(Counter [15 15 15 15])"}, "expected_output": "(Counter {15 4})"},
        {"input": {"op": "evaluate", "source": "(range 0 5 2)"}, "expected_output": "(range 0 5 2)"},
        {"input": {"op": "evaluate", "source": "(re.compile \"foo\")"}, "expected_output": "(re.compile \"foo\")"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the reader, the reversible identifier normalizer, the prefix-operator evaluator, and the canonical value printer described above. Its physical structure MUST strictly align with the "Scale-Driven Code Organization" constraint — multiple cohesive units, not a monolithic file — while remaining free of over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to the core system. It reads a single JSON command object from stdin (`{"op": ..., ...}`), invokes the appropriate core operation, and prints the result to stdout, strictly matching the per-leaf-feature contracts above (including the normalized `error=<category>` lines). This adapter must be logically and physically separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_mangle.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_mangle@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same structure as the nested collections module
- apply the same mapping as the dictionary parser
