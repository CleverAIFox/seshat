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


def test_결과는_레이크보다_먼저_아티팩트로_간다():
    """레이크 단계가 실패해도 GPU 시간이 살아남는다(DECISIONS §28)."""
    t = (ROOT / ".github/workflows/gpu-eval.yml").read_text(encoding="utf-8")
    assert t.index("upload-artifact") < t.index("lake.py put")
    art = t[t.index("upload-artifact"):t.index("lake.py put")]
    assert "if: always()" in art


def test_예약_작업은_main_을_안_민다():
    """봇이 main 을 움직이면 보내 둔 패치의 기준 나무가 갈린다(DECISIONS §30 · §126)."""
    text = (ROOT / ".github/workflows/papers.yml").read_text(encoding="utf-8")
    assert "schedule:" in text and "gh pr create" in text
    assert "push -u origin" in text and "push origin main" not in text
    assert re.search(r"git switch -c", text)


def test_예약_작업은_정각을_피한다():
    """정각에 세상의 작업이 몰려 밀린다. 분을 흩는다."""
    m = re.search(r'cron: "(\d+) ', (ROOT / ".github/workflows/papers.yml").read_text(encoding="utf-8"))
    assert m and m.group(1) not in ("0", "30")


def test_셸의_변수_이름은_ASCII_다():
    """배시는 한글 변수 이름을 못 받는다 — 2026-09-28 에 **두 번째**로 겪었다(DECISIONS §164).

    한 번은 우연이고 두 번은 자리다. 셸 파일 전부를 훑어 막는다.
    """
    import re
    나쁜 = []
    for f in (*ROOT.glob("tools/*.sh"), *ROOT.glob(".githooks/*"), *ROOT.glob(".github/workflows/*.yml")):
        if not f.is_file():
            continue
        for i, 줄 in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            몸 = 줄.split("#", 1)[0]
            for m in re.finditer(r"(^|[;&|]|\s)([A-Za-z_]*[^\x00-\x7F][^\s=]*)=", 몸):
                나쁜.append(f"{f.name}:{i} {m.group(2)}=")
    assert not 나쁜, "셸 변수 이름은 ASCII 여야 한다\n" + "\n".join(나쁜)


def test_커밋_훅이_탐침을_들고_있다():
    """**탐침은 막는다.** `exit 0` 으로 두면 환경변수 한 줄이 모든 커밋의 훅을 조용히 통과시키고
    `--no-verify` 와 달리 흔적도 안 남는다(DECISIONS §164)."""
    훅 = (ROOT / ".githooks/pre-commit").read_text(encoding="utf-8")
    assert "SESHAT_HOOK_PROBE" in 훅
    탐침 = 훅.split("SESHAT_HOOK_PROBE", 1)[1].split("fi", 1)[0]
    assert "exit 1" in 탐침 and "exit 0" not in 탐침, "탐침이 통과시키면 그것은 영구 우회 스위치다"


def test_훅이_규칙을_두_번_적지_않는다():
    """검사의 정본은 `tools/` 의 도구들이다 — 목록을 두 곳에 적으면 한쪽만 고쳐진다(§157)."""
    몸 = "\n".join(x.split("#", 1)[0] for x in
                   (ROOT / ".githooks/pre-commit").read_text(encoding="utf-8").splitlines())
    assert "pytest" not in 몸, "커밋마다 7초를 물리면 사람이 훅을 끈다 — pytest 는 verify 의 몫이다"


def test_CI_에서_안_도는_단계는_까닭을_적는다():
    """★ **2026-09-28 CI 가 네 판째 빨간 것을 아무도 몰랐다**(DECISIONS §170).

    `verify.sh` 가 CI 에서 훅을 검사하고 있었다 — **CI 는 커밋을 안 하므로 깔 까닭이 없다.**
    이 기계에서는 훅이 깔려 있어 초록이었고, 빨간 것은 GitHub 에만 있었고, 아무도 안 봤다.
    """
    v = (ROOT / "tools/verify.sh").read_text(encoding="utf-8")
    for 이름, 까닭 in (("훅", "CI 는 커밋을 안 한다"), ("lake", "SSD 는 이 기계에만")):
        블록 = v[v.index(f'NAMES+=("{이름}")'):]
        assert 까닭 in 블록.splitlines()[0], f"{이름} 이 CI 에서 왜 안 도는지 안 적혀 있다"


def test_verify_가_CI_판정을_본다():
    """★ **이 기계가 초록인 것과 CI 가 초록인 것은 다른 말이다**(DECISIONS §170).
    훅은 이 기계에만 있다 — 남의 PR 도 새로 받은 저장소도 안 막는다. **강제자는 CI 다.**"""
    v = (ROOT / "tools/verify.sh").read_text(encoding="utf-8")
    assert "tools/ci_status.py" in v
    assert v.index("ci_status.py") > v.index("tools/lake.py"), "CI 판정은 마지막에 본다"
