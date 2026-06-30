## Product Requirement Document

# File Synchronization Engine - Note Vault to Remote Repository Synchronization

## Project Goal

Build a file synchronization library and execution adapter that allows developers to synchronize a note workspace with a remote repository while preserving Unicode content, binary files, conflict safety, and actionable error reporting without forcing users to resolve low-level API or filesystem details manually.

---

## Background & Problem

Without this library, developers are forced to hand-code path normalization, base64 conversion, file hashing, local/remote state comparison, conflict detection, protected-path handling, retry behavior, and user-facing error translation. This leads to repetitive code, accidental overwrites, corrupted binary content, Unicode path mismatches, stale cache bugs, and confusing technical errors.

With this library, a caller can provide workspace and remote snapshots, run synchronization through a small adapter, and receive deterministic stdout describing what was encoded, detected, written, skipped, synchronized, or reported as an error.

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

## Core Features

### Feature 1: UTF-8 Base64 Text Encoding

**As a developer**, I want to convert plain UTF-8 text to base64 and decode it back, so I can store and transfer text content without losing Unicode characters.

**Expected Behavior / Usage:**

Input is an object selecting text encoding or decoding. Encoding prints a single `base64=` line. Decoding prints a single `text=` line. Invalid encoded input is normalized to `error=invalid_encoded_content` without exposing runtime exception names.

**Test Cases:** `rcb_tests/public_test_cases/feature1_text_base64.json`

```json
{
  "description": "UTF-8 text is converted to and from base64 without losing ASCII, multi-byte, emoji, accented, or empty content.",
  "cases": [
    {
      "description": "ASCII text is encoded as UTF-8 bytes and rendered as base64.",
      "input": {
        "command": "content.encode",
        "text": "Hello, World!"
      },
      "expected_output": "base64=SGVsbG8sIFdvcmxkIQ==\n"
    }
  ]
}
```

---

### Feature 2: Runtime File Content Representation

**As a developer**, I want to carry file content with an explicit representation tag, so I can safely convert between user-readable text and transport-safe base64.

**Expected Behavior / Usage:**

Input supplies content with `encoding` set to `plaintext` or `base64`. Output prints the retained encoding, plaintext rendering, canonical base64 rendering, and byte-size metadata. Base64 input may contain whitespace and must be normalized before rendering.

**Test Cases:** `rcb_tests/public_test_cases/feature2_file_content_representation.json`

```json
{
  "description": "File content keeps an explicit text-or-base64 representation while allowing callers to request either plaintext or base64 form.",
  "cases": [
    {
      "description": "Plain Unicode file content can be rendered as plaintext, base64, and byte-size metadata.",
      "input": {
        "command": "content.file",
        "encoding": "plaintext",
        "content": "你好, World! ✨ €50"
      },
      "expected_output": "encoding=plaintext\nplain=你好, World! ✨ €50\nbase64=5L2g5aW9LCBXb3JsZCEg4pyoIOKCrDUw\nsize=16\n"
    }
  ]
}
```

---

### Feature 3: Workspace Path Analysis

**As a developer**, I want to normalize and inspect workspace paths, so I can make cross-device path comparison stable and explain path properties.

**Expected Behavior / Usage:**

Input is a workspace-relative path string. Output prints the normalized path, basename, final extension or `null`, whether any path segment is hidden, Unicode normalization flags, non-ASCII presence, character length, and UTF-8 byte length. Paths are normalized to composed Unicode form before metadata is produced.

**Test Cases:** `rcb_tests/public_test_cases/feature3_path_analysis.json`

```json
{
  "description": "Workspace file paths are normalized and analyzed for filename, extension, hidden-path status, and Unicode diagnostic metadata.",
  "cases": [
    {
      "description": "A normal ASCII file path reports its basename, extension, visibility, and byte counts.",
      "input": {
        "command": "path.analyze",
        "path": "notes/daily/2024-01-01.md"
      },
      "expected_output": "path=notes/daily/2024-01-01.md\nname=2024-01-01.md\nextension=md\nhidden=false\nis_nfc=true\nis_nfd=true\nhas_non_ascii=false\nchar_length=25\nbyte_length=25\n"
    }
  ]
}
```

---

### Feature 4: File State Change Detection

**As a developer**, I want to compare a current file-state snapshot with a saved baseline, so I can identify which paths need synchronization.

**Expected Behavior / Usage:**

