from typing import Any


class InMemoryHashStore:
    """
    Development-only hash store.

    Mimics the CosmosHashStore interface without
    requiring Azure credentials.
    """

    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}

    def hash_exists(
        self,
        hash_value: str,
    ) -> bool:
        return hash_value in self._items

    def save_hash(
        self,
        hash_value: str,
        hash_type: str,
        **metadata: Any,
    ) -> dict[str, Any]:
        item: dict[str, Any] = {
            "id": hash_value,
            "hash": hash_value,
            "type": hash_type,
            **metadata,
        }

        self._items[hash_value] = item

        return item

    def count(self) -> int:
        return len(self._items)