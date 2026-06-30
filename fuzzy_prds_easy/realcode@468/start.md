## Product Requirement Document

# Content Utilities Toolkit — Input Parsing, Localized Formatting, Validation, and Collection Ordering

## Project Goal

Build a self-contained library of small, dependency-light utility functions that a content/file-management front end repeatedly needs: parsing user-typed lists of values and email addresses, deciding whether a collaborator is external, turning raw byte counts and large numbers into compact human- and locale-friendly strings, fuzzy-matching search terms, validating network identifiers and email addresses, encoding binary digests, and ordering heterogeneous item collections and activity feeds. The goal is to let application developers reuse one well-tested, predictable implementation of each behavior instead of re-deriving fiddly edge-case logic in every screen.

---

## Background & Problem

Front ends that deal with files, collaborators, and activity streams are full of small but error-prone transformations: a user pastes `"Foo Bar <foo@x.com>; baz@y.com"` into a share box and the app must extract clean addresses; a file is 629644 bytes and must read as `614.9 KB` in English but `614,9 КБ` in Russian; a counter shows 87,654,321 and should display as `88M`; a list mixing folders, files, and links must always show folders first and then sort consistently. Done ad hoc, each of these spawns subtly different behavior across screens, regressions on edge cases (empty input, missing fields, unknown locales), and inconsistent error handling.

This toolkit centralizes those behaviors behind tiny, pure, well-specified functions. Each function has a precise, deterministic input/output contract, handles its edge cases the same way every time, and reports failure through neutral, structured error categories rather than ad hoc exceptions — so callers across the whole product behave identically.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain is a collection of independent, mostly-pure utilities, so each functional point SHOULD live in its own small module with a focused public function, grouped under a utilities namespace/directory. Avoid a single monolithic "god file"; equally, do not over-engineer each one-line helper into a multi-layer subsystem.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in the "Core Features" section define a **black-box contract for an execution adapter**, not the internal signatures of the core functions. The core utilities MUST NOT read stdin, write stdout, or know about JSON. A thin execution/test adapter is solely responsible for decoding a JSON command, calling the relevant core function with idiomatic arguments, and rendering the result (or a normalized error) to stdout.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Keep parsing, formatting, validation, ordering, and output rendering in distinct units.
   - **Open/Closed Principle (OCP):** New locales, units, validators, or sort fields should be addable without rewriting existing functions.
   - **Liskov Substitution Principle (LSP):** Any item kind handled by the ordering logic must be substitutable wherever a generic item is expected.
   - **Interface Segregation Principle (ISP):** Each utility exposes a minimal, cohesive signature; callers depend only on what they use.
   - **Dependency Inversion Principle (DIP):** The adapter depends on the utilities' abstractions, not the other way around.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** Each function's signature must be natural in the target language (a value in, a value/list/boolean out).
   - **Resilience:** Edge cases (null/empty input, missing fields, unknown locale, oversized magnitudes) must be handled deterministically. Failure conditions in the ordering feature must be surfaced as explicit, modeled errors that the adapter renders as neutral category strings — never as leaked host-language runtime details.

5. **Language-Neutral Output Contract:** All rendered output is line-oriented and language-neutral. Lists are rendered as a `count=<n>` header followed by one labeled line per element. Boolean and echo behaviors are rendered as labeled lines (e.g. `valid=true`, `is_external=false`). Failures are rendered as `error=<category>` lines drawn from a fixed vocabulary. No host-language type names, exception classes, stack traces, or object reprs ever reach stdout.

---

## Core Features

### Feature 1: Comma-Separated Value Parsing

**As a developer**, I want to turn a single line of comma-separated text into a clean list of field values, so I can accept pasted or typed lists without writing quote/whitespace handling each time.

**Expected Behavior / Usage:**

The input is a string (or null). The output is the ordered list of fields. Each field is trimmed of surrounding whitespace. A field wrapped in double quotes may itself contain commas and carriage returns, and the matched outer quote pair is removed. A trailing comma or trailing line break does not add an empty field at the end. Null or empty-string input yields an empty list. The rendered output reports the number of fields as `count=<n>` followed by one `item=<value>` line per field in order.

**Test Cases:** `rcb_tests/public_test_cases/feature1_csv_parsing.json`

```json
{
    "description": "Parse comma-separated text into a trimmed list of field values. Surrounding whitespace is stripped; a field wrapped in double quotes may itself contain commas and carriage returns; matched pairs of surrounding double quotes are removed; a trailing comma or line break produces no extra empty field. Null or empty input yields an empty list. The first output line reports the field count, followed by one line per field.",
    "cases": [
        {
            "input": null,
            "expected_output": "count=0"
        },
        {
            "input": "a,b,c,d",
            "expected_output": "count=4\nitem=a\nitem=b\nitem=c\nitem=d"
        },
        {
            "input": " a, b,c, d  ",
            "expected_output": "count=4\nitem=a\nitem=b\nitem=c\nitem=d"
        },
        {
            "input": "a, \"b, c\", d",
            "expected_output": "count=3\nitem=a\nitem=b, c\nitem=d"
        },
        {
            "input": "a\r\nb, c",
            "expected_output": "count=3\nitem=a\nitem=b\nitem=c"
        }
    ]
}
```

---

### Feature 2: Collaborator Email Handling

**As a developer**, I want to pull clean email addresses out of free-form input and decide whether a collaborator is external, so sharing flows can normalize input and flag outside parties consistently.

**Expected Behavior / Usage:**

*2.1 Email Extraction — pull a list of addresses out of a free-form string*

