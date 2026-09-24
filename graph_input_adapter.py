from dataclasses import dataclass
from typing import Any

from pre_llm_processor import (
    PreLLMResult,
    prepare_graph_message,
)


@dataclass
class GraphMessageResult:
    """
    Associates one Microsoft Graph message
    with its pre-LLM processing result.
    """

    message_id: str
    subject: str
    result: PreLLMResult


def is_graph_file_attachment(
    attachment: dict[str, Any],
) -> bool:
    """
    Return True when the Graph attachment contains
    actual file bytes that our pipeline can process.

    Microsoft Graph can return other attachment types,
    such as item attachments.
    """

    attachment_type = str(
        attachment.get(
            "@odata.type",
            "",
        )
    )

    if attachment_type:
        if not attachment_type.endswith(
            "fileAttachment"
        ):
            return False

    return bool(
        attachment.get("contentBytes")
    )


def is_supported_attachment(
    attachment: dict[str, Any],
) -> bool:
    """
    Limit the hashing/vision pipeline to PDFs
    and supported image formats.
    """

    name = str(
        attachment.get("name", "")
    ).lower()

    content_type = str(
        attachment.get(
            "contentType",
            "",
        )
    ).lower()

    if content_type == "application/pdf":
        return True

    if name.endswith(".pdf"):
        return True

    supported_image_types = {
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/webp",
        "image/gif",
    }

    return (
        content_type
        in supported_image_types
    )


def get_message_attachments(
    message: dict[str, Any],
    attachments_by_message: dict[
        str,
        list[dict[str, Any]],
    ],
) -> list[dict[str, Any]]:
    """
    Retrieve processable attachments belonging
    to one Graph message.
    """

    message_id = str(
        message.get("id", "")
    )

    if not message_id:
        raise ValueError(
            "Graph message is missing 'id'."
        )

    attachments = (
        attachments_by_message.get(
            message_id,
            [],
        )
    )

    return [
        attachment
        for attachment in attachments
        if is_graph_file_attachment(
            attachment
        )
        and is_supported_attachment(
            attachment
        )
    ]


def process_graph_messages(
    messages: list[dict[str, Any]],
    attachments_by_message: dict[
        str,
        list[dict[str, Any]],
    ],
    hash_store: Any,
) -> list[GraphMessageResult]:
    """
    Run Microsoft's Graph message/attachment payloads
    through the complete pre-LLM hashing pipeline.

    No hash is committed here.
    """

    results: list[
        GraphMessageResult
    ] = []

    for message in messages:
        message_id = str(
            message.get("id", "")
        )

        if not message_id:
            continue

        attachments = (
            get_message_attachments(
                message,
                attachments_by_message,
            )
        )

        result = prepare_graph_message(
            message=message,
            attachments=attachments,
            hash_store=hash_store,
        )

        results.append(
            GraphMessageResult(
                message_id=message_id,
                subject=str(
                    message.get(
                        "subject",
                        "",
                    )
                ),
                result=result,
            )
        )

    return results