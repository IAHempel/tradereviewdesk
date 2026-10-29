import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.schemas.desk import DeskConfig
from app.services.desk import seat as seat_module
from app.services.desk.engine import run_desk_session
from app.services.desk.seat import SeatContext, heuristic_verdict
from app.services.report_generation_provider import LLMProviderError, ProviderGenerationResult

SYMBOLS = ["AAPL", "NVDA", "SPY", "QQQ"]


class FakeModel:
    """Stands in for the OpenAI provider; `answer` returns the raw text the model would send."""

    def __init__(self, answer, *, configured: bool = True) -> None:
        self.answer = answer
        self.is_live_configured = configured
        self.prompts: list[tuple[str, str]] = []

    def request_json(self, *, system_prompt: str, user_prompt: str) -> ProviderGenerationResult:
        self.prompts.append((system_prompt, user_prompt))
        raw = self.answer(json.loads(user_prompt))
        if isinstance(raw, Exception):
            raise raw
        return ProviderGenerationResult(raw_output=raw)


def answers(probabilities: dict[str, float], thesis: str = "Betting the breakout holds.") -> str:
    return json.dumps(
        {
            "answers": [{"id": key, "probability": value, "reason": f"{key} reason"} for key, value in probabilities.items()],
            "thesis": thesis,
        }
    )


CALM = {"chasing": 0.1, "noise_stop": 0.1, "against_context": 0.1, "thin_volume": 0.1}


def run(model: FakeModel | None = None, **overrides):
    config = DeskConfig(**{"symbols": SYMBOLS, "seed": 21, "sessions": 2, **overrides})
    if model is None:
        return run_desk_session(config, watchlist_symbols=[], journal_trades=[])
    with patch.object(seat_module, "report_generation_provider", model):
        return run_desk_session(config, watchlist_symbols=[], journal_trades=[])


class HeuristicSeatTests(unittest.TestCase):
    def test_answers_cover_the_questions_in_order(self) -> None:
        context = SeatContext("AAPL", "breakout", "long", "10:00", 100, 99, 102.5, 2.5, 0.8, 3.4, 1.0, 0.5, -0.4, False, [0.5, 0.9])
        verdict = heuristic_verdict(context)
        self.assertEqual([answer.id for answer in verdict.answers], ["chasing", "noise_stop", "against_context", "thin_volume"])
        self.assertTrue(all(0 <= answer.probability <= 1 for answer in verdict.answers))
        by_id = {answer.id: answer.probability for answer in verdict.answers}
        self.assertGreater(by_id["chasing"], 0.7)
        self.assertGreater(by_id["against_context"], 0.7)
        self.assertGreater(by_id["thin_volume"], 0.5)
        self.assertLess(by_id["noise_stop"], 0.2)

    def test_runs_without_a_key_use_the_built_in_scorer(self) -> None:
        result = run()
        self.assertGreater(result.pipeline.seat_reviews, 0)
        self.assertEqual(result.pipeline.seat_ai_calls, 0)
        self.assertTrue(all(verdict.source == "heuristic" for verdict in result.seat_verdicts))
        self.assertEqual(run().model_dump_json(), result.model_dump_json())

    def test_every_trade_has_a_passing_verdict_and_vetoes_have_none(self) -> None:
        result = run(sessions=4)
        traded = {trade.id for trade in result.trades}
        passed = {verdict.trade_id for verdict in result.seat_verdicts if not verdict.vetoed}
        self.assertTrue(traded <= passed)
        self.assertTrue(all(verdict.trade_id is None for verdict in result.seat_verdicts if verdict.vetoed))
        self.assertEqual(result.pipeline.seat_vetoes, sum(verdict.vetoed for verdict in result.seat_verdicts))
        self.assertEqual(result.pipeline.seat_reviews, len(result.seat_verdicts))

    def test_threshold_of_one_never_vetoes(self) -> None:
        self.assertEqual(run(seat_veto=1.0, sessions=4).pipeline.seat_vetoes, 0)


