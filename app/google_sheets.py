"""
Reads submissions from the Google Sheet linked to the Luminarium Google Form.

Column mapping auto-detected from the Sheet header row.
Each submission dict uses normalized snake_case keys.
Unique submission ID = sha256(timestamp + email).
"""
import hashlib
import json
import gspread
from google.oauth2.service_account import Credentials
from app.config import config
from app.logger import process_logger

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# Maps normalized key → possible header substrings (case-insensitive)
FIELD_MAP = {
    "timestamp":         ["timestamp"],
    "email":             ["email"],
    "name":              ["your name", "tell us your name"],
    "linkedin":          ["linkedin"],
    "country_residence": ["country of residence"],
    "country_represent": ["country do you represent"],
    "category":          ["category", "sector", "vertical", "ai agents", "humanoid"],
    "startup_pitch":     ["startup's name and one-sentence", "startup name and one"],
    "problem":           ["problem are you solving"],
    "solution":          ["unique solution or technology"],
    "target_customers":  ["target customers"],
    "wow_factor":        ["wow factor", "makes people say"],
    "business_model":    ["business model", "how do you make money"],
    "traction":          ["traction"],
    "unfair_advantage":  ["unfair advantage"],
    "gtm":               ["go-to-market"],
    "competitors":       ["competitors"],
    "team":              ["founders and key team"],
    "funds_raised":      ["raised any funds"],
    "key_metric":        ["key metric"],
    "biggest_risk":      ["biggest risk"],
    "right_team":        ["right team to solve"],
    "ten_second_pitch":  ["10 seconds", "ten seconds", "10-second"],
    "mvp":               ["mvp", "built or launched"],
    "inspiration":       ["inspires you"],
    "deck_url":          ["upload your deck", "deck"],
}


def _normalize_headers(headers: list[str]) -> dict[str, int]:
    """Return {field_key: column_index} by fuzzy-matching headers to FIELD_MAP."""
    mapping: dict[str, int] = {}
    for idx, header in enumerate(headers):
        h_lower = header.lower().strip()
        for field_key, patterns in FIELD_MAP.items():
            if field_key in mapping:
                continue
            if any(p in h_lower for p in patterns):
                mapping[field_key] = idx
                break
    return mapping


def _submission_id(timestamp: str, email: str) -> str:
    raw = f"{timestamp}|{email}".encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def _get_client() -> gspread.Client:
    creds = Credentials.from_service_account_file(
        config.GOOGLE_SERVICE_ACCOUNT_JSON, scopes=SCOPES
    )
    return gspread.authorize(creds)


def fetch_submissions() -> list[dict]:
    """
    Returns all submissions from the linked Sheet as a list of dicts.
    Each dict has normalized keys + 'submission_id'.
    """
    try:
        client = _get_client()
        sheet = client.open_by_key(config.GOOGLE_SHEET_ID).sheet1
        all_values = sheet.get_all_values()
    except Exception as e:
        process_logger.error(f"Failed to fetch Google Sheet: {e}")
        raise

    if not all_values or len(all_values) < 2:
        process_logger.info("Google Sheet has no data rows.")
        return []

    headers = all_values[0]
    col_map = _normalize_headers(headers)
    process_logger.info(
        f"Sheet has {len(all_values) - 1} rows. Column mapping: "
        + json.dumps({k: headers[v] for k, v in col_map.items()}, indent=None)
    )

    def _get(row: list[str], key: str) -> str:
        idx = col_map.get(key)
        if idx is None or idx >= len(row):
            return ""
        return row[idx].strip()

    submissions = []
    for row in all_values[1:]:
        if not any(cell.strip() for cell in row):
            continue  # skip blank rows

        ts = _get(row, "timestamp")
        email = _get(row, "email")
        sub_id = _submission_id(ts, email)

        sub = {"submission_id": sub_id}
        for key in FIELD_MAP:
            sub[key] = _get(row, key)

        submissions.append(sub)

    return submissions
