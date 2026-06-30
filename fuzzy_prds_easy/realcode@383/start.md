## Product Requirement Document

# Interactive Code Playground Toolkit - Foundation Library for a Browser-Based Code Editor

## Project Goal

Build the client-side foundation library that powers an interactive, browser-based code playground — the kind of environment where a reader opens a page, sees an editable program, modifies it, and runs it against a remote execution service. This library is not the editor UI and not the execution backend; it is the middle layer everything else depends on. It allows developers to load shareable code documents from many remote sources, split authored exercise blobs into named files, track unsaved edits, map between text offsets and line numbers, react to value changes through lightweight bindings, and reach shared services through a scoped registry — all behind small, deterministic, externally-observable contracts.

---

## Background & Problem

Without this library, every team building a web code playground re-implements the same fragile plumbing: ad-hoc HTTP calls to fetch documents from several different remote sources (each with its own URL shape and failure modes), brittle hand-written string splitting to break authored exercises into files, scattered "is this modified?" flags sprinkled through the UI, and one-off arithmetic to convert between cursor offsets and line numbers. The result is repetitive, error-prone boilerplate where each remote source leaks a different failure shape, malformed input crashes the page, and editor state drifts out of sync with what was loaded.

With this library, those concerns become a handful of crisp primitives with stable, language-neutral contracts. Documents load through a single predictable set of outcomes regardless of source; authored blobs split cleanly into named files or fail with a normalized reason; edits are reversible and observably "dirty" or "clean"; positions, bindings, and a scoped service registry are reusable building blocks. Every behavior is a pure function of its inputs, reproducible offline, so the rest of the playground can be built on top with confidence.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility library (position math, snippet parsing, token parsing, HTML extraction, reactive bindings, a scoped registry, remote loading over HTTP, and an editable document model). It MUST NOT be a single "god file". Output a clear directory tree separating each responsibility into its own cohesive unit, plus a separate execution adapter. Do not over-engineer the simple primitives, but keep the remote-loading and document-model concerns physically separated from the pure utilities.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in the "Core Features" section are a black-box contract for the execution adapter, NOT the internal data model. The core logic must remain completely decoupled from stdin/stdout and JSON parsing. The execution adapter is the only component that knows about JSON commands and the line-oriented text output; it translates each command into idiomatic calls to the core and renders the result.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Parsing, routing, validation, core execution, and output formatting live in distinct units.
   - **Open/Closed Principle (OCP):** New remote-source kinds or new command actions can be added without modifying existing core behavior.
   - **Liskov Substitution Principle (LSP):** A stream source and a property source must be interchangeable wherever a binding source is expected; a property target and a callback target must be interchangeable wherever a binding target is expected.
   - **Interface Segregation Principle (ISP):** The observable-value interface (read current value, set value, observe changes) stays small and cohesive.
   - **Dependency Inversion Principle (DIP):** Remote loading depends on an injected HTTP client abstraction, never on a concrete network implementation, so it can be driven by an in-memory fixture.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public surface must be elegant and idiomatic to the target language, hiding internal complexity.
   - **Resilience:** Edge cases (empty buffers, marker-less blobs, malformed HTML, unbalanced markers, missing/over-quota remote content, malformed metadata) are handled gracefully. Errors are modeled as proper typed failures internally.
   - **Determinism:** No wall-clock time, randomness, global mutable state, or real network access may influence outputs. Remote loading is exercised against an in-process HTTP stub returning fixed fixtures keyed by request URL, so a given input always yields the same output.
   - **Normalized, language-neutral errors:** No host-language exception type names, runtime message suffixes, or object-repr renderings may appear in output. All failures surface as stable category tokens (e.g. `error=snippet_parse` with a `reason=` field, or `error=content_not_found`). The adapter's render layer performs this normalization; the core may throw idiomatic exceptions internally.
   - **Observable protocol:** Remote-loading outputs must surface the exact request URL and HTTP status code that drove the outcome, in addition to the loaded content or error category, so a stub that bypasses the HTTP boundary cannot pass.
   - **Output discipline:** Outputs are deterministic, line-oriented text — each line is `key=value` or `key=value value` (paired rows). Trailing newlines are significant. No PASS/FAIL or diagnostic words ever appear in program output.

---

## Core Features

### Feature 1: Text position mapping

**As a developer**, I want to convert between absolute character offsets and zero-based line numbers over a text buffer, so I can place cursors and highlights consistently between the editor and the underlying text.

