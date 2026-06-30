## Product Requirement Document

# Foreign-Function String Boundary Contract - Native String Round-Trip with UTF-8 Validation

## Project Goal

Build a thin language-binding layer that lets application developers pass strings from a managed runtime into a native (compiled) library and receive them back, while guaranteeing that text is transferred as valid UTF-8 bytes. The layer hides the byte-level marshalling so developers can call a single "send this string to the native side and get it back" operation and trust that any Unicode text — including supplementary-plane emoji — survives the trip intact, and that malformed text is rejected at the boundary rather than silently corrupting native memory.

---

## Background & Problem

Without this layer, developers crossing the managed/native boundary must hand-marshal every string: choose an encoding, allocate a byte buffer on the correct side of the boundary, copy the bytes, pass a length, and decode on the other side. Managed runtimes store text as UTF-16 code units and tolerate unpaired surrogates, but native code typically expects a contiguous UTF-8 byte sequence. If an unpaired surrogate is encoded naively it produces an invalid UTF-8 stream, which can corrupt the native string, crash the callee, or introduce a security hole. Getting this right by hand for every function is repetitive and error-prone, and getting it wrong fails in ways that are hard to diagnose.

With this layer, the developer calls one operation that transfers a string to the native side and returns it. Valid text of any Unicode plane round-trips byte-for-byte; text that cannot be represented as valid UTF-8 is rejected deterministically at the boundary with a clear, neutral error category, before any malformed bytes reach native code.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This contract is narrow (a single boundary operation over one scalar type), so a small, well-separated implementation is appropriate: keep the core boundary/marshalling logic in its own unit, and keep the input/output adapter separate from it. Do not collapse everything into one file that mixes JSON parsing, byte marshalling, and output formatting; equally, do not over-engineer a multi-layer framework for one operation.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in the "Core Features" section are a **black-box contract for the execution adapter**, not the internal data model of the core boundary logic. The core string-transfer logic must not know about JSON, stdin, or stdout. The execution adapter is solely responsible for parsing a JSON command, invoking the core transfer operation, and formatting the neutral output lines.

3. **Adherence to SOLID Design Principles** (scaled to this project's size):
   - **Single Responsibility Principle (SRP):** Separate JSON parsing, the boundary-transfer call, error normalization, and output formatting into distinct units.
   - **Open/Closed Principle (OCP):** Adding a new boundary operation must not require rewriting the existing transfer logic.
   - **Liskov Substitution Principle (LSP):** Any concrete encoder/marshaller must be substitutable wherever the abstract one is expected.
   - **Interface Segregation Principle (ISP):** Keep the transfer interface minimal — a value in, a value out, or a typed failure.
   - **Dependency Inversion Principle (DIP):** The adapter depends on the abstract transfer operation, not on the concrete native-loading details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public transfer operation must read naturally in the target language — a plain "string in, string out" call.
   - **Resilience:** Invalid input must be modeled as a typed failure (a specific error category / Result), never a generic crash. No malformed bytes may reach the native side.

---

## Core Features

### Feature 1: Native String Boundary Transfer

**As a developer**, I want to send a string into a native library and get it back through one operation, so I can move text across the managed/native boundary without hand-writing UTF-8 marshalling and without risking native memory corruption from malformed text.

**Expected Behavior / Usage:**

The execution adapter reads one JSON command object from stdin of the shape `{"op": "take_string", "value": "<string>"}` and invokes the core boundary-transfer operation on `value`. The operation lowers the string to UTF-8 bytes, passes them into the native library, and lifts the returned bytes back to a string. The adapter prints, on stdout, the echoed `op` line followed by an operation-specific result. The boundary's defining behavior is that a string is transferred as a UTF-8 byte sequence (not as opaque managed text), so encodability is enforced at the boundary.

*1.1 Valid Unicode round-trip — text of any plane is preserved byte-for-byte*

When `value` is any string that has a valid UTF-8 representation, the operation returns exactly that string. The adapter prints three lines: `op=take_string`, then `output=<the returned string>`, then `utf8_bytes=<number of UTF-8 bytes in the returned string>`. The byte count is part of the contract: it proves the value crossed the boundary as encoded bytes rather than being short-circuited, and it distinguishes Basic-Multilingual-Plane characters (which encode to fewer bytes) from supplementary-plane characters (which require a surrogate pair on the managed side and more bytes when encoded). The empty string is valid and yields an empty `output` value and a byte count of zero. This must hold for the empty string, a BMP character, and a supplementary-plane (emoji) character alike.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_valid_string_roundtrip.json`

```json
{
    "description": "Send a Unicode string across the foreign-function boundary into the native string-transfer routine and receive it back unchanged. Valid strings of any plane must round-trip byte-for-byte; the reported UTF-8 byte length confirms the value crossed the boundary as encoded bytes rather than being short-circuited. Covers the empty string, a Basic-Multilingual-Plane character, and a supplementary-plane (surrogate-pair) character.",
    "cases": [
        {"input": {"op": "take_string", "value": ""},   "expected_output": "op=take_string\noutput=\nutf8_bytes=0\n"},
        {"input": {"op": "take_string", "value": "愛"},  "expected_output": "op=take_string\noutput=愛\nutf8_bytes=3\n"},
        {"input": {"op": "take_string", "value": "💖"}, "expected_output": "op=take_string\noutput=💖\nutf8_bytes=4\n"}
    ]
}
```

*1.2 Invalid-UTF-8 rejection — unpaired surrogates are refused at the boundary*

When `value` contains a code unit that cannot be encoded as valid UTF-8 — for example an unpaired (lone) UTF-16 surrogate, which managed runtimes permit in a string but which has no valid UTF-8 byte representation — the boundary refuses to transfer it. No malformed bytes are sent to the native side. The adapter prints `op=take_string` followed by the neutral error line `error=invalid_utf8`. The error is reported as a language-neutral category; no host-language exception type, stack trace, or runtime message text appears in the output.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_invalid_utf8_rejection.json`

```json
{
    "description": "Send a string containing an unpaired UTF-16 surrogate code unit into the native string-transfer routine. Because the value cannot be encoded as valid UTF-8, the boundary rejects it and the adapter reports a neutral invalid-UTF-8 error category instead of round-tripping the value.",
    "cases": [
        {"input": {"op": "take_string", "value": "\ud800"}, "expected_output": "op=take_string\nerror=invalid_utf8\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the native string boundary transfer described above — lowering a string to UTF-8, passing it into the native library, lifting the result back, and enforcing UTF-8 validity at the boundary. Its physical structure must align with the "Scale-Driven Code Organization" constraint: small and well-separated, not a single god file mixing concerns, and not an over-engineered framework.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads one JSON command from stdin, invokes the core transfer operation, normalizes any boundary failure into the neutral `error=<category>` line, and prints the result to stdout exactly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core boundary logic.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_valid_string_roundtrip.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_valid_string_roundtrip@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
