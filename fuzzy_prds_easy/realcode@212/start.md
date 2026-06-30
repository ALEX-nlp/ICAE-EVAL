## Product Requirement Document

# Deterministic Wallet & Transaction Primitives - HD Keys, Address Encoding, and CBOR Transaction Serialization

## Project Goal

Build a library of deterministic cryptographic wallet primitives that allows developers to derive hierarchical-deterministic (HD) keys, encode and decode human-readable blockchain addresses, recover mnemonic seed phrases, and serialize blockchain transactions to their canonical binary form — all without hand-rolling the underlying BIP39/BIP32/Bech32/CBOR machinery or worrying about subtle byte-level encoding mistakes.

---

## Background & Problem

Without this library, developers integrating with a UTXO/account blockchain are forced to reimplement a large stack of fiddly, standards-bound primitives by hand: BIP39 mnemonic encoding, BIP32-Ed25519 hierarchical key derivation, Bech32 address checksums, Blake2b key hashing, native-script policy identifiers, and canonical CBOR transaction layouts. Each of these has exacting, well-specified byte-level outputs; a single off-by-one in a checksum, a wrong bit-clamp during seed derivation, or a mis-ordered CBOR map silently produces values that are rejected by the network. This leads to repetitive, error-prone boilerplate that is hard to test and hard to maintain.

With this library, developers express intent at a high level ("restore this mnemonic", "derive this path", "encode this address", "serialize this transaction") and receive deterministic, specification-correct results. Every operation in this document is a pure function of its inputs: identical inputs always yield identical outputs, with no dependence on randomness (except where a fresh phrase is explicitly requested), wall-clock time, or network access.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility domain (encoding/decoding, key derivation, hashing, scripts, transaction model + serialization). It MUST NOT be a single "god file". Provide a clear, multi-file directory tree separating the encoding layer, the key/derivation layer, the address layer, the transaction model, and the serialization layer.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a **black-box testing contract** for a thin execution adapter, NOT the internal data model of the core system. The core domain must be completely decoupled from stdin/stdout and JSON parsing. A separate adapter translates JSON commands into idiomatic calls on the core library and renders the documented stdout contract.

3. **Adherence to SOLID Design Principles:** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units. The core engine should be open for extension (new address types, new certificate kinds) but closed for modification. Keep interfaces small and cohesive; high-level modules depend on abstractions, not on I/O details.

4. **Robustness & Interface Design:** The public interface must be elegant and idiomatic to the target language. Edge cases (malformed encodings, invalid derivation paths, null inputs) must be modeled with proper error handling rather than generic faults.

### Execution Adapter I/O Contract

The execution adapter reads exactly one JSON object from stdin. The object always carries a string field `op` selecting the operation; the remaining fields are operation-specific (documented per feature below). The adapter prints results to stdout as a sequence of newline-terminated `key=value` lines, in the order documented for each operation. Booleans render lower-case (`true`/`false`).

When the requested operation cannot be completed because the input is malformed for that operation, the adapter prints a single normalized error line `error=<category>` instead of a result, where `<category>` is a language-neutral, domain-level token (e.g. `invalid_encoding` for a corrupt encoded string, `invalid_path` for a derivation path that cannot be constructed). Error output MUST NOT leak host-language runtime details (built-in exception type names, stack traces, auto-appended message suffixes).

Hex strings are lower-case on output and accepted case-insensitively on input. Byte arrays referenced by the cases are conventionally given as hex.

---

## Core Features

### Feature 1: Bech32 Address Encoding (BIP-0173 / CIP-19)

**As a developer**, I want to decode, re-encode, and validate Bech32 strings, so I can move between human-readable addresses and their raw byte payloads with checksum safety.

**Expected Behavior / Usage:**

*1.1 Decode — split an encoded string into payload, version, and prefix.*

`op=[a set of cryptographic and validation function names that are NOT exposed to the user interface]` with field `address`. Decode the Bech32 string into its raw data payload (emitted as `data_hex`), the embedded witness/header version byte (`version`, a small integer), and the human-readable prefix (`hrp`). Also emit `valid=true`. The version byte is the first 5-bit group of the decoded data as surfaced by the decoder.

