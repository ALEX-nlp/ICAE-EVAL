## Product Requirement Document

# Unified Multi-Provider SMS Dispatch Library — Number Normalization, Message Modeling, Gateway Resolution & Provider Request Building

## Project Goal

Build a reusable library that gives developers a single, uniform way to format and dispatch short text messages through many different SMS provider back-ends, so they can model a recipient, a message, and a choice of providers once and let the library handle each provider's particular request shape, credentials, and error reporting without hand-coding every integration.

---

## Background & Problem

Sending SMS in real applications means integrating with multiple providers, each of which has its own endpoint, its own parameter names, its own way of encoding the recipient and the message, and its own success/error response format. Without a unifying layer, developers re-implement number formatting, per-provider request assembly, credential handling, and error translation again and again, and they end up with brittle, provider-specific code scattered across the codebase.

With this library, a developer describes the recipient (a local number plus an optional international dialing code), the message (content, template id, template variables, and a preferred set of providers), and a configuration map of credentials, and the library normalizes the number, models the message, resolves the requested provider, and assembles the exact outbound HTTP request that provider expects — surfacing provider failures as a single, normalized error category rather than leaking each provider's idiosyncrasies.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains. This domain (number model, message model, configuration accessor, gateway resolver, and several distinct provider integrations) is multi-responsibility and should be organized accordingly.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension (new providers) but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details (in particular, the HTTP transport must be an injectable seam so request assembly can be exercised without real network calls).

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result/Monad patterns) rather than relying on generic faults. Provider-reported failures must be normalized into a stable error category that does not leak the host language's runtime details.

---

## Core Features

### Feature 1: Phone Number Normalization

**As a developer**, I want to model a recipient number with an optional international dialing code and read it back in several canonical forms, so I can hand the right shape to each provider without re-deriving it.

**Expected Behavior / Usage:**

The input supplies a local `number` and an optional `idd_code` (the international dialing / country code). The code may be given as a bare integer, with a leading `+`, or with leading zeros; all such forms denote the same integer country code, and any leading `+` or `0` characters are stripped when parsing it. The component exposes: the raw local `number`; the parsed integer country code (reported empty when none was supplied); a `universal` form which is `+` followed by the country code followed by the number; a `zero_prefixed` form which is `00` followed by the country code followed by the number; and a JSON serialization which equals the universal form. When no country code is supplied, the universal and zero-prefixed forms are identical to the bare local number (no prefix is added).

**Test Cases:** `rcb_tests/public_test_cases/feature1_phone_number.json`

```json
{
    "description": "Normalize a subscriber phone number that may carry an international dialing (IDD) country code. The number is provided as the local number plus an optional IDD code; the code may be given as a bare integer, with a leading plus sign, or with leading zeros, and all three forms denote the same country code. The component exposes the raw local number, the parsed integer country code (empty when none was supplied), a '+'-prefixed universal form, a '00'-prefixed form, and a JSON serialization that equals the universal form. When no IDD code is present, the universal and zero-prefixed forms are identical to the bare local number.",
    "cases": [
        {
            "input": {"action": "phone_number", "number": 18888888888},
            "expected_output": "number=18888888888\nidd_code=\nuniversal=18888888888\nzero_prefixed=18888888888\njson={\"number\":\"18888888888\"}\n"
        },
        {
            "input": {"action": "phone_number", "number": 18888888888, "idd_code": 68},
            "expected_output": "number=18888888888\nidd_code=68\nuniversal=+6818888888888\nzero_prefixed=006818888888888\njson={\"number\":\"+6818888888888\"}\n"
        }
    ]
}
```

---

### Feature 2: Dot-Notation Configuration Access

**As a developer**, I want to read and mutate a nested configuration map with simple dotted keys, so I can pull credentials and settings out of arbitrarily nested structures without manual traversal.

**Expected Behavior / Usage:**

The input supplies a nested `config` map and a list of `operations`. A `get` resolves a key: a top-level key returns its value; a dotted key descends through nested maps and through numerically-indexed lists (so `numbers.0.id` reads index 0 of the `numbers` list); a key that cannot be resolved — or a null key — yields null. An `isset` reports whether a top-level key is present. A `set` updates the value of an already-present top-level key. An `unset` removes a present top-level key, after which a `get` of that key yields null. Each operation emits exactly one line: `get <key> => <json-value>` (null keys are shown as `(null)`, and resolved values are rendered as JSON), `isset <key> => true|false`, `set <key>`, or `unset <key>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_config_access.json`

