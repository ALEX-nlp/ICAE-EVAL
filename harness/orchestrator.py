"""ICAE-Bench evaluation orchestrator.

Entry point. Two subcommands:

  run   mint/resume an append_id, then for each repo: build the PRD, provision a
        PRD-only container, run the agent-under-test (Claude Code CLI via
        claude-agent-sdk) in results/<append_id>/<repo>, optionally score it.

  eval  re-run all scoring groups over an existing results/<append_id>
        (reuses the recorded run config, repositories, and container images).

Usage examples:
  python -m harness.orchestrator run \
      --model-name Opus-4.8 \
      --user-model-name DeepSeek-V3.2 --query-count 16 \
      --user-host 127.0.0.1 --repos realcode@001
  python -m harness.orchestrator eval --append-id <id>
"""
import argparse
import asyncio
import os
import subprocess
import time
from pathlib import Path

from . import config as C
from . import prd as prd_mod
from . import docker_env
from . import evaluate as eval_mod
from . import structural as struct_mod
from . import agentic as agentic_mod
from .critic_pool import CriticPool
from . import user_agent_client as ua
from .agent_runner import run_agent, RateLimited
from .task_template import render_task_prompt

RATELIMIT_BACKOFF = [30, 60, 120, 240]


def _no_proxy(args) -> str:
    """no_proxy list for in-container env, used whenever ANY proxy is injected.

    A proxy reaches the public internet (for apt/pip/npm installs) but the
    Oracle/User-Agent lives on the internal network, so its host must bypass the
    proxy or the agent's clarification POSTs would be routed to the gateway and
    fail. This list is consumed only when a proxy (explicit --proxy or the
    one-shot fallback) is actually injected; harmless otherwise.
    """
    if getattr(args, "no_proxy", None):
        return args.no_proxy
    hosts = ["localhost", "127.0.0.1"]
    if getattr(args, "user_host", None):
        hosts.append(args.user_host)
    return ",".join(hosts)


def _fallback_proxy(args) -> str | None:
    """Resolve the one-shot retry proxy address from --proxy-fallback-file.

    The file is a shell snippet exporting http_proxy/https_proxy (e.g.
    ~/proxy.sh). We source it in a subshell and read the address back, so the
    proxy is NOT applied to anything by default — evaluate.py only injects it for
    a single retry after a direct install fails on a network error. Returns None
    when no fallback file is given or it yields no address.
    """
    f = getattr(args, "proxy_fallback_file", None)
    if not f:
        return None
    p = Path(f).expanduser()
    if not p.is_file():
        return None
    try:
        out = subprocess.run(
            ["bash", "-c", f"source '{p}' >/dev/null 2>&1; "
                           f"printf '%s' \"${{https_proxy:-$http_proxy}}\""],
            capture_output=True, text=True, timeout=10)
        addr = (out.stdout or "").strip()
        return addr or None
    except Exception:  # noqa: BLE001
        return None


# ── repo selection ────────────────────────────────────────────────────────────

def available_repos(prd_type: str, difficulty: str = "normal") -> list[str]:
    """All anonymized aliases ('realcode@NNN') with a PRD, sorted numerically.

    Dir names are zero-padded ('realcode@001'..'realcode@480') so lexical sort is
    numeric — this also defines the lite slice (the 50 smallest-by-golden-LOC).
    """
    if prd_type == "fuzzy":
        root = C.fuzzy_prds_dir(difficulty)
    else:
        root = C.DETAILED_PRDS
    if not root.is_dir():
        return []
    return sorted(d.name for d in root.iterdir() if (d / "start.md").exists())