The input is a string (or null) that may contain display names, angle-bracket-wrapped addresses, and addresses separated by spaces, commas, or semicolons. The output is the ordered list of bare email addresses, each trimmed of surrounding whitespace. Null, empty-string, or address-free input yields an empty list. The rendered output reports `count=<n>` followed by one `email=<address>` line per extracted address in order.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_email_extraction.json`

```json
{
    "description": "Extract every email address embedded in a free-form string that may contain display names, angle-bracket contact wrappers, and comma/semicolon/space delimiters. Addresses are returned in order of appearance with surrounding whitespace trimmed. Null or empty input yields an empty list. The first output line reports the count, followed by one line per address.",
    "cases": [
        {
            "input": null,
            "expected_output": "count=0"
        },
        {
            "input": " fbar@example.com ",
            "expected_output": "count=1\nemail=fbar@example.com"
        },
        {
            "input": "fbar@example.com dvader@example.com",
            "expected_output": "count=2\nemail=fbar@example.com\nemail=dvader@example.com"
        },
        {
            "input": "Bar, Foo <fbar@example.com>",
            "expected_output": "count=1\nemail=fbar@example.com"
        },
        {
            "input": "Bar, Foo <fbar@example.com>; Vader, Darth <dvader@example.com>",
            "expected_output": "count=2\nemail=fbar@example.com\nemail=dvader@example.com"
        }
    ]
}
```

*2.2 External Collaborator Check — decide whether a collaborator is outside the owner's domain*

The input is an object with three fields: whether the current viewer owns the item (`isCurrentUserOwner`), the owner's email domain (`ownerEmailDomain`, possibly null), and the collaborator's email address to check (`emailToCheck`, possibly null). The result is true only when the viewer owns the item, an owner domain is present, and the domain portion of the collaborator's address differs from the owner domain. A non-owning viewer, a missing owner domain, or a missing address all yield false. The rendered output echoes the three inputs and the boolean decision as four labeled lines.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_external_collaborator.json`

```json
{
    "description": "Decide whether a collaborator should be flagged as external. The result is true only when the current viewer owns the item, an owner email domain is known, and the collaborator's email domain differs from the owner's. A missing collaborator email, a missing owner domain, or a non-owning viewer all force false. Output echoes the three inputs and the boolean decision.",
    "cases": [
        {
            "input": {
                "isCurrentUserOwner": true,
                "ownerEmailDomain": "box.com",
                "emailToCheck": "narwhal@box.com"
            },
            "expected_output": "is_current_user_owner=true\nowner_email_domain=box.com\nemail_to_check=narwhal@box.com\nis_external=false"
        },
        {
            "input": {
                "isCurrentUserOwner": true,
                "ownerEmailDomain": "boxuielements.com",
                "emailToCheck": "narwhal@box.com"
            },
            "expected_output": "is_current_user_owner=true\nowner_email_domain=boxuielements.com\nemail_to_check=narwhal@box.com\nis_external=true"
        },
        {
            "input": {
                "isCurrentUserOwner": true,
                "ownerEmailDomain": "box.com",
                "emailToCheck": null
            },
            "expected_output": "is_current_user_owner=true\nowner_email_domain=box.com\nemail_to_check=\nis_external=false"
        },
        {
            "input": {
                "isCurrentUserOwner": true,
                "ownerEmailDomain": null,
                "emailToCheck": "narwhal@box.com"
            },
            "expected_output": "is_current_user_owner=true\nowner_email_domain=\nemail_to_check=narwhal@box.com\nis_external=false"
        }
    ]
}
```

---

### Feature 3: Human-Readable Sizes

**As a developer**, I want to turn raw byte counts into compact size strings, so file sizes read naturally for users.

**Expected Behavior / Usage:**

*3.1 Byte Size in Words — short, fixed-unit size string*

The input is a byte count (number) or null (meaning "no argument supplied"). Output is a single string scaling the value by powers of 1024 with up to two decimal places. A falsy or absent size renders the zero placeholder `0 Byte`; `1` renders as `1 Bytes`. The rendered output is exactly that string on one line.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_byte_size_words.json`

```json
{
    "description": "Render a raw byte count as a short human-readable size string using binary (1024) steps and up to two decimal places. A falsy or absent size renders the zero placeholder. A null input represents calling with no argument supplied.",
    "cases": [
        {
            "input": null,
            "expected_output": "0 Byte"
        },
        {
            "input": 0,
            "expected_output": "0 Byte"
        },
        {
            "input": 1,
            "expected_output": "1 Bytes"
        },
        {
            "input": 1024,
            "expected_output": "[a unit-based formatting pattern with example outputs]"
        },
        {
            "input": 1048576,
            "expected_output": "[a unit-based formatting pattern with example outputs]"
        }
    ]
}
```

*3.2 Localized File Size — locale-aware size string*

The input is an object with a byte count (`size`) and an optional `locale` tag. Output is a single string that localizes both the decimal separator and the unit suffix for the given locale; a few locales have dedicated unit symbols while unknown locales fall back to the default symbols with locale-appropriate number formatting. When no locale is supplied the default locale is used. The rendered output is exactly that string on one line.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_localized_file_size.json`

```json
{
    "description": "Format a byte count as a localized human-readable size string. The locale controls both the decimal separator and the unit suffix; a few locales have dedicated unit symbols while unknown locales fall back to default symbols with locale-appropriate number formatting. When no locale is supplied the default locale is used.",
    "cases": [
        {
            "input": {
                "size": 629644
            },
            "expected_output": "614.9 KB"
        },
        {
            "input": {
                "size": 629644,
                "locale": "ru"
            },
            "expected_output": "614,9 КБ"
        },
        {
            "input": {
                "size": 629644,
                "locale": "fr"
            },
            "expected_output": "614,9 Ko"
        },
        {
            "input": {
                "size": 629644,
                "locale": "de"
            },
            "expected_output": "614,9 KB"
        }
    ]
}
```