class ModelSeatTests(unittest.TestCase):
    def test_model_answers_drive_vetoes(self) -> None:
        model = FakeModel(lambda prompt: answers({**CALM, "chasing": 0.9}))
        result = run(model, ai_seat_budget=30)
        self.assertGreater(result.pipeline.seat_ai_calls, 0)
        llm_verdicts = [verdict for verdict in result.seat_verdicts if verdict.source == "llm"]
        self.assertTrue(llm_verdicts)
        self.assertTrue(all(verdict.vetoed for verdict in llm_verdicts))
        self.assertTrue(any(reason.code == "seat_veto" for reason in result.kill_reasons))
        vetoed_steps = {(verdict.step, verdict.symbol) for verdict in llm_verdicts}
        self.assertFalse(any((trade.open_step - 1, trade.symbol) in vetoed_steps for trade in result.trades))

    def test_calm_model_answers_let_orders_through_with_its_thesis(self) -> None:
        model = FakeModel(lambda prompt: answers(CALM, "Betting buyers defend the reclaimed level."))
        result = run(model)
        verdict = next(verdict for verdict in result.seat_verdicts if verdict.source == "llm")
        self.assertFalse(verdict.vetoed)
        self.assertIsNotNone(verdict.trade_id)
        self.assertEqual(verdict.thesis, "Betting buyers defend the reclaimed level.")
        self.assertEqual(verdict.model, "gpt-4.1-mini")

    def test_budget_caps_model_calls(self) -> None:
        model = FakeModel(lambda prompt: answers(CALM))
        result = run(model, ai_seat_budget=2, sessions=3)
        self.assertEqual(len(model.prompts), 2)
        self.assertEqual(result.pipeline.seat_ai_calls, 2)
        self.assertEqual(sum(verdict.source == "llm" for verdict in result.seat_verdicts), 2)
        self.assertGreater(sum(verdict.source == "heuristic" for verdict in result.seat_verdicts), 0)

    def test_bad_or_failed_answers_fall_back_with_a_note(self) -> None:
        cases = [
            ("not json", "failed validation"),
            (answers({"chasing": 0.2}), "failed validation"),
            (answers({**CALM, "chasing": 1.7}), "failed validation"),
            (LLMProviderError("OpenAI request failed: APITimeoutError"), "AI seat unavailable"),
        ]
        for raw, note in cases:
            with self.subTest(note=note, raw=str(raw)[:30]):
                result = run(FakeModel(lambda prompt, raw=raw: raw), ai_seat_budget=1)
                self.assertEqual(result.seat_verdicts[0].source, "heuristic")
                self.assertTrue(any(event.kind == "fallback" and note in event.message for event in result.events))

    def test_opting_out_or_no_key_makes_no_calls(self) -> None:
        for model, overrides in (
            (FakeModel(lambda prompt: answers(CALM)), {"use_ai_seat": False}),
            (FakeModel(lambda prompt: answers(CALM), configured=False), {}),
        ):
            result = run(model, **overrides)
            self.assertEqual(model.prompts, [])
            self.assertEqual(result.pipeline.seat_ai_calls, 0)

    def test_prompt_keeps_the_compliance_boundary_and_numbers(self) -> None:
        model = FakeModel(lambda prompt: answers(CALM))
        run(model, ai_seat_budget=1)
        system_prompt, user_prompt = model.prompts[0]
        self.assertIn("Do not recommend buying, selling, or any trade", system_prompt)
        payload = json.loads(user_prompt)
        self.assertEqual([item["id"] for item in payload["questions"]], ["chasing", "noise_stop", "against_context", "thin_volume"])
        order = payload["proposed_paper_order"]
        for key in ("symbol", "side", "entry", "stop", "target", "stop_atr", "extension_atr", "flow_imbalance"):
            self.assertIn(key, order)


if __name__ == "__main__":
    unittest.main()
