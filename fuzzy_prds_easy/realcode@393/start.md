## Product Requirement Document

# Bitcoin Primitives Toolkit - Encoding, Hashing & Key Management Library

## Project Goal

Build a self-contained library that implements the low-level building blocks of a Bitcoin-style cryptocurrency: byte/string encodings, cryptographic digests, arbitrary-precision integers, script opcodes, deterministic key derivation, and address handling. The library lets developers encode/decode wallet data, derive keys, and build addresses with exact, reproducible, spec-compliant results, without re-implementing fragile binary formats and elliptic-curve math by hand.

---

## Background & Problem

Bitcoin-style systems rely on a stack of precise, unforgiving wire formats: a custom Base58 alphabet, a checksummed Base58Check envelope, variable-length integers, sign-magnitude script numbers, BIP32 hierarchical key derivation, BIP39 mnemonic seeds, and version-tagged addresses. A single off-by-one byte, wrong endianness, or missing checksum produces silently invalid data that can cause irreversible loss of funds.

Without a library like this, developers must hand-roll each format and curve operation, duplicating error-prone boilerplate across projects and re-discovering the same edge cases (leading zero bytes, hardened derivation, compressed vs. uncompressed keys, network mismatches). With this library, all of these primitives are exposed behind a small, idiomatic interface that produces deterministic, test-vector-verified outputs and surfaces well-modeled errors for malformed input.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-domain library (encodings, hashing, big-number math, script, keys, addresses, mnemonics). It MUST be organized as a multi-file repository with clear separation between domains (e.g. an `encoding/` area, a `crypto/` area, a key/address area). It MUST NOT be a single "god file". Do not over-engineer individual primitives, but keep each domain in its own cohesive unit.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in "Core Features" are a **black-box contract for an execution adapter**, not the library's internal data model. The core primitives must expose ordinary, idiomatic methods (e.g. encode a buffer, derive a child key) and must know nothing about stdin/stdout or JSON. A thin execution adapter is solely responsible for parsing a JSON command, calling the matching core method, and rendering the line-oriented stdout contract.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Keep parsing, the codec/crypto core, error normalization, and output formatting in distinct units.
   - **Open/Closed Principle (OCP):** Adding a new encoding or hash must not require editing unrelated primitives.
   - **Liskov Substitution Principle (LSP):** Key types that share an interface (e.g. extended private vs. public keys) must be substitutable where that interface is expected.
   - **Interface Segregation Principle (ISP):** Keep per-primitive interfaces small and focused.
   - **Dependency Inversion Principle (DIP):** The adapter depends on the core's abstractions, never the reverse.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of each primitive must be elegant and idiomatic to the target language, hiding internal byte juggling.
   - **Resilience:** Malformed inputs (bad checksum, too-short string, off-curve point, unknown opcode, invalid mnemonic) must be modeled as well-typed errors, not generic crashes. The execution adapter MUST normalize every error into a language-neutral category line (see each feature for the exact category) and MUST NOT leak host-language runtime identity into stdout.

---

## Core Features

### Feature 1: Base58 Encoding

**As a developer**, I want to convert arbitrary byte buffers to and from the Bitcoin Base58 alphabet, so I can render and parse compact, human-friendly identifiers.

**Expected Behavior / Usage:**

*1.1 Base58 Encode/Decode — buffer ⇄ Base58 string*

Encoding takes a byte buffer (supplied as a hex string) and returns its Base58 representation; decoding takes a Base58 string and returns the original bytes as hex. Leading zero bytes are preserved across the round-trip. Output is a single line `base58=<string>` for encoding and `hex=<string>` for decoding.

**Test Cases:** `rcb_tests/public_test_cases/feature1_base58_encode_decode.json`

```json
{
    "description": "Round-trip arbitrary byte buffers (given as hex) through Base58 (the Bitcoin alphabet, no checksum). Encoding maps hex bytes to a Base58 string; decoding maps a Base58 string back to the original hex bytes. Leading zero bytes are preserved.",
    "cases": [
        {"input": {"op": "base58.encode", "hex": "00010203fdfeff"}, "expected_output": "base58=1W7N4RuG\n"},
        {"input": {"op": "base58.decode", "text": "1W7N4RuG"}, "expected_output": "hex=00010203fdfeff\n"}
    ]
}
```

*1.2 Base58 Alphabet Validation — character set check*

Validation reports whether a candidate string is composed solely of characters from the Base58 alphabet. Output is `valid=[the three specific boolean comparisons for integer relationship]` or `valid=false`. Strings containing symbols outside the alphabet are rejected.

**Test Cases:** `rcb_tests/public_test_cases/feature1_base58_validate.json`

```json
{
    "description": "Check whether a candidate string contains only characters from the Base58 alphabet. Returns a boolean. Strings containing symbols outside the alphabet are rejected.",
    "cases": [
        {"input": {"op": "base58.validate", "text": "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"}, "expected_output": "valid=[the three specific boolean comparisons for integer relationship]\n"},
        {"input": {"op": "base58.validate", "text": "!@#%^$&*()\\"}, "expected_output": "valid=false\n"}
    ]
}
```

---

### Feature 2: Base58Check Envelope

**As a developer**, I want a checksummed Base58 envelope, so I can detect typos and corruption in serialized wallet data before acting on it.

**Expected Behavior / Usage:**

*2.1 Base58Check Encode/Decode — payload ⇄ checksummed string*

