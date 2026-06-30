## Product Requirement Document

# Behavior-Driven Step Definition Core — Step Matching, Snippet Generation, Data Tables & Tag Expressions

## Project Goal

Build the deterministic core of a behavior-driven-development (BDD) automation library that connects plain-language scenario steps to executable step definitions. The core lets developers register step-definition patterns, match a written step against them while extracting its embedded arguments, generate a ready-to-paste stub for any step that has no definition yet, model the tabular data attached to a step, and decide whether a scenario's tags satisfy a tag-filter expression — all as pure, value-in/value-out logic with no I/O, sockets, or external processes.

---

## Background & Problem

In BDD, feature files describe behavior in readable sentences ("steps"), and each step is wired to code through a matcher pattern. Without a shared core, every tool re-implements the same fiddly pieces: turning a step sentence into a regex-safe stub, matching steps to definitions and pulling out the typed arguments at the right character offsets, validating the data tables attached to steps, and evaluating the boolean tag filters that decide which scenarios run.

This library provides one well-defined contract for those pieces. It exposes: a snippet generator that converts an undefined step into a suggested definition stub (with correct escaping); a regular-expression matcher that reports captured values and their positions; a step registry that matches a step description against many registered patterns at once; a data-table builder with strict shape rules; and disjunctive/conjunctive tag-expression evaluators. Each piece is deterministic and observable purely through its return values.

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

### Feature 1: Undefined-Step Snippet Generation

**As a developer**, I want an undefined step turned into a ready-to-paste definition stub with all special characters escaped, so I can implement the missing step without hand-escaping regex and string syntax.

**Expected Behavior / Usage:**

*1.1 Step snippet stub — assemble the suggested definition stub for a step.*

Given a step keyword and the literal text of the step, produce a multi-line stub. The keyword is upper-cased and placed first, followed by a parenthesised, double-quoted, anchored pattern: a leading caret `^`, then the step text transformed so it would match literally (every regular-expression metacharacter is backslash-escaped, then every double-quote and backslash is escaped a second time so the pattern is valid inside a double-quoted string literal), then a trailing `$`. After the pattern comes a fixed body that marks the step as pending. Every line is newline-terminated.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_snippet.json`

```json
{
    "description": "Given a step keyword and the literal text of an undefined step, produce a ready-to-paste step-definition stub. The stub uppercases the keyword, then on the first line emits the keyword followed by, in parentheses and double quotes, an anchored pattern built from the step text: a leading caret, the step text with every regular-expression metacharacter backslash-escaped and then every double-quote and backslash escaped again for embedding inside a C-style string literal, and a trailing dollar sign. The body is a fixed two-line block that marks the step as pending.",
    "cases": [
        {
            "input": {"action": "snippet", "keyword": "then", "step_name": "x|y\"z"},
            "expected_output": "THEN(\"^x\\\\|y\\\"z$\") {\n    pending();\n}\n"
        }
    ]
}
```

*1.2 Regex-metacharacter escaping — escape a literal string for use as a pattern.*

Given an arbitrary literal string, return it with every regular-expression metacharacter prefixed by a backslash so the result matches the original text literally. The escaped characters are the alternation bar, parentheses, square brackets, curly braces, caret, dollar, star, plus, question mark, dot and backslash; all other characters are unchanged. The single-line result is newline-terminated.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_regex_escape.json`

```json
{
    "description": "Given an arbitrary literal string, return the string with every regular-expression metacharacter escaped by a preceding backslash so the result matches the original text literally when used as a pattern. The metacharacters that get escaped are the alternation bar, parentheses, square brackets, curly braces, caret, dollar, star, plus, question mark, dot and backslash; all other characters pass through unchanged.",
    "cases": [
        {
            "input": {"action": "escape_regex", "text": "abc|()[]{}^$*+?.\\def"},
            "expected_output": "abc\\|\\(\\)\\[\\]\\{\\}\\^\\$\\*\\+\\?\\.\\\\def\n"
        }
    ]
}
```

*1.3 String-literal escaping — escape a string for embedding in a double-quoted literal.*

Given an arbitrary literal string, return it escaped for safe embedding inside a double-quoted string literal: every double-quote and every backslash is prefixed with a backslash, and all other characters are unchanged. The single-line result is newline-terminated.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_cstring_escape.json`

```json
{
    "description": "Given an arbitrary literal string, return the string escaped for safe embedding inside a double-quoted C-style string literal: every double-quote character and every backslash character is prefixed with a backslash, while all other characters pass through unchanged.",
    "cases": [
        {
            "input": {"action": "escape_cstring", "text": "abc\"def\\ghi"},
            "expected_output": "abc\\\"def\\\\ghi\n"
        }
    ]
}
```

---

### Feature 2: Regular-Expression Matching With Captured Arguments

**As a developer**, I want to match a pattern against a string and recover each captured group's value and offset, so I can extract step arguments and their positions.

**Expected Behavior / Usage:**

*2.1 Single match with captures — match a pattern once and report captured groups.*

Match a pattern against an input string. The first line reports whether a match occurred. On a successful match, each capturing group is reported in order with its captured value and its zero-based character position in the input; a pattern with no capturing groups reports only the match. A failed match reports no captured groups. Anchored patterns (`^`…`$`) only match when the whole string conforms.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_regex_find.json`

