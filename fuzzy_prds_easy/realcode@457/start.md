## Product Requirement Document

# Media Delivery URL Toolkit - Transformation, Signing & Configuration Library

## Project Goal

Build a media delivery toolkit that lets developers turn high-level, declarative descriptions of an image/video [a list of transformation component strings] into the compact URL strings a CDN-backed media service expects, assemble complete delivery URLs, generate and verify access-control signatures, and parse connection configuration — all without hand-writing fragile string concatenation or cryptographic boilerplate.

---

## Background & Problem

A CDN-backed media service delivers transformed images and videos through URLs whose path segments encode an ordered chain of [a list of transformation component strings] instructions (resize, crop, effects, overlays, format, etc.), each expressed as a terse code such as `c_scale`, `h_300`, `[a list of transformation component strings]`, or `l_text:...`. Without a toolkit, developers must memorize every short code, the exact ordering and separator rules, the escaping rules for overlay text, and the base64 rules for remote sources — then concatenate them by hand. They must also implement HMAC-based URL signing and signature verification correctly, and parse a credentials URL into a structured configuration. This is repetitive, easy to get subtly wrong, and a frequent source of broken links and security mistakes.

With this toolkit, a developer passes a plain map of intent (`{"height": 300, "crop": "scale"}`) and receives the correct wire string (`c_scale,h_300`); passes a source plus options and receives a complete delivery URL; passes a signing key and lifetime and receives a valid signed token; and passes a connection URL and receives a normalized configuration tree. The library owns all the ordering, escaping, encoding, and cryptographic detail.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility domain ([a list of transformation component strings]-string assembly, URL composition, cryptographic signing/verification, string/array/path utilities, configuration parsing). It MUST NOT be a single "god file". Output a clear, multi-file directory tree (e.g. a core source tree plus a separate execution adapter) that reflects a production-grade repository. Do not over-engineer the small utilities, but keep each responsibility in its own cohesive unit.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in "Core Features" are a **black-box contract for the execution adapter**, NOT the internal data model of the core system. The core [a list of transformation component strings]/signing/config logic must be completely decoupled from stdin/stdout and JSON parsing. The execution adapter alone translates JSON commands into idiomatic calls to the core and renders the results.

3. **Adherence to SOLID Design Principles:** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units (SRP). The [a list of transformation component strings] engine must be open to new qualifier types without modifying existing ones (OCP). Qualifier/layer types should be substitutable behind a common abstraction (LSP), interfaces kept small and cohesive (ISP), and high-level URL assembly should depend on [a list of transformation component strings] abstractions rather than concrete formatting details (DIP).

4. **Robustness & Interface Design:** The public API must be elegant and idiomatic. Edge cases (missing token lifetime, invalid configuration URLs, missing signing secret, malformed overlays) must be modeled as proper error conditions, not silent failures. In the stdout contract these are normalized to neutral `error=<category>` lines (see below) so the contract is language-independent.

---

## Core Features

Every feature is exercised through one execution adapter that reads a single JSON command object from stdin and writes a deterministic, line-oriented result to stdout. Each output line is `key=value`. Errors are normalized to a leading `error=<category>` line (plus optional neutral fields) and never leak host-language exception types or runtime messages. Unless a case overrides them, the delivery cloud is fixed to the name `test123` so URLs are reproducible.

### Feature 1: Transformation Component String

**As a developer**, I want to turn a declarative map of [a list of transformation component strings] qualifiers into the compact URL path segment a media CDN expects, so I can build [a list of transformation component strings]s without memorizing every short code, separator, or ordering rule.

**Expected Behavior / Usage:**

The input is a map of [a list of transformation component strings] qualifiers (e.g. crop, width, height, effect, angle, density, aspect_ratio, flags, border, audio_codec, bit_rate, offset, custom_function, conditional `if`). The adapter renders the single assembled action as `[a list of transformation component strings]=<segment>`. Within one segment, individual qualifiers are emitted in a canonical order and joined with commas; each qualifier uses its short code (crop→`c_`, height→`h_`, width→`w_`, effect→`e_`, angle→`a_`, density→`dn_`, aspect_ratio→`ar_`, flags→`fl_`, border→`bo_`, audio_codec→`ac_`, bit_rate→`br_`). An effect given as `[name, level]` renders as `e_<name>:<level>`. An angle given as `[mode, value]` renders as `a_<mode>.<value>`. Multiple flags join with `.`. A border map renders as `bo_<width>px_solid_<color>` with a hex color normalized to `rgb:...`. An `offset` pair `[start, end]` expands to both `so_` (start offset) and `eo_` (end offset). A `custom_function` of type `remote` base64-url-encodes its source. A conditional `if` expression is translated to its short operator/variable form (e.g. `aspect_ratio > 0.3 && aspect_ratio < 0.5` → `if_ar_gt_0.3_and_ar_lt_0.5`).

