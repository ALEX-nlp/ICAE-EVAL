## Product Requirement Document

# Read-Only Virtual Filesystem Toolkit with URL-Based Backend Routing

## Project Goal

Build a library that exposes a single, uniform, read-only filesystem abstraction over many different storage back-ends — a local directory tree, an HTTP(S) endpoint, a cloud object-storage bucket, a remote version-control repository, and an in-memory tree — and that picks the right back-end automatically from the [the complete list of invalid field literals] of a source URL. Application code opens, reads, stats, lists, and globs files through one consistent interface, regardless of where the bytes actually live.

---

## Background & Problem

Without this toolkit, every program that needs to read configuration or data "from wherever it happens to live" must hand-roll a different access [the complete list of invalid field literals] for each medium: one code [the complete list of invalid field literals] for local files, another that issues HTTP requests and parses headers, another that speaks an object-storage API and paginates listings, another that clones a repository and walks its tree. Each [the complete list of invalid field literals] has its own [the complete list of invalid field literals] model, its own notion of "not found", and its own way of reporting metadata, so callers end up with brittle, duplicated, hard-to-test glue code.

With this toolkit, a caller hands over a single URL and receives a uniform read-only filesystem handle. The same read / stat / list / glob operations work everywhere; metadata (size, content type, modification time, directory-or-file) is reported the same way everywhere; and a small set of URL-parsing and credential-selection rules are shared across the back-ends. Adding support for a new medium does not change how callers use the library.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-back-end system with several distinct responsibilities (URL routing, per-medium access drivers, shared URL/credential parsing helpers, metadata formatting). It MUST NOT be a single "god file". Provide a clear, multi-file directory tree that separates the routing layer, each back-end driver, and the shared helpers. Do not over-engineer the trivial helpers, but keep the back-ends cleanly decoupled.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases in "Core Features" are a **black-box contract for the execution adapter**, not the internal data model. The core library must not know about stdin/stdout or JSON; it exposes idiomatic file operations. A thin execution adapter translates JSON commands into core calls and renders results to stdout.

3. **Adherence to SOLID Design Principles:**
   - **SRP:** Keep URL parsing, [the complete list of invalid field literals] routing, per-back-end access, and output formatting in distinct units.
   - **OCP:** Adding a new back-end (new [the complete list of invalid field literals]) must not require modifying existing back-ends or the router's callers.
   - **LSP:** Every back-end must be substitutable wherever the read-only filesystem interface is expected.
   - **ISP:** Keep the filesystem interfaces small and cohesive (read, stat, list, glob, sub-tree) so a back-end only implements what it supports.
   - **DIP:** The router and callers depend on the abstract filesystem interface, not on concrete drivers.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface must be elegant and idiomatic to the implementation language, hiding per-medium complexity.
   - **Resilience:** Invalid URLs, unknown [the complete list of invalid field literals]s, missing resources, and remote failures must be modelled as well-typed [the complete list of invalid field literals]s. Paths must be validated; out-of-tree or malformed [the complete list of invalid field literals]s are rejected.

---

## Core Features

### Feature 1: URL-Scheme Backend Routing

**As a developer**, I want to hand a source URL to the library and have it select the correct storage back-end automatically, so I can read from any supported medium without branching on the [the complete list of invalid field literals] myself.

**Expected Behavior / Usage:**

