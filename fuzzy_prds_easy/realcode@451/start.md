## Product Requirement Document

# Entity Data-Modeling Toolkit - Typed Values, Schema Graph & Record Mapping

## Project Goal

Build a library for modeling structured information about people, companies, assets and their relationships as a graph of typed entities. It allows developers to clean and validate real-world values (emails, phone numbers, dates, bank accounts, countries, …), describe entities against a shared schema ontology, derive stable identifiers, and map tabular source records into linked entities — all without re-implementing the messy parsing, normalization and matching rules that every data-integration project otherwise rewrites by hand.

---

## Background & Problem

Without this library, developers integrating heterogeneous data sources are forced to hand-roll value cleaning (lowercasing email domains, reformatting phone numbers to international form, padding partial dates), invent ad-hoc entity schemas with no shared vocabulary, hash record keys inconsistently, and write bespoke code to decide whether two records describe the same person. This leads to repetitive, error-prone boilerplate, identifiers that disagree between systems, and matching logic that cannot be reused.

With this library, values are normalized through a single registry of well-defined property types, entities are described against one coherent schema ontology with inheritance and inverse relations, source rows are mapped into linked entities with deterministic ids, and similarity scoring is built in — so the same authoritative rules drive cleaning, storage, export and comparison everywhere.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a non-trivial domain (typed values, an entity model, a schema ontology, record mapping, a graph, transformation helpers). It MUST NOT be a single "god file"; output a clear multi-file tree separating the type system, the entity/schema core, the mapping engine, the graph, and the I/O execution adapter. Do not over-engineer individual leaf utilities, but keep each responsibility in its own module.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in "Core Features" represent a **black-box testing contract** for the execution adapter, NOT the internal data model. The core business logic must remain completely decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls on the core domain and rendering the results.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Separate value parsing, schema resolution, record mapping, comparison, and output formatting into distinct units.
   - **Open/Closed Principle (OCP):** New property types or schemas must be addable without modifying the comparison or rendering engine.
   - **Liskov Substitution Principle (LSP):** Every property type must be substitutable wherever the abstract property-type interface is expected.
   - **Interface Segregation Principle (ISP):** Keep type/schema interfaces small and cohesive.
   - **Dependency Inversion Principle (DIP):** High-level mapping and comparison logic depend on the abstract type/schema interfaces, not on concrete I/O.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface (a value-type registry, an entity proxy, a schema model) must be elegant and idiomatic to the target language.
   - **Resilience:** Edge cases (null values, unknown properties, incompatible schemas, malformed records) must be modeled with explicit error types rather than generic faults. The execution adapter normalizes every such error into a language-neutral category line of the form `error=<category>` plus neutral context fields; it MUST NOT leak host-language exception classes, runtime message text, or object reprs into stdout.

---

## Core Features

### Feature 1: Typed Value Normalization & Validation

**As a developer**, I want to clean and validate raw values against a library of property types, so I can store consistent, canonical data regardless of how messy the input was.

**Expected Behavior / Usage:**

The system exposes a registry of named property types. Two operations are common to every type. `normalize` returns a canonical string form of a value or the null token `<none>` when the value cannot be represented as that type. `validate` returns `valid=true`/`valid=false` indicating whether the value is a usable instance of the type. Each leaf below is one property type with its own rules.

*1.1 Email — local part preserved, domain lowercased, malformed/over-long rejected*

An email is canonicalized by lowercasing only the domain (the local part keeps its case), stripping surrounding quotes. Values without an `@`, without a local part, without a domain, or with a domain label longer than the DNS limit are not valid emails.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_email.json`

```json
{
    "description": "Email addresses are normalized by lowercasing the domain while preserving the local part, stripping surrounding quotes, and rejecting malformed or over-long values; validation reports whether a value is a usable address.",
    "cases": [
        {"input": {"command": "normalize", "type": "email", "value": "foo@PUDO.org"}, "expected_output": "value=foo@pudo.org"},
        {"input": {"command": "normalize", "type": "email", "value": "FOO@PUDO.org"}, "expected_output": "value=FOO@pudo.org"},
        {"input": {"command": "normalize", "type": "email", "value": "\"foo@pudo.org\""}, "expected_output": "value=foo@pudo.org"},
        {"input": {"command": "normalize", "type": "email", "value": "@pudo.org"}, "expected_output": "value=<none>"},
        {"input": {"command": "validate", "type": "email", "value": "foo@pudo.org"}, "expected_output": "valid=true"},
        {"input": {"command": "validate", "type": "email", "value": "foo@pudo"}, "expected_output": "valid=false"}
    ]
}
```

*1.2 Phone — normalized to international form, region hint required for local numbers*

A phone number is normalized to its international `+<digits>` form. A number already carrying an international prefix is normalized directly. A number written in national form can only be resolved when an associated country region hint is supplied (`country`); otherwise it normalizes to `<none>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_phone.json`

```json
{
    "description": "Phone numbers are normalized to E.164 form. A value without an international prefix can only be resolved when a region hint is supplied via an associated country; otherwise it is rejected.",
    "cases": [
        {"input": {"command": "normalize", "type": "phone", "value": "+1-800-784-2433"}, "expected_output": "value=+18007842433"},
        {"input": {"command": "normalize", "type": "phone", "value": "+1 800 784 2433"}, "expected_output": "value=+18007842433"},
        {"input": {"command": "normalize", "type": "phone", "value": "+1 555 8379"}, "expected_output": "value=<none>"},
        {"input": {"command": "normalize", "type": "phone", "value": "017623423980"}, "expected_output": "value=<none>"},
        {"input": {"command": "normalize", "type": "phone", "value": "017623423980", "country": "DE"}, "expected_output": "value=+4917623423980"},
        {"input": {"command": "validate", "type": "phone", "value": "banana"}, "expected_output": "valid=false"}
    ]
}
```

*1.3 URL — canonical absolute form, host case preserved*

A URL is canonicalized to an absolute form: a missing path becomes `/`, query parameters are reordered into a stable order, while the host's letter case is preserved. Validation accepts schemeless hosts and protocol-relative `//host` forms but rejects bare words.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_url.json`

```json
{
    "description": "URLs are normalized to a canonical absolute form: a path is added when missing and query parameters are reordered, while the host case is preserved. Validation accepts schemeless and protocol-relative hosts but rejects bare words.",
    "cases": [
        {"input": {"command": "normalize", "type": "url", "value": "http://foo.com?b=1&a=2"}, "expected_output": "value=http://foo.com/?b=1&a=2"},
        {"input": {"command": "normalize", "type": "url", "value": "http://FOO.com"}, "expected_output": "value=http://FOO.com/"},
        {"input": {"command": "normalize", "type": "url", "value": "http://foo.com/#lala"}, "expected_output": "value=http://foo.com/#lala"},
        {"input": {"command": "validate", "type": "url", "value": "foo.org"}, "expected_output": "valid=true"},
        {"input": {"command": "validate", "type": "url", "value": "//foo.org"}, "expected_output": "valid=true"},
        {"input": {"command": "validate", "type": "url", "value": "hello"}, "expected_output": "valid=false"}
    ]
}
```

*1.4 Bank account number — spaces stripped, uppercased, checksum & structure validated*

