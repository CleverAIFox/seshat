"""회귀를 막는 문 — 떨어지면 막고, 못 재면 통과가 아니고, 사전이 바뀌면 막지 않는다(DECISIONS §131)."""
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("gate", ROOT / "tools/gate.py")
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)

REC = {"arm": "가짜", "set_sha256": "셋해시", "onto_sha256": "사전해시",
       "term_off": 0.90, "lit": 0.80, "guard": ["term_off", "lit"], "tol": 0.01}


def 머리(**kw):
    return {"meta": True, "backend": "가짜", "set_sha256": "셋해시", "onto_sha256": "사전해시", **kw}


def test_올랐으면_통과한다():
    assert G.check(REC, 머리(term_off=0.92, lit=0.85)) == ([], [])


def test_떨어지면_막는다():
    막, _ = G.check(REC, 머리(term_off=0.85, lit=0.80))
    assert len(막) == 1 and "term_off" in 막[0] and "떨어졌다" in 막[0]


def test_허용_안이면_말만_한다():
    """여섯을 다 꽉 막으면 잡음에 막히고 곧 아무도 안 본다."""
    막, 말 = G.check(REC, 머리(term_off=0.895, lit=0.80))
    assert 막 == [] and 말 and "허용" in 말[0]


def test_못_잰_것은_통과가_아니다():
    """결과에 지표가 없으면 0 이 아니라 빨간불이다(tools/doctor.py 와 같은 규율)."""
    막, _ = G.check(REC, 머리(term_off=0.95))
    assert any("이번 결과에 없다" in x for x in 막)


def test_셋이_다르면_비교하지_않는다():
    막, _ = G.check(REC, 머리(set_sha256="딴셋", term_off=0.99, lit=0.99))
    assert len(막) == 1 and "셋이 다르다" in 막[0]


def test_셋_해시가_없으면_박으라고_한다():
    막, _ = G.check({**REC, "set_sha256": ""}, 머리(term_off=0.99))
    assert 막 and "박는다" in 막[0]


def test_사전이_바뀌면_막지_않고_말한다():
    """사전을 고치면 같은 번역의 점수가 바뀐다 — 그것을 회귀로 읽으면 사전을 영영 못 고친다."""
    막, 말 = G.check(REC, 머리(onto_sha256="새사전", term_off=0.92, lit=0.85))
    assert 막 == [] and any("사전이 바뀌었다" in x for x in 말)


def test_기록판에_없는_팔은_안_막는다():
    """실험 팔은 판마다 새로 생긴다 — 그것까지 막으면 가설 세울 때마다 문이 빨개진다."""
    assert G.고른다({"record": [REC]}, 머리(backend="딴팔"), None) is None
    with pytest.raises(SystemExit, match="견줄 대상이 없으면"):
        G.고른다({"record": [REC]}, 머리(backend="딴팔"), None, 꼭=True)


def test_올라간_것만_기록한다():
    """기록판은 최고를 든다 — 떨어진 값을 쓰면 다음 문이 낮은 선에서 열린다."""
    오른 = G.올릴_것(REC, 머리(term_off=0.95, lit=0.70))
    assert 오른 == {"term_off": 0.95}


def test_기록판을_고쳐도_주석이_남는다(tmp_path, monkeypatch):
    """TOML 을 다시 찍으면 주석이 사라지는데 이 파일은 주석이 절반이다."""
    p = tmp_path / "sb.toml"
    p.write_text((ROOT / "data/scoreboard.toml").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(G.catalog, "gate", lambda *a, **k: None)
    rec = G.load(p)["record"][0]
    head = 머리(backend=rec["arm"], set_sha256="새해시", commit="abc123", term_off=0.95)
    G._쓴다("runs/새실행.jsonl", rec, head, {"term_off": 0.95}, p)
    새 = p.read_text(encoding="utf-8")
    assert "★ **이 파일은 값을 만들지 않는다.**" in 새          # 주석이 살아 있다
    다시 = G.load(p)["record"][0]
    assert 다시["term_off"] == 0.95 and 다시["set_sha256"] == "새해시"
    assert 다시["run"] == "새실행" and 다시["commit"] == "abc123"
    assert 다시["lit"] == rec["lit"]                          # 안 올라간 것은 그대로


def test_실제_기록판이_읽힌다():
    board = G.load()
    rec = board["record"][0]
    assert rec["arm"] and rec["guard"] and rec["set"].startswith("data/")
    assert board["target"], "넘어야 할 선이 없으면 기록판이 목표를 안 든다"


def test_기록판이_카탈로그에_있다():
    from seshat import catalog
    e = catalog.match(catalog.load(), "repo", "data/scoreboard.toml")
    assert e and e["id"] == "scoreboard" and "evidence" in e["uses"]


def test_머리줄_없는_파일은_안_받는다(tmp_path):
    p = tmp_path / "x.jsonl"
    p.write_text(json.dumps({"id": "a", "out": "x"}) + "\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="머리줄이 없다"):
        G.head_of(str(p))