Encoding appends a 4-byte checksum (the first 4 bytes of the double SHA-256 of the payload) to the payload, then Base58-encodes the whole. Decoding verifies that checksum and, on success, returns the original payload hex. Output is `base58check=<string>` for encoding and `hex=<string>` for decoding.

**Test Cases:** `rcb_tests/public_test_cases/feature2_base58check_encode_decode.json`

```json
{
    "description": "Round-trip byte buffers (given as hex) through Base58Check, which appends a 4-byte double-SHA256 checksum before Base58 encoding. Decoding verifies and strips the checksum, returning the original payload hex.",
    "cases": [
        {"input": {"op": "base58check.encode", "hex": "00010203fdfeff"}, "expected_output": "base58check=14HV44ipwoaqfg\n"},
        {"input": {"op": "base58check.decode", "text": "14HV44ipwoaqfg"}, "expected_output": "hex=00010203fdfeff\n"}
    ]
}
```

*2.2 Base58Check Decode Errors — distinct failure categories*

Decoding distinguishes two malformed-input categories: an input too short to contain a checksum (`error=[a specific error code for underflow condition — confirm exact casing]`) and an input whose trailing checksum does not match the recomputed checksum of the payload (`error=[a specific error code indicating checksum failure — verify spelling with the team]`).

**Test Cases:** `rcb_tests/public_test_cases/feature2_base58check_errors.json`

```json
{
    "description": "Decoding a Base58Check string surfaces distinct error categories: an input shorter than the checksum length, and an input whose trailing checksum does not match the recomputed checksum of the payload.",
    "cases": [
        {"input": {"op": "base58check.decode", "text": "1"}, "expected_output": "error=[a specific error code for underflow condition — confirm exact casing]\n"},
        {"input": {"op": "base58check.decode", "text": "24HV44ipwoaqfg"}, "expected_output": "error=[a specific error code indicating checksum failure — verify spelling with the team]\n"}
    ]
}
```

*2.3 Base58Check Checksum Validation — boolean check without decoding*

Validation reports whether the trailing checksum of an encoded string is correct, without returning the payload. Output is `valid=[the three specific boolean comparisons for integer relationship]` or `valid=false`. Appending a stray character breaks the checksum.

**Test Cases:** `rcb_tests/public_test_cases/feature2_base58check_validate.json`

```json
{
    "description": "Validate whether a Base58Check-encoded string has a correct trailing checksum, without decoding the payload. Returns a boolean; appending a stray character breaks the checksum.",
    "cases": [
        {"input": {"op": "base58check.validate", "text": "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy"}, "expected_output": "valid=[the three specific boolean comparisons for integer relationship]\n"},
        {"input": {"op": "base58check.validate", "text": "3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLya"}, "expected_output": "valid=false\n"}
    ]
}
```

---

### Feature 3: Cryptographic Digests

**As a developer**, I want canonical hash and HMAC primitives over byte buffers, so I can build commitments, addresses and authentication codes against known test vectors.

**Expected Behavior / Usage:** Every digest takes a message as a hex string and returns its digest as lowercase hex on a single `digest=<hex>` line. HMAC variants additionally take a hex key. The empty input is a valid message.

*3.1 SHA-256 — 32-byte digest*

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_hash_sha256.json`

```json
{
    "description": "Compute the SHA-256 digest of a message supplied as hex. Output is the 32-byte digest in lowercase hex.",
    "cases": [
        {"input": {"op": "hash.sha256", "hex": "00010203fdfeff"}, "expected_output": "digest=6f2c7b22fd1626998287b3636089087961091de80311b9279c4033ec678a83e8\n"}
    ]
}
```

*3.2 Double SHA-256 — SHA-256 applied twice*

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_hash_sha256d.json`

```json
{
    "description": "Compute the double SHA-256 digest (SHA-256 applied twice) of a hex message. Output is the 32-byte digest in lowercase hex.",
    "cases": [
        {"input": {"op": "hash.sha256d", "hex": "00010203fdfeff"}, "expected_output": "digest=be586c8b20dee549bdd66018c7a79e2b67bb88b7c7d428fa4c970976d2bec5ba\n"}
    ]
}
```

*3.3 HASH160 — RIPEMD-160 of SHA-256*

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_hash_hash160.json`

```json
{
    "description": "Compute the Bitcoin HASH160 digest: RIPEMD-160 applied to the SHA-256 of a hex message. Output is the 20-byte digest in lowercase hex.",
    "cases": [
        {"input": {"op": "hash.sha256ripemd160", "hex": "00010203fdfeff"}, "expected_output": "digest=7322e2bd8535e476c092934e16a6169ca9b707ec\n"}
    ]
}
```

*3.4 RIPEMD-160 — 20-byte digest*

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_hash_ripemd160.json`

```json
{
    "description": "Compute the RIPEMD-160 digest of a hex message. Output is the 20-byte digest in lowercase hex.",
    "cases": [
        {"input": {"op": "hash.ripemd160", "hex": "00010203fdfeff"}, "expected_output": "digest=fa0f4565ff776fee0034c713cbf48b5ec06b7f5c\n"}
    ]
}
```

*3.5 SHA-1 — 20-byte digest*

The empty input yields the well-known empty SHA-1 digest.

**Test Cases:** `rcb_tests/public_test_cases/feature3_5_hash_sha1.json`

