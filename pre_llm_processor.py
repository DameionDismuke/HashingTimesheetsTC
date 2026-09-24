import base64
from dataclasses import dataclass
from typing import Any

from document_processing import render_pdf_pages
from hashing_pipeline import (
    HashingResult,
    HashStore,
    prepare_message_for_llm,
)


@dataclass
class LLMInput:
    """
    Final document payload ready to be passed
    to a vision-capable LLM.
    """

    file_name: str
    content_type: str
    content_base64: str
    attachment_id: str | None = None
    page_number: int | None = None


@dataclass
class PreLLMResult:
    """
    Complete result of message preprocessing.

    hashing_result:
        Contains the message hash and pending hashes
        that may later be committed to Cosmos.

    llm_inputs:
        Contains only content that has NOT already
        been successfully processed.
    """

    hashing_result: HashingResult
    llm_inputs: list[LLMInput]


def encode_for_llm(
    data: bytes,
) -> str:
    """
    Convert binary content into Base64 for the LLM.
    """
    return base64.b64encode(
        data
    ).decode("utf-8")


def prepare_graph_message(
    message: dict[str, Any],
    attachments: list[dict[str, Any]],
    hash_store: HashStore,
) -> PreLLMResult:
    """
    Production pre-LLM processing entry point.

    Flow:

        Graph message
            ↓
        message hash
            ↓
        Cosmos duplicate check
            ↓
        attachment hash
            ↓
        PDF -> PNG pages
        Image -> original bytes
            ↓
        page/content duplicate check
            ↓
        Base64
            ↓
        LLM-ready inputs

    No hashes are written to Cosmos here.
    """

    hashing_result = prepare_message_for_llm(
        message=message,
        attachments=attachments,
        hash_store=hash_store,
        render_pdf_pages=render_pdf_pages,
    )

    if hashing_result.skip_message:
        return PreLLMResult(
            hashing_result=hashing_result,
            llm_inputs=[],
        )

    llm_inputs: list[LLMInput] = []

    for document in hashing_result.llm_documents:
        llm_inputs.append(
            LLMInput(
                file_name=document.file_name,
                content_type=document.content_type,
                content_base64=encode_for_llm(
                    document.content_bytes
                ),
                attachment_id=document.attachment_id,
                page_number=document.page_number,
            )
        )

    return PreLLMResult(
        hashing_result=hashing_result,
        llm_inputs=llm_inputs,
    )