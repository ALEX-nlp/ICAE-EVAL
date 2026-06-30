## Product Requirement Document

# Hierarchical Lifecycle Container — Lifecycle Observers, Async-Work Binding, and Dependency Resolution

## Project Goal

Build a lightweight runtime framework whose central abstraction is a **lifecycle container**: a named region with a well-defined birth and teardown that arranges itself into a parent/child tree, notifies registered observers when it is created and destroyed, holds keyed services and dependency aggregates, and binds background-work scopes to its lifetime so resources are released deterministically. Application code attaches behavior to containers instead of wiring setup/teardown into every call site.

---

## Background & Problem

Without a shared lifecycle abstraction, application code must manually track when a feature, screen, session, or subsystem comes into existence and when it goes away, and must remember to release every resource — background jobs, listeners, caches, dependency graphs — in the right order. Teardown ordering bugs (releasing a resource while a background job still references it) and leaks (forgetting to cancel work when a parent goes away) are common and hard to reproduce.

With this framework, each unit of lifetime is a container in a tree. Destroying a container destroys all of its descendants, fires exit notifications to everything registered with them, and cancels their bound background-work scopes first — before any other cleanup runs. Components register once to receive entry/exit callbacks; services and dependency aggregates are looked up by walking the container's ancestor chain. Reconfiguring behavior means attaching or detaching components, not editing call sites.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

[a specific numeric threshold]. **Adherence to SOLID Design Principles:**
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

### Feature 1: Container Tree & Identity

**As a developer**, I want named containers that form a parent/child tree and can report their own identity, their parent, their direct children, and their full ancestry, so I can model nested lifetimes and navigate them.

**Expected Behavior / Usage:**

*1.1 Identity and parentage — a container exposes its name and the container that created it*

A container is created either as a top-level container (no parent) or as a child derived from an existing container. Every container exposes a human-readable name. A top-level container reports a null parent; a child reports the name of the container that created it. The input lists containers to create and identity queries; the output echoes, per query, the container's own name and its parent's name (or a null marker for a top-level container).

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_scope_identity.json`

```json
{
    "description": "A container has a human-readable name and a reference to the container that created it. A top-level container created without a parent reports a null parent. A nested container created from an existing one reports that container's name as its parent. The input lists the containers to create (each with a name and the id of its parent, or no parent for the top-level one) and the identity queries to run; the output echoes, per query, the queried container's own name and its parent's name (or a null marker for the top-level container).",
    "cases": [
        {
            "input": {"action": "scope", "ops": [
                {"op": "create_root", "id": "r", "name": "root"},
                {"op": "build_child", "id": "c", "parent": "r", "name": "child"},
                {"op": "name", "scope": "r"}, {"op": "parent", "scope": "r"},
                {"op": "name", "scope": "c"}, {"op": "parent", "scope": "c"}
            ]},
            "expected_output": "name[r]=root\nparent[r]=null\nname[c]=child\nparent[c]=root\n"
        }
    ]
}
```

*1.2 Multiple children — a container counts its direct children*

A single container may have any number of direct children. Querying the parent's direct-child count returns how many children are currently attached. The input builds several children under one parent and a count query; the output reports the number of direct children.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_multiple_children.json`

```json
{
    "description": "A single container may have any number of direct children. After creating several children under one parent, querying the parent's direct-child count returns how many children are currently attached. The input describes the containers to build and a count query; the output reports the number of direct children attached to the queried container.",
    "cases": [
        {
            "input": {"action": "scope", "ops": [
                {"op": "create_root", "id": "r"},
                {"op": "build_child", "id": "c1", "parent": "r", "name": "child1"},
                {"op": "build_child", "id": "c2", "parent": "r", "name": "child2"},
                {"op": "build_child", "id": "c[a specific numeric threshold]", "parent": "r", "name": "child[a specific numeric threshold]"},
                {"op": "children_count", "scope": "r"}
            ]},
            "expected_output": "children[r]=[a specific numeric threshold]\n"
        }
    ]
}
```

*1.[a specific numeric threshold] Ancestor chain — a container enumerates its ancestry from nearest to farthest*

