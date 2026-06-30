## Product Requirement Document

# Container Image Manifest & Registry Tag Toolkit - Behavior Specification

## Project Goal

Build a toolkit that turns a declarative description of a multi-repository, multi-platform container image catalog into the derived strings and documents that a publishing pipeline needs. It allows release engineers to describe architectures, base operating systems, build variables, and tag layouts once, and have the toolkit deterministically compute canonical names, stable build identifiers, a fully merged catalog model, and the registry-facing tag metadata document — without hand-writing any of that boilerplate.

---

## Background & Problem

Without this toolkit, teams that ship large families of container images are forced to maintain naming conventions, OS marketing names, build identifiers, shared/concrete tag groupings, and registry tag documentation by hand and keep them in sync across dozens of repositories. This leads to repetitive, error-prone string munging, inconsistent display names, duplicated variable definitions across split catalog files, and tag-documentation files that drift away from the actual image layout.

With this toolkit, the catalog is described declaratively (a primary document that may pull in additional included documents), and every derived value is computed by a single, deterministic engine: architecture and OS display names, package-naming forms, per-platform build identifiers, cross-referencing variable resolution, document composition with conflict detection, and the rendered registry tag-metadata YAML.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain has several distinct responsibilities (naming/formatting helpers, a variable resolver, a catalog-composition loader, and a tag-metadata renderer), so it MUST be organized as a multi-file project with clear separation between the core domain and the execution adapter. Do not collapse it into a single monolithic file, but do not over-engineer the simple formatting helpers either.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below define a **black-box contract** for the execution adapter, NOT the internal data model. The core engine must be completely decoupled from stdin/stdout and JSON parsing. A thin adapter is solely responsible for translating each JSON command into idiomatic calls on the core domain and rendering the result as the line-based or YAML contract shown below.

3. **Adherence to SOLID Design Principles:** Separate parsing, command routing, validation, core computation, and output formatting into distinct units. The core engine must be open for extension (new architectures, new OS families, new template blocks) but closed for modification. Keep interfaces small and cohesive, and have high-level logic depend on abstractions rather than on the I/O layer.

4. **Robustness & Interface Design:** The public interface of the core system must be idiomatic and hide internal complexity. Edge cases (missing included files, unresolved or undefined variable references, duplicate variable declarations) must be modeled as distinct, typed error conditions. The execution adapter is responsible for translating those errors into the language-neutral error categories specified below; error output must never leak host-language runtime details.

---

## Core Features

### Feature 1: Processor Architecture Naming

**As a developer**, I want canonical name forms for a processor architecture, so I can build consistent image tags, display strings, and downloadable package file names without reinventing the normalization rules each time.

**Expected Behavior / Usage:**

Each command names an architecture from a fixed set of families (a 64-bit x86 family, a 32-bit ARM family, and a 64-bit ARM family) and asks for one specific naming form. The three naming forms (display, short, package) apply slightly different normalization rules, described in the leaf sub-features below. Input is case-insensitive on the architecture token; output is a single `key=value` line.

*1.1 Architecture display name — the human-facing architecture label, with an optional variant suffix.*

The display name is the architecture token rendered in lowercase, except the 32-bit ARM family is normalized to the fixed string `[a specific sentinel value — ask the PM for the exact string]`. An optional `variant` field (for example a microarchitecture level) is lowercased and appended directly to the display name with no separator.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_architecture_display_name.json`

```json
{
    "description": "Render the canonical display name of a processor architecture. The display name is the lowercased architecture token, except that the 32-bit ARM family is normalized to the fixed string '[a specific sentinel value — ask the PM for the exact string]'. An optional variant suffix (e.g. a microarchitecture level) is lowercased and appended directly to the display name.",
    "cases": [
        {"input": {"action": "arch_display_name", "architecture": "AMD64"}, "expected_output": "display_name=amd64\n"},
        {"input": {"action": "arch_display_name", "architecture": "ARM"}, "expected_output": "display_name=[a specific sentinel value — ask the PM for the exact string]\n"},
        {"input": {"action": "arch_display_name", "architecture": "ARM64"}, "expected_output": "display_name=arm64\n"},
        {"input": {"action": "arch_display_name", "architecture": "AMD64", "variant": "v8"}, "expected_output": "display_name=amd64v8\n"},
        {"input": {"action": "arch_display_name", "architecture": "ARM", "variant": "V7"}, "expected_output": "display_name=[a specific sentinel value — ask the PM for the exact string]v7\n"}
    ]
}
```

*1.2 Architecture short name — the compact label used in concise tag segments.*

The short name is the architecture token in lowercase, except the 64-bit x86 family is normalized to the fixed string `x64`. There is no variant handling for the short form.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_architecture_short_name.json`

