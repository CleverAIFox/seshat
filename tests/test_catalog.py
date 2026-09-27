"""카탈로그 — 칸 · 쓰임 · 미확인 라이선스는 학습 불가 · data/ 의 카탈로그 밖 파일(DECISIONS §22)."""
import pathlib

import pytest

from seshat import catalog, paths

ROOT = pathlib.Path(__file__).resolve().parent.parent

OK = {"id": "a", "where": "lake:raw/a/*", "origin": "o", "license": "CC BY 4.0", "uses": ["eval"],
      "how": "사람", "feeds": ["seshat/evaluate.py"]}


def test_실제_카탈로그가_통과한다():
    entries = catalog.load()
    assert catalog.validate(entries) == []
    assert catalog.unlisted_repo_files(entries) == []


def test_미확인_라이선스는_학습에_못_쓴다():
    assert catalog.validate([{**OK, "license": "미확인", "uses": ["train"]}]) == ["a: 라이선스가 미확인인데 train 을 달았다"]


def test_빈_칸_모르는_쓰임_겹친_id_없는_도구():
    fails = catalog.validate([{**OK, "origin": ""}, {**OK, "uses": ["publish"]}, {**OK, "how": "tools/없다.py"}])
    assert any("`origin` 가 비었다" in f for f in fails)
    assert any("모르는 쓰임" in f for f in fails)
    assert any("id 가 겹친다" in f for f in fails)
    assert any("tools/없다.py" in f for f in fails)


def test_쓰임이_문이다():
    assert catalog.allowed("thoth-pairs", "train")
    assert not catalog.allowed("flores-plus", "train")     # 평가가 학습에 새지 않는다
    assert not catalog.allowed("aws-docs", "train")
    assert not catalog.allowed("없는-출처", "eval")


def test_자리를_맞춘다():
    e = catalog.load()
    assert catalog.match(e, "lake", "runs/H-001-base-1.jsonl")["id"] == "runs"
    assert catalog.match(e, "lake", "raw/thoth-pairs/2026-09.jsonl")["id"] == "thoth-pairs"
    assert catalog.match(e, "lake", "raw/x.jsonl") is None
    assert catalog.match(e, "repo", "data/bench/flores_plus.dev.jsonl")["id"] == "flores-plus"


def test_data_밖에_몰래_둔_파일을_짚는다(tmp_path):
    (tmp_path / "data/ontology").mkdir(parents=True)
    (tmp_path / "data/ontology/aws.jsonl").write_text("{}")
    (tmp_path / "data/scratch.csv").write_text("x")
    assert catalog.unlisted_repo_files(catalog.load(), root=tmp_path) == ["data/scratch.csv"]


def test_가중치가_카탈로그_밖에_있으면_짚는다(tmp_path, monkeypatch):
    """카탈로그는 약속이고 ollama 는 그 약속을 모른다(DECISIONS §106)."""
    lake = tmp_path / "lake"; (lake / "cache/models").mkdir(parents=True)
    outside = tmp_path / "home/.ollama/models"; outside.mkdir(parents=True)
    (outside / "blob").write_text("가중치인 척", encoding="utf-8")
    entries = catalog.load()
    monkeypatch.setenv("SESHAT_DATA", str(lake))

    got = catalog.weights_outside(entries, where=(str(outside), "시험"))
    assert got and "카탈로그는 lake:cache/models/*" in got[0] and str(outside) in got[0]

    inside = lake / "cache/models/ollama"; inside.mkdir(parents=True)
    (inside / "blob").write_text("가중치인 척", encoding="utf-8")
    (outside / "blob").unlink()                       # 기본 자리를 비운다 — 옮긴 상태다
    assert catalog.weights_outside(entries, where=(str(inside), "시험")) == []

    # 빈 자리는 짚지 않는다 — 아직 아무것도 안 받은 기계다
    empty = tmp_path / "empty"; empty.mkdir()
    assert catalog.weights_outside(entries, where=(str(empty), "시험")) == []

    # 레이크가 없는 기계(CI)에서는 묻지 않는다
    monkeypatch.setenv("SESHAT_DATA", "")
    assert catalog.weights_outside(entries, where=(str(outside), "시험")) == []


