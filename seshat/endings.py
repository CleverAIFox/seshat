"""종결 어미 정규화 — 해요체 의문을 합쇼체 의문으로(DECISIONS §31).

★ **좁게 만든다.** H-019 에서 깨진 14줄은 전부 `… 충족할까요?` 한 모양이다. 한국어 종결 전체를 다루는 규칙을
  쓰면 맞는 문장까지 건드린다. 관측한 모양만 바꾸고, 나머지는 그대로 둔다.
★ 2026-09-23 H-032 에서 깨진 3줄은 의문이 아니었다 — `암호화되어야 한다.` · `늘려야 한다.` · `연결하세요.`
  관측한 모양을 하나씩 더 받는다. **여전히 관측한 것만 받는다** — 한국어 종결 전체를 다루지 않는다.
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

# 문장 끝 — 마침표 · 느낌표 · 닫는 따옴표 앞, 또는 줄 끝
_TAIL = r"(?=\s*[.!。！]|\s*$)"
_HANDA = re.compile(r"([가-힣])다" + _TAIL)          # 한다 · 된다 · 먹는다 · 이다
_NEUNDA = re.compile(r"([가-힣])는다" + _TAIL)        # 먹는다 · 읽는다
_SEYO = re.compile(r"세요" + _TAIL)                  # 하세요 · 주세요


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


def to_hapsyo_statement(text: str) -> str:
    """`…한다.` · `…먹는다.` · `…이다.` → `…합니다.` · `…먹습니다.` · `…입니다.`

    자모로 가른다 — 종성 `ㄴ` 이면 그 자리를 `ㅂ` 으로 바꾸고 `니다` 를 붙인다(하+ㄴ다 → 합니다).
    `는` 앞 글자에 받침이 있으면 `는다` 를 `습니다` 로 바꾼다(먹는다 → 먹습니다).
    `이다` 는 `입니다`. **그 밖의 `…다` 는 건드리지 않는다** — 명사 `기다` · 인용 `…다고` 를 깨뜨린다.
    """
    def fix(m: re.Match) -> str:
        ch = m.group(1)
        p = _parts(ch)
        if p is None:
            return m.group(0)
        if p[1] == _NIEUN:                       # 한다 · 된다 · 간다
            return _put_jong(ch, _BIEUP) + "니다"
        if ch == "이":                            # …이다
            return "입니다"
        return m.group(0)

    def fix_neun(m: re.Match) -> str:
        ch = m.group(1)
        p = _parts(ch)
        return ch + "습니다" if p and p[1] else m.group(0)

    text = _NEUNDA.sub(fix_neun, text)
    return _HANDA.sub(fix, text)


def to_hapsyo_command(text: str) -> str:
    """`…하세요.` → `…하십시오.` 해요체 명령은 합쇼체 명령으로."""
    return _SEYO.sub("십시오", text)


def normalize(text: str) -> str:
    return to_hapsyo_command(to_hapsyo_statement(to_hapsyo_question(text)))