---

### Feature 4: Number Abbreviation

**As a developer**, I want to abbreviate large counts to a few significant digits, so dashboards and counters stay compact and readable.

**Expected Behavior / Usage:**

Variants 4.1, 4.2, and 4.3 operate in the default English locale; 4.4 takes an explicit locale. Each scalar value is wrapped as `{ "value": <x> }`.

*4.1 Short Form — compact suffix abbreviation*

The value may be a number, a numeric string, a boolean, null, or a plain object. Numbers are abbreviated with a compact magnitude suffix (for example `1K`, `1M`, `1B`, `1T`); magnitudes larger than the largest known bucket reuse the largest bucket with a grouped leading number. Numeric strings are parsed first; booleans count as 1 or 0; null, empty strings, non-numeric strings, and plain objects all collapse to `0`; negative numbers keep their sign. The rendered output is the abbreviated string on one line.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_number_abbreviation_short.json`

```json
{
    "description": "Abbreviate a numeric value to its shortest form, keeping a few significant digits and rounding the rest, in the default English locale. Strings are parsed as numbers; booleans count as 1 or 0; null, empty strings, non-numeric strings, and plain objects collapse to the zero placeholder; negative numbers keep their sign; values beyond the largest defined bucket are expressed as a grouped multiple of that bucket.",
    "cases": [
        {
            "input": {
                "value": 1
            },
            "expected_output": "1"
        },
        {
            "input": {
                "value": 1000
            },
            "expected_output": "1K"
        },
        {
            "input": {
                "value": 1000000
            },
            "expected_output": "1M"
        },
        {
            "input": {
                "value": 1000000000
            },
            "expected_output": "1B"
        },
        {
            "input": {
                "value": 1000000000000000000
            },
            "expected_output": "1,000,000T"
        },
        {
            "input": {
                "value": 12345678
            },
            "expected_output": "12M"
        },
        {
            "input": {
                "value": 87654321
            },
            "expected_output": "88M"
        },
        {
            "input": {
                "value": "3230000"
            },
            "expected_output": "3M"
        },
        {
            "input": {
                "value": "asdf"
            },
            "expected_output": "0"
        },
        {
            "input": {
                "value": false
            },
            "expected_output": "0"
        },
        {
            "input": {
                "value": true
            },
            "expected_output": "1"
        },
        {
            "input": {
                "value": {
                    "foo": 2,
                    "bar": 4
                }
            },
            "expected_output": "0"
        },
        {
            "input": {
                "value": 24734.45674
            },
            "expected_output": "25K"
        },
        {
            "input": {
                "value": -24
            },
            "expected_output": "-24"
        },
        {
            "input": {
                "value": -24567000000
            },
            "expected_output": "-25B"
        }
    ]
}
```

*4.2 Long Form — spelled-out magnitude words*

Same scaling as the short form, but the magnitude is spelled out in full (for example `thousand`, `million`, `billion`, `trillion`); magnitudes beyond the largest known bucket reuse the largest bucket with a grouped leading number. The rendered output is the abbreviated phrase on one line.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_number_abbreviation_long.json`

```json
{
    "description": "Abbreviate a numeric value the same way as the short form but spelling the magnitude word in full (for example the long-form word for the thousands or millions bucket) in the default English locale. Values beyond the largest defined bucket are expressed as a grouped multiple of that bucket plus the long word.",
    "cases": [
        {
            "input": {
                "value": 1
            },
            "expected_output": "1"
        },
        {
            "input": {
                "value": 1000
            },
            "expected_output": "[magnitude terminology for large numbers]"
        },
        {
            "input": {
                "value": 1000000
            },
            "expected_output": "[magnitude terminology for large numbers]"
        },
        {
            "input": {
                "value": 1000000000
            },
            "expected_output": "[magnitude terminology for large numbers]"
        },
        {
            "input": {
                "value": 1000000000000
            },
            "expected_output": "[magnitude terminology for large numbers]"
        },
        {
            "input": {
                "value": 1000000000000000000
            },
            "expected_output": "1,000,000 trillion"
        }
    ]
}
```

*4.3 Batch — abbreviate each element of a list*

When the value is a list, each element is abbreviated independently in short form, preserving order; elements may mix numbers and numeric strings. The rendered output reports `count=<n>` followed by one `value=<abbreviation>` line per element in order.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_number_abbreviation_batch.json`

```json
{
    "description": "Abbreviate every element of a list of values to short form in one call, preserving order. Each element is coerced independently, so a mix of numbers and numeric strings is allowed. The first output line reports the count, followed by one abbreviated value per line.",
    "cases": [
        {
            "input": {
                "value": [
                    34534,
                    333000000,
                    34
                ]
            },
            "expected_output": "count=3\nvalue=35K\nvalue=333M\nvalue=34"
        },
        {
            "input": {
                "value": [
                    34534,
                    "333000000",
                    34
                ]
            },
            "expected_output": "count=3\nvalue=35K\nvalue=333M\nvalue=34"
        }
    ]
}
```

*4.4 Localized — abbreviate using a specific locale's conventions*

The input is an object with a `value`, a `locale` tag, and an optional `length` (`short`, the default, or `long`). The locale governs the grouping separators, the choice and pluralization of the magnitude word, and whether short and long forms differ. The rendered output is the abbreviated string on one line.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_number_abbreviation_localized.json`

