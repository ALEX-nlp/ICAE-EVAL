## Product Requirement Document

# Text Moderation Pattern Engine - Configurable Matching, Normalization, Censoring, and Phrase Data Contracts

## Project Goal

Build a text moderation pattern engine that allows developers to define phrase patterns, normalize adversarial text, locate prohibited terms, censor matched spans, and manage phrase datasets without writing repetitive parser, matcher, and replacement logic by hand.

---

## Background & Problem

Without this library/tool, developers are forced to hand-roll pattern parsing, Unicode-aware text scanning, normalization for obfuscation, overlapping replacement logic, and metadata bookkeeping. This leads to fragile moderation behavior, inconsistent match positions, repeated boilerplate, and difficult maintenance when new phrases or normalization rules are added.

With this library/tool, developers can describe moderation phrases and transformations declaratively, receive deterministic match payloads, censor exact spans, and attach phrase-level metadata while keeping input/output behavior predictable.

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

### Feature 1: Pattern Syntax Parsing

**As a developer**, I want to parse moderation pattern text into a structured representation, so I can validate phrase definitions and later use them for matching.

**Expected Behavior / Usage:**

The input is an object with a `pattern` string. Ordinary characters become literal nodes with both their text and Unicode code point values. Square brackets mark an optional expression, `?` marks a wildcard, and `|` at the beginning or end sets boundary flags. Escaped special characters are treated as literals. The output is a JSON string containing `boundary_start`, `boundary_end`, and `nodes`. Invalid syntax prints a normalized multi-line error with `error=pattern_syntax`, `line`, `column`, and a domain message; it must not expose host-language exception names.

**Test Cases:** `rcb_tests/public_test_cases/feature1_pattern_parsing.json`

```json
{
  "description": "Pattern text is parsed into boundary flags and literal, optional, or wildcard nodes; invalid syntax returns normalized pattern-syntax errors.",
  "cases": [
    {
      "input": {
        "pattern": "hello [world]"
      },
      "expected_output": "{\"boundary_start\":false,\"boundary_end\":false,\"nodes\":[{\"kind\":\"literal\",\"chars\":\"hello \",\"code_points\":[\"U+0068\",\"U+0065\",\"U+006C\",\"U+006C\",\"U+006F\",\"U+0020\"]},{\"kind\":\"optional\",\"child\":{\"kind\":\"literal\",\"chars\":\"world\",\"code_points\":[\"U+0077\",\"U+006F\",\"U+0072\",\"U+006C\",\"U+0064\"]}}]}"
    },
    {
      "input": {
        "pattern": "[bar]]"
      },
      "expected_output": "error=pattern_syntax\nline=1\ncolumn=6\nmessage=Unexpected ']' with no corresponding '['."
    }
  ]
}
```

---

### Feature 2: Pattern Matching With Whitelisting and Normalization

**As a developer**, I want to scan text with configured phrase patterns, optional whitelisted spans, and optional normalization transforms, so I can identify only the prohibited ranges that remain actionable.

**Expected Behavior / Usage:**

The input provides either ordered `patterns` or explicit `terms` with ids, a `text` string, and optional `whitelist`, `blacklist_transforms`, `whitelist_transforms`, and `sorted` settings. The output is a JSON string with `has_match` and `matches`; every match includes `term_id`, inclusive `start_index`, inclusive `end_index`, and `match_length`. Matching is case-sensitive unless an input transform changes the text. Unicode characters that occupy multiple storage units still report externally visible match positions consistent with the original string. A whitelisted span suppresses a prohibited match only when it completely covers that match after the relevant whitelist normalization.

**Test Cases:** `rcb_tests/public_test_cases/feature2_pattern_matching.json`

