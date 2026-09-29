"""**닫힌 PLAN 행을 되살리는 길**이 살아 있나(DECISIONS §222).

★ 이 시험이 지키는 것은 「행이 남아 있다」 가 아니라 **「없어진 행을 꺼낼 수 있다」** 다.
  git 은 한 글자도 안 버린다 — 없던 것은 꺼내는 길이다.
"""
from __future__ import annotations

import importlib.util
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("plan_closed", ROOT / "tools/plan_closed.py")
PC = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(PC)


def test_닫힌_번호를_빠짐없이_센다():
    """★ `re.M` 이 빠지면 `findall` 이 첫 줄만 보고 **닫힌 행이 0** 으로 나온다 — 조용한 거짓이다."""
    글 = (ROOT / PC.PLAN).read_text(encoding="utf-8")
    있는 = sorted(int(m) for m in re.findall(r"^\| (\d+) \|", 글, re.M))
    assert PC.닫힌_번호() == [n for n in range(1, max(있는) + 1) if n not in 있는]
    assert PC.닫힌_번호(), "닫힌 행이 하나도 없다고 한다 — 스물 넘게 닫았다"


def test_얕은_사본이면_이력이_없다고_말한다(capsys):
    """★ **CI 의 `checkout` 은 깊이 1 이다**(DECISIONS §224). 이력이 없을 때 죽지 말고 말해야 한다.

    2026-09-29 이 시험의 앞 판이 CI 에서만 빨개졌다 — 이 기계에는 이력이 있고 거기엔 없었다(§170).
    """
    import subprocess
    얕나 = subprocess.run(["git", "rev-parse", "--is-shallow-repository"],
                         capture_output=True, text=True, cwd=ROOT).stdout.strip() == "true"
    if not 얕나:
        return
    assert PC.main([str(PC.닫힌_번호()[-1])]) == 1
    말 = capsys.readouterr().err
    assert "--unshallow" in 말 and "fetch-depth" in 말, "막기만 하고 넘는 길을 안 준다"


def test_닫힌_행의_본문을_이력에서_꺼낸다():
    """★ **지워진 것과 못 찾는 것은 다르다.** 본문은 이력에 있고 이 길이 그것을 꺼낸다."""
    판 = PC.판본들()
    if len(판) < 2:
        return                       # 얕은 사본 — 위 시험이 그 길을 본다
    n = PC.닫힌_번호()[-1]
    본문 = next((PC.그때의_행(c, n) for c, _, _ in 판 if PC.그때의_행(c, n)), "")
    assert 본문.startswith(f"| {n} |"), 본문[:80]


def test_그_번호를_든_절을_찾는다():
    """번호만 본다 — **뜻이 맞는지는 사람이 읽는다**(도장의 일과 가른다)."""
    for n in PC.닫힌_번호():
        assert PC.든_절(n), f"#{n} 을 든 절이 없다 — check_plan_closed 가 막았어야 한다"
