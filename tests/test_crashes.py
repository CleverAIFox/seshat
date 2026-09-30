"""**도구가 역추적으로 죽지 않는가** — 그 검사가 살아 있는가(DECISIONS §232).

★ 이 시험이 지키는 것은 「다 싼다」 가 아니라 **「맨몸이 늘지 않는다」** 다.
  스물여섯을 한 판에 고치는 것은 판을 위험하게 만들고, 새로 생기는 것을 막는 것은 오늘 할 수 있다.
★ 이 파일은 **seshat 것**이다 — thoth 사본이 아니다(DECISIONS §5).
"""
from __future__ import annotations

import importlib.util
import pathlib

ROOT = next(p for p in pathlib.Path(__file__).resolve().parents if (p / "tools/check_crashes.py").exists())
_spec = importlib.util.spec_from_file_location("cc", ROOT / "tools/check_crashes.py")
CC = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CC)

맨몸 = 'import sys\n\n\ndef main():\n    return 0\n\n\nif __name__ == "__main__":\n    sys.exit(main())\n'
싼것 = (맨몸.replace("    sys.exit(main())\n",
                    "    try:\n        sys.exit(main())\n"
                    "    except SystemExit:\n        raise\n"
                    "    except Exception:\n        sys.exit(2)\n"))
도구아님 = "def 도움(x):\n    return x\n"


def test_맨몸을_찾는다():
    assert CC.맨몸인가(맨몸)


def test_싼_것은_안_잡는다():
    assert not CC.맨몸인가(싼것)


def test_문이_없으면_도구가_아니다():
    """★ `__main__` 이 없는 것은 모듈이다 — 죽어도 부른 쪽이 받는다."""
    assert not CC.맨몸인가(도구아님)


def test_새로_생긴_것만_말한다():
    assert CC.견준다(["tools/새것.py"], frozenset()), "새로 생겼는데 조용하다"
    assert CC.견준다(["a.py"], frozenset({"a.py", "b.py"})) == [], "갚은 것은 실패가 아니다"
    assert CC.견준다([], frozenset({"a.py"})) == []


def test_저장소가_장부와_맞는다():
    """★ **장부가 실물보다 늦으면 이 도구는 거짓 초록을 낸다**(§170 과 같은 병).

    줄었으면 안 깨진다 — `--update` 로 박으라고 도구가 말한다. 늘면 깨진다.
    """
    assert CC.main([]) == 0


def test_제_규칙을_제가_지킨다():
    """★ 검사기가 맨몸이면 그 검사는 농담이다."""
    assert not CC.맨몸인가((ROOT / "tools/check_crashes.py").read_text(encoding="utf-8"))


def test_오늘_죽은_도구는_갚았다():
    """★ 2026-09-30 `lake.py` 가 메모리 부족으로 역추적을 뱉었다 — 그 자리부터 갚는다(§232)."""
    assert "tools/lake.py" not in CC.장부
    assert not CC.맨몸인가((ROOT / "tools/lake.py").read_text(encoding="utf-8"))
