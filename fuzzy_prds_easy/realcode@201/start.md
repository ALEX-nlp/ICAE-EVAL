## Product Requirement Document

# Container Deployment Command Builder - Generating Docker & SSH Invocations from Declarative Config

## Project Goal

Build a library that turns a declarative deployment description (one service, an image, registry credentials, a set of servers grouped into roles, environment variables, healthchecks, logging, volumes, and SSH settings) into the exact shell command strings needed to deploy and operate that service with a container runtime over SSH. It lets developers describe *what* they want deployed once, and have every `docker ...` and `ssh ...` command derived deterministically, so they never hand-write or hand-escape these commands.

---

## Background & Problem

Without this library, operators deploy containerized applications by typing long, fragile `docker run`/`docker ps`/`docker logs` commands by hand and wrapping them in `ssh` invocations per host. These commands carry dozens of flags (restart policy, env injection, healthcheck, log rotation, routing labels, name/label filters), must be quoted and shell-escaped correctly, and must stay consistent across roles, destinations, and versions. Doing this manually is repetitive and error-prone: a missing label breaks routing, a mis-escaped secret leaks into logs, an off-by-one filter targets the wrong container.

With this library, the operator supplies a structured config object and asks for a named operation (run, start, stop, logs, remove, etc.) for a given role/version/destination. The library returns the precise command string, with all flags ordered, all values shell-escaped, secrets resolved from the host environment and redactable for safe logging, and SSH wrapping applied where remote execution is needed.

---

## Architecture & Engineering Constraints

To ensure this project is delivered as a maintainable software artifact, the following architectural and non-functional requirements (NFRs) MUST be strictly observed:

1. **Scale-Driven Code Organization:** This is a non-trivial domain (config resolution, role specialization, command building, SSH wrapping, secret redaction). It MUST NOT be a single "god file". Provide a clear multi-file structure separating configuration/role resolution, command building, shell-escaping/redaction utilities, and the execution adapter.

2. **Strict Separation of Concerns (Anti-Overfitting):** The JSON input/output cases below are a **black-box contract** for the execution adapter, NOT the internal data model. Core logic must not know about JSON or stdin/stdout. The adapter translates a JSON command into idiomatic calls on the core and renders the result.

3. **Adherence to SOLID Design Principles:** Separate config resolution, role specialization, command formatting, escaping/redaction, and output rendering into distinct cohesive units. The command builder should be open to new operations without modifying existing ones.

4. **Robustness & Interface Design:** The public interface must be idiomatic to the target language. Resolving a secret whose value is absent from the host environment is an error condition and must be modeled as such (a typed failure), not a silent empty value. The adapter renders such failures as a neutral category (e.g. `error=missing_env`).

---

## Core Features

### Feature 1: Launch a Long-Lived Application Container

**As a developer**, I want one declarative config to produce the full container run command, so I don't hand-assemble restart policy, env injection, healthcheck, logging, and routing flags.

**Expected Behavior / Usage:**

*1.1 Baseline run command — minimal config with one server and a secret env var*

Given a service name, an image, registry credentials, a single server, and a secret env var (whose value comes from the host environment), produce a detached run command. It always includes: `--detach`, `--restart unless-stopped`, a `--name` of the form `service-role-version`, an injected container-name env var, the resolved env vars, a default HTTP healthcheck hitting `/up` on port 3000 with a 1s interval, a default log-rotation option `max-size=10m`, the service/role labels, the web routing labels (see Feature 6), and finally the `repository:version` image reference. All values are shell-quoted.

**Test Cases:** `rcb_tests/public_test_cases/feature1_1_run_basic.json`

```json
{
    "description": "Generate the docker run command that launches a long-lived application container in detached mode. The base deployment defines a single service, image, registry credentials, one server, and a secret environment variable resolved from the host environment. The output is the full docker run invocation including restart policy, container name, injected environment variables, default HTTP healthcheck, default log rotation, and the standard service/role/routing labels.",
    "cases": [
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"},
                "version": "999",
                "role": "web",
                "action": "run"
            },
            "expected_output": "docker run --detach --restart unless-stopped --name app-web-999 -e MRSK_CONTAINER_NAME=\"app-web-999\" -e RAILS_MASTER_KEY=\"456\" --health-cmd \"curl -f http://localhost:3000/up || exit 1\" --health-interval \"1s\" --log-opt max-size=\"10m\" --label service=\"app\" --label role=\"web\" --label traefik.http.services.app-web.loadbalancer.server.scheme=\"http\" --label traefik.http.routers.app-web.rule=\"PathPrefix(\\`/\\`)\" --label traefik.http.middlewares.app-web-retry.retry.attempts=\"5\" --label traefik.http.middlewares.app-web-retry.retry.initialinterval=\"500ms\" --label traefik.http.routers.app-web.middlewares=\"app-web-retry@docker\" dhh/app:999"
        }
    ]
}
```

