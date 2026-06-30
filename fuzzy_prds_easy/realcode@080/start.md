## Product Requirement Document

# Container Image Reference & Credential Parsing Toolkit — Deterministic Helpers for an Image-Copy Service

## Project Goal

Build a small, well-factored library of pure parsing and validation helpers that an image-transfer service relies on before it ever touches the network: classify and route registry URIs, parse object-storage archive references, classify credential strings, and bound in-memory reads. The goal is to let the service decide *what* to do — which region, which credential resolution strategy, which storage object, which docker tag — from input strings alone, deterministically and without any I/O.

---

## Background & Problem

A service that copies container images between registries must first interpret a handful of user-supplied strings: a source/destination registry URI, an optional credential string, and (for archives kept in object storage) a custom location reference. Doing this ad hoc scatters fragile string-munging across the codebase and makes the network-touching code impossible to test in isolation.

This toolkit isolates the deterministic decisions into reusable, side-effect-free functions: extract the region from a registry hostname, classify a credential string into a resolution strategy, parse an object-storage archive reference into its structured parts, expose the archive transport's scheme identity and its (deliberately empty) policy-scope support, and read a stream while enforcing a hard size cap. Each function maps inputs to structured output with clearly defined edge cases and error conditions, so the surrounding service can be assembled and validated without any registry, cloud API, or storage backend.

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

Every request is a single JSON object read from stdin. The object always carries an `op` field selecting the operation; the remaining fields are operation-specific. Output is a small, value-rich, newline-terminated `[a specific string to represent an empty key]value` contract written to stdout (one field per line). Errors are reported as neutral, language-independent category lines — never as host-runtime type names or stack traces.

### Feature 1: Registry Region Extraction

**As a developer**, I want to pull the cloud region out of a managed-registry hostname, so I can authenticate against the right regional endpoint before copying an image.

**Expected Behavior / Usage:**

The input carries `op` = `ecr_region` and a `uri` string. The hostname of a managed elastic container registry has the shape `<account>.dkr.ecr.<region>.amazonaws.com`; the region is the single segment sitting between the `dkr.ecr.` label and the `.amazonaws.com` suffix. The operation extracts and reports that region as `region=<value>`. When the URI contains no such hostname, a fixed default region is reported instead. Matching is performed on the substring anywhere within the URI, so any surrounding scheme, path, or tag is ignored.

**Test Cases:** `rcb_tests/public_test_cases/feature1_ecr_region.json`

```json
{
    "description": "Given a container-registry URI string, extract the cloud region embedded in an Elastic Container Registry hostname. The hostname has the shape <account>.dkr.ecr.<region>.amazonaws.com, and the region is the segment located between the registry-service label and the cloud domain suffix. The output reports the extracted region name. When the URI does not contain such a hostname, a fixed default region is reported instead.",
    "cases": [
        {"input": {"op": "ecr_region", "uri": "docker://1234567890.dkr.ecr.us-west-2.amazonaws.com/test:ubuntu"}, "expected_output": "region=us-west-2\n"},
        {"input": {"op": "ecr_region", "uri": "docker://1234567890.dkr.ecr.cn-north-1.amazonaws.com/test:ubuntu"}, "expected_output": "region=cn-north-1\n"}
    ]
}
```

---

### Feature 2: Credential String Classification

**As a developer**, I want to classify a credential string into a resolution strategy, so the service knows whether to fetch a stored secret or use the value inline.

**Expected Behavior / Usage:**

The input carries `op` = `creds_type` and a `creds` string. The value is classified into exactly one of three categories and reported as `creds_type=<CATEGORY>`:
- A value beginning with the well-known cloud resource-name prefix (`arn:aws`) is a stored-secret ARN reference → `SECRET_ARN`.
- Otherwise, a value containing a colon is treated as inline secret text (a literal username/password style value) → `SECRET_TEXT`.
- Any remaining value, including the empty string, is a stored-secret name → `SECRET_NAME`.

The categories are checked in that priority order (prefix first, then colon, then the default), so an ARN prefix wins even though an ARN also contains colons.

