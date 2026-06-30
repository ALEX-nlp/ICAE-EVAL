## Product Requirement Document

# Isomorphic Web Component Framework Primitives — URL Routing, HTML Tag Tokenization, Cookies, and a Server-Side Module API

## Project Goal

Build the foundational primitives of an isomorphic (server-and-browser) web component framework that allows developers to map request URLs to per-store application state, tokenize HTML start tags, manage cookies, name and resolve components, and expose a small server-side module API — without re-implementing routing, parsing, and cookie handling by hand for every application.

---

## Background & Problem

Without these primitives, developers building a component-based, server-rendered web framework are forced to hand-roll URL parameter extraction, write ad-hoc HTML attribute parsers, manually format and parse cookie headers, and reinvent component-naming conventions for every project. This leads to repetitive, error-prone boilerplate, inconsistent edge-case handling (trailing slashes, percent-encoding, malformed tags, missing cookies), and tight coupling between request handling and rendering.

With this library, the framework offers a single coherent set of building blocks: a declarative route language that distributes URL parameters into named state buckets, a standards-aligned HTML start-tag tokenizer, a cookie reader/writer, deterministic component name conversions, and a server-side API that records deferred actions (redirects, fragment clearing, cookie writes) and replays them as an inline browser script.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility system (routing, tokenization, cookie handling, naming helpers, a server-side action API). It MUST be organized as a clear multi-file tree separating these concerns; it MUST NOT be a single "god file". Do not over-engineer, but keep each concern in its own cohesive unit.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a **black-box contract for the execution adapter**, not the internal data model. Core logic MUST be decoupled from stdin/stdout and JSON parsing. The execution adapter alone translates a JSON command into idiomatic calls on the core and renders the result.

3. **Adherence to SOLID Design Principles:** Separate parsing, routing, validation, core execution, and output formatting into distinct units; keep the core open for extension but closed for modification; keep interfaces small and cohesive; depend on abstractions rather than I/O details.

4. **Robustness & Interface Design:** The public interface MUST be idiomatic and hide internal complexity. Edge cases (non-string inputs, malformed tags, missing cookies, non-matching URLs) MUST be handled gracefully. Invalid inputs surface as neutral, domain-level error categories rather than leaking runtime internals.

---

## Core Features

### Feature 1: Component Naming & Method Resolution

**As a developer**, I want deterministic conversions between component names, element tag names, and the methods to invoke on a component module, so I can wire components to markup and behavior consistently.

**Expected Behavior / Usage:**

*1.1 Error-template name — derive the name of a component's "error" rendering variant*

Given a component's base name (a string), produce the lookup name of its error variant by appending the reserved error suffix `--error`. If the base name is not a string, produce an empty name. Output is the resulting name followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_error_template_name.json`

```json
{
	"description": "Derive the lookup name of a component's error variant from its base name; a non-string base yields an empty name.",
	"cases": [
		{ "input": { "op": "component_error_template_name", "name": "some" }, "expected_output": "some--error\n" },
		{ "input": { "op": "component_error_template_name", "name": null }, "expected_output": "\n" }
	]
}
```

*1.2 camelCase identifier — normalize an identifier, with an optional prefix*

Given an optional prefix and a raw name, join them (when a prefix is present) and collapse the result into a single camelCase token: runs of non-alphanumeric separators are removed and the following letter is uppercased; leading/trailing separators are trimmed. An empty/falsy name yields an empty token. Output is the token followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_camel_case_name.json`

```json
{
	"description": "Normalize an arbitrary identifier (with separators, optional prefix) into a single camelCase token; an empty identifier yields an empty token.",
	"cases": [
		{ "input": { "op": "component_camel_case_name", "prefix": "some", "name": "awesome-module_name" }, "expected_output": "someAwesomeModuleName\n" },
		{ "input": { "op": "component_camel_case_name", "prefix": null, "name": "awesome-module-name-" }, "expected_output": "awesomeModuleName\n" }
	]
}
```

*1.3 Original component name — strip the reserved prefix from a tag name*

Given a custom-element tag name, recover the original lowercase component name by stripping the reserved component prefix (`cat-`, case-insensitive). The reserved document tag (`HTML`) and head tag (`HEAD`) map back to `document` and `head` respectively. A non-string yields an empty name. Output is the name followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_original_component_name.json`

