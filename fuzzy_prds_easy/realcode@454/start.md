## Product Requirement Document

# Bytecode Decompiler Support Toolkit - Input/Output Behavior Specification

## Project Goal

Build a collection of pure, reusable building blocks that a bytecode-to-source decompiler needs in order to turn compiled class metadata back into readable source-level information. The toolkit covers source-literal rendering, identifier validation, type-descriptor parsing, version comparison, lightweight string-view operations, navigation history, command-line option parsing, output-path resolution, an attribute set, a class-hierarchy query, and certificate inspection. Each block has a small, well-defined input/output contract so the decompiler's higher layers can rely on them without re-implementing fiddly low-level rules.

---

## Background & Problem

A decompiler repeatedly needs the same low-level helpers: it must re-escape string and char constants into valid source literals, validate and sanitize names, parse the compact wire-format type descriptors emitted by a compiler into human-readable types, resolve where output files should go, and so on. Without a dedicated toolkit, each of these rules ends up duplicated and subtly inconsistent across the code base, which produces output that does not round-trip and is hard to test.

With this toolkit, every such rule lives behind one tiny, independently testable function with a stable contract. Callers feed in raw data (a string, a descriptor, a list of option tokens, certificate bytes) and get back a deterministic, language-neutral result they can render or act on directly.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This domain has many distinct responsibilities (literal escaping, descriptor parsing, path resolution, CLI parsing, certificate decoding, ...). It MUST NOT be a single "god file". Group related responsibilities into cohesive modules (e.g. text/literals, type descriptors, CLI/config, GUI-support utilities, crypto inspection) under a clear `src/` tree, with the execution adapter kept separate.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below define a **black-box contract for the execution adapter**, not the internal data model. The core helpers must take and return ordinary in-language values (strings, lists, enums, booleans, integers) and must not know anything about JSON, stdin/stdout, or the wire format used by the tests. The adapter alone translates JSON commands into idiomatic calls and renders results.

3. **Adherence to SOLID Design Principles:** Separate parsing, validation, core computation, and output formatting. Each helper has a single responsibility; the parsers are open for new descriptor forms without rewriting existing ones; the adapter depends on the helpers' abstractions, not the reverse.

4. **Robustness & Interface Design:** The public surface of each helper must be idiomatic and minimal. Edge cases (empty input, out-of-range indices, malformed descriptors, unknown options) must be handled deterministically rather than throwing generic faults. When a routine cannot produce a value it must degrade to a well-defined neutral result (e.g. an empty collection or a null type), and the adapter must normalize any error into a neutral, language-independent category line.

---

## Core Features

### Feature 1: Source String-Literal Rendering

**As a developer**, I want to turn an arbitrary text value into a valid double-quoted source string literal, so I can emit constants that compile and round-trip.

**Expected Behavior / Usage:**

The input command is `{"feature":"string_escape","escape_unicode":<bool>,"input":<text>}`. The result is the text rendered as a double-quoted literal on one `escaped=` line. Inside the quotes: a newline becomes `\n`, a tab `\t`, a carriage return `\r`, a backspace `\b`, a form-feed `\f`; a backslash becomes `\\` and a double-quote becomes `\"`; a single-quote is left unchanged; an empty input yields just `""`. When `escape_unicode` is true, every character whose code point is 127 or greater is emitted as a four-hex-digit `\uXXXX` sequence. The surrounding double-quotes are always part of the output.

**Test Cases:** `rcb_tests/public_test_cases/feature1_string_escape.json`

```json
{
    "description": "Render a raw text value as a double-quoted literal: control characters become two-character escape sequences (\\n, \\t, \\r, \\b, \\f), backslash and double-quote are escaped, a single-quote is left as-is, and (with unicode escaping on) any character at or above code point 127 becomes a \\uXXXX sequence. Output is the quoted literal on an 'escaped=' line.",
    "cases": [
        {"input": {"feature": "string_escape", "escape_unicode": true, "input": ""}, "expected_output": "escaped=\"\"\n"},
        {"input": {"feature": "string_escape", "escape_unicode": true, "input": "\n"}, "expected_output": "escaped=\"\\n\"\n"},
        {"input": {"feature": "string_escape", "escape_unicode": true, "input": "\\"}, "expected_output": "escaped=\"\\\\\"\n"},
        {"input": {"feature": "string_escape", "escape_unicode": true, "input": "\""}, "expected_output": "escaped=\"\\\"\"\n"},
        {"input": {"feature": "string_escape", "escape_unicode": true, "input": "ሴ"}, "expected_output": "escaped=\"\[a specific escape sequence placeholder]\"\n"}
    ]
}
```

---

### Feature 2: Source Char-Literal Rendering

**As a developer**, I want to turn a single character into a valid single-quoted source char literal, so I can emit character constants correctly.

**Expected Behavior / Usage:**

The input command is `{"feature":"char_escape","input":<single character>}`. The result is the character rendered as a single-quoted literal on one `escaped=` line. A printable character is kept verbatim; a single-quote is escaped as `\'`; common whitespace control characters use their two-character escapes (e.g. newline → `\n`); any other control character (such as the NUL character) becomes a four-hex-digit `\uXXXX` sequence. The input must be exactly one character.

**Test Cases:** `rcb_tests/public_test_cases/feature2_char_escape.json`

```json
{
    "description": "Render a single character as a single-quoted literal: printable characters are kept verbatim, a single-quote is escaped, common whitespace control characters become their two-character escapes, and other control characters (such as the NUL character) become a four-digit \\uXXXX sequence. Output is the quoted literal on an 'escaped=' line.",
    "cases": [
        {"input": {"feature": "char_escape", "input": "a"}, "expected_output": "escaped='a'\n"},
        {"input": {"feature": "char_escape", "input": "\n"}, "expected_output": "escaped='\\n'\n"},
        {"input": {"feature": "char_escape", "input": "'"}, "expected_output": "escaped='\\''\n"},
        {"input": {"feature": "char_escape", "input": "\u0000"}, "expected_output": "escaped='\\u0000'\n"}
    ]
}
```

