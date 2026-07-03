import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise EnvironmentError(f"Required environment variable missing: {key}")
    return val


class Config:
    # Google Sheets
    GOOGLE_SHEET_ID: str = _require("GOOGLE_SHEET_ID")
    GOOGLE_SERVICE_ACCOUNT_JSON: str = _require("GOOGLE_SERVICE_ACCOUNT_JSON")

    # OpenAI
    OPENAI_API_KEY: str = _require("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

    # AWS S3 (supports both AWS_S3_BUCKET/AWS_S3_REGION and S3_BUCKET/AWS_REGION)
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_S3_REGION") or os.getenv("AWS_REGION", "us-east-1")
    S3_BUCKET: str = os.getenv("AWS_S3_BUCKET") or os.getenv("S3_BUCKET", "")
    S3_ENABLED: bool = bool(
        os.getenv("AWS_ACCESS_KEY_ID") and
        (os.getenv("AWS_S3_BUCKET") or os.getenv("S3_BUCKET"))
    )

    # Scheduler — interval in minutes (default 2)
    SCHEDULE_INTERVAL_MINUTES: int = int(os.getenv("SCHEDULE_INTERVAL_MINUTES", "2"))
    # Google Sheets polling scheduler — disabled in API mode (in-house form calls the API)
    SCHEDULER_ENABLED: bool = os.getenv("SCHEDULER_ENABLED", "false").lower() == "true"

    # Paths
    DB_PATH: str = os.getenv("DB_PATH", "/data/luminarium.db")
    REPORTS_DIR: str = os.getenv("REPORTS_DIR", "/reports")
    LOGS_DIR: str = os.getenv("LOGS_DIR", "/data/logs")

    # Web
    WEB_PORT: int = int(os.getenv("WEB_PORT", "5050"))
    WEB_SECRET_KEY: str = os.getenv("WEB_SECRET_KEY", "dev-secret-key")

    # Agent API — shared secret for the User Management app (Bearer auth on
    # POST /generate-report and on the outgoing callback POST)
    AGENT_API_KEY: str = os.getenv("AGENT_API_KEY", "")

    # SendGrid notifications (optional — disabled if key not set)
    # NOTIFY_EMAIL_TO accepts comma-separated addresses: a@x.com,b@x.com
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
    NOTIFY_EMAIL_TO: list[str] = [
        e.strip() for e in os.getenv("NOTIFY_EMAIL_TO", "").split(",") if e.strip()
    ]
    NOTIFY_EMAIL_FROM: str = os.getenv("NOTIFY_EMAIL_FROM", "")
    NOTIFY_ENABLED: bool = bool(
        os.getenv("SENDGRID_API_KEY") and
        os.getenv("NOTIFY_EMAIL_TO") and
        os.getenv("NOTIFY_EMAIL_FROM")
    )


config = Config()
