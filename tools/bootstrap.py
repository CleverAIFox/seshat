"""**차이가 잡음인가** — 짝지은 부트스트랩 재표집(DECISIONS §180).

  python3 tools/bootstrap.py A.jsonl B.jsonl --set data/domain/d001.jsonl
  python3 tools/bootstrap.py A.jsonl B.jsonl --set ... --metric term_off --n 2000
  python3 tools/bootstrap.py --selftest

★ **2026-09-28 하루에 선을 세 번 잘못 그었다** — 짐작한 허용치(§139) · 이산 변수에 중앙값(§178) ·
  항등식을 바닥값으로(§179). 셋 다 **자가 변수에 맞는지**를 안 물은 것이고, 셋 다 **손으로 그은
  선**이었다. 이 도구가 들어오면 그 선을 손으로 안 긋는다.
★ **새것이 아니다.** Koehn, *Statistical Significance Tests for Machine Translation Evaluation*,
  EMNLP 2004(aclanthology.org/W04-3250). 그 논문도 Efron 1979 의 부트스트랩을 MT 점수에 댄 것이다 —
  **이 저장소가 늦은 것은 22년이 아니라 「이것을 아는가」 한 칸**이다(docs/related.md).
★ **짝지어 뽑는다.** 두 판에서 **같은 줄 번호**를 뽑아 양쪽을 같이 센다. 따로 뽑으면 줄 난이도가
  잡음으로 들어와 차이가 묻힌다 — 그것이 「짝지은」 의 뜻이다.
★ **비율 지표는 줄마다 분자와 분모를 들고 다시 더한다.** `term_off` 는 줄마다 자리 수가 다르므로
  줄별 비율을 평균내면 틀린다 — 자리가 하나인 줄과 열인 줄이 같은 무게를 갖는다.
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
from seshat import compare, evaluate  # noqa: E402

# 줄마다 (분자, 분모)를 낼 수 있는 지표. `_n` 이 결과에 실리거나 분모를 줄에서 셀 수 있어야 한다
지표 = ("term_off", "term", "term_bad", "lit", "ui", "keep", "style", "hangul")


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
    lines = [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
    head = next(x for x in lines if x.get("meta"))
    return head, {x["id"]: x for x in lines if not x.get("meta")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a", nargs="?")
    ap.add_argument("b", nargs="?")
    ap.add_argument("--set", dest="set_", default="")
    ap.add_argument("--metric", default="", help="비우면 잴 수 있는 것을 전부")
    ap.add_argument("--n", type=int, default=1000, help="재표집 횟수")
    ap.add_argument("--seed", type=int, default=7)
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

    spec = {r["id"]: r for r in evaluate.load(a.set_)}
    같은줄 = [i for i in 가줄 if i in 나줄 and i in spec]
    rows = [spec[i] for i in 같은줄]
    print(f"  줄 {len(같은줄)} · 재표집 {a.n} · 씨 {a.seed}\n  줄별로 채점하는 중…", file=sys.stderr)
    가표 = 줄별(rows, [가줄[i]["out"] for i in 같은줄])
    나표 = 줄별(rows, [나줄[i]["out"] for i in 같은줄])

    볼것 = [a.metric] if a.metric else list(지표)
    print(f"\n  {'지표':<10}{'A':>9}{'B':>9}{'차':>10}{'95% 구간':>22}{'p':>8}   판정")
    for m in 볼것:
        got = 잰다(가표[m], 나표[m], n=a.n, seed=a.seed)
        if got is None:
            print(f"  {m:<10}{'—':>9}{'—':>9}{'분모가 없다':>10}")
            continue
        품 = got["아래"] <= 0 <= got["위"]
        판 = "**차이를 말할 수 없다**" if 품 else ("B 가 낫다" if got["차"] > 0 else "A 가 낫다")
        구간 = f"[{got['아래']:+.4f}, {got['위']:+.4f}]"
        print(f"  {m:<10}{got['가']:>9.4f}{got['나']:>9.4f}{got['차']:>+10.4f}"
              f"{구간:>22}{got['p']:>8.3f}   {판}")
    print("\n  ※ **구간이 0 을 품으면 차이를 말할 수 없다** — 「같다」 가 아니라 **「못 가른다」** 다")
    print("  ※ 짝지은 재표집 — Koehn 2004(W04-3250) · 부트스트랩은 Efron 1979")
    return 0


if __name__ == "__main__":
    sys.exit(main())
