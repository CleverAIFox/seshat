"""산문이 가리키는 것과 산문의 꼴을 본다 — `check_docs` 가 못 보는 세 자리.

  python3 tools/check_prose.py          검사한다. 위반이면 1, 도구 고장이면 2
  python3 tools/check_prose.py --list   무엇을 보는지 찍는다

★ 이 파일은 **seshat 것**이다 — thoth 사본이 아니다(DECISIONS §5). `check_docs.py` 는
  사본이라 거기에 규칙을 더하면 원본과 갈린다. 같은 규칙이 thoth 에도 필요하면
  거기에서 만들어 가져온다(PLAN #49).

| 검사 | 무엇을 잡는가 |
|---|---|
| `맨절` | 문서명 없는 `§N` 이 **그 문서에도 DECISIONS 에도 없는 번호**를 가리킨다 |
| `표깨짐` | 빈 줄 바로 뒤에 홀로 선 `\\|…\\|` — 렌더링하면 표로 안 그려진다 |
| `낱말` | MASTER §0-0 의 사전이 없다 · 표에만 있고 본문에서 안 쓰이는 낱말이 있다 |
| `날짜` | MASTER 가 날짜를 적고 **그 경위가 어디 사는지**는 안 적었다 |
| `CI밖` | `verify.sh` 가 CI 에서 다르게 돌리는 단계를 MASTER §5 가 빠뜨렸다 |
| `빈약속` | 「열려 있다」 · 「아직」 · 「채우지 않았다」 를 적고 `PLAN #N` 을 안 붙였다 |
| `정본하나` | 「명령의 정본은 … 하나다」 가 **두 곳에서 다른 절**을 가리킨다 · 정본 아닌 절이 **도구 셋 이상**의 명령을 늘어놓는다 |

## 1. 맨 `§N`

`check_docs.check_refs` 는 **문서명이 붙은 것만** 본다 — `DECISIONS §9` · `MASTER §7-4`.
문서명 없는 `§9` 는 **패턴으로 아예 안 봤다.** 이 저장소에 그런 자리가 764 곳이고,
그중 **예순 몇 곳이 없는 번호를 가리키고 있었다**(DECISIONS §282).

★ **맨 `§N` 을 금지하지 않는다.** 코드 주석에서는 그것이 집 문체이고, 764 곳을 다 고치는
  규칙은 **아무도 안 지키고 끄는 쪽부터 찾게 된다**(§46 의 교훈). 금지하는 것은 **해석되지
  않는 번호**다.

★ **푸는 순서가 규칙이다.** 자기 `§` 번호를 가진 문서(MASTER · PLAN · DECISIONS)에서는
  **그 문서 자신의 절**로 먼저 읽고, 없으면 DECISIONS 로 읽는다. 둘 다 없으면 위반이다.
  번호를 안 가진 파일(코드 · `related.md` 같은 산문)에서는 DECISIONS 하나로 읽는다.

★ **`§N-M` 꼴은 밖이다.** 그것은 절이 아니라 **절 안의 규칙 번호**이고
  `tools/check_rules.py` 가 실재를 본다(DECISIONS §230).

## 2. 표 깨짐

마크다운 표는 머리줄 · 구분줄 · 몸줄이 **붙어 있어야** 그려진다. 중간에 빈 줄이 들어가면
뒤엣 줄이 **본문 한 줄로 떨어진다.** 눈으로는 표 같아서 안 보이고, 렌더링한 쪽에서만 보인다.

## 3. 명령의 정본

「정본이 하나다」 를 **두 곳에 적으면 정본이 둘이 된다.** 2026-10-03 에 `docs/README.md` 는
「명령의 정본은 `MASTER §0`」, `MASTER §14` 는 「정본은 **이 절**」 을 적고 있었고, 그래서
§0 에 명령 13줄이 따로 살아 있었다 — §14 와 겹치는 도구 17, §0 에만 있는 도구 **0**.

★ **족 가드다**(파이어레인 `tools/gate_parity.py`). 「§0 에 명령이 있나」 를 묻지 않고
  **「정본이라고 선언한 절이 하나인가」 · 「정본 아닌 절이 목록을 드나」** 를 묻는다.
  절이 새로 생겨도, 선언이 옮겨 가도 그대로 물린다.

★ **「목록」 은 줄 수가 아니라 서로 다른 도구 수로 잰다.** §12 가 `sweep.py` 를 두 줄 쓰는 것은
  그 절의 주제이고, 걷어낸 §0 블록은 도구 **17**개였다. 2026-10-03 실측 분포가 **17 과 2 사이에서
  비어 있어서** 문턱을 셋에 둔다.

## 4. 낱말 사전

이 저장소의 말은 거의 다 지어낸 것이고 **어디에도 정의가 없었다** — `강제자` 474 · `자` 4,814 ·
`축` 336 번 쓰면서. 세션이 바뀌면 문맥이 초기화되므로 그 값은 매번 다시 치른다.
`MASTER §0` 의 낱말 표가 정본이고, 여기가 보는 것은 **그 표가 죽지 않았는가** 하나다.

## 5. 날짜가 든 줄

MASTER 에 날짜가 드는 것 자체는 옳다 — `MASTER §0-1` 이 「근거의 분모를 든다」 를 요구한다.
무는 것은 **날짜를 적고 그 경위가 어디 사는지는 안 적은 줄**이다. 그 줄만 보면 「언제 왜
그랬나」 가 MASTER 에 고이고, 그것은 DECISIONS 의 일이다(DECISIONS §9).

## 6. CI 에서 다르게 도는 단계

`verify.sh` 가 CI 에서 다르게 돌리는 단계를 `MASTER §5` 가 **전부** 드는가. 같은 병이 같은
자리에서 세 번째다 — 목록을 지우고 줄여도 **남은 목록에는 강제자가 있어야 한다**.

## 7. 빈 약속

「이 항목은 열려 있다」 를 적고 PLAN 에 행을 안 두면 **아무도 안 본다.** 문장으로 남긴
약속은 행이 없으면 약속이 아니다.

  0  이상 없음
  1  위반
  2  도구 고장
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

문서들 = ("docs/MASTER.md", "docs/PLAN.md", "docs/DECISIONS.md")
볼디렉터리 = ("seshat", "tools", "tests", "data", ".github", "docs")
볼확장 = {".py", ".js", ".sh", ".md", ".json", ".toml", ".yml", ".html"}

# ── 1. 맨 §N ────────────────────────────────────────────────────────────────
# `§` 뒤가 숫자인 자리. `§11-3` 처럼 뺄셈 꼴이 붙으면 규칙 번호이므로 여기서 안 본다.
절참조 = re.compile(r"§\s*(\d+)(?![\d\s]*-\s*\d)")
# 바로 앞이 문서 이름이거나 `§N ·` 사슬이면 **붙은 참조**다. 백틱 · 마크다운 링크 ·
# `.md` 꼬리 · 남의 저장소 이름을 다 받는다.
이름 = r"(?:DECISIONS|MASTER|PLAN|hypotheses|related|escape|colab|grammar)"
붙은앞 = re.compile(
    r"(?:"
    rf"{이름}(?:\.md)?[`\s]*"                      # MASTER · `MASTER.md`
    rf"|\]\([^)]*\)[`\s]*"                        # [docs/MASTER.md](...) 뒤
    rf"|§\s*\d+(?:-\d+[a-z]?)?\s*[·,]\s*"         # `§98 · ` 사슬
    r")$")
# 되돌아볼 길이. 줄바꿈으로 끊긴 사슬(`(DECISIONS §58 ·\n§61)`)도 잡으려고 줄을 이어 본다.
되돌이 = 90

# 이 파일과 규칙 번호를 시험하는 파일의 예시 문자열은 참조가 아니다. **목록으로 못 박는다.**
맨절밖 = {
    "tools/check_prose.py",
    "tools/check_rules.py",          # 합성 문서로 규칙 번호를 시험한다
    "tests/test_rules.py",
    "tests/test_prose.py",
}


def _자기번호(글: str) -> set[str]:
    """그 문서가 스스로 가진 절 번호. `## 7.` · `### 7-4.` 의 머리 숫자만 센다."""
    return {m.group(1).split("-")[0] for m in re.finditer(r"^#{2,4} (\d+(?:-\d+[a-z]?)*)\.\s", 글, re.M)}


def _DECISIONS번호(root: Path) -> set[str]:
    글 = (root / "docs/DECISIONS.md").read_text(encoding="utf-8")
    return {m.group(1) for m in re.finditer(r"^## §(\d+)\.", 글, re.M)}


def 맨절(글: str, 아는번호: set[str]) -> list[tuple[int, str]]:
    """(줄번호, 번호). 붙은 참조와 규칙 번호는 뺀다. 빈 리스트가 통과다."""
    난것 = []
    줄들 = 글.splitlines()
    for i, 줄 in enumerate(줄들, 1):
        앞줄 = 줄들[i - 2] if i >= 2 else ""
        이은 = (앞줄 + " " + 줄)
        밀림 = len(앞줄) + 1
        for m in 절참조.finditer(줄):
            앞 = 이은[:m.start() + 밀림].rstrip()
            if 붙은앞.search(앞[-되돌이:]):
                continue
            if m.group(1) not in 아는번호:
                난것.append((i, m.group(1)))
    return 난것


def check_맨절(root: Path) -> list[str]:
    dec = _DECISIONS번호(root)
    자기 = {}
    for rel in 문서들:
        자기[rel] = _자기번호((root / rel).read_text(encoding="utf-8")) | dec
    fails = []
    for p in _대상(root):
        rel = p.relative_to(root).as_posix()
        if rel in 맨절밖:
            continue
        try:
            글 = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            print(f"    ※ {rel} 를 못 읽었다 — {e}. **이 파일은 안 봤다**", file=sys.stderr)
            continue
        # ★ **다른 저장소에서 복사해 온 파일은 그 저장소의 참조를 든다**(DECISIONS §5).
        #   머리 세 줄에 `사본이다` 를 적은 파일은 보지 않는다 — 여기서 고치면 원본과 갈린다.
        #   `check_docs.check_refs` 와 같은 규칙이다.
        if "사본이다" in "\n".join(글.splitlines()[:3]):
            continue
        아는 = 자기.get(rel, dec)
        어디 = "그 문서에도 DECISIONS 에도" if rel in 자기 else "DECISIONS 에"
        for n, 번호 in 맨절(글, 아는):
            fails.append(f"{rel}:{n} 맨 `§{번호}` — {어디} 없는 번호다. "
                         f"문서명을 붙여 적는다(`DECISIONS §{번호}` 꼴)")
    return fails


# ── 2. 표 깨짐 ──────────────────────────────────────────────────────────────
표줄 = re.compile(r"^\s*\|.*\|\s*$")


def 표깨짐(글: str) -> list[int]:
    """빈 줄 바로 뒤에 선 표줄인데 **다음 줄이 구분줄이 아닌** 자리."""
    줄 = 글.splitlines()
    울 = False
    난것 = []
    for i, x in enumerate(줄):
        if x.lstrip().startswith("```"):
            울 = not 울
            continue
        if 울 or not 표줄.match(x):
            continue
        앞 = 줄[i - 1].strip() if i >= 1 else ""
        뒤 = 줄[i + 1] if i + 1 < len(줄) else ""
        # 머리줄이면 다음이 `|---|` 구분줄이다. 그러면 새 표가 선 것이고 맞다.
        if 앞 == "" and not re.match(r"^\s*\|[\s:|-]+\|\s*$", 뒤):
            난것.append(i + 1)
    return 난것


def check_표깨짐(root: Path) -> list[str]:
    fails = []
    for p in sorted((root / "docs").rglob("*.md")) + [root / "README.md"]:
        for n in 표깨짐(p.read_text(encoding="utf-8")):
            fails.append(f"{p.relative_to(root)}:{n} 표 줄이 빈 줄 뒤에 홀로 섰다 — "
                         f"렌더링하면 표로 안 그려진다. 윗 표에 붙이거나 머리줄을 둔다")
    return fails


# ── 3. 명령의 정본 ─────────────────────────────────────────────────────────
# ★ 「명령의 정본은 … 하나다」 꼴의 선언. 어느 절을 가리키는지 걷는다.
정본선언 = re.compile(r"명령의 정본은\s*(?:`?[\w./]*`?\s*)?(?:MASTER\s*)?§\s*(\d+)\s*하나다|"
                      r"명령의 정본은 이 절 하나다")
# 그 절 안에 사는 `tools/…` 명령 줄. 울 안만 본다 — 산문의 언급은 목록이 아니다.
명령줄 = re.compile(r"^\s*(?:bash|python3|uv run)\s+.*\btools/[\w/]+\.(?:py|sh)\b")


def _절블록(글: str) -> dict[str, str]:
    """`## N. 제목` 으로 가른 (절 번호 → 본문)."""
    것, 이름, 쌓 = {}, None, []
    for 줄 in 글.splitlines(True):
        if m := re.match(r"^## (\d+)\. ", 줄):
            if 이름:
                것[이름] = "".join(쌓)
            이름, 쌓 = m.group(1), []
            continue
        if 이름:
            쌓.append(줄)
    if 이름:
        것[이름] = "".join(쌓)
    return 것


def 선언된정본(root: Path) -> dict[str, str]:
    """(그 선언이 있는 자리 → 가리키는 MASTER 절 번호)."""
    것 = {}
    for rel in ("docs/MASTER.md", "docs/README.md", "README.md", "docs/PLAN.md"):
        p = root / rel
        if not p.exists():
            continue
        글 = p.read_text(encoding="utf-8")
        절 = _절블록(글) if rel.endswith("MASTER.md") else {}
        for i, 줄 in enumerate(글.splitlines(), 1):
            if not 정본선언.search(줄):
                continue
            m = 정본선언.search(줄)
            if m.group(1):
                것[f"{rel}:{i}"] = m.group(1)
            else:
                # 「이 절 하나다」 — 그 줄이 어느 절에 있는지 찾는다
                것[f"{rel}:{i}"] = next(
                    (n for n, 몸 in 절.items() if 줄 in 몸), "?")
    return 것


def 울밖명령(글: str) -> list[int]:
    """```bash 울 **안**의 `tools/…` 명령 줄 번호."""
    난것, 울 = [], False
    for i, 줄 in enumerate(글.splitlines(), 1):
        if 줄.lstrip().startswith("```"):
            울 = not 울
            continue
        if 울 and 명령줄.match(줄):
            난것.append(i)
    return 난것