*1.2 Run with optional container features — volumes, healthcheck overrides, logging driver*

The same run command absorbs optional declarations: a bind-mount volume adds a `--volume` argument before the labels; a custom healthcheck `path` changes the URL in the default HTTP healthcheck; a custom healthcheck `cmd` replaces the whole healthcheck command; a role-scoped healthcheck `cmd` does the same for that role; and a logging declaration with a driver and options emits `--log-driver` plus one `--log-opt` per option (replacing the default `max-size=10m`). Each feature appears in its fixed argument position.

**Test Cases:** `rcb_tests/public_test_cases/feature1_2_run_options.json`

```json
{
    "description": "Generate the docker run command when the deployment declares extra container features: a bind-mount volume, a custom HTTP healthcheck path, a custom healthcheck shell command, a role-scoped healthcheck command, or a custom logging driver with options. Each input adds one feature to the base deployment and the output is the full docker run invocation reflecting that feature in the correct argument position.",
    "cases": [
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}, "volumes": ["/local/path:/container/path"]},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "run"
            },
            "expected_output": "docker run --detach --restart unless-stopped --name app-web-999 -e MRSK_CONTAINER_NAME=\"app-web-999\" -e RAILS_MASTER_KEY=\"456\" --health-cmd \"curl -f http://localhost:3000/up || exit 1\" --health-interval \"1s\" --log-opt max-size=\"10m\" --volume /local/path:/container/path --label service=\"app\" --label role=\"web\" --label traefik.http.services.app-web.loadbalancer.server.scheme=\"http\" --label traefik.http.routers.app-web.rule=\"PathPrefix(\\`/\\`)\" --label traefik.http.middlewares.app-web-retry.retry.attempts=\"5\" --label traefik.http.middlewares.app-web-retry.retry.initialinterval=\"500ms\" --label traefik.http.routers.app-web.middlewares=\"app-web-retry@docker\" dhh/app:999"
        },
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}, "healthcheck": {"path": "/healthz"}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "run"
            },
            "expected_output": "docker run --detach --restart unless-stopped --name app-web-999 -e MRSK_CONTAINER_NAME=\"app-web-999\" -e RAILS_MASTER_KEY=\"456\" --health-cmd \"curl -f http://localhost:3000/healthz || exit 1\" --health-interval \"1s\" --log-opt max-size=\"10m\" --label service=\"app\" --label role=\"web\" --label traefik.http.services.app-web.loadbalancer.server.scheme=\"http\" --label traefik.http.routers.app-web.rule=\"PathPrefix(\\`/\\`)\" --label traefik.http.middlewares.app-web-retry.retry.attempts=\"5\" --label traefik.http.middlewares.app-web-retry.retry.initialinterval=\"500ms\" --label traefik.http.routers.app-web.middlewares=\"app-web-retry@docker\" dhh/app:999"
        }
    ]
}
```

*1.3 Run for a non-web role with a custom command and raw options*

A role that is not web-routed declares its own host list, a startup command, and a map of raw container options. Its run command omits the HTTP healthcheck and the web routing labels, carries only the service/role labels, appends each raw option as a flag (a boolean-true value becomes a value-less flag), and appends the role's startup command after the image reference.

**Test Cases:** `rcb_tests/public_test_cases/feature1_3_run_custom_role_options.json`

```json
{
    "description": "Generate the docker run command for a non-web role that defines its own host list, a startup command, and extra raw container options. A non-web role does not receive the HTTP healthcheck or the web routing labels; instead it carries only service and role labels, its custom option flags, and appends its startup command after the image reference. Option values that are boolean-true become value-less flags.",
    "cases": [
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": {"web": ["1.1.1.1"], "jobs": {"hosts": ["1.1.1.2"], "cmd": "bin/jobs", "options": {"mount": "somewhere", "cap-add": true}}}, "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "jobs", "action": "run"
            },
            "expected_output": "docker run --detach --restart unless-stopped --name app-jobs-999 -e MRSK_CONTAINER_NAME=\"app-jobs-999\" -e RAILS_MASTER_KEY=\"456\" --log-opt max-size=\"10m\" --label service=\"app\" --label role=\"jobs\" --mount \"somewhere\" --cap-add dhh/app:999 bin/jobs"
        }
    ]
}
```

