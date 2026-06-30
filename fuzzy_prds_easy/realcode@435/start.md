## Product Requirement Document

# Bootstrap-Styled Form Markup Renderer

## Project Goal

Build a server-side HTML form-rendering library that turns a declarative description of a data entity plus per-field rendering options into Bootstrap-styled markup. It lets developers obtain accessible, grid-aware, validation-aware form HTML (labels, inputs, input groups, feedback blocks, buttons) without hand-writing the repetitive class names, ARIA attributes and wrapper `<div>`s that a CSS framework expects.

---

## Background & Problem

Without such a library, developers hand-assemble form markup string by string: every input needs the framework's control class, every label its label class, every validation error its feedback block wired to the input by id, every layout variant (stacked, inline, horizontal grid) a different nest of wrapper divs. This is verbose, easy to get subtly wrong (a missing `aria-describedby`, a misplaced `input-group`), and hard to keep consistent across a codebase.

With this library, the developer describes the entity once (its fields, which are required, which currently have validation errors) and then asks for a field by name; the library emits a complete, correctly-classed, accessible control group. Layout, spacing, validation-feedback presentation and accessibility wiring are all driven by options rather than by hand-written markup.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a non-trivial domain (entity/context modelling, control-type inference, layout strategies, input-group composition, validation feedback, accessibility, button styling). It MUST NOT be a single "god file"; use a clear multi-file structure that separates the context model, the individual widget/control renderers, the layout/alignment strategies, and the output assembly.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a **black-box contract for an execution adapter**, not the internal data model of the renderer. The core rendering logic must be decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating each JSON request into idiomatic calls on the core renderer and serializing the produced markup.

3. **Adherence to SOLID Design Principles:** Separate parsing/routing, context modelling, control rendering, layout strategy, and output formatting into distinct cohesive units; keep the rendering engine open for extension (new control types, new layouts) but closed for modification; keep interfaces small; depend on abstractions, not on concrete I/O.

4. **Robustness & Interface Design:** The public interface must be elegant and idiomatic. Invalid configuration (e.g. an unsupported layout alignment) must be rejected through a well-modelled error rather than producing broken markup.

### Output contract & normalization (read carefully)

Every case's `expected_output` is the **generated HTML**, with one normalization rule applied so the contract is independent of incidental attribute ordering:

- **Within every start tag, attributes are sorted alphabetically by attribute name.** For example a rendered input is emitted as `<input aria-required="true" class="form-control" id="title" name="title" required="required" type="text">` — note `aria-required` before `class` before `id`, etc. Close tags (`</div>`) and text nodes are emitted verbatim.
- HTML special characters are entity-escaped exactly as a browser-safe renderer would (e.g. a literal apostrophe becomes `&#039;`).
- When a request emits several pieces of markup (several controls, or a form tag followed by controls), each piece is printed on its own line, in request order.
- Boolean/markerless HTML attributes that the framework emits as `name="name"` (e.g. `required="required"`) are preserved in that doubled form.

The reference field model used throughout is a single entity with these fields: an integer `id`; a nullable integer `author_id`; a nullable string `title`; a text `body`; a boolean `published` (default off). Unless a case states otherwise, `author_id` and `title` are flagged **required**. A field is rendered as **errored** when the entity carries a validation error message for it.

### Error contract

Invalid input is reported as a single neutral line `error=<category>\n`, never as a host-language exception. The only category exercised here is `error=invalid_alignment` (an unsupported form-layout alignment value).

---

## Core Features


### Feature 1: Basic Labelled Controls

**As a developer**, I want to render a labelled input for an entity field by naming the field, so I get a correctly-classed, accessible control group without hand-writing the label/input markup.

**Expected Behavior / Usage:**

A control group wraps a `<label>` and an `<input>` inside a `<div>` whose class encodes the inferred control type (e.g. `text`, `password`). The input type is inferred from the field's declared data type. The label text is the humanized field name. When the field is flagged **required** by the entity metadata, three things change: the wrapper div gains a `required` marker class; the input gains `required="required"`, an `aria-required="true"` flag, and native HTML5 custom-validity wiring (`data-validity-message`, `oninvalid`, `oninput`); and these are emitted in addition to the base `form-control` class. A non-required field omits all of that and renders just the label and a plain `form-control` input.

**Test Cases:** `rcb_tests/public_test_cases/feature1_basic_controls.json`

```json
{
    "description": "Render a single labelled form control by binding the helper to an entity description and asking for one of its fields. The control type is inferred from the field's declared data type, and the rendered group wraps a label and an input together. When the bound field is marked required by the entity metadata, the input additionally carries native required/validity wiring and an accessibility flag, and the group exposes a required marker class. Output is the generated HTML for the control group.",
    "cases": [
        {
            "input": {
                "steps": [
                    {
                        "op": "article",
                        "set": {
                            "schema.password": {
                                "type": "string"
                            }
                        }
                    },
                    {
                        "op": "create"
                    },
                    {
                        "op": "control",
                        "field": "password",
                        "emit": true
                    }
                ]
            },
            "expected_output": "<div class=\"mb-3 form-group password\"><label class=\"form-label\" for=\"password\">Password</label><input class=\"form-control\" id=\"password\" name=\"password\" type=\"password\"></div>\n"
        },
        {
            "input": {
                "steps": [
                    {
                        "op": "create"
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true
                    }
                ]
            },
            "expected_output": "<div class=\"mb-3 form-group text required\"><label class=\"form-label\" for=\"title\">Title</label><input aria-required=\"true\" class=\"form-control\" data-validity-message=\"This field cannot be left empty\" id=\"title\" name=\"title\" oninput=\"this.setCustomValidity(&#039;&#039;)\" oninvalid=\"this.setCustomValidity(&#039;&#039;); if (!this.value) this.setCustomValidity(this.dataset.validityMessage)\" required=\"required\" type=\"text\"></div>\n"
        }
    ]
}
```

