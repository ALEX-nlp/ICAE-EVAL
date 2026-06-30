## Product Requirement Document

Hey team, we need to build out that native extension helper tool we've been talking about. The idea is that devs shouldn't have to hand-roll all the platform detection and binary naming stuff every time they set up a new native extension project. It's the same pain every time — figuring out what to call the .so or .dll, where to put it, how to name the archive for CI uploads, all of that.

Basically the tool should handle the full lifecycle: figure out the right names for compiled artifacts based on the platform, run the build tool if it's there (but don't blow up if it isn't, similar to how we handled the optional-tool pattern in the login module refactor), package up the result, and optionally pull down a prebuilt binary from a release feed or a custom URL so people don't have to compile locally.

The output needs to be automation-friendly — key=value lines, one per thing, easy to parse in shell scripts or CI steps. Each 'command' maps to a specific concern.

We also want debug logging that can be toggled via a file destination — if no destination is set it should just be silent. Oh and the archive pack/unpack needs to actually round-trip correctly, not just create the file.

I don't have all the exact field names nailed down yet so just check with me if something's unclear. The platform naming rules for shared libs are a bit specific — there's some Mac/Windows edge case logic that I know trips people up.