```json
{
    "description": "Read from and mutate a nested configuration map using dot-notation keys. A `get` resolves a key against the map: a top-level key returns its value, a dotted key descends into nested maps and numerically-indexed lists, and a key that does not resolve (or a null key) yields null. An existence check reports whether a top-level key is present. An assignment updates the value of an already-present top-level key, and a removal deletes a present top-level key; after removal a subsequent read of that key returns null. Each operation emits one line describing its result, with scalar values rendered as JSON.",
    "cases": [
        {
            "input": {
                "action": "config",
                "config": {
                    "foo": "bar",
                    "bar": {"screen_name": "somebody", "profile": {"id": 9999, "name": "overtrue"}},
                    "numbers": [{"id": 1, "number": 1}, {"id": 2, "number": 2}]
                },
                "operations": [
                    {"op": "isset", "key": "foo"},
                    {"op": "get", "key": "foo"},
                    {"op": "get", "key": null},
                    {"op": "get", "key": "bar.profile.id"},
                    {"op": "get", "key": "bar.profile.name"},
                    {"op": "get", "key": "numbers.0.id"},
                    {"op": "get", "key": "numbers.0.number"},
                    {"op": "get", "key": "numbers.1.id"},
                    {"op": "get", "key": "numbers.1.number"},
                    {"op": "set", "key": "foo", "value": "new-bar"},
                    {"op": "get", "key": "foo"},
                    {"op": "unset", "key": "foo"},
                    {"op": "get", "key": "foo"}
                ]
            },
            "expected_output": "isset foo => true\nget foo => \"bar\"\nget (null) => null\nget bar.profile.id => 9999\nget bar.profile.name => \"overtrue\"\nget numbers.0.id => 1\nget numbers.0.number => 1\nget numbers.1.id => 2\nget numbers.1.number => 2\nset foo\nget foo => \"new-bar\"\nunset foo\nget foo => null\n"
        }
    ]
}
```

---

### Feature 3: Message Envelope Construction

**As a developer**, I want to describe a message either as a bare string or as a structured object, so simple cases stay terse while richer cases can carry a template id, template variables, and preferred providers.

**Expected Behavior / Usage:**

The input supplies a `message`. When it is a bare string, that string becomes both the content and the template identifier. When it is a structured object, the supplied attributes — `content`, `template`, template `data`, and the list of preferred `gateways` — are stored as given. In all cases the message `type` defaults to text, content and template default to empty, template data defaults to an empty collection, and the preferred-gateway list defaults to empty. The component reports the resolved type, content, template, template data (as JSON), and gateway list (as JSON).

**Test Cases:** `rcb_tests/public_test_cases/feature3_message.json`

```json
{
    "description": "Construct a message envelope. When the message is supplied as a bare string, that string becomes both the message content and the template identifier. When supplied as a structured object, the individual attributes (content, template, template data, and the list of preferred gateways) are stored as given. In all cases the message type defaults to text, content and template default to empty, template data defaults to an empty collection, and the preferred-gateway list defaults to empty. The component reports the resolved type, content, template, template data, and gateway list.",
    "cases": [
        {
            "input": {"action": "message", "message": "文本"},
            "expected_output": "type=text\ncontent=文本\ntemplate=文本\ndata=[]\ngateways=[]\n"
        },
        {
            "input": {"action": "message", "message": {"content": "hello", "template": "SMS_001", "data": {"code": "1234"}, "gateways": ["yunpian", "aliyun"]}},
            "expected_output": "type=text\ncontent=hello\ntemplate=SMS_001\ndata={\"code\":\"1234\"}\ngateways=[\"yunpian\",\"aliyun\"]\n"
        }
    ]
}
```

---

### Feature 4: Gateway Resolution

**As a developer**, I want to resolve a delivery gateway by a short name (or fall back to a configured default), and to get a clear, normalized error when the name is unknown or no default exists, so misconfiguration fails fast.

**Expected Behavior / Usage:**

*4.1 Resolve a gateway by name (or default) — successful resolution*

The input supplies an optional `default` gateway name and an optional `gateway` name to resolve. A short name is mapped to a built-in provider; on success the gateway's canonical lower-case name is reported as `name=<value>`. The short name is matched case-insensitively and ignoring hyphens/underscores (for example `error-log` resolves to the provider whose canonical name is `errorlog`). When no `gateway` name is requested but a `default` was configured, the default is resolved instead.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_gateway_resolve.json`

