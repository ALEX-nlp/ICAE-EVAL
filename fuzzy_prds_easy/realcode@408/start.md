## Product Requirement Document

# TypeScript/JavaScript Source-Model Toolkit — Parse, Generate, Index & Normalize

## Project Goal

Build a reusable toolkit that turns TypeScript and JavaScript source text into a structured, language-aware **source model** — and back again. Given a piece of source, the toolkit produces a tree describing the file's imports, exports, declarations (classes, interfaces, enums, functions, variables, type aliases) and nested module/namespace resources, together with the list of identifier names the code references ("usages"). The same model elements can be rendered back to idiomatic source, indexed into a reverse "where is this exported from" map, and supported by small path-normalization helpers. This gives editor tooling, refactoring engines and code-intelligence features one well-defined contract for understanding and emitting code, instead of each consumer re-deriving the structure from a raw compiler AST.

---

## Background & Problem

Editor and refactoring features constantly need to answer structural questions about source files: *What does this file import? What does it export? What classes and methods does it declare, with what visibility and return types? Which identifiers does it reference? Where can a given symbol be imported from across a project?* The raw compiler AST can answer these, but it is verbose, version-sensitive, and awkward to consume directly.

This toolkit defines a compact, stable **source model** layered over the compiler's syntax tree, plus the inverse operation of generating source from model elements, a project-wide **declaration index** that resolves re-exports, and helper routines for normalizing file paths and URIs. The four capabilities together let a consumer parse a file once, reason over a clean model, synthesize new code (e.g. a stubbed method or a fresh import statement), and look up the canonical origin of any exported name.

The toolkit understands four script kinds — `TS`, `TSX`, `JS`, `JSX` — and parses each with the appropriate syntax rules (e.g. JSX elements in `.tsx`/`.jsx`, plain ES classes in `.js`).

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This is a non-trivial domain with several distinct responsibilities (parsing/visiting the syntax tree, the model classes, source generation, the declaration index, and path helpers). It MUST NOT be a single "god file"; output a clear, multi-file directory tree (e.g. `src/` with sub-folders for the model, the parser, the generators, the index) that reflects a production-grade repository. Do not over-engineer, but strictly avoid a monolith here.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in the "Core Features" section are a **black-box testing contract** for an execution adapter, NOT the internal data model of the core system. The core logic (parsing, model, generation, indexing) must be completely decoupled from stdin/stdout and JSON. A thin execution adapter is solely responsible for translating JSON commands into idiomatic calls on the core API and rendering results back to stdout. You may use a TypeScript compiler library as the underlying syntax-tree provider.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility (SRP):** Separate parsing, the model classes, source generation, the index, validation, and output formatting into distinct units.
   - **Open/Closed (OCP):** Adding a new declaration kind, a new generator, or a new import kind must be possible by extension, not by editing a central switch in many places.
   - **Liskov Substitution (LSP):** All declaration / import / export / resource types must be substitutable through their shared abstractions.
   - **Interface Segregation (ISP):** Keep the model interfaces small and cohesive (e.g. a node that can report a source span, a thing that can be generated).
   - **Dependency Inversion (DIP):** High-level parsing/indexing logic depends on abstractions, not on stdin/stdout details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public API must be elegant and idiomatic TypeScript, hiding the underlying compiler complexity.
   - **Resilience:** Edge cases must be handled gracefully and errors modeled properly (specific error types), surfaced through the adapter as neutral, language-agnostic error lines rather than raw host runtime traces.

---

## The Source Model (shared vocabulary)

Every parse result is a **file** node serialized as JSON with a `kind` discriminator. Containers expose ordered arrays; absent optional fields are omitted entirely. The model uses these `kind` values:

- Containers / resources: `file`, `module`, `namespace`. A resource carries `imports`, `exports`, `declarations`, `resources` (nested) and `usages`.
- Declarations: `class`, `interface`, `enum`, `function`, `variable`, `typeAlias`, `default` (a default-export marker), plus the callable members `method`, `constructor`, `getter`, `setter`, and the data members `property`, `parameter`. Variables local to a callable appear under `variables`.
- Imports: `stringImport` (bare `import 'x'`), `namedImport` (`import {a, b as c} from 'x'`, optionally with a `defaultAlias`), `namespaceImport` (`import * as ns from 'x'`), `externalModuleImport` (`import x = require('x')`). Named-import members are `symbol` specifiers with a `specifier` and optional `alias`.
- Exports: `allExport` (`export * from 'x'`), `namedExport` (`export {a} from 'x'`), `assignedExport` (`export = x` / default assignment).

Common fields: `name`; ordered position fields `start` and `end` (character offsets into the source, present only when the node came from real source — absent for hand-built elements); `isExported`, `isConst`, `isAbstract` booleans where meaningful; `visibility` rendered as the strings `"public"`, `"protected"`, `"private"`; `type` for declared/return types; `members` (string list) for enums. Each resource's `usages` is the ordered, de-duplicated list of referenced identifier names discovered within it.

Parsing is performed against an in-memory source with a fixed virtual filename and root, so offsets and the resulting model are deterministic for a given `source` + `scriptKind`.

---

## Core Features

> The cases embedded below are the authoritative public contract and are mirrored verbatim under `rcb_tests/public_test_cases/`. Each feature maps to exactly one case file. (The full hidden suite under `rcb_tests/test_cases/` exercises the same behaviors with additional inputs.)

### Feature 1: Parse — File Overview

**As a tooling author**, I want a complete structural snapshot of a source file, so I can see its imports, declarations and referenced names at a glance.

**Expected Behavior:** A `parse` request supplies `source` text and a `scriptKind`. The toolkit returns the `file` model: top-level `imports`, `exports`, `declarations`, nested `resources`, and the file-level `usages`. A `new X()` expression contributes both the class declaration and the identifiers it references.

**Test Cases:** `rcb_tests/public_test_cases/feature01_parse_source_overview.json`

