"""한 · 영 문법 대조 축 — 오류가 **어느 구문에서** 나는지 가르는 자(MASTER §7 R1 · DECISIONS §125).

  from seshat import grammar
  grammar.axes("The data that Glue writes to S3 is not encrypted.")   # ('관형절', '피동', '부정')
  grammar.chains("Use the local secondary index.")                     # ['local secondary index']

★ **지표가 아니라 축이다.** 이 파일은 점수를 안 매긴다 — 줄을 무더기로 가른다. 「4B 가 나쁘다」 는
  쓸모가 적고 「4B 가 **관형절에서** 나쁘다」 는 다음에 무엇을 할지 말해 준다(`tools/slice.py`).
★ **원문만 본다.** 조사와 높임법은 번역 쪽의 일이고 `josa` · `style` 이 이미 잰다. 여기서 세는 것은
  **영어 원문이 한국어로 갈 때 뒤집히는 자리**다.
★ **모양으로만 본다. 구문 분석기가 아니다.** 정확도를 재고 적었다 — d001 600줄에서 축마다 20줄씩
  눈으로 확인했다(DECISIONS §125). 틀리는 자리를 아래에 적는다. **틀리는 줄이 있다는 것을 알고 쓴다.**
★ **`that` 은 두 가지다.** `the data that Glue writes`(관형절)와 `ensure that the setting is on`(명사절)은
  한국어에서 가는 길이 다르다 — 앞엣것은 「Glue 가 쓰는 데이터」 로 **앞으로 돌고**, 뒤엣것은
  「설정이 켜져 있는지 확인」 으로 **안긴다.** 절을 이끄는 동사 목록으로 가른다.
"""
from __future__ import annotations

import re

# 명사절을 이끄는 말. 이 뒤의 `that` 은 관형절이 아니다 — 「… 인지 확인」 으로 안긴다
_CLAUSE_HEAD = frozenset(
    "ensure ensures ensured note notes noted mean means meant show shows shown verify verifies confirm confirms "
    "assume assumes indicate indicates specify specifies require requires required believe believes recommend "
    "recommends suggest suggests say says state states imply implies guarantee guarantees know knows so such "
    "provided assuming given".split())
_THAT = re.compile(r"(\w+)?\s*\bthat\s+(\w+)")

PATTERNS: dict[str, re.Pattern] = {
    # 관형절 — 한국어는 **머리 명사 앞**으로 돈다. 길면 머리 명사가 통째로 사라진다(DECISIONS §95)
    # 관형절 · 명사절은 `that` 앞말을 봐야 갈리므로 아래 `_that` 이 따로 센다
    # 피동 — 한국어는 능동으로 푸는 쪽이 자연스럽고, 행위자가 빠지면 주어를 잃는다
    "피동": re.compile(r"\b(?:is|are|was|were|be|been|being)\s+(?:not\s+)?(?:\w+ly\s+)?\w+(?:ed|en)\b", re.I),
    # 부정 — 부정어 자리가 문장 끝으로 간다. 범위를 잘못 잡으면 뜻이 뒤집힌다
    "부정": re.compile(r"\b(?:not|never|cannot|can't|doesn't|don't|won't|without|neither|nor|unable|no)\b", re.I),
    # 최상급 — thoth 도메인의 핵심이다(「LEAST operational overhead」). d001 에는 드물다
    "최상급": re.compile(r"\b(?:most|least|best|worst|largest|smallest|highest|lowest|fewest|greatest)\b"
                      r"|\b\w{4,}est\b", re.I),
    "비교급": re.compile(r"\bthan\b|\b(?:more|less|fewer|greater|larger|smaller|higher|lower)\b", re.I),
    # 조건절 — 한국어는 앞에 놓는다. 통째로 빠지는 것이 관측됐다(DECISIONS §105)
    "조건절": re.compile(r"\b(?:if|unless|whenever|when)\b", re.I),
    # 목적 — `to reduce latency, …` 는 「지연을 줄이려면」 으로 앞으로 돈다
    "목적": re.compile(r"\bto\s+[a-z]{3,}\b"),
    "등위": re.compile(r",\s+and\b|\band then\b|\b\w+,\s+\w+,\s+and\b", re.I),
}