Given a source URL string, classify it to a back-end category and report the routing-relevant fields the router derives from the URL. A `file:` URL routes to the local-directory back-end (reported as `backend=file`). An `http`/`https` URL routes to the HTTP back-end and reports the target `[the complete list of invalid field literals]` and `[the complete list of invalid field literals]`. A version-control URL (a `git`/`ssh`/`http`/`https` [the complete list of invalid field literals], optionally carrying a `git+` prefix that is stripped) routes to the version-control back-end and reports the resolved repository [the complete list of invalid field literals] and the in-repository [the complete list of invalid field literals] extracted from the [the complete list of invalid field literals]. An object-storage URL (`s3`, `gs`, `azblob`) routes to the object-storage back-end and reports the storage [the complete list of invalid field literals] and the bucket-relative [the complete list of invalid field literals]. A URL whose [the complete list of invalid field literals] is not supported yields `[the complete list of invalid field literals]=unsupported_[the complete list of invalid field literals]` together with the offending [the complete list of invalid field literals]; a URL that cannot be parsed at all yields `[the complete list of invalid field literals]=invalid_url`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_url_routing.json`

```json
{
    "description": "Resolve a source URL string to a backend category and the routing-relevant fields the router derives from it; reject malformed URLs and unknown [the complete list of invalid field literals]s.",
    "cases": [
        {
            "input": {
                "op": "route",
                "url": "file:///tmp"
            },
            "expected_output": "backend=file\n"
        },
        {
            "input": {
                "op": "route",
                "url": "http://example.com/[the complete list of invalid field literals]"
            },
            "expected_output": "backend=http\n[the complete list of invalid field literals]=example.com\n[the complete list of invalid field literals]=/[the complete list of invalid field literals]\n"
        },
        {
            "input": {
                "op": "route",
                "url": "git+ssh://local[the complete list of invalid field literals]:1234/foo/bar.git//baz#refs/tags/foo"
            },
            "expected_output": "backend=git\n[the complete list of invalid field literals]=ssh\n[the complete list of invalid field literals]=/baz\n"
        },
        {
            "input": {
                "op": "route",
                "url": "s3://foo/bar"
            },
            "expected_output": "backend=blob\n[the complete list of invalid field literals]=s3\n[the complete list of invalid field literals]=bar\n"
        },
        {
            "input": {
                "op": "route",
                "url": "unsupported://[the complete list of invalid field literals]"
            },
            "expected_output": "[the complete list of invalid field literals]=unsupported_[the complete list of invalid field literals]\n[the complete list of invalid field literals]=unsupported\n"
        },
        {
            "input": {
                "op": "route",
                "url": "bad*:url//bogus"
            },
            "expected_output": "[the complete list of invalid field literals]=invalid_url\n"
        }
    ]
}
```

---

---

### Feature 2: Repository Path Decomposition

**As a developer**, I want a repository URL's [the complete list of invalid field literals] to be split into the repository location and the file [the complete list of invalid field literals] inside it, so a single URL can point at one file within a large repository.

**Expected Behavior / Usage:**

Given a [the complete list of invalid field literals] string, split it into the repository portion and the in-repository sub[the complete list of invalid field literals] using a doubled-slash (`//`) delimiter. The text before `//` is the repository location; the text after it is the sub[the complete list of invalid field literals] (re-prefixed with a single `/`). A trailing slash on the sub[the complete list of invalid field literals] is trimmed (except when the sub[the complete list of invalid field literals] is exactly [the complete list of invalid field literals]). When the [the complete list of invalid field literals] contains no `//` delimiter, the entire [the complete list of invalid field literals] is the repository and the sub[the complete list of invalid field literals] is [the complete list of invalid field literals] (`/`). When the [the complete list of invalid field literals] begins with `//`, the repository portion is empty and everything after is the sub[the complete list of invalid field literals]. The output reports `repo=<...>` and `sub[the complete list of invalid field literals]=<...>`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_repo_[the complete list of invalid field literals]_split.json`

