## Product Requirement Document

Hey team, we need to build out that deployment automation toolkit we've been discussing. The core idea is that right now our devs are spending way too much time manually typing out server lists, copy-pasting SSH flags, and debugging why staging got the wrong config values because someone forgot to update a placeholder. It's causing real pain especially around release days.

Basically the tool should let you write something compact like `h[1:20]` instead of listing 20 hostnames, load an inventory file that can have reusable template blocks (the hidden/dot-prefixed ones shouldn't show up in output), and spit out the right SSH connection strings automatically. We also want filtering so you can say 'only run this on prod servers' or 'skip frontend tier'.

Config-wise, it should handle the inheritance thing we talked about — child hosts should be able to pull values from parent scope, and if a parent has a placeholder like `{{name}}` in a path, each child should fill that in with their own name. Also need array config merging but it should scream if you try to append to something that isn't a list.

Finally, task planning — similar to how we handled the hook ordering in that pipeline module a while back — before/after hooks around grouped task expansion, with a clean error if someone references a task that doesn't exist.

We need a test harness that can run against the case files automatically. Python is preferred.