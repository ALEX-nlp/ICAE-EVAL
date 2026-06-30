## Product Requirement Document

# Permission Status Toolkit - A Typed Model and Request Lifecycle for Runtime Permissions

## Project Goal

Build a library that gives developers a precise, typed vocabulary for the **status of an OS-level permission** and a small **request lifecycle** around it, so they can reason about "granted / denied / needs-a-rationale / must-ask-at-runtime" with simple, composable checks instead of juggling raw integer result codes and ad-hoc boolean flags. The library lets an app decide what to do next (proceed, show an explanation, or trigger a request) from a single status value, and lets it subscribe to the outcome of a request through a clean listener/callback model.

---

## Background & Problem

Without this library, developers inspect permissions by comparing raw platform constants, then hand-roll booleans like `isDenied`, `neverAskAgain`, `shouldExplain` scattered across the codebase. The rules are subtle: a permission can be granted; denied in a way that is *permanent* (the user opted out for good, or the platform never exposes it); denied in a way where *showing a rationale* is appropriate; or in a state where the only way to learn more is to actually launch a runtime request. Encoding these distinctions with loose booleans is error-prone — combinations get mishandled, "deny" and "permanently deny" get conflated, and aggregating the status of several permissions at once (all granted? any still need asking?) becomes repetitive boilerplate.

With this library, every permission outcome is one value drawn from a closed set of categories. Each category has a cheap predicate, collections of statuses have ready-made `all_*` / `any_*` quantifiers, and a request object provides a uniform way to attach listeners, deliver results to them, and run a one-shot callback that cleans itself up. A configuration builder assembles a request and fails fast with clear, categorized errors when its required inputs are missing.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain has several distinct responsibilities (a status type model, predicate/quantifier helpers, a request lifecycle with a listener registry, a one-shot callback, and a validating builder). Organize these into clear logical units; do not collapse everything into one file, but do not over-engineer either.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box contract for the execution adapter**, not the internal data model. The core domain (status model, predicates, request lifecycle, builder) MUST be completely decoupled from stdin/stdout and JSON parsing. The execution adapter is the only component that translates JSON commands into idiomatic core calls and renders results as the line-oriented text contract.

3. **Adherence to SOLID Design Principles:**
   - **SRP:** Keep the status model, the predicates/quantifiers, the listener registry, the one-shot callback, and the builder validation as separate concerns.
   - **OCP:** New status categories or new quantifiers should extend the model without rewriting existing logic.
   - **LSP:** The denied sub-kinds must be usable anywhere a denied status is expected; any concrete request must be usable anywhere the request abstraction is expected.
   - **ISP:** The listener interface must be minimal — a single "results are available" notification.
   - **DIP:** The builder must depend on the request abstraction and on a handler-provider abstraction, not on any concrete request implementation.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** Predicates and quantifiers should read naturally; building a request should be a fluent, hard-to-misuse sequence.
   - **Resilience:** Missing required configuration must be reported as a specific, normalized error category (not a generic crash). The one-shot callback must detach itself after firing so it cannot leak or double-fire.

---

## Core Features

### Feature 1: Single Permission Status Classification

**As a developer**, I want to ask a single permission status which category it belongs to, so I can branch my app's behavior (proceed, explain, or request) from one value.

**Expected Behavior / Usage:**

A permission status carries a category and the permission identifier it relates to. There are four mutually exclusive top-level categories: **granted**, **permanently denied**, **should-show-rationale**, and **request-required**. The two denied sub-kinds (permanently denied and should-show-rationale) both belong to the broader **denied** category. Given one status, the system reports the result of five independent predicates: granted, denied (any denied sub-kind), permanently-denied, should-show-rationale, and request-required. For any single status, exactly one of {granted, denied, request-required} is true; and within denied, exactly one of {permanently-denied, should-show-rationale} is true while the other is false. The input is a status object `{type, permission}`; the output is one `key=boolean` line per predicate, preceded by the permission identifier.

**Test Cases:** `rcb_tests/public_test_cases/feature1_status_classification.json`

