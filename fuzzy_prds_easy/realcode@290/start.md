## Product Requirement Document

# Transactional Email Toolkit — Templated Mail Composition & MIME Assembly Library

## Project Goal

Build a server-side email toolkit that lets application developers describe an outbound email declaratively — sender, recipients, subject, body, attachments, inline images and custom headers — and turn it into a ready-to-send transport message, while also rendering the email body from server-side HTML templates through a choice of interchangeable templating engines. The toolkit removes the need to hand-assemble MIME messages or hand-wire a templating engine for every project.

---

## Background & Problem

Without this toolkit, developers who need to send transactional email are forced to work directly against the low-level mail transport API: manually creating MIME messages, setting each recipient class (primary, carbon-copy, blind-copy) by hand, juggling multipart bodies whenever an attachment is present, remembering the exact header names for read-receipt and disposition-notification, and detecting attachment content types themselves. In parallel they must bolt a templating engine onto the project just to interpolate a few values into an HTML body, learning each engine's idiosyncratic file-extension and loader rules. This leads to repetitive, error-prone boilerplate that is copied between services and drifts out of sync.

With this toolkit, the developer constructs a small set of validated value objects (an email, its attachments, its inline pictures), hands them to a converter that produces a correct transport message, and renders bodies through a uniform templating interface that hides each engine's wiring. Mandatory fields are enforced at construction time, content types are detected automatically, and template references are validated before rendering — so mistakes surface as clear, typed errors instead of malformed messages.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility domain (value-object modeling and validation, MIME assembly, content-type detection, and pluggable template rendering). It MUST NOT be a single "god file". Output a clear, multi-module/multi-package directory tree that separates the email domain model, the transport-message assembly, the content-type utilities, and each templating engine integration. Do not over-engineer trivial helpers, but keep each responsibility in its own cohesive unit.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below are a **black-box contract for the execution adapter**, not the internal data model. The core library must expose idiomatic value objects and services and must know nothing about JSON, stdin, or stdout. A thin execution adapter is solely responsible for translating JSON commands into idiomatic calls on the core and rendering the results.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility:** Keep model validation, MIME assembly, content detection, template resolution, and output formatting in distinct units.
   - **Open/Closed:** Adding a new templating engine MUST NOT require modifying existing engines or the email model — engines plug in behind a common rendering abstraction.
   - **Liskov Substitution:** Every templating engine must be substitutable behind the common rendering interface; every attachment/email implementation behind its interface.
   - **Interface Segregation:** Keep the rendering interface, the email interface, and the attachment interface small and focused.
   - **Dependency Inversion:** High-level email assembly depends on abstractions (an email contract, an attachment contract, a rendering contract), not concrete engines or transport classes.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface (builders for value objects, a single render method per engine) must be elegant and hide internal complexity.
   - **Resilience:** Mandatory-field violations, invalid template references, and template-processing failures must be modeled as specific, typed error conditions rather than generic faults.

---

## Core Features

### Feature 1: Email Value Object

**As a developer**, I want to compose an email from its individual parts with mandatory fields enforced up front, so I can catch incomplete messages before they ever reach the mail server.

**Expected Behavior / Usage:**

The caller supplies a sender address, one or more primary recipients, a subject, and a body; optionally carbon-copy and blind-copy recipient lists and a map of custom headers. Sender, primary recipients, subject and body are mandatory — if any one is missing, construction fails with a normalized `error=missing_required_field` line plus a `field=<name>` line naming the absent part (`from`, `to`, `subject`, or `body`). On success the email echoes back its sender, the semicolon-joined recipient lists for each class (carbon-copy and blind-copy render empty when not supplied), the subject and body, the count of custom headers, and each custom header as `custom_header.<key>=<value>` sorted by key. When no custom headers are supplied the header set is empty (count `0`).

**Test Cases:** `rcb_tests/public_test_cases/feature1_email_model.json`

