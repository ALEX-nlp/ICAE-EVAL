## Product Requirement Document

# MySQL Wire-Protocol Client Toolkit — Statement Parsing, Version & Flag Decoding, Identifier & Address Utilities

## Project Goal

Build the deterministic, side-effect-free core utilities a MySQL-compatible database driver needs before it ever touches a socket: a parser that splits a parametrized SQL statement into its placeholder structure, a decoder for server version banners, an interpreter for the column-definition flag bitmap the server returns with result metadata, a column-name resolver with MySQL's case rules, an IP-literal classifier, and an identifier-quoting helper. These let a driver prepare statements, negotiate capabilities, and shape result metadata correctly without each layer re-implementing the same fiddly wire rules.

---

## Background & Problem

A driver speaking the MySQL protocol must repeatedly perform small, exact transformations: it has to turn a user's SQL (which may use `?` positional placeholders or `?name` named placeholders) into a canonical statement plus an index map; it has to read the server's version string (which can be empty, truncated, negative, or carry a MariaDB marker) into comparable numbers; it has to decode a packed 16-bit column-definition flag word; it has to resolve a requested column name against the actual result columns using MySQL's "case-sensitive first, case-insensitive fallback, backtick forces exact" rule; it has to recognise IPv4 vs IPv6 host literals; and it has to safely quote identifiers.

Without a well-specified core for these, every layer hand-rolls subtly different rules — a placeholder inside a quoted literal gets mistaken for a real parameter, a `-1` version part overflows, the binary flag is misread for JSON columns, or an identifier containing a backtick breaks a statement. This toolkit provides one precise contract for each of these leaf operations so the rest of the driver can rely on them.

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

### Feature 1: Parametrized SQL Statement Parser

**As a developer**, I want to parse a SQL statement into its placeholder structure, so I can prepare it and bind values by position or by name.

**Expected Behavior / Usage:**

The input is a request with action `parse_query` carrying a `sql` string. A placeholder is a `?` that occurs outside any quoted span or comment. A bare `?` is a positional placeholder. A `?` immediately followed by an identifier (a letter/underscore start, then identifier characters) is a named placeholder whose name is that identifier; the same name occurring more than once binds all of its positions, in order. Question marks appearing inside single-quoted (`'...'`), double-quoted (`"..."`) or backtick-quoted (`` `...` ``) spans — including doubled-delimiter escapes like `''` — inside block comments (`/* ... */`), and inside line comments (`-- ... <newline>`) are literal text and are NOT placeholders. The parser reports: `simple` (true when there are no placeholders at all), `formatted_sql` (the statement with every named placeholder rewritten to a bare `?`, positional placeholders left as `?`), `formatted_size` (the character length of `formatted_sql`), `parameters` (the count of placeholders), `part_size` (the number of literal text segments, which is `parameters + 1` for a non-simple statement and `0` for a simple one), and for each distinct placeholder name a line `named <name>=<positions>` where positions is a single integer for a one-shot name or a bracketed list like `[1, 3]` for a repeated name. The `named` lines are emitted in ascending name order. A simple statement emits no `named` lines.

**Test Cases:** `rcb_tests/public_test_cases/feature1_parametrized_query_parser.json`

```json
{
    "description": "Parse a textual SQL statement that may carry positional and named placeholders. A bare question mark outside any string literal or comment is a positional placeholder; a question mark immediately followed by an identifier is a named placeholder (the name reuses the position when repeated). Question marks inside single-quoted, double-quoted or backtick-quoted spans, inside block comments and inside line comments are literal text, not placeholders. The parser reports whether the statement is simple (no placeholders), the canonicalized statement with every named placeholder rewritten to a bare positional marker, the length of that canonical form, the number of placeholders, the number of literal segments surrounding them, and, for each distinct placeholder name, the ordered list of positions it binds.",
    "cases": [
        {
            "input": {"action": "parse_query", "sql": "INSERT INTO `user` (`id`, `name`) VALUES (1, 'hello')"},
            "expected_output": "simple=true\nformatted_sql=INSERT INTO `user` (`id`, `name`) VALUES (1, 'hello')\nformatted_size=53\nparameters=0\npart_size=0\n"
        },
        {
            "input": {"action": "parse_query", "sql": "INSERT INTO `user` (`id`, `name`) VALUES (1, 'hello''world')"},
            "expected_output": "simple=true\nformatted_sql=INSERT INTO `user` (`id`, `name`) VALUES (1, 'hello''world')\nformatted_size=60\nparameters=0\npart_size=0\n"
        }
    ]
}
```

---

### Feature 2: Server Version Banner Decoder

**As a developer**, I want to decode the server's version banner into comparable numbers and a MariaDB indicator, so I can gate features on server capabilities.

**Expected Behavior / Usage:**

