## Product Requirement Document

# Portable Shell-Command Runner — A Cross-Platform CLI Wrapper for Common Shell Utilities

## Project Goal

Build a single command-line program that exposes a curated set of common shell utilities (copy, remove, list, test, print working directory, echo, stream-substitute, pattern-search, change permissions, and more) behind one uniform front end, so developers can run the same portable commands on any operating system without depending on a platform-specific shell.

---

## Background & Problem

Build scripts and developer tooling frequently need to run small shell utilities, but the available utilities and their flags differ across platforms, and writing portable scripts by hand is tedious and error-prone. Without a unified runner, every project reinvents fragile shims around platform shells.

With this runner, a developer invokes one program with a command name and its arguments; the program validates the request, routes it to the matching utility, runs it, and reports results through a uniform contract: standard output for produced text, a non-zero exit status for failures, and clearly categorized errors for misuse. The runner also adds a few cross-cutting conveniences: a global flag to silence diagnostics, automatic consumption of piped input for the commands that accept it, an extensibility hook that loads optional plugins named in a working-directory configuration file, and a compatibility shim that lets stream-substitution use familiar `s/<pattern>/<replacement>/` syntax.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain. This runner has several distinct responsibilities (argument parsing, command routing and validation, the substitution-syntax shim, optional plugin loading, result formatting). It MUST NOT be a single "god file"; output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository. Do not over-engineer, but strictly avoid monolithic files.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core command-routing logic must remain completely decoupled from standard I/O and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls to the core.

3. **Adherence to SOLID Design Principles:** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units (SRP); keep the routing engine open for new commands but closed for modification (OCP); model commands behind a uniform abstraction so they are interchangeable (LSP, ISP); and have high-level routing depend on abstractions rather than concrete I/O (DIP).

4. **Robustness & Interface Design:** The public interface must be elegant and idiomatic to the target language. The system must handle edge cases gracefully and model errors properly (specific error types or a Result pattern) rather than relying on generic faults.

---

## Core Features

### Feature 1: Run A Named Command And Capture Its Output

**As a developer**, I want to invoke a named utility with arguments and receive its produced text, so I can use portable commands uniformly.

**Expected Behavior / Usage:**

The adapter reads one request describing a command line (`args`: the command name followed by its operands) and optional simulated piped input (`stdin`). It runs the command and renders, on standard output, the exit status as `exit_code=<n>`, then `stdout=<json-encoded text>`, then `stderr=<json-encoded text>`. Both text fields are JSON string literals so that newlines and special characters are represented unambiguously. The line-printing command joins its operands with single spaces and appends one trailing newline; with no operands it still emits a single newline. A successful run reports exit status zero.

**Test Cases:** `rcb_tests/public_test_cases/feature1_echo.json`

```json
{
    "description": "Run the line-printing command, which writes its space-joined operands followed by a single trailing newline to standard output and exits successfully. With no operands it still emits one newline.",
    "cases": [
        {"input": {"args": ["echo"]}, "expected_output": "exit_code=0\nstdout=\"\\n\"\nstderr=\"\"\n"},
        {"input": {"args": ["echo", "hello", "world"]}, "expected_output": "exit_code=0\nstdout=\"hello world\\n\"\nstderr=\"\"\n"}
    ]
}
```

---

### Feature 2: Side-Effecting Commands With No Textual Output

**As a developer**, I want filesystem-mutating commands to run quietly, so a successful operation is signalled by its effect and a zero exit status rather than by chatter.

**Expected Behavior / Usage:**

