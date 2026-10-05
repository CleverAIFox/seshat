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
# ★ **SHA 로 고정한 줄의 판은 주석에 산다**(DECISIONS §282). 그래서 `@v(\d+)` 하나만 보면
#   고정한 뒤로 이 검사가 **조용히 0건이 된다** — thoth 가 같은 날 정확히 그렇게 됐다.
#   꼴을 바꾸는 고침이 **그 꼴을 읽던 검사를 껐다.**
USES_PINNED = re.compile(r"uses:\s*([\w.-]+/[\w.-]+)@[0-9a-f]{40}\s*#\s*v(\d+)\b")
# `uses:` 가 가리킬 수 있는 꼴 — 저장소 액션 · 같은 저장소 경로 · 도커.
USES_ANY = re.compile(r"^\s*(?:-\s*)?uses:\s*(\S+)")


def 액션들(line: str) -> list[tuple[str, int]]:
    """한 줄에서 (액션 이름, 메이저). 맨 태그와 SHA 고정을 다 읽는다."""
    것 = [(m.group(1), int(m.group(2))) for m in USES.finditer(line.split("#", 1)[0])]
    것 += [(m.group(1), int(m.group(2))) for m in USES_PINNED.finditer(line)]
    return 것


def 안고정된것(text: str) -> list[tuple[int, str]]:
    """SHA 로 안 고정한 `uses:`. 판 주석이 없는 것도 잡는다 — 주석은 위 검사의 자료다."""
    bad = []
    for n, line in enumerate(text.split("\n"), 1):
        m = USES_ANY.match(line.split("#", 1)[0])
        if not m:
            continue
        ref = m.group(1)
        if ref.startswith(("./", "docker://")):
            continue
        _, _, 가리키는것 = ref.partition("@")
        if not re.fullmatch(r"[0-9a-f]{40}", 가리키는것):
            bad.append((n, ref))
        elif not re.search(r"#\s*v\d+", line):
            bad.append((n, f"{ref[:20]}… 판 주석이 없다"))
    return bad


def test_Node_20_액션이_없다():
    bad = []
    for p in sorted((ROOT / ".github/workflows").glob("*.yml")):
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for 이름, 메이저 in 액션들(line):
                if 이름 in NODE20 and 메이저 <= NODE20[이름]:
                    bad.append(f"{p.name}:{n} {이름}@v{메이저}")
    assert bad == []


def test_고정한_줄에서도_Node20_을_읽는다():
    """★ **이것이 이 묶음의 핵이다**(DECISIONS §282).

    고정은 **판을 못 박는 것**이고 **옛 판을 허락하는 것이 아니다.** 옛 메이저를 SHA 로
    고정해도 잡혀야 한다 — 그러지 않으면 「고정했다」 가 「검사를 껐다」 와 같은 말이 된다.
    """
    옛 = "      - uses: actions/checkout@" + "a" * 40 + "  # v4.2.2\n"
    assert [x for x in 액션들(옛)] == [("actions/checkout", 4)]


def test_액션을_SHA_로_고정한다():
    """★ 메이저 태그는 업스트림이 옮긴다. 러너를 `ubuntu-24.04` 로 못 박은 것과 같은 규율이고,
    고정이 가장 값진 자리는 **자격증명과 같은 작업에서 도는 액션**이다(thoth DECISIONS §125)."""
    나쁜 = [f"{p.name}:{n} {ref}"
           for p in _workflows()
           for n, ref in 안고정된것(p.read_text(encoding="utf-8"))]
    assert 나쁜 == [], "`uses:` 를 40자 SHA 로 고정하고 판을 `# v7.0.1` 로 적는다\n" + "\n".join(나쁜)


def test_카나리아():
    assert USES.search("      - uses: actions/upload-artifact@v4").groups() == ("actions/upload-artifact", "4")
    assert 안고정된것("      - uses: actions/checkout@v7\n") == [(1, "actions/checkout@v7")]
    assert 안고정된것("      - uses: a/b@" + "0" * 40 + "  # v1.2.3\n") == []


