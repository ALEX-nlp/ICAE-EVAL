## Product Requirement Document

# JSON Web Token Toolkit - Signing, Verification and Key Conversion

## Project Goal

Build a self-contained JSON Web Token (JWT) toolkit that lets developers issue, verify and inspect signed tokens across the full set of standard signature algorithms (HMAC, RSA PKCS#1 v1.5, RSA-PSS, ECDSA and EdDSA) without hand-rolling base64url framing, signature math or claim-validation logic. The same toolkit converts signing keys to and from the standard JWK JSON representation so keys can be transported and re-loaded.

---

## Background & Problem

Without a dedicated toolkit, developers who need stateless authentication tokens are forced to assemble the compact serialization by hand: base64url-encode a header and a payload, compute a cryptographic signature with the correct hash and padding scheme for each algorithm, concatenate the three segments, and then reverse every step (plus revalidate the signature and every time-sensitive claim) on the receiving side. This is repetitive, easy to get subtly wrong, and a frequent source of security bugs (accepting expired tokens, mishandling not-before windows, or trusting an unverified signature).

With this toolkit, issuing a token is a single call that takes a payload, an algorithm and a key and returns the finished compact string; verification is a single call that re-checks the signature, enforces the temporal claims, and hands back the decoded claim set. Keys can be serialized to JWK and parsed back, so the same material works across services.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain has several distinct responsibilities (algorithm implementations, key models, claim validation, base64url/JSON framing, and an execution adapter), so it MUST be organized into clearly separated modules rather than a single "god file". Keep the cryptographic core, the key models and the I/O adapter in distinct units.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box contract for the execution adapter only**, not the internal data model. The core signing/verification logic MUST be completely decoupled from stdin/stdout and from the JSON command envelope. The adapter is solely responsible for translating a JSON command into idiomatic calls on the core, and for rendering results (and normalized errors) as text.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Separate command parsing, key construction, signing, verification, claim validation and output formatting.
   - **Open/Closed Principle (OCP):** Adding a new signature algorithm must not require modifying existing algorithm code or the verification flow.
   - **Liskov Substitution Principle (LSP):** Every algorithm must be usable wherever the algorithm abstraction is expected; every key type wherever the key abstraction is expected.
   - **Interface Segregation Principle (ISP):** Keep the algorithm and key abstractions small (sign / verify; export / import).
   - **Dependency Inversion Principle (DIP):** High-level sign/verify flows depend on algorithm and key abstractions, not on concrete crypto primitives or on the I/O layer.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core must be elegant and idiomatic to the target language, hiding base64url and ASN.1/PEM parsing details.
   - **Resilience:** Failures (bad signature, expired token, not-yet-active token, unparseable key/JWK, unsupported payload type) must be modeled as explicit, typed error conditions rather than generic faults.

---

## Execution Adapter I/O Convention

The execution adapter reads exactly one JSON object ("command") from stdin and writes a plain-text result to stdout. Every command carries an `op` field selecting the operation; the remaining fields are operation-specific and are described per feature below. Keys are supplied as a small object `{"kind": <category>, ...}` where `kind` is one of `secret`, `rsa_private`, `rsa_public`, `ec_private`, `ec_public`, `ed_private`, `ed_public`; a `secret` carries a `secret` string, every other kind carries a PEM string under `pem`. Algorithm names are the standard JWT identifiers (`HS256`/`HS384`/`HS512`, `RS256`/`RS384`/`RS512`, `PS256`/`PS384`/`PS512`, `ES256`/`ES384`/`ES512`/`ES256K`, `EdDSA`).

Output is line-oriented and deterministic. A successful signing emits the compact token on a single line. A successful verification emits `alg=<algorithm>` followed by `payload=<canonical-json>` (object keys sorted). A JWK export emits the JWK as a single canonical-json line. A JWK import emits `kind=<category>` and `kty=<key-type>`. Any failure is rendered as a normalized, language-neutral category and never leaks host runtime details: `error=token_expired`, `error=token_not_active`, `error=invalid_payload_type`, `error=invalid_token` (with a `reason=<slug>` second line, e.g. `reason=invalid_signature` or `reason=expired_issue_at`), or `error=parse_error` (with a `reason=<slug>`).

---

## Core Features

### Feature 1: Issue a signed compact token

**As a developer**, I want to turn a payload and a key into a finished signed token string, so I can hand clients a self-describing credential without assembling the serialization myself.

**Expected Behavior / Usage:**

A signing command (`op: sign`) takes an `algorithm`, a `key` and a `payload` (and, here, `no_iat: true` to suppress the automatic issued-at stamp so the output is fully deterministic). The result is the three-segment compact serialization `header.payload.signature`, base64url-encoded and unpadded, emitted on one line. The header always advertises the algorithm and a token type of `JWT`. Signatures for HMAC, RSA PKCS#1 v1.5, deterministic ECDSA and EdDSA are byte-for-byte reproducible for a given key and payload; the cases below pin those exact strings. (RSA-PSS signing is randomized by design, so it is covered under verification rather than by a fixed signature.)

*1.1 HMAC shared-secret signing — issue a token with HS256/HS384/HS512 from a shared secret*

The key is a shared secret string. Each HMAC variant selects a different SHA-2 digest and yields a distinct signature segment over the same header and payload.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_sign_hmac.json`

```json
{
  "description": "Issue a compact token from a map payload using an HMAC shared-secret algorithm; the output is the full compact serialization (header.payload.signature).",
  "cases": [
    {
      "input": {
        "op": "sign",
        "algorithm": "HS256",
        "key": {
          "kind": "secret",
          "secret": "secret passphrase"
        },
        "payload": {
          "foo": "bar"
        },
        "no_iat": true
      },
      "expected_output": "[a specific token output for a secret payload]\n"
    }
  ]
}
```

*1.2 RSA PKCS#1 v1.5 signing — issue a token with RS256/RS384/RS512 from an RSA private key*

The key is an RSA private key in PEM form. PKCS#1 v1.5 padding is deterministic, so the signature is a fixed function of key, payload and digest.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_sign_rsa_pkcs1.json`

```json
{
  "description": "Issue a compact token from a map payload using an RSA PKCS#1 v1.5 private key; deterministic signature.",
  "cases": [
    {
      "input": {
        "op": "sign",
        "algorithm": "RS256",
        "key": {
          "kind": "rsa_private",
          "pem": "-----BEGIN PRIVATE KEY-----\nMIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQC7VJTUt9Us8cKj\nMzEfYyjiWA4R4/M2bS1GB4t7NXp98C3SC6dVMvDuictGeurT8jNbvJZHtCSuYEvu\nNMoSfm76oqFvAp8Gy0iz5sxjZmSnXyCdPEovGhLa0VzMaQ8s+CLOyS56YyCFGeJZ\nqgtzJ6GR3eqoYSW9b9UMvkBpZODSctWSNGj3P7jRFDO5VoTwCQAWbFnOjDfH5Ulg\np2PKSQnSJP3AJLQNFNe7br1XbrhV//eO+t51mIpGSDCUv3E0DDFcWDTH9cXDTTlR\nZVEiR2BwpZOOkE/Z0/BVnhZYL71oZV34bKfWjQIt6V/isSMahdsAASACp4ZTGtwi\nVuNd9tybAgMBAAECggEBAKTmjaS6tkK8BlPXClTQ2vpz/N6uxDeS35mXpqasqskV\nlaAidgg/sWqpjXDbXr93otIMLlWsM+X0CqMDgSXKejLS2jx4GDjI1ZTXg++0AMJ8\nsJ74pWzVDOfmCEQ/7wXs3+cbnXhKriO8Z036q92Qc1+N87SI38nkGa0ABH9CN83H\nmQqt4fB7UdHzuIRe/me2PGhIq5ZBzj6h3BpoPGzEP+x3l9YmK8t/1cN0pqI+dQwY\ndgfGjackLu/2qH80MCF7IyQaseZUOJyKrCLtSD/Iixv/hzDEUPfOCjFDgTpzf3cw\nta8+oE4wHCo1iI1/4TlPkwmXx4qSXtmw4aQPz7IDQvECgYEA8KNThCO2gsC2I9PQ\nDM/8Cw0O983WCDY+oi+7JPiNAJwv5DYBqEZB1QYdj06YD16XlC/HAZMsMku1na2T\nN0driwenQQWzoev3g2S7gRDoS/FCJSI3jJ+kjgtaA7Qmzlgk1TxODN+G1H91HW7t\n0l7VnL27IWyYo2qRRK3jzxqUiPUCgYEAx0oQs2reBQGMVZnApD1jeq7n4MvNLcPv\nt8b/eU9iUv6Y4Mj0Suo/AU8lYZXm8ubbqAlwz2VSVunD2tOplHyMUrtCtObAfVDU\nAhCndKaA9gApgfb3xw1IKbuQ1u4IF1FJl3VtumfQn//LiH1B3rXhcdyo3/vIttEk\n48RakUKClU8CgYEAzV7W3COOlDDcQd935DdtKBFRAPRPAlspQUnzMi5eSHMD/ISL\nDY5IiQHbIH83D4bvXq0X7qQoSBSNP7Dvv3HYuqMhf0DaegrlBuJllFVVq9qPVRnK\nxt1Il2HgxOBvbhOT+9in1BzA+YJ99UzC85O0Qz06A+CmtHEy4aZ2kj5hHjECgYEA\nmNS4+A8Fkss8Js1RieK2LniBxMgmYml3pfVLKGnzmng7H2+cwPLhPIzIuwytXywh\n2bzbsYEfYx3EoEVgMEpPhoarQnYPukrJO4gwE2o5Te6T5mJSZGlQJQj9q4ZB2Dfz\net6INsK0oG8XVGXSpQvQh3RUYekCZQkBBFcpqWpbIEsCgYAnM3DQf3FJoSnXaMhr\nVBIovic5l0xFkEHskAjFTevO86Fsz1C2aSeRKSqGFoOQ0tmJzBEs1R6KqnHInicD\nTQrKhArgLXX4v3CddjfTRJkFWDbE/CkvKZNOrcf1nhaGCPspRJj2KUkj1Fhl9Cnc\ndn/RsYEONbwQSjIfMPkvxF+8HQ==\n-----END PRIVATE KEY-----"
        },
        "payload": {
          "foo": "bar"
        },
        "no_iat": true
      },
      "expected_output": "[a specific token output for a secret payload]\n"
    }
  ]
}
```

*1.3 ECDSA signing — issue a token with ES256/ES384/ES512/ES256K from an elliptic-curve private key*

The key is an elliptic-curve private key in PEM form. Signing is deterministic (RFC 6979 style), so each curve/digest pairing produces a fixed fixed-length signature; `ES256K` uses the secp256k1 curve while `ES256/384/512` use the P-256/P-384/P-521 curves.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_sign_ecdsa.json`

```json
{
  "description": "Issue a compact token from a map payload using an elliptic-curve private key (deterministic ECDSA) across the P-256, P-384, P-521 and secp256k1 curves.",
  "cases": [
    {
      "input": {
        "op": "sign",
        "algorithm": "ES256",
        "key": {
          "kind": "ec_private",
          "pem": "-----BEGIN PRIVATE KEY-----\nMIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgevZzL1gdAFr88hb2\nOF/2NxApJCzGCEDdfSp6VQO30hyhRANCAAQRWz+jn65BtOMvdyHKcvjBeBSDZH2r\n1RTwjmYSi9R/zpBnuQ4EiMnCqfMPWiZqB4QdbAd0E7oH50VpuZ1P087G\n-----END PRIVATE KEY-----"
        },
        "payload": {
          "foo": "bar"
        },
        "no_iat": true
      },
      "expected_output": "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJmb28iOiJiYXIifQ.mUJVRsRm7VXpxNHfVWdU43BJtuV8MKDcNMSr9agp_-M4FsamUibn04y8PgNzQizdw9BWTwkjQcpm1Go1LHPMyg\n"
    },
    {
      "input": {
        "op": "sign",
        "algorithm": "ES256K",
        "key": {
          "kind": "ec_private",
          "pem": "-----BEGIN EC PRIVATE KEY-----\nMHQCAQEEINCRiJnNDnzfo2So2tWY4AIuzeC2ZBp/hmMDcZz3Fh45oAcGBSuBBAAK\noUQDQgAE0aELkvG/Xeo5y6o0WXRAjlediLptGz7Q8zjDmpGFXkKBYZ6IiL7JJ2Tk\ncHzd83bmeUeGX33RGTYFPXs5t/VBnw==\n-----END EC PRIVATE KEY-----"
        },
        "payload": {
          "foo": "bar"
        },
        "no_iat": true
      },
      "expected_output": "[a specific token output for a secret payload]\n"
    }
  ]
}
```

*1.4 EdDSA signing — issue a token with Ed25519 from an Edwards-curve private key*

The key is an Ed25519 private key in PEM form. EdDSA is deterministic and produces a fixed signature segment.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_sign_eddsa.json`

```json
{
  "description": "Issue a compact token from a map payload using an Edwards-curve (Ed25519) private key.",
  "cases": [
    {
      "input": {
        "op": "sign",
        "algorithm": "EdDSA",
        "key": {
          "kind": "ed_private",
          "pem": "-----BEGIN PRIVATE KEY-----\nMC4CAQAwBQYDK2VwBCIEICXCjBHvjArjXquUI5jo3x5SHI4ofZA2azwJ39IC/Qct\n-----END PRIVATE KEY-----"
        },
        "payload": {
          "foo": "bar"
        },
        "no_iat": true
      },
      "expected_output": "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJmb28iOiJiYXIifQ.6Bw5vvdpJ_kgDwidU1l7aagtKCD9-QIJxrz44HXxtc6OJoOmImNko0dgXYpTtXhcEuX7vamSR5JPfGP1Q9d9DA\n"
    }
  ]
}
```

---

### Feature 2: Verify a token and extract its claims

**As a developer**, I want to confirm a token's signature with the matching key and read back its claims, so I can trust an incoming credential.

**Expected Behavior / Usage:**

A verification command (`op: verify`) takes a compact `token` and a `key`. When the signature is valid the adapter emits two lines: `alg=<algorithm>` taken from the verified header, and `payload=<canonical-json>` containing the decoded claim set with object keys sorted. Verification must use the public half of the key pair for the asymmetric families. The algorithm line is a framework-observable signal: a stub that returned a hard-coded payload without parsing and checking the token could not reproduce it together with the correct claim set.

*2.1 HMAC verification — validate HS256/HS384/HS512 with the shared secret*

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_verify_hmac.json`

```json
{
  "description": "Validate an HMAC-signed compact token with the shared secret and return the embedded algorithm and claims.",
  "cases": [
    {
      "input": {
        "op": "verify",
        "token": "[a specific token output for a secret payload]",
        "key": {
          "kind": "secret",
          "secret": "secret passphrase"
        }
      },
      "expected_output": "alg=HS256\npayload={\"foo\":\"bar\"}\n"
    }
  ]
}
```

*2.2 RSA PKCS#1 v1.5 verification — validate RS256/RS384/RS512 with the RSA public key*

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_verify_rsa_pkcs1.json`

```json
{
  "description": "Validate an RSA PKCS#1 v1.5 signed compact token with the RSA public key and return algorithm and claims.",
  "cases": [
    {
      "input": {
        "op": "verify",
        "token": "[a specific token output for a secret payload]",
        "key": {
          "kind": "rsa_public",
          "pem": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAu1SU1LfVLPHCozMxH2Mo\n4lgOEePzNm0tRgeLezV6ffAt0gunVTLw7onLRnrq0/IzW7yWR7QkrmBL7jTKEn5u\n+qKhbwKfBstIs+bMY2Zkp18gnTxKLxoS2tFczGkPLPgizskuemMghRniWaoLcyeh\nkd3qqGElvW/VDL5AaWTg0nLVkjRo9z+40RQzuVaE8AkAFmxZzow3x+VJYKdjykkJ\n0iT9wCS0DRTXu269V264Vf/3jvredZiKRkgwlL9xNAwxXFg0x/XFw005UWVRIkdg\ncKWTjpBP2dPwVZ4WWC+9aGVd+Gyn1o0CLelf4rEjGoXbAAEgAqeGUxrcIlbjXfbc\nmwIDAQAB\n-----END PUBLIC KEY-----"
        }
      },
      "expected_output": "alg=RS256\npayload={\"foo\":\"bar\"}\n"
    }
  ]
}
```

*2.3 ECDSA verification — validate ES256/ES384/ES512/ES256K with the matching public key*

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_verify_ecdsa.json`

```json
{
  "description": "Validate an ECDSA signed compact token with the matching public key across P-256, P-384, P-521 and secp256k1.",
  "cases": [
    {
      "input": {
        "op": "verify",
        "token": "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJmb28iOiJiYXIifQ.mUJVRsRm7VXpxNHfVWdU43BJtuV8MKDcNMSr9agp_-M4FsamUibn04y8PgNzQizdw9BWTwkjQcpm1Go1LHPMyg",
        "key": {
          "kind": "ec_public",
          "pem": "-----BEGIN PUBLIC KEY-----\nMFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEEVs/o5+uQbTjL3chynL4wXgUg2R9\nq9UU8I5mEovUf86QZ7kOBIjJwqnzD1omageEHWwHdBO6B+dFabmdT9POxg==\n-----END PUBLIC KEY-----"
        }
      },
      "expected_output": "alg=ES256\npayload={\"foo\":\"bar\"}\n"
    }
  ]
}
```

*2.4 RSA-PSS verification — validate PS256/PS384/PS512 with the RSA public key*

RSA-PSS signatures carry a random salt and differ run to run, but any well-formed PSS signature verifies against the public key; these cases confirm that path.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_verify_rsa_pss.json`

```json
{
  "description": "Validate an RSA-PSS signed compact token with the RSA public key and return algorithm and claims.",
  "cases": [
    {
      "input": {
        "op": "verify",
        "token": "eyJhbGciOiJQUzI1NiIsInR5cCI6IkpXVCJ9.eyJmb28iOiJiYXIifQ.JYyEew2G-Bb6p8L7BCfZ79o-42HlMynq7zS_Rc_3q3M2CjvaEY1F_ratOPlveR8wqTAN6swxVfx48ZdRnV282EckX9JOel_MjQH87Iutauj-v6D90xLW2IZt-T2gOkqIo2AQ2i1PeM47jCwbawwuYyy_G433-Rw3tP2j6neNV9tTIAjQicaDVxeqKcvF3l1YjsSLqrLGB4rHLZcCv47CURpO9ZB7WgmOvP_vqKJB_Pcoo6iMI0EIW6REYFIXF1Wxs8Xg9Schyb6p1WjRD4fGPDW9m_uqoaOw9TfAh4GKeWYXE5sw1EZH2l5grStK3_dA0bLeLCOKZkZJZm-TD_cyRw",
        "key": {
          "kind": "rsa_public",
          "pem": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAu1SU1LfVLPHCozMxH2Mo\n4lgOEePzNm0tRgeLezV6ffAt0gunVTLw7onLRnrq0/IzW7yWR7QkrmBL7jTKEn5u\n+qKhbwKfBstIs+bMY2Zkp18gnTxKLxoS2tFczGkPLPgizskuemMghRniWaoLcyeh\nkd3qqGElvW/VDL5AaWTg0nLVkjRo9z+40RQzuVaE8AkAFmxZzow3x+VJYKdjykkJ\n0iT9wCS0DRTXu269V264Vf/3jvredZiKRkgwlL9xNAwxXFg0x/XFw005UWVRIkdg\ncKWTjpBP2dPwVZ4WWC+9aGVd+Gyn1o0CLelf4rEjGoXbAAEgAqeGUxrcIlbjXfbc\nmwIDAQAB\n-----END PUBLIC KEY-----"
        }
      },
      "expected_output": "alg=PS256\npayload={\"foo\":\"bar\"}\n"
    }
  ]
}
```

*2.5 EdDSA verification — validate Ed25519 with the Edwards-curve public key*

**Test Cases:** `rcb_tests/public_test_cases/feature2_5_verify_eddsa.json`

```json
{
  "description": "Validate an Ed25519 signed compact token with the Edwards-curve public key and return algorithm and claims.",
  "cases": [
    {
      "input": {
        "op": "verify",
        "token": "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJmb28iOiJiYXIifQ.6Bw5vvdpJ_kgDwidU1l7aagtKCD9-QIJxrz44HXxtc6OJoOmImNko0dgXYpTtXhcEuX7vamSR5JPfGP1Q9d9DA",
        "key": {
          "kind": "ed_public",
          "pem": "-----BEGIN PUBLIC KEY-----\nMCowBQYDK2VwAyEAEi7MNW0Q9T83UA3Rw+8DbspMgqeuxCqa2wXaWS+tHqY=\n-----END PUBLIC KEY-----"
        }
      },
      "expected_output": "alg=EdDSA\npayload={\"foo\":\"bar\"}\n"
    }
  ]
}
```

---

### Feature 3: Enforce time-sensitive claims during verification

**As a developer**, I want verification to automatically reject tokens that are expired or not yet active and to honor an issued-at lower bound, so I do not have to re-implement temporal checks at every call site.

**Expected Behavior / Usage:**

Verification inspects the standard temporal claims carried in the payload and compares them to the current time. Each check can be individually disabled through a boolean flag on the command, in which case the corresponding claim is ignored and the token verifies on signature alone. When a check fails the adapter emits the matching normalized error category instead of the claim set. Timestamps in the cases below are absolute seconds-since-epoch chosen far in the past or future so the outcome is independent of the wall clock.

*3.1 Expiration (exp) — reject a token past its expiry unless expiry checking is disabled*

A token whose `exp` is in the past is rejected with `error=token_expired`. A token whose `exp` is in the future returns its full claim set. Passing `check_exp: false` ignores `exp` entirely and returns the claims even for an expired token.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_exp.json`

```json
{
  "description": "Enforce the expiration (exp) claim during verification: a token past its expiry is rejected, a token within validity returns its claims, and expiry checking can be switched off.",
  "cases": [
    {
      "input": {
        "op": "verify",
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmb28iOiJiYXIiLCJleHAiOjEwMDAwMDAwMDB9.VzhO3OD13EEaSQ77BReTZnNDv9EtRxhegH1Y0T8nq7A",
        "key": {
          "kind": "secret",
          "secret": "secret passphrase"
        }
      },
      "expected_output": "error=token_expired\n"
    },
    {
      "input": {
        "op": "verify",
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmb28iOiJiYXIiLCJpYXQiOjE2MDAwMDAwMDAsImV4cCI6NDEwMjQ0NDgwMH0.0dGWV6Y1EMDkHtbLRB5O1eEL4ZiCivhGrKfKbaXimug",
        "key": {
          "kind": "secret",
          "secret": "secret passphrase"
        }
      },
      "expected_output": "alg=HS256\npayload={\"exp\":4102444800,\"foo\":\"bar\",\"iat\":1600000000}\n"
    },
    {
      "input": {
        "op": "verify",
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmb28iOiJiYXIiLCJleHAiOjEwMDAwMDAwMDB9.VzhO3OD13EEaSQ77BReTZnNDv9EtRxhegH1Y0T8nq7A",
        "key": {
          "kind": "secret",
          "secret": "secret passphrase"
        },
        "check_exp": false
      },
      "expected_output": "alg=HS256\npayload={\"exp\":1000000000,\"foo\":\"bar\"}\n"
    }
  ]
}
```

*3.2 Not-before (nbf) — reject a token whose activation time has not arrived unless the check is disabled*

A token whose `nbf` is in the future is rejected with `error=token_not_active`. A token whose `nbf` is already in the past returns its claim set. Passing `check_nbf: false` ignores `nbf` and returns the claims even before activation.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_nbf.json`

```json
{
  "description": "Enforce the not-before (nbf) claim during verification: a token not yet active is rejected, an already-active token returns its claims, and the not-before check can be switched off.",
  "cases": [
    {
      "input": {
        "op": "verify",
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmb28iOiJiYXIiLCJuYmYiOjQxMDI0NDQ4MDB9.nVD1NOgwZ3_B6qVB3Y0nVfz7bbU_vmuzM9gm9XN28n8",
        "key": {
          "kind": "secret",
          "secret": "secret passphrase"
        }
      },
      "expected_output": "error=token_not_active\n"
    },
    {
      "input": {
        "op": "verify",
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmb28iOiJiYXIiLCJuYmYiOjEwMDAwMDAwMDB9.j9cL7lSN2OhJUu7XjTDYmtQGhfxXaHArfxbggDBQzIQ",
        "key": {
          "kind": "secret",
          "secret": "secret passphrase"
        }
      },
      "expected_output": "alg=HS256\npayload={\"foo\":\"bar\",\"nbf\":1000000000}\n"
    },
    {
      "input": {
        "op": "verify",
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmb28iOiJiYXIiLCJuYmYiOjQxMDI0NDQ4MDB9.nVD1NOgwZ3_B6qVB3Y0nVfz7bbU_vmuzM9gm9XN28n8",
        "key": {
          "kind": "secret",
          "secret": "secret passphrase"
        },
        "check_nbf": false
      },
      "expected_output": "alg=HS256\npayload={\"foo\":\"bar\",\"nbf\":4102444800}\n"
    }
  ]
}
```

*3.3 Issued-at lower bound (issue_at) — require the token's issued-at to be at or after a threshold*

When the command supplies an `issue_at` threshold (seconds since epoch), the token passes only if its `iat` claim is at or after the threshold; an `iat` strictly before the threshold is rejected with `error=invalid_token` / `reason=expired_issue_at`. With no threshold supplied, the `iat` claim is not constrained, so even a future `iat` is accepted.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_issue_at.json`

```json
{
  "description": "Enforce an issued-at lower bound during verification: with a minimum issued-at threshold the token passes when its iat is at or after the threshold and is rejected when its iat predates it; with no threshold a future iat is accepted.",
  "cases": [
    {
      "input": {
        "op": "verify",
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmb28iOiJiYXIiLCJpYXQiOjE2MDAwMDAwMDB9.xI02uz2AqzPMpDdLTwzXo7raBheKETETCHCYHEyl1ZQ",
        "key": {
          "kind": "secret",
          "secret": "secret passphrase"
        },
        "issue_at": 1600000000
      },
      "expected_output": "alg=HS256\npayload={\"foo\":\"bar\",\"iat\":1600000000}\n"
    },
    {
      "input": {
        "op": "verify",
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmb28iOiJiYXIiLCJpYXQiOjE2MDAwMDAwMDB9.xI02uz2AqzPMpDdLTwzXo7raBheKETETCHCYHEyl1ZQ",
        "key": {
          "kind": "secret",
          "secret": "secret passphrase"
        },
        "issue_at": 1600000001
      },
      "expected_output": "error=invalid_token\nreason=expired_issue_at\n"
    },
    {
      "input": {
        "op": "verify",
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmb28iOiJiYXIiLCJpYXQiOjQxMDI0NDQ4MDB9.tE3_DpKlyEaAr226sqTkMerhXsH6a8JM4wvAXmo9ZXY",
        "key": {
          "kind": "secret",
          "secret": "secret passphrase"
        }
      },
      "expected_output": "alg=HS256\npayload={\"foo\":\"bar\",\"iat\":4102444800}\n"
    }
  ]
}
```

---

### Feature 4: Payload type rules

**As a developer**, I want clear, predictable rules about what may be used as a token payload, so invalid payloads fail fast with a meaningful error.

**Expected Behavior / Usage:**

A payload may be either a string or a key/value map; both are accepted and produce a valid token (a string payload is carried verbatim as the base64url body, a map payload is JSON-encoded first). Any other scalar type, such as a bare number, is rejected before signing with `error=invalid_payload_type`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_payload_types.json`

```json
{
  "description": "Accept string and map payloads when issuing a token but reject a numeric payload as an invalid payload type.",
  "cases": [
    {
      "input": {
        "op": "sign",
        "algorithm": "HS256",
        "key": {
          "kind": "secret",
          "secret": "secret passphrase"
        },
        "payload": "asdf123",
        "no_iat": true
      },
      "expected_output": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.YXNkZjEyMw.e8SvhajhZIR_HFN9r-DncvNJ4ZlWqvdcRf_RMNvAdMU\n"
    },
    {
      "input": {
        "op": "sign",
        "algorithm": "HS256",
        "key": {
          "kind": "secret",
          "secret": "secret passphrase"
        },
        "payload": {
          "foo": "bar"
        },
        "no_iat": true
      },
      "expected_output": "[a specific token output for a secret payload]\n"
    },
    {
      "input": {
        "op": "sign",
        "algorithm": "HS256",
        "key": {
          "kind": "secret",
          "secret": "secret passphrase"
        },
        "payload": 1234,
        "no_iat": true
      },
      "expected_output": "error=invalid_payload_type\n"
    }
  ]
}
```

---

### Feature 5: JWK key conversion

**As a developer**, I want to export a signing key to the standard JWK JSON form and parse a JWK back into a usable key, so keys can be published, transported and re-loaded across services.

**Expected Behavior / Usage:**

The toolkit converts every supported key category to a JWK JSON object and parses a JWK object back into the corresponding key. Shared-secret keys map to `kty: oct`, RSA keys to `kty: RSA`, elliptic-curve keys to `kty: EC` (with the NIST curve name), and Edwards-curve keys to `kty: OKP`. Private keys include their private parameters in the JWK; public keys include only the public ones.

*5.1 Export to JWK — serialize a key to its JWK JSON object*

Each key category emits its standard JWK fields as a single canonical-json line (object keys sorted). Shared-secret and RSA exports omit the algorithm hint unless one is explicitly requested (`with_alg`); elliptic-curve and Edwards-curve exports always include the algorithm implied by the curve.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_export_jwk.json`

```json
{
  "description": "Export a key to its JWK JSON object. Secret and RSA keys omit the algorithm hint unless requested; elliptic-curve and Edwards-curve keys always include their algorithm.",
  "cases": [
    {
      "input": {
        "op": "to_jwk",
        "key": {
          "kind": "secret",
          "secret": "secret passphrase"
        }
      },
      "expected_output": "{\"k\":\"c2VjcmV0IHBhc3NwaHJhc2U\",\"kty\":\"oct\",\"use\":\"sig\"}\n"
    },
    {
      "input": {
        "op": "to_jwk",
        "key": {
          "kind": "secret",
          "secret": "secret passphrase"
        },
        "with_alg": "HS256"
      },
      "expected_output": "{\"alg\":\"HS256\",\"k\":\"c2VjcmV0IHBhc3NwaHJhc2U\",\"kty\":\"oct\",\"use\":\"sig\"}\n"
    },
    {
      "input": {
        "op": "to_jwk",
        "key": {
          "kind": "ec_private",
          "pem": "-----BEGIN PRIVATE KEY-----\nMIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgevZzL1gdAFr88hb2\nOF/2NxApJCzGCEDdfSp6VQO30hyhRANCAAQRWz+jn65BtOMvdyHKcvjBeBSDZH2r\n1RTwjmYSi9R/zpBnuQ4EiMnCqfMPWiZqB4QdbAd0E7oH50VpuZ1P087G\n-----END PRIVATE KEY-----"
        }
      },
      "expected_output": "{\"alg\":\"ES256\",\"crv\":\"P-256\",\"d\":\"evZzL1gdAFr88hb2OF_2NxApJCzGCEDdfSp6VQO30hw\",\"kty\":\"EC\",\"use\":\"sig\",\"x\":\"EVs_o5-uQbTjL3chynL4wXgUg2R9q9UU8I5mEovUf84\",\"y\":\"kGe5DgSIycKp8w9aJmoHhB1sB3QTugfnRWm5nU_TzsY\"}\n"
    }
  ]
}
```

*5.2 Import from JWK — parse a JWK JSON object back into a key*

A JWK object is parsed into the matching key, and the adapter reports `kind=<category>` (one of the seven key categories) and `kty=<key-type>` echoed from the JWK. The presence of private parameters distinguishes a private key from a public key of the same family.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_import_jwk.json`

```json
{
  "description": "Import a JWK JSON object and report the resolved key category and key type for secret, RSA, elliptic-curve and Edwards-curve public and private keys.",
  "cases": [
    {
      "input": {
        "op": "from_jwk",
        "jwk": {
          "k": "c2VjcmV0IHBhc3NwaHJhc2U",
          "kty": "oct",
          "use": "sig"
        }
      },
      "expected_output": "kind=secret\nkty=oct\n"
    },
    {
      "input": {
        "op": "from_jwk",
        "jwk": {
          "d": "pOaNpLq2QrwGU9cKVNDa-nP83q7EN5LfmZempqyqyRWVoCJ2CD-xaqmNcNtev3ei0gwuVawz5fQKowOBJcp6MtLaPHgYOMjVlNeD77QAwnywnvilbNUM5-YIRD_vBezf5xudeEquI7xnTfqr3ZBzX43ztIjfyeQZrQAEf0I3zceZCq3h8HtR0fO4hF7-Z7Y8aEirlkHOPqHcGmg8bMQ_7HeX1iYry3_Vw3Smoj51DBh2B8aNpyQu7_aofzQwIXsjJBqx5lQ4nIqsIu1IP8iLG_-HMMRQ984KMUOBOnN_dzC1rz6gTjAcKjWIjX_hOU-TCZfHipJe2bDhpA_PsgNC8Q",
          "dp": "zV7W3COOlDDcQd935DdtKBFRAPRPAlspQUnzMi5eSHMD_ISLDY5IiQHbIH83D4bvXq0X7qQoSBSNP7Dvv3HYuqMhf0DaegrlBuJllFVVq9qPVRnKxt1Il2HgxOBvbhOT-9in1BzA-YJ99UzC85O0Qz06A-CmtHEy4aZ2kj5hHjE",
          "dq": "mNS4-A8Fkss8Js1RieK2LniBxMgmYml3pfVLKGnzmng7H2-cwPLhPIzIuwytXywh2bzbsYEfYx3EoEVgMEpPhoarQnYPukrJO4gwE2o5Te6T5mJSZGlQJQj9q4ZB2Dfzet6INsK0oG8XVGXSpQvQh3RUYekCZQkBBFcpqWpbIEs",
          "e": "AQAB",
          "kty": "RSA",
          "n": "u1SU1LfVLPHCozMxH2Mo4lgOEePzNm0tRgeLezV6ffAt0gunVTLw7onLRnrq0_IzW7yWR7QkrmBL7jTKEn5u-qKhbwKfBstIs-bMY2Zkp18gnTxKLxoS2tFczGkPLPgizskuemMghRniWaoLcyehkd3qqGElvW_VDL5AaWTg0nLVkjRo9z-40RQzuVaE8AkAFmxZzow3x-VJYKdjykkJ0iT9wCS0DRTXu269V264Vf_3jvredZiKRkgwlL9xNAwxXFg0x_XFw005UWVRIkdgcKWTjpBP2dPwVZ4WWC-9aGVd-Gyn1o0CLelf4rEjGoXbAAEgAqeGUxrcIlbjXfbcmw",
          "p": "8KNThCO2gsC2I9PQDM_8Cw0O983WCDY-oi-7JPiNAJwv5DYBqEZB1QYdj06YD16XlC_HAZMsMku1na2TN0driwenQQWzoev3g2S7gRDoS_FCJSI3jJ-kjgtaA7Qmzlgk1TxODN-G1H91HW7t0l7VnL27IWyYo2qRRK3jzxqUiPU",
          "q": "x0oQs2reBQGMVZnApD1jeq7n4MvNLcPvt8b_eU9iUv6Y4Mj0Suo_AU8lYZXm8ubbqAlwz2VSVunD2tOplHyMUrtCtObAfVDUAhCndKaA9gApgfb3xw1IKbuQ1u4IF1FJl3VtumfQn__LiH1B3rXhcdyo3_vIttEk48RakUKClU8",
          "qi": "JzNw0H9xSaEp12jIa1QSKL4nOZdMRZBB7JAIxU3rzvOhbM9QtmknkSkqhhaDkNLZicwRLNUeiqpxyJ4nA00KyoQK4C11-L9wnXY300SZBVg2xPwpLymTTq3H9Z4Whgj7KUSY9ilJI9RYZfQp3HZ_0bGBDjW8EEoyHzD5L8RfvB0",
          "use": "sig"
        }
      },
      "expected_output": "kind=rsa_private\nkty=RSA\n"
    },
    {
      "input": {
        "op": "from_jwk",
        "jwk": {
          "alg": "ES256",
          "crv": "P-256",
          "d": "evZzL1gdAFr88hb2OF_2NxApJCzGCEDdfSp6VQO30hw",
          "kty": "EC",
          "use": "sig",
          "x": "EVs_o5-uQbTjL3chynL4wXgUg2R9q9UU8I5mEovUf84",
          "y": "kGe5DgSIycKp8w9aJmoHhB1sB3QTugfnRWm5nU_TzsY"
        }
      },
      "expected_output": "kind=ec_private\nkty=EC\n"
    },
    {
      "input": {
        "op": "from_jwk",
        "jwk": {
          "alg": "EdDSA",
          "crv": "Ed25519",
          "d": "JcKMEe-MCuNeq5QjmOjfHlIcjih9kDZrPAnf0gL9By0",
          "kty": "OKP",
          "use": "sig",
          "x": "Ei7MNW0Q9T83UA3Rw-8DbspMgqeuxCqa2wXaWS-tHqY"
        }
      },
      "expected_output": "kind=ed_private\nkty=OKP\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-module codebase implementing signing, verification, temporal claim enforcement, payload rules and JWK conversion across all listed algorithms, with the cryptographic core decoupled from any I/O.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON command from stdin, invokes the core, and prints the result (or a normalized error) to stdout exactly matching the per-leaf-feature contracts above. It must be logically separate from the core domain.

3. **Automated test harness:** The cases embedded above live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory (default `test_cases`). For each case it writes one file `rcb_tests/stdout/<cases-dir>/{stem}@{index:03d}.txt` (e.g. the first case of `feature1_1_sign_hmac.json` under `--cases-dir public_test_cases` becomes `rcb_tests/stdout/public_test_cases/feature1_1_sign_hmac@000.txt`). Output is namespaced by `<cases-dir>` so different directories never overwrite each other, and each `.txt` holds **only** the raw stdout of the program under test so it can be compared directly against `expected_output`.



---
**Implementation notes:**
- use the same behavior as C025 but omit the alg field
- export the EC key with alg ES256 by default
