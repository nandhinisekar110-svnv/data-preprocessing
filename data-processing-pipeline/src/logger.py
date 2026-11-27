"""Logging setup: console + optional file."""
import logging
from pathlib import Path


def setup_logging(cfg: dict | None = None) -> logging.Logger:
    cfg = cfg or {}
    level = getattr(logging, str(cfg.get("level", "INFO")).upper(), logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")

    logger = logging.getLogger("pipeline")
    logger.setLevel(level)
    logger.handlers.clear()

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    log_file = cfg.get("file")
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
    return logger
