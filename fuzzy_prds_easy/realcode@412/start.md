## Product Requirement Document

# WHATWG-Compliant URL Parser & Manipulation Library — Standards-Conformant Parsing, Normalization, Component Access, and Query Strings

## Project Goal

Build a URL library that parses a URL string (optionally relative to a base URL) into a structured, standards-conformant result, exposes every URL component for reading and in-place editing, re-serializes the URL canonically after each edit, and provides an ordered query-parameter collection — so developers can work with URLs correctly without hand-rolling fragile string manipulation.

---

## Background & Problem

URLs look simple but are governed by an exacting living standard: schemes are case-folded, hosts may be domains, IPv4, or IPv6 and each is normalized differently, paths collapse `.`/`..` segments and percent-encode unsafe characters, default ports are dropped, some schemes carry an opaque (non-hierarchical) body, and relative references must be resolved against a base. Doing this by hand with string splitting produces subtly wrong, insecure results.

Without this library, developers reinvent parsing and normalization per project and disagree on edge cases. With it, a single well-defined contract turns a raw string into a validated URL, lets each component be read or mutated through a stable interface, guarantees a canonical serialization after every change, and offers a query-parameter multimap with correct form-encoding and stable sorting.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains. This domain (parser, host/IP handling, path normalization, percent-encoding, query parameters, serialization) is non-trivial and warrants a multi-file structure.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, host/IP handling, path resolution, percent-encoding, query parameters, and serialization into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. A parse that cannot succeed must be reported as a failure result (e.g., an optional/Result type), not a crash, and an invalid component assignment must be rejected without corrupting the existing URL.

---

## Core Features

### Feature 1: Parse And Validate

**As a developer**, I want to know whether a string is a usable URL (optionally relative to a base), so I can accept or reject input up front.

**Expected Behavior / Usage:**

Parsing takes an input string and an optional base URL. A syntactically valid absolute URL is accepted; a relative reference is accepted only when it can be resolved against a usable base. An empty input, a bare fragment with no base, or a host that violates the host grammar (for example an out-of-range IPv4 address) is rejected. This feature observes only the accept/reject outcome, not any parsed component.

**Test Cases:** `rcb_tests/public_test_cases/feature1_parse_validity.json`

```json
{
    "description": "Parse a URL string, optionally against a base URL, and report only whether the input is accepted as a valid URL. A syntactically valid absolute URL, or a relative reference resolved against a usable base, is accepted; an empty input, a bare fragment with no base, or a host that violates the host grammar is rejected. The output states validity without exposing any parsed component.",
    "cases": [
        {"input": {"action": "parse_url", "url": "https://www.google.com"}, "expected_output": "url=valid\n"},
        {"input": {"action": "parse_url", "url": ""}, "expected_output": "url=invalid\n"}
    ]
}
```

---

### Feature 2: Read URL Components

**As a developer**, I want to read each part of a parsed URL, so I can inspect the scheme, credentials, host, port, path, query, fragment, and origin independently.

**Expected Behavior / Usage:**

After a successful parse, each component can be read back by name: the scheme (reported with its trailing colon), the optional username and password, the host (with the port) and the bare hostname, the port, the path, the query, the fragment, and the computed origin. Boolean flags report whether the path is opaque and whether the host section is empty. Each requested component is reported on its own line.

**Test Cases:** `rcb_tests/public_test_cases/feature2_read_components.json`

```json
{
    "description": "Parse a URL and read back its individual components: the scheme, the optional username and password, the host (with and without the port), the port, the path, and the computed origin, along with flags reporting whether the path is opaque and whether the host section is empty. Each requested component is reported on its own line so the full decomposition of one URL is observable at once.",
    "cases": [
        {"input": {"action": "parse_url", "url": "http://::@c@d:2", "base": "http://example.org/foo/bar", "steps": [{"op": "get", "field": "has_opaque_path"}, {"op": "get", "field": "hostname"}, {"op": "get", "field": "host"}, {"op": "get", "field": "pathname"}, {"op": "get", "field": "href"}, {"op": "get", "field": "origin"}]}, "expected_output": "url=valid\nhas_opaque_path=false\nhostname=d\nhost=d:2\npathname=/\nhref=http://:%3A%40c@d:2/\norigin=http://d:2\n"}
    ]
}
```

---

