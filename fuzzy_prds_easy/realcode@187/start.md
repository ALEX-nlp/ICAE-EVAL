## Product Requirement Document

# Test-Double Toolkit - A Fluent Library for Creating, Programming, and Verifying Mock Objects

## Project Goal

Build a test-double toolkit that lets developers create stand-in objects for the collaborators of the code under test, program how those stand-ins respond to calls, and afterwards verify how they were used — all through a small, expressive, idiomatic API. The toolkit must support both ordinary (synchronous) members and asynchronous (suspending) members, and must let callers express expectations about call counts and argument values without writing fragile boilerplate.

---

## Background & Problem

Without such a toolkit, developers who want to test a unit in isolation must hand-write fake implementations of every collaborator interface, manually record which methods were called and with what arguments, and assert on that bookkeeping by hand. This produces large amounts of repetitive, error-prone code: a fake that needs to return different values on successive calls, throw on demand, or compute a result from its arguments has to re-implement that logic each time, and verifying "this method was called exactly twice with an argument greater than five" turns into manual counters and conditionals.

With this toolkit, a developer asks for a stand-in of any interface in one call, declaratively programs the responses they need ("when this member is called, return X" / "throw Y" / "compute from the argument"), exercises the code under test, and then states expectations ("this member was called N times with an argument matching this predicate"). Mismatches are reported as clear, categorized failures rather than as low-level assertion noise. The same surface works uniformly for plain objects, for spies that wrap a real object, and for asynchronous members.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This is a multi-responsibility library (double creation, response programming, argument matching, invocation verification, argument capture, asynchronous support, behavior-driven phrasing). It MUST NOT be a single "god file"; lay it out as a clear, multi-file repository (core domain modules plus a separate execution adapter), reflecting a production-grade library. Do not over-engineer, but strictly avoid monolithic files.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in "Core Features" are a **black-box contract for the execution adapter**, NOT the internal data model of the core toolkit. The core logic must be completely decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls against the core API and for rendering observable results (including normalized errors) to stdout.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, response programming, argument matching, verification, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** New response strategies, matchers, and verification modes must be addable without modifying the core engine.
   - **Liskov Substitution Principle (LSP):** A spy (real-backed double) must be substitutable everywhere a plain double is accepted.
   - **Interface Segregation Principle (ISP):** Keep the programming, matching, and verification interfaces small and cohesive.
   - **Dependency Inversion Principle (DIP):** High-level test logic depends on abstractions (a double, a matcher, a verification mode), not on low-level I/O.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public API must read fluently and hide internal complexity.
   - **Resilience:** Edge cases (unmet expectations, too many/too few calls, construction failures, verification on a history-less double) must be modeled as well-defined, categorized error outcomes rather than generic faults. Errors surfaced to the outside world are language-neutral categories, never host-runtime exception class names.

---

## Core Features

### Feature 1: Create a Test Double with Default Responses

**As a developer**, I want to create a stand-in for an interface in a single step, so I can supply it to the code under test without hand-writing a fake.

**Expected Behavior / Usage:**