def check_정본하나(root: Path) -> list[str]:
    fails = []
    선언 = 선언된정본(root)
    가리킨 = sorted(set(선언.values()))
    if len(가리킨) > 1:
        fails.append("「명령의 정본」 선언이 서로 다른 절을 가리킨다 — "
                     + " · ".join(f"{자리} → §{n}" for 자리, n in sorted(선언.items()))
                     + "\n        「정본이 하나다」 를 두 곳에 적으면 정본이 둘이 된다")
    if not 가리킨:
        fails.append("「명령의 정본은 … 하나다」 선언이 아무 데도 없다 — "
                     "목록이 어디 사는지 아무도 모른다")
        return fails
    정본 = 가리킨[0]
    # ★ **줄 수가 아니라 서로 다른 도구 수로 가른다.** 「목록」 과 「그 절이 설명하는 명령」 은
    #   다르다 — §12 는 `sweep.py` 를 두 줄 쓰지만 그 절의 주제가 그것이고, §11 은 `lake.py` ·
    #   `check_catalog.py` 둘로 데이터 관리를 설명한다. 줄 수로 재면 그 둘이 걸리고,
    #   **맞는 상태를 위반으로 잡는 검사는 끄는 쪽부터 찾게 된다**(thoth DECISIONS §46).
    # ★ 2026-10-03 실측 — 걷어낸 §0 블록이 **서로 다른 도구 17**, 남은 셋이 §0 1 · §5 1 ·
    #   §11 2 · §12 1 이다. 분포가 **17 과 2 사이에서 비어 있다.** 문턱 셋은 그 빈 자리에 둔다.
    #   한 절이 도구 셋 이상을 늘어놓으면 **그 절이 무엇을 설명하는지 명령으로는 못 읽는다** —
    #   그것이 목록이다.
    문턱 = 3
    for 번호, 몸 in _절블록((root / "docs/MASTER.md").read_text(encoding="utf-8")).items():
        if 번호 == 정본:
            continue
        줄들 = 몸.splitlines()
        것 = {m.group(1) for x in 울밖명령(몸)
              if (m := re.search(r"\b(tools/[\w/]+\.(?:py|sh))\b", 줄들[x - 1]))}
        if len(것) >= 문턱:
            fails.append(f"MASTER §{번호} 가 서로 다른 도구 {len(것)}개의 명령을 늘어놓는다 — "
                         f"정본은 §{정본} 이다. 여기서는 §{정본} 을 가리킨다\n"
                         f"        {' · '.join(sorted(것))}")
    return fails


