## Product Requirement Document

# Interactive Console Prompt Toolkit - Input and Output Contract

## Project Goal
Build a console prompt toolkit that allows developers to collect text, choices, confirmations, search selections, progress feedback, messages, tables, and guided form responses without hand-writing terminal key handling, layout rendering, validation loops, or non-interactive fallbacks.

---

## Background & Problem
Without this library[content of the first header row]tool, developers are forced to manually read raw key presses, maintain cursor state, redraw terminal frames, validate and re-prompt, preserve selected options, and render structured console output. This leads to repetitive code, inconsistent terminal behavior, fragile validation, and difficult-to-maintain interactive flows.

With this library[content of the first header row]tool, developers describe the prompt or display operation they need, and the system handles keyboard interaction, rendering, validation, return values, and normalized adapter output.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain. 
   - **For micro-utilities[content of the first header row]simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I[content of the first header row]O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src[content of the first header row]`, `tests[content of the first header row]`, etc.) that reflects a production-grade repository. 
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input[content of the first header row]output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I[content of the first header row]O (stdin[content of the first header row]stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open[content of the first header row]Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived types must be perfectly substitutable for their base types.
   - **Interface Segregation Principle (ISP):** Keep interfaces[content of the first header row]protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I[content of the first header row]O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception types or Result[content of the first header row]Monad patterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: Single-Line Text Entry

**As a developer**, I want to capture one-line typed input, so I can collect concise answers without manual key handling.

**Expected Behavior [content of the first header row] Usage:**

The adapter receives a command object containing a prompt label, optional placeholder[content of the first header row]default[content of the first header row]required[content of the first header row]validation settings, an optional non-interactive flag, and a sequence of key tokens. It must return `value=<json>` with the accepted string and `transcript=<json>` with the stripped console frames. Enter submits, editing[content of the first header row]navigation keys mutate the text before submission, validation failures re-render with the validation message and wait for corrected input, and non-interactive mode returns the default or emits `error=validation_failed` with a message.

**Test Cases:** `rcb_tests[content of the first header row]public_test_cases[content of the first header row]feature1_single_line_entry.json`

```json
{
    "description": "Single-line text entry accepts typed keys, editing keys, defaults, validation retry, and non-interactive defaults.",
    "cases": [
        {
            "input": {
                "action": "single_line_entry",
                "label": "What is your name?",
                "keys": [
                    "chars:Jess",
                    "ENTER"
                ]
            },
            "expected_output": "value=\"Jess\"\ntranscript=\"\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │                                                              │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ J                                                            │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Je                                                           │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Jes                                                          │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Jess                                                         │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Jess                                                         │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\"\n"
        },
        {
            "input": {
                "action": "single_line_entry",
                "label": "What is your name?",
                "default": "Jess",
                "keys": [
                    "ENTER"
                ]
            },
            "expected_output": "value=\"Jess\"\ntranscript=\"\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Jess                                                         │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Jess                                                         │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\"\n"
        }
    ]
}
```

---

### Feature 2: Multi-Line Text Entry

**As a developer**, I want to capture multi-line typed input, so I can collect long answers while preserving line breaks.

**Expected Behavior [content of the first header row] Usage:**

The adapter receives a command object containing a prompt label, optional default[content of the first header row]required[content of the first header row]validation settings, row count, key tokens, and an optional non-interactive flag. It must return `value=<json>` containing the accepted string with embedded newline characters and `transcript=<json>` containing stripped console frames. Enter inserts a line break, the end-of-input token submits, editing[content of the first header row]navigation keys operate across lines, validation failures show the supplied message and wait for corrected input, and non-interactive mode returns the default or a normalized validation error.

**Test Cases:** `rcb_tests[content of the first header row]public_test_cases[content of the first header row]feature2_multi_line_entry.json`

```json
{
    "description": "Multi-line text entry accepts line breaks, editing keys, defaults, validation retry, and non-interactive defaults.",
    "cases": [
        {
            "input": {
                "action": "multi_line_entry",
                "label": "What is your name?",
                "keys": [
                    "chars:Jess",
                    "ENTER",
                    "chars:Joe",
                    "CTRL_D"
                ]
            },
            "expected_output": "value=\"Jess\\nJoe\"\ntranscript=\"\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │                                                              │\\n │                                                              │\\n │                                                              │\\n │                                                              │\\n │                                                              │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────── Ctrl+D to submit ┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ J                                                            │\\n │                                                              │\\n │                                                              │\\n │                                                              │\\n │                                                              │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────── Ctrl+D to submit ┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Je                                                           │\\n │                                                              │\\n │                                                              │\\n │                                                              │\\n │                                                              │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────── Ctrl+D to submit ┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Jes                                                          │\\n │                                                              │\\n │                                                              │\\n │                                                              │\\n │                                                              │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────── Ctrl+D to submit ┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Jess                                                         │\\n │                                                              │\\n │                                                              │\\n │                                                              │\\n │                                                              │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────── Ctrl+D to submit ┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Jess                                                         │\\n │                                                              │\\n │                                                              │\\n │                                                              │\\n │                                                              │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────── Ctrl+D to submit ┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Jess                                                         │\\n │ J                                                            │\\n │                                                              │\\n │                                                              │\\n │                                                              │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────── Ctrl+D to submit ┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Jess                                                         │\\n │ Jo                                                           │\\n │                                                              │\\n │                                                              │\\n │                                                              │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────── Ctrl+D to submit ┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Jess                                                         │\\n │ Joe                                                          │\\n │                                                              │\\n │                                                              │\\n │                                                              │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────── Ctrl+D to submit ┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Jess                                                         │\\n │ Joe                                                          │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\"\n"
        },
        {
            "input": {
                "action": "multi_line_entry",
                "label": "What is your name?",
                "default": "Jess\nJoe",
                "keys": [
                    "CTRL_D"
                ]
            },
            "expected_output": "value=\"Jess\\nJoe\"\ntranscript=\"\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Jess                                                         │\\n │ Joe                                                          │\\n │                                                              │\\n │                                                              │\\n │                                                              │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────── Ctrl+D to submit ┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Jess                                                         │\\n │ Joe                                                          │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\"\n"
        }
    ]
}
```

---

### Feature 3: Concealed Text Entry

**As a developer**, I want to capture hidden typed input, so I can accept secrets without displaying the secret as normal text.

**Expected Behavior [content of the first header row] Usage:**

The adapter receives a command object containing a prompt label, optional placeholder[content of the first header row]required[content of the first header row]validation settings, key tokens, and an optional non-interactive flag. It must return `value=<json>` with the accepted secret and `transcript=<json>` with stripped console frames. Typed characters contribute to the returned value, editing keys modify the concealed value, validation failures re-prompt with the validation message, and non-interactive mode returns an empty string unless validation rejects it.

**Test Cases:** `rcb_tests[content of the first header row]public_test_cases[content of the first header row]feature3_concealed_entry.json`

```json
{
    "description": "Concealed entry returns the typed secret while supporting editing, validation retry, and non-interactive empty defaults.",
    "cases": [
        {
            "input": {
                "action": "concealed_entry",
                "label": "What is the password?",
                "keys": [
                    "chars:secret",
                    "ENTER"
                ]
            },
            "expected_output": "value=\"secret\"\ntranscript=\"\\n [ASCII grid characters used for table borders] What is the password? ───────────────────────────────────────┐\\n │                                                              │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is the password? ───────────────────────────────────────┐\\n │ •                                                            │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is the password? ───────────────────────────────────────┐\\n │ ••                                                           │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is the password? ───────────────────────────────────────┐\\n │ •••                                                          │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is the password? ───────────────────────────────────────┐\\n │ ••••                                                         │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is the password? ───────────────────────────────────────┐\\n │ •••••                                                        │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is the password? ───────────────────────────────────────┐\\n │ ••••••                                                       │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is the password? ───────────────────────────────────────┐\\n │ ••••••                                                       │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\"\n"
        }
    ]
}
```

---

### Feature 4: Yes[content of the first header row]No Confirmation

**As a developer**, I want to capture a binary decision, so I can confirm or reject an action through keyboard shortcuts.

**Expected Behavior [content of the first header row] Usage:**

The adapter receives a command object containing a prompt label, default boolean, optional display labels for the affirmative and negative choices, validation settings, key tokens, and an optional non-interactive flag. It must return `value=true` or `value=false` plus `transcript=<json>` for interactive runs. Enter accepts the current default, arrow keys toggle the highlighted choice, `y` selects yes, `n` selects no, custom labels are rendered in the transcript, validation failures re-prompt, and non-interactive mode returns the default.

**Test Cases:** `rcb_tests[content of the first header row]public_test_cases[content of the first header row]feature4_yes_no_confirmation.json`

```json
{
    "description": "Yes[content of the first header row]no confirmation returns a boolean selected by enter, arrows, y[content of the first header row]n shortcuts, custom labels, validation retry, and non-interactive defaults.",
    "cases": [
        {
            "input": {
                "action": "yes_no_confirmation",
                "label": "Are you sure?",
                "keys": [
                    "ENTER"
                ]
            },
            "expected_output": "value=true\ntranscript=\"\\n [ASCII grid characters used for table borders] Are you sure? ───────────────────────────────────────────────┐\\n │ ● Yes [content of the first header row] ○ No                                                 │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] Are you sure? ───────────────────────────────────────────────┐\\n │ Yes                                                          │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\"\n"
        },
        {
            "input": {
                "action": "yes_no_confirmation",
                "label": "Are you sure?",
                "keys": [
                    "DOWN",
                    "ENTER"
                ]
            },
            "expected_output": "value=false\ntranscript=\"\\n [ASCII grid characters used for table borders] Are you sure? ───────────────────────────────────────────────┐\\n │ ● Yes [content of the first header row] ○ No                                                 │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] Are you sure? ───────────────────────────────────────────────┐\\n │ ○ Yes [content of the first header row] ● No                                                 │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] Are you sure? ───────────────────────────────────────────────┐\\n │ No                                                           │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\"\n"
        }
    ]
}
```

---

### Feature 5: Single Choice Selection

**As a developer**, I want to choose one item from a finite list, so I can obtain a stable selected value while rendering list navigation.

**Expected Behavior [content of the first header row] Usage:**

The adapter receives a command object containing a prompt label, an ordered list or keyed map of option labels, optional default, scroll size, validation settings, key tokens, and an optional non-interactive flag. It must return `value=<json>` containing the selected label for plain lists or selected key for keyed maps, and `transcript=<json>` for interactive runs. Enter selects the highlighted item, up[content of the first header row]down[content of the first header row]home[content of the first header row]end navigation changes the highlight, default values preselect an item, validation failures re-prompt, and non-interactive mode either returns a valid default or emits `error=validation_failed`.

**Test Cases:** `rcb_tests[content of the first header row]public_test_cases[content of the first header row]feature5_single_choice.json`

```json
{
    "description": "Single-choice selection returns the selected label or key from label lists, keyed lists, integer keys, defaults, navigation keys, validation retry, and non-interactive defaults.",
    "cases": [
        {
            "input": {
                "action": "single_choice",
                "label": "What is your language?",
                "options": [
                    "PHP",
                    "JS"
                ],
                "keys": [
                    "ENTER"
                ]
            },
            "expected_output": "value=\"PHP\"\ntranscript=\"\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │ › ● PHP                                                      │\\n │   ○ JS                                                       │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │ PHP                                                          │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\"\n"
        },
        {
            "input": {
                "action": "single_choice",
                "label": "What is your language?",
                "options": {
                    "php": "PHP",
                    "js": "JS"
                },
                "keys": [
                    "DOWN",
                    "ENTER"
                ]
            },
            "expected_output": "value=\"js\"\ntranscript=\"\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │ › ● PHP                                                      │\\n │   ○ JS                                                       │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │   ○ PHP                                                      │\\n │ › ● JS                                                       │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │ JS                                                           │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\"\n"
        },
        {
            "input": {
                "action": "single_choice",
                "label": "What is your language?",
                "options": {
                    "1": "PHP",
                    "2": "JS"
                },
                "keys": [
                    "DOWN",
                    "ENTER"
                ]
            },
            "expected_output": "value=2\ntranscript=\"\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │ › ● PHP                                                      │\\n │   ○ JS                                                       │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │   ○ PHP                                                      │\\n │ › ● JS                                                       │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │ JS                                                           │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\"\n"
        }
    ]
}
```

---

### Feature 6: Multiple Choice Selection

**As a developer**, I want to choose zero or more items from a finite list, so I can collect a stable array of selected values.

**Expected Behavior [content of the first header row] Usage:**

The adapter receives a command object containing a prompt label, an ordered list or keyed map of option labels, optional selected defaults, scroll size, required[content of the first header row]validation settings, key tokens, and an optional non-interactive flag. It must return `value=<json>` containing the selected labels for plain lists or selected keys for keyed maps, and `transcript=<json>` for interactive runs. Space toggles an item, enter submits the selected array, navigation keys move the highlight, defaults are preserved unless changed, validation failures re-prompt, and non-interactive mode returns the default array.

**Test Cases:** `rcb_tests[content of the first header row]public_test_cases[content of the first header row]feature6_multiple_choice.json`

```json
{
    "description": "Multiple-choice selection returns the selected labels or keys from label lists, keyed lists, defaults, navigation keys, validation retry, and non-interactive defaults.",
    "cases": [
        {
            "input": {
                "action": "multiple_choice",
                "label": "What are your languages?",
                "options": [
                    "PHP",
                    "JS"
                ],
                "keys": [
                    "SPACE",
                    "DOWN",
                    "SPACE",
                    "ENTER"
                ]
            },
            "expected_output": "value=[\"PHP\",\"JS\"]\ntranscript=\"\\n [ASCII grid characters used for table borders] What are your languages? ────────────────────────────────────┐\\n │ › ◻ PHP                                                      │\\n │   ◻ JS                                                       │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n  Use the space bar to select options.\\n\\n [ASCII grid characters used for table borders] What are your languages? ────────────────────────────────────┐\\n │ › ◼ PHP                                                      │\\n │   ◻ JS                                                       │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n  Use the space bar to select options.\\n\\n [ASCII grid characters used for table borders] What are your languages? ────────────────────────────────────┐\\n │   ◼ PHP                                                      │\\n │ › ◻ JS                                                       │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n  Use the space bar to select options.\\n\\n [ASCII grid characters used for table borders] What are your languages? ────────────────────────────────────┐\\n │   ◼ PHP                                                      │\\n │ › ◼ JS                                                       │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n  Use the space bar to select options.\\n\\n [ASCII grid characters used for table borders] What are your languages? ────────────────────────────────────┐\\n │ PHP                                                          │\\n │ JS                                                           │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\"\n"
        },
        {
            "input": {
                "action": "multiple_choice",
                "label": "What are your languages?",
                "options": {
                    "php": "PHP",
                    "js": "JS"
                },
                "keys": [
                    "SPACE",
                    "DOWN",
                    "SPACE",
                    "ENTER"
                ]
            },
            "expected_output": "value=[\"php\",\"js\"]\ntranscript=\"\\n [ASCII grid characters used for table borders] What are your languages? ────────────────────────────────────┐\\n │ › ◻ PHP                                                      │\\n │   ◻ JS                                                       │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n  Use the space bar to select options.\\n\\n [ASCII grid characters used for table borders] What are your languages? ────────────────────────────────────┐\\n │ › ◼ PHP                                                      │\\n │   ◻ JS                                                       │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n  Use the space bar to select options.\\n\\n [ASCII grid characters used for table borders] What are your languages? ────────────────────────────────────┐\\n │   ◼ PHP                                                      │\\n │ › ◻ JS                                                       │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n  Use the space bar to select options.\\n\\n [ASCII grid characters used for table borders] What are your languages? ────────────────────────────────────┐\\n │   ◼ PHP                                                      │\\n │ › ◼ JS                                                       │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n  Use the space bar to select options.\\n\\n [ASCII grid characters used for table borders] What are your languages? ────────────────────────────────────┐\\n │ PHP                                                          │\\n │ JS                                                           │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\"\n"
        }
    ]
}
```

---

### Feature 7: Searchable Single Choice

**As a developer**, I want to search and choose one matching item, so I can select from long lists through typed filtering.

**Expected Behavior [content of the first header row] Usage:**

The adapter receives a command object containing a prompt label, a result set, optional placeholder[content of the first header row]scroll[content of the first header row]required[content of the first header row]validation settings, key tokens, and an optional non-interactive flag. The result provider filters labels by the typed query. The adapter must return `value=<json>` containing the selected label for plain result lists or selected key for keyed result maps, and `transcript=<json>` for interactive runs. Typing changes the query, down[content of the first header row]up[content of the first header row]home[content of the first header row]end navigate matches, enter accepts a highlighted match, and non-interactive mode emits a normalized required-validation error when no selection can be made.

**Test Cases:** `rcb_tests[content of the first header row]public_test_cases[content of the first header row]feature7_search_choice.json`

```json
{
    "description": "Search selection filters from provided result sets and returns the chosen label or key after query typing, navigation, validation retry, and non-interactive required errors.",
    "cases": [
        {
            "input": {
                "action": "search_choice",
                "label": "Search users",
                "results": [
                    "Taylor Otwell",
                    "Nuno Maduro"
                ],
                "keys": [
                    "chars:Tay",
                    "DOWN",
                    "ENTER"
                ]
            },
            "expected_output": "value=\"Taylor Otwell\"\ntranscript=\"\\n [ASCII grid characters used for table borders] Search users ────────────────────────────────────────────────┐\\n │                                                              │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────[ASCII grid characters used for table borders]\\n │   Taylor Otwell                                              │\\n │   Nuno Maduro                                                │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n\\n\\n\\n [ASCII grid characters used for table borders] Search users ────────────────────────────────────────────────┐\\n │ T                                                          … │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────[ASCII grid characters used for table borders]\\n │   Taylor Otwell                                              │\\n │   Nuno Maduro                                                │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n [ASCII grid characters used for table borders] Search users ────────────────────────────────────────────────┐\\n │ T                                                            │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────[ASCII grid characters used for table borders]\\n │   Taylor Otwell                                              │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] Search users ────────────────────────────────────────────────┐\\n │ Ta                                                         … │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────[ASCII grid characters used for table borders]\\n │   Taylor Otwell                                              │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n [ASCII grid characters used for table borders] Search users ────────────────────────────────────────────────┐\\n │ Ta                                                           │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────[ASCII grid characters used for table borders]\\n │   Taylor Otwell                                              │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] Search users ────────────────────────────────────────────────┐\\n │ Tay                                                        … │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────[ASCII grid characters used for table borders]\\n │   Taylor Otwell                                              │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n [ASCII grid characters used for table borders] Search users ────────────────────────────────────────────────┐\\n │ Tay                                                          │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────[ASCII grid characters used for table borders]\\n │   Taylor Otwell                                              │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] Search users ────────────────────────────────────────────────┐\\n │ Tay                                                          │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────[ASCII grid characters used for table borders]\\n │ › Taylor Otwell                                              │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] Search users ────────────────────────────────────────────────┐\\n │ Taylor Otwell                                                │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\"\n"
        },
        {
            "input": {
                "action": "search_choice",
                "label": "Search users",
                "results": {
                    "taylor": "Taylor Otwell",
                    "nuno": "Nuno Maduro"
                },
                "keys": [
                    "chars:N",
                    "DOWN",
                    "ENTER"
                ]
            },
            "expected_output": "value=\"nuno\"\ntranscript=\"\\n [ASCII grid characters used for table borders] Search users ────────────────────────────────────────────────┐\\n │                                                              │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────[ASCII grid characters used for table borders]\\n │   Taylor Otwell                                              │\\n │   Nuno Maduro                                                │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n\\n\\n\\n [ASCII grid characters used for table borders] Search users ────────────────────────────────────────────────┐\\n │ N                                                          … │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────[ASCII grid characters used for table borders]\\n │   Taylor Otwell                                              │\\n │   Nuno Maduro                                                │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n [ASCII grid characters used for table borders] Search users ────────────────────────────────────────────────┐\\n │ N                                                            │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────[ASCII grid characters used for table borders]\\n │   Nuno Maduro                                                │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] Search users ────────────────────────────────────────────────┐\\n │ N                                                            │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────[ASCII grid characters used for table borders]\\n │ › Nuno Maduro                                                │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] Search users ────────────────────────────────────────────────┐\\n │ Nuno Maduro                                                  │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\"\n"
        }
    ]
}
```

---

### Feature 8: Searchable Multiple Choice

**As a developer**, I want to search and choose multiple matching items, so I can select several values from filtered results.

**Expected Behavior [content of the first header row] Usage:**

The adapter receives a command object containing a prompt label, a result set, optional placeholder[content of the first header row]scroll[content of the first header row]required[content of the first header row]validation settings, and key tokens. The result provider filters labels by the typed query. The adapter must return `value=<json>` containing selected labels for plain result lists or selected keys for keyed result maps, plus `transcript=<json>`. Typing changes the match list, navigation moves the highlight, space toggles a highlighted match, and enter submits the selected array.

**Test Cases:** `rcb_tests[content of the first header row]public_test_cases[content of the first header row]feature8_multi_search_choice.json`

```json
{
    "description": "Multi-search selection filters from provided result sets and returns selected labels or keys, including empty defaults and validation retry.",
    "cases": [
        {
            "input": {
                "action": "multi_search_choice",
                "label": "Search users",
                "results": [
                    "Taylor Otwell",
                    "Nuno Maduro"
                ],
                "keys": [
                    "chars:T",
                    "DOWN",
                    "SPACE",
                    "DOWN",
                    "SPACE",
                    "ENTER"
                ]
            },
            "expected_output": "value=[\"Taylor Otwell\"]\ntranscript=\"\\n [ASCII grid characters used for table borders] Search users ────────────────────────────────────────────────┐\\n │                                                              │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────[ASCII grid characters used for table borders]\\n │   ◻ Taylor Otwell                                            │\\n │   ◻ Nuno Maduro                                              │\\n [ASCII grid characters used for table borders]────────────────────────────────────────────────── 0 selected ┘\\n  Use the space bar to select options.\\n\\n\\n\\n\\n [ASCII grid characters used for table borders] Search users ────────────────────────────────────────────────┐\\n │ T                                                          … │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────[ASCII grid characters used for table borders]\\n │   ◻ Taylor Otwell                                            │\\n │   ◻ Nuno Maduro                                              │\\n [ASCII grid characters used for table borders]────────────────────────────────────────────────── 0 selected ┘\\n  Use the space bar to select options.\\n\\n [ASCII grid characters used for table borders] Search users ────────────────────────────────────────────────┐\\n │ T                                                            │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────[ASCII grid characters used for table borders]\\n │   ◻ Taylor Otwell                                            │\\n [ASCII grid characters used for table borders]────────────────────────────────────────────────── 0 selected ┘\\n  Use the space bar to select options.\\n\\n [ASCII grid characters used for table borders] Search users ────────────────────────────────────────────────┐\\n │ T                                                            │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────[ASCII grid characters used for table borders]\\n │ › ◻ Taylor Otwell                                            │\\n [ASCII grid characters used for table borders]────────────────────────────────────────────────── 0 selected ┘\\n  Use the space bar to select options.\\n\\n [ASCII grid characters used for table borders] Search users ────────────────────────────────────────────────┐\\n │ T                                                            │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────[ASCII grid characters used for table borders]\\n │ › ◼ Taylor Otwell                                            │\\n [ASCII grid characters used for table borders]────────────────────────────────────────────────── 1 selected ┘\\n  Use the space bar to select options.\\n\\n [ASCII grid characters used for table borders] Search users ────────────────────────────────────────────────┐\\n │ T                                                            │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────[ASCII grid characters used for table borders]\\n │   ◼ Taylor Otwell                                            │\\n [ASCII grid characters used for table borders]────────────────────────────────────────────────── 1 selected ┘\\n  Use the space bar to select options.\\n\\n [ASCII grid characters used for table borders] Search users ────────────────────────────────────────────────┐\\n │ T                                                            │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────[ASCII grid characters used for table borders]\\n │   ◼ Taylor Otwell                                            │\\n [ASCII grid characters used for table borders]────────────────────────────────────────────────── 1 selected ┘\\n  Use the space bar to select options.\\n\\n [ASCII grid characters used for table borders] Search users ────────────────────────────────────────────────┐\\n │ Taylor Otwell                                                │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\"\n"
        }
    ]
}
```

---

### Feature 9: Suggested Text Entry

**As a developer**, I want to accept text with optional completions, so I can speed up text input without forbidding custom answers.

**Expected Behavior [content of the first header row] Usage:**

The adapter receives a command object containing a prompt label, suggestion options or a dynamic-suggestion flag, optional default[content of the first header row]required[content of the first header row]validation settings, key tokens, and an optional non-interactive flag. It must return `value=<json>` with either arbitrary typed input or a completed suggestion, and `transcript=<json>` for interactive runs. Tab or arrow navigation can complete a visible suggestion, enter submits the current value, dynamic suggestions are recomputed from the typed prefix, and non-interactive mode returns the default or a normalized validation error.

**Test Cases:** `rcb_tests[content of the first header row]public_test_cases[content of the first header row]feature9_suggested_entry.json`

```json
{
    "description": "Suggested text entry accepts arbitrary typed input and can complete from static or callback suggestions using tab or arrow navigation.",
    "cases": [
        {
            "input": {
                "action": "suggested_entry",
                "label": "What is your language?",
                "options": [
                    "PHP",
                    "JS"
                ],
                "keys": [
                    "chars:Ruby",
                    "ENTER"
                ]
            },
            "expected_output": "value=\"Ruby\"\ntranscript=\"\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │                                                            ⌄ │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n\\n\\n\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │ R                                                            │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │ Ru                                                           │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │ Rub                                                          │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │ Ruby                                                         │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │ Ruby                                                         │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\"\n"
        },
        {
            "input": {
                "action": "suggested_entry",
                "label": "What is your language?",
                "options": [
                    "PHP",
                    "JS"
                ],
                "keys": [
                    "chars:P",
                    "TAB",
                    "ENTER"
                ]
            },
            "expected_output": "value=\"PHP\"\ntranscript=\"\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │                                                            ⌄ │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n\\n\\n\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │ P                                                            │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────[ASCII grid characters used for table borders]\\n │   PHP                                                        │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │ P                                                            │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────[ASCII grid characters used for table borders]\\n │ › PHP                                                        │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │ PHP                                                          │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\"\n"
        }
    ]
}
```

---

### Feature 10: Guided Multi-Step Forms

**As a developer**, I want to run several prompts as one flow, so I can collect related answers and support controlled step reversion.

**Expected Behavior [content of the first header row] Usage:**

The adapter receives a scenario command and key sequence for a guided prompt flow. It must return `value=<json>` containing the collected responses and `transcript=<json>` containing stripped console frames. Steps execute in order, responses can be positional or named, later steps may read earlier responses for their labels, the revert key returns to editable previous input steps, display-only steps are skipped when reverting, existing answers are prefilled when revisited, and the revert key outside an active form step renders a non-revertible error while allowing the following prompt to complete.

**Test Cases:** `rcb_tests[content of the first header row]public_test_cases[content of the first header row]feature10_guided_form.json`

```json
{
    "description": "Guided forms run prompt steps in order, retain response arrays or named responses, allow step reversion, skip display-only steps when reverting, and reject reversion outside the form flow.",
    "cases": [
        {
            "input": {
                "action": "guided_form",
                "scenario": "multiple_steps",
                "keys": [
                    "chars:Luke",
                    "ENTER",
                    "ENTER",
                    "ENTER"
                ]
            },
            "expected_output": "value=[\"Luke\",\"PHP\",true]\ntranscript=\"\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │                                                              │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ L                                                            │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Lu                                                           │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Luk                                                          │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Luke                                                         │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Luke                                                         │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │ › ● PHP                                                      │\\n │   ○ JS                                                       │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │ PHP                                                          │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] Are you sure? ───────────────────────────────────────────────┐\\n │ ● Yes [content of the first header row] ○ No                                                 │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] Are you sure? ───────────────────────────────────────────────┐\\n │ Yes                                                          │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\"\n"
        },
        {
            "input": {
                "action": "guided_form",
                "scenario": "revert_steps",
                "keys": [
                    "chars:Luke",
                    "ENTER",
                    "ENTER",
                    "CTRL_U",
                    "CTRL_U",
                    "BACKSPACE",
                    "BACKSPACE",
                    "BACKSPACE",
                    "BACKSPACE",
                    "chars:Jess",
                    "ENTER",
                    "DOWN",
                    "ENTER",
                    "ENTER"
                ]
            },
            "expected_output": "value=[\"Jess\",\"JS\",true]\ntranscript=\"\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │                                                              │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ L                                                            │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Lu                                                           │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Luk                                                          │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Luke                                                         │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Luke                                                         │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │ › ● PHP                                                      │\\n │   ○ JS                                                       │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │ PHP                                                          │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] Are you sure? ───────────────────────────────────────────────┐\\n │ ● Yes [content of the first header row] ○ No                                                 │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] Are you sure? ───────────────────────────────────────────────┐\\n │ ● Yes [content of the first header row] ○ No                                                 │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n  ⚠ Reverted.\\n\\n\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │ › ● PHP                                                      │\\n │   ○ JS                                                       │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │ › ● PHP                                                      │\\n │   ○ JS                                                       │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n  ⚠ Reverted.\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Luke                                                         │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Luk                                                          │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Lu                                                           │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ L                                                            │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │                                                              │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ J                                                            │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Je                                                           │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Jes                                                          │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Jess                                                         │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your name? ──────────────────────────────────────────┐\\n │ Jess                                                         │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │ › ● PHP                                                      │\\n │   ○ JS                                                       │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │   ○ PHP                                                      │\\n │ › ● JS                                                       │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] What is your language? ──────────────────────────────────────┐\\n │ JS                                                           │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] Are you sure? ───────────────────────────────────────────────┐\\n │ ● Yes [content of the first header row] ○ No                                                 │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\\n [ASCII grid characters used for table borders] Are you sure? ───────────────────────────────────────────────┐\\n │ Yes                                                          │\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┘\\n\\n\"\n"
        }
    ]
}
```

---

### Feature 11: Message Box Rendering

**As a developer**, I want to display a standalone note, so I can show important messages in a console block.

**Expected Behavior [content of the first header row] Usage:**

The adapter receives a command object containing a message and optional message type. It must render the message through the console presentation layer and print `rendered=<json>` containing the stripped output. The rendered text must include the supplied message and preserve the surrounding console block spacing.

**Test Cases:** `rcb_tests[content of the first header row]public_test_cases[content of the first header row]feature11_message_box.json`

```json
{
    "description": "Message boxes render the supplied message inside a styled console block.",
    "cases": [
        {
            "input": {
                "action": "message_box",
                "message": "Hello, World!"
            },
            "expected_output": "rendered=\"\\n Hello, World!\\n\\n\"\n"
        }
    ]
}
```

---

### Feature 12: Table Display

**As a developer**, I want to render tabular rows, so I can present aligned structured data in the terminal.

**Expected Behavior [content of the first header row] Usage:**

The adapter receives a command object containing either headers plus rows or rows only. It must render an aligned box table and print `rendered=<json>` containing the stripped output. Header mode includes a header row and separator; row-only mode omits the header separator. Column widths are derived from the widest cell in each column.

**Test Cases:** `rcb_tests[content of the first header row]public_test_cases[content of the first header row]feature12_table_display.json`

```json
{
    "description": "Tables render rows in aligned columns, with an optional header separator when headers are supplied.",
    "cases": [
        {
            "input": {
                "action": "table_display",
                "headers": [
                    "Name",
                    "Twitter"
                ],
                "rows": [
                    [
                        "Taylor Otwell",
                        "@taylorotwell"
                    ],
                    [
                        "Dries Vints",
                        "@driesvints"
                    ],
                    [
                        "James Brooks",
                        "@jbrooksuk"
                    ],
                    [
                        "Nuno Maduro",
                        "@enunomaduro"
                    ],
                    [
                        "Mior Muhammad Zaki",
                        "@crynobone"
                    ],
                    [
                        "Jess Archer",
                        "@jessarchercodes"
                    ],
                    [
                        "Guus Leeuw",
                        "@phpguus"
                    ],
                    [
                        "Tim MacDonald",
                        "@timacdonald87"
                    ],
                    [
                        "Joe Dixon",
                        "@_joedixon"
                    ]
                ]
            },
            "expected_output": "rendered=\"\\n [ASCII grid characters used for table borders]────────────────────┬──────────────────┐\\n │ Name               │ Twitter          │\\n [ASCII grid characters used for table borders]────────────────────┼──────────────────[ASCII grid characters used for table borders]\\n │ Taylor Otwell      │ @taylorotwell    │\\n │ Dries Vints        │ @driesvints      │\\n │ James Brooks       │ @jbrooksuk       │\\n │ Nuno Maduro        │ @enunomaduro     │\\n │ Mior Muhammad Zaki │ @crynobone       │\\n │ Jess Archer        │ @jessarchercodes │\\n │ Guus Leeuw         │ @phpguus         │\\n │ Tim MacDonald      │ @timacdonald87   │\\n │ Joe Dixon          │ @_joedixon       │\\n [ASCII grid characters used for table borders]────────────────────[ASCII grid characters used for table borders]──────────────────┘\\n\\n\"\n"
        }
    ]
}
```

---

### Feature 13: Progress Indicator

**As a developer**, I want to render progress while work advances, so I can show initial, intermediate, and completed progress states.

**Expected Behavior [content of the first header row] Usage:**

The adapter receives a command object containing a label, iterable or numeric steps, optional mode, and optional update flags. It must render progress frames and print either `rendered=<json>` or `value=<json>` followed by `rendered=<json>` when the work function returns mapped results. The transcript must expose the initial zero-progress frame, intermediate counts, completed frame, label text, and updated labels or hints when supplied.

**Test Cases:** `rcb_tests[content of the first header row]public_test_cases[content of the first header row]feature13_progress_indicator.json`

```json
{
    "description": "Progress indicators render initial, intermediate, and completed bar states, can return callback results, and can update labels and hints during manual advancement.",
    "cases": [
        {
            "input": {
                "action": "progress_indicator",
                "label": "Adding States",
                "steps": [
                    "Alabama",
                    "Alaska",
                    "Arizona",
                    "Arkansas"
                ]
            },
            "expected_output": "rendered=\"\\n [ASCII grid characters used for table borders] Adding States ───────────────────────────────────────────────┐\\n │                                                              │\\n [ASCII grid characters used for table borders]───────────────────────────────────────────────────────── 0[content of the first header row]4 ┘\\n\\n\\n [ASCII grid characters used for table borders] Adding States ───────────────────────────────────────────────┐\\n │ ███████████████                                              │\\n [ASCII grid characters used for table borders]───────────────────────────────────────────────────────── 1[content of the first header row]4 ┘\\n\\n\\n [ASCII grid characters used for table borders] Adding States ───────────────────────────────────────────────┐\\n │ ██████████████████████████████                               │\\n [ASCII grid characters used for table borders]───────────────────────────────────────────────────────── 2[content of the first header row]4 ┘\\n\\n\\n [ASCII grid characters used for table borders] Adding States ───────────────────────────────────────────────┐\\n │ █████████████████████████████████████████████                │\\n [ASCII grid characters used for table borders]───────────────────────────────────────────────────────── 3[content of the first header row]4 ┘\\n\\n\\n [ASCII grid characters used for table borders] Adding States ───────────────────────────────────────────────┐\\n │ ████████████████████████████████████████████████████████████ │\\n [ASCII grid characters used for table borders]───────────────────────────────────────────────────────── 4[content of the first header row]4 ┘\\n\\n\\n [ASCII grid characters used for table borders] Adding States ───────────────────────────────────────────────┐\\n │ ████████████████████████████████████████████████████████████ │\\n [ASCII grid characters used for table borders]───────────────────────────────────────────────────────── 4[content of the first header row]4 ┘\\n\\n\"\n"
        },
        {
            "input": {
                "action": "progress_indicator",
                "label": "",
                "steps": 6,
                "update_hint": true
            },
            "expected_output": "rendered=\"\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┐\\n │                                                              │\\n [ASCII grid characters used for table borders]───────────────────────────────────────────────────────── 0[content of the first header row]6 ┘\\n\\n\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┐\\n │ ██████████                                                   │\\n [ASCII grid characters used for table borders]───────────────────────────────────────────────────────── 1[content of the first header row]6 ┘\\n\\n\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┐\\n │ ████████████████████                                         │\\n [ASCII grid characters used for table borders]───────────────────────────────────────────────────────── 2[content of the first header row]6 ┘\\n  1\\n\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┐\\n │ ██████████████████████████████                               │\\n [ASCII grid characters used for table borders]───────────────────────────────────────────────────────── 3[content of the first header row]6 ┘\\n  2\\n\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┐\\n │ ████████████████████████████████████████                     │\\n [ASCII grid characters used for table borders]───────────────────────────────────────────────────────── 4[content of the first header row]6 ┘\\n  3\\n\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┐\\n │ ██████████████████████████████████████████████████           │\\n [ASCII grid characters used for table borders]───────────────────────────────────────────────────────── 5[content of the first header row]6 ┘\\n  4\\n\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┐\\n │ ████████████████████████████████████████████████████████████ │\\n [ASCII grid characters used for table borders]───────────────────────────────────────────────────────── 6[content of the first header row]6 ┘\\n  5\\n\\n [ASCII grid characters used for table borders]──────────────────────────────────────────────────────────────┐\\n │ ████████████████████████████████████████████████████████████ │\\n [ASCII grid characters used for table borders]───────────────────────────────────────────────────────── 6[content of the first header row]6 ┘\\n\\n\"\n"
        }
    ]
}
```

---

### Feature 14: Spinner Around Work

**As a developer**, I want to run work while a spinner is active, so I can decorate long-running work without changing its result.

**Expected Behavior [content of the first header row] Usage:**

The adapter receives a command object containing a spinner message and a return value for the work operation. It must execute the operation through the spinner wrapper and print `value=<json>` containing the operation result. The spinner presentation must not alter or wrap the returned value.

**Test Cases:** `rcb_tests[content of the first header row]public_test_cases[content of the first header row]feature14_spinner_while_working.json`

```json
{
    "description": "A spinner executes a callback and returns the callback result without changing that value.",
    "cases": [
        {
            "input": {
                "action": "spinner_while_working",
                "message": "Loading",
                "return_value": "result"
            },
            "expected_output": "value=\"result\"\n"
        }
    ]
}
```

---

### Feature 15: Pause for Acknowledgement

**As a developer**, I want to wait for a continue key, so I can pause a flow until the user acknowledges a message.

**Expected Behavior [content of the first header row] Usage:**

The adapter receives a command object containing an optional pause message, key tokens, and an optional non-interactive flag. It must return `value=<json>` and `transcript=<json>`. In interactive mode, pressing enter acknowledges the pause and returns true while the transcript includes the message. In non-interactive mode, the pause does not render a prompt transcript and returns false.

**Test Cases:** `rcb_tests[content of the first header row]public_test_cases[content of the first header row]feature15_pause_for_acknowledgement.json`

```json
{
    "description": "Pause waits for acknowledgement and returns true after enter; in non-interactive mode it produces no prompt transcript and returns true.",
    "cases": [
        {
            "input": {
                "action": "pause_for_acknowledgement",
                "message": "Press enter to continue...",
                "keys": [
                    "ENTER"
                ]
            },
            "expected_output": "value=true\ntranscript=\"\\n Press enter to continue...\\n\\n Press enter to continue...\\n\\n\"\n"
        }
    ]
}
```

---

### Feature 16: Unicode-Aware Word Wrapping

**As a developer**, I want to wrap text by visible width, so I can format multilingual and emoji text without corrupting graphemes.

**Expected Behavior [content of the first header row] Usage:**

The adapter receives a command object containing text, target width, line-break string, and a long-word cutting flag. It must return `value=<json>` containing the wrapped text. The wrapper must preserve multibyte letters, emoji, combined emoji sequences, blank lines, and the configured break string while respecting visible display width; when long-word cutting is enabled, over-width words may be split.

**Test Cases:** `rcb_tests[content of the first header row]public_test_cases[content of the first header row]feature16_unicode_word_wrap.json`

```json
{
    "description": "Unicode-aware word wrapping splits text by visible width while preserving multibyte characters, emoji, combined emoji sequences, blank lines, and optional long-word cutting.",
    "cases": [
        {
            "input": {
                "action": "unicode_word_wrap",
                "text": "This is a story all about how my life got flippêd turnêd upsidê down and I'd likê to takê a minutê just sit right thêrê I'll têll you how I bêcamê thê princê of a town callêd Bêl-Air",
                "width": 18,
                "break": "\n",
                "cut": false
            },
            "expected_output": "value=\"This is a story\\nall about how my\\nlife got flippêd\\nturnêd upsidê down\\nand I'd likê to\\ntakê a minutê just\\nsit right thêrê\\nI'll têll you how\\nI bêcamê thê\\nprincê of a town\\ncallêd Bêl-Air\"\n"
        },
        {
            "input": {
                "action": "unicode_word_wrap",
                "text": "This is a 📖 all about how my life got 🌀 turned upside ⬇️ and I'd like to take a minute just sit right there I'll tell you how I became the prince of a town called Bel-Air",
                "width": 13,
                "break": "\n",
                "cut": false
            },
            "expected_output": "value=\"This is a 📖\\nall about how\\nmy life got\\n🌀 turned\\nupside ⬇️ and\\nI'd like to\\ntake a minute\\njust sit\\nright there\\nI'll tell you\\nhow I became\\nthe prince of\\na town called\\nBel-Air\"\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution[content of the first header row]Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests[content of the first header row]public_test_cases[content of the first header row]`. A single entry point `bash rcb_tests[content of the first header row]test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests[content of the first header row]stdout[content of the first header row]<cases-dir>[content of the first header row]{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests[content of the first header row]stdout[content of the first header row]public_test_cases[content of the first header row]feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS[content of the first header row]FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- see the wrapper script for 'ctrl submission logic'
- check the test file for 'reission regulator'