```json
{
    "description": "Match a regular expression against an input string, reporting whether it matched and, when it did, the value and zero-based character position of each captured group in the order they appear. The first output line states whether a match occurred. When the pattern contains no capturing groups a successful match reports the match only; when it contains capturing groups each captured substring is reported with its absolute position in the input. A failed match reports no captured groups.",
    "cases": [
        {
            "input": {"action": "regex_find", "pattern": "^cde$", "text": "cde"},
            "expected_output": "[special case for empty AND queries]\n"
        },
        {
            "input": {"action": "regex_find", "pattern": "^(\\d+)\\+\\d+=(\\d+)$", "text": "42+27=69"},
            "expected_output": "[special case for empty AND queries]\nsubmatch[0] value=42 position=0\nsubmatch[1] value=69 position=6\n"
        }
    ]
}
```

*2.2 Tokenized scan — extract the first group of every token.*

Scan the input from the start for consecutive non-overlapping tokens that each match the pattern, and report the value of each token's first capturing group, in order. The first line reports whether any token was found; an input that yields no tokens reports the no-match outcome with no values.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_regex_find_all.json`

```json
{
    "description": "Scan an input string from the beginning for consecutive non-overlapping tokens that each match the supplied pattern, and report the value of the first capturing group of every token in order. The first output line states whether at least one token was found. When the input yields no tokens, no token values are reported; otherwise each token's first-group value is listed in order of appearance.",
    "cases": [
        {
            "input": {"action": "regex_find_all", "pattern": "([^,]+)(?:,|$)", "text": "a,b,cc"},
            "expected_output": "[special case for empty AND queries]\ntoken[0]=a\ntoken[1]=b\ntoken[2]=cc\n"
        }
    ]
}
```

---

### Feature 3: Step Definition Registry & Matching

**As a developer**, I want to register many step-definition patterns and match a written step against all of them at once, recovering which ones matched and the arguments they captured, so I can route a step to its implementation and supply its parameters.

**Expected Behavior / Usage:**

Register an ordered list of matcher patterns, then match a single step description against the whole set. Report the number of matching definitions, and for each match (in registration order) the zero-based index of the matching definition, the number of captured arguments, and each argument's value and absolute position. A plain-text matcher matches any description that contains it; a matcher with capturing groups also extracts the argument values and offsets. The same matcher registered more than once yields one match per registration. Patterns and descriptions may contain non-ASCII text, compared literally.

**Test Cases:** `rcb_tests/public_test_cases/feature3_step_match.json`

```json
{
    "description": "Register an ordered list of step-definition matcher patterns, then match a single step description against all of them. Report how many definitions matched and, for each match in registration order, the zero-based index of the matching definition together with the count and the value and absolute position of every captured argument. A plain-text matcher matches a description that contains it; a matcher with capturing groups extracts the corresponding argument values and positions. Identical matchers registered more than once each produce their own match. Matchers and descriptions may contain non-ASCII text, which is compared literally.",
    "cases": [
        {
            "input": {"action": "step_match", "definitions": ["match no params", "match the (\\w+) param", "match a (.+)$", "match params (\\w+), (\\w+) and (\\w+)"], "query": "match the first param"},
            "expected_output": "matches=1\ndef[1] args=1\narg[0] value=first position=10\n"
        },
        {
            "input": {"action": "step_match", "definitions": ["a matcher", "another matcher", "a matcher"], "query": "a matcher"},
            "expected_output": "matches=2\ndef[0] args=0\ndef[2] args=0\n"
        }
    ]
}
```

---

### Feature 4: Data Table Builder

**As a developer**, I want to build the tabular data attached to a step from a sequence of column and row operations, with strict shape validation, so malformed tables fail fast instead of silently corrupting data.

**Expected Behavior / Usage:**

Apply an ordered sequence of operations that either declare a column or append a row of cell values, then report the table. A row may be appended only after at least one column exists and must supply exactly one value per declared column; a column may not be declared once any row has been appended. On success, report the row count followed by one line per row pairing each column name with its value, column names in sorted order. A rule violation halts processing and reports a neutral error category: a row whose width differs from the column count, a row appended before any column is declared, or a column declared after rows exist.

**Test Cases:** `rcb_tests/public_test_cases/feature4_table.json`

