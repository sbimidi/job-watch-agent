"""
Scores a job posting against each of your resumes using Claude, and picks
the single best-fit resume + score. Returns None if scoring fails or no
resume is a good fit.
"""

import json
import os
import re
import time
import anthropic
import config

# Retry settings for transient Anthropic API errors (529 overloaded, etc.)
MAX_RETRIES = 4
RETRY_BASE_DELAY_SECONDS = 5  # doubles each retry: 5s, 10s, 20s, 40s


def _load_resumes():
    resumes = []
    for r in config.RESUMES:
        path = os.path.join(config.RESUME_DIR, r["file"])
        if not os.path.exists(path):
            print(f"[score] WARNING: resume file missing: {path}")
            continue
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        resumes.append({"id": r["id"], "label": r["label"], "text": text})
    return resumes


_RESUMES_CACHE = None


def get_resumes():
    global _RESUMES_CACHE
    if _RESUMES_CACHE is None:
        _RESUMES_CACHE = _load_resumes()
    return _RESUMES_CACHE


SYSTEM_PROMPT = """You are a strict, honest technical recruiter assistant. \
You will be given a job posting and a candidate's resume. Your job is to \
evaluate realistically how strong a match the candidate is for this specific \
role, based ONLY on what's in the resume and job description.

Score honestly. A 90+ score should be rare and reserved for cases where the \
candidate's actual skills, experience level, and background closely match \
what the job is asking for. Do not inflate scores. Penalize heavily for:
- seniority mismatches (e.g. job wants 5+ years, candidate is a student/new grad)
- missing required/core technologies
- visa/work-authorization requirements the candidate likely can't meet, IF stated in the posting

Respond with ONLY valid JSON, no markdown fences, no preamble:
{
  "match_score": <integer 0-100>,
  "key_strengths": ["short phrase", "short phrase"],
  "key_gaps": ["short phrase", "short phrase"],
  "reasoning": "1-2 sentence explanation"
}
"""

ELIGIBILITY_SYSTEM_PROMPT = """You are screening a job posting for hard \
eligibility blockers for a specific candidate. The candidate is an \
international student on F-1/OPT status (NOT a US citizen or green card \
holder), and is an entry-level candidate (0-2 years of professional \
experience).

Read the job posting and determine if either of these hard blockers apply:

1. CITIZENSHIP_REQUIRED: The posting explicitly requires US citizenship, a \
   green card, permanent residency, or states it cannot sponsor / will not \
   consider visa candidates (e.g. "must be a US citizen", "no sponsorship \
   available", "active security clearance required", "ITAR/export-control \
   restricted to US persons"). General EEO boilerplate or routine "must be \
   authorized to work in the US" language does NOT count as a blocker by \
   itself, since OPT provides US work authorization — only flag this if the \
   posting goes further and excludes visa/sponsorship candidates specifically.

2. EXPERIENCE_TOO_SENIOR: The posting explicitly requires more than 2 years \
   of professional experience (e.g. "3+ years", "5+ years required", \
   "Senior", "Staff", "Lead" roles with seniority requirements). If the \
   posting doesn't specify years or says "0-2", "entry-level", "new grad", \
   or similar, this is NOT a blocker.

Respond with ONLY valid JSON, no markdown fences, no preamble:
{
  "citizenship_blocker": true/false,
  "experience_blocker": true/false,
  "reason": "1 short sentence explaining any blocker found, or 'none' if eligible"
}
"""


def _extract_json(text):
    text = text.strip()
    text = re.sub(r"^```json\s*|\s*```$", "", text.strip())
    return json.loads(text)


def _call_claude_with_retry(client, **kwargs):
    """
    Wraps client.messages.create() with retry + exponential backoff for
    transient errors (529 overloaded, rate limits, connection errors).
    Raises the final exception if all retries are exhausted.
    """
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            return client.messages.create(**kwargs)
        except (anthropic.InternalServerError, anthropic.RateLimitError,
                anthropic.APIConnectionError) as e:
            last_error = e
            delay = RETRY_BASE_DELAY_SECONDS * (2 ** attempt)
            print(f"[claude] transient error ({type(e).__name__}), "
                  f"retry {attempt + 1}/{MAX_RETRIES} in {delay}s: {e}")
            time.sleep(delay)
        except Exception as e:
            # Non-transient error (bad request, auth failure, etc.) - don't retry
            raise
    # All retries exhausted
    raise last_error


