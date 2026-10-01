"""사본을 세는 도구가 제구실을 하나(DECISIONS §163 · §171)."""
from __future__ import annotations

import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("dupcheck", ROOT / "tools/dupcheck.py")
D = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(D)

def test_인자가_갈리는_부름을_센다(tmp_path, monkeypatch):
    """★ **2026-09-28 의 아홉 번째 병은 함수도 글자도 아니었다**(DECISIONS §171 · §169).
    `compare.갈림(rec, head, X)` 의 `X` 가 곳마다 달랐고, 앞의 두 탐지기는 그것을 못 봤다."""
    (tmp_path / "가.py").write_text("c.갈림(a, b, ('자',))\nc.갈림(a, b, 막)\n", encoding="utf-8")
    (tmp_path / "나.py").write_text("c.같다(a, b)\nc.같다(a, b)\nxs.append(1)\nxs.append(2)\n",
                                   encoding="utf-8")
    monkeypatch.setattr(D, "ROOT", tmp_path)
    got = D.부름_갈림((".",))
    assert "c.갈림" in got and len(got["c.갈림"]) == 2
    assert "c.같다" not in got, "인자가 같으면 사본이 아니라 쓰임이다"
    assert "xs.append" not in got, "담개는 원래 곳마다 다른 것을 받는다"


def test_꼴이_너무_많으면_다목적_도구다(tmp_path, monkeypatch):
    """★ 갈려서 병이 나는 자리는 **두엇**으로 갈린다. 아흔세 꼴은 사본이 아니라 쓰임이다."""
    (tmp_path / "가.py").write_text("\n".join(f"m.무엇({i})" for i in range(12)) + "\n",
                                   encoding="utf-8")
    monkeypatch.setattr(D, "ROOT", tmp_path)
    assert "m.무엇" not in D.부름_갈림((".",), 최대꼴=8)
    assert "m.무엇" in D.부름_갈림((".",), 최대꼴=20)


def test_이_저장소의_문이_갈리는_자리로_잡힌다():
    """★ **프로브가 진짜 병을 잡나.** 손으로 만든 예제만 잡는 탐지기는 살아 있는지 알 수 없다 —
    §169 를 만든 그 자리가 지금도 목록에 있어야 한다(축을 하나로 모았으니 꼴은 줄었다)."""
    got = D.부름_갈림(("seshat", "tools"))
    assert "compare.갈림" in got, "문의 축 부름이 안 잡힌다 — 탐지기가 죽었다"


# ── 같은 정규식이 파일을 넘나(DECISIONS §266) ─────────────────────────────────

def test_같은_정규식이_파일을_안_넘는다():
    """★ **절대 규칙이다** — 같은 뜻의 정규식이 두 파일에 있으면 **한 곳만 고쳐진다**(§163).

    2026-10-01 `tools/compare_runs.py` 가 `seshat/terms.py` 의 자리표시 정규식을 베꼈고
    **열흘 살았다**(§263). 글자 사본으로는 못 잡혔다 — 원본이 f-string 이라 글자가 다르다.
    """
    난것, 못본 = D.같은_정규식(("seshat", "tools"))
    assert 못본 == [], f"**못 들인 파일은 0 이 아니다**(§172 · §258) — {못본}"
    assert 난것 == {}, 난것


def test_들여_쓰는_것은_사본이_아니다(tmp_path, monkeypatch):
    """★ **거짓 양성 하나가 검사를 끈다**(§213). 처음 짠 판이 `from … import RESIDUE` 를
    사본으로 들었다 — 두 모듈에 보이지만 **같은 물건**이다."""
    (tmp_path / "가").mkdir()
    (tmp_path / "가/원본.py").write_text(
        'import re\nPAT = re.compile(r"(?:⟦X(\\d+)⟧|\\[X(\\d+)\\])")\n', encoding="utf-8")
    (tmp_path / "나").mkdir()
    (tmp_path / "나/들여쓴다.py").write_text(
        "import sys; sys.path.insert(0, r'" + str(tmp_path / "가") + "')\nfrom 원본 import PAT  # noqa\n",
        encoding="utf-8")
    monkeypatch.setattr(D, "ROOT", tmp_path)
    난것, 못본 = D.같은_정규식(("가", "나"))
    assert 못본 == [], 못본
    assert 난것 == {}, "들여 쓴 것을 사본으로 들었다 — 물건이 하나다"