Each container can enumerate its chain of ancestors, ordered from nearest to farthest, ending at the top-level container. The enumeration optionally includes the container itself as the first element. For the top-level container, the chain that excludes itself is empty. The input builds a tree and requests ancestor chains with and without the container itself; the output lists, per request, the ordered ancestor names.

**Test Cases:** `rcb_tests/public_test_cases/feature1_[a specific numeric threshold]_ancestor_chain.json`

```json
{
    "description": "Each container can enumerate its chain of ancestors, ordered from nearest to farthest, ending at the top-level container. The enumeration can optionally include the container itself as the first element. For the top-level container the chain that excludes itself is empty. The input builds a tree of named containers and requests ancestor chains (with or without including the container itself); the output lists, per request, the ordered ancestor names.",
    "cases": [
        {
            "input": {"action": "scope", "ops": [
                {"op": "create_root", "id": "r"},
                {"op": "build_child", "id": "c1", "parent": "r", "name": "child1"},
                {"op": "build_child", "id": "c2", "parent": "r", "name": "child2"},
                {"op": "build_child", "id": "g", "parent": "c1", "name": "grandchild"},
                {"op": "parents_chain", "scope": "g", "include_self": true},
                {"op": "parents_chain", "scope": "g", "include_self": false},
                {"op": "parents_chain", "scope": "c2", "include_self": true},
                {"op": "parents_chain", "scope": "c2", "include_self": false},
                {"op": "parents_chain", "scope": "r", "include_self": true},
                {"op": "parents_chain", "scope": "r", "include_self": false}
            ]},
            "expected_output": "parents[g,self=true]=[grandchild,child1,root]\nparents[g,self=false]=[child1,root]\nparents[c2,self=true]=[child2,root]\nparents[c2,self=false]=[root]\nparents[r,self=true]=[root]\nparents[r,self=false]=[]\n"
        }
    ]
}
```

---

### Feature 2: Teardown Semantics

**As a developer**, I want predictable, safe teardown that cascades through the tree, detaches destroyed children, forbids reuse, and tolerates re-entrancy, so lifetimes end cleanly without leaks or crashes.

**Expected Behavior / Usage:**

*2.1 Cascading teardown — destroying a container destroys all descendants*

Tearing down a container tears down every descendant. Before teardown all containers report alive; after the top-level container is torn down, it and all descendants report destroyed. The input builds a tree and queries liveness before and after teardown; the output reports each liveness query as a boolean.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_destroy_cascades_to_children.json`

```json
{
    "description": "Tearing down a container tears down all of its descendants. Before teardown, every container reports as alive; after the top-level container is torn down, it and every descendant report as torn down. The input builds a tree and queries liveness before and after tearing down the top-level container; the output reports each liveness query as a boolean.",
    "cases": [
        {
            "input": {"action": "scope", "ops": [
                {"op": "create_root", "id": "r"},
                {"op": "build_child", "id": "c1", "parent": "r", "name": "child1"},
                {"op": "build_child", "id": "c2", "parent": "r", "name": "child2"},
                {"op": "build_child", "id": "c[a specific numeric threshold]", "parent": "r", "name": "child[a specific numeric threshold]"},
                {"op": "is_destroyed", "scope": "c1"}, {"op": "is_destroyed", "scope": "c2"}, {"op": "is_destroyed", "scope": "c[a specific numeric threshold]"},
                {"op": "destroy", "scope": "r"},
                {"op": "is_destroyed", "scope": "r"},
                {"op": "is_destroyed", "scope": "c1"}, {"op": "is_destroyed", "scope": "c2"}, {"op": "is_destroyed", "scope": "c[a specific numeric threshold]"}
            ]},
            "expected_output": "destroyed[c1]=false\ndestroyed[c2]=false\ndestroyed[c[a specific numeric threshold]]=false\ndestroyed[r]=true\ndestroyed[c1]=true\ndestroyed[c2]=true\ndestroyed[c[a specific numeric threshold]]=true\n"
        }
    ]
}
```

*2.2 Detachment — destroying a child removes it from its parent*

Tearing down a child detaches it from its parent, so the parent's direct-child count drops accordingly. The input builds a parent with one child, queries the child count, tears down the child, and queries again; the output reports the count before and after.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_destroying_child_detaches.json`