---

### Feature 3: Fully-Qualified Identifier Validation

**As a developer**, I want to check whether a dotted name is a legal fully-qualified identifier, so I can decide if a name is safe to emit or must be sanitized.

**Expected Behavior / Usage:**

The input command is `{"feature":"identifier_validation","input":<name>}`. The result is one `valid=` line carrying `true` or `false`. A name is valid only if it is non-empty and every dot-separated segment is itself a valid identifier: it must start with a letter, underscore or dollar sign and continue only with letters, digits, underscore or dollar sign, and all characters must be printable ASCII. An empty string, a bare digit, a segment starting with a digit, a leading dot, and an empty segment caused by consecutive dots are all invalid.

**Test Cases:** `rcb_tests/public_test_cases/feature3_identifier_validation.json`

```json
{
    "description": "Decide whether a dotted name is a valid fully-qualified identifier: every dot-separated segment must be a non-empty identifier that starts with a letter / underscore / dollar and continues with letters, digits, underscore or dollar; empty strings, segments starting with a digit, leading dots and empty segments (consecutive dots) are all invalid. Output is a single 'valid=' line.",
    "cases": [
        {"input": {"feature": "identifier_validation", "input": "b.C"}, "expected_output": "valid=true\n"},
        {"input": {"feature": "identifier_validation", "input": "a.b.C$c"}, "expected_output": "valid=true\n"},
        {"input": {"feature": "identifier_validation", "input": "a.b.C9"}, "expected_output": "valid=true\n"},
        {"input": {"feature": "identifier_validation", "input": ""}, "expected_output": "valid=false\n"},
        {"input": {"feature": "identifier_validation", "input": ".C"}, "expected_output": "valid=false\n"},
        {"input": {"feature": "identifier_validation", "input": "b..C"}, "expected_output": "valid=false\n"}
    ]
}
```

---

### Feature 4: Type Descriptor Parsing

**As a developer**, I want to parse the compact type descriptors emitted by a compiler into readable types, so I can reconstruct field, parameter and generic-signature information.

**Expected Behavior / Usage:**

*4.1 Simple and Array Types — parse primitive, object and array descriptors*

The input command is `{"feature":"type_signature","input":<descriptor>}`. The result is a `type=` line with the human-readable type and an `object=` line with the dotted class name (or `-` when the type is not an object). An empty descriptor yields `type=null`. Single-letter primitive descriptors map to their language type name (e.g. `I` → `int`). An object descriptor has the form `L<slash/path>;` and renders as a dotted class name. Each leading `[` adds one `[]` array dimension to the element type.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_type_simple.json`

```json
{
    "description": "Parse a JVM type descriptor into a human-readable type. An empty descriptor yields the null type; primitive descriptors map to their language type names; an object descriptor 'L<path>;' becomes a dotted class name; a leading '[' adds one array dimension. Output gives the rendered 'type=' and, for object types, the dotted class name on 'object=' ('-' for non-object types).",
    "cases": [
        {"input": {"feature": "type_signature", "input": ""}, "expected_output": "type=null\n"},
        {"input": {"feature": "type_signature", "input": "I"}, "expected_output": "type=int\nobject=-\n"},
        {"input": {"feature": "type_signature", "input": "[I"}, "expected_output": "type=int[]\nobject=-\n"},
        {"input": {"feature": "type_signature", "input": "Ljava/lang/Object;"}, "expected_output": "type=java.lang.Object\nobject=java.lang.Object\n"},
        {"input": {"feature": "type_signature", "input": "[[I"}, "expected_output": "type=int[][]\nobject=-\n"}
    ]
}
```

*4.2 Generic Types — parse parameterized and nested generic descriptors*

The input command is `{"feature":"type_signature","input":<descriptor>}` where the descriptor carries type arguments. A type variable `T<name>;` renders as the bare name. A parameterized type `L<path><args>;` renders as `name<arg, ...>` with arguments comma-space separated, and nesting is supported to any depth. An inner type written as `L<outer><args>.inner;` renders the inner class joined to its enclosing class with `$`; the `object=` line carries that joined dotted name.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_type_generics.json`

```json
{
    "description": "Parse a generic type descriptor. Type variables 'T<name>;' render as the bare name; parameterized types 'L<path><args>;' render as name<arg, ...> with arguments comma-space separated; nesting is supported; an inner type written with the outer's type arguments and a '.inner' suffix renders the inner class joined to its enclosing class with '$'. Output gives the rendered 'type=' and the dotted 'object=' name.",
    "cases": [
        {"input": {"feature": "type_signature", "input": "TD;"}, "expected_output": "type=D\nobject=D\n"},
        {"input": {"feature": "type_signature", "input": "La<TV;Lb;>;"}, "expected_output": "type=a<V, b>\nobject=a\n"},
        {"input": {"feature": "type_signature", "input": "La<TD;>.c;"}, "expected_output": "type=a$c<>\nobject=a$c\n"},
        {"input": {"feature": "type_signature", "input": "La<TV;>.LinkedHashIterator<Lb$c<Ls;TV;>;>;"}, "expected_output": "type=a$LinkedHashIterator<b$c<s, V>>\nobject=a$LinkedHashIterator\n"}
    ]
}
```

*4.3 Wildcard Type Arguments — parse bounded and unbounded wildcards*

