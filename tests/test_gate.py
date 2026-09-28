"""회귀를 막는 문 — 떨어지면 막고, 못 재면 통과가 아니고, 사전이 바뀌면 막지 않는다(DECISIONS §131)."""
import importlib.util
import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("gate", ROOT / "tools/gate.py")
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)

# `metrics` — 자 판. 없으면 문이 「재채점하고 박아라」 로 막는다(DECISIONS §145)
REC = {"arm": "가짜", "set_sha256": "셋해시", "onto_sha256": "사전해시", "metrics": "2",
       "term_off": 0.90, "lit": 0.80, "guard": ["term_off", "lit"], "tol": 0.01}


def 머리(**kw):
    return {"meta": True, "backend": "가짜", "set_sha256": "셋해시", "onto_sha256": "사전해시",
            "metrics": "2", **kw}


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


def test_처음_박는_판은_막지_않는다():
    """`--update` 가 해시를 박으러 왔는데 해시가 없다고 막으면 박을 길이 없다(DECISIONS §132)."""
    빈 = {**REC, "set_sha256": ""}
    막, 말 = G.check(빈, 머리(term_off=0.8), pin=True)
    assert 막 == [] and 말 and "박는다" in 말[0]
    막2, _ = G.check(빈, 머리(term_off=0.8), pin=False)
    assert 막2                                   # 그냥 보기만 할 때는 여전히 막는다


def test_처음_박을_때는_있는_값을_그대로_쓴다():
    """어느 셋의 값인지 몰랐으므로 「올랐다 · 내렸다」 를 말할 수 없다. 견주기는 다음 판부터다."""
    빈 = {**REC, "set_sha256": ""}
    assert G.올릴_것(빈, 머리(term_off=0.10, lit=0.10), pin=True) == {"term_off": 0.1, "lit": 0.1}
    assert G.올릴_것(REC, 머리(term_off=0.10, lit=0.10), pin=True) == {}   # 이미 박혔으면 최고만


def test_사전_해시도_같이_박는다(tmp_path, monkeypatch):
    """안 박으면 §96 경고(사전이 바뀌었다)가 영영 안 켜진다."""
    p = tmp_path / "sb.toml"
    p.write_text((ROOT / "data/scoreboard.toml").read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(G.catalog, "gate", lambda *a, **k: None)
    rec = G.load(p)["record"][0]
    head = 머리(backend=rec["arm"], set_sha256="새셋", onto_sha256="새사전", term_off=0.9)
    G._쓴다("runs/x.jsonl", rec, head, {"term_off": 0.9}, p)
    assert G.load(p)["record"][0]["onto_sha256"] == "새사전"


def test_처음부터_끝까지_한_번_돈다(tmp_path, monkeypatch, capsys):
    """**도구가 실제로 도는 길을 밟는다**(DECISIONS §128). 조각 시험만으로는 §132 를 못 잡았다."""
    # ★ **살아 있는 기록판의 상태에 기대지 않는다**(DECISIONS §132 와 같은 병). 해시가 박히기 전에는
    #   통과하고 박힌 뒤에는 깨지는 시험은, 저장소가 정상으로 갈수록 빨개진다. 여기서 비우고 시작한다
    sb = tmp_path / "sb.toml"
    sb.write_text(re.sub(r'^(set_sha256|onto_sha256) = "[^"]*"', r'\1 = ""',
                         (ROOT / "data/scoreboard.toml").read_text(encoding="utf-8"), flags=re.M),
                  encoding="utf-8")
    monkeypatch.setattr(G, "PATH", sb)
    monkeypatch.setattr(G.catalog, "gate", lambda *a, **k: None)
    arm = G.load(sb)["record"][0]["arm"]
    run = tmp_path / "H-999-x.jsonl"
    run.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in (
        {"meta": True, "backend": arm, "set_sha256": "셋1", "onto_sha256": "사전1",
         "metrics": "2", "term_off": 0.8858, "lit": 0.803, "keep": 0.9853, "josa": 0.99},
        {"id": "a", "src": "x", "out": "y"})) + "\n", encoding="utf-8")

    assert G.main([str(run), "--update"]) == 0           # ① 처음 박는다
    rec = G.load(sb)["record"][0]
    assert rec["set_sha256"] == "셋1" and rec["run"] == "H-999-x"

    assert G.main([str(run)]) == 0                       # ② 같은 값이면 통과
    좋 = tmp_path / "H-999-y.jsonl"
    좋.write_text(json.dumps({"meta": True, "backend": arm, "set_sha256": "셋1", "onto_sha256": "사전1",
                              "metrics": "2", "term_off": 0.95, "lit": 0.90, "keep": 0.99, "josa": 1.0}, ensure_ascii=False) + "\n",
                  encoding="utf-8")
    assert G.main([str(좋), "--update"]) == 0            # ③ 오르면 기록이 바뀐다
    assert G.load(sb)["record"][0]["term_off"] == 0.95

    나 = tmp_path / "H-999-z.jsonl"
    나.write_text(json.dumps({"meta": True, "backend": arm, "set_sha256": "셋1", "onto_sha256": "사전1",
                              "metrics": "2", "term_off": 0.80, "lit": 0.90, "keep": 0.99, "josa": 1.0}, ensure_ascii=False) + "\n",
                  encoding="utf-8")
    assert G.main([str(나)]) == 1                        # ④ 떨어지면 막는다
    assert G.load(sb)["record"][0]["term_off"] == 0.95   # 막힌 값은 기록에 안 남는다