---

### Feature 2: Container Lifecycle Commands

**As a developer**, I want start/stop/info commands derived from the config, so lifecycle operations target exactly the right container by name or label.

**Expected Behavior / Usage:**

*2.1 Start by container name — name composition with optional destination*

Starting a container references it by the composed name `service-role-[destination-]version`. When a destination is configured it is inserted between role and version.

**Test Cases:** `rcb_tests/public_test_cases/feature2_1_start.json`

```json
{
    "description": "Generate the docker command that starts an already-created container by name. The container name is composed from service, role, optional destination, and version. When a destination is set it is inserted between role and version.",
    "cases": [
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "start"
            },
            "expected_output": "docker start app-web-999"
        },
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "destination": "staging", "role": "web", "action": "start"
            },
            "expected_output": "docker start app-web-staging-999"
        }
    ]
}
```

*2.2 Stop — latest running by label, optional grace timeout, or exact version*

By default stop finds the latest running container by service/role labels and pipes its id into a stop command. A configured graceful stop-wait-time appends a `-t <seconds>` timeout. Supplying an explicit version instead targets that exact container name.

**Test Cases:** `rcb_tests/public_test_cases/feature2_2_stop.json`

```json
{
    "description": "Generate the docker command that stops a running container. By default it finds the latest running container by service/role labels and pipes its id to docker stop. An optional graceful stop-wait-time appends a timeout flag. Supplying an explicit version instead targets the exact container name rather than the latest running one.",
    "cases": [
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "stop"
            },
            "expected_output": "docker ps --quiet --filter label=service=app --filter label=role=web --filter status=running --latest | xargs docker stop"
        },
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "stop", "args": {"version": "123"}
            },
            "expected_output": "docker container ls --all --filter name=^app-web-123$ --quiet | xargs docker stop"
        }
    ]
}
```

*2.3 Info — list containers by label with optional destination filter*

Info lists containers for the service/role. When a destination is configured a destination label filter is inserted between the service filter and the role filter.

**Test Cases:** `rcb_tests/public_test_cases/feature2_3_info.json`

```json
{
    "description": "Generate the docker ps command that lists containers for the service/role. When a destination is configured an extra destination label filter is inserted between the service filter and the role filter.",
    "cases": [
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "info"
            },
            "expected_output": "docker ps --filter label=service=app --filter label=role=web"
        },
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "destination": "staging", "role": "web", "action": "info"
            },
            "expected_output": "docker ps --filter label=service=app --filter label=destination=staging --filter label=role=web"
        }
    ]
}
```

---

### Feature 3: Log Inspection Commands

**As a developer**, I want to read and stream container logs through derived commands, so I can filter by time window, line count, and text without hand-writing pipelines.

**Expected Behavior / Usage:**

*3.1 Read logs — latest running container with optional since/tail/grep*

Logs finds the latest running container by label, pipes its id into a logs command with stderr merged (`2>&1`), and conditionally appends modifiers in a fixed order: a `--since` time window, a `--tail` line limit, then a `grep '<text>'` filter on the output.

**Test Cases:** `rcb_tests/public_test_cases/feature3_1_logs.json`

```json
{
    "description": "Generate the docker logs command for the latest running container, piping its id into docker logs with stderr merged into stdout. Optional modifiers append a since time window, a tail line limit, and a grep filter on the output. Each modifier is added in a fixed order: since, tail, then grep.",
    "cases": [
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "logs"
            },
            "expected_output": "docker ps --quiet --filter label=service=app --filter label=role=web --filter status=running --latest | xargs docker logs 2>&1"
        },
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "logs", "args": {"since": "5m"}
            },
            "expected_output": "docker ps --quiet --filter label=service=app --filter label=role=web --filter status=running --latest | xargs docker logs --since 5m 2>&1"
        },
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "logs", "args": {"grep": "my-id"}
            },
            "expected_output": "docker ps --quiet --filter label=service=app --filter label=role=web --filter status=running --latest | xargs docker logs 2>&1 | grep 'my-id'"
        }
    ]
}
```

