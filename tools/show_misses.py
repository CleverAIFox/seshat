"""숫자 뒤의 줄을 본다 — 어느 줄이 어떻게 틀렸나(DECISIONS §53).

  uv run python tools/show_misses.py runs/H-032-gemma3-4b-20260923-204451.jsonl
  uv run python tools/show_misses.py 결과.jsonl --what keep      이름이 사라진 줄만
  uv run python tools/show_misses.py 결과.jsonl --what term      뜻이 안 남은 줄만
  uv run python tools/show_misses.py 결과.jsonl --what hangul    번역이 아닌 줄만
  uv run python tools/show_misses.py 결과.jsonl --what style     합쇼체가 아닌 줄만
  uv run python tools/show_misses.py 결과.jsonl --what short     **가장 짧게 나온 줄**(H-079)

★ **지표는 어디가 아픈지 말해 주지 않는다.** keep 0.962 는 「이름 하나가 사라졌다」 인데 어느 이름인지는
  숫자에 없다. 매번 손으로 캐내면 안 캐내게 된다 — 그러면 0.786 과 0.857 의 차이를 못 읽는다.
★ 결과 파일 하나만 있으면 된다. 평가셋은 `set` 머리줄이 가리키는 자리에서 다시 읽는다 — 셋이 바뀌었으면
  말하고 멈춘다(`set_sha256`).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from seshat import evaluate as ev  # noqa: E402
from seshat import ontology  # noqa: E402

WHAT = ("keep", "term", "hangul", "style", "short", "all")

# ★ **누락은 아무 지표도 안 본다**(H-079 · DECISIONS §214). `hangul` 은 「원문의 세 배보다 길면」 만 보고
#   **하한이 없다.** 2026-09-29 `keep` 이 잡은 다섯 줄 중 넷이 절 통째 누락이었는데, 규칙 지표 여섯이
#   그 줄을 전부 통과시켰다 — 이름이 든 줄이라 우연히 보인 것이다.
# ★ **선을 여기서 긋지 않는다**(§139). 이 갈래는 **가장 짧은 N 줄을 보여 줄 뿐**이고, 그 줄이 정말
#   누락인지는 사람이 본다. 자로 쓸지는 H-079 가 그 판정으로 정한다.
SHORT_N = 20


def read(path: Path) -> tuple[dict, list[dict]]:
    lines = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    if not lines or not lines[0].get("meta"):
        raise SystemExit(f"결과 파일이 아니다 — 머리줄이 없다 : {path}\n"
                         f"    있는 것 : ls -t runs/*.jsonl | head")
    return lines[0], lines[1:]


def keeps(meta: dict, rows: list[dict]) -> dict[str, list[str]]:
    """평가셋에서 줄마다의 `keep` 목록을 다시 읽는다. 셋이 없거나 바뀌었으면 빈 표."""
    p = ROOT / meta.get("set", "")
    if not p.exists():
        return {}
    got = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
    if meta.get("set_sha256") and got != meta["set_sha256"]:
        raise SystemExit(f"평가셋이 그때와 다르다 — {meta['set_sha256']} 였고 지금 {got}\n"
                         "       tools/make_probes.py 로 그때 것을 다시 만든다")
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if not r.get("meta"):
            out[r.get("id")] = r.get("keep", [])
    return out


def 짧은_줄(rows: list[dict], n: int = SHORT_N) -> list[tuple[str, dict, str]]:
    """**원문 대비 번역이 가장 짧은 N 줄.** 이 셋의 가운데 비를 기준으로 얼마나 짧은지 같이 적는다.

    ★ 글자 수로 잰다. 한국어는 영어보다 촘촘해서 비가 1 보다 작은 것이 정상이고, **정상값이
      얼마인지는 셋마다 다르다** — 그래서 절대값이 아니라 **이 셋의 가운데**와 견준다.
    """
    잰 = [(len(r.get("out", "")) / max(len(r["src"]), 1), r) for r in rows if r.get("src")]
    if not 잰:
        return []
    가운데 = sorted(x for x, _ in 잰)[len(잰) // 2]
    잰.sort(key=lambda x: x[0])
    return [("short", r, f"길이 비 {비:.2f} · 이 셋의 가운데 {가운데:.2f} 의 {비 / 가운데:.0%}")
            for 비, r in 잰[:n]]


def misses(meta: dict, rows: list[dict], what: str) -> list[tuple[str, dict, str]]:
    """(까닭, 줄, 자세히) — 까닭은 WHAT 의 이름이다."""
    onto = ontology.load()
    table = keeps(meta, rows) if what in ("keep", "all") else {}
    out = []
    if what == "short":                  # **자가 아니라 눈이 볼 후보다** — 다른 까닭과 섞지 않는다
        return 짧은_줄(rows)
    for r in rows:
        src, o = r["src"], r.get("out", "")
        if what in ("hangul", "all") and not ev.ko_line(src, o):
            out.append(("hangul", r, "번역이 아니다"))
            continue                      # 번역이 아니면 나머지 까닭은 이것의 결과다
        if what in ("style", "all") and not ev.is_hapsyo(o):
            out.append(("style", r, "합쇼체가 아니다"))
        if what in ("keep", "all"):
            gone = [k for k in table.get(r.get("id"), []) if k not in o]
            if gone:
                out.append(("keep", r, "사라진 이름 " + " · ".join(gone)))
        if what in ("term", "all"):
            for _, _, s in ontology.find(onto, src):
                if s.node["keep"]:
                    continue
                want = [s.node["ko"], *s.node.get("alt_ko", [])]
                if not any(k in o for k in want):
                    bad = [k for k in s.node.get("bad_ko", []) if k in o]
                    how = f"오역 {bad[0]}" if bad else "버렸다"
                    out.append(("term", r, f"{s.node['en']} → {s.node['ko']} 인데 {how}"))
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run", type=Path)
    ap.add_argument("--what", choices=WHAT, default="all")
    a = ap.parse_args(argv)

    meta, rows = read(a.run)
    found = misses(meta, rows, a.what)
    print(f"  {meta.get('backend', meta.get('url'))} · {len(rows)}줄 · 걸린 자리 {len(found)}")
    for why, r, detail in found:
        print(f"\n  [{why}] {r.get('id')} — {detail}")
        print(f"    원문 {r['src']}")
        print(f"    번역 {r.get('out', '')[:300]}")
    if a.what == "short" and found:
        print(f"\n  ※ **후보다, 판정이 아니다.** 절이 통째로 빠진 줄을 눈으로 세고 그 수를 "
              f"H-079 의 근거 칸에 적는다 — {SHORT_N} 중 10 이상이면 자로 삼는다(미리 그은 선)")
    return 0


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
