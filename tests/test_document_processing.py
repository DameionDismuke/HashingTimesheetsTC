import base64
from io import BytesIO
from typing import Any, cast

import pymupdf
import pytest
from PIL import Image

from document_processing import (
    bytes_to_base64,
    is_pdf,
    is_supported_image,
    prepare_attachment,
    prepare_image,
    render_pdf_pages,
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


def make_pdf_bytes() -> bytes:
    document: Any = pymupdf.open()

    page_1: Any = document.new_page()

    page_1.insert_text(
        (72, 72),
        "Page One",
    )

    page_2: Any = document.new_page()

    page_2.insert_text(
        (72, 72),
        "Page Two",
    )

    pdf_bytes = cast(
        bytes,
        document.tobytes(),
    )

    document.close()

    return pdf_bytes


def test_bytes_to_base64() -> None:
    original = b"timesheet"

    encoded = bytes_to_base64(
        original
    )

    assert (
        base64.b64decode(encoded)
        == original
    )


def test_is_pdf_by_content_type() -> None:
    assert (
        is_pdf(
            "document.bin",
            "application/pdf",
        )
        is True
    )


def test_is_pdf_by_file_extension() -> None:
    assert (
        is_pdf(
            "timesheet.PDF",
            "application/octet-stream",
        )
        is True
    )


def test_supported_image_type() -> None:
    assert (
        is_supported_image(
            "image/png"
        )
        is True
    )


def test_unsupported_image_type() -> None:
    assert (
        is_supported_image(
            "application/zip"
        )
        is False
    )


def test_prepare_image_preserves_bytes() -> None:
    image_bytes = make_png_bytes()

    result = prepare_image(
        file_name="timesheet.png",
        content_type="image/png",
        image_bytes=image_bytes,
    )

    assert (
        result.content_bytes
        == image_bytes
    )

    assert (
        result.content_type
        == "image/png"
    )

    assert (
        base64.b64decode(
            result.content_base64
        )
        == image_bytes
    )

    assert result.page_number is None


def test_render_pdf_pages() -> None:
    pdf_bytes = make_pdf_bytes()

    pages = render_pdf_pages(
        pdf_bytes
    )

    assert len(pages) == 2

    assert pages[0].startswith(
        b"\x89PNG"
    )

    assert pages[1].startswith(
        b"\x89PNG"
    )


def test_prepare_pdf_returns_page_documents() -> None:
    pdf_bytes = make_pdf_bytes()

    results = prepare_attachment(
        file_name="timesheet.pdf",
        content_type="application/pdf",
        raw_bytes=pdf_bytes,
    )

    assert len(results) == 2

    assert (
        results[0].page_number
        == 1
    )

    assert (
        results[1].page_number
        == 2
    )

    assert (
        results[0].content_type
        == "image/png"
    )


def test_prepare_image_attachment() -> None:
    image_bytes = make_png_bytes()

    results = prepare_attachment(
        file_name="timesheet.png",
        content_type="image/png",
        raw_bytes=image_bytes,
    )

    assert len(results) == 1

    assert (
        results[0].file_name
        == "timesheet.png"
    )


def test_invalid_image_is_rejected() -> None:
    with pytest.raises(
        ValueError
    ):
        prepare_attachment(
            file_name="bad.png",
            content_type="image/png",
            raw_bytes=b"not an image",
        )


def test_unsupported_attachment_is_rejected() -> None:
    with pytest.raises(
        ValueError
    ):
        prepare_attachment(
            file_name="notes.txt",
            content_type="text/plain",
            raw_bytes=b"hello",
        )