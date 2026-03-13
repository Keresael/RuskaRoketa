import logging
import twitchio



LOGGER: logging.Logger = logging.getLogger("Bot")
twitchio.utils.setup_logging(level=logging.INFO)