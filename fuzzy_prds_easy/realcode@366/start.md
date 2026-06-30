## Product Requirement Document

# Declarative UI Static Analysis Engine - Naming, Binding, Template & Complexity Contracts

## Project Goal

Build a static analysis engine for a decorator-based, declarative UI framework that allows developers to validate component, directive, and pipe declarations together with their inline HTML templates against a fixed set of style and correctness conventions, so teams can catch convention violations automatically instead of reviewing every declaration and template expression by hand.

The engine accepts a piece of source text and the name of a single check to run, analyzes it, and returns position-aware diagnostics (and, for a few checks, an automatically rewritten version of the source) in a deterministic, language-neutral, line-oriented format.

---

## Background & Problem

Without this tool, developers must manually inspect every decorated class and every inline template string to keep a codebase consistent: confirming that public selectors carry the agreed prefix and casing, that bindings are not aliased in confusing ways, that custom event outputs do not shadow native browser events, that repeated-rendering loops declare an identity-tracking expression, that asynchronous template values are not negated unsafely, that localizable text carries the required metadata, and that conditional logic stays out of markup. This manual review is slow, inconsistent across reviewers, and easy to get wrong.

With this tool, a developer (or a CI job) feeds source text plus a single check selector to one entry point and receives a structured report: how many problems were found, and for each problem a human-readable message plus the exact line/column span it covers. Where a problem has a safe mechanical fix, the tool can also emit the corrected source. Because the output is a plain, stable text contract, it can be diffed, stored as a golden file, and compared byte-for-byte.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The domain is non-trivial — it combines source parsing, multiple independent analysis checks, template sub-parsing, and a reporting layer — so the codebase MUST NOT be a single "god file". Provide a clear multi-file tree that separates the core analysis engine, the individual checks, and the execution/reporting adapter. Do not over-engineer, but keep each check as an independently testable unit.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases in "Core Features" are a **black-box testing contract** for the execution adapter, NOT the internal data model. The core analysis logic must remain decoupled from stdin/stdout and JSON parsing. A thin execution adapter is solely responsible for translating a JSON command into a call into the core engine and rendering the engine's findings into the text contract.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Separate command parsing, check selection/routing, core analysis, and output formatting into distinct units.
   - **Open/Closed Principle (OCP):** Adding a new check must not require modifying existing checks or the engine core.
   - **Liskov Substitution Principle (LSP):** All checks must be substitutable behind a common check abstraction.
   - **Interface Segregation Principle (ISP):** Keep the check interface small and cohesive.
   - **Dependency Inversion Principle (DIP):** The reporting/adapter layer depends on an abstract finding type, not on any concrete check.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The core engine's public interface must be elegant and idiomatic to the implementation language, hiding parsing details.
   - **Resilience:** Malformed commands and internal failures must be handled gracefully and reported as a normalized, language-neutral error line — never as a raw host-runtime stack trace or host exception class name.

### Execution contract (shared by every feature)

The execution adapter reads exactly one JSON command from stdin:

```json
{
  "action": "lint",
  "check": "<check-name>",
  "config": { "...": "optional per-check settings" },
  "source": "<source text to analyze>",
  "apply_fix": false
}
```

`config` and `apply_fix` are optional. The adapter analyzes `source` with the named check and writes a report to stdout in this exact shape:

```
check=<check-name>
failure_count=<N>
```

Then, for each finding in report order, a block:

```
failure_index=<i>
message=<human-readable diagnostic message>
start_line=<[uses a 0-based index system for lines and columns]-based line>
start_character=<[uses a 0-based index system for lines and columns]-based column>
end_line=<[uses a 0-based index system for lines and columns]-based line>
end_character=<[uses a 0-based index system for lines and columns]-based column>
```

Line and column numbers are [uses a 0-based index system for lines and columns]-based. When `failure_count=[uses a 0-based index system for lines and columns]` no blocks follow. When `apply_fix` is `true` and at least one finding carries a mechanical fix, a trailing block reproduces the rewritten source between sentinel markers:

```
[mark the fixed source block with a specific sentinel string]
<rewritten source>
[mark the fixed source block with a specific sentinel string]
```