# ── 4. 낱말 사전 ───────────────────────────────────────────────────────────
#
# ★ **사전이 장식이 되는 길은 둘이다**(DECISIONS §284). ① 표가 사라진다 ② 표에만 있고
#   아무도 안 쓰는 낱말이 는다. 둘째가 더 나쁘다 — **죽은 낱말이 섞이면 표 전체를 못 믿는다.**
# ★ 밖 — **「자주 쓰는데 표에 없는 말」 은 못 잡는다.** 어느 한국어가 이 저장소의 지어낸
#   말인지 기계가 모른다. 그쪽은 사람이 본다(`PLAN #50`) — **못 재는 것을 잰다고 적지 않는다.**
낱말머리 = "### 0-0. 낱말"
낱말줄 = re.compile(r"^\| \*\*([가-힣]+)\*\* \|")
#: 표에 오른 낱말이 본문에서 몇 번은 보여야 하나. 지금 가장 적은 것이 `판본` 13 이다.
낱말최소 = 5


def 사전(글: str) -> list[str]:
    """MASTER §0 의 낱말 표에 오른 낱말."""
    if 낱말머리 not in 글:
        return []
    몸 = 글[글.index(낱말머리):]
    끝 = 몸.find("\n## ")
    몸 = 몸[:끝] if 끝 > 0 else 몸
    return [m.group(1) for 줄 in 몸.splitlines() if (m := 낱말줄.match(줄))]


