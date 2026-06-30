## Product Requirement Document

# Headless Autosuggest Field — An Interactive, Accessible Type-Ahead Suggestion Component

## Project Goal

Build a reusable type-ahead (autosuggest / combobox) text-field component that lets developers add a fully interactive suggestion experience — keyboard navigation, mouse selection, asynchronous suggestion loading, multi-group results, and screen-reader accessibility — without re-implementing the intricate focus/selection state machine every time.

---

## Background & Problem

A type-ahead field looks simple but hides a deep interaction state machine: when to show or hide the suggestion list, how the keyboard moves a highlight through it (with wrap-around), how the displayed text tracks the highlighted item yet can be reverted, what counts as "selecting" an item by mouse versus keyboard, when to ask the host to fetch or clear results, and how to stay accessible to assistive technology throughout. Hand-rolling this per project leads to subtle, inconsistent bugs.

This component owns that state machine and delegates only the *data* concerns to the host application: the host decides which candidates match a value, how to turn a candidate into its textual value, and how to render a candidate. The component decides *when* suggestions are visible, *which* one is highlighted, *what* the field shows, and *which* notifications fire — and it keeps the field accessible the whole time.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain. This is a non-trivial domain (interaction state machine, view rendering, host adapter); it MUST be a clear multi-file tree (core state/logic, view layer, and the execution adapter kept separate), not a single god file. Do not over-engineer, but do not collapse distinct responsibilities.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box contract for the execution adapter**, NOT the internal data model of the component. The core interaction logic must be decoupled from stdin/stdout and JSON parsing. The adapter is solely responsible for translating a JSON scenario into idiomatic interactions against the component and serialising the observable result.

3. **Adherence to SOLID Design Principles:** Separate parsing/routing, the interaction state machine, the view, the host-data callbacks, and output formatting into distinct cohesive units; depend on abstractions, keep the public surface idiomatic.

4. **Robustness & Interface Design:** Handle edge cases gracefully (no matches, navigation past the ends of the list, time-delayed results, empty values). Errors should be modeled properly rather than via generic faults.

---

## Execution Adapter Contract (shared by every feature)

The execution adapter reads ONE JSON object from stdin describing a scenario, drives a single instance of the component through it, and prints an observable snapshot to stdout. The scenario object has three keys: `config`, `actions`, and `observe`.

### `config` — how the component and its host are wired

- `mode`: `"single"` (a flat candidate list) or `"multi"` (candidates grouped into titled sections). Default `"single"`.
- `dataset` (single mode): an array of candidate objects, each at least `{ "name": <string> }`. The host's matcher returns every candidate whose `name` starts with the current value, compared case-insensitively, after trimming the value. A candidate's textual value is its `name`.
- `sections` (multi mode): an array of `{ "title": <string>, "languages": [ {"name": ...}, ... ] }`. The host's matcher filters each group's items by the same case-insensitive prefix rule and drops groups left empty; group order is preserved.
- `shouldRender`: the host predicate deciding whether a value is even eligible to show suggestions: `"default"` = the trimmed value is non-empty; `"nonEmptyNoLeadingSpace"` = trimmed value non-empty AND its first character is not a space; `"alwaysTrue"` = always eligible. Default `"default"`.
- `alwaysRenderSuggestions` (bool): when true, matching suggestions are always shown (even before focus and while blurred) and selection never hides them. Default false.
- `focusFirstSuggestion` (bool): when true, as soon as a fresh set of matches appears the first item is auto-highlighted. Default false.
- `focusInputOnSuggestionClick` (bool): when true (default) clicking a suggestion returns keyboard focus to the field; when false, focus is not returned and the field emits a blur notification.
- `async` (bool): when true the host delivers matches on a 1[zero (indicating no matches)][zero (indicating no matches)]ms timer instead of synchronously, and discards results whose originating value no longer matches the current value. Default false.
- `emptyReturnsNone` (bool): when true the host's matcher returns nothing for an empty/whitespace value. Default false.
- `highlight` (bool): when true the renderer wraps the matched leading portion of each candidate in emphasis markup; otherwise it renders the plain name. Default false.

### `actions` — the interaction sequence (applied in order)

Each action is `{ "type": <verb>, ... }`:

- `focus` / `blur` — focus or blur the text field.
- `type` `{ "value": <s> }` — set the field's text to `<s>` and fire the change.
- `focusAndType` `{ "value": <s> }` — focus, then `type`.
- `arrowDown` / `arrowUp` `{ "count": <n=1> }` — press the key `n` times.
- `enter` — press Enter.
- `escape` — press Escape.
- `mouseEnter` / `mouseLeave` `{ "index": <i> }` — move the mouse onto / off the i-th visible suggestion.
- `clickSuggestion` `{ "index": <i> }` — perform a full mouse click on the i-th visible suggestion.
- `clickSuggestionsContainer` — click inside the suggestions container but not on a suggestion.
- `clickClearButton` — activate the host-provided "clear" control.
- `tick` `{ "ms": <n> }` — advance virtual time by `n` milliseconds (drives async delivery).
- `clearEvents` — reset the captured notification log (so a later `events` observation shows only what happened afterwards).

