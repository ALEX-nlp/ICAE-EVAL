## Product Requirement Document

# Project Scaffolding & Template Rendering Engine - Product Requirements

## Project Goal

Build a project-scaffolding engine that turns a *template tree* (a directory of files and folders, some of which contain placeholders) into a concrete *destination project*, substituting caller-supplied answers into both file contents and file/folder names. The engine allows developers to capture a reusable project skeleton once and stamp out fresh, customised copies of it on demand, without hand-editing every generated file.

---

## Background & Problem

Without such a tool, teams that start many similar projects (services, libraries, packages) are forced to copy an old project by hand and then walk through every file renaming things, swapping in the new project name, deleting the bits that do not apply, and remembering which files must never be overwritten on a re-run. This is repetitive, slow, and error-prone: a missed rename or an accidentally clobbered local change can silently break the new project.

With this engine, a template author declares the skeleton, the placeholders, the selection rules (what to copy, what to skip), and the overwrite policy once. A consumer then supplies a small set of answers and receives a fully materialised project. Re-running the engine over an existing project is safe: unchanged files are recognised, changed files are flagged, and protected files are preserved.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This is a multi-responsibility system (input/output routing, template rendering, entry selection, overwrite policy, configuration loading, configuration validation, configuration merging, action reporting). It MUST therefore be organised as a clear, multi-file repository (e.g. a core package plus a separate execution adapter) rather than a single "god file". Do not over-engineer, but do not collapse distinct responsibilities into one module.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in the "Core Features" section are a **black-box testing contract** for the execution adapter, NOT the internal data model of the engine. The core rendering/selection/validation logic MUST remain fully decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls into the core engine and for rendering results and errors to stdout per the contract below.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, rendering, overwrite resolution, and output formatting into distinct units.
   - **Open/Closed Principle (OCP):** Adding a new selection rule or option must not require rewriting the rendering core.
   - **Liskov Substitution Principle (LSP):** Derived option/config types must be substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep option/config interfaces small and cohesive.
   - **Dependency Inversion Principle (DIP):** The rendering core must depend on abstractions, not on the stdin/stdout adapter.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core engine must be elegant and idiomatic to the target language, hiding internal complexity behind a small render/copy entry point.
   - **Resilience:** Invalid configuration, missing templates, and unresolved references must be modelled as explicit, typed error conditions rather than generic faults. Every error surfaced to stdout MUST be a **language-neutral category** (e.g. `error=invalid_config_data`, `error=[a specific template resolution error code]`) with structured fields; it MUST NOT leak host-language exception class names, runtime message suffixes, or object reprs.

---

## Core Features

### Feature 1: Template Tree Rendering

**As a developer**, I want files and folder names in a template tree to be expanded with my supplied answers, so I can stamp out a customised project from a reusable skeleton.

**Expected Behavior / Usage:**

The engine walks a source template tree and writes a destination tree. A file whose name carries the template suffix (`.tmpl`) has its contents expanded by the templating engine using the supplied named answers, and the suffix is stripped from the produced file name. A file without that suffix is copied verbatim. Names of files and directories may themselves contain placeholders written as `[[ name ]]`; these are expanded into the produced path. If both a plain file and a same-named file carrying the template suffix exist, the suffixed (rendered) one wins and the plain one is dropped. The output reports the count of produced files, then the sorted produced paths (lines prefixed `path: `), then the produced content of each file (lines prefixed `file: <path> -> ` followed by the JSON-escaped file text).

**Test Cases:** `rcb_tests/public_test_cases/feature1_render_engine.json`