**Expected Behavior / Usage:**

*1.1 Offset to line — resolve a character offset to the line that contains it.*

Given a (possibly multi-line) source string and a list of absolute character offsets, resolve each offset to the zero-based line that contains it. An offset lands on the line whose half-open `[start, nextStart)` range contains it; offsets at or beyond the final line resolve to the last line. An empty buffer resolves every offset to line `0`. The output emits one `offset=<o> line=<l>` row per requested offset.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_offset_to_line.json`

```json
{
    "description": "Maps absolute character offsets within a text buffer to their zero-based line numbers. The input is a multi-line source string and a list of character offsets; each offset is resolved to the line that contains it. Offsets at or beyond the final newline resolve to the last line, and an empty buffer resolves every offset to line zero.",
    "cases": [
        {
            "input": {
                "action": "line_for_offset",
                "source": "one\ntwo\nthree",
                "offsets": [0, 3, 4, 7, 8, 13]
            },
            "expected_output": "offset=0 line=0\noffset=3 line=0\noffset=4 line=1\noffset=7 line=1\noffset=8 line=2\noffset=13 line=2\n"
        },
        {
            "input": {
                "action": "line_for_offset",
                "source": "",
                "offsets": [0, 1]
            },
            "expected_output": "offset=0 line=0\noffset=1 line=0\n"
        }
    ]
}
```

*1.2 Line to offset — resolve a line number to the offset where it begins.*

Given a source string and a list of zero-based line numbers, resolve each line to the absolute character offset where that line begins. A line number beyond the last line clamps to the start offset of the last line. An empty buffer maps every line to offset `0`. The output emits one `line=<l> offset=<o>` row per requested line.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_line_to_offset.json`

```json
{
    "description": "Maps zero-based line numbers to the absolute character offset where each line begins. The input is a multi-line source string and a list of line numbers; line numbers beyond the last line clamp to the start offset of the last line, and an empty buffer maps every line to offset zero.",
    "cases": [
        {
            "input": {
                "action": "offset_for_line",
                "source": "one\ntwo\nthree",
                "lines": [0, 1, 2, 3]
            },
            "expected_output": "line=0 offset=0\nline=1 offset=4\nline=2 offset=8\nline=3 offset=8\n"
        },
        {
            "input": {
                "action": "offset_for_line",
                "source": "",
                "lines": [0, 1]
            },
            "expected_output": "line=0 offset=0\nline=1 offset=0\n"
        }
    ]
}
```

---

### Feature 2: Authored snippet parsing into named files

**As a developer**, I want to split a single authored exercise blob into named virtual files, so I can store a multi-file exercise as one text block and reconstruct its files on load.

**Expected Behavior / Usage:**

*2.1 Delimited multi-file snippet — split a blob with begin/end markers.*

Files are delimited by inline markers of the form `{$ begin <name> $}` and `{$ end <name> $}`. Captured file bodies are emitted in declaration order; each captured body ends with a trailing newline. The output emits, for each file, a `file=<name>` line followed by that file's body.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_delimited_files.json`

```json
{
    "description": "Parses a snippet that declares several named virtual files using begin/end markers of the form '{$ begin <name> $}' ... '{$ end <name> $}'. The output is the set of file names and their contents in declaration order; each captured file body is terminated with a trailing newline.",
    "cases": [
        {
            "input": {
                "action": "parse_snippet",
                "source": "{$ begin main.dart $}\nString message = 'Hello, World!';\n{$ end main.dart $}\n\n{$ begin solution.dart $}\nString message = 'delete your code';\n{$ end solution.dart $}\n\n{$ begin test.dart $}\nmain() => print(message);\n{$ end test.dart $}\n"
            },
            "expected_output": "file=main.dart\nString message = 'Hello, World!';\n\nfile=solution.dart\nString message = 'delete your code';\n\nfile=test.dart\nmain() => print(message);\n\n"
        }
    ]
}
```

*2.2 Marker-less snippet — treat an unmarked blob as a single default file.*

