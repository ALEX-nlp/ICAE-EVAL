## Product Requirement Document

# Credential Autofill Data Engine - Credential Projection, Matching, and Screen-State Contracts

## Project Goal

Build a credential autofill data engine that allows developers to project saved credentials, match them to requesting web or app contexts, identify fill targets in structured screen trees, and coordinate lock/navigation state without hand-writing repetitive domain, view-tree, and state-stream glue code.

---

## Background & Problem

Without this library/tool, developers are forced to manually clean hostnames for display, derive comparable registrable domains from multiple request sources, inspect screen trees for fillable fields, and coordinate credential UI state with lock and navigation events. This leads to duplicated parsing logic, inconsistent matching rules, fragile autofill behavior, and error-prone state handling.

With this library/tool, saved credential data, request context, screen structure, and state events are converted into deterministic line-oriented results that can be tested as black-box behavior and reused by a UI or service adapter.

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

### Feature 1: Credential Summary Projection

**As a developer**, I want to view a saved credential as a compact list entry, so I can show users recognizable saved-login rows without exposing secret fields.

**Expected Behavior / Usage:**

The input is one saved credential object containing a stable identifier, an origin host, an optional username, and a secret. The output is line-oriented stdout with `title`, `subtitle`, and `id`. The title is the display host with leading URL scheme and leading `www` variants removed; a missing username is rendered as an empty subtitle rather than an error.

**Test Cases:** `rcb_tests/public_test_cases/feature1_credential_summary.json`

```json
{
    "description": "Convert a stored credential into a list-row summary with a display title, subtitle, and stable identifier.",
    "cases": [
        {
            "input": {
                "feature": "credential_summary",
                "credential": {
                    "id": "afdsfdsa",
                    "hostname": "www.mozilla.org",
                    "username": "cats@cats.com",
                    "password": "woof"
                }
            },
            "expected_output": "title=mozilla.org\nsubtitle=cats@cats.com\nid=afdsfdsa\n"
        }
    ]
}
```

---

### Feature 2: Credential Detail Projection

**As a developer**, I want to view the full non-redacted detail for a selected saved credential, so I can display and copy the exact values associated with that credential.

**Expected Behavior / Usage:**

The input is one saved credential object containing a stable identifier, an origin host, an optional username, and a secret. The output is line-oriented stdout with `id`, `title`, `hostname`, `username`, `password`, and `has_username`. The title uses the same user-facing host cleanup as summary output, while `hostname` remains the exact stored origin. `has_username` is `false` for a blank or absent username.

**Test Cases:** `rcb_tests/public_test_cases/feature2_credential_detail.json`

```json
{
    "description": "Convert a stored credential into a detail record preserving origin, username, password, and whether a visible username exists.",
    "cases": [
        {
            "input": {
                "feature": "credential_detail",
                "credential": {
                    "id": "id0",
                    "hostname": "https://www.mozilla.org",
                    "username": "dogs@dogs.com",
                    "password": "woof"
                }
            },
            "expected_output": "id=id0\ntitle=mozilla.org\nhostname=https://www.mozilla.org\nusername=dogs@dogs.com\npassword=woof\nhas_username=true\n"
        }
    ]
}
```

---

### Feature 3.1: Registrable Domain from Web Domain

**As a developer**, I want to normalize a web domain into a registrable comparison key, so I can match credentials across equivalent subdomains while preserving the original domain string.

**Expected Behavior / Usage:**