Creating a test double for an interface returns a usable, non-null stand-in object. Before any response is programmed, every member returns the empty/default value for its declared return type: a member returning an object or string yields `null`, a member returning an integer yields `0`, and a member returning a boolean yields `false`. The input names the double kind (`mock`) and a script of members to invoke; each invocation of a value-returning member emits one `value=<rendered>` line, where `null` renders as the literal `null`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_create_double_defaults.json`

```json
{
    "description": "Creating a test double for an interface returns a usable, non-null stand-in. With no responses configured, every member returns its type's default empty value: object/string members yield null, numeric members yield 0, and boolean members yield false.",
    "cases": [
        {"input": {"double": "mock", "script": [{"do": "invoke", "member": "number"}]}, "expected_output": "value=0\n"},
        {"input": {"double": "mock", "script": [{"do": "invoke", "member": "flag"}]}, "expected_output": "value=false\n"},
        {"input": {"double": "mock", "script": [{"do": "invoke", "member": "nullable"}]}, "expected_output": "value=null\n"}
    ]
}
```

---

### Feature 2: Program Member Responses

**As a developer**, I want to declaratively program what a member returns, so the code under test sees the collaborator behavior my scenario requires.

**Expected Behavior / Usage:**

*2.1 Return a Fixed Value — every invocation yields the configured value.*

A member can be programmed to return a fixed value. After programming, every invocation of that member yields the configured value instead of the type default. The same mechanism works whether the response is attached at creation time (`stubs`) or added to an already-created double (a `stub` step in the script). Each subsequent `invoke` emits `value=<configured>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_stub_return_value.json`

```json
{
    "description": "Configuring a member of a test double to return a fixed value: after programming the response, every invocation of that member yields the configured value instead of the default. The same mechanism works whether the response is programmed at creation time or added to an already-created double.",
    "cases": [
        {"input": {"double": "mock", "stubs": [{"member": "text", "return": "A"}], "script": [{"do": "invoke", "member": "text"}]}, "expected_output": "value=A\n"},
        {"input": {"double": "mock", "script": [{"do": "stub", "member": "text", "return": "result"}, {"do": "invoke", "member": "text"}]}, "expected_output": "value=result\n"}
    ]
}
```

*2.2 Return a Sequence of Values — successive calls yield each value in turn.*

A member can be programmed with an ordered sequence of responses. Successive invocations yield each value in turn; once the sequence is exhausted, the last value repeats for every further invocation. The input lists the sequence; the output is one `value=` line per invocation.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_stub_consecutive.json`

```json
{
    "description": "A member can be programmed with a sequence of responses: successive invocations yield each value in turn, and once the sequence is exhausted the last value is repeated for every further invocation.",
    "cases": [
        {"input": {"double": "mock", "stubs": [{"member": "text", "return_consecutively": ["a", "b"]}], "script": [{"do": "invoke", "member": "text"}, {"do": "invoke", "member": "text"}, {"do": "invoke", "member": "text"}]}, "expected_output": "value=a\nvalue=b\nvalue=b\n"},
        {"input": {"double": "mock", "stubs": [{"member": "number", "return_consecutively": [1, 2, 3]}], "script": [{"do": "invoke", "member": "number"}, {"do": "invoke", "member": "number"}, {"do": "invoke", "member": "number"}, {"do": "invoke", "member": "number"}]}, "expected_output": "value=1\nvalue=2\nvalue=3\nvalue=3\n"}
    ]
}
```

*2.3 Re-program a Member — the most recent response wins.*

Programming a member that already has a configured response replaces the earlier one: the most recently programmed value wins for subsequent invocations.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_stub_override.json`

```json
{
    "description": "Programming a member that already has a configured response replaces the earlier response: the most recently programmed value wins for subsequent invocations.",
    "cases": [
        {"input": {"double": "mock", "stubs": [{"member": "text", "return": "first"}], "script": [{"do": "stub", "member": "text", "return": "second"}, {"do": "invoke", "member": "text"}]}, "expected_output": "value=second\n"}
    ]
}
```

*2.4 Argument-Conditional Response — the response depends on the call argument.*

A response can be made conditional on the argument supplied to the member, using an equality matcher. Invocations whose argument satisfies the condition yield the programmed value; invocations with any other argument fall back to the type's default empty value.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_stub_per_argument.json`

```json
{
    "description": "A response can be made conditional on the argument supplied to a member. Invocations whose argument satisfies the configured condition yield the programmed value; invocations with any other argument fall back to the type's default empty value.",
    "cases": [
        {"input": {"double": "mock", "stubs": [{"member": "echo", "matcher": {"eq": "x"}, "return": "MATCHED"}], "script": [{"do": "invoke", "member": "echo", "arg": "x"}]}, "expected_output": "value=MATCHED\n"},
        {"input": {"double": "mock", "stubs": [{"member": "echo", "matcher": {"eq": "x"}, "return": "MATCHED"}], "script": [{"do": "invoke", "member": "echo", "arg": "y"}]}, "expected_output": "value=null\n"}
    ]
}
```