def select_repos(args) -> list[str]:
    """Resolve the requested aliases. --repos/--repo-file accept either an alias
    ('realcode@001') or a real repo key (auto-translated). eval_mode=lite keeps the
    first 50 (smallest golden code); --limit further truncates. An eval-only run
    defaults to the successfully generated repos recorded under its append_id."""
    repos = available_repos(args.prd_type, getattr(args, "difficulty", "normal"))
    if args.repos:
        want = [r.strip() for r in args.repos.split(",") if r.strip()]
        want = [_to_alias(r) for r in want]
        repos = [r for r in want if r in repos] or want
    elif args.repo_file:
        want = [l.strip() for l in Path(args.repo_file).read_text().splitlines() if l.strip()]
        want = [_to_alias(r) for r in want]
        repos = [r for r in want if r in repos] or want
    elif getattr(args, "only_eval", False) and args.append_id:
        recorded = ua.load_run_record(args.append_id).get("repos", {})
        successful = [
            alias for alias, status in recorded.items()
            if status.get("generation") == "success"
        ]
        # Older run records may predate the generation-status field. Fall back
        # to their persisted code paths only when no explicit successes exist.
        repos = successful or [
            alias for alias, status in recorded.items() if status.get("code_path")
        ]
    elif getattr(args, "eval_mode", "full") == "lite":
        repos = repos[:50]
    if getattr(args, "resume_fill", False):
        repos = _resume_fill(repos, args.append_id)
    if args.limit:
        repos = repos[: args.limit]
    return repos


def _hydrate_eval_args(args) -> dict:
    """Load immutable run context for `eval` without overwriting it with defaults."""
    run = ua.load_run_record(args.append_id)
    if not run:
        raise SystemExit(
            f"no per-run settings found for append_id {args.append_id} "
            f"({C.run_settings_path(args.append_id)})")
    cfg = run.get("config", {})

    # Evaluation reuses the generation context. The three values exposed on the
    # eval CLI remain overridable for migrations to another Oracle/Critic host.
    fixed = {
        "model_name": "",
        "env_mode": "base",
        "eval_mode": "full",
        "prd_type": "fuzzy",
        "difficulty": "normal",
        "user_model_name": "",
        "query_count": 16,
        "agent_framework": "claude-code",
    }
    for key, fallback in fixed.items():
        setattr(args, key, cfg.get(key, fallback))

    overridable = {
        "critic_model_name": "Deepseek-V4-Flash",
        "user_host": "127.0.0.1",
        "user_init_port": 50001,
        "user_query_port": 50002,
        "user_eval_port": 50003,
    }
    for key, fallback in overridable.items():
        if getattr(args, key, None) is None:
            setattr(args, key, cfg.get(key, fallback))

    # Generation-only flags are referenced by shared control flow but must never
    # affect an eval-only pass.
    args.force = False
    args.resume_fill = False
    args.scaffold = False
    return run


def _resume_fill(repos: list[str], append_id: str | None) -> list[str]:
    """Single-phase resume target. From `repos`, keep ONLY the unfinished ones
    (no record yet, or generation=='running' — an interrupted half-run); if there
    are none, fall back to the failures (generation in 'error'/'skipped'). Repos
    whose generation=='success' are dropped either way, so resume never re-evals an
    already-scored repo. Phase choice is logged so a run's intent is auditable."""
    if not append_id:
        raise SystemExit("--resume-fill requires --append-id (it reads that run's "
                         "results/<id>/settings.json to find unfinished/failed repos)")
    record = ua.load_run_record(append_id)
    status = record.get("repos", {})
    unfinished, failed = [], []
    for alias in repos:
        gen = (status.get(alias) or {}).get("generation")
        if gen == "success":
            continue
        if gen in (None, "running"):
            unfinished.append(alias)
        else:  # 'error', 'skipped', anything else non-success
            failed.append(alias)
    if unfinished:
        print(f"[resume-fill] phase=unfinished: {len(unfinished)} repo(s) "
              f"(never generated or interrupted); {len(failed)} failed repo(s) "
              f"deferred to a later pass")
        return unfinished
    print(f"[resume-fill] phase=retry-error: no unfinished repos left; "
          f"retrying {len(failed)} failed repo(s)")
    return failed


def _to_alias(token: str) -> str:
    """Accept an alias or a real key; return the alias (unchanged if unknown)."""
    try:
        return C.resolve_alias(token)
    except KeyError:
        return token


