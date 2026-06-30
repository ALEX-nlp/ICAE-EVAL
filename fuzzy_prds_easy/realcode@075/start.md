## Product Requirement Document

# HTML Content Processing Pipeline - Safe Transformation of User-Authored Markup

## Project Goal

Build a content-processing library that allows developers to transform user-authored text, Markdown, and HTML fragments into safe, enriched HTML without hand-writing repetitive parsing, linking, sanitizing, and navigation-generation logic.

---

## Background & Problem

Without this library/tool, developers are forced to combine separate parsers, URL rewriters, sanitizers, mention scanners, emoji renderers, and table-of-contents builders manually. This leads to repetitive code, inconsistent escaping, missed edge cases, unsafe links, and fragile behavior whenever user-authored content mixes Markdown, HTML, URLs, images, and mentions.

With this library/tool, developers can pass well-defined text or HTML inputs through composable content transformations and receive deterministic HTML or structured text signals suitable for rendering, indexing, or testing.

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

### Feature 1: Plain Text Input Escaping

**As a developer**, I want to wrap untrusted plain text into an HTML fragment, so I can feed user text into an HTML-processing workflow without accidentally treating it as markup.

**Expected Behavior / Usage:**

The input is a JSON object with a `text` string. The output is an HTML fragment containing one wrapper element around the escaped text, followed by a trailing newline. Any markup-looking characters in the text must be escaped so they render as text rather than elements. If parsed HTML is supplied instead of text, the adapter reports `error=invalid_input_type` with the expected input category.

**Test Cases:** `rcb_tests/public_test_cases/feature1_plain_text_input.json`

```json
{
    "description": "Plain text is wrapped and HTML-escaped before later HTML processing.",
    "cases": [
        {
            "input": {
                "text": "howdy pahtner"
            },
            "expected_output": "<div>howdy pahtner</div>\n"
        },
        {
            "input": {
                "text": "See: <http://example.org>"
            },
            "expected_output": "<div>See: [escape single quotes and double quotes within the block]http://example.org[escape single quotes and double quotes within the block]</div>\n"
        }
    ]
}
```

---

### Feature 2: Markdown Rendering

**As a developer**, I want to convert Markdown text into HTML fragments, so I can support authored prose, line breaks, lists, and fenced code using a simple text input.

**Expected Behavior / Usage:**

The input is a JSON object with a `text` string and, when needed, a `soft_line_breaks` boolean. The output is the rendered HTML fragment followed by a trailing newline. Soft line breaks insert `<br>` elements inside paragraph text when enabled, but list structure is preserved. Fenced code blocks render as preformatted code, and an optional fence language is preserved as a language signal on the rendered block. Parsed HTML supplied in place of text is rejected with `error=invalid_input_type`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_markdown_rendering.json`

```json
{
    "description": "Markdown text is converted to HTML with configurable GitHub-style line break behavior and fenced-code handling.",
    "cases": [
        {
            "input": {
                "text": "Pointing at the moon\nReminded of simple things\nMoments matter most",
                "soft_line_breaks": true
            },
            "expected_output": "<p>Pointing at the moon<br>\nReminded of simple things<br>\nMoments matter most</p>\n"
        },
        {
            "input": {
                "text": "Pointing at the moon\nReminded of simple things\nMoments matter most",
                "soft_line_breaks": false
            },
            "expected_output": "<p>Pointing at the moon\nReminded of simple things\nMoments matter most</p>\n"
        }
    ]
}
```

---

### Feature 3: Automatic URL Linking

**As a developer**, I want to turn visible bare URLs inside HTML text into hyperlinks, so I can make user-authored links clickable without manually parsing every text node.

**Expected Behavior / Usage:**

The input is a JSON object with an `html` fragment and optional controls for disabling linking, adding raw link attributes, enabling short-domain recognition, or changing skipped element names. The output is the transformed HTML fragment followed by a trailing newline. URLs in ordinary text become anchors whose `href` is the same URL. When linking is disabled the fragment is unchanged. Protected elements are skipped unless the caller overrides the skip list.

**Test Cases:** `rcb_tests/public_test_cases/feature3_autolink.json`

```json
{
    "description": "Bare URLs in HTML text are converted to anchors unless disabled or skipped by tag rules.",
    "cases": [
        {
            "input": {
                "html": "<p>\"http://www.github.com\"</p>"
            },
            "expected_output": "<p>\"<a href=\"http://www.github.com\">http://www.github.com</a>\"</p>\n"
        },
        {
            "input": {
                "html": "<p>\"http://www.github.com\"</p>",
                "enabled": false
            },
            "expected_output": "<p>\"http://www.github.com\"</p>\n"
        }
    ]
}
```

---

### Feature 4: Emoji Image Replacement

**As a developer**, I want to replace colon-delimited emoji tokens with image elements, so I can display emoji aliases consistently using caller-provided image assets.

**Expected Behavior / Usage:**

The input is a JSON object with an `html` string plus an `image_asset_root`, and optionally an `image_asset_path` pattern. The output is an HTML fragment followed by a trailing newline. Recognized colon-delimited emoji aliases become image elements whose source URL combines the asset root with the encoded emoji filename. Emoji names containing URL-reserved characters are percent-encoded in the image URL. Missing asset configuration is reported as `error=missing_required_input`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_emoji_rendering.json`

