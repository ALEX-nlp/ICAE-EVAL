## Product Requirement Document

# Synthetic Data Generator - Deterministic Development Data Contracts

## Project Goal

Build a synthetic data generation library that allows developers to create realistic names, internet identifiers, numbers, dates, addresses, commerce data, financial identifiers, and structured sample payloads without hand-authoring repetitive fixture values.

---

## Background & Problem

Without this library, developers are forced to manually invent test data for forms, APIs, documents, and examples. This leads to brittle fixtures, repetitive boilerplate, unrealistic values, and maintenance overhead when formats change.

With this library, developers can request domain-specific generated values through a clean interface and can seed generation when stable, reproducible output is needed.

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

### Feature 1: Person Name Generation

**As a developer**, I want to request a full human name on demand, so I can fill out forms and example records without inventing names by hand.

**Expected Behavior / Usage:**

The adapter accepts a random seed and returns a generated full person name plus the number of whitespace-separated name parts. The name must be human-readable text and the part count must reflect the rendered name.

**Test Cases:** `rcb_tests/public_test_cases/feature1_person_name.json`

```json
{
    "description": "Generate a complete human name from the default person-name data set using a deterministic random seed.",
    "cases": [
        {
            "input": {
                "seed": 101
            },
            "expected_output": "name=Art Sipes\nword_count=2\n"
        }
    ]
}
```

---

### Feature 2: Initial Generation

**As a developer**, I want to produce a fixed number of uppercase initials, so I can build avatar placeholders and short labels deterministically.

**Expected Behavior / Usage:**

The adapter accepts a random seed and an initials count, then returns exactly that many uppercase letters and their length.

**Test Cases:** `rcb_tests/public_test_cases/feature2_person_initials.json`

```json
{
    "description": "Generate uppercase initials where the caller controls the number of letters.",
    "cases": [
        {
            "input": {
                "seed": 303,
                "count": 3
            },
            "expected_output": "initials=SBE\nlength=3\n"
        }
    ]
}
```

---

### Feature 3: Username Generation

**As a developer**, I want to derive lowercase usernames from names or length constraints, so I can seed account fixtures that satisfy field limits.

**Expected Behavior / Usage:**

The adapter accepts either source name text or length constraints and returns a lowercase username. When source text is supplied, words are normalized and joined with an allowed separator; when length bounds are supplied, the rendered username length must satisfy those bounds.

**Test Cases:** `rcb_tests/public_test_cases/feature3_username.json`

```json
{
    "description": "Create a lowercase internet username from caller-provided name text or length constraints.",
    "cases": [
        {
            "input": {
                "seed": 505,
                "source_text": "bo peep"
            },
            "expected_output": "username=bo.peep\nlength=7\n"
        }
    ]
}
```

---

### Feature 4: Password Generation

**As a developer**, I want to generate passwords within length bounds with optional case and symbols, so I can populate credentials that match policy rules.

**Expected Behavior / Usage:**

The adapter accepts minimum and maximum lengths plus flags for uppercase letters and special symbols. It returns the password, its length, and explicit signals showing whether uppercase letters and symbol characters are present.

**Test Cases:** `rcb_tests/public_test_cases/feature4_password.json`

```json
{
    "description": "Generate a password within requested length bounds with optional uppercase letters and symbols.",
    "cases": [
        {
            "input": {
                "seed": 601,
                "min_length": 8,
                "max_length": 12,
                "mixed_case": true,
                "special_chars": true
            },
            "expected_output": "password=^##$&#2oL\nlength=9\ncontains_uppercase=true\n[a specific sentinel value — ask the PM for the exact string]=true\n"
        }
    ]
}
```

---

### Feature 5: Network Address Generation

**As a developer**, I want to fabricate network addressing values such as IPs, MACs, UUIDs, and user-agent strings, so I can exercise networking code without real hosts.

**Expected Behavior / Usage:**

The adapter returns generated IPv4 values, private and public IPv4 values, a CIDR prefix, a MAC address honoring any supplied prefix, a version-4 UUID, and a user-agent family signal for the requested family or fallback behavior.

**Test Cases:** `rcb_tests/public_test_cases/feature5_network_addresses.json`