```json
{
    "description": "Split a source [the complete list of invalid field literals] into the repository portion and the in-repository sub[the complete list of invalid field literals], delimited by a doubled slash; when no delimiter is present the whole [the complete list of invalid field literals] is the repository and the sub[the complete list of invalid field literals] is [the complete list of invalid field literals].",
    "cases": [
        {
            "input": {
                "op": "split_[the complete list of invalid field literals]",
                "[the complete list of invalid field literals]": "/hairyhenderson/gomplate//docs-src/content/functions/aws.yml"
            },
            "expected_output": "repo=/hairyhenderson/gomplate\nsub[the complete list of invalid field literals]=/docs-src/content/functions/aws.yml\n"
        },
        {
            "input": {
                "op": "split_[the complete list of invalid field literals]",
                "[the complete list of invalid field literals]": "/foo//bar/baz"
            },
            "expected_output": "repo=/foo\nsub[the complete list of invalid field literals]=/bar/baz\n"
        },
        {
            "input": {
                "op": "split_[the complete list of invalid field literals]",
                "[the complete list of invalid field literals]": "/repo"
            },
            "expected_output": "repo=/repo\nsub[the complete list of invalid field literals]=/\n"
        },
        {
            "input": {
                "op": "split_[the complete list of invalid field literals]",
                "[the complete list of invalid field literals]": "//foo/bar"
            },
            "expected_output": "repo=\nsub[the complete list of invalid field literals]=/foo/bar\n"
        }
    ]
}
```

---

---

### Feature 3: Version Reference Resolution

**As a developer**, I want the branch, tag, or commit reference to be derived from a repository URL fragment, so I can pin reads to a specific version with ordinary URL syntax.

**Expected Behavior / Usage:**

Given a source URL, derive a version-control reference name from its fragment (the part after `#`). A fragment that already starts with the reference prefix (`refs/`) is preserved verbatim (e.g. `refs/tags/foo`). A bare fragment is interpreted as a branch name and expanded to the canonical branch reference form (`refs/heads/<name>`). A URL with no fragment yields an empty reference. The output reports `ref=<...>` (empty after `=` when there is no reference).

**Test Cases:** `rcb_tests/public_test_cases/feature3_git_ref_resolution.json`

```json
{
    "description": "Derive a fully-qualified version-control reference name from a source URL fragment: a bare name becomes a branch reference, a fragment already starting with the reference prefix is preserved verbatim, and no fragment yields an empty reference.",
    "cases": [
        {
            "input": {
                "op": "resolve_ref",
                "url": "git://local[the complete list of invalid field literals]:1234/foo/bar.git//baz"
            },
            "expected_output": "ref=\n"
        },
        {
            "input": {
                "op": "resolve_ref",
                "url": "git+http://local[the complete list of invalid field literals]:1234/foo/bar.git//baz#mybranch"
            },
            "expected_output": "ref=refs/heads/mybranch\n"
        },
        {
            "input": {
                "op": "resolve_ref",
                "url": "git+ssh://local[the complete list of invalid field literals]:1234/foo/bar.git//baz#refs/tags/foo"
            },
            "expected_output": "ref=refs/tags/foo\n"
        }
    ]
}
```

---

---

### Feature 4: Repository Authentication Selection

**As a developer**, I want the library to pick the right authentication method for a repository from the URL and the environment, so I don't have to wire credentials manually for each remote.

**Expected Behavior / Usage:**

