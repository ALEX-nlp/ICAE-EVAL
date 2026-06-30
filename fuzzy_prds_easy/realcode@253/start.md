## Product Requirement Document

# SAML2 Single Sign-On Message & Metadata Toolkit — Parsing, Value Semantics & Front-Channel Encoding

## Project Goal

Build a library that lets identity- and service-provider applications work with the SAML2 single sign-on protocol at the level of well-typed domain objects, so developers can parse and validate incoming protocol XML, reason about identifiers and timestamps with correct value semantics, and move messages across the browser front channel — without hand-writing brittle XML traversal, ad-hoc string comparisons, or bespoke URL (de)serialization for every integration.

---

## Background & Problem

SAML2 web single sign-on is defined by a family of XML documents (authentication requests, assertions, protocol responses, and provider metadata) plus a set of HTTP bindings that carry those documents between a browser, a service provider, and an identity provider. The documents are deeply nested, the mandatory-vs-optional rules are strict, timestamps must be UTC, identifiers compare by both a value and an optional format, and the redirect binding compresses and base64-encodes the payload into a URL query string.

Without a dedicated library, every integration re-implements the same fragile machinery: walking XML namespaces by hand, guessing which attributes are required, mishandling time zones, comparing identifiers with naive string equality, and re-deriving the deflate/base64 URL encoding. This is repetitive and error-prone, and subtle mistakes become security and interoperability bugs.

This library provides one well-defined contract for the load-bearing transformations: a UTC-only timestamp value type with validated conversions and ordering; a name-identifier type with precise equality semantics; readers that turn protocol/metadata XML into domain objects while reporting a normalized error category for any structural violation; and a redirect-binding decoder that recovers a message from a URL. Every structural error is reported as a neutral category line (for example `error=missing_attribute`), never as a host-language exception.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain. This is a multi-responsibility domain (value types, several distinct XML readers, error modelling, a front-channel binding); it MUST NOT be a single "god file". Output a clear, multi-file directory tree (e.g. value types, parsers, error model, bindings, and a separate execution adapter) that reflects a production-grade repository. Do not over-engineer, but strictly avoid monolithic files.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core logic must remain completely decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls to the core domain and rendering results to the line-oriented contract.

3. **Adherence to SOLID Design Principles:** Separate parsing, validation, error reporting, value semantics, binding (de)serialization, and output formatting into distinct logical units. The core readers must be open for extension (new element types) but closed for modification; error reporting must depend on an abstraction, not on the I/O layer.

4. **Robustness & Interface Design:** The public interface must be elegant and idiomatic to the target language, hiding internal complexity. Errors must be modeled properly (specific error categories / a structured error type) rather than relying on generic faults. Crucially, the line-oriented output contract is language-neutral: structural failures are surfaced as `error=<category>` lines and MUST NOT leak host-language runtime type names, stack traces, or runtime-generated message text.

---

## Core Features

### Feature 1: UTC Timestamp Value Type

**As a developer**, I want a timestamp value type that guarantees its instant is in UTC and supports correct ordering against offset-aware timestamps, so I can store and compare SAML time conditions without time-zone ambiguity.

**Expected Behavior / Usage:**

*1.1 Kind-validated construction — converting a tagged wall-clock timestamp into the UTC value*

