## Product Requirement Document

# SPIR-V Cross-Compilation Library - Translate Compiled Shader Modules Into Shading Languages

## Project Goal

Build a library and command adapter that take a compiled intermediate shader module — a SPIR-V binary, supplied here as its textual assembly listing — validate it, and translate it into whatever representation a target graphics platform expects: a high-level textual shading program (GLSL, HLSL, or Metal Shading Language) or a platform-flavoured SPIR-V binary. Developers can ship one intermediate shader artifact and obtain the right form for each backend without hand-porting shader code.

---

## Background & Problem

A modern application targets many graphics backends at once: desktop OpenGL wants GLSL, Direct3D wants HLSL, Apple platforms want Metal Shading Language, and Vulkan wants its own dialect of SPIR-V. Authoring and maintaining one hand-written shader per backend is repetitive, error-prone, and drifts out of sync as the shader evolves. There is also no easy way to be confident a module is well-formed before feeding it to a downstream driver.

With this library a developer compiles a shader once to the intermediate SPIR-V form and then asks for whichever target representation a given platform needs. The library validates the incoming module, emits the requested representation, and reports a clean, normalized failure when the module is not valid. It also understands that a module may have been authored for a particular source execution environment (for example the WebGPU environment) and can transform such a module into a conventional target environment before producing output.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** The physical structure of the codebase MUST match the complexity of the domain. The cross-compilation engine (validation, environment handling, per-target translation) is a non-trivial domain and MUST NOT be a single "god file"; separate the engine, the per-target translators, and the execution adapter into clear units. Do not over-engineer, but do not collapse distinct responsibilities together either.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output test cases in the "Core Features" section are a **black-box testing contract** for the execution adapter, NOT the internal data model of the engine. The core translation logic must remain completely decoupled from stdin/stdout and JSON parsing. The execution adapter is solely responsible for translating a JSON command into idiomatic calls into the core engine and rendering the result on stdout.

3. **Adherence to SOLID Design Principles:**
   - **Single Responsibility Principle (SRP):** Separate input parsing, target routing, module validation, core translation, and output formatting.
   - **Open/Closed Principle (OCP):** Adding a new target representation must not require modifying the existing engine core.
   - **Liskov Substitution Principle (LSP):** Each target translator must be substitutable behind a common translation abstraction.
   - **Interface Segregation Principle (ISP):** Keep the translation interfaces small and cohesive.
   - **Dependency Inversion Principle (DIP):** High-level orchestration depends on translation abstractions, not on concrete I/O.

4. **Robustness & Interface Design:**
   - **Idiomatic Usage:** The public interface of the core engine must be elegant and idiomatic to the implementation language, hiding the internal translation machinery.
   - **Resilience:** Invalid or malformed modules must be handled gracefully. Failures must be modeled as explicit result states (not silent crashes), and the adapter must render them as the normalized error contract described below — never leaking host-language runtime artifacts.

---

## Core Features

### Feature 1: Cross-Compile a Module Into GLSL

**As a developer**, I want to translate a validated shader module into a GLSL program, so I can run my single intermediate artifact on OpenGL-style backends.

**Expected Behavior / Usage:**

The command names a textual target and supplies a SPIR-V assembly listing. The engine assembles the listing into a binary module, validates it, and translates it into GLSL. On success the output is two header lines — a `status=success` line and a `target=glsl` line — then a single `---` separator line, then the verbatim generated GLSL program text. The GLSL version line in the generated program reflects the version detected in the source module (for example an embedded ES [check for embedded GLSL version string within assembly] hint yields a `#version [check for embedded GLSL version string within assembly] es` program). An empty or malformed module is not a valid input here; that error path is covered by Feature 5.

**Test Cases:** `rcb_tests/public_test_cases/feature1_compile_to_glsl.json`

