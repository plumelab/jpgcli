from __future__ import annotations

import json

from openai import OpenAI
from pydantic import ValidationError

from jpgcli.config import load_app_config
from jpgcli.llm.prompting import build_chart_prompt
from jpgcli.schemas.chart_spec import ChartRequest, ChartSpec
from jpgcli.schemas.data_summary import DataFrameSummary
from jpgcli.utils.errors import LLMError, SpecValidationError


class ChartSpecGenerator:
    def __init__(self, client: OpenAI | None = None) -> None:
        self._client = client

    def generate(self, summary: DataFrameSummary, request: ChartRequest) -> ChartSpec:
        if summary.source_type == "text":
            raise LLMError("Text-only input is not enough for v1. Please provide Excel or CSV data.")

        client = self._client or self._build_client()
        prompt = build_chart_prompt(summary, request.prompt, request.desired_theme)
        config = load_app_config()
        model = config.model
        if not model:
            raise LLMError("OPENAI_MODEL is not set.")

        response = client.responses.create(
            model=model,
            input=prompt,
        )
        text = getattr(response, "output_text", None)
        if not text:
            raise LLMError("Model returned an empty response.")

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise SpecValidationError("Model response was not valid JSON.") from exc

        try:
            return ChartSpec.model_validate(payload)
        except ValidationError as exc:
            raise SpecValidationError(f"Model JSON failed schema validation: {exc}") from exc

    def _build_client(self) -> OpenAI:
        config = load_app_config()
        if not config.api_key:
            raise LLMError("OPENAI_API_KEY is not set.")
        return OpenAI(api_key=config.api_key, base_url=config.base_url or None)
