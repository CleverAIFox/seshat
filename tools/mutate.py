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
★ **밖 — 반환 주석이 없으면 안 본다.** 꼴을 모르면 중립값을 못 고른다. 그 수도 같이 찍는다 —
  **못 잰 것을 0 으로 세지 않는다**(§172 · §258).
★ **밖 — 「살아남았다」 가 「나쁘다」 는 아니다.** 사소한 접근자는 붙들 값이 없을 수 있다.
  이 도구는 **볼 자리를 준다**(§163 의 `dupcheck` 와 같은 성질) — 다만 **지표와 검사가 거기
  있으면 그것은 빚이다.**
★ **원본을 반드시 되돌린다.** 끝에 해시로 대 보고 다르면 **소리친다** — 중간에 끊겨 망가진
  소스를 남기는 것이 이 도구의 가장 큰 위험이다.

★ **`try/finally` 는 신호를 안 막는다**(DECISIONS §287). 2026-10-04 에 이 도구를 `timeout`
  으로 끊었더니 `tools/check_docs.py` 가 **`ast.unparse` 결과로 남았다 — 주석 269줄이
  사라진 채로.** `git diff` 를 보고서야 알았고, 그 사이 다른 검사 넷이 빨개져서 **원인을
  엉뚱한 데서 찾았다.** `SIGINT` · `SIGTERM` 을 받아 되돌린다 — `SIGKILL` 은 못 막으므로
  **망가진 파일의 이름을 끝에 찍어 둔다.**

★ **좁혀 부르되 믿지 않는다**(DECISIONS §287). 한 판에 시험 전부를 돌려 **2.1시간**이었고
  그래서 MASTER 가 「관문이 아니다 — 손으로 돌린다」 고 적었다. **사슬 밖에 둔 검사는 사람이
  기억해야 돌고, 사람은 안 돌린다** — 2026-10-01 에 적은 「못 잰 41」 이 아무도 안 세는 사이
  **47 로 늘었다.**

  짝 시험(`tools/check_X.py` ↔ `tests/test_X.py`)만 돌리면 1.4초다. 그런데 **짝이 그 함수를
  붙드는 시험이라는 보장이 없다.** 좁힌 쪽이 조용한 것을 「붙드는 시험이 없다」 로 세면
  **거짓 양성**이다 — **2026-10-04 실측으로 99자리 중 26**이 그랬다(DECISIONS §287 이 정본).
  그래서 **짝이 울면 거기서 끝내고,
  안 울면 전부로 다시 확인한다.** 빠른 길은 **긍정만** 결론내고 부정은 느린 길이 낸다.

