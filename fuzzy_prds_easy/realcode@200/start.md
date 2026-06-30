## Product Requirement Document

# Password Strength Estimator - Black-Box Password Guessability Contracts

## Project Goal
Build a password strength estimation library that allows developers to evaluate passwords, detect guessable structures, and return actionable feedback without hand-writing dictionary, pattern, entropy, and crack-time logic.

---

## Background & Problem
Without this library/tool, developers are forced to manually combine dictionary checks, personal-term checks, keyboard-pattern detection, repeated-character detection, date detection, entropy estimates, and user-facing feedback. This leads to repetitive code, inconsistent scoring, missed weak-password patterns, and confusing password guidance.

With this library/tool, callers submit passwords and optional context terms, then receive deterministic strength summaries, match details, entropy calculations, score categories, and improvement feedback through a stable adapter contract.

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

### Feature 1: Password Strength Evaluation

**As a developer**, I want to evaluate supplied passwords with optional caller context, so I can identify weak choices and present stable strength signals to users.

**Expected Behavior / Usage:**

*1.1 Password Strength Summary — Evaluate a single password and return a deterministic strength summary.*

The input is an object with a `password` value. The output is raw stdout lines in `key=value` form: the normalized password, entropy, crack-time seconds, crack-time display text, score, total match count, and each selected match pattern and token. A missing or null password is treated as the empty password when evaluated.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_password_strength_summary.json`

```json
{
    "description": "Evaluate a password and return its normalized strength summary, crack-time estimate, score, and selected match sequence.",
    "cases": [
        {
            "input": {
                "password": "qwER43@!"
            },
            "expected_output": "password=qwER43@!\nentropy=26.44\ncrack_time=4551.454\ncrack_time_display=3 hours\nscore=1\n[internal constant for max matches — ask the backend team]=1\n[a specific unknown value — ask the architect].pattern=spatial\n[a specific unknown value — ask the architect].token=qwER43@!\n"
        },
        {
            "input": {
                "password": "correcthorsebatterystaple"
            },
            "expected_output": "password=correcthorsebatterystaple\nentropy=45.212\ncrack_time=2037200406.475\ncrack_time_display=65 years\nscore=4\n[internal constant for max matches — ask the backend team]=4\n[a specific unknown value — ask the architect].pattern=dictionary\n[a specific unknown value — ask the architect].token=correct\n[a specific unknown value — ask the architect].pattern=dictionary\n[a specific unknown value — ask the architect].token=horse\n[a specific unknown value — ask the architect].pattern=dictionary\n[a specific unknown value — ask the architect].token=battery\n[a specific unknown value — ask the architect].pattern=dictionary\n[a specific unknown value — ask the architect].token=staple\n"
        }
    ]
}
```

*1.2 Strength With User-Supplied Terms — the input is an object with `password` and `user_terms`.*

The input is an object with `password` and `user_terms`. Only text-like user terms participate in matching; invalid entries are ignored. The output shape is the same strength-summary stdout used by Feature 1.1, so the caller can see whether a supplied term or predictable substitution reduced entropy and score.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_strength_with_user_terms.json`

```json
{
    "description": "Evaluate a password while treating caller-provided personal terms as additional weak dictionary entries for that request.",
    "cases": [
        {
            "input": {
                "password": "✅🐴🔋staple",
                "user_terms": [
                    "✅",
                    "🐴",
                    "🔋"
                ]
            },
            "expected_output": "password=✅🐴🔋staple\nentropy=16.365\ncrack_time=4.22\ncrack_time_display=instant\nscore=0\n[internal constant for max matches — ask the backend team]=4\n[a specific unknown value — ask the architect].pattern=dictionary\n[a specific unknown value — ask the architect].token=✅\n[a specific unknown value — ask the architect].pattern=dictionary\n[a specific unknown value — ask the architect].token=🐴\n[a specific unknown value — ask the architect].pattern=dictionary\n[a specific unknown value — ask the architect].token=🔋\n[a specific unknown value — ask the architect].pattern=dictionary\n[a specific unknown value — ask the architect].token=staple\n"
        },
        {
            "input": {
                "password": "correct horse battery staple",
                "user_terms": [
                    "✅",
                    "🐴",
                    "🔋"
                ]
            },
            "expected_output": "password=correct horse battery staple\nentropy=62.86\ncrack_time=418398182281428.56\ncrack_time_display=centuries\nscore=4\n[internal constant for max matches — ask the backend team]=7\n[a specific unknown value — ask the architect].pattern=dictionary\n[a specific unknown value — ask the architect].token=correct\n[a specific unknown value — ask the architect].pattern=bruteforce\n[a specific unknown value — ask the architect].token= \n[a specific unknown value — ask the architect].pattern=dictionary\n[a specific unknown value — ask the architect].token=horse\n[a specific unknown value — ask the architect].pattern=bruteforce\n[a specific unknown value — ask the architect].token= \nmatch4.pattern=dictionary\nmatch4.token=battery\nmatch5.pattern=bruteforce\nmatch5.token= \nmatch6.pattern=dictionary\nmatch6.token=staple\n"
        }
    ]
}
```

