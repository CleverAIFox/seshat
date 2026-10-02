"""번역이 아닌 출력을 가려낸다.

2026-10-02. 교사 돌림에서 원문이 **모델에게 내리는 지시로 읽히는** 줄이 나왔다.
"Use a minimum of H2 headings (with two leading # characters)." 를 받고 `##` 를
250줄 찍었고, "Use double quotes to …" 를 받고 큰따옴표를 덧씌워 돌려줬다.
gemba 는 그중 셋에 90점 이상을 줬다 — 영어를 글자 하나 안 바꾸고 돌려준 줄에
100점을 줬다(DECISIONS 참조).

★ 밖 — **번역이 맞는지는 안 본다.** 뜻이 틀렸는지 · 어색한지 · 용어가 다른지 ·
  조사가 맞는지는 여기서 안 센다. 그것은 gemba 와 terms 가 보는 자리다.
  여기가 묻는 것은 하나다 — **이 출력이 번역이기는 한가.**

★ 밖 — **거짓 양성을 0 에 가깝게 두려고 갈래를 좁게 잡았다.** "제출하지
  마십시오"(원문: Exclude this label from your webhook match conditions) 처럼
  한국어이고 번역 모양이지만 뜻이 딴판인 줄은 **못 잡는다.** 그런 줄은 gemba 가
  0점을 줬다 — 두 검사가 서로 다른 것을 보므로 **둘 다 걸어야 한다.**
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from seshat import paths  # noqa: E402

한글 = re.compile(r"[가-힣]")

# ★ **통째로 이것일 때만 센다.** 부분 일치로 잡으면 "시간을 알려주는 것입니다"
#   같은 멀쩡한 번역이 걸린다 — 실제로 내 첫 정규식이 그렇게 틀렸다.
혼잣말 = {
    "알겠습니다", "알겠습니다.", "확인했습니다", "확인했습니다.",
    "알려주십시오", "알려주십시오.", "알려주시면 됩니다", "알려주시면 됩니다.",
    "네", "네.", "물론입니다", "물론입니다.",
}

# ★ 이 토막들은 번역문에 섞일 수 없다. 번역을 **요청하는** 말이다.
되묻는말 = (
    "번역할 텍스트", "번역할 문장", "번역할 내용",
    "텍스트를 입력", "텍스트를 제공", "문장을 입력", "문장을 제공",
    "무엇을 도와", "번역해 드리", "번역해 주십시오", "번역해 주세요",
)


def 납작(글: str) -> str:
    return re.sub(r"\s+", " ", (글 or "")).strip()


def 칸(글: str, 폭: int) -> str:
    """★ 한글은 두 칸을 먹는다. 글자 수로 맞추면 표가 어긋난다."""
    쓴 = sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in 글)
    return 글 + " " * max(0, 폭 - 쓴)


def 이탈(원문: str, 출력: str) -> str:
    """번역이 아니면 갈래 이름, 번역이면 빈 문자열."""
    나 = 납작(출력)
    if not 나:
        return "빈 출력"
    if 나.lower() == 납작(원문).lower():
        return "원문 그대로"

    줄 = [x for x in (출력 or "").splitlines() if x.strip()]
    if len(줄) >= 5:
        많 = Counter(x.strip() for x in 줄).most_common(1)[0][1]
        if 많 >= 5:
            return "되풀이"

    if 나 in 혼잣말:
        return "비서 응답"
    if any(x in 나 for x in 되묻는말):
        return "비서 응답"
    if not 한글.search(나):
        return "한글 없음"
    return ""


def 짧은가(원문: str, 출력: str) -> bool:
    """이탈로 세지는 않지만 눈으로 봐야 하는 줄 — 내용이 날아갔을 수 있다.

    ★ 밖 — 한국어가 영어보다 짧아지는 것은 정상이다. 그래서 이것은 **판정이
      아니라 표시**다. 게이트로 쓰면 멀쩡한 압축 번역이 걸린다.
    """
    원 = len(re.sub(r"\s+", "", 원문 or ""))
    낸 = len(re.sub(r"\s+", "", 납작(출력)))
    return 원 >= 40 and 낸 * 4 < 원


def 읽는다(경로: str) -> dict:
    것 = {}
    for 한줄 in paths.줄들(경로, "돌림 결과", ("경로를 다시 본다 — runs/ 밑이다",)):
        d = json.loads(한줄)
        if d.get("meta") or not d.get("id"):
            continue
        것[d["id"]] = d
    return 것


def 갈래들(경로: str | None) -> dict:
    if not 경로:
        return {}
    것 = {}
    for 한줄 in paths.줄들(경로, "탐침 셋", ("ls data/probe/ 로 본다 — git 이 드는 파일이다",)):
        d = json.loads(한줄)
        것[d["id"]] = d.get("갈래", "?")
    return 것


def main() -> int:
    받 = argparse.ArgumentParser()
    받.add_argument("돌림", help="runs/<이름>.jsonl")
    받.add_argument("--셋", help="갈래를 적어 둔 탐침 셋 — 있으면 갈래별로 나눈다")
    받.add_argument("--문턱", type=float, default=None,
                    help="이탈률이 이 값(%%)을 넘으면 1 로 끝낸다 — 게이트로 쓸 때")
    받.add_argument("--보인다", type=int, default=12, help="이탈한 줄을 몇 개 찍을지")
    고 = 받.parse_args()

    것 = 읽는다(고.돌림)
    갈 = 갈래들(고.셋)
    if not 것:
        print("잰 줄이 없다 — 돌림 결과가 비었다")
        return 1

    판정 = {}
    for i, d in 것.items():
        판정[i] = 이탈(d.get("src", ""), d.get("out", ""))

    모든갈래 = sorted({갈.get(i, "전체") for i in 것})
    print(f"{len(것)}줄 · {Path(고.돌림).name}\n")
    print(칸("갈래", 10) + f"{'줄':>5}{'이탈':>7}{'이탈률':>10}")
    print("-" * 32)
    전체이탈 = 0
    for g in 모든갈래:
        들 = [i for i in 것 if 갈.get(i, "전체") == g]
        난 = sum(1 for i in 들 if 판정[i])
        전체이탈 += 난
        print(칸(g, 10) + f"{len(들):>5}{난:>5}{난 / len(들) * 100:>9.1f}%")
    print("-" * 32)
    률 = 전체이탈 / len(것) * 100
    print(칸("합", 10) + f"{len(것):>5}{전체이탈:>5}{률:>9.1f}%")

    셈 = Counter(판정[i] for i in 것 if 판정[i])
    if 셈:
        print("\n갈래별 —", " · ".join(f"{k} {v}" for k, v in 셈.most_common()))

    짧 = [i for i in 것 if not 판정[i] and 짧은가(것[i].get("src", ""), 것[i].get("out", ""))]
    if 짧:
        print(f"눈으로 볼 것 — 많이 짧아진 줄 {len(짧)}건 (이탈로는 세지 않았다)")

    난것 = [i for i in sorted(것) if 판정[i]]
    for i in 난것[: 고.보인다]:
        print(f"\n[{i}] {판정[i]}" + (f" · {갈[i]}" if i in 갈 else ""))
        print(f"  원: {것[i].get('src', '')[:100]}")
        print(f"  번: {납작(것[i].get('out', ''))[:100]}")
    if len(난것) > 고.보인다:
        print(f"\n… {len(난것) - 고.보인다}건 더 있다 — --보인다 로 늘린다")

    if 고.문턱 is not None and 률 > 고.문턱:
        print(f"\n이탈률 {률:.1f}% 가 문턱 {고.문턱:.1f}% 를 넘었다")
        return 1
    return 0


if __name__ == "__main__":
    # ★ 위반(1)과 도구 고장(2)을 다른 코드로 끝낸다(DECISIONS §21 · §232). 같은 코드면
    #   **도구가 깨진 것을 검사가 실패한 것으로 읽는다**
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        print("    ✗ 도구가 깨졌다 — 위 역추적이 자리를 든다\n"
              "      고치고 다시 돌린다 : bash tools/verify.sh", file=sys.stderr)
        sys.exit(2)
