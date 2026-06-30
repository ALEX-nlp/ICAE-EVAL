## Product Requirement Document

# Serverless HTTP Request Adapter - Event Routing and Response Contract

## Project Goal

Build a serverless HTTP request adapter that allows developers to route cloud-provider HTTP events through concise request handlers and emit predictable HTTP-style responses without manually parsing provider event formats or assembling response envelopes.

---

## Background & Problem

Without this library/tool, developers are forced to decode cloud gateway and load balancer event objects, match URL paths, extract route parameters, parse headers/query strings/cookies, execute middleware, serialize bodies, and build provider-specific response objects by hand. This leads to repetitive routing code, inconsistent response formatting, fragile error handling, and maintenance issues across functions.

With this library/tool, developers define handler behavior once and receive normalized request objects plus consistent response helpers for JSON, HTML, redirects, cookies, headers, CORS, middleware, and errors.

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

### Feature 1: HTTP Routing and Request Matching

**As a developer**, I want to send an HTTP-style request event through registered handlers, so I can receive the response selected by method, path, parameters, query values, and fallback rules.

**Expected Behavior / Usage:**

The adapter input describes an HTTP request with a route-suite selector, HTTP method, URL path, optional query values, optional multi-value query values, and optional body. The output is raw stdout containing status, base64 flag, normalized headers, and body lines. Exact path matches, parameterized path matches, catch-all handlers, handler return values, and method-not-allowed responses must be visible in the output envelope.

**Test Cases:** `rcb_tests/public_test_cases/feature1_routing.json`

```json
{
  "description": "A registered route is selected by request method and exact path, returning the route response envelope.",
  "cases": [
    {
      "input": {
        "feature": "routing",
        "method": "get",
        "path": "/"
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]200\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody={\"method\":\"get\",\"status\":\"ok\"[a specific section name prefix — ask the PM for the exact delimiter]\n"
    [a specific section name prefix — ask the PM for the exact delimiter],
    {
      "input": {
        "feature": "routing",
        "method": "post",
        "path": "/test"
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]200\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody={\"method\":\"post\",\"status\":\"ok\"[a specific section name prefix — ask the PM for the exact delimiter]\n"
    [a specific section name prefix — ask the PM for the exact delimiter],
    {
      "input": {
        "feature": "routing",
        "method": "get",
        "path": "/test/123"
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]200\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody={\"method\":\"get\",\"status\":\"ok\",\"param\":\"123\",\"param2\":\"123\"[a specific section name prefix — ask the PM for the exact delimiter]\n"
    [a specific section name prefix — ask the PM for the exact delimiter],
    {
      "input": {
        "feature": "routing",
        "method": "delete",
        "path": "/test/abc"
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]200\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody={\"method\":\"delete\",\"status\":\"ok\",\"param\":\"abc\"[a specific section name prefix — ask the PM for the exact delimiter]\n"
    [a specific section name prefix — ask the PM for the exact delimiter]
  ]
[a specific section name prefix — ask the PM for the exact delimiter]
```

---
### Feature 2: Response Body and Redirect Rendering

**As a developer**, I want to return common response body types and redirect responses, so I can produce an HTTP-style response envelope that clients can consume consistently.

**Expected Behavior / Usage:**

The adapter input selects the response behavior suite and supplies an HTTP method, path, optional query values, and optional response-configuration variant. The output must show the status code, base64 flag, normalized headers, and body. Object, number, array, string, and empty outputs are rendered as response bodies; status helpers produce the correct status and reason body; JSONP wraps JSON in the selected callback name; location and redirect responses expose Location headers and redirect bodies; configured serializers can alter body rendering and base64/compression metadata.

**Test Cases:** `rcb_tests/public_test_cases/feature2_responses.json`

