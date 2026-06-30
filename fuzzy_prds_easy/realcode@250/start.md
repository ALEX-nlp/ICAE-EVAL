## Product Requirement Document

# Test Runner Output Stream Analyzer - Translating a Test Harness Event Stream into Structured Outcomes

## Project Goal

Build a library that consumes the raw progress/result event stream emitted by a Java unit-test harness (a line-oriented text protocol) and translates it into structured, UI-ready test outcomes — per-test lifecycle signals (started / passed / failed / errored) plus rich diagnostic messages whose stack frames are turned into navigable source links. This lets an editor integration render live test results and let a developer jump straight from a failure to the offending source line, without re-implementing the brittle parsing of the harness wire format by hand.

---

## Background & Problem

A Java test harness streams its progress as a flat sequence of prefixed control lines: a tree of declared test nodes, then start/end markers, optional failure or error markers, and embedded stack-trace blocks. Each line is terse and positional (comma-delimited fields, fixed `%`-prefixed tags), and the stack-trace text is plain compiler output. An editor that wants to show a green/red tree and clickable failures must interpret this stream correctly: associate each event line with the right declared test, decide the final state of each test, extract the failure message, and rewrite stack frames into clickable links pointing at the exact file and line.

Without a dedicated analyzer, every integration re-parses this protocol ad hoc, mishandles edge cases (nested classes, frames from library code vs. the test source, multi-line traces), and produces inconsistent diagnostics. With this library, the stream is parsed once into a stable contract: a deterministic ordered list of lifecycle signals and a normalized diagnostic message anchored to the correct source line.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. The core here is a focused stream parser plus an outcome model; it should be organized into clear logical units (protocol tokenizing, state tracking, stack-frame rewriting, outcome emission) rather than one tangled function, but it must not be over-engineered into needless layers.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in the "Core Features" section are a **black-box contract for the execution adapter**, NOT the internal data model. The core parser MUST be decoupled from stdin/stdout and JSON. The execution adapter is solely responsible for decoding a JSON command, driving the core over the supplied stream text, and serializing the observed outcome to stdout in the documented line format.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility:** Separate protocol parsing, test-node bookkeeping, stack-frame link rewriting, and outcome formatting.
   - **Open/Closed:** Adding a new harness family (a different test framework value) must be possible by extension, not by editing the existing parser.
   - **Liskov Substitution:** Any framework-specific analyzer must be substitutable wherever the base analyzer type is expected.
   - **Interface Segregation:** Keep the outcome-sink interface (started / passed / failed / errored / skipped) small and cohesive.
   - **Dependency Inversion:** The parser depends on an abstract outcome sink, not on a concrete editor or I/O implementation.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public surface (feed text → receive ordered outcomes) must be elegant and idiomatic to the target language.
   - **Resilience:** Unrecognized lines, blank lines, traces with no in-file frame, and frames from library code must be handled gracefully and deterministically rather than throwing.

---

## Core Features

### Feature 1: Passing Test Result

**As a developer**, I want a test that runs to completion with no failure marker to be reported as started and then passed, so the editor can show it green and attribute it to the correct test identity.

**Expected Behavior / Usage:**

The input command carries three fields: `testKind` (the harness family, e.g. `JUnit`), `item` (the single test under observation, identified by `id` of the form `<project>@<fully.qualified.Class>#<method>` plus the `uri` of its source file), and `runnerOutput` (the raw event-stream text).

The stream is a sequence of `\n`-separated control lines:
- `%TESTC <n> v2` — a header announcing the run.
- `%TSTTREE<idx>,<name>(<class>),<isSuite>,<count>,<isDynamic>,<parentId>,<displayName>,,` — declares test node `<idx>` and binds it to a test identity built as `<project>@<class>#<name>`.
- `%TESTS  <idx>,<name>(<class>)` — that node has started executing.
- `%TESTE  <idx>,<name>(<class>)` — that node has finished.
- `%RUNTIME<ms>` — total elapsed time (consumed, not surfaced).

When a declared node starts and later ends with no intervening failure/error marker, the analyzer emits exactly two lifecycle signals for that node’s identity: a `started` signal followed by a `passed` signal. Output is one `key=value` line per signal, in occurrence order, where the value is the resolved test identity. No timing value is emitted (it is non-deterministic and therefore not part of the contract).

**Test Cases:** `rcb_tests/public_test_cases/feature1_passing_test_result.json`

