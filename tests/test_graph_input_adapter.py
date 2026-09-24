import base64
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock

from PIL import Image

from graph_input_adapter import (
    get_message_attachments,
    is_graph_file_attachment,
    is_supported_attachment,
    process_graph_messages,
)


def make_png_bytes() -> bytes:
    image = Image.new(
        "RGB",
        (10, 10),
        "white",
    )

    buffer = BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    return buffer.getvalue()


def encode(data: bytes) -> str:
    return base64.b64encode(
        data
    ).decode("utf-8")


def make_message() -> dict[str, Any]:
    return {
        "id": "message-123",
        "internetMessageId":
            "<message-123@example.com>",
        "receivedDateTime":
            "2026-09-24T10:00:00Z",
        "subject":
            "Approved Timesheet",
        "hasAttachments": True,
    }


def test_graph_file_attachment_is_accepted() -> None:
    attachment = {
        "@odata.type":
            "#microsoft.graph.fileAttachment",
        "contentBytes": "abc",
    }

    assert (
        is_graph_file_attachment(
            attachment
        )
        is True
    )


def test_graph_item_attachment_is_rejected() -> None:
    attachment = {
        "@odata.type":
            "#microsoft.graph.itemAttachment",
        "contentBytes": "abc",
    }

    assert (
        is_graph_file_attachment(
            attachment
        )
        is False
    )


def test_pdf_is_supported() -> None:
    attachment = {
        "name": "timesheet.pdf",
        "contentType":
            "application/pdf",
    }

    assert (
        is_supported_attachment(
            attachment
        )
        is True
    )


def test_image_is_supported() -> None:
    attachment = {
        "name": "timesheet.png",
        "contentType": "image/png",
    }

    assert (
        is_supported_attachment(
            attachment
        )
        is True
    )


def test_text_file_is_rejected() -> None:
    attachment = {
        "name": "notes.txt",
        "contentType": "text/plain",
    }

    assert (
        is_supported_attachment(
            attachment
        )
        is False
    )


def test_message_receives_only_supported_attachments() -> None:
    message = make_message()

    image_bytes = make_png_bytes()

    attachments = {
        "message-123": [
            {
                "@odata.type":
                    "#microsoft.graph.fileAttachment",
                "id": "image-1",
                "name": "timesheet.png",
                "contentType": "image/png",
                "contentBytes":
                    encode(image_bytes),
            },
            {
                "@odata.type":
                    "#microsoft.graph.fileAttachment",
                "id": "text-1",
                "name": "notes.txt",
                "contentType":
                    "text/plain",
                "contentBytes":
                    encode(b"hello"),
            },
        ]
    }

    result = get_message_attachments(
        message,
        attachments,
    )

    assert len(result) == 1

    assert (
        result[0]["name"]
        == "timesheet.png"
    )


def test_real_graph_style_message_reaches_pre_llm() -> None:
    store: Any = MagicMock()

    store.hash_exists.return_value = False

    message = make_message()

    image_bytes = make_png_bytes()

    attachments = {
        "message-123": [
            {
                "@odata.type":
                    "#microsoft.graph.fileAttachment",
                "id": "image-1",
                "name": "timesheet.png",
                "contentType": "image/png",
                "contentBytes":
                    encode(image_bytes),
            }
        ]
    }

    results = process_graph_messages(
        messages=[message],
        attachments_by_message=attachments,
        hash_store=store,
    )

    assert len(results) == 1

    graph_result = results[0]

    assert (
        graph_result.message_id
        == "message-123"
    )

    assert (
        graph_result.subject
        == "Approved Timesheet"
    )

    assert (
        graph_result.result
        .hashing_result
        .skip_message
        is False
    )

    assert len(
        graph_result.result.llm_inputs
    ) == 1