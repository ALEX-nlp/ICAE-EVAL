## Product Requirement Document

# SEO Markup Generation Toolkit - Server-Side Meta, Open Graph, Twitter Card & JSON-LD Renderer

## Project Goal

Build a server-side library that lets web developers declare a page's SEO and social-sharing metadata through a small, fluent API and render it as ready-to-embed HTML head markup. It produces standards-compliant `[standard HTML entity encoding conventions]title>`, `[standard HTML entity encoding conventions]meta>`, and `[standard HTML entity encoding conventions]link>` tags, Open Graph property tags, Twitter Card tags, and JSON-LD structured-data scripts from a single set of inputs, without hand-writing repetitive markup.

---

## Background & Problem

Without this library, developers hand-author the same SEO markup on every page: a `[standard HTML entity encoding conventions]title>` composed from a page name plus a site name, a description meta, canonical and pagination links, Open Graph tags for social previews, Twitter Card tags, and JSON-LD structured data. This boilerplate is verbose, easy to get subtly wrong (forgetting to HTML-escape user-supplied text, mis-ordering tags, duplicating the site title across four different vocabularies), and painful to keep consistent as a page's data changes.

With this library, a developer sets the page title and description once and the toolkit fans those values out across every vocabulary, applies the configured defaults, escapes untrusted text, and emits each tag family in a predictable order. Individual vocabularies remain independently controllable for cases that need finer-grained tuning (e.g. a typed Open Graph article, multiple JSON-LD graphs).

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-vocabulary domain (head meta, Open Graph, Twitter Card, JSON-LD, multi-graph JSON-LD, and a unifying facade). It MUST NOT be a single "god file". Each vocabulary is a distinct responsibility and belongs in its own unit, with a clear directory tree separating core domain code, the configuration/defaults layer, and the execution adapter. Do not over-engineer, but do reflect the genuine breadth of the domain.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box contract for the execution adapter**, not the core data model. The core rendering logic must not know about stdin/stdout or JSON parsing. The adapter alone translates JSON commands into idiomatic calls on the core renderers and serializes their output.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Keep parsing/routing (adapter), per-vocabulary rendering, default merging, and output formatting in separate units.
   - **Open/Closed Principle (OCP):** Adding a new tag vocabulary or a new typed object should not require modifying existing renderers.
   - **Liskov Substitution Principle (LSP):** Each renderer should be substitutable behind its abstraction.
   - **Interface Segregation Principle (ISP):** Each vocabulary exposes only its own cohesive operations.
   - **Dependency Inversion Principle (DIP):** The unifying facade depends on renderer abstractions, not concrete implementations or I/O.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public API should be fluent and read naturally in the target language.
   - **Security:** Free-text fields that surface in markup (description fields especially) MUST be HTML-escaped to neutralize injection; the exact escaping is specified per feature below.
   - **Resilience:** Unknown commands and malformed input must be handled gracefully and reported through a neutral error category rather than leaking runtime fault details.

---

## Core Features

The execution adapter reads one JSON command object from stdin. Every command carries a `channel` field selecting the vocabulary, plus either a `steps` array (an ordered list of field operations) or, for the multi-graph channel, a `graphs` array. The adapter applies the operations and prints the rendered markup to stdout. All rendered output below is the minified form (tags concatenated with no separators).

Two default values are configured for the runtime and appear throughout the contracts: the default head title is `It's Over 9000!`, the default Open Graph / JSON-LD title is `Over 9000 Thousand!`, and the default description for all vocabularies is `For those who helped create the Genki Dama`. The default head title separator is ` - `.

---

### Feature 1: Document Head Meta Tags

**As a developer**, I want to declare the page title, description, keywords, link relations, and crawl directives once, so I can emit a correct, escaped HTML head without hand-writing tags.

**Expected Behavior / Usage:**

This vocabulary (`"channel": "meta"`) always renders a `[standard HTML entity encoding conventions]title>` element followed by a description `[standard HTML entity encoding conventions]meta>`, then any additional tags in a fixed order: keywords, custom tags, canonical, AMP, prev, next, alternate-language links, robots. An optional `config` object on the command can override the runtime defaults (used by the no-translate sub-feature).

*1.1 Title composition — page title combined with the site default*