```json
{
    "description": "Parsing a runner stream where a single test method starts and ends without any failure marker, yielding a started signal followed by a passed signal for that test id.",
    "cases": [
        {
            "input": {
                "testKind": "JUnit",
                "item": {
                    "id": "junit@junit4.TestAnnotation#shouldPass",
                    "uri": "/mock/test/TestAnnotation.java"
                },
                "runnerOutput": "%TESTC  1 v2\n%TSTTREE1,shouldPass(junit4.TestAnnotation),false,1,false,-1,shouldPass(junit4.TestAnnotation),,\n%TESTS  1,shouldPass(junit4.TestAnnotation)\n%TESTE  1,shouldPass(junit4.TestAnnotation)\n%RUNTIME15"
            },
            "expected_output": "started=junit@junit4.TestAnnotation#shouldPass\npassed=junit@junit4.TestAnnotation#shouldPass\n"
        }
    ]
}
```

---

### Feature 2: Failing Test Result with Navigable Stack-Trace Diagnostic

**As a developer**, I want a failing test to be reported as failed together with a diagnostic message in which each stack frame becomes a clickable link to its file and line, so I can jump from the failure straight into the responsible code.

**Expected Behavior / Usage:**

Same input shape as Feature 1, but the stream contains a failure marker and an embedded stack-trace block:
- `%FAILED <idx>,<name>(<class>)` — marks the running node as failed.
- `%TRACES` … `%TRACEE` — delimit a block of raw stack-trace lines.

Each non-empty trace line that matches a stack frame of the form `at <pkg.Class.method>(<File.java>:<line>)` is rewritten into a markdown link: the qualified `<pkg.Class.method>` text, followed by `([<File.java>:<line>](command:_java.test.openStackTrace?<payload>))`, where `<payload>` is the URL-encoding of a JSON array `[<the exact original trace line>, <project>]`. The leading `at ` token of the frame is preserved verbatim before the link. Trace lines that are not recognizable frames (e.g. the exception header line) are passed through as plain text with `<`/`>` HTML-escaped. The accumulated, newline-joined trace is the diagnostic message.

The analyzer emits, in order: a `started` signal, a `failed` signal, then the diagnostic — a `message.location.line=<n>` line giving the **[a calculated index derived from stack analysis]** source line the message is anchored to (see Feature 3 for the anchoring rule; here the deepest frame whose file matches the test source determines it), a literal `message:` marker line, and finally the rendered multi-line message text.

**Test Cases:** `rcb_tests/public_test_cases/feature2_failing_test_result.json`

```json
{
    "description": "Parsing a runner stream containing a failure marker and a stack trace, yielding a started signal, a failed signal, and a diagnostic message whose stack frames are rendered as navigable links carrying the raw frame text and project name.",
    "cases": [
        {
            "input": {
                "testKind": "JUnit",
                "item": {
                    "id": "junit@junit4.TestAnnotation#shouldFail",
                    "uri": "/mock/test/TestAnnotation.java"
                },
                "runnerOutput": "%TESTC  1 v2\n%TSTTREE1,shouldFail(junit4.TestAnnotation),false,1,false,-1,shouldFail(junit4.TestAnnotation),,\n%TESTS  1,shouldFail(junit4.TestAnnotation)\n%FAILED 1,shouldFail(junit4.TestAnnotation)\n%TRACES \njava.lang.AssertionError\nat org.junit.Assert.fail(Assert.java:87)\nat org.junit.Assert.assertTrue(Assert.java:42)\nat org.junit.Assert.assertTrue(Assert.java:53)\nat junit4.TestAnnotation.shouldFail(TestAnnotation.java:15)\n%TRACEE \n%TESTE  1,shouldFail(junit4.TestAnnotation)\n%RUNTIME20;"
            },
            "expected_output": "started=junit@junit4.TestAnnotation#shouldFail\nfailed=junit@junit4.TestAnnotation#shouldFail\nmessage.location.line=14\nmessage:\njava.lang.AssertionError\nat org.junit.Assert.fail([Assert.java:87](command:_java.test.openStackTrace?%5B%22at%20org.junit.Assert.fail(Assert.java%3A87)%22%2C%22junit%22%5D))\nat org.junit.Assert.assertTrue([Assert.java:42](command:_java.test.openStackTrace?%5B%22at%20org.junit.Assert.assertTrue(Assert.java%3A42)%22%2C%22junit%22%5D))\nat org.junit.Assert.assertTrue([Assert.java:53](command:_java.test.openStackTrace?%5B%22at%20org.junit.Assert.assertTrue(Assert.java%3A53)%22%2C%22junit%22%5D))\nat junit4.TestAnnotation.shouldFail([TestAnnotation.java:15](command:_java.test.openStackTrace?%5B%22at%20junit4.TestAnnotation.shouldFail(TestAnnotation.java%3A15)%22%2C%22junit%22%5D))\n"
        }
    ]
}
```

---

### Feature 3: Errored Test Result with Source-Anchored Diagnostic

**As a developer**, I want a test that aborts with an uncaught error to be reported as errored, with its diagnostic message anchored to the exact line inside my test file where the failure originated, so the editor can place the squiggle on the right line even when the trace also contains frames from library code.