```json
{
  "description": "Object, array, number, string, and empty handler outputs are serialized into an HTTP-style response envelope.",
  "cases": [
    {
      "input": {
        "feature": "responses",
        "method": "get",
        "path": "/object"
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]200\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody={\"object\":true[a specific section name prefix — ask the PM for the exact delimiter]\n"
    [a specific section name prefix — ask the PM for the exact delimiter],
    {
      "input": {
        "feature": "responses",
        "method": "get",
        "path": "/number"
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]200\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody=123\n"
    [a specific section name prefix — ask the PM for the exact delimiter],
    {
      "input": {
        "feature": "responses",
        "method": "get",
        "path": "/array"
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]200\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody=[1,2,3]\n"
    [a specific section name prefix — ask the PM for the exact delimiter],
    {
      "input": {
        "feature": "responses",
        "method": "get",
        "path": "/string"
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]200\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody=this is a string\n"
    [a specific section name prefix — ask the PM for the exact delimiter],
    {
      "input": {
        "feature": "responses",
        "method": "get",
        "path": "/empty"
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]200\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody=\n"
    [a specific section name prefix — ask the PM for the exact delimiter]
  ]
[a specific section name prefix — ask the PM for the exact delimiter]
```

---
### Feature 3: Header Rendering and CORS Helpers

**As a developer**, I want to set, override, append, and generate response headers, so I can send predictable multi-value headers for regular, HTML, and CORS responses.

**Expected Behavior / Usage:**

The adapter input selects the header behavior suite and supplies an HTTP method and path. The output must show lower-case normalized headers as a JSON object of arrays, along with status, base64 flag, and body. Empty header values are preserved as empty strings, appended values remain multiple values, content type can be overridden by response helpers, HTML helpers emit text/html, and CORS helpers emit default or custom access-control headers.

**Test Cases:** `rcb_tests/public_test_cases/feature3_headers.json`

```json
{
  "description": "Response headers are normalized to lower-case multi-value headers in the HTTP response envelope.",
  "cases": [
    {
      "input": {
        "feature": "headers",
        "method": "get",
        "path": "/header"
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]200\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"],\"test\":[\"testVal\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody={\"method\":\"get\",\"status\":\"ok\"[a specific section name prefix — ask the PM for the exact delimiter]\n"
    [a specific section name prefix — ask the PM for the exact delimiter],
    {
      "input": {
        "feature": "headers",
        "method": "get",
        "path": "/emptyHeader"
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]200\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"],\"test\":[\"\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody={\"method\":\"get\",\"status\":\"ok\"[a specific section name prefix — ask the PM for the exact delimiter]\n"
    [a specific section name prefix — ask the PM for the exact delimiter],
    {
      "input": {
        "feature": "headers",
        "method": "get",
        "path": "/overrideType"
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]200\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"text/html\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody=<div>testHTML</div>\n"
    [a specific section name prefix — ask the PM for the exact delimiter],
    {
      "input": {
        "feature": "headers",
        "method": "get",
        "path": "/appendHeader"
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]200\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"],\"test\":[\"testVal1\",\"testVal2\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody={\"method\":\"get\",\"status\":\"ok\"[a specific section name prefix — ask the PM for the exact delimiter]\n"
    [a specific section name prefix — ask the PM for the exact delimiter]
  ]
[a specific section name prefix — ask the PM for the exact delimiter]
```

---
### Feature 4: Cookie Serialization and Parsing

**As a developer**, I want to set, clear, and read cookies in HTTP-style events, so I can preserve cookie wire-format behavior in response headers and request bodies.

**Expected Behavior / Usage:**

The adapter input selects the cookie behavior suite and supplies an HTTP request path, with optional incoming Cookie headers. The output must show Set-Cookie values in normalized response headers and any parsed incoming cookies in the body. Cookie names and values are serialized, reserved characters are percent-encoded, object values are serialized before encoding, multiple cookies remain separate header values, attributes such as Domain, Expires, HttpOnly, and SameSite are included when requested, and clearing a cookie emits an expired cookie value.

**Test Cases:** `rcb_tests/public_test_cases/feature4_cookies.json`

