## Product Requirement Document

# Container-Update Targeting & Registry Access Toolkit — Selection Filters, Credential Encoding, and Option Resolution

## Project Goal

Build a reusable toolkit that decides *which* running containers an automated update agent should act on, prepares the *credentials and server address* needed to talk to an image registry, and *resolves runtime options* (including secrets) from the command line and the environment — so an update agent can be configured deterministically and safely without re-implementing this plumbing.

---

## Background & Problem

An agent that automatically refreshes running containers must answer several pure-logic questions before it ever touches a daemon or a network: Given a fleet of candidate containers and a user's configuration, which ones are in scope? Given an image reference and ambient credentials, what auth token and server address should be used? Given a mix of command-line flags, environment variables, and secret files, what is the effective configuration?

Without a shared toolkit, each integration re-implements this glue with subtle inconsistencies — mishandling opt-in versus opt-out markers, leaking secrets, or mis-parsing references. This toolkit centralizes the deterministic decision logic into small, composable, well-specified functions that operate purely on in-memory inputs, leaving the side-effecting work (dialing the daemon, pulling images) to other layers.

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

### Feature 1: Container Selection Filtering

**As a developer**, I want composable predicates that decide whether each candidate container is in scope for an automated update, so I can combine name allow-lists, opt-in/opt-out markers, and scopes into one selection rule.

**Expected Behavior / Usage:**

A candidate container is described by a `name`, a self-identification flag `is_self_agent`, an enable marker `enabled` (a pair of a boolean `value` and a `present` flag), and a `scope` (a pair of a string `value` and a `present` flag). A selector is a predicate that, given a candidate, decides admission. The adapter applies a chosen selector to a list of candidates and, for each one, emits a line `container=<name> included=<bool>` in input order. The sub-features below specify each selector independently.

*1.1 Name Allow-List — admit containers whose name matches a configured list*

A name selector is built from a list of target names layered over a base selector that admits everything. A candidate is admitted only when its name equals one of the target names; the equality check also succeeds when the target equals the candidate name with its first character removed (to tolerate a leading path separator on the reported name). If the target list is empty, the selector imposes no restriction and the base (admit-all) decision stands.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_filter_by_name.json`

```json
{
    "description": "Selecting containers by an explicit allow-list of names. A candidate is admitted only when its name equals one of the target names (the comparison also succeeds against the candidate name with its first character removed). An empty target list imposes no restriction. Output lists each candidate as its name and whether it was admitted.",
    "cases": [
        {"input": {"action": "filter", "mode": "names", "names": ["test"], "containers": [{"name": "test"}]}, "expected_output": "container=test included=true\n"},
        {"input": {"action": "filter", "mode": "names", "names": ["test"], "containers": [{"name": "NoTest"}]}, "expected_output": "container=NoTest included=false\n"}
    ]
}
```

*1.2 Require Opt-In Marker — admit only containers that explicitly set the enable marker*

The selector admits a candidate only when its enable marker is present, regardless of whether the marker's value is true or false; an absent marker causes rejection.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_filter_by_enable_label.json`

```json
{
    "description": "Restricting selection to containers that explicitly carry an opt-in enable marker. The selector admits a candidate only when the marker is present (value irrelevant); an absent marker is rejected. Output lists each candidate as its name and whether it was admitted.",
    "cases": [
        {"input": {"action": "filter", "mode": "enable_label", "containers": [{"name": "a", "enabled": {"value": true, "present": true}}]}, "expected_output": "container=a included=true\n"},
        {"input": {"action": "filter", "mode": "enable_label", "containers": [{"name": "c", "enabled": {"value": false, "present": false}}]}, "expected_output": "container=c included=false\n"}
    ]
}
```

*1.3 Honor Opt-Out Marker — reject only containers that explicitly opt out*

The selector rejects a candidate only when its enable marker is present and its value is the opt-out value (false); in every other case (marker present and true, or marker absent) the candidate is admitted.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_filter_by_disabled_label.json`

```json
{
    "description": "Excluding only containers that explicitly opt out via the enable marker. A candidate is rejected only when the marker is present with the opt-out value; otherwise it is admitted. Output lists each candidate as its name and whether it was admitted.",
    "cases": [
        {"input": {"action": "filter", "mode": "disabled_label", "containers": [{"name": "b", "enabled": {"value": false, "present": true}}]}, "expected_output": "container=b included=false\n"},
        {"input": {"action": "filter", "mode": "disabled_label", "containers": [{"name": "c", "enabled": {"value": false, "present": false}}]}, "expected_output": "container=c included=true\n"}
    ]
}
```

*1.4 Scope Match — admit only containers in a configured scope*

A scope selector is built from a target scope string. A candidate is admitted only when it has a scope present whose value equals the target scope; a mismatched or absent scope causes rejection.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_filter_by_scope.json`

