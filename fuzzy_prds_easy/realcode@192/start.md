## Product Requirement Document

# Build Notification Dispatch Library - Chat Workspace Messaging

## Project Goal

Build a notification-dispatch library that lets a continuous-integration system turn build events into well-formed chat-workspace messages and deliver them to one or more channels, without each job having to hand-craft message markup or talk to the chat HTTP API directly. The library owns three concerns: rendering safe message text in the workspace's display dialect, composing build-status lines, and routing/delivering those messages to the right upstream endpoint.

---

## Background & Problem

Without this library, every job that wants to announce its progress in a team chat must re-implement the same fiddly logic: escaping user-supplied build and commit text so that stray angle brackets, ampersands, or embedded HTML links do not corrupt the chat message; deciding which upstream URL and request shape to use depending on whether messages go through an incoming webhook or a bot account; fanning a single announcement out to several channels; and interpreting transport responses to know whether the announcement actually landed. This leads to duplicated, error-prone boilerplate scattered across pipelines, and to broken or unsafe messages whenever someone's branch name or pull-request title contains markup.

With this library, a job hands over plain values — a project name, a build name, a list of channels, a credential — and gets back correctly escaped text and a single delivery call that handles endpoint selection, multi-channel fan-out, and success reporting.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain has several distinct responsibilities — text rendering, status-line composition, endpoint routing, HTTP transport, and configuration state — so it MUST be organized into clear, separately testable units rather than a single monolithic file. Do not over-engineer, but do not collapse independent concerns together either.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases in the "Core Features" section are a black-box contract for an execution adapter, NOT the internal data model. The core rendering, routing, and delivery logic MUST be usable through ordinary in-language calls and MUST NOT depend on stdin/stdout or JSON parsing. The execution adapter is the only component that translates JSON commands into core calls and renders results to stdout.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Keep escaping, status-line building, endpoint routing, transport, and result formatting in distinct units.
   - **Open/Closed Principle (OCP):** New sending modes or message decorations should be addable without rewriting existing delivery logic.
   - **Liskov Substitution Principle (LSP):** The HTTP transport must be replaceable (e.g. with an in-memory recorder) without changing delivery behavior.
   - **Interface Segregation Principle (ISP):** Keep the message-sender interface small and cohesive.
   - **Dependency Inversion Principle (DIP):** Delivery logic depends on a transport abstraction, not on a concrete HTTP client.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public surface must be elegant and natural for the target language, hiding the escaping and routing details.
   - **Resilience:** Transport failures must never propagate as crashes to the calling job; a failed delivery is reported as an outcome, not thrown. Unrecognized commands and malformed input are reported as neutral error categories.

---

## Core Features

### Feature 1: Message Text Escaping

**As a developer**, I want arbitrary build and commit text rendered into the chat workspace's safe display dialect, so I can embed user-controlled strings in a notification without breaking its markup.

**Expected Behavior / Usage:**

The escaper takes one free-text string and returns the chat-safe rendering. Two transformations apply. First, an HTML anchor of the form `<a href='URL'>LABEL</a>` is collapsed into the workspace's inline-link syntax `<URL|LABEL>`, with surrounding quote characters on the URL preserved as written. Second, the three characters the chat protocol reserves — `&`, `<`, `>` — are entity-encoded to `&amp;`, `&lt;`, `&gt;` respectively, so any non-anchor markup is shown literally rather than interpreted. Characters that are NOT reserved, including percent signs and curly braces, pass through unchanged. The command is `{"op":"escape","text":<raw text>}` and the program prints a single line `escaped=<rendered text>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_message_escaping.json`

```json
{
    "description": "Escape arbitrary notification text into the chat workspace's display dialect: HTML anchor tags become inline links, the angle brackets and ampersand that the chat protocol reserves are entity-encoded, and ordinary punctuation such as percent signs and curly braces pass through untouched. The command is {\"op\":\"escape\",\"text\":<raw text>} and the program prints a single line `escaped=<rendered text>`.",
    "cases": [
        {
            "input": {"op": "escape", "text": "<a href='target'>test</a>"},
            "expected_output": "escaped=<'target'|test>\n"
        },
        {
            "input": {"op": "escape", "text": "something { is } odd"},
            "expected_output": "escaped=something { is } odd\n"
        }
    ]
}
```

---

### Feature 2: Build Start-Line Composition

**As a developer**, I want a one-line opening message built from a project name and a build name, so I can announce that a build has started with a consistent, safe header.

**Expected Behavior / Usage:**

The composer takes a project display name and a build display name and renders the line `<project> - <build> `, with exactly one trailing space after the build name. The build name is passed through the same escaping rules described in Feature 1, so an embedded anchor collapses into an inline link and any reserved markup is entity-encoded. Empty names are allowed and simply produce empty segments, yielding ` -  ` for two empty inputs. The command is `{"op":"start_message","project_name":<name>,"build_name":<name>}` and the program prints `message=<rendered line>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_start_message.json`

