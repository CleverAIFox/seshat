"""교사 돌림에서 증류셋을 뽑는다 — 두 자로 거른다.

2026-10-02. gemba 하나로는 모자란다. 영어를 글자 하나 안 바꾸고 돌려준 줄에
100점을 줬다(`k001-0078` · `k001-2795`). 그래서 품질 점수와 **번역이기는 한가**를
따로 묻고 둘 다 통과한 줄만 남긴다.

★ 밖 — **번역이 맞는지 다시 보지 않는다.** 여기는 두 검사의 결과를 합치는
  자리일 뿐이고, 뜻을 보는 것은 gemba, 모양을 보는 것은 escape 다. 여기서
  세 번째 기준을 만들지 않는다 — 만들면 판단이 세 곳에 살게 된다.

★ 밖 — **점수를 다시 매기지 않는다.** gemba 머리줄의 model 과 체계_sha 를
  그대로 베껴 낸다. 여기서 모델 이름을 짓거나 고르면 어느 자로 쟀는지가
  결과 파일에서 사라진다.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from seshat import paths
from tools.escape import 이탈


def 줄줄이(경로: str, 무엇: str, 길: tuple[str, ...] = ()):
    for 한줄 in paths.줄들(경로, 무엇, 길):
        yield json.loads(한줄)


def 점수를_읽는다(경로: str) -> tuple[dict, dict]:
    """(id→점수, 머리줄). 머리줄이 없으면 어느 자로 쟀는지 모르므로 멈춘다."""
    점, 머리 = {}, None
    for d in 줄줄이(경로, "gemba 점수", ("uv run python tools/gemba.py 로 먼저 잰다",)):
        if d.get("meta"):
            if 머리 is None and d.get("model"):
                머리 = d
            continue
        점[d["id"]] = d["score"]
    if 머리 is None:
        raise SystemExit(
            f"머리줄이 없다 — 어느 모델로 쟀는지 모른다: {경로}\n"
            f"    head -1 {경로} 로 본다 — `model` 과 `체계_sha` 를 든 줄이 맨 앞에 있어야 한다\n"
            f"    없으면 gemba 를 처음부터 다시 돌린다 — **이어 돌리기로는 머리줄이 안 생긴다**")
    return 점, 머리


def main() -> int:
    받 = argparse.ArgumentParser()
    받.add_argument("--돌림", required=True, help="runs/<교사 돌림>.jsonl")
    받.add_argument("--점수", required=True, help="runs/<gemba 결과>.jsonl")
    받.add_argument("--낼곳", required=True, help="data/distill/<이름>.jsonl")
    받.add_argument("--문턱", type=float, default=90.0, help="gemba 점수 하한 (기본 90)")
    고 = 받.parse_args()

    점, 머리 = 점수를_읽는다(고.점수)
    돌림 = {d["id"]: d for d in 줄줄이(고.돌림, "교사 돌림") if d.get("id")}

    없는점수 = [i for i in 돌림 if i not in 점]
    if 없는점수:
        raise SystemExit(
            f"점수가 없는 줄이 {len(없는점수)}건 있다 — 두 파일이 같은 돌림이 아니다\n"
            f"    gemba 를 이 돌림에 대해 끝까지 돌렸는지 본다 (--resume)")

    산것, 버린것 = [], Counter()
    for i in sorted(돌림):
        d = 돌림[i]
        갈 = 이탈(d.get("src", ""), d.get("out", ""))
        if 갈:
            버린것[갈] += 1
            continue
        if 점[i] < 고.문턱:
            버린것[f"{고.문턱:.0f}점 미만"] += 1
            continue
        산것.append({"id": i, "src": d["src"], "out": d["out"], "score": 점[i]})

    낼 = Path(고.낼곳)
    낼.parent.mkdir(parents=True, exist_ok=True)
    with 낼.open("w", encoding="utf-8") as f:
        f.write(json.dumps({
            "meta": True,
            "교사돌림": Path(고.돌림).name,
            "점수파일": Path(고.점수).name,
            "자": 머리.get("자"),
            "model": 머리.get("model"),
            "대장이름": 머리.get("대장이름"),
            "체계_sha": 머리.get("체계_sha"),
            "문턱": 고.문턱,
            "이탈검사": "tools/escape.py::이탈",
            "들어온줄": len(돌림),
            "낸줄": len(산것),
            "note": "두 자를 AND 로 걸렀다 — gemba 는 뜻을, escape 는 번역 여부를 본다",
        }, ensure_ascii=False) + "\n")
        for r in 산것:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    들 = len(돌림)
    print(f"{고.낼곳} — {len(산것)}줄 / {들}줄  ({len(산것) / 들 * 100:.1f}%)")
    print(f"  자: {머리.get('model')} · 문턱 {고.문턱:.0f}점 + 이탈 검사\n")
    for k, v in 버린것.most_common():
        print(f"  버림  {k:<12} {v:>5}건")
    print(f"  {'버림 합':<18} {sum(버린것.values()):>5}건")
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
