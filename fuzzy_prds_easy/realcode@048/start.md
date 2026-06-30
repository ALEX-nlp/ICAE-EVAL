## Product Requirement Document

# Native Extension Build Helper - Build, Package, and Retrieve Prebuilt Native Artifacts

## Project Goal

Build a native-extension build helper that allows developers to compile, package, locate, and retrieve platform-specific native binaries without hand-writing repetitive build, archive, and download plumbing.

---

## Background & Problem

Without this library/tool, developers are forced to manually detect platform naming conventions, invoke external native build tools, copy compiled shared libraries into host-project load paths, create platform-specific archives, and optionally fetch prebuilt binaries from release locations. This leads to repeated boilerplate, inconsistent artifact names, fragile install scripts, and difficult troubleshooting.

With this library/tool, developers describe the project and distribution settings once, and the helper resolves names and paths, invokes or skips build commands appropriately, packages binaries, downloads compatible archives when available, and emits deterministic adapter output for automation.

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

### Feature 1: Diagnostic Log Destination

**As a developer**, I want to see where diagnostic output will be written, so I can enable troubleshooting without changing build logic.

**Expected Behavior / Usage:**

The adapter accepts an object describing whether a debug destination is set. It prints one line, `debug_destination=<path-or-null>`, where `null` means diagnostic logging is disabled and any other value is the configured destination path.

**Test Cases:** `rcb_tests/public_test_cases/feature1_debug_destination.json`

```json
{
    "description": "Reports whether diagnostic logging has a configured destination.",
    "cases": [
        {
            "input": {
                "command": "config",
                "data": {
                    "selector": "debug_destination",
                    "debug_filename_env": "build-debug.log"
                }
            },
            "expected_output": "debug_destination=build-debug.log\n"
        }
    ]
}
```

---

### Feature 2: Native Shared Extension Selection

**As a developer**, I want to derive the correct shared-library extension for the target platform, so I can name compiled native artifacts consistently.

**Expected Behavior / Usage:**

The adapter accepts the host dynamic-extension value and a platform flag. If the host extension is `bundle`, the native shared extension is `dylib`; on Windows platforms it is `dll`; otherwise the host extension is preserved. It prints `shared_extension=<extension>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_shared_extension.json`

```json
{
    "description": "Maps platform dynamic-library conventions to the native shared-library extension used for a build artifact.",
    "cases": [
        {
            "input": {
                "command": "config",
                "data": {
                    "selector": "shared_extension",
                    "dynamic_extension": "bundle",
                    "windows": false
                }
            },
            "expected_output": "shared_extension=dylib\n"
        }
    ]
}
```

---

### Feature 3: Runtime Version Key Formatting

**As a developer**, I want to convert a runtime version into an artifact key, so I can publish binary archives with stable runtime identifiers.

**Expected Behavior / Usage:**

The adapter accepts a dotted runtime version and prints `runtime_key=<key>`. The key is formed from the word `ruby` followed by the major and minor version numbers with dots removed.

**Test Cases:** `rcb_tests/public_test_cases/feature3_runtime_key.json`

```json
{
    "description": "Formats a runtime version into the compact key used in binary artifact names.",
    "cases": [
        {
            "input": {
                "command": "config",
                "data": {
                    "selector": "runtime_key",
                    "runtime_version": "3.2.0"
                }
            },
            "expected_output": "runtime_key=ruby32\n"
        }
    ]
}
```

---

### Feature 4: Library Base Name Resolution

**As a developer**, I want to choose the native library base name from manifest data, so I can avoid duplicating binary naming decisions.

**Expected Behavior / Usage:**

The adapter accepts manifest data that may contain both an explicit library name and a package name. If an explicit library name exists, it is used; otherwise the package name is used. It prints `library_base_name=<name>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_library_base_name.json`

```json
{
    "description": "Chooses the native library base name from manifest data, preferring an explicit library name over the package name.",
    "cases": [
        {
            "input": {
                "command": "config",
                "data": {
                    "selector": "library_base_name",
                    "manifest": {
                        "lib": {
                            "name": "fast_ext"
                        },
                        "package": {
                            "name": "fallback_pkg"
                        }
                    }
                }
            },
            "expected_output": "library_base_name=fast_ext\n"
        }
    ]
}
```

---

### Feature 5: Shared Library Filename Formatting

