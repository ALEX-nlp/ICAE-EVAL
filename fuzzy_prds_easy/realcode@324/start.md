## Product Requirement Document

# Embeddable Logging Engine — Thread-Aware Filtering, Encoding-Safe Capture, and Downstream Fan-Out

## Project Goal

Build an embeddable logging engine that accepts structured log entries from application code and hands them, after a small set of well-defined transformations, to one or more pluggable sinks. The engine lets developers attach rich context to each entry, filter entries by severity on a per-thread basis, repair text that would otherwise be unloggable, and broadcast the same entry to additional downstream loggers — all without the calling code having to know how or where entries are ultimately stored.

---

## Background & Problem

Without such an engine, developers wire ad-hoc logging by hand: they re-check severity thresholds at every call site, they discover too late that a message containing malformed bytes blows up serialization deep inside the stack, they copy entries by hand when they want the same line to reach both an in-memory inspector and a file logger, and they thread context (a captured backtrace, a request environment map) through layers of method calls because the logging call only accepts a bare string. Per-thread tuning — e.g. temporarily raising verbosity inside one worker thread without affecting the rest of the process — is essentially impossible with a single global level.

With this engine, the calling code emits one entry with optional structured metadata; the engine applies a per-thread severity gate, guarantees the message is valid text, preserves the metadata verbatim, fans the entry out to every attached downstream logger, and only then records it in the primary sink. A suppression switch lets callers route an entry to downstream loggers while skipping the primary sink. The result is a single, predictable entry point that hides all of this behind one call.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This is a focused engine with a handful of cohesive responsibilities (severity gating, encoding repair, metadata passthrough, fan-out, sink reporting). A small, well-separated module set is appropriate; do not inflate it into a sprawling framework, but do keep the core engine, the sink abstraction, and the execution adapter as distinct units rather than one monolithic file.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases in "Core Features" are a **black-box contract for the execution adapter**, not the internal data model of the engine. The core engine MUST NOT know about stdin/stdout or JSON. It exposes an idiomatic in-process API (emit an entry; configure a per-thread threshold; attach a downstream logger; toggle suppression) and reports finalized entries to a sink abstraction. The execution adapter is solely responsible for translating JSON commands into core API calls and rendering recorded entries to stdout.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Keep severity gating, encoding repair, metadata assembly, fan-out, and sink reporting as separate logical units.
   - **Open/Closed Principle (OCP):** New sink kinds and new downstream logger kinds must be addable without modifying the core engine.
   - **Liskov Substitution Principle (LSP):** Any sink must be usable wherever the sink abstraction is expected; any downstream logger that honours the documented forwarding interface must be substitutable for another.
   - **Interface Segregation Principle (ISP):** The sink interface should be minimal (accept a finalized entry); the downstream-logger interface should require only what fan-out actually calls.
   - **Dependency Inversion Principle (DIP):** The engine depends on the sink abstraction, never on a concrete storage or output implementation.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The emit call must accept a level plus optional message, source tag, structured metadata, and a deferred message producer, with sensible defaults, in a way idiomatic to the target language.
   - **Resilience:** Malformed input to the adapter must yield a normalized error line, never a host-language stack trace. A failure while forwarding to one downstream logger must not prevent the entry from reaching the others or the primary sink.

---

## Core Features

### Feature 1: Per-Thread Severity Threshold Filtering

**As a developer**, I want to gate log entries by a severity threshold that I can raise or lower on a single thread, so I can suppress low-importance entries — and temporarily change that decision inside one thread without disturbing the rest of the process.

**Expected Behavior / Usage:**