```json
{
    "description": "Colon-delimited emoji names are replaced with image tags whose source is built from the configured image asset location.",
    "cases": [
        {
            "input": {
                "html": "<p>:shipit:</p>",
                "image_asset_root": "https://foo.com"
            },
            "expected_output": "<p><img class=\"emoji\" title=\":shipit:\" alt=\":shipit:\" src=\"https://foo.com/emoji/shipit.png\" height=\"20\" width=\"20\" align=\"absmiddle\"></p>\n"
        },
        {
            "input": {
                "html": ":shipit:",
                "image_asset_root": "https://foo.com"
            },
            "expected_output": "<img class=\"emoji\" title=\":shipit:\" alt=\":shipit:\" src=\"https://foo.com/emoji/shipit.png\" height=\"20\" width=\"20\" align=\"absmiddle\">\n"
        }
    ]
}
```

---

### Feature 5: Absolute Image Source Rewriting

**As a developer**, I want to rewrite relative image sources to absolute URLs, so I can serve images correctly after content moves between pages or hosts.

**Expected Behavior / Usage:**

The input is a JSON object with an `html` fragment and URL context for a site image root and current page location. The output is the transformed HTML fragment followed by a trailing newline. Root-relative image paths are resolved against the image root. Page-relative image paths are resolved against the current page URL. Already absolute image URLs are preserved. If a needed URL context is absent, the adapter reports `error=missing_required_input` and names the missing field.

**Test Cases:** `rcb_tests/public_test_cases/feature5_image_source_urls.json`

```json
{
    "description": "Relative image sources are rewritten to absolute URLs using either a site image root or the current page URL.",
    "cases": [
        {
            "input": {
                "html": "<p><img src=\"/img.png\"></p>",
                "image_base_url": "http://assets.example.com",
                "image_page_url": "http://blog.example.com/a/post"
            },
            "expected_output": "<p><img src=\"http://assets.example.com/img.png\"></p>\n"
        },
        {
            "input": {
                "html": "<p><img src=\"post/img.png\"></p>",
                "image_base_url": "http://assets.example.com",
                "image_page_url": "http://blog.example.com/a/post"
            },
            "expected_output": "<p><img src=\"http://blog.example.com/a/post/img.png\"></p>\n"
        }
    ]
}
```

---

### Feature 6: External Image Proxying

**As a developer**, I want to rewrite remote image URLs through a configured proxy, so I can protect readers from direct loads of non-whitelisted remote images.

**Expected Behavior / Usage:**

