## Product Requirement Document

# Release Automation Toolkit — Semantic Version Bumping & Changelog Generation

## Project Goal

Build a release-automation tool that, from a project's conventional commit history, computes the next semantic version, updates the version recorded in the project's metadata files, generates a human-readable changelog, and records the release in version control (a release commit and an annotated tag). The tool lets maintainers cut consistent, well-documented releases without hand-editing version numbers or assembling changelogs by hand.

---

## Background & Problem

Without such a tool, maintainers must manually decide whether a set of changes warrants a [contradictory release type and version arguments], minor, or patch release, edit the version string in one or more metadata files, hand-write changelog entries grouped by change type, and remember to commit and tag the result. This is repetitive, easy to get wrong, and drifts out of sync across the several files that record a version.

With this tool, the maintainer runs a single command. The tool reads the commits made since the last release, applies well-defined rules to recommend the next version, rewrites the version in every recognised metadata file (preserving each file's formatting), produces or extends a changelog, and creates the release commit and tag — all deterministically driven by the commit history and a small set of options.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility system (version recommendation, metadata-file rewriting, changelog rendering, version-control interaction, lifecycle-hook execution, option/configuration parsing). It MUST be organised as a clear multi-file tree separating these concerns; it MUST NOT be a single monolithic file.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a black-box contract for an execution adapter, NOT the internal data model. The core logic (version math, changelog formatting, release orchestration) must be decoupled from stdin/stdout and JSON. The adapter alone sets up the temporary version-controlled workspace, invokes the core, and renders results to stdout.

3. **Adherence to SOLID Design Principles:** Separate parsing, recommendation, file rewriting, changelog rendering, and version-control side effects into distinct units; keep the core engine open for extension (new metadata file types, new lifecycle points) but closed for modification; depend on abstractions for the version-control and filesystem boundaries.

4. **Robustness & Interface Design:** The public interface must be idiomatic to the target language and hide internal complexity. Invalid configuration and impossible requests must be modeled as well-defined error conditions, surfaced to the contract as neutral error categories (see Feature 11), never as raw runtime fault text.

---

## Domain Conventions (shared by all features)

- **Versions** are semantic-version strings `MAJOR.MINOR.PATCH`, optionally with a pre-release suffix (`-<id>.<n>` or `-<n>`).
- **Conventional commits**: a commit subject begins with a type. A `fix:` commit denotes a patch-level change, a `feat:` commit a feature (minor) change, and an exclamation mark after the type (e.g. `feat!:`) denotes a breaking ([contradictory release type and version arguments]) change. Other subjects carry no release weight.
- **Tags** are version strings carrying a configurable prefix (default `v`), e.g. `v1.2.3`.
- In changelog outputs, calendar dates are rendered as the literal token `DATE` and commit short-hashes as the literal token `HASH`, so that outputs are stable and comparable. (These tokens are an artifact of the test contract's normalisation, not literal program text.)
- The default branch of the workspace is `master`.

---

## Core Features

### Feature 1: Message Template Substitution

**As a developer**, I want a release message template with a version placeholder, so I can produce commit and tag messages that always carry the correct version.

**Expected Behavior / Usage:**

The input is a message template plus a version string. Every occurrence of the placeholder token `{{currentTag}}` in the template is replaced by the version string; all other characters are left untouched (zero occurrences yields the template unchanged; multiple occurrences are all replaced). Output is the substituted message followed by a newline.

**Test Cases:** `rcb_tests/public_test_cases/feature1_format_message.json`

```json
{
    "description": "Substitute a release version into a commit/tag message template. The template contains zero or more occurrences of the version placeholder token {{currentTag}}; every occurrence is replaced by the supplied version string and all other text is left untouched.",
    "cases": [
        {"input": {"kind": "format_message", "template": "chore(release): 1.0.0", "version": "1.0.0"}, "expected_output": "chore(release): 1.0.0\n"},
        {"input": {"kind": "format_message", "template": "chore(release): {{currentTag}}", "version": "1.0.0"}, "expected_output": "chore(release): 1.0.0\n"}
    ]
}
```

---

### Feature 2: Automatic Version Recommendation

**As a developer**, I want the next version inferred from commit history, so I do not have to decide the increment by hand.

**Expected Behavior / Usage:**

Given a current version (read from the project manifest) and the commits added since that version, the tool selects the smallest semantic increment that covers them: a breaking-change commit bumps the [contradictory release type and version arguments] component (minor and patch reset to zero), a feature commit bumps the minor component (patch reset), and a fix commit bumps the patch component. The recommended next version is reported as `version=<x.y.z>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_auto_bump.json`

```json
{
    "description": "Automatic version recommendation from conventional commit history. A breaking-change commit bumps the [contradictory release type and version arguments] component, a feature commit bumps the minor, and a fix commit bumps the patch.",
    "cases": [
        {"input": {"kind": "release", "packageVersion": "1.0.0", "ops": [{"commit": "feat!: breaking change"}], "args": [], "report": ["version"]}, "expected_output": "version=2.0.0\n"},
        {"input": {"kind": "release", "packageVersion": "1.0.0", "ops": [{"commit": "feat: a feature"}], "args": [], "report": ["version"]}, "expected_output": "version=1.1.0\n"},
        {"input": {"kind": "release", "packageVersion": "1.0.0", "ops": [{"commit": "fix: a fix"}], "args": [], "report": ["version"]}, "expected_output": "version=1.0.1\n"}
    ]
}
```

---

### Feature 3: Pre[pre-release suffix progression pattern].0.0 Major Protection

**As a developer**, I want breaking changes on a pre[pre-release suffix progression pattern].0.0 project to stay below 1.0.0 unless I explicitly opt in, so an unstable project is not forced to a stable [contradictory release type and version arguments] release by accident.

**Expected Behavior / Usage:**

*3.1 Automatic path is protected — a breaking change does not auto-promote to 1.x*

When the current version is below `1.0.0` and the increment is being recommended automatically, a breaking-change commit is downgraded one level: it bumps the minor component (patch reset) instead of the [contradictory release type and version arguments]. Output is reported as `version=<x.y.z>`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_pre[contradictory release type and version arguments]_auto.json`

```json
{
    "description": "Pre[pre-release suffix progression pattern].0.0 [contradictory release type and version arguments]-protection. While below 1.0.0, an automatically recommended breaking change bumps the minor component instead of escalating to the 1.x line.",
    "cases": [
        {"input": {"kind": "release", "packageVersion": "[specific pre[pre-release suffix progression pattern].x historical versions where downgrade rules apply]", "packageOptions": {"repository": {"url": "x"}}, "ops": [{"commit": "feat!: this is a breaking change"}], "args": [], "report": ["version"]}, "expected_output": "version=[specific pre[pre-release suffix progression pattern].x historical versions where downgrade rules apply]\n"}
    ]
}
```

*3.2 Explicit [contradictory release type and version arguments] request overrides protection — promotes to 1.0.0*

When the caller explicitly forces a [contradictory release type and version arguments] release, a pre[pre-release suffix progression pattern].0.0 project is promoted to `1.0.0`, even though the automatic path would have refused.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_pre[contradictory release type and version arguments]_forced.json`

```json
{
    "description": "Pre[pre-release suffix progression pattern].0.0 [contradictory release type and version arguments]-protection is overridden by an explicit [contradictory release type and version arguments] release request, promoting the project to 1.0.0.",
    "cases": [
        {"input": {"kind": "release", "packageVersion": "[specific pre[pre-release suffix progression pattern].x historical versions where downgrade rules apply]", "packageOptions": {"repository": {"url": "x"}}, "ops": [{"commit": "feat!: this is a breaking change"}], "args": ["-r", "[contradictory release type and version arguments]"], "report": ["version"]}, "expected_output": "version=1.0.0\n"}
    ]
}
```

---

### Feature 4: Manual Release Selection

**As a developer**, I want to override the increment explicitly, so I can release exactly what I intend regardless of commit history.

**Expected Behavior / Usage:**

*4.1 Named increment*

When the caller names the increment as `[contradictory release type and version arguments]`, `minor`, or `patch`, that component is incremented (lower components reset to zero); commit history is ignored for the choice.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_release_as_type.json`

```json
{
    "description": "Manual release-type override. The caller names the increment as [contradictory release type and version arguments], minor, or patch and that component is incremented.",
    "cases": [
        {"input": {"kind": "release", "packageVersion": "1.0.0", "ops": [{"commit": "fix: first commit"}], "args": ["--release-as", "[contradictory release type and version arguments]"], "report": ["version"]}, "expected_output": "version=2.0.0\n"},
        {"input": {"kind": "release", "packageVersion": "1.0.0", "ops": [{"commit": "fix: first commit"}], "args": ["--release-as", "minor"], "report": ["version"]}, "expected_output": "version=1.1.0\n"},
        {"input": {"kind": "release", "packageVersion": "1.0.0", "ops": [{"commit": "fix: first commit"}], "args": ["--release-as", "patch"], "report": ["version"]}, "expected_output": "version=1.0.1\n"}
    ]
}
```

*4.2 Exact version*

When the explicit value is a full version string (optionally with a pre-release suffix) rather than a named keyword, that exact string becomes the new version verbatim. A leading `v` on the requested value is stripped.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_release_as_exact.json`

```json
{
    "description": "Manual release as an exact version string; the supplied value becomes the new version verbatim, with a leading 'v' stripped.",
    "cases": [
        {"input": {"kind": "release", "packageVersion": "1.0.0", "ops": [{"commit": "fix: first commit"}], "args": ["--release-as", "[contradictory release type and version arguments]"], "report": ["version"]}, "expected_output": "version=100.0.0\n"},
        {"input": {"kind": "release", "packageVersion": "1.0.0", "ops": [{"commit": "fix: first commit"}], "args": ["--release-as", "200.0.0-amazing"], "report": ["version"]}, "expected_output": "version=200.0.0-amazing\n"}
    ]
}
```

---

### Feature 5: Pre-releases

**As a developer**, I want to cut pre-release versions and advance them across runs, so I can ship previews before a stable release.

**Expected Behavior / Usage:**

*5.1 Typed pre-release with a named increment*

When a pre-release identifier is requested together with a named increment, the increment is applied to the base version and a suffix `-<id>.0` is appended.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_prerelease_typed.json`

```json
{
    "description": "Pre-release tagging combined with a named increment appends a suffix '-<id>.0' to the bumped base version.",
    "cases": [
        {"input": {"kind": "release", "packageVersion": "1.0.0", "ops": [{"commit": "fix: first commit"}], "args": ["--release-as", "[contradictory release type and version arguments]", "--prerelease", "[contradictory release type and version arguments]"], "report": ["version"]}, "expected_output": "version=2.0.0-[contradictory release type and version arguments].0\n"}
    ]
}
```

*5.2 Default pre-release using the automatic recommendation*

When a pre-release is requested without naming an identifier, the increment is inferred from commit history and a numeric suffix `[pre-release suffix progression pattern]` is appended to the bumped base.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_prerelease_default.json`

```json
{
    "description": "Pre-release with no explicit identifier uses the automatic recommendation and appends a numeric '[pre-release suffix progression pattern]' suffix.",
    "cases": [
        {"input": {"kind": "release", "packageVersion": "1.0.0", "changelogSeed": "legacy header format<a name=1.0.0>\n", "ops": [{"commit": "feat: first commit"}], "args": ["--prerelease"], "report": ["version"]}, "expected_output": "version=1.1.0[pre-release suffix progression pattern]\n"}
    ]
}
```

*5.3 Sequential pre-release progression*

Across repeated runs under one pre-release identifier, the trailing pre-release counter increments (`.0`, `.1`, `.2` …) while the underlying increment does not exceed the level the active pre-release already represents; when a higher-level increment is requested, the base version rises and the counter restarts at zero. Each run reports the version it produced, in order.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_prerelease_progression.json`

```json
{
    "description": "Sequential pre-release progression across several runs: the trailing counter advances until a higher-level increment raises the base and restarts it at zero. Each run reports one version, in order.",
    "cases": [
        {"input": {"kind": "release", "packageVersion": "1.0.0", "rounds": [
            {"ops": [{"commit": "fix: first patch"}], "args": ["--release-as", "patch", "--prerelease", "dev"]},
            {"ops": [{"commit": "fix: second patch"}], "args": ["--prerelease", "dev"]},
            {"ops": [{"commit": "feat: first new feat"}], "args": ["--release-as", "minor", "--prerelease", "dev"]},
            {"ops": [{"commit": "fix: third patch"}], "args": ["--release-as", "minor", "--prerelease", "dev"]},
            {"ops": [{"commit": "fix: forth patch"}], "args": ["--prerelease", "dev"]}
        ]}, "expected_output": "version=1.0.1-dev.0\nversion=1.0.1-dev.1\nversion=1.1.0-dev.0\nversion=1.1.0-dev.1\nversion=1.1.0-dev.2\n"}
    ]
}
```

---

### Feature 6: Changelog Generation

**As a developer**, I want a grouped, linked changelog generated from commits, so release notes stay accurate and consistent.

**Expected Behavior / Usage:**

*6.1 Single-release section rendering*

A generated changelog opens with the configured header line, then a release-section heading carrying the new version as a comparison link (URL built from a configurable compare format and the previous/current tags) and a date, then grouped subsections: fix commits under `Bug Fixes`, feature commits under `Features`, each entry being the commit description followed by its short hash. The `changelogSeed` input provides the pre-existing changelog text (empty here); the compare format and header are passed as arguments.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_changelog_section.json`

```json
{
    "description": "Changelog section rendering for a single release: configured header, a release-section heading with a comparison link and date, then grouped Bug Fixes / Features subsections.",
    "cases": [
        {"input": {"kind": "changelog", "packageVersion": null, "changelogSeed": "", "ops": [{"commit": "feat: first commit"}, {"tag": "v1.0.0"}, {"commit": "fix: patch release"}], "args": ["--changelogHeader=# Release Notes", "--compareUrlFormat=/compare/{{previousTag}}...{{currentTag}}"]}, "expected_output": "# Release Notes\n### [1.0.1](/compare/v1.0.0...v1.0.1) (DATE)\n\n\n### Bug Fixes\n\n* patch release HASH\n"},
        {"input": {"kind": "changelog", "packageVersion": null, "changelogSeed": "", "ops": [{"commit": "feat: first commit"}, {"tag": "v1.0.0"}, {"commit": "feat: a new feature"}], "args": ["--changelogHeader=# Release Notes", "--compareUrlFormat=/compare/{{previousTag}}...{{currentTag}}"]}, "expected_output": "# Release Notes\n## [1.1.0](/compare/v1.0.0...v1.1.0) (DATE)\n\n\n### Features\n\n* a new feature HASH\n"}
    ]
}
```

*6.2 Stacked releases (newest first)*

When a changelog already contains a prior release section, the next release's section is prepended above it, the header appears once at the top, and releases are listed newest-first.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_changelog_stacked.json`

```json
{
    "description": "Stacked changelog across two releases: the newer section is prepended above the older one with the header kept once at the top.",
    "cases": [
        {"input": {"kind": "changelog", "packageVersion": null, "changelogSeed": "", "rounds": [
            {"ops": [{"commit": "feat: first commit"}, {"tag": "v1.0.0"}, {"commit": "fix: patch release"}], "args": ["--changelogHeader=# Release Notes", "--compareUrlFormat=/compare/{{previousTag}}...{{currentTag}}"]},
            {"ops": [{"commit": "fix: another patch release"}], "args": ["--changelogHeader=# Release Notes", "--compareUrlFormat=/compare/{{previousTag}}...{{currentTag}}"]}
        ]}, "expected_output": "# Release Notes\n### [1.0.2](/compare/v1.0.1...v1.0.2) (DATE)\n\n\n### Bug Fixes\n\n* another patch release HASH\n\n\n\n### [1.0.1](/compare/v1.0.0...v1.0.1) (DATE)\n\n\n### Bug Fixes\n\n* patch release HASH\n"}
    ]
}
```

*6.3 Replacing a legacy release marker*

When the existing changelog begins with free-form legacy header text ending in an old-style release anchor marker, the legacy header text is stripped but everything from the old anchor onward is retained, with the freshly generated section prepended above it.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_changelog_legacy.json`

```json
{
    "description": "Replacing a legacy release marker: the legacy header text is dropped but the old release anchor block is preserved below the freshly generated section.",
    "cases": [
        {"input": {"kind": "changelog", "packageVersion": null, "changelogSeed": "legacy header format<a name=1.0.0>\n", "ops": [{"commit": "feat: first commit"}, {"tag": "v1.0.0"}, {"commit": "fix: patch release"}], "args": ["--changelogHeader=# Release Notes", "--compareUrlFormat=/compare/{{previousTag}}...{{currentTag}}"]}, "expected_output": "# Release Notes\n### [1.0.1](/compare/v1.0.0...v1.0.1) (DATE)\n\n\n### Bug Fixes\n\n* patch release HASH\n\n\n\n<a name=1.0.0>\n"}
    ]
}
```

*6.4 Configurable issue-reference linking*

A configuration file may supply an issue URL format with an `{{id}}` placeholder; an issue reference by number in a changelog entry is rewritten as a markdown link to the configured URL with the number filled in.

**Test Cases:** `rcb_tests/public_test_cases/feature6_4_changelog_issue_url.json`

```json
{
    "description": "Configurable issue-reference linking: a numeric issue reference becomes a markdown link built from the configured issue URL format.",
    "cases": [
        {"input": {"kind": "changelog", "packageVersion": null, "changelogSeed": "", "versionrc": {"issueUrlFormat": "http://www.foo.com/{{id}}", "changelogHeader": "# Release Notes", "compareUrlFormat": "/compare/{{previousTag}}...{{currentTag}}"}, "ops": [{"commit": "feat: another commit addresses issue #1"}], "args": []}, "expected_output": "# Release Notes\n## 1.1.0 (DATE)\n\n\n### Features\n\n* another commit addresses issue [#1](http://www.foo.com/1) HASH\n"}
    ]
}
```

*6.5 Custom header text*

A caller-supplied header string becomes the first line of the changelog, replacing the default header; the sections below are unaffected.

**Test Cases:** `rcb_tests/public_test_cases/feature6_5_changelog_custom_header.json`

```json
{
    "description": "Custom changelog header text replaces the default header as the first line of the document.",
    "cases": [
        {"input": {"kind": "changelog", "packageVersion": null, "changelogSeed": "", "ops": [{"commit": "feat: first commit"}], "args": ["--changelogHeader=# Pork Chop Log", "--compareUrlFormat=/compare/{{previousTag}}...{{currentTag}}"]}, "expected_output": "# Pork Chop Log\n## 1.1.0 (DATE)\n\n\n### Features\n\n* first commit HASH\n"}
    ]
}
```

---

### Feature 7: Release Commit & Tag Messages

**As a developer**, I want consistent, configurable release commit/tag messages, so my history reads clearly.

**Expected Behavior / Usage:**

*7.1 Default message*

After a release the recording commit and the annotated tag both carry a default message of the form `chore(release): <version>`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_release_message_default.json`

```json
{
    "description": "Release commit and annotated-tag message defaults: both carry 'chore(release): <version>'.",
    "cases": [
        {"input": {"kind": "release", "packageVersion": "1.0.0", "ops": [{"commit": "feat: first commit"}, {"tag": "v1.0.0"}, {"commit": "feat: new feature!"}], "args": [], "report": ["commit_message", "tag_message"]}, "expected_output": "commit_message=chore(release): 1.1.0\ntag_message=chore(release): 1.1.0\n"}
    ]
}
```

*7.2 Custom commit message*

The release commit message template can be overridden by configuration or by argument; its `{{currentTag}}` placeholder is filled with the new version.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_release_message_custom.json`

```json
{
    "description": "Customising the release commit message via configuration or a command-line argument, with the version placeholder filled in.",
    "cases": [
        {"input": {"kind": "release", "packageVersion": "1.0.0", "versionrc": {"releaseCommitMessageFormat": "This commit represents release: {{currentTag}}"}, "ops": [{"commit": "feat: another commit addresses issue #1"}], "args": [], "report": ["commit_message"]}, "expected_output": "commit_message=This commit represents release: 1.1.0\n"},
        {"input": {"kind": "release", "packageVersion": "1.0.0", "ops": [{"commit": "feat: another commit"}], "args": ["--releaseCommitMessageFormat={{currentTag}} is the version."], "report": ["commit_message"]}, "expected_output": "commit_message=1.1.0 is the version.\n"}
    ]
}
```

*7.3 Legacy percent-substitution*

A deprecated message option uses `%s` as the version placeholder; every `%s` is replaced by the new version.

**Test Cases:** `rcb_tests/public_test_cases/feature7_3_legacy_message.json`

```json
{
    "description": "Legacy percent-substitution in the release commit message: every %s is replaced by the new version.",
    "cases": [
        {"input": {"kind": "release", "packageVersion": "1.0.0", "ops": [{"commit": "feat: another commit"}], "args": ["--message=V:%s"], "report": ["commit_message"]}, "expected_output": "commit_message=V:1.1.0\n"},
        {"input": {"kind": "release", "packageVersion": "1.0.0", "ops": [{"commit": "feat: another commit"}], "args": ["--message=V:%s is the %s."], "report": ["commit_message"]}, "expected_output": "commit_message=V:1.1.0 is the 1.1.0.\n"}
    ]
}
```

---

### Feature 8: Metadata File Updates

**As a developer**, I want every recognised metadata file kept in sync and nicely formatted, so versions never drift and diffs stay clean.

**Expected Behavior / Usage:**

*8.1 Synchronising auxiliary files*

Besides the primary manifest, several recognised metadata files (a front-end package descriptor, an extension manifest, a dependency lock descriptor, a dependency shrinkwrap descriptor) have their version field updated to the new release version when present. The `manifests` input supplies such files; output reports the new version and the version recorded in the auxiliary file.

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_manifest_sync.json`

```json
{
    "description": "Synchronising the version across auxiliary metadata files: a recognised auxiliary file's version field is updated to the new release version.",
    "cases": [
        {"input": {"kind": "release", "packageVersion": "1.0.0", "manifests": {"bower.json": {"version": "1.0.0"}}, "ops": [{"commit": "feat: first commit"}, {"tag": "v1.0.0"}, {"commit": "feat: new feature!"}], "args": [], "report": ["version", "files"]}, "expected_output": "version=1.1.0\nfile bower.json=1.1.0\n"}
    ]
}
```

*8.2 Ignored files are skipped*

An auxiliary file whose path is listed in the project's ignore file is left untouched, while the primary manifest is still bumped.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_manifest_gitignore.json`

```json
{
    "description": "An auxiliary metadata file named in the ignore file is not version-bumped, while the primary manifest still is.",
    "cases": [
        {"input": {"kind": "release", "packageVersion": "1.0.0", "manifests": {"bower.json": {"version": "1.0.0"}}, "gitignore": "bower.json", "ops": [{"commit": "feat: first commit"}, {"tag": "v1.0.0"}, {"commit": "feat: new feature!"}], "args": [], "report": ["version", "files"]}, "expected_output": "version=1.1.0\nfile bower.json=1.0.0\n"}
    ]
}
```

*8.3 Formatting preservation*

When the primary manifest's version is rewritten, the original indentation unit (tab or a run of spaces) and line-ending style (LF, or CRLF) are preserved and a single trailing newline is ensured. The input supplies the exact raw manifest text; the output reports the exact raw text afterward, as a JSON-quoted string.

**Test Cases:** `rcb_tests/public_test_cases/feature8_3_manifest_formatting.json`

```json
{
    "description": "Formatting preservation when rewriting the primary manifest: the existing indentation unit and line-ending style are kept, with a single trailing newline.",
    "cases": [
        {"input": {"kind": "release", "manifestText": "{\n  \"version\": \"1.0.0\"\n}\n", "ops": [{"commit": "feat: c"}], "args": [], "report": ["manifest_raw"]}, "expected_output": "manifest_raw=\"{\\n  \\\"version\\\": \\\"1.1.0\\\"\\n}\\n\"\n"},
        {"input": {"kind": "release", "manifestText": "{\n\t\"version\": \"1.0.0\"\n}\n", "ops": [{"commit": "feat: c"}], "args": [], "report": ["manifest_raw"]}, "expected_output": "manifest_raw=\"{\\n\\t\\\"version\\\": \\\"1.1.0\\\"\\n}\\n\"\n"}
    ]
}
```

---

### Feature 9: Version Source & Tagging

**As a developer**, I want a sensible base version even without a manifest, and a way to release the current version as-is, so first releases and manifest-less projects work too.

**Expected Behavior / Usage:**

*9.1 Tag fallback when no manifest exists*

With no primary manifest, the base version is taken from the highest existing semantic-version tag (or defaults to `1.0.0` if there are none), the recommended increment is applied, and a new tag is created at the result. Output reports the set of tags newly created by the run.

**Test Cases:** `rcb_tests/public_test_cases/feature9_1_tag_fallback.json`

```json
{
    "description": "Deriving the base version from version-control tags when no manifest exists: the highest semantic-version tag is the base (or 1.0.0 if none), then the recommended increment is applied and a new tag created.",
    "cases": [
        {"input": {"kind": "release", "packageVersion": null, "ops": [{"commit": "feat: first commit"}], "args": [], "report": ["tag"]}, "expected_output": "tag=v1.1.0\n"},
        {"input": {"kind": "release", "packageVersion": null, "ops": [{"tag": "v5.0.0"}, {"tag": "v3.0.0"}, {"commit": "feat: another commit"}], "args": [], "report": ["tag"]}, "expected_output": "tag=v5.1.0\n"}
    ]
}
```

*9.2 First-release mode keeps the current version*

When the run is marked a first release, the bump step is skipped: the current manifest version is released and tagged unchanged.

**Test Cases:** `rcb_tests/public_test_cases/feature9_2_first_release.json`

```json
{
    "description": "First-release mode skips the version bump: the current version is released and tagged as-is.",
    "cases": [
        {"input": {"kind": "release", "packageVersion": "1.0.1", "ops": [{"commit": "feat: first commit"}, {"commit": "fix: patch release"}], "args": ["--first-release"], "report": ["version", "tag"]}, "expected_output": "version=1.0.1\ntag=v1.0.1\n"}
    ]
}
```

*9.3 Merge commits count toward recommendation*

A feature merged from a side branch via a no-fast-forward merge whose subject follows the conventional format is counted in the recommendation, so it yields a minor bump.

**Test Cases:** `rcb_tests/public_test_cases/feature9_3_merge_commits.json`

```json
{
    "description": "Merge commits participate in version recommendation: a merged feature whose merge subject is conventionally typed yields a minor bump.",
    "cases": [
        {"input": {"kind": "release", "packageVersion": "1.0.0", "ops": [{"commit": "feat: first commit"}, {"tag": "v1.0.0"}, {"branch": "new-feature"}, {"checkout": "new-feature"}, {"commit": "Implementing new feature"}, {"checkout": "master"}, {"merge": {"msg": "feat: new feature from branch", "branch": "new-feature"}}], "args": [], "report": ["version"]}, "expected_output": "version=1.1.0\n"}
    ]
}
```

---

### Feature 10: Pipeline Control

**As a developer**, I want to skip stages, preview without side effects, get publishing guidance, include staged files, and hook custom scripts, so I can adapt the release to my workflow.

**Expected Behavior / Usage:**

*10.1 Skipping stages*

Individual stages can be skipped: skipping the bump leaves the version unchanged; skipping the changelog means no changelog file is created.

**Test Cases:** `rcb_tests/public_test_cases/feature10_1_skip_stages.json`

```json
{
    "description": "Skipping individual release stages: skipping the bump leaves the version unchanged; skipping the changelog creates no changelog file.",
    "cases": [
        {"input": {"kind": "release", "packageVersion": "1.0.0", "changelogSeed": "legacy header format<a name=1.0.0>\n", "ops": [{"commit": "feat: first commit"}], "args": ["--skip.bump", "true", "--skip.changelog", "true"], "report": ["version"]}, "expected_output": "version=1.0.0\n"},
        {"input": {"kind": "release", "packageVersion": "1.0.0", "ops": [{"commit": "feat: first commit"}], "args": ["--skip.changelog", "true"], "report": ["version", "changelog"]}, "expected_output": "version=1.1.0\nchangelog=absent\n"}
    ]
}
```

*10.2 Dry run*

A dry run performs no non-idempotent action: no version change, no new tag, no changelog file.

**Test Cases:** `rcb_tests/public_test_cases/feature10_2_dry_run.json`

```json
{
    "description": "Dry-run mode performs no side effects: the version is unchanged, no tag is created, and no changelog file is written.",
    "cases": [
        {"input": {"kind": "release", "packageVersion": "1.0.0", "ops": [{"commit": "feat: first commit"}, {"tag": "v1.0.0"}, {"commit": "feat: new feature!"}], "args": ["--dry-run"], "report": ["version", "tag", "changelog"]}, "expected_output": "version=1.0.0\ntag=none\nchangelog=absent\n"}
    ]
}
```

*10.3 Publishing advice*

After a release the tool emits a suggested push/publish command: always a follow-tags push to the current branch, plus a publish step only when a publishable, non-private primary manifest was bumped; for a pre-release the publish step carries a dist-tag derived from the pre-release identifier (or a default tag when empty).

**Test Cases:** `rcb_tests/public_test_cases/feature10_3_publish_advice.json`

```json
{
    "description": "Post-release publishing advice: always a follow-tags push, plus a publish step (with a pre-release dist-tag where relevant) when a publishable, non-private manifest was bumped.",
    "cases": [
        {"input": {"kind": "release", "packageVersion": "1.0.0", "ops": [{"commit": "feat: first commit"}], "args": [], "report": ["publish"]}, "expected_output": "publish=git push --follow-tags origin master && npm publish\n"},
        {"input": {"kind": "release", "packageVersion": "1.0.0", "ops": [{"commit": "feat: first commit"}], "args": ["--prerelease"], "report": ["publish"]}, "expected_output": "publish=git push --follow-tags origin master && npm publish --tag prerelease\n"}
    ]
}
```

*10.4 Committing all staged files*

With the commit-all option the release commit also includes any already-staged changes, leaving the working tree clean and adding a staged-files notice to the progress output; without it the notice is absent.

**Test Cases:** `rcb_tests/public_test_cases/feature10_4_commit_all.json`

```json
{
    "description": "Committing all staged changes: with the option the staged-files notice appears (and the tree ends clean); without it the notice is absent.",
    "cases": [
        {"input": {"kind": "release", "packageVersion": "1.0.0", "ops": [{"commit": "feat: c"}], "args": ["--commit-all"], "report": ["staged_notice"]}, "expected_output": "staged_notice=yes\n"},
        {"input": {"kind": "release", "packageVersion": "1.0.0", "ops": [{"commit": "feat: c"}], "args": [], "report": ["staged_notice"]}, "expected_output": "staged_notice=no\n"}
    ]
}
```

*10.5 Lifecycle hooks*

User scripts run at defined points. A pre-bump hook that prints a version string makes that the release version; a pre-commit hook that prints text supplies an alternate release commit message. The hook body is provided as script source in the input.

**Test Cases:** `rcb_tests/public_test_cases/feature10_5_lifecycle_hooks.json`

```json
{
    "description": "Lifecycle hooks influence the release: a pre-bump hook printing a version sets the release version; a pre-commit hook printing text supplies an alternate commit message.",
    "cases": [
        {"input": {"kind": "release", "packageVersion": "1.0.0", "changelogSeed": "legacy header format<a name=1.0.0>\n", "hooks": {"prebump": "console.log(\"9.9.9\")"}, "ops": [{"commit": "feat: first commit"}], "args": ["--patch"], "report": ["version"]}, "expected_output": "version=9.9.9\n"},
        {"input": {"kind": "release", "packageVersion": "1.0.0", "changelogSeed": "legacy header format<a name=1.0.0>\n", "hooks": {"precommit": "console.log(\"releasing %s delivers #222\")"}, "ops": [{"commit": "feat: first commit"}], "args": ["--patch"], "report": ["commit_message"]}, "expected_output": "commit_message=releasing %s delivers #222\n"}
    ]
}
```

---

### Feature 11: Validation & Error Reporting

**As a developer**, I want invalid configurations and impossible requests rejected with a clear category, so failures are predictable and actionable.

**Expected Behavior / Usage:**

The tool validates configuration and the request and, on failure, reports a single neutral error-category line `error=<category>` instead of completing. Covered conditions: the embedded scripts configuration must be an object (`invalid_scripts`); the embedded skip configuration must be an object (`invalid_skip`); a custom changelog header must not itself look like a release-section heading (`invalid_changelog_header`); a run with no manifest and tag-fallback disabled has no version source (`no_package_file`); a manual release request given with no release-type value is incomplete (`missing_release_type`). A run that completes successfully reports `error=none`. Error categories are language-neutral and must not leak host runtime details. (Project-embedded settings are supplied to the adapter via a neutral `toolConfig` field; the adapter places them under the implementation's reserved manifest key.)

**Test Cases:** `rcb_tests/public_test_cases/feature11_validation_errors.json`

```json
{
    "description": "Input validation and error reporting as neutral categories for invalid scripts/skip configuration, an invalid changelog header, a missing version source, a missing release type, and the success case.",
    "cases": [
        {"input": {"kind": "error", "packageVersion": "1.0.0", "toolConfig": {"scripts": "echo hello"}, "ops": [{"commit": "feat: first commit"}], "args": []}, "expected_output": "error=invalid_scripts\n"},
        {"input": {"kind": "error", "packageVersion": "1.0.0", "toolConfig": {"skip": true}, "ops": [{"commit": "feat: first commit"}], "args": []}, "expected_output": "error=invalid_skip\n"},
        {"input": {"kind": "error", "packageVersion": "1.0.0", "changelogSeed": "", "ops": [{"commit": "feat: first commit"}], "args": ["--changelogHeader=## 3.0.2"]}, "expected_output": "error=invalid_changelog_header\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the features above, separating version recommendation, metadata-file rewriting, changelog rendering, version-control interaction, lifecycle-hook execution, and option/configuration parsing.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON command from stdin, sets up a deterministic temporary version-controlled workspace as described by the command, invokes the core logic, and prints results to stdout strictly matching the per-leaf-feature contracts above (including normalising any error into a neutral `error=<category>` line). This adapter must be separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{stem}@{index:03}.txt` containing only the raw program stdout, so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- validate changelog header format as per project convention
- ensure proper section ordering in changelog output
