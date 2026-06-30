## Product Requirement Document

# Hierarchical-Deterministic Key Derivation Toolkit — Mnemonic, Seed & Extended-Key Generation

## Project Goal

Build a deterministic key-derivation library that turns raw entropy into a human-recoverable mnemonic phrase, turns that phrase back into a cryptographic seed, and derives a tree of payment addresses and extended keys from that seed, so wallet developers can implement standards-compliant account recovery and address generation without hand-rolling the underlying bit-manipulation, checksum, PBKDF2 and elliptic-curve math.

---

## Background & Problem

A self-custody wallet must let a user back up their funds as a short list of ordinary words and later restore full spending capability from those words alone. Doing this correctly requires several precise, interlocking transformations: packing entropy plus a checksum into 11-bit groups that index a fixed dictionary (BIP39 mnemonic encoding), stretching the chosen words into a 512-bit seed with PBKDF2-HMAC-SHA512, and walking a BIP32 hierarchical-deterministic key tree along BIP44 account paths to produce per-address public keys and Base58Check addresses.

Without a shared library, every wallet re-implements these byte-exact algorithms, and any deviation (a wrong checksum, a mis-ordered bit, a wrong salt, an off-by-one in the derivation path) silently produces keys that cannot recover real funds. This toolkit provides one well-defined, deterministic contract for each step: entropy → words, words → validity verdict, words → seed, seed → address/public-key, and seed+path → extended keys. Every output is a stable, language-neutral string (dictionary words, lowercase hex, or Base58Check text) so two independent implementations of the same standard must produce byte-identical results.

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

### Feature 1: Entropy To Mnemonic Phrase

**As a developer**, I want to turn a block of raw entropy into a recoverable word phrase, so I can present a user with a memorable backup of their wallet seed.

**Expected Behavior / Usage:**

The input supplies entropy as a hexadecimal string. The algorithm computes a checksum equal to the leading bits of the SHA-256 hash of the entropy (one checksum bit per 32 bits of entropy), appends the checksum to the entropy bit stream, splits the combined bits into groups of 11, and maps each 11-bit group (a value 0–2047) to a word in a fixed, ordered 2048-word English dictionary. The words are emitted as a single space-separated sentence on one line followed by a newline. The word count is determined entirely by the entropy length: 128 bits (16 bytes) produces 12 words. Empty entropy is invalid and is rejected with the neutral line `error=empty_entropy`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_entropy_to_mnemonic.json`

```json
{
    "description": "Convert a hexadecimal entropy value into a BIP39-style mnemonic word sentence. The entropy is supplied as a hex string; its length in bits determines the number of words produced (128 bits of entropy yields a 12-word sentence). A checksum derived from the SHA-256 hash of the entropy is appended before the bit stream is split into 11-bit groups, each mapping to one word in the fixed 2048-word English list; the words are returned space-separated in order. Supplying empty entropy is rejected with a neutral error.",
    "cases": [
        {"input": {"action": "entropy_to_mnemonic", "entropy": "7787bfe5815e1912a1ec409a56391109"}, "expected_output": "jealous digital west actor thunder matter marble marine olympic range dust banner\n"},
        {"input": {"action": "entropy_to_mnemonic", "entropy": ""}, "expected_output": "error=empty_entropy\n"}
    ]
}
```

---

### Feature 2: Mnemonic Phrase Validation

**As a developer**, I want to check whether a phrase a user typed is structurally a valid mnemonic, so I can reject typos before attempting recovery.

**Expected Behavior / Usage:**

The input supplies a list of words. Validation enforces two structural rules: the number of words must be one of 12, 15, 18, 21, or 24; and every word must be a member of the fixed English dictionary. When both rules hold, the output is the line `valid` followed by a line `word_count=<n>` reporting the number of words. When the word count is not one of the allowed values, the output is `error=invalid_mnemonic_count` followed by `word_count=<n>` reporting the offending count. When the count is acceptable but at least one word is not in the dictionary, the output is `error=invalid_mnemonic_key` followed by `word=<w>`, where `<w>` is the first word, in order, that is not in the dictionary. Each line ends with a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature2_validate_mnemonic.json`

