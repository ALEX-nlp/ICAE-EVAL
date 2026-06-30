## Product Requirement Document

# Source Quality Analysis Toolkit - Black-Box Behavior Contract

## Project Goal

Build a source quality analysis library and command adapter that allows developers to normalize configuration, choose report formats, and analyze source text for maintainability issues without hand-writing repetitive AST checks, path filtering, and output routing.

---

## Background & Problem

Without this library/tool, developers are forced to combine custom string/path utilities, configuration parsing, suppression handling, report dispatch, and source-code inspections manually. This leads to repetitive code, inconsistent diagnostics, fragile filtering logic, and maintenance issues when checks need exact locations and automated fixes.

With this library/tool, a caller sends structured JSON commands to an execution adapter, the adapter invokes the core quality-analysis behavior, and stdout contains deterministic field-oriented results suitable for black-box verification.

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

### Feature 1: String Identifier Conversion

**As a developer**, I want to convert identifier-like strings into readable or normalized display forms, so I can present names consistently in reports and configuration output.

**Expected Behavior / Usage:**

The input is a JSON command containing an ordered list of strings. For each string, the adapter prints the original value, its camel-case-to-text conversion, its first-character capitalization, and its snake-case-to-kebab-case conversion. Each record is separated by a delimiter line so callers can compare multiple conversions in one run.

**Test Cases:** `rcb_tests/public_test_cases/feature1_string_conversions.json`

```json
{
    "description": "Convert identifier-like text into human-readable, capitalized, and hyphen-separated forms.",
    "cases": [
        {
            "input": {
                "command": "convert_strings",
                "values": [
                    "camelCaseString",
                    "CamelCaseString",
                    "snake_case",
                    "snake_case_string",
                    "kebab-case"
                ]
            },
            "expected_output": "input=camelCaseString\ncamel_text=camel case string\ncapitalized=CamelCaseString\nkebab=camelCaseString\n---\ninput=CamelCaseString\ncamel_text=camel case string\ncapitalized=CamelCaseString\nkebab=CamelCaseString\n---\ninput=snake_case\ncamel_text=snake_case\ncapitalized=Snake_case\nkebab=snake-case\n---\ninput=snake_case_string\ncamel_text=snake_case_string\ncapitalized=Snake_case_string\nkebab=snake-case-string\n---\ninput=kebab-case\ncamel_text=kebab-case\ncapitalized=Kebab-case\nkebab=kebab-case\n---\n"
        }
    ]
}
```

---

### Feature 2: Path and Exclude Utilities

**As a developer**, I want to normalize path-related inputs and exclusion settings, so I can apply file filtering consistently across platforms.

**Expected Behavior / Usage:**

*2.1 URI to Path Conversion — Convert nullable and non-file URI values to filesystem paths.*

The input is a JSON command containing nullable URI strings. A null URI prints `path=null`. A file URI prints its filesystem path. A non-file URI is interpreted by its path component and resolved against the current working directory. Backslashes are normalized in stdout so the contract remains stable.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_path_uri_conversion.json`

```json
{
    "description": "Convert absent, file, and package-style URIs into nullable normalized filesystem paths.",
    "cases": [
        {
            "input": {
                "command": "normalize_paths",
                "uris": [
                    null,
                    "file://[a specific filesystem path derived from removing the file:// scheme]",
                    "package:quality_tool/src/utils/path_utils.dart"
                ]
            },
            "expected_output": "path=null\npath=[a specific filesystem path derived from removing the file:// scheme]\npath=/testbed/quality_tool/src/utils/path_utils.dart\n"
        }
    ]
}
```

*2.2 Exclude Pattern Preparation and Matching — Build absolute exclude patterns and test whether a path is excluded.*

The input either provides a root directory with relative patterns or provides already-built patterns plus a path to test. Pattern preparation prints one absolute pattern per line in input order. Matching prints whether the supplied path is excluded after path-separator normalization.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_exclude_patterns.json`

```json
{
    "description": "Prepare relative exclude patterns under a project root and test whether a normalized path matches the configured excludes.",
    "cases": [
        {
            "input": {
                "command": "build_excludes",
                "root": "/home/user/project",
                "patterns": [
                    ".dart_tool/**",
                    "packages/**",
                    "src/exclude_me.dart"
                ]
            },
            "expected_output": "pattern=/home/user/project/.dart_tool/**\npattern=/home/user/project/packages/**\npattern=/home/user/project/src/exclude_me.dart\n"
        },
        {
            "input": {
                "command": "check_excluded",
                "patterns": [
                    "/home/user/project/.dart_tool/**",
                    "/home/user/project/packages/**",
                    "/home/user/project/src/exclude_me.dart"
                ],
                "path": "/home/user/project/src/exclude_me.dart"
            },
            "expected_output": "excluded=true\n"
        }
    ]
}
```

---

### Feature 3: YAML Configuration Conversion

**As a developer**, I want to convert YAML configuration into native JSON-compatible data, so I can consume nested configuration without losing primitive values.

**Expected Behavior / Usage:**

The input is a JSON command containing YAML text. The output is a single JSON object line with nested maps, arrays, strings, and numbers preserved. Object keys are rendered in stable sorted order to make stdout directly comparable.

**Test Cases:** `rcb_tests/public_test_cases/feature3_yaml_config_conversion.json`

```json
{
    "description": "Convert nested YAML configuration into a JSON object while preserving strings, numbers, lists, and maps.",
    "cases": [
        {
            "input": {
                "command": "parse_yaml",
                "content": "\ncode_checker:\n  metrics:\n    cyclomatic-complexity: 20\n    number-of-methods: 8\n  metrics-exclude:\n    - test/**\n  rules:\n    - no-boolean-literal-compare\n"
            },
            "expected_output": "{\"code_checker\":{\"metrics\":{\"cyclomatic-complexity\":20,\"number-of-methods\":8},\"metrics-exclude\":[\"test/**\"],\"rules\":[\"no-boolean-literal-compare\"]}}\n"
        }
    ]
}
```

---

### Feature 4: Analysis Metadata Interpretation

**As a developer**, I want to interpret metadata that controls analysis reporting, so I can apply severities and suppressions predictably.

**Expected Behavior / Usage:**

*4.1 Severity Text Mapping — Convert human-entered severity labels to canonical output labels.*

The input is a JSON command containing severity text values, including mixed case strings, blank strings, and null. Each non-null value is matched case-insensitively; unknown or blank text maps to `none`, while null maps to `null`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_severity_mapping.json`

```json
{
    "description": "Map case-insensitive severity text to canonical severity labels, using none for blank or unknown text and null for an absent value.",
    "cases": [
        {
            "input": {
                "command": "severity_from_text",
                "values": [
                    "nOne",
                    "StyLe",
                    "wArnInG",
                    "erROr",
                    "",
                    null
                ]
            },
            "expected_output": "severity=none\nseverity=style\nseverity=warning\nseverity=error\nseverity=none\nseverity=null\n"
        }
    ]
}
```

*4.2 Suppression Comment Detection — Determine whether named checks are suppressed globally or at specific lines.*

The input is source text plus rule identifiers to query. File-wide suppression comments affect the entire file. Line-local comments affect the line on which the ignored code appears. Matching is case-insensitive for identifiers appearing in comments, and stdout prints one boolean answer per query.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_suppression_comments.json`

