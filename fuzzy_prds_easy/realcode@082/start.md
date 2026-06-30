## Product Requirement Document

# Transparent Attribute Encryption Mixin — Declarative Encrypt-on-Write / Decrypt-on-Read Attributes

## Project Goal

Build a reusable mixin that lets developers declare ordinary-looking model attributes that are **encrypted automatically when written and decrypted automatically when read**, so that sensitive fields (emails, passwords, credentials, identifiers) are never stored in plaintext. A single declarative statement registers an attribute, generates the backing storage accessors, and wires up the cipher, encoding, serialization, key resolution, and per-record randomization — all without the developer writing any cipher code at the call site.

---

## Background & Problem

Without this mixin, developers who want field-level encryption must hand-write encrypt/decrypt calls every time a sensitive attribute is read or written, manually manage initialization vectors and salts per record, base64-encode ciphertext for safe text storage, serialize non-string values before encryption, and thread the encryption key through every access path. This boilerplate is repetitive, easy to get wrong (reused IVs, leaked plaintext, forgotten encoding), and scatters cryptographic concerns across the whole model layer.

With this mixin, a developer declares an attribute once with a key and a handful of options. Reading and writing the attribute then behaves exactly like a normal accessor, while the library transparently encrypts on assignment, decrypts on read, generates a fresh initialization vector (and optionally a salt) for every encryption, and stores the result in a conventionally named backing attribute. The same declaration also exposes class-level encrypt/decrypt helpers and a boolean presence predicate, supports custom cipher backends, conditional gating, value serialization, and inheritance of declarations and defaults across subclasses.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This is a multi-responsibility library (attribute registration/metadata, option resolution, key resolution, cipher delegation, encoding, serialization, IV/salt generation, presence predicates, inheritance). It MUST NOT be a single "god file": separate the declaration/registration surface, the per-instance evaluation logic, and the encode/serialize helpers into cohesive units. The execution adapter that renders the stdout contract MUST be a separate program from the core mixin.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases in "Core Features" are a **black-box contract for the execution adapter**, not the internal data model. The core mixin must expose idiomatic declarative methods and accessors; it must know nothing about JSON, stdin, or stdout. The adapter alone translates JSON commands into idiomatic calls (declare attributes, assign values, read values, call class-level helpers) and formats results into the line-oriented transcript.

3. **Adherence to SOLID Design Principles (scaled to size):**
   - **SRP:** Keep registration, option evaluation, key resolution, cipher delegation, encoding, and IV/salt generation in distinct units.
   - **OCP:** The cipher backend, the serializer, and the encoding must be replaceable via options without modifying the core engine.
   - **LSP:** A subclass that inherits declarations must be fully substitutable and must observe all inherited behavior.
   - **ISP:** Keep the per-attribute option surface small and cohesive; do not force unrelated options on every attribute.
   - **DIP:** The engine depends on abstract "encryptor", "serializer", and "key provider" roles, not on a concrete implementation.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** Declaring an encrypted attribute and using it must read like declaring and using a normal attribute.
   - **Resilience:** Absent and empty values are handled gracefully (passthrough by default, opt-in encryption otherwise). Errors are normalized to neutral, language-agnostic categories at the adapter boundary; no host-language exception type names, object renderings, or runtime message fragments may appear in stdout.

---

## Execution Adapter Contract (how cases are run)

The execution adapter reads one JSON object from stdin describing a `model` to build and a list of `ops` to perform, then prints a deterministic, line-oriented transcript to stdout. **All transcript lines are sorted**, so output is order-independent.

A `model` object has:
- `attributes`: a list of declarations. Each has `names` (one or more attribute names declared together), an optional `via` (`"alias"` selects the alternate declaration entry point; default is the primary one), and `options` (per-attribute options).
- `global_options` (optional): default options applied to every attribute of this model. The key `{"$proc_key": true}` installs a callable that returns the fixed test key; `"mode"` selects the randomization mode.
- `instance_methods` (optional): named instance methods returning fixed values (e.g. a key accessor or a boolean guard flag). The value `{"$key": true}` resolves to the fixed test key.
- `subclass` (optional): a child model declaring its own additional `attributes`.

Option value encodings used in cases: `{"$key": true}` → the fixed symmetric key; `{"$proc_key": true}` → a callable returning the fixed key; `{"$sym": "name"}` → a reference to an instance method named `name`; `{"$silly": true}` → a sample custom cipher object whose transform is fully specified in Feature 7.

To keep ciphertext reproducible where a case inspects it, the adapter pins the initialization vector (and salt when relevant); where the case only asserts structural facts or uniqueness, the real randomized generation is used. Encryption key material and raw cipher bytes are never printed; only domain-level signals (recovered values, storage names, presence/uniqueness/equality flags, the algorithm name, encoding flags) appear in stdout. Binary bytes, when they must be shown, are rendered as a neutral `b64:`-prefixed token; absent is `nil`; empty string is `<empty>`; the model class object is `<model-class>`.