```json
{
    "description": "Resolve a delivery gateway by its short name. A short name is mapped to a built-in gateway provider and, on success, the gateway's canonical lower-case name is reported. The resolver may also be configured with a default gateway up front; when no explicit name is requested, the default is resolved instead.",
    "cases": [
        {
            "input": {"action": "gateway_resolve", "gateway": "error-log"},
            "expected_output": "name=errorlog\n"
        },
        {
            "input": {"action": "gateway_resolve", "default": "errorlog"},
            "expected_output": "name=errorlog\n"
        }
    ]
}
```

*4.2 Unknown gateway name — normalized error*

When the requested `gateway` name does not correspond to any known built-in provider, resolution fails and emits a neutral, language-independent error: an `error=invalid_gateway` line followed by a `name=<requested>` line carrying the offending name. No host-language exception type or message is leaked.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_unknown_gateway.json`

```json
{
    "description": "Attempt to resolve a gateway by a name that does not correspond to any known built-in provider. Resolution fails and a neutral error category is reported together with the offending requested name.",
    "cases": [
        {
            "input": {"action": "gateway_resolve", "gateway": "NotExistsGatewayName"},
            "expected_output": "error=invalid_gateway\nname=NotExistsGatewayName\n"
        }
    ]
}
```

*4.3 No default configured — normalized error*

When the default gateway is requested (no explicit name) but none has been configured, resolution fails fast and emits a single `error=no_default_gateway` line.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_no_default_gateway.json`

```json
{
    "description": "Request the default gateway when none has been configured. Resolution fails fast with a neutral error category indicating that no default gateway is available.",
    "cases": [
        {
            "input": {"action": "gateway_resolve"},
            "expected_output": "error=no_default_gateway\n"
        }
    ]
}
```

---

### Feature 5: Gateway Timeout Resolution

**As a developer**, I want a resolved gateway to compute its effective request timeout from configuration with a sensible default and an explicit override, so I can control latency behavior consistently across providers.

**Expected Behavior / Usage:**

The input supplies a `config` map (used to build the resolver), the `gateway` to resolve, and an optional `set_timeout` override. The effective timeout (in seconds) is determined by precedence: an explicit per-instance override (`set_timeout`), if provided, wins; otherwise a `timeout` value present in configuration is used; otherwise a built-in default of 5 seconds applies. The effective timeout is reported as `timeout=<value>` rendered with one decimal place.

**Test Cases:** `rcb_tests/public_test_cases/feature5_gateway_timeout.json`

```json
{
    "description": "Determine the effective request timeout (in seconds) of a resolved gateway. When the configuration specifies no timeout, a built-in default of 5 seconds applies. A timeout supplied in the configuration overrides the default. An explicit per-instance timeout override, once set, takes precedence over both. The effective timeout is reported as a one-decimal value.",
    "cases": [
        {
            "input": {"action": "gateway_timeout", "config": {}, "gateway": "aliyun"},
            "expected_output": "timeout=5.0\n"
        },
        {
            "input": {"action": "gateway_timeout", "config": {"timeout": 12.0}, "gateway": "aliyun"},
            "expected_output": "timeout=12.0\n"
        },
        {
            "input": {"action": "gateway_timeout", "config": {}, "gateway": "aliyun", "set_timeout": 4.0},
            "expected_output": "timeout=4.0\n"
        }
    ]
}
```

---

### Feature 6: Provider Request Building

**As a developer**, I want each provider integration to assemble exactly the outbound HTTP request that provider expects from a recipient, a message, and a credential config, and to normalize the provider's reply into either an accepted outcome or a single error category, so I can rely on uniform behavior across very different provider APIs.

**Expected Behavior / Usage:**

For each provider, the input supplies the `gateway` name, a credential `config`, the recipient `to` (same shape as Feature 1), the `message` (same shape as Feature 3), and a canned provider `response` (the JSON body the provider would return) with an optional `response_status` (default 200). The library assembles the request via the provider's own logic and the canned response is fed back through the provider's normal response handling, exercising request assembly without a live network. The output reports the request `method`, the endpoint `url` (without query string), then one `param.<name>=<value>` line per request parameter sorted by parameter name (query parameters for GET, form/body parameters for POST), then the outcome: `outcome=sent` on acceptance, or `outcome=error` followed by `error_code=<code>` and `error_message=<message>` when the provider reply indicates failure. The error code and message are the provider's own domain values; no host-language runtime detail is included.

*6.1 Form-encoded single-send provider with signature-prefix rule*