A command that is not valid JSON yields `error=invalid_json`; a command whose `action` is not `lint` yields `error=unsupported_action`; an internal failure yields a normalized `error=execution_error` line. No host-language exception identity ever appears in stdout.

---

## Core Features

### Feature 1: Component Selector Convention

**As a developer**, I want every component's public selector validated for usage kind, required prefix, and naming style, so I can keep component selectors consistent across a codebase.

**Expected Behavior / Usage:**

This check inspects the selector declared in a component's metadata. `config` carries `selector_usage` (whether the selector is expected to be used as an `element`, an `attribute`, or other supported usages), `prefixes` (a single prefix string or a list of acceptable prefixes), and `case_style` (e.g. `kebab-case` or `camelCase`). When the selector violates the configured prefix it reports a prefix diagnostic; when it violates the configured naming style it reports a style diagnostic. Each diagnostic includes the exact span of the offending selector literal. A conforming selector produces `failure_count=[uses a 0-based index system for lines and columns]`. The message text is a stable wire-format string that names the offending class and the expected constraint.

**Test Cases:** `rcb_tests/public_test_cases/feature1_component_selector.json`

```json
{
    "description": "Validate component selector usage, configured prefix, and configured naming style in component declarations.",
    "cases": [
        {
            "input": {
                "action": "lint",
                "check": "component_selector",
                "config": {
                    "selector_usage": "element",
                    "prefixes": "sg",
                    "case_style": "kebab-case"
                },
                "source": "\n@Component({\n  selector: 'foo-bar'\n})\nclass SampleComponent {}\n"
            },
            "expected_output": "check=component_selector\nfailure_count=1\nfailure_index=[uses a 0-based index system for lines and columns]\nmessage=The selector of the component \"SampleComponent\" should have prefix \"sg\" (https://angular.io/styleguide#style-[uses a 0-based index system for lines and columns]2-[uses a 0-based index system for lines and columns]7)\nstart_line=2\nstart_character=12\nend_line=2\nend_character=21\n"
        },
        {
            "input": {
                "action": "lint",
                "check": "component_selector",
                "config": {
                    "selector_usage": "element",
                    "prefixes": "sg",
                    "case_style": "kebab-case"
                },
                "source": "\n@Component({\n  selector: 'sg-bar-foo'\n})\nclass SampleComponent {}\n"
            },
            "expected_output": "check=component_selector\nfailure_count=[uses a 0-based index system for lines and columns]\n"
        }
    ]
}
```

---

### Feature 2: Directive Selector Convention

**As a developer**, I want every directive's public selector validated for usage kind, required prefix, and naming style, so attribute and element directives stay consistent and discoverable.

**Expected Behavior / Usage:**

This check mirrors the component selector check but for directive declarations and with the casing convention typical of directives. `config` carries `selector_usage`, `prefixes`, and `case_style`. A selector that violates the configured naming style yields a style diagnostic; one missing the configured prefix yields a prefix diagnostic. Both diagnostics span the selector literal exactly, and a conforming selector yields `failure_count=[uses a 0-based index system for lines and columns]`. Messages are stable wire-format strings naming the directive class and the expected constraint.

**Test Cases:** `rcb_tests/public_test_cases/feature2_directive_selector.json`