```json
{
    "description": "Compute the SHA-1 digest of a hex message. Output is the 20-byte digest in lowercase hex. The empty input yields the well-known empty SHA-1 digest.",
    "cases": [
        {"input": {"op": "hash.sha1", "hex": "00010203fdfeff"}, "expected_output": "digest=de69b8a4a5604d0486e6420db81e39eb464a17b2\n"},
        {"input": {"op": "hash.sha1", "hex": ""}, "expected_output": "digest=da39a3ee5e6b4b0d3255bfef95601890afd80709\n"}
    ]
}
```

*3.6 SHA-512 — 64-byte digest*

**Test Cases:** `rcb_tests/public_test_cases/feature3_6_hash_sha512.json`

```json
{
    "description": "Compute the SHA-512 digest of a hex message. Output is the 64-byte digest in lowercase hex.",
    "cases": [
        {"input": {"op": "hash.sha512", "hex": "00010203fdfeff"}, "expected_output": "digest=c0530aa32048f4904ae162bc14b9eb535eab6c465e960130005feddb71613e7d62aea75f7d3333ba06e805fc8e45681454524e3f8050969fe5a5f7f2392e31d0\n"}
    ]
}
```

*3.7 HMAC-SHA256 — keyed MAC*

**Test Cases:** `rcb_tests/public_test_cases/feature3_7_hash_sha256hmac.json`

```json
{
    "description": "Compute the HMAC-SHA256 of a hex message under a hex key. Output is the 32-byte MAC in lowercase hex. Covers the empty key/empty data vector and a standard \"quick brown fox\" vector.",
    "cases": [
        {"input": {"op": "hash.sha256hmac", "hex": "", "key": ""}, "expected_output": "digest=b613679a0814d9ec772f95d778c35fc5ff1697c493715653c6c712144292c5ad\n"},
        {"input": {"op": "hash.sha256hmac", "hex": "54686520717569636b2062726f776e20666f78206a756d7073206f76657220746865206c617a7920646f67", "key": "6b6579"}, "expected_output": "digest=f7bc83f430538424b13298e6aa6fb143ef4d59a14946175997479dbc2d1a3cd8\n"}
    ]
}
```

*3.8 HMAC-SHA512 — keyed MAC*

**Test Cases:** `rcb_tests/public_test_cases/feature3_8_hash_sha512hmac.json`

```json
{
    "description": "Compute the HMAC-SHA512 of a hex message under a hex key. Output is the 64-byte MAC in lowercase hex.",
    "cases": [
        {"input": {"op": "hash.sha512hmac", "hex": "", "key": ""}, "expected_output": "digest=b936cee86c9f87aa5d3c6f2e84cb5a4239a5fe50480a6ec66b70ab5b1f4ac6730c6c515421b327ec1d69402e53dfb49ad7381eb067b338fd7b0cb22247225d47\n"}
    ]
}
```

---

### Feature 4: Variable-Length Integer Codec

**As a developer**, I want to encode counts and lengths compactly, so I can serialize and parse the variable-length integer fields used throughout Bitcoin wire formats.

**Expected Behavior / Usage:**

A non-negative integer is encoded to its varint wire bytes (returned as hex), and varint wire bytes are decoded back to an integer. Values below 0xFD encode as a single byte. Output is `hex=<varint hex>` for encoding and `number=<int>` for decoding.

**Test Cases:** `rcb_tests/public_test_cases/feature4_varint_codec.json`

```json
{
    "description": "Encode a non-negative integer into a Bitcoin variable-length integer (varint) wire form, and decode varint wire bytes back to an integer. Values below 0xFD encode as a single byte.",
    "cases": [
        {"input": {"op": "varint.encode", "number": 5}, "expected_output": "hex=05\n"},
        {"input": {"op": "varint.decode", "hex": "05"}, "expected_output": "number=5\n"}
    ]
}
```

---

### Feature 5: Arbitrary-Precision Integers

**As a developer**, I want big-integer arithmetic and the Bitcoin-specific serialization formats, so I can handle values that exceed native integer range and the exact byte layouts Bitcoin scripts expect.

**Expected Behavior / Usage:** Operands and results that may exceed native range are carried as base-10 strings.

*5.1 Arithmetic — addition and subtraction*

Adds or subtracts two integers given as base-10 strings and returns the base-10 result on a `result=<dec>` line.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_bignumber_arithmetic.json`

```json
{
    "description": "Arbitrary-precision integer arithmetic. Operands are supplied as base-10 strings (so they may exceed native integer range) and the result is returned as a base-10 string. Supports addition and subtraction.",
    "cases": [
        {"input": {"op": "bignumber.add", "a": "50", "b": "75"}, "expected_output": "result=125\n"},
        {"input": {"op": "bignumber.sub", "a": "50", "b": "25"}, "expected_output": "result=25\n"}
    ]
}
```

*5.2 Comparison — ordering and equality*

Compares two integers (base-10 strings) and returns the greater-than, less-than and equality relations as three boolean lines `gt=`, `lt=`, `eq=`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_bignumber_compare.json`

```json
{
    "description": "Compare two arbitrary-precision integers given as base-10 strings, returning the greater-than, less-than and equality relations as three boolean lines.",
    "cases": [
        {"input": {"op": "bignumber.compare", "a": "1", "b": "0"}, "expected_output": "gt=[the three specific boolean comparisons for integer relationship]\nlt=false\neq=false\n"},
        {"input": {"op": "bignumber.compare", "a": "24023452345398529485723980457", "b": "5"}, "expected_output": "gt=[the three specific boolean comparisons for integer relationship]\nlt=false\neq=false\n"}
    ]
}
```

