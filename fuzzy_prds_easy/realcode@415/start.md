## Product Requirement Document

# OAuth 2.0 Scope, Audience & Redirect-URI Helper Library — Pure String/Set Transformation Functions

## Project Goal

Build a small, dependency-light library of pure, deterministic helper functions that an authorization layer can use to decide scope grants, audience grants, redirect-URI acceptance, and to perform a couple of low-level string transformations, so that developers building OAuth 2.0 style servers can reuse one well-tested set of matching/validation primitives instead of re-implementing fiddly string and URL comparison rules by hand.

---

## Background & Problem

Authorization servers constantly answer the same low-level questions: is a requested scope covered by the scopes a client was granted? Do two lists of arguments represent the same set (regardless of order/case)? Is a requested audience whitelisted? Is a redirect URI registered, secure, and well-formed? Each of these has subtle rules (dot-segment hierarchies, wildcard segments, case sensitivity, loopback-port exceptions, trailing-slash tolerance) that are easy to get wrong.

Without a shared library, every project re-codes these rules inline, producing inconsistent and occasionally insecure behavior. This library packages each rule as a small pure function with a precise, well-documented contract: given plain inputs (lists of strings, URLs, parameter maps) it returns a plain, deterministic answer. There is no I/O, no network, and no global state — every function is a referentially transparent transformation, which makes the behavior trivial to test and reuse.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains. Here the domain naturally splits into a few cohesive groups (scope matching, set comparison, audience matching, redirect-URI validation, parameter encoding) — organize accordingly.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic function calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification. New matching strategies should be addable without editing existing ones.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully (empty lists, empty strings, malformed URLs). Errors should be modeled properly rather than relying on generic faults.

---

## Core Features

The execution adapter reads one JSON object from stdin. The object carries an `op` field selecting the operation; the remaining fields are operation-specific (described per feature below). For batch operations the input carries a `checks`/`requests`/`urls` array and the adapter prints one output line per element, in input order. All boolean results are rendered as the lowercase words `true` / `false`. Errors are rendered as a neutral `error=<category>` line and never leak host-language type names.


### Feature 1: Scope Strategy Matching

**As a developer**, I want to test whether a requested scope is covered by the set of scopes a client was granted, under several well-defined matching strategies, so I can authorize requests consistently.

**Expected Behavior / Usage:**

Three independent strategies decide whether a requested scope is granted given a list of granted scopes. The adapter input names the `strategy` (`hierarchic`, `wildcard`, or `exact`), the `granted` scope list, and a `requests` list of scopes to test. For each requested scope the adapter prints `request=<scope> allowed=<true|false>`.

*1.1 Hierarchic matching*

Under hierarchic matching, a request is granted when a granted scope equals it exactly, or is a dot-separated ancestor of it: a broader scope `a.b` covers any more specific `a.b.c`, `a.b.c.d`, etc. A granted scope can never satisfy a request that is broader (shorter) than itself. An empty granted list grants nothing.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_hierarchic_scope.json`

```json
{
    "description": "Hierarchic scope matching. A request scope is granted when one of the granted scopes either equals it exactly, or is a dot-separated prefix of it (a broader scope such as 'a.b' covers any more specific 'a.b.c'); a granted scope can never satisfy a request that is broader than itself. The input names the matching strategy, a set of granted scopes, and a list of requested scopes; for each request the output reports whether it is allowed.",
    "cases": [
        {
            "input": {"op": "scope_match", "strategy": "hierarchic", "granted": ["foo.bar", "bar.baz", "baz.baz.1", "baz.baz.2", "baz.baz.3", "baz.baz.baz"], "requests": ["foo.bar.baz", "baz.baz.baz", "foo.bar", "foo", "bar.baz", "bar.baz.zad", "bar", "baz"]},
            "expected_output": "request=foo.bar.baz allowed=true\nrequest=baz.baz.baz allowed=true\nrequest=foo.bar allowed=true\nrequest=foo allowed=false\nrequest=bar.baz allowed=true\nrequest=bar.baz.zad allowed=true\nrequest=bar allowed=false\nrequest=baz allowed=false\n"
        }
    ]
}
```

*1.2 Wildcard matching*

Under wildcard matching, scopes are split on `.` into segments. A granted pattern matches a request when it has no more segments than the request and each segment matches positionally, where a `*` segment matches exactly one non-empty request segment. If the granted pattern has fewer segments than the request, its final segment must be `*` to match the remainder; a non-`*` final segment only matches when the two segment counts are equal. An empty request segment is never matched by `*`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_wildcard_scope.json`

