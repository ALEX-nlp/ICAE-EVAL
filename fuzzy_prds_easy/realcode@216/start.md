## Product Requirement Document

# Secure HTTP Response Header Engine

## Project Goal

Build a configurable engine that hardens HTTP responses by attaching a curated
set of security-related response headers. The engine accepts a single
declarative configuration command describing which protections to apply (and how
to parameterise each one), runs against an incoming request, and produces the
exact set of response headers a browser would receive. The goal is a faithful,
deterministic translation from "what protections do I want" to "what header
name/value pairs are emitted on the wire", including the precedence, formatting
and validation rules that make each header standards-compliant.

## Background & Problem

Web applications are expected to ship a baseline of defensive HTTP response
headers — controls for transport security, framing, content-type sniffing,
referrer leakage, cross-origin isolation, content security policy, cache
behaviour, and data clearing. Hand-writing these headers is error prone: each
header has its own grammar (quoting rules, token separators, ordering,
conditional fields), several headers interact (one cannot be enabled without
another), and some values must be validated before a response is allowed to go
out. Applying the wrong string silently weakens the protection.

This project centralises that knowledge into one engine so that an application
can declare its intent once and rely on the engine to emit byte-correct headers,
to skip headers that were not requested, to enforce cross-header dependencies,
and to refuse configurations that would produce a malformed or unsafe header.

## Architecture & Engineering Constraints

The engine is exercised as a command-line program for testing purposes:

- **Input.** The program reads exactly one JSON object from standard input. The
  object describes the request and the desired protections. All fields are
  optional unless stated otherwise. Recognised top-level fields:
  - `request_path` (string, default `"/"`): the path of the incoming request.
  - `with_config` (boolean, default `true`): when `false`, the engine is invoked
    with **no** configuration at all.
  - `preset` (string): when set to `"default"`, the recommended baseline bundle
    is applied (see Feature 1). When a preset is used, the `headers` object is
    ignored.
  - `ignore_paths` (array of strings): request paths for which the engine must
    emit no headers at all.
  - `headers` (object): a map selecting and parameterising individual headers.
    Each recognised key and its sub-fields are defined in the corresponding
    feature below. A header is emitted only if its key is present.

- **Output.** The program writes the resulting response headers to standard
  output, one header per line, formatted as `Name: value`, with a trailing
  newline after every line. Lines are sorted in ascending ordinal order by
  header name so the output is deterministic. When the request produces no
  headers at all, the program writes the single line `<no-headers>`.

- **Errors.** When a configuration is invalid the program writes a neutral,
  language-independent error contract instead of headers:
  - `error=missing_configuration` — the engine was invoked without configuration.
  - `error=embedder_policy_requires_resource_policy` — an embedder-isolation
    header was requested without its mandatory companion header.
  - `error=missing_required_value` followed by a second line `field=<name>` —
    a required value (`report_uri`, `path`, or `directives`) was absent or empty.
  - `error=invalid_configuration` — any other rejected configuration.

  Error output must contain only these neutral tokens; no host-language type
  names, stack traces or runtime message fragments may appear.

Engineering constraints:

- Header emission must be **conditional**: only requested headers appear.
- Header **values must be byte-exact** — quoting, separators, ordering and
  optional fields all matter and are asserted directly against stdout.
- Cross-header **dependencies and validation** must be enforced before output.
- Output ordering must be **stable** regardless of insertion order.

## Core Features

### Feature 1: Recommended baseline bundle

Applying the recommended default bundle (`preset: "default"`) emits the engine's
full opinionated set of headers in one step: transport security with
sub-domains, deny framing, disabled legacy XSS auditor, no-sniff, a self-only
content security policy, no permitted cross-domain policies, no-referrer,
non-storing cache control, and the three cross-origin isolation headers. All
header values use their canonical wire form, and the output is sorted by header
name.

Example:

```json
{
  "input": { "preset": "default", "request_path": "/hello" },
  "expected_output": "[the canonical set of default headers]\n[the canonical set of default headers]\n[the canonical set of default headers]\n[the canonical set of default headers]\n[the canonical set of default headers]\n[the canonical set of default headers]\n[the canonical set of default headers]\n[the canonical set of default headers]\n[the canonical set of default headers]\n[the canonical set of default headers]\n[the canonical set of default headers]\n"
}
```

### Feature 2: Strict transport security

`headers.strict_transport_security` enables the `Strict-Transport-Security`
header. Sub-fields: `max_age` (integer seconds, default `31536000`) and
`include_subdomains` (boolean, default `true`). The value is
`max-age=<n>` optionally followed by `;includeSubDomains`. The header is absent
when not requested.

```json
{
  "input": { "headers": { "strict_transport_security": {} } },
  "expected_output": "[the canonical set of default headers]\n"
}
```

