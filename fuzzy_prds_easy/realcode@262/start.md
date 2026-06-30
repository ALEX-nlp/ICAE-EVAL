## Product Requirement Document

# Widget-Gallery Source-Code Generator — Deterministic Dart Emission for a Component Showcase

## Project Goal

Build a code-generation library that, given a structured description of a project's annotated widgets, data models, enumerations, and theme accessors, emits the Dart source code for a self-contained "component gallery" application, so developers can preview and tweak their UI components without hand-writing the boilerplate gallery scaffolding for every project.

---

## Background & Problem

Teams that build reusable Flutter components often want a running "gallery" app that lists every component, lets you open a page per component, and lets you live-edit each component's inputs. Hand-writing that gallery — its navigation drawer, its route table, its root app widget, the maps that turn a type name into a constructor, the import block, and so on — is repetitive, error-prone, and must be regenerated whenever components change.

This library is the deterministic core of such a tool. It does not parse source or talk to a build system; it is a set of pure functions that each take an in-memory description (a list of *object descriptors*) and return a string of Dart source. Each descriptor carries a small, fixed set of fields: a `name`, a `category` (e.g. widget, model, enumeration, color, theme), an optional `import` path, and — for widgets and models — a list of constructor/[a specific third-party package name — ask the PM for the exact dependency string] dependencies. Because the emitted source is consumed verbatim by a downstream Flutter app, the exact text each function produces (identifiers, punctuation, indentation, ordering) is the contract: two correct implementations must emit identical output for identical input.

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

Each leaf feature below is a single pure generator: it takes an input description and returns a Dart-source string. The returned string is compared verbatim against the expected output. Every emitted identifier and the surrounding scaffolding text are part of the contract.

### Feature 1: Enumeration Value Registry

**As a developer**, I want a single map literal that lists every enumeration used by my components and binds it to its set of values, so the generated gallery can offer a dropdown of valid choices for any enum-typed input.

**Expected Behavior / Usage:**

