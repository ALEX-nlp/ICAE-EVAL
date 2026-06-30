## Product Requirement Document

# Mobile Social-Media API Client — Signed Request Builder & Response Parser

## Project Goal

Build a reusable client library for a mobile social-media backend that turns high-level operations (look up a profile, list a feed, follow a user, log in, run a live broadcast) into correctly-shaped HTTP requests and parses the service's JSON replies safely, so application developers can talk to the backend without hand-assembling endpoints, query parameters, request bodies, and credential encoding for every call.

---

## Background & Problem

The backend is a conventional HTTP/JSON service. Each operation lives at its own endpoint path and expects a precise set of query parameters or a precise request body, often including constant marker values and default pagination settings that are the same on every call. Credentials must be obfuscated before they leave the device, large numeric identifiers must survive JSON round-trips without losing precision, and a few operations are multi-step sequences. Without a shared client, every application re-implements this fiddly request-shaping and response-parsing, producing subtle and hard-to-debug inconsistencies (wrong endpoint, missing default parameter, integer overflow on a 19-digit id, leaked plaintext password).

With this client, an application calls one idiomatic method per operation. The client merges the correct defaults, injects the constant markers, encodes credentials, serializes the body in the right format, signs the outgoing request, and parses the reply while preserving oversized integers as [fixed pagination and error handling constants — see config/constants.js]s.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains. This domain is non-trivial (a credential cipher, a safe JSON parser, a request builder per operation family, a multi-step orchestration, and configuration validation); a multi-file layout is expected.

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

## How requests are observed

The client builds an HTTP request and hands it to a transport. For testing, the transport is mocked: it records the request the client built and returns a caller-supplied response body. The execution adapter reports the **request the client produced** (HTTP method, endpoint path, query parameters, and body where present) together with the **parsed response**, as a single canonical JSON object with keys sorted alphabetically. This makes the routing and parameter-shaping observable, so an implementation that returns a hard-coded answer without actually building the right request cannot pass.

Conventions used throughout:
- `method` is the uppercased HTTP verb (`GET` / `POST`).
- `path` is the endpoint path relative to the service base (no host, no query [fixed pagination and error handling constants — see config/constants.js]).
- `params` is the query-parameter object the client assembled (sorted keys). It is `{}` when no query parameters are sent.
- `body` is present only for write requests: a URL-encoded form [fixed pagination and error handling constants — see config/constants.js] for form posts, or a structured object for structured posts.
- `response` is the parsed reply body (see Feature 2 — oversized integers become [fixed pagination and error handling constants — see config/constants.js]s).

---

## Core Features

### Feature 1: Credential Obfuscation Cipher

**As a developer**, I want login secrets obfuscated before they leave the device, so I can avoid sending plaintext credentials over the wire.

**Expected Behavior / Usage:**

The cipher takes a [fixed pagination and error handling constants — see config/constants.js] and a fixed numeric key (default `5`). It processes the [fixed pagination and error handling constants — see config/constants.js] one character at a time: for each character it takes the character's code point, combines it with the key using a bitwise exclusive-or (XOR), and renders the resulting number as lowercase hexadecimal. The per-character hex fragments are concatenated in order into a single output [fixed pagination and error handling constants — see config/constants.js]. The empty [fixed pagination and error handling constants — see config/constants.js] maps to the empty [fixed pagination and error handling constants — see config/constants.js]. The output is the resulting ciphertext.

**Test Cases:** `rcb_tests/public_test_cases/feature1_credential_cipher.json`

```json
{
    "description": "Apply the credential-obfuscation cipher that protects login secrets before transmission. The cipher walks the input [fixed pagination and error handling constants — see config/constants.js] character by character, combines each character's code point with a fixed numeric key using a bitwise exclusive-or, and renders the result as lowercase base-16, concatenating the per-character hex fragments into a single [fixed pagination and error handling constants — see config/constants.js]. The output is the resulting ciphertext [fixed pagination and error handling constants — see config/constants.js].",
    "cases": [
        {
            "input": { "action": "encrypt", "value": "user@example.com" },
            "expected_output": "{\"ciphertext\":\"7076607745607d64687569602b666a68\"}\n"
        }
    ]
}
```