```json
{
	"description": "Recover the original lowercase component name from a custom-element tag name, stripping the reserved component prefix; a non-string yields an empty name.",
	"cases": [
		{ "input": { "op": "component_original_name", "tag": "CAT-SOME" }, "expected_output": "some\n" },
		{ "input": { "op": "component_original_name", "tag": null }, "expected_output": "\n" }
	]
}
```

*1.4 Tag name — map a component name to its element tag name*

Given a component name, produce the element tag name: the `head` component keeps the uppercased reserved tag `HEAD`, the `document` component uses the reserved tag `HTML`, and every other component is uppercased and given the reserved component prefix `CAT-`. A non-string yields an empty name. Output is the tag name followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_tag_name.json`

```json
{
	"description": "Map a component name to its element tag name: the document and head components use reserved tag names, every other component is uppercased and prefixed; a non-string yields an empty name.",
	"cases": [
		{ "input": { "op": "component_tag_name", "name": "some" }, "expected_output": "CAT-SOME\n" },
		{ "input": { "op": "component_tag_name", "name": "document" }, "expected_output": "HTML\n" }
	]
}
```

*1.5 Method resolution — choose the handler to invoke on a module*

Given a module object, a method prefix, and an entity name, resolve the handler to call: prefer a method whose name is the camelCase join of prefix and entity name; otherwise, if a method named exactly after the prefix exists, use it and pass the entity name as its argument; otherwise fall back to a no-op that resolves asynchronously with no value. The `module` field selects which module shape is presented to the resolver: `"named"` exposes the prefixed camelCase method (returns `hello` immediately), `"default"` exposes only the generic prefix method (returns `hello:<name>` immediately), `"empty"` exposes neither, and `"null"` is not an object — both of the latter fall back to the deferred no-op. Output is two lines: `kind=immediate` or `kind=deferred` (whether the resolved call produced a value synchronously or returned a thenable), then `result=<value>` (the value, or `undefined` for the no-op).

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_method_resolution.json`

```json
{
	"description": "Resolve the handler to invoke on a module object given a prefix and entity name: a prefixed camelCase method is preferred, then a generic prefix method receiving the entity name, otherwise a no-op that resolves with no value. The output marks whether the resolved call returned a value immediately or deferred.",
	"cases": [
		{ "input": { "op": "component_method_resolution", "module": "named", "prefix": "some", "name": "method-to-invoke" }, "expected_output": "kind=immediate\nresult=hello\n" },
		{ "input": { "op": "component_method_resolution", "module": "empty", "prefix": "some", "name": "method-to-invoke" }, "expected_output": "kind=deferred\nresult=undefined\n" }
	]
}
```

---

### Feature 2: URL Routing

**As a developer**, I want to declare routes with named parameters and match request URLs to structured application state, so I can drive per-store state from the URL without manual parsing.

**Expected Behavior / Usage:**

*2.1 Trailing-slash normalization — remove a single trailing slash from a path*

