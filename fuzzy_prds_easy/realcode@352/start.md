## Product Requirement Document

# Embedded-Device Application Build Pipeline — Artifact Assembly & Packaging Contract

## Project Goal

Build a staged build pipeline that turns a compiled cross-platform UI application and its native plugins into the layout and package format required by an embedded-device target, so application developers can produce a runnable, signable on-device package without hand-copying engine binaries, snapshots, headers, and plugin libraries into the exact directory structure the device runtime expects.

---

## Background & Problem

A cross-platform UI application that targets an embedded device is not a single artifact: at install time the device runtime expects a precise on-disk layout — the engine runtime shared object, a platform embedder shared object, an interpreter/ICU data blob, the application's compiled snapshot, an asset bundle, generated plugin-registration glue, and every native plugin compiled and linked in the correct form. Without a pipeline, developers must manually compile the C++ embedding and each native plugin, decide which shipped prebuilt libraries are valid for the target architecture and api level, lay everything out under runtime-specific paths, and finally drive the platform packaging/signing tool. This is repetitive, easy to get subtly wrong (a misplaced or wrong-variant `.so` only fails on-device), and must differ between a *managed-runtime* application and a *native* application, and again between producing a final installable package versus an add-to-app module.

With this pipeline, each concern becomes an independently invokable stage with a deterministic, inspectable output contract: given a prepared workspace, a stage runs the corresponding build step and reports exactly which output artifacts were produced at which relative paths, or a normalized error category when a precondition (such as a signing certificate) is missing.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a multi-responsibility domain (asset bundling, native compilation, plugin selection, packaging, signing, error normalization). It MUST NOT be a single "god file". Separate the build stages, the workspace/process abstractions, and the output rendering into distinct logical units with a clear directory tree.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a **black-box contract** for an execution adapter, NOT the internal data model. The core build-stage logic must be decoupled from stdin/stdout and JSON parsing. A thin adapter translates a JSON command into an idiomatic call into a build stage and renders the produced artifacts (or a normalized error) into the line-oriented contract.

3. **Adherence to SOLID Design Principles:**
   - **SRP:** Keep command parsing, workspace setup, stage execution, artifact probing, and output formatting in distinct units.
   - **OCP:** Adding a new build stage must not require modifying existing stages.
   - **LSP:** The device-SDK and process abstractions must be substitutable by test doubles without changing stage logic.
   - **ISP:** Keep the device-SDK / process interfaces small and cohesive.
   - **DIP:** Stages depend on filesystem, process, and device-SDK abstractions, not concrete I/O.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public stage interface must be elegant and idiomatic to the target language.
   - **Resilience:** Missing preconditions (e.g. no signing certificate) must surface as a modeled, normalized error category — never as a raw runtime fault leaking host-language detail.

---

## Core Features

The execution adapter reads one JSON command object from stdin. The command selects a build `stage` and, for stages with variants, a `scenario`. The adapter renders a line-oriented report: each probed output is emitted as an `artifact=<relative path>` header immediately followed by a `present=true|false` line; stages that emit linkage metadata add domain fields such as `user_libs=<value>`; and a rejected precondition produces a single normalized `error=<category>` line.

### Feature 1: Debug Asset Bundle Assembly

**As a developer**, I want a stage that assembles the debug-mode runtime asset bundle, so I can ship the interpreter snapshots and JIT kernel needed to run an unoptimized build on device.

**Expected Behavior / Usage:**

Given a build workspace where the compiled kernel (`app.dill`) and the shared VM/isolate snapshot data already exist, the stage produces the asset bundle directory. For a debug build the bundle MUST contain the two interpreter snapshot blobs (`[a specific set of debug artifacts listed in the PRD]`, `[a specific set of debug artifacts listed in the PRD]`) and the JIT kernel blob (`[a specific set of debug artifacts listed in the PRD]`). The output reports each expected entry with its presence flag, in order.

**Test Cases:** `rcb_tests/public_test_cases/feature1_debug_asset_bundle.json`