A supplied title is, by default, joined with the default title using the separator, page-title-first (`"[standard HTML entity encoding conventions]page> - [standard HTML entity encoding conventions]default>"`). The caller can opt out of appending the default to render the page title verbatim, can override the separator, or can change the default title itself. With no title set, the default title renders alone.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_title.json`

```json
{
    "description": "Title composition for the document head. The renderer always emits a [standard HTML entity encoding conventions]title> element plus the default description meta. A supplied page title is, by default, combined with the configured site/default title using a separator (page title first, then separator, then default). Callers may opt out of appending the default to render the page title verbatim, may override the separator, or may change the default title itself; when no explicit page title is given the default title is rendered alone.",
    "cases": [
        {
            "input": {"channel": "meta", "steps": [{"title": "Kamehamehaaaaaaaa"}]},
            "expected_output": "[standard HTML entity encoding conventions]title>Kamehamehaaaaaaaa - It's Over 9000![standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"For those who helped create the Genki Dama\">"
        },
        {
            "input": {"channel": "meta", "steps": [{"title": {"text": "Kamehamehaaaaaaaa", "append_default": false}}]},
            "expected_output": "[standard HTML entity encoding conventions]title>Kamehamehaaaaaaaa[standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"For those who helped create the Genki Dama\">"
        },
        {
            "input": {"channel": "meta", "steps": [{"title_separator": " | "}, {"title": "Kamehamehaaaaaaaa"}]},
            "expected_output": "[standard HTML entity encoding conventions]title>Kamehamehaaaaaaaa | It's Over 9000![standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"For those who helped create the Genki Dama\">"
        },
        {
            "input": {"channel": "meta", "steps": [{"default_title": "Kamehamehaaaaaaaa"}]},
            "expected_output": "[standard HTML entity encoding conventions]title>Kamehamehaaaaaaaa[standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"For those who helped create the Genki Dama\">"
        }
    ]
}
```

*1.2 Description meta — escaped free text with suppression*

A supplied description is HTML-escaped (double quotes → `&quot;`, `[standard HTML entity encoding conventions]`/`>` → entities) before rendering; non-ASCII letters are preserved. Passing boolean `false` suppresses the description tag entirely.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_description.json`

```json
{
    "description": "Description meta handling. A supplied description is HTML-escaped (double quotes become &quot;, [standard HTML entity encoding conventions] and > become entities) before being rendered into the description meta tag, protecting against markup injection while leaving non-ASCII letters intact. Passing a boolean false suppresses the description entirely so no description tag is emitted.",
    "cases": [
        {
            "input": {"channel": "meta", "steps": [{"description": "Kamehamehaaaaaaaa"}]},
            "expected_output": "[standard HTML entity encoding conventions]title>It's Over 9000![standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"Kamehamehaaaaaaaa\">"
        },
        {
            "input": {"channel": "meta", "steps": [{"description": "\"Foo bar\" -> abc"}]},
            "expected_output": "[standard HTML entity encoding conventions]title>It's Over 9000![standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"&quot;Foo bar&quot; -&gt; abc\">"
        },
        {
            "input": {"channel": "meta", "steps": [{"description": "de fidélisation des salariés"}]},
            "expected_output": "[standard HTML entity encoding conventions]title>It's Over 9000![standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"de fidélisation des salariés\">"
        },
        {
            "input": {"channel": "meta", "steps": [{"description": false}]},
            "expected_output": "[standard HTML entity encoding conventions]title>It's Over 9000![standard HTML entity encoding conventions]/title>"
        }
    ]
}
```

*1.3 Keywords — set verbatim or accumulate*

Keywords may be supplied as a single comma-delimited string (rendered verbatim), or accumulated incrementally. When accumulating, a single keyword is appended to the running list while a list of keywords is prepended ahead of those already collected; the rendered keywords meta joins them with comma-and-space.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_keywords.json`

```json
{
    "description": "Keyword meta handling. Keywords may be supplied as a single comma-delimited string (rendered verbatim as the keywords meta content), or accumulated one at a time. When accumulating, a single keyword is appended to the running list, while a list of keywords is prepended ahead of the already-collected ones; the final keywords meta joins them with a comma-and-space separator.",
    "cases": [
        {
            "input": {"channel": "meta", "steps": [{"keywords": "masenko,makankosappo"}]},
            "expected_output": "[standard HTML entity encoding conventions]title>It's Over 9000![standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"For those who helped create the Genki Dama\">[standard HTML entity encoding conventions]meta name=\"keywords\" content=\"masenko,makankosappo\">"
        },
        {
            "input": {"channel": "meta", "steps": [{"keyword": "masenko"}, {"keyword": "makankosappo"}]},
            "expected_output": "[standard HTML entity encoding conventions]title>It's Over 9000![standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"For those who helped create the Genki Dama\">[standard HTML entity encoding conventions]meta name=\"keywords\" content=\"masenko, makankosappo\">"
        },
        {
            "input": {"channel": "meta", "steps": [{"keyword": "masenko"}, {"keyword": "makankosappo"}, {"keyword": ["kienzan", "tayoken"]}]},
            "expected_output": "[standard HTML entity encoding conventions]title>It's Over 9000![standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"For those who helped create the Genki Dama\">[standard HTML entity encoding conventions]meta name=\"keywords\" content=\"kienzan, tayoken, masenko, makankosappo\">"
        }
    ]
}
```

*1.4 Custom meta tags — add and remove*

A custom tag is registered under a key with a content value and the attribute name that should carry the key (default `name`). Tags render after the title/description block. A custom tag can be removed by key, restoring the baseline head.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_custom_meta.json`