```json
{
    "description": "Read file-wide and line-local suppression comments and answer whether named checks are suppressed globally or at a specific line.",
    "cases": [
        {
            "input": {
                "command": "check_suppressions",
                "content": "// ignore_for_file:rule_id1\n\nvoid main() {\n  // ignore: rule_id4\n  const a = 5; // ignore: RULE_ID5\n\n  // ignore:rule_id6 ,rule_id7\n  const b = a + 5; // ignore: RULE_ID8, rule_id9, unused_local_variable\n}\n\n// ignore_for_file: rule_id2 , RULE_ID3\n",
                "global_rules": [
                    "rule_id1",
                    "rule_id2",
                    "rule_id3",
                    "rule_id4"
                ],
                "line_rules": [
                    {
                        "rule": "rule_id1",
                        "line": 5
                    },
                    {
                        "rule": "rule_id2",
                        "line": 8
                    },
                    {
                        "rule": "rule_id3",
                        "line": 2
                    },
                    {
                        "rule": "rule_id4",
                        "line": 5
                    },
                    {
                        "rule": "rule_id5",
                        "line": 5
                    },
                    {
                        "rule": "rule_id6",
                        "line": 8
                    },
                    {
                        "rule": "rule_id7",
                        "line": 8
                    },
                    {
                        "rule": "rule_id8",
                        "line": 8
                    },
                    {
                        "rule": "rule_id9",
                        "line": 8
                    }
                ]
            },
            "expected_output": "global:rule_id1=true\nglobal:rule_id2=true\nglobal:rule_id3=true\nglobal:rule_id4=false\nline:5:rule_id1=true\nline:8:rule_id2=true\nline:2:rule_id3=true\nline:5:rule_id4=true\nline:5:rule_id5=true\nline:8:rule_id6=true\nline:8:rule_id7=true\nline:8:rule_id8=true\nline:8:rule_id9=true\n"
        }
    ]
}
```

---

### Feature 5: Report Format Selection

**As a developer**, I want to select the renderer associated with a requested report format, so I can route analysis results to the expected output format.

**Expected Behavior / Usage:**

The input is a JSON command containing report format names. For each name, the output prints the original name and a neutral reporter category. Unknown blank names produce `none`; aliases that share the same underlying output format produce the same category.

**Test Cases:** `rcb_tests/public_test_cases/feature5_reporter_selection.json`

```json
{
    "description": "Select the report renderer associated with each requested report format name, returning none for an unrecognized blank name.",
    "cases": [
        {
            "input": {
                "command": "select_lint_reporter",
                "names": [
                    "",
                    "console",
                    "console-verbose",
                    "codeclimate",
                    "html",
                    "json",
                    "github",
                    "gitlab"
                ]
            },
            "expected_output": "name=\nreporter=none\n---\nname=console\nreporter=console\n---\nname=console-verbose\nreporter=console\n---\nname=codeclimate\nreporter=code-quality-json\n---\nname=html\nreporter=html\n---\nname=json\nreporter=json\n---\nname=github\nreporter=workflow-commands\n---\nname=gitlab\nreporter=code-quality-json\n---\n"
        },
        {
            "input": {
                "command": "select_unused_code_reporter",
                "names": [
                    "",
                    "console",
                    "json"
                ]
            },
            "expected_output": "name=\nreporter=none\n---\nname=console\nreporter=console\n---\nname=json\nreporter=json\n---\n"
        }
    ]
}
```

---

### Feature 6: Source Analysis Rules

**As a developer**, I want to analyze source text for maintainability and correctness findings, so I can surface actionable diagnostics with locations and suggested replacements where available.

**Expected Behavior / Usage:**

*6.1 Empty Block Detection — Report executable blocks that contain no statements or comments.*

The input is source text. The output starts with the check identifier, severity, and issue count, then prints each issue location, exact source span text, and diagnostic message. Empty function bodies, empty anonymous function bodies, and empty conditional or exception blocks are reported; blocks containing comments are not reported.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_empty_blocks_rule.json`

```json
{
    "description": "Analyze source text and report empty executable blocks while ignoring blocks that contain comments or statements.",
    "cases": [
        {
            "input": {
                "command": "analyze_rule",
                "rule": "empty-blocks",
                "code": "int simpleFunction() {\n  try {} catch (_) {} // LINT\n\n  var a = 4;\n\n  // LINT\n  if (a > 70) {\n  } else if (a > 65) {\n    // TODO(developerName): message.\n\n  } else if (a > 60) {\n    return a + 2;\n  }\n\n  // LINT\n  [1, 2, 3, 4].forEach((val) {});\n\n  [1, 2, 3, 4].forEach((val) {\n    // TODO(developerName): need to implement.\n  });\n\n  return a;\n}\n\n// LINT\nvoid emptyFunction() {}\n\nvoid emptyFunction2() {\n  // TODO(developerName): need to implement.\n}\n"
            },
            "expected_output": "rule=no-empty-block\nseverity=style\nissue_count=4\nissue[0].line=2\nissue[0].column=7\nissue[0].text={}\nissue[0].message=Block is empty. Empty blocks are often indicators of missing code.\nissue[1].line=7\nissue[1].column=15\nissue[1].text={\\n  }\nissue[1].message=Block is empty. Empty blocks are often indicators of missing code.\nissue[2].line=16\nissue[2].column=30\nissue[2].text={}\nissue[2].message=Block is empty. Empty blocks are often indicators of missing code.\nissue[3].line=26\nissue[3].column=22\nissue[3].text={}\nissue[3].message=Block is empty. Empty blocks are often indicators of missing code.\n"
        }
    ]
}
```

*6.2 Magic Number Detection — Report unapproved numeric literals used directly in expressions.*

The input is source text and optional configuration listing allowed numeric values. The output reports numeric literals that are directly embedded in executable expressions. Named constants, common sentinel values, date/duration-style constructors, constant collection literals, and configured allowed numbers are ignored; object-construction arguments in nested widget-like structures remain reportable when not allowed.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_magic_numbers_rule.json`