```json
{
    "description": "Validate a SPIR-V module and cross-compile it into a GLSL program. The input is a SPIR-V assembly listing for the requested textual target; on success the output is a header line block followed by the verbatim generated GLSL source.",
    "cases": [
        {
            "input": {
                "target": "glsl",
                "assembly": "               OpCapability Shader\n          %1 = OpExtInstImport \"GLSL.std.450\"\n               OpMemoryModel Logical GLSL450\n               OpEntryPoint Vertex %main \"main\" %outColor %vtxColor\n               OpSource ESSL [check for embedded GLSL version string within assembly]\n               OpName %main \"main\"\n               OpName %outColor \"outColor\"\n               OpName %vtxColor \"vtxColor\"\n               OpDecorate %outColor Location 0\n               OpDecorate %vtxColor Location 0\n       %void = OpTypeVoid\n          %3 = OpTypeFunction %void\n      %float = OpTypeFloat 32\n    %v4float = OpTypeVector %float 4\n%_ptr_Output_v4float = OpTypePointer Output %v4float\n   %outColor = OpVariable %_ptr_Output_v4float Output\n%_ptr_Input_v4float = OpTypePointer Input %v4float\n   %vtxColor = OpVariable %_ptr_Input_v4float Input\n       %main = OpFunction %void None %3\n          %5 = OpLabel\n         %12 = OpLoad %v4float %vtxColor\n               OpStore %outColor %12\n               OpReturn\n               OpFunctionEnd\n"
            },
            "expected_output": "status=success\ntarget=glsl\n---\n#version [check for embedded GLSL version string within assembly] es\n\nlayout(location = 0) out vec4 outColor;\nlayout(location = 0) in vec4 vtxColor;\n\nvoid main()\n{\n    outColor = vtxColor;\n}\n\n"
        }
    ]
}
```

---

### Feature 2: Cross-Compile a Module Into HLSL

**As a developer**, I want to translate a validated shader module into an HLSL program, so I can run my single intermediate artifact on Direct3D-style backends.

**Expected Behavior / Usage:**

The command names the HLSL target and supplies a SPIR-V assembly listing. The engine assembles, validates, and translates the module into HLSL. On success the output is a `status=success` line, a `target=hlsl` line, a `---` separator line, and then the verbatim generated HLSL program text. The generated program reflects the default HLSL shader model conventions (for example, the produced vertex entry point is wrapped in a `main` function that calls an inner `vert_main`).

**Test Cases:** `rcb_tests/public_test_cases/feature2_compile_to_hlsl.json`

```json
{
    "description": "Validate a SPIR-V module and cross-compile it into an HLSL program. On success the output is the header block followed by the verbatim generated HLSL source.",
    "cases": [
        {
            "input": {
                "target": "hlsl",
                "assembly": "               OpCapability Shader\n          %1 = OpExtInstImport \"GLSL.std.450\"\n               OpMemoryModel Logical GLSL450\n               OpEntryPoint Vertex %main \"main\" %outColor %vtxColor\n               OpSource ESSL [check for embedded GLSL version string within assembly]\n               OpName %main \"main\"\n               OpName %outColor \"outColor\"\n               OpName %vtxColor \"vtxColor\"\n               OpDecorate %outColor Location 0\n               OpDecorate %vtxColor Location 0\n       %void = OpTypeVoid\n          %3 = OpTypeFunction %void\n      %float = OpTypeFloat 32\n    %v4float = OpTypeVector %float 4\n%_ptr_Output_v4float = OpTypePointer Output %v4float\n   %outColor = OpVariable %_ptr_Output_v4float Output\n%_ptr_Input_v4float = OpTypePointer Input %v4float\n   %vtxColor = OpVariable %_ptr_Input_v4float Input\n       %main = OpFunction %void None %3\n          %5 = OpLabel\n         %12 = OpLoad %v4float %vtxColor\n               OpStore %outColor %12\n               OpReturn\n               OpFunctionEnd\n"
            },
            "expected_output": "status=success\ntarget=hlsl\n---\nuniform float4 gl_HalfPixel;\n\nvoid vert_main()\n{\n    gl_Position.x = gl_Position.x - gl_HalfPixel.x * gl_Position.w;\n    gl_Position.y = gl_Position.y + gl_HalfPixel.y * gl_Position.w;\n}\n\nvoid main()\n{\n    vert_main();\n}\n"
        }
    ]
}
```

---

### Feature 3: Cross-Compile a Module Into Metal Shading Language

**As a developer**, I want to translate a validated shader module into a Metal Shading Language program, so I can run my single intermediate artifact on Apple-platform backends.

**Expected Behavior / Usage:**

The command names the MSL target and supplies a SPIR-V assembly listing. The engine assembles, validates, and translates the module into MSL. On success the output is a `status=success` line, a `target=msl` line, a `---` separator line, and then the verbatim generated MSL program text, including the Metal standard-library includes and the `using namespace metal;` preamble, the input/output struct declarations derived from the module's interface, and the entry-point function.

**Test Cases:** `rcb_tests/public_test_cases/feature3_compile_to_msl.json`

