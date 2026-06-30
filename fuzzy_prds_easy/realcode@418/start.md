## Product Requirement Document

# Plain-Language Scenario Runner - Behavioural Test Execution Engine

## Project Goal

Build a scenario execution engine that lets developers describe software behaviour in structured, plain-language scenarios (a feature title, optional shared setup, and one or more scenarios made of ordered steps) and then run those scenarios, reporting for each one whether it passed, failed, was left undefined, or is still pending. The engine binds each step phrase to an implementation, executes the matching scenarios subject to selection rules, classifies the outcome, and produces a stable machine-readable report so that behaviour specifications double as an automated regression suite.

---

## Background & Problem

Without this engine, developers verifying that an application behaves as specified must either translate every acceptance criterion into hand-written, low-level test code, or check behaviour manually. The specification (what the business expects) and the test (what the machine checks) drift apart: prose lives in one document, assertions in another, and nobody can tell which scenarios are covered, which are merely planned, and which are silently broken.

With this engine, the specification *is* the test. A scenario is written once in plain language; each line ("step") is matched to a small piece of glue code that performs the action or assertion. Running the suite tells you exactly how many scenarios passed, failed, are undefined (no glue yet), or pending (glue exists but is explicitly marked unfinished), and lets you slice the suite by tag, by name, or by source position so large suites stay manageable.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a non-trivial system with several distinct responsibilities (source parsing, scenario compilation, selection/filtering, step matching, execution, result classification, report formatting, snippet suggestion, localized keyword lookup). It MUST NOT be a single "god file". Provide a clear, multi-file directory tree (e.g. `src/`/`lib/`, `tests/`) that reflects a production-grade repository, with each responsibility isolated. Do not over-engineer, but do not collapse the domain into one module either.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in the "Core Features" section are a **black-box contract for an execution adapter**, not the internal data model of the engine. The core engine must be usable as a library through idiomatic calls and must not know anything about JSON, stdin/stdout, or the specific wire format used by the tests. A thin execution adapter is solely responsible for parsing a JSON command, driving the core, and rendering the neutral output lines.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Keep parsing, selection, matching, execution, classification, and formatting in distinct units.
   - **Open/Closed Principle (OCP):** New report formats, new selection strategies, or new step-result categories should be addable without rewriting the execution core.
   - **Liskov Substitution Principle (LSP):** All step-result categories and all selection filters must be substitutable behind their respective abstractions.
   - **Interface Segregation Principle (ISP):** A formatter should depend only on the run-report shape it consumes, not on execution internals.
   - **Dependency Inversion Principle (DIP):** The execution core depends on abstractions for "where do scenarios come from" and "where does output go", not on concrete I/O.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the engine must be elegant and idiomatic to the target language.
   - **Resilience:** Configuration errors (an impossible selection limit, an unknown language code, no scenario sources at all) must be modelled as distinct, typed error conditions and surfaced as neutral error categories — never as a crash dump. Step-level failures must be contained so the run can classify and continue.

---

## Core Features

### Feature 1: Run scenarios and classify results

**As a developer**, I want to run a set of plain-language scenarios and get each scenario's outcome plus aggregate counts, so I can see at a glance what passes, fails, is undefined, or is pending.

**Expected Behavior / Usage:**

The input is a `run` command carrying a set of source files (each a feature with scenarios and steps) and a set of step bindings. Each binding declares a phrase pattern and the outcome that phrase produces when executed: `pass` (does nothing and succeeds), `fail` (raises, optionally with a message), `pending` (signals "not yet implemented"). A step phrase with no matching binding is classified `undefined`. The engine executes every scenario and emits, in order: a `scenarios` tally line, a `steps` tally line, one `scenario ...` line per executed scenario (carrying its keyword, name, source line, and resolved status), and a final `result=` line. A scenario's status is the worst of its steps' statuses under the precedence failed > undefined > pending > skipped > passed. The run-level `result` is `ok` when no scenario failed, `failed` when at least one scenario failed, and `error` for configuration errors. Tags written on scenarios do not change classification here; they exist for later selection.

**Test Cases:** `rcb_tests/public_test_cases/feature1_result_classification.json`

