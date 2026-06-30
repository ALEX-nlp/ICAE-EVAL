## Product Requirement Document

# Multiplayer Session Identity & Module Compatibility Toolkit - PRD

## Project Goal

Build a small toolkit that lets a multiplayer game client and server agree on two things before a session starts: **who is connecting** (a compact, transmittable identity token carrying a client id and a mod version) and **whether the two sides are running a compatible set of game modules**. Developers can encode/decode connection tokens and compare module manifests without hand-rolling delimiter parsing, version comparison, or manifest serialization.

---

## Background & Problem

When a client connects to a host, the host must (a) recognize the client by a stable identity and the exact mod version it runs, and (b) confirm the client's installed modules match the host's closely enough to share a session. Without a dedicated toolkit, developers stitch this together by hand: concatenating identity fields into strings with ad-hoc delimiters (and forgetting to reject values that themselves contain the delimiter), reparsing those strings defensively, and writing bespoke equality/serialization for module manifests. This is repetitive, easy to get subtly wrong (a malformed token silently accepted, two different manifests hashing the same), and hard to evolve.

With this toolkit, identity is expressed as a single round-trippable token with strict validation on both construction and parsing, and module compatibility is a first-class operation: summarize a manifest, compare two manifests for mutual compatibility and version agreement, and serialize a manifest to a portable payload that faithfully round-trips and distinguishes different manifests.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The codebase has two distinct domains (identity tokens and module compatibility) plus an execution adapter. It MUST be organized into clear, separately-compiled units (e.g. a core domain library and a thin adapter), not a single monolithic file. Do not over-engineer — each domain is small — but keep the domains and the I/O adapter physically separated.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases in "Core Features" are a **black-box contract for the execution adapter**, not the internal data model. Core logic MUST NOT read stdin, write stdout, or parse JSON. The adapter alone translates JSON commands into idiomatic calls on the core domain and renders results.

3. **Adherence to SOLID Design Principles:** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units. The core must be open for extension but closed for modification, depend on abstractions (e.g. the source of the module manifest is injected, not hard-wired), and expose small cohesive interfaces.

4. **Robustness & Interface Design:** The public interface must be idiomatic to the target language and hide internal complexity. Invalid input must be modeled explicitly — construction rejects an empty identity or a missing version, and parsing reports malformed input — rather than producing corrupt values or leaking generic faults. All error conditions are surfaced to the adapter boundary as language-neutral categories.

---

## Core Features

### Feature 1: Connection Identity Token

**As a developer**, I want to turn a client identity and mod version into one compact transmittable token (and back), so I can carry session identity across the wire without ad-hoc string handling.

**Expected Behavior / Usage:**

A connection identity consists of a **client id** — a 128-bit globally-unique identifier in canonical hyphenated form — and a **mod version** — four dot-separated non-negative integers. The two domains below cover producing a token from an identity and recovering an identity from a token.

*1.1 Encode Identity to Token — produce a delimited token from a validated identity*

The encoder takes a client id and a version and produces a single token string of the form `<client_id>%<version>` joined by a `%` delimiter. Construction enforces two preconditions before a token is produced: the client id must not be the all-zero identity, and the version must be present. If the client id is the all-zero identity, the operation fails with the neutral category `argument_null` naming the field `client_id`. If the version is absent, it fails with `argument_null` naming the field `version`. The empty-identity check takes precedence over the missing-version check. On success the output is a single `token=` line.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_token_encode.json`

```json
{
    "description": "Build a connection identity token from a client identity (a 128-bit GUID) and a four-part numeric mod version. A valid identity and version produce a single delimited token string of the form '<guid>%<version>'. Construction rejects an empty/zero identity and a missing version, each surfaced as a neutral argument_null error naming the offending field.",
    "cases": [
        {
            "input": {"action": "encode_token", "client_id": "8e8a09e4-eddf-4c33-a1d8-1e399b763fd4", "version": "1.2.3.4"},
            "expected_output": "token=8e8a09e4-eddf-4c33-a1d8-1e399b763fd4%1.2.3.4\n"
        },
        {
            "input": {"action": "encode_token", "client_id": "11111111-2222-3333-4444-555555555555", "version": "1.1.1.1"},
            "expected_output": "token=11111111-2222-3333-4444-555555555555%1.1.1.1\n"
        },
        {
            "input": {"action": "encode_token", "client_id": "[a specific null/zero sentinel value for client_id — ask the system spec for the exact representation]", "version": "1.1.1.1"},
            "expected_output": "error=argument_null\nparam=client_id\n"
        },
        {
            "input": {"action": "encode_token", "client_id": "8e8a09e4-eddf-4c33-a1d8-1e399b763fd4"},
            "expected_output": "error=argument_null\nparam=version\n"
        }
    ]
}
```

*1.2 Decode Token to Identity — recover an identity from a token, rejecting malformed input*

The decoder takes a token string and attempts to recover the client id and version. A well-formed token has exactly two `%`-delimited parts: a parseable non-zero client id and a parseable four-part version. On success the output is a `client_id=` line followed by a `version=` line. The decode must reject, with the neutral category `invalid_token`, every malformed input: an empty string, a token missing one of the two parts, a token with a trailing delimiter (empty second part), a token with a leading delimiter, and a token whose recovered identity is the all-zero identity. No fields are emitted on rejection.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_token_decode.json`

