## Product Requirement Document

Hey team, we need to build out the automation driver wrapper we've been talking about for the mobile QA platform. Basically right now every time someone wants to run a test session they have to hand-roll a bunch of device setup stuff — figuring out if the session config even makes sense, doing the touch math, flipping network radios, picking the right device, all that. It's a mess and people keep getting it wrong in slightly different ways each time.

The core thing we need is a clean interface that handles all of this internally so test engineers just describe what they want and the driver figures out the rest. Think of it like that capability-checking pattern we used in the login compatibility module — same idea but for device sessions.

Specifically we're getting bug reports about: sessions starting with broken configs and only failing halfway through, gesture coordinates being off especially on drags, network state getting out of sync, locale changes not sticking after device restart, and people not knowing which automation context they're in when switching between native and web views.

Also the ops team is complaining that teardown leaves devices in weird states — keyboards not restored, apps still running, that kind of thing. We need deterministic cleanup.

Output from this thing needs to be totally plain and parseable — no exception class names or runtime garbage in the output, just clean key=value lines. Can someone own this and make sure it handles all the edge cases properly?

One more pass on the details the team asked about. For session config validation, a capability set is only good if it names at least one launch target through app, appPackage, or browserName. The platform name match should be case-insensitive. If there’s no launch target at all, return error=missing_required_capability and required=app_or_package_or_browser. If someone names a browser we don’t support, return error=unsupported_browser plus the bad browser value. If both app and browserName are set at the same time, return error=conflicting_capabilities and conflict=app_and_browser. If it all checks out, just output valid=true.

On the proxying side, the avoid list is exactly 8 entries and the order matters: POST ^/session/[^/]+/context, GET ^/session/[^/]+/context, POST ^/session/[^/]+/appium, GET ^/session/[^/]+/appium, POST ^/session/[^/]+/touch/perform, POST ^/session/[^/]+/touch/multi/perform, POST ^/session/[^/]+/orientation, GET ^/session/[^/]+/orientation. Each one should come out as avoid_route method=<METHOD> pattern=<REGEX>. Also, until an external web engine is attached, proxy_active=false.

For cleanup of config objects, only strip properties whose value is null or undefined. Keep falsy-but-defined stuff like false and 0. The output here should be remaining_keys as a comma-separated list in original order, and key_count as the integer count of remaining properties.

For contexts, NATIVE_APP always comes first. If the session is targeting an in-app web engine browser like Chrome, also include CHROMIUM. Otherwise, append whatever web views the device actually reports. Output stays contexts=<comma-separated list>.

For teardown, if alreadyShutDown is true, emit already_shut_down=true and stop right there. Otherwise, if unicodeKeyboard and resetKeyboard are both true and we recorded a defaultIME, restore that first as device_op=set_ime value=<ime>. After that it is always device_op=force_stop, then device_op=go_to_home, and if fullReset is true, add device_op=uninstall_apk at the end. That order is fixed.

For the Java version parser, it just scans the raw banner text for a line with a Java or OpenJDK version banner and pulls the version token from inside the quotes. If we recognize it, output java_version=<version>. If not, output error=java_version_unavailable. Still no exception-y host language noise in the output.

For gesture command naming, when swipe, flick, or drag is tied to a specific element, the resolved name is element:<gesture>, like element:swipe. If it isn’t tied to an element, use the plain command name like swipe. Output is command=<resolved_name>.

And on the touch math, moveTo is relative to the running position, not absolute. So if we’re currently at (100,101) and a moveTo says x=50, y=51, the resolved position is (150,152). If the next moveTo is x=-40, y=-41, that resolves to (110,111). A wait action carries forward the current running position and emits x and y, and a release action emits no coordinates at all. Also calling out that we still need the drag duration behavior with API-level-dependent minimums covered alongside the relative moveTo behavior.