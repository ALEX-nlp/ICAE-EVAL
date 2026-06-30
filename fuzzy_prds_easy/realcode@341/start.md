## Product Requirement Document

# Source-Aware Spell Checker - Spell Checking for Code and Prose

## Project Goal

Build a spell-checking engine that understands source code, so developers can flag genuine spelling mistakes in identifiers, comments, and string literals without drowning in false positives from keywords, syntax, URLs, hex colors, and other technical strings that ordinary spell checkers cannot tell apart from real words.

---

## Background & Problem

Without a code-aware checker, developers either skip spell checking on their source entirely or run a prose spell checker over it and are buried under noise: every language keyword, every `camelCase` identifier, every URL, hex color, file path, and base64 blob is reported as "misspelled". The signal-to-noise ratio is so poor that the tool gets disabled. Catching a typo in a public method name or a user-facing string then falls back to manual review, where it is routinely missed and ships to production.

With this engine, the same body of code is parsed structurally first: only the regions a human actually wrote as words — declared names, comments, and string contents — are examined, each identifier is split into its real constituent words, and technical strings are masked out before checking. The result is a short, trustworthy list of true misspellings with their exact byte positions, plus correction suggestions, suitable for driving an editor's squiggly underlines.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This is a multi-responsibility system (identifier splitting, technical-string masking, syntax-aware region extraction, dictionary lookup, suggestion generation, end-to-end orchestration, and a configuration layer). It MUST NOT be a single "god file"; output a clear, multi-file directory tree (e.g. `src/` with cohesive modules, `tests/`) that reflects a production-grade repository. Do not over-engineer, but strictly avoid monolithic files here.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core spell-checking logic must remain completely decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls to the core domain and rendering results as text.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Separate word splitting, skip-pattern masking, source-region extraction, dictionary membership, suggestion generation, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** Adding a new source language or a new skip pattern must not require modifying the core checking engine.
   - **Liskov Substitution Principle (LSP):** All dictionary kinds (in-memory word list, affix-based) must be substitutable behind one dictionary abstraction.
   - **Interface Segregation Principle (ISP):** Keep the dictionary and configuration interfaces small and cohesive.
   - **Dependency Inversion Principle (DIP):** The engine must depend on a dictionary abstraction and a configuration abstraction, not on concrete file/network loaders.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core must be elegant and idiomatic to the target language, hiding parsing and dictionary plumbing.
   - **Resilience:** All byte offsets must be valid UTF-8 boundaries and remain correct in the presence of multi-byte and multi-codepoint characters. Invalid or unsupported requests must be modeled as explicit errors, not crashes. Unsupported language identifiers degrade gracefully to plain-prose handling rather than failing.

---

## Core Features

### Feature 1: Identifier Word Splitting

**As a developer**, I want a single compound identifier broken into the real words it contains, so I can spell-check each word of a `camelCase`, `snake_case`, or `SCREAMING_SNAKE` name independently.

**Expected Behavior / Usage:**

The input is one contiguous token. The splitter emits the constituent words with their positions. Splits happen at: a lowercase letter immediately followed by an uppercase letter (a case hump); inside a run of uppercase letters, where the last capital of the run attaches to the following lowercase word (so an acronym directly before a capitalized word, like an all-caps prefix joined to a `Capitalized` word, is separated correctly); at underscores, periods, colons, and hyphens, which act purely as separators and are themselves never emitted; and at every transition between letters and digits. Any segment consisting only of digits is discarded. Each surviving word is reported on its own line as `<start_byte> <end_byte> <word>`, where the offsets are UTF-8 byte offsets into the original token, ordered by position. The request shape is `{"op":"split","text":<token>}` with no language field.

**Test Cases:** `rcb_tests/public_test_cases/feature1_identifier_splitting.json`