```json
{
  "description": "Setting one cookie emits a Set-Cookie header with the encoded name, value, and default path.",
  "cases": [
    {
      "input": {
        "feature": "cookies",
        "method": "get",
        "path": "/single"
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]200\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"],\"set-cookie\":[\"test=value; Path=/\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody={[a specific section name prefix — ask the PM for the exact delimiter]\n"
    [a specific section name prefix — ask the PM for the exact delimiter],
    {
      "input": {
        "feature": "cookies",
        "method": "get",
        "path": "/multiple"
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]200\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"],\"set-cookie\":[\"test=value; Path=/\",\"test2=value2; Path=/\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody={[a specific section name prefix — ask the PM for the exact delimiter]\n"
    [a specific section name prefix — ask the PM for the exact delimiter],
    {
      "input": {
        "feature": "cookies",
        "method": "get",
        "path": "/encoded"
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]200\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"],\"set-cookie\":[\"test=http%3A%2F%2F%20%5B%5D%20foo%3Bbar; Path=/\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody={[a specific section name prefix — ask the PM for the exact delimiter]\n"
    [a specific section name prefix — ask the PM for the exact delimiter],
    {
      "input": {
        "feature": "cookies",
        "method": "get",
        "path": "/object"
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]200\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"],\"set-cookie\":[\"test=%7B%22foo%22%3A%22bar%22%7D; Path=/\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody={[a specific section name prefix — ask the PM for the exact delimiter]\n"
    [a specific section name prefix — ask the PM for the exact delimiter],
    {
      "input": {
        "feature": "cookies",
        "method": "get",
        "path": "/domain"
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]200\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"],\"set-cookie\":[\"test=value; Domain=test.com; Expires=Tue, 01 Jan 2019 00:00:00 GMT; Path=/\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody={[a specific section name prefix — ask the PM for the exact delimiter]\n"
    [a specific section name prefix — ask the PM for the exact delimiter]
  ]
[a specific section name prefix — ask the PM for the exact delimiter]
```

---
### Feature 5: Middleware Execution

**As a developer**, I want to run middleware before handlers, so I can observe request enrichment, path scoping, and short-circuit behavior in the final response.

**Expected Behavior / Usage:**

The adapter input selects a middleware suite variant and supplies an HTTP method, path, optional query values, and optional body. The output must prove middleware execution through response body fields or headers. Global middleware can attach data used by the handler, middleware can see route parameters/query/body values, path-scoped middleware runs only for matching exact, wildcard, or parameterized paths, and middleware that sends a response prevents later middleware and route handlers from changing the result.

**Test Cases:** `rcb_tests/public_test_cases/feature5_middleware.json`

```json
{
  "description": "Global middleware runs before matching route handlers and can attach values used by the handler response.",
  "cases": [
    {
      "input": {
        "feature": "middleware",
        "variant": "global",
        "method": "get",
        "path": "/test"
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]200\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody={\"method\":\"get\",\"testMiddleware\":\"123\",\"testMiddleware2\":\"456\"[a specific section name prefix — ask the PM for the exact delimiter]\n"
    [a specific section name prefix — ask the PM for the exact delimiter],
    {
      "input": {
        "feature": "middleware",
        "variant": "global",
        "method": "post",
        "path": "/test/abc",
        "query": {
          "test": "queryValue"
        [a specific section name prefix — ask the PM for the exact delimiter],
        "body": {
          "test": "bodyValue"
        [a specific section name prefix — ask the PM for the exact delimiter]
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]200\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody={\"method\":\"get\",\"testMiddleware3\":\"abc\",\"testMiddleware4\":\"queryValue\",\"testMiddleware5\":\"bodyValue\"[a specific section name prefix — ask the PM for the exact delimiter]\n"
    [a specific section name prefix — ask the PM for the exact delimiter],
    {
      "input": {
        "feature": "middleware",
        "variant": "path",
        "method": "get",
        "path": "/test"
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]200\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody={\"middleware\":true,\"middlewareWildcard\":false,\"middlewareParam\":false[a specific section name prefix — ask the PM for the exact delimiter]\n"
    [a specific section name prefix — ask the PM for the exact delimiter]
  ]
[a specific section name prefix — ask the PM for the exact delimiter]
```

---
### Feature 6: Error Response Handling

**As a developer**, I want to convert handler errors into HTTP-style responses, so I can expose predictable error status, headers, and body without leaking runtime exception identities.

**Expected Behavior / Usage:**

The adapter input selects the error behavior suite and supplies an HTTP method, path, and optional error-middleware variant. The output must use the same status/header/body envelope as successful responses. A called error helper produces a serialized domain error body, thrown handler errors are converted into serialized domain error text, handlers may explicitly return non-500 error statuses, explicit error status codes control the status line, and error middleware can replace the default body and content type. Output must not include host-language exception class names.

