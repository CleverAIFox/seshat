"""A/A — 같은 팔을 여러 판 돌린 흔들림을 잰다(DECISIONS §139).

★ 모델을 안 부른다. **결과 파일을 손으로 짓고** 세는 규칙만 본다.
"""
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("noise", ROOT / "tools/noise.py")
N = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(N)


def 판(tmp, 이름, 줄, **머리):
    """결과 파일 하나. 머리줄 + 줄들 — 진짜 `evaluate` 가 쓰는 꼴이다."""
    p = tmp / f"{이름}.jsonl"
    머 = {"meta": True, "backend": "가짜", "set_sha256": "셋", "onto_sha256": "사전",
          "term_off": 0.9, "lit": 0.8, "keep": 0.99, **머리}
    with p.open("w", encoding="utf-8") as f:
        f.write(json.dumps(머, ensure_ascii=False) + "\n")
        for i, o in 줄.items():
            f.write(json.dumps({"id": i, "src": "x", "out": o}, ensure_ascii=False) + "\n")
    return p


def test_머리줄_없는_파일은_안_받는다(tmp_path):
    """재현 조건이 없으면 견줄 수 없다 — 0 이 아니라 거절이다."""
    p = tmp_path / "민둥.jsonl"
    p.write_text(json.dumps({"id": "a", "out": "가"}) + "\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="머리줄이 없다"):
        N.read(p)


def test_셋이_다르면_거절한다(tmp_path):
    """섞어 재고 「잡음이 크다」 고 적는 것이 가장 나쁜 결과다(DECISIONS §45)."""
    a = 판(tmp_path, "a", {"1": "가"})
    b = 판(tmp_path, "b", {"1": "가"}, set_sha256="딴셋")
    with pytest.raises(SystemExit, match="set_sha256 가 판마다 다르다"):
        N.main([str(a), str(b)])


def test_팔이_다르면_거절한다(tmp_path):
    a = 판(tmp_path, "a", {"1": "가"})
    b = 판(tmp_path, "b", {"1": "가"}, backend="딴팔")
    with pytest.raises(SystemExit, match="backend 가 판마다 다르다"):
        N.main([str(a), str(b)])


def test_판이_하나면_못_잰다(tmp_path):
    a = 판(tmp_path, "a", {"1": "가"})
    with pytest.raises(SystemExit, match="판이 하나면"):
        N.main([str(a)])


def test_지표는_같은데_본문이_다른_판을_가른다(tmp_path, capsys):
    """2026-09-28 에 실제로 일어난 일이다 — 지표 아홉이 같고 본문이 600 중 7줄 달랐다."""
    a = 판(tmp_path, "a", {"1": "가", "2": "나", "3": "다"})
    b = 판(tmp_path, "b", {"1": "가", "2": "**딴 글자**", "3": "다"})
    N.main([str(a), str(b)])
    out = capsys.readouterr().out
    assert "쓸 만한 tol 0.0000" in out
    assert "1/3 줄이 판마다 다른 글자를 냈다" in out
    assert "지표가 이 변동을 못 본다" in out, "지표 0 과 결정적인 것을 같은 말로 내면 안 된다"


def test_판이_둘이면_표본_하나라고_적는다(tmp_path, capsys):
    """쌍 하나로 나온 0 은 「흔들리지 않는다」 가 아니라 「한 번 봤더니 같았다」 다."""
    a = 판(tmp_path, "a", {"1": "가"})
    b = 판(tmp_path, "b", {"1": "가"})
    N.main([str(a), str(b)])
    assert "판이 둘이다" in capsys.readouterr().out


def test_넷이면_그_말을_안_한다(tmp_path, capsys):
    이 = [판(tmp_path, n, {"1": "가"}) for n in "abcd"]
    N.main([str(p) for p in 이])
    out = capsys.readouterr().out
    assert "판이 둘이다" not in out and "쌍 6" in out


def test_퍼짐은_최대에서_최소를_뺀다(tmp_path):
    머리들 = [{"term_off": 0.90, "lit": 0.80}, {"term_off": 0.91, "lit": 0.80},
             {"term_off": 0.88, "lit": 0.80}]
    got = N.퍼짐(머리들)
    assert got["term_off"] == (0.88, 0.91, pytest.approx(0.03))
    assert got["lit"][2] == 0


def test_못_잰_지표는_0_이_아니다(tmp_path):
    """한 판에 없는 지표를 0 으로 채우면 퍼짐이 지표값만큼 나온다 — 그것은 거짓말이다."""
    assert "chrf" not in N.퍼짐([{"chrf": 0.5}, {"chrf": None}])
    assert "chrf" not in N.퍼짐([{"chrf": 0.5}, {}])


def test_판마다_없는_줄은_안_센다(tmp_path):
    """이어 돌린 판은 줄이 빠질 수 있다 — 빠진 것을 「달랐다」 로 세면 흔들림이 부풀려진다."""
    got = N.흔들린_줄([{"1": "가", "2": "나"}, {"1": "가"}])
    assert got == {"1": 1}


def test_흔들림을_판_수만큼_센다(tmp_path):
    """서로 다른 번역이 몇 개인가 — 셋 다 다르면 3 이다. H-058 이 이 수를 쓴다."""
    got = N.흔들린_줄([{"1": "가"}, {"1": "나"}, {"1": "다"}, {"1": "가"}])
    assert got == {"1": 3}


def test_셋이_어느_사전으로_만들어졌는지_판이_든다(tmp_path):
    """★ **셋의 `keep` · `lit` · `ui` 자리는 만들 때의 사전이 찍은 것이다**(DECISIONS §171 · §207).
    2026-09-28 사전에 `AWS` 를 넣었는데 `keep` 이 한 자리도 안 움직였다 — **분모가 옛 사전에
    묶여 있다**는 뜻인데 그 사실이 **아무 데도 안 적혀 있었다.**

    ★ **「모른다」 를 「낡지 않았다」 로 치지 않는다**(§110). 옛 셋은 None 이고, None 이 판에 실린다.
    """
    from seshat import evaluate
    옛셋 = tmp_path / "옛.jsonl"
    옛셋.write_text(json.dumps({"meta": True, "about": "칸이 없다"}, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    assert evaluate.셋의_사전(옛셋) is None
    assert evaluate.셋이_낡았나(옛셋) is None, "모르는 것은 낡지 않은 것이 아니다"

    낡은 = tmp_path / "낡은.jsonl"
    낡은.write_text(json.dumps({"meta": True, "onto_score": "옛지문"}, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    assert evaluate.셋이_낡았나(낡은) is True

    새것 = tmp_path / "새.jsonl"
    새것.write_text(json.dumps({"meta": True, "onto_score": evaluate.onto_score_sha256()},
                              ensure_ascii=False) + "\n", encoding="utf-8")
    assert evaluate.셋이_낡았나(새것) is False


def test_셋을_만드는_도구가_사전을_적는다():
    """적는 자리가 없으면 다음 셋도 똑같이 썩는다 — **고치는 것은 셋이 아니라 만드는 길이다.**"""
    t = (ROOT / "tools/fetch_awsdocs.py").read_text(encoding="utf-8")
    assert '"onto_score": evaluate.onto_score_sha256()' in t
