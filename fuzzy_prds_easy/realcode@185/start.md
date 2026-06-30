## Product Requirement Document

# Provider Schema Documentation Renderer - Markdown Generation for Infrastructure-as-Code Schemas

## Project Goal

Build a documentation-rendering library that turns a machine-readable infrastructure provider schema (attributes, nested attributes, and nested blocks, each carrying a value type and behavior flags) into clean, deterministic Markdown reference documentation. It allows tool authors to publish accurate, consistently formatted resource/data-source reference pages directly from a schema definition, without hand-writing or hand-maintaining the documentation.

---

## Background & Problem

Without this library, authors of infrastructure provider tooling must hand-write reference docs for every resource, data source, and provider configuration: enumerating each field, stating its value type, marking whether it is required/optional/read-only, flagging sensitive and deprecated fields, and re-deriving all of that whenever the schema changes. This is repetitive, easy to get out of sync with the real schema, and inconsistent across pages.

With this library, a schema document is rendered into a Markdown `## Schema` section automatically: fields are grouped into Required/Optional/Read-Only sections, each annotated with a uniform inline label describing its type and behavior, and nested structures are expanded into linked sub-sections. The same primitives that render the schema are also exposed so authors can render individual type names, individual field labels, and small text-formatting helpers used inside documentation templates.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain has several distinct responsibilities (type rendering, field-label rendering, behavior classification, whole-schema rendering, and small text helpers); it MUST therefore be organized into clearly separated modules/packages rather than a single monolithic file. Do not over-engineer, but strictly avoid a "god file".

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in "Core Features" describe a **black-box contract for the execution adapter**, NOT the internal data model. The core rendering logic MUST remain decoupled from stdin/stdout and JSON parsing. A thin execution adapter is solely responsible for translating a JSON command into idiomatic calls into the core rendering functions and printing the raw result.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility:** Keep parsing, routing, classification, rendering, and output formatting in distinct units.
   - **Open/Closed:** New value types or new label markers should extend the renderer without rewriting existing rendering paths.
   - **Liskov Substitution:** Type/attribute/block renderers must be interchangeable through their common writer-based interface.
   - **Interface Segregation:** Keep rendering interfaces small (a function that writes one thing to an output sink).
   - **Dependency Inversion:** Renderers depend on an abstract output sink, not on concrete I/O.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public rendering interface should be elegant and idiomatic to the target language, hiding internal grouping/classification complexity.
   - **Resilience:** Edge cases (unsupported value types, unclassifiable fields, missing files) must be modeled as proper, distinguishable errors rather than generic failures or silent empty output.

---

##[a dynamic character separator]Core[a dynamic character separator]Features

###[a dynamic character separator]Feature 1: Value Type Name Rendering

**As a developer**, I want to render a field's value type into a human-readable name, so I can label each field's type consistently in documentation.

**Expected Behavior / Usage:**