```json
{
    "description": "Debug-mode asset bundling stage. Given a build environment whose kernel snapshot (app.dill) and the shared VM/isolate snapshot data have already been produced, the stage assembles the runtime asset bundle. The output is a line-oriented report listing each expected bundle entry as an `artifact=<relative path>` header followed by a `present=true|false` line indicating whether it was emitted under the bundle directory. For a debug build, the bundle must contain the two interpreter snapshot blobs plus the JIT kernel blob.",
    "cases": [
        {
            "input": {"stage": "debug_application"},
            "expected_output": "artifact=[a specific set of debug artifacts listed in the PRD]\npresent=true\nartifact=[a specific set of debug artifacts listed in the PRD]\npresent=true\nartifact=[a specific set of debug artifacts listed in the PRD]\npresent=true\n"
        }
    ]
}
```

---

### Feature 2: Native C++ Embedding Compilation

**As a developer**, I want a stage that compiles the native C++ embedding into a static archive and stages its public headers, so the native application package can link against the embedding.

**Expected Behavior / Usage:**

Given an embedding source tree that declares a static-library project and ships public C++ headers, the stage compiles the embedding into a static archive and copies the public headers into the embedding output directory. The output reports the staged header (`include/flutter.h`) and the produced static archive (`libembedding_cpp.a`), each with its presence flag.

**Test Cases:** `rcb_tests/public_test_cases/feature2_cpp_embedding.json`

```json
{
    "description": "Native C++ embedding compilation stage. Given an embedding source tree that declares a static-library project and ships public C++ headers, the stage compiles the embedding into a static archive and stages the public headers into the build output. The report lists the staged header and the produced static archive, each as an `artifact=<relative path>` / `present=true|false` pair under the embedding output directory.",
    "cases": [
        {
            "input": {"stage": "native_embedding"},
            "expected_output": "artifact=include/flutter.h\npresent=true\nartifact=libembedding_cpp.a\npresent=true\n"
        }
    ]
}
```

---

### Feature 3: Native Plugin Compilation

**As a developer**, I want a stage that compiles a project's native plugins and selects only the prebuilt libraries valid for my target, so the packaged app links the right native code for the device.

**Expected Behavior / Usage:**

*3.1 Static-Library Plugin — a plugin declared as a static library is folded into one combined plugin shared object*

When a project depends on a native plugin whose platform manifest declares a plugin class and a public header, and whose build descriptor marks it as a static library, the stage compiles it and aggregates all static-library plugins into a single combined plugin shared object. The plugin's public header is staged into the plugin include directory, and the combined shared object (`lib/libflutter_plugins.so`) is produced.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_plugin_static_library.json`

```json
{
    "description": "Native plugin compilation — static-library plugin. A project depends on one native plugin whose platform manifest declares a plugin class and a public header, and whose build descriptor marks it as a static library. The stage compiles the plugin and aggregates all static-library plugins into a single combined shared object. The report shows the plugin's public header is staged into the plugin include directory and that the combined plugin shared object is produced.",
    "cases": [
        {
            "input": {"stage": "native_plugins", "scenario": "static_lib"},
            "expected_output": "artifact=include/some_native_plugin.h\npresent=true\nartifact=lib/libflutter_plugins.so\npresent=true\n"
        }
    ]
}
```

*3.2 Shared-Library Plugin — a plugin declared as a shared library keeps its own object and is not folded in*

