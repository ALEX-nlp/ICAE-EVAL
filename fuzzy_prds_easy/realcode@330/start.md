## Product Requirement Document

# Transparent Build Accelerator with a Typed Wire-Message Layer - PRD

## Project Goal

Build a system that makes repeated execution of command-driven build pipelines dramatically faster by transparently caching the results of each process and replaying them on later runs, while staying completely invisible to the commands being run. The system has two cooperating parts: a transparent execution layer that wraps a build command and every descendant process it spawns, observes what each one does, and serves identical re-executions from a cache; and a compact, allocation-free typed-message layer used to describe those processes on the wire with minimal overhead. Developers get the speedups of a caching build system without rewriting their build scripts, declaring dependencies, or changing the commands they already use.

---

## Background & Problem

Without this system, developers who want incremental or cached builds must either adopt a bespoke build tool that demands hand-written dependency declarations, or rerun every step from scratch on every build. Hand-declared dependencies drift out of sync with reality and produce stale outputs; rerunning everything wastes time recompiling files that never changed. Existing approaches are also intrusive: they require commands to be wrapped, annotated, or rewritten, which breaks for the long tail of shell pipelines, generated code, and ad-hoc scripts that real builds rely on.

With this system, a developer simply prefixes an ordinary build command. The execution layer transparently follows that command and every child it spawns — no matter how the child is launched — records the real file and process behavior, and serves identical re-executions from a content-addressed cache, so the second build of an unchanged input is near-instant. Because the wrapper and the wrapped processes must exchange a high volume of small structured messages with minimal overhead and without risking deadlock inside signal handlers, the system also needs an extremely lightweight serialization format, provided here as a dedicated typed-message layer.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This is a multi-responsibility system (process interception, an execution/cache engine, a wire-format serializer, a command front-end). It MUST NOT be a single "god file"; output a clear, multi-file directory tree separating the interception layer, the supervising engine, the serialization layer, and the command-line entry point. Do not over-engineer, but strictly avoid monolithic files for this domain.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in "Core Features" are a **black-box contract for the execution adapter**, NOT the internal data model of the core system. The core engine and serializer must remain completely decoupled from stdin/stdout and JSON parsing. A thin execution adapter is solely responsible for translating JSON commands into idiomatic calls into the core and rendering normalized output.

3. **Adherence to SOLID Design Principles:**
   - **SRP:** Separate parsing, routing, interception, cache lookup/store, command execution, and output formatting into distinct units.
   - **OCP:** The core engine must be open for extension (new intercepted operations, new spawn mechanisms) but closed for modification.
   - **LSP:** All process-creation mechanisms must be handled uniformly, so a child launched by any of them is substitutable for any other.
   - **ISP:** Keep message-builder and message-reader interfaces small and cohesive.
   - **DIP:** High-level cache/replay logic must depend on abstractions, not on low-level I/O details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the serializer and the command front-end must be elegant and idiomatic to the target language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully — unknown options, non-zero child exit codes, statically linked children, malformed environments, and missing mandatory message fields — modeling errors as explicit, normalized categories rather than generic faults.

---

## Core Features

### Feature 1: Command Front-End

**As a developer**, I want a single command-line entry point that wraps any build command, so I can adopt acceleration by prefixing my existing commands without learning a new build language.

**Expected Behavior / Usage:**