A bank account number is normalized by removing whitespace and uppercasing. Validation enforces the country-specific structure and the checksum; an account with a broken checksum or a non-numeric body where digits are required is rejected.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_iban.json`

```json
{
    "description": "International bank account numbers are normalized by removing spaces and uppercasing. Validation enforces the checksum and per-country structure across many national formats.",
    "cases": [
        {"input": {"command": "normalize", "type": "iban", "value": "GB29 NWBK 6016 1331 9268 19"}, "expected_output": "value=GB29NWBK60161331926819"},
        {"input": {"command": "validate", "type": "iban", "value": "GB29 NWBK 6016 1331 9268 19"}, "expected_output": "valid=true"},
        {"input": {"command": "validate", "type": "iban", "value": "GB28 NWBK 6016 1331 9268 19"}, "expected_output": "valid=false"},
        {"input": {"command": "validate", "type": "iban", "value": "DE91100000000123456789"}, "expected_output": "valid=true"}
    ]
}
```

*1.5 Name — whitespace collapsed, quotes stripped*

A name is normalized by collapsing runs of internal whitespace to a single space, trimming the ends, and stripping enclosing quotes. An empty string is not a valid name.

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_name.json`

```json
{
    "description": "Personal and organization names are normalized by collapsing internal whitespace and stripping surrounding quotes. Empty input is rejected by validation.",
    "cases": [
        {"input": {"command": "normalize", "type": "name", "value": "Hans   Well "}, "expected_output": "value=Hans Well"},
        {"input": {"command": "normalize", "type": "name", "value": "\"Hans Well\""}, "expected_output": "value=Hans Well"},
        {"input": {"command": "validate", "type": "name", "value": "huhu"}, "expected_output": "valid=true"},
        {"input": {"command": "validate", "type": "name", "value": ""}, "expected_output": "valid=false"}
    ]
}
```

*1.6 Address — line breaks flattened to comma-separated segments*

A postal address is normalized by turning line breaks into comma separators and collapsing whitespace, without producing duplicated separators when the input already contains a comma at a line end.

**Test Cases:** `rcb_tests/public_test_cases/feature1_6_address.json`

```json
{
    "description": "Postal addresses are normalized by flattening line breaks into comma-separated segments and collapsing whitespace, avoiding duplicated separators.",
    "cases": [
        {"input": {"command": "normalize", "type": "address", "value": "43 Duke Street\nEdinburgh\nEH6 8HH"}, "expected_output": "value=43 Duke Street, Edinburgh, EH6 8HH"},
        {"input": {"command": "normalize", "type": "address", "value": "huhu\n   haha"}, "expected_output": "value=huhu, haha"},
        {"input": {"command": "normalize", "type": "address", "value": "huhu,\n haha"}, "expected_output": "value=huhu, haha"}
    ]
}
```

*1.7 Date — ISO-8601 partial form, zero-padding, all-zero segments chopped*

A date is normalized toward ISO-8601: numeric month/day components are zero-padded; trailing all-zero segments are chopped back to the most precise meaningful prefix (`2017-00-00` → `2017`); unparseable input becomes `<none>`. A custom input `format` may be provided. Validation accepts ISO timestamps (with timezones) and partial ISO dates down to a 4-digit year, but rejects non-ISO orderings and impossible months.

**Test Cases:** `rcb_tests/public_test_cases/feature1_7_date.json`

```json
{
    "description": "Dates are normalized to ISO-8601 partial form: numeric components are zero-padded, all-zero month/day segments are chopped back to the most precise meaningful prefix, and unparseable input is rejected. A custom input format can be supplied.",
    "cases": [
        {"input": {"command": "normalize", "type": "date", "value": "2017-1-3"}, "expected_output": "value=2017-01-03"},
        {"input": {"command": "normalize", "type": "date", "value": "2017-00-00T12:03:49"}, "expected_output": "value=2017"},
        {"input": {"command": "normalize", "type": "date", "value": "2017-0"}, "expected_output": "value=2017"},
        {"input": {"command": "normalize", "type": "date", "value": "banana"}, "expected_output": "value=<none>"},
        {"input": {"command": "normalize", "type": "date", "value": "4/2017", "format": "%m/%Y"}, "expected_output": "value=2017-04"},
        {"input": {"command": "validate", "type": "date", "value": "2017-04-04T10:30:29+03:00"}, "expected_output": "valid=true"},
        {"input": {"command": "validate", "type": "date", "value": "2017-20-01"}, "expected_output": "valid=false"}
    ]
}
```

*1.8 Country — resolved to lowercase ISO codes, names and historical states mapped*

A country value is resolved to a lowercase code. Known country names (including historical states) are mapped to their codes; two-letter codes pass through lowercased; three-letter or unknown codes are rejected. Fuzzy name matching can be disabled (`fuzzy: false`).

**Test Cases:** `rcb_tests/public_test_cases/feature1_8_country.json`

```json
{
    "description": "Country values are resolved to lowercase ISO codes. Known names (including historical states) are mapped to their codes, three-letter and unknown codes are rejected, and fuzzy name matching can be disabled.",
    "cases": [
        {"input": {"command": "normalize", "type": "country", "value": "DE"}, "expected_output": "value=de"},
        {"input": {"command": "normalize", "type": "country", "value": "Germany"}, "expected_output": "value=de"},
        {"input": {"command": "normalize", "type": "country", "value": "Soviet Union"}, "expected_output": "value=suhh"},
        {"input": {"command": "normalize", "type": "country", "value": "Takatukaland", "fuzzy": false}, "expected_output": "value=<none>"},
        {"input": {"command": "validate", "type": "country", "value": "DEU"}, "expected_output": "valid=false"},
        {"input": {"command": "validate", "type": "country", "value": "XK"}, "expected_output": "valid=true"}
    ]
}
```

*1.9 Language — resolved to three-letter codes*

A language value resolves to a three-letter code; a two-letter code is expanded to its three-letter equivalent; unknown codes are rejected.

**Test Cases:** `rcb_tests/public_test_cases/feature1_9_language.json`

```json
{
    "description": "Language values are resolved to three-letter codes; two-letter codes are expanded, and unknown codes are rejected.",
    "cases": [
        {"input": {"command": "normalize", "type": "language", "value": "de"}, "expected_output": "value=deu"},
        {"input": {"command": "normalize", "type": "language", "value": "deu"}, "expected_output": "value=deu"},
        {"input": {"command": "normalize", "type": "language", "value": "xx"}, "expected_output": "value=<none>"},
        {"input": {"command": "validate", "type": "language", "value": "eng"}, "expected_output": "valid=true"},
        {"input": {"command": "validate", "type": "language", "value": "us"}, "expected_output": "valid=false"}
    ]
}
```

*1.10 Topic — controlled vocabulary, lowercased*

A topic tag is normalized by lowercasing and must belong to a fixed controlled vocabulary; arbitrary words are rejected.

**Test Cases:** `rcb_tests/public_test_cases/feature1_10_topic.json`

```json
{
    "description": "Topic tags are normalized by lowercasing and must belong to the controlled vocabulary; arbitrary words are rejected.",
    "cases": [
        {"input": {"command": "normalize", "type": "topic", "value": "role.PEP"}, "expected_output": "value=role.pep"},
        {"input": {"command": "normalize", "type": "topic", "value": "banana"}, "expected_output": "value=<none>"},
        {"input": {"command": "validate", "type": "topic", "value": "role.pep"}, "expected_output": "valid=true"},
        {"input": {"command": "validate", "type": "topic", "value": "DEU"}, "expected_output": "valid=false"}
    ]
}
```

