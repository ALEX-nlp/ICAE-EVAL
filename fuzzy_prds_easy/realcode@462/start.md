## Product Requirement Document

# Web Page URL & Content Parsing Toolkit — URL Classification, Redirect Cleanup, and HTML Metadata Extraction

## Project Goal

Build a reusable toolkit of pure, deterministic helpers for cleaning and interpreting web content, so developers can normalize titles, classify and de-clutter URLs, follow link-shim redirects, and pull representative images, links, and icons out of an HTML fragment — without each application re-implementing this fiddly string and DOM handling itself.

---

## Background & Problem

Applications that ingest web pages repeatedly face the same low-level chores: page titles arrive padded with a trailing site-name segment, URLs arrive wrapped in tracking parameters or in service-specific "interstitial" redirect shims, and the single best image or link for a snippet is buried somewhere in a messy DOM subtree. Hand-rolling each of these tasks is repetitive and error-prone, and subtle differences (which separator wins in a title, which query parameter holds the real target, how a size string is parsed) lead to inconsistent results across tools.

This toolkit provides one well-defined behavioral contract for each task: whitespace/title normalization, substring counting, file-extension-based media classification, redirect unwrapping for known link shims, removal of analytics query parameters, parsing of HTML size descriptors, selection of the largest declared icon, and extraction of a representative image or link from a DOM subtree. Every operation is a pure function of its input and produces a stable, inspectable result.

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

Every operation is selected by an `op` field in the JSON request read from stdin. The adapter renders the result to stdout as one or more `key=value` lines, each terminated by a newline. Boolean values render as the lowercase words `true`/`false`. URL values render in their normalized string form (for example, a host-only URL gains a trailing `/` path).

### Feature 1: Text Normalization Utilities

**As a developer**, I want small, reliable string helpers for cleaning page text, so I can normalize titles and whitespace consistently across my application.

**Expected Behavior / Usage:**

*1.1 Collapse Whitespace — normalize runs of whitespace and trim the ends.*

The request carries `op` = `clean_whitespace` and a `text` string. Every maximal run of whitespace characters (spaces, tabs, newlines) inside the text is replaced by a single space, and leading/trailing whitespace is removed. The result is emitted as `[clean_whitespace]<normalized text>`. An all-whitespace input yields an empty result string.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_collapse_whitespace.json`

```json
{
    "description": "Collapse every run of whitespace (spaces, tabs, newlines) inside a string down to a single space and strip leading and trailing whitespace, returning the normalized text.",
    "cases": [
        {"input": {"op": "clean_whitespace", "text": "t    \nt "}, "expected_output": "[clean_whitespace]t t\n"},
        {"input": {"op": "clean_whitespace", "text": "t  peter "}, "expected_output": "[clean_whitespace]t peter\n"}
    ]
}
```

*1.2 Count Substring Occurrences — count non-overlapping matches.*

The request carries `op` = `count_matches`, a `text` string, and a `substring` string. The output is `count=<n>`, where `n` is the number of non-overlapping occurrences of the substring within the text.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_count_substring.json`

```json
{
    "description": "Count how many non-overlapping times a substring occurs within a string.",
    "cases": [
        {"input": {"op": "count_matches", "text": "hi wie &test; gehts", "substring": "&test;"}, "expected_output": "count=1\n"},
        {"input": {"op": "count_matches", "text": "&test; test; &test; plu &test;", "substring": "&test;"}, "expected_output": "count=3\n"}
    ]
}
```

*1.3 Clean Title — strip a trailing site-name segment.*