---

## Core Features

### Feature 1: Attribute Registration & Predicate

**As a developer**, I want declaring an encrypted attribute to register it in a queryable catalogue, so I can introspect which attributes are encrypted and rely on an alternate declaration keyword behaving identically.

**Expected Behavior / Usage:**

Declaring one or more attributes adds each to the model's catalogue of encrypted attributes; names that were never declared as encrypted (ordinary accessors) are absent from the catalogue. The catalogue can be queried two ways for the same fact: by direct membership of an attribute name, and by a boolean predicate that takes the attribute name. An alternate declaration keyword registers its attribute exactly like the primary keyword. Each transcript line is `encrypted_attributes_include[<name>]=<bool>` or `attr_encrypted[<name>]=<bool>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_registration.json`

```json
{
  "description": "Declaring encrypted attributes registers them in the model's catalogue of encrypted attributes, while ordinary non-encrypted accessor names stay out of it. The catalogue can be queried both by direct membership and by a boolean predicate that accepts the attribute name. An alternate declaration keyword behaves identically to the primary one and registers its attribute the same way. Each transcript line reports one membership or predicate result keyed by the queried attribute name.",
  "cases": [
    {
      "input": {
        "model": {
          "attributes": [
            { "names": ["email"], "options": { "key": { "$key": true } } },
            { "names": ["aliased"], "via": "alias", "options": { "key": { "$key": true } } }
          ]
        },
        "ops": [
          { "kind": "encrypted_attributes_include", "attr": "email" },
          { "kind": "encrypted_attributes_include", "attr": "salt" },
          { "kind": "attr_encrypted", "attr": "email" },
          { "kind": "attr_encrypted", "attr": "salt" }
        ]
      },
      "expected_output": "attr_encrypted[email]=true\nattr_encrypted[salt]=false\nencrypted_attributes_include[email]=true\nencrypted_attributes_include[salt]=false\n"
    },
    {
      "input": {
        "model": {
          "attributes": [
            { "names": ["email"], "options": { "key": { "$key": true } } },
            { "names": ["aliased"], "via": "alias", "options": { "key": { "$key": true } } }
          ]
        },
        "ops": [ { "kind": "encrypted_attributes_include", "attr": "aliased" } ]
      },
      "expected_output": "encrypted_attributes_include[aliased]=true\n"
    }
  ]
}
```

---

### Feature 2: Backing Storage-Attribute Naming

**As a developer**, I want each declared attribute to generate a companion accessor for the storage attribute that physically holds the ciphertext, with controllable naming, so I can map encrypted fields onto persistence columns predictably.

**Expected Behavior / Usage:**

Declaring an encrypted attribute generates accessors for a backing storage attribute. By default the storage name is the attribute name with a conventional fixed prefix. The name can be overridden by a custom prefix/suffix pair, or by supplying an explicit storage-attribute name. Each transcript line is `respond_to[<accessor>]=<bool>` (does a fresh instance expose the named accessor) or `storage_attr[<attr>]=<resolved storage name>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_storage_naming.json`

```json
{
  "description": "Declaring an encrypted attribute also generates a companion accessor for the backing storage attribute that physically holds the encrypted bytes. By default the storage name is the attribute name with a conventional fixed prefix. A caller may override that with a custom prefix and suffix pair, or by supplying an explicit storage-attribute name outright. Each transcript line reports whether a freshly built instance responds to a named generated accessor, or reports the resolved storage name for an attribute.",
  "cases": [
    {
      "input": {
        "model": {
          "attributes": [
            { "names": ["email"], "options": { "key": { "$key": true } } },
            { "names": ["password"], "options": { "prefix": "crypted_", "suffix": "_test" } },
            { "names": ["ssn"], "options": { "key": { "$key": true }, "attribute": "ssn_encrypted" } }
          ]
        },
        "ops": [
          { "kind": "respond_to", "method": "encrypted_email" },
          { "kind": "respond_to", "method": "crypted_password_test" },
          { "kind": "respond_to", "method": "ssn_encrypted" }
        ]
      },
      "expected_output": "respond_to[crypted_password_test]=true\nrespond_to[encrypted_email]=true\nrespond_to[ssn_encrypted]=true\n"
    }
  ]
}
```

---

### Feature 3: Class-Level Encrypt / Decrypt & String Coercion

**As a developer**, I want direct class-level encrypt and decrypt helpers for any declared attribute, so I can transform values outside an instance and rely on predictable passthrough and coercion rules.

**Expected Behavior / Usage:**

