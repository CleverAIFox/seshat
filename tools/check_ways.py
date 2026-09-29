"""**막는 자리마다 넘는 길이 있는가**(DECISIONS §210).

  python3 tools/check_ways.py            # 늘었으면 1
  python3 tools/check_ways.py --list     # 길이 안 보이는 자리를 전부 찍는다
  python3 tools/check_ways.py --update   # 지금 수를 장부에 박는다(줄었을 때만 쓴다)

★ **이것은 대증요법을 끝내려고 만든 도구다.** 2026-09-27 ~ 09-29 사이에 같은 병으로 절을 **열 개**
  적었다(§174 · §175 · §188 · §196 · §197 · §198 · §201 · §202 · §203 · §205). 매번 **그 한 자리**를
  고쳤다. 막는 자리는 저장소에 아흔 곳이 넘으므로, 한 곳씩 고치는 한 이 절은 계속 늘어난다.
★ **고치는 대신 「늘지 못하게」 한다.** 있는 것을 하루에 다 고치는 것은 거짓말이고, 새로 생기는 것을
  막는 것은 오늘 할 수 있다. 수는 **파일마다** 센다 — 총합만 보면 한 곳을 고치고 다른 곳에 만들어도
  통과한다.
★ **완전하지 않다.** 넘는 길이 변수에 담겨 있으면 못 본다(앞 일곱 줄까지는 본다). 그래서
  **거짓 양성이 남고, 그것이 이 도구의 값을 안 깎는다** — 숫자가 안 늘기만 하면 된다.
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# ★ **넘는 길로 읽는 것들.** 명령 · 깃발 · 「무엇을 한다」 꼴. 늘려도 되지만 **넓히면 거짓 초록**이 된다
길표 = re.compile(r"(tools/[a-z_]+\.(py|sh)|uv run|python3 |bash |--[a-z-]{2,}|ollama |git |rm "
                  r"|적는다|친다 :|한다 :|띄운다|올린다|넣는다|고친다|지운다|만든다|본다 :|받는다)")

# ★ 자가 시험과 카나리아는 **사람에게 하는 말이 아니다** — 죽은 검사를 알리는 소리다
안보는함수 = {"_selftest", "_canary", "_프로브"}

# ★ **장부.** 파일마다 「길이 안 보이는 자리」 의 수. 늘면 막는다. 줄이면 `--update` 로 박는다.
#   0 이 된 파일은 여기서 지운다 — 그러면 **다시 생기는 순간** 새 파일로 걸린다
장부: dict[str, int] = {
    "seshat/evaluate.py": 2,
    "tools/bootstrap.py": 1,
    "tools/ci_status.py": 1,
    "tools/fetch_awsdocs.py": 2,
    "tools/fetch_flores.py": 3,
    "tools/gate.py": 3,
    "tools/labels.py": 7,
    "tools/lake.py": 1,
    "tools/mine_terms.py": 1,
    "tools/noise.py": 1,
    "tools/show_misses.py": 1,
    "tools/slice.py": 1,
    "tools/style_na.py": 1,
    "tools/term_diff.py": 2,
    "tools/watch_papers.py": 3,
}


def _막는자리(나무: ast.AST) -> list[ast.Call]:
    안 = {n for f in ast.walk(나무) if isinstance(f, ast.FunctionDef) and f.name in 안보는함수
          for n in ast.walk(f)}
    out = []
    for n in ast.walk(나무):
        if not isinstance(n, ast.Call) or not isinstance(n.func, ast.Name) or n in 안:
            continue
        글 = ast.unparse(n)
        if n.func.id == "SystemExit" and re.search(r"['\"]", 글):
            out.append(n)                      # `SystemExit(2)` 는 말이 아니라 종료 코드다
        elif n.func.id == "print" and "✗" in 글:
            out.append(n)
    return out


def 길없는자리(root: pathlib.Path | None = None) -> list[tuple[str, int, str]]:
    """(파일, 줄, 글). **앞 일곱 줄까지 같이 본다** — 넘는 길을 바로 위에서 짓는 자리가 있다."""
    root = root or ROOT
    out = []
    for f in sorted(list((root / "seshat").glob("*.py")) + list((root / "tools").glob("*.py"))):
        줄 = f.read_text(encoding="utf-8").splitlines()
        for n in _막는자리(ast.parse("\n".join(줄))):
            글 = ast.unparse(n)
            둘레 = "\n".join(줄[max(0, n.lineno - 7):(n.end_lineno or n.lineno)])
            if not (길표.search(글) or 길표.search(둘레)):
                out.append((f.relative_to(root).as_posix(), n.lineno, 글.replace("\n", " ")[:90]))
    return out


def 센다(자리: list[tuple[str, int, str]]) -> dict[str, int]:
    셈: dict[str, int] = {}
    for f, _, _ in 자리:
        셈[f] = 셈.get(f, 0) + 1
    return 셈


def 견준다(지금: dict[str, int], 장부: dict[str, int]) -> list[str]:
    """**늘어난 것만** 말한다. 줄어든 것은 잘한 일이지 실패가 아니다."""
    말 = []
    for f in sorted(set(지금) | set(장부)):
        옛, 새 = 장부.get(f, 0), 지금.get(f, 0)
        if 새 > 옛:
            말.append(f"{f} — 길 없는 자리가 {옛} → {새} 로 늘었다. "
                      f"막는 자리를 새로 만들었으면 **넘는 길을 같이 적는다**(DECISIONS §210)")
    return 말


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    자리 = 길없는자리()
    지금 = 센다(자리)
    if "--list" in args:
        print(f"  길이 안 보이는 자리 {len(자리)}")
        for f, ln, s in 자리:
            print(f"    {f}:{ln}  {s}")
        print("\n  ※ 이 목록은 **할 일**이지 실패가 아니다. 하나 고칠 때마다 `--update` 로 장부를 줄인다")
        return 0
    if "--update" in args:
        늘었나 = 견준다(지금, 장부)
        if 늘었나:
            for x in 늘었나:
                print(f"    ✗ {x}", file=sys.stderr)
            print("    **늘어난 채로 박지 않는다** — 먼저 고친다", file=sys.stderr)
            return 1
        print("장부: dict[str, int] = {")
        for f in sorted(지금):
            print(f'    "{f}": {지금[f]},')
        print("}")
        print("\n  ※ 위를 `tools/check_ways.py` 의 `장부` 에 넣는다", file=sys.stderr)
        return 0
    말 = 견준다(지금, 장부)
    for x in 말:
        print(f"    ✗ {x}")
    남 = sum(장부.values()) - len(자리)
    if not 말:
        print(f"  길 없는 자리 {len(자리)} — 장부 {sum(장부.values())}"
              + (f" · **{남} 곳 줄었다.** `--update` 로 장부를 줄인다" if 남 > 0 else ""))
    return 1 if 말 else 0


if __name__ == "__main__":
    sys.exit(main())