*5.3 Script-Number Buffer — signed sign-magnitude codec*

Converts an integer to/from the Bitcoin script-number buffer encoding (sign-magnitude, little-endian, with the sign carried in the high bit of the most significant byte). Negative numbers set the high bit. Output is `hex=<scriptnum hex>` for encoding and `number=<int>` for decoding. The encoding round-trips losslessly.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_bignumber_scriptnum.json`

```json
{
    "description": "Convert an integer to/from the Bitcoin script-number buffer encoding (sign-magnitude, little-endian, with a sign bit in the most significant byte). Negative numbers set the high bit. The encoding round-trips losslessly.",
    "cases": [
        {"input": {"op": "bignumber.to_scriptnum", "number": 1000}, "expected_output": "hex=e803\n"},
        {"input": {"op": "bignumber.to_scriptnum", "number": -1000}, "expected_output": "hex=e883\n"},
        {"input": {"op": "bignumber.from_scriptnum", "hex": "e883"}, "expected_output": "number=-1000\n"}
    ]
}
```

*5.4 Fixed-Width Buffer — sized, endian-aware conversion*

Converts an integer (base-10 string) to a fixed-width byte buffer and back, with selectable byte width (`size`) and byte order (`endian`: `big` or `little`). Output is `hex=<fixed-width hex>` for encoding and `result=<dec>` for decoding.

**Test Cases:** `rcb_tests/public_test_cases/feature5_4_bignumber_buffer.json`

```json
{
    "description": "Convert an integer (base-10 string) to a fixed-width byte buffer and back, with selectable byte width (size) and byte order (endian: big or little). The width is padded/right-sized as requested.",
    "cases": [
        {"input": {"op": "bignumber.to_buffer", "dec": "1", "size": 4}, "expected_output": "hex=00000001\n"},
        {"input": {"op": "bignumber.to_buffer", "dec": "1", "size": 4, "endian": "little"}, "expected_output": "hex=01000000\n"},
        {"input": {"op": "bignumber.from_buffer", "hex": "0100", "endian": "big"}, "expected_output": "result=256\n"}
    ]
}
```

---

### Feature 6: Script Opcode Mapping

**As a developer**, I want to translate between script opcode byte values and their canonical names, so I can read and write scripts in human-readable form.

**Expected Behavior / Usage:**

Maps a numeric opcode value to its canonical `OP_*` name and a name back to its byte value. Byte 0 maps to `OP_0`, 96 to `OP_16`, 97 to `OP_NOP`. Output is `name=<OP_*>` or `number=<int>`. An unknown opcode name is rejected with `error=invalid_opcode`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_opcode_mapping.json`

```json
{
    "description": "Map between Bitcoin script opcode byte values and their canonical OP_* names. Numeric 0 maps to OP_0, 96 to OP_16, 97 to OP_NOP; names map back to their byte value. An unknown opcode name is rejected.",
    "cases": [
        {"input": {"op": "opcode.to_name", "number": 0}, "expected_output": "name=OP_0\n"},
        {"input": {"op": "opcode.to_name", "number": 97}, "expected_output": "name=OP_NOP\n"},
        {"input": {"op": "opcode.to_number", "name": "OP_NOP"}, "expected_output": "number=97\n"},
        {"input": {"op": "opcode.to_number", "name": "OP_SATOSHI"}, "expected_output": "error=invalid_opcode\n"}
    ]
}
```

---

### Feature 7: BIP39 Mnemonic Seeds

**As a developer**, I want to turn entropy into recoverable word phrases and derive seeds from them, so I can back up and restore wallets with human-writable words.

**Expected Behavior / Usage:** A language is selected by a neutral tag: `english` (default), `spanish`, `japanese`, `chinese`, `french`, `italian`.

*7.1 Mnemonic from Entropy — entropy bytes to phrase*

Derives a mnemonic phrase from raw entropy bytes (hex) using the selected wordlist. The phrase length scales with entropy length (128 bits → 12 words). Output is `phrase=<space-separated words>`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_mnemonic_from_entropy.json`

```json
{
    "description": "Derive a BIP39 mnemonic phrase from raw entropy bytes (given as hex) using a selected language wordlist. The phrase length scales with entropy length (128 bits -> 12 words).",
    "cases": [
        {"input": {"op": "mnemonic.from_entropy", "hex": "00000000000000000000000000000000", "lang": "english"}, "expected_output": "phrase=abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about\n"},
        {"input": {"op": "mnemonic.from_entropy", "hex": "7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f7f", "lang": "english"}, "expected_output": "phrase=legal winner thank year wave sausage worth useful legal winner thank yellow\n"}
    ]
}
```

*7.2 Seed from Mnemonic — phrase + passphrase to 64-byte seed*

Derives the 64-byte seed from a phrase and an optional passphrase (which salts the derivation). Output is `seed=<64-byte hex>`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_mnemonic_to_seed.json`

```json
{
    "description": "Derive the 64-byte BIP39 seed from a mnemonic phrase and an optional passphrase. Output is the seed in lowercase hex. The passphrase salts the PBKDF2 derivation.",
    "cases": [
        {"input": {"op": "mnemonic.to_seed", "phrase": "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about", "passphrase": "TREZOR"}, "expected_output": "seed=c55257c360c07c72029aebc1b53c05ed0362ada38ead3e3e9efa3708e53495531f09a6987599d18264c1e1c92f2cf141630c7a3c4ab7c81b2f001698e7463b04\n"},
        {"input": {"op": "mnemonic.to_seed", "phrase": "legal winner thank year wave sausage worth useful legal winner thank yellow", "passphrase": "TREZOR"}, "expected_output": "seed=2e8905819b8723fe2c1d161860e5ee1830318dbf49a83bd451cfb8440c28bd6fa457fe1296106559a3c80937a1c1069be3a3a5bd381ee6260e8d9739fce1f607\n"}
    ]
}
```

