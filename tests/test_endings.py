"""종결 정규화 — 관측한 모양만 바꾼다(DECISIONS §31)."""
from seshat import endings, evaluate

BROKEN = "어떤 솔루션이 AWS Lambda를 사용하여 가장 적은 운영 오버헤드로 이러한 요구 사항을 충족할까요?"


def test_H_019_에서_깨진_모양을_고친다():
    fixed = endings.normalize(BROKEN)
    assert fixed.endswith("충족합니까?")
    assert not evaluate.is_hapsyo(BROKEN) and evaluate.is_hapsyo(fixed)


def test_받침이_맞을_때만_바꾼다():
    assert endings.normalize("무엇인가요?") == "무엇입니까?"        # ㄴ + 가요
    assert endings.normalize("괜찮나요?") == "괜찮나요?"            # 받침이 다르다 — 두고 본다
    assert endings.normalize("뭐할까요") == "뭐할까요"              # 물음표가 없으면 문장 끝이 아니다


def test_이미_합쇼체인_문장은_건드리지_않는다():
    for s in ["Amazon S3를 씁니다.", "이것은 무엇입니까?", "설정을 확인하십시오."]:
        assert endings.normalize(s) == s