*3.2 Follow logs over SSH — stream latest running container with optional grep*

Following logs builds a remote pipeline (find latest running container, tail its logs with timestamps in follow mode, stderr merged, optional grep) and wraps the whole single-quoted pipeline in an SSH invocation (with TTY) to the named host.

**Test Cases:** `rcb_tests/public_test_cases/feature3_2_follow_logs.json`

```json
{
    "description": "Generate the SSH-wrapped command to follow (stream) logs of the latest running container on a given host. The remote command finds the running container by service/role labels and tails its logs with timestamps in follow mode, stderr merged. An optional grep filter is appended to the remote pipeline. The whole remote pipeline is single-quoted and wrapped in an ssh invocation to the host.",
    "cases": [
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "follow_logs", "args": {"host": "app-1"}
            },
            "expected_output": "ssh -t root@app-1 'docker ps --quiet --filter label=service=app --filter label=role=web --filter status=running --latest | xargs docker logs --timestamps --tail 10 --follow 2>&1'"
        },
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "follow_logs", "args": {"host": "app-1", "grep": "Completed"}
            },
            "expected_output": "ssh -t root@app-1 'docker ps --quiet --filter label=service=app --filter label=role=web --filter status=running --latest | xargs docker logs --timestamps --tail 10 --follow 2>&1 | grep \"Completed\"'"
        }
    ]
}
```

---

### Feature 4: One-Off Command Execution

**As a developer**, I want to run ad-hoc commands either locally-targeted or wrapped over SSH, so I can execute maintenance tasks against fresh or existing containers.

**Expected Behavior / Usage:**

*4.1 Execute locally — fresh ephemeral container or existing container*

Two variants. A fresh ephemeral run uses `docker run --rm` with the injected environment and the absolute `repository:version` image, then appends the command. An existing-container exec uses `docker exec <container-name>` then appends the command.

**Test Cases:** `rcb_tests/public_test_cases/feature4_1_execute_local.json`

```json
{
    "description": "Generate docker commands that execute a one-off command against the application. Two variants: a fresh ephemeral container (docker run --rm) that injects the configured environment and uses the absolute image, then appends the command; and an existing container (docker exec) addressed by container name. The interactive variants are not requested here.",
    "cases": [
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "execute_in_new_container", "args": {"command": ["bin/rails", "db:setup"]}
            },
            "expected_output": "docker run --rm -e RAILS_MASTER_KEY=\"456\" dhh/app:999 bin/rails db:setup"
        },
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "execute_in_existing_container", "args": {"command": ["bin/rails", "db:setup"]}
            },
            "expected_output": "docker exec app-web-999 bin/rails db:setup"
        }
    ]
}
```

*4.2 Execute interactively over SSH — fresh or existing container with a TTY*

The interactive variants add `-it` to the docker command (fresh: `docker run -it --rm ...`; existing: `docker exec -it ...`), single-quote it, and wrap it in an `ssh -t` invocation to the host.

**Test Cases:** `rcb_tests/public_test_cases/feature4_2_execute_over_ssh.json`

```json
{
    "description": "Generate the SSH-wrapped interactive one-off command. Two variants: a fresh interactive container (docker run -it --rm) and an interactive exec into the existing container (docker exec -it). The docker command is single-quoted and wrapped in an ssh -t invocation to the target host.",
    "cases": [
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "execute_in_new_container_over_ssh", "args": {"command": ["bin/rails", "c"], "host": "app-1"}
            },
            "expected_output": "ssh -t root@app-1 'docker run -it --rm -e RAILS_MASTER_KEY=\"456\" dhh/app:999 bin/rails c'"
        },
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "execute_in_existing_container_over_ssh", "args": {"command": ["bin/rails", "c"], "host": "app-1"}
            },
            "expected_output": "ssh -t root@app-1 'docker exec -it app-web-999 bin/rails c'"
        }
    ]
}
```

*4.3 SSH wrapping — login user and jump-proxy resolution*

Any command can be wrapped for remote execution. The wrapper always uses a TTY and addresses the host as `user@host` with the command single-quoted. The login user defaults to `root` but is overridable. A configured proxy adds a jump host (`-J user@proxy`); the jump user defaults to `root` unless the proxy value already embeds a user. Login user and proxy resolve independently.

**Test Cases:** `rcb_tests/public_test_cases/feature4_3_run_over_ssh.json`