**Test Cases:** `rcb_tests/public_test_cases/feature1_[a list of transformation component strings]_qualifiers.json`

```json
{
    "description": "Build the Cloudinary [a list of transformation component strings] component string from a declarative map of [a list of transformation component strings] qualifiers. The adapter constructs a single [a list of transformation component strings] action from key/value qualifiers and renders its compact URL-segment form, prefixed as '[a list of transformation component strings]=<segment>'. Component qualifiers are emitted in canonical order separated by commas; each qualifier uses its short code (e.g. crop->c_, height->h_, width->w_, effect->e_, angle->a_, density->dn_, aspect_ratio->ar_).",
    "cases": [
        {"input": {"op": "[a list of transformation component strings]", "qualifiers": {"effect": "sepia"}}, "expected_output": "[a list of transformation component strings]=[a list of transformation component strings]\n"},
        {"input": {"op": "[a list of transformation component strings]", "qualifiers": {"effect": ["sepia", -10]}}, "expected_output": "[a list of transformation component strings]=[a list of transformation component strings]:-10\n"},
        {"input": {"op": "[a list of transformation component strings]", "qualifiers": {"height": 300, "crop": "scale"}}, "expected_output": "[a list of transformation component strings]=c_scale,h_300\n"},
        {"input": {"op": "[a list of transformation component strings]", "qualifiers": {"angle": 12}}, "expected_output": "[a list of transformation component strings]=a_12\n"},
        {"input": {"op": "[a list of transformation component strings]", "qualifiers": {"angle": ["auto", 12]}}, "expected_output": "[a list of transformation component strings]=[a list of transformation component strings]\n"},
        {"input": {"op": "[a list of transformation component strings]", "qualifiers": {"density": 150}}, "expected_output": "[a list of transformation component strings]=dn_150\n"},
        {"input": {"op": "[a list of transformation component strings]", "qualifiers": {"aspect_ratio": "3:2"}}, "expected_output": "[a list of transformation component strings]=ar_3:2\n"},
        {"input": {"op": "[a list of transformation component strings]", "qualifiers": {"flags": ["abc", "def"]}}, "expected_output": "[a list of transformation component strings]=fl_abc.def\n"},
        {"input": {"op": "[a list of transformation component strings]", "qualifiers": {"border": {"width": 5, "color": "#ffaabbdd"}}}, "expected_output": "[a list of transformation component strings]=[a list of transformation component strings]\n"},
        {"input": {"op": "[a list of transformation component strings]", "qualifiers": {"audio_codec": "acc"}}, "expected_output": "[a list of transformation component strings]=ac_acc\n"},
        {"input": {"op": "[a list of transformation component strings]", "qualifiers": {"bit_rate": "44k"}}, "expected_output": "[a list of transformation component strings]=br_44k\n"},
        {"input": {"op": "[a list of transformation component strings]", "qualifiers": {"offset": [2.67, 3.22]}}, "expected_output": "[a list of transformation component strings]=eo_3.22,so_2.67\n"},
        {"input": {"op": "[a list of transformation component strings]", "qualifiers": {"custom_function": {"function_type": "remote", "source": "https://df34ra4a.execute-api.us-west-2.amazonaws.com/default/cloudinaryFn"}}}, "expected_output": "[a list of transformation component strings]=[a list of transformation component strings]\n"},
        {"input": {"op": "[a list of transformation component strings]", "qualifiers": {"if": "aspect_ratio > 0.3 && aspect_ratio < 0.5", "effect": "grayscale"}}, "expected_output": "[a list of transformation component strings]=if_ar_gt_0.3_and_ar_lt_0.5,e_grayscale\n"}
    ]
}
```

---

### Feature 2: Layer / Overlay Qualifier String

**As a developer**, I want to describe an overlay (another asset, a video, subtitles, a styled text block, or a fetched remote image) declaratively and get back the correct layer qualifier string, so I can compose overlays without hand-encoding text escaping or base64 rules.

**Expected Behavior / Usage:**

The input is a layer description map. The adapter renders `layer=<qualifier>`. A plain asset renders as `l_<public_id>`, where a folder separator `/` in the id becomes `:`. A non-default delivery type prepends a token (e.g. `private:`), a format suffix appends `.png`, and a non-image resource type prepends the type (e.g. `video:`, `subtitles:`). Default values (`type=upload`, `resource_type=image`) are omitted. A text layer renders as `l_text:<style>:<encoded-text>` where the style is built from font family/size and the text is URL-encoded with commas and slashes double-escaped (`,`→`%252C`, `/`→`%252F`, `?`→`%3F`). A `fetch` source is base64-url-encoded. Error conditions are normalized: a text layer lacking both a style and a public_id yields `error=overlay_text_requires_style`; a non-text layer lacking a public_id yields `error=overlay_requires_public_id` with a `layer_type=<type>` field.