Input contains two path-to-hash maps: `current` and `baseline`. Output contains one line per changed path in deterministic path order using `PATH=ADDED`, `PATH=[the status string for modified keys]`, or `PATH=REMOVED`. Equal snapshots produce empty stdout.

**Test Cases:** `rcb_tests/public_test_cases/feature4_state_change_detection.json`

```json
{
  "description": "Comparing current file hashes against a stored baseline reports added, modified, and removed paths.",
  "cases": [
    {
      "description": "Mixed current and baseline states produce one added, one modified, and one removed change.",
      "input": {
        "command": "state.compare",
        "current": {
          "same.md": "aaa",
          "changed.md": "new",
          "added.md": "sha"
        },
        "baseline": {
          "same.md": "aaa",
          "changed.md": "old",
          "removed.md": "gone"
        }
      },
      "expected_output": "added.md=ADDED\nchanged.md=[the status string for modified keys]\nremoved.md=REMOVED\n"
    }
  ]
}
```

---

### Feature 5: Safe Change Resolution

**As a developer**, I want to categorize local and remote changes before applying them, so I can avoid overwriting protected or unverifiable workspace files.

**Expected Behavior / Usage:**

Input contains local changes, remote changes, locally scanned paths, protected paths, optional filesystem existence results, baseline hashes, and current hashes for untracked paths. Output reports needed filesystem checks, safe local pushes, safe remote pulls, and clashes as JSON arrays. A remote change to a protected path is a `protected` clash; a remote change to an existing untracked path whose current hash differs from baseline is an `untracked` clash.

**Test Cases:** `rcb_tests/public_test_cases/feature5_change_resolution.json`

```json
{
  "description": "Local and remote change lists are separated into safe pushes, safe pulls, and clashes using protected-path and untracked-file checks.",
  "cases": [
    {
      "description": "A local-only update, remote-only update, protected remote update, and both-sides update are categorized separately.",
      "input": {
        "command": "state.resolve",
        "localChanges": [
          {
            "path": "local.md",
            "type": "ADDED"
          },
          {
            "path": "both.md",
            "type": "[the status string for modified keys]"
          }
        ],
        "remoteChanges": [
          {
            "path": "remote.md",
            "type": "ADDED"
          },
          {
            "path": "both.md",
            "type": "[the status string for modified keys]"
          },
          {
            "path": ".obsidian/app.json",
            "type": "ADDED"
          }
        ],
        "localScanPaths": [
          "local.md",
          "both.md"
        ],
        "protectedPaths": [
          ".obsidian/app.json"
        ],
        "filesystemState": [
          {
            "path": "remote.md",
            "exists": false
          }
        ],
        "baselineShas": {}
      },
      "expected_output": "checks=[{\"path\":\"remote.md\",\"remoteOp\":\"ADDED\"}]\nsafe_local=[{\"path\":\"local.md\",\"type\":\"ADDED\"}]\nsafe_remote=[{\"path\":\"remote.md\",\"type\":\"ADDED\"}]\nclashes=[{\"localState\":\"[the status string for modified keys]\",\"path\":\"both.md\",\"remoteOp\":\"[the status string for modified keys]\"},{\"localState\":\"protected\",\"path\":\".obsidian/app.json\",\"remoteOp\":\"ADDED\"}]\n"
    }
  ]
}
```

---

### Feature 6: Local Workspace Scan and Content Read

**As a developer**, I want to scan local files and read file bytes safely, so I can track only supported files while preserving binary content.

**Expected Behavior / Usage:**

Input describes an in-memory workspace. Scanning outputs a stable path-to-hash state for trackable files and excludes hidden path segments. Reading a path outputs whether bytes are represented as plaintext or base64; bytes containing nulls or invalid UTF-8 are returned as base64 rather than corrupted text.

**Test Cases:** `rcb_tests/public_test_cases/feature6_local_scan_and_read.json`

```json
{
  "description": "A local workspace scan computes stable file states for trackable files, ignores hidden paths for state tracking, and detects text versus binary content when reading.",
  "cases": [
    {
      "description": "Scanning text and binary files returns stable hashes while omitting hidden paths from tracked state.",
      "input": {
        "command": "local.scan",
        "files": [
          {
            "path": "note1.md",
            "encoding": "plaintext",
            "content": "Content of note 1"
          },
          {
            "path": "image.png",
            "encoding": "base64",
            "content": "AAAAAAAAAAA="
          },
          {
            "path": ".obsidian/config.json",
            "encoding": "plaintext",
            "content": "secret"
          }
        ]
      },
      "expected_output": "state={\"image.png\":\"fe954d839c04f84471b6dd90c945e55a6035de80\",\"note1.md\":\"b8b1b70958bbc0b6f0305f4bc57a8393ba333130\"}\n"
    }
  ]
}
```