*1.3 Reusable Custom Word Lists — the input is an object with `word_lists`, mapping neutral list names to arrays of entries, and `passwords`, an array of password strings to evaluate after registration.*

The input is an object with `word_lists`, mapping neutral list names to arrays of entries, and `passwords`, an array of password strings to evaluate after registration. Non-text entries in custom lists are ignored. The output contains one strength summary per password, separated by `---`, with each section beginning with the password being evaluated.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_reusable_custom_word_lists.json`

```json
{
    "description": "Evaluate one or more passwords against custom word lists that are registered once and reused across checks.",
    "cases": [
        {
            "input": {
                "word_lists": {
                    "custom": [
                        "words"
                    ]
                },
                "passwords": [
                    "password"
                ]
            },
            "expected_output": "password=password\npassword=password\nentropy=0.0\ncrack_time=0.0\ncrack_time_display=instant\nscore=0\n[internal constant for max matches — ask the backend team]=1\n[a specific unknown value — ask the architect].pattern=dictionary\n[a specific unknown value — ask the architect].token=password\n"
        }
    ]
}
```

---

### Feature 2: Feedback Messages

**As a developer**, I want to receive plain-language warnings and suggestions for weak passwords, so I can explain how to improve weak choices without interpreting internal scores.

**Expected Behavior / Usage:**

The input is an object with `password` and optional `user_terms`. The output always includes `warning=<text-or-none>`, zero or more `suggestion=<text>` lines, and `suggestion_count=<number>`. Strong passwords produce `warning=none` and no suggestion lines; weak passwords produce warning and suggestion text that reflects the dominant weakness, such as common dictionary terms, keyboard rows, repeated characters, sequences, or dates.

**Test Cases:** `rcb_tests/public_test_cases/feature2_feedback_messages.json`

```json
{
    "description": "Return warning and suggestion lines that explain why a tested password is weak or omit feedback when the score is good.",
    "cases": [
        {
            "input": {
                "password": "5815A30BE798"
            },
            "expected_output": "warning=none\nsuggestion_count=0\n"
        },
        {
            "input": {
                "password": "password"
            },
            "expected_output": "warning=This is a top-10 common password\nsuggestion=Add another word or two. Uncommon words are better.\nsuggestion_count=1\n"
        },
        {
            "input": {
                "password": "1qaz"
            },
            "expected_output": "warning=Straight rows of keys are easy to guess\nsuggestion=Add another word or two. Uncommon words are better.\nsuggestion=Use a longer keyboard pattern with more turns\nsuggestion_count=2\n"
        }
    ]
}
```

---

### Feature 3: Password Pattern Detection

**As a developer**, I want to detect human-guessable structures inside passwords, so I can explain and score why those passwords are easier to guess.

**Expected Behavior / Usage:**

*3.1 Dictionary Word Matches — Detect dictionary words and normalized custom-list entries.*

The input is an object with `password` and either `dictionary: "english"` for the built-in English word list or `dictionary: "custom"` plus `words` for a supplied word list. Matching is case-insensitive and returns normalized words. The output begins with `[internal constant for max matches — ask the backend team]`, followed by each match token, matched word, and rank.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_dictionary_word_matches.json`

```json
{
    "description": "Find dictionary terms inside a password and return each matched token, normalized word, and rank.",
    "cases": [
        {
            "input": {
                "dictionary": "custom",
                "words": [
                    "test",
                    "AB10CD"
                ],
                "password": "AB10CD"
            },
            "expected_output": "[internal constant for max matches — ask the backend team]=1\n[a specific unknown value — ask the architect].token=AB10CD\n[a specific unknown value — ask the architect].matched_word=ab10cd\n[a specific unknown value — ask the architect].rank=2\n"
        }
    ]
}
```

*3.2 Leetspeak Dictionary Matches — the input is an object with `password` and a dictionary selector.*

