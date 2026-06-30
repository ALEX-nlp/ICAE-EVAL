## Product Requirement Document

Hey team, we need to build out the automation driver wrapper we've been talking about for the mobile QA platform. Basically right now every time someone wants to run a test session they have to hand-roll a bunch of device setup stuff — figuring out if the session config even makes sense, doing the touch math, flipping network radios, picking the right device, all that. It's a mess and people keep getting it wrong in slightly different ways each time.

The core thing we need is a clean interface that handles all of this internally so test engineers just describe what they want and the driver figures out the rest. Think of it like that capability-checking pattern we used in the login compatibility module — same idea but for device sessions.

Specifically we're getting bug reports about: sessions starting with broken configs and only failing halfway through, gesture coordinates being off especially on drags, network state getting out of sync, locale changes not sticking after device restart, and people not knowing which automation context they're in when switching between native and web views.

Also the ops team is complaining that teardown leaves devices in weird states — keyboards not restored, apps still running, that kind of thing. We need deterministic cleanup.

Output from this thing needs to be totally plain and parseable — no exception class names or runtime garbage in the output, just clean key=value lines. Can someone own this and make sure it handles all the edge cases properly?