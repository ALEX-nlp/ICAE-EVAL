## Product Requirement Document

# Multi-Jurisdiction Holiday Calendar - Public holiday and business-day date calculations

## Project Goal

Build a holiday calendar and business-day calculation library that allows developers to determine public holidays, observed dates, and working-day offsets across multiple jurisdictions without hard-coding country-specific holiday tables.

---

## Background & Problem

Without this library, developers are forced to maintain separate date tables and one-off formulas for fixed holidays, Easter-based holidays, weekend substitutions, regional observances, and special one-time holidays. This leads to duplicated logic, stale calendars, inconsistent weekend handling, and scheduling bugs in payroll, settlement, booking, and deadline systems.

With this library, applications can ask for annual holiday lists, evaluate individual dates, move forward or backward across working days, and inspect observed-versus-actual holiday records through a consistent calendar interface.

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

### Feature 1: Annual Holiday Lists

**As a developer**, I want to retrieve the complete set of observed public holiday dates for a jurisdiction and year, so I can avoid manually maintaining yearly holiday tables.

**Expected Behavior / Usage:**

The adapter accepts a command identifying annual holiday-list generation, a supported calendar code, and a year. It prints the number of observed holiday dates and a comma-separated ascending `YYYY-MM-DD` list. The output represents observed holiday dates, including substitutions where the observed day differs from the actual holiday.

**Test Cases:** `rcb_tests/public_test_cases/feature1_annual_holiday_lists.json`

```json
{
    "description": "Annual calendar generation returns the complete sorted observed holiday date list for a supported calendar and year.",
    "cases": [
        {
            "input": {
                "feature": "holiday_list",
                "calendar": "US",
                "year": 1999
            },
            "expected_output": "count=10\ndates=1999-01-01,1999-01-18,1999-02-15,1999-05-31,1999-07-05,1999-09-06,1999-10-11,1999-11-11,1999-11-25,1999-12-24\n"
        },
        {
            "input": {
                "feature": "holiday_list",
                "calendar": "FR",
                "year": 2006
            },
            "expected_output": "count=11\ndates=2006-01-01,2006-04-17,2006-05-01,2006-05-08,2006-05-25,2006-06-05,2006-07-14,2006-08-15,2006-11-01,2006-11-11,2006-12-25\n"
        },
        {
            "input": {
                "feature": "holiday_list",
                "calendar": "IT",
                "year": 2017
            },
            "expected_output": "count=12\ndates=2017-01-01,2017-01-06,2017-04-16,2017-04-17,2017-04-25,2017-05-01,2017-06-02,2017-08-15,2017-11-01,2017-12-08,2017-12-25,2017-12-26\n"
        },
        {
            "input": {
                "feature": "holiday_list",
                "calendar": "JP",
                "year": 2025
            },
            "expected_output": "count=16\ndates=2025-01-01,2025-01-13,2025-02-11,2025-02-24,2025-03-20,2025-04-29,2025-05-03,2025-05-05,2025-05-06,2025-07-21,2025-08-11,2025-09-15,2025-09-23,2025-10-13,2025-11-03,2025-11-24\n"
        }
    ]
}
```

---

### Feature 2: Regional Holiday Lists

**As a developer**, I want to apply a regional selection such as province, state, district, or territory, so I can calculate jurisdiction-specific observances instead of relying on national defaults.

**Expected Behavior / Usage:**

The adapter accepts a regional holiday-list command with a calendar code, year, and the relevant regional selector. It prints the count and sorted observed dates for that regional calendar. Regional selectors narrow or extend the base calendar according to that jurisdiction’s tested rules.

**Test Cases:** `rcb_tests/public_test_cases/feature2_regional_holiday_lists.json`

```json
{
    "description": "Regional calendar generation applies the selected province, state, district, or region and returns sorted observed holiday dates for that jurisdiction.",
    "cases": [
        {
            "input": {
                "feature": "holiday_list",
                "calendar": "CA",
                "province": "BC",
                "year": 2016
            },
            "expected_output": "count=10\ndates=2016-01-01,2016-02-08,2016-03-25,2016-05-23,2016-07-01,2016-08-01,2016-09-05,2016-10-10,2016-11-11,2016-12-26\n"
        },
        {
            "input": {
                "feature": "holiday_list",
                "calendar": "CA",
                "province": "SK",
                "year": 2016
            },
            "expected_output": "count=10\ndates=2016-01-01,2016-02-15,2016-03-25,2016-05-23,2016-07-01,2016-08-01,2016-09-05,2016-10-10,2016-11-11,2016-12-26\n"
        },
        {
            "input": {
                "feature": "holiday_list",
                "calendar": "NZ",
                "district": "WELLINGTON",
                "year": 2022
            },
            "expected_output": "count=13\ndates=2022-01-03,2022-01-04,2022-01-24,2022-02-07,2022-04-15,2022-04-18,2022-04-25,2022-06-06,2022-06-24,2022-09-26,2022-10-24,2022-12-26,2022-12-27\n"
        }
    ]
}
```