**Test Cases:** `rcb_tests/public_test_cases/feature1_decode.json`

```json
{
  "description": "Decode a Bech32-encoded value into its raw data payload, the embedded witness/header version byte, and the human-readable prefix, and report whether the input is well formed.",
  "cases": [
    {"input": {"op": "[a set of cryptographic and validation function names that are NOT exposed to the user interface]", "address": "stake1uyehkck0lajq8gr28t9uxnuvgcqrc6070x3k9r8048z8y5gh6ffgw"}, "expected_output": "data_hex=e1337b62cfff6403a06a3acbc34f8c46003c69fe79a3628cefa9c47251\nversion=28\nhrp=stake\nvalid=true"}
  ]
}
```

*1.2 Round-trip — decode then re-encode under a supplied prefix.*

`op=[a set of cryptographic and validation function names that are NOT exposed to the user interface]` with fields `address` and `prefix`. Decode the payload, then re-encode it under `prefix`; emit `reencoded=<string>`. For a well-formed input re-encoded under its own prefix, the output equals the original string. The authoritative case list lives in `rcb_tests/test_cases/feature1_roundtrip.json`.

*1.3 Decode errors — reject malformed strings.*

`op=[a set of cryptographic and validation function names that are NOT exposed to the user interface]` over malformed inputs (out-of-range prefix characters, missing/empty separator, invalid data characters, bad checksums) must emit `error=invalid_encoding`. The authoritative case list lives in `rcb_tests/test_cases/feature1_decode_errors.json`.

*1.4 Validity predicate.*

