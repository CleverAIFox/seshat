"""짝지은 부트스트랩이 제구실을 하나(DECISIONS §180).

★ **이 시험이 막는 것은 「손으로 그은 선」 이다.** 2026-09-28 하루에 세 번 그었고 세 번 틀렸다
  (§139 · §178 · §179). 자가 살아 있는지는 **알려진 답**으로만 잰다.
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("bs", ROOT / "tools/bootstrap.py")
bs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bs)


def 표(맞음: int, 전체: int) -> list[tuple[float, float]]:
    return [(1.0, 1.0)] * 맞음 + [(0.0, 1.0)] * (전체 - 맞음)


def test_프로브가_살아_있다():
    assert bs._selftest() == 0


def test_같은_둘은_구간이_0_을_품는다():
    가 = 표(300, 600)
    got = bs.잰다(가, list(가), n=300)
    assert got["차"] == 0.0
    assert got["아래"] <= 0 <= got["위"]
    assert got["p"] > 0.5, "같은 둘에 작은 p 를 주면 아무 차이나 유의해진다"


def test_뚜렷이_다른_둘은_0_을_안_품는다():
    got = bs.잰다(표(300, 600), 표(480, 600), n=300)
    assert got["아래"] > 0 and got["p"] < 0.05


def test_한쪽으로만_8줄이면_작아도_유의하다():
    """★ **크기가 작은 것과 못 가르는 것은 다르다**(DECISIONS §180).

    600 중 8줄이라도 **B 만 지고 A 는 안 지면** 재표집마다 부호가 같아서 구간이 0 을 안 품는다.
    §179 에 적은 「8줄은 작다」 는 **크기 판단**이었지 유의성 판단이 아니었다 — 손으로 그으면
    그 둘이 섞인다. 이 도구는 **크기와 확실함을 따로 준다.**
    """
    got = bs.잰다(표(300, 600), 표(308, 600), n=600)
    assert got["아래"] > 0, "한쪽으로만 난 차이는 작아도 확실하다"
    assert abs(got["차"]) < 0.02, "그러면서도 크기는 작다 — 두 가지를 같이 읽는다"


def test_양쪽에서_엇갈리면_못_가른다():
    """★ **이것이 「못 가른다」 의 참모습이다.** B 가 여덟 줄 이기고 일곱 줄 지면 순증은 한 줄이고,
    재표집마다 부호가 뒤집힌다 — **평균만 보면 「B 가 낫다」 로 읽힌다.**"""
    가 = [(1.0, 1.0)] * 7 + [(0.0, 1.0)] * 8 + [(1.0, 1.0)] * 585
    나 = [(0.0, 1.0)] * 7 + [(1.0, 1.0)] * 8 + [(1.0, 1.0)] * 585
    got = bs.잰다(가, 나, n=800)
    assert got["차"] > 0, "평균으로는 B 가 낫다"
    assert got["아래"] <= 0 <= got["위"], "그런데 구간이 0 을 품는다 — 못 가른다"
    assert got["p"] > 0.05


def test_분모가_줄마다_다르면_다시_더한다():
    """★ **줄별 비율을 평균내면 틀린다**(§180). 자리가 하나인 줄과 열인 줄은 무게가 다르다."""
    가 = [(0.0, 10.0), (1.0, 1.0)]          # 다시 더하면 1/11 · 줄 평균이면 0.5
    assert bs.비율(가, [0, 1]) == pytest.approx(1 / 11)


def test_분모가_없으면_안_잰다():
    assert bs.잰다([(0.0, 0.0)] * 5, [(0.0, 0.0)] * 5, n=10) is None


def test_같은_씨는_같은_수를_준다():
    """재현되지 않는 유의성은 유의성이 아니다."""
    가, 나 = 표(300, 600), 표(330, 600)
    assert bs.잰다(가, 나, n=200, seed=3) == bs.잰다(가, 나, n=200, seed=3)


def test_짝지어_뽑는다():
    """★ **같은 줄 번호를 양쪽에 쓴다**(§180). 따로 뽑으면 줄 난이도가 잡음으로 들어와
    작은 차이가 묻힌다 — 짝지음이 없으면 이 도구는 쓸 데가 없다."""
    import inspect
    src = inspect.getsource(bs.잰다)
    assert "차례" in src and src.count("비율(가, 차례)") == 1 and src.count("비율(나, 차례)") == 1


def test_못_견주는_둘은_거절한다(tmp_path, capsys):
    """★ 부트스트랩은 차이를 재는 자이지 **견줄 자격**을 묻지 않는다(compare.AB)."""
    import json
    가 = tmp_path / "a.jsonl"
    나 = tmp_path / "b.jsonl"
    가.write_text(json.dumps({"meta": True, "set_sha256": "셋", "metrics": "2",
                              "onto_sha256": "사전"}) + "\n", encoding="utf-8")
    나.write_text(json.dumps({"meta": True, "set_sha256": "셋", "metrics": "3",
                              "onto_sha256": "사전"}) + "\n", encoding="utf-8")
    assert bs.main([str(가), str(나), "--set", "x"]) == 1
    말 = capsys.readouterr().err
    assert "자가 바뀌었다" in 말
    # ★ **막으면서 넘는 길을 준다**(DECISIONS §202) — 옛 판은 줄을 들고 있으니 다시 채점하면 된다
    assert "rescore.py" in 말, "막기만 하고 어떻게 견줄지를 안 말한다"


def test_낮을수록_좋은_지표의_부호를_안다():
    """★ **2026-09-28 이 도구가 `term_bad` 를 반대로 찍었다**(DECISIONS §182).
    오역 0.0061 대 0.0010 을 보고 **「A 가 낫다」** 고 했다 — 부호를 모르면 논문에 반대로 적힌다."""
    assert "term_bad" in bs.낮을수록_좋다
    assert not (bs.낮을수록_좋다 & {"term_off", "term", "lit", "ui", "keep", "style", "hangul"})


def test_기계가_지키는_지표를_못_견준다고_찍는다(tmp_path, capsys):
    """★ **자 · 셋 · 사전이 다 같아서 위의 검사는 전부 통과한다**(§156 · §182). 거기에 p 값까지
    붙으면 **가장 그럴듯한 거짓말**이 된다 — 한쪽은 기계가 지킨 수인데."""
    import json
    from seshat import backends
    우리 = "gemma3-4b+ph+marks2+gloss2+retry+endings+terms"
    저쪽 = "nova-lite (thoth 워커)"
    assert backends.지키는_지표(우리) >= {"keep", "lit", "ui"}
    assert backends.지키는_지표(저쪽) == frozenset()
    머리 = {"meta": True, "set_sha256": "셋", "metrics": "3", "onto_sha256": "사전"}
    가 = tmp_path / "a.jsonl"
    나 = tmp_path / "b.jsonl"
    가.write_text(json.dumps({**머리, "backend": 저쪽}) + "\n", encoding="utf-8")
    나.write_text(json.dumps({**머리, "backend": 우리}) + "\n", encoding="utf-8")
    with pytest.raises(SystemExit):        # 셋이 없어 멈추지만, 경고는 그 전에 나온다
        bs.main([str(가), str(나), "--set", str(tmp_path / "없는셋.jsonl")])
    말 = capsys.readouterr().err
    assert "못 견주는 지표" in 말 and "keep" in 말 and "lit" in 말


def test_보호_표가_MARK_ARMS_를_만든다():
    """★ **두 곳에 안 적는다**(§163). 표시를 빼는 팔 목록은 보호 표에서 나온다."""
    from seshat import backends
    assert backends.MARK_ARMS == set(backends.보호)
    assert backends.지키는_지표("gemma3-12b+ph+retry+endings+terms") == {"keep"}, "+ph 는 이름을 지킨다"
    assert backends.지키는_지표("aws-translate") == frozenset()
    # ★ **이름이 없으면 「모른다」 다** — 「안 지킨다」 가 아니다(DECISIONS §206)
    assert backends.지키는_지표(None) is None
    assert backends.지키는_지표("") is None
    from seshat import compare
    # 모르는 팔이 섞이면 **지킬 수 있는 것을 전부** 못 견주는 것으로 친다
    assert compare.가린_지표({"arm": None}, {"arm": "aws-translate"}) == set(backends.지킬수있는것)
    assert compare.가린_지표({"arm": "aws-translate"}, {"arm": "aws-translate"}) == set()