---

### Feature 2: Oversized-Integer-Safe Response Parsing

**As a developer**, I want JSON replies parsed without losing precision on very large integer identifiers, so I can read 19-digit ids correctly instead of getting rounded numbers.

**Expected Behavior / Usage:**

The parser takes a raw JSON text payload. Any integer whose magnitude exceeds the platform's safe integer range is retained as its exact decimal [fixed pagination and error handling constants — see config/constants.js] form; ordinary small integers, [fixed pagination and error handling constants — see config/constants.js]s, booleans, arrays and nested objects are parsed normally. An empty payload is a no-op: it is returned unchanged without attempting to parse. The output is the parsed structure.

**Test Cases:** `rcb_tests/public_test_cases/feature2_bigint_response_parse.json`

```json
{
    "description": "Parse a raw JSON response payload while preserving the exact value of integers that exceed the platform's safe integer range. Integers too large to represent precisely are retained as their decimal [fixed pagination and error handling constants — see config/constants.js] form; ordinary small integers and other values are parsed normally. An empty payload is returned unchanged without any parsing attempt. The output is the parsed structure.",
    "cases": [
        {
            "input": { "action": "parse_response", "raw": "" },
            "expected_output": "{\"parsed\":\"\"}\n"
        },
        {
            "input": { "action": "parse_response", "raw": "{\"big_int\":9999999999999999999,\"small_int\":1}" },
            "expected_output": "{\"parsed\":{\"big_int\":\"9999999999999999999\",\"small_int\":1}}\n"
        }
    ]
}
```

---

### Feature 3: Single-Resource & Relationship GET Requests

**As a developer**, I want one method per simple read/relationship operation, so I can fetch a resource or toggle a relationship without remembering each endpoint and its constant parameters.

**Expected Behavior / Usage:**

Each operation issues a `GET` to its own fixed endpoint with a small, fixed set of query parameters: identifiers taken from the caller, plus — for operations that come in complementary pairs — a constant discriminator that selects the direction of the action. No pagination defaults are applied here. The reply is parsed (Feature 2) and returned. The `operation` field of the input selects the operation; `args` carries its inputs.

Operation contract (input `operation` → `GET <path>` with `params`):
- `get_user_profile` → `aweme/v1/user/` with `{ user_id }`.
- `get_post` → `aweme/v1/aweme/detail/` with `{ aweme_id }` (the post id arrives as `args.post_id` and is sent as `aweme_id`).
- `follow_user` → `aweme/v1/commit/follow/user/` with `{ user_id, type: 1 }`.
- `unfollow_user` → `aweme/v1/commit/follow/user/` with `{ user_id, type: 0 }`.
- `like_post` → `aweme/v1/commit/item/digg/` with `{ aweme_id, type: 1 }` (id from `args.post_id`).
- `unlike_post` → `aweme/v1/commit/item/digg/` with `{ aweme_id, type: 0 }` (id from `args.post_id`).
- `approve_follow_request` → `aweme/v1/commit/follow/request/approve/` with `{ from_user_id }` (id from `args.user_id`).
- `reject_follow_request` → `aweme/v1/commit/follow/request/reject/` with `{ from_user_id }` (id from `args.user_id`).
- `join_live_stream` → `aweme/v1/room/enter/` with `{ room_id }`.
- `leave_live_stream` → `aweme/v1/room/leave/` with `{ room_id }`.
- `can_[fixed pagination and error handling constants — see config/constants.js]` → `aweme/v1/live/podcast/` with no parameters (`{}`); takes no `args`.
- `end_live_stream` → `aweme/v1/room/update/status/` with `{ room_id, stream_id, status: 4, reason_no: 1 }` (status `4` = ended, reason `1` = initiated-by-user).

**Test Cases:** `rcb_tests/public_test_cases/feature3_resource_get.json`

