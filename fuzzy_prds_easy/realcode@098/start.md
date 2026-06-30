## Product Requirement Document

# Domain Suffix Component Extractor - URL Host Parsing Contract

## Project Goal

Build a domain suffix component extractor that allows developers to split URL-like inputs into fully qualified host, subdomain, registrable domain, public suffix, and IP-address-literal fields without maintaining public suffix parsing rules by hand.

---

## Background & Problem

Without this library/tool, developers are forced to parse host names with ad hoc string splitting and incomplete suffix tables. This leads to incorrect handling of multi-label suffixes, wildcard suffix rules, suffix exceptions, privately managed suffix policies, internationalized and punycode labels, embedded credentials, ports, paths, query strings, fragments, and IP address literals.

With this library/tool, developers pass a URL-like input and receive a stable set of text fields that describe the externally visible host components under public suffix rules, plus optional configuration hooks for custom suffix data, additional suffixes, batch formatting, private-suffix policy, and data-source validation.

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

The default extraction output is a fixed six-row, newline-terminated key/value block in this exact order: `fqdn`, `subdomain`, `domain`, `suffix`, `ipv4`, `ipv6`. The `fqdn` (fully qualified host) is non-empty only when both a registrable domain label and a suffix are present. The `subdomain` holds every label before the registrable domain label, `domain` holds the single registrable label, and `suffix` holds the matched public suffix. The `ipv4`/`ipv6` rows are populated only when the host is an address literal. Unless a feature states otherwise, a bare string input is treated as a URL-like string parsed under the default suffix policy using the bundled suffix data.

### Feature 1: Registered Domain Extraction

**As a developer**, I want to parse common host names against public suffix rules, so I can present stable domain components for ordinary URLs.

**Expected Behavior / Usage:**

The input is a URL-like string whose host ends in a recognized public suffix. The output is the six-row block. `fqdn` equals the complete host (because both a domain label and suffix exist); `subdomain` contains all labels before the registrable domain; `domain` contains the registrable domain label; `suffix` contains the matched public suffix, which may itself span multiple labels (for example a country-code second-level suffix). IP fields stay empty for non-address hosts.

**Test Cases:** `rcb_tests/public_test_cases/feature1_registered_domain_extraction.json`

```json
{
    "description": "Extract a URL-like input into fully qualified host, subdomain, registrable domain label, public suffix, and IPv4/IPv6 fields for ordinary host names whose final labels match a recognized public suffix.",
    "cases": [
        {"input": "http://www.google.com", "expected_output": "fqdn=www.google.com\nsubdomain=www\ndomain=google\nsuffix=com\nipv4=\nipv6=\n"},
        {"input": "http://www.theregister.co.uk", "expected_output": "fqdn=www.theregister.co.uk\nsubdomain=www\ndomain=theregister\nsuffix=co.uk\nipv4=\nipv6=\n"},
        {"input": "http://media.forums.theregister.co.uk", "expected_output": "fqdn=media.forums.theregister.co.uk\nsubdomain=media.forums\ndomain=theregister\nsuffix=co.uk\nipv4=\nipv6=\n"}
    ]
}
```

---

### Feature 2: Suffix Boundary Rules

**As a developer**, I want to handle inputs at or near suffix boundaries, so I can avoid inventing a registrable domain where none exists.

**Expected Behavior / Usage:**

The input is a host whose labels may be exactly a suffix, sit directly below a multi-label suffix, or end in a label not recognized as any suffix. When the input is itself only a suffix, `fqdn`, `subdomain`, and `domain` are empty while `suffix` carries the full matched suffix. When labels exist below the suffix, the closest label before the suffix becomes the `domain` and any earlier labels become the `subdomain`. When no suffix is recognized at all, `suffix` is empty, `fqdn` is empty, the final label becomes the `domain`, and earlier labels become the `subdomain`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_suffix_boundary_rules.json`

```json
{
    "description": "Handle inputs that sit exactly on or near a suffix boundary: bare suffixes, multi-label suffixes, suffix-only registrations, single-label names below a multi-level suffix, and names with no recognized first-level suffix, without inventing a registrable label that does not exist.",
    "cases": [
        {"input": "com", "expected_output": "fqdn=\nsubdomain=\ndomain=\nsuffix=com\nipv4=\nipv6=\n"},
        {"input": "www.example.ck", "expected_output": "fqdn=www.example.ck\nsubdomain=\ndomain=www\nsuffix=example.ck\nipv4=\nipv6=\n"},
        {"input": "nes.buskerud.no", "expected_output": "fqdn=\nsubdomain=\ndomain=\nsuffix=nes.buskerud.no\nipv4=\nipv6=\n"},
        {"input": "example.co.za", "expected_output": "fqdn=example.co.za\nsubdomain=\ndomain=example\nsuffix=co.za\nipv4=\nipv6=\n"}
    ]
}
```

---

### Feature 3: URL Syntax Normalization

**As a developer**, I want to extract the host from URL-like strings, so I can ignore surrounding scheme, credentials, port, path, query, fragment, and root-label syntax.

**Expected Behavior / Usage:**

The input is a URL-like string that may include an accepted scheme, a scheme-relative `//` prefix, embedded credentials, a port, a path, a query string, a fragment, or a trailing DNS root-label dot (including its full-width and ideographic variants). The parser first identifies the visible host leniently, strips credentials and port, ignores path/query/fragment text, normalizes recognized root-label dot variants to plain dots, and then produces the six-row block. Scheme-like prefixes that do not expose a real host (a lone `//`, a bare `://`, an unrecognized scheme separator, or a fragment/`@` that consumes the host) produce empty components or are treated as ordinary text exactly as the lenient host detection rules dictate.

