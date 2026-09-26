import pytest
from solution import collect_stream

@pytest.mark.asyncio
async def test_collect_stream():
    res = await collect_stream([1, 2, 3])
    assert res == [2, 4, 6]