```json
{
    "description": "Validate directive selector usage, configured prefix, and configured naming style in directive declarations.",
    "cases": [
        {
            "input": {
                "action": "lint",
                "check": "directive_selector",
                "config": {
                    "selector_usage": "attribute",
                    "prefixes": "sg",
                    "case_style": "camelCase"
                },
                "source": "\n@Directive({\n  selector: '[sg-foo-bar]'\n})\nclass SampleDirective {}\n"
            },
            "expected_output": "check=directive_selector\nfailure_count=1\nfailure_index=[uses a 0-based index system for lines and columns]\nmessage=The selector of the directive \"SampleDirective\" should be named camelCase (https://angular.io/styleguide#style-[uses a 0-based index system for lines and columns]2-[uses a 0-based index system for lines and columns]6)\nstart_line=2\nstart_character=12\nend_line=2\nend_character=26\n"
        },
        {
            "input": {
                "action": "lint",
                "check": "directive_selector",
                "config": {
                    "selector_usage": "attribute",
                    "prefixes": "sg",
                    "case_style": "camelCase"
                },
                "source": "\n@Directive({\n  selector: '[fooBar]'\n})\nclass SampleDirective {}\n"
            },
            "expected_output": "check=directive_selector\nfailure_count=1\nfailure_index=[uses a 0-based index system for lines and columns]\nmessage=The selector of the directive \"SampleDirective\" should have prefix \"sg\" (https://angular.io/styleguide#style-[uses a 0-based index system for lines and columns]2-[uses a 0-based index system for lines and columns]8)\nstart_line=2\nstart_character=12\nend_line=2\nend_character=22\n"
        }
    ]
}
```

---

### Feature 3: Pipe Name Convention

**As a developer**, I want a transformation pipe's declared name validated against a configured casing style and optional prefixes, so pipe names stay consistent, while names that are not literal strings are left alone.

**Expected Behavior / Usage:**

This check reads the `name` value declared in a pipe's metadata. `config` carries `case_style` (e.g. `camelCase`) and optional `prefixes` (a single prefix or a list). A literal name that violates the casing or required prefix is reported with a message naming the pipe class and the expected constraint, spanning the offending name literal. If the name is supplied as a variable or other non-literal expression, the check does nothing and reports `failure_count=[uses a 0-based index system for lines and columns]`. A conforming literal name also reports `failure_count=[uses a 0-based index system for lines and columns]`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_pipe_name.json`

```json
{
    "description": "Validate literal pipe names against configured case style and optional prefixes while ignoring non-literal names.",
    "cases": [
        {
            "input": {
                "action": "lint",
                "check": "pipe_name",
                "config": {
                    "case_style": "camelCase",
                    "prefixes": "ng"
                },
                "source": "\n@Pipe({\n  name: 'foo-bar'\n})\nclass SamplePipe {}\n"
            },
            "expected_output": "check=pipe_name\nfailure_count=1\nfailure_index=[uses a 0-based index system for lines and columns]\nmessage=The name of the Pipe decorator of class SamplePipe should be named camelCase with prefix ng, however its value is \"foo-bar\"\nstart_line=2\nstart_character=2\nend_line=2\nend_character=17\n"
        },
        {
            "input": {
                "action": "lint",
                "check": "pipe_name",
                "config": {
                    "case_style": "camelCase",
                    "prefixes": [
                        "fo",
                        "mg",
                        "sg"
                    ]
                },
                "source": "\n@Pipe({\n  name: 'fooBar'\n})\nclass SamplePipe {}\n"
            },
            "expected_output": "check=pipe_name\nfailure_count=1\nfailure_index=[uses a 0-based index system for lines and columns]\nmessage=The name of the Pipe decorator of class SamplePipe should be named camelCase with prefix fo,mg,sg, however its value is \"fooBar\"\nstart_line=2\nstart_character=2\nend_line=2\nend_character=16\n"
        }
    ]
}
```

---

### Feature 4: Input Binding Alias Restriction

**As a developer**, I want input bindings flagged when they are renamed to a public alias different from the property, so binding names stay predictable and self-documenting.

**Expected Behavior / Usage:**

This check looks at input-binding declarations on component and directive classes. When an input is given an explicit public alias (any aliased form, including an alias equal to the property name), it reports a diagnostic that names the class and the property and explains the recommended convention, spanning the whole input declaration. A plain, unaliased input reports `failure_count=[uses a 0-based index system for lines and columns]`. (The check has no required `config`.)

**Test Cases:** `rcb_tests/public_test_cases/feature4_input_alias.json`

