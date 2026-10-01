"""회귀를 막는 문 — 떨어지면 막고, 못 재면 통과가 아니고, 사전이 바뀌면 막지 않는다(DECISIONS §131)."""
import importlib.util
import json
import pathlib
import re

import pytest

from seshat import evaluate as _E

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("gate", ROOT / "tools/gate.py")
G = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(G)

# ★ **자 판을 손으로 박지 않는다**(DECISIONS §162). 코드의 자가 올라가면 픽스처도 같이 올라야
#   한다 — 박으면 자를 올리는 날 시험이 빨개지고, 그러면 시험을 고치느라 고침이 늦어진다
자 = _E.METRICS_VER

# `metrics` — 자 판. 없으면 문이 「재채점하고 박아라」 로 막는다(DECISIONS §145)
REC = {"arm": "가짜", "set_sha256": "셋해시", "onto_sha256": "사전해시", "metrics": 자,
       "term_off": 0.90, "lit": 0.80, "guard": ["term_off", "lit"], "tol": 0.01}


def 머리(**kw):
    return {"meta": True, "backend": "가짜", "set_sha256": "셋해시", "onto_sha256": "사전해시",
            "metrics": 자, **kw}


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
         "metrics": 자, "term_off": 0.8858, "lit": 0.803, "keep": 0.9853, "josa": 0.99},
        {"id": "a", "src": "x", "out": "y"})) + "\n", encoding="utf-8")

    assert G.main([str(run), "--update"]) == 0           # ① 처음 박는다
    rec = G.load(sb)["record"][0]
    assert rec["set_sha256"] == "셋1" and rec["run"] == "H-999-x"

    assert G.main([str(run)]) == 0                       # ② 같은 값이면 통과
    좋 = tmp_path / "H-999-y.jsonl"
    좋.write_text(json.dumps({"meta": True, "backend": arm, "set_sha256": "셋1", "onto_sha256": "사전1",
                              "metrics": 자, "term_off": 0.95, "lit": 0.90, "keep": 0.99, "josa": 1.0}, ensure_ascii=False) + "\n",
                  encoding="utf-8")
    assert G.main([str(좋), "--update"]) == 0            # ③ 오르면 기록이 바뀐다
    assert G.load(sb)["record"][0]["term_off"] == 0.95

    나 = tmp_path / "H-999-z.jsonl"
    나.write_text(json.dumps({"meta": True, "backend": arm, "set_sha256": "셋1", "onto_sha256": "사전1",
                              "metrics": 자, "term_off": 0.80, "lit": 0.90, "keep": 0.99, "josa": 1.0}, ensure_ascii=False) + "\n",
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
        'commit = "0000000"\ndate = "2020-01-01"\nonto_sha256 = "사전"\nmetrics = "' + 자 + '"\n'
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
        'commit = "0"\ndate = "2020-01-01"\nonto_sha256 = "사전"\nmetrics = "' + 자 + '"\n'
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
    # `지금` 을 기록과 같게 준다 — 그래야 **기록 대 실행** 축만 남는다.
    # 안 주면 「기록판이 낡았다」(DECISIONS §162)가 먼저 걸리고 둘 다 참이라 무엇을 보는지 흐려진다
    rec = {**REC, "metrics": "1"}
    막, _ = G.check(rec, 머리(metrics=자, term_off=0.99, lit=0.99), 지금="1")
    assert len(막) == 1 and "자가 바뀌었다" in 막[0]


def test_기록에_자_판이_없으면_박으라고_한다():
    옛 = {k: v for k, v in REC.items() if k != "metrics"}
    막, _ = G.check(옛, 머리(term_off=0.99, lit=0.99))
    assert 막 and "자 판" in 막[0] and "rescore" in 막[0]
    말2, = G.check(옛, 머리(term_off=0.99), pin=True)[1]
    assert "이번 실행으로 박는다" in 말2


def test_같은_자면_통과한다():
    rec = {**REC, "metrics": 자}
    assert G.check(rec, 머리(metrics=자, term_off=0.92, lit=0.85)) == ([], [])


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


def test_자가_바뀌면_내려가도_그대로_박는다():
    """재채점은 값을 **내리는** 일이 잦다 — 오른 것만 쓰면 「새 자」 라고 적힌 채 옛 수가 남는다.

    2026-09-28 `term` 을 출현 횟수로 바꾸자 기준이 0.9772 → 0.9619 로 내려갔다(DECISIONS §146).
    """
    rec = {**REC, "metrics": "1", "term_off": 0.9772, "lit": 0.8099, "keep": 0.9979,
           "guard": ["term_off", "lit", "keep"]}
    got = G.올릴_것(rec, 머리(metrics=자, term_off=0.9619, lit=0.8099, keep=0.9979), pin=True)
    assert got["term_off"] == 0.9619, "내려간 값이 안 박히면 기록판이 거짓말한다"


def test_자가_같으면_내려간_값은_안_박는다():
    """봐주는 것이 아니다 — 같은 자에서 내려간 것은 회귀다."""
    rec = {**REC, "metrics": 자, "term_off": 0.9772, "guard": ["term_off"]}
    assert "term_off" not in G.올릴_것(rec, 머리(metrics=자, term_off=0.9619), pin=True)


def test_다른_자로_잰_선은_차를_안_찍는다(tmp_path, monkeypatch, capsys):
    """비교를 거절하는 도구가 스스로 섞어 재고 있었다(DECISIONS §147)."""
    board = tmp_path / "b.toml"
    board.write_text(
        '[[record]]\nset = "s"\nset_sha256 = "셋"\nonto_sha256 = "사전"\nmetrics = "' + 자 + '"\narm = "팔"\n'
        'term_off = 0.96\nlit = 0.81\nguard = ["term_off"]\ntol = 0.0\n\n'
        '[[target]]\nset = "s"\narm = "옛선"\nonto_sha256 = "사전"\nterm_off = 0.9163\nlit = 0.923\n\n'
        '[[target]]\nset = "s"\narm = "새선"\nonto_sha256 = "사전"\nmetrics = "' + 자 + '"\n'
        'term_off = 0.90\nlit = 0.93\n',
        encoding="utf-8")
    run = tmp_path / "r-20260928-1.jsonl"
    run.write_text(json.dumps(머리(backend="팔", set_sha256="셋", onto_sha256="사전",
                                   metrics=자, term_off=0.97, lit=0.82), ensure_ascii=False) + "\n",
                   encoding="utf-8")
    monkeypatch.setattr(G, "PATH", board)
    assert G.main([str(run)]) == 0
    out = capsys.readouterr().out
    assert "옛선" in out and "분모가 다른 선이다" in out
    assert "선까지 새선" in out, "같은 자로 잰 선은 그대로 찍어야 한다"


def test_주석의_자리를_지킨다(tmp_path, monkeypatch):
    """기록판은 주석이 절반이고 세로로 맞춰 읽는다 — 고쳐 쓰는 도구가 모양을 망가뜨리면 안 된다."""
    board = tmp_path / "b.toml"
    board.write_text('[[record]]\narm = "팔"\nset_sha256 = "셋"\n'
                     'term_off = 0.5                       # 앞 칸\n'
                     '                                     # 이어지는 줄\n'
                     'guard = ["term_off"]\ntol = 0.0\n', encoding="utf-8")
    monkeypatch.setattr(G.catalog, "gate", lambda p: None)
    rec = G.load(board)["record"][0]
    head = 머리(backend="팔", set_sha256="셋", term_off=0.6)
    G._쓴다("r-20260928-1.jsonl", rec, head, G.올릴_것(rec, head), path=board)
    줄 = [x for x in board.read_text(encoding="utf-8").splitlines() if "앞 칸" in x][0]
    이어 = [x for x in board.read_text(encoding="utf-8").splitlines() if "이어지는" in x][0]
    assert 줄.index("#") == 이어.index("#"), f"주석 자리가 어긋났다\n{줄}\n{이어}"


def test_맞바꿈은_사람이_받는다(tmp_path, monkeypatch, capsys):
    """문은 맞바꿈을 못 정한다 — 한쪽이 크게 오르고 한쪽이 조금 떨어지는 판(DECISIONS §155)."""
    board = tmp_path / "b.toml"
    board.write_text('[[record]]\nset = "s"\nset_sha256 = "셋"\nonto_sha256 = "사전"\nmetrics = "' + 자 + '"\n'
                     'arm = "옛팔"\nrun = "r"\ncommit = "0"\ndate = "2020-01-01"\n'
                     'term_off = 0.9619\nlit = 0.8099\nguard = ["term_off", "lit"]\ntol = 0.0\n',
                     encoding="utf-8")
    run = tmp_path / "새-20260928-1.jsonl"
    run.write_text(json.dumps(머리(backend="새팔", set_sha256="셋", onto_sha256="사전", metrics=자,
                                   term_off=0.9559, lit=0.9930), ensure_ascii=False) + "\n",
                   encoding="utf-8")
    monkeypatch.setattr(G, "PATH", board)
    monkeypatch.setattr(G.catalog, "gate", lambda p: None)
    assert G.main([str(run), "--arm", "옛팔"]) == 1                    # ① 그냥은 막는다
    assert G.main([str(run), "--arm", "옛팔",
                   "--accept", "식별자 26 · 라벨 67 을 개념 4 와 바꾼다"]) == 0
    새 = G.load(board)["record"][0]
    assert 새["term_off"] == 0.9559, "받은 판은 **떨어진 값도** 박아야 다음 판이 안 막힌다"
    assert 새["lit"] == 0.993 and 새["arm"] == "새팔"
    assert "식별자 26" in 새["accepted"]
    assert "사람이 받아들였다" in capsys.readouterr().err


def test_까닭_없는_받아들임은_문을_끈_것이다(tmp_path, monkeypatch):
    board = tmp_path / "b.toml"
    board.write_text('[[record]]\nset = "s"\nset_sha256 = "셋"\nonto_sha256 = "사전"\nmetrics = "' + 자 + '"\n'
                     'arm = "팔"\nterm_off = 0.9\nguard = ["term_off"]\ntol = 0.0\n', encoding="utf-8")
    run = tmp_path / "새-20260928-1.jsonl"
    run.write_text(json.dumps(머리(backend="팔", set_sha256="셋", onto_sha256="사전", metrics=자,
                                   term_off=0.8), ensure_ascii=False) + "\n", encoding="utf-8")
    monkeypatch.setattr(G, "PATH", board)
    monkeypatch.setattr(G.catalog, "gate", lambda p: None)
    with pytest.raises(SystemExit, match="까닭이 비었다"):
        G.main([str(run), "--accept", "   "])


def test_다른_자는_못_받는다(tmp_path, monkeypatch, capsys):
    """맞바꿈이 아니라 **다른 것을 잰 것**이다(§145 · §147) — 까닭을 적어도 안 받는다."""
    rec = {**REC, "metrics": "1"}
    막, _ = G.check(rec, 머리(metrics=자, term_off=0.99, lit=0.99))
    assert 막 and "떨어졌다" not in 막[0]


def test_기계가_지킨_수와_모델이_지킨_수를_안_견준다(tmp_path, monkeypatch, capsys):
    """자도 셋도 같아서 다른 검사가 다 통과한다 — `protects` 만이 이것을 본다(DECISIONS §156)."""
    board = tmp_path / "b.toml"
    board.write_text('[[record]]\nset = "s"\nset_sha256 = "셋"\nonto_sha256 = "사전"\nmetrics = "' + 자 + '"\n'
                     'arm = "gemma3-4b+ph+marks2+gloss2+retry+endings+terms"\nterm_off = 0.95\nlit = 0.99\n'
                     'guard = ["term_off"]\ntol = 0.0\n\n'
                     '[[target]]\nset = "s"\narm = "nova-lite (thoth 워커)"\nonto_sha256 = "사전"\nmetrics = "' + 자 + '"\nterm_off = 0.90\nlit = 0.92\n',
                     encoding="utf-8")
    run = tmp_path / "새-20260928-1.jsonl"
    run.write_text(json.dumps(머리(backend="gemma3-4b+ph+marks2+gloss2+retry+endings+terms",
                                   set_sha256="셋", onto_sha256="사전", metrics=자,
                                   term_off=0.96, lit=0.99), ensure_ascii=False) + "\n", encoding="utf-8")
    monkeypatch.setattr(G, "PATH", board)
    assert G.main([str(run)]) == 0
    out = capsys.readouterr().out
    assert "term_off" in out.split("선까지")[1]
    assert "lit 는 안 찍는다" in out, "보호가 다른 lit 을 견주면 「넘었다」 가 거짓이 된다"


def test_보호가_같으면_그대로_견준다(tmp_path, monkeypatch, capsys):
    board = tmp_path / "b.toml"
    board.write_text('[[record]]\nset = "s"\nset_sha256 = "셋"\nonto_sha256 = "사전"\nmetrics = "' + 자 + '"\n'
                     'arm = "우리"\nprotects = ["lit"]\nterm_off = 0.95\nlit = 0.99\n'
                     'guard = ["term_off"]\ntol = 0.0\n\n'
                     '[[target]]\nset = "s"\narm = "같은보호"\nonto_sha256 = "사전"\nmetrics = "' + 자 + '"\nprotects = ["lit"]\n'
                     'term_off = 0.90\nlit = 0.92\n', encoding="utf-8")
    run = tmp_path / "새-20260928-1.jsonl"
    run.write_text(json.dumps(머리(backend="우리", set_sha256="셋", onto_sha256="사전", metrics=자,
                                   term_off=0.96, lit=0.99), ensure_ascii=False) + "\n", encoding="utf-8")
    monkeypatch.setattr(G, "PATH", board)
    assert G.main([str(run)]) == 0
    out = capsys.readouterr().out
    assert "안 찍는다" not in out and "lit" in out.split("선까지")[1]


def test_기록판이_낡은_것을_문이_스스로_안다():
    """2026-09-28 자를 3 으로 올렸는데 기록판도 그 실행도 2 라 **둘이 같아서 통과했다**.

    문은 두 산출물끼리만 견주고 **지금 코드의 자**는 안 봤다(DECISIONS §162).
    """
    rec = {**REC, "metrics": "1"}
    막, _ = G.check(rec, 머리(metrics="1", term_off=0.99, lit=0.99), 지금="9")
    assert 막 and "기록판이 낡았다" in 막[0] and "rescore" in 막[0]


def test_박는_판에서는_낡음을_안_막는다():
    """`--update` 는 **박으러 온 것**이다 — 막으면 박을 길이 없다(§144 의 닭과 달걀)."""
    rec = {**REC, "metrics": "1"}
    막, _ = G.check(rec, 머리(metrics="9", term_off=0.99, lit=0.99), pin=True, 지금="9")
    assert not [x for x in 막 if "낡았다" in x]


def test_박는_판에서_자_바뀜은_안_막는다():
    """「재채점하고 `--update` 로 박아라」 고 이르면서 박을 길을 막으면 안 된다(DECISIONS §165).

    2026-09-28 §144 의 닭과 달걀이 자에서 그대로 되풀이됐다 — 열 번째 구멍이다.
    """
    rec = {**REC, "metrics": "2"}
    막, 말 = G.check(rec, 머리(metrics="3", term_off=0.99, lit=0.99), pin=True, 지금="3")
    assert 막 == [] and any("다시 박는다" in x for x in 말)


def test_박는_판에서도_셋이_다르면_막는다():
    """다른 글로 잰 수를 기록으로 삼으면 그 기록이 거짓말한다."""
    rec = {**REC, "metrics": "3"}
    막, _ = G.check(rec, 머리(metrics="3", set_sha256="딴셋", term_off=0.99), pin=True, 지금="3")
    assert 막 and "셋이 다르다" in 막[0]


def _판(tmp_path, 기록자, 기록사전, 판자, 판사전, **값):
    """기록판 한 줄 · 실행 한 판. **분모 축만 바꿔 가며 본다**(DECISIONS §169)."""
    board = tmp_path / "b.toml"
    board.write_text(f'[[record]]\nset = "s"\nset_sha256 = "셋"\nonto_sha256 = "{기록사전}"\n'
                     f'metrics = "{기록자}"\narm = "팔"\nrun = "옛판"\ndate = "2026-09-01"\n'
                     'term_off = 0.9559\nkeep = 1.0\nguard = ["term_off", "keep"]\ntol = 0.0\n',
                     encoding="utf-8")
    run = tmp_path / "새-20260928-1.jsonl"
    run.write_text(json.dumps(머리(backend="팔", set_sha256="셋", onto_sha256=판사전,
                                   metrics=판자, **값), ensure_ascii=False) + "\n", encoding="utf-8")
    return board, run


@pytest.mark.parametrize("기록자, 기록사전, 판자, 판사전, 이름", [
    ("2", "옛사전", "3", "새사전", "둘 다"),
    ("3", "옛사전", "3", "새사전", "사전만"),
    ("2", "새사전", "3", "새사전", "자만"),
])
def test_분모가_갈리면_박으러_온_판을_지킴으로_막지_않는다(
        tmp_path, monkeypatch, capsys, 기록자, 기록사전, 판자, 판사전, 이름):
    """★ **2026-09-28 문이 스스로 「자가 바뀌었다 · 사전이 바뀌었다」 를 찍고 바로 다음 줄에서
    그 수로 막았다**(DECISIONS §169). 0.9532(982자리)와 0.9559(674자리)는 높낮이가 없다.

    ★ **떨어진 값도 그대로 박힌다.** 「오른 것만」 쓰면 기록판이 새 사전이라 적힌 채 옛 분모의
      수를 들게 되고, 그것이 §166 의 순환을 다시 만든다.
    """
    board, run = _판(tmp_path, 기록자, 기록사전, 판자, 판사전, term_off=0.9532, keep=0.9979)
    monkeypatch.setattr(G, "PATH", board)
    assert G.main([str(run), "--update"]) == 0, 이름
    out = capsys.readouterr().out
    assert "분모가 갈렸다" in out
    쓴 = board.read_text(encoding="utf-8")
    assert "0.9532" in 쓴 and "0.9979" in 쓴, "떨어진 값도 다시 박는다"


def test_분모가_같으면_박으러_와도_떨어진_것을_막는다(tmp_path, monkeypatch, capsys):
    """★ **문을 끄는 길을 만든 것이 아니다.** 같은 자 · 같은 사전이면 `--update` 여도 막는다 —
    안 그러면 자를 한 번 올릴 때마다 아무 팔이나 기록이 된다."""
    board, run = _판(tmp_path, "3", "새사전", "3", "새사전", term_off=0.9532, keep=0.9979)
    monkeypatch.setattr(G, "PATH", board)
    assert G.main([str(run), "--update"]) == 1
    assert "떨어졌다" in capsys.readouterr().err


def test_check_와_올릴것이_같은_물음을_쓴다():
    """★ **같은 판단이 두 곳에 있으면 한 곳만 고쳐진다**(DECISIONS §163 · §169). `올릴_것` 은
    자 바뀜을 알았고 `check` 는 몰랐다 — 둘 다 `compare.분모` 를 본다."""
    import inspect
    from seshat import compare
    for fn in (G.check, G.올릴_것):
        assert "compare.분모" in inspect.getsource(fn), f"{fn.__name__} 이 제 손으로 축을 적는다"
    assert "set_sha256" not in compare.분모, "다른 시험지는 GATE_막 이 막는다 — 선 줄이 침묵한다"


def test_선을_판으로_박는다(tmp_path, monkeypatch, capsys):
    """★ **선 줄만 손으로 고치고 있었다**(DECISIONS §171). 기록판 첫 줄이 「짐작으로 채우지
    않는다」 인데 선은 짐작으로 채우고 있었고, 그래서 자 2 · 옛 사전인 채로 남아 §166 을 만들었다.

    ★ **선은 올랐는지를 안 묻는다.** 기록은 내 최고이고 선은 남의 값이다 — 내려가도 박는다.
    """
    board = tmp_path / "b.toml"
    board.write_text('[[record]]\nset = "s"\nset_sha256 = "셋"\nonto_sha256 = "사전"\nmetrics = "' + 자 + '"\n'
                     'arm = "우리"\nterm_off = 0.95\nguard = ["term_off"]\ntol = 0.0\n\n'
                     '[[target]]\nnote = "배포본"\nset = "s"\narm = "배포본"\nmetrics = "2"\n'
                     'term_off = 0.9026\nlit = 0.9225\n', encoding="utf-8")
    run = tmp_path / "재-20260928-1.jsonl"
    run.write_text(json.dumps(머리(backend="배포본", set="s", set_sha256="셋", onto_sha256="새사전",
                                   onto_score="새지문", metrics=자, term_off=0.8859, lit=0.9225),
                              ensure_ascii=False) + "\n", encoding="utf-8")
    monkeypatch.setattr(G, "PATH", board)
    assert G.main([str(run), "--pin-target", "배포본"]) == 0
    쓴 = board.read_text(encoding="utf-8")
    assert "0.8859" in 쓴, "선이 내려가도 박는다 — 남을 다시 잰 것이다"
    assert f'metrics = "{자}"' in 쓴 and '"새지문"' in 쓴
    assert 'note = "배포본"' in 쓴, "주석과 note 는 그대로 둔다"
    assert "term_off = 0.95" in 쓴, "기록 줄은 안 건드린다"


def test_선을_딴_셋의_판으로는_못_박는다(tmp_path, monkeypatch, capsys):
    board = tmp_path / "b.toml"
    board.write_text('[[record]]\nset = "s"\nset_sha256 = "셋"\nmetrics = "' + 자 + '"\narm = "우리"\n'
                     'term_off = 0.95\nguard = ["term_off"]\ntol = 0.0\n\n'
                     '[[target]]\nset = "s"\narm = "배포본"\nterm_off = 0.9\n', encoding="utf-8")
    run = tmp_path / "재-20260928-1.jsonl"
    run.write_text(json.dumps(머리(backend="배포본", set="딴셋", metrics=자, term_off=0.99),
                              ensure_ascii=False) + "\n", encoding="utf-8")
    monkeypatch.setattr(G, "PATH", board)
    assert G.main([str(run), "--pin-target", "배포본"]) == 1
    assert "셋이 다르다" in capsys.readouterr().err
    assert "0.99" not in board.read_text(encoding="utf-8")


def test_선과_판이_견줄_이름이_없으면_안_박는다(tmp_path, monkeypatch, capsys):
    """★ **모르는 것은 같은 것이 아니다**(DECISIONS §173 · §110). 재채점 판은 `set_sha256` 만 들고
    기록판의 선 줄은 `set` 만 들어서, 둘이 같은 글을 쟀는지 **물을 이름이 없었다.**"""
    board = tmp_path / "b.toml"
    board.write_text('[[record]]\nset = "s"\nset_sha256 = "셋"\nmetrics = "' + 자 + '"\narm = "우리"\n'
                     'term_off = 0.95\nguard = ["term_off"]\ntol = 0.0\n\n'
                     '[[target]]\nset = "s"\narm = "배포본"\nterm_off = 0.9\n', encoding="utf-8")
    run = tmp_path / "재-20260928-1.jsonl"
    run.write_text(json.dumps(머리(backend="배포본", set_sha256="셋", metrics=자, term_off=0.88),
                              ensure_ascii=False) + "\n", encoding="utf-8")
    monkeypatch.setattr(G, "PATH", board)
    assert G.main([str(run), "--pin-target", "배포본"]) == 1
    assert "모른다" in capsys.readouterr().err
    assert "0.88" not in board.read_text(encoding="utf-8")


def test_해시가_양쪽에_있으면_해시로_묻는다(tmp_path, monkeypatch):
    """★ **자리는 옮기면 바뀌고 해시는 안 바뀐다**(DECISIONS §173). 둘 다 들면 해시가 먼저다."""
    board = tmp_path / "b.toml"
    board.write_text('[[record]]\nset = "s"\nset_sha256 = "셋"\nmetrics = "' + 자 + '"\narm = "우리"\n'
                     'term_off = 0.95\nguard = ["term_off"]\ntol = 0.0\n\n'
                     '[[target]]\nset = "옛자리"\nset_sha256 = "셋"\narm = "배포본"\nterm_off = 0.9\n',
                     encoding="utf-8")
    run = tmp_path / "재-20260928-1.jsonl"
    run.write_text(json.dumps(머리(backend="배포본", set="새자리", set_sha256="셋", metrics=자,
                                   term_off=0.88), ensure_ascii=False) + "\n", encoding="utf-8")
    monkeypatch.setattr(G, "PATH", board)
    assert G.main([str(run), "--pin-target", "배포본"]) == 0, "자리가 달라도 같은 글이다"
    assert "0.88" in board.read_text(encoding="utf-8")


def test_재채점이_셋의_자리도_적는다():
    """적는 자리가 없으면 다음 재채점 판도 똑같이 선을 못 박는다(DECISIONS §173)."""
    t = (ROOT / "tools/rescore.py").read_text(encoding="utf-8")
    for k in ('keep["set"]', 'keep["onto_score"]', 'keep["set_stale"]'):
        assert k in t, f"재채점 머리줄에 {k} 가 없다"


# ---------- 주 셋을 갈아끼운다(DECISIONS §203) ----------

def _옮길판(tmp_path, arm, 이름, 셋해시, **값):
    p = tmp_path / f"{이름}.jsonl"
    p.write_text(json.dumps({"meta": True, "backend": arm, "set": "data/domain/새셋.jsonl",
                             "set_sha256": 셋해시, "onto_sha256": "사전1", "onto_score": "채점1",
                             "metrics": 자, "commit": "abc1234", **값}, ensure_ascii=False) + "\n",
                 encoding="utf-8")
    return str(p)


def _빈판(tmp_path, monkeypatch):
    sb = tmp_path / "sb.toml"
    # ★ `onto_score` 도 비운다 — 안 비우면 저장소의 실제 지문과 시험의 가짜 지문이 갈려
    #   갈아끼움이 「채점하는 칸이 바뀌었다」 로 막힌다(DECISIONS §220 을 세우며 걸렸다)
    sb.write_text(re.sub(r'^(set_sha256|onto_sha256|onto_score) = "[^"]*"', r'\1 = ""',
                         (ROOT / "data/scoreboard.toml").read_text(encoding="utf-8"), flags=re.M),
                  encoding="utf-8")
    monkeypatch.setattr(G, "PATH", sb)
    monkeypatch.setattr(G.catalog, "gate", lambda *a, **k: None)
    return sb


def test_셋이_다르면_update_가_옮기는_길을_모른다(tmp_path, monkeypatch, capsys):
    """★ **막는 것은 옳고, 어떻게 옮기는지를 안 말하는 것이 빚이다**(DECISIONS §203)."""
    sb = _빈판(tmp_path, monkeypatch)
    arm = G.load(sb)["record"][0]["arm"]
    G.main([_옮길판(tmp_path, arm, "H-999-a", "셋1", term_off=0.9, lit=0.9, keep=0.99, josa=1.0), "--update"])
    나중 = _옮길판(tmp_path, arm, "H-999-b", "셋2", term_off=0.95, lit=0.9, keep=0.99, josa=1.0)
    assert G.main([나중, "--update"]) == 1               # 셋이 다르니 막는다 — 옳다
    assert "셋이 다르다" in capsys.readouterr().err


def test_까닭을_주면_셋을_갈아끼운다(tmp_path, monkeypatch, capsys):
    sb = _빈판(tmp_path, monkeypatch)
    arm = G.load(sb)["record"][0]["arm"]
    G.main([_옮길판(tmp_path, arm, "H-999-a", "셋1", term_off=0.9, lit=0.9, keep=0.99, josa=1.0), "--update"])
    나중 = _옮길판(tmp_path, arm, "H-999-b", "셋2", term_off=0.88, lit=0.9, keep=0.99, josa=1.0)
    assert G.main([나중, "--move-set", "H-078 채택 — 떼어둔 셋에서 순서가 유지됐다"]) == 0
    rec = G.load(sb)["record"][0]
    # ★ **떨어진 값도 그대로 박힌다** — 다른 글로 잰 수라 높낮이를 묻지 않는다
    assert rec["term_off"] == 0.88 and rec["set_sha256"] == "셋2" and rec["run"] == "H-999-b"
    assert rec["moved_from"] == "셋1" and "H-078" in rec["moved_why"]
    assert "tol" in capsys.readouterr().out, "옛 셋에서 잰 허용치를 그대로 쓴다고 말 안 했다"


def test_같은_셋이면_옮길_것이_없다고_한다(tmp_path, monkeypatch, capsys):
    sb = _빈판(tmp_path, monkeypatch)
    arm = G.load(sb)["record"][0]["arm"]
    판 = _옮길판(tmp_path, arm, "H-999-a", "셋1", term_off=0.9, lit=0.9, keep=0.99, josa=1.0)
    G.main([판, "--update"])
    assert G.main([판, "--move-set", "까닭"]) == 1
    assert "--update" in capsys.readouterr().err, "막기만 하고 무엇을 쳐야 하는지 안 말한다"


def test_까닭이_비면_안_옮긴다(tmp_path, monkeypatch):
    sb = _빈판(tmp_path, monkeypatch)
    arm = G.load(sb)["record"][0]["arm"]
    판 = _옮길판(tmp_path, arm, "H-999-b", "셋2", term_off=0.9, lit=0.9, keep=0.99, josa=1.0)
    with pytest.raises(SystemExit):
        G.main([판, "--move-set", "   "])


def test_선도_같이_옮긴다(tmp_path, monkeypatch, capsys):
    """선 줄은 셋이 다르면 안 박는다 — **주 셋을 옮기는 판에서만** 연다(§203)."""
    sb = _빈판(tmp_path, monkeypatch)
    선팔 = G.load(sb)["target"][0]["arm"]
    판 = _옮길판(tmp_path, 선팔, "H-999-t", "셋2", term_off=0.88, lit=0.9, keep=1.0, style=0.98)
    assert G.main([판, "--pin-target", 선팔]) == 1
    assert "--move-set" in capsys.readouterr().err, "막으면서 넘는 길을 안 준다"
    assert G.main([판, "--pin-target", 선팔, "--move-set", "H-078 채택"]) == 0
    assert G.load(sb)["target"][0]["set_sha256"] == "셋2"


def test_옛_값을_가리키는_주석은_같이_지운다(tmp_path, monkeypatch):
    """★ 값을 옮기면서 **그 값에 대한 말**을 안 옮기면 주석이 거짓말한다(DECISIONS §208).

    2026-09-29 주 셋을 `d002` 로 옮겼더니 `set_sha256` 옆에 「표시를 든 **d001** 로 다시 만든 판」 이
    그대로 남아 `d002` 의 해시를 `d001` 이라고 설명했다.
    """
    p = tmp_path / "sb.toml"
    p.write_text('[[record]]\narm = "a"\n'
                 'set = "data/domain/d001.jsonl"  # 표시를 든 d001 로 다시 만든 판\n'
                 'onto_sha256 = "x"  # 사전이 바뀌면 막지 않고 말한다\n', encoding="utf-8")
    monkeypatch.setattr(G.catalog, "gate", lambda *a, **k: None)
    G._블록을_고친다("record", "a", {"set": "data/domain/d002.jsonl", "onto_sha256": "y"}, path=p)
    글 = p.read_text(encoding="utf-8")
    assert "d001" not in 글, 글                      # 값에 대한 말은 갔다
    assert "사전이 바뀌면 막지 않고 말한다" in 글    # 규칙에 대한 말은 남는다


def test_값이_같으면_주석도_남는다(tmp_path, monkeypatch):
    """지우는 쪽으로 기울되 **안 바뀐 값의 주석까지 걷어내지는 않는다.**"""
    p = tmp_path / "sb.toml"
    p.write_text('[[record]]\narm = "a"\nterm_off = 0.95  # H-013 에서 잰 값이다\n', encoding="utf-8")
    monkeypatch.setattr(G.catalog, "gate", lambda *a, **k: None)
    G._블록을_고친다("record", "a", {"term_off": 0.96}, path=p)
    assert "H-013" in p.read_text(encoding="utf-8")


def test_선을_박으면_셋_자리도_같이_박힌다(tmp_path, monkeypatch, capsys):
    """★ 문은 「선도 같은 셋인가」 를 `set` 으로 묻는다(DECISIONS §209).

    2026-09-29 주 셋을 옮기니 기록은 `d002` · 선은 `set_sha256` 만 `d002` 이고 `set` 은 `d001` 인
    채로 남았다. 그러면 **선까지의 차가 조용히 안 찍힌다** — 막지도 않고 말하지도 않는다.
    """
    sb = _빈판(tmp_path, monkeypatch)
    선팔 = G.load(sb)["target"][0]["arm"]
    판 = _옮길판(tmp_path, 선팔, "H-999-t", "셋2", term_off=0.88, lit=0.9, keep=1.0, style=0.98)
    assert G.main([판, "--pin-target", 선팔, "--move-set", "H-078 채택"]) == 0
    t = G.load(sb)["target"][0]
    assert t["set_sha256"] == "셋2"
    assert t["set"] == "data/domain/새셋.jsonl", "해시만 갈고 자리를 안 갈았다"


# ---------- 팔을 갈아끼운다(DECISIONS §220) ----------

def _팔판(tmp_path, arm, 이름, **값):
    p = tmp_path / f"{이름}.jsonl"
    p.write_text(json.dumps({"meta": True, "backend": arm, "set": "data/domain/d.jsonl",
                             "set_sha256": "셋1", "onto_sha256": "사전1", "onto_score": "채점1",
                             "metrics": 자, "commit": "abc1234", **값}, ensure_ascii=False) + "\n",
                 encoding="utf-8")
    return str(p)


def test_팔이_다르면_update_는_그_줄을_아예_못_찾는다(tmp_path, monkeypatch, capsys):
    """★ **조용히 끝나는 것이 가장 나쁘다** — 막지도 않고 박지도 않는다(DECISIONS §220)."""
    sb = _빈판(tmp_path, monkeypatch)
    옛 = G.load(sb)["record"][0]["arm"]
    G.main([_팔판(tmp_path, 옛, "a", term_off=0.9, lit=0.9, keep=0.98, josa=1.0), "--update"])
    # ★ **살아 있는 기록판에서 새 이름을 짓지 않는다**(§132 와 같은 병). 2026-09-29 기록판이
    #   `+retry2` 로 갈리자 `replace` 가 아무것도 안 바꿔 이 시험이 제 꼬리를 물었다
    새 = 옛 + "+아직없는처치"
    assert G.main([_팔판(tmp_path, 새, "b", term_off=0.9, lit=0.9, keep=0.99, josa=1.0), "--update"]) == 0
    assert "기록판에 없는 팔" in capsys.readouterr().out
    assert G.load(sb)["record"][0]["arm"] == 옛, "몰래 바뀌었다"


def test_까닭을_주면_팔을_갈아끼운다(tmp_path, monkeypatch, capsys):
    sb = _빈판(tmp_path, monkeypatch)
    옛 = G.load(sb)["record"][0]["arm"]
    G.main([_팔판(tmp_path, 옛, "a", term_off=0.9578, lit=1.0, keep=0.9896, josa=0.99), "--update"])
    새 = "gemma3-4b+ph+marks2+gloss2+retry2+endings+terms"      # 보호가 같은 실재 팔
    옛_ = "gemma3-4b+ph+marks2+gloss2+retry+endings+terms"
    _블록 = G.load(sb)["record"][0]
    G._블록을_고친다("record", _블록["arm"], {"arm": 옛_}, path=sb)
    G.main([_팔판(tmp_path, 옛_, "a2", term_off=0.9578, lit=1.0, keep=0.9896, josa=0.99), "--update"])
    옛 = 옛_
    판 = _팔판(tmp_path, 새, "b", term_off=0.9543, lit=1.0, keep=0.9979, josa=0.99)
    assert G.main([판, "--swap-arm", "H-080 채택 — keep 을 얻고 term_off 는 못 가른다"]) == 0
    rec = G.load(sb)["record"][0]
    assert rec["arm"] == 새 and rec["keep"] == 0.9979
    # ★ **떨어진 값도 그대로 박힌다** — 대신 그만큼 문이 느슨해졌다고 말한다
    assert rec["term_off"] == 0.9543
    assert rec["swapped_from"] == 옛 and "H-080" in rec["swapped_why"]
    assert "느슨" in capsys.readouterr().out


def test_보호가_다른_팔로는_안_갈아끼운다(tmp_path, monkeypatch, capsys):
    """★ 보호가 다르면 같은 칸의 수가 **뜻을 바꾼다**(§156)."""
    sb = _빈판(tmp_path, monkeypatch)
    옛 = G.load(sb)["record"][0]["arm"]
    G.main([_팔판(tmp_path, 옛, "a", term_off=0.9, lit=0.9, keep=0.98, josa=1.0), "--update"])
    판 = _팔판(tmp_path, "aws-translate", "b", term_off=0.9, lit=0.9, keep=0.98, josa=1.0)
    assert G.main([판, "--swap-arm", "까닭"]) == 1
    assert "지키는 지표가 다르다" in capsys.readouterr().err


def test_셋이_다르면_안_갈아끼운다(tmp_path, monkeypatch, capsys):
    sb = _빈판(tmp_path, monkeypatch)
    옛 = G.load(sb)["record"][0]["arm"]
    G.main([_팔판(tmp_path, 옛, "a", term_off=0.9, lit=0.9, keep=0.98, josa=1.0), "--update"])
    새 = 옛 + "+아직없는처치"
    판 = _팔판(tmp_path, 새, "b", term_off=0.9, lit=0.9, keep=0.99, josa=1.0)
    import json as _j
    줄 = [_j.loads(x) for x in pathlib.Path(판).read_text(encoding="utf-8").splitlines()]
    줄[0]["set_sha256"] = "셋2"
    pathlib.Path(판).write_text("\n".join(_j.dumps(x, ensure_ascii=False) for x in 줄) + "\n",
                                encoding="utf-8")
    assert G.main([판, "--swap-arm", "까닭"]) == 1
    assert "셋이 다르다" in capsys.readouterr().err


# ── 벗겨진 자리표시 괄호(DECISIONS §263) ──────────────────────────────────────

def test_괄호가_남은_줄을_찾는다():
    """★ **이름이 제자리여도 망가진 줄이다** — `keep` · `lit` · `RESIDUE` 가 셋 다 초록이다."""
    from seshat import terms
    출력 = {
        "a": "정상적인 번역입니다.",
        "b": "⟧AWS Identity and Access Management⟧ 역할을 지정하십시오.",   # 2026-10-01 실물
        "c": "⟦T1⟧ 을 고릅니다.",                                        # 꼴이 남은 것도 잡는다
    }
    assert terms.괄호가_남은_줄(출력) == ["b", "c"], terms.괄호가_남은_줄(출력)
    # ★ `RESIDUE` 는 b 를 못 본다 — 그것이 이 검사를 만든 까닭이다
    assert not terms.RESIDUE.search(출력["b"])
    assert terms.RESIDUE.search(출력["c"])


def test_문이_괄호_남은_판을_막는다(tmp_path):
    """★ **`--accept` 로도 안 받는다** — 맞바꿈이 아니라 망가진 줄이다."""
    import importlib.util
    import json
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("g", root / "tools/gate.py")
    G = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(G)
    판 = tmp_path / "run.jsonl"
    판.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in [
        {"meta": True, "backend": "x", "set_sha256": "s"},
        {"id": "a", "out": "정상입니다."},
        {"id": "b", "out": "⟧AWS Identity and Access Management⟧ 역할"},
    ]) + "\n", encoding="utf-8")
    assert G.괄호가_남았나(str(판)) == ["b"]
    글 = (root / "tools/gate.py").read_text(encoding="utf-8")
    assert "`--accept` 로도 안 받는다" in 글, "받을 길을 열어 두면 그 길로 간다"
