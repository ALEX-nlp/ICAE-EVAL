## Product Requirement Document

# Cloud Infrastructure Storage Adapter - Configuration, Storage, and Share Integration Contracts

## Project Goal

Build a cloud infrastructure storage adapter library that allows developers to parse service endpoints, expose storage-interface identity and capabilities, validate storage/share options, encrypt secrets, and translate shared filesystem data into persistent-volume outputs without hand-writing repetitive integration glue.

---

## Background & Problem

Without this library/tool, developers are forced to manually parse endpoint strings, maintain storage-interface metadata, validate interdependent option maps, manage encrypted secret payloads, and translate shared filesystem API responses into volume definitions. This leads to repetitive code, inconsistent validation behavior, fragile error handling, and integration bugs around storage and shared filesystem provisioning.

With this library/tool, callers can provide structured input values and receive deterministic, externally observable outputs for endpoint parsing, encryption round-trips, driver discovery, option validation, shared filesystem volume-source construction, HTTP-backed access grants, and command-line user-agent parsing.

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

### Feature 1: Endpoint String Parsing

**As a developer**, I want to parse listener endpoint strings, so I can configure storage services from compact endpoint values without duplicating parsing rules.

**Expected Behavior / Usage:**

The input is an object containing `endpoint`, a string. Supported endpoints begin with `unix://` or `tcp://` in any letter case and must include a non-empty address after the separator. The output contains the exact protocol text before the separator and the address text after the separator. Malformed endpoints, missing separators, unsupported forms, and empty addresses produce a normalized `invalid_endpoint` error with the raw endpoint on its own line.

**Test Cases:** `rcb_tests/public_test_cases/feature1_endpoint_parsing.json`

```json
{
  "description": "Parse supported listener endpoint strings into transport protocol and address, while malformed or empty endpoint strings produce a normalized endpoint error.",
  "cases": [
    {
      "input": {"endpoint": "unix://fake.sock"},
      "expected_output": "protocol=unix\naddress=fake.sock\n"
    },
    {
      "input": {"endpoint": "unix:///fakedir/fakedir/fake.sock"},
      "expected_output": "protocol=unix\naddress=/fakedir/fakedir/fake.sock\n"
    },
    {
      "input": {"endpoint": "UNIX://fake.sock"},
      "expected_output": "protocol=UNIX\naddress=fake.sock\n"
    },
    {
      "input": {"endpoint": "tcp://127.0.0.1:80"},
      "expected_output": "protocol=tcp\naddress=127.0.0.1:80\n"
    },
    {
      "input": {"endpoint": "TCP://127.0.0.1:80"},
      "expected_output": "protocol=TCP\naddress=127.0.0.1:80\n"
    },
    {
      "input": {"endpoint": "tcp://fakehost:80"},
      "expected_output": "protocol=tcp\naddress=fakehost:80\n"
    },
    {
      "input": {"endpoint": "unix:/fake.sock/"},
      "expected_output": "error=invalid_endpoint\nendpoint=unix:/fake.sock/\n"
    },
    {
      "input": {"endpoint": "fake.sock"},
      "expected_output": "error=invalid_endpoint\nendpoint=fake.sock\n"
    },
    {
      "input": {"endpoint": "unix://"},
      "expected_output": "error=invalid_endpoint\nendpoint=unix://\n"
    },
    {
      "input": {"endpoint": "://"},
      "expected_output": "error=invalid_endpoint\nendpoint=://\n"
    },
    {
      "input": {"endpoint": ""},
      "expected_output": "error=invalid_endpoint\nendpoint=\n"
    }
  ]
}
```

---

### Feature 2: AES-CBC Secret Round Trip

**As a developer**, I want to encrypt secret text and decrypt it back, so I can verify encrypted storage payload handling without exposing random ciphertext bytes as a stable contract.

**Expected Behavior / Usage:**

The input is an object with `plaintext` and a valid AES key string. The system encrypts the plaintext, decrypts the produced ciphertext, and prints the recovered plaintext plus the produced ciphertext length. Because encryption uses random initialization data, ciphertext bytes are not part of the stable output. If `corrupt_ciphertext` is true, the adapter corrupts the generated ciphertext before decrypting and must print the normalized `invalid_ciphertext` category.

