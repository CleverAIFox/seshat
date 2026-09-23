"""이미 있는 결과 파일을 다시 채점한다 — GPU 없이 되돌리기만 바꿔 본다(DECISIONS §16).

  python3 tools/rescore.py runs/H-001-ph-*.jsonl --set data/probes/h001.jsonl --hypothesis H-016

★ **모델을 다시 부르지 않는다.** 처치군 출력에 남은 자리표시를 지금의 `terms.unmask` 로 한 번 더 되돌리고
  `evaluate.score` 로 다시 잰다. 원문을 다시 `mask` 해 자리를 얻는다 — `mask` 는 결정적이다.
★ 가설의 문은 같다 — `--hypothesis` 가 대장에서 `실험` 상태여야 한다.
★ 새 결과 파일은 머리줄에 `rescored_from` 을 들고, 원래 조건(커밋 · 해시 · 디코딩)을 그대로 옮긴다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from seshat import endings, evaluate, ontology, terms  # noqa: E402


def rescore(run_path: str, set_path: str, post: str = "none") -> tuple[dict, list[dict]]:
    lines = [json.loads(x) for x in Path(run_path).read_text(encoding="utf-8").splitlines() if x.strip()]
    head = next(x for x in lines if x.get("meta"))
    body = [x for x in lines if not x.get("meta")]
    spec = {r["id"]: r for r in evaluate.load(set_path)}
    onto = ontology.load()
    rows, outs, out_lines = [], [], []
    for x in body:
        _, slots = terms.mask(onto, x["src"])
        fixed, missing = terms.unmask(x["out"], slots)
        if post == "endings":                     # 종결 정규화(DECISIONS §31) — 검사기가 고칠 수 있는 몫을 잰다
            fixed = endings.normalize(fixed)
        rows.append(spec[x["id"]])
        outs.append(fixed)
        out_lines.append({**x, "out": fixed, "missing": missing})
    res = evaluate.score(rows, outs)
    keep = {k: head[k] for k in ("commit", "set_sha256", "chars", "backend", "weights", "decoding", "model", "ms") if k in head}
    return {"meta": True, **res, **keep, "post": post, "rescored_from": Path(run_path).name}, out_lines


def out_path(hypothesis: str, run: str, now: dt.datetime | None = None) -> Path:
    """결과 파일 이름에 **재채점한 팔**이 들어간다(DECISIONS §26).

    ★ 2026-09-23. 이름이 `가설-rescore-시각` 뿐이라 같은 초에 두 팔을 재채점하니 **뒤엣것이 앞엣것을 덮었다.**
      대조군 결과가 레이크에 닿기 전에 사라졌다. 레이크는 이름이 같고 내용이 다르면 거절하지만, 작업대에서 덮인
      파일은 레이크가 볼 기회조차 없다 — 이름은 만드는 쪽이 책임진다.
    """
    stem = Path(run).stem
    for x in ("-rescore", ):                    # 재채점의 재채점이 이름을 길게 늘이지 않는다
        stem = stem.replace(x, "")
    stamp = (now or dt.datetime.now()).strftime("%Y%m%d-%H%M%S")
    return Path("runs") / f"{hypothesis}-rescore-{stem}-{stamp}.jsonl"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--set", required=True)
    ap.add_argument("--hypothesis", required=True)
    ap.add_argument("--post", default="none", choices=["none", "endings"],
                    help="되돌린 뒤 덧붙일 후처리 — endings 는 해요체 의문을 합쇼체로 고친다")
    a = ap.parse_args(argv)
    evaluate.door(a.hypothesis)
    head, body = rescore(a.run, a.set, a.post)
    head["hypothesis"] = a.hypothesis
    out = out_path(a.hypothesis, a.run if a.post == "none" else f"{Path(a.run).stem}-{a.post}")
    out.parent.mkdir(exist_ok=True)
    if out.exists():
        print(f"{out} 가 이미 있다 — 덮지 않는다. 같은 팔을 다시 재는 것이면 앞의 것을 레이크에 넣고 치운다", file=sys.stderr)
        return 1
    out.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in [head, *body]) + "\n", encoding="utf-8")
    show = [k for k in ("n", "keep", "josa", "style", "term", "term_off", "term_bad", "post", "rescored_from") if k in head]
    print(json.dumps({k: head[k] for k in show}, ensure_ascii=False))
    print(f"→ {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
