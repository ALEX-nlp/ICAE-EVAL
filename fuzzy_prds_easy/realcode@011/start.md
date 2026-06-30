## Product Requirement Document

# Rendered Markup Assertion Adapter - Black-Box HTML Verification Contracts

## Project Goal

Build a rendered-markup assertion utility that allows developers to verify the externally visible structure, text, attributes, classes, and links of generated HTML without writing repetitive low-level DOM traversal code.

---

## Background & Problem

Without this library/tool, developers are forced to parse generated markup manually, locate elements by selector, compare text and attributes by hand, and repeat the same failure handling in every test. This leads to noisy tests, fragile boilerplate, and missed regressions in rendered output.

With this library/tool, developers express black-box expectations against rendered HTML and receive deterministic stdout contracts for matches and normalized assertion failures.

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

### Feature 1: Text Fragment Presence

**As a developer**, I want to verify that rendered markup includes literal text fragments, so I can catch missing or altered content in complete, partial, or malformed documents.

**Expected Behavior / Usage:**

The adapter accepts a JSON object with a `document` string containing rendered markup and a `text` string containing the required literal fragment. It prints `result=matched` plus the checked fragment when the raw rendered markup contains the fragment exactly. If the fragment is absent, it prints `error=assertion_failed`, `condition=text_present`, and the checked fragment. Documents may be full HTML documents, multiple sibling root nodes, or malformed/recovered markup; the check is still based on observable rendered text/markup content.

**Test Cases:** `rcb_tests/public_test_cases/feature1_text_presence.json`

```json
{
    "description": "Checks whether raw rendered markup includes a required text fragment, including fragments inside complete documents, multiple root nodes, and recovered malformed markup.",
    "cases": [
        {
            "input": {
                "document": "<a href=\"https://link.com\" prop=\"value\">\n    <button class=\"btn btn-blue\" >\n        Click me\n    </button>\n</a>\n",
                "text": "Click me"
            },
            "expected_output": "result=matched\ntext=Click me\n"
        },
        {
            "input": {
                "document": "<p>FIRST_PARAGRAPH</p>\n<p>SECOND_PARAGRAPH</p>",
                "text": "FIRST_PARAGRAPH"
            },
            "expected_output": "result=matched\ntext=FIRST_PARAGRAPH\n"
        },
        {
            "input": {
                "document": "WIDGETBEFBEFOREArchivesAFTER\n<ul></ul>\nWIDGETAFT",
                "text": "BEFORE"
            },
            "expected_output": "result=matched\ntext=BEFORE\n"
        }
    ]
}
```

---

### Feature 2: CSS Selector Presence

**As a developer**, I want to verify that rendered markup includes elements matching CSS selectors, so I can confirm document structure without manually traversing markup.

**Expected Behavior / Usage:**

The adapter accepts a JSON object with a `document` string and a CSS `selector`; it may also include `scope_selector` to first narrow the document to a subtree. It prints `result=matched` with the scope and selector when at least one matching element exists in the relevant document region. If the selector or required scope has no match, it prints `error=assertion_failed`, `condition=selector_present`, and the relevant selector fields.

**Test Cases:** `rcb_tests/public_test_cases/feature2_selector_presence.json`

