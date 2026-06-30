## Product Requirement Document

Hey team, we need to build out this spell-checking tool for source code that we talked about in the last planning session. The big complaint from devs is that existing spell checkers are totally useless on code — they flag every identifier, URL, hex code, whatever, as a misspelling and people just turn them off. We need something smarter.

Basically it should be able to break apart compound names (like the camelCase stuff, underscored names, etc.) into real words before checking, and it should know to skip over technical garbage like URLs and email addresses and file paths. It also needs to actually understand code structure for different languages — so it only checks the parts humans wrote as words, not keywords and operators and all that.

There should be a way to get spelling suggestions for bad words, and the end-to-end check should support some kind of override list so teams can whitelist their own domain terms. Also teams sometimes have naming conventions that look like misspellings — there should be a way to define patterns to skip those too.

For the architecture, we want this structured properly — not one giant file. Think about how we did the config layering on the auth module last quarter, similar vibe for extensibility. The I/O adapter should be totally separate from the core logic. Output should be byte-accurate positions so editors can use it directly.