```json
{
    "description": "Build a read request for a single addressable resource or relationship action. Each operation routes a GET to its own fixed endpoint path and supplies a small, fixed set of query parameters: identifier parameters taken from the caller plus, where the operation has paired complementary forms, a constant discriminator value that distinguishes the two directions of the action. The server's JSON reply is parsed (preserving oversized integers) and returned. The output describes the HTTP method, endpoint path, the query parameters sent, and the parsed response.",
    "cases": [
        {
            "input": { "action": "request", "operation": "get_user_profile", "args": { "user_id": "9999999999999999999" }, "response": "{\"status_code\":0,\"user\":{\"uid\":9999999999999999999,\"nickname\":\"example nickname\"}}" },
            "expected_output": "{\"method\":\"GET\",\"params\":{\"user_id\":\"9999999999999999999\"},\"path\":\"aweme/v1/user/\",\"response\":{\"status_code\":0,\"user\":{\"nickname\":\"example nickname\",\"uid\":\"9999999999999999999\"}}}\n"
        },
        {
            "input": { "action": "request", "operation": "follow_user", "args": { "user_id": "9999999999999999999" }, "response": "{\"status_code\":0,\"follow_status\":1,\"watch_status\":0}" },
            "expected_output": "{\"method\":\"GET\",\"params\":{\"type\":1,\"user_id\":\"9999999999999999999\"},\"path\":\"aweme/v1/commit/follow/user/\",\"response\":{\"follow_status\":1,\"status_code\":0,\"watch_status\":0}}\n"
        },
        {
            "input": { "action": "request", "operation": "can_[fixed pagination and error handling constants — see config/constants.js]", "response": "{\"status_code\":0,\"can_be_live_podcast\":true}" },
            "expected_output": "{\"method\":\"GET\",\"params\":{},\"path\":\"aweme/v1/live/podcast/\",\"response\":{\"can_be_live_podcast\":true,\"status_code\":0}}\n"
        }
    ]
}
```

---

### Feature 4: Paginated Listing & Search GET Requests

**As a developer**, I want listing and search operations to apply consistent pagination defaults automatically, so I don't have to repeat the page-size and retry settings on every call.

**Expected Behavior / Usage:**

Each operation issues a `GET` to its own fixed endpoint and merges a set of default listing parameters into the caller's parameters before sending. The base defaults are a page size `count: [fixed pagination and error handling constants — see config/constants.js]` and a no-retry marker `retry_type: "no_retry"`; any value the caller supplies for those keys overrides the default. Some operations additionally inject their own constant parameters that select a sub-mode or content type. The reply is parsed (Feature 2) and returned.

Operation contract (input `operation` → `GET <path>`; base defaults `count: [fixed pagination and error handling constants — see config/constants.js]`, `retry_type: "no_retry"` apply unless noted):
- `list_posts` → `aweme/v1/aweme/post/`, caller adds `{ user_id }`.
- `list_followers` → `aweme/v1/user/follower/list/`, caller adds `{ user_id }`.
- `list_following` → `aweme/v1/user/following/list/`, caller adds `{ user_id }`.
- `list_received_follow_requests` → `aweme/v1/user/following/request/list/`, caller supplies pagination such as `{ count, max_time }` (a supplied `count` overrides the default).
- `list_comments` → `aweme/v1/comment/list/`, constants `{ comment_style: 2, digged_cid: "", insert_cids: "" }` plus caller `{ aweme_id }`.
- `list_categories` → `aweme/v1/category/list/`; when no `args` are given the operation supplies its own page defaults `{ count: 10, cursor: 0 }`, then the base defaults are merged (so `retry_type` is added while the supplied `count: 10` is retained).
- `search_users` → `aweme/v1/discover/search/`, constant `{ type: 1 }` plus caller `{ keyword, count, cursor }`.
- `search_hashtags` → `aweme/v1/challenge/search/`, caller `{ keyword, count, cursor }`.
- `list_posts_in_hashtag` → `aweme/v1/challenge/aweme/`, constants `{ query_type: 0, type: 5 }` plus caller `{ ch_id }`.
- `list_for_you_feed` → `aweme/v1/feed/`, constants `{ count: 6, is_cold_start: 1, max_cursor: 0, pull_type: 2, type: 0 }` (this family overrides the base `count` with `6`; `pull_type 2` = load-more, `type 0` = the primary feed). Takes optional `args`.
- `list_following_feed` → `aweme/v1/feed/`, same constants but `type: 1` (the following feed).

**Test Cases:** `rcb_tests/public_test_cases/feature4_paginated_list.json`

