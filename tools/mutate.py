r"""**몸통을 지워도 시험이 통과하나** — 붙드는 시험이 없는 함수를 센다(DECISIONS §267).

  python3 tools/mutate.py --only seshat/evaluate.py     한 파일만
  python3 tools/mutate.py --list                        잴 수 있는 자리를 찍는다
  python3 tools/mutate.py --selftest                    프로브가 살아 있나

★ **검사가 틀리는 것이 검사가 없는 것보다 나쁘다.** 2026-10-01 하루에 다섯 번, 검사가 **있는데
  통과**했다 — `RESIDUE` 는 `T\d+` 꼴만 보면서 「잔재」 라는 이름을 달았고, 시험 하나는 「둘이
  같은지」 만 보면서 「사본을 막는다」 로 읽혔다(§263 · §265 · §266). **다섯 번 다 손으로 뚫어
  보고 알았다.**
★ **`_canary` 는 「도구가 고장났나」 를 보고 이 자는 「도구를 붙드는 시험이 있나」 를 본다.**
  `check_deadchecks` 가 **시험**에 대해 묻는 「몸통을 지워도 통과하나」 를 **코드**에 대해 묻는다.
★ **꼴을 지키는 값으로 바꾼다.** `-> bool` 은 `True`, `-> list[...]` 는 `[]` 로 바꾼다.
  `None` 으로 바꾸면 `TypeError` 로 죽는데 **그 죽음은 시험이 값을 봤다는 뜻이 아니다** —
  꼴이 맞는 값으로 바꿔야 **살아남은 것이 진짜 살아남은 것**이다.
★ **밖 — 반환 주석이 없으면 안 잰다.** 꼴을 모르면 중립값을 못 고른다. 그 수도 같이 찍는다 —
  **못 잰 것을 0 으로 세지 않는다**(§172 · §258).
★ **밖 — 「살아남았다」 가 「나쁘다」 는 아니다.** 사소한 접근자는 붙들 값이 없을 수 있다.
  이 도구는 **볼 자리를 준다**(§163 의 `dupcheck` 와 같은 성질) — 다만 **지표와 검사가 거기
  있으면 그것은 빚이다.**
★ **원본을 반드시 되돌린다.** 끝에 해시로 대 보고 다르면 **소리친다** — 중간에 끊겨 망가진
  소스를 남기는 것이 이 도구의 가장 큰 위험이다.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
# ★ **검사 술어가 `tools/` 에 산다.** 2026-10-01 터진 다섯 중 셋이 거기였다 — seshat/ 만 재면
#   **재는 쪽을 안 재는 것**이다(§172 와 같은 꼴)
볼곳 = ("seshat/*.py", "tools/*.py")
# 반환 주석 → 꼴을 지키는 중립값
중립 = {"bool": "True", "int": "0", "float": "0.0", "str": '""', "bytes": 'b""',
        "list": "[]", "dict": "{}", "set": "set()", "tuple": "()"}


def _중립값(주석: ast.AST | None) -> str | None:
    """반환 주석이 말하는 꼴의 중립값. 모르면 `None` — **안 잰다.**"""
    if 주석 is None:
        return None
    if isinstance(주석, ast.Subscript):          # list[str] · dict[str, int]
        주석 = 주석.value
    if isinstance(주석, ast.BinOp):              # `str | None` — 왼쪽을 쓴다
        return _중립값(주석.left)
    이름 = 주석.id if isinstance(주석, ast.Name) else getattr(주석, "attr", "")
    if isinstance(주석, ast.Constant) and 주석.value is None:
        return "None"
    return 중립.get(이름)


def 잴것(root: pathlib.Path | None = None) -> tuple[list[tuple[str, str, int, str]], list[str]]:
    """(잴 수 있는 자리, 주석이 없어 못 재는 자리). 자리는 (파일, 이름, 줄, 중립값)."""
    root = root or ROOT
    잰다, 못잰다 = [], []
    for 무늬 in 볼곳:
        for f in sorted(root.glob(무늬)):
            if f.stem == "__init__":
                continue
            이름 = f.relative_to(root).as_posix()
            나무 = ast.parse(f.read_text(encoding="utf-8"))
            for n in 나무.body:
                if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if n.name.startswith("__"):
                    continue
                v = _중립값(n.returns)
                (잰다.append((이름, n.name, n.lineno, v)) if v else 못잰다.append(f"{이름}::{n.name}"))
    return 잰다, 못잰다


def 지운다(글: str, 이름: str, 값: str) -> str:
    """그 함수의 몸통을 `return <값>` 하나로 바꾼다. 머리말은 남긴다."""
    나무 = ast.parse(글)
    for n in ast.walk(나무):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == 이름:
            머리 = [n.body[0]] if (isinstance(n.body[0], ast.Expr)
                                   and isinstance(n.body[0].value, ast.Constant)) else []
            n.body = [*머리, ast.parse(f"return {값}").body[0]]
            ast.fix_missing_locations(나무)
            return ast.unparse(나무)
    raise SystemExit(f"{이름} 을 못 찾았다 — 그 파일의 최상위에 그 함수가 없다\n"
                     f"    잴 자리를 다시 본다 : python3 tools/mutate.py --list\n"
                     f"    한 파일만 : python3 tools/mutate.py --only <파일>")


def 돌린다(걸음: list[str]) -> bool:
    """시험이 **빨개지나**. 빨개지면 그 함수를 붙드는 시험이 있다."""
    r = subprocess.run(걸음, cwd=ROOT, capture_output=True, text=True)
    return r.returncode != 0


def _canary() -> None:
    """★ **지우는 일이 정말 지우나.** 몸통이 그대로 남으면 **전부 살아남았다고 찍는다.**"""
    글 = 지운다("def f(a: int) -> bool:\n    '''머리말.'''\n    return a > 3\n", "f", "True")
    if "a > 3" in 글 or "return True" not in 글:
        print("    ★ 카나리아가 죽었다 — 몸통이 안 지워진다")
        sys.exit(2)
    if "'''머리말.'''" not in 글 and "머리말" not in 글:
        print("    ★ 카나리아가 죽었다 — 머리말이 사라진다")
        sys.exit(2)
    if _중립값(ast.parse("def f() -> list[str]: ...").body[0].returns) != "[]":
        print("    ★ 카나리아가 죽었다 — 꼴을 못 읽는다")
        sys.exit(2)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="이 파일만 — 비우면 전부")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--tests", default="tests", help="돌릴 시험")
    a = ap.parse_args(sys.argv[1:] if argv is None else argv)
    _canary()
    if a.selftest:
        print("  프로브 살아 있다 — 몸통을 지우고 머리말을 남기고 꼴을 읽는다")
        return 0

    잰다, 못잰다 = 잴것()
    if a.only:
        잰다 = [x for x in 잰다 if x[0] == a.only]
        못잰다 = [x for x in 못잰다 if x.split("::")[0] == a.only]
    if a.list:
        print(f"  잴 수 있는 자리 {len(잰다)} · **반환 주석이 없어 못 재는 자리 {len(못잰다)}**")
        for 파일, 이름, 줄, v in 잰다:
            print(f"    {파일}:{줄:4} {이름:34} → {v}")
        return 0

    걸음 = [sys.executable, "-m", "pytest", "-x", "-q", a.tests]
    산다 = []
    print(f"  {len(잰다)} 자리를 뚫어 본다 · 못 재는 자리 {len(못잰다)}(반환 주석 없음)", file=sys.stderr)
    for i, (파일, 이름, 줄, v) in enumerate(잰다, 1):
        p = ROOT / 파일
        원 = p.read_text(encoding="utf-8")
        앞해시 = hashlib.sha256(원.encode()).hexdigest()
        try:
            p.write_text(지운다(원, 이름, v), encoding="utf-8")
            if not 돌린다(걸음):
                산다.append(f"{파일}::{이름}  (몸통을 `return {v}` 로 바꿔도 통과)")
                print(f"    ✗ {파일}::{이름}", file=sys.stderr)
        finally:
            p.write_text(원, encoding="utf-8")
        if hashlib.sha256(p.read_text(encoding="utf-8").encode()).hexdigest() != 앞해시:
            print(f"    ★ **{파일} 을 못 되돌렸다** — git 으로 되돌린다 : git checkout -- {파일}",
                  file=sys.stderr)
            return 2
        if i % 10 == 0:
            print(f"    … {i}/{len(잰다)}", file=sys.stderr)

    print(f"\n  붙드는 시험이 없는 자리 **{len(산다)}** / 잰 {len(잰다)} "
          f"· 못 잰 {len(못잰다)}(반환 주석 없음)")
    for x in 산다:
        print(f"    {x}")
    print("\n  ※ **「살아남았다」 가 「나쁘다」 는 아니다** — 사소한 접근자는 붙들 값이 없다.\n"
          "    그러나 **지표와 검사가 여기 있으면 그것은 빚이다**(DECISIONS §267)")
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
              "      소스가 망가졌을 수 있다 : git status --short seshat", file=sys.stderr)
        sys.exit(2)
