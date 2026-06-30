## Product Requirement Document

# Component Route Access Guard - Declarative Authorization for Routed UI Components

## Project Goal

Build a route access guard library for component-based applications that allows developers to protect routed UI components, redirect unauthorized navigation, and pass authorized session context to protected content without writing repetitive route-level authorization boilerplate.

---

## Background & Problem

Without this library/tool, developers are forced to manually check session state in each protected route, trigger redirects, preserve attempted URLs, handle pending authentication, and forward route and session data to protected components. This leads to duplicated control flow, inconsistent redirect behavior, and fragile handling of nested routes or profile-based authorization rules.

With this library/tool, developers define reusable access policies around routed components. The guard observes session state and route context, renders loading or protected content as appropriate, and emits router-visible redirects with consistent return-location behavior.

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

### Feature 1: Unauthenticated Route Redirect

**As a developer**, I want to protect private routes from visitors without a usable session, so I can send them to a safe public destination while preserving where they tried to go.

**Expected Behavior / Usage:**

The input describes a route navigation flow using a configured access policy and a sequence of events. When a visitor without an authorized session enters a protected route, the output must report the router-visible final path, final search string, and rendered route target. The final path must be the configured failure destination, and the search string must contain the attempted route encoded as the return-location parameter, including any original query string.

**Test Cases:** `rcb_tests/public_test_cases/feature1_redirect_unauthenticated.json`

```json
{
  "description": "A protected route redirects an unauthenticated visitor to the login route and records the attempted URL in a query parameter.",
  "cases": [
    {
      "input": {
        "flow": "route_flow",
        "policy": "requires_session",
        "events": [
          {
            "type": "visit",
            "url": "/auth"
          }
        ]
      },
      "expected_output": "step=0\nevent=visit:/auth\npath=[a specific path prefix — verify against the website configuration section]\nsearch=?[the standard query parameter for redirects]%2Fauth\nrendered=target\n"
    },
    {
      "input": {
        "flow": "route_flow",
        "policy": "requires_session",
        "events": [
          {
            "type": "visit",
            "url": "/auth?test=foo"
          }
        ]
      },
      "expected_output": "step=0\nevent=visit:/auth?test=foo\npath=[a specific path prefix — verify against the website configuration section]\nsearch=?[the standard query parameter for redirects]%2Fauth%3Ftest%3Dfoo\nrendered=target\n"
    }
  ]
}
```

---

### Feature 2: Pending Authentication Rendering

**As a developer**, I want to show an in-progress authentication state without treating it as an authorization failure, so I can avoid redirecting users before the authentication attempt has finished.

**Expected Behavior / Usage:**

The input describes navigation to a protected route while authentication is considered pending. The router-visible path must remain on the attempted protected route with an empty search string. If a loading view is configured, the rendered signal must identify that loading view; if no loading view is configured, the rendered signal must identify the empty placeholder and report that no props were passed to that placeholder.

**Test Cases:** `rcb_tests/public_test_cases/feature2_pending_authentication.json`

```json
{
  "description": "While authentication is still pending, the guarded route remains active and renders either the configured loading view or the default empty placeholder instead of redirecting.",
  "cases": [
    {
      "input": {
        "flow": "route_flow",
        "policy": "pending_custom_loading",
        "events": [
          {
            "type": "visit",
            "url": "/alwaysAuth"
          }
        ]
      },
      "expected_output": "step=0\nevent=visit:/alwaysAuth\npath=/alwaysAuth\nsearch=\nrendered=loading\n"
    },
    {
      "input": {
        "flow": "route_flow",
        "policy": "pending_default_loading",
        "events": [
          {
            "type": "visit",
            "url": "/alwaysAuthDef"
          }
        ]
      },
      "expected_output": "step=0\nevent=visit:/alwaysAuthDef\npath=/alwaysAuthDef\nsearch=\nrendered=empty\nplaceholder_props={}\n"
    }
  ]
}
```

---

### Feature 3: Session State Change Handling