The input is a domain string or null. The output is line-oriented stdout with `top_domain`, `full_domain`, `is_empty`, and `is_not_empty`. Recognized subdomains collapse to their registrable domain, public suffixes without a registrable owner produce an empty top domain, and null input produces empty fields.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_domain_from_web_domain.json`

```json
{
    "description": "Resolve a web domain string to its registrable top domain while preserving the full supplied domain and empty status.",
    "cases": [
        {
            "input": {
                "feature": "domain_from_web_domain",
                "domain": "example.com"
            },
            "expected_output": "top_domain=example.com\nfull_domain=example.com\nis_empty=false\nis_not_empty=true\n"
        }
    ]
}
```

---

### Feature 3.2: Registrable Domain from Application Identifier

**As a developer**, I want to derive a domain comparison key from an application identifier, so I can match native app requests to credentials using domain-like ownership signals.

**Expected Behavior / Usage:**

The input is an application identifier made of dot-separated labels. The system reverses those labels to form a domain-like name, then emits `top_domain`, `full_domain`, `is_empty`, and `is_not_empty` using the same registrable-domain rules as web domains.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_domain_from_package_name.json`

```json
{
    "description": "Resolve an application package identifier by reversing its labels into a domain and then deriving the registrable top domain.",
    "cases": [
        {
            "input": {
                "feature": "domain_from_package_name",
                "package_name": "com.example"
            },
            "expected_output": "top_domain=example.com\nfull_domain=example.com\nis_empty=false\nis_not_empty=true\n"
        }
    ]
}
```

---

### Feature 3.3: Registrable Domain from URL Origin

**As a developer**, I want to derive a domain comparison key from a URL origin, so I can match credentials requested by browser or web-view contexts.

**Expected Behavior / Usage:**

The input is a URL origin string or null. The host portion is extracted before registrable-domain resolution. The output is line-oriented stdout with `top_domain`, `full_domain`, `is_empty`, and `is_not_empty`. Empty or unparsable origins produce an empty domain result.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_domain_from_origin.json`

```json
{
    "description": "Resolve a URL origin by extracting its host and deriving the registrable top domain, falling back to an empty result when no valid host is available.",
    "cases": [
        {
            "input": {
                "feature": "domain_from_origin",
                "origin": "https://example.com"
            },
            "expected_output": "top_domain=example.com\nfull_domain=example.com\nis_empty=false\nis_not_empty=true\n"
        }
    ]
}
```

---

### Feature 3.4: Domain Equivalence Matching

**As a developer**, I want to compare two domain-derived keys, so I can allow saved credentials to match across subdomains of the same registered site.

**Expected Behavior / Usage:**

The input contains an expected domain and a candidate domain. Each is resolved to a registrable top domain, and the output includes `expected_top_domain`, `candidate_top_domain`, and `matches`. Matching is true when the resolved top domains are equal ignoring case.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_domain_match.json`

```json
{
    "description": "Compare two resolved domains as matching when their registrable top domains are equal, regardless of subdomain differences.",
    "cases": [
        {
            "input": {
                "feature": "domain_match",
                "expected_domain": "www.example.com",
                "candidate_domain": "mobile.example.com"
            },
            "expected_output": "expected_top_domain=example.com\ncandidate_top_domain=example.com\nmatches=true\n"
        }
    ]
}
```

---

### Feature 3.5: Credential Filtering by Requesting Domain

**As a developer**, I want to filter saved credentials for a requesting site or app, so I can show only credentials that belong to the current request context.

**Expected Behavior / Usage:**

The input contains a requesting web domain, a fallback application identifier, and an ordered list of saved credentials. If the web domain is null or empty, the application identifier supplies the expected domain. Each credential hostname is resolved from its URL origin, and only credentials with the same non-empty registrable top domain are emitted. The output starts with `matched_count`, followed by each matched credential id and hostname in original order.

**Test Cases:** `rcb_tests/public_test_cases/feature3_5_filter_credentials.json`