The input command is `{"feature":"type_signature","input":<descriptor>}` where the type arguments include wildcards. Inside `La<...>;`, a bare `*` is an unbounded wildcard rendered `?`; `+X` is an upper-bounded wildcard rendered `? extends X`; `-X` is a lower-bounded wildcard rendered `? super X`. Several arguments are comma-space separated, preserving order, and may mix wildcards with ordinary type arguments.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_type_wildcards.json`

```json
{
    "description": "Parse wildcard type arguments inside a parameterized type 'La<...>;'. A bare '*' is an unbounded wildcard ('?'); '+X' is an upper-bounded wildcard ('? extends X'); '-X' is a lower-bounded wildcard ('? super X'); multiple arguments are comma-space separated in order. Output renders the whole parameterized type on 'type='.",
    "cases": [
        {"input": {"feature": "type_signature", "input": "La<*>;"}, "expected_output": "type=a<?>\nobject=a\n"},
        {"input": {"feature": "type_signature", "input": "La<+Lb;>;"}, "expected_output": "type=a<? extends b>\nobject=a\n"},
        {"input": {"feature": "type_signature", "input": "La<-Lb;>;"}, "expected_output": "type=a<? super b>\nobject=a\n"},
        {"input": {"feature": "type_signature", "input": "La<**>;"}, "expected_output": "type=a<?, ?>\nobject=a\n"},
        {"input": {"feature": "type_signature", "input": "La<TV;*>;"}, "expected_output": "type=a<V, ?>\nobject=a\n"}
    ]
}
```

*4.4 Generic Parameter Declaration — parse a formal type-parameter block into variables and bounds*

The input command is `{"feature":"generic_declaration","input":<declaration>}`. A declaration has the form `<Name:Bound...;Name2:...;>`. The result starts with a `count=` line giving the number of declared variables, followed by one `var=<name> bounds=<...>` line each, in declaration order. A bound equal to plain Object is treated as no explicit bound and shown as `-`; a non-Object class bound is shown by its dotted name. A syntactically incomplete declaration yields `count=0` with no variable lines.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_generic_declaration.json`

```json
{
    "description": "Parse a formal type-parameter declaration block '<Name:Bound...;...>' into an ordered list of type variables with their bounds. A bound equal to plain Object is treated as no explicit bound ('-'); a non-Object class bound is listed by dotted name; multiple variables preserve declaration order. A syntactically incomplete block yields an empty result. Output starts with 'count=' then one 'var=... bounds=...' line per variable.",
    "cases": [
        {"input": {"feature": "generic_declaration", "input": "<T:Ljava/lang/Object;>"}, "expected_output": "count=1\nvar=T bounds=-\n"},
        {"input": {"feature": "generic_declaration", "input": "<K:Ljava/lang/Object;LongType:Ljava/lang/Object;>"}, "expected_output": "count=2\nvar=K bounds=-\nvar=LongType bounds=-\n"},
        {"input": {"feature": "generic_declaration", "input": "<ResultT:Ljava/lang/Exception;:Ljava/lang/Object;>"}, "expected_output": "count=1\nvar=ResultT bounds=java.lang.Exception\n"},
        {"input": {"feature": "generic_declaration", "input": "<A:Ljava/lang/Object;B"}, "expected_output": "count=0\n"}
    ]
}
```

*4.5 Method Parameter Types — parse the parameter section of a method descriptor*

The input command is `{"feature":"method_args","input":<method descriptor>}`. A method descriptor has the form `(<param descriptors>)<return descriptor>`. The result starts with a `count=` line giving the number of parameters, followed by one `arg=` line per parameter rendered as a human-readable type, including generic and inner-class forms.

**Test Cases:** `rcb_tests/public_test_cases/feature4_5_method_args.json`

```json
{
    "description": "Parse the parameter section of a method descriptor '(...)R' into the ordered list of parameter types, rendering each as a human-readable type (including generic and inner-class forms). Output starts with 'count=' then one 'arg=' line per parameter.",
    "cases": [
        {"input": {"feature": "method_args", "input": "(Ljava/util/List<*>;)V"}, "expected_output": "count=1\narg=java.util.List<?>\n"},
        {"input": {"feature": "method_args", "input": "(La/b/C<TT;>.d/E;)V"}, "expected_output": "count=1\narg=a.b.C$d.E<>\n"}
    ]
}
```

---

### Feature 5: Version Comparison

**As a developer**, I want to compare two dotted numeric version strings, so I can detect whether an update is newer.

**Expected Behavior / Usage:**

The input command is `{"feature":"version_compare","left":<version>,"right":<version>}`. Each version is a dot-separated sequence of non-negative integers. Comparison proceeds ordinal by ordinal; a version with fewer ordinals is treated as having trailing zeros, so `0.5`, `0.5.0` and `0.5.00` are all equal. The result is one `compare=` line carrying `-1` when the left version is lower, `1` when higher, and `0` when equal.

**Test Cases:** `rcb_tests/public_test_cases/feature5_version_compare.json`

```json
{
    "description": "Compare two dotted numeric version strings ordinal by ordinal. Missing trailing ordinals are treated as zero so '0.5', '0.5.0' and '0.5.00' are equal; the result is -1 if the left version is lower, 1 if higher, 0 if equal. Output is a single 'compare=' line carrying -1, 0 or 1.",
    "cases": [
        {"input": {"feature": "version_compare", "left": "1", "right": "2"}, "expected_output": "compare=-1\n"},
        {"input": {"feature": "version_compare", "left": "0.5", "right": "0.5.0"}, "expected_output": "compare=0\n"},
        {"input": {"feature": "version_compare", "left": "0.5", "right": "0.5.0.1"}, "expected_output": "compare=-1\n"},
        {"input": {"feature": "version_compare", "left": "0.4.8", "right": "0.5"}, "expected_output": "compare=-1\n"}
    ]
}
```

