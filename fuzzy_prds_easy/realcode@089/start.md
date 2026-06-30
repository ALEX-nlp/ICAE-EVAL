## Product Requirement Document

# Container Image Version Toolkit - Registry-Aware Tag Parsing & Comparison

## Project Goal

Build a small library that allows developers to reason about container image references the way a registry-watching controller does: parse a raw image tag into a comparable version, decide which of two tags is older, recognise which public registry a host belongs to, decompose an image path into its repository and image parts, and route a full image URL to the registry that should serve it — all as pure, deterministic functions with no network access required.

---

## Background & Problem

Without this toolkit, developers who want to track "is a newer image available?" are forced to hand-roll fragile string parsing for every registry: tags come in wildly inconsistent shapes (`1`, `v1.0.1`, `0.21.0-debian-10-r39`, `v1.3.hello1-debian-3.hello-world-12`), each registry names repositories and images differently, and host detection done with naive substring checks accidentally matches look-alike domains such as `foodocker.io` or `docker.iofoo`. This leads to repetitive, error-prone boilerplate and subtle ordering bugs (e.g. treating a pre-release `-alpha` build as newer than its final release).

With this toolkit, a caller hands in a raw tag or image URL and gets back a structured, comparable result: a numeric version triple plus a preserved metadata suffix, a correct older/newer decision that understands pre-release suffixes and numeric-vs-lexical segments, strict host matching that only accepts a registry's real domain and its subdomains, and a single routing entry point that maps any image URL to the right registry, host, and path.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. This domain has several distinct responsibilities — version parsing/comparison, per-registry host matching, per-registry path splitting, and URL routing — so it MUST be organised into clear, separated units (e.g. a version module and a registry/client module with one sub-unit per registry) rather than a single monolithic file. Do not over-engineer, but do not collapse distinct registries into one tangled function either.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases below represent a **black-box testing contract** for an execution adapter, NOT the internal data model of the core system. The core logic must remain decoupled from stdin/stdout and JSON parsing. An execution adapter is solely responsible for translating JSON commands into idiomatic calls to the core domain and rendering results in the line-based contract shown here.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility:** Keep version logic, host matching, path splitting, routing, and output formatting in distinct units.
   - **Open/Closed:** Adding a new registry should mean adding a new unit that satisfies the registry abstraction, not editing the router's core.
   - **Liskov Substitution:** Every registry handler must be substitutable wherever the registry abstraction is expected.
   - **Interface Segregation:** The registry abstraction should expose only what routing needs (host test, path split, tag listing).
   - **Dependency Inversion:** The router must depend on the registry abstraction, not on any concrete registry implementation.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface must be elegant and idiomatic to the target language, hiding internal parsing complexity.
   - **Resilience:** Edge cases (empty strings, single-segment paths, tags with no numbers, unknown registries) must be handled gracefully and deterministically rather than throwing generic faults. Where an input is invalid, errors are surfaced as a normalised, language-neutral category rather than a host-runtime exception.

---

## Core Features

### Feature 1: Image Tag Version Parsing

**As a developer**, I want to parse an arbitrary image tag into a numeric major/minor/patch triple plus a metadata suffix, so I can compare and reason about versions regardless of how the tag was formatted.

**Expected Behavior / Usage:**

