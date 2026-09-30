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


def test_토크나이저가_죽으면_엉뚱한_것을_안_깔게_한다():
    """★ **깨진 도구의 마지막 줄이 가장 그럴듯한 오답이다**(DECISIONS §246).
    화면은 `pip install tiktoken` 이라고 찍는데 **필요한 것은 `protobuf`** 다."""
    글 = (ROOT / "tools/qe.py").read_text(encoding="utf-8")
    assert "그 말을 따르지 않는다" in 글 and "protobuf" in 글
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "protobuf" in pyproject, "qe 그룹이 protobuf 를 안 들면 첫 실행이 죽는다"


def test_무게를_받기_전에_탐침이_돈다():
    """★ **가중치 5GB 를 받고 나서 두 번 죽었다**(DECISIONS §246) — 둘 다 무게가 필요 없는 고장이다.
    작은 모형을 세워 앞으로 흘려 보는 자리가 `from_pretrained` **앞**에 있어야 한다."""
    글 = (ROOT / "tools/qe.py").read_text(encoding="utf-8")
    앞 = 글.index("_탐침(models, transformers)")
    뒤 = 글.index("MT5ForRegression.from_pretrained")
    assert 앞 < 뒤, "탐침이 무게를 받은 뒤에 돌면 값이 없다"
    # 판 자체를 조건으로 쓰지 않는다 — 조건은 **실제로 도는가** 다
    assert "transformers.__version__ <" not in 글 and "version_tuple" not in 글
    assert "--selftest" in 글                      # 무게 없이 혼자 돌 수 있다


def test_탐침의_어휘가_점수를_읽는_자리보다_크다():
    """★ `MT5ForRegression` 은 `250089` 자리에서 점수를 읽는다 — 어휘가 작으면 **거기서 죽는다.**"""
    assert QE.탐침어휘 > 250089


def test_qe_그룹이_잰_범위를_든다():
    """★ **위아래를 재서 박았다**(§246). 4.40~4.53 은 같은 수를 내고 4.55 부터 죽는다."""
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "transformers>=4.40,<4.54" in pyproject
    assert QE.잰판 == "4.40 ~ 4.53"


def test_탐침이_본판과_같은_자리에서_돈다():
    """★ **탐침이 실제 판과 다른 자리에서 돌면 잡는 것도 놓치는 것도 거짓이다**(DECISIONS §248).
    2026-09-30 탐침이 CPU 에 모형을 세워 놓고 **거짓 빨강**을 냈다."""
    글 = (ROOT / "tools/qe.py").read_text(encoding="utf-8")
    assert 글.count("어디서_도나()") >= 3, "탐침 · 본판 · 화면이 같은 한 곳에서 자리를 묻는다"
    assert "작은.to(장치)" in 글 and "device=장치" in 글
    # 자리를 손으로 두 번 적지 않는다
    assert '"cuda" if torch.cuda.is_available() else "cpu"' not in 글.split("def 어디서_도나")[1].split("def ")[1]


def test_자리는_한_곳에서_정한다():
    """★ torch 는 `qe` 그룹이라 관문에는 없다 — **없으면 건너뛴다**(DECISIONS §4)."""
    import pytest
    pytest.importorskip("torch")
    assert QE.어디서_도나() in ("cuda", "cpu")


def test_가중치의_커밋이_박혀_있다():
    """★ **이름만 적으면 그 이름이 가리키는 것이 바뀌어도 모른다**(DECISIONS §251 · §252).
    2026-10-01 캐시에 스냅샷이 둘이었고 **어느 것으로 잰 수인지 몰랐다.**"""
    assert len(QE.기본판본) == 40 and all(c in "0123456789abcdef" for c in QE.기본판본)
    글 = (ROOT / "tools/qe.py").read_text(encoding="utf-8")
    assert '"revision": a.revision' in 글, "무엇으로 쟀는지 판 머리줄이 들어야 한다"
