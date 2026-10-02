"""이미 있는 결과 파일을 다시 채점한다 — GPU 없이 되돌리기만 바꿔 본다(DECISIONS §16).

  python3 tools/rescore.py runs/H-001-ph-*.jsonl --set data/probes/h001.jsonl --hypothesis H-016

★ **모델을 다시 부르지 않는다.** 처치군 출력에 남은 자리표시를 지금의 `terms.unmask` 로 한 번 더 되돌리고
  `evaluate.score` 로 다시 잰다. 원문을 다시 `mask` 해 자리를 얻는다 — `mask` 는 결정적이다.
★ 가설의 문은 같다 — `--hypothesis` 가 대장에서 `실험` 상태여야 한다.
★ 새 결과 파일은 머리줄에 `rescored_from` 을 들고, 원래 조건(커밋 · 해시 · 디코딩)을 그대로 옮긴다.
★ **셋 · 사전 · 자는 물려받지 않고 지금 것을 적는다.** 다시 잰 것은 지금 것으로 잰 것이다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from seshat import endings, evaluate, ontology, terms


def rescore(run_path: str, set_path: str, post: str = "none") -> tuple[dict, list[dict]]:
    쪽 = Path(run_path)
    if not 쪽.exists():
        # ★ **없는 파일에 추적을 뱉지 않는다**(DECISIONS §175). 판은 레이크로 옮겨 가므로
        #   `runs/…` 글로브가 안 맞는 것이 흔하다 — **어디서 찾는지**를 같이 말한다
        raise SystemExit(f"{run_path} 가 없다 — 레이크로 옮겨졌을 수 있다\n"
                         f"  찾는다 : python3 tools/lake.py ls {쪽.stem.split('-2026')[0]}")
    lines = [json.loads(x) for x in 쪽.read_text(encoding="utf-8").splitlines() if x.strip()]
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
    keep = {k: head[k] for k in ("commit", "chars", "backend", "weights", "decoding", "model", "ms") if k in head}
    keep["onto_sha256"] = evaluate.onto_sha256()      # 지금 사전으로 다시 쟀다(DECISIONS §32)
    # ★ **지금 자로 다시 쟀다.** 옛 머리줄의 자 판을 물려받으면 「옛 자로 잰 수」 라고 거짓말한다 —
    #   바로 위의 셋 · 사전과 같은 병이다(DECISIONS §145). 재채점의 값어치가 여기 있다
    keep["metrics"] = evaluate.METRICS_VER
    # ★ **쓴 셋을 적는다.** 2026-09-27 까지 이 줄은 옛 머리줄의 `set_sha256` 을 그대로 옮겼다 —
    #   `--set` 으로 다른 셋을 대도 결과는 옛 셋을 쟀다고 말했다. §106 과 같은 병이다(DECISIONS §122).
    keep["set_sha256"] = evaluate.set_sha256(set_path)
    # ★ **자리도 적는다**(DECISIONS §173). 해시만 적었더니 기록판의 선 줄(자리만 든다)과
    #   견줄 이름이 없어서 `--pin-target` 이 「셋이 다르다 — 이번 None」 으로 막혔다
    keep["set"] = set_path
    keep["onto_score"] = evaluate.onto_score_sha256()
    keep["set_onto"] = evaluate.셋의_사전(set_path)
    keep["set_stale"] = evaluate.셋이_낡았나(set_path)
    if head.get("set_sha256") and head["set_sha256"] != keep["set_sha256"]:
        keep["set_was"] = head["set_sha256"]          # 원래 어느 셋이었는지도 남긴다
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