```json
{
    "description": "Compose a logical email value object from its parts. Sender, at least one primary recipient, subject and body are mandatory; omitting any of them is reported as a missing-required-field error naming the absent part. Supplied recipients and custom headers are echoed back; when no custom headers are given the email exposes an empty header set.",
    "cases": [
        {
            "input": {"op": "email.build", "from": "marco@urbs.aeterna", "to": ["roberto@gmail.com", "titus@de.natura"], "cc": ["info@de.natura"], "subject": "Laelius de amicitia", "body": "Firmamentum autem stabilitatis.", "customHeaders": {"K2": "V2", "K1": "V1"}},
            "expected_output": "from=marco@urbs.aeterna\nto=roberto@gmail.com;titus@de.natura\ncc=info@de.natura\nbcc=\nsubject=Laelius de amicitia\nbody=Firmamentum autem stabilitatis.\ncustom_header_count=2\ncustom_header.K1=V1\ncustom_header.K2=V2\n"
        },
        {
            "input": {"op": "email.build", "from": "marco@urbs.aeterna", "to": ["roberto@gmail.com"], "subject": "Hello", "body": "Body text"},
            "expected_output": "from=marco@urbs.aeterna\nto=roberto@gmail.com\ncc=\nbcc=\nsubject=Hello\nbody=Body text\ncustom_header_count=0\n"
        },
        {
            "input": {"op": "email.build", "to": ["roberto@gmail.com"], "subject": "Hello", "body": "Body text"},
            "expected_output": "error=missing_required_field\nfield=from\n"
        },
        {
            "input": {"op": "email.build", "from": "marco@urbs.aeterna", "to": ["roberto@gmail.com"], "body": "Body text"},
            "expected_output": "error=missing_required_field\nfield=subject\n"
        }
    ]
}
```

---

### Feature 2: Inline Picture Descriptor

**As a developer**, I want to describe an image that should be embedded inside the email body and referenced from a template placeholder, so I can produce rich HTML emails with logos and graphics.

**Expected Behavior / Usage:**

An inline-picture descriptor binds three coordinates: the image kind (one of the supported kinds — see Feature 4), the backing file path, and the template placeholder name that the body refers to. All three are mandatory; omitting any one fails with `error=missing_required_field` and a `field=<name>` line (`imageType`, `file`, or `templateName`). On success the descriptor exposes the image kind, the resolved MIME `content_type` for that kind, the placeholder name, and the file path.

**Test Cases:** `rcb_tests/public_test_cases/feature2_inline_picture.json`

```json
{
    "description": "Describe an image to be embedded inline in an email body and referenced from a template placeholder. The descriptor requires three coordinates - the image kind, the backing file path, and the template placeholder name - and exposes the resolved MIME content type for the chosen image kind. Omitting any coordinate is reported as a missing-required-field error.",
    "cases": [
        {
            "input": {"op": "inline_picture.build", "imageType": "PNG", "file": "/images/logo.png", "templateName": "logo.ftl"},
            "expected_output": "image_type=PNG\ncontent_type=image/png\ntemplate_name=logo.ftl\nfile=/images/logo.png\n"
        },
        {
            "input": {"op": "inline_picture.build", "imageType": "JPEG", "templateName": "logo.ftl"},
            "expected_output": "error=missing_required_field\nfield=file\n"
        }
    ]
}
```

---

### Feature 3: Named Attachment with Content-Type Detection

**As a developer**, I want to wrap arbitrary bytes as a named attachment whose MIME type is resolved automatically, so I can attach files without manually classifying their content.

**Expected Behavior / Usage:**