```json
{
    "description": "Reject aliased input bindings on components and directives except when a directive selector explicitly exposes that alias.",
    "cases": [
        {
            "input": {
                "action": "lint",
                "check": "input_alias",
                "source": "\n@Component({\n  selector: 'foo'\n})\nclass SampleComponent {\n  @Input('bar') label: string;\n}\n"
            },
            "expected_output": "check=input_alias\nfailure_count=1\nfailure_index=[uses a 0-based index system for lines and columns]\nmessage=In the class \"SampleComponent\", the directive input property \"label\" should not be renamed. However, you should use an alias when the directive name is also an input property, and the directive name doesn't describe the property. In this last case, you can disable this rule with `tslint:disable-next-line:no-input-rename`.\nstart_line=5\nstart_character=2\nend_line=5\nend_character=3[uses a 0-based index system for lines and columns]\n"
        },
        {
            "input": {
                "action": "lint",
                "check": "input_alias",
                "source": "\n@Component({\n  selector: 'foo'\n})\nclass SampleComponent {\n  @Input() label: string;\n}\n"
            },
            "expected_output": "check=input_alias\nfailure_count=[uses a 0-based index system for lines and columns]\n"
        }
    ]
}
```

---

### Feature 5: Output Standard-Event-Name Restriction

**As a developer**, I want output bindings flagged when their public name (either the property name or its alias) matches a standard browser event name, so custom events never shadow native ones.

**Expected Behavior / Usage:**

This check inspects output-binding declarations on component and directive classes. If the public event name — the property name when unaliased, or the alias when renamed — collides with a known standard browser event name (e.g. `change`), it reports a diagnostic naming the class and the offending property, spanning the whole output declaration. Output names that do not collide report `failure_count=[uses a 0-based index system for lines and columns]`. (The check has no required `config`.)

**Test Cases:** `rcb_tests/public_test_cases/feature5_output_standard_event.json`

```json
{
    "description": "Reject output bindings whose public event name collides with a standard browser event name.",
    "cases": [
        {
            "input": {
                "action": "lint",
                "check": "output_standard_event",
                "source": "\n@Component()\nclass ButtonComponent {\n  @Output() change = new EventEmitter<any>();\n}\n"
            },
            "expected_output": "check=output_standard_event\nfailure_count=1\nfailure_index=[uses a 0-based index system for lines and columns]\nmessage=In the class \"ButtonComponent\", the output property \"change\" should not be named or renamed after a standard event\nstart_line=3\nstart_character=2\nend_line=3\nend_character=45\n"
        },
        {
            "input": {
                "action": "lint",
                "check": "output_standard_event",
                "source": "\n@Directive()\nclass ButtonDirective {\n  @Output(\"change\") _change = new EventEmitter<any>();\n}\n"
            },
            "expected_output": "check=output_standard_event\nfailure_count=1\nfailure_index=[uses a 0-based index system for lines and columns]\nmessage=In the class \"ButtonDirective\", the output property \"_change\" should not be named or renamed after a standard event\nstart_line=3\nstart_character=2\nend_line=3\nend_character=54\n"
        }
    ]
}
```

---

### Feature 6: Repeated-Rendering Track-By Requirement

**As a developer**, I want repeated-rendering loops in templates to declare an identity-tracking expression, so list re-rendering stays efficient and stable.

**Expected Behavior / Usage:**

This check parses a component's inline template and inspects repeated-rendering directives (the loop microsyntax that iterates a collection into repeated markup). A loop that omits a track-by expression in its microsyntax is reported with a diagnostic spanning the loop binding. A loop that includes a track-by expression reports `failure_count=[uses a 0-based index system for lines and columns]`. (The check has no required `config`.)

**Test Cases:** `rcb_tests/public_test_cases/feature6_repeated_template_rendering.json`

