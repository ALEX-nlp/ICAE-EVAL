## Product Requirement Document

# Terminal Agent Workflow Manager - Task Board, Workspace, and Skill-Orchestration Behavior

## Project Goal

Build a terminal-native workflow manager that allows developers to coordinate agent-driven coding tasks across a kanban-style lifecycle, isolated version-controlled workspaces, configurable per-phase agents, and portable skill commands without manually wiring together prompts, branches, terminal panes, and workspace setup for every task.

---

## Background & Problem

Without this library/tool, developers are forced to manually choose agents, remember phase-specific prompts, create and clean up isolated workspaces, copy configuration files, inspect terminal output, and keep task state synchronized with version-control branches. This leads to repetitive setup, fragile command conventions, stale terminal views, and inconsistent handling of agent-specific workflow features.

With this library/tool, task records, board navigation, workspace lifecycle, terminal capture, and agent skill discovery are represented through stable behavior that can be tested as black-box input and output contracts.

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

### Feature 1: Agent Selection Input

**As a developer**, I want to choose an automation agent from a numbered prompt, so I can start the requested worker without ambiguous selection handling.

**Expected Behavior / Usage:**

The input is an object with raw selection text and the count of available agents. Blank input selects the first agent, valid one-based numbers select the matching zero-based index, and invalid text or out-of-range numbers report no selected index.

**Test Cases:** `rcb_tests/public_test_cases/feature1_agent_selection.json`

```json
{
    "description": "Interpret a user selection from a numbered list of available automation agents.",
    "cases": [
        {
            "input": {
                "selection_text": " 2 ",
                "agent_count": 3
            },
            "expected_output": "selection=valid\nselected_index=1\ndisplay_number=2\n"
        }
    ]
}
```

---

### Feature 2: Theme Color Parsing

**As a developer**, I want to accept user-supplied theme colors, so I can render configured colors consistently.

**Expected Behavior / Usage:**

The input is a color string. Six hexadecimal digits are valid with or without a leading hash and output separate red, green, and blue channels. Invalid length or non-hexadecimal characters output an invalid color result.

**Test Cases:** `rcb_tests/public_test_cases/feature2_color_parsing.json`

```json
{
    "description": "Parse six-digit hexadecimal color text into RGB channel values.",
    "cases": [
        {
            "input": {
                "color_text": "#5cfff7"
            },
            "expected_output": "color=valid\nred=92\ngreen=255\nblue=247\n"
        }
    ]
}
```

---

### Feature 3: First-Run State Decision

**As a developer**, I want to map persisted setup state to one startup action, so I can handle new, migrated, and existing users predictably.

**Expected Behavior / Usage:**

The input contains booleans for existing configuration, migrated settings, and prior data. Existing configuration has highest priority, followed by migration, existing data, and finally new-user prompting.

**Test Cases:** `rcb_tests/public_test_cases/feature3_first_run_action.json`

```json
{
    "description": "Choose the first-start action from existing configuration, migration, and data-store signals.",
    "cases": [
        {
            "input": {
                "config_exists": false,
                "migrated": false,
                "database_exists": true
            },
            "expected_output": "action=existing_user_save_defaults\n"
        }
    ]
}
```

---

### Feature 4: Configuration Merge and Phase Agent Resolution

**As a developer**, I want to combine global and project settings, so I can use the right defaults and phase-specific worker choices.

**Expected Behavior / Usage:**

The input contains global settings, project settings, and queried phases. Project defaults override global defaults, project phase agents override global phase agents, unset phases fall back to the merged default, and explicit phase output is `none` when no phase override exists.

**Test Cases:** `rcb_tests/public_test_cases/feature4_config_merge_and_phase_agents.json`

```json
{
    "description": "Merge global and project settings and resolve per-phase agents.",
    "cases": [
        {
            "input": {
                "global_settings": {
                    "default_agent": "claude",
                    "base_branch": "main",
                    "phase_agents": {
                        "running": "codex"
                    }
                },
                "project_settings": {
                    "default_agent": "opencode",
                    "base_branch": "develop",
                    "phase_agents": {
                        "running": "gemini"
                    },
                    "copy_files": ".env",
                    "init_script": "npm install"
                },
                "phase_queries": [
                    "planning",
                    "running"
                ]
            },
            "expected_output": "default_agent=opencode\nbase_branch=develop\ncopy_files=.env\ninit_script=npm install\nphase:planning=opencode\n[a specific magic string sentinel for disabled phases]\nphase:running=gemini\nexplicit:running=gemini\n"
        }
    ]
}
```

---

### Feature 5: Workflow Status Vocabulary

**As a developer**, I want to use a stable workflow status vocabulary, so I can serialize and parse board columns reliably.

**Expected Behavior / Usage:**

The input contains status text values to parse. Output begins with the canonical ordered workflow columns and then reports each supplied value as canonical or invalid.

**Test Cases:** `rcb_tests/public_test_cases/feature5_status_vocabulary.json`

