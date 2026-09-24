from unittest.mock import MagicMock

import pytest
from azure.cosmos.exceptions import (
    CosmosResourceNotFoundError,
)

from cosmos_hash_store import CosmosHashStore
from typing import Any

def return_item(
    item: dict[str, Any],
) -> dict[str, Any]:
    return item

def create_store():
    client = MagicMock()
    container = MagicMock()

    store = CosmosHashStore(
        client=client,
        container=container,
    )

    return store, container


def test_existing_hash_returns_true():
    store, container = create_store()

    container.read_item.return_value = {
        "id": "abc123"
    }

    result = store.hash_exists(
        "abc123"
    )

    assert result is True

    container.read_item.assert_called_once_with(
        item="abc123",
        partition_key="abc123",
    )


def test_missing_hash_returns_false():
    store, container = create_store()

    container.read_item.side_effect = (
        CosmosResourceNotFoundError(
            status_code=404,
            message="Not found",
        )
    )

    result = store.hash_exists(
        "does-not-exist"
    )

    assert result is False


def test_save_hash_writes_expected_item():
    store, container = create_store()

    container.upsert_item.side_effect = return_item

    result = store.save_hash(
        "hash123",
        "attachment",
        fileName="timesheet.pdf",
        messageHash="message456",
    )

    assert result["id"] == "hash123"
    assert result["hash"] == "hash123"
    assert result["type"] == "attachment"
    assert result["status"] == "excel_saved"

    assert (
        result["fileName"]
        == "timesheet.pdf"
    )

    assert (
        result["messageHash"]
        == "message456"
    )

    assert "processedAt" in result


def test_empty_hash_is_rejected():
    store, _ = create_store()

    with pytest.raises(ValueError):
        store.hash_exists("")


def test_empty_hash_type_is_rejected():
    store, _ = create_store()

    with pytest.raises(ValueError):
        store.save_hash(
            "abc123",
            "",
        )