```json
{
    "description": "Checks whether a rendered document, or a scoped fragment of it, includes at least one element matching a CSS selector.",
    "cases": [
        {
            "input": {
                "document": "<div class=\"alert-class\">\n    <button class=\"btn btn-blue\" href=\"https://link.com\">\n        Click me\n    </button>\n</div>",
                "selector": "button"
            },
            "expected_output": "result=matched\nselector=button\n"
        },
        {
            "input": {
                "document": "<html lang=\"en\">\n<head>\n    <meta charset=\"utf-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n\n    <title>Laravel</title>\n\n    <!-- Fonts -->\n    <link href=\"https://fonts.googleapis.com/css?family=Nunito:200,600\" rel=\"stylesheet\">\n\n    <!-- Styles -->\n    <style>\n        html, body {\n            background-color: #fff;\n            color: #636b6f;\n            font-family: 'Nunito', sans-serif;\n            font-weight: 200;\n            height: 100vh;\n            margin: 0;\n        }\n\n        .full-height {\n            height: 100vh;\n        }\n\n        .flex-center {\n            align-items: center;\n            display: flex;\n            justify-content: center;\n        }\n\n        .position-ref {\n            position: relative;\n        }\n\n        .top-right {\n            position: absolute;\n            right: 10px;\n            top: 18px;\n        }\n\n        .content {\n            text-align: center;\n        }\n\n        .title {\n            font-size: 84px;\n        }\n\n        .links > a {\n            color: #636b6f;\n            padding: 0 25px;\n            font-size: 13px;\n            font-weight: 600;\n            letter-spacing: .1rem;\n            text-decoration: none;\n            text-transform: uppercase;\n        }\n\n        .m-b-md {\n            margin-bottom: 30px;\n        }\n    </style>\n</head>\n<body>\n<div class=\"flex-center position-ref full-height\">\n\n    <div class=\"content\">\n        <div class=\"title m-b-md\">\n            Laravel\n        </div>\n\n        <div class=\"links\">\n            <a href=\"https://laravel.com/docs\">Docs</a>\n            <a href=\"https://laracasts.com\">Laracasts</a>\n            <a href=\"https://laravel-news.com\">News</a>\n            <a href=\"https://blog.laravel.com\">Blog</a>\n            <a href=\"https://nova.laravel.com\">Nova</a>\n            <a href=\"https://forge.laravel.com\">Forge</a>\n            <a href=\"https://vapor.laravel.com\">Vapor</a>\n            <a href=\"https://github.com/laravel/laravel\">GitHub</a>\n        </div>\n    </div>\n</div>\n</body>\n</html>",
                "scope_selector": "body",
                "selector": ".content"
            },
            "expected_output": "result=matched\nscope_selector=body\nselector=.content\n"
        },
        {
            "input": {
                "document": "<div class=\"alert-class\">\n    <button class=\"btn btn-blue\" href=\"https://link.com\">\n        Click me\n    </button>\n</div>",
                "selector": "form"
            },
            "expected_output": "error=assertion_failed\ncondition=selector_present\nselector=form\n"
        }
    ]
}
```

---

### Feature 3: Scoped Text Fragment Presence

**As a developer**, I want to limit checks to a selected portion of the document, so I can verify content in context instead of anywhere in the page.

**Expected Behavior / Usage:**

The adapter accepts a JSON object with `document`, `scope_selector`, and `text`. It first builds the fragment formed by all elements matching the scope selector, then checks the required literal text fragment inside that scoped output. Success prints `result=matched` with the scope selector and text; failure prints a normalized assertion error for `text_present_in_scope` with the same fields.

**Test Cases:** `rcb_tests/public_test_cases/feature3_scoped_text_presence.json`