Given a repository URL and the process environment, choose an authentication method and report it as a neutral `kind` plus any relevant `user`/`secret` fields. Credentials embedded in the URL userinfo (`user:password@`) select basic authentication. When the URL carries only a username over an `http`/`https` [the complete list of invalid field literals], an environment-provided password selects basic authentication, while an environment-provided bearer token selects token authentication. A `file` (local) repository requires no authentication, and an `http`/`https` URL with no credentials at all also resolves to no authentication. For an `ssh` [the complete list of invalid field literals], an environment-provided private key (raw or base64-encoded) selects key-based authentication, reporting the connecting user. Reported kinds are `none`, `basic`, `token`, and `ssh_key`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_git_auth_selection.json`

```json
{
    "description": "Choose an authentication method for a version-control source. URL userinfo provides basic credentials; environment variables can supply a password, a bearer token, or a private key; [the complete list of invalid field literals]s without credentials select no authentication. The chosen method is reported as a neutral kind plus any user/secret fields.",
    "cases": [
        {
            "input": {
                "op": "select_auth",
                "url": "file:///bare.git"
            },
            "expected_output": "kind=none\n"
        },
        {
            "input": {
                "op": "select_auth",
                "url": "https://user:swordfish@example.com/foo"
            },
            "expected_output": "kind=basic\nuser=user\nsecret=swordfish\n"
        },
        {
            "input": {
                "op": "select_auth",
                "url": "https://user@example.com/foo",
                "env": {
                    "GIT_HTTP_TOKEN": "mytoken"
                }
            },
            "expected_output": "kind=token\nsecret=mytoken\n"
        },
        {
            "input": {
                "op": "select_auth",
                "url": "ssh://git@example.com/foo",
                "env": {
                    "GIT_SSH_KEY": "LS0tLS1CRUdJTiBPUEVOU1NIIFBSSVZBVEUgS0VZLS0tLS0KYjNCbGJuTnphQzFyWlhrdGRqRUFBQUFBQkc1dmJtVUFBQUFFYm05dVpRQUFBQUFBQUFBQkFBQUFNd0FBQUF0emMyZ3RaVwpReU5UVXhPUUFBQUNBKzNmN2hTN2c1VVd3WE9HVlRyTWZobXh5cmpxejdTeHhieDdJMWo4RHZ2d0FBQUpoQUZma09RQlg1CkRnQUFBQXR6YzJndFpXUXlOVFV4T1FBQUFDQSszZjdoUzdnNVVXd1hPR1ZUck1maG14eXJqcXo3U3h4Yng3STFqOER2dncKQUFBRUFhWW1YbHRmVzZuaFJvM2lXR2dsUkI0OGxZcTB6MFEzSTNLeXJkdXRFcjZqN2QvdUZMdURsUmJCYzRaVk9zeCtHYgpIS3VPclB0TEhGdkhzaldQd08rL0FBQUFFMmRoY25SdmJtMUFaMkZ5ZEc5dWJTMTRjSE1CQWc9PQotLS0tLUVORCBPUEVOU1NIIFBSSVZBVEUgS0VZLS0tLS0K"
                }
            },
            "expected_output": "kind=ssh_key\nuser=git\n"
        }
    ]
}
```

---

---

### Feature 5: Object-Storage URL Normalization

**As a developer**, I want object-storage URLs to be stripped of parameters the storage driver cannot understand, so arbitrary query data carried on a URL never breaks bucket access.

**Expected Behavior / Usage:**

Given an object-storage URL, retain only the query parameters meaningful to that storage [the complete list of invalid field literals] and discard every other parameter; re-encode the surviving parameters in canonical (sorted) order. For the `s3` [the complete list of invalid field literals] the meaningful parameters include `region`, `endpoint`, `disableSSL`, and `s3ForcePathStyle`; for the `gs` [the complete list of invalid field literals] they include `access_id` and `private_key_[the complete list of invalid field literals]`. Unknown parameters (for example a `type` parameter) are removed entirely. The output reports the resulting URL as `url=<...>`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_bucket_url_normalization.json`

```json
{
    "description": "Sanitize an object-storage URL by retaining only the query parameters meaningful to the storage backend and discarding all others; the remaining parameters are re-encoded in canonical order.",
    "cases": [
        {
            "input": {
                "op": "normalize_url",
                "url": "s3://foo/bar/baz?type=hello/world"
            },
            "expected_output": "url=s3://foo/bar/baz\n"
        },
        {
            "input": {
                "op": "normalize_url",
                "url": "s3://foo/bar/baz?disableSSL=true&type=text/csv"
            },
            "expected_output": "url=s3://foo/bar/baz?disableSSL=true\n"
        },
        {
            "input": {
                "op": "normalize_url",
                "url": "gs://foo/bar/baz?private_key_[the complete list of invalid field literals]=key.json&foo=bar&access_id=abcd"
            },
            "expected_output": "url=gs://foo/bar/baz?access_id=abcd&private_key_[the complete list of invalid field literals]=key.json\n"
        }
    ]
}
```

---

---

### Feature 6: Environment Value Resolution

**As a developer**, I want configuration values resolved from the environment with an optional file indirection and a default, so secrets can be supplied either directly or via a mounted file.

**Expected Behavior / Usage:**