```json
{
    "description": "Classify a single permission status into the full set of category predicates. The input is a status object with a category type and the permission identifier it relates to; the output reports, for that one status, the boolean result of each independent predicate: whether it counts as granted, as denied (any denied sub-kind), as permanently denied, as needing a rationale, and as still requiring a runtime request. Exactly one of granted / denied / request-required is true for any status, and the two denied sub-kinds (permanently denied vs. should-show-rationale) are mutually exclusive within the denied category.",
    "cases": [
        {
            "input": {"op": "classify_status", "status": {"type": [a specific set of status type literals (includes runtime decision types) — ask the PM for the exact strings], "permission": "android.permission.SEND_SMS"}},
            "expected_output": "permission=android.permission.SEND_SMS\ngranted=true\ndenied=false\npermanently_denied=false\nshould_show_rationale=false\nrequest_required=false\n"
        },
        {
            "input": {"op": "classify_status", "status": {"type": [a specific set of status type literals (includes runtime decision types) — ask the PM for the exact strings], "permission": "android.permission.SEND_SMS"}},
            "expected_output": "permission=android.permission.SEND_SMS\ngranted=false\ndenied=true\npermanently_denied=false\nshould_show_rationale=true\nrequest_required=false\n"
        }
    ]
}
```

---

### Feature 2: Collective Status Aggregation

**As a developer**, I want to ask whether *all* or *any* permissions in a set fall into a given category, so I can make a single decision over a multi-permission request without writing loops.

**Expected Behavior / Usage:**

Given an ordered list of statuses, the system reports, for each category, two quantifiers: an `all_*` flag that is true only when every element of the list belongs to that category, and an `any_*` flag that is true when at least one element does. The five categories are granted, denied (any denied sub-kind), permanently-denied, should-show-rationale, and request-required. The output begins with the list size, then emits all `all_*` lines followed by all `any_*` lines. A mixed list typically yields `any_* = true` with `all_* = false` for the categories represented; a homogeneous list yields `all_* = true` for its category. The input is a list of status objects; the output is `count=<n>` followed by the ten quantifier lines.

**Test Cases:** `rcb_tests/public_test_cases/feature2_status_aggregation.json`

```json
{
    "description": "Aggregate a list of permission statuses into collective predicates. The input is an ordered list of status objects (each with a category type and permission identifier). The output reports the size of the list, then for every category a pair of quantifiers: an `all_*` flag (true only when every element of the list belongs to that category) and an `any_*` flag (true when at least one element belongs to it). The categories covered are: granted, denied (any denied sub-kind), permanently denied, should-show-rationale, and request-required. An empty-category list yields false for the corresponding flags; mixed lists let `any_*` be true while `all_*` is false.",
    "cases": [
        {
            "input": {"op": "aggregate_statuses", "statuses": [{"type": [a specific set of status type literals (includes runtime decision types) — ask the PM for the exact strings], "permission": "android.permission.SEND_SMS"}, {"type": [a specific set of status type literals (includes runtime decision types) — ask the PM for the exact strings], "permission": "android.permission.CALL_PHONE"}]},
            "expected_output": "count=2\nall_granted=true\nall_denied=false\nall_permanently_denied=false\nall_should_show_rationale=false\nall_request_required=false\nany_granted=true\nany_denied=false\nany_permanently_denied=false\nany_should_show_rationale=false\nany_request_required=false\n"
        },
        {
            "input": {"op": "aggregate_statuses", "statuses": [{"type": [a specific set of status type literals (includes runtime decision types) — ask the PM for the exact strings], "permission": "android.permission.SEND_SMS"}, {"type": [a specific set of status type literals (includes runtime decision types) — ask the PM for the exact strings], "permission": "android.permission.CALL_PHONE"}]},
            "expected_output": "count=2\nall_granted=false\nall_denied=false\nall_permanently_denied=false\nall_should_show_rationale=false\nall_request_required=false\nany_granted=true\nany_denied=true\nany_permanently_denied=true\nany_should_show_rationale=false\nany_request_required=false\n"
        }
    ]
}
```

---

### Feature 3: One-Shot Result Callback

**As a developer**, I want to register a callback that receives the result of a request exactly once and then detaches itself, so I avoid leaks and accidental re-entry without manual cleanup.

**Expected Behavior / Usage:**