```json
{
    "description": "Arbitrary custom meta tags. A custom tag is registered under a key together with a content value and the name of the attribute that should carry the key (defaulting to name). Tags are rendered after the standard title/description block. A previously added custom tag can be removed by its key, restoring the output to the baseline head.",
    "cases": [
        {
            "input": {"channel": "meta", "steps": [{"meta": {"name": "custom-meta", "content": "value", "attribute": "test"}}]},
            "expected_output": "[standard HTML entity encoding conventions]title>It's Over 9000![standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"For those who helped create the Genki Dama\">[standard HTML entity encoding conventions]meta test=\"custom-meta\" content=\"value\">"
        },
        {
            "input": {"channel": "meta", "steps": [{"meta": {"name": "custom-meta", "content": "value", "attribute": "test"}}, {"remove_meta": "custom-meta"}]},
            "expected_output": "[standard HTML entity encoding conventions]title>It's Over 9000![standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"For those who helped create the Genki Dama\">"
        }
    ]
}
```

*1.5 Link relation tags — canonical, AMP, pagination, alternate language*

Each relation renders as a self-closing `[standard HTML entity encoding conventions]link>` with the relation-specific `rel` and the supplied URL; alternate-language links additionally carry `hreflang`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_link_relations.json`

```json
{
    "description": "Link relation tags for SEO and navigation. The renderer can emit canonical, AMP, pagination previous/next, and per-language alternate link elements. Each is rendered as a self-closing link element with the relation-specific rel attribute and the supplied URL; alternate-language links additionally carry the hreflang code.",
    "cases": [
        {
            "input": {"channel": "meta", "steps": [{"canonical": "http://domain.com"}]},
            "expected_output": "[standard HTML entity encoding conventions]title>It's Over 9000![standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"For those who helped create the Genki Dama\">[standard HTML entity encoding conventions]link rel=\"canonical\" href=\"http://domain.com\"/>"
        },
        {
            "input": {"channel": "meta", "steps": [{"amphtml": "http://domain.com/amp"}]},
            "expected_output": "[standard HTML entity encoding conventions]title>It's Over 9000![standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"For those who helped create the Genki Dama\">[standard HTML entity encoding conventions]link rel=\"amphtml\" href=\"http://domain.com/amp\"/>"
        },
        {
            "input": {"channel": "meta", "steps": [{"next": "http://domain.com"}]},
            "expected_output": "[standard HTML entity encoding conventions]title>It's Over 9000![standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"For those who helped create the Genki Dama\">[standard HTML entity encoding conventions]link rel=\"next\" href=\"http://domain.com\"/>"
        },
        {
            "input": {"channel": "meta", "steps": [{"prev": "http://domain.com"}]},
            "expected_output": "[standard HTML entity encoding conventions]title>It's Over 9000![standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"For those who helped create the Genki Dama\">[standard HTML entity encoding conventions]link rel=\"prev\" href=\"http://domain.com\"/>"
        },
        {
            "input": {"channel": "meta", "steps": [{"alternate_language": {"lang": "en", "url": "http://domain.com"}}]},
            "expected_output": "[standard HTML entity encoding conventions]title>It's Over 9000![standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"For those who helped create the Genki Dama\">[standard HTML entity encoding conventions]link rel=\"alternate\" hreflang=\"en\" href=\"http://domain.com\"/>"
        }
    ]
}
```

*1.6 Robots directive and reset*

A robots crawl directive renders as a robots meta tag. The reset operation clears all accumulated state and returns the output to the baseline title/description head.

**Test Cases:** `rcb_tests/public_test_cases/feature1_6_robots_reset.json`

```json
{
    "description": "Robots directive and reset. A robots crawl directive is rendered as a robots meta tag. The reset operation clears all accumulated state (description override, keywords, pagination, canonical, custom tags, alternate languages, robots) and returns the output to the baseline title/description head.",
    "cases": [
        {
            "input": {"channel": "meta", "steps": [{"robots": "all"}]},
            "expected_output": "[standard HTML entity encoding conventions]title>It's Over 9000![standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"For those who helped create the Genki Dama\">[standard HTML entity encoding conventions]meta name=\"robots\" content=\"all\">"
        },
        {
            "input": {"channel": "meta", "steps": [{"description": "test"}, {"keyword": "test"}, {"next": "test"}, {"canonical": "test"}, {"robots": "all"}, {"reset": true}]},
            "expected_output": "[standard HTML entity encoding conventions]title>It's Over 9000![standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"For those who helped create the Genki Dama\">"
        }
    ]
}
```

*1.7 No-translate title styling*

When the head is configured to mark the title non-translatable, the title element carries a `notranslate` class so page translators leave it untouched.

**Test Cases:** `rcb_tests/public_test_cases/feature1_7_notranslate_title.json`

```json
{
    "description": "Optional no-translate styling on the title. When the document head is configured to mark the title as non-translatable, the rendered title element carries a notranslate class so automated page translators leave it untouched. The description meta is unaffected.",
    "cases": [
        {
            "input": {"channel": "meta", "config": {"add_notranslate_class": true, "defaults": {"title": "It's Over 9000!", "description": "For those who helped create the Genki Dama"}}, "steps": []},
            "expected_output": "[standard HTML entity encoding conventions]title class=\"notranslate\">It's Over 9000![standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"For those who helped create the Genki Dama\">"
        }
    ]
}
```

---

### Feature 2: Open Graph Property Tags

**As a developer**, I want to emit Open Graph tags for rich social link previews, so shared URLs render with the right title, description, image, and structured object type.

**Expected Behavior / Usage:**

This vocabulary (`"channel": "opengraph"`) renders `[standard HTML entity encoding conventions]meta property="..." content="..." />` tags. Configured defaults supply title and description, which are emitted even when the caller sets only other fields.

*2.1 Basic properties — title, description, url*

Title and description render as `og:title` and `og:description`; a supplied URL adds `og:url`. Defaults fill title/description when the caller sets only the URL.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_basic_properties.json`