**As a developer**, I want to react to session changes after a guarded route has mounted, so I can keep protected screens synchronized with the current authorization state.

**Expected Behavior / Usage:**

The input is an ordered event stream containing session changes and route visits. A valid session must allow navigation to the protected route and render protected content. If a session is removed while a protected route is active, or if an in-progress authentication attempt ends without an authorized session, the output must show a redirect to the failure destination and preserve the protected route in the return-location query.

**Test Cases:** `rcb_tests/public_test_cases/feature3_session_state_changes.json`

```json
{
  "description": "A protected route allows a valid session, and if the session later becomes missing or authentication finishes unsuccessfully, the active route changes to the login route.",
  "cases": [
    {
      "input": {
        "flow": "route_flow",
        "policy": "requires_session",
        "events": [
          {
            "type": "login"
          },
          {
            "type": "visit",
            "url": "/auth"
          }
        ]
      },
      "expected_output": "step=0\nevent=login\npath=/\nsearch=\nrendered=empty\nstep=1\nevent=visit:/auth\npath=/auth\nsearch=\nrendered=target\n"
    },
    {
      "input": {
        "flow": "route_flow",
        "policy": "requires_session",
        "events": [
          {
            "type": "login"
          },
          {
            "type": "visit",
            "url": "/auth"
          },
          {
            "type": "logout"
          }
        ]
      },
      "expected_output": "step=0\nevent=login\npath=/\nsearch=\nrendered=empty\nstep=1\nevent=visit:/auth\npath=/auth\nsearch=\nrendered=target\nstep=2\nevent=logout\npath=[a specific path prefix — verify against the website configuration section]\nsearch=?[the standard query parameter for redirects]%2Fauth\nrendered=target\n"
    },
    {
      "input": {
        "flow": "route_flow",
        "policy": "requires_session",
        "events": [
          {
            "type": "start_authentication"
          },
          {
            "type": "visit",
            "url": "/auth"
          },
          {
            "type": "logout"
          }
        ]
      },
      "expected_output": "step=0\nevent=start_authentication\npath=/\nsearch=\nrendered=empty\nstep=1\nevent=visit:/auth\npath=/auth\nsearch=\nrendered=empty\nstep=2\nevent=logout\npath=[a specific path prefix — verify against the website configuration section]\nsearch=?[the standard query parameter for redirects]%2Fauth\nrendered=target\n"
    }
  ]
}
```

---

### Feature 4: Profile-Based Authorization Rules

**As a developer**, I want to authorize a route using fields from the selected session profile, so I can express access rules beyond simple login presence.

**Expected Behavior / Usage:**

The input supplies session profile values and a route visit under a policy that checks a profile field. A nonmatching profile must leave the router at the policy failure destination with the denied URL recorded in the query string, and a later matching profile must allow the protected route and render protected content.

**Test Cases:** `rcb_tests/public_test_cases/feature4_predicate_authorization.json`

```json
{
  "description": "Custom authorization rules may inspect session profile fields, deny mismatches with a redirect, and allow matching profiles to stay on the guarded route.",
  "cases": [
    {
      "input": {
        "flow": "route_flow",
        "policy": "first_name_rule",
        "events": [
          {
            "type": "login",
            "first_name": "NotTest",
            "last_name": "McDuderson"
          },
          {
            "type": "visit",
            "url": "/testOnly"
          },
          {
            "type": "login",
            "first_name": "Test",
            "last_name": "McDuderson"
          },
          {
            "type": "visit",
            "url": "/testOnly"
          }
        ]
      },
      "expected_output": "step=0\nevent=login\npath=/\nsearch=\nrendered=empty\nstep=1\nevent=visit:/testOnly\npath=/\nsearch=?[the standard query parameter for redirects]%2FtestOnly\nrendered=empty\nstep=2\nevent=login\npath=/\nsearch=?[the standard query parameter for redirects]%2FtestOnly\nrendered=empty\nstep=3\nevent=visit:/testOnly\npath=/testOnly\nsearch=\nrendered=target\n"
    }
  ]
}
```

---

