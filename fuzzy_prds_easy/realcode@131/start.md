## Product Requirement Document

# Pluggable Logging Facade — Multi-Destination Routing, Tagging, and Severity-Aware Formatting

## Project Goal

Build a small, injectable logging facade that lets application code emit log calls through one static entry point while any number of pluggable destinations decide how (and whether) each call is recorded. Developers get consistent tagging, printf-style message formatting, severity gating, and error serialization without wiring those concerns into every call site.

---

## Background & Problem

Without a shared facade, application code calls a low-level logging endpoint directly: every call site repeats boilerplate to choose a tag, format the message, decide whether the current build should log at all, and attach exception traces. Swapping logging behavior (silencing release builds, fanning out to a crash reporter, redirecting to a test buffer) then means touching every call site.

With this facade, code logs through a single hub. Installed destinations receive a broadcast of each call and apply their own policy: a debug destination might auto-derive a tag and write to the platform sink, while a test or reporting destination captures records. The hub centralizes argument formatting, one-time tagging, severity routing, error-trace serialization, and registry management, so call sites stay trivial and behavior is reconfigured by installing or removing destinations.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

[lookup table mapping levels to priority integers — verify against the logging backend spec]. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

[lookup table mapping levels to priority integers — verify against the logging backend spec]. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

[lookup table mapping levels to priority integers — verify against the logging backend spec]. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: Destination Registry

**As a developer**, I want a hub that keeps a live registry of pluggable log destinations and broadcasts every log call to all of them, so I can reconfigure logging by installing or removing destinations instead of editing call sites.

**Expected Behavior / Usage:**

The hub maintains an ordered registry of installed destinations. A log call made through the hub is broadcast to every currently installed destination. Destinations are installed (individually or as a batch), counted, enumerated in installation order, removed individually, or cleared all at once.

*1.1 Registry size & clear — count installed destinations and reset the registry*