def _other_live_orchestrators(append_id: str) -> list[str]:
    """PIDs of OTHER live `harness.orchestrator` processes whose cmdline carries this
    append_id (excludes self). Used to guard --resume-fill against colliding with a
    still-running resume of the same id."""
    try:
        out = subprocess.run(["pgrep", "-af", "harness.orchestrator"],
                             capture_output=True, text=True).stdout
    except Exception:  # noqa: BLE001 — pgrep absent: best-effort, don't block
        return []
    me = str(os.getpid())
    pids = []
    for line in out.splitlines():
        parts = line.split(None, 1)
        if len(parts) < 2:
            continue
        pid, cmd = parts
        if pid == me or "pgrep" in cmd:
            continue
        if append_id in cmd:
            pids.append(pid)
    return pids


# ── per-repo pipeline ─────────────────────────────────────────────────────────

async def process_repo(alias: str, args, model_entries: list, append_id: str,
                       sem: asyncio.Semaphore, entry_idx: int = 0) -> None:
    async with sem:
        t0 = time.time()
        code_path = C.code_path(append_id, alias)
        log_path = C.RESULTS / append_id / "_logs" / f"{C.docker_safe(alias)}.log"
        lang = C.prompt_language(args.env_mode, alias)
        print(f"[{alias}] start (env_mode={args.env_mode} lang={lang})")

        # resume: skip repos already done unless --force
        prior = ua.get_repo_status(append_id, alias)
        if prior.get("generation") == "success" and not args.force and not args.only_eval:
            print(f"[{alias}] already generated — skipping (use --force to redo)")
            if args.eval:
                await _eval_only(alias, args, append_id, prior)
            return

        if args.only_eval:
            await _eval_only(alias, args, append_id, prior)
            return

        try:
            tar_path = C.resolve_docker_tar(args.env_mode, alias)
        except Exception as e:  # noqa: BLE001
            print(f"[{alias}] SKIP: {e}")
            ua.update_repo_status(append_id, alias, {"generation": "skipped", "reason": str(e)})
            return

        # 1. build the PRD text
        try:
            prd_text = prd_mod.resolve_prd(
                alias, prd_type=args.prd_type, append_id=append_id,
                user_host=args.user_host, user_query_port=args.user_query_port,
                user_model_name=args.user_model_name, query_count=args.query_count,
                difficulty=getattr(args, "difficulty", "normal"),
            )
        except Exception as e:  # noqa: BLE001
            print(f"[{alias}] SKIP (PRD): {e}")
            ua.update_repo_status(append_id, alias, {"generation": "skipped", "reason": f"prd: {e}"})
            return

        # 2. provision container (PRD-only workdir, bind-mounted to host code path)
        #    --scaffold additionally drops the repo's public cases at
        #    rcb_tests/public_test_cases so the agent can self-check; off by default.
        scaffold_src = None
        if getattr(args, "scaffold", False):
            cand = C.REPOS_DIR / C.key_for_alias(alias) / "rcb_tests" / "public_test_cases"
            if cand.is_dir():
                scaffold_src = cand
            else:
                print(f"[{alias}] scaffold: no public_test_cases at {cand} — skipping")
        container = None
        try:
            container = await asyncio.to_thread(
                docker_env.provision, alias, code_path, prd_text, tar_path,
                clean_workdir=not args.force, proxy=args.proxy,
                no_proxy=_no_proxy(args),
                hide_real_tag=(args.env_mode.strip() == "ultimate"),
                name_suffix=append_id[:8],
                scaffold_src=scaffold_src,
            )
        except Exception as e:  # noqa: BLE001
            print(f"[{alias}] FAIL (docker): {e}")
            ua.update_repo_status(append_id, alias, {"generation": "error", "reason": f"docker: {e}"})
            return

        # settings.json is host-side (never seen by the agent), so we keep the real
        # repo key + the anon image tag for traceability/eval.
        ua.update_repo_status(append_id, alias, {
            "code_path": str(code_path), "image": container.image_tag,
            "real_key": C.key_for_alias(alias),
            "container_id": container.container_id, "language": lang,
            "docker_tar": str(tar_path), "generation": "running",
        })

        # 3. run the agent (with simple rate-limit backoff).
        #    teardown is in `finally` so the container is ALWAYS reclaimed —
        #    success, model/infra error, an unexpected exception from the runner,
        #    or task cancellation alike. Without this, any generation that raised
        #    left a live `sleep infinity` container holding its RAM; over a long
        #    run those orphans pile up past the concurrency cap and exhaust host
        #    memory (the failure mode behind the 2026-06-20 hang).
        image_tag = container.image_tag
        prompt = render_task_prompt(alias, docker_id=container.container_id, lang=lang)
        try:
            result = await _run_with_backoff(prompt, code_path, log_path,
                                             model_entries, args, start_idx=entry_idx)
        finally:
            try:
                container.teardown()
            except Exception:  # noqa: BLE001
                pass

        gen_status = {
            "generation": result.status, "is_error": result.is_error,
            "refused": result.refused, "num_turns": result.num_turns,
            "cost_usd": result.cost_usd, "detail": result.detail,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
            "cache_creation_tokens": result.cache_creation_tokens,
            "cache_read_tokens": result.cache_read_tokens,
            "gen_seconds": round(time.time() - t0, 1),
        }
        ua.update_repo_status(append_id, alias, gen_status)
        print(f"[{alias}] generation={result.status} turns={result.num_turns} "
              f"cost=${result.cost_usd:.3f} tok={result.input_tokens}/{result.output_tokens} "
              f"({gen_status['gen_seconds']}s)")

        # 4. objective eval
        if args.eval and result.status == "success":
            await _eval_repo(alias, args, append_id, image_tag)