The class exposes encrypt and decrypt helpers for a declared attribute. Encrypting an absent value returns the absent value; encrypting an empty value returns the empty value; decryption mirrors this passthrough for absent and empty inputs. Encrypting a present value produces an encoded representation that differs from the plaintext, and decrypting it recovers the original exactly (round-trip). Non-string inputs are coerced to their string form before encryption, so two inputs with the same string form encrypt identically under a fixed initialization vector. Transcript lines include `class_encrypt[<attr>]=<nil|b64:...|...>`, `class_roundtrip[<attr>]=<recovered>`, and `class_roundtrip_differs[<attr>]=<bool>`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_encrypt_decrypt.json`

```json
{
  "description": "The class exposes direct encryption and decryption helpers for any declared attribute. Encrypting an absent value yields the absent value unchanged, and encrypting an empty value yields the empty value unchanged; decryption mirrors this passthrough for absent and empty inputs. Encrypting a present value produces an encoded representation that differs from the plaintext, and decrypting that representation recovers the original plaintext exactly. Non-string inputs are coerced to their string form before encryption, so two inputs with the same string form produce identical ciphertext under a fixed initialization vector. Each transcript line reports an encrypt/decrypt outcome, a round-trip recovery, a ciphertext-differs flag, or a coercion-equality flag.",
  "cases": [
    {
      "input": {
        "model": {
          "attributes": [ { "names": ["email"], "options": { "key": { "$key": true } } } ],
          "global_options": { "key": { "$proc_key": true }, "mode": "per_attribute_iv_and_salt" }
        },
        "ops": [ { "kind": "class_encrypt", "attr": "email", "value": null } ]
      },
      "expected_output": "class_encrypt[email]=nil\n"
    },
    {
      "input": {
        "model": {
          "attributes": [ { "names": ["email"], "options": { "key": { "$key": true } } } ],
          "global_options": { "key": { "$proc_key": true }, "mode": "per_attribute_iv_and_salt" }
        },
        "ops": [ { "kind": "class_roundtrip", "attr": "email", "value": "test@example.com", "with_salt": true, "report_differs": true } ]
      },
      "expected_output": "class_roundtrip[email]=test@example.com\nclass_roundtrip_differs[email]=true\n"
    }
  ]
}
```

---

### Feature 4: Transparent Assignment, Read & Presence Predicate

**As a developer**, I want assigning and reading an encrypted attribute to behave like a normal accessor while encryption happens behind the scenes, so my model code stays clean and a boolean predicate tells me whether a value is present.

**Expected Behavior / Usage:**

Assigning plaintext writes a non-plaintext representation into the backing storage; reading the attribute recovers the original plaintext. Because each encryption uses a fresh initialization vector, two independent instances assigned the same plaintext store different ciphertext. A boolean query accessor reports whether the attribute currently holds a non-empty value: false before any assignment, false after assigning an empty value, true after assigning a non-empty value. Transcript lines include `assign_read[<attr>]=<recovered>`, `stored_present[<attr>]=<bool>`, `stored_equals_plain[<attr>]=<bool>`, and `predicate[<attr>][<NN>]=<bool>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_transparent_access.json`

```json
{
  "description": "Assigning plaintext to an encrypted attribute transparently writes a non-plaintext representation into its backing storage, and reading the attribute back transparently recovers the original plaintext. Because each encryption uses a fresh initialization vector, two independent instances assigned the same plaintext store different ciphertext. A boolean query accessor reports whether the attribute currently holds a non-empty value: it is false before assignment and after assigning an empty value, and true after assigning a non-empty value. Each transcript line reports a recovered value, a storage-presence fact, a stored-versus-plaintext comparison, a per-instance uniqueness flag, or a query-accessor result.",
  "cases": [
    {
      "input": {
        "model": {
          "attributes": [ { "names": ["email"], "options": { "key": { "$key": true } } } ],
          "global_options": { "key": { "$proc_key": true }, "mode": "per_attribute_iv_and_salt" }
        },
        "ops": [ { "kind": "assign_read", "attr": "email", "value": "test@example.com", "report_stored": true, "report_stored_equals_plain": true } ]
      },
      "expected_output": "assign_read[email]=test@example.com\nstored_equals_plain[email]=false\nstored_present[email]=true\n"
    },
    {
      "input": {
        "model": {
          "attributes": [ { "names": ["email"], "options": { "key": { "$key": true } } } ],
          "global_options": { "key": { "$proc_key": true }, "mode": "per_attribute_iv_and_salt" }
        },
        "ops": [ { "kind": "predicate_steps", "attr": "email", "steps": [ { "assign": false }, { "assign": true, "value": "" }, { "assign": true, "value": "test@example.com" } ] } ]
      },
      "expected_output": "predicate[email][00]=false\npredicate[email][01]=false\npredicate[email][02]=true\n"
    }
  ]
}
```

---

### Feature 5: Optional Encoding of the Encrypted Representation

**As a developer**, I want to optionally encode the encrypted bytes for safe text storage, so I can persist ciphertext in text columns and still round-trip it back.

**Expected Behavior / Usage:**

An attribute can be configured to additionally encode its encrypted representation (base64 by default, or with an explicit encoding directive). With encoding enabled, the stored representation equals the packed (base64) form of the corresponding un-encoded representation produced under the same initialization vector and salt. Decoding the stored value and then decrypting it round-trips back to the original plaintext, and equals decrypting the unpacked un-encoded representation. Transcript lines are `encode_matches_packed=<bool>`, `decode_roundtrip=<recovered>`, and `decode_matches_plain=<bool>`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_encoding.json`

