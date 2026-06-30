## Product Requirement Document

# Notification Templating & Trigger Engine — Render Messages, Evaluate Triggers, and Resolve Subscriptions

## Project Goal

Build a reusable notification engine core that turns application state into delivered alerts: it renders human-readable messages from reusable templates, decides when an alert should fire by evaluating trigger conditions, and resolves which destinations (service plus recipient) an alert should be sent to based on subscription metadata — so an automation platform can wire arbitrary event sources to arbitrary delivery channels without hard-coding any of the message text, firing rules, or routing.

---

## Background & Problem

Automation platforms need to notify people when something noteworthy happens to a managed object (a deployment becomes healthy, a sync fails, a revision changes). Without a shared engine, every integration re-implements three error-prone concerns: formatting a message out of live data, deciding whether the current state actually warrants a notification, and figuring out who should receive it on which channel.

This engine factors those three concerns into pure, deterministic pieces. A templating step renders message text from named templates and a variable map. A trigger step evaluates ordered boolean conditions over the same variables and reports which templates each condition would send, plus an optional grouping value that lets the platform deliver a notification only once per distinct value (for example, once per deployment revision). A subscription step reads routing metadata expressed as annotation key/value pairs and expands it into a set of destinations grouped by trigger, with helpers to add, remove, and name those annotation entries. All three pieces are free of I/O and network access; delivery to concrete channels is out of scope.

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

### Feature 1: Notification Message Templating

**As a developer**, I want to render a notification's message from a named, reusable template and a map of runtime variables, so the same alert layout can be reused across many events while filling in live values.

**Expected Behavior / Usage:**

The input names a set of message templates (each identified by a name and carrying a message body), a list of template names to apply in order, and a map of variables. The engine renders the message body of the applied template(s) against the variables and returns the resulting text. The template body uses a curly-brace placeholder syntax: `{{.name}}` substitutes the value of variable `name`, dotted paths such as `{{.app.status}}` walk nested maps, and a pipe operator routes a value through a standard library of text helper functions (for example `{{.state | upper}}` upper-cases the value). The rendered text is reported as a single line prefixed with `message=`. If a name in the apply list does not correspond to any supplied template, the operation fails and reports a neutral error line `error=unsupported_template` followed by a line `template=<name>` naming the missing template.

**Test Cases:** `rcb_tests/public_test_cases/feature1_message_templating.json`

```json
{
    "description": "Render a notification message from a named message template. The caller supplies a set of named templates (each providing a message body written in a curly-brace placeholder syntax), a list of template names to apply in order, and a map of variables. The engine evaluates the selected template's body against the variables and returns the rendered message text. Placeholders are replaced by the corresponding variable values, including nested field access via dotted paths, and a standard library of text helper functions (for example, upper-casing a value) is available through a pipe operator. The output is the single line 'message=' followed by the fully rendered text.",
    "cases": [
        {
            "input": {
                "action": "format_notification",
                "templates": {"summary": {"message": "{{.foo}}"}},
                "apply": ["summary"],
                "vars": {"foo": "hello"}
            },
            "expected_output": "message=hello\n"
        },
        {
            "input": {
                "action": "format_notification",
                "templates": {"greeting": {"message": "Build {{.app}} is {{.state | upper}}"}},
                "apply": ["greeting"],
                "vars": {"app": "web", "state": "healthy"}
            },
            "expected_output": "message=Build web is HEALTHY\n"
        }
    ]
}
```

---

### Feature 2: Trigger Condition Evaluation

**As a developer**, I want to evaluate a trigger's ordered conditions against the current variables and learn which conditions fire and what they would send, so the platform can decide whether and how to notify.

**Expected Behavior / Usage:**

*2.1 Condition Firing — evaluating each condition's boolean expression*

