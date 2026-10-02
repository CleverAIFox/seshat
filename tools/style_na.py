"""**합쇼체가 설 수 없는 줄**의 후보를 뽑는다(DECISIONS §189 · §194).

  python3 tools/style_na.py runs/A.jsonl runs/B.jsonl runs/C.jsonl
  python3 tools/style_na.py runs/*.jsonl --least 3

★ **`style` 의 분모에 합쇼체가 설 수 없는 줄이 섞여 있다**(DECISIONS §194). `A list of triggers for the
  specified job.` → `지정된 작업에 대한 트리거 목록.` 은 **명사구**라 종결어미가 설 자리가 없는데
  지표는 깨진 것으로 센다. 목록으로 끝나는 줄도 같다.
★ **고치기 전에 크기부터 잰다**(DECISIONS §183). 지금은 「더럽다」 만 알고 **얼마나**를 모른다.
  자동으로 가르지 않는다 — 「완전한 문장인가」 는 규칙으로 못 가른다(파서가 있어야 하고, 그 파서가
  또 자가 된다). **사람이 한 번 보는 것**이 가장 싸고 가장 정확하다.
★ **어느 팔도 못 맞힌 줄이 후보다.** 한 팔만 틀리면 그것은 그 팔의 실력이고, **넷이 다 틀리면**
  줄 쪽을 의심할 값어치가 있다. 이 도구는 **후보를 주고 판정은 사람이 한다**(§34 · §65 와 같은 규율).
★ **판정한 것은 어딘가에 적혀야 한다.** 눈으로 보고 넘기면 다음 달에 또 본다 — 끝에 찍히는 꼴로
  `data/domain/<셋>.style-na.txt` 에 id 를 적는다.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from seshat import compare, evaluate
from seshat import paths


def read(path: str) -> tuple[dict, dict[str, dict]]:
    줄 = [json.loads(x) for x in paths.줄들(path, "판", ("`ls runs/*.jsonl` 로 있는 판을 본다",))]
    머리 = next(x for x in 줄 if x.get("meta"))
    return 머리, {x["id"]: x for x in 줄 if not x.get("meta") and x.get("id")}


def 못맞힌_줄(판들: list[tuple[dict, dict[str, dict]]]) -> Counter:
    """{id: 몇 판에서 합쇼체가 아니었나}. **같은 셋을 잰 판만 넣는다.**"""
    셈: Counter = Counter()
    for _, 줄 in 판들:
        for i, r in 줄.items():
            if not evaluate.is_hapsyo(r.get("out") or ""):
                셈[i] += 1
    return 셈


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--least", type=int, default=0,
                    help="이만큼의 판에서 틀린 줄만 — 비우면 **전부**(판 수)")
    ap.add_argument("--set", dest="set_", default="", help="비우면 첫 판의 머리줄이 가리키는 셋")
    a = ap.parse_args(argv)

    판들 = [read(x) for x in a.runs]
    # ★ **같은 글을 잰 판만 모은다.** 다른 셋의 줄 번호를 섞으면 후보가 거짓이 된다(§45)
    첫 = 판들[0][0]
    for 길, (머리, _) in zip(a.runs, 판들):
        갈린 = compare.갈림(첫, 머리, ("set_sha256",))
        if 갈린:
            print(f"  ✗ {pathlib.Path(길).name} 이 딴 셋이다 — {갈린[0].글()}", file=sys.stderr)
            return 1

    셋 = a.set_ or 첫.get("set") or ""
    if not 셋:
        print("  ✗ 셋을 모른다 — --set 으로 준다", file=sys.stderr)
        return 1
    원문 = {r["id"]: r.get("src") or "" for r in evaluate.load(셋)}

    셈 = 못맞힌_줄(판들)
    선 = a.least or len(판들)
    후보 = sorted(i for i, n in 셈.items() if n >= 선)
    print(f"  판 {len(판들)} · 셋 {셋}\n"
          f"  **{선} 판 모두에서** 합쇼체가 아니었던 줄 {len(후보)} — 후보다, 판정이 아니다\n"
          f"  ※ 한 팔만 틀리면 그 팔의 실력이고, 다 틀리면 줄 쪽을 의심할 값어치가 있다\n")
    for i in 후보:
        print(f"    [{i}] {원문.get(i, '(원문 없음)')[:120]}")
    if 후보:
        이름 = pathlib.Path(셋).stem
        print(f"\n  눈으로 보고 **합쇼체가 설 수 없는 것**만 골라 여기 적는다 —"
              f" `data/domain/{이름}.style-na.txt`(한 줄에 id 하나)")
        print("  적고 나면 그 수가 DECISIONS §194 의 크기다 — 그때 분모에서 뺄지 정한다(자가 바뀐다)")
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
