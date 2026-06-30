## Product Requirement Document

# Python Function Signature to Statically-Typed Binding Generator — Parse Python Signatures and Emit Equivalent Strongly-Typed Method Bindings

## Project Goal

Build a toolkit that reads Python function signatures (and the type annotations within them) from source text and produces the equivalent strongly-typed surface for a statically typed host language, so developers can call dynamically-typed Python functions from a statically typed codebase through generated, type-safe wrappers without hand-writing interop glue for every function.

---

## Background & Problem

Calling Python functions from a statically typed language normally forces developers to hand-write a wrapper for every function: pick a target type for each Python annotation, translate `snake_case` Python names into the host language's `PascalCase`/`camelCase` conventions, escape names that collide with host keywords, and keep all of this in sync as the Python code changes. This is tedious, repetitive, and error-prone.

This toolkit automates the front half of that pipeline. Given Python source, it (1) recognizes function-definition headers — even when they span multiple lines, carry trailing comments, or sit at the end of the file — and extracts each function's name, parameters, and return annotation; (2) maps every Python type annotation to the corresponding host-language type, handling scalars, homogeneous sequences, fixed heterogeneous sequences, and key/value mappings, with recursive nesting and case-insensitive aliases; (3) converts identifier casing between Python and host conventions; (4) renders a complete host-language method signature for each function, including idiomatic default-value literals and variadic parameters; and (5) reports precise positions when a header cannot be parsed. The behavior is defined purely in terms of text in and text out, so it can be validated independently of any runtime.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., lexing, parsing, type mapping, signature rendering), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
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

### Feature 1: Identifier Casing Conversion

**As a developer**, I want to convert Python `snake_case` identifiers into the host language's casing conventions, so generated type and member names look idiomatic in the target codebase.

**Expected Behavior / Usage:**

*1.1 snake_case to PascalCase — convert a member-style identifier to upper-camel form*

The input is an identifier string. The identifier is split on underscore (`_`) boundaries. Each segment that has at least two characters contributes its first character upper-cased followed by its remaining characters unchanged; the segments are then concatenated. An empty segment — produced by a leading underscore, a trailing underscore, or a run of consecutive underscores — contributes a single literal underscore. The result therefore preserves leading underscores, trailing underscores, and the gaps left by doubled underscores as underscore characters. Output is the converted identifier followed by a trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_[a specific action type — verify with the spec sheet].json`

```json
{
    "description": "Convert a snake_case style identifier into a PascalCase identifier suitable for a statically typed target language. The identifier is split on underscore boundaries; each non-empty segment has its first character upper-cased and the remainder preserved, then the segments are concatenated. A trailing underscore (an empty final segment) and runs of consecutive underscores are preserved as literal underscore characters in the output. A leading underscore is likewise preserved. Output is the converted identifier followed by a trailing newline.",
    "cases": [
        {"input": {"action": "[a specific action type — verify with the spec sheet]", "text": "hello_world"}, "expected_output": "HelloWorld\n"},
        {"input": {"action": "[a specific action type — verify with the spec sheet]", "text": "hello__world"}, "expected_output": "Hello_World\n"}
    ]
}
```

*1.2 snake_case to camelCase — convert a parameter-style identifier to lower-camel form*

The conversion first produces the PascalCase form (per 1.1), then forces the very first character of that result to lower-case. Because a leading underscore is not a letter, an identifier that begins with an underscore yields a result whose first character is already an underscore, so its output equals the PascalCase form. Output is the converted identifier followed by a trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_camel_case.json`

```json
{
    "description": "Convert a snake_case style identifier into a camelCase identifier (lower-cased leading character) suitable for a statically typed target language. The conversion first builds the PascalCase form (split on underscores, capitalize each non-empty segment, preserve empty segments and leading underscores as literal underscores), then forces the very first character of the result to lower-case. Note that for an input that begins with an underscore the first character is already an underscore, so the output is identical to the PascalCase form. Output is the converted identifier followed by a trailing newline.",
    "cases": [
        {"input": {"action": "camel_case", "text": "hello_world"}, "expected_output": "helloWorld\n"},
        {"input": {"action": "camel_case", "text": "hello__world"}, "expected_output": "hello_World\n"}
    ]
}
```

---

### Feature 2: Type Annotation Mapping

**As a developer**, I want each Python type annotation translated into the equivalent host-language type, so generated wrappers expose strongly-typed parameters and return values.