```json
{
    "description": "Narrows a document to elements matching a CSS selector and then checks that the selected fragment contains a required text fragment.",
    "cases": [
        {
            "input": {
                "document": "<html lang=\"en\">\n<head>\n    <meta charset=\"utf-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n\n    <title>Laravel</title>\n\n    <!-- Fonts -->\n    <link href=\"https://fonts.googleapis.com/css?family=Nunito:200,600\" rel=\"stylesheet\">\n\n    <!-- Styles -->\n    <style>\n        html, body {\n            background-color: #fff;\n            color: #636b6f;\n            font-family: 'Nunito', sans-serif;\n            font-weight: 200;\n            height: 100vh;\n            margin: 0;\n        }\n\n        .full-height {\n            height: 100vh;\n        }\n\n        .flex-center {\n            align-items: center;\n            display: flex;\n            justify-content: center;\n        }\n\n        .position-ref {\n            position: relative;\n        }\n\n        .top-right {\n            position: absolute;\n            right: 10px;\n            top: 18px;\n        }\n\n        .content {\n            text-align: center;\n        }\n\n        .title {\n            font-size: 84px;\n        }\n\n        .links > a {\n            color: #636b6f;\n            padding: 0 25px;\n            font-size: 13px;\n            font-weight: 600;\n            letter-spacing: .1rem;\n            text-decoration: none;\n            text-transform: uppercase;\n        }\n\n        .m-b-md {\n            margin-bottom: 30px;\n        }\n    </style>\n</head>\n<body>\n<div class=\"flex-center position-ref full-height\">\n\n    <div class=\"content\">\n        <div class=\"title m-b-md\">\n            Laravel\n        </div>\n\n        <div class=\"links\">\n            <a href=\"https://laravel.com/docs\">Docs</a>\n            <a href=\"https://laracasts.com\">Laracasts</a>\n            <a href=\"https://laravel-news.com\">News</a>\n            <a href=\"https://blog.laravel.com\">Blog</a>\n            <a href=\"https://nova.laravel.com\">Nova</a>\n            <a href=\"https://forge.laravel.com\">Forge</a>\n            <a href=\"https://vapor.laravel.com\">Vapor</a>\n            <a href=\"https://github.com/laravel/laravel\">GitHub</a>\n        </div>\n    </div>\n</div>\n</body>\n</html>",
                "scope_selector": "title",
                "text": "Laravel"
            },
            "expected_output": "result=matched\nscope_selector=title\ntext=Laravel\n"
        },
        {
            "input": {
                "document": "<html lang=\"en\">\n<head>\n    <meta charset=\"utf-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n\n    <title>Laravel</title>\n\n    <!-- Fonts -->\n    <link href=\"https://fonts.googleapis.com/css?family=Nunito:200,600\" rel=\"stylesheet\">\n\n    <!-- Styles -->\n    <style>\n        html, body {\n            background-color: #fff;\n            color: #636b6f;\n            font-family: 'Nunito', sans-serif;\n            font-weight: 200;\n            height: 100vh;\n            margin: 0;\n        }\n\n        .full-height {\n            height: 100vh;\n        }\n\n        .flex-center {\n            align-items: center;\n            display: flex;\n            justify-content: center;\n        }\n\n        .position-ref {\n            position: relative;\n        }\n\n        .top-right {\n            position: absolute;\n            right: 10px;\n            top: 18px;\n        }\n\n        .content {\n            text-align: center;\n        }\n\n        .title {\n            font-size: 84px;\n        }\n\n        .links > a {\n            color: #636b6f;\n            padding: 0 25px;\n            font-size: 13px;\n            font-weight: 600;\n            letter-spacing: .1rem;\n            text-decoration: none;\n            text-transform: uppercase;\n        }\n\n        .m-b-md {\n            margin-bottom: 30px;\n        }\n    </style>\n</head>\n<body>\n<div class=\"flex-center position-ref full-height\">\n\n    <div class=\"content\">\n        <div class=\"title m-b-md\">\n            Laravel\n        </div>\n\n        <div class=\"links\">\n            <a href=\"https://laravel.com/docs\">Docs</a>\n            <a href=\"https://laracasts.com\">Laracasts</a>\n            <a href=\"https://laravel-news.com\">News</a>\n            <a href=\"https://blog.laravel.com\">Blog</a>\n            <a href=\"https://nova.laravel.com\">Nova</a>\n            <a href=\"https://forge.laravel.com\">Forge</a>\n            <a href=\"https://vapor.laravel.com\">Vapor</a>\n            <a href=\"https://github.com/laravel/laravel\">GitHub</a>\n        </div>\n    </div>\n</div>\n</body>\n</html>",
                "scope_selector": ".links a",
                "text": "Laracast"
            },
            "expected_output": "result=matched\nscope_selector=.links a\ntext=Laracast\n"
        }
    ]
}
```

---

### Feature 4: Root Attribute Value Matching

**As a developer**, I want to assert exact attribute values on the root of a selected fragment, so I can validate metadata and element configuration precisely.

**Expected Behavior / Usage:**

The adapter accepts a JSON object with `document`, `attribute`, and `value`. It may also include `scope_selector` plus `selection_selector`, `selection_mode`, and `position` to choose a fragment before checking. The check compares the named attribute on the current root element to the expected value exactly. Success prints `result=matched` with the selector context and attribute fields; mismatch prints `error=assertion_failed` and `condition=attribute_value_matches` without exposing runtime exception details.

**Test Cases:** `rcb_tests/public_test_cases/feature4_attribute_match.json`

