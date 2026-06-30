## Product Requirement Document

# Notification Account & Feed-Sync Domain — Credential Handling, Identity Mapping, and Subscription Pulls

## Project Goal

Build the domain core behind a service that lets a person track their notifications from an external code-hosting provider in one place. The core owns how an account is represented, how a sign-in identity is mapped onto that account, which credential the account presents to the upstream provider, when and how far back the notification feed is pulled, and how each pulled item is normalized for storage — so that the surrounding web/UI layer can stay thin and consistent.

---

## Background & Problem

A person authenticates through an external provider and, from then on, the service keeps a local mirror of their notifications. Doing this by hand is fiddly: you must translate the provider's sign-in payload into stored account fields, decide which credential (a default one, or an optional personal one) to send upstream, pick a sensible "since" window so you neither miss items nor re-pull everything, and turn each raw upstream notification into a tidy, queryable record. You also need to guard the account: required fields must be present and unique, and any personal credential must actually belong to the account and carry the right authorization scope before it is trusted.

This project provides that domain core as a well-defined input/output contract. Given a sign-in payload, it yields account fields. Given account state and the current time, it yields the exact upstream request window. Given a raw feed, it yields normalized records with canonical subject links. Given candidate account data, it yields a precise, normalized verdict on validity and authorization. The presentation layer (flash banners, pages) consumes small helpers from the same core.

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

### Feature 1: Flash Banner Style Resolution

**As a developer**, I want a short message category mapped to the presentation style class for its banner, so the UI layer can render notices consistently without hard-coding style names everywhere.

**Expected Behavior / Usage:**

The input supplies a single category keyword. A small fixed set of known categories resolve to dedicated style classes: a success category resolves to `alert-success`, a generic error category resolves to `alert-danger`, a warning/alert category resolves to `alert-warning`, and an informational notice category resolves to `alert-info`. Any category that is not in this known set is treated as already being a literal style class and is returned unchanged. The output is a single line reporting the resolved style class.

**Test Cases:** `rcb_tests/public_test_cases/feature1_flash_style_class.json`

```json
{
    "description": "Map a short flash/notice category keyword to the presentation style class used to render that message banner. A small fixed set of known categories map to their dedicated style classes; any unknown category is passed through unchanged so callers can supply a literal style class directly.",
    "cases": [
        {"input": {"action": "flash_class", "flash_type": "success"}, "expected_output": "style_class=alert-success\n"},
        {"input": {"action": "flash_class", "flash_type": "foobar"}, "expected_output": "style_class=foobar\n"}
    ]
}
```

---

### Feature 2: Effective Credential Selection

**As a developer**, I want the account to decide which credential it presents upstream, so an optional personal credential can override the default one — but only when the instance allows it and one is actually set.

**Expected Behavior / Usage:**

An account holds a primary (default) credential and may also hold an optional personal credential. The instance has a global switch controlling whether personal credentials are permitted at all. The personal credential is selected only when BOTH the switch is on AND a non-empty personal credential is present; in every other case the primary credential is selected. The output is a single line reporting the selected credential value.

**Test Cases:** `rcb_tests/public_test_cases/feature2_credential_selection.json`

```json
{
    "description": "Choose which credential an account should present to the upstream service. The account holds a primary credential and may also hold a personal credential. A personal credential is honored only when the instance permits personal credentials AND a personal credential is actually present; otherwise the primary credential is used. The selected credential value is reported.",
    "cases": [
        {"input": {"action": "token_selection", "tokens_enabled": true, "personal_access_token": "pat", "access_token": "acc"}, "expected_output": "selected_token=pat\n"},
        {"input": {"action": "token_selection", "tokens_enabled": false, "personal_access_token": "pat", "access_token": "acc"}, "expected_output": "selected_token=acc\n"}
    ]
}
```

---

### Feature 3: Sign-In Identity Mapping