### Feature 5: Redirect-Back Suppression

**As a developer**, I want to disable return-location recording for routes that should not reveal or reuse the attempted URL, so I can send denied users to the failure destination without extra redirect metadata.

**Expected Behavior / Usage:**

The input describes a denied route whose policy suppresses redirect-back information. The output must show the configured failure path with an empty search string and no protected content rendered, even though the denied route was attempted after a session event.

**Test Cases:** `rcb_tests/public_test_cases/feature5_redirect_back_options.json`

```json
{
  "description": "Redirect behavior can omit the return-location query value when configured to hide the attempted guarded URL.",
  "cases": [
    {
      "input": {
        "flow": "route_flow",
        "policy": "no_redirect_back",
        "events": [
          {
            "type": "login"
          },
          {
            "type": "visit",
            "url": "/hidden"
          }
        ]
      },
      "expected_output": "step=0\nevent=login\npath=/\nsearch=\nrendered=empty\nstep=1\nevent=visit:/hidden\npath=/\nsearch=\nrendered=empty\n"
    }
  ]
}
```

---

### Feature 6: Composed Authorization Layers

**As a developer**, I want to combine multiple independent authorization layers on one protected route, so I can require every layer to approve before protected content appears.

**Expected Behavior / Usage:**

The input provides a sequence of session profiles and visits to a route protected by two stacked rules. If either rule rejects the profile, the output must show the failure destination and the attempted URL in the query. Only when both profile conditions match may the router remain on the protected route and render the protected target.

**Test Cases:** `rcb_tests/public_test_cases/feature6_composed_authorization.json`

```json
{
  "description": "Multiple guarded layers on the same route must all authorize the session before the protected content is rendered.",
  "cases": [
    {
      "input": {
        "flow": "route_flow",
        "policy": "two_nested_name_rules",
        "events": [
          {
            "type": "login",
            "first_name": "NotTest",
            "last_name": "McDuderson"
          },
          {
            "type": "visit",
            "url": "/testMcDudersonOnly"
          },
          {
            "type": "login",
            "first_name": "Test",
            "last_name": "NotMcDuderson"
          },
          {
            "type": "visit",
            "url": "/testMcDudersonOnly"
          },
          {
            "type": "login",
            "first_name": "Test",
            "last_name": "McDuderson"
          },
          {
            "type": "visit",
            "url": "/testMcDudersonOnly"
          }
        ]
      },
      "expected_output": "step=0\nevent=login\npath=/\nsearch=\nrendered=empty\nstep=1\nevent=visit:/testMcDudersonOnly\npath=/\nsearch=?[the standard query parameter for redirects]%2FtestMcDudersonOnly\nrendered=empty\nstep=2\nevent=login\npath=/\nsearch=?[the standard query parameter for redirects]%2FtestMcDudersonOnly\nrendered=empty\nstep=3\nevent=visit:/testMcDudersonOnly\npath=/\nsearch=?[the standard query parameter for redirects]%2FtestMcDudersonOnly\nrendered=empty\nstep=4\nevent=login\npath=/\nsearch=?[the standard query parameter for redirects]%2FtestMcDudersonOnly\nrendered=empty\nstep=5\nevent=visit:/testMcDudersonOnly\npath=/testMcDudersonOnly\nsearch=\nrendered=target\n"
    }
  ]
}
```

---

### Feature 7: Nested Route Protection

**As a developer**, I want to protect parent and child routes while preserving the full nested URL, so I can enforce authorization consistently across route hierarchies.

**Expected Behavior / Usage:**

The input navigates to a nested protected route, changes session state, revisits the nested route, and then removes the session. Unauthorized access must redirect to the failure path with the full nested URL encoded in the return-location query. Authorized access must allow the full nested path and render the protected route target. Losing authorization from the nested route must redirect again with the same full nested URL preserved.

**Test Cases:** `rcb_tests/public_test_cases/feature7_nested_routes.json`