**Test Cases:** `rcb_tests/public_test_cases/feature3_url_syntax_normalization.json`

```json
{
    "description": "Locate the visible host inside URL-like syntax before extraction: strip accepted scheme and scheme-relative prefixes, drop user credentials and port, ignore path/query/fragment text, and treat malformed scheme-like prefixes as plain text or empty hosts exactly as the lenient host detection rules dictate.",
    "cases": [
        {"input": "a+-.://example.com", "expected_output": "fqdn=example.com\nsubdomain=\ndomain=example\nsuffix=com\nipv4=\nipv6=\n"},
        {"input": "ftp://johndoe:5cr1p7k1dd13@1337.warez.com:2501", "expected_output": "fqdn=1337.warez.com\nsubdomain=1337\ndomain=warez\nsuffix=com\nipv4=\nipv6=\n"},
        {"input": "http://google.com/s?q=cats#Welcome", "expected_output": "fqdn=google.com\nsubdomain=\ndomain=google\nsuffix=com\nipv4=\nipv6=\n"},
        {"input": "http://www.example.com\u3002/", "expected_output": "fqdn=www.example.com\nsubdomain=www\ndomain=example\nsuffix=com\nipv4=\nipv6=\n"}
    ]
}
```

---

### Feature 4: Unrecognized and Local Names

**As a developer**, I want to handle local or unknown-suffix names, so I can still receive deterministic component fields.

**Expected Behavior / Usage:**

The input is a single-label local name, a host whose final label is not a recognized suffix, or an odd string containing unusual characters or embedded line separators. When no suffix is recognized, `suffix` and `fqdn` are empty, the last label becomes the `domain`, and earlier labels become the `subdomain`. Inputs are never rejected merely for containing unusual characters; the raw label text (including any embedded line separator) is preserved verbatim in the output fields.

**Test Cases:** `rcb_tests/public_test_cases/feature4_unrecognized_and_local_names.json`

```json
{
    "description": "Return deterministic components for single-label local names, host names whose final label is not a recognized public suffix, and odd inputs containing unusual characters or embedded line separators; when no suffix is recognized the suffix and fully qualified host stay empty, the last label becomes the domain, and earlier labels become the subdomain.",
    "cases": [
        {"input": "http://internalunlikelyhostname/", "expected_output": "fqdn=\nsubdomain=\ndomain=internalunlikelyhostname\nsuffix=\nipv4=\nipv6=\n"},
        {"input": "http://internalunlikelyhostname.bizarre", "expected_output": "fqdn=\nsubdomain=internalunlikelyhostname\ndomain=bizarre\nsuffix=\nipv4=\nipv6=\n"},
        {"input": "http://internalunlikelyhostname.info/", "expected_output": "fqdn=internalunlikelyhostname.info\nsubdomain=\ndomain=internalunlikelyhostname\nsuffix=info\nipv4=\nipv6=\n"},
        {"input": "1.1.1.1\ncom", "expected_output": "fqdn=\nsubdomain=1.1.1\ndomain=1\ncom\nsuffix=\nipv4=\nipv6=\n"}
    ]
}
```

---

### Feature 5: IP Address Handling

**As a developer**, I want to classify address literals separately from domain names, so I can distinguish real IP hosts from lookalike labels.

**Expected Behavior / Usage:**

