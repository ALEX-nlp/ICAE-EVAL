## Product Requirement Document

# Thread Stack Traceback Renderer — Mixed Python/Native Call-Stack Formatter

## Project Goal

Build a renderer that turns a captured snapshot of one thread's call stack — its Python-level frames, its native (C) frames, and a few runtime status flags — into a clean, human-readable traceback, so a developer inspecting a running or crashed program can read exactly where each thread was executing, across both the interpreter and native layers, in a single consistent layout.

---

## Background & Problem

A diagnostic tool that inspects a live process or a core dump produces, for each thread, two parallel views of the same call stack: a list of Python frames (each with a file, a function/scope name, a line, optional column range, optional source text, optional arguments and locals, and flags marking whether it is a call entry point or an internal placeholder), and a list of native frames (each with a symbol name, a file, a line and an originating library). It also knows a few thread-wide conditions: whether the thread holds the global interpreter lock, whether it is waiting for or releasing that lock, and whether it is collecting garbage.

Without a shared renderer, each consumer reinvents how to print this, leading to inconsistent layouts and — worst of all — no agreed rule for *reconciling* the native and Python views (the native stack re-enters the interpreter once per Python call, so the two must be interleaved carefully, with interpreter-internal frames suppressed). This component defines one contract: given a structured thread snapshot and a flag selecting plain-Python or merged-native output, emit the exact traceback text.

### Input Contract (shared wire format)

Every request is a single JSON object:

- `native` (boolean): when false, render only Python frames; when true, attempt to interleave native and Python frames.
- `thread` (object):
  - `tid` (integer): the thread identifier shown in the header.
  - `name` (string or null): an optional human label for the thread.
  - `holds_the_gil` (integer/boolean): whether the thread currently holds the global lock.
  - `is_gc_collecting` (integer/boolean): collection-state flag; `-1` means "unknown".
  - `python_version` (`[major, minor]` or null): used to recognize interpreter evaluation frames.
  - `python_frames` (array): outermost call first; each later frame is one level deeper (most recent call last). Each frame has `filename`, `function`, `lineno`, `end_lineno`, `column`, `end_column`, `is_entry` (whether it begins a real call, as opposed to an inlined continuation), `is_shim` (whether it is an internal placeholder frame), and optional `arguments` / `locals` maps and a `source` string (the full text of `filename`, used to show the relevant source line).
  - `native_frames` (array): innermost-to-outermost native frames, each with `symbol`, `file`, `line`, `library`.

All output is plain text (no terminal color codes). Each emitted line is terminated by a newline.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls to the core domain.

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

### Feature 1: Python-Only Stack Rendering

**As a developer**, I want a thread's Python call stack rendered as a readable traceback, so I can see which Python functions were on the stack without wading through interpreter internals.

**Expected Behavior / Usage:**

When native interleaving is not requested, the renderer ignores any native frames and prints only the Python view. The first line is always a header of the form `Traceback for thread <tid><name?> <status> (most recent call last):`, where `<name?>` is ` (name) ` when a thread name is present (and a single space otherwise) and `<status>` is a bracketed, comma-joined list of active conditions (empty brackets `[]` when none). Each rendered Python frame produces an indented line `    (Python) File "<filename>", line <lineno>, in <function>`. The whole block ends with a trailing blank line. The sub-features below specify the leaf behaviors.

*1.1 Basic Frame Listing — one line per Python frame, native frames ignored when not in merge mode*

The renderer emits the header, then one `(Python) File ...` line per frame in call order (outermost first, most recent last), then a trailing blank line. If native frames are supplied while `native` is false, they have no effect on the output.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_python_only_listing.json`

```json
{
    "description": "Render a thread's pure Python call stack (no native interleaving requested). The output starts with a header line naming the thread and its (possibly empty) status bracket, followed by one indented frame line per Python frame in call order (most recent call last), each naming the source file, the line number and the function, and ends with a trailing blank line. When native interleaving is not requested, any supplied native frames are ignored entirely.",
    "cases": [
        {
            "input": {"native": false, "thread": {"tid": 1, "name": null, "holds_the_gil": false, "is_gc_collecting": false, "python_version": [3, 8], "python_frames": [{"filename": "file1.py", "function": "function1", "lineno": 1, "end_lineno": 1, "column": 0, "end_column": 0, "is_entry": true, "is_shim": false}, {"filename": "file2.py", "function": "function2", "lineno": 2, "end_lineno": 2, "column": 0, "end_column": 0, "is_entry": true, "is_shim": false}, {"filename": "file3.py", "function": "function3", "lineno": 3, "end_lineno": 3, "column": 0, "end_column": 0, "is_entry": true, "is_shim": false}], "native_frames": []}},
            "expected_output": "Traceback for thread 1 [] (most recent call last):\n    (Python) File \"file1.py\", line 1, in function1\n    (Python) File \"file2.py\", line 2, in function2\n    (Python) File \"file3.py\", line 3, in function3[a specific trailing line break command — ask the PM for the exact adder]"
        }
    ]
}
```

*1.2 Empty Stack — explicit message when there are no Python frames*

When `native` is false and the thread has no Python frames, the renderer emits exactly one line stating that the frame stack for that thread id is empty (no header, no trailing blank line).

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_empty_stack.json`

