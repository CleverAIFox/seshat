"""쿠버네티스 문서에서 **증류용 원문**을 뽑는다 — AWS 밖이고 동일조건이 없다(DECISIONS §276).

  python3 tools/fetch_k8s.py --name k001 --n 2000 --seed 21
  python3 tools/fetch_k8s.py --list                      # 어느 자리에서 몇 문장이 나오나

★ **왜 AWS 안내서가 아닌가.** 그쪽은 **CC BY-SA 4.0** 이고 동일조건변경허락이 **나눠 줄 때** 걸린다.
  학생을 뿌릴 생각이 있으면 그 짐이 따라붙는다(§269 가 교사에서 같은 물음을 겪었다).
  **쿠버네티스 문서는 CC BY 4.0 — 표시만 하면 된다**(`kubernetes/website` 의 `LICENSE` · 2026-10-01 확인).
★ **그리고 평가셋과 안 겹친다.** `d001` · `d002` 는 AWS 안내서 14권에서 **467 문서**를 떠 왔다 —
  같은 권으로 학습하면 **평가셋의 이웃을 학습하는 것**이다. 다른 코퍼스면 그 물음이 아예 없다.
★ **그리고 한 벤더에 안 갇힌다.** 사람이 적은 말 — 「aws 도메인만 과적합 하지 말고」.
★ **마크다운을 다시 안 읽는다.** 문장 자르기 · 표시(`lit` · `ui`) 뽑기는 `tools/fetch_awsdocs.py` 가
  이미 안다(§122). **그 함수를 부른다** — 같은 규칙을 두 곳에 두지 않는다(§158 · §163).
★ **온톨로지로 안 거른다.** 평가셋은 「잴 것이 있는 줄」 만 남겨야 하지만(§70) **학습 원문은 넓어야**
  한다. AWS 사전이 든 줄만 남기면 **AWS 문장만 골라 담는 꼴**이고 그것이 피하려던 바로 그 일이다.
★ **자리마다 상한을 둔다.** `content/en/docs/` 아래 첫 칸(`concepts` · `tasks` · `reference` …)으로
  나눈다 — `reference` 가 기계 생성 문서라 그대로 두면 셋을 먹는다.
★ **결정적이다.** 문장 해시로 정렬하고 `seed` 로 뽑는다(`fetch_awsdocs.choose` 와 같은 셈).
★ **밖 — 번역하지 않는다.** 이 도구가 내는 것은 **영어 원문**이고, 교사가 번역하는 것은 다음 걸음이다.
★ **밖 — 품질을 안 본다.** 문장이 번역할 만한가는 `gemba` 가 번역 뒤에 묻는다.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from seshat import ontology, paths  # noqa: E402

REPO = "https://github.com/kubernetes/website.git"
가지 = "main"
문서자리 = "content/en/docs"
라이선스 = "CC BY 4.0"
표시 = "© The Kubernetes Authors · https://github.com/kubernetes/website · CC BY 4.0"


def _도구(이름: str):
    """같은 규칙을 두 곳에 두지 않는다(DECISIONS §158) — `gemba.py` 와 같은 꼴."""
    spec = importlib.util.spec_from_file_location(이름, ROOT / f"tools/{이름}.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[이름] = m
    spec.loader.exec_module(m)
    return m


def clone(cache: pathlib.Path) -> str:
    """받아 두고 커밋 sha 를 돌려준다. **`cache` 층이라 해시 대장 밖이다**(다시 받을 수 있다).

    ★ **성긴 체크아웃이다.** 저장소 전체는 이미지까지 들어 크고, 쓰는 것은 영어 문서뿐이다 —
      `--filter=blob:none --sparse` 로 **29MB · 1,720 문서**만 받는다.
    """
    d = cache / "website"
    if not (d / ".git").exists():
        d.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run(["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
                            "--branch", 가지, "-q", REPO, str(d)], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"쿠버네티스 문서를 못 받았다 — {r.stderr.strip()[:200]}\n"
                             f"    망이 되는지 본다 : git ls-remote --heads {REPO} {가지}\n"
                             f"    받는 곳 : {d}")
        subprocess.run(["git", "sparse-checkout", "set", 문서자리], cwd=d, check=True,
                       capture_output=True)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=d, capture_output=True, text=True)
    return sha.stdout.strip()[:12]


def harvest(root: pathlib.Path) -> dict[str, list]:
    """`content/en/docs/<자리>/…` 의 첫 칸으로 모은다. (자리 → 문장들).

    ★ **자리로 나누는 까닭은 상한이다.** `reference` 아래는 API 레퍼런스라 기계 생성 문장이 많고,
      그대로 두면 **한 자리가 셋을 먹는다**(`fetch_awsdocs` 가 DynamoDB 에서 겪은 그 일).
    ★ **밖 — 번역 난이도를 안 본다.** 어느 자리가 배우기 좋은지는 이 도구가 모른다.
    """
    FA = _도구("fetch_awsdocs")
    난것: dict[str, list] = collections.defaultdict(list)
    본문 = root / 문서자리
    if not 본문.exists():
        raise SystemExit(f"문서 자리가 없다 — {본문}\n"
                         f"    성긴 체크아웃이 안 됐다 : git -C {root} sparse-checkout set {문서자리}")
    for f in sorted(본문.rglob("*.md")):
        안 = f.relative_to(본문).parts
        자리 = 안[0] if len(안) > 1 else "(뿌리)"
        문서 = f.relative_to(본문).as_posix()
        for ln in FA.sentences(f.read_text(encoding="utf-8")):
            난것[자리].append(ln._replace(doc=문서))
    return dict(난것)


def rows(onto: list[dict], picked: list, 이름: str) -> list[dict]:
    """학습 원문 줄. **도메인셋과 같은 꼴**이라 `evaluate` · `backends` · `gemba` 가 그대로 읽는다.

    ★ `keep` 은 **AWS 사전이 아는 이름**이고 쿠버네티스 글에는 드물다 — 비어도 맞다.
      거르는 열쇠가 아니라 **있으면 자리표시가 지켜 준다**는 뜻으로만 싣는다.
    ★ **밖 — 정답(ref)이 없다.** 교사가 만들 것이고, 이 파일은 원문만 든다.
    """
    out = []
    for i, ln in enumerate(picked, 1):
        keep = sorted({ln.text[a:b] for a, b, _ in ontology.find(onto, ln.text, keep_only=True)})
        빼기 = [[t, at] for t, at in ln.lit if t not in keep]
        빼기2 = [[t, at] for t, at in ln.ui if t not in keep]
        out.append({"id": f"{이름}-{i:04d}", "src": ln.text, "keep": keep,
                    "lit": 빼기, "ui": 빼기2, "guide": ln.guide, "doc": ln.doc})
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="k001")
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=21)
    ap.add_argument("--cap", type=int, default=1200, help="자리마다 이만큼까지")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(sys.argv[1:] if argv is None else argv)

    FA = _도구("fetch_awsdocs")
    cache = paths.require_lake() / "cache/k8s"
    sha = clone(cache)
    found = harvest(cache / "website")
    if a.list:
        print(f"  커밋 {sha} · 자리 {len(found)} · 문장 {sum(len(v) for v in found.values())}")
        for 자리, 줄 in sorted(found.items(), key=lambda kv: -len(kv[1])):
            print(f"    {len(줄):6}  {자리}")
        return 0

    picked = FA.choose(found, a.n, a.seed, a.cap)
    onto = ontology.load()
    줄 = rows(onto, picked, a.name)
    낼곳 = ROOT / f"data/train/{a.name}.jsonl"
    낼곳.parent.mkdir(parents=True, exist_ok=True)
    머리 = {"meta": True, "about": "쿠버네티스 문서에서 뽑은 증류용 영어 원문 — 정답(ref)이 없다",
            "license": 라이선스, "attribution": 표시, "repo": REPO, "branch": 가지,
            "commit": sha, "n": len(줄), "seed": a.seed, "cap": a.cap,
            "made_by": "tools/fetch_k8s.py",
            "note": "평가에 쓰지 않는다 — 학습 원문이다. 동일조건(SA)이 없어 뿌려도 표시만 하면 된다"}
    낼곳.write_text("\n".join([json.dumps(머리, ensure_ascii=False),
                              *(json.dumps(r, ensure_ascii=False) for r in 줄)]) + "\n",
                    encoding="utf-8")
    해시 = hashlib.sha256(낼곳.read_bytes()).hexdigest()[:16]
    print(f"  {낼곳.relative_to(ROOT)}  {len(줄)}줄 · 커밋 {sha} · sha {해시}")
    print(f"  다음 : 교사로 번역한다(**판 하나가 곧 증류셋의 절반이다**)\n"
          f"    uv run python -m seshat.evaluate --backend gemma3-12b+ph+retry+endings+terms \\\n"
          f"      --set data/train/{a.name}.jsonl --name H-088-teacher-{a.name} --resume\n"
          f"  그 뒤 : 거른다 — python3 tools/gemba.py --run teacher=runs/<그 판>.jsonl --out …")
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
