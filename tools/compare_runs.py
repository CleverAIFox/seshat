"""두 결과 파일을 줄 단위로 대조한다 — 가설 판정의 EDA(MASTER §7 R7).

  python3 tools/compare_runs.py runs/H-001-base-*.jsonl runs/H-001-ph-*.jsonl --set data/probes/h001.jsonl

★ **평균 하나로 판정하지 않는다.** 어느 줄에서 이기고 어느 줄에서 졌는지, 어느 구문에서 몰리는지를 본다.
★ 평가셋(`--set`)을 주면 줄마다 `keep` 과 `construction` 을 붙인다. 결과 파일에는 원문 · 출력만 있다.
★ 처치군 출력에 자리표시 모양(`⟦T1⟧` · `[T1]` · `\\[T1]` · `【T1】`)이 남았으면 되돌아오지 못한 것이다.
  **처음에는 `⟦` 만 셌고 0 이 나왔다** — 모델이 모양을 바꾼 `\\[T1]` 26 개를 못 봤다(DECISIONS §16).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from seshat import compare as _축  # noqa: E402  (이 파일에 `compare` 함수가 따로 있다)

# seshat/terms.py 의 SLOT_FORMS 와 같다. 도구가 패키지 없이도 돌게 여기에 둔다 — 테스트가 둘을 대조한다
RESIDUE = re.compile(r"(?:⟦T(\d+)⟧|\\?\[T(\d+)\\?\]|【T(\d+)】|`T(\d+)`"
                     r"|(?<![A-Za-z0-9])T(\d+)(?![0-9]))")


def read(path: str) -> tuple[dict, dict[str, dict]]:
    lines = [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]
    head = next(x for x in lines if x.get("meta"))
    return head, {x["id"]: x for x in lines if not x.get("meta")}


def kept(keep: list[str], out: str) -> list[str]:
    return [k for k in keep if k not in out]


def words_after_last_name(src: str, keep: list[str]) -> int | None:
    """원문에서 마지막 영어 이름 뒤에 낱말이 몇 개 남았는가. 문장 끝에 가까울수록 작다(H-017)."""
    ends = [src.rfind(k) + len(k) for k in keep if k in src]
    return len([w for w in src[max(ends):].split() if any(c.isalnum() for c in w)]) if ends else None


def style_flips(a_rows: dict, b_rows: dict, spec: dict[str, dict]) -> dict:
    """A 는 합쇼체인데 B 는 아닌 줄과, 그 줄에서 마지막 이름이 문장 끝에서 얼마나 떨어졌는가."""
    import importlib.util
    root = Path(__file__).resolve().parent.parent
    sp = importlib.util.spec_from_file_location("ev", root / "seshat/evaluate.py")
    ev = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(ev)
    flips, dist_flip, dist_rest = [], [], []
    for i in a_rows:
        if i not in b_rows:
            continue
        d = words_after_last_name(a_rows[i]["src"], spec.get(i, {}).get("keep", []))
        flipped = ev.is_hapsyo(a_rows[i]["out"]) and not ev.is_hapsyo(b_rows[i]["out"])
        if flipped:
            flips.append(i)
        if d is not None:
            (dist_flip if flipped else dist_rest).append(d)
    mean = lambda xs: round(sum(xs) / len(xs), 2) if xs else None  # noqa: E731
    return {"flips": flips, "after_flip": mean(dist_flip), "after_rest": mean(dist_rest),
            **style_sides(a_rows, b_rows, ev)}


def style_sides(a_rows: dict, b_rows: dict, ev) -> dict:
    """문체가 깨진 줄을 **양쪽 다** 본다 — A 만 · B 만 · 둘 다(DECISIONS §29).

    ★ 처음에는 「A 는 합쇼체인데 B 는 아닌 줄」만 셌다. 두 팔이 같은 줄에서 같이 깨지면 0 이 찍히고,
      그것을 「B 가 안 깨졌다」 로 읽게 된다. H-019 에서 두 팔의 style 이 똑같이 0.93 이었는데 표는 0 만
      보여 줬다 — 지표가 같으면 원인도 같은지 **줄로 보여야** 안다.
    """
    a_bad = {i for i in a_rows if i in b_rows and not ev.is_hapsyo(a_rows[i]["out"])}
    b_bad = {i for i in b_rows if i in a_rows and not ev.is_hapsyo(b_rows[i]["out"])}
    return {"a_only": sorted(a_bad - b_bad), "b_only": sorted(b_bad - a_bad), "both": sorted(a_bad & b_bad)}


def terms_by_construction(a_rows: dict, b_rows: dict, spec: dict[str, dict]) -> dict:
    """구문별로 원문 개념의 한국어가 번역에 남은 비율(H-012). 관계절의 머리 명사가 여기서 보인다."""
    import sys as _s
    root = Path(__file__).resolve().parent.parent
    _s.path.insert(0, str(root))
    from seshat import ontology
    onto = ontology.load()
    out = defaultdict(lambda: [0, 0, 0])
    for i in a_rows:
        if i not in b_rows:
            continue
        cons = spec.get(i, {}).get("construction", "?")
        for _, _, s in ontology.find(onto, a_rows[i]["src"]):
            if s.node["keep"]:
                continue
            names = [s.node["ko"], *s.node.get("alt_ko", [])]
            c = out[cons]
            c[0] += 1
            c[1] += any(k in a_rows[i]["out"] for k in names)
            c[2] += any(k in b_rows[i]["out"] for k in names)
    return dict(out)


def term_misses(rows: dict, spec: dict[str, dict]) -> tuple[Counter, list[tuple]]:
    """개념이 번역에 없다고 센 자리를 줄로 본다(H-020). 모델이 버렸나, 온톨로지가 모르는 표기인가를 눈으로 가른다.

    돌려주는 것 — (개념별 누락 수, [(구문, 원문의 표면, 기대한 한국어들, 번역)])
    """
    import sys as _s
    root = Path(__file__).resolve().parent.parent
    _s.path.insert(0, str(root))
    from seshat import ontology
    onto = ontology.load()
    count, lines = Counter(), []
    for i, r in rows.items():
        for _, _, s in ontology.find(onto, r["src"]):
            if s.node["keep"]:
                continue
            names = [s.node["ko"], *s.node.get("alt_ko", [])]
            if not any(k in r["out"] for k in names):
                tag = "오역" if any(k in r["out"] for k in s.node.get("bad_ko", [])) else "없음"
                count[f"{s.node['id']} · {tag}"] += 1
                lines.append((spec.get(i, {}).get("construction", "?"), f"{s.text} · {tag}", names, r["out"]))
    return count, lines


def compare(a_rows: dict, b_rows: dict, spec: dict[str, dict]) -> dict:
    ids = [i for i in a_rows if i in b_rows]
    lost_a, lost_b, only_b_worse, only_b_better, residue = Counter(), Counter(), [], [], []
    by_cons = defaultdict(lambda: [0, 0, 0])   # 이름 수 · 대조군 유지 · 처치군 유지
    for i in ids:
        keep = spec.get(i, {}).get("keep", [])
        cons = spec.get(i, {}).get("construction", "?")
        ma, mb = kept(keep, a_rows[i]["out"]), kept(keep, b_rows[i]["out"])
        for k in ma:
            lost_a[k] += 1
        for k in mb:
            lost_b[k] += 1
        c = by_cons[cons]
        c[0] += len(keep)
        c[1] += len(keep) - len(ma)
        c[2] += len(keep) - len(mb)
        if len(mb) > len(ma):
            only_b_worse.append(i)
        elif len(mb) < len(ma):
            only_b_better.append(i)
        if RESIDUE.search(b_rows[i]["out"]):
            residue.append(i)
    return {"lines": len(ids), "b_worse": only_b_worse, "b_better": only_b_better, "residue": residue,
            "lost_a": lost_a, "lost_b": lost_b, "by_construction": dict(by_cons)}



def 토막_길이(ids, rows: dict) -> dict[str, int]:
    """줄마다 **용어집 토막에 실리는 항목 수**(DECISIONS §177 · H-075).

    ★ **가린 뒤에 센다.** `+ph` 가 이름을 먼저 빼므로 사전은 **가려진 글**에서 찾는다 —
      원문으로 세면 이름까지 세어 실제보다 길게 나온다(`glossary.for_line` 의 문서주석과 같은 말).
    """
    from seshat import glossary, ontology, terms
    onto = ontology.load()
    out = {}
    for i in ids:
        src = rows.get(i, {}).get("src") or ""
        가린, _ = terms.mask(onto, src)
        out[i] = len(glossary.for_line(onto, 가린))
    return out


def 중앙(xs: list[int]) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    n = len(s)
    return float(s[n // 2]) if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--set", default="")
    ap.add_argument("--show", type=int, default=6)
    ap.add_argument("--open", dest="open_", default="",
                    choices=["", "style"], help="style — B 만 합쇼체가 깨진 줄을 전부 연다(H-075)")
    a = ap.parse_args(argv)
    ha, ra = read(a.a)
    hb, rb = read(a.b)
    spec = {}
    if a.set:
        spec = {x["id"]: x for x in (json.loads(y) for y in Path(a.set).read_text(encoding="utf-8").splitlines() if y.strip())
                if not x.get("meta")}
    # ★ **축은 `seshat/compare.py` 하나에만 적는다**(DECISIONS §157). 2026-09-28 까지 이 도구는
    #   셋과 사전만 보고 **자는 안 봤다** — 같은 병의 여덟 번째였다
    for g in _축.갈림(ha, hb, ("set_sha256", "metrics")):
        print(f"    ★ 두 파일의 {g.글()}")
        print("      같은 셋이 아니면 줄 대조는 뜻이 없다" if g.키 == "set_sha256"
              else "      `tools/rescore.py` 로 한쪽을 지금 자로 다시 잰다")
        return 1
    # ★ **줄 수가 다르면 머리줄의 숫자는 짝이 아니다**(DECISIONS §45). `--limit` 으로 싸게 본 판과 전수를
    #   나란히 놓으면 다른 문장을 비교하게 된다. 줄 대조는 겹치는 id 만 보지만 머리줄은 각자 전체를 든다
    if ha.get("n") != hb.get("n"):
        print(f"    ★ 두 파일의 줄 수가 다르다 — A {ha.get('n')} · B {hb.get('n')}")
        print("      같은 줄 수로 다시 재거나, 적은 쪽에 맞춰 `--limit` 으로 다시 잰다")
        return 1
    # ★ 온톨로지도 채점기의 일부다(DECISIONS §32). 사전이 다르면 term 은 모델이 아니라 사전을 재고 있다.
    #   **여기서는 막는다** — 문과 달리 이 도구는 두 팔을 나란히 놓는 것이 전부다
    for g in _축.갈림(ha, hb, ("onto_sha256",)):
        print(f"    ★ 두 파일의 온톨로지 해시가 다르다 — A {g.가} · B {g.나}")
        print("      term 은 사전이 바뀐 몫까지 센다. 같은 사전으로 한쪽을 다시 채점한다(tools/rescore.py)")
        return 1
    r = compare(ra, rb, spec)
    for name, h in (("A", ha), ("B", hb)):
        t = " · ".join(f"{k} {h[k]:.3f}" for k in ("term", "term_off", "term_bad") if h.get(k) is not None)
        print(f"  {name} {h.get('backend') or h.get('url')}: keep {h['keep']:.3f} · josa {h.get('josa')} · style {h['style']:.2f}"
              + (f" · {t}" if t else "") + f" · {h['ms']}ms")
    print(f"\n  줄 {r['lines']} — B 가 이긴 줄 {len(r['b_better'])} · 진 줄 {len(r['b_worse'])} · B 에 자리표시가 남은 줄 {len(r['residue'])}")
    print("\n  구문별 keep (이름 수 · A · B)")
    for cons, (n, ka, kb) in sorted(r["by_construction"].items(), key=lambda x: (x[1][2] - x[1][0])):
        print(f"    {cons:<13} {n:>4} · {ka / n:.2f} · {kb / n:.2f}" if n else f"    {cons:<13} 0")
    tb = terms_by_construction(ra, rb, spec)
    if tb:
        print("\n  구문별 개념 유지 — 원문 개념의 한국어가 번역에 있는가 (개념 수 · A · B)  [H-012]")
        for cons, (n, ka, kb) in sorted(tb.items(), key=lambda x: x[1][1] / max(x[1][0], 1)):
            print(f"    {cons:<13} {n:>4} · {ka / n:.2f} · {kb / n:.2f}")
    sf = style_flips(ra, rb, spec)
    print(f"\n  합쇼체가 깨진 줄 — A 만 {len(sf['a_only'])} · B 만 {len(sf['b_only'])} · 둘 다 {len(sf['both'])}"
          f" · 마지막 이름 뒤 낱말: B 만 깨진 줄 {sf['after_flip']} · 나머지 {sf['after_rest']}  [H-017 · H-019]")
    for i in sf["both"][: a.show]:
        print(f"    [둘 다 · {spec.get(i, {}).get('construction', '?')}] {ra[i]['src']}\n      A: {ra[i]['out']}\n      B: {rb[i]['out']}")
    for i in sf["flips"][: a.show]:
        print(f"    [{spec.get(i, {}).get('construction', '?')}] {ra[i]['src']}\n      A: {ra[i]['out']}\n      B: {rb[i]['out']}")
    if a.open_ == "style":
        # ★ **7줄은 세는 것이 아니라 여는 것이다**(H-075). 평균으로는 「왜」 가 안 나온다
        깨진 = sf["b_only"]
        길이 = 토막_길이(rb.keys(), rb)
        깨진중앙, 전체중앙 = 중앙([길이[i] for i in 깨진]), 중앙(list(길이.values()))
        print(f"\n  ── B 만 합쇼체가 깨진 줄 {len(깨진)} 를 전부 연다  [H-075]")
        for i in 깨진:
            print(f"    [{i} · 용어집 {길이.get(i, 0)}항목 · {spec.get(i, {}).get('construction', '?')}]")
            print(f"      원문: {ra[i]['src'][:100]}")
            print(f"      A   : …{ra[i]['out'][-40:]}")
            print(f"      B   : …{rb[i]['out'][-40:]}")
        배 = (깨진중앙 / 전체중앙) if 전체중앙 else 0.0
        판 = ("**길어서 샌다 — 참**" if 배 >= 1.5 else
              "**거짓 — 토막 길이 탓이 아니다**" if 배 <= 1.2 else "**사이다 — 표본이 모자란다**")
        print(f"\n    용어집 항목 수 중앙값 — 깨진 줄 {깨진중앙} · 전체 {전체중앙} · {배:.2f}배 → {판}")
        print("    (미리 그은 선: 1.5배 이상이면 참 · 1.2배 아래면 거짓)")
        # ★ **중앙값 견주기는 약한 자다**(DECISIONS §178). 항목 수는 0·1·2·3 뿐이라 중앙값 1 대 2 는
        #   **한 칸**이고, 분모에 **토막이 0 항목인 줄**이 섞인다 — 그 줄은 길이 탓으로 깨질 수가 없다.
        #   묻고 싶은 것은 「길수록 더 깨지나」 이고, 그것은 **항목 수별 깨짐 비율**이 답한다.
        #   **선을 옮기지 않는다** — 위의 판정은 그대로 두고 이 표는 다음 가설의 근거로만 쓴다
        import importlib.util as _iu
        _sp = _iu.spec_from_file_location("ev2", Path(__file__).resolve().parent.parent / "seshat/evaluate.py")
        _ev = _iu.module_from_spec(_sp)
        _sp.loader.exec_module(_ev)
        통 = {}
        for i in ra:
            if i not in rb:
                continue
            k = min(길이.get(i, 0), 3)
            n, ka, kb = 통.get(k, (0, 0, 0))
            통[k] = (n + 1,
                     ka + (0 if _ev.is_hapsyo(ra[i]["out"]) else 1),
                     kb + (0 if _ev.is_hapsyo(rb[i]["out"]) else 1))
        print("\n    항목 수별 합쇼체 깨짐 — 「길수록 더 깨지나」 에 곧바로 답한다")
        print(f"      {'항목':>6} {'줄':>5} {'A 깨짐':>9} {'B 깨짐':>9}")
        for k in sorted(통):
            n, ka, kb = 통[k]
            이름 = f"{k}+" if k == 3 else str(k)
            print(f"      {이름:>6} {n:>5} {ka / n:>8.3f} {kb / n:>8.3f}")
    mc, ml = term_misses(ra, spec)
    print(f"\n  A 에서 개념이 없다고 센 자리 {len(ml)} — 모델이 버렸나 · 온톨로지가 모르는 표기인가  [H-020]")
    for k, c in mc.most_common(8):
        print(f"    {c:>3} · {k}")
    for cons, surf, names, out in ml[: a.show * 2]:
        print(f"    [{cons}] {surf} → 기대 {' / '.join(names)}\n      A: {out}")
    print("\n  B 가 가장 많이 잃은 이름")
    for k, c in r["lost_b"].most_common(8):
        print(f"    {c:>3} · A 도 잃음 {r['lost_a'].get(k, 0):>3} · {k}")
    print("\n  B 가 진 줄")
    for i in (r["b_worse"] + r["residue"])[: a.show]:
        print(f"    [{spec.get(i, {}).get('construction', '?')}] {ra[i]['src']}\n      A: {ra[i]['out']}\n      B: {rb[i]['out']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
