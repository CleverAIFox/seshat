"""AWS 공식 문서에서 도메인 평가셋을 만든다 — 정답 없이(DECISIONS §92).

  python3 tools/fetch_awsdocs.py --name d001 --n 600 --seed 21
  python3 tools/fetch_awsdocs.py --list                      # 어느 안내서를 받는가
  python3 tools/fetch_awsdocs.py --name d001 --guides amazon-dynamodb-developer-guide,aws-glue-developer-guide

★ **문서가 코퍼스다.** AWS 는 2023-06 에 GitHub 문서 저장소를 얼렸지만(`archived` 가지) 본문이 든
  `master` 가지는 그대로 있고 **CC BY-SA 4.0** 이다(각 저장소 `LICENSE` · 2026-09-27 확인). 긁는 것이
  아니라 라이선스가 열린 저장소를 받는 것이다 — thoth PLAN §4 가 버린 「스크래핑 · 봇 감지 우회」와
  다른 일이다.
★ **정답이 필요 없다.** 도메인 지표(`term` · `term_off` · `keep` · `josa` · `style` · `hangul`)는 전부
  참조 없이 센다. 참조가 필요한 것은 `chrf` 뿐이고 그 자는 FLORES+ 가 든다(PLAN #6 「원문만 쓴다」).
  그래서 **영어 원문만으로 도메인셋이 선다** — 장비도 사람도 필요 없다.
★ **온톨로지가 없는 줄은 버린다.** 도메인셋인데 도메인 낱말이 한 개도 없으면 `term` 의 분모가 0 이고
  `keep` 이 잴 것이 없다. 재는 것이 없는 줄을 500 개 넣으면 숫자가 묽어지기만 한다(DECISIONS §70).
★ **안내서마다 상한을 둔다.** DynamoDB 하나가 10,767 문장이라 그대로 두면 한 서비스의 말투가 셋을
  먹는다. `--cap` 이 고르게 자른다.
★ **결정적이다.** 문장 해시로 정렬한 뒤 `seed` 로 뽑는다. 파일을 훑는 순서 · OS · 재클론에 안 흔들린다.
  같은 인자면 같은 셋이고 `set_sha256` 이 그것을 증언한다.
★ **커밋하지 않는다.** CC BY-SA 는 **나눠 줄 때** 저작자 표시와 동일 조건을 건다. 받는 도구를 커밋하고
  데이터는 `data/domain/` 에 둔다(git 이 무시한다 · FLORES+ 와 같은 처분, DECISIONS §11).
★ **`train` 을 달지 않는다.** 동일 조건(ShareAlike)이 학습 산출물까지 미치는지 읽지 않았다. 모르면
  미확인 쪽으로 간다 — 카탈로그가 그 문을 지킨다(`uses`).
★ **커밋 sha 를 적는다.** 얼린 저장소라 안 바뀌지만, 바뀌면 같은 인자에서 다른 셋이 나온다. 머리줄이
  sha 를 들어서 그때 무엇이 달라졌는지 말할 수 있게 한다.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from seshat import catalog, ontology, paths  # noqa: E402

OUT = ROOT / "data/domain"
LICENSE = "CC BY-SA 4.0"
ORG = "https://github.com/awsdocs"
# ★ **본문 가지를 이름으로 못 맞힌다.** 얼릴 때 기본 가지를 `archived` 로 돌렸는데 그 아래 남은
#   본문 가지는 저장소마다 `master` 이거나 `main` 이다(2026-09-27 실측 — athena · s3 · msk 는 main,
#   step-functions · cloudwatch 는 master). 원격에 무엇이 있는지 **묻고 고른다.** `archived` 는 본문이
#   없다 — NOTICE 한 장이다.
BRANCHES = ("master", "main")

# DEA-C01 이 묻는 범위. 저장소 이름은 2026-09-27 에 `master/README.md` 로 확인했다.
GUIDES = (
    "amazon-dynamodb-developer-guide",
    "amazon-redshift-developer-guide",
    "amazon-redshift-management-guide",
    "aws-glue-developer-guide",
    "amazon-kinesis-data-streams-developer-guide",
    "amazon-kinesis-data-firehose-developer-guide",
    "amazon-athena-user-guide",
    "amazon-emr-management-guide",
    "amazon-s3-userguide",
    "amazon-msk-developer-guide",
    "aws-step-functions-developer-guide",
    "amazon-cloudwatch-user-guide",
    "amazon-opensearch-service-developer-guide",
    "aws-dms-user-guide",
)

_FENCE = re.compile(r"^\s*```")
_IMG = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_CODE = re.compile(r"`([^`]*)`")
_BULLET = re.compile(r"^\s*[-+*]\s+")
_EMPH = re.compile(r"\*\*|__|\*")
_ESCAPED = re.compile(r"\\([-.\[\]()*_+#!<>|])")
_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(])")
# 산문이 아닌 것 — 자리표시 · URL · 명령줄 · 끊긴 문장
_NOT_PROSE = re.compile(r"[{}<>|]|\$\{|https?://|\.\.\.|^\s*aws\s", re.I)
# ★ 머리에 붙은 콜론은 정의 목록이다 — `Table: The tables that this policy applies to.` 는 표의 칸이
#   문장처럼 보이는 것이고, 앞머리가 문장 밖에 있어 번역이 제 자리를 못 찾는다.
_DEFLIST = re.compile(r"^[^:]{1,20}:\s")
MIN_CHARS, MAX_CHARS, MIN_WORDS = 40, 300, 7


def _body(md: str) -> list[str]:
    """코드 · 표 · 제목을 뺀 줄. **본문만 남긴다.**

    ★ 들여쓴 줄을 버리는 것은 마크다운에서 그것이 코드 블록이기 때문이다. 목록 안의 이어진 줄도
      같이 버려지지만, 그런 줄은 앞줄에서 이미 끊겨 있어 문장으로 서지 못한다.
    """
    out, fence = [], False
    for ln in md.splitlines():
        if _FENCE.match(ln):
            fence = not fence
            continue
        if fence or ln.startswith(("    ", "\t")):
            continue
        s = ln.lstrip()
        if s.startswith(("|", "#")):
            continue
        out.append(ln)
    return out


def _plain(ln: str) -> str:
    """마크다운 표시를 걷는다. **링크는 글자만 남긴다** — 주소는 문장이 아니다."""
    ln = _IMG.sub("", ln)
    ln = _LINK.sub(r"\1", ln)
    ln = _CODE.sub(r"\1", ln)
    ln = _BULLET.sub("", ln)
    ln = _EMPH.sub("", ln)
    return _ESCAPED.sub(r"\1", ln).strip()


def sentences(md: str) -> list[str]:
    """한 문서에서 산문 문장만. 모양으로만 거르고 뜻은 보지 않는다."""
    out = []
    for ln in _body(md):
        c = _plain(ln)
        if not c:
            continue
        for s in _SPLIT.split(c):
            s = s.strip()
            if not (MIN_CHARS <= len(s) <= MAX_CHARS):
                continue
            if not s[0].isupper() or s[-1] not in ".?!":
                continue
            if len(s.split()) < MIN_WORDS or _NOT_PROSE.search(s) or _DEFLIST.match(s):
                continue
            if sum(ch.isascii() for ch in s) / len(s) < 0.99:
                continue
            out.append(s)
    return out


def branch_of(guide: str) -> str:
    """원격이 든 본문 가지. **묻고 고른다** — 이름으로 맞히면 절반이 틀린다."""
    r = subprocess.run(["git", "ls-remote", "--heads", f"{ORG}/{guide}.git"], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"{guide} 의 가지를 못 물었다 — {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else '까닭 없음'}")
    heads = {ln.rsplit("refs/heads/", 1)[-1] for ln in r.stdout.splitlines() if "refs/heads/" in ln}
    got = next((b for b in BRANCHES if b in heads), None)
    if not got:
        raise SystemExit(f"{guide}: 본문 가지가 없다 — 원격에 {sorted(heads)} 뿐이다\n"
                         f"    `archived` 에는 NOTICE 한 장만 있다. 저장소가 정말 비었는지 본다")
    return got


def clone(cache: pathlib.Path, guide: str) -> str:
    """받아 두고 커밋 sha 를 돌려준다. 이미 있으면 다시 받지 않는다 — `cache` 층은 해시 대장 밖이다."""
    d = cache / guide
    if not (d / ".git").exists():
        d.parent.mkdir(parents=True, exist_ok=True)
        branch = branch_of(guide)
        r = subprocess.run(["git", "clone", "--depth", "1", "--branch", branch, "-q",
                            f"{ORG}/{guide}.git", str(d)], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"{guide} 를 못 받았다 — {r.stderr.strip().splitlines()[-1] if r.stderr.strip() else '까닭 없음'}\n"
                             f"    가지   : {branch}\n"
                             f"    받는 곳: {cache}")
        if not (d / "LICENSE").exists():
            raise SystemExit(f"{guide}: LICENSE 가 없다 — 라이선스를 못 읽은 것을 {LICENSE} 라고 적지 않는다")
    return subprocess.run(["git", "-C", str(d), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()


def harvest(onto: list[dict], root: pathlib.Path) -> list[tuple[str, str]]:
    """(문장, 문서 이름). **온톨로지가 든 줄만** 남긴다."""
    out, seen = [], set()
    for p in sorted(root.rglob("*.md")):
        if p.name in ("README.md", "CONTRIBUTING.md", "LICENSE-SUMMARY.md"):
            continue
        for s in sentences(p.read_text(encoding="utf-8", errors="replace")):
            if s in seen or not ontology.find(onto, s):
                continue
            seen.add(s)
            out.append((s, p.name))
    return out


def rows(onto: list[dict], picked: list[tuple[str, str, str]]) -> list[dict]:
    """평가셋 줄. `keep` 은 **온톨로지가 영어로 남기라고 한 표기**다 — 탐침과 같은 근거다."""
    out = []
    for i, (src, guide, doc) in enumerate(picked, 1):
        keep = sorted({src[a:b] for a, b, _ in ontology.find(onto, src, keep_only=True)})
        out.append({"id": f"awsdocs-{i:04d}", "src": src, "keep": keep, "guide": guide, "doc": doc})
    return out


def choose(found: dict[str, list[tuple[str, str]]], n: int, seed: int, cap: int) -> list[tuple[str, str, str]]:
    """안내서마다 `cap` 까지 자르고 합쳐서 `n` 을 뽑는다. **해시로 정렬한다** — 순서가 기계를 안 탄다."""
    pool: list[tuple[str, str, str]] = []
    for guide in sorted(found):
        got = sorted(found[guide], key=lambda t: hashlib.sha256(t[0].encode()).hexdigest())
        pool += [(s, guide, doc) for s, doc in got[:cap]]
    pool.sort(key=lambda t: hashlib.sha256(t[0].encode()).hexdigest())
    if len(pool) < n:
        raise SystemExit(f"문장이 {len(pool)} 뿐인데 {n} 을 달라고 했다 — `--cap` 을 올리거나 `--n` 을 내린다")
    return random.Random(seed).sample(pool, n)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", help="data/domain/<이름>.jsonl")
    ap.add_argument("--n", type=int, default=600)
    ap.add_argument("--seed", type=int, default=21)
    ap.add_argument("--cap", type=int, default=400, help="안내서 하나에서 가져올 최대 문장")
    ap.add_argument("--guides", default="", help="쉼표로 고른다. 비면 전부")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)
    if a.list:
        for g in GUIDES:
            print(f"  {ORG}/{g}  {LICENSE}")
        return 0
    if not a.name:
        raise SystemExit("--name 이 필요하다 (또는 --list)")

    guides = [g.strip() for g in a.guides.split(",") if g.strip()] or list(GUIDES)
    unknown = [g for g in guides if g not in GUIDES]
    if unknown:
        raise SystemExit(f"모르는 안내서 {unknown} — `--list` 가 아는 것을 든다")

    cache = paths.require_lake() / "cache/awsdocs"
    catalog.gate(cache)             # 레이크 자리도 묻는다(DECISIONS §121)
    onto = ontology.load()
    found, shas = {}, {}
    for g in guides:
        shas[g] = clone(cache, g)
        found[g] = harvest(onto, cache / g)
        print(f"  {g:48} {len(found[g]):>6}문장  {shas[g][:10]}", file=sys.stderr)

    picked = choose(found, a.n, a.seed, a.cap)
    made = rows(onto, picked)
    meta = {"meta": True,
            "about": f"AWS 공식 문서 {len(guides)}권에서 뽑은 도메인 문장 {a.n}줄 · seed {a.seed} · 안내서당 최대 {a.cap}",
            "license": LICENSE,
            "attribution": f"© Amazon Web Services, Inc. · {ORG} · {LICENSE}",
            "sources": {g: shas[g] for g in sorted(shas)},
            "made_by": "tools/fetch_awsdocs.py",
            "note": "참조(ref)가 없다 — 도메인 지표는 참조 없이 센다. chrF 는 FLORES+ 가 든다"}
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{a.name}.jsonl"
    catalog.gate(out)               # 쓰기 전에 묻는다(DECISIONS §121)
    out.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in [meta, *made]) + "\n", encoding="utf-8")
    print(f"  {out.relative_to(ROOT)}  {len(made)}줄")
    return 0


if __name__ == "__main__":
    sys.exit(main())