```json
{
  "description": "A single contiguous identifier or token is broken into its constituent words. Splits occur at lowercase-to-uppercase humps, inside uppercase runs (an uppercase run keeps its trailing capital with the following lowercase word, so an acronym immediately before a capitalized word is separated correctly), at underscores, periods, colons and hyphens (these separators are consumed and never emitted), and at every transition between letters and digits. Segments made only of digits are discarded. Each surviving word is reported as its UTF-8 start byte offset, end byte offset, and text, one per line, ordered by position. The request is {\"op\":\"split\",\"text\":<token>} with no language.",
  "cases": [
    {
      "input": {"op": "split", "text": "calculateUserAge"},
      "expected_output": "0 9 calculate\n9 13 User\n13 16 Age\n"
    },
    {
      "input": {"op": "split", "text": "XMLHttpRequest"},
      "expected_output": "0 3 XML\n3 7 Http\n7 14 Request\n"
    }
  ]
}
```

---

### Feature 2: Technical-String Masking

**As a developer**, I want URLs, emails, hex colors, file paths, and hashes ignored when checking prose, so the random-looking letters inside them are never reported as misspelled words.

**Expected Behavior / Usage:**

The input is a line of prose that may contain technical strings. Before tokenizing, spans that match the built-in skip patterns are masked out; any word that is fully or partially covered by a masked span is dropped, while ordinary words around it are kept. The built-in patterns cover web URLs (`http`/`https`), email addresses, hex color codes introduced by a leading `#`, absolute filesystem paths, and long hexadecimal hashes. Each surviving word is reported on its own line as `<start_byte> <end_byte> <word>` using UTF-8 byte offsets into the original text, ordered by position. The request shape is `{"op":"skip","text":<text>}`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_skip_patterns.json`

```json
{
  "description": "Before tokenizing prose, spans matching built-in skip patterns for technical strings are masked out, so any word fully or partially covered by such a span is removed from the results while ordinary surrounding words are still emitted. The default patterns cover web URLs, email addresses, hex color codes introduced by a leading hash sign, absolute filesystem paths, and long hexadecimal hashes. Each surviving word is reported as its UTF-8 start byte offset, end byte offset, and text, one per line, ordered by position. The request is {\"op\":\"skip\",\"text\":<text>}.",
  "cases": [
    {
      "input": {"op": "skip", "text": "visit https://example.com/page now"},
      "expected_output": "0 5 visit\n31 34 now\n"
    },
    {
      "input": {"op": "skip", "text": "contact admin@example.com please"},
      "expected_output": "0 7 contact\n26 32 please\n"
    }
  ]
}
```

---

### Feature 3: Word-List Dictionary Membership

**As a developer**, I want to ask whether a word exists in a known word list, case-insensitively, so I can decide whether it is spelled correctly regardless of capitalization.

**Expected Behavior / Usage:**

A plain dictionary is built from a list of entry strings, then answers membership for a list of query words. A query word is considered known when its lowercased form equals the lowercased form of any entry; the original casing on either side is irrelevant. For each query word the output is one line: the query word exactly as given, a single space, and `true` if known or `false` if unknown — in the same order the query words were supplied. The request shape is `{"op":"check","dict":[entries...],"words":[queries...]}`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_dictionary_lookup.json`

```json
{
  "description": "A plain word-list dictionary is built from a list of entries and answers membership queries case-insensitively: a query word is known when its lowercased form equals the lowercased form of any entry, regardless of the original casing on either side. For each query word the result is the word, a space, and either true (known) or false (unknown), one per line, in the order the query words were given. The request is {\"op\":\"check\",\"dict\":[entries...],\"words\":[queries...]}.",
  "cases": [
    {
      "input": {"op": "check", "dict": ["Hello", "world", "Rust"], "words": ["hello", "WORLD", "rust", "python"]},
      "expected_output": "hello true\nWORLD true\nrust true\npython false\n"
    }
  ]
}
```

---

### Feature 4: Correction Suggestions

**As a developer**, I want a short ranked list of plausible corrections for a misspelled word, so I can offer quick fixes in an editor.