Each entry carries an integer `level` (higher = more severe). The engine compares the level against the threshold currently active **for the thread that emits the entry**: if the level is below the threshold the entry is dropped silently; if it is at or above the threshold the entry is recorded. A thread may install a threshold override; that override applies only to that thread, so an entry emitted on a different thread (which carries no override) is judged against the default acceptance level and is recorded. Clearing the override on a thread returns that thread to accepting all levels. Each recorded entry is rendered as a line `primary level=<L> source=<tag> message=<text> backtrace=<bt> env=<json> valid_encoding=<flag>` (absent fields render empty after `=`), and a trailing `primary total=<n>` reports how many entries were recorded.

**Test Cases:** `rcb_tests/public_test_cases/feature1_threshold_override.json`

```json
{
    "description": "A per-thread severity threshold filters log entries: an entry whose numeric level is below the active threshold for the thread that emits it is dropped, while an entry at or above the threshold is recorded. A threshold override applies only to the thread that set it; entries emitted on other threads are unaffected, and clearing the override on a thread restores its default acceptance of all levels. Each recorded entry is rendered with its level, source tag, message, attached metadata, and an encoding-validity flag, followed by a count of how many entries were recorded.",
    "cases": [
        {
            "input": {
                "actions": [
                    {"thread_threshold": 2},
                    {"log": {"level": 0, "message": "test", "source": "prog", "metadata": {"backtrace": "backtrace", "env": {"a": "x"}}, "thread": "main"}},
                    {"log": {"level": 0, "message": "test", "source": "prog", "metadata": {"backtrace": "backtrace", "env": {"a": "x"}}, "thread": "other"}},
                    {"thread_threshold": null},
                    {"log": {"level": 0, "message": "test", "source": "prog", "metadata": {"backtrace": "backtrace", "env": {"a": "x"}}, "thread": "main"}}
                ]
            },
            "expected_output": "primary level=0 source=prog message=test backtrace=backtrace env={\"a\":\"x\"} valid_encoding=true\nprimary level=0 source=prog message=test backtrace=backtrace env={\"a\":\"x\"} valid_encoding=true\nprimary total=2\n"
        }
    ]
}
```

---

### Feature 2: Encoding-Safe Message Capture

**As a developer**, I want messages containing malformed byte sequences to be repaired automatically before they are recorded, so I never lose a log entry — or crash a later serialization step — just because some bytes were not valid text.

**Expected Behavior / Usage:**

When an entry's message contains a byte run that is not valid text in its declared encoding, the engine repairs the message before recording, substituting the standard replacement character for each invalid run. The recorded message is therefore always valid text. The output shows the repaired message and an encoding-validity flag of `true`, confirming the stored message is valid. (In the sample, the input message is supplied as raw bytes where one byte is not valid standalone text; the recorded message shows that byte replaced.)

**Test Cases:** `rcb_tests/public_test_cases/feature2_encoding_scrub.json`

```json
{
    "description": "When a message carries a byte sequence that is not valid text in the declared encoding, the logger repairs the message before recording it by replacing each invalid byte run with the standard replacement character, so the stored message is always valid text. The output shows the repaired message and an encoding-validity flag confirming the stored message is now valid.",
    "cases": [
        {
            "input": {
                "actions": [
                    {"log": {"level": 4, "message": {"bytes": [97, 32, 228, 32, 116, 101, 115, 116]}, "source": "prog"}}
                ]
            },
            "expected_output": "primary level=4 source=prog message=a \uFFFD test backtrace= env= valid_encoding=true\nprimary total=1\n"
        }
    ]
}
```

---

### Feature 3: Structured Metadata Passthrough

**As a developer**, I want to attach a captured backtrace and an arbitrary context map to an entry and have them survive verbatim to the sink, so downstream tooling can use that context without me threading it through every layer by hand.

**Expected Behavior / Usage:**

An entry may carry a `metadata` object with a `backtrace` string and an `env` map of arbitrary keys and values. These are preserved unchanged on the recorded entry and rendered as their own labelled segments: `backtrace=<text>` and `env=<json-object>`. The engine does not interpret or reshape the env map; it round-trips exactly.