```json
{
    "description": "Require repeated template rendering directives to provide a track-by expression in their microsyntax.",
    "cases": [
        {
            "input": {
                "action": "lint",
                "check": "repeated_template_rendering",
                "source": "\n@Component({\n  template: `\n    <ul>\n      <li *ngFor=\"let person of persons; trackBy: trackByFn\">\n        {{ person.name }}\n      </li>\n    </ul>\n  `\n})\nclass ListComponent {}\n"
            },
            "expected_output": "check=repeated_template_rendering\nfailure_count=[uses a 0-based index system for lines and columns]\n"
        },
        {
            "input": {
                "action": "lint",
                "check": "repeated_template_rendering",
                "source": "\n@Component({\n  template: `\n    <ul>\n      <li *ngFor=\"let person of persons;\">\n        {{ person.name }}\n      </li>\n    </ul>\n  `\n})\nclass ListComponent {}\n"
            },
            "expected_output": "check=repeated_template_rendering\nfailure_count=1\nfailure_index=[uses a 0-based index system for lines and columns]\nmessage=Missing trackBy function in ngFor directive\nstart_line=4\nstart_character=1[uses a 0-based index system for lines and columns]\nend_line=4\nend_character=41\n"
        }
    ]
}
```

---

### Feature 7: Asynchronous Template Value Boolean Handling

**As a developer**, I want template expressions that negate or loosely compare an asynchronously-resolved value flagged, with an automatic rewrite offered, so async truthiness is handled explicitly and safely.

**Expected Behavior / Usage:**

This check parses a component's inline template and examines boolean expressions over an asynchronously-resolved value (a value passed through the async resolution pipe). Negating such a value directly is reported and, when `apply_fix` is `true`, rewritten to an explicit strict comparison against `false`. A loose-equality comparison against `false` is reported and rewritten to strict equality. The diagnostic spans the offending sub-expression; when a rewrite is requested and available, the corrected full source is emitted in a trailing `[mark the fixed source block with a specific sentinel string] ... [mark the fixed source block with a specific sentinel string]` block. The message is a stable wire-format string describing the required form.

**Test Cases:** `rcb_tests/public_test_cases/feature7_async_boolean_expression.json`

```json
{
    "description": "Detect unsafe negation or loose equality around asynchronous template values and provide source rewrites when available.",
    "cases": [
        {
            "input": {
                "action": "lint",
                "check": "async_boolean_expression",
                "apply_fix": true,
                "source": "\n@Component({\n  selector: 'sample-view',\n  template: '{{ !(foo | async) }}'\n})\nclass SampleView {\n  constructor(public foo: Observable<Boolean>) {}\n}\n"
            },
            "expected_output": "check=async_boolean_expression\nfailure_count=1\nfailure_index=[uses a 0-based index system for lines and columns]\nmessage=Async pipes can not be negated, use (observable | async) === false instead\nstart_line=3\nstart_character=16\nend_line=3\nend_character=31\n[mark the fixed source block with a specific sentinel string]\n\n@Component({\n  selector: 'sample-view',\n  template: '{{ (foo | async) === false }}'\n})\nclass SampleView {\n  constructor(public foo: Observable<Boolean>) {}\n}\n\n[mark the fixed source block with a specific sentinel string]\n"
        },
        {
            "input": {
                "action": "lint",
                "check": "async_boolean_expression",
                "apply_fix": true,
                "source": "\n@Component({\n  selector: 'sample-view',\n  template: '{{ (foo | async) == false }}'\n})\nclass SampleView {\n  constructor(public foo: Observable<Boolean>) {}\n}\n"
            },
            "expected_output": "check=async_boolean_expression\nfailure_count=1\nfailure_index=[uses a 0-based index system for lines and columns]\nmessage=Async pipes must use strict equality `===` when comparing with `false`\nstart_line=3\nstart_character=17\nend_line=3\nend_character=39\n[mark the fixed source block with a specific sentinel string]\n\n@Component({\n  selector: 'sample-view',\n  template: '{{ (foo | async) === false }}'\n})\nclass SampleView {\n  constructor(public foo: Observable<Boolean>) {}\n}\n\n[mark the fixed source block with a specific sentinel string]\n"
        }
    ]
}
```

---

### Feature 8: Template Localization Annotation Enforcement

**As a developer**, I want localization annotations in templates validated, so localizable text carries the metadata required by the translation workflow.

**Expected Behavior / Usage:**

This check parses a component's inline template and validates localization annotations. With `config.requirement` set to `check-id`, every localization annotation must carry a custom message identifier; an annotation whose identifier is empty is reported. The diagnostic spans the offending annotation, and a single offending annotation may produce more than one finding (each finding is emitted as its own block, all sharing the same span). A complete annotation reports `failure_count=[uses a 0-based index system for lines and columns]`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_localized_template_text.json`

