## Product Requirement Document

# In-Memory File System Engine - Product Requirements

## Project Goal

Build an in-memory file system engine that gives developers a complete, POSIX-style file system — directories, files, symbolic links, file handles, and a current working directory — living entirely in process memory. It allows developers to create, read, write, move, link, and inspect file system entities with the exact semantics of a real disk-backed file system, but without touching real storage, so tests and tooling become fast, isolated, and fully deterministic.

---

## Background & Problem

Without this engine, developers who want to test or simulate file system behavior are forced to write to real disk: they must pick scratch directories, clean them up, worry about cross-test pollution, tolerate slow I/O, and accept platform-specific path quirks. This leads to flaky tests, leftover temp files, and logic that is hard to exercise (symlink loops, permission-style errors, exotic path traversals) because reproducing those states on a real disk is awkward and destructive.

With this engine, the entire file tree is a programmable in-memory structure. Tests run in microseconds, every run starts from a clean root, error conditions (missing paths, link loops, non-empty directory deletes) are trivially reproducible, and behavior is identical regardless of host platform. Developers get a faithful POSIX-style contract — including byte-accurate reads/writes, link resolution, and seekable file handles — that behaves like the real thing.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a non-trivial domain (path resolution, multiple entity kinds, link following, seekable handles, error mapping). The codebase MUST be organized into clear, separated units — at minimum: a core model of the file tree and entities, a path-resolution component, the public file-system operations, and a separate execution adapter for I/O. It MUST NOT be a single "god file". Do not over-engineer, but reflect the real complexity in a production-grade directory layout.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in "Core Features" are a **black-box contract for the execution adapter**, NOT the internal data model of the engine. The core file-system logic must be completely decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating JSON command programs into idiomatic calls on the core engine and rendering results.

3. **Adherence to SOLID Design Principles:**
   - **SRP:** Separate parsing, command routing, path resolution, core entity operations, and output formatting.
   - **OCP:** Adding a new entity operation should not require rewriting existing ones.
   - **LSP:** File, directory, and link entity types must be substitutable wherever a generic entity is expected.
   - **ISP:** Keep entity interfaces small and cohesive (a directory listing concern is distinct from a byte-seek concern).
   - **DIP:** High-level operations depend on an abstract file-system interface, not on the adapter or any concrete I/O.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the engine must be elegant and idiomatic to the implementation language, hiding path-resolution and link-following complexity.
   - **Resilience:** Every failure path must be modeled as a typed error mapped to a stable, language-neutral category (see Feature 7). The engine must never crash on malformed-but-valid operations; it surfaces the proper error category instead.

---

## Execution Adapter Contract (shared by all features)

The execution adapter reads **one JSON object** from stdin describing a *program*, runs it against **one fresh, empty in-memory file system** rooted at `/`, and writes a **line-oriented, language-neutral result** to stdout.

The program shape is:

```json
{ "ops": [ { "op": "<name>", ... }, ... ] }
```

Operations execute in order against shared state. Each operation appends zero or more `key=value` lines to stdout in execution order. Paths are POSIX-style (`/`-separated, root `/`). The features below define each operation's inputs and its exact stdout lines. All of an op's observable result is expressed through these lines; there is no trailing status line.

Common output conventions:
- Text content is emitted JSON-quoted (e.g. `[a specific error message format for non-UTF-8 bytes]hello"`), so embedded quotes/newlines are escaped and an empty file reads as `[a specific error message format for non-UTF-8 bytes]"`.
- Byte sequences are emitted as comma-joined decimal byte values (e.g. `bytes=1,2,3,255`); an empty file reads as `bytes=`.
- Entity kinds are the literal words `file`, `directory`, `link`, or `not_found`.
- Booleans are the literal words `true` / `false`.
- Any failure replaces the op's normal lines with a single `error=<category>` line (see Feature 7).

---

## Core Features

### Feature 1: Directory Management

**As a developer**, I want to create, list, delete, rename, navigate, and allocate temporary directories, so I can model a full directory tree in memory.

**Expected Behavior / Usage:**

*1.1 Create Directory — materialize a directory, optionally creating missing ancestors*