A wall-clock timestamp arrives tagged with a time-zone-kind marker: `utc`, `local`, or `unspecified`. Conversion into the UTC value type succeeds only when the marker is `utc`. A marker of `local` or `unspecified` is rejected — with one exception: the zero/default timestamp (tick count `0`) is accepted when its marker is `unspecified` (it represents an uninitialised default), but is still rejected when marked `local`. On success the adapter prints the marker, an acceptance flag, and the resulting absolute tick count. On rejection it prints the marker, a `false` acceptance flag, and a neutral error category. Input is `{kind, year, month, day, hour, minute, second}`, or `{kind, ticks}` for the zero/default case.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_timestamp_kind_validation.json`

```json
{
    "description": "Convert a wall-clock timestamp tagged with a time-zone-kind marker into the domain UTC timestamp value. The conversion only accepts a timestamp explicitly marked as UTC; a timestamp marked as local or as having an unspecified zone is rejected. The sole exception is the zero/default timestamp, which is accepted when its marker is unspecified (representing the uninitialised default) but still rejected when marked local. On acceptance the resulting value is reported by its absolute tick count; on rejection a neutral error category is reported.",
    "cases": [
        {"input": {"action": "datetime_validate", "kind": "utc", "year": 2025, "month": 5, "day": 28, "hour": 21, "minute": 49, "second": 43}, "expected_output": "[a specific UTC literal prefix for timezones]\naccepted=true\nticks=638840657830000000\n"},
        {"input": {"action": "datetime_validate", "kind": "unspecified", "year": 2025, "month": 5, "day": 28, "hour": 21, "minute": 49, "second": 43}, "expected_output": "kind=unspecified\naccepted=false\nerror=non_utc_datetime_kind\n"},
        {"input": {"action": "datetime_validate", "kind": "unspecified", "ticks": 0}, "expected_output": "kind=unspecified\naccepted=true\nticks=0\n"}
    ]
}
```

*1.2 Ordering against an offset-aware timestamp*

Compare an offset-aware timestamp (a wall-clock time plus an integer hour offset from UTC) against a UTC timestamp using a relational operator. `lt` tests whether the offset timestamp is strictly earlier than the UTC timestamp; `gte` tests whether it is at or after it. Both operands are normalised to the same absolute instant first, so a positive offset shifts the offset timestamp to an earlier absolute instant. The output echoes both normalised operands (the offset operand in ISO-8601 with its offset; the UTC operand in ISO-8601 `Z` form), the operator, and the boolean result. Input is `{op, left:{year..second, offsetHours}, right:{year..second}}`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_timestamp_comparison.json`

```json
{
    "description": "Compare an offset-aware timestamp (a wall-clock time plus an hour offset from UTC) against a domain UTC timestamp using a relational operator. 'lt' tests whether the offset timestamp is strictly earlier than the UTC timestamp; 'gte' tests whether it is at or after it. Both operands are normalised to the same absolute instant before comparison, so the offset shifts the effective instant accordingly. The output echoes both normalised operands, the operator, and the boolean result.",
    "cases": [
        {"input": {"action": "datetime_compare", "op": "lt", "left": {"year": 2025, "month": 1, "day": 2, "hour": 3, "minute": 4, "second": 5, "offsetHours": 0}, "right": {"year": 2025, "month": 1, "day": 2, "hour": 3, "minute": 4, "second": 5}}, "expected_output": "left=2025-01-02T03:04:05+00:00\nright=2025-01-02T03:04:05Z\nop=lt\nresult=false\n"},
        {"input": {"action": "datetime_compare", "op": "lt", "left": {"year": 2025, "month": 1, "day": 2, "hour": 3, "minute": 4, "second": 4, "offsetHours": 0}, "right": {"year": 2025, "month": 1, "day": 2, "hour": 3, "minute": 4, "second": 5}}, "expected_output": "left=2025-01-02T03:04:04+00:00\nright=2025-01-02T03:04:05Z\nop=lt\nresult=true\n"},
        {"input": {"action": "datetime_compare", "op": "gte", "left": {"year": 2025, "month": 1, "day": 2, "hour": 3, "minute": 4, "second": 5, "offsetHours": 0}, "right": {"year": 2025, "month": 1, "day": 2, "hour": 3, "minute": 4, "second": 5}}, "expected_output": "left=2025-01-02T03:04:05+00:00\nright=2025-01-02T03:04:05Z\nop=gte\nresult=true\n"}
    ]
}
```

---

### Feature 2: Name Identifier Equality

**As a developer**, I want a name-identifier type with precise equality semantics, so I can compare subjects and issuers without subtle bugs around the optional format component.

**Expected Behavior / Usage:**

A name identifier carries a string `value` and an optional `format` URI.

*2.1 Identifier-to-identifier equality*