The input is an object with `password` and a dictionary selector. The output begins with `[internal constant for max matches — ask the backend team]`, followed by each observed token, normalized matched word, and the substitution mapping used to recover the word. Only substitutions relevant to the supplied password appear in stdout.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_leetspeak_dictionary_matches.json`

```json
{
    "description": "Find dictionary terms that appear through predictable character substitutions and return the observed token and substitution map.",
    "cases": [
        {
            "input": {
                "dictionary": "english",
                "password": "p@ssword"
            },
            "expected_output": "[internal constant for max matches — ask the backend team]=4\n[a specific unknown value — ask the architect].token=p@s\n[a specific unknown value — ask the architect].matched_word=pas\n[a specific unknown value — ask the architect].sub=@:a\n[a specific unknown value — ask the architect].token=@\n[a specific unknown value — ask the architect].matched_word=a\n[a specific unknown value — ask the architect].sub=@:a\n[a specific unknown value — ask the architect].token=@s\n[a specific unknown value — ask the architect].matched_word=as\n[a specific unknown value — ask the architect].sub=@:a\n[a specific unknown value — ask the architect].token=@ss\n[a specific unknown value — ask the architect].matched_word=ass\n[a specific unknown value — ask the architect].sub=@:a\n"
        }
    ]
}
```

*3.3 Numeric, Year, and Date Matches — the input is an object with `password`.*

The input is an object with `password`. The output begins with `[internal constant for max matches — ask the backend team]`, then emits each detected numeric pattern. Digit and year matches include their token; date matches also include separator, day, month, and year fields. Supported separated date examples use spaces, hyphens, slashes, backslashes, underscores, or periods when the calendar fields are valid.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_numeric_year_date_matches.json`

```json
{
    "description": "Find digit runs, years, and separated calendar dates in a password and return normalized date fields when present.",
    "cases": [
        {
            "input": {
                "password": "testing1239xx9712"
            },
            "expected_output": "[internal constant for max matches — ask the backend team]=2\n[a specific unknown value — ask the architect].pattern=digits\n[a specific unknown value — ask the architect].token=1239\n[a specific unknown value — ask the architect].pattern=digits\n[a specific unknown value — ask the architect].token=9712\n"
        },
        {
            "input": {
                "password": "testing02/12/1997"
            },
            "expected_output": "[internal constant for max matches — ask the backend team]=3\n[a specific unknown value — ask the architect].pattern=date\n[a specific unknown value — ask the architect].token=02/12/1997\n[a specific unknown value — ask the architect].separator=/\n[a specific unknown value — ask the architect].day=2\n[a specific unknown value — ask the architect].month=12\n[a specific unknown value — ask the architect].year=1997\n[a specific unknown value — ask the architect].pattern=digits\n[a specific unknown value — ask the architect].token=1997\n[a specific unknown value — ask the architect].pattern=year\n[a specific unknown value — ask the architect].token=1997\n"
        }
    ]
}
```

*3.4 Repeat, Sequence, and Keyboard Matches — the input is an object with `password`.*

The input is an object with `password`. The output begins with `[internal constant for max matches — ask the backend team]`, then reports each detected repeat, sequence, or keyboard-adjacency match with its pattern and token. Repeats include the repeated character, sequences include direction when available, and keyboard paths include the detected layout and path metadata when available.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_repeat_sequence_keyboard_matches.json`

```json
{
    "description": "Find repeated characters, ascending or descending sequences, and keyboard-adjacency patterns in a password.",
    "cases": [
        {
            "input": {
                "password": "bbbbbtestingaaa"
            },
            "expected_output": "[internal constant for max matches — ask the backend team]=2\n[a specific unknown value — ask the architect].pattern=repeat\n[a specific unknown value — ask the architect].token=bbbbb\n[a specific unknown value — ask the architect].repeated_char=b\n[a specific unknown value — ask the architect].pattern=repeat\n[a specific unknown value — ask the architect].token=aaa\n[a specific unknown value — ask the architect].repeated_char=a\n"
        },
        {
            "input": {
                "password": "abcde87654"
            },
            "expected_output": "[internal constant for max matches — ask the backend team]=7\n[a specific unknown value — ask the architect].pattern=sequence\n[a specific unknown value — ask the architect].token=abcde\n[a specific unknown value — ask the architect].ascending=true\n[a specific unknown value — ask the architect].pattern=spatial\n[a specific unknown value — ask the architect].token=cde\n[a specific unknown value — ask the architect].graph=qwerty\n[a specific unknown value — ask the architect].turns=1\n[a specific unknown value — ask the architect].shifted_count=0\n[a specific unknown value — ask the architect].pattern=sequence\n[a specific unknown value — ask the architect].token=87654\n[a specific unknown value — ask the architect].ascending=false\n[a specific unknown value — ask the architect].pattern=spatial\n[a specific unknown value — ask the architect].token=87654\n[a specific unknown value — ask the architect].graph=dvorak\n[a specific unknown value — ask the architect].turns=1\n[a specific unknown value — ask the architect].shifted_count=0\nmatch4.pattern=spatial\nmatch4.token=87654\nmatch4.graph=qwerty\nmatch4.turns=1\nmatch4.shifted_count=0\nmatch5.pattern=spatial\nmatch5.token=654\nmatch5.graph=keypad\nmatch5.turns=1\nmatch5.shifted_count=0\nmatch6.pattern=spatial\nmatch6.token=654\nmatch6.graph=mac_keypad\nmatch6.turns=1\nmatch6.shifted_count=0\n"
        }
    ]
}
```

---

### Feature 4: Guessability Estimation Calculations

**As a developer**, I want reusable estimate calculations for recognized patterns and brute-force segments, so I can produce consistent password scores and displays.

**Expected Behavior / Usage:**

*4.1 Entropy Estimates for Recognized Patterns — Calculate pattern-specific entropy values from normalized sample attributes.*

The input is an object with `samples`, where each sample has a `kind` such as repeat, sequence, digits, year, date, dictionary, or keyboard and includes the attributes needed for that pattern. The output contains one section per sample, separated by `---`; each section reports `kind` and the calculated `entropy` value.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_entropy_estimates.json`