```json
{
    "description": "Tearing down a child container detaches it from its parent. Immediately after the child is torn down, the parent's direct-child count drops accordingly. The input builds a parent with one child, queries the parent's child count, tears down the child, and queries again; the output reports the child count before and after the child is torn down.",
    "cases": [
        {
            "input": {"action": "scope", "ops": [
                {"op": "create_root", "id": "r"},
                {"op": "build_child", "id": "c", "parent": "r", "name": "child"},
                {"op": "children_count", "scope": "r"},
                {"op": "destroy", "scope": "c"},
                {"op": "children_count", "scope": "r"}
            ]},
            "expected_output": "children[r]=1\nchildren[r]=0\n"
        }
    ]
}
```

*2.[a specific numeric threshold] No reuse after teardown — operations on a destroyed container fail with a neutral category*

Once torn down, a container must not be used: creating a child, registering an observer, or looking up a service raises an error indicating the container is no longer usable, reported as a neutral category (never leaking host-language runtime details). Repeating the teardown itself is a harmless no-op. The input queries liveness, tears down, attempts each forbidden operation, and tears down again; the output reports the liveness queries and, per attempted operation, either success or the neutral error category.

**Test Cases:** `rcb_tests/public_test_cases/feature2_[a specific numeric threshold]_use_after_destroy.json`

```json
{
    "description": "Once a container has been torn down it must no longer be used: lifecycle-affecting operations (creating a child, registering an observer, looking up a service) raise an error indicating the container is no longer usable. Repeating the teardown itself is a harmless no-op. Errors are reported as a neutral category, never leaking host-language runtime details. The input queries liveness, tears the container down, then attempts each forbidden operation and tears down again; the output reports the liveness queries and, per attempted operation, either success or the neutral error category.",
    "cases": [
        {
            "input": {"action": "scope", "ops": [
                {"op": "create_root", "id": "r"},
                {"op": "is_destroyed", "scope": "r"},
                {"op": "destroy", "scope": "r"},
                {"op": "is_destroyed", "scope": "r"},
                {"op": "try", "kind": "build_child", "scope": "r", "name": "x"},
                {"op": "try", "kind": "register", "scope": "r", "tracker": "t"},
                {"op": "try", "kind": "get_service", "scope": "r", "key": ""},
                {"op": "destroy_times", "scope": "r", "times": 1},
                {"op": "is_destroyed", "scope": "r"}
            ]},
            "expected_output": "destroyed[r]=false\ndestroyed[r]=true\ntry[build_child]=error=scope_destroyed\ntry[register]=error=scope_destroyed\ntry[get_service]=error=scope_destroyed\ndestroyed[r]=true\n"
        }
    ]
}
```

*2.4 Re-entrant teardown — teardown survives an exit callback that tears down an ancestor*