Given a URL string, remove exactly one trailing slash from the path portion while preserving any query (`?…`) or fragment (`#…`) suffix. A bare root path `/` is returned unchanged (including `/#hash` and `/?arg=some`). A non-string input yields an empty string. Output is the resulting URL followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_trim_trailing_slash.json`

```json
{
	"description": "Remove a single trailing slash from a URL path while preserving a query or fragment suffix; a bare root path and non-string inputs are handled specially.",
	"cases": [
		{ "input": { "op": "trim_trailing_slash", "uri": "http:///some/ggg/dsd/" }, "expected_output": "http:///some/ggg/dsd\n" },
		{ "input": { "op": "trim_trailing_slash", "uri": "/" }, "expected_output": "/\n" }
	]
}
```

*2.2 Route-to-state mapping — compile route patterns and resolve a URL to per-store state*

A route pattern is a URL-shaped string in which a parameter is written as `:name[StoreA, StoreB, …]`: the `name` is the parameter and the bracketed list names the stores that receive it. Parameters may appear in the path and in query-string values, and may be embedded among literal characters (e.g. `w:arg1[…]q`). Given a list of route patterns and a request URL, compile the patterns and match the URL against them in order, using the first whose path matches. Produce a state object mapping each store name to an object of its parameter values. Rules: path parameters are always captured when the path matches; a query parameter is captured only when present in both the route and the URL; a query key appearing multiple times yields an array value (in URL order); percent-encoded characters in captured values are decoded; when the same parameter name targets the same store from both path and query, the query value overrides; query keys not declared in the route are ignored, and routes whose query side declares no parameters contribute only path state. If no route's path matches (or there are no routes, or the URL is not a usable string), the state is `null`. Output is the state serialized as canonical JSON (object keys sorted) followed by a newline; the absence of any match is the literal `null`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_route_state.json`

```json
{
	"description": "Compile colon-parameter route patterns and match a request URL against them, producing a per-store state map where each named parameter is distributed to the stores listed in its brackets. Path and query parameters, partial-literal parameters, repeated (array) query parameters, percent-encoded values, parameter overriding, and non-matching URLs are all covered.",
	"cases": [
		{ "input": { "op": "route_state", "routes": ["/state/:arg1[Store1, Store2]/:arg2[Store2]?a=:arg3[Store1]&b=:arg4[Store3]"], "uri": "/state/val1/val2?a=val3&b=val4" }, "expected_output": "{\"Store1\":{\"arg1\":\"val1\",\"arg3\":\"val3\"},\"Store2\":{\"arg1\":\"val1\",\"arg2\":\"val2\"},\"Store3\":{\"arg4\":\"val4\"}}\n" },
		{ "input": { "op": "route_state", "routes": ["/state/:arg1[Store1, Store2]/:arg2[Store2]?a=:arg3[Store1]&b=:arg4[Store3]"], "uri": "/none/val1/val2?a=val3&b=val4" }, "expected_output": "null\n" }
	]
}
```

---

### Feature 3: HTML Start-Tag Tokenization

**As a developer**, I want to tokenize a single HTML start tag into typed segments, so I can read tag names and attributes during component discovery and rendering.

**Expected Behavior / Usage:**

Given the source of a single HTML start tag, emit a stream of tokens, each identified by a state name and carrying the exact source substring it spans. Token states cover: `TAG_OPEN` (`<`), `TAG_NAME`, whitespace boundaries (`BEFORE_ATTRIBUTE_NAME`, `AFTER_ATTRIBUTE_NAME`), `ATTRIBUTE_NAME`, the equals/quote lead-in (`BEFORE_ATTRIBUTE_VALUE`), the three attribute-value modes (`ATTRIBUTE_VALUE_DOUBLE_QUOTED`, `ATTRIBUTE_VALUE_SINGLE_QUOTED`, `ATTRIBUTE_VALUE_UNQUOTED`), the closing quote (`AFTER_ATTRIBUTE_VALUE_QUOTED`), the self-closing marker (`SELF_CLOSING_START_TAG_STATE`, `/`), and the terminal `TAG_CLOSE` (`>`). Tokenization runs until it reaches `TAG_CLOSE` or `ILLEGAL`; any malformed construct (bad first character, NUL byte, missing tag end, unterminated quote, illegal character where an attribute name/value is expected) terminates the stream with an `ILLEGAL` token whose value marks the offending position (empty when input ends prematurely). Boolean attributes (no value) and whitespace runs are preserved as their own tokens. Output is one line per token, `STATE <json-quoted-substring>`, each followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature3_tokenize_tag.json`

```json
{
	"description": "Tokenize a single HTML start tag into a stream of typed segments (tag open, tag name, attribute names/values in their quoting modes, whitespace boundaries, self-closing marker, close). Malformed input terminates with an ILLEGAL segment marking the offending position.",
	"cases": [
		{ "input": { "op": "tokenize_tag", "html": "<tag>" }, "expected_output": "TAG_OPEN \"<\"\nTAG_NAME \"tag\"\nTAG_CLOSE \">\"\n" },
		{ "input": { "op": "tokenize_tag", "html": "<>" }, "expected_output": "TAG_OPEN \"<\"\nILLEGAL \">\"\n" }
	]
}
```

---

### Feature 4: Cookie Management

**As a developer**, I want to read, write, and serialize cookies, so I can manage session and preference state on both server and browser.

**Expected Behavior / Usage:**

*4.1 Read a cookie value by name*

Given a raw cookie header string and a name, return the matching cookie value. A non-string name, an absent (null) header, a malformed header, or a name not present all yield an empty value. Output is the value followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_cookie_get.json`

