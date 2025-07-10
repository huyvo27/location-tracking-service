import uuid

import pytest

from app.utils.consistent_hash import get_server_index


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "key,num_servers,expected_range",
    [
        (str(uuid.uuid4()), 5, range(5)),
        (str(uuid.uuid4()), 3, range(3)),
        (str(uuid.uuid4()), 10, range(10)),
    ],
)
async def test_get_server_index_valid(key, num_servers, expected_range):
    index = get_server_index(key, num_servers)
    assert isinstance(index, int)
    assert index in expected_range


@pytest.mark.asyncio
async def test_get_server_index_invalid_num_servers():
    with pytest.raises(ValueError, match="Number of servers must be at least 1"):
        get_server_index(str(uuid.uuid4()), 0)


@pytest.mark.asyncio
async def test_get_server_index_deterministic():
    key = str(uuid.uuid4())
    num_servers = 4

    index1 = get_server_index(key, num_servers)
    index2 = get_server_index(key, num_servers)

    assert index1 == index2  # Hashing must be consistent


@pytest.mark.asyncio
async def test_get_server_index_large_number_of_servers():
    key = str(uuid.uuid4())
    num_servers = 1_000_000
    index = get_server_index(key, num_servers)

    assert 0 <= index < num_servers