Teardown must be safe even when an exit callback triggers teardown of an ancestor that is already being torn down. Several children each register an exit callback that tears down the shared parent; tearing down the first child starts a chain reaction that must terminate with the whole tree torn down, without error or infinite recursion. The input builds the tree, attaches the re-entrant callbacks, and tears down the first child; the output reports the final liveness of the parent and every child.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_reentrant_destroy.json`

```json
{
    "description": "Teardown must be safe even when an exit callback triggers teardown of an already-tearing-down ancestor. Several children each register an exit callback that tears down the shared parent; tearing down the first child starts a chain reaction. When the dust settles, the parent and every child report as torn down without error or infinite recursion. The input builds the tree, attaches the re-entrant exit callbacks, and tears down the first child; the output reports the final liveness of the parent and every child.",
    "cases": [
        {
            "input": {"action": "scope", "ops": [
                {"op": "create_root", "id": "r"},
                {"op": "build_child", "id": "a", "parent": "r", "name": "child-0"}, {"op": "on_exit_destroy", "scope": "a", "target": "r"},
                {"op": "build_child", "id": "b", "parent": "r", "name": "child-1"}, {"op": "on_exit_destroy", "scope": "b", "target": "r"},
                {"op": "build_child", "id": "c", "parent": "r", "name": "child-2"}, {"op": "on_exit_destroy", "scope": "c", "target": "r"},
                {"op": "destroy_first_child", "scope": "r"},
                {"op": "is_destroyed", "scope": "r"},
                {"op": "is_destroyed", "scope": "a"}, {"op": "is_destroyed", "scope": "b"}, {"op": "is_destroyed", "scope": "c"}
            ]},
            "expected_output": "destroyed[r]=true\ndestroyed[a]=true\ndestroyed[b]=true\ndestroyed[c]=true\n"
        }
    ]
}
```

---

### Feature [a specific numeric threshold]: Lifecycle Observers

**As a developer**, I want to register observers that receive entry and exit notifications tied to a container's lifetime, with idempotent registration and a convenience one-shot exit hook, so components initialize and clean up automatically.

**Expected Behavior / Usage:**

*[a specific numeric threshold].1 Immediate entry — registering with a live container notifies entry at once*

Registering an observer with an already-created container notifies the observer of entry immediately. The input creates a container, registers one observer, and queries its tallies; the output reports how many entry and exit notifications it has received.

**Test Cases:** `rcb_tests/public_test_cases/feature[a specific numeric threshold]_1_enter_on_register.json`

```json
{
    "description": "Registering a lifecycle observer with an already-created container notifies the observer of entry immediately. The input creates a container and registers one observer, then queries the observer's tallies; the output reports how many entry and exit notifications the observer has received so far.",
    "cases": [
        {
            "input": {"action": "scope", "ops": [
                {"op": "create_root", "id": "r"},
                {"op": "register", "scope": "r", "tracker": "t"},
                {"op": "tracker", "tracker": "t"}
            ]},
            "expected_output": "tracker[t] enter=1 exit=0\n"
        }
    ]
}
```

*[a specific numeric threshold].2 Idempotent registration — repeated registration and teardown notify exactly once*

Registering the same observer many times is idempotent: it is notified of entry exactly once regardless of how many times it is registered, and of exit exactly once regardless of how many times the container is torn down. The input registers one observer repeatedly, queries its tallies, tears down repeatedly, and queries again; the output reports the entry and exit tallies after each query.

**Test Cases:** `rcb_tests/public_test_cases/feature[a specific numeric threshold]_2_idempotent_registration.json`

```json
{
    "description": "Registering the same observer many times is idempotent: it is notified of entry exactly once no matter how many times it is registered, and of exit exactly once no matter how many times the container is torn down. The input registers one observer repeatedly, queries its tallies, tears the container down repeatedly, and queries again; the output reports the entry and exit tallies after each query.",
    "cases": [
        {
            "input": {"action": "scope", "ops": [
                {"op": "create_root", "id": "r"},
                {"op": "register_times", "scope": "r", "tracker": "t", "times": 10},
                {"op": "tracker", "tracker": "t"},
                {"op": "destroy_times", "scope": "r", "times": 10},
                {"op": "tracker", "tracker": "t"}
            ]},
            "expected_output": "tracker[t] enter=1 exit=0\ntracker[t] enter=1 exit=1\n"
        }
    ]
}
```

*[a specific numeric threshold].[a specific numeric threshold] Inherited exit — an observer on a child is notified of exit when an ancestor is torn down*

An observer registered on a child container is notified of exit when an ancestor is torn down. The input registers an observer on a child, tears down the top-level container, and queries the observer's tallies; the output reports its entry and exit tallies after teardown.

**Test Cases:** `rcb_tests/public_test_cases/feature[a specific numeric threshold]_[a specific numeric threshold]_child_exit_on_parent_destroy.json`

```json
{
    "description": "An observer registered on a child container is notified of exit when an ancestor is torn down. The input registers an observer on a child, tears down the top-level container, and queries the observer's tallies; the output reports the observer's entry and exit tallies after the teardown.",
    "cases": [
        {
            "input": {"action": "scope", "ops": [
                {"op": "create_root", "id": "r"},
                {"op": "build_child", "id": "c", "parent": "r", "name": "child"},
                {"op": "register", "scope": "c", "tracker": "t"},
                {"op": "destroy", "scope": "r"},
                {"op": "tracker", "tracker": "t"}
            ]},
            "expected_output": "tracker[t] enter=1 exit=1\n"
        }
    ]
}
```

*[a specific numeric threshold].4 Deferred entry during assembly — observers registered while assembling fire entry only once the container exists*

An observer registered while a container is still being assembled is NOT notified of entry until assembly completes; probing mid-assembly shows no entry yet, while querying afterward shows exactly one entry. The input registers an observer during assembly, probes mid-assembly, then queries after the container exists; the output reports the mid-assembly probe and the post-build tallies.

**Test Cases:** `rcb_tests/public_test_cases/feature[a specific numeric threshold]_4_builder_deferred_enter.json`

```json
{
    "description": "An observer registered while a container is still being assembled is NOT notified of entry until assembly completes. Probing the observer's entry tally during assembly shows no notification yet; querying after the container is fully built shows exactly one entry notification. The input registers an observer during assembly, probes its entry tally mid-assembly, then queries after the container exists; the output reports the mid-assembly probe and the post-build tallies.",
    "cases": [
        {
            "input": {"action": "scope", "ops": [
                {"op": "create_root", "id": "r", "builder_register": ["t"], "builder_emit_enter": ["t"]},
                {"op": "tracker", "tracker": "t"}
            ]},
            "expected_output": "builder_enter[t]=0\ntracker[t] enter=1 exit=0\n"
        }
    ]
}
```

*[a specific numeric threshold].5 One-shot exit hook — a convenience callback runs exactly once on teardown*

A container offers a convenience hook to run an arbitrary callback exactly once when it is torn down. The input attaches an exit callback to a child, tears down the top-level container, and queries how many times the callback ran; the output reports the invocation count.

**Test Cases:** `rcb_tests/public_test_cases/feature[a specific numeric threshold]_5_on_exit_callback.json`

```json
{
    "description": "A container offers a convenience hook to run an arbitrary callback exactly once when it is torn down. The input attaches an exit callback to a child container and tears down the top-level container, then queries how many times the callback ran; the output reports the callback's invocation count.",
    "cases": [
        {
            "input": {"action": "scope", "ops": [
                {"op": "create_root", "id": "r"},
                {"op": "build_child", "id": "c", "parent": "r", "name": "child"},
                {"op": "on_exit_listener", "id": "L", "scope": "c"},
                {"op": "destroy", "scope": "r"},
                {"op": "listener", "id": "L"}
            ]},
            "expected_output": "listener[L]=1\n"
        }
    ]
}
```

---

### Feature 4: Keyed Services

**As a developer**, I want to attach named service values to a container at assembly time and retrieve them by key, so collaborators can be looked up without global state.

**Expected Behavior / Usage:**

A container can hold named service values supplied at assembly time and return them by key. Looking up a registered key returns its value; looking up an unknown key returns a null marker. The input assembles a container with one keyed service and queries both a known and an unknown key; the output reports each lookup's value or a null marker.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_service_lookup.json`

