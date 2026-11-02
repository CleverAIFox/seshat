"""워크플로가 기대는 GitHub 설정(tools/check_gh.py, DECISIONS §331) — 선언·값·종료 코드를 가른다."""
import importlib.util
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("check_gh", ROOT / "tools/check_gh.py")
CG = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CG)

_표 = {("a.yml", "gh pr create"): [("actions/permissions/workflow", "can_approve_pull_request_reviews",
                                    True, "까닭")]}
_글 = "      - run: |\n          gh pr create --base main\n"


def test_실제_워크플로의_쓰임에_선언이_다_있다():
    assert CG.선언_점검(CG.워크플로들()) == []


def test_papers_가_PR_을_여는_것이_선언돼_있다():
    assert (".github/workflows/papers.yml", "gh pr create") in CG.선언


@pytest.mark.parametrize("꼴", [
    "gh pr create --base main", "gh pr merge 3 --squash",
    "uses: peter-evans/create-pull-request@" + "a" * 40, "gh api -X PUT repos/x/y",
    "gh api repos/x/y --method PATCH", "gh api \\\n  -X DELETE repos/x/y"])
def test_쓰임_꼴을_뽑는다(꼴):
    assert CG.쓰임들(f"      - run: |\n          {꼴}\n") != []


def test_읽기만_하는_gh_api_는_쓰임이_아니다():
    assert CG.쓰임들("      - run: gh api repos/x/y/actions/runs\n") == []


def test_주석에_적힌_쓰임은_안_센다():
    assert CG.쓰임들("      # gh pr create 가 실패했다\n      - run: echo\n") == []


def test_선언_없는_쓰임은_운다():
    난것 = CG.선언_점검({"new.yml": _글}, {})
    assert len(난것) == 1 and "new.yml" in 난것[0]


def test_쓰임_없는_낡은_선언은_운다():
    assert len(CG.선언_점검({"a.yml": "      - run: echo\n"}, _표)) == 1


def test_맞는_값은_0():
    assert CG.견준다(_표, lambda e: {"can_approve_pull_request_reviews": True})[0] == 0


def test_틀린_값은_1_이고_까닭을_든다():
    rc, 말 = CG.견준다(_표, lambda e: {"can_approve_pull_request_reviews": False})
    assert rc == 1 and "까닭" in "\n".join(말) and "False" in "\n".join(말)


def test_1_은_True_가_아니다():
    assert CG.견준다(_표, lambda e: {"can_approve_pull_request_reviews": 1})[0] == 1


def test_권한이_없으면_3_이다_어긋남이_아니다():
    def 막힘(e):
        raise CG.못쟀다("HTTP 403")
    assert CG.견준다(_표, 막힘)[0] == 3


def test_응답에_필드가_없으면_3_이다():
    assert CG.견준다(_표, lambda e: {})[0] == 3


def test_gh_가_없으면_CLI_가_3_으로_끝난다():
    r = subprocess.run([sys.executable, str(ROOT / "tools/check_gh.py")], cwd=ROOT,
                       env={"PATH": ""}, capture_output=True, text=True)
    assert r.returncode == 3 and "`gh` 가 없다" in r.stdout + r.stderr


def test_static_은_망_없이_산다():
    r = subprocess.run([sys.executable, str(ROOT / "tools/check_gh.py"), "--static"], cwd=ROOT,
                       env={"PATH": ""}, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_카나리아():
    assert CG._selftest() == 0


def test_선언_비교를_뒤집으면_카나리아가_운다(monkeypatch, capsys):
    """★ 판별식을 돌연변이로 문다 — 견줌이 늘 0 을 돌려주면 `_selftest` 가 2 여야 한다."""
    monkeypatch.setattr(CG, "견준다", lambda 표, 읽는다: (0, []))
    assert CG._selftest() == 2
    assert "판별식이 거꾸로다" in capsys.readouterr().err


# ───────── `gh` 를 갈아 끼워 실제로 읽는 길을 건다 ─────────

def _가짜_gh(tmp_path, 몸: str) -> dict:
    """PATH 맨 앞에 가짜 `gh` 를 둔다 — 망 없이 `읽는다` · `_저장소` 를 끝까지 탄다."""
    (tmp_path / "gh").write_text("#!/bin/sh\n" + 몸, encoding="utf-8")
    (tmp_path / "gh").chmod(0o755)
    import os
    return {**os.environ, "PATH": f"{tmp_path}:{os.environ['PATH']}"}


_정상 = ('if [ "$1 $2" = "repo view" ]; then echo owner/repo; exit 0; fi\n'
       'echo \'{"can_approve_pull_request_reviews": %s, "has_issues": true}\'\n')


def _cli(env):
    return subprocess.run([sys.executable, str(ROOT / "tools/check_gh.py")], cwd=ROOT, env=env,
                          capture_output=True, text=True)


def test_읽는_길_끝까지_맞으면_0(tmp_path):
    r = _cli(_가짜_gh(tmp_path, _정상 % "true"))
    assert r.returncode == 0 and "맞다" in r.stdout


def test_읽는_길_끝까지_틀리면_1(tmp_path):
    r = _cli(_가짜_gh(tmp_path, _정상 % "false"))
    assert r.returncode == 1 and "False" in r.stdout


def test_읽는_길_403_이면_3(tmp_path):
    env = _가짜_gh(tmp_path, 'if [ "$1 $2" = "repo view" ]; then echo o/r; exit 0; fi\n'
                  'echo "gh: Resource not accessible (HTTP 403)" >&2; exit 1\n')
    r = _cli(env)
    assert r.returncode == 3 and "HTTP 403" in r.stdout + r.stderr


def test_읽는_길_JSON_이_아니면_3(tmp_path):
    r = _cli(_가짜_gh(tmp_path, 'if [ "$1 $2" = "repo view" ]; then echo o/r; exit 0; fi\necho nope\n'))
    assert r.returncode == 3 and "JSON" in r.stdout + r.stderr


def test_저장소_이름을_못_읽으면_3(tmp_path):
    r = _cli(_가짜_gh(tmp_path, 'echo "no repo" >&2; exit 1\n'))
    assert r.returncode == 3 and "저장소 이름" in r.stdout + r.stderr


def test_읽을_때_저장소와_끝점을_붙여_부른다(tmp_path):
    로그 = tmp_path / "calls"
    몸 = (f'echo "$@" >> {로그}\n' + _정상 % "true")
    _cli(_가짜_gh(tmp_path, 몸))
    부름 = 로그.read_text(encoding="utf-8")
    assert "api repos/owner/repo/actions/permissions/workflow" in 부름
    assert "api repos/owner/repo\n" in 부름          # 끝점이 빈 선언은 저장소 자체를 읽는다
