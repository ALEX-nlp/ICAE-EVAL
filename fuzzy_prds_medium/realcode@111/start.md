## Product Requirement Document

Hey team, we need to wire up a new adapter for that WebDAV remote storage integration we've been talking about. Basically the idea is that other devs can just hand us some raw server responses and configuration blobs and we spit out clean, predictable text output they can parse easily — no XML wrangling on their end. Think of it like that 'compatibility normalization layer' approach we did for the login module a while back, same kind of neutral output style.

The big pain points we keep hearing: people are frustrated when quota info just silently disappears on certain servers instead of getting a clear signal that it's unsupported. Also, folks building directory browsers are confused about when something is a folder vs a file because the raw protocol data is inconsistent across servers. And connection setup keeps tripping people up — timeouts get ignored, root paths aren't applied, the whole thing just feels brittle.

We also need proper handling for custom metadata properties (the namespace/name/value things), XML generation for protocol requests, and a consistent way to surface errors so frontend devs aren't parsing stack traces.

One thing I'm not sure about — how exactly should the XML declaration be formatted? I think there's a specific encoding format we settled on somewhere. Also the default timeout value, I forget what we landed on. Can someone check the original spec?

This should be multi-file, cleanly separated — not one giant script please.

Quick follow-up after the questions that came in: the default timeout we were trying to remember is 30 seconds, so if the user doesn’t provide one we should show that in the validated connection settings output as `timeout=30`. And on the XML declaration, the format is `<?xml version='1.0' encoding='UTF-8'?>` everywhere we generate XML — quota request XML, property request XML, and any other serialized XML output. Keep the single quotes exactly like that.

Also, for quota handling, if a WebDAV server doesn’t return quota properties, we should not throw or just return nothing. It needs to come back as a normalized error record using the neutral `error=` style, with the category `operation_not_supported` or the same kind of unsupported-operation signal. That should fit the same flat newline-delimited key=value stdout format used for all adapter outputs, where errors use `error=<category>` prefix lines followed by structured field lines — as specified in the PRD's 'Expected Behavior / Usage' sections and demonstrated in feature7_1_exception_rendering.json test cases.

On the file vs folder confusion, the rule is: treat a resource as a directory when its `resourcetype` element contains a `collection` child element in the DAV namespace. If `resourcetype` is empty, whether self-closing or just no children, that means file. For listing entries the output should be `is_directory=true` or `is_directory=false`, and for metadata records it should be `isdir=true` or `isdir=false`.

One more detail for custom properties: when building a property lookup or property update XML body, if a namespace is provided it needs to show up as an `xmlns` attribute on the property element itself, for example `<aProperty xmlns="test"/>`. If no namespace is provided, we still want the attribute there, just empty as `xmlns=""`.