"""**강제자라고 선언한 함수가 제 밖을 적었나** — 그 검사가 살아 있는가(DECISIONS §267).

★ 이 파일은 **seshat 것**이다 — thoth 사본이 아니다(DECISIONS §5).
★ 양성과 음성을 함께 본다. 밖을 안 적은 강제자는 **걸리고**, 적은 것은 안 걸린다.
"""
from __future__ import annotations

import importlib.util
import pathlib

ROOT = next(p for p in pathlib.Path(__file__).resolve().parents if (p / "tools/check_claims.py").exists())
_spec = importlib.util.spec_from_file_location("cc", ROOT / "tools/check_claims.py")
CC = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CC)

글머리 = '"""머리말.\n\n{밖}\n"""'


def _나무(tmp_path: pathlib.Path, 코드: str, 강제자: str) -> pathlib.Path:
    for d in ("seshat", "tools", "docs/why"):
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    (tmp_path / "seshat/a.py").write_text(코드, encoding="utf-8")
    (tmp_path / "docs/why/DECISIONS.md").write_text(f"강제자 — {강제자}\n", encoding="utf-8")
    return tmp_path


def test_저장소가_장부와_맞는다():
    """★ **라쳇이다** — `main` 처럼 밖이 없는 것이 맞는 자리가 있다(DECISIONS §233 · §267)."""
    난것 = {자리 for 자리, _ in CC.안한것()}
    assert 난것 <= CC.장부, f"늘었다 — {sorted(난것 - CC.장부)}"


def test_카나리아가_산다():
    """★ **카나리아를 `pass` 로 바꿔도 통과하면 그 시험이 죽은 것이다**(DECISIONS §255)."""
    import inspect
    assert CC._canary() is None
    assert "sys.exit(2)" in inspect.getsource(CC._canary)


def test_밖을_안_적으면_걸린다(tmp_path):
    t = _나무(tmp_path, 'def f():\n    """무엇을 보는지만 적는다."""\n', "`seshat/a.py::f`")
    난 = CC.안한것(t, (t / "docs/why/DECISIONS.md").read_text(encoding="utf-8"))
    assert len(난) == 1 and "밖을 안 적었다" in 난[0][1], 난


def test_밖을_적으면_안_걸린다(tmp_path):
    t = _나무(tmp_path, 'def f():\n    """잰다.\n\n    ★ **밖 — 뜻은 안 본다.**\n    """\n', "`seshat/a.py::f`")
    assert CC.안한것(t, (t / "docs/why/DECISIONS.md").read_text(encoding="utf-8")) == []


def test_모듈_머리말이_적어도_된다(tmp_path):
    """★ **파일 하나가 한 규칙인 자리가 많다** — `RESIDUE` 가 그렇다."""
    t = _나무(tmp_path, '"""이 파일은 꼴만 본다 — 뜻은 **안 본다**."""\n\n\ndef f():\n    """잰다."""\n',
              "`seshat/a.py::f`")
    assert CC.안한것(t, (t / "docs/why/DECISIONS.md").read_text(encoding="utf-8")) == []


def test_없는_함수를_강제자로_들면_걸린다(tmp_path):
    """★ **이름이 바뀌면 그 선언이 거짓이 된다** — 2026-10-01 §16 이 그 자리였다(§265)."""
    t = _나무(tmp_path, 'def g():\n    """잰다. 뜻은 **안 본다**."""\n', "`seshat/a.py::f`")
    난 = CC.안한것(t, (t / "docs/why/DECISIONS.md").read_text(encoding="utf-8"))
    assert len(난) == 1 and "함수가 없다" in 난[0][1], 난


def test_강제자_줄이_아니면_안_본다(tmp_path):
    """★ **선언한 것에만 책임을 묻는다** — 모든 함수에 밖을 요구하면 사람이 검사를 끈다(§213)."""
    t = _나무(tmp_path, 'def f():\n    """무엇을 보는지만."""\n', "없음")
    assert CC.안한것(t, "아무 줄 — `seshat/a.py::f`") == []


def test_라쳇은_줄어든_것을_실패로_안_읽는다():
    """★ **갚은 것은 잘한 일이지 실패가 아니다.**"""
    assert CC.견준다([], frozenset({"seshat/a.py::옛것"})) == []
    assert len(CC.견준다([("seshat/a.py::새것", "밖을 안 적었다")], frozenset())) == 1