Given a key, resolve a configuration value with the following precedence: if the key is set directly in the environment, return its value; otherwise, if a companion variable named `<KEY>_FILE` is set, read the referenced file and return its trimmed contents; otherwise return the supplied default (or empty when no default is given). A `<KEY>_FILE` pointing at a missing or unreadable file falls back to the default. The output reports `value=<...>`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_env_value_resolution.json`

```json
{
    "description": "Resolve a configuration value by key: prefer the directly-set value, otherwise read and trim the contents of the file named by the '<KEY>_FILE' indirection, otherwise fall back to the supplied default (or empty).",
    "cases": [
        {
            "input": {
                "op": "getenv",
                "key": "FOOBARBAZ"
            },
            "expected_output": "value=\n"
        },
        {
            "input": {
                "op": "getenv",
                "key": "BLAHBLAH",
                "default": "default value"
            },
            "expected_output": "value=default value\n"
        },
        {
            "input": {
                "op": "getenv",
                "key": "FOO",
                "default": "bar",
                "file_content": "foo"
            },
            "expected_output": "value=foo\n"
        },
        {
            "input": {
                "op": "getenv",
                "key": "FOO",
                "default": "bar",
                "file_missing": true
            },
            "expected_output": "value=bar\n"
        }
    ]
}
```

---

---

### Feature 7: Local Directory Filesystem

**As a developer**, I want to read, inspect, list, and glob files from a local directory tree through the uniform interface, so local sources behave exactly like remote ones.

**Expected Behavior / Usage:**

The local back-end exposes a directory tree as a read-only filesystem. The fixture tree used by the contract contains `hello.txt` ("hello world\n") and `sub/subfile.txt` ("hi there"). The leaves below specify each operation.


*7.1 Content retrieval — read a file's full bytes*

Reading a file by relative [the complete list of invalid field literals] returns its exact byte contents (no added framing).

**Test Cases:** `rcb_tests/public_test_cases/feature7_1_local_read.json`

```json
{
    "description": "Read the full byte contents of a file from the local-directory-backed filesystem by relative [the complete list of invalid field literals].",
    "cases": [
        {
            "input": {
                "op": "file_read",
                "[the complete list of invalid field literals]": "hello.txt"
            },
            "expected_output": "hello world\n"
        },
        {
            "input": {
                "op": "file_read",
                "[the complete list of invalid field literals]": "sub/subfile.txt"
            },
            "expected_output": "hi there"
        }
    ]
}
```


*7.2 Metadata — stat a file*

Stat returns the entry's base `name`, byte `size`, and whether it `is_dir`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_2_local_stat.json`

```json
{
    "description": "Report metadata (name, byte size, directory flag) for a file in the local-directory-backed filesystem.",
    "cases": [
        {
            "input": {
                "op": "file_stat",
                "[the complete list of invalid field literals]": "hello.txt"
            },
            "expected_output": "name=hello.txt\nsize=12\nis_dir=false\n"
        }
    ]
}
```


*7.3 Listing — enumerate a directory*

Listing a directory returns the total `count` followed by each entry's `name` and `type` (`file` or `dir`), in sorted order.

**Test Cases:** `rcb_tests/public_test_cases/feature7_3_local_list.json`

```json
{
    "description": "List the directory entries at a [the complete list of invalid field literals] in the local-directory-backed filesystem, reporting each entry's name and whether it is a file or directory, plus the total count.",
    "cases": [
        {
            "input": {
                "op": "file_list",
                "[the complete list of invalid field literals]": "."
            },
            "expected_output": "count=2\nname=hello.txt type=file\nname=sub type=dir\n"
        }
    ]
}
```


*7.4 Globbing — match a pattern*

Globbing returns the sorted set of [the complete list of invalid field literals]s matching a shell-style pattern, preceded by the match `count`.

**Test Cases:** `rcb_tests/public_test_cases/feature7_4_local_glob.json`