```json
{
    "description": "Wildcard scope matching. Scopes are split on dots into segments; a granted pattern matches a request when it has no more segments than the request and every segment matches positionally, where a '*' segment matches exactly one non-empty request segment. A trailing pattern segment that is not '*' only matches when the segment counts are equal. The input names the strategy, the granted patterns, and the requested scopes; for each request the output reports whether it is allowed.",
    "cases": [
        {
            "input": {"op": "scope_match", "strategy": "wildcard", "granted": ["foo.*"], "requests": ["foo.bar", "foo.baz", "foo.bar.baz", "foo"]},
            "expected_output": "request=foo.bar allowed=true\nrequest=foo.baz allowed=true\nrequest=foo.bar.baz allowed=true\nrequest=foo allowed=false\n"
        }
    ]
}
```

*1.3 Exact matching*

Under exact matching, a request is granted only when it is byte-for-byte identical to one of the granted scopes. No prefix, hierarchy, or wildcard semantics apply.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_exact_scope.json`

```json
{
    "description": "Exact scope matching. A request scope is granted only when it is byte-for-byte identical to one of the granted scopes; no prefix or wildcard semantics apply. The input names the strategy, the granted scopes, and the requested scopes; for each request the output reports whether it is allowed.",
    "cases": [
        {
            "input": {"op": "scope_match", "strategy": "exact", "granted": ["foo.bar.baz", "foo.bar"], "requests": ["foo.bar.baz", "foo.bar", "foo.bar.baz.baz", "foo.bar.bar", "foo.bar.baz1", "foo.bar1"]},
            "expected_output": "request=foo.bar.baz allowed=true\nrequest=foo.bar allowed=true\nrequest=foo.bar.baz.baz allowed=false\nrequest=foo.bar.bar allowed=false\nrequest=foo.bar.baz1 allowed=false\nrequest=foo.bar1 allowed=false\n"
        }
    ]
}
```

---

### Feature 2: Argument-Set Comparison

**As a developer**, I want a set of comparison predicates over two lists of string arguments, so I can compare requested vs. allowed [a specific expected [a specific expected value string] string]s under different ordering/case rules.

**Expected Behavior / Usage:**

Each operation takes a `checks` array; every check provides a reference list (`arguments`) and either a probe list (`items`) or a single probe `[a specific expected [a specific expected value string] string]`. The adapter prints one result line per check.

*2.1 Unordered, case-insensitive set equality*

Two lists match only when they have the same length and every probe item is found in the reference list ignoring letter case and order. Because membership is case-insensitive, probe items that collapse to the same case-folded [a specific expected [a specific expected value string] string] (duplicates) make the matched set smaller than the reference length, so such inputs do NOT match. Output line: `matched=<true|false>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_match_unordered.json`

```json
{
    "description": "Unordered, case-insensitive set equality between a reference list and a probe list. The two lists match only when they have the same length and every probe item is present in the reference list ignoring letter case and ignoring order. Because membership is case-insensitive, repeated items that collapse to the same [a specific expected [a specific expected value string] string] cause a length mismatch and therefore do NOT match. The input is a list of checks, each with the reference 'arguments' and the probe 'items'; for each check the output reports whether they match.",
    "cases": [
        {
            "input": {"op": "args_matches", "checks": [{"arguments": [], "items": []}, {"arguments": ["foo", "bar"], "items": ["foo", "bar"]}, {"arguments": ["Foo", "Bar"], "items": ["Foo", "Bar"]}, {"arguments": ["foo", "foo"], "items": ["foo"]}, {"arguments": ["foo", "foo"], "items": ["bar", "foo"]}, {"arguments": ["foo", "bar"], "items": ["bar", "foo", "baz"]}, {"arguments": ["foo", "bar"], "items": ["foo"]}, {"arguments": ["foo", "bar"], "items": ["bar", "bar"]}, {"arguments": ["foo", "bar"], "items": ["baz"]}, {"arguments": [], "items": ["baz"]}, {"arguments": ["foo", "bar"], "items": ["bar", "foo"]}, {"arguments": ["fOo", "bar"], "items": ["foo", "BaR"]}, {"arguments": ["foo", "bar"], "items": ["FOO", "FOO", "bar"]}, {"arguments": ["foo", "foo"], "items": ["foo", "foo"]}]},
            "expected_output": "matched=true\nmatched=true\nmatched=true\nmatched=false\nmatched=false\nmatched=false\nmatched=false\nmatched=false\nmatched=false\nmatched=false\nmatched=true\nmatched=true\nmatched=false\nmatched=false\n"
        }
    ]
}
```

*2.2 Ordered, case-sensitive sequence equality*

Two lists match only when they have the same length and, at every index, the items are byte-for-byte identical. Order and case both matter; identical duplicates in identical positions are allowed. Output line: `matched=<true|false>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_match_ordered.json`

```json
{
    "description": "Ordered, case-sensitive sequence equality between a reference list and a probe list. The two lists match only when they have the same length and, at every position, the items are byte-for-byte identical. Order and letter case both matter, but exact duplicates in the same positions are allowed. The input is a list of checks, each with the reference 'arguments' and the probe 'items'; for each check the output reports whether they match.",
    "cases": [
        {
            "input": {"op": "args_matches_exact", "checks": [{"arguments": [], "items": []}, {"arguments": ["foo", "bar"], "items": ["foo", "bar"]}, {"arguments": ["Foo", "Bar"], "items": ["Foo", "Bar"]}, {"arguments": ["foo", "foo"], "items": ["foo"]}, {"arguments": ["foo", "foo"], "items": ["bar", "foo"]}, {"arguments": ["foo", "bar"], "items": ["bar", "foo", "baz"]}, {"arguments": ["foo", "bar"], "items": ["foo"]}, {"arguments": ["foo", "bar"], "items": ["bar", "bar"]}, {"arguments": ["foo", "bar"], "items": ["baz"]}, {"arguments": [], "items": ["baz"]}, {"arguments": ["foo", "bar"], "items": ["bar", "foo"]}, {"arguments": ["fOo", "bar"], "items": ["foo", "BaR"]}, {"arguments": ["foo", "foo"], "items": ["foo", "foo"]}]},
            "expected_output": "matched=true\nmatched=true\nmatched=true\nmatched=false\nmatched=false\nmatched=false\nmatched=false\nmatched=false\nmatched=false\nmatched=false\nmatched=false\nmatched=false\nmatched=true\n"
        }
    ]
}
```

*2.3 Contains-all (case-insensitive)*

Returns true when every probe item is present somewhere in the reference list, compared ignoring case. The reference list may hold extra, un-probed items. Output line: `has_all=<true|false>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_contains_all.json`

```json
{
    "description": "Case-insensitive 'contains all' check: every probe item must be present somewhere in the reference list, compared ignoring letter case and ignoring order. The reference list may contain extra items not probed. The input is a list of checks, each with the reference 'arguments' and the probe 'items'; for each check the output reports whether all probes are present.",
    "cases": [
        {
            "input": {"op": "args_has_all", "checks": [{"arguments": ["foo", "bar"], "items": ["foo", "bar"]}, {"arguments": ["foo", "bar"], "items": ["bar", "foo"]}, {"arguments": ["bar", "foo"], "items": ["foo"]}, {"arguments": ["foo", "bar"], "items": ["bar", "foo", "baz"]}, {"arguments": ["foo", "bar"], "items": ["foo"]}, {"arguments": ["foo", "bar"], "items": ["bar"]}, {"arguments": ["foo", "bar"], "items": ["baz"]}, {"arguments": [], "items": ["baz"]}]},
            "expected_output": "has_all=true\nhas_all=true\nhas_all=true\nhas_all=false\nhas_all=true\nhas_all=true\nhas_all=false\nhas_all=false\n"
        }
    ]
}
```

*2.4 Contains-any (case-insensitive)*

Returns true when at least one probe item is present in the reference list, compared ignoring case. Output line: `has_one=<true|false>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_contains_any.json`

```json
{
    "description": "Case-insensitive 'contains any' check: the result is true when at least one probe item is present in the reference list, compared ignoring letter case. The input is a list of checks, each with the reference 'arguments' and the probe 'items'; for each check the output reports whether any probe is present.",
    "cases": [
        {
            "input": {"op": "args_has_one", "checks": [{"arguments": ["baz", "bar"], "items": ["foo", "bar"]}, {"arguments": ["foo", "baz"], "items": ["foo", "bar"]}, {"arguments": ["baz"], "items": ["foo", "bar"]}]},
            "expected_output": "has_one=true\nhas_one=true\nhas_one=false\n"
        }
    ]
}
```

*2.5 Single-[a specific expected [a specific expected value string] string] equality*

Returns true only when the reference list holds exactly one item that is byte-for-byte identical to the probe `[a specific expected [a specific expected value string] string]`. Lists of length 0 or >1 never match; a multi-word probe is never split. Output line: `matched=<true|false>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_5_single_[a specific expected [a specific expected value string] string].json`

```json
{
    "description": "Single-[a specific expected [a specific expected value string] string] equality: the result is true only when the reference list holds exactly one item and that item is byte-for-byte identical to the probe [a specific expected [a specific expected value string] string]. A list with zero or multiple items never matches, and a multi-word probe is never split. The input is a list of checks, each with the reference 'arguments' and a single probe '[a specific expected [a specific expected value string] string]'; for each check the output reports whether it matches.",
    "cases": [
        {
            "input": {"op": "args_exact_one", "checks": [{"arguments": ["foo"], "[a specific expected [a specific expected value string] string]": "foo"}, {"arguments": ["foo", "bar"], "[a specific expected [a specific expected value string] string]": "foo"}, {"arguments": ["foo", "bar"], "[a specific expected [a specific expected value string] string]": "bar"}, {"arguments": ["foo", "bar"], "[a specific expected [a specific expected value string] string]": "baz"}, {"arguments": [], "[a specific expected [a specific expected value string] string]": "baz"}, {"arguments": ["foo", "bar"], "[a specific expected [a specific expected value string] string]": "foo bar"}]},
            "expected_output": "matched=true\nmatched=false\nmatched=false\nmatched=false\nmatched=false\nmatched=false\n"
        }
    ]
}
```

*2.6 Space-joined equality*

The reference list is joined into one string with a single space between items, and the result is true when that joined string equals the probe `[a specific expected [a specific expected value string] string]` exactly. Thus probe `"foo bar"` matches the two-item list `["foo","bar"]`. Output line: `matched=<true|false>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_6_space_joined.json`

```json
{
    "description": "Space-joined equality: the reference list is joined into a single string using one space between items, and the result is true when that joined string is byte-for-byte identical to the probe [a specific expected [a specific expected value string] string]. Thus a probe like 'foo bar' matches a two-item list of 'foo' and 'bar'. The input is a list of checks, each with the reference 'arguments' and a single probe '[a specific expected [a specific expected value string] string]'; for each check the output reports whether it matches.",
    "cases": [
        {
            "input": {"op": "args_exact_join", "checks": [{"arguments": ["foo"], "[a specific expected [a specific expected value string] string]": "foo"}, {"arguments": ["foo", "bar"], "[a specific expected [a specific expected value string] string]": "foo"}, {"arguments": ["foo", "bar"], "[a specific expected [a specific expected value string] string]": "bar"}, {"arguments": ["foo", "bar"], "[a specific expected [a specific expected value string] string]": "baz"}, {"arguments": [], "[a specific expected [a specific expected value string] string]": "baz"}, {"arguments": ["foo", "bar"], "[a specific expected [a specific expected value string] string]": "foo bar"}]},
            "expected_output": "matched=true\nmatched=false\nmatched=false\nmatched=false\nmatched=false\nmatched=true\n"
        }
    ]
}
```

---

### Feature 3: String Utilities

**As a developer**, I want two low-level string helpers — case-insensitive membership and minimal JSON escaping — so I can reuse them across the matching layer.

**Expected Behavior / Usage:**

*3.1 Case-insensitive membership*

Given a `checks` array of `{needle, haystack}`, report for each whether the needle occurs in the haystack list comparing ignoring letter case. Output line: `present=<true|false>`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_membership.json`