```json
{
  "description": "An attribute can be configured to additionally encode its encrypted representation so the stored value is safe for text storage, optionally with an explicit encoding directive. With encoding enabled, the stored representation equals the packed (base64) form of the corresponding un-encoded representation produced under the same initialization vector and salt. Decoding the stored value and then decrypting it round-trips back to the original plaintext, and equals the result of decrypting the unpacked un-encoded representation. Each transcript line reports an encode-equivalence flag, a decode round-trip value, or a decode-matches-plain flag.",
  "cases": [
    {
      "input": {
        "model": {
          "attributes": [
            { "names": ["without_encoding"], "options": { "key": { "$key": true } } },
            { "names": ["with_encoding"], "options": { "key": { "$key": true }, "encode": true } },
            { "names": ["with_custom_encoding"], "options": { "key": { "$key": true }, "encode": "m" } }
          ],
          "global_options": { "key": { "$proc_key": true }, "mode": "per_attribute_iv_and_salt" }
        },
        "ops": [ { "kind": "encode_matches_packed", "encoded_attr": "with_encoding", "plain_attr": "without_encoding", "value": "test", "with_salt": true } ]
      },
      "expected_output": "encode_matches_packed=true\n"
    },
    {
      "input": {
        "model": {
          "attributes": [
            { "names": ["without_encoding"], "options": { "key": { "$key": true } } },
            { "names": ["with_encoding"], "options": { "key": { "$key": true }, "encode": true } },
            { "names": ["with_custom_encoding"], "options": { "key": { "$key": true }, "encode": "m" } }
          ],
          "global_options": { "key": { "$proc_key": true }, "mode": "per_attribute_iv_and_salt" }
        },
        "ops": [ { "kind": "decode_roundtrip", "encoded_attr": "with_encoding", "plain_attr": "without_encoding", "value": "test", "with_salt": true } ]
      },
      "expected_output": "decode_matches_plain=true\ndecode_roundtrip=test\n"
    }
  ]
}
```

---

### Feature 6: Value Serialization for Non-String Attributes

**As a developer**, I want to encrypt structured values (lists, maps) by serializing them first, so I can store non-string data and recover it intact.

**Expected Behavior / Usage:**

An attribute can be configured to serialize its value before encryption. Assigning a structured value populates the backing storage with encrypted bytes; reading the attribute recovers an equal structured value (not its string form). Transcript lines are `marshal_read[<attr>]=<structured value>` and `stored_present[<attr>]=<bool>`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_marshaling.json`

```json
{
  "description": "An attribute can be configured to serialize its value before encryption, allowing non-string objects such as lists or maps to be stored. Assigning a structured value populates the backing storage with encrypted bytes and reading the attribute back recovers an equal structured value (not its string form). Each transcript line reports the recovered structured value and a storage-presence fact.",
  "cases": [
    {
      "input": {
        "model": {
          "attributes": [ { "names": ["with_marshaling"], "options": { "key": { "$key": true }, "marshal": true } } ],
          "global_options": { "key": { "$proc_key": true }, "mode": "per_attribute_iv_and_salt" }
        },
        "ops": [ { "kind": "marshal_assign_read", "attr": "with_marshaling", "value": [1, 2, 3] } ]
      },
      "expected_output": "marshal_read[with_marshaling]=[1, 2, 3]\nstored_present[with_marshaling]=true\n"
    }
  ]
}
```

---

### Feature 7: Pluggable Custom Cipher Backend

**As a developer**, I want to swap in my own cipher object with named encrypt/decrypt methods and extra arguments, so I can integrate an alternate or domain-specific transform.

**Expected Behavior / Usage:**

An attribute can delegate to a caller-supplied cipher object, naming the encrypt and decrypt methods to call and passing through extra arguments. The custom transform is applied on encryption and inverted on decryption, with no built-in key required. The sample transform: encryption concatenates the value with the extra argument and reverses the result; decryption reverses it back and strips the trailing argument. With value `"testing"` and extra argument `"test"`, encryption yields `tsetgnitset` and decryption recovers `testing`. Transcript lines are `custom_encrypt[<attr>]=<transformed>` and `custom_roundtrip[<attr>]=<recovered>`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_custom_encryptor.json`

