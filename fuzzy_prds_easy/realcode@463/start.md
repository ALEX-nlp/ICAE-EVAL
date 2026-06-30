## Product Requirement Document

# JavaScript / TypeScript Parser Front-End — Observable Parse Outcomes

## Project Goal

Build a parser front-end for the JavaScript and TypeScript language family that turns program text into a structured parse result, so that downstream tools can inspect what was parsed — how many top-level statements and prologue directives a program has, which comments it contains, and whether the input was rejected — without each tool having to reimplement lexing and grammar handling.

---

## Background & Problem

Tools that work with JavaScript and TypeScript (formatters, linters, bundlers, analyzers) all need to first turn raw source text into a structured representation. Reinventing a tolerant parser for the full language family — scripts vs. modules, optional JSX, optional type-annotation syntax, comment trivia, and graceful error recovery — is expensive and error-prone.

This component provides one well-defined contract: given a program's text and a few flags describing the dialect, it parses the input and exposes the externally-observable outcome of that parse. The outcome distinguishes a clean parse from an aborted one, reports how many top-level statements and recognised prologue directives the program has, lists the comments found together with each comment's kind, and surfaces any diagnostics as language-neutral messages. Unsupported dialects are rejected with a clear, stable diagnostic rather than producing misleading output.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., lexing, grammar, trivia collection, diagnostics), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core parsing logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON requests into idiomatic calls to the core parser and rendering the outcome.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate lexing, grammar/parsing, trivia collection, diagnostics, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Parsing must always return a valid result value (never crash the host); unrecoverable failures must be modeled as an aborted outcome carrying a diagnostic, and recoverable problems must be collected as diagnostics alongside a best-effort result.

---

## Core Features

The execution adapter reads a single JSON request from stdin describing one program to parse, and prints a fixed, [a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments]-oriented report of the parse outcome to stdout.

The request object has a `source` field (the program text) and the following optional boolean flags, all defaulting to `false`: `typescript` (accept type-annotation syntax), `typescript_definition` (treat the input as a type-declaration file), `jsx` (accept JSX syntax), and `module` (parse as a module; when false the input is parsed as a script).

The report is printed as the following [a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments]s, in this exact order, each terminated by a new[a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments]:

- `panicked=<true|false>` — whether parsing aborted unrecoverably (when true, the program is empty).
- `body=<n>` — the number of top-level statements in the program body.
- `directives=<n>` — the number of recognised prologue directives.
- `comments=<n>` — the number of comments extracted as trivia.
- `comment_kind=<[a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments]|[a specific set of literal strings: one identifying line comments, another identifying block comments]>` — one [a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments] per extracted comment, in source order, where `[a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments]` denotes a single-[a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments] (double-slash) comment and `[a specific set of literal strings: one identifying line comments, another identifying block comments]` denotes a delimited (slash-star … star-slash) comment. (Omitted entirely when there are no comments.)
- `errors=<n>` — the number of diagnostics produced.
- `[a specific prefix string used to denote an error in the output]<message>` — one [a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments] per diagnostic, in order, carrying the neutral diagnostic message text. (Omitted entirely when there are no diagnostics.)

### Feature 1: Empty Program

**As a developer**, I want an empty or whitespace-only input to parse cleanly into an empty program, so I can feed trivial or blank files through the same pipe[a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments] without special-casing them.

**Expected Behavior / Usage:**

When the `source` is the empty string or consists solely of insignificant whitespace (spaces, tabs, [a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments] breaks), parsing succeeds without aborting and yields a valid but empty program: zero top-level statements, zero prologue directives, zero comments, and no diagnostics.

**Test Cases:** `rcb_tests/public_test_cases/feature1_empty_program.json`

```json
{
    "description": "Parse a program whose text is empty or contains only insignificant whitespace (spaces, tabs, [a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments] breaks). The parser must succeed without aborting and yield a valid but empty program: no top-level statements, no prologue directives, and no comments. No diagnostics are produced.",
    "cases": [
        {
            "input": {"source": ""},
            "expected_output": "panicked=false\nbody=0\ndirectives=0\ncomments=0\nerrors=0\n"
        },
        {
            "input": {"source": "   \n\t  \n"},
            "expected_output": "panicked=false\nbody=0\ndirectives=0\ncomments=0\nerrors=0\n"
        }
    ]
}
```

