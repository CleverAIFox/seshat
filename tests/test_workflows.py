"""워크플로가 원격이 거절할 것을 쓰지 않는가(thoth tools/check_static.py 의 Node 20 검사를 옮겼다)."""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
# ★ 액션 → Node 20 인 메이저. 이 번호 이하를 막는다. **알고 있는 목록은 언젠가 하나를 빠뜨린다**
#   (thoth DECISIONS §43) — 러너가 경고를 내면 그 액션을 여기에 더한다. upload-artifact 는 2026-09-22
#   GPU 평가 실행의 주석이 짚었다.
NODE20 = {"actions/checkout": 4, "actions/setup-python": 5, "astral-sh/setup-uv": 6,
          "gitleaks/gitleaks-action": 2, "actions/upload-artifact": 4}
USES = re.compile(r"uses:\s*([\w.-]+/[\w.-]+)@v(\d+)\b")


def test_Node_20_액션이_없다():
    bad = []
    for p in sorted((ROOT / ".github/workflows").glob("*.yml")):
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            m = USES.search(line)
            if m and m.group(1) in NODE20 and int(m.group(2)) <= NODE20[m.group(1)]:
                bad.append(f"{p.name}:{n} {m.group(0)}")
    assert bad == []


def test_카나리아():
    assert USES.search("      - uses: actions/upload-artifact@v4").groups() == ("actions/upload-artifact", "4")


def test_GPU_작업은_손으로만_돈다():
    text = (ROOT / ".github/workflows/gpu-eval.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch" in text and "push:" not in text and "[self-hosted, gpu]" in text


def _workflows():
    return sorted((ROOT / ".github/workflows").glob("*.yml"))


def test_워크플로마다_권한을_적는다():
    """비공개 저장소는 적지 않은 권한이 없다. 기본값에 기대면 저장소 설정이 바뀔 때 조용히 달라진다(DECISIONS §20)."""
    assert [p.name for p in _workflows() if not re.search(r"^permissions:", p.read_text(encoding="utf-8"), re.M)] == []


def test_gitleaks_는_PR_을_읽을_수_있다():
    """gitleaks 는 PR 의 커밋 목록을 읽는다. `pull-requests: read` 가 없으면 봇의 PR 에서 403 이다(2026-09-22)."""
    bad = [p.name for p in _workflows()
           if "gitleaks/gitleaks-action" in (t := p.read_text(encoding="utf-8"))
           and not re.search(r"^\s+pull-requests:\s*(read|write)\b", t, re.M)]
    assert bad == []


def test_CI_는_verify_를_부르기만_한다():
    """점검 목록이 두 곳에 살면 한쪽만 고쳐진다 — MASTER 가 다섯이라 적는 동안 CI 는 일곱을 돌았다."""
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "bash tools/verify.sh" in ci
    assert re.findall(r"tools/(?:check_\w+|doc_fsck)\.py|ruff check|pytest", ci) == []


def test_verify_가_검사기를_빠뜨리지_않는다():
    """새 `check_*.py` 를 만들고 verify 에 안 올리면 아무도 안 돈다."""
    v = (ROOT / "tools/verify.sh").read_text(encoding="utf-8")
    tools = [p.name for p in (ROOT / "tools").glob("check_*.py")] + ["doc_fsck.py", "lake.py"]
    assert [t for t in tools if f"tools/{t}" not in v] == []
