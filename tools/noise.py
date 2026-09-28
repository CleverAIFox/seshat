"""같은 팔을 여러 판 돌린 결과에서 **흔들림을 잰다**(DECISIONS §139).

  python3 tools/noise.py runs/H-056-대조-*.jsonl          지표 퍼짐 · 흔들린 줄 수
  python3 tools/noise.py runs/… --lines                   흔들린 줄을 열어 본다

★ **A/B 를 하기 전에 A/A 를 한다.** 처치의 효과를 말하려면 처치가 없을 때의 흔들림을 알아야 한다.
  가설 57개를 세우는 동안 이 저장소는 A/A 를 한 번도 안 했고, 그래서 `tol` 을 짐작으로 적었다.
  짐작한 허용치는 H-055 의 `term_off` −0.0076 을 통과시켰다.
★ **지표가 같다고 출력이 같은 것이 아니다.** 2026-09-28 대조 두 판은 지표 아홉이 소수점 끝까지
  같았는데 **본문은 600 중 7줄이 달랐다.** 온도 0 · seed 고정인데도 ollama 가 다른 글자를 낸다.
  그래서 이 도구는 **둘 다 센다** — 지표 퍼짐과 줄 흔들림은 다른 수다.
★ **셋 · 사전 · 팔이 다르면 거절한다.** 다른 자로 잰 두 수의 차이는 잡음이 아니라 딴 것이다
  (`compare_runs` · `tools/gate.py` 와 같은 규율 · DECISIONS §45).
★ **판이 둘뿐이면 그렇게 적는다.** 쌍 하나로 나온 0 은 「흔들리지 않는다」 가 아니라
  **「한 번 봤더니 같았다」** 다. 넷이면 쌍이 여섯이고, 그때 최댓값이 쓸 만한 `tol` 이다.
"""
from __future__ import annotations

import argparse
import itertools
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from seshat import compare  # noqa: E402

# 흔들림을 볼 지표. `ms` 는 기계 속도지 번역이 아니다 — 여기 넣으면 늘 빨갛다
METRICS = ("term_off", "lit", "keep", "style", "term", "hangul", "josa", "ui", "chrf")
# ★ **축은 `seshat/compare.py` 하나에만 적는다**(DECISIONS §157). 여기 손으로 적었을 때
#   `metrics` 가 빠져 있었다 — 자를 바꾸기 전후의 두 판을 섞어 「잡음」 이라 부를 뻔했다
SAME = compare.AA


def read(path: str | pathlib.Path) -> tuple[dict, dict[str, str]]:
    """(머리줄, {id: 번역}). 머리줄이 없는 파일은 안 받는다 — 재현 조건이 없으면 견줄 수 없다."""
    머리: dict = {}
    줄: dict[str, str] = {}
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        if d.get("meta"):
            머리 = d
        elif d.get("id") is not None:
            줄[d["id"]] = d.get("out", "")
    if not 머리:
        raise SystemExit(f"{pathlib.Path(path).name} 에 머리줄이 없다 — 재현 조건 없는 파일은 안 받는다")
    return 머리, 줄


def 같은_것인가(머리들: list[dict], 이름: list[str]) -> None:
    """★ **거절이 기본이다.** 섞어 재고 「잡음이 크다」 고 적는 것이 가장 나쁜 결과다."""
    for m, n in zip(머리들[1:], 이름[1:]):
        갈린 = compare.갈림(머리들[0], m, SAME)
        if 갈린:
            줄 = "\n".join(f"    {g.이름} — {이름[0]} {g.가 or '없다'} · {n} {g.나 or '없다'}"
                          for g in 갈린)
            raise SystemExit(f"{갈린[0].키} 가 판마다 다르다 — 다른 것을 잰 차이는 잡음이 아니다\n{줄}")


