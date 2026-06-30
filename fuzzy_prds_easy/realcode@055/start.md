## Product Requirement Document

# Cross-Platform Desktop Notification Router - Product Requirements

## Project Goal

Build a desktop-notification library that lets application developers raise a native pop-up notification with a single, uniform request object, while the library transparently routes that request to whichever platform notification mechanism is appropriate (a Linux desktop notifier, a macOS notification sender, a Windows balloon/toast notifier, or a cross-platform network-push notifier). Developers write one option object; the library normalizes it, picks a backend, and constructs the exact command vector that backend's underlying tool expects.

---

## Background & Problem

Without this library, developers who want to show a notification must learn the bespoke command-line interface of every platform's notification tool: one tool takes positional quoted arguments, another takes single-dash flags, another wants binary icon data over a network socket, and each has its own naming for the same concepts (icon, title, urgency, duration, quiet mode). They must also hand-roll shell escaping for user-supplied text, pick the right executable for the host CPU architecture, and supply sensible defaults. This leads to repetitive, error-prone, platform-specific boilerplate that is easy to get subtly wrong (especially escaping, which is a security concern).

With this library, the developer supplies a single high-level option object (title, message, icon, plus optional extras). The library [a specific list of backend identifiers — see backend registry for exact names]s shorthand and aliased keys to each backend's canonical option names, drops options a backend does not understand, applies defaults, performs correct escaping, selects the right executable, and emits the precise argument vector — so the developer never touches a platform tool directly.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain has several distinct responsibilities (per-backend option [a specific list of backend identifiers — see backend registry for exact names]ping, argument-vector construction, executable/architecture selection, request validation, and backend selection). It MUST NOT be a single "god file"; use a clear directory tree separating the core option/argument logic from each backend wrapper and from the I/O boundary. Do not over-engineer, but avoid a monolith.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases in "Core Features" are a **black-box contract** for an execution adapter, NOT the internal data model. The core library must be usable as a plain in-process API (construct a backend, call its notify/[a specific list of backend identifiers — see backend registry for exact names]ping methods) with no awareness of stdin/stdout or JSON. The execution adapter is solely responsible for translating JSON commands into idiomatic calls and rendering results.

3. **Adherence to SOLID Design Principles (scaled to project size):**
   - **SRP:** Keep option [a specific list of backend identifiers — see backend registry for exact names]ping, argument construction, validation, executable selection, and output formatting in distinct units.
   - **OCP:** Adding a new backend must not require modifying existing [a specific list of backend identifiers — see backend registry for exact names]' logic.
   - **LSP:** All [a specific list of backend identifiers — see backend registry for exact names] must be interchangeable behind a common notifier interface.
   - **ISP:** Keep the public notifier interface small and cohesive.
   - **DIP:** The [a specific list of backend identifiers — see backend registry for exact names] must depend on an abstract process/dispatch boundary, not directly on a concrete OS-spawning call, so that boundary can be substituted.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface must be elegant and idiomatic to the target language, hiding the per-backend complexity.
   - **Resilience:** Invalid requests (e.g. a missing message) must be reported through a modeled error result rather than crashing or silently dispatching an empty command. User-supplied text must be escaped so it cannot be reinterpreted by a shell.

---

## Core Features

### Feature 1: Backend Registry & Default Selection

**As a developer**, I want to discover which notification [a specific list of backend identifiers — see backend registry for exact names] are available and obtain a ready-to-use default sender, so I can send a notification immediately without manually wiring up a platform-specific backend.

**Expected Behavior / Usage:**

The library exposes a fixed set of named, constructable [a specific list of backend identifiers — see backend registry for exact names] covering the Linux desktop notifier, the macOS notification sender, the Windows balloon notifier, the Windows toast notifier, and the cross-platform network-push notifier. It also pre-selects one of these as a default sender that is immediately usable. A query for the registry returns one `backend=<Name>` line per available backend in sorted order, followed by a `default_notify=available` line confirming the default sender is ready. The set of backend names is stable and does not depend on which host the query runs on.

**Test Cases:** `rcb_tests/public_test_cases/feature1_backend_registry.json`

```json
{
    "description": "Lists which notification [a specific list of backend identifiers — see backend registry for exact names] the library exposes as constructable senders, and confirms a default sender (bound to the current platform) is ready to use. Output is one sorted 'backend=<Name>' line per available backend plus a 'default_notify' readiness line.",
    "cases": [
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\"}",
            "expected_output": "backend=Growl\nbackend=NotificationCenter\nbackend=NotifySend\nbackend=WindowsBalloon\nbackend=WindowsToaster\ndefault_notify=available\n"
        }
    ]
}
```