The input is a single tag string. The output reports the original tag, the three numeric components, and the metadata suffix. Parsing rules: an optional leading `v` is ignored; the version is read as up to three dot-separated leading integers; any component that is absent defaults to `0`. Everything after the matched numeric prefix is preserved verbatim as `metadata`. If the string does not begin with a number at all (e.g. `v` alone, or `hello-1.2.3`), the version is `0.0.0` and the entire original string becomes the metadata. Note that only the first three dot-separated groups are treated as numbers: in `v1.3.hello1-...` the third group is non-numeric, so patch is `0` and metadata begins at `.hello1...`. The output is five lines: `tag=<tag>`, `major=<n>`, `minor=<n>`, `patch=<n>`, `metadata=<suffix>`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_version_parsing.json`

```json
{
    "description": "Parse a container image tag into a three-part numeric version (major, minor, patch) plus a free-form metadata suffix. A leading 'v' is optional. Missing numeric components default to 0. Any text that follows the patch number (or any text that prevents a leading numeric match) is preserved verbatim as metadata. Tags that do not start with a number yield a zero version and carry the whole string as metadata.",
    "cases": [
        {
            "input": {"action": "parse_version", "tag": "v1.0.1"},
            "expected_output": "tag=v1.0.1\nmajor=1\nminor=0\npatch=1\nmetadata="
        },
        {
            "input": {"action": "parse_version", "tag": "1.2"},
            "expected_output": "tag=1.2\nmajor=1\nminor=2\npatch=0\nmetadata="
        },
        {
            "input": {"action": "parse_version", "tag": "v1.0.1-debian-3.hello-world-12"},
            "expected_output": "tag=v1.0.1-debian-3.hello-world-12\nmajor=1\nminor=0\npatch=1\nmetadata=-debian-3.hello-world-12"
        },
        {
            "input": {"action": "parse_version", "tag": "hello-1.2.3"},
            "expected_output": "tag=hello-1.2.3\nmajor=0\nminor=0\npatch=0\nmetadata=hello-1.2.3"
        }
    ]
}
```

---

### Feature 2: Version Ordering (Older / Newer)

**As a developer**, I want to ask whether one tag is strictly older than another, so I can decide if a newer image is available.

**Expected Behavior / Usage:**

The input is two tag strings, `first` and `second`. The output echoes both and reports `[a specific boolean literal derived from string comparison]<bool>`, true when `first` represents an older version than `second`. Ordering rules, applied in order: (1) if either tag is empty, order purely by string length (shorter is "less", equal length is not less); (2) if `first` has no metadata suffix but `second` does, `first` is treated as the newer release, so the result is false — a final release outranks a same-numbered pre-release; (3) compare the numeric major/minor/patch triple, lower is older; (4) on a numeric tie, tokenise each metadata suffix into alternating runs of digits and non-digits and compare token-by-token left to right — digit runs compare numerically (so `r9` < `r39`), non-digit runs compare lexically (so `alpha` < `beta`); the side that runs out of tokens first is the older one. Two arbitrary non-numeric strings of differing content never compare as less-than under these rules.

**Test Cases:** `rcb_tests/public_test_cases/feature2_version_comparison.json`

```json
{
    "description": "Determine whether one image tag represents an older version than another, returning a boolean ordering result. Comparison first weighs the numeric major/minor/patch triple; ties are broken by tokenising the metadata suffix into alternating number/word segments and comparing them left-to-right (numbers compared numerically, words lexicographically). A tag with no metadata is considered newer than the same numeric version with a pre-release metadata suffix. Empty tags order purely by length. Two arbitrary non-numeric strings never order as less-than.",
    "cases": [
        {
            "input": {"action": "compare_versions", "first": "v0.1.2", "second": "v0.1.3"},
            "expected_output": "first=v0.1.2\nsecond=v0.1.3\n[a specific boolean literal derived from string comparison]true"
        },
        {
            "input": {"action": "compare_versions", "first": "v0.1.2", "second": "v0.1.3-alpha"},
            "expected_output": "first=v0.1.2\nsecond=v0.1.3-alpha\n[a specific boolean literal derived from string comparison]false"
        },
        {
            "input": {"action": "compare_versions", "first": "v0.1.3-alpha.0", "second": "v0.1.3-alpha.1"},
            "expected_output": "first=v0.1.3-alpha.0\nsecond=v0.1.3-alpha.1\n[a specific boolean literal derived from string comparison]true"
        },
        {
            "input": {"action": "compare_versions", "first": "0.21.0-debian-10-r9", "second": "0.21.0-debian-10-r39"},
            "expected_output": "first=0.21.0-debian-10-r9\nsecond=0.21.0-debian-10-r39\n[a specific boolean literal derived from string comparison]true"
        }
    ]
}
```

---

### Feature 3: Registry Host Recognition

**As a developer**, I want to test whether a given host belongs to a specific public registry, so I can pick the right client without being fooled by look-alike domains.

**Expected Behavior / Usage:**

Each leaf below covers one registry. The input is a registry selector plus a host string; the output is `registry=<name>`, `host=<host>`, `match=<bool>`. A host matches a registry only if it equals the registry's canonical domain exactly, or is a subdomain ending in `.<canonical-domain>`. Substrings glued onto either end (e.g. `foodocker.io`, `docker.iofoo`) must NOT match, and an empty host never matches.

*3.1 Docker Hub host recognition — matches `docker.io`, `docker.com`, and their subdomains*

A host matches when it is exactly `docker.io` or `docker.com`, or ends in `.docker.io` / `.docker.com`. Anything else, including substring look-alikes and the empty string, does not match.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_host_match_docker.json`

