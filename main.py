from loguru import logger
from pathlib import Path
from api import API
import signal
import sys


def signal_handler(signum, frame):
    print(f"Signal {signum} at {frame.f_code.co_name}:{frame.f_lineno}")
    sys.exit(0)

ek: int # exit key, для передачи кода завершения из API в main.py
logger.remove() 

log_dir = Path(__file__).resolve().parent / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logger.add(
    log_dir / "main.log",
    rotation="10 MB",
    retention="10 days",
    encoding="utf-8",
    level="DEBUG",
)
logger.add(
    sys.stderr,
    format="<level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
)





if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)  
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        api = API()
        ek = api.run() 
        logger.info("Application exited successfully")
        sys.exit(ek)
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"The program unexpectedly terminated with exit code {ek}: {e}")
        sys.exit(1)