**Expected Behavior / Usage:**

The input is the textual form of a single Python type annotation. The mapping rules are:
- Scalars: integer maps to `long`, text maps to `string`, floating point maps to `double`, boolean maps to `bool`.
- A homogeneous sequence `list[T]` maps to `IEnumerable<map(T)>`.
- A fixed heterogeneous sequence `tuple[...]` with two or more elements maps to a parenthesized, comma-separated tuple type `(map(T1),map(T2),...)`; a single-element `tuple[T]` maps to the explicit one-arity value-tuple generic `ValueTuple<map(T)>`.
- A mapping `dict[K, V]` maps to `IReadOnlyDictionary<map(K),map(V)>`.
- The generic head name is matched case-insensitively, so capitalized aliases (`List`, `Tuple`, `Dict`) behave identically to their lower-case forms.
- Any unrecognized scalar name, and any unknown/dynamic element (such as `object` or `Any`), maps to the opaque dynamic object type `PyObject`.
- Mapping is recursive: nested annotations are mapped by the same rules.

The rendered type is emitted in compact form (no space after commas) followed by a trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature2_type_mapping.json`

```json
{
    "description": "Map a Python type annotation (given as its textual form) to the equivalent type in a statically typed target language. Scalar builtins map to their target primitives. A homogeneous sequence type maps to a generic enumerable of the mapped element type. A fixed-size heterogeneous sequence with two or more elements maps to a target tuple type written as a parenthesized, comma-separated list of mapped element types; a single-element fixed sequence maps to the explicit one-arity value-tuple generic. A mapping/association type maps to a read-only dictionary generic over its mapped key and value types. The generic head name is matched case-insensitively, so capitalized aliases behave identically to their lower-case forms. An unknown element type, or an unrecognized type name, maps to the opaque dynamic object type. Element types nest recursively. Output is the rendered target type (compact form, no spaces after commas) followed by a trailing newline.",
    "cases": [
        {"input": {"action": "map_type", "python_type": "list[int]"}, "expected_output": "IEnumerable<long>\n"},
        {"input": {"action": "map_type", "python_type": "tuple[str, list[int]]"}, "expected_output": "(string,IEnumerable<long>)\n"},
        {"input": {"action": "map_type", "python_type": "dict[str, int]"}, "expected_output": "IReadOnlyDictionary<string,long>\n"},
        {"input": {"action": "map_type", "python_type": "tuple[str]"}, "expected_output": "ValueTuple<string>\n"}
    ]
}
```

---

### Feature 3: Method Signature Generation

**As a developer**, I want a complete host-language method signature generated from a Python function definition, so I get a ready-to-use, type-safe wrapper declaration.

**Expected Behavior / Usage:**

The input is Python source text containing one function definition. The generator:
- Converts the Python function name to PascalCase to form the method name.
- Maps the return annotation to the host type; a none-return annotation produces a `void` method, and a missing return annotation produces the dynamic `PyObject` type.
- Renders each parameter as `mapped_type name`, where the name is converted to lower-camelCase; a parameter whose converted name collides with a reserved host keyword is escaped with a leading `@`.
- Models a variadic positional parameter (`*args`) as a one-arity value-tuple of the dynamic object type, always named with the conventional variadic name `args`; a bare keyword-only separator (`*`) introduces the same `args` placeholder; a variadic keyword parameter (`**kwargs`) is modeled as `IReadOnlyDictionary<string, PyObject>`.
- Renders default values idiomatically: integers and floats as numeric literals, booleans as `true`/`false`, the none constant as `null`, and hexadecimal / binary integer literals preserved in their original base (uppercased hex digits).

The output is the rendered signature — the return type, a space, the method name, then the parenthesized parameter list, with a single space after each comma in the list — followed by a trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature3_signature_generation.json`