```json
{
    "description": "Case-insensitive membership test: report whether a needle string is present in a haystack list, comparing ignoring letter case. The input is a list of checks, each with a 'needle' and a 'haystack'; for each check the output reports whether the needle is present.",
    "cases": [
        {
            "input": {"op": "string_in_slice", "checks": [{"needle": "foo", "haystack": ["foo", "bar"]}, {"needle": "bar", "haystack": ["foo", "bar"]}, {"needle": "baz", "haystack": ["foo", "bar"]}, {"needle": "foo", "haystack": ["bar"]}, {"needle": "bar", "haystack": ["bar"]}, {"needle": "foo", "haystack": []}]},
            "expected_output": "present=true\npresent=true\npresent=false\npresent=false\npresent=true\npresent=false\n"
        }
    ]
}
```

*3.2 Minimal JSON string escaping*

Given a raw `[a specific expected [a specific expected value string] string]`, produce a string safe to embed between JSON double quotes: escape the backslash to `\\`, escape the double quote to `\"`, and escape every control character (code points U+0000–U+001F) as a six-character lowercase `\u00xx` sequence (for example newline becomes `\u000a` and tab becomes `\u0009`). All other characters, including printable punctuation, pass through unchanged. The output is the escaped string on its own line. Note: the escaping does NOT use the short forms `\n`/`\t`; control characters always use the `\u00xx` form.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_json_escape.json`

```json
{
    "description": "Minimal JSON string escaping: produce a string safe to place inside JSON double quotes by escaping the backslash, the double-quote character, and every control character (code points U+0000 through U+001F) as a six-character \\u00xx sequence. Ordinary characters, including printable punctuation, pass through unchanged. The input supplies the raw '[a specific expected [a specific expected value string] string]'; the output is the escaped form on its own line.",
    "cases": [
        {
            "input": {"op": "escape_json", "[a specific expected [a specific expected value string] string]": "foo\"bar"},
            "expected_output": "foo\\\"bar\n"
        },
        {
            "input": {"op": "escape_json", "[a specific expected [a specific expected value string] string]": "foo\n\tbar"},
            "expected_output": "foo\\u000a\\u0009bar\n"
        }
    ]
}
```

---

### Feature 4: Audience Matching

**As a developer**, I want to check that every requested audience is whitelisted, under either URI-aware or exact-string rules, so I can validate token audiences.

**Expected Behavior / Usage:**

Each operation takes a `checks` array of `{whitelist, requested}` string lists. A check passes (all requested audiences allowed) or fails. An empty `requested` list always passes. Output line per check: `allowed=<true|false>`.

*4.1 URI-aware audience matching*

Each requested audience is parsed as a URL and is allowed when some whitelisted audience (also parsed) shares the same scheme and host and has a path that either equals the requested path, equals it ignoring a single trailing slash, or is a path-segment prefix of it (so a whitelisted `.../users` covers `.../users/1234` and `.../users/`). Inputs that are not URLs parse to empty scheme/host and therefore only match an identical whitelist entry under these same rules. The whole check fails if any single requested audience is not allowed.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_audience_uri.json`