*1.11 MIME type — lowercased and trimmed*

A MIME type is normalized by lowercasing and trimming; blank input becomes `<none>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_11_mimetype.json`

```json
{
    "description": "MIME types are normalized by lowercasing and trimming; blank input is rejected.",
    "cases": [
        {"input": {"command": "normalize", "type": "mimetype", "value": "text/PLAIN"}, "expected_output": "value=text/plain"},
        {"input": {"command": "normalize", "type": "mimetype", "value": " "}, "expected_output": "value=<none>"}
    ]
}
```

*1.12 IP address — IPv4 and IPv6 structure validated*

An IP value is validated for IPv4 and IPv6 structure: out-of-range octets, wrong group counts and non-hex IPv6 groups are rejected. Normalizing junk yields `<none>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_12_ip.json`

```json
{
    "description": "IP addresses are validated for both IPv4 and IPv6 structure; malformed octets or groups are rejected. Cleaning passes through valid addresses and rejects junk.",
    "cases": [
        {"input": {"command": "validate", "type": "ip", "value": "172.16.254.1"}, "expected_output": "valid=true"},
        {"input": {"command": "validate", "type": "ip", "value": "355.16.254.1"}, "expected_output": "valid=false"},
        {"input": {"command": "validate", "type": "ip", "value": "2001:db8:0:1234:0:567:8:1"}, "expected_output": "valid=true"},
        {"input": {"command": "validate", "type": "ip", "value": "2001:zz8:0:1234:0:567:8:1"}, "expected_output": "valid=false"},
        {"input": {"command": "normalize", "type": "ip", "value": "-1"}, "expected_output": "value=<none>"}
    ]
}
```

*1.13 Entity reference — id strings and id-bearing objects*

An entity-reference identifier accepts digits, dashes and dots, and may be extracted from an object carrying an `id` field, but rejects values containing spaces or special characters.

**Test Cases:** `rcb_tests/public_test_cases/feature1_13_entity_ref.json`

```json
{
    "description": "Entity reference identifiers accept digits, dashes and dots and may be extracted from an object carrying an id field, but reject values containing spaces or special characters.",
    "cases": [
        {"input": {"command": "normalize", "type": "entity", "value": "888"}, "expected_output": "value=888"},
        {"input": {"command": "normalize", "type": "entity", "value": {"id": 888}}, "expected_output": "value=888"},
        {"input": {"command": "normalize", "type": "entity", "value": "With spaces"}, "expected_output": "value=<none>"},
        {"input": {"command": "normalize", "type": "entity", "value": "With-dash"}, "expected_output": "value=With-dash"},
        {"input": {"command": "normalize", "type": "entity", "value": "with.dot"}, "expected_output": "value=with.dot"},
        {"input": {"command": "normalize", "type": "entity", "value": "With!special"}, "expected_output": "value=<none>"}
    ]
}
```

*1.14 Generic identifier — prefix-tolerant comparison*

A generic identifier passes through largely unchanged, but supports a fuzzy `similarity` comparison (0.0–1.0) that ignores a differing leading alphabetic prefix when matching the numeric body. A null operand scores `0.0`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_14_identifier.json`

```json
{
    "description": "Generic identifiers pass through largely unchanged but support fuzzy comparison that ignores a leading alphabetic prefix.",
    "cases": [
        {"input": {"command": "normalize", "type": "identifier", "value": "88/9"}, "expected_output": "value=88/9"},
        {"input": {"command": "similarity", "type": "identifier", "left": "AS9818700", "right": "9818700"}, "expected_output": "score=0.7778"},
        {"input": {"command": "similarity", "type": "identifier", "left": null, "right": "9818700"}, "expected_output": "score=0.0"}
    ]
}
```

*1.15 Structured JSON value — packed and unpacked*

An arbitrary structured value is packed into a stable JSON wire string by `normalize`, and `json_unpack` recovers the original structure. `value=<none>` is produced for null input.

**Test Cases:** `rcb_tests/public_test_cases/feature1_15_json.json`

```json
{
    "description": "Arbitrary structured values are packed into a stable JSON wire string and can be unpacked back into the original structure.",
    "cases": [
        {"input": {"command": "normalize", "type": "json", "value": "88"}, "expected_output": "value=88"},
        {"input": {"command": "json_unpack", "value": {"id": 88}}, "expected_output": "value={\"id\": 88}"}
    ]
}
```

---

### Feature 2: Numeric & Temporal Casting

**As a developer**, I want to cast string values into comparable numbers, so I can sort, range-filter and compute on data that arrived as text.

**Expected Behavior / Usage:**

*2.1 Number casting — grouping separators and sign spacing tolerated*

A numeric string is cast to a floating-point value, tolerating thousands/grouping separators and spacing around the sign. Non-numeric input yields `<none>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_number.json`

```json
{
    "description": "Numeric strings are cast to floating-point values, tolerating grouping separators and sign spacing; non-numeric input yields no value.",
    "cases": [
        {"input": {"command": "as_number", "type": "number", "value": "1,00,000"}, "expected_output": "number=100000.0"},
        {"input": {"command": "as_number", "type": "number", "value": " -999.0"}, "expected_output": "number=-999.0"},
        {"input": {"command": "as_number", "type": "number", "value": "- 1,00,000.234"}, "expected_output": "number=-100000.234"},
        {"input": {"command": "as_number", "type": "number", "value": "banana"}, "expected_output": "number=<none>"}
    ]
}
```

*2.2 Date-to-number casting — precision follows input precision*

A date is cast to an epoch-seconds value whose magnitude reflects the precision of the input: a full timestamp, a day, and a bare year each produce a distinct numeric anchor.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_date_number.json`

```json
{
    "description": "Dates are cast to a numeric epoch-seconds value whose precision follows the precision of the input (year, month, day, hour, minute or second).",
    "cases": [
        {"input": {"command": "as_number", "type": "date", "value": "2017-04-04T10:30:29"}, "expected_output": "number=1491301829.0"},
        {"input": {"command": "as_number", "type": "date", "value": "2017-04-04"}, "expected_output": "number=1491264000.0"},
        {"input": {"command": "as_number", "type": "date", "value": "2017"}, "expected_output": "number=1483228800.0"}
    ]
}
```

---

### Feature 3: Region Inference

**As a developer**, I want to infer a region code from values that embed one, so I can geo-tag data that has no explicit country field.

**Expected Behavior / Usage:**

A region hint is a lowercase country code or `<none>` when none can be inferred. Each leaf covers one value type whose structure embeds a region.

*3.1 Phone region — derived from the calling-code prefix*

A normalized international phone number yields a lowercase region code derived from its leading calling code.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_phone_country.json`

```json
{
    "description": "A normalized international phone number yields a lowercase region code derived from its calling-code prefix.",
    "cases": [
        {"input": {"command": "infer_country", "type": "phone", "value": "+4917623423980"}, "expected_output": "country=de"},
        {"input": {"command": "infer_country", "type": "phone", "value": "+18007842433"}, "expected_output": "country=us"},
        {"input": {"command": "infer_country", "type": "phone", "value": null}, "expected_output": "country=<none>"}
    ]
}
```

*3.2 Bank account region — derived from the leading country segment*

A bank account number yields a lowercase region code from its leading country segment.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_iban_country.json`

