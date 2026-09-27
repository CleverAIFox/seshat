"""결과를 **문법 축으로 갈라** 다시 센다 — 「4B 가 나쁘다」 를 「4B 가 어디서 나쁘다」 로(DECISIONS §125).

  python3 tools/slice.py runs/H-045-4b-d001-*.jsonl --set data/domain/d001.jsonl
  python3 tools/slice.py A.jsonl B.jsonl --set …            두 팔을 축마다 나란히
  python3 tools/slice.py --labels labels/d001-60.claude.jsonl --set …   사람 판정을 축으로

★ **새로 재지 않는다.** 이미 있는 결과 파일을 다시 셀 뿐이라 모델도 돈도 안 든다. 가설의 문을
  안 지나가는 까닭이다 — 이 도구는 잰 것을 보는 도구이지 재는 도구가 아니다.
★ **줄이 적은 축은 숫자가 흔들린다.** 분모를 늘 같이 찍는다(DECISIONS §70). `최상급` 은 d001 에
  15줄뿐이다 — 그 칸의 0.87 과 1.00 은 한 줄 차이다.
★ **축은 겹친다.** 한 줄이 관형절이면서 피동일 수 있고, 그래서 세로합이 전체와 다르다. 그것이 맞다.
★ 연쇄 축의 정확도는 0.68 이다(DECISIONS §125). **한 줄을 두고 말하는 자가 아니라 무더기를 가르는
  자다** — 두 팔을 같은 무더기에서 견주므로 잡음은 양쪽에 같이 든다.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from seshat import evaluate, grammar  # noqa: E402

SHOW = ("term_off", "term", "keep", "lit", "hangul", "style")


def 축_of(rows: list[dict]) -> dict[str, tuple[str, ...]]:
    """줄 id → 축들. 표시된 자리는 연쇄에서 뺀다(DECISIONS §122)."""
    return {r["id"]: grammar.axes(r["src"], evaluate.marked(r)) for r in rows}


def read_run(path: str) -> tuple[dict, dict[str, str]]:
    lines = [json.loads(x) for x in pathlib.Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
    head = next((x for x in lines if x.get("meta")), {})
    return head, {x["id"]: x["out"] for x in lines if not x.get("meta") and "out" in x}


def read_labels(path: str) -> dict[str, dict[str, str]]:
    """`labels.py read` 가 레이크에 넣은 판정 → **팔마다** {줄 id: 판정}(DECISIONS §103).

    ★ **한 장에 팔이 여럿 든다.** 눈가림 채점표가 같은 줄의 세 팔을 섞어 내므로, 파일 하나에
      `(id, arm)` 짝이 줄 수의 몇 배로 들어 있다. `id` 만으로 모으면 **마지막 팔이 앞의 것을
      덮는다** — 팔을 견주려고 만든 자가 팔을 지워 버린다.
    """
    out: dict[str, dict[str, str]] = {}
    for x in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        if not x.strip():
            continue
        d = json.loads(x)
        if not d.get("meta") and d.get("id") and d.get("verdict"):
            out.setdefault(d.get("arm", "?"), {})[d["id"]] = d["verdict"]
    if not out:
        raise SystemExit(f"{pathlib.Path(path).name} 에 판정이 없다 — 0 건이 아니라 못 읽은 것이다")
    return out


def by_axis(rows: list[dict], outs: dict[str, str]) -> dict[str, dict]:
    """축마다 그 축에 든 줄만 모아 다시 채점한다."""
    축 = 축_of(rows)
    got = {}
    for ax in ("전체", *grammar.AXES):
        골 = [r for r in rows if (ax == "전체" or ax in 축[r["id"]]) and r["id"] in outs]
        if 골:
            got[ax] = evaluate.score(골, [outs[r["id"]] for r in 골])
    return got


def by_axis_labels(rows: list[dict], verdicts: dict[str, str]) -> dict[str, dict]:
    """한 팔의 판정을 축으로 가른다. **「뜻이 맞다」 비율만 본다**(H-046)."""
    축 = 축_of(rows)
    got = {}
    for ax in ("전체", *grammar.AXES):
        골 = [i for i in verdicts if i in 축 and (ax == "전체" or ax in 축[i])]
        if 골:
            got[ax] = {"n": len(골), "맞다": sum(verdicts[i] == "맞다" for i in 골) / len(골)}
    return got


def _칸(v) -> str:
    return "     —" if v is None else (f"{v:6.3f}" if isinstance(v, float) else f"{v:>6}")


def _맞다칸(c: dict | None) -> str:
    """축마다 「뜻이 맞다」 비율과 **분모**. 분모 없이 비율만 두면 한 줄짜리 칸을 믿게 된다(§70)."""
    if not c:
        return " " * 14
    글 = "%.3f /%d" % (c["맞다"], c["n"])
    return 글.rjust(14)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="*", help="결과 파일. 여럿이면 축마다 나란히 찍는다")
    ap.add_argument("--set", required=True)
    ap.add_argument("--labels", action="append", default=[], help="판정 파일. 축마다 「뜻이 맞다」 비율")
    ap.add_argument("--metric", default="term_off", help=f"여러 팔을 견줄 때 볼 지표 — {' · '.join(SHOW)}")
    a = ap.parse_args(argv)
    if not a.runs and not a.labels:
        raise SystemExit("결과 파일이나 --labels 가 하나는 있어야 한다")
    rows = evaluate.load(a.set)

    for p in a.labels:
        팔 = read_labels(p)
        표 = {arm: by_axis_labels(rows, v) for arm, v in sorted(팔.items())}
        print(f"\n  {pathlib.Path(p).name} — 「뜻이 맞다」 비율 · 팔 {len(표)}")
        print(f"  {'축':<8}" + "".join(f"{arm[:12]:>14}" for arm in 표))
        for ax in ("전체", *grammar.AXES):
            if not any(ax in v for v in 표.values()):
                continue
            print(f"  {ax:<8}" + "".join(_맞다칸(v.get(ax)) for v in 표.values()))

    for p in a.runs:
        head, outs = read_run(p)
        got = by_axis(rows, outs)
        if len(a.runs) == 1:
            print(f"\n  {pathlib.Path(p).name}  {head.get('model') or head.get('backend') or ''}")
            print(f"  {'축':<8}{'n':>5}" + "".join(f"{m:>9}" for m in SHOW))
            for ax, s in got.items():
                print(f"  {ax:<8}{s['n']:>5}" + "".join(_칸(s.get(m)).rjust(9) for m in SHOW))
        else:
            if p == a.runs[0]:
                print(f"\n  {a.metric} — 축마다")
                print(f"  {'축':<8}{'n':>5}" + "".join(f"{pathlib.Path(x).stem[:14]:>16}" for x in a.runs))
            # 여러 팔은 아래에서 한 번에 찍는다
    if len(a.runs) > 1:
        모 = {p: by_axis(rows, read_run(p)[1]) for p in a.runs}
        첫 = next(iter(모.values()))
        for ax in 첫:
            print(f"  {ax:<8}{첫[ax]['n']:>5}" + "".join(_칸(모[p].get(ax, {}).get(a.metric)).rjust(16) for p in a.runs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
