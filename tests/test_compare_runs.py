"""결과 대조 도구(MASTER §7 R7)."""
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("cr", ROOT / "tools/compare_runs.py")
cr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cr)


def _run(p, outs, sha="x"):
    lines = [{"meta": True, "set_sha256": sha, "keep": 0.5, "style": 1.0, "ms": 1}]
    lines += [{"id": i, "src": "s", "out": o} for i, o in outs.items()]
    p.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in lines) + "\n", encoding="utf-8")
    return str(p)


def test_줄마다_이기고_진_것을_가른다():
    spec = {"1": {"keep": ["Amazon S3"], "construction": "SV"}, "2": {"keep": ["Athena"], "construction": "SVO"},
            "3": {"keep": ["IAM"], "construction": "SV"}}
    a = {"1": {"out": "아마존 S3"}, "2": {"out": "Athena 를"}, "3": {"out": "IAM"}}
    b = {"1": {"out": "Amazon S3를"}, "2": {"out": "아테나"}, "3": {"out": "⟦T1⟧"}}
    r = cr.compare(a, b, spec)
    assert r["b_better"] == ["1"] and r["b_worse"] == ["2", "3"] and r["residue"] == ["3"]
    assert r["by_construction"]["SV"] == [2, 1, 1]


def test_평가셋이_다르면_멈춘다(tmp_path):
    x = _run(tmp_path / "a.jsonl", {"1": "가"}, "aaa")
    y = _run(tmp_path / "b.jsonl", {"1": "가"}, "bbb")
    assert cr.main([x, y]) == 1
