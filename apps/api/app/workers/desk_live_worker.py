"""Background ticker for live desk sessions.

Run it as its own process next to the API (for example a second Railway service):

    python -m app.workers.desk_live_worker

Every 30 seconds it ticks each active live session: fetches any newly closed
5-minute bars, recomputes the day, and sends due notifications. Without it,
sessions still advance whenever someone has the desk open, but checkpoint
notifications only go out while a browser is polling.
"""

import logging
import time

from app.services import desk_live_service

TICK_SECONDS = 30
logger = logging.getLogger("desk_live_worker")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("Live desk worker started; ticking every %s seconds.", TICK_SECONDS)
    while True:
        try:
            checked = desk_live_service.tick_all()
            if checked:
                logger.info("Checked %s live session(s).", checked)
        except Exception:  # noqa: BLE001 - keep the loop alive through transient failures
            logger.exception("Live desk tick loop failed")
        time.sleep(TICK_SECONDS)


if __name__ == "__main__":
    main()
