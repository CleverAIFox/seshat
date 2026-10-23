"""문서 **색인**을 박고 지킨다(DECISIONS §327 · `PLAN #51`).

`check_docs` 는 두 일을 한 파일에서 했다 — **문서 규약**(문체 · 참조 · 지도)과 **색인 기계**.
2026-10-23 가설 대장을 접으면서 참조 면제가 필요해졌는데 그 파일이 **제 상한에 정확히
붙어 있어** 한 줄도 못 받았다. `check_size` 가 울었고, `PLAN #51` 이 이미 적어 둔 선이
여기였다 — 색인은 「문서 규약」 과 다른 일이다.

★ **밖 — 색인의 *내용*이 옳은지는 안 본다.** 절 제목과 번호가 본문과 **같은가**만 본다.
★ **밖 — `docseal` 과 무관하다.** 여기는 도장을 안 만지고 글만 다시 짠다.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: 절 안의 날짜. **이 저장소에 한 번만 적힌다** — `check_docs` 가 여기서 가져다 쓴다(§57).
DATE = re.compile(r"^\*\*(20\d\d-\d\d-\d\d)\*\*", re.M)

색인_시작, 색인_끝 = "<!-- 색인 시작 -->", "<!-- 색인 끝 -->"

def _절들(text: str) -> list[tuple[int, str, str]]:
    """DECISIONS 의 (번호, 제목, 날짜)."""
    out = []
    for m in re.finditer(r"^## §(\d+)\. (.+)$", text, re.M):
        뒤 = text[m.end():m.end() + 400]
        날 = DATE.search(뒤)
        out.append((int(m.group(1)), m.group(2).strip(), 날.group(0).strip("*") if 날 else ""))
    return out
def 색인_글(절들: list[tuple[int, str, str]]) -> str:
    줄 = [f"{색인_시작}",
          f"<details><summary><b>절 색인</b> — {len(절들)} 절. "
          f"<code>python3 tools/check_docs.py --fix-index</code> 가 다시 쓴다</summary>",
          "", "| § | 날짜 | 무엇 |", "|---|---|---|"]
    줄 += [f"| {n} | {d} | {제} |" for n, 제, d in 절들]
    줄 += ["", "</details>", 색인_끝]
    return "\n".join(줄)
def _색인을_박는다(text: str) -> str:
    새 = 색인_글(_절들(text))
    if 색인_시작 in text and 색인_끝 in text:
        앞, 뒤 = text.split(색인_시작, 1)
        return 앞 + 새 + 뒤.split(색인_끝, 1)[1]
    첫 = text.index("## §1.")
    return text[:첫] + 새 + "\n\n" + text[첫:]
def check_index(text: str, fails: list) -> None:
    """색인이 절과 맞나. **자동으로 다시 쓸 수 있는 것은 손으로 고치라고 하지 않는다.**"""
    if 색인_시작 not in text:
        fails.append("DECISIONS 에 절 색인이 없다 — `python3 tools/check_docs.py --fix-index`")
        return
    if _색인을_박는다(text) != text:
        fails.append("DECISIONS 색인이 절과 어긋난다 — `python3 tools/check_docs.py --fix-index`")
