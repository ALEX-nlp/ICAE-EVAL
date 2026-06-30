## Product Requirement Document

Hey team, we need to build out that catalog runtime thing we talked about last sprint. Basically devs should be able to register their resources and tools once and have clients discover and call them without writing all the boilerplate themselves. Think of it like that registry pattern we used in the notification service — same idea but for resources and callable operations.

Right now without this, every team is hand-rolling their own listing logic, pagination, URI matching, and error handling, and it's all inconsistent. Clients can't reliably figure out what's available or how to call it.

The listing endpoints need to support paging — we had some complaints from the mobile team about large catalogs being unwieldy. Also the URI matching for the dynamic ones needs to pull out path variables and use them to render content, similar to how the old routing layer worked.

For the callable operations side, inputs need to have machine-readable type info attached — nested objects and arrays included — and we should be validating required fields before anything gets invoked. If something's wrong with a registration or a call, we want a clean normalized error shape, not a stack trace.

One thing I keep forgetting to mention: the cursor for paging should work the way we agreed with the frontend team. And make sure the MIME type defaulting follows the same rule we established for static content. Reach out if unclear.

Quick follow-up from the questions that came in: on the MIME type piece, when mimeType is absent from a resource or resource template definition, it defaults to 'text/plain'. Same rule if no MIME type is explicitly provided for a static resource or resource template. That applies in both listing and reading responses, and it needs to show up in the mimeType field of every resource entry.

On paging, the cursor is a decimal string representing the integer offset (index) into the registration-ordered list, or said another way a decimal string encoding the integer start index into the registration-ordered list. So if page_size is 5 and you're on the first page, nextCursor is '5'. nextCursor equals the start index of the next page and is only included when more items remain beyond the current page. If the full remaining set fits in the page or no page_size is given, nextCursor must NOT appear in the response.

Also wanted to be explicit about read misses and template reads. If a read request hits a URI that matches neither a static resource nor a template, return a JSON object with exactly two fields: 'error' set to the string 'resource_not_found', and 'uri' set to the requested URI string. No other fields should appear. For resource templates, the uri_template uses {variable_name} placeholders. When a concrete URI is read, the runtime matches it against registered templates, extracts the path variable values by position, then substitutes them into the text_format string using the same {variable_name} syntax to produce the rendered text content. The response uses the concrete URI, not the template URI.

Last thing, a couple validations need to happen up front when the catalog is built. If a static resource is registered with a null or empty string URI, the catalog build must fail immediately and return a JSON error object with a single field: 'error' set to 'invalid_resource_uri'. Same idea for tools: a null tool name must return 'error': 'invalid_tool_name'. These happen at build time, not during list, read, or call.