```json
{
    "description": "Render the short name of a processor architecture. The short name is the lowercased architecture token, except that the 64-bit x86 family is normalized to the fixed string 'x64'.",
    "cases": [
        {"input": {"action": "arch_short_name", "architecture": "AMD64"}, "expected_output": "short_name=x64\n"},
        {"input": {"action": "arch_short_name", "architecture": "ARM"}, "expected_output": "short_name=arm\n"},
        {"input": {"action": "arch_short_name", "architecture": "ARM64"}, "expected_output": "short_name=arm64\n"}
    ]
}
```

*1.3 Architecture package name — the form used when constructing downloadable package file names.*

The package name is the architecture token in lowercase, except the 64-bit x86 family is normalized to `x64` and the 32-bit ARM family is normalized to `[a specific sentinel value — ask the PM for the exact string]`. (The 64-bit ARM family keeps its token unchanged.)

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_architecture_package_name.json`

```json
{
    "description": "Render the package-naming form of a processor architecture, used when constructing downloadable package file names. The package name is the lowercased architecture token, except that the 64-bit x86 family is normalized to 'x64' and the 32-bit ARM family is normalized to '[a specific sentinel value — ask the PM for the exact string]'.",
    "cases": [
        {"input": {"action": "arch_nupkg_name", "architecture": "AMD64"}, "expected_output": "nupkg_name=x64\n"},
        {"input": {"action": "arch_nupkg_name", "architecture": "ARM"}, "expected_output": "nupkg_name=[a specific sentinel value — ask the PM for the exact string]\n"},
        {"input": {"action": "arch_nupkg_name", "architecture": "ARM64"}, "expected_output": "nupkg_name=arm64\n"}
    ]
}
```

---

### Feature 2: Base Operating System Display Names

**As a developer**, I want a base-OS version identifier translated into a human-readable display name, so I can present consistent OS labels in generated documentation without hardcoding distribution marketing names everywhere.

**Expected Behavior / Usage:**

The command provides an `os` family (`Linux` or `Windows`) and an `os_version` identifier, and returns a single `display_name=...` line. Linux and Windows follow different rules, given in the leaf sub-features below.

*2.1 Linux OS display name — translate Linux base-OS identifiers into distribution display names.*

Distributions with no numeric version (plain Debian codenames such as `debian`) map to a bare distribution name. Well-known Debian and Ubuntu release codenames map to their marketing name and number (e.g. `stretch` → `Debian 9`, `focal` → `Ubuntu 20.04`). Version-bearing identifiers (Alpine, CentOS, Fedora, Azure Linux, CBL-Mariner, and similar) are split into a capitalized/branded distribution name plus the version number (e.g. `alpine3.12` → `Alpine 3.12`, `cbl-mariner2.0` → `CBL-Mariner 2.0`, `azurelinux3.0` → `Azure Linux 3.0`). A trailing flavor suffix such as `-slim` or `-distroless` is ignored and does not change the result.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_os_display_name_linux.json`