---

### Feature 6: String-View Operations

**As a developer**, I want lightweight substring/trim/split operations on a string view, so I can scan and slice text without allocating intermediate copies.

**Expected Behavior / Usage:**

*6.1 Substring View — take a sub-view by start (and optional exclusive end) index*

The input command is `{"feature":"substring","input":<string>,"from":<int>[,"to":<int>]}`. With only `from`, the view runs from that index to the end of the string. With both `from` and `to`, the view spans `[from, to)`. A start equal to the length yields an empty view; an equal start/end pair yields an empty view. The result is a `value=` line with the view's text and a `length=` line with its length.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_substring.json`

```json
{
    "description": "Take a substring view of a string by start index (and optional end index, exclusive). With only a start index the view runs to the end of the string; a start equal to the length yields an empty view; an explicit equal start/end pair yields an empty view. Output gives the 'value=' of the view and its 'length='.",
    "cases": [
        {"input": {"feature": "substring", "input": "a", "from": 0}, "expected_output": "value=a\nlength=1\n"},
        {"input": {"feature": "substring", "input": "a", "from": 1}, "expected_output": "value=\nlength=0\n"},
        {"input": {"feature": "substring", "input": "a", "from": 0, "to": 0}, "expected_output": "value=\nlength=0\n"},
        {"input": {"feature": "substring", "input": "abc", "from": 1, "to": 2}, "expected_output": "value=b\nlength=1\n"}
    ]
}
```

*6.2 Trim — strip leading/trailing whitespace from a view*

The input command is `{"feature":"trim","input":<string>[,"from":<int>[,"to":<int>]]}`. The view is the whole string, or a sub-view defined by `from`/`to`; trimming removes any characters at or below the space character from both ends of that view. The result is one `value=` line with the trimmed text.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_trim.json`

```json
{
    "description": "Trim leading and trailing whitespace from a string view. The view may be the whole string or a sub-view defined by start (and optional end) indices; trimming removes any characters at or below the space character from both ends of that view. Output is a single 'value=' line with the trimmed text.",
    "cases": [
        {"input": {"feature": "trim", "input": " a "}, "expected_output": "value=a\n"},
        {"input": {"feature": "trim", "input": "\ta"}, "expected_output": "value=a\n"},
        {"input": {"feature": "trim", "input": "a b c", "from": 1}, "expected_output": "value=b c\n"},
        {"input": {"feature": "trim", "input": "a b\tc", "from": 1, "to": 4}, "expected_output": "value=b\n"}
    ]
}
```

*6.3 Split — split a string on a literal separator*

The input command is `{"feature":"split","input":<string>,"separator":<string>}`. The string is split on every non-overlapping occurrence of the literal separator. Consecutive separators produce empty pieces; a leading separator produces a leading empty piece; a separator that does not occur yields the whole string as a single piece; a trailing separator does not add a trailing empty piece. The result starts with a `count=` line followed by one `part=` line per piece.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_split.json`

```json
{
    "description": "Split a string on every non-overlapping occurrence of a literal separator. Consecutive separators produce empty pieces; a leading separator produces a leading empty piece; a separator that does not occur yields the whole string as a single piece; a trailing separator does not produce a trailing empty piece. Output starts with 'count=' then one 'part=' line per piece.",
    "cases": [
        {"input": {"feature": "split", "input": "abc", "separator": "b"}, "expected_output": "count=2\npart=a\npart=c\n"},
        {"input": {"feature": "split", "input": "abc", "separator": "a"}, "expected_output": "count=2\npart=\npart=bc\n"},
        {"input": {"feature": "split", "input": "abbbc", "separator": "b"}, "expected_output": "count=4\npart=a\npart=\npart=\npart=c\n"},
        {"input": {"feature": "split", "input": "abbbc", "separator": "bb"}, "expected_output": "count=2\npart=a\npart=bc\n"}
    ]
}
```

---

### Feature 7: Back/Forward Navigation History

**As a developer**, I want a back/forward history of visited positions, so users can step backward and forward through their navigation trail.

**Expected Behavior / Usage:**