---

### Feature 3: Compute a Response from the Call Arguments

**As a developer**, I want a member to derive its result from the actual arguments of each call, so the stand-in can react dynamically instead of returning a constant.

**Expected Behavior / Usage:**

A member can be programmed with a computed answer: instead of a fixed value, the response is derived from the invocation's actual arguments, so it varies per call. The input selects a computation (e.g. append a suffix to the argument, or reverse the argument string) and supplies the argument; the output is the computed `value=` line.

**Test Cases:** `rcb_tests/public_test_cases/feature3_computed_answer.json`

```json
{
    "description": "A member can be programmed to compute its result from the actual invocation arguments rather than returning a fixed value, so the response varies with each call's input.",
    "cases": [
        {"input": {"double": "mock", "stubs": [{"member": "echo", "answer_echo": true}], "script": [{"do": "invoke", "member": "echo", "arg": "foo"}]}, "expected_output": "value=foo-result\n"},
        {"input": {"double": "mock", "stubs": [{"member": "echo", "answer_reverse": true}], "script": [{"do": "invoke", "member": "echo", "arg": "abc"}]}, "expected_output": "value=cba\n"}
    ]
}
```

---

### Feature 4: Program a Member to Raise an Error

**As a developer**, I want a member to raise an error on demand, so I can exercise the failure paths of the code under test.

**Expected Behavior / Usage:**

A member can be programmed to raise an error instead of returning a value. Invoking such a member surfaces the configured error to the caller. The input names a neutral error category (e.g. `illegal_state`, `runtime`); the output is a single `error=<category>` line. No host-runtime exception class name ever appears.

**Test Cases:** `rcb_tests/public_test_cases/feature4_stub_throws.json`

```json
{
    "description": "A member can be programmed to raise an error instead of returning a value. Invoking such a member surfaces the configured error category to the caller in a language-neutral form.",
    "cases": [
        {"input": {"double": "mock", "stubs": [{"member": "text", "throw": "illegal_state"}], "script": [{"do": "invoke", "member": "text"}]}, "expected_output": "error=illegal_state\n"},
        {"input": {"double": "mock", "stubs": [{"member": "number", "throw": "runtime"}], "script": [{"do": "invoke", "member": "number"}]}, "expected_output": "error=runtime\n"}
    ]
}
```

---

### Feature 5: Spy on a Real Object

**As a developer**, I want a stand-in that delegates to a real object except where I override it, so I can observe and selectively alter genuine behavior.

**Expected Behavior / Usage:**

A spy wraps a real object: members that are not programmed execute the real implementation and observe real mutable state (e.g. a running total that accumulates across calls), while individual members can still be overridden with a configured response that takes precedence over the real one. The input selects `spy`; invoking real members reflects real state, and any programmed member returns the override instead.

**Test Cases:** `rcb_tests/public_test_cases/feature5_spy.json`

```json
{
    "description": "A spy wraps a real object: unprogrammed members execute the real implementation and observe real state, while individual members can still be overridden with a configured response that takes precedence.",
    "cases": [
        {"input": {"double": "spy", "script": [{"do": "invoke", "member": "add", "arg": 2}, {"do": "invoke", "member": "add", "arg": 3}, {"do": "invoke", "member": "current"}]}, "expected_output": "value=2\nvalue=5\nvalue=5\n"},
        {"input": {"double": "spy", "stubs": [{"member": "current", "return": 99}], "script": [{"do": "invoke", "member": "current"}]}, "expected_output": "value=99\n"}
    ]
}
```

---

### Feature 6: Verify Invocations

**As a developer**, I want to assert how a member was used after exercising the double, so I can confirm the code under test interacts with its collaborators correctly.

