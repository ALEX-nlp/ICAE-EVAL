## Product Requirement Document

# Field-Level Encryption Support Toolkit for ORM Query Middleware — Key Management, Schema-Annotation Parsing & Payload Traversal

## Project Goal

Build the supporting toolkit that lets an ORM/query-middleware layer transparently encrypt selected string fields at rest, so application developers can mark a field as encrypted in their data-model schema and have values encrypted on write and decrypted on read automatically, without hand-rolling per-field crypto or rewriting every query. This toolkit covers the non-database building blocks: assembling a key/keychain from configuration, parsing the inline schema annotations that declare encryption and hashing intent, analysing a whole data-model schema into per-model descriptors, and the generic tree-walking primitives used to locate target fields inside arbitrary query payloads and result sets.

---

## Background & Problem

Without such a toolkit, developers who want encryption-at-rest for a few sensitive columns must intercept every read and write, manually walk deeply nested query arguments to find the right fields, manage multiple keys for rotation, and keep all of this in sync with their schema. This is repetitive, fragile, and easy to get wrong (missing a nested relation, leaking plaintext into a search clause, or losing the ability to decrypt old rows after a key change).

With this toolkit, the intent is declared once per field as an inline annotation in the schema, configuration is reduced to providing one encryption key (plus optional extra decryption keys for rotation), and a generic depth-first traversal locates exactly the fields that need transformation anywhere in a payload — including inside nested relation operations. The components are pure and deterministic so they can be unit-tested in isolation from any live database.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains. This domain has several distinct responsibilities (key management, annotation parsing, schema analysis, tree traversal, payload visiting) and should be organized into separate modules.

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

### Feature 1: Key & Keychain Configuration

**As a developer**, I want to build an encryption key and a multi-key keychain from a small configuration object, so I can encrypt new data with one key while still being able to decrypt data written under older keys (key rotation).

**Expected Behavior / Usage:**

The input supplies an optional encryption key as a self-describing key string (a string that encodes its own algorithm and key material, of the form `k1.aesgcm256.<base64-material>`), and an optional list of additional decryption-only key strings. An encryption key is mandatory: if none is provided, configuration is rejected and reported as a neutral error category line `error=no_encryption_key` with no further output. When a valid encryption key is provided, configuration succeeds and reports three lines: `encryptionKey=<canonical key string>` — the encryption key re-serialized to its canonical string form (it must round-trip to the same value that was supplied); `encryptionKeyInKeychain=<true|false>` — whether the encryption key is itself present in the resulting keychain (it always is, so the same key can both encrypt new data and decrypt its own ciphertext); and `keychainSize=<n>` — the number of distinct keys in the keychain. The keychain always contains the encryption key plus every supplied decryption key, with duplicates collapsed so a key is never counted twice (the encryption key is implicitly a decryption key as well). Each line is terminated by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_key_configuration.json`

```json
{
  "description": "Build an encryption/decryption keychain from a configuration. A configuration must supply an encryption key (a self-describing key string); when it is absent the operation is rejected with a neutral error category. When a valid encryption key is supplied the operation succeeds and reports the canonical (re-serialized) form of that encryption key, whether the encryption key itself is present in the resulting keychain (it always is, so it can both encrypt and decrypt), and the total number of distinct keys in the keychain. Additional decryption-only keys may be supplied to enlarge the keychain, with duplicates collapsed so the encryption key is never counted twice.",
  "cases": [
    {
      "input": { "op": "configure_keys" },
      "expected_output": "error=no_encryption_key\n"
    },
    {
      "input": {
        "op": "configure_keys",
        "encryptionKey": "k1.aesgcm256.DbQoar8ZLuUsOHZNyrnjlskInHDYlzF3q6y1KGM7DUM="
      },
      "expected_output": "encryptionKey=k1.aesgcm256.DbQoar8ZLuUsOHZNyrnjlskInHDYlzF3q6y1KGM7DUM=\nencryptionKeyInKeychain=true\nkeychainSize=1\n"
    },
    {
      "input": {
        "op": "configure_keys",
        "encryptionKey": "k1.aesgcm256.DbQoar8ZLuUsOHZNyrnjlskInHDYlzF3q6y1KGM7DUM=",
        "decryptionKeys": [
          "k1.aesgcm256.4BNYdJnjOQJP2adq9cGM9kb4dZxDujUs6aPS0VeRtAM=",
          "k1.aesgcm256.El9unG7WBAVRQdATOyMggE3XrLV2ZjTGKdajfmIeBPs="
        ]
      },
      "expected_output": "encryptionKey=k1.aesgcm256.DbQoar8ZLuUsOHZNyrnjlskInHDYlzF3q6y1KGM7DUM=\nencryptionKeyInKeychain=true\nkeychainSize=3\n"
    }
  ]
}
```

---

### Feature 2: Encrypted-Field Annotation Parsing

**As a developer**, I want an inline annotation embedded in a schema field's documentation comment to be parsed into a clear encrypt/strict-decryption decision, so a single marker on the field controls how that field is protected.

**Expected Behavior / Usage:**

The input is an optional annotation string (the free text attached to a field). Parsing looks for an `@encrypted` marker, optionally followed by a query string of flags (e.g. `?mode=strict`). When the marker is absent entirely (or the input is omitted), the result is `match=none`. When the marker is present, the parse yields two booleans, reported as `encrypt=<true|false>` and `strictDecryption=<true|false>`. A `mode` query parameter selects the behavior: `mode=default` (or no mode) gives `encrypt=true`, `strictDecryption=false`; `mode=strict` gives `encrypt=true`, `strictDecryption=true` (decryption failures are fatal); `mode=readonly` gives `encrypt=false`, `strictDecryption=false` (values are read/decrypted but never re-encrypted). Two legacy bare flags are also accepted and map onto the same modes: `?strict` ⇒ strict mode, `?readonly` ⇒ readonly mode; when both are present, `readonly` takes precedence over `strict`. Any unrecognized query parameter (e.g. `?with=junk`) and any unknown `mode` value both fall back to default behavior. Each output line ends with a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature2_parse_encrypted_annotation.json`

