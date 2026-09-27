"""참조 번역 — 그 줄의 용어만 싣는다(DECISIONS §134 · #16).

★ 모델을 안 부른다. **무엇을 싣는가**만 본다 — 그것이 이 처치의 전부다.
"""
from seshat import backends, glossary, ontology, terms

ONTO = ontology.load()


def test_그_줄에_나온_것만_싣는다():
    """사전 137 줄을 통째로 싣는 것은 RAG 가 아니라 그냥 긴 프롬프트다."""
    got = dict(glossary.for_line(ONTO, "Increase the quota for the stream."))
    assert got == {"quota": "할당량", "stream": "스트림"}


def test_공식_표기만_싣는다():
    """`alt_ko` 를 같이 실으면 모델이 고를 여지가 생기고 term_off 가 안 오른다."""
    노드 = next(n for n in ONTO if n["id"] == "con.quota")
    assert 노드["alt_ko"], "이 시험은 허용 표기가 있는 노드를 쓴다"
    실린 = dict(glossary.for_line(ONTO, "Raise the quota."))["quota"]
    assert 실린 == 노드["ko"] and 실린 not in 노드["alt_ko"]


def test_관측된_오역은_안_싣는다():
    """「쿼리 한도 라고 쓰지 마라」 는 그 말을 프롬프트에 넣는 것이고 모델은 프롬프트의 말을 쓴다."""
    토막 = glossary.block(glossary.for_line(ONTO, "Raise the quota for this table."))
    노드 = next(n for n in ONTO if n["id"] == "con.quota")
    assert all(bad not in 토막 for bad in 노드.get("bad_ko", []))


def test_영어로_남는_것은_그대로라고_적는다():
    got = dict(glossary.for_line(ONTO, "Use Amazon S3 for this workload."))
    assert got.get("Amazon S3") == glossary.KEEP


def test_자리표시가_뺀_이름은_안_걸린다():
    """자리표시와 용어집이 서로 다른 자리를 맡는다 — 같은 것을 두 번 말하지 않는다."""
    src = "Write the record to Amazon Kinesis Data Streams now."
    masked, _ = terms.mask(ONTO, src)
    assert "⟦T1⟧" in masked
    got = dict(glossary.for_line(ONTO, masked))
    assert "record" in got and not any("Kinesis" in k for k in got)


def test_겹치면_한_번만():
    got = glossary.for_line(ONTO, "The snapshot of the snapshot repository is a snapshot.")
    assert [en for en, _ in got].count("snapshot") == 1


def test_상한을_넘으면_앞에서_자른다():
    """긴 사전은 안 읽힌다."""
    긴 = "The quota, stream, snapshot, cluster, node, bucket, object, queue, topic, schema, policy, role, endpoint."
    assert len(glossary.for_line(ONTO, 긴, cap=3)) == 3


def test_사전이_비면_빈_글자다():
    """빈 사전을 실으면 모델이 없는 것을 찾는다."""
    assert glossary.block([]) == ""
    assert glossary.block(glossary.for_line(ONTO, "The quick brown fox jumped over it.")) == ""


def test_토막이_지시문처럼_읽힌다():
    토막 = glossary.block([("quota", "할당량")])
    assert 토막.startswith(glossary.HEAD) and "- quota → 할당량" in 토막


def test_팔이_등록되고_배선이_같다():
    """달라진 것이 체계 지시 하나여야 무엇이 효과인지 가른다."""
    for arm in ("gemma3-4b+ph+gloss+endings", "gemma3-4b+ph+gloss+endings+terms"):
        assert arm in backends.REGISTRY
        assert backends.OLLAMA_OF[arm] == "gemma3:4b"
        assert backends.WEIGHTS[arm] == "google/gemma-3-4b-it"
        assert backends.DECODING_OF[arm]["temperature"] == 0     # 고르기가 아니라 지시가 바뀐 팔이다


def test_후처리_있는_팔과_없는_팔이_둘_다_있다():
    """사전을 미리 주면 후처리가 필요 없어지는가 — 그것이 이 판의 물음이다."""
    assert "gemma3-4b+ph+gloss+endings" in backends.REGISTRY
    assert "gemma3-4b+ph+gloss+endings+terms" in backends.REGISTRY
