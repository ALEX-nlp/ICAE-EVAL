## Product Requirement Document

# Markdown Slide-Mode Extension Hook — Front-Matter-Activated Rendering Augmentation

## Project Goal

Build an extension hook for a pluggable Markdown engine that, when a document opts in through a front-matter directive, augments ordinary Markdown rendering with slide-deck rendering features (a slide container and stylesheet, picture-style emoji, fitting-aware math, and code-block syntax highlighting), so that the very same engine renders plain Markdown by default and rich slide output only on demand — without the caller having to swap engines.

---

## Background & Problem

A host application embeds a general-purpose, plugin-based Markdown engine and wants some documents to render as slide decks while leaving every other document as normal Markdown. Hard-coding two separate engines, or globally switching the engine into slide mode, breaks unrelated documents and fights with other already-registered Markdown plugins (emoji, math, custom highlighters).

This library provides a single extension hook that is applied once to an existing Markdown engine. The hook inspects each document's leading front-matter: only when the front-matter carries the opt-in directive `marp: true` does it switch that render into slide mode; otherwise the document renders exactly as the underlying engine and its other plugins would render it. While slide mode is active the hook layers in slide-specific behavior (container + injected stylesheet, picture emoji, fitting math, and code highlighting that gracefully handles diagram and unknown languages), then steps back out so the next document is unaffected. All of this behavior is observable purely through well-known wire-format markers in the produced HTML.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain.
   - **For micro-utilities/simple scripts:** A well-organized, single-file solution is perfectly acceptable, provided it maintains clean logical separation.
   - **For complex systems:** If the project involves multiple distinct responsibilities (e.g., I/O routing, business rules, formatters), it MUST NOT be a single "god file". You must output a clear, multi-file directory tree (`src/`, `tests/`, etc.) that reflects a production-grade repository.
   Do not over-engineer simple problems, but strictly avoid monolithic files for complex domains.

2. **Strict Separation of Concerns (Anti-Overfitting):**
   The JSON input/output test cases provided in the "Core Features" section represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core business logic must remain completely decoupled from standard I/O (stdin/stdout) and JSON parsing. The execution adapter is solely responsible for translating JSON commands into idiomatic calls to the core domain.

