import base64
from io import BytesIO
from typing import Any
from unittest.mock import MagicMock

import pymupdf
from PIL import Image

from pre_llm_processor import (
    prepare_graph_message,
)


def make_message() -> dict[str, str]:
    return {
        "id": "message-123",
        "receivedDateTime":
            "2026-09-24T10:00:00Z",
    }


def encode(data: bytes) -> str:
    return base64.b64encode(
        data
    ).decode("utf-8")


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


def make_pdf_bytes() -> bytes:
    document: Any = pymupdf.open()

    page_1: Any = document.new_page()

    page_1.insert_text(
        (72, 72),
        "Timesheet Page One",
    )

    page_2: Any = document.new_page()

    page_2.insert_text(
        (72, 72),
        "Timesheet Page Two",
    )

    pdf_bytes: bytes = document.tobytes()

    document.close()

    return pdf_bytes


def test_real_image_becomes_llm_input() -> None:
    store: Any = MagicMock()

    store.hash_exists.return_value = False

    image_bytes = make_png_bytes()

    attachment: dict[str, Any] = {
        "id": "image-1",
        "name": "timesheet.png",
        "contentType": "image/png",
        "contentBytes": encode(
            image_bytes
        ),
    }

    result = prepare_graph_message(
        message=make_message(),
        attachments=[attachment],
        hash_store=store,
    )

    assert (
        result.hashing_result.skip_message
        is False
    )

    assert len(
        result.llm_inputs
    ) == 1

    llm_input = result.llm_inputs[0]

    assert (
        llm_input.content_type
        == "image/png"
    )

    decoded = base64.b64decode(
        llm_input.content_base64
    )

    assert decoded == image_bytes


def test_real_pdf_becomes_one_llm_input_per_page() -> None:
    store: Any = MagicMock()

    store.hash_exists.return_value = False

    pdf_bytes = make_pdf_bytes()

    attachment: dict[str, Any] = {
        "id": "pdf-1",
        "name": "timesheet.pdf",
        "contentType": "application/pdf",
        "contentBytes": encode(
            pdf_bytes
        ),
    }

    result = prepare_graph_message(
        message=make_message(),
        attachments=[attachment],
        hash_store=store,
    )

    assert (
        result.hashing_result.skip_message
        is False
    )

    assert len(
        result.llm_inputs
    ) == 2

    assert (
        result.llm_inputs[0].page_number
        == 1
    )

    assert (
        result.llm_inputs[1].page_number
        == 2
    )

    assert (
        result.llm_inputs[0].content_type
        == "image/png"
    )

    first_page = base64.b64decode(
        result.llm_inputs[0].content_base64
    )

    assert first_page.startswith(
        b"\x89PNG"
    )


def test_existing_message_produces_no_llm_inputs() -> None:
    store: Any = MagicMock()

    store.hash_exists.return_value = True

    result = prepare_graph_message(
        message=make_message(),
        attachments=[],
        hash_store=store,
    )

    assert (
        result.hashing_result.skip_message
        is True
    )

    assert result.llm_inputs == []