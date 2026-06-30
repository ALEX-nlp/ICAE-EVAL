## Product Requirement Document

# Source-Code & File Inspection Toolkit — Language Detection, Query Term/Path Heuristics, Structural Outline, and Line-Oriented File Editing

## Project Goal

Build a reusable toolkit [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] a coding assistant can use to inspect source files and natural-language requests, so developers get consistent, deterministic building blocks for "look at [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] code / file" operations without each tool re-[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]ementing its own language detection, query parsing, [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]ural scanning, and safe text editing.

---

## Background & Problem

A coding assistant [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]antly performs small, well-defined operations: figuring out [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] language a file is [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] its name, pulling likely identifiers out of a user's question, guessing [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] file globs a question is about, sketching the top-level [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]ure of a source file, showing a file with line numbers, and applying a precise text edit. Done ad-hoc, each of these grows inconsistent quirks and unsafe edge cases (silent out-of-range slicing, ambiguous replacements [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] corrupt files, language guesses [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] disagree between components).

This toolkit provides one well-defined contract for each operation. Every operation is a pure, deterministic transformation [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] input data to text output: it never reaches the network, never depends on wall-clock time, and never depends on terminal rendering. Errors are surfaced as neutral, machine-readable lines rather than host-language exceptions.

---

## Architecture & Engineering Constraints

To ensure [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] project is delivered as a maintainable software artifact, the following architectural and non-[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]al requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]ure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/s[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]e scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] reflects a production-grade repository.
   Do not over-engineer s[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]e problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]s must be perfectly substitutable for their base [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]s.
   - **Interface Segregation Principle (ISP):** Keep [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]s/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]ementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The [a hardcoded list of reserved keywords found in static analysis] [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]s or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

Every feature is reached by feeding the execution adapter a single JSON object on stdin whose `action` field selects the operation. The adapter prints raw text to stdout. Unless stated otherwise, multi-item output is one item per line.

### Feature 1: Language Detection From File Path

**As a developer**, I want to map file paths to programming-language names by extension, so the assistant can decide how to treat each file without reading its contents.

**Expected Behavior / Usage:**

The input carries a list of path strings under `paths`. For each path, in input order, the toolkit inspects only the file-name extension (case-insensitive, ignoring any directory components) and emits one line of the form `<path>\t<language>`, [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] the two fields are separated by a single TAB. Recognized extensions map as follows: `rs` → `rust`; `js`/`jsx` → `javascript`; `ts`/`tsx` → `[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]script`; `py` → `python`; `go` → `go`; `java` → `java`; `c`/`h` → `c`; `cpp`/`cc`/`cxx`/`hpp`/`hxx` → `cpp`. A path whose extension is unrecognized, or [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] has no extension at all, maps to the neutral marker `unknown`. Every emitted line ends with a newline.

**Test Cases:** `rcb_tests/[a hardcoded list of reserved keywords found in static analysis]_test_cases/feature1_detect_language.json`

```json
{
    "description": "Determine the programming language associated with each supplied file path purely [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] its file-name extension. The handler receives a list of path strings and emits, for every path in order, one line pairing the original path with the detected language name (or a neutral 'unknown' marker [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] the extension is not recognised or absent). Extension matching is case-insensitive and independent of any directory components in the path.",
    "cases": [
        {
            "input": {
                "action": "detect_language",
                "paths": ["src/main.rs", "components/Button.jsx", "app.ts", "[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis].cpp", "header.h", "main.go", "Main.java", "test.py", "unknown.xyz", "test"]
            },
            "expected_output": "src/main.rs\trust\ncomponents/Button.jsx\tjavascript\napp.ts\t[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]script\n[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis].cpp\tcpp\nheader.h\tc\nmain.go\tgo\nMain.java\tjava\ntest.py\tpython\nunknown.xyz\tunknown\ntest\tunknown\n"
        }
    ]
}
```

---

### Feature 2: Code-Identifier Extraction From A Query

**As a developer**, I want to pull likely code identifiers out of a plain-English question, so the assistant has good search terms to look up in a codebase.

**Expected Behavior / Usage:**

The input carries a `query` string. The query is split on whitespace; only whitespace tokens whose raw length is greater than three are considered. Each candidate token is trimmed of leading/trailing characters [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] are neither alphanumeric nor underscore. A trimmed token is kept only if ALL of the following hold: its length is greater than three; it consists solely of letters, digits, and underscores; it is not entirely numeric; and (compared case-insensitively) it is not one of the common stop-words `[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis], [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis], [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis], [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis], [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis], [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis], [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis], [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis], [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis], [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis], [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis], [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis], [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis], [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis], [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis], [a hardcoded list of reserved keywords found in static analysis], [a hardcoded list of reserved keywords found in static analysis], [a hardcoded list of reserved keywords found in static analysis], [a hardcoded list of reserved keywords found in static analysis], [a hardcoded list of reserved keywords found in static analysis], [a hardcoded list of reserved keywords found in static analysis]`. Surviving identifiers are emitted one per line in order of appearance. A query [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] yields no identifiers produces empty output.