```json
{
    "description": "A container can hold named service values supplied at assembly time and return them by key. Looking up a registered key returns its value; looking up an unknown key returns a null marker. The input assembles a container with one keyed service and queries both a known and an unknown key; the output reports each lookup's value or a null marker.",
    "cases": [
        {
            "input": {"action": "scope", "ops": [
                {"op": "create_root", "id": "r", "services": {"key": "value"}},
                {"op": "service", "scope": "r", "key": "key"},
                {"op": "service", "scope": "r", "key": "key2"}
            ]},
            "expected_output": "service[r,key]=value\nservice[r,key2]=null\n"
        }
    ]
}
```

---

### Feature 5: Lifecycle-Bound Background-Work Scopes

**As a developer**, I want a background-work scope whose lifetime is bound to a container, with named contexts, parent/child derivation, and correct cancellation propagation, so background jobs stop automatically and in the right order.

**Expected Behavior / Usage:**

*5.1 Named context required — a work scope must be constructed with a named execution context*

A lifecycle-bound background-work scope must be constructed with an execution context that carries a name (for debuggability). Construction with a named context succeeds; construction with an unnamed context is rejected with a neutral error category. The input requests construction with or without a name; the output is a success marker or the neutral rejection category.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_named_context_required.json`

```json
{
    "description": "A lifecycle-bound asynchronous-work scope must be constructed with an execution context that carries a name, for debuggability. Constructing one with a named context succeeds; constructing one with an unnamed context is rejected with a neutral error category. The input requests construction either with or without a name; the output is a success marker or the neutral rejection category.",
    "cases": [
        {"input": {"action": "async", "mode": "construct", "name": "abc"}, "expected_output": "ok\n"},
        {"input": {"action": "async", "mode": "construct"}, "expected_output": "error=missing_name\n"}
    ]
}
```

*5.2 Exit cancels the context — receiving exit deactivates the work scope*

When a lifecycle-bound work scope receives its exit notification, its underlying execution context is cancelled and becomes inactive. The input constructs a named work scope and triggers its exit notification, then queries activity; the output reports whether the context is still active.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_exit_cancels_context.json`