**Expected Behavior / Usage:**

*6.1 Verify Call Counts — assert a member was invoked an expected number of times.*

After exercising a double, the number of times a member was invoked can be verified against an expectation: an exact count (`times`), never invoked (`never`), a lower bound (`at_least`), an upper bound (`at_most`), or at-least-once (`at_least_once`). A satisfied expectation emits a `verified member=<name> <mode>` line, where `<mode>` echoes the expectation form (`times=N`, `never`, `at_least=N`, `at_most=N`, `at_least_once`).

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_verify_counts.json`

```json
{
    "description": "After exercising a test double, the number of times a member was invoked can be verified against an expectation. Supported expectations include an exact count, a never-invoked check, a lower bound, an upper bound, and at-least-once.",
    "cases": [
        {"input": {"double": "mock", "script": [{"do": "invoke", "member": "acceptNumber", "arg": 1}, {"do": "verify", "member": "acceptNumber", "matcher": {"any": true}, "mode": {"times": 1}}]}, "expected_output": "verified member=acceptNumber times=1\n"},
        {"input": {"double": "mock", "script": [{"do": "verify", "member": "acceptNumber", "matcher": {"any": true}, "mode": {"never": true}}]}, "expected_output": "verified member=acceptNumber never\n"},
        {"input": {"double": "mock", "script": [{"do": "invoke", "member": "acceptNumber", "arg": 1}, {"do": "invoke", "member": "acceptNumber", "arg": 2}, {"do": "invoke", "member": "acceptNumber", "arg": 3}, {"do": "verify", "member": "acceptNumber", "matcher": {"any": true}, "mode": {"at_least": 2}}]}, "expected_output": "verified member=acceptNumber at_least=2\n"}
    ]
}
```

*6.2 Distinguish Verification Failures — report the kind of count mismatch.*

When the observed count does not satisfy the expectation, verification fails with a category that distinguishes the kind of mismatch: a member that was wanted but never invoked (`wanted_but_not_invoked`, reported with the call target including the double's name), too few invocations (`too_few_invocations`), too many invocations (`too_many_invocations`), or an unwanted invocation of a member expected never to be called (`never_wanted_but_invoked`). Failures other than the never-invoked case echo the member and mode.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_verify_failures.json`

```json
{
    "description": "When the observed invocation count does not satisfy a verification expectation, verification fails with a category that distinguishes the kind of mismatch: a never-invoked member, too few invocations, too many invocations, or an unwanted invocation of a member expected never to be called.",
    "cases": [
        {"input": {"double": "mock", "script": [{"do": "verify", "member": "text", "mode": {"times": 1}}]}, "expected_output": "error=wanted_but_not_invoked target=collaborator.text()\n"},
        {"input": {"double": "mock", "script": [{"do": "invoke", "member": "acceptNumber", "arg": 1}, {"do": "verify", "member": "acceptNumber", "matcher": {"any": true}, "mode": {"times": 2}}]}, "expected_output": "error=too_few_invocations member=acceptNumber times=2\n"},
        {"input": {"double": "mock", "script": [{"do": "invoke", "member": "acceptNumber", "arg": 1}, {"do": "invoke", "member": "acceptNumber", "arg": 2}, {"do": "verify", "member": "acceptNumber", "matcher": {"any": true}, "mode": {"times": 1}}]}, "expected_output": "error=too_many_invocations member=acceptNumber times=1\n"},
        {"input": {"double": "mock", "script": [{"do": "invoke", "member": "acceptNumber", "arg": 1}, {"do": "verify", "member": "acceptNumber", "matcher": {"any": true}, "mode": {"never": true}}]}, "expected_output": "error=never_wanted_but_invoked member=acceptNumber never\n"}
    ]
}
```

*6.3 Reset Recorded History — clear invocations while keeping responses.*