The input is a JSON object with an `html` fragment, a `proxy_endpoint`, a `proxy_secret`, and optional `disabled` flag. The output is the transformed HTML fragment followed by a trailing newline. Absolute remote image URLs outside the whitelist are replaced by proxy URLs and retain their original URL in `data-canonical-src`. Whitelisted hosts, root-relative paths, page-relative paths, images with no source, and disabled proxy runs leave the image source unchanged. Missing proxy configuration is reported as `error=missing_required_input`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_image_proxying.json`

```json
{
    "description": "External absolute image URLs are rewritten through a configured image proxy while whitelisted hosts and local paths are preserved.",
    "cases": [
        {
            "input": {
                "html": "<p><img src=\"http://twitter.com/img.png\"></p>",
                "proxy_endpoint": "https//assets.example.org",
                "proxy_secret": "ssssh-secret",
                "disabled": true
            },
            "expected_output": "<p><img src=\"http://twitter.com/img.png\"></p>\n"
        },
        {
            "input": {
                "html": "<p><img src=\"http://twitter.com/img.png\"></p>",
                "proxy_endpoint": "https//assets.example.org",
                "proxy_secret": "ssssh-secret"
            },
            "expected_output": "<p><img src=\"https//assets.example.org/a5ad43494e343b20d745586282be61ff530e6fa0/687474703a2f2f747769747465722e636f6d2f696d672e706e67\" data-canonical-src=\"http://twitter.com/img.png\"></p>\n"
        }
    ]
}
```

---

### Feature 7: Same-Site HTTPS Upgrade

**As a developer**, I want to upgrade links for a configured HTTP site origin to HTTPS, so I can avoid insecure links while not changing unrelated domains.

**Expected Behavior / Usage:**

The input is a JSON object with an `html` fragment and either a canonical site URL or an explicit HTTP site URL. The output is the transformed HTML fragment followed by a trailing newline. Links whose `href` exactly targets the configured HTTP origin are upgraded to HTTPS. Existing HTTPS links, subdomains, and different domains are not changed. If no site URL is provided, the adapter reports `error=missing_required_input`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_same_host_https.json`

```json
{
    "description": "Links pointing to the configured HTTP site root are upgraded to HTTPS while subdomains and other domains are left unchanged.",
    "cases": [
        {
            "input": {
                "html": "<a href=\"http://github.com\">github.com</a>",
                "canonical_site_url": "http://github.com"
            },
            "expected_output": "<a href=\"https://github.com\">github.com</a>\n"
        },
        {
            "input": {
                "html": "<a href=\"https://github.com\">github.com</a>",
                "canonical_site_url": "http://github.com"
            },
            "expected_output": "<a href=\"https://github.com\">github.com</a>\n"
        }
    ]
}
```

---

### Feature 8: Responsive Image Wrapping

**As a developer**, I want to make image elements fit their container and link to the original image, so I can avoid oversized embedded images while preserving access to the source asset.

**Expected Behavior / Usage:**

The input is a JSON object with an `html` fragment. The output is the transformed HTML fragment followed by a trailing newline. Images without an existing style receive a maximum-width style. Images not already inside a link are wrapped in a link that opens the image source in a new browsing context. Existing image styles are preserved, and images already inside links are not wrapped again.

**Test Cases:** `rcb_tests/public_test_cases/feature8_responsive_images.json`

```json
{
    "description": "Images without existing style are constrained to the container width and linked to their source unless already inside a link.",
    "cases": [
        {
            "input": {
                "html": "<p>Screenshot: <img src='screenshot.png'></p>"
            },
            "expected_output": "<p>Screenshot: <a href=\"screenshot.png\" target=\"_blank\"><img src=\"screenshot.png\" style=\"max-width:100%;\"></a></p>\n"
        },
        {
            "input": {
                "html": "<p><img src='screenshot.png' style='width:100px;'></p>"
            },
            "expected_output": "<p><img src=\"screenshot.png\" style=\"width:100px;\"></p>\n"
        }
    ]
}
```

---

### Feature 9: Mention Link Rendering

**As a developer**, I want to convert user mention tokens in HTML text into profile links, so I can make mentions navigable without altering code, preformatted text, or existing links.

**Expected Behavior / Usage:**

