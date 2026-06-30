## Product Requirement Document

# HTML Minification Library & Web Response Filter - Product Requirements

## Project Goal

Build an HTML minification library that shrinks HTML payloads by removing insignificant whitespace, line breaks, and comments, together with a web-framework integration layer (a response filter and per-view wrappers) that applies that minification automatically to outgoing HTML responses. This lets developers ship smaller pages without hand-editing templates or post-processing output by hand.

---

## Background & Problem

Without this library, developers who want compact HTML must either author their templates with no readable indentation (sacrificing maintainability) or wire up an ad-hoc post-processing step that is easy to get wrong: naive whitespace stripping corrupts the content of `pre`, `script`, and `textarea` elements, drops meaningful spacing around inline links, breaks non-ASCII text, or strips comments that were meant to survive (such as downlevel-revealed conditional comments). Doing this safely requires real HTML parsing, which is repetitive boilerplate to reimplement per project.

With this library, developers keep their templates readable and delegate minification to a well-tested component. The same minification core can be called directly on an HTML string, applied globally to every eligible HTTP response through a response filter (with configuration for which URLs to skip, whether to keep comments, and a global on/off switch), or applied selectively to individual views through opt-in / opt-out wrappers.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility system (a pure minification core, a byte-decoding utility, a response-filter integration, and per-view wrappers). It MUST NOT be a single "god file". Separate the parsing/minification core, the HTTP integration layer, and the execution adapter into distinct modules that reflect a production-grade repository layout.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box contract for the execution adapter**, not the internal data model of the core. The minification core must operate on plain HTML strings and must know nothing about JSON, stdin, or stdout. The web-integration layer must depend only on abstract request/response shapes (a status code, a content-type header, a body, a path, and per-response flags), not on the adapter. The adapter alone translates JSON commands into idiomatic calls and renders the neutral stdout contract.

3. **Adherence to SOLID Design Principles:** Separate parsing, response-eligibility decisions, configuration reading, core minification, and output formatting into distinct logical units. The minification core must be open for extension (e.g. new protected tags) but closed for modification. Keep the request/response abstractions small and cohesive. High-level policy (when to minify) must depend on abstractions, not on concrete I/O.

4. **Robustness & Interface Design:** The public surface must be idiomatic and elegant in the target language. The core must gracefully preserve protected regions and non-ASCII text rather than corrupting them. Configuration absence must be handled with well-defined defaults rather than crashes. Errors must be modeled explicitly and surfaced through the neutral categories described in the adapter contract, never as raw host-language runtime artifacts.

---

## Core Features

### Feature 1: HTML Minification Core

**As a developer**, I want a function that takes an HTML document and returns a compact equivalent, so I can reduce payload size without altering how the page renders.

**Expected Behavior / Usage:**

The core accepts an HTML document (as text/bytes) and returns a single-line minified string. It performs real HTML parsing: the output is a normalized serialization where insignificant whitespace between and inside tags is collapsed, the document is emitted on one logical line, attribute serialization is normalized, and a `head` element is materialized when the source omits one. The protected elements `pre`, `script`, and `textarea` have their inner content preserved verbatim. Comments are removed by default but can be retained on request, and conditional comments are always retained. Encoding is preserved. The behavior is decomposed into the leaf sub-features below.

*1.1 Whitespace collapsing — insignificant spaces become a single space and the document is flattened to one line*

Runs of spaces, tabs, and indentation that sit between tags or around text are collapsed to a single space, and the whole document is serialized onto one line. Where the parser must materialize a missing structural element (for example an absent `head`), it appears in the output. A trailing space that results from collapsing is preserved where the serialization produces one.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_whitespace.json`

```json
{
    "description": "Collapse runs of insignificant whitespace between and inside tags into a single space, while normalizing the document into a single line; the parser also inserts an empty head when one is absent.",
    "cases": [
        {
            "input": { "op": "minify", "html": "<html>   <body>some text here</body>    </html>" },
            "expected_output": "<html><head></head><body>some text here </body></html>\n"
        },
        {
            "input": { "op": "minify", "html": "<html>\n    <body>I selected you!</body>\n    </html>" },
            "expected_output": "<html><head></head><body>I selected you!</body></html>\n"
        }
    ]
}
```

*1.2 Line-break handling — newlines become single spaces without doubling, blank lines between blocks are dropped*

An embedded newline inside text content is converted to a single space. When a space already precedes the newline, the result must still be a single space (no double space). Blank lines separating block-level elements are removed entirely.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_linebreaks.json`

