"""
Tracks which job IDs we've already processed, so we don't re-notify on
every run. Stored as a flat JSON list, capped to avoid unbounded growth.
"""

import json
import os
import config

MAX_STORED = 5000


def load_seen_jobs() -> set:
    if not os.path.exists(config.SEEN_JOBS_PATH):
        return set()
    try:
        with open(config.SEEN_JOBS_PATH, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception as e:
        print(f"[dedup] failed to load seen_jobs.json: {e}")
        return set()


def save_seen_jobs(seen_ids: set):
    ids_list = list(seen_ids)
    if len(ids_list) > MAX_STORED:
        # keep only the most recently added MAX_STORED (approx, since sets
        # are unordered we just truncate arbitrarily - fine for dedup purposes)
        ids_list = ids_list[-MAX_STORED:]
    os.makedirs(os.path.dirname(config.SEEN_JOBS_PATH), exist_ok=True)
    with open(config.SEEN_JOBS_PATH, "w", encoding="utf-8") as f:
        json.dump(ids_list, f)
