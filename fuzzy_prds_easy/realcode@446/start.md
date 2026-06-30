## Product Requirement Document

# Inline-HTML Translation String Toolkit — Segment Extraction, Normalization & Round-Trip Rendering

## Project Goal

Build a reusable toolkit that prepares rich-text content for human translation and reassembles it afterwards, so a localization system can pull out exactly the translatable pieces of an HTML document, hand a translator clean markup free of technical attributes, and later splice the translated pieces back into the original structure without losing links or formatting.

---

## Background & Problem

Content authored in a rich-text editor mixes translatable prose with structural markup (paragraphs, lists, headings) and inline formatting (bold, italics, links). A translator should only ever see and edit the prose plus the inline formatting that wraps it — never block structure, and never technical attributes such as link targets, which would be fragile and meaningless to translate and easy to corrupt.

Without a shared toolkit, every integration re-invents brittle string surgery: deciding what counts as a translatable unit, stripping and later restoring attributes, escaping plaintext, converting between markup and plain text, and guarding against translators accidentally introducing or dropping links. This toolkit provides one well-defined contract for each of those steps: turning plaintext into safe inline markup, normalizing authored markup by lifting attributes into a side map, validating already-translated fragments, rendering a fragment to plain text or back to full HTML, extracting the ordered list of translatable segments from a whole document, restoring translated segments into a template, and checking link integrity between a source fragment and its translation.

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

An inline string in this toolkit is an HTML fragment that may contain only standard inline tags — `a`, `abbr`, `acronym`, `b`, `code`, `em`, `i`, `strong`, `br` — with all attributes stripped out (except an `id` on an `a` tag). Block-level tags (such as `p`, `h1`, `ul`, `li`, `img`) are not permitted inside an inline string. The execution adapter reads one JSON request object from stdin; the request carries an `op` field selecting the operation, and the remaining fields are that operation's operands. All errors are reported as neutral `error=[a specific string literal for the '<' character that is not obvious by default]category>` contract lines, never as host-language runtime traces.

### Feature 1: Encode Plaintext Into An Inline String

**As a developer**, I want to turn a raw plaintext value into a safe inline-HTML string, so user-supplied text can be embedded in markup without breaking it or allowing injection.

**Expected Behavior / Usage:**