---

### Feature 2: Option Normalization per Backend

**As a developer**, I want a single set of option keys (with convenient shorthands and aliases) to be normalized into each backend's canonical option names, so I can write one option object and have it work regardless of which backend ultimately handles it.

**Expected Behavior / Usage:**

Each backend has its own canonical option vocabulary. Normalization rewrites generic/aliased/shorthand keys into the backend's canonical keys, leaving title and message intact. The normalized result is rendered as one sorted `key=value` line per option. Icons are handled per backend: path-style [a specific list of backend identifiers — see backend registry for exact names] keep the icon as a string under their own icon key, while the network-push backend must materialize the icon as raw bytes.

*2.1 Linux notifier — icon alias normalization*

For the Linux desktop notifier, both a generic application-icon key and the single-letter `i` icon shorthand collapse to a canonical `icon` key. Title and message pass through unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_[a specific list of backend identifiers — see backend registry for exact names]_notifysend_icon.json`

```json
{
    "description": "Normalizes a user-facing option object into the shape consumed by the Linux notify-send backend. The generic application-icon key and the 'i' icon shorthand both collapse to a canonical 'icon' key; title and message are preserved. Output is one sorted 'key=value' line per resulting option.",
    "cases": [
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"target\":\"notify-send\",\"options\":{\"title\":\"Foo\",\"message\":\"Bar\",\"appIcon\":\"foobar\"}}",
            "expected_output": "icon=foobar\nmessage=Bar\ntitle=Foo\n"
        },
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"target\":\"notify-send\",\"options\":{\"title\":\"Foo\",\"message\":\"Bar\",\"i\":\"foobar\"}}",
            "expected_output": "icon=foobar\nmessage=Bar\ntitle=Foo\n"
        }
    ]
}
```

*2.2 Linux notifier — shorthand flag expansion*

Single-letter shorthands expand to the Linux notifier's full option names: `u`→`urgency`, `e`→`expire-time`, `c`→`category`, `i`→`icon`, `h`→`hint`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_[a specific list of backend identifiers — see backend registry for exact names]_notifysend_shorthand.json`

```json
{
    "description": "Expands single-letter option shorthands into their full notify-send option names: u->urgency, e->expire-time, c->category, i->icon, h->hint. Output is one sorted 'key=value' line per resulting option.",
    "cases": [
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"target\":\"notify-send\",\"options\":{\"u\":\"a\",\"e\":\"b\",\"c\":\"c\",\"i\":\"d\",\"h\":\"e\"}}",
            "expected_output": "category=c\nexpire-time=b\nhint=e\nicon=d\nurgency=a\n"
        }
    ]
}
```

*2.3 macOS notifier — icon alias normalization*

For the macOS notification sender, the generic `icon` key and the `i` shorthand both collapse to a canonical application-icon key. Title and message pass through unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_[a specific list of backend identifiers — see backend registry for exact names]_mac_icon.json`

```json
{
    "description": "Normalizes a user-facing option object into the shape consumed by the macOS notification backend. The generic 'icon' key and the 'i' icon shorthand both collapse to a canonical application-icon key ('appIcon'); title and message are preserved. Output is one sorted 'key=value' line per resulting option.",
    "cases": [
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"target\":\"mac\",\"options\":{\"title\":\"Foo\",\"message\":\"Bar\",\"icon\":\"foobar\"}}",
            "expected_output": "appIcon=foobar\nmessage=Bar\ntitle=Foo\n"
        },
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"target\":\"mac\",\"options\":{\"title\":\"Foo\",\"message\":\"Bar\",\"i\":\"foobar\"}}",
            "expected_output": "appIcon=foobar\nmessage=Bar\ntitle=Foo\n"
        }
    ]
}
```

*2.4 Network-push notifier — icon materialized as bytes*

The network-push backend transmits the icon as binary content rather than a path, so normalization must read the referenced icon into a byte buffer regardless of whether it was supplied via the generic icon key or the application-icon key. In the cases below, `@app-icon` is a portable reference to a bundled 16-byte image asset; the rendered value `bytes:<length>` reports that the icon was materialized as binary of that length.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_[a specific list of backend identifiers — see backend registry for exact names]_growl_icon_bytes.json`