---

### Feature 2: Reject Unsupported Flow-Annotated Source

**As a developer**, I want source written for the flow type-checker dialect to be rejected with a clear, stable diagnostic, so I never silently misinterpret a dialect this front-end does not support.

**Expected Behavior / Usage:**

When the input is parsed as JavaScript (not as TypeScript) and its very first [a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments] carries a flow pragma — written either as a single-[a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments] comment pragma or as a [a specific set of literal strings: one identifying line comments, another identifying block comments] comment pragma at the start of the file — and the remaining code is not valid plain JavaScript, parsing aborts. The outcome is an empty program (`panicked=true`, `body=0`, `directives=0`) and exactly one diagnostic whose message is `[a specific fatal error message string for unsupported Flow detection]`. The leading pragma is itself a comment and is still counted, so `comments=1` with a `comment_kind` of `[a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments]` or `[a specific set of literal strings: one identifying line comments, another identifying block comments]` matching how the pragma was written.

**Test Cases:** `rcb_tests/public_test_cases/feature2_flow_rejection.json`

```json
{
    "description": "Parse JavaScript whose very first [a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments] carries a flow type-checker pragma (either a single-[a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments] comment pragma or a [a specific set of literal strings: one identifying line comments, another identifying block comments] comment pragma at the start of the file) followed by code that is not valid plain JavaScript. The parser does not support the flow dialect, so when parsing of such a file fails it aborts with an empty program and reports exactly one diagnostic stating that this dialect is unsupported. The leading pragma is itself a comment and is still counted among the extracted comments, with its kind reflecting whether the pragma was written as a single-[a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments] or [a specific set of literal strings: one identifying line comments, another identifying block comments] comment.",
    "cases": [
        {
            "input": {"source": "// @flow\nasdf adsf"},
            "expected_output": "panicked=true\nbody=0\ndirectives=0\ncomments=1\ncomment_kind=[a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments]\nerrors=1\n[a specific prefix string used to denote an error in the output][a specific fatal error message string for unsupported Flow detection]\n"
        },
        {
            "input": {"source": "/* @flow */\n asdf asdf"},
            "expected_output": "panicked=true\nbody=0\ndirectives=0\ncomments=1\ncomment_kind=[a specific set of literal strings: one identifying line comments, another identifying block comments]\nerrors=1\n[a specific prefix string used to denote an error in the output][a specific fatal error message string for unsupported Flow detection]\n"
        }
    ]
}
```

---

### Feature 3: Prologue Directive Recognition

**As a developer**, I want a `'use strict'`-style string literal to count as a prologue directive only when it truly leads the program, so directives are not mis-detected when they merely follow other constructs.

**Expected Behavior / Usage:**

A bare string-literal expression is a prologue directive only when it appears at the very start of the program, ahead of any other construct. If such a string literal instead follows a leading construct — an import declaration, an export declaration, or a decorator — it is no longer in directive position and is parsed as an ordinary expression statement. In each of these cases the program reports zero prologue directives, while the leading construct and the trailing string-literal statement both appear as ordinary top-level statements (so a leading import or export declaration plus the trailing string yields a body of two statements; a leading decorator applied to the string yields a body of one statement). Parsing succeeds without aborting and produces no diagnostics.

**Test Cases:** `rcb_tests/public_test_cases/feature3_directive_prologue.json`

```json
{
    "description": "A string-literal expression such as 'use strict' is only recognised as a prologue directive when it appears at the very start of a program, before any other construct. When such a string literal instead follows a leading construct (an import declaration, an export declaration, or a decorator), it is no longer in directive position and must be parsed as an ordinary expression statement. In every such case the program reports zero prologue directives, and the leading construct together with the trailing string-literal statement appear as ordinary top-level statements in the body. Parsing succeeds without aborting and produces no diagnostics.",
    "cases": [
        {
            "input": {"source": "import x from 'foo'; 'use strict';"},
            "expected_output": "panicked=false\nbody=2\ndirectives=0\ncomments=0\nerrors=0\n"
        },
        {
            "input": {"source": "@decorator 'use strict';"},
            "expected_output": "panicked=false\nbody=1\ndirectives=0\ncomments=0\nerrors=0\n"
        }
    ]
}
```