```json
{
  "description": "Run a set of plain-language scenarios where each step declares its own outcome, and report the per-scenario classification plus aggregate tallies. A scenario's classification is the worst of its step outcomes, with precedence failed > undefined > pending > skipped > passed. A step whose phrase matches no definition is 'undefined'; a step that signals it is not yet implemented is 'pending'; a step that raises is 'failed'. The final 'result' line is the run-level category: 'ok' when nothing failed, 'failed' when at least one scenario failed or (in plain mode) every step still ran, 'error' for configuration errors.",
  "cases": [
    {
      "input": {
        "command": "run",
        "args": ["-q"],
        "steps": [
          {"pattern": "^this step passes$", "outcome": "pass"},
          {"pattern": "^this step fails$", "outcome": "fail", "message": "boom"},
          {"pattern": "^this step is pending$", "outcome": "pending"}
        ],
        "files": [
          {"path": "features/test.feature", "content": "@a\nFeature: Sample\n  @b\n  Scenario: P\n    Given this step passes\n  @c\n  Scenario: F\n    Given this step fails\n  Scenario: U\n    Given this step is undefined\n  Scenario: D\n    Given this step is pending\n"}
        ]
      },
      "expected_output": "scenarios total=4 passed=1 failed=1 undefined=1 pending=1 skipped=0\nsteps total=4 passed=1 failed=1 undefined=1 pending=1 skipped=0\nscenario keyword=Scenario name=P line=4 status=passed\nscenario keyword=Scenario name=F line=7 status=failed\nscenario keyword=Scenario name=U line=9 status=undefined\nscenario keyword=Scenario name=D line=11 status=pending\nresult=failed\n"
    }
  ]
}
```

---

### Feature 2: Shared background steps

**As a developer**, I want a block of setup steps to run before every scenario in a feature, so I can express common context once instead of repeating it.

**Expected Behavior / Usage:**

A feature may declare a single background block of steps. Before each scenario in that feature, the background steps run first, then the scenario's own steps. The tallies count the steps that actually ran for each scenario instance (background plus scenario steps). If a background step passes, it contributes passing steps to every scenario it precedes. If a background step fails for a scenario, that scenario is classified by the failure and its remaining steps (background or scenario) are not executed and are reported as skipped; the run-level result becomes `failed`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_background.json`

```json
{
  "description": "Steps listed under a shared background are executed before every scenario in the same feature. The reported run shows each scenario together with the steps that actually ran (background steps plus the scenario's own steps) and tallies them. If a background step fails for a scenario, that scenario is classified failed and its later steps are skipped; a passing background contributes passed steps to every scenario it precedes.",
  "cases": [
    {
      "input": {
        "command": "run",
        "args": ["-q"],
        "steps": [
          {"pattern": "^this step passes$", "outcome": "pass"},
          {"pattern": "^this step fails$", "outcome": "fail", "message": "boom"}
        ],
        "files": [
          {"path": "features/test.feature", "content": "Feature: Sample\n  Background:\n    Given this step passes\n  Scenario: A\n    Given this step passes\n  Scenario: B\n    Given this step passes\n"}
        ]
      },
      "expected_output": "scenarios total=2 passed=2 failed=0 undefined=0 pending=0 skipped=0\nsteps total=2 passed=2 failed=0 undefined=0 pending=0 skipped=0\nscenario keyword=Scenario name=A line=4 status=passed\nscenario keyword=Scenario name=B line=6 status=passed\nresult=ok\n"
    },
    {
      "input": {
        "command": "run",
        "args": ["-q"],
        "steps": [
          {"pattern": "^this step passes$", "outcome": "pass"},
          {"pattern": "^this step fails$", "outcome": "fail", "message": "boom"}
        ],
        "files": [
          {"path": "features/test.feature", "content": "Feature: Sample\n  Background:\n    Given this step fails\n  Scenario: A\n    Given this step passes\n  Scenario: B\n    Given this step passes\n"}
        ]
      },
      "expected_output": "scenarios total=2 passed=0 failed=0 undefined=0 pending=0 skipped=2\nsteps total=2 passed=0 failed=0 undefined=0 pending=0 skipped=2\nscenario keyword=Scenario name=A line=4 status=skipped\nscenario keyword=Scenario name=B line=6 status=skipped\nresult=failed\n"
    }
  ]
}
```

---