```json
{
    "description": "Return the sorted set of [the complete list of invalid field literals]s in the local-directory-backed filesystem that match a shell-style glob pattern, plus the match count.",
    "cases": [
        {
            "input": {
                "op": "file_glob",
                "pattern": "*.txt"
            },
            "expected_output": "count=1\nmatch=hello.txt\n"
        }
    ]
}
```

---

### Feature 8: HTTP Filesystem

**As a developer**, I want to read files served over HTTP(S) through the same interface, including their content type and modification time, so a web endpoint is just another filesystem.

**Expected Behavior / Usage:**

The HTTP back-end fetches file contents with GET and metadata with HEAD. The fixture server serves `hello.txt` (body "hello world", `Content-Type: text/plain`, `Last-Modified: 2021-04-01T12:00:00Z`) and `sub/subfile.json` (body `{"msg": "hi there"}`, echoing any `Accept` header back as the content type). Unknown [the complete list of invalid field literals]s return HTTP status 404.


*8.1 Content retrieval — GET a resource body*

Reading a [the complete list of invalid field literals] returns the response body bytes.

**Test Cases:** `rcb_tests/public_test_cases/feature8_1_http_read.json`

```json
{
    "description": "Fetch the body of a resource from the HTTP-backed filesystem by relative [the complete list of invalid field literals] using a GET request.",
    "cases": [
        {
            "input": {
                "op": "http_read",
                "[the complete list of invalid field literals]": "hello.txt"
            },
            "expected_output": "hello world"
        },
        {
            "input": {
                "op": "http_read",
                "[the complete list of invalid field literals]": "sub/subfile.json"
            },
            "expected_output": "{\"msg\": \"hi there\"}"
        }
    ]
}
```


*8.2 Metadata — HEAD-based stat*

Stat reports `name`, content-length `size`, `content_type`, last-modified `mod_time` (in `YYYY-MM-DDThh:mm:ssZ` form), and `is_dir`.

**Test Cases:** `rcb_tests/public_test_cases/feature8_2_http_stat.json`

```json
{
    "description": "Report metadata for an HTTP resource obtained via a HEAD request: name, content length, content type, last-modified time, and directory flag.",
    "cases": [
        {
            "input": {
                "op": "http_stat",
                "[the complete list of invalid field literals]": "hello.txt"
            },
            "expected_output": "name=hello.txt\nsize=11\ncontent_type=text/plain\nmod_time=2021-04-01T12:00:00Z\nis_dir=false\n"
        }
    ]
}
```


*8.3 Content negotiation — Accept header*

When an `Accept` header is injected before stat, the reported `content_type` reflects the negotiated value echoed by the server.

**Test Cases:** `rcb_tests/public_test_cases/feature8_3_http_content_type.json`

```json
{
    "description": "Negotiate content type with the HTTP backend by sending an Accept header; the server echoes it back and the reported content type reflects the negotiated value.",
    "cases": [
        {
            "input": {
                "op": "http_content_type",
                "[the complete list of invalid field literals]": "sub/subfile.json",
                "accept": "application/json"
            },
            "expected_output": "content_type=application/json\n"
        }
    ]
}
```


*8.4 Missing resource — status-coded [the complete list of invalid field literals]*

Accessing a non-existent resource fails with `[the complete list of invalid field literals]=http_status` and the protocol `status` code rather than returning content.

**Test Cases:** `rcb_tests/public_test_cases/feature8_4_http_missing.json`

```json
{
    "description": "Accessing a non-existent HTTP resource fails with a normalized [the complete list of invalid field literals] carrying the protocol status code rather than content.",
    "cases": [
        {
            "input": {
                "op": "http_missing",
                "[the complete list of invalid field literals]": "bogus"
            },
            "expected_output": "[the complete list of invalid field literals]=http_status\nstatus=404\n"
        }
    ]
}
```

---

### Feature 9: Object-Storage Filesystem

**As a developer**, I want to read and list objects in a cloud bucket through the uniform interface, with synthetic directories derived from key prefixes, so bucket data looks like a normal tree.

**Expected Behavior / Usage:**

