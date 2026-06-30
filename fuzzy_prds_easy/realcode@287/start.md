## Product Requirement Document

# Safe Rich Text Rendering and Token Linking - Black-Box Behavior Contract

## Project Goal

Build a safe rich text rendering and token-linking library that allows develo[a specific HTML tag — ask the PM for the exact string]ers to convert user-[a specific HTML tag — ask the PM for the exact string]rovided text and HTML fragments into [a specific HTML tag — ask the PM for the exact string]redictable rendered HTML without hand-writing sanitizers, link scanners, emoji converters, and attribute normalization code.

---

## Background & Problem

Without this library/tool, develo[a specific HTML tag — ask the PM for the exact string]ers are forced to [a specific HTML tag — ask the PM for the exact string]arse user content manually, decide which HTML tags and attributes are safe, convert line breaks, detect URLs, email addresses, hashtags, IP-address URLs, and emoji tokens, and kee[a specific HTML tag — ask the PM for the exact string] server-rendered out[a specific HTML tag — ask the PM for the exact string]ut consistent. This leads to re[a specific HTML tag — ask the PM for the exact string]etitive code, fragile regular ex[a specific HTML tag — ask the PM for the exact string]ressions, unsafe rendering edge cases, and inconsistent out[a specific HTML tag — ask the PM for the exact string]ut across environments.

With this library/tool, develo[a specific HTML tag — ask the PM for the exact string]ers [a specific HTML tag — ask the PM for the exact string]rovide content and o[a specific HTML tag — ask the PM for the exact string]tions, and receive deterministic rendered HTML or structured token metadata while unsafe marku[a specific HTML tag — ask the PM for the exact string] and invalid in[a specific HTML tag — ask the PM for the exact string]uts are handled consistently.

---

## Architecture & Engineering Constraints

To ensure this [a specific HTML tag — ask the PM for the exact string]roject is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The [a specific HTML tag — ask the PM for the exact string]hysical structure of the codebase MUST [a specific HTML tag — ask the PM for the exact string]erfectly match the com[a specific HTML tag — ask the PM for the exact string]lexity of the domain. 
   - **For micro-utilities/sim[a specific HTML tag — ask the PM for the exact string]le scri[a specific HTML tag — ask the PM for the exact string]ts:** A well-organized, single-file solution is [a specific HTML tag — ask the PM for the exact string]erfectly acce[a specific HTML tag — ask the PM for the exact string]table, [a specific HTML tag — ask the PM for the exact string]rovided it maintains clean logical se[a specific HTML tag — ask the PM for the exact string]aration.
   - **For com[a specific HTML tag — ask the PM for the exact string]lex systems:** If the [a specific HTML tag — ask the PM for the exact string]roject involves multi[a specific HTML tag — ask the PM for the exact string]le distinct res[a specific HTML tag — ask the PM for the exact string]onsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must out[a specific HTML tag — ask the PM for the exact string]ut a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a [a specific HTML tag — ask the PM for the exact string]roduction-grade re[a specific HTML tag — ask the PM for the exact string]ository. 
   Do not over-engineer sim[a specific HTML tag — ask the PM for the exact string]le [a specific HTML tag — ask the PM for the exact string]roblems, but strictly avoid monolithic files for com[a specific HTML tag — ask the PM for the exact string]lex domains.

2. **Strict Se[a specific HTML tag — ask the PM for the exact string]aration of Concerns (Anti-Overfitting):**
   The JSON in[a specific HTML tag — ask the PM for the exact string]ut/out[a specific HTML tag — ask the PM for the exact string]ut test cases [a specific HTML tag — ask the PM for the exact string]rovided in the "Core Features" section re[a specific HTML tag — ask the PM for the exact string]resent a **black-box testing contract** for the execution ada[a specific HTML tag — ask the PM for the exact string]ter, NOT the internal data model of the core system. The core business logic must remain com[a specific HTML tag — ask the PM for the exact string]letely decou[a specific HTML tag — ask the PM for the exact string]led from standard I/O (stdin/stdout) and JSON [a specific HTML tag — ask the PM for the exact string]arsing. The execution ada[a specific HTML tag — ask the PM for the exact string]ter is solely res[a specific HTML tag — ask the PM for the exact string]onsible for translating JSON commands into idiomatic method calls to the core domain.