```json
{
    "description": "Open Graph property tags for social link previews. Title and description are rendered as og:title and og:description property meta tags; a supplied URL adds an og:url tag. When the configured defaults provide a title and description, they are emitted even if the caller only sets the URL. Each tag uses the property/content meta shape with the og: prefix.",
    "cases": [
        {
            "input": {"channel": "opengraph", "steps": [{"title": "Hello, Ali"}, {"description": "This is a test by Ali."}]},
            "expected_output": "[standard HTML entity encoding conventions]meta property=\"og:title\" content=\"Hello, Ali\" />[standard HTML entity encoding conventions]meta property=\"og:description\" content=\"This is a test by Ali.\" />"
        },
        {
            "input": {"channel": "opengraph", "steps": [{"url": "https://www.domain.com"}]},
            "expected_output": "[standard HTML entity encoding conventions]meta property=\"og:title\" content=\"Over 9000 Thousand!\" />[standard HTML entity encoding conventions]meta property=\"og:description\" content=\"For those who helped create the Genki Dama\" />[standard HTML entity encoding conventions]meta property=\"og:url\" content=\"https://www.domain.com\" />"
        }
    ]
}
```

*2.2 Typed object with structured sub-properties*

After declaring an object type (e.g. `article`), structured attributes for that type can be attached; a list-valued attribute expands into one tag per element. The type tag renders first, then default title/description, then the type-namespaced attribute tags (e.g. `article:tag`). Attributes are accepted only when they belong to the declared type's allowed set.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_typed_object.json`

```json
{
    "description": "Typed Open Graph objects with structured sub-properties. After declaring an object type (e.g. article), structured attributes for that type can be attached; a list-valued attribute expands into one property tag per element. The type tag is rendered first, followed by the default title/description, then the type-namespaced attribute tags (e.g. article:tag). Attributes are only accepted when they belong to the declared object type's allowed set.",
    "cases": [
        {
            "input": {"channel": "opengraph", "steps": [{"type": "article"}, {"article": {"tag": ["Example", "tags", "test"]}}]},
            "expected_output": "[standard HTML entity encoding conventions]meta property=\"og:type\" content=\"article\" />[standard HTML entity encoding conventions]meta property=\"og:title\" content=\"Over 9000 Thousand!\" />[standard HTML entity encoding conventions]meta property=\"og:description\" content=\"For those who helped create the Genki Dama\" />[standard HTML entity encoding conventions]meta property=\"article:tag\" content=\"Example\" />[standard HTML entity encoding conventions]meta property=\"article:tag\" content=\"tags\" />[standard HTML entity encoding conventions]meta property=\"article:tag\" content=\"test\" />"
        }
    ]
}
```

---

### Feature 3: Twitter Card Tags

**As a developer**, I want to emit Twitter Card meta tags, so links shared on that platform render as rich cards.

**Expected Behavior / Usage:**

This vocabulary (`"channel": "twitter"`) renders `[standard HTML entity encoding conventions]meta name="twitter:..." content="..." />` tags. Only fields the caller sets are emitted; there are no defaults.

*3.1 Card text fields*

Title, site handle, URL, and card type render verbatim under their `twitter:` names; the description field is HTML-escaped before output.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_card_fields.json`

```json
{
    "description": "Twitter Card meta tags. Each card field maps to a name/content meta tag prefixed with twitter:. Title, site handle, URL, and card type are rendered verbatim; the description field is HTML-escaped before output to neutralize markup. Only the fields the caller sets are emitted (no defaults).",
    "cases": [
        {
            "input": {"channel": "twitter", "steps": [{"title": "Kamehamehaaaaaaaa"}]},
            "expected_output": "[standard HTML entity encoding conventions]meta name=\"twitter:title\" content=\"Kamehamehaaaaaaaa\" />"
        },
        {
            "input": {"channel": "twitter", "steps": [{"site": "http://kakaroto.9000"}]},
            "expected_output": "[standard HTML entity encoding conventions]meta name=\"twitter:site\" content=\"http://kakaroto.9000\" />"
        },
        {
            "input": {"channel": "twitter", "steps": [{"url": "http://kakaroto.9000"}]},
            "expected_output": "[standard HTML entity encoding conventions]meta name=\"twitter:url\" content=\"http://kakaroto.9000\" />"
        },
        {
            "input": {"channel": "twitter", "steps": [{"type": "sayajin"}]},
            "expected_output": "[standard HTML entity encoding conventions]meta name=\"twitter:card\" content=\"sayajin\" />"
        },
        {
            "input": {"channel": "twitter", "steps": [{"description": "\"Foo bar\" -> abc"}]},
            "expected_output": "[standard HTML entity encoding conventions]meta name=\"twitter:description\" content=\"&quot;Foo bar&quot; -&gt; abc\" />"
        }
    ]
}
```

*3.2 Card images*

A single image renders as one `twitter:image` tag. A list of images renders as indexed tags (`twitter:images0`, `twitter:images1`, ...), one per image, in order.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_card_images.json`