### Feature 3: Canonical Serialization & Normalization

**As a developer**, I want the serialized URL to be canonical, so equivalent inputs normalize to one well-defined output.

**Expected Behavior / Usage:**

Reading the serialized form returns a normalized URL. A special scheme and its host are lower-cased; ignored or zero-width characters in a host are removed; `.` and `..` path segments are resolved; characters not allowed literally in a path are percent-encoded while already-encoded sequences and permitted characters are preserved. A relative reference resolved against a base serializes as an absolute URL with its path percent-encoded.

**Test Cases:** `rcb_tests/public_test_cases/feature3_serialization_normalization.json`

```json
{
    "description": "Parse a URL and read its canonical serialized form. Serialization normalizes the input: a special scheme and its host are lower-cased, ignored or zero-width characters in a host are removed, dot path segments are resolved, and characters not allowed literally in a path are percent-encoded while already-encoded sequences and permitted characters are preserved. A relative reference resolved against a base is serialized as an absolute URL with its path percent-encoded.",
    "cases": [
        {"input": {"action": "parse_url", "url": "HTTP://AMAZON.COM", "steps": [{"op": "get", "field": "href"}]}, "expected_output": "url=valid\nhref=http://amazon.com/\n"},
        {"input": {"action": "parse_url", "url": "file:///foo/.bar/../baz.js", "steps": [{"op": "get", "field": "pathname"}]}, "expected_output": "url=valid\npathname=/foo/baz.js\n"}
    ]
}
```

---

### Feature 4: Percent-Encoding Tolerance & Rejection

**As a developer**, I want predictable handling of percent signs, so malformed escapes are tolerated in a path but rejected in a host.

**Expected Behavior / Usage:**

A stray percent sign that is not part of a valid two-hex-digit escape is tolerated in the path and preserved verbatim in the serialized output, but the same malformed escape inside a host makes the URL invalid. Replacing the whole URL string follows the same rule, and an attempt to set a host containing a malformed escape is rejected.

**Test Cases:** `rcb_tests/public_test_cases/feature4_percent_encoding.json`

```json
{
    "description": "Handle percent signs and percent-encoded sequences during parsing. A stray percent sign that is not part of a valid two-hex-digit escape is tolerated in the path and preserved verbatim in the serialized output, but the same malformed escape inside a host makes the URL invalid. Replacing the whole URL string is subject to the same rule, and an attempt to set a host containing a malformed escape is rejected.",
    "cases": [
        {"input": {"action": "parse_url", "url": "http://www.google.com/%X%", "steps": [{"op": "get", "field": "href"}]}, "expected_output": "url=valid\nhref=http://www.google.com/%X%\n"},
        {"input": {"action": "parse_url", "url": "http://www.google%X%.com/"}, "expected_output": "url=invalid\n"}
    ]
}
```

---

### Feature 5: Parseability Probe

**As a developer**, I want to test whether a string would parse without building a result, so I can validate cheaply.

**Expected Behavior / Usage:**

