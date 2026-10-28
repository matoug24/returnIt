import json
from collections.abc import Callable, Mapping
from typing import Any, Protocol


class SqsClient(Protocol):
    def receive_message(self, **kwargs: object) -> Mapping[str, Any]: ...

    def delete_message(self, **kwargs: object) -> object: ...


class SqsWorker:
    def __init__(self, client: SqsClient, queue_url: str, wait_seconds: int = 20) -> None:
        self.client = client
        self.queue_url = queue_url
        self.wait_seconds = wait_seconds

    def run_once(self, handler: Callable[[Mapping[str, Any]], object]) -> int:
        response = self.client.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=self.wait_seconds,
            AttributeNames=["ApproximateReceiveCount"],
        )
        processed = 0
        for message in response.get("Messages", []):
            body = json.loads(message["Body"])
            handler(body)
            self.client.delete_message(
                QueueUrl=self.queue_url, ReceiptHandle=message["ReceiptHandle"]
            )
            processed += 1
        return processed


def boto3_sqs_client() -> SqsClient:
    import boto3  # type: ignore[import-untyped]

    return boto3.client("sqs")  # type: ignore[no-any-return]