`create_directory` takes a `path` and an optional `recursive` flag. When the parent already exists it creates the directory and emits `created_directory=<path>`. With `recursive: true` it also creates every missing ancestor. Creating a directory that already exists as a directory is a successful no-op. Creating a directory whose parent does not exist while `recursive` is false fails with a not-found category. `exists` with `as: "directory"` reports `[a specific boolean literal and response prefix]true|false`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_directory_create.json`

```json
{
  "description": "Create directories. A directory can be created at a path whose parent already exists; creating it recursively also materializes any missing ancestor directories. Creating a directory that already exists as a directory is a no-op success. The created directory's path is echoed back.",
  "cases": [
    {"input": {"ops": [{"op": "create_directory", "path": "/foo"}, {"op": "exists", "path": "/foo", "as": "directory"}]}, "expected_output": "created_directory=/foo\n[a specific boolean literal and response prefix]true\n"},
    {"input": {"ops": [{"op": "create_directory", "path": "/a/b/c", "recursive": true}, {"op": "exists", "path": "/a/b/c", "as": "directory"}]}, "expected_output": "created_directory=/a/b/c\n[a specific boolean literal and response prefix]true\n"},
    {"input": {"ops": [{"op": "create_directory", "path": "/a/b/c"}]}, "expected_output": "error=no_such_file_or_directory\n"}
  ]
}
```

*1.2 List Directory — enumerate immediate or recursive children, sorted*

`list` takes a `path` and optional `recursive` flag. It emits `entry_count=<n>` followed by one `entry=<kind>:<path>` line per child, where `<kind>` is `file`/`directory`/`link`. Entries are emitted in stable lexicographically sorted order. With `recursive: true`, all descendants are included. Listing a path that does not exist fails with a not-found category. An empty directory yields `entry_count=0`.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_directory_list.json`

```json
{
  "description": "List the immediate children of a directory, or recursively list all descendants. Each entry is reported as its kind (file/directory/link) and its path. Entries are emitted in a stable, lexicographically sorted order and the total count is reported first.",
  "cases": [
    {"input": {"ops": [{"op": "create_directory", "path": "/d"}, {"op": "create_file", "path": "/d/b"}, {"op": "create_file", "path": "/d/a"}, {"op": "create_directory", "path": "/d/sub"}, {"op": "list", "path": "/d"}]}, "expected_output": "created_directory=/d\ncreated_file=/d/b\ncreated_file=/d/a\ncreated_directory=/d/sub\nentry_count=3\nentry=directory:/d/sub\nentry=file:/d/a\nentry=file:/d/b\n"},
    {"input": {"ops": [{"op": "create_directory", "path": "/a/b/c", "recursive": true}, {"op": "create_file", "path": "/a/b/c/f.txt"}, {"op": "list", "path": "/a", "recursive": true}]}, "expected_output": "created_directory=/a/b/c\ncreated_file=/a/b/c/f.txt\nentry_count=3\nentry=directory:/a/b\nentry=directory:/a/b/c\nentry=file:/a/b/c/f.txt\n"},
    {"input": {"ops": [{"op": "create_directory", "path": "/empty"}, {"op": "list", "path": "/empty"}]}, "expected_output": "created_directory=/empty\nentry_count=0\n"}
  ]
}
```

*1.3 Delete Directory — empty-only delete vs. recursive delete*