The recorded invocation history of a double can be reset while keeping its programmed responses intact. After a reset, verification sees no prior invocations until the double is exercised again.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_clear_invocations.json`

```json
{
    "description": "The recorded invocation history of a test double can be reset while keeping its programmed responses. After a reset, verification sees no prior invocations until the double is exercised again.",
    "cases": [
        {"input": {"double": "mock", "script": [{"do": "invoke", "member": "acceptNumber", "arg": 1}, {"do": "clear"}, {"do": "verify", "member": "acceptNumber", "matcher": {"any": true}, "mode": {"never": true}}]}, "expected_output": "verified member=acceptNumber never\n"}
    ]
}
```

---

### Feature 7: Argument Matchers

**As a developer**, I want to constrain which arguments a stubbing or verification applies to, so I can match by value, type, comparison, or structure rather than only exact instances.

**Expected Behavior / Usage:**

*7.1 Any and Any-or-Null — accept any argument, optionally including absent.*

A matcher can accept any value rather than a specific one. A plain any-matcher accepts any present (non-null) argument; an any-or-null matcher additionally accepts an absent (null) argument. A satisfied verification emits `verified member=<name> times=1`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_any_and_null.json`

```json
{
    "description": "Verification can use an argument matcher that accepts any value rather than a specific one. A plain any-matcher accepts any present (non-null) argument, while an any-or-null matcher additionally accepts an absent (null) argument.",
    "cases": [
        {"input": {"double": "mock", "script": [{"do": "invoke", "member": "consume", "arg": "anything"}, {"do": "verify", "member": "consume", "matcher": {"any": true}}]}, "expected_output": "verified member=consume times=1\n"},
        {"input": {"double": "mock", "script": [{"do": "invoke", "member": "record", "arg": null}, {"do": "verify", "member": "record", "matcher": {"any_or_null": true}}]}, "expected_output": "verified member=record times=1\n"}
    ]
}
```

*7.2 Value Matchers — equality, identity, type, and pattern.*