```json
{
  "description": "Guarded parent and child routes preserve the full nested URL when redirecting and allow the nested content when a valid session exists.",
  "cases": [
    {
      "input": {
        "flow": "route_flow",
        "policy": "nested_parent_child",
        "events": [
          {
            "type": "visit",
            "url": "/parent/child"
          },
          {
            "type": "login"
          },
          {
            "type": "visit",
            "url": "/parent/child"
          },
          {
            "type": "logout"
          }
        ]
      },
      "expected_output": "step=0\nevent=visit:/parent/child\npath=[a specific path prefix — verify against the website configuration section]\nsearch=?[the standard query parameter for redirects]%2Fparent%2Fchild\nrendered=target\nstep=1\nevent=login\npath=[a specific path prefix — verify against the website configuration section]\nsearch=?[the standard query parameter for redirects]%2Fparent%2Fchild\nrendered=target\nstep=2\nevent=visit:/parent/child\npath=/parent/child\nsearch=\nrendered=target\nstep=3\nevent=logout\npath=[a specific path prefix — verify against the website configuration section]\nsearch=?[the standard query parameter for redirects]%2Fparent%2Fchild\nrendered=target\n"
    }
  ]
}
```

---

### Feature 8: Protected Component Input Propagation

**As a developer**, I want to deliver route context, selected session data, and parent-supplied values to authorized protected content, so I can let protected components behave like normal routed components after access is granted.

**Expected Behavior / Usage:**

The input requests a successful protected render. The output must include the final router path and search string, the rendered protected target signal, the route path received by the protected target, selected session fields received by the target, and the parent-supplied boolean flag received by the target.

**Test Cases:** `rcb_tests/public_test_cases/feature8_protected_component_props.json`

```json
{
  "description": "When authorization succeeds, the protected component receives router props, selected session data, and props supplied by its parent.",
  "cases": [
    {
      "input": {
        "flow": "rendered_props"
      },
      "expected_output": "path=/prop\nsearch=\nrendered=target\nreceived_route_path=/prop\nreceived_auth_email=test@test.com\nreceived_auth_first_name=Test\nreceived_auth_last_name=McDuderson\nreceived_parent_flag=true\n"
    }
  ]
}
```

---

### Feature 9: Component Metadata Preservation

**As a developer**, I want to preserve metadata and callable fields attached to a protected component, so I can allow downstream code to use the guarded component without losing static information.

**Expected Behavior / Usage:**

The input requests wrapping a component that has attached metadata and a callable field. The output must report that the metadata flag is present, that the callable field is still callable, and that invoking it returns its original wire-format value.

**Test Cases:** `rcb_tests/public_test_cases/feature9_component_metadata.json`

```json
{
  "description": "Metadata and callable fields attached to a protected component remain available on the guarded component returned by the wrapper.",
  "cases": [
    {
      "input": {
        "flow": "static_metadata"
      },
      "expected_output": "static_flag=true\nstatic_function_type=function\nstatic_function_result=auth\n"
    }
  ]
}
```

---

### Feature 10: Route-Entry Guard Redirect

**As a developer**, I want to enforce authorization before a route is activated, so I can block unauthorized transitions at route-entry time using the same redirect contract as rendered guards.

**Expected Behavior / Usage:**

The input invokes a route-entry guard for an unauthorized route transition. The output must report the router-visible failure path, the return-location query containing the denied entry URL, and the rendered public route target.

**Test Cases:** `rcb_tests/public_test_cases/feature10_entry_guard.json`

```json
{
  "description": "The route-entry guard can be used before route activation and redirects unauthorized navigation using the same return-location query behavior.",
  "cases": [
    {
      "input": {
        "flow": "entry_guard"
      },
      "expected_output": "path=[a specific path prefix — verify against the website configuration section]\nsearch=?[the standard query parameter for redirects]%2FonEnter\nrendered=target\n"
    }
  ]
}
```

---

### Feature 11: Route-Parameter-Aware Authorization

**As a developer**, I want to combine selected session data with route parameters when deciding access, so I can make authorization depend on the concrete route instance being visited.

**Expected Behavior / Usage:**