```json
{
    "description": "When a lifecycle-bound asynchronous-work scope receives its exit notification, its underlying execution context is cancelled and becomes inactive. The input constructs a named work scope and triggers its exit notification, then queries activity; the output reports whether the context is still active.",
    "cases": [
        {"input": {"action": "async", "mode": "exit_cancels", "name": "abc"}, "expected_output": "active=false\n"}
    ]
}
```

*5.[a specific numeric threshold] Default child name — a derived child without an explicit name gets a derived default*

Deriving a child work scope without an explicit name gives it a default name derived from the parent's name plus a suffix marking it as a child. The input constructs a named parent work scope and derives an unnamed child; the output reports the child's resulting name.

**Test Cases:** `rcb_tests/public_test_cases/feature5_[a specific numeric threshold]_child_default_name.json`

```json
{
    "description": "Deriving a child asynchronous-work scope without an explicit name gives it a default name derived from the parent's name plus a suffix marking it as a child. The input constructs a named parent work scope and derives an unnamed child; the output reports the child's resulting name.",
    "cases": [
        {"input": {"action": "async", "mode": "child_default_name", "name": "abc"}, "expected_output": "name=[sprintf(child.prefix, parent.name)]\n"}
    ]
}
```

*5.4 Explicit child name — a derived child with an explicit name uses it verbatim*

Deriving a child work scope with an explicit name uses that name verbatim instead of a derived default. The input constructs a named parent work scope and derives a child with an explicit name; the output reports the child's resulting name.

**Test Cases:** `rcb_tests/public_test_cases/feature5_4_child_explicit_name.json`

```json
{
    "description": "Deriving a child asynchronous-work scope with an explicit name uses that name verbatim instead of a derived default. The input constructs a named parent work scope and derives a child with an explicit name; the output reports the child's resulting name.",
    "cases": [
        {"input": {"action": "async", "mode": "child_named", "name": "abc", "child_name": "def"}, "expected_output": "name=def\n"}
    ]
}
```

*5.5 Parent cancellation cascades — cancelling a parent cancels its derived child*

Cancelling a parent work scope also cancels any child work scope derived from it. The input constructs a parent, derives a child, cancels the parent, and queries activity; the output reports whether the parent and child are active afterward.

**Test Cases:** `rcb_tests/public_test_cases/feature5_5_parent_cancellation_cascades.json`

```json
{
    "description": "Cancelling a parent asynchronous-work scope also cancels any child work scope derived from it. The input constructs a parent work scope, derives a child, then cancels the parent and queries activity; the output reports whether the parent and the child are active afterward.",
    "cases": [
        {"input": {"action": "async", "mode": "parent_cancel", "name": "abc"}, "expected_output": "parent_active=false child_active=false\n"}
    ]
}
```