A snippet containing no markers is treated as a single default file named `main.dart` whose content is the input with surrounding whitespace trimmed. The output emits a single `file=main.dart` line followed by the trimmed content.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_plain_snippet.json`

```json
{
    "description": "Parses a snippet that contains no begin/end markers. The whole input is treated as a single default file named main.dart whose content is the input with surrounding whitespace trimmed.",
    "cases": [
        {
            "input": {
                "action": "parse_snippet",
                "source": "main() => print('Hello, World!');\n"
            },
            "expected_output": "file=main.dart\nmain() => print('Hello, World!');\n"
        }
    ]
}
```

*2.3 Unbalanced markers — reject a structurally broken marker sequence.*

A snippet whose markers are unbalanced — for example a new begin marker appearing before the previous file was closed — fails with a normalized error. The output is `error=snippet_parse` followed by a `reason=` token identifying the structural problem (e.g. `unexpected_begin`).

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_invalid_markers.json`

```json
{
    "description": "Rejects a snippet whose begin/end markers are unbalanced (for example a new begin marker appearing before the previous file was closed). The parse fails with a normalized error category identifying the kind of structural problem.",
    "cases": [
        {
            "input": {
                "action": "parse_snippet",
                "source": "{$ begin main.dart $}\nString message = 'Hello, World!';\n{$ end main.dart $}\n\n{$ begin solution.dart $}\nString message = 'delete your code';\n{$ begin main.dart $}\n"
            },
            "expected_output": "error=snippet_parse\nreason=unexpected_begin\n"
        }
    ]
}
```

---

### Feature 3: Embed-token interpretation

**As a developer**, I want to interpret a marker token that both activates an embedded playground and carries its configuration, so I can drive embed behavior from a single string written in the host document.

**Expected Behavior / Usage:**

*3.1 Activation check — decide whether a token activates an embed.*

A token is valid when it contains the activation keyword, optionally preceded by a leading prefix. A token referencing a different, unrelated keyword is rejected. The output is a single `valid=<bool>` line.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_class_validity.json`

```json
{
    "description": "Decides whether a marker token activates the embeddable playground. A token is valid when it contains the activation keyword (optionally with a leading prefix); a token referencing a different, unrelated keyword is rejected.",
    "cases": [
        {
            "input": {"action": "css_options", "token": "run-dartpad"},
            "expected_output": "valid=true\n"
        },
        {
            "input": {"action": "css_options", "token": "language-run-dartpad"},
            "expected_output": "valid=true\n"
        },
        {
            "input": {"action": "css_options", "token": "run-flutterpad"},
            "expected_output": "valid=false\n"
        }
    ]
}
```

*3.2 Option extraction — parse colon-delimited options from a valid token.*

A valid token may carry colon-delimited `key-value` options (display mode, theme, run flag, split, width, height, analytics id, and similar). Values may contain characters such as percent signs and unit suffixes. The output emits `valid=true` followed by one `<key>=<value>` line per parsed option, with keys sorted alphabetically.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_class_options.json`

```json
{
    "description": "Extracts colon-delimited key-value options from a valid marker token. Each option is written as 'key-value'; the output lists every parsed option (keys sorted) together with the validity flag. Values may include characters such as percent signs and units.",
    "cases": [
        {
            "input": {
                "action": "css_options",
                "token": "run-dartpad:mode-html:theme-dark:run-true:split-50:width-100%:height-400px:ga_id-example1"
            },
            "expected_output": "valid=true\n[a list of forbidden keys to prevent overriding system state — review security policy for the complete exclusion set]example1\n[a list of forbidden keys to prevent overriding system state — review security policy for the complete exclusion set]400px\n[a list of forbidden keys to prevent overriding system state — review security policy for the complete exclusion set]html\n[a list of forbidden keys to prevent overriding system state — review security policy for the complete exclusion set]true\n[a list of forbidden keys to prevent overriding system state — review security policy for the complete exclusion set]50\n[a list of forbidden keys to prevent overriding system state — review security policy for the complete exclusion set]dark\n[a list of forbidden keys to prevent overriding system state — review security policy for the complete exclusion set]100%\n"
        }
    ]
}
```

---

### Feature 4: HTML body extraction

**As a developer**, I want to extract the inner content of an HTML document's body region, so I can render only the meaningful markup of a shared HTML document without its surrounding boilerplate.

**Expected Behavior / Usage:**

A well-formed document yields its trimmed body content. A document with no body region yields empty content. Input that is not a full HTML document is returned unchanged. Malformed closing tags inside the body are preserved verbatim. The output emits `len=<n>` (the character length of the extracted content) followed by the content itself when non-empty.

**Test Cases:** `rcb_tests/public_test_cases/feature4_extract_html_body.json`