**Test Cases:** `rcb_tests/public_test_cases/feature2_layer_qualifiers.json`

```json
{
    "description": "Build the Cloudinary layer (overlay/underlay) qualifier string from a declarative description of the layer. The adapter renders the result prefixed as 'layer=<qualifier>'. Plain assets render as 'l_<public_id>' where a folder separator '/' becomes ':'. Non-default resource types prepend a type token (e.g. video:, subtitles:). Text layers render as 'l_text:<style>:<url-encoded text>' where the text is double-escaped for commas and slashes. A 'fetch' source is base64-url-encoded. Error conditions are normalized: a text layer without style or public_id yields 'error=overlay_text_requires_style', and a non-text layer without a public_id yields 'error=overlay_requires_public_id' plus a 'layer_type' field.",
    "cases": [
        {"input": {"op": "overlay", "layer": {"public_id": "logo"}}, "expected_output": "layer=l_logo\n"},
        {"input": {"op": "overlay", "layer": {"public_id": "folder/logo"}}, "expected_output": "layer=l_folder:logo\n"},
        {"input": {"op": "overlay", "layer": {"public_id": "logo", "type": "private"}}, "expected_output": "layer=l_private:logo\n"},
        {"input": {"op": "overlay", "layer": {"public_id": "logo", "format": "png"}}, "expected_output": "layer=l_logo.png\n"},
        {"input": {"op": "overlay", "layer": {"resource_type": "video", "public_id": "cat"}}, "expected_output": "layer=l_video:cat\n"},
        {"input": {"op": "overlay", "layer": {"public_id": "logo", "text": "Hello World, Nice to meet you?"}}, "expected_output": "layer=l_text:logo:Hello%20World%252C%20Nice%20to%20meet%20you%3F\n"},
        {"input": {"op": "overlay", "layer": {"text": "Hello World, Nice to meet you?", "font_family": "Arial", "font_size": "18"}}, "expected_output": "layer=[complexly encoded text string for text layers]\n"},
        {"input": {"op": "overlay", "layer": {"text": "Hello World, Nice/ to meet you?", "font_family": "Arial", "font_size": "18"}}, "expected_output": "layer=[complexly encoded text string for text layers]\n"},
        {"input": {"op": "overlay", "layer": {"resource_type": "subtitles", "public_id": "sample_sub_en.srt"}}, "expected_output": "layer=l_subtitles:sample_sub_en.srt\n"},
        {"input": {"op": "overlay", "layer": {"public_id": "logo", "fetch": "https://cloudinary.com/images/old_logo.png"}}, "expected_output": "layer=l_fetch:aHR0cHM6Ly9jbG91ZGluYXJ5LmNvbS9pbWFnZXMvb2xkX2xvZ28ucG5n\n"},
        {"input": {"op": "overlay", "layer": {"public_id": "logo", "type": "upload", "resource_type": "image"}}, "expected_output": "layer=l_logo\n"},
        {"input": {"op": "overlay", "layer": {"text": "text"}}, "expected_output": "error=overlay_text_requires_style\n"},
        {"input": {"op": "overlay", "layer": {"resource_type": "image"}}, "expected_output": "error=overlay_requires_public_id\nlayer_type=image\n"},
        {"input": {"op": "overlay", "layer": {"resource_type": "video"}}, "expected_output": "error=overlay_requires_public_id\nlayer_type=video\n"}
    ]
}
```

---

### Feature 3: Delivery URL Composition

**As a developer**, I want to compose a complete delivery URL from a source identifier and a map of options (cloud name, secure scheme, asset/delivery type, [a list of transformation component strings] chain), so I can produce correct links without manually assembling host, path, and [a list of transformation component strings] segments.

**Expected Behavior / Usage:**

The input is a `source` plus an optional `params` map. The adapter renders `url=<full url>`. The URL has the shape `<scheme>://res.cloudinary.com/<cloud_name>/<asset_type>/<delivery_type>/<[a list of transformation component strings]s>/<source>`. Defaults: scheme `http`, asset_type `image`, delivery_type `upload`, cloud name from configuration. Options override: `cloud_name` swaps the cloud, `secure=true` switches the scheme to `https`, `resource_type` changes the asset type, `type` changes the delivery type, and `[a list of transformation component strings]` (an ordered list of qualifier maps) is rendered into one path segment per entry, inserted before the source filename.

**Test Cases:** `rcb_tests/public_test_cases/feature3_delivery_url.json`

