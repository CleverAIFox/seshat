"""온톨로지가 제 규칙을 지키는가(DECISIONS §13).

  python3 tools/check_ontology.py          검사한다. 위반 1 · 고장 2
  python3 tools/check_ontology.py --list   종류별 수를 찍는다
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
    if "--list" in args:
        for k, v in sorted(Counter(n["kind"] for n in onto).items()):
            print(f"  {k:<8} {v}")
        print(f"  표기 {len(ontology.surfaces(onto))}")
        print(f"  허용 표기 {sum(len(n.get('alt_ko', [])) for n in onto)} · 관측된 오역 {sum(len(n.get('bad_ko', [])) for n in onto)}")
        return 0
    fails = ontology.validate(onto)
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