```json
{
    "description": "Decide whether a registry host string belongs to the Docker Hub registry. A host matches only when it is exactly docker.io or docker.com, or any subdomain ending in .docker.io / .docker.com. Strings that merely contain the substring (prefix or suffix glued on) do not match, and an empty host never matches.",
    "cases": [
        {
            "input": {"action": "match_host", "registry": "docker", "host": "docker.io"},
            "expected_output": "registry=docker\nhost=docker.io\nmatch=true"
        },
        {
            "input": {"action": "match_host", "registry": "docker", "host": "foo.bar.docker.com"},
            "expected_output": "registry=docker\nhost=foo.bar.docker.com\nmatch=true"
        },
        {
            "input": {"action": "match_host", "registry": "docker", "host": "foodocker.io"},
            "expected_output": "registry=docker\nhost=foodocker.io\nmatch=false"
        },
        {
            "input": {"action": "match_host", "registry": "docker", "host": "docker.iofoo"},
            "expected_output": "registry=docker\nhost=docker.iofoo\nmatch=false"
        }
    ]
}
```

*3.2 GCR host recognition — matches `gcr.io` and its subdomains*

A host matches when it is exactly `gcr.io` or ends in `.gcr.io`. Substring look-alikes (`foogcr.io`, `gcr.iofoo`) and the empty string do not match.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_host_match_gcr.json`

```json
{
    "description": "Decide whether a registry host string belongs to the GCR registry. A host matches only when it is exactly gcr.io or any subdomain ending in .gcr.io. Strings that merely contain the substring (prefix or suffix glued on) do not match, and an empty host never matches.",
    "cases": [
        {
            "input": {"action": "match_host", "registry": "gcr", "host": "gcr.io"},
            "expected_output": "registry=gcr\nhost=gcr.io\nmatch=true"
        },
        {
            "input": {"action": "match_host", "registry": "gcr", "host": "k8s.gcr.io"},
            "expected_output": "registry=gcr\nhost=k8s.gcr.io\nmatch=true"
        },
        {
            "input": {"action": "match_host", "registry": "gcr", "host": "foogcr.io"},
            "expected_output": "registry=gcr\nhost=foogcr.io\nmatch=false"
        }
    ]
}
```

*3.3 Quay host recognition — matches `quay.io` and its subdomains*

A host matches when it is exactly `quay.io` or ends in `.quay.io`. Substring look-alikes (`fooquay.io`, `quay.iofoo`) and the empty string do not match.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_host_match_quay.json`