```json
{
    "description": "Validate a SPIR-V module and cross-compile it into a Metal Shading Language program. On success the output is the header block followed by the verbatim generated MSL source.",
    "cases": [
        {
            "input": {
                "target": "msl",
                "assembly": "               OpCapability Shader\n          %1 = OpExtInstImport \"GLSL.std.450\"\n               OpMemoryModel Logical GLSL450\n               OpEntryPoint Vertex %main \"main\" %outColor %vtxColor\n               OpSource ESSL [check for embedded GLSL version string within assembly]\n               OpName %main \"main\"\n               OpName %outColor \"outColor\"\n               OpName %vtxColor \"vtxColor\"\n               OpDecorate %outColor Location 0\n               OpDecorate %vtxColor Location 0\n       %void = OpTypeVoid\n          %3 = OpTypeFunction %void\n      %float = OpTypeFloat 32\n    %v4float = OpTypeVector %float 4\n%_ptr_Output_v4float = OpTypePointer Output %v4float\n   %outColor = OpVariable %_ptr_Output_v4float Output\n%_ptr_Input_v4float = OpTypePointer Input %v4float\n   %vtxColor = OpVariable %_ptr_Input_v4float Input\n       %main = OpFunction %void None %3\n          %5 = OpLabel\n         %12 = OpLoad %v4float %vtxColor\n               OpStore %outColor %12\n               OpReturn\n               OpFunctionEnd\n"
            },
            "expected_output": "status=success\ntarget=msl\n---\n#include <metal_stdlib>\n#include <simd/simd.h>\n\nusing namespace metal;\n\nstruct main0_out\n{\n    float4 outColor [[user(locn0)]];\n};\n\nstruct main0_in\n{\n    float4 vtxColor [[attribute(0)]];\n};\n\nvertex main0_out main0(main0_in in [[stage_in]])\n{\n    main0_out out = {};\n    out.outColor = in.vtxColor;\n    return out;\n}\n\n"
        }
    ]
}
```

---

### Feature 4: Re-Emit a Module as a Vulkan SPIR-V Binary

**As a developer**, I want to validate a module and obtain it as a Vulkan-flavoured SPIR-V binary, so I can feed a known-good binary directly to a Vulkan driver.

**Expected Behavior / Usage:**

The command names the binary target and supplies a SPIR-V assembly listing. The engine assembles, validates, and produces a binary word stream rather than textual source. Because raw binary is not meaningful as printed characters, the contract reports the observable binary signals instead: a `status=success` line, a `target=vulkan` line, a `magic=` line carrying the SPIR-V container magic number `0x07230203`, and a `word_count=` line giving the number of 32-bit words in the produced module. The word count is a stable property of the validated module for a given input.

**Test Cases:** `rcb_tests/public_test_cases/feature4_compile_to_vulkan.json`

```json
{
    "description": "Validate a SPIR-V module and re-emit it as a Vulkan SPIR-V binary module. Unlike the textual targets, the result is a binary word stream; the output reports the binary container magic number and the number of 32-bit words produced.",
    "cases": [
        {
            "input": {
                "target": "vulkan",
                "assembly": "               OpCapability Shader\n          %1 = OpExtInstImport \"GLSL.std.450\"\n               OpMemoryModel Logical GLSL450\n               OpEntryPoint Vertex %main \"main\" %outColor %vtxColor\n               OpSource ESSL [check for embedded GLSL version string within assembly]\n               OpName %main \"main\"\n               OpName %outColor \"outColor\"\n               OpName %vtxColor \"vtxColor\"\n               OpDecorate %outColor Location 0\n               OpDecorate %vtxColor Location 0\n       %void = OpTypeVoid\n          %3 = OpTypeFunction %void\n      %float = OpTypeFloat 32\n    %v4float = OpTypeVector %float 4\n%_ptr_Output_v4float = OpTypePointer Output %v4float\n   %outColor = OpVariable %_ptr_Output_v4float Output\n%_ptr_Input_v4float = OpTypePointer Input %v4float\n   %vtxColor = OpVariable %_ptr_Input_v4float Input\n       %main = OpFunction %void None %3\n          %5 = OpLabel\n         %12 = OpLoad %v4float %vtxColor\n               OpStore %outColor %12\n               OpReturn\n               OpFunctionEnd\n"
            },
            "expected_output": "status=success\ntarget=vulkan\nmagic=0x07230203\nword_count=92\n"
        }
    ]
}
```

---

### Feature 5: Reject Invalid Modules With a Normalized Error

**As a developer**, I want malformed or empty inputs to fail cleanly with a stable error category, so I can detect bad shaders early without my tool crashing or leaking internal diagnostics.

