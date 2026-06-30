## Product Requirement Document

# Security-Event Logging Toolkit — Classification Markers, Sensitive-Value Masking & Marker-Based Routing

## Project Goal

Build a reusable security-logging toolkit that lets developers tag log events with standard security classifications, automatically redact sensitive values out of rendered log text, and route events to different destinations based on their classification — so security-relevant information is consistently labeled, never leaks into the wrong log, and untrusted content cannot tamper with the log stream.

---

## Background & Problem

Applications constantly log information that has different sensitivity levels: ordinary diagnostics, audited security events (logins, access decisions), and outright secrets (passwords, card numbers, tokens). Without a shared vocabulary and a set of reusable processing primitives, every team invents ad-hoc conventions: secrets end up printed in plain text, security events are buried in the same file as debug noise, and attacker-controlled strings smuggle forged lines into the log.

This toolkit provides four cooperating capabilities expressed as a black-box contract. First, a small set of named **classification markers** (information levels such as restricted/confidential/secret/top-secret, and event outcomes such as security success/failure/audit) that can be attached to an event and combined into a composite, with a containment query to test what a composite carries. Second, **confidential-argument redaction** that blanks out the arguments of a parameterized message when the event is confidential. Third, **pattern-based field redaction** that scrubs named sensitive fields (passwords, usernames, order numbers, emails) inside free-form message text using four distinct masking strategies. Fourth, **control-character neutralization** that defuses log-injection. Finally, **marker-based routing filters** that turn an event's markers into a three-way routing decision.

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

### Feature 1: Security Classification Markers

**As a developer**, I want to attach standard security classification markers to an event and combine several of them, so I can label what an event contains and later test that labeling programmatically.

**Expected Behavior / Usage:**

A marker is identified by its name. The supported names include the information-classification levels `RESTRICTED`, `CONFIDENTIAL`, `SECRET`, `TOPSECRET`, the security-event outcomes `SECURITY SUCCESS`, `SECURITY FAILURE`, `SECURITY AUDIT`, and the non-security event outcomes `EVENT SUCCESS`, `EVENT FAILURE`. Given an ordered list of marker names, the toolkit produces one composite marker. The composite exposes a `name` equal to the concatenation of its child marker names in the order they were supplied (the child names are joined directly, with no separator inserted between them). The composite also answers a containment query: for any marker name, it reports whether that marker is present inside the composite. A composite contains exactly the markers it was built from — each member name resolves to true, and any name that was never added resolves to false. The output reports the composite name on the first line, then one `contains[<name>]=<true|false>` line per probed name, in the order probed.

**Test Cases:** `rcb_tests/public_test_cases/feature1_marker_composition.json`

```json
{
    "description": "Combine one or more security log markers into a single composite marker and probe its containment relationships. A composite is built from an ordered list of marker names; its reported name is the concatenation of the child marker names in order, and a containment query answers, for any given marker name, whether that marker is reachable inside the composite. A single-element composite contains its own marker and nothing else; a multi-element composite contains each of its members but not markers that were never added.",
    "cases": [
        {
            "input": {"op": "markers", "markers": ["SECURITY AUDIT"], "probes": ["SECURITY AUDIT", "CONFIDENTIAL"]},
            "expected_output": "name=SECURITY AUDIT\ncontains[SECURITY AUDIT]=true\ncontains[CONFIDENTIAL]=false\n"
        },
        {
            "input": {"op": "markers", "markers": ["SECURITY AUDIT", "CONFIDENTIAL"], "probes": ["SECURITY AUDIT", "CONFIDENTIAL", "SECURITY FAILURE"]},
            "expected_output": "name=SECURITY AUDITCONFIDENTIAL\ncontains[SECURITY AUDIT]=true\ncontains[CONFIDENTIAL]=true\ncontains[SECURITY FAILURE]=false\n"
        }
    ]
}
```

---

### Feature 2: Confidential Argument Redaction

**As a developer**, I want the arguments of a parameterized log message blanked out whenever the event is marked confidential, so secrets passed as message parameters never appear in the rendered log.

**Expected Behavior / Usage:**

