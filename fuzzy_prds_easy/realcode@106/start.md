## Product Requirement Document

# Word Shape and Number Inflection Utility - String Naming and Multilingual Word Forms

## Project Goal

Build a string inflection utility that allows developers to convert identifier-like text between common naming shapes and convert words between singular and plural forms across supported languages without hand-writing repetitive casing and grammar rules.

---

## Background & Problem

Without this library/tool, developers are forced to manually split identifiers, manage delimiter-specific capitalization, and maintain language-specific singular/plural lookup and suffix rules. This leads to repetitive code, inconsistent naming, and fragile edge-case handling for irregular or invariant words.

With this library/tool, callers provide a small structured request describing the desired conversion and receive a deterministic text result suitable for use in application naming, schema naming, display transformations, or language-aware word-form conversion.

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

## Core Feature[see french_inflection_rul[see french_inflection_rul[see french_inflection_rules.md for the exact suffix logic].md for the exact suffix logic].md for the exact suffix logic]

### Feature 1: Identifier and Phra[see french_inflection_rul[see french_inflection_rul[see french_inflection_rules.md for the exact suffix logic].md for the exact suffix logic].md for the exact suffix logic]e Ca[see french_inflection_rul[see french_inflection_rul[see french_inflection_rules.md for the exact suffix logic].md for the exact suffix logic].md for the exact suffix logic]e Conversion

**As a developer**, I want to convert identifier-like strings between storage, type, property, and display-oriented shapes, so I can produce consistent names from varied input text.

**Expected Behavior / Usage:**

*1.1 Delimited Storage Names — Convert identifier text into lowercase underscore-separated storage names.*

The input is a JSON object with `feature` set to `case_conversion`, `style` set to `table`, and `text` containing an identifier-like string. The output is exactly one line, `output=<value>`, where `<value>` is the converted lowercase underscore-separated text. Empty input text produces an empty value after `output=`. Existing underscores may remain, camel-case boundaries become underscores, and numeric characters are preserved as part of their surrounding word.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_delimited_table_names.json`

```json
{
    "description": "Convert identifier text to a lowercase underscore-separated storage name without changing numeric characters.",
    "cases": [
        {
            "input": {
                "feature": "case_conversion",
                "style": "table",
                "text": ""
            },
            "expected_output": "output=\n"
        },
        {
            "input": {
                "feature": "case_conversion",
                "style": "table",
                "text": "FooBar"
            },
            "expected_output": "output=foo_bar\n"
        }
    ]
}
```

*1.2 Upper-Initial Identifiers — Convert separated or mixed identifier text into an upper-initial concatenated identifier.*

The input is a JSON object with `feature` set to `case_conversion`, `style` set to `pascal`, and `text` containing words separated by spaces or underscores, or an already mixed-case identifier. The output is exactly one line, `output=<value>`, where `<value>` joins the words with no separators and an uppercase first letter. Empty input text produces an empty value after `output=`. Repeated separators and trailing separators are ignored for the resulting identifier.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_pascal_identifiers.json`

```json
{
    "description": "Convert separated or mixed identifier text to an upper-initial concatenated identifier.",
    "cases": [
        {
            "input": {
                "feature": "case_conversion",
                "style": "pascal",
                "text": ""
            },
            "expected_output": "output=\n"
        },
        {
            "input": {
                "feature": "case_conversion",
                "style": "pascal",
                "text": "foo_bar"
            },
            "expected_output": "output=FooBar\n"
        }
    ]
}
```

*1.3 Lower-Initial Identifiers — Convert separated or mixed identifier text into a lower-initial concatenated identifier.*

The input is a JSON object with `feature` set to `case_conversion`, `style` set to `camel`, and `text` containing words separated by spaces or underscores, or an already mixed-case identifier. The output is exactly one line, `output=<value>`, where `<value>` joins the words with no separators and a lowercase first letter. Empty input text produces an empty value after `output=`. Repeated separators are ignored, and numeric characters stay in place.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_camel_identifiers.json`

```json
{
    "description": "Convert separated or mixed identifier text to a lower-initial concatenated identifier.",
    "cases": [
        {
            "input": {
                "feature": "case_conversion",
                "style": "camel",
                "text": ""
            },
            "expected_output": "output=\n"
        },
        {
            "input": {
                "feature": "case_conversion",
                "style": "camel",
                "text": "foo_bar"
            },
            "expected_output": "output=fooBar\n"
        }
    ]
}
```

*1.4 Delimiter-Based Title Casing — Uppercase word starts after selected delimiters.*

The input is a JSON object with `feature` set to `case_conversion`, `style` set to `title`, `text` containing the phrase to transform, and optionally `delimiters` containing the characters that mark word boundaries. The output is exactly one line, `output=<value>`, where the first character of the text and the first character after each configured delimiter are uppercased while all other characters remain otherwise preserved. When `delimiters` is omitted, hyphen and space boundaries are included; when provided, the supplied delimiter characters define the boundary set.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_title_casing.json`