```json
{
  "description": "An attribute can delegate to a caller-supplied encryptor object, naming the encrypt and decrypt methods to call and passing through extra arguments to them. The custom transform is applied on encryption and inverted on decryption, with no built-in key required. For the sample transform, encrypting concatenates the value with the extra argument and reverses the result; decrypting reverses it back and strips the argument. Each transcript line reports the transformed representation and its round-trip recovery.",
  "cases": [
    {
      "input": {
        "model": {
          "attributes": [
            { "names": ["credit_card"], "options": { "encryptor": { "$silly": true }, "encrypt_method": "silly_encrypt", "decrypt_method": "silly_decrypt", "some_arg": "test" } }
          ]
        },
        "ops": [ { "kind": "custom_encrypt", "attr": "credit_card", "value": "testing", "roundtrip": true } ]
      },
      "expected_output": "custom_encrypt[credit_card]=tsetgnitset\ncustom_roundtrip[credit_card]=testing\n"
    }
  ]
}
```

---

### Feature 8: Indirect Key Resolution

**As a developer**, I want to supply the encryption key indirectly (via an instance method reference or a callable), so the key can be derived from instance state instead of hard-coded.

**Expected Behavior / Usage:**

The key for an attribute can be supplied as a reference naming an instance method that returns the key, or as a callable evaluated in the instance's context. In every form the resolved key is used so that assigning a value stores a non-plaintext representation and reading it back recovers the original plaintext. Transcript lines include `assign_read[<attr>]=<recovered>`, `stored_present[<attr>]=<bool>`, and `stored_equals_plain[<attr>]=<bool>`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_key_resolution.json`

```json
{
  "description": "The encryption key for an attribute can be supplied indirectly rather than as a literal: as a reference naming an instance method that returns the key, or as a callable evaluated in the instance's context. In every form the resolved key is used so that assigning a value stores a non-plaintext representation and reading it back recovers the original plaintext. Each transcript line reports a recovered value, a storage-presence fact, or a stored-versus-plaintext comparison.",
  "cases": [
    {
      "input": {
        "model": {
          "attributes": [
            { "names": ["ssn"], "options": { "key": { "$sym": "secret_key" }, "attribute": "ssn_encrypted" } },
            { "names": ["password"], "options": { "key": { "$proc_key": true }, "prefix": "crypted_", "suffix": "_test" } }
          ],
          "global_options": { "mode": "per_attribute_iv_and_salt" },
          "instance_methods": { "secret_key": { "$key": true } }
        },
        "ops": [ { "kind": "assign_read", "attr": "ssn", "value": "testing", "report_stored": true, "report_stored_equals_plain": true } ]
      },
      "expected_output": "assign_read[ssn]=testing\nstored_equals_plain[ssn]=false\nstored_present[ssn]=true\n"
    }
  ]
}
```

---

### Feature 9: Dynamic Option Evaluation

**As a developer**, I want option values to be resolvable against an instance at use time, so an option can be a method reference, a callable, or a plain value and behave consistently.

**Expected Behavior / Usage:**

An option value is resolved dynamically: a name referring to an instance method is invoked and replaced by its return value; any callable is called with the instance and replaced by the result; a plain value is returned unchanged. Each transcript line is `evaluate_option=<result>`; when the result is the model class object itself it is reported with the neutral placeholder `<model-class>` so no host-language object rendering leaks.

**Test Cases:** `rcb_tests/public_test_cases/feature9_option_evaluation.json`

```json
{
  "description": "Option values can be resolved dynamically against an instance at the moment they are needed. A name that refers to an instance method is invoked and replaced by its return value; any callable is called with the instance as its argument and replaced by the result; a plain value is returned unchanged. Each transcript line reports the resolved option result; when the result is the model class object itself it is reported with a neutral placeholder so no host-language object rendering leaks.",
  "cases": [
    {
      "input": { "model": { "attributes": [] }, "ops": [ { "kind": "evaluate_option", "value": { "$proc_object_class": true } } ] },
      "expected_output": "evaluate_option=<model-class>\n"
    },
    {
      "input": { "model": { "attributes": [] }, "ops": [ { "kind": "evaluate_option", "value": "SomeString" } ] },
      "expected_output": "evaluate_option=SomeString\n"
    }
  ]
}
```

---

### Feature 10: Conditional Encryption Guards

