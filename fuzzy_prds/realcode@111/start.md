## Product Requirement Document

Hey team, we need to wire up a new adapter for that WebDAV remote storage integration we've been talking about. Basically the idea is that other devs can just hand us some raw server responses and configuration blobs and we spit out clean, predictable text output they can parse easily — no XML wrangling on their end. Think of it like that 'compatibility normalization layer' approach we did for the login module a while back, same kind of neutral output style.

The big pain points we keep hearing: people are frustrated when quota info just silently disappears on certain servers instead of getting a clear signal that it's unsupported. Also, folks building directory browsers are confused about when something is a folder vs a file because the raw protocol data is inconsistent across servers. And connection setup keeps tripping people up — timeouts get ignored, root paths aren't applied, the whole thing just feels brittle.

We also need proper handling for custom metadata properties (the namespace/name/value things), XML generation for protocol requests, and a consistent way to surface errors so frontend devs aren't parsing stack traces.

One thing I'm not sure about — how exactly should the XML declaration be formatted? I think there's a specific encoding format we settled on somewhere. Also the default timeout value, I forget what we landed on. Can someone check the original spec?

This should be multi-file, cleanly separated — not one giant script please.