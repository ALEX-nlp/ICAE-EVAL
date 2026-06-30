## Product Requirement Document

Hey team, we need to wrap up the speech coordinator work we've been scoping out. The gist is: we want a clean interface that handles the whole lifecycle of a voice recognition session — starting it up, feeding it audio events from the underlying platform, and shutting it down gracefully. Think of it like that channel-wrapper pattern we used in the notification module a while back, but for speech.

The tricky parts are around state management: the coordinator should know whether it's been set up yet, whether it's actively listening, and it should track the last thing it heard plus some basic audio level info. We also need it to handle errors smartly — some errors are 'just retry' situations and others are 'something is broken, stop everything' situations, and the behavior when a session is already cancelled is a bit nuanced (the team had opinions about this in the last standup).

There's also a locale/language selection piece — the platform hands us a raw list and we need to parse it into something usable, sorted in a sensible way for display, but the 'default' choice follows a different rule than the display order.

Please make sure the value objects (transcription candidates, results, errors) all support proper equality checks and can round-trip through the wire format. The confidence scoring logic has a special case for when the platform doesn't give us a score at all — make sure that edge case is handled consistently everywhere.