```json
{
    "description": "Compose the opening line of a build notification from a project's display name and a build's display name. The line is rendered as `<project> - <build> ` (note the single trailing space), and the build name is passed through the same escaping rules as free text, so anchor tags collapse into inline links and reserved markup characters are entity-encoded. The command is {\"op\":\"start_message\",\"project_name\":<name>,\"build_name\":<name>} and the program prints `message=<rendered line>`.",
    "cases": [
        {
            "input": {"op": "start_message", "project_name": "project", "build_name": "#43 Started by changes from Bob"},
            "expected_output": "message=project - #43 Started by changes from Bob \n"
        },
        {
            "input": {"op": "start_message", "project_name": "project", "build_name": "#541 <a href=\"https://bitbucket.org/org/project/pull-request/125\">#125 Bug</a>"},
            "expected_output": "message=project - #541 <https://bitbucket.org/org/project/pull-request/125|#125 Bug> \n"
        },
        {
            "input": {"op": "start_message", "project_name": "project", "build_name": "#541 <b>Bold Project</b>"},
            "expected_output": "message=project - #541 &lt;b&gt;Bold Project&lt;/b&gt; \n"
        }
    ]
}
```

---

### Feature 3: Message Delivery

**As a developer**, I want a single delivery call that sends a message to one or more channels and reports whether it arrived, so I do not have to manage HTTP requests, multi-channel fan-out, or response interpretation myself.

**Expected Behavior / Usage:**

*3.1 Channel Fan-Out & Delivery Outcome — multi-channel dispatch and success reporting*

The sender accepts a channel string that may name several channels separated by commas, semicolons, or spaces, and fires exactly one HTTP request per named channel. An empty channel string still produces a single request to an empty target. Delivery is reported as successful only when every request returns HTTP 200; if any request returns a non-200 status, or responses alternate between success and failure across multiple channels, the overall delivery is reported as failed. A failing transport never crashes the call — it is always surfaced as a boolean outcome. The command is `{"op":"publish","mode":"webhook","team_domain":<d>,"token":<t>,"channel":<c>,"status":<status the transport returns>,"fail_alternate":<bool>}` and the program prints `requests=<n>`, then `delivered=<bool>`, then one `[the exact multi-line output structure for requested URLs — check PRD example]<url>` line per request (the routed URL is described in 3.2).

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_delivery_fanout.json`

```json
{
    "description": "Deliver a notification to one or more chat channels over HTTP and report transport-level outcomes. The target channel string may name several channels separated by commas/semicolons/spaces; the sender fires exactly one HTTP request per channel. Delivery is considered successful only when every request returns HTTP 200; any non-200 response (or an alternating-failure pattern across multiple channels) makes the overall delivery fail. The command is {\"op\":\"publish\",\"mode\":\"webhook\",\"team_domain\":<d>,\"token\":<t>,\"channel\":<c>,\"status\":<http status the transport returns>,\"fail_alternate\":<bool>} and the program prints `requests=<n>`, `delivered=<bool>`, and one `[the exact multi-line output structure for requested URLs — check PRD example]<url>` line per request.",
    "cases": [
        {
            "input": {"op": "publish", "mode": "webhook", "base_url": "", "team_domain": "domain", "token": "token", "channel": "#room1,#room2,#room3", "status": 200},
            "expected_output": "requests=3\ndelivered=true\n[the exact multi-line output structure for requested URLs — check PRD example]https://domain.slack.com/services/hooks/jenkins-ci?token=token\n[the exact multi-line output structure for requested URLs — check PRD example]https://domain.slack.com/services/hooks/jenkins-ci?token=token\nrequest_3_url=https://domain.slack.com/services/hooks/jenkins-ci?token=token\n"
        },
        {
            "input": {"op": "publish", "mode": "webhook", "base_url": "", "team_domain": "domain", "token": "token", "channel": "#room1", "status": 404},
            "expected_output": "requests=1\ndelivered=false\n[the exact multi-line output structure for requested URLs — check PRD example]https://domain.slack.com/services/hooks/jenkins-ci?token=token\n"
        },
        {
            "input": {"op": "publish", "mode": "webhook", "base_url": "", "team_domain": "domain", "token": "token", "channel": "#room1,#room2,#room3", "status": 200, "fail_alternate": true},
            "expected_output": "requests=3\ndelivered=false\n[the exact multi-line output structure for requested URLs — check PRD example]https://domain.slack.com/services/hooks/jenkins-ci?token=token\n[the exact multi-line output structure for requested URLs — check PRD example]https://domain.slack.com/services/hooks/jenkins-ci?token=token\nrequest_3_url=https://domain.slack.com/services/hooks/jenkins-ci?token=token\n"
        }
    ]
}
```

*3.2 Endpoint Routing by Mode — choosing the upstream URL and request shape*

The sending mode selects which upstream endpoint each request targets. In `webhook` mode, the message is posted to the team's incoming-webhook path derived from the team domain (`https://<team_domain>.slack.com/services/hooks/jenkins-ci?token=<token>`). In `bot` mode, the message is posted to the chat post-message API (`https://slack.com/api/chat.postMessage`) with the channel, link-name expansion, and as-user flags encoded as query parameters, and the leading `#` is stripped from the channel name. When the channel carries a thread timestamp after a colon (`channel:timestamp`), `bot` mode appends a thread parameter so the message lands inside that thread. The command is `{"op":"publish","mode":"webhook"|"bot","team_domain":<d>,"token":<t>,"channel":<c>,"status":200}` and the program prints `requests=1`, `delivered=true`, and `[the exact multi-line output structure for requested URLs — check PRD example]<routed url>`; the message-payload query segment is omitted from the reported URL so only routing-relevant parameters appear.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_endpoint_routing.json`

