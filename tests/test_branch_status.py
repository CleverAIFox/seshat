"""`tools/branch_status.py` — **민 가지가 PR 없이 떠 있는가**의 판정이 사는 자리(DECISIONS §315).

★ **판정을 직접 부른다.** `판정` 은 망을 안 타는 순수 함수라 **합성으로 전부 물을 수 있다** —
  `gh` 를 흉내 내는 시험은 `gh` 의 답 꼴을 시험하는 것이지 판정을 시험하는 것이 아니다.
★ **눈금을 시험한다.** 이 자의 값은 「고아를 잡는다」 만큼이나 **「승인 대기로는 안 막는다」**
  에 있다 — 매주 우는 검사는 사람이 끈다(hathor GR-0.8).
"""
from __future__ import annotations

import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _든다(이름: str):
    s = importlib.util.spec_from_file_location(이름, ROOT / "tools" / f"{이름}.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


BS = _든다("branch_status")


def 판(결론: str, 때: str = "2026-10-22T00:00:00Z", 이름: str = "ci") -> dict:
    return {"conclusion": 결론, "status": "completed", "workflowName": 이름,
            "url": "https://example.invalid/판", "createdAt": 때}


# ───────────────────────────── 판정 ─────────────────────────────

def test_PR_없는_가지는_빨강이다():
    """★ **2026-10-19 의 그 꼴이다.** 가지는 밀렸고 PR 은 없다."""
    코드, 말 = BS.판정(["main", "papers/2026-10-19"], {}, {})
    assert 코드 == 1
    assert any("papers/2026-10-19" in m for m in 말)


def test_고아의_말에_건질지_볼_명령이_든다():
    """★ **지우라고만 하면 지운다** — 10-19 가지에는 오늘 PR 에 없는 후보가 열아홉 있었다."""
    _, 말 = BS.판정(["papers/x"], {}, {})
    글 = "\n".join(말)
    assert "git diff origin/main...origin/papers/x" in 글
    assert 글.index("git diff") < 글.index("--delete"), "지우는 길이 보는 길보다 먼저 나온다"


def test_PR_이_열려_있으면_안_운다():
    assert BS.판정(["papers/x"], {"papers/x": 7}, {})[0] == 0


def test_PR_의_빨강은_막는다():
    코드, 말 = BS.판정(["papers/x"], {"papers/x": 7}, {"papers/x": [판("failure")]})
    assert 코드 == 1
    assert any("#7" in m for m in 말)


@pytest.mark.parametrize("결론", ["", "success", "skipped", "neutral"])
def test_초록으로_세는_결론은_안_막는다(결론):
    """빈 것은 **도는 중**이다 — 아직 판정이 아니다."""
    assert BS.판정(["papers/x"], {"papers/x": 7}, {"papers/x": [판(결론)]})[0] == 0


def test_승인_대기는_적되_안_막는다():
    """★ **이 자의 눈금이다**(hathor GR-0.8). 봇 PR 의 승인 대기는 **설정**이지 결함이 아니다.

    매주 울면 사람이 검사를 끄고, 꺼진 검사는 고아도 못 잡는다.
    """
    코드, 말 = BS.판정(["papers/x"], {"papers/x": 7},
                      {"papers/x": [판(BS.대기결론)]})
    assert 코드 == 0
    assert any("승인" in m for m in 말), "조용히 삼키면 셋째 반쪽이 또 앉는다"


def test_대기와_고아가_같이_있으면_막는다():
    """대기가 안 막는다고 **같은 판에 있는 고아까지 봐주면** 안 된다."""
    코드, 말 = BS.판정(["papers/a", "papers/b"], {"papers/b": 7},
                      {"papers/b": [판(BS.대기결론)]})
    assert 코드 == 1
    assert any("papers/a" in m for m in 말) and any("승인" in m for m in 말)


@pytest.mark.parametrize("가지", ["main", "feature/x", "paper/x", "papers", "dependabot/pip/x"])
def test_감시_밖의_가지는_안_본다(가지):
    """★ **넓히면 매일 운다.** 일하는 가지는 PR 없이 떠 있는 것이 정상이다."""
    assert BS.판정([가지], {}, {})[0] == 0


def test_아무것도_없으면_센_수를_적는다():
    """★ **「0건」 과 「안 봤다」 를 가른다**(DECISIONS §59)."""
    _, 말 = BS.판정(["main", "papers/x"], {"papers/x": 1}, {})
    assert "1" in "\n".join(말)


# ───────────────────────── 워크플로마다 최신 판 ─────────────────────────

def test_옛_빨강이_새_초록을_못_이긴다():
    """★ §292 가 적은 그것 — 판 하나가 저장소의 판정이 되면 안 된다."""
    둘 = [판("failure", "2026-10-20T00:00:00Z"), 판("success", "2026-10-22T00:00:00Z")]
    assert BS.판정(["papers/x"], {"papers/x": 7}, {"papers/x": 둘})[0] == 0
    assert BS.판정(["papers/x"], {"papers/x": 7}, {"papers/x": list(reversed(둘))})[0] == 0, \
        "받은 순서를 안 믿는다(§169 · §172)"


def test_워크플로가_둘이면_둘다_본다():
    """한 워크플로가 초록이라고 **다른 워크플로의 빨강이 덮이면** 안 된다."""
    둘 = [판("success", 이름="ci"), 판("failure", 이름="gitleaks")]
    assert BS.판정(["papers/x"], {"papers/x": 7}, {"papers/x": 둘})[0] == 1


def test_최신판은_워크플로마다_하나다():
    난것 = BS._최신판([판("failure", "2026-10-20T00:00:00Z", "ci"),
                     판("success", "2026-10-22T00:00:00Z", "ci"),
                     판("failure", "2026-10-21T00:00:00Z", "gitleaks")])
    assert sorted((x["workflowName"], x["conclusion"]) for x in 난것) == \
        [("ci", "success"), ("gitleaks", "failure")]


# ───────────────────────── gh 를 못 볼 때 ─────────────────────────

def test_gh_가_죽으면_글을_준다():
    """★ **못 보는 것은 통과가 아니다**(§59) — 빈 목록이 아니라 **까닭**을 돌려준다."""
    for 이름, 부른다 in (
        ("가지를_받는다", lambda a: (1, "", "HTTP 403")),
        ("PR을_받는다", lambda a: (1, "", "gh: not logged in")),
    ):
        난것 = getattr(BS, 이름)(부른다=부른다)
        assert isinstance(난것, str) and 난것, 이름


def test_답이_json_이_아니면_글을_준다():
    난것 = BS.PR을_받는다(부른다=lambda a: (0, "<html>로그인 하세요</html>", ""))
    assert isinstance(난것, str) and "못 읽었다" in 난것


def test_빈_답은_빈_표다():
    """빈 것과 깨진 것을 **가른다** — 빈 PR 목록은 정상이다."""
    assert BS.PR을_받는다(부른다=lambda a: (0, "", "")) == {}
    assert BS.판을_받는다("papers/x", 부른다=lambda a: (0, "", "")) == []


def test_PR_표는_머리가지로_맞춘다():
    답 = json.dumps([{"number": 2, "headRefName": "papers/2026-10-22"}])
    assert BS.PR을_받는다(부른다=lambda a: (0, 답, "")) == {"papers/2026-10-22": 2}


def test_열린_것만_묻는다():
    """닫힌 PR 은 **떠 있는 가지를 설명하지 않는다** — 물을 때부터 가른다."""
    본것 = []
    BS.PR을_받는다(부른다=lambda a: (본것.append(a), (0, "[]", ""))[1])
    assert "--state" in 본것[0] and "open" in 본것[0]


# ───────────────────────── 카나리아와 배선 ─────────────────────────

def test_카나리아가_산다():
    """★ **판별식이 죽으면 0건이 초록으로 보인다.** 죽으면 `SystemExit` 다."""
    assert BS._canary() is None, "카나리아는 말없이 돌아온다 — 죽으면 SystemExit 다"


def test_카나리아가_눈금을_묻는다():
    """★ **카나리아의 글에 승인 대기가 들어 있나** — 그 줄이 빠지면 눈금이 사라진다."""
    글 = (ROOT / "tools/branch_status.py").read_text(encoding="utf-8")
    assert "승인 대기로 막는다" in 글, "안 막는다를 묻는 줄이 카나리아에 있어야 한다"


def test_verify_가_부른다():
    """★ **사슬에 안 걸린 검사는 아무도 안 돌린다**(DECISIONS §170)."""
    v = (ROOT / "tools/verify.sh").read_text(encoding="utf-8")
    assert "tools/branch_status.py" in v
    assert v.index("branch_status.py") > v.index("tools/ci_status.py"), "가지 판정은 마지막에 본다"


def test_papers_가_제_끝에서_부른다():
    """★ **반쪽이 나는 자리가 거기다.** 이 기계의 `verify.sh` 와 **같은 구현**을 부른다(§57)."""
    y = (ROOT / ".github/workflows/papers.yml").read_text(encoding="utf-8")
    assert "tools/branch_status.py" in y
    assert "if: always()" in y[y.index("gh pr create"):], "위가 죽어도 도는 자리여야 뜻이 있다"
    assert "actions: read" in y, "`gh run list` 가 없으면 403 이고, 403 은 못 봄이다"


def test_PR_을_못_열면_가지를_되돌린다():
    """★ **둘은 한 거래다**(DECISIONS §315) — 뒤가 깨지면 앞을 무른다."""
    y = (ROOT / ".github/workflows/papers.yml").read_text(encoding="utf-8")
    뒤 = y[y.index("gh pr create"):]
    assert "push origin --delete" in 뒤
    assert 뒤.index("push origin --delete") < 뒤.index("if: always()")