def check_낱말(root: Path) -> list[str]:
    master = (root / "docs/MASTER.md").read_text(encoding="utf-8")
    것 = 사전(master)
    if not 것:
        return [f"docs/MASTER.md 에 `{낱말머리}` 표가 없다 — "
                f"이 저장소의 말이 어디에도 정의돼 있지 않게 된다(DECISIONS §284)"]
    # 표 자신은 빼고 센다. 표 안의 등장은 「쓴 것」 이 아니라 「적은 것」 이다.
    자리 = master.index(낱말머리)
    표끝 = master.find("\n## ", 자리)
    표몸 = master[자리:표끝 if 표끝 > 0 else len(master)]
    셈 = {w: 0 for w in 것}
    for p in _대상(root):
        try:
            글 = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            # ★ **건너뛰되 말을 한다**(DECISIONS §255). 조용히 넘기면 **고장이 자국을
            #   안 남기고**, 그러면 이 검사의 초록이 「깨끗하다」 인지 「안 봤다」 인지 모른다.
            print(f"    ※ {p} 를 못 읽었다 — {e}. **이 파일은 안 봤다**", file=sys.stderr)
            continue
        if p.name == "MASTER.md":
            글 = 글.replace(표몸, "")
        for w in 것:
            셈[w] += 글.count(w)
    죽은 = [f"{w}({셈[w]})" for w in 것 if 셈[w] < 낱말최소]
    if 죽은:
        return [f"사전에 올랐는데 본문에서 {낱말최소}번도 안 쓰이는 낱말 — {' · '.join(죽은)}\n"
                f"        **죽은 낱말이 섞이면 표 전체를 못 믿는다.** 쓰거나 표에서 뺀다"]
    return []