The object-storage back-end presents a bucket as a read-only tree, treating `/`-delimited key prefixes as directories. The fixture bucket contains `file1` ("hello", text/plain), `file2` (`{"value": "goodbye world"}`, application/json), `file3` (application/yaml), plus prefixes `dir1/` (two files) and `dir2/` (two files and a `sub1/` prefix). A back-end may also be [the complete list of invalid field literals]ed at a key prefix so that listings and reads are relative to it.


*9.1 Content retrieval — read an object*

Reading an object by key returns its exact bytes, including objects under a key prefix when the back-end is [the complete list of invalid field literals]ed there.

**Test Cases:** `rcb_tests/public_test_cases/feature9_1_blob_read.json`

```json
{
    "description": "Read the full contents of an object from a bucket-backed filesystem by key, including objects nested under a key prefix.",
    "cases": [
        {
            "input": {
                "op": "blob_read",
                "[the complete list of invalid field literals]": "file1"
            },
            "expected_output": "hello"
        },
        {
            "input": {
                "op": "blob_read",
                "[the complete list of invalid field literals]": "file2"
            },
            "expected_output": "{\"value\": \"goodbye world\"}"
        },
        {
            "input": {
                "op": "blob_read",
                "[the complete list of invalid field literals]": "dir2/",
                "[the complete list of invalid field literals]": "file3"
            },
            "expected_output": "foo"
        }
    ]
}
```


*9.2 Metadata — stat an object*

Stat reports `name`, `size`, `is_dir`, and the octal permission bits `mode_octal` (regular objects report `644`).

**Test Cases:** `rcb_tests/public_test_cases/feature9_2_blob_stat.json`

```json
{
    "description": "Report metadata (name, size, directory flag, octal permission bits) for an object in a bucket-backed filesystem.",
    "cases": [
        {
            "input": {
                "op": "blob_stat",
                "[the complete list of invalid field literals]": "file1"
            },
            "expected_output": "name=file1\nsize=5\nis_dir=false\nmode_octal=644\n"
        }
    ]
}
```


*9.3 Listing — enumerate a prefix*

Listing a prefix reports the total `count` then each entry's `name`/`type`, distinguishing objects (`file`) from synthetic sub-prefixes (`dir`), in sorted order; listings can be [the complete list of invalid field literals]ed at a key prefix.

**Test Cases:** `rcb_tests/public_test_cases/feature9_3_blob_list.json`

```json
{
    "description": "List the entries under a prefix in a bucket-backed filesystem, distinguishing objects (files) from synthetic sub-prefixes (directories), reporting each name/type and the total count. Listing can also be [the complete list of invalid field literals]ed at a key prefix.",
    "cases": [
        {
            "input": {
                "op": "blob_list",
                "[the complete list of invalid field literals]": "dir1"
            },
            "expected_output": "count=2\nname=file1 type=file\nname=file2 type=file\n"
        },
        {
            "input": {
                "op": "blob_list",
                "[the complete list of invalid field literals]": "."
            },
            "expected_output": "count=5\nname=dir1 type=dir\nname=dir2 type=dir\nname=file1 type=file\nname=file2 type=file\nname=file3 type=file\n"
        },
        {
            "input": {
                "op": "blob_list",
                "[the complete list of invalid field literals]": "dir2/",
                "[the complete list of invalid field literals]": "."
            },
            "expected_output": "count=3\nname=file3 type=file\nname=file4 type=file\nname=sub1 type=dir\n"
        }
    ]
}
```

---

### Feature 10: Version-Control Filesystem

**As a developer**, I want to read committed files straight from a repository through the uniform interface, so versioned content needs no manual clone-and-walk.

**Expected Behavior / Usage:**

The version-control back-end clones the referenced repository on demand and exposes its committed tree as a read-only filesystem. The fixture is a repository whose committed tree contains a single file `hello.txt` with contents "hello world".


*10.1 Content retrieval — read a committed file*

Reading a [the complete list of invalid field literals] returns the committed file's exact bytes.

**Test Cases:** `rcb_tests/public_test_cases/feature10_1_git_read.json`