```json
{
    "description": "Parse a small mixed TypeScript source string and return the structured source model. The model groups top-level imports, exports, declarations, nested resources, and the flat list of referenced identifier names (usages). Each node carries its source character span (start/end).",
    "cases": [
        {
            "input": {
                "action": "parse",
                "source": "import {foo} from 'bar'; class Foobar {}; const bar = new Foobar();",
                "scriptKind": "TS"
            },
            "expected_output": "{\n  \"kind\": \"file\",\n  \"imports\": [\n    {\n      \"kind\": \"namedImport\",\n      \"libraryName\": \"bar\",\n      \"specifiers\": [\n        {\n          \"specifier\": \"foo\"\n        }\n      ],\n      \"start\": 0,\n      \"end\": 24\n    }\n  ],\n  \"exports\": [],\n  \"declarations\": [\n    {\n      \"kind\": \"class\",\n      \"name\": \"Foobar\",\n      \"isExported\": false,\n      \"accessors\": [],\n      \"properties\": [],\n      \"methods\": [],\n      \"start\": 25,\n      \"end\": 40\n    },\n    {\n      \"kind\": \"variable\",\n      \"name\": \"bar\",\n      \"isConst\": true,\n      \"isExported\": false,\n      \"start\": 42,\n      \"end\": 67\n    }\n  ],\n  \"resources\": [],\n  \"usages\": [\n    \"bar\",\n    \"Foobar\"\n  ]\n}"
        }
    ]
}
```

---

### Feature 2: Parse — Imports

**As a tooling author**, I want every import form recognized and classified, so I know exactly what a file pulls in.

**Expected Behavior:** Each import is modeled by its kind: bare `stringImport`, `namedImport` (with `specifiers`, optional per-specifier `alias`, optional `defaultAlias`), `namespaceImport` (with `alias`), and `externalModuleImport` (`import x = require(...)`). Each carries its `libraryName` and source span.

**Test Cases:** `rcb_tests/public_test_cases/feature02_parse_imports.json`

```json
{
    "description": "Parse the various import syntaxes into typed import nodes: bare string imports, named imports (with and without aliased members), namespace imports, equals/require external-module imports, default imports, mixed default+named imports, and multi-line imports. A malformed default specifier yields no import node.",
    "cases": [
        {
            "input": {
                "action": "parse",
                "source": "import 'sideEffect';\nimport { A, B as C } from 'lib';\nimport * as ns from 'space';\nimport def from 'mod';",
                "scriptKind": "TS"
            },
            "expected_output": "{\n  \"kind\": \"file\",\n  \"imports\": [\n    {\n      \"kind\": \"stringImport\",\n      \"libraryName\": \"sideEffect\",\n      \"start\": 0,\n      \"end\": 20\n    },\n    {\n      \"kind\": \"namedImport\",\n      \"libraryName\": \"lib\",\n      \"specifiers\": [\n        {\n          \"specifier\": \"A\"\n        },\n        {\n          \"specifier\": \"B\",\n          \"alias\": \"C\"\n        }\n      ],\n      \"start\": 21,\n      \"end\": 53\n    },\n    {\n      \"kind\": \"namespaceImport\",\n      \"libraryName\": \"space\",\n      \"alias\": \"ns\",\n      \"start\": 54,\n      \"end\": 82\n    },\n    {\n      \"kind\": \"namedImport\",\n      \"libraryName\": \"mod\",\n      \"defaultAlias\": \"def\",\n      \"specifiers\": [],\n      \"start\": 83,\n      \"end\": 105\n    }\n  ],\n  \"exports\": [],\n  \"declarations\": [],\n  \"resources\": [],\n  \"usages\": []\n}"
        }
    ]
}
```

---

### Feature 3: Parse — Exports

**As a tooling author**, I want re-export statements classified, so I can follow how a file forwards declarations from elsewhere.

**Expected Behavior:** `export * from 'x'` becomes an `allExport`; `export {a} from 'x'` becomes a `namedExport` carrying its specifiers; `export = x` becomes an `assignedExport`. Each carries the relevant `from`/specifier/identifier data and source span.

**Test Cases:** `rcb_tests/public_test_cases/feature03_parse_exports.json`

```json
{
    "description": "Parse export statements into typed export nodes: re-export-all (export * from), named re-export (export { } from) including aliased members, export-assignment (export = X), and a default export (which surfaces as a default declaration).",
    "cases": [
        {
            "input": {
                "action": "parse",
                "source": "export * from './OtherFile';\nexport { Specifier, Specifier as Alias } from './AnotherFile';",
                "scriptKind": "TS"
            },
            "expected_output": "{\n  \"kind\": \"file\",\n  \"imports\": [],\n  \"exports\": [\n    {\n      \"kind\": \"allExport\",\n      \"from\": \"./OtherFile\",\n      \"start\": 0,\n      \"end\": 28\n    },\n    {\n      \"kind\": \"namedExport\",\n      \"from\": \"./AnotherFile\",\n      \"specifiers\": [\n        {\n          \"specifier\": \"Specifier\"\n        },\n        {\n          \"specifier\": \"Specifier\",\n          \"alias\": \"Alias\"\n        }\n      ],\n      \"start\": 29,\n      \"end\": 91\n    }\n  ],\n  \"declarations\": [],\n  \"resources\": [],\n  \"usages\": []\n}"
        }
    ]
}
```

---

### Feature 4: Parse — Enums

**As a tooling author**, I want enum declarations modeled with their members, so I can list the constants a type defines.

**Expected Behavior:** An `enum` declaration carries its `name`, `isExported`, and the ordered list of member names in `members`.

**Test Cases:** `rcb_tests/public_test_cases/feature04_parse_enums.json`

```json
{
    "description": "Parse enum declarations, capturing the enum name, its member names in order, and whether it is exported.",
    "cases": [
        {
            "input": {
                "action": "parse",
                "source": "enum Enumeration {\n    Member1,\n    Member2\n}",
                "scriptKind": "TS"
            },
            "expected_output": "{\n  \"kind\": \"file\",\n  \"imports\": [],\n  \"exports\": [],\n  \"declarations\": [\n    {\n      \"kind\": \"enum\",\n      \"name\": \"Enumeration\",\n      \"isExported\": false,\n      \"members\": [\n        \"Member1\",\n        \"Member2\"\n      ],\n      \"start\": 0,\n      \"end\": 45\n    }\n  ],\n  \"resources\": [],\n  \"usages\": [\n    \"Member1\",\n    \"Member2\"\n  ]\n}"
        }
    ]
}
```

---

### Feature 5: Parse — Type Aliases

**As a tooling author**, I want type-alias declarations modeled, so I can track named type shorthands.

**Expected Behavior:** A `typeAlias` declaration carries its `name` and `isExported` flag.

**Test Cases:** `rcb_tests/public_test_cases/feature05_parse_type_aliases.json`

```json
{
    "description": "Parse type-alias declarations, capturing the alias name and whether it is exported.",
    "cases": [
        {
            "input": {
                "action": "parse",
                "source": "export type ExportedAlias = {};",
                "scriptKind": "TS"
            },
            "expected_output": "{\n  \"kind\": \"file\",\n  \"imports\": [],\n  \"exports\": [],\n  \"declarations\": [\n    {\n      \"kind\": \"typeAlias\",\n      \"name\": \"ExportedAlias\",\n      \"isExported\": true,\n      \"start\": 0,\n      \"end\": 31\n    }\n  ],\n  \"resources\": [],\n  \"usages\": []\n}"
        }
    ]
}
```