### Feature 3: Data-driven scenario outlines

**As a developer**, I want to express one scenario template that runs once per row of an example table, so I can cover many input combinations without copying scenarios.

**Expected Behavior / Usage:**

*3.1 Expanding an outline over its example rows — Each example row produces one independent scenario instance.*

A scenario outline is a template whose steps contain angle-bracketed placeholders. It is paired with one or more example tables; the first row of each table is the header naming the columns, and each subsequent row supplies values. For every data row, the placeholders in the outline's steps are replaced by that row's column values, and the resulting concrete step is matched and executed. The report emits one `scenario` line per data row (each carrying the outline's keyword and name and the data row's source line), classified independently, and the tallies count every expanded instance across all example tables. The header row never executes.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_outlines.json`

```json
{
  "description": "A scenario outline is a template run once per data row in its examples table (excluding the header row). Placeholders delimited by angle brackets in the outline's steps are substituted with the row's column values before matching against step definitions. The report lists one scenario instance per data row, each classified independently by the substituted step's outcome, and the tallies count every expanded instance.",
  "cases": [
    {
      "input": {
        "command": "run",
        "args": ["-q"],
        "steps": [
          {"pattern": "^this step passes$", "outcome": "pass"},
          {"pattern": "^this step fails$", "outcome": "fail"}
        ],
        "files": [
          {"path": "features/o.feature", "content": "Feature: Outline\n  Scenario Outline: Test\n    Given this step <state>\n    Examples:\n      | state |\n      | passes |\n      | fails |\n"}
        ]
      },
      "expected_output": "scenarios total=2 passed=1 failed=1 undefined=0 pending=0 skipped=0\nsteps total=2 passed=1 failed=1 undefined=0 pending=0 skipped=0\nscenario keyword=Scenario Outline name=Test line=6 status=passed\nscenario keyword=Scenario Outline name=Test line=7 status=failed\nresult=failed\n"
    }
  ]
}
```

*3.2 Selecting a single example row by source position — Targeting one data row's line runs only that instance.*

When the run is given a source position (path:line) that lands on a single example data row, only the scenario instance produced by that row is executed and reported; all other rows of the outline are excluded from both the report and the tallies.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_outline_row_selection.json`

```json
{
  "description": "A single data row of a scenario outline can be selected for execution by pointing at its line position in the source file. Only the instance produced by the targeted row is run and reported; the other rows are excluded entirely from the report and the tallies.",
  "cases": [
    {
      "input": {
        "command": "run",
        "args": ["-q", "features/o.feature:7"],
        "steps": [
          {"pattern": "^this step passes$", "outcome": "pass"},
          {"pattern": "^this step fails$", "outcome": "fail"}
        ],
        "files": [
          {"path": "features/o.feature", "content": "Feature: Outline\n  Scenario Outline: Test\n    Given this step <state>\n    Examples:\n      | state |\n      | passes |\n      | fails |\n"}
        ]
      },
      "expected_output": "scenarios total=1 passed=0 failed=1 undefined=0 pending=0 skipped=0\nsteps total=1 passed=0 failed=1 undefined=0 pending=0 skipped=0\nscenario keyword=Scenario Outline name=Test line=7 status=failed\nresult=failed\n"
    }
  ]
}
```

---

### Feature 4: Select scenarios by tag expression

**As a developer**, I want to run only the scenarios whose tags satisfy a boolean expression, so I can focus on a relevant subset of a large suite.

**Expected Behavior / Usage:**

Scenarios and features may be annotated with tags (tokens beginning with `@`). A tag placed on a feature is inherited by every scenario in that feature. A selection expression combines tag names with the operators `and`, `or`, and `not`. Only scenarios whose effective tag set satisfies the expression are executed and reported; the tallies reflect only the selected scenarios. `and` keeps scenarios that carry every named tag, `or` keeps scenarios that carry any named tag, and `not` excludes scenarios that carry the named tag.

**Test Cases:** `rcb_tests/public_test_cases/feature4_tag_filter.json`