def _select_runner(framework: str):
    """Return the framework's run_agent. Claude Code (Claude Agent SDK) is default."""
    if framework == "openhands":
        from .openhands_runner import run_agent as oh_run_agent
        return oh_run_agent
    return run_agent


# Transient infra/API failures that come back inside an AgentResult (status=
# "error", detail=...) rather than as a RateLimited exception. These are NOT the
# model's fault, so we retry them with backoff AND rotate to the next endpoint in
# the pool (a sibling token / gateway may be healthy). Kept loosely in sync with
# summarize._INFRA_MARKERS.
_RETRYABLE_DETAIL = (
    "no_db_connection", "no connected db", "ratelimited", "rate limit",
    "rate_limit", "429", "overloaded", "overload",
    "timeout_inactivity", "timeout_overall", "timed out", "timeout",
    "upstream_error", "upstream error", "bad gateway", "gateway timeout",
    "service unavailable", "service_unavailable", "internal server error",
    "502", "503", "504", "500",
    "connection", "connection reset", "connection refused", "network",
    "econnreset", "econnrefused", "dns",
)


def _is_retryable_detail(detail: str) -> bool:
    d = (detail or "").lower()
    return any(m in d for m in _RETRYABLE_DETAIL)


async def _run_with_backoff(prompt, code_path, log_path, model_entries, args,
                            start_idx: int = 0):
    """Run the agent, retrying transient infra/API failures with backoff.

    `model_entries` is the model's endpoint pool. Each retry rotates to the next
    endpoint (round-robin from `start_idx`) so a single sick token/gateway does
    not doom the repo. Two failure shapes are handled: a RateLimited exception,
    and an AgentResult(status="error") whose `detail` matches an infra marker
    (no_db_connection, 5xx, connection/timeout, ...). Genuine model errors (and
    success) return immediately. After the backoff schedule is exhausted, the
    last error result is returned so it is recorded as infra (excluded from
    scoring), never silently dropped.
    """
    runner = _select_runner(getattr(args, "agent_framework", "claude-code"))
    pool = model_entries if isinstance(model_entries, list) else [model_entries]
    n = max(1, len(pool))
    attempt = 0
    while True:
        entry = pool[(start_idx + attempt) % n]
        try:
            result = await runner(prompt, code_path, log_path, entry,
                                  max_turns=args.max_turns, timeout=args.timeout)
        except RateLimited as e:
            if attempt >= len(RATELIMIT_BACKOFF):
                from .agent_runner import AgentResult
                return AgentResult(status="error", is_error=True, detail=f"ratelimited: {e}")
            delay = RATELIMIT_BACKOFF[attempt]
            print(f"  [ratelimit] rotate endpoint + backoff {delay}s (attempt {attempt + 1})")
            await asyncio.sleep(delay)
            attempt += 1
            continue
        if (getattr(result, "status", None) == "error"
                and _is_retryable_detail(getattr(result, "detail", ""))
                and attempt < len(RATELIMIT_BACKOFF)):
            delay = RATELIMIT_BACKOFF[attempt]
            print(f"  [infra] {result.detail!r}; rotate endpoint + backoff {delay}s "
                  f"(attempt {attempt + 1})")
            await asyncio.sleep(delay)
            attempt += 1
            continue
        return result