The input command is `{"feature":"history","operations":[ ... ]}`, a list of operations applied in order. Each operation is `{"op":"add","id":<int>}`, `{"op":"prev"}`, or `{"op":"next"}`. A position is identified by an integer id. Adding a position whose id equals the current one is ignored. `prev` steps the cursor back and returns the id at the new position, or `none` when already at the oldest; `next` steps forward and returns the id, or `none` when already at the newest. Stepping back and then adding truncates any forward history beyond the new position. The result echoes each operation: `add=<id>`, `prev=<id|none>`, `next=<id|none>`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_history.json`

```json
{
    "description": "Maintain a back/forward navigation history. 'add' appends a position identified by an integer id; adding the same id that is already current is ignored; 'prev' steps back and 'next' steps forward, each returning the id at the new cursor or 'none' at the ends. Moving back and then adding truncates any forward history. Output echoes each operation: 'add=<id>', 'prev=<id|none>', 'next=<id|none>'.",
    "cases": [
        {"input": {"feature": "history", "operations": [{"op": "prev"}, {"op": "next"}]}, "expected_output": "prev=none\nnext=none\n"},
        {"input": {"feature": "history", "operations": [{"op": "add", "id": 1}, {"op": "add", "id": 2}, {"op": "prev"}, {"op": "prev"}, {"op": "next"}, {"op": "next"}]}, "expected_output": "add=1\nadd=2\nprev=1\nprev=none\nnext=2\nnext=none\n"},
        {"input": {"feature": "history", "operations": [{"op": "add", "id": 1}, {"op": "add", "id": 2}, {"op": "add", "id": 3}, {"op": "add", "id": 4}, {"op": "prev"}, {"op": "prev"}, {"op": "add", "id": 5}, {"op": "next"}, {"op": "next"}, {"op": "prev"}, {"op": "prev"}, {"op": "prev"}, {"op": "next"}, {"op": "next"}, {"op": "next"}]}, "expected_output": "add=1\nadd=2\nadd=3\nadd=4\nprev=3\nprev=2\nadd=5\nnext=none\nnext=none\nprev=2\nprev=1\nprev=none\nnext=2\nnext=5\nnext=none\n"},
        {"input": {"feature": "history", "operations": [{"op": "add", "id": 7}, {"op": "add", "id": 7}, {"op": "prev"}, {"op": "next"}]}, "expected_output": "add=7\nadd=7\nprev=none\nnext=none\n"}
    ]
}
```

---

### Feature 8: Command-Line Option Parsing

**As a developer**, I want to parse option tokens into boolean settings, so a command-line front end can configure a run.

**Expected Behavior / Usage:**

The input command is `{"feature":"cli_flags","args":[<tokens>],"query":[<flag names>]}` with optional `"override":true` and `"base":{...}`. A `--no-<feature>` token turns a default-on feature off; a plain long flag turns a feature on; some flags accept a short alias (for example skipping sources can be requested with a short token). An empty token list keeps all defaults. In *override* mode only flags explicitly present in the tokens are applied, and any flag supplied in `base` keeps its base value when not mentioned. The result is one `<flag>=<true|false>` line per queried flag. Queryable flags include: replace-constants, escape-unicode, skip-sources, use-imports, debug-info.

**Test Cases:** `rcb_tests/public_test_cases/feature8_cli_flags.json`

```json
{
    "description": "Parse command-line option tokens into boolean settings and report selected flags. A '--no-...' token turns a default-on feature off; a long flag turns a feature on; some flags accept a short alias; an empty token list keeps defaults. An 'override' parse only applies flags explicitly present in the tokens, leaving a pre-existing base setting otherwise untouched. Output is one '<flag>=<true|false>' line per queried flag.",
    "cases": [
        {"input": {"feature": "cli_flags", "args": ["--no-replace-consts"], "query": ["replace_consts"]}, "expected_output": "replace_consts=false\n"},
        {"input": {"feature": "cli_flags", "args": ["--no-src"], "query": ["skip_sources"]}, "expected_output": "skip_sources=true\n"},
        {"input": {"feature": "cli_flags", "args": ["-s"], "query": ["skip_sources"]}, "expected_output": "skip_sources=true\n"},
        {"input": {"feature": "cli_flags", "override": true, "args": ["--no-imports"], "query": ["use_imports"]}, "expected_output": "use_imports=false\n"},
        {"input": {"feature": "cli_flags", "override": true, "base": {"use_imports": false}, "args": [""], "query": ["use_imports"]}, "expected_output": "use_imports=false\n"}
    ]
}
```

---

### Feature 9: Output Directory Resolution

**As a developer**, I want to resolve the effective output, sources and resources directories from a partial configuration, so output always lands in well-defined locations.

**Expected Behavior / Usage:**

The input command is `{"feature":"output_dirs","input_name":<file name>,"out_dir":<path|null>,"src_dir":<path|null>,"res_dir":<path|null>}`. If all three are given they are kept as-is. If the root output is omitted it falls back to the sources directory, else the resources directory, else a directory derived from the input file's base name (its name with the extension removed). When omitted, the sources and resources directories default to fixed sub-folders (`sources` and `resources`) under the resolved root. The result is three lines: `out=`, `src=`, `res=`, using forward slashes.

**Test Cases:** `rcb_tests/public_test_cases/feature9_output_dirs.json`

```json
{
    "description": "Resolve the effective output, sources and resources directories from a partially specified configuration. If all three are given they are kept as-is. If the root output is omitted it falls back to the sources dir, else the resources dir, else a directory derived from the input file's base name; the sources and resources directories, when omitted, default to fixed sub-folders under the resolved root. Output is three lines: 'out=', 'src=', 'res='.",
    "cases": [
        {"input": {"feature": "output_dirs", "input_name": "some.apk", "out_dir": "r", "src_dir": "s", "res_dir": "r"}, "expected_output": "out=r\nsrc=s\nres=r\n"},
        {"input": {"feature": "output_dirs", "input_name": "some.apk", "out_dir": "out", "src_dir": null, "res_dir": null}, "expected_output": "out=out\nsrc=out/sources\nres=out/resources\n"},
        {"input": {"feature": "output_dirs", "input_name": "some.apk", "out_dir": null, "src_dir": "src", "res_dir": null}, "expected_output": "out=src\nsrc=src\nres=src/resources\n"},
        {"input": {"feature": "output_dirs", "input_name": "some.apk", "out_dir": null, "src_dir": null, "res_dir": "res"}, "expected_output": "out=res\nsrc=res/sources\nres=res\n"}
    ]
}
```

---

### Feature 10: Named Flag Set

**As a developer**, I want a small mutable set of named flags, so I can attach and query boolean markers on a node.

**Expected Behavior / Usage:**

The input command is `{"feature":"attributes","operations":[ ... ]}`, a list applied in order. Each operation is `{"op":"add","flag":<name>}`, `{"op":"remove","flag":<name>}`, `{"op":"clear"}`, or `{"op":"contains","flag":<name>}`. Adding then removing a flag leaves it absent; `clear` empties the set. Mutating operations echo themselves (`add=<name>`, `remove=<name>`, `clear`); a `contains` query renders as `contains[<name>]=<true|false>`.

**Test Cases:** `rcb_tests/public_test_cases/feature10_attributes.json`

```json
{
    "description": "Maintain a small set of named flags. 'add' inserts a flag, 'remove' deletes it, 'clear' empties the set, and 'contains' queries membership; adding then removing leaves it absent, and clearing removes everything. Output echoes each mutating operation and renders each query as 'contains[<flag>]=<true|false>'.",
    "cases": [
        {"input": {"feature": "attributes", "operations": [{"op": "add", "flag": "[a specific flag placeholder]"}, {"op": "contains", "flag": "[a specific flag placeholder]"}]}, "expected_output": "add=[a specific flag placeholder]\ncontains[[a specific flag placeholder]]=true\n"},
        {"input": {"feature": "attributes", "operations": [{"op": "add", "flag": "[a specific flag placeholder]"}, {"op": "remove", "flag": "[a specific flag placeholder]"}, {"op": "contains", "flag": "[a specific flag placeholder]"}]}, "expected_output": "add=[a specific flag placeholder]\nremove=[a specific flag placeholder]\ncontains[[a specific flag placeholder]]=false\n"},
        {"input": {"feature": "attributes", "operations": [{"op": "add", "flag": "[a specific flag placeholder]"}, {"op": "add", "flag": "LOOP_START"}, {"op": "clear"}, {"op": "contains", "flag": "[a specific flag placeholder]"}, {"op": "contains", "flag": "LOOP_START"}]}, "expected_output": "add=[a specific flag placeholder]\nadd=LOOP_START\nclear\ncontains[[a specific flag placeholder]]=false\ncontains[LOOP_START]=false\n"}
    ]
}
```

---

### Feature 11: Class Hierarchy Query

**As a developer**, I want to ask whether one runtime class is the same as or a subtype of another, so I can reason about assignability and casts.

**Expected Behavior / Usage:**

The input command is `{"feature":"class_hierarchy","type":<dotted class name>,"ancestor":<dotted class name>}`. Using the bundled standard-library hierarchy, the result is one `implements=` line: `true` when the first class is the same as or transitively derived from the second, `false` otherwise. The relation is directional, so swapping the two classes generally flips the answer.

**Test Cases:** `rcb_tests/public_test_cases/feature11_class_hierarchy.json`

```json
{
    "description": "Query the bundled Java class hierarchy to decide whether one class is the same as or a subtype of another. The relation is directional: a subtype is in an 'implements' relation with its ancestor, but not the other way round. Output is a single 'implements=' line.",
    "cases": [
        {"input": {"feature": "class_hierarchy", "type": "java.lang.Exception", "ancestor": "java.lang.Throwable"}, "expected_output": "implements=true\n"},
        {"input": {"feature": "class_hierarchy", "type": "java.lang.Throwable", "ancestor": "java.lang.Exception"}, "expected_output": "implements=false\n"}
    ]
}
```

---

### Feature 12: Certificate Inspection

**As a developer**, I want to decode an X.509 certificate and read out its signature and public-key details, so I can display who signed a package.

**Expected Behavior / Usage:**

The input command is `{"feature":"certificate","field":<"signature"|"public_key">,"der_base64":<base64 DER bytes>}`. The DER bytes are decoded as an X.509 certificate. The `signature` field reports the signature algorithm name and its dotted object identifier. The `public_key` field reports the key algorithm and, for an RSA key, its exponent, modulus bit-size and full decimal modulus value. The result is one `label: value` line per detail.

**Test Cases:** `rcb_tests/public_test_cases/feature12_certificate.json`

```json
{
    "description": "Decode an X.509 certificate (provided as base64-encoded DER bytes) and extract human-readable details. The 'signature' field reports the signature algorithm name and its object identifier; the 'public_key' field reports the key algorithm and, for an RSA key, its exponent, modulus bit-size and full modulus value. Output is one 'label: value' line per detail.",
    "cases": [
        {"input": {"feature": "certificate", "field": "signature", "der_base64": "MIIFbwYJKoZIhvcNAQcCoIIFYDCCBVwCAQExCzAJBgUrDgMCGgUAMAsGCSqGSIb3DQEHAaCCA5EwggONMIICdaADAgECAgRL1oBSMA0GCSqGSIb3DQEBCwUAMHcxDzANBgNVBAYTBjEyMzQ1NjEPMA0GA1UECBMGUnVzc2lhMRUwEwYDVQQHEwxTdC5QZXRlcmJ1cmcxFDASBgNVBAoTC09PTyBUZXN0T3JnMRIwEAYDVQQLEwl0ZXN0IHVuaXQxEjAQBgNVBAMTCXRlc3QgY2VydDAeFw0xODA3MDMxMDU4MTdaFw00MzA2MjcxMDU4MTdaMHcxDzANBgNVBAYTBjEyMzQ1NjEPMA0GA1UECBMGUnVzc2lhMRUwEwYDVQQHEwxTdC5QZXRlcmJ1cmcxFDASBgNVBAoTC09PTyBUZXN0T3JnMRIwEAYDVQQLEwl0ZXN0IHVuaXQxEjAQBgNVBAMTCXRlc3QgY2VydDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAIU8gZe6yLvHhHC/uqVCapDPTxzq2r2q0JJSS5IIrFCWHJGttRhM0zqKMRITtFjMTM8iOi7vj7WoLvkERjsAc1jxP5eFet5HU3vbhq+a6QPELsnSVU8oE3MTrnj7xNPTTMfu+/+oAVOONIu4kYW6v3HGuRu2PP2ezyUN3U5IKd46KF1TYbrhgnKW6vI9oiTBtG+NT/06elENBu1zl7x8XwLgGmPdJ7ayOfPoTjrTZ+TnZdoGvTVtnI4CY2Ziv1tI3pGliN0079IoWvpaG9ilJ+VMhqsFQ2YYBrs5eGLZdM6UzPiP3w4GWWFjRp4S6QaymQtFDZ0Wdza0u5KORLBwWycCAwEAAaMhMB8wHQYDVR0OBBYEFOz7yf7nd1+dwEdG7KW0XTHC/RcZMA0GCSqGSIb3DQEBCwUAA4IBAQAi+wjOWaWFFMYlTMH6V3ndiU9aMprO8PzfeivL4b3OoXudhnHfVZJTtwm56gUGSb9zClKwm3w6pYAVYGyoqg4LPfEcyjCBDKjaR+UUYlX8ICvFKi0tO0Y2TNoaQq/qmUcbEXOG4JKghnxEnphuvvOyfq63n/5XuijR2MiixsVH6LYeOBf4J2zfyZK1H4kG/mxBoGHGExP3P5uWGCMZl0t69M4u28rLnJJWC3XsImSbAzJ3TweHzxsrqnt3dpF1xrI+0v5KzBp5Jx9+agapzVVj29dDNkApv+/wxVmYWgfJINpOL/WiiiBDdSKd+p/8IUQo7zlje5BP5nRkWHbmJNb7MYIBpjCCAaICAQEwfzB3MQ8wDQYDVQQGEwYxMjM0NTYxDzANBgNVBAgTBlJ1c3NpYTEVMBMGA1UEBxMMU3QuUGV0ZXJidXJnMRQwEgYDVQQKEwtPT08gVGVzdE9yZzESMBAGA1UECxMJdGVzdCB1bml0MRIwEAYDVQQDEwl0ZXN0IGNlcnQCBEvWgFIwCQYFKw4DAhoFADANBgkqhkiG9w0BAQEFAASCAQAsbGm1vUj60WPWcpJfpi1WdHNJRFIpnjB/NgFyVtFV3rnXoVsmSOl/6cFySDZG2+AzoqubCaKKbFTr7v0ojx2/1ESSx/eS2NsOH7VkFV1cswqb7Qc+/IETsi4DK4rPJOr3HRKBMQVAxd2HDJZgk2CcyvnDxdbBquoQH/gzxZpoLsQPWajpcBcCQH+hp59y0mbHjgqyW5yQWh94thBMImcgxKzt4vYrQjK4IykSCXs843fqRTey5bCAwExEzFlSIkcWPSdbUWSs1s1cu6pLK0EGMWP78XdG+LsfMuSCKahnhvZ5ii3ZPG+EOw/L7kglOdw0sKq0AnqyfRC0WH4HiesM"}, "expected_output": "Signature type: SHA256withRSA\nSignature OID: [a specific OID placeholder]\n"},
        {"input": {"feature": "certificate", "field": "public_key", "der_base64": "MIIFbwYJKoZIhvcNAQcCoIIFYDCCBVwCAQExCzAJBgUrDgMCGgUAMAsGCSqGSIb3DQEHAaCCA5EwggONMIICdaADAgECAgRL1oBSMA0GCSqGSIb3DQEBCwUAMHcxDzANBgNVBAYTBjEyMzQ1NjEPMA0GA1UECBMGUnVzc2lhMRUwEwYDVQQHEwxTdC5QZXRlcmJ1cmcxFDASBgNVBAoTC09PTyBUZXN0T3JnMRIwEAYDVQQLEwl0ZXN0IHVuaXQxEjAQBgNVBAMTCXRlc3QgY2VydDAeFw0xODA3MDMxMDU4MTdaFw00MzA2MjcxMDU4MTdaMHcxDzANBgNVBAYTBjEyMzQ1NjEPMA0GA1UECBMGUnVzc2lhMRUwEwYDVQQHEwxTdC5QZXRlcmJ1cmcxFDASBgNVBAoTC09PTyBUZXN0T3JnMRIwEAYDVQQLEwl0ZXN0IHVuaXQxEjAQBgNVBAMTCXRlc3QgY2VydDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAIU8gZe6yLvHhHC/uqVCapDPTxzq2r2q0JJSS5IIrFCWHJGttRhM0zqKMRITtFjMTM8iOi7vj7WoLvkERjsAc1jxP5eFet5HU3vbhq+a6QPELsnSVU8oE3MTrnj7xNPTTMfu+/+oAVOONIu4kYW6v3HGuRu2PP2ezyUN3U5IKd46KF1TYbrhgnKW6vI9oiTBtG+NT/06elENBu1zl7x8XwLgGmPdJ7ayOfPoTjrTZ+TnZdoGvTVtnI4CY2Ziv1tI3pGliN0079IoWvpaG9ilJ+VMhqsFQ2YYBrs5eGLZdM6UzPiP3w4GWWFjRp4S6QaymQtFDZ0Wdza0u5KORLBwWycCAwEAAaMhMB8wHQYDVR0OBBYEFOz7yf7nd1+dwEdG7KW0XTHC/RcZMA0GCSqGSIb3DQEBCwUAA4IBAQAi+wjOWaWFFMYlTMH6V3ndiU9aMprO8PzfeivL4b3OoXudhnHfVZJTtwm56gUGSb9zClKwm3w6pYAVYGyoqg4LPfEcyjCBDKjaR+UUYlX8ICvFKi0tO0Y2TNoaQq/qmUcbEXOG4JKghnxEnphuvvOyfq63n/5XuijR2MiixsVH6LYeOBf4J2zfyZK1H4kG/mxBoGHGExP3P5uWGCMZl0t69M4u28rLnJJWC3XsImSbAzJ3TweHzxsrqnt3dpF1xrI+0v5KzBp5Jx9+agapzVVj29dDNkApv+/wxVmYWgfJINpOL/WiiiBDdSKd+p/8IUQo7zlje5BP5nRkWHbmJNb7MYIBpjCCAaICAQEwfzB3MQ8wDQYDVQQGEwYxMjM0NTYxDzANBgNVBAgTBlJ1c3NpYTEVMBMGA1UEBxMMU3QuUGV0ZXJidXJnMRQwEgYDVQQKEwtPT08gVGVzdE9yZzESMBAGA1UECxMJdGVzdCB1bml0MRIwEAYDVQQDEwl0ZXN0IGNlcnQCBEvWgFIwCQYFKw4DAhoFADANBgkqhkiG9w0BAQEFAASCAQAsbGm1vUj60WPWcpJfpi1WdHNJRFIpnjB/NgFyVtFV3rnXoVsmSOl/6cFySDZG2+AzoqubCaKKbFTr7v0ojx2/1ESSx/eS2NsOH7VkFV1cswqb7Qc+/IETsi4DK4rPJOr3HRKBMQVAxd2HDJZgk2CcyvnDxdbBquoQH/gzxZpoLsQPWajpcBcCQH+hp59y0mbHjgqyW5yQWh94thBMImcgxKzt4vYrQjK4IykSCXs843fqRTey5bCAwExEzFlSIkcWPSdbUWSs1s1cu6pLK0EGMWP78XdG+LsfMuSCKahnhvZ5ii3ZPG+EOw/L7kglOdw0sKq0AnqyfRC0WH4HiesM"}, "expected_output": "Public key type: RSA\nExponent: 65537\nModulus size (bits): 2048\nModulus: 16819531290318044625546437357099080306019392752925688951114880688329201213180109168890384305768067101521914473763638669503560977521269328582980060332888147680193318231260043189411794465899645633586173494259691101582064441956032924396850221679489313043628562082670183392670094163371858684118480409374749790551473773845213427476236147328434427272177623018935282929152308753854314219987617604037468769472089902090243358285991739642170211970862773121939911777280101937073243006335384636193260583579409760790138329893534549366882523130765297472656435892831796545149793228897111760122091442123535919361963075454640516520743\n"},
        {"input": {"feature": "certificate", "field": "signature", "der_base64": "MIIDUwYJKoZIhvcNAQcCoIIDRDCCA0ACAQExCzAJBgUrDgMCGgUAMAsGCSqGSIb3DQEHAaCCAqQwggKgMIICXqADAgECAgQWQguiMAsGByqGSM44BAMFADAiMSAwHgYDVQQKExdVSk1SRlZWIENOPUVEQ1ZCR1QgQz1URzAeFw0xODAxMjIxNDI5MzJaFw00NTA2MDkxNDI5MzJaMCIxIDAeBgNVBAoTF1VKTVJGVlYgQ049RURDVkJHVCBDPVRHMIIBtzCCASwGByqGSM44BAEwggEfAoGBAP1/U4EddRIpUt9KnC7s5Of2EbdSPO9EAMMeP4C2USZpRV1AIlH7WT2NWPq/xfW6MPbLm1Vs14E7gB00b/JmYLdrmVClpJ+f6AR7ECLCT7up1/63xhv4O1fnxqimFQ8E+4P208UewwI1VBNaFpEy9nXzrith1yrv8iIDGZ3RSAHHAhUAl2BQjxUjC8yykrmCouuEC/BYHPUCgYEA9+GghdabPd7LvKtcNrhXuXmUr7v6OuqC+VdMCz0HgmdRWVeOutRZT+ZxBxCBgLRJFnEj6EwoFhO3zwkyjMim4TwWeotUfI0o4KOuHiuzpnWRbqN/C/ohNWLx+2J6ASQ7zKTxvqhRkImog9/hWuWfBpKLZl6Ae1UlZAFMO/7PSSoDgYQAAoGAG4RzmOcb7sXBupMmxznZWKeDCqXDmkFhT98vkp/a3hAabAVjJGyPDyB7TrUEBYqRs7CnQYzu2gicj50IHrpn5IafZQzmI5esv4JEkxKHFZ4IMNOnihGGZ7IVt360znVDcdshF3wS7vA9XBWpKtAkv1ZzdtoBUj1tcv2xCFW//R6jITAfMB0GA1UdDgQWBBQhoNGqG1xbm3eLo11neK/ZRskcBzALBgcqhkjOOAQDBQADLwAwLAIUNWj3CjKJS3TQvQzT97miRbeGm/sCFCn1WjywjJh8HpvbI5OwavWGZRAeMXkwdwIBATAqMCIxIDAeBgNVBAoTF1VKTVJGVlYgQ049RURDVkJHVCBDPVRHAgQWQguiMAkGBSsOAwIaBQAwCwYHKoZIzjgEAQUABC4wLAIUCRqB38SQ3RiltjsnKa5MIBsnEaECFB/JoshLl+kZKoEfNIk9mL/BL3zK"}, "expected_output": "Signature type: SHA1withDSA\nSignature OID: 1.2.840.10040.4.3\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-module codebase implementing the helpers above, with text/literal rendering, type-descriptor parsing, version comparison, string-view utilities, navigation history, CLI/config handling, the named-flag set, the class-hierarchy query, and certificate inspection kept in cohesive units. The core logic must not depend on JSON or stdin/stdout.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON command object from stdin, invokes the appropriate core helper, and prints the result to stdout exactly per the per-feature contracts above. It is responsible for normalizing any native error into a neutral category line and for keeping stdout free of host runtime log noise. This adapter must be logically and physically separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_string_escape.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_string_escape@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites the other. Each `.txt` file contains **only** the raw stdout of the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- remove whitespace from start if start <= end
- requires non-empty dot-segment starting with a-z_