```json
{
    "description": "Abbreviate a numeric value using the number-formatting conventions of a specific locale supplied alongside the value. The locale governs grouping separators, the choice and pluralization of the magnitude word, and whether short and long forms differ. The optional length selects the short (default) or long magnitude word.",
    "cases": [
        {
            "input": {
                "value": 1000,
                "locale": "de-DE"
            },
            "expected_output": "1.000"
        },
        {
            "input": {
                "value": 1000000,
                "locale": "de-DE"
            },
            "expected_output": "1 Mio."
        },
        {
            "input": {
                "value": 1000000,
                "locale": "de-DE",
                "length": "long"
            },
            "expected_output": "1 Million"
        },
        {
            "input": {
                "value": 1000,
                "locale": "ru-RU"
            },
            "expected_output": "1 тыс."
        },
        {
            "input": {
                "value": 1000,
                "locale": "ru-RU",
                "length": "long"
            },
            "expected_output": "1 тысяча"
        },
        {
            "input": {
                "value": 2000,
                "locale": "ru-RU",
                "length": "long"
            },
            "expected_output": "2 тысячи"
        },
        {
            "input": {
                "value": 5000,
                "locale": "ru-RU",
                "length": "long"
            },
            "expected_output": "5 тысяч"
        },
        {
            "input": {
                "value": 1000,
                "locale": "ja-JP"
            },
            "expected_output": "1,000"
        },
        {
            "input": {
                "value": 10000,
                "locale": "ja-JP"
            },
            "expected_output": "1万"
        },
        {
            "input": {
                "value": 100000000,
                "locale": "ja-JP"
            },
            "expected_output": "1億"
        }
    ]
}
```

---

### Feature 5: Fuzzy Search Matching

**As a developer**, I want a forgiving substring matcher, so a short query can match longer labels even with gaps and ignored whitespace.

**Expected Behavior / Usage:**

The input is an object with a `search` term, a `content` string, and optional `minCharacters` (default 3) and `maxGaps` (default 2). The result is true only when every character of the search appears in the content in order. Whitespace is ignored in both the search and the content. The search must be at least `minCharacters` long and no longer than the content, otherwise the result is false. Matches split across more than approximately `maxGaps` breaks are rejected, but a single long unbroken streak of matching characters can compensate for additional gaps; both bounds are configurable. Empty content or an empty search yields false. The rendered output echoes the search term, the content, and the boolean decision as three labeled lines.

**Test Cases:** `rcb_tests/public_test_cases/feature5_fuzzy_search.json`

```json
{
    "description": "Report whether a search term fuzzily matches a content string. Every search character must appear in the content in order; whitespace is ignored in both inputs; the term must meet a minimum length (default 3) and stay within an approximate maximum number of gaps (default 2). Both bounds are configurable, and a long unbroken streak of matching characters can compensate for extra gaps. Output echoes the search term, the content, and the boolean decision.",
    "cases": [
        {
            "input": {
                "search": "foo",
                "content": "foo"
            },
            "expected_output": "search=foo\ncontent=foo\nmatched=true"
        },
        {
            "input": {
                "search": "fooo",
                "content": "foo"
            },
            "expected_output": "search=fooo\ncontent=foo\nmatched=false"
        },
        {
            "input": {
                "search": "foo",
                "content": "foo bar"
            },
            "expected_output": "search=foo\ncontent=foo bar\nmatched=true"
        },
        {
            "input": {
                "search": "fo",
                "content": "foo bar"
            },
            "expected_output": "search=fo\ncontent=foo bar\nmatched=false"
        },
        {
            "input": {
                "search": "fo",
                "content": "foo bar",
                "minCharacters": 2
            },
            "expected_output": "search=fo\ncontent=foo bar\nmatched=true"
        },
        {
            "input": {
                "search": "fooimuartles",
                "content": "footimus bartocles"
            },
            "expected_output": "search=fooimuartles\ncontent=footimus bartocles\nmatched=false"
        },
        {
            "input": {
                "search": "fooimuartles",
                "content": "footimus bartocles",
                "minCharacters": 3,
                "maxGaps": 3
            },
            "expected_output": "search=fooimuartles\ncontent=footimus bartocles\nmatched=true"
        },
        {
            "input": {
                "search": "footimusatce",
                "content": "footimus bartocles"
            },
            "expected_output": "search=footimusatce\ncontent=footimus bartocles\nmatched=true"
        },
        {
            "input": {
                "search": "f o o",
                "content": "foo bar"
            },
            "expected_output": "search=f o o\ncontent=foo bar\nmatched=true"
        },
        {
            "input": {
                "search": "foo",
                "content": ""
            },
            "expected_output": "search=foo\ncontent=\nmatched=false"
        },
        {
            "input": {
                "search": "",
                "content": "foo bar"
            },
            "expected_output": "search=\ncontent=foo bar\nmatched=false"
        }
    ]
}
```

---

### Feature 6: Identifier & Email Validation

**As a developer**, I want predicate validators for the common network identifiers and email addresses, so input forms reject malformed values consistently.

**Expected Behavior / Usage:**

Each validator takes a single string and renders two labeled lines: `input=<value>` echoing the input and `valid=true`/`valid=false` reporting the verdict.

*6.1 Domain Name — strict registrable domain*

Accepts a name of at least two dot-separated labels ending in a recognizable top-level label; labels are alphanumeric with internal hyphens only. Rejects leading/trailing hyphens, an embedded `@`, a trailing dot, bare dotted-numeric (IP-like) values, and single labels.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_domain_name_validation.json`

```json
{
    "description": "Validate whether a string is a syntactically valid registrable domain name: at least two dot-separated labels ending in a recognizable top-level label. Leading or trailing hyphens, an embedded at-sign, a trailing dot, bare numeric IP-like values, and single labels are all rejected. Output echoes the input and the boolean verdict.",
    "cases": [
        {
            "input": "a.com",
            "expected_output": "input=a.com\nvalid=true"
        },
        {
            "input": "www.a.com",
            "expected_output": "input=www.a.com\nvalid=true"
        },
        {
            "input": "-a.com",
            "expected_output": "input=-a.com\nvalid=false"
        },
        {
            "input": "a@b.com",
            "expected_output": "input=a@b.com\nvalid=false"
        },
        {
            "input": "1.1.1.1",
            "expected_output": "input=1.1.1.1\nvalid=false"
        },
        {
            "input": "a",
            "expected_output": "input=a\nvalid=false"
        }
    ]
}
```

*6.2 Hostname — general label syntax*

Accepts dot-separated labels of alphanumerics with internal hyphens. Unlike strict domain validation, single labels and dotted-numeric forms are accepted. Rejects leading/trailing hyphens, an embedded `@`, and a trailing dot.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_hostname_validation.json`