The input is a value type expressed in the schema wire format: a primitive is a bare string (`"bool"`, `"number"`, `"string"`), the dynamic pseudo-type is `"dynamic"`, and composite types are arrays whose first element is the kind (`"list"`, `"set"`, `"map"`, `"object"`, `"tuple"`) followed by the element/member definition. The output is the rendered name: `Boolean`, `Number`, `String`, or `Dynamic` for scalars; collection kinds render as `List of <element>`, `Set of <element>`, `Map of <element>` with the element type rendered recursively; structural object types render as the bare word `Object` and tuple types render as the bare word `[a specific sentinel value — ask the PM for the exact string]` (their members are not expanded). Nesting composes, e.g. a list of maps of sets of objects renders as `List of Map of Set of Object`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_type_name_rendering.json`

```json
{
    "description": "Render a Terraform value type into its human-readable documentation name. Primitive types map to Boolean/Number/String, the dynamic pseudo-type maps to Dynamic, collection wrappers prepend 'List of '/'Set of '/'Map of ' to their recursively rendered element type, structural object types render as Object and tuple types render as [a specific sentinel value — ask the PM for the exact string]. The type is provided in JSON wire format.",
    "cases": [
        {"input": {"op": "write_type", "type": "bool"}, "expected_output": "Boolean"},
        {"input": {"op": "write_type", "type": "number"}, "expected_output": "Number"},
        {"input": {"op": "write_type", "type": "string"}, "expected_output": "String"},
        {"input": {"op": "write_type", "type": ["list", "bool"]}, "expected_output": "List of Boolean"},
        {"input": {"op": "write_type", "type": ["map", "bool"]}, "expected_output": "Map of Boolean"},
        {"input": {"op": "write_type", "type": ["object", {"bool": "bool"}]}, "expected_output": "Object"},
        {"input": {"op": "write_type", "type": ["list", ["map", ["set", ["object", {"bool": "bool"}]]]]}, "expected_output": "List of Map of Set of Object"}
    ]
}
```

---

### Feature 2: Attribute Inline Label

**As a developer**, I want to render a single scalar attribute into a compact inline label, so each field in the docs shows its type, behavior, and notable markers at a glance.

**Expected Behavior / Usage:**

The input is one attribute carrying a value type plus boolean flags (`required`, `optional`, `computed`, `sensitive`, `deprecated`) and a `description`. The output is a single line. It opens with `(`, then the rendered value type (see Feature 1), then a behavior word: `Required` when the field is required, `Optional` when it is optional (this includes the optional-and-computed combination), and `Read-only` when it is computed only. After the behavior word, `Sensitive` is appended when the field is sensitive and `Deprecated` is appended when it is deprecated, in that order; each marker is comma-separated. The label closes with `)`. If a non-empty description is present, a single space and the description follow the closing parenthesis; leading and trailing whitespace in the description is trimmed.

**Test Cases:** `rcb_tests/public_test_cases/feature2_attribute_label.json`

```json
{
    "description": "Render a single attribute's inline label. The label is wrapped in parentheses and begins with the rendered value type, followed by a behavior word derived from the attribute's flags (Required when required; Optional when optional, including optional+computed; Read-only when computed only), then optional Sensitive and Deprecated markers in that order, and finally the trimmed description text after the closing parenthesis. Surrounding whitespace in the description is trimmed.",
    "cases": [
        {"input": {"op": "attribute_description", "attribute": {"type": "string", "required": true, "description": "This is an attribute."}}, "expected_output": "(String, Required) This is an attribute."},
        {"input": {"op": "attribute_description", "attribute": {"type": "string", "required": true, "description": "This is an attribute.", "deprecated": true}}, "expected_output": "(String, Required, Deprecated) This is an attribute."},
        {"input": {"op": "attribute_description", "attribute": {"type": "string", "required": true, "description": "This is an attribute.", "deprecated": true, "sensitive": true}}, "expected_output": "(String, Required, Sensitive, Deprecated) This is an attribute."},
        {"input": {"op": "attribute_description", "attribute": {"type": "string", "optional": true, "description": "This is an attribute."}}, "expected_output": "(String, Optional) This is an attribute."},
        {"input": {"op": "attribute_description", "attribute": {"type": "string", "optional": true, "computed": true, "description": "This is an attribute."}}, "expected_output": "(String, Optional) This is an attribute."},
        {"input": {"op": "attribute_description", "attribute": {"type": "string", "computed": true, "description": "This is an attribute."}}, "expected_output": "(String, Read-only) This is an attribute."},
        {"input": {"op": "attribute_description", "attribute": {"type": "string", "required": true, "description": " This is an attribute."}}, "expected_output": "(String, Required) This is an attribute."}
    ]
}
```

---

### Feature 3: Nested-Attribute Inline Label

**As a developer**, I want to render an attribute whose type is itself a collection of structured attributes, so nested object fields get a clear inline label distinct from scalar fields.

**Expected Behavior / Usage:**

The input is an attribute whose type is a nested-attribute object with a `nesting_mode` of `single`, `list`, `set`, or `map`, plus optional `min_items`/`max_items` bounds and the usual behavior flags and description. The output is a single line opening with `(Attributes`. A collection word follows the mode: nothing for `single`, ` List`, ` Set`, or ` Map` for the others. For `single` nesting a behavior word (`Required`/`Optional`/`Read-only`, derived exactly as in Feature 2) is appended; for `list`/`set`/`map` nesting the minimum item count is appended as `Min: N` only when greater than zero. A maximum item count is appended as `Max: N` only when greater than zero. Sensitive/Deprecated markers and the trimmed description are appended following the same rules as Feature 2, and the label closes with `)`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_nested_attribute_label.json`