```json
{
	"description": "Read a single cookie value by name from a raw cookie header string; a missing name, a non-string name, an absent header, or a malformed header all return an empty value.",
	"cases": [
		{ "input": { "op": "cookie_get", "cookieString": "some=value; some2=value2", "key": "some" }, "expected_output": "value\n" },
		{ "input": { "op": "cookie_get", "cookieString": null, "key": "some" }, "expected_output": "\n" }
	]
}
```

*4.2 Serialize cookie definitions into Set-Cookie strings*

Given a list of cookie definitions, serialize each into a Set-Cookie header string. Each definition has a `key` and `value` (both required strings) plus optional `maxAge` (seconds), `expires` (a date), `path`, `domain`, and the boolean flags `secure` and `httpOnly`. Attributes are emitted in fixed order: `key=value`, then `Max-Age`, `Expires` (as a UTC string), `Path`, `Domain`, `Secure`, `HttpOnly`, each present only when supplied. A definition whose key or value is not a string is rejected and reported as the neutral error category `invalid_cookie`. Output is one serialized string per cookie, each followed by a newline (or the single error line).

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_cookie_set.json`

```json
{
	"description": "Serialize one or more cookie definitions (name, value, max-age, expiry, path, domain, secure, http-only flags) into Set-Cookie header strings in attribute order; a non-string name or value is rejected as an invalid cookie.",
	"cases": [
		{ "input": { "op": "cookie_set", "cookies": [ { "key": "some", "value": "value", "maxAge": 100, "expires": "2016-02-23T19:57:16.000Z", "domain": ".new.domain", "path": "/some", "secure": true, "httpOnly": true } ] }, "expected_output": "some=value; Max-Age=100; Expires=Tue, 23 Feb 2016 19:57:16 GMT; Path=/some; Domain=.new.domain; Secure; HttpOnly\n" },
		{ "input": { "op": "cookie_set", "cookies": [ { "key": {} } ] }, "expected_output": "error=invalid_cookie\n" }
	]
}
```

*4.3 Build the combined cookie header string*

Given an initial cookie header string and a list of cookies to add, build the combined header: the initial string followed by each added `key=value` pair, joined by the standard `; ` separator. Output is the combined header followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_cookie_string.json`

```json
{
	"description": "Build the combined cookie header string from an initial header plus any cookies added afterward, joined with the standard separator.",
	"cases": [
		{ "input": { "op": "cookie_string", "initString": "some=value; some2=value2", "cookies": [ { "key": "some3", "value": "value3" }, { "key": "some4", "value": "value4" } ] }, "expected_output": "some=value; some2=value2; some3=value3; some4=value4\n" }
	]
}
```

