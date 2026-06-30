## Product Requirement Document

# Developer Profile Stat Card Toolkit — SVG Card Rendering, Rank Scoring & Formatting Helpers

## Project Goal

Build a reusable toolkit that turns a developer's account and repository data into compact, self-contained SVG "stat cards" (a profile statistics summary, a top-languages breakdown, and a single-repository summary), backed by a small set of pure formatting and color-resolution helpers and a contributor-rank scoring function, so that any service can embed an at-a-glance, theme-able visual summary without re-implementing number formatting, HTML escaping, color/theme resolution, or SVG layout.

---

## Background & Problem

Services that want to show a developer's activity as an embeddable image must repeatedly solve the same sub-problems: abbreviating large counts (e.g. star totals) into short tokens, escaping arbitrary text safely into markup, resolving a final color from a user override or a named theme palette, laying out a list of elements with even spacing, scoring overall activity into a comparable rank, and assembling all of this into valid SVG whose observable text and attributes are stable and predictable.

Without a shared toolkit, each service hand-rolls these pieces, producing inconsistent output, subtle formatting bugs, and cards that are hard to test. This toolkit provides one well-defined contract for each piece: deterministic pure helpers, a deterministic rank score, and three card renderers whose observable output (rendered text, geometry, resolved colors, and per-element attributes) is fully specified.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST perfectly match the complexity of the domain. This domain has several distinct responsibilities (pure formatting helpers, color/theme resolution, rank scoring, and three independent card renderers), so it MUST NOT be a single "god file"; output a clear, multi-file directory tree that reflects a production-grade repository. Do not over-engineer, but strictly avoid a monolith.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below represent a **black-box testing contract** for the execution adapter, NOT the internal data model of the core system. The core logic (helpers, scorer, renderers) must remain completely decoupled from standard I/O and JSON parsing. The execution adapter alone translates a JSON request into idiomatic calls to the core.

3. **Adherence to SOLID Design Principles:** Separate parsing/routing, the pure helpers, the rank scorer, and each renderer into distinct cohesive units; the renderers should share the color-resolution and layout helpers rather than duplicating them.

4. **Robustness & Interface Design:** The public interface must be idiomatic to the target language and hide internal complexity. Inputs with optional fields must degrade gracefully (missing options take documented defaults; invalid color overrides fall back; absent data is omitted rather than rendered as blanks).

---

## Execution Adapter I/O Contract (applies to every feature)

The execution adapter reads exactly **one JSON object** from standard input and writes the result to standard output. The object always carries a string field `op` naming the requested operation; the remaining fields are that operation's data. Output is **raw text only** (no status words, no metadata).

For operations whose result is a single scalar token (the formatting helpers), the adapter prints that token followed by a single trailing newline. For operations whose result is a set of named signals (color resolution, rank scoring, and the three card renderers), the adapter prints one `key=value` line per signal, the lines **sorted in ascending order by key**, each terminated by a newline. A value that is absent or not applicable is rendered with a documented placeholder token (e.g. `[value when stargazers count is zero]` or `<none>`). These exact key sets, ordering, and placeholder tokens are part of the contract and are shown in each feature's cases below.

**Shared color/theme model (referenced by several features):** A "valid hex color" is a string of exactly 3, 4, 6, or 8 hexadecimal digits with no leading hash. Named themes provide four colors — `title`, `icon`, `text`, `bg`. The palettes referenced by the cases in this document are:

- `default` → title `2f80ed`, icon `4c71f2`, text `333`, bg `FFFEFE`
- `default_repocard` → title `2f80ed`, icon `586069`, text `333`, bg `FFFEFE`
- `dark` → title `fff`, icon `79ff97`, text `9f9f9f`, bg `151515`
- `radical` → title `fe428e`, icon `f8d847`, text `a9fef7`, bg `141321`

---

## Core Features

### Feature 1: Compact Number Abbreviation

**As a developer**, I want large counts shortened to a compact token, so totals fit neatly on a card without overflowing.

**Expected Behavior / Usage:**