```json
{
    "description": "URI-aware audience matching. Each requested audience is allowed only when some whitelisted audience has the same scheme and host and a path that either equals the requested path or is a prefix of it at a path-segment boundary (a trailing slash on either side is ignored). An empty request list is always allowed. Strings that are not URLs are compared by these same URL rules (empty scheme/host), so plain tokens match only an identical whitelist entry. The input is a list of checks, each with a 'whitelist' and the 'requested' audiences; for each check the output reports whether all requested audiences are allowed.",
    "cases": [
        {
            "input": {"op": "audience_default", "checks": [{"whitelist": [], "requested": []}, {"whitelist": ["http://foo/bar"], "requested": []}, {"whitelist": [], "requested": ["http://foo/bar"]}, {"whitelist": ["https://cloud.ory.sh/api/users"], "requested": ["https://cloud.ory.sh/api/users"]}, {"whitelist": ["https://cloud.ory.sh/api/users"], "requested": ["https://cloud.ory.sh/api/users/"]}, {"whitelist": ["https://cloud.ory.sh/api/users/"], "requested": ["https://cloud.ory.sh/api/users"]}, {"whitelist": ["https://cloud.ory.sh/api/users"], "requested": ["https://cloud.ory.sh/api/users/1234"]}, {"whitelist": ["https://cloud.ory.sh/api/users"], "requested": ["https://cloud.ory.sh/api/users", "https://cloud.ory.sh/api/users/", "https://cloud.ory.sh/api/users/1234"]}, {"whitelist": ["https://cloud.ory.sh/api/users", "https://cloud.ory.sh/api/tenants"], "requested": ["https://cloud.ory.sh/api/users", "https://cloud.ory.sh/api/users/", "https://cloud.ory.sh/api/users/1234", "https://cloud.ory.sh/api/tenants"]}, {"whitelist": ["https://cloud.ory.sh/api/users"], "requested": ["https://cloud.ory.sh/api/users1234"]}, {"whitelist": ["https://cloud.ory.sh/api/users"], "requested": ["http://cloud.ory.sh/api/users"]}, {"whitelist": ["https://cloud.ory.sh/api/users"], "requested": ["https://cloud.ory.sh:8000/api/users"]}, {"whitelist": ["https://cloud.ory.sh/api/users"], "requested": ["https://cloud.ory.xyz/api/users"]}, {"whitelist": ["foobar"], "requested": ["foobar"]}, {"whitelist": ["foo bar"], "requested": ["foo bar"]}, {"whitelist": ["zoo", "bar"], "requested": ["zoo"]}, {"whitelist": ["zoo"], "requested": ["zoo", "bar"]}, {"whitelist": ["foobar"], "requested": ["foobar/"]}, {"whitelist": ["foobar/"], "requested": ["foobar"]}]},
            "expected_output": "allowed=true\nallowed=true\nallowed=false\nallowed=true\nallowed=true\nallowed=true\nallowed=true\nallowed=true\nallowed=true\nallowed=false\nallowed=false\nallowed=false\nallowed=false\nallowed=true\nallowed=true\nallowed=true\nallowed=false\nallowed=true\nallowed=true\n"
        }
    ]
}
```