`delete` with `as: "directory"` removes a directory and emits `deleted=<path>`. Without `recursive`, it succeeds only on an empty directory; deleting a non-empty directory fails with a directory-not-empty category. With `recursive: true` it removes the directory and all contents.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_directory_delete.json`

```json
{
  "description": "Delete a directory. A non-recursive delete succeeds only when the directory is empty; deleting a non-empty directory non-recursively fails with a directory-not-empty category. A recursive delete removes the directory and all of its contents. The deleted path is echoed back.",
  "cases": [
    {"input": {"ops": [{"op": "create_directory", "path": "/d"}, {"op": "delete", "path": "/d", "as": "directory"}, {"op": "exists", "path": "/d", "as": "directory"}]}, "expected_output": "created_directory=/d\ndeleted=/d\n[a specific boolean literal and response prefix]false\n"},
    {"input": {"ops": [{"op": "create_directory", "path": "/foo"}, {"op": "create_file", "path": "/foo/x"}, {"op": "delete", "path": "/foo", "as": "directory"}]}, "expected_output": "created_directory=/foo\ncreated_file=/foo/x\nerror=directory_not_empty\n"},
    {"input": {"ops": [{"op": "create_directory", "path": "/foo"}, {"op": "create_file", "path": "/foo/x"}, {"op": "delete", "path": "/foo", "as": "directory", "recursive": true}, {"op": "exists", "path": "/foo", "as": "directory"}]}, "expected_output": "created_directory=/foo\ncreated_file=/foo/x\ndeleted=/foo\n[a specific boolean literal and response prefix]false\n"}
  ]
}
```

*1.4 Rename Directory — move a directory subtree*

`rename` with `as: "directory"` moves a directory from `from` to `to`, emitting `renamed=<to>`. Renaming a source that does not exist fails with a not-found category.

**Test Cases:** `rcb_tests/public_test_cases/feature1_4_directory_rename.json`

```json
{
  "description": "Rename (move) a directory to a new path. Renaming onto a path whose parent does not exist fails, and renaming a source that does not exist fails, both with a not-found category. A successful rename reports the new path.",
  "cases": [
    {"input": {"ops": [{"op": "create_directory", "path": "/a"}, {"op": "rename", "from": "/a", "to": "/b", "as": "directory"}, {"op": "exists", "path": "/b", "as": "directory"}]}, "expected_output": "created_directory=/a\nrenamed=/b\n[a specific boolean literal and response prefix]true\n"},
    {"input": {"ops": [{"op": "rename", "from": "/nope", "to": "/b", "as": "directory"}]}, "expected_output": "error=no_such_file_or_directory\n"}
  ]
}
```

*1.5 Path Navigation — parent and absolute resolution*

`parent` emits `parent=<path>` for the parent directory of `path`; the parent of root `/` is `/` itself. `absolute` emits `absolute=<path>`, resolving a relative `path` against the current working directory (root by default). These are pure path computations and do not require the entity to exist.

**Test Cases:** `rcb_tests/public_test_cases/feature1_5_directory_navigation.json`

```json
{
  "description": "Compute structural path properties of a directory without touching storage: the parent directory of a path, and the absolute form of a relative path resolved against the current working directory. The parent of the root directory is the root itself.",
  "cases": [
    {"input": {"ops": [{"op": "parent", "path": "/foo/bar"}]}, "expected_output": "parent=/foo\n"},
    {"input": {"ops": [{"op": "parent", "path": "/"}]}, "expected_output": "parent=/\n"},
    {"input": {"ops": [{"op": "absolute", "path": "foo"}]}, "expected_output": "absolute=/foo\n"}
  ]
}
```

*1.6 Temporary Directory — collision-free unique names*

`create_temp` allocates a uniquely-named directory under a system temp area and emits `temp=<path>`. An optional `prefix` is incorporated into the generated name. Successive allocations with the same prefix receive distinct names via an incrementing suffix, so no two collide.

**Test Cases:** `rcb_tests/public_test_cases/feature1_6_temp_directory.json`

```json
{
  "description": "Create a uniquely-named temporary directory under a system temp area. Successive temp directories created with the same prefix receive distinct names by appending an incrementing suffix.",
  "cases": [
    {"input": {"ops": [{"op": "create_temp", "prefix": "x"}]}, "expected_output": "temp=/.tmp_rand0/xrand0\n"},
    {"input": {"ops": [{"op": "create_temp", "prefix": "foo"}, {"op": "create_temp", "prefix": "foo"}]}, "expected_output": "temp=/.tmp_rand0/foorand0\ntemp=/.tmp_rand0/foorand1\n"}
  ]
}
```

---

### Feature 2: File Content I/O

**As a developer**, I want to write and read file content as text, bytes, or lines, and copy/rename/measure files, so I can manipulate file data with byte-accurate fidelity.

**Expected Behavior / Usage:**

*2.1 Text Read/Write — write a string and read it back*

`write` with a `text` field writes the UTF-8 bytes of the string (default overwrite mode) and emits `wrote_bytes=<n>` where `n` is the UTF-8 byte count. `read` (default `as: "text"`) emits `text=<json-quoted-content>`. `create_file` (optionally `recursive`) creates an empty file and emits `created_file=<path>`. A zero-byte file reads as `[a specific error message format for non-UTF-8 bytes]"`. Multi-byte characters count as multiple bytes.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_file_text.json`

```json
{
  "description": "Write a string to a file and read it back as text. Writing reports the number of bytes (UTF-8 encoded) written; reading returns the JSON-quoted text content. Reading a zero-byte file yields an empty string.",
  "cases": [
    {"input": {"ops": [{"op": "create_file", "path": "/foo/bar.txt", "recursive": true}, {"op": "write", "path": "/foo/bar.txt", "text": "hello"}, {"op": "read", "path": "/foo/bar.txt"}, {"op": "length", "path": "/foo/bar.txt"}]}, "expected_output": "created_file=/foo/bar.txt\nwrote_bytes=5\ntext=\"hello\"\nlength=5\n"},
    {"input": {"ops": [{"op": "create_file", "path": "/e"}, {"op": "read", "path": "/e"}]}, "expected_output": "created_file=/e\ntext=\"\"\n"},
    {"input": {"ops": [{"op": "write", "path": "/u.txt", "text": "héllo"}, {"op": "read", "path": "/u.txt"}, {"op": "length", "path": "/u.txt"}]}, "expected_output": "wrote_bytes=6\ntext=\"héllo\"\nlength=6\n"}
  ]
}
```

*2.2 Byte Read/Write — write and read raw byte values*

`write` with a `bytes` field (list of integer byte values) writes them verbatim and emits `wrote_bytes=<n>`. `read` with `as: "bytes"` emits `bytes=<comma-joined values>`. A zero-byte file reads as `bytes=` (empty).

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_file_bytes.json`

```json
{
  "description": "Write a list of raw byte values to a file and read them back as bytes. The byte count is reported on write; reading returns the comma-joined byte values. A zero-byte file reads back as an empty byte sequence.",
  "cases": [
    {"input": {"ops": [{"op": "write", "path": "/b.bin", "bytes": [1, 2, 3, 255]}, {"op": "read", "path": "/b.bin", "as": "bytes"}]}, "expected_output": "wrote_bytes=4\nbytes=1,2,3,255\n"},
    {"input": {"ops": [{"op": "create_file", "path": "/e"}, {"op": "read", "path": "/e", "as": "bytes"}]}, "expected_output": "created_file=/e\nbytes=\n"}
  ]
}
```

*2.3 Line Read — split content into trailing-newline-agnostic lines*

`read` with `as: "lines"` emits `[the exact count prefix and line format]<n>` followed by one `line=<text>` per line. Line splitting is trailing-newline agnostic: a final newline does not add an empty trailing line. A zero-byte file yields `[the exact count prefix and line format]0`.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_file_lines.json`

