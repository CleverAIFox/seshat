r"""**아무도 안 부르는 이름이 남아 있는가**(DECISIONS §240).

  python3 tools/check_dead.py            # 새로 생긴 죽은 이름이 있으면 1
  python3 tools/check_dead.py --list     # 지금 죽은 이름을 전부 찍는다

★ **죽은 코드는 틀린 코드보다 나쁘다.** 틀린 코드는 걸리지만 죽은 코드는 **읽힌다** — 사람이 그것을
  현행으로 믿고 고치고, 고친 것이 아무 데도 안 닿는다. 2026-09-30 `_josa_re` 가 그 자리였다:
  §158 이 「조사 목록은 하나뿐이다」 를 적으면서 만든 창구인데 **`josa()` 는 그것을 안 거치고
  `terms.josa_머리()` 를 직접 부른다.** 창구가 아니라 **장식**이었다.
★ **한 번만 나오는 이름이 죽은 이름이다.** 저장소 전체(코드 · 시험 · 문서 · 셸 · 워크플로)에서
  그 낱말이 **제 정의 줄 하나**로 끝나면 아무도 안 쓴다.
★ **문서에 이름이 적혀 있으면 안 죽은 것으로 센다.** 느슨한 쪽으로 둔다 — `getattr` · 이름 문자열로
  부르는 자리가 있고, **거짓 양성이 하나라도 나면 사람이 검사를 끈다**(§213 · §239 와 같은 판단).
★ **밖 — 「불리지만 쓸모없는 것」 은 안 본다.** 한 곳에서라도 이름이 나오면 산 것으로 센다.
  **죽은 분기 · 안 도는 시험 · 늘 참인 조건**은 이 자의 밖이고, 그것은 사람이 읽는 일이다.
★ **밖 — 몸통 안의 이름은 안 본다.** 모듈 최상위의 `def` · `class` 만 본다. 안쪽 함수는 제 몸통이
  곧 쓰임이라 이 셈이 안 맞는다.
"""
from __future__ import annotations

import ast
import collections
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
# 이름을 정의하는 곳 — 여기의 최상위 `def` · `class` 만 후보다
정의터 = ("seshat/*.py", "tools/*.py")
# 이름이 쓰일 수 있는 곳 — **넓게 본다.** 좁히면 거짓 양성이 난다
쓰임터 = ("seshat/*.py", "tools/*.py", "tests/*.py", "tools/*.sh", "*.md",
          "docs/**/*.md", ".github/workflows/*.yml")
낱말 = re.compile(r"[A-Za-z_가-힣][\w가-힣]*")

# ★ **장부가 비었다**(2026-09-30 · DECISIONS §240). 둘을 세운 그 판에서 지웠으므로 라쳇은
#   **절대 규칙**이다 — 죽은 이름은 하나도 못 들어온다. 다시 채우지 않는다
장부: frozenset[str] = frozenset()


def _글들(root: pathlib.Path, 무늬: tuple[str, ...]) -> dict[pathlib.Path, str]:
    난것 = {}
    for g in 무늬:
        for p in sorted(root.glob(g)):
            if p.is_file():
                난것[p] = p.read_text(encoding="utf-8", errors="replace")
    return 난것


def 죽은이름(root: pathlib.Path | None = None) -> list[str]:
    """`파일::이름`. **저장소 전체에서 낱말이 한 번만 나오는** 최상위 정의."""
    root = root or ROOT
    센다: collections.Counter[str] = collections.Counter()
    for 글 in _글들(root, 쓰임터).values():
        센다.update(낱말.findall(글))
    죽은 = []
    for p, 글 in sorted(_글들(root, 정의터).items()):
        try:
            나무 = ast.parse(글)
        except SyntaxError:
            continue
        for n in 나무.body:                      # ★ 최상위만 본다 — 안쪽 함수는 몸통이 쓰임이다
            if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if n.name.startswith("__") or 센다[n.name] > 1:
                continue
            죽은.append(f"{p.relative_to(root).as_posix()}::{n.name}")
    return 죽은


def 견준다(지금: list[str], 장부: frozenset[str]) -> list[str]:
    """**새로 생긴 것만** 말한다. 지운 것은 잘한 일이지 실패가 아니다."""
    return [f"{x} — 저장소 어디서도 이 이름을 안 부른다. **지운다.** 남겨 둘 까닭이 있으면 "
            f"문서에 이름을 적는다(적힌 이름은 산 것으로 센다)"
            for x in sorted(set(지금) - 장부)]


def _canary(root: pathlib.Path | None = None) -> None:
    """★ **판별식이 죽으면 죽은 이름이 0 으로 보인다** — 0 이 「깨끗하다」 인지 묻는다."""
    난것 = 죽은이름(root)
    if any("::main" in x for x in 난것):
        print("    ★ 카나리아가 죽었다 — `main` 을 죽었다고 한다(`__main__` 이 부르는 것을 못 센다)")
        sys.exit(2)
    if 낱말.findall("_residue_of 를 적었다") != ["_residue_of", "를", "적었다"]:
        print("    ★ 카나리아가 죽었다 — 낱말을 못 가른다(밑줄 이름이 쪼개진다)")
        sys.exit(2)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    _canary()
    지금 = 죽은이름()
    if "--list" in args:
        print(f"  아무도 안 부르는 이름 {len(지금)}")
        for x in 지금:
            print(f"    {x}")
        return 0
    늘었나 = 견준다(지금, 장부)
    for x in 늘었나:
        print(f"    ✗ {x}", file=sys.stderr)
    if 늘었나:
        print("      어디서 부르는지 본다 : grep -rn '<이름>' seshat tools tests docs", file=sys.stderr)
        return 1
    print(f"  최상위 이름 — 죽은 것 {len(지금)} / 장부 {len(장부)}")
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
