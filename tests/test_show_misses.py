"""숫자 뒤의 줄을 보는 도구(DECISIONS §53)."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("show_misses", ROOT / "tools/show_misses.py")
sm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sm)


def _set(tmp_path: pathlib.Path) -> pathlib.Path:
    p = tmp_path / "probes.jsonl"
    p.write_text(json.dumps({"id": "p1", "src": "Configure Amazon Athena for the data lake.",
                             "keep": ["Amazon Athena"]}, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def _run(tmp_path: pathlib.Path, out: str) -> tuple[dict, list[dict]]:
    s = _set(tmp_path)
    meta = {"meta": True, "backend": "t", "set": str(s),
            "set_sha256": hashlib.sha256(s.read_bytes()).hexdigest()[:16]}
    return meta, [{"id": "p1", "src": "Configure Amazon Athena for the data lake.", "out": out}]


def test_사라진_이름을_이름으로_말한다(tmp_path):
    meta, rows = _run(tmp_path, "데이터 레이크를 위해 아마존 아테나를 구성합니다.")
    got = sm.misses(meta, rows, "keep")
    assert [w for w, _, _ in got] == ["keep"]
    assert "Amazon Athena" in got[0][2]


def test_이름이_남았으면_걸리지_않는다(tmp_path):
    meta, rows = _run(tmp_path, "데이터 레이크를 위해 Amazon Athena를 구성합니다.")
    assert sm.misses(meta, rows, "keep") == []


def test_번역이_아닌_줄은_그_까닭_하나로_끝낸다(tmp_path):
    """사고문은 keep 도 term 도 style 도 다 틀린다 — 까닭 넷을 늘어놓으면 읽히지 않는다."""
    meta, rows = _run(tmp_path, "Okay, the user wants me to translate this into Korean. Let me think.")
    got = sm.misses(meta, rows, "all")
    assert [w for w, _, _ in got] == ["hangul"]


def test_셋이_바뀌었으면_멈춘다(tmp_path):
    meta, rows = _run(tmp_path, "무엇이든")
    meta["set_sha256"] = "0" * 16
    with pytest.raises(SystemExit):
        sm.misses(meta, rows, "keep")


def test_결과_파일이_아니면_멈춘다(tmp_path):
    p = tmp_path / "x.jsonl"
    p.write_text('{"id": "p1"}\n', encoding="utf-8")
    with pytest.raises(SystemExit):
        sm.read(p)
