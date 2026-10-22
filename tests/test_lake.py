"""레이크는 넣기만 하고 바꾸지 않는다 · 대장 밖을 지우지 않고 짚는다 · 가설의 근거가 있는가(DECISIONS §21)."""
import importlib.util
import os
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("lake", ROOT / "tools/lake.py")
lake = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lake)
from seshat import paths


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
    lake.put(d, "raw", [_f(tmp_path, "glossary.html", "원본")], into="aws-docs")
    (d / "raw/aws-docs/glossary.html").write_text("고침", encoding="utf-8")
    (d / "runs/몰래.jsonl").write_text("?", encoding="utf-8")
    fails = lake.check(d, ledger=tmp_path / "없음.md")
    assert any(f.startswith("바뀌었다 raw/aws-docs/glossary.html") for f in fails)
    assert any(f.startswith("대장 밖  runs/몰래.jsonl") for f in fails)
    assert (d / "runs/몰래.jsonl").exists()


def test_가설_대장의_근거가_레이크에_없으면_실패한다(tmp_path):
    d = _lake(tmp_path)
    led = _f(tmp_path, "h.md", "| H-016 | 채택 | … | runs/H-016-rescore-1.jsonl — keep 0.99 |\n")
    assert lake.check(d, ledger=led) == ["근거 없음 runs/H-016-rescore-1.jsonl — 가설 대장이 드는데 레이크에 없다"]
    lake.put(d, "runs", [_f(tmp_path, "H-016-rescore-1.jsonl", "r\n")])
    assert lake.check(d, ledger=led) == []


def test_캐시는_해시_대장_밖이지만_카탈로그_안이다(tmp_path):
    d = _lake(tmp_path)
    (d / "cache/papers").mkdir()
    (d / "cache/papers/x.pdf").write_text("x", encoding="utf-8")
    (d / "cache/flores.jsonl").write_text("x", encoding="utf-8")
    assert lake.check(d, ledger=tmp_path / "없음.md") == [
        "카탈로그 밖 cache/flores.jsonl — data/catalog.toml 에 자리를 적거나 치운다"]


def test_카탈로그에_없는_자리에는_못_넣는다(tmp_path):
    d = _lake(tmp_path)
    assert lake.put(d, "raw", [_f(tmp_path, "pairs.jsonl", "p")]) == 1          # raw/ 바로 아래는 자리가 없다
    assert lake.put(d, "raw", [_f(tmp_path, "pairs.jsonl", "p")], into="thoth-pairs") == 0
    assert (d / "raw/thoth-pairs/pairs.jsonl").exists()


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


def test_패키지를_부르면_env_가_얹힌다():
    """도구마다 따로 읽으면 부르는 방법에 따라 설정이 있다 없다 한다(DECISIONS §39)."""
    import subprocess
    code = "import seshat, sys; print('seshat.paths' in sys.modules)"
    r = subprocess.run(["python3", "-c", code], capture_output=True, text=True, cwd=ROOT)
    assert r.stdout.strip() == "True"                 # 패키지를 부르는 순간 .env 가 얹힌다


def test_env_에_같은_열쇠가_둘이면_나중_줄이_이기고_말한다(tmp_path, monkeypatch, capsys):
    """셸 로더는 소싱이라 나중 줄이 이긴다 — 파이썬이 앞줄을 집으면 두 도구가 갈린다(DECISIONS §73)."""
    env = tmp_path / ".env"
    env.write_text("HF_TOKEN=hf_죽은것\nSESHAT_INBOX=/x\nHF_TOKEN=hf_새것\n", encoding="utf-8")
    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("SESHAT_INBOX", raising=False)
    paths.load_dotenv(env)
    assert os.environ["HF_TOKEN"] == "hf_새것"
    assert "HF_TOKEN" in capsys.readouterr().err        # 조용히 고르지 않는다