Two identifiers are equal exactly when both their `value` and their `format` agree (an absent format only matches an absent format). Equality is exposed two ways: a structural-equality check (`op` = `equals`) and an equality operator (`op` = `operator`). The operator additionally treats two absent identifiers as equal, and treats an absent identifier as unequal to any present identifier — including a present identifier whose own value and format happen to be absent. The output echoes each operand (`<side>.value`/`<side>.format`, or `<side>=null` for an absent identifier) and the boolean `result`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_nameid_equality.json`

```json
{
    "description": "Determine whether two name identifiers are equal. A name identifier carries a string value and an optional format URI. Two identifiers are equal exactly when both their value and their format agree (a missing format only matches a missing format). Equality is offered both as a structural-equality check ('equals') and as an equality operator ('operator'); the operator additionally treats two absent identifiers as equal and an absent identifier as unequal to a present one (even one whose value and format are themselves absent).",
    "cases": [
        {"input": {"action": "nameid_compare", "op": "equals", "left": {"value": "https://idp1.example.com"}, "right": {"value": "https://idp1.example.com"}}, "expected_output": "op=equals\nleft.value=https://idp1.example.com\nleft.format=\nright.value=https://idp1.example.com\nright.format=\nresult=true\n"},
        {"input": {"action": "nameid_compare", "op": "equals", "left": {"value": "https://idp1.example.com"}, "right": {"value": "https://idp2.example.com"}}, "expected_output": "op=equals\nleft.value=https://idp1.example.com\nleft.format=\nright.value=https://idp2.example.com\nright.format=\nresult=false\n"},
        {"input": {"action": "nameid_compare", "op": "equals", "left": {"value": "https://idp1.example.com"}, "right": null}, "expected_output": "op=equals\nleft.value=https://idp1.example.com\nleft.format=\nright=null\nresult=false\n"},
        {"input": {"action": "nameid_compare", "op": "operator", "left": null, "right": null}, "expected_output": "op=operator\nleft=null\nright=null\nresult=true\n"},
        {"input": {"action": "nameid_compare", "op": "operator", "left": {}, "right": null}, "expected_output": "op=operator\nleft.value=\nleft.format=\nright=null\nresult=false\n"}
    ]
}
```

*2.2 Identifier-to-string equality*

An identifier equals a bare string only when the identifier has no format set and its value equals the string; if the identifier carries any format, it never equals a bare string. This is exposed both as a structural-equality check (`op` = `equals`) against the string and as the equality operator (`op` = `operator`), where the bare string is first promoted to a format-less identifier. The string operand is echoed as `<side>.string`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_nameid_string_equality.json`

```json
{
    "description": "Determine whether a name identifier equals a bare string. A name identifier equals a string only when the identifier has no format set and its value equals the string. If the identifier carries any format, it never equals a bare string. This is offered both as a structural-equality check ('equals') against the string and as the equality operator ('operator'), where the bare string is first promoted to a format-less identifier.",
    "cases": [
        {"input": {"action": "nameid_compare", "op": "equals", "left": {"value": "https://idp1.example.com"}, "right": "https://idp1.example.com"}, "expected_output": "op=equals\nleft.value=https://idp1.example.com\nleft.format=\nright.string=https://idp1.example.com\nresult=true\n"},
        {"input": {"action": "nameid_compare", "op": "equals", "left": {"value": "https://idp1.example.com"}, "right": "xyz"}, "expected_output": "op=equals\nleft.value=https://idp1.example.com\nleft.format=\nright.string=xyz\nresult=false\n"},
        {"input": {"action": "nameid_compare", "op": "operator", "left": {"value": "https://idp1.example.com"}, "right": "https://idp1.example.com"}, "expected_output": "op=operator\nleft.value=https://idp1.example.com\nleft.format=\nright.string=https://idp1.example.com\nresult=true\n"}
    ]
}
```

---

### Feature 3: Authentication Request Parsing

**As a developer**, I want to parse a SAML2 authentication-request XML element into a domain object, so I can read the requesting service provider's parameters with mandatory-field validation.

**Expected Behavior / Usage:**

