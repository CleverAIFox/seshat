"""레이크는 넣기만 하고 바꾸지 않는다 · 대장 밖을 지우지 않고 짚는다 · 가설의 근거가 있는가(DECISIONS §21)."""
import importlib.util
import os
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("lake", ROOT / "tools/lake.py")
lake = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lake)
from seshat import paths  # noqa: E402


def _lake(tmp_path):
    d = tmp_path / "lake"
    lake.init(d)
    return d


def _f(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_넣은_것은_대장에_오르고_검사를_통과한다(tmp_path):
    d = _lake(tmp_path)
    assert lake.put(d, "runs", [_f(tmp_path, "H-001-base-1.jsonl", "a\n")], now="t") == 0
    assert (d / "runs/H-001-base-1.jsonl").read_text() == "a\n"
    assert list(lake.manifest(d)) == ["runs/H-001-base-1.jsonl"]
    assert lake.check(d, ledger=tmp_path / "없음.md") == []


def test_같은_내용은_다시_넣어도_한_줄이다(tmp_path):
    d = _lake(tmp_path)
    f = _f(tmp_path, "x.jsonl", "a\n")
    lake.put(d, "runs", [f])
    assert lake.put(d, "runs", [f]) == 0
    assert len((d / "MANIFEST.tsv").read_text().splitlines()) == 2


def test_같은_이름에_다른_내용은_거절한다(tmp_path):
    d = _lake(tmp_path)
    lake.put(d, "runs", [_f(tmp_path, "x.jsonl", "a\n")])
    (tmp_path / "b").mkdir()
    assert lake.put(d, "runs", [_f(tmp_path / "b", "x.jsonl", "b\n")]) == 1
    assert (d / "runs/x.jsonl").read_text() == "a\n"


def test_바뀐_파일과_대장_밖_파일을_짚고_지우지_않는다(tmp_path):
    d = _lake(tmp_path)
    lake.put(d, "raw", [_f(tmp_path, "glossary.html", "원본")])
    (d / "raw/glossary.html").write_text("고침", encoding="utf-8")
    (d / "runs/몰래.jsonl").write_text("?", encoding="utf-8")
    fails = lake.check(d, ledger=tmp_path / "없음.md")
    assert any(f.startswith("바뀌었다 raw/glossary.html") for f in fails)
    assert any(f.startswith("대장 밖  runs/몰래.jsonl") for f in fails)
    assert (d / "runs/몰래.jsonl").exists()


def test_가설_대장의_근거가_레이크에_없으면_실패한다(tmp_path):
    d = _lake(tmp_path)
    led = _f(tmp_path, "h.md", "| H-016 | 채택 | … | runs/H-016-rescore-1.jsonl — keep 0.99 |\n")
    assert lake.check(d, ledger=led) == ["근거 없음 runs/H-016-rescore-1.jsonl — 가설 대장이 드는데 레이크에 없다"]
    lake.put(d, "runs", [_f(tmp_path, "H-016-rescore-1.jsonl", "r\n")])
    assert lake.check(d, ledger=led) == []


def test_캐시는_대장_밖이다(tmp_path):
    d = _lake(tmp_path)
    (d / "cache/flores.jsonl").write_text("x", encoding="utf-8")
    assert lake.check(d, ledger=tmp_path / "없음.md") == []


def test_실제_가설_대장에서_근거를_찾는다():
    """정규식 카나리아 — 대장에 runs/ 근거가 하나는 있다(H-016)."""
    assert lake.EVIDENCE.findall((ROOT / "docs/hypotheses.md").read_text(encoding="utf-8"))


def test_셸이_env_를_이긴다(tmp_path, monkeypatch):
    env = _f(tmp_path, ".env", "SESHAT_DATA=/from/env\nSESHAT_INBOX=\nexport X_SESHAT_T='q'\n")
    monkeypatch.setenv("SESHAT_DATA", "/from/shell")
    monkeypatch.delenv("SESHAT_INBOX", raising=False)
    monkeypatch.delenv("X_SESHAT_T", raising=False)
    paths.load_dotenv(env)
    assert os.environ["SESHAT_DATA"] == "/from/shell"
    assert "SESHAT_INBOX" not in os.environ          # 빈 값은 미설정이다
    assert os.environ["X_SESHAT_T"] == "q"


def test_붙지_않은_드라이브는_종료코드_2다(tmp_path):
    empty = tmp_path / "mnt_f"
    empty.mkdir()                                      # WSL 은 안 붙어도 빈 디렉터리를 둔다
    r = subprocess.run(["python3", str(ROOT / "tools/lake.py"), "check"], capture_output=True, text=True,
                       env={**os.environ, "SESHAT_DATA": str(empty)})
    assert r.returncode == 2 and "MANIFEST.tsv" in r.stderr
