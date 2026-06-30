# ICAE-Bench

An **interactive** code-generation benchmark. Each task hands the agent-under-test a deliberately **fuzzy** Product Requirement Document (PRD). To fill the gaps the agent must hold a multi-turn conversation with a **User Agent (Oracle)** that answers clarifying questions strictly from a hidden ground-truth spec. The agent then implements the feature inside a language-specific Docker container, and the harness scores the result along four metric groups (dynamic tests, structural similarity, agentic review, and interaction quality).

- **480 real-world tasks** across 12 languages (C#, C++, Dart, Go, Java, JavaScript, Kotlin, PHP, Python, Ruby, Rust, TypeScript). A `lite` subset of 50 is provided for quick runs.
- **Anonymized**: the agent only ever sees an opaque alias `realcode@NNN`, never the real repository name or the golden source.
- **Two agent frameworks**: `claude-code` (default, via `claude-agent-sdk`) and `openhands` (via the OpenHands SDK).
- **Three PRD difficulties**: `normal`, `medium`, `easy`.

---

## 1. Repository layout

```
icae_eval_anonymous/
├── README.md
├── requirements.txt              # core deps (claude-code framework)
├── requirements-openhands.txt    # extra deps for --agent-framework openhands
├── download_scaffold.sh          # pull base-language Docker images + data tars
├── model_list.json               # TEMPLATE — fill in your gateways/tokens (SUT + Critic)
├── repo_alias.json               # realcode@NNN -> {real key, language, LOC, ...}
├── task.md                       # parameter + metric reference
├── harness/                      # the evaluation engine
│   ├── orchestrator.py           # CLI entry point (run | eval)
│   ├── config.py                 # all paths + model_list lookup (relative + env-overridable)
│   ├── agent_runner.py           # claude-code runner
│   ├── openhands_runner.py       # openhands runner
│   ├── docker_env.py             # per-repo container provisioning
│   ├── evaluate.py               # (a) dynamic test execution
│   ├── structural.py             # (b) structural assessment
│   ├── agentic.py                # (c) agentic (critic) evaluation
│   ├── summarize.py              # per-run report -> results/<id>/summary.md
│   ├── analyze.py + repos.yaml   # vendored language extractors used by (b)
│   └── prompt_templates/         # task_docker.md, task_agentic.md
├── scripts/                      # convenience launchers (base env, lite)
│   ├── _common.sh                # shared defaults + run_orchestrator wrapper
│   ├── run_lite_base.sh          # one model, lite, base env
│   └── run_all_lite_base.sh      # all models in parallel
├── tools/
│   └── write_fuzzy_prds.py       # (re)generate fuzzy_prds*/ from user_agent/prd_json*
├── user_agent/                   # the Oracle service (separate from the harness)
│   ├── main.py                   # 3-port FastAPI service (50001/50002/50003)
│   ├── user_agent.py             # Oracle core (Messages API, oracle_data only)
│   ├── user_model.json           # TEMPLATE — Oracle model endpoints
│   ├── init.md                   # Oracle persona + interaction rules
│   ├── fuzzy_suffix.md           # clarification block appended to every fuzzy PRD
│   ├── example_client.py         # how the harness drives the three ports
│   ├── prd_json/                 # 480 task specs (normal)   — fuzzy_prd + oracle_data + tests
│   ├── prd_json_medium/          # 480 task specs (medium)
│   └── prd_json_easy/            # 480 task specs (easy)
├── fuzzy_prds/                   # generated raw PRDs (normal)  — start.md per alias
├── fuzzy_prds_medium/            # generated raw PRDs (medium)
└── fuzzy_prds_easy/              # generated raw PRDs (easy)
```

Two large data artifacts are **not** bundled and must be downloaded (see §2):

| Artifact | Default unpack location | Env override | Used by |
|---|---|---|---|
| Base-language Docker images | `docker_lang_official/` | `ICAE_DOCKER_LANG_DIR` | container provisioning |
| Golden original source (`realcode_repos.tar.lz4`) | `realcode_repos/<key>/` | `ICAE_GOLDEN_REPOS_DIR` | structural + agentic scoring |
| Authoritative tests (`rcb_tests` tar) | `rcb_tests_repos/<key>/rcb_tests/` | `ICAE_RCB_TESTS_DIR` | dynamic test execution |

All other paths are derived **relative to the repo root**, so you can clone/unzip this directory anywhere.

---

## 2. Download the data

> If your network needs a proxy for the public internet (Docker Hub / Zenodo), enable it first, e.g. `source ~/proxy.sh`.

```bash
bash download_scaffold.sh
```

This script:

1. `docker pull` + `docker save` the 12 base-language images into `docker_lang_official/` (Python 3.11, Node 20, Go 1.22, Java 17, … plus the Kotlin image fetched from Zenodo).
2. Downloads and unpacks the **golden source** tar `realcode_repos.tar.lz4` into `realcode_repos/<username>__<repo>/`.
3. Downloads and unpacks the **authoritative tests** tar into `rcb_tests_repos/<username>__<repo>/rcb_tests/`.

> The two data-tar download URLs are filled in at the bottom of `download_scaffold.sh` (the Zenodo records). If you unpack them elsewhere, point `ICAE_GOLDEN_REPOS_DIR` / `ICAE_RCB_TESTS_DIR` at those locations instead.

Docker must be installed and runnable by the current user.

---

## 3. Install

```bash
python -m venv .venv && source .venv/bin/activate   # Python >= 3.11
pip install -r requirements.txt

# Only if you intend to run --agent-framework openhands (Python >= 3.12):
pip install -r requirements-openhands.txt
```

You also need the **Claude Code CLI** on your `$PATH` for the default `claude-code` framework. If it lives at a custom path, set:

```bash
export ICAE_CLAUDE_CLI=/path/to/claude
```

---

## 4. Configure model endpoints

Both registries ship as **templates** with `<...>` placeholders — fill in your own gateway URLs and tokens. Nothing in this repo contains real credentials.

- **`model_list.json`** — the agent-under-test (`Tested Model`) and the Critic reviewer (`Critic Model`). Each model name maps to one endpoint dict or a list of interchangeable endpoints (load-balanced round-robin). An endpoint carries `ANTHROPIC_*` (for the claude-code runner) and/or `OPENHANDS_*` (for openhands).
- **`user_agent/user_model.json`** — the Oracle's own model(s), keyed by `user_model_name` (e.g. `DeepSeek-V3.2`, `Gemini-3.1-Flash-Lite`).

---

## 5. Start the User Agent (Oracle)

The Oracle is a standalone 3-port FastAPI service that runs in **one process**:

| Port | Service | Purpose |
|---|---|---|
| 50001 | Init | validate the secret key, mint an `append_id` |
| 50002 | Interaction | answer clarifying questions for `{append_id, task_id}` |
| 50003 | Stats | report interaction-quality metrics for an `append_id` |

```bash
# Do NOT route this through a github proxy — it binds local ports.
python user_agent/main.py
```

It listens on `0.0.0.0:50001/50002/50003`. The secret init key is the demo constant `INIT_KEY` in `user_agent/main.py` (and mirrored in `harness/config.py`); change both for a real deployment. See `user_agent/README.md` for the full API contract and `user_agent/example_client.py` for a worked client example.

> **Model choice matters.** The Oracle relies on the caller-supplied `system` prompt to take on the reviewer persona. A gateway that bakes in a fixed identity and ignores/overrides `system` will not work — pick a clean pass-through deployment that respects `system`.

---

## 6. Generate the raw fuzzy PRDs (one-time)

The `fuzzy_prds*/` trees are already populated, but you can regenerate them from the authoritative task specs in `user_agent/prd_json*` at any time:

```bash
python tools/write_fuzzy_prds.py --difficulty all   # or: normal | medium | easy
```

---

## 7. Run an evaluation

### Quick start (convenience scripts)

```bash
# One model, lite (50 repos), base env, concurrency 4:
bash scripts/run_lite_base.sh Opus-4.8

# All default models in parallel (each gets its own append_id):
bash scripts/run_all_lite_base.sh

# Override Oracle host / model via env:
USER_HOST=127.0.0.1 USER_MODEL_NAME=DeepSeek-V3.2 bash scripts/run_lite_base.sh GLM-5.1
```

### Direct invocation

```bash
python -m harness.orchestrator run \
    --model-name        Opus-4.8 \
    --env-mode          base \
    --eval-mode         lite \
    --prd-type          fuzzy \
    --difficulty        normal \
    --agent-framework   claude-code \
    --user-model-name   DeepSeek-V3.2 \
    --critic-model-name Deepseek-V4-Flash \
    --query-count       16 \
    --concurrency       4 \
    --user-host         127.0.0.1
```

Re-score an existing run without regenerating code:

```bash
python -m harness.orchestrator eval --append-id <append_id>
```

### Key parameters

| Flag | Default | Meaning |
|---|---|---|
| `--model-name` | (required) | key in `model_list.json["Tested Model"]` |
| `--env-mode` | (required) | `base` (this release ships base-language images only) |
| `--eval-mode` | `lite` | `lite` = first 50 repos, `full` = all 480 |
| `--prd-type` | `fuzzy` | `fuzzy` (Oracle interaction) — the mode shipped in this release |
| `--difficulty` | `normal` | `normal` / `medium` / `easy` PRD detail level |
| `--agent-framework` | `claude-code` | `claude-code` or `openhands` |
| `--user-model-name` | `DeepSeek-V3.2` | Oracle model (key in `user_model.json`: DeepSeek-V3.2 / Gemini-3.1-Flash-Lite / Qwen3.5-4B) |
| `--critic-model-name` | `Deepseek-V4-Flash` | reviewer for the agentic metric |
| `--query-count` | `16` | max clarifying questions per repo |
| `--append-id` | — | resume an existing run; omit to mint a fresh one |
| `--concurrency` | `10` | repos generated in parallel |
| `--user-host` / `--user-*-port` | `127.0.0.1` / `50001-3` | Oracle endpoint |
| `--repos` | all in scope | restrict to specific aliases, e.g. `realcode@001` |

A fresh run (no `--append-id`) mints a new id from the Oracle and writes:

```
results/settings.json              # registry: append_id -> config
results/<append_id>/settings.json  # this run's config + per-repo results
results/<append_id>/<alias>/       # the agent's working tree (bind-mounted)
results/<append_id>/_eval/<alias>/ # structural.json / subjective.json / objective.json
```

Generate a human-readable report:

```bash
python -m harness.summarize <append_id>   # -> results/<append_id>/summary.md
```

---

## 8. Metrics

| Group | Source | Metrics |
|---|---|---|
| (a) Dynamic Test Execution | container run, host-side stdout compare | Public / Native (hidden) / Enhanced pass rate |
| (b) Structural Assessment | host-side AST/regex over golden vs generated | File Count / LOC, Class Similarity, Method Similarity |
| (c) Agentic Evaluation | Critic Model, single forced-tool call | Semantic Similarity, API Similarity, Design Quality |
| (d) Interaction Quality | Oracle stats endpoint (50003) | Constraint Coverage, Fallback Rate, Budget Usage Rate |

Canonical column mapping in `summarize.py`: `public_visible → Public`, `hidden → Native`, `enhanced → Enhanced`. Overall is the case-micro pass rate over hidden + enhanced cases.

---

## 9. Environment variables

| Variable | Purpose |
|---|---|
| `ICAE_GOLDEN_REPOS_DIR` | golden original-source root (`realcode_repos.tar.lz4`) |
| `ICAE_RCB_TESTS_DIR` | authoritative test root (`rcb_tests` tar) |
| `ICAE_DOCKER_LANG_DIR` | base-image tar directory |
| `ICAE_CLAUDE_CLI` | path to the `claude` CLI binary |
| `PROXY` / `PROXY_FALLBACK_FILE` | in-container dependency-install proxy (see `scripts/_common.sh`) |
