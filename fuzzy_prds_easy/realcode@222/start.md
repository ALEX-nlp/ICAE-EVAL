## Product Requirement Document

# Annotation-Driven Dependency-Injection Contribution & Merge Processor

## Project Goal

Build a compile-time processor, exercised through a single batch program, that turns
ordinary annotated Kotlin source into the wiring needed by a dependency-injection
graph. Modules annotate interfaces, implementations, subcomponents and custom markers;
the processor **generates** the per-contribution glue and, at the application root,
**merges** every contribution that targets a scope into one component.

The program is a black box driven entirely by text. It accepts a JSON command on
standard input describing a set of Kotlin source files plus what to inspect, runs the
symbol-processing pipeline, and prints a small, deterministic, language-neutral report
on standard output. The report either describes the generated symbols (origins,
providers, merged super-interfaces, discovery markers) or, when the input is invalid,
a normalized domain reason. No part of the report leaks host-language types, stack
traces, or file-system paths.

## Background & Problem

In a modular code base each feature module wants to register its own dependencies —
component interfaces, concrete bindings, child scopes — without the root module having
to know about every one of them by hand. Maintaining one giant hand-written wiring
file at the root is brittle: every new module forces an edit there, and a typo only
surfaces at runtime.

The standard solution is *contribution + merge*. A module annotates a declaration to
say "this belongs to scope X". The processor emits a small discoverable stub for each
contribution into a well-known lookup package. At the root, a component annotated to
merge scope X collects every stub for that scope and folds them into a single generated
super-interface, so the fully wired graph is assembled automatically across module
boundaries.

Because this is a code generator, its behavior is easy to get subtly wrong and hard to
test portably. We therefore need a contract that is independent of any host language or
test framework: drive the processor with source snippets and assert on a stable textual
description of what it generated, or on the normalized reason it rejected the input.

## Architecture & Engineering Constraints

**Interface.** The program runs in a batch loop. For each command it reads one JSON
object and writes one text report. The command schema is:

- `sources` (required, array of strings): each string is the full text of one Kotlin
  source file to compile together.
- `inspect` (optional, array of fully-qualified type names): for each name, report the
  generated component stub in the lookup package — its recorded origin, the interfaces
  it extends, and any provider methods it declares.
- `merged` (optional, array of fully-qualified component names): for each name, report
  which user-package contributions ended up merged into that component's generated
  super-interface.
- `annotation` (optional, array of fully-qualified annotation names): for each name,
  report the generated cross-module discovery marker for that custom annotation.
- `multiplatform` (optional, boolean): compile in common Kotlin-Multiplatform mode.

**Output grammar.** Lines are emitted in a fixed order and any repeatable group is
sorted, so output is deterministic:

- On success the first line is `status=compiled`. Then, per inspected type:
  - `contribution origin=<fqn>` — the declaration the stub was generated from.
  - `extends <fqn>` — each super-interface of the stub (sorted).
  - `provides from=<fqn|none> to=<fqn> kind=<single|multi>` — each provider method:
    where the value comes from, the bound type it is exposed as, and whether it is a
    single binding or a set-multibinding element (sorted).
  - per merged component: `merges <fqn>` — each contributed user type folded in (sorted).
  - per annotation: `contributing-annotation origin=<fqn>` — the discovery marker.
- On rejection the output is `status=rejected`, then `error=invalid_usage`, then one
  `reason=<domain message>` line per distinct diagnostic. Reasons are the processor's
  own domain sentences only; the adapter strips any source location prefix and never
  emits host-language exception class names, stack traces, or paths. An unexpected
  [a specific error category string — consult the internal error taxonomy document] failure is reported as `error=[a specific error category string — consult the internal error taxonomy document]`.

**Constraints.**

- The processor's functional code must not be modified. Behavior is observed only by
  reflecting over the generated classes and by reading the compiler's diagnostics.
- Generated component stubs live in a fixed lookup package; their class names are
  derived deterministically from the fully-qualified source name.
- Nested type names are normalized to dotted form in the report.
- Everything for one run executes inside a single process for speed; the process
  terminates promptly even though the in-process compiler may leave worker threads.

## Core Features

### Feature 1: Contribute a component interface to a scope