```json
{
    "description": "Wrap an arbitrary shell command for remote execution over SSH. The wrapper always uses a TTY and addresses the host as user@host with the command single-quoted. The login user defaults to root but can be overridden. A configured proxy adds an SSH jump host (-J user@proxy); the jump user defaults to root unless the proxy value already embeds a user. User and proxy options combine independently.",
    "cases": [
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "run_over_ssh", "args": {"command": "ls", "host": "1.1.1.1"}
            },
            "expected_output": "ssh -t root@1.1.1.1 'ls'"
        },
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}, "ssh": {"proxy": "2.2.2.2"}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "run_over_ssh", "args": {"command": "ls", "host": "1.1.1.1"}
            },
            "expected_output": "ssh -J root@2.2.2.2 -t root@1.1.1.1 'ls'"
        }
    ]
}
```

---

### Feature 5: Container & Image Discovery and Cleanup

**As a developer**, I want commands that locate, enumerate, and remove containers/images by label or name, so I can introspect deployed versions and prune old ones.

**Expected Behavior / Usage:**

*5.1 Locate containers — latest running id and exact-name lookup*

Find the latest running container id for the service/role (a destination inserts an extra destination filter). A name lookup builds a query matching an exact container name anchored with `^` and `$`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_1_container_id.json`

```json
{
    "description": "Generate docker ps queries that locate containers by label. current_running_container_id returns the id of the latest running container for the service/role; with a destination configured, a destination label filter is inserted. container_id_for builds a query that matches an exact container name anchored with ^ and $.",
    "cases": [
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "current_running_container_id"
            },
            "expected_output": "docker ps --quiet --filter label=service=app --filter label=role=web --filter status=running --latest"
        },
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "container_id_for", "args": {"container_name": "app-999"}
            },
            "expected_output": "docker container ls --all --filter name=^app-999$ --quiet"
        }
    ]
}
```

*5.2 Extract deployed versions — current running and full list*

Version queries format container names then extract the trailing dash-delimited segment (the version) via grep/cut. The current-version query restricts to the latest running container; the list query lists all versions and optionally accepts extra flags plus a status filter inserted before those flags.

**Test Cases:** `rcb_tests/public_test_cases/feature5_2_versions.json`

```json
{
    "description": "Generate docker ps pipelines that extract deployed version identifiers from container names. The pipeline formats names, then uses grep/cut to extract the trailing dash-delimited segment (the version). current_running_version restricts to the latest running container. list_versions lists all versions for the service/role and optionally accepts extra docker flags plus a status filter that is inserted before those flags.",
    "cases": [
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "current_running_version"
            },
            "expected_output": "docker ps --filter label=service=app --filter label=role=web --filter status=running --latest --format \"{{.Names}}\" | grep -oE \"\\-[^-]+$\" | cut -c 2-"
        },
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "list_versions"
            },
            "expected_output": "docker ps --filter label=service=app --filter label=role=web --format \"{{.Names}}\" | grep -oE \"\\-[^-]+$\" | cut -c 2-"
        }
    ]
}
```

*5.3 Enumerate containers — list all and list names*

List all containers (including stopped) by label filters; a destination inserts a destination filter. The names variant appends a name-formatting template.

**Test Cases:** `rcb_tests/public_test_cases/feature5_3_list_containers.json`

```json
{
    "description": "Generate docker commands that enumerate containers for the service/role. list_containers lists all (including stopped) by label filters; with a destination a destination filter is inserted. list_container_names is the same query with a Go-template name format appended.",
    "cases": [
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "list_containers"
            },
            "expected_output": "docker container ls --all --filter label=service=app --filter label=role=web"
        },
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "list_container_names"
            },
            "expected_output": "docker container ls --all --filter label=service=app --filter label=role=web --format '{{ .Names }}'"
        }
    ]
}
```

*5.4 Remove containers — one by exact name, or prune all by label*

Remove one container by exact name (with destination inserted) by piping its id into a remove command. Prune removes all stopped containers matching the label filters; a destination inserts a destination filter.

**Test Cases:** `rcb_tests/public_test_cases/feature5_4_remove_containers.json`

```json
{
    "description": "Generate docker commands that remove containers. remove_container targets one exact container name (service-role-[destination-]version) anchored with ^ and $, piping its id into docker container rm; a destination is inserted into the name. remove_containers prunes all stopped containers matching the service/role label filters; with a destination an extra destination filter is inserted.",
    "cases": [
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "remove_container", "args": {"version": "999"}
            },
            "expected_output": "docker container ls --all --filter name=^app-web-999$ --quiet | xargs docker container rm"
        },
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "remove_containers"
            },
            "expected_output": "docker container prune --force --filter label=service=app --filter label=role=web"
        }
    ]
}
```

*5.5 Manage images — list, prune, and tag-as-latest*

List images for the configured repository (registry server joined to image name, or just the image when no server). Prune removes all images matching the label filters (a destination inserts a destination filter). Tag-as-latest tags the current `repository:version` reference as `repository:latest`.

**Test Cases:** `rcb_tests/public_test_cases/feature5_5_images.json`

```json
{
    "description": "Generate docker commands that manage images. list_images lists images for the configured repository (registry server plus image name, or just the image when no server). remove_images prunes all images matching the service/role label filters; a destination inserts an extra destination filter. tag_current_as_latest tags the current versioned image reference as :latest for the same repository.",
    "cases": [
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "list_images"
            },
            "expected_output": "docker image ls dhh/app"
        },
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1"], "env": {"secret": ["RAILS_MASTER_KEY"]}},
                "env": {"RAILS_MASTER_KEY": "456"}, "version": "999", "role": "web", "action": "tag_current_as_latest"
            },
            "expected_output": "docker tag dhh/app:999 dhh/app:latest"
        }
    ]
}
```

---

### Feature 6: Role Configuration Resolution

**As a developer**, I want roles resolved from one declarative config (hosts, commands, labels, env, secrets), so each role gets correctly merged settings without duplication.

**Expected Behavior / Usage:**

*6.1 Resolve hosts and startup command per role*

When servers is a flat array, a single implicit role owns all hosts and has no startup command. When servers is a map, each named role lists hosts directly or under a `hosts` key and may define its own startup command. Querying hosts returns them one per line; querying the command returns it (empty when none).

**Test Cases:** `rcb_tests/public_test_cases/feature6_1_role_hosts_cmd.json`

```json
{
    "description": "Resolve the host list and startup command for a named role from the deployment. When servers is a flat array, the single implicit role owns all hosts and has no startup command. When servers is a map, each named role may list hosts directly or under a hosts key and may define its own startup command. role.hosts returns the role's hosts one per line; role.cmd returns the role's startup command (empty when none).",
    "cases": [
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1", "1.1.1.2"], "env": {"REDIS_URL": "redis://x/y"}},
                "role": "web", "action": "role.hosts"
            },
            "expected_output": "1.1.1.1\n1.1.1.2"
        },
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": {"web": ["1.1.1.1", "1.1.1.2"], "workers": {"hosts": ["1.1.1.3", "1.1.1.4"], "cmd": "bin/jobs", "env": {"REDIS_URL": "redis://a/b", "WEB_CONCURRENCY": 4}}}, "env": {"REDIS_URL": "redis://x/y"}},
                "role": "workers", "action": "role.hosts"
            },
            "expected_output": "1.1.1.3\n1.1.1.4"
        },
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1", "1.1.1.2"], "env": {"REDIS_URL": "redis://x/y"}},
                "role": "web", "action": "role.cmd"
            },
            "expected_output": "cmd="
        },
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": {"web": ["1.1.1.1", "1.1.1.2"], "workers": {"hosts": ["1.1.1.3", "1.1.1.4"], "cmd": "bin/jobs", "env": {"REDIS_URL": "redis://a/b", "WEB_CONCURRENCY": 4}}}, "env": {"REDIS_URL": "redis://x/y"}},
                "role": "workers", "action": "role.cmd"
            },
            "expected_output": "cmd=bin/jobs"
        }
    ]
}
```

*6.2 Resolve label arguments per role, including web routing labels*

A non-routed role gets only service and role labels. The web role (and any role explicitly opted into routing) additionally gets a fixed set of reverse-proxy routing labels whose keys embed the `service-role` identifier: a loadbalancer scheme, a path-prefix router rule, a retry middleware with attempts and initial interval, and a router-to-middleware binding. These are derived purely from the service and role names.

**Test Cases:** `rcb_tests/public_test_cases/feature6_2_role_label_args.json`

```json
{
    "description": "Compute the docker --label arguments for a role. A non-web role without traffic-routing enabled gets only the service and role labels. The web role (and any role explicitly opted into routing) additionally gets a fixed set of reverse-proxy routing labels whose keys embed the service-role identifier: a loadbalancer scheme, a path-prefix router rule, a retry middleware with attempts and initial interval, and a router-to-middleware binding. The routing labels are derived purely from the service and role names.",
    "cases": [
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": {"web": ["1.1.1.1", "1.1.1.2"], "workers": {"hosts": ["1.1.1.3", "1.1.1.4"], "cmd": "bin/jobs", "env": {"REDIS_URL": "redis://a/b", "WEB_CONCURRENCY": 4}}}, "env": {"REDIS_URL": "redis://x/y"}},
                "role": "workers", "action": "role.label_args"
            },
            "expected_output": "--label service=\"app\" --label role=\"workers\""
        },
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1", "1.1.1.2"], "env": {"REDIS_URL": "redis://x/y"}},
                "role": "web", "action": "role.label_args"
            },
            "expected_output": "--label service=\"app\" --label role=\"web\" --label traefik.http.services.app-web.loadbalancer.server.scheme=\"http\" --label traefik.http.routers.app-web.rule=\"PathPrefix(\\`/\\`)\" --label traefik.http.middlewares.app-web-retry.retry.attempts=\"5\" --label traefik.http.middlewares.app-web-retry.retry.initialinterval=\"500ms\" --label traefik.http.routers.app-web.middlewares=\"app-web-retry@docker\""
        }
    ]
}
```

*6.3 Resolve a single custom label with override precedence*

Custom labels declared at the deployment level apply to every role. A role-level custom label of the same key overrides the deployment value. A custom label that reuses a default routing-label key overrides that default. Querying a label key returns the resolved `key=value`.

**Test Cases:** `rcb_tests/public_test_cases/feature6_3_role_custom_labels.json`

```json
{
    "description": "Resolve the value of a single label for a role, given a label key. Custom labels declared at the deployment level apply to every role. A role-level custom label of the same key overrides the deployment-level value. A custom label that uses the same key as a default routing label overrides that default. The query returns the resolved key=value for the requested label key.",
    "cases": [
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": ["1.1.1.1", "1.1.1.2"], "env": {"REDIS_URL": "redis://x/y"}, "labels": {"my.custom.label": "50"}},
                "role": "web", "action": "role.label", "args": {"key": "my.custom.label"}
            },
            "expected_output": "my.custom.label=50"
        },
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": {"web": ["1.1.1.1", "1.1.1.2"], "workers": {"hosts": ["1.1.1.3", "1.1.1.4"], "cmd": "bin/jobs", "labels": {"my.custom.label": "70"}}}, "env": {"REDIS_URL": "redis://x/y"}, "labels": {"my.custom.label": "50"}},
                "role": "workers", "action": "role.label", "args": {"key": "my.custom.label"}
            },
            "expected_output": "my.custom.label=70"
        }
    ]
}
```

*6.4 Resolve plain (non-secret) env with role override*

Deployment-level env applies to all roles; a role's own env merges over it, so a role can override a value for a key. Querying one key returns its resolved value. Rendering the full env args produces an ordered list of `-e KEY="value"` pairs; the output shows an unredacted line and a redacted line (identical here, as none of these values are secret).

**Test Cases:** `rcb_tests/public_test_cases/feature6_4_role_env_merge.json`

```json
{
    "description": "Resolve environment variables for a role and render them as docker -e arguments. Deployment-level clear env applies to all roles; a role's own env merges over it, so a role can override a deployment value for a given key. role.env_value returns the resolved value for one key. role.env_args renders the full ordered list of -e KEY=\"value\" pairs; the output shows both an unredacted line (real values) and a redacted line (here identical, since none of these values are secret).",
    "cases": [
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": {"web": ["1.1.1.1", "1.1.1.2"], "workers": {"hosts": ["1.1.1.3", "1.1.1.4"], "cmd": "bin/jobs", "env": {"REDIS_URL": "redis://a/b", "WEB_CONCURRENCY": 4}}}, "env": {"REDIS_URL": "redis://x/y"}},
                "role": "workers", "action": "role.env_value", "args": {"key": "REDIS_URL"}
            },
            "expected_output": "REDIS_URL=redis://a/b"
        },
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": {"web": ["1.1.1.1", "1.1.1.2"], "workers": {"hosts": ["1.1.1.3", "1.1.1.4"], "cmd": "bin/jobs", "env": {"REDIS_URL": "redis://a/b", "WEB_CONCURRENCY": 4}}}, "env": {"REDIS_URL": "redis://x/y"}},
                "role": "workers", "action": "role.env_args"
            },
            "expected_output": "unredacted: -e REDIS_URL=\"redis://a/b\" -e WEB_CONCURRENCY=\"4\"\nredacted: -e REDIS_URL=\"redis://a/b\" -e WEB_CONCURRENCY=\"4\""
        }
    ]
}
```

*6.5 Resolve secret env with redaction and concatenation order*

Env may split into a clear map (literal values) and a secret list (names whose values are read from the host environment at render time). Secrets and clear values may be declared at the deployment level, the role level, or both; the secret name lists from both levels are concatenated (deployment first, then role) ahead of the merged clear values. Rendering shows an unredacted line (real resolved secret values, shell-escaped) and a redacted line (secret values masked, clear values shown). Resolution order is significant and quoting must survive special characters.

**Test Cases:** `rcb_tests/public_test_cases/feature6_5_role_env_secrets.json`

```json
{
    "description": "Resolve environment variables when secrets are involved and render docker -e arguments with redaction. Env may be split into a clear map (literal values) and a secret list (names whose values are read from the host environment at render time). Secrets and clear values can be declared at the deployment level, at the role level, or both; secret name lists from both levels are concatenated (deployment secrets first, then role secrets) ahead of the merged clear values. Each rendered line shows the unredacted arguments (real resolved secret values, shell-escaped) and the redacted arguments (secret values masked, clear values shown). Secret resolution is order-sensitive and quoting must survive special characters.",
    "cases": [
        {
            "input": {
                "deploy": {"service": "app", "image": "dhh/app", "registry": {"username": "dhh", "password": "secret"}, "servers": {"web": ["1.1.1.1", "1.1.1.2"], "workers": {"hosts": ["1.1.1.3", "1.1.1.4"], "cmd": "bin/jobs", "env": {"clear": {"REDIS_URL": "redis://a/b", "WEB_CONCURRENCY": 4}, "secret": ["DB_PASSWORD"]}}}, "env": {"clear": {"REDIS_URL": "redis://a/b"}, "secret": ["REDIS_PASSWORD"]}},
                "env": {"REDIS_PASSWORD": "secret456", "DB_PASSWORD": "secret&\"123"},
                "role": "workers", "action": "role.env_args"
            },
            "expected_output": "unredacted: -e REDIS_PASSWORD=\"secret456\" -e DB_PASSWORD=\"secret&\\\"123\" -e REDIS_URL=\"redis://a/b\" -e WEB_CONCURRENCY=\"4\"\nredacted: -e REDIS_PASSWORD=[REDACTED] -e DB_PASSWORD=[REDACTED] -e REDIS_URL=\"redis://a/b\" -e WEB_CONCURRENCY=\"4\""
        }
    ]
}
```

---

## Deliverables

1. **The Core System:** A cleanly structured, multi-file codebase implementing config/role resolution, command building, shell-escaping/redaction, and SSH wrapping, with clear logical separation and no monolithic file.

2. **The Execution/Test Adapter:** A runnable entry point that reads one JSON command object from stdin, invokes the appropriate core logic, and prints the resulting command string (or resolved value) to stdout, strictly matching the per-leaf-feature contracts above. Native runtime failures (e.g. a missing secret env var) are rendered as a neutral category line, never leaking host-language exception details. The adapter is logically separated from the core domain.

3. **Automated test harness:** The cases embedded in this PRD live under `rcb_tests/public_test_cases/`. A single entry point `bash rcb_tests/test.sh` reads every `*.json` case file from a case directory and runs the full suite; it accepts `--cases-dir <subdir>` (default `public_test_cases`). For each case it writes one file to `rcb_tests/stdout/<cases-dir>/{filename.stem}@{case_index.zfill(3)}.txt` (e.g. the first case of `feature1_1_run_basic.json` run with `--cases-dir public_test_cases` → `rcb_tests/stdout/public_test_cases/feature1_1_run_basic@000.txt`). Output is namespaced by `<cases-dir>` so different case directories never overwrite each other. Each `.txt` contains only the raw stdout of the program under test (no PASS/FAIL or metadata) so it can be compared directly against `expected_output`.


---
**Implementation notes:**
- follow the exact flag ordering shown in the prior test cases