```json
{
    "description": "A bank account number yields a lowercase region code taken from its leading country segment.",
    "cases": [
        {"input": {"command": "infer_country", "type": "iban", "value": "AE460090000000123456789"}, "expected_output": "country=ae"}
    ]
}
```

*3.3 Country self-hint — a country code hints itself, unrelated text hints nothing*

A country code is echoed as its own region hint; a value of an unrelated type (e.g. a name) produces no hint.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_country_hint.json`

```json
{
    "description": "A country code is echoed as its own region hint.",
    "cases": [
        {"input": {"command": "infer_country", "type": "country", "value": "eu"}, "expected_output": "country=eu"},
        {"input": {"command": "infer_country", "type": "name", "value": "banana"}, "expected_output": "country=<none>"}
    ]
}
```

---

### Feature 4: RDF Terms & Graph Node Identifiers

**As a developer**, I want typed values to render to stable, namespaced string keys, so I can export them to a triple store or use them as graph node ids.

**Expected Behavior / Usage:**

*4.1 RDF term — type-prefixed term string*

A typed value renders to a stable RDF term string whose prefix encodes the value's type namespace.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_rdf_term.json`

```json
{
    "description": "Typed values render to stable, namespaced RDF term strings that encode the value's type as a prefix.",
    "cases": [
        {"input": {"command": "rdf_term", "type": "ip", "value": "172.16.254.1"}, "expected_output": "term=ip:172.16.254.1"},
        {"input": {"command": "rdf_term", "type": "iban", "value": "GB29NWBK60161331926819"}, "expected_output": "term=iban:GB29NWBK60161331926819"},
        {"input": {"command": "rdf_term", "type": "language", "value": "deu"}, "expected_output": "term=iso-639:deu"},
        {"input": {"command": "rdf_term", "type": "mimetype", "value": "text/plain"}, "expected_output": "term=urn:mimetype:text/plain"},
        {"input": {"command": "rdf_term", "type": "topic", "value": "role.pep"}, "expected_output": "term=ftm:topic:role.pep"},
        {"input": {"command": "rdf_term", "type": "country", "value": "eu"}, "expected_output": "term=iso-3166-1:eu"},
        {"input": {"command": "rdf_term", "type": "checksum", "value": "00deadbeef"}, "expected_output": "term=hash:00deadbeef"}
    ]
}
```

*4.2 Node identifier — type-prefixed, case-normalized*

A pivotable typed value renders to a graph node id that is type-prefixed and case-normalized (so a mixed-case account number yields the same id as its canonical form).

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_node_id.json`

```json
{
    "description": "Pivotable typed values render to a graph node identifier string that is type-prefixed and case-normalized.",
    "cases": [
        {"input": {"command": "node_id", "type": "iban", "value": "gb29NWBK60161331926819"}, "expected_output": "node_id=iban:GB29NWBK60161331926819"},
        {"input": {"command": "node_id", "type": "ip", "value": "172.16.254.1"}, "expected_output": "node_id=ip:172.16.254.1"}
    ]
}
```

---

### Feature 5: Specificity & Similarity Scoring

**As a developer**, I want to score how informative a value is and how similar two values are, so I can weight and drive entity matching.

**Expected Behavior / Usage:**

*5.1 Specificity — how informative a single value is*

`specificity` returns a 0.0–1.0 score: a full date scores above a bare year, a longer email/name above a tiny one, and unmatchable values score `0.0`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_specificity.json`

```json
{
    "description": "Specificity scores how informative a value is (0.0 to 1.0): a full date scores above a bare year, a longer name above a two-letter one, and unmatchable values score zero.",
    "cases": [
        {"input": {"command": "specificity", "type": "date", "value": "2011"}, "expected_output": "specificity=0.0"},
        {"input": {"command": "specificity", "type": "date", "value": "2011-01-01"}, "expected_output": "specificity=0.625"},
        {"input": {"command": "specificity", "type": "email", "value": "foo@pudo.org"}, "expected_output": "specificity=1.0"},
        {"input": {"command": "specificity", "type": "name", "value": "bo"}, "expected_output": "specificity=0.0"}
    ]
}
```

*5.2 Pairwise similarity — identical max, mismatch/null zero*

`similarity` compares two values of the same type on a 0.0–1.0 scale: identical values score the maximum, a mismatch or a null operand scores `0.0`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_similarity.json`

```json
{
    "description": "Similarity compares two values of the same type on a 0.0 to 1.0 scale: identical values score the maximum, a mismatch or a null operand scores zero, and identifiers match across a differing leading prefix.",
    "cases": [
        {"input": {"command": "similarity", "type": "iban", "left": "AE460090000000123456789", "right": "AE460090000000123456789"}, "expected_output": "score=1.0"},
        {"input": {"command": "similarity", "type": "iban", "left": "AE460090000000123456789", "right": "AE460090000000123456789X"}, "expected_output": "score=0.0"},
        {"input": {"command": "similarity", "type": "iban", "left": "AE460090000000123456789", "right": null}, "expected_output": "score=0.0"}
    ]
}
```

*5.3 Best value — pick the most informative candidate*

`best_value` selects the most informative form from a candidate list (e.g. the variant carrying the most capitalization signal), returning `<none>` for an empty list.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_best_value.json`

```json
{
    "description": "Selecting the best value from a candidate list prefers the most informative form (e.g. the variant with the most capitalization signal), returning nothing for an empty list.",
    "cases": [
        {"input": {"command": "best_value", "type": "name", "values": ["Banana", "banana", "nanana", "Batman"]}, "expected_output": "value=Banana"},
        {"input": {"command": "best_value", "type": "name", "values": ["Robert Smith", "Rob Smith", "Robert SMITH"]}, "expected_output": "value=Robert SMITH"},
        {"input": {"command": "best_value", "type": "name", "values": []}, "expected_output": "value=<none>"}
    ]
}
```

*5.4 Set similarity — overlap between two collections*

`similarity_sets` compares two collections and returns a positive score when they share members (including prefix-tolerant identifier matches), zero when one side is empty.

**Test Cases:** `rcb_tests/public_test_cases/feature5_4_set_similarity.json`

```json
{
    "description": "Set similarity compares two collections of values and returns a positive score when they share members, zero when one side is empty.",
    "cases": [
        {"input": {"command": "similarity_sets", "type": "name", "left": ["banana"], "right": ["banana"]}, "expected_output": "score=1.0"},
        {"input": {"command": "similarity_sets", "type": "name", "left": ["banana"], "right": []}, "expected_output": "score=0.0"},
        {"input": {"command": "similarity_sets", "type": "identifier", "left": ["9818700"], "right": ["AS9818700"]}, "expected_output": "score=0.7778"}
    ]
}
```

---

### Feature 6: Type Registry & Metadata

**As a developer**, I want to discover types and their descriptive metadata by name, so I can build generic UIs and pipelines over the type system.

**Expected Behavior / Usage:**

*6.1 Registry lookup — resolve a type by name*

