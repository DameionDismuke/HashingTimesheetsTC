import base64
from typing import Any
from unittest.mock import MagicMock

from hashing import (
    create_attachment_hash,
    create_message_hash,
    create_page_hash,
)
from hashing_pipeline import (
    commit_successful_hashes,
    prepare_message_for_llm,
)


def make_message() -> dict[str, str]:
    """
    Return a sample Microsoft Graph message
    used by the hashing pipeline tests.
    """
    return {
        "id": "message-123",
        "receivedDateTime": "2026-09-24T08:00:00Z",
    }


def encode(data: bytes) -> str:
    """
    Convert raw bytes into a Base64 string matching
    Microsoft Graph attachment contentBytes.
    """
    return base64.b64encode(
        data
    ).decode("utf-8")


def unused_pdf_renderer(
    _: bytes,
) -> list[bytes]:
    """
    Placeholder PDF renderer for tests that do not
    actually process a PDF.
    """
    return []


def test_existing_message_is_skipped() -> None:
    store: Any = MagicMock()

    store.hash_exists.return_value = True

    result = prepare_message_for_llm(
        message=make_message(),
        attachments=[],
        hash_store=store,
        render_pdf_pages=unused_pdf_renderer,
    )

    assert result.skip_message is True
    assert result.llm_documents == []
    assert result.pending_hashes == []


def test_new_image_goes_to_llm() -> None:
    store: Any = MagicMock()

    store.hash_exists.return_value = False

    attachment: dict[str, Any] = {
        "id": "attachment-1",
        "name": "timesheet.png",
        "contentType": "image/png",
        "contentBytes": encode(
            b"image bytes"
        ),
    }

    result = prepare_message_for_llm(
        message=make_message(),
        attachments=[attachment],
        hash_store=store,
        render_pdf_pages=unused_pdf_renderer,
    )

    assert result.skip_message is False

    assert len(
        result.llm_documents
    ) == 1

    assert (
        result.llm_documents[0].file_name
        == "timesheet.png"
    )

    assert (
        result.llm_documents[0].content_type
        == "image/png"
    )

    assert (
        result.llm_documents[0].content_bytes
        == b"image bytes"
    )


def test_existing_attachment_is_not_sent_to_llm() -> None:
    store: Any = MagicMock()

    message = make_message()

    message_hash = create_message_hash(
        message
    )

    attachment_content = encode(
        b"image bytes"
    )

    attachment_hash = create_attachment_hash(
        attachment_content
    )

    def exists_side_effect(
        value: str,
    ) -> bool:
        if value == message_hash:
            return False

        if value == attachment_hash:
            return True

        return False

    store.hash_exists.side_effect = (
        exists_side_effect
    )

    attachment: dict[str, Any] = {
        "id": "attachment-1",
        "name": "timesheet.png",
        "contentType": "image/png",
        "contentBytes": attachment_content,
    }

    result = prepare_message_for_llm(
        message=message,
        attachments=[attachment],
        hash_store=store,
        render_pdf_pages=unused_pdf_renderer,
    )

    assert result.skip_message is False
    assert result.llm_documents == []

    # Only the message itself should remain pending.
    assert len(
        result.pending_hashes
    ) == 1

    assert (
        result.pending_hashes[0].hash_type
        == "message"
    )


def test_pdf_only_sends_unseen_pages() -> None:
    store: Any = MagicMock()

    message = make_message()

    pdf_content = encode(
        b"fake pdf bytes"
    )

    page_1 = b"page one"
    page_2 = b"page two"

    existing_page_hash = create_page_hash(
        page_1
    )

    message_hash = create_message_hash(
        message
    )

    pdf_hash = create_attachment_hash(
        pdf_content
    )

    def exists_side_effect(
        value: str,
    ) -> bool:
        if value == message_hash:
            return False

        if value == pdf_hash:
            return False

        if value == existing_page_hash:
            return True

        return False

    store.hash_exists.side_effect = (
        exists_side_effect
    )

    attachment: dict[str, Any] = {
        "id": "pdf-1",
        "name": "timesheet.pdf",
        "contentType": "application/pdf",
        "contentBytes": pdf_content,
    }

    def render_pages(
        _: bytes,
    ) -> list[bytes]:
        return [
            page_1,
            page_2,
        ]

    result = prepare_message_for_llm(
        message=message,
        attachments=[attachment],
        hash_store=store,
        render_pdf_pages=render_pages,
    )

    assert result.skip_message is False

    assert len(
        result.llm_documents
    ) == 1

    document = result.llm_documents[0]

    assert document.page_number == 2
    assert document.file_name == "timesheet.pdf"
    assert document.content_type == "image/png"
    assert document.content_bytes == page_2


def test_hashes_are_not_saved_during_preparation() -> None:
    store: Any = MagicMock()

    store.hash_exists.return_value = False

    attachment: dict[str, Any] = {
        "id": "attachment-1",
        "name": "timesheet.png",
        "contentType": "image/png",
        "contentBytes": encode(
            b"image bytes"
        ),
    }

    result = prepare_message_for_llm(
        message=make_message(),
        attachments=[attachment],
        hash_store=store,
        render_pdf_pages=unused_pdf_renderer,
    )

    # Preparing content for the LLM must never write
    # hashes to Cosmos yet.
    store.save_hash.assert_not_called()

    # One pending message hash
    # + one pending attachment hash.
    assert len(
        result.pending_hashes
    ) == 2


def test_hashes_are_saved_after_success() -> None:
    store: Any = MagicMock()

    store.hash_exists.return_value = False

    attachment: dict[str, Any] = {
        "id": "attachment-1",
        "name": "timesheet.png",
        "contentType": "image/png",
        "contentBytes": encode(
            b"image bytes"
        ),
    }

    result = prepare_message_for_llm(
        message=make_message(),
        attachments=[attachment],
        hash_store=store,
        render_pdf_pages=unused_pdf_renderer,
    )

    # Represents the step that happens only after
    # the extracted information is successfully
    # written to Excel.
    commit_successful_hashes(
        store,
        result.pending_hashes,
    )

    assert store.save_hash.call_count == 2