The request carries `op` = `clean_title` and a `title` string. Titles frequently end with a separator followed by the site name (for example `Article Headline | Site Name`). If a pipe character (`|`) occurs in the right half of the string (its last position is past the midpoint of the string's length), keep only the text before the FIRST pipe, trimmed of surrounding whitespace. Otherwise (no pipe, or the pipe sits in the left half), leave the title as-is apart from collapsing internal whitespace. The output is `title=<cleaned title>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_clean_title.json`

```json
{
    "description": "Clean a raw page title by removing a trailing site-name segment. When a pipe separator appears in the right half of the string, keep only the text before the first pipe (trimmed); otherwise just normalize internal whitespace and leave the title intact.",
    "cases": [
        {"input": {"op": "clean_title", "title": "mytitle irgendwas | Facebook"}, "expected_output": "title=mytitle irgendwas\n"},
        {"input": {"op": "clean_title", "title": "Irgendwas | mytitle irgendwas"}, "expected_output": "title=Irgendwas | mytitle irgendwas\n"}
    ]
}
```

---

### Feature 2: URL Media-Type Classification

**As a developer**, I want to classify a URL by the file extension of its path, so I can guess whether it points at a downloadable media file or at a readable article.

**Expected Behavior / Usage:**

The request carries `op` = `classify_url` and a `url` string. Classification looks only at the lowercased file extension of the URL's path (the text after the final `.` in the last path segment). The adapter emits seven boolean lines, in this exact order: `video`, `image`, `audio`, `binary_document`, `archive`, `executable`, and finally `article`. Each of the first six is `true` when the extension belongs to that media category's known extension set, else `false`. The `article` line is `true` only when the URL belongs to NONE of those six downloadable-media categories (i.e. it is likely a readable page), else `false`. Common readable URLs (no extension, or a non-media extension such as `.txt`/`.tmp`/`.log`) classify as `article=true`; a `.mp4` URL classifies as `video=true` and `article=false`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_classify_url.json`

```json
{
    "description": "Classify a URL purely by the file extension of its path into media categories. Emit one boolean line per category (video, image, audio, binary_document, archive, executable) plus a final 'article' flag that is true only when the URL matches none of the downloadable-media categories.",
    "cases": [
        {"input": {"op": "classify_url", "url": "http://example.com/video.mp4"}, "expected_output": "video=true\nimage=false\naudio=false\nbinary_document=false\narchive=false\nexecutable=false\narticle=false\n"},
        {"input": {"op": "classify_url", "url": "http://example.com/test.txt"}, "expected_output": "video=false\nimage=false\naudio=false\nbinary_document=false\narchive=false\nexecutable=false\narticle=true\n"}
    ]
}
```

---

### Feature 3: URL Redirect Resolution & Query Cleanup

**As a developer**, I want to unwrap service link-shims and drop tracking parameters, so the URLs I store and display point directly at the real destination and are free of analytics clutter.

**Expected Behavior / Usage:**

*3.1 Facebook Link-Shim Unwrapping — follow a Facebook interstitial to its target.*

The request carries `op` = `rewrite_facebook` and a `url` string. A Facebook link shim is a URL whose host ends with `.facebook.com` and whose path is `/l.php`; the real destination is carried URL-encoded in the `u` query parameter. When the input is such a shim, replace it with the wrapped target, repeating while the result is still a Facebook shim. A URL that is not a Facebook shim is returned unchanged (only normalized by URL parsing). Output: `[resolves all known redirects]<resolved url>`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_facebook_rewriter.json`

```json
{
    "description": "Unwrap a Facebook link-shim URL: when the host ends with .facebook.com and the path is the link interstitial, follow the wrapped target carried in the query, repeating until the result is no longer a Facebook shim. URLs that are not Facebook shims are returned unchanged.",
    "cases": [
        {"input": {"op": "rewrite_facebook", "url": "http://example.com"}, "expected_output": "[resolves all known redirects]http://example.com/\n"},
        {"input": {"op": "rewrite_facebook", "url": "http://www.facebook.com/l.php?u=http%3A%2F%2Fwww.bet.com%2Fcollegemarketingreps&h=42263"}, "expected_output": "[resolves all known redirects]http://www.bet.com/collegemarketingreps\n"}
    ]
}
```

*3.2 Google Redirect Unwrapping — follow a Google redirect to its target.*

The request carries `op` = `rewrite_google` and a `url` string. A Google redirect is a URL whose host ends with `.google.com` and whose path is `/url`; the real destination is carried in the `q` query parameter, falling back to a `url` query parameter when `q` is absent. When the input is such a redirect, replace it with the wrapped target, repeating while the result is still a Google redirect (which correctly handles nested/double-wrapped redirects). A URL that is not a Google redirect is returned unchanged. Output: `[resolves all known redirects]<resolved url>`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_google_rewriter.json`

```json
{
    "description": "Unwrap a Google link-redirect URL: when the host ends with .google.com and the path is the redirect endpoint, follow the wrapped target carried in the 'q' query parameter (falling back to 'url'), repeating until the result is no longer a Google redirect. URLs that are not Google redirects are returned unchanged.",
    "cases": [
        {"input": {"op": "rewrite_google", "url": "http://example.com/"}, "expected_output": "[resolves all known redirects]http://example.com/\n"},
        {"input": {"op": "rewrite_google", "url": "https://plus.url.google.com/url?q=https://arstechnica.com/business/2017/01/before-the-760mph-hyperloop-dream-there-was-the-atmospheric-railway/&rct=j&ust=1485739059621000&usg=AFQjCNH6Cgp4iU0NB5OoDpT3OtOXds7HQg"}, "expected_output": "[resolves all known redirects]https://arstechnica.com/business/2017/01/before-the-760mph-hyperloop-dream-there-was-the-atmospheric-railway/\n"}
    ]
}
```

*3.3 Combined Redirect Resolution — apply all known redirectors until stable.*

The request carries `op` = `resolve_redirects` and a `url` string. This applies every known redirect provider (the Facebook and Google shims described above) in turn, re-applying the whole set repeatedly until the URL stops changing, then returns the final destination. A URL matching no provider is returned unchanged (only normalized by URL parsing). Output: `[resolves all known redirects]<resolved url>`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_resolve_redirects.json`

```json
{
    "description": "Resolve a URL through all known interstitial/redirect providers (Facebook link shims and Google redirect endpoints) repeatedly until the URL stops changing, returning the final destination. A URL that matches no provider is returned unchanged (only normalized by the URL parser).",
    "cases": [
        {"input": {"op": "resolve_redirects", "url": "http://example.com"}, "expected_output": "[resolves all known redirects]http://example.com/\n"},
        {"input": {"op": "resolve_redirects", "url": "http://www.facebook.com/l.php?u=http%3A%2F%2Fwww.bet.com%2Fcollegemarketingreps&h=42263"}, "expected_output": "[resolves all known redirects]http://www.bet.com/collegemarketingreps\n"}
    ]
}
```

*3.4 Tracking Parameter Removal — drop analytics query parameters.*

The request carries `op` = `remove_tracking` and a `url` string. Any query parameter whose name is in the known set of analytics/tracking tags (the `utm_*` family and related campaign tags such as `ga_*`, `fb_*`, `yclid`, `_openstat`, `gs_l`, etc.) is removed; all other query parameters and the rest of the URL are preserved. A URL with no tracking parameters is returned unchanged (only normalized by URL parsing). Output: `[resolves all known redirects]<cleaned url>`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_remove_tracking.json`

```json
{
    "description": "Strip known analytics/tracking query parameters (e.g. utm_* and similar campaign tags) from a URL while preserving all other query parameters and the rest of the URL. URLs with no tracking parameters are returned unchanged (only normalized by the URL parser).",
    "cases": [
        {"input": {"op": "remove_tracking", "url": "https://example.org?utm_source"}, "expected_output": "[resolves all known redirects]https://example.org/\n"},
        {"input": {"op": "remove_tracking", "url": "https://www.example.com/?utm_source=tracker&non-tracking-parameter=dont-remove"}, "expected_output": "[resolves all known redirects]https://www.example.com/?non-tracking-parameter=dont-remove\n"}
    ]
}
```

---

### Feature 4: HTML Icon & Size Metadata

**As a developer**, I want to interpret size descriptors and choose the best icon declared in a page, so I can pick a high-resolution favicon without guesswork.

**Expected Behavior / Usage:**

*4.1 Parse Size Descriptor — find the largest dimension in a size string.*

The request carries `op` = `parse_size` and a `sizes` value that is either a string or null. A size descriptor is a `WxH` pair using a case-insensitive `x` separator (for example `128x128`). For a single pair, the larger of the two numbers is returned. A descriptor may contain several space-separated pairs, in which case the largest dimension found across all of them is returned. Empty, null, or unparseable input (no valid `WxH` pair) yields `0`. Output: `size=<n>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_parse_size.json`

```json
{
    "description": "Parse an HTML size descriptor string and return the single largest dimension it contains. A descriptor is a 'WxH' pair (case-insensitive 'x'); multiple space-separated pairs are all considered and the largest dimension across them wins. Unparseable or empty input yields 0.",
    "cases": [
        {"input": {"op": "parse_size", "sizes": null}, "expected_output": "size=0\n"},
        {"input": {"op": "parse_size", "sizes": "128x128"}, "expected_output": "size=128\n"},
        {"input": {"op": "parse_size", "sizes": "16x16 24x24 32x32 48x48"}, "expected_output": "size=48\n"}
    ]
}
```

*4.2 Select Largest Icon — pick the highest-resolution declared icon.*

The request carries `op` = `find_largest_icon`, an `html` fragment, and a `base_url` against which relative references are resolved. Among the icon link elements in the fragment (each optionally carrying a `sizes` attribute parsed as in 4.1), select the one whose declared size has the largest dimension and return its absolute URL. Output: `[resolves all known redirects]<absolute icon url>`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_largest_icon.json`

```json
{
    "description": "Given an HTML fragment (parsed against a base URL) containing icon link elements with optional 'sizes' attributes, select the icon whose declared size has the largest dimension and return its absolute URL.",
    "cases": [
        {"input": {"op": "find_largest_icon", "html": "<link rel=\"icon\" sizes=\"57x57\"   href=\"/57.png\">\n<link rel=\"icon\" sizes=\"72x72\"   href=\"/72.png\">\n<link rel=\"icon\" sizes=\"114x114\" href=\"/114.png\">\n<link rel=\"icon\" sizes=\"144x144\" href=\"/144.png\">\n<link rel=\"icon\"                 href=\"/no-size.png\">", "base_url": "https://example.org/"}, "expected_output": "[resolves all known redirects]https://example.org/144.png\n"},
        {"input": {"op": "find_largest_icon", "html": "<link rel=\"apple-touch-icon-precomposed\" sizes=\"512x512\" href=\"/512.png\">\n<link rel=\"apple-touch-icon\"             sizes=\"57x57\"   href=\"/57.png\">\n<link rel=\"icon\"                         sizes=\"72x72\"   href=\"/72.png\">\n<link rel=\"icon\"                         sizes=\"114x114\" href=\"/114.png\">\n<link rel=\"apple-touch-icon\"             sizes=\"144x144\" href=\"/144.png\">", "base_url": "https://example.org/"}, "expected_output": "[resolves all known redirects]https://example.org/512.png\n"}
    ]
}
```

---

### Feature 5: DOM Subtree Image & Link Extraction

**As a developer**, I want to pick the single best image and link out of an HTML subtree, so I can build a snippet/preview without writing custom CSS selectors per site.

**Expected Behavior / Usage:**

*5.1 Extract Representative Image — choose the best image reference in a subtree.*

The request carries `op` = `extract_image`, an `html` fragment, and a `base_url`. The extractor inspects the subtree and returns the first viable image reference, trying in priority order: a `src` then a `data-src` attribute on the root element; then `src`/`data-src` on descendant `<img>` elements; then `src`/`data-src` on any descendant element; then a CSS background image declared via a `url(...)` in a `style` attribute (preferring elements with `role=img`, then any element). The chosen reference is resolved against the base URL into an absolute URL. Output: `image_[resolves all known redirects]<absolute url>` (empty after `=` if no image is found).

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_extract_image.json`

```json
{
    "description": "Given an HTML fragment and a base URL, pick the single best representative image URL from the DOM subtree. The search prefers a src/data-src on the root, then on descendant <img> elements, then any element with src/data-src, then a CSS background-image declared in a style attribute. The chosen reference is resolved against the base URL to an absolute URL.",
    "cases": [
        {"input": {"op": "extract_image", "html": "<html>\n<a href=\"/test-url\">\n  <img class=\"header-photo\" src=\"//hermit.chimbori.com/static/media/test.jpg\">\n  <div class=\"header-name\">Hermit</div>\n</a>\n</html>", "base_url": "https://hermit.chimbori.com"}, "expected_output": "image_[resolves all known redirects]https://hermit.chimbori.com/static/media/test.jpg\n"},
        {"input": {"op": "extract_image", "html": "<html>\n<a class=\"test-case\" href=\"/test\">\n  <img style=\"background: url('//hermit.chimbori.com/static/media/test.jpg');\">\n</a>\n</html>", "base_url": "https://hermit.chimbori.com"}, "expected_output": "image_[resolves all known redirects]https://hermit.chimbori.com/static/media/test.jpg\n"}
    ]
}
```

*5.2 Extract Representative Link — choose the best link reference in a subtree.*

The request carries `op` = `extract_link`, an `html` fragment, and a `base_url`. The extractor returns the first viable link reference, trying in priority order: an `href` on the root element; then an `href` on any descendant element. The chosen reference is resolved against the base URL into an absolute URL. Output: `link_[resolves all known redirects]<absolute url>` (empty after `=` if no link is found).

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_extract_link.json`

```json
{
    "description": "Given an HTML fragment and a base URL, pick the single best representative link URL from the DOM subtree. The search prefers an href on the root element, then any descendant element carrying an href. The chosen reference is resolved against the base URL to an absolute URL.",
    "cases": [
        {"input": {"op": "extract_link", "html": "<html>\n<a href=\"/test-url\">\n  <img class=\"header-photo\" src=\"//hermit.chimbori.com/static/media/test.jpg\">\n  <div class=\"header-name\">Hermit</div>\n</a>\n</html>", "base_url": "https://hermit.chimbori.com"}, "expected_output": "link_[resolves all known redirects]https://hermit.chimbori.com/test-url\n"},
        {"input": {"op": "extract_link", "html": "<html>\n<a class=\"test-case\" href=\"/test\">\n  <img style=\"background: url('//hermit.chimbori.com/static/media/test.jpg');\">\n</a>\n</html>", "base_url": "https://hermit.chimbori.com"}, "expected_output": "link_[resolves all known redirects]https://hermit.chimbori.com/test\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin, selects the operation via the `op` field, invokes the appropriate core logic, and prints the resulting `key=value` line(s) to stdout, matching the per-feature contracts above. URL values are rendered in their normalized string form; booleans render as `true`/`false`.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- collapsing internal whitespace logic as defined in C003 for clean_title
