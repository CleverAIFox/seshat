"""문형 탐침 — 문형 템플릿 × 온톨로지 어휘로 통제된 영어 문장을 만든다(MASTER §7 R5).

  python3 tools/make_probes.py --name h001 --n 200      → data/probes/h001.jsonl

★ **번역 방식이 아니라 탐침이다.** 문형 하나를 고정하고 어휘만 바꾸면, 오류가 어느 구문에서 나는지를
  어휘와 떼어 볼 수 있다(DECISIONS §12). 줄마다 `construction` 이 그 구문을 적는다.
★ **결정적이다.** 같은 `--seed` 면 같은 파일이 나온다. 그래서 커밋하지 않고 다시 만든다 — 결과 파일
  머리줄의 평가셋 해시가 같은 셋인지를 증명한다.
★ `keep` 은 문장에 넣은 영어 이름 그대로다. 정답(`ref`)은 없다 — keep · 조사 · 문체는 정답 없이 잰다.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from seshat import catalog, ontology  # noqa: E402

# (구문, 템플릿). {S} 서비스 · 기능 · {S2} 두 번째 · {A} API(그 부모가 {P}) · {C} 개념
TEMPLATES = [
    ("SV", "{S} scales automatically."),
    ("SVC", "{S} is the most cost-effective option for this workload."),
    ("SVO", "The data engineering team uses {S} to process the {C}."),
    ("SVOO", "{S} gives the analysts a single view of the {C}."),
    ("SVOC", "The company wants to keep {S} available during peak hours."),
    ("question", "Which solution that uses {S} will meet these requirements with the LEAST operational overhead?"),
    ("passive", "The {C} is ingested by {S} and stored in {S2}."),
    ("relative", "The {C} that {S} writes to {S2} must be encrypted."),
    ("negation", "{S} does not support the {C} that the application requires."),
    ("conditional", "If {S} throttles the requests, the team must increase the {C}."),
    ("comparison", "{S} is faster than {S2} for this type of {C}."),
    ("api", "Call the {A} API of {P} to write the {C}."),
    ("purpose", "To reduce latency, move the {C} from {S} to {S2}."),
    ("coordination", "Configure {S}, and then connect it to {S2}."),
]


def pick_name(rng: random.Random, node: dict) -> str:
    names = [node["en"], *node.get("aliases", [])]
    return rng.choice(names)


def make(onto: list[dict], n: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    names = [x for x in onto if x["kind"] in ("service", "feature")]
    apis = [x for x in onto if x["kind"] == "api"]
    concepts = [x for x in onto if x["kind"] == "concept"]
    by_id = {x["id"]: x for x in onto}
    out = []
    for i in range(n):
        cons, tpl = TEMPLATES[i % len(TEMPLATES)]
        a, b = rng.sample(names, 2)
        api = rng.choice(apis)
        fill = {"S": pick_name(rng, a), "S2": pick_name(rng, b), "A": api["en"],
                "P": pick_name(rng, by_id[api["parent"]]), "C": rng.choice(concepts)["en"]}
        src = tpl.format(**fill)
        src = src[0].upper() + src[1:]
        keep = [fill[k] for k in ("S", "S2", "A", "P") if "{" + k + "}" in tpl]
        out.append({"id": f"probe-{seed}-{i + 1:03d}", "src": src, "keep": keep, "construction": cons})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args(argv)
    rows = make(ontology.load(), a.n, a.seed)
    meta = {"meta": True, "about": f"문형 탐침 {a.n}줄 · seed {a.seed} · 템플릿 {len(TEMPLATES)}", "license": "CC0-1.0",
            "made_by": "tools/make_probes.py"}
    out = ROOT / "data/probes" / f"{a.name}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    catalog.gate(out)               # 쓰기 전에 묻는다(DECISIONS §121)
    out.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in [meta, *rows]) + "\n", encoding="utf-8")
    print(f"  {out.relative_to(ROOT)}  {len(rows)}줄")
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
