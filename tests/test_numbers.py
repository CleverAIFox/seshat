"""**결과 문서가 든 수에 근거가 있는가** — 그 검사가 살아 있는가(DECISIONS §235).

★ 이 파일은 **seshat 것**이다 — thoth 사본이 아니다(DECISIONS §5).
★ 양성과 음성을 함께 본다. 근거 없는 수를 **넣으면 걸리고**, 있는 수는 안 걸린다.
"""
from __future__ import annotations

import importlib.util
import pathlib

ROOT = next(p for p in pathlib.Path(__file__).resolve().parents if (p / "tools/check_numbers.py").exists())
_spec = importlib.util.spec_from_file_location("cn", ROOT / "tools/check_numbers.py")
CN = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CN)


def _나무(tmp_path: pathlib.Path, 결과: str, 근거글: str = "") -> pathlib.Path:
    for d in ("docs/now", "docs/why", "docs/next", "data"):
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    (tmp_path / CN.문서).write_text(결과, encoding="utf-8")
    (tmp_path / "docs/DECISIONS.md").write_text(근거글, encoding="utf-8")
    return tmp_path


def test_실제_저장소가_통과한다():
    assert CN.근거없는수() == []


def test_카나리아가_산다():
    """★ **카나리아를 `pass` 로 바꿔도 통과하면 그 시험이 죽은 것이다**(DECISIONS §255).
    도는 것과 **판별식을 들고 있는 것**을 함께 본다."""
    import inspect
    assert CN._canary() is None            # 살아 있으면 조용히 돌아온다
    글 = inspect.getsource(CN._canary)
    assert "sys.exit(2)" in 글, "카나리아가 죽었을 때 **고장(2)으로 끝내야 한다**"


def test_근거에_있는_수는_안_걸린다(tmp_path):
    t = _나무(tmp_path, "차 **+0.0739** 이다\n", "그 판에서 +0.0739 가 났다\n")
    assert CN.근거없는수(t) == []


def test_근거에_없는_수가_걸린다(tmp_path):
    """★ `+0.0739` 를 `+0.0793` 으로 잘못 치면 **아무도 안 울던 자리**다."""
    t = _나무(tmp_path, "차 **+0.0793** 이다\n", "그 판에서 +0.0739 가 났다\n")
    got = CN.근거없는수(t)
    assert [x[1] for x in got] == ["0.0793"], got
    assert got[0][0] == 1                                  # 줄 번호를 든다


def test_arXiv_번호는_수가_아니다(tmp_path):
    """★ `2310.0582` 를 지표로 읽으면 논문 표가 전부 걸린다 — 그러면 사람이 검사를 끈다."""
    t = _나무(tmp_path, "*Terminology…* (arXiv 2310.0582)\n", "")
    assert CN.근거없는수(t) == []


def test_수가_없으면_조용하다(tmp_path):
    assert CN.근거없는수(_나무(tmp_path, "수가 없는 줄이다\n", "")) == []


def test_기록판도_근거다():
    """★ 근거는 DECISIONS 만이 아니다 — 기록판의 값이 결과 문서에 실린다(`term_off` 0.9543)."""
    assert "data/scoreboard.toml" in CN.근거
    assert (ROOT / "data/scoreboard.toml").is_file()


def test_넘는_길을_든다(capsys):
    """★ 막는 자리는 **무엇을 하면 되는가**를 말한다(DECISIONS §210)."""
    import io
    import sys
    옛, sys.stderr = sys.stderr, io.StringIO()
    try:
        CN.main(["--list"])
        말 = sys.stderr.getvalue()
    finally:
        sys.stderr = 옛
    # 지금은 근거 없는 수가 0 이라 안 운다 — 울 때의 글이 길을 드는지는 소스로 본다
    글 = (ROOT / "tools/check_numbers.py").read_text(encoding="utf-8")
    assert "docs/DECISIONS.md" in 글 and "--list" in 글, 말