---

### Feature 7: Local Workspace Apply Operations

**As a developer**, I want to apply additions, modifications, deletions, and conflict writes to a local workspace, so I can materialize remote changes without losing local data.

**Expected Behavior / Usage:**

Input provides initial files, writes, deletions, and optional clash paths. Output reports performed changes, newly computed baseline hashes, and final stored file bytes as base64. Clash paths are written under the visible conflict area while baseline hashes may still be associated with the original path when that path is not normally trackable.

**Test Cases:** `rcb_tests/public_test_cases/feature7_local_apply_changes.json`

```json
{
  "description": "Applying local workspace changes writes text and binary files with the correct operation type, supports deletion, and writes clashes under a conflict area while hashing the original path when needed.",
  "cases": [
    {
      "description": "A batch containing a text addition, binary addition, and deletion reports all performed file operations and final stored bytes.",
      "input": {
        "command": "local.apply",
        "initial": [
          {
            "path": "old.md",
            "encoding": "plaintext",
            "content": "old"
          }
        ],
        "writes": [
          {
            "path": "new.md",
            "encoding": "plaintext",
            "content": "Hello"
          },
          {
            "path": "image.png",
            "encoding": "base64",
            "content": "AQIDAA=="
          }
        ],
        "deletes": [
          "old.md"
        ]
      },
      "expected_output": "changes=[{\"path\":\"new.md\",\"type\":\"ADDED\"},{\"path\":\"image.png\",\"type\":\"ADDED\"},{\"path\":\"old.md\",\"type\":\"REMOVED\"}]\nnew_baseline={\"image.png\":\"9e1f9134d8418b3367ac4a9b6741c27b1bbaada9\",\"new.md\":\"f3fbfed40eafab440b506b503df6cd0495b71f4d\"}\nfiles={\"image.png\":\"AQIDAA==\",\"new.md\":\"SGVsbG8=\"}\n"
    }
  ]
}
```

---

### Feature 8: Retry After Synchronization Failure

**As a developer**, I want to keep the saved baseline unchanged when synchronization fails, so I can retry later without losing accumulated local edits.

**Expected Behavior / Usage:**

Input is a sequence of synchronization steps that can mutate local files, remote files, or inject a categorized failure. Output prints each step result, notice-message sequence, operations applied to each side, final local and remote files, and saved state. If a remote failure occurs before state persistence, the later successful run must upload all local changes accumulated since the unchanged baseline.

**Test Cases:** `rcb_tests/public_test_cases/feature8_sync_retry_after_failure.json`

```json
{
  "description": "A failed synchronization leaves cached state and remote files unchanged; the next successful synchronization uploads all accumulated local changes from the unchanged baseline.",
  "cases": [
    {
      "description": "A network failure on the first synchronization does not mark local changes as synced, so a later retry uploads both accumulated files.",
      "input": {
        "command": "sync.run",
        "steps": [
          {
            "localSet": [
              {
                "path": "fileA.md",
                "content": "Content of file A"
              }
            ],
            "remoteFailure": {
              "type": "network",
              "message": "Could not reach remote API"
            },
            "sync": true
          },
          {
            "localSet": [
              {
                "path": "fileB.md",
                "content": "Content of file B"
              }
            ],
            "sync": true
          }
        ]
      },
      "expected_output": "step=0\nnotice=[[\"Checking for changes...\"]]\nsuccess=false\nerror_message=Could not reach remote API. Please check your internet connection.\nstep=1\nnotice=[[\"Checking for changes...\"],[\"Uploading local changes\"],[\"Writing remote changes to local\"],[\"Sync successful\"]]\nsuccess=true\nlocal_ops=[]\nremote_ops=[{\"path\":\"fileA.md\",\"type\":\"ADDED\"},{\"path\":\"fileB.md\",\"type\":\"ADDED\"}]\nclashes=[]\nlocal_files={\"fileA.md\":{\"content\":\"Content of file A\",\"encoding\":\"plaintext\"},\"fileB.md\":{\"content\":\"Content of file B\",\"encoding\":\"plaintext\"}}\nremote_files={\"fileA.md\":{\"content\":\"Content of file A\",\"encoding\":\"plaintext\"},\"fileB.md\":{\"content\":\"Content of file B\",\"encoding\":\"plaintext\"}}\nstore={\"lastFetchedCommitSha\":\"b86a9aba597a30fd17d6e13c4893f32890ebb062\",\"lastFetchedRemoteSha\":{\"fileA.md\":\"b1745ccb0ebf92d8141e3f2969db2760c72523dd\",\"fileB.md\":\"26294f3aff9abaccd5dc7c1954f5aa170eeb4aa6\"},\"localSha\":{\"fileA.md\":\"c6bb8c90633a9971e4c4ca55b445922198e1c57d\",\"fileB.md\":\"acc5b1ab5649b944c2108e0067b5dea0cf8b8b37\"}}\n"
    }
  ]
}
```