**As a developer**, I want to format the compiled native library filename, so I can copy and package the correct file across platforms.

**Expected Behavior / Usage:**

The adapter accepts manifest data, a native shared extension, and a platform flag. Non-Windows platforms prefix the base name with `lib`, while Windows platforms omit that prefix. The extension is appended after a dot. It prints `shared_library_file=<filename>`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_shared_library_file.json`

```json
{
    "description": "Formats the compiled shared-library filename with the correct platform prefix and extension.",
    "cases": [
        {
            "input": {
                "command": "config",
                "data": {
                    "selector": "shared_library_file",
                    "manifest": {
                        "lib": {
                            "name": "fast_ext"
                        },
                        "package": {
                            "name": "fallback"
                        }
                    },
                    "dynamic_extension": "ext",
                    "windows": false
                }
            },
            "expected_output": "shared_library_file=libfast_ext.ext\n"
        }
    ]
}
```

---

### Feature 6: Binary Archive Filename Formatting

**As a developer**, I want to construct a complete prebuilt-binary archive name, so I can publish and retrieve platform-specific archives predictably.

**Expected Behavior / Usage:**

The adapter accepts a library name source, package version, runtime version, operating system, and architecture. It prints `binary_archive_name=<name-version-runtime-os-arch[a format string containing dots and extensions]>`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_binary_archive_name.json`

```json
{
    "description": "Builds the binary archive filename from library name, package version, runtime key, operating system, and CPU architecture.",
    "cases": [
        {
            "input": {
                "command": "config",
                "data": {
                    "selector": "binary_archive_name",
                    "manifest": {
                        "lib": {
                            "name": "fast_ext"
                        },
                        "package": {
                            "name": "fallback"
                        }
                    },
                    "runtime_version": "1.2.0",
                    "target_os": "c64",
                    "target_arch": "z80",
                    "version": "0.1.2"
                }
            },
            "expected_output": "binary_archive_name=fast_ext-0.1.2-ruby12-c64-z80[a format string containing dots and extensions]\n"
        }
    ]
}
```

---

### Feature 7: Project Root and Relative Path Resolution

**As a developer**, I want to resolve host and native project roots and child paths, so I can support projects where host-language and native-code roots differ.

**Expected Behavior / Usage:**

The adapter accepts the current directory, optional host and native project roots, and relative path components. Defaults use the current directory for both roots. It prints the resolved host root, host child path, native root, and native child path on separate lines.

**Test Cases:** `rcb_tests/public_test_cases/feature7_project_paths.json`

```json
{
    "description": "Resolves host-language and native-project roots and joins relative path components beneath those roots.",
    "cases": [
        {
            "input": {
                "command": "config",
                "data": {
                    "selector": "project_paths",
                    "current_dir": "/tmp/project",
                    "options": {
                        "host_project_path": "/opt/host",
                        "native_project_path": "/opt/native"
                    },
                    "components": [
                        "target",
                        "release"
                    ]
                }
            },
            "expected_output": "host_project_root=/opt/host\nhost_project_path=/opt/host/target/release\nnative_project_root=/opt/native\nnative_project_path=/opt/native/target/release\n"
        }
    ]
}
```

---

### Feature 8: Host Extension Install Path

**As a developer**, I want to compute the destination path for a compiled extension, so I can place native artifacts where the host project loads them.

**Expected Behavior / Usage:**