`op=[a set of cryptographic and validation function names that are NOT exposed to the user interface]` with field `value` (which may be a JSON string or `null`). Emit `valid=true` for a syntactically correct Bech32 string (upper- or lower-case), otherwise `valid=false`. A null reference, empty/whitespace-only text, or a checksum/format error all yield `valid=false`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_is_valid_false.json`

```json
{
  "description": "A validity predicate reports false for inputs that are not well-formed Bech32 strings, including a null reference, empty or whitespace-only text, strings with no separator or an out-of-range character, and strings carrying a corrupted checksum.",
  "cases": [
    {"input": {"op": "[a set of cryptographic and validation function names that are NOT exposed to the user interface]", "value": null}, "expected_output": "valid=false"},
    {"input": {"op": "[a set of cryptographic and validation function names that are NOT exposed to the user interface]", "value": "1nwldj5"}, "expected_output": "valid=false"}
  ]
}
```

---

### Feature 2: Address Structure & Network Tagging (CIP-19)

**As a developer**, I want to parse addresses into structured parts and check their network tag, so I can route and validate addresses safely.

**Expected Behavior / Usage:**

*2.1 Parse — structured view of an address.*

`op=[a set of cryptographic and validation function names that are NOT exposed to the user interface]` with field `address`. Parse the Bech32 address and emit `data_hex` (raw payload), `prefix` (human-readable prefix), `network` (`Mainnet`/`Testnet`/`Unknown`), and `address_type` (e.g. `Base`). The network is determined from the prefix; the `addr`/`stake` prefixes are mainnet, `addr_test`/`stake_test` are testnet.

**Test Cases:** `rcb_tests/public_test_cases/feature2_parse.json`

```json
{
  "description": "Parse a Bech32 address string into a structured address, exposing its raw byte payload as hex, its human-readable prefix, the network it belongs to, and the address type.",
  "cases": [
    {"input": {"op": "[a set of cryptographic and validation function names that are NOT exposed to the user interface]", "address": "addr1q8d9pcrn38veygv638ftw0f82gm4h6rmrs599pkr3qfxx073eyjrmj0hnx6xz8emx03l6hszjclm8fmnlaewe4adp7dqsd8pa6"}, "expected_output": "data_hex=01da50e07389d992219a89d2b73d2752375be87b1c285286c38812633fd1c9243dc9f799b4611f3b33e3fd5e02963fb3a773ff72ecd7ad0f9a\nprefix=addr\nnetwork=Mainnet\naddress_type=Base"}
  ]
}
```

*2.2 Network validity.*

`op=[a set of cryptographic and validation function names that are NOT exposed to the user interface]` with field `address`. Emit `valid_network=true` when the address carries a recognized mainnet/testnet prefix, otherwise `false`. Authoritative cases: `rcb_tests/test_cases/feature2_valid_network.json`.

*2.3 Base address construction.*

`op=[a set of cryptographic and validation function names that are NOT exposed to the user interface]` builds a base address from a payment public key and a stake public key derived from the same seed (fields: `mnemonic`, a `keys` map of names→derivation paths, a `payment` key name, a `stake` key name, and `network`). Emit `address=<bech32>` and `address_hex=<hex>`. Different payment keys sharing the same stake key produce addresses with an identical trailing stake part. Authoritative cases: `rcb_tests/test_cases/feature2_[a set of cryptographic and validation function names that are NOT exposed to the user interface].json`.

---

### Feature 3: BIP39 Mnemonics & Language Wordlists

**As a developer**, I want to recover entropy from a phrase, generate phrases of a given size, and validate language wordlists, so I can implement standards-compliant seed handling.

**Expected Behavior / Usage:**

*3.1 Mnemonic → entropy.*

`op=[a set of cryptographic and validation function names that are NOT exposed to the user interface]` with field `mnemonic`. Restore the phrase and emit `entropy_hex=<hex>`, the raw entropy the phrase encodes.

**Test Cases:** `rcb_tests/public_test_cases/feature3_entropy.json`

```json
{
  "description": "Restore a mnemonic phrase back to the raw entropy it encodes, returned as a hex string.",
  "cases": [
    {"input": {"op": "[a set of cryptographic and validation function names that are NOT exposed to the user interface]", "mnemonic": "elder lottery unlock common assume beauty grant curtain various horn spot youth exclude rude boost fence used two spawn toddler soup awake across use"}, "expected_output": "entropy_hex=475083b81730de275969b1f18db34b7fb4ef79c66aa8efdd7742f1bcfe204097"}
  ]
}
```

*3.2 Phrase generation size.*

`op=[a set of cryptographic and validation function names that are NOT exposed to the user interface]` with integer field `word_count`. Generate a fresh phrase of the requested size (a standard BIP39 strength) and emit `word_count=<n>` equal to the requested value. Authoritative cases: `rcb_tests/test_cases/feature3_word_count.json`.

*3.3 Wordlist length.*

`op=[a set of cryptographic and validation function names that are NOT exposed to the user interface]` with field `language`. Emit `length=<n>`; every supported language wordlist holds exactly the standard number of entries. Authoritative cases: `rcb_tests/test_cases/feature3_[a set of cryptographic and validation function names that are NOT exposed to the user interface].json`.

*3.4 Wordlist membership.*

`op=[a set of cryptographic and validation function names that are NOT exposed to the user interface]` with fields `language` and `words` (an array). For each word, emit a line `<word>=<true|false>` reporting whether it is present in that language's wordlist, in input order.

**Test Cases:** `rcb_tests/public_test_cases/feature3_wordlist_membership.json`

```json
{
  "description": "For each supported language, the corresponding BIP39 wordlist contains a set of known sample words drawn from that language. Membership is checked word by word.",
  "cases": [
    {"input": {"op": "[a set of cryptographic and validation function names that are NOT exposed to the user interface]", "language": "English", "words": ["abandon", "lend", "zoo"]}, "expected_output": "abandon=true\nlend=true\nzoo=true"}
  ]
}
```

---

### Feature 4: BIP32-Ed25519 Hierarchical Key Derivation

**As a developer**, I want to derive a root key from a seed and walk derivation paths, so I can produce the keys behind addresses and signatures.

**Expected Behavior / Usage:**

*4.1 Root key.*

`op=[a set of cryptographic and validation function names that are NOT exposed to the user interface]` with field `mnemonic`. Emit `key_hex` (the extended private key half) and `chaincode_hex` (the 32-byte chain code).

**Test Cases:** `rcb_tests/public_test_cases/feature4_root_key.json`

```json
{
  "description": "Derive the root (master) extended private key from a restored mnemonic, returning the key half and the chain code as hex.",
  "cases": [
    {"input": {"op": "[a set of cryptographic and validation function names that are NOT exposed to the user interface]", "mnemonic": "art forum devote street sure rather head chuckle guard poverty release quote oak craft enemy"}, "expected_output": "key_hex=b8f2bece9bdfe2b0282f5bad705562ac996efb6af96b648f4445ec44f47ad95c10e3d72f26ed075422a36ed8585c745a0e1150bcceba2357d058636991f38a37\nchaincode_hex=91e248de509c070d812ab2fda57860ac876bc489192c1ef4ce253c197ee219a4"}
  ]
}
```

*4.2 Private-key derivation along a path.*

`op=derive_private_key` with fields `mnemonic` and `path` (a path string with hardened levels marked by an apostrophe, e.g. `m/1852'/1815'/0'/0/0`). Emit `key_hex` and `chaincode_hex` for the derived node. Derivation is well defined at every depth of a path (purpose, coin, account, role, index) and on alternate hardened branches. Authoritative cases: `rcb_tests/test_cases/feature4_path_derivation.json`, `feature4_partial_derivation.json`, `feature4_policy_key.json`.

