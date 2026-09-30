"""온톨로지가 제 규칙을 지키는가(DECISIONS §13).

  python3 tools/check_ontology.py          검사한다. 위반 1 · 고장 2
  python3 tools/check_ontology.py --list   종류별 수를 찍는다

★ **밖 — 사전이 옳은지는 안 본다.** 꼴과 겹침과 빈칸을 본다. **한국어 표기가 맞는지**는 사람이
  대조하고(§34 · §65), **사전이 넓은지**는 `term` 의 분모 문제라 PLAN #22 가 든다.
★ **누수는 안 본다.** 이 사전을 캔 줄이 평가셋에 있는지는 `onto_leak` 이 판마다 센다(§168).
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from seshat import ontology  # noqa: E402


def _canary() -> None:
    probe = [{"id": "svc.a", "kind": "service", "en": "Amazon A", "keep": True, "coda": "none", "aliases": ["A"], "src": "author"},
             {"id": "svc.b", "kind": "service", "en": "Amazon B", "keep": True, "coda": "none", "aliases": ["a"], "src": "author"}]
    got = ontology.validate(probe)
    if not any("둘을 가리킨다" in f for f in got):
        print(f"    ★ 카나리아가 죽었다 — {got}")
        sys.exit(2)


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    _canary()
    onto = ontology.load()
    # ★ **장부가 사전보다 먼저 썩는다.** 노드를 지우거나 이름을 바꾸면 장부의 id 가 허공을 가리키고,
    #   그러면 판의 `onto_leak` 이 **실제보다 작게** 나온다 — 누수가 저절로 줄어든 것처럼 보인다(§168)
    있는id = {n["id"] for n in onto}
    장부 = ontology.누수_장부()
    if "--list" in args:
        for k, v in sorted(Counter(n["kind"] for n in onto).items()):
            print(f"  {k:<8} {v}")
        print(f"  표기 {len(ontology.surfaces(onto))}")
        print(f"  허용 표기 {sum(len(n.get('alt_ko', [])) for n in onto)} · 관측된 오역 {sum(len(n.get('bad_ko', [])) for n in onto)}")
        con = [n for n in onto if n["kind"] == "concept"]
        print(f"  공식 표기 대조 {sum(1 for n in con if n.get('ko_ref'))}/{len(con)} 개념 (PLAN #22)")
        for 셋, v in sorted(Counter(d["mined_from"] for d in 장부).items()):
            print(f"  누수 {v} — {셋} 에서 캐서 넣었다 (DECISIONS §192)")
        return 0
    fails = ontology.validate(onto)
    fails += [f"누수 장부의 {d.get('id')!r} 가 사전에 없다 — 지웠으면 장부에서도 지운다"
              for d in 장부 if d.get("id") not in 있는id]
    fails += [f"누수 장부의 {d.get('id')!r} 가 든 mined_from 이 셋의 자리가 아니다 — {d.get('mined_from')!r}"
              for d in 장부
              if not (isinstance(d.get("mined_from"), str) and ontology.MINED_FROM.fullmatch(d["mined_from"]))]
    for f in fails:
        print(f"    {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(2)