This provider POSTs `apikey`, the recipient's universal number as `mobile`, and the message `text` to a fixed single-send endpoint. A configured `signature` is prepended to the text only when the text does not already begin with the signature bracket character `【`; text that already begins with `【` is sent unchanged. The reply carries a numeric `code`: zero means accepted; any non-zero code becomes an error whose `error_code` is that code and whose `error_message` is the reply's `msg`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_yunpian_request.json`

```json
{
    "description": "Build the outbound HTTP request for a form-encoded SMS provider whose single-send endpoint takes an API key, the recipient's universal number, and the message text. A configured signature prefix is prepended to the text only when the text does not already begin with the signature-bracket character; text that already starts with that bracket is sent unchanged. The provider's JSON reply carries a numeric result code: a zero code means accepted, and any non-zero code is surfaced as a normalized gateway error carrying that code and the provider's message. The output reports the request method, endpoint URL, the sorted form parameters, and the outcome.",
    "cases": [
        {
            "input": {"action": "gateway_send", "gateway": "yunpian", "config": {"api_key": "mock-api-key", "signature": "【测试】"}, "to": {"number": 18188888888}, "message": {"content": "This is a 【test】 message."}, "response": {"code": 0, "msg": "ok"}},
            "expected_output": "method=POST\nurl=https://sms.yunpian.com/v2/sms/single_send.json\nparam.apikey=mock-api-key\nparam.mobile=18188888888\nparam.text=【测试】This is a 【test】 message.\noutcome=sent\n"
        },
        {
            "input": {"action": "gateway_send", "gateway": "yunpian", "config": {"api_key": "mock-api-key"}, "to": {"number": 18188888888}, "message": {"content": "【overtrue】This is a test message."}, "response": {"code": 100, "msg": "发送失败"}},
            "expected_output": "method=POST\nurl=https://sms.yunpian.com/v2/sms/single_send.json\nparam.apikey=mock-api-key\nparam.mobile=18188888888\nparam.text=【overtrue】This is a test message.\noutcome=error\nerror_code=100\nerror_message=发送失败\n"
        }
    ]
}
```

*6.2 International provider with account id in the endpoint path*

This provider interpolates the configured `account_sid` into a per-account messages endpoint path and POSTs the recipient in `+`-prefixed universal form as `To`, the configured sender as `From`, and the message as `Body`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_twilio_request.json`

```json
{
    "description": "Build the outbound HTTP request for an international form-encoded SMS provider. The account identifier is interpolated into the per-account messages endpoint path, and the request carries the recipient in '+'-prefixed universal form together with the configured sender and the message body. The output reports the request method, endpoint URL, the sorted form parameters, and the outcome.",
    "cases": [
        {
            "input": {"action": "gateway_send", "gateway": "twilio", "config": {"account_sid": "mock-api-account-sid", "from": "mock-from", "token": "mock-token"}, "to": {"number": 18888888888, "idd_code": 86}, "message": {"content": "【twilio】This is a test message."}, "response": {"status": "queued", "from": "mock-from", "to": "+8618888888888", "body": "【twilio】This is a test message.", "sid": "mock-api-account-sid", "error_code": null}},
            "expected_output": "method=POST\nurl=https://api.twilio.com/2010-04-01/Accounts/mock-api-account-sid/Messages.json\nparam.Body=【twilio】This is a test message.\nparam.From=mock-from\nparam.To=+8618888888888\noutcome=sent\n"
        }
    ]
}
```

*6.3 Template provider using HTTP GET query parameters*