```json
{
    "description": "Twitter Card image fields. A single image is rendered as one twitter:image tag. A list of images is rendered as a series of indexed tags (twitter:images0, twitter:images1, ...), one per supplied image, preserving order.",
    "cases": [
        {
            "input": {"channel": "twitter", "steps": [{"image": "sayajin.png"}]},
            "expected_output": "[standard HTML entity encoding conventions]meta name=\"twitter:image\" content=\"sayajin.png\" />"
        },
        {
            "input": {"channel": "twitter", "steps": [{"images": ["sayajin.png", "namekusei.png"]}]},
            "expected_output": "[standard HTML entity encoding conventions]meta name=\"twitter:images0\" content=\"sayajin.png\" />[standard HTML entity encoding conventions]meta name=\"twitter:images1\" content=\"namekusei.png\" />"
        }
    ]
}
```

---

### Feature 4: JSON-LD Structured Data

**As a developer**, I want to emit a JSON-LD structured-data script, so search engines can parse rich machine-readable metadata about the page.

**Expected Behavior / Usage:**

This vocabulary (`"channel": "jsonld"`) renders a single `[standard HTML entity encoding conventions]script type="application/ld+json">...[standard HTML entity encoding conventions]/script>` wrapping a JSON object. The object always opens with the schema.org context (`"@context":"https://schema.org"`) and a type, then `name` (from title), then `description`. In the serialized JSON, forward slashes are escaped (`https:\/\/...`).

*4.1 Core fields — type, name, description*

Title sets `name`, description sets `description`, type sets `@type`; defaults supply name/description when not overridden. The description is embedded literally at this layer (no HTML escaping), so quotes appear as JSON-escaped `\"` and `>` stays literal.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_core_fields.json`

```json
{
    "description": "JSON-LD structured-data document. The renderer emits a single application/ld+json script element wrapping a JSON object that always starts with the schema.org context and a type, then a name (from title) and description. Callers may override the title, description, or type; defaults supply name and description when not overridden. Note slashes inside URLs/the context are escaped in the JSON output, and the description text is embedded literally (no HTML escaping at this layer).",
    "cases": [
        {
            "input": {"channel": "jsonld", "steps": [{"title": "Kamehamehaaaaaaaa"}]},
            "expected_output": "[standard HTML entity encoding conventions]script type=\"application/ld+json\">{\"@context\":\"https:\\/\\/schema.org\",\"@type\":\"WebPage\",\"name\":\"Kamehamehaaaaaaaa\",\"description\":\"For those who helped create the Genki Dama\"}[standard HTML entity encoding conventions]/script>"
        },
        {
            "input": {"channel": "jsonld", "steps": [{"description": "Kamehamehaaaaaaaa"}]},
            "expected_output": "[standard HTML entity encoding conventions]script type=\"application/ld+json\">{\"@context\":\"https:\\/\\/schema.org\",\"@type\":\"WebPage\",\"name\":\"Over 9000 Thousand!\",\"description\":\"Kamehamehaaaaaaaa\"}[standard HTML entity encoding conventions]/script>"
        },
        {
            "input": {"channel": "jsonld", "steps": [{"type": "sayajin"}]},
            "expected_output": "[standard HTML entity encoding conventions]script type=\"application/ld+json\">{\"@context\":\"https:\\/\\/schema.org\",\"@type\":\"sayajin\",\"name\":\"Over 9000 Thousand!\",\"description\":\"For those who helped create the Genki Dama\"}[standard HTML entity encoding conventions]/script>"
        },
        {
            "input": {"channel": "jsonld", "steps": [{"description": "\"Foo bar\" -> abc"}]},
            "expected_output": "[standard HTML entity encoding conventions]script type=\"application/ld+json\">{\"@context\":\"https:\\/\\/schema.org\",\"@type\":\"WebPage\",\"name\":\"Over 9000 Thousand!\",\"description\":\"\\\"Foo bar\\\" -> abc\"}[standard HTML entity encoding conventions]/script>"
        }
    ]
}
```

*4.2 URL field resolution*

Setting an explicit URL (directly or via a site reference) appends a `url` entry. Setting the URL to `null` resolves it to the current request URL, which in the default runtime is `http://localhost`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_url_resolution.json`