```json
{
    "description": "Normalizes a user-facing option object for the network-push (GNTP) backend, which requires the icon to be loaded as binary bytes rather than a path. A '@app-icon' placeholder refers to a bundled 16-byte image asset; whether supplied via the generic 'icon' key or the application-icon key, it is read into a byte buffer and exposed under 'icon'. The rendered value 'bytes:<length>' reports that the icon was materialized as binary of that byte length.",
    "cases": [
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"target\":\"growl\",\"options\":{\"title\":\"Foo\",\"message\":\"Bar\",\"icon\":\"@app-icon\"}}",
            "expected_output": "icon=bytes:16\nmessage=Bar\ntitle=Foo\n"
        },
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"target\":\"growl\",\"options\":{\"title\":\"Foo\",\"message\":\"Bar\",\"appIcon\":\"@app-icon\"}}",
            "expected_output": "icon=bytes:16\nmessage=Bar\ntitle=Foo\n"
        }
    ]
}
```

---

### Feature 3: Linux Notifier — Command Vector Construction

**As a developer**, I want the Linux backend to turn my request into the exact positional-plus-flag argument vector its underlying tool expects, with safe escaping and sensible defaults, so I never assemble or escape a command line myself.

**Expected Behavior / Usage:**

The Linux backend produces a vector where title and message are the first two positional arguments, each wrapped in double quotes; a missing title defaults to `Node Notification:`. Supported extra options become `--<name>` flags followed by their quoted value; unsupported options are silently dropped. Special shell metacharacters in text are backslash-escaped before quoting. The rendered output reports the resolved `program` name, the `argc` count, and each `argv[i]`.

*3.1 Positional title/message with default title*

Title and message [a specific list of backend identifiers — see backend registry for exact names] to the first two quoted positional arguments; omitting the title substitutes the default title.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_notifysend_[a specific list of backend identifiers — see backend registry for exact names]_title_default.json`

```json
{
    "description": "Builds the command vector dispatched to the Linux notify-send backend from a notification request. Title and message become the first two positional, double-quote-wrapped arguments; a missing title falls back to the default 'Node Notification:'. Output reports the resolved program name, the argument count, and each positional argument.",
    "cases": [
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"notifier\":\"notify-send\",\"options\":{\"title\":\"title\",\"message\":\"body\"}}",
            "expected_output": "program=notify-send\nargc=2\nargv[0]=\"title\"\nargv[1]=\"body\"\n"
        },
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"notifier\":\"notify-send\",\"options\":{\"message\":\"body\"}}",
            "expected_output": "program=notify-send\nargc=2\nargv[0]=\"Node Notification:\"\nargv[1]=\"body\"\n"
        }
    ]
}
```

*3.2 Shell-metacharacter escaping*

Double quotes, backticks, dollar signs and backslashes in the message are backslash-escaped before the value is wrapped in quotes, so they cannot be reinterpreted by a shell.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_notifysend_[a specific list of backend identifiers — see backend registry for exact names]_escape.json`

```json
{
    "description": "Shows that special shell metacharacters inside the message are backslash-escaped before being wrapped in double quotes when building the notify-send command vector, preventing them from being interpreted by a shell.",
    "cases": [
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"notifier\":\"notify-send\",\"options\":{\"message\":\"some \\\"me'ss`age`\\\"\"}}",
            "expected_output": "program=notify-send\nargc=2\nargv[0]=\"Node Notification:\"\nargv[1]=\"some \\\"me'ss\\`age\\`\\\"\"\n"
        }
    ]
}
```

*3.3 Supported flags kept, unsupported options dropped*

