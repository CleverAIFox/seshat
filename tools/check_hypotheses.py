"""가설 대장이 실험의 문을 지키는가(DECISIONS §12).

  python3 tools/check_hypotheses.py      검사한다. 위반 1 · 고장 2

★ **seshat 은 연구다.** 직관 → 가설 → 가장 싼 검증 → 채택 · 기각. 대장의 한 줄이 한 가설이다.
★ **검증 방법과 비용 상한이 없는 가설은 실험에 들어가지 못한다.** 무엇을 확인하려는지 없이 잰 숫자는
  쓸 데가 없고, 상한 없이 도는 실험은 돈을 태운다.
★ **판정은 근거를 든다.** 채택 · 기각은 `runs/` 의 결과 파일이나 DECISIONS 절을 가리킨다. 근거 없는
  판정은 의견이다.
★ 번호는 PLAN 과 같은 규칙이다 — 영구 식별자 · 오름차순 · 재사용 금지.

| 열 | 규칙 |
|---|---|
| H | `H-NNN` · 유일 · 오름차순 |
| 상태 | 제안 · 실험 · 채택 · 기각 |
| 트랙 | `R1`–`R7` (MASTER §7) |
| 검증 · 상한 | 실험 · 채택 · 기각이면 비지 않는다. 상한은 `$N` · `0` · `T4 N시간` · `장비 N시간` |
| 근거 | 채택 · 기각이면 `runs/…` 또는 `DECISIONS §N` |
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LEDGER = ROOT / "docs/next/hypotheses.md"
STATES = {"제안", "실험", "채택", "기각"}
TRACKS = {f"R{i}" for i in range(1, 8)}
ROW = re.compile(r"^\| (H-\d{3}) \|(.*)\|\s*$")
CAP = re.compile(r"^(\$\d+(\.\d+)?|0|T4 \d+시간|장비 \d+시간)$")
EVIDENCE = re.compile(r"(runs/\S+|DECISIONS §\d+)")


def rows(text: str) -> list[tuple[int, str, list[str]]]:
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        m = ROW.match(line)
        if m:
            out.append((n, m.group(1), [c.strip() for c in m.group(2).split("|")]))
    return out


def check(text: str) -> list[str]:
    fails, prev, seen = [], 0, set()
    rs = rows(text)
    if not rs:
        return ["가설이 한 줄도 없다"]
    for n, h, cells in rs:
        where = f"hypotheses.md:{n} {h}"
        if len(cells) != 6:
            fails.append(f"{where} 열이 {len(cells) + 1} 개다 — H · 상태 · 트랙 · 직관 · 검증 · 상한 · 근거 일곱")
            continue
        state, track, idea, method, cap, evidence = cells
        num = int(h[2:])
        if h in seen:
            fails.append(f"{where} 번호가 겹친다")
        elif num <= prev:
            fails.append(f"{where} 번호가 오름차순이 아니다")
        seen.add(h)
        prev = max(prev, num)
        if state not in STATES:
            fails.append(f"{where} 상태 '{state}' 가 어휘 밖이다 — {sorted(STATES)}")
        if track not in TRACKS:
            fails.append(f"{where} 트랙 '{track}' 가 R1–R7 밖이다")
        if not idea:
            fails.append(f"{where} 직관이 비었다")
        if state in {"실험", "채택", "기각"}:
            if not method:
                fails.append(f"{where} 검증 방법 없이 {state} 이다")
            if not CAP.match(cap):
                fails.append(f"{where} 비용 상한 '{cap}' 가 형식 밖이다 — $N · 0 · T4 N시간 · 장비 N시간")
        elif cap and not CAP.match(cap):
            fails.append(f"{where} 비용 상한 '{cap}' 가 형식 밖이다")
        if state in {"채택", "기각"} and not EVIDENCE.search(evidence):
            fails.append(f"{where} {state} 의 근거가 없다 — runs/… 또는 DECISIONS §N")
    return fails


def _canary() -> None:
    probe = "| H-001 | 채택 | R1 | a | b | $1 | runs/x.jsonl |\n| H-001 | 기각 | R9 | a | | 많이 | |\n"
    got = check(probe)
    want = ["겹친다", "R1–R7 밖", "검증 방법 없이", "형식 밖", "근거가 없다"]
    if not all(any(w in f for f in got) for w in want) or len(rows(probe)) != 2:
        print(f"    ★ 카나리아가 죽었다 — {got}")
        sys.exit(2)


def main() -> int:
    _canary()
    fails = check(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else ["docs/next/hypotheses.md 가 없다"]
    for f in fails:
        print(f"    {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(2)