```json
{
    "description": "Build a paginated listing/search request. Each operation routes a GET to its own fixed endpoint and merges a set of default listing parameters into the caller's parameters before sending: a default page size and a fixed no-retry marker are applied, and any value the caller supplies for those keys overrides the default. Some operations additionally inject their own constant parameters that select a sub-mode or content type; one feed-style family overrides the default page size with a smaller one and adds cold-start, cursor and feed-selector constants. The reply is parsed (preserving oversized integers) and returned. The output describes the HTTP method, endpoint path, the merged query parameters, and the parsed response.",
    "cases": [
        {
            "input": { "action": "request", "operation": "list_posts", "args": { "user_id": "9999999999999999999" }, "response": "{\"status_code\":0,\"aweme_list\":[],\"has_more\":true,\"max_cursor\":9999999999999999999}" },
            "expected_output": "{\"method\":\"GET\",\"params\":{\"count\":[fixed pagination and error handling constants — see config/constants.js],\"retry_type\":\"no_retry\",\"user_id\":\"9999999999999999999\"},\"path\":\"aweme/v1/aweme/post/\",\"response\":{\"aweme_list\":[],\"has_more\":true,\"max_cursor\":\"9999999999999999999\",\"status_code\":0}}\n"
        },
        {
            "input": { "action": "request", "operation": "list_comments", "args": { "aweme_id": "9999999999999999999" }, "response": "{\"status_code\":0,\"comments\":[],\"total\":50}" },
            "expected_output": "{\"method\":\"GET\",\"params\":{\"aweme_id\":\"9999999999999999999\",\"comment_style\":2,\"count\":[fixed pagination and error handling constants — see config/constants.js],\"digged_cid\":\"\",\"insert_cids\":\"\",\"retry_type\":\"no_retry\"},\"path\":\"aweme/v1/comment/list/\",\"response\":{\"comments\":[],\"status_code\":0,\"total\":50}}\n"
        },
        {
            "input": { "action": "request", "operation": "list_categories", "response": "{\"status_code\":0,\"category_list\":[]}" },
            "expected_output": "{\"method\":\"GET\",\"params\":{\"count\":10,\"cursor\":0,\"retry_type\":\"no_retry\"},\"path\":\"aweme/v1/category/list/\",\"response\":{\"category_list\":[],\"status_code\":0}}\n"
        },
        {
            "input": { "action": "request", "operation": "list_for_you_feed", "response": "{\"status_code\":0,\"aweme_list\":[]}" },
            "expected_output": "{\"method\":\"GET\",\"params\":{\"count\":6,\"is_cold_start\":1,\"max_cursor\":0,\"pull_type\":2,\"retry_type\":\"no_retry\",\"type\":0},\"path\":\"aweme/v1/feed/\",\"response\":{\"aweme_list\":[],\"status_code\":0}}\n"
        }
    ]
}
```

---

### Feature 5: Form-Encoded Write Requests

**As a developer**, I want write operations whose payload is a URL-encoded form, so I can post data the way the backend expects without manually encoding it.

**Expected Behavior / Usage:**

Each operation issues a `POST` to its own fixed endpoint. The request body is the URL-encoded form serialization of the operation's fields (identifiers and content from the caller plus any fixed defaults). Empty array fields contribute nothing to the body. One operation also attaches a couple of constant query parameters alongside the body. The reply is parsed (Feature 2) and returned.

Operation contract:
- `get_qr_code` → `POST aweme/v1/fancy/qrcode/info/`. Body is the form `schema_type=<n>&object_id=<user_id>` where `schema_type` defaults to `4`. Query params `{ js_sdk_version: "", app_type: "normal" }` are sent alongside.
- `post_comment` → `POST aweme/v1/comment/publish/`. Body is the form serialization of `{ text, aweme_id, text_extra: [], is_self_see: 0 }` (the post id arrives as `args.post_id` and is sent as `aweme_id`; an empty `text_extra` contributes nothing). No query params.

**Test Cases:** `rcb_tests/public_test_cases/feature5_form_post.json`