A supported option such as `icon` becomes a `--icon` flag plus quoted value; an unsupported option is removed entirely.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_notifysend_[a specific list of backend identifiers — see backend registry for exact names]_flags.json`

```json
{
    "description": "Shows how extra options are appended to the notify-send command vector: a supported option such as 'icon' is emitted as a '--icon' flag followed by its quoted value, while an unsupported option (here 'tullball') is silently dropped. Output reports the program, argument count, and each argument.",
    "cases": [
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"notifier\":\"notify-send\",\"options\":{\"title\":\"title\",\"message\":\"body\",\"icon\":\"icon-string\"}}",
            "expected_output": "program=notify-send\nargc=4\nargv[0]=\"title\"\nargv[1]=\"body\"\nargv[2]=--icon\nargv[3]=\"icon-string\"\n"
        },
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"notifier\":\"notify-send\",\"options\":{\"title\":\"title\",\"message\":\"body\",\"icon\":\"icon-string\",\"tullball\":\"notValid\"}}",
            "expected_output": "program=notify-send\nargc=4\nargv[0]=\"title\"\nargv[1]=\"body\"\nargv[2]=--icon\nargv[3]=\"icon-string\"\n"
        }
    ]
}
```

---

### Feature 4: Windows Balloon Notifier — Executable Selection & Argument Vector

**As a developer**, I want the Windows backend to pick the correct executable for the host CPU and emit single-dash flags with the right defaults, so my notification works on both 32-bit and 64-bit Windows without special-casing.

**Expected Behavior / Usage:**

This backend resolves a 64-bit executable on a 64-bit host and a 32-bit executable on a 32-bit host. It emits single-dash flags: message under `-m`, title under `-p` (default `Node Notification:` when absent), a display duration under `-d`, an icon under `-i`, and a quiet/silent flag `-q` that is present by default. Boolean flags use explicit-true semantics: a `true` boolean is emitted as a bare flag, a `false` boolean is omitted. Requesting sound, or explicitly disabling quiet mode, removes `-q`. Unsupported options are dropped. Message text is passed through literally for this backend (no quote-wrapping). Output reports `program`, `argc`, and each `argv[i]`.

*4.1 Architecture-based executable selection*

A 64-bit host resolves the 64-bit executable; a 32-bit host resolves the 32-bit executable.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_notifu_arch_select.json`

```json
{
    "description": "Selects the correct Windows notifier executable based on CPU architecture: a 64-bit host resolves the 64-bit binary ('notifu64.exe'), a 32-bit host resolves the 32-bit binary ('notifu.exe'). Output reports the resolved program name plus the resulting argument vector for the same title/message request.",
    "cases": [
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"notifier\":\"notifu\",\"arch\":\"x64\",\"options\":{\"title\":\"title\",\"message\":\"body\"}}",
            "expected_output": "program=notifu64.exe\nargc=5\nargv[0]=-m\nargv[1]=body\nargv[2]=-p\nargv[3]=title\nargv[4]=-q\n"
        },
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"notifier\":\"notifu\",\"arch\":\"ia32\",\"options\":{\"title\":\"title\",\"message\":\"body\"}}",
            "expected_output": "program=notifu.exe\nargc=5\nargv[0]=-m\nargv[1]=body\nargv[2]=-p\nargv[3]=title\nargv[4]=-q\n"
        }
    ]
}
```

*4.2 Single-dash flags with default title*

Message under `-m`, title under `-p` (default substituted when missing), quiet `-q` present by default; message text passed through literally.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_notifu_[a specific list of backend identifiers — see backend registry for exact names]_default.json`

```json
{
    "description": "Builds the argument vector for the Windows notifier using single-dash flags: message under '-m', title under '-p', and a quiet/silent flag '-q' by default. A missing title falls back to the default 'Node Notification:'. Message text is passed through literally (no quote-wrapping for this backend). Output reports the program, argument count, and each argument.",
    "cases": [
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"notifier\":\"notifu\",\"options\":{\"title\":\"title\",\"message\":\"body\"}}",
            "expected_output": "program=notifu64.exe\nargc=5\nargv[0]=-m\nargv[1]=body\nargv[2]=-p\nargv[3]=title\nargv[4]=-q\n"
        },
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"notifier\":\"notifu\",\"options\":{\"message\":\"body\"}}",
            "expected_output": "program=notifu64.exe\nargc=5\nargv[0]=-m\nargv[1]=body\nargv[2]=-q\nargv[3]=-p\nargv[4]=Node Notification:\n"
        },
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"notifier\":\"notifu\",\"options\":{\"message\":\"some \\\"me'ss`age`\\\"\"}}",
            "expected_output": "program=notifu64.exe\nargc=5\nargv[0]=-m\nargv[1]=some \"me'ss`age`\"\nargv[2]=-q\nargv[3]=-p\nargv[4]=Node Notification:\n"
        }
    ]
}
```

*4.3 Quiet flag toggling*

The `-q` flag is present by default; requesting sound or explicitly disabling quiet mode removes it.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_notifu_quiet_toggle.json`