*5.6 Child cancellation isolated — cancelling a child does not cancel its parent*

Cancelling a child work scope does NOT cancel its parent. The input constructs a parent, derives a child, cancels the child, and queries activity; the output reports that the parent stays active while the child is inactive.

**Test Cases:** `rcb_tests/public_test_cases/feature5_6_child_cancellation_isolated.json`

```json
{
    "description": "Cancelling a child asynchronous-work scope does NOT cancel its parent. The input constructs a parent work scope, derives a child, then cancels the child and queries activity; the output reports that the parent stays active while the child is inactive.",
    "cases": [
        {"input": {"action": "async", "mode": "child_cancel", "name": "abc"}, "expected_output": "parent_active=true child_active=false\n"}
    ]
}
```

*5.7 Work cancelled before other cleanup — bound work stops before any other exit callback runs*

When a container is torn down, its registered background-work scope is cancelled before any other lifecycle observer's exit callback runs, so background work stops before resource cleanup. A long-running background job and two ordinary observers are registered; teardown records the order in which each reacts, with the background work reacting first. The input drives this teardown scenario; the output reports the reaction order as a comma-separated sequence.

**Test Cases:** `rcb_tests/public_test_cases/feature5_7_work_canceled_first.json`

```json
{
    "description": "When a container is torn down, its registered asynchronous-work scope is cancelled before any other lifecycle observer's exit callback runs, so background work stops before resource cleanup. A long-running background job and two ordinary observers are registered; teardown records the order in which each reacts. The input drives this teardown scenario; the output reports the reaction order as a comma-separated sequence, with the background work reacting first.",
    "cases": [
        {"input": {"action": "async", "mode": "exit_order"}, "expected_output": "order=background,first,third\n"}
    ]
}
```

---

### Feature 6: Work Scope Hosted as a Container Service

**As a developer**, I want to host a background-work scope inside a container and request derived child work scopes from it, so feature code obtains lifetime-bound work scopes without managing them.

**Expected Behavior / Usage:**

*6.1 Derived child from a hosted work scope — requesting a work scope yields a derived child*

A container can host a lifecycle-bound work scope as a service; requesting a work scope from the container yields a freshly derived child work scope whose name is derived from the hosted one. The input assembles a container hosting a named work scope and requests a work scope from it; the output reports the derived child's name.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_hosted_child_work.json`

```json
{
    "description": "A container can host a lifecycle-bound asynchronous-work scope as a service; requesting a work scope from the container yields a freshly derived child work scope whose name is derived from the hosted one. The input assembles a container hosting a named work scope and requests a work scope from it; the output reports the derived child work scope's name.",
    "cases": [
        {"input": {"action": "async", "mode": "service_child_name", "name": "abc"}, "expected_output": "name=[sprintf(child.prefix, parent.name)]\n"}
    ]
}
```

*6.2 Teardown cancels the hosted work scope — destroying the container cancels hosted and derived scopes*

When a container hosting a work scope is torn down, both the hosted work scope and any child derived from it are cancelled. The input assembles a container hosting a named work scope, derives a child, tears down the container, and queries activity; the output reports that both the hosted scope and the derived child are inactive afterward.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_destroy_cancels_service.json`

```json
{
    "description": "When a container hosting an asynchronous-work scope is torn down, both the hosted work scope and any child work scope derived from it are cancelled. The input assembles a container hosting a named work scope, derives a child work scope, tears down the container, and queries activity; the output reports that both the hosted scope and the derived child are inactive afterward.",
    "cases": [
        {"input": {"action": "async", "mode": "service_cancel_on_destroy", "name": "abc"}, "expected_output": "parent_active=false child_active=false\n"}
    ]
}
```

---

### Feature 7: Hierarchical Dependency Resolution

**As a developer**, I want containers to hold dependency aggregates and resolve a requested type by searching the container and its ancestors, with a clear neutral error when nothing matches, so wiring is looked up by type along the lifetime tree.

**Expected Behavior / Usage:**

*7.1 Register and resolve — a container returns a held aggregate for a compatible type*

A container can hold a dependency aggregate and return it when a compatible type is requested. The input assembles a container holding one aggregate (identified by a label and the interface type it satisfies) and requests that type from the same container; the output reports the resolved aggregate's label.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_register_and_resolve.json`