```json
{
    "description": "Generate a full media delivery URL from a source identifier and a map of delivery options. The adapter renders the result prefixed as 'url=<full url>'. The URL has the shape '<scheme>://res.cloudinary.com/<cloud_name>/<asset_type>/<delivery_type>/<[a list of transformation component strings]s>/<source>'. By default the scheme is http, asset_type is image, delivery_type is upload, and the cloud name comes from configuration. Options can override the cloud_name, switch the scheme to https ('secure'=true), select a different asset type ('resource_type') or delivery type ('type'), and inject a [a list of transformation component strings] chain (an ordered list of qualifier maps) inserted as path segments before the source filename.",
    "cases": [
        {"input": {"op": "delivery_url", "source": "sample.png"}, "expected_output": "url=http://res.cloudinary.com/test123/image/upload/sample.png\n"},
        {"input": {"op": "delivery_url", "source": "sample.png", "params": {"secure": true}}, "expected_output": "url=https://res.cloudinary.com/test123/image/upload/sample.png\n"},
        {"input": {"op": "delivery_url", "source": "sample.png", "params": {"cloud_name": "test321"}}, "expected_output": "url=http://res.cloudinary.com/test321/image/upload/sample.png\n"},
        {"input": {"op": "delivery_url", "source": "sample.png", "params": {"resource_type": "video"}}, "expected_output": "url=http://res.cloudinary.com/test123/video/upload/sample.png\n"},
        {"input": {"op": "delivery_url", "source": "sample.png", "params": {"type": "fetch"}}, "expected_output": "url=http://res.cloudinary.com/test123/image/fetch/sample.png\n"},
        {"input": {"op": "delivery_url", "source": "sample.png", "params": {"[a list of transformation component strings]": [{"effect": "sepia"}, {"height": 300, "crop": "scale"}]}}, "expected_output": "url=http://res.cloudinary.com/test123/image/upload/[a list of transformation component strings]/c_scale,h_300/sample.png\n"}
    ]
}
```

---

### Feature 4: Signed Access Token Generation

**As a developer**, I want to generate a signed, time-limited access token for delivering access-controlled media, so I can grant temporary access without implementing the HMAC scheme myself.

**Expected Behavior / Usage:**

The input is a token `config` (signing `key`, optional `start_time`, a `duration` or an `expiration`, optional `acl`, `ip`) plus an optional URL `path`. The adapter renders `token=<token>`. The token is a tilde-separated list under the name `__cld_token__`, containing the start time `st`, the expiry `exp` (computed as `start_time + duration` when only a duration is given), an optional lowercased and percent-escaped `acl`, and a hex `hmac` digest computed (HMAC-SHA256) over the signed parts. When an `acl` is present, any URL `path` is ignored (the token is reusable across matching URLs); when no `acl` is present, the `path` is folded into the signed payload, producing a different `hmac`. Supplying neither `duration` nor `expiration` is an error, normalized to `error=missing_token_lifetime`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_auth_token.json`

```json
{
    "description": "Generate a signed authentication token used to deliver access-controlled media. The adapter accepts a token config (signing key, optional start_time, duration or expiration, optional acl/ip) plus an optional URL path, and renders the result prefixed as 'token=<token>'. The token is a tilde-separated list under the name '__cld_token__', containing the start time (st), expiry (exp = start + duration when only duration is given), an optional lowercased+escaped acl, and an HMAC-SHA256 digest (hmac) over the signed parts. When an acl is present the URL path is ignored; otherwise the path is folded into the signed payload, producing a different hmac. Omitting both duration and expiration is an error, normalized to 'error=missing_token_lifetime'.",
    "cases": [
        {"input": {"op": "auth_token", "config": {"key": "00112233FF99", "start_time": 1111111111, "duration": 300, "acl": "/image/*"}}, "expected_output": "token=__cld_token__=st=1111111111~exp=1111111411~acl=%2fimage%2f*~hmac=1751370bcc6cfe9e03f30dd1a9722ba0f2cdca283fa3e6df3342a00a7528cc51\n"},
        {"input": {"op": "auth_token", "config": {"key": "00112233FF99", "start_time": 1111111111, "duration": 300}, "path": "sample.jpg"}, "expected_output": "token=__cld_token__=st=1111111111~exp=1111111411~hmac=1b191b2c76e58f0e65f76224c22490a6fa361681570b15eece7b9e9f4ad3d5e4\n"},
        {"input": {"op": "auth_token", "config": {"key": "00112233FF99", "start_time": 1111111111, "duration": 300, "acl": "/image/*"}, "path": "sample.jpg"}, "expected_output": "token=__cld_token__=st=1111111111~exp=1111111411~acl=%2fimage%2f*~hmac=1751370bcc6cfe9e03f30dd1a9722ba0f2cdca283fa3e6df3342a00a7528cc51\n"},
        {"input": {"op": "auth_token", "config": {"key": "00112233FF99"}}, "expected_output": "error=missing_token_lifetime\n"}
    ]
}
```

---

### Feature 5: API Response Signature Verification

**As a developer**, I want to recompute and verify the signature attached to an API response, so I can confirm a payload's authenticity without re-implementing the signing scheme.

**Expected Behavior / Usage:**

The input is an asset `public_id`, its `version`, a candidate `signature`, and the signing `api_secret`. The adapter recomputes the expected signature as the SHA1 of `public_id=<public_id>&version=<version><api_secret>` and renders both `expected_signature=<hex>` and `signature_match=true|false`. Tampering with the public_id, version, or candidate signature breaks the match. A missing or empty `api_secret` is an error, normalized to `error=invalid_api_secret`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_signature_verification.json`

