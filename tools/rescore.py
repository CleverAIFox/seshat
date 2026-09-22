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
from seshat import evaluate, ontology, terms  # noqa: E402


def rescore(run_path: str, set_path: str) -> tuple[dict, list[dict]]:
    lines = [json.loads(x) for x in Path(run_path).read_text(encoding="utf-8").splitlines() if x.strip()]
    head = next(x for x in lines if x.get("meta"))
    body = [x for x in lines if not x.get("meta")]
    spec = {r["id"]: r for r in evaluate.load(set_path)}
    onto = ontology.load()
    rows, outs, out_lines = [], [], []
    for x in body:
        _, slots = terms.mask(onto, x["src"])
        fixed, missing = terms.unmask(x["out"], slots)
        rows.append(spec[x["id"]])
        outs.append(fixed)
        out_lines.append({**x, "out": fixed, "missing": missing})
    res = evaluate.score(rows, outs)
    keep = {k: head[k] for k in ("commit", "set_sha256", "chars", "backend", "weights", "decoding", "model", "ms") if k in head}
    return {"meta": True, **res, **keep, "rescored_from": Path(run_path).name}, out_lines


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--set", required=True)
    ap.add_argument("--hypothesis", required=True)
    a = ap.parse_args(argv)
    evaluate.door(a.hypothesis)
    head, body = rescore(a.run, a.set)
    head["hypothesis"] = a.hypothesis
    out = Path("runs") / f"{a.hypothesis}-rescore-{dt.datetime.now().strftime('%Y%m%d-%H%M%S')}.jsonl"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in [head, *body]) + "\n", encoding="utf-8")
    print(json.dumps({k: head[k] for k in ("n", "keep", "josa", "style", "rescored_from")}, ensure_ascii=False))
    print(f"→ {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