**Expected Behavior / Usage:**

When the supplied source does not assemble and validate into a well-formed SPIR-V module — whether it is empty or syntactically meaningless — the request is rejected before any program is produced, regardless of which target was requested. The output is a normalized, language-neutral error block: an `error=invalid_module` line, a `stage=cross_compile` line indicating the phase that rejected the input, and a `target=` line echoing the requested target. No partial source, no binary signals, and no host-runtime diagnostic strings are emitted.

**Test Cases:** `rcb_tests/public_test_cases/feature5_reject_invalid_module.json`

```json
{
    "description": "Reject a source that is not a valid SPIR-V module. Whether the input is empty or syntactically meaningless, and regardless of the requested target, the request is rejected with a normalized error category instead of producing any program output.",
    "cases": [
        {
            "input": {
                "target": "glsl",
                "assembly": ""
            },
            "expected_output": "error=invalid_module\nstage=cross_compile\ntarget=glsl\n"
        },
        {
            "input": {
                "target": "glsl",
                "assembly": "this is not valid spirv assembly"
            },
            "expected_output": "error=invalid_module\nstage=cross_compile\ntarget=glsl\n"
        },
        {
            "input": {
                "target": "vulkan",
                "assembly": "this is not valid spirv assembly"
            },
            "expected_output": "error=invalid_module\nstage=cross_compile\ntarget=vulkan\n"
        }
    ]
}
```

---

### Feature 6: Transform a WebGPU-Environment Module Before Cross-Compiling

**As a developer**, I want a module authored for the WebGPU execution environment to be transformed into a conventional target environment before output, so I can reuse WebGPU-authored shaders across every backend.

**Expected Behavior / Usage:**

When the command declares the source execution environment as WebGPU, the engine first transforms the module from the WebGPU environment into the Vulkan environment, re-validates the transformed module, and only then cross-compiles it to the requested target. The success contract is identical to Features 1–4 for each target shape (textual targets emit the header block plus generated source; the binary target emits the magic and word count). This feature groups one leaf functional point per target so each transform-and-translate path is described in isolation.

*6.1 WebGPU → GLSL — transform a WebGPU module and produce a GLSL program*

The WebGPU module is transformed to the Vulkan environment, re-validated, and translated to GLSL. On success the output is the `status=success` / `target=glsl` header block, the `---` separator, and the generated GLSL source. A minimal entry-only WebGPU shader yields a default-version GLSL program with an empty `main`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_webgpu_to_glsl.json`

```json
{
    "description": "Cross-compile a module authored for the WebGPU execution environment into GLSL. The module is first transformed from WebGPU to the Vulkan environment, then validated and cross-compiled; on success the output is the header block followed by the generated GLSL source.",
    "cases": [
        {
            "input": {
                "target": "glsl",
                "assembly": "          OpCapability Shader\n          OpCapability VulkanMemoryModelKHR\n          OpExtension \"SPV_KHR_vulkan_memory_model\"\n          OpMemoryModel Logical VulkanKHR\n          OpEntryPoint Vertex %func \"shader\"\n%void   = OpTypeVoid\n%void_f = OpTypeFunction %void\n%func   = OpFunction %void None %void_f\n%label  = OpLabel\n          OpReturn\n          OpFunctionEnd\n",
                "source_env": "webgpu"
            },
            "expected_output": "status=success\ntarget=glsl\n---\n#version 450\n\nvoid main()\n{\n}\n\n"
        }
    ]
}
```

*6.2 WebGPU → HLSL — transform a WebGPU module and produce an HLSL program*

The WebGPU module is transformed to the Vulkan environment, re-validated, and translated to HLSL. On success the output is the `status=success` / `target=hlsl` header block, the `---` separator, and the generated HLSL source.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_webgpu_to_hlsl.json`

```json
{
    "description": "Cross-compile a WebGPU-environment module into HLSL via a WebGPU-to-Vulkan transform followed by validation and cross-compilation.",
    "cases": [
        {
            "input": {
                "target": "hlsl",
                "assembly": "          OpCapability Shader\n          OpCapability VulkanMemoryModelKHR\n          OpExtension \"SPV_KHR_vulkan_memory_model\"\n          OpMemoryModel Logical VulkanKHR\n          OpEntryPoint Vertex %func \"shader\"\n%void   = OpTypeVoid\n%void_f = OpTypeFunction %void\n%func   = OpFunction %void None %void_f\n%label  = OpLabel\n          OpReturn\n          OpFunctionEnd\n",
                "source_env": "webgpu"
            },
            "expected_output": "status=success\ntarget=hlsl\n---\nuniform float4 gl_HalfPixel;\n\nvoid vert_main()\n{\n    gl_Position.x = gl_Position.x - gl_HalfPixel.x * gl_Position.w;\n    gl_Position.y = gl_Position.y + gl_HalfPixel.y * gl_Position.w;\n}\n\nvoid main()\n{\n    vert_main();\n}\n"
        }
    ]
}
```