*4.3 Soft public-key derivation.*

`op=derive_public_key` with fields `mnemonic`, `account_path` (hardened, to account level), and `soft_path` (non-hardened role/index tail, e.g. `0/1`). Take the account public key, derive the soft child, and emit `pubkey_key_hex`, `pubkey_chaincode_hex`, and `private_key=absent`. Soft public-key derivation yields the same public key as deriving the corresponding private key, and the derived public node has no private key. Authoritative cases: `rcb_tests/test_cases/feature4_public_derivation.json`.

*4.4 Encrypt / decrypt round-trip.*

`op=encrypt_decrypt_roundtrip` with fields `mnemonic` and `password`. Encrypt the root key with the passphrase, serialize/deserialize as JSON, decrypt, and emit the recovered `key_hex` and `chaincode_hex`, which match the original. Authoritative cases: `rcb_tests/test_cases/feature4_encrypt_decrypt.json`.

---

### Feature 5: Derivation Path Parsing & Formatting

**As a developer**, I want to parse, build, normalize, and validate derivation paths, so I can manipulate wallet account structure reliably.

**Expected Behavior / Usage:**

*5.1 Parse a full path.*

`op=[a set of cryptographic and validation function names that are NOT exposed to the user interface]` with field `path`. Emit `path` (canonical re-rendering), `purpose`, `coin`, `account_index`, `role`, and `index`. Purpose values include `Byron` (44'), `Shelley` (1852'), and `PolicyKeys` (1855'); coin is `Ada` (1815'); role is `ExternalChain` (0), `InternalChain` (1), or `Staking` (2).

**Test Cases:** `rcb_tests/public_test_cases/feature5_parse.json`

```json
{
  "description": "Parse a full derivation path string into its components: purpose, coin type, account index, role, and index. Re-rendering the parsed path reproduces the original string.",
  "cases": [
    {"input": {"op": "[a set of cryptographic and validation function names that are NOT exposed to the user interface]", "path": "m/44'/1815'/0'/0/0"}, "expected_output": "path=m/44'/1815'/0'/0/0\npurpose=Byron\ncoin=Ada\naccount_index=0\nrole=ExternalChain\nindex=0"}
  ]
}
```

*5.2 Build from components.*

`op=path_from_components` with fields `purpose`, `coin`, `account_index`, `role`, `index`. Emit the same six lines as 5.1; the rendered path matches the equivalent parsed path. Authoritative cases: `rcb_tests/test_cases/feature5_from_components.json`.

*5.3 Normalize.*

