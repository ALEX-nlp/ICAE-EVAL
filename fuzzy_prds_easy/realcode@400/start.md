## Product Requirement Document

# Secure Secret State Manager — Vault, Snapshot, Store, and Cryptographic Procedure Contracts

## Project Goal

Build a secure secret state management system that lets developers keep sensitive records in isolated client vaults, persist and restore encrypted snapshots, use a separate non-secret key/value store, and execute cryptographic procedures over protected key material — all while exposing only explicit, well-defined outputs (hint listings, existence signals, public keys, signatures, ciphertext, tags, message authentication codes) and never leaking raw secret bytes through the public interface.

---

## Background & Problem

Without this system, developers must hand-roll record indexing, client isolation, encrypted persistence, and cryptographic workflows around secret material. This produces repetitive boilerplate, accidental secret exposure, inconsistent snapshot behavior, and fragile cryptographic composition.

With this system, developers interact with a high-level secret-state engine: they write indexed records into vault paths, manage multiple isolated clients, persist state to named encrypted snapshots, use a general-purpose store for non-secret data, and ask the runtime to perform cryptographic operations while receiving only the intended outputs. Secret bytes (seeds, private keys, shared secrets) stay inside vaults and are observable only indirectly through derived public artifacts.

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
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Protocol & Output Conventions

- The execution adapter reads a single JSON object from stdin and writes a deterministic plain-text report to stdout. Each line is `key=value`; the report ends with a trailing newline.
- The leading line is always `operation=<name>` identifying which behavior ran.
- Vault hint listings are emitted as repeated `hint=<text>` lines in the system's internal record-storage order (which is deterministic but not necessarily ascending by index); record existence is reported as `record_index_<I>=present|absent`.
- All cryptographic byte outputs (digests, public keys, signatures, ciphertext, tags, MACs) are rendered as lowercase hexadecimal.
- Cryptographic operations are made deterministic by supplying fixed key material in the input (seed bytes, raw private keys, nonces in hex). Given identical input, the output is byte-for-byte reproducible.
- On malformed input or a rejected operation, the adapter emits a single language-neutral category line such as `error=invalid_input` or `error=procedure_rejected` (no host-language exception names or stack traces).

---

## Core Features

### Feature 1: Indexed Secret Vault Records

**As a developer**, I want to write several indexed secret records into one vault path and then confirm which record slots exist, so I can distinguish a real, indexed vault from a stubbed success response.

**Operation:** `vault_records`

**Input fields:**
- `op`: the literal `"vault_records"`.
- `client`: client identifier string.
- `vault`: vault path string.
- `records`: list of `{index, value, hint}` entries written into the vault.
- `queries`: list of record indices to probe for existence.

**Expected Behavior:**
Write every supplied record into the named vault for the named client. Emit the vault path, the total number of visible records (`record_count`), every stored hint as a `hint=` line in internal storage order, and one `record_index_<I>=present|absent` line per queried index.

**Test Cases:** `rcb_tests/public_test_cases/feature1_vault_records.json`

```json
{
  "feature": "feature1_vault_records",
  "cases": [
    {
      "name": "basic",
      "input": {
        "op": "vault_records",
        "client": "client-main",
        "vault": "path",
        "records": [
          { "index": 0, "value": "alpha", "hint": "h0" },
          { "index": 5, "value": "bravo", "hint": "h5" },
          { "index": 15, "value": "charlie", "hint": "h15" },
          { "index": 19, "value": "delta", "hint": "h19" }
        ],
        "queries": [ 5, 15, 19, 7 ]
      },
      "expected_output": "operation=vault_records\nvault=path\n[a specific placeholder count for record retrieval]\n[a specific placeholder string for hint keys]\n[a specific placeholder string for hint keys]\n[a specific placeholder string for hint keys]\n[a specific placeholder string for hint keys]\n[a specific list of missing index numbers]\n[a specific list of missing index numbers]\n[a specific list of missing index numbers]\n[a specific list of missing index numbers]\n"
    }
  ]
}
```

---

### Feature 2: Secret Record Revocation and Garbage Collection