**Test Cases:** `rcb_tests/public_test_cases/feature6_errors.json`

```json
{
  "description": "Calling the error response helper returns an HTTP error envelope with a serialized domain error body.",
  "cases": [
    {
      "input": {
        "feature": "errors",
        "method": "get",
        "path": "/called"
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]500\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody={\"error\":\"This is a test error message\"[a specific section name prefix — ask the PM for the exact delimiter]\n"
    [a specific section name prefix — ask the PM for the exact delimiter],
    {
      "input": {
        "feature": "errors",
        "method": "get",
        "path": "/thrown"
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]500\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody={\"error\":\"This is a test thrown error\"[a specific section name prefix — ask the PM for the exact delimiter]\n"
    [a specific section name prefix — ask the PM for the exact delimiter],
    {
      "input": {
        "feature": "errors",
        "method": "get",
        "path": "/simulated"
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]405\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody={\"error\":\"This is a simulated error\"[a specific section name prefix — ask the PM for the exact delimiter]\n"
    [a specific section name prefix — ask the PM for the exact delimiter],
    {
      "input": {
        "feature": "errors",
        "method": "get",
        "path": "/coded"
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]403\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody={\"error\":\"This is a test error message\"[a specific section name prefix — ask the PM for the exact delimiter]\n"
    [a specific section name prefix — ask the PM for the exact delimiter]
  ]
[a specific section name prefix — ask the PM for the exact delimiter]
```

---
### Feature 7: Cloud Event Normalization

**As a developer**, I want to send cloud provider HTTP events through the router, so I can receive responses that prove provider-specific request fields were normalized.

**Expected Behavior / Usage:**

The adapter input provides a complete cloud HTTP event and context. The output must include response status, base64 flag, normalized headers or cookies, and a body containing request-observable fields such as interface type, source IP, selected route, query values, multi-value query values, headers, cookies, path parameters, stage variables, client metadata, and base64 input flag. Gateway events and load balancer events must render their different header/cookie/status-description conventions so the framework behavior cannot be bypassed by returning a fixed body.

**Test Cases:** `rcb_tests/public_test_cases/feature7_cloud_events.json`

