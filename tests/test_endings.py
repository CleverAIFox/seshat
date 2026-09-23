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


# ── 평서 · 명령 종결(DECISIONS §54) — H-032 에서 깨진 3줄이 여기 그대로 있다
def test_해라체_평서를_합쇼체로():
    assert endings.normalize("역할은 암호화되어야 한다.") == "역할은 암호화되어야 합니다."
    assert endings.normalize("팀은 트리거를 늘려야 한다.") == "팀은 트리거를 늘려야 합니다."
    assert endings.normalize("작업은 자동으로 확장된다.") == "작업은 자동으로 확장됩니다."
    assert endings.normalize("팀은 로그를 읽는다.") == "팀은 로그를 읽습니다."
    assert endings.normalize("이것은 데이터 레이크이다.") == "이것은 데이터 레이크입니다."


def test_해요체_명령을_합쇼체로():
    assert endings.normalize("Athena를 구성하고, Redshift에 연결하세요.") == \
        "Athena를 구성하고, Redshift에 연결하십시오."


def test_문장_끝이_아닌_다는_건드리지_않는다():
    """`한다는 것` · `간다고` 를 깨뜨리면 맞는 문장을 틀리게 만든다(DECISIONS §31)."""
    assert endings.normalize("한다는 것은 쉽지 않습니다.") == "한다는 것은 쉽지 않습니다."
    assert endings.normalize("그는 간다고 말했습니다.") == "그는 간다고 말했습니다."


def test_종성이_ㄴ_이_아닌_다는_그대로_둔다():
    """`기다` · `보다` 같은 말을 `깁니다` 로 만들면 안 된다 — 자모가 안 맞으면 멈춘다."""
    assert endings.normalize("그 답은 기다.") == "그 답은 기다."
    assert endings.normalize("이 방식이 저 방식보다.") == "이 방식이 저 방식보다."