```json
{
    "description": "When a thread has no Python frames and native interleaving is not requested, the formatter emits a single line stating that the frame stack for that thread id is empty.",
    "cases": [
        {
            "input": {"native": false, "thread": {"tid": 1, "name": null, "holds_the_gil": false, "is_gc_collecting": false, "python_version": [3, 8], "python_frames": [], "native_frames": []}},
            "expected_output": "The frame stack for thread 1 is empty\n"
        }
    ]
}
```

*1.3 Inline Source Line — show the source for a frame when its file content is available*

When a Python frame carries the text of its source file, the renderer prints, immediately beneath that frame's location line, an indented copy of the single source line at the frame's line number, stripped of surrounding whitespace. Column-range position information present on a frame does not alter the plain-text output: the full source line is shown regardless. Frames without source content show no extra line.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_inline_source.json`

```json
{
    "description": "When a Python frame's source file is available, the formatter prints the relevant source line, stripped of surrounding whitespace, on its own indented line beneath the frame's location line. The selected source line is the one at the frame's line number. Column-range position information present on a frame does not change the plain-text output: the full source line is shown regardless.",
    "cases": [
        {
            "input": {"native": false, "thread": {"tid": 1, "name": null, "holds_the_gil": false, "is_gc_collecting": false, "python_version": [3, 8], "python_frames": [{"filename": "file1.py", "function": "function1", "lineno": 1, "end_lineno": 1, "column": 0, "end_column": 0, "is_entry": true, "is_shim": false, "source": "x = \"This is the line 1\"\nx = \"This is the line 2\"\nx = \"This is the line 3\"\nx = \"This is the line 4\""}, {"filename": "file2.py", "function": "function2", "lineno": 2, "end_lineno": 2, "column": 0, "end_column": 0, "is_entry": true, "is_shim": false, "source": "x = \"This is the line 1\"\nx = \"This is the line 2\"\nx = \"This is the line 3\"\nx = \"This is the line 4\""}, {"filename": "file3.py", "function": "function3", "lineno": 3, "end_lineno": 3, "column": 0, "end_column": 0, "is_entry": true, "is_shim": false, "source": "x = \"This is the line 1\"\nx = \"This is the line 2\"\nx = \"This is the line 3\"\nx = \"This is the line 4\""}], "native_frames": []}},
            "expected_output": "Traceback for thread 1 [] (most recent call last):\n    (Python) File \"file1.py\", line 1, in function1\n        x = \"This is the line 1\"\n    (Python) File \"file2.py\", line 2, in function2\n        x = \"This is the line 2\"\n    (Python) File \"file3.py\", line 3, in function3\n        x = \"This is the line 3\"[a specific trailing line break command — ask the PM for the exact adder]"
        }
    ]
}
```

*1.4 Arguments and Locals — render a frame's captured arguments and local variables*

When a frame carries call arguments and/or local variables, the renderer adds, beneath that frame (after any source line), an `      Arguments:` header followed by one `        name: value` line per argument (only when at least one argument exists), then a `      Locals:` header followed by one `        name: value` line per local (only when at least one local exists). Argument values are rendered so that embedded control characters and newlines are escaped into a single visible line (e.g. a literal escape byte becomes the text `\x1b`, a newline becomes `\n`). A section with no entries is omitted entirely.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_arguments_and_locals.json`

