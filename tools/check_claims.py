r"""**강제자라고 선언한 함수가 제 밖을 적었나**(DECISIONS §267).

  python3 tools/check_claims.py            장부보다 늘면 1
  python3 tools/check_claims.py --list     지금 자리를 전부 찍는다
  python3 tools/check_claims.py --update   갚은 만큼 장부를 줄인다

★ **검사가 틀리는 것이 검사가 없는 것보다 나쁘다.** 2026-10-01 하루에 다섯 번, 검사가 **있는데
  통과**했다(§263 · §265 · §266). 그날 뮤테이션으로 재 보니 `seshat/` 과 `tools/` 의 함수
  **377 중 377** 이 시험에 붙들려 있었다 — **구현은 선언대로였다.** 틀린 것은 **선언이 좁은데
  이름이 넓은 것**이다. `RESIDUE` 는 `T\d+` **꼴**만 보면서 「잔재」 라는 이름을 달았다.
★ **`tools/check_scope.py` 가 이 병을 위해 있는데 관문 16 만 본다.** 지표도 되돌리기도 그 자의
  밖이다 — 이 자가 그 자리를 든다. **DECISIONS 가 「강제자」 로 든 함수**를 본다. 저장소가
  **스스로 「이것이 막는다」 고 선언한** 자리이고, 그 선언에는 **무엇을 안 막는지**가 붙어야 한다.
★ **밖을 적는 자리는 함수 머리말이나 모듈 머리말이다.** 모듈이 적으면 그 파일의 함수는 다 된다 —
  `RESIDUE` 처럼 **파일 하나가 한 규칙**인 자리가 많다.
★ **밖 — 밖이 옳은지는 안 본다.** 「안 본다」 가 적혀 있으면 산 것으로 센다. **적은 밖이 실제
  범위와 맞는지는 사람이 읽는 일**이고, 이 자는 **적었나**만 묻는다.
★ **밖 — DECISIONS 가 안 든 함수는 안 본다.** 모든 함수에 밖을 요구하면 **거짓 양성이 쏟아지고
  사람이 검사를 끈다**(§213). 선언한 것에만 책임을 묻는다.
★ **라쳇이다.** 자리마다 판단이 다르다 — `main` 처럼 **밖이 없는 것이 맞는** 자리가 있다.
  §233 의 규칙대로 **늘면 막고**, 갚을 때마다 `--update` 로 줄인다. **늘리지 않는다.**
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
대장 = ROOT / "docs/DECISIONS.md"
# 강제자 줄에서 뽑는 꼴 — `파일::이름`
자리꼴 = re.compile(r"`((?:seshat|tools)/[\w./-]+\.py)::([\w가-힣_]+)`")
# 「무엇을 안 보는가」 를 말하는 말. **넓히면 거짓 초록이 된다**
밖말 = ("안 본다", "못 본다", "밖이", "밖 —", "안 센다", "안 묻는다", "못 잡는다", "안 잡는다",
        "못 센다", "안 받는다", "못 가른다")

# ★ **장부**(2026-10-01 · DECISIONS §267). 지금 밖을 안 적은 자리를 적어 두고 **늘면 막는다.**
#
# ★ **2026-10-03 일곱을 다 갚아 0 이 됐다**(DECISIONS §286). 종전 주석은 「`main` 처럼 밖이
#   없는 것이 맞는 자리가 있어 한 판에 다 못 갚는다」 였는데 **그것이 틀렸다** — `main` 에도
#   밖이 있었다(「판정하지 않는다」 · 「레이크에 안 넣는다」). **「밖이 없는 함수」 는 대개
#   「밖을 아직 안 생각한 함수」** 다.
# ★ **0 이 된 장부는 지우지 않는다.** 비어 있는 채로 두면 **다음에 하나가 늘 때 그 줄이 보인다** —
#   지우면 「장부가 없다」 와 「장부가 비었다」 를 못 가른다.
장부: frozenset[str] = frozenset()


def 선언한_자리(글: str | None = None) -> set[tuple[str, str]]:
    """DECISIONS 의 「강제자」 줄이 든 (파일, 함수). **저장소가 스스로 든 것만** 본다."""
    글 = 글 if 글 is not None else 대장.read_text(encoding="utf-8")
    난것 = set()
    for 줄 in 글.splitlines():
        if "강제자" not in 줄:
            continue
        난것 |= {(m.group(1), m.group(2)) for m in 자리꼴.finditer(줄)}
    return 난것


def 밖을_적었나(f: pathlib.Path, 이름: str) -> str | None:
    """`None` 이면 적었다. 글자를 돌려주면 그것이 **까닭**이다."""
    if not f.exists():
        return "파일이 없다 — DECISIONS 가 없는 자리를 강제자로 든다"
    나무 = ast.parse(f.read_text(encoding="utf-8"))
    찾 = [n for n in ast.walk(나무)
          if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == 이름]
    if not 찾:
        return "함수가 없다 — 이름이 바뀌었거나 지워졌다"
    독 = (ast.get_docstring(찾[0]) or "") + "\n" + (ast.get_docstring(나무) or "")
    if any(w in 독 for w in 밖말):
        return None
    return "밖을 안 적었다 — **무엇을 안 보는지**가 머리말에 없다"


def 안한것(root: pathlib.Path | None = None, 글: str | None = None) -> list[tuple[str, str]]:
    """(자리, 까닭). 자리는 `파일::이름` — **장부의 열쇠다.**"""
    root = root or ROOT
    난것 = []
    for f, 이름 in sorted(선언한_자리(글)):
        왜 = 밖을_적었나(root / f, 이름)
        if 왜:
            난것.append((f"{f}::{이름}", 왜))
    return 난것


def 견준다(지금: list[tuple[str, str]], 장부: frozenset[str]) -> list[str]:
    """**새로 생긴 것만** 말한다. 갚은 것은 잘한 일이지 실패가 아니다."""
    return [f"{자리} — {왜}" for 자리, 왜 in 지금 if 자리 not in 장부]


def _canary() -> None:
    """★ **판별식이 죽으면 「다 적었다」 로 보인다** — 0 이 「깨끗하다」 인지 묻는다."""
    if 선언한_자리("강제자 — `seshat/x.py::f` · `tools/y.py::g`") != {("seshat/x.py", "f"), ("tools/y.py", "g")}:
        print("    ★ 카나리아가 죽었다 — 강제자 줄에서 자리를 못 뽑는다")
        sys.exit(2)
    if 선언한_자리("아무 줄 — `seshat/x.py::f`"):
        print("    ★ 카나리아가 죽었다 — 강제자 줄이 아닌 것을 든다")
        sys.exit(2)
    if not any(w in "★ **밖 — 뜻이 옳은지는 안 본다.**" for w in 밖말):
        print("    ★ 카나리아가 죽었다 — 밖말을 못 가른다")
        sys.exit(2)
    if any(w in "이 도구는 꼴과 겹침을 전부 검사한다" for w in 밖말):
        print("    ★ 카나리아가 죽었다 — 긍정문을 밖으로 센다")
        sys.exit(2)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    _canary()
    지금 = 안한것()
    if "--list" in args:
        전체 = len(선언한_자리())
        print(f"  강제자로 선언한 함수 {전체} · 밖을 안 적은 것 {len(지금)}")
        for 자리, 왜 in 지금:
            print(f"    {자리:48} {왜}")
        print("\n  ※ 이 목록은 **할 일**이지 실패가 아니다. 하나 갚을 때마다 `--update` 로 장부를 줄인다")
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
        print(f"      밖을 안 적은 강제자가 {len(장부)} → {len(지금)} 로 늘었다.\n"
              f"      ★ **검사가 틀리는 것이 검사가 없는 것보다 나쁘다**(DECISIONS §267) —\n"
              f"        이름이 넓고 선언이 좁으면 사람이 그 이름을 믿는다\n"
              f"      전부 본다 : python3 tools/check_claims.py --list", file=sys.stderr)
        return 1
    print(f"  강제자 {len(선언한_자리())} · 밖을 안 적은 것 {len(지금)} / 장부 {len(장부)}")
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