async def _eval_repo(alias: str, args, append_id: str, image_tag: str) -> None:
    """Run all enabled metric groups for one repo and persist them to settings.

      (a) Dynamic Test Execution  -> objective.json  (fresh container)
      (b) Structural Assessment   -> structural.json (golden vs generated, scripted)
      (c) Agentic Evaluation      -> subjective.json (Critic Model review)
      (d) Interaction Quality     -> from the User Agent stats port, by task_id
    """
    print(f"[{alias}] evaluating ...")

    # (a) objective dynamic tests
    try:
        res = await asyncio.to_thread(
            eval_mod.evaluate_repo, append_id, alias, image_tag,
            proxy=args.proxy, no_proxy=_no_proxy(args),
            fallback_proxy=_fallback_proxy(args))
        ua.update_repo_status(append_id, alias, {"objective": res})
        summary = {k: res[k].get("rate") for k in ("public_visible", "hidden", "enhanced")
                   if isinstance(res.get(k), dict)}
        print(f"[{alias}] (a) objective rates: {summary}")
    except Exception as e:  # noqa: BLE001
        ua.update_repo_status(append_id, alias,
                              {"objective": {"error": f"eval crashed: {e}", "repo": alias}})
        print(f"[{alias}] (a) objective FAILED: {e}")

    # (b) structural assessment (File Count/LOC, Class/Method Similarity)
    try:
        struct_res = await asyncio.to_thread(
            struct_mod.evaluate_structural, append_id, alias, args.env_mode)
        ua.update_repo_status(append_id, alias, {"structural": struct_res})
        print(f"[{alias}] (b) class_sim={struct_res.get('class_similarity')} "
              f"method_sim={struct_res.get('method_similarity')}")
    except Exception as e:  # noqa: BLE001
        print(f"[{alias}] (b) structural FAILED: {e}")

    # (c) agentic evaluation (Critic Model: Semantic/API/Design)
    critic_pool = getattr(args, "_critic_pool", None)
    if critic_pool is not None:
        try:
            agentic_res = await agentic_mod.evaluate_agentic(
                append_id, alias, critic_pool, env_mode=args.env_mode)
            ua.update_repo_status(append_id, alias, {"agentic": agentic_res})
            print(f"[{alias}] (c) semantic={agentic_res.get('semantic_similarity')} "
                  f"api={agentic_res.get('api_similarity')} "
                  f"design={agentic_res.get('design_quality')} "
                  f"via={agentic_res.get('critic_label')}")
        except RateLimited as e:
            print(f"[{alias}] (c) agentic ratelimited: {e}")
        except Exception as e:  # noqa: BLE001
            print(f"[{alias}] (c) agentic FAILED: {e}")

    # (d) interaction quality (User Agent stats port, keyed by task_id=alias)
    inter = await asyncio.to_thread(
        ua.fetch_interaction_stats, append_id,
        user_host=args.user_host, user_eval_port=args.user_eval_port, task_id=alias)
    ua.update_repo_status(append_id, alias, {"interaction": inter})
    if inter.get("ok"):
        print(f"[{alias}] (d) coverage={inter.get('constraint_coverage')} "
              f"fallback={inter.get('fallback_rate')} budget={inter.get('budget_usage_rate')}")
    else:
        print(f"[{alias}] (d) interaction stats unavailable: {inter.get('error')}")