```json
{
    "description": "Filter saved credentials to those whose stored host resolves to the same registrable domain as the requesting web domain or package-derived domain.",
    "cases": [
        {
            "input": {
                "feature": "filter_credentials",
                "web_domain": "firefox.com",
                "package_name": "com.android.chrome",
                "credentials": [
                    {
                        "id": "example.com",
                        "hostname": "https://example.com",
                        "username": "example.com",
                        "password": "example.com"
                    },
                    {
                        "id": "firefox.com",
                        "hostname": "https://firefox.com",
                        "username": "firefox.com",
                        "password": "firefox.com"
                    },
                    {
                        "id": "accounts.firefox.com",
                        "hostname": "https://accounts.firefox.com",
                        "username": "accounts.firefox.com",
                        "password": "accounts.firefox.com"
                    },
                    {
                        "id": "mozilla.org",
                        "hostname": "https://mozilla.org",
                        "username": "mozilla.org",
                        "password": "mozilla.org"
                    }
                ]
            },
            "expected_output": "matched_count=2\nmatch_0_id=firefox.com\nmatch_0_hostname=https://firefox.com\nmatch_1_id=accounts.firefox.com\nmatch_1_hostname=https://accounts.firefox.com\n"
        }
    ]
}
```

---

### Feature 4: Autofill Field Detection from View Trees

**As a developer**, I want to identify username and password fields in a structured screen tree, so I can prepare precise fill targets for a credential autofill response.

**Expected Behavior / Usage:**

The input is a tree of screen nodes plus the activity package fallback. Nodes may expose semantic fill hints, visible text labels, generic node kinds such as text input or display text, HTML input tags, HTML attributes, package clues, and web-domain clues. The output is line-oriented stdout with `username_id`, `password_id`, `web_domain`, and `package_name`. Editable text inputs and HTML input fields are eligible fill targets when their own clues contain username/email or password keywords. A display label immediately followed by an eligible input can also identify that following input. Non-editable display text is not itself fillable. Domain and package clues are taken from the nearest ancestor of an identified fill target, falling back to the activity package when no package clue is found.

**Test Cases:** `rcb_tests/public_test_cases/feature4_autofill_fields.json`

```json
{
    "description": "Parse a view tree to identify username and password fill targets from fill hints, visible labels, HTML inputs, and nearby package or web origin clues.",
    "cases": [
        {
            "input": {
                "feature": "autofill_fields",
                "activity_package": "caller.package",
                "roots": [
                    {
                        "children": [
                            {
                                "id": "username",
                                "autofill_hints": [
                                    "username"
                                ],
                                "kind": "text_input"
                            },
                            {
                                "id": "password",
                                "autofill_hints": [
                                    "password"
                                ],
                                "kind": "text_input"
                            }
                        ]
                    }
                ]
            },
            "expected_output": "username_id=username\npassword_id=password\nweb_domain=\npackage_name=caller.package\n"
        }
    ]
}
```

---

### Feature 5: Replayable History Stack

**As a developer**, I want to maintain a stack of recent values with observer replay, so I can restore the latest navigation-like state for late subscribers without replaying the full history.

**Expected Behavior / Usage:**

The input is an ordered list of stack operations. `push` appends and emits a value to active subscribers; `subscribe` begins observing and immediately receives only the current top value if one exists; `pop`, `trim`, `trim_tail`, and `clear` mutate stored history without emitting by themselves. The output reports final `size`, final `top`, and comma-separated `observed` values received by subscribers.

**Test Cases:** `rcb_tests/public_test_cases/feature5_history_stack.json`

```json
{
    "description": "Maintain a replayable history stack that emits pushed values to subscribers and replays only the current top value to new subscribers; stack mutation operations do not emit by themselves.",
    "cases": [
        {
            "input": {
                "feature": "history_stack",
                "operations": [
                    {
                        "op": "subscribe"
                    },
                    {
                        "op": "push",
                        "value": 0
                    },
                    {
                        "op": "push",
                        "value": 1
                    }
                ]
            },
            "expected_output": "size=2\ntop=1\nobserved=0,1\n"
        }
    ]
}
```

---

### Feature 6: Route Reduction from State Events

**As a developer**, I want to turn navigation and data-state events into screen routes, so I can keep the visible screen synchronized with high-level app state.

**Expected Behavior / Usage:**