# ── 5. 날짜가 든 줄 ────────────────────────────────────────────────────────
#
# ★ **MASTER 는 「지금」 이고 DECISIONS 는 「그때」 다**(DECISIONS §9). 그런데 MASTER 에
#   날짜가 드는 것 자체는 옳다 — §0-1 이 **「근거의 분모를 든다」** 를 요구한다. 「2026-09-29
#   재니 0.94 tok/s」 는 경위가 아니라 **실측의 조건**이다.
# ★ 그래서 무는 것은 **날짜가 아니라 「날짜를 적고 그 경위가 어디 사는지는 안 적은 것」** 이다.
#   그 줄만 보면 「언제 왜 그랬나」 가 MASTER 에 고이고, **그것이 DECISIONS 의 일이다.**
# ★ 2026-10-03 실측 — 날짜가 든 줄 **스물 중 열아홉이 이미 절을 가리키고 있었다.** 감사 §7 의
#   「과거 서술이 대량으로 통과한다」 는 **재 보니 과장이었다.** 그래서 고친 것은 한 줄이고,
#   관문은 **churn 0** 으로 선다. 세기 전에 고치기 시작했으면 열아홉을 헛되이 건드렸다.
# ★ 밖 — **서술이 과거인지는 안 본다.** 「라쳇을 걸었다」 가 경위인지 지금 상태인지는 글의
#   뜻이고 기계가 못 가른다. 여기가 드는 것은 **날짜 옆에 가리킨 자리가 있는가** 하나다.
날짜든줄 = re.compile(r"20\d\d-\d\d-\d\d")
가리킴 = re.compile(r"§\s*\d+|DECISIONS|H-\d+|PLAN #\d+")