### `observe` — what to print, in order

The output is the concatenation of one block per requested observation, each terminated by a newline. Observation keys and their exact line formats:

- `value` → `value=<field text>`
- `suggestions` → `suggestions=<count>` then, for each visible suggestion in order, a line `  [<index>] <suggestion text>`
- `focused` → `focused=<highlighted suggestion text>`, or `focused=([a specific sentinel state representing 'no value'])` when nothing is highlighted
- `expanded` → `expanded=true` or `expanded=false` (whether the list is exposed as expanded)
- `activedescendant` → `activedescendant=present` when a highlighted suggestion is advertised to assistive tech, else `activedescendant=absent`
- `role` → three lines: `inputRole=<role>`, `listRole=<role or ([a specific sentinel state representing 'no value'])>`, `suggestionRole=<role of first option or ([a specific sentinel state representing 'no value'])>`
- `titles` → `titles=<count>` then, for each visible section title, `  [<index>] <title text>`
- `inputFocused` → `inputFocused=true` or `inputFocused=false` (does the field currently hold keyboard focus)
- `inputAttr:<name>` → `inputAttr <name>=<attribute value, or (null) if absent>`
- `suggestionHTML:<i>` → `suggestionHTML[<i>]=<inner markup of the i-th suggestion>`
- `titleHTML:<i>` → `titleHTML[<i>]=<inner markup of the i-th section title>`
- `containerClass` → `containerClass=<class attribute of the outer container>`

The notification log observation:

- `events` → `events=<count>` then one indented line per notification, in fire order. Notification grammar:
  - `  change method=<m> newValue=<v>` — the field value changed; `<m>` is one of `type`, `down`, `up`, `click`, `enter`, `escape`.
  - `  focus` — the field gained focus.
  - `  blur focusedSuggestion=<name or null>` — the field lost focus; reports the suggestion highlighted at that moment.
  - `  suggestionSelected value=<v> section=<index or null> method=<m>` — a suggestion was selected; `<m>` is `enter` or `click`.
  - `  fetch value=<v>` — the host was asked to fetch suggestions for `<v>`.
  - `  clear` — the host was asked to clear suggestions.

A change notification is only emitted when the new value actually differs from the current value.

---

## Core Features


### Feature 1: Showing and Hiding Suggestions

**As a developer**, I want suggestions to appear only when they are useful and disappear when the user moves on, so the field is not cluttered.

**Expected Behavior / Usage:**

Suggestions are visible only when all of these hold: the field is focused, the current value passes the host's render predicate, and the host returned at least one match. Typing a matching value shows the matches; a value that matches nothing, or that fails the predicate (such as one beginning with a space under the no-leading-space predicate), shows [a specific sentinel state representing 'no value']. Pressing Escape or blurring the field hides the list; focusing the field again re-shows the matches for the current value.

**Test Cases:** `rcb_tests/public_test_cases/feature1_show_hide_suggestions.json`

```json
{
  "description": "Drive the component through focusing the text field and typing, then observe which suggestions are visible. Suggestions become visible only while the field is focused, the typed value passes the host's render predicate, and at least one candidate matches the value as a case-insensitive prefix. Pressing Escape or blurring the field hides them; focusing again re-shows the matches. A value that fails the render predicate (e.g. one that begins with a space) or that matches nothing yields no visible suggestions.",
  "cases": [
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace"
        },
        "actions": [
          {
            "type": "focusAndType",
            "value": "p"
          }
        ],
        "observe": [
          "value",
          "suggestions"
        ]
      },
      "expected_output": "value=p\nsuggestions=3\n  [[zero (indicating no matches)]] Perl\n  [1] PHP\n  [2] Python\n"
    },
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace"
        },
        "actions": [
          {
            "type": "focusAndType",
            "value": "z"
          }
        ],
        "observe": [
          "value",
          "suggestions"
        ]
      },
      "expected_output": "value=z\nsuggestions=[zero (indicating no matches)]\n"
    }
  ]
}
```

---

### Feature 2: Keyboard Navigation With Wrap-Around

**As a developer**, I want arrow keys to move a highlight through the suggestions, so the user can pick one without the mouse.

**Expected Behavior / Usage:**

While suggestions are visible, Down highlights the first item and advances one item per press; pressing Down past the last item clears the highlight (a '[a specific sentinel state representing 'no value']' state), and one more Down returns to the first — a full cycle of length count+1. Up is the mirror image, starting from the last item and wrapping symmetrically. Whenever an item is highlighted the field's displayed text mirrors that item's value. If the suggestions are currently hidden, the first arrow press merely reveals the list again with nothing highlighted.