**As a developer**, I want to revoke vault records and then garbage-collect the vault, so I can ensure revoked secrets are no longer visible while the vault itself still exists.

**Operation:** `vault_revoke`

**Input fields:**
- `op`: the literal `"vault_revoke"`.
- `client`: client identifier string.
- `vault`: vault path string.
- `records`: list of `{index, value, hint}` entries written and then revoked.

**Expected Behavior:**
Write each supplied record, then revoke each written record. Report the number of records written (`records_written`), the number of visible hints after revocation but before collection (`hints_before_gc`), an existence probe per revoked index (`record_index_<I>=absent`), whether the vault still exists after garbage collection (`garbage_collected_vault`), the hint count after collection (`hints_after_gc`), and whether the vault remains present (`vault_after_gc`).

**Test Cases:** `rcb_tests/public_test_cases/feature2_vault_revoke.json`

```json
{
  "feature": "feature2_vault_revoke",
  "cases": [
    {
      "name": "basic",
      "input": {
        "op": "vault_revoke",
        "client": "client-main",
        "vault": "path",
        "records": [
          { "index": 0, "value": "a", "hint": "h0" },
          { "index": 1, "value": "b", "hint": "h1" },
          { "index": 2, "value": "c", "hint": "h2" }
        ]
      },
      "expected_output": "operation=vault_revoke\nvault=path\nrecords_written=3\nhints_before_gc=3\nrecord_index_0=absent\nrecord_index_1=absent\nrecord_index_2=absent\ngarbage_collected_vault=present\nhints_after_gc=0\nvault_after_gc=present\n"
    }
  ]
}
```

---

### Feature 3: General Key/Value Store Lifecycle

**As a developer**, I want to store non-secret bytes outside the secret vault, so I can read ordinary application data and remove it independently of vault records.

**Operation:** `store`

**Input fields:**
- `op`: the literal `"store"`.
- `client`: client identifier string.
- `store`: a `{key, value}` entry for the general store.

**Expected Behavior:**
On the first write of the key, report no previous value (`previous=none`). A read with the same key must return the stored value (`read_value=<value>`). After deletion, a read must return no value (`after_delete=none`).

**Test Cases:** `rcb_tests/public_test_cases/feature3_store.json`

```json
{
  "feature": "feature3_store",
  "cases": [
    {
      "name": "basic",
      "input": {
        "op": "store",
        "client": "client-main",
        "store": { "key": "session-token", "value": "payload-1234" }
      },
      "expected_output": "operation=store\nkey=session-token\nprevious=none\nread_value=payload-1234\nafter_delete=none\n"
    }
  ]
}
```

---

### Feature 4: Named Snapshot Restore

**As a developer**, I want to persist client vault state into a named encrypted snapshot, so I can restore visible vault state after clearing the in-memory client cache.

**Operation:** `snapshot`

**Input fields:**
- `op`: the literal `"snapshot"`.
- `client`: client identifier string.
- `vault`: vault path string.
- `records`: list of `{index, value, hint}` entries written before snapshotting.
- `snapshot`: a `{name, key}` pair naming the snapshot and its encryption key.
- `queries`: list of record indices to probe after restore.

**Expected Behavior:**
Write the records, persist all client state into the named snapshot, clear the in-memory client cache, reload the named snapshot with the same key, and confirm the visible hint count after restore equals the count before snapshotting. Emit the snapshot name, the before/after hint counts, each restored hint as a `hint=` line, and a `record_index_<I>=present|absent` probe per queried index.

**Test Cases:** `rcb_tests/public_test_cases/feature4_snapshot.json`

```json
{
  "feature": "feature4_snapshot",
  "cases": [
    {
      "name": "basic",
      "input": {
        "op": "snapshot",
        "client": "client-main",
        "vault": "path",
        "records": [
          { "index": 0, "value": "a", "hint": "h0" },
          { "index": 1, "value": "b", "hint": "h1" }
        ],
        "snapshot": { "name": "snap1", "key": "abcdefghijklmnopqrstuvwxyz012345" },
        "queries": [ 0, 1, 2 ]
      },
      "expected_output": "operation=snapshot\nsnapshot=snap1\nhints_before_snapshot=2\nhints_after_restore=2\n[a specific placeholder string for hint keys]\nhint=h1\nrecord_index_0=present\nrecord_index_1=present\nrecord_index_2=absent\n"
    }
  ]
}
```