```json
{
    "description": "Translate a Linux base-OS version identifier into a human-readable distribution display name. Distributions that carry no numeric version (e.g. plain Debian codenames) map to a bare distribution name; Debian and Ubuntu release codenames map to their well-known marketing names and numbers; version-bearing identifiers (Alpine, CentOS, Fedora, Azure Linux, CBL-Mariner, etc.) are split into a capitalized/branded distribution name plus their version number. A trailing flavor suffix such as '-slim' or '-distroless' is ignored and does not affect the result.",
    "cases": [
        {"input": {"action": "os_display_name", "os": "Linux", "os_version": "debian"}, "expected_output": "display_name=Debian\n"},
        {"input": {"action": "os_display_name", "os": "Linux", "os_version": "stretch"}, "expected_output": "display_name=Debian 9\n"},
        {"input": {"action": "os_display_name", "os": "Linux", "os_version": "buster-slim"}, "expected_output": "display_name=Debian 10\n"},
        {"input": {"action": "os_display_name", "os": "Linux", "os_version": "focal"}, "expected_output": "display_name=Ubuntu 20.04\n"},
        {"input": {"action": "os_display_name", "os": "Linux", "os_version": "jammy-chiseled"}, "expected_output": "display_name=Ubuntu 22.04\n"},
        {"input": {"action": "os_display_name", "os": "Linux", "os_version": "alpine3.12"}, "expected_output": "display_name=Alpine 3.12\n"},
        {"input": {"action": "os_display_name", "os": "Linux", "os_version": "cbl-mariner2.0"}, "expected_output": "display_name=CBL-Mariner 2.0\n"},
        {"input": {"action": "os_display_name", "os": "Linux", "os_version": "azurelinux3.0-distroless"}, "expected_output": "display_name=Azure Linux 3.0\n"}
    ]
}
```

*2.2 Windows OS display name — translate Windows base-OS identifiers into display names.*