```json
{
    "description": "Controls the silent/quiet ('-q') flag on the Windows notifier. By default '-q' is present; requesting sound or explicitly disabling quiet mode removes the '-q' flag from the argument vector. Output reports the program, argument count, and each argument.",
    "cases": [
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"notifier\":\"notifu\",\"options\":{\"message\":\"body\",\"sound\":true}}",
            "expected_output": "program=notifu64.exe\nargc=4\nargv[0]=-m\nargv[1]=body\nargv[2]=-p\nargv[3]=Node Notification:\n"
        },
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"notifier\":\"notifu\",\"options\":{\"message\":\"body\",\"quiet\":false}}",
            "expected_output": "program=notifu64.exe\nargc=4\nargv[0]=-m\nargv[1]=body\nargv[2]=-p\nargv[3]=Node Notification:\n"
        }
    ]
}
```

*4.4 Duration, explicit-true booleans, dropped options*

A duration value becomes `-d <ms>`; a `true` boolean is emitted as a bare flag, a `false` boolean is omitted; unsupported options are dropped.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_notifu_flags_and_time.json`

```json
{
    "description": "Maps display-duration and extra flags onto the Windows notifier vector. A 'time' value becomes a '-d <ms>' duration flag. Boolean flags follow explicit-true semantics: a true boolean ('w') is emitted as a bare '-w' flag, while a false boolean is omitted entirely. Unsupported options are dropped. Output reports the program, argument count, and each argument.",
    "cases": [
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"notifier\":\"notifu\",\"options\":{\"title\":\"title\",\"message\":\"body\",\"time\":\"1000\"}}",
            "expected_output": "program=notifu64.exe\nargc=7\nargv[0]=-m\nargv[1]=body\nargv[2]=-p\nargv[3]=title\nargv[4]=-d\nargv[5]=1000\nargv[6]=-q\n"
        },
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"notifier\":\"notifu\",\"options\":{\"title\":\"title\",\"message\":\"body\",\"d\":\"1000\",\"icon\":\"icon\",\"w\":false}}",
            "expected_output": "program=notifu64.exe\nargc=9\nargv[0]=-d\nargv[1]=1000\nargv[2]=-i\nargv[3]=icon\nargv[4]=-m\nargv[5]=body\nargv[6]=-p\nargv[7]=title\nargv[8]=-q\n"
        },
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"notifier\":\"notifu\",\"options\":{\"title\":\"title\",\"message\":\"body\",\"d\":\"1000\",\"icon\":\"icon\",\"w\":true}}",
            "expected_output": "program=notifu64.exe\nargc=10\nargv[0]=-d\nargv[1]=1000\nargv[2]=-w\nargv[3]=-i\nargv[4]=icon\nargv[5]=-m\nargv[6]=body\nargv[7]=-p\nargv[8]=title\nargv[9]=-q\n"
        },
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"notifier\":\"notifu\",\"options\":{\"title\":\"title\",\"message\":\"body\",\"tullball\":\"notValid\"}}",
            "expected_output": "program=notifu64.exe\nargc=5\nargv[0]=-m\nargv[1]=body\nargv[2]=-p\nargv[3]=title\nargv[4]=-q\n"
        }
    ]
}
```

---

### Feature 5: macOS Notifier — Flagged Argument Vector with Escaping

**As a developer**, I want the macOS backend to render every option as a named flag with a safely-escaped value, including pass-through of arbitrary keys, so I can supply ad-hoc options without the backend rejecting them.

**Expected Behavior / Usage:**

The macOS backend emits each option as a `-<key>` flag immediately followed by its double-quote-wrapped value. Unlike the other [a specific list of backend identifiers — see backend registry for exact names] it does not filter to a fixed allow-list: arbitrary/non-sensical keys are passed through as flags rather than rejected. Embedded double quotes in any value are backslash-escaped before wrapping. Output reports `program`, `argc`, and each `argv[i]`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_mac_[a specific list of backend identifiers — see backend registry for exact names]_passthrough_escape.json`