---

### Feature 2: Input-Group Add-ons

**As a developer**, I want to decorate a control with leading or trailing add-ons (icons, text, buttons) inside an input group, so I can build prefixed/suffixed inputs declaratively.

**Expected Behavior / Usage:**

*2.1 Text add-ons*

An `[the order specified by the addon position selector]` (leading) or `append` (trailing) option places static add-on text next to the input, all wrapped in an `input-group` container. A single string yields one `input-group-text` segment; a list of strings yields one segment per element, in order. The labelled control group otherwise renders as usual (label, required wiring) with the input nested inside the input group.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_addon_text.json`

```json
{
    "description": "Wrap a labelled text control in an input group with leading ([the order specified by the addon position selector]) or trailing (append) static text add-ons. A single string yields one add-on segment; a list of strings yields several segments in order. The input sits inside an input-group container together with the add-on segments. Output is the generated HTML for the control group.",
    "cases": [
        {
            "input": {
                "steps": [
                    {
                        "op": "create"
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true,
                        "options": {
                            "[the order specified by the addon position selector]": "@"
                        }
                    }
                ]
            },
            "expected_output": "<div class=\"mb-3 form-group text required\"><label class=\"form-label\" for=\"title\">Title</label><div class=\"input-group\"><span class=\"input-group-text\">@</span><input aria-required=\"true\" class=\"form-control\" data-validity-message=\"This field cannot be left empty\" id=\"title\" name=\"title\" oninput=\"this.setCustomValidity(&#039;&#039;)\" oninvalid=\"this.setCustomValidity(&#039;&#039;); if (!this.value) this.setCustomValidity(this.dataset.validityMessage)\" required=\"required\" type=\"text\"></div></div>\n"
        },
        {
            "input": {
                "steps": [
                    {
                        "op": "create"
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true,
                        "options": {
                            "append": "@"
                        }
                    }
                ]
            },
            "expected_output": "<div class=\"mb-3 form-group text required\"><label class=\"form-label\" for=\"title\">Title</label><div class=\"input-group\"><input aria-required=\"true\" class=\"form-control\" data-validity-message=\"This field cannot be left empty\" id=\"title\" name=\"title\" oninput=\"this.setCustomValidity(&#039;&#039;)\" oninvalid=\"this.setCustomValidity(&#039;&#039;); if (!this.value) this.setCustomValidity(this.dataset.validityMessage)\" required=\"required\" type=\"text\"><span class=\"input-group-text\">@</span></div></div>\n"
        }
    ]
}
```

*2.2 Button add-ons*

When an add-on value is itself rendered button markup, it is embedded directly into the input group before or after the input. Supplying a list of button markups yields several buttons in order. This composes the button renderer (Feature 4) with the input group.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_addon_button.json`

```json
{
    "description": "Wrap a labelled text control in an input group whose add-on is itself a rendered button (or several buttons) placed before or after the input. The button markup is produced by the same helper's button builder and embedded directly into the input group. Output is the generated HTML for the control group.",
    "cases": [
        {
            "input": {
                "steps": [
                    {
                        "op": "create"
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true,
                        "options": {
                            "[the order specified by the addon position selector]": {
                                "_button": "GO"
                            }
                        }
                    }
                ]
            },
            "expected_output": "<div class=\"mb-3 form-group text required\"><label class=\"form-label\" for=\"title\">Title</label><div class=\"input-group\"><button class=\"btn btn-secondary\" type=\"submit\">GO</button><input aria-required=\"true\" class=\"form-control\" data-validity-message=\"This field cannot be left empty\" id=\"title\" name=\"title\" oninput=\"this.setCustomValidity(&#039;&#039;)\" oninvalid=\"this.setCustomValidity(&#039;&#039;); if (!this.value) this.setCustomValidity(this.dataset.validityMessage)\" required=\"required\" type=\"text\"></div></div>\n"
        },
        {
            "input": {
                "steps": [
                    {
                        "op": "create"
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true,
                        "options": {
                            "append": {
                                "_button": "GO"
                            }
                        }
                    }
                ]
            },
            "expected_output": "<div class=\"mb-3 form-group text required\"><label class=\"form-label\" for=\"title\">Title</label><div class=\"input-group\"><input aria-required=\"true\" class=\"form-control\" data-validity-message=\"This field cannot be left empty\" id=\"title\" name=\"title\" oninput=\"this.setCustomValidity(&#039;&#039;)\" oninvalid=\"this.setCustomValidity(&#039;&#039;); if (!this.value) this.setCustomValidity(this.dataset.validityMessage)\" required=\"required\" type=\"text\"><button class=\"btn btn-secondary\" type=\"submit\">GO</button></div></div>\n"
        }
    ]
}
```

*2.3 Add-on container options*

