## Product Requirement Document

Hey team, picking this up from the last sprint planning — we need to ship the shader cross-compilation adapter. The basic idea is: a developer drops in one compiled shader artifact and our tool spits out whatever the target platform needs. We've had complaints from the graphics team that they're maintaining like four different hand-written versions of the same shader and they keep drifting out of sync, so this is supposed to fix that pain point.

The tool should read a JSON command from stdin and write results to stdout. We support a handful of output targets — the usual suspects the graphics team uses day-to-day. One thing that keeps coming up in reviews: when something goes wrong (bad input, garbage assembly, etc.), it should NOT crash or leak any internal runtime stuff — just return a clean, predictable error shape every time, whatever the target was.

Also, remember that compatibility handling we did for the browser-side shader environment? Same idea here — if the shader was authored for that environment, we need to normalize it before processing. Check how we handled the environment transform logic in the existing pipeline, it's similar.

Output format matters a lot — the graphics team's CI is parsing stdout directly, so the exact shape of success AND error responses needs to be locked down. Binary targets are a special case too, since you obviously can't print raw bytes — figure out what observable signals make sense there.

Architecture-wise, keep things modular — adding a new output target later shouldn't require touching the core engine.