A public interface annotated as a scope contribution produces a component-interface
stub in the lookup package whose recorded origin is the source type and which extends
that source interface. A non-public contribution is rejected with a domain reason.

```json
{
  "description": "A public interface annotated as a scope contribution generates a component-interface stub in the lookup package whose origin is the source type and which extends that source interface. Non-public or non-interface declarations are rejected with a domain reason.",
  "cases": [
    {
      "input": {
        "sources": [
          "package com.example\n\nimport software.amazon.lastmile.kotlin.inject.anvil.ContributesTo\n\n@ContributesTo(Unit::class)\ninterface ComponentInterface\n"
        ],
        "inspect": [
          "com.example.ComponentInterface"
        ]
      },
      "expected_output": "status=compiled\ncontribution origin=com.example.ComponentInterface\nextends com.example.ComponentInterface\n"
    },
    {
      "input": {
        "sources": [
          "package com.example\n\nimport software.amazon.lastmile.kotlin.inject.anvil.ContributesTo\n\n@ContributesTo(Unit::class)\nprivate interface ComponentInterface\n"
        ]
      },
      "expected_output": "status=rejected\nerror=invalid_usage\nreason=Contributed component interfaces must be public.\n"
    }
  ]
}
```

### Feature 2: Contribute a binding (single and multibinding)

An injectable implementation annotated as a binding generates a provider exposing it
under its super type. Both the provider direction (implementation → bound type) and the
binding kind (single vs. set-multibinding element) are observable. The bound type must
be unambiguous: an implementation with no super type is rejected.

```json
{
  "description": "An injectable implementation annotated as a binding generates a provider that exposes it under its super type. The provider direction (from implementation to bound type) and the binding kind (single vs multibinding set element) are observable.",
  "cases": [
    {
      "input": {
        "sources": [
          "package com.example\n\nimport software.amazon.lastmile.kotlin.inject.anvil.ContributesBinding\nimport me.tatarka.inject.annotations.Inject\n\ninterface Base\n\n@Inject\n@ContributesBinding(Unit::class)\nclass Impl : Base\n"
        ],
        "inspect": [
          "com.example.Impl"
        ]
      },
      "expected_output": "status=compiled\ncontribution origin=com.example.Impl\nprovides from=com.example.Impl to=com.example.Base kind=single\n"
    },
    {
      "input": {
        "sources": [
          "package com.example\n\nimport software.amazon.lastmile.kotlin.inject.anvil.ContributesBinding\nimport me.tatarka.inject.annotations.Inject\n\ninterface Base\n\n@Inject\n@ContributesBinding(Unit::class, multibinding = true)\nclass Impl : Base\n"
        ],
        "inspect": [
          "com.example.Impl"
        ]
      },
      "expected_output": "status=compiled\ncontribution origin=com.example.Impl\nprovides from=com.example.Impl to=com.example.Base kind=multi\n"
    }
  ]
}
```

```json
{
  "description": "Binding contribution validates the bound type and scope: the bound type must be unambiguous (exactly one super type), the same type may not be bound twice, and all scope-defining annotations must agree.",
  "cases": [
    {
      "input": {
        "sources": [
          "package com.example\n\nimport software.amazon.lastmile.kotlin.inject.anvil.ContributesBinding\nimport me.tatarka.inject.annotations.Inject\n\n@Inject\n@ContributesBinding(Unit::class)\nclass Impl\n"
        ]
      },
      "expected_output": "status=rejected\nerror=invalid_usage\nreason=The bound type could not be determined for Impl. There are no super types.\n"
    }
  ]
}
```

### Feature 3: Merge contributions into a component

A component annotated to merge a scope collects every contribution for that scope; the
generated merged super-interface inherits the contributed component interfaces, proving
they were folded in. A component that is hand-wired with the manual component annotation
but does not declare the generated merged super-interface is rejected.

