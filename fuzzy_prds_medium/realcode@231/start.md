## Product Requirement Document

Hey team, we need a HTML-to-Markdown converter library — basically something devs can call programmatically to transform HTML snippets into clean Markdown text. The output needs to be totally deterministic so we can store it or compare it reliably. Think of it like that sanitizer utility we built for the content pipeline last quarter, but this time it's about converting structure not stripping it.

The main things it needs to handle: headings, paragraphs, emphasis/bold, links (including ones with weird spaces in URLs), images, code blocks with language hints, ordered and unordered lists, tables (just the data rows, not header rows), blockquotes, horizontal rules, and line breaks. There should also be a way to tweak the output style — like different heading formats or rule styles — and a way to just skip certain element types entirely if the caller doesn't want them in the output.

It needs a proper CLI/stdin adapter so our test harness can pipe JSON in and get results back. The test runner script lives under rcb_tests/ and should be a single bash entry point. We want results written to per-case output files so nothing gets overwritten between runs.

The internal structure matters too — don't just throw everything in one file. Keep the conversion logic separate from the I/O stuff. We'll be extending this over time so it needs to be easy to add new element handlers without touching the core.

Let me know if anything's unclear — I'll be honest I'm fuzzy on some of the edge cases around inline code escaping and reference-style links.

Quick follow-up from the questions that came in: for headings, default is still ATX hash-prefix style, but we do support `heading_style: 'setext'`. In that mode, h1 is the title followed by a line of `=` characters matching the title length, and h2 does the same thing with `-` characters. That only applies to h1 and h2 though — anything deeper should fall back to the normal ATX hash-prefix format.

Also on rules and breaks, by default `<hr>` should come out as `* * *`, and if `horizontal_rule: 'dashes'` is set then it should be `- - -`. In block context it should have blank lines on both sides. For `<br>`, default is two trailing spaces followed by a newline (`  \n`), and if `line_break: 'backslash'` is set then it should be a backslash followed by a newline (`\\\n`). If there are consecutive `<br>` elements, each one should emit its own break marker.

A couple formatting details too: the final assembled Markdown string needs all leading and trailing whitespace stripped from the overall result, including newlines. Internal blank lines between block elements should stay as-is, so this trimming is only for the final combined output, not for each individual element as it's converted. And for links, the text content inside an `<a>` gets trimmed before it goes in the square brackets, so `<a href="/"> bla </a>` becomes `[bla](/)`. That trimming is only for the link text itself and shouldn't affect surrounding document text.

For list spacing, unordered list items should default to 3 spaces after the `*` marker, so `*   Item`. That should be configurable with `unordered_list_spacing` as an integer, so for example `unordered_list_spacing: 2` gives `*  Item`. Ordered list items default to 2 spaces after the period, so `1.  Item`.

And just to make the structure expectation a little more explicit: this really does need to be split across multiple files. The core conversion logic — HTML parsing, element handlers, options — should be physically separate from the stdin/stdout JSON adapter. A recommended shape is a `src/` directory for the library plus a separate adapter or CLI entry point. Basically the same clean split we called out in the architecture guidance: no single god file here, and the JSON stdin/stdout adapter should be logically and physically separate from the converter domain logic.