```json
{
    "description": "Validate a candidate mnemonic word list against the structural rules: the count must be one of 12, 15, 18, 21 or 24 words, and every word must belong to the fixed English word list. A well-formed list reports success together with its word count; a list containing a word outside the dictionary is rejected as a key error (reporting the offending word).",
    "cases": [
        {"input": {"action": "validate_mnemonic", "words": ["jealous","digital","west","actor","thunder","matter","marble","marine","olympic","range","dust","banner"]}, "expected_output": "valid\nword_count=12\n"},
        {"input": {"action": "validate_mnemonic", "words": ["jealous","digitalll","west","actor","thunder","matter","marble","marine","olympic","range","dust","banner"]}, "expected_output": "error=invalid_mnemonic_key\nword=digitalll\n"}
    ]
}
```

---

### Feature 3: Mnemonic Phrase To Seed

**As a developer**, I want to stretch a validated phrase into the binary seed, so I can feed deterministic key derivation from a recovered backup.

**Expected Behavior / Usage:**

The input supplies a list of words. The phrase is validated first using the rules of Feature 2, so an invalid word count yields `error=invalid_mnemonic_count` + `word_count=<n>` and an out-of-dictionary word yields `error=invalid_mnemonic_key` + `word=<w>`. When the phrase is valid, the seed is computed with PBKDF2 using HMAC-SHA512 as the pseudo-random function, 2048 iterations, the space-joined phrase (UTF-8) as the password, and the constant ASCII string `mnemonic` as the salt, producing a 64-byte (512-bit) derived key. The seed is emitted as the line `seed=<hex>`, where `<hex>` is the 128-character lowercase hexadecimal encoding of the 64 bytes, followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature3_mnemonic_to_seed.json`

```json
{
    "description": "Derive the 64-byte binary seed from a mnemonic word list using PBKDF2 with HMAC-SHA512, 2048 iterations, the space-joined mnemonic as the password and the constant string \"mnemonic\" as the salt. The word list is validated first, so a disallowed word count is rejected with the same neutral error contract used for validation. On success the 64-byte seed is reported as a lowercase hex string.",
    "cases": [
        {"input": {"action": "mnemonic_to_seed", "words": ["jealous","digital","west","actor","thunder","matter","marble","marine","olympic","range","dust","banner"]}, "expected_output": "seed=6908630f564bd3ca9efb521e72da86727fc78285b15decedb44f40b02474502ed6844958b29465246a618b1b56b4bdffacd1de8b324159e0f7f594c611b0519d\n"},
        {"input": {"action": "mnemonic_to_seed", "words": ["digital","west","actor","thunder","matter","marble","marine","olympic","range","dust","banner"]}, "expected_output": "error=invalid_mnemonic_count\nword_count=11\n"}
    ]
}
```

---

### Feature 4: Address And Public-Key Derivation

**As a developer**, I want to derive a payment address and its public key for a chosen account chain and index, so I can hand out fresh receive and change addresses from a single seed.

**Expected Behavior / Usage:**

The input supplies the binary seed as a hex string, a chain selector, and a numeric address index. Derivation follows the BIP44 path `m/44'/0'/0'/chain/index`, where the apostrophe marks hardened derivation, the external (receive) chain number is `0`, and the internal (change) chain number is `1`. The caller selects the chain by name: `receive` for the external chain and `change` for the internal chain. From the derived key the system computes the compressed (33-byte) public key and the corresponding pay-to-public-key-hash address in Base58Check form. The output is the line `address=<base58check-address>` followed by the line `public_key=<hex>`, where `<hex>` is the 66-character lowercase hexadecimal encoding of the compressed public key. Each line ends with a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature4_address_derivation.json`

