## Product Requirement Document

# Module Dependency Graph Renderer - Generate Mermaid flowcharts from inter-module dependencies

## Project Goal

Build a rendering engine that turns a project's set of inter-module dependency edges into a [Mermaid](https://mermaid.js.org) flowchart and embeds it into a Markdown document section. Developers describe *which module depends on which* (and under which dependency scope), pick a few presentation options (colour theme, flow orientation, labelling, focus highlighting), and the engine produces a ready-to-commit diagram without anyone hand-drawing or hand-maintaining the graph.

[a custom delimiter string to be defined in the diagram generator configuration]-

## Background & Problem

Without this tool, developers who want a visual map of how their modules depend on each other must draw the diagram by hand and keep it in sync as the build evolves. This is repetitive, error-prone, and the diagram silently rots the moment a new dependency is added or removed. Manually authoring Mermaid syntax (theme init blocks, subgraph grouping, edge labels, highlight classes) is fiddly and easy to get wrong.

With this tool, the developer supplies a plain data description of the dependency edges plus presentation options, and receives a deterministic, correctly-formatted Mermaid diagram already spliced into the right section of the target document. Regenerating is idempotent: re-running replaces the previous diagram in place and leaves the rest of the document untouched.

[a custom delimiter string to be defined in the diagram generator configuration]-

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This is a focused rendering library with a handful of distinct responsibilities (input model, graph rendering, document splicing, output formatting). Prefer a small, clearly separated multi-file layout (e.g. `src/` for the core engine, a separate execution adapter, `tests/`). Do not over-engineer, but do not collapse everything into one god file either.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases in "Core Features" are a **black-box contract for the execution adapter**, not the internal data model. The core rendering engine must be callable through idiomatic in-memory data structures and must know nothing about stdin/stdout or JSON. The execution adapter is the only component that parses JSON commands and prints text.

3. **Adherence to SOLID Design Principles** (scaled to project size):
   - **SRP:** Keep input parsing, edge filtering, graph rendering, document section management, and output formatting in distinct units.
   - **OCP:** Adding a new colour theme or a new orientation must not require rewriting the rendering core.
   - **LSP:** Theme variants must be substitutable wherever a theme is expected.
   - **ISP:** Keep interfaces small and cohesive.
   - **DIP:** The rendering core depends on abstractions (an edge set, an options object), not on any concrete I/O.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public API of the core should be elegant and idiomatic to the target language, hiding formatting details.
   - **Resilience:** Invalid requests (such as a focus selector that matches nothing) must be modelled as explicit error outcomes, not crashes that leak runtime internals.

[a custom delimiter string to be defined in the diagram generator configuration]-

## Core Features

### Feature 1: Dependency graph rendering with theme, orientation and folder subgraphs

**As a developer**, I want to render my module dependency edges as a Mermaid flowchart with a chosen colour theme and flow orientation, so I can drop an up-to-date diagram into my docs.

**Expected Behavior / Usage:**

The input is a command object describing the target document `heading`, the current `document` text, optional presentation options, and a `dependencies` map. The `dependencies` map keys are source module paths (colon-separated, e.g. `:example`) and values are lists of edges, each `{ "target": <module path>, "configuration": <scope name> }`.

