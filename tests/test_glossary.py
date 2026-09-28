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


def test_울타리가_경계를_긋는다():
    """목록만 주면 **행동이 번진다** — 사전에 없는 식별자까지 옮긴다(DECISIONS §140)."""
    토막 = glossary.block([("quota", "할당량")], fence=True)
    assert 토막.endswith(glossary.FENCE) and "- quota → 할당량" in 토막
    # 「부분이 영어 낱말처럼 보여도」 가 이 줄의 핵심이다 — 옮겨진 것은 `DocumentBatchWrite` 였다
    assert "look like English words" in glossary.FENCE


def test_울타리만_남기지_않는다():
    """사전이 빈 줄에 경고만 주면 그것은 사전 처치가 아니라 딴 처치다."""
    assert glossary.block([], fence=True) == ""


def test_잰_팔의_뜻을_뒤에서_안_바꾼다():
    """`runs/H-056-gloss-*` 가 이 함수의 기본값으로 잰 판이다 — 기본이 바뀌면 그 판이 거짓이 된다."""
    assert glossary.block([("quota", "할당량")]) == glossary.block([("quota", "할당량")], fence=False)
    assert glossary.FENCE not in glossary.block([("quota", "할당량")])


def test_울타리_팔이_등록되고_배선이_같다():
    """달라진 것이 **사전 토막 끝의 한 줄**이어야 그것이 원인인지 가른다(DECISIONS §134)."""
    arm = "gemma3-4b+ph+gloss2+endings"
    assert arm in backends.REGISTRY
    assert backends.OLLAMA_OF[arm] == backends.OLLAMA_OF["gemma3-4b+ph+gloss+endings"]
    assert backends.WEIGHTS[arm] == backends.WEIGHTS["gemma3-4b+ph+gloss+endings"]
    assert backends.DECODING_OF[arm] == backends.DECODING_OF["gemma3-4b+ph+gloss+endings"]


def test_d001_사례를_프롬프트에_안_적는다():
    """실제 셋에서 본 식별자를 예시로 적으면 고침이 아니라 **시험 셋에 맞춘 프롬프트**다(§130)."""
    for 본것 in ("CreateTable", "SCHEDULED", "DocumentBatchWrite", "processing-failed", "DynamicFrames"):
        assert 본것 not in glossary.FENCE


def test_서빙_배선_팔이_기록판_팔과_하나만_다르다():
    """승격을 노리는 팔은 **기록판 팔과 `gloss2` 하나만** 달라야 한다(DECISIONS §134 · §142).

    `+retry` 가 빠져 있어서 `keep` 이 0.0042 모자랐다 — 그것은 사전의 죄가 아니라 배선의 죄다.
    """
    새, 옛 = "gemma3-4b+ph+gloss2+retry+endings+terms", "gemma3-4b+ph+retry+endings+terms"
    assert 새 in backends.REGISTRY
    assert backends.OLLAMA_OF[새] == backends.OLLAMA_OF[옛]
    assert backends.WEIGHTS[새] == backends.WEIGHTS[옛]
    assert backends.DECODING_OF[새] == backends.DECODING_OF[옛], "복호화까지 같아야 사전만 남는다"
    assert 새 in backends.REPAIR_ARMS, "고치는 판을 쓰면 그 조건도 머리줄에 실려야 한다(§57)"
    # 이름이 곧 배선이다 — 기록판 팔 이름에 `gloss2` 를 끼운 것이어야 한다
    assert 새 == 옛.replace("+ph+", "+ph+gloss2+")


def test_콘솔_라벨_갈래는_울타리_위에만_선다():
    """울타리 없이 갈래만 더하면 그것은 딴 처치다 — 하나만 달라야 무엇이 효과인지 가른다(§134)."""
    assert glossary.FENCE_UI not in glossary.block([("quota", "할당량")], ui=True)
    토막 = glossary.block([("quota", "할당량")], fence=True, ui=True)
    assert glossary.FENCE in 토막 and glossary.FENCE_UI in 토막


def test_울타리_팔의_뜻을_뒤에서_안_바꾼다():
    """`runs/H-057-gloss2-*` 가 `ui` 없는 울타리로 잰 판이다."""
    assert glossary.FENCE_UI not in glossary.block([("quota", "할당량")], fence=True)


def test_콘솔_갈래도_d001_사례를_안_적는다():
    for 본것 in ("Security Groups", "Type", "유형", "Create bucket"):
        assert 본것 not in glossary.FENCE_UI


def test_콘솔_팔이_울타리_팔과_하나만_다르다():
    새, 옛 = "gemma3-4b+ph+gloss3+endings", "gemma3-4b+ph+gloss2+endings"
    assert 새 in backends.REGISTRY
    assert backends.OLLAMA_OF[새] == backends.OLLAMA_OF[옛]
    assert backends.WEIGHTS[새] == backends.WEIGHTS[옛]
    assert backends.DECODING_OF[새] == backends.DECODING_OF[옛]