Input is `{xml}`: the authentication-request element. The mandatory shape requires an `ID`, a protocol `Version`, and an `IssueInstant` timestamp; these are surfaced as `id`, `version`, and `issueInstant` (normalised to ISO-8601 UTC). A present optional destination and issuer are surfaced when available. If a mandatory attribute (such as `Version`) is absent, parsing is rejected with `error=missing_attribute`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_authn_request_read.json`

```json
{
    "description": "Parse a SAML2 authentication-request XML element. The mandatory shape requires an ID, a protocol Version, and an IssueInstant timestamp; these are surfaced as id/version/issueInstant. The IssueInstant is normalised to ISO-8601 UTC. If a mandatory attribute (such as Version) is absent, parsing is rejected with a neutral error category identifying a missing attribute.",
    "cases": [
        {"input": {"action": "read_authn_request", "xml": "<saml:AuthnRequest xmlns:saml=\"urn:oasis:names:tc:SAML:2.0:protocol\" ID=\"x123\" Version=\"2.0\" IssueInstant=\"2023-11-24T22:44:14Z\" />"}, "expected_output": "id=x123\nversion=2.0\nissueInstant=2023-11-24T22:44:14Z\n"},
        {"input": {"action": "read_authn_request", "xml": "<saml:AuthnRequest xmlns:saml=\"urn:oasis:names:tc:SAML:2.0:protocol\" ID=\"x123\" IssueInstant=\"2023-11-24T22:44:14Z\" />"}, "expected_output": "error=missing_attribute\n"}
    ]
}
```

---

### Feature 4: Assertion Parsing

**As a developer**, I want to parse a SAML2 assertion XML element into a domain object with strict structural validation, so I can read the authenticated subject and reject malformed assertions with a precise reason.

**Expected Behavior / Usage:**

Input is `{xml}`: the assertion element. The mandatory shape requires `Version`, `ID`, and `IssueInstant` attributes, an `Issuer` element, and a `Subject` element (carrying a `NameID`); these are surfaced as `version`, `id`, `issueInstant`, `issuer.value`, and `subject.nameId.value`. Errors are reported as neutral categories: a missing mandatory attribute yields `error=missing_attribute`; a mandatory child element that is absent so that the next element appears where it was expected yields `error=unexpected_local_name` (for the `Issuer` and `Subject` positions); an `AttributeStatement` present but empty yields `error=missing_element`; and a `SubjectConfirmation` lacking its required `Method` attribute yields `error=missing_attribute`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_assertion_read.json`

```json
{
    "description": "Parse a SAML2 assertion XML element. The mandatory shape requires Version, ID and IssueInstant attributes, an Issuer element, and a Subject element (with its NameID); these are surfaced as version/id/issueInstant/issuer.value/subject.nameId.value. When a mandatory attribute is absent the result is a missing-attribute error; when a mandatory child element is in the wrong position (Issuer or Subject absent) the result is an unexpected-local-name error; when a required repeated child is absent (an empty AttributeStatement, or a SubjectConfirmation without its Method) the result is a missing-element or missing-attribute error respectively.",
    "cases": [
        {"input": {"action": "read_assertion", "xml": "<Assertion xmlns=\"urn:oasis:names:tc:SAML:2.0:assertion\" Version=\"2.42\" ID=\"a9329\" IssueInstant=\"2024-02-03T18:24:14Z\"><Issuer>https://idp.example.com/Saml2</Issuer><Subject><NameID>x987654</NameID><SubjectConfirmation Method=\"urn:foo\" /></Subject><AttributeStatement><Attribute Name=\"foo\"><AttributeValue>Bar</AttributeValue></Attribute></AttributeStatement></Assertion>"}, "expected_output": "version=2.42\nid=a9329\nissueInstant=2024-02-03T18:24:14Z\nissuer.value=https://idp.example.com/Saml2\nsubject.nameId.value=x987654\n"},
        {"input": {"action": "read_assertion", "xml": "<Assertion xmlns=\"urn:oasis:names:tc:SAML:2.0:assertion\" Version=\"2.42\" IssueInstant=\"2024-02-03T18:24:14Z\"><Issuer>https://idp.example.com/Saml2</Issuer><Subject><NameID>x987654</NameID><SubjectConfirmation Method=\"urn:foo\" /></Subject><AttributeStatement><Attribute Name=\"foo\"><AttributeValue>Bar</AttributeValue></Attribute></AttributeStatement></Assertion>"}, "expected_output": "error=missing_attribute\n"},
        {"input": {"action": "read_assertion", "xml": "<Assertion xmlns=\"urn:oasis:names:tc:SAML:2.0:assertion\" Version=\"2.42\" ID=\"a9329\" IssueInstant=\"2024-02-03T18:24:14Z\"><Subject><NameID>x987654</NameID><SubjectConfirmation Method=\"urn:foo\" /></Subject><AttributeStatement><Attribute Name=\"foo\"><AttributeValue>Bar</AttributeValue></Attribute></AttributeStatement></Assertion>"}, "expected_output": "error=unexpected_local_name\n"},
        {"input": {"action": "read_assertion", "xml": "<Assertion xmlns=\"urn:oasis:names:tc:SAML:2.0:assertion\" Version=\"2.42\" ID=\"a9329\" IssueInstant=\"2024-02-03T18:24:14Z\"><Issuer>https://idp.example.com/Saml2</Issuer><Subject><NameID>x987654</NameID><SubjectConfirmation Method=\"urn:foo\" /></Subject><AttributeStatement></AttributeStatement></Assertion>"}, "expected_output": "error=missing_element\n"}
    ]
}
```