*4.4 Parse the combined cookie header into a map*

Given an initial cookie header string and a list of cookies to add, parse the resulting combined header into a name-to-value map. Output is the map serialized as canonical JSON (keys sorted) followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_cookie_all.json`

```json
{
	"description": "Parse the combined cookie header into a name-to-value map.",
	"cases": [
		{ "input": { "op": "cookie_all", "initString": "some=value; some2=value2", "cookies": [] }, "expected_output": "{\"some\":\"value\",\"some2\":\"value2\"}\n" }
	]
}
```

---

### Feature 5: Server-Side Module API

**As a developer**, I want a server-side API that reports the runtime environment, brokers event subscriptions, and records deferred page actions, so components can interact with the framework uniformly and have their actions replayed in the browser.

**Expected Behavior / Usage:**

*5.1 Environment flags — report the runtime*

The server-side API exposes two boolean environment flags. Querying `isBrowser` yields false and `isServer` yields true. Output is `<flag>=<value>` followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_environment_flags.json`

```json
{
	"description": "Report the runtime environment flags exposed by the server-side API provider.",
	"cases": [
		{ "input": { "op": "environment_flag", "flag": "isBrowser" }, "expected_output": "isBrowser=false\n" },
		{ "input": { "op": "environment_flag", "flag": "isServer" }, "expected_output": "isServer=true\n" }
	]
}
```

*5.2 Event subscription — subscribe, fire, and remove handlers on a shared bus*

The API brokers subscriptions to a shared event bus. A sequence of operations is applied: `on` adds a persistent handler, `once` adds a one-shot handler, `removeListener` removes a specific handler, `removeAllListeners` removes every handler for an event, and `emit` fires an event with arguments. Handlers are referenced by symbolic id (`rec`, `rec2`); each records every invocation's arguments. A persistent handler fires on every matching emission, a one-shot handler fires only on the first, and removed handlers do not fire. Output is `invocations=<count>` followed by one `arg=<canonical-json-array>` line per recorded invocation, each terminated by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_event_subscription.json`

```json
{
	"description": "Subscribe handlers to a shared event bus through the API provider and observe how many times they fire when events are emitted: a persistent subscription fires every emission, a one-shot subscription fires only once, and a removed handler does not fire.",
	"cases": [
		{ "input": { "op": "event_api", "ops": [ { "action": "on", "event": "event", "handler": "rec" }, { "action": "emit", "event": "event", "args": ["hello"] } ] }, "expected_output": "invocations=1\narg=[\"hello\"]\n" },
		{ "input": { "op": "event_api", "ops": [ { "action": "once", "event": "event", "handler": "rec" }, { "action": "emit", "event": "event", "args": ["hello"] }, { "action": "emit", "event": "event", "args": ["world"] } ] }, "expected_output": "invocations=1\narg=[\"hello\"]\n" }
	]
}
```

*5.3 Event validation — reject malformed subscription calls*

Subscription and removal calls validate their arguments: the event name must be a string and (for `on`/`once`/`removeListener`) the handler must be a function. A non-string event name is rejected as the neutral category `invalid_event_name`; a non-function handler is rejected as `invalid_event_handler`. The handler id `notfunction` denotes a non-function value. Output is the single error line.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_event_validation.json`

```json
{
	"description": "Reject subscription and removal calls whose event name is not a string or whose handler is not a function, reporting a neutral validation error category.",
	"cases": [
		{ "input": { "op": "event_api", "ops": [ { "action": "on", "event": "some", "handler": "notfunction" } ] }, "expected_output": "error=invalid_event_handler\n" },
		{ "input": { "op": "event_api", "ops": [ { "action": "on", "event": {}, "handler": "rec" } ] }, "expected_output": "error=invalid_event_name\n" }
	]
}
```

*5.4 Redirect tracking — remember the last redirect target*

The API records deferred redirects. Given a sequence of redirect targets, it remembers the most recent one. Output is `redirected_to=<last-uri>` followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature5_4_redirect_tracking.json`