---

### Feature 5: Multiple Client Isolation

**As a developer**, I want to operate multiple clients against the same vault coordinates, so I can keep each client's record state separate.

**Operation:** `multi_client`

**Input fields:**
- `op`: the literal `"multi_client"`.
- `vault`: vault path string shared by all clients.
- `clients`: list of `{name, value, hint}` entries; each names a client that writes its own record to the shared vault path.

**Expected Behavior:**
Create or target each client, write that client's record to the shared vault path, then revisit each client and report a separate record count. Emit the number of clients, the shared vault path, and one `client=<name> record_count=<n> hint=<hint>` line per client, proving isolated per-client storage.

**Test Cases:** `rcb_tests/public_test_cases/feature5_multi_client.json`

```json
{
  "feature": "feature5_multi_client",
  "cases": [
    {
      "name": "three",
      "input": {
        "op": "multi_client",
        "vault": "path",
        "clients": [
          { "name": "c0", "value": "v0", "hint": "h0" },
          { "name": "c1", "value": "v1", "hint": "h1" },
          { "name": "c2", "value": "v2", "hint": "h2" }
        ]
      },
      "expected_output": "operation=multi_client\nclients=3\nvault=path\nclient=c0 [a specific placeholder count for record retrieval] [a specific placeholder string for hint keys]\nclient=c1 [a specific placeholder count for record retrieval] hint=h1\nclient=c2 [a specific placeholder count for record retrieval] hint=h2\n"
    }
  ]
}
```

---

### Feature 6: Client Targeting and Removal

**As a developer**, I want to spawn several clients, switch the active target, remove a client, and observe that re-targeting a removed client fails, so I can rely on explicit client lifecycle errors.

**Operation:** `client_targeting`

**Input fields:**
- `op`: the literal `"client_targeting"`.
- `clients`: list of `{name}` entries naming clients to spawn in order.

**Expected Behavior:**
Spawn each named client, switch the active target to the last one, remove that client, and attempt to re-target it. Emit the number spawned, the client switched to, the removed client, and a language-neutral error category for the failed re-target (`reswitch_error=target_not_found`).

**Test Cases:** `rcb_tests/public_test_cases/feature6_client_targeting.json`

```json
{
  "feature": "feature6_client_targeting",
  "cases": [
    {
      "name": "three",
      "input": {
        "op": "client_targeting",
        "clients": [ { "name": "c0" }, { "name": "c1" }, { "name": "c2" } ]
      },
      "expected_output": "operation=client_targeting\nclients_spawned=3\nswitched_to=c2\nkilled_client=c2\nreswitch_error=target_not_found\n"
    }
  ]
}
```

---

### Feature 7: Cryptographic Hashing

**As a developer**, I want to hash a message with a named algorithm, so I can obtain a stable digest of input data.

**Operation:** `hash`

**Input fields:**
- `op`: the literal `"hash"`.
- `client`: client identifier string.
- `algorithm`: hash algorithm name (e.g. `"sha-256"`).
- `message`: the message text to hash.

**Expected Behavior:**
Compute the digest of the message under the named algorithm and emit it as lowercase hex. The output reports the algorithm and the full digest value so the result is independently verifiable.

**Test Cases:** `rcb_tests/public_test_cases/feature7_hash.json`

```json
{
  "feature": "feature7_hash",
  "cases": [
    {
      "name": "sha256",
      "input": {
        "op": "hash",
        "client": "c",
        "algorithm": "sha-256",
        "message": "hello world"
      },
      "expected_output": "operation=hash\nalgorithm=sha-256\ndigest=b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9\n"
    }
  ]
}
```

---

### Feature 8: Stored Ed25519 Signing

**As a developer**, I want to derive a protected Ed25519 signing key from a fixed seed inside a vault and sign a message, so I can expose only the public key and signature.