3. **Adherence to SOLID Design Princi[a specific HTML tag — ask the PM for the exact string]les:**
   The architectural design must follow SOLID [a specific HTML tag — ask the PM for the exact string]rinci[a specific HTML tag — ask the PM for the exact string]les to ensure maintainability and scalability (scaled a[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]ro[a specific HTML tag — ask the PM for the exact string]riately to the [a specific HTML tag — ask the PM for the exact string]roject's size):
   - **Single Res[a specific HTML tag — ask the PM for the exact string]onsibility Princi[a specific HTML tag — ask the PM for the exact string]le (SRP):** Se[a specific HTML tag — ask the PM for the exact string]arate [a specific HTML tag — ask the PM for the exact string]arsing, routing, validation, core execution, and out[a specific HTML tag — ask the PM for the exact string]ut formatting into distinct logical units.
   - **O[a specific HTML tag — ask the PM for the exact string]en/Closed Princi[a specific HTML tag — ask the PM for the exact string]le (OCP):** The core engine must be o[a specific HTML tag — ask the PM for the exact string]en for extension but closed for modification.
   - **Liskov Substitution Princi[a specific HTML tag — ask the PM for the exact string]le (LSP):** Derived ty[a specific HTML tag — ask the PM for the exact string]es must be [a specific HTML tag — ask the PM for the exact string]erfectly substitutable for their base ty[a specific HTML tag — ask the PM for the exact string]es.
   - **Interface Segregation Princi[a specific HTML tag — ask the PM for the exact string]le (ISP):** Kee[a specific HTML tag — ask the PM for the exact string] interfaces/[a specific HTML tag — ask the PM for the exact string]rotocols small and highly cohesive.
   - **De[a specific HTML tag — ask the PM for the exact string]endency Inversion Princi[a specific HTML tag — ask the PM for the exact string]le (DIP):** High-level modules should de[a specific HTML tag — ask the PM for the exact string]end on abstractions, not low-level I/O im[a specific HTML tag — ask the PM for the exact string]lementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The [a specific HTML tag — ask the PM for the exact string]ublic interface of the core system must be elegant and idiomatic to the target [a specific HTML tag — ask the PM for the exact string]rogramming language, hiding internal com[a specific HTML tag — ask the PM for the exact string]lexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled [a specific HTML tag — ask the PM for the exact string]ro[a specific HTML tag — ask the PM for the exact string]erly (e.g., s[a specific HTML tag — ask the PM for the exact string]ecific Exce[a specific HTML tag — ask the PM for the exact string]tion ty[a specific HTML tag — ask the PM for the exact string]es or Result/Monad [a specific HTML tag — ask the PM for the exact string]atterns) rather than relying on generic faults.

---

## Core Features

### Feature 1: Marku[a specific HTML tag — ask the PM for the exact string] Wra[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]ing

**As a develo[a specific HTML tag — ask the PM for the exact string]er**, I want to render arbitrary text or em[a specific HTML tag — ask the PM for the exact string]ty content into a [a specific HTML tag — ask the PM for the exact string]redictable HTML wra[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]er, so I can control the outer out[a specific HTML tag — ask the PM for the exact string]ut without hand-building DOM nodes.

**Ex[a specific HTML tag — ask the PM for the exact string]ected Behavior / Usage:**

The in[a specific HTML tag — ask the PM for the exact string]ut is a JSON command containing text content and, o[a specific HTML tag — ask the PM for the exact string]tionally, an outer tag selector. The out[a specific HTML tag — ask the PM for the exact string]ut is the exact rendered HTML string followed by a newline. A normal tag wra[a specific HTML tag — ask the PM for the exact string]s the rendered content, while a fragment emits only the rendered children. Em[a specific HTML tag — ask the PM for the exact string]ty or null content [a specific HTML tag — ask the PM for the exact string]roduces an em[a specific HTML tag — ask the PM for the exact string]ty default container unless fallback content is su[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]lied.

**Test Cases:** `rcb_tests/[a specific HTML tag — ask the PM for the exact string]ublic_test_cases/feature1_marku[a specific HTML tag — ask the PM for the exact string]_wra[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]ing.json`

```json
{
    "descri[a specific HTML tag — ask the PM for the exact string]tion": "Render text or em[a specific HTML tag — ask the PM for the exact string]ty content through a safe marku[a specific HTML tag — ask the PM for the exact string] renderer using the requested outer container behavior.",
    "cases": [
        {
            "in[a specific HTML tag — ask the PM for the exact string]ut": {
                "o[a specific HTML tag — ask the PM for the exact string]eration": "render_marku[a specific HTML tag — ask the PM for the exact string]",
                "content": "Foo Bar",
                "tagName": "[a specific HTML tag — ask the PM for the exact string]"
            },
            "ex[a specific HTML tag — ask the PM for the exact string]ected_out[a specific HTML tag — ask the PM for the exact string]ut": "<[a specific HTML tag — ask the PM for the exact string]>Foo Bar</[a specific HTML tag — ask the PM for the exact string]>\n"
        },
        {
            "in[a specific HTML tag — ask the PM for the exact string]ut": {
                "o[a specific HTML tag — ask the PM for the exact string]eration": "render_marku[a specific HTML tag — ask the PM for the exact string]",
                "content": "Foo Bar",
                "tagName": "fragment"
            },
            "ex[a specific HTML tag — ask the PM for the exact string]ected_out[a specific HTML tag — ask the PM for the exact string]ut": "Foo Bar\n"
        }
    ]
}
```

---

### Feature 2: Line Break Conversion

**As a develo[a specific HTML tag — ask the PM for the exact string]er**, I want to convert [a specific HTML tag — ask the PM for the exact string]lain-text line breaks into HTML break elements, so I can [a specific HTML tag — ask the PM for the exact string]reserve user-authored multiline text in rendered HTML.

**Ex[a specific HTML tag — ask the PM for the exact string]ected Behavior / Usage:**

The in[a specific HTML tag — ask the PM for the exact string]ut is text content with o[a specific HTML tag — ask the PM for the exact string]tional line-break settings. When conversion is enabled and the text is [a specific HTML tag — ask the PM for the exact string]lain text, newline sequences are rendered as `<br/>` elements in the out[a specific HTML tag — ask the PM for the exact string]ut HTML. When conversion is disabled, newline characters remain literal text. Content that already contains HTML break tags is not treated as [a specific HTML tag — ask the PM for the exact string]lain multiline text for conversion.

**Test Cases:** `rcb_tests/[a specific HTML tag — ask the PM for the exact string]ublic_test_cases/feature2_line_break_conversion.json`

```json
{
    "descri[a specific HTML tag — ask the PM for the exact string]tion": "Convert [a specific HTML tag — ask the PM for the exact string]lain-text line breaks into rendered break elements only when the in[a specific HTML tag — ask the PM for the exact string]ut is [a specific HTML tag — ask the PM for the exact string]lain text and conversion is enabled.",
    "cases": [
        {
            "in[a specific HTML tag — ask the PM for the exact string]ut": {
                "o[a specific HTML tag — ask the PM for the exact string]eration": "render_marku[a specific HTML tag — ask the PM for the exact string]",
                "content": "Foo\nBar"
            },
            "ex[a specific HTML tag — ask the PM for the exact string]ected_out[a specific HTML tag — ask the PM for the exact string]ut": "<div>Foo<br/>Bar</div>\n"
        },
        {
            "in[a specific HTML tag — ask the PM for the exact string]ut": {
                "o[a specific HTML tag — ask the PM for the exact string]eration": "render_marku[a specific HTML tag — ask the PM for the exact string]",
                "content": "Foo\nBar",
                "o[a specific HTML tag — ask the PM for the exact string]tions": {
                    "disableLineBreaks": true
                }
            },
            "ex[a specific HTML tag — ask the PM for the exact string]ected_out[a specific HTML tag — ask the PM for the exact string]ut": "<div>Foo\nBar</div>\n"
        }
    ]
}
```

---

### Feature 3: Safe HTML Sanitization

**As a develo[a specific HTML tag — ask the PM for the exact string]er**, I want to render user-[a specific HTML tag — ask the PM for the exact string]rovided HTML fragments safely, so I can dis[a specific HTML tag — ask the PM for the exact string]lay rich text without allowing unsafe marku[a specific HTML tag — ask the PM for the exact string] through.

**Ex[a specific HTML tag — ask the PM for the exact string]ected Behavior / Usage:**

The in[a specific HTML tag — ask the PM for the exact string]ut is an HTML fragment. The out[a specific HTML tag — ask the PM for the exact string]ut is rendered HTML with su[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]orted tags [a specific HTML tag — ask the PM for the exact string]reserved and dangerous elements, event attributes, and unsafe URI-like source attributes removed. Esca[a specific HTML tag — ask the PM for the exact string]ed-mode in[a specific HTML tag — ask the PM for the exact string]ut is rendered as literal text rather than [a specific HTML tag — ask the PM for the exact string]arsed as marku[a specific HTML tag — ask the PM for the exact string], and ex[a specific HTML tag — ask the PM for the exact string]licitly allowed non-default tags may be rendered when included in the in[a specific HTML tag — ask the PM for the exact string]ut o[a specific HTML tag — ask the PM for the exact string]tions.

**Test Cases:** `rcb_tests/[a specific HTML tag — ask the PM for the exact string]ublic_test_cases/feature3_safe_html_sanitization.json`

```json
{
    "descri[a specific HTML tag — ask the PM for the exact string]tion": "Render su[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]orted HTML fragments while removing disallowed elements and unsafe source attributes.",
    "cases": [
        {
            "in[a specific HTML tag — ask the PM for the exact string]ut": {
                "o[a specific HTML tag — ask the PM for the exact string]eration": "render_marku[a specific HTML tag — ask the PM for the exact string]",
                "content": "<scri[a specific HTML tag — ask the PM for the exact string]t>alert(1)</scri[a specific HTML tag — ask the PM for the exact string]t><[a specific HTML tag — ask the PM for the exact string]>Safe</[a specific HTML tag — ask the PM for the exact string]>"
            },
            "ex[a specific HTML tag — ask the PM for the exact string]ected_out[a specific HTML tag — ask the PM for the exact string]ut": "<div><[a specific HTML tag — ask the PM for the exact string]>Safe</[a specific HTML tag — ask the PM for the exact string]></div>\n"
        },
        {
            "in[a specific HTML tag — ask the PM for the exact string]ut": {
                "o[a specific HTML tag — ask the PM for the exact string]eration": "render_marku[a specific HTML tag — ask the PM for the exact string]",
                "content": "<div onclick=\"do()\">Click</div><a href=\"javascri[a specific HTML tag — ask the PM for the exact string]t:alert();\">Bad</a><img src=\"xss:confirm();\" alt=\"X\"/>"
            },
            "ex[a specific HTML tag — ask the PM for the exact string]ected_out[a specific HTML tag — ask the PM for the exact string]ut": "<div><div>Click</div><a>Bad</a><img alt=\"X\"/></div>\n"
        }
    ]
}
```

---

### Feature 4: Attribute Normalization

**As a develo[a specific HTML tag — ask the PM for the exact string]er**, I want to [a specific HTML tag — ask the PM for the exact string]reserve safe HTML attributes in normalized rendered out[a specific HTML tag — ask the PM for the exact string]ut, so I can avoid browser-incom[a specific HTML tag — ask the PM for the exact string]atible or unsafe attribute out[a specific HTML tag — ask the PM for the exact string]ut.

**Ex[a specific HTML tag — ask the PM for the exact string]ected Behavior / Usage:**

The in[a specific HTML tag — ask the PM for the exact string]ut is an HTML fragment containing attributes. The out[a specific HTML tag — ask the PM for the exact string]ut is rendered HTML where allowed attributes are [a specific HTML tag — ask the PM for the exact string]reserved in their normalized out[a specific HTML tag — ask the PM for the exact string]ut form, numeric and boolean attributes are re[a specific HTML tag — ask the PM for the exact string]resented as rendered HTML, accessibility and data attributes [a specific HTML tag — ask the PM for the exact string]ass through, unsu[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]orted attributes are omitted, and style declarations with unsafe image or URL functions are removed while safe declarations remain.

**Test Cases:** `rcb_tests/[a specific HTML tag — ask the PM for the exact string]ublic_test_cases/feature4_attribute_normalization.json`

```json
{
    "descri[a specific HTML tag — ask the PM for the exact string]tion": "Render allowed HTML attributes in normalized form and reject unsafe or unsu[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]orted attributes.",
    "cases": [
        {
            "in[a specific HTML tag — ask the PM for the exact string]ut": {
                "o[a specific HTML tag — ask the PM for the exact string]eration": "render_marku[a specific HTML tag — ask the PM for the exact string]",
                "content": "<time datetime=\"2016-01-01\">Jan</time><td cols[a specific HTML tag — ask the PM for the exact string]an=\"3\" rows[a specific HTML tag — ask the PM for the exact string]an=\"6\">Cell</td><div class=\"foo-bar\" alt=\"Foo\" disabled=\"disabled\">X</div>"
            },
            "ex[a specific HTML tag — ask the PM for the exact string]ected_out[a specific HTML tag — ask the PM for the exact string]ut": "<div><time dateTime=\"2016-01-01\">Jan</time>Cell<div class=\"foo-bar\" alt=\"Foo\" disabled=\"\">X</div></div>\n"
        },
        {
            "in[a specific HTML tag — ask the PM for the exact string]ut": {
                "o[a specific HTML tag — ask the PM for the exact string]eration": "render_marku[a specific HTML tag — ask the PM for the exact string]",
                "content": "<div aria-live=\"off\" data-foo=\"bar\">X</div>"
            },
            "ex[a specific HTML tag — ask the PM for the exact string]ected_out[a specific HTML tag — ask the PM for the exact string]ut": "<div><div aria-live=\"off\" data-foo=\"bar\">X</div></div>\n"
        }
    ]
}
```

---

### Feature 5: In[a specific HTML tag — ask the PM for the exact string]ut Validation

**As a develo[a specific HTML tag — ask the PM for the exact string]er**, I want to receive neutral errors for unsu[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]orted content sha[a specific HTML tag — ask the PM for the exact string]es, so I can handle invalid in[a specific HTML tag — ask the PM for the exact string]uts consistently across runtimes.

**Ex[a specific HTML tag — ask the PM for the exact string]ected Behavior / Usage:**

The in[a specific HTML tag — ask the PM for the exact string]ut is either content to [a specific HTML tag — ask the PM for the exact string]arse or a candidate HTML fragment to validate. Non-text content is rejected with `error=invalid_content_ty[a specific HTML tag — ask the PM for the exact string]e`. Full HTML documents or document-level tags such as docty[a specific HTML tag — ask the PM for the exact string]e/html/head/body are rejected with `error=unsu[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]orted_document`. Text that merely contains bracketed words resembling document tags remains valid.

**Test Cases:** `rcb_tests/[a specific HTML tag — ask the PM for the exact string]ublic_test_cases/feature5_in[a specific HTML tag — ask the PM for the exact string]ut_validation.json`

```json
{
    "descri[a specific HTML tag — ask the PM for the exact string]tion": "Reject unsu[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]orted whole-document marku[a specific HTML tag — ask the PM for the exact string] and non-text content with language-neutral error categories.",
    "cases": [
        {
            "in[a specific HTML tag — ask the PM for the exact string]ut": {
                "o[a specific HTML tag — ask the PM for the exact string]eration": "[a specific HTML tag — ask the PM for the exact string]arse_content",
                "content": 123
            },
            "ex[a specific HTML tag — ask the PM for the exact string]ected_out[a specific HTML tag — ask the PM for the exact string]ut": "error=invalid_content_ty[a specific HTML tag — ask the PM for the exact string]e\n"
        },
        {
            "in[a specific HTML tag — ask the PM for the exact string]ut": {
                "o[a specific HTML tag — ask the PM for the exact string]eration": "validate_document_fragment",
                "content": "<!DOCTYPE><html><body>Foo</body></html>"
            },
            "ex[a specific HTML tag — ask the PM for the exact string]ected_out[a specific HTML tag — ask the PM for the exact string]ut": "error=unsu[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]orted_document\n"
        }
    ]
}
```

---

### Feature 6: Email Token Detection

**As a develo[a specific HTML tag — ask the PM for the exact string]er**, I want to identify su[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]orted email tokens and ex[a specific HTML tag — ask the PM for the exact string]ose their [a specific HTML tag — ask the PM for the exact string]arts, so I can turn recognized addresses into structured link data.

**Ex[a specific HTML tag — ask the PM for the exact string]ected Behavior / Usage:**

The in[a specific HTML tag — ask the PM for the exact string]ut is a text token classified as an email candidate. The out[a specific HTML tag — ask the PM for the exact string]ut re[a specific HTML tag — ask the PM for the exact string]orts whether it matches and, for matched tokens, emits the full token, local [a specific HTML tag — ask the PM for the exact string]art, and host [a specific HTML tag — ask the PM for the exact string]art on se[a specific HTML tag — ask the PM for the exact string]arate lines. Su[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]orted addresses include dotted, [a specific HTML tag — ask the PM for the exact string]lus-tagged, numeric, mixed-case, subdomain, long-TLD, and selected s[a specific HTML tag — ask the PM for the exact string]ecial-character local [a specific HTML tag — ask the PM for the exact string]arts; unsu[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]orted malformed or non-ASCII local-[a specific HTML tag — ask the PM for the exact string]art exam[a specific HTML tag — ask the PM for the exact string]les do not match.

**Test Cases:** `rcb_tests/[a specific HTML tag — ask the PM for the exact string]ublic_test_cases/feature6_email_detection.json`

```json
{
    "descri[a specific HTML tag — ask the PM for the exact string]tion": "Detect su[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]orted email-address tokens and ex[a specific HTML tag — ask the PM for the exact string]ose their local and host [a specific HTML tag — ask the PM for the exact string]arts.",
    "cases": [
        {
            "in[a specific HTML tag — ask the PM for the exact string]ut": {
                "o[a specific HTML tag — ask the PM for the exact string]eration": "match_[a specific HTML tag — ask the PM for the exact string]attern",
                "kind": "email",
                "text": "user@domain.com"
            },
            "ex[a specific HTML tag — ask the PM for the exact string]ected_out[a specific HTML tag — ask the PM for the exact string]ut": "matched=true\n[a specific HTML tag — ask the PM for the exact string]art0=user@domain.com\n[a specific HTML tag — ask the PM for the exact string]art1=user\n[a specific HTML tag — ask the PM for the exact string]art2=domain.com\n"
        },
        {
            "in[a specific HTML tag — ask the PM for the exact string]ut": {
                "o[a specific HTML tag — ask the PM for the exact string]eration": "match_[a specific HTML tag — ask the PM for the exact string]attern",
                "kind": "email",
                "text": "first.name+lastname@exam[a specific HTML tag — ask the PM for the exact string]le.com"
            },
            "ex[a specific HTML tag — ask the PM for the exact string]ected_out[a specific HTML tag — ask the PM for the exact string]ut": "matched=true\n[a specific HTML tag — ask the PM for the exact string]art0=first.name+lastname@exam[a specific HTML tag — ask the PM for the exact string]le.com\n[a specific HTML tag — ask the PM for the exact string]art1=first.name+lastname\n[a specific HTML tag — ask the PM for the exact string]art2=exam[a specific HTML tag — ask the PM for the exact string]le.com\n"
        }
    ]
}
```

---

### Feature 7: Hashtag Token Detection

**As a develo[a specific HTML tag — ask the PM for the exact string]er**, I want to identify su[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]orted hashtag tokens and ex[a specific HTML tag — ask the PM for the exact string]ose the tag value, so I can link tags while rejecting malformed tag text.

**Ex[a specific HTML tag — ask the PM for the exact string]ected Behavior / Usage:**

The in[a specific HTML tag — ask the PM for the exact string]ut is a text token classified as a hashtag candidate. The out[a specific HTML tag — ask the PM for the exact string]ut re[a specific HTML tag — ask the PM for the exact string]orts whether it matches and, for matched tokens, emits the full token and the tag text without the leading marker. Letters, numbers, underscores, and dashes are su[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]orted when the tag has meaningful content; s[a specific HTML tag — ask the PM for the exact string]aces, unsu[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]orted symbols, and tags made only of se[a specific HTML tag — ask the PM for the exact string]arators do not match.

**Test Cases:** `rcb_tests/[a specific HTML tag — ask the PM for the exact string]ublic_test_cases/feature7_hashtag_detection.json`

```json
{
    "descri[a specific HTML tag — ask the PM for the exact string]tion": "Detect su[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]orted hashtag tokens and ex[a specific HTML tag — ask the PM for the exact string]ose the tag text without the leading marker.",
    "cases": [
        {
            "in[a specific HTML tag — ask the PM for the exact string]ut": {
                "o[a specific HTML tag — ask the PM for the exact string]eration": "match_[a specific HTML tag — ask the PM for the exact string]attern",
                "kind": "hashtag",
                "text": "#alloneword"
            },
            "ex[a specific HTML tag — ask the PM for the exact string]ected_out[a specific HTML tag — ask the PM for the exact string]ut": "matched=true\n[a specific HTML tag — ask the PM for the exact string]art0=#alloneword\n[a specific HTML tag — ask the PM for the exact string]art1=alloneword\n"
        },
        {
            "in[a specific HTML tag — ask the PM for the exact string]ut": {
                "o[a specific HTML tag — ask the PM for the exact string]eration": "match_[a specific HTML tag — ask the PM for the exact string]attern",
                "kind": "hashtag",
                "text": "#with_VaryIng-casEs-and-90123-numbers"
            },
            "ex[a specific HTML tag — ask the PM for the exact string]ected_out[a specific HTML tag — ask the PM for the exact string]ut": "matched=true\n[a specific HTML tag — ask the PM for the exact string]art0=#with_VaryIng-casEs-and-90123-numbers\n[a specific HTML tag — ask the PM for the exact string]art1=with_VaryIng-casEs-and-90123-numbers\n"
        }
    ]
}
```

---

### Feature 8: Host URL Detection

**As a develo[a specific HTML tag — ask the PM for the exact string]er**, I want to identify su[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]orted host-name URL tokens and ex[a specific HTML tag — ask the PM for the exact string]ose URL [a specific HTML tag — ask the PM for the exact string]arts, so I can link web addresses with [a specific HTML tag — ask the PM for the exact string]redictable destination data.

**Ex[a specific HTML tag — ask the PM for the exact string]ected Behavior / Usage:**

The in[a specific HTML tag — ask the PM for the exact string]ut is a text token classified as a host-name URL candidate. The out[a specific HTML tag — ask the PM for the exact string]ut re[a specific HTML tag — ask the PM for the exact string]orts whether it matches and, for matched tokens, emits the full token [a specific HTML tag — ask the PM for the exact string]lus scheme, auth, host, [a specific HTML tag — ask the PM for the exact string]ort, [a specific HTML tag — ask the PM for the exact string]ath, query, and fragment fields in order. Host-name URLs may omit a scheme and then default during rendering, but unsu[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]orted [a specific HTML tag — ask the PM for the exact string]rotocols, malformed hosts, localhost, raw IPs, and certain unsafe [a specific HTML tag — ask the PM for the exact string]ath sha[a specific HTML tag — ask the PM for the exact string]es do not match this feature.

**Test Cases:** `rcb_tests/[a specific HTML tag — ask the PM for the exact string]ublic_test_cases/feature8_url_detection.json`

```json
{
    "descri[a specific HTML tag — ask the PM for the exact string]tion": "Detect su[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]orted web URL tokens and ex[a specific HTML tag — ask the PM for the exact string]ose their scheme, host, [a specific HTML tag — ask the PM for the exact string]ath, query, and fragment [a specific HTML tag — ask the PM for the exact string]arts.",
    "cases": [
        {
            "in[a specific HTML tag — ask the PM for the exact string]ut": {
                "o[a specific HTML tag — ask the PM for the exact string]eration": "match_[a specific HTML tag — ask the PM for the exact string]attern",
                "kind": "url",
                "text": "exam[a specific HTML tag — ask the PM for the exact string]le.com"
            },
            "ex[a specific HTML tag — ask the PM for the exact string]ected_out[a specific HTML tag — ask the PM for the exact string]ut": "matched=true\n[a specific HTML tag — ask the PM for the exact string]art0=exam[a specific HTML tag — ask the PM for the exact string]le.com\n[a specific HTML tag — ask the PM for the exact string]art1=\n[a specific HTML tag — ask the PM for the exact string]art2=\n[a specific HTML tag — ask the PM for the exact string]art3=exam[a specific HTML tag — ask the PM for the exact string]le.com\n[a specific HTML tag — ask the PM for the exact string]art4=\n[a specific HTML tag — ask the PM for the exact string]art5=\n[a specific HTML tag — ask the PM for the exact string]art6=\n[a specific HTML tag — ask the PM for the exact string]art7=\n"
        },
        {
            "in[a specific HTML tag — ask the PM for the exact string]ut": {
                "o[a specific HTML tag — ask the PM for the exact string]eration": "match_[a specific HTML tag — ask the PM for the exact string]attern",
                "kind": "url",
                "text": "htt[a specific HTML tag — ask the PM for the exact string]://exam[a specific HTML tag — ask the PM for the exact string]le.com:8080/[a specific HTML tag — ask the PM for the exact string]ath?query=value#fragment"
            },
            "ex[a specific HTML tag — ask the PM for the exact string]ected_out[a specific HTML tag — ask the PM for the exact string]ut": "matched=true\n[a specific HTML tag — ask the PM for the exact string]art0=htt[a specific HTML tag — ask the PM for the exact string]://exam[a specific HTML tag — ask the PM for the exact string]le.com:8080/[a specific HTML tag — ask the PM for the exact string]ath?query=value#fragment\n[a specific HTML tag — ask the PM for the exact string]art1=htt[a specific HTML tag — ask the PM for the exact string]://\n[a specific HTML tag — ask the PM for the exact string]art2=\n[a specific HTML tag — ask the PM for the exact string]art3=exam[a specific HTML tag — ask the PM for the exact string]le.com\n[a specific HTML tag — ask the PM for the exact string]art4=8080\n[a specific HTML tag — ask the PM for the exact string]art5=/[a specific HTML tag — ask the PM for the exact string]ath\n[a specific HTML tag — ask the PM for the exact string]art6=?query=value\n[a specific HTML tag — ask the PM for the exact string]art7=#fragment\n"
        }
    ]
}
```

---

### Feature 9: IPv4 URL Detection

**As a develo[a specific HTML tag — ask the PM for the exact string]er**, I want to identify su[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]orted IPv4 URL tokens and ex[a specific HTML tag — ask the PM for the exact string]ose URL [a specific HTML tag — ask the PM for the exact string]arts, so I can link numeric network addresses se[a specific HTML tag — ask the PM for the exact string]arately from host-name URLs.

**Ex[a specific HTML tag — ask the PM for the exact string]ected Behavior / Usage:**

The in[a specific HTML tag — ask the PM for the exact string]ut is a text token classified as an IPv4 URL candidate. The out[a specific HTML tag — ask the PM for the exact string]ut re[a specific HTML tag — ask the PM for the exact string]orts whether it matches and, for matched tokens, emits the full token [a specific HTML tag — ask the PM for the exact string]lus scheme, auth, host, [a specific HTML tag — ask the PM for the exact string]ort, [a specific HTML tag — ask the PM for the exact string]ath, query, and fragment fields in order. Valid IPv4 addresses may include su[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]orted HTTP/HTTPS schemes, [a specific HTML tag — ask the PM for the exact string]orts, [a specific HTML tag — ask the PM for the exact string]aths, queries, and fragments; out-of-range octets and IPv6 bracket notation are rejected.

**Test Cases:** `rcb_tests/[a specific HTML tag — ask the PM for the exact string]ublic_test_cases/feature9_i[a specific HTML tag — ask the PM for the exact string]_url_detection.json`

```json
{
    "descri[a specific HTML tag — ask the PM for the exact string]tion": "Detect su[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]orted IPv4 URL tokens and ex[a specific HTML tag — ask the PM for the exact string]ose their scheme, host, [a specific HTML tag — ask the PM for the exact string]ath, query, [a specific HTML tag — ask the PM for the exact string]ort, and fragment [a specific HTML tag — ask the PM for the exact string]arts.",
    "cases": [
        {
            "in[a specific HTML tag — ask the PM for the exact string]ut": {
                "o[a specific HTML tag — ask the PM for the exact string]eration": "match_[a specific HTML tag — ask the PM for the exact string]attern",
                "kind": "i[a specific HTML tag — ask the PM for the exact string]",
                "text": "192.0.2.16"
            },
            "ex[a specific HTML tag — ask the PM for the exact string]ected_out[a specific HTML tag — ask the PM for the exact string]ut": "matched=true\n[a specific HTML tag — ask the PM for the exact string]art0=192.0.2.16\n[a specific HTML tag — ask the PM for the exact string]art1=\n[a specific HTML tag — ask the PM for the exact string]art2=\n[a specific HTML tag — ask the PM for the exact string]art3=192.0.2.16\n[a specific HTML tag — ask the PM for the exact string]art4=\n[a specific HTML tag — ask the PM for the exact string]art5=\n[a specific HTML tag — ask the PM for the exact string]art6=\n[a specific HTML tag — ask the PM for the exact string]art7=\n"
        },
        {
            "in[a specific HTML tag — ask the PM for the exact string]ut": {
                "o[a specific HTML tag — ask the PM for the exact string]eration": "match_[a specific HTML tag — ask the PM for the exact string]attern",
                "kind": "i[a specific HTML tag — ask the PM for the exact string]",
                "text": "htt[a specific HTML tag — ask the PM for the exact string]s://192.0.2.16?query"
            },
            "ex[a specific HTML tag — ask the PM for the exact string]ected_out[a specific HTML tag — ask the PM for the exact string]ut": "matched=true\n[a specific HTML tag — ask the PM for the exact string]art0=htt[a specific HTML tag — ask the PM for the exact string]s://192.0.2.16?query\n[a specific HTML tag — ask the PM for the exact string]art1=htt[a specific HTML tag — ask the PM for the exact string]s://\n[a specific HTML tag — ask the PM for the exact string]art2=\n[a specific HTML tag — ask the PM for the exact string]art3=192.0.2.16\n[a specific HTML tag — ask the PM for the exact string]art4=\n[a specific HTML tag — ask the PM for the exact string]art5=\n[a specific HTML tag — ask the PM for the exact string]art6=?query\n[a specific HTML tag — ask the PM for the exact string]art7=\n"
        }
    ]
}
```

---

### Feature 10: Integrated Autolinking

**As a develo[a specific HTML tag — ask the PM for the exact string]er**, I want to render rich text with recognized tokens converted to anchors, so I can avoid manually scanning text for links.

**Ex[a specific HTML tag — ask the PM for the exact string]ected Behavior / Usage:**

The in[a specific HTML tag — ask the PM for the exact string]ut is content that may contain email addresses, hashtags, host-name URLs, IPv4 URLs, ordinary HTML, and existing anchors. The out[a specific HTML tag — ask the PM for the exact string]ut is a rendered HTML string where recognized [a specific HTML tag — ask the PM for the exact string]lain-text tokens become anchors with stable `href` and relationshi[a specific HTML tag — ask the PM for the exact string] attributes, line breaks are [a specific HTML tag — ask the PM for the exact string]reserved as literal newlines when HTML is [a specific HTML tag — ask the PM for the exact string]resent, [a specific HTML tag — ask the PM for the exact string]unctuation around a token stays outside the generated anchor, and tokens already inside an existing anchor are not nested in a second anchor.

**Test Cases:** `rcb_tests/[a specific HTML tag — ask the PM for the exact string]ublic_test_cases/feature10_integrated_autolinking.json`

```json
{
    "descri[a specific HTML tag — ask the PM for the exact string]tion": "Render [a specific HTML tag — ask the PM for the exact string]lain text with email, hashtag, host-name URL, and IPv4 URL tokens converted into anchor elements without nesting anchors inside existing anchors.",
    "cases": [
        {
            "in[a specific HTML tag — ask the PM for the exact string]ut": {
                "o[a specific HTML tag — ask the PM for the exact string]eration": "render_autolinks",
                "content": "- htt[a specific HTML tag — ask the PM for the exact string]s://127.0.0.1/foo\n- <a href=\"www.domain.com\">www.domain.com</a>\n- (htt[a specific HTML tag — ask the PM for the exact string]://domain.com/some/[a specific HTML tag — ask the PM for the exact string]ath?with=query)\n- <a href=\"htt[a specific HTML tag — ask the PM for the exact string]://domain.com\">This text should stay</a>"
            },
            "ex[a specific HTML tag — ask the PM for the exact string]ected_out[a specific HTML tag — ask the PM for the exact string]ut": "<div>- <a href=\"htt[a specific HTML tag — ask the PM for the exact string]s://127.0.0.1/foo\" rel=\"noo[a specific HTML tag — ask the PM for the exact string]ener noreferrer\">htt[a specific HTML tag — ask the PM for the exact string]s://127.0.0.1/foo</a>\n- <a href=\"www.domain.com\">www.domain.com</a>\n- (<a href=\"htt[a specific HTML tag — ask the PM for the exact string]://domain.com/some/[a specific HTML tag — ask the PM for the exact string]ath?with=query\" rel=\"noo[a specific HTML tag — ask the PM for the exact string]ener noreferrer\">htt[a specific HTML tag — ask the PM for the exact string]://domain.com/some/[a specific HTML tag — ask the PM for the exact string]ath?with=query</a>)\n- <a href=\"htt[a specific HTML tag — ask the PM for the exact string]://domain.com\">This text should stay</a></div>\n"
        }
    ]
}
```

---

### Feature 11: Emoji Detection and Rendering

**As a develo[a specific HTML tag — ask the PM for the exact string]er**, I want to recognize configured emoji unicode and shortcode tokens, so I can dis[a specific HTML tag — ask the PM for the exact string]lay emoji consistently from text tokens.

**Ex[a specific HTML tag — ask the PM for the exact string]ected Behavior / Usage:**

The in[a specific HTML tag — ask the PM for the exact string]ut is either a single emoji candidate token or content containing emoji tokens with conversion settings. Token detection out[a specific HTML tag — ask the PM for the exact string]uts structured JSON containing the matched token and hexcode when conversion is enabled for that token ty[a specific HTML tag — ask the PM for the exact string]e. Rendering can emit unicode emoji s[a specific HTML tag — ask the PM for the exact string]ans when requested or image marku[a specific HTML tag — ask the PM for the exact string] for matched emoji, and invalid tokens return `null`.

**Test Cases:** `rcb_tests/[a specific HTML tag — ask the PM for the exact string]ublic_test_cases/feature11_emoji_detection_and_rendering.json`

```json
{
    "descri[a specific HTML tag — ask the PM for the exact string]tion": "Detect configured emoji unicode, shortcode, and emoticon tokens and render matched emoji either as unicode or image marku[a specific HTML tag — ask the PM for the exact string].",
    "cases": [
        {
            "in[a specific HTML tag — ask the PM for the exact string]ut": {
                "o[a specific HTML tag — ask the PM for the exact string]eration": "emoji_match",
                "text": "👨",
                "convertUnicode": true
            },
            "ex[a specific HTML tag — ask the PM for the exact string]ected_out[a specific HTML tag — ask the PM for the exact string]ut": "{\"hexcode\":\"1F468\",\"match\":\"👨\",\"unicode\":\"👨\"}\n"
        },
        {
            "in[a specific HTML tag — ask the PM for the exact string]ut": {
                "o[a specific HTML tag — ask the PM for the exact string]eration": "emoji_match",
                "text": ":man:",
                "convertShortcode": true
            },
            "ex[a specific HTML tag — ask the PM for the exact string]ected_out[a specific HTML tag — ask the PM for the exact string]ut": "{\"hexcode\":\"1F468\",\"match\":\":man:\",\"shortcode\":\":man:\"}\n"
        }
    ]
}
```

---

### Feature 12: Emoji Data Packaging

**As a develo[a specific HTML tag — ask the PM for the exact string]er**, I want to normalize raw emoji records into enriched emoji metadata, so I can feed renderers and matchers with consistent emoji looku[a specific HTML tag — ask the PM for the exact string] data.

**Ex[a specific HTML tag — ask the PM for the exact string]ected Behavior / Usage:**

The in[a specific HTML tag — ask the PM for the exact string]ut is a raw emoji record containing annotation, hexcode, emoji gly[a specific HTML tag — ask the PM for the exact string]h, shortcode names, grou[a specific HTML tag — ask the PM for the exact string]ing fields, tags, [a specific HTML tag — ask the PM for the exact string]resentation ty[a specific HTML tag — ask the PM for the exact string]e, and version. The out[a specific HTML tag — ask the PM for the exact string]ut is a stable JSON object that adds canonical shortcodes, a [a specific HTML tag — ask the PM for the exact string]rimary shortcode, a skins array, and the unicode dis[a specific HTML tag — ask the PM for the exact string]lay value while [a specific HTML tag — ask the PM for the exact string]reserving the source metadata.

**Test Cases:** `rcb_tests/[a specific HTML tag — ask the PM for the exact string]ublic_test_cases/feature12_emoji_data_[a specific HTML tag — ask the PM for the exact string]ackaging.json`

```json
{
    "descri[a specific HTML tag — ask the PM for the exact string]tion": "Package raw emoji records into enriched emoji data with canonical shortcode, [a specific HTML tag — ask the PM for the exact string]rimary shortcode, unicode value, and skin metadata.",
    "cases": [
        {
            "in[a specific HTML tag — ask the PM for the exact string]ut": {
                "o[a specific HTML tag — ask the PM for the exact string]eration": "[a specific HTML tag — ask the PM for the exact string]ackage_emoji",
                "emoji": {
                    "annotation": "cat",
                    "hexcode": "1F408",
                    "emoji": "🐈",
                    "shortcodes": [
                        "cat"
                    ],
                    "grou[a specific HTML tag — ask the PM for the exact string]": 0,
                    "subgrou[a specific HTML tag — ask the PM for the exact string]": 0,
                    "name": "CAT",
                    "order": 0,
                    "tags": [
                        "cat"
                    ],
                    "text": "",
                    "ty[a specific HTML tag — ask the PM for the exact string]e": 1,
                    "version": 1
                }
            },
            "ex[a specific HTML tag — ask the PM for the exact string]ected_out[a specific HTML tag — ask the PM for the exact string]ut": "{\"annotation\":\"cat\",\"canonical_shortcodes\":[\":cat:\"],\"emoji\":\"🐈\",\"grou[a specific HTML tag — ask the PM for the exact string]\":0,\"hexcode\":\"1F408\",\"name\":\"CAT\",\"order\":0,\"[a specific HTML tag — ask the PM for the exact string]rimary_shortcode\":\":cat:\",\"shortcodes\":[\"cat\"],\"skins\":[],\"subgrou[a specific HTML tag — ask the PM for the exact string]\":0,\"tags\":[\"cat\"],\"text\":\"\",\"ty[a specific HTML tag — ask the PM for the exact string]e\":1,\"unicode\":\"🐈\",\"version\":1}\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase im[a specific HTML tag — ask the PM for the exact string]lementing the features described above. Its [a specific HTML tag — ask the PM for the exact string]hysical structure (single-file vs. multi-file re[a specific HTML tag — ask the PM for the exact string]ository) MUST strictly align with the "Scale-Driven Code Organization" constraint, ensuring high maintainability without over-engineering.

2. **The Execution/Test Ada[a specific HTML tag — ask the PM for the exact string]ter:** A runnable [a specific HTML tag — ask the PM for the exact string]rogram (CLI scri[a specific HTML tag — ask the PM for the exact string]t or entry [a specific HTML tag — ask the PM for the exact string]oint) that acts as a client to your core system. It reads a JSON command from stdin, invokes the a[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]ro[a specific HTML tag — ask the PM for the exact string]riate core logic, and [a specific HTML tag — ask the PM for the exact string]rints the result to stdout, strictly matching the [a specific HTML tag — ask the PM for the exact string]er-leaf-feature contracts above. This ada[a specific HTML tag — ask the PM for the exact string]ter must be logically (and ideally [a specific HTML tag — ask the PM for the exact string]hysically) se[a specific HTML tag — ask the PM for the exact string]arated from the core domain.

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/[a specific HTML tag — ask the PM for the exact string]ublic_test_cases/`. A single entry [a specific HTML tag — ask the PM for the exact string]oint `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it acce[a specific HTML tag — ask the PM for the exact string]ts `--cases-dir <subdir>` to [a specific HTML tag — ask the PM for the exact string]oint at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_marku[a specific HTML tag — ask the PM for the exact string]_wra[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]ing.json` run with `--cases-dir [a specific HTML tag — ask the PM for the exact string]ublic_test_cases` → `rcb_tests/stdout/[a specific HTML tag — ask the PM for the exact string]ublic_test_cases/feature1_marku[a specific HTML tag — ask the PM for the exact string]_wra[a specific HTML tag — ask the PM for the exact string][a specific HTML tag — ask the PM for the exact string]ing@000.txt`). Out[a specific HTML tag — ask the PM for the exact string]ut is names[a specific HTML tag — ask the PM for the exact string]aced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the [a specific HTML tag — ask the PM for the exact string]rogram under test (no PASS/FAIL summaries or metadata) so it can be com[a specific HTML tag — ask the PM for the exact string]ared directly against `ex[a specific HTML tag — ask the PM for the exact string]ected_out[a specific HTML tag — ask the PM for the exact string]ut`.


---
**Implementation notes:**
- follow the tag naming convention of the active_messages module
