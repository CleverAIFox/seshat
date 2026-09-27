"""데이터 카탈로그 검사 — 칸 · 쓰임 · 미확인 라이선스의 학습 · `data/` 의 카탈로그 밖 파일(DECISIONS §22).

  python3 tools/check_catalog.py         위반이면 1
  python3 tools/check_catalog.py --list  출처와 쓰임을 표로
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from seshat import catalog  # noqa: E402


def main(argv: list[str]) -> int:
    entries = catalog.load()
    if "--list" in argv:
        for n, d in catalog.layers().items():
            깃 = "커밋" if d["committed"] else ("다시 만든다" if d["regenerable"] else "레이크가 지킨다")
            print(f"  층 {n:<6} {d['base']:<5} {' '.join(d['dirs']):<38} {깃}")
        print()
        for e in entries:
            print(f"  {e['id']:<14} {e['where']:<30} {','.join(e['uses']):<16} {e['license']}")
        return 0
    fails = (catalog.validate(entries)
             + [f"카탈로그 밖 {r}" for r in catalog.unlisted_repo_files(entries)]
             + catalog.weights_outside(entries)
             + catalog.check_layers())
    for f in fails:
        print(f"  {f}")
    print(f"  카탈로그 {len(entries)}출처 · 실패 {len(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
