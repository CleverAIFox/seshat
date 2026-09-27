"""make_patch.sh 의 경고 — 기계마다 다른 파일 · 판정과 사전을 같이 바꾸기(DECISIONS §96).

★ **패치를 진짜로 만들지 않는다.** 경고는 산출물(`$OUT`)을 grep 해서 내므로, 그 grep 이 무엇을 잡는지만
  본다. 저장소 상태를 흔들지 않고 규칙만 시험하는 자리다.
"""
import pathlib

import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
SH = (ROOT / "tools/make_patch.sh").read_text(encoding="utf-8")

VERDICT_PAT = r"^\+\| H-[0-9]+ \| (채택|기각) \|"
PROPOSED_PAT = r"^\+\| H-[0-9]+ \| 제안 \|"

def _grep(pattern: str, text: str) -> int:
    """스크립트가 쓰는 것과 같은 grep -E 로 센다 — 파이썬 정규식으로 흉내 내지 않는다."""
    r = subprocess.run(["grep", "-cE", pattern], input=text, capture_output=True, text=True)
    return int(r.stdout.strip() or 0)

def test_스크립트가_세_가지를_경고한다():
    assert "판 번호 말고도" in SH
    assert "판정과 온톨로지를 같이 바꾼다" in SH
    assert "제안 상태로 더하는 가설" in SH

def _lock_hunk(body: str) -> int:
    """스크립트의 awk + grep 과 같은 셈 — uv.lock 안에서 판 번호 아닌 변경 줄을 센다."""
    patch = "diff --git a/uv.lock b/uv.lock\n" + body + "diff --git a/x b/x\n+다른 파일\n"
    awk = subprocess.run(
        ["awk", r'/^diff --git a\/uv.lock/{on=1;next} on&&/^diff --git /{on=0} on&&/^[-+][^-+]/'],
        input=patch, capture_output=True, text=True).stdout
    r = subprocess.run(["grep", "-vcE", r'^[-+]version = "[0-9.]+"$'], input=awk, capture_output=True, text=True)
    return int(r.stdout.strip() or 0)


def test_판_번호만_바뀐_lock_은_안_잡는다():
    assert _lock_hunk('-version = "0.0.81"\n+version = "0.0.82"\n') == 0


def test_의존성이_바뀐_lock_은_잡는다():
    assert _lock_hunk('-version = "0.0.81"\n+version = "0.0.82"\n+name = "새-의존성"\n') == 1


def test_uv_lock_을_담은_패치를_잡는다():
    assert _grep("^diff --git a/uv.lock", "diff --git a/uv.lock b/uv.lock\n")
    assert _grep("^diff --git a/uv.lock", "diff --git a/tools/x.sh b/tools/x.sh\n") == 0
    # 본문에 든 이름은 안 센다 — 줄머리만 본다
    assert _grep("^diff --git a/uv.lock", "  uv.lock 을 담았다\n") == 0

def test_온톨로지_변경을_잡는다():
    assert _grep("^diff --git a/data/ontology/", "diff --git a/data/ontology/aws.jsonl b/data/ontology/aws.jsonl\n")
    assert _grep("^diff --git a/data/ontology/", "diff --git a/data/catalog.toml b/data/catalog.toml\n") == 0

def test_판정_줄만_센다():
    patch = ("+| H-047 | 실험 | R2 | 무엇 | 어떻게 | 0 | |\n"
             "+| H-045 | 채택 | R7 | 무엇 | 어떻게 | 0 | 근거 |\n"
             "+| H-044 | 기각 | R2 | 무엇 | 어떻게 | 0 | 근거 |\n"
             "-| H-043 | 채택 | R2 | 지운 줄은 안 센다 | | 0 | |\n")
    assert _grep(VERDICT_PAT, patch) == 2
    assert _grep(PROPOSED_PAT, patch) == 0

def test_스크립트가_문법에_맞는다():
    assert subprocess.run(["bash", "-n", str(ROOT / "tools/make_patch.sh")]).returncode == 0
