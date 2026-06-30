## Product Requirement Document

Hey team, we need to build out our error reporting client library. The core idea is that devs drop this into their app and it handles all the messy stuff — capturing errors, cleaning up sensitive data before it goes out, keeping a running log of what happened leading up to a crash, and shipping the report off to the right place depending on whether we're talking browser or server context.

One thing that burned us before (remember that login module incident?) is we kept leaking things like passwords and tokens in query strings and form data. So redaction needs to be really solid — both in URLs and in nested object data. Same substring-match approach we've used elsewhere.

We also had issues with deeply recursive objects crashing the serializer, so there needs to be some kind of depth-limiting safety net.

For the browser side, we need to hook into the global error surfaces and make sure cross-origin noise doesn't spam us. The server side needs clean HTTP delivery with proper callbacks.

Also — and this is the one people keep forgetting — we shouldn't be firing off reports in local dev environments unless someone has explicitly said they want that. We've had too many dev machines polluting production dashboards.

Middleware integration should clear per-request state cleanly and forward errors down the chain. The breadcrumb trail should cap out at a reasonable size so memory doesn't balloon. Can someone own this end to end?