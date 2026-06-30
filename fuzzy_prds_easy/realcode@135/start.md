## Product Requirement Document

# Container Name Registry & Authoritative Resolver — Text-Configured DNS Backend for Virtual Networks

## Project Goal

Build a reusable in-memory name registry and authoritative resolver that ingests simple text descriptions of one or more virtual networks (their bind addresses and the containers attached to them) and answers forward, reverse, and resolver-discovery queries, so a network runtime can serve names for containers without each component re-implementing its own ad-hoc lookup tables.

---

## Background & Problem

On a host that runs many containers across several virtual networks, every container needs to reach its peers by name rather than by hard-coded address. The membership of each network — which gateway/bind addresses it listens on, which containers belong to it, what names and aliases each container answers to, and which upstream resolvers should serve queries the registry cannot answer itself — is published as a set of small text files, one per network.

Without a shared component, each consumer hand-rolls its own parser and lookup tables, leading to inconsistent name matching, missed dual-stack (IPv4 + IPv6) addresses, and brittle handling of malformed input. This library defines one well-specified contract: it parses the network description text, builds the lookup tables once, and exposes a small query surface — resolve a name to its addresses, resolve an address back to its names, list a container's per-container or per-network upstream resolvers, enumerate a network's bind addresses, and report which networks an address belongs to. Name matching is case-insensitive; a name or address may carry several addresses of either family; and a single malformed network description is skipped rather than aborting the whole parse.

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

## Input Model (shared by all features)

Every request is a single JSON object. It always carries an `op` (the operation to perform) and a `config` object that maps a **network name** to that network's **configuration text**. Operation-specific fields (such as `requester`, `name`, `target`, or `container`) are described per feature.

Each network's configuration text is line-oriented (lines separated by `\n`; blank lines are ignored):

- **First line — network bind addresses:** a comma-separated list of the network's bind/gateway addresses (IPv4 and/or IPv6). It may be followed, after a single space, by one more token: a comma-separated list of **network-level** upstream resolver addresses.
- **Each following line — one container:** four space-separated fields, `<id> <ipv4-list> <ipv6-list> <names>`, optionally followed by a fifth field `<dns-servers>`. The `ipv4-list`, `ipv6-list`, `names`, and `dns-servers` fields are each comma-separated; an address field may be empty (the container has no address of that family). `names` holds the container's primary name plus any aliases. Names are stored and matched **case-insensitively**.

The parser builds all lookup tables up front from this text; the features below query those tables.

---

## Core Features

### Feature 1: Per-Network Bind Address Parsing

**As a developer**, I want to parse the network descriptions and read back each network's bind addresses split by address family, so I can confirm where each network listens and verify the parser tolerates a malformed description.

**Expected Behavior / Usage:**

With `op` set to `bind_addresses`, the parser reads every network in `config` and reports, per network, the bind addresses taken from that network's first line, partitioned into an IPv4 group and an IPv6 group while preserving the order in which they were listed. The output lists networks ordered by network name; for each it emits a `network=<name>` line, then a `bind_v4=` line, then a `bind_v6=` line, each carrying the comma-joined addresses of that family (empty when that family has none). A network whose description is malformed (for example, its first line carries an unparseable address token) is skipped entirely and contributes nothing to the output, but its presence does not cause the overall parse to fail — well-formed networks are still reported, and a `config` containing only a malformed network yields empty output.

**Test Cases:** `rcb_tests/public_test_cases/feature1_parse_bind_addresses.json`