```json
{
    "description": "JSON-LD url field resolution. Setting an explicit URL (whether via the dedicated url field or a site reference) appends a url entry to the structured-data object. Setting the URL to null resolves it to the current request URL, which in the default runtime environment is http://localhost.",
    "cases": [
        {
            "input": {"channel": "jsonld", "steps": [{"site": "http://kakaroto.9000"}]},
            "expected_output": "[standard HTML entity encoding conventions]script type=\"application/ld+json\">{\"@context\":\"https:\\/\\/schema.org\",\"@type\":\"WebPage\",\"name\":\"Over 9000 Thousand!\",\"description\":\"For those who helped create the Genki Dama\",\"url\":\"http:\\/\\/kakaroto.9000\"}[standard HTML entity encoding conventions]/script>"
        },
        {
            "input": {"channel": "jsonld", "steps": [{"url": null}]},
            "expected_output": "[standard HTML entity encoding conventions]script type=\"application/ld+json\">{\"@context\":\"https:\\/\\/schema.org\",\"@type\":\"WebPage\",\"name\":\"Over 9000 Thousand!\",\"description\":\"For those who helped create the Genki Dama\",\"url\":\"http:\\/\\/localhost\"}[standard HTML entity encoding conventions]/script>"
        }
    ]
}
```

*4.3 Image field*

A single image serializes as a scalar `image` string; a list serializes as a JSON array under `image`, in order. The image entry appears after name/description.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_images.json`

```json
{
    "description": "JSON-LD image field. A single image is serialized as a scalar image string. A list of images is serialized as a JSON array under the image key, preserving order. The image entry appears after the core name/description fields.",
    "cases": [
        {
            "input": {"channel": "jsonld", "steps": [{"image": "sayajin.png"}]},
            "expected_output": "[standard HTML entity encoding conventions]script type=\"application/ld+json\">{\"@context\":\"https:\\/\\/schema.org\",\"@type\":\"WebPage\",\"name\":\"Over 9000 Thousand!\",\"description\":\"For those who helped create the Genki Dama\",\"image\":\"sayajin.png\"}[standard HTML entity encoding conventions]/script>"
        },
        {
            "input": {"channel": "jsonld", "steps": [{"images": ["sayajin.png", "namekusei.png"]}]},
            "expected_output": "[standard HTML entity encoding conventions]script type=\"application/ld+json\">{\"@context\":\"https:\\/\\/schema.org\",\"@type\":\"WebPage\",\"name\":\"Over 9000 Thousand!\",\"description\":\"For those who helped create the Genki Dama\",\"image\":[\"sayajin.png\",\"namekusei.png\"]}[standard HTML entity encoding conventions]/script>"
        }
    ]
}
```

*4.4 Custom properties*

Extra key/value pairs can be attached one at a time or in bulk. Scalars serialize as JSON scalars; objects serialize as nested JSON objects. Custom entries appear after name/description in insertion order.

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_custom_values.json`

```json
{
    "description": "Arbitrary custom JSON-LD properties. Callers can attach extra key/value pairs to the structured-data object, either one at a time or in bulk. Scalar values render as JSON scalars; object values render as nested JSON objects. Custom entries appear after the core name/description fields in insertion order.",
    "cases": [
        {
            "input": {"channel": "jsonld", "steps": [{"value": {"key": "test", "data": "1-2-3"}}, {"value": {"key": "another", "data": "test-value"}}]},
            "expected_output": "[standard HTML entity encoding conventions]script type=\"application/ld+json\">{\"@context\":\"https:\\/\\/schema.org\",\"@type\":\"WebPage\",\"name\":\"Over 9000 Thousand!\",\"description\":\"For those who helped create the Genki Dama\",\"test\":\"1-2-3\",\"another\":\"test-value\"}[standard HTML entity encoding conventions]/script>"
        },
        {
            "input": {"channel": "jsonld", "steps": [{"value": {"key": "author", "data": {"@type": "Organization", "name": "SeoTools", "url": "https://github.com/artesaos/seotools"}}}]},
            "expected_output": "[standard HTML entity encoding conventions]script type=\"application/ld+json\">{\"@context\":\"https:\\/\\/schema.org\",\"@type\":\"WebPage\",\"name\":\"Over 9000 Thousand!\",\"description\":\"For those who helped create the Genki Dama\",\"author\":{\"@type\":\"Organization\",\"name\":\"SeoTools\",\"url\":\"https:\\/\\/github.com\\/artesaos\\/seotools\"}}[standard HTML entity encoding conventions]/script>"
        },
        {
            "input": {"channel": "jsonld", "steps": [{"values": {"test": "1-2-3", "author": {"@type": "Organization", "name": "SeoTools"}}}]},
            "expected_output": "[standard HTML entity encoding conventions]script type=\"application/ld+json\">{\"@context\":\"https:\\/\\/schema.org\",\"@type\":\"WebPage\",\"name\":\"Over 9000 Thousand!\",\"description\":\"For those who helped create the Genki Dama\",\"test\":\"1-2-3\",\"author\":{\"@type\":\"Organization\",\"name\":\"SeoTools\"}}[standard HTML entity encoding conventions]/script>"
        }
    ]
}
```

---

### Feature 5: Multiple JSON-LD Graphs

**As a developer**, I want to declare several independent structured-data graphs for one page, so I can describe multiple entities (e.g. a page and an organization) in separate scripts.

**Expected Behavior / Usage:**