*7.3 Mnemonic Validation — well-formedness check*

Reports whether a phrase is a well-formed mnemonic for a given language (correct words and checksum). Output is `valid=[the three specific boolean comparisons for integer relationship]`/`valid=false`. A phrase with a wrong checksum or non-wordlist tokens is invalid.

**Test Cases:** `rcb_tests/public_test_cases/feature7_3_mnemonic_validate.json`

```json
{
    "description": "Validate whether a phrase is a well-formed BIP39 mnemonic for a given language (correct words and checksum). Returns a boolean; a phrase with a wrong checksum or non-wordlist tokens is invalid.",
    "cases": [
        {"input": {"op": "mnemonic.validate", "phrase": "afirmar diseño hielo fideo etapa ogro cambio fideo toalla pomelo número buscar", "lang": "spanish"}, "expected_output": "valid=[the three specific boolean comparisons for integer relationship]\n"},
        {"input": {"op": "mnemonic.validate", "phrase": "afirmar diseño hielo fideo etapa ogro cambio fideo hielo pomelo número buscar", "lang": "spanish"}, "expected_output": "valid=false\n"},
        {"input": {"op": "mnemonic.validate", "phrase": "totally invalid phrase", "lang": "english"}, "expected_output": "valid=false\n"}
    ]
}
```

*7.4 Wordlist Introspection — size and first word*

Reports the size and first entry of a language wordlist. Each supported language provides exactly 2048 words; the first word is language specific. Output is `count=<int>` then `first=<word>`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_4_mnemonic_wordlist.json`

```json
{
    "description": "Report the size and first entry of a language wordlist. Each supported language provides exactly 2048 words; the first word is language specific.",
    "cases": [
        {"input": {"op": "mnemonic.wordlist_info", "lang": "english"}, "expected_output": "count=2048\nfirst=abandon\n"},
        {"input": {"op": "mnemonic.wordlist_info", "lang": "spanish"}, "expected_output": "count=2048\nfirst=ábaco\n"}
    ]
}
```

---

### Feature 8: Private Keys & WIF

**As a developer**, I want to import/export private keys in Wallet Import Format and derive their public keys and addresses, so I can manage spending keys interoperably.

**Expected Behavior / Usage:** A private key is supplied either as a 32-byte hex scalar or as a WIF string.

*8.1 Public Key from Private Key — scalar to compressed public key*

Derives the compressed public key from a 32-byte hex scalar. Output is `public_key=<33-byte hex>`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_privatekey_to_public.json`

```json
{
    "description": "Derive the compressed public key from a 32-byte private key scalar given as hex. Output is the 33-byte compressed public key in hex.",
    "cases": [
        {"input": {"op": "privatekey.from_hex_to_public", "hex": "906977a061af29276e40bf377042ffbde414e496ae2260bbf1fa9d085637bfff"}, "expected_output": "public_key=02a1633cafcc01ebfb6d78e39f687a1f0995c62fc95f51ead10a02ee0be551b5dc\n"}
    ]
}
```

*8.2 WIF Introspection — network and compression flags*

Parses a WIF string and reports its network and whether it encodes a compressed public key. Output is `network=<livenet|testnet>` then `compressed=<bool>`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_privatekey_wif_info.json`

```json
{
    "description": "Parse a WIF (Wallet Import Format) private key string and report its network (livenet/testnet) and whether it encodes a compressed public key.",
    "cases": [
        {"input": {"op": "privatekey.wif_info", "wif": "L3T1s1TYP9oyhHpXgkyLoJFGniEgkv2Jhi138d7R2yJ9F4QdDU2m"}, "expected_output": "network=livenet\ncompressed=[the three specific boolean comparisons for integer relationship]\n"},
        {"input": {"op": "privatekey.wif_info", "wif": "5JxgQaFM1FMd38cd14e3mbdxsdSa9iM2BV6DHBYsvGzxkTNQ7Un"}, "expected_output": "network=livenet\ncompressed=false\n"}
    ]
}
```

*8.3 Address from Private Key — WIF to P2PKH address*

Derives the P2PKH address of a WIF private key, reporting the address and its network (inferred from the WIF version byte). Output is `address=<base58>` then `network=<...>`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_3_privatekey_to_address.json`

```json
{
    "description": "Derive the P2PKH address of a WIF private key, reporting the address string and its network. The network is inferred from the WIF version byte.",
    "cases": [
        {"input": {"op": "privatekey.to_address", "wif": "L3T1s1TYP9oyhHpXgkyLoJFGniEgkv2Jhi138d7R2yJ9F4QdDU2m"}, "expected_output": "address=1A6ut1tWnUq1SEQLMr4ttDh24wcbJ5o9TT\nnetwork=livenet\n"},
        {"input": {"op": "privatekey.to_address", "wif": "cR4qogdN9UxLZJXCNFNwDRRZNeLRWuds9TTSuLNweFVjiaE4gPaq"}, "expected_output": "address=mtX8nPZZdJ8d3QNLRJ1oJTiEi26Sj6LQXS\nnetwork=testnet\n"}
    ]
}
```