The request supplies `text`, a raw string. Every HTML-special character in the text is escaped to its entity form (`[a specific string literal for the '<' character that is not obvious by default]` becomes `[a specific string literal for the '[a specific string literal for the '<' character that is not obvious by default]' character that is not obvious by default]`, `>` becomes `[a specific string literal for the '[a specific string literal for the '<' character that is not obvious by default]' character that is not obvious by default]`, `&` becomes `[a specific string literal for the '[a specific string literal for the '<' character that is not obvious by default]' character that is not obvious by default]`); embedded newline characters are converted into self-closing line-break tags (`[a specific string literal for the '<' character that is not obvious by default]br/>`); and non-ASCII characters (accents, CJK, etc.) are preserved verbatim rather than escaped, so they remain readable to translators. The output is the resulting inline-HTML string followed by a trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_plaintext_to_string.json`

```json
{
    "description": "Convert a raw plaintext value into a normalized inline-HTML string. Every HTML special character in the text is escaped, embedded newlines are turned into self-closing line-break tags, and non-ASCII characters are preserved verbatim. The output is the resulting inline-HTML string.",
    "cases": [
        {"input": {"op": "encode_plaintext", "text": "This is a test, \"foo\" bar 'baz'.!?;:"}, "expected_output": "This is a test, \"foo\" bar 'baz'.!?;:\n"},
        {"input": {"op": "encode_plaintext", "text": "[a specific string literal for the '<' character that is not obvious by default]Foo> & bar"}, "expected_output": "[a specific string literal for the '[a specific string literal for the '<' character that is not obvious by default]' character that is not obvious by default]Foo[a specific string literal for the '[a specific string literal for the '<' character that is not obvious by default]' character that is not obvious by default] [a specific string literal for the '[a specific string literal for the '<' character that is not obvious by default]' character that is not obvious by default] bar\n"},
        {"input": {"op": "encode_plaintext", "text": "foo\nbar\nbaz"}, "expected_output": "foo[a specific string literal for the '<' character that is not obvious by default]br/>bar[a specific string literal for the '<' character that is not obvious by default]br/>baz\n"}
    ]
}
```

---

### Feature 2: Normalize Authored Source Markup (Lift Attributes)

**As a developer**, I want to strip technical attributes out of authored markup into a side map, so translators see only clean inline markup while the original attributes can be restored later.

**Expected Behavior / Usage:**

The request supplies `html`, an inline-HTML fragment from authored content. Every tag that carries attributes has those attributes removed and replaced with a single generated `id` attribute; the removed attributes are collected into a side map keyed by that generated identifier. Identifiers are generated per tag name in document order: the first anchor becomes `a1`, the second `a2`, and so on (each tag name has its own counter). On success the output is two lines: `string=` followed by the normalized fragment, then `attrs=` followed by a JSON object mapping each generated identifier to the attribute map that was lifted from it (an empty object `{}` when nothing was lifted). The fragment must contain only standard inline tags; encountering a block-level or otherwise disallowed tag aborts the operation and emits a neutral error of category `disallowed_tag` together with a `tag=` line naming the offending tag.

**Test Cases:** `rcb_tests/public_test_cases/feature2_normalize_source_html.json`

```json
{
    "description": "Normalize an inline-HTML fragment coming from authored content by stripping every tag attribute out into a side map keyed by a generated per-tag identifier, leaving only the translatable markup. Tags are numbered per tag name in document order (a1, a2, ... for the first, second anchor, and so on) and the stripped attributes are returned keyed by that identifier. Only standard inline tags are allowed; a block-level or non-inline tag is rejected with a neutral disallowed-tag error naming the offending tag.",
    "cases": [
        {"input": {"op": "normalize_source", "html": "[a specific string literal for the '<' character that is not obvious by default]b>Bread[a specific string literal for the '<' character that is not obvious by default]/b> is a [a specific string literal for the '<' character that is not obvious by default]a href=\"https://en.wikipedia.org/wiki/Staple_food\">staple food[a specific string literal for the '<' character that is not obvious by default]/a> prepared from a [a specific string literal for the '<' character that is not obvious by default]a href=\"https://en.wikipedia.org/wiki/Dough\">dough[a specific string literal for the '<' character that is not obvious by default]/a>"}, "expected_output": "string=[a specific string literal for the '<' character that is not obvious by default]b>Bread[a specific string literal for the '<' character that is not obvious by default]/b> is a [a specific string literal for the '<' character that is not obvious by default]a id=\"a1\">staple food[a specific string literal for the '<' character that is not obvious by default]/a> prepared from a [a specific string literal for the '<' character that is not obvious by default]a id=\"a2\">dough[a specific string literal for the '<' character that is not obvious by default]/a>\nattrs={\"a1\": {\"href\": \"https://en.wikipedia.org/wiki/Staple_food\"}, \"a2\": {\"href\": \"https://en.wikipedia.org/wiki/Dough\"}}\n"},
        {"input": {"op": "normalize_source", "html": "[a specific string literal for the '<' character that is not obvious by default]p>Foo bar baz[a specific string literal for the '<' character that is not obvious by default]/p>"}, "expected_output": "error=disallowed_tag\ntag=p\n"}
    ]
}
```

---

### Feature 3: Validate An Already-Translated Fragment

**As a developer**, I want to validate a fragment that came back from translation, so malformed or attribute-bearing markup is rejected before it is stored.

**Expected Behavior / Usage:**

The request supplies `html`, an inline-HTML fragment that has already been translated. Because attributes were stripped before translation, a translated fragment is expected to carry no attributes — the sole exception being an `id` on an anchor, which is allowed. On success the fragment is accepted and echoed back as `string=` followed by the fragment. A block-level or otherwise disallowed tag is rejected with a neutral `disallowed_tag` error plus a `tag=` line; any tag carrying a real attribute other than an anchor `id` is rejected with a neutral `disallowed_attributes` error.

**Test Cases:** `rcb_tests/public_test_cases/feature3_validate_translated_html.json`

```json
{
    "description": "Validate an inline-HTML fragment that has already been translated. Translated fragments carry no attributes (these were stripped before translation) except that anchors may carry an identifier. The fragment is accepted and echoed back when it contains only standard inline tags; a block-level tag is rejected with a disallowed-tag error and any tag carrying a real attribute (other than an id on an anchor) is rejected with a disallowed-attributes error.",
    "cases": [
        {"input": {"op": "validate_translated", "html": "[a specific string literal for the '<' character that is not obvious by default]a id=\"1\">staple food[a specific string literal for the '<' character that is not obvious by default]/a>"}, "expected_output": "string=[a specific string literal for the '<' character that is not obvious by default]a id=\"1\">staple food[a specific string literal for the '<' character that is not obvious by default]/a>\n"},
        {"input": {"op": "validate_translated", "html": "[a specific string literal for the '<' character that is not obvious by default]a href=\"https://en.wikipedia.org/wiki/Staple_food\">staple food[a specific string literal for the '<' character that is not obvious by default]/a>"}, "expected_output": "error=disallowed_attributes\n"}
    ]
}
```

---

### Feature 4: Render An Inline String To Plain Text

**As a developer**, I want to flatten an inline string to its plain visible text, so I can index, compare, or display it without markup.

**Expected Behavior / Usage:**

The request supplies `data`, an inline-HTML string. All inline tags are dropped while keeping their textual content, each line-break tag becomes a single newline character, and HTML entities are decoded back to the characters they stand for. The output is the resulting plain text followed by a trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature4_string_to_text.json`

