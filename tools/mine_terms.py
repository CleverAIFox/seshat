"""셋에 자주 나오는데 **사전이 모르는** 말을 캔다(PLAN #22 · DECISIONS §160).

  python3 tools/mine_terms.py data/domain/d001.jsonl --top 40

★ **사전이 모르는 말은 분모에도 안 들어간다.** `term` 은 `ontology.find` 가 찾은 것만 센다 —
  사전이 좁으면 점수가 높은 것이 아니라 **재는 범위가 좁은 것**이다. §66 은 「틀린 표기」 였고
  이것은 「없는 표기」 라 더 나쁘다. 틀린 것은 점수를 깎지만 없는 것은 **아무 자국도 안 남긴다.**
★ **표시된 자리는 뺀다**(`lit` · `ui` · DECISIONS §122). `bucket-owner-full-control` 은 개념이
  아니라 값이고, 사전에 넣으면 안 된다 — 식별자는 무한하다.
★ **이름(`keep`)도 뺀다.** 그것은 이미 사전이 아는 것이고, 영어로 남는다.
★ **캔 것을 그대로 넣지 않는다.** 이 도구는 **후보**를 준다. 공식 한국어 표기는 사람이 AWS 한국어
  문서와 대조해서 적고(`ko_ref`), 그때까지는 사전에 안 들어간다(§34 · §65 와 같은 규율).
★ **이 도구가 2026-09-28 의 누수를 만들었다**(DECISIONS §168 · DECISIONS §192). 점수를 내는 `d001` 을 캐서
  개념 14 를 넣었고, **시험지가 분모를 골랐다.** 캘 때는 안 보였다 — 표기를 공식 용어집에서 베꼈으니
  근거는 깨끗했고, **무엇을 넣을지를 누가 골랐나**는 아무 데도 안 적혔기 때문이다.
  그래서 이 도구는 이제 **기록판에 오른 셋을 거절한다.** 굳이 캐려면 `--leak-ok` 를 들고, 그때 이
  도구가 **누수 장부에 적을 줄을 찍어 준다.** 막는 것이 아니라 **적게 만드는 것**이 목적이다.
"""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import re
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from seshat import ontology
from seshat import paths

# 후보가 될 수 있는 꼴. 평범한 영어 명사(구)만 본다 — 식별자꼴은 개념이 아니다(§150)
_낱말 = re.compile(r"[A-Za-z][A-Za-z-]*")
# 개념일 수 없는 것들. 관사 · 전치사 · 조동사 — 빈도만 보면 이것들이 맨 위를 채운다
_STOP = frozenset("""a an the this that these those and or but if then than of in on at to for with by from
into over under is are was were be been being has have had do does did can could may might must should will
would you your we our it its they them their there here when where which who whom what how why all any each
more most other some such no not only own same so too very s t just now""".split())


def 표시된_자리(row: dict) -> list[tuple[int, int]]:
    out = []
    for kind in ("lit", "ui"):
        for t, at in (row.get(kind) or []):
            out.append((int(at), int(at) + len(t)))
    return out


def 캔다(rows: list[dict], onto: list[dict]) -> Counter:
    """{후보: 나온 줄 수}. **줄마다 한 번씩만** 센다 — 한 줄에 열 번 나오는 말이 순위를 뒤집는다."""
    셈: Counter = Counter()
    for r in rows:
        src = r.get("src") or ""
        가린 = 표시된_자리(r)
        아는곳 = [(a, b) for a, b, _ in ontology.find(onto, src)]
        본줄 = set()
        for m in _낱말.finditer(src):
            a, b = m.span()
            낱 = m.group(0)
            if 낱.lower() in _STOP or len(낱) < 3:
                continue
            if any(a >= x and b <= y for x, y in 가린):       # 표시된 자리는 개념이 아니다
                continue
            if any(a < y and x < b for x, y in 아는곳):        # 사전이 이미 아는 자리
                continue
            if 낱[0].isupper() and not src[:a].rstrip().endswith((".", "", ":")):
                continue                                     # 고유명 후보는 이름 쪽 일이다
            본줄.add(낱.lower())
        셈.update(본줄)
    return 셈


def 점수를_내는_셋() -> set[str]:
    """`data/scoreboard.toml` 이 든 셋들. **이 셋을 캐면 분모를 시험지가 고른다**(§168)."""
    p = ROOT / "data/scoreboard.toml"
    if not p.exists():
        return set()
    return set(re.findall(r'^\s*set\s*=\s*"([^"]+)"', p.read_text(encoding="utf-8"), re.M))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("set", help="평가셋 jsonl")
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--least", type=int, default=3, help="이보다 적게 나온 말은 안 보인다")
    ap.add_argument("--leak-ok", action="store_true",
                    help="기록판에 오른 셋이어도 캔다 — 넣거든 누수 장부에 적는다")
    a = ap.parse_args(argv)

    잰셋 = 점수를_내는_셋()
    몫 = str(a.set).replace("\\", "/")
    걸린 = sorted(s for s in 잰셋 if 몫.endswith(s))
    if 걸린 and not a.leak_ok:
        print(f"  ✗ {걸린[0]} 은 **점수를 내는 셋**이다 — 여기서 캐서 사전에 넣으면 "
              f"시험지가 분모를 고른다(DECISIONS §168 · §192)", file=sys.stderr)
        print("    딴 셋에서 캔다 : python3 tools/mine_terms.py <딴 셋> --top 80\n"
              "    알면서 캔다 : --leak-ok 를 든다 — 그때 장부에 적을 줄을 찍어 준다",
              file=sys.stderr)
        return 1

    rows = [d for d in (json.loads(x) for x in
            paths.줄들(a.set, "셋", ("`ls data/**/*.jsonl` 로 있는 셋을 본다",)))
            if d.get("src")]
    onto = ontology.load()
    셈 = 캔다(rows, onto)
    아는수 = sum(1 for _ in ontology.surfaces(onto))
    print(f"  셋 {len(rows)}줄 · 사전이 아는 표기 {아는수} · 사전 밖 후보 {len(셈)}")
    print("  ※ **후보다.** 공식 한국어 표기를 AWS 한국어 문서와 대조하기 전에는 사전에 안 넣는다\n")
    for 말, n in 셈.most_common(a.top):
        if n < a.least:
            break
        print(f"    {n:>4}줄  {말}")
    if 걸린:
        오늘 = datetime.date.today().isoformat()
        print(f"\n  ⚠ **{걸린[0]} 은 점수를 내는 셋이다.** 여기서 캔 것을 사전에 넣거든 "
              f"`data/ontology/mined.jsonl` 에 이 꼴로 적는다 —")
        print(f'    {{"id": "con.<이름>", "mined_from": "{걸린[0]}", "date": "{오늘}", "note": "…"}}')
        print("    안 적으면 누수가 없어지는 것이 아니라 **안 보이게 된다**(판의 `onto_leak` 이 거짓이 된다)")
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