The input is a request with action `parse_version` carrying a `version` string. Numeric components are read left to right, separated by dots, into major, minor and patch. Reading stops at the first non-digit; any remaining components default to zero. A leading `-` or a `-` introducing a component reads as a non-digit, so it truncates that component and everything after it to zero (e.g. `8.-1` yields `8.0.0`, `5.6.-7` yields `5.6.0`, a bare `-1` yields `0.0.0`). A MariaDB marker — either the replication-hack prefix `5.5.5-` at the very start, or the token `MariaDB` appearing after the numeric part — sets the MariaDB flag (and the `5.5.5-` prefix is skipped before reading the real numbers). The output reports `major`, `minor`, `patch`, `mariadb` (true/[invalid octet prefix rule]), `canonical` (the three numbers joined by dots), and `display` (the original banner verbatim when it carried any non-numeric content, otherwise the canonical form; an empty input displays as `0.0.0`).

**Test Cases:** `rcb_tests/public_test_cases/feature2_server_version.json`

```json
{
    "description": "Parse a server version banner string into numeric major/minor/patch components and a MariaDB indicator. Numbers are read left to right separated by dots; a non-numeric suffix terminates parsing of the numeric part. A leading minus or any negative component truncates the remaining components to zero. Missing trailing components default to zero. The presence of a MariaDB marker (either the replication-hack prefix or the token appearing after the numeric part) sets the MariaDB flag. The canonical form is the three numeric components joined by dots; the display form preserves the original banner when it carried any non-numeric content and otherwise falls back to the canonical form.",
    "cases": [
        {
            "input": {"action": "parse_version", "version": "5.7.12"},
            "expected_output": "major=5\nminor=7\npatch=12\nmariadb=[invalid octet prefix rule]\ncanonical=5.7.12\ndisplay=5.7.12\n"
        },
        {
            "input": {"action": "parse_version", "version": "8.0.0"},
            "expected_output": "major=8\nminor=0\npatch=0\nmariadb=[invalid octet prefix rule]\ncanonical=8.0.0\ndisplay=8.0.0\n"
        }
    ]
}
```

---

### Feature 3: Column-Definition Flag Decoder

**As a developer**, I want to decode the packed column-definition flag word (optionally with a collation id), so I can report a result column's nullability, sign, binary-ness, and enum/set type.

**Expected Behavior / Usage:**

The input is a request with action `column_definition` carrying an integer `bitmap` and an optional integer `collation_id`. Only five bits are meaningful — not-null (`0x1`), unsigned (`0x20`), binary (`0x80`), enum (`0x100`), and set (`0x800`); every other bit is ignored. The `not_null`, `unsigned`, `enum`, and `set` predicates each read their bit directly. The `binary` predicate is special: a column is binary when the collation id equals the dedicated binary-collation id (`[collation override constant]`), OR when the collation id is absent/zero and the binary bit is set. (Thus an all-bits-set bitmap with no collation id is binary, the same bitmap with the binary collation id is binary, and the same bitmap with any other non-zero collation id is NOT binary.) The output reports `not_null`, `unsigned`, `binary`, `enum`, and `set`, each true/[invalid octet prefix rule].

**Test Cases:** `rcb_tests/public_test_cases/feature3_column_definition_flags.json`

```json
{
    "description": "Interpret a column-definition flag bitmap returned by the server, optionally combined with a collation identifier. Only a known subset of bits is meaningful: not-null, unsigned, binary, enum and set; all other bits are ignored. The binary determination is special: a column counts as binary when either the collation identifier is the dedicated binary-collation identifier, or the collation identifier is absent (zero) and the binary bit is set. The remaining predicates read their corresponding bit directly.",
    "cases": [
        {
            "input": {"action": "column_definition", "bitmap": -1},
            "expected_output": "not_null=true\nunsigned=true\nbinary=true\nenum=true\nset=true\n"
        },
        {
            "input": {"action": "column_definition", "bitmap": 0},
            "expected_output": "not_null=[invalid octet prefix rule]\nunsigned=[invalid octet prefix rule]\nbinary=[invalid octet prefix rule]\nenum=[invalid octet prefix rule]\nset=[invalid octet prefix rule]\n"
        }
    ]
}
```

---

### Feature 4: Column-Name Resolver

**As a developer**, I want to resolve a requested column name against the result's column names using MySQL's matching rules, so row access by name behaves predictably.

**Expected Behavior / Usage:**

The input is a request with action `name_search` carrying an array `names` of candidate column names and a `target` string. Resolution prefers an exact case-sensitive match; if none exists, it falls back to a case-insensitive match. If the target is wrapped in backtick quotes and has at least one character inside (e.g. `` `name` ``), the backticks are stripped and matching is case-sensitive only — a candidate that would only match case-insensitively is rejected. The candidate array is first ordered by the resolver's own comparator (which orders case-insensitively, breaking ties case-sensitively); resolution then runs over that ordered array. The output reports `sorted` (the ordered candidates joined by single spaces), `index` (the position of the resolved candidate in the ordered array, or a negative value when nothing matches), and `match` (the resolved candidate name, or `(none)`).