```json
{
    "description": "Generate internet addressing values including IPv4, CIDR, MAC, UUID, and user-agent strings.",
    "cases": [
        {
            "input": {
                "seed": 701,
                "mac_prefix": "fa:fa:fa",
                "user_agent_family": "opera"
            },
            "expected_output": "ipv4=230.84.212.229\nipv4_octets=4\nprivate_ipv4=127.243.248.112\npublic_ipv4=157.173.202.142\ncidr4_prefix=5\nmac_address=fa:fa:fa:fc:49:38\nuuid=ea62efb7-d69c-4742-adf8-adc0670705ab\nuuid_length=36\nuser_agent_family_signal=Opera\n"
        }
    ]
}
```

---

### Feature 6: Slug and URL Formatting

**As a developer**, I want to turn free text into a slug and assemble URLs from parts, so I can build link fixtures that mirror production routing.

**Expected Behavior / Usage:**

The adapter accepts free-form content, a glue string, a domain, a path, and a scheme. It returns a lowercased slug with punctuation removed and words joined by the glue, plus the complete URL assembled from the supplied parts.

**Test Cases:** `rcb_tests/public_test_cases/feature6_slug_and_url.json`

```json
{
    "description": "Normalize text into a URL slug and assemble a URL from scheme, domain, and path inputs.",
    "cases": [
        {
            "input": {
                "seed": 801,
                "content": "Foo.. bAr., baZ,,",
                "glue": "-",
                "domain": "domain.com",
                "path": "/username",
                "scheme": "https"
            },
            "expected_output": "slug=foo-bar-baz\nurl=https://domain.com/username\n"
        }
    ]
}
```

---

### Feature 7: Fixed-Length Number Generation

**As a developer**, I want to generate numeric strings of an exact digit count, so I can create identifiers and codes of a known width.

**Expected Behavior / Usage:**

The adapter accepts a requested digit count and returns a numeric value rendered as stdout plus its rendered length. A zero digit request returns a null value and length zero.

**Test Cases:** `rcb_tests/public_test_cases/feature7_fixed_length_number.json`

```json
{
    "description": "Generate numeric strings with requested digit counts, including the zero-digit nil case.",
    "cases": [
        {
            "input": {
                "seed": 901,
                "digits": 10
            },
            "expected_output": "number=6603196585\nlength=10\n"
        }
    ]
}
```

---

### Feature 8: Numeric Range Generation

**As a developer**, I want to draw numbers from inclusive ranges with optional sign forcing, so I can bound generated quantities precisely.

**Expected Behavior / Usage:**

The adapter accepts numeric bounds and returns a value inside the effective inclusive range. Positive and negative modes force the sign even when the supplied bounds have the opposite sign; reversed bounds are normalized before generation.

**Test Cases:** `rcb_tests/public_test_cases/feature8_numeric_ranges.json`

```json
{
    "description": "Generate numbers constrained to inclusive, sign-forced, and reordered numeric bounds.",
    "cases": [
        {
            "input": {
                "seed": 1001,
                "min": -50,
                "max": 50
            },
            "expected_output": "between=-41\n"
        }
    ]
}
```

---

### Feature 9: Date Range Exclusion

**As a developer**, I want to pick a date within a range while excluding one date, so I can build scheduling fixtures that avoid a reserved day.

**Expected Behavior / Usage:**

The adapter accepts start, end, and excluded dates in ISO format. It returns a generated ISO date in the range that is not equal to the excluded date, and echoes the excluded date as a verification signal.

**Test Cases:** `rcb_tests/public_test_cases/feature9_date_between_except.json`

```json
{
    "description": "Generate a date inside a range while excluding a specified date.",
    "cases": [
        {
            "input": {
                "seed": 1101,
                "from": "2012-01-01",
                "to": "2012-01-05",
                "except": "2012-01-03"
            },
            "expected_output": "date=2012-01-04\nexcluded=2012-01-03\n"
        }
    ]
}
```

---

### Feature 10: Placeholder Text Counts

**As a developer**, I want to generate placeholder text sized by exact counts, ranges, or choice lists, so I can fill layouts with body copy of controlled length.

**Expected Behavior / Usage:**

The adapter accepts exact counts, inclusive ranges, or choice lists for characters, words, sentences, and paragraphs. It returns generated placeholder text and explicit count or length lines for each requested collection type.

**Test Cases:** `rcb_tests/public_test_cases/feature10_lorem_counts.json`

```json
{
    "description": "Generate placeholder text collections whose lengths follow exact, range, or choice-list count inputs.",
    "cases": [
        {
            "input": {
                "seed": 1201,
                "characters": 5,
                "words": 3,
                "sentences": 2,
                "paragraphs": 1
            },
            "expected_output": "characters=5jd4c\ncharacters_length=5\nwords=et|in|eligendi\nwords_count=3\nsentences_count=2\nparagraphs_count=1\n"
        }
    ]
}
```