```json
{
  "description": "Read a file as a list of text lines. The line count is reported first, followed by each line. Line splitting is trailing-newline agnostic: a final newline does not produce an extra empty line. A zero-byte file yields zero lines.",
  "cases": [
    {"input": {"ops": [{"op": "write", "path": "/t.txt", "text": "a\nb\nc"}, {"op": "read", "path": "/t.txt", "as": "lines"}]}, "expected_output": "wrote_bytes=5\n[the exact count prefix and line format]3\nline=a\nline=b\nline=c\n"},
    {"input": {"ops": [{"op": "write", "path": "/t.txt", "text": "a\nb\nc\n"}, {"op": "read", "path": "/t.txt", "as": "lines"}]}, "expected_output": "wrote_bytes=6\n[the exact count prefix and line format]3\nline=a\nline=b\nline=c\n"},
    {"input": {"ops": [{"op": "create_file", "path": "/e"}, {"op": "read", "path": "/e", "as": "lines"}]}, "expected_output": "created_file=/e\n[the exact count prefix and line format]0\n"}
  ]
}
```

*2.4 Append vs. Overwrite — write modes*

`write` defaults to overwrite mode (replaces content). With `mode: "append"` it preserves existing content and appends. Appending to a non-existent file creates it.

**Test Cases:** `rcb_tests/public_test_cases/feature2_4_file_append.json`

```json
{
  "description": "Append mode preserves existing file content and adds new content at the end, in contrast to the default write mode which overwrites. Appending to a non-existent file creates it.",
  "cases": [
    {"input": {"ops": [{"op": "write", "path": "/f", "text": "ab"}, {"op": "write", "path": "/f", "text": "cd", "mode": "append"}, {"op": "read", "path": "/f"}]}, "expected_output": "wrote_bytes=2\nwrote_bytes=2\ntext=\"abcd\"\n"},
    {"input": {"ops": [{"op": "write", "path": "/f", "text": "x", "mode": "append"}, {"op": "read", "path": "/f"}]}, "expected_output": "wrote_bytes=1\ntext=\"x\"\n"},
    {"input": {"ops": [{"op": "write", "path": "/f", "text": "old"}, {"op": "write", "path": "/f", "text": "new"}, {"op": "read", "path": "/f"}]}, "expected_output": "wrote_bytes=3\nwrote_bytes=3\ntext=\"new\"\n"}
  ]
}
```

*2.5 File Length — measure byte size*

`length` emits `length=<n>`, the byte size of the file. A newly created file has length 0; after writing N bytes it is N. Querying the length of a non-existent path fails with a not-found category.

**Test Cases:** `rcb_tests/public_test_cases/feature2_5_file_length.json`

```json
{
  "description": "Report the byte length of a file. A newly created file has length zero; after writing N bytes the length is N. Querying the length of a path that does not exist fails with a not-found category.",
  "cases": [
    {"input": {"ops": [{"op": "create_file", "path": "/f"}, {"op": "length", "path": "/f"}]}, "expected_output": "created_file=/f\nlength=0\n"},
    {"input": {"ops": [{"op": "write", "path": "/f", "text": "hello"}, {"op": "length", "path": "/f"}]}, "expected_output": "wrote_bytes=5\nlength=5\n"},
    {"input": {"ops": [{"op": "length", "path": "/nope"}]}, "expected_output": "error=no_such_file_or_directory\n"}
  ]
}
```

*2.6 Copy File — duplicate content to a destination*

`copy` copies file content from `from` to `to`, emitting `copied=<to>`. If the destination exists as a file, its content is overwritten. Copying a non-existent source fails with a not-found category.

**Test Cases:** `rcb_tests/public_test_cases/feature2_6_file_copy.json`

```json
{
  "description": "Copy a file's content to a destination path, returning the destination path. If the destination already exists as a file, its content is overwritten by the source's content. Copying a non-existent source fails with a not-found category.",
  "cases": [
    {"input": {"ops": [{"op": "write", "path": "/a", "text": "hi"}, {"op": "copy", "from": "/a", "to": "/b"}, {"op": "read", "path": "/b"}]}, "expected_output": "wrote_bytes=2\ncopied=/b\ntext=\"hi\"\n"},
    {"input": {"ops": [{"op": "write", "path": "/a", "text": "new"}, {"op": "write", "path": "/b", "text": "old"}, {"op": "copy", "from": "/a", "to": "/b"}, {"op": "read", "path": "/b"}]}, "expected_output": "wrote_bytes=3\nwrote_bytes=3\ncopied=/b\ntext=\"new\"\n"},
    {"input": {"ops": [{"op": "copy", "from": "/nope", "to": "/b"}]}, "expected_output": "error=no_such_file_or_directory\n"}
  ]
}
```

