import logging

FORMAT = "[%(levelname)s] %(asctime)s | %(message)s"

logger = logging.getLogger("aiocronjob")

logger.setLevel(level="INFO")

handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(FORMAT))
logger.addHandler(handler)