```json
{
    "description": "Checks whether the root element of the current document or selected fragment has a named attribute with an exact expected value.",
    "cases": [
        {
            "input": {
                "document": "<a href=\"https://link.com\" prop=\"value\">\n    <button class=\"btn btn-blue\" >\n        Click me\n    </button>\n</a>\n",
                "attribute": "prop",
                "value": "value"
            },
            "expected_output": "result=matched\nattribute=prop\nvalue=value\n"
        },
        {
            "input": {
                "document": "<html lang=\"en\">\n<head>\n    <meta charset=\"utf-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n\n    <title>Laravel</title>\n\n    <!-- Fonts -->\n    <link href=\"https://fonts.googleapis.com/css?family=Nunito:200,600\" rel=\"stylesheet\">\n\n    <!-- Styles -->\n    <style>\n        html, body {\n            background-color: #fff;\n            color: #636b6f;\n            font-family: 'Nunito', sans-serif;\n            font-weight: 200;\n            height: 100vh;\n            margin: 0;\n        }\n\n        .full-height {\n            height: 100vh;\n        }\n\n        .flex-center {\n            align-items: center;\n            display: flex;\n            justify-content: center;\n        }\n\n        .position-ref {\n            position: relative;\n        }\n\n        .top-right {\n            position: absolute;\n            right: 10px;\n            top: 18px;\n        }\n\n        .content {\n            text-align: center;\n        }\n\n        .title {\n            font-size: 84px;\n        }\n\n        .links > a {\n            color: #636b6f;\n            padding: 0 25px;\n            font-size: 13px;\n            font-weight: 600;\n            letter-spacing: .1rem;\n            text-decoration: none;\n            text-transform: uppercase;\n        }\n\n        .m-b-md {\n            margin-bottom: 30px;\n        }\n    </style>\n</head>\n<body>\n<div class=\"flex-center position-ref full-height\">\n\n    <div class=\"content\">\n        <div class=\"title m-b-md\">\n            Laravel\n        </div>\n\n        <div class=\"links\">\n            <a href=\"https://laravel.com/docs\">Docs</a>\n            <a href=\"https://laracasts.com\">Laracasts</a>\n            <a href=\"https://laravel-news.com\">News</a>\n            <a href=\"https://blog.laravel.com\">Blog</a>\n            <a href=\"https://nova.laravel.com\">Nova</a>\n            <a href=\"https://forge.laravel.com\">Forge</a>\n            <a href=\"https://vapor.laravel.com\">Vapor</a>\n            <a href=\"https://github.com/laravel/laravel\">GitHub</a>\n        </div>\n    </div>\n</div>\n</body>\n</html>",
                "scope_selector": "head",
                "selection_selector": "meta",
                "selection_mode": "first",
                "attribute": "charset",
                "value": "utf-8"
            },
            "expected_output": "result=matched\nscope_selector=head\nselection_selector=meta\nselection_mode=first\nattribute=charset\nvalue=utf-8\n"
        },
        {
            "input": {
                "document": "<a href=\"https://link.com\" prop=\"value\">\n    <button class=\"btn btn-blue\" >\n        Click me\n    </button>\n</a>\n",
                "attribute": "prop",
                "value": "missing-value"
            },
            "expected_output": "error=assertion_failed\ncondition=attribute_value_matches\nattribute=prop\nvalue=missing-value\n"
        }
    ]
}
```

---

### Feature 5: CSS Class Presence

**As a developer**, I want to assert that required style class tokens are present, so I can validate styling hooks in rendered output.

**Expected Behavior / Usage:**

The adapter accepts a JSON object with `document` and `class`. It may include the same optional scope and ordered-selection fields used for fragment selection. The check succeeds when the current document or selected fragment contains an element with the required CSS class token. Success prints `result=matched` with the selector context and class; absence prints `error=assertion_failed` and `condition=class_present`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_class_presence.json`

```json
{
    "description": "Checks whether the current document or selected fragment contains an element carrying a required CSS class token.",
    "cases": [
        {
            "input": {
                "document": "<a href=\"https://link.com\" prop=\"value\">\n    <button class=\"btn btn-blue\" >\n        Click me\n    </button>\n</a>\n",
                "class": "btn"
            },
            "expected_output": "result=matched\nclass=btn\n"
        },
        {
            "input": {
                "document": "<html lang=\"en\">\n<head>\n    <meta charset=\"utf-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n\n    <title>Laravel</title>\n\n    <!-- Fonts -->\n    <link href=\"https://fonts.googleapis.com/css?family=Nunito:200,600\" rel=\"stylesheet\">\n\n    <!-- Styles -->\n    <style>\n        html, body {\n            background-color: #fff;\n            color: #636b6f;\n            font-family: 'Nunito', sans-serif;\n            font-weight: 200;\n            height: 100vh;\n            margin: 0;\n        }\n\n        .full-height {\n            height: 100vh;\n        }\n\n        .flex-center {\n            align-items: center;\n            display: flex;\n            justify-content: center;\n        }\n\n        .position-ref {\n            position: relative;\n        }\n\n        .top-right {\n            position: absolute;\n            right: 10px;\n            top: 18px;\n        }\n\n        .content {\n            text-align: center;\n        }\n\n        .title {\n            font-size: 84px;\n        }\n\n        .links > a {\n            color: #636b6f;\n            padding: 0 25px;\n            font-size: 13px;\n            font-weight: 600;\n            letter-spacing: .1rem;\n            text-decoration: none;\n            text-transform: uppercase;\n        }\n\n        .m-b-md {\n            margin-bottom: 30px;\n        }\n    </style>\n</head>\n<body>\n<div class=\"flex-center position-ref full-height\">\n\n    <div class=\"content\">\n        <div class=\"title m-b-md\">\n            Laravel\n        </div>\n\n        <div class=\"links\">\n            <a href=\"https://laravel.com/docs\">Docs</a>\n            <a href=\"https://laracasts.com\">Laracasts</a>\n            <a href=\"https://laravel-news.com\">News</a>\n            <a href=\"https://blog.laravel.com\">Blog</a>\n            <a href=\"https://nova.laravel.com\">Nova</a>\n            <a href=\"https://forge.laravel.com\">Forge</a>\n            <a href=\"https://vapor.laravel.com\">Vapor</a>\n            <a href=\"https://github.com/laravel/laravel\">GitHub</a>\n        </div>\n    </div>\n</div>\n</body>\n</html>",
                "scope_selector": ".content",
                "selection_selector": "div > div",
                "selection_mode": "index",
                "position": 0,
                "class": "title"
            },
            "expected_output": "result=matched\nscope_selector=.content\nselection_selector=div > div\nselection_mode=index\nposition=0\nclass=title\n"
        },
        {
            "input": {
                "document": "<a href=\"https://link.com\" prop=\"value\">\n    <button class=\"btn btn-blue\" >\n        Click me\n    </button>\n</a>\n",
                "class": "btn-danger"
            },
            "expected_output": "error=assertion_failed\ncondition=class_present\nclass=btn-danger\n"
        }
    ]
}
```

---

### Feature 6: Anchor Target Presence

**As a developer**, I want to assert that rendered anchors point to exact targets, so I can validate navigation targets in rendered output.

**Expected Behavior / Usage:**

The adapter accepts a JSON object with `document` and `href`. It may include optional scope and ordered-selection fields. The check succeeds when the current document or selected fragment contains an anchor element whose `href` value exactly equals the requested target. Success prints `result=matched` with selector context and href; absence prints `error=assertion_failed` and `condition=link_target_present`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_link_target_presence.json`