*8.4 WIF Round-Trip — re-encode preserving network and compression*

Re-encodes a private key parsed from WIF back to WIF, preserving the network and compression flag. Both compressed and uncompressed WIFs round-trip exactly. Output is `wif=<base58>`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_4_privatekey_wif_roundtrip.json`

```json
{
    "description": "Re-encode a private key parsed from WIF back to WIF, preserving the network and compression flag. Both compressed and uncompressed WIFs round-trip exactly.",
    "cases": [
        {"input": {"op": "privatekey.to_wif", "wif": "L2Gkw3kKJ6N24QcDuH4XDqt9cTqsKTVNDGz1CRZhk9cq4auDUbJy"}, "expected_output": "wif=L2Gkw3kKJ6N24QcDuH4XDqt9cTqsKTVNDGz1CRZhk9cq4auDUbJy\n"},
        {"input": {"op": "privatekey.to_wif", "wif": "5JxgQaFM1FMd38cd14e3mbdxsdSa9iM2BV6DHBYsvGzxkTNQ7Un"}, "expected_output": "wif=5JxgQaFM1FMd38cd14e3mbdxsdSa9iM2BV6DHBYsvGzxkTNQ7Un\n"}
    ]
}
```

---

### Feature 9: Public Keys & Curve Points

**As a developer**, I want to parse serialized public keys, inspect their curve coordinates, and reject invalid points, so I can safely handle keys received from third parties.

**Expected Behavior / Usage:** A public key is supplied as serialized hex (compressed 33-byte or uncompressed 65-byte).

*9.1 Public Key from Private Key — scalar to serialized public key*

Derives the compressed public key from a private key scalar (hex). Output is `public_key=<hex>`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_1_publickey_from_private.json`

```json
{
    "description": "Derive the compressed public key from a private key scalar (hex) and return its serialized hex. Equivalent known-answer vectors are produced for documented private keys.",
    "cases": [
        {"input": {"op": "publickey.from_private", "hex": "6d1229a6b24c2e775c062870ad26bc261051e0198c67203167273c7c62538846"}, "expected_output": "public_key=03d6106302d2698d6a41e9c9a114269e7be7c6a0081317de444bb2980bf9265a01\n"}
    ]
}
```

*9.2 Public Key Info — re-serialization and compression*

Parses a serialized public key and reports its canonical re-serialization plus whether it is compressed. Output is `serialized=<hex>` then `compressed=<bool>`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_2_publickey_info.json`

```json
{
    "description": "Parse a serialized public key (compressed 33-byte or uncompressed 65-byte hex) and report its canonical re-serialization plus whether it is compressed.",
    "cases": [
        {"input": {"op": "publickey.info", "hex": "03d6106302d2698d6a41e9c9a114269e7be7c6a0081317de444bb2980bf9265a01"}, "expected_output": "serialized=03d6106302d2698d6a41e9c9a114269e7be7c6a0081317de444bb2980bf9265a01\ncompressed=[the three specific boolean comparisons for integer relationship]\n"},
        {"input": {"op": "publickey.info", "hex": "0485e9737a74c30a873f74df05124f2aa6f53042c2fc0a130d6cbd7d16b944b004833fef26c8be4c4823754869ff4e46755b85d851077771c220e2610496a29d98"}, "expected_output": "serialized=0485e9737a74c30a873f74df05124f2aa6f53042c2fc0a130d6cbd7d16b944b004833fef26c8be4c4823754869ff4e46755b85d851077771c220e2610496a29d98\ncompressed=false\n"}
    ]
}
```

*9.3 Curve Coordinates — affine X and Y*

Recovers the affine X and Y coordinates (hex) of the point encoded by a serialized public key. Output is `x=<hex>` then `y=<hex>`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_3_publickey_coordinates.json`

```json
{
    "description": "Recover the affine X and Y coordinates (as hex) of the elliptic-curve point encoded by a serialized public key.",
    "cases": [
        {"input": {"op": "publickey.coordinates", "hex": "03d6106302d2698d6a41e9c9a114269e7be7c6a0081317de444bb2980bf9265a01"}, "expected_output": "x=d6106302d2698d6a41e9c9a114269e7be7c6a0081317de444bb2980bf9265a01\ny=e05fb262e64b108991a29979809fcef9d3e70cafceb3248c922c17d83d66bc9d\n"}
    ]
}
```

*9.4 Invalid Point Rejection — off-curve coordinates*