```json
{
    "description": "Extracts the inner content of the body region from an HTML document. Well-formed documents yield the trimmed body content; documents without a body region yield empty content; input that is not a full HTML document is returned unchanged; malformed closing tags inside the body are preserved. The output reports the length of the extracted content followed by the content itself.",
    "cases": [
        {
            "input": {"action": "extract_html_body", "html": ""},
            "expected_output": "len=0\n"
        },
        {
            "input": {"action": "extract_html_body", "html": "<html><body><h1>Hello World!</h1></body></html>"},
            "expected_output": "len=21\n<h1>Hello World!</h1>\n"
        },
        {
            "input": {"action": "extract_html_body", "html": "<html><head><title>Hello World!</title></head></html>"},
            "expected_output": "len=0\n"
        },
        {
            "input": {"action": "extract_html_body", "html": "Hello World!"},
            "expected_output": "len=12\nHello World!\n"
        },
        {
            "input": {"action": "extract_html_body", "html": "<html><body><h1>Hello World!</h1></XXX></body></html>"},
            "expected_output": "len=27\n<h1>Hello World!</h1></XXX>\n"
        }
    ]
}
```

---

### Feature 5: Reactive value bindings

**As a developer**, I want to propagate value changes from a source to a target through a cancellable binding, so I can keep UI and model values in sync without writing manual listener wiring.

**Expected Behavior / Usage:**

A source may be a value stream or an observable property; a target may be an observable property or a callback. Each value produced by the source is delivered to the target. An explicit flush delivers the source's current value immediately (relevant for property sources). The output reports the target's final `value=<v>` and its `updates=<count>`.

*5.1 Stream source — propagate each value pushed onto a stream.*

Each value pushed onto the source stream is delivered to the target property; the update count equals the number of values pushed.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_stream_source.json`

```json
{
    "description": "Binds a value stream to a target so that each value pushed onto the stream is propagated to the target. The output reports the latest value received by the target and how many times the target was updated.",
    "cases": [
        {
            "input": {"action": "bind", "source_type": "stream", "target_type": "property", "events": ["foo"]},
            "expected_output": "value=foo\nupdates=1\n"
        },
        {
            "input": {"action": "bind", "source_type": "stream", "target_type": "property", "events": ["foo", "bar"]},
            "expected_output": "value=bar\nupdates=2\n"
        }
    ]
}
```

*5.2 Property-to-property — mirror one observable property onto another.*

Binding a source property to a target property mirrors the source's value onto the target; an explicit flush pushes the source's current value immediately, producing one update.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_property_source.json`

```json
{
    "description": "Binds one observable property to another so that changes in the source are mirrored on the target. An explicit flush pushes the source's current value to the target immediately. The output reports the target's final value and its update count.",
    "cases": [
        {
            "input": {"action": "bind", "source_type": "property", "target_type": "property", "initial": "foo", "flush": true, "events": []},
            "expected_output": "value=foo\nupdates=1\n"
        }
    ]
}
```

*5.3 Callback target — deliver values to a callback function.*

Binding a source property to a callback target delivers the value to the callback; an explicit flush invokes the callback with the source's current value, producing one update.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_function_target.json`

```json
{
    "description": "Binds an observable property to a callback target so that the property's value is delivered to the callback. An explicit flush invokes the callback with the source's current value. The output reports the value received by the callback and how many times it was invoked.",
    "cases": [
        {
            "input": {"action": "bind", "source_type": "property", "target_type": "function", "initial": "foo", "flush": true, "events": []},
            "expected_output": "value=foo\nupdates=1\n"
        }
    ]
}
```

*5.4 Cancellation — stop propagation after cancel.*

Cancelling a binding stops further propagation: values produced before the cancellation are delivered, values produced after it are ignored. With a `cancel_after` index, only events before that index reach the target.

**Test Cases:** `rcb_tests/public_test_cases/feature5_4_cancel.json`

```json
{
    "description": "Cancels an active binding so that further source changes are no longer propagated to the target. Changes emitted before cancellation are delivered; changes emitted after cancellation are ignored. The output reports the target's final value and update count.",
    "cases": [
        {
            "input": {"action": "bind", "source_type": "property", "target_type": "property", "events": ["foo", "bar"], "cancel_after": 1},
            "expected_output": "value=foo\nupdates=1\n"
        }
    ]
}
```

---

### Feature 6: Scoped service registry