**Test Cases:** `rcb_tests/public_test_cases/feature2_aescbc_roundtrip.json`

```json
{
  "description": "Encrypt plaintext with a 32-byte AES key and decrypt the produced ciphertext back to the original plaintext; corrupted ciphertext is reported as a normalized ciphertext error.",
  "cases": [
    {
      "input": {"plaintext": "mypassword", "key": "0123456789abcdef0123456789abcdef"},
      "expected_output": "plaintext=mypassword\nciphertext_len=32\n"
    },
    {
      "input": {"plaintext": "mypassword", "key": "0123456789abcdef0123456789abcdef", "corrupt_ciphertext": true},
      "expected_output": "error=invalid_ciphertext\n"
    }
  ]
}
```

---

### Feature 3: Storage Interface Driver Discovery

**As a developer**, I want to query storage driver identity and advertised controller operations, so I can verify that an integration endpoint exposes the expected interface surface.

**Expected Behavior / Usage:**

The input either requests plugin metadata with `metadata_service` or asks whether a named `controller_capability` is supported. Metadata output includes a stable driver name and vendor version. Capability output includes `supported=true` and echoes the requested capability for supported operations. The supported capability names in this contract are `unknown`, `publish_unpublish_volume`, `create_delete_volume`, `list_volumes`, `create_delete_snapshot`, and `list_snapshots`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_csi_identity_and_capabilities.json`

```json
{
  "description": "Expose storage interface identity metadata and report the controller operations that the driver advertises as supported.",
  "cases": [
    {
      "input": {"metadata_service": "plugin_info"},
      "expected_output": "name=cinder.csi.openstack.org\nvendor_version=1.1.0\n"
    },
    {
      "input": {"controller_capability": "unknown"},
      "expected_output": "supported=true\ncapability=unknown\n"
    },
    {
      "input": {"controller_capability": "publish_unpublish_volume"},
      "expected_output": "supported=true\ncapability=publish_unpublish_volume\n"
    },
    {
      "input": {"controller_capability": "create_delete_volume"},
      "expected_output": "supported=true\ncapability=create_delete_volume\n"
    },
    {
      "input": {"controller_capability": "list_volumes"},
      "expected_output": "supported=true\ncapability=list_volumes\n"
    },
    {
      "input": {"controller_capability": "create_delete_snapshot"},
      "expected_output": "supported=true\ncapability=create_delete_snapshot\n"
    },
    {
      "input": {"controller_capability": "list_snapshots"},
      "expected_output": "supported=true\ncapability=list_snapshots\n"
    }
  ]
}
```

---

### Feature 4: String Option Map Validation

**As a developer**, I want to validate string option maps with required, optional, conditional, default, dependency, preclusion, and pattern rules, so I can reject invalid storage configuration before provisioning.

**Expected Behavior / Usage:**

The input is an object containing a named `rule_set` and a `values` object of string key/value pairs. A successful validation prints `valid=true` followed by all fields in stable key order and their populated values, including empty fields and defaulted values. A failed validation prints `valid=false` and a normalized language-neutral error category: `missing_required_value`, `dependency_not_satisfied`, `precluded_value_present`, or `pattern_mismatch`. The named rule sets define the behavior under test: required fields must be present; optional fields may be absent; conditional required/optional behavior depends on whether `a` equals `FOO`; defaulting fills `a` with `FOO` when absent; dependency rules require `d` to be accompanied by `c` and exactly one of `a` or `b`; preclusion rules reject `a` or `b` when `c` is present; pattern rules accept boolean text and reject non-matching text.

**Test Cases:** `rcb_tests/public_test_cases/feature4_option_validation.json`

```json
{
  "description": "Validate string option maps against required, optional, conditional, defaulting, dependency, preclusion, and pattern rules, returning populated fields or normalized validation errors.",
  "cases": [
    {"input": {"rule_set": "required", "values": {}}, "expected_output": "valid=false\n[a specific sentinel value — ask the PM for the exact string]\n"},
    {"input": {"rule_set": "required", "values": {"a": "A"}}, "expected_output": "valid=true\na=A\n"},
    {"input": {"rule_set": "optional", "values": {}}, "expected_output": "valid=true\na=\n"},
    {"input": {"rule_set": "required_when_a_is_FOO", "values": {}}, "expected_output": "valid=true\na=\nb=\n"},
    {"input": {"rule_set": "required_when_a_is_FOO", "values": {"a": "xxx"}}, "expected_output": "valid=true\na=xxx\nb=\n"},
    {"input": {"rule_set": "required_when_a_is_FOO", "values": {"a": "FOO"}}, "expected_output": "valid=false\n[a specific sentinel value — ask the PM for the exact string]\n"},
    {"input": {"rule_set": "required_when_a_is_FOO", "values": {"a": "FOO", "b": "BAR"}}, "expected_output": "valid=true\na=FOO\nb=BAR\n"},
    {"input": {"rule_set": "optional_when_a_is_FOO", "values": {}}, "expected_output": "valid=false\n[a specific sentinel value — ask the PM for the exact string]\n"},
    {"input": {"rule_set": "optional_when_a_is_FOO", "values": {"a": "xxx"}}, "expected_output": "valid=false\n[a specific sentinel value — ask the PM for the exact string]\n"},
    {"input": {"rule_set": "optional_when_a_is_FOO", "values": {"a": "FOO"}}, "expected_output": "valid=true\na=FOO\nb=\n"},
    {"input": {"rule_set": "default_FOO", "values": {}}, "expected_output": "valid=true\na=FOO\n"},
    {"input": {"rule_set": "default_FOO", "values": {"a": "xxx"}}, "expected_output": "valid=true\na=xxx\n"},
    {"input": {"rule_set": "depends_on_exactly_one_of_a_or_b_and_c", "values": {}}, "expected_output": "valid=true\na=\nb=\nc=\nd=\n"},
    {"input": {"rule_set": "depends_on_exactly_one_of_a_or_b_and_c", "values": {"d": "ddd"}}, "expected_output": "valid=false\nerror=dependency_not_satisfied\n"},
    {"input": {"rule_set": "depends_on_exactly_one_of_a_or_b_and_c", "values": {"d": "ddd", "c": "ccc"}}, "expected_output": "valid=false\nerror=dependency_not_satisfied\n"},
    {"input": {"rule_set": "depends_on_exactly_one_of_a_or_b_and_c", "values": {"d": "ddd", "c": "ccc", "b": "bbb", "a": "aaa"}}, "expected_output": "valid=false\nerror=dependency_not_satisfied\n"},
    {"input": {"rule_set": "depends_on_exactly_one_of_a_or_b_and_c", "values": {"d": "ddd", "c": "ccc", "a": "aaa"}}, "expected_output": "valid=true\na=aaa\nb=\nc=ccc\nd=ddd\n"},
    {"input": {"rule_set": "depends_on_exactly_one_of_a_or_b_and_c", "values": {"d": "ddd", "c": "ccc", "b": "bbb"}}, "expected_output": "valid=true\na=\nb=bbb\nc=ccc\nd=ddd\n"},
    {"input": {"rule_set": "precludes_a_or_b_when_c_present", "values": {"c": "ccc", "a": "aaa"}}, "expected_output": "valid=false\nerror=precluded_value_present\n"},
    {"input": {"rule_set": "precludes_a_or_b_when_c_present", "values": {"c": "ccc", "b": "bbb"}}, "expected_output": "valid=false\nerror=precluded_value_present\n"},
    {"input": {"rule_set": "precludes_a_or_b_when_c_present", "values": {"c": "ccc", "a": "aaa", "b": "bbb"}}, "expected_output": "valid=false\nerror=precluded_value_present\n"},
    {"input": {"rule_set": "precludes_a_or_b_when_c_present", "values": {"c": "ccc"}}, "expected_output": "valid=true\na=\nb=\nc=ccc\n"},
    {"input": {"rule_set": "boolean_text_pattern", "values": {"a": "xxx"}}, "expected_output": "valid=false\nerror=pattern_mismatch\n"},
    {"input": {"rule_set": "boolean_text_pattern", "values": {"a": "false"}}, "expected_output": "valid=true\na=false\n"}
  ]
}
```

---

### Feature 5: Shared Filesystem Volume Source Construction

**As a developer**, I want to build a persistent-volume source from a shared filesystem export location, so I can mount provisioned shares through a storage interface with the correct monitor and root path attributes.

**Expected Behavior / Usage:**

The input contains an `export_location` whose last colon separates the address/monitor portion from the root path, plus a volume handle, share ID, driver name, mounter, and staging secret reference. The output identifies a CSI-style source, echoes the driver and volume handle, prints deterministic attributes for monitors, mounter, provisioning flag, and root path, and prints the staging secret name and namespace. Invalid export-location strings must be reported with a normalized `invalid_export_location` error.

**Test Cases:** `rcb_tests/public_test_cases/feature5_shared_filesystem_volume_source.json`

```json
{
  "description": "Build a CSI persistent-volume source from a shared filesystem export location by splitting monitor addresses from the root path and carrying driver, mounter, volume handle, and staging secret fields into the output.",
  "cases": [
    {
      "input": {"export_location": "192.168.2.1:6789,192.168.2.2:6789:/shares/011d21e2-fbc3-4e4a-9993-9ea223f73264", "volume_handle": "pvc-011d21e2-fbc3-4e4a-9993-9ea223f73264", "share_id": "011d21e2-fbc3-4e4a-9993-9ea223f73264", "driver": "csi-cephfs", "mounter": "fuse", "os_secret_namespace": "default", "share_secret_namespace": "default", "secret_name": "manila-011d21e2-fbc3-4e4a-9993-9ea223f73264", "secret_namespace": "default"},
      "expected_output": "[internal configuration constants for CSI attributes]\ndriver=csi-cephfs\nvolume_handle=pvc-011d21e2-fbc3-4e4a-9993-9ea223f73264\n[internal configuration constants for CSI attributes]192.168.2.1:6789,192.168.2.2:6789\n[internal configuration constants for CSI attributes]fuse\n[internal configuration constants for CSI attributes]\n[internal configuration constants for CSI attributes]/shares/011d21e2-fbc3-4e4a-9993-9ea223f73264\n[internal configuration constants for CSI attributes]manila-011d21e2-fbc3-4e4a-9993-9ea223f73264\n[internal configuration constants for CSI attributes]default\n"
    },
    {
      "input": {"export_location": "addr1:port1,addr2:port2:/some-path", "volume_handle": "pvc-test", "share_id": "share-test", "driver": "csi-cephfs", "mounter": "fuse", "os_secret_namespace": "default", "share_secret_namespace": "default", "secret_name": "manila-test", "secret_namespace": "default"},
      "expected_output": "[internal configuration constants for CSI attributes]\ndriver=csi-cephfs\nvolume_handle=pvc-test\n[internal configuration constants for CSI attributes]addr1:port1,addr2:port2\n[internal configuration constants for CSI attributes]fuse\n[internal configuration constants for CSI attributes]\n[internal configuration constants for CSI attributes]/some-path\n[internal configuration constants for CSI attributes]manila-test\n[internal configuration constants for CSI attributes]default\n"
    }
  ]
}
```

---

### Feature 6: Shared Filesystem Access Granting

**As a developer**, I want to grant access to a shared filesystem through an HTTP API and read back the resulting access rule, so I can verify both the API interaction and the credential data used for mounting.

**Expected Behavior / Usage:**

The input supplies a share ID, share name, secret reference data, and an `access_service` object with HTTP JSON responses for the grant and list operations. The system must issue POST requests to `/shares/{share_id}/action`, first requesting a read-write `cephx` access grant for the share name and then listing access rules. The output must include framework-observable HTTP signals: request count, request method, routed URL path, and request bodies. It must then print the resulting access rule ID, share ID, access type, access target, access level, state, and access key. API failures are rendered as `error=share_access_failed`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_shared_filesystem_access_grant.json`