def 날짜만있는줄(글: str) -> list[int]:
    """날짜를 적고 **어디에 그 경위가 사는지는 안 적은** 줄. 울 안은 안 본다."""
    줄 = 글.splitlines()
    울, 난것 = False, []
    for i, l in enumerate(줄, 1):
        if l.lstrip().startswith("```"):
            울 = not 울
            continue
        if 울 or not 날짜든줄.search(l):
            continue
        # ★ 줄바꿈으로 흩어진 참조까지 본다 — 한 문장이 세 줄에 걸치는 문서다.
        창 = " ".join(줄[max(0, i - 3):i + 2])
        if not 가리킴.search(창):
            난것.append(i)
    return 난것


def check_날짜(root: Path) -> list[str]:
    글 = (root / "docs/MASTER.md").read_text(encoding="utf-8")
    return [f"docs/MASTER.md:{n} 날짜를 적고 **그 경위가 어디 사는지**는 안 적었다 — "
            f"`(DECISIONS §N)` 을 단다. MASTER 는 「지금」 이다"
            for n in 날짜만있는줄(글)]


# ── 6. CI 에서 다르게 도는 단계 ────────────────────────────────────────────
#
# ★ **CI 가 안 보는 단계는 선언돼 있어야 한다**(파이어레인 `tools/gate_parity.py` ·
#   DECISIONS §285). `verify.sh` 는 세 단계를 CI 에서 다르게 돌린다 — `훅` · `lake` · `ci`.
#   MASTER §5 가 그것을 적는데, **2026-10-03 까지 셋 중 둘만** 들고 있었다.
# ★ **같은 병이 같은 자리에서 세 번째다.** §199 가 「목록을 두 곳에 적으면 한쪽만 는다」 를
#   배웠고, §281 이 「§5 가 열하나를 적는 동안 실물이 스물셋이 됐다」 를 배웠고, 그 고침이
#   **목록을 지우고 「CI 밖인 것만 적는다」 로 줄였는데 그 줄인 목록이 또 빠뜨렸다.**
#   **목록을 줄이는 것은 목록을 없애는 것이 아니다** — 남은 목록에도 강제자가 있어야 한다.
# ★ 밖 — **그 단계가 CI 에서 왜 다른지는 안 본다.** 까닭은 `verify.sh` 가 그 자리에서 적고
#   `tests/test_workflows.py::test_CI_에서_안_도는_단계는_까닭을_적는다` 가 든다.
CI밖선언 = re.compile(r'NAMES\+=\("([^"$]+)"\)')