**Test Cases:** `rcb_tests/public_test_cases/feature2_creds_type.json`

```json
{
    "description": "Classify a credential string into one of three domain categories used to decide how the credential should later be resolved. A value that begins with the well-known cloud resource-name prefix is classified as a stored-secret ARN reference. Otherwise, a value that contains a colon is classified as inline secret text (a literal username/password style value). Any remaining value, including the empty string, is classified as a stored-secret name. The output reports the category label.",
    "cases": [
        {"input": {"op": "creds_type", "creds": "arn:aws:secretsmanager:us-west-2:00000:secret:fake-secret"}, "expected_output": "creds_type=SECRET_ARN\n"},
        {"input": {"op": "creds_type", "creds": "username:password"}, "expected_output": "creds_type=SECRET_TEXT\n"},
        {"input": {"op": "creds_type", "creds": "fake-secret"}, "expected_output": "creds_type=SECRET_NAME\n"}
    ]
}
```

---

### Feature 3: Object-Storage Archive Image Transport

**As a developer**, I want a transport that understands references to image archives kept in object storage, so the copy engine can route, validate, and structurally parse such references the same way it does for any other image location.

**Expected Behavior / Usage:**

*3.1 Reference Parsing — parse an object-storage archive reference into its structured parts*

The input carries `op` = `parse_reference` and a `ref` string. A reference has the form `//<bucket>[/<key>][:<suffix>]`. Everything up to the first colon identifies a storage bucket and an optional object key: the text immediately after `//` up to the first `/` is the bucket, and anything after that first `/` is the key (the key is empty when omitted, and a trailing slash with no key still yields an empty key). The optional suffix after the first colon is interpreted as either a docker image reference (a repository name with an optional tag) or a zero-based source index introduced by `@`.

A successful parse reports five lines: `valid=true`, then `bucket=<bucket>`, `[a specific string to represent an empty key]<key>`, `ref=<docker-reference-or-(none)>`, and `source_index=<n>`. A supplied docker reference is normalized to its canonical fully-qualified repository form, and a missing tag defaults to the conventional `latest` tag (for example, a bare short repository name expands to its fully-qualified `latest` form). When no docker reference is supplied, `[a specific sentinel string for missing docker regions]` is reported; when no source index is supplied, the sentinel `source_index=-1` is reported. A supplied source index reproduces its numeric value.

The reference is rejected with the single line `valid=false` when: the input is empty; the embedded docker reference is malformed (e.g., contains characters not allowed in a repository name); the embedded reference carries a content digest; a docker reference and a source index are supplied together in either order; or the source index is negative. A docker reference and a source index are mutually exclusive.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_reference_parse.json`

```json
{
    "description": "Parse a location reference for an image archive stored in object storage. The reference has the form //<bucket>[/<key>][:<suffix>]: everything up to the first colon names a storage bucket and an optional object key (the key is empty when omitted, and a trailing slash with no key also yields an empty key). The optional suffix after the first colon is either a docker image reference (a repository with an optional tag) or a zero-based source index introduced by an '@'. A successful parse reports the bucket, the object key, the normalized docker reference, and the source index. A docker reference is normalized to its canonical fully-qualified repository form, and a missing tag defaults to the conventional 'latest' tag; when no docker reference is supplied a none-marker is reported. When no source index is supplied a sentinel negative value is reported. The reference is rejected as invalid when it is empty, when the embedded docker reference is malformed, when it carries a content digest, when a docker reference and a source index are supplied together, or when the source index is negative.",
    "cases": [
        {"input": {"op": "parse_reference", "ref": "//bucket/a/b"}, "expected_output": "valid=true\nbucket=bucket\n[a specific string to represent an empty key]a/b\n[a specific sentinel string for missing docker regions]\nsource_index=-1\n"},
        {"input": {"op": "parse_reference", "ref": "//bucket:busybox"}, "expected_output": "valid=true\nbucket=bucket\n[a specific string to represent an empty key]\nref=docker.io/library/busybox:latest\nsource_index=-1\n"},
        {"input": {"op": "parse_reference", "ref": "//bucket:@0"}, "expected_output": "valid=true\nbucket=bucket\n[a specific string to represent an empty key]\n[a specific sentinel string for missing docker regions]\nsource_index=0\n"},
        {"input": {"op": "parse_reference", "ref": "//bucket:@-1"}, "expected_output": "valid=false\n"}
    ]
}
```

*3.2 Transport Scheme Name — report the transport's scheme identifier*

The input carries `op` = `transport_name`. The transport registers itself under a short, fixed scheme identifier used by callers to select it. The operation reports that identifier as `name=<scheme>`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_transport_name.json`

