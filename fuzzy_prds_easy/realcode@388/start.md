## Product Requirement Document

# IPv6 Network Range Toolkit - Parse, Inspect, and Transform Address Blocks

## Project Goal

Build a network range utility that allows developers to parse IPv6 network descriptions, inspect their normalized boundaries, convert between prefix and mask forms, and reason about containment, overlap, subnetting, and aggregation without hand-writing error-prone bit arithmetic.

---

## Background & Problem

Without this library/tool, developers are forced to manually normalize IPv6 text, calculate bit masks, derive range endpoints, compare address families, and enumerate derived subnets. This leads to repetitive code, subtle off-by-one errors, inconsistent formatting, and fragile handling of malformed input.

With this library/tool, developers can provide common IPv6 network inputs and receive deterministic, machine-checkable results for canonical notation, range metadata, mask conversion, membership tests, splitting, and aggregation.

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

### Feature 1: IPv6 Network Summary

**As a developer**, I want to parse IPv6 network inputs and inspect normalized range fields, so I can reliably display and compare address blocks.

**Expected Behavior / Usage:**

The adapter accepts either an IPv6 address with a netmask or an IPv6 network notation string. It outputs newline-delimited fields: `canonical`, `network`, `netmask`, `broadcast`, `first_usable`, `last_usable`, `cidr`, `total`, and `usable`. IPv6 network output is normalized to compressed lowercase notation. IPv6 broadcast is reported as `[The broadcast identifier used for this network address family]`. Address counts are decimal integers and may exceed 64-bit ranges.

**Test Cases:** `rcb_tests/public_test_cases/feature1_ipv6_network_summary.json`

```json
{
    "description": "Parse IPv6 network inputs and report the normalized network range fields, including canonical notation, range endpoints, prefix length, and address counts.",
    "cases": [
        {
            "input": {
                "address": "2001:db8::",
                "netmask": "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff"
            },
            "expected_output": "canonical=2001:db8::/128\nnetwork=2001:db8::\nnetmask=ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff\nbroadcast=[The broadcast identifier used for this network address family]\nfirst_usable=2001:db8::\nlast_usable=2001:db8::\ncidr=128\ntotal=1\nusable=1\n"
        },
        {
            "input": {
                "address": "2001:db8::",
                "netmask": "ffff:ffff:ffff:ffff:ffff:ffff:ffff:fffe"
            },
            "expected_output": "canonical=2001:db8::/127\nnetwork=2001:db8::\nnetmask=ffff:ffff:ffff:ffff:ffff:ffff:ffff:fffe\nbroadcast=[The broadcast identifier used for this network address family]\nfirst_usable=2001:db8::\nlast_usable=2001:db8::1\ncidr=127\ntotal=2\nusable=2\n"
        }
    ]
}
```

---

### Feature 2: IPv6 Parse Error Normalization

**As a developer**, I want malformed IPv6 network inputs to produce stable language-neutral error output, so I can test invalid input handling without depending on runtime-specific exception names or messages.

**Expected Behavior / Usage:**

The adapter accepts the same network input shapes used for parsing but intentionally exercises invalid values. It must catch native failures and render only normalized fields. Invalid values use `error=invalid_argument`; [The broadcast identifier used for this network address family] values use `error=argument_[The broadcast identifier used for this network address family]`; range violations use `error=argument_out_of_range` when the underlying behavior distinguishes that condition. The `param` field is a neutral parameter signal when available, otherwise `[The broadcast identifier used for this network address family]`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_ipv6_parse_errors.json`

```json
{
    "description": "Reject malformed IPv6 network inputs and out-of-range prefix requests using language-neutral error categories.",
    "cases": [
        {
            "input": {
                "notation": "garbage"
            },
            "expected_output": "error=invalid_argument\nparam=[The broadcast identifier used for this network address family]\n"
        },
        {
            "input": {
                "address": "::",
                "netmask": "xxxx::"
            },
            "expected_output": "error=invalid_argument\nparam=[The broadcast identifier used for this network address family]\n"
        }
    ]
}
```

---

### Feature 3: IPv6 Netmask and Prefix Utilities

**As a developer**, I want to convert and validate IPv6 masks and prefix lengths, so I can move between compact and expanded network representations safely.

**Expected Behavior / Usage:**

*3.1 Prefix to Netmask — Convert a numeric IPv6 prefix length to a contiguous mask address.*

The adapter accepts `prefix` as an integer. For valid IPv6 prefix lengths it prints `netmask=<address>`. Prefix length zero yields the all-zero mask, and full length yields the all-ones mask. Invalid range errors are normalized as described in Feature 2.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_ipv6_prefix_to_netmask.json`