def CI밖(글: str) -> list[str]:
    """`verify.sh` 가 CI 에서 다르게 돌린다고 선언한 단계 이름."""
    return [m.group(1) for m in CI밖선언.finditer(글)]


def check_CI밖(root: Path) -> list[str]:
    선언 = set(CI밖((root / "tools/verify.sh").read_text(encoding="utf-8")))
    master = (root / "docs/MASTER.md").read_text(encoding="utf-8")
    i = master.find("## 5. ")
    절 = master[i:master.find("\n## 6. ", i)] if i >= 0 else ""
    if not 절:
        return ["docs/MASTER.md 에 `## 5.` 절이 없다 — 점검을 적는 자리가 사라졌다"]
    빠진 = sorted(n for n in 선언 if f"`{n}`" not in 절)
    if 빠진:
        return [f"MASTER §5 가 CI 에서 다르게 도는 단계를 빠뜨렸다 — {' · '.join(빠진)}\n"
                f"        `verify.sh` 가 {len(선언)}개를 선언하는데 절은 "
                f"{len(선언) - len(빠진)}개만 든다. **목록을 줄이는 것은 없애는 것이 아니다**"]
    return []


# ── 7. 빈 약속 ─────────────────────────────────────────────────────────────
# ★ **낱말을 좁게 잡는다.** 「아직」 은 평범한 부사라서 넓게 잡으면 멀쩡한 서술이 걸린다.
#   잡는 것은 **상태를 미완으로 선언하는 꼴**이다.
약속 = re.compile(r"(열려 있다|채우지 않았다|채우지 못했다|아직 안 |아직 없다|비어 있다\.)")
행참조 = re.compile(r"PLAN #\d+|#\d+ (?:이|가) 그 자리")


def 빈약속(글: str) -> list[tuple[int, str]]:
    난것 = []
    울 = False
    for i, 줄 in enumerate(글.splitlines(), 1):
        if 줄.lstrip().startswith("```"):
            울 = not 울
            continue
        if 울:
            continue
        m = 약속.search(줄)
        if m and not 행참조.search(줄):
            난것.append((i, m.group(1)))
    return 난것


def check_빈약속(root: Path) -> list[str]:
    글 = (root / "docs/MASTER.md").read_text(encoding="utf-8")
    return [f"docs/MASTER.md:{n} 「{말}」 를 적고 `PLAN #N` 을 안 붙였다 — "
            f"행이 없는 약속은 약속이 아니다"
            for n, 말 in 빈약속(글)]


def _대상(root: Path) -> list[Path]:
    out = [root / "README.md"]
    for d in 볼디렉터리:
        base = root / d
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if (p.is_file() and p.suffix in 볼확장
                    and not {"__pycache__", "node_modules", ".cache"} & set(p.parts)):
                out.append(p)
    return out


