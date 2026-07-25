"""Messaging adapter: enqueue research jobs (SQS in prod, in-memory for dev/tests)."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Protocol


class Queue(Protocol):
    async def enqueue(self, message: dict[str, Any]) -> None: ...


class InMemoryQueue:
    """Captures messages in a list. Used in tests and single-process local dev."""

    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    async def enqueue(self, message: dict[str, Any]) -> None:
        self.messages.append(message)


class SqsQueue:
    """AWS SQS-backed queue. boto3 is imported lazily and calls run off-loop."""

    def __init__(self, queue_url: str, region: str, endpoint_url: str | None) -> None:
        import boto3

        self._url = queue_url
        self._client = boto3.client(
            "sqs", region_name=region, endpoint_url=endpoint_url
        )

    async def enqueue(self, message: dict[str, Any]) -> None:
        body = json.dumps(message)
        await asyncio.to_thread(
            self._client.send_message, QueueUrl=self._url, MessageBody=body
        )


def build_queue(settings) -> Queue:
    if settings.sqs_research_queue_url:
        return SqsQueue(
            queue_url=settings.sqs_research_queue_url,
            region=settings.aws_region,
            endpoint_url=settings.sqs_endpoint_url,
        )
    return InMemoryQueue()
