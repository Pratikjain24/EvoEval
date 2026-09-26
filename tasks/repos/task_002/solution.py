"""Task task_002: Feature implementation."""

import asyncio
from typing import Any, Callable, List, Optional


class BatchPipeline:
    """Asynchronous batch processor with concurrency bounds."""

    def __init__(self, concurrency_limit: int = 5):
        self.concurrency_limit = concurrency_limit
        self._semaphore = asyncio.Semaphore(concurrency_limit)
        self.processed_count = 0

    async def execute_task(self, task_fn: Callable[[], Any]) -> Any:
        async with self._semaphore:
            res = await task_fn() if asyncio.iscoroutinefunction(task_fn) else task_fn()
            self.processed_count += 1
            return res

    async def run_batch(self, items: List[Callable[[], Any]]) -> List[Any]:
        tasks = [self.execute_task(item) for item in items]
        return await asyncio.gather(*tasks)
