"""`tools/check_prose.py` 의 세 규칙이 살아 있는가(DECISIONS §282).

★ 이 파일은 **seshat 것**이다 — thoth 사본이 아니다(DECISIONS §5).
★ **양성과 음성을 함께 본다.** 「잡는다」 만 보면 **전부 잡는 규칙**도 통과한다 — 그러면
  규칙을 켜는 날 멀쩡한 문장이 다 걸리고, 그때 사람은 고치는 대신 **끈다**(thoth §46).
★ 규칙을 하나씩 들어내 **셋 전부 빨개지는 것**을 봤다 — 통과만 보는 검사는 검사가 아니다
  (DECISIONS §265).
"""
from __future__ import annotations

import importlib.util
import pathlib

ROOT = next(p for p in pathlib.Path(__file__).resolve().parents if (p / "tools/check_prose.py").exists())
_spec = importlib.util.spec_from_file_location("cp", ROOT / "tools/check_prose.py")
CP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CP)


# ---------- 1. 맨 §N ----------

def test_없는_번호를_잡는다():
    assert CP.맨절("보라 §999 를", {"9"}) == [(1, "999")]


def test_아는_번호는_통과한다():
    """★ **이것이 음성 대조다.** 맨 `§N` 을 **금지하지 않는다** — 코드 주석 600 곳이 그 문체다."""
    assert CP.맨절("재표집으로 본다(§180)", {"180"}) == []


def test_문서명이_붙으면_그_문서로_읽는다():
    assert CP.맨절("DECISIONS §9 와 MASTER §7", {"9", "7"}) == []


def test_사슬의_뒤쪽도_붙은_참조다():
    """`DECISIONS §98 · §110` 의 뒤쪽은 이름 없이 온다. 앞만 보면 뒤쪽이 검사 밖이다."""
    assert CP.맨절("(DECISIONS §98 · §110)", {"98", "110"}) == []


def test_줄바꿈으로_끊긴_사슬도_붙은_참조다():
    """★ MASTER 에 실제로 그런 자리가 있다 — `(DECISIONS §58 ·` 에서 줄이 바뀌고 `§61)` 로 이어진다."""
    assert CP.맨절("탐침 200 줄에서(DECISIONS §58 ·\n§61) 재니", {"58", "61"}) == []


def test_백틱_문서명도_붙은_참조다():
    assert CP.맨절("정본은 thoth `docs/now/MASTER.md` §7-4 다", {"7"}) == []


def test_마크다운_링크_뒤도_붙은_참조다():
    assert CP.맨절("[PLAN](docs/next/PLAN.md) §0 부터 읽는다", {"0"}) == []


def test_규칙_번호는_이_검사의_밖이다():
    """★ 밖 — `§11-3` 은 절이 아니라 **절 안의 규칙 번호**이고 `check_rules` 가 본다(DECISIONS §230)."""
    assert CP.맨절("★ §11-3 **결과 파일의 이름은**", set()) == []


def test_저장소가_지금_통과한다():
    """★ 검사를 넣는 날 이미 깨져 있으면 아무도 고치지 않고 꺼 버린다(thoth §46)."""
    assert CP.check_맨절(ROOT) == []


# ---------- 2. 표 깨짐 ----------

표 = "| a | b |\n|---|---|\n| 1 | 2 |\n"


def test_붙은_표는_통과한다():
    assert CP.표깨짐(표) == []


def test_빈_줄_뒤에_떨어진_줄을_잡는다():
    assert CP.표깨짐(표 + "\n| 3 | 4 |\n") == [5]


def test_새_표의_머리줄은_통과한다():
    """머리줄 다음이 `|---|` 면 새 표가 선 것이고 맞다."""
    assert CP.표깨짐("글\n\n" + 표) == []


def test_울_안의_표는_안_본다():
    assert CP.표깨짐("```\n\n| a | b |\n```\n") == []


def test_문서에_떨어진_표_줄이_없다():
    assert CP.check_표깨짐(ROOT) == []


# ---------- 3. 빈 약속 ----------

def test_행이_없는_약속을_잡는다():
    assert CP.빈약속("이 항목은 열려 있다.\n") == [(1, "열려 있다")]


def test_행이_있으면_통과한다():
    assert CP.빈약속("이 항목은 열려 있고 PLAN #47 이 그 자리다\n") == []


def test_울_안은_안_본다():
    assert CP.빈약속("```\n이 항목은 열려 있다.\n```\n") == []


def test_MASTER_에_빈_약속이_없다():
    assert CP.check_빈약속(ROOT) == []


# ---------- 카나리아 ----------

def test_카나리아가_살아_있다():
    """★ 0건이 목표인 검사는 0건을 성공으로만 읽으면 안 된다 — 깨끗해서인지 정규식이
    죽어서인지 가를 수 없다(DECISIONS §265). `_canary` 가 죽으면 2 로 끝난다.

    ★ **`assert` 로 적는다.** 몸통이 부름 하나면 지워도 통과하므로 그것은 검사가 아니다
      (`tools/check_deadchecks.py` · DECISIONS §255).
    """
    import pytest
    CP._canary()                     # 죽었으면 SystemExit(2)
    # 양성 대조 — 규칙 하나를 죽이면 카나리아가 **멈춰야 한다**
    원 = CP.표줄
    try:
        CP.표줄 = __import__("re").compile(r"NEVERMATCH")
        with pytest.raises(SystemExit) as 났:
            CP._canary()
        assert 났.value.code == 2, "카나리아가 죽었는데 위반(1)으로 끝났다"
    finally:
        CP.표줄 = 원
    assert CP._canary() is None      # 되돌리면 다시 조용하다