The adapter accepts a project root and a shared-library filename. It prints `host_extension_path=<root>/lib/<filename>`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_host_extension_path.json`

```json
{
    "description": "Computes where the host project should receive the compiled native extension file.",
    "cases": [
        {
            "input": {
                "command": "config",
                "data": {
                    "selector": "host_extension_path",
                    "current_dir": "/tmp/project",
                    "shared_library": "libfast_ext.so"
                }
            },
            "expected_output": "host_extension_path=/tmp/project/lib/libfast_ext.so\n"
        }
    ]
}
```

---

### Feature 9: Release Tag and Manifest Metadata Reading

**As a developer**, I want to evaluate release-tag patterns and manifest-provided tool metadata, so I can select compatible prebuilt binaries from release feeds.

**Expected Behavior / Usage:**

The adapter accepts a release tag pattern and a sample tag. It prints the pattern, sample tag, and the captured version value or `null` if there is no match. Manifest metadata, when requested, is rendered as sorted `key=value` pairs.

**Test Cases:** `rcb_tests/public_test_cases/feature9_release_metadata.json`

```json
{
    "description": "Reads release-tag matching rules and tool metadata from configuration and manifest data.",
    "cases": [
        {
            "input": {
                "command": "config",
                "data": {
                    "selector": "release_tag_pattern",
                    "options": {
                        "release_tag_pattern": "abc(\\d)"
                    },
                    "sample_tag": "abc7"
                }
            },
            "expected_output": "tag_pattern=abc(\\d)\nsample_tag=abc7\nversion_match=7\n"
        }
    ]
}
```

---

### Feature 10: External Native Build Tool Invocation

**As a developer**, I want to run the native build tool only when it is available, so I can avoid failing optional workflows while still building when possible.

**Expected Behavior / Usage:**

The adapter accepts a tool path, arguments, build target, and optional-extension setting. When a tool path exists, it prints that the tool was found, how many shell commands ran, and each shell command. Debug builds run `build`; release builds run `build --release`. When the tool is missing and the extension is required, it prints a neutral error category and notice.

**Test Cases:** `rcb_tests/public_test_cases/feature10_external_build_tool.json`

```json
{
    "description": "Invokes the external native build tool only when available, chooses build flags by target type, and reports a neutral notice when the tool is missing.",
    "cases": [
        {
            "input": {
                "command": "cargo",
                "data": {
                    "selector": "invoke_tool_when_available",
                    "cargo_path": "/opt/tools/cargo",
                    "args": [
                        "foo",
                        "bar"
                    ]
                }
            },
            "expected_output": "tool_found=true\ncommands_run=1\nshell=/opt/tools/cargo foo bar\n"
        },
        {
            "input": {
                "command": "cargo",
                "data": {
                    "selector": "build_target",
                    "cargo_path": "/opt/tools/cargo",
                    "target": "release"
                }
            },
            "expected_output": "tool_found=true\ncommands_run=1\nshell=/opt/tools/cargo build --release\n"
        },
        {
            "input": {
                "command": "cargo",
                "data": {
                    "selector": "missing_tool_notice",
                    "options": {
                        "native_extension_optional": false
                    }
                }
            },
            "expected_output": "error=required_tool_missing\nnotice=external build tool required for native extension build\n"
        }
    ]
}
```

---

### Feature 11: Custom Binary Download Template

**As a developer**, I want to download a versioned prebuilt binary from a caller-provided URL template, so I can install native artifacts without compiling locally.

**Expected Behavior / Usage:**

The adapter accepts a custom URL template, package version, archive filename, and simulated HTTP responses. If no template is configured it prints `downloaded=false`. Otherwise it interpolates version and filename into the URL, performs a GET, logs the URL, emits a debug line naming the archive, unpacks when a body is returned, and prints `downloaded=true`.

**Test Cases:** `rcb_tests/public_test_cases/feature11_custom_binary_download.json`

```json
{
    "description": "Uses an optional custom download URL template to fetch and unpack a versioned binary archive, or skips downloading when no template is configured.",
    "cases": [
        {
            "input": {
                "command": "custom_binary",
                "data": {
                    "options": {
                        "custom_download_template": "https://downloads.example/%{version}/%{filename}"
                    },
                    "manifest": {
                        "package": {
                            "version": "4.5.6"
                        }
                    },
                    "tarball_filename": "fast_ext-4.5.6-runtime-os-arch[a format string containing dots and extensions]",
                    "http": [
                        {
                            "kind": "body",
                            "body": "tarball"
                        }
                    ]
                }
            },
            "expected_output": "downloaded=true\nhttp_get=https://downloads.example/4.5.6/fast_ext-4.5.6-runtime-os-arch[a format string containing dots and extensions]\ndebug=Unpacking binary from Cargo version: fast_ext-4.5.6-runtime-os-arch[a format string containing dots and extensions]\nunpack=called\n"
        }
    ]
}
```

---

### Feature 12: Repository Release Binary Download

**As a developer**, I want to download prebuilt binaries from versioned or latest repository releases, so I can reuse published native artifacts when compilation is unavailable.

**Expected Behavior / Usage:**

The adapter accepts release-download settings, package manifest data, archive filename, and simulated HTTP responses. Disabled release downloads print `downloaded=false`. Cargo-version mode downloads from a URL containing the package version tag. Latest-release mode first reads a release feed, selects the first tag matching the configured pattern, then downloads that tag’s archive. Client failures produce `downloaded=false`; server failures are normalized to `error=server_response_error`.

**Test Cases:** `rcb_tests/public_test_cases/feature12_release_binary_download.json`

```json
{
    "description": "Downloads prebuilt binary archives from repository releases according to cargo-version or latest-release selection, with neutral handling for absent and failing downloads.",
    "cases": [
        {
            "input": {
                "command": "github_release_binary",
                "data": {
                    "options": {
                        "release_downloads_enabled": true
                    },
                    "manifest": {
                        "package": {
                            "version": "4.5.6",
                            "repository": "https://example.invalid/project"
                        }
                    },
                    "tarball_filename": "project-4.5.6[a format string containing dots and extensions]",
                    "http": [
                        {
                            "kind": "body",
                            "body": "tarball"
                        }
                    ]
                }
            },
            "expected_output": "downloaded=true\nhttp_get=https://example.invalid/project/releases/download/v4.5.6/project-4.5.6[a format string containing dots and extensions]\ndebug=Unpacking GitHub release from Cargo version: project-4.5.6[a format string containing dots and extensions]\nunpack=called\n"
        },
        {
            "input": {
                "command": "github_release_binary",
                "data": {
                    "options": {
                        "release_downloads_enabled": true,
                        "release_selection": "latest",
                        "release_tag_pattern": "v(.*)-rust"
                    },
                    "manifest": {
                        "package": {
                            "version": "4.5.6",
                            "repository": "https://example.invalid/project"
                        }
                    },
                    "tarball_filename": "project-latest[a format string containing dots and extensions]",
                    "http": [
                        {
                            "kind": "text",
                            "body": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<feed><entry><title>v0.1.12-rust</title></entry><entry><title>v0.1.11-rust</title></entry></feed>\n"
                        },
                        {
                            "kind": "body",
                            "body": "tarball"
                        }
                    ]
                }
            },
            "expected_output": "downloaded=true\nhttp_get=https://example.invalid/project/releases.atom\nhttp_get=https://example.invalid/project/releases/download/v0.1.12-rust/project-latest[a format string containing dots and extensions]\ndebug=Unpacking GitHub release: project-latest[a format string containing dots and extensions]\nunpack=called\n"
        }
    ]
}
```

---

### Feature 13: Archive Package Round Trip

**As a developer**, I want to package a compiled native file and restore it from the archive, so I can verify distributed archives preserve the extension bytes.

**Expected Behavior / Usage:**

The adapter accepts a file name, file content, package version, and archive name. It creates an archive from the file, removes the source, restores from the archive, and prints whether the archive exists, whether the restored file exists, and the restored content.

**Test Cases:** `rcb_tests/public_test_cases/feature13_archive_roundtrip.json`

```json
{
    "description": "Packages a built native extension into a compressed archive and restores the file from that archive.",
    "cases": [
        {
            "input": {
                "command": "package_roundtrip",
                "data": {
                    "file_name": "test.txt",
                    "file_content": "some extension",
                    "version": "7.8.9",
                    "tarball_name": "test-7.8.9[a format string containing dots and extensions]"
                }
            },
            "expected_output": "tarball_created=true\nrestored_file=true\nrestored_content=some extension\n"
        }
    ]
}
```

---

### Feature 14: Debug Message Writing

**As a developer**, I want to write diagnostic messages only when logging is enabled, so I can troubleshoot build steps without unwanted output files.

**Expected Behavior / Usage:**

The adapter accepts an enabled flag and message. When disabled, no file is created and it prints `debug_file=absent`. When enabled, it writes the message with a trailing newline and prints `debug_file=created` plus the file content.

**Test Cases:** `rcb_tests/public_test_cases/feature14_debug_logging.json`

```json
{
    "description": "Writes diagnostic messages only when a debug destination is enabled.",
    "cases": [
        {
            "input": {
                "command": "debug_log",
                "data": {
                    "enabled": true,
                    "message": "some message"
                }
            },
            "expected_output": "debug_file=created\ndebug_content=some message\n"
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
- use the same environment variable convention as the destination modules
- follow the directory structure logic defined in the project root calculation