This provider GETs the recipient's local `mobile`, the `tpl_id` template identifier, the template variables as `tpl_value` (URL-encoded as a query string whose keys are each variable name wrapped in `#…#`), a `dtype` response-format flag set to `json`, and the API `key`. The reply carries a numeric `error_code`: zero means accepted; non-zero becomes an error whose `error_message` is the reply's `reason`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_juhe_request.json`

```json
{
    "description": "Build the outbound HTTP request for a template-based SMS provider that uses an HTTP GET with query parameters. The query carries the recipient's local number, the template identifier, the template variables (URL-encoded as a '#name#'-keyed query string), a JSON response-format flag, and the API key. The provider's JSON reply carries a numeric error code: zero means accepted, and any non-zero code is surfaced as a normalized gateway error with that code and the provider's reason. The output reports the request method, endpoint URL, the sorted query parameters, and the outcome.",
    "cases": [
        {
            "input": {"action": "gateway_send", "gateway": "juhe", "config": {"app_key": "mock-key"}, "to": {"number": 18188888888}, "message": {"content": "This is a test message.", "template": "mock-tpl-id", "data": {"code": 1234}}, "response": {"reason": "操作成功", "error_code": 0}},
            "expected_output": "method=GET\nurl=http://v.juhe.cn/sms/send\nparam.dtype=json\nparam.key=mock-key\nparam.mobile=18188888888\nparam.tpl_id=mock-tpl-id\nparam.tpl_value=%23code%23=1234\noutcome=sent\n"
        },
        {
            "input": {"action": "gateway_send", "gateway": "juhe", "config": {"app_key": "mock-key"}, "to": {"number": 18188888888}, "message": {"content": "x", "template": "mock-tpl-id", "data": {"code": 1234}}, "response": {"reason": "操作失败", "error_code": 21000}},
            "expected_output": "method=GET\nurl=http://v.juhe.cn/sms/send\nparam.dtype=json\nparam.key=mock-key\nparam.mobile=18188888888\nparam.tpl_id=mock-tpl-id\nparam.tpl_value=%23code%23=1234\noutcome=error\nerror_code=21000\nerror_message=操作失败\n"
        }
    ]
}
```

*6.4 Project provider with region-based endpoint selection*

This provider selects its endpoint by the recipient's region: a recipient with no country code or the mainland country code (86) routes to the domestic send endpoint, while any other country code routes to the international send endpoint. It POSTs the `appid`, the `signature` credential, the `project` id (taken from message data when present, otherwise from configuration), the recipient in `+`-prefixed universal form as `to`, and the template variables encoded as a JSON object string in `vars`. The reply carries a `status`: a `success` status means accepted; any other status becomes an error whose `error_code` is the reply's `code` and whose `error_message` is the reply's `msg`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_4_submail_request.json`

```json
{
    "description": "Build the outbound HTTP request for a project-based SMS provider whose endpoint is selected by the recipient's region: recipients with no country code or the mainland country code route to the domestic send endpoint, while any other country code routes to the international send endpoint. The form parameters carry the application id, the signature credential, the project id (taken from the message data when present, otherwise from configuration), the recipient in '+'-prefixed universal form, and the template variables encoded as a JSON object. The provider's JSON reply carries a status: a success status means accepted, and any other status is surfaced as a normalized gateway error with the reply's code and message. The output reports the request method, endpoint URL, the sorted form parameters, and the outcome.",
    "cases": [
        {
            "input": {"action": "gateway_send", "gateway": "submail", "config": {"app_id": "mock-app-id", "app_key": "mock-app-key", "project": "mock-project"}, "to": {"number": 18188888888}, "message": {"data": {"code": "123456", "time": "15"}}, "response": {"status": "success", "send_id": "093c0a7df143c087d6cba9cdf0cf3738", "fee": 1, "sms_credits": 14197}},
            "expected_output": "method=POST\nurl=https://api.mysubmail.com/message/xsend.json\nparam.appid=mock-app-id\nparam.project=mock-project\nparam.signature=mock-app-key\nparam.to=18188888888\nparam.vars={\"code\":\"123456\",\"time\":\"15\"}\noutcome=sent\n"
        },
        {
            "input": {"action": "gateway_send", "gateway": "submail", "config": {"app_id": "mock-app-id", "app_key": "mock-app-key", "project": "mock-project"}, "to": {"number": 18188888888, "idd_code": 1}, "message": {"data": {"code": "123456", "time": "15"}}, "response": {"status": "success", "send_id": "093c0a7df143c087d6cba9cdf0cf3738", "fee": 1, "sms_credits": 14197}},
            "expected_output": "method=POST\nurl=https://api.mysubmail.com/internationalsms/xsend.json\nparam.appid=mock-app-id\nparam.project=mock-project\nparam.signature=mock-app-key\nparam.to=+118188888888\nparam.vars={\"code\":\"123456\",\"time\":\"15\"}\noutcome=sent\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the features above — a recipient number model, a message model, a dot-notation configuration accessor, a gateway resolver with a pluggable set of provider integrations, and the per-provider request builders. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing, and the HTTP transport must be an injectable seam so each provider's request assembly and response handling can be exercised with a canned reply instead of a live call.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the result to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `phone_number`, `config`, `message`, `gateway_resolve`, `gateway_timeout`, and `gateway_send`. For `gateway_send`, the adapter injects the supplied canned `response` (with optional `response_status`) into the provider's HTTP seam, drives the provider's real request assembly and response handling, then renders the captured outbound request and the normalized outcome. All provider-reported failures must be rendered as the neutral `outcome=error` / `error_code` / `error_message` contract (and resolution failures as `error=<category>`), never leaking host-language runtime details.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use standard JSON path syntax for nested lookups
- apply gentle name normalization rules
