"""**무엇이 같아야 견줄 수 있나** — 한 곳에서 답한다(DECISIONS §157).

  from seshat import compare
  compare.갈림(a_head, b_head, compare.AA)      # 같은 팔 두 판(A/A)
  compare.갈림(a_head, b_head, compare.AB)      # 처치 대 대조(A/B)
  compare.가린_지표(rec, target)                # 보호가 다르면 못 견주는 지표

★ **2026-09-28 하루에 같은 병을 여덟 번 앓았다** — 허용치(§139) · 이름(§143) · 반올림(§144) ·
  자(§145) · 올리기(§146) · 선 줄(§147) · 보호(§156) · 그리고 `compare_runs` 가 자를 안 보던 것.
  **전부 「견줄 수 없는 두 수를 견줬다」 의 변형**이고, 까닭은 하나다 — **조건이 다섯 곳에 손으로
  적혀 있었다**(문의 `check` 에 셋 · 문의 선 줄 · `noise.SAME` · `compare_runs`). 손으로 적으면
  반드시 한 곳이 빠진다.
★ **이 파일이 그 목록의 유일한 자리다.** 새 축이 생기면 여기에만 더한다.
★ **`protects` 는 통째로 막지 않는다.** 보호가 다르면 **그 지표만** 못 견주고 나머지는 견준다 —
  `term_off` 는 끝까지 나온 문장을 재므로 양쪽 다 모델이 만든 값이다(§156).
"""
from __future__ import annotations

from typing import NamedTuple


class 축(NamedTuple):
    이름: str
    말머리: str        # 갈렸을 때 첫 줄. 문의 시험이 이 글자를 본다 — 바꾸면 같이 고친다
    왜: str


AXIS: dict[str, 축] = {
    "set_sha256": 축("셋", "셋이 다르다",
                     "다른 글로 잰 두 수를 견주면 그 비교가 거짓말이다(DECISIONS §45)"),
    "metrics": 축("자", "자가 바뀌었다",
                  "사전이 바뀐 것과 다르다 — 사전은 **같은 것을 더 잘 재는** 일이고 "
                  "자가 바뀌는 것은 **다른 것을 재는** 일이다(§145)"),
    "onto_sha256": 축("사전", "사전이 바뀌었다",
                      "같은 번역의 점수가 바뀐다(§32 · §96). **막지 않는다** — 막으면 사전을 "
                      "영영 못 고친다. 재채점으로 기준을 다시 박으라고 이른다"),
    "backend": 축("팔", "팔이 다르다",
                  "다른 팔의 차이는 잡음이 아니다 — A/A 에서만 막는다"),
}

# 같은 팔을 여러 판(A/A) — 넷이 다 같아야 그 차이가 잡음이다
AA = ("backend", "set_sha256", "onto_sha256", "metrics")
# 처치 대 대조(A/B) — 팔은 다른 것이 요점이다
AB = ("set_sha256", "onto_sha256", "metrics")
# 문이 **막는** 축. 사전은 여기 없다 — 말만 한다
GATE_막 = ("metrics", "set_sha256")


class 갈린것(NamedTuple):
    키: str
    이름: str
    말머리: str
    왜: str
    가: object
    나: object

    def 글(self) -> str:
        return (f"{self.말머리} — 이쪽 {self.가 or '없다'} · 저쪽 {self.나 or '없다'}\n"
                f"    {self.왜}")


def 갈림(a: dict, b: dict, axes: tuple[str, ...]) -> list[갈린것]:
    """두 머리줄에서 **견줄 수 없게 만드는 축**만 든다. 비었으면 견줘도 된다.

    ★ **한쪽이 비어 있어도 갈린 것이다.** 「값이 없다」 는 「같다」 가 아니다 — 옛 판에는 `metrics`
      가 아예 없고, 그것을 같음으로 치면 자를 바꾸기 전후가 조용히 섞인다(§110 과 같은 규율).
    """
    out = []
    for k in axes:
        가, 나 = a.get(k), b.get(k)
        if (가 or "") != (나 or ""):
            축_ = AXIS[k]
            out.append(갈린것(k, 축_.이름, 축_.말머리, 축_.왜, 가, 나))
    return out


def 가린_지표(가: dict, 나: dict) -> set[str]:
    """보호가 달라서 **못 견주는 지표**. 통째로 막지 않는다(DECISIONS §156).

    ★ 자리표시가 지키는 `lit` 1.0 과 모델이 지킨 `lit` 0.92 는 **다른 수**다. 셋도 사전도 자도
      같으므로 위의 축들은 전부 통과한다 — 이것만이 그 차이를 본다.
    """
    return set(가.get("protects") or []) ^ set(나.get("protects") or [])
