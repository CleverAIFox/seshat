"""`tools/check_prose.py` 의 세 규칙이 살아 있는가(DECISIONS §282).

★ 이 파일은 **seshat 것**이다 — thoth 사본이 아니다(DECISIONS §5).
★ **양성과 음성을 함께 본다.** 「잡는다」 만 보면 **전부 잡는 규칙**도 통과한다 — 그러면
  규칙을 켜는 날 멀쩡한 문장이 다 걸리고, 그때 사람은 고치는 대신 **끈다**(thoth §46).
★ 규칙을 하나씩 들어내 **셋 전부 빨개지는 것**을 봤다 — 통과만 보는 검사는 검사가 아니다
  (DECISIONS §265).
"""
from __future__ import annotations

import importlib.util
import pathlib

ROOT = next(p for p in pathlib.Path(__file__).resolve().parents if (p / "tools/check_prose.py").exists())
_spec = importlib.util.spec_from_file_location("cp", ROOT / "tools/check_prose.py")
CP = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CP)

NL = chr(10)
NL2 = NL + NL


# ---------- 1. 맨 §N ----------

def test_없는_번호를_잡는다():
    assert CP.맨절("보라 §999 를", {"9"}) == [(1, "999")]


def test_아는_번호는_통과한다():
    """★ **이것이 음성 대조다.** 맨 `§N` 을 **금지하지 않는다** — 코드 주석 600 곳이 그 문체다."""
    assert CP.맨절("재표집으로 본다(§180)", {"180"}) == []


def test_문서명이_붙으면_그_문서로_읽는다():
    assert CP.맨절("DECISIONS §9 와 MASTER §7", {"9", "7"}) == []


def test_사슬의_뒤쪽도_붙은_참조다():
    """`DECISIONS §98 · §110` 의 뒤쪽은 이름 없이 온다. 앞만 보면 뒤쪽이 검사 밖이다."""
    assert CP.맨절("(DECISIONS §98 · §110)", {"98", "110"}) == []


def test_줄바꿈으로_끊긴_사슬도_붙은_참조다():
    """★ MASTER 에 실제로 그런 자리가 있다 — `(DECISIONS §58 ·` 에서 줄이 바뀌고 `§61)` 로 이어진다."""
    assert CP.맨절("탐침 200 줄에서(DECISIONS §58 ·\n§61) 재니", {"58", "61"}) == []


def test_백틱_문서명도_붙은_참조다():
    assert CP.맨절("정본은 thoth `docs/MASTER.md` §7-4 다", {"7"}) == []


def test_마크다운_링크_뒤도_붙은_참조다():
    assert CP.맨절("[PLAN](docs/PLAN.md) §0 부터 읽는다", {"0"}) == []


def test_규칙_번호는_이_검사의_밖이다():
    """★ 밖 — `§11-3` 은 절이 아니라 **절 안의 규칙 번호**이고 `check_rules` 가 본다(DECISIONS §230)."""
    assert CP.맨절("★ §11-3 **결과 파일의 이름은**", set()) == []


def test_저장소가_지금_통과한다():
    """★ 검사를 넣는 날 이미 깨져 있으면 아무도 고치지 않고 꺼 버린다(thoth §46)."""
    assert CP.check_맨절(ROOT) == []


# ---------- 2. 표 깨짐 ----------

표 = "| a | b |\n|---|---|\n| 1 | 2 |\n"


def test_붙은_표는_통과한다():
    assert CP.표깨짐(표) == []


def test_빈_줄_뒤에_떨어진_줄을_잡는다():
    assert CP.표깨짐(표 + "\n| 3 | 4 |\n") == [5]


def test_새_표의_머리줄은_통과한다():
    """머리줄 다음이 `|---|` 면 새 표가 선 것이고 맞다."""
    assert CP.표깨짐("글\n\n" + 표) == []


def test_울_안의_표는_안_본다():
    assert CP.표깨짐("```\n\n| a | b |\n```\n") == []


def test_문서에_떨어진_표_줄이_없다():
    assert CP.check_표깨짐(ROOT) == []


# ---------- 3. 명령의 정본 ----------

def test_이_절_꼴의_선언을_읽는다():
    assert CP.정본선언.search("**명령의 정본은 이 절 하나다**(DECISIONS §199).")