★ **관문이다**(§287). 종전에는 산 자리를 찍고 **언제나 0 으로 끝났다** — 장부가 비어 있는데도
  늘어도 아무 일이 없었다. 셋을 본다 : 산 자리는 **0** 이어야 하고, 못 잰 자리는 **늘면** 울고,
  잴 자리는 **줄면** 운다(양방향 — 안 그러면 주석을 떼어 잴 자리를 줄여 초록을 만든다).
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import pathlib
import re
import signal
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
# ★ **신호를 받아도 되돌린다**(§287). 지금 뚫어 놓은 파일과 그 원본을 들고 있다가
#   `SIGINT`/`SIGTERM` 에 되돌려 놓고 죽는다. 비어 있으면 뚫린 파일이 없다는 뜻이다.
_뚫린것: dict[pathlib.Path, str] = {}
# ★ **손잡이로는 모자랐다**(DECISIONS §319). 2026-10-22 에 `check_scope.py` 가 **`main` 의 몸이
#   `return 0` 으로 바뀐 채** 디스크에 남아 있었다 — 관문이 활짝 열린 채다. 까닭이 셋이다 :
#   막는 신호에 **`SIGHUP` 이 없었고**(창을 닫으면 그것이다), **되돌리는 손잡이 자체가 또
#   끊기며**, 남은 뒤에 **그것을 보는 자가 없었다.** 손잡이는 `SIGKILL` 도 못 막는다.
#   그래서 **디스크에 자국을 남긴다** — 다음 판이 그것을 보고 되돌린다.
남은자국 = ROOT / ".mutate-남은것.json"
# ★ **검사 술어가 `tools/` 에 산다.** 2026-10-01 터진 다섯 중 셋이 거기였다 — seshat/ 만 재면
#   **재는 쪽을 안 재는 것**이다(§172 와 같은 꼴)
볼곳 = ("seshat/*.py", "tools/*.py")
# ★ **양방향**(§287). 산 자리는 절대 0 이고, 못 잰 자리는 늘면 울고, **잴 자리는 줄면 운다** —
#   반환 주석을 떼면 그 함수가 조용히 검사 밖으로 나간다. 2026-10-01 → 10-04 에 못 잰 자리가
#   41 → 47 로 늘었는데 **아무도 안 셌다.**
MIN_잴것 = 492
MAX_못잴것 = 47
# ★ **장부**(§287). `verify.sh` 가 보는 범위에서 **지금 붙드는 시험이 없는 자리.** 늘면 막고,
#   갚으면 `--update` 가 줄인다 — `check_deadchecks` 와 같은 꼴(§255 · §258).
#
# ★ **`main` 이 넷이었다 — 하나 갚았다**(2026-10-19 · §307). 관문의 `main` 을 `return 0`
#   으로 바꿔도 아무도 안 운다 — 시험이 속 함수만 부르고 **도구를 통째로 돌려 보는 자리가
#   없다.** 「검사를 껐는데 초록」 의 가장 곧은 꼴이다. `seshat/serve.py::main` 은
#   `tests/test_serve.py` 가 **가짜 `serve` 로 들머리를 통째로 불러** 막았다. 남은 셋은
#   `tools/` 에 있고 아직 사슬 밖이다(PLAN #53).
# ★ **`check_prose` 술어 셋은 저장소가 깨끗해서 산다.** 지금 위반이 0 이라 `[]` 를 돌려줘도
#   맞는 답이다 — **가짜 입력으로 물어야** 문다(§287 · thoth §150 과 같은 자리).
# ★ **`check_size::_canary` 가 산다.** 카나리아를 붙드는 것이 없다 — 「도구가 고장났나」 를
#   보는 자가 고장나도 조용하다.
장부: frozenset[str] = frozenset({})
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


def 범위안(파일: str, 무늬: str | list[str]) -> bool:
    """`--only` 무늬에 드는가. **뚫을 자리와 장부를 같은 자로 거른다** — 두 곳이 각각
    거르면 갈린다(§287 · thoth §132).

    ★ **무늬가 여럿일 수 있다**(2026-10-19 · DECISIONS §307). 사슬이 `tools/check_*.py` 와
      `seshat/*.py` 둘을 보게 되면서 `--only` 가 **쌓이는 인자**가 됐다. 글자 하나를 받던
      옛 꼴도 그대로 받는다 — 시험과 부르는 자리가 둘 다 산다.
    """
    import fnmatch
    무늬들 = [무늬] if isinstance(무늬, str) else list(무늬)
    무늬들 = [x for x in 무늬들 if x]
    return not 무늬들 or any(fnmatch.fnmatch(파일, x) for x in 무늬들)


def 견준다(산것: list[str], 장부: frozenset[str]) -> tuple[list[str], list[str]]:
    """(장부에 없는 것, 장부에 있는데 이제 안 사는 것). **둘 다 낸다** — 늘면 막고 줄면 알린다.

    ★ 장부만 보면 **갚아도 아무도 모른다.** 갚은 것을 안 찍으면 장부는 영원히 안 줄고,
      줄지 않는 장부는 **영구 면제**가 된다(§258 이 절대 규칙으로 올린 까닭).
    """
    새것 = [x for x in 산것 if x not in 장부]
    갚음 = [x for x in sorted(장부) if x not in set(산것)]
    return 새것, 갚음