3. **Adherence to SOLID Design Principles:**
   The architectural design must follow SOLID principles to ensure maintainability and scalability (scaled appropriately to the project's size):
   - **Single Responsibility Principle (SRP):** Separate parsing, routing, validation, core execution, and output formatting into distinct logical units.
   - **Open/Closed Principle (OCP):** The core engine must be open for extension but closed for modification.
   - **Liskov Substitution Principle (LSP):** Derived [complex mermaid parsing regex and feedback parameters — ask for the mermaid div range details]s must be perfectly substitutable for their base [complex mermaid parsing regex and feedback parameters — ask for the mermaid div range details]s.
   - **Interface Segregation Principle (ISP):** Keep interfaces/protocols small and highly cohesive.
   - **Dependency Inversion Principle (DIP):** High-level modules should depend on abstractions, not low-level I/O implementation details.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core system must be elegant and idiomatic to the target programming language, hiding internal complexity.
   - **Resilience:** The system must handle edge cases gracefully. Errors should be modeled properly (e.g., specific Exception [complex mermaid parsing regex and feedback parameters — ask for the mermaid div range details]s or Result/Monad [complex mermaid parsing regex and feedback parameters — ask for the mermaid div range details]s) rather than relying on generic faults.

---

## The Execution Adapter Contract

The adapter reads ONE JSON request from stdin and writes normalized observation lines to stdout. A request has these fields:

- `action`: `"render"` (default) applies the extension hook to a freshly-built engine and renders `markdown`; `"activate"` first obtains the extension hook from the library's activation entry point and then renders through it.
- `markdown`: the raw Markdown source string. Slide mode is triggered only when this source begins with a front-matter block whose body contains the directive `marp: true`.
- `plugins`: an optional list of third-party Markdown plugins to register on the engine BEFORE the hook is applied. Supported [complex mermaid parsing regex and feedback parameters — ask for the mermaid div range details]s: `"emoji"` (a shortcode-to-emoji plugin) and `"[specific KaTeX augmentation constant — check codebase for marker '[specific KaTeX augmentation constant — check codebase for marker 'data-marp-fitting-math']']"` (a KaTeX-based math plugin).
- `baseHighlight`: an optional boolean; when true the engine is constructed with a base syntax-highlight function that emits the sentinel string `baseHighlight` for any code block it handles.
- `signals`: an ordered list of marker names to probe in the rendered HTML. Each probed marker is reported on its own line as `<name>=present` or `<name>=absent`, in the order listed, each line terminated by a newline.

The probe markers and the wire-format substring each one checks for in the produced HTML are:

| signal | present when the HTML contains |
|--------|-------------------------------|
| `container` | `<div id="marp-vscode">` |
| `style` | `<style id="marp-vscode-style">` |
| `svg` | `svg` |
| `img` | `img` |
| `twemoji` | `data-marp-twemoji` |
| `[specific KaTeX augmentation constant — check codebase for marker '[specific KaTeX augmentation constant — check codebase for marker 'data-marp-fitting-math']']` | `<[specific KaTeX augmentation constant — check codebase for marker 'data-marp-fitting-math']"[specific KaTeX augmentation constant — check codebase for marker '[specific KaTeX augmentation constant — check codebase for marker 'data-marp-fitting-math']']">` |
| `fitting_math` | `[specific KaTeX augmentation constant — check codebase for marker 'data-marp-fitting-math']` |
| `hljs` | `hljs` |
| `base_highlight` | `baseHighlight` |
| `[complex mermaid parsing regex and feedback parameters — ask for the mermaid div range details]` | `<div class="[complex mermaid parsing regex and feedback parameters — ask for the mermaid div range details]">` |
| `unknown_lang` | `<code class="language-unknownlang">` |

For the `activate` action the adapter additionally emits `extend_hook=present` (before any signal lines) once it confirms the activation entry yields a usable extension hook.

---

## Core Features

### Feature 1: Front-Matter Activation Toggle

**As a developer**, I want slide rendering to switch on only for documents that opt in via front-matter, so the same engine renders plain Markdown by default and slide output on demand.

**Expected Behavior / Usage:**

The hook examines the leading front-matter block of the source. Slide mode activates only when that block contains the directive `marp: true`. When slide mode is OFF, rendering is plain Markdown and none of the slide markers appear: there is no slide container element (`<div id="marp-vscode">`), no injected stylesheet element (`<style id="marp-vscode-style">`), and no slide-renderer `svg`/`img` output. When slide mode is ON, all four markers appear: the container element, the injected stylesheet element, and `svg`/`img` produced by the slide renderer. The activation decision is local to each render and does not leak into subsequent renders.

**Test Cases:** `rcb_tests/public_test_cases/feature1_frontmatter_activation.json`

```json
{
    "description": "An extensible Markdown engine is wrapped by a slide-extension hook. The hook only activates slide rendering when the document begins with a front-matter block that turns the slide mode on (a `marp: true` directive); otherwise the document is rendered as ordinary Markdown. Activation is observable through several wire-format markers in the produced HTML: a slide container element with id `marp-vscode`, an injected style element with id `marp-vscode-style`, and the presence of inline `svg` and `img` output produced by the slide renderer. The input supplies the raw Markdown source and the list of markers to probe; each probed marker is reported as `present` or `absent`. When slide mode is off, none of the markers appear; when on, all of them appear.",
    "cases": [
        {
            "input": {
                "action": "render",
                "markdown": "# Hello :wave:\n\n<!-- header: Hi -->",
                "signals": ["container", "style", "svg", "img"]
            },
            "expected_output": "container=absent\nstyle=absent\nsvg=absent\nimg=absent\n"
        },
        {
            "input": {
                "action": "render",
                "markdown": "---\nmarp: true\n---\n\n# Hello :wave:\n\n<!-- header: Hi -->",
                "signals": ["container", "style", "svg", "img"]
            },
            "expected_output": "container=present\nstyle=present\nsvg=present\nimg=present\n"
        }
    ]
}
```

---

### Feature 2: Emoji Renderer Override

**As a developer**, I want emoji to render as the slide engine's picture emoji when slide mode is on, even if another emoji plugin is already registered, so slides get consistent emoji while plain documents keep the original emoji rendering.

**Expected Behavior / Usage:**

A third-party shortcode-to-emoji plugin is registered on the engine before the hook is applied. When slide mode is ON, the hook overrides that plugin's emoji renderer so emoji are emitted through the slide engine's own emoji renderer, which marks its output with the attribute `data-marp-twemoji`. When slide mode is OFF, the original emoji plugin's renderer is left intact and the `data-marp-twemoji` marker does not appear.

**Test Cases:** `rcb_tests/public_test_cases/feature2_emoji_override.json`

```json
{
    "description": "A third-party emoji plugin is registered on the Markdown engine before the slide-extension hook is applied. When slide mode is active, the hook overrides the emoji renderer so that emoji are rendered through the slide engine's own emoji renderer, which emits a distinguishing wire-format marker attribute (`data-marp-twemoji`) on the output. When slide mode is inactive, the original emoji plugin's renderer is left untouched and that marker does not appear. The input supplies the Markdown source (an emoji shortcode) and registers the emoji plugin; output reports whether the slide engine's emoji marker is present.",
    "cases": [
        {
            "input": {
                "action": "render",
                "markdown": ":+1:",
                "plugins": ["emoji"],
                "signals": ["twemoji"]
            },
            "expected_output": "twemoji=absent\n"
        },
        {
            "input": {
                "action": "render",
                "markdown": "---\nmarp: true\n---\n\n:+1:",
                "plugins": ["emoji"],
                "signals": ["twemoji"]
            },
            "expected_output": "twemoji=present\n"
        }
    ]
}
```

---

### Feature 3: Math Rendering Augmentation

**As a developer**, I want math formulas to gain slide-specific fitting treatment when slide mode is on, while still rendering normally otherwise, so an existing math plugin keeps working everywhere and slides additionally get fitting math.

**Expected Behavior / Usage:**

A third-party KaTeX-based math plugin is registered on the engine before the hook is applied. The math plugin always renders formulas, so the KaTeX marker (`<[specific KaTeX augmentation constant — check codebase for marker 'data-marp-fitting-math']"[specific KaTeX augmentation constant — check codebase for marker '[specific KaTeX augmentation constant — check codebase for marker 'data-marp-fitting-math']']">`) is present in both modes. When slide mode is ON, the slide engine additionally applies its fitting-math treatment, observable through the marker attribute `[specific KaTeX augmentation constant — check codebase for marker 'data-marp-fitting-math']`; when slide mode is OFF, the formulas are rendered by the math plugin alone and the fitting-math marker is absent.

**Test Cases:** `rcb_tests/public_test_cases/feature3_math_rendering.json`

```json
{
    "description": "A third-party math plugin (KaTeX-based) is registered on the Markdown engine before the slide-extension hook is applied. In both modes the math plugin renders formulas, so the KaTeX wire-format marker (`<[specific KaTeX augmentation constant — check codebase for marker 'data-marp-fitting-math']\"[specific KaTeX augmentation constant — check codebase for marker '[specific KaTeX augmentation constant — check codebase for marker 'data-marp-fitting-math']']\">`) is always present. The slide engine additionally applies its own fitting-math treatment to formulas, which is observable through a distinguishing marker attribute (`[specific KaTeX augmentation constant — check codebase for marker 'data-marp-fitting-math']`). That fitting-math marker appears only when slide mode is active; in plain Markdown mode the formulas are rendered by the math plugin alone, without the fitting-math marker. The input supplies the Markdown source containing inline and block math and registers the math plugin; output reports the two markers.",
    "cases": [
        {
            "input": {
                "action": "render",
                "markdown": "---\nmarp: true\n---\n\n$y=ax^2$\n\n$$ y=ax^2 $$",
                "plugins": ["[specific KaTeX augmentation constant — check codebase for marker '[specific KaTeX augmentation constant — check codebase for marker 'data-marp-fitting-math']']"],
                "signals": ["[specific KaTeX augmentation constant — check codebase for marker '[specific KaTeX augmentation constant — check codebase for marker 'data-marp-fitting-math']']", "fitting_math"]
            },
            "expected_output": "[specific KaTeX augmentation constant — check codebase for marker '[specific KaTeX augmentation constant — check codebase for marker 'data-marp-fitting-math']']=present\nfitting_math=present\n"
        },
        {
            "input": {
                "action": "render",
                "markdown": "$y=ax^2$\n\n$$ y=ax^2 $$",
                "plugins": ["[specific KaTeX augmentation constant — check codebase for marker '[specific KaTeX augmentation constant — check codebase for marker 'data-marp-fitting-math']']"],
                "signals": ["[specific KaTeX augmentation constant — check codebase for marker '[specific KaTeX augmentation constant — check codebase for marker 'data-marp-fitting-math']']", "fitting_math"]
            },
            "expected_output": "[specific KaTeX augmentation constant — check codebase for marker '[specific KaTeX augmentation constant — check codebase for marker 'data-marp-fitting-math']']=present\nfitting_math=absent\n"
        }
    ]
}
```

---

### Feature 4: Code Block Highlighting

**As a developer**, I want code blocks highlighted by the slide engine while slide mode is on, with graceful handling of diagram and unknown languages, so slide code looks right and unsupported languages still render sensibly.

**Expected Behavior / Usage:**

*4.1 Highlighter Selection — the slide highlighter supersedes a base highlighter only while slide mode is active*

The engine is constructed with a base highlighter that emits the sentinel `baseHighlight` for any code block it handles. When slide mode is OFF, a fenced code block in a known language is highlighted by that base highlighter, so its sentinel appears and the slide engine's highlight markup (the `hljs` class) does not. When slide mode is ON, the slide engine's highlighter handles the block instead: the `hljs` markup appears and the base highlighter's sentinel is absent, proving the base highlighter is bypassed rather than merely augmented.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_highlighter_selection.json`