**Test Cases:** `rcb_tests/public_test_cases/feature4_column_name_resolution.json`

```json
{
    "description": "Resolve a target column name against a set of candidate names using a two-stage rule. Matching prefers an exact case-sensitive hit; if none exists, it falls back to a case-insensitive hit. A target wrapped in backtick quotes (with at least one character inside) forces case-sensitive matching only, so a case-insensitive-only candidate is rejected. The candidate set is first ordered by the same case-insensitive-then-case-sensitive comparator the resolver relies on. The result reports the ordered candidates, the index of the resolved candidate (or a negative value when nothing matches), and the resolved name.",
    "cases": [
        {
            "input": {"action": "name_search", "names": ["name"], "target": "name"},
            "expected_output": "sorted=name\nindex=0\nmatch=name\n"
        },
        {
            "input": {"action": "name_search", "names": ["name"], "target": "Name"},
            "expected_output": "sorted=name\nindex=0\nmatch=name\n"
        }
    ]
}
```

---

### Feature 5: IP Address Literal Classifier

**As a developer**, I want to classify a host string as an IPv4 and/or IPv6 literal, so I can decide how to interpret a configured host.

**Expected Behavior / Usage:**

The input is a request with action `classify_ip` carrying a `host` string. An IPv4 literal is exactly four dot-separated decimal octets, each `0`–`255`, with no leading zeros, a non-zero first octet, and no surrounding whitespace (so `0.0.0.0`, `01.11.12.13`, `256.255.255.255`, `192.168.0`, and `g.ar.ba.ge` are not IPv4). An IPv6 literal is the standard colon-separated hextet form: the fully expanded eight-group form, or a form using a single `::` compression; a value with two `::` compressions, too few groups, or invalid hex is not IPv6. The two checks are independent; the output reports `ipv4` and `ipv6`, each true/[invalid octet prefix rule].

**Test Cases:** `rcb_tests/public_test_cases/feature5_ip_address_classification.json`

```json
{
    "description": "Classify a host string as an IPv4 literal, an IPv6 literal, both, or neither. An IPv4 literal is four dot-separated decimal octets each in range, with no leading zeros and a non-zero first octet, and no surrounding whitespace. An IPv6 literal is the standard colon-separated hextet form, including the fully expanded eight-group form and the compressed double-colon form, but a doubly-compressed or otherwise malformed value is rejected. The two predicates are independent and reported separately.",
    "cases": [
        {
            "input": {"action": "classify_ip", "host": "1.0.0.0"},
            "expected_output": "ipv4=true\nipv6=[invalid octet prefix rule]\n"
        },
        {
            "input": {"action": "classify_ip", "host": "127.0.0.1"},
            "expected_output": "ipv4=true\nipv6=[invalid octet prefix rule]\n"
        }
    ]
}
```

---

### Feature 6: Identifier Quoting

**As a developer**, I want to safely quote an identifier for embedding in a statement, so embedded names can never break out of their quoting.

**Expected Behavior / Usage:**

The input is a request with action `quote_identifier` carrying an `identifier` string. A non-empty identifier is wrapped in backtick quotes, and every backtick inside the identifier is doubled (so `` ` `` becomes `` ```` `` and `` bad`name `` becomes `` `bad``name` ``). A null/absent or empty identifier is rejected and surfaced as the neutral error category line `error=illegal_argument` rather than a quoted value. The output is either `quoted=<quoted identifier>` or `error=illegal_argument`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_identifier_quoting.json`

```json
{
    "description": "Wrap an identifier in backtick quotes so it is safe to embed in a statement, doubling any backtick that appears inside the identifier. A null or empty identifier is rejected and surfaced as a neutral error category rather than a quoted value.",
    "cases": [
        {
            "input": {"action": "quote_identifier", "identifier": " "},
            "expected_output": "quoted=` `\n"
        },
        {
            "input": {"action": "quote_identifier", "identifier": "`"},
            "expected_output": "quoted=````\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the six features above, with each leaf operation (statement parsing, version decoding, flag decoding, name resolution, address classification, identifier quoting) in its own cohesive unit. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, selects behavior by the request's `action` field (`parse_query`, `parse_version`, `column_definition`, `name_search`, `classify_ip`, `quote_identifier`), invokes the appropriate core logic, and prints the resulting lines to stdout exactly as specified per feature. Native runtime exceptions (e.g. rejecting an empty identifier) must be rendered as neutral `error=<category>` lines, never as host-language type names or stack traces.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the same failure mode for null input as the headers module parses
- follow the positional list format used in the major version constraint checker
