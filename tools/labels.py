"""사람이 줄마다 내리는 판정 — 눈가림으로 받고 다시 붙인다(DECISIONS §98 · H-046).

  python3 tools/labels.py make --set data/domain/d001.jsonl --a <A결과> --b <B결과> --n 60
  # → /tmp/labels-<이름>.tsv (채점표) · data/labels/<이름>.key.jsonl (열쇠)
  python3 tools/labels.py read --name d001-60      # 채운 표를 읽어 판정과 비율을 낸다

★ **눈가림이다.** 채점표는 어느 팔의 출력인지 적지 않는다. 알면 큰 모델에 후하게 준다 — 사람이
  정직하지 않아서가 아니라 **기대가 채점을 민다.** 팔 이름은 열쇠 파일에만 있고, `read` 가 붙인다.
★ **줄을 먼저 뽑고 출력을 나중에 본다.** seed 로 뽑으므로 무엇이 나올지 모르는 채로 표본이 정해진다.
  보고 고르면 그 표본이 결론이다(DECISIONS §86 이 같은 잘못을 적는다).
★ **판정은 셋이다.** `맞다`(뜻이 통한다) · `어긋난다`(뜻이 틀렸거나 지어냈다) · `아니다`(번역이 아니다).
  표기가 공식이 아닌 것은 **맞다** 다 — `term_off` 가 이미 그것을 센다. 여기서 재는 것은 **뜻**이다.
★ **원문도 출력도 저장소에 안 들어온다.** 채점표는 `/tmp` 에 있고, `data/labels/` 에는 줄 id 와 판정만
  남는다 — 문서 본문이 CC BY-SA 라서다(카탈로그 `labels`).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from seshat import evaluate  # noqa: E402

OUT = ROOT / "data/labels"


def _짧게(p: pathlib.Path) -> str:
    """저장소 안이면 상대 경로로, 밖이면 그대로. 시험이 임시 폴더를 써도 안 죽는다."""
    return str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
VERDICTS = ("맞다", "어긋난다", "아니다")
HEAD = ("표", "원문", "번역", "판정(맞다 · 어긋난다 · 아니다)")


def read_run(path: pathlib.Path) -> tuple[dict, dict[str, str]]:
    """결과 파일 → (머리줄, id → 출력). 줄 id 가 없는 옛 파일은 거절한다."""
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    head, body = rows[0], rows[1:]
    out = {}
    for i, r in enumerate(body):
        rid = r.get("id")
        if not rid:
            raise SystemExit(f"{path.name}: {i + 1}번째 줄에 id 가 없다 — 줄 id 가 있어야 짝을 짓는다")
        out[rid] = r.get("out", r.get("ko", ""))
    return head, out


def tag(name: str, rid: str, arm: str) -> str:
    """채점표의 불투명한 이름. **팔을 못 읽게** 해시로 만든다."""
    return hashlib.sha256(f"{name}|{rid}|{arm}".encode()).hexdigest()[:8]


def make(a: pathlib.Path, b: pathlib.Path, rows: list[dict], name: str, n: int, seed: int) -> tuple[str, list[dict]]:
    ha, oa = read_run(a)
    hb, ob = read_run(b)
    if ha.get("set_sha256") != hb.get("set_sha256"):
        raise SystemExit(f"두 결과가 다른 셋이다 — {ha.get('set_sha256')} · {hb.get('set_sha256')}")
    src = {r["id"]: r["src"] for r in rows}
    both = sorted(set(oa) & set(ob) & set(src))
    if len(both) < n:
        raise SystemExit(f"두 팔에 다 있는 줄이 {len(both)} 뿐인데 {n} 을 달라고 했다")
    rng = random.Random(seed)
    picked = sorted(rng.sample(both, n))          # ★ 줄을 먼저 뽑는다 — 출력을 보기 전에
    sheet, key = [], []
    for rid in picked:
        for arm, out in (("a", oa[rid]), ("b", ob[rid])):
            t = tag(name, rid, arm)
            sheet.append((t, src[rid], out))
            key.append({"tag": t, "id": rid, "arm": arm})
    rng.shuffle(sheet)                            # ★ 두 팔이 나란히 서지 않게
    lines = ["\t".join(HEAD)] + ["\t".join([t, s.replace("\t", " "), o.replace("\t", " "), ""]) for t, s, o in sheet]
    return "\n".join(lines) + "\n", key


def read(name: str, sheet: pathlib.Path) -> int:
    key = {r["tag"]: r for r in (json.loads(x) for x in (OUT / f"{name}.key.jsonl").read_text(encoding="utf-8").splitlines() if x.strip())}
    got, blank = [], 0
    for ln in sheet.read_text(encoding="utf-8").splitlines()[1:]:
        if not ln.strip():
            continue
        cols = ln.split("\t")
        t, verdict = cols[0].strip(), (cols[3].strip() if len(cols) > 3 else "")
        if not verdict:
            blank += 1
            continue
        if verdict not in VERDICTS:
            raise SystemExit(f"{t}: 모르는 판정 {verdict!r} — {' · '.join(VERDICTS)} 중 하나다")
        if t not in key:
            raise SystemExit(f"{t}: 열쇠에 없는 표 — 채점표를 바꿔 썼나")
        got.append({**key[t], "verdict": verdict})
    if blank:
        print(f"  ※ 아직 안 매긴 줄 {blank}", file=sys.stderr)
    if not got:
        raise SystemExit("매긴 줄이 없다")
    path = OUT / f"{name}.jsonl"
    meta = {"meta": True, "about": f"{name} 사람 판정 — 뜻만 본다. 표기는 term_off 가 센다(H-046)",
            "license": "자체 — 판정만 든다", "made_by": "tools/labels.py"}
    path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in [meta, *sorted(got, key=lambda r: (r["id"], r["arm"]))]) + "\n",
                    encoding="utf-8")
    print(f"  {_짧게(path)}  {len(got)}줄")
    for arm in ("a", "b"):
        mine = [r for r in got if r["arm"] == arm]
        if not mine:
            continue
        tally = {v: sum(1 for r in mine if r["verdict"] == v) for v in VERDICTS}
        ok = tally["맞다"] / len(mine)
        print(f"  {arm}  뜻이 맞다 {ok:.3f}  ({' · '.join(f'{v} {tally[v]}' for v in VERDICTS)})")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("--set", dest="setpath", required=True)
    m.add_argument("--a", required=True)
    m.add_argument("--b", required=True)
    m.add_argument("--name", default="")
    m.add_argument("--n", type=int, default=60)
    m.add_argument("--seed", type=int, default=31)
    r = sub.add_parser("read")
    r.add_argument("--name", required=True)
    r.add_argument("--sheet", default="")
    a = ap.parse_args(argv)

    if a.cmd == "read":
        return read(a.name, pathlib.Path(a.sheet or f"/tmp/labels-{a.name}.tsv"))

    name = a.name or f"{pathlib.Path(a.setpath).stem}-{a.n}"
    sheet, key = make(pathlib.Path(a.a), pathlib.Path(a.b), evaluate.load(a.setpath), name, a.n, a.seed)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.key.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in key) + "\n", encoding="utf-8")
    out = pathlib.Path(f"/tmp/labels-{name}.tsv")
    out.write_text(sheet, encoding="utf-8")
    print(f"  {out}  {len(key)}줄 (눈가림 · 어느 팔인지 안 적혀 있다)")
    print(f"  {_짧게(OUT / f'{name}.key.jsonl')}  열쇠 — 다 매기기 전에 열지 않는다")
    print(f"  다 매기면 : python3 tools/labels.py read --name {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