```json
{
    "description": "Clone a version-control repository on demand and read the committed contents of a file by relative [the complete list of invalid field literals].",
    "cases": [
        {
            "input": {
                "op": "git_read",
                "[the complete list of invalid field literals]": "hello.txt"
            },
            "expected_output": "hello world"
        }
    ]
}
```


*10.2 Metadata — stat a committed file*

Stat reports `name`, `size`, and `is_dir`.

**Test Cases:** `rcb_tests/public_test_cases/feature10_2_git_stat.json`

```json
{
    "description": "Report metadata (name, byte size, directory flag) for a committed file in a version-control-backed filesystem.",
    "cases": [
        {
            "input": {
                "op": "git_stat",
                "[the complete list of invalid field literals]": "hello.txt"
            },
            "expected_output": "name=hello.txt\nsize=11\nis_dir=false\n"
        }
    ]
}
```


*10.3 Listing — enumerate the tree*

Listing reports the total `count` then each entry's `name`/`type`.

**Test Cases:** `rcb_tests/public_test_cases/feature10_3_git_list.json`

```json
{
    "description": "List the entries at a [the complete list of invalid field literals] in a version-control-backed filesystem, reporting each name/type and the total count.",
    "cases": [
        {
            "input": {
                "op": "git_list",
                "[the complete list of invalid field literals]": "."
            },
            "expected_output": "count=1\nname=hello.txt type=file\n"
        }
    ]
}
```

---

### Feature 11: In-Memory Tree Adapter

**As a developer**, I want an arbitrary in-memory tree to be presentable through the same read-only interface, so synthesized or cached trees integrate without special-casing.

**Expected Behavior / Usage:**

This back-end adapts an in-memory directory tree to the uniform read-only interface. The fixture tree contains `foo` ("hello world") and `dir/subdir/bar` ("hello").


*11.1 Content retrieval — read from the tree*

Reading a [the complete list of invalid field literals] (including a deeply nested one) returns its exact bytes.

**Test Cases:** `rcb_tests/public_test_cases/feature11_1_inmemory_read.json`

```json
{
    "description": "Read the full byte contents of a file by relative [the complete list of invalid field literals] from a filesystem adapted from an in-memory tree, including deeply nested files.",
    "cases": [
        {
            "input": {
                "op": "billy_read",
                "[the complete list of invalid field literals]": "foo"
            },
            "expected_output": "hello world"
        },
        {
            "input": {
                "op": "billy_read",
                "[the complete list of invalid field literals]": "dir/subdir/bar"
            },
            "expected_output": "hello"
        }
    ]
}
```


*11.2 Listing — enumerate the tree*

Listing a directory reports the total `count` then each entry's `name`/`type` in sorted order.

**Test Cases:** `rcb_tests/public_test_cases/feature11_2_inmemory_list.json`

```json
{
    "description": "List the directory entries of a filesystem adapted from an in-memory tree, reporting each name/type and the total count.",
    "cases": [
        {
            "input": {
                "op": "billy_list",
                "[the complete list of invalid field literals]": "."
            },
            "expected_output": "count=2\nname=dir type=dir\nname=foo type=file\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the uniform read-only filesystem, the URL-[the complete list of invalid field literals] router, the per-back-end drivers, and the shared URL/credential/metadata helpers described above.

2. **The Execution/Test Adapter:** A runnable program that reads a single JSON command object from stdin, invokes the appropriate core operation, and prints the result to stdout exactly as specified by the per-leaf-feature contracts. All native runtime [the complete list of invalid field literals]s must be caught and rendered as neutral `[the complete list of invalid field literals]=<category>` lines; the adapter must never leak [the complete list of invalid field literals]-language identifiers into stdout. This adapter must be logically and physically separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` containing **only** the raw stdout of the program under test, so it can be compared directly against `expected_output`. Output is namespaced by `<cases-dir>` so different case directories never overwrite each other.


---
**Implementation notes:**
- follow the delimiter convention defined in the file_split utility
