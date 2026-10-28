import logging
import time

from .config import get_settings
from .db import SessionLocal
from .domain import process_outbox_batch
from .queue import SqsWorker, boto3_sqs_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("returnet.worker")


def run_once() -> int:
    with SessionLocal() as db:
        return process_outbox_batch(db)


def main() -> None:
    settings = get_settings()
    sqs = (
        SqsWorker(boto3_sqs_client(), settings.sqs_queue_url, settings.sqs_wait_seconds)
        if settings.queue_mode == "sqs"
        else None
    )
    logger.info("Returnet worker started mode=%s", settings.queue_mode)
    while True:
        processed = sqs.run_once(lambda _message: run_once()) if sqs else run_once()
        time.sleep(0.2 if processed else 2.0)


if __name__ == "__main__":
    main()