```json
{
    "description": "Verify the authenticity of an API response signature. Given the asset's public_id, its version, a candidate signature, and the signing api_secret, the adapter recomputes the expected signature as SHA1 of 'public_id=<public_id>&version=<version><api_secret>' and reports both the recomputed 'expected_signature=<hex>' and whether the candidate matches ('signature_match=true|false'). Tampering with the public_id, version, or signature breaks the match. When the api_secret is missing or empty, the operation is rejected and normalized to 'error=invalid_api_secret'.",
    "cases": [
        {"input": {"op": "verify_api_signature", "public_id": "tests/logo.png", "version": 1, "signature": "08d3107a5b2ad82e7d82c0b972218fbf20b5b1e0", "api_secret": "X7qLTrsES31MzxxkxPPA-pAGGfU"}, "expected_output": "expected_signature=08d3107a5b2ad82e7d82c0b972218fbf20b5b1e0\nsignature_match=true\n"},
        {"input": {"op": "verify_api_signature", "public_id": "tests/logo.pnga", "version": 1, "signature": "08d3107a5b2ad82e7d82c0b972218fbf20b5b1e0", "api_secret": "X7qLTrsES31MzxxkxPPA-pAGGfU"}, "expected_output": "expected_signature=b59e75ec8ad874219dbb2219ba0fc81e5d5fdfec\nsignature_match=false\n"},
        {"input": {"op": "verify_api_signature", "public_id": "tests/logo.png", "version": 2, "signature": "08d3107a5b2ad82e7d82c0b972218fbf20b5b1e0", "api_secret": "X7qLTrsES31MzxxkxPPA-pAGGfU"}, "expected_output": "expected_signature=ccb069e6cc6087b32913b6d49a9882991a4906ce\nsignature_match=false\n"},
        {"input": {"op": "verify_api_signature", "public_id": "tests/logo.png", "version": 1, "signature": "x", "api_secret": null}, "expected_output": "error=invalid_api_secret\n"}
    ]
}
```

---

### Feature 6: String Utilities

**As a developer**, I want a set of small, predictable string helpers (middle truncation, case conversion, acronym building, character escaping), so I can normalize identifiers and labels consistently across the codebase.

**Expected Behavior / Usage:**

*6.1 Middle Truncation — shorten a string to a maximum length while keeping both ends*

The input is a `text`, an optional `max_length`, and an optional `glue` (default `...`). The adapter renders `result=<truncated>`. If the text already fits within the maximum, it is returned unchanged. Otherwise the kept prefix and suffix are joined with the glue so the total length does not exceed the maximum; when the maximum is too small for the glue plus suffix, the prefix shrinks (possibly to nothing) and the glue itself is truncated, always preserving the tail of the original string.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_truncate_middle.json`

```json
{
    "description": "Truncate a string in the middle so its length does not exceed a maximum, joining the kept prefix and suffix with a glue marker. The adapter renders 'result=<truncated>'. When the string already fits within the maximum, it is returned unchanged. The glue defaults to '...' but can be customized. If the maximum is so small that the glue plus suffix overflow, the kept prefix shrinks (possibly to nothing) and the glue itself may be truncated, always keeping the tail of the original string.",
    "cases": [
        {"input": {"op": "truncate_middle", "text": "Lorem ipsum dolor sit amet, consectetur adipiscing elit", "max_length": 16}, "expected_output": "result=Lorem...ing elit\n"},
        {"input": {"op": "truncate_middle", "text": "Lorem ipsum dolor sit amet, consectetur adipiscing elit", "max_length": 16, "glue": "**"}, "expected_output": "result=Lorem **ing elit\n"},
        {"input": {"op": "truncate_middle", "text": "Lorem ipsum dolor sit amet, consectetur adipiscing elit", "max_length": 6}, "expected_output": "result=...lit\n"},
        {"input": {"op": "truncate_middle", "text": "Lorem ipsum dolor sit amet, consectetur adipiscing elit", "max_length": 6, "glue": "!@#$"}, "expected_output": "result=!@#lit\n"},
        {"input": {"op": "truncate_middle", "text": "Lorem ipsum dolor sit amet, consectetur adipiscing elit"}, "expected_output": "result=Lorem ipsum dolor sit amet, consectetur adipiscing elit\n"}
    ]
}
```

*6.2 camelCase to snake_case — split an identifier on uppercase boundaries*

The input is a `text` and an optional `separator` (default `_`). The adapter renders `result=<converted>`. A separator is inserted before each uppercase letter and the letter is lowercased, so every uppercase boundary is split (an all-uppercase input becomes fully separated single letters).

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_camel_to_snake.json`