*4.2 Exact-string audience matching*

Each requested audience is allowed only when it is byte-for-byte identical to some whitelisted audience. No URL parsing and no trailing-slash tolerance. The whole check fails if any requested audience is not present verbatim.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_audience_exact.json`

```json
{
    "description": "Exact-string audience matching. Each requested audience is allowed only when it is byte-for-byte identical to some whitelisted audience; no URL parsing or trailing-slash tolerance applies. An empty request list is always allowed. The input is a list of checks, each with a 'whitelist' and the 'requested' audiences; for each check the output reports whether all requested audiences are allowed.",
    "cases": [
        {
            "input": {"op": "audience_exact", "checks": [{"whitelist": [], "requested": []}, {"whitelist": ["http://foo/bar"], "requested": []}, {"whitelist": [], "requested": ["http://foo/bar"]}, {"whitelist": ["https://cloud.ory.sh/api/users"], "requested": ["https://cloud.ory.sh/api/users"]}, {"whitelist": ["https://cloud.ory.sh/api/users"], "requested": ["https://cloud.ory.sh/api/users/"]}, {"whitelist": ["https://cloud.ory.sh/api/users/"], "requested": ["https://cloud.ory.sh/api/users/"]}, {"whitelist": ["https://cloud.ory.sh/api/users/"], "requested": ["https://cloud.ory.sh/api/users"]}, {"whitelist": ["https://cloud.ory.sh/api/users"], "requested": ["https://cloud.ory.sh/api/users/1234"]}, {"whitelist": ["https://cloud.ory.sh/api/users"], "requested": ["https://cloud.ory.sh/api/users", "https://cloud.ory.sh/api/users/", "https://cloud.ory.sh/api/users/1234"]}, {"whitelist": ["https://cloud.ory.sh/api/users"], "requested": ["https://cloud.ory.sh/api/users1234"]}, {"whitelist": ["foobar"], "requested": ["foobar"]}, {"whitelist": ["zoo", "bar"], "requested": ["zoo"]}, {"whitelist": ["zoo"], "requested": ["zoo", "bar"]}, {"whitelist": ["foobar"], "requested": ["foobar/"]}, {"whitelist": ["foobar/"], "requested": ["foobar"]}]},
            "expected_output": "allowed=true\nallowed=true\nallowed=false\nallowed=true\nallowed=false\nallowed=true\nallowed=false\nallowed=false\nallowed=false\nallowed=false\nallowed=true\nallowed=true\nallowed=false\nallowed=false\nallowed=false\n"
        }
    ]
}
```

---

### Feature 5: Redirect-URI Validation

**As a developer**, I want helpers that classify and match redirect URIs, so I can enforce OAuth 2.0 redirect rules.

**Expected Behavior / Usage:**

*5.1 Loopback / localhost detection*

Given a `urls` list, report for each whether its host is a localhost address: host exactly `localhost`, `127.0.0.1`, or `::1`, or any host ending with the suffix `.localhost`. An optional port is ignored. Output line: `localhost=<true|false>`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_localhost.json`