```json
{
  "description": "Parse an inline encryption annotation that may appear inside a schema field documentation string and decide whether that field should be encrypted and whether decryption must be strict. The annotation marker may carry an optional query string of flags. When no annotation marker is present at all the result is a no-match. When the marker is present, two booleans are derived: whether values are encrypted on write, and whether a failed decryption must be treated as fatal. A mode selector chooses among default behavior (encrypt, non-strict), strict behavior (encrypt, strict decryption), and read-only behavior (do not encrypt, non-strict). Two legacy boolean flags map onto the same modes, with the read-only flag taking precedence over the strict flag when both are present. Unrecognized query parameters and unknown mode values fall back to the default behavior.",
  "cases": [
    {
      "input": { "op": "parse_encrypted" },
      "expected_output": "match=none\n"
    },
    {
      "input": { "op": "parse_encrypted", "annotation": " pre @encrypted post " },
      "expected_output": "encrypt=true\nstrictDecryption=false\n"
    },
    {
      "input": { "op": "parse_encrypted", "annotation": " pre @encrypted?mode=strict post " },
      "expected_output": "encrypt=true\nstrictDecryption=true\n"
    },
    {
      "input": { "op": "parse_encrypted", "annotation": " pre @encrypted?mode=readonly post " },
      "expected_output": "encrypt=false\nstrictDecryption=false\n"
    }
  ]
}
```

---

### Feature 3: Hash-Field Annotation Parsing

**As a developer**, I want an inline hash annotation parsed into a hashing configuration, so a companion field can store a deterministic hash of an encrypted field to enable equality search over data that is otherwise encrypted.

**Expected Behavior / Usage:**