def test_절_번호_꼴의_선언을_읽는다():
    assert CP.정본선언.search("명령의 정본은 `now/MASTER.md` §14 하나다.").group(1) == "14"


def test_아무_문장이나_선언으로_안_읽는다():
    """★ **음성 대조다.** 넓게 잡으면 「명령을 여기 적지 않는다」 같은 줄이 선언이 되고,
    그러면 선언이 저절로 늘어 「정본이 둘」 이 거짓으로 뜬다."""
    assert not CP.정본선언.search("명령을 여기 적지 않는다")
    assert not CP.정본선언.search("정본은 verify.sh 하나다")


def test_울_안의_명령만_센다():
    """★ 산문이 `tools/y.py` 를 언급하는 것은 「목록에 있다」 가 아니다."""
    assert CP.울밖명령("```bash\npython3 tools/x.py\n```\n산문의 `tools/y.py`\n") == [2]


def test_저장소의_정본이_한_곳이다():
    assert CP.check_정본하나(ROOT) == []


def _나무(tmp_path, master, readme):
    """합성 저장소 하나. **셋을 따로 쓰면 그 셋이 매번 조금씩 달라진다.**"""
    (tmp_path / "docs/now").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs/why").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs/MASTER.md").write_text(master, encoding="utf-8")
    (tmp_path / "docs/README.md").write_text(readme, encoding="utf-8")
    (tmp_path / "docs/DECISIONS.md").write_text("## §1. x" + NL, encoding="utf-8")
    return tmp_path


M14 = "## 0. 규약" + NL2 + "## 14. 도구" + NL2 + "**명령의 정본은 이 절 하나다**" + NL
R14 = "★ **명령의 정본은 `now/MASTER.md` §14 하나다.**" + NL
R0 = "★ **명령의 정본은 `now/MASTER.md` §0 하나다.**" + NL


def test_선언이_둘로_갈리면_잡는다(tmp_path):
    """★ **이것이 2026-10-03 의 실물이다**(DECISIONS §283).

    `docs/README.md` 가 `MASTER §0` 을, `MASTER §14` 가 「이 절」 을 정본으로 선언하고 있었다.
    **「정본이 하나다」 를 두 곳에 적으면 정본이 둘이 된다.**
    """
    난 = CP.check_정본하나(_나무(tmp_path, M14, R0))
    assert 난 and "서로 다른 절" in 난[0], 난


def test_한_절을_함께_가리키면_통과한다(tmp_path):
    assert CP.check_정본하나(_나무(tmp_path, M14, R14)) == []


def test_도구_둘까지는_목록이_아니다(tmp_path):
    """★ **줄 수가 아니라 서로 다른 도구 수로 가른다**(DECISIONS §283).

    §12 가 `sweep.py` 를 두 줄 쓰는 것은 **그 절이 설명하는 명령**이고 목록이 아니다.
    맞는 상태를 위반으로 잡는 검사는 **끄는 쪽부터 찾게 된다**(thoth DECISIONS §46).
    """
    울 = "```bash"
    둘 = NL.join(["## 12. 위생", "", 울, "python3 tools/sweep.py",
                 "python3 tools/sweep.py --fix", 울, "", ""])
    assert CP.check_정본하나(_나무(tmp_path, 둘 + M14, R14)) == []


def test_도구_셋이면_목록이다(tmp_path):
    울 = "```bash"
    셋 = NL.join(["## 12. 위생", "", 울, "python3 tools/sweep.py",
                 "python3 tools/lake.py check", "bash tools/verify.sh", 울, "", ""])
    난 = CP.check_정본하나(_나무(tmp_path, 셋 + M14, R14))
    assert 난 and "서로 다른 도구 3" in 난[0], 난


# ---------- 4. 낱말 사전 ----------

def test_표에서_낱말을_걷는다():
    글 = NL.join(["### 0-0. 낱말", "", "| 낱말 | 뜻 | 헷갈리는 자리 |", "|---|---|---|",
                 "| **자** | 재는 것 | 조사와 같다 |", "| **셋** | 줄 묶음 | 수 3 과 같다 |",
                 "", "## 1. 다음 절", "", "| **팔** | 여기는 표 밖이다 |"])
    assert CP.사전(글) == ["자", "셋"], CP.사전(글)