```json
{
    "description": "Render the inline label for an attribute whose type is a nested object collection. The label opens with 'Attributes' plus a collection word (none for single, List/Set/Map otherwise). For single nesting the behavior word (Required/Optional/Read-only) is appended; for List/Set/Map nesting the minimum item count is appended as 'Min: N' when greater than zero. A maximum item count is appended as 'Max: N' when greater than zero, followed by the trimmed description.",
    "cases": [
        {"input": {"op": "nested_attribute_description", "attribute": {"description": "This is an attribute.", "optional": true, "nested_type": {"nesting_mode": "single", "attributes": {"foo": {"type": "string", "required": true, "description": "This is a nested attribute."}}}}}, "expected_output": "(Attributes, Optional) This is an attribute."},
        {"input": {"op": "nested_attribute_description", "attribute": {"description": "This is an attribute.", "required": true, "nested_type": {"nesting_mode": "list", "min_items": 2, "max_items": 3, "attributes": {"foo": {"type": "string", "required": true, "description": "This is a nested attribute."}}}}}, "expected_output": "(Attributes List, Min: 2, Max: 3) This is an attribute."},
        {"input": {"op": "nested_attribute_description", "attribute": {"description": "This is an attribute.", "nested_type": {"nesting_mode": "map", "attributes": {"foo": {"type": "string", "required": true, "description": "This is a nested attribute."}}}}}, "expected_output": "(Attributes Map) This is an attribute."},
        {"input": {"op": "nested_attribute_description", "attribute": {"description": "This is an attribute.", "nested_type": {"nesting_mode": "set", "min_items": 5, "attributes": {"foo": {"type": "string", "required": true, "description": "This is a nested attribute."}}}}}, "expected_output": "(Attributes Set, Min: 5) This is an attribute."}
    ]
}
```

---

### Feature 4: Nested-Block Inline Label

**As a developer**, I want to render a nested configuration block into a compact inline label, so block-style fields are documented consistently with their cardinality.

**Expected Behavior / Usage:**

The input is a nested block with a `nesting_mode` of `single`, `list`, `set`, or `map`, optional `min_items`/`max_items` bounds, and an inner block carrying a `description`, a `deprecated` flag, and child attributes/blocks. The output is a single line opening with `(Block`. A collection word follows the mode: nothing for `single`, ` List`, ` Set`, or ` Map` otherwise. For `single` nesting a behavior word is appended: `Required` when the block has a positive minimum item count; otherwise `Optional` when the block is empty or has any required/optional descendant; otherwise `Read-only` when every leaf is computed-only. For `list`/`set`/`map` nesting the minimum item count is appended as `Min: N` only when greater than zero. A maximum item count is appended as `Max: N` only when greater than zero, then `Deprecated` when the inner block is deprecated, and the label closes with `)` followed by the trimmed block description when present.

**Test Cases:** `rcb_tests/public_test_cases/feature4_block_label.json`

```json
{
    "description": "Render the inline label for a nested block. The label opens with 'Block' plus a collection word (none for single, List/Set/Map otherwise). For single nesting the behavior word (Required/Optional/Read-only) is appended based on the block's minimum items and child characteristics; for List/Set/Map nesting the minimum item count is appended as 'Min: N' when greater than zero. A maximum item count is appended as 'Max: N' when greater than zero, then a Deprecated marker when the block is deprecated, and finally the trimmed block description.",
    "cases": [
        {"input": {"op": "block_description", "block": {"nesting_mode": "single", "block": {"description": "This is a block.", "attributes": {"foo": {"required": true}}}}}, "expected_output": "(Block, Optional) This is a block."},
        {"input": {"op": "block_description", "block": {"nesting_mode": "single", "min_items": 1, "block": {"description": "This is a block."}}}, "expected_output": "(Block, Required) This is a block."},
        {"input": {"op": "block_description", "block": {"nesting_mode": "single", "min_items": 1, "block": {"description": "This is a block.", "deprecated": true}}}, "expected_output": "(Block, Required, Deprecated) This is a block."},
        {"input": {"op": "block_description", "block": {"nesting_mode": "list", "block": {"description": "This is a block."}}}, "expected_output": "(Block List) This is a block."},
        {"input": {"op": "block_description", "block": {"nesting_mode": "list", "min_items": 1, "block": {"description": "This is a block."}}}, "expected_output": "(Block List, Min: 1) This is a block."},
        {"input": {"op": "block_description", "block": {"nesting_mode": "list", "min_items": 1, "max_items": 4, "block": {"description": "This is a block."}}}, "expected_output": "(Block List, Min: 1, Max: 4) This is a block."},
        {"input": {"op": "block_description", "block": {"nesting_mode": "list", "min_items": 1, "max_items": 4, "block": {"description": "This is a block.", "deprecated": true}}}, "expected_output": "(Block List, Min: 1, Max: 4, Deprecated) This is a block."},
        {"input": {"op": "block_description", "block": {"nesting_mode": "map", "block": {"description": "This is a block."}}}, "expected_output": "(Block Map) This is a block."}
    ]
}
```

---

### Feature 5: Whole-Schema Markdown Rendering