```json
{
    "description": "When a Python frame carries call arguments and/or local variables, the formatter renders them beneath the frame: an 'Arguments:' header followed by one 'name: value' line per argument (when any arguments exist), then a 'Locals:' header followed by one 'name: value' line per local (when any locals exist). Argument values are rendered with non-printable and control characters escaped into a single visible line; a header section is omitted entirely when it has no entries.",
    "cases": [
        {
            "input": {"native": false, "thread": {"tid": 1, "name": null, "holds_the_gil": false, "is_gc_collecting": false, "python_version": [3, 8], "python_frames": [{"filename": "file1.py", "function": "function1", "lineno": 1, "end_lineno": 1, "column": 0, "end_column": 0, "is_entry": true, "is_shim": false, "arguments": {"the_argument": "some_value", "the_second_argument": "42"}, "locals": {"the_local": "some_other_value", "the_second_local": "7"}, "source": "x = \"This is the line 1\" or (1+1)\nx = \"This is the line 2\" or (1+1)\nx = \"This is the line 3\" or (1+1)\nx = \"This is the line 4\" or (1+1)"}], "native_frames": []}},
            "expected_output": "Traceback for thread 1 [] (most recent call last):\n    (Python) File \"file1.py\", line 1, in function1\n        x = \"This is the line 1\" or (1+1)\n      Arguments:\n        the_argument: some_value\n        the_second_argument: 42\n      Locals:\n        the_local: some_other_value\n        the_second_local: 7[a specific trailing line break command — ask the PM for the exact adder]"
        },
        {
            "input": {"native": false, "thread": {"tid": 1, "name": null, "holds_the_gil": false, "is_gc_collecting": false, "python_version": [3, 8], "python_frames": [{"filename": "file1.py", "function": "function1", "lineno": 1, "end_lineno": 1, "column": 0, "end_column": 0, "is_entry": true, "is_shim": false, "arguments": {"the_argument": "\u001b[6;30;42m some_value\nwith\nnewlines'\u001b[0m"}, "locals": {}, "source": "x = \"This is the line 1\" or (1+1)\nx = \"This is the line 2\" or (1+1)\nx = \"This is the line 3\" or (1+1)\nx = \"This is the line 4\" or (1+1)"}], "native_frames": []}},
            "expected_output": "Traceback for thread 1 [] (most recent call last):\n    (Python) File \"file1.py\", line 1, in function1\n        x = \"This is the line 1\" or (1+1)\n      Arguments:\n        the_argument: \\x1b[6;30;42m some_value[a specific escape sequence string — ask the PM for the exact macro]with[a specific escape sequence string — ask the PM for the exact macro]newlines'\\x1b[0m[a specific trailing line break command — ask the PM for the exact adder]"
        }
    ]
}
```

*1.5 Shim Frames Skipped — internal placeholder frames are omitted in plain mode*