---

### Feature 3: Observed and Actual Holiday Information

**As a developer**, I want to retrieve richer holiday records that distinguish actual holiday dates from observed dates, so I can preserve substitution details and names for downstream scheduling logic.

**Expected Behavior / Usage:**

The adapter accepts a holiday-information command with a calendar code and year. It prints `count=<n>` followed by one line per holiday sorted by observed date. Each line includes `holiday=<YYYY-MM-DD>`, `observed=<YYYY-MM-DD>`, `public=<true|false>`, and includes `name=<text>` or `[a pipe-separated list formatted region string]<pipe-separated-list>` when those fields are present.

**Test Cases:** `rcb_tests/public_test_cases/feature3_holiday_information.json`

```json
{
    "description": "Holiday information returns each holiday with actual holiday date, observed date, optional name, public flag, and optional regional applicability.",
    "cases": [
        {
            "input": {
                "feature": "holiday_info",
                "calendar": "US",
                "year": 2023
            },
            "expected_output": "count=11\nholiday=2023-01-01 observed=2023-01-02 name=New Year public=true\nholiday=2023-01-16 observed=2023-01-16 name=Martin Luther King Day public=true\nholiday=2023-02-20 observed=2023-02-20 name=President's Day public=true\nholiday=2023-05-29 observed=2023-05-29 name=Memorial Day public=true\nholiday=2023-06-19 observed=2023-06-19 name=Juneteenth public=true\nholiday=2023-07-04 observed=2023-07-04 name=Independence Day public=true\nholiday=2023-09-04 observed=2023-09-04 name=Labor Day public=true\nholiday=2023-10-09 observed=2023-10-09 name=Columbus Day public=true\nholiday=2023-11-11 observed=2023-11-10 name=Veteran's Day public=true\nholiday=2023-11-23 observed=2023-11-23 name=Thanksgiving public=true\nholiday=2023-12-25 observed=2023-12-25 name=Christmas public=true\n"
        }
    ]
}
```

---

### Feature 4: Single-Date Public Holiday Checks

**As a developer**, I want to ask whether one date is an observed public holiday, so I can validate user-entered dates without loading and searching calendars manually.

**Expected Behavior / Usage:**

The adapter accepts a calendar code, optional regional selector, and date. It prints the normalized date and `is_public_holiday=true` when that date is an observed public holiday for the selected calendar; otherwise it prints `is_public_holiday=false`. Weekends alone do not count as public holidays unless the calendar marks the date as an observed holiday.

**Test Cases:** `rcb_tests/public_test_cases/feature4_public_holiday_checks.json`

```json
{
    "description": "Single-date holiday checks report whether a date is an observed public holiday in the requested calendar.",
    "cases": [
        {
            "input": {
                "feature": "is_public_holiday",
                "calendar": "US",
                "date": "1999-11-25"
            },
            "expected_output": "date=1999-11-25\nis_public_holiday=true\n"
        },
        {
            "input": {
                "feature": "is_public_holiday",
                "calendar": "FR",
                "date": "2006-05-08"
            },
            "expected_output": "date=2006-05-08\nis_public_holiday=true\n"
        },
        {
            "input": {
                "feature": "is_public_holiday",
                "calendar": "FR",
                "date": "2006-05-09"
            },
            "expected_output": "date=2006-05-09\nis_public_holiday=false\n"
        },
        {
            "input": {
                "feature": "is_public_holiday",
                "calendar": "GB",
                "date": "2006-01-01"
            },
            "expected_output": "date=2006-01-01\nis_public_holiday=false\n"
        },
        {
            "input": {
                "feature": "is_public_holiday",
                "calendar": "GB",
                "date": "2006-01-02"
            },
            "expected_output": "date=2006-01-02\nis_public_holiday=true\n"
        }
    ]
}
```

---

### Feature 5: Single-Date Working Day Checks

**As a developer**, I want to ask whether one date is a business working day, so I can distinguish normal work days from weekends and public holidays.

**Expected Behavior / Usage:**

The adapter accepts a calendar code and date. It prints the normalized date and `is_working_day=true` only when the date is not a Saturday, not a Sunday, and not an observed public holiday in the selected calendar. It prints `is_working_day=false` for weekends and observed public holidays.

**Test Cases:** `rcb_tests/public_test_cases/feature5_working_day_checks.json`