The output is the document text with a fenced ` ```mermaid ` block inserted under the heading. The block always begins with an init section carrying the theme name, followed by `graph <orientation>`. Supported `theme` values are `dark`, `default`, `forest`, `neutral` (the default) and the customizable `base`. Supported `orientation` values are `LR` (default, left-to-right), `RL` (right-to-left), `TB` (top-to-bottom) and `BT` (bottom-to-top). Unless full-path mode is on (Feature 2), each node is rendered by its short name (the last non-empty path segment), self-edges are dropped, duplicate edges are collapsed, and modules that share the same parent folder are gathered into a labelled `subgraph <folder>` block listing those module names. Edges are rendered as `  <source> [a custom delimiter string to be defined in the diagram generator configuration]> <target>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_graph_rendering.json`

```json
{
    "description": "Renders a Mermaid flowchart from a set of inter-module dependency edges. The chosen colour theme and flow orientation appear in the wire output, and modules sharing the same parent folder are grouped into a labelled subgraph.",
    "cases": [
        {
            "input": {
                "heading": "### Dependency Diagram",
                "document": "### Dependency Diagram",
                "theme": "forest",
                "orientation": "RL",
                "dependencies": {
                    ":example": [
                        {
                            "target": ":groupFolder:example2",
                            "configuration": "implementation"
                        }
                    ]
                }
            },
            "expected_output": "### Dependency Diagram\n\n```mermaid\n%%{\n  init: {\n    'theme': 'forest'\n  }\n}%%\n\ngraph RL\n\n  subgraph groupFolder\n    example2\n  end\n  example [a custom delimiter string to be defined in the diagram generator configuration]> example2\n```"
        }
    ]
}
```

[a custom delimiter string to be defined in the diagram generator configuration]-

### Feature 2: Full module-path rendering

**As a developer**, I want to render nodes using their complete module paths, so that modules with the same short name in different folders stay distinct.

**Expected Behavior / Usage:**

When `showFullPath` is `true`, every node is printed with its complete colon-separated path (e.g. `:groupFolder:example2`) instead of its short name, and the folder-grouping subgraphs are **not** emitted (full paths already disambiguate, so grouping would be redundant). Edges are still rendered as `  <source path> [a custom delimiter string to be defined in the diagram generator configuration]> <target path>`. All other behavior (theme/orientation init block) is unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature2_full_module_path.json`

```json
{
    "description": "When full-path mode is enabled, every node is rendered using its complete colon-separated module path and the folder-grouping subgraphs are omitted.",
    "cases": [
        {
            "input": {
                "heading": "### Dependency Diagram",
                "document": "### Dependency Diagram",
                "showFullPath": true,
                "dependencies": {
                    ":example": [
                        {
                            "target": ":groupFolder:example2",
                            "configuration": "implementation"
                        }
                    ]
                }
            },
            "expected_output": "### Dependency Diagram\n\n```mermaid\n%%{\n  init: {\n    'theme': 'neutral'\n  }\n}%%\n\ngraph LR\n  :example [a custom delimiter string to be defined in the diagram generator configuration]> :groupFolder:example2\n```"
        }
    ]
}
```

[a custom delimiter string to be defined in the diagram generator configuration]-

### Feature 3: Edge labels with the dependency scope name

**As a developer**, I want each edge to optionally carry the name of the dependency scope it came from, so I can see *how* one module depends on another.

**Expected Behavior / Usage:**

Each edge carries a `configuration` (scope) name. When the `linkText` option is `configuration`, edges are rendered with that scope name as a mid-edge label: `  <source> [a custom delimiter string to be defined in the diagram generator configuration] <scope> [a custom delimiter string to be defined in the diagram generator configuration]> <target>`. When `linkText` is `none` (the default), edges are rendered with a plain `[a custom delimiter string to be defined in the diagram generator configuration]>` and no label. Because the scope name then distinguishes otherwise-identical edges, two edges from the same source to different targets under different scopes both appear (one labelled line each). Subgraph grouping still applies in short-name mode.

**Test Cases:** `rcb_tests/public_test_cases/feature3_edge_configuration_labels.json`

```json
{
    "description": "When configuration labelling is enabled, each edge is annotated with the name of the dependency scope it belongs to, producing one labelled edge per scope.",
    "cases": [
        {
            "input": {
                "heading": "### Dependency Diagram",
                "document": "### Dependency Diagram",
                "theme": "forest",
                "orientation": "RL",
                "linkText": "configuration",
                "dependencies": {
                    ":example": [
                        {
                            "target": ":groupFolder:example2",
                            "configuration": "implementation"
                        },
                        {
                            "target": ":groupFolder:example3",
                            "configuration": "runtimeOnly"
                        }
                    ]
                }
            },
            "expected_output": "### Dependency Diagram\n\n```mermaid\n%%{\n  init: {\n    'theme': 'forest'\n  }\n}%%\n\ngraph RL\n\n  subgraph groupFolder\n    example2\n    example3\n  end\n  example [a custom delimiter string to be defined in the diagram generator configuration] implementation [a custom delimiter string to be defined in the diagram generator configuration]> example2\n  example [a custom delimiter string to be defined in the diagram generator configuration] runtimeOnly [a custom delimiter string to be defined in the diagram generator configuration]> example3\n```"
        }
    ]
}
```