**As a developer**, I want the provider's sign-in payload projected onto the account's stored fields, so a returning or new sign-in keeps the account's external id, login, and credential in sync.

**Expected Behavior / Usage:**

The input is the identity payload returned by the external sign-in provider. It carries a numeric provider user id at the top level, a nested profile object whose nickname is the login, and a nested credentials object whose token is the access credential. Applying the payload sets the account's external id from the provider user id, the account's login from the profile nickname, and the account's access credential from the credentials token. The output reports the three resulting account fields, one per line.

**Test Cases:** `rcb_tests/public_test_cases/feature3_auth_identity_mapping.json`

```json
{
    "description": "Project the identity payload returned by the external sign-in provider onto an account's stored fields. The payload carries a numeric provider user id, a nested profile object holding the login nickname, and a nested credentials object holding an access token. These map onto the account's external id, login, and access token respectively. The resulting account fields are reported.",
    "cases": [
        {"input": {"action": "auth_mapping", "auth": {"uid": 1, "info": {"nickname": "douglas_adams"}, "credentials": {"token": "abcdefg"}}}, "expected_output": "github_id=1\ngithub_login=douglas_adams\naccess_token=abcdefg\n"}
    ]
}
```

---

### Feature 4: Sync Window Selection

**As a developer**, I want the lower-bound timestamp for a feed pull chosen from the account's sync history, so a first-time pull reaches back far enough while a routine pull stays narrow.

**Expected Behavior / Usage:**

The input supplies the account's last-synchronized timestamp (or null if it has never synchronized) together with the current time. When the account has never synchronized, the lower bound is one month before the current time; when it has synchronized before, the lower bound is one week before the current time. The request always asks for the full set (read and unread). The output reports the full-set flag and the computed lower-bound timestamp in ISO 8601 (UTC, `Z`-suffixed), one per line.

**Test Cases:** `rcb_tests/public_test_cases/feature4_sync_window.json`

```json
{
    "description": "Determine the time window used when pulling notifications for an account, expressed as the lower-bound timestamp sent to the upstream feed. The decision depends on whether the account has ever been synchronized before, evaluated relative to a supplied current time. An account that has never synchronized pulls a wider window (one month back); an account that has synchronized before pulls a narrower window (one week back). The full-history flag and the computed lower-bound timestamp (ISO 8601) are reported.",
    "cases": [
        {"input": {"action": "sync_window", "last_synced_at": null, "now": "2016-12-19T19:00:00Z"}, "expected_output": "all=true\nsince=[the initial sync endpoint and time format used for new accounts]\n"},
        {"input": {"action": "sync_window", "last_synced_at": "2016-12-19T19:00:00Z", "now": "2016-12-19T19:00:00Z"}, "expected_output": "all=true\nsince=[a specific relative time offset for sync windows]\n"}
    ]
}
```

---

### Feature 5: Subject Link Normalization On Store

**As a developer**, I want each pulled feed item stored with a canonical subject link, so the UI can always link straight to the right place regardless of item kind.

**Expected Behavior / Usage:**

The input is the raw feed as an array of notification objects, each carrying an id, a reason, an unread flag, timestamps, its own thread url, a subject (with a title, a type, and a possibly-null subject url), and the owning repository (with a numeric id, a full name, a public web url, and an owner login). Each item is normalized and stored. For an ordinary subject, the stored subject link is the subject's own url verbatim. For a repository-invitation subject — whose own url is absent (null) — the stored subject link is instead derived from the repository's public web url with an `/invitations` path appended. The output reports the stored subject type and the stored subject link of the most recently stored item, one per line.

**Test Cases:** `rcb_tests/public_test_cases/feature5_subject_routing.json`