`op=path_normalize` with field `path`. A partial path that omits the hardened account prefix resolves to its soft role/index tail (e.g. `1852'/1815'/1'/0/1` → `0/1`); a complete hardened path is preserved. Emit `normalized=<path>`. Authoritative cases: `rcb_tests/test_cases/feature5_normalize.json`.

*5.4 Invalid paths.*

`op=[a set of cryptographic and validation function names that are NOT exposed to the user interface]` with field `path`. Strings that are neither a complete hardened path nor a valid soft tail are rejected; emit `error=invalid_path`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_invalid.json`

```json
{
  "description": "Strings that are neither a complete hardened path nor a valid soft tail are rejected when constructing a path. Each such input surfaces as a normalized invalid-path error.",
  "cases": [
    {"input": {"op": "[a set of cryptographic and validation function names that are NOT exposed to the user interface]", "path": "m/1852'/1815'"}, "expected_output": "error=invalid_path"}
  ]
}
```

---

### Feature 6: Hashing & Native-Script Policy Identifiers

**As a developer**, I want to compute key hashes and native-script policy ids, so I can build credentials and asset policies.

**Expected Behavior / Usage:**

*6.1 Blake2b-224 key hash.*

`op=[a set of cryptographic and validation function names that are NOT exposed to the user interface]` with field `data_hex`. Emit `hash_hex=<hex>`, the 28-byte Blake2b-224 digest of the input bytes.

**Test Cases:** `rcb_tests/public_test_cases/feature6_[a set of cryptographic and validation function names that are NOT exposed to the user interface].json`

```json
{
  "description": "Compute the 28-byte Blake2b-224 hash of a byte input, returned as hex.",
  "cases": [
    {"input": {"op": "[a set of cryptographic and validation function names that are NOT exposed to the user interface]", "data_hex": "848AC717B552FCD1F2DCB4933E4A8198187E7E424693B51E1B8B16250F3CADFE"}, "expected_output": "hash_hex=5cd719e99fdd80fd889e82cf012e64d5da7ab35364bb02163bc93974"}
  ]
}
```

*6.2 Native-script policy id.*

`op=policy_id_all_sig` with field `key_hash_hex`. Build an "all of" native script requiring one signature from the given key hash, then emit `policy_id=<hex>`, the hash of the serialized script. Authoritative cases: `rcb_tests/test_cases/feature6_policy_id.json`.

---

### Feature 7: Bit Utility

**As a developer**, I want to extract the low bits of a byte, so I can decode packed header fields.

**Expected Behavior / Usage:**

`op=[a set of cryptographic and validation function names that are NOT exposed to the user interface]` with integer fields `byte` (0–255) and `n`. Emit `result=<int>`, the value of the least-significant `n` bits of the byte.

**Test Cases:** `rcb_tests/public_test_cases/feature7_[a set of cryptographic and validation function names that are NOT exposed to the user interface].json`

```json
{
  "description": "Extract the least-significant N bits of a single byte, returning the resulting integer value.",
  "cases": [
    {"input": {"op": "[a set of cryptographic and validation function names that are NOT exposed to the user interface]", "byte": 131, "n": 4}, "expected_output": "result=3"}
  ]
}
```

---

### Feature 8: Transaction CBOR Serialization

**As a developer**, I want to assemble transactions (inputs, outputs, native assets, certificates, mints, witnesses, metadata) and serialize them to canonical CBOR, so I can submit valid transactions.

**Expected Behavior / Usage:**

`op=[a set of cryptographic and validation function names that are NOT exposed to the user interface]` drives a transaction builder and renders canonical CBOR as hex. Common fields:

- `mode`: `body` serializes the unsigned transaction body alone (emit `cbor=<hex>`); `full` serializes the complete transaction (body + witness set + optional auxiliary data) and emits `cbor=<hex>`.
- `inputs`: array of `{tx_hash, index}`.
- `outputs`: array of `{address, amount}` with optional `assets`. An `address` is one of `{"hex": "..."}`, `{"bech32": "..."}`, or `{"base": {"payment": <keyName>, "stake": <keyName>}}`. `assets` is an array of `{policy, name_hex, quantity}` where `policy` is `{"hex": <policyId>}` or `{"vkey_hex": <vkey>}` (the latter derives the policy id from an all-of script over the key's Blake2b-224 hash).
- `ttl`, `fee`: optional integers.
- `certificate`: optional `{stake_registration, stake_delegation: {credential, pool}}` (hex credentials).
- `mint`: optional asset array (same shape as `assets`).
- key material: either `{"mnemonic", "keys": {name: path}}` (named derived keys) and/or raw witness keys supplied inline.
- `witnesses` (full mode): `{vkeys: [...], native_script_all: {...}}`. A vkey entry is either `{"key": <keyName>}` or a raw `{"public_hex", "private_hex", "chaincode"}` (chaincode `"null"`, `"empty"`, or hex). `native_script_all` carries `keyhash` or `keyhash_of_vkey`.
- `aux_data` (full mode): array of `{label, value}` metadata entries; `value` is serialized as a CBOR map/value.
- `calculate_fee`: when true (full mode), additionally emit `fee=<int>`.

Native assets serialize as a policy→(asset-name→quantity) map; multiple asset names group under one policy, and multiple policies group under the output. Attaching metadata also embeds the metadata hash into the body.

**Test Cases:** `rcb_tests/public_test_cases/feature8_body_change.json`

```json
{
  "description": "Serialize an unsigned transaction body that spends one input into a payment output and a change output (both base addresses derived from the same seed), with an explicit time-to-live and fee, to its CBOR encoding (hex).",
  "cases": [
    {"input": {"op": "[a set of cryptographic and validation function names that are NOT exposed to the user interface]", "mode": "body", "mnemonic": "art forum devote street sure rather head chuckle guard poverty release quote oak craft enemy", "keys": {"payment": "m/1852'/1815'/0'/0/0", "change": "m/1852'/1815'/0'/1/0", "stake": "m/1852'/1815'/0'/2/0"}, "inputs": [{"tx_hash": "0000000000000000000000000000000000000000000000000000000000000000", "index": 0}], "outputs": [{"address": {"base": {"payment": "payment", "stake": "stake"}}, "amount": 10}, {"address": {"base": {"payment": "change", "stake": "stake"}}, "amount": 856488}], "ttl": 1000, "fee": 143502}, "expected_output": "cbor=a4008182582000000000000000000000000000000000000000000000000000000000000000000001828258390079467c69a9ac66280174d09d62575ba955748b21dec3b483a9469a65cc339a35f9e0fe039cf510c761d4dd29040c48e9657fdac7e9c01d940a82583900c05e80bdcf267e7fe7bf4a867afe54a65a3605b32aae830ed07f8e1ccc339a35f9e0fe039cf510c761d4dd29040c48e9657fdac7e9c01d941a000d11a8021a0002308e031903e8"}
  ]
}
```

Further authoritative transaction cases (signed transactions, certificates, single- and multi-policy native assets, fee calculation, metadata, and minting) live under `rcb_tests/test_cases/feature8_*.json`.

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the features above (encoding, key derivation, addresses, hashing/scripts, transaction model, and CBOR serialization as separated layers), idiomatic to the target language.

2. **The Execution/Test Adapter:** A runnable program that reads one JSON command from stdin, invokes the core library, and prints the documented `key=value` stdout contract (and normalized `error=<category>` lines on invalid input). It must be logically and physically separate from the core domain.

3. **Automated test harness:** A single entry point `bash rcb_tests/test.sh` that runs every `*.json` case file in a case directory, accepting `--cases-dir <subdir>` (default `test_cases`; the PRD-embedded examples are mirrored under `public_test_cases`). For each case it writes one file `rcb_tests/stdout/<cases-dir>/{stem}@{index:03}.txt` containing only the raw stdout of the program under test, directly comparable against `expected_output`.


---
**Implementation notes:**
- follow the same prefix-to-network mapping logic used in the address validation module
- initialize using the default English language wordlist size defined in the configuration constants
