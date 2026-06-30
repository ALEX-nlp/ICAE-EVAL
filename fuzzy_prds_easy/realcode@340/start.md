## Product Requirement Document

# Schema & Route Annotation Engine - Generating In-File Documentation Comments

## Project Goal

Build a library and command-line tool that generates human-readable comment blocks describing a relational database table and a project's request-routing table, and that inserts, refreshes, or removes those comment blocks inside source files. It allows developers to keep an always-current summary of their schema and routes pinned directly in their code, without hand-writing or hand-maintaining those comments.

---

## Background & Problem

Without this tool, developers who want a quick reference to a table's columns, indexes, foreign keys, and constraints — or to the project's route table — must read migrations, open a database console, or run a separate routing command, then manually transcribe the results into comments. Those hand-maintained comments drift out of date the moment the schema or routes change, and reformatting them by hand for different documentation styles is tedious and error-prone.

With this tool, the description is derived mechanically from a structured table description (or a raw route listing) and rendered into a consistent, aligned comment block. The same source can be rendered in several documentation styles, filtered and reordered, and the block can be inserted into or stripped from a file idempotently, so the embedded documentation stays correct and consistent with no manual upkeep.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility domain (column formatting, section builders for indexes/foreign-keys/check-constraints, multiple output styles, an argument parser, and a file-rewriting routine for routes). It MUST NOT be a single "god file". Output a clear, multi-file directory tree (e.g. `src/` for the core builders and `tests/` for the suite) that reflects a production-grade repository. Do not over-engineer, but strictly avoid a monolith.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in the "Core Features" section are a **black-box contract for the execution adapter**, NOT the internal data model. The core builders must operate on domain objects (a table description, a column, an index, an argument vector, a file body) and must not parse JSON or read stdin/stdout themselves. The execution adapter is solely responsible for translating JSON commands into idiomatic calls into the core and rendering results to stdout.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Keep type formatting, attribute assembly, default-value formatting, each section builder, style selection, argument parsing, and file rewriting as distinct units.
   - **Open/Closed Principle (OCP):** Adding a new output style or a new section must not require modifying existing builders.
   - **Liskov Substitution Principle (LSP):** All output-style renderers must be substitutable behind one rendering interface.
   - **Interface Segregation Principle (ISP):** Keep renderer and builder interfaces small and cohesive.
   - **Dependency Inversion Principle (DIP):** High-level assembly logic must depend on builder/renderer abstractions, not on concrete I/O.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The core's public interface must be elegant and idiomatic to the target language, hiding alignment math and string assembly behind clear method calls.
   - **Resilience:** Handle edge cases gracefully — absent expressions, columns that permit null, unnamed foreign keys, empty route listings, missing target files. Errors must be modeled as proper error types, and the adapter must translate any raised error into a neutral `error=<category>` line (e.g. `error=missing_field`) rather than leaking host-language runtime detail.

---

## Core Features

### Feature 1: Table Schema Annotation Block

**As a developer**, I want a structured description of a database table rendered into an aligned, hash-commented summary block, so I can keep an accurate schema reference pinned in my model files.

**Expected Behavior / Usage:**

The operation reads one JSON object describing a single table and writes the rendered comment block to stdout. The object carries `table_name` (string), `primary_key` (a column name, an array of names for a composite key, or `null`), an `options` object of formatting switches, and ordered arrays `columns`, `indexes`, `foreign_keys`, and `check_constraints`. Output is a pure function of the input: the same input always yields the same bytes. A column descriptor has `name` and `type` (required) plus optional `limit`, `null` (defaults to non-null), `default`, `precision`, `scale`, `comment`, and `array`. This feature groups the leaf functional points below; each leaf block is self-contained.

*1.1 Basic column block — The skeleton of the block and the per-column line.*