```json
{
    "description": "Uppercase the first letter of words after configured delimiters while preserving other characters.",
    "cases": [
        {
            "input": {
                "feature": "case_conversion",
                "style": "title",
                "text": "top-o-the-morning to all_of_you!"
            },
            "expected_output": "output=Top-O-The-Morning To All_of_you!\n"
        },
        {
            "input": {
                "feature": "case_conversion",
                "style": "title",
                "text": "top-o-the-morning to all_of_you!",
                "delimiters": "-_ "
            },
            "expected_output": "output=Top-O-The-Morning To All_Of_You!\n"
        }
    ]
}
```

---

### Feature 2: Multilingual Singular and Plural Word Forms

**As a developer**, I want to convert words between singular and plural forms for supported languages, so I can generate grammatically appropriate labels and names without maintaining custom rule tables.

**Expected Behavior / Usage:**

*2.1 English Word Number Inflection — Convert english words between singular and plural forms.*

The input is a JSON object with `feature` set to `number_inflection`, `language` set to `english`, `direction` set to either `plural` or `singular`, and `word` containing one English word or compound expression. The output is exactly one line, `output=<value>`, where `<value>` is the requested number form. The behavior covers empty strings, regular suffix changes, Latin or Greek-derived irregular forms, irregular everyday nouns, compounds with hyphen or underscore separators, case-preserving examples, and words whose singular and plural are identical.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_english_word_number.json`

```json
{
    "description": "Inflect English words between singular and plural forms, including regular nouns, irregular nouns, compounds, and unchanging words.",
    "cases": [
        {
            "input": {
                "feature": "number_inflection",
                "language": "english",
                "direction": "plural",
                "word": ""
            },
            "expected_output": "output=\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "english",
                "direction": "singular",
                "word": ""
            },
            "expected_output": "output=\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "english",
                "direction": "plural",
                "word": "ability"
            },
            "expected_output": "output=abilities\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "english",
                "direction": "singular",
                "word": "abilities"
            },
            "expected_output": "output=ability\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "english",
                "direction": "plural",
                "word": "acceptancecriterion"
            },
            "expected_output": "output=acceptancecriteria\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "english",
                "direction": "singular",
                "word": "acceptancecriteria"
            },
            "expected_output": "output=acceptancecriterion\n"
        }
    ]
}
```

*2.2 French Word Number Inflection — Convert french words between singular and plural forms.*

The input is a JSON object with `feature` set to `number_inflection`, `language` set to `french`, `direction` set to either `plural` or `singular`, and `word` containing a French word. The output is exactly one line, `output=<value>`, where `<value>` is the requested number form. The behavior covers regular final-s addition, special -ou and -au/-eau/-eu outcomes, -al and -ail variants, invariant words, accented text, and common irregular honorific forms.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_french_word_number.json`

```json
{
    "description": "Inflect French words between singular and plural forms, including common suffix rules, invariant forms, and listed irregular forms.",
    "cases": [
        {
            "input": {
                "feature": "number_inflection",
                "language": "french",
                "direction": "plural",
                "word": "ami"
            },
            "expected_output": "output=amis\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "french",
                "direction": "singular",
                "word": "amis"
            },
            "expected_output": "output=ami\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "french",
                "direction": "plural",
                "word": "chien"
            },
            "expected_output": "output=chiens\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "french",
                "direction": "singular",
                "word": "chiens"
            },
            "expected_output": "output=chien\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "french",
                "direction": "plural",
                "word": "fidèle"
            },
            "expected_output": "output=fidèles\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "french",
                "direction": "singular",
                "word": "fidèles"
            },
            "expected_output": "output=fidèle\n"
        }
    ]
}
```

*2.3 Spanish Word Number Inflection — Convert spanish words between singular and plural forms.*

The input is a JSON object with `feature` set to `number_inflection`, `language` set to `spanish`, `direction` set to either `plural` or `singular`, and `word` containing a Spanish word. The output is exactly one line, `output=<value>`, where `<value>` is the requested number form. The behavior covers vowel-final words, consonant-final words, accented vowel endings, z-to-c plural spelling changes, y endings, invariant words, and an irregular article form.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_spanish_word_number.json`

```json
{
    "description": "Inflect Spanish words between singular and plural forms, including accented endings, consonant changes, invariant words, and articles.",
    "cases": [
        {
            "input": {
                "feature": "number_inflection",
                "language": "spanish",
                "direction": "plural",
                "word": "libro"
            },
            "expected_output": "output=libros\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "spanish",
                "direction": "singular",
                "word": "libros"
            },
            "expected_output": "output=libro\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "spanish",
                "direction": "plural",
                "word": "pluma"
            },
            "expected_output": "output=plumas\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "spanish",
                "direction": "singular",
                "word": "plumas"
            },
            "expected_output": "output=pluma\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "spanish",
                "direction": "plural",
                "word": "señora"
            },
            "expected_output": "output=señoras\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "spanish",
                "direction": "singular",
                "word": "señoras"
            },
            "expected_output": "output=señora\n"
        }
    ]
}
```

*2.4 Portuguese Word Number Inflection — Convert portuguese words between singular and plural forms.*

The input is a JSON object with `feature` set to `number_inflection`, `language` set to `portuguese`, `direction` set to either `plural` or `singular`, and `word` containing a Portuguese word. The output is exactly one line, `output=<value>`, where `<value>` is the requested number form. The behavior covers regular vowel-final plurals, consonant-final plurals, accented words, l-ending changes, and multiple observed outcomes for words ending in -ão.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_portuguese_word_number.json`