```json
{
  "description": "Rendering of a source template tree into a destination. Files whose name carries the template suffix have their contents expanded with the templating engine using the supplied named answers, and the suffix is stripped from the produced name. Files without the suffix are copied verbatim. Names of files and directories may themselves contain placeholders that are expanded into the produced path. When a plain file and a same-named file carrying the template suffix both exist, the suffixed (rendered) one takes precedence and the plain one is dropped. Output reports the count of produced files, the sorted produced paths, and the produced content of each file.",
  "cases": [
    {
      "input": {
        "op": "render",
        "src": {
          "README.txt": "Static line.\n",
          "greeting.txt.tmpl": "Hello [[ audience ]]!\n"
        },
        "data": {
          "audience": "world"
        }
      },
      "expected_output": "produced=2\npath: README.txt\npath: greeting.txt\nfile: README.txt -> \"Static line.\\n\"\nfile: greeting.txt -> \"Hello world!\\n\"\n"
    },
    {
      "input": {
        "op": "render",
        "src": {
          "[[ pkg ]]/__init__.py.tmpl": "name = '[[ pkg ]]'\n",
          "[[ title ]].txt": "verbatim content\n"
        },
        "data": {
          "pkg": "acme",
          "title": "NOTES"
        }
      },
      "expected_output": "produced=2\npath: NOTES.txt\npath: acme/__init__.py\nfile: NOTES.txt -> \"verbatim content\\n\"\nfile: acme/__init__.py -> \"name = 'acme'\\n\"\n"
    },
    {
      "input": {
        "op": "render",
        "src": {
          "README.txt": "PLAIN\n",
          "README.txt.tmpl": "Rendered for [[ project ]].\n"
        },
        "data": {
          "project": "Demo"
        }
      },
      "expected_output": "produced=1\npath: README.txt\nfile: README.txt -> \"Rendered for Demo.\\n\"\n"
    }
  ]
}
```

---

### Feature 2: Entry Selection (Exclude / Include)

**As a developer**, I want fine-grained control over which template entries reach the destination, so I can keep junk and metadata out while still admitting specific files when needed.

**Expected Behavior / Usage:**

A built-in set of patterns is excluded by default: version-control metadata, compiled/cache artifacts, editor backup files, and the configuration file itself. An explicit `exclude` option drops additional entries matching shell-style glob patterns (e.g. `*.log`). An `include` option re-admits entries that the default exclusion would otherwise drop, either by exact name or by glob pattern. The configuration file may also declare exclusion and inclusion pattern lists that drive the same selection. The output is the rendered destination listing (produced count, sorted `path:` lines, then `file:` content lines), so the effect of a selection rule is observable as the presence or absence of entries.

**Test Cases:** `rcb_tests/public_test_cases/feature2_exclude_include.json`

```json
{
  "description": "Selection of which template entries reach the destination. A built-in set of patterns is excluded by default (version-control metadata, compiled/cache artifacts, editor backups, the configuration file itself). An explicit exclude option drops entries matching shell-style patterns. An include option re-admits entries that the default exclusion would otherwise drop, by exact name or by pattern. The configuration file may also declare exclusion and inclusion pattern lists that drive the same selection.",
  "cases": [
    {
      "input": {
        "op": "render",
        "src": {
          "keep.txt": "keep\n",
          ".svn": "x\n",
          "a.pyc": "x\n",
          "~tmp": "x\n"
        },
        "data": {}
      },
      "expected_output": "produced=1\npath: keep.txt\nfile: keep.txt -> \"keep\\n\"\n"
    },
    {
      "input": {
        "op": "render",
        "src": {
          "a.txt": "A\n",
          "b.log": "B\n"
        },
        "exclude": [
          "*.log"
        ],
        "data": {}
      },
      "expected_output": "produced=1\npath: a.txt\nfile: a.txt -> \"A\\n\"\n"
    },
    {
      "input": {
        "op": "render",
        "src": {
          "keep.txt": "keep\n",
          ".svn": "svn\n"
        },
        "include": [
          ".svn"
        ],
        "data": {}
      },
      "expected_output": "produced=2\npath: .svn\npath: keep.txt\nfile: .svn -> \"svn\\n\"\nfile: keep.txt -> \"keep\\n\"\n"
    }
  ]
}
```

---

### Feature 3: Overwrite & Preservation Control