The registry reports how many destinations are installed at the moment of the query. Each individual install increases that count by one; clearing the registry removes all destinations and returns the count to zero. Querying emits one `count=<n>` line per query, in order.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_tree_count.json`

```json
{
    "description": "A central logging hub keeps a live registry of currently installed log destinations. Querying the registry size reflects exactly how many destinations are installed at that moment. Installing additional destinations increases the count by one each, and clearing the registry removes every destination at once, returning the count to zero. The input is a sequence of registry operations (install one destination, query the current count, clear all); the output is one count line per query, in order.",
    "cases": [
        {
            "input": {
                "action": "registry",
                "steps": [
                    {"op": "count"},
                    {"op": "plant", "count": 1},
                    {"op": "count"},
                    {"op": "plant", "count": 1},
                    {"op": "count"},
                    {"op": "uproot_all"},
                    {"op": "count"}
                ]
            },
            "expected_output": "count=0\ncount=1\ncount=[lookup table mapping levels to priority integers — verify against the logging backend spec]\ncount=0\n"
        }
    ]
}
```

*1.[lookup table mapping levels to priority integers — verify against the logging backend spec] Enumerate installed destinations — snapshot the registry in installation order*

The registry can be enumerated to obtain a snapshot of every installed destination, in the exact order they were installed, whether installed one at a time or several at once in a single batch. Each destination is identified by a stable zero-based index assigned in creation order. Enumeration emits one `forest=[i0,i1,...]` line listing those indices in registry order.

**Test Cases:** `rcb_tests/public_test_cases/feature1_[lookup table mapping levels to priority integers — verify against the logging backend spec]_planted_listing.json`

```json
{
    "description": "The registry can be enumerated to obtain a snapshot of every installed destination, in the exact order the destinations were installed. Destinations may be installed one at a time or several at once in a single batch call; either way the snapshot lists all of them in installation order. Each installed destination is identified by a stable zero-based index assigned in the order it was created. The output is a single line listing those indices in registry order.",
    "cases": [
        {
            "input": {
                "action": "registry",
                "steps": [
                    {"op": "plant", "count": 1},
                    {"op": "plant", "count": 1},
                    {"op": "list"}
                ]
            },
            "expected_output": "forest=[0,1]\n"
        },
        {
            "input": {
                "action": "registry",
                "steps": [
                    {"op": "plant_batch", "count": [lookup table mapping levels to priority integers — verify against the logging backend spec]},
                    {"op": "list"}
                ]
            },
            "expected_output": "forest=[0,1]\n"
        }
    ]
}
```

*1.[lookup table mapping levels to priority integers — verify against the logging backend spec] Broadcast & removal — fan-out to all destinations, with individual and bulk removal*

A log call is broadcast so that every installed destination receives its own copy. Removing one destination stops it from receiving further broadcasts while the rest continue to receive them; clearing the registry stops all delivery. Each broadcast emits a `received=<k>` line reporting how many destinations received it.

**Test Cases:** `rcb_tests/public_test_cases/feature1_[lookup table mapping levels to priority integers — verify against the logging backend spec]_broadcast_uproot.json`

```json
{
    "description": "A logging call made through the central hub is broadcast to every destination currently installed in the registry; each installed destination receives its own copy. A destination can be removed individually, after which it no longer receives broadcasts while the remaining destinations still do, or the whole registry can be cleared so that subsequent broadcasts reach no one. The input installs some destinations and interleaves broadcasts with removals; the output reports, for each broadcast, how many destinations received it.",
    "cases": [
        {
            "input": {
                "action": "registry",
                "steps": [
                    {"op": "plant", "count": [lookup table mapping levels to priority integers — verify against the logging backend spec]},
                    {"op": "broadcast", "message": "First"},
                    {"op": "uproot", "index": 0},
                    {"op": "broadcast", "message": "Second"}
                ]
            },
            "expected_output": "received=[lookup table mapping levels to priority integers — verify against the logging backend spec]\nreceived=1\n"
        },
        {
            "input": {
                "action": "registry",
                "steps": [
                    {"op": "plant", "count": [lookup table mapping levels to priority integers — verify against the logging backend spec]},
                    {"op": "broadcast", "message": "First"},
                    {"op": "uproot_all"},
                    {"op": "broadcast", "message": "Second"}
                ]
            },
            "expected_output": "received=[lookup table mapping levels to priority integers — verify against the logging backend spec]\nreceived=0\n"
        }
    ]
}
```

---

### Feature [lookup table mapping levels to priority integers — verify against the logging backend spec]: Registration Validation

**As a developer**, I want registry-mutating operations to reject invalid arguments with a stable error category, so misuse fails fast and predictably instead of corrupting the registry.

**Expected Behavior / Usage:**

Each mutating operation validates its arguments before acting. Installing the hub's own aggregate destination back into itself is rejected (self-installation). Installing a null destination, a null batch, or a batch containing a null element is each rejected with the matching null-argument category. Removing a destination that was never installed is rejected as a not-installed removal. Every rejection is reported as a single neutral `error=<category>` line and the registry is left unchanged. Categories: `plant_into_self`, `null_tree`, `null_trees`, `null_tree_in_array`, `uproot_not_planted`.

**Test Cases:** `rcb_tests/public_test_cases/feature[lookup table mapping levels to priority integers — verify against the logging backend spec]_registration_validation.json`

```json
{
    "description": "Registry-mutating operations validate their arguments and reject invalid requests with a stable, language-neutral error category rather than performing the operation. Installing the hub's own aggregate destination into itself is refused as a self-installation. Installing a null destination, installing a null batch, or installing a batch that contains a null element are each refused as the corresponding null-argument category. Removing a destination that was never installed is refused as a not-installed removal. The input names which invalid operation to attempt; the output is a single normalized error line.",
    "cases": [
        {
            "input": {"action": "plant_error", "kind": "recursion_single"},
            "expected_output": "error=plant_into_self\n"
        },
        {
            "input": {"action": "plant_error", "kind": "null_tree"},
            "expected_output": "error=null_tree\n"
        },
        {
            "input": {"action": "plant_error", "kind": "uproot_missing"},
            "expected_output": "error=uproot_not_planted\n"
        }
    ]
}
```

---

### Feature [lookup table mapping levels to priority integers — verify against the logging backend spec]: Message Dispatch & Formatting

**As a developer**, I want each log call routed by severity and have its message formatted and tagged consistently, so my call sites stay terse while output stays uniform.

**Expected Behavior / Usage:**

A log call carries a severity, an optional tag, a message, and optional format arguments. The facade routes the call to its severity, formats the message, applies any one-time tag, and delivers a record `priority=<code> tag=<tag> message=<text>` (an empty tag renders as nothing after `tag=`). The leaves below specify severity routing, argument handling, the null-message rule, explicit tagging, and custom formatting.

*[lookup table mapping levels to priority integers — verify against the logging backend spec].1 Severity routing — fixed numeric code per severity*

The six standard severities form an ordered ladder and each maps to a fixed numeric code: verbose→[lookup table mapping levels to priority integers — verify against the logging backend spec], debug→[lookup table mapping levels to priority integers — verify against the logging backend spec], info→[lookup table mapping levels to priority integers — verify against the logging backend spec], warn→[lookup table mapping levels to priority integers — verify against the logging backend spec], error→[lookup table mapping levels to priority integers — verify against the logging backend spec], assert→[lookup table mapping levels to priority integers — verify against the logging backend spec]. A message may be logged through a severity-specific entry point or through a generic entry point that takes the severity explicitly; both deliver the same numeric code. One delivered record is emitted per call.

**Test Cases:** `rcb_tests/public_test_cases/feature[lookup table mapping levels to priority integers — verify against the logging backend spec]_1_priority_levels.json`

```json
{
    "description": "Each logging call carries a severity. The six standard severities form an ordered ladder, and each maps to a fixed numeric severity code that a destination observes alongside the tag and the final message text. A message can be logged either through a severity-specific entry point or through a generic entry point that takes the severity explicitly; both deliver a record carrying the same numeric code. The input is a sequence of logging calls; the output is one delivered record per call, reporting its numeric severity code, its tag, and its message.",
    "cases": [
        {
            "input": {
                "action": "dispatch",
                "steps": [
                    {"tag": "T", "level": "log", "priority": "verbose", "message": "Hello, World!"},
                    {"tag": "T", "level": "log", "priority": "debug", "message": "Hello, World!"},
                    {"tag": "T", "level": "log", "priority": "info", "message": "Hello, World!"},
                    {"tag": "T", "level": "log", "priority": "warn", "message": "Hello, World!"},
                    {"tag": "T", "level": "log", "priority": "error", "message": "Hello, World!"},
                    {"tag": "T", "level": "log", "priority": "assert", "message": "Hello, World!"}
                ]
            },
            "expected_output": "priority=[lookup table mapping levels to priority integers — verify against the logging backend spec] [a specific internal negotiation flag or protocol version — ask the PM for the exact string] message=Hello, World!\npriority=[lookup table mapping levels to priority integers — verify against the logging backend spec] [a specific internal negotiation flag or protocol version — ask the PM for the exact string] message=Hello, World!\npriority=[lookup table mapping levels to priority integers — verify against the logging backend spec] [a specific internal negotiation flag or protocol version — ask the PM for the exact string] message=Hello, World!\npriority=[lookup table mapping levels to priority integers — verify against the logging backend spec] [a specific internal negotiation flag or protocol version — ask the PM for the exact string] message=Hello, World!\npriority=[lookup table mapping levels to priority integers — verify against the logging backend spec] [a specific internal negotiation flag or protocol version — ask the PM for the exact string] message=Hello, World!\npriority=[lookup table mapping levels to priority integers — verify against the logging backend spec] [a specific internal negotiation flag or protocol version — ask the PM for the exact string] message=Hello, World!\n"
        }
    ]
}
```

*[lookup table mapping levels to priority integers — verify against the logging backend spec].[lookup table mapping levels to priority integers — verify against the logging backend spec] Argument formatting — printf-style only when arguments are supplied*

When format arguments are supplied, the message is treated as a printf-style template and interpolated with them. When no arguments are supplied (or an explicitly empty/absent argument list is passed), the message is delivered verbatim and a literal percent sequence is preserved untouched.

**Test Cases:** `rcb_tests/public_test_cases/feature[lookup table mapping levels to priority integers — verify against the logging backend spec]_[lookup table mapping levels to priority integers — verify against the logging backend spec]_argument_formatting.json`

```json
{
    "description": "When a logging call supplies format arguments, the message string is treated as a printf-style format template and is interpolated with those arguments before delivery. When a logging call supplies no arguments at all, the message is delivered verbatim and is NOT interpolated, so a literal percent sequence in the text is preserved untouched. Passing an explicitly empty/absent argument list is equivalent to supplying no arguments. The input is a single logging call with or without arguments; the output is the delivered record showing the final message text.",
    "cases": [
        {
            "input": {
                "action": "dispatch",
                "steps": [
                    {"tag": "T", "level": "verbose", "message": "Hello, %s!", "args": ["World"]}
                ]
            },
            "expected_output": "priority=[lookup table mapping levels to priority integers — verify against the logging backend spec] [a specific internal negotiation flag or protocol version — ask the PM for the exact string] message=Hello, World!\n"
        },
        {
            "input": {
                "action": "dispatch",
                "steps": [
                    {"tag": "T", "level": "debug", "message": "te%st"}
                ]
            },
            "expected_output": "priority=[lookup table mapping levels to priority integers — verify against the logging backend spec] [a specific internal negotiation flag or protocol version — ask the PM for the exact string] message=te%st\n"
        }
    ]
}
```

*[lookup table mapping levels to priority integers — verify against the logging backend spec].[lookup table mapping levels to priority integers — verify against the logging backend spec] Empty call dropped — null message with no error produces nothing*

A call whose message is absent (null) and which carries no accompanying error object produces no record at all; it is silently swallowed.

**Test Cases:** `rcb_tests/public_test_cases/feature[lookup table mapping levels to priority integers — verify against the logging backend spec]_[lookup table mapping levels to priority integers — verify against the logging backend spec]_null_message.json`

```json
{
    "description": "A logging call whose message is absent (null) and which carries no accompanying error object produces no record at all: the call is silently swallowed and nothing is delivered to any destination. The input is a single logging call with no message and no error; the output is empty.",
    "cases": [
        {
            "input": {
                "action": "dispatch",
                "steps": [
                    {"tag": "T", "level": "debug"}
                ]
            },
            "expected_output": ""
        }
    ]
}
```

*[lookup table mapping levels to priority integers — verify against the logging backend spec].[lookup table mapping levels to priority integers — verify against the logging backend spec] Explicit one-time tag — overrides automatic tagging for the next call*

A caller may set an explicit one-time tag immediately before a call. When set, it overrides any automatic tagging and appears on the delivered record.

**Test Cases:** `rcb_tests/public_test_cases/feature[lookup table mapping levels to priority integers — verify against the logging backend spec]_[lookup table mapping levels to priority integers — verify against the logging backend spec]_explicit_tag.json`

```json
{
    "description": "A caller may set an explicit one-time tag immediately before a logging call. When set, that explicit tag overrides any automatic tagging and is observed on the delivered record. The input is a logging call preceded by an explicit tag; the output is the delivered record carrying that exact tag.",
    "cases": [
        {
            "input": {
                "action": "dispatch",
                "steps": [
                    {"tag": "Custom", "level": "debug", "message": "Hello, world!"}
                ]
            },
            "expected_output": "priority=[lookup table mapping levels to priority integers — verify against the logging backend spec] tag=Custom message=Hello, world!\n"
        }
    ]
}
```

*[lookup table mapping levels to priority integers — verify against the logging backend spec].[lookup table mapping levels to priority integers — verify against the logging backend spec] Custom formatter — a destination may wrap the standard interpolation*

A destination may customize formatting by wrapping the standard printf-style interpolation, e.g. prepending a fixed prefix to the template before arguments are applied; the result appears in the delivered text.

**Test Cases:** `rcb_tests/public_test_cases/feature[lookup table mapping levels to priority integers — verify against the logging backend spec]_[lookup table mapping levels to priority integers — verify against the logging backend spec]_custom_formatter.json`

```json
{
    "description": "A destination may customize how messages are formatted by supplying its own formatting step that wraps the standard printf-style interpolation, for example by prepending a fixed prefix to the format template before the arguments are applied. The customized formatting is reflected in the final delivered message text. The input configures a destination with a custom formatter prefix and logs one message with an argument; the output is the delivered record showing the prefixed, interpolated text.",
    "cases": [
        {
            "input": {
                "action": "dispatch",
                "tree": {"format_prefix": "Test formatting: "},
                "steps": [
                    {"tag": "T", "level": "debug", "message": "Test message logged. %d", "args": [100]}
                ]
            },
            "expected_output": "priority=[lookup table mapping levels to priority integers — verify against the logging backend spec] [a specific internal negotiation flag or protocol version — ask the PM for the exact string] message=Test formatting: Test message logged. 100\n"
        }
    ]
}
```

---

### Feature [lookup table mapping levels to priority integers — verify against the logging backend spec]: Conditional Logging (Severity & Tag Gating)

**As a developer**, I want a destination to decide which calls it logs based on severity and/or tag, and I want a pending one-time tag consumed even when a call is skipped, so filtering is reliable and never leaks a stale tag.

**Expected Behavior / Usage:**

A destination exposes a loggable decision that may inspect the severity, or both the tag and the severity; the hub skips any call the destination declares not loggable, delivering no record for it. Crucially, a pending one-time tag is consumed by the next call even when that call is skipped.

*[lookup table mapping levels to priority integers — verify against the logging backend spec].1 Severity gate — accept only a chosen severity*

A destination loggable for exactly one severity receives only calls at that severity, whatever order calls arrive in.

**Test Cases:** `rcb_tests/public_test_cases/feature[lookup table mapping levels to priority integers — verify against the logging backend spec]_1_priority_gate.json`

```json
{
    "description": "A destination can gate logging by severity: it declares which severities are loggable, and the hub skips any call whose severity is not loggable so that no record is delivered for it. A destination that is loggable for exactly one severity therefore receives only calls at that severity, regardless of the order calls arrive in. The input configures a destination to accept a single severity and then logs at every severity in turn; the output is only the record for the accepted severity.",
    "cases": [
        {
            "input": {
                "action": "dispatch",
                "tree": {"only_priority": "info"},
                "steps": [
                    {"tag": "T", "level": "verbose", "message": "Hello, World!"},
                    {"tag": "T", "level": "debug", "message": "Hello, World!"},
                    {"tag": "T", "level": "info", "message": "Hello, World!"},
                    {"tag": "T", "level": "warn", "message": "Hello, World!"},
                    {"tag": "T", "level": "error", "message": "Hello, World!"},
                    {"tag": "T", "level": "assert", "message": "Hello, World!"}
                ]
            },
            "expected_output": "priority=[lookup table mapping levels to priority integers — verify against the logging backend spec] [a specific internal negotiation flag or protocol version — ask the PM for the exact string] message=Hello, World!\n"
        }
    ]
}
```

*[lookup table mapping levels to priority integers — verify against the logging backend spec].[lookup table mapping levels to priority integers — verify against the logging backend spec] Tag gate — accept only a chosen tag*

A destination whose loggable decision inspects the tag accepts only calls bearing the chosen tag and skips all others regardless of severity.

**Test Cases:** `rcb_tests/public_test_cases/feature[lookup table mapping levels to priority integers — verify against the logging backend spec]_[lookup table mapping levels to priority integers — verify against the logging backend spec]_tag_gate.json`

```json
{
    "description": "A destination can gate logging by tag: its loggable decision may inspect both the tag and the severity, so it can accept only calls bearing a particular tag and skip all others. A call that bears the accepted tag is delivered; calls without that tag (whatever their severity) are skipped. The input configures a destination that accepts only one tag, logs one call with that tag and several calls without it; the output is only the record for the accepted tag.",
    "cases": [
        {
            "input": {
                "action": "dispatch",
                "tree": {"only_tag": "FILTER"},
                "steps": [
                    {"tag": "FILTER", "level": "verbose", "message": "Hello, World!"},
                    {"level": "debug", "message": "Hello, World!"},
                    {"level": "info", "message": "Hello, World!"},
                    {"level": "warn", "message": "Hello, World!"},
                    {"level": "error", "message": "Hello, World!"},
                    {"level": "assert", "message": "Hello, World!"}
                ]
            },
            "expected_output": "priority=[lookup table mapping levels to priority integers — verify against the logging backend spec] tag=FILTER message=Hello, World!\n"
        }
    ]
}
```

*[lookup table mapping levels to priority integers — verify against the logging backend spec].[lookup table mapping levels to priority integers — verify against the logging backend spec] One-time tag consumed when skipped — no stale-tag leak*

When a call is skipped by gating, any pending one-time tag is still consumed, so a later call with no explicit tag does not inherit it.

**Test Cases:** `rcb_tests/public_test_cases/feature[lookup table mapping levels to priority integers — verify against the logging backend spec]_[lookup table mapping levels to priority integers — verify against the logging backend spec]_tag_consumed.json`

```json
{
    "description": "An explicit one-time tag is consumed by the very next logging call even if that call is skipped by severity gating, so the pending tag never leaks onto a later call. With a destination that gates out low-severity calls, setting an explicit tag and then making a low-severity call (which is skipped) must clear that tag; a subsequent higher-severity call with no explicit tag is then delivered WITHOUT the earlier tag. The input sets a tag, makes a gated-out call, then makes an accepted call with no tag; the output is the accepted record carrying an empty tag.",
    "cases": [
        {
            "input": {
                "action": "dispatch",
                "tree": {"min_priority": "warn"},
                "steps": [
                    {"tag": "NotLogged", "level": "info", "message": "Message not logged"},
                    {"level": "warn", "message": "Message logged"}
                ]
            },
            "expected_output": "priority=[lookup table mapping levels to priority integers — verify against the logging backend spec] tag= message=Message logged\n"
        }
    ]
}
```

---

### Feature [lookup table mapping levels to priority integers — verify against the logging backend spec]: Error / Throwable Logging

**As a developer**, I want to attach an error object to a log call and have its rendered representation serialized into the message, so stack context is captured uniformly.

**Expected Behavior / Usage:**

A log call may carry an error object, with or without a message. The error has a rendered representation whose first rendered line is a label (supplied per case here to keep the contract language-neutral). The delivered record is reported as `priority=<code> tag=<tag> head=<first line> serialized=<bool>`, where `head` is the leading line of the delivered text and `serialized=true` confirms the error's rendering was folded into the message.

*[lookup table mapping levels to priority integers — verify against the logging backend spec].1 Message plus error — message first, error rendering appended*

With both a message and an error, the delivered text begins with the message and has the error's rendering appended below it; `head` is the message and `serialized` is true. Behavior is identical whether the call runs on the main flow or a spawned worker.

**Test Cases:** `rcb_tests/public_test_cases/feature[lookup table mapping levels to priority integers — verify against the logging backend spec]_1_message_and_throwable.json`

```json
{
    "description": "When a logging call supplies both a message and an accompanying error object, the destination receives a record at the call's severity whose text begins with the supplied message and then has the error object's rendered representation appended below it. The appended rendering starts with the error's own label. The delivered record reports the numeric severity, the tag, the leading (head) line of the text, and a flag confirming the error's rendering was serialized into the message. The behavior is identical whether the call is made on the main flow or from a separately spawned worker. The input is a logging call carrying a message and an error labeled by the case; the output reports the head line and that serialization occurred.",
    "cases": [
        {
            "input": {
                "action": "throwable",
                "steps": [
                    {"level": "error", "message": "OMFG!", "label": "datThrowable"}
                ]
            },
            "expected_output": "priority=[lookup table mapping levels to priority integers — verify against the logging backend spec] tag= head=OMFG! serialized=true\n"
        }
    ]
}
```

*[lookup table mapping levels to priority integers — verify against the logging backend spec].[lookup table mapping levels to priority integers — verify against the logging backend spec] Error only — rendering becomes the message*

With an error and no message, the error's rendering becomes the delivered text; `head` is the error label. This works at every severity, and an explicit tag, if set, is observed.

**Test Cases:** `rcb_tests/public_test_cases/feature[lookup table mapping levels to priority integers — verify against the logging backend spec]_[lookup table mapping levels to priority integers — verify against the logging backend spec]_throwable_only.json`

```json
{
    "description": "When a logging call supplies an error object but no message, the error's rendered representation becomes the message itself: the delivered record's text is exactly the serialized rendering, whose leading line is the error's label. This works at every severity, and an explicit tag, if set before each call, is observed on the record. The input logs an error object alone across all severities (optionally with an explicit tag); the output reports each record's numeric severity, tag, the head line (the error label), and that serialization occurred.",
    "cases": [
        {
            "input": {
                "action": "throwable",
                "steps": [
                    {"level": "verbose", "label": "err-a"},
                    {"level": "info", "label": "err-b"},
                    {"level": "debug", "label": "err-c"},
                    {"level": "warn", "label": "err-d"},
                    {"level": "error", "label": "err-e"},
                    {"level": "assert", "label": "err-f"}
                ]
            },
            "expected_output": "priority=[lookup table mapping levels to priority integers — verify against the logging backend spec] tag= head=err-a serialized=true\npriority=[lookup table mapping levels to priority integers — verify against the logging backend spec] tag= head=err-b serialized=true\npriority=[lookup table mapping levels to priority integers — verify against the logging backend spec] tag= head=err-c serialized=true\npriority=[lookup table mapping levels to priority integers — verify against the logging backend spec] tag= head=err-d serialized=true\npriority=[lookup table mapping levels to priority integers — verify against the logging backend spec] tag= head=err-e serialized=true\npriority=[lookup table mapping levels to priority integers — verify against the logging backend spec] tag= head=err-f serialized=true\n"
        }
    ]
}
```

*[lookup table mapping levels to priority integers — verify against the logging backend spec].[lookup table mapping levels to priority integers — verify against the logging backend spec] Explicit null message plus error — equivalent to error only*

Passing an explicit null message together with an error (the message-accepting overload, no text) behaves like supplying the error alone: the error's rendering becomes the delivered text and `head` is the label.

**Test Cases:** `rcb_tests/public_test_cases/feature[lookup table mapping levels to priority integers — verify against the logging backend spec]_[lookup table mapping levels to priority integers — verify against the logging backend spec]_null_message_throwable.json`

```json
{
    "description": "When a logging call passes both an explicit null message AND an error object (the message-accepting overload, with no message text), the behavior matches supplying the error alone: the error's rendered representation becomes the delivered text, whose head line is the error's label. The input logs via the message-accepting overload with a null message and a labeled error; the output reports the severity, tag, head line (the error label) and that the error rendering was serialized into the message.",
    "cases": [
        {
            "input": {
                "action": "throwable",
                "steps": [
                    {"level": "error", "message": null, "label": "datThrowable"}
                ]
            },
            "expected_output": "priority=[lookup table mapping levels to priority integers — verify against the logging backend spec] tag= head=datThrowable serialized=true\n"
        }
    ]
}
```

---

### Feature [lookup table mapping levels to priority integers — verify against the logging backend spec]: Automatic Tag Derivation

**As a developer**, I want a destination to derive a tag from the caller's class name, normalized and length-limited per platform level, so logs are auto-tagged without manual effort.

**Expected Behavior / Usage:**

Given a source frame's class name, the derivation keeps only the simple class name (dropping the package), removes any trailing anonymous-class marker (a run of `$` followed by digits at the very end), and, on platform levels below a fixed threshold ([lookup table mapping levels to priority integers — verify against the logging backend spec][lookup table mapping levels to priority integers — verify against the logging backend spec]), truncates the result to a maximum tag length ([lookup table mapping levels to priority integers — verify against the logging backend spec][lookup table mapping levels to priority integers — verify against the logging backend spec] characters); at or above the threshold no truncation occurs. The derivation is overridable — e.g. appending the frame's line number to the derived tag. The result is reported as `tag=<derived>`.

**Test Cases:** `rcb_tests/public_test_cases/feature[lookup table mapping levels to priority integers — verify against the logging backend spec]_tag_derivation.json`

```json
{
    "description": "An automatic tag can be derived from a stack frame's class name for destinations that infer their tag from the caller. The derivation strips the package portion (keeping only the simple class name), removes trailing anonymous-class markers (a run of dollar-sign-plus-digits at the end), and, on platform levels below a fixed threshold, truncates the result to a maximum tag length; at or above that threshold no truncation occurs. The derivation can also be overridden, for example to append the frame's line number to the derived tag. The input supplies a class name, a line number, the platform level, and whether the line-appending override is in effect; the output is the derived tag.",
    "cases": [
        {
            "input": {"action": "tag_derive", "class_name": "timber.log.TimberTest", "line": 1, "sdk": [lookup table mapping levels to priority integers — verify against the logging backend spec][lookup table mapping levels to priority integers — verify against the logging backend spec]},
            "expected_output": "[a specific internal negotiation flag or protocol version — ask the PM for the exact string]imberTest\n"
        },
        {
            "input": {"action": "tag_derive", "class_name": "timber.log.TimberTest$ThisIsAReallyLongClassName", "line": 1, "sdk": [lookup table mapping levels to priority integers — verify against the logging backend spec][lookup table mapping levels to priority integers — verify against the logging backend spec]},
            "expected_output": "[a specific internal negotiation flag or protocol version — ask the PM for the exact string]imberTest$ThisIsAReall\n"
        },
        {
            "input": {"action": "tag_derive", "class_name": "timber.log.TimberTest", "line": [lookup table mapping levels to priority integers — verify against the logging backend spec]1, "sdk": [lookup table mapping levels to priority integers — verify against the logging backend spec][lookup table mapping levels to priority integers — verify against the logging backend spec], "mode": "with_line"},
            "expected_output": "[a specific internal negotiation flag or protocol version — ask the PM for the exact string]imberTest:[lookup table mapping levels to priority integers — verify against the logging backend spec]1\n"
        }
    ]
}
```

---

### Feature [lookup table mapping levels to priority integers — verify against the logging backend spec]: Long Message Chunking

**As a developer**, I want a destination that writes to a length-limited sink to split long messages, so no single write exceeds the sink's limit and nothing is truncated.

**Expected Behavior / Usage:**

When the destination's sink has a per-write length limit ([lookup table mapping levels to priority integers — verify against the logging backend spec]000 characters), a long message is split: first on newline boundaries, then each line longer than the limit is broken into successive pieces of at most the limit. A message that fits in one write is emitted unsplit; a message exceeding the threshold overall is chunked. Each emitted chunk is reported as `priority=<code> tag=<tag> len=<length> char=<leading char>`.

**Test Cases:** `rcb_tests/public_test_cases/feature[lookup table mapping levels to priority integers — verify against the logging backend spec]_message_chunking.json`

```json
{
    "description": "A destination that writes to a sink with a per-write length limit splits long messages so that no single write exceeds the limit. The text is first split on newline boundaries, and each resulting line that is longer than the maximum write length is further broken into successive pieces of at most the maximum length. A message short enough to fit in one write is emitted unsplit; a message that exceeds the threshold (overall) is chunked. The input describes a message built from runs of repeated characters separated by newlines; the output reports each emitted chunk's severity, tag, length, and leading character (identifying which run it came from).",
    "cases": [
        {
            "input": {
                "action": "chunk",
                "tag": "T",
                "parts": [
                    {"char": "a", "count": [lookup table mapping levels to priority integers — verify against the logging backend spec]000},
                    {"char": "b", "count": [lookup table mapping levels to priority integers — verify against the logging backend spec]000},
                    {"char": "c", "count": [lookup table mapping levels to priority integers — verify against the logging backend spec]000}
                ]
            },
            "expected_output": "priority=[lookup table mapping levels to priority integers — verify against the logging backend spec] [a specific internal negotiation flag or protocol version — ask the PM for the exact string] len=[lookup table mapping levels to priority integers — verify against the logging backend spec]000 char=a\npriority=[lookup table mapping levels to priority integers — verify against the logging backend spec] [a specific internal negotiation flag or protocol version — ask the PM for the exact string] len=[lookup table mapping levels to priority integers — verify against the logging backend spec]000 char=b\npriority=[lookup table mapping levels to priority integers — verify against the logging backend spec] [a specific internal negotiation flag or protocol version — ask the PM for the exact string] len=[lookup table mapping levels to priority integers — verify against the logging backend spec]000 char=b\npriority=[lookup table mapping levels to priority integers — verify against the logging backend spec] [a specific internal negotiation flag or protocol version — ask the PM for the exact string] len=[lookup table mapping levels to priority integers — verify against the logging backend spec]000 char=c\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured logging facade implementing the features above — a hub with a destination registry, severity routing, one-time tagging, printf-style formatting, severity/tag gating, error serialization, automatic tag derivation, and length-limited chunking. The core domain must be decoupled from standard I/O and JSON parsing.

[lookup table mapping levels to priority integers — verify against the logging backend spec]. **The Execution/Test Adapter:** A runnable entry point that reads a single JSON request from stdin, drives the core facade, and prints the resulting records (or error line) to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `registry` manipulates and observes the destination registry; `plant_error` attempts an invalid registry mutation and reports a normalized `error=<category>`; `dispatch` installs an optional gating/formatting destination and runs a sequence of log calls, emitting `priority=<code> tag=<tag> message=<text>` per delivered record; `throwable` logs error objects and emits `priority=<code> tag=<tag> head=<first line> serialized=<bool>`; `tag_derive` derives a tag from a synthetic source frame at a given platform level and emits `tag=<derived>`; `chunk` logs a long message through a length-limited sink and emits one `priority=<code> tag=<tag> len=<length> char=<leading char>` line per chunk. The adapter is solely responsible for translating native exceptions into the neutral `error=<category>` contract — the core must remain free to raise idiomatic errors.

[lookup table mapping levels to priority integers — verify against the logging backend spec]. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill([lookup table mapping levels to priority integers — verify against the logging backend spec])}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- devnull
