from dataclasses import dataclass, field
from typing import Any, Callable

from cosmos_hash_store import CosmosHashStore
from hashing import (
    create_attachment_hash,
    create_message_hash,
    create_page_hash,
    decode_base64_content,
)


def empty_metadata() -> dict[str, Any]:
    return {}


@dataclass
class PendingHash:
    hash_value: str
    hash_type: str
    metadata: dict[str, Any] = field(
        default_factory=empty_metadata
    )


@dataclass
class LLMDocument:
    """
    One piece of content that is safe to send to the LLM
    because its hash was not found in Cosmos DB.
    """

    file_name: str
    content_bytes: bytes
    content_type: str
    attachment_id: str | None = None
    page_number: int | None = None


@dataclass
class HashingResult:
    """
    Result of the pre-LLM hashing stage.
    """

    skip_message: bool
    message_hash: str
    llm_documents: list[LLMDocument]
    pending_hashes: list[PendingHash]


def is_pdf(
    file_name: str,
    content_type: str,
) -> bool:
    return (
        content_type.lower() == "application/pdf"
        or file_name.lower().endswith(".pdf")
    )


def prepare_message_for_llm(
    message: dict[str, Any],
    attachments: list[dict[str, Any]],
    hash_store: CosmosHashStore,
    render_pdf_pages: Callable[
        [bytes],
        list[bytes],
    ],
) -> HashingResult:
    """
    Perform all duplicate checks before the LLM.

    Nothing is written to Cosmos here.

    Hashes are collected as pending and should only be
    committed after Excel successfully saves the result.
    """

    message_hash = create_message_hash(
        message
    )

    # Step 3/4:
    # If the message has already successfully completed,
    # skip the entire message.
    if hash_store.hash_exists(message_hash):
        return HashingResult(
            skip_message=True,
            message_hash=message_hash,
            llm_documents=[],
            pending_hashes=[],
        )

    llm_documents: list[LLMDocument] = []
    pending_hashes: list[PendingHash] = []

    # Message hash is pending until downstream Excel succeeds.
    pending_hashes.append(
        PendingHash(
            hash_value=message_hash,
            hash_type="message",
            metadata={
                "messageId": message.get("id"),
                "receivedDateTime": message.get(
                    "receivedDateTime"
                ),
            },
        )
    )

    for attachment in attachments:
        file_name = attachment.get(
            "name",
            "unknown",
        )

        content_type = attachment.get(
            "contentType",
            "application/octet-stream",
        )

        attachment_id = attachment.get("id")

        content_bytes_b64 = attachment.get(
            "contentBytes"
        )

        if not content_bytes_b64:
            continue

        attachment_hash = (
            create_attachment_hash(
                content_bytes_b64
            )
        )

        # Exact same file has already completed.
        if hash_store.hash_exists(
            attachment_hash
        ):
            continue

        raw_bytes = decode_base64_content(
            content_bytes_b64
        )

        if is_pdf(
            file_name,
            content_type,
        ):
            pages = render_pdf_pages(
                raw_bytes
            )

            new_page_found = False

            for page_number, page_bytes in enumerate(
                pages,
                start=1,
            ):
                page_hash = create_page_hash(
                    page_bytes
                )

                # Don't pay for another LLM call
                # for a page we've already processed.
                if hash_store.hash_exists(
                    page_hash
                ):
                    continue

                new_page_found = True

                llm_documents.append(
                    LLMDocument(
                        file_name=file_name,
                        content_bytes=page_bytes,
                        content_type="image/png",
                        attachment_id=attachment_id,
                        page_number=page_number,
                    )
                )

                pending_hashes.append(
                    PendingHash(
                        hash_value=page_hash,
                        hash_type=(
                            "attachment_page"
                        ),
                        metadata={
                            "messageHash":
                                message_hash,
                            "attachmentId":
                                attachment_id,
                            "fileName":
                                file_name,
                            "pageNumber":
                                page_number,
                        },
                    )
                )

            # Record the whole PDF only if at least one
            # previously unseen page was processed.
            if new_page_found:
                pending_hashes.append(
                    PendingHash(
                        hash_value=attachment_hash,
                        hash_type="attachment",
                        metadata={
                            "messageHash":
                                message_hash,
                            "attachmentId":
                                attachment_id,
                            "fileName":
                                file_name,
                            "contentType":
                                content_type,
                        },
                    )
                )

        else:
            # Non-PDF attachment. This will normally
            # represent an image file.
            llm_documents.append(
                LLMDocument(
                    file_name=file_name,
                    content_bytes=raw_bytes,
                    content_type=content_type,
                    attachment_id=attachment_id,
                )
            )

            pending_hashes.append(
                PendingHash(
                    hash_value=attachment_hash,
                    hash_type="attachment",
                    metadata={
                        "messageHash":
                            message_hash,
                        "attachmentId":
                            attachment_id,
                        "fileName":
                            file_name,
                        "contentType":
                            content_type,
                    },
                )
            )

    return HashingResult(
        skip_message=False,
        message_hash=message_hash,
        llm_documents=llm_documents,
        pending_hashes=pending_hashes,
    )


def commit_successful_hashes(
    hash_store: CosmosHashStore,
    pending_hashes: list[PendingHash],
) -> None:
    """
    Commit hashes only AFTER Excel reports success.
    """

    for pending in pending_hashes:
        hash_store.save_hash(
            pending.hash_value,
            pending.hash_type,
            **pending.metadata,
        )