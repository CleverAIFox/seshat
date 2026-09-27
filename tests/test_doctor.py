"""기계 검사 — 못 재면 빨간불 · 세고 짚기만 한다(DECISIONS §110).

★ **기계를 안 건드린다.** ollama 도 디스크도 부르지 않는다 — 프로브가 못 잴 때 무엇을 하는지만 본다.
  그것이 이 도구의 요점이라서다. 실제로 세는 일이 맞는지는 실행이 말한다.
"""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("doctor", ROOT / "tools/doctor.py")
D = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(D)


def _reset():
    D.HITS.clear()
    D.NOTES.clear()


def test_레이크가_안_붙으면_빨간불이다(monkeypatch):
    """0건이 아니다 — 못 잰 것을 통과로 세면 「없다」가 「괜찮다」가 된다."""
    _reset()
    monkeypatch.setattr(D.paths, "data", lambda: None)
    D.d1_lake()
    assert D.HITS and "SESHAT_DATA" in D.HITS[0][1]


def test_MANIFEST_가_없으면_빨간불이다(tmp_path, monkeypatch):
    _reset()
    monkeypatch.setattr(D.paths, "data", lambda: tmp_path)
    D.d1_lake()
    assert D.HITS and "MANIFEST.tsv" in D.HITS[0][1]


def test_ollama_를_못_부르면_0개가_아니다(monkeypatch):
    _reset()
    monkeypatch.setattr(D.catalog, "weights_outside", lambda e: [])
    monkeypatch.setattr(D, "_ollama", lambda: None)
    D.d2_weights()
    assert D.HITS and "0개가 아니다" in D.HITS[0][1]


def test_배선이_안_부르는_가중치를_짚는다(monkeypatch):
    """이름을 글자로 맞히지 않는다 — `gemma3:4b` 와 `google/gemma-3-4b-it` 는 안 이어진다."""
    _reset()
    monkeypatch.setattr(D.catalog, "weights_outside", lambda e: [])
    monkeypatch.setattr(D, "_ollama", lambda: [{"name": "gemma3:4b", "size": "3.3 GB"},
                                               {"name": "몰래깔린:7b", "size": "4.0 GB"}])
    D.d2_weights()
    assert len(D.HITS) == 1
    assert "몰래깔린:7b" in D.HITS[0][1] and "gemma3:4b" not in D.HITS[0][1]


def test_배선에_있는데_라이선스_대장에_없으면_짚는다(monkeypatch):
    _reset()
    monkeypatch.setattr(D.catalog, "weights_outside", lambda e: [])
    monkeypatch.setattr(D.backends, "WEIGHTS_OF_MODEL", {"새모델:9b": "누가/새모델-9b"})
    monkeypatch.setattr(D, "_ollama", lambda: [{"name": "새모델:9b", "size": "5.0 GB"}])
    D.d2_weights()
    assert len(D.HITS) == 1 and "누가/새모델-9b" in D.HITS[0][1]


def _레이크(tmp_path):
    """빈 레이크를 세운다 — **레이크를 못 물면 작업대를 못 잰다**(DECISIONS §136)."""
    lake = tmp_path / "lake"
    lake.mkdir()
    (lake / "MANIFEST.tsv").write_text("sha256\tpath\tbytes\tadded\torigin\n", encoding="utf-8")
    return lake


def test_작업대에_남은_것을_짚고_다음_명령을_든다(tmp_path, monkeypatch):
    """다시 못 만드는 것이 저장소 밖에서 혼자 살면 안 된다(DECISIONS §103)."""
    _reset()
    monkeypatch.setattr(D, "ROOT", tmp_path)
    monkeypatch.setattr(D.paths, "data", lambda: _레이크(tmp_path))
    (tmp_path / "runs").mkdir()
    (tmp_path / "runs/a.jsonl").write_text("{}\n", encoding="utf-8")
    D.d3_bench()
    assert D.HITS and "lake.py put runs" in D.HITS[0][1]


def test_레이크를_못_물면_작업대를_못_잰다(tmp_path, monkeypatch):
    """0건이 아니다 — 못 잰 것을 「안 간 것 0」 으로 적으면 치우는 쪽이 그것을 믿는다."""
    _reset()
    monkeypatch.setattr(D, "ROOT", tmp_path)
    monkeypatch.setattr(D.paths, "data", lambda: None)
    (tmp_path / "runs").mkdir()
    (tmp_path / "runs/a.jsonl").write_text("{}\n", encoding="utf-8")
    D.d3_bench()
    assert D.HITS and "0건이 아니다" in D.HITS[0][1]


def test_레이크에_들어간_것은_안_짚는다(tmp_path, monkeypatch):
    """**이름이 아니라 해시로 본다**(DECISIONS §136) — 이름만 맞히면 바뀐 파일을 치운다."""
    import hashlib
    _reset()
    lake = tmp_path / "lake"; lake.mkdir()
    (tmp_path / "runs").mkdir()
    f = tmp_path / "runs/a.jsonl"
    f.write_text("{}\n", encoding="utf-8")
    h = hashlib.sha256(f.read_bytes()).hexdigest()
    (lake / "MANIFEST.tsv").write_text("sha256\tpath\tbytes\tadded\torigin\n"
                                       f"{h}\truns/a.jsonl\t3\t2026-09-27\t-\n", encoding="utf-8")
    monkeypatch.setattr(D, "ROOT", tmp_path)
    monkeypatch.setattr(D.paths, "data", lambda: lake)
    D.d3_bench()
    assert D.HITS == []
    _reset()
    f.write_text("{\"바뀜\": 1}\n", encoding="utf-8")        # 이름은 같고 내용이 다르다
    D.d3_bench()
    assert D.HITS and "안 간 파일 1개" in D.HITS[0][1]


def test_없어도_되는_키는_안_센다(monkeypatch, tmp_path):
    _reset()
    (tmp_path / ".env.example").write_text("# 주석\nSESHAT_DATA=\nHF_TOKEN=\n", encoding="utf-8")
    monkeypatch.setattr(D, "ROOT", tmp_path)
    monkeypatch.setenv("SESHAT_DATA", "/어딘가")
    monkeypatch.setenv("HF_TOKEN", "")
    D.d4_env()
    assert D.HITS == []          # HF_TOKEN 은 쓰는 도구가 있을 때만 필요하다
    monkeypatch.setenv("SESHAT_DATA", "")
    _reset()
    D.d4_env()
    assert D.HITS and "SESHAT_DATA" in D.HITS[0][1]


def test_프로브가_죽으면_그것이_결과다(monkeypatch):
    """조용히 넘어가지 않는다 — 죽은 프로브를 0건으로 세면 검사가 거짓말을 한다."""
    _reset()
    def 죽는다():
        raise RuntimeError("일부러")
    죽는다.__name__ = "d9_죽는다"
    monkeypatch.setattr(D, "PROBES", (죽는다,))
    assert D.main([]) == 1
    assert any("프로브가 죽었다" in w for _, w in D.HITS)


def test_verify_는_이것을_부르지_않는다():
    """CI 에는 레이크도 ollama 도 없다. 기계 검사를 CI 에 넣으면 거기서 늘 빨갛다."""
    assert "doctor.py" not in (ROOT / "tools/verify.sh").read_text(encoding="utf-8")