**Expected Behavior / Usage:**

The input is a single word. Using an affix-based English dictionary fixture, the engine returns an ordered list of at most five candidate corrections. The casing of the candidates is adapted to the casing of the query word: an all-uppercase query upper-cases every candidate, an all-lowercase query lower-cases every candidate, and a mixed- or title-cased query leaves the candidate text unchanged. Each candidate is printed on its own line, in ranked suggestion order. The request shape is `{"op":"suggest","word":<word>}`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_suggestions.json`

```json
{
  "description": "Given a misspelled word, an ordered list of at most five correction candidates is produced from the bundled English affix/dictionary fixture. The casing of the candidates follows the casing of the query word: an all-uppercase query upper-cases the candidates, an all-lowercase query lower-cases them, and mixed or title casing leaves candidate text unchanged. Each candidate is printed on its own line in suggestion order. The request is {\"op\":\"suggest\",\"word\":<word>}.",
  "cases": [
    {
      "input": {"op": "suggest", "word": "wrld"},
      "expected_output": "world\nweld\nwild\nwold\n"
    },
    {
      "input": {"op": "suggest", "word": "colot"},
      "expected_output": "clot\ncoot\ncolt\ncolon\ncolor\n"
    }
  ]
}
```

---

### Feature 5: Source-Region Extraction

**As a developer**, I want only the human-authored words in my source extracted before splitting, so keywords, operators, punctuation, and numeric literals are never spell-checked.

**Expected Behavior / Usage:**

The input is a fragment of source code plus a language identifier (for example `rust` or `python`). The engine performs a syntax-aware parse and extracts only the spell-checkable regions: declared names (function, parameter, local binding, type, and field names), comment text, and the contents of string literals. Language keywords, operators, punctuation, and numeric literals are excluded. Each extracted region is then run through the same word splitter from Feature 1 (case humps, separators consumed, letter/digit transitions, digit-only segments discarded). Every resulting word is reported on its own line as `<start_byte> <end_byte> <word>`, where offsets are UTF-8 byte offsets into the whole original input, ordered by position. An unrecognized language identifier falls back to treating the input as plain prose. The request shape is `{"op":"split","text":<source>,"lang":<id>}`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_code_extraction.json`

```json
{
  "description": "When a source language is supplied, a syntax-aware parse first extracts only the spell-checkable regions of code: declared names (function, parameter, local binding, type, field names), comment text, and the contents of string literals. Language keywords, operators, punctuation and numeric literals are not extracted. The extracted regions are then run through the same word splitter (case humps, separators, letter/digit transitions, digit-only segments discarded). Each resulting word is reported as its UTF-8 start byte offset within the whole input, end byte offset, and text, one per line, ordered by position. The request is {\"op\":\"split\",\"text\":<source>,\"lang\":<id>}.",
  "cases": [
    {
      "input": {"op": "split", "lang": "rust", "text": "let userName = 42; // greet visitor"},
      "expected_output": "4 8 user\n8 12 Name\n22 27 greet\n28 35 visitor\n"
    },
    {
      "input": {"op": "split", "lang": "rust", "text": "fn parseValue() { let s = \"helloWorld\"; }"},
      "expected_output": "3 8 parse\n8 13 Value\n22 23 s\n27 32 hello\n32 37 World\n"
    }
  ]
}
```

---

### Feature 6: End-to-End Spell Checking

**As a developer**, I want one call that takes text or source and returns exactly the words that are genuinely misspelled, with their positions, so I can drive editor diagnostics directly.

**Expected Behavior / Usage:**

This feature composes the previous building blocks into a single pipeline: optional source-region extraction, technical-string masking, identifier splitting, and dictionary membership. A word is reported as misspelled only when it is not found in any active dictionary after all masking and allowances are applied. Every reported misspelling is one line `<start_byte> <end_byte> <word>` with UTF-8 byte offsets into the whole original input, ordered by position. Correctly spelled input produces empty output. The request shape is `{"op":"spellcheck","text":<text>,"lang":<id>, ...}`, where the optional `lang` selects a source parser (omit or use `text` for plain prose) and optional configuration fields are described in the sub-features below.