```json
{
    "description": "Parse a set of textual network-configuration files and report, per network, the gateway/bind addresses split into IPv4 and IPv6 families. Each file represents one network whose name is the file name; the file's first line lists the network's bind addresses (comma-separated, optionally followed by network-level upstream servers). The parser groups bind addresses by family preserving their listed order, and tolerates a malformed file by skipping that network entirely without failing the whole parse.",
    "cases": [
        {"input": {"op": "bind_addresses", "config": {"net0": "10.88.0.1\n68fb291b0318b54a71f6f3636e58bd0896f084e5ba4fa311ecf36e019c5e6e43 10.88.0.2  condescendingnash\n68fb291b0318b54a71f6f3636e58bd0896f084e5ba4fa311ecf36e019c5e6e48 10.88.0.5  HelloWorld\n95655fb6832ba134efa66e9c80862a6c9b04f3cc6abf8adfdda8c38112c2c6fa 10.88.0.3  hopefulmontalcini,testdbctr\n8bcc5fe0cb09bee5dfb71d61503a87688cfc82aa5f130bcedb19357a17765926 10.88.0.4  trustingzhukovsky,ctr1,ctra\n"}}, "expected_output": "network=net0\nbind_v4=10.88.0.1\nbind_v6=\n"},
        {"input": {"op": "bind_addresses", "config": {"net0": "10.89.0.1\n7b46c7ad93fcbcb945c35286a5ba19d6976093e2ce39d2cb38ba1eba636404ab 10.89.0.2  test1,7b46c7ad93fc\n7b46c7ad93fcbcb945c35286a5ba19d6976093e2ce39d2cb38ba1eba636404ab  fdfd:733b:dc3:220b::2 test1,7b46c7ad93fc\n88dde8a2489780d3c8c90db54a9a97faf5dbe4f555b23e27880ca189dae0e2b0 10.89.0.3  test2,88dde8a24897\n88dde8a2489780d3c8c90db54a9a97faf5dbe4f555b23e27880ca189dae0e2b0  fdfd:733b:dc3:220b::3 test2,88dde8a24897\n", "net1": "10.0.0.1,10.0.1.1,fdfd::1,fddd::1\nf35256b5e2f72ec8cb7d974d4f8841686fc8921fdfbc867285b50164e313f715 10.0.0.2,10.0.1.2 fdfd::2,fddd::2 testmulti1\ne5df0cdbe0136a30cc3e848d495d2cc6dada25b7dedc776b4584ce2cbba6f06f 10.0.0.3,10.0.1.3 fdfd::3,fddd::3 testmulti2\n"}}, "expected_output": "network=net0\nbind_v4=10.89.0.1\nbind_v6=\nnetwork=net1\nbind_v4=10.0.0.1,10.0.1.1\nbind_v6=fdfd::1,fddd::1\n"}
    ]
}
```

---

### Feature 2: Forward Name Resolution

**As a developer**, I want to resolve a name into the addresses registered for it, from the perspective of a requesting container, so peers can reach each other by name across the family (IPv4/IPv6) of their choice.

**Expected Behavior / Usage:**