The input is a JSON object with an `html` fragment, a `profile_base_url`, and optionally a `generic_info_url` for generic mention help. The output is the transformed HTML fragment followed by a trailing newline. Valid mention tokens in normal text become anchors with a user-mention class. Mentions inside preformatted blocks, inline code, or existing anchors are left unchanged. Encoded text is normalized safely, and escaped markup remains escaped.

**Test Cases:** `rcb_tests/public_test_cases/feature9_mention_links.json`

```json
{
    "description": "User mention tokens in rendered HTML are linked to profile URLs outside protected tags, with safe entity handling.",
    "cases": [
        {
            "input": {
                "html": "<p>@kneath: check it out.</p>",
                "profile_base_url": "/"
            },
            "expected_output": "<p><a href=\"/kneath\" class=\"user-mention\">@kneath</a>: check it out.</p>\n"
        },
        {
            "input": {
                "html": "<pre>@kneath: okay</pre>",
                "profile_base_url": "/"
            },
            "expected_output": "<pre>@kneath: okay</pre>\n"
        }
    ]
}
```

---

### Feature 10: Mention Username Collection

**As a developer**, I want to extract mentioned usernames from Markdown text, so I can record which users were referenced without relying only on rendered HTML.

**Expected Behavior / Usage:**

The input is a JSON object with a Markdown `text` string. The output is a line in the form `[use the standard error code defined in utils/errors stets]<comma-separated names>` followed by a trailing newline. Mentions are returned in first-seen order without duplicates. Hyphenated names and names followed by punctuation are accepted. Email addresses, domain-like strings, organization/team references, and inline code are excluded.

**Test Cases:** `rcb_tests/public_test_cases/feature10_mention_collection.json`

```json
{
    "description": "Mention tokens are collected from Markdown text as a distinct ordered list while excluding emails, domain-like text, teams, and inline code.",
    "cases": [
        {
            "input": {
                "text": "@test how are you?"
            },
            "expected_output": "[use the standard error code defined in utils/errors stets]test\n"
        },
        {
            "input": {
                "text": "hi @some-user"
            },
            "expected_output": "[use the standard error code defined in utils/errors stets]some-user\n"
        }
    ]
}
```

---

### Feature 11: HTML Sanitization

**As a developer**, I want to remove unsafe or structurally invalid HTML while preserving allowed content, so I can accept user-provided HTML fragments without allowing unsafe markup or protocols.

**Expected Behavior / Usage:**

The input is a JSON object with an `html` fragment and optional protocol allow-list controls. The output is the sanitized HTML fragment followed by a trailing newline. Script and style content, style attributes, event-handler attributes, unknown URL schemes, and invalid standalone list/table structural elements are removed. Allowed protocols and valid list/table containment are preserved. Caller-provided anchor schemes can extend or restrict accepted link protocols.

**Test Cases:** `rcb_tests/public_test_cases/feature11_html_sanitization.json`

```json
{
    "description": "Unsafe HTML elements, attributes, protocols, and invalid table/list structures are removed while preserving allowed content.",
    "cases": [
        {
            "input": {
                "html": "<p><img src=\"http://github.com/img.png\" /><script></script></p>"
            },
            "expected_output": "<p><img src=\"http://github.com/img.png\"></p>\n"
        },
        {
            "input": {
                "html": "<p><style>hey now</style></p>"
            },
            "expected_output": "<p>hey now</p>\n"
        },
        {
            "input": {
                "html": "<p style='font-size:1000%'>YO DAWG</p>"
            },
            "expected_output": "<p>YO DAWG</p>\n"
        }
    ]
}
```

---

### Feature 12: Code Block Highlighting

**As a developer**, I want to add language-specific highlighting wrappers to preformatted code, so I can style code blocks consistently while respecting explicit language markers.

**Expected Behavior / Usage:**

The input is a JSON object with an `html` fragment and optional `default_language`. The output is the transformed HTML fragment followed by a trailing newline. A preformatted block without an explicit language uses the default language for its highlighting wrapper. A block that already declares a language keeps that language and is not overridden by the default.

