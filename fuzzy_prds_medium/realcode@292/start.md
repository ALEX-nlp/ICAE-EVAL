## Product Requirement Document

We need a service layer for our desktop software management application that lets the UI query, install, remove, update, and inspect both traditional system packages and sandboxed applications — without ever talking to the underlying system daemons directly. The service must expose a clean set of asynchronous calls and observable streams so each screen just subscribes to lifecycle state, progress, and metadata signals.

For package metadata, the service should retrieve a package's one-line summary, homepage, license, raw disk size, and long description. The disk size must be automatically converted to a human-friendly format (using binary units like KB, MB, GB, with two decimal places), similar to how our existing size-formatting helper works elsewhere in the codebase — please handle it the same way as the common utilities module does.

Package operations (install and remove) need to emit a busy/idle lifecycle state at start and end, plus progress values as the operation runs. Notably, removal progress should be reported as remaining work rather than work done, so a progress bar can drain toward zero.

For sandboxed applications, the service must support looking up an app by name (returning null gracefully when not found), free-text search with an early-exit for empty queries, listing per-app interface connection points with their connection status (filtering out system-owned and content-type plugs — follow the same filtering logic as the plugs loader in the snap service), and checking whether an operation is currently in flight for a given app.

Update management must include a check-and-notify flow: run a refresh that transitions through checking and settles at no-updates or ready-to-update, and send a desktop notification only when the system is actually ready to install updates.

Both back-ends must be injected abstractions so all logic can be tested with in-memory doubles.

A couple extra specifics from the team’s questions. For disk size, this should match the behavior of formatBytes in golden/lib/store_app/common/utils.dart. It’s 1024-based binary units, picks the largest fitting unit from ['B','KB','MB','GB','TB','PB','EB','ZB','YB'], always uses exactly 2 decimal places, and always includes a single space before the unit. So 43008 bytes becomes '42.00 KB' and 1572864 bytes becomes '1.50 MB'. If bytes <= 0, the result is '0 B'.

Also, the package lifecycle state is intentionally very small: the enum has exactly two values, 'processing' and 'ready'. During both install and remove, emit 'processing' at the start and 'ready' at the end, and those are the only two values we should ever use here. When we print or collect operation output, keep it grouped by observable channel in this exact order: first all lifecycle state lines, which means 'state=processing' then 'state=ready', then the activity info line, so either 'info=installing' or 'info=removing', and then all progress lines in sequence order as 'progress=<value>'. The channels are collected independently and printed as three grouped blocks.

On progress, install just forwards percentages unchanged. Remove is the inverted one: each raw back-end progress percentage is converted with reported_value = 100 - backend_percentage. So a backend value of 27 is reported as 73, 72 as 28, and 100 as 0.

One more detail on package ID search: findPackageKitPackageIds caps results at 20 by doing ids.take(20).toList() before returning. It also uses a synchronized lock so at most one search transaction runs at a time, and it cancels any pending search transaction before starting a new one.

For updates, the enum has four values and we should use the exact strings 'checkingForUpdates', 'noUpdates', 'updating', 'readyToUpdate'. If a refresh finds no pending updates, the sequence is checkingForUpdates then noUpdates. If updates are found, it settles at readyToUpdate.