---

### Feature 6: Parse — Functions

**As a tooling author**, I want function declarations modeled with their parameters and local variables, so I can reason about callable signatures and bodies.

**Expected Behavior:** A `function` declaration carries `name`, `isExported`, an optional return `type`, the ordered `parameters`, and `variables` declared in its body.

**Test Cases:** `rcb_tests/public_test_cases/feature06_parse_functions.json`

```json
{
    "description": "Parse function declarations, capturing name, exported flag, declared return type (including a type-guard return such as \"str is number\", and undefined when omitted), parameters, and local variables declared inside the body.",
    "cases": [
        {
            "input": {
                "action": "parse",
                "source": "function function1(param1): string {\n    let var1 = 'foobar';\n    return 'foobar';\n}",
                "scriptKind": "TS"
            },
            "expected_output": "{\n  \"kind\": \"file\",\n  \"imports\": [],\n  \"exports\": [],\n  \"declarations\": [\n    {\n      \"kind\": \"function\",\n      \"name\": \"function1\",\n      \"isExported\": false,\n      \"type\": \"string\",\n      \"parameters\": [\n        {\n          \"kind\": \"parameter\",\n          \"name\": \"param1\",\n          \"start\": 19,\n          \"end\": 25\n        }\n      ],\n      \"variables\": [\n        {\n          \"kind\": \"variable\",\n          \"name\": \"var1\",\n          \"isConst\": false,\n          \"isExported\": false,\n          \"start\": 41,\n          \"end\": 61\n        }\n      ],\n      \"start\": 0,\n      \"end\": 84\n    }\n  ],\n  \"resources\": [],\n  \"usages\": [\n    \"param1\",\n    \"var1\"\n  ]\n}"
        }
    ]
}
```

---

### Feature 7: Parse — Variables

**As a tooling author**, I want top-level variable statements modeled, so I can see each declared name, its const-ness, export status and type.

**Expected Behavior:** Each `variable` carries `name`, `isConst`, `isExported`, optional `type`, and a span. A statement declaring multiple names yields multiple nodes.

**Test Cases:** `rcb_tests/public_test_cases/feature07_parse_variables.json`

```json
{
    "description": "Parse top-level variable statements (var/let/const), capturing each variable name, whether it is const, whether it is exported, and its declared type; multiple declarations in one statement produce multiple nodes.",
    "cases": [
        {
            "input": {
                "action": "parse",
                "source": "export const ExportedConst = '';",
                "scriptKind": "TS"
            },
            "expected_output": "{\n  \"kind\": \"file\",\n  \"imports\": [],\n  \"exports\": [],\n  \"declarations\": [\n    {\n      \"kind\": \"variable\",\n      \"name\": \"ExportedConst\",\n      \"isConst\": true,\n      \"isExported\": true,\n      \"start\": 0,\n      \"end\": 32\n    }\n  ],\n  \"resources\": [],\n  \"usages\": [\n    \"ExportedConst\"\n  ]\n}"
        }
    ]
}
```

---

### Feature 8: Parse — Interfaces

**As a tooling author**, I want interface declarations modeled with their properties and methods, so I can reason about a contract's shape.

**Expected Behavior:** An `interface` declaration carries `name`, `isExported`, its `properties` (each a `property` with `name`, `visibility` and `type`) and its `methods` (each a `method` with `name`, `isAbstract`, `visibility`, optional return `type`, `parameters` and `variables`). Method return type is omitted when not annotated.

**Test Cases:** `rcb_tests/public_test_cases/feature08_parse_interfaces.json`

```json
{
    "description": "Parse interface declarations, capturing name, exported flag, generic type parameters, property members (name and type) and method members (name and return type, undefined when omitted).",
    "cases": [
        {
            "input": {
                "action": "parse",
                "source": "interface NonExportedInterface {\n    property1: string;\n    method2(param1: string): void;\n}",
                "scriptKind": "TS"
            },
            "expected_output": "{\n  \"kind\": \"file\",\n  \"imports\": [],\n  \"exports\": [],\n  \"declarations\": [\n    {\n      \"kind\": \"interface\",\n      \"name\": \"NonExportedInterface\",\n      \"isExported\": false,\n      \"properties\": [\n        {\n          \"kind\": \"property\",\n          \"name\": \"property1\",\n          \"visibility\": \"public\",\n          \"type\": \"string\",\n          \"start\": 37,\n          \"end\": 55\n        }\n      ],\n      \"methods\": [\n        {\n          \"kind\": \"method\",\n          \"name\": \"method2\",\n          \"isAbstract\": true,\n          \"visibility\": \"public\",\n          \"type\": \"void\",\n          \"parameters\": [\n            {\n              \"kind\": \"parameter\",\n              \"name\": \"param1\",\n              \"type\": \"string\",\n              \"start\": 68,\n              \"end\": 82\n            }\n          ],\n          \"variables\": [],\n          \"start\": 60,\n          \"end\": 90\n        }\n      ],\n      \"start\": 0,\n      \"end\": 92\n    }\n  ],\n  \"resources\": [],\n  \"usages\": [\n    \"property1\",\n    \"method2\",\n    \"param1\"\n  ]\n}"
        }
    ]
}
```

---

### Feature 9: Parse — Classes

**As a tooling author**, I want class declarations modeled in full, so I can reason about constructors, members, visibility and accessors — including properties introduced by constructor-parameter modifiers.

**Expected Behavior:** A `class` declaration carries `name`, `isExported`, an optional `ctor` (`constructor`), `accessors`, `properties` and `methods`. A constructor parameter with a visibility modifier (e.g. `public param`) ALSO contributes a `property` of the same name/type/visibility. Methods carry `isAbstract`, `visibility`, optional return `type`, `parameters` and local `variables`.

**Test Cases:** `rcb_tests/public_test_cases/feature09_parse_classes.json`

