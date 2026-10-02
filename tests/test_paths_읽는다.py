"""**사람이 밟는 자리가 「도구가 깨졌다」 로 떨어지지 않는가**(DECISIONS §270).

★ 이 파일은 **seshat 것**이다 — thoth 사본이 아니다(DECISIONS §5).
★ **catch-all 은 바닥이지 길이 아니다.** `check_crashes`(§232)는 맨몸을 싸는지만 보고,
  **싼 뒤에 무슨 말을 하는지**는 안 본다 — 그 자리를 이 시험이 든다.
"""
from __future__ import annotations

import ast
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from seshat import paths  # noqa: E402

없는 = "/tmp/__seshat_없는파일__.jsonl"
# ★ **셋은 시험이 제 손으로 만든다**(2026-10-01 · DECISIONS §271). 종전에는 `data/domain/d002.jsonl`
#   을 줬는데 **그 파일은 레이크에 있고 git 에는 없다** — 없는 기계에서는 도구가 **「평가셋이 없다」
#   로 앞 단계에서 멈추고**, 진짜 밟으려던 자리에 **닿지도 못한 채 초록**이 났다. `slice.py` 가
#   그렇게 샜고 사람 기계에서만 빨개졌다. **§170 과 같은 병** — 이 기계의 초록이 저 기계의 초록이 아니다.


# ★ **git 에 든 셋이어야 한다**(2026-10-01 · DECISIONS §273). `data/domain/` 은 `.gitignore` 에 있고,
#   §271 이 「시험은 git 안의 것만 전제해야 한다」 고 적은 **그 패치에서 그것을 어겼다** —
#   상자에 파일이 보이는 것을 **git 에 있다는 뜻으로 읽었다.** CI 에서만 빨개졌다.
셋원본 = "data/eval/seed.jsonl"


@pytest.fixture(scope="module")
def 셋(tmp_path_factory) -> str:
    """git 에 **추적되는** 셋에서 세 줄만 떠서 임시 셋을 만든다 — 어느 기계에서나 같은 깊이까지 간다."""
    원 = ROOT / 셋원본
    assert 원.exists(), f"{셋원본} 이 사라졌다 — 이 시험의 전제다"
    p = tmp_path_factory.mktemp("셋") / "t.jsonl"
    p.write_text("\n".join(원.read_text(encoding="utf-8").splitlines()[:3]) + "\n", encoding="utf-8")
    return str(p)