If the last element of an add-on list is an options map, it configures the input-group container itself: a `size` value (e.g. `lg`) adds a sizing modifier class (`input-group-lg`), and any `class`/arbitrary attribute entries are merged onto the container element. Works for both leading and trailing placement.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_addon_options.json`

```json
{
    "description": "Attach add-ons to a labelled control where the final element of the add-on list is an options map applied to the surrounding input-group container. A size option maps to a sizing modifier class on the group, and arbitrary class/attribute entries are merged onto the group element. Both leading and trailing placement are supported. Output is the generated HTML for the control group.",
    "cases": [
        {
            "input": {
                "steps": [
                    {
                        "op": "create"
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true,
                        "options": {
                            "[the order specified by the addon position selector]": [
                                "@",
                                {
                                    "size": "lg"
                                }
                            ]
                        }
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true,
                        "options": {
                            "append": [
                                "@",
                                {
                                    "size": "lg"
                                }
                            ]
                        }
                    }
                ]
            },
            "expected_output": "<div class=\"mb-3 form-group text required\"><label class=\"form-label\" for=\"title\">Title</label><div class=\"input-group input-group-lg\"><span class=\"input-group-text\">@</span><input aria-required=\"true\" class=\"form-control\" data-validity-message=\"This field cannot be left empty\" id=\"title\" name=\"title\" oninput=\"this.setCustomValidity(&#039;&#039;)\" oninvalid=\"this.setCustomValidity(&#039;&#039;); if (!this.value) this.setCustomValidity(this.dataset.validityMessage)\" required=\"required\" type=\"text\"></div></div>\n<div class=\"mb-3 form-group text required\"><label class=\"form-label\" for=\"title\">Title</label><div class=\"input-group input-group-lg\"><input aria-required=\"true\" class=\"form-control\" data-validity-message=\"This field cannot be left empty\" id=\"title\" name=\"title\" oninput=\"this.setCustomValidity(&#039;&#039;)\" oninvalid=\"this.setCustomValidity(&#039;&#039;); if (!this.value) this.setCustomValidity(this.dataset.validityMessage)\" required=\"required\" type=\"text\"><span class=\"input-group-text\">@</span></div></div>\n"
        }
    ]
}
```

*2.4 Add-ons on an errored field*

When the bound field carries a validation error, the input-group container and the outer control group each gain an invalid-state class, the input is marked invalid and linked by `aria-describedby` to a separate feedback `<div>` (identified by `{field}-error`) that carries the error message. Exercised with both leading and trailing add-ons.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_addon_error.json`

```json
{
    "description": "Render a control with an add-on while the bound field carries a validation error. The input-group container and the control group both gain an invalid-state class, the input is marked invalid and linked to a separate feedback block by id, and the feedback block carries the error message. Both leading and trailing add-on placements are exercised. Output is the generated HTML for the control group.",
    "cases": [
        {
            "input": {
                "steps": [
                    {
                        "op": "article",
                        "set": {
                            "errors.title": [
                                "error message"
                            ]
                        },
                        "unset": [
                            "required.title"
                        ]
                    },
                    {
                        "op": "create"
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true,
                        "options": {
                            "[the order specified by the addon position selector]": "@"
                        }
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true,
                        "options": {
                            "append": "@"
                        }
                    }
                ]
            },
            "expected_output": "<div class=\"mb-3 form-group text is-invalid\"><label class=\"form-label\" for=\"title\">Title</label><div class=\"input-group is-invalid\"><span class=\"input-group-text\">@</span><input aria-describedby=\"title-error\" aria-invalid=\"true\" class=\"is-invalid form-control\" id=\"title\" name=\"title\" type=\"text\"></div><div class=\"ms-0 invalid-feedback\" id=\"title-error\">error message</div></div>\n<div class=\"mb-3 form-group text is-invalid\"><label class=\"form-label\" for=\"title\">Title</label><div class=\"input-group is-invalid\"><input aria-describedby=\"title-error\" aria-invalid=\"true\" class=\"is-invalid form-control\" id=\"title\" name=\"title\" type=\"text\"><span class=\"input-group-text\">@</span></div><div class=\"ms-0 invalid-feedback\" id=\"title-error\">error message</div></div>\n"
        }
    ]
}
```

*2.5 Add-ons on standalone widgets*

A leading add-on can also be applied to standalone widgets rendered outside the labelled-control wrapper — single-line text, multi-line text, a select box, a file picker, and a date-time picker. Each widget is nested in an input group next to the add-on segment while keeping its own kind-appropriate styling class.

**Test Cases:** `rcb_tests/public_test_cases/feature2_5_addon_basic_widgets.json`

```json
{
    "description": "Apply a leading add-on directly to standalone form widgets (single-line text, multi-line text, a select box, a file picker, and a date-time picker) rendered outside the labelled-control wrapper. Each widget is placed inside an input-group container next to the add-on segment, and each widget keeps its own appropriate styling class. Output is the generated HTML for each widget in turn.",
    "cases": [
        {
            "input": {
                "steps": [
                    {
                        "op": "article",
                        "set": {
                            "required.title": false
                        }
                    },
                    {
                        "op": "create"
                    },
                    {
                        "op": "text",
                        "field": "title",
                        "options": {
                            "[the order specified by the addon position selector]": "@"
                        }
                    },
                    {
                        "op": "textarea",
                        "field": "title",
                        "options": {
                            "[the order specified by the addon position selector]": "@"
                        }
                    },
                    {
                        "op": "select",
                        "field": "title",
                        "choices": [],
                        "options": {
                            "[the order specified by the addon position selector]": "@"
                        }
                    },
                    {
                        "op": "file",
                        "field": "title",
                        "options": {
                            "[the order specified by the addon position selector]": "@"
                        }
                    },
                    {
                        "op": "dateTime",
                        "field": "title",
                        "options": {
                            "[the order specified by the addon position selector]": "@"
                        }
                    }
                ]
            },
            "expected_output": "<div class=\"input-group\"><span class=\"input-group-text\">@</span><input class=\"form-control\" name=\"title\" type=\"text\"></div>\n<div class=\"input-group\"><span class=\"input-group-text\">@</span><textarea class=\"form-control\" name=\"title\" rows=\"5\"></textarea></div>\n<div class=\"input-group\"><span class=\"input-group-text\">@</span><select class=\"form-select\" name=\"title\"><option value=\"\"></option></select></div>\n<div class=\"input-group\"><span class=\"input-group-text\">@</span><input class=\"form-control\" name=\"title\" type=\"file\"></div>\n<div class=\"input-group\"><span class=\"input-group-text\">@</span><input class=\"form-control\" name=\"title\" step=\"1\" type=\"datetime-local\" value=\"\"></div>\n"
        }
    ]
}
```

