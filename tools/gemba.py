r"""**transformers 없이 도는 자** — 로컬 LLM 에게 품질을 묻는다(GEMBA 꼴 · H-086 · DECISIONS §253).

  python3 tools/gemba.py --run 4b=runs/….jsonl --run 12b=… --표 d002-60 --out /tmp/gemba.jsonl
  python3 tools/gemba.py --run … --out …                # 표를 안 주면 판의 모든 줄을 잰다

★ **왜 만드나.** `tools/qe.py`(MetricX)는 `transformers` 4.x 를 끌고 오고, 그 줄에는 **고침이 없는
  취약점 넷**이 산다(DECISIONS §251 — Trainer 는 5.0.0rc3 · `save_pretrained` 는 5.10.0 에서 고쳐졌고
  MetricX 는 4.55 부터 안 돈다). **의존성을 지우는 것이 가장 센 수리다.** 이 자는 ollama 로 도므로
  torch 도 transformers 도 안 든다 — 이 저장소의 기본 의존성은 0 이다(§4).
★ **판정자는 팔과 집안이 달라야 한다.** 기본은 `Qwen/Qwen3-8B`(ollama `qwen3:8b` · Apache-2.0 ·
  대장에 `yes · yes`)다. 팔은 Gemma 이고 배포본은 Nova 이므로 **셋 다 남이다.**
★ **점수는 클수록 좋다** — 0~100 을 그대로 쓴다. `labels.py corr` 이 「클수록 좋다」 를 전제한다(§242).
  MetricX 는 오류 점수라 `qe.py` 가 뒤집어 내는데, **여기는 뒤집지 않는다** — 뒤집는 자리를 자마다
  하나씩만 둔다.
★ **못 읽은 답은 버리지 않고 센다.** 0~100 이 아닌 답이 오면 **그 줄을 안 내고 몇이었는지 찍는다** —
  0 으로 적으면 「모른다」 가 「최악이다」 가 된다(`labels.py rule` 의 분모 0 과 같은 규율 · §244).
★ **밖 — 이 자가 옳은지는 이 도구가 모른다.** 내는 것은 수이고, **사람과 같은 순서로 줄을 세우는가**는
  `tools/labels.py corr` 이 묻는다(H-086). ⚠ **판정자가 하나다** — H-081 은 넷을 썼다(§101). 그래서
  이 수는 **참값이 아니라 자 후보**로만 쓴다.
★ **밖 — 왜 그 점수인지는 안 묻는다.** 까닭을 받으면 토큰이 늘고 사고가 섞인다(§48). 수 하나만 받는다.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from seshat import backends  # noqa: E402

# ★ 대장이 이 가중치를 안다(DECISIONS §6) — `Qwen/Qwen3-8B` · Apache-2.0 · 상업 yes · 교사 yes
기본모형 = "qwen3:8b"
대장이름 = "Qwen/Qwen3-8B"

# ★ **지시문은 `labels.py` 의 판정 규율과 같다**(§108 · §227) — 어느 팔인지 안 알리고, 참조가 없고,
#   찾아보지 않는다. 다른 것은 **사람은 셋으로 가르고 이 자는 0~100 을 준다**는 것뿐이다.
체계 = (
    "You rate English→Korean translation quality for AWS technical documentation.\n"
    "Given the English source and one Korean translation, output a single integer 0-100:\n"
    "  100 = the Korean carries the full meaning of the English, nothing added or lost\n"
    "   50 = part of the meaning is wrong, missing, or invented\n"
    "    0 = it is not a translation of this source at all\n"
    "Judge MEANING. Do not reward or punish style, politeness level, or term spelling by itself.\n"
    "You are given no reference translation. Do not look anything up.\n"
    "Output ONLY the integer. No words, no explanation, no punctuation."
)
수 = re.compile(r"-?\d+")


def _도구(이름: str):
    spec = importlib.util.spec_from_file_location(이름, ROOT / f"tools/{이름}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def 물을_줄(판: dict[str, pathlib.Path], 표: str = "", setpath: str = "") -> list[dict]:
    """(id, arm, src, out). **표를 주면 그 표가 물어본 (줄,팔) 만 남긴다.**

    ★ 자를 검증하는 데 드는 것은 **사람이 본 자리**뿐이다 — 1,800 줄을 다 물으면 열 배가 든다.
      표를 안 주면 판의 모든 줄을 잰다(다른 표에도 쓰려면 그쪽이다).
    """
    qe = _도구("qe")
    줄 = qe.줄을_모은다(판, setpath)
    if not 표:
        return 줄
    labels = _도구("labels")
    kp = labels.out_dir() / f"{표}.key.jsonl"
    if not kp.exists():
        raise SystemExit(f"표의 열쇠가 없다 — {labels._짧게(kp)}\n"
                         f"    있는 표를 본다 : ls {labels._짧게(labels.out_dir())}/*.key.jsonl\n"
                         f"    표 없이 판 전부를 재려면 : --표 를 뺀다")
    물은것 = {(r["id"], r["arm"]) for r in
              (json.loads(x) for x in kp.read_text(encoding="utf-8").splitlines() if x.strip())
              if not r.get("meta")}
    남 = [x for x in 줄 if (x["id"], x["arm"]) in 물은것]
    if not 남:
        있는팔 = sorted({a for _, a in 물은것})
        raise SystemExit(f"표 `{표}` 가 물어본 (줄,팔) 이 이 판들에 하나도 없다\n"
                         f"    표의 팔 : {' · '.join(있는팔)}\n"
                         f"    `--run <그 팔>=<판>` 으로 이름을 맞춘다")
    return 남


def 읽는다(답: str) -> float | None:
    """0~100 하나. **못 읽으면 None** — 0 이 아니다(「모른다」 와 「최악이다」 는 다르다)."""
    m = 수.search(답 or "")
    if not m:
        return None
    v = float(m.group())
    return v if 0 <= v <= 100 else None


def 잰다(줄: list[dict], 모형: str) -> list[tuple[dict, float | None]]:
    """★ **한 줄씩 묻는다.** 묶어 보내면 모델이 자리를 섞고, 섞인 것을 못 알아챈다."""
    부른다 = backends.ollama_chat(모형, 체계 + backends.NO_THINK, {"think": False}, backends.NO_THINK)
    난것 = []
    for i, x in enumerate(줄, 1):
        답 = 부른다([f"English: {x['src']}\nKorean: {x['out']}"], {})[0]
        난것.append((x, 읽는다(답)))
        print(f"\r  {i}/{len(줄)}", end="", file=sys.stderr, flush=True)
    print("", file=sys.stderr)
    return 난것


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", default=[], metavar="팔=경로")
    ap.add_argument("--out", default="")
    ap.add_argument("--표", default="", help="이 표가 물어본 (줄,팔) 만 잰다 — 열 배가 준다")
    ap.add_argument("--model", default=기본모형)
    ap.add_argument("--set", dest="setpath", default="")
    a = ap.parse_args(sys.argv[1:] if argv is None else argv)

    if not a.run or not a.out:
        raise SystemExit("`--run 팔=경로` 와 `--out` 이 있어야 잰다\n"
                         "    보기 : --run 4b=runs/H-080-retry2-….jsonl --표 d002-60 "
                         "--out /tmp/gemba.jsonl")
    판: dict[str, pathlib.Path] = {}
    for spec in a.run:
        if "=" not in spec:
            raise SystemExit(f"--run 은 팔=경로 다 — {spec}\n"
                             "    보기 : --run 4b=runs/H-080-retry2-20260929-201747.jsonl")
        k, _, v = spec.partition("=")
        판[k.strip()] = pathlib.Path(v.strip())

    backends.들어가나(a.model)              # 카드에 안 들어가면 넘는 길을 든다(§84 · §196)
    줄 = 물을_줄(판, a.표, a.setpath)
    print(f"  {len(줄)}줄 · 팔 {len(판)} · {a.model}" + (f" · 표 {a.표}" if a.표 else ""),
          file=sys.stderr)
    잰것 = 잰다(줄, a.model)

    못읽음 = [x for x, v in 잰것 if v is None]
    # ★ **머리줄이 조건을 든다**(DECISIONS §57). 자가 바뀌면 수가 바뀐다
    머리 = {"meta": True, "자": "gemba-qwen3-8b", "model": a.model, "대장이름": 대장이름,
            "표": a.표 or "(판 전부)", "체계_sha": __import__("hashlib").sha256(
                체계.encode("utf-8")).hexdigest()[:16],
            "못읽음": len(못읽음), "뒤집었다": False,
            "note": "0~100 · 클수록 좋다 — 뒤집지 않는다(DECISIONS §253)"}
    글 = [json.dumps(머리, ensure_ascii=False)]
    글 += [json.dumps({"id": x["id"], "arm": x["arm"], "score": v}, ensure_ascii=False)
           for x, v in 잰것 if v is not None]
    pathlib.Path(a.out).write_text("\n".join(글) + "\n", encoding="utf-8")
    print(f"  {a.out}  {len(글) - 1}줄" + (f" · **못 읽은 답 {len(못읽음)}** (그 줄은 안 냈다)"
                                          if 못읽음 else " · 전부 읽혔다"))
    print("  자가 사람과 같은 순서인지 묻는다 :\n"
          f"    python3 tools/labels.py corr --name {a.표 or '<표>'} --judges <쉼표> "
          f"--자 gemba={a.out} --자 metricx=<점수> --기준 metricx")
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