---

### Feature 9: Protected and Untracked Remote Conflict Handling

**As a developer**, I want to receive remote updates for unsafe paths without overwriting the workspace, so I can let users inspect conflicts manually.

**Expected Behavior / Usage:**

Input initializes local and remote files and runs synchronization. Remote additions or modifications to protected paths, hidden paths, or locally existing untracked paths must not overwrite the original workspace path. Non-deletion conflicts are written below the conflict area, reported in the `clashes` list with `protected` or `untracked` local state, and synchronization can still succeed.

**Test Cases:** `rcb_tests/public_test_cases/feature9_sync_protected_remote_paths.json`

```json
{
  "description": "Remote updates to protected or locally untracked paths are not written directly over the workspace; non-deletion conflicts are materialized in the conflict area and reported to the caller.",
  "cases": [
    {
      "description": "A remote workspace-configuration file is saved into the conflict area, reported as a protected clash, and retained in remote state.",
      "input": {
        "command": "sync.run",
        "remote_initial": [
          {
            "path": ".obsidian/app.json",
            "content": "remote settings"
          }
        ],
        "steps": [
          {
            "sync": true
          }
        ]
      },
      "expected_output": "step=0\nnotice=[[\"Checking for changes...\"],[\"Uploading local changes\"],[\"Change conflicts detected\"],[\"Synced with remote, unresolved conflicts written to _fit\"]]\nsuccess=true\nlocal_ops=[{\"path\":\"_fit/.obsidian/app.json\",\"type\":\"ADDED\"}]\nremote_ops=[]\nclashes=[{\"localState\":\"protected\",\"path\":\".obsidian/app.json\",\"remoteOp\":\"ADDED\"}]\nlocal_files={\"_fit/.obsidian/app.json\":{\"content\":\"cmVtb3RlIHNldHRpbmdz\",\"encoding\":\"base64\"}}\nremote_files={\".obsidian/app.json\":{\"content\":\"remote settings\",\"encoding\":\"plaintext\"}}\nstore={\"lastFetchedCommitSha\":\"initial-commit\",\"lastFetchedRemoteSha\":{\".obsidian/app.json\":\"db14b5062a2a893cb61947d6c10e76fbcddffd9a\"},\"localSha\":{}}\n"
    }
  ]
}
```

---

### Feature 10: User-Facing Synchronization Errors

**As a developer**, I want to render categorized synchronization failures as actionable messages, so I can show recovery guidance without leaking runtime exception types.

**Expected Behavior / Usage:**

Input injects categorized synchronization failures such as authentication, missing remote resources, network, or filesystem problems. Output prints a failed sync result with the user-facing message generated from the category. Error output must use domain categories and guidance, not host-language exception names.

**Test Cases:** `rcb_tests/public_test_cases/feature10_sync_error_messages.json`

```json
{
  "description": "Synchronization failures are categorized into user-facing messages for authentication, missing remote resources, filesystem problems, and concurrent requests.",
  "cases": [
    {
      "description": "An authentication failure is rendered with credential-recovery guidance.",
      "input": {
        "command": "sync.run",
        "steps": [
          {
            "remoteFailure": {
              "type": "authentication",
              "message": "Bad credentials"
            },
            "sync": true
          }
        ]
      },
      "expected_output": "step=0\nnotice=[[\"Checking for changes...\"]]\nsuccess=false\nerror_message=Bad credentials. Check your GitHub personal access token.\nlocal_files={}\nremote_files={}\nstore={\"lastFetchedCommitSha\":\"commit-initial\",\"lastFetchedRemoteSha\":{},\"localSha\":{}}\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_text_base64.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_text_base64@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- describe the default rebuild strategy
- same prefix pattern as protected files