def test_GPU_작업은_손으로만_돈다():
    text = (ROOT / ".github/workflows/gpu-eval.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch" in text and "push:" not in text and "[self-hosted, gpu]" in text


def _workflows():
    return sorted((ROOT / ".github/workflows").glob("*.yml"))


def test_워크플로마다_권한을_적는다():
    """비공개 저장소는 적지 않은 권한이 없다. 기본값에 기대면 저장소 설정이 바뀔 때 조용히 달라진다(DECISIONS §20)."""
    assert [p.name for p in _workflows() if not re.search(r"^permissions:", p.read_text(encoding="utf-8"), re.M)] == []


def test_gitleaks_는_PR_을_읽을_수_있다():
    """★ **`read` 로는 모자란다**(DECISIONS §282).

    ★ **이름은 안 바꿨다.** DECISIONS §20 의 강제자와 MASTER 가 이 이름을 들고 있고
      DECISIONS 는 덧붙이기만 한다 — 이름을 바꾸면 **옛 절의 강제자가 죽는다.**
      `write` 는 `read` 를 품으므로 이름이 거짓이 되지도 않는다.

    gitleaks 는 PR 의 커밋 목록을 읽고(2026-09-22 봇의 첫 PR 에서 403), **누출을 찾으면
    PR 에 위치를 댓글로 단다** — `GITLEAKS_ENABLE_COMMENTS` 의 기본값이 켬이다. 읽기만
    주면 그 호출이 403 이고, **지금까지 초록이었던 것은 누출이 없었기 때문**이다.
    전의 이 검사는 `read|write` 둘 다 받아서 **thoth 와 어긋난 것을 못 잡았다** —
    한쪽만 받도록 좁힌다.
    """
    bad = [p.name for p in _workflows()
           if "gitleaks/gitleaks-action" in (t := p.read_text(encoding="utf-8"))
           and not re.search(r"^\s+pull-requests:\s*write\b", t, re.M)]
    assert bad == [], "gitleaks 가 도는 작업에 `pull-requests: write` 를 준다"


def test_쓰기_권한은_그것을_쓰는_작업에만_있다():
    """★ **맨 위 `permissions:` 는 모든 작업에 걸린다**(DECISIONS §282). gitleaks 때문에
    필요한 쓰기를 거기 적으면 `verify` 작업도 그 권한을 들고 돈다 — 쓰지 않는 권한이다."""
    # ★ 주석을 벗긴 뒤에 본다. **까닭을 적은 줄이 검사에 걸리면 까닭을 못 적는다.**
    몸 = _몸만(ROOT / ".github/workflows/ci.yml")
    위 = 몸[:몸.index("jobs:")]
    assert "pull-requests:" not in 위, "맨 위에 쓰기를 두면 모든 작업이 그것을 받는다"


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


def _몸만(p) -> str:
    """주석을 벗긴 워크플로 본문. **까닭을 적은 줄이 검사에 걸리면 까닭을 못 적는다.**"""
    return "\n".join(x.split("#", 1)[0] for x in p.read_text(encoding="utf-8").splitlines())


def test_워크플로가_가설_번호를_안_박는다():
    """★ **2026-09-22 `h001` 이 박힌 채로 H-019 를 쟀다**(DECISIONS §280).

    탐침은 `h001` 로 만들고 `--set data/probes/h001.jsonl` 로 재는데, 결과 파일만
    `H-019-probes-*` 로 복사했다 — **이름은 H-019 이고 내용은 h001 이다.** 레이크에 들어가면
    나중에 데이터만 보고는 구별이 안 되고, **GPU 시간은 다시 못 만든다**(DECISIONS §28).
    그 파일 안의 ★ 가 「백엔드 이름을 박으면 실험마다 이 파일을 고친다」 를 적어 놓고 있었다 —
    **원칙을 적어 두고 한 칸 아래에서 어겼다.** 이름은 입력이 정한다.
    """
    박힘 = re.compile(r"\bh\d{3}\b|\bH-\d{3}\b")
    나쁜 = [f"{p.name}:{i} {m.group(0)}"
           for p in _workflows()
           for i, 줄 in enumerate(_몸만(p).splitlines(), 1)
           if (m := 박힘.search(줄))]
    assert 나쁜 == [], "워크플로에 가설 번호가 박혔다 — 입력이 정한다\n" + "\n".join(나쁜)


def test_GPU_작업은_한_인터프리터로_돈다():
    """★ 셀프 호스티드 러너에서 `python3` 과 `uv run python` 이 다른 해석기면 **조용히 다르게 돈다.**

    2026-10-02 `check_hypotheses` 와 `lake.py put` 만 시스템 `python3` 이었다 — 그 둘이 다른
    자리의 의존성을 보면 문이 열리거나 레이크가 비어도 작업은 초록이다.
    """
    몸 = _몸만(ROOT / ".github/workflows/gpu-eval.yml")
    나쁜 = [x.strip() for x in 몸.splitlines() if re.search(r"(?<!uv run )\bpython3? tools/", x)]
    assert 나쁜 == [], "GPU 작업은 `uv run` 하나로 돈다\n" + "\n".join(나쁜)


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


작업머리 = re.compile(r"^  ([\w-]+):\s*$")


def 작업들(text: str) -> dict[str, list[str]]:
    """`jobs:` 아래의 (작업 이름 → 그 블록의 줄들)."""
    것, 이름, 안 = {}, None, False
    for 줄 in text.split("\n"):
        if 줄.startswith("jobs:"):
            안 = True
            continue
        if not 안:
            continue
        if 줄 and not 줄.startswith(" "):
            break
        if m := 작업머리.match(줄):
            이름 = m.group(1)
            것[이름] = []
            continue
        if 이름:
            것[이름].append(줄)
    return 것


def 상한없는것(text: str) -> list[str]:
    난것 = []
    for 이름, 블록 in 작업들(text).items():
        if any(re.match(r"^    uses:\s*\S", x) for x in 블록):
            continue                   # 재사용 워크플로 호출 — GitHub 이 상한을 거부한다
        if not any(re.match(r"^    timeout-minutes:\s*\d+", x) for x in 블록):
            난것.append(이름)
    return 난것


def test_작업마다_시간_상한이_있다():
    """★ **없으면 GitHub 기본 6시간까지 매달린다**(DECISIONS §283).

    이 저장소에서 더 아픈 자리는 `gpu-eval` 이다 — **셀프 호스티드 러너가 이 기계다.**
    매달린 작업이 GPU 를 여섯 시간 쥐고 있으면 그 시간은 다시 안 온다(DECISIONS §28).
    `gpu-eval` 은 상한을 들고 있었고 **나머지 셋이 안 들고 있었다.**

    ★ **족 가드다**(파이어레인 `tools/actionpin.py`). 「이 작업에 상한이 있나」 를 하나씩
      묻지 않고 「상한 없는 작업이 있나」 를 묻는다 — 새 작업이 생기는 순간 물린다.
    """
    나쁜 = [f"{p.name} · {이름}" for p in _workflows() for 이름 in 상한없는것(p.read_text(encoding="utf-8"))]
    assert 나쁜 == [], "작업마다 `timeout-minutes` 를 적는다\n" + "\n".join(나쁜)


def test_상한_카나리아():
    좋 = "jobs:\n  a:\n    runs-on: x\n    timeout-minutes: 5\n    steps:\n      - run: echo\n"
    assert 상한없는것(좋) == []
    assert 상한없는것(좋.replace("    timeout-minutes: 5\n", "")) == ["a"]
    assert 상한없는것("jobs:\n  a:\n    uses: ./.github/workflows/x.yml\n") == []


# ── 워크플로가 드는 저장소 경로(DECISIONS §291) ──────────────────────────────
#
# ★ **2026-10-05 에 이것 때문에 CI 가 빨갰다.** §288 이 `docs/next/papers.md` 를
#   `docs/papers.md` 로 옮기고 `watch_papers.py` 는 따라 고쳤는데 **`papers.yml` 세 자리를
#   안 고쳤다.** 예약 작업은 주 1회라 **엿새 동안 아무도 모른다** — 그리고 그 판이 「마지막으로
#   끝난 CI」 가 되어 **관계없는 밀기를 막았다.**
# ★ **문서 쪽은 `doc_fsck` 가 이미 본다.** 워크플로는 아무도 안 봤다 — 코드도 문서도 아닌
#   자리가 검사의 사각이었다.
# ★ **밖 — 글롭과 변수가 든 경로는 안 본다.** `$GITHUB_WORKSPACE/...` · `docs/*.md` 는
#   무엇을 가리킬지 돌려 봐야 안다.
# ★ **밖 — 저장소 이름이 붙은 남의 것은 안 본다.** `파이어레인 tools/actionpin.py` 는
#   이 저장소의 파일이 아니다(`check_docs` 의 같은 규칙).
# ★ **밖 — git 이 무시하는 자리는 안 본다.** `data/probes/` 는 **결정적이라 다시 만드는** 것이고
#   (`make_probes.py`) 저장소에 없는 것이 정상이다. 요구하면 **거짓 빨강**이고, 거짓 빨강이
#   쌓이면 사람이 검사를 끈다(thoth DECISIONS §158).

_WF앞 = ("tools", "tests", "seshat", "data", "docs", ".github", "site", "web")
_WF경로 = re.compile(r"(?<![\w./-])((?:%s)/[A-Za-z0-9_./-]*[A-Za-z0-9_])"
                     % "|".join(re.escape(t) for t in _WF앞))
_남의것 = ("파이어레인", "하토르", "thoth", "fire-lane", "hathor")


def 워크플로경로(글: str) -> list[tuple[int, str]]:
    """워크플로가 드는 (줄, 저장소 경로). 글롭 · 변수 · 남의 저장소 것은 뺀다."""
    난것 = []
    for n, 줄 in enumerate(글.split("\n"), 1):
        if any(q in 줄 for q in _남의것):
            continue
        for m in _WF경로.finditer(줄):
            q = m.group(1).rstrip(".,)'\"")
            if "*" in q or "$" in q:
                continue
            난것.append((n, q))
    return 난것


def _무시된다(q: str) -> bool:
    """git 이 무시하는 자리. 없는 디렉터리는 `dir/` 꼴 규칙에 안 걸려 끝에 `/` 를 붙여 한 번 더 묻는다."""
    import subprocess
    try:
        return any(subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", x],
                                  capture_output=True).returncode == 0
                   for x in (q, q.rstrip("/") + "/"))
    except OSError:
        return False