---

### Feature 5: Protocol Response Parsing

**As a developer**, I want to parse a SAML2 protocol response XML element, so I can read its status and contained assertions while rejecting malformed responses.

**Expected Behavior / Usage:**

Input is `{xml}`: the response element. The minimal shape requires `ID`, `Version`, and `IssueInstant` attributes and a `Status` element containing a `StatusCode` with a `Value`; these are surfaced as `id`, `version`, `issueInstant`, and `status.statusCode`, together with `assertionCount` (the number of contained assertions). A missing mandatory attribute yields `error=missing_attribute`; an absent `Status` element, an absent `StatusCode` child, or an absent `Value` attribute yields `error=missing_element` / `error=missing_attribute` as appropriate.

**Test Cases:** `rcb_tests/public_test_cases/feature5_response_read.json`

```json
{
    "description": "Parse a SAML2 protocol response XML element. The minimal shape requires ID, Version and IssueInstant attributes and a Status element containing a StatusCode with a Value; these are surfaced as id/version/issueInstant/status.statusCode together with a count of contained assertions. When a mandatory attribute is absent the result is a missing-attribute error; when the Status element, its StatusCode child, or the StatusCode Value is absent the result is a missing-element or missing-attribute error.",
    "cases": [
        {"input": {"action": "read_response", "xml": "<samlp:Response xmlns:samlp=\"urn:oasis:names:tc:SAML:2.0:protocol\" xmlns:saml=\"urn:oasis:names:tc:SAML:2.0:assertion\" ID=\"x123\" Version=\"2.0\" IssueInstant=\"2023-10-14T13:46:32Z\"><samlp:Status><samlp:StatusCode Value=\"urn:oasis:names:tc:SAML:2.0:status:Requester\" /></samlp:Status></samlp:Response>"}, "expected_output": "id=x123\nversion=2.0\nissueInstant=2023-10-14T13:46:32Z\nstatus.statusCode=urn:oasis:names:tc:SAML:2.0:status:Requester\nassertionCount=0\n"},
        {"input": {"action": "read_response", "xml": "<samlp:Response xmlns:samlp=\"urn:oasis:names:tc:SAML:2.0:protocol\" xmlns:saml=\"urn:oasis:names:tc:SAML:2.0:assertion\" Version=\"2.0\" IssueInstant=\"2023-10-14T13:46:32Z\"><samlp:Status><samlp:StatusCode Value=\"urn:oasis:names:tc:SAML:2.0:status:Requester\" /></samlp:Status></samlp:Response>"}, "expected_output": "error=missing_attribute\n"},
        {"input": {"action": "read_response", "xml": "<samlp:Response xmlns:samlp=\"urn:oasis:names:tc:SAML:2.0:protocol\" xmlns:saml=\"urn:oasis:names:tc:SAML:2.0:assertion\" ID=\"x123\" Version=\"2.0\" IssueInstant=\"2023-10-14T13:46:32Z\"></samlp:Response>"}, "expected_output": "error=missing_element\n"},
        {"input": {"action": "read_response", "xml": "<samlp:Response xmlns:samlp=\"urn:oasis:names:tc:SAML:2.0:protocol\" xmlns:saml=\"urn:oasis:names:tc:SAML:2.0:assertion\" ID=\"x123\" Version=\"2.0\" IssueInstant=\"2023-10-14T13:46:32Z\"><samlp:Status></samlp:Status></samlp:Response>"}, "expected_output": "error=missing_element\n"}
    ]
}
```

---

### Feature 6: Entity Metadata Parsing

**As a developer**, I want to parse a SAML2 metadata entity-descriptor XML element, so I can discover a provider's identity and roles with namespace and structural validation.

**Expected Behavior / Usage:**

