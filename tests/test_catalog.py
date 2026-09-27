"""카탈로그 — 칸 · 쓰임 · 미확인 라이선스는 학습 불가 · data/ 의 카탈로그 밖 파일(DECISIONS §22)."""
import pathlib

from seshat import catalog

ROOT = pathlib.Path(__file__).resolve().parent.parent

OK = {"id": "a", "where": "lake:raw/a/*", "origin": "o", "license": "CC BY 4.0", "uses": ["eval"], "how": "사람"}


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

    monkeypatch.setenv("OLLAMA_MODELS", str(outside))
    got = catalog.weights_outside(entries)
    assert got and "카탈로그는 lake:cache/models/*" in got[0] and str(outside) in got[0]

    inside = lake / "cache/models/ollama"; inside.mkdir(parents=True)
    (inside / "blob").write_text("가중치인 척", encoding="utf-8")
    monkeypatch.setenv("OLLAMA_MODELS", str(inside))
    assert catalog.weights_outside(entries) == []

    # 빈 자리는 짚지 않는다 — 아직 아무것도 안 받은 기계다
    empty = tmp_path / "empty"; empty.mkdir()
    monkeypatch.setenv("OLLAMA_MODELS", str(empty))
    assert catalog.weights_outside(entries) == []

    # 레이크가 없는 기계(CI)에서는 묻지 않는다
    monkeypatch.setenv("OLLAMA_MODELS", str(outside))
    monkeypatch.setenv("SESHAT_DATA", "")
    assert catalog.weights_outside(entries) == []


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
    monkeypatch.setenv("OLLAMA_MODELS", str(inside))
    got = catalog.weights_outside(catalog.load())
    assert len(got) == 1 and str(default) in got[0]
    assert "셸이 OLLAMA_MODELS 를 모른다" in got[0]

    # 기본 자리를 치우면 조용해진다
    (default / "blob").unlink()
    assert catalog.weights_outside(catalog.load()) == []


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
