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


@pytest.mark.parametrize("form", ["⟦T1⟧", "[T1]", "\\[T1]", "\\[T1\\]", "【T1】", "`T1`", "T1"])
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


def test_백틱으로_싼_자리표시를_되돌린다():
    """H-001 처치군이 마지막으로 잃은 줄이다 — 모델이 `⟦T1⟧` 을 마크다운 코드로 바꿨다(DECISIONS §24)."""
    slots = {"T1": {"text": "AWS CloudFormation", "coda": "none", "id": "svc.cfn"},
             "T2": {"text": "Amazon Simple Storage Service", "coda": "none", "id": "svc.s3"}}
    ko, missing = terms.unmask("`T1`에서 크로스 계정 데이터를 가져와 `T2`에 저장합니다.", slots)
    assert ko == "AWS CloudFormation에서 크로스 계정 데이터를 가져와 Amazon Simple Storage Service에 저장합니다."
    assert missing == []


def test_허용_표기와_오역_표기는_겹치지_않는다():
    """같은 표기가 허용이면서 오역이면 `term` 이 같은 줄을 맞다고도 틀리다고도 센다(DECISIONS §25)."""
    node = {"id": "con.a", "kind": "concept", "en": "a", "keep": False, "ko": "가", "src": "author",
            "ko_ref": "s3/UsingBucket"}
    assert ontology.validate([{**node, "alt_ko": ["나"], "bad_ko": ["나"]}])
    assert ontology.validate([{**node, "alt_ko": ["가"]}])                     # ko 를 다시 적지 않는다
    assert ontology.validate([{**node, "alt_ko": "나"}])                       # 목록이다
    assert ontology.validate([{"id": "svc.a", "kind": "service", "en": "A", "keep": True, "coda": "none",
                               "src": "author", "alt_ko": ["에이"]}])          # 영어로 남는 노드는 한국어 표기를 안 든다
    assert ontology.validate([{**node, "alt_ko": ["나"], "bad_ko": ["다"]}]) == []


def test_공식_표기의_근거는_문서_자리다():
    """URL 은 깨진다. 서비스와 페이지 이름이면 다시 찾는다(DECISIONS §34)."""
    node = {"id": "con.a", "kind": "concept", "en": "a", "keep": False, "ko": "가", "src": "author"}
    assert ontology.validate([{**node, "ko_ref": "sqs/sqs-visibility-timeout"}]) == []
    assert ontology.validate([{**node, "ko_ref": "https://docs.aws.amazon.com/ko_kr/x.html"}])
    assert ontology.validate([{**node, "ko_ref": ""}])


def test_대조한_개념이_실제로_있다():
    """카나리아 — 2판이 대조한 개념이 하나도 없으면 검사가 죽은 것이다."""
    onto = ontology.load()
    refs = [n for n in onto if n.get("ko_ref")]
    assert len(refs) >= 60          # 2판에서 60/60 을 채웠다(DECISIONS §65) — 줄어들면 누가 지운 것이다
    assert all(n["kind"] == "concept" and not n["keep"] for n in refs)


def test_괄호가_벗겨진_맨_자리표시와_붙은_조사를_되돌린다():
    """AWS Translate 는 `⟦T1⟧` 을 `T1` 로 돌려주고 조사까지 붙인다(DECISIONS §42)."""
    slots = {"T1": {"text": "KCL", "coda": "rieul", "id": "feat.kcl"}}
    assert terms.unmask("T1는 자동으로 크기가 조절됩니다.", slots)[0] == "KCL은 자동으로 크기가 조절됩니다."
    slots2 = {"T1": {"text": "AWS Transfer Family", "coda": "none", "id": "svc.tf"}}
    assert terms.unmask("팀은 T1를 사용합니다.", slots2)[0] == "팀은 AWS Transfer Family를 사용합니다."


def test_맨_자리표시는_낱말_속을_건드리지_않는다():
    """`MT1` · `T10` 은 자리표시가 아니다 — 맨 모양을 받는 값으로 오검출을 사지 않는다."""
    slots = {"T1": {"text": "KCL", "coda": "rieul", "id": "feat.kcl"}}
    for keep in ("MT1 은 다르다.", "T10 은 다르다.", "xT1y"):
        assert terms.unmask(keep, slots)[0] == keep


# ── 사전으로 표기를 바로잡는다(DECISIONS §56)
def _node(ko, bad, alt=None):
    return {"id": "con.t", "kind": "concept", "en": "t", "keep": False, "ko": ko,
            "aliases": [], "parent": None, "src": "author", "bad_ko": bad, "alt_ko": alt or []}


def test_관측된_오역을_공식_표기로_바꾼다():
    onto = [_node("글로벌 보조 인덱스", ["글로벌 이차 인덱스"])]
    got, hits = terms.fix_terms(onto, "분석가에게 글로벌 이차 인덱스의 뷰를 제공합니다.")
    assert got == "분석가에게 글로벌 보조 인덱스의 뷰를 제공합니다."
    assert hits == ["글로벌 이차 인덱스 → 글로벌 보조 인덱스"]


