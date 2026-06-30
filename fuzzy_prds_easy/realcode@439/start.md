## Product Requirement Document

# Topic-Based Message Routing Engine — Hierarchical Routing Keys, Wildcard Subscriptions & Member Lookup

## Project Goal

Build a routing engine for a publish/subscribe messaging system that decides, purely from data, whether a published message should be delivered to a given subscription. Messages carry a hierarchical *routing key* derived from their own fields; subscriptions carry a *binding key* pattern with wildcards. The engine answers "does this pattern select this message?" deterministically, so that higher-level transport code can fan messages out to interested parties without re-implementing matching logic.

---

## Background & Problem

In a topic-based messaging system, every message is tagged with a routing key made of ordered parts (for example `zone.exchange.ticker`), and every subscriber registers a binding key pattern describing which messages it wants. Without a shared engine, every component invents its own pattern syntax and matching rules, producing inconsistent behavior and subtle delivery bugs.

This engine provides one well-defined contract. It (1) derives a routing key from a message's declared routing members, (2) matches a routing key against a binding-key pattern using single-level (`*`) and multi-level (`#`) wildcards, (3) compiles a pattern into a predicate that can be evaluated directly against a message's members, and (4) lets callers resolve which token in a binding key corresponds to a named routing member. All behavior is pure data-in / value-out and locale-independent.

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

### Feature 1: Wildcard Routing-Key Matching

**As a developer**, I want to test a message's routing key against a subscription's binding-key pattern, so I can decide whether the subscription should receive the message.

**Expected Behavior / Usage:**

A binding-key pattern and a routing key are both sequences of parts separated by [a specific locale-based number formatting rule — ask the PM for the exact culture string]s. Matching proceeds part by part. A literal pattern part matches only the identical routing-key part. A single-level wildcard `*` matches exactly one routing-key part in that position, whatever its value. A multi-level wildcard `#` matches the entire remainder of the routing key (including the case of zero remaining parts) and ends the comparison immediately. A pattern that is empty, or that is exactly the single token `#`, is a match-all pattern and accepts every routing key. When no `#` short-circuits the comparison, a routing key matches only if every part agreed AND the routing key has the same number of parts as the pattern (so a pattern with more or fewer literal/`*` parts than the routing key does not match). The output reports the canonical rendering of the pattern and of the routing key (a match-all/empty pattern renders as `#`) and then whether they match. In the input, a `binding_key` of `null` denotes the empty match-all pattern.

**Test Cases:** `rcb_tests/public_test_cases/feature1_routing_key_matching.json`

```json
{
    "description": "Match a hierarchical routing key against a subscription pattern. A pattern is a sequence of [a specific locale-based number formatting rule — ask the PM for the exact culture string]-separated parts; a part may be a literal token, the single-level wildcard '*' (matches exactly one part in that position, regardless of value), or the multi-level wildcard '#' (matches the remainder of the routing key, including zero further parts). A pattern that is empty, or that consists of the single token '#', matches every routing key. Otherwise a routing key matches only when each of its parts agrees with the corresponding pattern part and the two have the same number of parts (unless a '#' short-circuits the comparison). The output echoes the canonical form of the pattern and of the routing key (an empty/match-all pattern renders as '#'), then reports whether they match.",
    "cases": [
        {"input": {"action": "match", "binding_key": "a.b.*", "routing_key": "a.b.c"}, "expected_output": "binding_key=a.b.*\nrouting_key=a.b.c\nmatch=true\n"},
        {"input": {"action": "match", "binding_key": "a.b.c.d", "routing_key": "a.b"}, "expected_output": "binding_key=a.b.c.d\nrouting_key=a.b\nmatch=false\n"}
    ]
}
```

---

### Feature 2: Predicate Matching Against a Message's Members

**As a developer**, I want to compile a binding-key pattern into a predicate and run it directly against a concrete message, so I can match without first materializing the message's routing key as a string.

**Expected Behavior / Usage:**

