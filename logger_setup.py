import sys
from pathlib import Path

from loguru import logger


def setup_logging() -> None:
    log_dir = Path.home() / ".skyfall" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.remove()

    logger.add(
        log_dir / "skyfall_{time:YYYY-MM-DD}.log",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        rotation="10 MB",
        retention="30 days",
        compression="gz",
        level="DEBUG",
        enqueue=True,
        backtrace=True,
        diagnose=True,
    )

    logger.add(
        sys.stderr,
        colorize=True,
        format=(
            "<green>{time:HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        ),
        level="DEBUG",
        enqueue=True,
    )