---

### Feature 3: Form Opening, Layout & Grid

**As a developer**, I want to open and close forms in different layout alignments and grid configurations, so the same controls can be stacked, inline, or laid out on a horizontal grid.

**Expected Behavior / Usage:**

*3.1 Opening and closing a form*

Opening a form bound to the entity emits a `<form>` start tag carrying the HTTP method, character set, a `role` attribute and the resolved action URL. Closing emits the matching `</form>` tag.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_form_open_close.json`

```json
{
    "description": "Open a form bound to an entity and close it. Opening emits the form start tag with method, charset, a role attribute and the resolved action URL. Closing emits the matching form end tag. Output is the generated markup.",
    "cases": [
        {
            "input": {
                "steps": [
                    {
                        "op": "create",
                        "emit": true
                    }
                ]
            },
            "expected_output": "<form accept-charset=\"utf-8\" action=\"/articles/add\" method=\"post\" role=\"form\">\n"
        },
        {
            "input": {
                "steps": [
                    {
                        "op": "create"
                    },
                    {
                        "op": "end",
                        "emit": true
                    }
                ]
            },
            "expected_output": "</form>\n"
        }
    ]
}
```

*3.2 Layout alignment*

An `align` option selects the layout. `inline` adds inline layout/grid classes to the form tag (and an optional `spacing` overrides the default gutter class); `horizontal` adds a horizontal-layout class. The default (stacked) layout adds no extra class.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_form_alignment.json`

```json
{
    "description": "Open a form in a chosen layout alignment. An inline alignment adds inline layout/grid classes to the form tag, and an optional spacing override replaces the default gutter class. A horizontal alignment adds a horizontal layout class. Output is the generated form start tag.",
    "cases": [
        {
            "input": {
                "steps": [
                    {
                        "op": "create",
                        "options": {
                            "align": "inline"
                        },
                        "emit": true
                    }
                ]
            },
            "expected_output": "<form accept-charset=\"utf-8\" action=\"/articles/add\" class=\"form-inline row g-3 align-items-center\" method=\"post\" role=\"form\">\n"
        },
        {
            "input": {
                "steps": [
                    {
                        "op": "create",
                        "options": {
                            "align": "horizontal"
                        },
                        "emit": true
                    }
                ]
            },
            "expected_output": "<form accept-charset=\"utf-8\" action=\"/articles/add\" class=\"form-horizontal\" method=\"post\" role=\"form\">\n"
        }
    ]
}
```

*3.3 Invalid alignment*

An unsupported `align` value is rejected: the adapter emits the neutral line `error=invalid_alignment` instead of producing markup.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_invalid_alignment.json`

```json
{
    "description": "Opening a form with an unsupported alignment value is rejected. The adapter surfaces a neutral error category identifying the offending alignment option rather than producing markup.",
    "cases": [
        {
            "input": {
                "steps": [
                    {
                        "op": "create",
                        "options": {
                            "align": "foo"
                        },
                        "emit": true
                    }
                ]
            },
            "expected_output": "error=invalid_alignment\n"
        }
    ]
}
```

*3.4 Custom grid widths*

A horizontal grid can be given an explicit label-column / input-column width pair, supplied either positionally or as a map keyed by column position (`0` = label column, `1` = input column). A control rendered afterwards spreads its label and input wrapper across the requested grid widths (`col-md-{n}`).

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_custom_grid.json`

```json
{
    "description": "Open a form with an explicit two-column grid specification (label column width and input column width). The specification may be given either as a positional pair or as an indexed map keyed by column position. A control rendered afterwards lays the label and the input wrapper out across the requested grid widths. Output is the generated HTML for the control group.",
    "cases": [
        {
            "input": {
                "steps": [
                    {
                        "op": "create",
                        "options": {
                            "align": {
                                "0": 3,
                                "1": 5
                            }
                        }
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true
                    }
                ]
            },
            "expected_output": "<div class=\"mb-3 form-group row text required\"><label class=\"col-form-label col-md-3\" for=\"title\">Title</label><div class=\"col-md-5\"><input aria-required=\"true\" class=\"form-control\" data-validity-message=\"This field cannot be left empty\" id=\"title\" name=\"title\" oninput=\"this.setCustomValidity(&#039;&#039;)\" oninvalid=\"this.setCustomValidity(&#039;&#039;); if (!this.value) this.setCustomValidity(this.dataset.validityMessage)\" required=\"required\" type=\"text\"></div></div>\n"
        },
        {
            "input": {
                "steps": [
                    {
                        "op": "create",
                        "options": {
                            "align": [
                                3,
                                5
                            ]
                        }
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true
                    }
                ]
            },
            "expected_output": "<div class=\"mb-3 form-group row text required\"><label class=\"col-form-label col-md-3\" for=\"title\">Title</label><div class=\"col-md-5\"><input aria-required=\"true\" class=\"form-control\" data-validity-message=\"This field cannot be left empty\" id=\"title\" name=\"title\" oninput=\"this.setCustomValidity(&#039;&#039;)\" oninvalid=\"this.setCustomValidity(&#039;&#039;); if (!this.value) this.setCustomValidity(this.dataset.validityMessage)\" required=\"required\" type=\"text\"></div></div>\n"
        }
    ]
}
```

*3.5 External template set*

Opening a form with a named external template set overrides the default markup templates. A control rendered afterwards picks up the custom container template, which contributes an extra wrapper class around the control group.

**Test Cases:** `rcb_tests/public_test_cases/feature3_5_templates_file.json`