def test_이_시험이_여는_셋이_git_에_있다():
    """★ **있는 것과 git 에 있는 것은 다르다**(DECISIONS §275).

    2026-10-01 이 시험이 `data/domain/d001.jsonl` 을 썼다. 작업 트리에는 있고 **git 에는 없다** —
    `.gitignore` 가 `data/domain/` 을 뺀다. 그래서 **사람 기계에서는 초록이고 CI 에서만 빨갰다.**
    §271 이 그 규칙을 적은 **바로 그 패치**에서 어겼고, 어긴 까닭은 **`ls` 로 확인**했기 때문이다.

    ★ **좁게 묻는다.** 「시험 전부가 git 밖 파일에 안 기대는가」 를 **정적으로** 재려고 세 판을
      썼고 세 판 다 **거짓 양성**이 남았다(카탈로그 조회 · 도장 규칙 · tmp 에 적는 글자는
      `ROOT /` 와 붙어도 **파일을 안 연다**). **그 물음에 답하는 자는 이미 있다 — CI 다.**
      레이크가 없는 곳에서 돌기 때문이고, 오늘도 **CI 가 잡았다.** 여기서는 **이 파일이 여는
      하나**만 묻는다(DECISIONS §275).
    """
    r = subprocess.run(["git", "ls-files", "--error-unmatch", 셋원본],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, (
        f"{셋원본} 이 git 에 없다 — 이 시험은 **git 에 든 셋**만 전제해야 한다(DECISIONS §275).\n"
        f"    git 에 있나는 git 에게 묻는다 : git ls-files {셋원본}\n"
        f"    무시되나 : git check-ignore -v {셋원본}")


def _밟는다(셋: str) -> dict[str, list[str]]:
    """**경로를 받는 도구와 그것을 밟는 인자.** 아래 시험이 이 표가 **빠짐없는지**까지 묻는다."""
    return {
        "bootstrap.py": [없는, 없는, "--set", 셋],
        "compare_runs.py": [없는, 없는, "--set", 셋],
        "gemba.py": ["--run", f"x={없는}", "--out", "/tmp/_o.jsonl", "--set", 셋],
        "qe.py": ["--run", f"x={없는}", "--out", "/tmp/_o.jsonl", "--set", 셋],
        "rescore.py": [없는, "--set", 셋],
        "show_misses.py": [없는],
        "slice.py": [없는, "--set", 셋],
        "style_na.py": [없는, "--set", 셋],
        "term_diff.py": [없는, 없는],
        "noise.py": [없는],
        "mine_terms.py": [없는],
        "gate.py": [없는],
        "labels.py": ["corr", "--set", 셋, "--a", 없는],
        "lake.py": ["check"],
    }


밟는다 = _밟는다("")      # ★ 이름만 쓰는 자리를 위한 것 — 인자는 `셋` 을 받아 다시 만든다


@pytest.mark.parametrize("도구", sorted(밟는다))
def test_없는_파일에_맨몸으로_안_죽는다(도구, 셋):
    """★ 2026-10-01 **열넷 중 일곱**이 역추적과 「도구가 깨졌다」 를 뱉었다(DECISIONS §270).

    `gemba` 가 아직 도는 중인데 `bootstrap --점수` 를 부른 것이 그 자리였다 — **도구는 멀쩡한데
    「제가 깨졌다」 고 말하고 `verify.sh` 로 고치라고 했다.** 고칠 것이 없는데.

    ★ **상한을 90 초에서 240 초로 올렸다**(2026-10-02). `lake.py check` 가 레이크 전체를 훑는데
      §277 이 받아 둔 k8s 클론이 **작은 파일 1,841 개**를 얹었고, 레이크는 `/mnt/f` 에 있다.
      실측 **63 초**인데 그중 CPU 는 **5 초**다 — 나머지는 전부 WSL↔윈도우 I/O 대기다.
      912 개 시험이 디스크를 같이 쓰면 63 초가 90 초를 넘는다.
      ★ **도구가 느려진 것이 아니라 레이크가 커졌고, 그 레이크가 느린 자리에 있다.**
        이 수가 다시 걸리면 올릴 것이 아니라 **레이크의 자리**를 다시 봐야 한다.
    """
    r = subprocess.run([sys.executable, f"tools/{도구}", *_밟는다(셋)[도구]],
                       cwd=ROOT, capture_output=True, text=True, timeout=240)
    글 = r.stdout + r.stderr
    assert "Traceback" not in 글, f"{도구} 가 맨몸으로 죽는다\n{글[-600:]}"
    assert "도구가 깨졌다" not in 글, f"{도구} 가 사람의 실수를 **도구 고장**이라 부른다\n{글[-600:]}"


def test_경로를_받는_도구가_표에_다_있다():
    """★ **표를 손으로 들면 새 도구가 조용히 빠진다**(DECISIONS §266 의 그 규율).

    도구를 더하면서 이 표를 안 늘리면 **그 도구는 안 밟힌 채 초록으로 보인다.**
    """
    낌새 = ("경로", "path", "jsonl", "--set", "--점수", "--run", "--out", "run", "runs", "a", "b", "set")
    빠진 = []
    for f in sorted((ROOT / "tools").glob("*.py")):
        t = f.read_text(encoding="utf-8")
        if "add_argument" not in t or f.name in 밟는다:
            continue
        인자 = [n.args[0].value for n in ast.walk(ast.parse(t))
               if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "add_argument"
               and n.args and isinstance(n.args[0], ast.Constant)]
        if any(str(x).lower().lstrip("-") in 낌새 for x in 인자):
            빠진.append(f"{f.name}  ({' '.join(str(x) for x in 인자)[:60]})")
    assert 빠진 == [], ("경로를 받는데 안 밟아 보는 도구가 있다 — `밟는다` 에 더한다:\n    "
                      + "\n    ".join(빠진))


def test_조사가_끝소리를_탄다():
    """★ 「점수 파일 **가** 없다」 로 적지 않는다 — 이 저장소는 그 셈을 이미 갖고 있다(H-013)."""
    for 무엇, 꼬리 in (("점수 파일", "파일이"), ("판", "판이"), ("원문 데이터", "데이터가")):
        with pytest.raises(SystemExit) as e:
            paths.읽는다(없는, 무엇, ("길",))
        assert str(e.value).splitlines()[0].startswith(f"{무엇[:-len(무엇.split()[-1])]}{꼬리}".strip() or 꼬리)


def test_길이_같이_나온다():
    """★ **막는 자리에는 넘는 길이 있어야 한다**(DECISIONS §210)."""
    with pytest.raises(SystemExit) as e:
        paths.읽는다(없는, "점수 파일", ("앞 단계가 끝났나 : tail /tmp/gemba.log", "둘째 길"))
    글 = str(e.value)
    assert "앞 단계가 끝났나" in 글 and "둘째 길" in 글


def test_디렉터리를_파일로_주면_그렇다고_말한다(tmp_path):
    """★ **「없다」 와 「파일이 아니다」 는 다른 실수다** — 같은 말을 하면 사람이 엉뚱한 데를 본다."""
    with pytest.raises(SystemExit) as e:
        paths.읽는다(tmp_path, "판", ("길",))
    assert "디렉터리다" in str(e.value)


def test_빈_파일은_그대로_돌려준다(tmp_path):
    """★ **밖 — 내용이 옳은지는 안 본다.** 「비었다」 를 어떻게 읽을지는 부르는 쪽의 일이다."""
    p = tmp_path / "a.jsonl"
    p.write_text("", encoding="utf-8")
    assert paths.읽는다(p, "판", ("길",)) == ""
    assert paths.줄들(p, "판", ("길",)) == []
