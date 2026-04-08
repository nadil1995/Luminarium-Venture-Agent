"""
CLI entry point for manual operations.

Usage (inside container or locally):
  python app/cli.py run                          # run pipeline now
  python app/cli.py regenerate <submission_id>   # force-reprocess one submission
  python app/cli.py list                         # list processed submissions
  python app/cli.py runs                         # list recent pipeline runs
  python app/cli.py status                       # show last run status
"""
import sys
import json
from app import db, pipeline
from app.logger import process_logger


def cmd_run():
    print("Starting manual pipeline run...")
    result = pipeline.run_pipeline(trigger="cli")
    print(json.dumps(result, indent=2))


def cmd_regenerate(submission_id: str):
    print(f"Regenerating submission: {submission_id}")
    result = pipeline.regenerate(submission_id)
    print(json.dumps(result, indent=2))


def cmd_list():
    db.init_db()
    records = db.get_all_processed()
    if not records:
        print("No processed submissions yet.")
        return
    print(f"{'ID':<18} {'Startup':<30} {'Submitter':<20} {'Score':<8} {'Processed At'}")
    print("-" * 90)
    for r in records:
        print(f"{r['submission_id']:<18} {r['startup_name'][:28]:<30} "
              f"{r['submitter_name'][:18]:<20} {'—':<8} {r['processed_at'][:19]}")


def cmd_runs():
    db.init_db()
    runs = db.get_runs()
    if not runs:
        print("No runs recorded yet.")
        return
    print(f"{'Run ID':<25} {'Trigger':<12} {'Status':<10} {'New':<5} {'Skip':<5} {'Started'}")
    print("-" * 80)
    for r in runs:
        print(f"{r['run_id']:<25} {r['trigger']:<12} {r['status']:<10} "
              f"{r['new_count']:<5} {r['skipped_count']:<5} {r['started_at'][:19]}")


def cmd_status():
    db.init_db()
    runs = db.get_runs(limit=1)
    if not runs:
        print("No runs yet.")
        return
    r = runs[0]
    print(json.dumps(r, indent=2))


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return

    cmd = args[0]
    if cmd == "run":
        cmd_run()
    elif cmd == "regenerate":
        if len(args) < 2:
            print("Usage: python app/cli.py regenerate <submission_id>")
            sys.exit(1)
        cmd_regenerate(args[1])
    elif cmd == "list":
        cmd_list()
    elif cmd == "runs":
        cmd_runs()
    elif cmd == "status":
        cmd_status()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
