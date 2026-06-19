"""
Central configuration for the Job Watch Agent.
Edit RESUMES, GREENHOUSE_COMPANIES, LEVER_COMPANIES, and ADZUNA_KEYWORDS
to match your job search.
"""

import os

# ---------------------------------------------------------------------------
# Resumes
# ---------------------------------------------------------------------------
# Each resume is plain text (extracted from your .docx/.pdf). We keep them
# as separate files in data/resumes/ so they're easy to update without
# touching code. The "label" is what gets shown in the WhatsApp message.

RESUME_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "resumes")

RESUMES = [
    {"id": "fullstack", "label": "Full-Stack / SWE Resume", "file": "fullstack_resume.txt"},
    {"id": "aiml", "label": "AI/ML Engineer Resume", "file": "aiml_resume.txt"},
]

# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------
# Minimum score (0-100) required before a WhatsApp notification fires.
MATCH_SCORE_THRESHOLD = 70

# ---------------------------------------------------------------------------
# Eligibility filters (hard filters, checked BEFORE detailed scoring)
# ---------------------------------------------------------------------------
# Candidate is on F-1/OPT and needs employers open to visa sponsorship.
# Jobs requiring "US Citizens only", active security clearance, or explicitly
# refusing visa sponsorship are auto-rejected regardless of match score.
REQUIRE_VISA_FRIENDLY = True

# Only consider entry-level roles. Jobs explicitly requiring 3+ years of
# experience are auto-rejected regardless of match score.
MAX_YEARS_EXPERIENCE_REQUIRED = 2

# ---------------------------------------------------------------------------
# Job sources: Greenhouse / Lever company board slugs (OPTIONAL)
# ---------------------------------------------------------------------------
# Currently empty — Adzuna alone is the active job source for now. Add
# company slugs here anytime to expand coverage; no code changes needed.
#
# Greenhouse API:  https://boards-api.greenhouse.io/v1/boards/{slug}/jobs
# Lever API:       https://api.lever.co/v0/postings/{slug}?mode=json
#
# Find a company's slug by checking their careers page URL, e.g.:
#   boards.greenhouse.io/stripe          -> slug = "stripe"
#   jobs.lever.co/netflix                -> slug = "netflix"
# Verify a slug works by pasting the API URL above into your browser —
# you should see JSON with a "jobs" array, not an error page.

GREENHOUSE_COMPANIES = [
    # "stripe",
    # "airbnb",
    # "doordash",
]

LEVER_COMPANIES = [
    # "netflix",
    # "palantir",
]

# ---------------------------------------------------------------------------
# Adzuna search (primary job source)
# ---------------------------------------------------------------------------
ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")
ADZUNA_COUNTRY = "us"

ADZUNA_KEYWORDS = [
    "entry level software engineer",
    "junior software engineer",
    "full stack developer",
    "backend developer",
    "AI engineer",
    "machine learning engineer",
    "software engineer new grad",
]

ADZUNA_LOCATIONS = [
    "Phoenix, AZ",
    "",  # empty = nationwide search, surfaces remote + broad US postings
]
ADZUNA_RESULTS_PER_PAGE = 20

# ---------------------------------------------------------------------------
# Notifications (CallMeBot WhatsApp)
# ---------------------------------------------------------------------------
CALLMEBOT_PHONE = os.environ.get("CALLMEBOT_PHONE", "")   # your number, e.g. +16025551234
CALLMEBOT_APIKEY = os.environ.get("CALLMEBOT_APIKEY", "")

# ---------------------------------------------------------------------------
# Anthropic (for scoring)
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = "claude-sonnet-4-6"

# ---------------------------------------------------------------------------
# Dedup storage
# ---------------------------------------------------------------------------
SEEN_JOBS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "seen_jobs.json")

# Safety cap: max number of NEW jobs evaluated in a single run. Prevents
# runaway run times (e.g. first-ever run with a large backlog, or an Adzuna
# search returning unusually many results). Any jobs beyond this cap are
# left unmarked (not added to seen_jobs.json) so they'll simply be picked
# up and evaluated on the next scheduled run instead.
MAX_JOBS_PER_RUN = 40