An attachment binds a file name and a payload of bytes; both are mandatory and omitting the data fails with `error=missing_required_field` / `field=attachmentData`. The attachment exposes its payload as a readable resource (`resource_exists=true` and the byte length as `resource_size`). For the content type, an explicitly supplied media type is honoured verbatim; otherwise the type is auto-detected from the byte content together with the file name (for example, a real JPEG image resolves to `image/jpeg`). Output reports the attachment name, the resource existence flag and size, and the resolved `content_type`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_attachment.json`

```json
{
    "description": "Wrap binary content as a named email attachment. Name and data are mandatory. The attachment exposes its bytes as a readable resource and resolves a MIME content type: an explicitly supplied type is honoured, otherwise the type is auto-detected from the byte content together with the file name. Omitting the data is reported as a missing-required-field error.",
    "cases": [
        {
            "input": {"op": "attachment.build", "attachmentName": "report.csv", "dataText": "col1,col2\n1,2\n3,4", "mediaType": "text/plain"},
            "expected_output": "attachment_name=report.csv\nresource_exists=true\nresource_size=17\ncontent_type=text/plain\n"
        },
        {
            "input": {"op": "attachment.build", "attachmentName": "Attachment.jpg", "sampleImage": true},
            "expected_output": "attachment_name=Attachment.jpg\nresource_exists=true\n[a hard-coded size and content type for the sample image flag — verify exact bytes in the image loader]\n[a hard-coded size and content type for the sample image flag — verify exact bytes in the image loader]\n"
        },
        {
            "input": {"op": "attachment.build", "attachmentName": "report.csv"},
            "expected_output": "error=missing_required_field\nfield=attachmentData\n"
        }
    ]
}
```

The `dataText` field supplies the attachment payload as UTF-8 text (escaped newlines count as single bytes, so `col1,col2\n1,2\n3,4` is 17 bytes); the `sampleImage` flag substitutes a bundled real JPEG image so that content-type auto-detection can be exercised against genuine image bytes.

---

### Feature 4: Supported Image-Kind Catalog

**As a developer**, I want to enumerate the inline image kinds the toolkit supports along with their extensions and MIME types, so I can validate user-supplied images against a known set.

**Expected Behavior / Usage:**

The catalog lists each supported image kind with its lowercase file extension and its wire MIME content type, rendered as `<KIND> extension=<ext> content_type=<mime>`. The whole catalog can be listed (in catalog order), or a single kind can be looked up by name. The supported kinds are `GIF` (`gif`, `image/gif`), `JPG` (`jpg`, `image/jpeg`), `JPEG` (`jpeg`, `image/jpeg`) and `PNG` (`png`, `image/png`).

**Test Cases:** `rcb_tests/public_test_cases/feature4_image_type.json`

```json
{
    "description": "Expose the catalog of inline image kinds supported by the library. Each kind maps to a lowercase file extension and a wire MIME content type. The whole catalog can be listed, or a single kind can be looked up by name.",
    "cases": [
        {
            "input": {"op": "image_type.list"},
            "expected_output": "GIF extension=gif content_type=image/gif\nJPG extension=jpg [a hard-coded size and content type for the sample image flag — verify exact bytes in the image loader]\nJPEG extension=jpeg [a hard-coded size and content type for the sample image flag — verify exact bytes in the image loader]\nPNG extension=png content_type=image/png\n"
        },
        {
            "input": {"op": "image_type.get", "name": "JPEG"},
            "expected_output": "JPEG extension=jpeg [a hard-coded size and content type for the sample image flag — verify exact bytes in the image loader]\n"
        }
    ]
}
```

---

### Feature 5: Transport MIME Message Assembly

**As a developer**, I want to convert a logical email into a transport MIME message with all recipient classes and special headers placed correctly, so I can hand a correct message to any standard mail sender.

**Expected Behavior / Usage:**

Given a logical email, the assembler produces a transport message and the framework-observable result is reported: the sender (`from`), the reply-to address (when reply-to is not explicitly set it defaults to the sender), the primary / carbon-copy / blind-copy recipients (`to` / `cc` / `bcc`, each semicolon-joined and empty when absent), the `subject`, and a `multipart` flag that is `true` exactly when one or more attachments are present and `false` otherwise. When the message is not multipart its text body is reported as `body`. Read-receipt and disposition-notification requests are emitted as the wire headers `header_return_receipt` and `header_disposition_notification_to` (empty when not requested). Any custom headers supplied on the email are passed through and reported as `custom_header.<key>=<value>`, sorted by key.

**Test Cases:** `rcb_tests/public_test_cases/feature5_mime_message.json`

```json
{
    "description": "Assemble a logical email into a transport MIME message and report the framework-observable headers it produced. Sender, reply-to, every recipient class (primary, carbon-copy, blind-copy), subject and body are mapped onto the message; read-receipt and disposition-notification headers are emitted when requested; arbitrary custom headers are passed through. The message is marked multipart exactly when one or more attachments are present.",
    "cases": [
        {
            "input": {"op": "mime.assemble", "from": "cicero@mala.currunt", "replyTo": "tullius@urbs.aeterna", "to": ["roberto@gmail.com"], "cc": ["tito@de.natura"], "bcc": ["caius@urbs.aeterna"], "subject": "Laelius de amicitia", "body": "Firmamentum autem stabilitatis.", "receiptTo": "caligola@urbs.aeterna", "depositionNotificationTo": "caligola@urbs.aeterna", "customHeaders": {"key1": "value1", "key2": "value2"}},
            "expected_output": "from=cicero@mala.currunt\nreply_to=tullius@urbs.aeterna\nto=roberto@gmail.com\ncc=tito@de.natura\nbcc=caius@urbs.aeterna\nsubject=Laelius de amicitia\nmultipart=false\nbody=Firmamentum autem stabilitatis.\nheader_return_receipt=caligola@urbs.aeterna\nheader_disposition_notification_to=caligola@urbs.aeterna\ncustom_header.key1=value1\ncustom_header.key2=value2\n"
        },
        {
            "input": {"op": "mime.assemble", "from": "cicero@mala.currunt", "to": ["roberto@gmail.com"], "subject": "With files", "body": "see attached", "attachments": [{"name": "test1.csv", "text": "col1,col2\n1,2"}, {"name": "test2.csv", "text": "a,b"}]},
            "expected_output": "from=cicero@mala.currunt\nreply_to=cicero@mala.currunt\nto=roberto@gmail.com\ncc=\nbcc=\nsubject=With files\nmultipart=true\nheader_return_receipt=\nheader_disposition_notification_to=\n"
        }
    ]
}
```

---

### Feature 6: Pluggable Template Rendering

**As a developer**, I want to render the email body from a server-side HTML template through a uniform interface regardless of which engine backs it, so I can pick an engine per project without changing how I render.

**Expected Behavior / Usage:**

Each engine merges a named template with a model of named values and returns the rendered document verbatim. Every engine enforces the same two validation rules before rendering: a blank template reference is rejected, and a template whose file extension does not match the engine's expected extension is rejected — both surface as `error=invalid_template_name` together with an `engine=<name>` line. A template that exists but cannot be parsed or compiled surfaces as `error=template_processing_failed` with the same `engine` line. Engines differ only in their expected file extension and their placeholder syntax; the rendering contract, the validation behavior, and the error categories are identical across all of them. Each engine below is an independent functional point with its own rendered output and its own expected extension.

*6.1 Expression-and-directive engine — templates with the `ftl` extension*

This engine substitutes `${name}`-style placeholders. A valid template merged with a model yields the rendered document; a blank reference or a non-`ftl` extension yields `invalid_template_name`; a template with a malformed directive yields `template_processing_failed`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_template_freemarker.json`

