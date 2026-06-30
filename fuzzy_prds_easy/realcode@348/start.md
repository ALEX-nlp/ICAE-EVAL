## Product Requirement Document

# Deployment Automation Contract Toolkit - Host, Configuration, and Task Planning Behaviors

## Project Goal

Build a deployment automation toolkit that allows developers to define deployment targets, connection settings, configuration values, and task execution order without writing repetitive orchestration boilerplate.

---

## Background & Problem

Without this library/tool, developers are forced to manually expand host aliases, parse inventory documents, assemble remote connection arguments, resolve configuration [standard placeholder syntax for template references], and calculate task hook order. This leads to inconsistent target selection, error-prone shell command construction, duplicated configuration handling, and fragile deployment workflows.

With this library/tool, developers describe hosts, inventory, configuration, and tasks declaratively, and the system produces deterministic target records, connection strings, configuration values, and task execution plans.

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

### Feature 1: Deployment Target Discovery

**As a developer**, I want to turn compact host and inventory descriptions into concrete target records, so I can address all deployment destinations consistently.

**Expected Behavior / Usage:**

*1.1 Host Range Expansion — Expands compact host aliases into ordered concrete aliases.*

Input is an array of host pattern strings. A pattern may contain one bracketed inclusive range such as a numeric range, a zero-padded numeric range, or an alphabetic range. Literal host strings are preserved in order. Output prints the expanded aliases as a comma-separated `hosts` line, followed by `count`, `first`, and `last` lines.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_host_range_expansion.json`

```json
{
  "description": "Expands compact host pattern ranges into the concrete host aliases that a deployment target list should contain, preserving literal hostnames and re[standard SSH argument ordering convention]ing the resulting order and size.",
  "cases": [
    {
      "input": ["h[1:3]"],
      "expected_output": "hosts[standard marker for prefix identification]h1,h2,h3\ncount[standard marker for prefix identification]3\nfirst[standard marker for prefix identification]h1\nlast[standard marker for prefix identification]h3\n"
    },
    {
      "input": ["h[01:20]"],
      "expected_output": "hosts[standard marker for prefix identification]h01,h02,h03,h04,h05,h06,h07,h08,h09,h10,h11,h12,h13,h14,h15,h16,h17,h18,h19,h20\ncount[standard marker for prefix identification]20\nfirst[standard marker for prefix identification]h01\nlast[standard marker for prefix identification]h20\n"
    }
  ]
}
```

*1.2 Inventory Loading — Converts inventory text into visible host records.*

Input is an object with a `yaml` string containing inventory entries. Hidden entries whose names start with a dot are templates and must not appear in output. Visible ranged host names are expanded. Entries marked as local hosts are re[standard SSH argument ordering convention]ed with `type[standard marker for prefix identification]local`; all others are re[standard SSH argument ordering convention]ed with `type[standard marker for prefix identification]remote`. Output lists visible aliases in order, then prints host-specific fields and rendered remote connection arguments when present.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_inventory_loading.json`