*6.1 Prose Spell Checking — checking plain text*

When `lang` is `text` (or omitted), the input is treated as prose: it is tokenized into words and every word not found in the active dictionaries is reported as a misspelling. Correctly spelled prose yields empty output. Offsets are UTF-8 byte offsets into the input, ordered by position.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_prose_spellcheck.json`

```json
{
  "description": "Plain prose is checked end to end: the text is tokenized into words and every word that is not found in the active dictionaries is reported as a misspelling, while correctly spelled words produce no output. Each misspelled word is reported as its UTF-8 start byte offset, end byte offset, and text, one per line, ordered by position; correctly spelled input yields empty output. The request is {\"op\":\"spellcheck\",\"text\":<text>,\"lang\":\"text\"}.",
  "cases": [
    {
      "input": {"op": "spellcheck", "lang": "text", "text": "hello regular regu"},
      "expected_output": "14 18 regu\n"
    },
    {
      "input": {"op": "spellcheck", "lang": "text", "text": "the quick brown fox jumps over the lazy dog"},
      "expected_output": ""
    }
  ]
}
```

*6.2 Source Spell Checking — checking code in a given language*

When a source `lang` is supplied, the spell-checkable regions (declared names, comments, string literals) are extracted with a syntax-aware parse, split into words, and each word not found in the active dictionaries is reported. Keywords, syntax, numeric literals, and dictionary-known words produce no output, so standard identifiers and dotted call targets are not flagged. Offsets are UTF-8 byte offsets into the whole original input, ordered by position.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_source_spellcheck.json`

```json
{
  "description": "Source code is checked end to end: the spell-checkable regions (declared names, comments, string literals) are extracted with a syntax-aware parse, split into words, and each word not found in the active dictionaries is reported as a misspelling. Keywords, syntax, numbers, and dictionary-known words produce no output, so dotted call targets and standard identifiers are not flagged. The supplied language id selects the parser. Each misspelling is reported as its UTF-8 start byte offset within the whole input, end byte offset, and text, one per line, ordered by position. The request is {\"op\":\"spellcheck\",\"text\":<source>,\"lang\":<id>}.",
  "cases": [
    {
      "input": {"op": "spellcheck", "lang": "rust", "text": "\n        // Comment with a typo: mment\n        "},
      "expected_output": "33 38 mment\n"
    },
    {
      "input": {"op": "spellcheck", "lang": "rust", "text": "\n        pub struct BadSpeler {\n            /// Terrible spelling: dwnloader\n            pub dataz: String,\n        }\n        "},
      "expected_output": "23 29 Speler\n67 76 dwnloader\n93 98 dataz\n"
    },
    {
      "input": {"op": "spellcheck", "lang": "python", "text": "\n        def calculat_user_age(bithDate) -> int:\n            # This is an examle_function that calculates age\n            usrAge = get_curent_date() - bithDate\n            userAge\n    "},
      "expected_output": "13 21 calculat\n31 35 bith\n74 80 examle\n"
    }
  ]
}
```

*6.3 Technical-String Masking In Context — skip patterns during a full check*