```json
{
  "description": "Scenarios can be selected by boolean logic over their tags. A tag expression supports 'and', 'or', and 'not' over tag names; tags placed on a feature are inherited by all its scenarios. Only the scenarios whose tags satisfy the expression are run and reported. AND keeps scenarios carrying every named tag; OR keeps scenarios carrying any; NOT excludes scenarios carrying the named tag.",
  "cases": [
    {
      "input": {
        "command": "run",
        "args": ["-q", "-t", "@one and @three"],
        "steps": [{"pattern": "^passing$", "outcome": "pass"}],
        "files": [
          {"path": "features/test.feature", "content": "@feature\nFeature: Sample\n  @one @three\n  Scenario: Example\n    Given passing\n  @one\n  Scenario: Another\n    Given passing\n  @three\n  Scenario: Yet\n    Given passing\n  @ignore\n  Scenario: And\n    Given passing\n"}
        ]
      },
      "expected_output": "scenarios total=1 passed=1 failed=0 undefined=0 pending=0 skipped=0\nsteps total=1 passed=1 failed=0 undefined=0 pending=0 skipped=0\nscenario keyword=Scenario name=Example line=4 status=passed\nresult=ok\n"
    },
    {
      "input": {
        "command": "run",
        "args": ["-q", "-t", "@one or @three"],
        "steps": [{"pattern": "^passing$", "outcome": "pass"}],
        "files": [
          {"path": "features/test.feature", "content": "@feature\nFeature: Sample\n  @one @three\n  Scenario: Example\n    Given passing\n  @one\n  Scenario: Another\n    Given passing\n  @three\n  Scenario: Yet\n    Given passing\n  @ignore\n  Scenario: And\n    Given passing\n"}
        ]
      },
      "expected_output": "scenarios total=3 passed=3 failed=0 undefined=0 pending=0 skipped=0\nsteps total=3 passed=3 failed=0 undefined=0 pending=0 skipped=0\nscenario keyword=Scenario name=Example line=4 status=passed\nscenario keyword=Scenario name=Another line=7 status=passed\nscenario keyword=Scenario name=Yet line=10 status=passed\nresult=ok\n"
    },
    {
      "input": {
        "command": "run",
        "args": ["-q", "-t", "not @three"],
        "steps": [{"pattern": "^passing$", "outcome": "pass"}],
        "files": [
          {"path": "features/test.feature", "content": "@feature\nFeature: Sample\n  @one @three\n  Scenario: Example\n    Given passing\n  @one\n  Scenario: Another\n    Given passing\n  @three\n  Scenario: Yet\n    Given passing\n  @ignore\n  Scenario: And\n    Given passing\n"}
        ]
      },
      "expected_output": "scenarios total=2 passed=2 failed=0 undefined=0 pending=0 skipped=0\nsteps total=2 passed=2 failed=0 undefined=0 pending=0 skipped=0\nscenario keyword=Scenario name=Another line=7 status=passed\nscenario keyword=Scenario name=And line=13 status=passed\nresult=ok\n"
    }
  ]
}
```

---

### Feature 5: Select scenarios by name substring

**As a developer**, I want to run only scenarios whose name contains a given substring, so I can target a feature, scenario, or example group without listing files.

**Expected Behavior / Usage:**

A name filter is a plain substring. A scenario is selected when the substring appears in its own name, in the name of the feature that contains it, in the name of its scenario outline, or in the name of its examples group. All matching scenarios across all source files are executed and reported in source order; non-matching scenarios are excluded from the report and tallies.

**Test Cases:** `rcb_tests/public_test_cases/feature5_name_filter.json`

```json
{
  "description": "Scenarios can be selected by a name substring. The match is tested against feature names, scenario names, scenario-outline names, and examples-block names; any scenario whose containing element matches the substring is run. Only matching scenarios appear in the report and tallies.",
  "cases": [
    {
      "input": {
        "command": "run",
        "args": ["-q", "--name", "foo"],
        "steps": [{"pattern": "^missing$", "outcome": "pass"}],
        "files": [
          {"path": "features/first.feature", "content": "Feature: first feature\n  Scenario: foo first\n    Given missing\n  Scenario: bar first\n    Given missing\n"},
          {"path": "features/second.feature", "content": "Feature: second\n  Scenario: foo second\n    Given missing\n  Scenario: bar second\n    Given missing\n"}
        ]
      },
      "expected_output": "scenarios total=2 passed=2 failed=0 undefined=0 pending=0 skipped=0\nsteps total=2 passed=2 failed=0 undefined=0 pending=0 skipped=0\nscenario keyword=Scenario name=foo first line=2 status=passed\nscenario keyword=Scenario name=foo second line=2 status=passed\nresult=ok\n"
    }
  ]
}
```