```json
{
    "description": "Analyze source text and report unapproved numeric literals used directly in expressions, while ignoring constants and configured allowed values.",
    "cases": [
        {
            "input": {
                "command": "analyze_rule",
                "rule": "magic-numbers",
                "code": "int bad_f1(int x) => x + 42; // LINT\nbool bad_f2(int x) => x != 12; // LINT\nvoid bad_f4(int x) => a * 3.14; // LINT\nvoid bad_f5() => bad_f4(12); // LINT\n"
            },
            "expected_output": "rule=no-magic-number\nseverity=warning\nissue_count=4\nissue[0].line=1\nissue[0].column=26\nissue[0].text=42\nissue[0].message=Avoid using magic numbers. Extract them to named constants or variables.\nissue[1].line=2\nissue[1].column=28\nissue[1].text=12\nissue[1].message=Avoid using magic numbers. Extract them to named constants or variables.\nissue[2].line=3\nissue[2].column=27\nissue[2].text=3.14\nissue[2].message=Avoid using magic numbers. Extract them to named constants or variables.\nissue[3].line=4\nissue[3].column=25\nissue[3].text=12\nissue[3].message=Avoid using magic numbers. Extract them to named constants or variables.\n"
        },
        {
            "input": {
                "command": "analyze_rule",
                "rule": "magic-numbers",
                "code": "const pi = 3.14;\nconst pi2 = pi * 2;\nconst str = 'Hello';\n\nvoid good_f4(int x) => a * pi;\nvoid good_f5() => good_f4(pi2);\n"
            },
            "expected_output": "rule=no-magic-number\nseverity=warning\nissue_count=0\n"
        },
        {
            "input": {
                "command": "analyze_rule",
                "rule": "magic-numbers",
                "code": "int good_f1(int x) => x + 1;\nbool good_f2(int x) => x != 0;\nbool good_f3(String x) => x.indexOf(str) != -1;\nfinal someDay = DateTime(2006, 12, 1);\nfinal anotherDay = DateTime.utc(2006, 12, 1);\nfinal f = Intl.message(example: const <String, int>{'Assigned': 3});\nfinal f = foo(const [32, 12]);\nfinal f = Future.delayed(const Duration(seconds: 5));\nfinal f = foo(const Bar(5));\nfinal number = 500;\nvar number = 500;\nvar numbers = [100, 200, 300];\n"
            },
            "expected_output": "rule=no-magic-number\nseverity=warning\nissue_count=0\n"
        },
        {
            "input": {
                "command": "analyze_rule",
                "rule": "magic-numbers",
                "code": "int bad_f1(int x) => x + 42; // LINT\nbool bad_f2(int x) => x != 12; // LINT\nvoid bad_f4(int x) => a * 3.14; // LINT\nvoid bad_f5() => bad_f4(12); // LINT\n",
                "config": {
                    "allowed": [
                        42,
                        12,
                        3.14
                    ]
                }
            },
            "expected_output": "rule=no-magic-number\nseverity=warning\nissue_count=0\n"
        },
        {
            "input": {
                "command": "analyze_rule",
                "rule": "magic-numbers",
                "code": "class ContainerWidget {\n  int height;\n  List<ContainerWidget>? children;\n  ContainerWidget({required this.height, this.children});\n\n  ContainerWidget build() {\n    return ContainerWidget(\n      height: 83, // LINT\n      children: [\n        ContainerWidget(\n          height: 83, // LINT\n        ),\n      ],\n    );\n  }\n}\n"
            },
            "expected_output": "rule=no-magic-number\nseverity=warning\nissue_count=2\nissue[0].line=8\nissue[0].column=15\nissue[0].text=83\nissue[0].message=Avoid using magic numbers. Extract them to named constants or variables.\nissue[1].line=11\nissue[1].column=19\nissue[1].text=83\nissue[1].message=Avoid using magic numbers. Extract them to named constants or variables.\n"
        }
    ]
}
```

*6.3 Duplicate Argument Detection — Report repeated non-literal arguments in a single call.*