def test_옮겼는데_기본_자리에_다시_받은_것을_짚는다(tmp_path, monkeypatch):
    """`.env` 는 파이썬만 읽는다. 셸이 모르면 ollama 가 기본 자리에 다시 받는다(DECISIONS §111).

    ★ 선언한 자리에만 파일이 있는지 묻던 검사는 이 상태를 **통과시켰다.**
    """
    lake = tmp_path / "lake"
    inside = lake / "cache/models/ollama"; inside.mkdir(parents=True)
    (inside / "blob").write_text("옮긴 것", encoding="utf-8")
    home = tmp_path / "home"; default = home / ".ollama/models"; default.mkdir(parents=True)
    (default / "blob").write_text("다시 받은 것", encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SESHAT_DATA", str(lake))
    got = catalog.weights_outside(catalog.load(), where=(str(inside), "시험"))
    assert len(got) == 1 and str(default) in got[0]
    assert "셸이 OLLAMA_MODELS 를 모른다" in got[0]

    # 기본 자리를 치우면 조용해진다
    (default / "blob").unlink()
    assert catalog.weights_outside(catalog.load(), where=(str(inside), "시험")) == []


def test_층_선언이_실물과_맞는다():
    """선언이 정본이고 `.gitignore` · `paths.TIERS` · `lake.MANAGED` 가 따라온다(DECISIONS §114)."""
    assert catalog.check_layers() == []
    from seshat import paths
    assert set(paths.TIERS) == set(catalog.lake_tiers())
    assert set(catalog.managed_tiers()) == {"raw", "runs"}


def test_커밋하는_층을_ignore_하면_짚는다(tmp_path):
    t = (tmp_path / "c.toml")
    t.write_text('[layers."정본"]\nbase="repo"\ndirs=["data/ontology"]\ncommitted=true\n'
                 'regenerable=false\nmanaged=false\nwhat="x"\n[[source]]\nid="a"\n'
                 'where="repo:x"\norigin="o"\nlicense="l"\nuses=["eval"]\nhow="사람"\n', encoding="utf-8")
    root = tmp_path
    (root / ".gitignore").write_text("data/ontology/\n", encoding="utf-8")
    fails = catalog.check_layers(root, t)
    assert any("committed 인데 .gitignore 가" in f for f in fails)


def test_안_커밋하는_층이_ignore_밖이면_짚는다(tmp_path):
    t = (tmp_path / "c.toml")
    t.write_text('[layers."셋"]\nbase="repo"\ndirs=["data/bench"]\ncommitted=false\n'
                 'regenerable=true\nmanaged=false\nwhat="x"\n[[source]]\nid="a"\n'
                 'where="repo:x"\norigin="o"\nlicense="l"\nuses=["eval"]\nhow="사람"\n', encoding="utf-8")
    (tmp_path / ".gitignore").write_text("# 비었다\n", encoding="utf-8")
    fails = catalog.check_layers(tmp_path, t)
    assert any(".gitignore 에 data/bench 가 없다" in f for f in fails)


def test_lake_의_MANAGED_는_선언에서_온다():
    """손으로 적으면 선언과 갈린다 — §57 의 「배선에서 끌어온다」와 같은 규칙이다."""
    src = (ROOT / "tools/lake.py").read_text(encoding="utf-8")
    assert "MANAGED = catalog.managed_tiers()" in src
    assert 'MANAGED = ("raw", "runs")' not in src


def test_feeds_는_비워_두지_않는다():
    """`uses` 는 허가고 `feeds` 는 사실이다 — 둘을 합치면 아무도 안 읽는 출처가 「쓸 수 있음」으로 남는다."""
    assert any("`feeds` 가 비었다" in f for f in catalog.validate([{**OK, "feeds": []}]))
    assert any("`feeds` 가 비었다" in f for f in catalog.validate([{k: v for k, v in OK.items() if k != "feeds"}]))


def test_아무도_안_읽으면_언제_쓸지를_적는다():
    assert catalog.feeds_fail("a", "미투입 — PLAN #6 이 뽑을 때") == []
    assert any("로 시작한다" in f for f in catalog.feeds_fail("a", "나중에"))
    assert any("언제 쓸지" in f for f in catalog.feeds_fail("a", "미투입 — "))


def test_없는_도구를_읽는다고_적으면_짚는다(tmp_path):
    """도구를 지우고 대장만 남으면 「누가 읽는다」 가 거짓이 된다."""
    assert catalog.feeds_fail("a", ["tools/없다.py"], tmp_path) == ["a: feeds 가 없는 tools/없다.py 를 든다"]
    assert catalog.feeds_fail("a", ["사람이 눈으로 본다"], tmp_path) == []


def test_실제_카탈로그의_미투입을_센다():
    """실패가 아니라 수다 — 아무도 안 읽는 출처가 몇인지 대장이 말한다."""
    got = catalog.unfed(catalog.load())
    assert "thoth-pairs" in got          # 넉 달째 아무도 안 읽는다
    assert "ontology-aws" not in got


def test_문은_선언_밖을_막는다():
    """데이터를 쓰기 전에 묻는다 — 파이어레인의 「대장에 없음 + 파일 있음 → 반입 정지」(DECISIONS §121)."""
    import pytest
    with pytest.raises(SystemExit, match="선언 밖에 쓰려고 한다"):
        catalog.gate(ROOT / "data/몰래/x.jsonl")
    # 밖은 이 문의 일이 아니다 — labels.py 는 채점표를 /tmp 에 쓰고 그것이 맞다
    assert catalog.gate(pathlib.Path("/etc/passwd")) is None


def test_문은_선언_안을_통과시킨다():
    assert catalog.gate(ROOT / "data/domain/d001.jsonl")["id"] == "awsdocs-domain"
    assert catalog.gate(ROOT / "data/probes/h001.jsonl")["id"] == "probes"
    assert catalog.gate(ROOT / "runs") is None          # 작업대는 출처가 없어도 된다
    assert catalog.gate(ROOT / "labels") is None


def test_쓰는_도구는_전부_문을_부른다():
    """문이 하나여도 부르지 않으면 없는 것과 같다 — 입구마다 부르는지 시험이 센다."""
    문 = ("tools/fetch_flores.py", "tools/fetch_awsdocs.py", "tools/make_probes.py",
          "tools/labels.py", "seshat/evaluate.py")
    for f in 문:
        src = (ROOT / f).read_text(encoding="utf-8")
        assert "catalog.gate(" in src, f"{f} 가 문을 안 부른다"


def test_등록된_파일이_사는_디렉터리는_등록된_자리다(tmp_path, monkeypatch):
    """`lake:cache/awsdocs/*` 가 대장에 있으면 그 디렉터리를 만드는 일도 허락된 일이다.

    2026-09-27 `fetch_awsdocs.py` 가 첫 줄에서 죽었다 — `catalog.gate(cache)` 가 디렉터리를
    물었는데 `fnmatch("cache/awsdocs", "cache/awsdocs/*")` 가 거짓이었다(DECISIONS §128).
    """
    lake = tmp_path / "lake"
    (lake / "cache").mkdir(parents=True)
    (lake / "MANIFEST.tsv").write_text("sha256\tpath\tbytes\tadded\torigin\n", encoding="utf-8")
    monkeypatch.setattr(paths, "data", lambda: lake)
    assert catalog.gate(lake / "cache/awsdocs")["id"] == "awsdocs-guides"
    assert catalog.gate(lake / "cache/awsdocs/amazon-athena-user-guide")["id"] == "awsdocs-guides"
    with pytest.raises(SystemExit, match="카탈로그 밖에"):
        catalog.gate(lake / "cache/몰래")


def test_홀드는_형제_디렉터리를_안_먹는다():
    e = [{"id": "x", "where": "lake:cache/awsdocs/*"}]
    assert catalog.holds(e, "lake", "cache/awsdocs")["id"] == "x"
    assert catalog.holds(e, "lake", "cache/awsdoc") is None      # 접두사만 같은 남의 자리
    assert catalog.holds(e, "repo", "cache/awsdocs") is None


def test_모든_출처의_디렉터리가_문을_지난다(tmp_path, monkeypatch):
    """**시험이 「문을 부르는가」 만 보고 「문을 지나는가」 를 안 봤다**(DECISIONS §128).

    도구는 파일을 쓰기 전에 디렉터리를 만든다. 대장의 모든 자리에 대해 그 디렉터리가 문을
    지나는지 여기서 한꺼번에 센다 — 한 출처를 더할 때마다 같은 사고가 나지 않게.
    """
    lake = tmp_path / "lake"
    lake.mkdir()
    (lake / "MANIFEST.tsv").write_text("sha256\tpath\tbytes\tadded\torigin\n", encoding="utf-8")
    monkeypatch.setattr(paths, "data", lambda: lake)
    막힌 = []
    for e in catalog.load():
        space, _, pat = e["where"].partition(":")
        # ★ 도구가 실제로 무엇을 묻는가 — **글로브면 그 디렉터리**를 만들고, 파일 하나면 **그 파일**을
        #   쓴다. 파일 하나짜리 출처에 부모 디렉터리를 물으면 묻지도 않는 것을 시험하는 것이다
        자리 = pathlib.PurePosixPath(pat).parent.as_posix() if "*" in pat else pat
        if 자리 in (".", ""):
            continue
        base = ROOT if space == "repo" else lake
        try:
            catalog.gate(base / 자리)
        except SystemExit as x:
            막힌.append(f'{e["id"]} → {space}:{자리} — {str(x).splitlines()[0]}')
    assert 막힌 == []


def _가짜_proc(tmp_path, pid: str, comm: str, env: dict[str, str] | None):
    d = tmp_path / pid
    d.mkdir(parents=True)
    (d / "comm").write_text(comm + "\n", encoding="utf-8")
    if env is not None:
        (d / "environ").write_bytes(("\0".join(f"{k}={v}" for k, v in env.items()) + "\0").encode())
    return tmp_path


def test_가중치_자리는_서버에게_묻는다(tmp_path, monkeypatch):
    """셸의 값은 서버의 값이 아니다 — systemd 로 뜨면 셸 export 는 안 닿는다(DECISIONS §138)."""
    proc = _가짜_proc(tmp_path, "4242", "ollama", {"OLLAMA_MODELS": "/서버가/아는/자리", "HOME": "/h"})
    monkeypatch.setattr(catalog, "Path", lambda p="/": pathlib.Path(proc) if str(p) == "/proc" else pathlib.Path(p))
    monkeypatch.setenv("OLLAMA_MODELS", "/셸이/아는/자리")
    자리, 어디서 = catalog.ollama_models_dir()
    assert 자리 == "/서버가/아는/자리" and "서버" in 어디서 and "4242" in 어디서


def test_서버가_안_정했으면_그렇다고_한다(tmp_path, monkeypatch):
    """서버가 기본 자리(`~/.ollama/models`)를 쓴다는 뜻이다 — 셸 값으로 덮어 읽지 않는다."""
    proc = _가짜_proc(tmp_path, "7", "ollama", {"HOME": "/h"})
    monkeypatch.setattr(catalog, "Path", lambda p="/": pathlib.Path(proc) if str(p) == "/proc" else pathlib.Path(p))
    monkeypatch.setenv("OLLAMA_MODELS", "/셸이/아는/자리")
    자리, 어디서 = catalog.ollama_models_dir()
    assert 자리 == "" and "안 정했다" in 어디서


def test_못_물으면_셸_값을_쓰되_그렇다고_적는다(tmp_path, monkeypatch):
    """「못 물었다」 와 「서버가 그렇다고 했다」 를 같은 문장으로 내지 않는다(§110)."""
    proc = _가짜_proc(tmp_path, "9", "다른프로그램", {"OLLAMA_MODELS": "/남의것"})
    monkeypatch.setattr(catalog, "Path", lambda p="/": pathlib.Path(proc) if str(p) == "/proc" else pathlib.Path(p))
    monkeypatch.setenv("OLLAMA_MODELS", "/셸이/아는/자리")
    자리, 어디서 = catalog.ollama_models_dir()
    assert 자리 == "/셸이/아는/자리" and "못 물었다" in 어디서


def test_가중치_검사가_기계를_안_읽는다():
    """**시험이 그 기계의 진짜 ollama 를 읽으면 시험이 아니다**(DECISIONS §138).

    2026-09-28 에 `weights_outside` 가 서버에게 묻게 만들었더니, `monkeypatch.setenv` 가 안 먹고
    시험이 실제 가중치를 셌다 — ollama 가 없는 컨테이너에서는 통과하고 있는 기계에서는 터졌다.
    **자리를 인자로 받는다.** 이 시험은 `where` 없이 부르는 곳이 시험에 없는지 센다.
    """
    src = (ROOT / "tests/test_catalog.py").read_text(encoding="utf-8")
    맨몸 = [ln.strip() for ln in src.splitlines()
            if "weights_outside(" in ln and "where=" not in ln and "def " not in ln and "맨몸" not in ln]
    assert 맨몸 == [], f"시험이 기계를 읽는다 — where= 로 자리를 준다: {맨몸}"