The input is a URL-like string whose host may be a complete dotted-quad IPv4 address, a bracketed IPv6 address, or an address lookalike. A valid IPv4 host (after normalizing Unicode dot separators) yields empty `fqdn`/`subdomain`/`suffix`, a `domain` equal to the normalized address text, an `ipv4` equal to that address, and empty `ipv6`. A valid bracketed IPv6 host yields a `domain` equal to the bracketed text and an `ipv6` equal to the unbracketed address. Address-like but invalid hosts (over-range octets, too few or too many labels, hex octets, a trailing extra octet) are returned as ordinary domain labels with both IP fields empty.

**Test Cases:** `rcb_tests/public_test_cases/feature5_ip_address_handling.json`

```json
{
    "description": "Classify the host as an address literal when it is a complete dotted-quad IPv4 address (after normalizing Unicode dot separators) or a bracketed IPv6 address, populating the ipv4 or ipv6 field and leaving suffix empty; address-like but invalid hosts (over-range octets, wrong label count, hex octets) remain ordinary domain labels with both IP fields empty.",
    "cases": [
        {"input": "http://216.22.0.192/", "expected_output": "fqdn=\nsubdomain=\ndomain=216.22.0.192\nsuffix=\nipv4=216.22.0.192\nipv6=\n"},
        {"input": "https://apple:pass@[::]:50/a", "expected_output": "fqdn=\nsubdomain=\ndomain=[::]\nsuffix=\nipv4=\nipv6=::\n"},
        {"input": "http://127\u30020\uff0e0\uff611/foo/bar", "expected_output": "fqdn=\nsubdomain=\ndomain=127.0.0.1\nsuffix=\nipv4=127.0.0.1\nipv6=\n"},
        {"input": "http://256.256.256.256/foo/bar", "expected_output": "fqdn=\nsubdomain=256.256.256\ndomain=256\nsuffix=\nipv4=\nipv6=\n"},
        {"input": "http://127.0.0.1.9/foo/bar", "expected_output": "fqdn=\nsubdomain=127.0.0.1\ndomain=9\nsuffix=\nipv4=\nipv6=\n"}
    ]
}
```

---

### Feature 6: Internationalized Label Handling

**As a developer**, I want to support internationalized and punycode labels, so I can match suffixes correctly without changing visible labels.

**Expected Behavior / Usage:**

The input is a host containing punycode (`xn--`) labels, Unicode labels, Unicode dot separators, or malformed punycode. Suffix matching uses Unicode-aware, case-insensitive label comparison: a punycode label is compared by its decoded form, the `xn--` prefix is matched case-insensitively, and labels whose punycode is invalid are tolerated and matched literally rather than causing a failure. The returned `fqdn`, `subdomain`, `domain`, and `suffix` preserve the original visible label text (after URL host normalization), not a re-encoded Unicode or ASCII form.

**Test Cases:** `rcb_tests/public_test_cases/feature6_internationalized_label_handling.json`

```json
{
    "description": "Match suffixes using Unicode-aware, case-insensitive comparison of punycode and Unicode labels, tolerating malformed punycode labels without failing, while preserving the original visible label text (not a re-encoded form) in the returned host fields.",
    "cases": [
        {"input": "http://xn--h1alffa9f.xn--p1ai", "expected_output": "fqdn=xn--h1alffa9f.xn--p1ai\nsubdomain=\ndomain=xn--h1alffa9f\nsuffix=xn--p1ai\nipv4=\nipv6=\n"},
        {"input": "http://xn--zckzap6140b352by.blog.so-net.xn--wcvs22d.hk", "expected_output": "fqdn=xn--zckzap6140b352by.blog.so-net.xn--wcvs22d.hk\nsubdomain=xn--zckzap6140b352by.blog\ndomain=so-net\nsuffix=xn--wcvs22d.hk\nipv4=\nipv6=\n"},
        {"input": "http://xn--zckzap6140b352by.blog.so-net.\u6559\u80b2.hk", "expected_output": "fqdn=xn--zckzap6140b352by.blog.so-net.\u6559\u80b2.hk\nsubdomain=xn--zckzap6140b352by.blog\ndomain=so-net\nsuffix=\u6559\u80b2.hk\nipv4=\nipv6=\n"},
        {"input": "angelinablog\u3002com.de", "expected_output": "fqdn=angelinablog.com.de\nsubdomain=angelinablog\ndomain=com\nsuffix=de\nipv4=\nipv6=\n"}
    ]
}
```

---

### Feature 7: Private Suffix Policy

**As a developer**, I want to choose whether privately managed suffix entries count as suffixes, so I can apply the same parser under either suffix policy.

**Expected Behavior / Usage:**