```json
{
    "description": "Decide whether a registry host string belongs to the Quay registry. A host matches only when it is exactly quay.io or any subdomain ending in .quay.io. Strings that merely contain the substring (prefix or suffix glued on) do not match, and an empty host never matches.",
    "cases": [
        {
            "input": {"action": "match_host", "registry": "quay", "host": "quay.io"},
            "expected_output": "registry=quay\nhost=quay.io\nmatch=true"
        },
        {
            "input": {"action": "match_host", "registry": "quay", "host": "k8s.quay.io"},
            "expected_output": "registry=quay\nhost=k8s.quay.io\nmatch=true"
        },
        {
            "input": {"action": "match_host", "registry": "quay", "host": "quay.iofoo"},
            "expected_output": "registry=quay\nhost=quay.iofoo\nmatch=false"
        }
    ]
}
```

---

### Feature 4: Image Path Decomposition

**As a developer**, I want to split a registry path into its repository and image name, so I can build the registry-specific API calls that list available tags.

**Expected Behavior / Usage:**

Each leaf below covers one registry, because each applies a different default for bare single-segment paths. The input is a registry selector plus a path; the output is `registry=<name>`, `path=<path>`, `repo=<repo>`, `image=<image>`.

*4.1 Docker Hub path split — single segment defaults to the `library` repository*

A single segment `x` becomes repository `library`, image `x`. With two or more slash-separated segments, only the last two are used: the second-to-last is the repository and the last is the image; any earlier segments are discarded.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_path_split_docker.json`

```json
{
    "description": "Split a Docker Hub image path into a repository and image name. A bare single segment is treated as an official image under the implicit 'library' repository. When the path has two or more segments, only the last two are used: the second-to-last is the repository and the last is the image (any leading registry segments are discarded).",
    "cases": [
        {
            "input": {"action": "split_path", "registry": "docker", "path": "nginx"},
            "expected_output": "registry=docker\npath=nginx\nrepo=library\nimage=nginx"
        },
        {
            "input": {"action": "split_path", "registry": "docker", "path": "joshvanl/version-checker"},
            "expected_output": "registry=docker\npath=joshvanl/version-checker\nrepo=joshvanl\nimage=version-checker"
        },
        {
            "input": {"action": "split_path", "registry": "docker", "path": "registry/joshvanl/version-checker"},
            "expected_output": "registry=docker\npath=registry/joshvanl/version-checker\nrepo=joshvanl\nimage=version-checker"
        }
    ]
}
```

*4.2 GCR path split — single segment defaults to the `google-containers` repository*

A single segment `x` becomes repository `google-containers`, image `x`. When the path contains slashes, everything before the last slash is the repository (intermediate segments preserved) and the final segment is the image.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_path_split_gcr.json`

```json
{
    "description": "Split a GCR image path into a repository and image name. A bare single segment is treated as an image under the implicit 'google-containers' repository. When the path contains slashes, everything before the last slash becomes the repository (preserving intermediate segments) and the final segment is the image.",
    "cases": [
        {
            "input": {"action": "split_path", "registry": "gcr", "path": "kube-scheduler"},
            "expected_output": "registry=gcr\npath=kube-scheduler\nrepo=google-containers\nimage=kube-scheduler"
        },
        {
            "input": {"action": "split_path", "registry": "gcr", "path": "k8s-artifacts-prod/ingress-nginx/nginx"},
            "expected_output": "registry=gcr\npath=k8s-artifacts-prod/ingress-nginx/nginx\nrepo=k8s-artifacts-prod/ingress-nginx\nimage=nginx"
        }
    ]
}
```

*4.3 Quay path split — single segment becomes the repository with an empty image*

