from loguru import logger
from pathlib import Path
from api import API
from db import Database
import signal
import sys


def signal_handler(signum, frame):
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

logger.remove() 
log_dir = Path(__file__).resolve().parent / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logger.add(
    log_dir / "main.log",
    rotation="10 MB",
    retention="10 days",
    encoding="utf-8",
    level="DEBUG",
    mode="w",
)

logger.add(
    sys.stderr,
    format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
)
logger.info("Logger initialized successfully")
logger.info("Application starting...")

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)  
    signal.signal(signal.SIGTERM, signal_handler)
    ek = 1  # Default exit code for unexpected termination
    try:
        db = Database()
        api = API(db)  
        ek = api.run() 
        db.close() 
        logger.info("Application exited successfully")
        sys.exit(ek)

    except Exception as e:
        logger.error(f"The program unexpectedly terminated with exit code {ek}: {e}")
        sys.exit(1)