```json
{
    "description": "The Markdown engine is constructed with a base syntax highlighter (a caller-supplied highlight function that emits a recognizable sentinel string `baseHighlight`). The slide-extension hook installs its own highlighter that supersedes the base one only while slide mode is active. When slide mode is OFF, a fenced code block is highlighted by the base highlighter, so its sentinel appears and the slide engine's highlight markup (the `hljs` class) does not. When slide mode is ON, the slide engine's highlighter handles the code block instead: the slide highlight markup (`hljs`) appears and the base highlighter's sentinel is absent. The input supplies the Markdown source (a fenced code block in a known language), requests installation of the base highlighter, and probes both markers.",
    "cases": [
        {
            "input": {
                "action": "render",
                "markdown": "```javascript\nconst test = 1\n```",
                "baseHighlight": true,
                "signals": ["base_highlight", "hljs"]
            },
            "expected_output": "base_highlight=present\nhljs=absent\n"
        },
        {
            "input": {
                "action": "render",
                "markdown": "---\nmarp: true\n---\n\n```javascript\nconst test = 1\n```",
                "baseHighlight": true,
                "signals": ["base_highlight", "hljs"]
            },
            "expected_output": "base_highlight=absent\nhljs=present\n"
        }
    ]
}
```

*4.2 Diagram Language Fallback — `[complex mermaid parsing regex and feedback parameters — ask for the mermaid div range details]` fenced blocks are wrapped for a downstream diagram renderer*