def test_끝소리가_바뀌면_조사도_바뀐다():
    """`대기열` 은 ㄹ 받침이고 `큐` 는 받침이 없다 — 조사를 안 고치면 `큐을` 이 된다."""
    onto = [_node("대기열", ["큐"])]
    assert terms.fix_terms(onto, "큐를 만듭니다.")[0] == "대기열을 만듭니다."
    onto = [_node("큐", ["대기열"])]
    assert terms.fix_terms(onto, "대기열을 만듭니다.")[0] == "큐를 만듭니다."


def test_긴_오역부터_바꾼다():
    """짧은 것이 먼저 먹으면 `글로벌` 이 남는다."""
    onto = [_node("글로벌 보조 인덱스", ["이차 인덱스", "글로벌 이차 인덱스"])]
    assert terms.fix_terms(onto, "글로벌 이차 인덱스입니다.")[0] == "글로벌 보조 인덱스입니다."


def test_맞는_표기는_건드리지_않는다():
    onto = [_node("저장 시 암호화", ["휴지 암호화"])]
    ko = "저장 시 암호화가 필요합니다."
    assert terms.fix_terms(onto, ko) == (ko, [])


def test_영어로_남는_이름은_사전이_안_건드린다():
    """`keep` 노드는 자리표시가 지킨다 — 여기서 또 만지면 두 규칙이 싸운다."""
    onto = [{"id": "svc.s3", "kind": "service", "en": "Amazon S3", "keep": True, "coda": "none",
             "aliases": [], "parent": None, "src": "author", "bad_ko": ["아마존 에스쓰리"]}]
    ko = "아마존 에스쓰리에 저장합니다."
    assert terms.fix_terms(onto, ko) == (ko, [])


def test_한글로_안_끝나는_표기는_끝소리를_모른다():
    assert terms.ko_coda("Amazon S3") is None
    assert terms.ko_coda("대기열") == "rieul"
    assert terms.ko_coda("큐") == "none"
    assert terms.ko_coda("인덱스") == "none"
    assert terms.ko_coda("검색") == "closed"


def test_번역_대상_개념은_근거를_든다():
    """근거 없는 표기는 표기가 아니다 — 1판 60 개 중 셋이 「자연스러워서」 틀렸다(DECISIONS §65)."""
    onto = ontology.load()
    없음 = [n["id"] for n in onto if not n["keep"] and not n.get("ko_ref")]
    assert 없음 == [], f"근거 없는 개념 {없음}"
    assert ontology.validate([_node("대기열", [])]) != []     # 새로 들어오는 개념도 같은 문을 지난다


def test_후처리는_원문에_있는_개념만_고친다():
    """`제한` 은 throttling 의 오역이면서 limit 의 바른 번역이다 — 원문이 가른다(DECISIONS §67)."""
    onto = [_node("스로틀링", ["제한"])]
    onto[0]["en"] = "throttling"
    ko = "요청 수를 제한하려면 할당량을 늘리십시오."
    assert terms.fix_terms(onto, ko, src="To limit the number of requests …")[0] == ko      # 안 건드린다
    assert terms.fix_terms(onto, ko, src="throttling happens here")[0] != ko                # 원문에 있으면 고친다
    assert terms.fix_terms(onto, ko)[0] != ko            # 원문을 모르면 전부 본다 — 도구용 옛 길


def test_후처리가_고치는_개념과_지표가_세는_개념이_같다():
    """처치가 지표 밖의 개념을 건드리면, 점수는 안 오르고 문장만 바뀐다(DECISIONS §67)."""
    onto = ontology.load()
    src = "The team uses the data lake and the queue for ingestion."
    보는것 = {s.node["id"] for _, _, s in ontology.find(onto, src) if not s.node["keep"]}
    _, hits = terms.fix_terms(onto, "데이터 레이크와 큐를 수집에 씁니다.", src=src)
    assert hits and 보는것                                # 카나리아 — 둘 다 비면 시험이 죽은 것이다
    고친것 = {h.split(" → ")[1] for h in hits}
    assert 고친것 <= {n["ko"] for n in onto if n["id"] in 보는것}


def test_개념이_동사로_나타나도_찾는다():
    """`ingestion` 은 찾고 `ingested` 는 못 찾으면, 지표의 분모가 실제보다 작다(DECISIONS §69)."""
    onto = ontology.load()
    def concepts(src):
        return {s.node["en"] for _, _, s in ontology.find(onto, src) if not s.node["keep"]}
    assert "ingestion" in concepts("The catalog is ingested by Kinesis.")
    assert "throttling" in concepts("If the service throttles the requests, increase the quota.")
    assert "encryption" in concepts("The role must be encrypted.")
    assert "compression" in concepts("The data is compressed before upload.")


