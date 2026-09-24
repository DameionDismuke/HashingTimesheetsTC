import json
from pathlib import Path
from typing import Any, cast

from graph_input_adapter import process_graph_messages
from in_memory_hash_store import InMemoryHashStore


MESSAGES_PATH = Path("messages.json")
ATTACHMENTS_PATH = Path("attachments.json")


GraphMessage = dict[str, Any]
GraphAttachment = dict[str, Any]
AttachmentMap = dict[
    str,
    list[GraphAttachment],
]


def load_json(
    path: Path,
) -> object:
    """
    Load JSON without assuming its structure yet.

    The caller validates the structure before casting
    it to the expected Graph data types.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Missing required file: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def validate_messages(
    raw_data: object,
) -> list[GraphMessage]:
    """
    Validate that messages.json contains a list
    of Microsoft Graph message dictionaries.
    """

    if not isinstance(
        raw_data,
        list,
    ):
        raise TypeError(
            "messages.json must contain a JSON list."
        )

    items = cast(
        list[object],
        raw_data,
    )

    for item in items:
        if not isinstance(
            item,
            dict,
        ):
            raise TypeError(
                "Every item in messages.json "
                "must be a JSON object."
            )

    return cast(
        list[GraphMessage],
        items,
    )


def validate_attachments(
    raw_data: object,
) -> AttachmentMap:
    """
    Validate that attachments.json contains:

        {
            "message-id": [
                {...attachment...},
                {...attachment...}
            ]
        }
    """

    if not isinstance(
        raw_data,
        dict,
    ):
        raise TypeError(
            "attachments.json must contain "
            "a JSON object keyed by message ID."
        )

    raw_mapping = cast(
        dict[object, object],
        raw_data,
    )

    for message_id, attachment_value in (
        raw_mapping.items()
    ):
        if not isinstance(
            message_id,
            str,
        ):
            raise TypeError(
                "Every attachments.json key "
                "must be a message ID string."
            )

        if not isinstance(
            attachment_value,
            list,
        ):
            raise TypeError(
                "Every attachments.json value "
                "must be a list of attachments."
            )

        attachment_list = cast(
            list[object],
            attachment_value,
        )

        for attachment in attachment_list:
            if not isinstance(
                attachment,
                dict,
            ):
                raise TypeError(
                    "Every attachment must be "
                    "a JSON object."
                )

    return cast(
        AttachmentMap,
        raw_mapping,
    )


def main() -> None:
    raw_messages = load_json(
        MESSAGES_PATH
    )

    raw_attachments = load_json(
        ATTACHMENTS_PATH
    )

    messages = validate_messages(
        raw_messages
    )

    attachments_by_message = (
        validate_attachments(
            raw_attachments
        )
    )

    print(
        f"Loaded {len(messages)} messages."
    )

    print(
        "Attachment map contains "
        f"{len(attachments_by_message)} "
        "message IDs."
    )

    total_attachments = sum(
        len(attachments)
        for attachments
        in attachments_by_message.values()
    )

    print(
        f"Loaded {total_attachments} attachments."
    )

    store = InMemoryHashStore()

    results = process_graph_messages(
        messages=messages,
        attachments_by_message=(
            attachments_by_message
        ),
        hash_store=store,
    )

    skipped_messages = 0
    llm_documents = 0
    messages_with_llm_content = 0

    print(
        "\n--- PROCESSING RESULTS ---"
    )

    for result in results:
        pre_llm = result.result

        if (
            pre_llm
            .hashing_result
            .skip_message
        ):
            skipped_messages += 1
            continue

        document_count = len(
            pre_llm.llm_inputs
        )

        llm_documents += document_count

        if document_count > 0:
            messages_with_llm_content += 1

            print(
                "\nMessage: "
                f"{result.subject}"
            )

            short_message_id = (
                result.message_id[:30]
            )

            print(
                "  Message ID: "
                f"{short_message_id}..."
            )

            print(
                "  LLM documents: "
                f"{document_count}"
            )

            for document in (
                pre_llm.llm_inputs
            ):
                if (
                    document.page_number
                    is not None
                ):
                    page_text = (
                        " "
                        f"page="
                        f"{document.page_number}"
                    )
                else:
                    page_text = ""

                print(
                    "   - "
                    f"{document.file_name}"
                    " "
                    f"[{document.content_type}]"
                    f"{page_text}"
                )

    print(
        "\n--- SUMMARY ---"
    )

    print(
        "Messages processed: "
        f"{len(results)}"
    )

    print(
        "Messages skipped as duplicates: "
        f"{skipped_messages}"
    )

    print(
        "Messages containing new "
        "LLM-ready content: "
        f"{messages_with_llm_content}"
    )

    print(
        "Total LLM-ready documents/pages: "
        f"{llm_documents}"
    )

    print(
        "Hashes currently persisted: "
        f"{store.count()}"
    )

    print(
        "\nNOTE: No hashes should be persisted "
        "yet because Excel success has not "
        "occurred."
    )


if __name__ == "__main__":
    main()