Given an input and an optional base, report whether the input would parse successfully, returning only a boolean. An absolute URL or a relative reference resolvable against a valid base reports `true`; a relative reference against an unusable base, or a string that is not a URL, reports `false`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_can_parse.json`

```json
{
    "description": "Probe whether a URL string would parse successfully, optionally against a base URL, without producing any parsed result. An absolute URL or a relative reference resolvable against a valid base reports parseability as true; a relative reference against an unusable base, or a string that is not a URL, reports false.",
    "cases": [
        {"input": {"action": "can_parse", "url": "https://www.yagiz.co"}, "expected_output": "can_parse=true\n"},
        {"input": {"action": "can_parse", "url": "/hello", "base": "!!!!!!!1"}, "expected_output": "can_parse=false\n"}
    ]
}
```

---

### Feature 6: Host Type Classification

**As a developer**, I want to know how a host was interpreted, so I can distinguish a domain from an IPv4 or IPv6 address.

**Expected Behavior / Usage:**

After parsing, report the host classification as a registrable domain/text host (`default`), an IPv4 address (`ipv4`), or an IPv6 address (`ipv6`), reflecting how the parser interpreted the host.

**Test Cases:** `rcb_tests/public_test_cases/feature6_host_type.json`

```json
{
    "description": "Parse a URL and report the classification of its host: a registrable domain or text host, an IPv4 address, or an IPv6 address. The classification reflects how the host was interpreted by the parser.",
    "cases": [
        {"input": {"action": "parse_url", "url": "http://localhost:3000", "steps": [{"op": "get", "field": "host_type"}]}, "expected_output": "url=valid\nhost_type=default\n"},
        {"input": {"action": "parse_url", "url": "http://0.0.0.0", "steps": [{"op": "get", "field": "host_type"}]}, "expected_output": "url=valid\nhost_type=ipv4\n"}
    ]
}
```

---

### Feature 7: Set Scheme

**As a developer**, I want to change a URL's scheme, so I can switch protocols while keeping a valid URL.

**Expected Behavior / Usage:**

Setting the scheme returns success or failure. Switching between compatible schemes succeeds and re-serializes the URL under the new scheme; a transition that is not allowed for the current URL shape is rejected (reported as failure) and leaves the URL unchanged. When a scheme change brings the host's default port into effect, that port is dropped from the serialization.

**Test Cases:** `rcb_tests/public_test_cases/feature7_set_scheme.json`

```json
{
    "description": "Change the scheme of a parsed URL and observe the result. Switching between compatible schemes succeeds and re-serializes the URL under the new scheme; switching a scheme is rejected (reported as failure, leaving the URL unchanged) when the transition is not allowed for the current URL shape. When a scheme change brings the host's default port into effect, that port is dropped from the serialization.",
    "cases": [
        {"input": {"action": "parse_url", "url": "https://www.google.com", "steps": [{"op": "set", "field": "protocol", "value": "wss"}, {"op": "get", "field": "protocol"}, {"op": "get", "field": "href"}]}, "expected_output": "url=valid\nset_protocol=true\nprotocol=wss:\nhref=wss://www.google.com/\n"},
        {"input": {"action": "parse_url", "url": "http://www.google.com:443", "steps": [{"op": "set", "field": "protocol", "value": "https"}, {"op": "get", "field": "port"}, {"op": "get", "field": "host"}]}, "expected_output": "url=valid\nset_protocol=true\nport=\nhost=www.google.com\n"}
    ]
}
```

---

### Feature 8: Set Host / Hostname

**As a developer**, I want to change a URL's host, so I can retarget it while rejecting invalid hosts.

**Expected Behavior / Usage:**

Setting the host (which may include a port) or the bare hostname returns success or failure. For a URL that has an authority, a syntactically valid replacement succeeds and is reflected when reading the host back; an invalid host value is rejected and leaves the URL unchanged. For a URL whose scheme cannot carry a host, the operation is rejected.

**Test Cases:** `rcb_tests/public_test_cases/feature8_set_host.json`

```json
{
    "description": "Set the host (or the bare hostname) of a parsed URL. For a URL that has an authority, a syntactically valid replacement succeeds and is reflected when reading the host back; an invalid host value is rejected and leaves the URL unchanged. For a URL whose scheme cannot carry a host, the operation is rejected.",
    "cases": [
        {"input": {"action": "parse_url", "url": "https://www.google.com", "steps": [{"op": "set", "field": "host", "value": "github.com"}, {"op": "get", "field": "host"}]}, "expected_output": "url=valid\nset_host=true\nhost=github.com\n"},
        {"input": {"action": "parse_url", "url": "mailto:a@b.com", "steps": [{"op": "set", "field": "host", "value": "something"}]}, "expected_output": "url=valid\nset_host=false\n"}
    ]
}
```

---

### Feature 9: Set / Clear Credentials

**As a developer**, I want to set or clear the username and password, so I can manage embedded credentials.

**Expected Behavior / Usage:**

Assigning a username or password makes it appear in the serialized authority; assigning an empty string clears that credential. Clearing both credentials removes the credentials block (and its separators) from the serialization entirely.

**Test Cases:** `rcb_tests/public_test_cases/feature9_set_userinfo.json`

```json
{
    "description": "Set or clear the username and password credentials of a parsed URL. Assigning credentials makes them appear in the serialized authority; assigning an empty string clears that credential, and clearing both removes the credentials block (and its separators) from the serialization entirely.",
    "cases": [
        {"input": {"action": "parse_url", "url": "https://www.google.com", "steps": [{"op": "set", "field": "username", "value": "username"}, {"op": "set", "field": "password", "value": "password"}, {"op": "get", "field": "href"}]}, "expected_output": "url=valid\nset_username=true\nset_password=true\nhref=https://username:password@www.google.com/\n"},
        {"input": {"action": "parse_url", "url": "http://me@example.net", "steps": [{"op": "set", "field": "username", "value": ""}, {"op": "get", "field": "username"}, {"op": "get", "field": "href"}]}, "expected_output": "url=valid\nset_username=true\nusername=\nhref=http://example.net/\n"}
    ]
}
```

---

### Feature 10: Set Port

**As a developer**, I want to set a URL's port, so I can redirect to a different port with predictable validation.

**Expected Behavior / Usage:**

Setting the port returns success or failure. A purely numeric value is accepted; a negative value is rejected. A value that begins with digits followed by non-digit characters is accepted by taking the leading numeric run as the port, while a value that does not begin with a digit is rejected and leaves the port empty. The URL remains valid throughout.

**Test Cases:** `rcb_tests/public_test_cases/feature10_set_port.json`

```json
{
    "description": "Set the port of a parsed URL. A purely numeric value is accepted; a negative value is rejected. A value that begins with digits and is then followed by non-digit characters is accepted by taking the leading numeric run as the port, while a value that does not begin with a digit is rejected and leaves the port empty. The URL remains valid throughout.",
    "cases": [
        {"input": {"action": "parse_url", "url": "https://www.google.com", "steps": [{"op": "set", "field": "port", "value": "8080"}, {"op": "get", "field": "port"}]}, "expected_output": "url=valid\nset_port=true\nport=8080\n"},
        {"input": {"action": "parse_url", "url": "fake://dummy.test", "steps": [{"op": "set", "field": "port", "value": "invalid80"}, {"op": "get", "field": "port"}, {"op": "set", "field": "port", "value": "80valid"}, {"op": "get", "field": "is_valid"}, {"op": "get", "field": "port"}]}, "expected_output": "url=valid\nset_port=false\nport=\nset_port=true\nis_valid=true\nport=80\n"}
    ]
}
```

---

### Feature 11: Set Path

**As a developer**, I want to set a URL's path, so I can change the resource while keeping the rest intact.

**Expected Behavior / Usage:**

Setting the path is reflected when read back, and re-serialization preserves any query already present. For schemes that are not special, a path that begins with two slashes is disambiguated from an authority by inserting a hidden marker segment in the serialization, while the read-back path stays as given; giving the URL a hostname removes that marker. Setting a path keeps the URL internally consistent.

**Test Cases:** `rcb_tests/public_test_cases/feature11_set_path.json`

```json
{
    "description": "Set the path of a parsed URL. The new path is reflected when read back, and re-serialization preserves any query already present. For schemes that are not special, a path that begins with two slashes is disambiguated from an authority by inserting a hidden marker segment in the serialization while the read-back path stays as given; giving the URL a hostname removes that marker. Setting a path keeps the URL internally consistent.",
    "cases": [
        {"input": {"action": "parse_url", "url": "https://www.google.com", "steps": [{"op": "set", "field": "pathname", "value": "/my-super-long-path"}, {"op": "get", "field": "pathname"}]}, "expected_output": "url=valid\nset_pathname=true\npathname=/my-super-long-path\n"},
        {"input": {"action": "parse_url", "url": "non-spec:/", "steps": [{"op": "set", "field": "pathname", "value": "//p"}, {"op": "get", "field": "pathname"}, {"op": "get", "field": "href"}]}, "expected_output": "url=valid\nset_pathname=true\npathname=//p\nhref=non-spec:/.//p\n"}
    ]
}
```

---

### Feature 12: Opaque-Path URLs

**As a developer**, I want correct handling of opaque-path URLs, so non-hierarchical schemes round-trip and resolve fragments correctly.

**Expected Behavior / Usage:**

A URL whose body is opaque (a scheme directly followed by a non-hierarchical, non-slash-prefixed body) reports an opaque path, exposes its scheme and the opaque body as the path, and serializes them back unchanged. Resolving a relative reference that contributes only a fragment against an opaque-path base keeps the opaque body intact and applies the fragment.

**Test Cases:** `rcb_tests/public_test_cases/feature12_opaque_path.json`

```json
{
    "description": "Handle URLs whose path is opaque (a scheme directly followed by a non-hierarchical, non-slash-prefixed body). Such a URL reports an opaque path, exposes its scheme and the opaque body as the path, and serializes them back unchanged. Resolving a relative reference that contributes only a fragment against an opaque-path base keeps the opaque body intact and applies the fragment.",
    "cases": [
        {"input": {"action": "parse_url", "url": "a:b", "steps": [{"op": "get", "field": "href"}, {"op": "get", "field": "protocol"}, {"op": "get", "field": "pathname"}, {"op": "get", "field": "has_opaque_path"}]}, "expected_output": "url=valid\nhref=a:b\nprotocol=a:\npathname=b\nhas_opaque_path=true\n"},
        {"input": {"action": "parse_url", "url": "..#", "base": "a:b", "steps": [{"op": "get", "field": "href"}, {"op": "get", "field": "pathname"}, {"op": "get", "field": "has_opaque_path"}]}, "expected_output": "url=valid\nhref=a:b#\npathname=b\nhas_opaque_path=true\n"}
    ]
}
```

---

### Feature 13: Set / Clear Query

**As a developer**, I want to set or clear the query string, so I can modify request parameters carried in the URL.

**Expected Behavior / Usage:**

Assigning a query makes it readable back with its leading question mark; assigning an empty string clears the query. On schemes whose body is opaque, clearing the query exposes the remaining encoded path and re-serializes the URL without the query while keeping any fragment.

**Test Cases:** `rcb_tests/public_test_cases/feature13_set_query.json`

```json
{
    "description": "Set or clear the query (search) component of a parsed URL. Assigning a query makes it readable back with its leading question mark; assigning an empty string clears the query, and on schemes whose body is opaque, clearing the query exposes the remaining encoded path and re-serializes the URL without the query while keeping any fragment.",
    "cases": [
        {"input": {"action": "parse_url", "url": "https://www.google.com", "steps": [{"op": "set", "field": "search", "value": "target=self"}, {"op": "get", "field": "search"}]}, "expected_output": "url=valid\nset_search=ok\nsearch=?target=self\n"},
        {"input": {"action": "parse_url", "url": "data:space    ?test", "steps": [{"op": "get", "field": "search"}, {"op": "set", "field": "search", "value": ""}, {"op": "get", "field": "search"}, {"op": "get", "field": "pathname"}, {"op": "get", "field": "href"}]}, "expected_output": "url=valid\nsearch=?test\nset_search=ok\nsearch=\npathname=space   %20\nhref=data:space   %20\n"}
    ]
}
```

---

### Feature 14: Set Fragment

**As a developer**, I want to set the fragment, so I can target an in-document anchor.

**Expected Behavior / Usage:**

Assigning a fragment makes it readable back with its leading hash marker.

**Test Cases:** `rcb_tests/public_test_cases/feature14_set_fragment.json`

```json
{
    "description": "Set the fragment (hash) component of a parsed URL. The assigned fragment is readable back with its leading hash marker.",
    "cases": [
        {"input": {"action": "parse_url", "url": "https://www.google.com", "steps": [{"op": "set", "field": "hash", "value": "is-this-the-real-life"}, {"op": "get", "field": "hash"}]}, "expected_output": "url=valid\nset_hash=ok\nhash=#is-this-the-real-life\n"}
    ]
}
```

---

### Feature 15: Replace Whole URL

**As a developer**, I want to assign a new full URL string to an existing object, so I can repoint it entirely while applying normalization.

**Expected Behavior / Usage:**

Assigning a new full URL string returns success or failure. On success the object adopts every component of the new string, including normalization such as collapsing an alternative numeric host notation to a canonical dotted IPv4 address, observable through the scheme and the serialized form.

**Test Cases:** `rcb_tests/public_test_cases/feature15_set_href.json`

```json
{
    "description": "Replace the entire URL of a parsed object by assigning a new full URL string. On success the object adopts every component of the new string, including normalization such as collapsing an alternative numeric host notation to a canonical dotted IPv4 address, observable through the scheme and the serialized form.",
    "cases": [
        {"input": {"action": "parse_url", "url": "file:///var/log/system.log", "steps": [{"op": "set", "field": "href", "value": "http://0300.168.0xF0"}, {"op": "get", "field": "protocol"}, {"op": "get", "field": "href"}]}, "expected_output": "url=valid\nset_href=true\nprotocol=http:\nhref=http://192.168.0.240/\n"}
    ]
}
```

---

### Feature 16: Query Parameter Multimap — Build & Mutate

**As a developer**, I want an ordered key/value parameter collection, so I can build and edit query parameters precisely.

**Expected Behavior / Usage:**

The collection supports appending (adds a new pair, preserving insertion order and allowing duplicate keys), setting (collapses all pairs for a key to a single value, in the key's existing position when present), and removing (deletes either all pairs for a key, or only the pairs matching a key and value). It can be queried by count, membership (optionally by key and value), single-value lookup, and multi-value lookup. It can also be built directly from a query string, where an optional leading question mark is ignored and a key with no value is treated as having an empty value.

**Test Cases:** `rcb_tests/public_test_cases/feature16_query_params_build.json`

```json
{
    "description": "Build and mutate an ordered multimap of query parameters and observe it through its count, membership tests, single and multi-value lookups, and serialized form. Appending adds a new pair preserving insertion order and allowing duplicate keys; setting collapses all pairs for a key to a single value (in the key's existing position when present); removing deletes either all pairs for a key or only the pairs matching a key and value. The collection can also be built directly from a query string, where an optional leading question mark is ignored and a key with no value is treated as having an empty value.",
    "cases": [
        {"input": {"action": "search_params", "steps": [{"op": "append", "key": "key", "value": "value"}, {"op": "size"}, {"op": "has", "key": "key"}, {"op": "append", "key": "key", "value": "value2"}, {"op": "size"}, {"op": "get_all", "key": "key"}]}, "expected_output": "size=1\nhas=true\nsize=2\nget_all=2\nvalue\nvalue2\n"},
        {"input": {"action": "search_params", "init": "?[a deterministic sorted query string — ask the PM for the exact string]", "steps": [{"op": "to_string"}]}, "expected_output": "to_string=[a deterministic sorted query string — ask the PM for the exact string]\n"}
    ]
}
```

---

### Feature 17: Query Parameter Form-Encoding

**As a developer**, I want correct form-encoding on serialization, so query parameters round-trip safely while values read back decoded.

**Expected Behavior / Usage:**

Serialization uses application/x-www-form-urlencoded rules: a space becomes a plus sign; a literal plus is percent-encoded; an ampersand and other reserved characters are percent-encoded; non-ASCII text is UTF-8 percent-encoded. Reading a value back returns its decoded form even though the serialized form is encoded.

**Test Cases:** `rcb_tests/public_test_cases/feature17_query_params_encoding.json`

```json
{
    "description": "Serialize query parameters using application/x-www-form-urlencoded rules while preserving the original decoded values for lookup. A space is encoded as a plus sign; a literal plus is percent-encoded; an ampersand and other reserved characters are percent-encoded; non-ASCII text is UTF-8 percent-encoded. Reading a value back returns its decoded form even though the serialized form is encoded.",
    "cases": [
        {"input": {"action": "search_params", "steps": [{"op": "append", "key": "key1", "value": "été"}, {"op": "append", "key": "key2", "value": "Céline Dion++"}, {"op": "size"}, {"op": "to_string"}, {"op": "get", "key": "key1"}, {"op": "get", "key": "key2"}]}, "expected_output": "size=2\nto_string=key1=%C3%A9t%C3%A9&key2=C%C3%A9line+Dion%2B%2B\nget=été\nget=Céline Dion++\n"},
        {"input": {"action": "search_params", "steps": [{"op": "append", "key": "a", "value": "b+c"}, {"op": "to_string"}, {"op": "remove", "key": "a"}, {"op": "append", "key": "a+b", "value": "c"}, {"op": "to_string"}]}, "expected_output": "[a specific x-www-form-urlencoded serialization output — ask the PM for the exact string]\n[a specific x-www-form-urlencoded serialization output — ask the PM for the exact string]\n"}
    ]
}
```

---

### Feature 18: Query Parameter Stable Sort

**As a developer**, I want a stable sort by key, so parameters can be canonically ordered without disturbing same-key order.

**Expected Behavior / Usage:**

Sorting orders pairs by key using a comparison over Unicode code units and is stable: pairs that share a key keep their original insertion order. After sorting, the pairs are observable in key order, with empty keys or empty values handled like any other.

**Test Cases:** `rcb_tests/public_test_cases/feature18_query_params_sort.json`

```json
{
    "description": "Stably sort query parameters by key using a comparison over Unicode code units, preserving the relative order of pairs that share a key. After sorting, the pairs are observable in key order, with equal keys keeping their original insertion order and empty keys or empty values handled like any other.",
    "cases": [
        {"input": {"action": "search_params", "steps": [{"op": "append", "key": "bbb", "value": "second"}, {"op": "append", "key": "aaa", "value": "first"}, {"op": "append", "key": "ccc", "value": "third"}, {"op": "size"}, {"op": "sort"}, {"op": "to_string"}]}, "expected_output": "size=3\nto_string=aaa=first&bbb=second&ccc=third\n"},
        {"input": {"action": "search_params", "init": "[a deterministic sorted query string — ask the PM for the exact string]&[a deterministic sorted query string — ask the PM for the exact string]&[a deterministic sorted query string — ask the PM for the exact string]&[a deterministic sorted query string — ask the PM for the exact string]", "steps": [{"op": "size"}, {"op": "sort"}, {"op": "entries"}]}, "expected_output": "size=4\nentries\n[a deterministic sorted query string — ask the PM for the exact string]\n[a deterministic sorted query string — ask the PM for the exact string]\n[a deterministic sorted query string — ask the PM for the exact string]\n[a deterministic sorted query string — ask the PM for the exact string]\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the URL parsing, normalization, component access/mutation, opaque-path handling, percent-encoding, and query-parameter features above. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program that reads one JSON request object from stdin, invokes the core, and prints the neutral line-based contract below to stdout. It must be logically (and ideally physically) separated from the core domain. The contract is line-oriented; every emitted line ends with a newline.

   - **`action`** selects behavior (default `parse_url`): `parse_url`, `can_parse`, or `search_params`.

   - **`parse_url`**: fields `url` (string) and optional `base` (string), plus an optional ordered `steps` array. First emit `url=valid` if the input parses (when `base` is present, both the base and the input must parse), otherwise emit `url=invalid` and stop (no steps run). Then process each step in order:
     - `{"op":"get","field":"<name>"}` emits `<name>=<value>`. Supported component names: `protocol` (with trailing colon), `username`, `password`, `host`, `hostname`, `port`, `pathname`, `search` (with leading `?` when present), `hash` (with leading `#` when present), `href`, `origin`, and `host_type` (one of `default`, `ipv4`, `ipv6`). Supported boolean fields (rendered `true`/`false`): `has_opaque_path`, `has_empty_hostname`, `has_hostname`, `has_valid_domain`, `is_valid`, `validate`.
     - `{"op":"set","field":"<name>","value":"<v>"}`. For `href`, `host`, `hostname`, `protocol`, `username`, `password`, `port`, `pathname` it emits `set_<name>=true|false` reflecting whether the assignment was accepted. For `search` and `hash` it always applies and emits `set_<name>=ok`.

   - **`can_parse`**: fields `url` and optional `base`. Emits `can_parse=true|false`.

   - **`search_params`**: optional `init` (a query string to initialize from) and an ordered `steps` array. Mutating steps emit nothing; observing steps emit a line.
     - Mutating: `{"op":"append","key","value"}`, `{"op":"set","key","value"}`, `{"op":"remove","key"[,"value"]}`, `{"op":"sort"}`.
     - Observing: `{"op":"to_string"}` → `to_string=<serialized>`; `{"op":"size"}` → `size=<n>`; `{"op":"get","key"}` → `get=<decoded value>` or `get=absent`; `{"op":"get_all","key"}` → `get_all=<n>` followed by `<n>` lines, one decoded value each; `{"op":"has","key"[,"value"]}` → `has=true|false`; `{"op":"keys"}` → a single `keys=` line whose first key follows `keys=` and whose remaining keys are each on their own following line; `{"op":"values"}` likewise; `{"op":"entries"}` → a literal `entries` line followed by one `<key>=<value>` line per pair in order.

   Error conditions are surfaced as neutral lines (e.g. `error=invalid_request`, `error=unknown_action`/`error=unknown_op`/`error=unknown_field` with the offending token on a following field line); the adapter never leaks host-language runtime identifiers.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- normalize components using the same logic as the serialization module
- encode parameters following the library's standard query encoding