The input is either a bare URL string (default policy) or an object with `url` and an optional boolean `include_private_suffixes`. Privately managed suffix entries are delegated subdomains operated as registries. When `include_private_suffixes` is false or omitted, those entries are treated as ordinary labels. When true, the suffix may consume the additional private labels. When a private registration occupies every available label with no registrable label below it, the registrable `domain` and `fqdn` are empty while `suffix` carries the whole private suffix. The output is the six-row block so a caller can compare the effect of the policy on identical host inputs.

**Test Cases:** `rcb_tests/public_test_cases/feature7_private_suffix_policy.json`

```json
{
    "description": "Choose whether privately managed suffix entries (delegated subdomains operated as registries) are treated as part of the suffix or as ordinary labels. With the private-suffix policy disabled (default) such entries are plain labels; enabling it lets the suffix consume more labels, and over-long private registrations with no label below them yield an empty registrable domain.",
    "cases": [
        {"input": "http://waiterrant.blogspot.com", "expected_output": "fqdn=waiterrant.blogspot.com\nsubdomain=waiterrant\ndomain=blogspot\nsuffix=com\nipv4=\nipv6=\n"},
        {"input": {"url": "foo.uk.com", "include_private_suffixes": true}, "expected_output": "fqdn=foo.uk.com\nsubdomain=\ndomain=foo\nsuffix=uk.com\nipv4=\nipv6=\n"},
        {"input": {"url": "foo.uk.com", "include_private_suffixes": false}, "expected_output": "fqdn=foo.uk.com\nsubdomain=foo\ndomain=uk\nsuffix=com\nipv4=\nipv6=\n"},
        {"input": {"url": "s3.ap-south-1.amazonaws.com", "include_private_suffixes": true}, "expected_output": "fqdn=\nsubdomain=\ndomain=\nsuffix=s3.ap-south-1.amazonaws.com\nipv4=\nipv6=\n"},
        {"input": {"url": "the-quick-brown-fox.cn-north-1.amazonaws.com.cn", "include_private_suffixes": true}, "expected_output": "fqdn=the-quick-brown-fox.cn-north-1.amazonaws.com.cn\nsubdomain=the-quick-brown-fox.cn-north-1\ndomain=amazonaws\nsuffix=com.cn\nipv4=\nipv6=\n"}
    ]
}
```

---

### Feature 8: Custom Suffix List

**As a developer**, I want to supply my own suffix list, so I can parse hosts against a private or test-specific set of suffixes instead of the built-in data.

**Expected Behavior / Usage:**

The input is an object with a `suffix_list` array of suffix entries plus the `url` to parse. Only the listed entries count as suffixes, replacing the built-in data entirely. Wildcard entries of the form `*.<label>` match any single label in that position and therefore consume one extra label as part of the suffix. A host whose final label is not present in the custom list resolves to an empty `suffix` (so `fqdn` is empty and the final label becomes the `domain`). The output is the six-row block.

**Test Cases:** `rcb_tests/public_test_cases/feature8_custom_suffix_list.json`

```json
{
    "description": "Supply a caller-provided suffix list instead of the built-in data, so that only the listed entries (including wildcard rules) count as suffixes. Inputs carry the custom suffix entries plus the host to parse; hosts whose final label is not in the custom list resolve to an empty suffix, and wildcard entries consume one extra label.",
    "cases": [
        {"input": {"suffix_list": ["foo", "bar", "baz", "*.co.jp"], "url": "www.google.com"}, "expected_output": "fqdn=\nsubdomain=www.google\ndomain=com\nsuffix=\nipv4=\nipv6=\n"},
        {"input": {"suffix_list": ["foo", "bar", "baz", "*.co.jp"], "url": "www.foo.bar.baz.quux.foo"}, "expected_output": "fqdn=www.foo.bar.baz.quux.foo\nsubdomain=www.foo.bar.baz\ndomain=quux\nsuffix=foo\nipv4=\nipv6=\n"},
        {"input": {"suffix_list": ["foo", "bar", "baz", "*.co.jp"], "url": "a.b.co.jp"}, "expected_output": "fqdn=a.b.co.jp\nsubdomain=\ndomain=a\nsuffix=b.co.jp\nipv4=\nipv6=\n"}
    ]
}
```

---

### Feature 9: Additional Suffixes

**As a developer**, I want to add extra suffix entries on top of an existing suffix list, so I can recognize a few private suffixes without replacing the whole list.

**Expected Behavior / Usage:**