A request may pre-populate the working directory via `files` (a map of path → content; a value may also be an object `{content, mode}` to set octal permission bits) and `dirs` (empty directories to create), and may request post-run inspection via `show_files` (render each file's contents as `file:<path>=<json text>`, or `file:<path>=null` when the file is absent). Commands that copy or remove files produce no standard output and no standard error and exit successfully; the effect is observable through the post-run file state — the copy destination now holds the source content, and a removed file is reported as absent.

**Test Cases:** `rcb_tests/public_test_cases/feature2_side_effect_no_output.json`

```json
{
    "description": "Commands that perform a filesystem side effect but yield no textual result write nothing to standard output or standard error and exit successfully; the effect is observable in the resulting filesystem state. Demonstrated by copying an existing file to a new name and by removing an existing file.",
    "cases": [
        {"input": {"args": ["cp", "a.txt", "b.txt"], "files": {"a.txt": "hello\n"}, "show_files": ["b.txt"]}, "expected_output": "exit_code=0\nstdout=\"\"\nstderr=\"\"\nfile:b.txt=\"hello\\n\"\n"},
        {"input": {"args": ["rm", "a.txt"], "files": {"a.txt": "x"}, "show_files": ["a.txt"]}, "expected_output": "exit_code=0\nstdout=\"\"\nstderr=\"\"\nfile:a.txt=null\n"}
    ]
}
```

---

### Feature 3: Usage And Routing Errors

**As a developer**, I want misuse of the runner itself to fail fast with a clear, categorized error and a dedicated status code, so mistakes are unambiguous and scriptable.

**Expected Behavior / Usage:**

When the request is malformed at the routing layer the run is rejected with the dedicated usage-error exit status `27` and a neutral `error=<category>` line (and, where relevant, the offending token). These usage errors are distinct from a command that ran but failed (Feature 5). Three categories exist.

*3.1 Missing command name — no command was supplied.*

When no command name is present, the runner reports `error=missing_command` with exit status `27`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_missing_command.json`

```json
{
    "description": "Invoking the runner with no command name reports a missing-command usage error and exits with the dedicated usage-error status.",
    "cases": [
        {"input": {"args": []}, "expected_output": "exit_code=27\nerror=missing_command\n"}
    ]
}
```

*3.2 Unknown command name — the requested command is not recognized.*

When the command name is not a known command, the runner reports `error=unknown_command` and echoes the offending token as `command=<json name>`, with exit status `27`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_unknown_command.json`

```json
{
    "description": "Requesting a command name that is not recognized reports an unknown-command error naming the offending token and exits with the usage-error status.",
    "cases": [
        {"input": {"args": ["foobar"]}, "expected_output": "exit_code=27\nerror=unknown_command\ncommand=\"foobar\"\n"}
    ]
}
```

*3.3 Unsupported command name — a known-but-disallowed command was requested.*

A set of command names is explicitly unsupported (for example, ones that would change the runner's own process state). Requesting one reports `error=unsupported_command` with the name as `command=<json name>` and exit status `27`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_unsupported_command.json`

```json
{
    "description": "Some command names are explicitly unsupported by the runner; requesting one reports an unsupported-command error naming it and exits with the usage-error status.",
    "cases": [
        {"input": {"args": ["cd", "src"]}, "expected_output": "exit_code=27\nerror=unsupported_command\ncommand=\"cd\"\n"}
    ]
}
```

---

### Feature 4: Forwarding A Command's Own Failure

**As a developer**, I want a command that runs but fails to surface its real exit status and diagnostic, so I can detect and diagnose runtime failures distinctly from misuse of the runner.

**Expected Behavior / Usage:**

When a routed command executes but fails (for example, listing a path that does not exist), the runner forwards the command's own non-zero exit status (not the usage status `27`) and renders the command's diagnostic message on `stderr`. The diagnostic is the utility's own message and appears in the JSON-encoded `stderr` field.

**Test Cases:** `rcb_tests/public_test_cases/feature6_command_failure.json`

```json
{
    "description": "When the underlying command fails (for example, listing a path that does not exist) the runner forwards the command's own non-zero exit status together with its diagnostic message on standard error.",
    "cases": [
        {"input": {"args": ["ls", "fakeFileName"]}, "expected_output": "exit_code=2\nstdout=\"\"\nstderr=\"ls: no such file or directory: fakeFileName\\n\"\n"}
    ]
}
```

---

### Feature 5: Silent Mode

**As a developer**, I want a global flag that suppresses diagnostic output while preserving the exit status, so failures stay scriptable without noise.

**Expected Behavior / Usage:**

A global silent flag (`--silent`) prefixed before the command suppresses the failing command's diagnostic message: the run still forwards the same non-zero exit status, but `stderr` is empty. Without the flag, the identical failing command prints its diagnostic on `stderr`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_silent_mode.json`

```json
{
    "description": "A global silent flag suppresses diagnostic output: a failing command still returns its non-zero exit status, but its error message is withheld from standard error. Without the flag the same failure prints its message.",
    "cases": [
        {"input": {"args": ["--silent", "ls", "fakeFileName"]}, "expected_output": "exit_code=2\nstdout=\"\"\nstderr=\"\"\n"},
        {"input": {"args": ["ls", "fakeFileName"]}, "expected_output": "exit_code=2\nstdout=\"\"\nstderr=\"ls: no such file or directory: fakeFileName\\n\"\n"}
    ]
}
```

---

### Feature 6: Boolean-Condition Commands

**As a developer**, I want commands that answer a yes/no question to be silent and convey the answer purely through the exit status, so conditions compose cleanly in scripts.

**Expected Behavior / Usage:**

Commands whose result is a boolean condition print nothing on either stream; the answer is the exit status — zero when the condition holds, one when it does not. Demonstrated with a file-type test that succeeds for an existing regular file and fails for a path that is not a symbolic link.

**Test Cases:** `rcb_tests/public_test_cases/feature8_boolean_commands.json`

```json
{
    "description": "Commands whose result is a boolean condition print nothing; the outcome is conveyed solely through the exit status (zero when the condition holds, one when it does not). Demonstrated with a file-type test against an existing regular file and against a path that is not a symbolic link.",
    "cases": [
        {"input": {"args": ["test", "-f", "README.md"], "files": {"README.md": "x"}}, "expected_output": "exit_code=0\nstdout=\"\"\nstderr=\"\"\n"},
        {"input": {"args": ["test", "-L", "somedir"], "dirs": ["somedir"]}, "expected_output": "exit_code=1\nstdout=\"\"\nstderr=\"\"\n"}
    ]
}
```

---

### Feature 7: Built-In True And False Commands

**As a developer**, I want always-available commands that unconditionally succeed or fail with no output, so I have portable primitives for control flow.

**Expected Behavior / Usage:**

Two always-available commands report a fixed condition and produce no output: one always exits zero, the other always exits one. These are available without any configuration.

**Test Cases:** `rcb_tests/public_test_cases/feature11_true_false.json`

```json
{
    "description": "Two always-available commands report a fixed condition with no output: one always exits zero, the other always exits one.",
    "cases": [
        {"input": {"args": ["true"]}, "expected_output": "exit_code=0\nstdout=\"\"\nstderr=\"\"\n"},
        {"input": {"args": ["false"]}, "expected_output": "exit_code=1\nstdout=\"\"\nstderr=\"\"\n"}
    ]
}
```

---

### Feature 8: Print Working Directory With Trailing Newline

**As a developer**, I want the working-directory command to emit a newline-terminated path, so its output is easy to consume line-by-line.

**Expected Behavior / Usage:**

The working-directory command prints the absolute path of the current directory followed by a trailing newline. The concrete absolute path is environment-specific; in the contract it is shown as the placeholder token `<cwd>`, and the salient, implementation-independent property is the trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature9_pwd_newline.json`

```json
{
    "description": "The working-directory command prints the absolute path of the current directory followed by a trailing newline (the concrete path is shown here as a placeholder token).",
    "cases": [
        {"input": {"args": ["pwd"]}, "expected_output": "exit_code=0\nstdout=\"<cwd>\\n\"\nstderr=\"\"\n"}
    ]
}
```

---

### Feature 9: Consuming Piped Input

**As a developer**, I want commands that accept standard input to read piped content, so I can compose the runner into pipelines.

**Expected Behavior / Usage:**

When piped input is supplied (the `stdin` field of the request), line-oriented commands consume it as their input. Demonstrated by filtering piped lines for those containing a literal substring; only matching lines are printed, each terminated by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature10_stdin_pipe.json`

```json
{
    "description": "When input is supplied on the pipe, line-filtering commands consume it as their input. Demonstrated by filtering piped lines for those containing a literal substring.",
    "cases": [
        {"input": {"args": ["grep", "foo"], "stdin": "foo\nbar\nfoobar"}, "expected_output": "exit_code=0\nstdout=\"foo\\nfoobar\\n\"\nstderr=\"\"\n"}
    ]
}
```

---

### Feature 10: Stream Substitution With `s/<pattern>/<replacement>/` Syntax

**As a developer**, I want familiar substitution-expression syntax for stream editing, so I can transform text portably.

**Expected Behavior / Usage:**

A stream-substitution command accepts an expression of the form `s/<pattern>/<replacement>/` (optionally with a trailing `g` for global) followed by one file path; the transformed text is written to standard output. A global in-place flag (`-i`) additionally writes the result back to the source file.

*10.1 Basic substitution — first match per line, source preserved.*

Without a global suffix, only the first match on each line is replaced. The source file is left unchanged (verified via `show_files`).

**Test Cases:** `rcb_tests/public_test_cases/feature12_1_sed_basic.json`

```json
{
    "description": "Stream substitution accepts an expression of the form s/<pattern>/<replacement>/ followed by a file path. By default it replaces only the first match on each line, prints the transformed text to standard output, and leaves the source file unchanged.",
    "cases": [
        {"input": {"args": ["sed", "s/foo/bar/", "foo.txt"], "files": {"foo.txt": "foo\nfoosomething\nfoofoosomething\n"}, "show_files": ["foo.txt"]}, "expected_output": "exit_code=0\nstdout=\"bar\\nbarsomething\\nbarfoosomething\\n\"\nstderr=\"\"\nfile:foo.txt=\"foo\\nfoosomething\\nfoofoosomething\\n\"\n"}
    ]
}
```

*10.2 Global and in-place — every match replaced and written back.*

With the global suffix, every match on each line is replaced; with the in-place flag, the transformed text is also written back to the source file (verified via `show_files`).

**Test Cases:** `rcb_tests/public_test_cases/feature12_2_sed_global_inplace.json`

```json
{
    "description": "With the global suffix on the expression, every match on each line is replaced. With the in-place flag, the transformed text is additionally written back to the source file.",
    "cases": [
        {"input": {"args": ["sed", "-i", "s/foo/bar/g", "foo.txt"], "files": {"foo.txt": "foo\nfoosomething\nfoofoosomething\n"}, "show_files": ["foo.txt"]}, "expected_output": "exit_code=0\nstdout=\"bar\\nbarsomething\\nbarbarsomething\\n\"\nstderr=\"\"\nfile:foo.txt=\"bar\\nbarsomething\\nbarbarsomething\\n\"\n"}
    ]
}
```

*10.3 Escaped forward slashes — literal slashes in pattern/replacement.*

Forward slashes inside the pattern or replacement may be escaped with a backslash so they are treated literally rather than as field delimiters.

**Test Cases:** `rcb_tests/public_test_cases/feature12_3_sed_escaped_slashes.json`

```json
{
    "description": "Forward slashes inside the pattern or replacement may be escaped with a backslash so they are treated literally rather than as field delimiters.",
    "cases": [
        {"input": {"args": ["sed", "s/http:\\/\\/www\\.google\\.com/https:\\/\\/www\\.facebook\\.com/", "urls.txt"], "files": {"urls.txt": "http://www.nochange.com\nhttp://www.google.com\n"}}, "expected_output": "exit_code=0\nstdout=\"http://www.nochange.com\\nhttps://www.facebook.com\\n\"\nstderr=\"\"\n"}
    ]
}
```

*10.4 Escaped backslashes — convert backslashes to forward slashes.*

An escaped backslash in the pattern matches a literal backslash, enabling conversion of every backslash to a forward slash across the input.

**Test Cases:** `rcb_tests/public_test_cases/feature12_4_sed_backslash_to_slash.json`

```json
{
    "description": "An escaped backslash in the pattern matches a literal backslash, enabling conversion of every backslash to a forward slash across the input.",
    "cases": [
        {"input": {"args": ["sed", "s/\\\\/\\//g", "win.txt"], "files": {"win.txt": "C:\\Some\\Windows\\file\\path.txt"}}, "expected_output": "exit_code=0\nstdout=\"C:/Some/Windows/file/path.txt\"\nstderr=\"\"\n"}
    ]
}
```

*10.5 Empty replacement — delete matched text.*

An empty replacement deletes matched text. With the global suffix every match on a line is removed; without it only the first match on each line is removed.

**Test Cases:** `rcb_tests/public_test_cases/feature12_5_sed_empty_replacement.json`

```json
{
    "description": "An empty replacement deletes matched text. With the global suffix every match on a line is removed; without it only the first match on each line is removed.",
    "cases": [
        {"input": {"args": ["sed", "s/foo//g", "foo.txt"], "files": {"foo.txt": "foo\nfoosomething\nfoofoosomething\n"}}, "expected_output": "exit_code=0\nstdout=\"\\nsomething\\nsomething\\n\"\nstderr=\"\"\n"},
        {"input": {"args": ["sed", "s/foo//", "foo.txt"], "files": {"foo.txt": "foo\nfoosomething\nfoofoosomething\n"}}, "expected_output": "exit_code=0\nstdout=\"\\nsomething\\nfoosomething\\n\"\nstderr=\"\"\n"}
    ]
}
```

*10.6 Empty pattern — rejected.*

An empty search pattern is rejected: the runner raises an error (rendered as `error=empty_pattern`) rather than performing an unbounded substitution.

**Test Cases:** `rcb_tests/public_test_cases/feature12_6_sed_empty_pattern.json`

```json
{
    "description": "An empty search pattern is rejected: the runner raises an error rather than performing an unbounded substitution.",
    "cases": [
        {"input": {"args": ["sed", "s//foo/g", "foo.txt"], "files": {"foo.txt": "foo\nfoosomething\nfoofoosomething\n"}}, "expected_output": "error=empty_pattern\n"}
    ]
}
```

*10.7 Expression vs. file disambiguation — only the first looks-like-an-expression operand is one.*

Only the first operand that looks like a substitution expression is treated as one; a later operand that merely resembles such an expression is treated as an ordinary file path.

**Test Cases:** `rcb_tests/public_test_cases/feature12_7_sed_filename_like_expression.json`

```json
{
    "description": "Only the first operand that looks like a substitution expression is treated as one; a later operand that merely resembles such an expression is treated as an ordinary file path.",
    "cases": [
        {"input": {"args": ["sed", "s/foo/bar/", "s/weirdfile"], "files": {"s/weirdfile": "foo\nfoosomething\nfoofoosomething\n"}}, "expected_output": "exit_code=0\nstdout=\"bar\\nbarsomething\\nbarfoosomething\\n\"\nstderr=\"\"\n"}
    ]
}
```

---

### Feature 11: Pattern Search Over A File

**As a developer**, I want to print lines of a file matching a regular expression, so I can search content portably.

**Expected Behavior / Usage:**

Pattern search over a file prints every line that matches the given regular expression, each terminated by a newline; non-matching lines are omitted.

**Test Cases:** `rcb_tests/public_test_cases/feature13_grep_regex.json`

```json
{
    "description": "Pattern search over a file prints every line that matches the given regular expression.",
    "cases": [
        {"input": {"args": ["grep", "fo*", "file.txt"], "files": {"file.txt": "1st line\nfoo\nf\ndoes not match\nsomething foo\n"}}, "expected_output": "exit_code=0\nstdout=\"foo\\nf\\nsomething foo\\n\"\nstderr=\"\"\n"}
    ]
}
```

---

### Feature 12: Change File Permissions (Octal And Symbolic)

**As a developer**, I want to change file permissions with either an absolute octal mode or a symbolic expression, so I can manage permissions portably.

**Expected Behavior / Usage:**

The permission-change command accepts both absolute octal modes and symbolic mode expressions. An absolute octal mode (e.g. `644`, `755`) sets the permission bits directly. A symbolic expression adjusts the existing bits — `+x` adds execute for all classes, and a class prefix such as `u+x` restricts the adjustment to the owner. The resulting permission bits are observable via `show_modes`, rendered as a three-digit octal value `mode:<path>=<octal>`. (A file's starting permission bits can be set through the object form of a `files` entry.)

**Test Cases:** `rcb_tests/public_test_cases/feature14_chmod_modes.json`

```json
{
    "description": "Changing file permissions accepts both absolute octal modes and symbolic mode expressions. An absolute octal mode sets the permission bits directly; a symbolic expression adjusts the existing bits, optionally restricted to a class such as the owner. The resulting permission bits are shown as a three-digit octal value.",
    "cases": [
        {"input": {"args": ["chmod", "644", "f.txt"], "files": {"f.txt": "x"}, "show_modes": ["f.txt"]}, "expected_output": "exit_code=0\nstdout=\"\"\nstderr=\"\"\nmode:f.txt=644\n"},
        {"input": {"args": ["chmod", "+x", "f.txt"], "files": {"f.txt": {"content": "x", "mode": "644"}}, "show_modes": ["f.txt"]}, "expected_output": "exit_code=0\nstdout=\"\"\nstderr=\"\"\nmode:f.txt=755\n"}
    ]
}
```

---

### Feature 13: Loading Optional Plugins From A Configuration File

**As a developer**, I want optional commands to be loadable from a working-directory configuration file, so I can extend the runner without modifying it.

**Expected Behavior / Usage:**

A configuration file named in the working directory may list plugins to load before routing. Two failure modes are categorized as neutral errors. The configuration content is supplied through a neutral `config` field on the request (the runner persists it under its own configuration-file name).

*13.1 Missing plugin — a listed plugin cannot be found.*

If a listed plugin cannot be resolved, the runner raises a plugin-load error (`error=plugin_not_found`) identifying the missing plugin as `plugin=<json name>`.

**Test Cases:** `rcb_tests/public_test_cases/feature15_plugin_not_found.json`

```json
{
    "description": "A configuration file in the working directory may list plugins to load. If a listed plugin cannot be found, the runner raises a plugin-load error identifying the missing plugin.",
    "cases": [
        {"input": {"args": ["ls"], "config": "{\"plugins\":[\"missing-plugin-xyz\"]}"}, "expected_output": "error=plugin_not_found\nplugin=\"missing-plugin-xyz\"\n"}
    ]
}
```

*13.2 Unreadable configuration — the file is not valid configuration.*

If the configuration file cannot be parsed as valid configuration, the runner raises a configuration error (`error=config_unreadable`) instead of executing its contents (it must never evaluate the file as code).

**Test Cases:** `rcb_tests/public_test_cases/feature16_config_unreadable.json`

```json
{
    "description": "If the configuration file in the working directory cannot be parsed as valid configuration, the runner raises a configuration error rather than executing its contents.",
    "cases": [
        {"input": {"args": ["ls"], "config": "this is not valid configuration\n"}, "expected_output": "error=config_unreadable\n"}
    ]
}
```

---

### Feature 14: Deciding Whether To Consume Piped Input

**As a developer**, I want the runner to decide automatically whether to wait for piped input, so commands neither block unnecessarily nor miss available input.

**Expected Behavior / Usage:**

Before running, the tool decides whether to consume piped input. Under the `stdin_decision` action it reports this decision (only) as `stdin_consumed=<true|false>` for a given command line (`args`) and whether the input is an interactive terminal (`tty`). It consumes piped input only when ALL of the following hold: input is actually piped (not an interactive terminal), the command is one that accepts standard input, and fewer file operands were supplied than the command requires (some commands such as the line-count-limited head/tail count a numeric option's value as consuming one of the expected operands). An interactive terminal, a command that does not accept standard input, or enough file operands each suppress reading.

**Test Cases:** `rcb_tests/public_test_cases/feature17_stdin_read_decision.json`

```json
{
    "description": "Before running, the tool decides whether to consume piped input. It consumes piped input only when all of the following hold: input is actually piped rather than an interactive terminal, the command is one that accepts standard input, and fewer file operands were supplied than the command requires. An interactive terminal, a command that does not accept standard input, or enough file operands each suppress reading. The decision is reported as a boolean.",
    "cases": [
        {"input": {"action": "stdin_decision", "args": ["cat"], "tty": false}, "expected_output": "stdin_consumed=true\n"},
        {"input": {"action": "stdin_decision", "args": ["grep", "a.*z"], "tty": false}, "expected_output": "stdin_consumed=true\n"},
        {"input": {"action": "stdin_decision", "args": ["cat"], "tty": true}, "expected_output": "stdin_consumed=false\n"},
        {"input": {"action": "stdin_decision", "args": ["cat", "file.txt"], "tty": false}, "expected_output": "stdin_consumed=false\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the command runner described above (argument parsing, command routing and validation, the substitution-syntax shim, optional plugin loading from a working-directory configuration file, and result handling). Its physical structure MUST align with the "Scale-Driven Code Organization" constraint. The core routing logic must be decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program that acts as a client to your core system — logically (and ideally physically) separated from it. It reads a single JSON request from stdin and prints the result to stdout, matching the per-feature contracts above. The request's `action` selects behavior: the default action sets up a sandbox working directory from the optional `files`/`dirs`, runs the command line in `args` with optional piped `stdin`, and renders `exit_code=<n>` plus JSON-encoded `stdout`/`stderr` (and optional `file:<path>=...` / `mode:<path>=...` lines requested via `show_files`/`show_modes`); the `stdin_decision` action renders only the pipe-consumption decision. Native exceptions raised by the core (empty substitution pattern, unresolved plugin, unreadable configuration) MUST be translated by the adapter into the neutral `error=<category>` lines shown above — never by leaking host-language runtime details. Usage/routing failures use exit status `27`; a command that ran but failed forwards its own status. The absolute working-directory path is normalized to the token `<cwd>` in rendered output.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- matches the internal ruby path traversal logic
- the G_FILE_PATTERN transformation rule