def 퍼짐(머리들: list[dict]) -> dict[str, tuple[float, float, float]]:
    """지표마다 (최소, 최대, 최대−최소). **판 전부에 있는 지표만** 본다 — 없는 것은 0 이 아니다."""
    out = {}
    for m in METRICS:
        값 = [h.get(m) for h in 머리들]
        if any(v is None or not isinstance(v, (int, float)) for v in 값):
            continue
        out[m] = (min(값), max(값), max(값) - min(값))
    return out


def 흔들린_줄(줄들: list[dict[str, str]]) -> dict[str, int]:
    """{id: 이 줄이 낸 서로 다른 번역의 수}. 1 이면 모든 판이 같았다.

    ★ **판마다 없는 id 는 세지 않는다.** 이어 돌린 판은 줄이 빠질 수 있고, 빠진 것을 「달랐다」 로
      세면 흔들림이 부풀려진다.
    """
    공통 = set(줄들[0])
    for d in 줄들[1:]:
        공통 &= set(d)
    return {i: len({d[i] for d in 줄들}) for i in sorted(공통)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="+", help="같은 팔을 여러 판 돌린 결과 파일들")
    ap.add_argument("--lines", action="store_true", help="흔들린 줄을 열어 본다")
    ap.add_argument("--guard", nargs="*", default=["term_off", "lit", "keep"],
                    help="이 지표들의 최대 퍼짐이 쓸 만한 tol 이다")
    a = ap.parse_args(argv)
    if len(a.runs) < 2:
        raise SystemExit("판이 하나면 흔들림을 못 잰다 — 같은 팔을 두 번 이상 돌린다")

    이름 = [pathlib.Path(p).stem for p in a.runs]
    읽은 = [read(p) for p in a.runs]
    머리들, 줄들 = [x[0] for x in 읽은], [x[1] for x in 읽은]
    같은_것인가(머리들, 이름)

    쌍 = len(list(itertools.combinations(a.runs, 2)))
    print(f"  팔 {머리들[0].get('backend')} · 판 {len(a.runs)} · 쌍 {쌍}")
    for n in 이름:
        print(f"      {n}")

    print("\n  지표 퍼짐")
    for m, (lo, hi, d) in 퍼짐(머리들).items():
        표 = " ←" if m in a.guard else ""
        print(f"      {m:<9} {lo:.6f} … {hi:.6f}   퍼짐 {d:.6f}{표}")

    흔 = 흔들린_줄(줄들)
    많 = [i for i, c in 흔.items() if c > 1]
    print(f"\n  줄 흔들림  {len(많)}/{len(흔)} 줄이 판마다 다른 글자를 냈다"
          f" ({100 * len(많) / max(len(흔), 1):.1f}%)")
    if 많:
        갈 = {}
        for i in 많:
            갈[흔[i]] = 갈.get(흔[i], 0) + 1
        print("      서로 다른 번역 수 : " + " · ".join(f"{k}개 {v}줄" for k, v in sorted(갈.items())))

    # ★ **지표가 같아도 본문은 다를 수 있다.** 그 둘을 한 문장으로 내지 않는다(DECISIONS §139)
    쓸 = max((퍼짐(머리들).get(m, (0, 0, 0))[2] for m in a.guard), default=0.0)
    print(f"\n  쓸 만한 tol {쓸:.4f}  — 막는 지표({' · '.join(a.guard)})의 최대 퍼짐")
    if len(a.runs) == 2:
        print("      ※ **판이 둘이다.** 여기 나온 0 은 「흔들리지 않는다」 가 아니라 「한 번 봤더니")
        print("        같았다」 다. 넷이면 쌍이 여섯이고 그때의 최댓값이 박을 만한 수다")
    if 많 and 쓸 == 0.0:
        print(f"      ※ **본문은 {len(많)}줄이 다른데 지표는 안 움직였다** — 지표가 이 변동을 못 본다.")
        print("        tol 이 0 인 것과 파이프라인이 결정적인 것은 다른 말이다")

    if a.lines and 많:
        print("\n  흔들린 줄")
        for i in 많[:20]:
            print(f"      {i}")
            for n, d in zip(이름, 줄들):
                print(f"        {n[-1]} {d[i][:96]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
