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
★ **문서의 표시를 들고 나온다**(DECISIONS §122). 마크다운의 `` `코드` `` 는 **손대면 안 되는 글자**이고
  `**굵게**` 는 콘솔 라벨이다. 2026-09-27 까지 이 도구는 둘을 지우기만 했고, 그래서
  `bucket-owner-full-control` 이 산문과 구별되지 않아 지표가 그것을 「개념」으로 셌다. 줄이 `lit` · `ui` 를
  든다. **식별자를 사전에 적으려 하지 않는다 — 무한하고, 문서가 이미 적어놨다.**
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
import typing

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
_BOLD = re.compile(r"\*\*([^*]+)\*\*")      # 콘솔 라벨. `_EMPH` 가 별표를 지우기 **전에** 집는다
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


class Line(typing.NamedTuple):
    """문장 하나와 **원문이 그 문장에 해 둔 표시**."""
    text: str
    lit: tuple[str, ...] = ()       # `` `코드` `` — 식별자 · 값 · API 이름. 그대로 남아야 한다
    ui: tuple[str, ...] = ()        # `**굵게**` — 콘솔 라벨. 지금은 기록만 한다
    guide: str = ""
    doc: str = ""


def _grab(pat: re.Pattern, ln: str, into: list[str]) -> str:
    """표시를 걷되 **걷어 낸 글자를 `into` 에 담는다.** 지우기와 기억하기를 한 번에 한다."""
    def keep(m: re.Match) -> str:
        into.append(m.group(1))
        return m.group(1)
    return pat.sub(keep, ln)


def plain(ln: str) -> tuple[str, list[str], list[str]]:
    """마크다운 표시를 걷는다. **링크는 글자만 남긴다** — 주소는 문장이 아니다.

    ★ **지우기만 하던 함수였다.** `_CODE.sub(r"\\1", ln)` 한 줄이 `` `bucket-owner-full-control` `` 의
      백틱을 없앴고, 그 뒤로는 그것이 산문인지 타이핑할 값인지 아무도 몰랐다. 지표는 몰라서 개념으로
      셌다(DECISIONS §98 · §122). **문서가 이미 답을 적어놨는데 수확기가 그것을 지웠다.**
    """
    ln = _IMG.sub("", ln)
    ln = _LINK.sub(r"\1", ln)
    lit: list[str] = []
    ui: list[str] = []
    ln = _grab(_CODE, ln, lit)
    ln = _BULLET.sub("", ln)
    ln = _grab(_BOLD, ln, ui)           # `_EMPH` 가 별표를 지우기 전이다
    ln = _EMPH.sub("", ln)
    씻기 = lambda xs: [t for t in (_ESCAPED.sub(r"\1", _EMPH.sub("", x)).strip() for x in xs) if t]  # noqa: E731
    return _ESCAPED.sub(r"\1", ln).strip(), 씻기(lit), 씻기(ui)


def sentences(md: str) -> list[Line]:
    """한 문서에서 산문 문장만. 모양으로만 거르고 뜻은 보지 않는다.

    ★ **한 줄이 여러 문장으로 쪼개진다.** 표시는 그것이 실제로 든 문장에만 붙인다 — 같은 줄의
      옆 문장에 붙이면 있지도 않은 글자가 남았는지 묻게 된다.
    """
    out = []
    for ln in _body(md):
        c, lit, ui = plain(ln)
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
            out.append(Line(s, tuple(sorted({t for t in lit if t in s})),
                            tuple(sorted({t for t in ui if t in s}))))
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


def harvest(onto: list[dict], root: pathlib.Path) -> list[Line]:
    """문서 이름을 붙인 문장. **온톨로지가 든 줄만** 남긴다."""
    out, seen = [], set()
    for p in sorted(root.rglob("*.md")):
        if p.name in ("README.md", "CONTRIBUTING.md", "LICENSE-SUMMARY.md"):
            continue
        for ln in sentences(p.read_text(encoding="utf-8", errors="replace")):
            if ln.text in seen or not ontology.find(onto, ln.text):
                continue
            seen.add(ln.text)
            out.append(ln._replace(doc=p.name))
    return out


def rows(onto: list[dict], picked: list[Line]) -> list[dict]:
    """평가셋 줄. `keep` 은 **온톨로지가 영어로 남기라고 한 표기**다 — 탐침과 같은 근거다.

    ★ `lit` 에서 `keep` 과 겹치는 것을 뺀다. 같은 글자를 두 지표가 세면 분모만 부푼다 —
      `keep` 은 사전이 아는 이름이고 `lit` 은 문서가 표시한 나머지다(DECISIONS §122).
    """
    out = []
    for i, ln in enumerate(picked, 1):
        keep = sorted({ln.text[a:b] for a, b, _ in ontology.find(onto, ln.text, keep_only=True)})
        out.append({"id": f"awsdocs-{i:04d}", "src": ln.text, "keep": keep,
                    "lit": [t for t in ln.lit if t not in keep], "ui": list(ln.ui),
                    "guide": ln.guide, "doc": ln.doc})
    return out


def choose(found: dict[str, list[Line]], n: int, seed: int, cap: int) -> list[Line]:
    """안내서마다 `cap` 까지 자르고 합쳐서 `n` 을 뽑는다. **해시로 정렬한다** — 순서가 기계를 안 탄다.

    ★ **뽑는 열쇠는 문장 글자뿐이다**(`t[0]` = `Line.text`). 줄이 표시를 더 들고 다녀도 같은 인자면
      같은 문장이 나온다 — 표시를 붙이는 일이 셋을 바꾸지 않는다.
    """
    pool: list[Line] = []
    for guide in sorted(found):
        got = sorted(found[guide], key=lambda t: hashlib.sha256(t[0].encode()).hexdigest())
        pool += [ln._replace(guide=guide) for ln in got[:cap]]
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
            "marks": "lit 은 원문의 `코드` — 그대로 남아야 한다(지표 lit). ui 는 **굵게** — 콘솔 라벨이고 "
                     "지금은 기록만 한다. 한국어 콘솔이 라벨을 현지화하는지 확인 전이다(DECISIONS §122)",
            "note": "참조(ref)가 없다 — 도메인 지표는 참조 없이 센다. chrF 는 FLORES+ 가 든다"}
    OUT.mkdir(parents=True, exist_ok=True)
    out = OUT / f"{a.name}.jsonl"
    catalog.gate(out)               # 쓰기 전에 묻는다(DECISIONS §121)
    out.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in [meta, *made]) + "\n", encoding="utf-8")
    print(f"  {out.relative_to(ROOT)}  {len(made)}줄")
    return 0


if __name__ == "__main__":
    sys.exit(main())