```json
{
    "description": "Expose the canonical board workflow statuses and parse status text.",
    "cases": [
        {
            "input": {
                "status_texts": [
                    "backlog",
                    "planning",
                    "invalid"
                ]
            },
            "expected_output": "columns=backlog,planning,running,review,done\nparse:backlog=backlog\nparse:planning=planning\nparse:invalid=invalid\n"
        }
    ]
}
```

---

### Feature 6: Task and Project Record Defaults

**As a developer**, I want to create task and project records from user-provided text, so I can start with predictable identifiers, workflow status, and unset optional metadata.

**Expected Behavior / Usage:**

The input supplies task and project fields. Output confirms generated identifiers, echoes supplied fields, sets new tasks to backlog, and reports optional metadata as none.

**Test Cases:** `rcb_tests/public_test_cases/feature6_task_and_project_defaults.json`

```json
{
    "description": "Create a task and a project record with supplied names and default optional fields unset.",
    "cases": [
        {
            "input": {
                "task_title": "Test Task",
                "agent_name": "claude",
                "project_id": "project-123",
                "project_name": "myproject",
                "project_path": "/path/to/project"
            },
            "expected_output": "task_id_present=true\ntask_title=Test Task\ntask_agent=claude\ntask_project_id=project-123\ntask_status=backlog\ntask_description=none\nproject_id_present=true\nproject_name=myproject\nproject_path=/path/to/project\nproject_remote=none\n"
        }
    ]
}
```

---

### Feature 7: Board Column Grouping and Navigation

**As a developer**, I want to group tasks by workflow column and move the current selection, so I can drive a keyboard-oriented task board without selecting nonexistent rows.

**Expected Behavior / Usage:**

The input contains tasks, selected coordinates, and directional moves. Output lists task titles by column and the final selected task, clamping rows when moving into shorter columns.

**Test Cases:** `rcb_tests/public_test_cases/feature7_board_columns_and_navigation.json`

```json
{
    "description": "Group tasks by workflow column and update the selected task as directional navigation is applied.",
    "cases": [
        {
            "input": {
                "board_tasks": [
                    {
                        "title": "Task 1",
                        "status": "backlog"
                    },
                    {
                        "title": "Task 2",
                        "status": "backlog"
                    },
                    {
                        "title": "Task 3",
                        "status": "running"
                    }
                ],
                "selected_column": 0,
                "selected_row": 1,
                "moves": []
            },
            "expected_output": "selected_column=0\nselected_row=1\ncolumn:0:backlog=Task 1|Task 2\ncolumn:1:planning=empty\ncolumn:2:running=Task 3\ncolumn:3:review=empty\ncolumn:4:done=empty\nselected_task=Task 2\nselected_status=backlog\n"
        }
    ]
}
```

---

### Feature 8: Task Workspace Path Resolution

**As a developer**, I want to derive an isolated workspace path for a task, so I can keep task-specific files under the project workspace area.

**Expected Behavior / Usage:**

The input supplies a project path and task slug. Output is the deterministic hidden worktree path beneath the project.

**Test Cases:** `rcb_tests/public_test_cases/feature8_worktree_path.json`

```json
{
    "description": "Resolve the filesystem location reserved for an isolated task workspace inside a project.",
    "cases": [
        {
            "input": {
                "project_path": "/home/user/project",
                "task_slug": "task-123"
            },
            "expected_output": "worktree_path=/home/user/project/.agtx/worktrees/task-123\n"
        }
    ]
}
```

---

### Feature 9: Version-Controlled Workspace Lifecycle

**As a developer**, I want to create and clean up isolated task workspaces in a real repository, so I can run coding tasks on separate branches without disturbing the main checkout.

**Expected Behavior / Usage:**

The input describes a temporary repository branch, workspace slugs, and cleanup. Output includes repository signals, created relative paths, existence after creation, and optional existence after removal.

**Test Cases:** `rcb_tests/public_test_cases/feature9_git_worktree_lifecycle.json`

```json
{
    "description": "Create, detect, and remove isolated workspaces in a real version-controlled project.",
    "cases": [
        {
            "input": {
                "repository_setup": {
                    "initial_branch": "main"
                },
                "worktree_slugs": [
                    "test-task"
                ],
                "remove_after_creation": true
            },
            "expected_output": "is_git_repo=true\ncurrent_branch=main\ncreated:test-task=.agtx/worktrees/test-task\nexists:test-task=true\nexists_after_remove:test-task=false\n"
        }
    ]
}
```

---

### Feature 10: Workspace Initialization

**As a developer**, I want to copy configured files and run setup commands in a new workspace, so I can prepare task workspaces with project-specific context before work starts.

**Expected Behavior / Usage:**

The input describes project files, paths to copy, an optional setup command, and paths to verify. Output reports warnings, path presence, and copied file contents.

**Test Cases:** `rcb_tests/public_test_cases/feature10_worktree_initialization.json`

