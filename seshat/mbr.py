"""최소 베이즈 위험(MBR) — **정답 없이** 후보 여럿에서 하나를 고른다(DECISIONS §133).

  from seshat import mbr
  mbr.pick(["가", "나", "가"])        # 나머지와 가장 닮은 것

★ **학습이 아니라 시간으로 품질을 산다.** 같은 모델을 N 번 불러 후보를 뽑고, **나머지 후보들과 가장
  닮은 것**을 고른다. 정답이 없어도 된다 — 다른 후보가 서로의 참조가 된다. N 배 느려지고 값은 0 이다.
★ **왜 4B 에 맞는 수인가.** 4B 가 지는 곳은 어순을 다시 짜는 자리다(DECISIONS §129). 자리 옮기기는
  **한 번에 되거나 안 되거나**여서 후보마다 갈린다 — 여덟 중 다섯이 제대로 옮겼으면 그 다섯이
  서로 닮고, 잘못 옮긴 셋은 서로도 안 닮는다. **다수가 옳을 때 MBR 이 그것을 찾는다.**
★ **다수가 틀리면 MBR 도 틀린다.** 모델이 늘 같은 자리에서 같게 무너지면 후보 여덟이 사이좋게
  무너지고, MBR 은 그 합의를 고른다. 그래서 이것은 **모델을 좋게 만드는 것이 아니라 흔들림을 줄이는 것**이다.
★ **효용은 chrF++ 다.** 지표(`evaluate`)와 같은 자를 쓴다 — 고르는 자와 재는 자가 다르면 무엇이
  좋아졌는지 모른다. 다만 그래서 **chrF 가 보는 것만 좋아진다.** `lit` · `term_off` 는 따로 본다.
"""
from __future__ import annotations

# 처치가 일했는지를 결과가 말한다 — 안 걸린 것과 걸렸는데 못 고친 것은 다르다(DECISIONS §60)
STATS: dict[str, float] = {"판": 0, "첫째_아님": 0, "모두_같음": 0, "퍼짐_합": 0.0}


def reset() -> None:
    STATS.update({"판": 0, "첫째_아님": 0, "모두_같음": 0, "퍼짐_합": 0.0})


def _chrf(hyp: str, ref: str) -> float:
    import sacrebleu
    return sacrebleu.sentence_chrf(hyp, [ref], word_order=2).score


def score(cands: list[str]) -> list[float]:
    """후보마다 **나머지에 대한 평균 chrF**. 자기 자신은 안 센다."""
    n = len(cands)
    if n < 2:
        return [0.0] * n
    return [sum(_chrf(c, o) for j, o in enumerate(cands) if j != i) / (n - 1)
            for i, c in enumerate(cands)]


def pick(cands: list[str]) -> str:
    """나머지와 가장 닮은 후보. **같은 입력이면 같은 답이다** — 동점이면 먼저 온 것을 든다.

    ★ 빈 후보는 버리지 않는다. 버리면 「모델이 아무것도 안 뱉었다」 가 점수에서 사라진다 —
      빈 것은 다른 후보와 안 닮아 저절로 진다. **못 한 것을 없던 일로 만들지 않는다.**
    """
    if not cands:
        return ""
    STATS["판"] += 1
    if len(set(cands)) == 1:
        STATS["모두_같음"] += 1
        return cands[0]
    s = score(cands)
    최고 = max(s)
    STATS["퍼짐_합"] += 최고 - min(s)
    i = s.index(최고)
    STATS["첫째_아님"] += i != 0
    return cands[i]