```json
{
    "description": "Convert a camelCase identifier into snake_case, inserting a separator before each uppercase letter and lowercasing it. The adapter renders 'result=<converted>'. The separator defaults to '_' but can be customized to any string. Every uppercase boundary is split, so an all-uppercase input becomes fully separated single letters.",
    "cases": [
        {"input": {"op": "camel_to_snake", "text": "testString"}, "expected_output": "result=test_string\n"},
        {"input": {"op": "camel_to_snake", "text": "TESTSTRING"}, "expected_output": "result=t_e_s_t_s_t_r_i_n_g\n"},
        {"input": {"op": "camel_to_snake", "text": "testString", "separator": "@"}, "expected_output": "result=test@string\n"}
    ]
}
```

*6.3 Acronym Building — take the first letter of each delimited segment*

The input is a `text`, an optional `exclusions` list, and an optional `delimiter` (default `_`). The adapter renders `result=<acronym>`. The text is split on the delimiter; any segment equal to an excluded word is dropped before initials are taken; the first character of each remaining segment is concatenated. An empty input yields an empty result.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_acronym.json`

```json
{
    "description": "Build an acronym from a delimited identifier by taking the first character of each segment. The adapter renders 'result=<acronym>'. Segments are split on a delimiter that defaults to '_'. An optional exclusion list drops any segment equal to one of the excluded words before taking initials, so only the meaningful segments contribute letters.",
    "cases": [
        {"input": {"op": "acronym", "text": ""}, "expected_output": "result=\n"},
        {"input": {"op": "acronym", "text": "test"}, "expected_output": "result=t\n"},
        {"input": {"op": "acronym", "text": "test_acronym"}, "expected_output": "result=ta\n"},
        {"input": {"op": "acronym", "text": "test_acronym_exclude_me", "exclusions": ["exclude", "me"]}, "expected_output": "result=ta\n"},
        {"input": {"op": "acronym", "text": "test@acronym@custom@delimiter", "exclusions": [], "delimiter": "@"}, "expected_output": "result=tacd\n"}
    ]
}
```

*6.4 Unsafe Character Escaping — backslash-escape a configured character set*

The input is a `text` and an `unsafe_chars` set, supplied either as a single string of characters or as a list of single-character strings (both forms equivalent). The adapter renders `result=<escaped>`. Each occurrence of a character in the set is prefixed with a backslash; characters not in the set are left untouched; an empty set leaves the input unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature6_4_escape_unsafe.json`

```json
{
    "description": "Escape a configured set of characters within a string by prefixing each occurrence with a backslash. The adapter renders 'result=<escaped>'. The set of characters to escape can be supplied either as a single string of characters or as a list of single-character strings; both forms are equivalent. Any character not in the set is left untouched, and an empty set leaves the input unchanged.",
    "cases": [
        {"input": {"op": "escape_unsafe", "text": "Lorem ipsum dolor sit amet, consectetur adipiscing elit", "unsafe_chars": "Lorem"}, "expected_output": "result=\\L\\o\\r\\e\\m ipsu\\m d\\ol\\o\\r sit a\\m\\et, c\\ons\\ect\\etu\\r adipiscing \\elit\n"},
        {"input": {"op": "escape_unsafe", "text": "Lorem ipsum dolor sit amet, consectetur adipiscing elit", "unsafe_chars": ["L", "o", "r", "e", "m"]}, "expected_output": "result=\\L\\o\\r\\e\\m ipsu\\m d\\ol\\o\\r sit a\\m\\et, c\\ons\\ect\\etu\\r adipiscing \\elit\n"},
        {"input": {"op": "escape_unsafe", "text": "Lorem ipsum dolor sit amet, consectetur adipiscing elit", "unsafe_chars": ""}, "expected_output": "result=Lorem ipsum dolor sit amet, consectetur adipiscing elit\n"}
    ]
}
```

---

### Feature 7: Array Utilities

**As a developer**, I want predictable helpers for reordering associative data and joining mixed scalars, so I can control serialization order and formatting deterministically.

**Expected Behavior / Usage:**

*7.1 Sort by Explicit Key Order — reorder a map to follow a key list*

