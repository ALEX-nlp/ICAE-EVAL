"""Critic Model endpoint pool — round-robin dispatch with cooldown-and-revive.

The Critic (Agentic eval, metric group (c)) is configured in model_list.json as a
LIST of interchangeable endpoint variants: the SAME model served by different
providers/tokens (e.g. two app-ids each across a few gateways).
Because they are the same model, spreading calls across them gives ~Nx throughput
with no self-grading bias and full cross-run consistency.

Policy:
  - round-robin over the endpoints;
  - a TRANSIENT failure (429 / timeout / 5xx / "no scores") quarantines the
    endpoint for a short cooldown, after which it is revived and tried again —
    a brief rate-limit must never permanently remove an endpoint;
  - a HARD failure (400 / 401 / 402 / 403 / 404) marks the endpoint permanently
    dead (bad token, no balance, unsupported request);
  - a single call is retried on the next healthy endpoint; when every endpoint is
    momentarily cooling down, run() WAITS for the soonest revival (bounded by
    MAX_WAIT) instead of giving up — so a result still comes out as long as any
    endpoint is recoverable.

The pool is async-safe: acquisition is guarded by an asyncio.Lock so the
orchestrator's per-repo concurrency hands out distinct endpoints cleanly.

`call(entry)` must return a 3-tuple `(status, value, err)` where status is:
  - "ok"    -> success; run() returns (value, label).
  - "retry" -> transient; endpoint cools down RETRY_COOLDOWN and is retried.
  - "dead"  -> hard error; endpoint is removed for the rest of the run.
"""
import asyncio
import time
from dataclasses import dataclass, field

RETRY_COOLDOWN = 45.0   # seconds an endpoint rests after a transient error
MAX_WAIT = 600.0        # max total seconds run() will wait across cooldowns


def _label(entry: dict) -> str:
    model = entry.get("ANTHROPIC_MODEL", "?")
    tok = str(entry.get("ANTHROPIC_AUTH_TOKEN", ""))[-4:]
    return f"{model}#{tok}"


@dataclass
class _Endpoint:
    entry: dict
    label: str
    dead: bool = False      # permanently removed (hard error)
    until: float = 0.0      # monotonic time the cooldown expires (transient)
    uses: int = 0
    fails: int = 0


@dataclass
class CriticPool:
    endpoints: list[_Endpoint] = field(default_factory=list)
    _idx: int = 0
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @classmethod
    def from_entries(cls, entries: list[dict]) -> "CriticPool":
        eps = [_Endpoint(entry=e, label=_label(e)) for e in entries]
        return cls(endpoints=eps)

    def alive_count(self) -> int:
        return sum(1 for e in self.endpoints if not e.dead)

    async def _acquire(self) -> "_Endpoint | None":
        """Round-robin to the next endpoint that is neither dead nor cooling down."""
        async with self._lock:
            now = time.monotonic()
            n = len(self.endpoints)
            for _ in range(n):
                ep = self.endpoints[self._idx % n]
                self._idx += 1
                if not ep.dead and ep.until <= now:
                    ep.uses += 1
                    return ep
            return None

    async def _next_revival(self) -> float | None:
        """Seconds until the soonest cooling-down endpoint revives.

        Returns 0.0 if one is ready now, or None when every endpoint is
        permanently dead (nothing left to wait for).
        """
        async with self._lock:
            now = time.monotonic()
            waits = [max(0.0, ep.until - now) for ep in self.endpoints if not ep.dead]
            if not waits:
                return None
            return min(waits)

    async def _cooldown(self, ep: _Endpoint) -> None:
        async with self._lock:
            ep.until = time.monotonic() + RETRY_COOLDOWN
            ep.fails += 1

    async def _kill(self, ep: _Endpoint) -> None:
        async with self._lock:
            ep.dead = True
            ep.fails += 1

    async def run(self, call):
        """Run `call(entry) -> (status, value, err)` across endpoints.

        status: "ok" -> return (value, label); "retry" -> cool down & try next;
        "dead" -> remove permanently. When all endpoints are momentarily cooling
        down, wait for the soonest revival (bounded by MAX_WAIT). Returns
        (None, errors) only when the pool is exhausted (all dead) or MAX_WAIT is
        hit; `errors` is a dict label->last error for diagnostics.

        `call` may be sync or async, returning a 3-tuple.
        """
        errors: dict[str, str] = {}
        deadline = time.monotonic() + MAX_WAIT
        while True:
            ep = await self._acquire()
            if ep is None:
                wait = await self._next_revival()
                if wait is None:
                    break  # every endpoint permanently dead
                if time.monotonic() + wait > deadline:
                    break  # would exceed the overall wait budget
                await asyncio.sleep(max(0.05, wait))
                continue
            res = call(ep.entry)
            if asyncio.iscoroutine(res):
                res = await res
            status, value, err = res
            if status == "ok":
                return value, ep.label
            errors[ep.label] = err
            if status == "dead":
                await self._kill(ep)
            else:
                await self._cooldown(ep)
        return None, errors

    def stats(self) -> list[dict]:
        return [{"label": e.label, "dead": e.dead, "uses": e.uses, "fails": e.fails}
                for e in self.endpoints]