```json
{
    "description": "Checks whether the current document or selected fragment contains an anchor element whose href exactly matches a required target.",
    "cases": [
        {
            "input": {
                "document": "<a href=\"https://link.com\" prop=\"value\">\n    <button class=\"btn btn-blue\" >\n        Click me\n    </button>\n</a>\n",
                "href": "https://link.com"
            },
            "expected_output": "result=matched\nhref=https://link.com\n"
        },
        {
            "input": {
                "document": "<html lang=\"en\">\n<head>\n    <meta charset=\"utf-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n\n    <title>Laravel</title>\n\n    <!-- Fonts -->\n    <link href=\"https://fonts.googleapis.com/css?family=Nunito:200,600\" rel=\"stylesheet\">\n\n    <!-- Styles -->\n    <style>\n        html, body {\n            background-color: #fff;\n            color: #636b6f;\n            font-family: 'Nunito', sans-serif;\n            font-weight: 200;\n            height: 100vh;\n            margin: 0;\n        }\n\n        .full-height {\n            height: 100vh;\n        }\n\n        .flex-center {\n            align-items: center;\n            display: flex;\n            justify-content: center;\n        }\n\n        .position-ref {\n            position: relative;\n        }\n\n        .top-right {\n            position: absolute;\n            right: 10px;\n            top: 18px;\n        }\n\n        .content {\n            text-align: center;\n        }\n\n        .title {\n            font-size: 84px;\n        }\n\n        .links > a {\n            color: #636b6f;\n            padding: 0 25px;\n            font-size: 13px;\n            font-weight: 600;\n            letter-spacing: .1rem;\n            text-decoration: none;\n            text-transform: uppercase;\n        }\n\n        .m-b-md {\n            margin-bottom: 30px;\n        }\n    </style>\n</head>\n<body>\n<div class=\"flex-center position-ref full-height\">\n\n    <div class=\"content\">\n        <div class=\"title m-b-md\">\n            Laravel\n        </div>\n\n        <div class=\"links\">\n            <a href=\"https://laravel.com/docs\">Docs</a>\n            <a href=\"https://laracasts.com\">Laracasts</a>\n            <a href=\"https://laravel-news.com\">News</a>\n            <a href=\"https://blog.laravel.com\">Blog</a>\n            <a href=\"https://nova.laravel.com\">Nova</a>\n            <a href=\"https://forge.laravel.com\">Forge</a>\n            <a href=\"https://vapor.laravel.com\">Vapor</a>\n            <a href=\"https://github.com/laravel/laravel\">GitHub</a>\n        </div>\n    </div>\n</div>\n</body>\n</html>",
                "scope_selector": ".links",
                "selection_selector": "a",
                "selection_mode": "first",
                "href": "https://laravel.com/docs"
            },
            "expected_output": "result=matched\nscope_selector=.links\nselection_selector=a\nselection_mode=first\nhref=https://laravel.com/docs\n"
        },
        {
            "input": {
                "document": "<a href=\"https://link.com\" prop=\"value\">\n    <button class=\"btn btn-blue\" >\n        Click me\n    </button>\n</a>\n",
                "href": "https://link-that-is-not-there.com"
            },
            "expected_output": "error=assertion_failed\ncondition=link_target_present\nhref=https://link-that-is-not-there.com\n"
        }
    ]
}
```