**Test Cases:** `rcb_tests/public_test_cases/feature2_keyboard_navigation.json`

```json
{
  "description": "With suggestions visible, the Down and Up arrow keys move a highlight through the list. Down starts at the first item and advances; after passing the last item the highlight wraps to '[a specific sentinel state representing 'no value']' and then back to the first. Up starts at the last item and moves backward, wrapping symmetrically. While an item is highlighted the field's displayed value mirrors that item's value. If suggestions are currently hidden, the first arrow press only reveals them again with no item highlighted.",
  "cases": [
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace"
        },
        "actions": [
          {
            "type": "focusAndType",
            "value": "p"
          },
          {
            "type": "arrowDown",
            "count": 1
          }
        ],
        "observe": [
          "value",
          "focused"
        ]
      },
      "expected_output": "value=Perl\nfocused=Perl\n"
    },
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace"
        },
        "actions": [
          {
            "type": "focusAndType",
            "value": "p"
          },
          {
            "type": "arrowDown",
            "count": 4
          }
        ],
        "observe": [
          "value",
          "focused"
        ]
      },
      "expected_output": "value=p\nfocused=([a specific sentinel state representing 'no value'])\n"
    }
  ]
}
```

---

### Feature 3: Mouse Highlighting

**As a developer**, I want hovering a suggestion to highlight it and leaving to unhighlight, so mouse users get feedback.

**Expected Behavior / Usage:**

Moving the mouse onto a suggestion highlights it; moving it off clears the highlight. A subtle interaction with the value: if the user highlighted an item by mouse and then presses Up from the first item (or Down from the last item, i.e. moves the highlight off the ends), the field shows the value the user originally typed rather than an item value.

**Test Cases:** `rcb_tests/public_test_cases/feature3_mouse_focus.json`

```json
{
  "description": "Moving the mouse onto a suggestion highlights it; moving the mouse off clears the highlight. After highlighting an item by mouse, pressing Up from the first item (or Down from the last item) restores the originally typed value rather than an item value.",
  "cases": [
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace"
        },
        "actions": [
          {
            "type": "focusAndType",
            "value": "p"
          },
          {
            "type": "mouseEnter",
            "index": 2
          }
        ],
        "observe": [
          "focused"
        ]
      },
      "expected_output": "focused=Python\n"
    },
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace"
        },
        "actions": [
          {
            "type": "focusAndType",
            "value": "p"
          },
          {
            "type": "mouseEnter",
            "index": 2
          },
          {
            "type": "mouseLeave",
            "index": 2
          }
        ],
        "observe": [
          "focused"
        ]
      },
      "expected_output": "focused=([a specific sentinel state representing 'no value'])\n"
    }
  ]
}
```

---

### Feature 4: Two-Stage Escape

**As a developer**, I want Escape to first dismiss the list and then clear the field, so users can back out in a predictable way.

**Expected Behavior / Usage:**

When suggestions are visible, the first Escape hides them and leaves the typed value untouched. With suggestions already hidden, Escape clears the field to empty. If suggestions were never shown for the value, a single Escape clears the field. However, if the user had been navigating with Up/Down, Escape instead reverts the field to the value typed before navigation began (and does not clear).

**Test Cases:** `rcb_tests/public_test_cases/feature4_escape_behavior.json`

```json
{
  "description": "Escape has two stages. When suggestions are visible, the first Escape hides them without changing the typed value. A subsequent Escape (now that suggestions are hidden) clears the field to empty. If suggestions were never shown for the value, a single Escape clears the field. If the user had navigated with Up/Down first, Escape instead reverts the field to the value typed before navigation.",
  "cases": [
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace"
        },
        "actions": [
          {
            "type": "focusAndType",
            "value": "p"
          },
          {
            "type": "escape"
          }
        ],
        "observe": [
          "value",
          "suggestions"
        ]
      },
      "expected_output": "value=p\nsuggestions=[zero (indicating no matches)]\n"
    },
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace"
        },
        "actions": [
          {
            "type": "focusAndType",
            "value": "p"
          },
          {
            "type": "escape"
          },
          {
            "type": "escape"
          }
        ],
        "observe": [
          "value",
          "suggestions"
        ]
      },
      "expected_output": "value=\nsuggestions=[zero (indicating no matches)]\n"
    }
  ]
}
```

---

### Feature 5: Selecting With Enter

**As a developer**, I want Enter to choose the highlighted suggestion, so keyboard users can commit a choice.

**Expected Behavior / Usage:**

Pressing Enter while a suggestion is highlighted selects it: a selection notification fires carrying the chosen value, the section index (null for a flat list), and method `enter`; the field shows the chosen value; and the suggestions are hidden afterwards. Pressing Enter with nothing highlighted fires no selection and still hides the list. (The example resets the notification log immediately before pressing Enter.)

**Test Cases:** `rcb_tests/public_test_cases/feature5_select_with_enter.json`