```json
{
    "description": "Render a server-side HTML template using the expression-and-directive engine whose templates carry the 'ftl' extension. A valid template merged with a model substitutes the model values and returns the rendered document verbatim. A blank template reference or one whose extension is not 'ftl' is rejected as an invalid template name; a syntactically broken template surfaces as a template-processing failure.",
    "cases": [
        {
            "input": {"op": "template.merge", "engine": "freemarker", "template": "email_template.ftl", "model": {"name": "Titus"}},
            "expected_output": "<!doctype html>\n<html>\n<body>\n<p>\n    Ciao <em>Titus</em>!\n</p>\n</body>\n</html>\n"
        },
        {
            "input": {"op": "template.merge", "engine": "freemarker", "template": "    ", "model": {}},
            "expected_output": "error=invalid_template_name\nengine=freemarker\n"
        },
        {
            "input": {"op": "template.merge", "engine": "freemarker", "template": "file.unknownext", "model": {}},
            "expected_output": "error=invalid_template_name\nengine=freemarker\n"
        },
        {
            "input": {"op": "template.merge", "engine": "freemarker", "template": "wrong_email_template.ftl", "model": {}},
            "expected_output": "error=template_processing_failed\nengine=freemarker\n"
        }
    ]
}
```

*6.2 Logic-less engine — templates with the `html` extension*

This engine substitutes `{{name}}`-style placeholders and performs no embedded logic. A valid template merged with a model yields the rendered document; a blank reference or a non-`html` extension yields `invalid_template_name`; a template that cannot be loaded or compiled yields `template_processing_failed`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_template_mustache.json`

```json
{
    "description": "Render a server-side HTML template using the logic-less mustache engine whose templates carry the 'html' extension. A valid template merged with a model substitutes the model values and returns the rendered document verbatim. A blank template reference or one whose extension is not 'html' is rejected as an invalid template name; a template that cannot be loaded or compiled surfaces as a template-processing failure.",
    "cases": [
        {
            "input": {"op": "template.merge", "engine": "mustache", "template": "email_template.html", "model": {"name": "Titus"}},
            "expected_output": "<!doctype html>\n<html>\n<body>\n<p>\n    Ciao <em>Titus</em>!\n</p>\n</body>\n</html>\n"
        },
        {
            "input": {"op": "template.merge", "engine": "mustache", "template": "   ", "model": {}},
            "expected_output": "error=invalid_template_name\nengine=mustache\n"
        },
        {
            "input": {"op": "template.merge", "engine": "mustache", "template": "file.unknownext", "model": {}},
            "expected_output": "error=invalid_template_name\nengine=mustache\n"
        }
    ]
}
```

*6.3 Inheritance-capable engine — templates with the `html` extension*

This engine substitutes `{{ name }}`-style placeholders and supports template inheritance. A valid template merged with a model yields the rendered document; a blank reference or a non-`html` extension yields `invalid_template_name`; a syntactically broken template yields `template_processing_failed`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_template_pebble.json`