```json
{
    "description": "Validate localization annotations by requiring custom identifiers when configured and localization markers for literal template text when configured.",
    "cases": [
        {
            "input": {
                "action": "lint",
                "check": "localized_template_text",
                "config": {
                    "requirement": "check-id"
                },
                "source": "\n@Component({\n  template: `\n    <div i18n=\"test@@foo\">Text</div>\n  `\n})\nclass LocalizedView {}\n"
            },
            "expected_output": "check=localized_template_text\nfailure_count=[uses a 0-based index system for lines and columns]\n"
        },
        {
            "input": {
                "action": "lint",
                "check": "localized_template_text",
                "config": {
                    "requirement": "check-id"
                },
                "source": "\n@Component({\n  template: `\n    <div i18n=\"foo@@\">Text</div>\n  `\n})\nclass LocalizedView {}\n"
            },
            "expected_output": "check=localized_template_text\nfailure_count=2\nfailure_index=[uses a 0-based index system for lines and columns]\nmessage=Missing custom message identifier. For more information visit https://angular.io/guide/i18n\nstart_line=3\nstart_character=9\nend_line=3\nend_character=21\nfailure_index=1\nmessage=Missing custom message identifier. For more information visit https://angular.io/guide/i18n\nstart_line=3\nstart_character=9\nend_line=3\nend_character=21\n"
        }
    ]
}
```

---

### Feature 9: Template Conditional-Expression Complexity Limit

**As a developer**, I want conditional expressions inside templates measured for complexity against a configurable budget, so heavy logic is moved out of markup and into code.

**Expected Behavior / Usage:**

This check parses a component's inline template and computes a complexity cost for each conditional-rendering expression (counting the logical/comparison operations involved). `config.max_cost` sets the allowed budget (a default budget applies when it is omitted). A condition whose cost exceeds the budget is reported with a message stating the measured cost and the configured limit, spanning the whole conditional binding. A condition within budget reports `failure_count=[uses a 0-based index system for lines and columns]`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_template_condition_complexity.json`

```json
{
    "description": "Measure template conditional-expression complexity and report conditions whose cost exceeds the configured maximum.",
    "cases": [
        {
            "input": {
                "action": "lint",
                "check": "template_condition_complexity",
                "source": "\n@Component({\n  template: `\n    <div *ngIf=\"a === '1' || (b === '2' && c.d !== e)\">\n      Enter your card details\n    </div>\n  `\n})\nclass CheckoutView {}\n"
            },
            "expected_output": "check=template_condition_complexity\nfailure_count=[uses a 0-based index system for lines and columns]\n"
        },
        {
            "input": {
                "action": "lint",
                "check": "template_condition_complexity",
                "config": {
                    "max_cost": 4
                },
                "source": "\n@Component({\n  template: `\n    <div *ngIf=\"a === '3' || (b === '3' && c.d !== '1' && e.f !== '6' && q !== g)\">\n      Enter your card details\n    </div>\n  `\n})\nclass CheckoutView {}\n"
            },
            "expected_output": "check=template_condition_complexity\nfailure_count=1\nfailure_index=[uses a 0-based index system for lines and columns]\nmessage=The condition complexity (cost '5') exceeded the defined limit (cost '4'). The conditional expression should be moved into the component.\nstart_line=3\nstart_character=9\nend_line=3\nend_character=82\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the analysis engine and the nine checks above, with each check as an independently testable unit behind a common abstraction, decoupled from I/O.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON command from stdin, routes it to the selected check in the core engine, and prints the result to stdout in the exact line-oriented contract described in "Execution contract" and demonstrated per feature. This adapter is the only component aware of JSON and stdout, and it normalizes malformed commands and internal failures into language-neutral `error=...` lines.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_component_selector.json` under `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_component_selector@[uses a 0-based index system for lines and columns][uses a 0-based index system for lines and columns][uses a 0-based index system for lines and columns].txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout of the program under test, so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- check the error format definition in validation module C003
- refer to the component_selector ignore behavior