```json
{
    "description": "Validate whether a string is a syntactically valid hostname. Unlike a registrable domain name, a single label and dotted numeric values are accepted, but leading or trailing hyphens, an embedded at-sign, and a trailing dot are rejected. Output echoes the input and the boolean verdict.",
    "cases": [
        {
            "input": "a.com",
            "expected_output": "input=a.com\nvalid=true"
        },
        {
            "input": "-a.com",
            "expected_output": "input=-a.com\nvalid=false"
        },
        {
            "input": "www.a.com-",
            "expected_output": "input=www.a.com-\nvalid=false"
        },
        {
            "input": "a@b.com",
            "expected_output": "input=a@b.com\nvalid=false"
        },
        {
            "input": "a.",
            "expected_output": "input=a.\nvalid=false"
        },
        {
            "input": "1.1.1.1",
            "expected_output": "input=1.1.1.1\nvalid=true"
        },
        {
            "input": "1.1.1",
            "expected_output": "input=1.1.1\nvalid=true"
        },
        {
            "input": "a",
            "expected_output": "input=a\nvalid=true"
        }
    ]
}
```

*6.3 IPv4 Address — dotted quad*

Accepts exactly four dot-separated octets, each an integer in the range 0–255. Rejects any octet above 255, fewer or more than four octets, a trailing dot, hostnames, and single labels.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_ipv4_validation.json`

```json
{
    "description": "Validate whether a string is a dotted-quad IPv4 address: exactly four dot-separated octets, each an integer in the range 0 through 255. Any octet above 255, too few or too many octets, a trailing dot, or non-numeric text is rejected. Output echoes the input and the boolean verdict.",
    "cases": [
        {
            "input": "1.1.1.1",
            "expected_output": "input=1.1.1.1\nvalid=true"
        },
        {
            "input": "256.1.1.1",
            "expected_output": "input=256.1.1.1\nvalid=false"
        },
        {
            "input": "1.1.1",
            "expected_output": "input=1.1.1\nvalid=false"
        }
    ]
}
```

*6.4 Email Address — allow-listed TLD*

Accepts a well-formed address whose top-level domain is on a recognized allow-list. Rejects unknown or junk top-level domains, a missing local part or host, consecutive dots, illegal characters in the local part, and bare domain-only values.

**Test Cases:** `rcb_tests/public_test_cases/feature6_4_email_validation.json`

```json
{
    "description": "Validate whether a string is a syntactically valid email address with a recognized top-level domain. A single local part, a dot, and a valid registrable domain are required; double dots, a colon in the local part, an empty local part or domain, unknown top-level domains, and bare IP-like values are rejected. Output echoes the input and the boolean verdict.",
    "cases": [
        {
            "input": "a@b.com",
            "expected_output": "input=a@b.com\nvalid=true"
        },
        {
            "input": "a@b.dfdsfsdffs",
            "expected_output": "input=a@b.dfdsfsdffs\nvalid=false"
        },
        {
            "input": "a@b.design",
            "expected_output": "input=a@b.design\nvalid=true"
        },
        {
            "input": "a@b.co.com",
            "expected_output": "input=a@b.co.com\nvalid=true"
        },
        {
            "input": "a.x@b.com",
            "expected_output": "input=a.x@b.com\nvalid=true"
        },
        {
            "input": "a:x@b.com",
            "expected_output": "input=a:x@b.com\nvalid=false"
        },
        {
            "input": "a..x@b.com",
            "expected_output": "input=a..x@b.com\nvalid=false"
        },
        {
            "input": "@b.com",
            "expected_output": "input=@b.com\nvalid=false"
        },
        {
            "input": "a@.com",
            "expected_output": "input=a@.com\nvalid=false"
        },
        {
            "input": "www.a.com",
            "expected_output": "input=www.a.com\nvalid=false"
        }
    ]
}
```

---

### Feature 7: Hex-to-Base64 Encoding

**As a developer**, I want to convert a hexadecimal digest into Base64, so binary identifiers can be transmitted in a compact text form.

**Expected Behavior / Usage:**

The input is a hexadecimal string where each byte is two hex digits; embedded carriage returns and line breaks are ignored. The output is the standard Base64 encoding obtained by interpreting each hex pair as one byte. The rendered output is exactly the Base64 string on one line.

**Test Cases:** `rcb_tests/public_test_cases/feature7_hex_to_base64.json`

```json
{
    "description": "Convert a hexadecimal byte string into its standard Base64 encoding. Each pair of hex digits is treated as one byte; any carriage returns or line breaks in the input are ignored before encoding.",
    "cases": [
        {
            "input": "12AB34",
            "expected_output": "Eqs0"
        }
    ]
}
```

---

### Feature 8: Collection & Feed Ordering

**As a developer**, I want deterministic ordering for mixed item collections and merged activity feeds, so listings and timelines are stable and predictable.

**Expected Behavior / Usage:**

*8.1 Item Collection Ordering — kind grouping plus field sort*

The input provides a catalog of `items` keyed by id (each item carrying an optional kind `type` of `folder`, `file`, or `web_link`, plus `name`, `modified_at`, `interacted_at`, and `size`), an `entries` list of ids to order, an `order` record of the field+direction the list is currently sorted by, a `sortBy` field (`name`, `modified_at`, `interacted_at`, or `size`), and a `sortDirection` (`ASC` or `DESC`). Items of different kinds are always grouped folders first, then files, then web links. Within the same kind they are ordered by the chosen field; an item missing `interacted_at` falls back to its `modified_at`, an item with no kind is treated as a file, and missing names/sizes are treated as empty/zero. If the collection already records exactly the requested field and direction, the order is returned unchanged. The rendered output reports `count=<n>` followed by one `entry=<id>` line per id in final order.

Failure conditions are surfaced as a neutral error category instead of an ordered list: an unsupported sort field yields `error=unsupported_sort_field` followed by a `field=<value>` line; an item of an unknown kind encountered during comparison yields `error=unsupported_item_type`; a collection whose `entries` is not a list yields `error=invalid_item`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_item_sorting.json`