This vocabulary (`"channel": "jsonld_multi"`) takes a `graphs` array; each element is an ordered list of field operations applied to its own structured-data object. The renderer emits one script element per graph, concatenated in order — but only when there is more than one graph. A single-graph collection produces no output. Per-graph operations affect only the graph they belong to.

**Test Cases:** `rcb_tests/public_test_cases/feature5_multi_graph.json`

```json
{
    "description": "Multiple JSON-LD structured-data graphs in one document. A collection holds several independent graphs; each graph is an ordered list of field operations (title/description/etc.) applied to its own structured-data object. The renderer emits a script element per graph, concatenated in order, but only when the collection holds more than one graph — a collection with a single graph produces no output. Field operations target the graph they belong to, so per-graph overrides (e.g. a distinct title on the second graph) appear only in that graph's script.",
    "cases": [
        {
            "input": {"channel": "jsonld_multi", "graphs": [[], [{"title": "Kamehamehaaaaaaaa"}]]},
            "expected_output": "[standard HTML entity encoding conventions]script type=\"application/ld+json\">{\"@context\":\"https:\\/\\/schema.org\",\"@type\":\"WebPage\",\"name\":\"Over 9000 Thousand!\",\"description\":\"For those who helped create the Genki Dama\"}[standard HTML entity encoding conventions]/script>[standard HTML entity encoding conventions]script type=\"application/ld+json\">{\"@context\":\"https:\\/\\/schema.org\",\"@type\":\"WebPage\",\"name\":\"Kamehamehaaaaaaaa\",\"description\":\"For those who helped create the Genki Dama\"}[standard HTML entity encoding conventions]/script>"
        },
        {
            "input": {"channel": "jsonld_multi", "graphs": [[], [], []]},
            "expected_output": "[standard HTML entity encoding conventions]script type=\"application/ld+json\">{\"@context\":\"https:\\/\\/schema.org\",\"@type\":\"WebPage\",\"name\":\"Over 9000 Thousand!\",\"description\":\"For those who helped create the Genki Dama\"}[standard HTML entity encoding conventions]/script>[standard HTML entity encoding conventions]script type=\"application/ld+json\">{\"@context\":\"https:\\/\\/schema.org\",\"@type\":\"WebPage\",\"name\":\"Over 9000 Thousand!\",\"description\":\"For those who helped create the Genki Dama\"}[standard HTML entity encoding conventions]/script>[standard HTML entity encoding conventions]script type=\"application/ld+json\">{\"@context\":\"https:\\/\\/schema.org\",\"@type\":\"WebPage\",\"name\":\"Over 9000 Thousand!\",\"description\":\"For those who helped create the Genki Dama\"}[standard HTML entity encoding conventions]/script>"
        },
        {
            "input": {"channel": "jsonld_multi", "graphs": [[]]},
            "expected_output": ""
        }
    ]
}
```

---

### Feature 6: Unified Multi-Vocabulary Facade

**As a developer**, I want one high-level instruction to populate every vocabulary at once, so a page's title/description/canonical/images stay consistent across head meta, Open Graph, Twitter, and JSON-LD without repeating myself.

**Expected Behavior / Usage:**

This vocabulary (`"channel": "seo"`) fans a single instruction out across all channels and renders their combined output in a fixed order: head tags, then Open Graph, then Twitter, then JSON-LD. Setting the title updates the head title (composed with the default), `og:title`, `twitter:title`, and the JSON-LD `name` together. Setting the description updates the head description, `og:description`, `twitter:description`, and the JSON-LD `description`. Setting canonical adds the head canonical link. Adding images fans out to `og:image` (one per image), a single `twitter:image`, and the JSON-LD `image` array. With no instructions, each channel's defaults render.

**Test Cases:** `rcb_tests/public_test_cases/feature6_unified_facade.json`