```json
{
    "description": "Render a server-side HTML template using the inheritance-capable engine whose templates carry the 'html' extension. A valid template merged with a model substitutes the model values and returns the rendered document verbatim. A blank template reference or one whose extension is not 'html' is rejected as an invalid template name; a syntactically broken template surfaces as a template-processing failure.",
    "cases": [
        {
            "input": {"op": "template.merge", "engine": "pebble", "template": "email_template.html", "model": {"name": "Titus"}},
            "expected_output": "<!doctype html>\n<html>\n<body>\n<p>\n    Ciao <em>Titus</em>!\n</p>\n</body>\n</html>\n"
        },
        {
            "input": {"op": "template.merge", "engine": "pebble", "template": "  ", "model": {}},
            "expected_output": "error=invalid_template_name\nengine=pebble\n"
        },
        {
            "input": {"op": "template.merge", "engine": "pebble", "template": "file.unknownext", "model": {}},
            "expected_output": "error=invalid_template_name\nengine=pebble\n"
        },
        {
            "input": {"op": "template.merge", "engine": "pebble", "template": "wrong_email_template.html", "model": {}},
            "expected_output": "error=template_processing_failed\nengine=pebble\n"
        }
    ]
}
```

*6.4 Natural-templating engine — templates with the `html` extension*

This engine carries expressions in HTML attributes, substituting both element text content and hyperlink targets, so the raw template is still valid HTML. A valid template merged with a model yields the rendered document with attribute expressions resolved into plain text and `href` targets; a blank reference or a non-`html` extension yields `invalid_template_name`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_4_template_thymeleaf.json`

```json
{
    "description": "Render a server-side HTML template using the natural-templating engine whose templates carry the 'html' extension and support attribute-level expressions for both text content and hyperlink targets. A valid template merged with a model substitutes the model values and returns the rendered document verbatim. A blank template reference or one whose extension is not 'html' is rejected as an invalid template name.",
    "cases": [
        {
            "input": {"op": "template.merge", "engine": "thymeleaf", "template": "email_template.html", "model": {"name": "Titus", "activationLink": "http://www.something.com/segment?key=val"}},
            "expected_output": "<html>\n<body>\n<p>\n    Ciao <em>Titus</em>!\n</p>\n<p>\n    <a href=\"http://www.something.com/segment?key=val\">Click Here</a> for activaing your account\n</p>\n</body>\n</html>\n"
        },
        {
            "input": {"op": "template.merge", "engine": "thymeleaf", "template": "   ", "model": {}},
            "expected_output": "error=invalid_template_name\nengine=thymeleaf\n"
        },
        {
            "input": {"op": "template.merge", "engine": "thymeleaf", "template": "file.unknownext", "model": {}},
            "expected_output": "error=invalid_template_name\nengine=thymeleaf\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the email value objects (email, attachment, inline picture, image-kind catalog), the transport MIME assembler, the content-type detector, and the pluggable template-rendering services described above. Its physical structure MUST follow the "Scale-Driven Code Organization" constraint: distinct modules/packages for the domain model, the transport assembly/utilities, and each templating engine integration.

2. **The Execution/Test Adapter:** A runnable program that acts as a client to the core system. It reads a single JSON command from stdin, invokes the appropriate core logic, and prints the language-neutral result to stdout, strictly matching the per-feature contracts above. All error conditions are rendered as normalized category lines (`error=...` with independent detail fields) — no host-language exception identity ever appears on stdout. This adapter MUST be logically and physically separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_email_model.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_email_model@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- echo the attachment mediaType exactly as received from the upstream service
- mirror the field format used for replyTo when the disposition header is configured
