import mmh3


def get_server_index(key: str, num_servers: int) -> int:
    """
    Determines the server index for a given UUID key using consistent hashing.

    Args:
        key (str): key string (e.g., 'd689a52b-6abe-48cd-b1b3-4c3dc7518145')
        num_servers (int): Number of available servers

    Returns:
        int: Index of the server to store the data (0 to num_servers-1)

    Raises:
        ValueError: If num_servers is less than 1
    """
    if num_servers < 1:
        raise ValueError("Number of servers must be at least 1")

    hash_value = mmh3.hash(key)

    hash_value = hash_value & 0xFFFFFFFF

    return hash_value % num_servers