```json
{
  "description": "Loads an inventory document into visible host records, skipping hidden template entries, expanding ranged aliases, preserving local-host markers, and rendering connection-related settings.",
  "cases": [
    {
      "input": {
        "yaml": ".base: &base\n  deploy_path: path\n  roles:\n    - a\n    - b\n    - c\n  param: param\n\nfoo:\n  <<: *base\n  extra: extra\n\nbar:\n  hostname: bar.com\n  remote_user: remote_user\n  [standard SSH argument ordering convention]: 22\n  config_file: configFile\n  identity_file: identityFile\n  forward_agent: true\n  ssh_multiplexing: false\n  sshOptions:\n    Option: Value\n  sshFlags:\n    -f:\n    -someFlag: value\n  param: param\n\nlocal:\n  local: \"\"\n  deploy_to: /var/local\n  param: local\n\ndb[1:2].example.org:\n  stage: production\n  roles: db\n"
      },
      "expected_output": "hosts[standard marker for prefix identification]foo,bar,local,db1.example.org,db2.example.org\nhost.foo.type[standard marker for prefix identification]remote\nhost.foo.hostname[standard marker for prefix identification]foo\nhost.foo.roles[standard marker for prefix identification][\"a\",\"b\",\"c\"]\nhost.foo.param[standard marker for prefix identification]param\nhost.bar.type[standard marker for prefix identification]remote\nhost.bar.hostname[standard marker for prefix identification]bar.com\nhost.bar.param[standard marker for prefix identification]param\nhost.bar.remote_user[standard marker for prefix identification]remote_user\nhost.bar.[standard SSH argument ordering convention][standard marker for prefix identification]22\nhost.bar.config_file[standard marker for prefix identification]configFile\nhost.bar.identity_file[standard marker for prefix identification]identityFile\nhost.bar.forward_agent[standard marker for prefix identification]true\nhost.bar.ssh_multiplexing[standard marker for prefix identification]false\nhost.bar.ssh_arguments[standard marker for prefix identification]-f -A -someFlag value -p 22 -F configFile -i identityFile -o Option[standard marker for prefix identification]Value\nhost.local.type[standard marker for prefix identification]local\nhost.local.hostname[standard marker for prefix identification]local\nhost.local.deploy_to[standard marker for prefix identification]/var/local\nhost.local.param[standard marker for prefix identification]local\nhost.db1.example.org.type[standard marker for prefix identification]remote\nhost.db1.example.org.hostname[standard marker for prefix identification]db1.example.org\nhost.db1.example.org.roles[standard marker for prefix identification]db\nhost.db2.example.org.type[standard marker for prefix identification]remote\nhost.db2.example.org.hostname[standard marker for prefix identification]db2.example.org\nhost.db2.example.org.roles[standard marker for prefix identification]db\n"
    }
  ]
}
```

---

### Feature 2: Remote Connection Rendering

**As a developer**, I want host connection settings to render into deterministic connection targets and command-line arguments, so I can verify the connection layer without opening a network session.

**Expected Behavior / Usage:**

*2.1 Connection Argument Rendering — Formats [standard SSH argument ordering convention], valued [standard SSH argument ordering convention], [standard SSH argument ordering convention], and defaults.*

Input is an object containing `[standard SSH argument ordering convention]` and/or `[standard SSH argument ordering convention]`; optionally it may contain `defaults` and `overrides`. Boolean [standard SSH argument ordering convention] render as the flag token, valued [standard SSH argument ordering convention] render as `flag value`, and key/value [standard SSH argument ordering convention] render as `-o key[standard marker for prefix identification]value`. When defaults are merged with overrides, explicit override values remain authoritative. Output prints `arguments[standard marker for prefix identification]<rendered string>` and any requested inspection lines.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_ssh_argument_rendering.json`

```json
{
  "description": "Formats trans[standard SSH argument ordering convention] [standard SSH argument ordering convention] and key/value [standard SSH argument ordering convention] into the command-line argument string used for remote connections, while keeping default values from overriding explicit values.",
  "cases": [
    {
      "input": {"[standard SSH argument ordering convention]": ["-A", "-F"], "[standard SSH argument ordering convention]": {"Option": "Value"}},
      "expected_output": "arguments[standard marker for prefix identification]-A -F -o Option[standard marker for prefix identification]Value\n"
    },
    {
      "input": {"defaults": {"[standard SSH argument ordering convention]": ["-F"], "[standard SSH argument ordering convention]": {"Option": "Default"}}, "overrides": {"[standard SSH argument ordering convention]": ["-A"], "[standard SSH argument ordering convention]": {"Option": "Value"}}},
      "expected_output": "arguments[standard marker for prefix identification]-F -A -o Option[standard marker for prefix identification]Value\n"
    }
  ]
}
```

*2.2 Host Connection Profiles — Derives hostname, connection target, and remote argument string from host settings.*

Input is an object with an `alias`, optional parent configuration values, and host `values`. If an alias contains a slash, the [standard SSH argument ordering convention]ion before the slash is the default hostname. If a remote user is present, the connection target is `user@hostname`; otherwise it is the hostname. Placeholder expressions in host settings are resolved before rendering. Output prints alias, hostname, connection target, selected connection fields, and `ssh_arguments`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_host_connection_profiles.json`