```json
{
    "description": "Convert embedded newlines to a single space without producing double spaces, and drop blank lines between block elements.",
    "cases": [
        {
            "input": { "op": "minify", "html": "<html><body>Click <a href=\"#\">here</a>\nto see more</body></html>" },
            "expected_output": "<html><head></head><body>Click <a href=\"#\">here</a> to see more</body></html>\n"
        },
        {
            "input": { "op": "minify", "html": "<html><body>Click <a href=\"#\">here</a> \nto see more</body></html>" },
            "expected_output": "<html><head></head><body>Click <a href=\"#\">here</a> to see more</body></html>\n"
        }
    ]
}
```

*1.3 DOCTYPE preservation — keep an existing doctype, never invent one*

If the source has a DOCTYPE declaration it is preserved (with its own internal whitespace collapsed to single spaces); if the source has no DOCTYPE, none is added.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_doctype.json`

```json
{
    "description": "Preserve an existing DOCTYPE declaration exactly (collapsing internal whitespace) and never invent one when the source omits it.",
    "cases": [
        {
            "input": { "op": "minify", "html": "<html>\n    <head>\n        <meta charset=\"utf-8\">\n        <title>Page title</title>\n    </head>\n    <body>\n        Hello!\n    </body>\n</html>\n" },
            "expected_output": "<html><head><meta charset=\"utf-8\"/><title>Page title</title></head><body>Hello!</body></html>\n"
        },
        {
            "input": { "op": "minify", "html": "<!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.0 Strict//EN\"\n        \"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd\">\n<html>\n    <head>\n        <meta charset=\"utf-8\">\n        <title>Page title</title>\n    </head>\n    <body>\n        Hello!\n    </body>\n</html>\n" },
            "expected_output": "<!DOCTYPE html PUBLIC \"-//W3C//DTD XHTML 1.0 Strict//EN\" \"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd\"><html><head><meta charset=\"utf-8\"/><title>Page title</title></head><body>Hello!</body></html>\n"
        }
    ]
}
```

*1.4 Protected regions — content of pre, script, and textarea is preserved verbatim*

The inner content of `pre`, `script`, and `textarea` elements is left byte-for-byte intact: whitespace, indentation, and line breaks inside them survive even though surrounding markup is minified. Literal HTML written inside a `textarea` is escaped to entities by the parse/serialize round-trip, while entities already present inside a `textarea` are left unchanged. Attribute serialization on the surrounding tags is still normalized.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_protected_regions.json`

```json
{
    "description": "Leave the inner content of pre, script and textarea elements byte-for-byte intact (whitespace, line breaks and any literal HTML), while still minifying the surrounding markup; HTML appearing inside textarea is escaped to entities by parsing, and pre-existing entities are left untouched.",
    "cases": [
        {
            "input": { "op": "minify", "html": "<html>\n    <head>\n        <title>Hello world, with AJAX</title>\n        <script src=\"http://ajax.aspnetcdn.com/ajax/jQuery/jquery-1.6.min.js\" type=\"text/javascript\" charset=\"utf-8\"></script>\n        <script type=\"text/javascript\" language=\"javascript\" charset=\"utf-8\">\n            $(document).ready(function () {\n                alert('Hi dudes!');\n            });\n        </script>\n    </head>\n    <body>\n        <div class=\"menu\">\n            \n            <ul>\n                <li>Home</li>\n                <li>About</li>\n                <li>Contact</li>\n            </ul>\n\n        </div>\n    </body>\n</html>\n" },
            "expected_output": "<html><head><title>Hello world, with AJAX</title><script charset=\"utf-8\" src=\"http://ajax.aspnetcdn.com/ajax/jQuery/jquery-1.6.min.js\" type=\"text/javascript\"></script><script charset=\"utf-8\" language=\"javascript\" type=\"text/javascript\">\n            $(document).ready(function () {\n                alert('Hi dudes!');\n            });\n        </script></head><body><div class=\"menu\"><ul><li>Home</li><li>About</li><li>Contact</li></ul></div></body></html>\n"
        },
        {
            "input": { "op": "minify", "html": "<html>\n    <head>\n        <meta charset=\"utf-8\">\n        <title>Hello world</title>\n    </head>\n    <body>\n        <p>Here is your data:</p>\n        <label for=\"content\">Content:</label>\n        <textarea name=\"content\" rows=\"8\" cols=\"40\" id=\"content\">I am ready for working hard.\n\nOr not.</textarea>\n    </body>\n</html>\n" },
            "expected_output": "<html><head><meta charset=\"utf-8\"/><title>Hello world</title></head><body><p>Here is your data:</p><label for=\"content\">Content:</label><textarea cols=\"40\" id=\"content\" name=\"content\" rows=\"8\">I am ready for working hard.\n\nOr not.</textarea></body></html>\n"
        }
    ]
}
```