```json
{
  "description": "A component annotated to merge a scope collects every contribution for that scope; the generated merged super-interface inherits the contributed component interfaces (a nested one and a top-level one), proving the contributions were actually merged into the component.",
  "cases": [
    {
      "input": {
        "sources": [
          "package com.example\n\nimport me.tatarka.inject.annotations.Component\nimport me.tatarka.inject.annotations.Inject\nimport me.tatarka.inject.annotations.Provides\nimport software.amazon.lastmile.kotlin.inject.anvil.AppScope\nimport software.amazon.lastmile.kotlin.inject.anvil.ContributesTo\nimport software.amazon.lastmile.kotlin.inject.anvil.MergeComponent\nimport software.amazon.lastmile.kotlin.inject.anvil.SingleIn\n\ninterface Base\n\n@Inject\n@SingleIn(AppScope::class)\nclass Impl : Base {\n    @ContributesTo(AppScope::class)\n    interface Component {\n        @Provides fun provideImpl(impl: Impl): Base = impl\n        val string: String\n    }\n}\n\n@ContributesTo(AppScope::class)\ninterface StringComponent {\n    @Provides fun provideString(): String = \"abc\"\n}\n\n@Component\n@MergeComponent(AppScope::class)\n@SingleIn(AppScope::class)\nabstract class ComponentInterface : ComponentInterfaceMerged {\n    abstract val base: Base\n}\n"
        ],
        "merged": [
          "com.example.ComponentInterface"
        ]
      },
      "expected_output": "status=compiled\nmerges com.example.Impl.Component\nmerges com.example.StringComponent\n"
    }
  ]
}
```

```json
{
  "description": "Merging validates the wiring: a manually @Component-wired class that merges a scope must add the generated merged super-interface, and excluding a contribution the component still depends on surfaces an unresolved-dependency reason.",
  "cases": [
    {
      "input": {
        "sources": [
          "package com.example\n\nimport me.tatarka.inject.annotations.Component\nimport software.amazon.lastmile.kotlin.inject.anvil.AppScope\nimport software.amazon.lastmile.kotlin.inject.anvil.MergeComponent\n\n@Component\n@MergeComponent(AppScope::class)\nabstract class ComponentInterface\n"
        ]
      },
      "expected_output": "status=rejected\nerror=invalid_usage\nreason=ComponentInterface is annotated with @MergeComponent and @Component. It's required to add ComponentInterfaceMerged as super type to ComponentInterface. If you don't want to add the super manually, then you must remove the @Component annotation.\n"
    }
  ]
}
```

### Feature 4: Validate the generated-component factory function

In common Kotlin-Multiplatform code a factory function materializes a merged component.
The processor enforces its shape: it must be public, use the expect modifier, return a
merge target (not a hand-wired component), and — if it has a receiver — that receiver
must be the component's class reference with matching argument and arity. Here a
non-public factory is rejected.

```json
{
  "description": "The common-multiplatform factory function that materializes a merged component has strict shape rules: it must be public and use the expect modifier, its return type must itself be a merge target (not hand-wired with @Component), and a receiver, if present, must be the KClass of the component with matching argument and arity.",
  "cases": [
    {
      "input": {
        "sources": [
          "package com.example\n\nimport software.amazon.lastmile.kotlin.inject.anvil.AppScope\nimport software.amazon.lastmile.kotlin.inject.anvil.MergeComponent\n\n@MergeComponent(AppScope::class)\ninterface ComponentInterface\n\n@MergeComponent.CreateComponent\n[a specific error category string — consult the internal error taxonomy document] expect fun createComponent(): ComponentInterface\n"
        ],
        "multiplatform": true
      },
      "expected_output": "status=rejected\nerror=invalid_usage\nreason=Factory functions for components annotated with `@CreateComponent` must be public.\n"
    }
  ]
}
```

### Feature 5: Contribute a subcomponent with a factory

A contributed subcomponent declares a nested factory interface. The processor generates
a factory component stub in the lookup package whose origin is the factory, which
extends the factory and provides it into the parent scope. The subcomponent must be an
interface; a contributed abstract class is rejected and steered toward the factory.

```json
{
  "description": "A contributed subcomponent declares a nested factory interface; a factory component stub is generated into the lookup package, named after the fully-qualified factory type, whose origin is the factory and which provides the factory into its parent scope.",
  "cases": [
    {
      "input": {
        "sources": [
          "package com.example\n\nimport software.amazon.lastmile.kotlin.inject.anvil.ContributesSubcomponent\nimport software.amazon.lastmile.kotlin.inject.anvil.SingleIn\n\n@ContributesSubcomponent(Unit::class)\n@SingleIn(Unit::class)\ninterface SubcomponentInterface {\n    @ContributesSubcomponent.Factory(String::class)\n    interface Factory {\n        fun createSubcomponentInterface(): SubcomponentInterface\n    }\n}\n"
        ],
        "inspect": [
          "com.example.SubcomponentInterface.Factory"
        ]
      },
      "expected_output": "status=compiled\ncontribution origin=com.example.SubcomponentInterface.Factory\nextends com.example.SubcomponentInterface.Factory\nprovides from=none to=com.example.SubcomponentInterface.Factory kind=single\n"
    }
  ]
}
```