```json
{
    "description": "Unified facade that fans a single high-level instruction out to all markup channels at once and renders their combined output in a fixed order: standard head tags, then Open Graph, then Twitter, then JSON-LD. Setting the title updates the head title (composed with the default), the og:title, twitter:title, and the JSON-LD name simultaneously. Setting the description updates the head description meta, og:description, twitter:description, and the JSON-LD description. With no instructions, the defaults for each channel are rendered.",
    "cases": [
        {
            "input": {"channel": "seo", "steps": []},
            "expected_output": "[standard HTML entity encoding conventions]title>It's Over 9000![standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"For those who helped create the Genki Dama\">[standard HTML entity encoding conventions]meta property=\"og:title\" content=\"Over 9000 Thousand!\" />[standard HTML entity encoding conventions]meta property=\"og:description\" content=\"For those who helped create the Genki Dama\" />[standard HTML entity encoding conventions]script type=\"application/ld+json\">{\"@context\":\"https:\\/\\/schema.org\",\"@type\":\"WebPage\",\"name\":\"Over 9000 Thousand!\",\"description\":\"For those who helped create the Genki Dama\"}[standard HTML entity encoding conventions]/script>"
        },
        {
            "input": {"channel": "seo", "steps": [{"title": "Kamehamehaaaaaaa"}]},
            "expected_output": "[standard HTML entity encoding conventions]title>Kamehamehaaaaaaa - It's Over 9000![standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"For those who helped create the Genki Dama\">[standard HTML entity encoding conventions]meta property=\"og:title\" content=\"Kamehamehaaaaaaa\" />[standard HTML entity encoding conventions]meta property=\"og:description\" content=\"For those who helped create the Genki Dama\" />[standard HTML entity encoding conventions]meta name=\"twitter:title\" content=\"Kamehamehaaaaaaa\" />[standard HTML entity encoding conventions]script type=\"application/ld+json\">{\"@context\":\"https:\\/\\/schema.org\",\"@type\":\"WebPage\",\"name\":\"Kamehamehaaaaaaa\",\"description\":\"For those who helped create the Genki Dama\"}[standard HTML entity encoding conventions]/script>"
        },
        {
            "input": {"channel": "seo", "steps": [{"description": "Kamehamehaaaaaaa"}]},
            "expected_output": "[standard HTML entity encoding conventions]title>It's Over 9000![standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"Kamehamehaaaaaaa\">[standard HTML entity encoding conventions]meta property=\"og:description\" content=\"Kamehamehaaaaaaa\" />[standard HTML entity encoding conventions]meta property=\"og:title\" content=\"Over 9000 Thousand!\" />[standard HTML entity encoding conventions]meta name=\"twitter:description\" content=\"Kamehamehaaaaaaa\" />[standard HTML entity encoding conventions]script type=\"application/ld+json\">{\"@context\":\"https:\\/\\/schema.org\",\"@type\":\"WebPage\",\"name\":\"Over 9000 Thousand!\",\"description\":\"Kamehamehaaaaaaa\"}[standard HTML entity encoding conventions]/script>"
        },
        {
            "input": {"channel": "seo", "steps": [{"canonical": "http://domain.com"}]},
            "expected_output": "[standard HTML entity encoding conventions]title>It's Over 9000![standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"For those who helped create the Genki Dama\">[standard HTML entity encoding conventions]link rel=\"canonical\" href=\"http://domain.com\"/>[standard HTML entity encoding conventions]meta property=\"og:title\" content=\"Over 9000 Thousand!\" />[standard HTML entity encoding conventions]meta property=\"og:description\" content=\"For those who helped create the Genki Dama\" />[standard HTML entity encoding conventions]script type=\"application/ld+json\">{\"@context\":\"https:\\/\\/schema.org\",\"@type\":\"WebPage\",\"name\":\"Over 9000 Thousand!\",\"description\":\"For those who helped create the Genki Dama\"}[standard HTML entity encoding conventions]/script>"
        },
        {
            "input": {"channel": "seo", "steps": [{"images": ["Kamehamehaaaaaaa.png"]}, {"images": "Kamehamehaaaaaaa.png"}]},
            "expected_output": "[standard HTML entity encoding conventions]title>It's Over 9000![standard HTML entity encoding conventions]/title>[standard HTML entity encoding conventions]meta name=\"description\" content=\"For those who helped create the Genki Dama\">[standard HTML entity encoding conventions]meta property=\"og:title\" content=\"Over 9000 Thousand!\" />[standard HTML entity encoding conventions]meta property=\"og:description\" content=\"For those who helped create the Genki Dama\" />[standard HTML entity encoding conventions]meta property=\"og:image\" content=\"Kamehamehaaaaaaa.png\" />[standard HTML entity encoding conventions]meta property=\"og:image\" content=\"Kamehamehaaaaaaa.png\" />[standard HTML entity encoding conventions]meta name=\"twitter:image\" content=\"Kamehamehaaaaaaa.png\" />[standard HTML entity encoding conventions]script type=\"application/ld+json\">{\"@context\":\"https:\\/\\/schema.org\",\"@type\":\"WebPage\",\"name\":\"Over 9000 Thousand!\",\"description\":\"For those who helped create the Genki Dama\",\"image\":[\"Kamehamehaaaaaaa.png\",\"Kamehamehaaaaaaa.png\"]}[standard HTML entity encoding conventions]/script>"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the six vocabularies above (head meta, Open Graph, Twitter Card, JSON-LD, multi-graph JSON-LD, and the unifying facade), with a clear directory tree separating per-vocabulary renderers, the defaults/configuration layer, and the public API. Its physical structure MUST follow the "Scale-Driven Code Organization" constraint.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON command from stdin, routes on `channel`, applies the ordered `steps` (or `graphs`) to the appropriate core renderer, and prints the rendered markup to stdout — strictly matching the per-feature contracts above. The adapter must be separated from the core domain, and must translate any native fault into a neutral error category line rather than leaking runtime details.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir [standard HTML entity encoding conventions]subdir>` to choose the directory (default `test_cases`, with `public_test_cases` holding the visible subset embedded in this PRD). For each case it writes one file to `rcb_tests/stdout/[standard HTML entity encoding conventions]cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_title.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_title@000.txt`). Output is namespaced by `[standard HTML entity encoding conventions]cases-dir>` so different case directories never overwrite each other. Each `.txt` contains **only** the raw stdout from the program under test (no PASS/FAIL or metadata), so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- maintains the facade sequence for SEO
- synchronizes values across channels
