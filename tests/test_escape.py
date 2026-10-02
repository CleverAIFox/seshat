"""이탈 판정이 실제로 본 줄을 가르는지 본다.

★ 여기 적힌 줄은 전부 **2026-10-02 교사 돌림에서 실제로 나온 출력**이다.
  지어낸 예가 아니다. 규칙을 느슨하게 고치면 여기가 먼저 빨개진다.
"""
import pytest

from tools.escape import 이탈, 짧은가

# (원문, 출력, 기대 갈래) — 전부 H-088-teacher-k001 에서 관측됐다.
났다 = [
    ("Use a minimum of H2 headings (with two leading # characters).", "##\n" * 250, "되풀이"),
    ("Set served to false for the old version in the spec.versions list.",
     "Set served to false for the old version in the spec.versions list.", "원문 그대로"),
    ("Leave the uid value set the same as you found it.",
     "Leave the uid value set the same as you found it.", "원문 그대로"),
    ("Use double quotes to quote text inside JSONPath expressions.",
     '"Use double quotes to quote text inside "JSONPath expressions"."', "한글 없음"),
    ("Make sure you indent sub-list items 2 spaces.", "번역할 텍스트를 제공해주십시오.", "비서 응답"),
    ("Then proceed with the steps outlined below.", "알겠습니다. 텍스트를 입력해주십시오.", "비서 응답"),
    ("You'll need to know the two-letter language code for your language.",
     "알려주십시오.", "비서 응답"),
    ("Note there's no mention of your Service.", "알려주시면 됩니다.", "비서 응답"),
    ("You have alternative option to generate json with -j.", "알겠습니다.", "비서 응답"),
    ("If the output is 0, then follow next steps.", "0", "한글 없음"),
    ("Prepend your diagram caption with Figure NUMBER..", "Figure 1.", "한글 없음"),
    ("Assume good intent and ask clarifying questions.",
     "알겠습니다. 번역할 문장을 알려주십시오. 혹시 문맥이나 특정 용어에 대한 추가 "
     "정보가 있다면 번역의 정확도를 높이는 데 도움이 될 수 있습니다.", "비서 응답"),
    ("The default output will be printed to stdout in YAML format.", "", "빈 출력"),
]

# ★ **여기가 더 중요하다.** 전부 gemba 100점짜리 실제 출력이고, 하나라도 걸리면
#   멀쩡한 번역을 버리는 검사가 된다. 내 첫 정규식은 "알려주는 것입니다" 를 물었다.
멀쩡하다 = [
    ("The default is to write a single stream to stdout.",
     "기본값은 stdout으로 단일 스트림을 쓰는 것입니다."),
    ("See Setting Sysctls for All Pods for more details.",
     "모든 파드에 대한 Sysctls 설정에 대한 자세한 내용은 Setting Sysctls for All Pods를 "
     "참조하십시오."),
    ("Leave the Allow edits from maintainers checkbox selected.",
     "Allow edits from maintainers 체크박스를 선택해 두십시오."),
    ("The workaround is to tell kubelet which IP to use using --node-ip.",
     "해결 방법은 --node-ip을 사용하여 kubelet에 사용할 IP를 알려주는 것입니다."),
    ("Depending on the state, additional information will be provided.",
     "상태에 따라 추가 정보가 제공됩니다 - 여기에서 Running 상태의 컨테이너의 경우 "
     "시스템이 컨테이너가 시작된 시간을 알려주는 것을 확인할 수 있습니다."),
    ("You may know this feature as _evented Pod lifecycle event generator (PLEG)_.",
     "이 기능을 _evented Pod lifecycle event generator (PLEG)_라고 부르기도 합니다."),
    ("For a list of recent kernels, see Windows Server Release Information.",
     "최근 커널 목록은 Windows Server Release Information을 참조하십시오."),
    ("NetworkDeviceData provides network-related details for the allocated device.",
     "NetworkDeviceData는 할당된 장치에 대한 네트워크 관련 세부 정보를 제공합니다."),
]


@pytest.mark.parametrize("원문,출력,기대", 났다, ids=[f"{x[2]}-{i}" for i, x in enumerate(났다)])
def test_이탈한_줄을_잡는다(원문, 출력, 기대):
    assert 이탈(원문, 출력) == 기대


@pytest.mark.parametrize("원문,출력", 멀쩡하다, ids=[x[0][:28] for x in 멀쩡하다])
def test_멀쩡한_번역은_안_건드린다(원문, 출력):
    assert 이탈(원문, 출력) == ""


def test_뜻이_틀린_번역은_이_검사의_밖이다():
    """★ 밖이라고 적었으면 실제로 밖이어야 한다 — 선언과 동작이 갈리지 않게 못 박는다.

    "Exclude this label…" 이 "제출하지 마십시오" 로 나온 줄은 한국어이고 번역
    모양이라 여기서는 통과한다. 그것을 잡는 것은 gemba 이고, 실제로 0점을 줬다.
    """
    assert 이탈("Exclude this label from your webhook match conditions.",
                "제출하지 마십시오.") == ""


def test_짧아진_것은_판정이_아니라_표시다():
    assert 짧은가("Depending on the state, additional information will be provided here.", "네.")
    assert not 짧은가("Logs are written to standard output.", "로그는 표준 출력에 기록됩니다.")
