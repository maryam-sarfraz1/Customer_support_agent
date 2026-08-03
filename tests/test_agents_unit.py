"""Unit tests for agent helpers and prompt-parsing edge cases."""

from __future__ import annotations

from app.agents.nodes import _format_context, _format_history, _parse_json


def test_parse_json_plain() -> None:
    assert _parse_json('{"intent": "question"}') == {"intent": "question"}


def test_parse_json_embedded_in_prose() -> None:
    text = 'Sure! Here is the analysis:\n```json\n{"a": 1}\n```\nDone.'
    assert _parse_json(text) == {"a": 1}


def test_parse_json_garbage_returns_empty() -> None:
    assert _parse_json("no json here") == {}
    assert _parse_json("{broken json") == {}
    assert _parse_json("[1, 2, 3]") == {}


def test_format_history_empty() -> None:
    assert "(no prior messages)" in _format_history([])


def test_format_history_truncates_long_content() -> None:
    history = [{"role": "user", "content": "x" * 2000}]
    out = _format_history(history)
    assert len(out) < 600


def test_format_context_empty() -> None:
    assert "(no relevant context found)" in _format_context([])


def test_format_context_numbers_passages() -> None:
    chunks = [
        {
            "content": "Refunds take 5 days.",
            "title": "Refund Policy",
            "source_type": "policy",
            "source_url": "",
            "score": 0.9,
        }
    ]
    out = _format_context(chunks)
    assert "[1]" in out
    assert "Refund Policy" in out
