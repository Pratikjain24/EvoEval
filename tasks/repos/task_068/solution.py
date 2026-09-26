"""Task task_068: Refactoring to async/await and modular generators."""

import asyncio
from typing import AsyncGenerator, Iterable, List


async def async_data_stream(items: Iterable[int]) -> AsyncGenerator[int, None]:
    """Yield items asynchronously without blocking."""
    for item in items:
        await asyncio.sleep(0.001)
        yield item * 2


async def collect_stream(items: Iterable[int]) -> List[int]:
    """Collect all streamed items into a list."""
    out = []
    async for x in async_data_stream(items):
        out.append(x)
    return out