**As a developer**, I want to gate whether an attribute is encrypted with positive/negative conditions, so some values can be stored verbatim while others are encrypted based on configuration or instance state.

**Expected Behavior / Usage:**

A positive condition that holds true (or a negative condition that holds false) causes the value to be encrypted; a positive condition that is false (or a negative condition that is true) causes the plaintext to be stored verbatim. The gating condition may itself be resolved dynamically from instance state at assignment time. Each transcript line reports `assign_read[<attr>]=<recovered>` and `stored_equals_plain[<attr>]=<bool>`, where true means the value was stored verbatim (not encrypted) and false means it was encrypted.

**Test Cases:** `rcb_tests/public_test_cases/feature10_conditional_guards.json`

```json
{
  "description": "Encryption can be gated by conditional options. A positive condition that holds true (or a negative condition that holds false) causes the value to be encrypted, while a positive condition that is false (or a negative condition that is true) causes the plaintext to be stored verbatim. The gating condition may itself be resolved dynamically from instance state at assignment time. Each transcript line reports the recovered value and whether the stored representation equals the assigned plaintext (true means it was stored verbatim, false means it was encrypted).",
  "cases": [
    {
      "input": {
        "model": {
          "attributes": [
            { "names": ["with_true_if"], "options": { "key": { "$key": true }, "if": true, "mode": "per_attribute_iv_and_salt" } },
            { "names": ["with_false_if"], "options": { "key": { "$key": true }, "if": false, "mode": "per_attribute_iv_and_salt" } },
            { "names": ["with_true_unless"], "options": { "key": { "$key": true }, "unless": true, "mode": "per_attribute_iv_and_salt" } },
            { "names": ["with_false_unless"], "options": { "key": { "$key": true }, "unless": false, "mode": "per_attribute_iv_and_salt" } },
            { "names": ["with_if_changed"], "options": { "key": { "$key": true }, "if": { "$sym": "should_encrypt" } } }
          ],
          "global_options": { "key": { "$proc_key": true } },
          "instance_methods": { "should_encrypt": false }
        },
        "ops": [ { "kind": "assign_read", "attr": "with_true_if", "value": "testing", "report_stored_equals_plain": true } ]
      },
      "expected_output": "assign_read[with_true_if]=testing\nstored_equals_plain[with_true_if]=false\n"
    },
    {
      "input": {
        "model": {
          "attributes": [
            { "names": ["with_true_if"], "options": { "key": { "$key": true }, "if": true, "mode": "per_attribute_iv_and_salt" } },
            { "names": ["with_false_if"], "options": { "key": { "$key": true }, "if": false, "mode": "per_attribute_iv_and_salt" } },
            { "names": ["with_true_unless"], "options": { "key": { "$key": true }, "unless": true, "mode": "per_attribute_iv_and_salt" } },
            { "names": ["with_false_unless"], "options": { "key": { "$key": true }, "unless": false, "mode": "per_attribute_iv_and_salt" } },
            { "names": ["with_if_changed"], "options": { "key": { "$key": true }, "if": { "$sym": "should_encrypt" } } }
          ],
          "global_options": { "key": { "$proc_key": true } },
          "instance_methods": { "should_encrypt": false }
        },
        "ops": [ { "kind": "assign_read", "attr": "with_false_if", "value": "testing", "report_stored_equals_plain": true } ]
      },
      "expected_output": "assign_read[with_false_if]=testing\nstored_equals_plain[with_false_if]=true\n"
    }
  ]
}
```

---

### Feature 11: Opt-In Encryption of Empty / Absent Values

**As a developer**, I want to optionally encrypt empty and absent values, so fields that must always be encrypted are never silently passed through.

**Expected Behavior / Usage:**

By default an empty or absent value is left unencrypted. An attribute can opt in to encrypting empty and absent values. With the opt-in enabled, assigning an empty value and assigning an absent value both populate the backing storage with encrypted bytes, and reading recovers the originally assigned empty or absent value. Transcript lines are `allow_empty_read[<attr>]=<recovered>` (empty rendered as `<empty>`, absent as `nil`) and `stored_present[<attr>]=<bool>`.

**Test Cases:** `rcb_tests/public_test_cases/feature11_allow_empty.json`