The front-end takes options followed by the build command to run. Two aspects of its argument-parsing surface are observable here: its self-description (a usage banner plus the set of options it accepts and the documented promise that the wrapped command's own exit status is propagated), and its handling of an unrecognized option. The reported view is normalized: a flag for whether a usage banner was shown, the sorted set of advertised long option names, a flag for whether the exit-status passthrough contract is documented, and — on bad input — a neutral `error=invalid_option` category naming the offending option letter. Self-description exits with status 0; an unrecognized option exits with status 1.

*1.1 Help / self-description — reports the usage banner, the full sorted set of long options, and the exit-status passthrough contract*

Asking the front-end to describe itself prints a usage banner, lists every long option it supports (in sorted order), documents that it passes the wrapped command's exit code through, and exits 0.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_cli_help.json`

```json
{
    "description": "Front-end help output normalized to its argument-parsing surface: the usage banner is shown, the full set of advertised long options is reported in sorted order, the documented contract that the wrapped command's exit code is passed through is detected, and the front-end itself exits 0.",
    "cases": [
        {
            "input": {"op": "cli", "args": ["--help"]},
            "expected_output": "exit_status=0\nusage_shown=true\nlong_options=config-file,debug-flags,directory,generate-report,help,[a specific sentinel value — ask the PM for the exact string],option\ndocuments_command_exit_passthrough=true\n"
        }
    ]
}
```

*1.2 Unrecognized option — reports a normalized invalid-option error and exits non-zero*

Passing an option the front-end does not recognize yields a neutral invalid-option error naming the offending letter, still prints the usage banner, and exits 1.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_cli_invalid_option.json`

```json
{
    "description": "When the front-end is given an unrecognized option letter, it reports the offending option in a normalized form, still prints the usage banner, and exits with the failure status 1.",
    "cases": [
        {
            "input": {"op": "cli", "args": ["-Z"]},
            "expected_output": "exit_status=1\nusage_shown=true\nerror=invalid_option\noption=Z\nlong_options=config-file,debug-flags,directory,generate-report,help,[a specific sentinel value — ask the PM for the exact string],option\ndocuments_command_exit_passthrough=true\n"
        }
    ]
}
```

---

### Feature 2: Transparent Execution Passthrough

**As a developer**, I want a wrapped command to behave exactly as it would unwrapped, so acceleration never changes my build's observable output or exit code.

**Expected Behavior / Usage:**

A shell command run under the accelerator produces byte-for-byte the same stdout it would produce on its own, consumes stdin normally, supports pipelines, and propagates the command's exit status verbatim. The reported contract is the wrapped command's exit status plus its stdout delimited between `stdout<<<` and `>>>` markers (so empty output is unambiguous). A command that exits non-zero reports that exact status with whatever output it produced.

**Test Cases:** `rcb_tests/public_test_cases/feature2_execute_passthrough.json`

```json
{
    "description": "A shell command run transparently under the accelerator produces exactly the stdout it would produce without it, and its exit status is propagated unchanged. Covers plain output, output filtered through a pipe, and a non-zero exit code.",
    "cases": [
        {
            "input": {"op": "execute", "command": "echo hello-world"},
            "expected_output": "exit_status=0\nstdout<<<\nhello-world\n>>>\n"
        },
        {
            "input": {"op": "execute", "command": "grep ok", "stdin": "foo\nok\nbar\n"},
            "expected_output": "exit_status=0\nstdout<<<\nok\n>>>\n"
        },
        {
            "input": {"op": "execute", "command": "seq 5 | grep 3"},
            "expected_output": "exit_status=0\nstdout<<<\n3\n>>>\n"
        },
        {
            "input": {"op": "execute", "command": "exit 7"},
            "expected_output": "exit_status=7\nstdout<<<\n>>>\n"
        }
    ]
}
```

---

### Feature 3: Descendant Interception

**As a developer**, I want the accelerator to follow every descendant process my build spawns, no matter how it is launched, so nothing in my pipeline escapes observation and caching.

**Expected Behavior / Usage:**

The accelerator injects an interception facility into the processes it runs, and that facility propagates into descendants across all standard process-creation mechanisms. A running child can observe that interception is active by inspecting the dynamic-preload mechanism it inherited. The reported contract is a neutral flag (`preload_injected=true`) plus confirmation the child actually ran — never the implementation identity of the injected facility. A descendant that cannot have anything injected into it (a statically linked program) must still be run to completion with its stdout passed straight through.

*3.1 Direct child — a program launched directly observes that interception is active*

A program the accelerator launches directly inherits the interception facility and reports it as injected.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_intercept_direct.json`

```json
{
    "description": "A program launched directly by the accelerator inherits the accelerator's interception library in its dynamic-preload environment, so the running child can observe that interception is active. The child also confirms it actually ran.",
    "cases": [
        {
            "input": {"op": "intercept", "method": "direct"},
            "expected_output": "exit_status=0\nchild_ran=true\npreload_injected=true\n"
        }
    ]
}
```

*3.2 Spawned child across all mechanisms — interception follows fork-then-exec, pipe-open, spawn, and the C library command runner*

Regardless of which of the four standard mechanisms a parent uses to spawn a child, the child still observes interception as active.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_intercept_spawn_methods.json`

```json
{
    "description": "Interception follows a descendant regardless of which standard process-creation mechanism the parent uses to spawn it. For each of fork-then-exec, pipe-open, spawn, and the C library command runner, the spawned child observes the interception library injected into its preload environment.",
    "cases": [
        {"input": {"op": "intercept", "method": "fork_exec"}, "expected_output": "exit_status=0\nchild_ran=true\npreload_injected=true\n"},
        {"input": {"op": "intercept", "method": "popen"}, "expected_output": "exit_status=0\nchild_ran=true\npreload_injected=true\n"},
        {"input": {"op": "intercept", "method": "posix_spawn"}, "expected_output": "exit_status=0\nchild_ran=true\npreload_injected=true\n"},
        {"input": {"op": "intercept", "method": "system"}, "expected_output": "exit_status=0\nchild_ran=true\npreload_injected=true\n"}
    ]
}
```

*3.3 Statically linked descendant — runs to completion with stdout passed through, via every spawn mechanism*

A statically linked program (into which nothing can be injected) is still executed correctly through each spawn mechanism, with its own stdout forwarded unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_intercept_static_binary.json`

```json
{
    "description": "A statically linked program (which cannot have any library injected into it) is still correctly run to completion when launched through each standard process-creation mechanism, and its own stdout passes straight through the accelerator unchanged.",
    "cases": [
        {"input": {"op": "intercept", "method": "fork_exec", "static": true}, "expected_output": "exit_status=0\nstdout<<<\nI am statically linked.\n>>>\n"},
        {"input": {"op": "intercept", "method": "popen", "static": true}, "expected_output": "exit_status=0\nstdout<<<\nI am statically linked.\n>>>\n"},
        {"input": {"op": "intercept", "method": "posix_spawn", "static": true}, "expected_output": "exit_status=0\nstdout<<<\nI am statically linked.\n>>>\n"},
        {"input": {"op": "intercept", "method": "system", "static": true}, "expected_output": "exit_status=0\nstdout<<<\nI am statically linked.\n>>>\n"}
    ]
}
```

---

### Feature 4: Environment Resilience

**As a developer**, I want interception to survive even when my build command rebuilds its own environment, so caching keeps working for scripts that manipulate the dynamic-preload list.

**Expected Behavior / Usage:**

A build command may completely replace its environment and write a malformed dynamic-preload list. The accelerator must guarantee two things: the interception facility remains preloaded in descendants (so observation continues), and every user-supplied environment variable is preserved exactly. In the probe, the command rebuilds its environment with two ordinary variables and a preload list whose only valid entry is the interception facility, surrounded by garbage entries and extra spaces. The reported contract confirms the user variables survived, the interception facility is still present, and the runtime loader's complaints about the garbage entries are normalized into neutral `preload_warning=<name>` lines (sorted), leaking no host-language identity.

**Test Cases:** `rcb_tests/public_test_cases/feature4_env_fixup.json`

```json
{
    "description": "Even when a build command completely rebuilds its own environment and writes a deliberately malformed preload list (whose only valid entry is the accelerator's own interception library, surrounded by garbage entries and extra spaces), the interception library still reaches the child while every user-supplied variable is preserved verbatim. The dynamic loader's complaints about the garbage entries are normalized into neutral warning lines.",
    "cases": [
        {
            "input": {"op": "env_fixup"},
            "expected_output": "exit_status=0\nAAA=aaa\nBBB=bbb\ninterceptor_present=true\npreload_warning=BOGUS1.SO\npreload_warning=BOGUS2.SO\n"
        }
    ]
}
```

---

### Feature 5: Diagnostic Stream Passthrough

**As a developer**, I want a wrapped program's diagnostic output and termination behavior to be untouched, so error reporting and cleanup hooks keep working under acceleration.

**Expected Behavior / Usage:**

A wrapped program that emits standard-library diagnostics and registers an at-exit cleanup hook must behave identically under the accelerator: the diagnostic lines (each combining a caller-supplied label with the message derived from the active error number) appear in order, a fatal diagnostic terminates the program with a failure status, the at-exit hook still runs before exit, and the failure status is reported. Two diagnostic-routine variants are exercised. Each diagnostic line is prefixed by a neutral fixed program token so the contract carries no fixture- or language-specific program name. The reported contract is the failure exit status plus the verbatim diagnostic stream delimited by `stderr<<<`/`>>>`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_diagnostics_passthrough.json`

```json
{
    "description": "Standard library diagnostic streams produced by a wrapped program pass through the accelerator unchanged, and the normal program-termination path is preserved: a sequence of non-fatal warnings followed by a fatal one, an at-exit handler that still runs, and a failure exit status. The 'warn' variant reports each diagnostic with the errno-derived message; the 'error' variant uses the alternative diagnostic routine. Each diagnostic line is prefixed by a neutral fixed program token.",
    "cases": [
        {
            "input": {"op": "diagnostics", "variant": "warn"},
            "expected_output": "exit_status=1\nstderr<<<\nprog: w1: No such file or directory\nprog: w2: Permission denied\nprog: e1: No such file or directory\natexit_handler\n>>>\n"
        },
        {
            "input": {"op": "diagnostics", "variant": "error"},
            "expected_output": "exit_status=1\nstderr<<<\nprog: e1: No such file or directory\nprog: e2: Permission denied\nprog: e3: No such file or directory\natexit_handler\n>>>\n"
        }
    ]
}
```

---

### Feature 6: Cache Hit on Repeated Work

**As a developer**, I want identical re-executions to be served from cache instead of re-run, so the second build of an unchanged input is near-instant.

**Expected Behavior / Usage:**

Running the same deterministic compilation twice against a fresh cache demonstrates the core acceleration guarantee. The first run is a cache miss and is executed normally; the second run, given identical inputs, is served from cache rather than re-executed. Both runs succeed. The reported contract is, per run, the run index, the exit status, and a `served_from_cache` flag — `false` on the first (miss) run and `true` on the second (hit) run. This signal distinguishes genuine acceleration from a stub that merely re-runs the command every time.

**Test Cases:** `rcb_tests/public_test_cases/feature6_accelerate_cache_hit.json`

```json
{
    "description": "Compiling the same source file twice against a fresh cache demonstrates the core acceleration guarantee: the first compilation is a cache miss and is executed normally, while the second compilation of the identical input is served from cache instead of being re-executed. Both runs succeed.",
    "cases": [
        {
            "input": {"op": "accelerate", "source": "int add(int a, int b) { return a + b; }\n", "runs": 2},
            "expected_output": "run=1\nexit_status=0\nserved_from_cache=false\nrun=2\nexit_status=0\nserved_from_cache=true\n"
        }
    ]
}
```

---

### Feature 7: Typed Wire-Message Layer

**As a developer**, I want a compact, allocation-free typed-message format, so the wrapper and the intercepted processes can exchange a high volume of small structured messages with minimal overhead.

**Expected Behavior / Usage:**

A message is exactly one of a set of predefined types and carries simple fields: scalars (integers), `'\0'`-terminated strings, and `NULL`-terminated string arrays. Fields are either required or optional; optional fields carry a presence flag. A message is serialized into a framed payload: a header of a payload length and an acknowledgement id, followed by the payload (the field values, then the strings laid out back-to-back), padded so the payload length is a multiple of 8 bytes. The reader decodes a framed payload back into the same field values. The observable round-trip contract reports: the acknowledgement id; whether the frame's declared payload length matches the bytes actually written; whether the payload is padded to an 8-byte boundary; every scalar; each optional's presence flag (and its value only when present); every string; and each string array's element count followed by its elements.

*7.1 Full message round-trip — every field kind present, serialized and decoded back exactly*

A message with all required and optional scalars, all required and optional strings, and two populated string arrays round-trips with every value, presence flag, and framing property reproduced.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_serialize_all_fields.json`

```json
{
    "description": "A message carrying every kind of field (required and optional integers, required and optional strings, and two string arrays) is serialized over the wire frame and decoded back. The decoded message reproduces the acknowledgement id, confirms the frame's declared payload length matches the bytes written and is padded to an 8-byte boundary, and reproduces every scalar, string, presence flag, and array element exactly.",
    "cases": [
        {
            "input": {"op": "serialize", "ack": 123, "fields": {"ri1": 42, "oi2": 100, "ri3": -200, "oi4": -5, "rs5": "foo", "os6": "loremipsum", "rs7": "quux", "os8": "opt", "sa9": ["item1", "item02", "item003"], "sa10": ["x"]}},
            "expected_output": "ack_id=123\ndeclared_length_matches_payload=true\npayload_padded_to_8=true\nri1=42\nhas_oi2=true\noi2=100\nri3=-200\nhas_oi4=true\noi4=-5\nrs5=foo\nhas_os6=true\nos6=loremipsum\nrs7=quux\nhas_os8=true\nos8=opt\nsa9_size=3\nsa9[0]=item1\nsa9[1]=item02\nsa9[2]=item003\nsa10_size=1\nsa10[0]=x\n"
        }
    ]
}
```

*7.2 Optional/empty handling — absent optionals decode as not-present, empty arrays and empty required strings round-trip*

When only required fields are supplied, every optional decodes as not-present with no value line emitted; unset string arrays decode as size 0; an empty required string round-trips as an empty value; an explicitly declared but empty string array also decodes as size 0.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_serialize_optionals_absent.json`

```json
{
    "description": "When only the required fields are provided, every optional integer and optional string decodes as absent (its presence flag is false and no value line is emitted), and unset string arrays decode as empty (size 0). An empty string supplied for a required string round-trips as an empty value, and an explicitly declared but empty string array also decodes as size 0.",
    "cases": [
        {
            "input": {"op": "serialize", "ack": 0, "fields": {"ri1": 7, "ri3": -7, "rs5": "hello", "rs7": "world"}},
            "expected_output": "ack_id=0\ndeclared_length_matches_payload=true\npayload_padded_to_8=true\nri1=7\nhas_oi2=false\nri3=-7\nhas_oi4=false\nrs5=hello\nhas_os6=false\nrs7=world\nhas_os8=false\nsa9_size=0\nsa10_size=0\n"
        },
        {
            "input": {"op": "serialize", "ack": 99, "fields": {"ri1": 1, "ri3": 2, "rs5": "", "rs7": "z", "sa9": []}},
            "expected_output": "ack_id=99\ndeclared_length_matches_payload=true\npayload_padded_to_8=true\nri1=1\nhas_oi2=false\nri3=2\nhas_oi4=false\nrs5=\nhas_os6=false\nrs7=z\nhas_os8=false\nsa9_size=0\nsa10_size=0\n"
        }
    ]
}
```

*7.3 Required-field validation — building a message without a mandatory field is rejected before any bytes are produced*

Omitting a mandatory field yields a neutral error category naming the first missing required field, and no message bytes are produced.

**Test Cases:** `rcb_tests/public_test_cases/feature7_3_serialize_missing_required.json`

```json
{
    "description": "Building a message without all of its mandatory fields is rejected before any wire bytes are produced. The result is a neutral error category naming the first missing required field rather than a partial or corrupt message.",
    "cases": [
        {
            "input": {"op": "serialize", "ack": 0, "fields": {"ri1": 1, "rs5": "a", "rs7": "b"}},
            "expected_output": "error=missing_required_field\nfield=ri3\n"
        },
        {
            "input": {"op": "serialize", "ack": 0, "fields": {"ri1": 1, "ri3": 2, "rs7": "b"}},
            "expected_output": "error=missing_required_field\nfield=rs5\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the features above — a process-interception layer, a supervising execution/cache engine, a typed wire-message serialization layer, and a command-line front-end — with their responsibilities physically separated as required by the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above (including normalizing any native runtime diagnostics into neutral `error=<category>` lines). This adapter must be logically and physically separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_cli_help.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_cli_help@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- document exit-passthrough contract