During an end-to-end check, technical strings embedded in prose or source are masked before tokenizing, so the letters inside web URLs, email addresses, hex color codes, and absolute filesystem paths are never reported as misspellings even though they are not real words. Ordinary misspelled words around them are still flagged. Offsets are UTF-8 byte offsets into the input, ordered by position.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_skip_in_context.json`

```json
{
  "description": "During an end-to-end check, technical strings embedded in prose or source are masked before tokenizing, so the letters inside web URLs, email addresses, hex color codes, and absolute filesystem paths are never reported as misspellings even though they are not real words. Ordinary misspelled words around them are still flagged. Each reported misspelling is its UTF-8 start byte offset, end byte offset, and text, one per line, ordered by position. The request is {\"op\":\"spellcheck\",\"text\":<text>,\"lang\":\"text\"}.",
  "cases": [
    {
      "input": {"op": "spellcheck", "lang": "text", "text": "\n        Visit https://www.exampl.com/badspeling for more info.\n        But this actualbadword should be flagged.\n    "},
      "expected_output": "81 94 actualbadword\n"
    },
    {
      "input": {"op": "spellcheck", "lang": "text", "text": "\n        Contact usr@exampl.com or admin@badspeling.org\n        This misspelledword should be flagged though.\n    "},
      "expected_output": "69 83 misspelledword\n"
    }
  ]
}
```

*6.4 Allowlist — accepting project-specific words*

An end-to-end check can be given an allowlist of accepted words. Any query word whose lowercased form is on the allowlist is treated as correctly spelled and never reported, even if it is unknown to every dictionary. Words that are neither on the allowlist nor in any dictionary are still reported. Offsets are UTF-8 byte offsets into the input, ordered by position. The optional field is `"allow":[words...]`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_4_allowlist.json`

```json
{
  "description": "An end-to-end check can be given an allowlist of accepted words; any query word whose lowercased form is on the allowlist is treated as correctly spelled and never reported, even if it is not in any dictionary. Words not on the allowlist and not in any dictionary are still reported. Each reported misspelling is its UTF-8 start byte offset, end byte offset, and text, one per line, ordered by position. The request is {\"op\":\"spellcheck\",\"text\":<text>,\"lang\":\"text\",\"allow\":[words...]}.",
  "cases": [
    {
      "input": {"op": "spellcheck", "lang": "text", "allow": ["testword"], "text": "\n        ok words\n        testword\n        good words\n        actualbad\n"},
      "expected_output": "62 71 actualbad\n"
    }
  ]
}
```

*6.5 Ignore Patterns — user-supplied skip regexes*

An end-to-end check can be given a list of regular expressions. Any word matching one of the supplied patterns is skipped and never reported, in addition to the built-in technical-string patterns. Words that match no pattern and are unknown to the dictionaries are still reported. Offsets are UTF-8 byte offsets into the input, ordered by position. The optional field is `"ignore_patterns":[regexes...]`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_5_ignore_patterns.json`

```json
{
  "description": "An end-to-end check can be given a list of regular expressions; any word matching one of the supplied patterns is skipped and never reported as a misspelling, in addition to the built-in technical-string patterns. Words that match no pattern and are unknown to the dictionaries are still reported. Each reported misspelling is its UTF-8 start byte offset, end byte offset, and text, one per line, ordered by position. The request is {\"op\":\"spellcheck\",\"text\":<text>,\"lang\":\"text\",\"ignore_patterns\":[regexes...]}.",
  "cases": [
    {
      "input": {"op": "spellcheck", "lang": "text", "ignore_patterns": ["^[A-Z]{2,}$", "\\bcustom\\w*", "testpattern"], "text": "\n        This text has HTML and CSS frameworks.\n        Also customword and testpattern should be ignored.\n        But badword and anotherbadword should be flagged.\n    "},
      "expected_output": "119 126 badword\n131 145 anotherbadword\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the features above — identifier splitting, technical-string masking, syntax-aware source-region extraction, dictionary membership and suggestions, and the end-to-end checking pipeline with its configuration layer — with high cohesion and clear module boundaries, free of stdin/stdout/JSON coupling.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core. It reads a single JSON request from stdin, dispatches on the `op` field, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. Invalid or unsupported requests are rendered as a neutral, language-neutral `error=<category>` line (for example `error=unknown_op`, `error=missing_text`); host-language exception identifiers and runtime message fragments must never appear in stdout. This adapter must be logically and physically separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_identifier_splitting.json` under `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_identifier_splitting@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
