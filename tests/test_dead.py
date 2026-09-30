"""**아무도 안 부르는 이름이 남아 있는가** — 그 검사가 살아 있는가(DECISIONS §240).

★ 이 파일은 **seshat 것**이다 — thoth 사본이 아니다(DECISIONS §5).
★ 양성과 음성을 함께 본다. 안 불리는 이름은 **걸리고**, 문서에만 적힌 이름은 안 걸린다.
"""
from __future__ import annotations

import importlib.util
import pathlib

ROOT = next(p for p in pathlib.Path(__file__).resolve().parents if (p / "tools/check_dead.py").exists())
_spec = importlib.util.spec_from_file_location("cd", ROOT / "tools/check_dead.py")
CD = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CD)


def _나무(tmp_path: pathlib.Path, 코드: str, 문서: str = "") -> pathlib.Path:
    for d in ("seshat", "tools", "tests", "docs/why"):
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    (tmp_path / "seshat/a.py").write_text(코드, encoding="utf-8")
    # ★ **부르는 자리를 놓아 둔다** — 안 그러면 fixture 의 이름이 전부 진짜로 죽는다
    (tmp_path / "tools/b.py").write_text("from seshat.a import 산다\n\n산다()\n", encoding="utf-8")
    (tmp_path / "docs/why/DECISIONS.md").write_text(문서, encoding="utf-8")
    return tmp_path


def test_저장소가_장부와_맞는다():
    """★ **장부는 절대 규칙이다** — 죽은 이름은 하나도 못 들어온다(DECISIONS §240)."""
    assert CD.장부 == frozenset()
    assert CD.죽은이름() == [], CD.죽은이름()


def test_카나리아가_산다():
    CD._canary()


def test_안_불리는_이름이_걸린다(tmp_path):
    t = _나무(tmp_path, "def 산다():\n    return 죽는다\n\n\ndef 죽는다():\n    return 1\n\n\ndef 아무도():\n    return 2\n")
    assert CD.죽은이름(t) == ["seshat/a.py::아무도"], CD.죽은이름(t)


def test_문서에_적힌_이름은_산_것이다(tmp_path):
    """★ **느슨한 쪽으로 둔다** — `getattr` 로 부르는 자리가 있고, 거짓 양성 하나가 검사를 끈다."""
    t = _나무(tmp_path, "def 아무도():\n    return 2\n", 문서="강제자 — `seshat/a.py::아무도`\n")
    assert CD.죽은이름(t) == []


def test_몸통_안의_이름은_안_본다(tmp_path):
    """★ **최상위만 본다** — 안쪽 함수는 제 몸통이 곧 쓰임이라 이 셈이 안 맞는다."""
    t = _나무(tmp_path, "def 산다():\n    def 안쪽():\n        return 1\n    return 안쪽()\n")
    assert CD.죽은이름(t) == []


def test_던더는_안_본다(tmp_path):
    t = _나무(tmp_path, "class C:\n    pass\n\n\ndef __getattr__(n):\n    return C\n")
    assert CD.죽은이름(t) == []


def test_클래스도_본다(tmp_path):
    t = _나무(tmp_path, "class 아무도아는:\n    pass\n")
    assert CD.죽은이름(t) == ["seshat/a.py::아무도아는"]


def test_라쳇은_줄어든_것을_실패로_안_읽는다():
    """★ **지운 것은 잘한 일이지 실패가 아니다.**"""
    assert CD.견준다([], frozenset({"seshat/a.py::옛것"})) == []
    assert len(CD.견준다(["seshat/a.py::새것"], frozenset())) == 1


def test_깨진_파일이_도구를_안_죽인다(tmp_path):
    """★ **못 읽는 파일 하나가 검사 전체를 역추적으로 끝내면 사람이 검사를 끈다**(DECISIONS §232)."""
    t = _나무(tmp_path, "def 산다(:\n")
    assert CD.죽은이름(t) == []