**Test Cases:** `rcb_tests/public_test_cases/feature3_metadata_passthrough.json`

```json
{
    "description": "Structured metadata attached to a log entry — a captured backtrace and an arbitrary environment map — is carried through unchanged to the recorded entry alongside the level, source tag, and message. The output renders each metadata field as its own labelled segment so callers can confirm the backtrace text and the environment map survived intact.",
    "cases": [
        {
            "input": {
                "actions": [
                    {"log": {"level": 0, "message": "test", "source": "prog", "metadata": {"backtrace": "backtrace", "env": {"a": "x"}}}}
                ]
            },
            "expected_output": "primary level=0 source=prog message=test backtrace=backtrace env={\"a\":\"x\"} valid_encoding=true\nprimary total=1\n"
        }
    ]
}
```

---

### Feature 4: Flexible Emit Arguments

**As a developer**, I want the emit call to accept a level with optional message, deferred message producer, and source tag, applying sensible defaults, so I can log tersely at call sites without boilerplate.

**Expected Behavior / Usage:**

*4.1 Deferred and Empty Messages — message resolved from a producer, or omitted entirely*

An entry may be emitted with an explicit message, OR with a deferred message producer instead of a message (the engine obtains the message from the producer when the entry is accepted), OR with neither (the entry is still recorded, with an empty message). All accepted entries are recorded in order; the output lists each and a trailing count. An entry whose message is empty renders an empty `message=` segment and an empty `valid_encoding=` segment (there is no text to validate).

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_block_and_default_message.json`

```json
{
    "description": "When an entry is logged without an explicit message but with a deferred message producer, the message is obtained from that producer and recorded. When an entry is logged with neither an explicit message nor a producer, it is still recorded but with an empty message. The output lists each recorded entry in order and a count, demonstrating that both forms are accepted and that the deferred producer's value is captured.",
    "cases": [
        {
            "input": {
                "actions": [
                    {"log": {"level": 2, "block": "test"}},
                    {"log": {"level": 2}}
                ]
            },
            "expected_output": "primary level=2 source= message=test backtrace= env= valid_encoding=true\nprimary level=2 source= message= backtrace= env= valid_encoding=\nprimary total=2\n"
        }
    ]
}
```

*4.2 Default Source Tag — source omitted defaults to empty*

When an entry is emitted with a level and a message but no source tag, the recorded entry's source tag defaults to empty. The source tag is never inferred from the message or any other field. The output shows an empty `source=` segment.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_default_source.json`

```json
{
    "description": "When an entry is logged with only a level and a message and no source tag is supplied, the recorded entry's source tag defaults to empty rather than being inferred from the message or any other field. The output shows the entry with an empty source segment, confirming the default.",
    "cases": [
        {
            "input": {
                "actions": [
                    {"log": {"level": 0, "message": "test"}}
                ]
            },
            "expected_output": "primary level=0 source= message=test backtrace= env= valid_encoding=true\nprimary total=1\n"
        }
    ]
}
```

---

### Feature 5: Downstream Fan-Out

**As a developer**, I want each accepted entry to be broadcast to additional loggers I attach, so the same line can reach an inspector, a file logger, and a remote collector at once — and I want a switch that broadcasts an entry while skipping my primary sink.

**Expected Behavior / Usage:**

*5.1 Forwarding to a Foreign Logger — standard logging interface, independent formatting*