The input supplies session state and a route visit containing a route parameter. When the selected session data and route parameter satisfy the policy, the output must remain on the parameterized protected route and render protected content. When the parameter does not satisfy the policy, the output must show a redirect to the failure path with the denied parameterized URL encoded in the query.

**Test Cases:** `rcb_tests/public_test_cases/feature11_route_parameter_policy.json`

```json
{
  "description": "Authorization decisions can combine selected session data with route parameters supplied by the router.",
  "cases": [
    {
      "input": {
        "flow": "route_parameter_policy",
        "events": [
          {
            "type": "login"
          },
          {
            "type": "visit",
            "url": "/ownProps/1"
          }
        ]
      },
      "expected_output": "path=/ownProps/1\nsearch=\nrendered=target\n"
    },
    {
      "input": {
        "flow": "route_parameter_policy",
        "events": [
          {
            "type": "login"
          },
          {
            "type": "visit",
            "url": "/ownProps/2"
          }
        ]
      },
      "expected_output": "path=[a specific path prefix — verify against the website configuration section]\nsearch=?[the standard query parameter for redirects]%2FownProps%2F2\nrendered=target\n"
    }
  ]
}
```

---

### Feature 12: Dynamic Failure Destination

**As a developer**, I want to choose the failure destination from current state and route parameters, so I can send different denied route instances to different public destinations.

**Expected Behavior / Usage:**

The input visits parameterized protected routes under a policy whose failure destination is computed from the current state and route parameters. The output must show the computed failure path for each parameter value and must still include the denied URL in the return-location query.

**Test Cases:** `rcb_tests/public_test_cases/feature12_dynamic_failure_destination.json`

```json
{
  "description": "The failure destination can be selected dynamically from current state and route parameters while still preserving the denied URL in the redirect query.",
  "cases": [
    {
      "input": {
        "flow": "dynamic_failure_destination",
        "events": [
          {
            "type": "visit",
            "url": "/ownProps/1"
          }
        ]
      },
      "expected_output": "path=[a specific path prefix — verify against the website configuration section]/1\nsearch=?[the standard query parameter for redirects]%2FownProps%2F1\nrendered=target\n"
    },
    {
      "input": {
        "flow": "dynamic_failure_destination",
        "events": [
          {
            "type": "visit",
            "url": "/ownProps/2"
          }
        ]
      },
      "expected_output": "path=[a specific path prefix — verify against the website configuration section]/0\nsearch=?[the standard query parameter for redirects]%2FownProps%2F2\nrendered=target\n"
    }
  ]
}
```

---

### Feature 13: Redirect Dispatch Semantics

**As a developer**, I want to support framework-native redirects and avoid duplicate redirects when authorization state has not changed, so I can integrate with routing infrastructure without repeated side effects.

**Expected Behavior / Usage:**

The input either navigates through a guard that uses router context for redirects or mounts a denied guard with a redirect action counter. Router-context redirects must produce the same final path, search string, and rendered public target as action-based redirects. A denied guard must trigger one redirect when mounted, and a later state update that does not change authorization from denied to allowed must not increase the redirect count.

**Test Cases:** `rcb_tests/public_test_cases/feature13_redirect_mechanisms.json`

```json
{
  "description": "Redirects work through router context when no explicit dispatch action is supplied, and unchanged authorization state does not trigger duplicate redirect actions after mount.",
  "cases": [
    {
      "input": {
        "flow": "route_flow",
        "policy": "context_router_redirect",
        "events": [
          {
            "type": "visit",
            "url": "/noaction"
          }
        ]
      },
      "expected_output": "step=0\nevent=visit:/noaction\npath=[a specific path prefix — verify against the website configuration section]\nsearch=?[the standard query parameter for redirects]%2Fnoaction\nrendered=target\n"
    },
    {
      "input": {
        "flow": "single_redirect"
      },
      "expected_output": "redirect_calls_after_mount=1\nredirect_calls_after_auth_change=1\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_redirect_unauthenticated.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_redirect_unauthenticated@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.
