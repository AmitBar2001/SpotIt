import logging
from app.config import settings

# --- Logging Setup ---
logging.basicConfig(
    level=logging.getLevelNamesMapping()[settings.log_level],
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)