In a pure Python listing, frames flagged as internal placeholders (`is_shim` true) are skipped entirely; only genuine Python frames are rendered, each with its source line when available.

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_shim_frames_skipped.json`

```json
{
    "description": "Internal placeholder ('shim') frames are not shown in a pure Python listing. Frames flagged as shim are skipped entirely, and only the genuine Python frames are rendered, each with its source line when available.",
    "cases": [
        {
            "input": {"native": false, "thread": {"tid": 1, "name": null, "holds_the_gil": false, "is_gc_collecting": false, "python_version": [3, 8], "python_frames": [{"filename": "file1.py", "function": "function1", "lineno": 1, "end_lineno": 1, "column": 0, "end_column": 3, "is_entry": true, "is_shim": false, "source": "x = \"This is the line 1\" or (1+1)\nx = \"This is the line 2\" or (1+1)\nx = \"This is the line 3\" or (1+1)\nx = \"This is the line 4\" or (1+1)"}, {"filename": "<shim>", "function": "<shim>", "lineno": 0, "end_lineno": 0, "column": 0, "end_column": 0, "is_entry": true, "is_shim": true}, {"filename": "file2.py", "function": "function2", "lineno": 2, "end_lineno": 2, "column": 4, "end_column": 25, "is_entry": true, "is_shim": false, "source": "x = \"This is the line 1\" or (1+1)\nx = \"This is the line 2\" or (1+1)\nx = \"This is the line 3\" or (1+1)\nx = \"This is the line 4\" or (1+1)"}, {"filename": "<shim>", "function": "<shim>", "lineno": 0, "end_lineno": 0, "column": 0, "end_column": 0, "is_entry": true, "is_shim": true}, {"filename": "file3.py", "function": "function3", "lineno": 3, "end_lineno": 3, "column": 28, "end_column": 33, "is_entry": true, "is_shim": false, "source": "x = \"This is the line 1\" or (1+1)\nx = \"This is the line 2\" or (1+1)\nx = \"This is the line 3\" or (1+1)\nx = \"This is the line 4\" or (1+1)"}, {"filename": "<shim>", "function": "<shim>", "lineno": 0, "end_lineno": 0, "column": 0, "end_column": 0, "is_entry": true, "is_shim": true}, {"filename": "file4.py", "function": "function4", "lineno": 4, "end_lineno": 4, "column": 60, "end_column": 45, "is_entry": true, "is_shim": false, "source": "x = \"This is the line 1\" or (1+1)\nx = \"This is the line 2\" or (1+1)\nx = \"This is the line 3\" or (1+1)\nx = \"This is the line 4\" or (1+1)"}], "native_frames": []}},
            "expected_output": "Traceback for thread 1 [] (most recent call last):\n    (Python) File \"file1.py\", line 1, in function1\n        x = \"This is the line 1\" or (1+1)\n    (Python) File \"file2.py\", line 2, in function2\n        x = \"This is the line 2\" or (1+1)\n    (Python) File \"file3.py\", line 3, in function3\n        x = \"This is the line 3\" or (1+1)\n    (Python) File \"file4.py\", line 4, in function4\n        x = \"This is the line 4\" or (1+1)[a specific trailing line break command — ask the PM for the exact adder]"
        }
    ]
}
```

---

### Feature 2: Thread Status Indicators

**As a developer**, I want the header to summarize the thread's runtime condition, so I can immediately tell which thread holds the lock or is collecting garbage.

**Expected Behavior / Usage:**

The header's bracket lists the active conditions, comma-joined, in this order: lock state, then collection state. Lock state is `Has the GIL` when the thread holds the global lock; otherwise `Waiting for the GIL` if its native stack is inside the lock-acquire routine, or `Dropping the GIL` if its native stack is inside the lock-release routine. Collection state is `Garbage collecting` when the native stack is inside a collection routine, or (when there are no native frames) when the collection flag is set while the thread holds the lock. With no active conditions the bracket is empty (`[]`). When multiple conditions hold, they appear together separated by commas.

**Test Cases:** `rcb_tests/public_test_cases/feature2_thread_status.json`

```json
{
    "description": "The header's status bracket reflects the thread's runtime condition. Holding the global lock yields a 'Has the GIL' marker. A native stack that is waiting to acquire the lock yields 'Waiting for the GIL'; one that is releasing it yields 'Dropping the GIL'. A native stack inside garbage collection, or the collection flag set while holding the lock, yields 'Garbage collecting'. Multiple active conditions are joined with commas inside the brackets.",
    "cases": [
        {
            "input": {"native": false, "thread": {"tid": 1, "name": null, "holds_the_gil": true, "is_gc_collecting": false, "python_version": [3, 8], "python_frames": [{"filename": "file1.py", "function": "function1", "lineno": 1, "end_lineno": 1, "column": 0, "end_column": 0, "is_entry": true, "is_shim": false}], "native_frames": []}},
            "expected_output": "Traceback for thread 1 [Has the GIL] (most recent call last):\n    (Python) File \"file1.py\", line 1, in function1[a specific trailing line break command — ask the PM for the exact adder]"
        },
        {
            "input": {"native": false, "thread": {"tid": 1, "name": null, "holds_the_gil": true, "is_gc_collecting": true, "python_version": [3, 8], "python_frames": [{"filename": "file1.py", "function": "function1", "lineno": 1, "end_lineno": 1, "column": 0, "end_column": 0, "is_entry": true, "is_shim": false}], "native_frames": []}},
            "expected_output": "Traceback for thread 1 [Has the GIL,Garbage collecting] (most recent call last):\n    (Python) File \"file1.py\", line 1, in function1[a specific trailing line break command — ask the PM for the exact adder]"
        }
    ]
}
```

---

### Feature 3: Merged Native / Python Rendering

**As a developer**, I want native and Python frames woven together into one stack, so I can follow control as it crosses between C and Python without losing context.

**Expected Behavior / Usage:**

When native interleaving is requested, the renderer first checks whether the two views can be reconciled: it counts the native frames that are interpreter *evaluation* frames (the per-Python-call re-entry into the interpreter, recognized from the symbol name in a manner that depends on the interpreter version) and the Python frames that are call entry points. If those counts match, it interleaves; otherwise it reports that the stacks could not be merged. Native frames are rendered as `    (C) File "<file>", line <line>, in <symbol> (<library>)`. The sub-features specify each leaf behavior.

*3.1 Unable To Merge — fall back when the two views cannot be reconciled*

When the count of native evaluation frames does not equal the count of Python entry frames, the renderer prints the header, then the line `[a specific merge failure fallback message — ask the PM for the exact literal string]`, then lists the Python frames (if any) exactly as in a plain listing, then a trailing blank line.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_unable_to_merge.json`

