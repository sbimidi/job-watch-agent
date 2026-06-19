"""
Main entrypoint. Run this on a schedule (e.g. via GitHub Actions cron).

Flow:
  1. Fetch jobs from all configured sources
  2. Filter out jobs we've already seen
  3. Score new jobs against all 3 resumes via Claude
  4. If best score >= threshold, send a WhatsApp notification
  5. Mark all newly-seen jobs as seen (whether notified or not, so we
     don't re-score them every run)
"""

import sys
import config
from fetch_jobs import fetch_all_jobs
from dedup import load_seen_jobs, save_seen_jobs
from score_job import best_match_for_job
from notify import notify_job


def main():
    print("=== Job Watch Agent run started ===")

    seen_ids = load_seen_jobs()
    all_jobs = fetch_all_jobs()

    new_jobs = [j for j in all_jobs if j["id"] not in seen_ids]
    print(f"[main] {len(new_jobs)} new jobs found (out of {len(all_jobs)} fetched)")

    if len(new_jobs) > config.MAX_JOBS_PER_RUN:
        print(
            f"[main] capping this run to {config.MAX_JOBS_PER_RUN} jobs "
            f"(remaining {len(new_jobs) - config.MAX_JOBS_PER_RUN} will be "
            f"picked up on a future run)"
        )
        new_jobs = new_jobs[:config.MAX_JOBS_PER_RUN]

    print(f"[main] evaluating {len(new_jobs)} job(s) this run")

    notified_count = 0
    skipped_for_retry = 0

    for job in new_jobs:
        try:
            match, should_mark_seen = best_match_for_job(job)
        except Exception as e:
            print(f"[main] unexpected error scoring '{job['title']}' @ {job['company']}: {e}")
            print(f"[main] will retry this job next run")
            skipped_for_retry += 1
            continue

        if should_mark_seen:
            seen_ids.add(job["id"])
        else:
            skipped_for_retry += 1

        if not match:
            continue

        print(
            f"[main] '{job['title']}' @ {job['company']} -> "
            f"{match['match_score']}/100 ({match['resume_label']})"
        )

        if match["match_score"] >= config.MATCH_SCORE_THRESHOLD:
            success = notify_job(job, match)
            if success:
                notified_count += 1

    save_seen_jobs(seen_ids)

    print(f"=== Run complete. {notified_count} notification(s) sent. "
          f"{skipped_for_retry} job(s) deferred to next run due to API issues. ===")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[main] FATAL ERROR: {e}")
        sys.exit(1)