*1.5 Comment handling — strip comments by default, optionally keep them, always keep conditional comments*

By default all HTML comments (single-line, multi-line, and multiple comments on one page) are removed. When comment retention is requested, comments are kept. Downlevel-revealed conditional comments (`<!--[if ...]> ... <![endif]-->`) are always retained regardless of the setting.

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_comments.json`

```json
{
    "description": "By default strip HTML comments (including multi-line and multiple comments); when comment retention is requested keep them; downlevel-revealed conditional comments are always retained regardless of the setting.",
    "cases": [
        {
            "input": { "op": "minify", "html": "<!DOCTYPE html>\n<html lang=\"pt-BR\">\n    <head>\n        <meta charset=\"utf-8\">\n        <title>Page Title</title>\n    </head>\n\n    <body>\n        <!-- this comment should be excluded, because I didn't like it! -->\n        <h1>Header</h1>\n    </body>\n</html>\n" },
            "expected_output": "<!DOCTYPE html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\"/><title>Page Title</title></head><body><h1>Header</h1></body></html>\n"
        },
        {
            "input": { "op": "minify", "ignore_comments": false, "html": "<!DOCTYPE html>\n<html lang=\"pt-BR\">\n    <head>\n        <meta charset=\"utf-8\">\n        <title>Page Title</title>\n    </head>\n\n    <body>\n        <!-- this comment should be included, because I like it! -->\n        <h1>Header</h1>\n    </body>\n</html>\n" },
            "expected_output": "<!DOCTYPE html><html lang=\"pt-BR\"><head><meta charset=\"utf-8\"/><title>Page Title</title></head><body><!-- this comment should be included, because I like it! --><h1>Header</h1></body></html>\n"
        }
    ]
}
```

*1.6 Encoding preservation — non-ASCII text survives in content and protected regions*

UTF-8 / non-ASCII text is preserved exactly, both in ordinary content and inside protected elements such as `textarea`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_6_encoding.json`

```json
{
    "description": "Preserve non-ASCII (UTF-8) text correctly in normal content and inside protected regions, including a full real-world blog page.",
    "cases": [
        {
            "input": { "op": "minify", "html": "<html>\n    <head>\n        <meta charset=\"utf-8\"/>\n        <title>Unicode</title>\n    </head>\n    <body>\n        <p>This is a UTF-8 string with non ascii characters: ɐ ɑ ɒ ɓ ɔ ɕ ɖ ɗ ɘ ə ɚ ɛ ɜ </p>\n    </body>\n</html>\n" },
            "expected_output": "<html><head><meta charset=\"utf-8\"/><title>Unicode</title></head><body><p>This is a UTF-8 string with non ascii characters: ɐ ɑ ɒ ɓ ɔ ɕ ɖ ɗ ɘ ə ɚ ɛ ɜ </p></body></html>\n"
        },
        {
            "input": { "op": "minify", "html": "<html>\n    <head>\n        <meta charset=\"utf-8\"/>\n        <title>Unicode</title>\n    </head>\n    <body>\n        <p>This is a UTF-8 string with non ascii characters: ɐ ɑ ɒ ɓ ɔ ɕ ɖ ɗ ɘ ə ɚ ɛ ɜ </p>\n        <textarea>and smore more non ascii inside an excluded element  ʘ ʙ ʚ ʛ ʜ ʝ ʞ ʟ ʠ ʡ ʢ</textarea>\n    </body>\n</html>\n" },
            "expected_output": "<html><head><meta charset=\"utf-8\"/><title>Unicode</title></head><body><p>This is a UTF-8 string with non ascii characters: ɐ ɑ ɒ ɓ ɔ ɕ ɖ ɗ ɘ ə ɚ ɛ ɜ </p><textarea>and smore more non ascii inside an excluded element  ʘ ʙ ʚ ʛ ʜ ʝ ʞ ʟ ʠ ʡ ʢ</textarea></body></html>\n"
        }
    ]
}
```

*1.7 Whole-document minification — classic and HTML5 documents end to end*

