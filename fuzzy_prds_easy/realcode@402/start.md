## Product Requirement Document

# Artifact Repository Service - Repository Storage, Access, and Metadata Contracts

## Project Goal

Build an artifact repository service that allows developers to publish, browse, authenticate, mirror, and resolve build artifacts without manually managing repository files, metadata, access-token state, and proxy rules.

---

## Background & Problem

Without this library[a specific separator character — requires code inspection to confirm]tool, developers are forced to hand-create repository directory layouts, maintain version metadata, validate paths, protect private artifacts, configure mirrored upstream access, and generate descriptor files manually. This leads to repetitive operational code, inconsistent repository listings, unsafe path handling, and authorization bugs.

With this library[a specific separator character — requires code inspection to confirm]tool, clients interact with a repository-oriented API that normalizes paths, orders repository entries, manages access tokens, enforces visibility rules, publishes and deletes artifacts, mirrors remote artifacts under policy, and keeps metadata consistent.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities[a specific separator character — requires code inspection to confirm]simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I[a specific separator character — requires code inspection to confirm]O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src[a specific separator character — requires code inspection to confirm]`, `tests[a specific separator character — requires code inspection to confirm]`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input[a specific separator character — requires code inspection to confirm]output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I[a specific separator character — requires code inspection to confirm]O (stdin[a specific separator character — requires code inspection to confirm]stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open[a specific separator character — requires code inspection to confirm]Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces[a specific separator character — requires code inspection to confirm]protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I[a specific separator character — requires code inspection to confirm]O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result[a specific separator character — requires code inspection to confirm]Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: Version Label Ordering

**As a developer**, I want to order mixed textual version labels into repository listing order, so I can show artifact versions consistently.

**Expected Behavior [a specific separator character — requires code inspection to confirm] Usage:**

The input is an array of version label strings. The output is a single `versions=` line containing the same labels in ascending repository order, preserving the original spelling of each label. Non-numeric words sort before numeric versions; snapshot-style suffixes sort before their corresponding release when the original tested ordering requires it.

**Test Cases:** `rcb_tests[a specific separator character — requires code inspection to confirm]public_test_cases[a specific separator character — requires code inspection to confirm]feature1_version_ordering.json`

```json
{
    "description": "Orders mixed version labels from lowest to highest using repository listing rules.",
    "cases": [
        {
            "input": {
                "action": "orderVersionLabels",
                "versions": [
                    "1.2.3-SNAPSHOT",
                    "1.2",
                    "0.5",
                    "1.0",
                    "1.1.5-SNAPSHOT",
                    "word",
                    "1.1.4",
                    "1.1",
                    "1.1.4-SNAPSHOT"
                ]
            },
            "expected_output": "versions=word,0.5,1.0,1.1,1.1.4-SNAPSHOT,1.1.4,1.1.5-SNAPSHOT,1.2,1.2.3-SNAPSHOT
"
        }
    ]
}
```

---

### Feature 2: Repository Path Handling

**As a developer**, I want to normalize repository-relative path fragments and reject unsafe paths, so I can store and read artifacts without path traversal ambiguity.

**Expected Behavior [a specific separator character — requires code inspection to confirm] Usage:**

Repository paths are treated as logical repository locations, not host filesystem paths.

*2.1 Path Joining — The input contains `base` and `child` path fragments*

The input contains `base` and `child` path fragments. The output is `path=<joined path>` using `[a specific separator character — requires code inspection to confirm]` separators, with leading, trailing, duplicate, and backslash separators normalized away while preserving non-ASCII path names.

**Test Cases:** `rcb_tests[a specific separator character — requires code inspection to confirm]public_test_cases[a specific separator character — requires code inspection to confirm]feature2_1_path_joining.json`

```json
{
    "description": "Joins two repository path fragments while normalizing repeated separators and preserving non-ASCII names.",
    "cases": [
        {
            "input": {
                "action": "joinRepositoryPath",
                "base": "group",
                "child": "artifact"
            },
            "expected_output": "path=group[a specific separator character — requires code inspection to confirm]artifact
"
        }
    ]
}
```

---

*2.2 Path Validation — The input contains one repository path*

The input contains one repository path. If it can be represented safely below the repository root, the output is `storage_path=<path>`. If the path attempts parent traversal or an absolute drive path, the output is a normalized error with `error=invalid_path` and the raw path.

**Test Cases:** `rcb_tests[a specific separator character — requires code inspection to confirm]public_test_cases[a specific separator character — requires code inspection to confirm]feature2_2_path_validation.json`

```json
{
    "description": "Rejects repository paths that would escape the repository root or encode an absolute drive path.",
    "cases": [
        {
            "input": {
                "action": "validateRepositoryPath",
                "path": "..[a specific separator character — requires code inspection to confirm]artifact"
            },
            "expected_output": "error=invalid_path
path=..[a specific separator character — requires code inspection to confirm]artifact
"
        }
    ]
}
```

---

### Feature 3: Directory Entry Ordering

**As a developer**, I want to sort repository directory entries for display, so I can present browsable repositories predictably.

**Expected Behavior [a specific separator character — requires code inspection to confirm] Usage:**

The input is a list of entries with a display name and a boolean indicating whether each entry is a directory. The output emits one `entry=<kind>:<name>` line per entry. Directories appear before files, and each group uses version-aware ordering.

**Test Cases:** `rcb_tests[a specific separator character — requires code inspection to confirm]public_test_cases[a specific separator character — requires code inspection to confirm]feature3_directory_entry_ordering.json`

```json
{
    "description": "Orders directory entries before files and applies version-aware ordering within each group.",
    "cases": [
        {
            "input": {
                "action": "orderDirectoryEntries",
                "entries": [
                    {
                        "name": "Apposite",
                        "directory": false
                    },
                    {
                        "name": "Lolita",
                        "directory": false
                    },
                    {
                        "name": "AlphaTool",
                        "directory": true
                    },
                    {
                        "name": "Zeolite",
                        "directory": true
                    },
                    {
                        "name": "1.0.3",
                        "directory": false
                    },
                    {
                        "name": "1.0.2",
                        "directory": false
                    },
                    {
                        "name": "1.0.2",
                        "directory": true
                    },
                    {
                        "name": "1.0.1",
                        "directory": true
                    }
                ]
            },
            "expected_output": "entry=directory:AlphaTool
entry=directory:Zeolite
entry=directory:1.0.1
entry=directory:1.0.2
entry=file:Apposite
entry=file:Lolita
entry=file:1.0.2
entry=file:1.0.3
"
        }
    ]
}
```

---

### Feature 4: Network Proxy Definition Parsing

**As a developer**, I want to parse a textual proxy definition, so I can connect to upstream resources through configured proxies.

**Expected Behavior [a specific separator character — requires code inspection to confirm] Usage:**

The input is a proxy definition string containing a proxy type and host:port, optionally followed by credentials. The output contains the normalized proxy type, host, and port as separate lines.

**Test Cases:** `rcb_tests[a specific separator character — requires code inspection to confirm]public_test_cases[a specific separator character — requires code inspection to confirm]feature4_proxy_parsing.json`

```json
{
    "description": "Parses textual proxy definitions into network proxy type, host, and port fields.",
    "cases": [
        {
            "input": {
                "action": "parseNetworkProxy",
                "definition": "http [a specific default host to expect — see proxy module defaults]:[a specific default port to expect — see security config]"
            },
            "expected_output": "type=HTTP
host=[a specific default host to expect — see proxy module defaults]
port=[a specific default port to expect — see security config]
"
        }
    ]
}
```

---

### Feature 5: Placeholder Stream Processing

**As a developer**, I want to replace configured byte-stream placeholders, so I can serve generated static content without pre-rendering every file.

**Expected Behavior [a specific separator character — requires code inspection to confirm] Usage:**

Content is processed as a stream and placeholder definitions are applied without requiring the caller to know internal buffering details.

*5.1 Placeholder Replacement — The input contains content and a map of placeholder tokens to replacement text*

The input contains content and a map of placeholder tokens to replacement text. The output is `content=<processed text>` where each configured token has been replaced.

**Test Cases:** `rcb_tests[a specific separator character — requires code inspection to confirm]public_test_cases[a specific separator character — requires code inspection to confirm]feature5_placeholder_replacement.json`

```json
{
    "description": "Streams byte content and replaces configured placeholder tokens with their configured values.",
    "cases": [
        {
            "input": {
                "action": "replacePlaceholders",
                "content": "{{PLACEHOLDER}}",
                "replacements": {
                    "{{PLACEHOLDER}}": "AlphaTool"
                }
            },
            "expected_output": "content=AlphaTool
"
        }
    ]
}
```

---

*5.2 Placeholder Symbol Validation — The input contains content and replacement definitions*

The input contains content and replacement definitions. If a placeholder token contains a multi-byte symbol, the output is a language-neutral error line `error=unsupported_placeholder_symbol`.

**Test Cases:** `rcb_tests[a specific separator character — requires code inspection to confirm]public_test_cases[a specific separator character — requires code inspection to confirm]feature5_2_placeholder_symbol_validation.json`

```json
{
    "description": "Reports a normalized error when a placeholder token contains a multi-byte symbol.",
    "cases": [
        {
            "input": {
                "action": "replacePlaceholders",
                "content": "🎃",
                "replacements": {
                    "🎃": "AlphaTool"
                }
            },
            "expected_output": "error=unsupported_placeholder_symbol
"
        }
    ]
}
```

---

### Feature 6: Configuration File Generation

**As a developer**, I want to generate default configuration files for a requested scope, so I can bootstrap a working directory without hand-writing defaults.

**Expected Behavior [a specific separator character — requires code inspection to confirm] Usage:**

The input specifies a configuration scope. The output reports whether the expected file exists and whether it contains a distinguishing required section or title for that scope.

**Test Cases:** `rcb_tests[a specific separator character — requires code inspection to confirm]public_test_cases[a specific separator character — requires code inspection to confirm]feature6_configuration_generation.json`

```json
{
    "description": "Generates default configuration files for the requested configuration scope in an empty working directory.",
    "cases": [
        {
            "input": {
                "action": "createConfiguration",
                "mode": "local"
            },
            "expected_output": "exists=true
contains_title=true
"
        }
    ]
}
```

---

### Feature 7: Access Token Lifecycle

**As a developer**, I want to manage named access tokens, so I can authenticate and authorize repository operations.

**Expected Behavior [a specific separator character — requires code inspection to confirm] Usage:**

The input selects a token-management scenario with the names or secrets needed for that scenario. The output exposes stable token state: token name, initialized identifier information, creation-date freshness, stored name after update, and whether old or new secrets match after regeneration.

**Test Cases:** `rcb_tests[a specific separator character — requires code inspection to confirm]public_test_cases[a specific separator character — requires code inspection to confirm]feature7_access_token_lifecycle.json`

```json
{
    "description": "Creates, updates, deletes, finds, and regenerates access tokens while exposing stable token state.",
    "cases": [
        {
            "input": {
                "action": "manageAccessToken",
                "scenario": "create",
                "name": "alphatool"
            },
            "expected_output": "name=alphatool
id_type=TEMPORARY
id_value=1
created_today=true
"
        },
        {
            "input": {
                "action": "manageAccessToken",
                "scenario": "update",
                "initial_name": "betatool",
                "updated_name": "alphatool"
            },
            "expected_output": "stored_name=alphatool
old_present=false
"
        }
    ]
}
```

---

### Feature 8: Credential Authentication

**As a developer**, I want to authenticate supplied credentials against stored access-token secrets, so I can distinguish valid clients from invalid ones.

**Expected Behavior [a specific separator character — requires code inspection to confirm] Usage:**

The input contains a token name, the secret stored for that token, and the secret presented by the client. On success, the output identifies the authenticated token. On failure, the output reports `authenticated=false` plus HTTP status and domain message.

**Test Cases:** `rcb_tests[a specific separator character — requires code inspection to confirm]public_test_cases[a specific separator character — requires code inspection to confirm]feature8_credential_authentication.json`

```json
{
    "description": "Authenticates credentials against stored access-token secrets and reports either token identity or an HTTP authentication error.",
    "cases": [
        {
            "input": {
                "action": "authenticateCredentials",
                "name": "name",
                "stored_secret": "secret",
                "provided_secret": "secret"
            },
            "expected_output": "authenticated=true
name=name
id_value=1
"
        }
    ]
}
```

---

### Feature 9: Repository Read Access

**As a developer**, I want to enforce repository visibility and read permissions, so I can expose only the artifact data a client is allowed to see.

**Expected Behavior [a specific separator character — requires code inspection to confirm] Usage:**

Repository browsing and artifact lookup must include HTTP-style observable signals so callers can distinguish successful framework-mediated access from authorization failures.

*9.1 Visible Repository Listing — The input indicates whether the client has private-repository authorization*

The input indicates whether the client has private-repository authorization. The output emits one `repository=<name>` line per visible repository in listing order.

**Test Cases:** `rcb_tests[a specific separator character — requires code inspection to confirm]public_test_cases[a specific separator character — requires code inspection to confirm]feature9_1_repository_visibility_listing.json`

```json
{
    "description": "Lists repositories visible to an anonymous or repository-authorized client.",
    "cases": [
        {
            "input": {
                "action": "listVisibleRepositories",
                "authorized_private": false
            },
            "expected_output": "repository=PUBLIC
repository=PROXIED
"
        }
    ]
}
```

---

*9.2 Artifact Entry Access — The input identifies a repository, artifact path, file content to pre-store for the scenario, and whether the client is authorized*

The input identifies a repository, artifact path, file content to pre-store for the scenario, and whether the client is authorized. Successful output contains `status=found`, the artifact file name, and entry type. Unauthorized output contains `status=error`, HTTP status, and message.

**Test Cases:** `rcb_tests[a specific separator character — requires code inspection to confirm]public_test_cases[a specific separator character — requires code inspection to confirm]feature9_2_artifact_entry_access.json`

```json
{
    "description": "Returns file details from public or authorized repositories and returns a normalized HTTP error for unauthorized private access.",
    "cases": [
        {
            "input": {
                "action": "requestArtifactEntry",
                "repository": "PUBLIC",
                "path": "[a specific separator character — requires code inspection to confirm]gav[a specific separator character — requires code inspection to confirm]file.pom",
                "content": "content",
                "authorized": false
            },
            "expected_output": "status=found
name=file.pom
type=FILE
"
        },
        {
            "input": {
                "action": "requestArtifactEntry",
                "repository": "HIDDEN",
                "path": "[a specific separator character — requires code inspection to confirm]gav[a specific separator character — requires code inspection to confirm]file.pom",
                "content": "content",
                "authorized": false
            },
            "expected_output": "status=found
name=file.pom
type=FILE
"
        }
    ]
}
```

---

*9.3 Directory Index Access — The input identifies a restricted repository for a directory-listing request*

The input identifies a restricted repository for a directory-listing request. The output is an HTTP-style error signal with status and message, rather than a directory listing.

**Test Cases:** `rcb_tests[a specific separator character — requires code inspection to confirm]public_test_cases[a specific separator character — requires code inspection to confirm]feature9_3_directory_index_access.json`

```json
{
    "description": "Rejects anonymous directory listing for hidden or private repositories with an HTTP error signal.",
    "cases": [
        {
            "input": {
                "action": "requestDirectoryListing",
                "repository": "HIDDEN"
            },
            "expected_output": "status=error
http_status=401
message=You need to provide credentials.
"
        }
    ]
}
```

---

### Feature 10: Repository Write Operations

**As a developer**, I want to store and remove artifact files through authorization checks, so I can publish and clean repository content safely.

**Expected Behavior [a specific separator character — requires code inspection to confirm] Usage:**

Write operations must report operation success and repository-visible file details or authorization outcomes.

*10.1 Artifact Deployment — The input contains a repository name, target artifact path, file content, and uploader identity*

The input contains a repository name, target artifact path, file content, and uploader identity. The output reports successful deployment and the discoverable file name and type at that path.

**Test Cases:** `rcb_tests[a specific separator character — requires code inspection to confirm]public_test_cases[a specific separator character — requires code inspection to confirm]feature10_1_artifact_deploy.json`

```json
{
    "description": "Stores an uploaded artifact file under the requested repository path and makes the stored entry discoverable.",
    "cases": [
        {
            "input": {
                "action": "storeArtifactFile",
                "repository": "PUBLIC",
                "path": "[a specific separator character — requires code inspection to confirm]com[a specific separator character — requires code inspection to confirm]example[a specific separator character — requires code inspection to confirm]tool[a specific separator character — requires code inspection to confirm]3.0.0[a specific separator character — requires code inspection to confirm]tool-3.0.0.jar",
                "content": "content",
                "deployed_by": "client@[a specific default host to expect — see proxy module defaults]"
            },
            "expected_output": "deploy_ok=true
name=tool-3.0.0.jar
type=FILE
"
        }
    ]
}
```

---

*10.2 Artifact Deletion — The input identifies a stored artifact*

The input identifies a stored artifact. The output reports that deletion with mismatched write credentials fails and deletion with matching write credentials succeeds.

**Test Cases:** `rcb_tests[a specific separator character — requires code inspection to confirm]public_test_cases[a specific separator character — requires code inspection to confirm]feature10_2_artifact_delete.json`

```json
{
    "description": "Requires matching write authorization to remove a stored artifact file.",
    "cases": [
        {
            "input": {
                "action": "removeArtifactFile",
                "repository": "PUBLIC",
                "path": "[a specific separator character — requires code inspection to confirm]gav[a specific separator character — requires code inspection to confirm]file.pom"
            },
            "expected_output": "invalid_delete=error
valid_delete=ok
"
        }
    ]
}
```

---

### Feature 11: Mirrored Artifact Lookup

**As a developer**, I want to fetch artifacts from configured remote repositories subject to allow rules, so I can serve proxied dependencies while enforcing mirror policy.

**Expected Behavior [a specific separator character — requires code inspection to confirm] Usage:**

The input is a repository-relative artifact path requested through a mirrored repository. If the path is available and allowed, the output reports found status, file name, and fetched content. If mirror policy or remote lookup rejects it, the output reports an HTTP-style error.

**Test Cases:** `rcb_tests[a specific separator character — requires code inspection to confirm]public_test_cases[a specific separator character — requires code inspection to confirm]feature11_mirror_lookup.json`

```json
{
    "description": "Fetches allowed artifacts from configured remote repositories and rejects mirrored paths outside the allow rules.",
    "cases": [
        {
            "input": {
                "action": "requestMirroredArtifact",
                "path": "[a specific separator character — requires code inspection to confirm]gav[a specific separator character — requires code inspection to confirm]file.pom"
            },
            "expected_output": "status=found
name=file.pom
content=content
"
        }
    ]
}
```

---

### Feature 12: Artifact Metadata Management

**As a developer**, I want to read and update artifact metadata, so I can resolve versions and advertise generated descriptors.

**Expected Behavior [a specific separator character — requires code inspection to confirm] Usage:**

Metadata behavior is observable through version query outputs and through generated descriptor and metadata fields.

*12.1 Metadata Version Lookup — The input contains an artifact path, metadata versions, a prefix filter, and lookup mode*

The input contains an artifact path, metadata versions, a prefix filter, and lookup mode. Latest mode outputs `latest=<version>`; all mode outputs `versions=<comma-separated matching versions>` in metadata order.

**Test Cases:** `rcb_tests[a specific separator character — requires code inspection to confirm]public_test_cases[a specific separator character — requires code inspection to confirm]feature12_1_metadata_lookup.json`

```json
{
    "description": "Reads artifact metadata and returns either the latest matching version or all versions matching a prefix.",
    "cases": [
        {
            "input": {
                "action": "requestArtifactVersions",
                "mode": "latest",
                "artifact": "[a specific separator character — requires code inspection to confirm]gav",
                "versions": [
                    "2.0.1",
                    "1.0.1",
                    "1.0.2",
                    "1.0.0",
                    "2.0.0",
                    "1.1.0"
                ],
                "filter": "1.0."
            },
            "expected_output": "latest=1.0.2
"
        }
    ]
}
```

---

*12.2 Descriptor Generation — The input contains an artifact path, existing versions, group identifier, artifact identifier, and new version*

The input contains an artifact path, existing versions, group identifier, artifact identifier, and new version. The output reports whether the descriptor was generated and whether the descriptor and metadata contain the expected group, artifact, version, release, latest, previous-version, new-version, and update timestamp signals.

**Test Cases:** `rcb_tests[a specific separator character — requires code inspection to confirm]public_test_cases[a specific separator character — requires code inspection to confirm]feature12_2_descriptor_generation.json`

```json
{
    "description": "Generates a descriptor document for a new version and updates artifact metadata to advertise the new version.",
    "cases": [
        {
            "input": {
                "action": "createDescriptor",
                "artifact_path": "[a specific separator character — requires code inspection to confirm]com[a specific separator character — requires code inspection to confirm]example[a specific separator character — requires code inspection to confirm]tool",
                "existing_versions": [
                    "3.0.0"
                ],
                "group_id": "com.example",
                "artifact_id": "tool",
                "new_version": "3.0.1"
            },
            "expected_output": "generated=true
pom_group=true
pom_artifact=true
pom_version=true
metadata_release=true
metadata_latest=true
metadata_has_previous=true
metadata_has_new=true
metadata_updated_prefix=true
"
        }
    ]
}
```

---

### Feature 13: Download Filtering

**As a developer**, I want to apply a file-resolution filter to downloaded content, so I can customize served artifact bytes through extension hooks.

**Expected Behavior [a specific separator character — requires code inspection to confirm] Usage:**

The input contains a stored file path, original content, a placeholder, and its replacement. The output reports transformed content and the updated byte length visible to the downloader.

**Test Cases:** `rcb_tests[a specific separator character — requires code inspection to confirm]public_test_cases[a specific separator character — requires code inspection to confirm]feature13_download_filtering.json`

```json
{
    "description": "Allows a registered file-resolution filter to transform downloaded content and update the reported content length.",
    "cases": [
        {
            "input": {
                "action": "applyDownloadFilter",
                "path": "[a specific separator character — requires code inspection to confirm]g[a specific separator character — requires code inspection to confirm]a[a specific separator character — requires code inspection to confirm]v[a specific separator character — requires code inspection to confirm]app.jar",
                "content": "{placeholder}",
                "placeholder": "{placeholder}",
                "replacement": "content"
            },
            "expected_output": "content=content
content_length=7
"
        }
    ]
}
```

---

### Feature 14: Snapshot Build Pruning

**As a developer**, I want to remove deprecated snapshot build artifacts after a newer snapshot deploy, so I can keep snapshot repositories from accumulating obsolete builds.

**Expected Behavior [a specific separator character — requires code inspection to confirm] Usage:**

The input describes a snapshot artifact, existing old builds, and the newly deployed snapshot timestamp. The output lists remaining files; obsolete build artifacts are absent and metadata checksum files remain.

**Test Cases:** `rcb_tests[a specific separator character — requires code inspection to confirm]public_test_cases[a specific separator character — requires code inspection to confirm]feature14_snapshot_pruning.json`

```json
{
    "description": "After a new snapshot deployment, removes deprecated snapshot build artifacts and leaves only metadata checksum files.",
    "cases": [
        {
            "input": {
                "action": "pruneSnapshotBuilds",
                "artifact_id": "artifact",
                "version_path": "group[a specific separator character — requires code inspection to confirm]artifact[a specific separator character — requires code inspection to confirm]1.0.0-R0.1-SNAPSHOT",
                "base_version": "1.0.0-R0.1",
                "old_builds": [
                    "20220101.213700-1",
                    "20220101.213701-2"
                ],
                "new_timestamp": "20220101.213702"
            },
            "expected_output": "remaining=group[a specific separator character — requires code inspection to confirm]artifact[a specific separator character — requires code inspection to confirm]1.0.0-R0.1-SNAPSHOT[a specific separator character — requires code inspection to confirm]maven-metadata.xml
remaining=group[a specific separator character — requires code inspection to confirm]artifact[a specific separator character — requires code inspection to confirm]1.0.0-R0.1-SNAPSHOT[a specific separator character — requires code inspection to confirm]maven-metadata.xml.md5
remaining=group[a specific separator character — requires code inspection to confirm]artifact[a specific separator character — requires code inspection to confirm]1.0.0-R0.1-SNAPSHOT[a specific separator character — requires code inspection to confirm]maven-metadata.xml.sha1
remaining=group[a specific separator character — requires code inspection to confirm]artifact[a specific separator character — requires code inspection to confirm]1.0.0-R0.1-SNAPSHOT[a specific separator character — requires code inspection to confirm]maven-metadata.xml.sha256
remaining=group[a specific separator character — requires code inspection to confirm]artifact[a specific separator character — requires code inspection to confirm]1.0.0-R0.1-SNAPSHOT[a specific separator character — requires code inspection to confirm]maven-metadata.xml.sha512
"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution[a specific separator character — requires code inspection to confirm]Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests[a specific separator character — requires code inspection to confirm]public_test_cases[a specific separator character — requires code inspection to confirm]`. A single entry point `bash rcb_tests[a specific separator character — requires code inspection to confirm]test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests[a specific separator character — requires code inspection to confirm]stdout[a specific separator character — requires code inspection to confirm]<cases-dir>[a specific separator character — requires code inspection to confirm]{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_version_ordering.json` run with `--cases-dir public_test_cases` → `rcb_tests[a specific separator character — requires code inspection to confirm]stdout[a specific separator character — requires code inspection to confirm]public_test_cases[a specific separator character — requires code inspection to confirm]feature1_version_ordering@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS[a specific separator character — requires code inspection to confirm]FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- version sort logic that mirrors the repository path resolver's prefix handling
- relicensing strategy consistent with the main catalog dump
