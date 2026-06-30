## Product Requirement Document

Hey team, we need a small notification dispatch library for our CI pipelines. Right now every job is basically copy-pasting the same messy logic to push messages into our chat workspace and it's causing all sorts of broken messages — especially when branch names or PR titles have weird characters in them. Someone's PR title had angle brackets last week and completely blew up the channel message lol.

The library should handle rendering text safely for the chat workspace (similar to what we did in the old Jenkins integration, you can check that codebase for reference), putting together a standard 'build started' line, and actually sending the message to one or more channels without the job having to know anything about HTTP or auth tokens.

On the delivery side, people sometimes want to blast the same notification to a whole list of rooms at once — the channel field might have multiple targets in it separated by different delimiters, so we need to handle that gracefully. We also have two different ways we send messages depending on the credential type (the webhook path vs the newer bot account method), and those need to route to totally different upstream URLs with different query parameters.

Also there's a custom message feature where users can override the notification text per build outcome — we just need a quick utility to check whether any of those slots have actually been filled in before we bother appending them.

Please keep the code clean and modular, not one giant file.