---

### Feature 11: Color Value Generation

**As a developer**, I want to obtain colors as names, hex, RGB, HSL, and HSLA values, so I can seed theming and design fixtures.

**Expected Behavior / Usage:**

The adapter accepts a random seed and returns a color name, a hex color string, one RGB channel, a three-channel RGB value, a three-component HSL value, and a four-component HSLA value.

**Test Cases:** `rcb_tests/public_test_cases/feature11_color_values.json`

```json
{
    "description": "Generate color values as names, hex strings, RGB arrays, HSL arrays, and HSLA arrays.",
    "cases": [
        {
            "input": {
                "seed": 1301
            },
            "expected_output": "name=white\nhex=#c9e49d\nsingle_rgb=59\nrgb=171,110,180\nhsl=337,0.57,0.8\nhsla=17,0.67,0.83,0.9\n"
        }
    ]
}
```

---

### Feature 12: Commerce Department Labels

**As a developer**, I want to compose multi-category department labels, so I can seed retail catalog fixtures with realistic groupings.

**Expected Behavior / Usage:**

The adapter accepts a category count and a fixed-or-random amount flag. It returns a department label joined with comma and ampersand separators, plus the number of categories and number of unique categories in the rendered label.

**Test Cases:** `rcb_tests/public_test_cases/feature12_commerce_department.json`

```json
{
    "description": "Generate commerce department labels with caller-controlled category counts and separators.",
    "cases": [
        {
            "input": {
                "seed": 1401,
                "category_count": 2,
                "fixed_amount": true
            },
            "expected_output": "department=Music & Baby\ncategory_count=2\nunique_categories=2\n"
        }
    ]
}
```

---

### Feature 13: Commerce Price Generation

**As a developer**, I want to generate prices in a range as a number or formatted string, so I can populate catalog and checkout fixtures.

**Expected Behavior / Usage:**

The adapter accepts an optional numeric price range and an optional string-rendering flag. It returns a generated price and a render-type line indicating whether stdout represents the price as a number or string.

**Test Cases:** `rcb_tests/public_test_cases/feature13_commerce_price.json`

```json
{
    "description": "Generate a commerce price within default or supplied ranges and optionally render it as a string.",
    "cases": [
        {
            "input": {
                "seed": 12345
            },
            "expected_output": "price=98.0\nrender_type=number\n"
        }
    ]
}
```

---

### Feature 14: Postal Address Values

**As a developer**, I want to generate postal address components and look up country codes and names, so I can seed location fixtures and validate lookups.

**Expected Behavior / Usage:**

The adapter accepts lookup inputs for a country code and a country-name key. It returns generated city, street, postal code, state abbreviation, lookup results, latitude, and longitude.

**Test Cases:** `rcb_tests/public_test_cases/feature14_address_values.json`

```json
{
    "description": "Generate postal address components and perform country code/name lookups.",
    "cases": [
        {
            "input": {
                "seed": 1601,
                "country_code": "NL",
                "country_name_key": "united_states"
            },
            "expected_output": "city=South Luisview\nstreet_address=44624 Roxy Extension\nzip_code=76964-6720\nstate_abbr=KY\ncountry_by_code=Netherlands\ncountry_code_by_name=US\nlatitude=-4.8283402654011525\nlongitude=2.059025084542867\n"
        }
    ]
}
```

---

### Feature 15: Banking Identifiers

**As a developer**, I want to generate account numbers and country-specific IBANs, so I can seed payment fixtures with structurally valid identifiers.

**Expected Behavior / Usage:**

The adapter accepts an account digit count and an IBAN country code. It returns a generated account number with its length and an IBAN with its length and country prefix.

**Test Cases:** `rcb_tests/public_test_cases/feature15_bank_identifiers.json`

```json
{
    "description": "Generate banking identifiers with caller-controlled account length and country-specific IBAN format.",
    "cases": [
        {
            "input": {
                "seed": 1701,
                "account_digits": 12,
                "iban_country": "de"
            },
            "expected_output": "account_number=089433234324\naccount_length=12\niban=DE22335004282336218517\niban_length=22\niban_country=DE\n"
        }
    ]
}
```

---

### Feature 16: Company Registration Identifiers

**As a developer**, I want to generate company and tax registration identifiers with valid checksums, so I can seed business fixtures that pass format validation.

**Expected Behavior / Usage:**

