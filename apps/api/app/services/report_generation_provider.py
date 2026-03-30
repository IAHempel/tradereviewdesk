import json
import re
from dataclasses import dataclass
from typing import Any

import httpx
from openai import APIConnectionError, APIError, APITimeoutError, OpenAI, RateLimitError
from pydantic import BaseModel

from app.core.config import settings
from app.schemas.reports import (
    DebriefGenerateRequest,
    DebriefOutput,
    PremarketGenerateRequest,
    PremarketOutput,
    WeeklyReviewGenerateRequest,
    WeeklyReviewOutput,
)


class LLMProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderGenerationResult:
    raw_output: str
    usage_metrics: dict[str, Any] | None = None


class ReportGenerationProvider:
    def __init__(self) -> None:
        self._client: OpenAI | None = None

    def _should_force_failure(self, values: list[str]) -> bool:
        return any("[force-fail]" in value.lower() for value in values)

    def _should_force_malformed(self, values: list[str], attempt: int) -> bool:
        return attempt == 1 and any("[force-malformed]" in value.lower() for value in values)

    def _is_live_provider_configured(self) -> bool:
        return not settings.is_placeholder_llm_key

    def _require_live_provider_if_production(self) -> None:
        if settings.is_production and not self._is_live_provider_configured():
            raise LLMProviderError("LLM provider is not configured for production.")

    def _get_client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                api_key=settings.llm_api_key,
                timeout=httpx.Timeout(settings.llm_request_timeout_seconds),
            )
        return self._client

    def _build_prompt_payload(self, payload: BaseModel, validation_error: str | None) -> str:
        sections = [
            "Return a raw JSON object only. Do not wrap it in markdown fences.",
            "Keep the response operational, concise, and focused on workflow support for a self-directed trader.",
            "Never provide investment advice, price targets, security recommendations, or execution instructions.",
            "Base the response only on the supplied user context.",
            "Payload:",
            payload.model_dump_json(indent=2),
        ]
        if validation_error:
            sections.extend(
                [
                    "",
                    "The previous response failed validation. Repair the structure and keep the same compliance boundary.",
                    f"Validation error: {validation_error}",
                ]
            )
        return "\n".join(sections)

    def _extract_json_text(self, text: str) -> str:
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
            stripped = re.sub(r"\s*```$", "", stripped)
        return stripped.strip()

    def _estimate_cost_usd(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
        pricing = {
            "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
            "gpt-5-mini": {"input": 0.25, "output": 2.00},
            "gpt-5.4-mini": {"input": 0.75, "output": 4.50},
        }.get(model_name)

        if pricing is None:
            return 0.0

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return round(input_cost + output_cost, 6)

    def _build_usage_metrics(self, response) -> dict[str, Any] | None:
        usage = getattr(response, "usage", None)
        if usage is None:
            return None

        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", input_tokens + output_tokens) or 0)

        return {
            "provider": "openai",
            "model": settings.llm_model_name,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": self._estimate_cost_usd(settings.llm_model_name, input_tokens, output_tokens),
        }

    def _request_openai_json_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> ProviderGenerationResult:
        try:
            response = self._get_client().responses.create(
                model=settings.llm_model_name,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except (APIConnectionError, APITimeoutError, RateLimitError, APIError) as exc:
            raise LLMProviderError(f"OpenAI request failed: {exc.__class__.__name__}") from exc

        output_text = getattr(response, "output_text", "") or ""
        if not output_text.strip():
            raise LLMProviderError("OpenAI returned no text output.")
        return ProviderGenerationResult(
            raw_output=self._extract_json_text(output_text),
            usage_metrics=self._build_usage_metrics(response),
        )

    def generate(
        self,
        report_type: str,
        payload: dict[str, Any],
        *,
        attempt: int,
        validation_error: str | None = None,
    ) -> ProviderGenerationResult:
        if report_type == "premarket":
            return self._generate_premarket(
                PremarketGenerateRequest.model_validate(payload),
                attempt=attempt,
                validation_error=validation_error,
            )
        if report_type == "debrief":
            return self._generate_debrief(
                DebriefGenerateRequest.model_validate(payload),
                attempt=attempt,
                validation_error=validation_error,
            )
        return self._generate_weekly_review(
            WeeklyReviewGenerateRequest.model_validate(payload),
            attempt=attempt,
            validation_error=validation_error,
        )

    def _generate_premarket(
        self,
        payload: PremarketGenerateRequest,
        *,
        attempt: int,
        validation_error: str | None,
    ) -> ProviderGenerationResult:
        self._require_live_provider_if_production()

        notes = [*payload.manual_events, *payload.user_priorities, *payload.prior_notes]
        if self._should_force_failure(notes):
            return ProviderGenerationResult(
                raw_output=json.dumps({"summary": 42, "watchlist_priorities": "bad-shape", "disclaimer": "Forced failure payload"})
            )
        if self._should_force_malformed(notes, attempt):
            return ProviderGenerationResult(
                raw_output=json.dumps({"summary": 42, "watchlist_priorities": "bad-shape", "disclaimer": "Malformed test payload"})
            )

        if self._is_live_provider_configured():
            return self._request_openai_json_output(
                system_prompt=(
                    "You are TradeReviewDesk, a trading workflow assistant. Produce a premarket planning summary for "
                    "a self-directed trader. Stay process-first, observational, and non-advisory."
                ),
                user_prompt=self._build_prompt_payload(payload, validation_error),
            )

        focus_reminders = ["Wait for confirmation before acting.", "Keep size aligned to planned risk."]
        if validation_error:
            focus_reminders.append("Recovered from a malformed draft by revalidating the workflow structure.")

        data = {
            "summary": "Focus on the smallest number of high-conviction names and keep the plan process-first.",
            "watchlist_priorities": [
                {
                    "symbol": symbol,
                    "priority": "high" if idx == 0 else "medium",
                    "reason": "User watchlist focus",
                }
                for idx, symbol in enumerate(payload.watchlist_symbols[:3])
            ],
            "changes_to_watch": payload.manual_events,
            "focus_reminders": focus_reminders,
            "session_checklist": ["Review catalysts", "Confirm risk levels", "Document plan before entry"],
            "disclaimer": "Workflow support only. No trade recommendations or execution guidance.",
        }
        return ProviderGenerationResult(raw_output=json.dumps(data))

    def _generate_debrief(
        self,
        payload: DebriefGenerateRequest,
        *,
        attempt: int,
        validation_error: str | None,
    ) -> ProviderGenerationResult:
        self._require_live_provider_if_production()

        if self._should_force_failure(payload.user_notes):
            return ProviderGenerationResult(raw_output='{"session_summary": "Broken", "what_went_well": "not-a-list"}')
        if self._should_force_malformed(payload.user_notes, attempt):
            return ProviderGenerationResult(raw_output='{"session_summary": "Broken", "what_went_well": "not-a-list"}')

        if self._is_live_provider_configured():
            return self._request_openai_json_output(
                system_prompt=(
                    "You are TradeReviewDesk, a trading workflow assistant. Produce a post-session debrief that helps a "
                    "self-directed trader review discipline, execution quality, and journaling consistency. Do not "
                    "provide future trade instructions or recommendations."
                ),
                user_prompt=self._build_prompt_payload(payload, validation_error),
            )

        next_day_improvements = ["Write the exit plan before the open.", "Tag each trade with the planned setup."]
        if validation_error:
            next_day_improvements.append("Validation repair path corrected the generated structure before saving.")

        data = {
            "session_summary": "The session stayed anchored to routine, with room to tighten note quality after exits.",
            "what_went_well": ["Checklist usage stayed consistent.", "Trades were logged promptly."],
            "deviations_from_plan": ["Review whether late-session entries matched the playbook."],
            "risk_behavior_notes": ["Avoid adding size when conviction is based on speed rather than setup quality."],
            "next_day_improvements": next_day_improvements,
            "disclaimer": "Workflow support only. No direct trade recommendations.",
        }
        return ProviderGenerationResult(raw_output=json.dumps(data))

    def _generate_weekly_review(
        self,
        payload: WeeklyReviewGenerateRequest,
        *,
        attempt: int,
        validation_error: str | None,
    ) -> ProviderGenerationResult:
        self._require_live_provider_if_production()

        markers = payload.debrief_summaries + payload.checklist_run_summaries
        if self._should_force_failure(markers):
            return ProviderGenerationResult(raw_output='{"top_strengths": ["Routine"], "repeated_mistakes": null}')
        if self._should_force_malformed(markers, attempt):
            return ProviderGenerationResult(raw_output='{"top_strengths": ["Routine"], "repeated_mistakes": null}')

        if self._is_live_provider_configured():
            return self._request_openai_json_output(
                system_prompt=(
                    "You are TradeReviewDesk, a trading workflow assistant. Produce a weekly review focused on patterns, "
                    "discipline, and process improvements for a self-directed trader. Stay observational and "
                    "non-advisory."
                ),
                user_prompt=self._build_prompt_payload(payload, validation_error),
            )

        next_week_action_items = ["Reduce watchlist sprawl.", "Complete debriefs on every trading day."]
        if validation_error:
            next_week_action_items.append("A malformed draft was repaired and revalidated before persistence.")

        data = {
            "top_strengths": ["Routine consistency improved.", "Review cadence stayed intact."],
            "repeated_mistakes": ["Some trades still lacked complete setup tags."],
            "setup_observations": ["Momentum names worked best when the plan was written in advance."],
            "discipline_observations": ["Checklist completion correlated with calmer execution."],
            "next_week_action_items": next_week_action_items,
            "disclaimer": "Workflow support only. No security recommendations, targets, or market calls.",
        }
        return ProviderGenerationResult(raw_output=json.dumps(data))


report_generation_provider = ReportGenerationProvider()