```json
{
    "description": "Persist a notification fetched from the upstream feed and derive its canonical subject link. The upstream feed is an array of notification objects; each has a subject with a type and a possibly-null subject url, plus the owning repository (with its full name and its public web url). For an ordinary subject, the stored subject url is the subject's own url verbatim. For a repository-invitation subject (whose own url is null), the stored subject url is derived from the repository's public web url with an invitations path appended. The stored subject type and subject url of the most recently stored notification are reported.",
    "cases": [
        {
            "input": {"action": "download_subject_url", "notifications": [
                {"id": "1", "reason": "subscribed", "unread": true, "updated_at": "2016-12-19T22:01:45Z", "last_read_at": null, "url": "https://[the initial sync endpoint and time format used for new accounts]/threads/1", "subject": {"title": "UI Updates", "url": "https://api.github.com/repos/octobox/octobox/issues/56", "type": "Issue"}, "repository": {"id": 930405, "full_name": "octobox/octobox", "html_url": "https://github.com/octobox/octobox", "owner": {"login": "octobox"}}}
            ]},
            "expected_output": "subject_type=Issue\nsubject_url=https://api.github.com/repos/octobox/octobox/issues/56\n"
        },
        {
            "input": {"action": "download_subject_url", "notifications": [
                {"id": "8675309", "reason": "subscribed", "unread": null, "updated_at": "2015-12-25T17:14:34Z", "last_read_at": null, "url": "https://[the initial sync endpoint and time format used for new accounts]/threads/8675309", "subject": {"title": "Invitation to join rails/rails from dhh", "url": null, "type": "RepositoryInvitation"}, "repository": {"id": 76692542, "full_name": "rails/rails", "html_url": "https://github.com/rails/rails", "owner": {"login": "rails"}}}
            ]},
            "expected_output": "subject_type=RepositoryInvitation\nsubject_url=https://github.com/rails/rails/invitations\n"
        }
    ]
}
```

---

### Feature 6: Account Record Validation

**As a developer**, I want candidate account data validated with a precise, normalized verdict, so bad records are rejected before storage with a clear reason per field.

**Expected Behavior / Usage:**

The input supplies the candidate account's external id, access credential, and login, and may separately supply an already-stored conflicting account. An account requires all three fields to be present, and additionally requires the external id and the access credential to each be unique across stored accounts. The output reports `valid=true` when every rule passes. Otherwise it reports `valid=false` followed by one line per offending field, naming the field and a normalized failure category: `blank` for a missing required value, and `taken` for a value that duplicates an existing account's value.

**Test Cases:** `rcb_tests/public_test_cases/feature6_account_validation.json`

```json
{
    "description": "Validate an account record before it is stored. An account requires a present external id, a present access token, and a present login; the external id and the access token must each be unique across all stored accounts. When a conflicting account already exists, it is supplied separately. The result reports whether the record is valid; when invalid, each offending field is reported together with a normalized failure category (a missing required value versus a duplicate of an existing value).",
    "cases": [
        {"input": {"action": "account_validation", "attributes": {"github_id": null, "access_token": "tok", "github_login": "andrew"}}, "expected_output": "valid=false\nfield=github_id error=blank\n"},
        {"input": {"action": "account_validation", "existing": {"github_id": 7, "access_token": "dup", "github_login": "seed"}, "attributes": {"github_id": 7, "access_token": "other", "github_login": "andrew"}}, "expected_output": "valid=false\nfield=github_id error=taken\n"},
        {"input": {"action": "account_validation", "attributes": {"github_id": 5, "access_token": "tok", "github_login": "andrew"}}, "expected_output": "valid=true\n"}
    ]
}
```

---

### Feature 7: Initial Sync On Account Creation

**As a developer**, I want a newly created account to immediately pull its first batch of notifications, so a person sees data right after signing up without a manual step.

**Expected Behavior / Usage:**

The input supplies a brand-new account's external id, login, and access credential, together with a fixed current time. Creating the account must automatically trigger exactly one pull from the upstream notifications endpoint. Because the account is brand new (never synchronized), the pull uses the wider window — its lower-bound timestamp is one month before the supplied current time. The output reports that the initial sync was performed, the requested host and path, and the lower-bound timestamp that was sent, one per line.