```json
{
    "description": "Parse class declarations, capturing name, exported flag, generic type parameters, the constructor, properties (including those introduced by constructor parameter modifiers), methods (with visibility, abstract flag, return type, parameters and local variables) and get/set accessors.",
    "cases": [
        {
            "input": {
                "action": "parse",
                "source": "class NonExportedClass {\n    constructor(public param1: string) { }\n    protected method2(): void { }\n}",
                "scriptKind": "TS"
            },
            "expected_output": "{\n  \"kind\": \"file\",\n  \"imports\": [],\n  \"exports\": [],\n  \"declarations\": [\n    {\n      \"kind\": \"class\",\n      \"name\": \"NonExportedClass\",\n      \"isExported\": false,\n      \"ctor\": {\n        \"kind\": \"constructor\",\n        \"name\": \"NonExportedClass\",\n        \"parameters\": [\n          {\n            \"kind\": \"parameter\",\n            \"name\": \"param1\",\n            \"type\": \"string\",\n            \"start\": 41,\n            \"end\": 62\n          }\n        ],\n        \"variables\": [],\n        \"start\": 29,\n        \"end\": 67\n      },\n      \"accessors\": [],\n      \"properties\": [\n        {\n          \"kind\": \"property\",\n          \"name\": \"param1\",\n          \"visibility\": \"public\",\n          \"type\": \"string\",\n          \"start\": 41,\n          \"end\": 62\n        }\n      ],\n      \"methods\": [\n        {\n          \"kind\": \"method\",\n          \"name\": \"method2\",\n          \"isAbstract\": false,\n          \"visibility\": \"protected\",\n          \"type\": \"void\",\n          \"parameters\": [],\n          \"variables\": [],\n          \"start\": 72,\n          \"end\": 101\n        }\n      ],\n      \"start\": 0,\n      \"end\": 103\n    }\n  ],\n  \"resources\": [],\n  \"usages\": [\n    \"param1\"\n  ]\n}"
        }
    ]
}
```

---

### Feature 10: Parse — Modules & Namespaces

**As a tooling author**, I want `declare module 'X'` and `declare namespace X` blocks modeled as nested resources, so I can recurse into ambient scopes.

**Expected Behavior:** A `declare namespace X { ... }` becomes a nested `namespace` resource (a `declare module 'X'` likewise becomes a `module` resource), each with its own `imports`, `exports`, `declarations`, nested `resources` and `usages`. The resource's `usages` include its own name.

**Test Cases:** `rcb_tests/public_test_cases/feature10_parse_modules_namespaces.json`

```json
{
    "description": "Parse ambient module (\"declare module 'X'\") and namespace (\"declare namespace X\") blocks into nested sub-resources, each with their own declarations.",
    "cases": [
        {
            "input": {
                "action": "parse",
                "source": "declare namespace Namespace {\n    export enum Exported {\n        MemberA,\n        MemberB\n    }\n}",
                "scriptKind": "TS"
            },
            "expected_output": "{\n  \"kind\": \"file\",\n  \"imports\": [],\n  \"exports\": [],\n  \"declarations\": [],\n  \"resources\": [\n    {\n      \"kind\": \"namespace\",\n      \"name\": \"Namespace\",\n      \"start\": 0,\n      \"end\": 97,\n      \"imports\": [],\n      \"exports\": [],\n      \"declarations\": [\n        {\n          \"kind\": \"enum\",\n          \"name\": \"Exported\",\n          \"isExported\": true,\n          \"members\": [\n            \"MemberA\",\n            \"MemberB\"\n          ],\n          \"start\": 34,\n          \"end\": 95\n        }\n      ],\n      \"resources\": [],\n      \"usages\": [\n        \"Namespace\",\n        \"MemberA\",\n        \"MemberB\"\n      ]\n    }\n  ],\n  \"usages\": []\n}"
        }
    ]
}
```

---

### Feature 11: Parse — Usages (TypeScript)

**As a tooling author**, I want the referenced identifier names harvested from TypeScript code, so I can answer "what does this code use?".

**Expected Behavior:** `usages` collects, in source order and de-duplicated: decorators, typed/assigned member types, parameters and default-parameter values, return values, the **leading** identifier of a property access (not sub-properties), function-call targets, indexer access, variable assignments, nested identifiers, and globally used / extended class names.

**Test Cases:** `rcb_tests/public_test_cases/feature11_parse_usages_ts.json`

```json
{
    "description": "Collect the referenced identifier names (usages) from a TypeScript source: decorators, typed/assigned class members, parameters and default-parameter values, return values, property access (only the leading identifier, not sub-properties), function calls, indexer access, variable assignments, nested identifiers, and globally used / extended class names.",
    "cases": [
        {
            "input": {
                "action": "parse",
                "source": "class C {\n    private prv(param): ReturnValue {\n        functionCall(MyProperty);\n        return null;\n    }\n}",
                "scriptKind": "TS"
            },
            "expected_output": "{\n  \"kind\": \"file\",\n  \"imports\": [],\n  \"exports\": [],\n  \"declarations\": [\n    {\n      \"kind\": \"class\",\n      \"name\": \"C\",\n      \"isExported\": false,\n      \"accessors\": [],\n      \"properties\": [],\n      \"methods\": [\n        {\n          \"kind\": \"method\",\n          \"name\": \"prv\",\n          \"isAbstract\": false,\n          \"visibility\": \"private\",\n          \"type\": \"ReturnValue\",\n          \"parameters\": [\n            {\n              \"kind\": \"parameter\",\n              \"name\": \"param\",\n              \"start\": 26,\n              \"end\": 31\n            }\n          ],\n          \"variables\": [],\n          \"start\": 14,\n          \"end\": 108\n        }\n      ],\n      \"start\": 0,\n      \"end\": 110\n    }\n  ],\n  \"resources\": [],\n  \"usages\": [\n    \"param\",\n    \"ReturnValue\",\n    \"functionCall\",\n    \"MyProperty\"\n  ]\n}"
        }
    ]
}
```

---

### Feature 12: Parse — Usages (TSX)

**As a tooling author**, I want usages harvested from TSX, including JSX element/component names and identifiers inside JSX braces and callbacks.

**Expected Behavior:** In addition to the TS usage rules, `usages` includes JSX element/component names and identifiers used inside JSX expression braces (e.g. `{myFunc()}`) and inside callbacks such as `map()`.

**Test Cases:** `rcb_tests/public_test_cases/feature12_parse_usages_tsx.json`

