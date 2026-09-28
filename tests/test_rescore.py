"""재채점 — 팔마다 다른 이름으로 남는다(DECISIONS §26)."""
import datetime as dt
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("rescore", ROOT / "tools/rescore.py")
rs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rs)

NOW = dt.datetime(2026, 9, 23, 9, 21, 29)


def test_같은_초에_두_팔을_재채점해도_이름이_갈린다():
    a = rs.out_path("H-021", "/mnt/f/projects/seshat/runs/H-001-base-20260922-162150.jsonl", NOW)
    b = rs.out_path("H-021", "/mnt/f/projects/seshat/runs/H-001-ph-20260922-162419.jsonl", NOW)
    assert a != b
    assert a.name == "H-021-rescore-H-001-base-20260922-162150-20260923-092129.jsonl"


def test_재채점의_재채점이_이름을_늘이지_않는다():
    p = rs.out_path("H-021", "runs/H-016-rescore-20260922-164235.jsonl", NOW)
    assert p.name.count("rescore") == 1


def test_후처리_이름이_결과_파일에_남는다():
    a = rs.out_path("H-023", "runs/H-019-x-20260923-110505.jsonl", NOW)
    b = rs.out_path("H-023", "runs/H-019-x-20260923-110505-endings", NOW)
    assert a != b and b.name.endswith("-endings-20260923-092129.jsonl")


def test_자_판은_물려받지_않고_지금_것을_적는다(tmp_path):
    """다시 잰 것은 **지금 자로** 잰 것이다 — 옛 판을 물려받으면 머리줄이 거짓말한다(§145)."""
    import json as _json

    from seshat import evaluate
    run = tmp_path / "옛.jsonl"
    run.write_text("\n".join(_json.dumps(x, ensure_ascii=False) for x in (
        {"meta": True, "backend": "가짜", "metrics": "1", "commit": "abc", "set_sha256": "옛셋"},
        {"id": "a", "src": "Increase the quota.", "out": "할당량을 늘리십시오."})) + "\n",
        encoding="utf-8")
    셋 = tmp_path / "s.jsonl"
    셋.write_text(_json.dumps({"id": "a", "src": "Increase the quota."}, ensure_ascii=False) + "\n",
                  encoding="utf-8")
    head, _ = rs.rescore(str(run), str(셋), post="none")
    assert head["metrics"] == evaluate.METRICS_VER != "1"
