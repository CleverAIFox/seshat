"""**닫힌 PLAN 행을 되살려 보여준다**(DECISIONS §222).

  python3 tools/plan_closed.py            닫힌 번호와 그것을 든 절
  python3 tools/plan_closed.py 46         그 행이 마지막으로 살아 있던 본문 · 언제 사라졌나
  python3 tools/plan_closed.py 46 --all   그 행이 바뀌어 온 이력 전부

★ **PLAN 은 닫힌 행을 지운다** — 닫힘 표식을 만들면 표가 무덤이 되기 때문이다(MASTER §0). 그 대가로
  **행의 본문은 이력에만 남는다.** DECISIONS 는 「왜 닫았나」 를 적지, 그 행이 몇 달 동안 모아 온
  근거 · 막는 문장 · 전건을 다 옮기지는 않는다.
★ **지워진 것과 못 찾는 것은 다르다.** git 은 한 글자도 안 버렸다. 없던 것은 **「거기 있다」 를 아는
  길**이고, 그것이 없으면 사람은 없어진 것으로 여긴다 — 2026-09-29 이 물음을 받고서야 알았다.
★ 이 도구는 **읽기만 한다.** 되살린 행을 PLAN 에 다시 붙이는 일은 사람이 한다 — 닫힌 행이 저절로
  돌아오면 닫는 일이 뜻을 잃는다.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PLAN = "docs/next/PLAN.md"
# ★ `re.M` 이 없으면 `findall` 이 **첫 줄만** 본다 — 닫힌 행이 0 으로 나온다
행 = re.compile(r"^\| (\d+) \|", re.M)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, cwd=ROOT).stdout


def 판본들() -> list[tuple[str, str, str]]:
    """(커밋, 날짜, 제목) — 새것부터. **옮긴 자리를 따라간다**(§199 에서 `docs/PLAN.md` 였다)."""
    글 = _git("log", "--follow", "--format=%H\t%cs\t%s", "--", PLAN)
    return [tuple(x.split("\t", 2)) for x in 글.splitlines() if x.count("\t") >= 2]


def 그때의_행(커밋: str, n: int) -> str:
    """그 커밋에서 `#n` 행의 본문. 없으면 빈 글."""
    for 자리 in (PLAN, "docs/PLAN.md"):
        글 = _git("show", f"{커밋}:{자리}")
        if 글:
            for x in 글.splitlines():
                m = 행.match(x)
                if m and int(m.group(1)) == n:
                    return x
            return ""
    return ""


def 얕은가() -> bool:
    """**이력이 잘린 사본인가**(DECISIONS §224). CI 의 `checkout` 은 기본이 깊이 1 이다.

    ★ 얕아도 `git log` 는 **한 판을 준다** — 그래서 「이력이 비었나」 로는 못 가른다. 물어야 한다.
    """
    return _git("rev-parse", "--is-shallow-repository").strip() == "true"


def 닫힌_번호() -> list[int]:
    글 = (ROOT / PLAN).read_text(encoding="utf-8")
    있는 = sorted(int(m) for m in 행.findall(글))
    return [n for n in range(1, max(있는) + 1) if n not in 있는] if 있는 else []


def 든_절(n: int) -> list[str]:
    """그 번호를 든 DECISIONS 절. **번호만 보고 뜻은 안 본다**(그것은 사람이 읽는다)."""
    글 = (ROOT / "docs/why/DECISIONS.md").read_text(encoding="utf-8")
    절 = [(m.group(1), m.start()) for m in re.finditer(r"^## §(\d+)\.", 글, re.M)]
    본 = set()
    for m in re.finditer(rf"(?<![\w§-])#{n}(?!\d)", 글):
        앞 = [번 for 번, s in 절 if s < m.start()]
        if 앞:
            본.add(앞[-1])
    return sorted(본, key=int)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    번호 = [x for x in args if x.isdigit()]
    if not 번호:
        닫힌 = 닫힌_번호()
        print(f"  닫힌 행 {len(닫힌)} — 본문은 이력에 산다. 하나를 보려면 번호를 준다\n"
              f"    친다 : python3 tools/plan_closed.py <번호>")
        for n in 닫힌:
            절 = 든_절(n)
            print(f"    #{n:<3} {'§' + ' · §'.join(절) if 절 else '**어느 절도 안 든다**'}")
        return 0

    n = int(번호[0])
    판 = 판본들()
    본문, 죽은판 = "", None
    for i, (커밋, 날, 제목) in enumerate(판):
        글 = 그때의_행(커밋, n)
        if 글:
            본문 = 글
            죽은판 = 판[i - 1] if i else None      # 그 바로 뒤 판에서 사라졌다
            break
    if not 본문:
        # ★ **못 찾은 것과 볼 수 없는 것을 가른다**(DECISIONS §224). 얕은 사본에서도 `git log` 는
        #   한 판을 주므로 「이력이 비었나」 로는 못 가른다 — 얕은지를 **묻는다**
        if 얕은가():
            print(f"  ✗ 이력이 잘린 사본이라 못 본다 — `#{n}` 이 없는 것이 아니다\n"
                  f"    이력째 받는다 : git fetch --unshallow\n"
                  f"    CI 라면 : `actions/checkout` 에 `with: {{ fetch-depth: 0 }}`", file=sys.stderr)
        else:
            print(f"  ✗ #{n} 은 이력에도 없다 — 번호가 맞나\n"
                  f"    닫힌 번호를 본다 : python3 tools/plan_closed.py", file=sys.stderr)
        return 1
    절 = 든_절(n)
    print(f"  #{n} — 마지막으로 살아 있던 본문\n")
    print(f"    {본문}\n")
    if 죽은판:
        print(f"  사라진 판 : {죽은판[0][:7]} {죽은판[1]} {죽은판[2][:60]}")
    else:
        print("  아직 살아 있다 — 닫힌 행이 아니다")
    print(f"  그 번호를 든 절 : {'§' + ' · §'.join(절) if 절 else '**없다**'}")
    if "--all" in args:
        print("\n  이력 —")
        앞 = None
        for 커밋, 날, 제목 in reversed(판):
            글 = 그때의_행(커밋, n)
            if 글 and 글 != 앞:
                print(f"    {날} {커밋[:7]} {제목[:50]}\n      {글[:160]}")
                앞 = 글
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