```json
{
    "description": "From a binary seed (hex), derive a payment address and its compressed public key at a hierarchical-deterministic BIP44 path of the form m/44'/0'/0'/chain/index, where the external (receive) chain is 0 and the internal (change) chain is 1. The caller selects the chain by name and supplies the address index. The result reports the Base58Check P2PKH address and the 33-byte compressed public key as lowercase hex.",
    "cases": [
        {"input": {"action": "derive_address", "seed": "6908630f564bd3ca9efb521e72da86727fc78285b15decedb44f40b02474502ed6844958b29465246a618b1b56b4bdffacd1de8b324159e0f7f594c611b0519d", "chain": "receive", "index": 0}, "expected_output": "address=188TR7fL2MpqoAMez2VgLgsjZoRcttZvAb\npublic_key=031f4e92f8d1f78d8a149863415690b2c2845fcae3be009f9d55595e4edc00e2ea\n"},
        {"input": {"action": "derive_address", "seed": "6908630f564bd3ca9efb521e72da86727fc78285b15decedb44f40b02474502ed6844958b29465246a618b1b56b4bdffacd1de8b324159e0f7f594c611b0519d", "chain": "change", "index": 0}, "expected_output": "address=14T7kwGvdxrEHgUA28BbcddJi7j4fhWy7Z\npublic_key=0301aeeb78a8ee9201659fcbe8d78e73205e7b26e0e46608e2a661aabe87822ce5\n"}
    ]
}
```

---

### Feature 5: Extended-Key Derivation By Path

**As a developer**, I want to derive the serialized extended private and public keys at an arbitrary derivation path, so I can export account-level keys for watch-only wallets and interoperate with other BIP32 tooling.

**Expected Behavior / Usage:**

The input supplies the binary seed as a hex string and a textual derivation path. A BIP32 master key is built from the seed, then the path is walked one component at a time. The path is slash-separated; a leading `m/` is optional; an empty path, `m`, or `/` denotes the master key itself; and a trailing apostrophe on a component marks hardened derivation. Each component must be a non-negative integer. On success the output is the line `xprv=<base58check>` (the serialized extended private key, which begins with `xprv`) followed by the line `xpub=<base58check>` (the serialized extended public key, which begins with `xpub`), each ending with a newline. If any path component is not a valid integer, derivation fails and the output is `error=invalid_path` followed by `path=<raw-path>`, echoing the original path string verbatim.

**Test Cases:** `rcb_tests/public_test_cases/feature5_extended_key.json`

```json
{
    "description": "Given a binary seed (hex), build the BIP32 master key and derive the extended key at a textual derivation path. The path uses slash-separated numeric child indexes, an optional leading m/, and a trailing apostrophe to mark a hardened index. The derived key is reported as its serialized extended private key (xprv...) and extended public key (xpub...), both Base58Check encoded. A path containing a non-numeric index component is rejected with a neutral error that echoes the raw path.",
    "cases": [
        {"input": {"action": "derive_extended_key", "seed": "6908630f564bd3ca9efb521e72da86727fc78285b15decedb44f40b02474502ed6844958b29465246a618b1b56b4bdffacd1de8b324159e0f7f594c611b0519d", "path": "m/0"}, "expected_output": "xprv=xprv9ubX8LNSQDq5LSMSKyMAmF7rajw2WqonJDcJxYwJmXAApWoQFj4vCg7DZFRrmPVGGc7Jn1oRsX585v2gJqojyVXrseGtk6GccmRDU51fzMX\nxpub=xpub68asXquLEbPNYvRuRztB8P4b8mmWvJXdfSXukwLvKrh9hK8YoGPAkURhQWY9JjmP5Fz8aGMxChcQHKMkfnLWgMaW7LBbnTgTwZb3fVMmfnS\n"},
        {"input": {"action": "derive_extended_key", "seed": "6908630f564bd3ca9efb521e72da86727fc78285b15decedb44f40b02474502ed6844958b29465246a618b1b56b4bdffacd1de8b324159e0f7f594c611b0519d", "path": "m/0/b"}, "expected_output": "error=invalid_path\npath=m/0/b\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the five derivation features above (mnemonic encoding, mnemonic validation, seed stretching, address/public-key derivation, and extended-key derivation). Its physical structure MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the resulting output (or neutral error) to stdout, matching the per-feature contracts above. The request's `action` field selects the operation: `entropy_to_mnemonic`, `validate_mnemonic`, `mnemonic_to_seed`, `derive_address`, or `derive_extended_key`. All hexadecimal outputs are lowercase; all error outputs use neutral `error=<category>` lines plus a single context field, never host-language exception type names.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the chain derivation convention used in DERIVE_ADDRESS
- utilize the BIP32 xprv/xpub encoding rules