The input is a message template containing positional `{}` placeholders plus an ordered list of argument values, together with an optional classification marker. When the event carries exactly the `CONFIDENTIAL` marker, every argument value is replaced by the fixed redaction token `********` before the template is formatted, so each placeholder in the rendered message is filled with the token rather than the real value. The rendered, fully formatted message string is returned. (The token is eight asterisks; the template's literal text and placeholder positions are preserved.)

**Test Cases:** `rcb_tests/public_test_cases/feature2_confidential_masking.json`

```json
{
    "description": "Render a parameterized log message whose arguments must be hidden because the event is tagged with the confidential classification marker. The message template uses positional placeholders that are normally substituted with the supplied argument values; when the confidential marker is present, every argument is first replaced with a fixed redaction token so no sensitive value reaches the rendered output, then the template is formatted. The output is the fully formatted message string with each placeholder filled by the redaction token.",
    "cases": [
        {
            "input": {"op": "mask_args", "marker": "CONFIDENTIAL", "template": "userid={}, password='{}'", "args": ["myId", "secret"]},
            "expected_output": "message=userid=********, password='********'\n"
        }
    ]
}
```

---

### Feature 3: Pattern-Based Field Redaction

**As a developer**, I want to scrub named sensitive fields out of free-form log text using a configurable strategy per field, so structured secrets embedded in messages are masked regardless of how the message was assembled.

**Expected Behavior / Usage:**

A redaction rule is configured with four field-name groups, each driving a different masking strategy. A field is recognized inside a message as `name` followed by an `=` or `:` separator and a value, where the name and value may optionally be wrapped in double quotes. Recognized fields are rewritten in place; everything else in the message passes through unchanged, and several fields in one message are each handled independently. The four strategies below are configured simultaneously and applied together.

*3.1 Full value masking — replace the entire value of a matched field with a fixed token*

The value of any field in the first group is completely replaced by the mask token `*****`, keeping the field name, separator, and any surrounding quotes. An empty message produces an empty result. Multiple matched fields in the same message are each fully masked.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_full_mask.json`

```json
{
    "description": "Fully redact the value of named sensitive fields found inside a free-form log message. A masking rule is configured for a set of field names (given as a regular-expression alternation). For any field whose name matches, the converter keeps the field name and its separator (an '=' or ':' assignment, optionally inside surrounding quotes) and replaces the entire value with a fixed mask token. Fields that do not match are left untouched, multiple matching fields in one message are each masked, and an empty message is returned unchanged.",
    "cases": [
        {
            "input": {"op": "regex_mask", "complete": "password|signature", "mask_tail": "username", "mask_head": "orderNumber|giftCardNum", "email": "email|customerEmail", "message": "password=[variable character truncation logic requiring boundary validation]"},
            "expected_output": "masked=password=*****\n"
        },
        {
            "input": {"op": "regex_mask", "complete": "password|signature", "mask_tail": "username", "mask_head": "orderNumber|giftCardNum", "email": "email|customerEmail", "message": "\"password\":\"[variable character truncation logic requiring boundary validation]\",signature=foo"},
            "expected_output": "masked=\"password\":\"*****\",signature=*****\n"
        }
    ]
}
```

*3.2 Trailing masking — keep a leading remainder, mask the rest*

For any field in the second group, the leading characters of the value are preserved and the trailing portion is collapsed into the mask token `*****`. Concretely, the final four value characters (plus the masking boundary) are replaced by the token, leaving the earlier characters visible (so a six-character value keeps its first two characters and ends in the token). Other groups continue to apply their own strategy to other fields in the same message.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_mask_trailing.json`

```json
{
    "description": "Partially redact a named field by masking the trailing portion of its value while preserving a leading remainder. A masking rule is configured for a field name; when that field is found in a message, all characters of its value except a short leading remainder are collapsed into a single mask token (concretely, the final four value characters and the mask boundary are replaced by the token, leaving the earlier characters visible). The field name, separator and optional surrounding quotes are retained. Other matching fields configured for full redaction are still fully masked in the same message.",
    "cases": [
        {
            "input": {"op": "regex_mask", "complete": "password|signature", "mask_tail": "username", "mask_head": "orderNumber|giftCardNum", "email": "email|customerEmail", "message": "username=[variable character truncation logic requiring boundary validation]"},
            "expected_output": "masked=username=[variable character truncation logic requiring boundary validation]\n"
        },
        {
            "input": {"op": "regex_mask", "complete": "password|signature", "mask_tail": "username", "mask_head": "orderNumber|giftCardNum", "email": "email|customerEmail", "message": "\"username\":\"[variable character truncation logic requiring boundary validation]\",signature=foo"},
            "expected_output": "masked=\"username\":\"[variable character truncation logic requiring boundary validation]\",signature=*****\n"
        }
    ]
}
```

*3.3 Leading masking — mask the front, keep the last four characters*

For any field in the third group, the leading run of value characters is replaced by the mask token `*****` while the last four characters of the value remain visible. The field name, separator and optional quotes are retained. Other groups continue to apply their own strategy to other fields in the same message.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_mask_leading.json`

```json
{
    "description": "Partially redact a named field by masking the leading portion of its value while preserving the last four characters. A masking rule is configured for a field name; when that field is found in a message, the converter keeps the field name and separator (optionally quoted), replaces the leading run of value characters with a single mask token, and leaves the final four characters visible. Other matching fields configured for full redaction are still fully masked in the same message.",
    "cases": [
        {
            "input": {"op": "regex_mask", "complete": "password|signature", "mask_tail": "username", "mask_head": "orderNumber|giftCardNum", "email": "email|customerEmail", "message": "orderNumber=77887765567[variable character truncation logic requiring boundary validation]"},
            "expected_output": "masked=orderNumber=*****c123\n"
        },
        {
            "input": {"op": "regex_mask", "complete": "password|signature", "mask_tail": "username", "mask_head": "orderNumber|giftCardNum", "email": "email|customerEmail", "message": "\"orderNumber\":\"[variable character truncation logic requiring boundary validation]\",signature=foo"},
            "expected_output": "masked=\"orderNumber\":\"*****c123\",signature=*****\n"
        }
    ]
}
```

*3.4 Email masking — keep the local part, mask the domain*

For any field in the fourth group whose value is an email address, the local part up to (but not including) the `@` is kept, and the `@` together with the entire domain is replaced by the mask token `*****`. The field name, separator and optional quotes are retained. Other groups continue to apply their own strategy to other fields in the same message.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_email_mask.json`

```json
{
    "description": "Redact the domain part of an email-valued field while keeping the local part visible. A masking rule is configured for a field name that holds an email address; when found, the converter keeps the field name and separator (optionally quoted) and the local part up to (but not including) the '@', then replaces the '@' and the entire domain with a single mask token. Other matching fields configured for full redaction are still fully masked in the same message.",
    "cases": [
        {
            "input": {"op": "regex_mask", "complete": "password|signature", "mask_tail": "username", "mask_head": "orderNumber|giftCardNum", "email": "email|customerEmail", "message": "email=foo@bar.com"},
            "expected_output": "masked=email=foo*****\n"
        },
        {
            "input": {"op": "regex_mask", "complete": "password|signature", "mask_tail": "username", "mask_head": "orderNumber|giftCardNum", "email": "email|customerEmail", "message": "\"email\":\"foo@bar.com.sg\",signature=foo"},
            "expected_output": "masked=\"email\":\"foo*****\",signature=*****\n"
        }
    ]
}
```

---

### Feature 4: Control-Character Neutralization

**As a developer**, I want carriage-return and line-feed characters in a string replaced before it is logged, so attacker-controlled content cannot forge extra log lines (log injection).

**Expected Behavior / Usage:**

Every carriage-return (`\r`) and line-feed (`\n`) character in the input string is replaced by a single underscore (`_`); all other characters are passed through unchanged. A `\r\n` pair therefore becomes two underscores. The result is always a single line.

**Test Cases:** `rcb_tests/public_test_cases/feature4_crlf_neutralize.json`

```json
{
    "description": "Neutralize line-breaking control characters in a string so that untrusted content cannot forge new log lines (a log-injection defense). Every carriage-return and line-feed character in the input is replaced by a single underscore; all other characters are passed through unchanged. The result is a single-line string with each control character swapped for an underscore.",
    "cases": [
        {
            "input": {"op": "crlf", "message": "This message contains \r\n line feeds"},
            "expected_output": "sanitized=This message contains __ line feeds\n"
        }
    ]
}
```

---

### Feature 5: Marker-Based Routing Filters

**As a developer**, I want filters that turn an event's classification markers into a routing decision, so I can send security events to a dedicated log, exclude classified data from a general log, or gate on one specific marker.

**Expected Behavior / Usage:**

Each filter inspects the marker (if any) attached to an event and returns a three-way routing decision drawn from `ACCEPT` (route immediately, short-circuiting the rest of the chain), `DENY` (drop), and `NEUTRAL` (no opinion — defer to the rest of the chain). The three filters below differ in which markers they react to and which decision they emit.

*5.1 Exclude-classified filter — drop events that carry an information-classification marker*

This filter returns `DENY` when the event carries any information-classification marker (`RESTRICTED`, `CONFIDENTIAL`, `SECRET`, `TOPSECRET`). It returns `NEUTRAL` when the event has no marker, or carries a marker that is not an information-classification level (e.g. a plain event-outcome marker). This is used to keep classified data out of a general-purpose log.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_exclude_classified.json`

```json
{
    "description": "Decide whether a log event should be excluded because it carries an information-classification marker. A routing filter returns one of three decisions: a deny decision when the event carries any classification marker (such as restricted, confidential, secret or top-secret), and a neutral (pass-through) decision when the event has no marker or carries a non-classification marker. The decision is reported as a neutral token.",
    "cases": [
        {
            "input": {"op": "filter_exclude"},
            "expected_output": "decision=NEUTRAL\n"
        },
        {
            "input": {"op": "filter_exclude", "marker": "CONFIDENTIAL"},
            "expected_output": "decision=DENY\n"
        },
        {
            "input": {"op": "filter_exclude", "marker": "EVENT SUCCESS"},
            "expected_output": "decision=NEUTRAL\n"
        }
    ]
}
```

*5.2 Security-routing filter — single out security-event markers, with an accept-all switch*

This filter reacts to the security-event markers (`SECURITY SUCCESS`, `SECURITY FAILURE`, `SECURITY AUDIT`). An event with no marker always yields `DENY`. An event carrying a security-event marker yields `NEUTRAL` in the default mode (pass it to the rest of the chain) or `ACCEPT` when the accept-all switch is enabled (route it immediately regardless of other filters). The `accept_all` boolean selects the mode and defaults to false.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_security_routing.json`

```json
{
    "description": "Decide how a log event should be routed based on whether it carries a security-event marker (security success, failure or audit). The filter denies any event that has no marker. For events that do carry a security-event marker the decision depends on a configuration flag: in the default mode the filter returns a neutral (pass-through) decision so the rest of the chain still applies; in accept-all mode it returns an accept decision so the event is routed immediately regardless of other filters. The decision is reported as a neutral token.",
    "cases": [
        {
            "input": {"op": "filter_security"},
            "expected_output": "decision=DENY\n"
        },
        {
            "input": {"op": "filter_security", "marker": "SECURITY SUCCESS"},
            "expected_output": "decision=NEUTRAL\n"
        },
        {
            "input": {"op": "filter_security", "accept_all": true, "marker": "SECURITY SUCCESS"},
            "expected_output": "decision=ACCEPT\n"
        }
    ]
}
```

*5.3 Named-marker filter — gate on one configured marker, with caller-chosen outcomes*

This filter is configured with a single target marker name plus a decision to emit on match and a decision to emit on mismatch. An event whose marker matches the configured target yields the configured on-match decision; an event with no marker (or whose marker does not match) yields the configured on-mismatch decision.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_named_marker.json`

```json
{
    "description": "Decide a log event using a filter configured to watch for one specific marker by name, with caller-chosen decisions for the match and mismatch outcomes. The filter is given a target marker name plus a decision to return on match and a decision to return on mismatch. An event whose marker matches the configured target yields the on-match decision; an event with no marker (or a non-matching marker) yields the on-mismatch decision. The decision is reported as a neutral token.",
    "cases": [
        {
            "input": {"op": "filter_named", "match_marker": "CONFIDENTIAL", "on_match": "ACCEPT", "on_mismatch": "DENY"},
            "expected_output": "decision=DENY\n"
        },
        {
            "input": {"op": "filter_named", "match_marker": "CONFIDENTIAL", "on_match": "ACCEPT", "on_mismatch": "DENY", "marker": "CONFIDENTIAL"},
            "expected_output": "decision=ACCEPT\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above (classification markers and composites, confidential-argument redaction, the four field-redaction strategies, control-character neutralization, and the three routing filters). Its physical structure MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the resulting contract line(s) to stdout. The request's `op` selects behavior: `markers` builds a composite from a list of marker names and reports its name plus the requested containment probes; `mask_args` renders a parameterized template, redacting all arguments when the `CONFIDENTIAL` marker is present; `regex_mask` applies the four field-redaction strategies (configured via `complete`, `mask_tail`, `mask_head`, `email`) to a `message`; `crlf` neutralizes carriage-returns and line-feeds in a `message`; `filter_exclude`, `filter_security` (honoring `accept_all`) and `filter_named` (honoring `match_marker`, `on_match`, `on_mismatch`) each report a routing `decision` of `ACCEPT`, `DENY` or `NEUTRAL` for the event's optional `marker`. Supported marker names are `RESTRICTED`, `CONFIDENTIAL`, `SECRET`, `TOPSECRET`, `SECURITY SUCCESS`, `SECURITY FAILURE`, `SECURITY AUDIT`, `EVENT SUCCESS`, `EVENT FAILURE`. The redaction token for whole-value masking is `*****`, and for confidential-argument masking is `********`.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same composition rules as the header module
