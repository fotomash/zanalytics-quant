import logging
import time
from typing import List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorizationService:
    """Simple service that converts incoming messages to vectors."""

    def __init__(self) -> None:
        self._running = False

    # Startup method: initialize resources
    def startup(self) -> None:
        """Prepare the service for processing messages."""
        logger.info("Starting VectorizationService...")
        self._running = True

    # Shutdown method: cleanup
    def shutdown(self) -> None:
        """Clean up resources before shutting down."""
        logger.info("Shutting down VectorizationService...")
        self._running = False

    # Process message method
    def process_message(self, message: str) -> List[int]:
        """Convert a message into a list of character codes.

        Args:
            message: Text message to vectorize.
        Returns:
            List of integer code points representing the message.
        """
        try:
            logger.debug("Vectorizing message: %s", message)
            return [ord(ch) for ch in message]
        except Exception as exc:  # pragma: no cover - log and re-raise
            logger.error("Failed to vectorize message: %s", exc)
            raise

    # Main run loop
    def run(self) -> None:
        """Run the service until interrupted."""
        self.startup()
        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt, shutting down...")
        finally:
            self.shutdown()


if __name__ == "__main__":
    service = VectorizationService()
    service.run()