```json
{
    "description": "Collect referenced identifier names from a TSX source, including JSX element/component names, and identifiers used inside JSX expression braces and inside callbacks such as map().",
    "cases": [
        {
            "input": {
                "action": "parse",
                "source": "export default function foobar() {\n    return (\n        <myComponent>\n            {myFunc()}\n        </myComponent>\n    );\n}",
                "scriptKind": "TSX"
            },
            "expected_output": "{\n  \"kind\": \"file\",\n  \"imports\": [],\n  \"exports\": [],\n  \"declarations\": [\n    {\n      \"kind\": \"default\",\n      \"name\": \"foobar\",\n      \"isExported\": true\n    },\n    {\n      \"kind\": \"function\",\n      \"name\": \"foobar\",\n      \"isExported\": false,\n      \"parameters\": [],\n      \"variables\": [],\n      \"start\": 0,\n      \"end\": 124\n    }\n  ],\n  \"resources\": [],\n  \"usages\": [\n    \"myComponent\",\n    \"myFunc\"\n  ]\n}"
        }
    ]
}
```

---

### Feature 13: Parse — Plain JavaScript

**As a tooling author**, I want plain JavaScript (`JS`) parsed, so ES6 classes and default exports are modeled even without type annotations.

**Expected Behavior:** With `scriptKind` `JS`, imports, exported ES6 classes (with their `ctor` and `methods`), and `export default X` (modeled as a `default` declaration) are recognized. Methods omit `visibility` and return `type` when none is present.

**Test Cases:** `rcb_tests/public_test_cases/feature13_parse_javascript.json`

```json
{
    "description": "Parse a plain JavaScript source (script kind JS): imports, exported ES6 classes with constructor and methods, and a default export.",
    "cases": [
        {
            "input": {
                "action": "parse",
                "source": "import $ from 'jquery';\n\nexport class ES6Class {\n    constructor() { }\n    doSomething() { }\n}\n\nexport default ES6Class;",
                "scriptKind": "JS"
            },
            "expected_output": "{\n  \"kind\": \"file\",\n  \"imports\": [\n    {\n      \"kind\": \"namedImport\",\n      \"libraryName\": \"jquery\",\n      \"defaultAlias\": \"$\",\n      \"specifiers\": [],\n      \"start\": 0,\n      \"end\": 23\n    }\n  ],\n  \"exports\": [],\n  \"declarations\": [\n    {\n      \"kind\": \"class\",\n      \"name\": \"ES6Class\",\n      \"isExported\": true,\n      \"ctor\": {\n        \"kind\": \"constructor\",\n        \"name\": \"ES6Class\",\n        \"parameters\": [],\n        \"variables\": [],\n        \"start\": 53,\n        \"end\": 70\n      },\n      \"accessors\": [],\n      \"properties\": [],\n      \"methods\": [\n        {\n          \"kind\": \"method\",\n          \"name\": \"doSomething\",\n          \"isAbstract\": false,\n          \"parameters\": [],\n          \"variables\": [],\n          \"start\": 75,\n          \"end\": 92\n        }\n      ],\n      \"start\": 25,\n      \"end\": 94\n    },\n    {\n      \"kind\": \"default\",\n      \"name\": \"ES6Class\",\n      \"isExported\": true\n    }\n  ],\n  \"resources\": [],\n  \"usages\": [\n    \"ES6Class\"\n  ]\n}"
        }
    ]
}
```

---

### Feature 14: Parse — JavaScript React (JSX)

**As a tooling author**, I want `JSX` script kind parsed, so a class whose method returns JSX is modeled and the JSX element names appear in usages.

**Expected Behavior:** With `scriptKind` `JSX`, imports, the exported class and its JSX-returning method are modeled, and the JSX element/component names contribute to `usages`.

**Test Cases:** `rcb_tests/public_test_cases/feature14_parse_jsx.json`

```json
{
    "description": "Parse a JavaScript-React source (script kind JSX): imports, an exported class whose method returns JSX, and a default export.",
    "cases": [
        {
            "input": {
                "action": "parse",
                "source": "import React from 'react';\n\nexport class ES6Class {\n    render() {\n        return (<div><Foobar /></div>);\n    }\n}\n\nexport default ES6Class;",
                "scriptKind": "JSX"
            },
            "expected_output": "{\n  \"kind\": \"file\",\n  \"imports\": [\n    {\n      \"kind\": \"namedImport\",\n      \"libraryName\": \"react\",\n      \"defaultAlias\": \"React\",\n      \"specifiers\": [],\n      \"start\": 0,\n      \"end\": 26\n    }\n  ],\n  \"exports\": [],\n  \"declarations\": [\n    {\n      \"kind\": \"class\",\n      \"name\": \"ES6Class\",\n      \"isExported\": true,\n      \"accessors\": [],\n      \"properties\": [],\n      \"methods\": [\n        {\n          \"kind\": \"method\",\n          \"name\": \"render\",\n          \"isAbstract\": false,\n          \"parameters\": [],\n          \"variables\": [],\n          \"start\": 56,\n          \"end\": 112\n        }\n      ],\n      \"start\": 28,\n      \"end\": 114\n    },\n    {\n      \"kind\": \"default\",\n      \"name\": \"ES6Class\",\n      \"isExported\": true\n    }\n  ],\n  \"resources\": [],\n  \"usages\": [\n    \"div\",\n    \"Foobar\",\n    \"ES6Class\"\n  ]\n}"
        }
    ]
}
```

---

### Feature 15: Parse — Nested Generic Arrow Function

**As a tooling author**, I want deeply nested constructs (a generic arrow function inside a method inside a class) fully modeled, so local variables at every depth are captured.

**Expected Behavior:** Variables declared inside a nested arrow function body are attributed to the enclosing method's `variables`, in source order, and the generic type parameter contributes to `usages`.

**Test Cases:** `rcb_tests/public_test_cases/feature15_parse_generic_arrow.json`

```json
{
    "description": "Parse a source where a generic arrow function is declared inside a method inside an exported class, capturing the full nested model.",
    "cases": [
        {
            "input": {
                "action": "parse",
                "source": "export class TestClass {\n                public test() {\n                    let a = <T>() => { let b = null; };\n                }\n            }",
                "scriptKind": "TS"
            },
            "expected_output": "{\n  \"kind\": \"file\",\n  \"imports\": [],\n  \"exports\": [],\n  \"declarations\": [\n    {\n      \"kind\": \"class\",\n      \"name\": \"TestClass\",\n      \"isExported\": true,\n      \"accessors\": [],\n      \"properties\": [],\n      \"methods\": [\n        {\n          \"kind\": \"method\",\n          \"name\": \"test\",\n          \"isAbstract\": false,\n          \"visibility\": \"public\",\n          \"parameters\": [],\n          \"variables\": [\n            {\n              \"kind\": \"variable\",\n              \"name\": \"a\",\n              \"isConst\": false,\n              \"isExported\": false,\n              \"start\": 77,\n              \"end\": 112\n            },\n            {\n              \"kind\": \"variable\",\n              \"name\": \"b\",\n              \"isConst\": false,\n              \"isExported\": false,\n              \"start\": 96,\n              \"end\": 109\n            }\n          ],\n          \"start\": 41,\n          \"end\": 130\n        }\n      ],\n      \"start\": 0,\n      \"end\": 144\n    }\n  ],\n  \"resources\": [],\n  \"usages\": [\n    \"a\",\n    \"T\",\n    \"b\"\n  ]\n}"
        }
    ]
}
```

