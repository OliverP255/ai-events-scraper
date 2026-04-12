"""Unit tests for enterprise LLM batch filtering (mocked HTTP)."""

from __future__ import annotations

from datetime import datetime

import httpx
import pytest

from ai_events.enterprise_llm import (
    BATCH_SIZE,
    _extract_json_object,
    _labels_from_response,
    filter_enterprise_events,
)
from ai_events.models import RawEvent


def _ev(title: str, description: str = "Desc", url: str = "https://example.com/e/1") -> RawEvent:
    return RawEvent(
        source="test",
        url=url,
        title=title,
        description=description,
        starts_at=datetime(2026, 6, 1, 10, 0, 0),
        ends_at=None,
        venue=None,
        city="London",
        country="GB",
        is_in_person=True,
        attendance_mode_uri=None,
        extra={},
    )


def test_filter_disabled_returns_all(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENTERPRISE_LLM_ENABLED", raising=False)
    transport = httpx.MockTransport(lambda r: httpx.Response(500))
    evs = [_ev("a"), _ev("b")]
    with httpx.Client(transport=transport) as client:
        out = filter_enterprise_events(client, evs, enabled=False)
    assert len(out) == 2


def test_filter_unset_env_skips_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unset ENTERPRISE_LLM_ENABLED keeps LLM off (pass-through)."""
    monkeypatch.delenv("ENTERPRISE_LLM_ENABLED", raising=False)
    transport = httpx.MockTransport(lambda r: httpx.Response(500))
    evs = [_ev("a")]
    with httpx.Client(transport=transport) as client:
        out = filter_enterprise_events(client, evs, enabled=None)
    assert len(out) == 1


def test_filter_explicit_zero_skips_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENTERPRISE_LLM_ENABLED", "0")
    transport = httpx.MockTransport(lambda r: httpx.Response(500))
    evs = [_ev("a")]
    with httpx.Client(transport=transport) as client:
        out = filter_enterprise_events(client, evs, enabled=None)
    assert len(out) == 1


def test_filter_keeps_only_ones(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENTERPRISE_LLM_ENABLED", "1")

    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read().decode()
        # batch of 5: return 1,0,1,1,0
        if '"model"' in body:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": '{"labels":[1,0,1,1,0]}',
                            }
                        }
                    ]
                },
            )
        return httpx.Response(400)

    transport = httpx.MockTransport(handler)
    evs = [_ev("t0"), _ev("t1"), _ev("t2"), _ev("t3"), _ev("t4")]
    with httpx.Client(transport=transport) as client:
        out = filter_enterprise_events(client, evs, enabled=True)
    assert len(out) == 3
    assert [e.title for e in out] == ["t0", "t2", "t3"]


def test_second_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENTERPRISE_LLM_ENABLED", "1")
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        payload = request.read().decode()
        if "There are exactly 5 events below" in payload:
            labels = [1, 0, 1, 1, 0]
        elif "There are exactly 2 events below" in payload:
            labels = [1, 0]
        else:
            return httpx.Response(400, text="unexpected batch")
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": f'{{"labels":{labels!r}}}'}}]},
        )

    transport = httpx.MockTransport(handler)
    evs = [_ev(f"t{i}", url=f"https://example.com/e/{i}") for i in range(7)]
    with httpx.Client(transport=transport) as client:
        out = filter_enterprise_events(client, evs, enabled=True)
    assert len(calls) == 2
    assert BATCH_SIZE == 5
    # [1,0,1,1,0] -> t0,t2,t3; [1,0] -> t5
    assert len(out) == 4
    assert {e.title for e in out} == {"t0", "t2", "t3", "t5"}


def test_extract_json_with_prefix() -> None:
    obj = _extract_json_object('Sure. {"labels": [1, 0]}')
    assert obj == {"labels": [1, 0]}


def test_labels_from_response() -> None:
    assert _labels_from_response('{"labels":[1,0,1]}', 3) == [1, 0, 1]
    assert _labels_from_response('{"labels":[true,false]}', 2) == [1, 0]
    assert _labels_from_response('{"labels":[1]}', 2) is None