```json
{
    "description": "Parse a connection identity token back into its identity and version fields. A well-formed '<guid>%<version>' token yields the recovered client identity and four-part version. Any malformed token — empty string, missing a part, an extra trailing delimiter, a leading delimiter, or a zero identity — is rejected as a neutral invalid_token error with no fields recovered.",
    "cases": [
        {
            "input": {"action": "decode_token", "token": "8e8a09e4-eddf-4c33-a1d8-1e399b763fd4%1.2.3.4"},
            "expected_output": "client_id=8e8a09e4-eddf-4c33-a1d8-1e399b763fd4\nversion=1.2.3.4\n"
        },
        {
            "input": {"action": "decode_token", "token": ""},
            "expected_output": "error=invalid_token\n"
        },
        {
            "input": {"action": "decode_token", "token": "8e8a09e4-eddf-4c33-a1d8-1e399b763fd4%"},
            "expected_output": "error=invalid_token\n"
        },
        {
            "input": {"action": "decode_token", "token": "%1.1.1.1"},
            "expected_output": "error=invalid_token\n"
        },
        {
            "input": {"action": "decode_token", "token": "8e8a09e4-eddf-4c33-a1d8-1e399b763fd4%1.1.1.1%"},
            "expected_output": "error=invalid_token\n"
        },
        {
            "input": {"action": "decode_token", "token": "%8e8a09e4-eddf-4c33-a1d8-1e399b763fd4%1.1.1.1"},
            "expected_output": "error=invalid_token\n"
        }
    ]
}
```

---

### Feature 2: Module Manifest Compatibility

**As a developer**, I want to summarize, compare, and serialize the set of installed game modules, so a client and host can decide whether they may share a session.

**Expected Behavior / Usage:**

A **module manifest** is a list of modules. Each module has an **id** (string), an **official** flag (boolean) marking it as a base-game module versus a third-party one, and a four-part numeric **version**. Exactly one module is expected to be flagged official; its version is treated as the **game version**. The three leaf operations below summarize a manifest, compare two manifests, and serialize a manifest.

*2.1 Summarize Manifest — report module count and game version*

Given a manifest, report the number of modules and the game version. The game version is the version of the module flagged official, formatted as four dot-separated numbers. The output is a `module_count=` line followed by a `game_version=` line.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_modules_inspect.json`

```json
{
    "description": "Summarize an installed module set into the count of modules and the game version. The game version is taken from the single module flagged as official; each module carries an id, an official flag, and a four-part numeric version. The reported game version is the official module's version formatted as four dot-separated numbers.",
    "cases": [
        {
            "input": {"action": "inspect_modules", "modules": [{"id": "M1", "official": [the boolean literal for successful compatibility check — confirm with the output parser spec], "version": "1.2.3.4"}, {"id": "M2", "official": [the boolean literal for successful compatibility check — confirm with the output parser spec], "version": "1.0.1.23"}]},
            "expected_output": "module_count=2\ngame_version=1.2.3.4\n"
        },
        {
            "input": {"action": "inspect_modules", "modules": [{"id": "Core", "official": [the boolean literal for successful compatibility check — confirm with the output parser spec], "version": "1.2.4.4"}, {"id": "Mod", "official": [the boolean literal for successful compatibility check — confirm with the output parser spec], "version": "1.0.2.23"}]},
            "expected_output": "module_count=2\ngame_version=1.2.4.4\n"
        }
    ]
}
```

*2.2 Compare Manifests — mutual compatibility and game-version agreement*

Given two manifests (`left` and `right`), report three booleans: whether left is compatible with right, whether right is compatible with left, and whether their game versions agree. One manifest is compatible with another only when **every** module in it — matched on id, official flag, and full four-part version — is also present in the other; this is checked in both directions. Game versions agree only when the official module's version is identical in all four components across the two manifests. The output is three lines: `compatible_left_to_right=`, `compatible_right_to_left=`, `game_version_match=`, each `[the boolean literal for successful compatibility check — confirm with the output parser spec]` or `[the boolean literal for successful compatibility check — confirm with the output parser spec]`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_modules_compare.json`