The input is an optional annotation string. Parsing looks for an `@encryption:hash(<sourceField>)` marker that names, in parentheses, the single source field whose value should be hashed, optionally followed by a query string of options. When no hash marker is present (or the input is omitted), or when the marker is present but the source-field name is missing/empty, the result is `match=none`. When a source field is named, the parse yields four reported values: `sourceField=<name>` (the named field), `algorithm=<name>` (the hash algorithm, default `sha256`), `inputEncoding=<name>` (how the source value is interpreted before hashing, default `utf8`), and `outputEncoding=<name>` (how the digest is encoded, default `hex`). Each of `algorithm`, `inputEncoding`, and `outputEncoding` can be overridden through a matching query parameter. Each output line ends with a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature3_parse_hash_annotation.json`

```json
{
  "description": "Parse an inline hash annotation that may appear inside a schema field documentation string. The annotation names a single source field in parentheses and may carry an optional query string of options. When no hash annotation marker is present, or when the marker is present but the source-field name is missing, the result is a no-match. When a valid source field is named, the parse yields the source field name plus a hashing algorithm, an input encoding and an output encoding; each of these has a default value used when the corresponding option is omitted, and each can be overridden through the query string.",
  "cases": [
    {
      "input": { "op": "parse_hash" },
      "expected_output": "match=none\n"
    },
    {
      "input": { "op": "parse_hash", "annotation": " pre @encryption:hash(foo) post " },
      "expected_output": "sourceField=foo\nalgorithm=sha256\ninputEncoding=utf8\noutputEncoding=hex\n"
    },
    {
      "input": {
        "op": "parse_hash",
        "annotation": " pre @encryption:hash(foo)?algorithm=sha512&inputEncoding=base64&outputEncoding=base64 post"
      },
      "expected_output": "sourceField=foo\nalgorithm=sha512\ninputEncoding=base64\noutputEncoding=base64\n"
    }
  ]
}
```

---

### Feature 4: Data-Model Schema Analysis

**As a developer**, I want a whole data-model schema analysed into a per-model descriptor, so the middleware knows which fields to encrypt, how models relate, and how to iterate rows during migrations.

**Expected Behavior / Usage:**

The input is a data-model schema written in a model-definition language: a set of `model <Name> { ... }` blocks whose fields may carry inline documentation annotations (the `@encrypted` and `@encryption:hash(...)` markers from Features 2 and 3, plus an `@encryption:cursor` marker). The analysis produces, for every model, a descriptor with three parts. `fields` maps each encrypted string field name to its encryption configuration (`encrypt`, `strictDecryption`), and when a hash annotation references that field, an attached `hash` block (`targetField` = the field carrying the annotation, plus `algorithm`, `inputEncoding`, `outputEncoding`, and a `normalize` list of normalization options). `connections` maps each field that refers to another model to a descriptor of the target `modelName` and whether the relation `isList`. `cursor` names the field used to iterate rows for migrations, chosen by preference order: an explicit `@encryption:cursor`-annotated field first, then the model's id field, then any unique field — restricted to cursor-capable scalar types (integer, string, big-integer). An explicit cursor annotation is validated: pointing it at a non-unique field, an unsupported-type field, or an encrypted field is an error. Only string-typed fields may be encrypted or hashed; annotating a non-string field is an error. The full descriptor is rendered as a canonical, pretty-printed JSON document (two-space indentation), with model entries in schema order and, within each model, the keys ordered `cursor`, `fields`, `connections`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_analyse_schema_model.json`