*2.7 Rename File — move a file and its content*

`rename` (default `as: "file"`) moves a file from `from` to `to`, emitting `renamed=<to>`. The content moves and the old path no longer exists. Renaming a non-existent source fails with a not-found category.

**Test Cases:** `rcb_tests/public_test_cases/feature2_7_file_rename.json`

```json
{
  "description": "Rename (move) a file to a new path, returning the new path. The content moves with the file and the old path no longer exists. Renaming a source that does not exist fails with a not-found category.",
  "cases": [
    {"input": {"ops": [{"op": "write", "path": "/a", "text": "data"}, {"op": "rename", "from": "/a", "to": "/b"}, {"op": "exists", "path": "/a"}, {"op": "read", "path": "/b"}]}, "expected_output": "wrote_bytes=4\nrenamed=/b\n[a specific boolean literal and response prefix]false\ntext=\"data\"\n"},
    {"input": {"ops": [{"op": "rename", "from": "/nope", "to": "/b"}]}, "expected_output": "error=no_such_file_or_directory\n"}
  ]
}
```

---

### Feature 3: Symbolic Links

**As a developer**, I want to create symbolic links, read their targets, follow or not-follow them, resolve them to real paths, and unlink them, so I can model indirection and aliasing in the file tree.

**Expected Behavior / Usage:**

*3.1 Create Link and Read Target — record an indirection*

`create_link` creates a link at `path` pointing at `target`, emitting `created_link=<path>` then `link_target=<target>`. The link stores the literal target string whether or not the target exists. `target` reads back the stored target as `target=<value>`. Creating a link where a file already exists fails with a file-exists category.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_link_create_target.json`

```json
{
  "description": "Create a symbolic link pointing at a target path, and read back the stored target. The link records the literal target string regardless of whether the target exists. Creating a link at a path already occupied by a file fails with an already-exists category.",
  "cases": [
    {"input": {"ops": [{"op": "create_file", "path": "/foo"}, {"op": "create_link", "path": "/bar", "target": "/foo"}, {"op": "target", "path": "/bar"}]}, "expected_output": "created_file=/foo\ncreated_link=/bar\nlink_target=/foo\ntarget=/foo\n"},
    {"input": {"ops": [{"op": "create_link", "path": "/l", "target": "/nope"}, {"op": "target", "path": "/l"}]}, "expected_output": "created_link=/l\nlink_target=/nope\ntarget=/nope\n"},
    {"input": {"ops": [{"op": "create_file", "path": "/foo"}, {"op": "create_link", "path": "/foo", "target": "/bar"}]}, "expected_output": "created_file=/foo\nerror=file_exists\n"}
  ]
}
```

*3.2 Link Following — type query with controllable follow*

`type` reports the entity kind at `path` as `type=<kind>`. With `follow_links: true` a link to a file reports `type=file`; with `follow_links: false` it reports `type=link`. A link whose target chain forms a loop reports `type=not_found` when followed.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_link_type.json`

```json
{
  "description": "Determine the kind of entity at a path with link following controlled by a flag. With link-following enabled, a link to a file reports as a file; with following disabled, it reports as a link. A link whose target chain forms a loop reports as not-found when followed.",
  "cases": [
    {"input": {"ops": [{"op": "create_file", "path": "/foo"}, {"op": "create_link", "path": "/bar", "target": "/foo"}, {"op": "type", "path": "/bar", "follow_links": true}]}, "expected_output": "created_file=/foo\ncreated_link=/bar\nlink_target=/foo\ntype=file\n"},
    {"input": {"ops": [{"op": "create_file", "path": "/foo"}, {"op": "create_link", "path": "/bar", "target": "/foo"}, {"op": "type", "path": "/bar", "follow_links": false}]}, "expected_output": "created_file=/foo\ncreated_link=/bar\nlink_target=/foo\ntype=link\n"},
    {"input": {"ops": [{"op": "create_link", "path": "/foo", "target": "/bar"}, {"op": "create_link", "path": "/bar", "target": "/foo"}, {"op": "type", "path": "/foo", "follow_links": true}]}, "expected_output": "created_link=/foo\nlink_target=/bar\ncreated_link=/bar\nlink_target=/foo\ntype=not_found\n"}
  ]
}
```

*3.3 Resolve Symbolic Links — canonicalize to a real path*