**As a developer**, I want a registry that stores a single value per type key and is reachable only inside a dynamically scoped execution region, so I can share services within a region without global singletons leaking outside it.

**Expected Behavior / Usage:**

*6.1 Register and retrieve — store and look up a value by type key.*

Looking up a type before anything is registered yields nothing; after registering a value it is retrievable by the same type key. The output reports the lookup result before and after registration (`before=...`, `after=...`), with absence rendered as `null`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_retrieve.json`

```json
{
    "description": "A scoped registry that stores a single value per type key. Looking up a type before anything is registered yields nothing; after registering a value it can be retrieved by the same type key. The output reports the lookup result before and after registration.",
    "cases": [
        {
            "input": {"action": "dep_retrieve", "value": "foo"},
            "expected_output": "before=null\nafter=foo\n"
        }
    ]
}
```

*6.2 Scoped ambient instance — expose the registry only inside its region.*

Outside any region the ambient instance is absent; while running inside the scoped region the registry becomes the ambient instance and its registered values are visible; after the region exits the ambient instance is absent again. The output reports the ambient-instance state and the visible value at each phase.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_scoped_zone.json`

```json
{
    "description": "Exposes the active registry only within a dynamically scoped execution region. Outside any region the ambient instance is absent; while running inside the region the registry's instance becomes the ambient one and its registered values are visible; after the region exits the ambient instance is absent again.",
    "cases": [
        {
            "input": {"action": "dep_zone", "value": "foo"},
            "expected_output": "outside_instance=absent\nbefore_zone_instance=absent\ninside_instance=present\ninside_value=foo\nafter_instance=absent\n"
        }
    ]
}
```

---

### Feature 7: Remote document loading over an HTTP boundary

**As a developer**, I want to load shareable code documents from several remote sources behind one predictable set of outcomes, so the UI sees the same shape — request URL, HTTP status, and either content or a normalized error — regardless of which source was used.

**Expected Behavior / Usage:**

Every remote-loading result surfaces the exact request URL and the HTTP status code that drove the outcome. Failures are reported as normalized categories: `content_not_found` (missing content, status 404), `rate_limit_exceeded` (over-quota response, status 403), and `invalid_exercise_metadata` (a descriptor that is malformed or incomplete).

*7.1 Load by identifier — fetch a saved document by a short id.*

A valid identifier returns the document and its primary file content (`main.dart=<content>`). An unknown identifier maps to `content_not_found`; an over-quota response maps to `rate_limit_exceeded`. The output reports `request=<url>`, `status=<code>`, and either the primary file content or the error category.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_load_by_id.json`

```json
{
    "description": "Loads a saved code document by its identifier over an HTTP boundary. A valid identifier returns the document and its primary file content; an unknown identifier and an over-quota response are surfaced as normalized error categories. The output reports the requested URL, the HTTP status observed, and either the primary file content or the error category.",
    "cases": [
        {
            "input": {"action": "load_gist", "id": "12345678901234567890123456789012"},
            "expected_output": "request=https://api.github.com/gists/12345678901234567890123456789012\nstatus=200\nmain.dart=This is some dart code!\n"
        },
        {
            "input": {"action": "load_gist", "id": "12345678901234567890123456789000"},
            "expected_output": "request=https://api.github.com/gists/12345678901234567890123456789000\nstatus=404\nerror=content_not_found\n"
        },
        {
            "input": {"action": "load_gist", "id": "12345678901234567890123456789012", "rate_limited": true},
            "expected_output": "request=https://api.github.com/gists/12345678901234567890123456789012\nstatus=403\nerror=rate_limit_exceeded\n"
        }
    ]
}
```

*7.2 Load by sample id — fetch a documentation sample from the samples endpoint.*

A valid sample id fetches a single primary file from the samples endpoint and reports its content length (`main.dart.length=<n>`). An unknown sample maps to `content_not_found`; an over-quota response maps to `rate_limit_exceeded`. The output reports `request=<url>`, `status=<code>`, and either the length or the error category.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_load_by_sample.json`