```json
{
    "description": "Open a form that loads an external template set by name, overriding the default markup templates. A control rendered afterwards uses the custom container template, which contributes an extra wrapper class around the control group. Output is the generated HTML for the control group.",
    "cases": [
        {
            "input": {
                "steps": [
                    {
                        "op": "article",
                        "unset": [
                            "required.title"
                        ]
                    },
                    {
                        "op": "create",
                        "options": {
                            "templates": "custom_templates"
                        }
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true
                    }
                ]
            },
            "expected_output": "<div class=\"custom-container mb-3 form-group\"><label class=\"form-label\" for=\"title\">Title</label><input class=\"form-control\" id=\"title\" name=\"title\" type=\"text\"></div>\n"
        }
    ]
}
```

*3.6 Horizontal layout from helper config*

The helper can be pre-configured with a horizontal alignment plus a custom template fragment for boolean (checkbox) groups. After opening the form, a text control is laid out on the default horizontal grid, while a boolean control uses the custom checkbox-group fragment and is offset to align with the input column.

**Test Cases:** `rcb_tests/public_test_cases/feature3_6_horizontal_from_config.json`

```json
{
    "description": "Configure the helper up front with a horizontal alignment plus a custom template fragment for the checkbox group, then open the form and render controls. A text control is laid out across the default horizontal grid; a boolean control uses the custom checkbox group fragment and is offset to align with the input column. Output is the form start tag followed by the generated HTML for each control.",
    "cases": [
        {
            "input": {
                "steps": [
                    {
                        "op": "config",
                        "config": {
                            "align": "horizontal",
                            "templateSet": {
                                "horizontal": {
                                    "checkboxFormGroup": "<div class=\"%s\"><div class=\"form-check my-checkbox\">{{input}}{{label}}</div>{{error}}{{help}}</div>"
                                }
                            }
                        }
                    },
                    {
                        "op": "create",
                        "emit": true
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true
                    },
                    {
                        "op": "control",
                        "field": "published",
                        "emit": true
                    }
                ]
            },
            "expected_output": "<form accept-charset=\"utf-8\" action=\"/articles/add\" class=\"form-horizontal\" method=\"post\" role=\"form\">\n<div class=\"mb-3 form-group row text required\"><label class=\"col-form-label col-md-2\" for=\"title\">Title</label><div class=\"col-md-10\"><input aria-required=\"true\" class=\"form-control\" data-validity-message=\"This field cannot be left empty\" id=\"title\" name=\"title\" oninput=\"this.setCustomValidity(&#039;&#039;)\" oninvalid=\"this.setCustomValidity(&#039;&#039;); if (!this.value) this.setCustomValidity(this.dataset.validityMessage)\" required=\"required\" type=\"text\"></div></div>\n<div class=\"mb-3 form-group row checkbox\"><div class=\"offset-md-2 col-md-10\"><div class=\"form-check my-checkbox\"><input name=\"published\" type=\"hidden\" value=\"0\"><input class=\"form-check-input\" id=\"published\" name=\"published\" type=\"checkbox\" value=\"1\"><label class=\"form-check-label\" for=\"published\">Published</label></div></div></div>\n"
        }
    ]
}
```

---

### Feature 4: Buttons & Submit

**As a developer**, I want to render styled buttons and submit controls, so action elements match the framework's button theming.

**Expected Behavior / Usage:**

*4.1 Buttons*

A standalone button defaults to a submit-type button carrying a base button class plus a secondary variant. Supplying a style keyword as the `class` (e.g. `success`, `primary`) translates it into the matching themed variant class (`btn-success`) while keeping the base `btn` class.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_buttons.json`

```json
{
    "description": "Render a standalone button. By default it is a submit-type button with a base and a secondary variant class. A style keyword supplied as a class is translated into the corresponding themed variant class while the base class is preserved. Output is the generated button markup.",
    "cases": [
        {
            "input": {
                "steps": [
                    {
                        "op": "button",
                        "text": "Submit"
                    }
                ]
            },
            "expected_output": "<button class=\"btn btn-secondary\" type=\"submit\">Submit</button>\n"
        },
        {
            "input": {
                "steps": [
                    {
                        "op": "button",
                        "text": "Submit",
                        "options": {
                            "class": "success"
                        }
                    }
                ]
            },
            "expected_output": "<button class=\"btn-success btn\" type=\"submit\">Submit</button>\n"
        }
    ]
}
```

*4.2 Submit control*

A submit control renders a submit `<input>` wrapped in a container `<div>`. Classes given either as a space-separated string or as a list are merged, and a default secondary variant class is appended.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_submit.json`

```json
{
    "description": "Render a submit input wrapped in a container. Classes supplied either as a space-separated string or as a list are merged, and a default secondary variant class is appended. Output is the generated submit markup.",
    "cases": [
        {
            "input": {
                "steps": [
                    {
                        "op": "submit",
                        "text": "Submit",
                        "options": {
                            "class": "btn btn-block"
                        }
                    },
                    {
                        "op": "submit",
                        "text": "Submit",
                        "options": {
                            "class": [
                                "btn",
                                "btn-block"
                            ]
                        }
                    }
                ]
            },
            "expected_output": "<div class=\"submit\"><input class=\"btn btn-block btn-secondary\" type=\"submit\" value=\"Submit\"></div>\n<div class=\"submit\"><input class=\"btn btn-block btn-secondary\" type=\"submit\" value=\"Submit\"></div>\n"
        }
    ]
}
```

---

### Feature 5: Control Composition Details

**As a developer**, I want to control fine-grained rendering details such as suppressing a label or confirming the per-widget styling class, so individual widgets stay correctly themed.

**Expected Behavior / Usage:**

*5.1 Suppressed label*