```json
{
  "description": "Configured phrase patterns scan input text and report whether any non-whitelisted match exists, with each match showing term id, inclusive start and end indices, and match length.",
  "cases": [
    {
      "input": {
        "patterns": [
          "cool 🌉"
        ],
        "text": "cool cool cool cool 🌉"
      },
      "expected_output": "{\"has_match\":true,\"matches\":[{\"term_id\":0,\"start_index\":15,\"end_index\":21,\"match_length\":6}]}"
    },
    {
      "input": {
        "terms": [
          {
            "id": 1,
            "pattern": "penis"
          }
        ],
        "text": "the pen is mightier than the penis",
        "whitelist": [
          "pen is"
        ],
        "blacklist_transforms": [
          "skip_non_alphabetic"
        ]
      },
      "expected_output": "{\"has_match\":true,\"matches\":[{\"term_id\":1,\"start_index\":29,\"end_index\":33,\"match_length\":5}]}"
    }
  ]
}
```

---

### Feature 3: Text Censoring

**As a developer**, I want to apply replacement strategies to exact match ranges, so I can produce censored text while preserving the rest of the original content.

**Expected Behavior / Usage:**

The input includes `text`, a list of `matches` with term id, inclusive indices, and match length, plus a `strategy`. Supported deterministic strategies include repeating a fixed character, inserting a fixed phrase, keeping the first matched character before replacing the rest, and keeping the last matched character after replacing the rest. Matches are applied in position order. Fully contained or equal duplicate ranges are ignored after the covering range is processed, while partially overlapping ranges are still replaced without duplicating the untouched gap. The output is a single line beginning with `text=` followed by the censored text; validation errors are normalized.

**Test Cases:** `rcb_tests/public_test_cases/feature3_text_censoring.json`

```json
{
  "description": "Text censoring replaces supplied match ranges using the selected replacement strategy while preserving unmatched text and deterministic overlap handling.",
  "cases": [
    {
      "input": {
        "text": "thinking of good test data is hard",
        "matches": [
          {
            "term_id": 0,
            "match_length": 5,
            "start_index": 0,
            "end_index": 4
          },
          {
            "term_id": 0,
            "match_length": 8,
            "start_index": 0,
            "end_index": 7
          }
        ],
        "strategy": {
          "type": "fixed_char",
          "char": "."
        }
      },
      "expected_output": "text=............. of good test data is hard"
    },
    {
      "input": {
        "text": "hello world!",
        "matches": [
          {
            "term_id": -1,
            "match_length": 5,
            "start_index": 6,
            "end_index": 10
          }
        ],
        "strategy": {
          "type": "keep_start",
          "base": {
            "type": "fixed_char",
            "char": "."
          }
        }
      },
      "expected_output": "text=hello w....!"
    }
  ]
}
```

---

### Feature 4: Character Normalization Transforms

**As a developer**, I want to normalize obfuscated characters before matching, so I can detect phrases hidden with leetspeak, confusable symbols, custom equivalent characters, or irrelevant non-alphabetic characters.

**Expected Behavior / Usage:**

The input contains `text` and a `pipeline` of transform steps. Each step is applied left to right to every Unicode code point, and skipped code points are removed from the resulting text. Built-in transform names include ASCII lowercasing, non-alphabetic skipping, leetspeak resolution, and confusable-character resolution; custom remapping maps any character in an equivalence string back to a canonical single character. The output is a JSON string containing normalized `text` and its `code_points`. Invalid custom remap keys are reported with normalized validation errors.

**Test Cases:** `rcb_tests/public_test_cases/feature4_character_transforms.json`

