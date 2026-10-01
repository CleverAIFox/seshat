"""transformers 없이 도는 자 — 꼴과 조건이 옳은가(DECISIONS §253 · H-086).

★ 이 파일은 **seshat 것**이다 — thoth 사본이 아니다(DECISIONS §5).
★ **ollama 를 안 부른다.** 보는 것은 **답을 읽는 법 · 못 읽은 답의 처리 · 조건 칸 · 지시문의 규율**이다.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import pytest

ROOT = next(p for p in pathlib.Path(__file__).resolve().parents if (p / "tools/gemba.py").exists())
_spec = importlib.util.spec_from_file_location("gemba", ROOT / "tools/gemba.py")
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)


def test_수를_읽는다():
    assert G.읽는다("87") == 87.0
    assert G.읽는다("  100  ") == 100.0
    assert G.읽는다("0") == 0.0


def test_못_읽은_답은_0_이_아니라_None_이다():
    """★ **「모른다」 와 「최악이다」 는 다르다** — 0 으로 적으면 못 읽은 줄이 최악의 줄이 된다."""
    assert G.읽는다("좋습니다") is None
    assert G.읽는다("") is None
    assert G.읽는다("101") is None                 # 범위 밖은 안 받는다
    assert G.읽는다("-5") is None


def test_못_읽은_줄은_안_내고_센다():
    """★ **버리지 않고 센다**(DECISIONS §244 와 같은 규율)."""
    글 = (ROOT / "tools/gemba.py").read_text(encoding="utf-8")
    assert "if v is not None" in 글 and '"못읽음"' in 글


def test_뒤집지_않는다():
    """★ **뒤집는 자리를 자마다 하나씩만 둔다** — MetricX 는 오류 점수라 `qe.py` 가 뒤집는다."""
    글 = (ROOT / "tools/gemba.py").read_text(encoding="utf-8")
    assert '"뒤집었다": False' in 글
    assert '"score": v' in 글 and '"score": -' not in 글


def test_지시문이_판정_규율을_지킨다():
    """★ 참조가 없고 · 찾아보지 않고 · 어느 팔인지 안 알린다(§108 · §227 · §223)."""
    assert "no reference translation" in G.체계
    assert "Do not look anything up" in G.체계
    assert "Output ONLY the integer" in G.체계
    for 팔 in ("gemma", "nova", "4b", "12b"):
        assert 팔 not in G.체계.lower(), f"지시문이 팔을 알린다 — {팔}"


def test_대장이_이_모형을_안다():
    """★ **코드가 부르는 가중치는 전부 대장에 있어야 한다**(DECISIONS §6)."""
    import sys
    sys.path.insert(0, str(ROOT))
    from seshat import licenses
    row = licenses.LEDGER[G.대장이름]
    assert row[0] == "Apache-2.0" and row[1] == "yes" and row[2] == "yes"


def test_팔들과_집안이_다르다():
    """★ **판정자가 팔의 집안이면 제 출력을 판정한다**(§227 의 ⚠ 와 같은 자리)."""
    assert "qwen" in G.기본모형.lower()
    assert "gemma" not in G.기본모형.lower() and "nova" not in G.기본모형.lower()


def test_표를_주면_그_표가_물어본_자리만_잰다(tmp_path, monkeypatch):
    """★ 자를 검증하는 데 드는 것은 **사람이 본 자리**뿐이다 — 1,800 을 다 물으면 열 배다."""
    labels = G._도구("labels")
    monkeypatch.setattr(labels, "out_dir", lambda: tmp_path)
    monkeypatch.setattr(G, "_도구", lambda 이름: labels if 이름 == "labels" else _가짜qe)

    class _가짜qe:
        @staticmethod
        def 줄을_모은다(판, setpath=""):
            return [{"id": f"x{i}", "arm": a, "src": "S", "out": "O"}
                    for i in range(3) for a in ("4b", "12b")]

    줄들 = [{"meta": True}] + [{"tag": f"t{i}", "id": f"x{i}", "arm": "4b"} for i in range(2)]
    (tmp_path / "t.key.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in 줄들) + "\n", encoding="utf-8")
    난것 = G.물을_줄({}, "t")
    assert [(x["id"], x["arm"]) for x in 난것] == [("x0", "4b"), ("x1", "4b")]


def test_없는_표는_말을_한다(tmp_path, monkeypatch):
    labels = G._도구("labels")
    monkeypatch.setattr(labels, "out_dir", lambda: tmp_path)
    monkeypatch.setattr(G, "_도구", lambda 이름: labels if 이름 == "labels" else _빈qe)

    class _빈qe:
        @staticmethod
        def 줄을_모은다(판, setpath=""):
            return [{"id": "x0", "arm": "4b", "src": "S", "out": "O"}]

    try:
        G.물을_줄({}, "없는표")
    except SystemExit as e:
        assert "표의 열쇠가 없다" in str(e) and "--표 를 뺀다" in str(e)
    else:
        raise AssertionError("안 멈췄다")


# ── 한 줄씩 쓰고 이어서 돈다(DECISIONS §272) ──────────────────────────────────

def test_로그로_나가면_줄바꿈으로_찍는다(capsys, monkeypatch):
    """★ **`\\r` 는 터미널에서만 진행이다**(DECISIONS §272).

    1,200 판정을 백그라운드로 던진 사람이 **한 시간 동안 살아 있는지도 몰랐다** —
    파일로 리다이렉트하면 `\\r` 가 한 줄을 덮어써서 `tail` 에 아무것도 안 보인다.
    """
    monkeypatch.setattr(sys.stderr, "isatty", lambda: False, raising=False)
    for i in (1, 20, 21, 40, 100):
        G._진행(i, 100)
    err = capsys.readouterr().err
    assert err.count("\n") == 4, err          # 1 · 20 · 40 · 100(끝) — 21 은 안 찍는다
    assert "\r" not in err


def test_이미_잰_것은_안_묻는다(tmp_path):
    """★ **끊기면 GPU 시간이 통째로 날아간다**(DECISIONS §272 · §21 — `runs/` 는 다시 못 만든다)."""
    머리 = {"meta": True, "model": "qwen3:8b", "체계_sha": "abc123"}
    p = tmp_path / "g.jsonl"
    p.write_text("\n".join([
        json.dumps(머리, ensure_ascii=False),
        json.dumps({"id": "a", "arm": "4b", "score": 70}, ensure_ascii=False),
    ]) + "\n", encoding="utf-8")
    got = G.이미_잰_것(p, 머리)
    assert got == {("a", "4b"): 70}


def test_자가_다르면_안_이어_돈다(tmp_path):
    """★ **이어서 도는 것과 섞는 것은 다르다** — 한 파일에 두 자가 섞이면 **아무 물음에도 답 못 한다**."""
    p = tmp_path / "g.jsonl"
    p.write_text(json.dumps({"meta": True, "model": "qwen3:8b", "체계_sha": "옛것"},
                            ensure_ascii=False) + "\n", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        G.이미_잰_것(p, {"model": "qwen3:8b", "체계_sha": "새것"})
    글 = str(e.value)
    assert "다른 자로 잰 것" in 글 and "체계_sha" in 글
    assert "--out <새 이름>" in 글, "막기만 하고 길을 안 줬다(DECISIONS §210)"


def test_없는_파일은_빈_것으로_본다(tmp_path):
    """★ 처음 도는 판은 **이어 돌 것이 없다** — 그것은 오류가 아니다."""
    assert G.이미_잰_것(tmp_path / "없다.jsonl", {"model": "x", "체계_sha": "y"}) == {}
