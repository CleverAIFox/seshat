"""**문서가 드는 수를 도구가 채운다** — 그 검사가 살아 있는가(DECISIONS §237).

★ 이 파일은 **seshat 것**이다 — thoth 사본이 아니다(DECISIONS §5).
★ 양성과 음성을 함께 본다. 틀린 수는 **걸리고**, 앵커가 0 곳이거나 둘 이상이면 **멈춘다.**
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

ROOT = next(p for p in pathlib.Path(__file__).resolve().parents if (p / "tools/docgen.py").exists())
_spec = importlib.util.spec_from_file_location("dg", ROOT / "tools/docgen.py")
DG = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(DG)

표 = """## 15. 어디까지 왔나

| 단계 | 비중 | 지금 | 근거 |
|---|---|---|---|
| ① 재는 체계 | 20% | **80%** | x |
| ② 기준선 | 20% | 85% | x |
| ③ 학습 데이터 | 20% | 5% | x |
| ④ 학습 | 25% | 0% | x |
| ⑤ 서빙 | 15% | 10% | x |

**합 35%**(2026-09-30).
"""


def _놓는다(tmp_path, master=표, plan="절 **97** 개가 「찍은 뒤에 바뀐 코드」 를 짚는다\n"):
    for d in ("docs/now", "docs/next"):
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs/MASTER.md").write_text(master, encoding="utf-8")
    (tmp_path / "docs/PLAN.md").write_text(plan, encoding="utf-8")
    return tmp_path


def test_실제_저장소가_통과한다():
    assert DG.견준다() == []


def test_진행률은_표에서_나온다(tmp_path, monkeypatch):
    monkeypatch.setattr(DG, "ROOT", tmp_path)
    _놓는다(tmp_path)
    assert DG.진행률() == 35                      # 0.20·80 + 0.20·85 + 0.20·5 + 0.25·0 + 0.15·10 = 35.5


def test_진행률은_올림하지_않는다(tmp_path, monkeypatch):
    """★ **진행률은 과장되는 쪽으로 틀리면 안 된다**(DECISIONS §237). 35.5 는 36 이 아니라 35 다."""
    monkeypatch.setattr(DG, "ROOT", tmp_path)
    _놓는다(tmp_path)
    assert DG.진행률() == 35 and round(35.5) == 36    # 반올림이면 36 이 됐을 자리다


def test_비중이_100_이_아니면_멈춘다(tmp_path, monkeypatch):
    monkeypatch.setattr(DG, "ROOT", tmp_path)
    _놓는다(tmp_path, master=표.replace("| ⑤ 서빙 | 15% |", "| ⑤ 서빙 | 25% |"))
    with pytest.raises(SystemExit, match="비중의 합"):
        DG.진행률()


def test_표가_사라지면_멈춘다(tmp_path, monkeypatch):
    """★ **정본이 죽으면 0 이 아니라 실패다** — 0 은 「다 갚았다」 가 아니라 「못 셌다」 다."""
    monkeypatch.setattr(DG, "ROOT", tmp_path)
    _놓는다(tmp_path, master="## 15. 어디까지 왔나\n\n**합 35%**\n")
    with pytest.raises(SystemExit, match="정본이 죽었다"):
        DG.진행률()


def test_앵커가_없으면_멈춘다(tmp_path, monkeypatch):
    """★ **못 찾은 초록은 「깨끗하다」 가 아니라 「안 봤다」 다.**"""
    monkeypatch.setattr(DG, "ROOT", tmp_path)
    _놓는다(tmp_path, master=표.replace("**합 35%**", "합이 안 적힌 절이다"))
    with pytest.raises(SystemExit, match="0 곳 잡혔다"):
        DG.견준다()


def test_앵커가_둘이면_멈춘다(tmp_path, monkeypatch):
    """★ **정본이 둘이면 한쪽만 고쳐진다** — 2026-09-30 PLAN 47행이 그 「둘」 이었다."""
    monkeypatch.setattr(DG, "ROOT", tmp_path)
    _놓는다(tmp_path, master=표 + "\n다시 적으면 **합 35%** 다\n")
    with pytest.raises(SystemExit, match="2 곳 잡혔다"):
        DG.견준다()


def test_틀린_수가_걸리고_fix_가_고친다(tmp_path, monkeypatch):
    # ★ **진행률 축만 본다**(DECISIONS §281). 합성 MASTER 에는 온톨로지 표도 라이선스
    #   문장도 없으므로, 전부 보게 하면 엉뚱한 축의 「앵커 0 곳」 으로 멈춘다 —
    #   그러면 이 시험이 보려던 `--fix` 를 못 본다. 축이 하나였을 때는 같은 말이었다.
    monkeypatch.setattr(DG, "ROOT", tmp_path)
    _놓는다(tmp_path, master=표.replace("**합 35%**", "**합 99%**"))
    안맞 = DG.견준다({"진행률"})
    assert ("진행률", 99, 35) in 안맞, 안맞
    DG.고친다({"진행률"})
    assert DG.견준다({"진행률"}) == []
    assert "**합 35%**" in (tmp_path / "docs/MASTER.md").read_text(encoding="utf-8")


def test_게이트는_축을_골라_보지_않는다():
    """★ **부분 실행을 허락하면 축을 빼고 통과시킬 수 있다**(DECISIONS §281).

    `고를` 은 시험만 쓰는 손잡이다. `main()` 이 그것을 넘기면 CI 에서 축 하나를
    끄고 초록을 받을 길이 생긴다 — 그 길이 없는지를 여기서 못 박는다.
    """
    몸 = (ROOT / "tools/docgen.py").read_text(encoding="utf-8")
    머리 = 몸[몸.index("def main("):]
    assert "견준다()" in 머리 and "견준다(고를" not in 머리, "main() 이 축을 골라 본다"


def test_축마다_앵커가_실제로_한_곳이다():
    """★ 축을 더하면서 앵커 표기를 안 맞추면 `견준다` 가 **멈추지 않고** 0 곳에서
    조용히 지나갈 길은 없다 — 그래도 축이 전부 실재하는지는 따로 못 박는다."""
    for 이름, (_, 자리, 앵커) in DG.축.items():
        글 = (ROOT / 자리).read_text(encoding="utf-8")
        assert len(앵커.findall(글)) == 1, f"{이름} 의 앵커가 {자리} 에서 한 곳이 아니다"


def test_커밋이_흔드는_수는_축이_아니다():
    """★ **채워 넣을 수 있는 수는 커밋이 안 흔드는 수다**(DECISIONS §238).

    `docseal audit` 의 수를 축으로 세웠다가 물렸다 — 그 수를 적는 커밋이 파일을 건드리면서
    수를 바꾸므로 **고정점이 한 커밋 안에 없다.**
    """
    assert "다시봐야할절" not in DG.축
    plan = (ROOT / "docs/PLAN.md").read_text(encoding="utf-8")
    assert "개가 「찍은 뒤에 바뀐 코드」" not in plan, "PLAN 이 그 수를 다시 들었다"
    assert "docseal.py audit" in plan, "그 수를 어디서 보는지가 빠졌다"
