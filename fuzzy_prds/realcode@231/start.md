## Product Requirement Document

Hey team, we need a HTML-to-Markdown converter library — basically something devs can call programmatically to transform HTML snippets into clean Markdown text. The output needs to be totally deterministic so we can store it or compare it reliably. Think of it like that sanitizer utility we built for the content pipeline last quarter, but this time it's about converting structure not stripping it.

The main things it needs to handle: headings, paragraphs, emphasis/bold, links (including ones with weird spaces in URLs), images, code blocks with language hints, ordered and unordered lists, tables (just the data rows, not header rows), blockquotes, horizontal rules, and line breaks. There should also be a way to tweak the output style — like different heading formats or rule styles — and a way to just skip certain element types entirely if the caller doesn't want them in the output.

It needs a proper CLI/stdin adapter so our test harness can pipe JSON in and get results back. The test runner script lives under rcb_tests/ and should be a single bash entry point. We want results written to per-case output files so nothing gets overwritten between runs.

The internal structure matters too — don't just throw everything in one file. Keep the conversion logic separate from the I/O stuff. We'll be extending this over time so it needs to be easy to add new element handlers without touching the core.

Let me know if anything's unclear — I'll be honest I'm fuzzy on some of the edge cases around inline code escaping and reference-style links.