```json
{
    "description": "Generate a target-language instance method signature from a single Python function definition supplied as source text. The Python function name is converted to PascalCase to form the method name. The return annotation is mapped to the target type, with the special none-return annotation producing a void method. Each parameter is rendered as its mapped target type followed by its name converted to lower-camelCase; a parameter whose name collides with a reserved keyword of the target language is escaped with a leading at-sign. A variadic positional parameter is modeled as a one-arity value-tuple of the opaque dynamic object type and is always named with the conventional variadic name; a variadic keyword parameter is modeled as a read-only dictionary from string to the opaque dynamic object type. A bare keyword-only separator introduces the same variadic-positional placeholder. Parameter default values are rendered idiomatically: integers and floats as numeric literals, booleans as the target boolean literals, the none constant as the target null literal, and hexadecimal / binary integer literals preserved in their original base. Output is the rendered signature (return type, a space, method name, then the parenthesized parameter list with a space after each comma) followed by a trailing newline.",
    "cases": [
        {"input": {"action": "generate_signature", "source": "def hello_world(name: str) -> str:\n    ...\n"}, "expected_output": "string HelloWorld(string name)\n"},
        {"input": {"action": "generate_signature", "source": "def hello_world(a: str, *args, **kwargs) -> None: \n ...\n"}, "expected_output": "void HelloWorld(string a, ValueTuple<PyObject> args, IReadOnlyDictionary<string, PyObject> kwargs)\n"}
    ]
}
```

---

### Feature 4: Python Signature Parsing

**As a developer**, I want the toolkit to parse Python signatures into structured components and report failures precisely, so the generation stages above have a reliable front end and tooling can surface parse problems.

**Expected Behavior / Usage:**

*4.1 Parse a single parameter — extract name, annotation, and default*

The input is the textual form of one parameter. A parameter has a name, an optional type annotation, and an optional default value. The output reports, one field per line: `name=<name>`; `type=<rendered type>` (the dynamic placeholder `Any` when there is no annotation); `annotated=<true|false>` indicating whether an explicit annotation was present; and, only when a default value is present, `default=<value>` rendered in canonical textual form — numbers as written, quoted strings with their surrounding quotes removed, and the boolean/none constants by name (`True`, `False`, `None`).

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_parse_parameter.json`

```json
{
    "description": "Parse a single Python function parameter from its textual form and report its structural components. A parameter has a name, an optional type annotation, and an optional default value. When a type annotation is present its rendered form is reported and the annotation flag is true; when absent the type defaults to the dynamic-any placeholder and the annotation flag is false. A default value, when present, is reported in its canonical textual form (numbers as written, quoted strings with the quotes stripped, the boolean and none constants by name). Output reports, one per line: name, type, the annotated flag (true/false), and, only when a default exists, the default value.",
    "cases": [
        {"input": {"action": "parse_parameter", "text": "a: int"}, "expected_output": "name=a\ntype=int\nannotated=true\n"},
        {"input": {"action": "parse_parameter", "text": "a: bool = None"}, "expected_output": "name=a\ntype=bool\nannotated=true\ndefault=None\n"}
    ]
}
```

*4.2 Parse a parameter list — extract every parameter in order*

The input is a parenthesized, comma-separated parameter list. The output is one line per parameter, in declaration order, formatted as `<name>:<rendered type>`. A parameter without an annotation uses the dynamic placeholder `Any`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_parse_parameter_list.json`

```json
{
    "description": "Parse a parenthesized Python parameter list and report each parameter in order. The list is delimited by parentheses and parameters are comma-separated. Each parameter may carry a type annotation; a parameter without an annotation is reported with the dynamic-any placeholder type. Output is one line per parameter, in declaration order, each formatted as the parameter name, a colon, and the rendered type.",
    "cases": [
        {"input": {"action": "parse_parameter_list", "text": "(a: int, b: float, c: str)"}, "expected_output": "a:int\nb:float\nc:str\n"},
        {"input": {"action": "parse_parameter_list", "text": "(a, b, c)"}, "expected_output": "a:Any\nb:Any\nc:Any\n"}
    ]
}
```

*4.3 Parse a function definition header — extract name, parameters, return type*

The input is a single-line function definition header: the `def` keyword, the function name, a parameter list, an optional return annotation introduced by `->`, and the trailing colon. The output reports `name=<name>`, then one `param=<name>:<rendered type>` line per parameter in order, then `return=<rendered return type>`. Missing annotations use the dynamic placeholder `Any`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_parse_function.json`

```json
{
    "description": "Parse a single-line Python function definition header (the def keyword, the function name, a parameter list, an optional return annotation, and the trailing colon) and report its structure. Each parameter without a type annotation is reported with the dynamic-any placeholder type; a function without a return annotation is reported with the dynamic-any return type. Output reports the function name, then one line per parameter (in order) giving the parameter name and its rendered type, then the rendered return type.",
    "cases": [
        {"input": {"action": "parse_function", "text": "def foo(a: int, b: str) -> None:"}, "expected_output": "name=foo\nparam=a:int\nparam=b:str\nreturn=None\n"}
    ]
}
```

*4.4 Parse a complete source block — recognize every function definition*

The input is a complete block of Python source text. The scanner walks it and extracts every top-level function-definition header, ignoring all other lines (imports, assignments, guard blocks, function bodies). It must recognize headers that span multiple physical lines, headers carrying a trailing inline comment after the colon, headers with trailing whitespace after the colon, and a final header not followed by a blank line. The output reports `functions=<count>`, then one line per recognized function in source order rendered as `def <name>(<name>:<type>, ...) -> <return type>`, then `errors=<count>` followed by one line per error.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_parse_module.json`

