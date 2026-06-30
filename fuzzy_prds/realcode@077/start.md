## Product Requirement Document

Hey team, we need to build out that catalog runtime thing we talked about last sprint. Basically devs should be able to register their resources and tools once and have clients discover and call them without writing all the boilerplate themselves. Think of it like that registry pattern we used in the notification service — same idea but for resources and callable operations.

Right now without this, every team is hand-rolling their own listing logic, pagination, URI matching, and error handling, and it's all inconsistent. Clients can't reliably figure out what's available or how to call it.

The listing endpoints need to support paging — we had some complaints from the mobile team about large catalogs being unwieldy. Also the URI matching for the dynamic ones needs to pull out path variables and use them to render content, similar to how the old routing layer worked.

For the callable operations side, inputs need to have machine-readable type info attached — nested objects and arrays included — and we should be validating required fields before anything gets invoked. If something's wrong with a registration or a call, we want a clean normalized error shape, not a stack trace.

One thing I keep forgetting to mention: the cursor for paging should work the way we agreed with the frontend team. And make sure the MIME type defaulting follows the same rule we established for static content. Reach out if unclear.