def check_eligibility(job, client):
    """
    Hard pre-filter: returns (is_eligible: bool, reason: str).
    Runs BEFORE detailed resume scoring to save API calls on jobs that are
    auto-disqualified regardless of how well the resume matches.
    """
    if not config.REQUIRE_VISA_FRIENDLY and config.MAX_YEARS_EXPERIENCE_REQUIRED is None:
        return True, "eligibility checks disabled"

    user_prompt = f"""JOB POSTING
Title: {job['title']}
Company: {job['company']}
Description:
{job['description'][:6000]}
"""

    try:
        response = _call_claude_with_retry(
            client,
            model=config.ANTHROPIC_MODEL,
            max_tokens=200,
            system=ELIGIBILITY_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw_text = "".join(
            block.text for block in response.content if block.type == "text"
        )
        parsed = _extract_json(raw_text)
    except Exception as e:
        print(f"[eligibility] check failed after retries, SKIPPING job (fail-safe): {e}")
        return False, f"eligibility check failed after retries: {e}"

    if config.REQUIRE_VISA_FRIENDLY and parsed.get("citizenship_blocker"):
        return False, parsed.get("reason", "citizenship/sponsorship blocker")

    if config.MAX_YEARS_EXPERIENCE_REQUIRED is not None and parsed.get("experience_blocker"):
        return False, parsed.get("reason", "requires too many years of experience")

    return True, "eligible"


def score_job_against_resume(job, resume, client):
    user_prompt = f"""JOB POSTING
Title: {job['title']}
Company: {job['company']}
Location: {job.get('location', 'N/A')}
Description:
{job['description'][:6000]}

---

CANDIDATE RESUME ({resume['label']}):
{resume['text'][:6000]}
"""

    response = _call_claude_with_retry(
        client,
        model=config.ANTHROPIC_MODEL,
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw_text = "".join(
        block.text for block in response.content if block.type == "text"
    )

    try:
        parsed = _extract_json(raw_text)
        return {
            "resume_id": resume["id"],
            "resume_label": resume["label"],
            "match_score": int(parsed["match_score"]),
            "key_strengths": parsed.get("key_strengths", []),
            "key_gaps": parsed.get("key_gaps", []),
            "reasoning": parsed.get("reasoning", ""),
        }
    except Exception as e:
        print(f"[score] failed to parse model output: {e}\nRaw: {raw_text[:300]}")
        return None


def best_match_for_job(job):
    """
    Runs eligibility checks first (citizenship/sponsorship, experience level).
    If the job fails eligibility, returns None immediately (no scoring done,
    saves API calls). Otherwise scores `job` against all configured resumes,
    returns the best result dict, or None if none could be scored.

    Returns a tuple: (result_dict_or_None, should_mark_seen: bool)
    should_mark_seen is False only when a persistent API failure occurred,
    so the job gets retried on the next run instead of being permanently
    skipped due to a transient outage.
    """
    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    is_eligible, reason = check_eligibility(job, client)
    if not is_eligible:
        if "failed after retries" in reason:
            # API outage during eligibility check - don't burn this job, retry later
            print(f"[score] '{job['title']}' @ {job['company']} -> eligibility check "
                  f"failed after retries, will retry next run")
            return None, False
        print(f"[score] SKIPPED (ineligible): '{job['title']}' @ {job['company']} -> {reason}")
        return None, True

    resumes = get_resumes()
    if not resumes:
        print("[score] no resumes loaded, skipping")
        return None, True

    results = []
    had_failure = False
    for resume in resumes:
        try:
            result = score_job_against_resume(job, resume, client)
            if result:
                results.append(result)
        except Exception as e:
            print(f"[score] scoring failed after retries for resume "
                  f"'{resume['label']}' on '{job['title']}': {e}")
            had_failure = True

    if not results:
        if had_failure:
            # all scoring attempts hit persistent API errors - retry next run
            return None, False
        return None, True

    best = max(results, key=lambda r: r["match_score"])
    return best, True