```json
{
  "description": "Pressing Enter while a suggestion is highlighted selects it: a selection event is emitted carrying the selected value, the section index (null for a flat list) and the method 'enter', and the suggestions are hidden afterwards. The displayed value reflects the highlighted item. Pressing Enter with no highlighted suggestion emits no selection event but still hides the suggestions. The events log here is captured from the moment just before Enter is pressed.",
  "cases": [
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace"
        },
        "actions": [
          {
            "type": "focusAndType",
            "value": "j"
          },
          {
            "type": "clearEvents"
          },
          {
            "type": "arrowDown",
            "count": 1
          },
          {
            "type": "enter"
          }
        ],
        "observe": [
          "value",
          "suggestions",
          "events"
        ]
      },
      "expected_output": "value=Java\nsuggestions=[zero (indicating no matches)]\nevents=3\n  change method=down newValue=Java\n  suggestionSelected value=Java section=null method=enter\n  clear\n"
    },
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace"
        },
        "actions": [
          {
            "type": "focusAndType",
            "value": "j"
          },
          {
            "type": "clearEvents"
          },
          {
            "type": "enter"
          }
        ],
        "observe": [
          "value",
          "suggestions",
          "events"
        ]
      },
      "expected_output": "value=j\nsuggestions=[zero (indicating no matches)]\nevents=[zero (indicating no matches)]\n"
    }
  ]
}
```

---

### Feature 6: Selecting With a Click

**As a developer**, I want clicking a suggestion to choose it and keep the field usable, so mouse users can commit a choice.

**Expected Behavior / Usage:**

Clicking a suggestion sets the field to the clicked item's value, fires a change notification with method `click` followed by a selection notification with method `click`, then a clear request, and — by default — returns keyboard focus to the field. (The example resets the notification log immediately before the click.)

**Test Cases:** `rcb_tests/public_test_cases/feature6_select_with_click.json`

```json
{
  "description": "Clicking a suggestion selects it: the displayed value becomes the clicked item's value, a change event with method 'click' is emitted followed by a selection event with method 'click', the suggestions are then cleared, and (by default) keyboard focus is returned to the text field. The events log here is captured from the moment just before the click.",
  "cases": [
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace"
        },
        "actions": [
          {
            "type": "focusAndType",
            "value": "p"
          },
          {
            "type": "clearEvents"
          },
          {
            "type": "clickSuggestion",
            "index": 1
          }
        ],
        "observe": [
          "value",
          "suggestions",
          "inputFocused",
          "events"
        ]
      },
      "expected_output": "value=PHP\nsuggestions=[zero (indicating no matches)]\ninputFocused=true\nevents=3\n  change method=click newValue=PHP\n  suggestionSelected value=PHP section=null method=click\n  clear\n"
    }
  ]
}
```

---

### Feature 7: Tagged Change Notifications

**As a developer**, I want each value change tagged with its cause, so the host can react appropriately.

**Expected Behavior / Usage:**

Every change to the field value is reported with the method that caused it: `type` for edits, `down`/`up` for navigation that lands on a different value, `click` for a clicked suggestion, and `escape` for an Escape that resets the value. Crucially, no change notification fires when the resulting value would equal the current value (for example, navigating onto an item whose value already matches the field). (Each example resets the notification log immediately before the final interaction.)

**Test Cases:** `rcb_tests/public_test_cases/feature7_change_event_methods.json`

```json
{
  "description": "Every programmatic change to the field's value is reported through a change event tagged with the method that caused it: 'type' when the user edits the text, 'down'/'up' when navigation moves the value to a different item, 'click' when a suggestion is clicked, and 'escape' when Escape resets the value. No change event is emitted when the resulting value would be identical to the current value (for example navigating onto an item whose value already equals the field). The events log here is captured from the moment just before the final interaction.",
  "cases": [
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace"
        },
        "actions": [
          {
            "type": "focusAndType",
            "value": "c"
          },
          {
            "type": "clearEvents"
          },
          {
            "type": "type",
            "value": "c+"
          }
        ],
        "observe": [
          "events"
        ]
      },
      "expected_output": "events=2\n  change method=type newValue=c+\n  fetch value=c+\n"
    },
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace"
        },
        "actions": [
          {
            "type": "focusAndType",
            "value": "c"
          },
          {
            "type": "clearEvents"
          },
          {
            "type": "arrowDown",
            "count": 1
          }
        ],
        "observe": [
          "events"
        ]
      },
      "expected_output": "events=1\n  change method=down newValue=C\n"
    }
  ]
}
```

---

### Feature 8: Fetch and Clear Requests

**As a developer**, I want the component to tell my host exactly when to load or drop suggestions, so I control the data.

**Expected Behavior / Usage:**

A fetch request (carrying the current value) is made when the user types a value that passes the render predicate. A clear request is made when the field is blurred, when Escape closes the list, and when a typed value fails the predicate. Focus and blur notifications are also reported. (Each example resets the notification log immediately before the final interaction.)