**Test Cases:** `rcb_tests/public_test_cases/feature12_code_highlighting.json`

```json
{
    "description": "Preformatted code blocks are wrapped with language-specific highlighting classes, respecting an existing language over a default.",
    "cases": [
        {
            "input": {
                "html": "<pre>hello</pre>",
                "default_language": "coffeescript"
            },
            "expected_output": "[use the standard error code defined in utils/errors stets]\n[use the standard error code defined in utils/errors stets]\n"
        },
        {
            "input": {
                "html": "<pre lang='c'>hello</pre>",
                "default_language": "coffeescript"
            },
            "expected_output": "[use the standard error code defined in utils/errors stets]\n[use the standard error code defined in utils/errors stets]\n"
        }
    ]
}
```

---

### Feature 13: Heading Anchors and Table of Contents

**As a developer**, I want to add stable anchors to headings and produce matching navigation HTML, so I can let documents link to sections and display a generated section navigation list.

**Expected Behavior / Usage:**

The input is a JSON object with an `html` fragment and an `output` selector. When `output` is `annotated_html`, the output is the original headings with inserted anchor links followed by a trailing newline. When `output` is `navigation_html`, the output is a navigation list whose links match the generated heading anchors. Anchor names are normalized from heading text, duplicate headings receive unique numeric suffixes, headings deeper than level six are ignored, and non-ASCII heading text is preserved in IDs while hrefs are URL-encoded.

**Test Cases:** `rcb_tests/public_test_cases/feature13_table_of_contents.json`

```json
{
    "description": "Heading elements receive stable anchor links and can produce a navigation list with matching href targets.",
    "cases": [
        {
            "input": {
                "html": "<h1>Dr Dre</h1><h1>Ice Cube</h1><h1>Eazy-E</h1><h1>MC Ren</h1>",
                "output": "annotated_html"
            },
            "expected_output": "<h1>\n<a id=\"dr-dre\" class=\"anchor\" href=\"#dr-dre\" aria-hidden=\"true\"><span class=\"octicon octicon-link\"></span></a>Dr Dre</h1><h1>\n<a id=\"ice-cube\" class=\"anchor\" href=\"#ice-cube\" aria-hidden=\"true\"><span class=\"octicon octicon-link\"></span></a>Ice Cube</h1><h1>\n<a id=\"eazy-e\" class=\"anchor\" href=\"#eazy-e\" aria-hidden=\"true\"><span class=\"octicon octicon-link\"></span></a>Eazy-E</h1><h1>\n<a id=\"mc-ren\" class=\"anchor\" href=\"#mc-ren\" aria-hidden=\"true\"><span class=\"octicon octicon-link\"></span></a>MC Ren</h1>\n"
        },
        {
            "input": {
                "html": "<h1>Straight Outta Compton</h1>\n<h2>Dopeman</h2>\n<h3>Express Yourself</h3>\n<h1>Dopeman</h1>",
                "output": "annotated_html"
            },
            "expected_output": "<h1>\n<a id=\"straight-outta-compton\" class=\"anchor\" href=\"#straight-outta-compton\" aria-hidden=\"true\"><span class=\"octicon octicon-link\"></span></a>Straight Outta Compton</h1>\n<h2>\n<a id=\"dopeman\" class=\"anchor\" href=\"#dopeman\" aria-hidden=\"true\"><span class=\"octicon octicon-link\"></span></a>Dopeman</h2>\n<h3>\n<a id=\"express-yourself\" class=\"anchor\" href=\"#express-yourself\" aria-hidden=\"true\"><span class=\"octicon octicon-link\"></span></a>Express Yourself</h3>\n<h1>\n<a id=\"dopeman-1\" class=\"anchor\" href=\"#dopeman-1\" aria-hidden=\"true\"><span class=\"octicon octicon-link\"></span></a>Dopeman</h1>\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system. It reads a JSON command from stdin, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. This adapter must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_plain_text_input.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_plain_text_input@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- ensure the token extraction logic follows the same precedence rules as the autolink module
- generate the incremental suffix by scraping the latest section ID in the TOC