```json
{
  "input": { "headers": { "strict_transport_security": { "max_age": 12345, "include_subdomains": false } } },
  "expected_output": "Strict-Transport-Security: max-age=12345\n"
}
```

```json
{
  "input": { "headers": {} },
  "expected_output": "<no-headers>\n"
}
```

### Feature 3: Framing control

`headers.x_frame_options` enables the `X-Frame-Options` header. Sub-field
`directive` is one of `deny`, `sameorigin`, `allowfrom`, `allowall` (default
`deny`). For `allowfrom`, the `domain` sub-field supplies the permitted origin
and the emitted value is `allow-from: (<domain>)`. The header is absent when not
requested.

```json
{
  "input": { "headers": { "x_frame_options": { "directive": "deny" } } },
  "expected_output": "[the canonical set of default headers]\n"
}
```

```json
{
  "input": { "headers": { "x_frame_options": { "directive": "allowfrom", "domain": "https://example.com" } } },
  "expected_output": "X-Frame-Options: allow-from: (https://example.com)\n"
}
```

### Feature 4: Content-type sniffing protection

`headers.content_type_options` enables the `X-Content-Type-Options` header with
the fixed value `nosniff`. The header is absent when not requested.

```json
{
  "input": { "headers": { "content_type_options": {} } },
  "expected_output": "[the canonical set of default headers]\n"
}
```

```json
{
  "input": { "headers": {} },
  "expected_output": "<no-headers>\n"
}
```

### Feature 5: Legacy XSS auditor control

`headers.xss_protection` enables the `X-XSS-Protection` header with the value
`0`, which disables the deprecated browser XSS auditor in line with current
guidance. The header is absent when not requested.

```json
{
  "input": { "headers": { "xss_protection": {} } },
  "expected_output": "[the canonical set of default headers]\n"
}
```

```json
{
  "input": { "headers": {} },
  "expected_output": "<no-headers>\n"
}
```

### Feature 6: Referrer policy

`headers.referrer_policy` enables the `Referrer-Policy` header. Sub-field
`value` is one of `no-referrer`, `no-referrer-when-downgrade`, `origin`,
`origin-when-cross-origin`, `same-origin`, `strict-origin`,
`strict-origin-when-cross-origin`, `unsafe-url` (default `no-referrer`). The
emitted value is the token verbatim. The header is absent when not requested.

```json
{
  "input": { "headers": { "referrer_policy": {} } },
  "expected_output": "[the canonical set of default headers]\n"
}
```

```json
{
  "input": { "headers": { "referrer_policy": { "value": "strict-origin-when-cross-origin" } } },
  "expected_output": "Referrer-Policy: strict-origin-when-cross-origin\n"
}
```

```json
{
  "input": { "headers": {} },
  "expected_output": "<no-headers>\n"
}
```

### Feature 7: Permitted cross-domain policies

`headers.permitted_cross_domain_policies` enables the
`X-Permitted-Cross-Domain-Policies` header. Sub-field `value` is one of `none`,
`master-only`, `by-content-type`, `by-ftp-file-type`, `all` (default `none`).
The emitted value is the token verbatim. The header is absent when not requested.

```json
{
  "input": { "headers": { "permitted_cross_domain_policies": { "value": "master-only" } } },
  "expected_output": "X-Permitted-Cross-Domain-Policies: master-only\n"
}
```

```json
{
  "input": { "headers": {} },
  "expected_output": "<no-headers>\n"
}
```

### Feature 8: Cache control

`headers.cache_control` enables the `Cache-Control` header. Sub-fields:
`private` (boolean, default `false`), `max_age` (integer, default `0`),
`no_cache` (boolean, default `false`), `no_store` (boolean, default `true`),
`must_revalidate` (boolean, default `false`). The value is produced by a strict
precedence: if `no_cache` then `no-cache`; else if `private` then `private`;
else if `must_revalidate` then `must-revalidate`; otherwise `max-age=<n>,` is
written and, when `no_store` is set, `no-store` is appended.

```json
{
  "input": { "headers": { "cache_control": {} } },
  "expected_output": "[the canonical set of default headers]\n"
}
```

```json
{
  "input": { "headers": { "cache_control": { "private": true } } },
  "expected_output": "Cache-Control: private\n"
}
```

```json
{
  "input": { "headers": { "cache_control": { "no_cache": true, "no_store": false } } },
  "expected_output": "Cache-Control: no-cache\n"
}
```

### Feature 9: Certificate transparency expectation

`headers.expect_ct` enables the `Expect-CT` header. Sub-fields: `report_uri`
(string), `max_age` (integer seconds, default `86400`), `enforce` (boolean,
default `false`). The value always begins with `max-age=<n>`; when `enforce` is
set, `, enforce` is appended; when `report_uri` is non-empty,
`, report-uri="<uri>"` is appended. The header is absent when not requested.

