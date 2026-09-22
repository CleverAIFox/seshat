"""카탈로그 — 칸 · 쓰임 · 미확인 라이선스는 학습 불가 · data/ 의 카탈로그 밖 파일(DECISIONS §22)."""
from seshat import catalog

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