**As a developer**, I want precise control over what happens when a produced file already exists in the destination, so a re-run never silently destroys files I want to protect.

**Expected Behavior / Usage:**

When a produced file already exists at the destination, the policy is resolved as follows. A `skip_if_exists` list names files whose pre-existing content must be preserved even when overwriting is otherwise forced; the patterns in this list are themselves rendered with the answers before matching (so `[[ name ]]/c.txt` expands first). A global skip mode preserves every pre-existing file. A global force mode overwrites every pre-existing file. The output reports the final destination contents (produced count, sorted `path:` lines, then `file:` content lines), so a preserved file shows its old content and an overwritten file shows the new content.

**Test Cases:** `rcb_tests/public_test_cases/feature3_overwrite.json`

```json
{
  "description": "Behaviour when a produced file already exists in the destination. A skip-if-exists list (whose patterns are themselves rendered with the answers) preserves the pre-existing content of matching files even when overwriting is forced. A global skip mode preserves every pre-existing file, while a global force mode overwrites every pre-existing file. Output reports the final destination contents.",
  "cases": [
    {
      "input": {
        "op": "render",
        "src": {
          "a.txt": "OVERWRITTEN\n",
          "b.txt": "OVERWRITTEN\n",
          "meh/c.txt": "OVERWRITTEN\n"
        },
        "dst_prefill": {
          "a.txt": "SKIPPED\n",
          "b.txt": "SKIPPED\n",
          "meh/c.txt": "SKIPPED\n"
        },
        "skip_if_exists": [
          "b.txt",
          "meh/c.txt"
        ],
        "force": true,
        "data": {}
      },
      "expected_output": "produced=3\npath: a.txt\npath: b.txt\npath: meh/c.txt\nfile: a.txt -> \"OVERWRITTEN\\n\"\nfile: b.txt -> \"SKIPPED\\n\"\nfile: meh/c.txt -> \"SKIPPED\\n\"\n"
    },
    {
      "input": {
        "op": "render",
        "src": {
          "f.txt": "NEW\n"
        },
        "dst_prefill": {
          "f.txt": "OLD\n"
        },
        "skip": true,
        "data": {}
      },
      "expected_output": "produced=1\npath: f.txt\nfile: f.txt -> \"OLD\\n\"\n"
    },
    {
      "input": {
        "op": "render",
        "src": {
          "f.txt": "NEW\n"
        },
        "dst_prefill": {
          "f.txt": "OLD\n"
        },
        "force": true,
        "data": {}
      },
      "expected_output": "produced=1\npath: f.txt\nfile: f.txt -> \"NEW\\n\"\n"
    }
  ]
}
```

---

### Feature 4: Dry-Run Mode

**As a developer**, I want a dry-run mode that computes the full render but touches nothing on disk, so I can preview the effect of a template before committing to it.

**Expected Behavior / Usage:**

When dry-run mode is enabled, the engine performs the complete rendering computation (placeholder expansion, selection, overwrite resolution) but writes nothing to the destination. The destination therefore remains empty, and the output reports that zero files were produced (`produced=0`).

**Test Cases:** `rcb_tests/public_test_cases/feature4_pretend.json`

```json
{
  "description": "A dry-run mode that performs the full rendering computation but makes no changes to the destination. Output reports that nothing was produced.",
  "cases": [
    {
      "input": {
        "op": "render",
        "src": {
          "a.txt": "A\n",
          "sub/b.txt.tmpl": "Hi [[ who ]]\n"
        },
        "pretend": true,
        "data": {
          "who": "there"
        }
      },
      "expected_output": "produced=0\n"
    }
  ]
}
```

---

### Feature 5: External Template Resolution

**As a developer**, I want a template to be able to extend or include another template that lives outside the source tree, so I can share a common parent template across projects.

**Expected Behavior / Usage:**