# 연쇄를 끊는 말 — 관사 · 전치사 · 접속사 · 조동사. 이 말이 나오면 명사 줄이 끊긴다
_STOP = frozenset(
    "the a an of in on to for with without and or but nor is are was were be been being by that this these those "
    "from as at it its their your our can could may might must will would should do does did not no if when then "
    "than there here into onto over under between through during each any all some other such more most both "
    "about after before above below up down out off per via until while since against among across within upon "
    "toward which who whose whom what where why how also however so because although unless whenever".split())
_WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")
# 명사구가 시작하는 자리. **한정사 뒤에서만 센다** — 아무 데서나 세면 동사가 명사로 세어진다
_DET = frozenset("the a an this that these those your their our its each every any all some no another".split())
DEEP = 3        # 이 깊이부터 「연쇄」 다. d001 600줄에서 17.5%


def chains(src: str, skip: list[tuple[int, int]] | None = None) -> list[str]:
    """**한정사 뒤에서 시작하는 명사 줄** 중 `DEEP` 이상인 것.

    영어는 명사를 왼쪽으로 쌓고 한국어는 오른쪽으로 푼다 — `the local secondary index` 는
    「로컬 보조 인덱스」 다. 쌓기가 깊을수록 수식 관계가 뒤집히기 쉽고, 4B 가 실제로 뒤집었다
    (「예시를 기반으로 한 리소스 정책」 · DECISIONS §95).

    ★ **정확도 0.68 이다**(d001 20줄 손 검사 · 정탐 13 · 오탐 7 · DECISIONS §125). 새는 자리는 늘
      같다 — 명사구 뒤의 **동사까지 줄에 들어온다**(`delivery stream uses` · `trust policy see`).
      품사 분석기 없이는 거기서 못 끊는다. **줄 하나를 두고 「이 줄은 연쇄다」 라고 말하는 자가
      아니라, 무더기를 가르는 자다** — 두 팔을 같은 무더기에서 견주므로 잡음은 양쪽에 같이 든다.
    ★ 대문자로 시작하는 낱말은 끊는다 — 제품 이름은 통째로 하나다(`Amazon Kinesis Data Streams`).
    ★ `-ing` · `-ed` 로 끝나는 낱말도 끊는다. 분사가 줄을 길게 늘인다(`by using relevant parameters`).
    ★ `skip` 은 세지 않을 자리다 — `evaluate.marked(row)` 를 넘기면 `arn:aws:s3:::my-bucket` 같은
      **식별자가 명사 줄로 세어지는 것**을 막는다(DECISIONS §122 의 표시를 여기서 다시 쓴다).
    """
    out: list[str] = []
    cur: list[str] = []
    armed = False

    def 닫기():
        if len(cur) >= DEEP:
            out.append(" ".join(cur))
        cur.clear()

    for m in _WORD.finditer(src):
        w, lw = m.group(), m.group().lower()
        if lw in _DET:
            닫기()
            armed = True
            continue
        if (lw in _STOP or w[0].isupper() or lw.endswith(("ing", "ed"))
                or any(m.start() >= a and m.end() <= b for a, b in (skip or ()))):
            닫기()
            armed = False
            continue
        if armed:
            cur.append(w)
    닫기()
    return out


def depth(src: str, skip: list[tuple[int, int]] | None = None) -> int:
    """가장 깊은 명사 줄의 길이. 없으면 0."""
    return max((len(c.split()) for c in chains(src, skip)), default=0)


def _that(src: str) -> set[str]:
    """`that` 을 관형절과 명사절로 가른다. **앞말이 정한다** — 정규식 되돌아보기로는 못 한다.

      the data **that** Glue writes      → 관형절 · 「Glue 가 쓰는 데이터」 로 앞으로 돈다
      ensure **that** the setting is on  → 명사절 · 「설정이 켜져 있는지 확인」 으로 안긴다
    """
    got = set()
    if re.search(r"\b(?:which|who|whose|whom)\s+\w+", src):
        got.add("관형절")
    for m in _THAT.finditer(src):
        got.add("명사절" if (m.group(1) or "").lower() in _CLAUSE_HEAD else "관형절")
    return got


def axes(src: str, skip: list[tuple[int, int]] | None = None) -> tuple[str, ...]:
    """이 문장이 걸린 축들. **겹친다** — 한 문장이 여러 축에 든다."""
    got = _that(src) | {k for k, p in PATTERNS.items() if p.search(src)}
    if chains(src, skip):
        got.add("연쇄")
    return tuple(a for a in AXES if a in got)


AXES = ("관형절", "명사절", *PATTERNS, "연쇄")