*6.3 WebGPU → MSL — transform a WebGPU module and produce a Metal Shading Language program*

The WebGPU module is transformed to the Vulkan environment, re-validated, and translated to MSL. On success the output is the `status=success` / `target=msl` header block, the `---` separator, and the generated MSL source. A minimal entry-only WebGPU shader yields the Metal preamble plus an empty entry-point function named after the module's entry point.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_webgpu_to_msl.json`

```json
{
    "description": "Cross-compile a WebGPU-environment module into Metal Shading Language via a WebGPU-to-Vulkan transform followed by validation and cross-compilation.",
    "cases": [
        {
            "input": {
                "target": "msl",
                "assembly": "          OpCapability Shader\n          OpCapability VulkanMemoryModelKHR\n          OpExtension \"SPV_KHR_vulkan_memory_model\"\n          OpMemoryModel Logical VulkanKHR\n          OpEntryPoint Vertex %func \"shader\"\n%void   = OpTypeVoid\n%void_f = OpTypeFunction %void\n%func   = OpFunction %void None %void_f\n%label  = OpLabel\n          OpReturn\n          OpFunctionEnd\n",
                "source_env": "webgpu"
            },
            "expected_output": "status=success\ntarget=msl\n---\n#include <metal_stdlib>\n#include <simd/simd.h>\n\nusing namespace metal;\n\nvertex void shader()\n{\n}\n\n"
        }
    ]
}
```

*6.4 WebGPU → Vulkan binary — transform a WebGPU module and re-emit a Vulkan SPIR-V binary*

The WebGPU module is transformed to the Vulkan environment, re-validated, and re-emitted as a Vulkan SPIR-V binary. On success the output reports the binary signals: `status=success`, `target=vulkan`, the `magic=0x07230203` container magic, and the `word_count=` of the produced module.

**Test Cases:** `rcb_tests/public_test_cases/feature6_4_webgpu_to_vulkan.json`

```json
{
    "description": "Transform a WebGPU-environment module to the Vulkan environment and re-emit it as a Vulkan SPIR-V binary; the output reports the binary magic number and word count.",
    "cases": [
        {
            "input": {
                "target": "vulkan",
                "assembly": "          OpCapability Shader\n          OpCapability VulkanMemoryModelKHR\n          OpExtension \"SPV_KHR_vulkan_memory_model\"\n          OpMemoryModel Logical VulkanKHR\n          OpEntryPoint Vertex %func \"shader\"\n%void   = OpTypeVoid\n%void_f = OpTypeFunction %void\n%func   = OpFunction %void None %void_f\n%label  = OpLabel\n          OpReturn\n          OpFunctionEnd\n",
                "source_env": "webgpu"
            },
            "expected_output": "status=success\ntarget=vulkan\nmagic=0x07230203\nword_count=[expect a small positive integer word count matching transformed size]\n"
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured cross-compilation engine implementing the features above — module assembly/validation, optional source-environment transformation, and per-target translation to GLSL, HLSL, MSL, and the Vulkan binary form. Its physical structure MUST follow the "Scale-Driven Code Organization" constraint: distinct units for the engine core, the per-target translators, and the execution adapter; no monolithic file.

2. **The Execution/Test Adapter:** A runnable program that acts as a client to the core engine. It reads a single JSON command from stdin (`target`, `assembly`, and optional `source_env`), invokes the appropriate core logic, and prints the result to stdout, strictly matching the per-leaf-feature contracts above. The adapter is solely responsible for normalizing any engine failure into the neutral `error=invalid_module` contract; it must be logically (and ideally physically) separated from the core domain.

3. **Automated test harness.** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` to point at a directory of case files (default `test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case in `feature1_compile_to_glsl.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_compile_to_glsl@000.txt`). Output is namespaced by `<cases-dir>` so running different case directories never overwrites each other. Each `.txt` file contains **only** the raw stdout from the program under test (no PASS/FAIL summaries or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- malformed text that cannot be parsed as SPIR-V
