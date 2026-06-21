# Job Watch Agent

Automatically scans job postings (via Adzuna, covering Arizona, California,
and remote-tagged US postings), filters to only jobs posted within the last
24 hours, scores each posting against your 2 resumes using Claude,
hard-filters out jobs requiring US citizenship/no-sponsorship or 3+ years
of experience, and sends you a WhatsApp message (via CallMeBot) for any
remaining job scoring **75+/100** match.

> **Note on "match score":** No system can give a true probability of
> landing an interview — that depends on factors outside any resume/job
> description comparison (recruiter judgment, applicant volume, internal
> referrals, etc). What this agent gives you is an honest, LLM-evaluated
> **fit score** based on skills, seniority, and requirements overlap. Treat
> 75+ as "strong enough to prioritize applying immediately," not a guarantee.

> **Eligibility filters:** Configured for an OPT/F-1 candidate seeking
> entry-level roles (0-2 years). Jobs explicitly requiring US citizenship,
> security clearance, "no sponsorship," or 3+ years of experience are
> auto-skipped before scoring even runs — see `REQUIRE_VISA_FRIENDLY` and
> `MAX_YEARS_EXPERIENCE_REQUIRED` in `src/config.py`.

> **Location & recency:** Searches are scoped to Arizona, California, and
> "Remote"-tagged postings (`ADZUNA_LOCATIONS` in `src/config.py`). Note
> Adzuna doesn't have a true remote-work flag — "Remote" as a location
> string only catches postings where the employer wrote "Remote" in the
> location field, which is common but not exhaustive. Jobs older than
> `MAX_JOB_AGE_HOURS` (default 24) are filtered out using Adzuna's
> `created` timestamp before eligibility/scoring even runs.

> **Job sources:** Currently Adzuna only (free API, broad legitimate
> coverage). Greenhouse/Lever company-board support is built in and ready
> to use — just add verified company slugs to `GREENHOUSE_COMPANIES` /
> `LEVER_COMPANIES` in `src/config.py` anytime (note: posted-date filtering
> currently only applies to Adzuna results). LinkedIn and Indeed are
> intentionally NOT included: neither offers a public API for individual
> developers, and scraping either risks violating their ToS and getting
> your personal LinkedIn account flagged or banned.

---

## 1. Setup

### 1.1 Install dependencies (for local testing)
```bash
pip install -r requirements.txt
```

### 1.2 Add your resumes
Replace the placeholder files in `data/resumes/` with your real resume text:
- `data/resumes/fullstack_resume.txt` (Full-Stack / SWE)
- `data/resumes/distributed_systems_resume.txt` (Distributed Systems / Backend)

(Plain text is fine — copy-paste from your Word doc / PDF.)

### 1.3 Configure target companies
Edit `src/config.py`:
- `GREENHOUSE_COMPANIES` — list of Greenhouse board slugs (from
  `boards.greenhouse.io/<slug>`)
- `LEVER_COMPANIES` — list of Lever board slugs (from `jobs.lever.co/<slug>`)
- `ADZUNA_KEYWORDS` — search terms for broader discovery
- `ADZUNA_LOCATION` — defaults to "Phoenix, AZ"
- `MATCH_SCORE_THRESHOLD` — defaults to 85

### 1.4 Get API keys

| Service | Where to get it | Used for |
|---|---|---|
| Anthropic | https://console.anthropic.com | Scoring jobs vs resumes |
| Adzuna | https://developer.adzuna.com/ | Broad job search |
| CallMeBot | WhatsApp setup (already done) | WhatsApp notifications |

### 1.5 Local testing
```bash
cp .env.example .env
# edit .env with your real keys
export $(cat .env | xargs)   # loads env vars into your shell (macOS/Linux)
python src/main.py
```

---

## 2. Deploy to GitHub Actions (runs every 30 min, free)

1. Push this repo to GitHub (private repo recommended, since it'll contain
   your resume content and job search activity)
2. Go to **Settings > Secrets and variables > Actions** and add these
   repository secrets:
   - `ANTHROPIC_API_KEY`
   - `ADZUNA_APP_ID`
   - `ADZUNA_APP_KEY`
   - `CALLMEBOT_PHONE`
   - `CALLMEBOT_APIKEY`
3. The workflow at `.github/workflows/job_watch.yml` will automatically run
   every 30 minutes. You can also trigger it manually from the **Actions**
   tab → **Job Watch Agent** → **Run workflow**.

---

## 3. How it works

```
GitHub Actions (cron, every 30 min)
  -> fetch_jobs.py        pulls from Greenhouse / Lever / Adzuna
  -> dedup.py              filters out jobs already seen (data/seen_jobs.json)
  -> score_job.py          Claude scores job vs all 3 resumes, picks best
  -> notify.py             if best score >= threshold, sends WhatsApp via CallMeBot
  -> commits updated seen_jobs.json back to the repo
```

## 4. Files

| File | Purpose |
|---|---|
| `src/config.py` | All settings: resumes, companies, threshold, API keys |
| `src/fetch_jobs.py` | Pulls jobs from Greenhouse/Lever/Adzuna |
| `src/score_job.py` | Scores jobs against resumes via Claude |
| `src/notify.py` | Sends WhatsApp messages via CallMeBot |
| `src/dedup.py` | Tracks which jobs have already been processed |
| `src/main.py` | Orchestrates the full pipeline |
| `.github/workflows/job_watch.yml` | Scheduled automation |

## 5. Known limitations

- **CallMeBot is a free, unofficial service** — not guaranteed uptime/SLA.
  If WhatsApp messages stop arriving, check the CallMeBot bot's WhatsApp
  chat for any "paused" notices (occasionally need to send "resume").
- **LinkedIn and Indeed are not included** — neither has a stable, ToS-safe
  API for individual developers. Greenhouse/Lever (direct company boards)
  and Adzuna are used instead.
- **GitHub Actions cron is "best effort"** — under high load, scheduled
  runs can be delayed by several minutes. For job alerts this is generally
  fine.
- **Match scores are not probabilities of getting an interview** — see the
  note at the top of this file.