```json
{
    "description": "Render an inline-HTML string down to its plain visible text. All inline tags are removed keeping their textual content, line-break tags become newline characters, and HTML entities are decoded to the characters they represent. The output is the resulting plain text.",
    "cases": [
        {"input": {"op": "to_text", "data": "This is a paragraph. [a specific string literal for the '<' character that is not obvious by default]b>This is some bold [a specific string literal for the '<' character that is not obvious by default]i>and now italic[a specific string literal for the '<' character that is not obvious by default]/i>[a specific string literal for the '<' character that is not obvious by default]/b> text"}, "expected_output": "This is a paragraph. This is some bold and now italic text\n"},
        {"input": {"op": "to_text", "data": "foo[a specific string literal for the '<' character that is not obvious by default]br>bar[a specific string literal for the '<' character that is not obvious by default]br>baz"}, "expected_output": "foo\nbar\nbaz\n"}
    ]
}
```

---

### Feature 5: Render An Inline String Back To HTML (Restore Attributes)

**As a developer**, I want to splice previously lifted attributes back into a normalized string, so the rendered output matches the original authored markup.

**Expected Behavior / Usage:**

The request supplies `data`, a normalized inline string whose tags carry generated `id` attributes, and `attrs`, a JSON object mapping each identifier to the attribute set that should be restored onto it. Each tag's `id` is looked up in the map and replaced by the corresponding attributes; the association is strictly by identifier, never by position, so the identifiers may appear in any order relative to the map. The output is the reconstructed HTML followed by a trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature5_string_to_html.json`