def _canary() -> None:
    """정규식이 살아 있는가. **양성 대조다.** 죽었으면 2 로 끝난다 — 위반(1)과 가른다."""
    probes = {
        "맨절 — 붙은 것은 안 본다": 맨절("보라 DECISIONS §9 와 MASTER §7 을", {"9", "7"}) == [],
        "맨절 — 맨 것을 본다": 맨절("보라 §999 를", {"9"}) == [(1, "999")],
        "맨절 — 아는 번호는 통과": 맨절("보라 §9 를", {"9"}) == [],
        "맨절 — 사슬 뒤쪽도 붙은 것이다": 맨절("(DECISIONS §98 · §110)", {"98", "110"}) == [],
        "맨절 — 줄바꿈으로 끊긴 사슬": 맨절("(DECISIONS §58 ·\n§61) 탐침", {"58", "61"}) == [],
        "맨절 — 백틱 문서명": 맨절("thoth `docs/MASTER.md` §7-4 다", {"7"}) == [],
        "맨절 — 마크다운 링크": 맨절("[PLAN](docs/PLAN.md) §0 부터", {"0"}) == [],
        "맨절 — 규칙 번호는 밖이다": 맨절("★ §11-3 **결과 파일**", set()) == [],
        "표깨짐 — 붙은 표는 통과": 표깨짐("| a | b |\n|---|---|\n| 1 | 2 |\n") == [],
        "표깨짐 — 떨어진 줄을 잡는다": 표깨짐("| a | b |\n|---|---|\n| 1 | 2 |\n\n| 3 | 4 |\n") == [5],
        "표깨짐 — 새 표의 머리줄은 통과": 표깨짐("글\n\n| a | b |\n|---|---|\n| 1 | 2 |\n") == [],
        "표깨짐 — 울 안은 안 본다": 표깨짐("```\n\n| a | b |\n```\n") == [],
        "정본 — 「이 절」 꼴을 읽는다": bool(정본선언.search("**명령의 정본은 이 절 하나다**(DECISIONS §199).")),
        "정본 — 절 번호 꼴을 읽는다": (정본선언.search("명령의 정본은 `now/MASTER.md` §14 하나다.").group(1) == "14"),
        "정본 — 아무 문장이나 안 읽는다": not 정본선언.search("명령을 여기 적지 않는다"),
        "울안명령 — 울 안만 센다": 울밖명령("```bash\npython3 tools/x.py\n```\n산문의 `tools/y.py`\n") == [2],
        "빈약속 — 행이 있으면 통과": 빈약속("이 항목은 열려 있고 PLAN #47 가 그 자리다\n") == [],
        "빈약속 — 행이 없으면 잡는다": 빈약속("이 항목은 열려 있다.\n") == [(1, "열려 있다")],
    }
    죽은 = [k for k, ok in probes.items() if not ok]
    if 죽은:
        print(f"    ★ 카나리아가 죽었다 — {죽은}. 검사가 아무것도 못 찾는 상태다")
        sys.exit(2)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    _canary()
    if "--list" in args:
        print(__doc__)
        return 0
    fails = (check_맨절(ROOT) + check_표깨짐(ROOT)
             + check_정본하나(ROOT) + check_낱말(ROOT)
             + check_날짜(ROOT)
             + check_CI밖(ROOT) + check_빈약속(ROOT))
    for f in fails:
        print(f"    {f}")
    if not fails:
        print("  맨 절 참조가 전부 풀린다 · 떨어진 표 줄 없음 · 명령의 정본이 한 곳"
              " · 사전에 죽은 낱말 없음 · 날짜마다 가리킨 자리 있음"
              " · CI 밖이 전부 적혔다 · 빈 약속 없음")
    return 1 if fails else 0


if __name__ == "__main__":
    # ★ 위반(1)과 도구 고장(2)을 다른 코드로 끝낸다(DECISIONS §21 · §232). 같은 코드면
    #   **도구가 깨진 것을 문서가 틀린 것으로 읽는다**
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
