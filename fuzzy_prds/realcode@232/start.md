## Product Requirement Document

Hey team, we need a serialization library for the foreground service config stuff. Basically devs are hand-building those ugly flat maps for the native layer right now and keep getting the integer codes wrong, mixing up the Android vs iOS fields, and forgetting which keys the host expects. It's causing a bunch of subtle runtime bugs that are really hard to debug in the field.

The library should let you describe the notification setup and background task scheduling as proper typed objects, and then spit out the exact wire map the native side needs. Think of it like how we handled the enum encoding in that background task module from before — same idea but for the full config payload.

We need to support Android channel config, iOS notification flags, task scheduling with the repeat event stuff, icon with color, action buttons with colors, and then two composite request types: one for starting the service (platform-specific merge) and one for updating it (no channel fields, platform-independent). Colors should come out as a simple decimal string. Enum levels need to come out as their numeric codes — the exact mapping matters a lot here so please double-check those.

The core logic must stay decoupled from JSON parsing — that's a hard requirement from infra. Individual config pieces should each own their own serialization. Invalid input like empty channel IDs or unknown level strings should be rejected cleanly, not silently produce garbage output.