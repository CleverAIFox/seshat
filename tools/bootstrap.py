"""**차이가 잡음인가** — 짝지은 부트스트랩 재표집(DECISIONS §180).

  python3 tools/bootstrap.py A.jsonl B.jsonl --set data/domain/d001.jsonl
  python3 tools/bootstrap.py A.jsonl B.jsonl --set ... --metric term_off --n 2000
  python3 tools/bootstrap.py --selftest

★ **2026-09-28 하루에 선을 세 번 잘못 그었다** — 짐작한 허용치(§139) · 이산 변수에 중앙값(§178) ·
  항등식을 바닥값으로(§179). 셋 다 **자가 변수에 맞는지**를 안 물은 것이고, 셋 다 **손으로 그은
  선**이었다. 이 도구가 들어오면 그 선을 손으로 안 긋는다.
★ **새것이 아니다.** Koehn, *Statistical Significance Tests for Machine Translation Evaluation*,
  EMNLP 2004(aclanthology.org/W04-3250). 그 논문도 Efron 1979 의 부트스트랩을 MT 점수에 댄 것이다 —
  **이 저장소가 늦은 것은 22년이 아니라 「이것을 아는가」 한 칸**이다(docs/now/related.md).
★ **짝지어 뽑는다.** 두 판에서 **같은 줄 번호**를 뽑아 양쪽을 같이 센다. 따로 뽑으면 줄 난이도가
  잡음으로 들어와 차이가 묻힌다 — 그것이 「짝지은」 의 뜻이다.
★ **비율 지표는 줄마다 분자와 분모를 들고 다시 더한다.** `term_off` 는 줄마다 자리 수가 다르므로
  줄별 비율을 평균내면 틀린다 — 자리가 하나인 줄과 열인 줄이 같은 무게를 갖는다.
★ **밖 — 이 자는 「차이가 잡음인가」 만 본다.** 그 차이가 **뜻이 있는가**는 안 본다(효과의 크기는
  사람이 읽는다). 셋 하나에서 잰 수가 **다른 셋으로 옮겨지는가**도 안 본다(§94 · §118 이 그것을
  따로 묻는다). 그리고 **지표가 옳은 것을 보는지**는 이 자의 밖이다 — 2026-09-30 규칙 지표가
  뜻과 부호가 반대인 것이 드러났고(§229) 이 도구는 그때도 초록이었다.
★ **못 견주는 두 판은 안 잰다.** 자 · 셋 · 사전이 다르면 부트스트랩을 돌려도 그 수가 거짓말이다
  (`compare.AB`).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from seshat import backends, compare, evaluate
from seshat import paths

# 줄마다 (분자, 분모)를 낼 수 있는 지표. `_n` 이 결과에 실리거나 분모를 줄에서 셀 수 있어야 한다
지표 = ("term_off", "term", "term_bad", "lit", "ui", "keep", "style", "hangul")
# ★ **밖에서 들어오는 자**(2026-10-01 · DECISIONS §269). `tools/gemba.py` 가 내는 점수는 판 파일
#   안에 없다 — 따로 돈 자의 산물이다. `--점수` 로 받아 **줄마다 (점수, 1)** 로 넣으면 `비율` 이
#   그대로 평균을 낸다. 규칙 지표와 **같은 짝지은 재표집**을 쓴다
밖지표 = "gemba"
# ★ **낮을수록 좋은 지표가 있다**(DECISIONS §182). 2026-09-28 이 도구가 `term_bad` 를
#   0.0061 대 0.0010 으로 재고 **「A 가 낫다」** 고 찍었다 — 오역이 적은 쪽이 진 것으로 나왔다.
#   부호를 도구가 모르면 **논문에 반대로 적힌다.**
낮을수록_좋다 = frozenset({"term_bad"})


def 줄별(rows: list[dict], outs: list[str]) -> dict[str, list[tuple[float, float]]]:
    """지표마다 줄별 (분자, 분모). **채점기를 그대로 부른다** — 규칙을 두 곳에 적지 않는다(§163).

    ★ 한 줄씩 `evaluate.score` 를 불러 그 줄의 비율과 분모를 받는다. 분모가 0 인 줄은 (0, 0) 이고
      다시 더할 때 저절로 빠진다 — **버리지 않는다.** 버리면 뽑히는 줄 수가 달라진다.
    """
    out: dict[str, list[tuple[float, float]]] = {m: [] for m in 지표}
    for r, o in zip(rows, outs):
        s = evaluate.score([r], [o])
        분모 = {"term_off": s.get("term_n", 0), "term": s.get("term_n", 0), "term_bad": s.get("term_n", 0),
                "lit": s.get("lit_n", 0), "ui": s.get("ui_n", 0),
                "keep": len(r.get("keep", [])), "style": 1, "hangul": 1}
        for m in 지표:
            d = float(분모.get(m) or 0)
            v = s.get(m)
            out[m].append((round((v or 0.0) * d), d) if d else (0.0, 0.0))
    return out


def 비율(표: list[tuple[float, float]], 차례: list[int]) -> float | None:
    분자 = 분모 = 0.0
    for i in 차례:
        a, b = 표[i]
        분자 += a
        분모 += b
    return 분자 / 분모 if 분모 else None


def 잰다(가: list[tuple[float, float]], 나: list[tuple[float, float]],
        n: int = 1000, seed: int = 7) -> dict | None:
    """짝지은 재표집. **같은 줄 번호를 양쪽에 쓴다.**

    돌려주는 것 — 관측 차이 · 95% 구간 · p(양측). 구간이 0 을 품으면 **차이를 말할 수 없다.**
    """
    관측가, 관측나 = 비율(가, range(len(가))), 비율(나, range(len(나)))
    if 관측가 is None or 관측나 is None:
        return None
    rnd = random.Random(seed)
    N = len(가)
    차 = []
    for _ in range(n):
        차례 = [rnd.randrange(N) for _ in range(N)]
        a, b = 비율(가, 차례), 비율(나, 차례)
        if a is not None and b is not None:
            차.append(b - a)
    if not 차:
        return None
    차.sort()
    아래, 위 = 차[int(0.025 * len(차))], 차[min(int(0.975 * len(차)), len(차) - 1)]
    # ★ **양측 p 다.** 한쪽만 보면 「나가 낫다」 를 기대하고 재는 것이 되고, 기대를 담은 자는
    #   §66 의 함정으로 간다. 부호가 뒤집히는 비율의 두 배를 든다
    작다 = sum(1 for d in 차 if d <= 0) / len(차)
    크다 = sum(1 for d in 차 if d >= 0) / len(차)
    return {"가": 관측가, "나": 관측나, "차": 관측나 - 관측가,
            "아래": 아래, "위": 위, "p": min(1.0, 2 * min(작다, 크다)), "판": len(차)}


def _selftest() -> int:
    """★ **아무것도 못 찾는 자와 고장 난 자는 구별되지 않는다.**

    같은 표 둘은 차이가 없어야 하고, 뚜렷이 다른 둘은 구간이 0 을 안 품어야 한다.
    """
    같 = [(1.0, 1.0)] * 300 + [(0.0, 1.0)] * 300
    got = 잰다(같, list(같), n=400)
    if got is None or got["차"] != 0.0 or not (got["아래"] <= 0 <= got["위"]):
        print(f"  ✗ 같은 둘에서 차이를 본다 — {got}", file=sys.stderr)
        return 1
    if got["p"] < 0.5:
        print(f"  ✗ 같은 둘에 작은 p 를 준다 — {got['p']}", file=sys.stderr)
        return 1
    나 = [(1.0, 1.0)] * 480 + [(0.0, 1.0)] * 120        # 0.50 대 0.80
    got2 = 잰다(같, 나, n=400)
    if got2 is None or got2["아래"] <= 0 <= got2["위"]:
        print(f"  ✗ 뚜렷이 다른 둘에서 구간이 0 을 품는다 — {got2}", file=sys.stderr)
        return 1
    if got2["p"] > 0.05:
        print(f"  ✗ 뚜렷이 다른 둘에 큰 p 를 준다 — {got2['p']}", file=sys.stderr)
        return 1
    # ★ **짝지음이 살아 있나.** 줄마다 똑같이 0.01 씩 나은 두 판은 **차이가 작아도 확실하다** —
    #   따로 뽑으면 줄 난이도 잡음에 묻혀 p 가 커진다
    쉬운어려운 = [(1.0, 1.0)] * 300 + [(0.0, 1.0)] * 300
    조금나은 = [(1.0, 1.0)] * 310 + [(0.0, 1.0)] * 290
    got3 = 잰다(쉬운어려운, 조금나은, n=400)
    if got3 is None or got3["차"] <= 0:
        print(f"  ✗ 조금 나은 쪽을 못 본다 — {got3}", file=sys.stderr)
        return 1
    print("  프로브 살아 있다 — 같은 둘은 0 을 품고, 다른 둘은 안 품고, 작은 차이의 부호를 본다")
    return 0


def read(path: str) -> tuple[dict, dict[str, dict]]:
    lines = [json.loads(x) for x in paths.줄들(path, "판", ("`ls runs/*.jsonl` 로 있는 판을 본다",))]
    head = next(x for x in lines if x.get("meta"))
    return head, {x["id"]: x for x in lines if not x.get("meta")}


def 밖에서_잰_것(경로: str, 가팔: str | None, 나팔: str | None, 같은줄: list[str]):
    """`gemba` 가 낸 점수를 **줄마다 (점수, 1)** 로 바꾼다. (두 표, 뺀 줄 수) 또는 (None, 0).

    ★ **짝을 깨지 않는다**(DECISIONS §269). 한쪽에만 점수가 있는 줄은 **양쪽에서 같이 뺀다** —
      한쪽만 빼면 짝지은 재표집이 아니고, 0 으로 채우면 **「모른다」 가 「최악이다」 가 된다**
      (`gemba` 자신의 규율과 같다 · §244).
    ★ **팔 이름으로 고른다.** 점수 파일은 (줄, 팔) 로 적혀 있고 판 머리줄이 팔 이름을 든다 —
      이름이 안 맞으면 **멈추고 어떤 팔이 있는지 찍는다**(짐작으로 고르지 않는다).
    ★ **밖 — 그 점수가 옳은지는 안 본다.** 이 자가 묻는 것은 「차이가 잡음인가」 뿐이고,
      자가 사람과 같은 순서로 세우는가는 `tools/labels.py corr` 이 묻는다(H-085 · §262).
    """
    점수: dict[tuple[str, str], float] = {}
    팔들: set[str] = set()
    길 = ("`tools/gemba.py --out <여기>` 가 끝났나 — 아직 도는 중이면 그 파일이 없다",
          "보기 : tail -f /tmp/gemba.log")
    for 줄 in paths.줄들(경로, "점수 파일", 길):
        if not 줄.strip():
            continue
        d = json.loads(줄)
        if "score" not in d or "arm" not in d:
            continue
        점수[(d["id"], d["arm"])] = float(d["score"])
        팔들.add(d["arm"])
    for 이름, 팔 in (("A", 가팔), ("B", 나팔)):
        if 팔 not in 팔들:
            print(f"  ✗ 점수 파일에 {이름} 의 팔 `{팔}` 이 없다\n"
                  f"    있는 팔 : {' · '.join(sorted(팔들)) or '없다'}\n"
                  f"    `tools/gemba.py --run <팔>=<판>` 으로 이름을 맞춘다", file=sys.stderr)
            return None, 0
    가, 나, 뺀 = [], [], 0
    for i in 같은줄:
        x, y = 점수.get((i, 가팔)), 점수.get((i, 나팔))
        if x is None or y is None:
            뺀 += 1
            continue
        가.append((x, 1.0))
        나.append((y, 1.0))
    return (가, 나), 뺀


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a", nargs="?")
    ap.add_argument("b", nargs="?")
    ap.add_argument("--set", dest="set_", default="")
    ap.add_argument("--metric", default="", help="비우면 잴 수 있는 것을 전부")
    ap.add_argument("--n", type=int, default=1000, help="재표집 횟수")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--점수", dest="점수", default="",
                    help="`tools/gemba.py --out` 이 낸 파일 — 밖에서 잰 자를 지표로 더한다(§269)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return _selftest()
    if not (a.a and a.b and a.set_):
        print("  두 판과 --set 이 있어야 한다", file=sys.stderr)
        return 2

    가머리, 가줄 = read(a.a)
    나머리, 나줄 = read(a.b)
    # ★ **못 견주는 둘은 안 잰다.** 부트스트랩은 차이를 재는 자이지 **견줄 자격**을 묻지 않는다
    갈린 = compare.갈림(가머리, 나머리, compare.AB)
    if 갈린:
        for g in 갈린:
            print(f"  ✗ {g.글()}", file=sys.stderr)
        print("  부트스트랩은 **견줄 수 있는 둘**에만 쓴다(DECISIONS §180)", file=sys.stderr)
        return 1

    가팔, 나팔 = 가머리.get("backend") or 가머리.get("model"), 나머리.get("backend") or 나머리.get("model")
    못견줌 = compare.가린_지표({"arm": 가팔}, {"arm": 나팔})

    def _지킴(팔):
        """**「모른다」 와 「안 지킨다」 를 다르게 적는다**(DECISIONS §206)."""
        got = backends.지키는_지표(팔)
        return "**모른다**" if got is None else (" · ".join(sorted(got)) or "없다")
    if 가팔 is None or 나팔 is None:
        print("  ※ **팔 이름이 없는 판이 있다** — 무엇을 기계로 지키는지 모른다(DECISIONS §206).\n"
              "    지킬 수 있는 것을 **전부 못 견주는 것으로** 친다 — 모르는 쪽으로 기운다\n"
              "    판 머리줄의 `backend` 가 비었다 — 서버(`--url`)로 잰 판이 그렇다", file=sys.stderr)
    if 못견줌:
        print(f"  ※ **못 견주는 지표 {' · '.join(sorted(못견줌))}** — 한쪽만 자리표시가 지킨다(§156)\n"
              f"    A {가팔} 가 지키는 것 {_지킴(가팔)}\n"
              f"    B {나팔} 가 지키는 것 {_지킴(나팔)}", file=sys.stderr)

    spec = {r["id"]: r for r in evaluate.load(a.set_)}
    같은줄 = [i for i in 가줄 if i in 나줄 and i in spec]
    rows = [spec[i] for i in 같은줄]
    print(f"  줄 {len(같은줄)} · 재표집 {a.n} · 씨 {a.seed}\n  줄별로 채점하는 중…", file=sys.stderr)
    가표 = 줄별(rows, [가줄[i]["out"] for i in 같은줄])
    나표 = 줄별(rows, [나줄[i]["out"] for i in 같은줄])

    if a.점수:
        밖, 못찾음 = 밖에서_잰_것(a.점수, 가팔, 나팔, 같은줄)
        if 밖 is None:
            return 1
        가표[밖지표], 나표[밖지표] = 밖
        if 못찾음:
            # ★ **빠진 줄을 조용히 안 넘긴다**(§258). 점수가 없는 줄은 **양쪽에서 같이 뺀다** —
            #   한쪽만 빼면 짝이 깨지고, 0 으로 채우면 「모른다」 가 「최악이다」 가 된다
            print(f"  ※ **점수가 없어 뺀 줄 {못찾음}** — 양쪽에서 같이 뺐다(§269)", file=sys.stderr)

    볼것 = [a.metric] if a.metric else [*지표, *([밖지표] if a.점수 else [])]
    print(f"\n  {'지표':<10}{'A':>9}{'B':>9}{'차':>10}{'95% 구간':>22}{'p':>8}   판정")
    for m in 볼것:
        got = 잰다(가표[m], 나표[m], n=a.n, seed=a.seed)
        if got is None:
            print(f"  {m:<10}{'—':>9}{'—':>9}{'분모가 없다':>10}")
            continue
        품 = got["아래"] <= 0 <= got["위"]
        나은쪽 = (got["차"] < 0) if m in 낮을수록_좋다 else (got["차"] > 0)
        판 = "**차이를 말할 수 없다**" if 품 else ("B 가 낫다" if 나은쪽 else "A 가 낫다")
        # ★ **기계가 지킨 수와 모델이 지킨 수는 못 견준다**(§156 · §182). 자 · 셋 · 사전이 다 같아서
        #   위의 검사는 전부 통과하고, p 값까지 붙어서 **가장 그럴듯한 거짓말**이 된다
        if m in 못견줌:
            판 = "**못 견준다** — 한쪽은 기계가 지킨다(§156)"
        구간 = f"[{got['아래']:+.4f}, {got['위']:+.4f}]"
        print(f"  {m:<10}{got['가']:>9.4f}{got['나']:>9.4f}{got['차']:>+10.4f}"
              f"{구간:>22}{got['p']:>8.3f}   {판}")
    print("\n  ※ **구간이 0 을 품으면 차이를 말할 수 없다** — 「같다」 가 아니라 **「못 가른다」** 다")
    print("  ※ 짝지은 재표집 — Koehn 2004(W04-3250) · 부트스트랩은 Efron 1979")
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