The block opens with a title line, a blank comment line, the table-name line, then one comment line per column showing the column name, its type token, and a `not null` marker, and closes with a blank comment line. The column flagged as the table primary key additionally gets a `primary key` marker; a column that permits null omits the `not null` marker. Column name and type are padded to fixed widths for alignment.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_basic_column_block.json`

```json
{
  "description": "Rendering the core annotation block for a table: an opening header line, a blank comment line, the table-name line, one formatted line per column listing its name, its type and any non-null marker, and a closing blank comment line. A column flagged as the table primary key is marked accordingly, and a column that permits null omits the non-null marker.",
  "cases": [
    {
      "input": {
        "table_name": "users",
        "primary_key": "id",
        "options": {},
        "columns": [
          {"name": "id", "type": "integer"},
          {"name": "name", "type": "string", "limit": 50}
        ]
      },
      "expected_output": "# == Schema Information\n#\n# Table name: users\n#\n#  id   :integer          not null, primary key\n#  name :string(50)       not null\n#\n"
    }
  ]
}
```

*1.2 Type token formatting — How the type cell is rendered.*

String-like types append their length in parentheses (e.g. `string(120)`); decimal types render precision and scale as `decimal(p, s)`; a length supplied as a list is not appended to the type token (it surfaces as a separate attribute instead); the set of types whose length suffix is suppressed can be overridden through an option.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_type_formatting.json`

```json
{
  "description": "Formatting of the column type token. String-like types append their length in parentheses, decimal types render their precision and scale, a type whose length is supplied as a list renders that list as a separate attribute while keeping a bare type token, list-backed columns gain an array marker, and the set of types whose length is suppressed can be overridden through an option.",
  "cases": [
    {
      "input": {
        "table_name": "products",
        "primary_key": "id",
        "options": {},
        "columns": [
          {"name": "id", "type": "integer"},
          {"name": "title", "type": "string", "limit": 120},
          {"name": "price", "type": "decimal", "precision": 10, "scale": 2}
        ]
      },
      "expected_output": "# == Schema Information\n#\n# Table name: products\n#\n#  id    :integer          not null, primary key\n#  title :string(120)      not null\n#  price :decimal(10, 2)   not null\n#\n"
    }
  ]
}
```

*1.3 Default values — How a column's default is shown.*

When a column has a default it is shown as a `default(...)` attribute: numbers verbatim, booleans as upper-case keywords, strings quoted, list defaults as a bracketed list. A column without a default omits the attribute. Types configured to suppress defaults (such as JSON-family types) never show one.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_default_values.json`

```json
{
  "description": "Display of column default values as an attribute. Numeric defaults are shown verbatim, boolean defaults are shown as upper-case keywords, string defaults are shown quoted, a column without a default omits the attribute entirely, and types configured to suppress defaults never show one.",
  "cases": [
    {
      "input": {
        "table_name": "accounts",
        "primary_key": "id",
        "options": {},
        "columns": [
          {"name": "id", "type": "integer"},
          {"name": "active", "type": "boolean", "default": true},
          {"name": "balance", "type": "integer", "default": 0},
          {"name": "tier", "type": "string", "limit": 20, "default": "guest"}
        ]
      },
      "expected_output": "# == Schema Information\n#\n# Table name: accounts\n#\n#  id      :integer          not null, primary key\n#  active  :boolean          default(TRUE), not null\n#  balance :integer          default(0), not null\n#  tier    :string(20)       default(\"guest\"), not null\n#\n"
    },
    {
      "input": {
        "table_name": "notes",
        "primary_key": "id",
        "options": {},
        "columns": [
          {"name": "id", "type": "integer"},
          {"name": "body", "type": "string", "limit": 40, "null": true, "default": null}
        ]
      },
      "expected_output": "# == Schema Information\n#\n# Table name: notes\n#\n#  id   :integer          not null, primary key\n#  body :string(40)\n#\n"
    }
  ]
}
```

*1.4 Indexes section — A section listing the table's indexes.*

When index display is enabled an `Indexes` section follows the columns. Each index renders its name and parenthesised column list, with trailing markers for uniqueness (`UNIQUE`), a partial predicate (`WHERE ...`), a non-default access method (`USING ...`), and per-column ordering (`col DESC`). Names are width-aligned and sorted. A separate inline mode instead annotates each indexed column on its own line with an `indexed` marker.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_indexes.json`

