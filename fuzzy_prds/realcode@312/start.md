## Product Requirement Document

Hey team, we need to build out that RPC server wrapper thing we discussed last sprint. The basic idea is: clients send requests in that standard JSON-based RPC format (you know the one, 2.0 spec), and our server needs to route them to the right backend operation and send back a properly shaped response. We also need it to work over plain byte streams AND HTTP — the HTTP side needs to return the right status codes depending on what happened (the usual suspects: success, not found, bad input, server error, etc.).

One thing that tripped us up with the old login module compatibility logic — make sure whatever dispatch mechanism we use handles methods that have the same name but different argument signatures. Clients might also send a whole bundle of requests at once in one shot, and we need to handle that gracefully.

Also critical: when backend services blow up, we absolutely cannot leak any internal Java class names or stack traces back to the client. Map errors to clean numeric codes only.

There's also a testing shim/adapter we need — something that reads a single JSON blob from stdin describing the scenario, runs the engine, and prints out a normalized line-by-line view of the result to stdout so our CI pipeline can diff it. The adapter needs to support a flag that lets callers say 'I know I'm sending extra/fewer args than expected, that's fine.' Refer to the existing parameter flexibility logic we discussed for details on how permissive mode should work.