```json
{
    "description": "Sort a collection of file/folder/link entries in place by a chosen field and direction, looking up each entry's attributes from a provided catalog. Items of different kinds are grouped kind-first (folders, then files, then links) and only items of the same kind are compared by the chosen field (name, last-modified time, last-interacted time, or size); missing attributes fall back to neutral defaults and a comparison is stable when values tie. If the existing recorded order already matches the requested field and direction, the entries are returned untouched. An unknown sort field, an entry whose kind has no defined ordering, and a malformed collection are reported as distinct normalized error categories. The first output line reports the entry count, followed by the sorted entry keys.",
    "cases": [
        {
            "input": {
                "items": {
                    "fo1": {"name": "a", "modified_at": "1", "interacted_at": "1", "size": 10, "type": "folder"},
                    "fo2": {"name": "b", "modified_at": "2", "interacted_at": "3", "size": 20, "type": "folder"},
                    "fo3": {"name": "c", "modified_at": "3", "interacted_at": "2", "size": 5, "type": "folder"},
                    "fo4": {"name": "a", "modified_at": "1", "interacted_at": "1", "size": 50, "type": "folder"},
                    "fo5": {"name": "d", "modified_at": "4", "type": "folder"},
                    "fo6": {"name": "e", "modified_at": "2", "type": "folder"},
                    "f1": {"name": "a", "modified_at": "1", "interacted_at": "1", "size": 100, "type": "file"},
                    "f2": {"name": "b", "modified_at": "2", "interacted_at": "3", "size": 10, "type": "file"},
                    "f3": {"name": "c", "modified_at": "3", "interacted_at": "2", "size": 40, "type": "file"},
                    "f4": {"name": "d", "modified_at": "2"},
                    "f5": {"name": "e", "modified_at": "1"},
                    "f6": {},
                    "f7": {},
                    "w1": {"name": "a", "modified_at": "1", "interacted_at": "4", "size": 50, "type": "web_link"},
                    "w2": {"name": "b", "modified_at": "2", "interacted_at": "2", "size": 20, "type": "web_link"},
                    "w3": {"name": "c", "modified_at": "3", "interacted_at": "1", "size": 70, "type": "web_link"},
                    "w4": {"name": "a", "modified_at": "1", "interacted_at": "3", "size": 80, "type": "web_link"},
                    "foo": {"name": "a", "modified_at": "1", "interacted_at": "1", "size": 10, "type": "bar"}
                },
                "entries": ["fo1", "fo2", "fo3", "f1", "f2", "f3", "w1", "w2", "w3"],
                "order": [{"by": "name", "direction": "ASC"}],
                "sortBy": "name",
                "sortDirection": "ASC"
            },
            "expected_output": "count=9\nentry=fo1\nentry=fo2\nentry=fo3\nentry=f1\nentry=f2\nentry=f3\nentry=w1\nentry=w2\nentry=w3"
        },
        {
            "input": {
                "items": {
                    "fo1": {"name": "a", "modified_at": "1", "interacted_at": "1", "size": 10, "type": "folder"},
                    "fo2": {"name": "b", "modified_at": "2", "interacted_at": "3", "size": 20, "type": "folder"},
                    "fo3": {"name": "c", "modified_at": "3", "interacted_at": "2", "size": 5, "type": "folder"},
                    "fo4": {"name": "a", "modified_at": "1", "interacted_at": "1", "size": 50, "type": "folder"},
                    "fo5": {"name": "d", "modified_at": "4", "type": "folder"},
                    "fo6": {"name": "e", "modified_at": "2", "type": "folder"},
                    "f1": {"name": "a", "modified_at": "1", "interacted_at": "1", "size": 100, "type": "file"},
                    "f2": {"name": "b", "modified_at": "2", "interacted_at": "3", "size": 10, "type": "file"},
                    "f3": {"name": "c", "modified_at": "3", "interacted_at": "2", "size": 40, "type": "file"},
                    "f4": {"name": "d", "modified_at": "2"},
                    "f5": {"name": "e", "modified_at": "1"},
                    "f6": {},
                    "f7": {},
                    "w1": {"name": "a", "modified_at": "1", "interacted_at": "4", "size": 50, "type": "web_link"},
                    "w2": {"name": "b", "modified_at": "2", "interacted_at": "2", "size": 20, "type": "web_link"},
                    "w3": {"name": "c", "modified_at": "3", "interacted_at": "1", "size": 70, "type": "web_link"},
                    "w4": {"name": "a", "modified_at": "1", "interacted_at": "3", "size": 80, "type": "web_link"},
                    "foo": {"name": "a", "modified_at": "1", "interacted_at": "1", "size": 10, "type": "bar"}
                },
                "entries": ["fo3", "fo2", "fo1", "f3", "f2", "f1", "w3", "w2", "w1"],
                "order": [{"by": "name", "direction": "ASC"}],
                "sortBy": "name",
                "sortDirection": "DESC"
            },
            "expected_output": "count=9\nentry=fo3\nentry=fo2\nentry=fo1\nentry=f3\nentry=f2\nentry=f1\nentry=w3\nentry=w2\nentry=w1"
        },
        {
            "input": {
                "items": {
                    "fo1": {"name": "a", "modified_at": "1", "interacted_at": "1", "size": 10, "type": "folder"},
                    "fo2": {"name": "b", "modified_at": "2", "interacted_at": "3", "size": 20, "type": "folder"},
                    "fo3": {"name": "c", "modified_at": "3", "interacted_at": "2", "size": 5, "type": "folder"},
                    "fo4": {"name": "a", "modified_at": "1", "interacted_at": "1", "size": 50, "type": "folder"},
                    "fo5": {"name": "d", "modified_at": "4", "type": "folder"},
                    "fo6": {"name": "e", "modified_at": "2", "type": "folder"},
                    "f1": {"name": "a", "modified_at": "1", "interacted_at": "1", "size": 100, "type": "file"},
                    "f2": {"name": "b", "modified_at": "2", "interacted_at": "3", "size": 10, "type": "file"},
                    "f3": {"name": "c", "modified_at": "3", "interacted_at": "2", "size": 40, "type": "file"},
                    "f4": {"name": "d", "modified_at": "2"},
                    "f5": {"name": "e", "modified_at": "1"},
                    "f6": {},
                    "f7": {},
                    "w1": {"name": "a", "modified_at": "1", "interacted_at": "4", "size": 50, "type": "web_link"},
                    "w2": {"name": "b", "modified_at": "2", "interacted_at": "2", "size": 20, "type": "web_link"},
                    "w3": {"name": "c", "modified_at": "3", "interacted_at": "1", "size": 70, "type": "web_link"},
                    "w4": {"name": "a", "modified_at": "1", "interacted_at": "3", "size": 80, "type": "web_link"},
                    "foo": {"name": "a", "modified_at": "1", "interacted_at": "1", "size": 10, "type": "bar"}
                },
                "entries": ["fo3", "fo1", "fo2", "fo4", "f2", "f3", "f1", "w2", "w1", "w3", "w4"],
                "order": [{"by": "name", "direction": "ASC"}],
                "sortBy": "size",
                "sortDirection": "ASC"
            },
            "expected_output": "count=11\nentry=fo3\nentry=fo1\nentry=fo2\nentry=fo4\nentry=f2\nentry=f3\nentry=f1\nentry=w2\nentry=w1\nentry=w3\nentry=w4"
        },
        {
            "input": {
                "items": {
                    "fo1": {"name": "a", "modified_at": "1", "interacted_at": "1", "size": 10, "type": "folder"},
                    "fo2": {"name": "b", "modified_at": "2", "interacted_at": "3", "size": 20, "type": "folder"},
                    "fo3": {"name": "c", "modified_at": "3", "interacted_at": "2", "size": 5, "type": "folder"},
                    "fo4": {"name": "a", "modified_at": "1", "interacted_at": "1", "size": 50, "type": "folder"},
                    "fo5": {"name": "d", "modified_at": "4", "type": "folder"},
                    "fo6": {"name": "e", "modified_at": "2", "type": "folder"},
                    "f1": {"name": "a", "modified_at": "1", "interacted_at": "1", "size": 100, "type": "file"},
                    "f2": {"name": "b", "modified_at": "2", "interacted_at": "3", "size": 10, "type": "file"},
                    "f3": {"name": "c", "modified_at": "3", "interacted_at": "2", "size": 40, "type": "file"},
                    "f4": {"name": "d", "modified_at": "2"},
                    "f5": {"name": "e", "modified_at": "1"},
                    "f6": {},
                    "f7": {},
                    "w1": {"name": "a", "modified_at": "1", "interacted_at": "4", "size": 50, "type": "web_link"},
                    "w2": {"name": "b", "modified_at": "2", "interacted_at": "2", "size": 20, "type": "web_link"},
                    "w3": {"name": "c", "modified_at": "3", "interacted_at": "1", "size": 70, "type": "web_link"},
                    "w4": {"name": "a", "modified_at": "1", "interacted_at": "3", "size": 80, "type": "web_link"},
                    "foo": {"name": "a", "modified_at": "1", "interacted_at": "1", "size": 10, "type": "bar"}
                },
                "entries": ["w1", "w3", "fo1", "fo4", "f1", "w2", "w4", "f3", "f2", "fo2", "fo3"],
                "order": [{"by": "name", "direction": "DESC"}],
                "sortBy": "foobar",
                "sortDirection": "ASC"
            },
            "expected_output": "error=unsupported_sort_field\nfield=foobar"
        },
        {
            "input": {
                "items": {
                    "fo1": {"name": "a", "modified_at": "1", "interacted_at": "1", "size": 10, "type": "folder"},
                    "fo2": {"name": "b", "modified_at": "2", "interacted_at": "3", "size": 20, "type": "folder"},
                    "fo3": {"name": "c", "modified_at": "3", "interacted_at": "2", "size": 5, "type": "folder"},
                    "fo4": {"name": "a", "modified_at": "1", "interacted_at": "1", "size": 50, "type": "folder"},
                    "fo5": {"name": "d", "modified_at": "4", "type": "folder"},
                    "fo6": {"name": "e", "modified_at": "2", "type": "folder"},
                    "f1": {"name": "a", "modified_at": "1", "interacted_at": "1", "size": 100, "type": "file"},
                    "f2": {"name": "b", "modified_at": "2", "interacted_at": "3", "size": 10, "type": "file"},
                    "f3": {"name": "c", "modified_at": "3", "interacted_at": "2", "size": 40, "type": "file"},
                    "f4": {"name": "d", "modified_at": "2"},
                    "f5": {"name": "e", "modified_at": "1"},
                    "f6": {},
                    "f7": {},
                    "w1": {"name": "a", "modified_at": "1", "interacted_at": "4", "size": 50, "type": "web_link"},
                    "w2": {"name": "b", "modified_at": "2", "interacted_at": "2", "size": 20, "type": "web_link"},
                    "w3": {"name": "c", "modified_at": "3", "interacted_at": "1", "size": 70, "type": "web_link"},
                    "w4": {"name": "a", "modified_at": "1", "interacted_at": "3", "size": 80, "type": "web_link"},
                    "foo": {"name": "a", "modified_at": "1", "interacted_at": "1", "size": 10, "type": "bar"}
                },
                "entries": ["w1", "w3", "fo1", "foo"],
                "order": [{"by": "name", "direction": "DESC"}],
                "sortBy": "name",
                "sortDirection": "ASC"
            },
            "expected_output": "error=unsupported_item_type"
        },
        {
            "input": {
                "items": {
                    "fo1": {"name": "a", "modified_at": "1", "interacted_at": "1", "size": 10, "type": "folder"},
                    "fo2": {"name": "b", "modified_at": "2", "interacted_at": "3", "size": 20, "type": "folder"},
                    "fo3": {"name": "c", "modified_at": "3", "interacted_at": "2", "size": 5, "type": "folder"},
                    "fo4": {"name": "a", "modified_at": "1", "interacted_at": "1", "size": 50, "type": "folder"},
                    "fo5": {"name": "d", "modified_at": "4", "type": "folder"},
                    "fo6": {"name": "e", "modified_at": "2", "type": "folder"},
                    "f1": {"name": "a", "modified_at": "1", "interacted_at": "1", "size": 100, "type": "file"},
                    "f2": {"name": "b", "modified_at": "2", "interacted_at": "3", "size": 10, "type": "file"},
                    "f3": {"name": "c", "modified_at": "3", "interacted_at": "2", "size": 40, "type": "file"},
                    "f4": {"name": "d", "modified_at": "2"},
                    "f5": {"name": "e", "modified_at": "1"},
                    "f6": {},
                    "f7": {},
                    "w1": {"name": "a", "modified_at": "1", "interacted_at": "4", "size": 50, "type": "web_link"},
                    "w2": {"name": "b", "modified_at": "2", "interacted_at": "2", "size": 20, "type": "web_link"},
                    "w3": {"name": "c", "modified_at": "3", "interacted_at": "1", "size": 70, "type": "web_link"},
                    "w4": {"name": "a", "modified_at": "1", "interacted_at": "3", "size": 80, "type": "web_link"},
                    "foo": {"name": "a", "modified_at": "1", "interacted_at": "1", "size": 10, "type": "bar"}
                },
                "entries": null,
                "sortBy": "name",
                "sortDirection": "ASC"
            },
            "expected_output": "error=invalid_item"
        }
    ]
}
```