An argument can be constrained by value-based matchers: equality to a specific value (`eq`), reference identity to a specific instance (`same`), being an instance of an expected type (`is_a`), or matching a regular-expression pattern (`find`). A matched invocation verifies; an unmatched equality fails with the `arguments_are_different` category.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_value_matchers.json`

```json
{
    "description": "Verification can constrain an argument by value-based matchers: equality to a specific value, reference identity to a specific instance, being an instance of an expected type, or matching a regular-expression pattern. A matched invocation verifies successfully; an unmatched one fails with an arguments-differ category.",
    "cases": [
        {"input": {"double": "mock", "script": [{"do": "invoke", "member": "consume", "arg": "hello"}, {"do": "verify", "member": "consume", "matcher": {"eq": "hello"}}]}, "expected_output": "verified member=consume times=1\n"},
        {"input": {"double": "mock", "script": [{"do": "invoke", "member": "consume", "arg": "hello"}, {"do": "verify", "member": "consume", "matcher": {"eq": "world"}}]}, "expected_output": "error=arguments_are_different member=consume times=1\n"}
    ]
}
```

*7.3 Numeric Comparison Matchers — bounds and logical combinators.*

A numeric argument can be constrained with comparison matchers: greater-or-equal (`geq`), less-or-equal (`leq`), strictly greater (`gt`), strictly less (`lt`), and comparable-equality (`cmp_eq`). Matchers can be combined with logical connectives (`and`, `or`, `not`).

**Test Cases:** `rcb_tests/public_test_cases/feature7_3_numeric_matchers.json`

```json
{
    "description": "Verification can constrain a numeric argument with comparison matchers: greater-or-equal, less-or-equal, strictly greater, strictly less, and comparable-equality. Matchers can also be combined with logical and/or/not connectives.",
    "cases": [
        {"input": {"double": "mock", "script": [{"do": "invoke", "member": "acceptNumber", "arg": 5}, {"do": "verify", "member": "acceptNumber", "matcher": {"geq": 5}}]}, "expected_output": "verified member=acceptNumber times=1\n"},
        {"input": {"double": "mock", "script": [{"do": "invoke", "member": "acceptNumber", "arg": 6}, {"do": "verify", "member": "acceptNumber", "matcher": {"and": [{"gt": 5}, {"lt": 10}]}}]}, "expected_output": "verified member=acceptNumber times=1\n"},
        {"input": {"double": "mock", "script": [{"do": "invoke", "member": "acceptNumber", "arg": 1}, {"do": "verify", "member": "acceptNumber", "matcher": {"not": {"eq": 2}}}]}, "expected_output": "verified member=acceptNumber times=1\n"}
    ]
}
```

*7.4 Collection Matchers — variadic, array, and list constraints.*

Collection-shaped arguments can be constrained: variadic arguments via an any-vararg matcher, fixed-size arrays via element-wise array equality, and lists via a predicate on their structure such as their size. A value-returning variadic member also emits its own `value=` line before the verification line.

**Test Cases:** `rcb_tests/public_test_cases/feature7_4_collection_matchers.json`

```json
{
    "description": "Verification can constrain collection-shaped arguments: variadic arguments via an any-vararg matcher, arrays via element-wise array equality, and lists via a predicate on their structure such as their size.",
    "cases": [
        {"input": {"double": "mock", "script": [{"do": "invoke", "member": "varargs", "args": ["a", "b"]}, {"do": "verify", "member": "varargs"}]}, "expected_output": "value=false\nverified member=varargs times=1\n"},
        {"input": {"double": "mock", "script": [{"do": "invoke", "member": "stringArrayArg", "args": ["a", "b"]}, {"do": "verify", "member": "stringArrayArg", "args": ["a", "b"]}]}, "expected_output": "verified member=stringArrayArg times=1\n"},
        {"input": {"double": "mock", "script": [{"do": "invoke", "member": "listArg", "args": [1, 2, 3]}, {"do": "verify", "member": "listArg", "size_is": 3}]}, "expected_output": "verified member=listArg times=1\n"}
    ]
}
```

---

### Feature 8: Capture Invocation Arguments

**As a developer**, I want to capture the actual arguments passed to a member, so I can inspect them with arbitrary assertions after the fact.

**Expected Behavior / Usage:**

The actual arguments passed to a member across all its invocations can be captured for later inspection. The capture exposes the full ordered list as well as positional selections (first, last). The input invokes the member some number of times and then captures with a `want` selector; the output renders the captured value(s): the full list as `captured=[v1, v2, ...]`, or a single positional value as `captured=<v>`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_capture_arguments.json`

```json
{
    "description": "The actual arguments passed to a member during invocations can be captured for later inspection, exposing the full ordered list as well as the first and last captured value.",
    "cases": [
        {"input": {"double": "mock", "script": [{"do": "invoke", "member": "acceptNumber", "arg": 1}, {"do": "invoke", "member": "acceptNumber", "arg": 2}, {"do": "capture", "member": "acceptNumber", "want": "all"}]}, "expected_output": "captured=[1, 2]\n"},
        {"input": {"double": "mock", "script": [{"do": "invoke", "member": "acceptNumber", "arg": 1}, {"do": "invoke", "member": "acceptNumber", "arg": 2}, {"do": "capture", "member": "acceptNumber", "want": "last"}]}, "expected_output": "captured=2\n"}
    ]
}
```

---

### Feature 9: Behavior-Driven Phrasing (Given/Will)

**As a developer**, I want an alternative given/will phrasing for programming responses, so my tests can read in a behavior-driven style.

**Expected Behavior / Usage:**

