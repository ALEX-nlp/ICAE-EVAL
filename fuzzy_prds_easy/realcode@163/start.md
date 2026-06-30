## Product Requirement Document

# Symmetric Envelope Encryption Service — Context-Scoped Encrypt/Decrypt with Optional Per-Context Key Derivation

## Project Goal

Build a small symmetric encryption service that turns a plaintext string into a self-describing, transportable ciphertext envelope and back again, so developers can protect short secrets with a single configured key without having to manage initialization vectors, padding, or key-derivation plumbing themselves.

---

## Background & Problem

Applications frequently need to encrypt small pieces of sensitive data (a token, a password, a short note) and store or transmit the result. Doing this by hand means picking a block cipher, generating a fresh initialization vector for every message, handling block padding, base64-encoding the parts, and gluing them into something that can be safely stored as text — and then reversing all of that on the way back. Getting any step wrong silently breaks confidentiality or interoperability.

This service hides that machinery behind two operations — encrypt and decrypt — over a fixed configured secret key. It always produces a textual envelope of the form `<base64 iv>:<base64 ciphertext>`, generating a fresh random initialization vector per encryption. It also offers two key modes: a shared-key mode where the configured key is used directly for every caller, and a derived-key mode where a distinct encryption key is deterministically derived from the configured master key plus a caller-supplied context identifier, so that data encrypted on behalf of one context cannot be decrypted on behalf of another.

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

The service is configured with a single secret key, supplied as a base64-encoded byte string, and a boolean flag selecting the key mode. In **shared-key mode** the configured key bytes are used directly as the encryption key for every operation, regardless of the context identifier. In **derived-key mode** the configured key is treated as a master key and a distinct 32-byte encryption key is deterministically derived from it together with the UTF-8 bytes of the caller-supplied context identifier; the same context always derives the same key, while different contexts derive different keys.

An **envelope** is the textual ciphertext produced by encryption: exactly two segments joined by a single colon, where the first segment is the base64 encoding of a freshly generated [a specific constant — ask the PM for the exact integer]-byte random initialization vector and the second segment is the base64 encoding of the block-cipher ciphertext. Plaintext is encoded as UTF-8 and encrypted with a 256-bit-key CBC-mode block cipher using standard block padding, so the ciphertext length is the plaintext length rounded up to the next full [a specific constant — ask the PM for the exact integer]-byte block. Decryption splits the envelope on the colon, base64-decodes both segments, decrypts, and returns the UTF-8 plaintext.

### Feature 1: Lossless Encrypt/Decrypt Round Trip

**As a developer**, I want to encrypt a plaintext and decrypt it back with the same configuration and context, so I can confirm the service is a lossless, self-contained envelope codec under either key mode.

**Expected Behavior / Usage:**

*1.1 Shared-Key Mode — round trip with the configured key used directly*

In shared-key mode, encrypting a plaintext for a context produces an envelope, and decrypting that envelope with the same context returns the original plaintext byte-for-byte. The reported output exposes structural facts about the produced envelope so that the encryption path is observable even though the random initialization vector makes the raw ciphertext non-deterministic: the number of colon-separated segments (always two), the byte length of the decoded initialization vector (always [a specific constant — ask the PM for the exact integer]), and the byte length of the decoded ciphertext (the padded block length of the plaintext), followed by the recovered plaintext.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_roundtrip_shared_key.json`

```json
{
    "description": "A symmetric envelope-encryption service is initialized in shared-key mode (the same secret key is used for every context, with no per-context key derivation). A short plaintext is encrypted for a given context and then immediately decrypted with the same context. The output reports structural facts about the produced envelope and the recovered plaintext. The envelope is a two-segment value: a fresh random initialization vector and the ciphertext, each carried as base64 and joined by a single colon. The initialization vector is always [a specific constant — ask the PM for the exact integer] bytes; the ciphertext is the block-cipher output of the (block-padded) plaintext. Decrypting the envelope with the originating context recovers the exact original plaintext, demonstrating a lossless round trip.",
    "cases": [
        {
            "input": {
                "action": "roundtrip",
                "key": "tWG4dk8ARsETnFL3jCf1xtMVe05imlx9vimER7iky2s=",
                "derivation": false,
                "plaintext": "hello",
                "context": "sa"
            },
            "expected_output": "envelope_segments=2\niv_byte_length=[a specific constant — ask the PM for the exact integer]\nciphertext_byte_length=[a specific constant — ask the PM for the exact integer]\ndecrypted=hello\n"
        }
    ]
}
```

*1.2 Derived-Key Mode — round trip with a per-context derived key*

In derived-key mode, the configured key is a master key and the actual encryption key is derived deterministically from the context identifier. Encrypting a plaintext for a context and then decrypting with the same context still recovers the original plaintext, and the envelope has the identical two-segment shape with a [a specific constant — ask the PM for the exact integer]-byte initialization vector.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_roundtrip_derived_key.json`

