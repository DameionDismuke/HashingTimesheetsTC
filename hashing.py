import base64
import hashlib
from typing import Any


def sha256_bytes(data: bytes) -> str:
    """
    Return a deterministic SHA-256 hexadecimal digest.
    """
    if not data:
        raise ValueError("Cannot hash empty data.")

    return hashlib.sha256(data).hexdigest()


def create_message_hash(message: dict[str, Any]) -> str:
    """
    Create a stable hash for a Microsoft Graph email message.

    The project requirement is:
        message id + message timestamp -> SHA-256

    The timestamp comes from the message itself so the same
    email always produces the same hash.
    """
    message_id = message.get("id")
    received_datetime = message.get("receivedDateTime")

    if not message_id:
        raise ValueError("Message is missing 'id'.")

    if not received_datetime:
        raise ValueError(
            "Message is missing 'receivedDateTime'."
        )

    canonical_value = (
        f"{message_id}|{received_datetime}"
    )

    return sha256_bytes(
        canonical_value.encode("utf-8")
    )


def decode_base64_content(
    content_bytes: str,
) -> bytes:
    """
    Convert Microsoft Graph contentBytes back into
    the attachment's original binary bytes.
    """
    if not content_bytes:
        raise ValueError(
            "Attachment contentBytes cannot be empty."
        )

    return base64.b64decode(
        content_bytes,
        validate=True,
    )


def create_attachment_hash(
    content_bytes: str,
) -> str:
    """
    Create SHA-256 for an attachment returned by Graph.

    Graph:
        contentBytes (Base64)
              ↓
        decode Base64
              ↓
        original file bytes
              ↓
        SHA-256
    """
    raw_bytes = decode_base64_content(
        content_bytes
    )

    return sha256_bytes(raw_bytes)


def create_page_hash(
    page_bytes: bytes,
) -> str:
    """
    Create SHA-256 for one rendered PDF page.

    PDF rendering will happen elsewhere. This function
    hashes the resulting standardized image bytes before
    they are sent to the LLM.
    """
    return sha256_bytes(page_bytes)