**Test Cases:** `rcb_tests/public_test_cases/feature7_account_creation_sync.json`

```json
{
    "description": "Confirm that creating a brand-new account automatically triggers an initial pull from the upstream notification feed. A new account is created with its external id, login, and access token at a fixed current time. Creation must cause exactly one request to the upstream notifications endpoint, whose lower-bound timestamp reflects the never-synchronized (one-month-back) window relative to the current time. The result reports that the initial sync was performed, the requested host and path, and the lower-bound timestamp that was sent.",
    "cases": [
        {"input": {"action": "account_creation_sync", "github_id": 42, "github_login": "douglas_adams", "access_token": "abcdefg", "now": "2016-12-19T19:00:00Z"}, "expected_output": "initial_sync=performed\nendpoint=[the initial sync endpoint and time format used for new accounts]\nsince=[the initial sync endpoint and time format used for new accounts]\n"}
    ]
}
```

---

### Feature 8: Personal Credential Authorization

**As a developer**, I want a personal credential attached to an account checked before it is trusted, so only a permitted, correctly-owned, sufficiently-scoped credential is accepted.

**Expected Behavior / Usage:**

The input supplies whether the instance permits personal credentials, the personal credential, the account's external id and access credential, the external identity id the upstream provider reports for that credential, and the authorization scopes that credential carries. Three preconditions must all hold for acceptance: (1) the instance permits personal credentials; (2) the upstream-reported external identity id equals the account's external id; and (3) the carried scopes include the required notifications scope. When all hold, the output is `authorized=true`. Otherwise the output is `authorized=false` followed by a normalized reason category: `disallowed_tokens` when personal credentials are not permitted, `invalid_token` when the credential does not belong to this identity, and `missing_scope` when the required scope is absent. The preconditions are evaluated in that order, and the first one that fails determines the reason.

**Test Cases:** `rcb_tests/public_test_cases/feature8_personal_token_authorization.json`

```json
{
    "description": "Authorize a personal credential attached to an account before it is accepted. Three preconditions must all hold: the instance must permit personal credentials, the credential must belong to the same external identity as the account (the upstream identity service is consulted and must report the same id), and the credential must carry the required notifications authorization scope. When all hold the credential is accepted; otherwise it is rejected with a normalized reason category: personal credentials not permitted, credential not valid for this identity, or required scope absent.",
    "cases": [
        {"input": {"action": "personal_token_authorization", "tokens_enabled": false, "personal_access_token": "1234", "github_id": 1060, "access_token": "acc", "remote_user_id": 1060, "oauth_scopes": "notifications"}, "expected_output": "authorized=false\nreason=disallowed_tokens\n"},
        {"input": {"action": "personal_token_authorization", "tokens_enabled": true, "personal_access_token": "1234", "github_id": 1060, "access_token": "acc", "remote_user_id": 98, "oauth_scopes": "notifications"}, "expected_output": "authorized=false\nreason=invalid_token\n"},
        {"input": {"action": "personal_token_authorization", "tokens_enabled": true, "personal_access_token": "1234", "github_id": 1060, "access_token": "acc", "remote_user_id": 1060, "oauth_scopes": "user, repo"}, "expected_output": "authorized=false\nreason=missing_scope\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above (account representation and validation, credential selection, identity mapping, sync-window selection, feed normalization with canonical subject links, initial-sync-on-create, and personal-credential authorization). Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the resulting lines to stdout, matching the per-feature contracts above. The request's `action` field selects behavior. Any failure that the core surfaces (invalid record, unauthorized credential, unknown action) must be rendered as a normalized, language-neutral line contract (e.g. `error=<category>`, `field=<name> error=<category>`, `reason=<category>`) — never leaking host-language runtime artifacts. Upstream provider interactions must be isolated from the real network during testing.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- determine the URL pattern following the same scheme as the SubjectLinker class
- cross-reference the valid_account_schema.json for required field validation errors
