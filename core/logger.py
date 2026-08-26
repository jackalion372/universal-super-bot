import logging
import sys

def setup_logger():
    # UTF-8 stdout wrapper on Windows
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("UniversalSuperBot")

logger = setup_logger()
