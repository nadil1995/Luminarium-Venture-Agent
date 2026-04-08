"""
Two named loggers:
  process_logger    — scheduler runs, pipeline events, errors  → process.log
  submission_logger — per-submission analysis events           → submissions.log
Both also write to stdout.
"""
import logging
import os
from app.config import config


def _make_logger(name: str, filename: str) -> logging.Logger:
    os.makedirs(config.LOGS_DIR, exist_ok=True)
    log_path = os.path.join(config.LOGS_DIR, filename)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(fmt)

    sh = logging.StreamHandler()
    sh.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


process_logger = _make_logger("process", "process.log")
submission_logger = _make_logger("submissions", "submissions.log")