When the plugin's build descriptor marks it as a shared library (and it ships its own shared object), the stage does NOT fold it into the combined static-plugin object. The combined aggregate (`lib/libflutter_plugins.so`) is absent, while the plugin's own shared object and its shipped side-car shared object are present.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_plugin_shared_library.json`

```json
{
    "description": "Native plugin compilation — shared-library plugin. When a plugin's build descriptor marks it as a shared library (and ships its own shared object), the stage does NOT fold it into the combined static-plugin shared object; instead it emits the plugin's own shared object plus any side-car shared objects it provides. The report shows the combined aggregate object is absent while the plugin's individual shared object and its shipped shared object are present.",
    "cases": [
        {
            "input": {"stage": "native_plugins", "scenario": "shared_lib"},
            "expected_output": "artifact=lib/libflutter_plugins.so\npresent=false\nartifact=lib/libsome_native_plugin.so\npresent=true\nartifact=[the specific signed library build order for shared profiles]\npresent=true\n"
        }
    ]
}
```

*3.3 Resource Staging — a plugin's resource tree is copied recursively under a per-plugin namespace*

A plugin that ships a resource tree under its platform resource directory has those resources copied recursively into a per-plugin resource sub-directory of the plugin build output, preserving nested paths. A nested resource file appears at its mirrored path namespaced under the plugin's name.

**Test Cases:** `rcb_tests/public_test_cases/feature3_3_plugin_resource_copy.json`

```json
{
    "description": "Native plugin compilation — resource staging. A plugin that ships a resource tree under its platform resource directory has those resources copied recursively into a per-plugin resource sub-directory of the plugin build output, preserving nested paths. The report confirms a nested resource file is present at its mirrored path namespaced under the plugin's name.",
    "cases": [
        {
            "input": {"stage": "native_plugins", "scenario": "resources"},
            "expected_output": "artifact=res/some_native_plugin/a/b.txt\npresent=true\n"
        }
    ]
}
```

*3.4 User Library Selection — only architecture/api-matching prebuilt libraries are copied, and linkage metadata is recorded*

A plugin may ship a mix of prebuilt libraries: a top-level static archive, a top-level shared object, architecture-specific shared objects (one matching the target architecture, one not), and api-version-specific shared objects (one at or below the project's api level, one above). The stage copies only the libraries valid for the target architecture and api version: top-level shared objects and matching arch/api shared objects are copied; the static archive and non-matching arch/api objects are skipped. It also records the selected user libraries by bare base name (dropping the `lib` prefix and the extension) in a `user_libs=` linkage field — which additionally carries the toolchain default `pthread`.

**Test Cases:** `rcb_tests/public_test_cases/feature3_4_plugin_user_libraries.json`

```json
{
    "description": "Native plugin compilation — user library selection and linkage metadata. A plugin ships a mix of prebuilt libraries under its platform lib directory: a top-level static archive, a top-level shared object, architecture-specific shared objects (one matching the target architecture, one not), and api-version-specific shared objects (one at or below the project's api level, one above). The stage copies only the libraries relevant to the target architecture and api version: top-level shared objects and matching arch/api shared objects are copied; the static archive and non-matching arch/api objects are skipped. It also records the selected user libraries (by bare base name, minus the `lib` prefix and extension) in a linkage metadata field. The report lists presence for each candidate library and a `user_libs=` line carrying the space-separated selected library names (which also includes the toolchain default `pthread`).",
    "cases": [
        {
            "input": {"stage": "native_plugins", "scenario": "user_libraries"},
            "expected_output": "artifact=[the specific signed library build order for shared profiles]\npresent=false\nartifact=[the specific signed library build order for shared profiles]\npresent=true\nartifact=[the specific signed library build order for shared profiles]\npresent=true\nartifact=[the specific signed library build order for shared profiles]\npresent=false\nartifact=[the specific signed library build order for shared profiles]\npresent=true\nartifact=[the specific signed library build order for shared profiles]\npresent=false\nuser_libs=pthread some_native_plugin static shared shared_arm shared_40\n"
        }
    ]
}
```

---

### Feature 4: Application Packaging & Module Layout

**As a developer**, I want stages that lay out the full runtime and either produce a signed on-device package or a flat add-to-app module, for both managed-runtime and native applications, so I can ship whichever artifact my deployment needs.

**Expected Behavior / Usage:**

All packaging stages stage a common runtime set — the engine runtime shared object (`lib/libflutter_engine.so`), a platform embedder shared object, the ICU data (`res/icudtl.dat`), the AOT app snapshot (`lib/libapp.so`), the asset bundle (`res/flutter_assets`), and the combined plugin objects. The *managed-runtime* variants stage the embedder as `lib/libflutter_tizen.so`; the *native* variants stage it as `lib/libflutter_tizen_common.so`. A *package* stage additionally drives the platform packaging/signing tool and emits a final installable package, reported under `artifact=tpk` with its presence flag. A *module* stage instead lays the runtime out flat into an output directory for embedding into a host application.

*4.1 Managed-Runtime Package — produce a signed installable package, requiring a certificate profile*

Stages the managed-runtime runtime set (including the asset bundle's runtime dependency manifest `res/flutter_assets/.app.deps.json`) into an ephemeral tree, then drives the packaging tool to produce the signed package and copies it to the output directory. Packaging requires a configured signing certificate profile: when present, the package is produced (`artifact=tpk` → `present=true`) and all staged inputs are present; when absent, the build is rejected with `error=no_certificate_profile`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_managed_tpk.json`