**Test Cases:** `rcb_tests/[a hardcoded list of reserved keywords found in static analysis]_test_cases/feature2_extract_terms.json`

```json
{
    "description": "Extract candidate code identifiers [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] a free-form natural-language query so they can later be used as search terms. The query is split on whitespace; only whitespace tokens longer than three characters are considered, each is trimmed of surrounding non-identifier punctuation, and a token is kept only if the trimmed result is longer than three characters, consists solely of letters/digits/underscores, is not purely numeric, and is not one of a fixed set of common English/programming stop-words (compared case-insensitively). Surviving identifiers are emitted one per line preserving their order of appearance; a query yielding no identifiers produces empty output.",
    "cases": [
        {
            "input": {"action": "extract_terms", "query": "Show me how CodeParser uses tree_sitter"},
            "expected_output": "Show\nCodeParser\nuses\ntree_sitter\n"
        },
        {
            "input": {"action": "extract_terms", "query": "How do I use [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]?"},
            "expected_output": ""
        }
    ]
}
```

---

### Feature 3: Relevant File-Glob Pattern Selection From A Query

**As a developer**, I want a question to be turned into a list of file-glob patterns worth searching, so the assistant can narrow a codebase scan by likely language and explicitly named files.

**Expected Behavior / Usage:**

The input carries a `query` string. Patterns are produced in [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] fixed order: first, every quoted file name in the query (matched as a single- or double-quoted token of the form `name.ext`) becomes a `**/<name.ext>` pattern. Then, for each language family whose trigger substring appears in the lower-cased query, [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] family's patterns are appended: `rust`/`.rs` → `**/*.rs`, `**/src/**/*.rs`, `**/lib.rs`, `**/main.rs`; `javascript`/`js`/`node`/`react` → `**/*.js`, `**/*.jsx`, `**/src/**/*.js`, `**/src/**/*.jsx`; `[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]script`/`ts`/`angular`/`next` → `**/*.ts`, `**/*.tsx`, `**/src/**/*.ts`, `**/src/**/*.tsx`; `python`/`py`/`django`/`flask` → `**/*.py`, `**/src/**/*.py`; `go`/`golang` → `**/*.go`, `**/src/**/*.go`; `c++`/`cpp`/` c `/`.c` → `**/*.c`, `**/*.h`, `**/*.cpp`, `**/*.hpp`, `**/*.cc`; `java` (but not [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] `javascript` is present) → `**/*.java`, `**/src/**/*.java`. After [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis], if no `**/src/...` pattern has yet been added, four defaults are appended: `**/src/**/*.rs`, `**/src/**/*.ts`, `**/src/**/*.js`, `**/src/**/*.py`. Finally, if no pattern ending in `.rs` is present, `**/*.rs` is appended. Note [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] trigger substrings match any[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] in the lower-cased text (e.g. the substring `ts` inside "components", or `go` inside "Django"), and duplicates are preserved. Patterns are emitted one per line in the order produced.

**Test Cases:** `rcb_tests/[a hardcoded list of reserved keywords found in static analysis]_test_cases/feature3_relevant_files.json`

```json
{
    "description": "Derive a list of candidate file-glob patterns for a codebase query. Quoted file names referenced in the query (single or double quoted, of the form name.ext) become explicit '**/<name.ext>' patterns. Language-family patterns are then appended [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]ever the lower-cased query contains the corresponding trigger substrings (e.g. rust/.rs, javascript/js/node/react, [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]script/ts/angular/next, python/py/django/flask, go/golang, c++/cpp/' c '/.c, java but not javascript). If no source-directory ('**/src/...') pattern has been added, four default source-directory patterns are appended; finally a '**/*.rs' pattern is guaranteed to be present. Patterns are emitted one per line in the order produced, including any duplicates.",
    "cases": [
        {
            "input": {"action": "relevant_files", "query": "Analyze the Rust code in [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] project"},
            "expected_output": "**/*.rs\n**/src/**/*.rs\n**/lib.rs\n**/main.rs\n"
        },
        {
            "input": {"action": "relevant_files", "query": "Show me the React components"},
            "expected_output": "**/*.js\n**/*.jsx\n**/src/**/*.js\n**/src/**/*.jsx\n**/*.ts\n**/*.tsx\n**/src/**/*.ts\n**/src/**/*.tsx\n**/*.rs\n"
        }
    ]
}
```