The input is a list of model descriptors, each with a `name` and a `category`. The generator emits a Dart map literal assigned to a variable named `framyEnumMap`, typed `<String, List<dynamic>>`. The map is always seeded with one built-in framework enumeration entry (`MaterialTapTargetSize`). Then, for each descriptor whose `category` marks it as an enumeration, one further entry is appended; descriptors of any other category are ignored. Each entry has the form `'<Name>': <Name>.values,` (a quoted string key mapping to the enum's `.values` list). Entries appear on their own lines inside the braces, the seeded entry first, followed by the input-derived entries in input order.

**Test Cases:** `rcb_tests/public_test_cases/feature1_enum_value_map.json`

```json
{
    "description": "Build the enum-value registry map literal from a list of model descriptors. The generator always seeds the map with one built-in framework enum entry, then appends one entry for every descriptor whose category marks it as an enumeration; descriptors of any other category are ignored. Each entry maps the enum's name (as a quoted string key) to that enum's `.values` list.",
    "cases": [
        {
            "input": {"target": "enum_map", "models": []},
            "expected_output": "final framyEnumMap = <String, List<dynamic>>{\n  'MaterialTapTargetSize': MaterialTapTargetSize.values,\n\n};"
        },
        {
            "input": {"target": "enum_map", "models": [{"name": "Foo", "category": "enum"}]},
            "expected_output": "final framyEnumMap = <String, List<dynamic>>{\n  'MaterialTapTargetSize': MaterialTapTargetSize.values,\n'Foo': Foo.values,\n\n};"
        }
    ]
}
```

---

### Feature 2: Import Directive Aggregation

**As a developer**, I want the generated gallery file to declare exactly the imports it needs, so the emitted code compiles without manual import fixing.

**Expected Behavior / Usage:**

The input is a list of source-object descriptors. The generator collects a de-duplicated, insertion-ordered set of import paths and emits one `import '<path>';` line per path, each terminated by a newline. The set always starts with two fixed framework imports (a foundation package, then a material package). Then each descriptor contributes its own `import` path. Finally, if any descriptor is a widget (`category` = widget) that declares at least one [a specific third-party package name — ask the PM for the exact dependency string]-style dependency, an additional [a specific third-party package name — ask the PM for the exact dependency string] package import is appended at the end. Duplicate paths collapse to a single line; first-seen order is preserved.

**Test Cases:** `rcb_tests/public_test_cases/feature2_import_aggregation.json`

```json
{
    "description": "Aggregate the set of import directives required by a generated gallery from a list of source objects. The result always begins with two fixed framework imports, then includes each object's own import path (de-duplicated, first-seen order preserved). If any object is a widget that declares at least one [a specific third-party package name — ask the PM for the exact dependency string]-style dependency, an extra [a specific third-party package name — ask the PM for the exact dependency string] package import is appended. Output is one `import '...';` line per path.",
    "cases": [
        {
            "input": {"target": "imports", "objects": []},
            "expected_output": "import 'package:flutter/foundation.dart';\nimport 'package:flutter/material.dart';\n"
        },
        {
            "input": {"target": "imports", "objects": [{"import": "package:my_app/theme.dart"}]},
            "expected_output": "import 'package:flutter/foundation.dart';\nimport 'package:flutter/material.dart';\nimport 'package:my_app/theme.dart';\n"
        }
    ]
}
```

---

### Feature 3: Route-Table Factory

**As a developer**, I want a route-resolving function that maps each gallery page name to its widget, so the gallery can navigate between the built-in pages and one page per custom component.

**Expected Behavior / Usage:**

The input is a list of object descriptors. The generator emits an `onGenerateRoute` function whose body builds a `routes` map. The map always contains four fixed built-in routes — `'/typography'`, `'/colors'`, `'/appbar'`, `'/button'` — each mapped to its corresponding built-in page widget constructor. Then, for every descriptor whose `category` marks it as a widget, one additional entry is inserted with key `'/<WidgetName>'` mapping to `Framy<WidgetName>CustomPage()`. The function then looks up the requested route name, falling back to the typography page when unknown, and returns a page-route builder that wraps the resolved page in a shared layout template. Non-widget descriptors contribute no routes.

**Test Cases:** `rcb_tests/public_test_cases/feature3_route_table.json`

```json
{
    "description": "Generate the route-table factory function for the gallery. The output is an `onGenerateRoute` function whose route map always contains four fixed built-in routes (typography, colors, app bar, button pages); for every object whose category marks it as a widget, an additional route keyed by `'/<WidgetName>'` mapping to a `Framy<WidgetName>CustomPage()` is inserted. Unknown route names fall back to the typography page, and every route is wrapped in a page-route builder around a shared layout template.",
    "cases": [
        {
            "input": {"target": "routing", "objects": []},
            "expected_output": "Route onGenerateRoute(RouteSettings settings) {\n  final routes = {\n    '/typography': FramyFontsPage(),\n    '/colors': FramyColorsPage(),\n    '/appbar': FramyAppBarPage(),\n    '/button': FramyButtonPage(),\n    \n  };\n  final page = routes[settings.name] ?? FramyFontsPage();\n  return PageRouteBuilder<dynamic>(\n    pageBuilder: (_, __, ___) => FramyLayoutTemplate(child: page),\n    settings: settings,\n  );\n}\n"
        },
        {
            "input": {"target": "routing", "objects": [{"name": "MyCustomWidget", "category": "widget"}]},
            "expected_output": "Route onGenerateRoute(RouteSettings settings) {\n  final routes = {\n    '/typography': FramyFontsPage(),\n    '/colors': FramyColorsPage(),\n    '/appbar': FramyAppBarPage(),\n    '/button': FramyButtonPage(),\n    '/MyCustomWidget': FramyMyCustomWidgetCustomPage(),\n  };\n  final page = routes[settings.name] ?? FramyFontsPage();\n  return PageRouteBuilder<dynamic>(\n    pageBuilder: (_, __, ___) => FramyLayoutTemplate(child: page),\n    settings: settings,\n  );\n}\n"
        }
    ]
}
```

---

### Feature 4: Model-Constructor Registry

**As a developer**, I want a map from a type name to a factory that builds a default instance of that type, so the gallery can materialize a custom value for any model-typed input.

**Expected Behavior / Usage:**

The input is a list of model descriptors, each with a `name`, a `category`, and a list of `params` (each parameter has a `name`, a `type`, and a `named` flag). The generator emits a map literal assigned to `framyModelConstructorMap`, typed `<String, dynamic Function(FramyDependencyModel)>`. The map body always begins by spreading the enum registry (mapping every enum type to its first value) and always ends with four primitive fallbacks in this order — string → `''`, double → `0.0`, int → `0`, bool → `false`. In between, for every descriptor whose `category` marks it as a model, one factory entry of the form `'<Name>': (dep) => <Name>( ... ),` is emitted. The constructor call passes, for each declared parameter, the value obtained by looking that parameter up by name in the descriptor's sub-dependencies (`dep.subDependencies.singleWhere((d) => d.name == '<param>').value`); a parameter whose `named` flag is set is prefixed with its `<param>:` label. Descriptors of any other category are skipped entirely.

**Test Cases:** `rcb_tests/public_test_cases/feature4_model_constructor_map.json`

```json
{
    "description": "Generate the model-constructor registry map. The output declares a map from type name to a factory function taking a dependency descriptor. It always spreads the enum registry (each enum mapped to its first value), ends with four primitive fallbacks (string, double, int, bool with their zero values), and in between emits one factory per descriptor whose category marks it as a model. Each model factory constructs the model by passing, for every declared parameter, the value looked up from the descriptor's sub-dependencies by that parameter's name; named parameters are emitted with their `name:` label. Descriptors of any other category are skipped.",
    "cases": [
        {
            "input": {"target": "model_constructor_map", "models": []},
            "expected_output": "final framyModelConstructorMap =\n    <String, dynamic Function(FramyDependencyModel)>{\n  ...framyEnumMap.map((type, values) => MapEntry(type, (FramyDependencyModel dep) => values.first)),\n  \n  'String': (dep) => '',\n  'double': (dep) => 0.0,\n  'int': (dep) => 0,\n  'bool': (dep) => false,\n};\n"
        },
        {
            "input": {"target": "model_constructor_map", "models": [{"name": "User", "category": "model", "params": [{"name": "firstName", "type": "String", "named": false}]}]},
            "expected_output": "final framyModelConstructorMap =\n    <String, dynamic Function(FramyDependencyModel)>{\n  ...framyEnumMap.map((type, values) => MapEntry(type, (FramyDependencyModel dep) => values.first)),\n  'User': (dep) => User(\n    dep.subDependencies.singleWhere((d) => d.name == 'firstName').value,\n),\n\n  'String': (dep) => '',\n  'double': (dep) => 0.0,\n  'int': (dep) => 0,\n  'bool': (dep) => false,\n};\n"
        }
    ]
}
```

---

### Feature 5: Root Application Widget With Optional Theme Accessor

**As a developer**, I want the generated root app widget to optionally wire in my project's theme, referencing it exactly the way it is declared (top-level function, static/instance method, or property), so the gallery renders with my theme without me editing generated code.

**Expected Behavior / Usage:**

The input optionally carries a single theme *accessor* descriptor. The generator emits a `FramyApp` stateless widget whose `build` returns a `MaterialApp` with a fixed key `Key('FramyApp')` and an `onGenerateRoute: onGenerateRoute` argument. Between them sits a `theme:` argument that depends on the accessor:

- When no accessor is supplied, no theme value is produced (the slot is blank).
- When an accessor is supplied, the `theme:` argument references it as `theme: <ref>,`, where `<ref>` is built as `[owner-prefix]<name>[()]`:
  - `<name>` is the accessor's identifier.
  - The optional `owner` prefix is `<Owner>.` when the accessor is `static`, or `<Owner>().` when it is an instance member; it is omitted entirely when there is no owner.
  - A trailing `()` is appended only when the accessor is `invokable` (a callable such as a function or method); it is omitted when the accessor is a readable property.

So a static top-level callable named `getThemeData` renders as `getThemeData()`; an instance method `getThemeData` on owner `CustomAppTheme` renders as `CustomAppTheme().getThemeData()`; the same method as static renders as `CustomAppTheme.getThemeData()`; and an instance property `theme` on `CustomAppTheme` renders as `CustomAppTheme().theme`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_root_app_widget.json`

```json
{
    "description": "Generate the root application widget. The output is a `FramyApp` stateless widget returning a `MaterialApp` with a fixed key and an `onGenerateRoute` hook. An optional theme accessor controls a `theme:` argument: when none is supplied no theme line is emitted; when supplied, the accessor is rendered as a reference of the form `[owner-prefix]name[()]`, where the owner prefix is `Owner.` for a static accessor or `Owner().` for an instance accessor (absent when there is no owner), and a trailing `()` is appended only when the accessor is callable rather than a readable property.",
    "cases": [
        {
            "input": {"target": "framy_app"},
            "expected_output": "class FramyApp extends StatelessWidget {\n  @override\n  Widget build(BuildContext context) {\n    return MaterialApp(\n      key: Key('FramyApp'),\n      \n      onGenerateRoute: onGenerateRoute,\n    );\n  }\n}\n"
        },
        {
            "input": {"target": "framy_app", "theme": {"name": "getThemeData", "static": true, "invokable": true}},
            "expected_output": "class FramyApp extends StatelessWidget {\n  @override\n  Widget build(BuildContext context) {\n    return MaterialApp(\n      key: Key('FramyApp'),\n      theme: getThemeData(),\n      onGenerateRoute: onGenerateRoute,\n    );\n  }\n}\n"
        },
        {
            "input": {"target": "framy_app", "theme": {"name": "getThemeData", "owner": "CustomAppTheme", "static": false, "invokable": true}},
            "expected_output": "class FramyApp extends StatelessWidget {\n  @override\n  Widget build(BuildContext context) {\n    return MaterialApp(\n      key: Key('FramyApp'),\n      theme: CustomAppTheme().getThemeData(),\n      onGenerateRoute: onGenerateRoute,\n    );\n  }\n}\n"
        }
    ]
}
```

---

### Feature 6: JSON Fragment Concatenation Normalizer

**As a developer**, I want two separately-emitted JSON array fragments that were concatenated into one stream to be flattened into a single array, so a multi-source build that appends array fragments yields one valid combined array instead of two adjacent ones.

**Expected Behavior / Usage:**

The input is a single string. Whenever the string contains the boundary between two back-to-back array fragments — a closing bracket on its own line, immediately followed by a blank-line gap, immediately followed by a fresh opening bracket on its own line — that exact boundary is collapsed so the closing/opening pair is replaced by an element separator, joining the two element lists into one array. A string that contains no such boundary (for example a single fragment) is returned completely unchanged. Only that specific bracket-gap-bracket boundary is affected; all other characters, indentation, and trailing content are preserved verbatim.

**Test Cases:** `rcb_tests/public_test_cases/feature6_json_fragment_merge.json`

```json
{
    "description": "Normalize a concatenation of independently-emitted JSON array fragments into a single array. When two array fragments are written back-to-back, the boundary where one array closes and the next opens (a closing bracket on its own line followed by a blank-line gap and a fresh opening bracket) is collapsed so the two element lists become one combined list. A single fragment with no such boundary is returned unchanged.",
    "cases": [
        {
            "input": {"target": "fix_json", "json": "[\n  {\n    \"name\": \"TestWidget\",\n  }\n]"},
            "expected_output": "[\n  {\n    \"name\": \"TestWidget\",\n  }\n]"
        },
        {
            "input": {"target": "fix_json", "json": "[\n  {\n    \"name\": \"TestWidget\",\n  }\n]\n\n[\n  {\n    \"name\": \"TestWidget\",\n  }\n]"},
            "expected_output": "[\n  {\n    \"name\": \"TestWidget\",\n  },\n  {\n    \"name\": \"TestWidget\",\n  }\n]"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the generators described above. Its physical structure MUST strictly align with the "Scale-Driven Code Organization" constraint. The core generators must be pure functions over in-memory descriptors and must be decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (entry point) that acts as a client to the core generators — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and writes the generated source string to stdout, matching the per-feature contracts above. The request's `target` field selects the generator: `enum_map`, `imports`, `routing`, `model_constructor_map`, `framy_app`, and `fix_json`. Object/model descriptors are supplied under `models`/`objects`, the optional theme accessor under `theme`, and the raw string for the normalizer under `json`. Any failure must be rendered as a language-neutral `error=<category>` line rather than leaking a host-runtime trace.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same lookup logic used for resolving sub-dependencies in the model injection module
- format the theme argument using the standard dynamic accessor pattern defined in the theme system module