def test_허용치는_잰_값이다():
    """짐작한 허용치는 **관대한 쪽으로** 틀린다 — 빡빡하면 내 실험이 막히기 때문이다(DECISIONS §139).

    2026-09-28 같은 팔(`+ph+endings+terms`)을 두 판 돌려 지표가 **소수점 끝자리까지 같았다.**
    잰 잡음이 0 인데 0.01 을 허용하면 그것은 잡음 여유가 아니라 **회귀 통행증**이다 —
    H-055 의 `term_off` −0.0076 이 그것으로 통과했다.
    """
    for r in G.load().get("record", []):
        assert r.get("tol", 0.0) <= 0.002, \
            f"{r['arm']} 의 tol {r['tol']} 이 잰 잡음(0)보다 훨씬 크다 — 재고 나서 올린다"
        assert len(r.get("tol_run", [])) >= 2, \
            f"{r['arm']} 의 tol 에 **그것을 잰 두 판**이 안 적혀 있다 — 짐작한 허용치는 문이 아니다"


def test_MBR_만큼_떨어지면_막는다():
    """옛 `tol` 0.01 이 통과시킨 그 크기를 지금은 막는가(DECISIONS §139 · H-055)."""
    실제 = G.load()["record"][0]["tol"]
    막, _ = G.check({**REC, "tol": 실제}, 머리(term_off=0.90 - 0.0076, lit=0.80))
    assert 막 and "term_off" in 막[0] and "떨어졌다" in 막[0]


def test_승격하면_이름과_날짜도_바뀐다(tmp_path, monkeypatch):
    """숫자만 고치면 기록판이 **자기가 안 든 팔의 숫자**를 든다(DECISIONS §143).

    그러면 다음 판에서 `--arm` 없이 부를 때 「기록판에 없는 팔」 로 통과한다 —
    **승격하는 순간 문이 서빙 후보를 안 지킨다.**
    """
    board = tmp_path / "board.toml"
    board.write_text(
        '[[record]]\nset = "s.jsonl"\nset_sha256 = "셋"\narm = "옛팔"\nrun = "옛실행"\n'
        'commit = "0000000"\ndate = "2020-01-01"\nonto_sha256 = "사전"\nmetrics = "2"\n'
        'term_off = 0.80\nlit = 0.70\nkeep = 0.90\nstyle = 0.90\n'
        'guard = ["term_off", "lit", "keep"]\ntol = 0.0\n', encoding="utf-8")
    run = tmp_path / "새실행-20260928-120000.jsonl"
    run.write_text(json.dumps(머리(backend="새팔", term_off=0.9, lit=0.8, keep=0.95, style=0.91,
                                   set_sha256="셋", onto_sha256="사전"), ensure_ascii=False) + "\n",
                   encoding="utf-8")
    monkeypatch.setattr(G.catalog, "gate", lambda p: None)
    rec = G.load(board)["record"][0]
    head = G.head_of(str(run))
    G._쓴다(str(run), rec, head, G.올릴_것(rec, head), path=board)
    새 = G.load(board)["record"][0]
    assert 새["arm"] == "새팔", "기록의 팔이 안 바뀌면 문이 다음 판부터 아무것도 안 지킨다"
    assert 새["run"] == "새실행-20260928-120000" and 새["date"] != "2020-01-01"
    assert 새["term_off"] == 0.9 and 새["keep"] == 0.95