```json
{
    "description": "Managed-runtime application packaging into the platform package (TPK). Given a project that produces a managed-runtime application, the stage stages the engine runtime, the platform embedder shared object, the ICU data, the AOT app snapshot, the asset bundle (including the runtime dependency manifest), and the combined plugin objects into an ephemeral staging tree, then drives the platform packaging tool to produce the signed package and copies it to the output directory. Packaging requires a valid signing certificate profile: when one is configured the package is produced and the staged inputs are present; when none is configured the build is rejected with a normalized `error=no_certificate_profile` line. The `present=true` line under `artifact=tpk` indicates the final package was emitted.",
    "cases": [
        {
            "input": {"stage": "dotnet_tpk", "scenario": "build_succeeds"},
            "expected_output": "artifact=tpk\npresent=true\nartifact=res/flutter_assets\npresent=true\nartifact=lib/libflutter_engine.so\npresent=true\nartifact=lib/libflutter_tizen.so\npresent=true\nartifact=res/icudtl.dat\npresent=true\nartifact=res/flutter_assets/.app.deps.json\npresent=true\nartifact=lib/libapp.so\npresent=true\nartifact=lib/libflutter_plugins.so\npresent=true\nartifact=[the specific signed library build order for shared profiles]\npresent=true\n"
        },
        {
            "input": {"stage": "dotnet_tpk", "scenario": "no_profile"},
            "expected_output": "error=no_certificate_profile\n"
        }
    ]
}
```

*4.2 Native Package — produce a signed installable package for a native application, requiring a certificate profile*

Same packaging contract as 4.1 but for a native application (declaring a native build descriptor); the embedder is staged as the native-common object `lib/libflutter_tizen_common.so`. A valid certificate profile is required, otherwise `error=no_certificate_profile`.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_native_tpk.json`

```json
{
    "description": "Native application packaging into the platform package (TPK). Given a project that produces a native application (declaring a native build descriptor), the stage stages the engine runtime, the native-common platform embedder shared object, the ICU data, the AOT app snapshot, the asset bundle (including the runtime dependency manifest), and the combined plugin objects into an ephemeral staging tree, then builds and signs the package and copies it to the output directory. Packaging requires a valid signing certificate profile: when one is configured the package is produced and the staged inputs are present; when none is configured the build is rejected with a normalized `error=no_certificate_profile` line. Note the native package stages the native-common embedder object, distinguishing it from the managed-runtime package.",
    "cases": [
        {
            "input": {"stage": "native_tpk", "scenario": "build_succeeds"},
            "expected_output": "artifact=tpk\npresent=true\nartifact=res/flutter_assets\npresent=true\nartifact=lib/libflutter_engine.so\npresent=true\nartifact=lib/libflutter_tizen_common.so\npresent=true\nartifact=res/icudtl.dat\npresent=true\nartifact=res/flutter_assets/.app.deps.json\npresent=true\nartifact=lib/libapp.so\npresent=true\nartifact=lib/libflutter_plugins.so\npresent=true\nartifact=[the specific signed library build order for shared profiles]\npresent=true\n"
        },
        {
            "input": {"stage": "native_tpk", "scenario": "no_profile"},
            "expected_output": "error=no_certificate_profile\n"
        }
    ]
}
```

*4.3 Managed-Runtime Module — lay out a flat add-to-app directory for a managed-runtime host*

Instead of producing a final package, the stage lays out the engine runtime, the managed embedder (`lib/libflutter_tizen.so`), the ICU data, the AOT app snapshot, the generated managed plugin-registrant source (`src/GeneratedPluginRegistrant.cs`), the asset bundle, and the combined plugin objects directly into a flat output directory consumable by a host application.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_managed_module.json`