def test_표가_없으면_빈_목록이다():
    assert CP.사전("## 0. 규약" + NL) == []


def test_저장소의_사전이_살아_있다():
    assert CP.check_낱말(ROOT) == []


def test_표가_사라지면_잡는다(tmp_path):
    """★ **사전이 장식이 되는 길 ①** — 표가 통째로 없어진다."""
    (tmp_path / "docs/now").mkdir(parents=True)
    (tmp_path / "docs/MASTER.md").write_text("## 0. 규약" + NL, encoding="utf-8")
    난 = CP.check_낱말(tmp_path)
    assert 난 and "표가 없다" in 난[0], 난


def test_안_쓰이는_낱말을_잡는다(tmp_path):
    """★ **사전이 장식이 되는 길 ②** — 표에만 있고 아무도 안 쓰는 말이 는다.

    둘째가 더 나쁘다. **죽은 낱말이 섞이면 표 전체를 못 믿는다.**
    """
    (tmp_path / "docs/now").mkdir(parents=True)
    (tmp_path / "docs/MASTER.md").write_text(
        NL.join(["## 0. 규약", "", "### 0-0. 낱말", "", "| 낱말 | 뜻 | 헷갈리는 자리 |",
                 "|---|---|---|", "| **쇠지렛대** | 아무도 안 쓴다 | — |", ""]), encoding="utf-8")
    난 = CP.check_낱말(tmp_path)
    assert 난 and "쇠지렛대(0)" in 난[0], 난


def test_표_안의_등장은_안_센다(tmp_path):
    """★ **적은 것과 쓴 것은 다르다.** 표 자신을 세면 어떤 낱말도 영원히 안 죽는다 —
    그러면 이 검사가 **아무것도 안 하는 검사**가 된다(DECISIONS §21)."""
    (tmp_path / "docs/now").mkdir(parents=True)
    몸 = NL.join(["## 0. 규약", "", "### 0-0. 낱말", "", "| 낱말 | 뜻 | 헷갈리는 자리 |", "|---|---|---|"]
                + ["| **쇠지렛대** | 쇠지렛대 쇠지렛대 쇠지렛대 쇠지렛대 쇠지렛대 | — |", ""])
    (tmp_path / "docs/MASTER.md").write_text(몸, encoding="utf-8")
    난 = CP.check_낱말(tmp_path)
    assert 난, "표 안의 여섯 번을 본문 사용으로 셌다"


# ---------- 5. 날짜가 든 줄 ----------

def test_가리킨_자리가_없는_날짜를_잡는다():
    assert CP.날짜만있는줄("2026-09-29 그렇게 됐다" + NL) == [1]


def test_절을_가리키면_통과한다():
    """★ **음성 대조다.** 날짜 자체를 금지하면 `MASTER §0-1` 이 요구하는
    「근거의 분모」 를 못 적는다 — 「2026-09-29 재니 0.94 tok/s」 는 경위가 아니라 **실측의 조건**이다."""
    assert CP.날짜만있는줄("2026-09-29 재니 0.94 tok/s 였다(DECISIONS §55)" + NL) == []
    assert CP.날짜만있는줄("2026-09-29 H-032 로 쟀다" + NL) == []


def test_줄바꿈으로_흩어진_참조도_본다():
    """★ 한 문장이 세 줄에 걸치는 문서다. 한 줄만 보면 **멀쩡한 글이 걸린다.**"""
    글 = NL.join(["2026-09-29 그렇게 됐다", "— 자세한 것은 DECISIONS §55 에 있다", ""])
    assert CP.날짜만있는줄(글) == []


def test_울_안의_날짜는_안_본다():
    assert CP.날짜만있는줄(NL.join(["```bash", "# 2026-09-29", "```", ""])) == []


def test_MASTER_의_날짜가_전부_자리를_가리킨다():
    """★ 2026-10-03 실측 — 날짜가 든 줄 **스물 중 열아홉이 이미 가리키고 있었다.**
    감사 §7 의 「과거 서술이 대량으로 통과한다」 는 재 보니 과장이었고, 고친 것은 한 줄이다.
    **세기 전에 고치기 시작했으면 열아홉을 헛되이 건드렸다.**"""
    assert CP.check_날짜(ROOT) == []


# ---------- 6. CI 에서 다르게 도는 단계 ----------