```json
{
    "description": "When native interleaving is requested but the native and Python stacks cannot be reconciled (the number of interpreter evaluation frames in the native stack does not match the number of entry-point Python frames), the formatter emits a notice that the native stack could not be merged, then falls back to listing the Python frames (if any) as in a plain listing.",
    "cases": [
        {
            "input": {"native": true, "thread": {"tid": 57005, "name": null, "holds_the_gil": false, "is_gc_collecting": false, "python_version": [2, 7], "python_frames": [], "native_frames": [{"symbol": "native_function1", "file": "native_file1.c", "line": 1, "library": "library.so"}, {"symbol": "PyEval_EvalFrameEx", "file": "Python/ceval.c", "line": 123, "library": "library.so"}, {"symbol": "native_function2", "file": "native_file2.c", "line": 2, "library": "library.so"}, {"symbol": "PyEval_EvalFrameEx", "file": "Python/ceval.c", "line": 123, "library": "library.so"}, {"symbol": "native_function3", "file": "native_file3.c", "line": 3, "library": "library.so"}, {"symbol": "PyEval_EvalFrameEx", "file": "Python/ceval.c", "line": 123, "library": "library.so"}, {"symbol": "native_function4", "file": "native_file4.c", "line": 4, "library": "library.so"}]}},
            "expected_output": "Traceback for thread 57005 [] (most recent call last):\n[a specific merge failure fallback message — ask the PM for the exact literal string][a specific trailing line break command — ask the PM for the exact adder]"
        }
    ]
}
```

*3.2 Native-Only Listing — render native frames directly when there are no Python frames*

When interleaving is requested for a thread that has native frames but no Python frames (and therefore no evaluation frames to reconcile), the renderer prints the header and one `(C) File ...` line per native frame, then a trailing blank line.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_native_only_listing.json`

```json
{
    "description": "When native interleaving is requested for a thread that has native frames but no Python frames, and there are no interpreter evaluation frames to reconcile, the native stack is rendered directly: one indented line per native frame naming its file, line, function and originating library.",
    "cases": [
        {
            "input": {"native": true, "thread": {"tid": 1, "name": null, "holds_the_gil": false, "is_gc_collecting": false, "python_version": [3, 8], "python_frames": [], "native_frames": [{"symbol": "native_function1", "file": "native_file1.c", "line": 1, "library": "library.so"}, {"symbol": "native_function2", "file": "native_file2.c", "line": 2, "library": "library.so"}, {"symbol": "native_function3", "file": "native_file3.c", "line": 3, "library": "library.so"}, {"symbol": "native_function4", "file": "native_file4.c", "line": 4, "library": "library.so"}]}},
            "expected_output": "Traceback for thread 1 [] (most recent call last):\n    (C) File \"native_file1.c\", line 1, in native_function1 (library.so)\n    (C) File \"native_file2.c\", line 2, in native_function2 (library.so)\n    (C) File \"native_file3.c\", line 3, in native_function3 (library.so)\n    (C) File \"native_file4.c\", line 4, in native_function4 (library.so)[a specific trailing line break command — ask the PM for the exact adder]"
        }
    ]
}
```

*3.3 Merged Interleave — weave native and Python frames in order*

When the views reconcile, the renderer walks the native frames in order: each interpreter evaluation frame is replaced by the next Python frame (rendered as a `(Python)` line); genuine native frames are rendered as `(C)` lines. The result alternates native and Python entries to show the full mixed stack. Multiple consecutive interpreter re-entry frames that correspond to a single Python call are collapsed so each Python call appears once.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_merged_interleave.json`