The input is source text and optional configuration listing named parameters to ignore. The output reports repeated non-literal positional arguments and repeated values passed through different named parameters. Repeated string or numeric literals are not reported. When a named parameter is configured to be ignored, repeated values assigned to that parameter do not produce an issue.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_duplicate_arguments_rule.json`

```json
{
    "description": "Analyze calls and report repeated non-literal arguments passed to separate positional or named parameters, with configurable named-parameter exceptions.",
    "cases": [
        {
            "input": {
                "command": "analyze_rule",
                "rule": "duplicate-arguments",
                "code": "class User {\n  final String firstName;\n  final String lastName;\n\n  const User(this.firstName, this.lastName);\n\n  String getName() => firstName;\n\n  String getFirstName() => firstName;\n\n  String getNewName(String name) => firstName + name;\n}\n\nUser createUser(String firstName, String lastName) {\n  return User(\n    firstName,\n    firstName, // LINT\n  );\n}\n\nvoid getUserData(User user) {\n  String getFullName(String firstName, String lastName) {\n    return firstName + ' ' + lastName;\n  }\n\n  String getUserImage({String firstName, String lastName}) {\n    return '/test_url/' + firstName ?? '' + lastName ?? '';\n  }\n\n  final fullName = getFullName(\n    user.firstName,\n    user.firstName, // LINT\n  );\n\n  final fullName = getFullName(\n    user.getName,\n    user.getName, // LINT\n  );\n\n  final fullName = getFullName(\n    user.getFirstName(),\n    user.getFirstName(), // LINT\n  );\n\n  final fullName = getFullName(\n    user.getNewName('name'),\n    user.getNewName('name'), // LINT\n  );\n\n  final name = 'name';\n\n  final fullName = getFullName(\n    user.getNewName(name),\n    user.getNewName(name), // LINT\n  );\n\n  final image = getUserImage(\n    firstName: user.firstName,\n    lastName: user.firstName, // LINT\n  );\n}\n"
            },
            "expected_output": "rule=no-equal-arguments\nseverity=warning\nissue_count=7\nissue[0].line=17\nissue[0].column=5\nissue[0].text=firstName\nissue[0].message=The argument has already been passed.\nissue[1].line=32\nissue[1].column=5\nissue[1].text=user.firstName\nissue[1].message=The argument has already been passed.\nissue[2].line=37\nissue[2].column=5\nissue[2].text=user.getName\nissue[2].message=The argument has already been passed.\nissue[3].line=42\nissue[3].column=5\nissue[3].text=user.getFirstName()\nissue[3].message=The argument has already been passed.\nissue[4].line=47\nissue[4].column=5\nissue[4].text=user.getNewName('name')\nissue[4].message=The argument has already been passed.\nissue[5].line=54\nissue[5].column=5\nissue[5].text=user.getNewName(name)\nissue[5].message=The argument has already been passed.\nissue[6].line=59\nissue[6].column=5\nissue[6].text=lastName: user.firstName\nissue[6].message=The argument has already been passed.\n"
        },
        {
            "input": {
                "command": "analyze_rule",
                "rule": "duplicate-arguments",
                "code": "class User {\n  final String firstName;\n  final String lastName;\n\n  const User(this.firstName, this.lastName);\n\n  String getName() => firstName;\n\n  String getFirstName() => firstName;\n\n  String getLastName() => lastName;\n\n  String getNewName(String name) => firstName + name;\n}\n\nUser createUser(String firstName, String lastName) {\n  return User(\n    firstName,\n    lastName,\n  );\n}\n\nvoid getUserData(User user) {\n  String getFullName(String firstName, String lastName) {\n    return firstName + ' ' + lastName;\n  }\n\n  String getUserImage({String firstName, String lastName}) {\n    return '/test_url/' + firstName! ?? '' + lastName! ?? '';\n  }\n\n  final fullName = getFullName(\n    user.firstName,\n    user.lastName,\n  );\n\n  final fullName = getFullName(\n    user.getName,\n    user.lastName,\n  );\n\n  final fullName = getFullName(\n    'firstName',\n    lastName,\n  );\n\n  final fullName = getFullName(\n    'firstName',\n    'lastName',\n  );\n\n  final fullName = getFullName(\n    'firstName',\n    'firstName',\n  );\n\n  final fullName = getFullName(\n    user.getFirstName(),\n    user.getLastName(),\n  );\n\n  final fullName = getFullName(\n    user.getNewName('name'),\n    user.getNewName('new name'),\n  );\n\n  final name = 'name';\n  final newName = 'new name';\n\n  final fullName = getFullName(\n    user.getNewName(name),\n    user.getNewName(newName),\n  );\n\n  final image = getUserImage(\n    firstName: user.firstName,\n    lastName: user.lastName,\n  );\n\n  final image = getUserImage(\n    firstName: 'name',\n    lastName: 'name',\n  );\n}\n\nint getWidthAndHeight() {\n  int calculate(int width, int height) => width + height;\n\n  return calculate(\n    -1,\n    -1,\n  );\n}\n"
            },
            "expected_output": "rule=no-equal-arguments\nseverity=warning\nissue_count=0\n"
        },
        {
            "input": {
                "command": "analyze_rule",
                "rule": "duplicate-arguments",
                "code": "String getUserImage({String firstName, String lastName}) {\n  return '/test_url/' + firstName ?? '' + lastName ?? '';\n}\n\nconst firstName = 'name';\n\nfinal image = getUserImage(\n  firstName: firstName,\n  lastName: firstName, // LINT\n);\n"
            },
            "expected_output": "rule=no-equal-arguments\nseverity=warning\nissue_count=1\nissue[0].line=9\nissue[0].column=3\nissue[0].text=lastName: firstName\nissue[0].message=The argument has already been passed.\n"
        },
        {
            "input": {
                "command": "analyze_rule",
                "rule": "duplicate-arguments",
                "code": "String getUserImage({String firstName, String lastName}) {\n  return '/test_url/' + firstName ?? '' + lastName ?? '';\n}\n\nconst firstName = 'name';\n\nfinal image = getUserImage(\n  firstName: firstName,\n  lastName: firstName, // LINT\n);\n",
                "config": {
                    "ignored-parameters": [
                        "lastName"
                    ]
                }
            },
            "expected_output": "rule=no-equal-arguments\nseverity=warning\nissue_count=0\n"
        }
    ]
}
```

*6.4 Forced Non-Null Assertion Detection — Report source expressions that force a nullable value to be non-null.*

The input is source text. The output reports each forced non-null assertion expression with its exact source span. Chained assertions can produce both the outer and inner relevant spans. Null-aware access and explicit null checks are not reported.

**Test Cases:** `rcb_tests/public_test_cases/feature6_4_non_null_assertions_rule.json`

```json
{
    "description": "Analyze source text and report every forced non-null assertion expression, including chained object access and map lookup assertions.",
    "cases": [
        {
            "input": {
                "command": "analyze_rule",
                "rule": "non-null-assertions",
                "code": "class Test {\n  String? field;\n\n  Test? object;\n\n  void method() {\n    field!.contains('other'); // LINT\n\n    field?.replaceAll('from', 'replace');\n\n    if (filed != null) {\n      field.split(' ');\n    }\n\n    object!.field!.contains('other'); // LINT\n\n    object?.field?.contains('other');\n\n    final field = object?.field;\n    if (field != null) {\n      field.contains('other');\n    }\n\n    final map = {'key': 'value'};\n    map['key']!.contains('other');\n\n    object!.method(); // LINT\n\n    object?.method();\n  }\n}\n"
            },
            "expected_output": "rule=avoid-non-null-assertion\nseverity=warning\nissue_count=4\nissue[0].line=7\nissue[0].column=5\nissue[0].text=field!\nissue[0].message=Avoid using non null assertion.\nissue[1].line=15\nissue[1].column=5\nissue[1].text=object!\nissue[1].message=Avoid using non null assertion.\nissue[2].line=15\nissue[2].column=5\nissue[2].text=object!.field!\nissue[2].message=Avoid using non null assertion.\nissue[3].line=27\nissue[3].column=5\nissue[3].text=object!\nissue[3].message=Avoid using non null assertion.\n"
        }
    ]
}
```

*6.5 Boolean Literal Comparison Detection — Report unnecessary comparisons between booleans and boolean literals.*

The input is source text. The output reports comparisons where a non-nullable boolean expression is compared directly to `true` or `false`. Each issue includes a replacement and replacement comment showing whether the expression should be used directly or negated. Nullable or dynamically typed comparisons are not reported.

**Test Cases:** `rcb_tests/public_test_cases/feature6_5_boolean_literal_comparisons_rule.json`

```json
{
    "description": "Analyze source text and report comparisons where a non-nullable boolean expression is compared directly to true or false, including replacement suggestions.",
    "cases": [
        {
            "input": {
                "command": "analyze_rule",
                "rule": "boolean-literal-comparisons",
                "code": "void main() {\n  const exampleString = 'text';\n\n  var a = true;\n\n  var b = a == true; // LINT\n\n  var c = b != true; // LINT\n\n  var d = true == c; // LINT\n\n  var e = false != c; // LINT\n\n  if (e == true) {} // LINT\n\n  if (e != false) {} // LINT\n\n  var f = exampleString?.isEmpty == true;\n\n  var g = true == exampleString?.isEmpty;\n\n  var h = exampleString.isEmpty == true; // LINT\n\n  var i = true == exampleString.isEmpty; // LINT\n\n  [true, false]\n      .where((value) => value == false) // LINT\n      .where((value) => value != false); // LINT\n\n  var y = a != e;\n  var z = a == e;\n\n  if (b == d) {}\n\n  if (b != d) {}\n\n  // LINT\n  [true, false].where((value) => value == true).where((value) => value == c);\n\n  dynamic dyn = 'a';\n  var dynamicWithBoolean = dyn == true;\n  var booleanWithDynamic = false == dyn;\n}\n"
            },
            "expected_output": "rule=no-boolean-literal-compare\nseverity=style\nissue_count=11\nissue[0].line=6\nissue[0].column=11\nissue[0].text=a == true\nissue[0].message=Comparing boolean values to boolean literals is unnecessary, as those expressions will result in booleans too. Just use the boolean values directly or negate them.\nissue[0].replacement=a\nissue[0].replacement_comment=This expression is unnecessarily compared to a boolean. Just use it directly.\nissue[1].line=8\nissue[1].column=11\nissue[1].text=b != true\nissue[1].message=Comparing boolean values to boolean literals is unnecessary, as those expressions will result in booleans too. Just use the boolean values directly or negate them.\nissue[1].replacement=!b\nissue[1].replacement_comment=This expression is unnecessarily compared to a boolean. Just negate it.\nissue[2].line=10\nissue[2].column=11\nissue[2].text=true == c\nissue[2].message=Comparing boolean values to boolean literals is unnecessary, as those expressions will result in booleans too. Just use the boolean values directly or negate them.\nissue[2].replacement=c\nissue[2].replacement_comment=This expression is unnecessarily compared to a boolean. Just use it directly.\nissue[3].line=12\nissue[3].column=11\nissue[3].text=false != c\nissue[3].message=Comparing boolean values to boolean literals is unnecessary, as those expressions will result in booleans too. Just use the boolean values directly or negate them.\nissue[3].replacement=c\nissue[3].replacement_comment=This expression is unnecessarily compared to a boolean. Just use it directly.\nissue[4].line=14\nissue[4].column=7\nissue[4].text=e == true\nissue[4].message=Comparing boolean values to boolean literals is unnecessary, as those expressions will result in booleans too. Just use the boolean values directly or negate them.\nissue[4].replacement=e\nissue[4].replacement_comment=This expression is unnecessarily compared to a boolean. Just use it directly.\nissue[5].line=16\nissue[5].column=7\nissue[5].text=e != false\nissue[5].message=Comparing boolean values to boolean literals is unnecessary, as those expressions will result in booleans too. Just use the boolean values directly or negate them.\nissue[5].replacement=e\nissue[5].replacement_comment=This expression is unnecessarily compared to a boolean. Just use it directly.\nissue[6].line=22\nissue[6].column=11\nissue[6].text=exampleString.isEmpty == true\nissue[6].message=Comparing boolean values to boolean literals is unnecessary, as those expressions will result in booleans too. Just use the boolean values directly or negate them.\nissue[6].replacement=exampleString.isEmpty\nissue[6].replacement_comment=This expression is unnecessarily compared to a boolean. Just use it directly.\nissue[7].line=24\nissue[7].column=11\nissue[7].text=true == exampleString.isEmpty\nissue[7].message=Comparing boolean values to boolean literals is unnecessary, as those expressions will result in booleans too. Just use the boolean values directly or negate them.\nissue[7].replacement=exampleString.isEmpty\nissue[7].replacement_comment=This expression is unnecessarily compared to a boolean. Just use it directly.\nissue[8].line=27\nissue[8].column=25\nissue[8].text=value == false\nissue[8].message=Comparing boolean values to boolean literals is unnecessary, as those expressions will result in booleans too. Just use the boolean values directly or negate them.\nissue[8].replacement=!value\nissue[8].replacement_comment=This expression is unnecessarily compared to a boolean. Just negate it.\nissue[9].line=28\nissue[9].column=25\nissue[9].text=value != false\nissue[9].message=Comparing boolean values to boolean literals is unnecessary, as those expressions will result in booleans too. Just use the boolean values directly or negate them.\nissue[9].replacement=value\nissue[9].replacement_comment=This expression is unnecessarily compared to a boolean. Just use it directly.\nissue[10].line=38\nissue[10].column=34\nissue[10].text=value == true\nissue[10].message=Comparing boolean values to boolean literals is unnecessary, as those expressions will result in booleans too. Just use the boolean values directly or negate them.\nissue[10].replacement=value\nissue[10].replacement_comment=This expression is unnecessarily compared to a boolean. Just use it directly.\n"
        }
    ]
}
```

*6.6 First Element Access Detection — Report zero-index element access that should use first-element access.*

The input is source text. The output reports calls or index expressions that retrieve index zero from iterable collection values. Each issue includes the exact source span and a replacement that uses first-element access, preserving cascade syntax where applicable.

**Test Cases:** `rcb_tests/public_test_cases/feature6_6_first_element_rule.json`

```json
{
    "description": "Analyze source text and report zero-index element access that should be expressed as first-element access, including replacement suggestions.",
    "cases": [
        {
            "input": {
                "command": "analyze_rule",
                "rule": "first-element-access",
                "code": "// ignore_for_file: unnecessary_cast, unused_local_variable\n\nimport 'dart:collection';\n\nconst _array = [1, 2, 3, 4, 5, 6, 7, 8, 9];\n\nvoid func() {\n  const iterable = _array as Iterable<int>;\n\n  final firstOfIterable = iterable.first;\n  final firstElementOfIterable = iterable.elementAt(0); // LINT\n  final secondElementOfIterable = iterable.elementAt(1);\n\n  iterable\n    ..elementAt(2)\n    ..elementAt(0) // LINT\n    ..elementAt(1);\n\n////////////////////////////////////////////////////////////////////////////////\n\n  const list = _array;\n\n  final firstOfList = list.first;\n  final firstElementOfList1 = list.elementAt(0); // LINT\n  final firstElementOfList2 = list[0]; // LINT\n  final secondElementOfList1 = list.elementAt(1);\n  final secondElementOfList2 = list[1];\n\n  list\n    ..elementAt(2)\n    ..elementAt(0) // LINT\n    ..elementAt(1)\n    ..[2]\n    ..[0] // LINT\n    ..[1];\n\n  (list\n        ..[2]\n        ..[0]) // LINT\n      .length;\n\n  list\n    ..[2].toDouble()\n    ..[0].toDouble(); // LINT\n\n////////////////////////////////////////////////////////////////////////////////\n\n  final set = _array.toSet();\n\n  final firstOfSet = set.first;\n  final firstElementOfSet = set.elementAt(0); // LINT\n  final secondElementOfSet = set.elementAt(1);\n\n  set\n    ..elementAt(2)\n    ..elementAt(0) // LINT\n    ..elementAt(1);\n\n////////////////////////////////////////////////////////////////////////////////\n\n  final doubleLinkedQueue = DoubleLinkedQueue.of(_array);\n\n  final firstOfDoubleLinkedQueue = doubleLinkedQueue.first;\n  final firstElementOfDoubleLinkedQueue =\n      doubleLinkedQueue.elementAt(0); // LINT\n  final secondElementOfDoubleLinkedQueue = doubleLinkedQueue.elementAt(1);\n\n  doubleLinkedQueue\n    ..elementAt(2)\n    ..elementAt(0) // LINT\n    ..elementAt(1);\n\n////////////////////////////////////////////////////////////////////////////////\n\n  final hashSet = HashSet.of(_array);\n\n  final firstOfHashSet = hashSet.first;\n  final firstElementOfHashSet = hashSet.elementAt(0); // LINT\n  final secondElementOfHashSet = hashSet.elementAt(1);\n\n  hashSet\n    ..elementAt(2)\n    ..elementAt(0) // LINT\n    ..elementAt(1);\n\n////////////////////////////////////////////////////////////////////////////////\n\n  final linkedHashSet = LinkedHashSet.of(_array);\n\n  final firstOfLinkedHashSet = linkedHashSet.first;\n  final firstElementOfLinkedHashSet = linkedHashSet.elementAt(0); // LINT\n  final secondElementOfLinkedHashSet = linkedHashSet.elementAt(1);\n\n  linkedHashSet\n    ..elementAt(2)\n    ..elementAt(0) // LINT\n    ..elementAt(1);\n\n////////////////////////////////////////////////////////////////////////////////\n\n  final listQueue = ListQueue.of(_array);\n\n  final firstOfListQueue = listQueue.first;\n  final firstElementOfListQueue = listQueue.elementAt(0); // LINT\n  final secondElementOfListQueue = listQueue.elementAt(1);\n\n  listQueue\n    ..elementAt(2)\n    ..elementAt(0) // LINT\n    ..elementAt(1);\n\n////////////////////////////////////////////////////////////////////////////////\n\n  final queue = Queue.of(_array);\n\n  final firstOfQueue = queue.first;\n  final firstElementOfQueue = queue.elementAt(0); // LINT\n  final secondElementOfQueue = queue.elementAt(1);\n\n  queue\n    ..elementAt(2)\n    ..elementAt(0) // LINT\n    ..elementAt(1);\n\n////////////////////////////////////////////////////////////////////////////////\n\n  final splayTreeSet = SplayTreeSet.of(_array);\n\n  final firstOfSplayTreeSet = splayTreeSet.first;\n  final firstElementOfSplayTreeSet = splayTreeSet.elementAt(0); // LINT\n  final secondElementOfSplayTreeSet = splayTreeSet.elementAt(1);\n\n  splayTreeSet\n    ..elementAt(2)\n    ..elementAt(0) // LINT\n    ..elementAt(1);\n\n////////////////////////////////////////////////////////////////////////////////\n\n  final unmodifiableListView = UnmodifiableListView<int>(_array);\n\n  final firstOfUnmodifiableListView = unmodifiableListView.first;\n  final firstElementOfUnmodifiableListView1 =\n      unmodifiableListView.elementAt(0); // LINT\n  final firstElementOfUnmodifiableListView2 = unmodifiableListView[0]; // LINT\n  final secondElementOfUnmodifiableListView1 =\n      unmodifiableListView.elementAt(1);\n  final secondElementOfUnmodifiableListView2 = unmodifiableListView[1];\n\n  unmodifiableListView\n    ..elementAt(2)\n    ..elementAt(0) // LINT\n    ..elementAt(1)\n    ..[2]\n    ..[0] // LINT\n    ..[1];\n\n////////////////////////////////////////////////////////////////////////////////\n\n  final unmodifiableSetView = UnmodifiableSetView<int>(_array.toSet());\n\n  final firstOfUnmodifiableSetView = unmodifiableSetView.first;\n  final firstElementOfUnmodifiableSetView =\n      unmodifiableSetView.elementAt(0); // LINT\n  final secondElementOfUnmodifiableSetView = unmodifiableSetView.elementAt(1);\n\n  unmodifiableSetView\n    ..elementAt(2)\n    ..elementAt(0) // LINT\n    ..elementAt(1);\n}\n"
            },
            "expected_output": "rule=prefer-first\nseverity=style\nissue_count=28\nissue[0].line=11\nissue[0].column=34\nissue[0].text=iterable.elementAt(0)\nissue[0].message=Use first instead of accessing the element at zero index.\nissue[0].replacement=iterable.first\nissue[0].replacement_comment=Replace with 'first'.\nissue[1].line=16\nissue[1].column=5\nissue[1].text=..elementAt(0)\nissue[1].message=Use first instead of accessing the element at zero index.\nissue[1].replacement=..first\nissue[1].replacement_comment=Replace with 'first'.\nissue[2].line=24\nissue[2].column=31\nissue[2].text=list.elementAt(0)\nissue[2].message=Use first instead of accessing the element at zero index.\nissue[2].replacement=list.first\nissue[2].replacement_comment=Replace with 'first'.\nissue[3].line=25\nissue[3].column=31\nissue[3].text=list[0]\nissue[3].message=Use first instead of accessing the element at zero index.\nissue[3].replacement=list.first\nissue[3].replacement_comment=Replace with 'first'.\nissue[4].line=31\nissue[4].column=5\nissue[4].text=..elementAt(0)\nissue[4].message=Use first instead of accessing the element at zero index.\nissue[4].replacement=..first\nissue[4].replacement_comment=Replace with 'first'.\nissue[5].line=34\nissue[5].column=5\nissue[5].text=..[0]\nissue[5].message=Use first instead of accessing the element at zero index.\nissue[5].replacement=..first\nissue[5].replacement_comment=Replace with 'first'.\nissue[6].line=39\nissue[6].column=9\nissue[6].text=..[0]\nissue[6].message=Use first instead of accessing the element at zero index.\nissue[6].replacement=..first\nissue[6].replacement_comment=Replace with 'first'.\nissue[7].line=44\nissue[7].column=5\nissue[7].text=..[0]\nissue[7].message=Use first instead of accessing the element at zero index.\nissue[7].replacement=..first\nissue[7].replacement_comment=Replace with 'first'.\nissue[8].line=51\nissue[8].column=29\nissue[8].text=set.elementAt(0)\nissue[8].message=Use first instead of accessing the element at zero index.\nissue[8].replacement=set.first\nissue[8].replacement_comment=Replace with 'first'.\nissue[9].line=56\nissue[9].column=5\nissue[9].text=..elementAt(0)\nissue[9].message=Use first instead of accessing the element at zero index.\nissue[9].replacement=..first\nissue[9].replacement_comment=Replace with 'first'.\nissue[10].line=65\nissue[10].column=7\nissue[10].text=doubleLinkedQueue.elementAt(0)\nissue[10].message=Use first instead of accessing the element at zero index.\nissue[10].replacement=doubleLinkedQueue.first\nissue[10].replacement_comment=Replace with 'first'.\nissue[11].line=70\nissue[11].column=5\nissue[11].text=..elementAt(0)\nissue[11].message=Use first instead of accessing the element at zero index.\nissue[11].replacement=..first\nissue[11].replacement_comment=Replace with 'first'.\nissue[12].line=78\nissue[12].column=33\nissue[12].text=hashSet.elementAt(0)\nissue[12].message=Use first instead of accessing the element at zero index.\nissue[12].replacement=hashSet.first\nissue[12].replacement_comment=Replace with 'first'.\nissue[13].line=83\nissue[13].column=5\nissue[13].text=..elementAt(0)\nissue[13].message=Use first instead of accessing the element at zero index.\nissue[13].replacement=..first\nissue[13].replacement_comment=Replace with 'first'.\nissue[14].line=91\nissue[14].column=39\nissue[14].text=linkedHashSet.elementAt(0)\nissue[14].message=Use first instead of accessing the element at zero index.\nissue[14].replacement=linkedHashSet.first\nissue[14].replacement_comment=Replace with 'first'.\nissue[15].line=96\nissue[15].column=5\nissue[15].text=..elementAt(0)\nissue[15].message=Use first instead of accessing the element at zero index.\nissue[15].replacement=..first\nissue[15].replacement_comment=Replace with 'first'.\nissue[16].line=104\nissue[16].column=35\nissue[16].text=listQueue.elementAt(0)\nissue[16].message=Use first instead of accessing the element at zero index.\nissue[16].replacement=listQueue.first\nissue[16].replacement_comment=Replace with 'first'.\nissue[17].line=109\nissue[17].column=5\nissue[17].text=..elementAt(0)\nissue[17].message=Use first instead of accessing the element at zero index.\nissue[17].replacement=..first\nissue[17].replacement_comment=Replace with 'first'.\nissue[18].line=117\nissue[18].column=31\nissue[18].text=queue.elementAt(0)\nissue[18].message=Use first instead of accessing the element at zero index.\nissue[18].replacement=queue.first\nissue[18].replacement_comment=Replace with 'first'.\nissue[19].line=122\nissue[19].column=5\nissue[19].text=..elementAt(0)\nissue[19].message=Use first instead of accessing the element at zero index.\nissue[19].replacement=..first\nissue[19].replacement_comment=Replace with 'first'.\nissue[20].line=130\nissue[20].column=38\nissue[20].text=splayTreeSet.elementAt(0)\nissue[20].message=Use first instead of accessing the element at zero index.\nissue[20].replacement=splayTreeSet.first\nissue[20].replacement_comment=Replace with 'first'.\nissue[21].line=135\nissue[21].column=5\nissue[21].text=..elementAt(0)\nissue[21].message=Use first instead of accessing the element at zero index.\nissue[21].replacement=..first\nissue[21].replacement_comment=Replace with 'first'.\nissue[22].line=144\nissue[22].column=7\nissue[22].text=unmodifiableListView.elementAt(0)\nissue[22].message=Use first instead of accessing the element at zero index.\nissue[22].replacement=unmodifiableListView.first\nissue[22].replacement_comment=Replace with 'first'.\nissue[23].line=145\nissue[23].column=47\nissue[23].text=unmodifiableListView[0]\nissue[23].message=Use first instead of accessing the element at zero index.\nissue[23].replacement=unmodifiableListView.first\nissue[23].replacement_comment=Replace with 'first'.\nissue[24].line=152\nissue[24].column=5\nissue[24].text=..elementAt(0)\nissue[24].message=Use first instead of accessing the element at zero index.\nissue[24].replacement=..first\nissue[24].replacement_comment=Replace with 'first'.\nissue[25].line=155\nissue[25].column=5\nissue[25].text=..[0]\nissue[25].message=Use first instead of accessing the element at zero index.\nissue[25].replacement=..first\nissue[25].replacement_comment=Replace with 'first'.\nissue[26].line=164\nissue[26].column=7\nissue[26].text=unmodifiableSetView.elementAt(0)\nissue[26].message=Use first instead of accessing the element at zero index.\nissue[26].replacement=unmodifiableSetView.first\nissue[26].replacement_comment=Replace with 'first'.\nissue[27].line=169\nissue[27].column=5\nissue[27].text=..elementAt(0)\nissue[27].message=Use first instead of accessing the element at zero index.\nissue[27].replacement=..first\nissue[27].replacement_comment=Replace with 'first'.\n"
        }
    ]
}
```

*6.7 Trailing Comma Detection — Report multiline constructs where a trailing comma should be inserted.*

The input is source text and optional line-breaking configuration. The output reports function parameters, call arguments, enum entries, constructor arguments, and collection entries that should end with a trailing comma, including replacement text when available.

**Test Cases:** `rcb_tests/public_test_cases/feature6_7_trailing_commas_rule.json`

```json
{
    "description": "Analyze multiline declarations or collection literals and report positions where a trailing comma should be added, including the replacement text.",
    "cases": [
        {
            "input": {
                "command": "analyze_rule",
                "rule": "missing-trailing-commas",
                "code": "// LINT\nvoid firstFunction(\n    String firstArgument, String secondArgument, String thirdArgument) {\n  return;\n}\n\nvoid secondFunction() {\n  firstFunction('some string', 'some other string',\n      'and another string for length exceed'); // LINT\n}\n\nvoid thirdFunction(String someLongVarName, void Function() someLongCallbackName,\n    String arg3) {} // LINT\n\nclass TestClass {\n  // LINT\n  void firstMethod(\n      String firstArgument, String secondArgument, String thirdArgument) {\n    return;\n  }\n\n  void secondMethod() {\n    firstMethod('some string', 'some other string',\n        'and another string for length exceed'); // LINT\n\n    thirdFunction('some string', () {\n      return;\n    }, 'some other string'); // LINT\n  }\n}\n\nenum FirstEnum {\n  firstItem,\n  secondItem,\n  thirdItem,\n  forthItem,\n  fifthItem,\n  sixthItem // LINT\n}\n\nclass FirstClass {\n  final num firstField;\n  final num secondField;\n  final num thirdField;\n  final num forthField;\n\n  // LINT\n  const FirstClass(\n      this.firstField, this.secondField, this.thirdField, this.forthField);\n}\n\nconst instance =\n    FirstClass(3.14159265359, 3.14159265359, 3.14159265359, 3.14159265359);\n\nfinal secondArray = [\n  'some string',\n  'some other string',\n  'and another string for length exceed' // LINT\n];\n\nfinal secondSet = {\n  'some string',\n  'some other string',\n  'and another string for length exceed' // LINT\n};\n\nfinal secondMap = {\n  'some string': 'and another string for length exceed',\n  // LINT\n  'and another string for length exceed': 'and another string for length exceed'\n};\n"
            },
            "expected_output": "rule=prefer-trailing-comma\nseverity=warning\nissue_count=11\nissue[0].line=3\nissue[0].column=50\nissue[0].text=String thirdArgument\nissue[0].message=Prefer trailing comma.\nissue[0].replacement=String thirdArgument,\nissue[0].replacement_comment=Add trailing comma.\nissue[1].line=9\nissue[1].column=7\nissue[1].text='and another string for length exceed'\nissue[1].message=Prefer trailing comma.\nissue[1].replacement='and another string for length exceed',\nissue[1].replacement_comment=Add trailing comma.\nissue[2].line=13\nissue[2].column=5\nissue[2].text=String arg3\nissue[2].message=Prefer trailing comma.\nissue[2].replacement=String arg3,\nissue[2].replacement_comment=Add trailing comma.\nissue[3].line=18\nissue[3].column=52\nissue[3].text=String thirdArgument\nissue[3].message=Prefer trailing comma.\nissue[3].replacement=String thirdArgument,\nissue[3].replacement_comment=Add trailing comma.\nissue[4].line=24\nissue[4].column=9\nissue[4].text='and another string for length exceed'\nissue[4].message=Prefer trailing comma.\nissue[4].replacement='and another string for length exceed',\nissue[4].replacement_comment=Add trailing comma.\nissue[5].line=28\nissue[5].column=8\nissue[5].text='some other string'\nissue[5].message=Prefer trailing comma.\nissue[5].replacement='some other string',\nissue[5].replacement_comment=Add trailing comma.\nissue[6].line=38\nissue[6].column=3\nissue[6].text=sixthItem\nissue[6].message=Prefer trailing comma.\nissue[6].replacement=sixthItem,\nissue[6].replacement_comment=Add trailing comma.\nissue[7].line=49\nissue[7].column=59\nissue[7].text=this.forthField\nissue[7].message=Prefer trailing comma.\nissue[7].replacement=this.forthField,\nissue[7].replacement_comment=Add trailing comma.\nissue[8].line=58\nissue[8].column=3\nissue[8].text='and another string for length exceed'\nissue[8].message=Prefer trailing comma.\nissue[8].replacement='and another string for length exceed',\nissue[8].replacement_comment=Add trailing comma.\nissue[9].line=64\nissue[9].column=3\nissue[9].text='and another string for length exceed'\nissue[9].message=Prefer trailing comma.\nissue[9].replacement='and another string for length exceed',\nissue[9].replacement_comment=Add trailing comma.\nissue[10].line=70\nissue[10].column=3\nissue[10].text='and another string for length exceed': 'and another string for length exceed'\nissue[10].message=Prefer trailing comma.\nissue[10].replacement='and another string for length exceed': 'and another string for length exceed',\nissue[10].replacement_comment=Add trailing comma.\n"
        },
        {
            "input": {
                "command": "analyze_rule",
                "rule": "missing-trailing-commas",
                "code": "void firstFunction(\n  String firstArgument,\n  String secondArgument,\n  String thirdArgument,\n) {\n  return;\n}\n\nvoid secondFunction(String arg1) {\n  firstFunction(\n    '',\n    '',\n    '',\n  );\n}\n\nvoid thirdFunction(String arg1, void Function() callback) {}\n\nvoid forthFunction(void Function() callback) {}\n\nclass TestClass {\n  void firstMethod(\n    String firstArgument,\n    String secondArgument,\n    String thirdArgument,\n  ) {\n    return;\n  }\n\n  void secondMethod() {\n    firstMethod(\n      'some string',\n      'some other string',\n      'and another string for length exceed',\n    );\n\n    thirdFunction('', () {\n      return;\n    });\n\n    forthFunction(() {\n      return;\n    });\n  }\n\n  void thirdMethod(\n    String arg1,\n  ) {\n    firstMethod(\n      arg1,\n      '',\n      '',\n    );\n    firstFunction(\n      arg1,\n      '',\n      '',\n    );\n  }\n}\n\nenum FirstEnum {\n  firstItem,\n  secondItem,\n  thirdItem,\n  forthItem,\n  fifthItem,\n  sixthItem,\n}\n\nenum SecondEnum {\n  firstItem,\n}\n\nenum ThirdEnum { firstItem }\n\nclass FirstClass {\n  final num firstField;\n  final num secondField;\n  final num thirdField;\n  final num forthField;\n\n  const FirstClass(\n    this.firstField,\n    this.secondField,\n    this.thirdField,\n    this.forthField,\n  );\n}\n\nconst firstInstance = FirstClass(0, 0, 0, 0);\nconst secondInstance = FirstClass(\n  0,\n  0,\n  0,\n  0,\n);\n\nfinal firstArray = ['some string'];\nfinal secondArray = [\n  'some string',\n  'some other string',\n  'and another string for length exceed',\n];\nfinal thirdArray = [\n  'some string',\n];\n\nfinal firstSet = {'some string'};\nfinal secondSet = {\n  'some string',\n  'some other string',\n  'and another string for length exceed',\n};\nfinal thirdSet = {\n  'some string',\n};\n\nfinal firstMap = {'some string': 'some string'};\nfinal secondMap = {\n  'some string': 'and another string for length exceed',\n  'and another string for length exceed':\n      'and another string for length exceed',\n};\nfinal thirdMap = {\n  'some string': 'some string',\n};\n",
                "config": {
                    "break-on": 1
                }
            },
            "expected_output": "rule=prefer-trailing-comma\nseverity=warning\nissue_count=10\nissue[0].line=9\nissue[0].column=21\nissue[0].text=String arg1\nissue[0].message=Prefer trailing comma.\nissue[0].replacement=String arg1,\nissue[0].replacement_comment=Add trailing comma.\nissue[1].line=17\nissue[1].column=33\nissue[1].text=void Function() callback\nissue[1].message=Prefer trailing comma.\nissue[1].replacement=void Function() callback,\nissue[1].replacement_comment=Add trailing comma.\nissue[2].line=19\nissue[2].column=20\nissue[2].text=void Function() callback\nissue[2].message=Prefer trailing comma.\nissue[2].replacement=void Function() callback,\nissue[2].replacement_comment=Add trailing comma.\nissue[3].line=37\nissue[3].column=23\nissue[3].text=() {\\n      return;\\n    }\nissue[3].message=Prefer trailing comma.\nissue[3].replacement=() {\\n      return;\\n    },\nissue[3].replacement_comment=Add trailing comma.\nissue[4].line=41\nissue[4].column=19\nissue[4].text=() {\\n      return;\\n    }\nissue[4].message=Prefer trailing comma.\nissue[4].replacement=() {\\n      return;\\n    },\nissue[4].replacement_comment=Add trailing comma.\nissue[5].line=75\nissue[5].column=18\nissue[5].text=firstItem\nissue[5].message=Prefer trailing comma.\nissue[5].replacement=firstItem,\nissue[5].replacement_comment=Add trailing comma.\nissue[6].line=91\nissue[6].column=43\nissue[6].text=0\nissue[6].message=Prefer trailing comma.\nissue[6].replacement=0,\nissue[6].replacement_comment=Add trailing comma.\nissue[7].line=99\nissue[7].column=21\nissue[7].text='some string'\nissue[7].message=Prefer trailing comma.\nissue[7].replacement='some string',\nissue[7].replacement_comment=Add trailing comma.\nissue[8].line=109\nissue[8].column=19\nissue[8].text='some string'\nissue[8].message=Prefer trailing comma.\nissue[8].replacement='some string',\nissue[8].replacement_comment=Add trailing comma.\nissue[9].line=119\nissue[9].column=19\nissue[9].text='some string': 'some string'\nissue[9].message=Prefer trailing comma.\nissue[9].replacement='some string': 'some string',\nissue[9].replacement_comment=Add trailing comma.\n"
        }
    ]
}
```

*6.8 Throw Inside Catch Detection — Report throw statements that occur inside catch handlers.*

The input is source text containing exception-handling blocks. The output reports throw statements inside catch handlers because they lose the original failure context, while preserving exact location and source span text.

**Test Cases:** `rcb_tests/public_test_cases/feature6_8_throw_inside_catch_rule.json`

```json
{
    "description": "Analyze exception-handling code and report throw statements inside catch handlers because they discard the original failure context.",
    "cases": [
        {
            "input": {
                "command": "analyze_rule",
                "rule": "throw-inside-catch",
                "code": "void main() {\n  try {\n    repository();\n  } on Object catch (error, stackTrace) {\n    logError(error, stackTrace);\n  }\n}\n\n/// Where did the original error occur based on the log?\nvoid logError(Object error, StackTrace stackTrace) =>\n    print('$error\\n$stackTrace');\n\nvoid repository() {\n  try {\n    networkDataProvider();\n  } on Object {\n    throw RepositoryException(); // LINT\n  }\n}\n\nvoid networkDataProvider() {\n  try {\n    networkClient();\n  } on Object {\n    throw DataProviderException(); // LINT\n  }\n}\n\nvoid networkClient() {\n  throw 'Some serious problem';\n}\n\nclass RepositoryException {}\n\nclass DataProviderException {}\n"
            },
            "expected_output": "rule=avoid-throw-in-catch-block\nseverity=warning\nissue_count=2\nissue[0].line=17\nissue[0].column=5\nissue[0].text=throw RepositoryException()\nissue[0].message=Call throw in a catch block loses the original stack trace and the original exception.\nissue[1].line=25\nissue[1].column=5\nissue[1].text=throw DataProviderException()\nissue[1].message=Call throw in a catch block loses the original stack trace and the original exception.\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same serialization style as used in the previous YAML round-trip tests