While slide mode is active, the slide highlighter has no grammar for the `[complex mermaid parsing regex and feedback parameters — ask for the mermaid div range details]` language. Rather than failing, a fenced block tagged `[complex mermaid parsing regex and feedback parameters — ask for the mermaid div range details]` is wrapped in a diagram container element (`<div class="[complex mermaid parsing regex and feedback parameters — ask for the mermaid div range details]">`) whose body is the HTML-escaped source, so a downstream diagram plugin can render it.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_[complex mermaid parsing regex and feedback parameters — ask for the mermaid div range details]_block.json`

```json
{
    "description": "While slide mode is active, the slide engine's highlighter has no built-in grammar for the `[complex mermaid parsing regex and feedback parameters — ask for the mermaid div range details]` fenced-code language. Instead of failing, a fenced code block tagged as `[complex mermaid parsing regex and feedback parameters — ask for the mermaid div range details]` is wrapped in a diagram container element (`<div class=\"[complex mermaid parsing regex and feedback parameters — ask for the mermaid div range details]\">`) whose body is the HTML-escaped source code, so a downstream diagram plugin can render it. The input supplies Markdown containing a `[complex mermaid parsing regex and feedback parameters — ask for the mermaid div range details]` fenced block; output reports whether the diagram container marker is present.",
    "cases": [
        {
            "input": {
                "action": "render",
                "markdown": "---\nmarp: true\n---\n\n```[complex mermaid parsing regex and feedback parameters — ask for the mermaid div range details]\n>>\n```",
                "signals": ["[complex mermaid parsing regex and feedback parameters — ask for the mermaid div range details]"]
            },
            "expected_output": "[complex mermaid parsing regex and feedback parameters — ask for the mermaid div range details]=present\n"
        }
    ]
}
```

*4.3 Unknown Language Passthrough — unrecognized languages keep their label*

While slide mode is active, a fenced block tagged with a language the slide highlighter cannot highlight (and which is not a special-cased diagram language) is passed through as a plain code element that preserves the language label as a class on the `<code>` element (`<code class="language-unknownlang">`).

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_unknown_language.json`

