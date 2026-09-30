"""**MASTER 의 규칙 번호**(DECISIONS §230 — 옛 PLAN 43행을 닫았다).

★ 이 파일도 `tools/check_rules.py` 도 **seshat 것**이다. `tools/check_docs.py` 와
  `tests/test_doc_enforcers.py` 는 thoth 사본이라 거기 넣으면 **다음 복사가 지운다**(DECISIONS §5).
★ 양성과 음성을 함께 본다 — 깨끗한 문서가 통과하는가, 그리고 **규칙마다 하나씩 어긴 문서가
  그 규칙으로 걸리는가.**
"""
from __future__ import annotations

import importlib.util
import pathlib

ROOT = next(p for p in pathlib.Path(__file__).resolve().parents if (p / "tools/check_rules.py").exists())
_spec = importlib.util.spec_from_file_location("cr", ROOT / "tools/check_rules.py")
CR = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CR)

GOOD = """# m

## 0. 서술 규약

★ §0-1 **첫 규칙이다.**

## 3. 평가

★ §3-1 **셋째 절의 첫 규칙.**
★ §3-2 **둘째.**
★ §3-9 **결번은 정상이다** — 번호는 영구 식별자다.
"""


def _번호(글: str) -> list[str]:
    """번호만 본다 — 가리킨 참조는 `_가리킴` 이 본다."""
    fails: list[str] = []
    CR.규칙들(글, fails)
    return fails


def _가리킴(tmp_path: pathlib.Path, 글: str) -> list[str]:
    """`tmp_path` 안의 작은 문서 하나가 가리킨 것만 본다 — 저장소 문서를 안 읽는다."""
    (tmp_path / "docs/now").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs/now/x.md").write_text(글, encoding="utf-8")
    옛 = CR.DOCS
    CR.DOCS = ("docs/now/x.md",)
    try:
        return CR.check(GOOD, tmp_path)
    finally:
        CR.DOCS = 옛


def test_깨끗한_문서는_통과한다():
    assert _번호(GOOD) == []


def test_실제_MASTER_가_통과한다():
    assert CR.check((ROOT / "docs/now/MASTER.md").read_text(encoding="utf-8"), ROOT) == []


def test_카나리아가_산다():
    """★ **카나리아를 `pass` 로 바꿔도 통과하면 그 시험이 죽은 것이다**(DECISIONS §255).
    도는 것과 **판별식을 들고 있는 것**을 함께 본다."""
    import inspect
    assert CR._canary() is None            # 살아 있으면 조용히 돌아온다
    글 = inspect.getsource(CR._canary)
    assert "sys.exit(2)" in 글, "카나리아가 죽었을 때 **고장(2)으로 끝내야 한다**"


def test_번호_없는_규칙이_걸린다():
    bad = GOOD.replace("★ §3-2 **둘째.**", "★ **둘째.**")
    assert any("번호가 없다" in f for f in _번호(bad)), _번호(bad)


def test_겹치는_번호가_걸린다():
    bad = GOOD.replace("★ §3-2 **둘째.**", "★ §3-1 **둘째.**")
    assert any("겹친다" in f for f in _번호(bad)), _번호(bad)


def test_거꾸로_가는_번호가_걸린다():
    bad = GOOD.replace("★ §3-9 **결번은", "★ §3-1 **결번은")
    assert any("겹친다" in f or "오름차순" in f for f in _번호(bad)), _번호(bad)


def test_남의_절_번호를_단_규칙이_걸린다():
    bad = GOOD.replace("★ §3-2 **둘째.**", "★ §4-2 **둘째.**")
    assert any("절 번호가 다르다" in f for f in _번호(bad)), _번호(bad)


def test_결번은_안_걸린다():
    """★ **연속을 요구하지 않는다.** 규칙 하나를 지울 때마다 뒤가 다 밀리면 **가리키던 글이 전부
    딴 것을 가리킨다** — 번호는 자산이다(`docs/README.md`)."""
    assert "3-9" in GOOD and _번호(GOOD) == []


def test_코드_울타리_안의_별은_규칙이_아니다():
    """세면 명령 예시가 규칙이 된다 — MASTER §14 의 주석이 전부 걸린다."""
    assert _번호(GOOD + "\n```\nls   # ★ 이것은 주석이다\n```\n") == []


def test_없는_규칙을_가리키면_걸린다(tmp_path):
    """★ **번호를 박는 값은 가리킬 수 있다는 것**이다 — 가리킨 곳이 없으면 번호가 거짓말을 한다."""
    got = _가리킴(tmp_path, "여기서 MASTER §3-77 을 가리킨다\n")
    assert any("MASTER §3-77" in f for f in got), got


def test_있는_규칙을_가리키면_안_걸린다(tmp_path):
    assert _가리킴(tmp_path, "여기서 MASTER §3-9 를 가리킨다\n") == []


def test_남의_저장소_번호는_안_본다(tmp_path):
    """★ **남의 저장소는 이름을 앞에 적는다**(`docs/README.md`). `파이어레인 MASTER §18-1a` 는
    이쪽 규칙이 아니고, 이쪽 대장으로 검사하면 영영 못 맞춘다."""
    assert _가리킴(tmp_path, "파이어레인 MASTER §18-1 과 thoth MASTER §7-4 를 든다\n") == []