A request can emit a sequence of result deliveries. A one-shot callback is registered on the request; registering it attaches exactly one listener. When the first delivery occurs, the callback fires with that delivery's status list and then removes itself, so any later deliveries reach no listeners and the callback never fires again. The input is the list of deliveries the request emits (each delivery is a list of status objects). The output reports: the listener count right after registration, the listener count immediately before each delivery, the total number of times the callback fired, the rendered contents of each fired callback (statuses as `type:permission` joined by commas, or `<empty>` for an empty result), and the listener count remaining at the end (which must be zero after the first delivery).

**Test Cases:** `rcb_tests/public_test_cases/feature3_one_shot_callback.json`

```json
{
    "description": "One-shot result callback on a permission request. A callback is registered on a request to receive a single result delivery; after the first delivery fires the callback, the callback auto-detaches so subsequent deliveries do not invoke it again. The input lists the sequence of result deliveries the request emits (each delivery is a list of permission statuses). The output reports the number of registered listeners right after registration, the number of listeners present immediately before each delivery, how many times the callback fired, the contents of each fired callback, and the number of listeners remaining at the end (which must be zero after the first delivery because the one-shot callback removes itself).",
    "cases": [
        {
            "input": {"op": "one_shot_result", "deliveries": [[{"type": [a specific set of status type literals (includes runtime decision types) — ask the PM for the exact strings], "permission": "android.permission.SEND_SMS"}, {"type": [a specific set of status type literals (includes runtime decision types) — ask the PM for the exact strings], "permission": "android.permission.CALL_PHONE"}]]},
            "expected_output": "listeners_after_register=1\ndelivery[0]_listeners_before=1\ncallbacks_fired=1\ncallback[0]=granted:android.permission.SEND_SMS,permanently_denied:android.permission.CALL_PHONE\nlisteners_remaining=0\n"
        },
        {
            "input": {"op": "one_shot_result", "deliveries": [[{"type": [a specific set of status type literals (includes runtime decision types) — ask the PM for the exact strings], "permission": "android.permission.SEND_SMS"}], [{"type": [a specific set of status type literals (includes runtime decision types) — ask the PM for the exact strings], "permission": "android.permission.CALL_PHONE"}]]},
            "expected_output": "listeners_after_register=1\ndelivery[0]_listeners_before=1\ndelivery[1]_listeners_before=0\ncallbacks_fired=1\ncallback[0]=granted:android.permission.SEND_SMS\nlisteners_remaining=0\n"
        }
    ]
}
```

---

### Feature 4: Request Builder & Configuration Validation

**As a developer**, I want a fluent builder that assembles a permission request and fails fast with a clear reason when required inputs are missing, so misconfiguration is caught immediately rather than surfacing as an obscure runtime fault.

**Expected Behavior / Usage:**

A request is assembled by a builder that requires two inputs before it can produce a request: the set of permissions to request, and a runtime handler provider. Permissions may be supplied either as a first-plus-rest sequence (`vararg`) or as a single `list`; both forms are equivalent. The builder validates **permissions first, then the handler provider**. If permissions were never supplied, building yields the normalized error category `missing_permissions`. If permissions were supplied but no handler provider was attached, building yields `missing_runtime_handler`. When both are present, building succeeds and the produced object conforms to the request abstraction. The input declares `permissions_mode` (`unset` / `vararg` / `list`), the permissions (when applicable), and whether a handler provider is attached. On success the output is `built=true` plus a confirmation that the result conforms to the request abstraction; on failure the output is a single `error=<category>` line.

**Test Cases:** `rcb_tests/public_test_cases/feature4_request_builder.json`

```json
{
    "description": "Build a permission request through the configuration builder and validate required configuration. The builder needs two things before it can produce a request: the set of permissions to request and a runtime handler provider. The input declares how permissions are supplied (`unset` = not supplied, `vararg` = supplied as a first-plus-rest sequence, `list` = supplied as a single list) and whether a handler provider is attached. On a valid configuration the output confirms the request was built and that it conforms to the request abstraction. On an invalid configuration the output is a normalized error category: `missing_permissions` when no permissions were supplied, or `missing_runtime_handler` when permissions were supplied but no handler provider was attached. Permissions are validated before the handler.",
    "cases": [
        {
            "input": {"op": "build_request", "permissions_mode": "unset", "provide_handler": true},
            "expected_output": "error=missing_permissions\n"
        },
        {
            "input": {"op": "build_request", "permissions_mode": "vararg", "permissions": ["android.permission.SEND_SMS"], "provide_handler": false},
            "expected_output": "error=missing_runtime_handler\n"
        },
        {
            "input": {"op": "build_request", "permissions_mode": "list", "permissions": ["android.permission.SEND_SMS"], "provide_handler": true},
            "expected_output": "built=true\nrequest_is_permission_request=true\n"
        }
    ]
}
```