`registry_lookup` reports whether a type name is known and echoes its canonical name.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_registry.json`

```json
{
    "description": "The type registry resolves a type by name, reporting whether the name is known.",
    "cases": [
        {"input": {"command": "registry_lookup", "name": "entity"}, "expected_output": "found=true\nname=entity"},
        {"input": {"command": "registry_lookup", "name": "banana"}, "expected_output": "found=false\nname=<none>"}
    ]
}
```

*6.2 Type metadata — machine name, label, group*

`type_info` exposes a type's stable machine name, a human label, and an optional grouping key used to invert properties of that type.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_type_info.json`

```json
{
    "description": "Each type exposes descriptive metadata: a stable machine name, a human label, and an optional grouping key.",
    "cases": [
        {"input": {"command": "type_info", "type": "name"}, "expected_output": "name=name\nlabel=Name\ngroup=names"},
        {"input": {"command": "type_info", "type": "country"}, "expected_output": "name=country\nlabel=Country\ngroup=countries"}
    ]
}
```

---

### Feature 7: Entity Proxy

**As a developer**, I want a convenient wrapper around an entity's typed multi-valued properties, so I can read, mutate and combine entity data safely.

**Expected Behavior / Usage:**

An entity is a JSON object with `id`, `schema` and a `properties` map of property name to a list of string values. Property values are always sets of strings (no duplicates, no nulls). Operations that name a property absent from the entity's schema produce the normalized error `error=unknown_property` with a `property=<name>` field.

*7.1 Add values — append valid, drop empties/dupes, reject unknown property*

Adding values appends each valid value, silently ignoring null/blank values and duplicates. The response lists the resulting (sorted) values and their count. Adding to, or reading, a property the schema does not define is a normalized `unknown_property` error.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_add.json`

```json
{
    "description": "Adding property values to an entity appends valid values, silently ignores null/blank input and duplicates, and reports a normalized error category when the property is not part of the schema.",
    "cases": [
        {"input": {"command": "entity_add", "entity": {"id": "t", "schema": "Person", "properties": {"name": ["Ralph Tester"]}}, "property": "name", "values": ["Ralph the Great", null, "", "Ralph Tester"]}, "expected_output": "values=Ralph Tester;Ralph the Great\ncount=2"},
        {"input": {"command": "entity_add", "entity": {"id": "t", "schema": "Person", "properties": {}}, "property": "banana", "values": ["yellow"]}, "expected_output": "error=unknown_property\nproperty=banana"},
        {"input": {"command": "entity_first", "entity": {"id": "test", "schema": "Person", "properties": {"name": ["Ralph Tester"], "idNumber": ["9177171", "8e839023"]}}, "property": "banana"}, "expected_output": "error=unknown_property\nproperty=banana"}
    ]
}
```

*7.2 Set — replace and deduplicate*

Setting a property replaces all current values with the given one(s), deduplicating repeated assignments; a subsequent add extends the set.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_set.json`

```json
{
    "description": "Setting a property replaces all existing values with the given one, deduplicating repeated assignments.",
    "cases": [
        {"input": {"command": "entity_set", "entity": {"id": "t", "schema": "Person", "properties": {}}, "property": "birthPlace", "set": ["Inferno", "Inferno"], "add": ["Hell"]}, "expected_output": "values=Hell;Inferno\ncount=2"},
        {"input": {"command": "entity_set", "entity": {"id": "t", "schema": "Person", "properties": {}}, "property": "birthPlace", "set": ["Inferno"]}, "expected_output": "values=Inferno\ncount=1"}
    ]
}
```

*7.3 Remove — drop one value, keep the rest*

Removing a specific value drops only that value and leaves the property otherwise intact; removing an absent value is a no-op. The response reports the remaining values and whether the property still has any.

**Test Cases:** `rcb_tests/public_test_cases/feature7_3_remove.json`

```json
{
    "description": "Removing a specific value drops only that value and leaves the rest of the property intact; removing an absent value is a no-op.",
    "cases": [
        {"input": {"command": "entity_remove", "entity": {"id": "test", "schema": "Person", "properties": {"name": ["Ralph Tester"], "idNumber": ["9177171", "8e839023"]}}, "property": "idNumber", "value": "9177171"}, "expected_output": "values=8e839023\npresent=true"},
        {"input": {"command": "entity_remove", "entity": {"id": "test", "schema": "Person", "properties": {"name": ["Ralph Tester"], "idNumber": ["9177171", "8e839023"]}}, "property": "idNumber", "value": "banana"}, "expected_output": "values=8e839023;9177171\npresent=true"}
    ]
}
```

*7.4 Pop — read and clear at once*

Popping a property returns and clears all of its values; popping an empty property returns nothing.

**Test Cases:** `rcb_tests/public_test_cases/feature7_4_pop.json`

```json
{
    "description": "Popping a property returns and clears all of its values at once; popping an empty property returns nothing.",
    "cases": [
        {"input": {"command": "entity_pop", "entity": {"id": "test", "schema": "Person", "properties": {"name": ["Ralph Tester"], "idNumber": ["9177171", "8e839023"]}}, "property": "idNumber"}, "expected_output": "popped=8e839023;9177171\nremaining="},
        {"input": {"command": "entity_pop", "entity": {"id": "t", "schema": "Person", "properties": {}}, "property": "name"}, "expected_output": "popped=\nremaining="}
    ]
}
```

*7.5 Type inversion & caption — group values by type, derive a caption*

