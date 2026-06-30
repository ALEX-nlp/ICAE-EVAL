## Product Requirement Document

# JSON Web Token Command-Line Encoder and Decoder - Black-Box Behavior Contract

## Project Goal

Build a command-line JSON Web Token utility that allows developers to create, inspect, and validate signed JWTs without manually constructing token headers, parsing claims, loading key material, or writing signature verification glue code.

---

## Background & Problem

Without this tool, developers are forced to hand-assemble JWT headers and claims, base64url encode data, manage HMAC or asymmetric signing keys, and decode token payloads with ad hoc scripts. This leads to repetitive shell work, fragile validation steps, and easy mistakes when handling timestamps, structured JSON claims, or key files.

With this tool, developers can pass token inputs as command-line arguments or JSON payloads, receive signed tokens, decode existing tokens into readable structures, and verify signatures using shared secrets or public keys.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section re[check specific claim presence] a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

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

### Feature 1: Encode Tokens with Mixed Claims

**As a developer**, I want to sign a JWT from standard registered claims, custom key-value claims, and an object-shaped JSON payload, so I can produce a token whose header and payload preserve the intended data types.

**Expected Behavior / Usage:**

The adapter accepts an encode-and-decode scenario containing token creation arguments, then verifies the produced token using the supplied decoding arguments. It must render the selected decoded header and claim values as newline-separated `key=value` lines. String claims remain strings, numeric claims remain numbers, booleans remain booleans, arrays and objects remain structured JSON values, and the key identifier is [check specific claim presence] in the decoded header when provided. Automatically added issue time may be rendered as a presence signal rather than a wall-clock-specific value.

**Test Cases:** `rcb_tests/public_test_cases/feature1_encode_mixed_claims.json`

```json
{
  "description": "Encode a signed token from registered claims, typed custom claims, and a JSON object payload, then decode it to verify the externally visible header and payload fields.",
  "cases": [
    {
      "input": {"action":"encode_then_decode","encode_args":["encode","-S","1234567890","-A","HS256","-a","yolo","-e","1893456000","-i","yolo-service","-k","1234","-n","1542492313","--jti","yolo-jti","-P","this=that","-P","number=10","-P","array=[1, 2, 3]","-P","object={\"foo\": \"bar\"}","-s","yolo-subject","{\"test\":\"json value\",\"bool\":true,\"json_number\":1}"],"decode_args":["decode","-S","1234567890","-A","HS256"],"report":["status","header.alg","header.kid","claim.aud","claim.iss","claim.sub","claim.nbf","claim.exp","claim.jti","claim.this","claim.test","claim.bool","claim.json_number","claim.number","claim.array","claim.object.foo","claim.iat.presence"]},
      "expected_output": "status=valid\nheader.alg=HS256\nheader.kid=1234\nclaim.aud=yolo\nclaim.iss=yolo-service\nclaim.sub=yolo-subject\nclaim.nbf=1542492313\nclaim.exp=1893456000\nclaim.jti=yolo-jti\nclaim.this=that\nclaim.test=json value\nclaim.bool=true\nclaim.json_number=1\nclaim.number=10\nclaim.array=[1,2,3]\nclaim.object.foo=bar\nclaim.iat=[check specific claim presence]\n"
    }
  ]
}
```

---

### Feature 2: Automatic and Optional Time Claims

**As a developer**, I want the encoder to manage issue and expiration time claims predictably, so I can rely on safe defaults while still disabling or overriding automatic fields when necessary.

**Expected Behavior / Usage:**

The adapter accepts an encode-and-decode scenario and renders whether automatic time claims are [check specific claim presence]. When expiration is requested without an explicit timestamp, the output must show a [check specific claim presence] numeric expiration claim and a [check specific claim presence] numeric issue-time claim. When issue-time creation is explicitly disabled, the decoded payload must omit the issue-time claim while still validating successfully if the expiration claim is [check specific claim presence].

**Test Cases:** `rcb_tests/public_test_cases/feature2_automatic_time_claims.json`

```json
{
  "description": "Encode tokens using automatic time-claim behavior and render whether issue-time and expiration claims are [check specific claim presence] after decoding.",
  "cases": [
    {
      "input": {"action":"encode_then_decode","encode_args":["encode","--exp","-S","1234567890"],"decode_args":["decode","-S","1234567890"],"report":["status","claim.iat.presence","claim.exp.presence"]},
      "expected_output": "status=valid\nclaim.iat=[check specific claim presence]\nclaim.exp=[check specific claim presence]\n"
    },
    {
      "input": {"action":"encode_then_decode","encode_args":["encode","--no-iat","--exp","-S","1234567890"],"decode_args":["decode","-S","1234567890"],"report":["status","claim.iat.presence","claim.exp.presence"]},
      "expected_output": "status=valid\nclaim.iat=[check specific claim presence]\nclaim.exp=[check specific claim presence]\n"
    }
  ]
}
```

---

### Feature 3: Relative Time Expressions

**As a developer**, I want relative duration strings for expiration and not-before claims, so I can specify validity windows without calculating Unix timestamps manually.

**Expected Behavior / Usage:**

The adapter accepts an encode-and-decode scenario using human-readable relative durations. It must render the numeric difference between the generated issue-time claim and the generated expiration or not-before claim. A relative expiration of ten minutes minus thirty seconds must produce a 570-second difference, and a relative not-before value of five minutes must produce a 300-second difference.