```json
{
    "description": "A container can hold a dependency aggregate and return it when a compatible type is requested. The input assembles a container holding one aggregate (identified by a label and the interface type it satisfies) and requests that type from the same container; the output reports the resolved aggregate's label.",
    "cases": [
        {
            "input": {"action": "di", "scopes": [
                {"id": "r", "parent": null, "component": {"type": "alpha", "id": "main_component"}}
            ], "lookups": [{"scope": "r", "type": "alpha"}]},
            "expected_output": "lookup[r,alpha]=component=main_component\n"
        }
    ]
}
```

*7.2 Resolve through ancestors — resolution walks up the tree and returns the nearest match*

Resolving a dependency aggregate searches the requesting container first and then walks up its ancestors, returning the nearest aggregate that satisfies the requested type; a type held only by a descendant is not visible to an ancestor. The input assembles a parent and child each holding an aggregate of a different type, then requests several types from both containers; the output reports, per request, the resolved aggregate's label, or a neutral not-found error listing the labels inspected along the ancestor chain when no match exists.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_resolve_through_ancestors.json`

```json
{
    "description": "Resolving a dependency aggregate searches the requesting container first and then walks up its ancestors, returning the nearest aggregate that satisfies the requested type; a type held only by a descendant is not visible to an ancestor. The input assembles a parent and child each holding an aggregate of a different type, then requests several types from both containers; the output reports, per request, the resolved aggregate's label, or a neutral not-found error listing the labels inspected along the ancestor chain when no match exists.",
    "cases": [
        {
            "input": {"action": "di", "scopes": [
                {"id": "p", "parent": null, "component": {"type": "alpha", "id": "parent_component"}},
                {"id": "c", "parent": "p", "component": {"type": "beta", "id": "child_component"}}
            ], "lookups": [
                {"scope": "c", "type": "beta"}, {"scope": "c", "type": "alpha"},
                {"scope": "p", "type": "alpha"}, {"scope": "p", "type": "beta"}
            ]},
            "expected_output": "lookup[c,beta]=component=child_component\nlookup[c,alpha]=component=parent_component\nlookup[p,alpha]=component=parent_component\nlookup[p,beta]=error=component_not_found inspected=[parent_component]\n"
        }
    ]
}
```

*7.[a specific numeric threshold] Unresolved dependency — a missing type yields a neutral not-found error with inspected labels*

Requesting a dependency type that no container along the ancestor chain satisfies raises a neutral not-found error that lists, from nearest to farthest, the labels of the aggregates inspected. The error carries only domain information, never host-language runtime details. The input assembles a parent and child each holding an aggregate, then requests a type none of them satisfies; the output reports the neutral not-found error with the inspected labels in nearest-to-farthest order.

**Test Cases:** `rcb_tests/public_test_cases/feature7_[a specific numeric threshold]_unresolved_component_error.json`

```json
{
    "description": "Requesting a dependency type that no container along the ancestor chain satisfies raises a neutral not-found error that lists, from nearest to farthest, the labels of the aggregates that were inspected. The error carries only domain information, never host-language runtime details. The input assembles a parent and child each holding an aggregate, then requests a type that none of them satisfies; the output reports the neutral not-found error with the inspected aggregate labels in nearest-to-farthest order.",
    "cases": [
        {
            "input": {"action": "di", "scopes": [
                {"id": "p", "parent": null, "component": {"type": "alpha", "id": "parent_component"}},
                {"id": "c", "parent": "p", "component": {"type": "beta", "id": "child_component"}}
            ], "lookups": [{"scope": "c", "type": "unit"}]},
            "expected_output": "lookup[c,unit]=error=component_not_found inspected=[child_component,parent_component]\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

[a specific numeric threshold]. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill([a specific numeric threshold])}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same cancellation sequence as the 'abort' workflow