`resolve` follows every link in `path` and emits `resolved=<canonical path>`. A link to a directory resolves to the directory, including when nested within a traversal. Resolving an empty path fails with a not-found category.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_link_resolve.json`

```json
{
  "description": "Resolve all symbolic links in a path to its canonical real path. A link to a directory resolves to the directory's path, including when the link is nested within a traversal. Resolving an empty path fails with a not-found category.",
  "cases": [
    {"input": {"ops": [{"op": "create_directory", "path": "/foo"}, {"op": "create_link", "path": "/bar", "target": "/foo"}, {"op": "resolve", "path": "/bar"}]}, "expected_output": "created_directory=/foo\ncreated_link=/bar\nlink_target=/foo\nresolved=/foo\n"},
    {"input": {"ops": [{"op": "create_directory", "path": "/foo/bar", "recursive": true}, {"op": "create_link", "path": "/foo/baz", "target": "/foo/bar"}, {"op": "resolve", "path": "/foo/baz"}]}, "expected_output": "created_directory=/foo/bar\ncreated_link=/foo/baz\nlink_target=/foo/bar\nresolved=/foo/bar\n"},
    {"input": {"ops": [{"op": "resolve", "path": ""}]}, "expected_output": "error=no_such_file_or_directory\n"}
  ]
}
```

*3.4 Unlink — delete the link without touching its target*

`delete` with `as: "link"` removes the link only, emitting `deleted=<path>`. The former target remains intact afterward.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_link_delete.json`

```json
{
  "description": "Delete a symbolic link itself without affecting the entity it points to. After unlinking, the link no longer exists but its former target remains.",
  "cases": [
    {"input": {"ops": [{"op": "create_file", "path": "/foo"}, {"op": "create_link", "path": "/bar", "target": "/foo"}, {"op": "delete", "path": "/bar", "as": "link"}, {"op": "exists", "path": "/foo"}, {"op": "exists", "path": "/bar", "as": "link"}]}, "expected_output": "created_file=/foo\ncreated_link=/bar\nlink_target=/foo\ndeleted=/bar\n[a specific boolean literal and response prefix]true\n[a specific boolean literal and response prefix]false\n"}
  ]
}
```

---

### Feature 4: Current Working Directory

**As a developer**, I want a mutable current working directory that relative paths resolve against, so I can model process-relative file access.

**Expected Behavior / Usage:**

`set_cwd` sets the working directory to `path` and emits `current_directory=<path>`; `cwd` reports it. After setting it, relative paths (e.g. via `absolute`) resolve against it. Setting the working directory to a non-existent path fails with a not-found category; setting it to a file fails with a not-a-directory category.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_cwd.json`

```json
{
  "description": "Get and set the current working directory. Setting the working directory to an existing directory updates it and echoes the new path; relative paths passed afterward resolve against it. Setting it to a path that does not exist fails with a not-found category, and setting it to a file fails with a not-a-directory category.",
  "cases": [
    {"input": {"ops": [{"op": "create_directory", "path": "/foo"}, {"op": "set_cwd", "path": "/foo"}, {"op": "cwd"}]}, "expected_output": "created_directory=/foo\ncurrent_directory=/foo\ncurrent_directory=/foo\n"},
    {"input": {"ops": [{"op": "create_directory", "path": "/foo"}, {"op": "set_cwd", "path": "/foo"}, {"op": "absolute", "path": "bar"}]}, "expected_output": "created_directory=/foo\ncurrent_directory=/foo\nabsolute=/foo/bar\n"},
    {"input": {"ops": [{"op": "set_cwd", "path": "/nope"}]}, "expected_output": "error=no_such_file_or_directory\n"},
    {"input": {"ops": [{"op": "create_file", "path": "/f"}, {"op": "set_cwd", "path": "/f"}]}, "expected_output": "created_file=/f\nerror=not_a_directory\n"}
  ]
}
```

---

### Feature 5: Random Access File Handles

**As a developer**, I want seekable file handles for byte-level sequential and positioned I/O, so I can read and write portions of a file without loading it whole.

**Expected Behavior / Usage:**

A handle is opened with `open` (`path`, `handle` name, `mode` one of `read`/`write`/`append`/`writeOnly`/`writeOnlyAppend`), emitting `opened=<path>`. Subsequent ops reference the handle by name. `raf_close` emits `closed=<handle>`.

*5.1 Sequential Read/Write — append-style byte/text writes*

`raf_write` writes a `text` string (or `bytes` list) at the cursor and emits `wrote_bytes=<n>`. `raf_write_byte` writes one byte `value` and emits `wrote_bytes=1`. `raf_length` emits `length=<n>` reflecting accumulated writes. After closing, the file content reflects the writes.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_raf_sequential.json`

```json
{
  "description": "Open a file handle and write bytes/text sequentially, then read them back. Writing reports the number of bytes written; the handle's length reflects accumulated writes. A single byte value can also be written and read back as raw bytes.",
  "cases": [
    {"input": {"ops": [{"op": "create_file", "path": "/f"}, {"op": "open", "path": "/f", "handle": "h", "mode": "write"}, {"op": "raf_write", "handle": "h", "text": "hello"}, {"op": "raf_length", "handle": "h"}, {"op": "raf_close", "handle": "h"}, {"op": "read", "path": "/f"}]}, "expected_output": "created_file=/f\nopened=/f\nwrote_bytes=5\nlength=5\nclosed=h\ntext=\"hello\"\n"},
    {"input": {"ops": [{"op": "create_file", "path": "/f"}, {"op": "open", "path": "/f", "handle": "h", "mode": "write"}, {"op": "raf_write_byte", "handle": "h", "value": 65}, {"op": "raf_close", "handle": "h"}, {"op": "read", "path": "/f", "as": "bytes"}]}, "expected_output": "created_file=/f\nopened=/f\nwrote_bytes=1\nclosed=h\nbytes=65\n"}
  ]
}
```