```json
{
  "description": "By default an empty or absent value is left unencrypted, but an attribute can opt in to encrypting empty and absent values. With that option enabled, assigning an empty value and assigning an absent value both populate the backing storage with encrypted bytes, and reading the attribute back recovers the originally assigned empty or absent value. Each transcript line reports a storage-presence fact or a recovered value (empty rendered as a neutral placeholder, absent rendered as a neutral nil token).",
  "cases": [
    {
      "input": {
        "model": {
          "attributes": [ { "names": ["with_allow_empty_value"], "options": { "key": { "$key": true }, "allow_empty_value": true, "marshal": true } } ],
          "global_options": { "key": { "$proc_key": true }, "mode": "per_attribute_iv_and_salt" }
        },
        "ops": [
          { "kind": "allow_empty", "attr": "with_allow_empty_value", "value": "" },
          { "kind": "allow_empty", "attr": "with_allow_empty_value", "value": null }
        ]
      },
      "expected_output": "allow_empty_read[with_allow_empty_value]=<empty>\nallow_empty_read[with_allow_empty_value]=nil\nstored_present[with_allow_empty_value]=true\nstored_present[with_allow_empty_value]=true\n"
    }
  ]
}
```

---

### Feature 12: Inheritance of Declarations & Defaults

**As a developer**, I want a subclass to inherit the parent's encrypted-attribute declarations and defaults while adding its own, so shared models compose cleanly and unrelated classes stay empty.

**Expected Behavior / Usage:**

A subclass inherits the parent's full catalogue of encrypted attributes plus the parent's default options, extended by any attributes the subclass declares: the subclass catalogue equals the parent catalogue plus the subclass-only attributes. Default options are shared and non-empty across parent and subclass. A separate unrelated class that merely enables the mixin but declares nothing starts with an empty catalogue and empty default options. Transcript lines are `inherit_keys_match=<bool>`, `inherit_options_match=<bool>`, `inherit_options_nonempty=<bool>`, `fresh_attributes_empty=<bool>`, and `fresh_options_empty=<bool>`.

**Test Cases:** `rcb_tests/public_test_cases/feature12_inheritance.json`

```json
{
  "description": "A subclass inherits its parent's full catalogue of encrypted attributes plus the parent's default options, extended by any attributes the subclass declares for itself: the subclass catalogue equals the parent catalogue plus the subclass-only attributes. The default options are shared and non-empty across parent and subclass. A separate, unrelated class that merely enables the mixin but declares nothing starts with an empty catalogue and empty default options. Each transcript line reports an inheritance-equivalence flag, a default-options-equivalence flag, a non-empty flag, or an emptiness fact.",
  "cases": [
    {
      "input": {
        "model": {
          "attributes": [ { "names": ["email"], "options": { "key": { "$key": true } } } ],
          "global_options": { "key": { "$proc_key": true }, "mode": "per_attribute_iv_and_salt" },
          "subclass": { "attributes": [ { "names": ["testing"], "options": {} } ] }
        },
        "ops": [ { "kind": "inherit_keys_match", "added": ["testing"] } ]
      },
      "expected_output": "inherit_keys_match=true\n"
    },
    {
      "input": {
        "model": {
          "attributes": [ { "names": ["email"], "options": { "key": { "$key": true } } } ],
          "global_options": { "key": { "$proc_key": true }, "mode": "per_attribute_iv_and_salt" },
          "subclass": { "attributes": [ { "names": ["testing"], "options": {} } ] }
        },
        "ops": [ { "kind": "fresh_class_empty" } ]
      },
      "expected_output": "fresh_attributes_empty=true\nfresh_options_empty=true\n"
    }
  ]
}
```

---

### Feature 13: Per-Encryption Randomization (IV / Salt / Algorithm)

**As a developer**, I want every encryption to use fresh randomization so identical plaintext never yields identical ciphertext, and I want a fixed default algorithm and predictable encoding of the initialization vector.

**Expected Behavior / Usage:**

Every encryption uses a freshly generated initialization vector, and in the salt-bearing mode a freshly generated salt, so these vary across attributes, across instances, and across successive encryptions of the same attribute. Under the default mode an initialization vector is generated but no salt; the salt-bearing mode adds a salt. The default symmetric algorithm is the fixed authenticated AES variant `[a specific sentinel value — ask the PM for the exact string]`, and the initialization vector is base64-encoded for storage unless that encoding is disabled. Transcript lines include `iv_differs_per_attribute=<bool>`, `salt_differs_per_instance[<attr>]=<bool>`, `iv_changes_on_reassign[<attr>]=<bool>`, `iv_present[<attr>]=<bool>`, `salt_present[<attr>]=<bool>`, `iv_base64[<attr>]=<bool>`, and `algorithm[<attr>]=<name>`.

**Test Cases:** `rcb_tests/public_test_cases/feature13_iv_salt.json`