def test_셸이_이긴다는_규칙은_그대로다(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("HF_TOKEN=hf_파일\n", encoding="utf-8")
    monkeypatch.setenv("HF_TOKEN", "hf_셸")
    paths.load_dotenv(env)
    assert os.environ["HF_TOKEN"] == "hf_셸"


def test_레이크에서_찾는다(tmp_path):
    """★ **넣는 길만 있고 찾는 길이 없었다**(DECISIONS §175). 판이 레이크로 간 뒤로는
    `runs/H-050-*.jsonl` 이 글로브가 안 맞아 그대로 넘어가고 도구가 추적을 뱉는다."""
    (tmp_path / "runs").mkdir()
    for n in ("H-050-nova-d001-20260927-181909.jsonl", "H-045-12b-d001-20260927-135211.jsonl"):
        (tmp_path / "runs" / n).write_text("{}\n", encoding="utf-8")
    assert len(lake.찾는다(tmp_path, "H-050-nova")) == 1, "조각만 줘도 찾는다"
    assert len(lake.찾는다(tmp_path, "H-0*-d001-*.jsonl")) == 2, "글로브는 그대로 쓴다"
    assert lake.찾는다(tmp_path, "없는것") == []


def _rs():
    s = importlib.util.spec_from_file_location("rescore", ROOT / "tools/rescore.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def test_없는_판에_추적을_안_뱉는다(tmp_path):
    """★ **막는 도구는 넘는 길을 같이 준다**(DECISIONS §174 · §175)."""
    import pytest as _p
    with _p.raises(SystemExit) as e:
        _rs().rescore(str(tmp_path / "runs/H-050-nova-d001-20260927-181909.jsonl"), "x")
    말 = str(e.value)
    assert "레이크" in 말 and "lake.py ls" in 말 and "H-050-nova-d001" in 말


def test_못_읽으면_역추적이_아니라_말을_한다(tmp_path, monkeypatch, capsys):
    """★ **벽도 없고 길도 없는 자리**(DECISIONS §232 · §231 의 셋째 얼굴).

    2026-09-30 윈도우 업데이트가 메모리를 먹은 채로 `verify` 를 돌렸더니 `sha256` 이 `OSError` 를
    그대로 올려 역추적 여섯 줄을 뱉었다. `check_ways` 는 `SystemExit` · `print("✗")` 만 보므로
    **이런 자리는 세지도 않는다.**
    """
    p = tmp_path / "x.jsonl"
    p.write_text("{}\n", encoding="utf-8")

    def 못읽게(_self, *a, **k):
        raise OSError(12, "Cannot allocate memory")
    monkeypatch.setattr(pathlib.Path, "open", 못읽게)
    try:
        lake.sha256(p)
    except lake.못읽음 as e:
        assert "errno 12" in str(e) and p.name in str(e)
    else:
        raise AssertionError("OSError 를 그대로 올렸다")


def test_못_읽은_것은_고장이라_2_로_끝난다(tmp_path, monkeypatch, capsys):
    """★ **위반은 1 이고 고장은 2 다**(§21). 1 을 내면 「레이크가 깨졌다」 로 읽힌다."""
    monkeypatch.setattr(lake.paths, "require_lake", lambda: tmp_path)
    # ★ **카나리아를 재운다**(DECISIONS §315). `_canary` 도 `check` 를 부르므로 아래 흉내가
    #   거기서 먼저 터진다 — 그러면 이 시험이 보려는 **`check` 의 실패 길**을 못 본다.
    #   둘 다 2 로 끝나지만 **같은 2 가 아니다** : 하나는 레이크가, 하나는 판별식이 죽은 것이다.
    monkeypatch.setattr(lake, "_canary", lambda: None)
    monkeypatch.setattr(lake, "check", lambda *a, **k: (_ for _ in ()).throw(lake.못읽음("x — 메모리")))
    assert lake.main(["check"]) == 2
    err = capsys.readouterr().err
    assert "레이크를 못 읽었다" in err
    assert "ollama stop" in err and "못 보는 것은 통과가 아니다" in err


def test_카나리아가_산다():
    """★ **아무것도 못 찾는 자와 고장 난 자는 구별되지 않는다**(DECISIONS §239 · §315).

    이 자는 2026-10-22 까지 `check_scope` 의 눈 밖이라 **카나리아가 없었다.**
    """
    assert lake._canary() is None, "카나리아는 말없이 돌아온다 — 죽으면 SystemExit 다"


def test_main_이_판별식을_먼저_묻는다(tmp_path, monkeypatch):
    """★ **안 부르는 카나리아는 없는 카나리아다.** 위 시험이 그것을 재우므로 여기서 센다."""
    monkeypatch.setattr(lake.paths, "require_lake", lambda: tmp_path)
    불렸나: list[int] = []
    monkeypatch.setattr(lake, "_canary", lambda: 불렸나.append(1))
    monkeypatch.setattr(lake, "check", lambda *a, **k: [])
    lake.init(tmp_path)
    lake.main(["check"])
    assert 불렸나 == [1]