```json
{
    "description": "Restricting selection to containers that belong to a specific named scope. A candidate is admitted only when its scope is present and equals the target scope; mismatch or absence is rejected. Output lists each candidate as its name and whether it was admitted.",
    "cases": [
        {"input": {"action": "filter", "mode": "scope", "scope": "testscope", "containers": [{"name": "a", "scope": {"value": "testscope", "present": true}}]}, "expected_output": "container=a included=true\n"},
        {"input": {"action": "filter", "mode": "scope", "scope": "testscope", "containers": [{"name": "b", "scope": {"value": "nottestscope", "present": true}}]}, "expected_output": "container=b included=false\n"}
    ]
}
```

*1.5 Composite Selector — combine name, optional opt-in requirement, optional scope, and always-on opt-out exclusion*

The composite selector is assembled from layers: a name allow-list, an optional requirement that the opt-in marker be present, an optional scope restriction, and an always-applied exclusion of containers that explicitly opt out. The opt-out exclusion is evaluated first, so a container that explicitly opts out is rejected before any other layer is consulted. The example below configures a name allow-list only.

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_composite_filter.json`

```json
{
    "description": "The composite selector used to choose update targets: a name allow-list, an optional opt-in requirement, an optional scope, and an always-applied opt-out exclusion evaluated first. This case configures a name allow-list only. Output lists each candidate as its name and whether it survived the full chain.",
    "cases": [
        {"input": {"action": "filter", "mode": "build", "names": ["test"], "enable_label": false, "scope": "", "containers": [{"name": "Invalid", "enabled": {"value": false, "present": false}}, {"name": "test", "enabled": {"value": false, "present": false}}, {"name": "Invalid", "enabled": {"value": true, "present": true}}, {"name": "test", "enabled": {"value": true, "present": true}}, {"name": "x", "enabled": {"value": false, "present": true}}]}, "expected_output": "container=Invalid included=false\ncontainer=test included=true\ncontainer=Invalid included=false\ncontainer=test included=true\ncontainer=x included=false\n"}
    ]
}
```

*1.6 Base Predicates — admit-all and self-identification*

Two trivial building-block predicates underlie the others: an unconditional admit-all predicate that accepts every candidate, and a self-identification predicate that admits a candidate only when it reports itself as an instance of the update agent.

**Test Cases:** `rcb_tests/public_test_cases/feature1_6_base_predicates.json`

```json
{
    "description": "The two base predicates: an unconditional admit-all, and a self-identification predicate that admits only candidates reporting themselves as the update agent. Output lists each candidate as its name and whether it was admitted.",
    "cases": [
        {"input": {"action": "filter", "mode": "no_filter", "containers": [{"name": "anything"}]}, "expected_output": "container=anything included=true\n"},
        {"input": {"action": "filter", "mode": "self_agent", "containers": [{"name": "agent", "is_self_agent": true}]}, "expected_output": "container=agent included=true\n"}
    ]
}
```

---

### Feature 2: Registry Credentials & Image Reference

**As a developer**, I want to derive the auth token and server address needed to reach an image registry from ambient inputs, so the agent can authenticate without bespoke parsing in each call site.

**Expected Behavior / Usage:**

*2.1 Environment Credential Token — encode user/password from the environment*

When both a user name and a password are supplied through their environment variables, the toolkit assembles an auth object and emits its transport encoding: the Base64 of a compact JSON document carrying a `username` and a `password` field (in that order, with no extra fields). When either credential is missing, no token is produced and a neutral missing-credentials error category is reported. Output is either `token=<base64>` or `error=missing_credentials`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_env_credentials.json`