The input is a `map` and an `order` list of keys. The adapter renders `keys=<comma-joined>` and `values=<comma-joined>` for the reordered map. Keys present in the order list come first in that order; keys in the map but absent from the order are appended afterwards in their original relative order; keys in the order list but absent from the map are ignored. An empty or wholly-irrelevant order falls back to the natural sorted order of the keys.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_sort_by_array.json`

```json
{
    "description": "Reorder an associative map so its entries follow an explicit key order. The adapter renders the resulting key sequence as 'keys=<comma-joined>' and the corresponding values as 'values=<comma-joined>'. Keys listed in the order array come first, in the order given; keys present in the map but absent from the order array are appended afterwards in their original relative order; keys in the order array that are not in the map are ignored. An empty or wholly-irrelevant order falls back to the natural sorted order of the keys.",
    "cases": [
        {"input": {"op": "sort_by_array", "map": {"y": "y", "z": "z", "b": "b", "a": "a"}, "order": ["z", "b", "y", "a"]}, "expected_output": "keys=z,b,y,a\nvalues=z,b,y,a\n"},
        {"input": {"op": "sort_by_array", "map": {"y": "y", "z": "z", "b": "b", "a": "a"}, "order": ["z", "b", "y", "a", "c", "x"]}, "expected_output": "keys=z,b,y,a\nvalues=z,b,y,a\n"},
        {"input": {"op": "sort_by_array", "map": {"y": "y", "z": "z", "b": "b", "a": "a"}, "order": ["z", "b"]}, "expected_output": "keys=z,b,a,y\nvalues=z,b,a,y\n"},
        {"input": {"op": "sort_by_array", "map": {"y": "y", "z": "z", "b": "b", "a": "a"}, "order": []}, "expected_output": "keys=a,b,y,z\nvalues=a,b,y,z\n"},
        {"input": {"op": "sort_by_array", "map": {"y": "y", "z": "z", "b": "b", "a": "a"}, "order": ["i", "j", "k"]}, "expected_output": "keys=a,b,y,z\nvalues=a,b,y,z\n"}
    ]
}
```

*7.2 Safe Implode — join mixed scalars without altering numeric formatting*

The input is an optional `glue` (default `,`) and a list of `items`. The adapter renders `result=<joined>`. Each value is converted to its string form verbatim; integers stay as their integer text and values already given as strings (including numeric-looking strings like `1.0`) are emitted unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_safe_implode.json`

```json
{
    "description": "Join a list of mixed scalar values into a single delimited string, converting each value to its string form without altering numeric formatting. The adapter renders 'result=<joined>'. Integers and floats are stringified verbatim (a float like 1.0 keeps its '1.0' form when given as a string and '1' integers stay '1'), and string values are emitted as-is.",
    "cases": [
        {"input": {"op": "safe_implode", "glue": ",", "items": ["s", 1, "1.0", "1.1", "1.0"]}, "expected_output": "result=s,1,1.0,1.1,1.0\n"},
        {"input": {"op": "safe_implode", "glue": "|", "items": ["a", "b", "c"]}, "expected_output": "result=a|b|c\n"}
    ]
}
```

---

### Feature 8: File Path Utilities

**As a developer**, I want helpers to decompose a file path and to classify a reference as local or remote, so I can route uploads and rewrites correctly.

**Expected Behavior / Usage:**

*8.1 Split Path — separate directory, filename, and extension*

The input is a `path`. The adapter renders `dir=<value>`, `filename=<value>`, and `extension=<value>`, using the literal token `<null>` when the directory or extension component is absent. A bare filename has no directory. A name containing no dot at all yields an empty extension (the `extension=` line carries an empty value). Only the final dot segment is treated as the extension, so a name whose dot is embedded in the body keeps the whole body as the filename and reports no extension at all (`<null>`).

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_split_path.json`

```json
{
    "description": "Split a file path into its directory, base filename, and extension. The adapter renders 'dir=<value>', 'filename=<value>', and 'extension=<value>', using the literal token '<null>' when a directory or extension component is absent. A bare filename has no directory; a name with no dot at all yields an empty extension; only the final dot segment is treated as the extension, so a name whose dot is part of the body keeps the whole body as the filename and reports no extension at all (<null>).",
    "cases": [
        {"input": {"op": "split_path", "path": "file.ext"}, "expected_output": "dir=<null>\nfilename=file\nextension=ext\n"},
        {"input": {"op": "split_path", "path": "file"}, "expected_output": "dir=<null>\nfilename=file\nextension=\n"},
        {"input": {"op": "split_path", "path": "file.not_ext"}, "expected_output": "dir=<null>\nfilename=file.not_ext\nextension=<null>\n"},
        {"input": {"op": "split_path", "path": "path/to/file.ext"}, "expected_output": "dir=path/to\nfilename=file\nextension=ext\n"}
    ]
}
```

*8.2 Local vs Remote Classification — detect a remote scheme or data URI*

The input is a `path`. The adapter renders `is_local=true|false`. A reference carrying a recognized remote scheme (`http`, `https`, `ftp`, `s3`, `gs`) or an inline `data:` URI is non-local; any plain filesystem path is local.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_is_local_path.json`