```json
{
    "description": "Scan a complete block of Python source text and extract every top-level function definition, ignoring all non-function lines (imports, assignments, guard blocks, bodies). Function headers that span multiple physical lines, headers that carry a trailing inline comment after the colon, headers with trailing whitespace after the colon, and a final header that is not followed by a blank line must all be recognized. Output first reports the count of recognized functions, then one line per function (in source order) rendering the function header as the name, a parenthesized comma-separated list of name:type parameters, an arrow, and the return type; then it reports the count of parse errors, followed by one line per error.",
    "cases": [
        {"input": {"action": "parse_module", "source": "import foo\n\ndef bar(a: int, b: str) -> None:\n    pass\n\ndef baz(c: float, d: bool) -> None:\n    ...\n\na = 1\n\nif __name__ == '__main__':\n  xyz = 1\n"}, "expected_output": "functions=2\ndef bar(a:int, b:str) -> None\ndef baz(c:float, d:bool) -> None\nerrors=0\n"}
    ]
}
```

*4.5 Report parse errors with position — pinpoint a malformed header*

When a function header inside a source block is malformed, the scanner reports a parse error rather than crashing or silently skipping. Each error carries a start position and an end position, each given as a zero-based line index and a column index. The output reports `functions=<count>`, then `errors=<count>`, then one line per error formatted as `error <startLine>:<startColumn>-<endLine>:<endColumn>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_5_parse_errors.json`

```json
{
    "description": "When a function header inside a source block is malformed, the scan reports a parse error that pinpoints where tokenization broke down rather than silently skipping or crashing. The error carries a start and end position, each expressed as a zero-based line index and a column index, so a tool can underline the offending span. Output reports the count of recognized functions, then the count of errors, then one line per error giving the start line and column and the end line and column of the offending span.",
    "cases": [
        {"input": {"action": "parse_module", "source": "\n\n\ndef bar(a: int, b:= str) -> None:\n    pass"}, "expected_output": "functions=0\nerrors=1\nerror 3:21-3:22\n"}
    ]
}
```

---

### Feature 5: Integer Literal Decoding

**As a developer**, I want Python integer literals decoded to their numeric value, so default values and constants are interpreted correctly regardless of base.

**Expected Behavior / Usage:**

The input is the textual form of a Python integer literal. A plain decimal literal may carry an optional leading minus sign. A hexadecimal literal uses the `0x` prefix and a binary literal uses the `0b` prefix; both are unsigned and are decoded from their respective base. The output is the decoded value rendered in base ten, followed by a trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature5_integer_literals.json`

```json
{
    "description": "Parse a Python integer literal from its textual form and report its decimal value. Plain decimal literals may carry an optional leading minus sign. Hexadecimal literals use the 0x prefix and binary literals use the 0b prefix; both are unsigned and are decoded to their numeric value. Output is the integer value rendered in base ten, followed by a trailing newline.",
    "cases": [
        {"input": {"action": "parse_integer", "text": "255"}, "expected_output": "255\n"},
        {"input": {"action": "parse_integer", "text": "0xdeadbeef"}, "expected_output": "3735928559\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above (lexing/parsing of Python signatures, identifier casing, type mapping, signature rendering, and error reporting). Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request object from stdin and prints the resulting plain text to stdout, matching the per-feature contracts above. The request's `action` field selects behavior: `[a specific action type — verify with the spec sheet]` / `camel_case` (identifier casing of `text`); `map_type` (map the `python_type` annotation); `generate_signature` (render the method signature for the function in `source`); `parse_parameter` / `parse_parameter_list` / `parse_function` (structured parse of `text`); `parse_module` (scan `source` for all functions and errors); and `parse_integer` (decode the integer literal in `text`). Malformed input for a given action must be reported as a neutral `error=<category>` line rather than leaking host-language runtime details.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