```json
{
  "description": "Analyse a full data-model schema and produce, for every model, a descriptor of: which string fields are encrypted (with their per-field encryption settings and any attached hash configuration), which fields are relation connections to other models (and whether each connection is a list), and which field should be used as the iteration cursor for that model. The cursor is chosen by preferring an explicitly annotated cursor field, then the model id field, then any unique field, restricted to cursor-capable scalar types. An explicit cursor annotation that points at a non-unique field, an unsupported type, or an encrypted field is rejected. A hash annotation attaches its configuration onto the encrypted source field it references. The descriptor is rendered as a canonical, pretty-printed JSON document.",
  "cases": [
    {
      "input": {
        "op": "analyse_schema",
        "datamodel": "\n        model User {\n          id           Int     @id @default(autoincrement())\n          email        String  @unique\n          name         String? /// @encrypted\n          nameHash     String? /// @encryption:hash(name)?normalize=lowercase\n          posts        Post[]\n          pinnedPost   Post?   @relation(fields: [pinnedPostId], references: [id], name: \"pinnedPost\")\n          pinnedPostId Int?\n        }\n\n        model Post {\n          id         Int        @id @default(autoincrement())\n          title      String\n          content    String?    /// @encrypted\n          author     User?      @relation(fields: [authorId], references: [id], onDelete: Cascade, onUpdate: Cascade)\n          authorId   Int?\n          cursor     Int        @unique /// @encryption:cursor\n          categories Category[]\n          havePinned User[]     @relation(\"pinnedPost\")\n        }\n\n        // Model without encrypted fields\n        model Category {\n          id    Int    @id @default(autoincrement())\n          name  String\n          posts Post[]\n        }\n\n        // Cursor fallback on unique fields\n        model Unique {\n          id     Json   @id // invalid type for iteration\n          unique String @unique\n        }\n      "
      },
      "expected_output": "{\n  \"User\": {\n    \"cursor\": \"id\",\n    \"fields\": {\n      \"name\": {\n        \"encrypt\": true,\n        \"strictDecryption\": false,\n        \"hash\": {\n          \"targetField\": \"nameHash\",\n          \"algorithm\": \"sha256\",\n          \"inputEncoding\": \"utf8\",\n          \"outputEncoding\": \"hex\",\n          \"normalize\": [\n            \"lowercase\"\n          ]\n        }\n      }\n    },\n    \"connections\": {\n      \"posts\": {\n        \"modelName\": \"Post\",\n        \"isList\": true\n      },\n      \"pinnedPost\": {\n        \"modelName\": \"Post\",\n        \"isList\": false\n      }\n    }\n  },\n  \"Post\": {\n    \"cursor\": \"cursor\",\n    \"fields\": {\n      \"content\": {\n        \"encrypt\": true,\n        \"strictDecryption\": false\n      }\n    },\n    \"connections\": {\n      \"author\": {\n        \"modelName\": \"User\",\n        \"isList\": false\n      },\n      \"categories\": {\n        \"modelName\": \"Category\",\n        \"isList\": true\n      },\n      \"havePinned\": {\n        \"modelName\": \"User\",\n        \"isList\": true\n      }\n    }\n  },\n  \"Category\": {\n    \"cursor\": \"id\",\n    \"fields\": {},\n    \"connections\": {\n      \"posts\": {\n        \"modelName\": \"Post\",\n        \"isList\": true\n      }\n    }\n  },\n  \"Unique\": {\n    \"cursor\": \"unique\",\n    \"fields\": {},\n    \"connections\": {}\n  }\n}\n"
    }
  ]
}
```

---

### Feature 5: Depth-First JSON Tree Traversal With State Threading

**As a developer**, I want a generic depth-first traversal of an arbitrary JSON value that threads an accumulating state from parents to children, so higher-level logic can locate and transform nodes anywhere in deeply nested query payloads and result sets.

**Expected Behavior / Usage:**

