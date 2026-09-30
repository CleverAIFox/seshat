"""**적어 둔 의존성이 실제 의존성인가**(DECISIONS §257).

★ 이 파일은 **seshat 것**이다 — thoth 사본이 아니다(DECISIONS §5).
★ 2026-10-01 §254 가 「`transformers` 를 통째로 뺐다」 고 적었는데 **안 빠져 있었다.**
  선언과 자물쇠를 **둘 다** 본다 — 선언만 고치고 자물쇠를 안 고치면 **깔리는 것은 그대로다.**
"""
from __future__ import annotations

import pathlib

ROOT = next(p for p in pathlib.Path(__file__).resolve().parents if (p / "pyproject.toml").exists())
PYPROJECT = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
LOCK = (ROOT / "uv.lock").read_text(encoding="utf-8")

# ★ **안 들이기로 한 것**(DECISIONS §254 · §257). 들이려면 이 줄을 먼저 지우고, 지우는 판에서
#   **취약점 넷이 돌아온다는 것**을 절에 적는다(§251)
안들인다 = ("torch", "transformers")


def test_안_들이기로_한_것이_선언에_없다():
    """★ **§254 가 뺐다고 적은 것이 그대로 있었다.** 적은 것과 한 것을 가른다."""
    for x in 안들인다:
        assert f'"{x}' not in PYPROJECT and f"'{x}" not in PYPROJECT, \
            f"`{x}` 가 pyproject 에 남아 있다 — §254 는 뺐다고 적었다"


def test_안_들이기로_한_것이_자물쇠에도_없다():
    """★ **선언만 고치면 안 빠진다.** 실제로 깔리는 것을 정하는 것은 `uv.lock` 이고,
    GitHub 의 경보도 그것을 읽는다(§251 의 넷이 전부 `uv.lock` 에서 잡혔다)."""
    for x in 안들인다:
        assert f'name = "{x}"' not in LOCK, \
            f"`{x}` 가 uv.lock 에 남아 있다 — `uv lock` 을 안 돌렸다"


def test_기본_의존성은_0_이다():
    """★ **관문은 기본 의존성 0 으로 돈다**(DECISIONS §4)."""
    assert "dependencies = []" in PYPROJECT


def test_그룹이_문서와_맞는다():
    """★ 문서가 든 그룹이 실재한다 — README 가 `--group eval` 을 적고 있다."""
    for g in ("dev", "eval", "aws", "data"):
        assert f"\n{g} = [" in PYPROJECT, g
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "--group eval" in readme
    assert "--group qe" not in readme, "README 가 없는 그룹을 든다(§254 에서 뺐다)"