**Test Cases:** `rcb_tests/public_test_cases/feature3_relative_time_expressions.json`

```json
{
  "description": "Encode tokens with relative duration expressions for time-based claims and render the decoded second offsets from the generated issue time.",
  "cases": [
    {
      "input": {"action":"encode_then_decode","encode_args":["encode","-S","1234567890","-e","+10 min -30 sec"],"decode_args":["decode","-S","1234567890"],"report":["status","claim.exp_minus_iat"]},
      "expected_output": "status=valid\nclaim.exp_minus_iat=570\n"
    },
    {
      "input": {"action":"encode_then_decode","encode_args":["encode","-S","1234567890","--exp","-n","+5 min"],"decode_args":["decode","-S","1234567890"],"report":["status","claim.nbf_minus_iat"]},
      "expected_output": "status=valid\nclaim.nbf_minus_iat=300\n"
    }
  ]
}
```

---

### Feature 4: Decode and Validate Existing Tokens

**As a developer**, I want to decode existing JWT strings with or without signature verification, so I can inspect token contents and distinguish valid, invalid-signature, and accepted-unverified cases.

**Expected Behavior / Usage:**

The adapter accepts decode scenarios containing the token string and optional verification inputs. It must trim leading and trailing whitespace from token input before decoding. When the supplied secret and algorithm match the token, output reports a valid status and selected header or claim values. When no secret is supplied, the token is decoded without signature verification and still reports as valid. When a mismatching secret is supplied, the output must use a language-neutral error category while still reporting the decoded payload fields that are externally visible.

**Test Cases:** `rcb_tests/public_test_cases/feature4_decode_existing_tokens.json`

```json
{
  "description": "Decode existing token strings under verified, unverified, whitespace-trimmed, and invalid-signature conditions and render observable status plus selected fields.",
  "cases": [
    {
      "input": {"action":"decode","args":["decode","eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJleHAiOjE4OTM0NTYwMDAsImlhdCI6MTU0MjQ5MjMxMywidGhpcyI6InRoYXQifQ.YTWit46_AEMMVv0P48NeJJIqXmMHarGjfRxtR7jLlxE","-S","1234567890","-A","HS256"],"report":["status","header.alg","header.typ","claim.exp","claim.iat","claim.this"]},
      "expected_output": "status=valid\nheader.alg=HS256\nheader.typ=JWT\nclaim.exp=1893456000\nclaim.iat=1542492313\nclaim.this=that\n"
    },
    {
      "input": {"action":"decode","args":["decode","eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ0aGlzIjoidGhhdCJ9.AdAECLE_4iRa0uomMEdsMV2hDXv1vhLpym567-AzhrM","-S","yolo","-A","HS256"],"report":["status","error","header.alg","claim.this"]},
      "expected_output": "status=invalid\nerror=invalid_signature\nheader.alg=HS256\nclaim.this=that\n"
    }
  ]
}
```

---

### Feature 5: Key Material Loaded from Files

**As a developer**, I want signing and verification keys to be loaded from file references, so I can use binary HMAC secrets and asymmetric private/public key pairs without embedding key bytes in arguments.

**Expected Behavior / Usage:**

The adapter accepts encode-and-decode scenarios where key arguments reference files. HMAC key files must be usable for both signing and verification. RSA and ECDSA private-key files must sign tokens that validate with the corresponding public-key files. Output reports successful validation plus the decoded signing algorithm and selected payload value.

**Test Cases:** `rcb_tests/public_test_cases/feature5_key_files.json`

```json
{
  "description": "Encode tokens using key material loaded from files and verify the produced tokens with the matching file-backed verification input.",
  "cases": [
    {
      "input": {"action":"encode_then_decode","encode_args":["encode","-A","RS256","--exp","-S","@./tests/private_rsa_key.der","{\"field\":\"value\"}"],"decode_args":["decode","-S","@./tests/public_rsa_key.der","-A","RS256"],"report":["status","header.alg","claim.field"]},
      "expected_output": "status=valid\nheader.alg=RS256\nclaim.field=value\n"
    }
  ]
}
```

---

### Feature 6: Input Validation Errors

**As a developer**, I want invalid claim and timestamp inputs to be rejected with neutral error categories, so I can report bad user input without exposing runtime-specific exception text.

**Expected Behavior / Usage:**

The adapter accepts encode scenarios with invalid user input. A custom claim must contain exactly one key/value separator. A timestamp field must be either an integer Unix timestamp or a recognized relative duration expression. Invalid inputs must be rendered as language-neutral `error=...` lines and include the offending input field category.

**Test Cases:** `rcb_tests/public_test_cases/feature6_input_validation_errors.json`

```json
{
  "description": "Attempt to encode tokens with invalid custom-claim and timestamp arguments and render normalized input-validation errors.",
  "cases": [
    {
      "input": {"action":"encode_error","args":["encode","-S","1234567890","-P","this"],"report":["error"]},
      "expected_output": "error=invalid_payload_item\n"
    },
    {
      "input": {"action":"encode_error","args":["encode","-S","1234567890","-e","yolo"],"report":["error"]},
      "expected_output": "error=invalid_timestamp_or_duration\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same format as caused by the default header module
- adhere to the compact list style established in module payload_utils
