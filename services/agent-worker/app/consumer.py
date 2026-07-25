"""SQS consumer: the worker's production entry point.

Long-polls the research queue, runs the graph, persists results, and deletes the
message on success. Failures leave the message to reappear after the visibility
timeout; the queue's redrive policy routes poison messages to the DLQ.

Idempotency: a Redis ``SET NX`` lock on ``request_id`` prevents double-processing on
SQS redelivery. Without Redis configured it falls back to an in-process set (single
worker only) — acceptable for local dev, not for the fleet.
"""

from __future__ import annotations

import json
import logging

from .config import Settings, get_settings
from .graph import Deps, build_deps
from .runner import run_analysis

logger = logging.getLogger("aegis.worker.consumer")


class _InProcessLock:
    def __init__(self) -> None:
        self._seen: set[str] = set()

    def acquire(self, key: str, ttl: int) -> bool:
        if key in self._seen:
            return False
        self._seen.add(key)
        return True


class SqsConsumer:
    def __init__(self, settings: Settings | None = None, deps: Deps | None = None) -> None:
        self.settings = settings or get_settings()
        self.deps = deps or build_deps(self.settings)
        self._lock = self._build_lock()
        self._sqs = None  # lazily created boto3 client
        if self.settings.database_url:
            from .persistence import DbPersistence

            self.deps.persistence = DbPersistence(self.settings.database_url)

    def _build_lock(self):
        if self.settings.redis_url:
            try:
                import redis

                client = redis.Redis.from_url(self.settings.redis_url)

                class _RedisLock:
                    def acquire(self, key: str, ttl: int) -> bool:
                        return bool(client.set(f"lock:{key}", "1", nx=True, ex=ttl))

                return _RedisLock()
            except Exception:  # pragma: no cover
                logger.warning("Redis unavailable; using in-process idempotency lock")
        return _InProcessLock()

    def _client(self):
        if self._sqs is None:
            import boto3

            self._sqs = boto3.client(
                "sqs",
                region_name=self.settings.aws_region,
                endpoint_url=self.settings.sqs_endpoint_url,
            )
        return self._sqs

    async def process_message(self, body: str) -> None:
        payload = json.loads(body)
        request_id = payload["request_id"]
        if not self._lock.acquire(request_id, self.settings.sqs_visibility_timeout):
            logger.info("Skipping duplicate delivery for %s", request_id)
            return
        await run_analysis(
            ticker=payload["ticker"],
            deps=self.deps,
            request_id=request_id,
            enable_debate=payload.get("enable_debate", True),
            max_debate_rounds=payload.get("max_debate_rounds"),
        )
        logger.info("Completed analysis for %s (%s)", payload["ticker"], request_id)

    async def poll_forever(self) -> None:  # pragma: no cover - needs live AWS
        queue_url = self.settings.sqs_research_queue_url
        if not queue_url:
            raise RuntimeError("SQS_RESEARCH_QUEUE_URL not configured")
        client = self._client()
        logger.info("Polling %s", queue_url)
        while True:
            resp = client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=5,
                WaitTimeSeconds=self.settings.sqs_wait_seconds,
                VisibilityTimeout=self.settings.sqs_visibility_timeout,
            )
            for msg in resp.get("Messages", []):
                try:
                    await self.process_message(msg["Body"])
                    client.delete_message(
                        QueueUrl=queue_url, ReceiptHandle=msg["ReceiptHandle"]
                    )
                except Exception:
                    logger.exception("Processing failed; message will be redelivered")
