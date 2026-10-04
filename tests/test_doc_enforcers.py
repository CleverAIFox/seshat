# ★ **thoth 의 `worker/tests/test_doc_enforcers.py` 사본이다**(DECISIONS §5). 고칠 것이 있으면 thoth 에서 고치고
#   다시 복사한다. 이 저장소에 맞춘 차이는 `# seshat:` 표시 줄뿐이다.
"""문서 강제자의 검사(DECISIONS §111). **강제자가 죽으면 문서는 조용히 늙는다.**

★ 양성과 음성을 함께 본다. 깨끗한 합성 문서가 통과하는가, 그리고 **규칙마다 하나씩 어긴
  문서가 그 규칙으로 걸리는가.** 음성만 있으면 무엇이든 잡는 검사가, 양성만 있으면 아무것도
  못 잡는 검사가 초록이다.
"""
import importlib.util
import pathlib
import re
import subprocess

import pytest

# ★ 저장소 뿌리를 위치로 찾지 않는다. 이 파일은 seshat 에 사본으로 가고 거기서는 깊이가 다르다.
ROOT = next(p for p in pathlib.Path(__file__).resolve().parents if (p / "tools/check_docs.py").exists())


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"tools/{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cd = _load("check_docs")
fsck = _load("doc_fsck")

PLAN = """# t

## 0. 다음 한 수

#7 을 본다.

## 1. 남은 일 — 2행

| # | 상태 | 항목 | 전건 · 막고 있는 것 |
|---|---|---|---|
| 3 | 📄 | 가 | |
| 7 | ⏳ | 나 | #3 |

## 2. 범위 밖

없다.
"""


def plan_fails(text):
    f = []
    cd.check_plan(text, f)
    return f


# ---------- 카나리아 ----------

def test_카나리아가_산다():
    """★ **카나리아를 `pass` 로 바꿔도 통과하면 그 시험이 죽은 것이다**(DECISIONS §255).
    도는 것과 **판별식을 들고 있는 것**을 함께 본다."""
    import inspect
    assert cd._canary() is None            # 살아 있으면 조용히 돌아온다
    글 = inspect.getsource(cd._canary)
    assert "sys.exit(2)" in 글, "카나리아가 죽었을 때 **고장(2)으로 끝내야 한다**"
    fsck._canary()


def test_실제_저장소가_통과한다():
    # ★ 도구를 CLI 로 돌려 종료 코드를 본다. 위반은 1, 고장은 2 다.
    for tool in ("check_docs", "doc_fsck"):
        r = subprocess.run(["python3", str(ROOT / f"tools/{tool}.py")], capture_output=True, text=True)
        assert r.returncode == 0, (tool, r.stdout[-800:], r.stderr[-800:])


# ---------- PLAN ----------

def test_깨끗한_PLAN_은_통과한다():
    assert plan_fails(PLAN) == []


@pytest.mark.parametrize("change,want", [
    (("2행", "3행"), "제목은 3행인데"),
    (("| 3 | 📄 | 가 | |\n| 7 |", "| 7 | 📄 | 가 | |\n| 3 |"), "오름차순"),
    (("| 7 | ⏳ | 나 | #3 |", "| 3 | ⏳ | 나 | #3 |"), "겹친다"),
    (("| 3 | 📄 |", "| 3 | ✅ |"), "어휘 밖"),
    (("| 3 | 📄 | 가 |", "| 3 | 📄 | 가 해결됨 |"), "닫힘 표시"),
    (("| 7 | ⏳ | 나 | #3 |", "| 7 | ⏳ | 나 | |"), "막고 있는 것이 비었다"),
    (("| 7 | ⏳ | 나 | #3 |", "| 7 | ⏳ | 나 | #4 |"), "전건 #4"),
    (("#7 을 본다.", "#9 을 본다."), "없는 #9"),
    (("#7 을 본다.", "#7 과 파이어레인 PLAN #9 · 하토르 #8 을 본다. #9"), "없는 #9"),
    (("없다.", "| 9 | 📄 | 다 | |"), "§1 밖"),
    (("## 1. 남은 일 — 2행", "## 1. 남은 일"), "제목이 없다"),
])
def test_PLAN_규칙마다_걸린다(change, want):
    bad = PLAN.replace(*change)
    assert bad != PLAN, "치환이 먹지 않았다 — 검사의 검사가 빈손이다"
    assert any(want in f for f in plan_fails(bad)), plan_fails(bad)


def test_남의_저장소_행은_보지_않는다():
    # ★ 예시 이름은 파이어레인 · 하토르다. 이 파일은 seshat 에 사본으로 가고, 거기서
    #   `seshat` 은 자기 이름이다.
    assert plan_fails(PLAN.replace("#7 을 본다.", "파이어레인 PLAN #9 · 하토르 #8 을 본다.")) == []