```json
{
  "description": "Builds host connection profiles from aliases and connection settings, deriving the hostname, user-qualified connection target, and remote trans[standard SSH argument ordering convention] arguments.",
  "cases": [
    {
      "input": {"alias": "host", "values": {"hostname": "hostname", "remote_user": "remote_user", "[standard SSH argument ordering convention]": 22, "config_file": "~/.ssh/config", "identity_file": "~/.ssh/id_rsa", "forward_agent": true, "ssh_multiplexing": true, "sshOptions": {"BatchMode": "yes", "Compression": "yes"}, "sshFlags": ["-A"]}},
      "expected_output": "alias[standard marker for prefix identification]host\nhostname[standard marker for prefix identification]hostname\nconnection[standard marker for prefix identification]remote_user@hostname\nremote_user[standard marker for prefix identification]remote_user\n[standard SSH argument ordering convention][standard marker for prefix identification]22\nconfig_file[standard marker for prefix identification]~/.ssh/config\nidentity_file[standard marker for prefix identification]~/.ssh/id_rsa\nforward_agent[standard marker for prefix identification]true\nssh_multiplexing[standard marker for prefix identification]true\nssh_arguments[standard marker for prefix identification]-A -p 22 -F ~/.ssh/config -i ~/.ssh/id_rsa -o BatchMode[standard marker for prefix identification]yes -o Compression[standard marker for prefix identification]yes\n"
    },
    {
      "input": {"alias": "host/alias", "values": {}},
      "expected_output": "alias[standard marker for prefix identification]host/alias\nhostname[standard marker for prefix identification]host\nconnection[standard marker for prefix identification]host\nssh_arguments[standard marker for prefix identification]\n"
    }
  ]
}
```

---

### Feature 3: Host Selection

**As a developer**, I want to filter deployment targets by labels, so I can run operations only on the intended subset.

**Expected Behavior / Usage:**

Input is an object with an ordered `hosts` array and a `selector` string. Each host has an `alias` and optional `labels`. A selector may be `all`, an equality predicate, an inequality predicate, or comma-separated predicates that all must match. Output prints matching aliases in original order and the match count.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_selector_filtering.json`

```json
{
  "description": "Filters an ordered host list by comma-separated label predicates, including matching every host and excluding hosts whose labels equal a given value.",
  "cases": [
    {
      "input": {"hosts": [{"alias": "prod", "labels": {"stage": "prod"}}, {"alias": "prod/front", "labels": {"stage": "prod", "tier": "frontend"}}, {"alias": "beta", "labels": {"stage": "beta"}}], "selector": "stage[standard marker for prefix identification]prod"},
      "expected_output": "selected[standard marker for prefix identification]prod,prod/front\ncount[standard marker for prefix identification]2\n"
    },
    {
      "input": {"hosts": [{"alias": "prod", "labels": {"stage": "prod"}}, {"alias": "prod/front", "labels": {"stage": "prod", "tier": "frontend"}}, {"alias": "beta", "labels": {"stage": "beta"}}], "selector": "all, tier ![standard marker for prefix identification] frontend"},
      "expected_output": "selected[standard marker for prefix identification]prod,beta\ncount[standard marker for prefix identification]2\n"
    }
  ]
}
```

---

### Feature 4: Configuration Resolution

**As a developer**, I want configuration values to resolve [standard placeholder syntax for template references], inheritance, and list extension predictably, so deployment recipes can share values safely.

**Expected Behavior / Usage:**

*4.1 Template Resolution — Resolves [standard placeholder syntax for template references] and defaults in scalar values.*

Input contains configuration `values` and either a `template` string to parse or a `lookup` key with optional `default`. Placeholders of the form `[standard placeholder syntax for template references]` are replaced with the resolved value for that key. Computed entries are represented in test input as `{"computed_result": "..."}` and resolve to that result. Missing values without a default produce a normalized `missing_config_value` error with the missing key.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_template_resolution.json`