```json
{
  "description": "Character normalization pipelines transform text by lowercasing ASCII, dropping non-lowercase alphabetic characters, resolving leetspeak/confusable characters, and applying custom remaps.",
  "cases": [
    {
      "input": {
        "text": "@$e\\",
        "pipeline": [
          "leet_speak"
        ]
      },
      "expected_output": "{\"text\":\"ase\\\\\",\"code_points\":[\"U+0061\",\"U+0073\",\"U+0065\",\"U+005C\"]}"
    },
    {
      "input": {
        "text": "⓵❌a",
        "pipeline": [
          "confusables"
        ]
      },
      "expected_output": "{\"text\":\"1Xa\",\"code_points\":[\"U+0031\",\"U+0058\",\"U+0061\"]}"
    },
    {
      "input": {
        "text": "bcez",
        "pipeline": [
          {
            "type": "remap_characters",
            "map": {
              "a": "bc"
            }
          }
        ]
      },
      "expected_output": "{\"text\":\"aaez\",\"code_points\":[\"U+0061\",\"U+0061\",\"U+0065\",\"U+007A\"]}"
    }
  ]
}
```

---

### Feature 5: Duplicate Character Collapse

**As a developer**, I want to collapse excessive consecutive duplicate characters using configurable thresholds, so repeated-letter obfuscation can be normalized without losing allowed repetitions.

**Expected Behavior / Usage:**

The input specifies `default_threshold`, optional per-character `custom_thresholds`, and a `sequence` of characters plus optional reset markers. For each character, the output sequence contains the emitted character until its consecutive threshold is exceeded; skipped duplicates are represented as `SKIP`, and reset markers are represented as `RESET`. A different character restarts counting with that character's threshold. The output is a JSON string with an `output` array.

**Test Cases:** `rcb_tests/public_test_cases/feature5_duplicate_collapse.json`

```json
{
  "description": "Duplicate collapse normalization emits repeated characters up to configured thresholds, skips further consecutive duplicates, and restarts counting after a different character or reset.",
  "cases": [
    {
      "input": {
        "default_threshold": 1,
        "custom_thresholds": [
          [
            "a",
            2
          ]
        ],
        "sequence": [
          "a",
          "a",
          "a"
        ]
      },
      "expected_output": "{\"output\":[\"a\",\"a\",\"SKIP\"]}"
    },
    {
      "input": {
        "default_threshold": 1,
        "custom_thresholds": [
          [
            "a",
            2
          ],
          [
            "b",
            3
          ]
        ],
        "sequence": [
          "a",
          "a",
          "a",
          "b",
          "b",
          "b",
          "b"
        ]
      },
      "expected_output": "{\"output\":[\"a\",\"a\",\"SKIP\",\"b\",\"b\",\"b\",\"SKIP\"]}"
    }
  ]
}
```

---

### Feature 6: Phrase Dataset Assembly and Metadata Lookup

**As a developer**, I want to assemble phrase datasets with patterns, whitelisted terms, and phrase metadata, so match results can later be associated with the phrase data that produced them.

**Expected Behavior / Usage:**

The input contains `phrases`, each with `patterns`, optional `whitelist`, and optional `metadata`. Building the dataset assigns sequential ids to every pattern in phrase order and returns `blacklisted_terms` with parsed pattern details plus `whitelisted_terms`. Optional `merge` appends another dataset while preserving ordering, `remove_metadata` filters out phrases with listed metadata values, and `payloads` asks the dataset to attach phrase metadata to match payloads by term id. Unknown ids print `error=unknown_pattern_id` and the requested `id` on separate lines.

**Test Cases:** `rcb_tests/public_test_cases/feature6_phrase_dataset.json`