```json
{
    "description": "Select the upstream endpoint and request shape from the sending mode. In webhook mode the message is posted to the team's incoming-webhook path derived from the team domain. In bot mode the message is posted to the chat post-message API with the channel, link-name expansion and as-user flags encoded as query parameters; the leading '#' is stripped. When the channel carries a thread timestamp after a colon (channel:timestamp), bot mode adds a thread parameter. The command is {\"op\":\"publish\",\"mode\":\"webhook\"|\"bot\",\"team_domain\":<d>,\"token\":<t>,\"channel\":<c>,\"status\":200} and the program prints `requests=1`, `delivered=true`, and `[the exact multi-line output structure for requested URLs — check PRD example]<routed url>`.",
    "cases": [
        {
            "input": {"op": "publish", "mode": "bot", "base_url": "", "team_domain": "domain", "token": "token", "channel": "#room1", "status": 200},
            "expected_output": "requests=1\ndelivered=true\n[the exact multi-line output structure for requested URLs — check PRD example]https://slack.com/api/chat.postMessage?token=token&channel=room1&link_names=1&as_user=true\n"
        },
        {
            "input": {"op": "publish", "mode": "bot", "base_url": "", "team_domain": "domain", "token": "token", "channel": "#room1:1528317530", "status": 200},
            "expected_output": "requests=1\ndelivered=true\n[the exact multi-line output structure for requested URLs — check PRD example]https://slack.com/api/chat.postMessage?token=token&channel=room1&link_names=1&as_user=true&[a specific timestamp format string — check Slack API requirements]\n"
        }
    ]
}
```

---

### Feature 4: Custom-Message Slot Population Check

**As a developer**, I want to know whether any custom-message override has been configured, so I can decide whether to append a custom note to a notification.

**Expected Behavior / Usage:**

The configuration exposes several optional custom-message slots: a default slot plus per-outcome overrides keyed `success`, `aborted`, `not_built`, `unstable`, and `failure`. The check returns true as soon as at least one provided slot holds a non-empty string, and false when every provided slot is empty or absent. The command is `{"op":"custom_message_populated","slots":{<slot>:<text>,...}}` and the program prints `any_populated=<bool>` followed by `populated_slots=<comma-separated names of the slots that held non-empty text, in default,success,aborted,not_built,unstable,failure order>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_custom_message_populated.json`

```json
{
    "description": "Report whether any custom-message slot has been filled. A notification config exposes several optional custom-message slots (a default one plus per-outcome overrides for success, aborted, not-built, unstable and failure). The check answers true as soon as at least one slot holds a non-empty string, and false when every provided slot is empty or absent. The command is {\"op\":\"custom_message_populated\",\"slots\":{<slot>:<text>,...}} and the program prints `any_populated=<bool>` followed by `populated_slots=<comma-separated slot names that held non-empty text>`.",
    "cases": [
        {
            "input": {"op": "custom_message_populated", "slots": {}},
            "expected_output": "any_populated=false\npopulated_slots=\n"
        },
        {
            "input": {"op": "custom_message_populated", "slots": {"default": "hi", "failure": "hii"}},
            "expected_output": "any_populated=true\npopulated_slots=default,failure\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the escaping, status-line composition, endpoint routing, multi-channel delivery, and custom-message configuration described above. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint, keeping the distinct responsibilities in separately testable units without over-engineering.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads one JSON command object from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-feature contracts above. Transport for delivery must be injectable so requests can be recorded in-memory. The adapter must be logically (and ideally physically) separated from the core domain, and it is the only place where native runtime errors are normalized into the neutral `error=<category>` lines.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_message_escaping.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_message_escaping@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the behavior described in the delivery fan-out section above
- delivered status logic similar to standard delivery logic