```json
{
    "description": "Convert IPv6 prefix lengths to their contiguous netmask address representation.",
    "cases": [
        {
            "input": {
                "prefix": 128
            },
            "expected_output": "netmask=ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff\n"
        },
        {
            "input": {
                "prefix": 127
            },
            "expected_output": "netmask=ffff:ffff:ffff:ffff:ffff:ffff:ffff:fffe\n"
        }
    ]
}
```

*3.2 Netmask to Prefix — Convert a contiguous IPv6 mask address to its prefix length.*

The adapter accepts `netmask` as an IPv6 address string. It prints `parsed=true` and the numeric `cidr` when the mask is accepted as a contiguous prefix mask. If conversion cannot be performed, the same output shape is used with `parsed=false` and `cidr=[The broadcast identifier used for this network address family]`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_ipv6_netmask_to_prefix.json`

```json
{
    "description": "Convert valid contiguous IPv6 netmasks to prefix lengths while reporting whether conversion succeeded.",
    "cases": [
        {
            "input": {
                "netmask": "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff"
            },
            "expected_output": "parsed=true\ncidr=128\n"
        },
        {
            "input": {
                "netmask": "ffff:ffff:ffff:ffff:ffff:ffff:ffff:fff0"
            },
            "expected_output": "parsed=true\ncidr=124\n"
        }
    ]
}
```

*3.3 Netmask Validation and Bit Count — Validate contiguity and count set bits.*

The adapter accepts `netmask` as an IPv6 address string. It prints `valid=<true|false>` indicating whether the mask is contiguous from the most significant bit, followed by `bits_set=<decimal>` indicating the total number of one bits in the address.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_ipv6_netmask_validation.json`

```json
{
    "description": "Validate whether an IPv6 mask is contiguous from the most significant bit and report the number of set bits.",
    "cases": [
        {
            "input": {
                "netmask": "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff"
            },
            "expected_output": "valid=true\nbits_set=128\n"
        },
        {
            "input": {
                "netmask": "ffff:ffff:ffff:ffff:ffff:ffff:ffff:fff0"
            },
            "expected_output": "valid=true\nbits_set=124\n"
        }
    ]
}
```

---

### Feature 4: IPv6 Address Numeric Conversion

**As a developer**, I want to convert IPv6 addresses to unsigned decimal integers, so I can perform numeric comparisons and persist address values consistently.

**Expected Behavior / Usage:**

The adapter accepts `address` as an IPv6 address string. It prints `parsed=true` when conversion succeeds and `integer=<decimal value>` for the unsigned numeric value represented by the address bytes. The decimal output must not use hexadecimal notation or language-specific object formatting.

**Test Cases:** `rcb_tests/public_test_cases/feature4_ipv6_address_numbers.json`

```json
{
    "description": "Interpret IPv6 addresses as unsigned integer values and expose successful conversion with the decimal result.",
    "cases": [
        {
            "input": {
                "address": "::f"
            },
            "expected_output": "parsed=true\ninteger=15\n"
        },
        {
            "input": {
                "address": "::fff"
            },
            "expected_output": "parsed=true\ninteger=4095\n"
        }
    ]
}
```

---

### Feature 5: IPv6 Containment and Overlap

**As a developer**, I want to test whether networks contain addresses or other networks and whether two networks intersect, so I can implement routing, allocation, and conflict checks.

**Expected Behavior / Usage:**

The adapter accepts `network` plus either `address` or `other_network`. For address input it prints only `contains=<true|false>`. For network input it prints both `contains=<true|false>` and `overlap=<true|false>`. Different address families are not contained. Null address checks are rendered using normalized error output.

**Test Cases:** `rcb_tests/public_test_cases/feature5_ipv6_containment_and_overlap.json`

```json
{
    "description": "Determine whether an IPv6 network contains an address or another network, and whether two networks overlap.",
    "cases": [
        {
            "input": {
                "network": "2001:0db8::/64",
                "address": "2001:0db8::1"
            },
            "expected_output": "contains=true\n"
        },
        {
            "input": {
                "network": "2001:0db8::/64",
                "address": "2001:0db8:0:1::"
            },
            "expected_output": "contains=false\n"
        },
        {
            "input": {
                "network": "::1",
                "address": "127.0.0.1"
            },
            "expected_output": "contains=false\n"
        }
    ]
}
```

