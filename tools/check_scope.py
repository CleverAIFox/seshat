r"""**관문이 제 범위와 생사를 선언하는가**(DECISIONS §239).

  python3 tools/check_scope.py            # 선언 안 한 관문이 있으면 1
  python3 tools/check_scope.py --list     # 무엇이 빠졌는지 찍는다

★ **범위가 이름보다 좁고 그것이 어디에도 안 적혀 있는 것**이 파이어레인이 여섯 번 반복해 겪은
  결함이다(그쪽 `tools/scopedecl.py`). 이름이 `check_docs` 인데 실제로는 문서 넷만 보면, 다섯째
  문서는 **검사 밖인데 아무도 모른다.**
★ 이 자가 보는 것은 둘이다.
  **① 밖** — 머리말이 **안 보는 것**을 말하는가. 「안 본다 · 못 본다 · 완전하지 않다 · 거짓 양성」
  같은 말이 머리말에 있어야 한다. **무엇을 보는가만 적힌 관문은 제 한계를 숨긴다.**
  **② 자가시험** — `_canary` 나 `--selftest` 로 **판별식이 살아 있는지**를 스스로 묻는가.
  **아무것도 못 찾는 자와 고장 난 자는 구별되지 않는다**(§211 · §180 이 같은 말을 한다).
★ **대상은 `tools/verify.sh` 가 `step` 으로 부르는 것뿐이다.** 도구 서른넷 전부를 보면 `rescore` ·
  `slice` 처럼 **관문이 아닌 것**까지 걸려 사람이 검사를 끈다 — 파이어레인이 같은 이유로 범위를
  좁게 잡는다. **목록을 손으로 안 든다** — `verify.sh` 에서 뽑는다.
★ **남의 저장소 사본은 뺀다** — 고치면 원본과 갈린다(§5). 손 목록이 아니라 **파일이 스스로
  말한다**(머리 세 줄의 「사본이다」).
★ **밖** — 선언이 **참인지는 못 본다.** 머리말에 그런 말이 있는지만 본다. 「밖 칸이 있다」 와
  「범위를 제대로 적었다」 는 다른 물음이고, 뒤쪽은 읽는 일이다.
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
# ★ **제 한계를 말하는 낱말.** 늘려도 되지만 **넓히면 거짓 초록**이 된다
밖말 = ("안 본다", "못 본다", "완전하지 않다", "안 잡는다", "보지 않는다", "안 센다",
        "뜻은 안", "거짓 양성", "안 가른다")
시험말 = ("_canary", "_selftest", "_프로브", "--selftest")


def 관문들(root: pathlib.Path | None = None) -> list[str]:
    """`verify.sh` 가 `step` 으로 부르는 `tools/*.py`. **손 목록을 안 만든다** — 실물에서 뽑는다."""
    root = root or ROOT
    글 = (root / "tools/verify.sh").read_text(encoding="utf-8")
    걸음 = "\n".join(x for x in 글.splitlines() if x.startswith("step "))
    return sorted(set(re.findall(r"tools/(\w+\.py)", 걸음)))


def 안한것(root: pathlib.Path | None = None) -> list[tuple[str, str]]:
    """(도구, 무엇이 빠졌나). 빠진 것이 둘이면 두 줄로 든다."""
    root = root or ROOT
    out = []
    for n in 관문들(root):
        p = root / "tools" / n
        if not p.is_file():
            out.append((n, "파일이 없다 — `verify.sh` 가 없는 도구를 부른다"))
            continue
        글 = p.read_text(encoding="utf-8")
        # ★ **남의 저장소 사본은 뺀다**(DECISIONS §5 · §239). 고치면 원본과 갈리고, 다음 복사가
        #   지운다. **손 목록이 아니라 파일이 스스로 말한다** — 머리 세 줄의 「사본이다」 를 본다
        if "사본이다" in "\n".join(글.splitlines()[:3]):
            continue
        나무 = ast.parse(글)
        독 = ast.get_docstring(나무) or ""
        if not any(w in 독 for w in 밖말):
            out.append((n, "머리말이 **안 보는 것**을 안 적는다 — 「… 는 안 본다」 를 한 줄 넣는다"))
        # ★ **글자가 아니라 정의를 본다**(DECISIONS §311). 종전에는 `"_canary" in 글` 이라
        #   **그 이름이 어디에 있든** 통과했다 — `check_ways.py` 는 `_canary` 를 **정의하지
        #   않는데** 파일 안에 그 글자가 있어서 초록이었다. 「모든 관문은 카나리아를 가진다」
        #   가 거짓 초록이었다. `ast` 로 **정의가 있나**를 묻는다.
        if not _정의가있나(나무, 시험말):
            out.append((n, "자가시험이 없다 — `_canary()` 로 판별식이 살아 있는지 스스로 묻는다"))
    return out


def _정의가있나(나무: ast.Module, 이름들) -> bool:
    """맨 위에 그 이름의 **함수 정의**가 있나. **글자가 있는 것과 다르다.**"""
    있는것 = {n.name for n in _맨위함수(나무)}
    return any(w.strip("`()") in 있는것 for w in 이름들)


def _맨위함수(나무: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """맨 위 함수 정의들. 속 함수는 안 센다 — 관문은 **제 몸에** 카나리아를 둔다."""
    return [n for n in 나무.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]


def _canary(root: pathlib.Path | None = None) -> None:
    """★ **제 규칙을 스스로 안 지키는 검사는 농담이다.** 판별식이 사는지 합성으로 묻는다."""
    if not 관문들(root):
        print("    ★ 카나리아가 죽었다 — `verify.sh` 에서 관문을 하나도 못 뽑았다")
        sys.exit(2)
    if any(w in "이 글은 무엇을 보는지만 적는다" for w in 밖말):
        print("    ★ 카나리아가 죽었다 — 밖을 안 적은 글을 적은 것으로 셌다")
        sys.exit(2)
    if not any(w in "def _canary():" for w in 시험말):
        print("    ★ 카나리아가 죽었다 — 자가시험이 있는 글을 없는 것으로 셌다")
        sys.exit(2)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    _canary()
    안 = 안한것()
    if "--list" in args or 안:
        for n, 왜 in 안:
            print(f"    tools/{n} — {왜}")
    if 안:
        print(f"    ✗ 선언 안 한 관문 {len(안)} — **범위가 이름보다 좁으면 그만큼이 검사 밖이다**"
              f"(DECISIONS §239)\n"
              f"      머리말에 한 줄 넣는다 : tools/<도구>.py\n"
              f"      무엇이 빠졌는지 다시 본다 : python3 tools/check_scope.py --list", file=sys.stderr)
        return 1
    print(f"  관문 {len(관문들())} — 전부 제 밖과 생사를 선언한다")
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