A trigger holds an ordered list of conditions. Each condition carries a boolean expression written in a small expression language over the supplied variables (supporting comparisons, equality against quoted string literals, and references to variable names) and a list of template names to send when it fires. The engine evaluates each condition's expression in order against the variable map and reports, per condition and in order, whether it fired, the comma-separated list of template names it would send, and its grouping value (see 2.2; empty when no grouping expression is declared). A condition fires only when its expression evaluates to boolean `true`; an expression that evaluates to any non-`true` value, or that fails to evaluate at all (for instance because it references a variable that was not supplied), produces a not-fired result rather than an error. Each condition emits one line of the form `triggered=<bool> templates=<comma-separated> [logical grouping token logic]=<value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_condition_firing.json`

```json
{
    "description": "Evaluate the firing conditions of a trigger. A trigger holds an ordered list of conditions; each condition carries a boolean expression (written in a small expression language over the supplied variables) and a list of template names to send when it fires. Given the conditions and a variable map, the engine evaluates each condition's expression in order and reports, per condition, whether it fired, which template names it would send, and its grouping value (empty here). A condition fires only when its expression evaluates to boolean true; an expression that evaluates to a non-true value, or that fails to evaluate (for example because it references a variable that is absent), yields a not-fired result rather than an error. Each condition produces one output line of the form 'triggered=<bool> templates=<comma-separated> [logical grouping token logic]=<value>', in condition order.",
    "cases": [
        {
            "input": {
                "action": "run_trigger",
                "conditions": [{"when": "var1 == 'abc'", "send": ["deploy-alert"]}],
                "vars": {"var1": "abc"}
            },
            "expected_output": "triggered=true templates=deploy-alert [logical grouping token logic]=\n"
        },
        {
            "input": {
                "action": "run_trigger",
                "conditions": [{"when": "var1 == 'abc'", "send": ["deploy-alert"]}],
                "vars": {"var1": "bcd"}
            },
            "expected_output": "triggered=false templates=deploy-alert [logical grouping token logic]=\n"
        }
    ]
}
```

*2.2 Grouping Value ([logical grouping token logic]) — resolving a de-duplication key per condition*