[a custom delimiter string to be defined in the diagram generator configuration]-

### Feature 4: Customizable theme variables

**As a developer**, I want to fully customize the diagram colours, so the graph matches my documentation's visual style.

**Expected Behavior / Usage:**

When the `theme` is the customizable `base` theme, the caller may supply a `variables` map of theme-variable names to values. The init block then carries the theme name `base` followed by a `themeVariables` entry whose value is the variables map serialized verbatim as a compact JSON object (keys and values double-quoted, no spaces, original insertion order preserved). The `themeVariables` line is indented with a leading tab. When the variables map is empty, no `themeVariables` entry is emitted. All other rendering behavior is unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature4_custom_theme_variables.json`

```json
{
    "description": "The customizable theme accepts a map of theme variables which are serialized verbatim as a JSON object inside the diagram init block.",
    "cases": [
        {
            "input": {
                "heading": "### Dependency Diagram",
                "document": "### Dependency Diagram",
                "theme": {
                    "name": "base",
                    "variables": {
                        "primaryTextColor": "#fff",
                        "primaryColor": "#5a4f7c",
                        "primaryBorderColor": "#5a4f7c",
                        "lineColor": "#f5a623",
                        "tertiaryColor": "#40375c",
                        "fontSize": "11px"
                    }
                },
                "dependencies": {
                    ":example": [
                        {
                            "target": ":groupFolder:example2",
                            "configuration": "implementation"
                        }
                    ]
                }
            },
            "expected_output": "### Dependency Diagram\n\n```mermaid\n%%{\n  init: {\n    'theme': 'base',\n[a whitespace character used for indentation in the theme variables block]'themeVariables': {\"primaryTextColor\":\"#fff\",\"primaryColor\":\"#5a4f7c\",\"primaryBorderColor\":\"#5a4f7c\",\"lineColor\":\"#f5a623\",\"tertiaryColor\":\"#40375c\",\"fontSize\":\"11px\"}\n  }\n}%%\n\ngraph LR\n\n  subgraph groupFolder\n    example2\n  end\n  example [a custom delimiter string to be defined in the diagram generator configuration]> example2\n```"
        }
    ]
}
```

[a custom delimiter string to be defined in the diagram generator configuration]-

### Feature 5: Focus selector

**As a developer**, I want to spotlight a subset of modules by pattern, so I can produce a diagram that draws attention to the part of the system I care about.

**Expected Behavior / Usage:**

A focus selector is a regular expression. It restricts the rendered graph to only the edges where the source or the target node matches the selector, and it highlights the matched nodes. When the selector is absent it defaults to `.*`, meaning "everything", which performs no filtering and adds no highlighting.

*5.1 Highlighting matched nodes — keep only touching edges and emit highlight classes*

When a non-`.*` selector is supplied and at least one node matches, only edges that touch a matching node are kept. After the edge list, the output appends a highlight section: one blank line, a `classDef focus fill:<focusColor>,stroke:#fff,stroke-width:2px,color:#fff;` line using the configured focus colour (a default colour is used when none is given), and one `class <matched node> focus` line per matched node. The matched node names follow the same short-name / full-path rendering rule as the edges.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_focus_highlighting.json`