**Operation:** `ed25519`

**Input fields:**
- `op`: the literal `"ed25519"`.
- `client`: client identifier string.
- `vault`: vault path string.
- `seed_hex`: fixed seed bytes in hex written into the vault.
- `chain`: list of hardened derivation path components.
- `message`: the message text to sign.

**Expected Behavior:**
Write the fixed seed into the vault, derive an Ed25519 signing key along the hardened chain, export the public key, and sign the message. Emit the message, the public key (hex), and the signature (hex). Because the seed is fixed, the public key and signature are deterministic and verifiable.

**Test Cases:** `rcb_tests/public_test_cases/feature8_ed25519.json`

```json
{
  "feature": "feature8_ed25519",
  "cases": [
    {
      "name": "sign",
      "input": {
        "op": "ed25519",
        "client": "c",
        "vault": "keys",
        "seed_hex": "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f",
        "chain": [ 44, 0, 0 ],
        "message": "attack at dawn"
      },
      "expected_output": "operation=ed25519\nmessage=attack at dawn\npublic_key=0fa55e69128c8112fdff45f5edc28985593b68ea198e0fed8c1ff8329753d16d\nsignature=b6d48d9f0d19dbecbfb81e44bff6b106db8ca0131c46cd198e88164a5dde52308db102320729de49871caaa7780a90a0c86d0c304c89fa6759ff33e249ca3801\n"
    }
  ]
}
```

---

### Feature 9: Equivalent Intermediate Derivation

**As a developer**, I want to derive hierarchical key material directly and via an intermediate parent key, so I can confirm both strategies produce the same chain code.

**Operation:** `slip10`

**Input fields:**
- `op`: the literal `"slip10"`.
- `client`: client identifier string.
- `vault`: vault path string.
- `seed_hex`: fixed seed bytes in hex written into the vault.
- `chain`: list of hardened derivation path components.

**Expected Behavior:**
Derive once over the full joined chain, and once by storing an intermediate parent key then deriving the remaining components. Emit both resulting chain codes as hex (`chain_code_full` and `chain_code_split`); with a fixed seed they must be equal.

**Test Cases:** `rcb_tests/public_test_cases/feature9_slip10.json`

```json
{
  "feature": "feature9_slip10",
  "cases": [
    {
      "name": "split4",
      "input": {
        "op": "slip10",
        "client": "c",
        "vault": "keys",
        "seed_hex": "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f",
        "chain": [ 44, 0, 0, 1 ]
      },
      "expected_output": "operation=slip10\nchain_code_full=a342f3b48dd457b17a20d62217566be9a71328bd6f90a65db83538162004124c\nchain_code_split=a342f3b48dd457b17a20d62217566be9a71328bd6f90a65db83538162004124c\n"
    }
  ]
}
```

---

### Feature 10: Authenticated Encryption Round Trip

**As a developer**, I want to encrypt and decrypt data with associated data and a nonce, so I can protect plaintext while verifying it can be restored exactly.

**Operation:** `aead`

**Input fields:**
- `op`: the literal `"aead"`.
- `client`: client identifier string.
- `vault`: vault path string.
- `algorithm`: AEAD algorithm name (e.g. `"aes-256-gcm"`).
- `key_hex`: fixed key bytes in hex written into the vault.
- `nonce_hex`: fixed nonce bytes in hex.
- `plaintext`: the plaintext text to encrypt.
- `associated_data`: additional authenticated data.

**Expected Behavior:**
Store the fixed key, encrypt the plaintext under the named algorithm with the given nonce and associated data, then decrypt with the same nonce and associated data. Emit the algorithm, the ciphertext (hex), the authentication tag (hex), and the restored plaintext text. With a fixed key and nonce these values are deterministic.

**Test Cases:** `rcb_tests/public_test_cases/feature10_aead.json`