All sub-features use `op` set to `lookup` with a `requester` (the querying container's address) and a `name`. The requester's network membership is derived from the parsed configuration; resolution is performed against the networks the requester belongs to. The result is the ordered list of addresses registered for the matched name. Address lists are rendered on a single `[addr list prefix]` line with comma-separated values; an unmatched name produces a non-existent-domain marker instead.

*2.1 Resolve A Name — own name, peer name, or alias*

The queried name may be the requester's own registered name, another container's primary name, or any alias of another container. In each case the registry returns the address list registered for that name on the requester's network, as `[addr list prefix]<comma-separated>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_resolve_name.json`

```json
{
    "description": "Resolve a name to its address list using the perspective of a requesting container IP. The requester's network membership is derived from configuration; the queried name may be the requester's own name, another container's primary name, or one of its aliases. The result is the ordered list of addresses registered for that name on the requester's network.",
    "cases": [
        {"input": {"op": "lookup", "config": {"net0": "10.88.0.1\n68fb291b0318b54a71f6f3636e58bd0896f084e5ba4fa311ecf36e019c5e6e43 10.88.0.2  condescendingnash\n68fb291b0318b54a71f6f3636e58bd0896f084e5ba4fa311ecf36e019c5e6e48 10.88.0.5  HelloWorld\n95655fb6832ba134efa66e9c80862a6c9b04f3cc6abf8adfdda8c38112c2c6fa 10.88.0.3  hopefulmontalcini,testdbctr\n8bcc5fe0cb09bee5dfb71d61503a87688cfc82aa5f130bcedb19357a17765926 10.88.0.4  trustingzhukovsky,ctr1,ctra\n"}, "requester": "10.88.0.2", "name": "condescendingnash"}, "expected_output": "[addr list prefix]10.88.0.2\n"},
        {"input": {"op": "lookup", "config": {"net0": "10.88.0.1\n68fb291b0318b54a71f6f3636e58bd0896f084e5ba4fa311ecf36e019c5e6e43 10.88.0.2  condescendingnash\n68fb291b0318b54a71f6f3636e58bd0896f084e5ba4fa311ecf36e019c5e6e48 10.88.0.5  HelloWorld\n95655fb6832ba134efa66e9c80862a6c9b04f3cc6abf8adfdda8c38112c2c6fa 10.88.0.3  hopefulmontalcini,testdbctr\n8bcc5fe0cb09bee5dfb71d61503a87688cfc82aa5f130bcedb19357a17765926 10.88.0.4  trustingzhukovsky,ctr1,ctra\n"}, "requester": "10.88.0.2", "name": "trustingzhukovsky"}, "expected_output": "[addr list prefix]10.88.0.4\n"}
    ]
}
```

*2.2 Case-Insensitive Resolution*

A name registered in mixed case is matched regardless of the case of the query: the same address list is returned for a lower-case query and an upper-case query.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_case_insensitive.json`

```json
{
    "description": "Resolve a name case-insensitively. Names registered with mixed case are matched regardless of the case used in the query, so the same address list is returned whether the query is lower-case or upper-case.",
    "cases": [
        {"input": {"op": "lookup", "config": {"net0": "10.88.0.1\n68fb291b0318b54a71f6f3636e58bd0896f084e5ba4fa311ecf36e019c5e6e43 10.88.0.2  condescendingnash\n68fb291b0318b54a71f6f3636e58bd0896f084e5ba4fa311ecf36e019c5e6e48 10.88.0.5  HelloWorld\n95655fb6832ba134efa66e9c80862a6c9b04f3cc6abf8adfdda8c38112c2c6fa 10.88.0.3  hopefulmontalcini,testdbctr\n8bcc5fe0cb09bee5dfb71d61503a87688cfc82aa5f130bcedb19357a17765926 10.88.0.4  trustingzhukovsky,ctr1,ctra\n"}, "requester": "10.88.0.2", "name": "helloworld"}, "expected_output": "[addr list prefix]10.88.0.5\n"},
        {"input": {"op": "lookup", "config": {"net0": "10.88.0.1\n68fb291b0318b54a71f6f3636e58bd0896f084e5ba4fa311ecf36e019c5e6e43 10.88.0.2  condescendingnash\n68fb291b0318b54a71f6f3636e58bd0896f084e5ba4fa311ecf36e019c5e6e48 10.88.0.5  HelloWorld\n95655fb6832ba134efa66e9c80862a6c9b04f3cc6abf8adfdda8c38112c2c6fa 10.88.0.3  hopefulmontalcini,testdbctr\n8bcc5fe0cb09bee5dfb71d61503a87688cfc82aa5f130bcedb19357a17765926 10.88.0.4  trustingzhukovsky,ctr1,ctra\n"}, "requester": "10.88.0.2", "name": "HELLOWORLD"}, "expected_output": "[addr list prefix]10.88.0.5\n"}
    ]
}
```

*2.3 Unknown Name*

A name that is not registered on the requester's network resolves to a non-existent-domain outcome (the single marker `[invalid domain notation]`) rather than an empty success.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_unknown_name.json`

```json
{
    "description": "Resolve a name that is not registered on the requester's network. When no address is registered for the queried name, the resolver reports a non-existent-domain outcome rather than an empty success.",
    "cases": [
        {"input": {"op": "lookup", "config": {"net0": "10.88.0.1\n68fb291b0318b54a71f6f3636e58bd0896f084e5ba4fa311ecf36e019c5e6e43 10.88.0.2  condescendingnash\n68fb291b0318b54a71f6f3636e58bd0896f084e5ba4fa311ecf36e019c5e6e48 10.88.0.5  HelloWorld\n95655fb6832ba134efa66e9c80862a6c9b04f3cc6abf8adfdda8c38112c2c6fa 10.88.0.3  hopefulmontalcini,testdbctr\n8bcc5fe0cb09bee5dfb71d61503a87688cfc82aa5f130bcedb19357a17765926 10.88.0.4  trustingzhukovsky,ctr1,ctra\n"}, "requester": "10.88.0.2", "name": "somebadquery"}, "expected_output": "[invalid domain notation]\n"}
    ]
}
```

*2.4 Dual-Stack Resolution*

A name may carry several addresses, mixing IPv4 and IPv6, and resolving it returns every registered address in listed order. The requester may be reached over either family and still observes the full list. A container may additionally be addressed by its identifier as well as by name.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_dual_stack.json`

```json
{
    "description": "Resolve a dual-stack name to all of its addresses. A name may carry both IPv4 and IPv6 addresses (and possibly several of each); resolving it returns every registered address in listed order. The requester may itself be reached over either family and still observes the full address list. A container may also be addressed by its identifier in addition to its name.",
    "cases": [
        {"input": {"op": "lookup", "config": {"net0": "10.89.0.1\n7b46c7ad93fcbcb945c35286a5ba19d6976093e2ce39d2cb38ba1eba636404ab 10.89.0.2  test1,7b46c7ad93fc\n7b46c7ad93fcbcb945c35286a5ba19d6976093e2ce39d2cb38ba1eba636404ab  fdfd:733b:dc3:220b::2 test1,7b46c7ad93fc\n88dde8a2489780d3c8c90db54a9a97faf5dbe4f555b23e27880ca189dae0e2b0 10.89.0.3  test2,88dde8a24897\n88dde8a2489780d3c8c90db54a9a97faf5dbe4f555b23e27880ca189dae0e2b0  fdfd:733b:dc3:220b::3 test2,88dde8a24897\n", "net1": "10.0.0.1,10.0.1.1,fdfd::1,fddd::1\nf35256b5e2f72ec8cb7d974d4f8841686fc8921fdfbc867285b50164e313f715 10.0.0.2,10.0.1.2 fdfd::2,fddd::2 testmulti1\ne5df0cdbe0136a30cc3e848d495d2cc6dada25b7dedc776b4584ce2cbba6f06f 10.0.0.3,10.0.1.3 fdfd::3,fddd::3 testmulti2\n"}, "requester": "10.89.0.2", "name": "test1"}, "expected_output": "[addr list prefix]10.89.0.2,fdfd:733b:dc3:220b::2\n"},
        {"input": {"op": "lookup", "config": {"net0": "10.89.0.1\n7b46c7ad93fcbcb945c35286a5ba19d6976093e2ce39d2cb38ba1eba636404ab 10.89.0.2  test1,7b46c7ad93fc\n7b46c7ad93fcbcb945c35286a5ba19d6976093e2ce39d2cb38ba1eba636404ab  fdfd:733b:dc3:220b::2 test1,7b46c7ad93fc\n88dde8a2489780d3c8c90db54a9a97faf5dbe4f555b23e27880ca189dae0e2b0 10.89.0.3  test2,88dde8a24897\n88dde8a2489780d3c8c90db54a9a97faf5dbe4f555b23e27880ca189dae0e2b0  fdfd:733b:dc3:220b::3 test2,88dde8a24897\n", "net1": "10.0.0.1,10.0.1.1,fdfd::1,fddd::1\nf35256b5e2f72ec8cb7d974d4f8841686fc8921fdfbc867285b50164e313f715 10.0.0.2,10.0.1.2 fdfd::2,fddd::2 testmulti1\ne5df0cdbe0136a30cc3e848d495d2cc6dada25b7dedc776b4584ce2cbba6f06f 10.0.0.3,10.0.1.3 fdfd::3,fddd::3 testmulti2\n"}, "requester": "fdfd:733b:dc3:220b::2", "name": "test1"}, "expected_output": "[addr list prefix]10.89.0.2,fdfd:733b:dc3:220b::2\n"}
    ]
}
```

---

### Feature 3: Reverse Address Lookup

**As a developer**, I want to turn an address back into the name(s) that own it, from the perspective of a requesting container on the same network, so logs and tooling can display friendly names for raw addresses.

**Expected Behavior / Usage:**

With `op` set to `reverse_lookup`, a `requester` and a `target` address are supplied. The registry locates the target on the requester's network(s) and returns every name and alias registered for that target, in registration order, on a single `names=` line with comma-separated values. This works for both IPv4 and IPv6 targets.

**Test Cases:** `rcb_tests/public_test_cases/feature3_reverse_lookup.json`

```json
{
    "description": "Given a requesting container IP and a target IP on the same network, return the registered name(s) and alias(es) for that target address, in registration order. Works for both IPv4 and IPv6 targets.",
    "cases": [
        {"input": {"op": "reverse_lookup", "config": {"net0": "10.88.0.1\n68fb291b0318b54a71f6f3636e58bd0896f084e5ba4fa311ecf36e019c5e6e43 10.88.0.2  condescendingnash\n68fb291b0318b54a71f6f3636e58bd0896f084e5ba4fa311ecf36e019c5e6e48 10.88.0.5  HelloWorld\n95655fb6832ba134efa66e9c80862a6c9b04f3cc6abf8adfdda8c38112c2c6fa 10.88.0.3  hopefulmontalcini,testdbctr\n8bcc5fe0cb09bee5dfb71d61503a87688cfc82aa5f130bcedb19357a17765926 10.88.0.4  trustingzhukovsky,ctr1,ctra\n"}, "requester": "10.88.0.4", "target": "10.88.0.4"}, "expected_output": "names=trustingzhukovsky,ctr1,ctra\n"},
        {"input": {"op": "reverse_lookup", "config": {"net0": "10.89.0.1\n7b46c7ad93fcbcb945c35286a5ba19d6976093e2ce39d2cb38ba1eba636404ab 10.89.0.2  test1,7b46c7ad93fc\n7b46c7ad93fcbcb945c35286a5ba19d6976093e2ce39d2cb38ba1eba636404ab  fdfd:733b:dc3:220b::2 test1,7b46c7ad93fc\n88dde8a2489780d3c8c90db54a9a97faf5dbe4f555b23e27880ca189dae0e2b0 10.89.0.3  test2,88dde8a24897\n88dde8a2489780d3c8c90db54a9a97faf5dbe4f555b23e27880ca189dae0e2b0  fdfd:733b:dc3:220b::3 test2,88dde8a24897\n"}, "requester": "fdfd:733b:dc3:220b::2", "target": "fdfd:733b:dc3:220b::2"}, "expected_output": "names=test1,7b46c7ad93fc\n"}
    ]
}
```

---

### Feature 4: Per-Container Upstream DNS Servers

**As a developer**, I want to read the upstream DNS servers declared for an individual container, so queries the registry cannot answer itself can be forwarded to that container's chosen resolvers.

**Expected Behavior / Usage:**

With `op` set to `container_dns_servers` and a `container` address, the registry returns the comma-separated upstream resolver list declared on that container's line (the optional fifth field), as `[dns config key]<comma-separated>`. The list may mix IPv4 and IPv6. A container that declares no upstream resolvers is reported as `[dns config key]none`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_container_dns_servers.json`

```json
{
    "description": "Report the per-container upstream DNS servers declared in configuration. A container line may optionally end with a comma-separated list of upstream resolver addresses (IPv4 and/or IPv6); querying that container's IP returns that list. A container with no declared upstream resolvers is reported as having none.",
    "cases": [
        {"input": {"op": "container_dns_servers", "config": {"net0": "10.88.0.1\n68fb291b0318b54a71f6f3636e58bd0896f084e5ba4fa311ecf36e019c5e6e43 10.88.0.2  condescendingnash 8.8.8.8\n68fb291b0318b54a71f6f3636e58bd0896f084e5ba4fa311ecf36e019c5e6e48 10.88.0.5  HelloWorld 3.3.3.3,1.1.1.1,::1\n95655fb6832ba134efa66e9c80862a6c9b04f3cc6abf8adfdda8c38112c2c6fa 10.88.0.3  hopefulmontalcini,testdbctr\n8bcc5fe0cb09bee5dfb71d61503a87688cfc82aa5f130bcedb19357a17765926 10.88.0.4  trustingzhukovsky,ctr1,ctra\n"}, "container": "10.88.0.2"}, "expected_output": "[dns config key]8.8.8.8\n"},
        {"input": {"op": "container_dns_servers", "config": {"net0": "10.88.0.1\n68fb291b0318b54a71f6f3636e58bd0896f084e5ba4fa311ecf36e019c5e6e43 10.88.0.2  condescendingnash 8.8.8.8\n68fb291b0318b54a71f6f3636e58bd0896f084e5ba4fa311ecf36e019c5e6e48 10.88.0.5  HelloWorld 3.3.3.3,1.1.1.1,::1\n95655fb6832ba134efa66e9c80862a6c9b04f3cc6abf8adfdda8c38112c2c6fa 10.88.0.3  hopefulmontalcini,testdbctr\n8bcc5fe0cb09bee5dfb71d61503a87688cfc82aa5f130bcedb19357a17765926 10.88.0.4  trustingzhukovsky,ctr1,ctra\n"}, "container": "10.88.0.5"}, "expected_output": "[dns config key]3.3.3.3,1.1.1.1,::1\n"}
    ]
}
```

---

### Feature 5: Network-Scoped Upstream Resolvers

**As a developer**, I want every container on a network to inherit the network's declared upstream resolvers, so I can configure resolvers once per network instead of per container.

**Expected Behavior / Usage:**

With `op` set to `network_resolvers` and a `container` address, the registry returns the network-level upstream resolvers (declared as the optional second token on the network's first line) that the container inherits by virtue of its network membership, as `resolvers=<comma-separated>`. The inherited list applies uniformly to every container on that network and may mix IPv4 and IPv6.

**Test Cases:** `rcb_tests/public_test_cases/feature5_network_scoped_resolvers.json`

```json
{
    "description": "Report the network-level upstream DNS resolvers that apply to a container. When a network's first configuration line declares network-scoped resolver addresses, every container on that network inherits them; querying any such container's IP returns that inherited resolver list.",
    "cases": [
        {"input": {"op": "network_resolvers", "config": {"net0": "10.88.0.1 127.0.0.1,::2\n68fb291b0318b54a71f6f3636e58bd0896f084e5ba4fa311ecf36e019c5e6e43 10.88.0.2  condescendingnash 8.8.8.8\n68fb291b0318b54a71f6f3636e58bd0896f084e5ba4fa311ecf36e019c5e6e48 10.88.0.5  HelloWorld 3.3.3.3,1.1.1.1,::1\n95655fb6832ba134efa66e9c80862a6c9b04f3cc6abf8adfdda8c38112c2c6fa 10.88.0.3  hopefulmontalcini,testdbctr\n8bcc5fe0cb09bee5dfb71d61503a87688cfc82aa5f130bcedb19357a17765926 10.88.0.4  trustingzhukovsky,ctr1,ctra\n"}, "container": "10.88.0.2"}, "expected_output": "resolvers=127.0.0.1,::2\n"}
    ]
}
```

---

### Feature 6: Network Membership Of An Address

**As a developer**, I want to learn which network(s) a given container address belongs to, so I can scope further queries and authorization to the right network(s).

**Expected Behavior / Usage:**

With `op` set to `network_membership` and a `container` address, the registry returns the deduplicated list of networks the owning container participates in, as `networks=<comma-separated>`. Every address of a container — IPv4 or IPv6 — maps to the same membership.

**Test Cases:** `rcb_tests/public_test_cases/feature6_network_membership.json`

```json
{
    "description": "Report which network(s) a container address belongs to. Each address registered in configuration is mapped to the set of networks the owning container participates in (deduplicated); querying an address returns that network list. Both IPv4 and IPv6 addresses of the same container resolve to the same membership.",
    "cases": [
        {"input": {"op": "network_membership", "config": {"net0": "10.89.0.1\n7b46c7ad93fcbcb945c35286a5ba19d6976093e2ce39d2cb38ba1eba636404ab 10.89.0.2  test1,7b46c7ad93fc\n7b46c7ad93fcbcb945c35286a5ba19d6976093e2ce39d2cb38ba1eba636404ab  fdfd:733b:dc3:220b::2 test1,7b46c7ad93fc\n88dde8a2489780d3c8c90db54a9a97faf5dbe4f555b23e27880ca189dae0e2b0 10.89.0.3  test2,88dde8a24897\n88dde8a2489780d3c8c90db54a9a97faf5dbe4f555b23e27880ca189dae0e2b0  fdfd:733b:dc3:220b::3 test2,88dde8a24897\n"}, "container": "10.89.0.3"}, "expected_output": "networks=net0\n"},
        {"input": {"op": "network_membership", "config": {"net0": "10.89.0.1\n7b46c7ad93fcbcb945c35286a5ba19d6976093e2ce39d2cb38ba1eba636404ab 10.89.0.2  test1,7b46c7ad93fc\n7b46c7ad93fcbcb945c35286a5ba19d6976093e2ce39d2cb38ba1eba636404ab  fdfd:733b:dc3:220b::2 test1,7b46c7ad93fc\n88dde8a2489780d3c8c90db54a9a97faf5dbe4f555b23e27880ca189dae0e2b0 10.89.0.3  test2,88dde8a24897\n88dde8a2489780d3c8c90db54a9a97faf5dbe4f555b23e27880ca189dae0e2b0  fdfd:733b:dc3:220b::3 test2,88dde8a24897\n"}, "container": "fdfd:733b:dc3:220b::2"}, "expected_output": "networks=net0\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above — a configuration parser that builds the in-memory lookup tables, and a query surface for forward resolution, reverse resolution, per-container and network-scoped resolver discovery, bind-address enumeration, and network membership. The core logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, materializes the supplied `config` map into network descriptions, parses them via the core system, dispatches on `op`, and prints the resulting contract line(s) to stdout. The request's `op` selects behavior: `bind_addresses`, `lookup` (with `requester`, `name`), `reverse_lookup` (with `requester`, `target`), `container_dns_servers` (with `container`), `network_resolvers` (with `container`), and `network_membership` (with `container`). Address lists are rendered as comma-separated values; an unmatched forward lookup renders `[invalid domain notation]`; a container with no declared upstream resolvers renders `[dns config key]none`.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
```


---
**Implementation notes:**
- see the first-line-upstream logic used for network parsing
- check the validation rules for a standard container definition line
