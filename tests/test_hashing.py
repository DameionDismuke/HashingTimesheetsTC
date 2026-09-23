import base64

import pytest

from hashing import (
    create_attachment_hash,
    create_message_hash,
    create_page_hash,
    decode_base64_content,
    sha256_bytes,
)


def test_message_hash_is_deterministic():
    message = {
        "id": "message-123",
        "receivedDateTime":
            "2026-09-23T12:00:00Z",
    }

    first = create_message_hash(message)
    second = create_message_hash(message)

    assert first == second
    assert len(first) == 64


def test_different_message_ids_get_different_hashes():
    first = {
        "id": "message-123",
        "receivedDateTime":
            "2026-09-23T12:00:00Z",
    }

    second = {
        "id": "message-456",
        "receivedDateTime":
            "2026-09-23T12:00:00Z",
    }

    assert (
        create_message_hash(first)
        != create_message_hash(second)
    )


def test_different_timestamps_get_different_hashes():
    first = {
        "id": "message-123",
        "receivedDateTime":
            "2026-09-23T12:00:00Z",
    }

    second = {
        "id": "message-123",
        "receivedDateTime":
            "2026-09-23T13:00:00Z",
    }

    assert (
        create_message_hash(first)
        != create_message_hash(second)
    )


def test_base64_decodes_original_bytes():
    original = b"example timesheet contents"

    encoded = base64.b64encode(
        original
    ).decode("utf-8")

    assert decode_base64_content(encoded) == original


def test_attachment_hash_is_deterministic():
    original = b"approved timesheet"

    encoded = base64.b64encode(
        original
    ).decode("utf-8")

    first = create_attachment_hash(encoded)
    second = create_attachment_hash(encoded)

    assert first == second
    assert len(first) == 64


def test_different_attachments_get_different_hashes():
    first = base64.b64encode(
        b"timesheet one"
    ).decode("utf-8")

    second = base64.b64encode(
        b"timesheet two"
    ).decode("utf-8")

    assert (
        create_attachment_hash(first)
        != create_attachment_hash(second)
    )


def test_page_hash_is_deterministic():
    page = b"rendered pdf page bytes"

    first = create_page_hash(page)
    second = create_page_hash(page)

    assert first == second
    assert len(first) == 64


def test_empty_data_is_rejected():
    with pytest.raises(ValueError):
        sha256_bytes(b"")