```json
{
  "description": "An indexes section appended after the columns when index display is enabled. Each index renders its name and parenthesised column list, with markers for uniqueness, a partial predicate, a non-default access method, and per-column ordering. A separate inline mode instead annotates each indexed column on its own line.",
  "cases": [
    {
      "input": {
        "table_name": "users",
        "primary_key": "id",
        "options": {"show_indexes": true},
        "columns": [
          {"name": "id", "type": "integer"},
          {"name": "email", "type": "string", "limit": 255, "null": true}
        ],
        "indexes": [
          {"name": "index_users_on_email", "columns": ["email"], "unique": true},
          {"name": "index_users_on_team_and_role", "columns": ["team", "role"]}
        ]
      },
      "expected_output": "# == Schema Information\n#\n# Table name: users\n#\n#  id    :integer          not null, primary key\n#  email :string(255)\n#\n# Indexes\n#\n#  index_users_on_email          (email) UNIQUE\n#  index_users_on_team_and_role  (team,role)\n#\n"
    }
  ]
}
```

*1.5 Foreign keys section — A section listing the table's foreign keys.*

When foreign-key display is enabled a `Foreign Keys` section follows the columns. Each entry shows its name and the `from_column => to_table.to_column` mapping, plus optional `ON DELETE`/`ON UPDATE` cascade actions. Auto-generated names matching a hashed pattern are abbreviated to an ellipsis unless complete names are requested; an unnamed key falls back to its column name; a custom target column is honoured. Entries are width-aligned and sorted.

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_foreign_keys.json`

```json
{
  "description": "A foreign keys section appended after the columns when foreign-key display is enabled. Each entry shows its name and the referencing-to-referenced column mapping, optionally with cascade actions. Auto-generated names are abbreviated unless full names are requested, an unnamed key falls back to its column, and a custom target column is honoured.",
  "cases": [
    {
      "input": {
        "table_name": "orders",
        "primary_key": "id",
        "options": {"show_foreign_keys": true},
        "columns": [
          {"name": "id", "type": "integer"},
          {"name": "user_id", "type": "integer", "null": true}
        ],
        "foreign_keys": [
          {"name": "fk_rails_a1b2c3d4e5", "column": "user_id", "to_table": "users"}
        ]
      },
      "expected_output": "# == Schema Information\n#\n# Table name: orders\n#\n#  id      :integer          not null, primary key\n#  user_id :integer\n#\n# Foreign Keys\n#\n#  fk_rails_...  (user_id => users.id)\n#\n"
    },
    {
      "input": {
        "table_name": "comments",
        "primary_key": "id",
        "options": {"show_foreign_keys": true},
        "columns": [
          {"name": "id", "type": "integer"},
          {"name": "post_id", "type": "integer", "null": true}
        ],
        "foreign_keys": [
          {"name": "fk_posts", "column": "post_id", "to_table": "posts", "on_delete": "cascade", "on_update": "restrict"}
        ]
      },
      "expected_output": "# == Schema Information\n#\n# Table name: comments\n#\n#  id      :integer          not null, primary key\n#  post_id :integer\n#\n# Foreign Keys\n#\n#  fk_posts  (post_id => posts.id) ON DELETE => cascade ON UPDATE => restrict\n#\n"
    }
  ]
}
```

*1.6 Check constraints section — A section listing the table's check constraints.*

When check-constraint display is enabled a `Check Constraints` section follows the columns. Each constraint renders its name followed by its boolean expression in parentheses; a constraint with no expression shows only its name; multi-line expressions are collapsed to a single spaced line; entries are sorted by name and width-aligned.

**Test Cases:** `rcb_tests/public_test_cases/feature1_6_check_constraints.json`

```json
{
  "description": "A check-constraints section appended after the columns when check-constraint display is enabled. Each constraint renders its name followed by its boolean expression in parentheses; a constraint with no expression shows only its name; multi-line expressions are collapsed to a single spaced line; entries are sorted by name and the name column is width-aligned. A Markdown rendering mode emits the same information as a bulleted list with code-formatted names and expressions.",
  "cases": [
    {
      "input": {
        "table_name": "users",
        "primary_key": "id",
        "options": {"show_check_constraints": true},
        "columns": [
          {"name": "id", "type": "integer"},
          {"name": "age", "type": "integer", "null": true}
        ],
        "check_constraints": [
          {"name": "alive", "expression": "age < 150"},
          {"name": "must_be_adult", "expression": "age >= 18"},
          {"name": "missing_expression", "expression": null},
          {"name": "multiline_test", "expression": "CASE\n  WHEN (age >= 18) THEN (age <= 21)\n  ELSE true\nEND\n"}
        ]
      },
      "expected_output": "# == Schema Information\n#\n# Table name: users\n#\n#  id  :integer          not null, primary key\n#  age :integer\n#\n# Check Constraints\n#\n#  alive               (age < 150)\n#  missing_expression\n#  multiline_test      (CASE WHEN (age >= 18) THEN (age <= 21) ELSE true END)\n#  must_be_adult       (age >= 18)\n#\n"
    }
  ]
}
```

*1.7 Column comments — Appending a database comment to a column.*

When comment display is enabled, each column whose comment is present appends the comment text in parentheses after its name, and the appended text participates in the alignment width of the block.

**Test Cases:** `rcb_tests/public_test_cases/feature1_7_column_comments.json`

```json
{
  "description": "Column comment rendering. When comment display is enabled, each column whose comment is present appends the comment text in parentheses after its name, and the appended text participates in the alignment width of the block.",
  "cases": [
    {
      "input": {
        "table_name": "users",
        "primary_key": "id",
        "options": {"with_comment": true, "with_column_comments": true},
        "columns": [
          {"name": "id", "type": "integer", "comment": "identifier"},
          {"name": "name", "type": "string", "limit": 50, "comment": "full name"}
        ]
      },
      "expected_output": "# == Schema Information\n#\n# Table name: users\n#\n#  id(identifier)  :integer          not null, primary key\n#  name(full name) :string(50)       not null\n#\n"
    }
  ]
}
```

*1.8 Ordering and filtering — Controlling which columns appear and in what order.*

Columns may be sorted alphabetically, or grouped by a classification that places the primary key first, then ordinary columns, then timestamp columns, then association columns (each group internally sorted). Columns whose name matches an ignore pattern are dropped, and an optional schema-version line may be appended to the header when a version is supplied and version display is enabled.

**Test Cases:** `rcb_tests/public_test_cases/feature1_8_ordering_and_filters.json`

```json
{
  "description": "Column ordering and filtering controls. Columns may be sorted alphabetically, or grouped by a classification that places the primary key first followed by ordinary, timestamp and association columns. Columns matching an ignore pattern are dropped, and an optional schema version line may be appended to the header.",
  "cases": [
    {
      "input": {
        "table_name": "items",
        "primary_key": "id",
        "options": {"sort": true},
        "columns": [
          {"name": "id", "type": "integer"},
          {"name": "zeta", "type": "string", "limit": 5},
          {"name": "alpha", "type": "string", "limit": 5}
        ]
      },
      "expected_output": "# == Schema Information\n#\n# Table name: items\n#\n#  alpha :string(5)        not null\n#  id    :integer          not null, primary key\n#  zeta  :string(5)        not null\n#\n"
    }
  ]
}
```

*1.9 Markdown style — Rendering the block as Markdown.*

In Markdown mode the title and section headings switch to Markdown headings, the table name is wrapped in code formatting, and columns render as a Markdown table with aligned name, type, and attribute cells.

**Test Cases:** `rcb_tests/public_test_cases/feature1_9_markdown_format.json`

```json
{
  "description": "Markdown rendering mode. The header and section titles switch to Markdown headings, the table name is wrapped in code formatting, and columns render as a Markdown table with aligned name, type and attribute cells. Index and foreign-key sections render as Markdown lists.",
  "cases": [
    {
      "input": {
        "table_name": "users",
        "primary_key": "id",
        "options": {"format_markdown": true},
        "columns": [
          {"name": "id", "type": "integer"},
          {"name": "email", "type": "string", "limit": 255}
        ]
      },
      "expected_output": "# [a specific markdown-level header string]\n#\n# Table name: `users`\n#\n# ### Columns\n#\n# Name         | Type               | Attributes\n# ------------ | ------------------ | ---------------------------\n# **`id`**     | `integer`          | `not null, primary key`\n# **`email`**  | `string(255)`      | `not null`\n#\n"
    }
  ]
}
```

*1.10 RDoc style — Rendering the block as RDoc.*

In RDoc mode each column renders as an RDoc definition entry pairing the column name with its type and attributes in inline-code markup, and the whole block is wrapped with RDoc begin/end schema markers.

**Test Cases:** `rcb_tests/public_test_cases/feature1_10_rdoc_format.json`

```json
{
  "description": "RDoc rendering mode. Each column renders as an RDoc definition entry pairing the column name with its type and attributes in inline-code markup, and the block is wrapped with the RDoc begin/end schema markers.",
  "cases": [
    {
      "input": {
        "table_name": "users",
        "primary_key": "id",
        "options": {"format_rdoc": true},
        "columns": [
          {"name": "id", "type": "integer"},
          {"name": "name", "type": "string", "limit": 50}
        ]
      },
      "expected_output": "# == Schema Information\n#\n# Table name: users\n#\n# *id*::   <tt>integer, not null, primary key</tt>\n# *name*:: <tt>string(50), not null</tt>\n#--\n# == Schema Information End\n#++\n"
    }
  ]
}
```

*1.11 YARD style — Rendering the block as YARD.*

In YARD mode each column renders as a YARD attribute directive followed by a return-type line, where the database type is mapped to a corresponding language class name and length suffixes are omitted. A type with no mapping yields an empty return-type bracket.

**Test Cases:** `rcb_tests/public_test_cases/feature1_11_yard_format.json`

```json
{
  "description": "YARD rendering mode. Each column renders as a YARD attribute directive followed by a return-type line, where the database type is mapped to a corresponding language class name and length suffixes are omitted.",
  "cases": [
    {
      "input": {
        "table_name": "users",
        "primary_key": "id",
        "options": {"format_yard": true},
        "columns": [
          {"name": "id", "type": "integer"},
          {"name": "name", "type": "string", "limit": 50},
          {"name": "balance", "type": "decimal", "precision": 8, "scale": 2},
          {"name": "created_at", "type": "datetime"}
        ]
      },
      "expected_output": "# == Schema Information\n#\n# Table name: users\n#\n# @!attribute id\n#   @return [Integer]\n# @!attribute name\n#   @return [String]\n# @!attribute balance\n#   @return []\n# @!attribute created_at\n#   @return [Time]\n#\n"
    }
  ]
}
```

---

### Feature 2: Command-Line Argument Parsing

**As a developer**, I want a single argument vector turned into a resolved set of named settings, so I can drive the tool from a terminal with predictable, well-defined options.

**Expected Behavior / Usage:**

The operation reads a JSON object with an `args` array (the argument vector) and an optional `existing_options` object of pre-set values, and writes the resolved settings to stdout as sorted `key=value` lines. The selected command is rendered as `command=<models|routes|help|version>`; boolean settings render as `true`/`false`; list-valued settings render as comma-joined; absent values render empty. Only settings actually established by parsing are emitted (the parser does not back-fill every possible default). The leaf blocks below cover the distinct parsing behaviors.

*2.1 Command selection — Choosing the sub-command.*

The leading word of the vector selects a command: the model-annotation command, the route-annotation command, the help command, or the version command. When no recognised command word leads the vector, the help command is selected by default. The default action stays the annotate action unless changed.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_command_selection.json`