```json
{
    "description": "Managed-runtime module packaging (add-to-app). Instead of producing a final package, the stage lays out the engine runtime, the platform embedder shared object, the ICU data, the AOT app snapshot, the generated managed plugin registrant source, the asset bundle, and the combined plugin objects directly into a flat output directory consumable by a host application. The report lists each emitted artifact under the output directory.",
    "cases": [
        {
            "input": {"stage": "dotnet_module"},
            "expected_output": "artifact=res/flutter_assets\npresent=true\nartifact=lib/libflutter_engine.so\npresent=true\nartifact=lib/libflutter_tizen.so\npresent=true\nartifact=res/icudtl.dat\npresent=true\nartifact=lib/libapp.so\npresent=true\nartifact=src/GeneratedPluginRegistrant.cs\npresent=true\nartifact=lib/libflutter_plugins.so\npresent=true\n"
        }
    ]
}
```

*4.4 Native Module — lay out a flat add-to-app directory for a native host, including the embedding artifacts*

The stage lays out, into a flat output directory consumable by a host native application, the engine runtime, the native-common embedder (`lib/libflutter_tizen_common.so`), the ICU data, the AOT app snapshot, the generated native plugin-registrant header (`inc/generated_plugin_registrant.h`), the combined plugin objects, and the staged native embedding header (`inc/flutter.h`) and embedding static archive (`Release/libembedding_cpp.a`).

**Test Cases:** `rcb_tests/public_test_cases/feature4_4_native_module.json`

```json
{
    "description": "Native module packaging (add-to-app). The stage lays out, into a flat output directory consumable by a host native application, the engine runtime, the native-common platform embedder shared object, the ICU data, the AOT app snapshot, the generated native plugin registrant header, the combined plugin objects, and the staged native embedding header and static archive. The report lists each emitted artifact under the output directory, including the embedding header staged into the include directory and the embedding archive staged into the configuration output directory.",
    "cases": [
        {
            "input": {"stage": "native_module"},
            "expected_output": "artifact=res/flutter_assets\npresent=true\nartifact=lib/libflutter_engine.so\npresent=true\nartifact=lib/libflutter_tizen_common.so\npresent=true\nartifact=res/icudtl.dat\npresent=true\nartifact=lib/libapp.so\npresent=true\nartifact=inc/generated_plugin_registrant.h\npresent=true\nartifact=lib/libflutter_plugins.so\npresent=true\nartifact=inc/flutter.h\npresent=true\nartifact=Release/libembedding_cpp.a\npresent=true\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing the build stages above (asset bundling, native embedding compilation, native plugin compilation with library selection, and managed/native package & module layout), with the device-SDK, process, and filesystem concerns behind abstractions.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON command from stdin, invokes the selected stage in a prepared workspace, and prints the line-oriented report (`artifact=`/`present=` pairs, `user_libs=` metadata, or a normalized `error=` category) to stdout, strictly matching the per-leaf-feature contracts above. The adapter is logically separated from the core stages and is the only component aware of JSON and stdin/stdout.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` containing **only** the raw stdout of the program under test, so it can be compared directly against `expected_output`. Output is namespaced by `<cases-dir>` so different case directories never overwrite each other.


---
**Implementation notes:**
- ensure the threading component has its namespace prepended before serialization
- respect the release build directory structure for the C++ embedding artifact