---

### Feature 16: Generate — Import Statements

**As a tooling author**, I want import model elements rendered back to source, so I can synthesize import statements honoring formatting options.

**Expected Behavior:** A `generate` request supplies formatting `options` and an `element`. For a `namedImport`, the output is `import { <specs> } from <q>lib<q>;` where `<q>` is the configured `stringQuoteStyle`, specifiers are comma-separated with `spec as alias` when an alias is present, and `spaceBraces` controls the inner padding. The same generator also handles `externalModuleImport`, `stringImport`, `namespaceImport`, default-only and default+named forms; when a single-line named import would exceed `multiLineWrapThreshold` it wraps onto multiple indented lines using `tabSize` and `multiLineTrailingComma`.

**Test Cases:** `rcb_tests/public_test_cases/feature16_generate_imports.json`

```json
{
    "description": "Render import model nodes back to TypeScript source. Covers external-module (equals/require) imports, bare string imports, namespace imports, and named imports (empty, single-line, multi-line wrapped past the threshold, default-only, default+named). The configured quote style and indent size are honored.",
    "cases": [
        {
            "input": {
                "action": "generate",
                "options": {
                    "eol": ";",
                    "multiLineTrailingComma": true,
                    "multiLineWrapThreshold": 125,
                    "spaceBraces": true,
                    "stringQuoteStyle": "'",
                    "tabSize": 4
                },
                "element": {
                    "kind": "namedImport",
                    "libraryName": "namedLib",
                    "specifiers": [
                        {
                            "specifier": "spec1"
                        },
                        {
                            "specifier": "spec2",
                            "alias": "alias2"
                        }
                    ]
                }
            },
            "expected_output": "import { spec1, spec2 as alias2 } from 'namedLib';"
        },
        {
            "input": {
                "action": "generate",
                "options": {
                    "eol": ";",
                    "multiLineTrailingComma": true,
                    "multiLineWrapThreshold": 125,
                    "spaceBraces": true,
                    "stringQuoteStyle": "\"",
                    "tabSize": 2
                },
                "element": {
                    "kind": "namedImport",
                    "libraryName": "namedLib",
                    "specifiers": [
                        {
                            "specifier": "spec1"
                        },
                        {
                            "specifier": "spec2",
                            "alias": "alias2"
                        }
                    ]
                }
            },
            "expected_output": "import { spec1, spec2 as alias2 } from \"namedLib\";"
        }
    ]
}
```

---

### Feature 17: Generate — Symbol Specifier

**As a tooling author**, I want a symbol specifier rendered, so I can emit `name` or `name as alias`.

**Expected Behavior:** A `symbol` element with a `specifier` renders as its name, or `specifier as alias` when an `alias` is present.

**Test Cases:** `rcb_tests/public_test_cases/feature17_generate_symbol.json`

```json
{
    "description": "Render a symbol specifier to source: just the symbol name, or \"name as alias\" when an alias is present.",
    "cases": [
        {
            "input": {
                "action": "generate",
                "options": {
                    "eol": ";",
                    "multiLineTrailingComma": true,
                    "multiLineWrapThreshold": 125,
                    "spaceBraces": true,
                    "stringQuoteStyle": "'",
                    "tabSize": 4
                },
                "element": {
                    "kind": "symbol",
                    "specifier": "SymbolSpecifier",
                    "alias": "WithAlias"
                }
            },
            "expected_output": "SymbolSpecifier as WithAlias"
        }
    ]
}
```

---

### Feature 18: Generate — Method

**As a tooling author**, I want method elements rendered, so I can synthesize a stubbed implementation or an abstract signature.

**Expected Behavior:** A `method` element renders an indented, visibility-prefixed signature with its return `type`. A throwing body (`throw new Error('Not implemented yet.');`) is emitted, wrapped in braces and indented with `tabSize`. Visibility (`public`/`protected`/`private`) and return type are honored.

**Test Cases:** `rcb_tests/public_test_cases/feature18_generate_method.json`

```json
{
    "description": "Render a method declaration to source. Non-abstract methods get a body that throws a not-implemented error; abstract methods are rendered as a single signature line. Visibility (public/protected/private) and return type are honored.",
    "cases": [
        {
            "input": {
                "action": "generate",
                "options": {
                    "eol": ";",
                    "multiLineTrailingComma": true,
                    "multiLineWrapThreshold": 125,
                    "spaceBraces": true,
                    "stringQuoteStyle": "'",
                    "tabSize": 4
                },
                "element": {
                    "kind": "method",
                    "name": "myMethod",
                    "isAbstract": false,
                    "visibility": "public",
                    "type": "void"
                }
            },
            "expected_output": "    public myMethod(): void {\n        throw new Error('Not implemented yet.');\n    }\n"
        },
        {
            "input": {
                "action": "generate",
                "options": {
                    "eol": ";",
                    "multiLineTrailingComma": true,
                    "multiLineWrapThreshold": 125,
                    "spaceBraces": true,
                    "stringQuoteStyle": "'",
                    "tabSize": 4
                },
                "element": {
                    "kind": "method",
                    "name": "myAbstractMethod",
                    "isAbstract": true,
                    "visibility": "public",
                    "type": "string"
                }
            },
            "expected_output": "    public myAbstractMethod(): string {\n        throw new Error('Not implemented yet.');\n    }\n"
        }
    ]
}
```

---

### Feature 19: Generate — Accessors

**As a tooling author**, I want get/set accessor elements rendered, so I can synthesize property accessors.

**Expected Behavior:** A `getter` renders `<vis> get <name>(): <type>` and a `setter` renders `<vis> set <name>(value: <type>)`, each followed by a throwing body. Visibility is honored; the getter renders its return `type` when present; the setter renders a typed (or untyped) `value` parameter.

**Test Cases:** `rcb_tests/public_test_cases/feature19_generate_accessor.json`