---

### Feature 7: Ordered Element Selection

**As a developer**, I want to select elements by order before checking their contents, so I can validate lists and repeated markup where position matters.

**Expected Behavior / Usage:**

The adapter accepts a JSON object with `document`, `selection_selector`, `selection_mode`, and `text`; `position` is used when `selection_mode` is `index`. `selection_mode` chooses the first matching element, last matching element, or zero-based indexed element, and the selected element is then checked for the required text fragment. Success prints `result=matched` with the selection fields and text; mismatch prints `error=assertion_failed` and `condition=ordered_selection_contains_text`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_ordered_selection_text.json`

```json
{
    "description": "Selects the first, last, or zero-based indexed element from a selector result and checks that the selected element contains a required text fragment.",
    "cases": [
        {
            "input": {
                "document": "<html lang=\"en\">\n<head>\n    <meta charset=\"utf-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n\n    <title>Laravel</title>\n\n    <!-- Fonts -->\n    <link href=\"https://fonts.googleapis.com/css?family=Nunito:200,600\" rel=\"stylesheet\">\n\n    <!-- Styles -->\n    <style>\n        html, body {\n            background-color: #fff;\n            color: #636b6f;\n            font-family: 'Nunito', sans-serif;\n            font-weight: 200;\n            height: 100vh;\n            margin: 0;\n        }\n\n        .full-height {\n            height: 100vh;\n        }\n\n        .flex-center {\n            align-items: center;\n            display: flex;\n            justify-content: center;\n        }\n\n        .position-ref {\n            position: relative;\n        }\n\n        .top-right {\n            position: absolute;\n            right: 10px;\n            top: 18px;\n        }\n\n        .content {\n            text-align: center;\n        }\n\n        .title {\n            font-size: 84px;\n        }\n\n        .links > a {\n            color: #636b6f;\n            padding: 0 25px;\n            font-size: 13px;\n            font-weight: 600;\n            letter-spacing: .1rem;\n            text-decoration: none;\n            text-transform: uppercase;\n        }\n\n        .m-b-md {\n            margin-bottom: 30px;\n        }\n    </style>\n</head>\n<body>\n<div class=\"flex-center position-ref full-height\">\n\n    <div class=\"content\">\n        <div class=\"title m-b-md\">\n            Laravel\n        </div>\n\n        <div class=\"links\">\n            <a href=\"https://laravel.com/docs\">Docs</a>\n            <a href=\"https://laracasts.com\">Laracasts</a>\n            <a href=\"https://laravel-news.com\">News</a>\n            <a href=\"https://blog.laravel.com\">Blog</a>\n            <a href=\"https://nova.laravel.com\">Nova</a>\n            <a href=\"https://forge.laravel.com\">Forge</a>\n            <a href=\"https://vapor.laravel.com\">Vapor</a>\n            <a href=\"https://github.com/laravel/laravel\">GitHub</a>\n        </div>\n    </div>\n</div>\n</body>\n</html>",
                "selection_selector": ".links a",
                "selection_mode": "first",
                "text": "Docs"
            },
            "expected_output": "result=matched\nselection_selector=.links a\nselection_mode=first\ntext=Docs\n"
        },
        {
            "input": {
                "document": "<html lang=\"en\">\n<head>\n    <meta charset=\"utf-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n\n    <title>Laravel</title>\n\n    <!-- Fonts -->\n    <link href=\"https://fonts.googleapis.com/css?family=Nunito:200,600\" rel=\"stylesheet\">\n\n    <!-- Styles -->\n    <style>\n        html, body {\n            background-color: #fff;\n            color: #636b6f;\n            font-family: 'Nunito', sans-serif;\n            font-weight: 200;\n            height: 100vh;\n            margin: 0;\n        }\n\n        .full-height {\n            height: 100vh;\n        }\n\n        .flex-center {\n            align-items: center;\n            display: flex;\n            justify-content: center;\n        }\n\n        .position-ref {\n            position: relative;\n        }\n\n        .top-right {\n            position: absolute;\n            right: 10px;\n            top: 18px;\n        }\n\n        .content {\n            text-align: center;\n        }\n\n        .title {\n            font-size: 84px;\n        }\n\n        .links > a {\n            color: #636b6f;\n            padding: 0 25px;\n            font-size: 13px;\n            font-weight: 600;\n            letter-spacing: .1rem;\n            text-decoration: none;\n            text-transform: uppercase;\n        }\n\n        .m-b-md {\n            margin-bottom: 30px;\n        }\n    </style>\n</head>\n<body>\n<div class=\"flex-center position-ref full-height\">\n\n    <div class=\"content\">\n        <div class=\"title m-b-md\">\n            Laravel\n        </div>\n\n        <div class=\"links\">\n            <a href=\"https://laravel.com/docs\">Docs</a>\n            <a href=\"https://laracasts.com\">Laracasts</a>\n            <a href=\"https://laravel-news.com\">News</a>\n            <a href=\"https://blog.laravel.com\">Blog</a>\n            <a href=\"https://nova.laravel.com\">Nova</a>\n            <a href=\"https://forge.laravel.com\">Forge</a>\n            <a href=\"https://vapor.laravel.com\">Vapor</a>\n            <a href=\"https://github.com/laravel/laravel\">GitHub</a>\n        </div>\n    </div>\n</div>\n</body>\n</html>",
                "selection_selector": ".links a",
                "selection_mode": "last",
                "text": "GitHub"
            },
            "expected_output": "result=matched\nselection_selector=.links a\nselection_mode=last\ntext=GitHub\n"
        },
        {
            "input": {
                "document": "<html lang=\"en\">\n<head>\n    <meta charset=\"utf-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n\n    <title>Laravel</title>\n\n    <!-- Fonts -->\n    <link href=\"https://fonts.googleapis.com/css?family=Nunito:200,600\" rel=\"stylesheet\">\n\n    <!-- Styles -->\n    <style>\n        html, body {\n            background-color: #fff;\n            color: #636b6f;\n            font-family: 'Nunito', sans-serif;\n            font-weight: 200;\n            height: 100vh;\n            margin: 0;\n        }\n\n        .full-height {\n            height: 100vh;\n        }\n\n        .flex-center {\n            align-items: center;\n            display: flex;\n            justify-content: center;\n        }\n\n        .position-ref {\n            position: relative;\n        }\n\n        .top-right {\n            position: absolute;\n            right: 10px;\n            top: 18px;\n        }\n\n        .content {\n            text-align: center;\n        }\n\n        .title {\n            font-size: 84px;\n        }\n\n        .links > a {\n            color: #636b6f;\n            padding: 0 25px;\n            font-size: 13px;\n            font-weight: 600;\n            letter-spacing: .1rem;\n            text-decoration: none;\n            text-transform: uppercase;\n        }\n\n        .m-b-md {\n            margin-bottom: 30px;\n        }\n    </style>\n</head>\n<body>\n<div class=\"flex-center position-ref full-height\">\n\n    <div class=\"content\">\n        <div class=\"title m-b-md\">\n            Laravel\n        </div>\n\n        <div class=\"links\">\n            <a href=\"https://laravel.com/docs\">Docs</a>\n            <a href=\"https://laracasts.com\">Laracasts</a>\n            <a href=\"https://laravel-news.com\">News</a>\n            <a href=\"https://blog.laravel.com\">Blog</a>\n            <a href=\"https://nova.laravel.com\">Nova</a>\n            <a href=\"https://forge.laravel.com\">Forge</a>\n            <a href=\"https://vapor.laravel.com\">Vapor</a>\n            <a href=\"https://github.com/laravel/laravel\">GitHub</a>\n        </div>\n    </div>\n</div>\n</body>\n</html>",
                "selection_selector": ".links a",
                "selection_mode": "last",
                "text": "Laracase"
            },
            "expected_output": "error=assertion_failed\ncondition=ordered_selection_contains_text\nselection_selector=.links a\nselection_mode=last\ntext=Laracase\n"
        }
    ]
}
```

---

### Feature 8: Reusable Custom Document Check

**As a developer**, I want to define and execute reusable document-specific checks, so I can compose higher-level assertions from the same black-box behavior.

**Expected Behavior / Usage:**

The adapter accepts a JSON object with `document` and `charset`. It runs a reusable custom check that narrows to the document head, selects the first metadata element, and verifies that its character set attribute exactly matches the requested value. Success prints `result=matched` and the charset; mismatch prints `error=assertion_failed` and `condition=reusable_check_passes`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_reusable_charset_check.json`

