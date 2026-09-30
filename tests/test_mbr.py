"""MBR — 정답 없이 후보에서 고른다(DECISIONS §133).

★ 모델을 안 부른다. 고르는 규칙만 본다 — 후보를 손으로 준다.
"""
# ★ **건너뛰지 않는다**(DECISIONS §258). 관문은 `uv sync --group eval` 을 늘 하므로
#   여기서 건너뛰면 그룹이 빠진 날 **이 파일 전체가 조용히 0 건**이 된다 — 없으면 시끄럽게 죽는다
import pytest
import sacrebleu  # noqa: F401

from seshat import backends, mbr


def setup_function():
    mbr.reset()


def test_다수와_닮은_것을_고른다():
    """여덟 중 다섯이 제대로 옮겼으면 그 다섯이 서로 닮는다 — 그것이 MBR 이 찾는 것이다."""
    좋 = "정책의 스냅샷 섹션에서 리포지토리 이름을 바꿉니다."
    나쁨 = "휴대폰에서 암호화를 캡샷합니다."
    assert mbr.pick([나쁨, 좋, 좋, 좋]) == 좋


def test_첫째가_아니어도_고른다():
    """첫 후보를 그냥 돌려주면 이 도구는 아무 일도 안 하는 것이다."""
    좋 = "클러스터를 삭제하기 전에 스냅샷을 만듭니다."
    mbr.pick(["전혀 다른 문장입니다.", 좋, 좋])
    assert mbr.STATS["첫째_아님"] == 1


def test_모두_같으면_재지_않는다():
    """온도 0 이면 후보 여덟이 같은 문장 여덟 개다 — 그때 chrF 를 28 번 부를 까닭이 없다."""
    mbr.pick(["같다."] * 5)
    assert mbr.STATS["모두_같음"] == 1 and mbr.STATS["첫째_아님"] == 0


def test_빈_후보를_버리지_않는다():
    """버리면 「모델이 아무것도 안 뱉었다」 가 점수에서 사라진다 — 저절로 지게 둔다."""
    좋 = "버킷에 객체를 저장합니다."
    assert mbr.pick(["", 좋, 좋]) == 좋
    assert mbr.pick(["", "", ""]) == ""          # 다 비면 빈 것이 답이다


@pytest.mark.parametrize("cands,want", [([], ""), (["하나"], "하나")])
def test_후보가_모자라도_안_죽는다(cands, want):
    assert mbr.pick(cands) == want


def test_같은_입력이면_같은_답이다():
    """동점이면 먼저 온 것 — 고르기가 실행마다 흔들리면 재현이 안 된다."""
    c = ["가나다라마", "가나다라마", "바사아자차"]
    assert mbr.pick(c) == mbr.pick(c) == "가나다라마"


def test_퍼짐을_센다():
    """후보가 얼마나 갈렸는지가 「이 줄이 어려웠는가」 다(DECISIONS §60 의 규율)."""
    mbr.pick(["아주 다른 문장 하나입니다.", "완전히 별개의 말입니다.", "세 번째로 다른 것입니다."])
    assert mbr.STATS["퍼짐_합"] > 0


def test_팔이_등록되고_온도를_솔직히_적는다():
    """머리줄이 「온도 0」 이라고 적으면 그 조건으로 되풀이해도 다른 수가 나온다(DECISIONS §57)."""
    for arm, n in backends.MBR_ARMS.items():
        assert arm in backends.REGISTRY and backends.OLLAMA_OF[arm] == "gemma3:4b"
        d = backends.DECODING_OF[arm]
        assert d["temperature"] > 0 and d["nbest"] == n and "seed0" in d


def test_서빙_후보와_후처리가_같다():
    """달라진 것이 고르기 하나여야 무엇이 효과인지 가른다."""
    for arm in backends.MBR_ARMS:
        assert arm.endswith("+endings+terms") and "+ph+" in arm
