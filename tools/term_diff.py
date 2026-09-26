"""두 결과의 **개념 단위** 대조 — 누가 어느 용어에서 이겼나(DECISIONS §85).

  uv run python tools/term_diff.py runs/A.jsonl runs/B.jsonl
  uv run python tools/term_diff.py A.jsonl B.jsonl --only=a      A 만 맞힌 자리
  uv run python tools/term_diff.py A.jsonl B.jsonl --max 40

★ `compare_runs` 는 **줄**을 대조한다. 용어는 한 줄에 여럿 들어 있으므로 줄로는 누가 어느 개념에서
  졌는지 못 가른다. 여기서는 개념마다 센다.
★ **판정은 사람이 한다.** 도구는 「A 는 공식 표기를 썼고 B 는 이렇게 썼다」 까지 보인다. 그 말이
  허용해도 되는 표기(`alt_ko` 로 올린다)인지 지어낸 말인지는 눈이 가른다.
★ 두 결과의 평가셋 · 사전 해시가 다르면 **멈춘다**(DECISIONS §32). 다른 자로 잰 것을 나란히 놓지 않는다.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from seshat import ontology  # noqa: E402


def read(path: Path) -> tuple[dict, dict[str, dict]]:
    lines = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    head = next((x for x in lines if x.get("meta")), None)
    if head is None:
        raise SystemExit(f"결과 파일이 아니다 — 머리줄이 없다 : {path}")
    return head, {x["id"]: x for x in lines if not x.get("meta")}


def 같은_자인가(a: dict, b: dict) -> None:
    for key, 무엇 in (("set_sha256", "평가셋"), ("onto_sha256", "사전")):
        if a.get(key) != b.get(key):
            raise SystemExit(f"{무엇}이 다르다 — {a.get(key)} 대 {b.get(key)}\n"
                             f"    다른 자로 잰 것을 나란히 놓지 않는다(DECISIONS §32)")


def 가른다(onto: list[dict], a_rows: dict, b_rows: dict) -> list[dict]:
    """개념마다 두 출력이 공식 표기를 썼는지. 다른 자리만 돌려준다."""
    out = []
    for rid, ra in a_rows.items():
        rb = b_rows.get(rid)
        if rb is None or rb["src"] != ra["src"]:
            continue
        for _, _, s in ontology.find(onto, ra["src"]):
            n = s.node
            if n["keep"]:
                continue
            ka, kb = n["ko"] in ra.get("out", ""), n["ko"] in rb.get("out", "")
            if ka != kb:
                out.append({"id": rid, "en": n["en"], "ko": n["ko"], "a": ka,
                            "a_out": ra.get("out", ""), "b_out": rb.get("out", ""), "src": ra["src"]})
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a", type=Path)
    ap.add_argument("b", type=Path)
    ap.add_argument("--only", choices=("a", "b", "both"), default="both", help="누가 맞힌 자리만 볼 것인가")
    ap.add_argument("--max", type=int, default=25, help="줄을 몇 개까지 펼칠 것인가")
    x = ap.parse_args(argv)

    ha, ra = read(x.a)
    hb, rb = read(x.b)
    같은_자인가(ha, hb)
    onto = ontology.load()
    자리 = 가른다(onto, ra, rb)
    A, B = ha.get("backend", x.a.name), hb.get("backend", x.b.name)
    a만 = [d for d in 자리 if d["a"]]
    b만 = [d for d in 자리 if not d["a"]]
    print(f"  A {A}  ·  B {B}  ·  갈린 자리 {len(자리)}")
    print(f"  A 만 공식 표기 {len(a만)} · B 만 공식 표기 {len(b만)}")
    for 이름, 묶음 in (("A 만", a만), ("B 만", b만)):
        if 묶음:
            print(f"\n  [{이름}] 개념별 " + " · ".join(f"{k}×{v}" for k, v in Counter(d["en"] for d in 묶음).most_common()))
    보일것 = (a만 if x.only == "a" else b만 if x.only == "b" else 자리)[:x.max]
    for d in 보일것:
        이긴쪽 = "A" if d["a"] else "B"
        print(f"\n  {d['id']} · {d['en']} → {d['ko']} ({이긴쪽} 만 썼다)")
        print(f"    원문 {d['src']}")
        print(f"    A    {d['a_out'][:200]}")
        print(f"    B    {d['b_out'][:200]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
