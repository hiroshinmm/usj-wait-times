import logging
import time
from datetime import datetime, timezone

import requests
import schedule

from config import API_BASE_URL, POLL_INTERVAL_SEC, USJ_ENTITY_ID
from database import init_db, insert_batch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def fetch_and_store() -> None:
    url = f"{API_BASE_URL}/entity/{USJ_ENTITY_ID}/live"
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        logger.error("API fetch failed: %s", e)
        return

    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    records = []

    for item in data.get("liveData", []):
        if item.get("entityType") not in ("ATTRACTION", "SHOW"):
            continue

        wait_minutes = None
        queue = item.get("queue") or {}
        standby = queue.get("STANDBY") or {}
        if standby:
            wait_minutes = standby.get("waitTime")

        records.append(
            {
                "attraction_id": item["id"],
                "attraction_name": item["name"],
                "wait_minutes": wait_minutes,
                "status": item.get("status", "UNKNOWN"),
                "fetched_at": fetched_at,
            }
        )

    if records:
        insert_batch(records)
        operating = sum(1 for r in records if r["status"] == "OPERATING")
        logger.info("Saved %d records (%d operating) at %s", len(records), operating, fetched_at)
    else:
        logger.warning("No records to save at %s", fetched_at)


def main() -> None:
    init_db()
    logger.info("Database initialized. Starting collector (interval: %ds)...", POLL_INTERVAL_SEC)

    fetch_and_store()

    schedule.every(POLL_INTERVAL_SEC).seconds.do(fetch_and_store)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