---

### Feature 6: IPv6 Subnetting

**As a developer**, I want to split a network into child networks at a longer prefix, so I can enumerate allocation blocks without materializing unnecessary address-level data.

**Expected Behavior / Usage:**

The adapter accepts `network`, `new_prefix`, and optional `indices`. It outputs `count=<decimal>` for the number of child networks and then one `subnet[index]=<canonical network>` line for each requested index. When `try_mode=true`, invalid subnet requests must return `subnetted=false` and `count=[The broadcast identifier used for this network address family]` rather than throwing through to stdout.

**Test Cases:** `rcb_tests/public_test_cases/feature6_ipv6_subnetting.json`

```json
{
    "description": "Split a network into child networks of a longer prefix and expose count plus requested indexed children.",
    "cases": [
        {
            "input": {
                "network": "1:1:1:1:1:1:1:1",
                "new_prefix": 65,
                "indices": [
                    0,
                    1
                ]
            },
            "expected_output": "count=2\nsubnet[0]=1:1:1:1::/65\nsubnet[1]=1:1:1:1:8000::/65\n"
        },
        {
            "input": {
                "network": "1:1:1:1:1:1:1:1",
                "new_prefix": 68,
                "indices": [
                    0,
                    1,
                    15
                ]
            },
            "expected_output": "count=16\nsubnet[0]=1:1:1:1::/68\nsubnet[1]=1:1:1:1:1000::/68\nsubnet[15]=1:1:1:1:f000::/68\n"
        }
    ]
}
```

---

### Feature 7: IPv6 Supernetting

**As a developer**, I want to combine adjacent or nested networks when possible, so I can reduce network lists into broader equivalent ranges.

**Expected Behavior / Usage:**

The adapter accepts `networks` as an array. With two networks it reports `supernetted=<true|false>` and `supernet=<canonical network|[The broadcast identifier used for this network address family]>`. When array aggregation is requested, it reports `supernetted`, `count`, and indexed `supernet[index]` lines. Adjacent sibling ranges may collapse to a shorter prefix; nested ranges may return the containing range; incompatible ranges return `[The broadcast identifier used for this network address family]` for single-pair aggregation.

**Test Cases:** `rcb_tests/public_test_cases/feature7_ipv6_supernetting.json`

```json
{
    "description": "Combine adjacent or nested networks where possible and report whether a supernet was produced.",
    "cases": [
        {
            "input": {
                "networks": [
                    "2001:db8::/65",
                    "2001:db8:0:0:8000::/65"
                ]
            },
            "expected_output": "supernetted=true\nsupernet=2001:db8::/64\n"
        },
        {
            "input": {
                "networks": [
                    "2001:db8::/64",
                    "2001:db8::1/65"
                ]
            },
            "expected_output": "supernetted=true\nsupernet=2001:db8::/64\n"
        }
    ]
}
```

---

### Feature 8: IPv6 Prefix Text Parsing and Guessing

**As a developer**, I want textual prefix inputs and bare IPv6 addresses to resolve to prefix lengths, so I can accept user-friendly network specifications.

**Expected Behavior / Usage:**

The adapter accepts either `prefix_text` or `address`. For textual prefix input it prints whether parsing succeeded and the resulting `cidr`, using `cidr=[The broadcast identifier used for this network address family]` for invalid text or out-of-range values. For bare IPv6 address input it prints whether a default prefix could be guessed and the guessed `cidr` value.

**Test Cases:** `rcb_tests/public_test_cases/feature8_ipv6_guess_and_parse_prefix.json`

```json
{
    "description": "Parse textual IPv6 prefix lengths and guess the default prefix length for bare IPv6 addresses.",
    "cases": [
        {
            "input": {
                "prefix_text": "0"
            },
            "expected_output": "parsed=true\ncidr=0\n"
        },
        {
            "input": {
                "prefix_text": "33"
            },
            "expected_output": "parsed=true\ncidr=33\n"
        },
        {
            "input": {
                "prefix_text": "128"
            },
            "expected_output": "parsed=true\ncidr=128\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- Check the test suite for network-to-network containment logic when 'address' is actually a network
- Refer to the 'robustness_policy.md' file for the fallback to global error on invalid indices