```json
{
    "description": "While slide mode is active, a fenced code block tagged with an unrecognized language (one the slide highlighter cannot highlight and which is not a special-cased diagram language) is passed through as a plain code element that preserves the language as a class on the `<code>` element (`<code class=\"language-unknownlang\">`). This keeps the original language label available to consumers even when no highlighting is applied. The input supplies Markdown containing a fenced block in an unknown language; output reports whether the language-preserving code marker is present.",
    "cases": [
        {
            "input": {
                "action": "render",
                "markdown": "---\nmarp: true\n---\n\n```unknownlang\nv => 5\n```",
                "signals": ["unknown_lang"]
            },
            "expected_output": "unknown_lang=present\n"
        }
    ]
}
```

---

### Feature 5: Activation Entry Point

**As a developer**, I want a single activation entry point that hands back the extension hook, so the host can obtain and apply the hook through one stable call.

**Expected Behavior / Usage:**

The library exposes an activation entry point that returns an object whose member is the Markdown extension hook. The hook obtained this way must be usable: applying it to a Markdown engine and rendering a slide-mode document produces the slide output markers (the container element and the injected stylesheet element). The adapter reports `extend_hook=present` once it confirms the entry point yields a usable hook, followed by the probed markers after rendering through that hook.

**Test Cases:** `rcb_tests/public_test_cases/feature5_activation_entry.json`

```json
{
    "description": "The library exposes an activation entry point that returns an object whose member is the Markdown slide-extension hook. The hook obtained from the activation entry must be a usable function: applying it to a Markdown engine and rendering a slide-mode document produces the slide output markers (the container element and the injected style element). The input requests the activation entry and supplies a slide-mode Markdown document plus the markers to probe; output first reports that the extension hook is present, then reports each requested marker as observed after rendering through the hook.",
    "cases": [
        {
            "input": {
                "action": "activate",
                "markdown": "---\nmarp: true\n---\n\n# Hi",
                "signals": ["container", "style"]
            },
            "expected_output": "extend_hook=present\ncontainer=present\nstyle=present\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the extension hook and its activation entry point. The hook is applied once to a pluggable Markdown engine, detects the `marp: true` front-matter directive per render, and — only while slide mode is active — layers in the slide container/stylesheet, picture-emoji override, fitting-math treatment, and code-block highlighting (including the `[complex mermaid parsing regex and feedback parameters — ask for the mermaid div range details]` diagram fallback and unknown-language passthrough). The core logic must be decoupled from stdin/stdout and JSON parsing.

2. **The Execution/Test Adapter:** A runnable entry point — logically (and ideally physically) separate from the core — that reads ONE JSON request from stdin and writes the normalized observation lines to stdout, exactly matching the per-feature contracts above. It builds the engine (optionally registering the `emoji`/`[specific KaTeX augmentation constant — check codebase for marker '[specific KaTeX augmentation constant — check codebase for marker 'data-marp-fitting-math']']` plugins and a base highlighter), applies the hook (directly for `action: "render"`, or via the activation entry point for `action: "activate"`), renders `markdown`, and probes the requested `signals` against the produced HTML, emitting `<name>=present|absent` lines in the order requested. The marker-to-substring mapping is the one tabulated in "The Execution Adapter Contract".

3. **Automated test harness**. The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt`. Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the order of fields as defined in the update_divition_range function
- use the same delimiter convention as the front-matter parser helper