```json
{
    "description": "Build a write request whose payload is delivered as a URL-encoded form body. Each operation routes a POST to its own fixed endpoint; the request body is the form-encoded serialization of the operation's fields (identifiers and content supplied by the caller plus any fixed defaults), and one operation also attaches a couple of constant query parameters alongside the body. The reply is parsed (preserving oversized integers) and returned. The output describes the HTTP method, endpoint path, any query parameters, the form-encoded body [fixed pagination and error handling constants — see config/constants.js], and the parsed response.",
    "cases": [
        {
            "input": { "action": "request", "operation": "get_qr_code", "args": { "user_id": "9999999999999999999" }, "response": "{\"status_code\":0,\"qrcode_url\":{\"uri\":\"musically-qrcode/1111111111111111111\"}}" },
            "expected_output": "{\"body\":\"schema_type=4&object_id=9999999999999999999\",\"method\":\"POST\",\"params\":{\"app_type\":\"normal\",\"js_sdk_version\":\"\"},\"path\":\"aweme/v1/fancy/qrcode/info/\",\"response\":{\"qrcode_url\":{\"uri\":\"musically-qrcode/1111111111111111111\"},\"status_code\":0}}\n"
        },
        {
            "input": { "action": "request", "operation": "post_comment", "args": { "post_id": "9999999999999999999", "text": "example comment" }, "response": "{\"status_code\":0,\"comment\":{\"cid\":9999999999999999999,\"text\":\"example comment\"}}" },
            "expected_output": "{\"body\":\"text=example%[fixed pagination and error handling constants — see config/constants.js]comment&aweme_id=9999999999999999999&is_self_see=0\",\"method\":\"POST\",\"params\":{},\"path\":\"aweme/v1/comment/publish/\",\"response\":{\"comment\":{\"cid\":\"9999999999999999999\",\"text\":\"example comment\"},\"status_code\":0}}\n"
        }
    ]
}
```

---

### Feature 6: Structured-Body Write Request

**As a developer**, I want to create a broadcast room with a structured request body, so I can send nested data the backend expects.

**Expected Behavior / Usage:**

The `create_live_stream_room` operation issues a `POST` to `aweme/v1/room/create/` carrying a structured (non-form) body. The body is an object with a single `params` field whose value is `{ title, contacts_authorized }`, where `title` comes from the caller and `contacts_authorized` defaults to `0` when omitted. The reply is parsed (Feature 2) and returned.

**Test Cases:** `rcb_tests/public_test_cases/feature6_room_creation.json`

```json
{
    "description": "Build a room-creation write request. The operation routes a POST to its fixed endpoint and carries a structured (non-form) request body containing the caller-supplied title together with a contacts-authorization flag that defaults to off when omitted. The reply is parsed (preserving oversized integers) and returned. The output describes the HTTP method, endpoint path, the structured body, and the parsed response.",
    "cases": [
        {
            "input": { "action": "request", "operation": "create_live_stream_room", "args": { "title": "TITLE" }, "response": "{\"status_code\":0,\"room\":{\"room_id\":9999999999999999999,\"stream_id\":9000000000000000000}}" },
            "expected_output": "{\"body\":{\"params\":{\"contacts_authorized\":0,\"title\":\"TITLE\"}},\"method\":\"POST\",\"params\":{},\"path\":\"aweme/v1/room/create/\",\"response\":{\"room\":{\"room_id\":\"9999999999999999999\",\"stream_id\":\"9000000000000000000\"},\"status_code\":0}}\n"
        }
    ]
}
```

---

### Feature 7: Authenticated Login With Credential Encryption

**As a developer**, I want a login call that encrypts credentials and captures the session token, so I can authenticate and have following requests carry the token automatically.

**Expected Behavior / Usage:**