**As a developer**, I want to render an entire schema into a complete Markdown reference section, so a resource/data-source/provider page can be generated in one call.

**Expected Behavior / Usage:**

The input is a full schema document: a `version` and a root `block` containing `attributes` and nested `block_types`. The output is a Markdown section beginning with `## Schema` followed by a blank line. Direct child attributes and blocks are partitioned into up to three groups, emitted in the fixed order `### Required`, `### Optional`, `### Read-Only`, each group present only when it has members. Within a group, children are listed alphabetically by name as bullets of the form `` - `name` `` followed by the inline label from Features 2–4 (rendered without the behavior word at top level, since the group heading already conveys it). Nested object attributes and nested blocks are expanded into their own linked sub-sections rendered below the top-level groups. Trailing newlines are not significant.

**Test Cases:** `rcb_tests/public_test_cases/feature5_schema_markdown.json`

```json
{
    "description": "Render a complete provider/resource schema into a Markdown '## Schema' section. Attributes and blocks are partitioned into '### Required', '### Optional' and '### Read-Only' groups, each item rendered as a bullet with its inline type/behavior label, and nested object/block structures are emitted as linked sub-sections below. Input is a full schema document in JSON wire format; output is the rendered Markdown with trailing newlines trimmed.",
    "cases": [
        {
            "input": {
                "op": "render_schema",
                "schema": {
                    "block": {
                        "attributes": {
                            "gateway_id": {"description_kind": "plain", "optional": true, "type": "string"},
                            "id": {"computed": true, "description_kind": "plain", "optional": true, "type": "string"},
                            "route_table_id": {"description_kind": "plain", "required": true, "type": "string"},
                            "subnet_id": {"description_kind": "plain", "optional": true, "type": "string"}
                        },
                        "description_kind": "plain"
                    },
                    "version": 0
                }
            },
            "expected_output": "## Schema\n\n### Required\n\n- `route_table_id` (String)\n\n### Optional\n\n- `gateway_id` (String)\n- `subnet_id` (String)\n\n### Read-Only\n\n- `id` (String) The ID of this resource."
        }
    ]
}
```

---

### Feature 6: Documentation Grouping Classification

**As a developer**, I want to classify a single field into the documentation group it belongs to, so I can bucket fields under Required/Optional/Read-Only headings consistently for both scalar attributes and nested blocks.

**Expected Behavior / Usage:**

The output of each classifier is a single line `role=<category>\n`, where `<category>` is one of `required`, `optional`, or `read_only`. This is the same grouping decision that drives the section headings in Feature 5, exposed as a standalone query.

*6.1 Attribute Classification — classify one scalar attribute into its documentation group*

The input is one attribute with behavior flags. A required attribute yields `role=required`. An optional attribute yields `role=optional`, including the optional-and-computed combination. A computed-only attribute yields `role=read_only`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_classify_attribute.json`

```json
{
    "description": "Classify a single attribute into the documentation grouping role used to bucket it under Required/Optional/Read-Only headings. A required attribute yields role=required, an optional attribute (including optional+computed) yields role=optional, and a computed-only attribute yields role=read_only.",
    "cases": [
        {"input": {"op": "classify_attribute", "attribute": {"type": "string", "required": true, "description": "This is an attribute."}}, "expected_output": "role=required\n"},
        {"input": {"op": "classify_attribute", "attribute": {"type": "string", "optional": true, "description": "This is an attribute."}}, "expected_output": "role=optional\n"},
        {"input": {"op": "classify_attribute", "attribute": {"type": "string", "computed": true, "description": "This is an attribute."}}, "expected_output": "role=read_only\n"},
        {"input": {"op": "classify_attribute", "attribute": {"type": "string", "optional": true, "computed": true, "description": "This is an attribute."}}, "expected_output": "role=optional\n"}
    ]
}
```

*6.2 Block Classification — classify one nested block into its documentation group*

The input is one nested block. A block with a positive minimum item count yields `role=required`. A zero-minimum block that is either empty or has at least one required-or-optional descendant (attribute or sub-block) yields `role=optional`. A block whose every leaf is computed-only yields `role=read_only`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_classify_block.json`

