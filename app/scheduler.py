"""
APScheduler-based cron runner.
Fires the pipeline at each hour listed in SCHEDULE_HOURS (UTC).
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
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
    hours = ",".join(str(h) for h in config.SCHEDULE_HOURS)
    scheduler.add_job(
        _job,
        trigger=CronTrigger(hour=hours, minute=0, timezone="UTC"),
        id="pipeline_job",
        name="Luminarium Pipeline",
        replace_existing=True,
    )
    scheduler.start()
    process_logger.info(f"Scheduler started — will run at UTC hours: {hours}")
    return scheduler