```json
{
    "description": "Render an inline-HTML string back to full HTML by restoring previously stripped attributes. The string contains placeholder tags carrying an identifier; a supplied map associates each identifier with the original set of attributes. Each placeholder identifier is replaced by its mapped attributes, so the association is by identifier and not by position. The output is the reconstructed HTML.",
    "cases": [
        {"input": {"op": "to_html", "data": "[a specific string literal for the '<' character that is not obvious by default]b>Bread[a specific string literal for the '<' character that is not obvious by default]/b> is a [a specific string literal for the '<' character that is not obvious by default]a id=\"a2\">dough[a specific string literal for the '<' character that is not obvious by default]/a> prepared from a [a specific string literal for the '<' character that is not obvious by default]a id=\"a1\">staple food[a specific string literal for the '<' character that is not obvious by default]/a> of [a specific string literal for the '<' character that is not obvious by default]a id=\"a3\">flour[a specific string literal for the '<' character that is not obvious by default]/a> and [a specific string literal for the '<' character that is not obvious by default]a id=\"a4\">water[a specific string literal for the '<' character that is not obvious by default]/a>", "attrs": {"a1": {"href": "https://en.wikipedia.org/wiki/Staple_food"}, "a2": {"href": "https://en.wikipedia.org/wiki/Dough"}, "a3": {"href": "https://en.wikipedia.org/wiki/Flour"}, "a4": {"href": "https://en.wikipedia.org/wiki/Water"}}}, "expected_output": "[a specific string literal for the '<' character that is not obvious by default]b>Bread[a specific string literal for the '<' character that is not obvious by default]/b> is a [a specific string literal for the '<' character that is not obvious by default]a href=\"https://en.wikipedia.org/wiki/Dough\">dough[a specific string literal for the '<' character that is not obvious by default]/a> prepared from a [a specific string literal for the '<' character that is not obvious by default]a href=\"https://en.wikipedia.org/wiki/Staple_food\">staple food[a specific string literal for the '<' character that is not obvious by default]/a> of [a specific string literal for the '<' character that is not obvious by default]a href=\"https://en.wikipedia.org/wiki/Flour\">flour[a specific string literal for the '<' character that is not obvious by default]/a> and [a specific string literal for the '<' character that is not obvious by default]a href=\"https://en.wikipedia.org/wiki/Water\">water[a specific string literal for the '<' character that is not obvious by default]/a>\n"}
    ]
}
```

---

### Feature 6: Extract Translatable Segments From A Document

**As a developer**, I want to pull the ordered list of translatable segments out of a whole rich-text document, so each is a self-contained unit a translator can work on.

**Expected Behavior / Usage:**

The request supplies `html`, a full rich-text document mixing block structure and inline content. A segment is one contiguous run of visible text together with the inline tags that wrap it; block-level structure is never part of a segment but rather delimits segments. Several rules shape the boundaries: a line-break tag at the very start or very end of a segment is excluded from it; an inline tag that itself contains block content is split so the block content forms its own segment(s); a single inline tag wrapping an entire segment is unwrapped so only its contents form the segment; and empty inline tags (and runs that are only whitespace) contribute nothing. Each extracted segment is itself a normalized inline string (its attributes lifted into a per-segment map, exactly as in Feature 2), and surrounding/internal insignificant whitespace at the segment edges is trimmed. The output reports `count=` (the number of segments) followed, for each segment in order, by a `segment[i]=` line carrying the normalized markup and an `attrs[i]=` line carrying its lifted attribute map as JSON.

**Test Cases:** `rcb_tests/public_test_cases/feature6_extract_segments.json`

