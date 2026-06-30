## Product Requirement Document

Hey team, so we need to get the gallery scaffolding generator wrapped up. The idea is that devs on any project can point this tool at their component list and get back a ready-to-run Dart gallery app without writing any of the boring boilerplate themselves. It basically needs to spit out all the different pieces — the navigation wiring, the import block at the top, the theme hookup, the type registries for enums and models, and the root app widget. We talked about this in the last arch sync and everyone agreed the output has to be 100% deterministic, like two runs on the same input must produce byte-identical output, because downstream tooling diffs the files.

One thing that keeps coming up from the mobile team is that the theme integration is fragile — sometimes the accessor is a plain function, sometimes it lives on a class, sometimes it's a getter not a method, and the current hand-rolled approach keeps getting it wrong. We need that handled cleanly without people having to edit the generated file afterwards.

Also there's a known pain point where multiple independently generated JSON chunks get concatenated and the boundary between them breaks downstream parsing — same kind of fix we did for the export merge issue in the settings module, just apply that same pattern here.

The whole thing should come in as a simple stdin command and write back to stdout so it fits into the existing CI pipe. Reach out if the enum seeding behaviour or the provider dependency detection logic is unclear.