```json
{
  "input": { "headers": { "expect_ct": { "report_uri": "https://ex.com/r", "enforce": true } } },
  "expected_output": "Expect-CT: max-age=86400, enforce, report-uri=\"https://ex.com/r\"\n"
}
```

```json
{
  "input": { "headers": { "expect_ct": { "report_uri": "" } } },
  "expected_output": "Expect-CT: max-age=86400\n"
}
```

```json
{
  "input": { "headers": {} },
  "expected_output": "<no-headers>\n"
}
```

### Feature 10: Cross-origin resource policy

`headers.cross_origin_resource_policy` enables the
`Cross-Origin-Resource-Policy` header. Sub-field `value` is one of `same-origin`,
`same-site`, `cross-origin` (default `same-origin`). The emitted value is the
token verbatim. The header is absent when not requested.

```json
{
  "input": { "headers": { "cross_origin_resource_policy": {} } },
  "expected_output": "[the canonical set of default headers]\n"
}
```

```json
{
  "input": { "headers": {} },
  "expected_output": "<no-headers>\n"
}
```

### Feature 11: Cross-origin opener policy

`headers.cross_origin_opener_policy` enables the `Cross-Origin-Opener-Policy`
header. Sub-field `value` is one of `same-origin`, `same-origin-allow-popups`,
`unsafe-none` (default `same-origin`). The emitted value is the token verbatim.
The header is absent when not requested.

```json
{
  "input": { "headers": { "cross_origin_opener_policy": { "value": "same-origin-allow-popups" } } },
  "expected_output": "[the canonical set of default headers]-allow-popups\n"
}
```

```json
{
  "input": { "headers": {} },
  "expected_output": "<no-headers>\n"
}
```

### Feature 12: Cross-origin embedder policy (with dependency)

`headers.cross_origin_embedder_policy` enables the
`Cross-Origin-Embedder-Policy` header. Sub-field `value` is one of
`require-corp`, `unsafe-none` (default `require-corp`). This header has a hard
dependency: it may only be emitted when `cross_origin_resource_policy` is also
enabled. If the embedder policy is requested without the resource policy, the
configuration is rejected with `error=embedder_policy_requires_resource_policy`.
The header is absent when not requested.

```json
{
  "input": { "headers": { "cross_origin_resource_policy": {}, "cross_origin_embedder_policy": {} } },
  "expected_output": "[the canonical set of default headers]\n[the canonical set of default headers]\n"
}
```

```json
{
  "input": { "headers": { "cross_origin_embedder_policy": {} } },
  "expected_output": "error=embedder_policy_requires_resource_policy\n"
}
```

### Feature 13: Content security policy modes

`headers.content_security_policy` enables a content security policy. With no
extra fields the value contains the trailing directives
`block-all-mixed-content;upgrade-insecure-requests;`. Sub-fields:
- `sandbox` (array of sandbox tokens, e.g. `allow-forms`, `allow-scripts`,
  `allow-same-origin`): prepends a `sandbox <tokens>` directive.
- `legacy_compat` (boolean): additionally mirrors the policy into the
  `X-Content-Security-Policy` header.
- `report_only` (boolean) with `report_uri` (string, required when
  `report_only` is set): emits a `Content-Security-Policy-Report-Only` header
  whose value ends with `report-uri <uri>;`. An empty `report_uri` in
  report-only mode is rejected with `error=missing_required_value` /
  `field=report_uri`.

The header is absent when the policy is not requested.

```json
{
  "input": { "headers": { "content_security_policy": { "sandbox": ["allow-forms", "allow-scripts", "allow-same-origin"] } } },
  "expected_output": "Content-Security-Policy: sandbox allow-forms allow-scripts allow-same-origin;block-all-mixed-content;upgrade-insecure-requests;\n"
}
```

```json
{
  "input": { "headers": { "content_security_policy": { "report_only": true, "report_uri": "https://localhost:5001/report-uri" } } },
  "expected_output": "Content-Security-Policy-Report-Only: block-all-mixed-content;upgrade-insecure-requests;report-uri https://localhost:5001/report-uri;\n"
}
```

### Feature 14: Content security policy directive formatting

When `content_security_policy.directives` is supplied, it maps a CSP source-list
name (e.g. `script-src`, `img-src`, `style-src`, `default-src`, `base-uri`,
`object-src`, `frame-ancestors`, `connect-src`, `font-src`, `form-action`,
`manifest-src`, `media-src`, `frame-src`, `child-src`) to an ordered array of
tokens. Each token is either `{ "keyword": "<value>" }`, which is wrapped in
single quotes, or `{ "uri": "<value>" }`, which is emitted unquoted. The
formatting rules: exactly one space separates tokens (no leading, trailing, or
double spaces), the source list ends with a single semicolon, and a repeated URI
is not duplicated. The example cases below disable the block/upgrade directives
(`block_all_mixed_content` and `upgrade_insecure_requests` set to `false`) to
isolate the formatting of the source list.