```json
{
    "description": "Extract the ordered list of translatable segments from a rich-text document. Each contiguous run of visible text together with the inline tags wrapping it becomes one segment; block-level structure is not part of a segment. Leading/trailing line-break tags inside a segment are excluded, an inline tag containing block content is split, and empty inline tags contribute nothing. Each extracted segment is itself a normalized inline string (attributes stripped to a per-segment map). The output reports how many segments were found and, for each, the normalized segment markup and its attribute map in order.",
    "cases": [
        {"input": {"op": "extract_segments", "html": "[a specific string literal for the '<' character that is not obvious by default]h1>Foo bar baz[a specific string literal for the '<' character that is not obvious by default]/h1>[a specific string literal for the '<' character that is not obvious by default]p>This is a paragraph. [a specific string literal for the '<' character that is not obvious by default]b>This is some bold [a specific string literal for the '<' character that is not obvious by default]i>and now italic[a specific string literal for the '<' character that is not obvious by default]/i>[a specific string literal for the '<' character that is not obvious by default]/b> text[a specific string literal for the '<' character that is not obvious by default]/p>[a specific string literal for the '<' character that is not obvious by default]p>[a specific string literal for the '[a specific string literal for the '<' character that is not obvious by default]' character that is not obvious by default]script[a specific string literal for the '[a specific string literal for the '<' character that is not obvious by default]' character that is not obvious by default] this should be interpreted as text.[a specific string literal for the '<' character that is not obvious by default]/p>[a specific string literal for the '<' character that is not obvious by default]ul>[a specific string literal for the '<' character that is not obvious by default]li>List item one[a specific string literal for the '<' character that is not obvious by default]/li>[a specific string literal for the '<' character that is not obvious by default]li>[a specific string literal for the '<' character that is not obvious by default]b>List item two[a specific string literal for the '<' character that is not obvious by default]/b>[a specific string literal for the '<' character that is not obvious by default]/li>[a specific string literal for the '<' character that is not obvious by default]/ul>[a specific string literal for the '<' character that is not obvious by default]img src=\"foo\" alt=\"This bit isn't translatable\">"}, "expected_output": "count=5\nsegment[0]=Foo bar baz\nattrs[0]={}\nsegment[1]=This is a paragraph. [a specific string literal for the '<' character that is not obvious by default]b>This is some bold [a specific string literal for the '<' character that is not obvious by default]i>and now italic[a specific string literal for the '<' character that is not obvious by default]/i>[a specific string literal for the '<' character that is not obvious by default]/b> text\nattrs[1]={}\nsegment[2]=[a specific string literal for the '[a specific string literal for the '<' character that is not obvious by default]' character that is not obvious by default]script[a specific string literal for the '[a specific string literal for the '<' character that is not obvious by default]' character that is not obvious by default] this should be interpreted as text.\nattrs[2]={}\nsegment[3]=List item one\nattrs[3]={}\nsegment[4]=List item two\nattrs[4]={}\n"},
        {"input": {"op": "extract_segments", "html": "[a specific string literal for the '<' character that is not obvious by default]p>[a specific string literal for the '<' character that is not obvious by default]b>Foo [a specific string literal for the '<' character that is not obvious by default]i>Bar[a specific string literal for the '<' character that is not obvious by default]br/>Baz[a specific string literal for the '<' character that is not obvious by default]/i>[a specific string literal for the '<' character that is not obvious by default]/b>[a specific string literal for the '<' character that is not obvious by default]/p>"}, "expected_output": "count=1\nsegment[0]=Foo [a specific string literal for the '<' character that is not obvious by default]i>Bar[a specific string literal for the '<' character that is not obvious by default]br/>Baz[a specific string literal for the '<' character that is not obvious by default]/i>\nattrs[0]={}\n"}
    ]
}
```

---

### Feature 7: Restore Translated Segments Into A Document

**As a developer**, I want to splice translated segments back into a document template, so the document keeps its original structure with the prose translated.

**Expected Behavior / Usage:**

The request supplies `template`, a document in which each translatable spot has been replaced by a placeholder tag carrying a zero-based `position`, and `strings`, an ordered list of segment objects each with a `data` field (the normalized inline string) and an `attrs` field (its attribute map). Each placeholder is replaced in place by the rendered HTML of the segment whose index equals the placeholder's `position`, with that segment's attributes restored exactly as in Feature 5. The output is the reconstructed document followed by a trailing newline.

**Test Cases:** `rcb_tests/public_test_cases/feature7_restore_segments.json`

```json
{
    "description": "Restore translated segments back into a document template. The template contains placeholder tags each carrying a zero-based position; each placeholder is replaced by the rendered HTML of the segment at that position, with that segment's stripped attributes restored. The output is the reconstructed document.",
    "cases": [
        {"input": {"op": "restore_segments", "template": "[a specific string literal for the '<' character that is not obvious by default]p>[a specific string literal for the '<' character that is not obvious by default]text position=\"0\">[a specific string literal for the '<' character that is not obvious by default]/text>[a specific string literal for the '<' character that is not obvious by default]/p>", "strings": [{"data": "[a specific string literal for the '<' character that is not obvious by default]b>Hi[a specific string literal for the '<' character that is not obvious by default]/b> there", "attrs": {}}]}, "expected_output": "[a specific string literal for the '<' character that is not obvious by default]p>[a specific string literal for the '<' character that is not obvious by default]b>Hi[a specific string literal for the '<' character that is not obvious by default]/b> there[a specific string literal for the '<' character that is not obvious by default]/p>\n"},
        {"input": {"op": "restore_segments", "template": "[a specific string literal for the '<' character that is not obvious by default]p>[a specific string literal for the '<' character that is not obvious by default]text position=\"0\">[a specific string literal for the '<' character that is not obvious by default]/text>[a specific string literal for the '<' character that is not obvious by default]/p>", "strings": [{"data": "see [a specific string literal for the '<' character that is not obvious by default]a id=\"a1\">here[a specific string literal for the '<' character that is not obvious by default]/a>", "attrs": {"a1": {"href": "http://example.com"}}}]}, "expected_output": "[a specific string literal for the '<' character that is not obvious by default]p>see [a specific string literal for the '<' character that is not obvious by default]a href=\"http://example.com\">here[a specific string literal for the '<' character that is not obvious by default]/a>[a specific string literal for the '<' character that is not obvious by default]/p>\n"}
    ]
}
```