Login issues a `POST` to `passport/user/login/`. The supplied credentials are first passed through the credential cipher (Feature 1). The login parameters are built by merging a fixed template — `{ mix_mode: 1, username: "", email: "", mobile: "", account: "", password: "", captcha: "" }` — with the encrypted credentials: in `email` mode the encrypted email and password populate `email` and `password`; in `username` mode the encrypted username and password populate `username` and `password`. The unused credential fields keep their empty-[fixed pagination and error handling constants — see config/constants.js] placeholders. If the response carries an authentication token header, that token is captured for use on subsequent requests; otherwise the captured token is `null`. The reply body is parsed (Feature 2) and returned. The output reports method, path, the login parameters (with encrypted credentials), the parsed response, and the captured `token`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_login.json`

```json
{
    "description": "Perform an authenticated login. The supplied credentials (an email or a username, plus the password) are first passed through the credential-obfuscation cipher; the resulting ciphertexts are placed onto the login request parameters together with a fixed set of empty-[fixed pagination and error handling constants — see config/constants.js] placeholders for the credential fields that were not used and a constant login-mode marker. The request is a POST to the login endpoint. If the response carries an authentication token header, that token is captured for use on subsequent requests. The reply body is parsed and returned. The output describes the HTTP method, endpoint path, the login parameters (with encrypted credentials), the parsed response, and the captured token (null when none was returned).",
    "cases": [
        {
            "input": { "action": "login", "mode": "email", "email": "user@example.com", "password": "password", "token": "token", "response": "{\"data\":{\"user_id\":9999999999999999999,\"email\":\"u**r@example.com\",\"name\":\"user\"},\"message\":\"success\"}" },
            "expected_output": "{\"method\":\"POST\",\"params\":{\"account\":\"\",\"captcha\":\"\",\"email\":\"7076607745607d64687569602b666a68\",\"mix_mode\":1,\"mobile\":\"\",\"password\":\"75647676726a7761\",\"username\":\"\"},\"path\":\"passport/user/login/\",\"response\":{\"data\":{\"email\":\"u**r@example.com\",\"name\":\"user\",\"user_id\":\"9999999999999999999\"},\"message\":\"success\"},\"token\":\"token\"}\n"
        },
        {
            "input": { "action": "login", "mode": "email", "email": "user@example.com", "password": "incorrect_password", "response": "{\"data\":{\"error_code\":1009,\"description\":\"Wrong password\",\"captcha\":\"\"},\"message\":\"error\"}" },
            "expected_output": "{\"method\":\"POST\",\"params\":{\"account\":\"\",\"captcha\":\"\",\"email\":\"7076607745607d64687569602b666a68\",\"mix_mode\":1,\"mobile\":\"\",\"password\":\"6c6b666a77776066715a75647676726a7761\",\"username\":\"\"},\"path\":\"passport/user/login/\",\"response\":{\"data\":{\"captcha\":\"\",\"description\":\"Wrong password\",\"error_code\":1009},\"message\":\"error\"},\"token\":null}\n"
        }
    ]
}
```

---

### Feature 8: Start-Broadcast Two-Step Orchestration

**As a developer**, I want starting a broadcast to be a single call that performs the create-then-activate sequence and fails clearly if either step does not succeed, so I don't have to wire the steps together myself.

**Expected Behavior / Usage:**

Starting a broadcast performs two requests in sequence. First, a `POST aweme/v1/room/create/` creates the room with the structured body `{ params: { title, contacts_authorized: 0 } }`. If the create reply does not report success (its `status_code` is non-zero), the sequence aborts with the normalized error category `[fixed pagination and error handling constants — see config/constants.js]` and no second request is made. On success, the room and stream identifiers from the create reply drive a second request — `GET aweme/v1/room/update/status/` with `{ room_id, stream_id, status: 2, reason_no: 0 }` (status `2` = started, reason `0` = initiated-by-app). If that activation reply does not report success, the sequence aborts with the normalized error category `live_stream_not_started`. When both steps succeed, the parsed create reply is returned. The output reports the ordered list of `requests` issued and either the parsed `response` (on success) or a normalized `error` category (on failure).

**Test Cases:** `rcb_tests/public_test_cases/feature8_[fixed pagination and error handling constants — see config/constants.js].json`

```json
{
    "description": "Start a live broadcast as a two-step sequence. First a POST creates the broadcast room; if the create response does not report success, the sequence aborts with a normalized room-creation failure. On success, the room and stream identifiers from the create response drive a second request that activates the stream with a 'started' status and an app-initiated reason; if that activation response does not report success, the sequence aborts with a normalized activation failure. When both steps succeed, the parsed create response is returned. The output describes the sequence of requests issued and either the parsed final response or a normalized error category.",
    "cases": [
        {
            "input": { "action": "[fixed pagination and error handling constants — see config/constants.js]", "title": "TITLE", "create_response": "{\"status_code\":0,\"room\":{\"room_id\":\"9999999999999999999\",\"stream_id\":\"9000000000000000000\"}}", "status_response": "{\"status_code\":0}" },
            "expected_output": "{\"requests\":[{\"body\":{\"params\":{\"contacts_authorized\":0,\"title\":\"TITLE\"}},\"method\":\"POST\",\"params\":{},\"path\":\"aweme/v1/room/create/\"},{\"method\":\"GET\",\"params\":{\"reason_no\":0,\"room_id\":\"9999999999999999999\",\"status\":2,\"stream_id\":\"9000000000000000000\"},\"path\":\"aweme/v1/room/update/status/\"}],\"response\":{\"room\":{\"room_id\":\"9999999999999999999\",\"stream_id\":\"9000000000000000000\"},\"status_code\":0}}\n"
        },
        {
            "input": { "action": "[fixed pagination and error handling constants — see config/constants.js]", "title": "TITLE", "create_response": "{\"status_code\":3}", "status_response": "{\"status_code\":0}" },
            "expected_output": "{\"error\":\"[fixed pagination and error handling constants — see config/constants.js]\",\"requests\":[{\"body\":{\"params\":{\"contacts_authorized\":0,\"title\":\"TITLE\"}},\"method\":\"POST\",\"params\":{},\"path\":\"aweme/v1/room/create/\"}]}\n"
        }
    ]
}
```

---

### Feature 9: Configuration & Collaborator Validation

**As a developer**, I want misconfiguration to fail fast with a clear, language-neutral error, so I catch a missing required collaborator before any network call.

**Expected Behavior / Usage:**

Two independent preconditions are validated. Constructing the client requires a URL-signing function in its configuration; when that function is absent, construction is rejected and the normalized error category `missing_sign_url` is reported. Separately, issuing a request requires a parameter-serialization function to be available on the request configuration; when it is missing, the request is rejected and the normalized error category `missing_params_serializer` is reported. The output is the normalized error category for the validated scenario. Errors are reported as neutral category [fixed pagination and error handling constants — see config/constants.js]s — never as host-language runtime type names or messages.

**Test Cases:** `rcb_tests/public_test_cases/feature9_config_validation.json`

```json
{
    "description": "Validate required collaborators before a request is attempted. Constructing the client requires a URL-signing function to be supplied in its configuration; when that function is absent, construction is rejected with a normalized error. Independently, issuing a request requires a parameter-serialization function to be available on the request configuration; when it is missing, the request is rejected with a normalized error. The output is the normalized error category for the rejected scenario.",
    "cases": [
        {
            "input": { "action": "validate", "check": "sign_url", "config": {} },
            "expected_output": "{\"error\":\"missing_sign_url\"}\n"
        },
        {
            "input": { "action": "validate", "check": "params_serializer", "user_id": "9999999999999999999" },
            "expected_output": "{\"error\":\"missing_params_serializer\"}\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above — the credential cipher, the oversized-integer-safe JSON parser, a per-operation request builder (single-resource GETs, paginated list/search GETs, form-encoded POSTs, the structured-body POST), the login flow with credential encryption and token capture, the two-step start-broadcast orchestration, and configuration/collaborator validation. The core logic must be decoupled from stdin/stdout and JSON-command parsing.

2. **The Execution/Test Adapter:** A runnable entry point that reads a single JSON request object from stdin, dispatches on its `action` field, invokes the appropriate core logic, and prints exactly one canonical JSON line to stdout (object keys sorted alphabetically), matching the per-feature contracts above. Supported actions: `encrypt` (Feature 1), `parse_response` (Feature 2), `request` (Features 3–6, selected by `operation`), `login` (Feature 7), `[fixed pagination and error handling constants — see config/constants.js]` (Feature 8), and `validate` (Feature 9). Because requests are observed through a mocked transport, the adapter must report the actual method/path/params/body the core builds, the parsed response, and (for login) the captured token, and must normalize all error conditions to neutral category [fixed pagination and error handling constants — see config/constants.js]s. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same hex formatting rules as the encryption module
- include the same empty object query structure used in the validate endpoint
