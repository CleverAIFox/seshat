r"""**검사가 죽어 있지 않은가** — 죽은 이름이 아니라 **죽은 검사**를 본다(DECISIONS §255).

  python3 tools/check_deadchecks.py           # 장부보다 늘면 1
  python3 tools/check_deadchecks.py --list    # 지금 자리를 전부 찍는다
  python3 tools/check_deadchecks.py --update  # 갚은 만큼 장부를 줄인다

★ **`tools/check_dead.py` 와 다른 물음이다.** 그쪽은 「아무도 안 부르는 **이름**」 을 보고 이쪽은
  「아무것도 안 잡는 **검사**」 를 본다. 2026-10-01 §240 이 파이어레인의 `deadcheck` 를 옮겼다고
  적었는데 **옮긴 것은 앞엣것이었다** — 이름만 같고 묻는 것이 달랐다(§255).
★ **이것이 이 저장소가 밤새 겪은 병이다.** 조용히 빠지는 자리는 **무효로도 안 뜬다** —
  §243(한글 이름이 지문 밖으로 나갔다) · §248(탐침이 거짓 빨강을 냈다) · §244(자마다 못 매기는 줄이
  다르다). **초록이 「깨끗하다」 인지 「안 봤다」 인지 가르는 것이 이 자의 일이다.**

보는 것 넷.

| | 무엇 | 왜 |
|---|---|---|
| **무검증 시험** | `assert` · `raises` · `warns` 가 하나도 없는 `test_*` | **몸통을 지워도 통과한다** |
| **건너뛴 시험** | `skip` · `skipif` · `xfail` · `importorskip` | 안 도는 시험은 **없는 시험**이다 |
| **삼킨 예외** | `except …: pass` · 몸이 `pass`/`continue` 뿐 | 고장이 **자국을 안 남긴다** |
| **빈 그물** | `parametrize` 의 목록이 비었다 | 돌긴 도는데 **한 판도 안 돈다** |

★ **밖 — 「무엇을 검사하는지」 는 안 본다.** `assert` 가 있으면 산 것으로 센다. **약한 단언**
  (`assert x is not None` 하나로 끝나는 것)은 이 자의 밖이고 사람이 읽는다.
★ **밖 — 시험 밖의 죽은 검사는 안 본다.** 늘 참인 조건 · 안 닿는 분기는 못 잡는다.
★ **라쳇이다.** 자리마다 판단이 다르다 — `except: continue` 가 **옳은 자리**가 있다(못 읽는 파일을
  건너뛰는 훑개). 그래서 **한 판에 다 못 갚고**, §233 의 규칙대로 **라쳇이 값을 한다.**
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
볼곳 = ("tests/*.py", "tools/*.py", "seshat/*.py")
시험곳 = "tests/"
단언하는말 = {"raises", "warns", "fail", "approx"}

# ★ **장부**(2026-10-01 · DECISIONS §255). 지금 있는 자리를 적어 두고 **늘면 막는다.**
#   자리마다 판단이 달라 한 판에 다 못 갚는다 — 갚을 때마다 `--update` 로 줄인다.
#   **늘리지 않는다.**
장부: frozenset[str] = frozenset({
    "seshat/backends.py:146",
    "seshat/catalog.py:231",
    "seshat/catalog.py:237",
    "seshat/serve.py:102",
    "tests/test_mbr.py:9",
    "tests/test_qe.py:149",
    "tools/check_dead.py:59",
    "tools/check_docs.py:294",
    "tools/dupcheck.py:133",
    "tools/dupcheck.py:65",
    "tools/dupcheck.py:87",
    "tools/sweep.py:88",
})


def _글들(root: pathlib.Path) -> dict[pathlib.Path, str]:
    난것 = {}
    for g in 볼곳:
        for p in sorted(root.glob(g)):
            if p.is_file():
                난것[p] = p.read_text(encoding="utf-8")
    return 난것


def _단언하나(n: ast.AST) -> bool:
    """`assert` 나 `pytest.raises` 류가 하나라도 있나. **`with` 만으로는 안 센다.**"""
    for x in ast.walk(n):
        if isinstance(x, ast.Assert):
            return True
        if isinstance(x, ast.Call) and getattr(x.func, "attr", "") in 단언하는말:
            return True
        if isinstance(x, ast.Raise):        # 시험이 스스로 터뜨리는 자리(else: raise AssertionError)
            return True
    return False


def 죽은검사(root: pathlib.Path | None = None) -> list[tuple[str, str]]:
    """(자리, 무엇). 자리는 `파일:줄` 또는 `파일::이름` — **장부의 열쇠다.**"""
    root = root or ROOT
    난것: list[tuple[str, str]] = []
    for p, 글 in _글들(root).items():
        이름 = p.relative_to(root).as_posix()
        try:
            나무 = ast.parse(글)
        except SyntaxError as e:
            # ★ **건너뛰되 말을 한다.** 조용히 건너뛰면 **못 읽은 파일이 깨끗한 파일로 보인다** —
            #   이 도구가 잡으려는 바로 그 병이다(DECISIONS §255)
            print(f"    ※ {이름} 을 못 읽었다 — {e.__class__.__name__}: {e}. **이 파일은 안 봤다**",
                  file=sys.stderr)
            continue
        시험파일 = 이름.startswith(시험곳)
        for n in ast.walk(나무):
            if 시험파일 and isinstance(n, ast.FunctionDef) and n.name.startswith("test"):
                if not _단언하나(n):
                    난것.append((f"{이름}::{n.name}",
                                 "무검증 시험 — **몸통을 지워도 통과한다.** 무엇을 잡는지 "
                                 "`assert` 로 적는다"))
            if isinstance(n, ast.ExceptHandler) and all(
                    isinstance(x, (ast.Pass, ast.Continue)) for x in n.body):
                난것.append((f"{이름}:{n.lineno}",
                             "삼킨 예외 — 고장이 **자국을 안 남긴다.** 건너뛰는 것이 옳아도 "
                             "**한 줄은 찍는다** — 주석은 이 자가 못 읽는다(DECISIONS §255)"))
            if isinstance(n, ast.Call):
                a = getattr(n.func, "attr", "")
                if a in ("skip", "skipif", "xfail"):
                    난것.append((f"{이름}:{n.lineno}",
                                 f"건너뛴 시험(`{a}`) — **안 도는 시험은 없는 시험이다**"))
                elif a == "importorskip":
                    난것.append((f"{이름}:{n.lineno}",
                                 "건너뛴 시험(`importorskip`) — 없는 기계에서 **조용히 0 건이 된다**"))
                elif a == "parametrize" and n.args and isinstance(
                        n.args[-1], (ast.List, ast.Tuple)) and not n.args[-1].elts:
                    난것.append((f"{이름}:{n.lineno}",
                                 "빈 그물 — `parametrize` 가 비었다. **한 판도 안 돈다**"))
    return sorted(난것)


def 견준다(지금: list[tuple[str, str]], 장부: frozenset[str]) -> list[str]:
    """**새로 생긴 것만** 말한다. 갚은 것은 잘한 일이지 실패가 아니다."""
    return [f"{자리} — {왜}" for 자리, 왜 in 지금 if 자리 not in 장부]


def _canary() -> None:
    """★ **제 규칙을 스스로 안 지키는 검사는 농담이다.** 판별식이 사는지 합성으로 묻는다."""
    나무 = ast.parse("def test_빈():\n    x = 1\n\ndef test_찬():\n    assert 1\n")
    빈, 찬 = 나무.body[0], 나무.body[1]
    if _단언하나(빈) or not _단언하나(찬):
        print("    ★ 카나리아가 죽었다 — 무검증 시험을 못 가른다")
        sys.exit(2)
    삼킴 = ast.parse("try:\n    pass\nexcept Exception:\n    pass\n").body[0].handlers[0]
    말함 = ast.parse("try:\n    pass\nexcept Exception:\n    print(1)\n").body[0].handlers[0]
    if not all(isinstance(x, (ast.Pass, ast.Continue)) for x in 삼킴.body) or all(
            isinstance(x, (ast.Pass, ast.Continue)) for x in 말함.body):
        print("    ★ 카나리아가 죽었다 — 삼킨 예외를 못 가른다")
        sys.exit(2)
    if not re.match(r"^tests/", 시험곳 + "x.py"):
        print("    ★ 카나리아가 죽었다 — 시험 파일의 자리가 바뀌었다")
        sys.exit(2)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    _canary()
    지금 = 죽은검사()
    if "--list" in args:
        print(f"  죽은 검사 {len(지금)}")
        for 자리, 왜 in 지금:
            print(f"    {자리:56} {왜}")
        print("\n  ※ 이 목록은 **할 일**이지 실패가 아니다. 하나 고칠 때마다 `--update` 로 장부를 줄인다")
        return 0
    늘었나 = 견준다(지금, 장부)
    if "--update" in args:
        새 = "\n".join(f'    "{자리}",' for 자리, _ in 지금)
        print(f"  장부를 이렇게 바꾼다 — 지금 {len(지금)} · 장부 {len(장부)}\n"
              f"장부: frozenset[str] = frozenset({{\n{새}\n}})")
        return 1 if 늘었나 else 0
    for x in 늘었나:
        print(f"    ✗ {x}", file=sys.stderr)
    if 늘었나:
        print(f"      죽은 검사가 {len(장부)} → {len(지금)} 로 늘었다. **초록이 「깨끗하다」 인지 "
              f"「안 봤다」 인지 가르는 자리다**(DECISIONS §255)\n"
              f"      전부 본다 : python3 tools/check_deadchecks.py --list", file=sys.stderr)
        return 1
    print(f"  죽은 검사 {len(지금)} / 장부 {len(장부)}")
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