The identifier has the form `<family>-<version>`, where the family is one of two Windows server product lines (a Nano Server line and a Windows Server Core line). When the version segment is a long-term-servicing-channel label (prefixed `ltsc`), the display name is `<Product Name> <year>` with the `ltsc` prefix stripped (e.g. `windowsservercore-ltsc2019` → `Windows Server Core 2019`). Otherwise the display name is `<Product Name>, version <version>` (e.g. `nanoserver-1809` → `Nano Server, version 1809`).

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_os_display_name_windows.json`

```json
{
    "description": "Translate a Windows base-OS version identifier into a human-readable display name. The identifier has the form '<family>-<version>' where family is either the Nano Server or Windows Server Core product line. When the version segment is a long-term-servicing-channel label (prefixed 'ltsc'), the display name is '<Product Name> <year>' (the 'ltsc' prefix stripped). Otherwise the display name is '<Product Name>, version <version>'.",
    "cases": [
        {"input": {"action": "os_display_name", "os": "Windows", "os_version": "windowsservercore-ltsc2016"}, "expected_output": "display_name=Windows Server Core 2016\n"},
        {"input": {"action": "os_display_name", "os": "Windows", "os_version": "windowsservercore-ltsc2019"}, "expected_output": "display_name=Windows Server Core 2019\n"},
        {"input": {"action": "os_display_name", "os": "Windows", "os_version": "nanoserver-1809"}, "expected_output": "display_name=Nano Server, version 1809\n"},
        {"input": {"action": "os_display_name", "os": "Windows", "os_version": "windowsservercore-1903"}, "expected_output": "display_name=Windows Server Core, version 1903\n"},
        {"input": {"action": "os_display_name", "os": "Windows", "os_version": "nanoserver-1903"}, "expected_output": "display_name=Nano Server, version 1903\n"},
        {"input": {"action": "os_display_name", "os": "Windows", "os_version": "nanoserver-ltsc2022"}, "expected_output": "display_name=Nano Server 2022\n"}
    ]
}
```

---

### Feature 3: Platform Build Identifier

**As a developer**, I want a stable, deterministic identifier for a platform-specific image, so I can key build results and matrices by platform while collapsing patch/pre-release noise into a single major.minor bucket.

**Expected Behavior / Usage:**

Given a Dockerfile path, an architecture string, an OS type, an OS version, and a product version, the identifier is the five values joined by `-` in this order: Dockerfile path, architecture, OS type, OS version, product-version segment. The product-version segment is reduced to its `major.minor` form only: any patch component and any pre-release suffix are dropped. As a result, versions sharing the same major and minor numbers (e.g. `5.0.0-preview.3`, `5.0`, and `5.0.1`) all produce the same identifier. Output is a single `identifier=...` line.

**Test Cases:** `rcb_tests/public_test_cases/feature3_platform_identifier.json`

```json
{
    "description": "Compute the stable build identifier for a platform-specific image. The identifier concatenates the Dockerfile path, architecture, OS type, OS version, and a product-version segment, joined by '-'. The product-version segment is reduced to its major.minor form only: any patch component and any pre-release suffix are dropped, so versions that share the same major and minor numbers produce the same identifier.",
    "cases": [
        {"input": {"action": "platform_identifier", "product_version": "5.0.0-preview.3", "architecture": "amd64", "os_type": "linux", "os_version": "focal", "dockerfile": "path"}, "expected_output": "identifier=path-amd64-linux-focal-5.0\n"},
        {"input": {"action": "platform_identifier", "product_version": "5.0", "architecture": "amd64", "os_type": "linux", "os_version": "focal", "dockerfile": "path"}, "expected_output": "identifier=path-amd64-linux-focal-5.0\n"},
        {"input": {"action": "platform_identifier", "product_version": "5.0.1", "architecture": "amd64", "os_type": "linux", "os_version": "focal", "dockerfile": "path"}, "expected_output": "identifier=path-amd64-linux-focal-5.0\n"}
    ]
}
```

---

### Feature 4: Cross-Referencing Variable Resolution

**As a developer**, I want named string variables that can reference one another and be overridden externally, so I can factor shared values out of my catalog and parameterize them at invocation time without manual substitution.

**Expected Behavior / Usage:**

Two sources of variables are supplied: a base set (`manifest_variables`) and an override set (`[an internal concept tied to the manifest merge strategy]`). Both are optional. Merging rules: a name present in both takes the override value; a name present only in the override set is added. After merging, every value has its `$(name)` references substituted with the already-resolved value of the referenced variable. References must point to variables that appear earlier in resolution order. A forward reference to a variable that *is* defined but has not yet been resolved is an error reported as `error=unresolved_variable_reference`. A reference to a name that does not exist anywhere is reported as `error=undefined_variable`. On success, output is `count=<N>` followed by each resolved `name=value` pair sorted by name.

**Test Cases:** `rcb_tests/public_test_cases/feature4_variable_resolution.json`

```json
{
    "description": "Resolve a set of named string variables that may reference one another using the syntax $(name). Two sources of variables are provided: a base set and an override set. For names present in both, the override value wins. Names that exist only in the override set are added. After overriding, every value has its $(name) references substituted with the already-resolved value of the referenced variable. References must point to variables that appear earlier in resolution order; a forward reference to a variable that is defined but not yet resolved is an error, and a reference to a name that does not exist anywhere is a separate error. Output reports the total count of resolved variables, then each resolved name=value pair sorted by name.",
    "cases": [
        {"input": {"action": "resolve_variables", "manifest_variables": {"test": "abc", "test2": "$(test)", "test3": "$(test2)", "test4": "xyz"}, "[an internal concept tied to the manifest merge strategy]": {"test4": "$(test)-123"}}, "expected_output": "count=4\ntest=abc\ntest2=abc\ntest3=abc\ntest4=abc-123\n"},
        {"input": {"action": "resolve_variables", "[an internal concept tied to the manifest merge strategy]": {"newVar": "abc"}}, "expected_output": "count=1\nnewVar=abc\n"},
        {"input": {"action": "resolve_variables", "manifest_variables": {"predefinedVar": "123"}, "[an internal concept tied to the manifest merge strategy]": {"newVar": "abc", "newDerivativeVar": "$(predefinedVar)456"}}, "expected_output": "count=3\nnewDerivativeVar=123456\nnewVar=abc\npredefinedVar=123\n"},
        {"input": {"action": "resolve_variables", "manifest_variables": {"test1": "$(test2)", "test2": "abc"}}, "expected_output": "error=unresolved_variable_reference\n"},
        {"input": {"action": "resolve_variables", "manifest_variables": {"test1": "$(test2)"}}, "expected_output": "error=undefined_variable\n"}
    ]
}
```

---

### Feature 5: Manifest Composition

**As a developer**, I want to split a catalog across a primary document and several included documents and have them merged into one model, so I can reuse shared variable and repository definitions across catalogs while detecting conflicts early.

**Expected Behavior / Usage:**

The primary document declares an ordered list of included document file names (`includes`) plus its own optional `variables` and `repos`. Each named included document is provided in the `includes` map. Composition rules: variables from each included document are merged into the primary document's variables; if the same variable name is declared in both the primary and an included document, composition fails with `error=duplicate_variable`. Repositories from included documents are appended after the primary repositories, in include order; repositories that share the same name across documents are consolidated into a single repository whose image sets are concatenated. Referencing an included document that does not exist fails with `error=file_not_found`. On success, output lists the final ordered repository names (`repos=...`), then `<repo>.images=<count>` for each repository in order, then `variables=<comma-separated sorted names>`, then each merged `name=value` variable line sorted by name.

**Test Cases:** `rcb_tests/public_test_cases/feature5_manifest_composition.json`

```json
{
    "description": "Compose a primary manifest document with a set of named included documents. The primary document lists which included documents to merge by file name. Variables from each included document are merged into the primary document's variables; if the same variable name is declared in both the primary and an included document, composition fails with a duplicate-variable error. Repositories from included documents are appended after the primary repositories, and repositories that share the same name across documents are consolidated into a single repository whose image sets are combined. Referencing an included document that does not exist fails with a file-not-found error. Output lists the final ordered repository names, the image count of each repository, and the final merged variable names with their values (sorted by name).",
    "cases": [
        {"input": {"action": "compose_manifest", "manifest": {"includes": ["manifest.variables.json"], "variables": {"variable1": "value1"}, "repos": [{"name": "testRepo", "images": [{"platforms": [{"dockerfile": "testDockerfile", "os": "linux", "osVersion": "stretch", "tags": {"testTag": {}}}]}]}]}, "includes": {"manifest.variables.json": {"variables": {"variable2": "value2"}}}}, "expected_output": "repos=testRepo\ntestRepo.images=1\nvariables=variable1,variable2\nvariable1=value1\nvariable2=value2\n"},
        {"input": {"action": "compose_manifest", "manifest": {"includes": ["manifest.custom1.json", "manifest.custom2.json"]}, "includes": {"manifest.custom1.json": {"repos": [{"name": "testRepo1", "images": [{"platforms": [{"dockerfile": "testDockerfile", "os": "linux", "osVersion": "stretch", "tags": {"testTag1": {}}}]}]}, {"name": "testRepo2", "images": [{"platforms": [{"dockerfile": "testDockerfile", "os": "linux", "osVersion": "stretch", "tags": {"testTag": {}}}]}]}]}, "manifest.custom2.json": {"repos": [{"name": "testRepo1", "images": [{"platforms": [{"dockerfile": "testDockerfile", "os": "linux", "osVersion": "stretch", "tags": {"testTag2": {}}}]}]}, {"name": "testRepo3", "images": [{"platforms": [{"dockerfile": "testDockerfile", "os": "linux", "osVersion": "stretch", "tags": {"testTag": {}}}]}]}]}}}, "expected_output": "repos=testRepo1,testRepo2,testRepo3\ntestRepo1.images=2\ntestRepo2.images=1\ntestRepo3.images=1\nvariables=\n"},
        {"input": {"action": "compose_manifest", "manifest": {"includes": ["invalid.json"], "repos": [{"name": "testRepo", "images": [{"platforms": [{"dockerfile": "testDockerfile", "os": "linux", "osVersion": "stretch", "tags": {"testTag": {}}}]}]}]}}, "expected_output": "error=file_not_found\n"},
        {"input": {"action": "compose_manifest", "manifest": {"includes": ["manifest.variables.json"], "variables": {"variable1": "value1"}, "repos": [{"name": "testRepo", "images": [{"platforms": [{"dockerfile": "testDockerfile", "os": "linux", "osVersion": "stretch", "tags": {"testTag": {}}}]}]}]}, "includes": {"manifest.variables.json": {"variables": {"variable1": "value1"}}}}, "expected_output": "error=duplicate_variable\n"}
    ]
}
```

---

### Feature 6: Registry Tag Metadata Generation

**As a developer**, I want the catalog rendered into the registry-facing tag-metadata YAML document, so I can publish accurate, deduplicated tag groupings and Dockerfile links without authoring the YAML by hand.

**Expected Behavior / Usage:**

A template document is supplied that references a repository block and one or more tag-group blocks; the engine expands it into a YAML document. Each repository renders as a `repoName` entry (prefixed with a fixed publishing scope, e.g. `public/`) carrying `customTablePivots: true` and a list of `tagGroups`. Each tag group reports its tag list, architecture, OS name, OS display version, and Dockerfile location. The input lists images, each with platforms (a Dockerfile directory and optional documented `tags` and `undocumented_tags`) and optional image-level `shared_tags`. Each platform's OS display version uses the same Linux/Windows rules as Feature 2 (e.g. `focal` → `Ubuntu 20.04`). The leaf sub-features below describe Dockerfile-link rendering, undocumented-platform filtering, and duplicated-platform tag combination.

*6.1 Dockerfile link rendering — choose between a source-control permalink and a plain relative path.*

When source-control link generation is enabled and a source branch is supplied, the Dockerfile location is rendered as a permalink of the form `<source repo url>/blob/<branch>/<dockerfile path>`. When link generation is disabled, the Dockerfile location is rendered as the plain repository-relative path to the Dockerfile instead.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_mcr_tags_dockerfile_link.json`