```json
{
    "description": "Loads a documentation code sample by its sample identifier from the samples endpoint. A valid sample returns a single primary file; an unknown sample is surfaced as a normalized not-found category. The output reports the requested URL, the HTTP status, and either the primary file length or the error category.",
    "cases": [
        {
            "input": {"action": "load_sample", "id": "material.AppBar.1"},
            "expected_output": "request=https://api.flutter.dev/snippets/material.AppBar.1.dart\nstatus=200\nmain.dart.length=255\n"
        },
        {
            "input": {"action": "load_sample", "id": "material.WunderWidget.1"},
            "expected_output": "request=https://api.flutter.dev/snippets/material.WunderWidget.1.dart\nstatus=404\nerror=content_not_found\n"
        },
        {
            "input": {"action": "load_sample", "id": "material.AppBar.1", "rate_limited": true},
            "expected_output": "request=https://api.flutter.dev/snippets/material.AppBar.1.dart\nstatus=403\nerror=rate_limit_exceeded\n"
        }
    ]
}
```

*7.3 Load multi-file exercise from a repository — descriptor-driven fetch.*

Loading from a repository first fetches a metadata descriptor (`dartpad_metadata.yaml` under the given path) and then fetches each listed file. The descriptor supplies the exercise name and the file list. An optional branch reference is appended to every request as a `?ref=<branch>` query. A file may declare an alternate path used to fetch its content while keeping its logical name. The output reports the first requested URL (the descriptor URL), the HTTP status, the exercise `description=<name>`, and the content of a selected file (`<name>=<content>`, defaulting to `main.dart`).

**Test Cases:** `rcb_tests/public_test_cases/feature7_3_load_from_repo.json`

```json
{
    "description": "Loads a multi-file exercise from a source repository by first fetching a metadata descriptor and then fetching each listed file. The descriptor supplies the exercise name and the file list; an optional branch reference is appended to every request. A file may declare an alternate path that is used to fetch its content while keeping its logical name. The output reports the first requested URL, the HTTP status, the exercise name, and the content of a selected file.",
    "cases": [
        {
            "input": {"action": "load_repo", "owner": "owner", "repo": "repo", "path": "basic"},
            "expected_output": "request=https://api.github.com/repos/owner/repo/contents/basic/dartpad_metadata.yaml\nstatus=200\ndescription=A Dart Exercise\nmain.dart=this is main.dart\n"
        },
        {
            "input": {"action": "load_repo", "owner": "owner", "repo": "repo", "path": "alt_branch", "ref": "some_branch"},
            "expected_output": "request=https://api.github.com/repos/owner/repo/contents/alt_branch/dartpad_metadata.yaml?ref=some_branch\nstatus=200\ndescription=A Dart Exercise\nmain.dart=this is main.dart\n"
        },
        {
            "input": {"action": "load_repo", "owner": "owner", "repo": "repo", "path": "alternate_path", "file": "test.dart"},
            "expected_output": "request=https://api.github.com/repos/owner/repo/contents/alternate_path/dartpad_metadata.yaml\nstatus=200\ndescription=A Dart Exercise\ntest.dart=this is test.dart\n"
        },
        {
            "input": {"action": "load_repo", "owner": "owner", "repo": "repo", "path": "unnecessary_file", "file": "unnecessary.txt"},
            "expected_output": "request=https://api.github.com/repos/owner/repo/contents/unnecessary_file/dartpad_metadata.yaml\nstatus=200\ndescription=A Dart Exercise\nunnecessary.txt=this is unnecessary.txt\n"
        }
    ]
}
```

*7.4 Repository load errors — normalize descriptor and transport failures.*