def 톱니(잴것: int, 못잴것: int) -> list[str]:
    """**재고 세는 일과 뚫는 일은 다르다**(§287). 뚫는 범위는 `--only` 로 좁혀도 **장부는 저장소
    전체의 것**이다 — 좁힌 판에서 톱니를 건너뛰면 사슬에서는 톱니가 영원히 안 돈다.

    ★ 순수 함수다. 저장소가 깨끗해도 **가짜 수로 물어 볼 수 있다** — 토트가 같은 모양의 돌연변이
      셋을 살려 보내고서야 배운 것이다(토트 §145 · §147 · §150).
    """
    난것 = []
    if 못잴것 > MAX_못잴것:
        난것.append(f"못 재는 자리가 {못잴것} 로 천장 {MAX_못잴것} 을 넘었다 — "
                    f"반환 주석을 달거나, 천장을 올린 까닭을 적는다")
    if 잴것 < MIN_잴것:
        난것.append(f"잴 자리가 {잴것} 로 바닥 {MIN_잴것} 아래다 — "
                    f"주석을 떼면 그 함수가 조용히 검사 밖으로 나간다")
    return 난것


def 짝시험(파일: str, root: pathlib.Path | None = None) -> list[str]:
    """그 파일의 짝 시험. 없으면 빈 목록 — **그러면 전부를 돌린다.**

    `tools/check_docs.py` → `tests/test_docs.py` · `seshat/mbr.py` → `tests/test_mbr.py`.
    `check_` 접두사는 떼고도 본다 — 저장소가 그 꼴을 쓴다.

    ★ **있는 것과 시험이 든 것은 다르다**(DECISIONS §296). 0 바이트 `tests/test_docs.py` 하나가
      이 자를 **도구 고장으로 멈춰 세웠다** — pytest 가 5(모은 시험이 0)로 끝나고, 위 `돌린다`
      의 가드가 그것을 옳게 「시험이 운 것이 아니다」 로 읽어 **거기서 그만뒀다.** 멈추는 쪽이
      거짓 초록보다 낫지만, **옳은 답은 짝이 아니라고 보고 전부로 재는 것**이다. 그래서 `def
      test` 가 **있는** 파일만 짝으로 센다 — 이름만 맞는 빈 껍데기는 짝이 아니다.
    """
    root = root or ROOT
    밑 = pathlib.Path(파일).stem
    쓸것 = [밑, 밑[6:]] if 밑.startswith("check_") else [밑]
    골랐다 = []
    for n in 쓸것:
        p = f"tests/test_{n}.py"
        f = root / p
        if f.exists() and "def test" in f.read_text(encoding="utf-8", errors="replace"):
            골랐다.append(p)
    for p in _들이는시험(파일, root):
        if p not in 골랐다:
            골랐다.append(p)
    return 골랐다


# ★ **이름 규약에 안 기댄다**(DECISIONS §302 · `PLAN #53`). `tests/test_X.py` 꼴은 **규약**이고,
#   규약은 지켜지는 동안만 참이다 — 그리고 지켜져도 **그 시험이 그 함수를 붙든다는 보장이 없다.**
#   실측으로 99 자리 중 21 이 그랬고, 그때마다 **전부(26초)로 다시 세느라** 느렸다.
# ★ **그 파일을 들이는 시험은 글자로 찾을 수 있다.** 이 저장소의 시험은 모듈을
#   `spec_from_file_location(…, "tools/X.py")` 나 `from seshat import X` 로 들인다 — 둘 다
#   **파일에 적혀 있다.** 손 목록이 아니라 파일에서 꺼내므로 시험이 늘면 저절로 따라온다.
# ★ **넓혀도 답은 안 바뀐다.** 빠른 길은 **긍정만** 결론내고(울면 붙드는 시험이 있다),
#   조용하면 전부로 다시 센다. 넓히는 것은 **느린 길로 가는 횟수**를 줄일 뿐이다.
_시험글: dict[str, str] = {}