Input is `{xml}`: the entity-descriptor element. The mandatory shape requires an `entityID` attribute and at least one role-descriptor child; these are surfaced as `entityId` plus an indexed list `roleDescriptor[<i>].protocolSupportEnumeration`. Optional attributes — the descriptor `id`, a `cacheDuration` (an ISO-8601 duration), and a `validUntil` expiry timestamp (ISO-8601 UTC) — are surfaced when present. Parsing is rejected with a neutral category when `entityID` is absent (`error=missing_attribute`), when the root element is in the wrong XML namespace (`error=unexpected_namespace`), when the root element has the wrong local name (`error=unexpected_local_name`), or when no role-descriptor children are present (`error=missing_element`).

**Test Cases:** `rcb_tests/public_test_cases/feature6_entity_descriptor_read.json`

```json
{
    "description": "Parse a SAML2 metadata entity-descriptor XML element. The mandatory shape requires an entityID attribute and at least one role-descriptor child; these are surfaced as entityId plus an indexed list of role descriptors with their protocolSupportEnumeration. Optional attributes (the descriptor id, a cache duration, and a valid-until expiry timestamp) are surfaced when present. Parsing is rejected with a neutral error category when entityID is absent (missing attribute), when the root element is in the wrong XML namespace (unexpected namespace), when the root element has the wrong local name (unexpected local name), or when no role-descriptor children are present (missing element).",
    "cases": [
        {"input": {"action": "read_entity_descriptor", "xml": "<EntityDescriptor xmlns=\"urn:oasis:names:tc:SAML:2.0:metadata\" entityID=\"https://stubidp.example.com/Metadata\"><RoleDescriptor protocolSupportEnumeration=\"urn:whatever\"/></EntityDescriptor>"}, "expected_output": "entityId=https://stubidp.example.com/Metadata\nroleDescriptor[0].protocolSupportEnumeration=urn:whatever\n"},
        {"input": {"action": "read_entity_descriptor", "xml": "<EntityDescriptor xmlns=\"urn:oasis:names:tc:SAML:2.0:metadata\" ID=\"_eb83b59a-572a-480b-b36c-e3a3edfd92d0\" entityID=\"https://stubidp.example.com/Metadata\" cacheDuration=\"PT15M\" validUntil=\"2022-03-15T20:47:00Z\"><RoleDescriptor protocolSupportEnumeration=\"urn:whatever\"/></EntityDescriptor>"}, "expected_output": "entityId=https://stubidp.example.com/Metadata\nid=_eb83b59a-572a-480b-b36c-e3a3edfd92d0\ncacheDuration=PT15M\nvalidUntil=2022-03-15T20:47:00Z\nroleDescriptor[0].protocolSupportEnumeration=urn:whatever\n"},
        {"input": {"action": "read_entity_descriptor", "xml": "<EntityDescriptor xmlns=\"urn:oasis:names:tc:SAML:2.0:metadata\"><RoleDescriptor protocolSupportEnumeration=\"urn:whatever\"/></EntityDescriptor>"}, "expected_output": "error=missing_attribute\n"},
        {"input": {"action": "read_entity_descriptor", "xml": "<EntityDescriptor xmlns=\"urn:incorrect:namespace\" entityID=\"https://stubidp.example.com/Metadata\"></EntityDescriptor>"}, "expected_output": "error=unexpected_namespace\n"}
    ]
}
```

---

### Feature 7: Identity-Provider Descriptor Parsing

**As a developer**, I want to extract the identity-provider role descriptor from a metadata entity-descriptor, so I can discover where to send authentication requests.

**Expected Behavior / Usage:**

Input is `{xml}`: an entity-descriptor element containing an identity-provider role descriptor. The descriptor reports its `protocolSupportEnumeration`, a `wantAuthnRequestsSigned` boolean flag (defaulting to `false` when the attribute is absent), and an indexed list of single-sign-on service endpoints, each surfaced as `singleSignOnService[<i>].binding` (a binding URI) and `singleSignOnService[<i>].location` (a location URL).

**Test Cases:** `rcb_tests/public_test_cases/feature7_idp_sso_descriptor_read.json`

