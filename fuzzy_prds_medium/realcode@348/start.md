## Product Requirement Document

Hey team, we need to build out that deployment automation toolkit we've been discussing. The core idea is that right now our devs are spending way too much time manually typing out server lists, copy-pasting SSH flags, and debugging why staging got the wrong config values because someone forgot to update a placeholder. It's causing real pain especially around release days.

Basically the tool should let you write something compact like `h[1:20]` instead of listing 20 hostnames, load an inventory file that can have reusable template blocks (the hidden/dot-prefixed ones shouldn't show up in output), and spit out the right SSH connection strings automatically. We also want filtering so you can say 'only run this on prod servers' or 'skip frontend tier'.

Config-wise, it should handle the inheritance thing we talked about — child hosts should be able to pull values from parent scope, and if a parent has a placeholder like `{{name}}` in a path, each child should fill that in with their own name. Also need array config merging but it should scream if you try to append to something that isn't a list.

Finally, task planning — similar to how we handled the hook ordering in that pipeline module a while back — before/after hooks around grouped task expansion, with a clean error if someone references a task that doesn't exist.

We need a test harness that can run against the case files automatically. Python is preferred.

One extra pass on the details the team asked about: for host range expansion, if the bracketed range is zero-padded like `[01:20]`, we need to keep that padding all the way through the generated names, so `01`, `02`, … `09`, `10`, … `20`. The width comes from the length of the start value string, so we shouldn't normalize or strip it during expansion.

Also on inventory loading, any entry whose alias/key starts with `.` is template-only and should stay fully out of the visible host list and all emitted output, even though it can still be used through YAML merge keys like `<<: *anchor` by visible entries. That's the same behavior we want in Feature 1.2 where those dot-prefixed entries are basically reusable anchor templates merged into real hosts.

A couple output formatting specifics too: if a host field is a list/array like `roles`, print it as a compact JSON array string, for example `host.foo.roles=["a","b","c"]`. Regular scalar strings still print as-is, and if `roles` happens to just be a plain scalar string instead of a list, then it should stay a plain string value. For host type, if a host entry has a `local` key at all, no matter what the value is, that host should come out as `type=local`. Every other visible host is `type=remote`, and local hosts should not get `ssh_arguments` output.

For SSH rendering, the order needs to be strict: first bare sshFlags with no value, then forward_agent as `-A` when true, then valued sshFlags as `flag value`, then `-p port`, then `-F config_file`, then `-i identity_file`, then `-o Key=Value` for each sshOptions entry. One subtle point there: if `ssh_multiplexing` is false, we still emit `-A` when `forward_agent` is true, and `ssh_multiplexing` by itself does not add any flag.

On the task planning side, for Feature 5 the before/after hook declarations should expand recursively around grouped task members, matching the `TaskPlanner` domain logic and the behavior shown in `feature5_1_task_execution_plan.json`.

And for the harness, the expected entry point is `bash rcb_tests/test.sh`, with an optional `--cases-dir <subdir>` and default `test_cases`. For each case file and case index, it writes actual output to `rcb_tests/stdout/<cases-dir>/<filename_stem>@<zero_padded_3_digit_index>.txt`, for example `rcb_tests/stdout/public_test_cases/feature1_1_host_range_expansion@000.txt`, and then compares actual vs expected and reports pass/fail per case.

A few exact details to be precise about: The test harness is invoked via `bash rcb_tests/test.sh` and accepts `--cases-dir <subdir>` (default `test_cases`). For each case file and case index, it writes actual output to `rcb_tests/stdout/<cases-dir>/<filename_stem>@<zero_padded_3_digit_index>.txt` (e.g., `rcb_tests/stdout/public_test_cases/feature1_1_host_range_expansion@000.txt`). The script compares actual vs expected output and reports pass/fail per case.