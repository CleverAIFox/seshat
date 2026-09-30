"""**도구가 역추적으로 죽지 않는가**(DECISIONS §232).

  python3 tools/check_crashes.py            # 늘었으면 1
  python3 tools/check_crashes.py --list     # 맨몸으로 죽는 도구를 전부 찍는다
  python3 tools/check_crashes.py --update   # 지금 목록을 장부에 박는다(줄었을 때만 쓴다)

★ `tools/check_ways.py` 는 **막는 자리마다 넘는 길이 있나**를 본다 — `SystemExit` 과 `print("✗")`
  자리만 본다. 그런데 도구는 **안 막고 죽기도 한다.** 2026-09-30 `lake.py` 가 메모리 부족으로
  `OSError` 를 그대로 올려 역추적 여섯 줄을 뱉었고, 「무엇이 잘못인가」 도 「무엇을 하면 되는가」 도
  없었다. **`check_ways` 는 그 자리를 초록으로 봤다** — 세는 자리가 아니기 때문이다.
★ **벽도 없고 길도 없는 자리**를 이 도구가 본다. `__main__` 블록이 `main()` 을 싸서, 뜻밖의 예외를
  **말과 종료 코드 2**(고장 · MASTER §0)로 바꾸는가.
★ **2026-09-30 스물일곱을 한 판에 다 갚았다**(DECISIONS §233). 싸는 일은 자리마다 같은 일곱 줄이라
  라쳇으로 미룰 까닭이 없었다 — `check_ways` 가 서른을 한 판에 갚은 것과 같다(§213). **장부는 비었고
  이제 절대 규칙이다.**
★ **완전하지 않다.** `main()` 안에서 스스로 싸는 도구는 맨몸으로 보인다 — **거짓 양성이 남고,
  그것이 이 도구의 값을 안 깎는다.** 숫자가 안 늘기만 하면 된다.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
문 = re.compile(r'^if __name__ == ["\']__main__["\']:', re.M)

# ★ **장부가 비었다**(2026-09-30 · DECISIONS §233). 스물일곱을 한 판에 다 갚았으므로 라쳇은 이제
#   **절대 규칙**이다 — 맨몸으로 죽는 도구는 하나도 못 들어온다. 다시 채우지 않는다.
장부: frozenset[str] = frozenset()


def 맨몸인가(글: str) -> bool:
    """`__main__` 블록이 뜻밖의 예외를 안 싸는가. **블록이 없으면 맨몸이 아니다**(도구가 아니다)."""
    m = 문.search(글)
    return bool(m) and "except Exception" not in 글[m.start():]


def 맨몸들(root: pathlib.Path | None = None) -> list[str]:
    root = root or ROOT
    out = []
    for d in ("seshat", "tools"):
        for f in sorted((root / d).glob("*.py")):
            if 맨몸인가(f.read_text(encoding="utf-8")):
                out.append(f.relative_to(root).as_posix())
    return out


def 견준다(지금: list[str], 장부: frozenset[str]) -> list[str]:
    """**새로 생긴 것만** 말한다. 갚은 것은 잘한 일이지 실패가 아니다."""
    return [f"{f} — `__main__` 이 맨몸이다. 뜻밖의 예외가 역추적으로 나간다. "
            f"`try: sys.exit(main())` 로 싸고 **고장은 2** 로 끝낸다(DECISIONS §232)"
            for f in sorted(set(지금) - 장부)]


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    지금 = 맨몸들()
    if "--list" in args:
        print(f"  맨몸으로 죽는 도구 {len(지금)}")
        for f in 지금:
            print(f"    {f}")
        print("\n  ※ 이 목록은 **할 일**이지 실패가 아니다. 하나 고칠 때마다 `--update` 로 장부를 줄인다")
        return 0
    늘었나 = 견준다(지금, 장부)
    if "--update" in args:
        if 늘었나:
            for x in 늘었나:
                print(f"    ✗ {x}", file=sys.stderr)
            print("    **늘어난 채로 박지 않는다** — 먼저 고친다", file=sys.stderr)
            return 1
        print("장부: frozenset[str] = frozenset({")
        for f in 지금:
            print(f'    "{f}",')
        print("})")
        print("\n  ※ 위를 `tools/check_crashes.py` 의 `장부` 에 넣는다", file=sys.stderr)
        return 0
    for x in 늘었나:
        print(f"    ✗ {x}")
    남 = len(장부) - len(지금)
    if not 늘었나:
        print(f"  맨몸 {len(지금)} — 장부 {len(장부)}"
              + (f" · **{남} 개 갚았다.** `--update` 로 장부를 줄인다" if 남 > 0 else ""))
    return 1 if 늘었나 else 0


if __name__ == "__main__":
    # ★ 제 규칙을 제가 지킨다 — 이 도구가 맨몸이면 검사가 농담이 된다
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(2)
