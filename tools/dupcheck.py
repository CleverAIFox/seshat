"""**같은 것이 몇 벌인가** — 구조가 같은 함수를 센다(DECISIONS §163).

  python3 tools/dupcheck.py                  전수
  python3 tools/dupcheck.py --min 12         더 큰 함수만
  python3 tools/dupcheck.py --selftest       프로브가 살아 있나

★ **2026-09-28 하루에 같은 병을 여덟 번 앓았다**(§157). 까닭은 조건이 네 곳에 손으로 적혀 있던 것이고,
  **그 네 곳을 센 것은 여덟 번째가 나고 나서였다.** 조사 목록은 네 곳에 있었는데 **한 번도 안 갈렸다**
  — 병이 안 났을 뿐 자리는 있었다(§158). **자리는 병이 나기 전에 셀 수 있다.**
★ **이름이 아니라 구조를 본다.** `_JOSA_TAIL` 과 `_PARTICLE` 은 이름이 달라서 안 보였다. 함수 본문을
  AST 로 파싱하고 **이름을 전부 지운 뒤** 지문을 낸다 — 변수명만 바꾼 사본이 같은 지문을 낸다.
★ **사본이 전부 나쁜 것은 아니다.** 이 도구는 **세는 것**이지 고치라고 하는 것이 아니다. 시험 두 개가
  같은 모양인 것은 정상이고, `seshat/` 과 `tools/` 에 같은 규칙이 있는 것은 정상이 아니다.
★ **함수만 보면 오늘의 병을 하나도 못 막는다.** 2026-09-28 의 사본 넷은 **상수**였다
  (조사 목록이 네 곳 · `seshat/terms.py` 의 `JOSA`). 그래서 **긴 글자 사본**도 같이 센다 — 열두 자 이상의 같은
  문자열이 두 곳에 있으면 든다. 정규식 · 메시지 · 경로가 여기 걸린다.
★ **`--min` 을 낮추면 잡음이 는다.** 한 줄짜리 접근자는 당연히 같다 — 기본 10 노드는 그 아래를 뺀다.
"""
from __future__ import annotations

import argparse
import ast
import collections
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
# 볼 곳. 시험은 서로 닮는 것이 정상이라 기본에서 뺀다 — `--tests` 로 넣는다
BASE = ("seshat", "tools")


class _지운다(ast.NodeTransformer):
    """이름 · 글자 · 수를 전부 한 가지로 만든다. **구조만 남는다.**"""

    def visit_Name(self, n):            # noqa: N802
        return ast.copy_location(ast.Name(id="_", ctx=n.ctx), n)

    def visit_arg(self, n):             # noqa: N802
        return ast.copy_location(ast.arg(arg="_", annotation=None), n)

    def visit_Attribute(self, n):       # noqa: N802
        self.generic_visit(n)
        return ast.copy_location(ast.Attribute(value=n.value, attr="_", ctx=n.ctx), n)

    def visit_Constant(self, n):        # noqa: N802
        return ast.copy_location(ast.Constant(value="_"), n)


def 지문(fn: ast.AST) -> tuple[str, int]:
    """(구조 지문, 노드 수). 문서주석은 뺀다 — 설명이 다르다고 사본이 아닌 것은 아니다."""
    몸 = list(getattr(fn, "body", []))
    if 몸 and isinstance(몸[0], ast.Expr) and isinstance(몸[0].value, ast.Constant):
        몸 = 몸[1:]
    나무 = ast.Module(body=[_지운다().visit(x) for x in 몸], type_ignores=[])
    ast.fix_missing_locations(나무)
    return ast.dump(나무), sum(1 for _ in ast.walk(나무))


def 훑는다(디렉토리: tuple[str, ...], least: int) -> dict[str, list[str]]:
    무리: dict[str, list[str]] = collections.defaultdict(list)
    for d in 디렉토리:
        for f in sorted((ROOT / d).rglob("*.py")):
            try:
                나무 = ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for n in ast.walk(나무):
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    지, 수 = 지문(n)
                    if 수 >= least:
                        무리[지].append(f"{f.relative_to(ROOT)}:{n.lineno} {n.name}")
    return {k: v for k, v in 무리.items() if len(v) > 1}