def test_손으로_베낀_것은_잡는다(tmp_path, monkeypatch):
    """★ **f-string 으로 짠 원본과 손으로 베낀 사본은 글자가 다르다** — 컴파일한 뒤라야 같다."""
    (tmp_path / "가").mkdir()
    (tmp_path / "가/원본.py").write_text(
        'import re\nL = "X"\nPAT = re.compile(rf"(?:⟦{L}(\\d+)⟧|\\[{L}(\\d+)\\])")\n', encoding="utf-8")
    (tmp_path / "나").mkdir()
    (tmp_path / "나/베꼈다.py").write_text(
        'import re\nPAT = re.compile(r"(?:⟦X(\\d+)⟧|\\[X(\\d+)\\])")\n', encoding="utf-8")
    monkeypatch.setattr(D, "ROOT", tmp_path)
    난것, 못본 = D.같은_정규식(("가", "나"))
    assert 못본 == [], 못본
    assert len(난것) == 1, 난것
    assert sorted(next(iter(난것.values()))) == ["가/원본.py::PAT", "나/베꼈다.py::PAT"]


def test_못_들인_파일을_0_으로_안_센다(tmp_path, monkeypatch, capsys):
    """★ **안 본 파일이 깨끗해 보이면 안 된다**(§172 · §258). 처음 짠 판이 `seshat/` 여섯을
    못 들이고 **「0 건」 을 찍었다** — 그 거짓 초록을 이 시험이 막는다."""
    (tmp_path / "가").mkdir()
    (tmp_path / "가/깨졌다.py").write_text("def f(:\n", encoding="utf-8")
    monkeypatch.setattr(D, "ROOT", tmp_path)
    난것, 못본 = D.같은_정규식(("가",))
    assert 못본 == ["가/깨졌다.py"], 못본
    assert "못 들였다" in capsys.readouterr().err


def test_별칭으로_베껴도_잡는다(tmp_path, monkeypatch):
    """★ **이름을 맞히는 검사는 별칭으로 뚫린다**(DECISIONS §266).

    처음 짠 판이 `re.compile` 이라는 **이름**을 찾았고, `import re as _r` 한 사본이 그 사이로
    샜다 — **고치자마자 그 구멍으로 사본을 되살려 보고** 알았다. 이제 「짓는가」 만 묻는다.
    """
    (tmp_path / "가").mkdir()
    (tmp_path / "가/원본.py").write_text(
        'import re\nL = "X"\nPAT = re.compile(rf"(?:⟦{L}(\\d+)⟧|\\[{L}(\\d+)\\])")\n', encoding="utf-8")
    (tmp_path / "나").mkdir()
    (tmp_path / "나/별칭.py").write_text(
        'import re as _r\nPAT = _r.compile(r"(?:⟦X(\\d+)⟧|\\[X(\\d+)\\])")\n', encoding="utf-8")
    monkeypatch.setattr(D, "ROOT", tmp_path)
    난것, 못본 = D.같은_정규식(("가", "나"))
    assert 못본 == [], 못본
    assert len(난것) == 1, 난것


def test_이름만_붙인_것은_사본이_아니다(tmp_path, monkeypatch):
    """★ `RESIDUE = terms.RESIDUE` 도 들여 쓰는 것이다 — **남이 지은 물건에 이름만 붙였다.**"""
    (tmp_path / "가").mkdir()
    (tmp_path / "가/원본.py").write_text(
        'import re\nPAT = re.compile(r"(?:⟦X(\\d+)⟧|\\[X(\\d+)\\])")\n', encoding="utf-8")
    (tmp_path / "나").mkdir()
    (tmp_path / "나/별명.py").write_text(
        "import sys; sys.path.insert(0, r'" + str(tmp_path / "가") + "')\n"
        "import 원본\nPAT = 원본.PAT\n", encoding="utf-8")
    monkeypatch.setattr(D, "ROOT", tmp_path)
    난것, 못본 = D.같은_정규식(("가", "나"))
    assert 못본 == [], 못본
    assert 난것 == {}, "이름만 붙인 것을 사본으로 들었다"