The adapter accepts a requested Polish register length and returns multiple organization identifiers. The output includes checksum validation signals for identifiers whose public contract includes check digits, plus rendered lengths where applicable.

**Test Cases:** `rcb_tests/public_test_cases/feature16_company_identifiers.json`

```json
{
    "description": "Generate company registration and tax identifiers with embedded checksum or format constraints.",
    "cases": [
        {
            "input": {
                "seed": 1801,
                "polish_register_length": 9
            },
            "expected_output": "french_siren=428343164\nfrench_siren_luhn_valid=true\nfrench_siret=85916236400227\nfrench_siret_luhn_valid=true\nnorwegian_org=898049590\nnorwegian_check_valid=true\npolish_register=044689728\npolish_register_length=9\nbrazilian_company_number=10222895000405\nbrazilian_length=14\n"
        }
    ]
}
```

---

### Feature 17: File and Directory Strings

**As a developer**, I want to generate file extensions, MIME types, file names, and directory paths, so I can seed filesystem fixtures with shaped paths.

**Expected Behavior / Usage:**

The adapter accepts a directory depth, root prefix, and separator. It returns a file extension, MIME type, complete file name, and directory path using the supplied directory-shaping inputs.

**Test Cases:** `rcb_tests/public_test_cases/feature17_file_paths.json`

```json
{
    "description": "Generate file extensions, MIME types, complete file names, and directory paths with optional root and separator inputs.",
    "cases": [
        {
            "input": {
                "seed": 1901,
                "depth": 2,
                "root": "\\root\\",
                "separator": "\\"
            },
            "expected_output": "extension=jpeg\nmime_type=image/pjpeg\nfile_name=quos_enim/asperiores.txt\ndirectory=\\root\\recusandae-reprehenderit\\quibusdam_vero\n"
        }
    ]
}
```

---

### Feature 18: International Phone Numbers

**As a developer**, I want to generate phone country codes and international phone strings, so I can seed contact fixtures with country-prefixed numbers.

**Expected Behavior / Usage:**

The adapter accepts a random seed and returns a phone country code, a phone number with a country code, and a cell number with a country code. International phone strings must begin with a plus-prefixed country component.

**Test Cases:** `rcb_tests/public_test_cases/feature18_phone_numbers.json`

```json
{
    "description": "Generate phone country codes and international phone strings that begin with a country prefix.",
    "cases": [
        {
            "input": {
                "seed": 2001
            },
            "expected_output": "country_code=+1\nphone_with_country_code=+1-268 1-165-010-4794\ncell_with_country_code=+233 991.671.6509\n"
        }
    ]
}
```

---

### Feature 19: JSON Document Shape

**As a developer**, I want to generate shallow and nested JSON documents of a chosen size, so I can seed API fixtures with controllable structure.

**Expected Behavior / Usage:**

The adapter accepts an item count and nesting depth. It returns the generated JSON document and shape signals for top-level pair count and flattened top-level length.

**Test Cases:** `rcb_tests/public_test_cases/feature19_json_shape.json`

```json
{
    "description": "Generate shallow and nested JSON documents with a requested key/value generator and element count.",
    "cases": [
        {
            "input": {
                "seed": 2101,
                "count": 3,
                "depth": 1
            },
            "expected_output": "json={\"Robby\":{\"Lorita\":\"Alonzo\",\"Booker\":\"Tamie\",\"Glory\":\"Monte\"},\"Karen\":{\"Daria\":\"Scarlet\",\"Carroll\":\"Kirsten\",\"Gia\":\"Clifton\"},\"Londa\":{\"Bennie\":\"Patricia\",\"Gino\":\"Faustino\",\"Willard\":\"Tuan\"}}\ntop_level_pairs=3\ntop_level_flatten_length=6\n"
        }
    ]
}
```

---

### Feature 20: Normalized Error Reporting

**As a developer**, I want invalid inputs to surface as neutral error categories instead of raw runtime faults, so I can handle failures uniformly across languages.

**Expected Behavior / Usage:**

The adapter accepts an error scenario and invalid parameters. Instead of leaking runtime exception names, it returns neutral error category lines and the relevant input fields.

**Test Cases:** `rcb_tests/public_test_cases/feature20_error_normalization.json`

```json
{
    "description": "Report language-neutral error categories when caller inputs make generation impossible or invalid.",
    "cases": [
        {
            "input": {
                "scenario": "oversized_username",
                "min_length": 10000000
            },
            "expected_output": "error=argument_too_large\nfield=min_length\nvalue=10000000\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- see the date exclusion utility function for handling except blocks