```json
{
    "description": "When the native and Python stacks reconcile, the formatter interleaves them: each interpreter evaluation frame in the native stack is replaced by the corresponding Python frame, while genuine native frames are shown as C lines. The result alternates native and Python frames so a reader sees the full mixed call stack in order. Native frames that merely re-enter the interpreter are collapsed so each Python call appears once.",
    "cases": [
        {
            "input": {"native": true, "thread": {"tid": 1, "name": null, "holds_the_gil": false, "is_gc_collecting": false, "python_version": [3, 8], "python_frames": [{"filename": "file1.py", "function": "function1", "lineno": 1, "end_lineno": 1, "column": 0, "end_column": 0, "is_entry": true, "is_shim": false}, {"filename": "file2.py", "function": "function2", "lineno": 2, "end_lineno": 2, "column": 0, "end_column": 0, "is_entry": true, "is_shim": false}, {"filename": "file3.py", "function": "function3", "lineno": 3, "end_lineno": 3, "column": 0, "end_column": 0, "is_entry": true, "is_shim": false}], "native_frames": [{"symbol": "native_function1", "file": "native_file1.c", "line": 1, "library": "library.so"}, {"symbol": "_PyEval_EvalFrameDefault", "file": "Python/ceval.c", "line": 123, "library": "library.so"}, {"symbol": "native_function2", "file": "native_file2.c", "line": 2, "library": "library.so"}, {"symbol": "_PyEval_EvalFrameDefault", "file": "Python/ceval.c", "line": 123, "library": "library.so"}, {"symbol": "native_function3", "file": "native_file3.c", "line": 3, "library": "library.so"}, {"symbol": "_PyEval_EvalFrameDefault", "file": "Python/ceval.c", "line": 123, "library": "library.so"}, {"symbol": "native_function4", "file": "native_file4.c", "line": 4, "library": "library.so"}]}},
            "expected_output": "Traceback for thread 1 [] (most recent call last):\n    (C) File \"native_file1.c\", line 1, in native_function1 (library.so)\n    (Python) File \"file1.py\", line 1, in function1\n    (C) File \"native_file2.c\", line 2, in native_function2 (library.so)\n    (Python) File \"file2.py\", line 2, in function2\n    (C) File \"native_file3.c\", line 3, in native_function3 (library.so)\n    (Python) File \"file3.py\", line 3, in function3\n    (C) File \"native_file4.c\", line 4, in native_function4 (library.so)[a specific trailing line break command — ask the PM for the exact adder]"
        }
    ]
}
```

*3.4 Internal Frames Filtered — drop interpreter-plumbing native frames during merge*