```json
{
    "description": "Inflect Portuguese words between singular and plural forms, including vowel endings, consonant endings, accented forms, and irregular -ão outcomes.",
    "cases": [
        {
            "input": {
                "feature": "number_inflection",
                "language": "portuguese",
                "direction": "plural",
                "word": "livro"
            },
            "expected_output": "output=livros\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "portuguese",
                "direction": "singular",
                "word": "livros"
            },
            "expected_output": "output=livro\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "portuguese",
                "direction": "plural",
                "word": "radio"
            },
            "expected_output": "output=radios\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "portuguese",
                "direction": "singular",
                "word": "radios"
            },
            "expected_output": "output=radio\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "portuguese",
                "direction": "plural",
                "word": "senhor"
            },
            "expected_output": "output=senhores\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "portuguese",
                "direction": "singular",
                "word": "senhores"
            },
            "expected_output": "output=senhor\n"
        }
    ]
}
```

*2.5 Norwegian Bokmål Word Number Inflection — Convert norwegian bokmål words between singular and plural forms.*

The input is a JSON object with `feature` set to `number_inflection`, `language` set to `norwegian_bokmal`, `direction` set to either `plural` or `singular`, and `word` containing a Norwegian Bokmål word. The output is exactly one line, `output=<value>`, where `<value>` is the requested number form. The behavior covers common -er, -r, and -e plural endings, an alternate plural form, and words whose singular and plural are identical.

**Test Cases:** `rcb_tests/public_test_cases/feature2_5_norwegian_bokmal_word_number.json`

```json
{
    "description": "Inflect Norwegian Bokmål words between singular and plural forms, including regular endings, alternate endings, and invariant nouns.",
    "cases": [
        {
            "input": {
                "feature": "number_inflection",
                "language": "norwegian_bokmal",
                "direction": "plural",
                "word": "dag"
            },
            "expected_output": "output=dager\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "norwegian_bokmal",
                "direction": "singular",
                "word": "dager"
            },
            "expected_output": "output=dag\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "norwegian_bokmal",
                "direction": "plural",
                "word": "fjord"
            },
            "expected_output": "output=fjorder\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "norwegian_bokmal",
                "direction": "singular",
                "word": "fjorder"
            },
            "expected_output": "output=fjord\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "norwegian_bokmal",
                "direction": "plural",
                "word": "hund"
            },
            "expected_output": "output=hunder\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "norwegian_bokmal",
                "direction": "singular",
                "word": "hunder"
            },
            "expected_output": "output=hund\n"
        }
    ]
}
```

*2.6 Turkish Word Number Inflection — Convert turkish words between singular and plural forms.*

The input is a JSON object with `feature` set to `number_inflection`, `language` set to `turkish`, `direction` set to either `plural` or `singular`, and `word` containing a Turkish word. The output is exactly one line, `output=<value>`, where `<value>` is the requested number form. The behavior covers plural suffix selection with vowel harmony and the tested personal pronoun singular/plural pairs.

**Test Cases:** `rcb_tests/public_test_cases/feature2_6_turkish_word_number.json`

```json
{
    "description": "Inflect Turkish words between singular and plural forms, including vowel-harmony plural suffixes and personal pronouns.",
    "cases": [
        {
            "input": {
                "feature": "number_inflection",
                "language": "turkish",
                "direction": "plural",
                "word": "gün"
            },
            "expected_output": "output=günler\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "turkish",
                "direction": "singular",
                "word": "günler"
            },
            "expected_output": "output=gün\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "turkish",
                "direction": "plural",
                "word": "kiraz"
            },
            "expected_output": "output=kirazlar\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "turkish",
                "direction": "singular",
                "word": "kirazlar"
            },
            "expected_output": "output=kiraz\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "turkish",
                "direction": "plural",
                "word": "kitap"
            },
            "expected_output": "output=kitaplar\n"
        },
        {
            "input": {
                "feature": "number_inflection",
                "language": "turkish",
                "direction": "singular",
                "word": "kitaplar"
            },
            "expected_output": "output=kitap\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_delimited_table_names.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_delimited_table_names@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the naming convention used in the pascal_case_utils module
- refer to the vowel_harmony_map for portuguese exceptions