def _들이는시험(파일: str, root: pathlib.Path) -> list[str]:
    """그 파일을 **들이는** 시험들. 이름이 아니라 글자로 찾는다."""
    쪽 = pathlib.Path(파일).as_posix()
    밑 = pathlib.Path(파일).stem
    꾸러미 = 쪽.split("/")[0]
    것 = []
    for f in sorted((root / "tests").glob("test_*.py")):
        글 = _시험글.get(f.name)
        if 글 is None:
            글 = _시험글[f.name] = f.read_text(encoding="utf-8", errors="replace")
        if "def test" not in 글:
            continue
        # ★ **「글에 나온다」 와 「들인다」 는 다르다.** `tests/test_mutate.py` 는 `"seshat/mbr.py"`
        #   를 **자기 시험의 입력으로** 적는다 — 그것을 짝으로 세면 상관없는 시험이 딸려 돌고,
        #   그 시험이 딴 까닭으로 울면 **「붙드는 시험이 있다」 로 잘못 센다.** 들이는 꼴만 센다.
        들인다 = (re.search(rf'ROOT\s*/\s*["\']{re.escape(쪽)}["\']', 글) is not None
                  or re.search(rf'spec_from_file_location\([^)]*{re.escape(쪽)}', 글) is not None
                  or (꾸러미 == "seshat"
                      and re.search(rf"from seshat import [^\n]*\b{re.escape(밑)}\b", 글) is not None))
        if 들인다:
            것.append(f"tests/{f.name}")
    return 것


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


# pytest 의 종료코드 — **1만 「시험이 울었다」 다**
#   0 전부 통과 · 1 실패 · 2 끊김 · 3 내부 오류 · 4 쓰는 법 틀림 · 5 모은 시험이 0
_울었다 = 1


