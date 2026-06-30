## Product Requirement Document

We need a service layer for our desktop software management application that lets the UI query, install, remove, update, and inspect both traditional system packages and sandboxed applications — without ever talking to the underlying system daemons directly. The service must expose a clean set of asynchronous calls and observable streams so each screen just subscribes to lifecycle state, progress, and metadata signals.

For package metadata, the service should retrieve a package's one-line summary, homepage, license, raw disk size, and long description. The disk size must be automatically converted to a human-friendly format (using binary units like KB, MB, GB, with two decimal places), similar to how our existing size-formatting helper works elsewhere in the codebase — please handle it the same way as the common utilities module does.

Package operations (install and remove) need to emit a busy/idle lifecycle state at start and end, plus progress values as the operation runs. Notably, removal progress should be reported as remaining work rather than work done, so a progress bar can drain toward zero.

For sandboxed applications, the service must support looking up an app by name (returning null gracefully when not found), free-text search with an early-exit for empty queries, listing per-app interface connection points with their connection status (filtering out system-owned and content-type plugs — follow the same filtering logic as the plugs loader in the snap service), and checking whether an operation is currently in flight for a given app.

Update management must include a check-and-notify flow: run a refresh that transitions through checking and settles at no-updates or ready-to-update, and send a desktop notification only when the system is actually ready to install updates.

Both back-ends must be injected abstractions so all logic can be tested with in-memory doubles.