```json
{
    "description": "A symmetric envelope-encryption service is initialized in derived-key mode (the configured secret key is treated as a master key, and a distinct encryption key is deterministically derived per context). A short plaintext is encrypted for a given context and then immediately decrypted with the same context. The output reports structural facts about the produced envelope and the recovered plaintext. The envelope has the same two-segment shape as in shared-key mode: a fresh [a specific constant — ask the PM for the exact integer]-byte random initialization vector and the ciphertext, each base64-encoded and joined by a colon. Because the derived key is stable for a fixed context, decrypting with the originating context recovers the exact original plaintext.",
    "cases": [
        {
            "input": {
                "action": "roundtrip",
                "key": "tWG4dk8ARsETnFL3jCf1xtMVe05imlx9vimER7iky2s=",
                "derivation": true,
                "plaintext": "hello",
                "context": "sa"
            },
            "expected_output": "envelope_segments=2\niv_byte_length=[a specific constant — ask the PM for the exact integer]\nciphertext_byte_length=[a specific constant — ask the PM for the exact integer]\ndecrypted=hello\n"
        }
    ]
}
```

---

### Feature 2: Context Scoping of Decryption

**As a developer**, I want the key mode to control whether one context can decrypt another context's data, so I can choose between a shared key for all callers and cryptographic isolation between callers.

**Expected Behavior / Usage:**

*2.1 Shared-Key Mode — any context can decrypt any envelope*

When key derivation is OFF, the context identifier has no effect on the encryption key; every context uses the same key bytes. The same plaintext is encrypted separately for two different contexts, and each resulting envelope is decrypted using the OTHER context. Both cross-context decryptions succeed and recover the original plaintext, demonstrating that shared-key mode does not isolate contexts. The output reports the plaintext recovered when each context decrypts the other context's envelope.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_cross_context_shared_key.json`

```json
{
    "description": "A symmetric envelope-encryption service is initialized in shared-key mode (no per-context key derivation), so every context encrypts and decrypts with the same underlying key. The same plaintext is encrypted independently for two different contexts, producing two envelopes. Each envelope is then decrypted using the OTHER context's identity. Because the underlying key is identical regardless of context, both cross-context decryptions succeed and recover the original plaintext. The output reports the plaintext recovered when each context decrypts the other context's envelope.",
    "cases": [
        {
            "input": {
                "action": "cross_account",
                "key": "tWG4dk8ARsETnFL3jCf1xtMVe05imlx9vimER7iky2s=",
                "derivation": false,
                "plaintext": "hello",
                "context_a": "sa1",
                "context_b": "sa2"
            },
            "expected_output": "decrypted_by_context_a=hello\ndecrypted_by_context_b=hello\n"
        }
    ]
}
```

*2.2 Derived-Key Mode — contexts are cryptographically isolated*

When key derivation is ON, each context derives a different encryption key. An envelope produced on behalf of one context cannot be decrypted on behalf of a different context: the mismatched derived key yields invalid padded output and decryption fails. The failure is surfaced as a neutral, language-agnostic error category (`error=decryption_failed`) rather than a recovered plaintext and rather than any host-runtime exception detail.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_cross_context_derived_key_isolation.json`

```json
{
    "description": "A symmetric envelope-encryption service is initialized in derived-key mode, where each context gets its own deterministically derived encryption key. A previously produced envelope that was encrypted under one originating context is presented for decryption under a DIFFERENT context. Because the derived key for the requesting context does not match the key used to produce the envelope, the cipher cannot recover valid padded plaintext and decryption fails. The failure is surfaced as a neutral error category rather than a recovered value, demonstrating that derived-key mode cryptographically isolates contexts from one another.",
    "cases": [
        {
            "input": {
                "action": "decrypt",
                "key": "tWG4dk8ARsETnFL3jCf1xtMVe05imlx9vimER7iky2s=",
                "derivation": true,
                "ciphertext": "VnZkifeNdxI7NWMbjr/MZg==:qskLf4Z57DC9HBTe6+IEkA==",
                "context": "other"
            },
            "expected_output": "error=decryption_failed\n"
        }
    ]
}
```

---

### Feature 3: Decrypting a Previously Produced Envelope (Stable Format)

**As a developer**, I want to decrypt an envelope that was produced earlier and stored as text, so I can confirm the envelope format and decryption are stable across runs for both key modes.

**Expected Behavior / Usage:**

*3.1 Shared-Key Mode — decrypt a stored envelope*

In shared-key mode, a fixed envelope that was produced earlier with the same configured key decrypts back to its original plaintext. Because the context identifier does not affect the key in this mode, the supplied context is irrelevant to the result.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_decrypt_known_ciphertext_shared_key.json`