def test_워크플로가_드는_경로가_실재한다():
    흠 = []
    for p in sorted((ROOT / ".github/workflows").glob("*.yml")):
        for n, q in 워크플로경로(p.read_text(encoding="utf-8")):
            if not (ROOT / q).exists() and not _무시된다(q):
                흠.append(f"{p.name}:{n} {q}")
    assert 흠 == [], "워크플로가 없는 것을 가리킨다 — " + " · ".join(흠)


def test_워크플로_경로_카나리아():
    # ★ **조용히 0건이 되는 자리다.** 정규식이 늙으면 아무것도 못 찾고 **그래도 초록**이다.
    assert 워크플로경로("  run: python3 tools/x.py\n") == [(1, "tools/x.py")]
    assert 워크플로경로("  run: cat docs/*.md\n") == []
    assert 워크플로경로("  # 파이어레인 tools/actionpin.py 와 같다\n") == []
    assert 워크플로경로("  run: ls $HOME/tools/x.py\n") == []
    assert 워크플로경로("  run: git add docs/papers.md\n") == [(1, "docs/papers.md")]


def test_실물에서_하나라도_찾는다():
    # ★ 「없는 것을 안 가리킨다」 만 보면 **아무것도 안 세는 검사**도 통과한다.
    전부 = [q for p in sorted((ROOT / ".github/workflows").glob("*.yml"))
            for _, q in 워크플로경로(p.read_text(encoding="utf-8"))]
    assert len(전부) >= 5, f"워크플로에서 경로를 {len(전부)} 개밖에 못 읽었다 — 정규식이 늙었다"