When an exercise cannot be loaded, the result is a normalized category: a descriptor that is not valid structured data, or one missing its file list, mode, or name, or one pointing at a file that does not exist, all map to `invalid_exercise_metadata` (status 200, since the descriptor itself was fetched). A path whose descriptor does not exist maps to `content_not_found` (status 404). An over-quota response maps to `rate_limit_exceeded` (status 403). The output reports `request=<url>`, `status=<code>`, and the `error=<category>`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_4_repo_errors.json`

```json
{
    "description": "Surfaces normalized error categories when an exercise cannot be loaded: a descriptor that is not valid structured data, a descriptor missing its file list, mode, or name, a descriptor that points at a file which does not exist, a descriptor path that itself does not exist, and an over-quota response. The output reports the first requested URL, the HTTP status, and the normalized error category.",
    "cases": [
        {
            "input": {"action": "load_repo", "owner": "owner", "repo": "repo", "path": "invalid"},
            "expected_output": "request=https://api.github.com/repos/owner/repo/contents/invalid/dartpad_metadata.yaml\nstatus=200\nerror=invalid_exercise_metadata\n"
        },
        {
            "input": {"action": "load_repo", "owner": "owner", "repo": "repo", "path": "missing_files"},
            "expected_output": "request=https://api.github.com/repos/owner/repo/contents/missing_files/dartpad_metadata.yaml\nstatus=200\nerror=invalid_exercise_metadata\n"
        },
        {
            "input": {"action": "load_repo", "owner": "owner", "repo": "repo", "path": "does_not_exist"},
            "expected_output": "request=https://api.github.com/repos/owner/repo/contents/does_not_exist/dartpad_metadata.yaml\nstatus=404\nerror=content_not_found\n"
        },
        {
            "input": {"action": "load_repo", "owner": "owner", "repo": "repo", "path": "basic", "rate_limited": true},
            "expected_output": "request=https://api.github.com/repos/owner/repo/contents/basic/dartpad_metadata.yaml\nstatus=403\nerror=rate_limit_exceeded\n"
        }
    ]
}
```

---

### Feature 8: Editable document overlay and snapshots

**As a developer**, I want an editable overlay on a loaded code document that knows when it diverges from its backing document and can be snapshotted or copied, so the UI can show a "modified" indicator and persist edits as new immutable documents.

**Expected Behavior / Usage:**

*8.1 Dirty tracking — report divergence from the backing document.*

An editable overlay starts clean (`initial_dirty=false`). Changing a field makes it dirty (`after_change_dirty=true`). Restoring the field to its original value makes it clean again (`after_restore_dirty=false`). Adopting a new backing document also makes it clean (`after_set_backing_dirty=false`). The output reports the dirty flag after each step performed.

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_dirty_tracking.json`

```json
{
    "description": "An editable overlay on a code document that tracks whether it diverges from its backing document. It starts clean, becomes dirty after a field is changed, becomes clean again if the field is restored to its original value, and becomes clean when a new backing document is adopted. The output reports the dirty flag after each step.",
    "cases": [
        {
            "input": {"action": "gist_dirty", "description": "foo", "change": "bar"},
            "expected_output": "initial_dirty=false\nafter_change_dirty=true\n"
        },
        {
            "input": {"action": "gist_dirty", "description": "foo", "change": "bar", "restore": true},
            "expected_output": "initial_dirty=false\nafter_change_dirty=true\nafter_restore_dirty=false\n"
        },
        {
            "input": {"action": "gist_dirty", "description": "foo", "change": "bar", "set_backing": true},
            "expected_output": "initial_dirty=false\nafter_change_dirty=true\nafter_set_backing_dirty=false\n"
        }
    ]
}
```

*8.2 Snapshot edited state — produce a new immutable document.*

Snapshotting an edited overlay produces a fresh immutable document that captures the current edited field value. The output reports the field value carried into the newly created document (`description=<value>`).

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_create_gist.json`

```json
{
    "description": "Produces a new immutable code document that captures the current edited state of an editable overlay. The output reports the field value carried into the newly created document.",
    "cases": [
        {
            "input": {"action": "gist_create", "description": "foo", "change": "bar"},
            "expected_output": "description=bar\n"
        }
    ]
}
```

*8.3 Deep copy — clone a document preserving identity.*

Cloning a document produces an independent deep copy that preserves its identifier and description. The output reports the cloned document's `id=<id>` and `description=<value>`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_3_clone.json`

```json
{
    "description": "Creates an independent deep copy of a code document, preserving its identifier and description. The output reports the cloned document's identifier and description.",
    "cases": [
        {
            "input": {"action": "gist_clone", "id": "2342jh2jh3g4", "description": "test gist"},
            "expected_output": "id=2342jh2jh3g4\ndescription=test gist\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the eight features above, with each responsibility (position math, snippet parsing, embed-token parsing, HTML extraction, reactive bindings, scoped registry, remote loading, editable document model) in its own cohesive unit. Remote loading depends on an injected HTTP client abstraction so it can run offline against a fixture.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads a JSON command (with an `action` field) per case, invokes the appropriate core logic, normalizes any failure into a language-neutral `error=<category>` contract, and prints the line-oriented `key=value` result to stdout, strictly matching the per-leaf-feature contracts above. This adapter is logically and physically separated from the core domain and is the only component aware of JSON and stdout.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_offset_to_line.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_offset_to_line@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains only the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`. The remote-loading features are exercised against an in-process HTTP stub returning fixed fixtures keyed by request URL, so all outputs are reproducible offline.


---
**Implementation notes:**
- apply the same error classification used in the rate limiting module
