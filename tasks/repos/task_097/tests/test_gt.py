import asyncio
import pytest
from solution import BatchPipeline

@pytest.mark.asyncio
async def test_gt_concurrency_stress():
    pipeline = BatchPipeline(concurrency_limit=2)
    active = 0
    max_active = 0
    async def worker():
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        return True

    res = await pipeline.run_batch([worker for _ in range(10)])
    assert len(res) == 10
    assert max_active <= 2