Requesting `label: false` suppresses the label entirely; the control group then contains only the input (still carrying its required/validity wiring) and no `<label>` element.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_tooltip_disabled_label.json`

```json
{
    "description": "Render a control whose label is suppressed while a tooltip helper text is requested. With the label disabled, the control group contains only the input (carrying its required/validity wiring) and no label element. Output is the generated HTML for the control group.",
    "cases": [
        {
            "input": {
                "steps": [
                    {
                        "op": "create"
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true,
                        "options": {
                            "tooltip": "Some important additional notes.",
                            "label": false
                        }
                    }
                ]
            },
            "expected_output": "<div class=\"mb-3 form-group text required\"><input aria-required=\"true\" class=\"form-control\" data-validity-message=\"This field cannot be left empty\" id=\"title\" name=\"title\" oninput=\"this.setCustomValidity(&#039;&#039;)\" oninvalid=\"this.setCustomValidity(&#039;&#039;); if (!this.value) this.setCustomValidity(this.dataset.validityMessage)\" required=\"required\" type=\"text\"></div>\n"
        }
    ]
}
```

*5.2 Per-widget styling class*

Each standalone widget receives the styling class appropriate to its kind: text/textarea/date-time/file/color get a control class (color additionally gets a color modifier), select gets a select class, checkbox/radio get a check-input class. A user-supplied class is preserved alongside the injected one.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_widget_class_injection.json`

```json
{
    "description": "Render assorted standalone widgets directly and confirm each receives the appropriate styling class: single-line text, select, multi-line text, date-time, file, checkbox, radio group, and color all get the styling class that matches their kind, and a user-supplied class is preserved alongside the injected one. Output is the generated markup for each widget in turn.",
    "cases": [
        {
            "input": {
                "steps": [
                    {
                        "op": "text",
                        "field": "foo"
                    },
                    {
                        "op": "text",
                        "field": "foo",
                        "options": {
                            "class": "custom"
                        }
                    },
                    {
                        "op": "select",
                        "field": "foo"
                    },
                    {
                        "op": "textarea",
                        "field": "foo"
                    },
                    {
                        "op": "dateTime",
                        "field": "foo"
                    },
                    {
                        "op": "file",
                        "field": "foo"
                    },
                    {
                        "op": "checkbox",
                        "field": "foo"
                    },
                    {
                        "op": "radio",
                        "field": "foo",
                        "choices": {
                            "1": "Opt 1",
                            "2": "Opt 2"
                        }
                    },
                    {
                        "op": "color",
                        "field": "foo"
                    }
                ]
            },
            "expected_output": "<input class=\"form-control\" name=\"foo\" type=\"text\">\n<input class=\"custom form-control\" name=\"foo\" type=\"text\">\n<select class=\"form-select\" name=\"foo\"></select>\n<textarea class=\"form-control\" name=\"foo\" rows=\"5\"></textarea>\n<input class=\"form-control\" name=\"foo\" step=\"1\" type=\"datetime-local\" value=\"\">\n<input class=\"form-control\" name=\"foo\" type=\"file\">\n<input name=\"foo\" type=\"hidden\" value=\"0\"><input class=\"form-check-input\" name=\"foo\" type=\"checkbox\" value=\"1\">\n<input id=\"foo\" name=\"foo\" type=\"hidden\" value=\"\"><div class=\"form-check\"><input class=\"form-check-input\" id=\"foo-1\" name=\"foo\" type=\"radio\" value=\"1\"><label class=\"form-check-label\" for=\"foo-1\">Opt 1</label></div><div class=\"form-check\"><input class=\"form-check-input\" id=\"foo-2\" name=\"foo\" type=\"radio\" value=\"2\"><label class=\"form-check-label\" for=\"foo-2\">Opt 2</label></div>\n<input class=\"form-control form-control-color\" name=\"foo\" type=\"color\">\n"
        }
    ]
}
```

---

### Feature 6: Validation Feedback Presentation

**As a developer**, I want to choose how validation feedback is presented and positioned for errored fields, so feedback can appear inline or as a floating tooltip across any layout.

**Expected Behavior / Usage:**

*6.1 Feedback style*

For an errored field the feedback presentation is selectable. The `default` style renders the feedback as an inline block (`invalid-feedback`); the `tooltip` style renders it as a floating tooltip (`invalid-tooltip`) and adds a positioning context class to the control group. The style can be a helper-wide default and overridden per control, and it composes with every layout (stacked, inline, horizontal). The input is always marked invalid and linked to the feedback block by id.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_feedback_style.json`

```json
{
    "description": "Control how validation feedback is presented for an errored field. A tooltip feedback style renders the feedback block as a floating tooltip and adds a positioning class to the control group; the default style renders the feedback as an inline block. The feedback style may be set as a helper-wide default and overridden per control, and it composes with the form alignment (default, inline, horizontal). The input is always marked invalid and linked to the feedback block by id. Output is the generated HTML for the control group.",
    "cases": [
        {
            "input": {
                "steps": [
                    {
                        "op": "article",
                        "set": {
                            "errors.title": [
                                "error message"
                            ],
                            "required.title": false
                        }
                    },
                    {
                        "op": "config",
                        "config": {
                            "feedbackStyle": "tooltip"
                        }
                    },
                    {
                        "op": "create"
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true
                    }
                ]
            },
            "expected_output": "<div class=\"mb-3 form-group position-relative text is-invalid\"><label class=\"form-label\" for=\"title\">Title</label><input aria-describedby=\"title-error\" aria-invalid=\"true\" class=\"is-invalid form-control\" id=\"title\" name=\"title\" type=\"text\"><div class=\"invalid-tooltip\" id=\"title-error\">error message</div></div>\n"
        },
        {
            "input": {
                "steps": [
                    {
                        "op": "article",
                        "set": {
                            "errors.title": [
                                "error message"
                            ],
                            "required.title": false
                        }
                    },
                    {
                        "op": "config",
                        "config": {
                            "feedbackStyle": "tooltip"
                        }
                    },
                    {
                        "op": "create"
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true,
                        "options": {
                            "feedbackStyle": "default"
                        }
                    }
                ]
            },
            "expected_output": "<div class=\"mb-3 form-group text is-invalid\"><label class=\"form-label\" for=\"title\">Title</label><input aria-describedby=\"title-error\" aria-invalid=\"true\" class=\"is-invalid form-control\" id=\"title\" name=\"title\" type=\"text\"><div class=\"ms-0 invalid-feedback\" id=\"title-error\">error message</div></div>\n"
        }
    ]
}
```

*6.2 Feedback positioning context*

When the tooltip feedback style is active, the control group's CSS positioning context is selectable (`absolute`, `static`, …), applied as a `position-{value}` class. Settable helper-wide and overridable per control.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_form_group_position.json`