```json
{
  "description": "Resolving the leading sub-command word of an argument vector into a selected command identifier. The recognised words select the model-annotation command, the route-annotation command, the help command, and the version command respectively. When no recognised command word is present, the help command is selected by default. The default action remains the annotate action unless changed by other arguments.",
  "cases": [
    {"input": {"op": "cli", "args": ["models"]}, "expected_output": "command=models\ntarget_action=do_annotations\n"},
    {"input": {"op": "cli", "args": ["routes"]}, "expected_output": "command=routes\ntarget_action=do_annotations\n"},
    {"input": {"op": "cli", "args": []}, "expected_output": "command=help\ntarget_action=do_annotations\n"}
  ]
}
```

*2.2 Annotation placement — Where annotations are written within a file.*

A global placement argument accepts one of `before`, `top`, `after`, or `bottom` and applies it to every per-file-type placement setting at once. Per-file-type placement arguments set only their own target. When a per-file-type placement is given an explicit value, a later global placement does not override that already-set per-file-type value.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_annotation_positioning.json`

```json
{
  "description": "Parsing of annotation-placement arguments. A global placement argument accepts one of the keywords before, top, after, or bottom and applies it to every per-file-type placement setting simultaneously. Per-file-type placement arguments set only their own target. When a per-file-type placement is given an explicit value, a subsequent global placement does not override that already-set per-file-type value.",
  "cases": [
    {"input": {"op": "cli", "args": ["-p", "before"]}, "expected_output": "command=help\nposition=before\nposition_in_class=before\nposition_in_factory=before\nposition_in_fixture=before\nposition_in_routes=before\nposition_in_serializer=before\nposition_in_test=before\ntarget_action=do_annotations\n"},
    {"input": {"op": "cli", "args": ["--pc", "top", "-p", "bottom"]}, "expected_output": "command=help\nposition=bottom\nposition_in_class=top\nposition_in_factory=bottom\nposition_in_fixture=bottom\nposition_in_routes=bottom\nposition_in_serializer=bottom\nposition_in_test=bottom\ntarget_action=do_annotations\n"}
  ]
}
```

*2.3 Flags and value options — Switches, list expansion, and repeatable values.*

Boolean switches turn a named setting on: a delete switch flips the action to removal; index display, foreign-key display, and check-constraint display each enable their section; one composite switch enables two related settings at once. A comma-list exclusion option expands into one enabled setting per named group. Value options capture their argument verbatim (a column-ignore pattern, a hide-limit type list). A repeatable path option appends to any previously supplied value rather than replacing it.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_flags_and_values.json`