**Test Cases:** `rcb_tests/public_test_cases/feature8_fetch_and_clear_requests.json`

```json
{
  "description": "The component asks the host to fetch suggestions (passing the current value) and to clear suggestions, at well-defined moments. A fetch is requested when the user types a value that passes the render predicate. Clearing is requested when the field is blurred, when Escape closes the suggestions, and when the typed value fails the render predicate. The events log here is captured from a reset point so only the events caused by the final interaction are shown; focus and blur notifications are included.",
  "cases": [
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace"
        },
        "actions": [
          {
            "type": "focus"
          },
          {
            "type": "clearEvents"
          },
          {
            "type": "type",
            "value": "j"
          }
        ],
        "observe": [
          "events"
        ]
      },
      "expected_output": "events=2\n  change method=type newValue=j\n  fetch value=j\n"
    },
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace"
        },
        "actions": [
          {
            "type": "focusAndType",
            "value": "p"
          },
          {
            "type": "clearEvents"
          },
          {
            "type": "blur"
          }
        ],
        "observe": [
          "events"
        ]
      },
      "expected_output": "events=2\n  blur focusedSuggestion=null\n  clear\n"
    }
  ]
}
```

---

### Feature 9: Click Without Refocusing the Field

**As a developer**, I want the option for a suggestion click to NOT refocus the field, so I can move focus elsewhere after selection.

**Expected Behavior / Usage:**

When configured not to return focus on click, clicking a suggestion leaves the field unfocused and fires a blur notification whose payload reports the suggestion that was highlighted at blur time (the clicked item). A clear request is also made. (The example resets the notification log immediately before the click.)

**Test Cases:** `rcb_tests/public_test_cases/feature9_blur_on_click_when_focus_not_retained.json`

```json
{
  "description": "When the component is configured NOT to return focus to the field after a suggestion click, clicking a suggestion leaves the field unfocused and emits a blur event whose payload reports the suggestion that was focused at blur time (the clicked item). A clear-suggestions request is also emitted. The events log here is captured from just before the click.",
  "cases": [
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace",
          "focusInputOnSuggestionClick": false
        },
        "actions": [
          {
            "type": "focusAndType",
            "value": "p"
          },
          {
            "type": "clearEvents"
          },
          {
            "type": "clickSuggestion",
            "index": 1
          }
        ],
        "observe": [
          "inputFocused",
          "events"
        ]
      },
      "expected_output": "inputFocused=false\nevents=4\n  change method=click newValue=PHP\n  suggestionSelected value=PHP section=null method=click\n  clear\n  blur focusedSuggestion=PHP\n"
    }
  ]
}
```

---

### Feature 1[zero (indicating no matches)]: Auto-Focusing the First Suggestion

**As a developer**, I want the first match pre-highlighted, so Enter immediately accepts the most likely choice.

**Expected Behavior / Usage:**

