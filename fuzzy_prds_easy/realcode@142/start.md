## Product Requirement Document

# Source Spell Checker — Dictionary-Driven Misspelling Detection and Correction

## Project Goal

Build a command-line spell-checking engine that scans text files for commonly misspelled words using a fixed dictionary of known misspellings and their corrections, so developers can find and optionally fix typos across a codebase without manually proofreading every file.

---

## Background & Problem

Source trees, comments, and documentation accumulate the same handful of typos over and over (for example writing "abandonned" for "abandoned"). Catching these by eye does not scale, and a general-purpose dictionary spell checker floods the output with false positives on identifiers, jargon, and code.

This tool takes the opposite approach: it ships a curated dictionary that maps each *known misspelling* to its correction, and only reports words that appear in that dictionary. It can scan individual files or whole directory trees, report each finding with its location, optionally rewrite files in place, narrow or widen what counts as a word, ignore chosen words, skip chosen files, and summarize how often each typo occurred.

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

## Execution Contract (How Cases Are Run)

Every test case is one invocation of the engine driven through an execution adapter. The adapter reads a single JSON request object from standard input and prints the resulting report to standard output. The request fields are:

- `files`: a map of file name to file content; the adapter materializes these files in a fresh, empty working directory before the run (names may include subdirectories).
- `args`: the ordered list of command-line arguments to the engine — option flags followed by the target path(s), interpreted relative to that working directory.
- `stdin` (optional): text fed to the engine's standard input.
- `show_files` (optional): a list of file names whose final on-disk content should be emitted after the run (used to observe in-place edits).

The adapter renders a fixed, language-neutral stdout contract:

- Zero or more **finding lines** (and any **summary** block) exactly as the engine prints them.
- One `warning=binary_file` line for each file skipped as binary.
- One `fixed=<name>` line for each file rewritten in place.
- A final `count=<n>` line giving the total number of misspellings found (this is the engine's numeric result; for a fatal configuration error it is a non-zero status).
- For each `show_files` entry, a `file=<name>` line followed by that file's resulting content.

A finding in a file's **content** is printed as `<path>:<line>: <wrong>  ==> <fix>` (note the two spaces before `==>`, with the path relative to the target as the engine encountered it). A finding in a file's **name** is printed as `<path>: <wrong>  ==> <fix>` (no line number). On a fatal configuration error the engine aborts before checking; the adapter emits a neutral `error=<category>` line instead of any report.

---

## Core Features

### Feature 1: Detect And Report Misspellings

**As a developer**, I want each known misspelling in a file reported with its exact location and suggested correction, so I can find and review every typo at a glance.

**Expected Behavior / Usage:**

The engine scans the content of the target file line by line, splitting it into words and looking each word up (case-insensitively) in the misspelling dictionary. For every match it prints one finding line `<path>:<line>: <wrong>  ==> <fix>`, where `<line>` is the one-based line number, in the order the matches are encountered (a word that occurs twice on one line is reported twice). After all findings the adapter prints `count=<n>` with the total number of matches. A file with no dictionary matches, an empty file, and a target path that does not exist each produce no finding lines and `count=0`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_detect_report.json`

```json
{
    "description": "Run the spell checker over the textual content of a single file using default settings and report what it finds. For each detected misspelling the tool emits one report line giving the file name, the one-based line number where the word occurs, the misspelled word, and its suggested correction. After the report lines a summary line states the total number of misspellings found. A file whose content contains no recognised misspellings produces no report lines and a total of zero.",
    "cases": [
        {
            "input": {"files": {"a.txt": "this is a test file\n"}, "args": ["a.txt"]},
            "expected_output": "count=0\n"
        },
        {
            "input": {"files": {"a.txt": "abandonned\n"}, "args": ["a.txt"]},
            "expected_output": "a.txt:1: abandonned  ==> abandoned\ncount=1\n"
        }
    ]
}
```

---

### Feature 2: Preserve Letter Casing In Suggestions

**As a developer**, I want each suggested correction to follow the capitalization of the word it replaces, so a fix dropped into the text reads naturally regardless of how the original was cased.

**Expected Behavior / Usage:**

When a misspelled word is detected, the engine adapts the dictionary's lower-case correction to the casing of the matched word before reporting it: an all-lower-case word yields a lower-case suggestion; a word capitalized only on its first letter yields a title-cased suggestion; an all-upper-case word yields an upper-case suggestion; and a word with any other (mixed) casing falls back to the plain lower-case correction. Each detection is still reported as one `<path>:<line>: <wrong>  ==> <fix>` line, followed by the total count.

**Test Cases:** `rcb_tests/public_test_cases/feature2_case_preserving.json`

```json
{
    "description": "Match the capitalization of each suggested correction to the capitalization of the misspelled word that was found. When the misspelled word is entirely lower case the suggestion is lower case; when it is in title case the suggestion is title-cased; when it is fully upper case the suggestion is upper-cased; and when its capitalization follows no recognised pattern the suggestion falls back to the plain lower-case correction. Each detection is reported as one line giving the file name, the one-based line number, the misspelled word, and the case-matched correction, followed by a count of detections.",
    "cases": [
        {
            "input": {"files": {"a.txt": "abandonned\nAbandonned\nABANDONNED\nAbAnDoNnEd"}, "args": ["a.txt"]},
            "expected_output": "a.txt:1: abandonned  ==> abandoned\na.txt:2: Abandonned  ==> Abandoned\na.txt:3: ABANDONNED  ==> ABANDONED\na.txt:4: AbAnDoNnEd  ==> abandoned\ncount=4\n"
        },
        {
            "input": {"files": {"a.txt": "this has an ACII error"}, "args": ["a.txt"]},
            "expected_output": "a.txt:1: ACII  ==> ASCII\ncount=1\n"
        }
    ]
}
```

---

### Feature 3: Apply And Suppress In-Place Corrections

**As a developer**, I want to optionally rewrite files with their corrections applied and control how chatty the tool is about doing so, so I can auto-fix typos either verbosely or silently.

**Expected Behavior / Usage:**

*3.1 Apply Corrections In Place — rewrite affected files with the write-changes flag*

With the write-changes flag (`-w`) enabled, instead of only reporting, the engine replaces every detected misspelling with its case-matched correction directly in the file. Each rewritten file is announced with a `fixed=<name>` line, the total `count` of remaining misspellings becomes zero (everything detected was fixed), and the resulting file content reflects every applied correction with the original line structure intact. (The `show_files` field is used to observe the rewritten content.)

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_write_changes.json`

```json
{
    "description": "When the write-changes flag is supplied, the tool rewrites each affected file in place, replacing every misspelled word with its case-matched correction instead of only reporting it. Each rewritten file is announced with a neutral notification carrying the file name, the total count of remaining misspellings drops to zero, and the resulting file content reflects every applied correction with the original line structure preserved.",
    "cases": [
        {
            "input": {"files": {"a.txt": "abandonned\nAbandonned\nABANDONNED\nAbAnDoNnEd"}, "args": ["-w", "a.txt"], "show_files": ["a.txt"]},
            "expected_output": "fixed=a.txt\ncount=0\nfile=a.txt\nabandoned\nAbandoned\nABANDONED\nabandoned\n"
        }
    ]
}
```

*3.2 Suppress Notifications Via Quiet Level — silence selected messages with a numeric bitmask*

The quiet-level option (`-q <n>`) is a numeric bitmask that suppresses chosen categories of informational messages. The bit with value 16 governs the per-file fixed notification: when it is set, an in-place rewrite still applies every correction but emits no `fixed=<name>` line; when it is not set, the notification appears. The two scenarios produce identical corrections and identical resulting content, differing only by the presence of the notification line.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_quiet_suppress.json`

```json
{
    "description": "The quiet-level option is a numeric bitmask that suppresses selected categories of informational messages. With the bit that controls fixed-file notifications enabled, rewriting files in place still applies every correction but no longer emits the per-file fixed notification, whereas without that bit the notification is emitted. The two scenarios share identical correction results and identical resulting file content; they differ only in whether the fixed-file notification line is present.",
    "cases": [
        {
            "input": {"files": {"a.txt": "abandonned abandonned\n"}, "args": ["-w", "a.txt"], "show_files": ["a.txt"]},
            "expected_output": "fixed=a.txt\ncount=0\nfile=a.txt\nabandoned abandoned\n"
        },
        {
            "input": {"files": {"a.txt": "abandonned abandonned\n"}, "args": ["-q", "16", "-w", "a.txt"], "show_files": ["a.txt"]},
            "expected_output": "count=0\nfile=a.txt\nabandoned abandoned\n"
        }
    ]
}
```

---

### Feature 4: Summarize Misspelling Frequency

**As a developer**, I want a tally of how often each distinct typo occurred, so I can prioritize the most widespread mistakes.

**Expected Behavior / Usage:**

When the summary option (`-s`/`--summary`) is enabled, the engine prints its normal per-finding report and then appends a summary section: a blank line, a fixed separator line, a `SUMMARY:` heading, and then one line per distinct misspelled word (keyed by its lower-case form, sorted alphabetically) consisting of the word, right-aligned numeric padding, and the number of times it occurred. When nothing was found the section is still printed but lists no words. The total `count` line follows the summary.

**Test Cases:** `rcb_tests/public_test_cases/feature4_summary.json`

```json
{
    "description": "When the summary option is enabled, after the normal per-finding report the tool appends a summary section: a separator line, a SUMMARY heading, and then one line per distinct misspelled word giving the word followed by right-aligned padding and the number of times that word was found, sorted by word. When nothing was found the summary section is present but lists no words. The total-count line follows the summary as usual.",
    "cases": [
        {
            "input": {"files": {"a.txt": ""}, "args": ["--summary", "a.txt"]},
            "expected_output": "\n-------8<-------\nSUMMARY:\n\ncount=0\n"
        },
        {
            "input": {"files": {"a.txt": "abandonned\nabandonned"}, "args": ["--summary", "a.txt"]},
            "expected_output": "a.txt:1: abandonned  ==> abandoned\na.txt:2: abandonned  ==> abandoned\n\n-------8<-------\nSUMMARY:\nabandonned    2\ncount=2\n"
        }
    ]
}
```

---

### Feature 5: Control What Counts As A Misspelling

**As a developer**, I want fine-grained control over which words and lines are checked and how text is split into words, so I can suppress false positives and focus the scan.

**Expected Behavior / Usage:**

*5.1 Ignore Words Given Inline — accept words from a comma-separated list*

The inline ignore-list option (`-L <words>`) names words that must never be reported, given as a comma-separated list. The option may be supplied multiple times and all lists are combined. Words on the combined list are skipped; every other dictionary match is still reported and counted.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_ignore_words_inline.json`

```json
{
    "description": "Words supplied through the inline ignore-list option are treated as acceptable and are never reported as misspellings. The option takes a comma-separated list of words and may be supplied more than once, with all supplied lists combined. With no ignore list every recognised misspelling in the file is reported; when some of those words are placed on the ignore list they are skipped and only the remaining misspellings are reported and counted.",
    "cases": [
        {
            "input": {"files": {"a.txt": "abandonned\nabondon\nabilty\n"}, "args": ["a.txt"]},
            "expected_output": "a.txt:1: abandonned  ==> abandoned\na.txt:2: abondon  ==> abandon\na.txt:3: abilty  ==> ability\ncount=3\n"
        },
        {
            "input": {"files": {"a.txt": "abandonned\nabondon\nabilty\n"}, "args": ["-Labandonned,someword", "-Labilty", "a.txt"]},
            "expected_output": "a.txt:2: abondon  ==> abandon\ncount=1\n"
        }
    ]
}
```

*5.2 Ignore Words From A File — accept words listed one per line in a file*

The ignore-words-file option (`-I <path>`) names a file listing acceptable words, one per line. Words appearing in that file are skipped; all other matches are reported and counted as usual.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_ignore_words_file.json`

```json
{
    "description": "An ignore-words file lists, one word per line, words that must never be reported as misspellings. When the file is supplied, words appearing in it are skipped while all other misspellings in the checked file are still reported and counted; without the ignore file those same words are reported normally.",
    "cases": [
        {
            "input": {"files": {"bad.txt": "abandonned\nabondon\n"}, "args": ["bad.txt"]},
            "expected_output": "bad.txt:1: abandonned  ==> abandoned\nbad.txt:2: abondon  ==> abandon\ncount=2\n"
        },
        {
            "input": {"files": {"bad.txt": "abandonned\nabondon\n", "iw.txt": "abandonned\n"}, "args": ["-I", "iw.txt", "bad.txt"]},
            "expected_output": "bad.txt:2: abondon  ==> abandon\ncount=1\n"
        }
    ]
}
```

*5.3 Custom Word-Matching Pattern — redefine what a word is*

By default words are built from a pattern that treats alphanumeric characters together with the underscore, hyphen and apostrophe as part of a word, so a misspelling joined to surrounding text by an underscore is never isolated and therefore not reported. A custom word-matching regular expression may be supplied (`-r <regex>`) to redefine word boundaries; a pattern that breaks on underscores isolates the embedded misspellings so they are detected.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_custom_word_pattern.json`

```json
{
    "description": "By default the tool builds candidate words using a pattern that treats alphanumeric characters together with the underscore, hyphen and apostrophe as part of a word, so a misspelling joined to other text by an underscore is not isolated and therefore not reported. A custom word-matching regular expression can be supplied to redefine what counts as a word; supplying a pattern that breaks on underscores isolates the embedded misspellings so they are detected.",
    "cases": [
        {
            "input": {"files": {"a.txt": "abandonned_abondon\n"}, "args": ["a.txt"]},
            "expected_output": "count=0\n"
        },
        {
            "input": {"files": {"a.txt": "abandonned_abondon\n"}, "args": ["-r", "[a-z]+", "a.txt"]},
            "expected_output": "a.txt:1: abandonned  ==> abandoned\na.txt:1: abondon  ==> abandon\ncount=2\n"
        }
    ]
}
```

*5.4 Exclude Specific Lines — leave listed whole lines unchecked*

The exclude-file option (`-x <path>`) names a file whose lines are treated as exclusions: any line in the target file whose full text exactly matches an excluded line is skipped entirely, so misspellings on it are not reported. Lines not listed are checked normally.

**Test Cases:** `rcb_tests/public_test_cases/feature5_4_exclude_lines.json`

```json
{
    "description": "An exclude file lists whole lines of text that should be left unchecked. Any line in the target file whose full text exactly matches a line in the exclude file is skipped entirely, so misspellings on that line are not reported; lines that are not listed are checked normally.",
    "cases": [
        {
            "input": {"files": {"bad.txt": "abandonned 1\nabandonned 2\n"}, "args": ["bad.txt"]},
            "expected_output": "bad.txt:1: abandonned  ==> abandoned\nbad.txt:2: abandonned  ==> abandoned\ncount=2\n"
        },
        {
            "input": {"files": {"bad.txt": "abandonned 1\nabandonned 2\n", "ex.txt": "abandonned 1\n"}, "args": ["-x", "ex.txt", "bad.txt"]},
            "expected_output": "bad.txt:2: abandonned  ==> abandoned\ncount=1\n"
        }
    ]
}
```

---

### Feature 6: Select Which Files Are Checked

**As a developer**, I want to control which files in a directory are scanned and whether file names and hidden files participate, so the scan covers exactly what I intend.

**Expected Behavior / Usage:**

*6.1 Skip Files By Pattern — exclude names matching wildcard patterns*

When a directory is checked, the engine walks it and checks each file, printing findings with each file's path relative to the target. The skip option (`--skip <patterns>`) takes a comma-separated list of shell-style wildcard patterns; a file whose name matches any pattern is omitted entirely from the scan and the count.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_skip_patterns.json`

```json
{
    "description": "When a directory is checked, the skip option excludes files whose names match any of a comma-separated list of patterns, where patterns may use shell-style wildcards. A clean file produces no findings; a file containing a misspelling is reported with its path relative to the checked directory unless its name matches a skip pattern, in which case it is omitted entirely.",
    "cases": [
        {
            "input": {"files": {"good.txt": "this file is okay", "bad.txt": "abandonned"}, "args": ["."]},
            "expected_output": "./bad.txt:1: abandonned  ==> abandoned\ncount=1\n"
        },
        {
            "input": {"files": {"good.txt": "this file is okay", "bad.txt": "abandonned"}, "args": ["--skip=bad*", "."]},
            "expected_output": "count=0\n"
        }
    ]
}
```

*6.2 Check File Names — also spell-check the names of files*

By default only file contents are checked. With the check-filenames option (`-f`) enabled, the words making up each file's name are also looked up, and a misspelling in a name is reported on its own line `<path>: <wrong>  ==> <fix>` (no line number, since the match is in the name).

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_check_filenames.json`

```json
{
    "description": "By default only file contents are checked. When the check-filenames option is enabled, the words that make up each file's name are also checked against the correction dictionary, and a misspelling in a file name is reported on its own line giving the file path and the suggested correction (without a line number, since the match is in the name rather than in the content).",
    "cases": [
        {
            "input": {"files": {"abandonned.txt": "."}, "args": ["."]},
            "expected_output": "count=0\n"
        },
        {
            "input": {"files": {"abandonned.txt": "."}, "args": ["-f", "."]},
            "expected_output": "./abandonned.txt: abandonned  ==> abandoned\ncount=1\n"
        }
    ]
}
```

*6.3 Check Hidden Files — include dot-prefixed files*

Files whose name begins with a dot are treated as hidden and skipped by default, so misspellings inside them are not reported. The check-hidden option (`--check-hidden`) makes hidden files participate like any other file; it composes with check-filenames so a hidden file with a misspelled name and misspelled content yields both findings.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_check_hidden.json`

```json
{
    "description": "Files whose name begins with a dot are treated as hidden and are skipped by default, so a misspelling inside such a file is not reported. When the check-hidden option is enabled, hidden files are checked like any other file. The total count reflects everything that was checked.",
    "cases": [
        {
            "input": {"files": {".test.txt": "abandonned\n"}, "args": [".test.txt"]},
            "expected_output": "count=0\n"
        },
        {
            "input": {"files": {".test.txt": "abandonned\n"}, "args": ["--check-hidden", ".test.txt"]},
            "expected_output": ".test.txt:1: abandonned  ==> abandoned\ncount=1\n"
        }
    ]
}
```

---

### Feature 7: Handle Text Encodings And Binary Files

**As a developer**, I want non-ASCII text read correctly and binary files left alone, so accented words are not flagged and binary blobs do not produce garbage.

**Expected Behavior / Usage:**

Text files are decoded as UTF-8 with a Latin-1 fallback, so content with valid accented characters is read correctly and a properly spelled accented word is not flagged, while an ordinary misspelling elsewhere in the same file is still detected. A file is considered binary if it contains a null byte; binary files are skipped without being checked. By default skipping a binary file emits a neutral `warning=binary_file` signal; enabling the quiet bit with value 2 (which governs binary-file messages) suppresses that signal. In every binary case the total count is zero because no content was checked.

**Test Cases:** `rcb_tests/public_test_cases/feature7_encoding_binary.json`

```json
{
    "description": "Text files are decoded as UTF-8 (falling back to Latin-1), so content containing non-ASCII letters is read correctly and a word with valid accented characters is not reported as a misspelling. Files detected as binary (those containing a null byte) are skipped without being spell-checked; by default skipping a binary file emits a neutral binary-file warning, and in every binary case the total count is zero because no content was checked.",
    "cases": [
        {
            "input": {"files": {"a.txt": "na\u00efve\n"}, "args": ["a.txt"]},
            "expected_output": "count=0\n"
        },
        {
            "input": {"files": {"a.txt": "\u0000\u0000naiive\u0000\u0000"}, "args": ["a.txt"]},
            "expected_output": "warning=binary_file\ncount=0\n"
        }
    ]
}
```

---

### Feature 8: Report A Missing Custom Dictionary

**As a developer**, I want a clear, fail-fast error when I point the tool at a dictionary file that does not exist, so a misconfiguration does not silently check nothing.

**Expected Behavior / Usage:**

A custom correction dictionary can be supplied by path (`-D <path>`). If the supplied path does not exist, the run is aborted before any file is checked and the engine reports a neutral configuration error indicating that the dictionary could not be found, instead of producing any spell-check report. The accompanying total is the non-zero error status.

**Test Cases:** `rcb_tests/public_test_cases/feature8_missing_dictionary.json`

```json
{
    "description": "A custom correction dictionary can be supplied by path. When the supplied dictionary path does not exist, the run is aborted before any file is checked and the tool reports a neutral configuration error indicating that the dictionary could not be found, rather than producing any spell-check report. The accompanying total is the non-zero error status.",
    "cases": [
        {
            "input": {"files": {"a.txt": "abandonned\n"}, "args": ["-D", "foo", "a.txt"]},
            "expected_output": "error=dictionary_not_found\ncount=1\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the spell-checking engine described above — dictionary loading, word tokenization, case-matching, in-place fixing, ignore/exclude/skip filtering, summary tallying, encoding/binary handling, and configuration validation — decoupled from standard I/O and JSON parsing. Its physical structure (single-file vs. multi-file) MUST align with the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core engine, logically (and ideally physically) separated from it. It reads a single JSON request from stdin — `files`, `args`, optional `stdin`, optional `show_files` — materializes the files in a fresh working directory, drives the engine with the given arguments, and prints the report to stdout following the Execution Contract above: finding/summary lines verbatim, `warning=binary_file` per skipped binary file, `fixed=<name>` per rewritten file, a final `count=<n>`, and the resulting content of any requested files. A fatal configuration error is rendered as a neutral `error=<category>` line.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- consult the spelling lemma table documentation
- follow the same line comparison strategy as the block exclusion module
