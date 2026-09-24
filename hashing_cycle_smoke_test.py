import json
from pathlib import Path
from typing import Any, cast

from graph_input_adapter import process_graph_messages
from hashing_pipeline import commit_successful_hashes
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
    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def load_messages() -> list[GraphMessage]:
    raw_data = load_json(
        MESSAGES_PATH
    )

    if not isinstance(
        raw_data,
        list,
    ):
        raise TypeError(
            "messages.json must contain a list."
        )

    return cast(
        list[GraphMessage],
        raw_data,
    )


def load_attachments() -> AttachmentMap:
    raw_data = load_json(
        ATTACHMENTS_PATH
    )

    if not isinstance(
        raw_data,
        dict,
    ):
        raise TypeError(
            "attachments.json must contain an object."
        )

    return cast(
        AttachmentMap,
        raw_data,
    )


def count_llm_inputs(
    results: list[Any],
) -> int:
    return sum(
        len(result.result.llm_inputs)
        for result in results
    )


def count_skipped_messages(
    results: list[Any],
) -> int:
    return sum(
        1
        for result in results
        if (
            result.result
            .hashing_result
            .skip_message
        )
    )


def main() -> None:
    messages = load_messages()
    attachments = load_attachments()

    store = InMemoryHashStore()

    print(
        "\n=== FIRST RUN ==="
    )

    first_results = process_graph_messages(
        messages=messages,
        attachments_by_message=attachments,
        hash_store=store,
    )

    first_llm_count = count_llm_inputs(
        first_results
    )

    print(
        "Messages processed:",
        len(first_results),
    )

    print(
        "LLM-ready documents/pages:",
        first_llm_count,
    )

    print(
        "Skipped messages:",
        count_skipped_messages(
            first_results
        ),
    )

    print(
        "Hashes before Excel success:",
        store.count(),
    )

    # Simulate successful downstream Excel writes.

    for graph_result in first_results:
        hashing_result = (
            graph_result
            .result
            .hashing_result
        )

        commit_successful_hashes(
            hash_store=store,
            pending_hashes=(
                hashing_result.pending_hashes
            ),
        )

    print(
        "Hashes after simulated Excel success:",
        store.count(),
    )

    print(
        "\n=== SECOND RUN ==="
    )

    second_results = process_graph_messages(
        messages=messages,
        attachments_by_message=attachments,
        hash_store=store,
    )

    second_llm_count = count_llm_inputs(
        second_results
    )

    second_skipped = count_skipped_messages(
        second_results
    )

    print(
        "Messages processed:",
        len(second_results),
    )

    print(
        "Skipped messages:",
        second_skipped,
    )

    print(
        "LLM-ready documents/pages:",
        second_llm_count,
    )

    print(
        "Hashes after second run:",
        store.count(),
    )

    print(
        "\n=== EXPECTED ==="
    )

    print(
        f"First run LLM documents > 0: "
        f"{first_llm_count > 0}"
    )

    print(
        f"Second run skipped all messages: "
        f"{second_skipped == len(messages)}"
    )

    print(
        f"Second run LLM documents == 0: "
        f"{second_llm_count == 0}"
    )


if __name__ == "__main__":
    main()