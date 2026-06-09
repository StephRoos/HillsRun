"""Unit tests for the adaptive coach Lot D2 (AI reasoning layer).

The LLM call is always mocked — no network. The load-bearing invariant under
test is that the agent can never relax the rule verdict (a RED stays RED).
"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.training.adaptive.readiness import DailyVerdict, Verdict, _modification
from src.training.adaptive import readiness_agent
from src.training.adaptive.readiness_agent import (
    AgentRecommendation,
    _call_llm,
    _reconcile_verdict,
    build_agent_recommendation,
)
from src.training.adaptive.queries import explain_daily_readiness


def _verdict(v: Verdict, hrv=52.0) -> DailyVerdict:
    """Build a DailyVerdict anchor for tests."""
    return DailyVerdict(
        verdict=v,
        reason=f"rule says {v.value}",
        suggested_modification=_modification(v),
        hrv_value=hrv,
        baseline_low=48.0,
        baseline_high=56.0,
    )


def _llm_reply(verdict: str):
    """A well-formed agent draft for a given proposed verdict."""
    return {
        "verdict": verdict,
        "headline": "Headline",
        "rationale": "Une explication courte.",
        "adjustment": "Ajustement proposé.",
    }


# ---------------------------------------------------------------------------
# _reconcile_verdict — the anchoring invariant
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "anchor,proposed,expected,anchored",
    [
        (Verdict.RED, Verdict.GREEN, Verdict.RED, True),  # the key invariant
        (Verdict.RED, Verdict.AMBER, Verdict.RED, True),
        (Verdict.RED, Verdict.RED, Verdict.RED, False),
        (Verdict.AMBER, Verdict.GREEN, Verdict.AMBER, True),
        (Verdict.GREEN, Verdict.AMBER, Verdict.AMBER, False),  # escalation allowed
        (Verdict.GREEN, Verdict.RED, Verdict.RED, False),
        (Verdict.GREEN, Verdict.GREEN, Verdict.GREEN, False),
    ],
)
def test_reconcile_never_relaxes(anchor, proposed, expected, anchored):
    assert _reconcile_verdict(anchor, proposed) == (expected, anchored)


# ---------------------------------------------------------------------------
# build_agent_recommendation
# ---------------------------------------------------------------------------


def test_red_cannot_become_green():
    """Agent proposes GREEN on a RED day -> stays RED, flagged anchored."""
    with patch.object(readiness_agent, "_call_llm", return_value=_llm_reply("green")):
        rec = build_agent_recommendation(_verdict(Verdict.RED), client=MagicMock())
    assert rec.verdict is Verdict.RED
    assert rec.anchored is True
    assert rec.suggested_modification == _modification(Verdict.RED)


def test_agent_may_escalate_caution():
    """GREEN rule + AMBER agent proposal -> AMBER (more cautious is allowed)."""
    with patch.object(readiness_agent, "_call_llm", return_value=_llm_reply("amber")):
        rec = build_agent_recommendation(_verdict(Verdict.GREEN), client=MagicMock())
    assert rec.verdict is Verdict.AMBER
    assert rec.anchored is False


def test_output_schema_shape():
    """Returned object is a fully-populated AgentRecommendation."""
    with patch.object(readiness_agent, "_call_llm", return_value=_llm_reply("green")):
        rec = build_agent_recommendation(
            _verdict(Verdict.GREEN),
            planned_session={"title": "Endurance", "sport_type": "road_running"},
            recent_context=[{"date": "2026-06-06", "verdict": "green", "hrv_value": 51.0}],
            client=MagicMock(),
            model="claude-haiku-4-5",
        )
    assert isinstance(rec, AgentRecommendation)
    assert rec.verdict is Verdict.GREEN
    assert rec.headline and rec.rationale and rec.adjustment
    assert rec.model == "claude-haiku-4-5"


def test_insufficient_baseline_skips_llm():
    """No baseline -> no LLM call, echoes the rule verdict at zero cost."""
    boom = MagicMock(side_effect=AssertionError("LLM must not be called"))
    with patch.object(readiness_agent, "_call_llm", boom):
        rec = build_agent_recommendation(
            _verdict(Verdict.INSUFFICIENT_BASELINE), client=MagicMock()
        )
    assert rec.verdict is Verdict.INSUFFICIENT_BASELINE
    assert rec.model == ""
    assert rec.anchored is False


def test_call_llm_parses_json_content():
    """_call_llm extracts the text block and json-decodes it."""
    block = SimpleNamespace(type="text", text='{"verdict": "amber", "headline": "h",'
                            ' "rationale": "r", "adjustment": "a"}')
    response = SimpleNamespace(content=[block])
    client = MagicMock()
    client.messages.create.return_value = response

    out = _call_llm(client, system="s", user="u", model="claude-haiku-4-5")
    assert out["verdict"] == "amber"
    # output_config.format must be passed so the model returns valid JSON.
    _, kwargs = client.messages.create.call_args
    assert kwargs["output_config"]["format"]["type"] == "json_schema"
    assert kwargs["model"] == "claude-haiku-4-5"


# ---------------------------------------------------------------------------
# explain_daily_readiness — mocked-pool orchestrator smoke
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_explain_orchestrator_persists_rationale():
    """End-to-end (mocked pool + LLM): fetches context, runs agent, persists."""
    pool = MagicMock()
    # fetchrow is called twice: planned session, then the persist UPDATE.
    pool.fetchrow = AsyncMock(
        side_effect=[
            {"title": "Seuil", "sport_type": "road_running",
             "planned_duration_seconds": 3600},  # planned session
            {"id": 1, "ai_rationale": "Une explication courte."},  # UPDATE RETURNING
        ]
    )
    pool.fetch = AsyncMock(
        return_value=[
            {"date": date(2026, 6, 6), "verdict": "green", "hrv_value": 51.0},
        ]
    )

    with patch.object(readiness_agent, "_call_llm", return_value=_llm_reply("red")):
        rec = await explain_daily_readiness(
            pool,
            user_id=42,
            day=date(2026, 6, 8),
            base_result=_verdict(Verdict.RED),
            client=MagicMock(),
        )

    assert rec.verdict is Verdict.RED  # anchored, even though we asked for red here
    # The persist UPDATE must target the AI columns, not the verdict column.
    update_sql = pool.fetchrow.call_args_list[1].args[0]
    assert "ai_rationale" in update_sql
    assert "SET verdict" not in update_sql


@pytest.mark.asyncio
async def test_explain_orchestrator_can_skip_persist():
    """persist=False -> agent runs but no UPDATE is issued."""
    pool = MagicMock()
    pool.fetchrow = AsyncMock(return_value=None)  # no planned session
    pool.fetch = AsyncMock(return_value=[])

    with patch.object(readiness_agent, "_call_llm", return_value=_llm_reply("green")):
        rec = await explain_daily_readiness(
            pool,
            user_id=42,
            day=date(2026, 6, 8),
            base_result=_verdict(Verdict.GREEN),
            persist=False,
            client=MagicMock(),
        )

    assert rec.verdict is Verdict.GREEN
    # Only the planned-session fetchrow ran — no UPDATE.
    assert pool.fetchrow.call_count == 1