*5.2 Cursor Positioning — seek and positioned reads*

`raf_read_byte` reads one byte and emits `read_byte=<value>`, advancing the cursor. `raf_position` emits `position=<offset>`. `raf_set_position` moves the cursor to an absolute `position` and emits the new `position=<offset>`. `raf_read` reads up to `count` bytes and emits `read_length=<n>` then `read_text=<json-quoted text>`; reading past end returns only the remaining bytes.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_raf_position.json`

```json
{
  "description": "A file handle tracks a read/write cursor position. Reading advances the position; the cursor can be repositioned to an absolute offset and subsequent reads start from there. Reading more bytes than remain returns only the available bytes.",
  "cases": [
    {"input": {"ops": [{"op": "write", "path": "/f", "text": "hello"}, {"op": "open", "path": "/f", "handle": "h", "mode": "read"}, {"op": "raf_read_byte", "handle": "h"}, {"op": "raf_position", "handle": "h"}, {"op": "raf_set_position", "handle": "h", "position": 0}, {"op": "raf_read", "handle": "h", "count": 5}]}, "expected_output": "wrote_bytes=5\nopened=/f\nread_byte=104\nposition=1\nposition=0\nread_length=5\nread_text=\"hello\"\n"},
    {"input": {"ops": [{"op": "write", "path": "/f", "text": "hi"}, {"op": "open", "path": "/f", "handle": "h", "mode": "read"}, {"op": "raf_read", "handle": "h", "count": 10}]}, "expected_output": "wrote_bytes=2\nopened=/f\nread_length=2\nread_text=\"hi\"\n"}
  ]
}
```

*5.3 Truncate — shrink an open handle*

`raf_truncate` truncates the handle to `length` bytes (discarding content beyond it) and emits `truncated=<length>`. The truncation is visible in the file content after the handle is closed.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_raf_truncate.json`

```json
{
  "description": "Truncate an open file handle to a given length, discarding any content beyond that length. The file content reflects the truncation after the handle is closed.",
  "cases": [
    {"input": {"ops": [{"op": "write", "path": "/f", "text": "hello"}, {"op": "open", "path": "/f", "handle": "h", "mode": "append"}, {"op": "raf_truncate", "handle": "h", "length": 2}, {"op": "raf_close", "handle": "h"}, {"op": "read", "path": "/f"}]}, "expected_output": "wrote_bytes=5\nopened=/f\ntruncated=2\nclosed=h\ntext=\"he\"\n"}
  ]
}
```

---

### Feature 6: Entity Inspection

**As a developer**, I want to test existence, query entity kind, and compare identity, so I can introspect the file tree without modifying it.

**Expected Behavior / Usage:**

*6.1 Existence — kind-aware existence test*

`exists` (with optional `as` of `file`/`directory`/`link`) emits `[a specific boolean literal and response prefix]<bool>`. A link is considered to exist as a link even when its target is missing, but does not exist as a file in that case.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_exists.json`

```json
{
  "description": "Test whether an entity exists at a path, interpreted as a specific kind (file/directory/link). A link is considered to exist as a link even when its target is missing, but does not exist as a file in that case.",
  "cases": [
    {"input": {"ops": [{"op": "create_file", "path": "/f"}, {"op": "exists", "path": "/f", "as": "file"}, {"op": "exists", "path": "/nope", "as": "file"}]}, "expected_output": "created_file=/f\n[a specific boolean literal and response prefix]true\n[a specific boolean literal and response prefix]false\n"},
    {"input": {"ops": [{"op": "create_link", "path": "/l", "target": "/nope"}, {"op": "exists", "path": "/l", "as": "link"}, {"op": "exists", "path": "/l", "as": "file"}]}, "expected_output": "created_link=/l\nlink_target=/nope\n[a specific boolean literal and response prefix]true\n[a specific boolean literal and response prefix]false\n"}
  ]
}
```

*6.2 Entity Kind — following vs. non-following kind queries*

`type` (non-following at tail, or following per `follow_links`) emits `type=<kind>`. `stat_type` always follows links and emits `stat_type=<kind>` of the final target — e.g. a link to a file reports `stat_type=file`, and a missing path reports `not_found`. The root directory and ancestors of root report as directories.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_entity_type.json`

