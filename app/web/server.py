"""
Flask web UI.
Routes:
  GET  /                     dashboard (recent runs + quick stats)
  GET  /reports              list all processed submissions + batch reports
  GET  /reports/<sid>        serve individual HTML report
  GET  /reports/batch/<rid>  serve batch HTML report
  GET  /logs                 process + submission logs
  POST /run                  trigger manual pipeline run (JSON response)
  POST /regenerate/<sid>     force-reprocess one submission (JSON response)
"""
import os
import threading
from flask import Flask, render_template, jsonify, abort, send_file, request
from app import db, pipeline
from app.config import config
from app.logger import process_logger


def create_app() -> Flask:
    template_dir = os.path.join(os.path.dirname(__file__), "templates")
    app = Flask(__name__, template_folder=template_dir)
    app.secret_key = config.WEB_SECRET_KEY

    _running_run: dict = {}

    def _async_run(trigger: str, force_ids: list[str] | None = None):
        try:
            result = pipeline.run_pipeline(trigger=trigger, force_ids=force_ids)
            _running_run.update(result)
        except Exception as e:
            _running_run.update({"status": "error", "error": str(e)})

    # ── Dashboard ──────────────────────────────────────────────────────────────
    @app.route("/")
    def index():
        db.init_db()
        runs = db.get_runs(limit=10)
        processed = db.get_all_processed(limit=5)
        schedule_hours = config.SCHEDULE_HOURS
        return render_template(
            "index.html",
            runs=runs,
            processed=processed,
            schedule_hours=schedule_hours,
        )

    # ── Reports list ───────────────────────────────────────────────────────────
    @app.route("/reports")
    def reports():
        db.init_db()
        processed = db.get_all_processed(limit=200)
        runs = db.get_runs(limit=50)
        batch_runs = [r for r in runs if r.get("batch_report_path")]
        return render_template("reports.html", processed=processed, batch_runs=batch_runs)

    # ── Serve individual report ────────────────────────────────────────────────
    @app.route("/reports/<sid>")
    def report_individual(sid: str):
        path = os.path.join(config.REPORTS_DIR, f"individual_{sid}.html")
        if not os.path.exists(path):
            abort(404)
        return send_file(path, mimetype="text/html")

    # ── Serve batch report ─────────────────────────────────────────────────────
    @app.route("/reports/batch/<run_id>")
    def report_batch(run_id: str):
        path = os.path.join(config.REPORTS_DIR, f"batch_{run_id}.html")
        if not os.path.exists(path):
            abort(404)
        return send_file(path, mimetype="text/html")

    # ── Logs ───────────────────────────────────────────────────────────────────
    @app.route("/logs")
    def logs():
        run_id = request.args.get("run_id")
        process_lines = _read_log("process.log", tail=200)
        submission_lines = _read_log("submissions.log", tail=200)
        submission_events = db.get_submission_events(run_id=run_id, limit=200)
        runs = db.get_runs(limit=30)
        return render_template(
            "logs.html",
            process_lines=process_lines,
            submission_lines=submission_lines,
            submission_events=submission_events,
            runs=runs,
            selected_run=run_id,
        )

    # ── Manual run (async, returns immediately) ────────────────────────────────
    @app.route("/run", methods=["POST"])
    def manual_run():
        _running_run.clear()
        _running_run["status"] = "started"
        t = threading.Thread(target=_async_run, args=("manual",), daemon=True)
        t.start()
        process_logger.info("Manual run triggered from web UI.")
        return jsonify({"status": "started", "message": "Pipeline running in background."})

    # ── Regenerate single submission ───────────────────────────────────────────
    @app.route("/regenerate/<sid>", methods=["POST"])
    def regenerate(sid: str):
        _running_run.clear()
        _running_run["status"] = "started"
        t = threading.Thread(
            target=_async_run, args=("manual", [sid]), daemon=True
        )
        t.start()
        process_logger.info(f"Regenerate triggered from web UI for {sid}.")
        return jsonify({
            "status": "started",
            "message": f"Regenerating submission {sid} in background."
        })

    # ── Run status (poll) ──────────────────────────────────────────────────────
    @app.route("/run-status")
    def run_status():
        return jsonify(_running_run or {"status": "idle"})

    return app


def _read_log(filename: str, tail: int = 200) -> list[str]:
    path = os.path.join(config.LOGS_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    return [l.rstrip() for l in lines[-tail:]]


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=config.WEB_PORT, debug=True)