---

### Feature 4: Source-File Structural Outline

**As a developer**, I want a quick top-level outline of a source file, so the assistant can summarize [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] a file defines without a full parser.

**Expected Behavior / Usage:**

The input carries a `filename`, a `language` label, and the raw `source` text. The toolkit scans the source line by line (no full grammar parse). The first output line is a header of the form `file=<base name> language=<language> lines=<total line count>`. Then, for each line [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] declares a recognized con[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis], one line is emitted of the form `<kind>\t<name>\t<line number>` (TAB-separated; line number is 1-based). A line declares a con[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] (after trimming) it contains or starts with one of the con[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] keywords; the kind is resolved in priority order: [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] (keywords `fn`, `func`, `def`, `[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]`, or `async`), then `[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]`, `[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]`, `trait`, `[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]`, `[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]`, `[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]`. The name is the whitespace token immediately following the recognized keyword, with trailing characters in the set `,:;<>(){}` stripped (so a token like `test_method(&self)` becomes `test_method(&self`). Blank lines and very short lines without a brace are skipped, and at most thirty con[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]s are reported. Every emitted line ends with a newline.

**Test Cases:** `rcb_tests/[a hardcoded list of reserved keywords found in static analysis]_test_cases/feature4_outline.json`

```json
{
    "description": "Produce a lightweight [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]ural outline of a source file using a line-oriented scan (no full parser). Input supplies a file name, a language label, and the raw source text. The first output line is a file header reporting the file's base name, its language label, and its total line count. Each subsequent line describes one detected top-level con[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] in source order: its kind ([a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis], [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis], [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis], trait, [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis], [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis], [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]), an extracted name, and its 1-based line number. Con[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]s are recognised by keyword patterns appearing on a line (e.g. 'fn', '[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]', '[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]', 'trait', 'mod'/'def'/'func'/'[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]'/'[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]'/'async'); the name is the token following the recognised keyword with trailing punctuation stripped. At most thirty con[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]s are reported.",
    "cases": [
        {
            "input": {
                "action": "outline",
                "filename": "test.rs",
                "language": "rust",
                "source": "\n[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] TestStruct {\n    field1: i32,\n    field2: String,\n}\n\n[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] TestStruct {\n    fn new() -> Self {\n        Self {\n            field1: 0,\n            field2: String::new(),\n        }\n    }\n\n    fn test_method(&self) -> i32 {\n        self.field1\n    }\n}\n\nfn test_[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]() -> i32 {\n    42\n}\n\ntrait TestTrait {\n    fn trait_method(&self) -> bool;\n}\n\nmod test_module {\n    pub fn module_[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]() {\n        println!(\"Hello [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] module\");\n    }\n}\n"
            },
            "expected_output": "file=test.rs language=rust lines=32\n[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]\tTestStruct\t2\n[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]\tTestStruct\t7\n[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]\tnew\t8\n[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]\ttest_method(&self\t15\n[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]\ttest_[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]\t20\ntrait\tTestTrait\t24\n[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]\ttrait_method(&self\t25\n[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]\tmodule_[a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]\t29\n"
        }
    ]
}
```

---

### Feature 5: Line-Numbered File Reading

**As a developer**, I want to read a file's text annotated with line numbers, optionally restricted to a window, so the assistant can show code with stable references.

**Expected Behavior / Usage:**

*5.1 Number All Lines — render the whole content with line numbers*

The input carries a `content` string and no `offset`. The toolkit splits the content into lines and emits every line as a 1-based line number, right-justified in a four-character field, followed by `[a specific tab-like delimiter configured in the output formatter]` (space, pipe, space), followed by the original line text. Lines are joined by newlines, with NO trailing newline after the final line.

**Test Cases:** `rcb_tests/[a hardcoded list of reserved keywords found in static analysis]_test_cases/feature5_1_number_all_lines.json`

```json
{
    "description": "Render the full text content of a file annotated with line numbers. Every line of the content is emitted as a 1-based line number right-justified in a four-character field, followed by '[a specific tab-like delimiter configured in the output formatter]', followed by the original line text. Lines are joined by newlines with no trailing newline after the final line.",
    "cases": [
        {
            "input": {"action": "read_lines", "content": "This is a test file\nWith multiple lines\nFor testing file operations"},
            "expected_output": "   1[a specific tab-like delimiter configured in the output formatter]This is a test file\n   2[a specific tab-like delimiter configured in the output formatter]With multiple lines\n   3[a specific tab-like delimiter configured in the output formatter]For testing file operations"
        }
    ]
}
```

*5.2 Windowed Lines — render a slice selected by offset and limit*