```json
{
    "description": "Generate the registry tags metadata YAML for a repository, controlling how the Dockerfile location is rendered. A template references a repository block and a tag-group block; the engine expands them into a YAML document describing each documented tag group, including the tag list, architecture, OS name, OS display version, and Dockerfile location. When source-control link generation is enabled and a source branch is supplied, the Dockerfile location becomes a permalink of the form '<source repo url>/blob/<branch>/<dockerfile path>'. When link generation is disabled, the Dockerfile location is the plain repository-relative path instead.",
    "cases": [
        {"input": {"action": "mcr_tags", "repo": "repo", "generate_github_links": true, "source_repo_url": "https://example.com/org/repo", "source_branch": "branch", "template": "$(McrTagsYmlRepo:repo)\n$(McrTagsYmlTagGroup:tag)", "images": [{"platforms": [{"dockerfile_dir": "1.0/repo/os", "tags": ["tag"]}]}]}, "expected_output": "repos:\n- repoName: public/repo\n  customTablePivots: true\n  tagGroups:\n  - tags: [ tag ]\n    architecture: amd64\n    os: linux\n    osVersion: Ubuntu 20.04\n    dockerfile: https://example.com/org/repo/blob/branch/1.0/repo/os/Dockerfile\n"},
        {"input": {"action": "mcr_tags", "repo": "repo", "generate_github_links": false, "template": "$(McrTagsYmlRepo:repo)\n$(McrTagsYmlTagGroup:tag)", "images": [{"platforms": [{"dockerfile_dir": "1.0/repo/os", "tags": ["tag"]}]}]}, "expected_output": "repos:\n- repoName: public/repo\n  customTablePivots: true\n  tagGroups:\n  - tags: [ tag ]\n    architecture: amd64\n    os: linux\n    osVersion: Ubuntu 20.04\n    dockerfile: 1.0/repo/os/Dockerfile\n"}
    ]
}
```