```json
{
    "description": "Working-day checks report whether a date is Monday through Friday and not an observed public holiday for the selected calendar.",
    "cases": [
        {
            "input": {
                "feature": "is_working_day",
                "calendar": "US",
                "date": "2019-07-15"
            },
            "expected_output": "date=2019-07-15\nis_working_day=true\n"
        },
        {
            "input": {
                "feature": "is_working_day",
                "calendar": "US",
                "date": "2019-07-20"
            },
            "expected_output": "date=2019-07-20\nis_working_day=false\n"
        }
    ]
}
```

---

### Feature 6: Next Working Day Calculation

**As a developer**, I want to move forward to the next usable working day, so I can schedule deadlines while skipping weekends and holidays.

**Expected Behavior / Usage:**

The adapter accepts a calendar code, date, optional non-negative `open_days` offset, optional `same_day` flag, and optional custom holiday list. It prints the input date and `next_working_day=<YYYY-MM-DD>`. When `same_day` is true, a working input date with zero offset may be returned as-is; when false, the search starts after the input date. Negative open-day offsets are rejected with the normalized error contract `[the standard argument out of range error line]`, `[the standard argument out of range error line plus parameter identification]`, and `value=`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_next_working_day.json`

```json
{
    "description": "Forward working-day calculation returns the first acceptable working date on or after the input unless same-day matching is disabled, optionally after adding open days and skipping supplied holidays.",
    "cases": [
        {
            "input": {
                "feature": "next_working_day",
                "calendar": "US",
                "date": "1999-11-25"
            },
            "expected_output": "date=1999-11-25\nnext_working_day=1999-11-26\n"
        },
        {
            "input": {
                "feature": "next_working_day",
                "calendar": "US",
                "date": "2006-10-08"
            },
            "expected_output": "date=2006-10-08\nnext_working_day=2006-10-10\n"
        },
        {
            "input": {
                "feature": "next_working_day",
                "calendar": "GB",
                "date": "2006-12-24"
            },
            "expected_output": "date=2006-12-24\nnext_working_day=2006-12-27\n"
        },
        {
            "input": {
                "feature": "next_working_day",
                "calendar": "FR",
                "date": "2006-05-25"
            },
            "expected_output": "date=2006-05-25\nnext_working_day=2006-05-26\n"
        }
    ]
}
```

---

### Feature 7: Previous Working Day Calculation

**As a developer**, I want to move backward to the previous usable working day, so I can schedule retroactive deadlines while skipping weekends and holidays.

**Expected Behavior / Usage:**

The adapter accepts a calendar code, date, optional non-negative `open_days` offset, optional `same_day` flag, and optional custom holiday list. It prints the input date and `previous_working_day=<YYYY-MM-DD>`. When `same_day` is true, a working input date with zero offset may be returned as-is; when false, the search starts before the input date. Negative open-day offsets are rejected with the normalized error contract `[the standard argument out of range error line]`, `[the standard argument out of range error line plus parameter identification]`, and `value=`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_previous_working_day.json`

```json
{
    "description": "Backward working-day calculation returns the first acceptable working date on or before the input unless same-day matching is disabled, optionally after subtracting open days and skipping supplied holidays.",
    "cases": [
        {
            "input": {
                "feature": "previous_working_day",
                "calendar": "GB",
                "date": "2007-01-01"
            },
            "expected_output": "date=2007-01-01\nprevious_working_day=2006-12-29\n"
        },
        {
            "input": {
                "feature": "previous_working_day",
                "calendar": "CUSTOM",
                "date": "2021-10-22",
                "open_days": 3,
                "same_day": true,
                "holidays": [
                    {
                        "date": "2021-10-04",
                        "name": "Holiday 2021-10-04"
                    },
                    {
                        "date": "2021-10-05",
                        "name": "Holiday 2021-10-05"
                    },
                    {
                        "date": "2021-10-06",
                        "name": "Holiday 2021-10-06"
                    },
                    {
                        "date": "2021-10-11",
                        "name": "Holiday 2021-10-11"
                    },
                    {
                        "date": "2021-10-15",
                        "name": "Holiday 2021-10-15"
                    },
                    {
                        "date": "2021-10-20",
                        "name": "Holiday 2021-10-20"
                    }
                ]
            },
            "expected_output": "date=2021-10-22\nprevious_working_day=2021-10-18\n"
        }
    ]
}
```

---

### Feature 8: Business-Day Arithmetic

**As a developer**, I want to add business days or count business days across a date range, so I can perform date arithmetic without treating weekends and configured holidays as work days.

**Expected Behavior / Usage:**

The adapter supports adding business days from a start date and counting business days between two dates. Adding is exclusive of the start date, so the first counted day is the next business day after the input date. Counting between two dates is inclusive. Output names the input dates, the offset or range, and the resulting date or count.