```json
{
	"description": "Track the most recent redirect target requested through the API provider across a sequence of redirect calls.",
	"cases": [
		{ "input": { "op": "redirect_tracking", "uris": ["/some1", "/some2"] }, "expected_output": "redirected_to=/some2\n" }
	]
}
```

*5.5 Clear-fragment tracking — record a request to clear the URL fragment*

The API records a deferred request to clear the URL fragment. The clear flag starts false and becomes true after the request. Output is two lines: `cleared_before=<flag>` then `cleared_after=<flag>`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_5_clear_fragment.json`

```json
{
	"description": "Track the flag indicating that a request to clear the URL fragment has been made, before and after the call.",
	"cases": [
		{ "input": { "op": "clear_fragment" }, "expected_output": "cleared_before=false\ncleared_after=true\n" }
	]
}
```

*5.6 Inline replay script — render deferred actions as a browser script*

The API renders the deferred actions it has accumulated into a single inline browser script that replays them: a redirect becomes a location assignment, each queued cookie becomes a document-cookie write, and a fragment-clear becomes a hash reset. Single quotes and backslashes within values are escaped, and any literal script-tag sequence inside a value is neutralized. Output is the script string followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature5_6_inline_script.json`

```json
{
	"description": "Produce the inline browser script that replays deferred server-side actions: assigning a redirect location, writing queued cookies, and clearing the URL fragment. Script-tag sequences inside values are neutralized.",
	"cases": [
		{ "input": { "op": "inline_script", "ops": [ { "action": "redirect", "uri": "http://some" } ] }, "expected_output": "<script>window.location.assign('http://some');</script>\n" },
		{ "input": { "op": "inline_script", "ops": [ { "action": "set_cookie", "cookie": { "key": "some1", "value": "value1" } }, { "action": "set_cookie", "cookie": { "key": "some2", "value": "value2" } } ] }, "expected_output": "<script>window.document.cookie = 'some1=value1';window.document.cookie = 'some2=value2';</script>\n" }
	]
}
```

---

### Feature 6: Callback-to-Promise Adaptation

**As a developer**, I want to adapt a Node-style callback function into a promise-returning function, so I can compose legacy callback APIs with promise-based code.

**Expected Behavior / Usage:**

Given a function whose final argument is a callback invoked as `(error, result)`, produce a function that returns a promise: when the callback reports success the promise resolves with the result, and when it reports an error the promise rejects with that error. The `callback` field models the underlying function's outcome: an object with a `result` field models a successful callback carrying that value, and an object with an `error` field models a failing callback carrying that error message. Output is `resolved=<value>` on success or `rejected=<message>` on failure, followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature6_callback_to_promise.json`

```json
{
	"description": "Adapt a Node-style callback function (final argument receives error-or-result) into a function returning a promise: a successful callback resolves with the result, an error callback rejects with the error message.",
	"cases": [
		{ "input": { "op": "callback_to_promise", "callback": { "result": "hello" } }, "expected_output": "resolved=hello\n" },
		{ "input": { "op": "callback_to_promise", "callback": { "error": "hello" } }, "expected_output": "rejected=hello\n" }
	]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the routing, tokenization, cookie, naming, and server-side-API primitives above, decoupled from standard I/O and JSON.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout exactly matching the per-leaf-feature contracts above, with all invalid inputs surfaced as the neutral `error=<category>` lines specified. This adapter must be separated from the core domain.

3. **Automated test harness:** A single entry point `bash rcb_tests/test.sh` that reads every `*.json` case file from a case directory and runs the full suite, accepting `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{stem}@{index:03}.txt` containing only the raw program stdout, comparable directly against `expected_output`.


---
**Implementation notes:**
- follow the same numeric precision rules as the financial ledger parser module
- use the same truthy/falsy logic applied in the environment checks module
