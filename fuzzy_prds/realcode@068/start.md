## Product Requirement Document

Hey team, we need to build out that secret mount adapter thing we talked about last sprint. The basic idea is: drivers pass in a big messy parameter map and we need to make sense of it — pull out the connection stuff, the pod identity bits, the secret descriptors (those are in that weird YAML-ish inline format, same pattern as the old CSI objects spec). We also need to validate it properly and give back clean neutral error codes, not raw exception dumps.

On top of that we need to handle the actual secret fetching — normalize the paths, pick the right HTTP method, encode body args when present. There's also a value extraction step where we pull a specific key out of the response, and it needs to handle both flat and nested response shapes.

The caching behavior is important too — same provider instance should reuse what it already fetched, but a fresh instance should go back to the source. We also need to wire up the connection settings resolution (env vars, flags, mount params — same precedence order we used in the auth module last time) and a version metadata endpoint.

Outputs should all be key=value lines except the version one which is JSON. File permissions need to come out as decimal. Please keep the core logic totally separate from the I/O layer, we've been burned by that before.