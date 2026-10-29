"""The Skeptic seat: a last check on each sized paper order before it goes out.

It answers four closed risk questions with probabilities and vetoes the order
when any answer reaches the user's threshold. With an LLM key configured it asks
the model (up to a per-run budget of calls); otherwise, past the budget, or when
the model's answer fails validation, a deterministic scorer answers from the same
numbers. Every verdict records which one answered.
"""

import json
import math
from dataclasses import asdict, dataclass

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.core.config import settings
from app.schemas.desk import DeskConfig
from app.services.desk.agents import LOOKBACK, SETUP_LABELS, Setup, SymbolTape
from app.services.report_generation_provider import LLMProviderError, ReportGenerationProvider, report_generation_provider

SEAT_QUESTIONS: tuple[tuple[str, str], ...] = (
    ("chasing", "Is this entry chasing a move that is already extended?"),
    ("noise_stop", "Is the stop close enough to be hit by ordinary noise?"),
    ("against_context", "Does the trade fight the session's trend or order flow?"),
    ("thin_volume", "Is volume too thin to trust the signal?"),
)
QUESTION_TEXT = dict(SEAT_QUESTIONS)

SYSTEM_PROMPT = (
    "You are the Skeptic seat on a paper-trading review desk. A rules engine has already proposed the paper order "
    "described below. Your only job is to judge four risk questions about it. For each question give the probability "
    "(0 to 1) that the answer is yes, with one short sentence grounded in the numbers provided. Then write one sentence "
    "describing what the setup is betting on. Do not recommend buying, selling, or any trade, and do not predict "
    "prices; assess only the risks of the proposed paper order. Return only JSON shaped like "
    '{"answers": [{"id": "chasing", "probability": 0.2, "reason": "..."}, ...], "thesis": "..."} '
    "with exactly these ids: chasing, noise_stop, against_context, thin_volume."
)


@dataclass(frozen=True)
class SeatContext:
    symbol: str
    setup: str
    side: str
    clock: str
    entry: float
    stop: float
    target: float
    reward_risk: float
    stop_atr: float
    extension_atr: float
    range_position: float
    volume_ratio: float
    flow_imbalance: float
    trend_aligned: bool
    recent_moves_atr: list[float]


def build_context(setup: Setup, tape: SymbolTape, flow: float, clock: str) -> SeatContext:
    """The numbers the seat judges, all signed so positive means 'in the trade's direction'."""
    bar = tape.last
    direction = setup.direction
    window = tape.bars[-LOOKBACK:]
    high = max(item.high for item in window)
    low = min(item.low for item in window)
    position = 0.5 if high == low else (bar.close - low) / (high - low)
    closes = [item.close for item in tape.bars[-7:]]
    return SeatContext(
        symbol=setup.symbol,
        setup=setup.setup,
        side=setup.side,
        clock=clock,
        entry=round(setup.entry, 4),
        stop=round(setup.stop, 4),
        target=round(setup.target, 4),
        reward_risk=round(setup.reward_risk, 2),
        stop_atr=round(setup.stop_atr, 2),
        extension_atr=round(direction * (bar.close - tape.ema_slow[-1]) / setup.atr, 2),
        range_position=round(position if direction == 1 else 1 - position, 2),
        volume_ratio=round(setup.volume_ratio, 2),
        flow_imbalance=round(direction * flow, 2),
        trend_aligned=setup.trend_aligned,
        recent_moves_atr=[round(direction * (b - a) / setup.atr, 2) for a, b in zip(closes, closes[1:])],
    )


class SeatAnswer(BaseModel):
    id: str
    probability: float = Field(ge=0, le=1)
    reason: str = Field(max_length=300)