```json
{
    "description": "Parse the identity-provider role descriptor from a metadata entity-descriptor and surface its single-sign-on endpoints. The descriptor reports its protocolSupportEnumeration, a flag for whether it wants authentication requests signed, and an indexed list of single-sign-on service endpoints each with a binding URI and a location URL.",
    "cases": [
        {"input": {"action": "read_idp_sso_descriptor", "xml": "<EntityDescriptor xmlns=\"urn:oasis:names:tc:SAML:2.0:metadata\" entityID=\"https://stubidp.example.com/Metadata\"><IDPSSODescriptor protocolSupportEnumeration=\"urn:oasis:names:tc:SAML:2.0:protocol\"><SingleSignOnService Binding=\"urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect\" Location=\"https://stubidp.example.com/\" /></IDPSSODescriptor></EntityDescriptor>"}, "expected_output": "protocolSupportEnumeration=urn:oasis:names:tc:SAML:2.0:protocol\nwantAuthnRequestsSigned=false\nsingleSignOnService[0].binding=urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect\nsingleSignOnService[0].location=https://stubidp.example.com/\n"}
    ]
}
```

---

### Feature 8: Redirect Binding Decode

**As a developer**, I want to decode a front-channel redirect URL back into a SAML2 message, so I can recover the protocol payload that a browser delivered via the HTTP-Redirect binding.

**Expected Behavior / Usage:**

Input is `{url}`: the full redirect URL. The message payload travels as a query parameter named exactly `SAMLRequest` or `SAMLResponse`, whose value is the URL-safe base64 of the raw-DEFLATE-compressed XML; an optional `RelayState` parameter is carried verbatim. Decoding surfaces `destination` (the scheme, host and path of the URL, without the query string), `name` (the message parameter name used), `relayState`, and `xml` (the inflated XML payload). Decoding is rejected with a neutral category when neither message parameter is present (`error=message_parameter_not_found`), when both message parameters appear (`error=duplicate_message_parameters`), or when the relay-state parameter appears more than once (`error=duplicate_relay_state`).

**Test Cases:** `rcb_tests/public_test_cases/feature8_redirect_binding_decode.json`

```json
{
    "description": "Decode a front-channel redirect URL back into a SAML2 message. The message payload travels as a query parameter named exactly 'SAMLRequest' or 'SAMLResponse' whose value is the URL-safe base64 of the raw-deflate-compressed XML; an optional 'RelayState' parameter is carried verbatim. Decoding surfaces the destination (scheme, host and path of the URL, without query), the parameter name used, the relay state, and the inflated XML. Decoding is rejected with a neutral error category when neither message parameter is present (parameter not found), when both message parameters appear (duplicate message parameters), or when the relay-state parameter appears more than once (duplicate relay state).",
    "cases": [
        {"input": {"action": "redirect_decode", "url": "https://idp.example.com/sso?SAMLRequest=s6nIzVHQtwMA&RelayState=xyz123"}, "expected_output": "destination=https://idp.example.com/sso\nname=SAMLRequest\nrelayState=xyz123\nxml=<xml />\n"},
        {"input": {"action": "redirect_decode", "url": "https://idp.example.com/sso?SAMLResponse=s6nIzVHQtwMA&RelayState=xyz123"}, "expected_output": "destination=https://idp.example.com/sso\nname=SAMLResponse\nrelayState=xyz123\nxml=<xml />\n"},
        {"input": {"action": "redirect_decode", "url": "https://idp.example.com/sso?Invalid=s6nIzVHQtwMA&RelayState=xyz123"}, "expected_output": "error=message_parameter_not_found\n"},
        {"input": {"action": "redirect_decode", "url": "https://idp.example.com/sso?SAMLResponse=x&SAMLRequest=s6nIzVHQtwMA&RelayState=xyz123"}, "expected_output": "error=duplicate_message_parameters\n"},
        {"input": {"action": "redirect_decode", "url": "https://idp.example.com/sso?RelayState=x&SAMLRequest=s6nIzVHQtwMA&RelayState=xyz123"}, "expected_output": "error=duplicate_relay_state\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the features above — a UTC-only timestamp value type with validated conversion and ordering, a name-identifier type with precise equality, a family of readers that turn protocol/metadata XML into domain objects with a structured error model, and a redirect-binding decoder. The core logic must be decoupled from stdin/stdout and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, routes on the request's `action`, invokes the appropriate core logic, and prints the line-oriented result (or a neutral `error=<category>` line) to stdout, matching the per-feature contracts above. Native exceptions thrown by the core MUST be translated into the neutral error contract in this adapter layer; no host-language runtime type names, stack traces, or runtime-generated message text may appear in stdout. The actions are: `datetime_validate`, `datetime_compare`, `nameid_compare`, `read_authn_request`, `read_assertion`, `read_response`, `read_entity_descriptor`, `read_idp_sso_descriptor`, and `redirect_decode`.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