def test_고친_기록으로_다시_부르면_문이_지킨다(tmp_path, monkeypatch):
    """승격 뒤 `--arm` 없이 불러도 그 팔을 찾아야 한다 — 그게 이 고침의 목적이다."""
    board = tmp_path / "board.toml"
    board.write_text(
        '[[record]]\nset = "s.jsonl"\nset_sha256 = "셋"\narm = "옛팔"\nrun = "r"\n'
        'commit = "0"\ndate = "2020-01-01"\nonto_sha256 = "사전"\nmetrics = "2"\n'
        'term_off = 0.80\nlit = 0.70\nkeep = 0.90\nstyle = 0.90\n'
        'guard = ["term_off", "lit", "keep"]\ntol = 0.0\n', encoding="utf-8")
    run = tmp_path / "새실행-20260928-120000.jsonl"
    run.write_text(json.dumps(머리(backend="새팔", term_off=0.9, lit=0.8, keep=0.95, style=0.91,
                                   set_sha256="셋", onto_sha256="사전"), ensure_ascii=False) + "\n",
                   encoding="utf-8")
    monkeypatch.setattr(G.catalog, "gate", lambda p: None)
    rec, head = G.load(board)["record"][0], G.head_of(str(run))
    G._쓴다(str(run), rec, head, G.올릴_것(rec, head), path=board)
    # 이제 팔 이름을 안 주고 골라도 찾아야 하고, 떨어진 실행을 막아야 한다
    새rec = G.고른다(G.load(board), 머리(backend="새팔"), None, 꼭=True)
    막, _ = G.check(새rec, 머리(backend="새팔", set_sha256="셋", onto_sha256="사전",
                                term_off=0.85, lit=0.8, keep=0.95))
    assert 막 and "term_off" in 막[0]


def test_자기가_세운_기록에_안_막힌다():
    """기록판은 4자리로 반올림해 든다 — **견줄 때도 같은 자리여야 한다**(DECISIONS §144).

    2026-09-28 승격 직후 같은 파일을 다시 넣었더니 `0.9771689497716894 < 0.9772` 로 막혔다.
    반올림이 올라가는 값은 **자기가 세운 기록에 영영 막힌다.**
    """
    rec = {**REC, "term_off": 0.9772, "lit": 0.8099, "guard": ["term_off", "lit"], "tol": 0.0}
    막, 말 = G.check(rec, 머리(term_off=0.9771689497716894, lit=0.8098591549295775))
    assert 막 == [], f"자기 기록에 막혔다 — {막}"


def test_반올림_아래로_떨어지면_그래도_막는다():
    """같은 자리에서 견주는 것이지 봐주는 것이 아니다."""
    rec = {**REC, "term_off": 0.9772, "guard": ["term_off"], "tol": 0.0}
    막, _ = G.check(rec, 머리(term_off=0.97714))          # 0.9771 로 내려앉는다
    assert 막 and "term_off" in 막[0]


def test_반올림_안쪽_상승은_기록하지_않는다():
    """0.00001 짜리 상승을 적으면 다음 판이 그 자릿수에 막힌다 — 같은 사고의 다른 얼굴이다."""
    rec = {**REC, "term_off": 0.9772, "guard": ["term_off"], "tol": 0.0}
    assert "term_off" not in G.올릴_것(rec, 머리(term_off=0.97721))
    assert G.올릴_것(rec, 머리(term_off=0.97731))["term_off"] == 0.9773


def test_자가_바뀌면_막는다():
    """채점 코드가 바뀌면 옛 수와 못 견준다 — 사전이 바뀌는 것과 다르다(DECISIONS §145)."""
    rec = {**REC, "metrics": "1"}  # 기록은 옛 자
    막, _ = G.check(rec, 머리(metrics="2", term_off=0.99, lit=0.99))
    assert len(막) == 1 and "자가 바뀌었다" in 막[0]


def test_기록에_자_판이_없으면_박으라고_한다():
    옛 = {k: v for k, v in REC.items() if k != "metrics"}
    막, _ = G.check(옛, 머리(term_off=0.99, lit=0.99))
    assert 막 and "자 판" in 막[0] and "rescore" in 막[0]
    말2, = G.check(옛, 머리(term_off=0.99), pin=True)[1]
    assert "이번 실행으로 박는다" in 말2


def test_같은_자면_통과한다():
    rec = {**REC, "metrics": "2"}
    assert G.check(rec, 머리(metrics="2", term_off=0.92, lit=0.85)) == ([], [])


def test_없는_키는_만든다(tmp_path, monkeypatch):
    """있는 줄만 고쳐 쓰면 새로 생긴 칸(`metrics`)이 영영 안 박힌다(DECISIONS §145)."""
    board = tmp_path / "b.toml"
    board.write_text('[[record]]\narm = "팔"\nset_sha256 = "셋"\nterm_off = 0.5\n'
                     'guard = ["term_off"]\ntol = 0.0\n\n[[target]]\narm = "선"\n', encoding="utf-8")
    monkeypatch.setattr(G.catalog, "gate", lambda p: None)
    rec = G.load(board)["record"][0]
    head = 머리(backend="팔", set_sha256="셋", metrics="7", term_off=0.6)
    G._쓴다("새-20260928-1.jsonl", rec, head, G.올릴_것(rec, head), path=board)
    새 = G.load(board)
    assert 새["record"][0]["metrics"] == "7" and 새["record"][0]["run"] == "새-20260928-1"
    assert 새["target"][0]["arm"] == "선", "뒤 블록을 안 건드려야 한다"