A template file may reference another template (for example `[% extends "parent.txt" %]`). The engine resolves such references against the source tree plus any additional search paths supplied by the caller. If the referenced template is found in a search path, its content is used and the render succeeds normally. If the referenced template cannot be located in any search path, a template-reference error is reported as `error=[a specific template resolution error code]` followed by `[a specific template resolution error code]<reference>`. If a supplied additional search path does not itself exist, a configuration-data error is reported as `error=invalid_config_data` followed by `field=extra_paths reason=not_found`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_extra_paths.json`

```json
{
  "description": "Resolution of template references that live outside the source tree. Additional search paths may be supplied so that a template can extend or include a shared parent template found there. If a referenced parent template cannot be located in any search path, a template-reference error is reported. If a supplied additional search path does not exist, a configuration-data error is reported categorising the offending field as not found.",
  "cases": [
    {
      "input": {
        "op": "render",
        "src": {
          "child.txt.tmpl": "[% extends \"parent.txt\" %]\n"
        },
        "extra": {
          "parent.txt": "PARENT_CONTENT\n"
        },
        "data": {}
      },
      "expected_output": "produced=1\npath: child.txt\nfile: child.txt -> \"PARENT_CONTENT\\n\"\n"
    },
    {
      "input": {
        "op": "render",
        "src": {
          "child.txt.tmpl": "[% extends \"parent.txt\" %]\n"
        },
        "data": {}
      },
      "expected_output": "error=[a specific template resolution error code]\n[a specific template resolution error code]parent.txt\n"
    },
    {
      "input": {
        "op": "render",
        "src": {
          "child.txt.tmpl": "[% extends \"parent.txt\" %]\n"
        },
        "extra_missing": true,
        "data": {}
      },
      "expected_output": "error=invalid_config_data\nfield=extra_paths reason=not_found\n"
    }
  ]
}
```

---

### Feature 6: Configuration File Loading

**As a developer**, I want the engine to load an optional configuration file from the template, preserving each declared value's type, so the template can ship its own defaults and engine options.

**Expected Behavior / Usage:**

The engine looks for an optional configuration file in the source tree. Two kinds of keys are returned: engine-option keys (those carrying a leading-underscore marker, e.g. `_exclude`, `_include`, `_skip_if_exists`, `_tasks`) and answer-default keys (any other key). Each value preserves its declared type: text stays text, integers stay integers, booleans stay booleans, and sequences stay sequences. The output reports the number of keys (`keys=N`) followed by one `key=value` line per key in sorted key order, where the value is rendered as a JSON literal. A malformed configuration file is reported as `error=invalid_config_file`. Two configuration files present at once are reported as `error=[a specific configuration loading exception]`. When no configuration file is present, the result is `keys=0`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_config_loading.json`

```json
{
  "description": "Loading of the optional configuration file from the source tree. Engine-option keys (those carrying a leading-underscore marker) and answer-default keys are both returned, each preserving its native declared type: text stays text, integers stay integers, booleans stay booleans, and sequences stay sequences. A malformed configuration file is reported as an invalid-config-file error. Two configuration files present at once are reported as a multiple-config-files error. When no configuration file is present, no keys are returned.",
  "cases": [
    {
      "input": {
        "op": "read_config",
        "config_files": [
          {
            "name": "copier.yml",
            "content": "a_string: lorem ipsum\na_number: 12345\na_boolean: true\na_list:\n  - one\n  - two\n  - three\n"
          }
        ]
      },
      "expected_output": "keys=4\na_boolean=true\na_list=[\"one\", \"two\", \"three\"]\na_number=12345\na_string=\"lorem ipsum\"\n"
    },
    {
      "input": {
        "op": "read_config",
        "config_files": [
          {
            "name": "copier.yml",
            "content": "%343\n"
          }
        ]
      },
      "expected_output": "error=invalid_config_file\n"
    },
    {
      "input": {
        "op": "read_config",
        "config_files": [
          {
            "name": "copier.yml",
            "content": "\n"
          },
          {
            "name": "copier.yaml",
            "content": "\n"
          }
        ]
      },
      "expected_output": "error=[a specific configuration loading exception]\n"
    }
  ]
}
```