```json
{
    "description": "Render get/set accessor declarations to source. Non-abstract accessors get a throwing body; abstract accessors are a single signature line. Visibility is honored; getters render their return type when present, setters render a typed/untyped value parameter.",
    "cases": [
        {
            "input": {
                "action": "generate",
                "options": {
                    "eol": ";",
                    "multiLineTrailingComma": true,
                    "multiLineWrapThreshold": 125,
                    "spaceBraces": true,
                    "stringQuoteStyle": "'",
                    "tabSize": 4
                },
                "element": {
                    "kind": "getter",
                    "name": "pubGetter",
                    "visibility": "public",
                    "type": "string",
                    "isAbstract": false
                }
            },
            "expected_output": "    public get pubGetter(): string {\n        throw new Error('Not implemented yet.');\n    }\n"
        },
        {
            "input": {
                "action": "generate",
                "options": {
                    "eol": ";",
                    "multiLineTrailingComma": true,
                    "multiLineWrapThreshold": 125,
                    "spaceBraces": true,
                    "stringQuoteStyle": "'",
                    "tabSize": 4
                },
                "element": {
                    "kind": "setter",
                    "name": "pubSetter",
                    "visibility": "public",
                    "type": "string",
                    "isAbstract": false
                }
            },
            "expected_output": "    public set pubSetter(value: string) {\n        throw new Error('Not implemented yet.');\n    }\n"
        }
    ]
}
```

---

### Feature 20: Generate — Property

**As a tooling author**, I want a property element rendered, so I can emit a typed field line.

**Expected Behavior:** A `property` element renders as an indented, visibility-prefixed, typed field line ending in `;`.

**Test Cases:** `rcb_tests/public_test_cases/feature20_generate_property.json`

```json
{
    "description": "Render a class property declaration to source as an indented, visibility-prefixed, typed field line.",
    "cases": [
        {
            "input": {
                "action": "generate",
                "options": {
                    "eol": ";",
                    "multiLineTrailingComma": true,
                    "multiLineWrapThreshold": 125,
                    "spaceBraces": true,
                    "stringQuoteStyle": "'",
                    "tabSize": 4
                },
                "element": {
                    "kind": "property",
                    "name": "pubProperty",
                    "visibility": "public",
                    "type": "string"
                }
            },
            "expected_output": "    public pubProperty: string;\n"
        }
    ]
}
```

---

### Feature 21: Generate — Parameter

**As a tooling author**, I want a parameter element rendered, so I can emit a bare or typed parameter.

**Expected Behavior:** A `parameter` element renders as just its `name` when it has no type, or `name: type` when typed.

**Test Cases:** `rcb_tests/public_test_cases/feature21_generate_parameter.json`

```json
{
    "description": "Render a parameter declaration to source: just the name when it has no type, or \"name: type\" when typed.",
    "cases": [
        {
            "input": {
                "action": "generate",
                "options": {
                    "eol": ";",
                    "multiLineTrailingComma": true,
                    "multiLineWrapThreshold": 125,
                    "spaceBraces": true,
                    "stringQuoteStyle": "'",
                    "tabSize": 4
                },
                "element": {
                    "kind": "parameter",
                    "name": "param",
                    "type": ""
                }
            },
            "expected_output": "param"
        },
        {
            "input": {
                "action": "generate",
                "options": {
                    "eol": ";",
                    "multiLineTrailingComma": true,
                    "multiLineWrapThreshold": 125,
                    "spaceBraces": true,
                    "stringQuoteStyle": "'",
                    "tabSize": 4
                },
                "element": {
                    "kind": "parameter",
                    "name": "stringParam",
                    "type": "string"
                }
            },
            "expected_output": "stringParam: string"
        }
    ]
}
```

---

### Feature 22: Generate — Variable

**As a tooling author**, I want a variable element rendered, so I can emit a `name: type` fragment.

**Expected Behavior:** A `variable` element renders as `name: type`.

**Test Cases:** `rcb_tests/public_test_cases/feature22_generate_variable.json`

```json
{
    "description": "Render a variable declaration to source as \"name: type\".",
    "cases": [
        {
            "input": {
                "action": "generate",
                "options": {
                    "eol": ";",
                    "multiLineTrailingComma": true,
                    "multiLineWrapThreshold": 125,
                    "spaceBraces": true,
                    "stringQuoteStyle": "'",
                    "tabSize": 4
                },
                "element": {
                    "kind": "variable",
                    "name": "myVar",
                    "isConst": false,
                    "type": "string"
                }
            },
            "expected_output": "myVar: string"
        }
    ]
}
```

---

### Feature 23: Generate — Not Generatable

**As a tooling author**, I want a clear, neutral failure when I ask to render an element kind that has no generator, so misuse fails predictably instead of producing garbage.

**Expected Behavior:** Requesting `generate` for an element kind with no registered generator (e.g. a whole `class`) yields a neutral error result identifying the un-renderable element: the two lines `error=not_generatable` and `element=<kind>`.

**Test Cases:** `rcb_tests/public_test_cases/feature23_generate_not_generatable.json`

```json
{
    "description": "Attempting to render an element kind that has no generator yields a neutral error result identifying that the element is not generatable, instead of producing source.",
    "cases": [
        {
            "input": {
                "action": "generate",
                "options": {
                    "eol": ";",
                    "multiLineTrailingComma": true,
                    "multiLineWrapThreshold": 125,
                    "spaceBraces": true,
                    "stringQuoteStyle": "'",
                    "tabSize": 4
                },
                "element": {
                    "kind": "class",
                    "name": "foo",
                    "isExported": true
                }
            },
            "expected_output": "error=not_generatable\nelement=class"
        }
    ]
}
```

---

### Feature 24: Build — Reverse Declaration Index

**As a tooling author**, I want a project-wide map from each exported name to where it can be imported from, so I can power auto-import. Re-exports must be resolved.

**Expected Behavior:** A `buildIndex` request supplies a `files` map (virtual path → source text) and an `entry` list of files to index. The result is a JSON object keyed by declaration name; each value is a list of origins `{kind, name, from}`, where `from` is the normalized (extension-stripped, leading-slash) path it is reachable from. Re-exports are resolved: `export * from './x'` moves all of `x`'s declarations to the re-exporting origin; `export { a } from './x'` moves only the named ones; aliased re-exports rename them at the new origin. Keys are emitted in sorted order.

**Test Cases:** `rcb_tests/public_test_cases/feature24_build_index.json`