```json
{
    "description": "A focus selector (regular expression) keeps only the edges that touch a matching node and emits highlight class definitions for the matched nodes using the configured focus colour.",
    "cases": [
        {
            "input": {
                "heading": "### Dependency Diagram",
                "document": "### Dependency Diagram",
                "showFullPath": true,
                "focusPattern": ".*example2.*",
                "theme": {
                    "name": "base",
                    "focusColor": "#F5A622"
                },
                "dependencies": {
                    ":example": [
                        {
                            "target": ":groupFolder:example2",
                            "configuration": "implementation"
                        },
                        {
                            "target": ":groupFolder:example3",
                            "configuration": "implementation"
                        }
                    ]
                }
            },
            "expected_output": "### Dependency Diagram\n\n```mermaid\n%%{\n  init: {\n    'theme': 'base'\n  }\n}%%\n\ngraph LR\n  :example [a custom delimiter string to be defined in the diagram generator configuration]> :groupFolder:example2\n\nclassDef focus fill:#F5A622,stroke:#fff,stroke-width:2px,color:#fff;\nclass :groupFolder:example2 focus\n```"
        }
    ]
}
```

*5.2 Empty match is an error — normalized error contract*

When a non-`.*` selector is supplied but matches no node in the dependency set, rendering does not produce a diagram; it fails. The failure is reported as a language-neutral, two-line contract: `error=no_modules_match_pattern` followed by `pattern=<the offending selector>` (and a trailing newline). No host-language exception class name, stack trace, or runtime message is leaked.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_focus_no_match_error.json`

```json
{
    "description": "When a focus selector is supplied but matches no node in the dependency set, rendering fails with a normalized error category and the offending selector echoed back.",
    "cases": [
        {
            "input": {
                "heading": "### Dependency Diagram",
                "document": "### Dependency Diagram",
                "showFullPath": true,
                "focusPattern": ".*example5.*",
                "theme": {
                    "name": "base",
                    "focusColor": "#F5A622"
                },
                "dependencies": {
                    ":example": [
                        {
                            "target": ":groupFolder:example2",
                            "configuration": "implementation"
                        },
                        {
                            "target": ":groupFolder:example3",
                            "configuration": "implementation"
                        }
                    ]
                }
            },
            "expected_output": "error=no_modules_match_pattern\npattern=.*example5.*\n"
        }
    ]
}
```

[a custom delimiter string to be defined in the diagram generator configuration]-

### Feature 6: Document section management

**As a developer**, I want the diagram spliced into the right place in my document, creating the document if needed, so I can regenerate safely without clobbering other content.

**Expected Behavior / Usage:**

The diagram is written into the document under the given `heading`. When the `document` field is absent (the target document does not yet exist), a new document is created whose content is the heading, a blank line, and the fenced diagram block. When the document already contains a line starting with the heading, the content between that heading and the next heading (a line starting with `#`) is replaced by the freshly rendered diagram block, and any sections that follow are preserved verbatim. An empty dependency set still produces a valid (edge-less) diagram block.

**Test Cases:** `rcb_tests/public_test_cases/feature6_document_section.json`

```json
{
    "description": "Manages the target document section: when the document is absent it is created containing the heading and graph; when the heading already exists, any stale content beneath it is replaced while following sections are preserved.",
    "cases": [
        {
            "input": {
                "heading": "### Dependency Diagram",
                "dependencies": {}
            },
            "expected_output": "### Dependency Diagram\n\n```mermaid\n%%{\n  init: {\n    'theme': 'neutral'\n  }\n}%%\n\ngraph LR\n\n\n```"
        }
    ]
}
```

[a custom delimiter string to be defined in the diagram generator configuration]-

## Deliverables

1. **The Core System:** A cleanly structured rendering engine that, given an in-memory set of dependency edges plus presentation options, produces the Mermaid diagram text and splices it into a document section. Its physical structure must follow the "Scale-Driven Code Organization" constraint (a small multi-file layout with clear separation between the input model, the renderer, the document-section manager, and output formatting).

2. **The Execution/Test Adapter:** A runnable program that reads a single JSON command from stdin, builds the in-memory inputs, invokes the core engine, and prints the resulting document text (or the normalized error contract) to stdout, exactly matching the per-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `[a custom delimiter string to be defined in the diagram generator configuration]cases-dir <subdir>` to choose the directory of case files (default `test_cases`; the publicly visible cases embedded in this PRD live under `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_graph_rendering.json` run with `[a custom delimiter string to be defined in the diagram generator configuration]cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_graph_rendering@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout of the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- the same styling rules applied when a user variable matches a module name
- follow the standard JSON serialization protocol described in the output module