---

### Feature 7: Run-Mode Option Validation

**As a developer**, I want the engine's run-mode options to be strictly validated, so an obviously wrong combination is rejected early with a clear, structured reason.

**Expected Behavior / Usage:**

The run-mode option set is a small group of strict boolean toggles (dry-run, quiet, force-overwrite, preserve-everything, cleanup-on-error). A non-boolean value for any toggle is reported as a validation error on the offending field with reason `value`. The force-overwrite and preserve-everything modes are mutually exclusive; enabling both is reported as a validation error on the offending field with reason `mutually_exclusive`. Unknown extra keys are ignored. Valid input echoes `valid=true` followed by every resolved toggle as a `key=value` line in sorted key order.

**Test Cases:** `rcb_tests/public_test_cases/feature7_flags_validation.json`

```json
{
  "description": "Validation of the run-mode option set. Each mode is a strict boolean; a non-boolean value is reported as a validation error on the offending field. The overwrite-everything and preserve-everything modes are mutually exclusive and enabling both is reported as a mutual-exclusion error. Unknown extra keys are ignored. Valid input echoes the resolved mode values.",
  "cases": [
    {
      "input": {
        "op": "check_flags",
        "flags": {
          "pretend": true,
          "quiet": false,
          "force": true,
          "skip": false,
          "cleanup_on_error": true
        }
      },
      "expected_output": "valid=true\ncleanup_on_error=true\nforce=true\npretend=true\nquiet=false\nskip=false\n"
    },
    {
      "input": {
        "op": "check_flags",
        "flags": {
          "pretend": "not_a_bool"
        }
      },
      "expected_output": "error=invalid_flags\nfield=pretend reason=value\n"
    },
    {
      "input": {
        "op": "check_flags",
        "flags": {
          "force": true,
          "skip": true
        }
      },
      "expected_output": "error=invalid_flags\nfield=skip reason=mutually_exclusive\n"
    }
  ]
}
```

---

### Feature 8: Templating-Engine Option Validation

**As a developer**, I want the templating-engine options (the delimiters and toggles that define placeholder syntax) to be validated, so I can safely customise the placeholder syntax of a template.

**Expected Behavior / Usage:**

The templating-engine option set configures the placeholder and block delimiter strings (block start/end, variable start/end) and a couple of boolean toggles (autoescape, keep-trailing-newline). Boolean toggles must be strict booleans and delimiter strings must be text. A non-boolean toggle is reported as a validation error on the offending field with reason `value`; a non-text delimiter (e.g. null) is reported with reason `type`. Unknown extra keys are accepted and preserved. Valid input echoes `valid=true` followed by every resolved option as a `key=value` line in sorted key order, with values rendered as JSON literals.

**Test Cases:** `rcb_tests/public_test_cases/feature8_envops_validation.json`

```json
{
  "description": "Validation of the templating-engine option set that configures the placeholder and block delimiters and toggles. Boolean toggles must be strict booleans and delimiter strings must be text; violations are reported as a validation error on the offending field. Unknown extra keys are accepted and preserved. Valid input echoes the resolved option values.",
  "cases": [
    {
      "input": {
        "op": "check_envops",
        "envops": {
          "autoescape": true,
          "block_start_string": "<%",
          "block_end_string": "%>",
          "variable_start_string": "<<",
          "variable_end_string": ">>",
          "keep_trailing_newline": false,
          "extra_member": null
        }
      },
      "expected_output": "valid=true\nautoescape=true\nblock_end_string=\"%>\"\nblock_start_string=\"<%\"\nextra_member=null\nkeep_trailing_newline=false\nvariable_end_string=\">>\"\nvariable_start_string=\"<<\"\n"
    },
    {
      "input": {
        "op": "check_envops",
        "envops": {
          "autoescape": "not_a_bool"
        }
      },
      "expected_output": "error=invalid_envops\nfield=autoescape reason=value\n"
    },
    {
      "input": {
        "op": "check_envops",
        "envops": {
          "block_start_string": null
        }
      },
      "expected_output": "error=invalid_envops\nfield=block_start_string reason=type\n"
    }
  ]
}
```