```json
{
    "description": "Allows a reusable custom check to validate that a document head begins with a metadata element declaring an exact character set.",
    "cases": [
        {
            "input": {
                "document": "<html lang=\"en\">\n<head>\n    <meta charset=\"utf-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n\n    <title>Laravel</title>\n\n    <!-- Fonts -->\n    <link href=\"https://fonts.googleapis.com/css?family=Nunito:200,600\" rel=\"stylesheet\">\n\n    <!-- Styles -->\n    <style>\n        html, body {\n            background-color: #fff;\n            color: #636b6f;\n            font-family: 'Nunito', sans-serif;\n            font-weight: 200;\n            height: 100vh;\n            margin: 0;\n        }\n\n        .full-height {\n            height: 100vh;\n        }\n\n        .flex-center {\n            align-items: center;\n            display: flex;\n            justify-content: center;\n        }\n\n        .position-ref {\n            position: relative;\n        }\n\n        .top-right {\n            position: absolute;\n            right: 10px;\n            top: 18px;\n        }\n\n        .content {\n            text-align: center;\n        }\n\n        .title {\n            font-size: 84px;\n        }\n\n        .links > a {\n            color: #636b6f;\n            padding: 0 25px;\n            font-size: 13px;\n            font-weight: 600;\n            letter-spacing: .1rem;\n            text-decoration: none;\n            text-transform: uppercase;\n        }\n\n        .m-b-md {\n            margin-bottom: 30px;\n        }\n    </style>\n</head>\n<body>\n<div class=\"flex-center position-ref full-height\">\n\n    <div class=\"content\">\n        <div class=\"title m-b-md\">\n            Laravel\n        </div>\n\n        <div class=\"links\">\n            <a href=\"https://laravel.com/docs\">Docs</a>\n            <a href=\"https://laracasts.com\">Laracasts</a>\n            <a href=\"https://laravel-news.com\">News</a>\n            <a href=\"https://blog.laravel.com\">Blog</a>\n            <a href=\"https://nova.laravel.com\">Nova</a>\n            <a href=\"https://forge.laravel.com\">Forge</a>\n            <a href=\"https://vapor.laravel.com\">Vapor</a>\n            <a href=\"https://github.com/laravel/laravel\">GitHub</a>\n        </div>\n    </div>\n</div>\n</body>\n</html>",
                "charset": "utf-8"
            },
            "expected_output": "result=matched\ncharset=utf-8\n"
        },
        {
            "input": {
                "document": "<html lang=\"en\">\n<head>\n    <meta charset=\"utf-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n\n    <title>Laravel</title>\n\n    <!-- Fonts -->\n    <link href=\"https://fonts.googleapis.com/css?family=Nunito:200,600\" rel=\"stylesheet\">\n\n    <!-- Styles -->\n    <style>\n        html, body {\n            background-color: #fff;\n            color: #636b6f;\n            font-family: 'Nunito', sans-serif;\n            font-weight: 200;\n            height: 100vh;\n            margin: 0;\n        }\n\n        .full-height {\n            height: 100vh;\n        }\n\n        .flex-center {\n            align-items: center;\n            display: flex;\n            justify-content: center;\n        }\n\n        .position-ref {\n            position: relative;\n        }\n\n        .top-right {\n            position: absolute;\n            right: 10px;\n            top: 18px;\n        }\n\n        .content {\n            text-align: center;\n        }\n\n        .title {\n            font-size: 84px;\n        }\n\n        .links > a {\n            color: #636b6f;\n            padding: 0 25px;\n            font-size: 13px;\n            font-weight: 600;\n            letter-spacing: .1rem;\n            text-decoration: none;\n            text-transform: uppercase;\n        }\n\n        .m-b-md {\n            margin-bottom: 30px;\n        }\n    </style>\n</head>\n<body>\n<div class=\"flex-center position-ref full-height\">\n\n    <div class=\"content\">\n        <div class=\"title m-b-md\">\n            Laravel\n        </div>\n\n        <div class=\"links\">\n            <a href=\"https://laravel.com/docs\">Docs</a>\n            <a href=\"https://laracasts.com\">Laracasts</a>\n            <a href=\"https://laravel-news.com\">News</a>\n            <a href=\"https://blog.laravel.com\">Blog</a>\n            <a href=\"https://nova.laravel.com\">Nova</a>\n            <a href=\"https://forge.laravel.com\">Forge</a>\n            <a href=\"https://vapor.laravel.com\">Vapor</a>\n            <a href=\"https://github.com/laravel/laravel\">GitHub</a>\n        </div>\n    </div>\n</div>\n</body>\n</html>",
                "charset": "not-valid"
            },
            "expected_output": "error=assertion_failed\ncondition=reusable_check_passes\ncharset=not-valid\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[name].json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[name]@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same scope application pattern as used in the root attribute matcher
- use the exact attribute name convention defined in the metadata parser utility