---

### Feature 5: Listener Registry & Result Notification

**As a developer**, I want a request to maintain a set of listeners and notify exactly the listeners currently attached when a result is available, so multiple observers can subscribe and unsubscribe independently over the request's lifetime.

**Expected Behavior / Usage:**

A request holds a **set** of listeners (identified by a stable id). Attaching the same id twice has no extra effect (set semantics, not a multiset). A result notification is delivered to exactly the listeners attached at that moment. A listener can be detached individually, or all listeners can be detached at once; a detached listener receives no further results, and after detaching all, a subsequent notification reaches nobody. The input is an ordered list of operations: `add` a listener by id, `remove` one by id, `remove_all`, or `notify` with a result (a list of status objects). The output reports, for each notify in order, how many listeners received it; then the final listener count; then, per listener id (in id order), how many results it received and the rendered content of each received result. Statuses are rendered as `type:permission` joined by commas, or `<empty>` for an empty result.

**Test Cases:** `rcb_tests/public_test_cases/feature5_listener_registry.json`

```json
{
    "description": "Manage the listener registry of a permission request and notify all currently attached listeners. A request keeps a set of listeners; each `notify` delivers a result to exactly the listeners attached at that moment. Listeners are identified by a stable id; adding the same id twice has no extra effect (a set, not a multiset); a listener can be detached individually, or every listener can be detached at once. The input is an ordered list of operations: attach a listener (`add`), detach one (`remove`), detach all (`remove_all`), or emit a result to current listeners (`notify`). The output reports, for each notify, how many listeners received it; then the final listener count; then, per listener id, how many results it received and the content of each received result. A detached listener stops receiving results from that point on, and after detaching all, a subsequent notify reaches nobody.",
    "cases": [
        {
            "input": {"op": "listener_registry", "ops": [{"action": "add", "id": "A"}, {"action": "add", "id": "B"}, {"action": "notify", "result": [{"type": [a specific set of status type literals (includes runtime decision types) — ask the PM for the exact strings], "permission": "android.permission.ACCESS_FINE_LOCATION"}, {"type": [a specific set of status type literals (includes runtime decision types) — ask the PM for the exact strings], "permission": "android.permission.SEND_SMS"}]}]},
            "expected_output": "notify[0]_recipients=2\nlisteners=2\nreceived[A]_count=1\nreceived[A][0]=granted:android.permission.ACCESS_FINE_LOCATION,permanently_denied:android.permission.SEND_SMS\nreceived[B]_count=1\nreceived[B][0]=granted:android.permission.ACCESS_FINE_LOCATION,permanently_denied:android.permission.SEND_SMS\n"
        },
        {
            "input": {"op": "listener_registry", "ops": [{"action": "add", "id": "A"}, {"action": "add", "id": "B"}, {"action": "notify", "result": [{"type": [a specific set of status type literals (includes runtime decision types) — ask the PM for the exact strings], "permission": "p"}]}, {"action": "remove", "id": "A"}, {"action": "notify", "result": [{"type": [a specific set of status type literals (includes runtime decision types) — ask the PM for the exact strings], "permission": "p"}]}]},
            "expected_output": "notify[0]_recipients=2\nnotify[1]_recipients=1\nlisteners=1\nreceived[A]_count=1\nreceived[A][0]=granted:p\nreceived[B]_count=2\nreceived[B][0]=granted:p\nreceived[B][1]=granted:p\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the typed status model, predicate/quantifier helpers, request lifecycle (listener registry + one-shot callback), and validating builder described above. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads a single JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-feature contracts above. Native errors raised by the core (e.g. missing configuration) MUST be translated by the adapter into the normalized `error=<category>` lines; the adapter is the only place that performs this translation, and it must not leak host-language exception class names or runtime message text into stdout.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_status_classification.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_status_classification@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the inverse logic pattern used in the fallback_denial module