def test_결번은_정상이다():
    # ★ 행 번호는 영구 식별자다. 3 다음이 7 이어도 통과한다.
    assert not any("연속" in f for f in plan_fails(PLAN))


# ---------- 절 번호 ----------

def test_절_번호가_겹치면_걸린다():
    f = []
    cd.check_headings("PLAN.md", "## 0. a\n## 1. b\n## 1. c\n", f)
    assert any("두 번" in x for x in f)


def test_번호_없는_절이_걸린다():
    f = []
    cd.check_headings("MASTER.md", "## 1. a\n## 부록\n", f)
    assert any("번호 없는" in x for x in f)


def test_DECISIONS_는_기호가_붙은_번호를_본다():
    f = []
    cd.check_headings("DECISIONS.md", "## §1. a\n## §2. b\n", f)
    assert f == []


# ---------- 파일 끝 ----------

@pytest.mark.parametrize("tail,want", [("끝.\n", None), ("끝.\n\n", "빈 줄"), ("끝.", "줄바꿈이 없다")])
def test_파일_끝은_줄바꿈_하나다(tail, want):
    f = []
    cd.check_eof("X.md", "# t\n\n" + tail, f)
    assert (f == []) if want is None else any(want in x for x in f), f


# ---------- DECISIONS ----------

def _dec(n, body):
    return f"## §{n}. 제목\n\n**2026-09-22**\n\n{body}\n\n### 배운 것\n\n무엇.\n"


def test_강제자는_정한_절부터_요구한다():
    n = cd.ENFORCER_FROM
    old = "".join(_dec(i, "본문") for i in range(1, n))
    if old:
        f = []
        cd.check_decisions(old, f)
        assert f == [], "옛 절에 소급하면 안 된다"
    f = []
    cd.check_decisions(old + _dec(n, "본문"), f)
    assert any(f"§{n}" in x and "강제자" in x for x in f)
    f = []
    cd.check_decisions(old + _dec(n, "강제자 없음 — 설계 판단이다"), f)
    assert f == []


def test_날짜_없는_절이_걸린다():
    f = []
    cd.check_decisions("## §1. a\n\n본문\n\n### 배운 것\n", f)
    assert any("날짜" in x for x in f)


# ---------- 참조 ----------

def _tree(tmp_path, plan=PLAN, master="# m\n\n## 1. a\n\n### 1-1. b\n", dec=None, extra=None):
    for 축 in ("now", "next", "why"):          # 축마다 한 칸(DECISIONS §199)
        (tmp_path / "docs" / 축).mkdir(parents=True)
    (tmp_path / "docs/PLAN.md").write_text(plan, encoding="utf-8")
    (tmp_path / "docs/MASTER.md").write_text(master, encoding="utf-8")
    (tmp_path / "docs/DECISIONS.md").write_text(dec or _dec(1, "본문"), encoding="utf-8")
    (tmp_path / "README.md").write_text(extra or "", encoding="utf-8")
    return tmp_path


@pytest.mark.parametrize("line,bad", [
    ("(DECISIONS §1)", False),
    ("(DECISIONS §1 · §2)", True),          # 사슬의 뒤쪽도 본다
    ("(MASTER §1-1)", False),
    # seshat: `§1-2` 는 **절 1 의 규칙 2** 라 이쪽에서는 실재한다(DECISIONS §230).
    #   thoth 의 MASTER 는 절 번호 자체가 `18-1a` 꼴이라 거기서는 없는 참조가 맞다
    ("(MASTER §1-2)", False),
    ("PLAN #7", False),
    ("PLAN #8", True),
    ("PLAN §2", False),
    ("PLAN §9", True),
    ("(파이어레인 DECISIONS §205)", False),  # 남의 저장소
    ("(하토르 PLAN #2)", False),       # 이 사본이 어느 저장소에 있든 남의 것인 이름
])
def test_참조가_실재해야_한다(tmp_path, line, bad):
    f = []
    cd.check_refs(_tree(tmp_path, extra=line), f)
    assert bool(f) is bad, f


# ---------- 실물 ----------

def test_없는_경로와_테스트가_걸린다(tmp_path):
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools/a.py").write_text("def check_x():\n    pass\n", encoding="utf-8")
    _tree(tmp_path, master="# m\n\n## 1. a\n\n`tools/a.py::check_x` · `tools/a.py::check_y` · `tools/b.py`\n")
    f = []
    fsck.check_paths(tmp_path, f)
    assert any("check_y" in x for x in f)
    assert any("tools/b.py" in x for x in f)
    assert not any("check_x" in x for x in f)