def test_verify_의_선언을_걷는다():
    글 = NL.join(['if [ "$CI" = "true" ]; then NAMES+=("훅"); MARKS+=("CI 밖")',
                 '  NAMES+=("$name"); MARKS+=("통과")',
                 'NAMES+=("lake")', ""])
    assert CP.CI밖(글) == ["훅", "lake"], CP.CI밖(글)


def test_변수_이름은_단계가_아니다():
    """★ `NAMES+=("$name")` 은 **모든** 단계가 지나는 자리다 — 그것을 세면 선언이 늘 맞는다."""
    assert CP.CI밖('NAMES+=("$name")' + NL) == []


def test_MASTER_가_셋을_다_든다():
    assert CP.check_CI밖(ROOT) == []


def test_하나라도_빠지면_잡는다(tmp_path):
    """★ **같은 병이 같은 자리에서 세 번째다**(DECISIONS §285).

    §199 가 「목록을 두 곳에 적으면 한쪽만 는다」 를, §281 이 「§5 가 열하나를 적는 동안
    실물이 스물셋이 됐다」 를 배웠다. 그 고침이 목록을 **줄였는데** 줄인 목록이 또 빠뜨렸다 —
    **목록을 줄이는 것은 없애는 것이 아니다.**
    """
    (tmp_path / "docs/now").mkdir(parents=True)
    (tmp_path / "tools").mkdir(parents=True)
    (tmp_path / "tools/verify.sh").write_text(
        NL.join(['NAMES+=("훅")', 'NAMES+=("lake")', 'NAMES+=("ci")', ""]), encoding="utf-8")
    (tmp_path / "docs/MASTER.md").write_text(
        NL.join(["## 5. 점검", "", "CI 밖은 `훅` · `lake` 다.", "", "## 6. 다음", ""]),
        encoding="utf-8")
    난 = CP.check_CI밖(tmp_path)
    assert 난 and "ci" in 난[0], 난


def test_셋을_다_들면_통과한다(tmp_path):
    (tmp_path / "docs/now").mkdir(parents=True)
    (tmp_path / "tools").mkdir(parents=True)
    (tmp_path / "tools/verify.sh").write_text(
        NL.join(['NAMES+=("훅")', 'NAMES+=("lake")', ""]), encoding="utf-8")
    (tmp_path / "docs/MASTER.md").write_text(
        NL.join(["## 5. 점검", "", "CI 밖은 `훅` · `lake` 다.", "", "## 6. 다음", ""]),
        encoding="utf-8")
    assert CP.check_CI밖(tmp_path) == []


# ---------- 4. 빈 약속 ----------

def test_행이_없는_약속을_잡는다():
    assert CP.빈약속("이 항목은 열려 있다.\n") == [(1, "열려 있다")]


def test_행이_있으면_통과한다():
    assert CP.빈약속("이 항목은 열려 있고 PLAN #47 이 그 자리다\n") == []


def test_울_안은_안_본다():
    assert CP.빈약속("```\n이 항목은 열려 있다.\n```\n") == []


def test_MASTER_에_빈_약속이_없다():
    assert CP.check_빈약속(ROOT) == []


# ---------- 카나리아 ----------

def test_카나리아가_살아_있다():
    """★ 0건이 목표인 검사는 0건을 성공으로만 읽으면 안 된다 — 깨끗해서인지 정규식이
    죽어서인지 가를 수 없다(DECISIONS §265). `_canary` 가 죽으면 2 로 끝난다.

    ★ **`assert` 로 적는다.** 몸통이 부름 하나면 지워도 통과하므로 그것은 검사가 아니다
      (`tools/check_deadchecks.py` · DECISIONS §255).
    """
    import pytest
    CP._canary()                     # 죽었으면 SystemExit(2)
    # 양성 대조 — 규칙 하나를 죽이면 카나리아가 **멈춰야 한다**
    원 = CP.표줄
    try:
        CP.표줄 = __import__("re").compile(r"NEVERMATCH")
        with pytest.raises(SystemExit) as 났:
            CP._canary()
        assert 났.value.code == 2, "카나리아가 죽었는데 위반(1)으로 끝났다"
    finally:
        CP.표줄 = 원
    assert CP._canary() is None      # 되돌리면 다시 조용하다
