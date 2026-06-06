# -*- coding: UTF-8 -*-
"""
Simple async send queue with worker pool, basic rate-limiting and anti-spam.

Usage:
  queue = SendQueue(send_callable, worker_count=4, rate_limit=1.0)
  await queue.start()
  await queue.enqueue(target_id, payload)

- `send_callable` should be a coroutine function or regular callable that
  accepts (target_id, payload) and performs the actual send.

This file is intentionally lightweight and designed to be integrated
into existing `ZaloAPI` instances without changing public APIs.
"""
import asyncio
import time
from collections import deque, defaultdict
from typing import Any, Callable, Coroutine


class SendQueue:
    def __init__(self, send_callable: Callable, worker_count: int = 4, rate_limit: float = 1.0, spam_limit: int = 5, spam_window: int = 10):
        """Create a SendQueue.

        Args:
            send_callable: coroutine or callable(target_id, payload)
            worker_count: number of worker coroutines to run
            rate_limit: minimum seconds between messages globally (float)
            spam_limit: number of allowed sends per-target in spam_window
            spam_window: time window in seconds for spam detection
        """
        self._send = send_callable
        self._queue = asyncio.Queue()
        self._worker_count = max(1, worker_count)
        self._rate_limit = float(rate_limit)
        self._last_sent = 0.0
        self._workers = []
        self._stopped = False

        # anti-spam: map target -> deque[timestamps]
        self._sent_history = defaultdict(deque)
        self._spam_limit = int(spam_limit)
        self._spam_window = int(spam_window)

        # simple lock for rate limiting
        self._lock = asyncio.Lock()

    async def start(self):
        self._stopped = False
        for _ in range(self._worker_count):
            w = asyncio.create_task(self._worker())
            self._workers.append(w)

    async def stop(self):
        self._stopped = True
        # wake workers
        for _ in range(len(self._workers)):
            await self._queue.put((None, None, None))
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()

    async def enqueue(self, target: Any, payload: Any, metadata: dict = None):
        """Enqueue a message to be sent.

        `target` is used for spam protection indexing.
        """
        await self._queue.put((target, payload, metadata or {}))

    async def _worker(self):
        while True:
            target, payload, metadata = await self._queue.get()
            if self._stopped and target is None:
                break

            try:
                # Basic anti-spam per-target
                now = time.time()
                hist = self._sent_history[target]

                # purge old entries
                while hist and now - hist[0] > self._spam_window:
                    hist.popleft()

                if len(hist) >= self._spam_limit:
                    # Too many messages to this target recently; drop or delay
                    # We choose to delay a little to avoid immediate drop
                    await asyncio.sleep(self._spam_window / 2)

                # Rate limit globally
                async with self._lock:
                    elapsed = now - self._last_sent
                    if elapsed < self._rate_limit:
                        await asyncio.sleep(self._rate_limit - elapsed)
                    self._last_sent = time.time()

                # execute send
                if asyncio.iscoroutinefunction(self._send):
                    await self._send(target, payload, metadata)
                else:
                    # run in executor to avoid blocking loop
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, self._send, target, payload, metadata)

                # record history
                self._sent_history[target].append(time.time())

            except Exception:
                # swallow errors; user-level code should handle logging
                pass
            finally:
                self._queue.task_done()

    async def join(self):
        await self._queue.join()


__all__ = ("SendQueue",)