Rejects a serialized public key whose encoded coordinates do not satisfy the curve equation, reporting `error=point_not_on_curve`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_4_publickey_invalid_point.json`

```json
{
    "description": "Reject a serialized public key whose encoded coordinates do not satisfy the secp256k1 curve equation. The error is reported as a point-not-on-curve category.",
    "cases": [
        {"input": {"op": "publickey.info", "hex": "0400000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000"}, "expected_output": "error=point_not_on_curve\n"}
    ]
}
```

---

### Feature 10: Addresses

**As a developer**, I want to classify, validate and build addresses across networks and types, so I can route payments correctly and reject mismatched addresses.

**Expected Behavior / Usage:** Addresses are Base58Check strings carrying a network (livenet/testnet), a type (`pubkeyhash` for P2PKH, `scripthash` for P2SH) and a 20-byte hash.

*10.1 Address Classification — network, type and hash*

Classifies an address and reports its network, type and embedded 20-byte hash. Output is `network=<...>`, `type=<...>`, `hash=<hex>`.

**Test Cases:** `rcb_tests/public_test_cases/feature10_1_address_classify.json`

```json
{
    "description": "Classify a Base58Check address: report its network (livenet/testnet), its type (pubkeyhash for P2PKH, scripthash for P2SH) and its embedded 20-byte hash as hex.",
    "cases": [
        {"input": {"op": "address.classify", "address": "13k3vneZ3yvZnc9dNWYH2RJRFsagTfAERv"}, "expected_output": "network=livenet\ntype=pubkeyhash\nhash=1e1494e15afa231d299f5e3ced336169cfcbd36e\n"},
        {"input": {"op": "address.classify", "address": "37BahqRsFrAd3qLiNNwLNV3AWMRD7itxTo"}, "expected_output": "network=livenet\ntype=scripthash\nhash=3c3fa3d4adcaf8f52d5b1843975e122548269937\n"},
        {"input": {"op": "address.classify", "address": "mtX8nPZZdJ8d3QNLRJ1oJTiEi26Sj6LQXS"}, "expected_output": "network=testnet\ntype=pubkeyhash\nhash=8ea263fd94aa5b0238982d4b5e05ba806a34691f\n"}
    ]
}
```

*10.2 Address Validation — network-scoped boolean*

Reports whether a string is a valid address for a given network. Output is `valid=[the three specific boolean comparisons for integer relationship]`/`valid=false`. A livenet address is invalid against testnet.

**Test Cases:** `rcb_tests/public_test_cases/feature10_2_address_is_valid.json`

```json
{
    "description": "Check whether a string is a valid address for a given network. Returns a boolean; a livenet address is invalid when checked against testnet.",
    "cases": [
        {"input": {"op": "address.is_valid", "address": "37BahqRsFrAd3qLiNNwLNV3AWMRD7itxTo", "network": "livenet"}, "expected_output": "valid=[the three specific boolean comparisons for integer relationship]\n"},
        {"input": {"op": "address.is_valid", "address": "37BahqRsFrAd3qLiNNwLNV3AWMRD7itxTo", "network": "testnet"}, "expected_output": "valid=false\n"}
    ]
}
```

*10.3 Address from Public Key — P2PKH derivation*

Builds the P2PKH address for a serialized public key on a given network. Compressed and uncompressed public keys yield different addresses. Output is `address=<base58>`.

**Test Cases:** `rcb_tests/public_test_cases/feature10_3_address_from_public_key.json`

```json
{
    "description": "Build the P2PKH address for a serialized public key on a given network. Compressed and uncompressed public keys yield different addresses.",
    "cases": [
        {"input": {"op": "address.from_public_key", "hex": "0285e9737a74c30a873f74df05124f2aa6f53042c2fc0a130d6cbd7d16b944b004", "network": "livenet"}, "expected_output": "address=19gH5uhqY6DKrtkU66PsZPUZdzTd11Y7ke\n"},
        {"input": {"op": "address.from_public_key", "hex": "0485e9737a74c30a873f74df05124f2aa6f53042c2fc0a130d6cbd7d16b944b004833fef26c8be4c4823754869ff4e46755b85d851077771c220e2610496a29d98", "network": "livenet"}, "expected_output": "address=16JXnhxjJUhxfyx4y6H4sFcxrgt8kQ8ewX\n"}
    ]
}
```

*10.4 Address from Hash — raw hash to address*

Builds an address from a raw 20-byte public-key hash (hex) for a given network and type. Output is `address=<base58>`.

**Test Cases:** `rcb_tests/public_test_cases/feature10_4_address_from_hash.json`

```json
{
    "description": "Build an address from a raw 20-byte public-key hash (hex) for a given network and type, returning the Base58Check address string.",
    "cases": [
        {"input": {"op": "address.from_public_key_hash", "hex": "1e1494e15afa231d299f5e3ced336169cfcbd36e", "network": "livenet", "type": "pubkeyhash"}, "expected_output": "address=13k3vneZ3yvZnc9dNWYH2RJRFsagTfAERv\n"},
        {"input": {"op": "address.from_public_key_hash", "hex": "1e1494e15afa231d299f5e3ced336169cfcbd36e", "network": "testnet", "type": "pubkeyhash"}, "expected_output": "address=miG1DqjXs1MpZidF65WerLWk7sBPMFBMWY\n"}
    ]
}
```

---

### Feature 11: Hierarchical Deterministic Keys (BIP32)

**As a developer**, I want to derive a tree of keys from a single master key, so I can generate unlimited child keys deterministically from one backup.

**Expected Behavior / Usage:** Extended keys are Base58Check strings: an extended private key (xprv) and an extended public key (xpub). A derivation path is `m/<index>[...]` where a trailing apostrophe marks a hardened index.

*11.1 Extended Public Key from Extended Private Key — same-node neutering*

Derives the xpub corresponding to an xprv at the same node, without deriving any child. Output is `xpub=<base58>`.

**Test Cases:** `rcb_tests/public_test_cases/feature11_1_hdkey_xpub_from_xprv.json`

```json
{
    "description": "Derive the extended public key (xpub) corresponding to an extended private key (xprv) at the same node, without deriving any child.",
    "cases": [
        {"input": {"op": "hdkey.xpub_from_xprv", "xprv": "xprv9s21ZrQH143K3QTDL4LXw2F7HEK3wJUD2nW2nRk4stbPy6cq3jPPqjiChkVvvNKmPGJxWUtg6LnF5kejMRNNU3TGtRBeJgk33yuGBxrMPHi"}, "expected_output": "xpub=xpub661MyMwAqRbcFtXgS5sYJABqqG9YLmC4Q1Rdap9gSE8NqtwybGhePY2gZ29ESFjqJoCu1Rupje8YtGqsefD265TMg7usUDFdp6W1EGMcet8\n"}
    ]
}
```

*11.2 Child Derivation — path-based descent with hardened indices*

Derives a child node from a master xprv along a derivation path and returns both the child xprv and xpub. Output is `xprv=<base58>` then `xpub=<base58>`.

**Test Cases:** `rcb_tests/public_test_cases/feature11_2_hdkey_derive.json`

```json
{
    "description": "Derive a BIP32 child node from a master xprv along a derivation path (where a trailing apostrophe marks a hardened index), returning the child extended private key (xprv) and extended public key (xpub).",
    "cases": [
        {"input": {"op": "hdkey.derive", "xprv": "xprv9s21ZrQH143K3QTDL4LXw2F7HEK3wJUD2nW2nRk4stbPy6cq3jPPqjiChkVvvNKmPGJxWUtg6LnF5kejMRNNU3TGtRBeJgk33yuGBxrMPHi", "path": "m/0'"}, "expected_output": "xprv=xprv9uHRZZhk6KAJC1avXpDAp4MDc3sQKNxDiPvvkX8Br5ngLNv1TxvUxt4cV1rGL5hj6KCesnDYUhd7oWgT11eZG7XnxHrnYeSvkzY7d2bhkJ7\nxpub=xpub68Gmy5EdvgibQVfPdqkBBCHxA5htiqg55crXYuXoQRKfDBFA1WEjWgP6LHhwBZeNK1VTsfTFUHCdrfp1bgwQ9xv5ski8PX9rL2dZXvgGDnw\n"},
        {"input": {"op": "hdkey.derive", "xprv": "xprv9s21ZrQH143K3QTDL4LXw2F7HEK3wJUD2nW2nRk4stbPy6cq3jPPqjiChkVvvNKmPGJxWUtg6LnF5kejMRNNU3TGtRBeJgk33yuGBxrMPHi", "path": "m/0'/1/2'/2/1000000000"}, "expected_output": "xprv=xprvA41z7zogVVwxVSgdKUHDy1SKmdb533PjDz7J6N6mV6uS3ze1ai8FHa8kmHScGpWmj4WggLyQjgPie1rFSruoUihUZREPSL39UNdE3BBDu76\nxpub=xpub6H1LXWLaKsWFhvm6RVpEL9P4KfRZSW7abD2ttkWP3SSQvnyA8FSVqNTEcYFgJS2UaFcxupHiYkro49S8yGasTvXEYBVPamhGW6cFJodrTHy\n"}
    ]
}
```

---

### Feature 12: Script Assembly

**As a developer**, I want to assemble and disassemble locking/unlocking scripts between human-readable text and the serialized wire form, so I can author and inspect scripts reliably.

**Expected Behavior / Usage:**

*12.1 ASM ⇄ Hex — assemble and disassemble*

Converts a script between its human-readable ASM form (opcode names and hex data pushes, space-separated) and its serialized hex wire form. A standard P2PKH locking script round-trips through both representations. Output is `hex=<serialized hex>` for assembly and `asm=<text>` for disassembly.

**Test Cases:** `rcb_tests/public_test_cases/feature12_1_script_asm_hex.json`

```json
{
    "description": "Convert a script between its human-readable ASM form and its serialized hex wire form. A standard P2PKH locking script round-trips through both representations.",
    "cases": [
        {"input": {"op": "script.asm_to_hex", "asm": "OP_DUP OP_HASH160 f4c03610e60ad15100929cc23da2f3a799af1725 OP_EQUALVERIFY OP_CHECKSIG"}, "expected_output": "hex=76a914f4c03610e60ad15100929cc23da2f3a799af172588ac\n"},
        {"input": {"op": "script.hex_to_asm", "hex": "76a914f4c03610e60ad15100929cc23da2f3a799af172588ac"}, "expected_output": "asm=OP_DUP OP_HASH160 f4c03610e60ad15100929cc23da2f3a799af1725 OP_EQUALVERIFY OP_CHECKSIG\n"}
    ]
}
```

*12.2 Invalid Data Push — non-hex token rejection*

A data push in ASM containing a non-hex (or odd-length) token is rejected as invalid hex when assembling. Output is `error=invalid_hex`.

**Test Cases:** `rcb_tests/public_test_cases/feature12_2_script_asm_errors.json`

```json
{
    "description": "A data push in ASM with an odd or non-hex token is rejected as invalid hex when assembling the script.",
    "cases": [
        {"input": {"op": "script.asm_to_hex", "asm": "OP_RETURN 026d02 0568656c6c6fzz"}, "expected_output": "error=invalid_hex\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the encoding, hashing, big-number, opcode, mnemonic, key, address and script primitives described above, with each domain in its own cohesive unit and no monolithic god file.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core library. It reads a single JSON command object from stdin, routes on the neutral `op` field to the matching core method, and prints the line-oriented `key=value` contract to stdout, normalizing any error into a language-neutral `error=<category>` line. This adapter is logically and physically separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_base58_encode_decode.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_base58_encode_decode@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the same output format prefix as the ripemd160 implementation
- adhere to the standard comparison semantics defined in the bignumber module docs
