"""개념 단위 대조 — 누가 어느 용어에서 이겼나(DECISIONS §85)."""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("term_diff", ROOT / "tools/term_diff.py")
td = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(td)

SRC = "The team uses the data lake for ingestion."


def _run(path: pathlib.Path, backend: str, out: str, *, onto="aaa", 셋="bbb") -> pathlib.Path:
    머리 = {"meta": True, "backend": backend, "set_sha256": 셋, "onto_sha256": onto}
    줄 = {"id": "p1", "src": SRC, "out": out}
    path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in (머리, 줄)) + "\n", encoding="utf-8")
    return path


def test_다른_자로_잰_것은_나란히_놓지_않는다(tmp_path):
    a = _run(tmp_path / "a.jsonl", "A", "데이터 레이크 수집")
    b = _run(tmp_path / "b.jsonl", "B", "데이터 레이크 수집", onto="zzz")
    with pytest.raises(SystemExit) as e:
        td.같은_자인가(td.read(a)[0], td.read(b)[0])
    assert "사전" in str(e.value)


def test_한_쪽만_공식_표기를_쓴_개념을_집는다(tmp_path):
    from seshat import ontology
    onto = ontology.load()
    a = td.read(_run(tmp_path / "a.jsonl", "A", "팀은 데이터 레이크를 수집에 씁니다."))[1]
    b = td.read(_run(tmp_path / "b.jsonl", "B", "팀은 데이터 호수를 수집에 씁니다."))[1]
    갈림 = td.가른다(onto, a, b)
    assert [d["en"] for d in 갈림] == ["data lake"]
    assert 갈림[0]["a"] is True and 갈림[0]["ko"] == "데이터 레이크"


def test_둘_다_맞거나_둘_다_틀리면_안_집는다(tmp_path):
    from seshat import ontology
    onto = ontology.load()
    같음 = "팀은 데이터 레이크를 수집에 씁니다."
    a = td.read(_run(tmp_path / "a.jsonl", "A", 같음))[1]
    b = td.read(_run(tmp_path / "b.jsonl", "B", 같음))[1]
    assert td.가른다(onto, a, b) == []


def test_갈린_자리가_적으면_잡음과_구별되지_않는다():
    """h003 의 4 대 11 은 눈에는 12B 승이지만 동전으로도 12% 확률이다(DECISIONS §88)."""
    assert td.부호검정(4, 11) > 0.05
    assert td.부호검정(21, 8) < 0.05          # h001 — 이만큼 갈리면 말할 수 있다
    assert td.부호검정(9, 25) < 0.01
    assert td.부호검정(0, 0) == 1.0           # 갈린 자리가 없으면 아무 말도 안 한다
    assert td.부호검정(7, 7) == 1.0           # 반반이면 차이가 없다