```json
{
    "description": "Calculate entropy estimates for individual recognized pattern samples using their relevant attributes.",
    "cases": [
        {
            "input": {
                "samples": [
                    {
                        "kind": "repeat",
                        "token": "2222"
                    },
                    {
                        "kind": "digits",
                        "token": "12345678"
                    },
                    {
                        "kind": "date",
                        "year": 2012,
                        "separator": "/"
                    }
                ]
            },
            "expected_output": "kind=repeat\nentropy=5.321928094887363\n---\nkind=digits\nentropy=26.5754247590989\n---\nkind=date\nentropy=17.433976574415976\n"
        }
    ]
}
```

*4.2 Crack-Time Display and Score Categories — the input is an object with `samples`.*

The input is an object with `samples`. A sample with `entropy` returns the derived crack-time seconds. A sample with `seconds` returns the same seconds value, a human-readable display bucket, and a score from 0 through 4. Output sections are separated by `---`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_crack_time_display_and_score.json`

```json
{
    "description": "Convert entropy or crack-time seconds into crack-time seconds, readable display buckets, and score categories.",
    "cases": [
        {
            "input": {
                "samples": [
                    {
                        "entropy": 15.433976574415976
                    },
                    {
                        "seconds": 90
                    },
                    {
                        "seconds": 5000
                    },
                    {
                        "seconds": 110000000
                    }
                ]
            },
            "expected_output": "entropy=15.433976574415976\nseconds=2.2134000000000014\n---\nseconds=90.0\ndisplay=2 minutes\nscore=0\n---\nseconds=5000.0\ndisplay=2 hours\nscore=1\n---\nseconds=110000000.0\ndisplay=4 years\nscore=4\n"
        }
    ]
}
```

*4.3 Brute-Force Cardinality — the input is an object with `passwords`, an array of strings.*

The input is an object with `passwords`, an array of strings. For each password, the output reports the password and the cardinality implied by its characters: empty strings use 0; digits add 10; lowercase letters add 26; uppercase letters add 26; symbols add 33; mixed classes add their component cardinalities.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_bruteforce_cardinality.json`

```json
{
    "description": "Determine the brute-force character-set cardinality implied by the character classes present in a password.",
    "cases": [
        {
            "input": {
                "passwords": [
                    "",
                    "5",
                    "A",
                    "a",
                    "/",
                    "123456789",
                    "p1SsWorD!"
                ]
            },
            "expected_output": "password=\ncardinality=0\n---\npassword=5\ncardinality=10\n---\npassword=A\ncardinality=26\n---\npassword=a\ncardinality=26\n---\npassword=/\ncardinality=33\n---\npassword=123456789\ncardinality=10\n---\npassword=p1SsWorD!\ncardinality=95\n"
        }
    ]
}
```

---

### Feature 5: Keyboard Graph Metrics

**As a developer**, I want to retrieve keyboard-layout graph metrics, so I can support reproducible estimation of keyboard path patterns.

**Expected Behavior / Usage:**

The input is an object with `layouts`, an array of keyboard layout names. For each layout, stdout reports the layout name, average graph degree, and number of starting positions. Supported layouts in the contract include qwerty, dvorak, keypad, and mac keypad variants.

**Test Cases:** `rcb_tests/public_test_cases/feature5_keyboard_graph_metrics.json`

```json
{
    "description": "Return graph metrics used for keyboard-layout pattern estimation for each named keyboard layout.",
    "cases": [
        {
            "input": {
                "layouts": [
                    "qwerty",
                    "keypad"
                ]
            },
            "expected_output": "layout=qwerty\naverage_degree=4.595744680851064\nstarting_positions=94\n---\nlayout=keypad\naverage_degree=5.066666666666666\nstarting_positions=15\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_password_strength_summary.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_password_strength_summary@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- Outputs normalized_password and entropy using the standard validation schema
- match_count defaults to the safe default for non-suspicious input