*6.2 Undocumented-platform filtering — omit platforms with no documented tags and append documented shared tags.*

A platform whose tags are all marked undocumented contributes nothing and is omitted from the output entirely; only the platform that owns the requested documented tag appears in its tag group, listing that platform's documented concrete tags. When the owning image additionally carries a shared tag that is documented for platforms that have documented concrete tags, that shared tag is appended to the same tag group after the concrete tags.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_mcr_tags_undocumented_platform.json`

```json
{
    "description": "Generate the registry tags metadata YAML when a repository contains platforms that contribute no documented tags, and shared tags that may or may not be documented. Platforms whose tags are all marked undocumented are omitted from the output entirely; only the platform that owns the requested documented tag appears in its tag group. The tag group lists that platform's documented concrete tags. When the owning image additionally carries a shared tag that is documented for platforms that have documented concrete tags, that shared tag is appended to the same tag group after the concrete tags.",
    "cases": [
        {"input": {"action": "mcr_tags", "repo": "repo", "generate_github_links": true, "source_repo_url": "https://example.com/org/repo", "source_branch": "branch", "template": "$(McrTagsYmlRepo:repo)\n$(McrTagsYmlTagGroup:tag1a)\n", "images": [{"platforms": [{"dockerfile_dir": "1.0/repo/os", "undocumented_tags": ["tag2"]}]}, {"platforms": [{"dockerfile_dir": "1.0/repo/os2", "tags": ["tag1a", "tag1b"]}]}]}, "expected_output": "repos:\n- repoName: public/repo\n  customTablePivots: true\n  tagGroups:\n  - tags: [ tag1a, tag1b ]\n    architecture: amd64\n    os: linux\n    osVersion: Ubuntu 20.04\n    dockerfile: https://example.com/org/repo/blob/branch/1.0/repo/os2/Dockerfile\n"},
        {"input": {"action": "mcr_tags", "repo": "repo", "generate_github_links": true, "source_repo_url": "https://example.com/org/repo", "source_branch": "branch", "template": "$(McrTagsYmlRepo:repo)\n$(McrTagsYmlTagGroup:tag1a)\n", "images": [{"platforms": [{"dockerfile_dir": "1.0/repo/os", "undocumented_tags": ["tag2"]}]}, {"platforms": [{"dockerfile_dir": "1.0/repo/os2", "tags": ["tag1a", "tag1b"]}], "shared_tags": {"shared": {"doc_type": "PlatformDocumented"}}}]}, "expected_output": "repos:\n- repoName: public/repo\n  customTablePivots: true\n  tagGroups:\n  - tags: [ tag1a, tag1b, shared ]\n    architecture: amd64\n    os: linux\n    osVersion: Ubuntu 20.04\n    dockerfile: https://example.com/org/repo/blob/branch/1.0/repo/os2/Dockerfile\n"}
    ]
}
```