```json
{
    "description": "A symmetric envelope-encryption service is initialized in shared-key mode (no per-context key derivation). A fixed, previously produced envelope is supplied for decryption. The envelope is a two-segment value (base64 initialization vector and base64 ciphertext joined by a colon) that was produced earlier with the same secret key. Decrypting it reproduces the original plaintext exactly, confirming that the envelope format and the decryption path are stable across runs and independent of the requesting context in shared-key mode.",
    "cases": [
        {
            "input": {
                "action": "decrypt",
                "key": "tWG4dk8ARsETnFL3jCf1xtMVe05imlx9vimER7iky2s=",
                "derivation": false,
                "ciphertext": "C4gChhspnTa5yVqYmSitrg==:tr0Ke6OGUaUa8KZgMJg14g==",
                "context": "sa"
            },
            "expected_output": "decrypted=hello\n"
        }
    ]
}
```

*3.2 Derived-Key Mode — decrypt a stored envelope with its originating context*

In derived-key mode, a fixed envelope decrypts back to its plaintext only when the same context that produced it is supplied, because the derived key reproduces deterministically for that context.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_decrypt_known_ciphertext_derived_key.json`

```json
{
    "description": "A symmetric envelope-encryption service is initialized in derived-key mode, where the encryption key is deterministically derived from the configured master key and the requesting context. A fixed, previously produced envelope is supplied for decryption together with the SAME context that originally produced it. The envelope is a two-segment value (base64 initialization vector and base64 ciphertext joined by a colon). Because the derived key reproduces deterministically for the originating context, decryption recovers the original plaintext exactly, confirming the derived-key envelope format is stable across runs.",
    "cases": [
        {
            "input": {
                "action": "decrypt",
                "key": "tWG4dk8ARsETnFL3jCf1xtMVe05imlx9vimER7iky2s=",
                "derivation": true,
                "ciphertext": "VnZkifeNdxI7NWMbjr/MZg==:qskLf4Z57DC9HBTe6+IEkA==",
                "context": "sa"
            },
            "expected_output": "decrypted=hello\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the symmetric envelope-encryption service described above — configuration with a base64 secret key and a key-mode flag, the two key modes (shared key used directly; per-context deterministic key derivation), and the two operations (encrypt to an `<base64 iv>:<base64 ciphertext>` envelope with a fresh [a specific constant — ask the PM for the exact integer]-byte initialization vector and standard block padding; decrypt the envelope back to UTF-8 plaintext). The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request object from stdin and prints the resulting contract lines to stdout. The request's `action` selects behavior:
   - `roundtrip` — configure the service from `key` (base64) and `derivation` (bool), encrypt `plaintext` for `context`, then decrypt the produced envelope with the same `context`. Print `envelope_segments=<n>`, `iv_byte_length=<n>`, `ciphertext_byte_length=<n>`, and `decrypted=<plaintext>`, each on its own line.
   - `cross_account` — encrypt `plaintext` separately for `context_a` and `context_b`, then decrypt each context's envelope using the other context. Print `decrypted_by_context_a=<value>` and `decrypted_by_context_b=<value>` (where context A decrypts context B's envelope and vice versa).
   - `decrypt` — decrypt the supplied `ciphertext` envelope under `context`. On success print `decrypted=<plaintext>`; on any decryption or format failure print a neutral `error=<category>` line (`error=decryption_failed` when the envelope cannot be decrypted with the effective key, `error=invalid_envelope_format` when the envelope is not exactly two colon-separated base64 segments). Native runtime exception types and messages MUST NOT appear in the output.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the salt derivation logic used in the ring-based KDF
- use the same line termination handler as the log output module
