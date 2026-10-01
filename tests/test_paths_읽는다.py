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
셋 = "data/domain/d002.jsonl"

# ★ **경로를 받는 도구와 그것을 밟는 인자.** 아래 시험이 이 표가 **빠짐없는지**까지 묻는다
밟는다: dict[str, list[str]] = {
    "bootstrap.py": [없는, 없는, "--set", 셋],
    "compare_runs.py": [없는, 없는, "--set", 셋],
    "gemba.py": ["--run", f"x={없는}", "--out", "/tmp/_o.jsonl"],
    "qe.py": ["--run", f"x={없는}", "--out", "/tmp/_o.jsonl"],
    "rescore.py": [없는],
    "show_misses.py": [없는],
    "slice.py": [없는, "--set", 셋],
    "style_na.py": [없는],
    "term_diff.py": [없는, 없는],
    "noise.py": [없는],
    "mine_terms.py": [없는],
    "gate.py": [없는],
    "labels.py": ["corr", "--set", 없는],
    "lake.py": ["check"],
}


@pytest.mark.parametrize("도구", sorted(밟는다))
def test_없는_파일에_맨몸으로_안_죽는다(도구):
    """★ 2026-10-01 **열넷 중 일곱**이 역추적과 「도구가 깨졌다」 를 뱉었다(DECISIONS §270).

    `gemba` 가 아직 도는 중인데 `bootstrap --점수` 를 부른 것이 그 자리였다 — **도구는 멀쩡한데
    「제가 깨졌다」 고 말하고 `verify.sh` 로 고치라고 했다.** 고칠 것이 없는데.
    """
    r = subprocess.run([sys.executable, f"tools/{도구}", *밟는다[도구]],
                       cwd=ROOT, capture_output=True, text=True, timeout=90)
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