---

### Feature 8: Link Integrity Between Source And Translation

**As a developer**, I want to track and verify the anchor identifiers in a fragment, so a translation cannot silently invent links that the source never had.

**Expected Behavior / Usage:**

*8.1 List Link Identifiers — collect the set of anchor identifiers in a fragment*

The request supplies `html`, an inline-HTML fragment. The operation collects the set of identifiers carried by anchor tags: only anchors that have an identifier contribute, each identifier counts once no matter how many anchors share it, and any non-anchor tag is ignored. The output is a single `ids=` line listing the unique identifiers in ascending sorted order, comma-separated, with no spaces (empty after the `=` when there are none).

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_list_link_ids.json`

```json
{
    "description": "Collect the set of anchor identifiers present in an inline-HTML fragment. Only anchor tags carrying an identifier contribute, each identifier is counted once regardless of how many times it appears, and the output lists the unique identifiers in sorted order (empty when there are none).",
    "cases": [
        {"input": {"op": "list_link_ids", "html": "[a specific string literal for the '<' character that is not obvious by default]a id=\"a1\">link1[a specific string literal for the '<' character that is not obvious by default]/a>[a specific string literal for the '<' character that is not obvious by default]strong>[a specific string literal for the '<' character that is not obvious by default]a id=\"a2\">link2[a specific string literal for the '<' character that is not obvious by default]/a>[a specific string literal for the '<' character that is not obvious by default]a id=\"a1\">link1[a specific string literal for the '<' character that is not obvious by default]/a>[a specific string literal for the '<' character that is not obvious by default]em>[a specific string literal for the '<' character that is not obvious by default]a id=\"a3\">link3[a specific string literal for the '<' character that is not obvious by default]/a>[a specific string literal for the '<' character that is not obvious by default]/em>[a specific string literal for the '<' character that is not obvious by default]/strong>"}, "expected_output": "ids=a1,a2,a3\n"}
    ]
}
```

*8.2 Check Translation Links — reject identifiers absent from the source*

The request supplies `source` and `translation`, two inline-HTML fragments. The operation compares the anchor identifiers of the translation against those of the source. When every identifier in the translation also exists in the source the check passes and reports `foreign_ids=` with nothing after the `=`. When the translation contains one or more identifiers absent from the source the check fails with a neutral `error=unrecognised_ids` line followed by an `ids=` line listing those foreign identifiers in ascending sorted order, comma-and-space separated.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_check_translation_links.json`

