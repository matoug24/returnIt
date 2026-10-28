from collections.abc import Mapping
from typing import Any

import pytest

from backend.app.queue import SqsWorker


class FakeSqs:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    def receive_message(self, **_kwargs: object) -> Mapping[str, Any]:
        return {"Messages": [{"Body": '{"type":"work"}', "ReceiptHandle": "receipt-1"}]}

    def delete_message(self, **kwargs: object) -> object:
        self.deleted.append(str(kwargs["ReceiptHandle"]))
        return {}


def test_sqs_worker_deletes_only_after_success() -> None:
    client = FakeSqs()
    worker = SqsWorker(client, "https://sqs.invalid/test", wait_seconds=0)
    assert worker.run_once(lambda message: message["type"]) == 1
    assert client.deleted == ["receipt-1"]

    client.deleted.clear()
    with pytest.raises(RuntimeError):
        worker.run_once(lambda _message: (_ for _ in ()).throw(RuntimeError("retry")))
    assert client.deleted == []