```json
{
  "input": { "headers": { "content_security_policy": { "block_all_mixed_content": false, "upgrade_insecure_requests": false, "directives": { "script-src": [ { "keyword": "self" }, { "keyword": "unsafe-inline" }, { "keyword": "none" } ] } } } },
  "expected_output": "Content-Security-Policy: script-src 'self' 'unsafe-inline' 'none';\n"
}
```

```json
{
  "input": { "headers": { "content_security_policy": { "block_all_mixed_content": false, "upgrade_insecure_requests": false, "directives": { "img-src": [ { "keyword": "self" }, { "uri": "data:" }, { "uri": "https://cdn.abc.net" }, { "uri": "https://cdn.abc.org" } ] } } } },
  "expected_output": "Content-Security-Policy: img-src 'self' data: https://cdn.abc.net https://cdn.abc.org;\n"
}
```

### Feature 15: Clear-site-data for all responses

`headers.clear_site_data` enables the `Clear-Site-Data` header for every
response. Sub-field `directives` is an array of `cache`, `cookies`, `storage`,
or `*` (default `["cache","cookies","storage"]` when omitted or empty). Each
token is emitted quoted and comma-separated. A `*` (wildcard) collapses the whole
value to `"*"` and takes precedence over all other tokens; duplicate tokens are
removed. The header is absent when not requested.

```json
{
  "input": { "headers": { "clear_site_data": {} } },
  "expected_output": "Clear-Site-Data: \"cache\",\"cookies\",\"storage\"\n"
}
```

```json
{
  "input": { "headers": { "clear_site_data": { "directives": ["cache", "*", "cookies"] } } },
  "expected_output": "Clear-Site-Data: \"*\"\n"
}
```

```json
{
  "input": { "headers": {} },
  "expected_output": "<no-headers>\n"
}
```

### Feature 16: Path-scoped clear-site-data

Clear-Site-Data may be scoped to specific request paths. Two configuration
shapes are supported under `headers`:
- `clear_site_data_paths`: an object with a `paths` map (request path → token
  array) and an optional `default` token array for non-matching paths.
- `clear_site_data_add_paths`: an array of `{ "path": "...", "directives": [...] }`
  entries added one at a time.

The header is emitted only when the request path matches a configured entry. When
several configured paths are prefixes of the request path, the most specific
(longest) match wins. Configuring an entry with an empty `path` is rejected with
`error=missing_required_value` / `field=path`; an empty token list for an added
path is rejected with `error=missing_required_value` / `field=directives`.

```json
{
  "input": { "request_path": "/logout", "headers": { "clear_site_data_paths": { "paths": { "/logout": ["*"] } } } },
  "expected_output": "Clear-Site-Data: \"*\"\n"
}
```

```json
{
  "input": { "request_path": "/account/logout", "headers": { "clear_site_data_paths": { "paths": { "/account": ["cache"], "/account/logout": ["*"] } } } },
  "expected_output": "Clear-Site-Data: \"*\"\n"
}
```

```json
{
  "input": { "headers": { "clear_site_data_add_paths": [ { "path": "", "directives": ["cache"] } ] } },
  "expected_output": "error=missing_required_value\nfield=path\n"
}
```

### Feature 17: Request-handling contract

The engine enforces two operational rules. First, invoking it with no
configuration (`with_config: false`) is rejected with
`error=missing_configuration`. Second, when an `ignore_paths` list is in effect,
a request whose path is in the list receives **no** headers, while a request to
any other path receives the full configured bundle.

```json
{
  "input": { "with_config": false },
  "expected_output": "error=missing_configuration\n"
}
```

```json
{
  "input": { "preset": "default", "request_path": "/ignore-me", "ignore_paths": ["/ignore-me"] },
  "expected_output": "<no-headers>\n"
}
```

## Deliverables

1. A runnable program that reads one JSON configuration command from standard
   input and writes the resulting response headers (or the neutral error
   contract) to standard output, exactly as specified in
   *Architecture & Engineering Constraints* and the per-feature contracts above.
2. Conditional, byte-exact emission of every header in *Core Features*, with
   stable ordinal ordering of output lines and the `<no-headers>` sentinel when
   no header is produced.
3. Enforcement of cross-header dependencies and value validation, surfaced only
   through the neutral, language-independent error categories.
4. A test harness (`rcb_tests/test.sh`) that drives the program with the case
   files under `rcb_tests/test_cases/` (and, via `--cases-dir public_test_cases`,
   the public mirror), capturing raw stdout per case and comparing it against the
   expected output.


---
**Implementation notes:**
- follow the same formatting pattern as the Allow-From header parser
- match the token expansion logic used in the sandbox directive