```json
{
  "description": "Every encryption uses a freshly generated initialization vector, and in the salt-bearing mode a freshly generated salt as well, so these values vary across attributes, across instances, and across successive encryptions of the same attribute. Under the default mode an initialization vector is generated but no salt; the salt-bearing mode adds a salt. The default symmetric algorithm is a fixed authenticated AES variant, the initialization vector is base64-encoded for storage unless that encoding is disabled. Each transcript line reports a uniqueness or presence flag, a base64-encoding flag, or the algorithm name.",
  "cases": [
    {
      "input": {
        "model": {
          "attributes": [
            { "names": ["email"], "options": { "key": { "$key": true } } },
            { "names": ["password"], "options": { "key": { "$key": true }, "prefix": "crypted_", "suffix": "_test" } }
          ],
          "global_options": { "key": { "$proc_key": true }, "mode": "per_attribute_iv_and_salt" }
        },
        "ops": [ { "kind": "differs_per_attribute", "attrs": ["email", "password"], "value": "x@y.com", "facet": "iv" } ]
      },
      "expected_output": "iv_differs_per_attribute=true\n"
    },
    {
      "input": {
        "model": {
          "attributes": [ { "names": ["email"], "options": { "key": { "$key": true } } } ],
          "global_options": { "key": { "$proc_key": true } }
        },
        "ops": [ { "kind": "algorithm", "attr": "email" } ]
      },
      "expected_output": "algorithm[email]=[a specific sentinel value — ask the PM for the exact string]\n"
    }
  ]
}
```

---

### Feature 14: Guarded Randomization Generation

**As a developer**, I want initialization-vector and salt generation to honour the same conditional gating as encryption, so randomization is produced exactly when (and only when) encryption actually happens.

**Expected Behavior / Usage:**

When the guard permits encryption, an initialization vector is generated, and in the salt-bearing mode a salt is generated too; when the guard suppresses encryption, neither is generated. An absent value also suppresses generation even when the guard would otherwise permit it. Transcript lines are `iv_present[<attr>]=<bool>` and `salt_present[<attr>]=<bool>`.

**Test Cases:** `rcb_tests/public_test_cases/feature14_guard_iv_salt.json`

```json
{
  "description": "Initialization-vector and salt generation honour the same conditional gating as encryption itself. When the guard permits encryption an initialization vector is generated, and in the salt-bearing mode a salt is generated too; when the guard suppresses encryption neither is generated. An absent value also suppresses generation even when the guard would otherwise permit it. Each transcript line reports whether an initialization vector or salt was generated for the guarded attribute.",
  "cases": [
    {
      "input": {
        "model": {
          "attributes": [
            { "names": ["with_true_if"], "options": { "key": { "$key": true }, "if": true, "mode": "per_attribute_iv_and_salt" } },
            { "names": ["with_false_if"], "options": { "key": { "$key": true }, "if": false, "mode": "per_attribute_iv_and_salt" } },
            { "names": ["with_true_unless"], "options": { "key": { "$key": true }, "unless": true, "mode": "per_attribute_iv_and_salt" } },
            { "names": ["with_false_unless"], "options": { "key": { "$key": true }, "unless": false, "mode": "per_attribute_iv_and_salt" } }
          ],
          "global_options": { "key": { "$proc_key": true } }
        },
        "ops": [ { "kind": "iv_present", "attr": "with_false_if", "value": "derp" } ]
      },
      "expected_output": "iv_present[with_false_if]=false\n"
    },
    {
      "input": {
        "model": {
          "attributes": [
            { "names": ["with_true_if"], "options": { "key": { "$key": true }, "if": true, "mode": "per_attribute_iv_and_salt" } },
            { "names": ["with_false_if"], "options": { "key": { "$key": true }, "if": false, "mode": "per_attribute_iv_and_salt" } },
            { "names": ["with_true_unless"], "options": { "key": { "$key": true }, "unless": true, "mode": "per_attribute_iv_and_salt" } },
            { "names": ["with_false_unless"], "options": { "key": { "$key": true }, "unless": false, "mode": "per_attribute_iv_and_salt" } }
          ],
          "global_options": { "key": { "$proc_key": true } }
        },
        "ops": [ { "kind": "iv_present", "attr": "with_true_if", "value": "derp" } ]
      },
      "expected_output": "iv_present[with_true_if]=true\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured mixin implementing the features above, organized into cohesive units (registration/metadata, per-instance option & key resolution, cipher delegation, encoding, serialization, IV/salt generation). No single god file; the cipher backend, serializer, and encoding are replaceable via options.

2. **The Execution/Test Adapter:** A runnable program that acts as a client to the core mixin. It reads one JSON command object from stdin (a `model` to build and `ops` to perform), invokes idiomatic core calls, and prints the sorted, line-oriented transcript to stdout, strictly matching the per-feature contracts above. It normalizes any error to a neutral category line and never leaks host-language runtime details. The adapter is logically and physically separate from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_registration.json` under `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_registration@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout from the program under test, directly comparable to the case `expected_output`.


---
**Implementation notes:**
- Use constructed name (name + prefix + suffix) or explicit name
- Ciphertext must differ from plaintext
