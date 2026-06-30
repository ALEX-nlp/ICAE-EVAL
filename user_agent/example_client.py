"""Example of how the test harness drives the three services.

Ports:
  50001 — Init:         mint an append_id (requires secret key + model)
  50002 — Interaction:  ask clarifying questions (agent under test)
  50003 — Stats:        query metrics for an append_id

Init parameters:
  - key:              required, secret key
  - model:            required, must be a key in user_model.json
  - max_interactions: optional, default 16
  - difficulty:       optional, "normal" (default), "medium", or "easy"
                      "medium" uses prd_json_medium/
                      "easy" uses prd_json_easy/ which contains simplified PRDs
  - open_access:      optional, bool, default false
                      if true, the Oracle also has access to the golden repo source
                      code and may answer questions not covered by oracle_data,
                      as long as no interaction rules are violated

Run `python main.py` in another terminal first.
"""

import requests

HOST       = "127.0.0.1"
INIT_URL   = f"http://{HOST}:50001/"
CHAT_URL   = f"http://{HOST}:50002/"
STATS_URL  = f"http://{HOST}:50003/"
SECRET_KEY = "zVtwLTkCKwoCWq4Jq9D2"


def main():
    # ── Example 1: medium difficulty, open_access off (default) ──────────────
    init = requests.post(INIT_URL, json={
        "key":              SECRET_KEY,
        "model":            "Gemini-3.5-Flash",
        "max_interactions": 16,
        "difficulty":       "medium",
        # "open_access":    False,       # default
    }).json()
    print("init (medium) ->", init["status"])

    if not init["status"]["ok"]:
        print("Init failed:", init["status"]["error"])
        return

    append_id = init["append_id"]

    # ── Example 2: easy difficulty, open_access on ────────────────────────────
    init_easy = requests.post(INIT_URL, json={
        "key":              SECRET_KEY,
        "model":            "Gemini-3.5-Flash",
        "max_interactions": 16,
        "difficulty":       "easy",
        "open_access":      True,
    }).json()
    print("init (easy + open_access) ->", init_easy["status"])

    # ── Example 3: normal difficulty (default) ────────────────────────────────
    init_normal = requests.post(INIT_URL, json={
        "key":              SECRET_KEY,
        "model":            "Gemini-3.5-Flash",
        "max_interactions": 16,
        # "difficulty":     "normal",   # default
    }).json()
    print("init (normal default) ->", init_normal["status"])

    # ── Interaction ───────────────────────────────────────────────────────────
    questions = [
        "What is the exact exponential back-off formula for the next retry time?",
        "What database engine should I use?",  # off-topic -> fallback_response
    ]
    for q in questions:
        resp = requests.post(CHAT_URL, json={
            "append_id": append_id,
            "task_id":   "realcode@001",
            "question":  q,
        }).json()
        print(f"\nQ: {q}\nA: {resp['data']}\nstatus: {resp['status']}")

    # ── Stats (aggregate) ─────────────────────────────────────────────────────
    print("\n--- Stats (aggregate) ---")
    stats = requests.post(STATS_URL, json={"append_id": append_id}).json()
    s = stats["stats"]
    print(f"repos              : {s['repos']}")
    print(f"budget_usage_rate  : {s['budget_usage_rate']}%")
    print(f"fallback_rate      : {s['fallback_rate']}%")
    print(f"constraint_coverage: {s['constraint_coverage']}%")
    print(f"interaction_score  : {s['interaction_score']:+d}")

    # ── Stats (single task) ───────────────────────────────────────────────────
    print("\n--- Stats (single task) ---")
    stats2 = requests.post(STATS_URL, json={
        "append_id": append_id,
        "task_id":   "realcode@001",
    }).json()
    print(stats2["stats"])


if __name__ == "__main__":
    main()
