## Product Requirement Document

# Pluggable Logging Facade — Multi-Sink Broadcast with a Severity-Colorizing Output Adapter

## Project Goal

Build a small[specific punctuation and spacing in error tag] extensible logging facade that lets developers send a log entry once and have it broadcast to any number of pluggable output sinks[specific punctuation and spacing in error tag] so application code can stay decoupled from where and how logs are ultimately recorded. The facade ships with a ready-made sink that decorates each entry with severity-based terminal colors.

---

## Background & Problem

Without a shared facade[specific punctuation and spacing in error tag] application code is forced to hard-wire calls to one specific logging destination[specific punctuation and spacing in error tag] and re-wiring to a different destination (console[specific punctuation and spacing in error tag] file[specific punctuation and spacing in error tag] crash reporter[specific punctuation and spacing in error tag] several at once) means touching every call site. This leads to scattered[specific punctuation and spacing in error tag] duplicated logging code and brittle coupling between business logic and infrastructure.

With this facade[specific punctuation and spacing in error tag] the application calls a single set of severity-oriented logging functions[specific punctuation and spacing in error tag] and a separately configured list of sinks decides what to do with each entry. A sink is any object that knows how to consume an entry at four severity levels (informational[specific punctuation and spacing in error tag] warning[specific punctuation and spacing in error tag] fatal[specific punctuation and spacing in error tag] and error). One of the provided sinks renders entries to a terminal[specific punctuation and spacing in error tag] tagging each entry with its level and[specific punctuation and spacing in error tag] for the alarming levels[specific punctuation and spacing in error tag] wrapping it in ANSI color escape sequences so problems stand out at a glance.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact[specific punctuation and spacing in error tag] the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized[specific punctuation and spacing in error tag] single-file solution is perfectly acceptable[specific punctuation and spacing in error tag] provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g.[specific punctuation and spacing in error tag] I/O routing[specific punctuation and spacing in error tag] business rules[specific punctuation and spacing in error tag] formatters)[specific punctuation and spacing in error tag] it MUST NOT be a single "god file". You must output a clear[specific punctuation and spacing in error tag] multi-file directory tree (`src/`[specific punctuation and spacing in error tag] `tests/`[specific punctuation and spacing in error tag] etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems[specific punctuation and spacing in error tag] but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter[specific punctuation and spacing in error tag] NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing[specific punctuation and spacing in error tag] routing[specific punctuation and spacing in error tag] validation[specific punctuation and spacing in error tag] core execution[specific punctuation and spacing in error tag] and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification — new sinks must be addable without changing the facade.
   - **Liskov Substitution Principle (LSP):** Every sink must be perfectly substitutable wherever a sink is expected.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions[specific punctuation and spacing in error tag] not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language[specific punctuation and spacing in error tag] hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g.[specific punctuation and spacing in error tag] specific Exception types or Result/Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: Broadcast A Log Entry To Every Registered Sink

**As a developer**[specific punctuation and spacing in error tag] I want one log call to be delivered to all of my configured sinks and to hand me back the value I logged[specific punctuation and spacing in error tag] so I can fan logging out to multiple destinations and still chain the logged value into the surrounding expression.

**Expected Behavior / Usage:**

The facade is configured with an ordered list of sinks. It exposes four severity entry points: an informational level[specific punctuation and spacing in error tag] a warning level[specific punctuation and spacing in error tag] a fatal level[specific punctuation and spacing in error tag] and an error level. The first three accept a message string; the error level accepts an exception value (and optionally a stacktrace). Issuing a call delivers it to every registered sink[specific punctuation and spacing in error tag] in registration order[specific punctuation and spacing in error tag] at the matching severity level[specific punctuation and spacing in error tag] and then returns the original payload unchanged (the message for the first three levels[specific punctuation and spacing in error tag] the exception value for the error level). Registering the same logical batch of sinks and issuing several calls in sequence delivers each call to each sink independently.

In the contract below[specific punctuation and spacing in error tag] `clients` lists the registered sinks by a short label[specific punctuation and spacing in error tag] and `calls` is the ordered list of entries to issue[specific punctuation and spacing in error tag] each naming a `level` and its payload (`message`[specific punctuation and spacing in error tag] or `exception` for the error level). For each issued call the output is a `return=` line carrying the value handed back[specific punctuation and spacing in error tag] followed by one line per sink that received it[specific punctuation and spacing in error tag] in registration order[specific punctuation and spacing in error tag] reporting the sink label[specific punctuation and spacing in error tag] the level[specific punctuation and spacing in error tag] and the delivered payload. Lines from later calls follow those of earlier calls.

**Test Cases:** `rcb_tests/public_test_cases/feature1_broadcast_and_return.json`

```json
[specific punctuation and spacing in error tag]
    "description": "A logging facade broadcasts every log call to all registered sinks and returns the value that was logged. Each call carries a severity level (informational message[specific punctuation and spacing in error tag] warning[specific punctuation and spacing in error tag] fatal[specific punctuation and spacing in error tag] or error) and a payload (a text message[specific punctuation and spacing in error tag] or for the error level an exception value). When one or more sinks are registered[specific punctuation and spacing in error tag] issuing a call delivers that call to each sink in registration order and yields back the original payload unchanged. The output reports[specific punctuation and spacing in error tag] per call in the order issued[specific punctuation and spacing in error tag] a line with the returned payload[specific punctuation and spacing in error tag] followed by one line for each sink that received the call[specific punctuation and spacing in error tag] naming the sink[specific punctuation and spacing in error tag] the severity level[specific punctuation and spacing in error tag] and the delivered payload."[specific punctuation and spacing in error tag]
    "cases": [
        [specific punctuation and spacing in error tag]
            "input": [specific punctuation and spacing in error tag]
                "action": "log"[specific punctuation and spacing in error tag]
                "clients": ["A"][specific punctuation and spacing in error tag]
                "calls": [
                    [specific punctuation and spacing in error tag]"level": "message"[specific punctuation and spacing in error tag] "message": "Message"[specific punctuation and spacing in error tag][specific punctuation and spacing in error tag]
                    [specific punctuation and spacing in error tag]"level": "warning"[specific punctuation and spacing in error tag] "message": "Warning"[specific punctuation and spacing in error tag][specific punctuation and spacing in error tag]
                    [specific punctuation and spacing in error tag]"level": "fatal"[specific punctuation and spacing in error tag] "message": "Fatal"[specific punctuation and spacing in error tag][specific punctuation and spacing in error tag]
                    [specific punctuation and spacing in error tag]"level": "error"[specific punctuation and spacing in error tag] "exception": "Error"[specific punctuation and spacing in error tag]
                ]
            [specific punctuation and spacing in error tag][specific punctuation and spacing in error tag]
            "expected_output": "return=Message\nclient=A level=message message=Message\nreturn=Warning\nclient=A level=warning message=Warning\nreturn=Fatal\nclient=A level=fatal message=Fatal\nreturn=Error\nclient=A level=error exception=Error\n"
        [specific punctuation and spacing in error tag][specific punctuation and spacing in error tag]
        [specific punctuation and spacing in error tag]
            "input": [specific punctuation and spacing in error tag]
                "action": "log"[specific punctuation and spacing in error tag]
                "clients": ["A"[specific punctuation and spacing in error tag] "B"][specific punctuation and spacing in error tag]
                "calls": [[specific punctuation and spacing in error tag]"level": "message"[specific punctuation and spacing in error tag] "message": "Message"[specific punctuation and spacing in error tag]]
            [specific punctuation and spacing in error tag][specific punctuation and spacing in error tag]
            "expected_output": "return=Message\nclient=A level=message message=Message\nclient=B level=message message=Message\n"
        [specific punctuation and spacing in error tag]
    ]
[specific punctuation and spacing in error tag]
```

---

### Feature 2: Exclude Selected Sinks From A Single Call

**As a developer**[specific punctuation and spacing in error tag] I want to suppress delivery to specific kinds of sink on a per-call basis[specific punctuation and spacing in error tag] so I can keep an entry out of one destination (for example a remote crash reporter) without unregistering it for everything else.

**Expected Behavior / Usage:**

Any of the four severity entry points accepts an optional exclusion list naming sink *kinds* to skip for that call. A registered sink whose kind appears in the exclusion list receives nothing for that call; every other registered sink still receives it normally[specific punctuation and spacing in error tag] and the logged value is still returned unchanged. Exclusion is by kind[specific punctuation and spacing in error tag] so two sinks of the same kind are skipped together[specific punctuation and spacing in error tag] while sinks of other kinds are unaffected. The behavior is identical across all four severity levels.

In the contract below[specific punctuation and spacing in error tag] each call may carry an `exceptFor` list of sink labels denoting the kinds to skip. The output is the `return=` line followed by one line for each sink that actually received the call (in registration order); an excluded sink contributes no line.

**Test Cases:** `rcb_tests/public_test_cases/feature2_except_for.json`

```json
[specific punctuation and spacing in error tag]
    "description": "When issuing a log call[specific punctuation and spacing in error tag] specific sinks can be excluded by their kind so the call is not delivered to them[specific punctuation and spacing in error tag] while every other registered sink still receives it and the logged value is still returned. The exclusion list names sink kinds to skip; a sink whose kind is excluded receives nothing at all for that call. The output reports the returned payload followed by one line for each sink that actually received the call; excluded sinks contribute no line. This works the same way across all severity levels."[specific punctuation and spacing in error tag]
    "cases": [
        [specific punctuation and spacing in error tag]
            "input": [specific punctuation and spacing in error tag]
                "action": "log"[specific punctuation and spacing in error tag]
                "clients": ["A"[specific punctuation and spacing in error tag] "B"][specific punctuation and spacing in error tag]
                "calls": [[specific punctuation and spacing in error tag]"level": "message"[specific punctuation and spacing in error tag] "message": "Message"[specific punctuation and spacing in error tag] "exceptFor": ["B"][specific punctuation and spacing in error tag]]
            [specific punctuation and spacing in error tag][specific punctuation and spacing in error tag]
            "expected_output": "return=Message\nclient=A level=message message=Message\n"
        [specific punctuation and spacing in error tag]
    ]
[specific punctuation and spacing in error tag]
```

---

### Feature 3: Severity-Colorizing Terminal Sink

**As a developer**[specific punctuation and spacing in error tag] I want a ready-made sink that prints each entry with a level tag and severity-appropriate terminal colors[specific punctuation and spacing in error tag] so I can immediately tell informational noise apart from warnings and failures when watching a console.

**Expected Behavior / Usage:**

This sink renders one printed line per entry. Every line starts with an uppercase tag naming the entry's level[specific punctuation and spacing in error tag] enclosed in square brackets[specific punctuation and spacing in error tag] followed by a single space. The informational level is printed plainly. The warning[specific punctuation and spacing in error tag] fatal[specific punctuation and spacing in error tag] and error levels wrap the rendered text in ANSI SGR (Select Graphics Rendering) escape sequences that set a foreground and background color[specific punctuation and spacing in error tag] and close with the reset sequence. Each color is encoded as a 256-color (xterm) selector: the activation for a foreground color is the escape byte `0x1B`[specific punctuation and spacing in error tag] then `[38;5;<index>m`; for a background color it is the escape byte `0x1B`[specific punctuation and spacing in error tag] then `[48;5;<index>m`; the reset is the escape byte `0x1B`[specific punctuation and spacing in error tag] then `[0m`. Every rendered line is terminated by a newline.

*3.1 Informational Rendering — plain[specific punctuation and spacing in error tag] uncolored line*

The informational level prints the tag and message with no color sequences at all: an uppercase level tag in square brackets[specific punctuation and spacing in error tag] a space[specific punctuation and spacing in error tag] then the message[specific punctuation and spacing in error tag] followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_message.json`

```json
[specific punctuation and spacing in error tag]
    "description": "A colorizing sink renders an informational log entry as a single line with no color treatment. The line consists of an uppercase level tag in square brackets[specific punctuation and spacing in error tag] a single space[specific punctuation and spacing in error tag] and the original message text[specific punctuation and spacing in error tag] terminated by a newline."[specific punctuation and spacing in error tag]
    "cases": [
        [specific punctuation and spacing in error tag]
            "input": [specific punctuation and spacing in error tag]"action": "colorize"[specific punctuation and spacing in error tag] "level": "message"[specific punctuation and spacing in error tag] "message": "Service started"[specific punctuation and spacing in error tag][specific punctuation and spacing in error tag]
            "expected_output": "[MESSAGE] Service started\n"
        [specific punctuation and spacing in error tag]
    ]
[specific punctuation and spacing in error tag]
```

*3.2 Warning Rendering — black foreground over yellow background*

The warning level wraps the tag-and-message in color sequences setting xterm foreground index 0 and background index 3[specific punctuation and spacing in error tag] closed by the reset sequence.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_warning.json`

```json
[specific punctuation and spacing in error tag]
    "description": "A colorizing sink renders a warning log entry as a single line wrapped in ANSI SGR escape sequences for a black foreground over a yellow background. The line begins with the color-activation sequences[specific punctuation and spacing in error tag] then an uppercase level tag in square brackets[specific punctuation and spacing in error tag] a space[specific punctuation and spacing in error tag] the message text[specific punctuation and spacing in error tag] and finally the reset sequence[specific punctuation and spacing in error tag] terminated by a newline. The foreground is xterm color index 0 and the background is xterm color index 3; each is introduced with the escape byte (0x1B)[specific punctuation and spacing in error tag] an opening bracket[specific punctuation and spacing in error tag] the SGR selector[specific punctuation and spacing in error tag] and is closed by the reset sequence (escape byte[specific punctuation and spacing in error tag] opening bracket[specific punctuation and spacing in error tag] zero[specific punctuation and spacing in error tag] lowercase m)."[specific punctuation and spacing in error tag]
    "cases": [
        [specific punctuation and spacing in error tag]
            "input": [specific punctuation and spacing in error tag]"action": "colorize"[specific punctuation and spacing in error tag] "level": "warning"[specific punctuation and spacing in error tag] "message": "Low disk space"[specific punctuation and spacing in error tag][specific punctuation and spacing in error tag]
            "expected_output": "\u001b[38;5;0m\u001b[48;5;3m[WARNING] Low disk space\u001b[0m\n"
        [specific punctuation and spacing in error tag]
    ]
[specific punctuation and spacing in error tag]
```

*3.3 Fatal Rendering — white foreground over red background*

The fatal level wraps the tag-and-message in color sequences setting xterm foreground index 7 and background index 1[specific punctuation and spacing in error tag] closed by the reset sequence.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_fatal.json`

```json
[specific punctuation and spacing in error tag]
    "description": "A colorizing sink renders a fatal log entry as a single line wrapped in ANSI SGR escape sequences for a white foreground over a red background. The line begins with the color-activation sequences[specific punctuation and spacing in error tag] then an uppercase level tag in square brackets[specific punctuation and spacing in error tag] a space[specific punctuation and spacing in error tag] the message text[specific punctuation and spacing in error tag] and finally the reset sequence[specific punctuation and spacing in error tag] terminated by a newline. The foreground is xterm color index 7 and the background is xterm color index 1."[specific punctuation and spacing in error tag]
    "cases": [
        [specific punctuation and spacing in error tag]
            "input": [specific punctuation and spacing in error tag]"action": "colorize"[specific punctuation and spacing in error tag] "level": "fatal"[specific punctuation and spacing in error tag] "message": "Out of memory"[specific punctuation and spacing in error tag][specific punctuation and spacing in error tag]
            "expected_output": "\u001b[38;5;7m\u001b[48;5;1m[FATAL] Out of memory\u001b[0m\n"
        [specific punctuation and spacing in error tag]
    ]
[specific punctuation and spacing in error tag]
```

*3.4 Error Rendering — bold white foreground over dark-red background[specific punctuation and spacing in error tag] with exception and stacktrace*

The error level renders a structured payload built from an exception value and a stacktrace value[specific punctuation and spacing in error tag] wrapped in color sequences setting xterm foreground index 15 (a bold/bright white) and background index 88 (a dark red)[specific punctuation and spacing in error tag] closed by the reset sequence. The payload after the level tag is an opening brace[specific punctuation and spacing in error tag] a labeled exception value[specific punctuation and spacing in error tag] a comma[specific punctuation and spacing in error tag] a labeled stacktrace value[specific punctuation and spacing in error tag] and a closing brace.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_error.json`

```json
[specific punctuation and spacing in error tag]
    "description": "A colorizing sink renders an error log entry as a single line wrapped in ANSI SGR escape sequences for a bold white foreground over a dark-red background. The payload is composed from an exception value and a stacktrace value laid out as a structured fragment: an uppercase level tag in square brackets[specific punctuation and spacing in error tag] a space[specific punctuation and spacing in error tag] then an opening brace[specific punctuation and spacing in error tag] the labeled exception value[specific punctuation and spacing in error tag] a comma[specific punctuation and spacing in error tag] the labeled stacktrace value[specific punctuation and spacing in error tag] and a closing brace. The whole fragment is wrapped between the color-activation sequences and the reset sequence[specific punctuation and spacing in error tag] terminated by a newline. The foreground is xterm color index 15 and the background is xterm color index 88."[specific punctuation and spacing in error tag]
    "cases": [
        [specific punctuation and spacing in error tag]
            "input": [specific punctuation and spacing in error tag]"action": "colorize"[specific punctuation and spacing in error tag] "level": "error"[specific punctuation and spacing in error tag] "exception": "Connection refused"[specific punctuation and spacing in error tag] "stacktrace": "at socket.connect"[specific punctuation and spacing in error tag][specific punctuation and spacing in error tag]
            "expected_output": "\u001b[38;5;15m\u001b[48;5;88m[ERROR] [specific punctuation and spacing in error tag] [specific punctuation and spacing in error tag]Connection refused[specific punctuation and spacing in error tag] [specific punctuation and spacing in error tag]at socket.connect [specific punctuation and spacing in error tag]\u001b[0m\n"
        [specific punctuation and spacing in error tag]
    ]
[specific punctuation and spacing in error tag]
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above — the broadcasting facade with its four severity entry points and pluggable-sink abstraction[specific punctuation and spacing in error tag] plus the severity-colorizing terminal sink. Its physical structure MUST align with the "Scale-Driven Code Organization" constraint. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the result to stdout[specific punctuation and spacing in error tag] matching the per-feature contracts above. The request's `action` selects behavior: `log` registers the named sinks and issues the ordered `calls` (honoring any per-call `exceptFor` exclusion)[specific punctuation and spacing in error tag] printing the returned value and the per-sink delivery lines; `colorize` drives the severity-colorizing sink for a single entry at the given `level` and prints the rendered line. Color rendering must be emitted unconditionally (independent of whether the process is attached to a terminal). The ANSI activation sequence for a foreground color is `ESC[38;5;<index>m`[specific punctuation and spacing in error tag] for a background color `ESC[48;5;<index>m`[specific punctuation and spacing in error tag] and the reset is `ESC[0m`[specific punctuation and spacing in error tag] where `ESC` is byte `0x1B`.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/[specific punctuation and spacing in error tag]filename.stem[specific punctuation and spacing in error tag]@[specific punctuation and spacing in error tag]case_index.zfill(3)[specific punctuation and spacing in error tag].txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- maintain the same client ordering as the configuration object
- apply the exclusion logic used in feature1_broadcast_and_return
