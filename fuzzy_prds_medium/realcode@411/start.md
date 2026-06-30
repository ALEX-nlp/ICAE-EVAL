## Product Requirement Document

Hey team, picking this up from the last sprint planning — we need to ship the shader cross-compilation adapter. The basic idea is: a developer drops in one compiled shader artifact and our tool spits out whatever the target platform needs. We've had complaints from the graphics team that they're maintaining like four different hand-written versions of the same shader and they keep drifting out of sync, so this is supposed to fix that pain point.

The tool should read a JSON command from stdin and write results to stdout. We support a handful of output targets — the usual suspects the graphics team uses day-to-day. One thing that keeps coming up in reviews: when something goes wrong (bad input, garbage assembly, etc.), it should NOT crash or leak any internal runtime stuff — just return a clean, predictable error shape every time, whatever the target was.

Also, remember that compatibility handling we did for the browser-side shader environment? Same idea here — if the shader was authored for that environment, we need to normalize it before processing. Check how we handled the environment transform logic in the existing pipeline, it's similar.

Output format matters a lot — the graphics team's CI is parsing stdout directly, so the exact shape of success AND error responses needs to be locked down. Binary targets are a special case too, since you obviously can't print raw bytes — figure out what observable signals make sense there.

Architecture-wise, keep things modular — adding a new output target later shouldn't require touching the core engine.

One follow-up from the questions in chat: the stdout shape needs to be really literal. For textual targets (glsl, hlsl, msl), a successful response is exactly a line `status=success`, a line `target=<target>`, a line `---`, then the verbatim generated source code. For the binary target (vulkan), a successful response is `status=success`, `target=vulkan`, `magic=0x07230203`, `word_count=<N>` — no source text, no raw bytes printed.

On the failure side, all validation or assembly failures must emit exactly three lines: `error=invalid_module`, `stage=cross_compile`, `target=<requested_target>`. No stack traces, no internal diagnostics, no partial output — regardless of which target was requested.

Also just to lock down the supported values, the target values are `glsl`, `hlsl`, `msl`, and `vulkan`. Each maps to a distinct translator. `glsl` produces GLSL source, `hlsl` produces HLSL source, `msl` produces Metal Shading Language source, and `vulkan` produces a Vulkan SPIR-V binary represented by its magic number and word count.

For the browser-authored path, when the JSON input includes `source_env`: `webgpu`, the engine must first transform the module from the WebGPU environment (using SPV_KHR_vulkan_memory_model / VulkanKHR memory model) into the standard Vulkan environment, then re-validate the transformed module, and only then cross-compile to the requested target. The success output shape is identical to non-webgpu inputs for each target type. If `source_env` is absent or null, no transform is applied. The transform itself is the WebGPU-to-Vulkan environment transform triggered by `source_env`: `webgpu` in the JSON input, which strips VulkanMemoryModelKHR capability and SPV_KHR_vulkan_memory_model extension and switches the memory model from VulkanKHR to GLSL450.

And for the couple of concrete output checks people asked for: for the standard test SPIR-V assembly (the vertex color pass-through shader with ESSL 310), the Vulkan binary output must report `word_count=92`. For the minimal WebGPU-sourced shader (entry-only, no interface variables), after WebGPU-to-Vulkan transform, `word_count=39`.