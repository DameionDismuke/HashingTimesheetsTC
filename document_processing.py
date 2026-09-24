import base64
from dataclasses import dataclass
from io import BytesIO
from typing import Any, cast

import pymupdf
from PIL import Image


@dataclass
class PreparedDocument:
    """
    LLM-ready document content.

    For image files, one PreparedDocument is returned.
    For PDFs, one PreparedDocument is returned per page.
    """

    file_name: str
    content_type: str
    content_bytes: bytes
    content_base64: str
    page_number: int | None = None


def bytes_to_base64(data: bytes) -> str:
    """
    Convert raw bytes into a Base64 string.
    """
    return base64.b64encode(
        data
    ).decode("utf-8")


def is_pdf(
    file_name: str,
    content_type: str,
) -> bool:
    """
    Detect whether an attachment should be treated as a PDF.
    """
    return (
        content_type.lower() == "application/pdf"
        or file_name.lower().endswith(".pdf")
    )


def is_supported_image(
    content_type: str,
) -> bool:
    """
    Return True for image MIME types we support.
    """
    supported_types = {
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/webp",
        "image/gif",
    }

    return content_type.lower() in supported_types


def verify_image(
    image_bytes: bytes,
) -> None:
    """
    Verify that the supplied bytes represent
    a readable image.
    """
    try:
        image = Image.open(
            BytesIO(image_bytes)
        )

        image.verify()

    except Exception as exc:
        raise ValueError(
            "Attachment is not a valid image."
        ) from exc


def render_pdf_pages(
    pdf_bytes: bytes,
) -> list[bytes]:
    """
    Render every page of a PDF into PNG bytes.
    """

    if not pdf_bytes:
        raise ValueError(
            "PDF bytes cannot be empty."
        )

    pages: list[bytes] = []

    try:
        document: Any = pymupdf.open(
            stream=pdf_bytes,
            filetype="pdf",
        )

        for page in document:
            pixmap: Any = page.get_pixmap(
                alpha=False
            )

            png_bytes = cast(
                bytes,
                pixmap.tobytes("png"),
            )

            pages.append(
                png_bytes
            )

        document.close()

    except Exception as exc:
        raise ValueError(
            "Unable to render PDF."
        ) from exc

    if not pages:
        raise ValueError(
            "PDF contains no pages."
        )

    return pages


def prepare_image(
    file_name: str,
    content_type: str,
    image_bytes: bytes,
) -> PreparedDocument:
    """
    Prepare an existing image attachment
    for the LLM without re-rendering it.
    """

    if not is_supported_image(
        content_type
    ):
        raise ValueError(
            f"Unsupported image type: {content_type}"
        )

    verify_image(
        image_bytes
    )

    return PreparedDocument(
        file_name=file_name,
        content_type=content_type,
        content_bytes=image_bytes,
        content_base64=bytes_to_base64(
            image_bytes
        ),
    )


def prepare_pdf(
    file_name: str,
    pdf_bytes: bytes,
) -> list[PreparedDocument]:
    """
    Render a PDF into one PNG image per page
    and prepare each page for the LLM.
    """

    rendered_pages = render_pdf_pages(
        pdf_bytes
    )

    prepared_pages: list[
        PreparedDocument
    ] = []

    for page_number, page_bytes in enumerate(
        rendered_pages,
        start=1,
    ):
        prepared_pages.append(
            PreparedDocument(
                file_name=file_name,
                content_type="image/png",
                content_bytes=page_bytes,
                content_base64=bytes_to_base64(
                    page_bytes
                ),
                page_number=page_number,
            )
        )

    return prepared_pages


def prepare_attachment(
    file_name: str,
    content_type: str,
    raw_bytes: bytes,
) -> list[PreparedDocument]:
    """
    Convert one decoded attachment into
    one or more LLM-ready documents.

    PDF:
        returns one PreparedDocument per page

    Image:
        returns a single PreparedDocument
    """

    if is_pdf(
        file_name=file_name,
        content_type=content_type,
    ):
        return prepare_pdf(
            file_name=file_name,
            pdf_bytes=raw_bytes,
        )

    if is_supported_image(
        content_type
    ):
        return [
            prepare_image(
                file_name=file_name,
                content_type=content_type,
                image_bytes=raw_bytes,
            )
        ]

    raise ValueError(
        f"Unsupported attachment type: {content_type}"
    )