def 글자_사본(디렉토리: tuple[str, ...], 길이: int) -> dict[str, list[str]]:
    """같은 **긴 문자열**이 두 곳 이상에 있나. 2026-09-28 의 사본 넷은 전부 이 꼴이었다(§163).

    ★ 문서주석은 뺀다 — 같은 설명을 두 곳에 적는 것은 사본이 아니라 중복 설명이다.
    ★ 짧은 글자는 안 본다. `"utf-8"` 이 스물몇 곳에 있는 것은 사본이 아니다.
    """
    무리: dict[str, list[str]] = collections.defaultdict(list)
    흔한 = {"utf-8", "__main__", "ensure_ascii"}
    for d in 디렉토리:
        for f in sorted((ROOT / d).rglob("*.py")):
            try:
                나무 = ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            독들 = {ast.get_docstring(x, clean=False) for x in ast.walk(나무)
                   if isinstance(x, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
            for n in ast.walk(나무):
                if isinstance(n, ast.Constant) and isinstance(n.value, str):
                    v = n.value
                    if len(v) >= 길이 and v not in 흔한 and v not in 독들 and "\n" not in v[:-1]:
                        무리[v].append(f"{f.relative_to(ROOT)}:{n.lineno}")
    return {k: sorted(set(v)) for k, v in 무리.items() if len(set(v)) > 1}


def _점이름(node: ast.AST) -> str:
    조각 = []
    while isinstance(node, ast.Attribute):
        조각.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return ""
    조각.append(node.id)
    return ".".join(reversed(조각))


def 부름_갈림(디렉토리: tuple[str, ...], 최대꼴: int = 8) -> dict[str, dict[str, list[str]]]:
    """같은 함수를 **여러 곳에서 서로 다른 인자로** 부르는 자리(DECISIONS §171).

    ★ **2026-09-28 의 아홉 번째 병은 함수도 글자도 아니었다.** `compare.갈림(rec, head, X)` 의 `X` 가
      `("metrics",)` · `GATE_막` 으로 **곳마다 달랐고**, 그래서 막는 쪽과 쓰는 쪽이 다른 기준으로
      돌았다(§169). 함수 지문도 긴 글자도 그것을 못 봤다 — **한 줄짜리 조건**이다.
    ★ **인자가 같으면 안 든다.** 같은 물음을 같은 축으로 던지는 것은 사본이 아니라 그냥 쓰임이다.
      **갈리는 것**만 본다 — 한 함수를 부르는 인자 꼴이 둘 이상일 때.
    ★ **세는 것이지 고치라는 것이 아니다.** `ontology.find(onto, src)` 와 `find(onto, ko)` 처럼
      갈리는 것이 요점인 자리가 많다. 사람이 본다 — 이 도구는 **볼 자리를 준다.**
    """
    본: dict[str, dict[str, list[str]]] = collections.defaultdict(lambda: collections.defaultdict(list))
    # ★ **담는 일과 정하는 일을 가른다.** `fails.append` 는 93 꼴인데 그것은 사본이 아니라 **쓰임**이다 —
    #   담개와 입출력은 원래 곳마다 다른 것을 받는다. 찾는 것은 **정책을 인자로 받는 부름**이다
    담개 = {"append", "add", "extend", "update", "insert", "pop", "get", "setdefault", "discard",
            "write", "write_text", "read_text", "print", "join", "format", "replace", "split",
            "startswith", "endswith", "strip", "count", "index", "match", "search", "sub",
            "fullmatch", "finditer", "findall", "run", "setattr", "getattr", "isinstance",
            "add_argument", "relative_to", "monkeypatch", "dumps", "loads", "assertEqual"}
    for d in 디렉토리:
        for f in sorted((ROOT / d).rglob("*.py")):
            try:
                나무 = ast.parse(f.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for n in ast.walk(나무):
                if not isinstance(n, ast.Call) or not n.args:
                    continue
                이름 = _점이름(n.func)
                if "." not in 이름 or 이름.rsplit(".", 1)[1] in 담개:
                    continue                 # 점 있는 부름만 · 담개는 뺀다
                꼴 = ", ".join(ast.unparse(x) for x in n.args)
                본[이름][꼴].append(f"{f.relative_to(ROOT)}:{n.lineno}")
    # ★ **꼴이 너무 많으면 그것은 다목적 도구다.** 갈려서 병이 나는 자리는 **두엇**으로 갈린다
    return {k: dict(v) for k, v in 본.items() if 1 < len(v) <= 최대꼴}


def _selftest() -> int:
    """★ **프로브가 살아 있나.** 아무것도 안 찾는 검사와 고장 난 검사는 구별되지 않는다."""
    가 = ast.parse("def a(x):\n    y = x + 1\n    return y * 2\n").body[0]
    나 = ast.parse("def b(q):\n    '''딴 설명'''\n    w = q + 1\n    return w * 2\n").body[0]
    다 = ast.parse("def c(x):\n    y = x - 1\n    return y * 2\n").body[0]
    if 지문(가)[0] != 지문(나)[0]:
        print("  ✗ 이름과 문서주석만 다른 둘을 사본으로 못 본다", file=sys.stderr)
        return 1
    if 지문(가)[0] == 지문(다)[0]:
        print("  ✗ 연산자가 다른 둘을 사본으로 본다", file=sys.stderr)
        return 1
    # ★ **글자 쪽 프로브도 있어야 한다.** 함수만 보는 도구였으면 2026-09-28 의 사본 넷을
    #   하나도 못 잡았다 — 그것들은 전부 상수였다
    import tempfile
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "가.py").write_text('X = "아주 긴 정규식 같은 글자"\n', encoding="utf-8")
    (d / "나.py").write_text('Y = "아주 긴 정규식 같은 글자"\n', encoding="utf-8")
    옛, globals()["ROOT"] = ROOT, d
    try:
        if not 글자_사본((".",), 8):
            print("  ✗ 두 파일에 같은 긴 글자가 있는데 못 본다", file=sys.stderr)
            return 1
    finally:
        globals()["ROOT"] = 옛
    # ★ **부름 갈림 프로브도 있어야 한다.** 2026-09-28 의 아홉 번째 병은 함수도 글자도 아니라
    #   **같은 부름의 인자가 곳마다 다른 것**이었다 — 앞의 둘은 그것을 하나도 못 봤다
    d2 = pathlib.Path(tempfile.mkdtemp())
    (d2 / "가.py").write_text("m.본다(a, b, ('자',))\nm.본다(a, b, 막)\n", encoding="utf-8")
    (d2 / "나.py").write_text("m.같다(a, b)\nm.같다(a, b)\n", encoding="utf-8")
    옛2, globals()["ROOT"] = ROOT, d2
    try:
        got = 부름_갈림((".",))
        if "m.본다" not in got:
            print("  ✗ 인자가 곳마다 다른 부름을 못 본다", file=sys.stderr)
            return 1
        if "m.같다" in got:
            print("  ✗ 인자가 같은 부름을 사본으로 본다", file=sys.stderr)
            return 1
    finally:
        globals()["ROOT"] = 옛2
    print("  프로브 살아 있다 — 이름·문서주석은 무시하고, 연산자는 가르고, "
          "긴 글자 사본과 **인자가 갈리는 부름**을 본다")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=int, default=10, help="이보다 작은 함수는 안 본다")
    ap.add_argument("--chars", type=int, default=16, help="이보다 짧은 글자는 안 본다")
    ap.add_argument("--tests", action="store_true", help="tests/ 도 본다 — 시험은 닮는 것이 정상이다")
    ap.add_argument("--calls", action="store_true", help="인자가 갈리는 부름만 본다(§171)")
    ap.add_argument("--shapes", type=int, default=8, help="이보다 여러 꼴로 불리면 다목적 도구다")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()

    곳 = (*BASE, "tests") if a.tests else BASE
    본 = sorted(훑는다(곳, a.min).values(), key=len, reverse=True)
    글 = sorted(글자_사본(곳, a.chars).items(), key=lambda kv: -len(kv[1]))
    부름 = sorted(부름_갈림(곳, a.shapes).items(), key=lambda kv: -len(kv[1]))
    if a.calls:
        print(f"  인자가 갈리는 부름 {len(부름)} · 본 곳 {' '.join(곳)}")
        print("  ※ **갈리는 것이 요점인 자리가 많다** — 이 도구는 볼 자리를 준다(§171)\n")
        for 이름, 꼴들 in 부름:
            print(f"    {이름}  꼴 {len(꼴들)}")
            for 꼴, 곳들 in sorted(꼴들.items()):
                print(f"        ({꼴})  {' · '.join(곳들)}")
        return 0
    print(f"  구조가 같은 함수 무리 {len(본)}(최소 {a.min} 노드) · "
          f"긴 글자 사본 {len(글)}(최소 {a.chars} 자) · "
          f"인자가 갈리는 부름 {len(부름)}(`--calls` 로 본다) · 본 곳 {' '.join(곳)}")
    print("  ※ **세는 것**이지 고치라는 것이 아니다 — 같은 규칙이 두 곳에 있으면 한 곳만 고쳐진다\n")
    for 무 in 본:
        print(f"    함수 {len(무)}벌")
        for x in 무:
            print(f"        {x}")
    for v, 곳들 in 글:
        print(f"    글자 {len(곳들)}곳  {v[:64]!r}")
        for x in 곳들:
            print(f"        {x}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