During interleaving, native frames that are interpreter-internal plumbing are dropped from the output: re-entrant evaluation entry points other than the recognized per-call evaluation frame, private runtime helpers (symbols beginning with the runtime's private prefix), generic call and vector-call dispatch shims, and a known set of internal call-helper symbols. Only meaningful native frames and their merged Python frames remain.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_internal_frames_filtered.json`

```json
{
    "description": "During interleaving, native frames that represent interpreter-internal plumbing — re-entrant evaluation entry points, private runtime helpers, generic call/vector-call dispatch shims, and a known set of internal call helpers — are dropped from the output, so only meaningful native frames and their merged Python frames remain.",
    "cases": [
        {
            "input": {"native": true, "thread": {"tid": 1, "name": null, "holds_the_gil": false, "is_gc_collecting": false, "python_version": [3, 8], "python_frames": [{"filename": "file1.py", "function": "function1", "lineno": 1, "end_lineno": 1, "column": 0, "end_column": 0, "is_entry": true, "is_shim": false}, {"filename": "file2.py", "function": "function2", "lineno": 2, "end_lineno": 2, "column": 0, "end_column": 0, "is_entry": true, "is_shim": false}], "native_frames": [{"symbol": "native_function1", "file": "native_file1.c", "line": 1, "library": "library.so"}, {"symbol": "_PyEval_EvalFrameDefault", "file": "Python/ceval.c", "line": 123, "library": "library.so"}, {"symbol": "PyEval_SomethingInternal", "file": "Python/ceval.c", "line": 13, "library": "library.so"}, {"symbol": "native_function2", "file": "native_file2.c", "line": 2, "library": "library.so"}, {"symbol": "_PyEval_EvalFrameDefault", "file": "Python/ceval.c", "line": 123, "library": "library.so"}, {"symbol": "PyObject_Call", "file": "Objects/call.c", "line": 13, "library": "library.so"}, {"symbol": "function_vectorcall", "file": "Objects/call.c", "line": 13, "library": "library.so"}, {"symbol": "native_function3", "file": "native_file3.c", "line": 3, "library": "library.so"}]}},
            "expected_output": "Traceback for thread 1 [] (most recent call last):\n    (C) File \"native_file1.c\", line 1, in native_function1 (library.so)\n    (Python) File \"file1.py\", line 1, in function1\n    (C) File \"native_file2.c\", line 2, in native_function2 (library.so)\n    (Python) File \"file2.py\", line 2, in function2\n    (C) File \"native_file3.c\", line 3, in native_function3 (library.so)[a specific trailing line break command — ask the PM for the exact adder]"
        }
    ]
}
```

*3.5 Inlined Frames — group consecutive Python frames that share one evaluation frame*

A single interpreter evaluation frame may correspond to several Python frames when calls are inlined. For each evaluation frame the renderer emits the current entry frame and then every following non-entry frame, before advancing to the next native frame. This holds whether only some calls are inlined or the entire Python chain collapses under one evaluation frame.

**Test Cases:** `rcb_tests/public_test_cases/feature3_5_inlined_frames.json`

```json
{
    "description": "Consecutive Python frames that share a single interpreter evaluation frame (inlined calls) are all emitted together under that one merged position: after the entry frame, every following non-entry frame is rendered before moving on to the next native frame. This holds whether only some calls are inlined or the entire Python chain collapses under one evaluation frame.",
    "cases": [
        {
            "input": {"native": true, "thread": {"tid": 1, "name": null, "holds_the_gil": false, "is_gc_collecting": false, "python_version": [3, 8], "python_frames": [{"filename": "file1.py", "function": "function1", "lineno": 1, "end_lineno": 1, "column": 0, "end_column": 0, "is_entry": true, "is_shim": false}, {"filename": "file2.py", "function": "function2", "lineno": 2, "end_lineno": 2, "column": 0, "end_column": 0, "is_entry": false, "is_shim": false}, {"filename": "file3.py", "function": "function3", "lineno": 3, "end_lineno": 3, "column": 0, "end_column": 0, "is_entry": true, "is_shim": false}, {"filename": "file4.py", "function": "function4", "lineno": 4, "end_lineno": 4, "column": 0, "end_column": 0, "is_entry": false, "is_shim": false}, {"filename": "file5.py", "function": "function5", "lineno": 5, "end_lineno": 5, "column": 0, "end_column": 0, "is_entry": false, "is_shim": false}], "native_frames": [{"symbol": "native_function1", "file": "native_file1.c", "line": 1, "library": "library.so"}, {"symbol": "PyEval_EvalFrameEx", "file": "Python/ceval.c", "line": 123, "library": "library.so"}, {"symbol": "_PyEval_EvalFrameDefault", "file": "Python/ceval.c", "line": 12, "library": "library.so"}, {"symbol": "native_function2", "file": "native_file2.c", "line": 2, "library": "library.so"}, {"symbol": "PyEval_EvalFrameEx", "file": "Python/ceval.c", "line": 123, "library": "library.so"}, {"symbol": "_PyEval_EvalFrameDefault", "file": "Python/ceval.c", "line": 12, "library": "library.so"}, {"symbol": "native_function3", "file": "native_file3.c", "line": 3, "library": "library.so"}]}},
            "expected_output": "Traceback for thread 1 [] (most recent call last):\n    (C) File \"native_file1.c\", line 1, in native_function1 (library.so)\n    (Python) File \"file1.py\", line 1, in function1\n    (Python) File \"file2.py\", line 2, in function2\n    (C) File \"native_file2.c\", line 2, in native_function2 (library.so)\n    (Python) File \"file3.py\", line 3, in function3\n    (Python) File \"file4.py\", line 4, in function4\n    (Python) File \"file5.py\", line 5, in function5\n    (C) File \"native_file3.c\", line 3, in native_function3 (library.so)[a specific trailing line break command — ask the PM for the exact adder]"
        }
    ]
}
```

*3.6 Shim Frames In Merge — placeholder frames ARE shown when merging*

Unlike the pure Python listing (where placeholder frames are skipped), the merged output renders the internal placeholder frames that sit between real Python frames as ordinary `(Python)` lines, including their source line when available. A placeholder frame whose line number is `0` shows the last line of its supplied source.

**Test Cases:** `rcb_tests/public_test_cases/feature3_6_shim_frames_in_merge.json`

```json
{
    "description": "Unlike the pure Python listing, when interleaving native and Python stacks the internal placeholder ('shim') frames that sit between real Python frames ARE rendered as part of the merged output, including their source line when available.",
    "cases": [
        {
            "input": {"native": true, "thread": {"tid": 1, "name": null, "holds_the_gil": false, "is_gc_collecting": false, "python_version": [3, 8], "python_frames": [{"filename": "<shim>", "function": "<shim>", "lineno": 0, "end_lineno": 0, "column": 0, "end_column": 0, "is_entry": false, "is_shim": true, "source": "x = \"This is the line 1\" or (1+1)\nx = \"This is the line 2\" or (1+1)\nx = \"This is the line 3\" or (1+1)\nx = \"This is the line 4\" or (1+1)"}, {"filename": "file1.py", "function": "function1", "lineno": 1, "end_lineno": 1, "column": 0, "end_column": 3, "is_entry": true, "is_shim": false, "source": "x = \"This is the line 1\" or (1+1)\nx = \"This is the line 2\" or (1+1)\nx = \"This is the line 3\" or (1+1)\nx = \"This is the line 4\" or (1+1)"}, {"filename": "<shim>", "function": "<shim>", "lineno": 0, "end_lineno": 0, "column": 0, "end_column": 0, "is_entry": false, "is_shim": true, "source": "x = \"This is the line 1\" or (1+1)\nx = \"This is the line 2\" or (1+1)\nx = \"This is the line 3\" or (1+1)\nx = \"This is the line 4\" or (1+1)"}, {"filename": "file2.py", "function": "function2", "lineno": 2, "end_lineno": 2, "column": 4, "end_column": 25, "is_entry": true, "is_shim": false, "source": "x = \"This is the line 1\" or (1+1)\nx = \"This is the line 2\" or (1+1)\nx = \"This is the line 3\" or (1+1)\nx = \"This is the line 4\" or (1+1)"}, {"filename": "<shim>", "function": "<shim>", "lineno": 0, "end_lineno": 0, "column": 0, "end_column": 0, "is_entry": false, "is_shim": true, "source": "x = \"This is the line 1\" or (1+1)\nx = \"This is the line 2\" or (1+1)\nx = \"This is the line 3\" or (1+1)\nx = \"This is the line 4\" or (1+1)"}, {"filename": "file3.py", "function": "function3", "lineno": 3, "end_lineno": 3, "column": 28, "end_column": 33, "is_entry": true, "is_shim": false, "source": "x = \"This is the line 1\" or (1+1)\nx = \"This is the line 2\" or (1+1)\nx = \"This is the line 3\" or (1+1)\nx = \"This is the line 4\" or (1+1)"}], "native_frames": [{"symbol": "native_function1", "file": "native_file1.c", "line": 1, "library": "library.so"}, {"symbol": "_PyEval_EvalFrameDefault", "file": "Python/ceval.c", "line": 123, "library": "library.so"}, {"symbol": "native_function2", "file": "native_file2.c", "line": 2, "library": "library.so"}, {"symbol": "_PyEval_EvalFrameDefault", "file": "Python/ceval.c", "line": 123, "library": "library.so"}, {"symbol": "native_function3", "file": "native_file3.c", "line": 3, "library": "library.so"}, {"symbol": "_PyEval_EvalFrameDefault", "file": "Python/ceval.c", "line": 123, "library": "library.so"}, {"symbol": "native_function4", "file": "native_file4.c", "line": 4, "library": "library.so"}]}},
            "expected_output": "Traceback for thread 1 [] (most recent call last):\n    (C) File \"native_file1.c\", line 1, in native_function1 (library.so)\n    (Python) File \"file1.py\", line 1, in function1\n        x = \"This is the line 1\" or (1+1)\n    (Python) File \"<shim>\", line 0, in <shim>\n        x = \"This is the line 4\" or (1+1)\n    (C) File \"native_file2.c\", line 2, in native_function2 (library.so)\n    (Python) File \"file2.py\", line 2, in function2\n        x = \"This is the line 2\" or (1+1)\n    (Python) File \"<shim>\", line 0, in <shim>\n        x = \"This is the line 4\" or (1+1)\n    (C) File \"native_file3.c\", line 3, in native_function3 (library.so)\n    (Python) File \"file3.py\", line 3, in function3\n        x = \"This is the line 3\" or (1+1)\n    (C) File \"native_file4.c\", line 4, in native_function4 (library.so)[a specific trailing line break command — ask the PM for the exact adder]"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the rendering behavior described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint. The core rendering logic must be decoupled from standard I/O and JSON parsing: it operates on in-memory stack/frame/thread structures, not on the wire format.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin (per the Input Contract), builds the in-memory thread snapshot, invokes the renderer with the requested `native` flag, and prints the resulting traceback text to stdout, matching the per-feature contracts above. All output is plain text with no terminal color codes; each line ends in a newline.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same boolean flag convention as the thread state module
- follow the same whitespace handling logic as the source string parser