def test_어디서도_안_불리는_도구가_걸린다(tmp_path):
    (tmp_path / "tools").mkdir()
    (tmp_path / ".github/workflows").mkdir(parents=True)
    (tmp_path / "tools/used.py").write_text("", encoding="utf-8")
    (tmp_path / "tools/dead.py").write_text("", encoding="utf-8")
    (tmp_path / "README.md").write_text("python3 tools/used.py", encoding="utf-8")
    f = []
    fsck.check_tools(tmp_path, f)
    assert f == ["tools/dead.py 가 어디서도 불리지 않는다 — README 에 적거나 지운다"]


def test_사본은_원본의_참조를_들어도_된다(tmp_path):
    # ★ 다른 저장소에서 복사한 파일을 고치면 원본과 갈린다. 머리에 `사본이다` 가 있으면 뺀다.
    root = _tree(tmp_path)
    (root / "tools").mkdir()
    (root / "tools/copy.py").write_text("# ★ 저쪽의 사본이다.\n# (DECISIONS §999)\n", encoding="utf-8")
    (root / "tools/mine.py").write_text("# (DECISIONS §999)\n", encoding="utf-8")
    f = []
    cd.check_refs(root, f)
    assert [x for x in f if "copy.py" in x] == []
    assert any("mine.py" in x for x in f)


def test_더럽힌다고_적었으면_무엇을_더럽히는지_적어야_한다(tmp_path):
    """안 적으면 🔴 이 「중요함」 의 다른 말이 되고, 그러면 곧 전부 🔴 이 된다(DECISIONS §159)."""
    plan = tmp_path / "PLAN.md"
    plan.write_text(
        "## 1. 남은 일 — 1행\n\n| # | 상태 | 항목 | 전건 |\n|---|---|---|---|\n"
        "| 1 | 🔴 📄 | 아주 중요한 일이다 | — |\n", encoding="utf-8")
    fails = []
    cd.check_plan(plan.read_text(encoding="utf-8"), fails)
    assert any("무엇을 더럽히는지" in f for f in fails)
    plan.write_text(
        "## 1. 남은 일 — 1행\n\n| # | 상태 | 항목 | 전건 |\n|---|---|---|---|\n"
        "| 1 | 🔴 📄 | 사전이 좁아 `term` 을 더럽힌다 | — |\n", encoding="utf-8")
    fails = []
    cd.check_plan(plan.read_text(encoding="utf-8"), fails)
    assert not [f for f in fails if "더럽히는지" in f]


def test_더럽히는_빚은_무엇을_더럽히는지_들고_있다():
    """**수를 박지 않는다.** 갚으면 줄어드는 것이 정상이고, 수를 박으면 갚을 때 시험이 빨개진다
    (2026-09-28 #34 를 갚자 「넷 이상」 이 깨졌다 · DECISIONS §161)."""
    plan = (ROOT / "docs/PLAN.md").read_text(encoding="utf-8")
    붉은 = [x for x in plan.splitlines() if re.match(r"^\| \d+ \|", x) and "🔴" in x]
    assert all("더럽힌다" in x for x in 붉은), \
        "🔴 인 행은 무엇을 더럽히는지 들어야 한다 — 안 들면 「중요함」 의 다른 말이 된다"