The input is an object carrying the active suffix list, an `extra_suffixes` array of additional entries to recognize, and the `url` to parse. The extra entries become recognized suffixes in addition to the entries from the configured list, rather than replacing them. A host ending in an extra entry resolves its `suffix` to that entry; a host not covered by either the configured list or the extra entries resolves to an empty `suffix`. The output is the six-row block.

**Test Cases:** `rcb_tests/public_test_cases/feature9_extra_suffixes.json`

```json
{
    "description": "Augment the active suffix list with caller-provided extra suffix entries without replacing the configured list. The extra entries become recognized suffixes in addition to whatever the base list already provides; hosts ending in an extra entry resolve their suffix to that entry, while hosts not covered by either source resolve to an empty suffix.",
    "cases": [
        {"input": {"suffix_list": ["foo", "bar", "baz", "*.co.jp"], "extra_suffixes": ["foo1", "bar1", "baz1"], "url": "www.google.com"}, "expected_output": "fqdn=\nsubdomain=www.google\ndomain=com\nsuffix=\nipv4=\nipv6=\n"},
        {"input": {"suffix_list": ["foo", "bar", "baz", "*.co.jp"], "extra_suffixes": ["foo1", "bar1", "baz1"], "url": "www.foo.bar.baz.quux.foo1"}, "expected_output": "fqdn=www.foo.bar.baz.quux.foo1\nsubdomain=www.foo.bar.baz\ndomain=quux\nsuffix=foo1\nipv4=\nipv6=\n"}
    ]
}
```

---

### Feature 10: Batch Component Formatting

**As a developer**, I want to format a batch of hosts into space-joined component lines, so I can pipe many hosts through one call and read a compact line-per-host result.

**Expected Behavior / Usage:**

The input is an object with a `urls` array. For each host the output is one line consisting of the `subdomain`, `domain`, and `suffix` joined by single spaces in that order, followed by a newline. Empty components render as empty fields, so a missing subdomain produces a leading space and a missing suffix produces a trailing-field gap; the spacing is fixed (always two separators) regardless of which components are present. Lines are emitted in input order.

**Test Cases:** `rcb_tests/public_test_cases/feature10_batch_component_formatting.json`

```json
{
    "description": "Process a batch of host inputs and emit one line per input. Each line is the subdomain, domain, and suffix joined by single spaces in that order (empty components render as empty fields, so leading/extra spaces appear when a component is absent), and each line is terminated by a newline.",
    "cases": [
        {"input": {"urls": ["example.com", "bbc.co.uk", "forums.bbc.co.uk"]}, "expected_output": [a specific expected whitespace and delimiter format — verify with the batch integration docs]\n bbc co.uk\nforums bbc co.uk\n"},
        {"input": {"urls": ["www.google.com"]}, "expected_output": [a specific expected whitespace and delimiter format — verify with the batch integration docs]\n"}
    ]
}
```

---

### Feature 11: Data Source Configuration

**As a developer**, I want the extractor to validate its configured suffix-data sources, so I get a clear, deterministic error when no data source is available instead of a silent or generic failure.

**Expected Behavior / Usage:**

The input is an object with a `data_sources` object whose booleans select where suffix data may come from: a local `cache` directory, a `remote_list`, and/or a `bundled_snapshot`, plus a `url` to parse. If every source is disabled, construction is rejected and the output is the single neutral line `error=no_data_sources` followed by a newline. If at least one source is enabled (for example the bundled snapshot), extraction proceeds and produces the normal six-row block. Errors are reported as a neutral category line and never expose host-language exception types or runtime message text.

**Test Cases:** `rcb_tests/public_test_cases/feature11_data_source_configuration.json`

```json
{
    "description": "Validate the configured data sources before extracting. The extractor may draw suffix data from a local cache directory, a remote list, or a bundled snapshot. If a configuration disables every possible source, construction is rejected with a neutral no_data_sources error category; if at least one source (such as the bundled snapshot) is enabled, extraction proceeds normally.",
    "cases": [
        {"input": {"data_sources": {"cache": false, "remote_list": false, "bundled_snapshot": false}, "url": "www.google.com"}, "expected_output": [the exact JSON error string for empty data sources — check the error schema configuration]},
        {"input": {"data_sources": {"cache": false, "remote_list": false, "bundled_snapshot": true}, "url": "www.google.com"}, "expected_output": "fqdn=www.google.com\nsubdomain=www\ndomain=google\nsuffix=com\nipv4=\nipv6=\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain. It is also responsible for translating any native runtime error into the neutral error-category lines specified above.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_registered_domain_extraction.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_registered_domain_extraction@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the private registry consume-all-labels behavior
- apply the longest-chain suffix matching logic