```json
{
  "description": "Parsing of boolean switches and value-bearing options into normalized settings. Switches turn a named setting on (delete-mode flips the action to removal; index display, foreign-key display, and check-constraint display each enable their section). One composite switch enables two related settings at once. A comma list option for excluded artifact groups expands into one enabled setting per named group. Value options capture their argument verbatim (a column-ignore pattern, a hide-limit type list). A repeatable path option appends to any previously supplied value rather than replacing it.",
  "cases": [
    {"input": {"op": "cli", "args": ["-d"]}, "expected_output": "command=help\ntarget_action=remove_annotations\n"},
    {"input": {"op": "cli", "args": ["-e", "tests,fixtures"]}, "expected_output": "command=help\nexclude_fixtures=true\nexclude_tests=true\ntarget_action=do_annotations\n"},
    {"input": {"op": "cli", "args": ["-R", "another_dir"], "existing_options": {"require": "some_dir/"}}, "expected_output": "command=help\nrequire=some_dir/,another_dir\ntarget_action=do_annotations\n"}
  ]
}
```

---

### Feature 3: Route Map Annotation In-File

**As a developer**, I want the project's route listing rendered into a comment block and inserted into or removed from a routes file idempotently, so the routing reference stays embedded and current without manual edits.

**Expected Behavior / Usage:**