```json
{
    "description": "Loopback / localhost host detection for a redirect URI. A URL is treated as localhost when its host name is exactly 'localhost', '127.0.0.1', or '::1', or when it ends with the suffix '.localhost'; an optional port does not change the result. The input is a list of URL strings; for each URL the output reports whether it is a localhost address.",
    "cases": [
        {
            "input": {"op": "redirect_is_localhost", "urls": ["https://foo.bar", "https://localhost", "https://localhost:1234", "https://127.0.0.1:1234", "https://127.0.0.1", "https://test.localhost:1234", "https://test.localhost"]},
            "expected_output": "localhost=false\nlocalhost=true\nlocalhost=true\nlocalhost=true\nlocalhost=true\nlocalhost=true\nlocalhost=true\n"
        }
    ]
}
```

*5.2 Transport-security check*

Given a `urls` list, report for each whether the redirect URI is considered transport-secure. A URI is secure unless it uses the `http` scheme with a non-localhost host: `https` is always secure, plain `http` is secure only for localhost addresses (per 5.1), and any non-http scheme (e.g. a custom app scheme) is considered secure. Output line: `secure=<true|false>`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_secure.json`

```json
{
    "description": "Transport-security check for a redirect URI. A URL is considered secure unless it uses the 'http' scheme with a non-localhost host; 'https' is always secure, plain 'http' is secure only for localhost addresses, and non-http schemes (custom app schemes) are considered secure. The input is a list of URL strings; for each URL the output reports whether it is secure.",
    "cases": [
        {
            "input": {"op": "redirect_is_secure", "urls": ["http://google.com", "https://google.com", "http://localhost", "http://test.localhost", "http://127.0.0.1/", "http://[::1]/", "http://127.0.0.1:8080/", "http://[::1]:8080/", "http://testlocalhost", "wta://auth"]},
            "expected_output": "secure=false\nsecure=true\nsecure=true\nsecure=true\nsecure=true\nsecure=true\nsecure=true\nsecure=true\nsecure=false\nsecure=true\n"
        }
    ]
}
```

*5.3 Strict transport-security check*

Given a `urls` list, report for each whether the redirect URI passes the stricter rule: only `https`, or `http` pointing at a localhost address, is accepted. Every other scheme — including custom application schemes — is rejected. Output line: `strict_secure=<true|false>`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_secure_strict.json`