**Expected Behavior / Usage:**

Same input shape, but the stream carries an error marker:
- `%ERROR  <idx>,<name>(<class>)` — marks the node as errored.

The trace block is rewritten exactly as in Feature 2 (recognizable frames become navigable links; non-frame lines pass through as plain escaped text). The distinguishing behavior is the **anchoring rule** for the diagnostic location:
- Scan the trace frames in order; the **last** frame whose file basename equals the basename of the test item’s source `uri` sets the anchor to that frame’s reported line, converted to a **[a calculated index derived from stack analysis]** line number (reported line minus one).
- If no frame refers to the test source file, the message falls back to the test item’s own position (line `0` in these scenarios).

The analyzer emits, in order: a `started` signal, an `errored` signal, a `message.location.line=<n>` line carrying the resolved [a calculated index derived from stack analysis] anchor, a literal `message:` marker, and the rendered multi-line message text. Note that frames from library/runtime code (e.g. native reflection frames that have no `(File.java:line)` shape) are emitted as plain text and never become links nor move the anchor.

**Test Cases:** `rcb_tests/public_test_cases/feature3_errored_test_message_location.json`

```json
{
    "description": "Parsing a runner stream containing an error marker and a stack trace, yielding a started signal, an errored signal, and a diagnostic message anchored to the [a calculated index derived from stack analysis] source line of the deepest stack frame that lives in the test source file (falling back to the test item position when no in-file frame exists).",
    "cases": [
        {
            "input": {
                "testKind": "JUnit",
                "item": {
                    "id": "junit@junit4.TestAnnotation#shouldFail",
                    "uri": "/mock/test/TestAnnotation.java"
                },
                "runnerOutput": "%TESTC  1 v2\n%TSTTREE1,shouldFail(junit4.TestAnnotation),false,1,false,-1,shouldFail(junit4.TestAnnotation),,\n%TESTS  1,shouldFail(junit4.TestAnnotation)\n%ERROR  1,shouldFail(junit4.TestAnnotation)\n%TRACES \njava.lang.RuntimeException\n        at junit4.TestAnnotation.fail2(TestAnnotation.java:23)\n        at junit4.TestAnnotation.fail(TestAnnotation.java:19)\n        at junit4.TestAnnotation.shouldFail(TestAnnotation.java:15)\n        at sun.reflect.NativeMethodAccessorImpl.invoke0(Native Method)\n        at sun.reflect.NativeMethodAccessorImpl.invoke(NativeMethodAccessorImpl.java:62)\n%TRACEE \n%TESTE  1,shouldFail(junit4.TestAnnotation)\n%RUNTIME16"
            },
            "expected_output": "started=junit@junit4.TestAnnotation#shouldFail\nerrored=junit@junit4.TestAnnotation#shouldFail\nmessage.location.line=14\nmessage:\njava.lang.RuntimeException\n at junit4.TestAnnotation.fail2([TestAnnotation.java:23](command:_java.test.openStackTrace?%5B%22%20%20%20%20%20%20%20%20at%20junit4.TestAnnotation.fail2(TestAnnotation.java%3A23)%22%2C%22junit%22%5D))\n at junit4.TestAnnotation.fail([TestAnnotation.java:19](command:_java.test.openStackTrace?%5B%22%20%20%20%20%20%20%20%20at%20junit4.TestAnnotation.fail(TestAnnotation.java%3A19)%22%2C%22junit%22%5D))\n at junit4.TestAnnotation.shouldFail([TestAnnotation.java:15](command:_java.test.openStackTrace?%5B%22%20%20%20%20%20%20%20%20at%20junit4.TestAnnotation.shouldFail(TestAnnotation.java%3A15)%22%2C%22junit%22%5D))\n        at sun.reflect.NativeMethodAccessorImpl.invoke0(Native Method)\n at sun.reflect.NativeMethodAccessorImpl.invoke([NativeMethodAccessorImpl.java:62](command:_java.test.openStackTrace?%5B%22%20%20%20%20%20%20%20%20at%20sun.reflect.NativeMethodAccessorImpl.invoke(NativeMethodAccessorImpl.java%3A62)%22%2C%22junit%22%5D))\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured library that parses the test-harness event stream and produces an ordered sequence of test lifecycle outcomes plus normalized, source-anchored diagnostic messages with navigable stack-frame links. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON command from stdin (`testKind`, `item`, `runnerOutput`), drives the core over the supplied stream, and prints the observed outcome to stdout in the exact line format defined per feature above. The adapter is the only component that touches stdin/stdout and JSON, and is the only place where native errors are normalized into neutral category lines.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.[a zero-padded case index formatted as an integer substring]}.txt` (e.g. the first case in `feature1_passing_test_result.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_passing_test_result@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout of the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- uses the command palette action defined for Java stack traces
- aligns with the integration adapter schema specification