The message under test declares three routing members at positions 1, 2 and 3: a numeric value, a text value, and an identifier value. The engine first derives the message's routing key by rendering those members in position order (numeric values rendered culture-invariantly; the identifier in its canonical textual form). It then compiles the supplied pattern into a predicate: for each pattern part that is a literal, the corresponding member's rendered value must equal that literal; `*` parts impose no constraint; a `#` part ends the constraint list and accepts the rest; an empty or all-wildcard pattern accepts everything. The output reports the derived routing key, the canonical pattern, and whether the predicate accepts the message.

**Test Cases:** `rcb_tests/public_test_cases/feature2_predicate_message_matching.json`

```json
{
    "description": "Build a matching predicate from a subscription pattern and evaluate it directly against a concrete message instance. The message carries three routing members declared at positions 1, 2 and 3: a numeric value, a text value, and an identifier value. The engine reads those members in position order to form the message's routing key (numeric values rendered culture-invariantly, the identifier in its canonical textual form), then tests the supplied pattern against the message: each literal pattern part must equal the corresponding member's rendered value, '*' parts impose no constraint, and a '#' part stops the comparison and accepts the rest. The output reports the message's derived routing key, the canonical pattern, and whether the predicate accepts the message.",
    "cases": [
        {"input": {"action": "predicate_match", "binding_key": "1.toto.*", "message": {"number": "1", "text": "toto", "identifier": "00000000-0000-0000-0000-000000000000"}}, "expected_output": "routing_key=1.toto.00000000-0000-0000-0000-000000000000\nbinding_key=1.toto.*\nmatch=true\n"},
        {"input": {"action": "predicate_match", "binding_key": "2.toto.*", "message": {"number": "1", "text": "toto", "identifier": "00000000-0000-0000-0000-000000000000"}}, "expected_output": "routing_key=1.toto.00000000-0000-0000-0000-000000000000\nbinding_key=2.toto.*\nmatch=false\n"}
    ]
}
```

---

### Feature 3: Routing-Key Extraction From a Message

**As a developer**, I want a message's routing key built from its declared routing members, so messages are tagged consistently regardless of host locale.

**Expected Behavior / Usage:**

A message declares zero or more routing members, each with an explicit position. The engine reads the members in ascending position order, renders each value as a culture-invariant string (so a decimal always uses a [a specific locale-based number formatting rule — ask the PM for the exact culture string] as its decimal separator, never a comma), and joins the rendered parts with [a specific locale-based number formatting rule — ask the PM for the exact culture string]s to form the routing key. A message that declares no routing members yields the special match-all token `#` and a part count of zero. If a routing member's value is missing/null, extraction fails and is reported as a normalized error that names the offending member's declared position. The output reports the routing key and its part count, or the normalized error. The input message shape is identified by its fields: a three-member message supplies `number`, `text` and `identifier`; a two-member message supplies `int_a` and `int_b`; a message with no routing members supplies an empty object.

**Test Cases:** `rcb_tests/public_test_cases/feature3_routing_key_extraction.json`

```json
{
    "description": "Derive a message's routing key from its declared routing members. Each routing member has an explicit position; members are read in ascending position order and each value is rendered as a culture-invariant string (so a decimal is rendered with a [a specific locale-based number formatting rule — ask the PM for the exact culture string] as decimal separator regardless of locale), then the rendered parts are joined with [a specific locale-based number formatting rule — ask the PM for the exact culture string]s to form the routing key. A message that declares no routing members produces the special match-all token. A routing member whose value is missing/null is rejected with a normalized error that reports the offending member's position. The output reports the routing key and its part count, or the normalized error.",
    "cases": [
        {"input": {"action": "routing_key", "message": {"number": "42.42", "text": "name", "identifier": "11111111-1111-1111-1111-111111111111"}}, "expected_output": "routing_key=42.42.name.11111111-1111-1111-1111-111111111111\npart_count=3\n"},
        {"input": {"action": "routing_key", "message": {"number": "0", "text": null, "identifier": "11111111-1111-1111-1111-111111111111"}}, "expected_output": "[a specific error category string — ask the PM for the exact prefix and key]\nposition=2\n"}
    ]
}
```