A single segment `x` becomes repository `x`, image empty. When the path contains slashes, everything before the last slash is the repository (intermediate segments preserved) and the final segment is the image.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_path_split_quay.json`

```json
{
    "description": "Split a Quay image path into a repository and image name. A bare single segment is treated as the repository with an empty image. When the path contains slashes, everything before the last slash becomes the repository (preserving intermediate segments) and the final segment is the image.",
    "cases": [
        {
            "input": {"action": "split_path", "registry": "quay", "path": "version-checker"},
            "expected_output": "registry=quay\npath=version-checker\nrepo=version-checker\nimage="
        },
        {
            "input": {"action": "split_path", "registry": "quay", "path": "jetstack/version-checker"},
            "expected_output": "registry=quay\npath=jetstack/version-checker\nrepo=jetstack\nimage=version-checker"
        },
        {
            "input": {"action": "split_path", "registry": "quay", "path": "k8s-artifacts-prod/ingress-nginx/nginx"},
            "expected_output": "registry=quay\npath=k8s-artifacts-prod/ingress-nginx/nginx\nrepo=k8s-artifacts-prod/ingress-nginx\nimage=nginx"
        }
    ]
}
```

---

### Feature 5: Image URL Routing

**As a developer**, I want to hand a full image URL to a single entry point and learn which registry will serve it together with the host and remaining path, so I can dispatch tag lookups without writing per-registry detection myself.

**Expected Behavior / Usage:**

The input is one `url` string. The output is `url=<url>`, `registry=<name>`, `host=<host>`, `path=<path>`. Routing splits the URL on its first slash into a candidate host and a remainder. If the candidate host satisfies the Docker, GCR, or Quay host rules (Feature 3), the URL routes to that registry with that host and the remainder as the path. Otherwise — including when the URL has no slash at all, or when the leading segment is not a recognised registry host — it falls back to the Docker registry with an empty host and the entire original string as the path. The registry name reported is one of `docker`, `gcr`, or `quay`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_url_routing.json`

```json
{
    "description": "Route a full image URL to the registry that should handle it, also reporting the host and the remaining path. The first slash-delimited segment is treated as a candidate host: if it matches the Docker, GCR, or Quay host rules the URL is routed there with that host and the remainder as path. A URL with no slash, or whose leading segment matches no known registry host, falls back to the Docker registry with an empty host and the entire original string as the path.",
    "cases": [
        {
            "input": {"action": "route_url", "url": "nginx"},
            "expected_output": "url=nginx\nregistry=docker\nhost=\npath=nginx"
        },
        {
            "input": {"action": "route_url", "url": "docker.io/joshvanl/version-checker"},
            "expected_output": "url=docker.io/joshvanl/version-checker\nregistry=docker\nhost=docker.io\npath=joshvanl/version-checker"
        },
        {
            "input": {"action": "route_url", "url": "us.gcr.io/k8s-artifacts-prod/ingress-nginx/nginx"},
            "expected_output": "url=us.gcr.io/k8s-artifacts-prod/ingress-nginx/nginx\nregistry=gcr\nhost=us.gcr.io\npath=k8s-artifacts-prod/ingress-nginx/nginx"
        },
        {
            "input": {"action": "route_url", "url": "quay.io/jetstack/version-checker"},
            "expected_output": "url=quay.io/jetstack/version-checker\nregistry=quay\nhost=quay.io\npath=jetstack/version-checker"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured codebase implementing the features above — a version module (parsing + ordering) and a registry/client module with one cohesive sub-unit per registry (host matching + path splitting) behind a shared registry abstraction, plus the URL router that depends on that abstraction. The physical structure MUST follow the "Scale-Driven Code Organization" constraint: multiple files reflecting these responsibilities, not a single god file.

2. **The Execution/Test Adapter:** A runnable program that acts as a client to the core system. It reads one JSON command from stdin (`action` plus the fields shown in each feature's cases), invokes the appropriate core logic, and prints the result to stdout in the exact line-based contract above. Invalid or unknown commands are rendered as a normalised, language-neutral `error=<category>` line (e.g. `error=unknown_action`, `error=unknown_registry`, `error=invalid_input`) — never as a host-runtime exception dump. This adapter must be logically and physically separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_version_parsing.json` under `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_version_parsing@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` file contains **only** the raw stdout of the program under test (no PASS/FAIL or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- align with the standard Docker suffix patterns defined in C014
- utilize the splitting logic for multi-segment paths as per C020
