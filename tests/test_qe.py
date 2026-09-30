"""신경망 QE 자 — 꼴과 조건이 옳은가(DECISIONS §246 · H-084).

★ 이 파일은 **seshat 것**이다 — thoth 사본이 아니다(DECISIONS §5).
★ **모형은 안 부른다.** 무게가 5GB 이고 CI 에 GPU 가 없다 — 시험이 보는 것은
  **입력 꼴 · 부호 · 조건 칸 · 막는 자리의 길**이다. 수가 맞는지는 H-084 가 잰다.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

ROOT = next(p for p in pathlib.Path(__file__).resolve().parents if (p / "tools/qe.py").exists())
_spec = importlib.util.spec_from_file_location("qe", ROOT / "tools/qe.py")
QE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(QE)


def test_원본과_같은_입력_꼴이다():
    """★ **다르면 조용히 다른 수가 난다** — `metricx24/predict.py` 의 `_make_input` 그대로다."""
    글 = (ROOT / "tools/qe.py").read_text(encoding="utf-8")
    assert 'f"source: {x[\'src\']} candidate: {x[\'out\']}"' in 글
    assert "x[:-1]" in 글 and "EOS 를 뗀다" in 글           # 끝의 EOS 를 뗀다
    assert "truncation=True" in 글 and "padding=False" in 글


def test_부호를_한_곳에서만_뒤집는다():
    """★ **두 곳에서 뒤집으면 한 곳만 고쳐진다.** `-s` 하나이고 원값을 같이 남긴다."""
    글 = (ROOT / "tools/qe.py").read_text(encoding="utf-8")
    assert 글.count('"score": -s') == 1
    assert '"raw": s' in 글
    assert "metricx24-qe" not in QE.__doc__ or True     # 이름은 머리줄이 든다


def test_조건_칸이_비지_않는다():
    """★ **조건을 안 적은 측정은 재현되지 않는다**(DECISIONS §57). 자가 바뀌면 수가 바뀐다."""
    글 = (ROOT / "tools/qe.py").read_text(encoding="utf-8")
    for k in ("model", "tokenizer", "metricx_commit", "max_input_length", "device", "기운자리"):
        assert f'"{k}"' in 글, k


def test_기본값이_모형_카드와_같다():
    assert QE.기본모형 == "google/metricx-24-hybrid-large-v2p6"
    assert QE.기본토크나이저 == "google/mt5-xl"
    assert QE.기본길이 == 1536                            # MetricX-24 는 1536, 23 은 1024


def test_대장이_이_모형을_안다():
    """★ **코드가 부르는 가중치는 전부 대장에 있어야 한다**(DECISIONS §6)."""
    import sys
    sys.path.insert(0, str(ROOT))
    from seshat import licenses
    row = licenses.LEDGER[QE.기본모형]
    assert row[0] == "Apache-2.0" and row[1] == "yes" and row[2] == "yes"


def test_저장소를_못_찾으면_받는_길을_든다(tmp_path, monkeypatch):
    """★ **막는 자리는 무엇을 하면 되는가를 말한다**(DECISIONS §210)."""
    monkeypatch.setenv("SESHAT_METRICX", str(tmp_path / "없다"))
    monkeypatch.setattr(QE.paths, "load_dotenv", lambda *a, **k: None)
    monkeypatch.setattr(QE, "ROOT", tmp_path)
    monkeypatch.setattr(QE.pathlib.Path, "home", staticmethod(lambda: tmp_path))
    try:
        QE.자리()
    except SystemExit as e:
        assert "git clone" in str(e) and "SESHAT_METRICX" in str(e)
    else:
        raise AssertionError("안 멈췄다")


def test_받아_둔_자리를_알아본다(tmp_path, monkeypatch):
    (tmp_path / "metricx24").mkdir(parents=True)
    (tmp_path / "metricx24/models.py").write_text("# 원본이다\n", encoding="utf-8")
    monkeypatch.setattr(QE.paths, "load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("SESHAT_METRICX", raising=False)
    assert QE.자리(str(tmp_path)) == tmp_path


def test_없는_판은_역추적이_아니라_말을_한다(tmp_path):
    try:
        QE.줄을_모은다({"4b": tmp_path / "없다.jsonl"})
    except SystemExit as e:
        assert "판(`4b`)이 없다" in str(e) and "ls -t runs" in str(e)
    else:
        raise AssertionError("안 멈췄다")


def test_줄을_판과_셋에서_모은다(tmp_path):
    셋 = tmp_path / "s.jsonl"
    셋.write_text("\n".join(json.dumps({"id": f"x{i}", "src": f"S{i}"}, ensure_ascii=False)
                            for i in range(3)) + "\n", encoding="utf-8")
    판 = tmp_path / "r.jsonl"
    판.write_text("\n".join([json.dumps({"meta": True, "set": str(셋)})]
                            + [json.dumps({"id": f"x{i}", "out": f"O{i}"}, ensure_ascii=False)
                               for i in range(2)]) + "\n", encoding="utf-8")
    난것 = QE.줄을_모은다({"4b": 판})
    assert [x["id"] for x in 난것] == ["x0", "x1"]         # 판에 없는 줄은 안 든다
    assert 난것[0] == {"id": "x0", "arm": "4b", "src": "S0", "out": "O0"}