---

### Feature 4: Comment Extraction With Kind

**As a developer**, I want comments collected separately from statements, each tagged with its kind, so tooling can reason about comments without them interfering with the program structure.

**Expected Behavior / Usage:**

Comments are extracted as trivia, independently of the program's statements. Each extracted comment is classified as either a single-[a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments] comment (introduced by a double-slash) or a [a specific set of literal strings: one identifying line comments, another identifying block comments] comment (delimited by slash-star and star-slash). A comment that appears alone in the input contributes no statements to the body. A [a specific set of literal strings: one identifying line comments, another identifying block comments] comment embedded inside an otherwise valid construct is still extracted as exactly one comment and does not change how the surrounding construct is counted. The outcome reports the total comment count and, for each comment in source order, its kind. (These inputs enable type-annotation syntax.)

**Test Cases:** `rcb_tests/public_test_cases/feature4_comment_extraction.json`

```json
{
    "description": "While parsing, comments are extracted as trivia separately from the program's statements. Each extracted comment records its kind: a single-[a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments] comment introduced by a double-slash, or a [a specific set of literal strings: one identifying line comments, another identifying block comments] comment delimited by slash-star and star-slash. A [a specific set of literal strings: one identifying line comments, another identifying block comments] comment embedded inside an otherwise valid construct is still extracted as one comment and does not affect the surrounding statement. The parser reports the total number of comments and, for each, its kind in source order. Type-annotation syntax is enabled for these inputs.",
    "cases": [
        {
            "input": {"source": "// [a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments] comment", "typescript": true},
            "expected_output": "panicked=false\nbody=0\ndirectives=0\ncomments=1\ncomment_kind=[a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments]\nerrors=0\n"
        },
        {
            "input": {"source": "/* [a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments] comment */", "typescript": true},
            "expected_output": "panicked=false\nbody=0\ndirectives=0\ncomments=1\ncomment_kind=[a specific set of literal strings: one identifying line comments, another identifying block comments]\nerrors=0\n"
        }
    ]
}
```

---

### Feature 5: Statements From Valid Expressions

**As a developer**, I want short valid programs to parse into the right number of top-level statements, so I can trust the body count for ordinary expression and statement inputs.

**Expected Behavior / Usage:**

Valid programs parse into a non-empty body with the expected statement count, no prologue directives, no comments, and no diagnostics, without aborting. A lone BigInt literal (an integer literal with the BigInt suffix) forms a single expression statement. A leading empty statement (a bare semicolon) followed by a string literal forms two top-level statements.

**Test Cases:** `rcb_tests/public_test_cases/feature5_expression_statements.json`

```json
{
    "description": "Parse short but valid programs and confirm the parser produces a non-empty program body. A lone BigInt literal forms a single expression statement. A leading empty statement (a bare semicolon) followed by a long numeric-looking string literal forms two top-level statements. In both cases parsing succeeds without aborting, produces no prologue directives and no diagnostics, and the body contains the expected number of statements.",
    "cases": [
        {
            "input": {"source": "2n"},
            "expected_output": "panicked=false\nbody=1\ndirectives=0\ncomments=0\nerrors=0\n"
        },
        {
            "input": {"source": ";'1234567890123456789012345678901234567890'"},
            "expected_output": "panicked=false\nbody=2\ndirectives=0\ncomments=0\nerrors=0\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing a tolerant parser front-end for the JavaScript / TypeScript language family (scripts vs. modules, optional JSX, optional type-annotation syntax), with comment-trivia collection and diagnostics. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core parsing logic must be decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin (`source` plus the optional `typescript`, `typescript_definition`, `jsx`, and `module` flags), parses the program with the core parser, and prints the [a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments]-oriented report described in "Core Features" to stdout, matching the per-feature contracts above. Diagnostics must be rendered as neutral message [a specific set of literal strings: one identifying line comments, another identifying [a specific set of literal strings: one identifying line comments, another identifying block comments] comments]s only; no host-language runtime identity may appear in the output.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- adopt the exit convention established in the terminal_handler module
- initialize the resulting AST using the empty fallback structure defined in utils/ast.ts