```json
{
    "description": "Classify a single nested block into the documentation grouping role. A block with a minimum item count above zero yields role=required; a zero-minimum block that is empty or contains any required/optional descendant yields role=optional; a block whose every leaf is computed-only yields role=read_only.",
    "cases": [
        {"input": {"op": "classify_block", "block": {"nesting_mode": "single", "min_items": 1, "block": {"description": "b", "attributes": {"foo": {"type": "string", "required": true, "description": "a"}}}}}, "expected_output": "role=required\n"},
        {"input": {"op": "classify_block", "block": {"nesting_mode": "single", "block": {"description": "b", "attributes": {"foo": {"type": "string", "optional": true, "description": "a"}}}}}, "expected_output": "role=optional\n"},
        {"input": {"op": "classify_block", "block": {"nesting_mode": "single", "block": {"description": "b", "attributes": {"foo": {"type": "string", "computed": true, "description": "a"}}}}}, "expected_output": "role=read_only\n"},
        {"input": {"op": "classify_block", "block": {"nesting_mode": "single", "block": {"description": "empty"}}}, "expected_output": "role=optional\n"},
        {"input": {"op": "classify_block", "block": {"nesting_mode": "single", "block": {"description": "b", "block_types": {"foo": {"min_items": 1, "block": {"attributes": {"foo": {"type": "string", "required": true, "description": "a"}}}}}}}}, "expected_output": "role=optional\n"}
    ]
}
```

---

### Feature 7: Documentation Text Helpers

**As a developer**, I want small text-formatting helpers used while assembling documentation pages, so templates can flatten Markdown, indent blocks, and embed source files without bespoke code.

**Expected Behavior / Usage:**

*7.1 Plain-Text Markdown Flattening — strip Markdown markup to readable plain text*

The input is Markdown source text. The output is that text with formatting markup removed: headings lose their `#` markers, emphasis and inline-code markup is stripped to its inner text, and the readable textual content is preserved.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_plain_markdown.json`

```json
{
    "description": "Flatten Markdown source into plain text, stripping formatting markup (headings, emphasis, inline code, list markers) while preserving the readable textual content.",
    "cases": [
        {"input": {"op": "plain_markdown", "text": "my Odly cAsed striNg"}, "expected_output": "my Odly cAsed striNg"},
        {"input": {"op": "plain_markdown", "text": "# Heading\n\nSome **bold** and `code` text."}, "expected_output": "Heading\nSome bold and code text."}
    ]
}
```

*7.2 Line Prefixing — prepend a fixed[a configurable line prefix]to every line*

The input is a[a configurable line prefix]string and a multi-line text block. The output prepends the[a configurable line prefix]to every line, including the first, preserving the existing line breaks.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_prefix_lines.json`

```json
{
    "description": "Prepend a fixed[a configurable line prefix]string to every line of a multi-line text block, including the first line, leaving line breaks otherwise intact.",
    "cases": [
        {"input": {"op": "prefix_lines", "prefix": "  ", "text": "This text used\nmultiple lines"}, "expected_output": "  This text used\n  multiple lines"},
        {"input": {"op": "prefix_lines", "prefix": "> ", "text": "single line"}, "expected_output": "> single line"}
    ]
}
```

*7.3 Source File Embedding — wrap a file's contents in a fenced code block*

The input is a language/format tag and a file path. On success the output is the file's contents (trimmed of surrounding whitespace) wrapped in a fenced code block whose opening fence carries the format tag. When the file cannot be read, the output is a normalized error: the line `error=file_not_found` followed by a line `file=<requested path>`. Errors never leak host-language exception names or runtime message text.

**Test Cases:** `rcb_tests/public_test_cases/feature7_3_code_file.json`

```json
{
    "description": "Read a source file from disk and wrap its trimmed contents in a fenced code block tagged with the given format/language. When the file cannot be read, a normalized file_not_found error is produced naming the requested file.",
    "cases": [
        {"input": {"op": "code_file", "format": "terraform", "file": "provider.tf"}, "expected_output": "```terraform\nprovider \"scaffolding\" {\n  # example configuration here\n}\n```"},
        {"input": {"op": "code_file", "format": "terraform", "file": "missing.tf"}, "expected_output": "error=file_not_found\nfile=missing.tf\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-module codebase implementing the rendering and classification features above (type rendering, attribute/nested-attribute/block label rendering, whole-schema rendering, grouping classification, and text helpers), decoupled from any I/O concern.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads a single JSON command object from stdin (`op` selects the operation; the remaining fields carry the operands described per feature), invokes the matching core function, and prints the raw result to stdout, strictly matching the per-leaf-feature contracts above. The adapter is responsible for translating any core error into the normalized, language-neutral contract lines shown above; it must be logically and physically separated from the core domain. A small fixture file (the embeddable source file referenced by Feature 7.3) is provided alongside the adapter.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_type_name_rendering.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_type_name_rendering@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the sensitive append convention
- use the default nesting syntax