---

### Feature 9: Configuration Data Validation

**As a developer**, I want the resolved configuration data to be validated before a render starts, so impossible runs (no source, missing paths) fail fast with structured reasons.

**Expected Behavior / Usage:**

The resolved configuration data carries the source and destination locations and the effective selection lists. The source and destination locations are mandatory; omitting either is reported as a missing-field error (`field=<name> reason=missing`), with the offending fields listed in sorted order. A source location (or additional search location) that does not exist on disk is reported as `field=src_path reason=not_found`. All such errors are categorised `error=invalid_config_data`. Valid input echoes `valid=true` followed by the requested resolved fields; the default `exclude` list is the built-in exclusion set, `include` defaults to empty, and the destination folder name is derived from the destination path.

**Test Cases:** `rcb_tests/public_test_cases/feature9_config_data_validation.json`

```json
{
  "description": "Validation of the resolved configuration data. The source and destination locations are mandatory; omitting them is reported as missing-field errors. A source location (or extra search location) that does not exist is reported as a not-found error. Valid input echoes requested resolved fields, including the destination folder name.",
  "cases": [
    {
      "input": {
        "op": "check_paths",
        "config": {},
        "report": []
      },
      "expected_output": "error=invalid_config_data\nfield=dst_path reason=missing\nfield=src_path reason=missing\n"
    },
    {
      "input": {
        "op": "check_paths",
        "config": {
          "src_path": "./i_do_not_exist",
          "dst_path": "@dst"
        },
        "report": []
      },
      "expected_output": "error=invalid_config_data\nfield=src_path reason=not_found\n"
    },
    {
      "input": {
        "op": "check_paths",
        "config": {
          "src_path": "@src_good",
          "dst_path": "@dst",
          "skip_if_exists": [
            "skip_me"
          ]
        },
        "report": [
          "exclude",
          "include",
          "skip_if_exists",
          "folder_name"
        ]
      },
      "expected_output": "valid=true\nexclude=[\"copier.yaml\", \"copier.yml\", \"~*\", \"*.py[co]\", \"__pycache__\", \"__pycache__/*\", \".git\", \".git/*\", \".DS_Store\", \".svn\"]\ninclude=[]\nskip_if_exists=[\"skip_me\"]\nfolder_[a specific template resolution error code]\"out_project\"\n"
    }
  ]
}
```

---

### Feature 10: Configuration Merge & Precedence

**As a developer**, I want configuration values to merge from multiple sources with a well-defined precedence, so an explicit call argument always beats a template default.

**Expected Behavior / Usage:**

The effective settings are merged from three sources, in decreasing precedence: explicit call arguments, then configuration-file answers, then built-in defaults. For the selection lists (`exclude`, `include`, `skip_if_exists`) and the task list (`tasks`), a value supplied as a call argument fully replaces the configuration-file value; when no argument is supplied, the configuration-file value is used; otherwise the built-in default applies. The destination folder name is derived from the destination path. The output echoes each requested resolved field as a `key=value` line in the requested order, with values rendered as JSON literals.

**Test Cases:** `rcb_tests/public_test_cases/feature10_config_merge.json`