The input is a signed integer `value`. If its magnitude is greater than 999, the result is the value divided by 1000, fixed to one decimal place, with the original sign preserved, followed by a lowercase `k` suffix (so 12345 becomes `12.3k`, and 9900000 becomes `9900k`). If the magnitude is 999 or less, the result is the plain integer (sign preserved). The output is the resulting token as a string on its own line.

**Test Cases:** `rcb_tests/public_test_cases/feature1_number_abbreviation.json`

```json
{
  "description": "Abbreviate a signed integer for compact display. Magnitudes of one thousand or greater are rendered with one decimal place of thousands followed by a lowercase 'k' suffix (with the sign preserved); smaller magnitudes are rendered as the plain integer. The output is the abbreviated token as a string.",
  "cases": [
    {"input": {"op": "abbreviate_number", "value": 500}, "expected_output": "500\n"},
    {"input": {"op": "abbreviate_number", "value": 12345}, "expected_output": "12.3k\n"}
  ]
}
```

---

### Feature 2: HTML Entity Escaping

**As a developer**, I want arbitrary text escaped before it is embedded in markup, so user-supplied strings cannot break or inject into the rendered document.

**Expected Behavior / Usage:**

The input is a raw `text` string. Every character that is markup-significant or non-ASCII (angle brackets, ampersand, double quote, and any character in the upper code-point range), when it is not already the start of a numeric entity, is replaced by its decimal numeric character reference of the form `&#<code>;` (where `<code>` is the character's code point). Ordinary printable ASCII characters pass through unchanged. The output is the escaped string on its own line.

**Test Cases:** `rcb_tests/public_test_cases/feature2_html_escape.json`

```json
{
  "description": "Escape a raw text string so it is safe to embed inside markup. Each angle bracket, ampersand, double quote and other non-ASCII/markup-significant character (when not already part of a numeric entity) is replaced by its decimal numeric character reference of the form &#<code>;. Ordinary printable ASCII characters are passed through unchanged. The output is the escaped string.",
  "cases": [
    {"input": {"op": "escape_html", "text": "<html>hello world<,.#4^&^@%!))"}, "expected_output": "&#60;html&#62;hello world&#60;,.#4^&#38;^@%!))\n"}
  ]
}
```

---

### Feature 3: Evenly Spaced Layout Grouping

**As a developer**, I want a list of pre-rendered markup fragments wrapped into evenly offset positioned groups, so I can lay items out in a row or a column without manually computing each offset.

**Expected Behavior / Usage:**

The input supplies `items` (an array of markup fragment strings), a numeric `gap`, and an optional `direction`. Each non-empty fragment is wrapped in a group element bearing a `translate(...)` transform; the i-th kept fragment is offset by `gap * i`. The offset is applied along the x-axis by default, or along the y-axis when `direction` is `"column"`. Empty-string fragments are filtered out before indexing. The output is the concatenation, in order, of the wrapped group elements on a single line.

**Test Cases:** `rcb_tests/public_test_cases/feature3_layout_group.json`

```json
{
  "description": "Wrap a list of already-rendered markup fragments into evenly spaced positioned groups. Each fragment is wrapped in a group element carrying a translate transform; successive fragments are offset by a fixed gap either horizontally (default) or vertically when a column direction is requested. Empty-string fragments are dropped. The output is the concatenation of the wrapped groups in order.",
  "cases": [
    {"input": {"op": "layout_group", "items": ["<text>1</text>", "<text>2</text>"], "gap": 60}, "expected_output": "<g transform=\"translate(0, 0)\"><text>1</text></g><g transform=\"translate(60, 0)\"><text>2</text></g>\n"},
    {"input": {"op": "layout_group", "items": ["<text>1</text>", "<text>2</text>"], "gap": 60, "direction": "column"}, "expected_output": "<g transform=\"translate(0, 0)\"><text>1</text></g><g transform=\"translate(0, 60)\"><text>2</text></g>\n"}
  ]
}
```

---

### Feature 4: Theme & Color Resolution

**As a developer**, I want the final title/icon/text/background colors resolved from optional per-field overrides and a named theme, so cards honor user choices while always falling back to a sensible palette.

**Expected Behavior / Usage:**

The input carries optional overrides `title_color`, `text_color`, `icon_color`, `bg_color` and an optional `theme`. For each of the four fields, the resolved color is the user override when that override is a valid hex color, emitted with a leading `#`. If the override is missing or invalid, the named theme's color for that field is used (also emitted with a leading `#`); if the theme is unknown, or the theme's value for the field is itself invalid, the field falls back to the `default` theme's color. The output lists the four resolved colors as `bgColor`, `iconColor`, `textColor`, `titleColor` (one `key=value` line each, sorted by key). See the shared palettes above (`dark` resolves to bg `#151515`, icon `#79ff97`, text `#9f9f9f`, title `#fff`).

**Test Cases:** `rcb_tests/public_test_cases/feature4_resolve_colors.json`

```json
{
  "description": "Resolve the four card colors (title, icon, text, background) from optional per-field user overrides and a named theme. A user override is honored only when it is a valid hex color (3/4/6/8 hex digits, no leading hash), in which case it is emitted prefixed with a hash; an invalid override is discarded. When no valid override is given for a field, the named theme's color for that field is used; if the named theme is unknown or its color is also invalid, the field falls back to the default theme's color. The output lists the four resolved colors.",
  "cases": [
    {"input": {"op": "resolve_colors", "title_color": "f00", "text_color": "0f0", "icon_color": "00f", "bg_color": "fff", "theme": "dark"}, "expected_output": "bgColor=#fff\niconColor=#00f\ntextColor=#0f0\ntitleColor=#f00\n"},
    {"input": {"op": "resolve_colors", "theme": "dark"}, "expected_output": "bgColor=#151515\niconColor=#79ff97\ntextColor=#9f9f9f\ntitleColor=#fff\n"}
  ]
}
```

---

### Feature 5: Error Card Message Embedding

**As a developer**, I want a short error message rendered into a small card, so failures are surfaced visually in the same medium as the data cards.

**Expected Behavior / Usage:**

The input is a `message` string. The renderer produces an error card containing a dedicated message element that carries the supplied text and a small-text styling class. The output reports that element's styling class and its text content, as the `key=value` lines `class` and `text` (sorted by key).

**Test Cases:** `rcb_tests/public_test_cases/feature5_error_card.json`

```json
{
  "description": "Render an error card from a short human-readable message and report the message element that carries the supplied text. The output names the styling class applied to the message element and the message text it contains.",
  "cases": [
    {"input": {"op": "error_card", "message": "Something went wrong"}, "expected_output": "class=text small\ntext=Something went wrong\n"}
  ]
}
```

---

### Feature 6: Contributor Rank Scoring

**As a developer**, I want a single comparable rank computed from a contributor's activity metrics, so accounts can be ranked consistently.

**Expected Behavior / Usage:**

The input supplies seven metrics: `totalRepos`, `totalCommits`, `contributions`, `followers`, `prs`, `issues`, and `stargazers`. These are combined into a weighted score (each metric has its own fixed weight), the score is normalized against a fixed reference distribution into a 0–100 percentile, and the percentile is mapped to a discrete rank level by fixed threshold bands (lower percentile values denote stronger ranks; the level strings include `S+`, `S`, `A++`, `A+`, and `B+`). The output reports the rank `level` and the exact normalized numeric `score` as two `key=value` lines (sorted by key); the score is the full-precision number.

**Test Cases:** `rcb_tests/public_test_cases/feature6_rank_score.json`

```json
{
  "description": "Compute a contributor's rank from seven activity metrics (total repositories, total commits, contributions, followers, pull requests, issues, and stargazers). The metrics are combined into a weighted score, normalized against a reference distribution into a 0-100 percentile, and mapped to a discrete rank level by threshold bands. The output reports the rank level and the exact normalized numeric score.",
  "cases": [
    {"input": {"op": "score_rank", "totalCommits": 100, "totalRepos": 5, "followers": 100, "contributions": 61, "stargazers": 400, "prs": 300, "issues": 200}, "expected_output": "level=A+\nscore=49.16605417270399\n"}
  ]
}
```

---

### Feature 7: Profile Statistics Summary Card

**As a developer**, I want a summary card of a contributor's headline totals and rank, so a profile can show an at-a-glance activity overview.

**Expected Behavior / Usage:**

The input supplies a `stats` object (`name`, `totalStars`, `totalCommits`, `totalIssues`, `totalPRs`, `contributedTo`, and a precomputed `rank` object with `level` and `score`) and an optional `options` object. The card renders a title of the form `<name>'s GitHub Stats`, where the possessive suffix is just an apostrophe when the name ends in `x` or `s` and `'s` otherwise; one row per stat showing its value (large values abbreviated per Feature 1); a rank circle; and a bordered background. Default colors come from the `default` theme (header `#2f80ed`, stat text `#333`, icon `#4c71f2`, background `#FFFEFE`).

Options: `hide` is a list of stat keys (`stars`, `commits`, `issues`, `prs`, `contribs`) to omit; `hide_title` removes the title and shifts the body group up by 30 (and reduces height); `hide_border` toggles the background stroke opacity between `1` (shown) and `0` (hidden); `hide_rank` removes the rank circle; `show_icons` adds one icon per stat and shifts the stat label to x `25`; and the color override/theme fields from Feature 4 apply. The card height is computed from the number of visible stats but clamped to a minimum of [specific height values based on stat count] while the rank circle is shown (the default full card is height `[specific height values based on stat count]`; hiding three stats clamps it to `[specific height values based on stat count]`).

The output reports these sorted `key=value` signals: `body_transform` (the body group's transform), `card_bg_fill`, `card_bg_stroke_opacity`, `header` (the title text or `<none>`), `height`, `icon_count` (number of stat icons), `rank_circle` (`present`/`absent`), `stat_stars`/`stat_commits`/`stat_issues`/`stat_prs`/`stat_contribs` (each the rendered value or `[value when stargazers count is zero]` when hidden), `stars_label_x` (the stat label's x attribute or `<none>`), and the resolved `style_header_fill`/`style_stat_fill`/`style_icon_fill`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_stats_card.json`

```json
{
  "description": "Render a profile statistics summary card from a stats object (display name, totals for stars, commits, issues, pull requests and items contributed to, plus a precomputed rank object) and an options object. The card shows a title built from the name (with a correct possessive apostrophe), one row per non-hidden stat value, a rank badge circle, a bordered background, and theme/override-driven colors; options can hide individual stats, hide the title, hide the border, hide the rank circle, toggle stat icons, and select colors. The output reports the externally observable signals: rendered title, card height, per-stat rendered values (or absence), background fill and border opacity, rank-circle presence, icon count, the stat-label x position, the body group transform, and the resolved header/stat/icon style colors.",
  "cases": [
    {"input": {"op": "stats_card", "stats": {"name": "Jane Doe", "totalStars": 100, "totalCommits": 200, "totalIssues": 300, "totalPRs": 400, "contributedTo": 500, "rank": {"level": "A+", "score": 40}}}, "expected_output": "body_transform=translate(0, 0)\ncard_bg_fill=#FFFEFE\ncard_bg_stroke_opacity=1\nheader=Jane Doe's GitHub Stats\nheight=[specific height values based on stat count]\nicon_count=0\nrank_circle=present\nstat_commits=200\nstat_contribs=500\nstat_issues=300\nstat_prs=400\nstat_stars=100\nstars_label_x=<none>\nstyle_header_fill=#2f80ed\nstyle_icon_fill=#4c71f2\nstyle_stat_fill=#333\n"},
    {"input": {"op": "stats_card", "stats": {"name": "Jane Doe", "totalStars": 100, "totalCommits": 200, "totalIssues": 300, "totalPRs": 400, "contributedTo": 500, "rank": {"level": "A+", "score": 40}}, "options": {"hide": ["issues", "prs", "contribs"]}}, "expected_output": "body_transform=translate(0, 0)\ncard_bg_fill=#FFFEFE\ncard_bg_stroke_opacity=1\nheader=Jane Doe's GitHub Stats\nheight=[specific height values based on stat count]\nicon_count=0\nrank_circle=present\nstat_commits=200\nstat_contribs=[value when stargazers count is zero]\nstat_issues=[value when stargazers count is zero]\nstat_prs=[value when stargazers count is zero]\nstat_stars=100\nstars_label_x=<none>\nstyle_header_fill=#2f80ed\nstyle_icon_fill=#4c71f2\nstyle_stat_fill=#333\n"}
  ]
}
```

---

### Feature 8: Top Languages Card

**As a developer**, I want a card that breaks down languages by share of code, so a profile can show what someone works in most.

**Expected Behavior / Usage:**

The input supplies a `languages` map (each entry has a `name`, a `color`, and a numeric `size`) and an optional `options` object. Languages are sorted by descending `size`; any names listed in `options.hide` are removed (matched case-insensitively, trimmed); each remaining language gets a row showing its name and a progress bar whose width percentage is its `size` divided by the total size of the visible languages, formatted to two decimals (so two equal-largest of three languages each render `40.00%`-class shares — note the bar widths reported are the clamped progress percentages, e.g. `40%`,`40%`,`20%`). The card height is `45 + (count + 1) * 40`, reduced by 30 when the title is hidden; the title element reads `Top Languages` and is omitted when `hide_title` is true; the language-items group sits at y `55` with the title and y `25` without it; width defaults to `300` and is overridable via `card_width`; and colors follow Feature 4 (default theme: header `#2f80ed`, label `#333`, background `#FFFEFE`).

The output reports these sorted `key=value` signals: `card_bg_fill`, `header` (the `Top Languages` text or `<none>`), `height`, `lang_items_y`, `lang_names` (the ordered, comma-joined visible names), `lang_progress` (the ordered, comma-joined progress-bar width attributes), `style_header_fill`, `style_langname_fill`, and `width`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_languages_card.json`

```json
{
  "description": "Render a top-languages card from a map of languages (each with a display name, a color and a byte size) and an options object. Languages are ordered by descending size; any names listed in the hide option are removed (case-insensitively); each remaining language shows its name and a progress bar whose width percentage is its share of the total size (clamped to a minimum). The card height grows with the number of languages, the title can be hidden, the card width is configurable, and colors come from overrides or a named theme. The output reports the rendered header (or its absence), card width and height, the language items group y offset, the ordered language names, the ordered progress-bar widths, the background fill, and the resolved header/label style colors.",
  "cases": [
    {"input": {"op": "languages_card", "languages": {"HTML": {"color": "#0f0", "name": "HTML", "size": 200}, "javascript": {"color": "#0ff", "name": "javascript", "size": 200}, "css": {"color": "#ff0", "name": "css", "size": 100}}}, "expected_output": "card_bg_fill=#FFFEFE\nheader=Top Languages\nheight=205\nlang_items_y=55\nlang_names=HTML,javascript,css\nlang_progress=40%,40%,20%\nstyle_header_fill=#2f80ed\nstyle_langname_fill=#333\nwidth=300\n"},
    {"input": {"op": "languages_card", "languages": {"HTML": {"color": "#0f0", "name": "HTML", "size": 200}, "javascript": {"color": "#0ff", "name": "javascript", "size": 200}, "css": {"color": "#ff0", "name": "css", "size": 100}}, "options": {"hide": ["HTML"]}}, "expected_output": "card_bg_fill=#FFFEFE\nheader=Top Languages\nheight=165\nlang_items_y=55\nlang_names=javascript,css\nlang_progress=66.67%,33.33%\nstyle_header_fill=#2f80ed\nstyle_langname_fill=#333\nwidth=300\n"}
  ]
}
```

---

### Feature 9: Repository Summary Card

**As a developer**, I want a single-repository card with its name, description, language and counts, so a repo can be pinned visually.

**Expected Behavior / Usage:**

The input supplies a `repo` object (`name`, `nameWithOwner`, `description`, `primaryLanguage` with `name`/`color`, `stargazers` with `totalCount`, `forkCount`, and optional `isArchived`/`isTemplate` flags) and an optional `options` object. The header is the bare `name` by default, or `nameWithOwner` when `options.show_owner` is true. The description is escaped (Feature 2) and trimmed to 55 characters with a trailing `..` when longer. The primary-language indicator shows the language name and a colored dot; when `primaryLanguage` is null the indicator is omitted, and when it is present but its name/color are null the label is `Unspecified` with color `#333`. Star and fork counts are each shown only when greater than zero, abbreviated per Feature 1 (so 38000 → `38k`); the star/fork group's x offset shifts based on the language-name length (names of 15 characters or fewer shift the group to x `125`, longer names to x `155`). An `isTemplate` repo shows a `Template` badge, else an `isArchived` repo shows an `Archived` badge, else no badge. Default colors come from the `default_repocard` theme (header `#2f80ed`, description/text `#333`, icon `#586069`, background `#FFFEFE`); Feature 4 overrides and named themes apply.

The output reports these sorted `key=value` signals: `badge` (badge text or `<none>`), `card_bg_fill`, `description` (the trimmed/escaped text), `forkcount` (rendered value or `[value when stargazers count is zero]`), `header`, `lang_color_fill` (or `[value when stargazers count is zero]`), `lang_name` (or `[value when stargazers count is zero]`), `stars_forks_group_transform`, `stargazers` (rendered value or `[value when stargazers count is zero]`), and the resolved `style_header_fill`/`style_desc_fill`/`style_icon_fill`.

**Test Cases:** `rcb_tests/public_test_cases/feature9_repo_card.json`

```json
{
  "description": "Render a repository summary card from a repo object (name, owner-qualified name, description, primary language with name and color, stargazer count, fork count, and archived/template flags) and an options object. The card shows a header (the bare name, or the owner-qualified name when owner display is enabled), a description trimmed with an ellipsis past a length limit, a colored primary-language indicator (falling back to a neutral color and an Unspecified label when no language is given), and star and fork counts (each shown only when greater than zero, with large counts abbreviated). An archived or template repository shows a corresponding badge, and the language/stat group shifts horizontally based on the language name length. The output reports the header text, trimmed description, star and fork values (or their absence), language name and color (or absence), any badge text, the stat group transform, the background fill, and the resolved header/description/icon style colors.",
  "cases": [
    {"input": {"op": "repo_card", "repo": {"nameWithOwner": "acme/widgets", "name": "widgets", "stargazers": {"totalCount": 38000}, "description": "Help us take over the world! React + TS + GraphQL Chat App", "primaryLanguage": {"color": "#2b7489", "id": "MDg6TGFuZ3VhZ2UyODc=", "name": "TypeScript"}, "forkCount": 100}}, "expected_output": "badge=<none>\ncard_bg_fill=#FFFEFE\ndescription=Help us take over the world! React + TS + GraphQL Chat ..\nforkcount=100\nheader=widgets\nlang_color_fill=#2b7489\nlang_name=TypeScript\nstars_forks_group_transform=translate(125, 100)\nstargazers=38k\nstyle_desc_fill=#333\nstyle_header_fill=#2f80ed\nstyle_icon_fill=#586069\n"},
    {"input": {"op": "repo_card", "repo": {"nameWithOwner": "acme/widgets", "name": "widgets", "stargazers": {"totalCount": 38000}, "description": "Help us take over the world! React + TS + GraphQL Chat App", "primaryLanguage": {"color": "#2b7489", "id": "MDg6TGFuZ3VhZ2UyODc=", "name": "TypeScript"}, "forkCount": 100}, "options": {"show_owner": true}}, "expected_output": "badge=<none>\ncard_bg_fill=#FFFEFE\ndescription=Help us take over the world! React + TS + GraphQL Chat ..\nforkcount=100\nheader=acme/widgets\nlang_color_fill=#2b7489\nlang_name=TypeScript\nstars_forks_group_transform=translate(125, 100)\nstargazers=38k\nstyle_desc_fill=#333\nstyle_header_fill=#2f80ed\nstyle_icon_fill=#586069\n"}
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the formatting helpers, color/theme resolution, rank scorer, and the three card renderers described above, decoupled from standard I/O and JSON parsing.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads a single JSON request from stdin, dispatches on the `op` field to the matching core operation, and prints the result to stdout exactly per the per-feature contracts above (single-token outputs for the helpers; sorted `key=value` lines for color resolution, rank scoring, and the card renderers, with the documented placeholder tokens for absent values).

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` containing **only** the raw stdout from the program under test, so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- sort lexicographically ascending
- descending size order