```json
{
    "description": "Strict transport-security check for a redirect URI. Only 'https', or 'http' pointing at a localhost address, is accepted; every other scheme, including custom application schemes, is rejected. The input is a list of URL strings; for each URL the output reports whether it passes the strict check.",
    "cases": [
        {
            "input": {"op": "redirect_is_secure_strict", "urls": ["http://google.com", "https://google.com", "http://localhost", "http://test.localhost", "http://127.0.0.1/", "http://[::1]/", "http://127.0.0.1:8080/", "http://[::1]:8080/", "http://testlocalhost", "wta://auth"]},
            "expected_output": "strict_secure=false\nstrict_secure=true\nstrict_secure=true\nstrict_secure=true\nstrict_secure=true\nstrict_secure=true\nstrict_secure=true\nstrict_secure=true\nstrict_secure=false\nstrict_secure=false\n"
        }
    ]
}
```

*5.4 Registered redirect-URI matching*

Given a `checks` array of `{registered, request}` (where `registered` is the client's list of pre-registered redirect URIs and `request` is the requested redirect URI), resolve the effective redirect URI. Rules: (a) if `request` is empty and the client registered exactly one redirect URI that is itself a valid absolute redirect URI, use that registered URI; (b) otherwise `request` must match a registered URI by simple string equality, EXCEPT that for loopback addresses (scheme `http` with host `127.0.0.1` or `[::1]`) the port is ignored, so a registered loopback URI matches the same hostname/path/query on any requested port (the requested URI, with its port, is what gets resolved); (c) the resolved URI must additionally be a valid absolute redirect URI (absolute, with a scheme, and no fragment). On success print `redirect_uri=<resolved-uri>`; on any failure print the neutral line `error=redirect_uri_mismatch`. A malformed request URI is a failure.

**Test Cases:** `rcb_tests/public_test_cases/feature5_4_redirect_match.json`

```json
{
    "description": "Match a requested redirect URI against a client's pre-registered redirect URIs. If the requested URI is empty and the client registered exactly one valid redirect URI, that registered URI is used. Otherwise the requested URI must match a registered one by simple string comparison, with one exception: for loopback addresses (http with host 127.0.0.1 or [::1]) the port is ignored, so a registered loopback URI matches the same path/query on any port. A matched URI must itself be a valid absolute redirect URI (absolute, no fragment). On success the resolved redirect URI is returned; otherwise a neutral mismatch error is reported. The input is a list of checks, each with the client's 'registered' URIs and the 'request' URI; for each check the output reports the resolved URI or an error.",
    "cases": [
        {
            "input": {"op": "redirect_match", "checks": [{"registered": [""], "request": "https://foo.com/cb"}, {"registered": ["wta://auth"], "request": "wta://auth"}, {"registered": ["wta:///auth"], "request": "wta:///auth"}, {"registered": ["wta://foo/auth"], "request": "wta://foo/auth"}, {"registered": ["https://bar.com/cb"], "request": "https://foo.com/cb"}, {"registered": ["https://bar.com/cb"], "request": ""}, {"registered": [""], "request": ""}, {"registered": ["https://bar.com/cb"], "request": "https://bar.com/cb"}, {"registered": ["https://bar.com/cb"], "request": "https://bar.com/cb123"}, {"registered": ["http://[::1]"], "request": "http://[::1]:1024"}, {"registered": ["http://[::1]"], "request": "http://[::1]:1024/cb"}, {"registered": ["http://[::1]/cb"], "request": "http://[::1]:1024/cb"}, {"registered": ["http://[::1]"], "request": "http://foo.bar/bar"}, {"registered": ["http://127.0.0.1"], "request": "http://127.0.0.1:1024"}, {"registered": ["http://127.0.0.1/cb"], "request": "http://127.0.0.1:64000/cb"}, {"registered": ["http://127.0.0.1"], "request": "http://127.0.0.1:64000/cb"}, {"registered": ["http://127.0.0.1"], "request": "http://127.0.0.1"}, {"registered": ["http://127.0.0.1/Cb"], "request": "http://127.0.0.1:8080/Cb"}, {"registered": ["http://127.0.0.1"], "request": "http://foo.bar/bar"}, {"registered": ["http://127.0.0.1"], "request": ":/invalid.uri)bar"}, {"registered": ["http://127.0.0.1:8080/cb"], "request": "http://127.0.0.1:8080/Cb"}, {"registered": ["http://127.0.0.1:8080/cb"], "request": "http://127.0.0.1:8080/cb?foo=bar"}, {"registered": ["http://127.0.0.1:8080/cb?foo=bar"], "request": "http://127.0.0.1:8080/cb?foo=bar"}, {"registered": ["http://127.0.0.1:8080/cb?foo=bar"], "request": "http://127.0.0.1:8080/cb?baz=bar&foo=bar"}, {"registered": ["http://127.0.0.1:8080/cb?foo=bar&baz=bar"], "request": "http://127.0.0.1:8080/cb?baz=bar&foo=bar"}, {"registered": ["https://www.ory.sh/cb"], "request": "http://127.0.0.1:8080/cb"}, {"registered": ["http://127.0.0.1:8080/cb"], "request": "https://www.ory.sh/cb"}, {"registered": ["web+application://callback"], "request": "web+application://callback"}, {"registered": ["https://google.com/?foo=bar%20foo+baz"], "request": "https://google.com/?foo=bar%20foo+baz"}]},
            "expected_output": "error=redirect_uri_mismatch\nredirect_uri=wta://auth\nredirect_uri=wta:///auth\nredirect_uri=wta://foo/auth\nerror=redirect_uri_mismatch\nredirect_uri=https://bar.com/cb\nerror=redirect_uri_mismatch\nredirect_uri=https://bar.com/cb\nerror=redirect_uri_mismatch\nredirect_uri=http://[::1]:1024\nerror=redirect_uri_mismatch\nredirect_uri=http://[::1]:1024/cb\nerror=redirect_uri_mismatch\nredirect_uri=http://127.0.0.1:1024\nredirect_uri=http://127.0.0.1:64000/cb\nerror=redirect_uri_mismatch\nredirect_uri=http://127.0.0.1\nredirect_uri=http://127.0.0.1:8080/Cb\nerror=redirect_uri_mismatch\nerror=redirect_uri_mismatch\nerror=redirect_uri_mismatch\nerror=redirect_uri_mismatch\nredirect_uri=http://127.0.0.1:8080/cb?foo=bar\nerror=redirect_uri_mismatch\nerror=redirect_uri_mismatch\nerror=redirect_uri_mismatch\nerror=redirect_uri_mismatch\nredirect_uri=web+application://callback\nredirect_uri=https://google.com/?foo=bar%20foo+baz\n"
        }
    ]
}
```

---

### Feature 6: Parameter Encoding Into A URL Fragment

**As a developer**, I want to write a parameter into the fragment component of a URL, so I can build redirect responses that carry data in the fragment.

**Expected Behavior / Usage:**

Given a base `url` and a `fragment` map of a single key to a single-element [a specific expected [a specific expected value string] string] list, write `key=[a specific expected [a specific expected value string] string]` into the URL's fragment (replacing any existing fragment) while preserving the scheme, host, and query of the base URL. The output is the serialized URL; when serialized, characters in the fragment that require percent-encoding (such as a space, which becomes `%20`) are encoded, while reserved characters that are legal in a fragment (such as `:` and `*`) are left as-is. Output: the serialized URL on its own line.

**Test Cases:** `rcb_tests/public_test_cases/feature6_fragment_encode.json`

```json
{
    "description": "Encode a single parameter (key with one [a specific expected [a specific expected value string] string]) into the fragment component of a URL. The given key and [a specific expected [a specific expected value string] string] are written as 'key=[a specific expected [a specific expected value string] string]' into the URL fragment, replacing any existing fragment and preserving the rest of the URL (scheme, host, query). When the resulting URL is serialized, characters in the fragment that require percent-encoding (such as a space) are encoded. The input supplies the base 'url' and a 'fragment' map of one key to a single-element [a specific expected [a specific expected value string] string] list; the output is the serialized URL including the new fragment.",
    "cases": [
        {
            "input": {"op": "fragment_encode", "url": "http://google.com", "fragment": {"code": ["567060896"]}},
            "expected_output": "http://google.com#code=567060896\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the matching, comparison, validation, and encoding functions described above, organized into cohesive modules (scope strategies, argument-set comparison, string utilities, audience matching, redirect-URI validation, parameter encoding). The core logic must be free of stdin/stdout and JSON handling.

2. **The Execution/Test Adapter:** A runnable program (entry point) that reads a single JSON object from stdin, dispatches on its `op` field to the appropriate core function(s), and prints the contract output to stdout. It must translate any native error into the neutral `error=<category>` form and never expose host-language runtime details. The adapter is logically (ideally physically) separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- align with the IP address validation utility used in the core routing module
- apply the security heuristic defined in the security gateway middleware