```json
{
  "description": "Subcomponent contribution enforces structural rules: the contributed type must be an interface, it must declare exactly one factory inner interface, the factory must contain exactly one function returning the subcomponent, and a kotlin-inject scope must be present.",
  "cases": [
    {
      "input": {
        "sources": [
          "package com.example\n\nimport software.amazon.lastmile.kotlin.inject.anvil.ContributesSubcomponent\nimport software.amazon.lastmile.kotlin.inject.anvil.SingleIn\n\n@ContributesSubcomponent(Unit::class)\n@SingleIn(Unit::class)\nabstract class OtherComponent {\n    @ContributesSubcomponent.Factory(Unit::class)\n    interface Parent {\n        fun otherComponent(stringArg: String, intArg: Int): OtherComponent\n    }\n}\n"
        ]
      },
      "expected_output": "status=rejected\nerror=invalid_usage\nreason=Only interfaces can be contributed. If you have parameters on your abstract class, then move them to the factory. See @ContributesSubcomponent for more details.\n"
    }
  ]
}
```

### Feature 6: Custom contributing annotations

A user-defined annotation can itself be marked as a contributing annotation. The
processor then generates a cross-module discovery marker for it in the lookup package
whose origin is the annotation, enabling other modules to discover the custom marker.
Such an annotation must be public.

```json
{
  "description": "Marking a user-defined annotation as a contributing annotation is accepted and compiles successfully, generating a cross-module discovery marker for the custom annotation in the lookup package.",
  "cases": [
    {
      "input": {
        "sources": [
          "package com.example\n\nimport software.amazon.lastmile.kotlin.inject.anvil.extend.ContributingAnnotation\nimport kotlin.annotation.AnnotationTarget.CLASS\n\n@ContributingAnnotation\n@Target(CLASS)\nannotation class ContributesRenderer\n"
        ],
        "annotation": [
          "com.example.ContributesRenderer"
        ]
      },
      "expected_output": "status=compiled\ncontributing-annotation origin=com.example.ContributesRenderer\n"
    }
  ]
}
```

```json
{
  "description": "A user-defined annotation marked as contributing must be public; a non-public annotation is rejected with a domain reason.",
  "cases": [
    {
      "input": {
        "sources": [
          "package com.example\n\nimport software.amazon.lastmile.kotlin.inject.anvil.extend.ContributingAnnotation\nimport kotlin.annotation.AnnotationTarget.CLASS\n\n@ContributingAnnotation\n@Target(CLASS)\n[a specific error category string — consult the internal error taxonomy document] annotation class ContributesRenderer\n"
        ]
      },
      "expected_output": "status=rejected\nerror=invalid_usage\nreason=Contributing annotations must be public.\n"
    }
  ]
}
```

## Deliverables

- A single entry point `rcb_tests/test.sh` that runs the whole suite. It accepts
  `--cases-dir <subdir>` (default `test_cases`), feeds every case's `input` to the
  processor, writes only the raw program stdout to
  `rcb_tests/stdout/<cases-dir>/<stem>@<NNN>.txt`, then compares against each case's
  `expected_output` and prints a `PASS`/`FAIL` line per case plus a final summary.
- An execution adapter that drives the unmodified processor in-process and renders the
  text contract defined above, plus its supporting harness scripts.
- The hidden evaluation set `rcb_tests/test_cases/featureN_*.json`, a faithful superset
  of the behaviors above.
- The public mirror `rcb_tests/public_test_cases/featureN_*.json`, containing exactly
  the cases embedded in this document.
- Each case file has the shape `{"description": ..., "cases": [{"input": ...,
  "expected_output": ...}]}`; `input` is real program input and `expected_output` is the
  exact raw stdout.


---
**Implementation notes:**
- follow the same sorting logic used by the module that handles 'extends' lines
- normalize names according to the convention from the core transformation layer