```json
{
  "feature": "feature10_aead",
  "cases": [
    {
      "name": "aes",
      "input": {
        "op": "aead",
        "client": "c",
        "vault": "keys",
        "algorithm": "aes-256-gcm",
        "key_hex": "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f",
        "nonce_hex": "000000000000000000000000",
        "plaintext": "secret message",
        "associated_data": "meta"
      },
      "expected_output": "operation=aead\nalgorithm=aes-256-gcm\nciphertext=7dd9d6acd058a3d06ddbda547f49\ntag=907b325789ec5352b1da50fdc45efeb0\ndecrypted=secret message\n"
    }
  ]
}
```

---

### Feature 11: X25519 Shared Secret Agreement

**As a developer**, I want to derive shared secret material from two fixed key pairs and prove both sides agree, so I can confirm key agreement without exposing the secret itself.

**Operation:** `x25519`

**Input fields:**
- `op`: the literal `"x25519"`.
- `client`: client identifier string.
- `vault`: vault path string.
- `sk1_hex`: first party's fixed 32-byte private key in hex.
- `sk2_hex`: second party's fixed 32-byte private key in hex.
- `message`: a message text used to bind both derived shared secrets.

**Expected Behavior:**
Store both fixed private keys, export both public keys, derive the shared secret in both directions, and compute a message authentication code over the binding message keyed by each derived shared secret. Emit both public keys (hex) and both MACs (hex). Because the shared secret agrees in both directions, the two MACs must be equal — proving key agreement without revealing the secret bytes.

**Test Cases:** `rcb_tests/public_test_cases/feature11_x25519.json`

```json
{
  "feature": "feature11_x25519",
  "cases": [
    {
      "name": "agree",
      "input": {
        "op": "x25519",
        "client": "c",
        "vault": "keys",
        "sk1_hex": "a8ababababababababababababababababababababababababababababababab",
        "sk2_hex": "c9cdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcdcd",
        "message": "channel-binding"
      },
      "expected_output": "operation=x25519\npublic_key_1=e3712d851a0e5d79b831c5e34ab22b41a198171de209b8b8faca23a11c624859\npublic_key_2=b5bea823d9c9ff576091c54b7c596c0ae296884f0e150290e88455d7fba6126f\nmac_1_2=153f96b2ee112b6eea37ca4139179f2435fc4e027a5b4900a902a7cf42e6aecd\nmac_2_1=153f96b2ee112b6eea37ca4139179f2435fc4e027a5b4900a902a7cf42e6aecd\n"
    }
  ]
}
```

---

### Feature 12: Mnemonic Recovery Signing

**As a developer**, I want to recover seed material from a fixed mnemonic and passphrase and sign a message, so I can reproduce derived signing output from a recovered seed.

**Operation:** `bip39_recover`

**Input fields:**
- `op`: the literal `"bip39_recover"`.
- `client`: client identifier string.
- `vault`: vault path string.
- `mnemonic`: a fixed English mnemonic phrase.
- `passphrase`: the recovery passphrase.
- `chain`: list of hardened derivation path components.
- `message`: the message text to sign.

**Expected Behavior:**
Recover the seed from the fixed mnemonic and passphrase into the vault, derive an Ed25519 signing key along the hardened chain, export the public key, and sign the message. Emit the message, the public key (hex), and the signature (hex). With a fixed mnemonic and passphrase the outputs are deterministic and verifiable.

**Test Cases:** `rcb_tests/public_test_cases/feature12_bip39_recover.json`

```json
{
  "feature": "feature12_bip39_recover",
  "cases": [
    {
      "name": "recover",
      "input": {
        "op": "bip39_recover",
        "client": "c",
        "vault": "keys",
        "mnemonic": "legal winner thank year wave sausage worth useful legal winner thank yellow",
        "passphrase": "TREZOR",
        "chain": [ 44, 0, 0 ],
        "message": "transfer 100"
      },
      "expected_output": "operation=bip39_recover\nmessage=transfer 100\npublic_key=212a1d51a066bef15be5005af7896e87915c67d1073699df2d383ae673f6b26c\nsignature=53619f6c672223d93775effa4ade2707ab22f7c50d4381c305b9e60d0e2aad9d6c40995b5b1ddc9660fa08283728260d4ee4bc1f7d4293e6ce8245388823aa06\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_vault_records.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_vault_records@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