```json
{
    "description": "Classify a file reference as a local filesystem path or a remote/non-local resource. The adapter renders 'is_local=true|false'. References carrying a recognized remote scheme (http, https, ftp, s3, gs) or an inline data URI are treated as non-local; plain filesystem paths are treated as local.",
    "cases": [
        {"input": {"op": "is_local_path", "path": "http://cloudinary.com/images/old_logo.png"}, "expected_output": "is_local=false\n"},
        {"input": {"op": "is_local_path", "path": "https://cloudinary.com/images/old_logo.png"}, "expected_output": "is_local=false\n"},
        {"input": {"op": "is_local_path", "path": "ftp://ftp.cloudinary.com/images/old_logo.png"}, "expected_output": "is_local=false\n"},
        {"input": {"op": "is_local_path", "path": "s3://s3-us-west-2.amazonaws.com/cloudinary/images/old_logo.png"}, "expected_output": "is_local=false\n"},
        {"input": {"op": "is_local_path", "path": "gs://cloudinary/images/old_logo.png"}, "expected_output": "is_local=false\n"},
        {"input": {"op": "is_local_path", "path": "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"}, "expected_output": "is_local=false\n"},
        {"input": {"op": "is_local_path", "path": "/etc/passwd"}, "expected_output": "is_local=true\n"},
        {"input": {"op": "is_local_path", "path": "/usr/local"}, "expected_output": "is_local=true\n"}
    ]
}
```

---

### Feature 9: Connection URL Parsing

**As a developer**, I want to parse a single connection URL into a normalized configuration tree, so I can bootstrap the client from one environment value instead of many separate settings.

**Expected Behavior / Usage:**

The input is a connection `url` of the form `cloudinary://[<api_key>:<api_secret>@]<cloud_name>[/<secure_cname>]`. The adapter renders `config=<json>`. The cloud name always lands under `cloud.cloud_name`; when credentials are present they populate `cloud.api_key` and `cloud.api_secret`; an extra path segment becomes `url.secure_cname` and implies `url.private_cdn=true`. A null or empty URL is rejected as `error=empty_config_url`; a wrong scheme or an otherwise unparseable URL is rejected as `error=invalid_config_url`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_parse_config_url.json`

```json
{
    "description": "Parse a Cloudinary connection URL of the form 'cloudinary://[<api_key>:<api_secret>@]<cloud_name>[/<secure_cname>]' into a normalized configuration tree, rendered as 'config=<json>'. The cloud_name always lands under cloud.cloud_name; when credentials are present they populate cloud.api_key and cloud.api_secret; an extra path segment becomes url.secure_cname and implies url.private_cdn=true. A null/empty URL is rejected as 'error=empty_config_url'; a wrong scheme or an otherwise unparseable URL is rejected as 'error=invalid_config_url'.",
    "cases": [
        {"input": {"op": "parse_config_url", "url": "cloudinary://test123"}, "expected_output": "config={\"cloud\":{\"cloud_name\":\"test123\"}}\n"},
        {"input": {"op": "parse_config_url", "url": "cloudinary://key:secret@test123"}, "expected_output": "config={\"cloud\":{\"cloud_name\":\"test123\",\"api_key\":\"key\",\"api_secret\":\"secret\"}}\n"},
        {"input": {"op": "parse_config_url", "url": "cloudinary://key:secret@test123/secure-dist"}, "expected_output": "config={\"cloud\":{\"cloud_name\":\"test123\",\"api_key\":\"key\",\"api_secret\":\"secret\"},\"url\":{\"secure_cname\":\"secure-dist\",\"private_cdn\":true}}\n"},
        {"input": {"op": "parse_config_url", "url": null}, "expected_output": "error=empty_config_url\n"},
        {"input": {"op": "parse_config_url", "url": "notcloudinary://key:secret@test123"}, "expected_output": "error=invalid_config_url\n"},
        {"input": {"op": "parse_config_url", "url": "cloudinary:///test123"}, "expected_output": "error=invalid_config_url\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the [a list of transformation component strings]-string assembly, layer/overlay encoding, delivery-URL composition, token signing, signature verification, string/array/path utilities, and connection-URL parsing described above. Its physical structure must reflect the multi-responsibility domain (a core source tree with cohesive modules per responsibility) without over-engineering the small utilities.

2. **The Execution/Test Adapter:** A runnable entry point that reads a single JSON command from stdin, dispatches on the `op` field to the appropriate core logic, and prints the result to stdout, strictly matching the per-feature line contracts above (including the normalized `error=<category>` lines). This adapter must be logically and physically separated from the core domain and must not leak host-language exception types, object reprs, or runtime message suffixes.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_[a list of transformation component strings]_qualifiers.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_[a list of transformation component strings]_qualifiers@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains only the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the standard delimiter convention for ellipsis inserts
- use the default IO channel standard for adapters