---

### Feature 6: Select a scenario by source position

**As a developer**, I want to run exactly one scenario by giving its line position, so I can iterate on a single case without running its siblings.

**Expected Behavior / Usage:**

A source position written as `path:line` selects the single scenario whose body covers that line; the line may fall anywhere within the scenario (its header, a step, a comment, a data table, or a doc string). Only that scenario is executed and reported; sibling scenarios in the same file are excluded from the report and tallies.

**Test Cases:** `rcb_tests/public_test_cases/feature6_line_selection.json`

```json
{
  "description": "An individual scenario can be selected by its line position within a feature file, written as path:line. The line may fall anywhere inside the scenario body. Only the scenario covering that line is run and reported; sibling scenarios in the same file are excluded.",
  "cases": [
    {
      "input": {
        "command": "run",
        "args": ["-q", "features/test.feature:7"],
        "steps": [{"pattern": "^this step passes$", "outcome": "pass"}],
        "files": [
          {"path": "features/test.feature", "content": "Feature: \n\n  Scenario: Miss\n    Given this step is undefined\n\n  Scenario: Hit\n    Given this step passes\n"}
        ]
      },
      "expected_output": "scenarios total=1 passed=1 failed=0 undefined=0 pending=0 skipped=0\nsteps total=1 passed=1 failed=0 undefined=0 pending=0 skipped=0\nscenario keyword=Scenario name=Hit line=6 status=passed\nresult=ok\n"
    }
  ]
}
```

---

### Feature 7: Enforce a per-tag occurrence limit

**As a developer**, I want the run to abort if a given tag appears on more scenarios than an allowed maximum, so I can guard against over-tagging (for example, too many work-in-progress markers).

**Expected Behavior / Usage:**