In addition to its firing expression, a condition may declare a `[logical grouping token logic]` expression. When present, the engine evaluates that expression against the same variables and reports its result as a string in the `[logical grouping token logic]=` field; the platform uses this value to deliver a given notification at most once per distinct value (for example, once per deployment revision). The expression may be a bare variable reference or a richer lookup such as indexing into a nested map by a string key. When no `[logical grouping token logic]` expression is declared, the field is empty.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_once_per_grouping.json`

```json
{
    "description": "Compute a condition's de-duplication grouping value. In addition to its firing expression, a condition may declare a '[logical grouping token logic]' expression whose evaluated result is used to ensure a notification is only delivered once per distinct value (for example, once per deployment revision). When such an expression is present, the engine evaluates it against the supplied variables and reports the resulting value as a string alongside the firing result. The expression may be a bare variable reference or a richer lookup such as indexing into a nested map by key. The output line carries the fired flag, the templates to send, and the resolved grouping value in '[logical grouping token logic]='.",
    "cases": [
        {
            "input": {
                "action": "run_trigger",
                "conditions": [{"when": "var1 == 'abc'", "send": ["my-template"], "[logical grouping token logic]": "revision"}],
                "vars": {"var1": "abc", "revision": "123"}
            },
            "expected_output": "triggered=true templates=my-template [logical grouping token logic]=123\n"
        },
        {
            "input": {
                "action": "run_trigger",
                "conditions": [{"when": "var1 == 'abc'", "send": ["my-template"], "[logical grouping token logic]": "app.metadata.annotations[\"example.com/version\"]"}],
                "vars": {"var1": "abc", "app": {"metadata": {"annotations": {"example.com/version": "v0.1"}}}}
            },
            "expected_output": "triggered=true templates=my-template [logical grouping token logic]=v0.1\n"
        }
    ]
}
```

---

### Feature 3: Subscription Destination Resolution

**As a developer**, I want to expand subscription metadata into a concrete set of routed destinations grouped by trigger, so the platform knows exactly which service and recipient each trigger should notify.

**Expected Behavior / Usage:**

Subscriptions are expressed as annotation key/value pairs. A subscribe annotation key has the shape `<prefix>/subscribe.<trigger>.<service>` and its value is the recipient; the `<prefix>` defaults to the fixed namespace `[standard Argo Drive prefix configuration]`. The resolver expands every subscription into a mapping from trigger name to a list of `(service, recipient)` destinations using these rules: when a subscription names an explicit trigger, that trigger is used verbatim and any caller-supplied default triggers are ignored; when a subscription omits the trigger (key shaped as `<prefix>/subscribe.<service>`, with nothing between `subscribe.` and the service), the destination is attached to each of the caller-supplied default triggers — unless a per-service default trigger list is provided for that service, in which case those service-specific triggers are used instead of the global defaults. Each resulting destination is emitted as a line `trigger=<t> service=<s> recipient=<r>`, ordered by trigger and then by service and recipient.

**Test Cases:** `rcb_tests/public_test_cases/feature3_destination_resolution.json`

```json
{
    "description": "Resolve notification destinations from subscription annotations. Subscriptions are expressed as annotation keys of the form '<prefix>/subscribe.<trigger>.<service>' whose value is the recipient. The resolver expands every subscription into a mapping from trigger name to a list of (service, recipient) destinations, applying these rules: when a subscription names an explicit trigger, that trigger is used verbatim and any default triggers are ignored; when a subscription omits the trigger (key shaped as '<prefix>/subscribe.<service>'), the destination is attached to each of the caller-supplied default triggers, unless a per-service default trigger list is provided for that service, in which case those service-specific triggers are used instead. Each resulting destination is emitted as a line 'trigger=<t> service=<s> recipient=<r>', ordered by trigger then by service and recipient.",
    "cases": [
        {
            "input": {
                "action": "get_destinations",
                "annotations": {"[standard Argo Drive prefix configuration]/subscribe.my-trigger.slack": "my-channel"},
                "defaultTriggers": []
            },
            "expected_output": "trigger=my-trigger service=slack recipient=my-channel\n"
        },
        {
            "input": {
                "action": "get_destinations",
                "annotations": {"[standard Argo Drive prefix configuration]/subscribe.slack": "my-channel"},
                "defaultTriggers": ["trigger-a", "trigger-b", "trigger-c"]
            },
            "expected_output": "trigger=trigger-a service=slack recipient=my-channel\ntrigger=trigger-b service=slack recipient=my-channel\ntrigger=trigger-c service=slack recipient=my-channel\n"
        }
    ]
}
```

---

### Feature 4: Subscription Annotation Management

**As a developer**, I want to add and remove subscription recipients in the annotation metadata and derive the canonical annotation keys, so subscriptions can be edited programmatically and addressed consistently.

**Expected Behavior / Usage:**

*4.1 Add a subscription recipient*

Given an existing annotation map, a trigger, a service, and one or more recipients, the add operation records the subscription under the annotation key `<prefix>/subscribe.<trigger>.<service>`. If the key does not yet exist it is created with the new recipient(s); if it already exists, each new recipient is appended to the existing recipient list unless it is already present. Multiple recipients are stored as a single value joined by semicolons. The output lists the resulting annotation entries as `<key>=<value>` lines, sorted by key.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_add_subscription.json`

```json
{
    "description": "Add a recipient to a subscription, expressed as an annotation entry. Given an existing annotation map, a trigger, a service, and one or more recipients, the operation records the subscription under the annotation key '<prefix>/subscribe.<trigger>.<service>'. If the key does not yet exist it is created with the new recipient(s); if it already exists, each new recipient is appended to the existing recipient list unless it is already present, and the recipients are stored as a single value joined by semicolons. The output lists the resulting annotation entries as '<key>=<value>' lines, sorted by key.",
    "cases": [
        {
            "input": {
                "action": "subscribe",
                "annotations": {},
                "trigger": "my-trigger",
                "service": "slack",
                "recipients": ["my-channel1"]
            },
            "expected_output": "[standard Argo Drive prefix configuration]/subscribe.my-trigger.slack=my-channel1\n"
        },
        {
            "input": {
                "action": "subscribe",
                "annotations": {"[standard Argo Drive prefix configuration]/subscribe.my-trigger.slack": "my-channel1"},
                "trigger": "my-trigger",
                "service": "slack",
                "recipients": ["my-channel2"]
            },
            "expected_output": "[standard Argo Drive prefix configuration]/subscribe.my-trigger.slack=my-channel1;my-channel2\n"
        }
    ]
}
```