*6.3 Duplicated-platform tag combination — merge identical platforms across images into one ordered tag group.*

When the same platform (identical Dockerfile and platform attributes) is defined in more than one image so that distinct sets of shared tags can be associated with it, the duplicated platforms are combined into a single tag group. The combined tag list is ordered from most specific to least specific: first the concrete platform tags in declaration order, then the shared tags belonging to images that have no documented concrete tags, then the shared tags belonging to images that do have documented concrete tags.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_mcr_tags_duplicated_platform.json`

```json
{
    "description": "Generate the registry tags metadata YAML when the same platform (identical Dockerfile and platform attributes) is defined in more than one image so that distinct sets of shared tags can be associated with it. The duplicated platforms are combined into a single tag group. The combined tag list is ordered from most specific to least specific: first the concrete platform tags (in declaration order), then the shared tags belonging to images that have no documented concrete tags, then the shared tags belonging to images that do have documented concrete tags.",
    "cases": [
        {"input": {"action": "mcr_tags", "repo": "repo", "generate_github_links": true, "source_repo_url": "https://example.com/org/repo", "source_branch": "branch", "template": "$(McrTagsYmlRepo:repo)\n$(McrTagsYmlTagGroup:concreteTagA)\n", "images": [{"platforms": [{"dockerfile_dir": "1.0/repo/os", "tags": ["concreteTagZ", "concreteTagA"]}], "shared_tags": {"shared1": {}, "latest": {}}}, {"platforms": [{"dockerfile_dir": "1.0/repo/os"}], "shared_tags": {"shared2": {}}}]}, "expected_output": "repos:\n- repoName: public/repo\n  customTablePivots: true\n  tagGroups:\n  - tags: [ concreteTagZ, concreteTagA, shared2, shared1, latest ]\n    architecture: amd64\n    os: linux\n    osVersion: Ubuntu 20.04\n    dockerfile: https://example.com/org/repo/blob/branch/1.0/repo/os/Dockerfile\n"}
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the naming/formatting helpers, the variable resolver, the catalog-composition loader, and the tag-metadata renderer described above, with the core domain fully decoupled from I/O.

2. **The Execution/Test Adapter:** A runnable entry point that acts as a client to the core system. It reads a single JSON command object from stdin, dispatches on the `action` field, invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. All error conditions are rendered as the language-neutral `error=<category>` lines specified above; no host-language exception identifiers or runtime message fragments may appear in stdout.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_1_architecture_display_name.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_architecture_display_name@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the same templating syntax as the variable resolver module
- derive defaults from the Dockerfile parsing context