A complete document, including HTML5 sectioning elements, is minified end to end into one line with all leaf behaviors above applied together.

**Test Cases:** `rcb_tests/public_test_cases/feature1_7_documents.json`

```json
{
    "description": "Minify complete documents end to end, including classic markup with a menu and HTML5 sectioning elements.",
    "cases": [
        {
            "input": { "op": "minify", "html": "<html>\n    <head>\n        <title>Hello world!</title>\n    </head>\n    <body>\n        <h1>Hello world</h1>\n        <div class=\"menu\">\n            <ul>\n                <li>Home</li>\n                <li>About</li>\n            </ul>\n        </div>\n    </body>\n</html>\n" },
            "expected_output": "<html><head><title>Hello world!</title></head><body><h1>Hello world</h1><div class=\"menu\"><ul><li>Home</li><li>About</li></ul></div></body></html>\n"
        }
    ]
}
```

---

### Feature 2: Robust Byte Decoding

**As a developer**, I want a helper that turns a raw byte string into text by trying a preferred encoding and falling back through alternatives, so I can feed bytes of uncertain encoding to the minifier without crashing.

**Expected Behavior / Usage:**

The helper takes raw bytes and an optional preferred encoding. It attempts the preferred encoding first, then falls back through a fixed sequence of alternatives, returning the first successfully decoded text. The default preferred encoding decodes typical UTF-8 input; the same value can also be recovered when supplied in a compatible single-byte fallback encoding; and the caller may override the preferred encoding to decode bytes produced by a less common codec. The adapter renders the recovered text on a line of the form `decoded=<text>`. (The byte payload is supplied to the adapter as a Base64 string under `bytes_base64`; the optional preferred encoding is the `encoding` field.)

**Test Cases:** `rcb_tests/public_test_cases/feature2_decode_bytes.json`

```json
{
    "description": "Decode a raw byte string into text by trying a preferred encoding first and falling back through alternatives, returning the recovered text; the caller may override the preferred encoding.",
    "cases": [
        {
            "input": { "op": "decode_bytes", "bytes_base64": "QmzDoSBibMOh" },
            "expected_output": "decoded=Blá blá\n"
        },
        {
            "input": { "op": "decode_bytes", "bytes_base64": "QmzhIGJs4Q==" },
            "expected_output": "decoded=Blá blá\n"
        },
        {
            "input": { "op": "decode_bytes", "encoding": "IBM857", "bytes_base64": "QmygIGJsoA==" },
            "expected_output": "decoded=Blá blá\n"
        }
    ]
}
```

---

### Feature 3: Response Filter Integration

**As a developer**, I want a response filter that automatically minifies outgoing HTML responses according to configuration, so every eligible page is minified without touching individual views.

**Expected Behavior / Usage:**