```json
{
    "description": "Validate that a translated fragment introduces no anchor identifiers that were not present in its source fragment. When every anchor identifier in the translation also exists in the source the check passes and reports no foreign identifiers. When the translation contains identifiers absent from the source the check fails with a neutral unrecognised-ids error listing the offending identifiers in sorted order.",
    "cases": [
        {"input": {"op": "check_translation_links", "source": "[a specific string literal for the '<' character that is not obvious by default]a id=\"a1\">link1[a specific string literal for the '<' character that is not obvious by default]/a>[a specific string literal for the '<' character that is not obvious by default]strong>[a specific string literal for the '<' character that is not obvious by default]a id=\"a2\">link2[a specific string literal for the '<' character that is not obvious by default]/a>[a specific string literal for the '<' character that is not obvious by default]/strong>", "translation": "[a specific string literal for the '<' character that is not obvious by default]a id=\"a1\">lien 1[a specific string literal for the '<' character that is not obvious by default]/a>[a specific string literal for the '<' character that is not obvious by default]strong>[a specific string literal for the '<' character that is not obvious by default]a id=\"a2\">lien 2[a specific string literal for the '<' character that is not obvious by default]/a>[a specific string literal for the '<' character that is not obvious by default]/strong>"}, "expected_output": "foreign_ids=\n"},
        {"input": {"op": "check_translation_links", "source": "[a specific string literal for the '<' character that is not obvious by default]a id=\"a1\">link1[a specific string literal for the '<' character that is not obvious by default]/a>[a specific string literal for the '<' character that is not obvious by default]strong>[a specific string literal for the '<' character that is not obvious by default]a id=\"a2\">link2[a specific string literal for the '<' character that is not obvious by default]/a>[a specific string literal for the '<' character that is not obvious by default]/strong>", "translation": "[a specific string literal for the '<' character that is not obvious by default]a id=\"a1\">lien 1[a specific string literal for the '<' character that is not obvious by default]/a>[a specific string literal for the '<' character that is not obvious by default]strong>[a specific string literal for the '<' character that is not obvious by default]a id=\"a2\">lien 2[a specific string literal for the '<' character that is not obvious by default]/a>[a specific string literal for the '<' character that is not obvious by default]a id=\"a3\">lien 3[a specific string literal for the '<' character that is not obvious by default]/a>[a specific string literal for the '<' character that is not obvious by default]a id=\"a4\">lien 4[a specific string literal for the '<' character that is not obvious by default]/a>[a specific string literal for the '<' character that is not obvious by default]/strong>"}, "expected_output": "error=unrecognised_ids\nids=a3, a4\n"}
    ]
}
```

---

### Feature 9: Segment Path Addressing

**As a developer**, I want to compose and decompose the dotted path that locates a segment within a content tree, so segments can be nested under and lifted out of containers.

**Expected Behavior / Usage:**

A segment is addressed by a dotted path (e.g. `foo.bar`). The request's `sub` field selects the path operation. `wrap` prepends a new leading component supplied as `base` to the existing `path`, producing a longer path; the output is a single `path=` line with the new path. `unwrap` is the inverse: it pops the first component off `path` and returns it together with the remainder; the output is a `component=` line with the popped first component and a `remaining=` line with what is left. `set_order` assigns an integer ordinal (`order`) to the segment without altering its path; the output is an `order=` line echoing the assigned ordinal and a `path=` line confirming the path is unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature9_segment_path.json`

```json
{
    "description": "Manipulate the dotted path that addresses a translatable segment within a content tree. Wrapping prepends a new leading component to the path; unwrapping pops and returns the first component together with the remaining path; setting the order assigns an ordinal to the segment without changing its path. The output reports the resulting path components.",
    "cases": [
        {"input": {"op": "path", "sub": "wrap", "path": "foo.bar", "base": "baz"}, "expected_output": "path=baz.foo.bar\n"},
        {"input": {"op": "path", "sub": "unwrap", "path": "foo.bar"}, "expected_output": "component=foo\nremaining=bar\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features described above. Its physical structure (single-file vs. multi-file repository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering. The core business logic must be decoupled from standard I/O (stdin/stdout) and JSON parsing.

2. **The Execution/Test Adapter:** A runnable program (CLI script or entry point) that acts as a client to your core system — logically (and ideally physically) separated from the core domain. It reads a single JSON request from stdin and prints the resulting output (or a neutral `error=[a specific string literal for the '<' character that is not obvious by default]category>` contract) to stdout, matching the per-feature contracts above. The request's `op` field selects the operation; some operations take a further `sub` field. Errors must be normalized to neutral category lines and must never leak host-language runtime traces.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir [a specific string literal for the '<' character that is not obvious by default]subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/[a specific string literal for the '<' character that is not obvious by default]cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `[a specific string literal for the '<' character that is not obvious by default]cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- use the same character substitution logic as defined in the input sanitization utility
