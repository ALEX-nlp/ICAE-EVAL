## Product Requirement Document

# Git Remote & URL Normalization Utilities — Owner/Repo Extraction and Query Sanitization

## Project Goal

Build a small library of URL-handling helpers that lets tooling reliably identify the owner/repository a Git remote points at, and clean tracking noise out of download URLs, so callers can work with stable, canonical identifiers and links without re-implementing fragile string parsing every time.

---

## Background & Problem

Tools that automate work against hosted Git repositories and external download links repeatedly face two small but error-prone parsing chores. First, a Git remote can be written in several equivalent forms — an SSH shorthand like `user@host:owner/name(.git)` or an HTTPS URL like `https://host/owner/name`, sometimes carrying embedded credentials — yet callers only care about the canonical `owner/name` identifier. Second, download URLs are frequently decorated with volatile tracking parameters (session ids, analytics tokens) that change on every request and must be stripped so that the same artifact always resolves to the same stable URL, while genuinely meaningful query parameters must be preserved.

Without a shared utility, each call site hand-rolls regular expressions and query manipulation, leading to subtle inconsistencies: credentials leaking into identifiers, `.git` suffixes not being trimmed, meaningful query parameters being discarded, or tracking parameters surviving. This library provides one well-defined contract for both chores.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic function calls to the core domain.

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

### Feature 1: Extract Owner/Repository Identifier From A Git Remote URL

**As a developer**, I want to turn any equivalent form of a Git remote URL into the canonical `owner/name` identifier, so I can key on a single stable string regardless of how the remote was written.

**Expected Behavior / Usage:**

The input is a single URL string. The output is the owner and repository name joined by exactly one forward slash, followed by a trailing newline. Two distinct remote forms are recognized — an SSH shorthand and an HTTPS URL — and each is handled by its own contract below.

*1.1 SSH shorthand remote — extract owner/name from a `user@host:owner/name` address*

When the remote is given in the SSH shorthand form `git@host:owner/name`, the result is the `owner/name` portion that follows the colon. If the repository name ends with a `.git` suffix, that suffix is stripped; if it is absent, the name is used verbatim. The host and the `git@` prefix never appear in the output.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_ssh_remote.json`

```json
{
    "description": "Extract the canonical owner/repository identifier from an SSH-style Git remote address of the form user@host:owner/name. The input is a single URL string; the output is the owner and repository name joined by a single forward slash. A trailing .git suffix on the repository name, if present, is removed; when it is absent the name is taken verbatim.",
    "cases": [
        {
            "input": {"action": "parse_repo_id", "url": "git@github.com:flathub/flatpak-external-data-checker.git"},
            "expected_output": "flathub/flatpak-external-data-checker\n"
        },
        {
            "input": {"action": "parse_repo_id", "url": "git@github.com:flathub/flatpak-external-data-checker"},
            "expected_output": "flathub/flatpak-external-data-checker\n"
        }
    ]
}
```

*1.2 HTTPS remote — extract owner/name from an `https://host/owner/name` URL, ignoring credentials*

When the remote is an HTTPS URL, the result is everything after the leading slash of the URL path — i.e. the `owner/name` segment. Any user credentials embedded in the authority (a `user:password@` prefix before the host) are ignored entirely and never leak into the output. The repository name is preserved verbatim, including dots in the name.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_https_remote.json`

```json
{
    "description": "Extract the canonical owner/repository identifier from an HTTPS Git remote URL. The input is a single URL string; the output is everything after the leading slash of the URL path, i.e. the owner and repository name joined by a single forward slash. Any user credentials embedded in the authority component (a user:password@ prefix before the host) are ignored and do not appear in the result.",
    "cases": [
        {
            "input": {"action": "parse_repo_id", "url": "https://github.com/flathub/com.dropbox.Client"},
            "expected_output": "flathub/com.dropbox.Client\n"
        },
        {
            "input": {"action": "parse_repo_id", "url": "https://acce55ed:x-oauth-basic@github.com/endlessm/eos-google-chrome-app"},
            "expected_output": "endlessm/eos-google-chrome-app\n"
        }
    ]
}
```

---

### Feature 2: Strip Tracking Parameters From A URL Query String

**As a developer**, I want volatile tracking parameters removed from a download URL while keeping the parameters that actually matter, so the same artifact always resolves to the same canonical link.

**Expected Behavior / Usage:**

The input is a single URL string. The output, followed by a trailing newline, is the same URL with its query string rewritten: every query parameter whose name begins with an underscore is treated as a tracking identifier and removed, while all other parameters are kept in their original order. A URL that has no query string at all is returned completely unchanged. Preserved parameter values are kept exactly as supplied, including percent-encoded characters. Credentials in the authority component are not part of the query string and are left untouched.

**Test Cases:** `rcb_tests/public_test_cases/feature2_strip_tracking_params.json`

```json
{
    "description": "Sanitize a URL's query string by dropping tracking parameters while preserving meaningful ones. The input is a single URL string; the output is the URL with every query parameter whose name begins with an underscore removed, and all other parameters kept in their original order. A URL with no query string is returned unchanged. Parameters whose names do not start with an underscore are preserved exactly, including their percent-encoded values. User credentials in the authority component are not part of the query string and are left untouched.",
    "cases": [
        {
            "input": {"action": "sanitize_query", "url": "https://d11yldzmag5yn.cloudfront.net/prod/3.5.372466.0322/zoom_x86_64.tar.xz?_x_zm_rtaid=muDd1uOqSZ-xUScZF698QQ.1585134521724.21e5ab14908b2121f5ed53882df91cb9&_x_zm_rhtaid=732"},
            "expected_output": "https://d11yldzmag5yn.cloudfront.net/prod/3.5.372466.0322/zoom_x86_64.tar.xz\n"
        },
        {
            "input": {"action": "sanitize_query", "url": "https://dl2.tlauncher.org/f.php?f=files%2FTLauncher-2.69.zip"},
            "expected_output": "https://dl2.tlauncher.org/f.php?f=files%2FTLauncher-2.69.zip\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the result to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `parse_repo_id` takes a `url` and prints the canonical `owner/name` identifier; `sanitize_query` takes a `url` and prints the URL with tracking parameters stripped. Every successful result is emitted on its own line terminated by a newline.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- keep the input as-is
- preserve dots in repo name