The toolkit offers a behavior-driven phrasing for programming responses that is equivalent to the primary phrasing: a member can be given a fixed value, a sequence of values, a computed answer, or an error to raise. The input describes the given/will instruction; a value response emits `value=<v>` and an error response emits `error=<category>`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_bdd_given_will.json`

```json
{
    "description": "The toolkit offers a behavior-driven phrasing (given/will) for programming responses, equivalent to the primary phrasing: a member can be given a fixed value, a sequence of values, a computed answer, or an error to raise.",
    "cases": [
        {"input": {"bdd": {"will_return": "given-value"}}, "expected_output": "value=given-value\n"},
        {"input": {"bdd": {"will_throw": "illegal_state"}}, "expected_output": "error=illegal_state\n"}
    ]
}
```

---

### Feature 10: Asynchronous (Suspending) Members

**As a developer**, I want suspending members to be programmable and verifiable just like ordinary members, so asynchronous collaborators are testable with the same toolkit.

**Expected Behavior / Usage:**

Suspending members are supported on equal footing with ordinary members: they can be programmed with a fixed value or a computed answer, and their invocation count can be verified. The input describes an `async` scenario — return a fixed value (`returns`), echo the argument (`answer_echo_arg`), or verify a count (`verify` with `invocations`). A value scenario emits `value=<v>`; a successful count verification emits `verified member=asyncNumber times=N`.

**Test Cases:** `rcb_tests/public_test_cases/feature10_async_members.json`

```json
{
    "description": "Suspending (asynchronous) members are supported on equal footing with ordinary members: they can be programmed with a fixed value or a computed answer, and their invocation count can be verified.",
    "cases": [
        {"input": {"async": {"returns": 42}}, "expected_output": "value=42\n"},
        {"input": {"async": {"verify": true, "invocations": 2}}, "expected_output": "verified member=asyncNumber times=2\n"}
    ]
}
```

---

### Feature 11: Creation Settings

**As a developer**, I want to configure optional settings when creating a double, so I can tune diagnostics, default behavior, memory, and lifecycle to my scenario.

**Expected Behavior / Usage:**

*11.1 Named Double — a custom name appears in diagnostics.*

A double can be created with a custom name. The name appears in diagnostic output, so an unmet verification on a named double reports the configured name as the target's prefix (`target=<name>.<member>()`).

**Test Cases:** `rcb_tests/public_test_cases/feature11_1_named_double.json`

```json
{
    "description": "A test double can be created with a custom name. The name appears in diagnostic output, so an unmet verification on a named double reports the configured name as the target's prefix.",
    "cases": [
        {"input": {"double": "mock", "settings": {"name": "myDouble"}, "script": [{"do": "verify", "member": "text", "mode": {"times": 1}}]}, "expected_output": "error=wanted_but_not_invoked target=myDouble.text()\n"}
    ]
}
```

*11.2 Default-Answer Strategy — alter the response for unprogrammed members.*

A double can be configured with an alternative default-answer strategy for unprogrammed members: return the double itself where the return type allows it (`returns_self`, reported as `identity=self`), return freshly created doubles for reference-typed members (`returns_mocks`, reported as `presence=present`), or resolve a chain of members lazily through deep stubbing (`deep_stubs`, allowing a chained member to be programmed and read back).

**Test Cases:** `rcb_tests/public_test_cases/feature11_2_default_answers.json`

```json
{
    "description": "A test double can be configured with an alternative default-answer strategy for unprogrammed members: return the double itself where the return type allows it, return freshly created doubles for reference-typed members, or resolve a chain of members lazily through deep stubbing.",
    "cases": [
        {"input": {"double": "mock", "settings": {"default_answer": "returns_self"}, "script": [{"do": "invoke", "member": "selfChain"}]}, "expected_output": "identity=self\n"},
        {"input": {"double": "mock", "settings": {"default_answer": "returns_mocks"}, "script": [{"do": "invoke", "member": "extra"}]}, "expected_output": "presence=present\n"},
        {"input": {"double": "mock", "settings": {"default_answer": "deep_stubs"}, "stubs": [{"member": "deepChain", "return": 7}], "script": [{"do": "invoke", "member": "deepChain"}]}, "expected_output": "value=7\n"}
    ]
}
```

*11.3 Serializable Marker — opt into serializability.*

A double can be marked serializable at creation time. A double created with the serializable option reports as serializable, whereas an ordinary double does not.

**Test Cases:** `rcb_tests/public_test_cases/feature11_3_serializable_marker.json`

```json
{
    "description": "A test double can be marked serializable at creation time. A double created with the serializable option reports as serializable, whereas an ordinary double does not.",
    "cases": [
        {"input": {"double": "mock", "settings": {"serializable": true}, "script": [{"do": "report_serializable"}]}, "expected_output": "serializable=true\n"},
        {"input": {"double": "mock", "script": [{"do": "report_serializable"}]}, "expected_output": "serializable=false\n"}
    ]
}
```

*11.4 Stub-Only Enforcement — no history, verification rejected.*

A double can be created as stub-only, recording no invocation history to save memory. Programmed responses still work, but attempting to verify invocations on a stub-only double is rejected with the `stub_only` error category.

**Test Cases:** `rcb_tests/public_test_cases/feature11_4_stub_only_enforcement.json`

```json
{
    "description": "A test double can be created as stub-only, which records no invocation history to save memory. Programmed responses still work, but attempting to verify invocations on a stub-only double is rejected.",
    "cases": [
        {"input": {"double": "mock", "settings": {"stub_only": true}, "stubs": [{"member": "text", "return": "S"}], "script": [{"do": "invoke", "member": "text"}]}, "expected_output": "value=S\n"},
        {"input": {"double": "mock", "settings": {"stub_only": true}, "script": [{"do": "invoke", "member": "acceptNumber", "arg": 1}, {"do": "verify", "member": "acceptNumber", "matcher": {"any": true}, "mode": {"times": 1}}]}, "expected_output": "error=stub_only member=acceptNumber times=1\n"}
    ]
}
```

*11.5 Invocation Listener — observe every call.*

A double can be created with an invocation listener that is notified whenever any member is invoked. After exercising the double, the listener reports that it was notified; without any invocation it reports that it was not.

**Test Cases:** `rcb_tests/public_test_cases/feature11_5_invocation_listener.json`

```json
{
    "description": "A test double can be created with an invocation listener that is notified whenever any member is invoked. After exercising the double, the listener reports that it was notified; without any invocation it reports that it was not.",
    "cases": [
        {"input": {"double": "mock", "settings": {"invocation_listener": true}, "script": [{"do": "invoke", "member": "acceptNumber", "arg": 1}, {"do": "report_listener"}]}, "expected_output": "listener_notified=true\n"},
        {"input": {"double": "mock", "settings": {"invocation_listener": true}, "script": [{"do": "report_listener"}]}, "expected_output": "listener_notified=false\n"}
    ]
}
```

*11.6 Construction Failure — real-constructor errors surface neutrally.*

A double can be created by invoking the real constructor of the underlying type. When that constructor raises an error during construction, double creation fails and the failure is surfaced as the neutral `mock_creation_failed` error category.

**Test Cases:** `rcb_tests/public_test_cases/feature11_6_construction_failure.json`

```json
{
    "description": "A test double can be created by invoking the real constructor of the underlying type. When that constructor raises an error during construction, double creation fails and the failure is surfaced as a neutral error category.",
    "cases": [
        {"input": {"create_with_constructor": {"throwing": true}}, "expected_output": "error=mock_creation_failed\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the features above — double creation, response programming (fixed/sequential/computed/throwing), spying, argument matching (any/value/numeric/collection plus logical combinators), invocation verification with distinct failure categories, history reset, argument capture, behavior-driven phrasing, asynchronous-member support, and creation settings. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads one JSON command object from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above (including normalizing all errors to language-neutral categories). This adapter must be logically and physically separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_create_double_defaults.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_create_double_defaults@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata), so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- refer to the derivation logic in the `answer_echo` and `answer_reverse` sections
- check for the 'wanted_but_not_invoked' error target format in the mock creation documentation