```json
{
  "description": "Grant shared filesystem access through the configured HTTP API action endpoint, then read the resulting access rule and expose both HTTP request signals and returned access credentials.",
  "cases": [
    {
      "input": {"share_id": "011d21e2-fbc3-4e4a-9993-9ea223f73264", "share_name": "pvc-011d21e2-fbc3-4e4a-9993-9ea223f73264", "secret_name": "manila-xxx", "secret_namespace": "default", "os_secret_namespace": "default", "share_secret_namespace": "default", "access_service": {"grant_response": "{\"access\":{\"share_id\":\"011d21e2-fbc3-4e4a-9993-9ea223f73264\",\"access_type\":\"ip\",\"access_to\":\"0.0.0.0/0\",\"access_key\":\"\",\"access_level\":\"rw\",\"state\":\"new\",\"id\":\"a2f226a5-cee8-430b-8a03-78a59bd84ee8\"}}", "list_response": "{\"access_list\":[{\"share_id\":\"011d21e2-fbc3-4e4a-9993-9ea223f73264\",\"access_type\":\"cephx\",\"access_to\":\"pvc-011d21e2-fbc3-4e4a-9993-9ea223f73264\",\"access_key\":\"MDExZDIxZTItZmJjMy00ZTRhLTk5OTMt\",\"access_level\":\"rw\",\"state\":\"available\",\"id\":\"a2f226a5-cee8-430b-8a03-78a59bd84ee8\"}]}"}},
      "expected_output": "http_requests=2\nrequest.0=POST /shares/011d21e2-fbc3-4e4a-9993-9ea223f73264/action {\"allow_access\":{\"access_level\":\"rw\",\"access_to\":\"pvc-011d21e2-fbc3-4e4a-9993-9ea223f73264\",\"access_type\":\"cephx\"}}\nrequest.1=POST /shares/011d21e2-fbc3-4e4a-9993-9ea223f73264/action {\"access_list\":null}\naccess_id=a2f226a5-cee8-430b-8a03-78a59bd84ee8\nshare_id=011d21e2-fbc3-4e4a-9993-9ea223f73264\naccess_type=cephx\naccess_to=pvc-011d21e2-fbc3-4e4a-9993-9ea223f73264\naccess_level=rw\nstate=available\naccess_key=MDExZDIxZTItZmJjMy00ZTRhLTk5OTMt\n"
    }
  ]
}
```