The input is an arbitrary JSON value (`tree`) plus an `initialState`. The traversal visits every node exactly once, depth-first: the root first, then descending into array elements (by index) and object entries in source order. For each visited node a callback receives the current threaded state and an item describing the node: `key` (the node's key relative to its parent, absent/`null` for the root), `path` (the list of keys from the root to this node), `type` (one of `string`, `number`, `boolean`, `null`, `array`, `object`), and `node` (the value itself). The value the callback returns becomes the state passed **only** to that node's direct children; sibling subtrees therefore each receive the same parent-contributed state independently, and a value returned deep in one branch never leaks into another branch. The total number of callback invocations equals the total node count (every collection node plus every nested leaf). In this contract the harness callback returns each node's path (joined with `.`, or the literal `root` for the root node) as the state handed to its children, which makes the parent→child threading directly observable in the `state` field of each child. The adapter emits one compact JSON line per visit, in visitation order, with keys in the fixed order `state`, `key`, `path`, `type`, `node`, followed by a final `count=<n>` line; every line ends with a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature5_traverse_json_tree.json`

```json
{
  "description": "Traverse an arbitrary JSON value depth-first in a reduce-like manner, invoking a callback once per node (the root first, then descending into array elements and object entries in source order). For each visited node the callback receives the threaded state and an item describing the node: its key relative to its parent (absent for the root), its path from the root as an array of keys, its kind (string, number, boolean, null, array, or object), and the node value itself. The callback returns a new state that is passed only to that node direct children, so sibling branches each observe the same parent-contributed state independently. The number of callback invocations equals the total number of nodes (collections plus all nested leaves). Here the harness callback returns each node path as the state handed to its children, making the threading observable.",
  "cases": [
    {
      "input": { "op": "traverse_tree", "tree": "Hello, World!", "initialState": null },
      "expected_output": "{\"state\":null,\"key\":null,\"path\":[],\"type\":\"string\",\"node\":\"Hello, World!\"}\ncount=1\n"
    },
    {
      "input": {
        "op": "traverse_tree",
        "tree": ["John", "Paul", "George", "Ringo"],
        "initialState": null
      },
      "expected_output": "{\"state\":null,\"key\":null,\"path\":[],\"type\":\"array\",\"node\":[\"John\",\"Paul\",\"George\",\"Ringo\"]}\n{\"state\":\"root\",\"key\":\"0\",\"path\":[\"0\"],\"type\":\"string\",\"node\":\"John\"}\n{\"state\":\"root\",\"key\":\"1\",\"path\":[\"1\"],\"type\":\"string\",\"node\":\"Paul\"}\n{\"state\":\"root\",\"key\":\"2\",\"path\":[\"2\"],\"type\":\"string\",\"node\":\"George\"}\n{\"state\":\"root\",\"key\":\"3\",\"path\":[\"3\"],\"type\":\"string\",\"node\":\"Ringo\"}\ncount=5\n"
    },
    {
      "input": {
        "op": "traverse_tree",
        "tree": { "John": "Lennon", "Paul": "McCartney", "George": "Harrison", "Ringo": "Starr" },
        "initialState": null
      },
      "expected_output": "{\"state\":null,\"key\":null,\"path\":[],\"type\":\"object\",\"node\":{\"John\":\"Lennon\",\"Paul\":\"McCartney\",\"George\":\"Harrison\",\"Ringo\":\"Starr\"}}\n{\"state\":\"root\",\"key\":\"John\",\"path\":[\"John\"],\"type\":\"string\",\"node\":\"Lennon\"}\n{\"state\":\"root\",\"key\":\"Paul\",\"path\":[\"Paul\"],\"type\":\"string\",\"node\":\"McCartney\"}\n{\"state\":\"root\",\"key\":\"George\",\"path\":[\"George\"],\"type\":\"string\",\"node\":\"Harrison\"}\n{\"state\":\"root\",\"key\":\"Ringo\",\"path\":[\"Ringo\"],\"type\":\"string\",\"node\":\"Starr\"}\ncount=5\n"
    }
  ]
}
```

---

### Feature 6: Visiting Encrypted Target Fields In A Write Payload

**As a developer**, I want a write operation's argument payload walked to surface every encrypted-target string field, following relation links so nested writes are covered too, so the middleware can transform exactly the right values before they hit the database.

**Expected Behavior / Usage:**

The input supplies an analysed data-model (the same schema-analysis used in Feature 4, provided here as a schema string the adapter analyses) and a write-operation payload: an `action`, a root `model` name, and an `args` object (plus inert bookkeeping fields). The traversal walks `args` and, whenever it reaches a string field that is configured as an encrypted target on the currently active model, emits one visit. As it descends through fields that are relation connections, the active model switches to the connected model, so encrypted fields inside nested relation operations (e.g. a `create` block under a relation) are found with their full nested path. Each emitted visit is a JSON object reporting `field` (the field name), `model` (the active model name), `fieldConfig` (the encryption configuration `encrypt`/`strictDecryption`), `path` (the dotted path of the value within `args`), and `value` (the plaintext at that path), with keys in the order `field`, `model`, `fieldConfig`, `path`, `value`. Top-level encrypted fields are visited with a single-segment path; encrypted fields inside nested relation create blocks are visited with their full dotted path and the connected model name. Non-encrypted fields produce no visit. After all visits, a final `count=<n>` line reports the number of visits. Every line ends with a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature6_visit_input_target_fields.json`

```json
{
  "description": "Given an analysed data-model and a write operation payload (an action, a root model name, and an args object), walk the args structure and emit one visit per encrypted-target string field reached, following relation connections to switch the active model as nesting changes. Each visit reports the dotted path to the value within args, the value itself, the active model and field names, and the field encryption configuration. Plain top-level encrypted fields are visited directly; encrypted fields located inside nested relation create blocks are visited with their full nested path and the connected model. Non-encrypted fields produce no visit. The total number of visits is also reported.",
  "cases": [
    {
      "input": {
        "op": "visit_input",
        "datamodel": "\n      model User {\n        id           Int     @id @default(autoincrement())\n        email        String  @unique\n        name         String? /// @encrypted\n        posts        Post[]\n        pinnedPost   Post?   @relation(fields: [pinnedPostId], references: [id], name: \"pinnedPost\")\n        pinnedPostId Int?\n      }\n\n      model Post {\n        id         Int        @id @default(autoincrement())\n        title      String\n        content    String? /// @encrypted\n        author     User?      @relation(fields: [authorId], references: [id], onDelete: Cascade, onUpdate: Cascade)\n        authorId   Int?\n        categories Category[]\n        havePinned User[]     @relation(\"pinnedPost\")\n      }\n\n      // Model without encrypted fields\n      model Category {\n        id    Int    @id @default(autoincrement())\n        name  String\n        posts Post[]\n      }\n    ",
        "params": {
          "action": "create",
          "model": "User",
          "args": { "email": "007@hmss.gov.uk", "name": "James Bond" },
          "dataPath": [],
          "runInTransaction": false
        }
      },
      "expected_output": "{\"field\":\"name\",\"model\":\"User\",\"fieldConfig\":{\"encrypt\":true,\"strictDecryption\":false},\"path\":\"name\",\"value\":\"James Bond\"}\ncount=1\n"
    },
    {
      "input": {
        "op": "visit_input",
        "datamodel": "\n      model User {\n        id           Int     @id @default(autoincrement())\n        email        String  @unique\n        name         String? /// @encrypted\n        posts        Post[]\n        pinnedPost   Post?   @relation(fields: [pinnedPostId], references: [id], name: \"pinnedPost\")\n        pinnedPostId Int?\n      }\n\n      model Post {\n        id         Int        @id @default(autoincrement())\n        title      String\n        content    String? /// @encrypted\n        author     User?      @relation(fields: [authorId], references: [id], onDelete: Cascade, onUpdate: Cascade)\n        authorId   Int?\n        categories Category[]\n        havePinned User[]     @relation(\"pinnedPost\")\n      }\n\n      // Model without encrypted fields\n      model Category {\n        id    Int    @id @default(autoincrement())\n        name  String\n        posts Post[]\n      }\n    ",
        "params": {
          "action": "create",
          "model": "User",
          "args": {
            "email": "007@hmss.gov.uk",
            "name": "James Bond",
            "posts": {
              "create": [
                { "title": "First report", "content": "Reporting for duty" },
                { "title": "Mission Briefing", "content": "Going after Spectre" }
              ]
            }
          },
          "dataPath": [],
          "runInTransaction": false
        }
      },
      "expected_output": "{\"field\":\"name\",\"model\":\"User\",\"fieldConfig\":{\"encrypt\":true,\"strictDecryption\":false},\"path\":\"name\",\"value\":\"James Bond\"}\n{\"field\":\"content\",\"model\":\"Post\",\"fieldConfig\":{\"encrypt\":true,\"strictDecryption\":false},\"path\":\"posts.create.0.content\",\"value\":\"Reporting for duty\"}\n{\"field\":\"content\",\"model\":\"Post\",\"fieldConfig\":{\"encrypt\":true,\"strictDecryption\":false},\"path\":\"posts.create.1.content\",\"value\":\"Going after Spectre\"}\ncount=3\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-module codebase implementing the features above — key/keychain configuration, encrypted-field annotation parsing, hash-field annotation parsing, schema analysis, generic depth-first tree traversal, and payload field visiting. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (entry point) that acts as a client to the core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request object from stdin, selects behavior by the `op` field (`configure_keys`, `parse_encrypted`, `parse_hash`, `analyse_schema`, `traverse_tree`, `visit_input`), invokes the appropriate core logic, and prints the result to stdout matching the per-feature contracts above. Native errors from the core (e.g. a missing encryption key) must be rendered as neutral `error=<category>` lines; the adapter must never leak host-language runtime details into stdout.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- the fallback type for string nodes
- follow the state object format from the parsing module
