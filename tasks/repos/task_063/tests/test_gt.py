import pytest
from solution import async_data_stream

@pytest.mark.asyncio
async def test_gt_stream_generation():
    count = 0
    async for val in async_data_stream(range(50)):
        count += 1
    assert count == 50