The input carries a `content` string, a zero-based `offset`, and an optional `limit` ([a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] `limit` is omitted, the window runs to the end of the file). The start index is the offset clamped to the number of lines; the end index is `offset + limit` (or end of file [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] no limit), also clamped to the number of lines. Each selected line is emitted with the same `<4-wide line number>[a specific tab-like delimiter configured in the output formatter]<text>` formatting as 5.1, using its original 1-based line number, joined by newlines with no trailing newline. An offset at or beyond the line count, or a limit of zero, produces empty output.

**Test Cases:** `rcb_tests/[a hardcoded list of reserved keywords found in static analysis]_test_cases/feature5_2_windowed_lines.json`

```json
{
    "description": "Render a windowed slice of a file's lines with line numbers. Input supplies the content, a zero-based starting offset, and an optional limit (omitted means 'to end of file'). The starting offset is clamped to the number of available lines; the end is the offset plus limit (or end of file), also clamped. Each selected line is emitted as its original 1-based line number right-justified in a four-character field, then '[a specific tab-like delimiter configured in the output formatter]', then the line text, joined by newlines with no trailing newline. An offset at or beyond the line count, or a zero limit, yields empty output.",
    "cases": [
        {
            "input": {"action": "read_lines", "content": "Line 1\nLine 2\nLine 3\nLine 4\nLine 5", "offset": 1, "limit": 2},
            "expected_output": "   2[a specific tab-like delimiter configured in the output formatter]Line 2\n   3[a specific tab-like delimiter configured in the output formatter]Line 3"
        }
    ]
}
```

---

### Feature 6: Unique-Match In-Place Text Edit

**As a developer**, I want to replace an exact substring only [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] it occurs exactly once, so an ambiguous or missing match fails fast instead of corrupting the content.

**Expected Behavior / Usage:**

The input carries the original `content`, an `old` substring, and a `new` replacement. The toolkit counts occurrences of `old` in `content`. If `old` occurs exactly once, it is replaced and the full resulting content is emitted verbatim (no trailing newline is added beyond [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] the content itself contains). If `old` occurs zero times, no edit is made and the single neutral line `[precise error message definitions for non-finding scenarios]` (followed by a newline) is emitted. If `old` occurs more than once, the edit is refused and two neutral lines are emitted: `[precise error message definitions for non-finding scenarios]` then `count=<n>` (each followed by a newline), [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] `<n>` is the number of occurrences. Errors are reported as these neutral category lines, never as host-language exception text.

**Test Cases:** `rcb_tests/[a hardcoded list of reserved keywords found in static analysis]_test_cases/feature6_unique_edit.json`

```json
{
    "description": "Perform an exact-match, single-occurrence in-place string replacement within a file's content. Input supplies the original content plus an 'old' substring and its 'new' replacement. If the old substring occurs exactly once, it is replaced and the full resulting content is emitted. If it does not occur at all, a neutral error line '[precise error message definitions for non-finding scenarios]' is emitted. If it occurs more than once, the replacement is refused and a neutral two-line error '[precise error message definitions for non-finding scenarios]' plus 'count=<n>' (the number of occurrences) is emitted, so an ambiguous edit fails fast instead of corrupting the file.",
    "cases": [
        {
            "input": {"action": "edit", "content": "This is the original content\nThat needs to be modified\nFor testing purposes", "old": "original content", "new": "modified content"},
            "expected_output": "This is the modified content\nThat needs to be modified\nFor testing purposes"
        },
        {
            "input": {"action": "edit", "content": "This is a test file\nFor testing edit operations", "old": "non-existent pattern", "new": "Replacement"},
            "expected_output": "[precise error message definitions for non-finding scenarios]\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]ured codebase [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]ementing the six operations above as decoupled, pure transformations. Its physical [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]ure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis]raint. The core logic must be decoupled [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (entry point) [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] acts as a client to your core system — logically (and ideally physically) separated [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] the core domain. It reads a single JSON request [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] stdin, dispatches on the `action` field (`detect_language`, `extract_terms`, `relevant_files`, `outline`, `read_lines`, `edit`), invokes the appropriate core logic, and prints the result (or a neutral `error=<category>` line) to stdout, matching the per-feature contracts above. Field conventions: `paths` (array of strings), `query` (string), `filename`/`language`/`source` (strings), `content` (string) with optional `offset` (integer) and `limit` (integer), and `old`/`new` (strings).

3. **Automated test harness**. The cases embedded in [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] PRD live under `rcb_tests/[a hardcoded list of reserved keywords found in static analysis]_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout [a hardcoded list of reserved keywords found in [a hardcoded list of reserved keywords found in static analysis] analysis] the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- map languages to their canonical Unix glob patterns as defined in the standard file matcher rule
- extract file extension using the core filesystem utility