An entity inverts into type-grouped value buckets (keyed by each type's group name) and exposes a human-readable caption derived from its most salient name.

**Test Cases:** `rcb_tests/public_test_cases/feature7_5_inverted.json`

```json
{
    "description": "An entity can be inverted into type-grouped value buckets and exposes a human-readable caption derived from its most salient name.",
    "cases": [
        {"input": {"command": "entity_inverted", "entity": {"id": "ralph", "schema": "Person", "properties": {"name": ["Ralph Tester"], "birthDate": ["1972-05-01"], "idNumber": ["9177171", "8e839023"], "website": ["https://ralphtester.me"], "phone": ["+12025557612"], "email": ["info@ralphtester.me"], "topics": ["role.spy"]}}}, "expected_output": "caption=Ralph Tester\ndates=1972-05-01\nemails=info@ralphtester.me\nidentifiers=8e839023;9177171\nnames=Ralph Tester\nphones=+12025557612\ntopics=role.spy\nurls=https://ralphtester.me"}
    ]
}
```

*7.6 Merge — union compatible entities, reject incompatible*

Merging one entity into another unions their property values when their schemas are compatible (one derives from the other or shares a common descendant); otherwise it is a normalized `error=schema_conflict`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_6_merge.json`

```json
{
    "description": "Merging one entity into another unions their property values when their schemas are compatible, and reports a normalized conflict category when they are not.",
    "cases": [
        {"input": {"command": "entity_merge", "entity": {"id": "x", "schema": "Person", "properties": {"name": ["Ralph Tester"]}}, "other": {"id": "x", "schema": "LegalEntity", "properties": {"country": ["gb"]}}}, "expected_output": "countries=gb\nnames=Ralph Tester"},
        {"input": {"command": "entity_merge", "entity": {"id": "x", "schema": "Person", "properties": {"name": ["Ralph Tester"]}}, "other": {"id": "x", "schema": "Vessel", "properties": {}}}, "expected_output": "error=schema_conflict"}
    ]
}
```

---

### Feature 8: Schema Model & Ontology

**As a developer**, I want a shared schema ontology with inheritance, inverse relations and matchability, so entities from different sources speak the same vocabulary.

**Expected Behavior / Usage:**

Schemas form an inheritance hierarchy and carry properties; some properties are relations with an inverse on the target schema. Operations naming an unknown schema produce `error=unknown_schema` with a `schema=<name>` field.

*8.1 Descent test — is-a a named ancestor*

A schema reports whether it is the same as, or descends from, a named ancestor.

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_is_a.json`

```json
{
    "description": "Schema descent can be queried: a schema reports whether it is the same as or derived from a named ancestor.",
    "cases": [
        {"input": {"command": "schema_is_a", "schema": "LegalEntity", "ancestor": "Thing"}, "expected_output": "is_a=true"},
        {"input": {"command": "schema_is_a", "schema": "Ownership", "ancestor": "Interest"}, "expected_output": "is_a=true"},
        {"input": {"command": "schema_is_a", "schema": "Vessel", "ancestor": "LegalEntity"}, "expected_output": "is_a=false"}
    ]
}
```

*8.2 Common schema — closest shared schema, or none*

The closest common schema of two schemas is resolved where one exists (the more specific of an ancestor/descendant pair); an incompatible pair yields `error=no_common_schema`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_common.json`

```json
{
    "description": "The closest common schema of two schemas is resolved where one exists; incompatible pairs yield a normalized error category.",
    "cases": [
        {"input": {"command": "schema_common", "left": "LegalEntity", "right": "Company"}, "expected_output": "schema=Company"},
        {"input": {"command": "schema_common", "left": "Thing", "right": "Person"}, "expected_output": "schema=Person"},
        {"input": {"command": "schema_common", "left": "Person", "right": "Company"}, "expected_output": "error=no_common_schema"}
    ]
}
```

*8.3 Descendants — schemas derived from this one*

A schema enumerates the set of schemas that derive from it, excluding itself. The response lists them sorted, separated by `;`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_3_descendants.json`

```json
{
    "description": "A schema enumerates the set of schemas that derive from it (excluding itself).",
    "cases": [
        {"input": {"command": "schema_descendants", "schema": "Interval"}, "expected_output": "descendants=Associate;Call;ContractAward;CourtCaseParty;Debt;Directorship;Documentation;EconomicActivity;Employment;Event;Family;Identification;Interest;Membership;Message;Ownership;Passport;Payment;Post;Project;ProjectParticipant;Representation;Sanction;Succession;TaxRoll;Trip;UnknownLink"}
    ]
}
```

*8.4 Matchability — may instances be compared*

Two schemas report whether instances of one may be compared against the other; document-like schemas are not matchable against legal entities.

**Test Cases:** `rcb_tests/public_test_cases/feature8_4_matchable.json`

```json
{
    "description": "Two schemas report whether instances of one may be compared against the other; document-like schemas are not matchable against legal entities.",
    "cases": [
        {"input": {"command": "schema_matchable", "left": "Company", "right": "LegalEntity"}, "expected_output": "can_match=true"},
        {"input": {"command": "schema_matchable", "left": "Document", "right": "LegalEntity"}, "expected_output": "can_match=false"}
    ]
}
```

*8.5 Inverse relations — stub flag and reverse name*

A property exposes whether it is a stub (reverse-only navigation) relation, and the name of its inverse property where one exists.

**Test Cases:** `rcb_tests/public_test_cases/feature8_5_reverse.json`

```json
{
    "description": "A property exposes whether it is a stub (reverse-only navigation) relation and the name of its inverse property where one exists.",
    "cases": [
        {"input": {"command": "schema_reverse", "schema": "Thing", "property": "noteEntities"}, "expected_output": "stub=true\nreverse=entity"},
        {"input": {"command": "schema_reverse", "schema": "Associate", "property": "associate"}, "expected_output": "stub=false\nreverse=associations"}
    ]
}
```

*8.6 Payload validation — well-formed vs. malformed property maps*

Validating an entity payload against a schema succeeds for well-formed property maps and yields `error=validation_failed` with a per-property field (e.g. `invalid_name=required`) when a required value is malformed.

**Test Cases:** `rcb_tests/public_test_cases/feature8_6_validate.json`

```json
{
    "description": "Validating an entity payload against a schema succeeds for well-formed property maps and reports a normalized, per-property error category when a required value is malformed.",
    "cases": [
        {"input": {"command": "schema_validate", "schema": "Thing", "data": {"properties": {"name": ["Banana"]}}}, "expected_output": "valid=true"},
        {"input": {"command": "schema_validate", "schema": "Thing", "data": {"properties": {"name": null}}}, "expected_output": "error=validation_failed\ninvalid_name=required"}
    ]
}
```

---

### Feature 9: Deterministic Identifiers & Record Mapping

**As a developer**, I want stable entity ids derived from source keys, so the same record always yields the same entity id across runs and systems.

**Expected Behavior / Usage:**

*9.1 Identifier derivation — stable hash of key fragments*

An entity id is derived by hashing its key fragments: the same fragment always yields the same id, a null fragment yields `<none>`, and an optional key prefix changes the result.

**Test Cases:** `rcb_tests/public_test_cases/feature9_1_make_id.json`

```json
{
    "description": "An entity derives a stable identifier by hashing its key fragments: the same input always yields the same id, a null fragment yields none, and an optional key prefix changes the result.",
    "cases": [
        {"input": {"command": "make_id", "schema": "Thing", "value": "banana"}, "expected_output": "id=250e77f12a5ab6972a0895d290c4792f0a326ea8"},
        {"input": {"command": "make_id", "schema": "Thing", "value": null}, "expected_output": "id=<none>"},
        {"input": {"command": "make_id", "schema": "Thing", "value": "banana", "prefix": "foo"}, "expected_output": "id=ee27ac3f37999d0a8a5ca97d4cf77fb423631edc"}
    ]
}
```

*9.2 Record key mapping — order-independent key hash with optional salt*

A record-to-entity mapping derives each entity id by hashing the configured key columns (order-independent: `[a,b]` and `[b,a]` agree) together with an optional literal salt that is prepended before hashing. A record missing all of its key values produces no entity. The response reports the number of entities and each entity's id.

**Test Cases:** `rcb_tests/public_test_cases/feature9_2_map_keys.json`

```json
{
    "description": "A record-to-entity mapping derives each entity id by hashing the configured key columns (order-independent) together with an optional literal salt; records missing all key values produce no entity.",
    "cases": [
        {"input": {"command": "map_record", "entities": {"test": {"schema": "Person", "key": "id"}}, "record": {"id": "foo"}, "capture": []}, "expected_output": "entities=1\ntest.id=0beec7b5ea3f0fdbc95d0dd47f3c5bc275da8a33"},
        {"input": {"command": "map_record", "entities": {"test": {"schema": "Person", "key": ["b", "a"]}}, "record": {"a": "aaa", "b": "bbb"}, "capture": []}, "expected_output": "entities=1\ntest.id=68d8572c2662b0f06f723d7d507954fb038b8558"},
        {"input": {"command": "map_record", "entities": {"test": {"schema": "Person", "key_literal": "test", "key": ["a", "b"]}}, "record": {"a": "aaa", "b": "bbb"}, "capture": []}, "expected_output": "entities=1\ntest.id=ac14dd13d46f172b4c28b1c3e5c90f0d342b5516"},
        {"input": {"command": "map_record", "entities": {"test": {"schema": "Person", "key": "id"}}, "record": {}, "capture": []}, "expected_output": "entities=0"}
    ]
}
```

*9.3 Mapping transforms — join columns / split a column*

A mapping property generator can join several source columns into one value with a separator, or split a single column into multiple values. The `capture` list requests specific produced property values back in the output.

**Test Cases:** `rcb_tests/public_test_cases/feature9_3_map_transform.json`

```json
{
    "description": "Mapping property generators can join several columns into one value with a separator, or split a single column into multiple values.",
    "cases": [
        {"input": {"command": "map_record", "entities": {"d": {"schema": "Person", "key": "id", "key_literal": "person", "properties": {"address": {"join": ", ", "columns": ["house_number", "town", "zip"]}}}}, "record": {"id": "1", "house_number": "64", "town": "The Desert", "zip": "01234"}, "capture": [{"ref": "d", "property": "address"}]}, "expected_output": "entities=1\nd.id=64abaade7c05afb815c615d3c43509fbd6ebd2ab\nd.address=64, The Desert, 01234"},
        {"input": {"command": "map_record", "entities": {"d": {"schema": "Person", "key": "id", "key_literal": "person", "properties": {"notes": {"split": "; ", "column": "fave_colours"}}}}, "record": {"id": "1", "fave_colours": "brown; black; blue"}, "capture": [{"ref": "d", "property": "notes"}]}, "expected_output": "entities=1\nd.id=64abaade7c05afb815c615d3c43509fbd6ebd2ab\nd.notes=black;blue;brown"}
    ]
}
```

*9.4 Linked entities — one record yields several related entities*

A single record can yield several linked entities, where a relation entity references others by their mapping key. The response reports each produced entity and any captured property.

**Test Cases:** `rcb_tests/public_test_cases/feature9_4_map_links.json`

```json
{
    "description": "A single record can yield multiple linked entities, where a relation entity references others by their mapping key.",
    "cases": [
        {"input": {"command": "map_record", "entities": {"director": {"schema": "Person", "key": "id", "properties": {"name": {"column": "name"}}}, "company": {"schema": "Company", "key": "comp_id", "properties": {"name": {"column": "comp_name"}}}, "directorship": {"schema": "Directorship", "keys": ["comp_id", "id"], "properties": {"director": {"entity": "director"}, "organization": {"entity": "company"}, "role": {"column": "role"}}}}, "record": {"id": "1", "name": "Bob", "comp_id": "9", "comp_name": "ACME", "role": "boss"}, "capture": [{"ref": "company", "property": "name"}]}, "expected_output": "entities=3\ncompany.id=0ade7c2cf97f75d009975f4d720d1fa6c19f4897\ndirector.id=356a192b7913b04c54574d18c28d46e6395428ab\ndirectorship.id=b3f0c7f6bb763af1be91d9e74eabfeb199dc1f1f\ncompany.name=ACME"}
    ]
}
```

---

### Feature 10: Namespace Signing

**As a developer**, I want to sign entity identifiers with a namespace secret, so ids from different datasets stay distinct and tamper-evident.

**Expected Behavior / Usage:**

*10.1 Sign — prefixed signed id plus bare signature*

Signing tags an identifier with a keyed signature computed from a namespace secret, producing a signed id of the form `<id>.<signature>` and the bare signature. A null identifier signs to `<none>`. An empty namespace passes the identifier through unsigned and produces no signature.

**Test Cases:** `rcb_tests/public_test_cases/feature10_1_sign.json`

```json
{
    "description": "Signing tags an identifier with an HMAC computed from a namespace secret, producing a prefixed signed id and a bare signature; an empty namespace passes the identifier through unsigned.",
    "cases": [
        {"input": {"command": "ns_sign", "namespace": "banana", "value": "split"}, "expected_output": "signed=split.18375e11927c10b772d57d7535888545782bd7cf\nsignature=18375e11927c10b772d57d7535888545782bd7cf"},
        {"input": {"command": "ns_sign", "namespace": "banana", "value": null}, "expected_output": "signed=<none>\nsignature=<none>"},
        {"input": {"command": "ns_sign", "namespace": null, "value": "split"}, "expected_output": "signed=split\nsignature=<none>"}
    ]
}
```

*10.2 Verify — accept correctly signed, reject otherwise*

Verification accepts a correctly signed identifier produced for the same namespace and rejects an unsigned or null one.

**Test Cases:** `rcb_tests/public_test_cases/feature10_2_verify.json`

```json
{
    "description": "Verification accepts a correctly signed identifier and rejects an unsigned or null one.",
    "cases": [
        {"input": {"command": "ns_sign", "namespace": "banana", "value": "split"}, "expected_output": "signed=split.18375e11927c10b772d57d7535888545782bd7cf\nsignature=18375e11927c10b772d57d7535888545782bd7cf"},
        {"input": {"command": "ns_verify", "namespace": "banana", "value": "split"}, "expected_output": "verified=false"},
        {"input": {"command": "ns_verify", "namespace": "banana", "value": null}, "expected_output": "verified=false"}
    ]
}
```

---

### Feature 11: Entity Graph Adjacency

**As a developer**, I want to load entities into a property graph and walk adjacency, so I can explore how entities connect through relations and shared values.

**Expected Behavior / Usage:**

Entities are added to a graph whose edges include both relation properties (a relation entity links its endpoints) and shared pivot values (two entities sharing a phone/email/name become adjacent). `graph_adjacent` reports the number of nodes adjacent to a named entity — counting both other entities and the value nodes it pivots on.

**Test Cases:** `rcb_tests/public_test_cases/feature11_adjacency.json`

```json
{
    "description": "Loading entities into a property graph lets callers count the nodes adjacent to a given entity, where adjacency spans both relation edges and shared pivot values.",
    "cases": [
        {"input": {"command": "graph_adjacent", "entities": [{"id": "ralph", "schema": "Person", "properties": {"name": ["Ralph Tester"], "phone": ["+12025557612"], "website": ["https://ralphtester.me"], "email": ["info@ralphtester.me"], "idNumber": ["9177171", "8e839023"]}}, {"id": "jodie", "schema": "Person", "properties": {"name": ["Jodie Tester"], "birthDate": ["1972-05-01"]}}, {"id": "j2r", "schema": "Family", "properties": {"person": ["jodie"], "relative": ["ralph"]}}, {"id": "pass", "schema": "Passport", "properties": {"holder": ["jodie"], "passportNumber": ["HJSJHAS"]}}], "node": "jodie"}, "expected_output": "adjacent=3"},
        {"input": {"command": "graph_adjacent", "entities": [{"id": "ralph", "schema": "Person", "properties": {"name": ["Ralph Tester"], "phone": ["+12025557612"], "website": ["https://ralphtester.me"], "email": ["info@ralphtester.me"], "idNumber": ["9177171", "8e839023"]}}, {"id": "jodie", "schema": "Person", "properties": {"name": ["Jodie Tester"], "birthDate": ["1972-05-01"]}}, {"id": "j2r", "schema": "Family", "properties": {"person": ["jodie"], "relative": ["ralph"]}}, {"id": "pass", "schema": "Passport", "properties": {"holder": ["jodie"], "passportNumber": ["HJSJHAS"]}}], "node": "ralph"}, "expected_output": "adjacent=7"},
        {"input": {"command": "graph_adjacent", "entities": [{"id": "ralph", "schema": "Person", "properties": {"name": ["Ralph Tester"], "phone": ["+12025557612"], "website": ["https://ralphtester.me"], "email": ["info@ralphtester.me"], "idNumber": ["9177171", "8e839023"]}}, {"id": "jodie", "schema": "Person", "properties": {"name": ["Jodie Tester"], "birthDate": ["1972-05-01"]}}, {"id": "j2r", "schema": "Family", "properties": {"person": ["jodie"], "relative": ["ralph"]}}, {"id": "pass", "schema": "Passport", "properties": {"holder": ["jodie"], "passportNumber": ["HJSJHAS"]}}], "node": "pass"}, "expected_output": "adjacent=2"}
    ]
}
```

---

### Feature 12: Entity Transformation Helpers

**As a developer**, I want reusable transformations over entities, so I can derive aliases, file names, cleaned dates and provenance without rewriting them per project.

**Expected Behavior / Usage:**

*12.1 Combine name parts — alias cross-product*

Combining the parts of a person's name produces alias values for every cross-product of first/patronymic/last name fragments; a single last name yields just that name.

**Test Cases:** `rcb_tests/public_test_cases/feature12_1_combine_names.json`

```json
{
    "description": "Combining name parts produces alias values for every cross-product of first/patronymic/last name fragments.",
    "cases": [
        {"input": {"command": "helper", "op": "combine_names", "entity": {"id": "b", "schema": "Person", "properties": {"firstName": ["Vladimir", "Wladimir"], "fatherName": ["Vladimirovitch"], "lastName": ["Putin"]}}}, "expected_output": "alias=Vladimir Putin;Vladimir Vladimirovitch Putin;Wladimir Putin;Wladimir Vladimirovitch Putin"},
        {"input": {"command": "helper", "op": "combine_names", "entity": {"id": "b", "schema": "Person", "properties": {"lastName": ["Putin"]}}}, "expected_output": "alias=Putin"}
    ]
}
```

*12.2 Derive download filename — extension from metadata*

A safe download filename is derived from an entity, taking the extension from an explicit override, then a declared extension, then the MIME type, then an existing file name.

**Test Cases:** `rcb_tests/public_test_cases/feature12_2_filename.json`

```json
{
    "description": "A safe download filename is derived from an entity, deriving the extension from an explicit extension, MIME type or existing file name, with an optional override.",
    "cases": [
        {"input": {"command": "helper", "op": "filename", "entity": {"id": "banana", "schema": "Document", "properties": {"mimeType": ["application/pdf"]}}}, "expected_output": "filename=banana.pdf"},
        {"input": {"command": "helper", "op": "filename", "entity": {"id": "banana", "schema": "Document", "properties": {"extension": [".doc"]}}}, "expected_output": "filename=banana.doc"},
        {"input": {"command": "helper", "op": "filename", "extension": "pdf", "entity": {"id": "banana", "schema": "Document", "properties": {"fileName": ["bla.doc"]}}}, "expected_output": "filename=bla.pdf"}
    ]
}
```

*12.3 Simplify provenance — earliest published, single modified*

Provenance timestamps are simplified to a single earliest published date and a single modified date.

**Test Cases:** `rcb_tests/public_test_cases/feature12_3_provenance.json`

```json
{
    "description": "Provenance timestamps are simplified to a single earliest published date and a single modified date.",
    "cases": [
        {"input": {"command": "helper", "op": "simplify_provenance", "entity": {"id": "b", "schema": "Document", "properties": {"publishedAt": ["2016-01-01", "2018-02-03"], "modifiedAt": ["2016-01-01"]}}}, "expected_output": "publishedAt=2016-01-01\nmodifiedAt=2016-01-01"}
    ]
}
```

*12.4 Drop redundant prefix dates — keep the most precise*

When several dates share a prefix, redundant low-precision dates are dropped in favor of the more precise one that shares the same prefix; unrelated dates are kept.

**Test Cases:** `rcb_tests/public_test_cases/feature12_4_prefix_dates.json`

```json
{
    "description": "Redundant low-precision dates are dropped when a more precise date sharing the same prefix is present.",
    "cases": [
        {"input": {"command": "helper", "op": "remove_prefix_dates", "property": "birthDate", "entity": {"id": "b", "schema": "Person", "properties": {"birthDate": ["2020-01-05", "2020-01", "2020-03", "2020"]}}}, "expected_output": "dates=2020-01-05;2020-03"}
    ]
}
```

*12.5 Assign canonical name — collapse to one*

An entity is assigned a single canonical name chosen from its name candidates; a lone name is left unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature12_5_name_entity.json`

```json
{
    "description": "An entity is assigned a single canonical name chosen from its name candidates; a lone name is left unchanged.",
    "cases": [
        {"input": {"command": "helper", "op": "name_entity", "entity": {"id": "b", "schema": "Person", "properties": {"name": ["Carl"]}}}, "expected_output": "name=Carl"}
    ]
}
```

*12.6 Deceased cutoff — flag implausibly old persons*

A person record is flagged when its birth date is so long ago that the person is assumed deceased; recent births or records already carrying a death date are not flagged.

**Test Cases:** `rcb_tests/public_test_cases/feature12_6_cutoff.json`

```json
{
    "description": "A person record is flagged when its birth date is so long ago that the person is assumed deceased; recent or already-dated records are not flagged.",
    "cases": [
        {"input": {"command": "helper", "op": "person_cutoff", "entity": {"id": "b", "schema": "Person", "properties": {"birthDate": ["1800"]}}}, "expected_output": "cutoff=true"},
        {"input": {"command": "helper", "op": "person_cutoff", "entity": {"id": "b", "schema": "Person", "properties": {"birthDate": ["1985"]}}}, "expected_output": "cutoff=false"},
        {"input": {"command": "helper", "op": "person_cutoff", "entity": {"id": "b", "schema": "Person", "properties": {"birthDate": ["1985"], "deathDate": ["2008"]}}}, "expected_output": "cutoff=false"}
    ]
}
```

*12.7 Strip content hashes — drop checksums, keep the rest*

Content-hash properties are stripped from an entity while other properties are retained.

**Test Cases:** `rcb_tests/public_test_cases/feature12_7_checksums.json`

```json
{
    "description": "Content-hash properties are stripped from an entity while other properties are retained.",
    "cases": [
        {"input": {"command": "helper", "op": "remove_checksums", "entity": {"id": "b", "schema": "Document", "properties": {"contentHash": ["banana"], "title": ["foo"]}}}, "expected_output": "contentHash="}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the typed-value registry, the entity proxy and schema ontology, the record-mapping engine, the entity graph, namespace signing and transformation helpers, with each responsibility in its own module per the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads a single JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. It normalizes every error — including native exceptions raised by the core — into a language-neutral `error=<category>` contract, and is logically and physically separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_email.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_email@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same validation logic as the schema_parser module
- reuse the ranking calculation found in the scoring engine