```json
{
    "description": "Initialize an isolated workspace by copying configured files and running an optional setup command.",
    "cases": [
        {
            "input": {
                "worktree_initialization": {
                    "project_files": {
                        ".env": "KEY=value"
                    },
                    "copy_files": ".env",
                    "init_script": "cat .env > verified.txt",
                    "check_paths": [
                        ".env",
                        "verified.txt"
                    ]
                }
            },
            "expected_output": "warning_count=0\npath:.env=present\ncontent:.env=KEY=value\npath:verified.txt=present\ncontent:verified.txt=KEY=value\n"
        }
    ]
}
```

---

### Feature 11: Terminal Popup Visible Window

**As a developer**, I want to compute the visible line slice for a scrollable terminal popup, so I can show current output or history consistently as users scroll.

**Expected Behavior / Usage:**

The input contains terminal lines, visible height, and scroll offset. Output reports start line, total effective lines, visible count, and visible line text.

**Test Cases:** `rcb_tests/public_test_cases/feature11_shell_popup_visible_window.json`

```json
{
    "description": "Compute the visible slice of captured terminal lines for a scrollable popup.",
    "cases": [
        {
            "input": {
                "popup_lines": [
                    "line 0",
                    "line 1",
                    "line 2"
                ],
                "visible_height": 10,
                "scroll_offset": 0
            },
            "expected_output": "start_line=0\ntotal_lines=3\nvisible_count=3\nvisible:0=line 0\nvisible:1=line 1\nvisible:2=line 2\n"
        }
    ]
}
```

---

### Feature 12: Terminal Capture Trimming

**As a developer**, I want to remove unused blank buffer space from captured terminal content, so I can avoid displaying stale empty pane area while preserving real content.

**Expected Behavior / Usage:**

The input contains captured terminal lines and optional cursor information. Output lists the retained line count and retained line text after trimming excessive blank buffer space.

**Test Cases:** `rcb_tests/public_test_cases/feature12_shell_capture_trimming.json`

```json
{
    "description": "Trim captured terminal content to remove unused blank buffer space while preserving real content.",
    "cases": [
        {
            "input": {
                "captured_lines": [
                    "line 1",
                    "line 2",
                    "",
                    "",
                    "",
                    ""
                ]
            },
            "expected_output": "line_count=4\nline:0=line 1\nline:1=line 2\nline:2=\nline:3=\n"
        }
    ]
}
```

---

### Feature 13: Agent Skill Mapping

**As a developer**, I want to map workflow skill identifiers to agent-specific command conventions, so I can install and invoke the same workflow on multiple agent CLIs.

**Expected Behavior / Usage:**

The input supplies an agent name and skill directory. Output reports native command location, file name, invocation syntax when supported, and fallback reference text.

**Test Cases:** `rcb_tests/public_test_cases/feature13_skill_mapping.json`

```json
{
    "description": "Map phase skill names to each agent family command discovery and invocation conventions.",
    "cases": [
        {
            "input": {
                "agent_name": "claude",
                "skill_directory": "agtx-plan",
                "phase": "planning"
            },
            "expected_output": "native_dir=.claude/commands|agtx\nfilename=plan.md\ninvocation=/agtx:plan\nreference=\n"
        }
    ]
}
```

---

### Feature 14: Plugin Command Transformation

**As a developer**, I want to translate canonical plugin commands into agent-specific interactive syntax, so I can reuse plugin workflows across different agent command syntaxes.

**Expected Behavior / Usage:**

The input contains a canonical command and agent name. Output is the command transformed for the target agent or none when unsupported.

**Test Cases:** `rcb_tests/public_test_cases/feature14_plugin_command_transform.json`

```json
{
    "description": "Transform canonical workflow plugin commands into agent-specific interactive command syntax.",
    "cases": [
        {
            "input": {
                "canonical_command": "/gsd:plan-phase 1",
                "agent_name": "opencode"
            },
            "expected_output": "transformed=/gsd-plan-phase 1\n"
        }
    ]
}
```

---

### Feature 15: Agent-Native Skill Discovery

**As a developer**, I want to scan command files installed for an agent, so I can show available workflow commands with human-readable descriptions.

**Expected Behavior / Usage:**

The input names an agent and provides command files. Output reports the discovered invocation strings and descriptions.

**Test Cases:** `rcb_tests/public_test_cases/feature15_skill_discovery_scan.json`

```json
{
    "description": "Scan agent-native command directories and list discovered invocation strings with descriptions.",
    "cases": [
        {
            "input": {
                "scan_agent": "claude",
                "command_files": {
                    ".claude/commands/agtx/plan.md": "---\nname: agtx-plan\ndescription: Plan a task implementation\n---\nBody\n"
                }
            },
            "expected_output": "skill_count=1\nskill=/agtx:plan | Plan a task implementation\n"
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
- follow the row clamping logic used in column resizing handlers
- use the syntax mechanism reserved for manual phase overrides
