## Task

A Docker container is already up and running; its container ID is `{docker_id}`. Inside the container, `{workdir}/{prd_name}` is the PRD document for this task. **Enter that container** and implement the required functionality based solely on the PRD. All development, compilation, execution, and self-testing MUST be done **inside this container**.

## Inputs

- Running container: `{docker_id}`
- PRD document: `{workdir}/{prd_name}` (inside the container)
- Target programming language: {lang}

## How to enter the container

The container is already running in the background (`sleep infinity`). Use `docker exec` to run commands, for example:

```bash
docker exec -w {workdir} {docker_id} bash -lc 'cat {prd_name}'
docker exec -w {workdir} {docker_id} bash -lc '<your build/run command>'
```

`{workdir}` is bind-mounted to the host's current working directory, so any code you generate under `{workdir}` inside the container automatically appears in the host's current directory for evaluation. **Write all of your deliverables under the container's `{workdir}` directory.**

## Requirements

1. You MUST implement the full functionality yourself. Downloading the source code of the target repository from the internet, or directly calling its existing API, is prohibited.
2. First read `{workdir}/{prd_name}` thoroughly. If the PRD contains a "Clarification / Oracle" interaction section, the requirement is **intentionally incomplete and vague** — you should **first ask the Oracle questions as instructed** to clarify the hidden interface contracts, feature details, and test cases, and **only start coding once things are clear**. Anything left unclarified will turn into bugs. The number of questions is budgeted, so watch `status.remaining`.
3. The example cases embedded in the PRD are the dispatcher's input/output contract. You need to design the dispatcher / runner / `rcb_tests/test.sh` yourself, and turn the examples shown in the PRD into `rcb_tests/public_test_cases/*.json` for self-checking.
4. `bash rcb_tests/test.sh` MUST support `--cases-dir <subdir>` to switch the cases directory, and MUST write each case's stdout to `rcb_tests/stdout/<cases-dir>/{{stem}}@{{idx:03}}.txt` (each file contains only the raw stdout of the program under test, without any PASS/FAIL markers). This is the evaluation protocol; you must follow it exactly.

## Environment & dependencies (**must read**)

5. **You are root inside the container, and it has network access.** You are allowed and expected to install missing dependencies yourself using tools such as `apt / pip / npm / cargo add / dotnet add package / mvn / composer / gem / pub get`. When you hit build/run errors (missing packages, missing SDKs, version mismatches, etc.), fix them based on the feedback; do not assume dependencies are already declared.

   **Network note:** the direct connection is the default and is usually enough. If a download fails with a network error (DNS / connection timeout / unreachable), a proxy is available — run `source ~/proxy.sh` once in that shell and retry only the command that failed. Do not export the proxy globally or for unrelated commands; it has limited bandwidth.

6. **Evaluation runs your `rcb_tests/test.sh` in a FRESH container started from the SAME base image, with NO network guaranteed and NONE of your interactive `apt`/`curl` installs preserved.** Anything you installed by hand in this session is gone at evaluation time. Therefore **every install/build step needed to run the tests MUST be reproducible from your committed files**, in one of these two ways:
   - put the language/runtime/system install commands **inside `rcb_tests/test.sh` itself** (or a helper script it calls), so a clean container can bootstrap the toolchain and dependencies on its own; **and**
   - record library dependencies in the language's declaration file so package managers can restore them:
     - Python: `requirements.txt` or `pyproject.toml`
     - JavaScript (Node): `dependencies` in `package.json`
     - TypeScript: `package.json` (incl. `typescript`/`ts-node` devDeps) + `tsconfig.json`
     - Go: `require` in `go.mod` (+ `go.sum`)
     - Rust: `[dependencies]` in `Cargo.toml`
     - Java: `pom.xml` (Maven) or `build.gradle` (Gradle)
     - Kotlin: `build.gradle.kts` / `build.gradle` (declare the Kotlin plugin/compiler)
     - C#: `<PackageReference>` in the `.csproj`
     - PHP: `require` in `composer.json`
     - Ruby: `Gemfile`
     - Dart: `pubspec.yaml`
     - C++: `CMakeLists.txt` (and `vcpkg.json` / `conanfile.txt` if you use a package manager)

   Installing inside the container without (a) capturing it in `test.sh` and (b) declaring it in the manifest is equivalent to hiding a dependency, and the build WILL fail at evaluation time. In particular, **do not call a language tool (e.g. `dart`, `go`, `mvn`, `cargo`, `dotnet`, `composer`, `kotlinc`) in `test.sh` without first ensuring `test.sh` installs that toolchain when it is absent** (e.g. guard with `command -v dart >/dev/null || <install dart>`).

7. **System packages count too.** Anything you install with `apt` (compilers, headers, `build-essential`, `cmake`, `pkg-config`, `protoc`, etc.) must also be installed by `rcb_tests/test.sh` (idempotently — check-then-install), because the evaluation container starts clean. Use the proxy fallback above only if such an `apt`/download step fails on the direct connection.

8. **Do not hard-code absolute paths.** Developer-machine paths, SDK install directories, and local package cache paths must never be written into `test.sh` / build scripts; use relative paths or environment variables only.

9. **Rebuild from a clean state before self-checking**: `rm -rf` build caches such as `target/`, `bin/`, `obj/`, `node_modules/`, `build/`, then run `bash rcb_tests/test.sh --cases-dir public_test_cases` to ensure the toolchain bootstrap and all dependencies are correctly captured by `test.sh` + the declaration files and all public cases pass. Only then is the task complete.
