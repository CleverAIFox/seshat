"""온톨로지와 용어 자리표시(DECISIONS §13 · H-001)."""
import pytest

from seshat import ontology, terms

ONTO = ontology.load()


def test_실제_온톨로지가_규칙을_지킨다():
    assert ontology.validate(ONTO) == []


def test_thoth_용어집이_씨앗으로_다_들어_있다():
    # ★ thoth 용어집 37항목 — 개념 35 는 con.*, 고유명 둘은 feature 로
    have = {s.text.lower() for s in ontology.surfaces(ONTO)}
    for en in ["record", "shard", "partition key", "consumer application", "throttling", "data catalog", "dynamodb streams"]:
        assert en in have


def _n(i, **kw):
    base = {"id": i, "kind": "service", "en": i, "keep": True, "coda": "none", "aliases": [], "src": "author"}
    return {**base, **kw}


@pytest.mark.parametrize("onto,want", [
    ([_n("svc.a", aliases=["X"]), _n("svc.b", aliases=["x"])], "둘을 가리킨다"),
    ([_n("svc.a", parent="svc.z")], "부모 svc.z 가 없다"),
    ([_n("svc.a", coda=None)], "끝소리가 없다"),
    ([_n("con.a", kind="concept", keep=False, ko="shard")], "한글이 없다"),
    ([_n("svc.a", kind="concept")], "접두사"),
    ([_n("svc.a", src="웹")], "출처"),
    ([_n("svc.a", parent="svc.b"), _n("svc.b", parent="svc.a")], "사슬이 돈다"),
])
def test_규칙마다_걸린다(onto, want):
    assert any(want in f for f in ontology.validate(onto)), ontology.validate(onto)


def test_긴_표기가_이긴다():
    got = [s.node["id"] for _, _, s in ontology.find(ONTO, "Use Amazon Kinesis Data Streams, not Kinesis Data Firehose.")]
    assert got == ["svc.kinesis-data-streams", "svc.data-firehose"]


def test_약어는_대소문자를_지킨다():
    # ★ 'iam' 이라는 낱말은 없지만 'dms' 같은 소문자 조각이 영어 본문에 끼면 오탐이다
    assert ontology.find(ONTO, "The dms folder.", keep_only=True) == []
    assert [s.node["id"] for _, _, s in ontology.find(ONTO, "Use DMS.", keep_only=True)] == ["svc.dms"]


def test_개념은_복수를_받는다():
    got = {s.node["id"] for _, _, s in ontology.find(ONTO, "Add shards and partition keys.")}
    assert {"con.shard", "con.partition-key"} <= got


@pytest.mark.parametrize("alias,want", [("KPL", "rieul"), ("IAM", "closed"), ("S3", "none"), ("EC2", "none"), ("EMR", "rieul")])
def test_약어의_끝소리는_글자_읽기다(alias, want):
    s = next(x for x in ontology.surfaces(ONTO) if x.text == alias)
    assert s.coda == want


def test_자리표시가_돌아온다():
    text = "Load records into Amazon S3 with AWS Glue and IAM."
    masked, slots = terms.mask(ONTO, text)
    assert masked == "Load records into ⟦T1⟧ with ⟦T2⟧ and ⟦T3⟧."
    ko, missing = terms.unmask("⟦T2⟧과 ⟦T3⟧를 사용해 레코드를 ⟦T1⟧에 적재합니다.", slots)
    assert ko == "AWS Glue와 IAM을 사용해 레코드를 Amazon S3에 적재합니다."
    assert missing == []


@pytest.mark.parametrize("coda,got,want", [
    ("none", "을", "를"), ("closed", "를", "을"), ("rieul", "가", "이"),
    ("none", "으로", "로"), ("rieul", "으로", "로"), ("closed", "로", "으로"), ("closed", "와", "과"),
])
def test_조사를_끝소리로_고른다(coda, got, want):
    assert terms.particle(coda, got) == want


def test_서술격은_건드리지_않는다():
    ko, _ = terms.unmask("정답은 ⟦T1⟧이다.", {"T1": {"text": "Amazon S3", "coda": "none", "id": "svc.s3"}})
    assert ko == "정답은 Amazon S3이다."


def test_사라진_자리표시를_센다():
    # ★ 모델이 이름을 빠뜨리면 그 번역은 이름을 잃었다 — H-001 의 판정 축
    _, slots = terms.mask(ONTO, "Use Amazon S3 and Amazon Athena.")
    _, missing = terms.unmask("⟦T1⟧를 씁니다.", slots)
    assert missing == ["T2"]


@pytest.mark.parametrize("form", ["⟦T1⟧", "[T1]", "\\[T1]", "\\[T1\\]", "【T1】"])
def test_모델이_바꾼_자리표시도_되돌린다(form):
    # ★ H-001 의 관계절에서 `⟦T1⟧` 이 `\[T1]` 로 돌아왔다(DECISIONS §16)
    slots = {"T1": {"text": "Amazon S3", "coda": "none", "id": "svc.s3"}}
    ko, missing = terms.unmask(f"{form}을 씁니다.", slots)
    assert ko == "Amazon S3를 씁니다." and missing == []


def test_대조_도구와_되돌리기가_같은_모양을_본다():
    import importlib.util
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("cr", root / "tools/compare_runs.py")
    cr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cr)
    assert cr.RESIDUE.pattern == terms.RESIDUE.pattern
