"""
Main pipeline orchestrator.

run_pipeline(trigger, force_ids)
  1. Fetch all submissions from Google Sheet
  2. Filter out already-processed (unless in force_ids)
  3. Analyze each new submission with OpenAI
  4. Generate individual HTML report per submission
  5. Generate batch HTML report for the whole run
  6. Upload everything to S3
  7. Persist state to SQLite
  8. Log everything

force_ids: list of submission_ids to reprocess even if already done
"""
import os
import uuid
from datetime import datetime
from app import db, analyzer, report_gen, storage
from app.google_sheets import fetch_submissions
from app.logger import process_logger, submission_logger


def run_pipeline(trigger: str = "scheduler", force_ids: list[str] | None = None) -> dict:
    """
    Execute the full pipeline.
    Returns a summary dict with run_id, counts, report paths.
    """
    force_ids = set(force_ids or [])
    run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]

    process_logger.info(f"=== Pipeline start | run_id={run_id} | trigger={trigger} ===")
    db.init_db()
    db.create_run(run_id, trigger)

    # ── 1. Fetch submissions ───────────────────────────────────────────────────
    try:
        all_submissions = fetch_submissions()
    except Exception as e:
        msg = f"Google Sheets fetch failed: {e}"
        process_logger.error(msg)
        db.finish_run(run_id, status="error", error_message=msg)
        return {"run_id": run_id, "status": "error", "error": msg}

    process_logger.info(f"Fetched {len(all_submissions)} total submission(s) from Sheet.")

    # ── 2. Filter new vs already processed ────────────────────────────────────
    new_submissions = []
    skipped = 0
    for sub in all_submissions:
        sid = sub["submission_id"]
        if sid not in force_ids and db.is_processed(sid):
            skipped += 1
            db.log_submission_event(run_id, sid, sub.get("startup_pitch", "")[:60], "skipped")
            submission_logger.info(f"Skipped (already processed): {sid}")
        else:
            new_submissions.append(sub)

    process_logger.info(
        f"{len(new_submissions)} new submission(s) to process, {skipped} skipped."
    )

    if not new_submissions:
        db.finish_run(run_id, status="success", new_count=0, skipped_count=skipped)
        process_logger.info("No new submissions. Run complete.")
        return {
            "run_id": run_id,
            "status": "success",
            "new_count": 0,
            "skipped_count": skipped,
        }

    # ── 3 & 4. Analyze + generate individual reports ──────────────────────────
    analyses = []
    errors = []
    for sub in new_submissions:
        sid = sub["submission_id"]
        startup_label = sub.get("startup_pitch", "Unknown")[:60]
        try:
            submission_logger.info(f"Processing: {startup_label} ({sid})")
            db.log_submission_event(run_id, sid, startup_label, "analyzing")

            analysis = analyzer.analyze(sub)
            db.log_submission_event(run_id, sid, analysis.get("startup_name", startup_label), "analyzed",
                                    f"score={analysis['total_score']}")

            # Individual report
            ind_path = report_gen.generate_individual_report(analysis)
            ind_s3 = storage.upload_report(ind_path, storage.s3_key_for_individual(sid))
            analysis["individual_report_path"] = ind_path
            analysis["individual_s3_url"] = ind_s3

            db.log_submission_event(run_id, sid, analysis.get("startup_name", startup_label),
                                    "report_generated", ind_path)

            # Mark processed
            db.mark_processed(
                submission_id=sid,
                timestamp=sub.get("timestamp", ""),
                submitter_name=sub.get("name", ""),
                startup_name=analysis.get("startup_name", startup_label),
                email=sub.get("email", ""),
                run_id=run_id,
                report_path=ind_path,
                s3_url=ind_s3,
            )
            analyses.append(analysis)

        except Exception as e:
            msg = str(e)
            process_logger.error(f"Error processing {sid}: {msg}")
            submission_logger.error(f"Error: {sid} — {msg}")
            db.log_submission_event(run_id, sid, startup_label, "error", msg)
            errors.append({"submission_id": sid, "error": msg})

    # ── 5. Batch report ────────────────────────────────────────────────────────
    batch_path = ""
    batch_s3 = ""
    if analyses:
        try:
            batch_path = report_gen.generate_batch_report(analyses, run_id)
            batch_s3 = storage.upload_report(batch_path, storage.s3_key_for_batch(run_id))
            process_logger.info(f"Batch report: {batch_path}")
        except Exception as e:
            process_logger.error(f"Batch report generation failed: {e}")

    # ── 6. Finish run ──────────────────────────────────────────────────────────
    status = "success" if not errors else ("partial" if analyses else "error")
    db.finish_run(
        run_id=run_id,
        status=status,
        new_count=len(analyses),
        skipped_count=skipped,
        error_message="; ".join(e["error"] for e in errors),
        batch_report_path=batch_path,
        batch_s3_url=batch_s3,
    )

    process_logger.info(
        f"=== Pipeline done | run_id={run_id} | status={status} | "
        f"analyzed={len(analyses)} | skipped={skipped} | errors={len(errors)} ==="
    )

    # ── 7. Upload logs to S3 ───────────────────────────────────────────────────
    from app.config import config
    for log_file in ("process.log", "submissions.log"):
        local_log = os.path.join(config.LOGS_DIR, log_file)
        storage.upload_log(local_log, storage.s3_key_for_log(log_file))

    return {
        "run_id": run_id,
        "status": status,
        "new_count": len(analyses),
        "skipped_count": skipped,
        "error_count": len(errors),
        "batch_report_path": batch_path,
        "batch_s3_url": batch_s3,
        "individual_reports": [
            {
                "submission_id": a["submission_id"],
                "startup_name": a.get("startup_name", ""),
                "total_score": a.get("total_score", 0),
                "report_path": a.get("individual_report_path", ""),
            }
            for a in analyses
        ],
    }


def regenerate(submission_id: str) -> dict:
    """Force reprocess a single submission by its ID."""
    process_logger.info(f"Manual regenerate requested for submission_id={submission_id}")
    db.unmark_processed(submission_id)
    return run_pipeline(trigger="manual", force_ids=[submission_id])