```json
{
  "description": "Report the entity kind at a path. The non-following type query reports file/directory/link/not-found at the tail of the path. The stat-based type follows links and reports the kind of the final target (e.g. a link to a file reports as a file), or not-found when nothing is there. The root directory and ancestors of root report as directories.",
  "cases": [
    {"input": {"ops": [{"op": "stat_type", "path": "/nope"}]}, "expected_output": "stat_type=not_found\n"},
    {"input": {"ops": [{"op": "create_file", "path": "/foo"}, {"op": "create_link", "path": "/bar", "target": "/foo"}, {"op": "stat_type", "path": "/bar"}]}, "expected_output": "created_file=/foo\ncreated_link=/bar\nlink_target=/foo\nstat_type=file\n"},
    {"input": {"ops": [{"op": "type", "path": "/"}]}, "expected_output": "type=directory\n"},
    {"input": {"ops": [{"op": "type", "path": "/nope"}]}, "expected_output": "type=not_found\n"}
  ]
}
```

*6.3 Identity — same-object comparison*

`identical` emits `identical=<bool>`, true only when `path1` and `path2` refer to the same underlying object. Comparing where an entity does not exist fails with a not-found category.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_identical.json`

```json
{
  "description": "Test whether two paths refer to the same underlying file system object. The same path compared with itself is identical; distinct files are not. Comparing paths where an entity does not exist fails with a not-found category.",
  "cases": [
    {"input": {"ops": [{"op": "create_file", "path": "/a"}, {"op": "create_file", "path": "/b"}, {"op": "identical", "path1": "/a", "path2": "/a"}, {"op": "identical", "path1": "/a", "path2": "/b"}]}, "expected_output": "created_file=/a\ncreated_file=/b\nidentical=true\nidentical=false\n"},
    {"input": {"ops": [{"op": "identical", "path1": "/a", "path2": "/b"}]}, "expected_output": "error=no_such_file_or_directory\n"}
  ]
}
```

---

### Feature 7: Error Normalization

**As a developer**, I want every failure surfaced as a stable, language-neutral category, so my error handling is portable and never depends on host-runtime exception details.

**Expected Behavior / Usage:**

When any operation fails, its normal output lines are replaced by a single `error=<category>` line. Categories are POSIX-style and language-neutral; they never expose host-language exception types, message suffixes, or object renderings. The defined categories include: `no_such_file_or_directory` (missing path), `is_a_directory` (a file-content operation aimed at a directory), `not_a_directory` (a directory operation aimed at a file, or traversing through a file), `file_exists` (creating over an existing entity), `directory_not_empty` (non-recursive delete of a populated directory), and `unknown_operation` (an unrecognized op name). Other POSIX categories (e.g. `too_many_symbolic_links`, `bad_file_descriptor`, `invalid_argument`) follow the same `error=<category>` convention.

**Test Cases:** `rcb_tests/public_test_cases/feature7_error_normalization.json`

```json
{
  "description": "All failures are surfaced as language-neutral POSIX-style error categories on an `error=` line, never as host-language exception artifacts. Categories include not-found (missing path), is-a-directory (file operation targeting a directory), not-a-directory (directory operation targeting a file), file-exists (creating over an existing entity), and directory-not-empty (non-recursive delete of a populated directory).",
  "cases": [
    {"input": {"ops": [{"op": "read", "path": "/nope.txt"}]}, "expected_output": "error=no_such_file_or_directory\n"},
    {"input": {"ops": [{"op": "create_directory", "path": "/foo"}, {"op": "read", "path": "/foo"}]}, "expected_output": "created_directory=/foo\nerror=is_a_directory\n"},
    {"input": {"ops": [{"op": "create_file", "path": "/foo"}, {"op": "create_directory", "path": "/foo"}]}, "expected_output": "created_file=/foo\nerror=not_a_directory\n"},
    {"input": {"ops": [{"op": "create_file", "path": "/foo"}, {"op": "create_link", "path": "/foo", "target": "/bar"}]}, "expected_output": "created_file=/foo\nerror=file_exists\n"},
    {"input": {"ops": [{"op": "create_directory", "path": "/foo"}, {"op": "create_file", "path": "/foo/x"}, {"op": "delete", "path": "/foo", "as": "directory"}]}, "expected_output": "created_directory=/foo\ncreated_file=/foo/x\nerror=directory_not_empty\n"},
    {"input": {"ops": [{"op": "frobnicate"}]}, "expected_output": "error=unknown_operation\n"}
  ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured in-memory file system engine implementing the features above — directory/file/link entities, path resolution with link following, seekable file handles, a mutable working directory, and typed errors. Its physical structure MUST follow the "Scale-Driven Code Organization" constraint: a multi-file layout separating the core model, path resolution, operations, and the execution adapter.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON program object from stdin, runs its `ops` in order against one fresh in-memory file system, and prints the line-oriented contract to stdout exactly as specified per leaf feature. The adapter owns all stdout formatting and error normalization (translating native errors into `error=<category>` lines); it must be logically and physically separated from the core engine.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to choose the directory (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_1_directory_create.json` under `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_directory_create@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` contains **only** the raw stdout of the program under test (no PASS/FAIL or metadata), so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the exact quoting convention used by the 'read' operation for text output
- inspect the codebase for the default 'mode' flag behavior when explicitly omitted during the 'write' operation
