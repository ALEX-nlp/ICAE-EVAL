## Product Requirement Document

hey team, we need to get this email toolkit wrapped up for the transactional messaging service. basically devs are complaining they have to hand-wire everything themselves every time a new service needs to send emails — it's a mess and keeps breaking in prod when someone forgets a header or messes up an attachment. we want a clean library that handles building email objects, sticking files onto them, and rendering the body from templates without everyone having to learn a new engine from scratch each time.

the value objects need to blow up early if someone forgets something important — similar to how we handled the validation in that user-profile module, just make sure errors are specific enough that devs know exactly what they forgot. for images embedded in the body, there's a fixed set of supported kinds (check the existing catalog logic) and each one needs its mime type resolved automatically.

for templates we want to support a few different engines — the ftl one, a couple of html-based ones (there are at least three of those, one is the logic-less one, one does inheritance, and there's that natural-templating one). wrong extensions or blank names should fail clearly, and broken templates should also have their own distinct failure mode.

attachments should auto-detect content type from actual bytes when no type is given explicitly. the whole thing should be modular — no god files. prioritize getting the test harness wired up so we can validate everything end to end.