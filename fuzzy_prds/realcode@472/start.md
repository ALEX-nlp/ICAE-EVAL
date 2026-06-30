## Product Requirement Document

hey team, we need to get the tokenized research project registry service shipped. basically the idea is researchers can register their IP-backed projects and get a full workspace spun up automatically — like accounts, a place to store files with versioning, and a feed for updates/announcements. all through one API surface so devs don't have to wire everything together themselves.

the tricky parts we keep forgetting to spec out properly: when two teams try to register the same project (or reuse a symbol someone else already claimed), we need to handle that gracefully — not just blow up. also the enable/disable flow from that lifecycle module we built before should behave the same way here (you know, the idempotency stuff and the different error messages depending on whether the project ever existed vs just currently inactive).

for files, people need to upload with all the metadata — the encryption stuff, categories, tags, access levels, etc — and get proper versioning automatically. announcements need to validate that any attached files actually exist before accepting the post.

the code needs to be properly structured, not one giant file. separate the API layer, domain logic, storage abstractions. think about what happens when someone queries a project that's been disabled vs one that never existed — those should feel different to the caller.

check how we handled the conflict resolution and not-found vs no-history distinction in the existing login/account module for reference.