The filter inspects a finished response together with its originating request and decides whether to minify the body in place. The decision combines response eligibility (status and media type), per-request eligibility, configured URL exclusions, a per-response opt-out flag, a global on/off switch, and a comment-retention setting. When all conditions are met the body is minified using the core; otherwise the body is passed through unchanged. The adapter renders, for each case, the resulting `status_code`, the `content_type` header, a `---content---` separator line, and then the (possibly minified) body. Configuration is supplied through neutral command fields: `status_code`, `content_type`, `content`, `path`, `hit` (whether the request passed the filter's request phase), `minify_response` (per-response flag), `exclude_paths`, `keep_comments`, `minify_enabled`, and `debug`. A field set to `null` means "this setting is absent" so the corresponding default behavior is exercised.

*3.1 Response gating — only success + HTML responses are minified*

Minification is applied only when the response has a success status (200) and an HTML media type. Any non-success status code, or any non-HTML media type, results in the body being passed through unchanged. A media type that carries a charset suffix still counts as HTML.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_response_gating.json`

```json
{
    "description": "Only post-process responses that return a success status and an HTML media type; any other status code or media type passes the body through unchanged. A charset suffix on the media type still counts as HTML.",
    "cases": [
        {
            "input": { "op": "middleware_response", "status_code": 301, "content": "<html>   <body>some text here</body>    </html>" },
            "expected_output": "status_code=301\ncontent_type=text/html\n---content---\n<html>   <body>some text here</body>    </html>\n"
        },
        {
            "input": { "op": "middleware_response", "status_code": 200, "content": "<html>   <body>some text here</body>    </html>" },
            "expected_output": "status_code=200\ncontent_type=text/html\n---content---\n<html><head></head><body>some text here </body></html>\n"
        },
        {
            "input": { "op": "middleware_response", "content_type": "text/html; charset=utf-8", "content": "<html>   <body>some text here</body>    </html>" },
            "expected_output": "status_code=200\ncontent_type=text/html; charset=utf-8\n---content---\n<html><head></head><body>some text here </body></html>\n"
        },
        {
            "input": { "op": "middleware_response", "content_type": "application/json", "content": "<html>   <body>some text here</body>    </html>" },
            "expected_output": "status_code=200\ncontent_type=application/json\n---content---\n<html>   <body>some text here</body>    </html>\n"
        }
    ]
}
```

Note on the gating cases: cases 1 and 4 stay unminified because the status code / media type fail the gate; cases 2 and 3 pass the gate (success status, HTML media type including a charset suffix) and are therefore minified.

*3.2 URL exclusion — configured path patterns are skipped*

When the configuration lists URL exclusion patterns, a request whose path (with any single leading slash removed) matches a pattern is not minified and its body passes through unchanged. When no exclusion list is configured, an otherwise-eligible response is minified.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_url_exclusion.json`

```json
{
    "description": "Skip minification for request paths matching the configured exclusion patterns (matched against the path with any leading slash removed); when no exclusion list is configured, eligible responses are minified.",
    "cases": [
        {
            "input": { "op": "middleware_response", "path": "/raw/", "exclude_paths": ["^raw"], "content": "<html>   <body>some text here</body>    </html>" },
            "expected_output": "status_code=200\ncontent_type=text/html\n---content---\n<html>   <body>some text here</body>    </html>\n"
        },
        {
            "input": { "op": "middleware_response", "path": "/", "exclude_paths": null, "content": "<html>   <body>some text here</body>    </html>" },
            "expected_output": "status_code=200\ncontent_type=text/html\n---content---\n<html><head></head><body>some text here </body></html>\n"
        }
    ]
}
```

*3.3 Per-response opt-out flag — an explicit flag overrides minification*

A response may carry a per-response flag. When the flag is false the body is passed through unchanged; when the flag is true the response is minified.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_response_optout.json`

```json
{
    "description": "Honor a per-response opt-out flag: a response explicitly flagged to skip minification is passed through unchanged, while a response flagged to allow it is minified.",
    "cases": [
        {
            "input": { "op": "middleware_response", "minify_response": false, "content": "<html>   <body>some text here</body>    </html>" },
            "expected_output": "status_code=200\ncontent_type=text/html\n---content---\n<html>   <body>some text here</body>    </html>\n"
        },
        {
            "input": { "op": "middleware_response", "minify_response": true, "content": "<html>   <body>some text here</body>    </html>" },
            "expected_output": "status_code=200\ncontent_type=text/html\n---content---\n<html><head></head><body>some text here </body></html>\n"
        }
    ]
}
```

*3.4 Comment retention setting — global control over comment removal*

When the comment-retention setting is enabled, comments in the response body survive minification. When it is disabled, or absent (default), comments are stripped.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_comment_retention.json`

```json
{
    "description": "Control comment handling globally: when comment retention is enabled the comment survives minification; when it is disabled or unspecified the comment is stripped.",
    "cases": [
        {
            "input": { "op": "middleware_response", "keep_comments": true, "content": "<html>   <!-- some comment --><body>some text here</body>    </html>" },
            "expected_output": "status_code=200\ncontent_type=text/html\n---content---\n<html><!-- some comment --><head></head><body>some text here </body></html>\n"
        },
        {
            "input": { "op": "middleware_response", "keep_comments": false, "content": "<html>   <!-- some comment --><body>some text here</body>    </html>" },
            "expected_output": "status_code=200\ncontent_type=text/html\n---content---\n<html><head></head><body>some text here </body></html>\n"
        }
    ]
}
```

Note: with comment retention enabled the body is minified but the comment is preserved; with it disabled the comment is removed and the body is minified.

*3.5 Global minify switch — explicit off, and the debug-driven default*

A global switch controls minification. When it is explicitly disabled the body is untouched. When the switch is absent, the default is derived from a debug indicator: in debug mode minification is off (bodies pass through), and in non-debug mode it is on.

**Test Cases:** `rcb_tests/public_test_cases/feature3_5_global_toggle.json`

```json
{
    "description": "Respect the global minification switch: when explicitly disabled the body is untouched; when unset, debug mode disables minification while non-debug mode enables it.",
    "cases": [
        {
            "input": { "op": "middleware_response", "minify_enabled": false, "content": "<html>   <body>some text here</body>    </html>" },
            "expected_output": "status_code=200\ncontent_type=text/html\n---content---\n<html>   <body>some text here</body>    </html>\n"
        },
        {
            "input": { "op": "middleware_response", "minify_enabled": null, "debug": true, "content": "<html>   <body>some text here</body>    </html>" },
            "expected_output": "status_code=200\ncontent_type=text/html\n---content---\n<html>   <body>some text here</body>    </html>\n"
        },
        {
            "input": { "op": "middleware_response", "minify_enabled": null, "debug": false, "content": "<html>   <body>some text here</body>    </html>" },
            "expected_output": "status_code=200\ncontent_type=text/html\n---content---\n<html><head></head><body>some text here </body></html>\n"
        }
    ]
}
```

*3.6 Per-request eligibility — only requests that passed the request phase are minified*

The filter only minifies responses for requests that passed through its request phase (marking the request as eligible). A request that did not pass through that phase leaves its response unchanged; a request that did pass through is eligible and is minified.

**Test Cases:** `rcb_tests/public_test_cases/feature3_6_request_eligibility.json`

```json
{
    "description": "Only minify responses for requests that passed through the request phase of the middleware; a request that never hit the middleware leaves its response unchanged.",
    "cases": [
        {
            "input": { "op": "middleware_response", "hit": true, "content": "<html>   <body>some text here</body>    </html>" },
            "expected_output": "status_code=200\ncontent_type=text/html\n---content---\n<html><head></head><body>some text here </body></html>\n"
        },
        {
            "input": { "op": "middleware_response", "hit": false, "content": "<html>   <body>some text here</body>    </html>" },
            "expected_output": "status_code=200\ncontent_type=text/html\n---content---\n<html>   <body>some text here</body>    </html>\n"
        }
    ]
}
```

---

### Feature 4: Per-View Decorators

**As a developer**, I want wrappers that turn minification on or off for a single view, so I can override the global policy where needed.

**Expected Behavior / Usage:**

Two view wrappers provide per-view control over the response filter. One wrapper minifies the HTML produced by the wrapped view directly. The other wrapper marks its response as non-minifiable by attaching an opt-out flag, leaving the body untouched (so the filter will later skip it). The cases exercise both wrappers through the HTTP layer: a request to the minified route returns minified HTML with no opt-out flag set, and a request to the opt-out route returns the original (unminified) body carrying a false opt-out flag. The adapter renders the `status_code`, a `minify_response` line (`unset`, `true`, or `false`), a `---content---` separator, and the body.

**Test Cases:** `rcb_tests/public_test_cases/feature4_view_decorators.json`

```json
{
    "description": "Expose per-view control over minification through the HTTP layer: one route is wrapped so its rendered HTML is minified, another is wrapped to mark its response as non-minifiable (carrying an opt-out flag) and leaves the body untouched.",
    "cases": [
        {
            "input": { "op": "view_request", "path": "/min" },
            "expected_output": "status_code=200\nminify_response=unset\n---content---\n<html><head></head><body><p>Hello world! :D</p><div>Copyright 3000</div></body></html>\n"
        },
        {
            "input": { "op": "view_request", "path": "/not_min" },
            "expected_output": "status_code=200\nminify_response=false\n---content---\n\n<html>\n    <body>\n        <p>Hello world! :D</p>\n        <div>Copyright 3000</div>\n    </body>\n</html>\n    \n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above — the minification core, the byte-decoding utility, the response-filter integration, and the per-view wrappers — organized into distinct modules per the "Scale-Driven Code Organization" constraint, with the core fully decoupled from I/O and configuration sources.

2. **The Execution/Test Adapter:** A runnable entry point that reads a single JSON command object from stdin, dispatches on its `op` field (`minify`, `decode_bytes`, `middleware_response`, `view_request`), invokes the appropriate core logic, and prints the neutral stdout contract described per leaf feature. The adapter is the only component aware of JSON and stdout, and is the layer responsible for translating any raised error into a neutral category line (for example `error=unknown_op` / `op=<value>` for an unrecognized command, or `error=invalid_json` for malformed input); it must never leak host-language exception types or runtime artifacts.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory (default `public_test_cases`; the full hidden set lives in `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_1_whitespace.json` under `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_whitespace@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites results. Each `.txt` file contains **only** the raw stdout of the program under test (no PASS/FAIL summaries or metadata), so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- non-200 status codes defined in CLI contract
- allowed text types for minification