class SeatOutput(BaseModel):
    answers: list[SeatAnswer]
    thesis: str = Field(max_length=400)

    @field_validator("answers")
    @classmethod
    def exactly_the_questions(cls, answers: list[SeatAnswer]) -> list[SeatAnswer]:
        if sorted(answer.id for answer in answers) != sorted(QUESTION_TEXT):
            raise ValueError(f"answers must cover exactly: {', '.join(QUESTION_TEXT)}")
        order = list(QUESTION_TEXT)
        return sorted(answers, key=lambda answer: order.index(answer.id))


def _sigmoid(value: float) -> float:
    return 1 / (1 + math.exp(-value))


def heuristic_verdict(context: SeatContext) -> SeatOutput:
    """Deterministic answers from the same numbers the model sees."""
    chasing = _sigmoid(2.0 * (context.extension_atr - 2.6) + 1.5 * (context.range_position - 0.9))
    noise = _sigmoid(6.0 * (0.45 - context.stop_atr))
    against = _sigmoid(4.0 * (-context.flow_imbalance - 0.2))
    if not context.trend_aligned:
        against = 1 - (1 - against) * 0.75
    thin = _sigmoid(3.0 * (0.7 - context.volume_ratio))
    label = SETUP_LABELS.get(context.setup, context.setup).lower()
    return SeatOutput(
        answers=[
            SeatAnswer(
                id="chasing",
                probability=round(chasing, 3),
                reason=f"Price is {context.extension_atr:+.1f} ATR from the slow EMA, at {context.range_position:.0%} of the recent range.",
            ),
            SeatAnswer(id="noise_stop", probability=round(noise, 3), reason=f"The stop sits {context.stop_atr:.2f} ATR away."),
            SeatAnswer(
                id="against_context",
                probability=round(against, 3),
                reason=(
                    f"Flow reads {context.flow_imbalance:+.2f} in the trade's direction; the trend is "
                    f"{'aligned' if context.trend_aligned else 'not aligned'}."
                ),
            ),
            SeatAnswer(
                id="thin_volume", probability=round(thin, 3), reason=f"The signal bar traded {context.volume_ratio:.1f}x average volume."
            ),
        ],
        thesis=(
            f"A {context.side} {label} betting the move carries {context.reward_risk:.1f}R to the target before the stop."
        ),
    )


def _user_prompt(context: SeatContext) -> str:
    return json.dumps(
        {
            "questions": [{"id": question_id, "question": text} for question_id, text in SEAT_QUESTIONS],
            "context_notes": (
                "Prices are from 5-minute bars. *_atr values are in units of average true range. extension_atr, "
                "flow_imbalance and recent_moves_atr are signed so positive means in the trade's direction. "
                "range_position is 1 at the extreme of the last 20 bars in the trade's direction."
            ),
            "proposed_paper_order": asdict(context),
        }
    )


@dataclass
class SeatReview:
    output: SeatOutput
    source: str
    model: str | None
    note: str | None

    @property
    def worst(self) -> SeatAnswer:
        return max(self.output.answers, key=lambda answer: answer.probability)


class SkepticSeat:
    def __init__(self, config: DeskConfig, provider: ReportGenerationProvider | None = None) -> None:
        self.provider = provider or report_generation_provider
        self.ai_calls_left = config.ai_seat_budget if config.use_ai_seat and self.provider.is_live_configured else 0
        self.ai_calls = 0

    def review(self, context: SeatContext) -> SeatReview:
        if self.ai_calls_left <= 0:
            return SeatReview(heuristic_verdict(context), "heuristic", None, None)

        self.ai_calls_left -= 1
        self.ai_calls += 1
        try:
            result = self.provider.request_json(system_prompt=SYSTEM_PROMPT, user_prompt=_user_prompt(context))
            output = SeatOutput.model_validate_json(result.raw_output)
        except LLMProviderError as exc:
            note = f"AI seat unavailable ({exc}); the built-in scorer answered."
        except (ValidationError, ValueError):
            note = "AI seat's answer failed validation; the built-in scorer answered."
        else:
            return SeatReview(output, "llm", settings.llm_model_name, None)
        return SeatReview(heuristic_verdict(context), "heuristic", None, note)