**Test Cases:** `rcb_tests/public_test_cases/feature8_business_day_arithmetic.json`

```json
{
    "description": "Business-day arithmetic adds business days exclusively from a start date and counts business days inclusively between two dates while excluding weekends and configured holidays.",
    "cases": [
        {
            "input": {
                "feature": "business_days_add",
                "calendar": "CUSTOM",
                "date": "2024-12-24",
                "business_days": 5,
                "holidays": [
                    {
                        "date": "2024-12-25",
                        "name": "Christmas"
                    },
                    {
                        "date": "2025-01-01",
                        "name": "New Year"
                    }
                ]
            },
            "expected_output": "date=2024-12-24\nbusiness_days=5\nresult=2025-01-02\n"
        },
        {
            "input": {
                "feature": "business_days_add",
                "calendar": "CUSTOM",
                "date": "2024-12-16",
                "business_days": 3,
                "holidays": []
            },
            "expected_output": "date=2024-12-16\nbusiness_days=3\nresult=2024-12-19\n"
        }
    ]
}
```

---

### Feature 9: Gregorian Easter Dates

**As a developer**, I want to calculate Easter Sunday for a year, so I can derive moveable holidays that depend on Easter.

**Expected Behavior / Usage:**

The adapter accepts a year and prints `year=<year>` plus `easter=<YYYY-MM-DD>`. The date is Easter Sunday in the Gregorian calendar for that year.

**Test Cases:** `rcb_tests/public_test_cases/feature9_easter_dates.json`

```json
{
    "description": "Gregorian Easter calculation returns Easter Sunday for the requested year.",
    "cases": [
        {
            "input": {
                "feature": "easter_date",
                "year": 2010
            },
            "expected_output": "year=2010\neaster=2010-04-04\n"
        },
        {
            "input": {
                "feature": "easter_date",
                "year": 2017
            },
            "expected_output": "year=2017\neaster=2017-04-16\n"
        }
    ]
}
```

---

### Feature 10: Weekend Observation Rules

**As a developer**, I want to adjust weekend holiday dates according to a named observation policy, so I can model calendars that move Saturday or Sunday holidays to nearby weekdays.

**Expected Behavior / Usage:**

The adapter accepts an input date and an observation rule. It prints the input date and the adjusted observed date. The tested policies include moving weekend dates to the following Monday, moving Saturday to Friday and Sunday to Monday, moving a two-holiday weekend block after the weekend, and moving a two-holiday weekend block before the weekend.

**Test Cases:** `rcb_tests/public_test_cases/feature10_weekend_observed_dates.json`

```json
{
    "description": "Weekend-observed date adjustment rules move weekend holidays according to the requested observation policy.",
    "cases": [
        {
            "input": {
                "feature": "weekend_observed_date",
                "rule": "next_monday",
                "date": "2021-10-09"
            },
            "expected_output": "date=2021-10-09\nobserved_date=2021-10-11\n"
        },
        {
            "input": {
                "feature": "weekend_observed_date",
                "rule": "next_monday",
                "date": "2021-10-10"
            },
            "expected_output": "date=2021-10-10\nobserved_date=2021-10-11\n"
        },
        {
            "input": {
                "feature": "weekend_observed_date",
                "rule": "saturday_before_sunday_after",
                "date": "2021-10-09"
            },
            "expected_output": "date=2021-10-09\nobserved_date=2021-10-08\n"
        }
    ]
}
```

---

### Feature 11: Country-Code Calendar Resolution

**As a developer**, I want to resolve supported two-letter jurisdiction codes into usable calendars, so I can select calendars dynamically from user configuration.

**Expected Behavior / Usage:**

The adapter accepts a two-letter calendar code and a year. It prints the requested code, `resolved=true`, the year, and `holiday_count=<n>` after successfully producing that year’s holiday list. Unsupported or empty codes are outside the public examples; implementations should model such errors with language-neutral categories rather than runtime-specific exception text.

**Test Cases:** `rcb_tests/public_test_cases/feature11_country_code_resolution.json`

```json
{
    "description": "Country-code resolution creates a holiday calendar for supported two-letter codes and reports that the code can produce a holiday list.",
    "cases": [
        {
            "input": {
                "feature": "factory_resolution",
                "country_code": "AU",
                "year": 2017
            },
            "expected_output": "country_code=AU\nresolved=true\nyear=2017\nholiday_count=7\n"
        },
        {
            "input": {
                "feature": "factory_resolution",
                "country_code": "AT",
                "year": 2017
            },
            "expected_output": "country_code=AT\nresolved=true\nyear=2017\nholiday_count=13\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_annual_holiday_lists.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_annual_holiday_lists@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- extend the date forward by the business_days count
- apply the omission rule for undefined metadata