```json
{
    "description": "Report the scheme name advertised by the object-storage image transport. The transport registers itself under a short, fixed scheme identifier that callers use to select it when routing a reference. The output reports that identifier.",
    "cases": [
        {"input": {"op": "transport_name"}, "expected_output": "[a specific identifier for the transport scheme]\n"}
    ]
}
```

*3.3 Policy Scope Validation — reject all policy-configuration scopes*

The input carries `op` = `policy_scope` and a `scope` string. This transport supports no named policy-configuration scopes: every scope value, including the empty default scope, is rejected. The operation reports `accepted=false` followed by the neutral error category `error=scope_not_supported`, identically for every scope string.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_policy_scope.json`

```json
{
    "description": "Validate a policy-configuration scope string for the object-storage image transport. This transport does not support any named policy scopes: every scope value, including the empty default scope, is rejected. The output reports that the scope was not accepted together with a neutral not-supported error category, independent of the specific scope string supplied.",
    "cases": [
        {"input": {"op": "policy_scope", "scope": "docker.io/library/busybox:notlatest"}, "expected_output": "accepted=false\nerror=scope_not_supported\n"}
    ]
}
```

---

### Feature 4: Size-Bounded Stream Read

**As a developer**, I want to read a stream fully but refuse to buffer more than a fixed number of bytes, so a hostile or oversized input cannot exhaust memory.

**Expected Behavior / Usage:**

The input carries `op` = `read_limit`, a `size` (the number of bytes available in the stream) and a `limit` (the maximum number of bytes permitted to be buffered). When `size` is less than or equal to `limit`, the read succeeds and reports `ok=true` followed by `bytes_read=<size>`. When `size` exceeds `limit`, the read fails and reports `ok=false`, the neutral category `error=size_exceeded`, and `limit=<limit>`. The boundary is inclusive: a stream exactly equal to the limit succeeds, and a stream one byte larger fails.

**Test Cases:** `rcb_tests/public_test_cases/feature4_read_limit.json`

```json
{
    "description": "Read an entire input stream into memory while enforcing an upper bound on how many bytes may be copied, guarding against unbounded memory use. The request supplies the number of bytes available in the stream and the maximum number of bytes permitted. When the available size is less than or equal to the limit the read succeeds and reports the number of bytes read. When the available size exceeds the limit the read fails and reports a neutral size-exceeded error together with the limit that was applied.",
    "cases": [
        {"input": {"op": "read_limit", "size": 2560, "limit": 2560}, "expected_output": "ok=true\nbytes_read=2560\n"},
        {"input": {"op": "read_limit", "size": 2561, "limit": 2560}, "expected_output": "ok=false\nerror=size_exceeded\nlimit=2560\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above — region extraction, credential classification, archive-reference parsing with transport metadata, and the size-bounded read — with the core logic decoupled from standard I/O and JSON parsing. Normalizing a docker reference to its canonical fully-qualified form with a default `latest` tag, and rejecting digest-bearing references, are part of the reference-parsing contract.

2. **The Execution/Test Adapter:** A runnable program (entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, dispatches on the `op` field, invokes the appropriate core logic, and prints the resulting `[a specific string to represent an empty key]value` contract (or a neutral `error=<category>` line) to stdout, matching the per-feature contracts above. Native failures from the core (malformed references, exceeded size limits, unsupported scopes) are translated into the neutral category lines in this adapter layer.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same trailing character convention as the audit log formatter helper
