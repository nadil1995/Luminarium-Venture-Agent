"""
AWS S3 storage helpers.
If S3_ENABLED is False (no credentials configured), uploads are skipped
and functions return empty strings — the agent still works fully locally.
"""
import os
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from app.config import config
from app.logger import process_logger


def _client():
    return boto3.client(
        "s3",
        region_name=config.AWS_REGION,
        aws_access_key_id=config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
    )


def upload_report(local_path: str, s3_key: str) -> str:
    """Upload a local file to S3. Returns public-style S3 URI or '' if disabled."""
    if not config.S3_ENABLED:
        process_logger.debug("S3 disabled — skipping upload.")
        return ""
    try:
        _client().upload_file(
            local_path,
            config.S3_BUCKET,
            s3_key,
            ExtraArgs={"ContentType": "text/html"},
        )
        uri = f"s3://{config.S3_BUCKET}/{s3_key}"
        process_logger.info(f"Uploaded to {uri}")
        return uri
    except (BotoCoreError, ClientError) as e:
        process_logger.error(f"S3 upload failed for {s3_key}: {e}")
        return ""


def download_report(s3_key: str, local_path: str) -> bool:
    """Download a file from S3 to local_path. Returns True on success."""
    if not config.S3_ENABLED:
        return False
    try:
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        _client().download_file(config.S3_BUCKET, s3_key, local_path)
        return True
    except (BotoCoreError, ClientError) as e:
        process_logger.error(f"S3 download failed for {s3_key}: {e}")
        return False


def list_reports(prefix: str = "reports/") -> list[str]:
    """List all S3 keys under a prefix."""
    if not config.S3_ENABLED:
        return []
    try:
        resp = _client().list_objects_v2(Bucket=config.S3_BUCKET, Prefix=prefix)
        return [obj["Key"] for obj in resp.get("Contents", [])]
    except (BotoCoreError, ClientError) as e:
        process_logger.error(f"S3 list failed: {e}")
        return []


def upload_log(local_path: str, s3_key: str) -> str:
    """Upload a log file to S3. Returns S3 URI or '' if disabled."""
    if not config.S3_ENABLED:
        return ""
    if not os.path.exists(local_path):
        return ""
    try:
        _client().upload_file(
            local_path,
            config.S3_BUCKET,
            s3_key,
            ExtraArgs={"ContentType": "text/plain"},
        )
        uri = f"s3://{config.S3_BUCKET}/{s3_key}"
        process_logger.info(f"Log uploaded to {uri}")
        return uri
    except (BotoCoreError, ClientError) as e:
        process_logger.error(f"S3 log upload failed for {s3_key}: {e}")
        return ""


def s3_key_for_batch(run_id: str) -> str:
    return f"reports/batch_{run_id}.html"


def s3_key_for_individual(submission_id: str) -> str:
    return f"reports/individual_{submission_id}.html"


def s3_key_for_log(filename: str) -> str:
    return f"logs/{filename}"