def test_빨간_행은_막는_문장을_든다():
    """★ **🔴 의 뜻이 넓으면 표식이 죽는다**(DECISIONS §187). 「측정을 더럽힌다」 만으로는 끝이
    없다 — 재는 것은 늘 조금씩 더럽고, 그러면 모든 행이 🔴 이 될 수 있다.

    ★ 카나리아 — 막는 문장을 안 든 🔴 행을 만들어 검사가 살아 있는지 본다.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("cd", ROOT / "tools/check_docs.py")
    cd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cd)
    나쁜 = ("## 1. 남은 일 — 1행\n\n| # | 상태 | 항목 | 전건 |\n|---|---|---|---|\n"
            "| 1 | 🔴 | **뭔가 — 측정을 더럽힌다.** | — |\n")
    got = []
    cd.check_plan(나쁜, got)
    assert any("어느 문장을 막는지" in x for x in got), "카나리아가 죽었다"

    좋은 = 나쁜.replace("측정을 더럽힌다.**", "측정을 더럽힌다.** `docs/related.md` §3 의 「무엇」 을 막는다")
    got2 = []
    cd.check_plan(좋은, got2)
    assert not any("어느 문장을 막는지" in x for x in got2)


# ---------- 지도 · 색인 · 도구 목록(DECISIONS §199) ----------

지도 = ("# 문서 지도\n\n```\ndocs/\n  now/    MASTER.md       지금\n"
        "          related.md      결과\n  next/   PLAN.md         앞으로\n"
        "  why/    DECISIONS.md    왜\n```\n")


def _축(tmp_path, 지도글=지도, 더=()):
    for 축 in ("now", "next", "why"):
        (tmp_path / "docs" / 축).mkdir(parents=True)
    for 자리 in ("now/MASTER.md", "now/related.md", "next/PLAN.md", "why/DECISIONS.md", *더):
        (tmp_path / "docs" / 자리).write_text("x\n", encoding="utf-8")
    (tmp_path / "docs/README.md").write_text(지도글, encoding="utf-8")
    return tmp_path


def test_지도가_실물과_맞으면_조용하다(tmp_path):
    f = []
    cd.check_map(_축(tmp_path), f)
    assert f == []


def test_지도에_없는_문서가_걸린다(tmp_path):
    """★ 지도에 없는 문서는 아무도 안 연다 — 흩어짐은 파일이 아니라 **안 적힌 파일**이다."""
    f = []
    cd.check_map(_축(tmp_path, 더=("now/grammar.md",)), f)
    assert any("grammar.md" in x for x in f)


def test_지도가_없는_문서를_들면_걸린다(tmp_path):
    f = []
    cd.check_map(_축(tmp_path, 지도글=지도.replace("결과", "결과\n          ghost.md      유령")), f)
    assert any("ghost.md" in x for x in f)


def test_지도가_아예_없으면_걸린다(tmp_path):
    (tmp_path / "docs").mkdir()
    f = []
    cd.check_map(tmp_path, f)
    assert any("지도" in x or "README" in x for x in f)


def test_색인이_절과_어긋나면_걸린다():
    글 = _dec(1, "본문") + _dec(2, "본문")
    박은 = cd._색인을_박는다(글)
    f = []
    cd.check_index(박은, f)
    assert f == [], f
    f = []
    cd.check_index(박은 + _dec(3, "본문"), f)      # 절만 늘고 색인은 그대로
    assert any("어긋난다" in x for x in f)


def test_색인이_없으면_고치는_길을_말한다():
    f = []
    cd.check_index(_dec(1, "본문"), f)
    assert any("--fix-index" in x for x in f)


def test_도구가_목록에_없으면_걸린다(tmp_path):
    """★ 목록이 두 곳에 살면 **한쪽만 는다** — 새로 만든 것부터 빠진다(DECISIONS §199)."""
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools/새도구.py").write_text("x\n", encoding="utf-8")
    (tmp_path / "tools/옛도구.py").write_text("x\n", encoding="utf-8")
    f = []
    cd.check_tools_listed(tmp_path, "## 14. 도구\n\n`tools/옛도구.py` 만 적혀 있다\n", f)
    assert len(f) == 1 and "새도구.py" in f[0]


def test_도구_절이_사라지면_걸린다(tmp_path):
    (tmp_path / "tools").mkdir()
    f = []
    cd.check_tools_listed(tmp_path, "# m\n\n## 1. a\n", f)
    assert any("14" in x for x in f)


def test_저장소의_지도와_목록이_통과한다():
    """★ 시험이 인공 나무에서만 초록이면 **저장소를 안 지킨다**(DECISIONS §170 과 같은 병)."""
    f = []
    cd.check_map(ROOT, f)
    cd.check_tools_listed(ROOT, (ROOT / "docs/MASTER.md").read_text(encoding="utf-8"), f)
    cd.check_index((ROOT / "docs/DECISIONS.md").read_text(encoding="utf-8"), f)
    assert f == [], f


def test_닫힌_행의_번호가_DECISIONS_에_남는다(tmp_path):
    """★ PLAN 은 닫힌 행을 **지운다** — 그러면 기록이 DECISIONS 한 벌뿐이고, 그것마저 없으면
    **영 벌**이 된다(DECISIONS §221). 2026-09-29 `#46` 이 그렇게 샜다."""
    plan = "## 1. 남은 일 — 2행\n\n| # | 상태 | 항목 | 전건 |\n|---|---|---|---|\n| 1 | 📄 | a | |\n| 3 | 📄 | b | |\n"
    f = []
    cd.check_plan_closed(tmp_path, plan, "## §9. 무엇\n\nPLAN #2 를 닫았다.\n", f)
    assert f == [], f
    f = []
    cd.check_plan_closed(tmp_path, plan, "## §9. 무엇\n\n아무 번호도 없다.\n", f)
    assert len(f) == 1 and "#2" in f[0]
