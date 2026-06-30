## Product Requirement Document

Hey team, we need to build out the core plumbing for our isomorphic component framework. This is similar to what we did for the old routing layer on the dashboard project — same general idea, just applied here more broadly across naming, URL handling, cookies, and the server-side action API.

Basically the framework needs to know how to turn a component's name into a tag and back again, handle camelCase normalization with optional prefixes (you'll know what I mean when you look at how identifiers flow through the system), match incoming URLs to application state across named 'buckets', parse and write cookies, and generate a small inline script that the browser can run to replay whatever the server decided to do (redirects, cookie writes, etc.).

There's also a method-lookup pattern — refer to how we resolved handlers on that earlier module API — where you try the specific named method first, then fall back to a generic one, then to a no-op. The no-op behavior is subtle and has caused bugs before so please be careful there.

We also need an event bus wired into the API provider with the usual on/once/off/emit, but validation needs to be strict — wrong types should surface as named error categories, not raw exceptions.

Please keep everything well-separated by concern, nothing monolithic. Ping me if anything in the routing parameter syntax is unclear, it's a bit custom.