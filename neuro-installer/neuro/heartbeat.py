import time
import psutil
from neuro.logger import get_logger

logger = get_logger("Heartbeat")

def start_heartbeat():
    logger.info("Heartbeat process started.")
    try:
        while True:
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            logger.info(f"System Status - CPU: {cpu}% | RAM: {ram}%")
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Heartbeat stopped.")
