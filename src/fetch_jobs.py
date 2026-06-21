"""
Fetches job postings from Greenhouse, Lever, and Adzuna.
Each fetcher returns a list of normalized job dicts:

{
    "id": <unique string, stable across runs>,
    "title": str,
    "company": str,
    "location": str,
    "description": str,
    "url": str,
    "source": "greenhouse" | "lever" | "adzuna",
    "posted_at": datetime or None,
}
"""

from datetime import datetime, timezone, timedelta
import requests
import config


def _parse_adzuna_date(date_str):
    """Adzuna 'created' field looks like '2026-06-18T14:32:10Z'."""
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def fetch_greenhouse_jobs():
    jobs = []
    for slug in config.GREENHOUSE_COMPANIES:
        url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[greenhouse] failed for {slug}: {e}")
            continue

        for job in data.get("jobs", []):
            jobs.append({
                "id": f"greenhouse:{slug}:{job['id']}",
                "title": job.get("title", ""),
                "company": slug,
                "location": (job.get("location") or {}).get("name", ""),
                "description": job.get("content", ""),
                "url": job.get("absolute_url", ""),
                "source": "greenhouse",
                "posted_at": None,  # Greenhouse doesn't expose a reliable post date via this endpoint
            })
    return jobs


def fetch_lever_jobs():
    jobs = []
    for slug in config.LEVER_COMPANIES:
        url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
        try:
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"[lever] failed for {slug}: {e}")
            continue

        for job in data:
            jobs.append({
                "id": f"lever:{slug}:{job['id']}",
                "title": job.get("text", ""),
                "company": slug,
                "location": (job.get("categories") or {}).get("location", ""),
                "description": job.get("descriptionPlain", "") or job.get("description", ""),
                "url": job.get("hostedUrl", ""),
                "source": "lever",
                "posted_at": None,  # not used for age filtering; Greenhouse/Lever currently unused anyway
            })
    return jobs


def fetch_adzuna_jobs():
    if not config.ADZUNA_APP_ID or not config.ADZUNA_APP_KEY:
        print("[adzuna] skipped: no API credentials set")
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(hours=config.MAX_JOB_AGE_HOURS)

    jobs = []
    filtered_old_count = 0

    for keyword in config.ADZUNA_KEYWORDS:
        for location in config.ADZUNA_LOCATIONS:
            url = f"https://api.adzuna.com/v1/api/jobs/{config.ADZUNA_COUNTRY}/search/1"
            params = {
                "app_id": config.ADZUNA_APP_ID,
                "app_key": config.ADZUNA_APP_KEY,
                "what": keyword,
                "results_per_page": config.ADZUNA_RESULTS_PER_PAGE,
                "content-type": "application/json",
                "sort_by": "date",  # newest first, so age cutoff trims efficiently
                "max_days_old": 2,  # coarse pre-filter; precise cutoff applied below
            }
            if location:
                params["where"] = location

            try:
                resp = requests.get(url, params=params, timeout=20)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                loc_label = location or "nationwide"
                print(f"[adzuna] failed for '{keyword}' @ '{loc_label}': {e}")
                continue

            for job in data.get("results", []):
                posted_at = _parse_adzuna_date(job.get("created"))

                # Skip jobs we can't date, or that are older than the cutoff
                if posted_at is None or posted_at < cutoff:
                    filtered_old_count += 1
                    continue

                jobs.append({
                    "id": f"adzuna:{job['id']}",
                    "title": job.get("title", ""),
                    "company": (job.get("company") or {}).get("display_name", ""),
                    "location": (job.get("location") or {}).get("display_name", ""),
                    "description": job.get("description", ""),
                    "url": job.get("redirect_url", ""),
                    "source": "adzuna",
                    "posted_at": posted_at,
                })

    # dedupe across the multiple keyword/location combinations
    seen = set()
    deduped = []
    for job in jobs:
        if job["id"] not in seen:
            seen.add(job["id"])
            deduped.append(job)

    print(f"[adzuna] {len(deduped)} jobs within last {config.MAX_JOB_AGE_HOURS}h "
          f"({filtered_old_count} older jobs filtered out)")

    return deduped


def fetch_all_jobs():
    jobs = []
    jobs.extend(fetch_greenhouse_jobs())
    jobs.extend(fetch_lever_jobs())
    jobs.extend(fetch_adzuna_jobs())
    print(f"[fetch] total jobs collected: {len(jobs)}")
    return jobs