```json
{
  "description": "An API gateway version 1 proxy event is normalized into request fields and returns gateway multi-value headers.",
  "cases": [
    {
      "input": {
        "feature": "cloudEvent",
        "event": {
          "path": "/test/hello",
          "headers": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, lzma, sdch, br",
            "Accept-Language": "en-US,en;q=0.8",
            "CloudFront-Forwarded-Proto": "https",
            "CloudFront-Is-Desktop-Viewer": "true",
            "CloudFront-Is-Mobile-Viewer": "false",
            "CloudFront-Is-SmartTV-Viewer": "false",
            "CloudFront-Is-Tablet-Viewer": "false",
            "CloudFront-Viewer-Country": "US",
            "Host": "wt6mne2s9k.execute-api.us-west-2.amazonaws.com",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.82 Safari/537.36 OPR/39.0.2256.48",
            "Via": "1.1 fb7cca60f0ecd82ce07790c9c5eef16c.cloudfront.net (CloudFront)",
            "X-Amz-Cf-Id": "nBsWBOrSHMgnaROZJK1wGCZ9PcRcSpq_oSXZNQwQ10OTZL4cimZo3g==",
            "X-Forwarded-For": "192.168.100.1, 192.168.1.1",
            "X-Forwarded-Port": "443",
            "X-Forwarded-Proto": "https"
          [a specific section name prefix — ask the PM for the exact delimiter],
          "multiValueHeaders": {
            "accept": [
              "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
            ],
            "accept-encoding": [
              "gzip, deflate, lzma, sdch, br"
            ],
            "accept-language": [
              "en-US,en;q=0.8"
            ],
            "cloudfront-forwarded-proto": [
              "https"
            ],
            "cloudfront-is-desktop-viewer": [
              "true"
            ],
            "cloudfront-is-mobile-viewer": [
              "false"
            ],
            "cloudfront-is-smarttv-viewer": [
              "false"
            ],
            "cloudfront-is-tablet-viewer": [
              "false"
            ],
            "cloudfront-viewer-country": [
              "US"
            ],
            "host": [
              "wt6mne2s9k.execute-api.us-west-2.amazonaws.com"
            ],
            "upgrade-insecure-requests": [
              "1"
            ],
            "user-agent": [
              "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.82 Safari/537.36 OPR/39.0.2256.48"
            ],
            "via": [
              "1.1 fb7cca60f0ecd82ce07790c9c5eef16c.cloudfront.net (CloudFront)"
            ],
            "x-amz-cf-id": [
              "nBsWBOrSHMgnaROZJK1wGCZ9PcRcSpq_oSXZNQwQ10OTZL4cimZo3g=="
            ],
            "x-forwarded-for": [
              "192.168.100.1, 192.168.1.1"
            ],
            "x-forwarded-port": [
              "443"
            ],
            "x-forwarded-proto": [
              "https"
            ],
            "test-header": [
              "val1",
              "val2"
            ]
          [a specific section name prefix — ask the PM for the exact delimiter],
          "pathParameters": {
            "proxy": "hello"
          [a specific section name prefix — ask the PM for the exact delimiter],
          "requestContext": {
            "accountId": "123456789012",
            "resourceId": "us4z18",
            "stage": "test",
            "requestId": "41b45ea3-70b5-11e6-b7bd-69b5aaebc7d9",
            "identity": {
              "cognitoIdentityPoolId": "",
              "accountId": "",
              "cognitoIdentityId": "",
              "caller": "",
              "apiKey": "",
              "sourceIp": "192.168.100.12",
              "cognitoAuthenticationType": "",
              "cognitoAuthenticationProvider": "",
              "userArn": "",
              "userAgent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.82 Safari/537.36 OPR/39.0.2256.48",
              "user": ""
            [a specific section name prefix — ask the PM for the exact delimiter],
            "resourcePath": "/{proxy+[a specific section name prefix — ask the PM for the exact delimiter]",
            "httpMethod": "GET",
            "apiId": "wt6mne2s9k"
          [a specific section name prefix — ask the PM for the exact delimiter],
          "resource": "/{proxy+[a specific section name prefix — ask the PM for the exact delimiter]",
          "httpMethod": "GET",
          "queryStringParameters": {
            "qs1": "foo",
            "qs2": "bar"
          [a specific section name prefix — ask the PM for the exact delimiter],
          "multiValueQueryStringParameters": {
            "qs2": [
              "foo",
              "bar"
            ],
            "qs3": [
              "bat",
              "baz"
            ]
          [a specific section name prefix — ask the PM for the exact delimiter],
          "stageVariables": {
            "stageVarName": "stageVarValue"
          [a specific section name prefix — ask the PM for the exact delimiter]
        [a specific section name prefix — ask the PM for the exact delimiter],
        "context": {
          "callbackWaitsForEmptyEventLoop": false,
          "logGroupName": "/aws/lambda/test-apigateway",
          "logStreamName": "2018/12/22/[$LATEST]21a094d27de15adeaceaf073140d5aca",
          "functionName": "test-alb",
          "memoryLimitInMB": "1024",
          "functionVersion": "$LATEST",
          "invokeid": "59327015-07f1-11e9-a63e-9f9eb869059e",
          "awsRequestId": "59327015-07f1-11e9-a63e-9f9eb869059e",
          "invokedFunctionArn": "arn:aws:lambda:us-east-1:XXXXXXXXXX:function:test-apigateway"
        [a specific section name prefix — ask the PM for the exact delimiter]
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]200\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":[\"application/json\"],\"set-cookie\":[\"test=value; Path=/\",\"test2=value2; Path=/\"][a specific section name prefix — ask the PM for the exact delimiter]\nbody={\"request\":{\"interface\":\"apigateway\",\"ip\":\"192.168.100.1\",\"route\":\"/test/hello\",\"query\":{\"qs1\":\"foo\",\"qs2\":\"bar\"[a specific section name prefix — ask the PM for the exact delimiter],\"multiValueQuery\":{\"qs2\":[\"foo\",\"bar\"],\"qs3\":[\"bat\",\"baz\"][a specific section name prefix — ask the PM for the exact delimiter],\"headers\":{\"accept\":\"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8\",\"accept-encoding\":\"gzip, deflate, lzma, sdch, br\",\"accept-language\":\"en-US,en;q=0.8\",\"cloudfront-forwarded-proto\":\"https\",\"cloudfront-is-desktop-viewer\":\"true\",\"cloudfront-is-mobile-viewer\":\"false\",\"cloudfront-is-smarttv-viewer\":\"false\",\"cloudfront-is-tablet-viewer\":\"false\",\"cloudfront-viewer-country\":\"US\",\"host\":\"wt6mne2s9k.execute-api.us-west-2.amazonaws.com\",\"upgrade-insecure-requests\":\"1\",\"user-agent\":\"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.82 Safari/537.36 OPR/39.0.2256.48\",\"via\":\"1.1 fb7cca60f0ecd82ce07790c9c5eef16c.cloudfront.net (CloudFront)\",\"x-amz-cf-id\":\"nBsWBOrSHMgnaROZJK1wGCZ9PcRcSpq_oSXZNQwQ10OTZL4cimZo3g==\",\"x-forwarded-for\":\"192.168.100.1, 192.168.1.1\",\"x-forwarded-port\":\"443\",\"x-forwarded-proto\":\"https\",\"test-header\":\"val1,val2\"[a specific section name prefix — ask the PM for the exact delimiter],\"multiValueHeaders\":{\"accept\":[\"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8\"],\"accept-encoding\":[\"gzip, deflate, lzma, sdch, br\"],\"accept-language\":[\"en-US,en;q=0.8\"],\"cloudfront-forwarded-proto\":[\"https\"],\"cloudfront-is-desktop-viewer\":[\"true\"],\"cloudfront-is-mobile-viewer\":[\"false\"],\"cloudfront-is-smarttv-viewer\":[\"false\"],\"cloudfront-is-tablet-viewer\":[\"false\"],\"cloudfront-viewer-country\":[\"US\"],\"host\":[\"wt6mne2s9k.execute-api.us-west-2.amazonaws.com\"],\"upgrade-insecure-requests\":[\"1\"],\"user-agent\":[\"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.82 Safari/537.36 OPR/39.0.2256.48\"],\"via\":[\"1.1 fb7cca60f0ecd82ce07790c9c5eef16c.cloudfront.net (CloudFront)\"],\"x-amz-cf-id\":[\"nBsWBOrSHMgnaROZJK1wGCZ9PcRcSpq_oSXZNQwQ10OTZL4cimZo3g==\"],\"x-forwarded-for\":[\"192.168.100.1, 192.168.1.1\"],\"x-forwarded-port\":[\"443\"],\"x-forwarded-proto\":[\"https\"],\"test-header\":[\"val1\",\"val2\"][a specific section name prefix — ask the PM for the exact delimiter],\"cookies\":{[a specific section name prefix — ask the PM for the exact delimiter],\"clientType\":\"desktop\",\"clientCountry\":\"US\",\"pathParameters\":{\"proxy\":\"hello\"[a specific section name prefix — ask the PM for the exact delimiter],\"stageVariables\":{\"stageVarName\":\"stageVarValue\"[a specific section name prefix — ask the PM for the exact delimiter],\"isBase64Encoded\":false[a specific section name prefix — ask the PM for the exact delimiter][a specific section name prefix — ask the PM for the exact delimiter]\n"
    [a specific section name prefix — ask the PM for the exact delimiter],
    {
      "input": {
        "feature": "cloudEvent",
        "event": {
          "version": "2.0",
          "routeKey": "$default",
          "rawPath": "/test/hello",
          "rawQueryString": "parameter1=value1&parameter1=value2&parameter2=value",
          "cookies": [
            "cookie1=test",
            "cookie2=123"
          ],
          "headers": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Encoding": "gzip, deflate, lzma, sdch, br",
            "Accept-Language": "en-US,en;q=0.8",
            "CloudFront-Forwarded-Proto": "https",
            "CloudFront-Is-Desktop-Viewer": "true",
            "CloudFront-Is-Mobile-Viewer": "false",
            "CloudFront-Is-SmartTV-Viewer": "false",
            "CloudFront-Is-Tablet-Viewer": "false",
            "CloudFront-Viewer-Country": "US",
            "Host": "wt6mne2s9k.execute-api.us-west-2.amazonaws.com",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.82 Safari/537.36 OPR/39.0.2256.48",
            "Via": "1.1 fb7cca60f0ecd82ce07790c9c5eef16c.cloudfront.net (CloudFront)",
            "X-Amz-Cf-Id": "nBsWBOrSHMgnaROZJK1wGCZ9PcRcSpq_oSXZNQwQ10OTZL4cimZo3g==",
            "X-Forwarded-For": "192.168.100.1, 192.168.1.1",
            "X-Forwarded-Port": "443",
            "X-Forwarded-Proto": "https",
            "test-header": "val1,val2"
          [a specific section name prefix — ask the PM for the exact delimiter],
          "queryStringParameters": {
            "qs1": "foo",
            "qs2": "foo,bar",
            "qs3": "bat,baz"
          [a specific section name prefix — ask the PM for the exact delimiter],
          "requestContext": {
            "accountId": "123456789012",
            "apiId": "api-id",
            "authentication": {
              "clientCert": {
                "clientCertPem": "CERT_CONTENT",
                "subjectDN": "www.example.com",
                "issuerDN": "Example issuer",
                "serialNumber": "a1:a1:a1:a1:a1:a1:a1:a1:a1:a1:a1:a1:a1:a1:a1:a1",
                "validity": {
                  "notBefore": "May 28 12:30:02 2019 GMT",
                  "notAfter": "Aug  5 09:36:04 2021 GMT"
                [a specific section name prefix — ask the PM for the exact delimiter]
              [a specific section name prefix — ask the PM for the exact delimiter]
            [a specific section name prefix — ask the PM for the exact delimiter],
            "authorizer": {
              "jwt": {
                "claims": {
                  "claim1": "value1",
                  "claim2": "value2"
                [a specific section name prefix — ask the PM for the exact delimiter],
                "scopes": [
                  "scope1",
                  "scope2"
                ]
              [a specific section name prefix — ask the PM for the exact delimiter]
            [a specific section name prefix — ask the PM for the exact delimiter],
            "domainName": "id.execute-api.us-east-1.amazonaws.com",
            "domainPrefix": "id",
            "http": {
              "method": "GET",
              "path": "/test/hello",
              "protocol": "HTTP/1.1",
              "sourceIp": "IP",
              "userAgent": "agent"
            [a specific section name prefix — ask the PM for the exact delimiter],
            "requestId": "id",
            "routeKey": "$default",
            "stage": "$default",
            "time": "12/Mar/2020:19:03:58 +0000",
            "timeEpoch": 1583348638390
          [a specific section name prefix — ask the PM for the exact delimiter],
          "body": "Hello from Lambda",
          "pathParameters": {
            "proxy": "hello"
          [a specific section name prefix — ask the PM for the exact delimiter],
          "isBase64Encoded": false,
          "stageVariables": {
            "stageVarName": "stageVarValue"
          [a specific section name prefix — ask the PM for the exact delimiter]
        [a specific section name prefix — ask the PM for the exact delimiter],
        "context": {
          "callbackWaitsForEmptyEventLoop": false,
          "logGroupName": "/aws/lambda/test-apigateway",
          "logStreamName": "2018/12/22/[$LATEST]21a094d27de15adeaceaf073140d5aca",
          "functionName": "test-alb",
          "memoryLimitInMB": "1024",
          "functionVersion": "$LATEST",
          "invokeid": "59327015-07f1-11e9-a63e-9f9eb869059e",
          "awsRequestId": "59327015-07f1-11e9-a63e-9f9eb869059e",
          "invokedFunctionArn": "arn:aws:lambda:us-east-1:XXXXXXXXXX:function:test-apigateway"
        [a specific section name prefix — ask the PM for the exact delimiter]
      [a specific section name prefix — ask the PM for the exact delimiter],
      "expected_output": "[a specific section name prefix — ask the PM for the exact delimiter]200\n[a specific section name prefix — ask the PM for the exact delimiter]false\n[a specific section name prefix — ask the PM for the exact delimiter]\"content-type\":\"application/json\"[a specific section name prefix — ask the PM for the exact delimiter]\ncookies=[\"test=value; Path=/\",\"test2=value2; Path=/\"]\nbody={\"request\":{\"interface\":\"apigateway\",\"ip\":\"192.168.100.1\",\"route\":\"/test/hello\",\"query\":{\"qs1\":\"foo\",\"qs2\":\"foo,bar\",\"qs3\":\"bat,baz\"[a specific section name prefix — ask the PM for the exact delimiter],\"multiValueQuery\":{\"qs1\":[\"foo\"],\"qs2\":[\"foo\",\"bar\"],\"qs3\":[\"bat\",\"baz\"][a specific section name prefix — ask the PM for the exact delimiter],\"headers\":{\"accept\":\"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8\",\"accept-encoding\":\"gzip, deflate, lzma, sdch, br\",\"accept-language\":\"en-US,en;q=0.8\",\"cloudfront-forwarded-proto\":\"https\",\"cloudfront-is-desktop-viewer\":\"true\",\"cloudfront-is-mobile-viewer\":\"false\",\"cloudfront-is-smarttv-viewer\":\"false\",\"cloudfront-is-tablet-viewer\":\"false\",\"cloudfront-viewer-country\":\"US\",\"host\":\"wt6mne2s9k.execute-api.us-west-2.amazonaws.com\",\"upgrade-insecure-requests\":\"1\",\"user-agent\":\"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.82 Safari/537.36 OPR/39.0.2256.48\",\"via\":\"1.1 fb7cca60f0ecd82ce07790c9c5eef16c.cloudfront.net (CloudFront)\",\"x-amz-cf-id\":\"nBsWBOrSHMgnaROZJK1wGCZ9PcRcSpq_oSXZNQwQ10OTZL4cimZo3g==\",\"x-forwarded-for\":\"192.168.100.1, 192.168.1.1\",\"x-forwarded-port\":\"443\",\"x-forwarded-proto\":\"https\",\"test-header\":\"val1,val2\"[a specific section name prefix — ask the PM for the exact delimiter],\"multiValueHeaders\":{\"accept\":[\"text/html\",\"application/xhtml+xml\",\"application/xml;q=0.9\",\"image/webp\",\"*/*;q=0.8\"],\"accept-encoding\":[\"gzip\",\" deflate\",\" lzma\",\" sdch\",\" br\"],\"accept-language\":[\"en-US\",\"en;q=0.8\"],\"cloudfront-forwarded-proto\":[\"https\"],\"cloudfront-is-desktop-viewer\":[\"true\"],\"cloudfront-is-mobile-viewer\":[\"false\"],\"cloudfront-is-smarttv-viewer\":[\"false\"],\"cloudfront-is-tablet-viewer\":[\"false\"],\"cloudfront-viewer-country\":[\"US\"],\"host\":[\"wt6mne2s9k.execute-api.us-west-2.amazonaws.com\"],\"upgrade-insecure-requests\":[\"1\"],\"user-agent\":[\"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML\",\" like Gecko) Chrome/52.0.2743.82 Safari/537.36 OPR/39.0.2256.48\"],\"via\":[\"1.1 fb7cca60f0ecd82ce07790c9c5eef16c.cloudfront.net (CloudFront)\"],\"x-amz-cf-id\":[\"nBsWBOrSHMgnaROZJK1wGCZ9PcRcSpq_oSXZNQwQ10OTZL4cimZo3g==\"],\"x-forwarded-for\":[\"192.168.100.1\",\" 192.168.1.1\"],\"x-forwarded-port\":[\"443\"],\"x-forwarded-proto\":[\"https\"],\"test-header\":[\"val1\",\"val2\"][a specific section name prefix — ask the PM for the exact delimiter],\"cookies\":{\"cookie1\":\"test\",\"cookie2\":123[a specific section name prefix — ask the PM for the exact delimiter],\"clientType\":\"desktop\",\"clientCountry\":\"US\",\"pathParameters\":{\"proxy\":\"hello\"[a specific section name prefix — ask the PM for the exact delimiter],\"stageVariables\":{\"stageVarName\":\"stageVarValue\"[a specific section name prefix — ask the PM for the exact delimiter],\"isBase64Encoded\":false[a specific section name prefix — ask the PM for the exact delimiter][a specific section name prefix — ask the PM for the exact delimiter]\n"
    [a specific section name prefix — ask the PM for the exact delimiter]
  ]
[a specific section name prefix — ask the PM for the exact delimiter]
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem[a specific section name prefix — ask the PM for the exact delimiter]@{case_index.zfill(3)[a specific section name prefix — ask the PM for the exact delimiter].txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
