"""`tools/check_size.py` 의 양방향 라쳇이 살아 있는가(DECISIONS §286).

★ 이 파일은 **seshat 것**이다 — thoth 사본이 아니다(DECISIONS §5).
★ **양방향을 둘 다 본다.** 「늘면 운다」 만 보면 **줄었을 때 선언을 안 내려도 초록**이고,
  그러면 그만큼 다시 늘 자리가 생긴다 — **느슨해진 라쳇은 초록으로 위장한다.**
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

ROOT = next(p for p in pathlib.Path(__file__).resolve().parents if (p / "tools/check_size.py").exists())
_spec = importlib.util.spec_from_file_location("cs", ROOT / "tools/check_size.py")
CS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CS)


@pytest.fixture
def 예외(monkeypatch):
    """예외표를 합성으로 갈아 끼운다. **실물을 건드리지 않는다.**"""
    것: dict[str, int] = {}
    monkeypatch.setattr(CS, "예외", 것)
    return 것


def test_늘면_운다(예외):
    예외["a.py"] = 100
    assert any("늘었다" in x for x in CS.견준다({"a.py": 101}))


def test_줄어도_운다(예외):
    """★ **이것이 양방향 라쳇의 핵이다.** 줄인 뒤 선언을 안 내리면 그만큼 다시 늘 자리가
    생기고, **그 자리는 아무에게도 안 보인다.**"""
    예외["a.py"] = 100
    난 = CS.견준다({"a.py": 99})
    assert 난 and "줄었다" in 난[0] and "99" in 난[0]


def test_같으면_조용하다(예외):
    예외["a.py"] = 100
    assert CS.견준다({"a.py": 100}) == []


def test_예외_밖이_상한을_넘으면_운다(예외):
    assert any("넘었다" in x for x in CS.견준다({"b.py": CS.상한 + 1}))


def test_예외_밖이_상한_안이면_조용하다(예외):
    """★ **음성 대조다.** 전부 우는 규칙도 「늘면 운다」 만 보면 통과한다."""
    assert CS.견준다({"b.py": CS.상한}) == []


def test_죽은_예외를_잡는다(예외):
    """★ 지워진 파일을 예외표가 들고 있으면 **그 줄은 영원히 참이다** — 라쳇이 아니라 장식이다."""
    예외["없는파일.py"] = 100
    assert any("죽은 예외" in x for x in CS.견준다({}))


def test_저장소가_지금_통과한다():
    """★ 검사를 넣는 날 이미 깨져 있으면 아무도 고치지 않고 꺼 버린다(thoth DECISIONS §46)."""
    assert CS.견준다(CS.센다(ROOT)) == []


def test_예외표가_실측과_같다():
    """★ **예외표는 「넘는다」 가 아니라 「지금 몇이다」 를 적는다.** 수를 안 적으면 그 파일은
    상한 밖으로 영원히 빠지고, 그것은 면제이지 라쳇이 아니다."""
    수 = CS.센다(ROOT)
    for rel, 선언 in CS.예외.items():
        assert 수.get(rel) == 선언, f"{rel} 선언 {선언} · 실측 {수.get(rel)}"


def test_예외표가_전부_상한을_넘는다():
    """★ 상한 아래인 파일이 예외표에 있으면 **그 줄은 아무것도 안 막는다** — 지워야 한다."""
    낮은 = {r: n for r, n in CS.예외.items() if n <= CS.상한}
    assert 낮은 == {}, f"상한 {CS.상한} 아래인데 예외에 있다 — {낮은}"


def test_카나리아가_예외표를_되돌려_놓는다():
    """★ **카나리아가 제 발자국을 지우는가.** `_canary` 는 판별식을 물어보려고 예외표를
    갈아 끼운다 — 되돌려 놓지 않으면 **그 뒤의 모든 판정이 합성 표로 난다.**
    0건이 목표인 검사는 0건을 성공으로만 읽으면 안 된다(DECISIONS §265).
    """
    원 = dict(CS.예외)
    assert CS._canary() is None
    assert dict(CS.예외) == 원, "카나리아가 예외표를 되돌려 놓지 않았다"
    assert 원, "예외표가 비었다 — 카나리아가 지우고 갔다"