When auto-focus is enabled, every time a fresh set of matches appears the first item is highlighted automatically — including when retyping yields the same matches, and after blurring and refocusing. From the auto-focused state, Down advances to the second item and a further Down past the last clears the highlight. Enter selects the auto-focused item and hides the list; Enter when there are no matches simply leaves the typed value unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature1[zero (indicating no matches)]_focus_first_suggestion.json`

```json
{
  "description": "When configured to auto-focus the first suggestion, typing a value that yields matches immediately highlights the first item (and keeps highlighting the first item when the same matches are shown again, or after blur+refocus). From this auto-focused state, Down advances to the second item and one more Down past the last clears the highlight. Pressing Enter selects the auto-focused item and hides suggestions; pressing Enter when there are no suggestions simply leaves the typed value unchanged.",
  "cases": [
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace",
          "focusFirstSuggestion": true
        },
        "actions": [
          {
            "type": "focusAndType",
            "value": "j"
          }
        ],
        "observe": [
          "focused"
        ]
      },
      "expected_output": "focused=Java\n"
    },
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace",
          "focusFirstSuggestion": true
        },
        "actions": [
          {
            "type": "focusAndType",
            "value": "j"
          },
          {
            "type": "arrowDown",
            "count": 1
          }
        ],
        "observe": [
          "focused"
        ]
      },
      "expected_output": "focused=Javascript\n"
    }
  ]
}
```

---

### Feature 11: Always-Rendered Suggestions

**As a developer**, I want a mode where the list is always visible, so the field behaves like an open picker.

**Expected Behavior / Usage:**

In always-render mode the matching list is visible from the start and remains visible through focus and blur. Typing narrows it. Arrow keys still highlight items. Enter on a highlighted item re-fetches around the selected value (so the list updates to just that item) but does not hide it; Enter with nothing highlighted leaves the full match list shown. Escape without prior navigation clears the field; Escape after navigation reverts the value and removes the highlight. Clicking an item updates the list to that item but keeps it shown.

**Test Cases:** `rcb_tests/public_test_cases/feature11_always_render_suggestions.json`

```json
{
  "description": "When configured to always render suggestions, the matching list is visible from the start and stays visible through focus and blur. Typing narrows the list to the matches. Arrow keys still highlight items. Pressing Enter on a highlighted item re-fetches around the selected value (so the list updates to just that item) but does not hide the list; Enter with nothing highlighted leaves the full match list shown. Escape without prior navigation clears the field; Escape after Up/Down reverts the value and removes the highlight. Clicking an item updates the list to that item but keeps suggestions shown.",
  "cases": [
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace",
          "alwaysRenderSuggestions": true
        },
        "actions": [],
        "observe": [
          "suggestions"
        ]
      },
      "expected_output": "suggestions=14\n  [[zero (indicating no matches)]] C\n  [1] C#\n  [2] C++\n  [3] Clojure\n  [4] Elm\n  [5] Go\n  [6] Haskell\n  [7] Java\n  [8] Javascript\n  [9] Perl\n  [1[zero (indicating no matches)]] PHP\n  [11] Python\n  [12] Ruby\n  [13] Scala\n"
    },
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace",
          "alwaysRenderSuggestions": true
        },
        "actions": [
          {
            "type": "focusAndType",
            "value": "p"
          },
          {
            "type": "arrowDown",
            "count": 1
          },
          {
            "type": "enter"
          }
        ],
        "observe": [
          "suggestions"
        ]
      },
      "expected_output": "suggestions=1\n  [[zero (indicating no matches)]] Perl\n"
    }
  ]
}
```

---

### Feature 12: Grouped (Multi-Section) Suggestions

**As a developer**, I want suggestions organised into titled groups, so related results are visually clustered.

**Expected Behavior / Usage:**

In multi-section mode the visible suggestions are the flattened, in-order concatenation of all non-empty groups, and each visible group shows a title. A selection reports the [zero (indicating no matches)]-based index of the section the chosen item belongs to. The flat highlight index produced by arrow keys maps onto the correct section. A host clear control can reset the field and re-show the full grouped set.

**Test Cases:** `rcb_tests/public_test_cases/feature12_multi_section.json`

```json
{
  "description": "In multi-section mode suggestions are organised into titled groups. The visible suggestions are the flattened concatenation of all non-empty groups in order, and each visible group renders a section title. A selection event reports the index of the section the chosen item belongs to ([zero (indicating no matches)]-based). The flat highlight index produced by arrow keys maps onto the correct section. A host 'clear' control can reset the field and re-show the full set of grouped suggestions.",
  "cases": [
    {
      "input": {
        "config": {
          "mode": "multi",
          "sections": [
            {
              "title": "C",
              "languages": [
                {
                  "name": "C",
                  "year": 1972
                },
                {
                  "name": "C#",
                  "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
                },
                {
                  "name": "C++",
                  "year": 1983
                },
                {
                  "name": "Clojure",
                  "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
                }
              ]
            },
            {
              "title": "E",
              "languages": [
                {
                  "name": "Elm",
                  "year": 2[zero (indicating no matches)]12
                }
              ]
            },
            {
              "title": "G",
              "languages": [
                {
                  "name": "Go",
                  "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
                }
              ]
            },
            {
              "title": "H",
              "languages": [
                {
                  "name": "Haskell",
                  "year": 199[zero (indicating no matches)]
                }
              ]
            },
            {
              "title": "J",
              "languages": [
                {
                  "name": "Java",
                  "year": 1995
                },
                {
                  "name": "Javascript",
                  "year": 1995
                }
              ]
            },
            {
              "title": "P",
              "languages": [
                {
                  "name": "Perl",
                  "year": 1987
                },
                {
                  "name": "PHP",
                  "year": 1995
                },
                {
                  "name": "Python",
                  "year": 1991
                }
              ]
            },
            {
              "title": "R",
              "languages": [
                {
                  "name": "Ruby",
                  "year": 1995
                }
              ]
            },
            {
              "title": "S",
              "languages": [
                {
                  "name": "Scala",
                  "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
                }
              ]
            }
          ],
          "shouldRender": "alwaysTrue"
        },
        "actions": [
          {
            "type": "focus"
          }
        ],
        "observe": [
          "suggestions"
        ]
      },
      "expected_output": "suggestions=14\n  [[zero (indicating no matches)]] C\n  [1] C#\n  [2] C++\n  [3] Clojure\n  [4] Elm\n  [5] Go\n  [6] Haskell\n  [7] Java\n  [8] Javascript\n  [9] Perl\n  [1[zero (indicating no matches)]] PHP\n  [11] Python\n  [12] Ruby\n  [13] Scala\n"
    },
    {
      "input": {
        "config": {
          "mode": "multi",
          "sections": [
            {
              "title": "C",
              "languages": [
                {
                  "name": "C",
                  "year": 1972
                },
                {
                  "name": "C#",
                  "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
                },
                {
                  "name": "C++",
                  "year": 1983
                },
                {
                  "name": "Clojure",
                  "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
                }
              ]
            },
            {
              "title": "E",
              "languages": [
                {
                  "name": "Elm",
                  "year": 2[zero (indicating no matches)]12
                }
              ]
            },
            {
              "title": "G",
              "languages": [
                {
                  "name": "Go",
                  "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
                }
              ]
            },
            {
              "title": "H",
              "languages": [
                {
                  "name": "Haskell",
                  "year": 199[zero (indicating no matches)]
                }
              ]
            },
            {
              "title": "J",
              "languages": [
                {
                  "name": "Java",
                  "year": 1995
                },
                {
                  "name": "Javascript",
                  "year": 1995
                }
              ]
            },
            {
              "title": "P",
              "languages": [
                {
                  "name": "Perl",
                  "year": 1987
                },
                {
                  "name": "PHP",
                  "year": 1995
                },
                {
                  "name": "Python",
                  "year": 1991
                }
              ]
            },
            {
              "title": "R",
              "languages": [
                {
                  "name": "Ruby",
                  "year": 1995
                }
              ]
            },
            {
              "title": "S",
              "languages": [
                {
                  "name": "Scala",
                  "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
                }
              ]
            }
          ],
          "shouldRender": "alwaysTrue"
        },
        "actions": [
          {
            "type": "focusAndType",
            "value": "c"
          }
        ],
        "observe": [
          "titles",
          "suggestions"
        ]
      },
      "expected_output": "titles=1\n  [[zero (indicating no matches)]] C\nsuggestions=4\n  [[zero (indicating no matches)]] C\n  [1] C#\n  [2] C++\n  [3] Clojure\n"
    }
  ]
}
```

---

### Feature 13: Asynchronous Suggestions

**As a developer**, I want suggestions that arrive after a delay handled correctly, so stale results never flash.

**Expected Behavior / Usage:**

When the host delivers matches on a timer, the list appears only after time advances. If the value changes before the timer fires, the outdated result is discarded so only matches for the current value appear. After a selection (click or Enter) the list is hidden and stays hidden even as more time passes.

**Test Cases:** `rcb_tests/public_test_cases/feature13_async_suggestions.json`

```json
{
  "description": "When the host resolves suggestions asynchronously (here after a 1[zero (indicating no matches)][zero (indicating no matches)]ms timer) the list only appears once time advances. If the value changes before the timer fires, stale results are discarded so only suggestions matching the current value appear. After a selection (click or Enter) the suggestions are hidden and remain hidden even after further time passes.",
  "cases": [
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "default",
          "async": true,
          "focusFirstSuggestion": true,
          "emptyReturnsNone": true
        },
        "actions": [
          {
            "type": "focusAndType",
            "value": "j"
          },
          {
            "type": "tick",
            "ms": 1[zero (indicating no matches)][zero (indicating no matches)]
          }
        ],
        "observe": [
          "suggestions"
        ]
      },
      "expected_output": "suggestions=2\n  [[zero (indicating no matches)]] Java\n  [1] Javascript\n"
    },
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "default",
          "async": true,
          "focusFirstSuggestion": true,
          "emptyReturnsNone": true
        },
        "actions": [
          {
            "type": "focusAndType",
            "value": "j"
          },
          {
            "type": "tick",
            "ms": 1[zero (indicating no matches)][zero (indicating no matches)]
          },
          {
            "type": "type",
            "value": ""
          },
          {
            "type": "type",
            "value": "p"
          }
        ],
        "observe": [
          "suggestions"
        ]
      },
      "expected_output": "suggestions=[zero (indicating no matches)]\n"
    }
  ]
}
```

---

### Feature 14: Query-Aware Suggestion Rendering

**As a developer**, I want the matched part of each suggestion emphasised against the right query, so matches are obvious.

**Expected Behavior / Usage:**

Each suggestion renders with the matched leading portion wrapped in emphasis markup and the remainder in plain markup. The query used for emphasis is the trimmed text the user originally typed: it stays fixed at the pre-navigation value while Up/Down navigation is active (so navigating does not change which characters are emphasised), and it is unaffected by hovering a suggestion and then leaving it.

**Test Cases:** `rcb_tests/public_test_cases/feature14_suggestion_highlight_query.json`

```json
{
  "description": "Each suggestion is rendered with the portion that matches the current query wrapped in emphasis markup and the remainder in plain markup. The query handed to the renderer is the trimmed value the user originally typed: it is the value-before-navigation while Up/Down navigation is active (so navigating does not change which characters are highlighted), and it is unaffected by hovering a suggestion and then leaving it.",
  "cases": [
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace",
          "highlight": true
        },
        "actions": [
          {
            "type": "focusAndType",
            "value": "r"
          }
        ],
        "observe": [
          "suggestionHTML:[zero (indicating no matches)]"
        ]
      },
      "expected_output": "suggestionHTML[[zero (indicating no matches)]]=<strong>R</strong><span>uby</span>\n"
    },
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace",
          "highlight": true
        },
        "actions": [
          {
            "type": "focusAndType",
            "value": "r"
          },
          {
            "type": "arrowDown",
            "count": 1
          }
        ],
        "observe": [
          "suggestionHTML:[zero (indicating no matches)]"
        ]
      },
      "expected_output": "suggestionHTML[[zero (indicating no matches)]]=<strong>R</strong><span>uby</span>\n"
    }
  ]
}
```

---

### Feature 15: Combobox Accessibility

**As a developer**, I want correct accessibility semantics, so assistive technology can operate the field.

**Expected Behavior / Usage:**

The field advertises combobox semantics: a `combobox` role, list autocomplete, and an expanded flag that is `false` when no suggestions are shown and `true` when they are. When open, the list advertises a `listbox` role and each option an `option` role. The active-descendant pointer is absent until a suggestion is highlighted (by keyboard or mouse) and present while one is, returning to absent when the highlight clears.

**Test Cases:** `rcb_tests/public_test_cases/feature15_aria_attributes.json`

```json
{
  "description": "The text field exposes combobox accessibility semantics: a role of 'combobox', list autocomplete, and an expanded flag that is 'false' when no suggestions are shown and 'true' when they are. When suggestions are open the list exposes a 'listbox' role and each option a role of 'option'. The active-descendant pointer is absent until a suggestion is highlighted (via keyboard or mouse) and becomes present while one is highlighted, returning to absent when the highlight is cleared.",
  "cases": [
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace"
        },
        "actions": [],
        "observe": [
          "inputAttr:role",
          "inputAttr:aria-autocomplete",
          "expanded",
          "activedescendant"
        ]
      },
      "expected_output": "inputAttr role=combobox\ninputAttr aria-autocomplete=list\nexpanded=false\nactivedescendant=absent\n"
    },
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace"
        },
        "actions": [
          {
            "type": "focusAndType",
            "value": "J"
          }
        ],
        "observe": [
          "expanded",
          "role"
        ]
      },
      "expected_output": "expanded=true\ninputRole=combobox\nlistRole=listbox\nsuggestionRole=option\n"
    }
  ]
}
```

---

### Feature 16: Field Attribute Pass-Through

**As a developer**, I want host-supplied field attributes to reach the rendered input, so I can configure it.

**Expected Behavior / Usage:**

Attributes the host supplies for the text field — its id, placeholder, and input type — are passed through to the rendered input element, and the field's displayed value tracks the host-provided value.

**Test Cases:** `rcb_tests/public_test_cases/feature16_input_props_passthrough.json`

```json
{
  "description": "Attributes supplied by the host for the text field (its id, placeholder and input type) are passed through to the rendered input element, and the field's displayed value tracks the host-provided value.",
  "cases": [
    {
      "input": {
        "config": {
          "mode": "single",
          "dataset": [
            {
              "name": "C",
              "year": 1972
            },
            {
              "name": "C#",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)][zero (indicating no matches)]
            },
            {
              "name": "C++",
              "year": 1983
            },
            {
              "name": "Clojure",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]7
            },
            {
              "name": "Elm",
              "year": 2[zero (indicating no matches)]12
            },
            {
              "name": "Go",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]9
            },
            {
              "name": "Haskell",
              "year": 199[zero (indicating no matches)]
            },
            {
              "name": "Java",
              "year": 1995
            },
            {
              "name": "Javascript",
              "year": 1995
            },
            {
              "name": "Perl",
              "year": 1987
            },
            {
              "name": "PHP",
              "year": 1995
            },
            {
              "name": "Python",
              "year": 1991
            },
            {
              "name": "Ruby",
              "year": 1995
            },
            {
              "name": "Scala",
              "year": 2[zero (indicating no matches)][zero (indicating no matches)]3
            }
          ],
          "shouldRender": "nonEmptyNoLeadingSpace"
        },
        "actions": [],
        "observe": [
          "inputAttr:id",
          "inputAttr:placeholder",
          "inputAttr:type",
          "value"
        ]
      },
      "expected_output": "inputAttr id=host-input\ninputAttr placeholder=Type a value\ninputAttr type=search\nvalue=\n"
    }
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the interaction state machine, the view layer, and the host-data integration described above, with core logic decoupled from stdin/stdout and JSON.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON scenario from stdin (`config`, `actions`, `observe`), drives a single component instance through the actions, and prints the requested observations to stdout exactly as specified in the "Execution Adapter Contract" section. It must be logically separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{stem}@{idx:[zero (indicating no matches)]3d}.txt` containing ONLY the raw program stdout, so it can be compared directly against `expected_output`.



---
**Implementation notes:**
- update the selection via the underlying data store using standard indexing
- apply the standard ARIA roles for a structured form input