```json
{
    "description": "When a tooltip feedback style is active, the control group's CSS positioning context can be selected. A helper-wide positioning setting applies a corresponding positioning class to the control group, and it can be overridden per control. Output is the generated HTML for the control group.",
    "cases": [
        {
            "input": {
                "steps": [
                    {
                        "op": "article",
                        "set": {
                            "errors.title": [
                                "error message"
                            ],
                            "required.title": false
                        }
                    },
                    {
                        "op": "config",
                        "config": {
                            "feedbackStyle": "tooltip",
                            "formGroupPosition": "absolute"
                        }
                    },
                    {
                        "op": "create"
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true
                    }
                ]
            },
            "expected_output": "<div class=\"mb-3 form-group position-absolute text is-invalid\"><label class=\"form-label\" for=\"title\">Title</label><input aria-describedby=\"title-error\" aria-invalid=\"true\" class=\"is-invalid form-control\" id=\"title\" name=\"title\" type=\"text\"><div class=\"invalid-tooltip\" id=\"title-error\">error message</div></div>\n"
        },
        {
            "input": {
                "steps": [
                    {
                        "op": "article",
                        "set": {
                            "errors.title": [
                                "error message"
                            ],
                            "required.title": false
                        }
                    },
                    {
                        "op": "config",
                        "config": {
                            "feedbackStyle": "tooltip",
                            "formGroupPosition": "absolute"
                        }
                    },
                    {
                        "op": "create"
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true,
                        "options": {
                            "formGroupPosition": "static"
                        }
                    }
                ]
            },
            "expected_output": "<div class=\"mb-3 form-group position-static text is-invalid\"><label class=\"form-label\" for=\"title\">Title</label><input aria-describedby=\"title-error\" aria-invalid=\"true\" class=\"is-invalid form-control\" id=\"title\" name=\"title\" type=\"text\"><div class=\"invalid-tooltip\" id=\"title-error\">error message</div></div>\n"
        }
    ]
}
```

---

### Feature 7: Accessibility Attributes

**As a developer**, I want to manage the accessibility attributes emitted on a control, so I can override or suppress individual ARIA flags while keeping the rest correct.

**Expected Behavior / Usage:**

*7.1 ARIA attribute management*

A hidden field never receives ARIA attributes. For a visible errored/required field, the ARIA flags (`aria-required`, `aria-invalid`, `aria-describedby`) are emitted by default, but each may be individually disabled (set to false) or overridden with a custom value; disabling one leaves the others intact.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_aria_attributes.json`

```json
{
    "description": "Manage accessibility attributes on a control. A hidden field never receives accessibility attributes. For a visible errored/required field, the accessibility flags (required, invalid, described-by linkage) are emitted by default but each can be individually disabled or overridden with a custom value, and disabling one leaves the others intact. Output is the generated HTML for the control.",
    "cases": [
        {
            "input": {
                "steps": [
                    {
                        "op": "article",
                        "set": {
                            "errors.title": [
                                "error message"
                            ]
                        }
                    },
                    {
                        "op": "create"
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true,
                        "options": {
                            "type": "hidden",
                            "help": "help text"
                        }
                    }
                ]
            },
            "expected_output": "<input class=\"is-invalid\" id=\"title\" name=\"title\" type=\"hidden\">\n"
        },
        {
            "input": {
                "steps": [
                    {
                        "op": "article",
                        "set": {
                            "errors.title": [
                                "error message"
                            ]
                        }
                    },
                    {
                        "op": "create"
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true,
                        "options": {
                            "aria-required": false,
                            "aria-invalid": false,
                            "aria-describedby": "custom"
                        }
                    }
                ]
            },
            "expected_output": "<div class=\"mb-3 form-group text required is-invalid\"><label class=\"form-label\" for=\"title\">Title</label><input aria-describedby=\"custom\" class=\"is-invalid form-control\" data-validity-message=\"This field cannot be left empty\" id=\"title\" name=\"title\" oninput=\"this.setCustomValidity(&#039;&#039;)\" oninvalid=\"this.setCustomValidity(&#039;&#039;); if (!this.value) this.setCustomValidity(this.dataset.validityMessage)\" required=\"required\" type=\"text\"><div class=\"ms-0 invalid-feedback\" id=\"title-error\">error message</div></div>\n"
        }
    ]
}
```

---

### Feature 8: Spacing Control

**As a developer**, I want to select or disable the spacing (margin) utility applied to a control group at helper, form, or control scope, so vertical rhythm is configurable and predictable.

**Expected Behavior / Usage:**

*8.1 Spacing override*

The spacing (margin) utility class on a control group can be chosen at three scopes — helper-wide default, per form-open, or per control — with the more specific scope winning. Spacing supplied at form-open scope is reset when the form is closed, so a subsequently opened form falls back to the default (`mb-3`).

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_spacing_override.json`

