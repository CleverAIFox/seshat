"""**검사가 죽어 있지 않은가** — 그 검사가 살아 있는가(DECISIONS §255).

★ 이 파일은 **seshat 것**이다 — thoth 사본이 아니다(DECISIONS §5).
★ 양성과 음성을 함께 본다. 죽은 검사는 **걸리고**, 산 검사는 안 걸린다.
"""
from __future__ import annotations

import importlib.util
import pathlib

ROOT = next(p for p in pathlib.Path(__file__).resolve().parents
            if (p / "tools/check_deadchecks.py").exists())
_spec = importlib.util.spec_from_file_location("cdc", ROOT / "tools/check_deadchecks.py")
DC = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(DC)


def _나무(tmp_path: pathlib.Path, 시험: str = "", 도구: str = "") -> pathlib.Path:
    for d in ("tests", "tools", "seshat"):
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    (tmp_path / "tests/test_x.py").write_text(시험 or "def test_산다():\n    assert 1\n", encoding="utf-8")
    (tmp_path / "tools/x.py").write_text(도구 or "def f():\n    return 1\n", encoding="utf-8")
    return tmp_path


def test_저장소가_장부와_맞는다():
    """★ **장부가 비었다 — 이제 절대 규칙이다**(DECISIONS §258).

    세운 판(§255)에서는 열둘이 있었고 「자리마다 판단이 다르다」 고 적었는데 **다 갚아 보니
    판단이 같았다** — 훑개도 건너뛴 수를 세어 사유에 실을 수 있었다. §233 의 규칙대로,
    판단이 같으면 라쳇을 미루는 것이 곧 빚이다.
    """
    assert DC.장부 == frozenset()
    난것 = {a for a, _ in DC.죽은검사()}
    assert 난것 == set(), f"늘었다 — {sorted(난것)}"


def test_카나리아가_산다():
    """★ **카나리아를 `pass` 로 바꿔도 통과하면 그 시험이 죽은 것이다.**"""
    import inspect
    assert DC._canary() is None
    assert "sys.exit(2)" in inspect.getsource(DC._canary)


def test_무검증_시험이_걸린다(tmp_path):
    """★ **몸통을 지워도 통과하는 시험**은 시험이 아니다."""
    t = _나무(tmp_path, "def test_빈():\n    x = 1\n    print(x)\n")
    assert [a for a, _ in DC.죽은검사(t)] == ["tests/test_x.py::test_빈"]


def test_단언이_있으면_안_걸린다(tmp_path):
    t = _나무(tmp_path, "def test_찬():\n    assert 1 == 1\n")
    assert DC.죽은검사(t) == []


def test_raises_도_단언이다(tmp_path):
    t = _나무(tmp_path, "import pytest\n\n\ndef test_터진다():\n    with pytest.raises(ValueError):\n        raise ValueError\n")
    assert DC.죽은검사(t) == []


def test_삼킨_예외가_걸린다(tmp_path):
    """★ **고장이 자국을 안 남긴다** — §243 · §248 이 그 병이었다."""
    t = _나무(tmp_path, 도구="def f():\n    try:\n        g()\n    except Exception:\n        pass\n")
    assert [a for a, _ in DC.죽은검사(t)] == ["tools/x.py:4"]


def test_말을_하면_안_걸린다(tmp_path):
    """★ **건너뛰되 말을 한다** — 주석은 이 자가 못 읽는다."""
    t = _나무(tmp_path, 도구="def f():\n    try:\n        g()\n    except Exception as e:\n        print(e)\n")
    assert DC.죽은검사(t) == []


def test_건너뛴_시험이_걸린다(tmp_path):
    """★ **안 도는 시험은 없는 시험이다.**"""
    t = _나무(tmp_path, "import pytest\n\n\ndef test_x():\n    pytest.importorskip('없는것')\n    assert 1\n")
    난것 = DC.죽은검사(t)
    assert len(난것) == 1 and "건너뛴 시험" in 난것[0][1]


def test_빈_그물이_걸린다(tmp_path):
    """★ **돌긴 도는데 한 판도 안 돈다.**"""
    t = _나무(tmp_path, "import pytest\n\n\n@pytest.mark.parametrize('x', [])\ndef test_x(x):\n    assert x\n")
    난것 = DC.죽은검사(t)
    assert any("빈 그물" in 왜 for _, 왜 in 난것), 난것


def test_시험_밖에서는_무검증을_안_본다(tmp_path):
    """★ **밖** — `tools/` 의 함수는 시험이 아니다."""
    t = _나무(tmp_path, 도구="def test_흉내():\n    x = 1\n    print(x)\n")
    assert DC.죽은검사(t) == []


def test_죽은_이름과_다른_물음이다():
    """★ **§240 이 이름만 같은 도구를 옮겼다**(DECISIONS §255). 둘은 다른 것을 센다."""
    글 = (ROOT / "tools/check_deadchecks.py").read_text(encoding="utf-8")
    assert "check_dead.py" in 글 and "다른 물음" in 글
    다른 = importlib.util.spec_from_file_location("cd2", ROOT / "tools/check_dead.py")
    CD = importlib.util.module_from_spec(다른)
    다른.loader.exec_module(CD)
    assert CD.죽은이름() == [] and DC.죽은검사() == []          # 저장소는 양쪽 다 0 이다(§258)
    # ★ **0 이 같다고 같은 물음이 아니다** — 한쪽만 잡는 나무를 지어서 가른다. 저장소가 둘 다 0 이
    #   된 뒤로(§258) 실물로는 못 가른다
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        t = _나무(pathlib.Path(d), 도구="def f():\n    try:\n        f()\n    except OSError:\n        pass\n")
        (t / "tests/test_x.py").write_text("from tools.x import f\n\n\ndef test_산다():\n    assert f\n",
                                           encoding="utf-8")
        assert CD.죽은이름(t) == [], CD.죽은이름(t)              # 이름은 다 불린다
        assert [a for a, _ in DC.죽은검사(t)] == ["tools/x.py:4"], DC.죽은검사(t)   # 검사는 죽어 있다