A limit is expressed as `tag:N`. Before any scenario executes, the engine counts how many selected scenarios carry that tag, counting feature-level tags once per inheriting scenario. If the count exceeds `N`, the run is aborted as a configuration error: it does not execute any scenario. The neutral error reports the category, the offending tag, the configured limit, the actual count, and the source location (path:line) of every scenario carrying the tag. The run-level result is `error`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_tag_limit.json`

```json
{
  "description": "When a maximum occurrence count is set for a tag (tag:N), the run is aborted before any scenario executes if that tag appears on more than N scenarios. The neutral error reports the offending tag, the configured limit, the actual count, and the source locations of every scenario carrying the tag. Inherited feature-level tags count toward the limit for each scenario that inherits them.",
  "cases": [
    {
      "input": {
        "command": "run",
        "args": ["-q", "--tags", "@one:1"],
        "steps": [{"pattern": "^passing$", "outcome": "pass"}],
        "files": [
          {"path": "features/test.feature", "content": "@feature\nFeature: Sample\n  @one @three\n  Scenario: Example\n    Given passing\n  @one\n  Scenario: Another\n    Given passing\n  @three\n  Scenario: Yet\n    Given passing\n  @ignore\n  Scenario: And\n    Given passing\n"}
        ]
      },
      "expected_output": "error=tag_limit_exceeded\ntag=@one\nlimit=1\ncount=2\nlocation=features/test.feature:4\nlocation=features/test.feature:7\n[a specific file-not-found error string]\n"
    }
  ]
}
```

---

### Feature 8: Strict mode escalation

**As a developer**, I want an opt-in strict mode that treats undefined and pending steps as failures of the whole run, so I can gate a build on the suite being fully implemented.

**Expected Behavior / Usage:**

Strict mode does not change how an individual scenario is classified — an undefined scenario is still reported as `undefined`, a pending one as `pending`. It changes only the run-level result: with strict enabled, the presence of any undefined or pending scenario makes the overall `result` a failure. Without strict, those same scenarios leave the overall `result` non-failing. A fully defined, passing scenario yields `ok` in both modes.

**Test Cases:** `rcb_tests/public_test_cases/feature8_strict_mode.json`

```json
{
  "description": "Strict mode escalates the run-level result: with strict enabled, the presence of any undefined or pending step makes the overall result a failure, even though the per-scenario classification is unchanged. Without strict, the same undefined/pending scenarios leave the overall result non-failing. Defined passing scenarios succeed in both modes.",
  "cases": [
    {
      "input": {
        "command": "run",
        "args": ["-q", "--strict"],
        "steps": [],
        "files": [
          {"path": "features/test.feature", "content": "Feature: Missing\n  Scenario: Missing\n    Given this step is undefined\n"}
        ]
      },
      "expected_output": "scenarios total=1 passed=0 failed=0 undefined=1 pending=0 skipped=0\nsteps total=1 passed=0 failed=0 undefined=1 pending=0 skipped=0\nscenario keyword=Scenario name=Missing line=2 status=undefined\nresult=failed\n"
    },
    {
      "input": {
        "command": "run",
        "args": ["-q"],
        "steps": [],
        "files": [
          {"path": "features/test.feature", "content": "Feature: Missing\n  Scenario: Missing\n    Given this step is undefined\n"}
        ]
      },
      "expected_output": "scenarios total=1 passed=0 failed=0 undefined=1 pending=0 skipped=0\nsteps total=1 passed=0 failed=0 undefined=1 pending=0 skipped=0\nscenario keyword=Scenario name=Missing line=2 status=undefined\nresult=ok\n"
    }
  ]
}
```

---

### Feature 9: Dry run

**As a developer**, I want to scan scenarios without executing any step, so I can quickly check structure and selection without side effects.

**Expected Behavior / Usage:**

In dry-run mode the engine resolves and enumerates the scenarios and their steps but never executes a step's outcome. Every step is classified `skipped` regardless of whether it would otherwise pass, fail, or be undefined when implemented, every scenario is reported with status `skipped`, the tallies count all steps as skipped, and the run-level result is non-failing.

**Test Cases:** `rcb_tests/public_test_cases/feature9_dry_run.json`

```json
{
  "description": "Dry-run mode scans the scenarios and classifies every step as skipped without executing any step's outcome, regardless of whether the step would otherwise pass, fail, or be undefined when defined. The report still enumerates the scenarios and counts all their steps as skipped, and the overall result is non-failing.",
  "cases": [
    {
      "input": {
        "command": "run",
        "args": ["-q", "--dry-run"],
        "steps": [{"pattern": "^this step fails$", "outcome": "fail"}],
        "files": [
          {"path": "features/test.feature", "content": "Feature: test\n  Scenario:\n    Given this step fails\n"}
        ]
      },
      "expected_output": "scenarios total=1 passed=0 failed=0 undefined=0 pending=0 skipped=1\nsteps total=1 passed=0 failed=0 undefined=0 pending=0 skipped=1\nscenario keyword=Scenario name= line=2 status=skipped\nresult=ok\n"
    }
  ]
}
```

---

### Feature 10: Suggest step-definition snippets

**As a developer**, I want the engine to suggest a reusable, parameterised binding for every undefined step, so I can implement missing glue quickly and consistently.

**Expected Behavior / Usage:**

For each step phrase that has no matching binding, the engine produces a snippet suggestion. The suggested expression is parameterised: literal integers in the phrase become an integer placeholder, and double-quoted substrings become a string placeholder. Each suggestion reports the parameterised expression and the names of the block arguments the implementer would receive (one per placeholder). A step backed by a data table additionally yields a `table` argument even though the phrase has no inline placeholder. Each emitted line carries the parameterised `expression` and, when there are any, its `args`.

**Test Cases:** `rcb_tests/public_test_cases/feature10_snippets.json`

```json
{
  "description": "For every step phrase that has no matching definition, a code-snippet suggestion is produced. The suggestion proposes a parameterised expression where literal numbers become an integer placeholder and quoted substrings become a string placeholder, and it lists the block argument names the implementer would receive. A step backed by a data table additionally yields a table argument. Each emitted snippet line carries the parameterised expression and its argument names.",
  "cases": [
    {
      "input": {
        "command": "snippets",
        "args": [],
        "files": [
          {"path": "features/u.feature", "content": "Feature:\n  Scenario: S\n    Given a Doc String\n    When 1 simple when step\n    And another \"when\" step\n    Then a simple then step\n"}
        ]
      },
      "expected_output": "snippet expression=a Doc String\nsnippet expression={int} simple when step args=int\nsnippet expression=another {string} step args=string\nsnippet expression=a simple then step\n"
    },
    {
      "input": {
        "command": "snippets",
        "args": [],
        "files": [
          {"path": "features/u.feature", "content": "Feature:\n  Scenario: table\n    Given a table\n      | table |\n      | example |\n"}
        ]
      },
      "expected_output": "snippet expression=a table args=table\n"
    }
  ]
}
```

---

### Feature 11: Localized keyword lookup

**As a developer**, I want to look up the natural-language keywords a given language uses, so I can author scenarios in that language.

**Expected Behavior / Usage:**

Given a language code, the engine reports the keywords that language assigns to each structural concept (feature, background, scenario, scenario outline, examples) and to each step kind (given, when, then, and, but), including both the spoken forms and the bare forms usable in glue code. Each line names the concept and lists its keyword variants. An unrecognised language code is a neutral error that names the rejected code.

**Test Cases:** `rcb_tests/public_test_cases/feature11_i18n_keywords.json`

```json
{
  "description": "Given a language code, the tool reports the natural-language keywords that language uses for each structural concept (feature, background, scenario, scenario outline, examples) and for each step kind (given, when, then, and, but), including the bare step forms usable in code. An unknown language code yields a neutral error naming the rejected code.",
  "cases": [
    {
      "input": {"command": "i18n_keywords", "lang": "pt"},
      "expected_output": "feature: \"Funcionalidade\", \"Característica\", \"Caracteristica\"\nbackground: \"Contexto\", \"Cenário de Fundo\", \"Cenario de Fundo\", \"Fundo\"\nscenario: \"Cenário\", \"Cenario\"\nscenario_outline: \"Esquema do Cenário\", \"Esquema do Cenario\", \"Delineação do Cenário\", \"Delineacao do Cenario\"\nexamples: \"Exemplos\", \"Cenários\", \"Cenarios\"\ngiven: \"* \", \"Dado \", \"Dada \", \"Dados \", \"Dadas \"\nwhen: \"* \", \"Quando \"\nthen: \"* \", \"Então \", \"Entao \"\nand: \"* \", \"E \"\nbut: \"* \", \"Mas \"\ngiven (code): \"Dado\", \"Dada\", \"Dados\", \"Dadas\"\nwhen (code): \"Quando\"\nthen (code): \"Então\", \"Entao\"\nand (code): \"E\"\nbut (code): \"Mas\"\n"
    },
    {
      "input": {"command": "i18n_keywords", "lang": "zzz"},
      "expected_output": "error=invalid_language\nlanguage=zzz\n"
    }
  ]
}
```

---

### Feature 12: Missing scenario sources

**As a developer**, I want a clear, typed error when there are no scenario sources to run, so misconfiguration is obvious instead of silently doing nothing.

**Expected Behavior / Usage:**

When the engine is invoked with no scenario sources available at all (no source directory present), it does not run or report any scenario. It surfaces a neutral configuration error indicating the absence of any feature sources, and the run-level result is `error`.

**Test Cases:** `rcb_tests/public_test_cases/feature12_no_features.json`

```json
{
  "description": "Running with no scenario sources available (no features directory present) does not run anything; it reports a neutral configuration error indicating the absence of any feature sources.",
  "cases": [
    {
      "input": {"command": "run", "args": [], "files": []},
      "expected_output": "error=missing_features_directory\n[a specific file-not-found error string]\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the features above — source parsing, scenario/outline compilation, tag/name/position selection and tag-limit enforcement, step matching, execution with result classification, strict and dry-run modes, report formatting, snippet suggestion, and localized keyword lookup — each as a separated concern, with the engine usable as a library independent of any I/O format.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads a single JSON command from stdin (`run`, `snippets`, or `i18n_keywords`, with the fields shown in the cases above), invokes the appropriate core logic, and prints the neutral contract lines to stdout exactly as specified per leaf feature. The adapter is solely responsible for translating native engine errors into the neutral `error=<category>` lines and stripping any host-language runtime traces; the core engine is never coupled to this wire format.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_result_classification.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_result_classification@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the template sequence
- according to the strict mode flag