When a foreign downstream logger is attached, each accepted entry is forwarded to it through the standard logging interface, and the foreign logger formats the entry on its own. The forwarded result exposes a single-letter severity indicator and the message text. The output shows the forwarded entry as observed at the foreign logger (`chain_standard severity=<letter> message=<text>`) followed by the entry recorded in the primary sink — proving the entry travelled the real downstream formatting path rather than being short-circuited.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_chain_standard.json`

```json
{
    "description": "When a foreign downstream logger is attached, each accepted entry is forwarded to it through the standard logging interface. The downstream logger formats the entry independently, exposing a single-letter severity indicator and the message text. The output shows the forwarded entry as observed at the downstream logger, plus the entry recorded by the primary sink, confirming the entry travelled through the real downstream formatting path rather than being short-circuited.",
    "cases": [
        {
            "input": {
                "actions": [
                    {"chain": "standard"},
                    {"log": {"level": 2, "message": null, "source": "boom"}}
                ]
            },
            "expected_output": "chain_standard severity=W message=boom\nprimary level=2 source= message=boom backtrace= env= valid_encoding=true\nprimary total=1\n"
        }
    ]
}
```

*5.2 Forwarding to a Same-Kind Sink — full payload, including metadata, preserved*

When another downstream logger of the same kind is attached, each accepted entry is forwarded to it carrying the **full** payload — level, source tag, message, and all attached metadata — identical to what the primary sink records. The output shows the entry as recorded by the downstream sink (with its own count) followed by the entry recorded by the primary sink (with its own count).

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_chain_recording.json`

```json
{
    "description": "When another sink of the same kind is attached downstream, each accepted entry is forwarded to it with the full payload — level, source tag, message, and all attached metadata (backtrace and environment map) — preserved identically to what the primary sink records. The output shows the forwarded entry as recorded by the downstream sink followed by the entry recorded by the primary sink, each with its own count.",
    "cases": [
        {
            "input": {
                "actions": [
                    {"chain": "recording"},
                    {"log": {"level": 0, "message": "test", "source": "prog", "metadata": {"backtrace": "backtrace", "env": {"a": "x"}}}}
                ]
            },
            "expected_output": "chained level=0 source=prog message=test backtrace=backtrace env={\"a\":\"x\"} valid_encoding=true\nchained total=1\nprimary level=0 source=prog message=test backtrace=backtrace env={\"a\":\"x\"} valid_encoding=true\nprimary total=1\n"
        }
    ]
}
```

*5.3 Suppression with Continued Fan-Out — primary skipped, downstream still reached and informed*

When the suppression switch is active, the primary sink records nothing, yet the entry is still forwarded to every attached downstream logger, and the suppression state is propagated to the downstream logger for the duration of the forwarded call. The output shows the downstream logger observing the entry with the suppression flag active (`chain_probe skip_store=true message=<text>`), while the primary sink reports a count of zero.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_skip_store_propagation.json`

```json
{
    "description": "A suppression flag prevents the primary sink from recording an entry, yet the entry is still forwarded to any attached downstream logger, and the suppression flag itself is propagated to that downstream logger for the duration of the forwarded call. The output shows the downstream logger observing the entry with the suppression flag active, while the primary sink records nothing.",
    "cases": [
        {
            "input": {
                "actions": [
                    {"chain": "probe"},
                    {"skip_store": true},
                    {"log": {"level": 2, "message": null, "source": "testing"}}
                ]
            },
            "expected_output": "chain_probe skip_store=true message=testing\nprimary total=0\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured logging engine implementing the features above — per-thread severity gating, encoding-safe message repair, structured metadata passthrough, flexible emit arguments, and downstream fan-out with a suppression switch — depending only on a minimal sink abstraction. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint: cohesive, separated modules without over-engineering.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core engine. It reads a single JSON command object from stdin, replays the listed `actions` (configure a per-thread threshold, toggle suppression, attach a downstream logger of a given kind, or emit an entry — optionally on another thread), and prints the recorded entries to stdout, strictly matching the per-leaf-feature contracts above. Native errors are normalized to neutral category lines; no host-language exception classes or runtime traces appear in stdout. This adapter is logically and physically separated from the core engine.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{stem}@{index_zero_padded_to_3}.txt` (e.g. the first case of `feature1_threshold_override.json` under `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_threshold_override@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout of the program under test (no PASS/FAIL or metadata), so it can be compared directly against `expected_output`.