```json
{
    "description": "Build a data table by applying an ordered sequence of operations that either declare a column or append a row of cell values, then report the table contents. A row may only be appended after at least one column is declared and must supply exactly one value per declared column; columns may not be declared after any row has been appended. On success the number of rows is reported followed by one line per row pairing each column name with its cell value (column names in sorted order). A violated rule stops processing and reports a neutral error category instead: a row whose width does not match the number of columns, a row appended before any column is declared, or a column declared after rows already exist.",
    "cases": [
        {
            "input": {"action": "table", "ops": [{"add_column": "C1"}, {"add_column": "C2"}, {"add_column": "C3"}, {"add_row": ["R11", "R12", "R13"]}, {"add_row": ["R21", "R22", "R23"]}, {"add_row": ["R31", "R32", "R33"]}, {"add_row": ["R41", "R42", "R43"]}]},
            "expected_output": "rows=4\nrow[0] [formatting constraints for cartesian products]\nrow[1] C1=R21 C2=R22 C3=R23\nrow[2] C1=R31 C2=R32 C3=R33\nrow[3] C1=R41 C2=R42 C3=R43\n"
        },
        {
            "input": {"action": "table", "ops": [{"add_column": "C1"}, {"add_row": ["R1", "R2"]}]},
            "expected_output": "error=row_size_mismatch\n"
        }
    ]
}
```

---

### Feature 5: Tag Expression Evaluation

**As a developer**, I want to test whether a scenario's tags satisfy a tag-filter expression, so I can decide which scenarios a filter selects.

**Expected Behavior / Usage:**

*5.1 Disjunctive (OR) expression — match when any token is present.*

A disjunctive expression is a comma-separated list of tag tokens (optional surrounding spaces). It matches a candidate tag list when at least one of its tokens is present in that list; an empty expression matches no tag list. Each candidate tag list is evaluated independently and reported on its own line with the comma-joined tags and the match outcome.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_or_tags.json`

```json
{
    "description": "Evaluate a disjunctive tag expression against one or more candidate tag lists. The expression is a comma-separated list of tag tokens (optionally spaced) and matches a tag list when at least one of its tokens is present in that list. An empty expression matches no tag list. For each candidate tag list the comma-joined tags and whether the expression matched are reported, one line per candidate.",
    "cases": [
        {
            "input": {"action": "tag_or", "expression": "@a,@b,@c", "queries": [["a"], ["b"], ["a", "b"], ["x", "a", "b"], ["x", "y", "z"]]},
            "expected_output": "query=a [special case for empty AND queries]\nquery=b [special case for empty AND queries]\nquery=a,b [special case for empty AND queries]\nquery=x,a,b [special case for empty AND queries]\nquery=x,y,z matched=false\n"
        }
    ]
}
```

*5.2 Conjunctive (AND) expression — match when every sub-expression is satisfied.*

A conjunctive expression is a comma-separated list of quoted sub-expressions (optional surrounding spaces). It matches a candidate tag list only when every sub-expression matches it, where each quoted sub-expression is itself a disjunctive group (its comma-separated tokens) that matches when any token is present. An empty expression matches every tag list. Each candidate is reported on its own line with the comma-joined tags and the match outcome.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_and_tags.json`

```json
{
    "description": "Evaluate a conjunctive tag expression against one or more candidate tag lists. The expression is a comma-separated list of quoted sub-expressions (optionally spaced), and matches a tag list only when every sub-expression matches it; each quoted sub-expression is itself a disjunctive (comma-separated) group that matches when any of its tokens is present. An empty expression matches every tag list. For each candidate tag list the comma-joined tags and whether the expression matched are reported, one line per candidate.",
    "cases": [
        {
            "input": {"action": "tag_and", "expression": "\"@a\",\"@b\"", "queries": [["a", "b"], ["x", "a", "b"], ["a"], ["b"], ["a", "y"], ["x", "b"], ["x", "y"]]},
            "expected_output": "query=a,b [special case for empty AND queries]\nquery=x,a,b [special case for empty AND queries]\nquery=a matched=false\nquery=b matched=false\nquery=a,y matched=false\nquery=x,b matched=false\nquery=x,y matched=false\n"
        },
        {
            "input": {"action": "tag_and", "expression": "\"@a,@b\", \"@c\", \"@d,@e,@f\"", "queries": [["a", "c", "d"], ["x", "c", "f"]]},
            "expected_output": "query=a,c,d [special case for empty AND queries]\nquery=x,c,f matched=false\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above (snippet generation with escaping, regular-expression matching with captures, the step-definition registry and matcher, the data-table builder, and the tag-expression evaluators). Its physical structure MUST align with the "Scale-Driven Code Organization" constraint, and the core logic MUST be decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program that reads a single JSON request from stdin and prints the result to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `snippet`, `escape_regex`, `escape_cstring`, `regex_find`, `regex_find_all`, `step_match`, `table`, `tag_or`, and `tag_and`. The adapter translates JSON into idiomatic core calls and renders results to the neutral line contract; native errors raised by the core (such as a table-shape violation) are caught at this layer and rendered as neutral `error=<category>` lines — the core may still raise idiomatic exceptions, but their language identity must never appear in stdout.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the cartesian product expansion convention
- adhere to the escape_regex character set