The operation reads a JSON object with an `action` (`add` or `remove`), a `file_present` flag, the current `routes_file_content` string, and for the add action a `rails_routes_output` string (the raw route listing) plus an `options` object. It returns a `status=<token>` line — `annotated`, `unchanged`, `removed`, or `not_found` — and, when the file is rewritten, a `file=<path>` line followed by the new file body. The route listing has one route per line with columns prefix, verb, URI pattern, and controller#action.

*3.1 Insert route map — Adding the annotation block.*

Given the file content and the raw route listing, the tool produces an updated file containing a titled, hash-commented route map: each route line preserved and right-aligned under a header row. By default the block is appended after existing content, separated by a blank line; a top placement option prepends it instead; a Markdown mode renders the routes as a pipe-delimited table. When the target file is absent the status is `not_found` and nothing is written.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_route_map_add.json`

```json
{
  "description": "Inserting a route-map annotation block into a routes file. Given the current file content and the raw route listing (prefix, verb, URI pattern, controller#action per line), the tool produces an updated file containing a titled, hash-commented route map. Each route line is preserved and right-aligned under a header row. By default the annotation is appended after existing content separated by a blank line; a top placement option instead prepends it. A Markdown mode renders the routes as a pipe-delimited table. The reported status indicates whether the file was changed.",
  "cases": [
    {
      "input": {
        "op": "routes",
        "action": "add",
        "file_present": true,
        "routes_file_content": "",
        "rails_routes_output": "                Prefix Verb       URI Pattern                  Controller#Action\n             myaction1 GET        /url1(.:format)              mycontroller1#action\n             myaction2 POST       /url2(.:format)              mycontroller2#action\n"
      },
      "expected_output": "status=annotated\nfile=config/routes.rb\n\n# == Route Map\n#\n#                 Prefix Verb       URI Pattern                  Controller#Action\n#              myaction1 GET        /url1(.:format)              mycontroller1#action\n#              myaction2 POST       /url2(.:format)              mycontroller2#action\n"
    },
    {
      "input": {"op": "routes", "action": "add", "file_present": false},
      "expected_output": "status=not_found\n"
    }
  ]
}
```

*3.2 Remove route map — Stripping the annotation block.*

The titled, hash-commented annotation block is removed while genuine file content and unrelated leading comment lines are preserved. When the annotation was trailing, the trailing blank lines it introduced are trimmed while leading blank lines are left intact; when it was leading, the reverse holds. The status reports that annotations were removed.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_route_map_remove.json`

