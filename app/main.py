"""
Main entry point for the agent container.
Starts the scheduler and the Flask web server together.
"""
import threading
from app import db
from app.scheduler import start_scheduler
from app.web.server import create_app
from app.config import config
from app.logger import process_logger


def main():
    process_logger.info("Luminarium Venture IQ Agent starting…")
    db.init_db()
    process_logger.info("Database initialised.")

    scheduler = start_scheduler()

    app = create_app()

    def run_flask():
        process_logger.info(f"Web UI available at http://0.0.0.0:{config.WEB_PORT}")
        app.run(host="0.0.0.0", port=config.WEB_PORT, use_reloader=False)

    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    try:
        flask_thread.join()
    except (KeyboardInterrupt, SystemExit):
        process_logger.info("Shutting down scheduler…")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
