r"""**MASTER 의 ★ 줄마다 번호가 있고, 가리킨 번호가 실재하나**(DECISIONS §230).

  python3 tools/check_rules.py      검사한다. 위반 1 · 고장 2

★ `MASTER §11` 은 절 전체를 가리킨다 — 그 절의 ★ 줄이 열이면 **어느 줄을 말하는지 못 좁힌다.**
  파이어레인에서 축 셋과 절 번호는 옮겼는데(DECISIONS §111) 규칙 번호는 안 옮겼다
  (`파이어레인 MASTER §18-1a R2`).
★ **`R\d+` 를 안 쓴다.** 이 저장소에서 `R1`–`R7` 은 **연구 트랙**이고(`MASTER §7`) 가설 대장의
  트랙 칸이 그것을 맨이름으로 든다 — 같은 글자를 두 뜻으로 쓰면 **가리키는 것이 안 좁혀진다.**
  `§N-M` 은 새 글자를 안 만들고 절 번호를 그대로 잇는다.
★ **유일과 오름차순만 본다 — 연속은 안 본다.** 번호는 영구 식별자이고 결번이 정상이다
  (`docs/README.md` 「번호는 자산이다」). 연속을 요구하면 규칙 하나를 지울 때마다 **뒤가 다 밀리고
  가리키던 글이 전부 딴 것을 가리킨다.**
★ **이 도구는 seshat 것이다.** `tools/check_docs.py` 는 thoth 사본이라 거기 넣으면 다음 복사가
  지운다(DECISIONS §5). 거기 남긴 차이는 `# seshat:` 을 단 한 줄뿐이다.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MASTER = ROOT / "docs/now/MASTER.md"
# 규칙 번호를 가리킬 수 있는 문서. 늘리는 것이지 줄이는 것이 아니다
DOCS = ("docs/README.md", "docs/now/MASTER.md", "docs/now/related.md", "docs/now/grammar.md",
        "docs/next/PLAN.md", "docs/next/hypotheses.md", "docs/next/papers.md",
        "docs/why/DECISIONS.md")


def 규칙들(master: str, fails: list) -> dict[int, list[int]]:
    """절마다 규칙 번호. **코드 울타리 안의 `★` 는 주석이지 규칙이 아니다** — 세면 명령 예시가 규칙이 된다."""
    절, 안, 본 = None, False, {}
    for n, x in enumerate(master.splitlines(), 1):
        if x.startswith("```"):
            안 = not 안
            continue
        if 안:
            continue
        if (m := re.match(r"^## (\d+)\.", x)):
            절 = int(m.group(1))
        elif x.startswith("★ ") and 절 is not None:
            g = re.match(r"^★ §(\d+)-(\d+) ", x)
            if not g:
                fails.append(f"MASTER:{n} ★ 줄에 번호가 없다 — `★ §{절}-N` 꼴로 적는다(DECISIONS §230)")
                continue
            사는절, 번 = int(g.group(1)), int(g.group(2))
            if 사는절 != 절:
                fails.append(f"MASTER:{n} §{사는절}-{번} 이 §{절} 안에 있다 — 절 번호가 다르다")
            앞 = 본.get(사는절, [])
            if 번 in 앞:
                fails.append(f"MASTER:{n} §{사는절}-{번} 이 겹친다 — 번호는 영구 식별자다")
            elif 앞 and 번 <= 앞[-1]:
                fails.append(f"MASTER:{n} §{사는절}-{번} 이 오름차순이 아니다(앞이 {앞[-1]})")
            본.setdefault(사는절, []).append(번)
    return 본


def 가리킨_것(root: pathlib.Path, 있는: set[str], fails: list) -> None:
    """가리킨 `MASTER §N-M` 이 실재하나. **번호를 박는 값은 가리킬 수 있다는 것**이다.

    ★ **남의 저장소는 이름을 앞에 적는다**(`docs/README.md`) — `파이어레인 MASTER §18-1a` 와
      `thoth MASTER §7-4` 는 이쪽 규칙이 아니다. 새 저장소를 가리키기 시작하면 여기 더한다.
    """
    for f in DOCS:
        q = root / f
        if not q.exists():
            continue
        글 = q.read_text(encoding="utf-8")
        for n, 줄 in enumerate(글.splitlines(), 1):
            for m in re.finditer(r"(?<!파이어레인 )(?<!thoth )MASTER §(\d+)-(\d+)", 줄):
                if f"{m.group(1)}-{m.group(2)}" not in 있는:
                    fails.append(f"{f}:{n} 가 없는 MASTER §{m.group(1)}-{m.group(2)} 를 가리킨다")


def check(master: str, root: pathlib.Path | None = None) -> list[str]:
    fails: list[str] = []
    본 = 규칙들(master, fails)
    가리킨_것(root or ROOT, {f"{s}-{r}" for s, rs in 본.items() for r in rs}, fails)
    return fails


def _canary() -> None:
    """★ **아무것도 못 찾는 자와 고장 난 자는 구별되지 않는다.** 깨끗한 것은 통과하고 어긴 것은 걸린다."""
    좋 = "## 3. x\n\n★ §3-1 **하나.**\n★ §3-7 **결번은 정상이다.**\n"
    나쁨 = "## 3. x\n\n★ §3-1 **하나.**\n★ §3-1 **겹친다.**\n★ **번호가 없다.**\n"
    if 규칙들(좋, f0 := []) != {3: [1, 7]} or f0 or not 규칙들(나쁨, f1 := []) or len(f1) != 2:
        print(f"    ★ 카나리아가 죽었다 — {f0} · {f1}")
        sys.exit(2)


def main() -> int:
    _canary()
    if not MASTER.exists():
        print("    docs/now/MASTER.md 가 없다\n"
              "    문서 지도를 본다 : docs/README.md")
        return 1
    fails = check(MASTER.read_text(encoding="utf-8"))
    for f in fails:
        print(f"    {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    # ★ 위반(1)과 도구 고장(2)을 다른 코드로 끝낸다(DECISIONS §21)
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(2)
