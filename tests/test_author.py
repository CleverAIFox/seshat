"""작성자 메일 검사(tools/check_author.py) — 가짜 주소는 막고 보통 주소는 통과시킨다."""
import importlib.util
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("check_author", ROOT / "tools/check_author.py")
CA = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CA)


def test_이력에_실제로_있는_가짜_주소_셋은_막힌다():
    assert [CA.갈수_있나(m) for m in ("c@x", "a@b", "t@t")] == [False, False, False]


def test_보통_주소는_통과한다():
    # 합성 값만 쓴다 — 실제 주소를 시험에 옮기지 않는다
    assert [CA.갈수_있나(m) for m in ("who@example.com", "a.b@mail.example.org", "noreply@example.co.kr")] == [True] * 3


def test_꼴이_깨진_것은_막힌다():
    assert [CA.갈수_있나(m) for m in ("", "no-at.example.com", "a@@b.com", "a b@c.com", "a@.com", "a@b.")] == [False] * 6


def test_ident_에서_메일을_뜬다():
    assert CA.메일을_뜬다("Some Name <who@example.com> 1700000000 +0900") == "who@example.com"
    assert CA.메일을_뜬다("<c@x> 1 +0900") == "c@x"
    assert CA.메일을_뜬다("메일이 없다") is None


def _돌린다(메일: str) -> subprocess.CompletedProcess:
    # git 이 합치는 값은 환경 변수가 이긴다 — 기계 설정과 무관하게 같은 답이 나온다
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": 메일}
    return subprocess.run([sys.executable, str(ROOT / "tools/check_author.py")],
                          cwd=ROOT, env=env, capture_output=True, text=True)


def test_도구는_가짜면_1_보통이면_0():
    assert _돌린다("c@x").returncode == 1
    r = _돌린다("who@example.com")
    assert r.returncode == 0 and "example.com" in r.stdout


def test_git_이_없으면_고장_2():
    # PATH 를 비워 git 을 못 부르게 한다 — 위반(1)과 고장(2)은 다른 말이다(§232)
    r = subprocess.run([sys.executable, str(ROOT / "tools/check_author.py")],
                       cwd=ROOT, env={"PATH": ""}, capture_output=True, text=True)
    assert r.returncode == 2 and "check_author" in r.stderr


def test_selftest_는_git_없이_산다():
    r = subprocess.run([sys.executable, str(ROOT / "tools/check_author.py"), "--selftest"],
                       cwd=ROOT, env={"PATH": ""}, capture_output=True, text=True)
    assert r.returncode == 0 and "판별식" in r.stdout
