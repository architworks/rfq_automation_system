from __future__ import annotations

from abc import ABC, abstractmethod
from typing import cast

from openai import OpenAI

from ..config import Settings
from ..models import OFFICIAL_AWARD_BASIS, RFQDraft, RubricProposal


class LLMConfigurationError(RuntimeError):
    pass


class RubricGenerationError(RuntimeError):
    pass


class LLMClient(ABC):
    @abstractmethod
    def generate_rubric(self, rfq_draft: RFQDraft) -> RubricProposal:
        raise NotImplementedError


class OpenAIResponsesClient(LLMClient):
    def __init__(self, settings: Settings) -> None:
        if not settings.azure_openai_endpoint:
            raise LLMConfigurationError("AZURE_OPENAI_ENDPOINT is required.")
        if not settings.azure_openai_api_key:
            raise LLMConfigurationError("AZURE_OPENAI_API_KEY is required.")
        if not settings.azure_openai_model:
            raise LLMConfigurationError("AZURE_OPENAI_MODEL is required.")

        self._model = settings.azure_openai_model
        base_url = settings.azure_openai_endpoint
        if not base_url.endswith("/"):
            base_url = f"{base_url}/"

        self._client = OpenAI(
            api_key=settings.azure_openai_api_key,
            base_url=base_url,
            timeout=settings.azure_openai_timeout_seconds,
        )

    def generate_rubric(self, rfq_draft: RFQDraft) -> RubricProposal:
        instructions = (
            "You are generating an RFQ evaluation framework for a procurement buyer. "
            "Return only structured data that matches the schema. "
            f"The official award basis must remain fixed to {OFFICIAL_AWARD_BASIS}. "
            "Use a moderate hierarchy of sections, criteria, and evidence checks. "
            "Classify criteria into mac, technical_cutoff_backed, technical_scored_only, or commercial. "
            "Technical scored and cutoff-backed criteria together must total 100 points. "
            "Use only a selected subset of critical technical cutoffs, not a cutoff on every scored criterion. "
            "Generate freeform questions plus structured response schedules for pricing, scope coverage, "
            "compliance, timelines, and commercial terms. "
            "Every criterion must have evidence checks or linked questions/schedule fields."
        )
        input_text = (
            "Generate an RFQ evaluation rubric for the following draft.\n"
            f"{rfq_draft.model_dump_json(indent=2)}"
        )

        try:
            response = self._client.responses.parse(
                model=self._model,
                instructions=instructions,
                input=input_text,
                max_output_tokens=4000,
                temperature=0.2,
                store=False,
                text_format=RubricProposal,
            )
        except Exception as exc:  # pragma: no cover - network/runtime dependent
            raise RubricGenerationError(f"Rubric generation failed: {exc}") from exc

        parsed = cast(RubricProposal | None, response.output_parsed)
        if parsed is None:
            raise RubricGenerationError("Rubric generation returned no structured proposal.")
        return parsed