```json
{
  "description": "Removing a route-map annotation block from a routes file. The titled, hash-commented annotation block is stripped while genuine file content and unrelated leading comment lines are preserved. When the annotation was trailing, trailing blank lines introduced by it are trimmed but leading blank lines are left intact; when the annotation was leading, the reverse holds. The reported status indicates that annotations were removed.",
  "cases": [
    {
      "input": {
        "op": "routes",
        "action": "remove",
        "file_present": true,
        "routes_file_content": "\n\n\nRails.application.routes.draw do\n  root 'root#index'\nend\n\n\n# == Route Map\n#\n# another good line\n# good line\n"
      },
      "expected_output": "status=removed\nfile=config/routes.rb\n\n\n\nRails.application.routes.draw do\n  root 'root#index'\nend\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the schema-block builders (column line, type token, attributes, default values, indexes, foreign keys, check constraints, comments, ordering/filtering, and the Markdown/RDoc/YARD styles), the argument parser, and the route-map insert/remove routine. Its physical structure MUST follow the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core. It reads one JSON command object from stdin, selects the operation (`schema` by default, or `cli`/`routes` via an `op` field), invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. It must translate any error raised by the core into a neutral `error=<category>` line and must be logically separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_basic_column_block.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_basic_column_block@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- apply the marker convention used in the primary key renderer
- format the link as seen in the existing foreign key output examples
