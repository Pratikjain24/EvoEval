import asyncio
import pytest
from solution import BatchPipeline

@pytest.mark.asyncio
async def test_batch_pipeline_execution():
    pipeline = BatchPipeline(concurrency_limit=3)
    results = await pipeline.run_batch([lambda: i * 2 for i in range(5)])
    assert results == [0, 2, 4, 6, 8]
    assert pipeline.processed_count == 5