```json
{
    "description": "Building an encoded registry credential token from environment-supplied credentials. With both user name and password present, emit the Base64 of a compact JSON document carrying the username and password fields; if either is missing, report a neutral missing-credentials error. Output is the encoded token or the neutral error line.",
    "cases": [
        {"input": {"action": "env_auth", "user": "user-a", "pass": "pass-a"}, "expected_output": "token=eyJ1c2VybmFtZSI6InVzZXItYSIsInBhc3N3b3JkIjoicGFzcy1hIn0=\n"},
        {"input": {"action": "env_auth", "user": "", "pass": ""}, "expected_output": "error=missing_credentials\n"}
    ]
}
```

*2.2 Server Address Extraction — derive the registry server from an image reference*

The image reference is parsed, then the server component is taken as the substring up to the first path separator of the parsed reference. A fully qualified reference whose leading component is a host name yields that host name; a reference whose leading component is an organization (no host) yields that organization name. An input that cannot be parsed as a reference (such as the empty string) reports a neutral invalid-reference error category. Output is either `server=<server>` or `[a specific sentinel value for invalid references]`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_server_address.json`

```json
{
    "description": "Extracting the registry server component from an image reference: parse the reference, then take the substring up to the first path separator. A leading host component yields the host; a leading organization component yields the organization. An unparseable input (e.g. empty string) reports a neutral invalid-reference error. Output is the extracted server or the neutral error line.",
    "cases": [
        {"input": {"action": "parse_server", "ref": "example.com/lib/app"}, "expected_output": "server=example.com\n"},
        {"input": {"action": "parse_server", "ref": ""}, "expected_output": "[a specific sentinel value for invalid references]\n"}
    ]
}
```

---

### Feature 3: Runtime Option Resolution

**As a developer**, I want command-line options, environment variables, and secret files reconciled into the effective configuration, so the agent behaves predictably regardless of how operators supply settings.

**Expected Behavior / Usage:**

*3.1 Daemon Connection Mapping — translate connection options into client environment variables*

Three options may be supplied: a daemon host address, a boolean verify-TLS switch, and an API version. With no options supplied, the host falls back to its built-in default socket address and the verify-TLS variable is left unset (empty string). When a custom host is supplied it is propagated verbatim; when the verify-TLS switch is enabled, the corresponding variable is set to the string `1`. Output reports `docker_host=<value>` then `docker_tls_verify=<value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_docker_env.json`

```json
{
    "description": "Translating connection options into client environment variables. With no options, the host defaults to the built-in socket address and verify-TLS is empty; a supplied host is propagated verbatim, and an enabled verify-TLS switch sets its variable to the string flag value. Output reports the resolved host and the resolved verify-TLS variable.",
    "cases": [
        {"input": {"action": "docker_env"}, "expected_output": "docker_host=[the magic default path for docker sockets]\ndocker_tls_verify=\n"},
        {"input": {"action": "docker_env", "host": "some-custom-docker-host", "tlsverify": true, "api_version": "1.99"}, "expected_output": "docker_host=some-custom-docker-host\ndocker_tls_verify=1\n"}
    ]
}
```

*3.2 Secret Resolution — accept a secret inline or as a file reference*

A sensitive option value may be supplied either inline or as a reference to a file holding the secret. The resolver inspects the configured value: if it names an existing file on disk, the value is replaced by the trimmed contents of that file; otherwise the inline string is kept as-is. Output reports `secret=<resolved value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_secret_from_file.json`

```json
{
    "description": "Resolving a sensitive option value supplied either inline or via a file reference. If the configured value names an existing file, it is replaced by the trimmed file contents; otherwise the inline string is kept. Output reports the resolved secret value.",
    "cases": [
        {"input": {"action": "secret_resolve", "value": "supersecretstring"}, "expected_output": "secret=supersecretstring\n"},
        {"input": {"action": "secret_resolve", "file_content": "megasecretstring"}, "expected_output": "secret=megasecretstring\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the selection predicates, the credential/reference helpers, and the option-resolution logic described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the result to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `filter` (with a `mode` of `names`, `enable_label`, `disabled_label`, `scope`, `build`, `no_filter`, or `self_agent`) applies a selector to a list of `containers`; `env_auth` encodes environment credentials; `parse_server` extracts a server from a `ref`; `docker_env` maps connection options to client environment variables; `secret_resolve` resolves an inline or file-backed secret. Native error conditions MUST be rendered as neutral `error=<category>` lines, never leaking host-language runtime identities.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- the candidate must pass the strict scope validation logic
- composites filter sequence ensures chain of custody first
