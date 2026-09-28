"""견줄 수 있는가 — 축이 **한 곳에만** 적혀 있다(DECISIONS §157).

★ 2026-09-28 하루에 같은 병을 여덟 번 앓았다. 까닭은 조건이 다섯 곳에 손으로 적혀 있던 것이다.
"""
import pathlib
import re

from seshat import compare

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_없는_값은_같음이_아니다():
    """옛 판에는 `metrics` 가 아예 없다 — 그것을 같음으로 치면 자를 바꾸기 전후가 조용히 섞인다."""
    갈린 = compare.갈림({"metrics": "2"}, {}, ("metrics",))
    assert 갈린 and 갈린[0].이름 == "자"


def test_같으면_비었다():
    가 = {"set_sha256": "x", "onto_sha256": "y", "metrics": "2", "backend": "팔"}
    assert compare.갈림(가, dict(가), compare.AA) == []


def test_AA_는_팔까지_본다():
    """같은 팔 두 판이어야 그 차이가 잡음이다."""
    가 = {"set_sha256": "x", "metrics": "2", "backend": "가팔"}
    assert [g.키 for g in compare.갈림(가, {**가, "backend": "나팔"}, compare.AA)] == ["backend"]
    assert compare.갈림(가, {**가, "backend": "나팔"}, compare.AB) == []


def test_문은_사전을_안_막는다():
    """사전을 막으면 사전을 영영 못 고친다(DECISIONS §32 · §96)."""
    assert "onto_sha256" not in compare.GATE_막
    assert "set_sha256" in compare.GATE_막 and "metrics" in compare.GATE_막


def test_보호는_그_지표만_가린다():
    """통째로 막지 않는다 — `term_off` 는 양쪽 다 모델이 만든 값이다(DECISIONS §156)."""
    assert compare.가린_지표({"protects": ["lit", "ui"]}, {}) == {"lit", "ui"}
    assert compare.가린_지표({"protects": ["lit"]}, {"protects": ["lit"]}) == set()


def test_축을_손으로_다시_적은_곳이_없다():
    """**이 시험이 §157 의 강제자다.** 축을 또 손으로 적으면 반드시 한 곳이 빠진다.

    2026-09-28 문의 `check` · 문의 선 줄 · `noise.SAME` · `compare_runs` 넷에 따로 적혀 있었고
    그중 셋이 서로 달랐다(§146 · §147 · §156).
    """
    쓰는곳 = ("tools/gate.py", "tools/noise.py", "tools/compare_runs.py")
    나쁜 = []
    for f in 쓰는곳:
        줄들 = (ROOT / f).read_text(encoding="utf-8").splitlines()
        for i, 줄 in enumerate(줄들, 1):
            몸 = 줄.split("#", 1)[0]
            if re.search(r'(get|\[)\("?(set_sha256|onto_sha256|metrics)"?\)?\s*!=', 몸):
                나쁜.append(f"{f}:{i} {줄.strip()[:80]}")
    assert not 나쁜, "축을 손으로 견주는 줄이 남았다 — `seshat/compare.py` 를 쓴다\n" + "\n".join(나쁜)
