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
}
"""

import requests
import config


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
            })
    return jobs


def fetch_adzuna_jobs():
    if not config.ADZUNA_APP_ID or not config.ADZUNA_APP_KEY:
        print("[adzuna] skipped: no API credentials set")
        return []

    jobs = []
    for keyword in config.ADZUNA_KEYWORDS:
        for location in config.ADZUNA_LOCATIONS:
            url = f"https://api.adzuna.com/v1/api/jobs/{config.ADZUNA_COUNTRY}/search/1"
            params = {
                "app_id": config.ADZUNA_APP_ID,
                "app_key": config.ADZUNA_APP_KEY,
                "what": keyword,
                "results_per_page": config.ADZUNA_RESULTS_PER_PAGE,
                "content-type": "application/json",
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
                jobs.append({
                    "id": f"adzuna:{job['id']}",
                    "title": job.get("title", ""),
                    "company": (job.get("company") or {}).get("display_name", ""),
                    "location": (job.get("location") or {}).get("display_name", ""),
                    "description": job.get("description", ""),
                    "url": job.get("redirect_url", ""),
                    "source": "adzuna",
                })

    # dedupe across the multiple keyword/location combinations
    seen = set()
    deduped = []
    for job in jobs:
        if job["id"] not in seen:
            seen.add(job["id"])
            deduped.append(job)

    return deduped


def fetch_all_jobs():
    jobs = []
    jobs.extend(fetch_greenhouse_jobs())
    jobs.extend(fetch_lever_jobs())
    jobs.extend(fetch_adzuna_jobs())
    print(f"[fetch] total jobs collected: {len(jobs)}")
    return jobs