def test_섭취는_수집으로_돌아온다():
    """`섭취` 는 밥을 먹는다는 뜻이다 — H-036 에서 잃었던 고침이다(DECISIONS §68 · §69)."""
    onto = ontology.load()
    got, hits = terms.fix_terms(onto, "카탈로그는 Kinesis에 의해 섭취되고 저장됩니다.",
                                src="The catalog is ingested by Kinesis and stored in Athena.")
    assert "수집" in got and "섭취" not in got and hits


def test_흔한_말은_그_개념을_말하는_줄에서만_바뀐다():
    """`제어` 는 throttling 의 오역이자 control 의 바른 번역이다 — 문맥 문이 지킨다(DECISIONS §67 · §86)."""
    onto = ontology.load()
    ko = "권한을 제어하는 정책입니다."
    assert terms.fix_terms(onto, ko, src="A policy that controls permissions.")[0] == ko
    고침, hits = terms.fix_terms(onto, "요청을 제어하면 늘려야 합니다.",
                                 src="If the service throttles the requests, increase it.")
    assert "스로틀링" in 고침 and hits


def test_제품_이름이_개념으로_쪼개지지_않는다():
    """`X Serverless` 는 제품이다. 뒷말이 개념이라고 갈라지면 지표가 **제품 이름을 번역하라고 요구한다**
    (DECISIONS §94). `Amazon OpenSearch Serverless` 를 「OpenSearch 서버리스」 로 쓴 쪽에 점수를 줬다."""
    onto = ontology.load()
    for text, want in (("OpenSearch Serverless", "feat.opensearch-serverless"),
                       ("Amazon EMR Serverless", "feat.emr-serverless"),
                       ("Aurora Serverless v2", "feat.aurora-serverless"),
                       ("Amazon Redshift Serverless", "feat.redshift-serverless")):
        hits = ontology.find(onto, f"Use {text} for this workload.")
        assert [s.node["id"] for _, _, s in hits] == [want], text
        assert all(s.node["keep"] for _, _, s in hits), text
    # 홀로 선 serverless 는 여전히 개념이다
    hits = ontology.find(onto, "The pipeline is serverless.")
    assert [s.node["id"] for _, _, s in hits] == ["con.serverless"]


def test_식별자는_사전에_못_들어온다():
    """`bucket-owner-full-control` 을 노드로 올리면 사전이 API 참조가 되고도 여전히 모자란다.
    **원문이 `` ` `` 로 이미 표시한다** — 자는 `lit` 이다(DECISIONS §122)."""
    바른 = {"id": "con.x", "kind": "concept", "en": "throughput", "keep": False, "ko": "처리량",
            "ko_ref": "streams/key-concepts", "src": "author"}
    assert ontology.validate([바른]) == []
    for 나쁜 in ("bucket-owner-full-control", "search_path", "KEYS_ONLY", "tasks.max"):
        fails = ontology.validate([{**바른, "aliases": [나쁜]}])
        assert any("식별자 모양이다" in f for f in fails), 나쁜


def test_평범한_붙임표_영어는_식별자가_아니다():
    """`server-side` · `cross-account` 는 산문이다 — 두 마디짜리를 막으면 사전이 못 자란다."""
    바른 = {"id": "con.x", "kind": "concept", "en": "throughput", "keep": False, "ko": "처리량",
            "ko_ref": "streams/key-concepts", "src": "author"}
    for 괜찮은 in ("server-side", "cross-account", "fan-out"):
        assert not any("식별자" in f for f in ontology.validate([{**바른, "aliases": [괜찮은]}])), 괜찮은


def test_지금_사전에_식별자가_없다():
    assert not [f for f in ontology.validate(ontology.load()) if "식별자" in f]


def test_규칙_복수를_전부_받는다():
    """`s` 를 짐작하면서 `ies` 를 안 짐작하는 것은 규율이 아니라 빠뜨린 것이다(DECISIONS §160).

    2026-09-28 까지 `policies` 가 d001 16줄에서 **한 번도 안 세어졌다.**
    """
    onto = ontology.load()

    def 잡히나(글):
        return [x.node["id"] for _, _, x in ontology.find(onto, 글)]

    assert 잡히나("Attach the policy.") == 잡히나("Attach the policies.") != []
    assert 잡히나("One bucket.") == 잡히나("Two buckets.") != []


def test_이름은_복수로_안_받는다():
    """`Amazon S3s` 는 없는 말이다 — 이름에 복수를 붙이면 엉뚱한 자리를 집는다."""
    onto = ontology.load()
    assert [x.node["id"] for _, _, x in ontology.find(onto, "Amazon S3s")] == []


def test_모음_뒤_y_는_그대로다():
    """`key` → `keies` 가 아니라 `keys` 다 — 모음 뒤 y 에 ies 를 붙이면 안 된다."""
    import re
    for 글 in ("key", "day", "array"):
        assert not re.search(r"[^aeiouAEIOU]y$", 글), f"{글} 은 자음+y 가 아니다"
    assert re.search(r"[^aeiouAEIOU]y$", "policy")