*8.2 Activity Feed Ordering — merge and order by creation time*

The input provides a list of `containers`, each either absent (null) or carrying a list of `entries`, where every entry has an `id` and a creation timestamp (`created_at`). All entries from the present containers are merged into one feed and ordered ascending by creation timestamp; absent containers are skipped entirely. The rendered output reports `count=<n>` followed by one `id=<id>` line per entry in final order.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_activity_feed_ordering.json`

```json
{
    "description": "Merge several containers of activity items into a single feed sorted ascending by creation timestamp. Each container exposes a list of entries; a null container is skipped entirely. The first output line reports the merged count, followed by each entry id in chronological order.",
    "cases": [
        {
            "input": {
                "containers": [
                    {
                        "entries": [
                            {
                                "id": "comment_1",
                                "created_at": "2020-03-01T10:00:00Z"
                            }
                        ]
                    },
                    {
                        "entries": [
                            {
                                "id": "task_1",
                                "created_at": "2020-01-15T10:00:00Z"
                            }
                        ]
                    },
                    {
                        "entries": [
                            {
                                "id": "annotation_1",
                                "created_at": "2020-02-10T10:00:00Z"
                            }
                        ]
                    }
                ]
            },
            "expected_output": "count=3\nid=task_1\nid=annotation_1\nid=comment_1"
        },
        {
            "input": {
                "containers": [
                    {
                        "entries": [
                            {
                                "id": "b",
                                "created_at": "2021-05-05T00:00:00Z"
                            }
                        ]
                    },
                    null,
                    {
                        "entries": [
                            {
                                "id": "a",
                                "created_at": "2020-05-05T00:00:00Z"
                            }
                        ]
                    }
                ]
            },
            "expected_output": "count=2\nid=a\nid=b"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured set of small utility modules implementing the features above — input parsing (CSV, emails), external-collaborator detection, human-readable and localized size formatting, number abbreviation, fuzzy search, identifier/email validation, hex-to-Base64 encoding, and collection/feed ordering — each with a focused, idiomatic public function and deterministic edge-case handling. Physical structure must follow the "Scale-Driven Code Organization" constraint (one small module per functional point under a utilities namespace; no monolith, no over-engineering).

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core utilities. It reads a JSON command (`{ "feature": <key>, "input": <value|object|array> }`) from stdin, invokes the matching core function with idiomatic arguments, and prints the rendered, language-neutral result to stdout, matching the per-leaf-feature contracts above. The adapter owns all output formatting and error normalization (mapping native failures to neutral `error=<category>` lines); it must be logically and physically separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_csv_parsing.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_csv_parsing@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the fail-safe return value for non-numeric inputs