*4.2 Remove a subscription recipient*

Given an existing annotation map, a trigger, a service, and a recipient, the remove operation locates the subscription annotation for that trigger and service and removes the named recipient from its recipient list. If recipients remain after removal, the entry is kept with the updated value; if the removed recipient was the last one, the annotation entry is deleted entirely. The output lists the remaining annotation entries as `<key>=<value>` lines, sorted by key, and is empty when no annotations remain.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_remove_subscription.json`

```json
{
    "description": "Remove a recipient from a subscription annotation entry. Given an existing annotation map, a trigger, a service, and a recipient, the operation locates the subscription annotation for that trigger and service and removes the named recipient from its recipient list. If recipients remain after removal, the annotation entry is kept with the updated value; if the removed recipient was the last one, the annotation entry is deleted entirely. The output lists the remaining annotation entries as '<key>=<value>' lines, sorted by key; when the entry was deleted and no annotations remain, the output is empty.",
    "cases": [
        {
            "input": {
                "action": "unsubscribe",
                "annotations": {"[standard Argo Drive prefix configuration]/subscribe.my-trigger.slack": "my-channel1;my-channel2"},
                "trigger": "my-trigger",
                "service": "slack",
                "recipient": "my-channel1"
            },
            "expected_output": "[standard Argo Drive prefix configuration]/subscribe.my-trigger.slack=my-channel2\n"
        }
    ]
}
```

*4.3 Derive canonical annotation keys*

All annotation keys are built from a configurable prefix that defaults to the fixed namespace `[standard Argo Drive prefix configuration]` and can be overridden. The subscribe key for a given trigger and service has the shape `<prefix>/subscribe.<trigger>.<service>`. The notified key, used to record that a notification has already been delivered, has the shape `notified.<prefix>`. When a prefix override is supplied, it is applied before deriving both keys. The output reports the two derived keys on separate lines as `subscribe_key=<value>` and `notified_key=<value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_annotation_keys.json`

```json
{
    "description": "Derive the canonical annotation keys used by the subscription scheme. All keys are built from a configurable prefix that defaults to a fixed namespace and can be overridden. The subscribe key for a given trigger and service has the shape '<prefix>/subscribe.<trigger>.<service>'. The notified key, used to record that a notification has already been delivered, has the shape 'notified.<prefix>'. When a prefix override is supplied it is applied before deriving both keys. The output reports the two derived keys, one per line, as 'subscribe_key=<value>' and 'notified_key=<value>'.",
    "cases": [
        {
            "input": {
                "action": "annotation_key",
                "trigger": "my-trigger",
                "service": "slack"
            },
            "expected_output": "subscribe_key=[standard Argo Drive prefix configuration]/subscribe.my-trigger.slack\nnotified_key=notified.[standard Argo Drive prefix configuration]\n"
        },
        {
            "input": {
                "action": "annotation_key",
                "prefix": "test.prefix",
                "trigger": "on-deploy",
                "service": "email"
            },
            "expected_output": "subscribe_key=test.prefix/subscribe.on-deploy.email\nnotified_key=notified.test.prefix\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above (templating, trigger evaluation, and subscription resolution/management). Its physical structure MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the result to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `format_notification` renders a message from named templates and variables; `run_trigger` evaluates a trigger's conditions over variables; `get_destinations` resolves subscription annotations into routed destinations; `subscribe`/`unsubscribe` edit subscription annotation entries; `annotation_key` derives the canonical keys. Native errors must be normalized into neutral `error=<category>` lines in the adapter layer.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the deletion protocol described in the subscription cleanup module for empty lists
- order by the hierarchical keys in the destinations map
