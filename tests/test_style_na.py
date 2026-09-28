"""합쇼체가 설 수 없는 줄의 후보 뽑기(DECISIONS §189 · §194)."""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("sna", ROOT / "tools/style_na.py")
sna = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sna)


def _판(tmp_path, 이름, 출력들, 셋해시="셋"):
    p = tmp_path / f"{이름}.jsonl"
    줄 = [{"meta": True, "set_sha256": 셋해시, "set": "data/domain/x.jsonl", "metrics": "3"}]
    줄 += [{"id": i, "out": o} for i, o in 출력들.items()]
    p.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in 줄) + "\n", encoding="utf-8")
    return str(p)


def test_다_틀린_줄만_후보다(tmp_path):
    """★ **한 팔만 틀리면 그 팔의 실력이다**(DECISIONS §189). 넷이 다 틀려야 줄을 의심한다."""
    가 = sna.read(_판(tmp_path, "a", {"1": "합니다.", "2": "목록.", "3": "봅니다."}))
    나 = sna.read(_판(tmp_path, "b", {"1": "합니다.", "2": "목록.", "3": "본다."}))
    셈 = sna.못맞힌_줄([가, 나])
    assert 셈["2"] == 2, "둘 다 종결이 아니다"
    assert 셈["3"] == 1, "한 판만 아니다"
    assert "1" not in 셈


def test_딴_셋의_판을_섞으면_멈춘다(tmp_path, capsys):
    """★ **다른 글의 줄 번호를 섞으면 후보가 거짓이 된다**(§45)."""
    가 = _판(tmp_path, "a", {"1": "합니다."})
    나 = _판(tmp_path, "b", {"1": "합니다."}, 셋해시="딴셋")
    assert sna.main([가, 나]) == 1
    assert "딴 셋이다" in capsys.readouterr().err


def test_판정은_사람이_한다():
    """★ **자동으로 가르지 않는다**(DECISIONS §189). 「완전한 문장인가」 는 규칙으로 못 가르고,
    가르는 파서를 놓으면 **그 파서가 또 자가 된다.** 이 도구는 후보만 준다."""
    글 = (ROOT / "tools/style_na.py").read_text(encoding="utf-8")
    assert "후보다, 판정이 아니다" in 글
    assert "style-na.txt" in 글, "판정을 적을 자리를 알려줘야 한다 — 눈으로 보고 넘기면 다음 달에 또 본다"


def test_없는_셋이면_멈춘다(tmp_path):
    가 = _판(tmp_path, "a", {"1": "합니다."})
    with pytest.raises(SystemExit):
        sna.main([가, "--set", str(tmp_path / "없는셋.jsonl")])