---

### Feature 7: User-Agent Flag Parsing

**As a developer**, I want to parse repeated user-agent command-line flags, so I can pass ordered user-agent fragments into downstream cloud API clients.

**Expected Behavior / Usage:**

The input is an object containing `user_agent_flags`, an array of command-line arguments. The system accepts zero or more `--user-agent=value` arguments, preserves argument order, preserves spaces inside one flag value, ignores a trailing non-flag positional value after a completed flag, and joins parsed values with commas. A missing value for `--user-agent` is reported as the normalized `invalid_flags` error.

**Test Cases:** `rcb_tests/public_test_cases/feature7_user_agent_flags.json`

```json
{
  "description": "Parse repeated user-agent command-line flags into ordered user-agent values, preserving spaces inside a flag value and reporting a normalized flag error when a value is missing.",
  "cases": [
    {"input": {"user_agent_flags": []}, "expected_output": "user_agents=\n"},
    {"input": {"user_agent_flags": ["--user-agent=cluster/abc-123"]}, "expected_output": "user_agents=cluster/abc-123\n"},
    {"input": {"user_agent_flags": ["--user-agent=a/b", "--user-agent=c/d"]}, "expected_output": "user_agents=a/b,c/d\n"},
    {"input": {"user_agent_flags": ["--user-agent=a b"]}, "expected_output": "user_agents=a b\n"},
    {"input": {"user_agent_flags": ["--user-agent=a", "b"]}, "expected_output": "user_agents=a\n"},
    {"input": {"user_agent_flags": ["--user-agent"]}, "expected_output": "[a specific sentinel value — ask the PM for the exact string]\n"}
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_endpoint_parsing.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_endpoint_parsing@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same ordering convention as the headers module in the CSI implementation
- use the stable key order defined in the options config struct