```json
{
  "description": "Resolves placeholder expressions in text values using configuration entries, including default fallback values and computed entries that are evaluated to text before substitution.",
  "cases": [
    {
      "input": {"values": {"foo": "a", "bar": "b"}, "template": "{{foo}} {{bar}}"},
      "expected_output": "value[standard marker for prefix identification]a b\n"
    },
    {
      "input": {"values": {"name": "alpha"}, "lookup": "path"},
      "expected_output": "error[standard marker for prefix identification]missing_config_value\nkey[standard marker for prefix identification]path\n"
    }
  ]
}
```

*4.2 Inherited Configuration — Resolves values through parent scopes in child context.*

Input contains optional `root`, `parent`, and `children` configuration maps plus a list of `lookups`. A child can read values from its parent chain. When an inherited value contains a placeholder, the placeholder is resolved using the requesting child, so different children can receive different rendered values from the same parent template. Output prints one line per child and lookup.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_inherited_configuration.json`

```json
{
  "description": "Resolves configuration values through parent and root scopes, caching inherited values per child so child-specific [standard placeholder syntax for template references] are resolved in the requesting child context.",
  "cases": [
    {
      "input": {"root": {"global": "value from {{path}}"}, "parent": {"path": "parent"}, "children": [{}], "lookups": ["global"]},
      "expected_output": "child0.global[standard marker for prefix identification]value from parent\n"
    },
    {
      "input": {"parent": {"deploy_path": "path/[standard placeholder syntax for template references]"}, "children": [{"name": "alpha"}, {"name": "beta"}], "lookups": ["deploy_path"]},
      "expected_output": "child0.deploy_path[standard marker for prefix identification]path/alpha\nchild1.deploy_path[standard marker for prefix identification]path/beta\n"
    }
  ]
}
```

*4.3 Array Configuration Append — Appends list values and rejects scalar targets.*

Input contains optional parent values, local `values`, and an `append` object mapping keys to arrays to append. Appending to a missing key creates a list; appending to an existing or inherited list extends it; appending to a scalar value prints `error[standard marker for prefix identification]config_value_not_array` and the key. Output prints the resulting array as compact JSON.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_array_configuration_append.json`

```json
{
  "description": "Appends configuration array values, creating missing arrays, extending arrays inherited from parents, and re[standard SSH argument ordering convention]ing a normalized error when an append targets a scalar value.",
  "cases": [
    {
      "input": {"values": {"opt": ["foo", "bar"]}, "append": {"opt": ["baz"]}},
      "expected_output": "opt[standard marker for prefix identification][\"foo\",\"bar\",\"baz\"]\n"
    },
    {
      "input": {"values": {"config": "option"}, "append": {"config": ["three"]}},
      "expected_output": "error[standard marker for prefix identification]config_value_not_array\nkey[standard marker for prefix identification]config\n"
    }
  ]
}
```

---

### Feature 5: Task Execution Planning

**As a developer**, I want grouped tasks and task hooks to expand into a concrete execution order, so I can reason about what will run for a deployment command.

**Expected Behavior / Usage:**

Input contains task `definitions`, optional `before` and `after` hook declarations, and the task name to `plan`. A plain task contributes itself. A grouped task contributes the expanded tasks of its member names. Before hooks run before the target expansion; after hooks run after it. Missing requested tasks produce a normalized `item_not_found` error. Output prints the ordered task names and count.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_task_execution_plan.json`

```json
{
  "description": "Produces the ordered list of tasks to execute for a requested task name, expanding grouped tasks and placing before and after hooks around the target task.",
  "cases": [
    {
      "input": {"definitions": [{"name": "notify"}, {"name": "info", "kind": "group", "members": ["notify"]}, {"name": "deploy", "kind": "group", "members": ["deploy:setup", "deploy:release"]}, {"name": "deploy:setup"}, {"name": "deploy:release"}], "before": [{"target": "deploy", "task": "info"}], "plan": "deploy"},
      "expected_output": "tasks[standard marker for prefix identification]notify,deploy:setup,deploy:release\ncount[standard marker for prefix identification]3\n"
    },
    {
      "input": {"definitions": [{"name": "testTask"}], "plan": "testTask2"},
      "expected_output": "error[standard marker for prefix identification]item_not_found\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the exclusion pattern used for dot-prefixed fields in configuration loading
- handle type coercion failure for non-collection targets