```json
{
    "description": "Choose the spacing (margin) utility class applied to a control group. The spacing can be set as a helper-wide default, supplied when opening the form, or supplied per control, with the more specific scope winning over the broader one. Spacing supplied at form-open scope is reset once the form is closed so a subsequently opened form falls back to the default. Output is the generated HTML for the affected control group(s).",
    "cases": [
        {
            "input": {
                "steps": [
                    {
                        "op": "article",
                        "set": {
                            "required.title": false
                        }
                    },
                    {
                        "op": "create",
                        "options": {
                            "spacing": "custom-spacing-create"
                        }
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true
                    },
                    {
                        "op": "end",
                        "emit": false
                    },
                    {
                        "op": "create"
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true
                    },
                    {
                        "op": "end",
                        "emit": false
                    }
                ]
            },
            "expected_output": "<div class=\"custom-spacing-create form-group text\"><label class=\"form-label\" for=\"title\">Title</label><input class=\"form-control\" id=\"title\" name=\"title\" type=\"text\"></div>\n<div class=\"mb-3 form-group text\"><label class=\"form-label\" for=\"title\">Title</label><input class=\"form-control\" id=\"title\" name=\"title\" type=\"text\"></div>\n"
        }
    ]
}
```

*8.2 Spacing disable*

Setting spacing to false removes the margin utility class from the control group entirely. Disabling can be requested at helper, form-open, or control scope, again with the more specific scope taking precedence.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_spacing_disable.json`

```json
{
    "description": "Disabling spacing removes the margin utility class from a control group entirely. Disabling can be requested as a helper-wide default, when opening the form, or per control, again with the more specific scope taking precedence. Output is the generated HTML for the affected control group(s).",
    "cases": [
        {
            "input": {
                "steps": [
                    {
                        "op": "article",
                        "set": {
                            "required.title": false
                        }
                    },
                    {
                        "op": "create"
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true
                    },
                    {
                        "op": "end",
                        "emit": false
                    },
                    {
                        "op": "config",
                        "config": {
                            "spacing": false
                        }
                    },
                    {
                        "op": "create"
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true
                    },
                    {
                        "op": "end",
                        "emit": false
                    }
                ]
            },
            "expected_output": "<div class=\"mb-3 form-group text\"><label class=\"form-label\" for=\"title\">Title</label><input class=\"form-control\" id=\"title\" name=\"title\" type=\"text\"></div>\n<div class=\"form-group text\"><label class=\"form-label\" for=\"title\">Title</label><input class=\"form-control\" id=\"title\" name=\"title\" type=\"text\"></div>\n"
        }
    ]
}
```

---

### Feature 9: Floating Labels

**As a developer**, I want to render controls with floating labels, so the label overlays the input and a placeholder is derived automatically from the field name.

**Expected Behavior / Usage:**

Requesting the label in floating mode places the input *before* the label inside a floating-label wrapper (`form-floating`) and derives a `placeholder` attribute on the input from the label text. The placeholder/label text is humanized from the field name, including for dotted/nested field paths (which also produce a bracketed input name and a dashed id) and for fields whose name ends in an id suffix (the suffix is dropped from the humanized text).

**Test Cases:** `rcb_tests/public_test_cases/feature9_1_floating_labels.json`

```json
{
    "description": "Render a control with a floating label. The label is requested in floating mode, which places the input before the label inside a floating-label wrapper and derives a placeholder attribute on the input from the label text. The placeholder text is humanized from the field name, including for dotted/nested field paths and for fields whose name ends in an id suffix. Output is the generated HTML for the control group.",
    "cases": [
        {
            "input": {
                "steps": [
                    {
                        "op": "article",
                        "set": {
                            "required.title": false
                        }
                    },
                    {
                        "op": "create"
                    },
                    {
                        "op": "control",
                        "field": "title",
                        "emit": true,
                        "options": {
                            "label": {
                                "floating": true
                            }
                        }
                    }
                ]
            },
            "expected_output": "<div class=\"mb-3 form-floating form-group text\"><input class=\"form-control\" id=\"title\" name=\"title\" placeholder=\"Title\" type=\"text\"><label for=\"title\">Title</label></div>\n"
        },
        {
            "input": {
                "steps": [
                    {
                        "op": "create"
                    },
                    {
                        "op": "control",
                        "field": "author.name",
                        "emit": true,
                        "options": {
                            "label": {
                                "floating": true
                            }
                        }
                    }
                ]
            },
            "expected_output": "<div class=\"mb-3 form-floating form-group text\"><input class=\"form-control\" id=\"author-name\" name=\"author[name]\" placeholder=\"Name\" type=\"text\"><label for=\"author-name\">Name</label></div>\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file rendering library implementing the features above (context/entity model, control-type inference, widget renderers, layout/alignment strategies, input-group composition, validation feedback, accessibility wiring, button styling). Physical structure must reflect this complexity without over-engineering.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON request from stdin, drives the core renderer through a fixed deterministic context, and prints the normalized generated HTML (attributes sorted within each start tag) — or a neutral `error=<category>` line — to stdout, matching the per-leaf contracts above. It must be logically separated from the core domain.

3. **Automated test harness:** A single entry point `bash rcb_tests/test.sh` that reads every `*.json` case file from a case directory and runs the full suite, accepting `--cases-dir <subdir>` (default `test_cases`). For each case it writes one file `rcb_tests/stdout/<cases-dir>/{stem}@{idx:03}.txt` containing only the raw program stdout, comparable directly against `expected_output`. The PRD-embedded examples live under `rcb_tests/public_test_cases/`.


---
**Implementation notes:**
- emit true in the closing action
- prepend is list with options object