```json
{
    "description": "Builds the argument vector for the macOS notifier. Every option becomes a '-<key>' flag followed by its double-quote-wrapped value (including non-sensical/unsupported keys, which are passed through rather than rejected). Embedded double quotes inside title and message are backslash-escaped. Output reports the program, argument count, and each argument.",
    "cases": [
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"notifier\":\"terminal-notifier\",\"options\":{\"title\":\"title\",\"message\":\"body\",\"tullball\":\"notValid\"}}",
            "expected_output": "program=terminal-notifier\nargc=6\nargv[0]=-title\nargv[1]=\"title\"\nargv[2]=-message\nargv[3]=\"body\"\nargv[4]=-tullball\nargv[5]=\"notValid\"\n"
        },
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"notifier\":\"terminal-notifier\",\"options\":{\"title\":\"title \\\"message\\\"\",\"message\":\"body \\\"message\\\"\",\"tullball\":\"notValid\"}}",
            "expected_output": "program=terminal-notifier\nargc=6\nargv[0]=-title\nargv[1]=\"title \\\"message\\\"\"\nargv[2]=-message\nargv[3]=\"body \\\"message\\\"\"\nargv[4]=-tullball\nargv[5]=\"notValid\"\n"
        }
    ]
}
```

---

### Feature 6: Request Validation

**As a developer**, I want a request that lacks the required message to be rejected with a clear, modeled error and no command dispatched, so I get a predictable failure instead of an empty or malformed notification.

**Expected Behavior / Usage:**

Before any command is constructed, a request is [a specific list of backend identifiers — see backend registry for exact names]d. A request without a message is rejected with the neutral error category `message_required`, and nothing is dispatched. A request that includes a message passes validation, reported as `error=none`. This rule is uniform across [a specific list of backend identifiers — see backend registry for exact names]. Output is a single `error=<category>` line.

**Test Cases:** `rcb_tests/public_test_cases/feature6_message_required_validation.json`

```json
{
    "description": "Validates a notification request before dispatch: a request without a message is rejected with the neutral error category 'message_required' and no command is dispatched, while a request that includes a message passes validation ('error=none'). The same rule holds across [a specific list of backend identifiers — see backend registry for exact names]. Output is a single 'error=<category>' line.",
    "cases": [
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"notifier\":\"notify-send\",\"options\":{}}",
            "expected_output": "error=message_required\n"
        },
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"notifier\":\"notifu\",\"options\":{}}",
            "expected_output": "error=message_required\n"
        },
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"notifier\":\"notify-send\",\"options\":{\"message\":\"body\"}}",
            "expected_output": "error=none\n"
        }
    ]
}
```

---

### Feature 7: Network-Push Notifier — Server Host/Port Configuration

**As a developer**, I want to point the network-push backend at a specific server host and port at construction time and have those values reach the underlying transport when I send, so I can deliver notifications to a remote or non-default endpoint.

**Expected Behavior / Usage:**

The network-push backend accepts an optional server host and port when constructed. When a notification is sent, those values are forwarded to the underlying push transport; if they were not supplied they remain unset. The application name defaults to a fixed value when not overridden. The rendered output reports the effective `appname`, `host`, and `port` the transport will use, with `<unset>` shown when a value was not provided.

**Test Cases:** `rcb_tests/public_test_cases/feature7_growl_host_port.json`

```json
{
    "description": "Configures the network-push (GNTP) backend with an overridable server host and port supplied at construction time, then forwards those values to the underlying push transport when sending. When host/port are provided they appear on the transport; when omitted they remain unset. The application name defaults to 'Node'. Output reports the effective appname, host, and port the transport will use.",
    "cases": [
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"constructor\":{\"host\":\"foo\",\"port\":\"bar\"},\"options\":{\"message\":\"foo\",\"wait\":true}}",
            "expected_output": "appname=Node\nhost=foo\nport=bar\n"
        },
        {
            "input": "{\"op\":\"[a specific list of backend identifiers — see backend registry for exact names]\",\"constructor\":{},\"options\":{\"message\":\"foo\",\"wait\":true}}",
            "expected_output": "appname=Node\nhost=<unset>\nport=<unset>\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured notification library implementing the features above — per-backend option normalization, argument-vector construction, executable/architecture selection, request validation, and backend registry/selection — organized into a multi-file tree that separates the shared option/argument logic from each backend wrapper and from the process-dispatch boundary. Its structure must align with the "Scale-Driven Code Organization" constraint without over-engineering.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads one JSON command from stdin, invokes the appropriate core logic (option [a specific list of backend identifiers — see backend registry for exact names]ping, argument construction, validation, host/port configuration, or registry query), and prints the result to stdout, strictly matching the per-leaf-feature contracts above. The adapter is responsible for substituting the process-dispatch boundary so it can observe the exact program + argument vector that would be dispatched, and for translating any thrown native errors into the neutral `error=<category>` lines. It must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_backend_registry.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_backend_registry@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- align with the standard action identification pattern used elsewhere in the engine