---

### Feature 4: Binding-Key Token For a Named Member

**As a developer**, I want to read the token a binding key assigns to a specific named routing member, so I can inspect or index subscriptions by member.

**Expected Behavior / Usage:**

A message type declares named routing members at positions 1, 2 and 3 (named `Number`, `Text` and `Identifier`). Given a binding key and a member name, the engine resolves the member to its index (by position order) and returns the token at that index in the binding key. When the binding key is empty/match-all, every member resolves to the single-level wildcard token `*`. Requesting a member name the type does not declare produces a normalized error that echoes the requested member name. The output is the resolved token, or the normalized error. In the input, a `binding_key` of `null` denotes the empty match-all binding key.

**Test Cases:** `rcb_tests/public_test_cases/feature4_member_token_lookup.json`

```json
{
    "description": "Look up the binding-key token bound to a single named routing member of a message type. The message type declares three routing members at positions 1, 2 and 3 (named Number, Text and Identifier). Given a binding key and a member name, the engine resolves the member to its position index and returns the token sitting at that index in the binding key. When the binding key is empty/match-all, every member resolves to the single-level wildcard token. Asking for a member name that the type does not declare yields a normalized error naming the requested member. The output is the resolved token, or the normalized error.",
    "cases": [
        {"input": {"action": "member_part", "binding_key": "123.456.793e1561-26e4-4737-817f-996b986c1666", "member": "Number"}, "expected_output": "part=123\n"},
        {"input": {"action": "member_part", "binding_key": null, "member": "Nonexistent"}, "expected_output": "error=unknown_routing_member\nmember=Nonexistent\n"}
    ]
}
```

---

### Feature 5: Sorted-Position Member Indexing Across Binding Keys

**As a developer**, I want to extract one member's token from several binding keys at once, with member indexing that is robust to non-contiguous declared positions, so batch inspection stays correct.

**Expected Behavior / Usage:**

A message type may declare routing members at non-contiguous positions (for example positions 2 and 4, named `First` and `Second`). Members are indexed by their sorted-position order — the member with the smallest position takes index 0, the next takes index 1, and so on — regardless of the literal position numbers. Given a member name and a list of binding keys, the engine returns the token at that member's index from each binding key, preserving order; an empty binding key yields the single-level wildcard token `*` for every member. The output lists one resolved token per supplied binding key. In the input, a `null` entry in `binding_keys` denotes an empty match-all binding key.

**Test Cases:** `rcb_tests/public_test_cases/feature5_sorted_position_indexing.json`

```json
{
    "description": "Extract a single routing member's token from each of several binding keys at once, for a message type whose routing positions are non-contiguous. The type declares two routing members at positions 2 and 4 (named First and Second). Even though the declared positions are non-contiguous, members are indexed by their sorted-position order: the member at the smallest position takes index 0, the next takes index 1, and so on. For the requested member, the engine returns the token at that member's index from each supplied binding key (an empty binding key yields the single-level wildcard token for every member). The output lists one resolved token per supplied binding key, in order.",
    "cases": [
        {"input": {"action": "member_parts", "member": "First", "binding_keys": ["123.*", "*.456", "123.456", null]}, "expected_output": "part=123\npart=*\npart=123\npart=*\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the routing engine described above (routing-key extraction, wildcard matching, predicate compilation, and member-token lookup). Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the result to stdout, matching the per-feature contracts above. The request's `action` selects behavior: `match` (Feature 1), `predicate_match` (Feature 2), `routing_key` (Feature 3), `member_part` (Feature 4), and `member_parts` (Feature 5). Native errors raised by the core (such as a null routing member or an unknown member name) must be translated by the adapter into the normalized, language-neutral `error=<category>` lines shown above — never leaking host-language runtime details.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the same placeholder syntax as the routing key formatter
- return the default fallback pattern defined in the core pattern engine