```json
{
    "description": "Compare two installed module sets for compatibility and for game-version agreement. Two sets are compatible only when every module (id, official flag, and full four-part version) in one set is also present in the other; compatibility is checked in both directions. Game versions agree only when the official module's version is identical across the two sets. Identical sets are mutually compatible and version-matching; sets differing in any version component are neither.",
    "cases": [
        {
            "input": {"action": "compare_modules", "left": [{"id": "M1", "official": [the boolean literal for successful compatibility check — confirm with the output parser spec], "version": "1.2.3.4"}, {"id": "M2", "official": [the boolean literal for successful compatibility check — confirm with the output parser spec], "version": "1.0.1.23"}], "right": [{"id": "M1", "official": [the boolean literal for successful compatibility check — confirm with the output parser spec], "version": "1.2.3.4"}, {"id": "M2", "official": [the boolean literal for successful compatibility check — confirm with the output parser spec], "version": "1.0.1.23"}]},
            "expected_output": "compatible_left_to_right=[the boolean literal for successful compatibility check — confirm with the output parser spec]\ncompatible_right_to_left=[the boolean literal for successful compatibility check — confirm with the output parser spec]\ngame_version_match=[the boolean literal for successful compatibility check — confirm with the output parser spec]\n"
        },
        {
            "input": {"action": "compare_modules", "left": [{"id": "M1", "official": [the boolean literal for successful compatibility check — confirm with the output parser spec], "version": "1.2.3.4"}, {"id": "M2", "official": [the boolean literal for successful compatibility check — confirm with the output parser spec], "version": "1.0.1.23"}], "right": [{"id": "M1", "official": [the boolean literal for successful compatibility check — confirm with the output parser spec], "version": "1.2.4.4"}, {"id": "M2", "official": [the boolean literal for successful compatibility check — confirm with the output parser spec], "version": "1.0.2.23"}]},
            "expected_output": "compatible_left_to_right=[the boolean literal for successful compatibility check — confirm with the output parser spec]\ncompatible_right_to_left=[the boolean literal for successful compatibility check — confirm with the output parser spec]\ngame_version_match=[the boolean literal for successful compatibility check — confirm with the output parser spec]\n"
        }
    ]
}
```

*2.3 Serialize Manifest — portable round-trip that distinguishes manifests*

Each manifest can be serialized to a portable payload and read back. A payload read back must yield a manifest equal (mutually compatible) to the manifest it came from. Two manifests that differ in any module version must produce distinct payloads, so a payload unambiguously identifies its source manifest. Given two differing manifests (`left`, `right`), the output reports `left_roundtrip_equal=`, `right_roundtrip_equal=`, and `payloads_distinct=`, each `[the boolean literal for successful compatibility check — confirm with the output parser spec]` or `[the boolean literal for successful compatibility check — confirm with the output parser spec]`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_modules_serialize.json`

```json
{
    "description": "Serialize each of two module sets to a portable payload and read it back. A payload deserialized back into a module set must be equal (mutually compatible) to the original set it came from. Two module sets that differ in any module version must produce distinct serialized payloads, so a payload unambiguously represents the set that produced it.",
    "cases": [
        {
            "input": {"action": "serialize_modules", "left": [{"id": "M1", "official": [the boolean literal for successful compatibility check — confirm with the output parser spec], "version": "1.2.3.4"}, {"id": "M2", "official": [the boolean literal for successful compatibility check — confirm with the output parser spec], "version": "1.0.1.23"}], "right": [{"id": "M1", "official": [the boolean literal for successful compatibility check — confirm with the output parser spec], "version": "1.2.4.4"}, {"id": "M2", "official": [the boolean literal for successful compatibility check — confirm with the output parser spec], "version": "1.0.2.23"}]},
            "expected_output": "left_roundtrip_equal=[the boolean literal for successful compatibility check — confirm with the output parser spec]\nright_roundtrip_equal=[the boolean literal for successful compatibility check — confirm with the output parser spec]\npayloads_distinct=[the boolean literal for successful compatibility check — confirm with the output parser spec]\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the identity-token codec and the module-manifest compatibility operations as separate domains, with the manifest source injected rather than hard-wired. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint — small, separated units rather than one monolithic file.

2. **The Execution/Test Adapter:** A runnable program that reads a single JSON command object from stdin, dispatches on its `action`, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. All native errors are translated at this boundary into neutral `error=<category>` lines (`argument_null`, `invalid_token`, …) with parameter names in separate fields — no host-language exception identity appears in stdout. This adapter is logically and physically separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_token_encode.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_token_encode@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the output ordering and key naming convention used in the standard identity response handler
- apply the same version format expected by the legacy authentication proxy
