"""종결 어미 정규화 — 해요체 의문을 합쇼체 의문으로(DECISIONS §31).

★ **좁게 만든다.** H-019 에서 깨진 14줄은 전부 `… 충족할까요?` 한 모양이다. 한국어 종결 전체를 다루는 규칙을
  쓰면 맞는 문장까지 건드린다. 관측한 모양만 바꾸고, 나머지는 그대로 둔다.
★ 규칙은 자모 계산이다 — 받침 `ㄹ` · `ㄴ` 뒤의 `까요` · `가요` 를 `ㅂ니까` 로 바꾼다.
    할까요 → 하 + ㅂ + 니까 = 합니까      인가요 → 이 + ㅂ + 니까 = 입니까
★ **번역 품질을 올리는 도구가 아니다.** 검사기가 고칠 수 있는 것을 재는 자다 — 학습(보상)이 무엇을 배워야
  하는지 가르려고 만든다(PLAN #19).
"""
from __future__ import annotations

import re

BASE, JONG = 0xAC00, 28
_RIEUL, _NIEUN, _BIEUP = 8, 4, 17      # 종성 자모 순번


def _parts(ch: str) -> tuple[int, int] | None:
    i = ord(ch) - BASE
    return (i // JONG, i % JONG) if 0 <= i < 11172 else None


def _put_jong(ch: str, jong: int) -> str:
    p = _parts(ch)
    return chr(BASE + p[0] * JONG + jong) if p else ch


_Q = re.compile(r"([가-힣])(까요|가요)(\s*[?？])")


def to_hapsyo_question(text: str) -> str:
    """`…할까요?` · `…인가요?` → `…합니까?` · `…입니까?`. 받침이 안 맞으면 그대로 둔다."""
    def fix(m: re.Match) -> str:
        ch, tail, mark = m.group(1), m.group(2), m.group(3)
        p = _parts(ch)
        want = _RIEUL if tail == "까요" else _NIEUN
        if p is None or p[1] != want:
            return m.group(0)
        return _put_jong(ch, _BIEUP) + "니까" + mark
    return _Q.sub(fix, text)


def normalize(text: str) -> str:
    return to_hapsyo_question(text)
