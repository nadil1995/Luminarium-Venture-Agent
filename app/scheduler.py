"""
APScheduler-based interval runner.
Fires the pipeline every SCHEDULE_INTERVAL_MINUTES minutes (default: 2).
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.config import config
from app.logger import process_logger
from app import pipeline


def _job():
    process_logger.info("Scheduler fired — starting pipeline.")
    try:
        result = pipeline.run_pipeline(trigger="scheduler")
        process_logger.info(f"Scheduled run complete: {result}")
    except Exception as e:
        process_logger.error(f"Scheduled run raised exception: {e}", exc_info=True)


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    interval = config.SCHEDULE_INTERVAL_MINUTES
    scheduler.add_job(
        _job,
        trigger=IntervalTrigger(minutes=interval),
        id="pipeline_job",
        name="Luminarium Pipeline",
        replace_existing=True,
    )
    scheduler.start()
    process_logger.info(f"Scheduler started — polling every {interval} minute(s).")
    return scheduler
