"""
Background worker for the /generate-report API.

Flow:
  1. Build a submission dict from the incoming form_data + user_data.
  2. Run the existing analyzer + report generator.
  3. POST the finished HTML back to the caller's callback_url.
  4. On any failure, POST an error indicator instead — so the caller never
     leaves a report stuck in "processing".

The callback POST is retried up to 3 times with exponential backoff.
This worker does NOT touch payment, user accounts, approval, SQLite dedup,
S3, or SendGrid — its only job is: generate → hand back via callback.
"""
import time
import requests
from app import analyzer, report_gen
from app.config import config
from app.logger import process_logger

# Form fields the analyzer reads (same questions as the retired Google Form).
_FORM_FIELDS = [
    "name", "linkedin", "country_residence", "country_represent",
    "category", "startup_pitch", "problem", "solution",
    "target_customers", "wow_factor", "business_model", "traction",
    "unfair_advantage", "gtm", "competitors", "team", "funds_raised",
    "key_metric", "biggest_risk", "right_team", "ten_second_pitch",
    "mvp", "inspiration",
]

_CALLBACK_MAX_ATTEMPTS = 3
_CALLBACK_TIMEOUT = 10          # seconds per attempt
_CALLBACK_BACKOFF_BASE = 2      # 2s, 4s, 8s


def run(report_id: str, form_data: dict, callback_url: str,
        user_data: dict | None = None, payment_data: dict | None = None) -> None:
    """
    Generate a report for one form submission and deliver it via callback.
    Intended to run in a background thread — never raises.
    """
    user_data = user_data or {}
    process_logger.info(f"[api] Generating report | report_id={report_id}")

    try:
        submission = _build_submission(report_id, form_data, user_data)

        analysis = analyzer.analyze(submission)
        process_logger.info(
            f"[api] Analyzed {analysis.get('startup_name', 'Unknown')} "
            f"({analysis['total_score']}/100) | report_id={report_id}"
        )

        report_path = report_gen.generate_individual_report(analysis)
        with open(report_path, encoding="utf-8") as f:
            report_content = f.read()

        process_logger.info(
            f"[api] Report generated ({len(report_content)} bytes) | report_id={report_id}"
        )
        _post_callback(callback_url, report_id, report_content=report_content)

    except Exception as e:
        msg = str(e)
        process_logger.error(f"[api] Generation failed | report_id={report_id} | {msg}")
        _post_callback(callback_url, report_id, error=msg)


def _build_submission(report_id: str, form_data: dict, user_data: dict) -> dict:
    """Map incoming form_data + user_data onto the analyzer's submission shape."""
    submission = {k: form_data.get(k, "Not provided") for k in _FORM_FIELDS}
    submission["submission_id"] = report_id
    # email comes from user_data, falling back to form_data if present
    submission["email"] = user_data.get("email") or form_data.get("email", "")
    # prefer explicit form name, else the account's full name
    if not form_data.get("name"):
        submission["name"] = user_data.get("full_name", "")
    submission["deck_url"] = form_data.get("deck_url", "")
    return submission


def _post_callback(url: str, report_id: str, *,
                   report_content: str | None = None, error: str | None = None) -> bool:
    """
    POST the result to the caller's callback_url with Bearer auth.
    Retries up to 3 times with exponential backoff. Returns True on success.
    """
    if error is not None:
        payload = {"report_id": report_id, "error": error}
        kind = "error"
    else:
        payload = {"report_id": report_id, "report_content": report_content}
        kind = "success"

    headers = {
        "Authorization": f"Bearer {config.AGENT_API_KEY}",
        "Content-Type": "application/json",
    }

    for attempt in range(1, _CALLBACK_MAX_ATTEMPTS + 1):
        try:
            resp = requests.post(url, json=payload, headers=headers,
                                 timeout=_CALLBACK_TIMEOUT)
            if 200 <= resp.status_code < 300:
                process_logger.info(
                    f"[api] Callback {kind} delivered | report_id={report_id} "
                    f"| attempt {attempt} | status {resp.status_code}"
                )
                return True
            process_logger.warning(
                f"[api] Callback {kind} rejected | report_id={report_id} "
                f"| attempt {attempt} | status {resp.status_code} | body={resp.text[:200]}"
            )
        except requests.RequestException as e:
            process_logger.warning(
                f"[api] Callback {kind} POST failed | report_id={report_id} "
                f"| attempt {attempt}/{_CALLBACK_MAX_ATTEMPTS} | {e}"
            )

        if attempt < _CALLBACK_MAX_ATTEMPTS:
            wait = _CALLBACK_BACKOFF_BASE ** attempt      # 2s, 4s
            time.sleep(wait)

    process_logger.error(
        f"[api] Callback {kind} FAILED after {_CALLBACK_MAX_ATTEMPTS} attempts "
        f"| report_id={report_id} | url={url}"
    )
    return False