```json
{
  "description": "Phrase datasets collect patterns, whitelisted terms, and metadata; building assigns sequential pattern ids, merging appends other data, removal filters phrases, and payload lookup attaches phrase metadata.",
  "cases": [
    {
      "input": {
        "phrases": [
          {
            "patterns": [
              "hi",
              "bye"
            ]
          },
          {
            "patterns": [
              "huh",
              "huhu"
            ]
          }
        ]
      },
      "expected_output": "{\"blacklisted_terms\":[{\"id\":0,\"pattern\":{\"boundary_start\":false,\"boundary_end\":false,\"nodes\":[{\"kind\":\"literal\",\"chars\":\"hi\",\"code_points\":[\"U+0068\",\"U+0069\"]}]}},{\"id\":1,\"pattern\":{\"boundary_start\":false,\"boundary_end\":false,\"nodes\":[{\"kind\":\"literal\",\"chars\":\"bye\",\"code_points\":[\"U+0062\",\"U+0079\",\"U+0065\"]}]}},{\"id\":2,\"pattern\":{\"boundary_start\":false,\"boundary_end\":false,\"nodes\":[{\"kind\":\"literal\",\"chars\":\"huh\",\"code_points\":[\"U+0068\",\"U+0075\",\"U+0068\"]}]}},{\"id\":3,\"pattern\":{\"boundary_start\":false,\"boundary_end\":false,\"nodes\":[{\"kind\":\"literal\",\"chars\":\"huhu\",\"code_points\":[\"U+0068\",\"U+0075\",\"U+0068\",\"U+0075\"]}]}}],\"whitelisted_terms\":[]}"
    },
    {
      "input": {
        "phrases": [
          {
            "patterns": [
              "hi",
              "bye"
            ],
            "metadata": "greetings"
          },
          {
            "patterns": [
              "sad",
              "happy"
            ],
            "metadata": "emotion"
          }
        ],
        "payloads": [
          {
            "term_id": 0,
            "start_index": 0,
            "end_index": 0,
            "match_length": 0
          },
          {
            "term_id": 1,
            "start_index": 0,
            "end_index": 0,
            "match_length": 0
          },
          {
            "term_id": 2,
            "start_index": 0,
            "end_index": 0,
            "match_length": 0
          },
          {
            "term_id": 3,
            "start_index": 0,
            "end_index": 0,
            "match_length": 0
          }
        ]
      },
      "expected_output": "{\"blacklisted_terms\":[{\"id\":0,\"pattern\":{\"boundary_start\":false,\"boundary_end\":false,\"nodes\":[{\"kind\":\"literal\",\"chars\":\"hi\",\"code_points\":[\"U+0068\",\"U+0069\"]}]}},{\"id\":1,\"pattern\":{\"boundary_start\":false,\"boundary_end\":false,\"nodes\":[{\"kind\":\"literal\",\"chars\":\"bye\",\"code_points\":[\"U+0062\",\"U+0079\",\"U+0065\"]}]}},{\"id\":2,\"pattern\":{\"boundary_start\":false,\"boundary_end\":false,\"nodes\":[{\"kind\":\"literal\",\"chars\":\"sad\",\"code_points\":[\"U+0073\",\"U+0061\",\"U+0064\"]}]}},{\"id\":3,\"pattern\":{\"boundary_start\":false,\"boundary_end\":false,\"nodes\":[{\"kind\":\"literal\",\"chars\":\"happy\",\"code_points\":[\"U+0068\",\"U+0061\",\"U+0070\",\"U+0070\",\"U+0079\"]}]}}],\"whitelisted_terms\":[],\"payloads\":[{\"term_id\":0,\"start_index\":0,\"end_index\":0,\"match_length\":0,\"phrase_metadata\":\"greetings\"},{\"term_id\":1,\"start_index\":0,\"end_index\":0,\"match_length\":0,\"phrase_metadata\":\"greetings\"},{\"term_id\":2,\"start_index\":0,\"end_index\":0,\"match_length\":0,\"phrase_metadata\":\"emotion\"},{\"term_id\":3,\"start_index\":0,\"end_index\":0,\"match_length\":0,\"phrase_metadata\":\"emotion\"}]}"
    },
    {
      "input": {
        "phrases": [
          {
            "patterns": [
              "hmm."
            ],
            "metadata": "hmm metadata"
          }
        ],
        "payloads": [
          {
            "term_id": 3,
            "start_index": 0,
            "end_index": 0,
            "match_length": 0
          }
        ]
      },
      "expected_output": "error=unknown_pattern_id\nid=3"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- resolve overlaps by processing covering ranges first
- emit characters up to threshold, then emit 'SKIP'