```json
{
  "description": "Merging of configuration sources to build the effective settings. The order of precedence is explicit call arguments over configuration-file answers over built-in defaults. Output reports the resolved selection lists and the destination folder name.",
  "cases": [
    {
      "input": {
        "op": "build_config",
        "config_file": {
          "name": "copier.yml",
          "content": "_exclude:\n  - \"exclude1\"\n  - \"exclude2\"\n_include:\n  - \"include1\"\n  - \"include2\"\n_skip_if_exists:\n  - \"skip1\"\n  - \"skip2\"\n_tasks:\n  - \"touch 1\"\n  - \"touch 2\"\n"
        },
        "args": {},
        "report": [
          "exclude",
          "include",
          "skip_if_exists",
          "tasks",
          "folder_name"
        ]
      },
      "expected_output": "exclude=[\"exclude1\", \"exclude2\"]\ninclude=[\"include1\", \"include2\"]\nskip_if_exists=[\"skip1\", \"skip2\"]\ntasks=[\"touch 1\", \"touch 2\"]\nfolder_[a specific template resolution error code]\"out_project\"\n"
    },
    {
      "input": {
        "op": "build_config",
        "config_file": {
          "name": "copier.yml",
          "content": "_include:\n  - \"include1\"\n  - \"include2\"\n"
        },
        "args": {
          "include": [
            "aaa"
          ]
        },
        "report": [
          "include"
        ]
      },
      "expected_output": "include=[\"aaa\"]\n"
    },
    {
      "input": {
        "op": "build_config",
        "config_file": {
          "name": "copier.yml",
          "content": "_include:\n  - \"include1\"\n  - \"include2\"\n"
        },
        "args": {},
        "report": [
          "include"
        ]
      },
      "expected_output": "include=[\"include1\", \"include2\"]\n"
    }
  ]
}
```

---

### Feature 11: Per-Entry Action Report

**As a developer**, I want a per-entry action report while rendering, so I can see exactly what the engine created, left untouched, flagged as conflicting, overwrote, or preserved.

**Expected Behavior / Usage:**

While rendering (when not quiet), the engine emits one action per destination entry. A fresh destination yields a `create` action for every produced folder and file. Re-rendering over an existing destination yields an `identical` action for a file whose new content matches the old, and a `conflict` action for a file whose content changed; a conflicting file is then followed by a `force` action when overwriting is forced, or a `skip` action when preservation is requested. The output reports the number of action lines (`lines=N`) followed by the actions as `<action> <target>` lines, sorted by target then action.

**Test Cases:** `rcb_tests/public_test_cases/feature11_status_report.json`

```json
{
  "description": "The per-entry action report produced while rendering. A fresh destination yields create actions for every produced folder and file. Re-rendering over an existing destination yields an identical action for unchanged files and a conflict action for changed files, followed by a force action when overwriting is forced or a skip action when preserving is requested. Output lists the actions and their targets.",
  "cases": [
    {
      "input": {
        "op": "status",
        "src": {
          "a.txt": "A\n",
          "sub/b.txt": "B\n"
        },
        "quiet": false,
        "data": {}
      },
      "expected_output": "lines=3\ncreate a.txt\ncreate sub/\ncreate sub/b.txt\n"
    },
    {
      "input": {
        "op": "status",
        "src": {
          "keep.txt": "SAME\n",
          "change.txt": "NEW\n"
        },
        "dst_prefill": {
          "keep.txt": "SAME\n",
          "change.txt": "OLD\n"
        },
        "force": true,
        "quiet": false,
        "data": {}
      },
      "expected_output": "lines=3\nconflict change.txt\nforce change.txt\nidentical keep.txt\n"
    },
    {
      "input": {
        "op": "status",
        "src": {
          "keep.txt": "SAME\n",
          "change.txt": "NEW\n"
        },
        "dst_prefill": {
          "keep.txt": "SAME\n",
          "change.txt": "OLD\n"
        },
        "skip": true,
        "quiet": false,
        "data": {}
      },
      "expected_output": "lines=3\nconflict change.txt\nskip change.txt\nidentical keep.txt\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the rendering engine, entry selection, overwrite policy, configuration loading/validation/merging, and the per-entry action report. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint (a core package separated from the execution adapter), ensuring maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads one JSON command object from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-feature contracts above. All error normalization (translating typed core errors into the language-neutral `error=<category>` / structured-field lines) happens in this adapter layer; the core engine is never modified to satisfy the stdout contract. This adapter MUST be logically (and ideally physically) separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_render_engine.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_render_engine@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- sort by the same key used in the root_directory module
- output lines matching the pattern shown in the success_unit tests