```json
{
    "description": "Build a reverse declaration index from a set of source files, mapping each exported declaration name to the list of origins that provide it (kind, name, and the source path it is reachable from). Re-exports are resolved: \"export * from\" moves all declarations to the re-exporting origin, \"export { } from\" moves only the named ones, and aliased re-exports rename them at the new origin.",
    "cases": [
        {
            "input": {
                "action": "buildIndex",
                "files": {
                    "classes.ts": "export class Class1 { }\nexport class Class2 { }\nexport class Class3 { }\n"
                },
                "entry": [
                    "classes.ts"
                ]
            },
            "expected_output": "{\n  \"Class1\": [\n    {\n      \"kind\": \"class\",\n      \"name\": \"Class1\",\n      \"from\": \"/classes\"\n    }\n  ],\n  \"Class2\": [\n    {\n      \"kind\": \"class\",\n      \"name\": \"Class2\",\n      \"from\": \"/classes\"\n    }\n  ],\n  \"Class3\": [\n    {\n      \"kind\": \"class\",\n      \"name\": \"Class3\",\n      \"from\": \"/classes\"\n    }\n  ]\n}"
        },
        {
            "input": {
                "action": "buildIndex",
                "files": {
                    "classes.ts": "export class Class1 { }\nexport class Class2 { }\nexport class Class3 { }\n",
                    "export-all.ts": "export * from './classes';"
                },
                "entry": [
                    "export-all.ts",
                    "classes.ts"
                ]
            },
            "expected_output": "{\n  \"Class1\": [\n    {\n      \"kind\": \"class\",\n      \"name\": \"Class1\",\n      \"from\": \"/export-all\"\n    }\n  ],\n  \"Class2\": [\n    {\n      \"kind\": \"class\",\n      \"name\": \"Class2\",\n      \"from\": \"/export-all\"\n    }\n  ],\n  \"Class3\": [\n    {\n      \"kind\": \"class\",\n      \"name\": \"Class3\",\n      \"from\": \"/export-all\"\n    }\n  ]\n}"
        }
    ]
}
```

---

### Feature 25: Inspect — Import "Is New"

**As a tooling author**, I want to know whether an import has a concrete source span, so I can tell a freshly synthesized import from one that was parsed out of real source.

**Expected Behavior:** A `describeImport` request builds an import of the given `importType` (and fields such as `libraryName`, `alias`, `start`, `end`) and echoes them back along with an `isNew` flag. An import is **new** when either `start` or `end` is missing; it is **not new** only when both are present. This applies to all import kinds.

**Test Cases:** `rcb_tests/public_test_cases/feature25_import_is_new.json`

```json
{
    "description": "Report whether an import is considered \"new\" (i.e. has no concrete source span). An import is new when either its start or end position is missing; it is not new only when both are present. Applies to all import kinds.",
    "cases": [
        {
            "input": {
                "action": "describeImport",
                "importType": "externalModuleImport",
                "libraryName": "lib",
                "alias": "alias",
                "end": 1337
            },
            "expected_output": "{\n  \"importType\": \"externalModuleImport\",\n  \"libraryName\": \"lib\",\n  \"alias\": \"alias\",\n  \"end\": 1337,\n  \"isNew\": true\n}"
        },
        {
            "input": {
                "action": "describeImport",
                "importType": "externalModuleImport",
                "libraryName": "lib",
                "alias": "alias",
                "start": 12,
                "end": 1337
            },
            "expected_output": "{\n  \"importType\": \"externalModuleImport\",\n  \"libraryName\": \"lib\",\n  \"alias\": \"alias\",\n  \"start\": 12,\n  \"end\": 1337,\n  \"isNew\": false\n}"
        }
    ]
}
```

---

### Feature 26: Normalize — Filename

**As a tooling author**, I want a file path normalized for indexing, so the same module is keyed consistently regardless of its source extension.

**Expected Behavior:** A `normalizeFilename` request strips a trailing source-file extension — one of `.d.ts`, `.d.tsx`, `.ts`, `.tsx`, `.js`, `.jsx` — while leaving the rest of the path intact.

**Test Cases:** `rcb_tests/public_test_cases/feature26_normalize_filename.json`

```json
{
    "description": "Normalize a file path for indexing by stripping a trailing source-file extension (.d.ts, .d.tsx, .ts, .tsx, .js, .jsx) while leaving the rest of the path intact.",
    "cases": [
        {
            "input": {
                "action": "normalizeFilename",
                "path": "./foobar.d.ts"
            },
            "expected_output": "./foobar"
        },
        {
            "input": {
                "action": "normalizeFilename",
                "path": "./foobar.ts"
            },
            "expected_output": "./foobar"
        }
    ]
}
```

---

### Feature 27: Normalize — Path URI

**As a tooling author**, I want a path URI normalized to a bare path, so URIs from editors can be compared with filesystem paths.

**Expected Behavior:** A `normalizePathUri` request URI-decodes the value and removes a leading `file://` scheme prefix, returning the bare path.

**Test Cases:** `rcb_tests/public_test_cases/feature27_normalize_path_uri.json`

```json
{
    "description": "Normalize a path URI by URI-decoding it and removing a leading \"file://\" scheme prefix, returning the bare path.",
    "cases": [
        {
            "input": {
                "action": "normalizePathUri",
                "uri": "file:///root/file.txt"
            },
            "expected_output": "/root/file.txt"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the parsing, model, source generation, declaration index and path-helper features above. The physical structure MUST align with the "Scale-Driven Code Organization" constraint. The core logic must be decoupled from stdin/stdout and JSON. You may build on a TypeScript compiler library as the syntax-tree provider, but the source model, generators, index and helpers are your own.

2. **The Execution/Test Adapter:** A runnable program (entry point) that acts as a client to your core system — logically and ideally physically separated from it. It reads a single JSON request from stdin and writes the result to stdout, matching the per-feature contracts. The request's `action` selects behavior:
   - `parse` — parse `source` with the given `scriptKind` (`TS`/`TSX`/`JS`/`JSX`) and emit the `file` model as pretty-printed JSON (2-space indent), with optional fields omitted and `usages` in source order.
   - `generate` — render the supplied `element` to source using the formatting `options` (`stringQuoteStyle`, `tabSize`, `spaceBraces`, `multiLineWrapThreshold`, `multiLineTrailingComma`, `eol`). An element kind with no generator must yield the two-line neutral error `error=not_generatable` / `element=<kind>`.
   - `buildIndex` — build the reverse declaration index from a virtual `files` map and `entry` list, resolving re-exports, and emit the name→origins JSON (2-space indent, sorted keys).
   - `describeImport` — construct an import of `importType` and echo its fields plus the computed `isNew` flag as JSON.
   - `normalizeFilename` / `normalizePathUri` — apply the corresponding path helper and print the bare result.

   All errors surfaced by the adapter MUST be neutral, language-agnostic lines (e.g. `error=<category>`), never a host-language runtime stack trace.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same layout rules as the type declarations in the core parser block