def 돌린다(걸음: list[str]) -> bool:
    """시험이 **빨개지나**. 빨개지면 그 함수를 붙드는 시험이 있다.

    ★ **`!= 0` 으로 보면 도구 고장을 「물었다」 로 센다**(DECISIONS §287). 2026-10-04 에
      의존성 묶음을 안 깐 채로 돌렸더니 **수집 단계에서 죽어 종료코드가 2** 였고, 뚫은 자리
      전부가 「붙드는 시험이 있다」 로 찍혔다 — **첫 판이 「99자리 · 산 자리 0」 이고 고친 판이
      9** 였다(2026-10-04 · DECISIONS §287). 저장소는 §21 · §232
      에서 「위반과 도구 고장을 다른 코드로」 를 이미 적고 있는데 **부르는 쪽이 그것을 안
      지켰다.**
    ★ **5(모은 시험이 0)가 좁혀 부르기의 함정이다.** 짝 시험의 이름이 틀리면 pytest 는 5 로
      끝나고, `!= 0` 은 그것도 「물었다」 로 센다 — 이름 하나 틀리면 그 자리가 안 보인다.
    ★ **밖 — 마지막 줄의 `== _울었다` 는 돌연변이가 물 수 없다.** 위 가드가 이미 `{0, 1}` 로
      좁혀 놓아 `!= 0` 과 **증명 가능하게 같다.** 관문이 아니라 **독립성**이므로 선언하지
      않는다 — 적어 두지 않으면 다음 사람이 다시 물려 보려다 시간을 버린다.
    """
    # ★ **뚫린 동안 바이트코드를 남기지 않는다**(§289). 막는 것이 치우는 것보다 싸다.
    r = subprocess.run(걸음, cwd=ROOT, capture_output=True, text=True,
                       env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    if r.returncode not in (0, _울었다):
        print(f"\n    ★ **pytest 가 {r.returncode} 로 끝났다 — 시험이 운 것이 아니라 도구가"
              f" 깨졌다.**\n       {' '.join(걸음)}\n"
              f"       의존성 묶음을 깐다 : uv sync --group eval\n"
              f"{r.stdout[-700:]}", file=sys.stderr)
        raise SystemExit(2)
    # ★ **건너뛴 시험은 안 문다**(§289). 의존성이 없는 기계에서 `skip` 된 시험은 통과로
    #   끝나므로 **「약해서 안 물었다」 와 구별이 안 된다** — thoth CI 가 그렇게 빨개졌고
    #   두 실패(돌연변이 · 문서 건수)가 **한 원인**이었다.
    if r.returncode == 0 and "skipped" in r.stdout and " passed" not in r.stdout:
        print("    ★ 시험이 **전부 건너뛰어졌다** — 건너뛴 시험은 안 문다.\n"
              "       깐다 : uv sync --group eval\n"
              f"       그 뒤 다시 : {' '.join(걸음)}", file=sys.stderr)
        raise SystemExit(2)
    return r.returncode == _울었다


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
    # ★ **자국이 안 읽히면 지난 판의 뚫린 파일을 영영 못 찾는다**(DECISIONS §319).
    #   합성으로 셋을 묻는다 — 없을 때 조용한가 · 있을 때 읽는가 · 신호 목록에 HUP 이 드는가.
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        자국 = pathlib.Path(d) / "자국.json"
        if 지난판이_남긴것(자국):
            print("    ★ 카나리아가 죽었다 — 자국이 없는데 있다고 한다"); sys.exit(2)
        자국.write_text('{"a.py": "원본"}', encoding="utf-8")
        if 지난판이_남긴것(자국) != {"a.py": "원본"}:
            print("    ★ 카나리아가 죽었다 — 자국을 못 읽는다"); sys.exit(2)
        자국.write_text("깨진 글", encoding="utf-8")
        if 지난판이_남긴것(자국):
            print("    ★ 카나리아가 죽었다 — 깨진 자국을 자국으로 센다"); sys.exit(2)
    if hasattr(signal, "SIGHUP") and signal.SIGHUP not in _막을신호():
        print("    ★ 카나리아가 죽었다 — SIGHUP 을 안 막는다(창을 닫으면 그것이다)")
        sys.exit(2)


def _바이트코드를_버린다(파일: pathlib.Path) -> None:
    """★ **길이가 같은 바꿈은 `__pycache__` 를 중독시킨다**(DECISIONS §289 · thoth §157).

    파이썬은 소스의 **크기와 mtime** 으로 캐시를 쓴다. 둘 다 같으면 **되돌린 뒤에도 뚫린
    바이트코드를 다시 쓴다** — 해시로 소스를 확인해도 안 잡힌다. 소스는 멀쩡하기 때문이다.

    ★ **이 자는 몸통을 통째로 `return <중립값>` 으로 바꾸므로** 길이가 같아지기 쉽다 —
      한 줄짜리 함수가 특히 그렇다. thoth 에서 `return 3` → `return 0` 으로 실제로 났고,
      시험 하나가 **설명 없이** 틀려 두 기계에서 각각 진단에 시간을 썼다.
    ★ **그 뒤의 모든 판정이 거짓이 된다** — 한 판이 끝난 뒤 사람이 돌리는 시험까지.
    """
    for q in 파일.parent.glob(f"__pycache__/{파일.stem}.*.pyc"):
        q.unlink(missing_ok=True)


def _이름(p: pathlib.Path) -> str:
    """보기 좋은 이름. ★ **되돌리는 길에서 이름 때문에 죽지 않는다** — `relative_to` 는
    ROOT 밖 경로에 `ValueError` 를 던지고, 그러면 **남은 파일을 못 되돌린다.**"""
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def _막을신호() -> list[int]:
    """되돌릴 틈을 주는 신호들. **`SIGHUP` 이 빠져 있었다**(DECISIONS §319) — 창을 닫으면
    그것이고, 그때는 아무도 안 되돌렸다. 윈도에 없는 것은 조용히 뺀다."""
    것 = []
    for 이름 in ("SIGINT", "SIGTERM", "SIGHUP", "SIGQUIT"):
        s = getattr(signal, 이름, None)
        if s is not None:
            것.append(s)
    return 것


def _자국을_남긴다() -> None:
    """지금 뚫어 둔 것을 디스크에 적는다. **`SIGKILL` 도 이것은 못 지운다.**"""
    try:
        남은자국.write_text(json.dumps({str(k): v for k, v in _뚫린것.items()},
                                     ensure_ascii=False), encoding="utf-8")
    except OSError as e:                      # 자국을 못 남겨도 본일은 돈다
        print(f"    ※ 자국을 못 남겼다({e}) — 끊기면 손으로 되돌린다", file=sys.stderr)


def _자국을_치운다() -> None:
    남은자국.unlink(missing_ok=True)


def 지난판이_남긴것(자국: pathlib.Path | None = None) -> dict[str, str]:
    """지난 판이 **안 끝났으면** 그때 뚫린 파일과 원본. 없으면 빈 것.

    ★ **밖 — 자국이 없으면 「없다」 가 아니라 「모른다」 다.** 자국을 못 남긴 채 죽었으면
      이 자도 못 본다. 그때 남는 길은 `git status` 뿐이다(2026-10-22 에 그랬다).
    ★ **밖 — 원본이 맞는지는 못 본다.** 자국이 든 글을 그대로 되돌린다.
    """
    자국 = 자국 or 남은자국
    if not 자국.is_file():
        return {}
    try:
        것 = json.loads(자국.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return 것 if isinstance(것, dict) else {}


def 지난판을_되돌린다() -> list[str]:
    """지난 판이 남긴 것을 되돌린다. **되돌린 이름들** — 비면 남은 것이 없었다."""
    것 = 지난판이_남긴것()
    되돌린것 = []
    for 자리, 원 in 것.items():
        p = pathlib.Path(자리)
        try:
            if p.is_file() and p.read_text(encoding="utf-8") != 원:
                p.write_text(원, encoding="utf-8")
                _바이트코드를_버린다(p)
                되돌린것.append(_이름(p))
        except OSError as e:
            print(f"    ★ **{자리} 를 못 되돌렸다**({e}) : git checkout -- {자리}", file=sys.stderr)
    if 것:
        _자국을_치운다()
    return 되돌린것


def _되돌리고_죽는다(signum: int, _frame: object) -> None:
    """★ **끊겨도 소스를 남기지 않는다.** `finally` 는 신호에 안 돈다.

    ★ **한 파일이 실패해도 나머지를 끝까지 되돌린다.** 되돌리는 길에서 예외가 새면
      그 뒤의 파일이 뚫린 채로 남는다 — 이 함수가 막으려던 바로 그 상태다.
    """
    # ★ **되돌리는 동안에는 더 안 끊긴다**(DECISIONS §319). 2026-10-22 에 이 손잡이가
    #   **제가 돌다가 또 끊겼다** — Ctrl-C 를 한 번 더 누르면 그 자리에서 죽고 남은 파일이
    #   뚫린 채 남는다. 되돌리기는 **끝까지 돈다.**
    for _sig in _막을신호():
        try:
            signal.signal(_sig, signal.SIG_IGN)
        except (OSError, ValueError) as e:
            print(f"\n    ※ 신호 {_sig} 를 못 막았다({e}) — 되돌리는 중에 또 끊길 수 있다",
                  file=sys.stderr)
    for p, 원 in list(_뚫린것.items()):
        try:
            p.write_text(원, encoding="utf-8")
            _바이트코드를_버린다(p)
            print(f"\n    신호 {signum} — {_이름(p)} 을 되돌렸다", file=sys.stderr)
        except Exception as e:
            print(f"\n    ★ 신호 {signum} — **{_이름(p)} 을 못 되돌렸다**({e}) : "
                  f"git checkout -- {_이름(p)}", file=sys.stderr)
    _자국을_치운다()
    sys.exit(130)


def main(argv: list[str] | None = None) -> int:
    for _sig in _막을신호():
        try:
            signal.signal(_sig, _되돌리고_죽는다)
        except (OSError, ValueError) as e:
            print(f"    ※ 신호 {_sig} 에 손잡이를 못 걸었다({e}) — 그 신호로 끊기면 "
                  f"뚫린 채 남는다. 자국이 다음 판에 그것을 든다", file=sys.stderr)
    ap = argparse.ArgumentParser()
    # ★ **쌓인다**(§307). 사슬이 `tools/check_*.py` 와 `seshat/*.py` 둘을 본다 —
    #   값 하나짜리면 뒤엣것만 먹고 **앞엣것이 조용히 범위 밖**이 된다.
    ap.add_argument("--only", action="append", default=[],
                    help="이 무늬만 — 여러 번 줄 수 있다. 비우면 전부")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    # ★ **훅이 쓴다**(DECISIONS §319). 뚫린 파일을 커밋하면 **관문이 열린 채 역사에 박힌다.**
    ap.add_argument("--남은것", action="store_true",
                    help="지난 판이 남긴 것이 있으면 이름을 대고 1 로 끝난다 (안 되돌린다)")
    ap.add_argument("--tests", default="tests", help="돌릴 시험")
    ap.add_argument("--full", action="store_true",
                    help="짝 시험을 안 쓰고 언제나 전부 돌린다 (느리다 — 짝짓기를 의심할 때)")
    a = ap.parse_args(sys.argv[1:] if argv is None else argv)
    # ★ **되돌리기보다 먼저 묻는다**(DECISIONS §319). 1판은 되돌린 **뒤에** 물어서 늘 0
    #   이었다 — 그러면 훅이 못 막고, **인덱스에 이미 올라간 돌연변이는 그대로 커밋된다.**
    #   이 깃발은 **안 되돌린다** : 고치는 일과 막는 일을 한 호출에 섞지 않는다.
    if a.남은것:
        것 = 지난판이_남긴것()
        if not 것:
            return 0
        print(f"    ✗ **지난 돌연변이 판이 안 끝났다** — {len(것)} 파일이 뚫린 채일 수 있다:",
              file=sys.stderr)
        for 자리 in 것:
            print(f"      {자리}", file=sys.stderr)
        print("      되돌린다 : python3 tools/mutate.py --list >/dev/null\n"
              "      또는     : git checkout -- <위 파일들>\n"
              "      **되돌린 뒤에 `git add` 를 다시 한다** — 인덱스에는 뚫린 것이 올라가 있다",
              file=sys.stderr)
        return 1
    # ★ 손잡이가 못 막은 지난 판을 여기서 되찾는다(DECISIONS §319).
    되돌린것 = 지난판을_되돌린다()
    if 되돌린것:
        print(f"    ★ **지난 판이 안 끝났다** — {' · '.join(되돌린것)} 을 되돌렸다.\n"
              f"      그 사이에 그 파일(들)은 **뚫린 채**였다 — 커밋했으면 git 으로 본다 :\n"
              f"        git log -p -1 -- {' '.join(되돌린것)}", file=sys.stderr)
    _canary()
    if a.selftest:
        print("  프로브 살아 있다 — 몸통을 지우고 머리말을 남기고 꼴을 읽는다")
        return 0

    잰다, 못잰다 = 잴것()
    온잰다, 온못잰다 = len(잰다), len(못잰다)   # ★ 좁히기 **전**의 수가 장부의 정본이다
    if a.only:
        # ★ 무늬를 받는다 — `tools/check_*.py` 처럼 **사슬에 넣을 범위**를 한 줄로 고른다
        잰다 = [x for x in 잰다 if 범위안(x[0], a.only)]
        못잰다 = [x for x in 못잰다 if 범위안(x.split("::")[0], a.only)]
    if a.list:
        print(f"  잴 수 있는 자리 {len(잰다)} · **반환 주석이 없어 못 재는 자리 {len(못잰다)}**")
        for 파일, 이름, 줄, v in 잰다:
            print(f"    {파일}:{줄:4} {이름:34} → {v}")
        return 0

    전부 = [sys.executable, "-m", "pytest", "-x", "-q", a.tests]
    산다, 느린길 = [], 0
    print(f"  {len(잰다)} 자리를 뚫어 본다 · 못 재는 자리 {len(못잰다)}(반환 주석 없음)", file=sys.stderr)
    for i, (파일, 이름, 줄, v) in enumerate(잰다, 1):
        f = ROOT / 파일
        원 = f.read_text(encoding="utf-8")
        앞해시 = hashlib.sha256(원.encode()).hexdigest()
        짝 = [] if a.full else 짝시험(파일)
        _뚫린것[f] = 원
        _자국을_남긴다()
        try:
            f.write_text(지운다(원, 이름, v), encoding="utf-8")
            # ★ **빠른 길은 긍정만 낸다.** 짝이 울면 붙드는 시험이 있는 것이 확실하다.
            물었나 = 돌린다([*전부[:-1], *짝]) if 짝 else False
            if not 물었나:
                # ★ 짝이 조용한 것은 **「없다」 가 아니라 「짝이 아니다」** 일 수 있다 — 전부로 센다
                if 짝:
                    느린길 += 1
                물었나 = 돌린다(전부)
            if not 물었나:
                # ★ **막는 자리에는 넘는 길을 같이 적는다**(DECISIONS §210). 한 자리를 보려면
                #   `python3 tools/mutate.py --only <파일>` 로 좁혀 다시 돌린다.
                산다.append(f"{파일}::{이름}  (몸통을 `return {v}` 로 바꿔도 통과)")
                print(f"    ✗ {파일}::{이름}"
                      f"  — 좁혀 본다 : python3 tools/mutate.py --only {파일}", file=sys.stderr)
        finally:
            f.write_text(원, encoding="utf-8")
            _바이트코드를_버린다(f)
            _뚫린것.pop(f, None)
            _자국을_치운다()
        if hashlib.sha256(f.read_text(encoding="utf-8").encode()).hexdigest() != 앞해시:
            print(f"    ★ **{파일} 을 못 되돌렸다** — git 으로 되돌린다 : git checkout -- {파일}",
                  file=sys.stderr)
            return 2
        if i % 25 == 0:
            print(f"    … {i}/{len(잰다)} (전부로 다시 센 것 {느린길})", file=sys.stderr)

    print(f"\n  붙드는 시험이 없는 자리 **{len(산다)}** / 잰 {len(잰다)} "
          f"· 못 잰 {len(못잰다)}(반환 주석 없음) · 전부로 다시 센 것 {느린길}")
    for x in 산다:
        print(f"    {x}")
    이름만 = [x.split("  ")[0] for x in 산다]
    # ★ **장부도 같은 범위로 좁힌다**(§287). 안 좁히면 `--only` 로 돈 판에서 범위 **밖**
    #   항목이 전부 「갚았다」 로 보이고, `--update` 가 그것을 지워 **장부가 조용히 비워진다.**
    본장부 = frozenset(x for x in 장부 if 범위안(x.split("::")[0], a.only))
    새것, 갚음 = 견준다(이름만, 본장부)
    난것 = [f"장부에 없는 자리 — 붙드는 시험이 없다 : {x}" for x in 새것]
    if 갚음:
        # ★ **갚은 것은 실패가 아니라 할 일이다.** 안 찍으면 장부는 영원히 안 줄고
        #   줄지 않는 장부는 영구 면제가 된다(§258).
        print(f"\n  ※ 갚았다 {len(갚음)} — 장부에서 지운다 : tools/mutate.py 의 `장부`")
        for x in 갚음:
            print(f"      {x}")
    # ★ **좁혀 뚫어도 장부는 전체로 센다**(§287). 사슬은 `--only` 로 도므로 여기서 건너뛰면
    #   톱니가 영원히 안 돈다 — 「검사를 더했다」 와 「검사가 문다」 의 그 자리다.
    난것 += 톱니(온잰다, 온못잰다)
    if 온못잰다 < MAX_못잴것 or 온잰다 > MIN_잴것:
        print(f"\n  ※ 좋아졌다 — MIN_잴것 을 {온잰다} 로, MAX_못잴것 을 {온못잰다} 로 내린다")
    if 난것:
        print()
        for x in 난것:
            print(f"    {x}")
        return 1
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
