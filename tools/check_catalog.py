"""데이터 카탈로그 검사 — 칸 · 쓰임 · 미확인 라이선스의 학습 · `data/` 의 카탈로그 밖 파일(DECISIONS §22).

  python3 tools/check_catalog.py         위반이면 1
  python3 tools/check_catalog.py --list  출처와 쓰임을 표로

★ **밖 — 선언이 참인지는 못 본다.** 카탈로그가 「이 출처는 학습에 안 쓴다」 고 적으면 그 말이
  **적혀 있는지**만 본다. 실제로 안 썼는지는 레이크와 판이 안다(`tools/lake.py`).
★ **`data/` 밖은 안 본다.** 레이크(SSD)의 파일은 `lake check` 의 몫이고, 여기는 저장소 안만 본다.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from seshat import catalog


def _canary() -> None:
    """★ **판별식이 죽으면 실패 0 이 초록으로 보인다** — 합성으로 물어 둔다."""
    나쁜 = [{"id": "x", "where": "어디도아니다", "uses": ["없는쓰임"], "license": "?"}]
    난것 = catalog.validate(나쁜)
    for 말, 왜 in (("where", "where 의 꼴을 안 본다"), ("모르는 쓰임", "쓰임 어휘를 안 본다"),
                  ("비었다", "빈 칸을 안 본다")):
        if not any(말 in f for f in 난것):
            print(f"    ★ 카나리아가 죽었다 — {왜} · {난것}")
            sys.exit(2)
    if catalog.USES & {"없는쓰임"}:
        print("    ★ 카나리아가 죽었다 — 쓰임 어휘가 아무거나 받는다")
        sys.exit(2)


def main(argv: list[str]) -> int:
    _canary()
    entries = catalog.load()
    if "--list" in argv:
        for n, d in catalog.layers().items():
            깃 = "커밋" if d["committed"] else ("다시 만든다" if d["regenerable"] else "레이크가 지킨다")
            print(f"  층 {n:<6} {d['base']:<5} {' '.join(d['dirs']):<38} {깃}")
        print()
        for e in entries:
            f = e["feeds"]
            읽는다 = f if isinstance(f, str) else " · ".join(f)
            print(f"  {e['id']:<14} {e['where']:<30} {','.join(e['uses']):<16} {e['license']}")
            print(f"  {'':<14} └ 읽는다 {읽는다[:96]}")
        return 0
    fails = (catalog.validate(entries)
             + [f"카탈로그 밖 {r}" for r in catalog.unlisted_repo_files(entries)]
             + catalog.weights_outside(entries)
             + catalog.check_layers())
    for f in fails:
        print(f"  {f}")
    아무도 = catalog.unfed(entries)
    print(f"  카탈로그 {len(entries)}출처 · 아무도 안 읽는 것 {len(아무도)}({' · '.join(아무도)}) · 실패 {len(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    # ★ 위반(1)과 도구 고장(2)을 다른 코드로 끝낸다(DECISIONS §21 · §232). 같은 코드면
    #   **도구가 깨진 것을 검사가 실패한 것으로 읽는다**
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        print("    ✗ 도구가 깨졌다 — 위 역추적이 자리를 든다\n"
              "      고치고 다시 돌린다 : bash tools/verify.sh", file=sys.stderr)
        sys.exit(2)