async def _eval_only(alias: str, args, append_id: str, prior: dict) -> None:
    # --reimage: ignore the image recorded at generation time and re-derive it from
    # the env_mode tar under the (now tar-keyed) anon tag. Needed to RECOMPUTE pass
    # rates for runs minted before the tag-collision fix, whose stored "image" is the
    # old ambiguous 'realcode/NNN:env' tag that may resolve to a base image on the
    # host (so re-evaluating an ultimate run would otherwise test in base again).
    image_tag = None if getattr(args, "reimage", False) else prior.get("image")
    if not image_tag:
        # reload the image from the tar to recover the (anon) tag
        try:
            tar_path = C.resolve_docker_tar(args.env_mode, alias)
            image_tag = docker_env.ensure_image(
                tar_path, anon_tag=docker_env.anon_tag_for(alias, tar_path),
                hide_real_tag=(args.env_mode.strip() == "ultimate"))
        except Exception as e:  # noqa: BLE001
            print(f"[{alias}] eval SKIP: no image ({e})")
            return
    await _eval_repo(alias, args, append_id, image_tag)


# ── driver ────────────────────────────────────────────────────────────────────

async def run_async(args) -> None:
    existing_run = _hydrate_eval_args(args) if args.only_eval else None
    framework = getattr(args, "agent_framework", "claude-code")
    model_entries = []
    if args.only_eval:
        print(f"[eval] loaded run config for append_id={args.append_id}")
    else:
        model_entries = C.resolve_model(args.model_name)
        # Keep only the endpoints meant for this framework: openhands wants the
        # OPENHANDS_*-routed (litellm) variants; claude-code wants plain Anthropic
        # gateway variants. Fall back to the whole pool when OpenHands can derive
        # its routing from an Anthropic entry.
        if framework == "openhands":
            picked = [e for e in model_entries if "OPENHANDS_MODEL" in e]
        else:
            picked = [e for e in model_entries if "OPENHANDS_MODEL" not in e]
        model_entries = picked or model_entries
        print(f"[model] '{args.model_name}': pool of {len(model_entries)} endpoint(s) "
              f"(framework={framework})")

    # Resolve the Critic Model for metric group (c). Tolerate a missing entry so a
    # run without agentic eval still proceeds (the (c) step is skipped instead).
    # Build ONE shared CriticPool so its round-robin cursor and skip-on-error state
    # persist across every repo in the run.
    args._critic_pool = None
    if getattr(args, "eval", False):
        try:
            entries = C.resolve_critic_model(args.critic_model_name)
            args._critic_pool = CriticPool.from_entries(entries)
            print(f"[critic] pool of {len(entries)} endpoint(s): "
                  f"{[e.label for e in args._critic_pool.endpoints]}")
        except Exception as e:  # noqa: BLE001
            print(f"[warn] critic model '{args.critic_model_name}' unavailable; "
                  f"skipping agentic eval (c): {e}")

    append_id, is_new = ua.mint_or_resume_append_id(
        args.append_id, user_host=args.user_host, user_init_port=args.user_init_port,
        user_model_name=args.user_model_name, query_count=args.query_count,
        difficulty=getattr(args, "difficulty", "normal"),
    ) if not args.only_eval else (args.append_id, False)

    if not append_id:
        raise SystemExit("append_id required (mint a new one or pass --append-id)")
    print(f"append_id = {append_id}  ({'new' if is_new else 'resume'})")

    # --resume-fill treats generation=='running' repos as unfinished and re-generates
    # them. That is only safe if no OTHER orchestrator is still working this id: a live
    # one would share the append_id[:8] container-name suffix and code_path, so the two
    # would collide. Refuse if another orchestrator process holds this id.
    if getattr(args, "resume_fill", False):
        live = _other_live_orchestrators(append_id)
        if live:
            raise SystemExit(
                f"--resume-fill: another orchestrator (pid {', '.join(live)}) is still "
                f"live on append_id {append_id}. Its 'running' repos are in flight and "
                f"share this run's container names/code paths. Wait for it to exit "
                f"(or kill it) before resume-fill, else the two will collide.")

    # Preflight: a generation run expects the agent to clarify with the Oracle, so
    # the append_id MUST be registered there. A resume that reuses an id the Oracle
    # never init'd (the f19f02 incident) otherwise runs every repo with all
    # clarifications silently rejected -> zero interaction data + blind generations.
    # Fail fast instead. Skip for eval-only (no generation/interaction) and when no
    # interaction budget is requested.
    if not args.only_eval and args.query_count > 0:
        ok = await asyncio.to_thread(
            ua.validate_append_id, append_id,
            user_host=args.user_host, user_query_port=args.user_query_port)
        if ok is False:
            raise SystemExit(
                f"append_id {append_id} is NOT registered on the Oracle "
                f"({args.user_host}:{args.user_query_port}) — every interaction "
                f"would be rejected ('invalid append_id'). Start a fresh run "
                f"(drop --append-id to mint a new id) or register this id first.")
        if ok is None:
            print(f"[warn] could not verify append_id with the Oracle "
                  f"({args.user_host}:{args.user_query_port}); proceeding anyway.")

    repos = select_repos(args)
    if not repos:
        if args.only_eval and existing_run is not None:
            raise SystemExit(
                f"run {append_id} has no successfully generated repos to evaluate")
        raise SystemExit("no repos selected (check --repos / --repo-file)")

    if not args.only_eval:
        # Persist enough context to reproduce or resume the run. Secrets and
        # proxy URLs are intentionally excluded.
        ua.init_settings(append_id, {
            "model_name": args.model_name, "env_mode": args.env_mode,
            "eval_mode": getattr(args, "eval_mode", "full"),
            "prd_type": args.prd_type, "user_model_name": args.user_model_name,
            "difficulty": getattr(args, "difficulty", "normal"),
            "critic_model_name": args.critic_model_name,
            "query_count": args.query_count, "user_host": args.user_host,
            "user_init_port": args.user_init_port, "user_query_port": args.user_query_port,
            "user_eval_port": args.user_eval_port,
            "anthropic_model": model_entries[0].get("ANTHROPIC_MODEL"),
            "endpoint_model": (
                model_entries[0].get("OPENHANDS_MODEL")
                or model_entries[0].get("ANTHROPIC_MODEL")
            ),
            "agent_framework": getattr(args, "agent_framework", "claude-code"),
            "selected_repos": repos,
            "requested_repos": args.repos,
            "repo_file": args.repo_file,
            "limit": args.limit,
            "concurrency": args.concurrency,
            "max_turns": args.max_turns,
            "timeout": args.timeout,
            "scaffold": args.scaffold,
            "evaluation_enabled": args.eval,
            "proxy_enabled": bool(args.proxy),
            "proxy_fallback_enabled": bool(args.proxy_fallback_file),
        })
    print(f"selected {len(repos)} repo(s); concurrency={args.concurrency}")

    sem = asyncio.Semaphore(args.concurrency)
    # Each repo starts on one endpoint (round-robin so concurrent generations
    # spread over the available provider tokens); on a transient infra/API error
    # _run_with_backoff rotates to the next endpoint in the pool.
    tasks = [process_repo(r, args, model_entries, append_id, sem, entry_idx=i)
             for i, r in enumerate(repos)]
    t_start = time.time()
    try:
        await asyncio.gather(*tasks)
    finally:
        # Belt-and-suspenders for the per-repo teardown: sweep any container this
        # run left alive (e.g. if gather aborted on an unexpected exception). Scoped
        # by the run's append_id suffix, so a concurrent batch is never touched.
        reaped = docker_env.reap_run_containers(append_id[:8])
        if reaped:
            print(f"[reap] removed {reaped} leftover container(s) for this run")
    run_seconds = round(time.time() - t_start, 1)

    if args.only_eval:
        ua.init_settings(append_id, {
            "last_eval_seconds": run_seconds,
            "last_eval_repos": len(repos),
            "last_eval_concurrency": args.concurrency,
            "last_evaluated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
    else:
        ua.init_settings(append_id, {
            "run_seconds": run_seconds,
            "run_repos": len(repos),
            "run_concurrency": args.concurrency,
            "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
    print(f"\nDONE. append_id={append_id}  wall_time={run_seconds}s "
          f"({len(repos)} repos, concurrency={args.concurrency})")

    # auto-generate the per-repo Markdown summary
    try:
        from . import summarize as summarize_mod
        out = summarize_mod.write_summary(append_id)
        print(f"summary: {out}")
    except Exception as e:  # noqa: BLE001
        print(f"[warn] summary generation failed: {e}")
    print(f"settings: {C.run_settings_path(append_id)}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="ICAE-Bench evaluation harness")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, *, eval_only: bool = False):
        # Fixed release scope. These are internal settings rather than CLI
        # choices because this release only supports base images + fuzzy PRDs.
        sp.set_defaults(env_mode="base", prd_type="fuzzy")
        if not eval_only:
            sp.add_argument("--eval-mode", default="full", choices=["lite", "full"],
                            help="lite = first 50 aliases (smallest golden code); full = all")
            sp.add_argument("--difficulty", default="normal",
                            choices=["normal", "easy", "medium"],
                            help="fuzzy PRD difficulty: normal = fuzzy_prds/, "
                                 "easy = fuzzy_prds_easy/ (simplified PRDs), "
                                 "medium = fuzzy_prds_medium/ (mid-detail PRDs)")
        sp.add_argument("--user-host", default=None if eval_only else "127.0.0.1")
        sp.add_argument("--user-init-port", type=int, default=None if eval_only else 50001)
        sp.add_argument("--user-query-port", type=int, default=None if eval_only else 50002)
        sp.add_argument("--user-eval-port", type=int, default=None if eval_only else 50003,
                        help="User Agent stats port for Interaction Quality (d)")
        sp.add_argument("--critic-model-name",
                        default=None if eval_only else "Deepseek-V4-Flash",
                        help="key in model_list.json['Critic Model'] for Agentic eval (c)")
        sp.add_argument("--append-id", default=None)
        sp.add_argument("--repos", default=None,
                        help="comma-separated aliases (realcode@NNN) or real repo keys")
        sp.add_argument("--repo-file", default=None,
                        help="file with one alias or real repo key per line")
        sp.add_argument("--limit", type=int, default=None)
        sp.add_argument("--concurrency", type=int, default=10)
        sp.add_argument("--proxy", default=None, help="http(s) proxy for in-container installs")
        sp.add_argument("--no-proxy", default=None,
                        help="comma-separated hosts that bypass the proxy "
                             "(default: localhost + the Oracle --user-host)")
        sp.add_argument("--proxy-fallback-file", default=None,
                        help="shell file exporting http(s)_proxy; used ONLY as a "
                             "one-shot retry when a direct (no-proxy) install fails")
        if eval_only:
            sp.add_argument("--reimage", action="store_true",
                            help="ignore the image tag recorded at generation time and "
                                 "reload the fixed base-image tar")
        else:
            sp.add_argument("--query-count", type=int, default=16)
            sp.add_argument("--resume-fill", action="store_true",
                            help="run only unfinished repos; if none remain, retry failures "
                                 "(requires --append-id)")
            sp.add_argument("--max-turns", type=int, default=200)
            sp.add_argument("--timeout", type=float, default=7200)
            sp.add_argument("--force", action="store_true",
                            help="re-generate even if already done")
            sp.add_argument("--scaffold", action="store_true",
                            help="place public test cases in the agent workdir")
            sp.add_argument("--agent-framework", default="claude-code",
                            choices=["claude-code", "openhands"],
                            help="agent engine for generation (default: claude-code)")
            sp.set_defaults(reimage=False)

    r = sub.add_parser("run", help="generate (and optionally evaluate)")
    common(r, eval_only=False)
    r.add_argument("--model-name", required=True, help="key in model_list.json")
    r.add_argument("--user-model-name", default="DeepSeek-V3.2",
                   choices=["Qwen3.5-4B", "Gemini-3.1-Flash-Lite", "DeepSeek-V3.2"],
                   help="User Agent (Oracle) model; synced to the User Agent at "
                        "init so it binds the model to the append_id (default: DeepSeek-V3.2)")
    r.add_argument("--no-eval", dest="eval", action="store_false")
    r.set_defaults(eval=True, only_eval=False)

    e = sub.add_parser("eval", help="re-score an existing append_id")
    common(e, eval_only=True)
    e.set_defaults(eval=True, only_eval=True)
    return p


def main() -> None:
    args = build_parser().parse_args()
    if args.only_eval and not args.append_id:
        raise SystemExit("eval requires --append-id")
    asyncio.run(run_async(args))


if __name__ == "__main__":
    main()
