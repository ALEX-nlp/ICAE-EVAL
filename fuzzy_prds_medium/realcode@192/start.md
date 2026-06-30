## Product Requirement Document

Hey team, we need a small notification dispatch library for our CI pipelines. Right now every job is basically copy-pasting the same messy logic to push messages into our chat workspace and it's causing all sorts of broken messages — especially when branch names or PR titles have weird characters in them. Someone's PR title had angle brackets last week and completely blew up the channel message lol.

The library should handle rendering text safely for the chat workspace (similar to what we did in the old Jenkins integration, you can check that codebase for reference), putting together a standard 'build started' line, and actually sending the message to one or more channels without the job having to know anything about HTTP or auth tokens.

On the delivery side, people sometimes want to blast the same notification to a whole list of rooms at once — the channel field might have multiple targets in it separated by different delimiters, so we need to handle that gracefully. We also have two different ways we send messages depending on the credential type (the webhook path vs the newer bot account method), and those need to route to totally different upstream URLs with different query parameters.

Also there's a custom message feature where users can override the notification text per build outcome — we just need a quick utility to check whether any of those slots have actually been filled in before we bother appending them.

Please keep the code clean and modular, not one giant file.

Quick follow-up from the questions that came in: for the text escaping bit, if we get an HTML anchor like `<a href='URL'>LABEL</a>`, we should first turn that into the workspace-style inline link `<URL|LABEL>`. Important detail there: the quote characters around the URL are kept exactly as written, so single or double quotes stay in the output. That anchor conversion happens BEFORE we do the reserved-character encoding. After that, we only entity-encode exactly three characters: `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`. Everything else passes through unchanged, including `%`, `{`, `}`, `#`, and spaces. Also, only actual anchors get collapsed this way — non-anchor angle-bracket text like `<b>` should not be treated as a link and just ends up with the brackets encoded literally.

Also confirming the standard start line format is exactly `<project_name> - <escaped_build_name> `, including that single trailing space at the end. The project name is NOT escaped; only the build name goes through the escaper. Empty names are totally valid here, so if both inputs are empty the output should be ` -  `.

For channel fan-out, split the channel string on commas, semicolons, and spaces, in any combination, and fire one HTTP request per named channel. One slightly weird but intentional edge case: an empty channel string still produces exactly one request to an empty target, it does NOT produce zero requests. And in webhook mode, the URL is `https://<team_domain>.slack.com/services/hooks/jenkins-ci?token=<token>`. That same URL is reused for every channel in a multi-channel send, so the channel name does not show up in the webhook URL at all.

Last thing, the escaping behavior should stay aligned with the Slack/Jenkins plugin conventions we’ve already been referencing — specifically the `<URL|LABEL>` inline-link syntax from Slack’s formatting dialect, plus the fact that only the three reserved characters `&`, `<`, `>` need entity-encoding per Slack’s API docs.