The input is an ordered list of route or data-state events. Explicit welcome route events emit the welcome route. Data error events do not emit a route. An unprepared data state emits the welcome route, an unlocked state emits the item-list route, and a locked state emits the lock-screen route. The output is a single `routes` line containing emitted route names in order.

**Test Cases:** `rcb_tests/public_test_cases/feature6_route_reducer.json`

```json
{
    "description": "Reduce navigation and data-state events into the current screen route, ignoring data error states while emitting explicit external route events.",
    "cases": [
        {
            "input": {
                "feature": "route_reducer",
                "events": [
                    {
                        "event": "route_welcome"
                    }
                ]
            },
            "expected_output": "routes=welcome\n"
        }
    ]
}
```

---

### Feature 7: Foreground Authentication Eligibility

**As a developer**, I want to track whether authentication can launch when returning to foreground, so I can avoid prompting at unsafe times while preserving authentication event signals.

**Expected Behavior / Usage:**

The input is an ordered list of lock, background, unlocking, and authentication-success events. The output contains `foreground_auth_values`, the comma-separated stream of eligibility states beginning with the default `true`, and `authentication_events`, the comma-separated authentication outcomes observed. Locking disables foreground launch until a background event re-enables it; active unlocking disables launch; a false unlocking event enables launch.

**Test Cases:** `rcb_tests/public_test_cases/feature7_lock_foreground_auth.json`

```json
{
    "description": "Track whether biometric authentication may be launched when the app comes to foreground based on lock, background, and unlocking events; pass authentication events through.",
    "cases": [
        {
            "input": {
                "feature": "lock_foreground_auth",
                "events": []
            },
            "expected_output": "foreground_auth_values=true\nauthentication_events=\n"
        }
    ]
}
```

---

### Feature 8: Auto-Lock Duration Values

**As a developer**, I want to read configured auto-lock choices as durations, so I can schedule lock behavior consistently from user-visible choices.

**Expected Behavior / Usage:**

The input is an ordered list of supported duration identifiers. The output contains one line per identifier with its millisecond value. The never-lock option is represented by zero milliseconds.

**Test Cases:** `rcb_tests/public_test_cases/feature8_auto_lock_durations.json`

```json
{
    "description": "Expose the configured auto-lock choices as millisecond durations, with the never-lock choice represented by zero.",
    "cases": [
        {
            "input": {
                "feature": "auto_lock_durations",
                "durations": [
                    "OneMinute",
                    "FiveMinutes",
                    "FifteenMinutes",
                    "ThirtyMinutes",
                    "OneHour",
                    "TwelveHours",
                    "TwentyFourHours",
                    "Never"
                ]
            },
            "expected_output": "OneMinute=60000\nFiveMinutes=300000\nFifteenMinutes=900000\nThirtyMinutes=1800000\nOneHour=3600000\nTwelveHours=43200000\nTwentyFourHours=86400000\nNever=0\n"
        }
    ]
}
```

---

### Feature 9: Text File Reading

**As a developer**, I want to read a text file as a complete string, so I can load small configuration or system marker files without partial reads.

**Expected Behavior / Usage:**

The input either provides inline file contents to be written to a temporary file before reading, or asks for a known-missing file. Successful output is `contents=<text>`. Missing files are normalized to the language-neutral line `error=file_not_found` and must not expose host-language exception names or runtime messages.

**Test Cases:** `rcb_tests/public_test_cases/feature9_read_text_file.json`

```json
{
    "description": "Read the complete contents of a text file and normalize missing-file failures to a language-neutral error category.",
    "cases": [
        {
            "input": {
                "feature": "read_text_file",
                "mode": "inline_file",
                "contents": "meow"
            },
            "expected_output": "contents=meow\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_credential_summary.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_credential_summary@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- apply the same leading 'www' and scheme stripping convention used in 'credential_summary_title'
- verify that the subscriber receives no value only when subscribe precedes push using the standard history_done logic
