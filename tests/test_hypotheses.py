"""가설 대장의 문지기(DECISIONS §12). 양성과 음성을 함께 본다."""
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("ch", ROOT / "tools/check_hypotheses.py")
ch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ch)

GOOD = """| H | 상태 | 트랙 | 직관 | 검증 | 상한 | 근거 |
|---|---|---|---|---|---|---|
| H-001 | 제안 | R2 | 자리표시가 누설을 없앤다 | | | |
| H-004 | 실험 | R7 | 재정렬이 이긴다 | 100문장 · QE | 0 | |
| H-007 | 채택 | R1 | 불규칙이 몰린다 | 코퍼스 | T4 2시간 | runs/a.jsonl |
"""


def test_카나리아가_산다():
    """★ **카나리아를 `pass` 로 바꿔도 통과하면 그 시험이 죽은 것이다**(DECISIONS §255).
    도는 것과 **판별식을 들고 있는 것**을 함께 본다."""
    import inspect
    assert ch._canary() is None            # 살아 있으면 조용히 돌아온다
    글 = inspect.getsource(ch._canary)
    assert "sys.exit(2)" in 글, "카나리아가 죽었을 때 **고장(2)으로 끝내야 한다**"


def test_실제_대장이_통과한다():
    assert ch.check(ch.LEDGER.read_text(encoding="utf-8")) == []


def test_깨끗한_대장은_통과한다():
    assert ch.check(GOOD) == []


@pytest.mark.parametrize("a,b,want", [
    ("| H-004 | 실험 | R7 | 재정렬이 이긴다 | 100문장 · QE | 0 |", "| H-004 | 실험 | R7 | 재정렬이 이긴다 | | 0 |", "검증 방법 없이"),
    ("| 100문장 · QE | 0 |", "| 100문장 · QE | 적당히 |", "형식 밖"),
    ("| T4 2시간 | runs/a.jsonl |", "| T4 2시간 | 좋아 보인다 |", "근거가 없다"),
    ("| H-007 |", "| H-001 |", "겹친다"),
    ("| H-004 | 실험 | R7", "| H-004 | 진행 | R7", "어휘 밖"),
    ("| H-001 | 제안 | R2", "| H-001 | 제안 | R8", "R1–R7 밖"),
])
def test_규칙마다_걸린다(a, b, want):
    bad = GOOD.replace(a, b)
    assert bad != GOOD
    assert any(want in f for f in ch.check(bad)), ch.check(bad)


def test_제안은_검증_없이도_된다():
    # ★ 직관은 공짜다. 문은 실험에 들어갈 때 닫힌다.
    assert ch.check(GOOD.splitlines()[0] + "\n" + GOOD.splitlines()[1] + "\n| H-001 | 제안 | R3 | 무엇 | | | |\n") == []


NEW = """| H | 상태 | 트랙 | 직관 | 검증 | 상한 | 근거 |
|---|---|---|---|---|---|---|
| H-090 | 실험 | R7 | 무엇 | 600줄 · **미리 긋는 선: 구간이 0 을 안 품으면 채택** · `tools/bootstrap.py` | 0 | |
"""


def test_문턱_위는_선과_자를_둘_다_요구한다():
    """★ **선을 그으면서 재는 자를 안 적으면 그 선은 못 긋는다**(DECISIONS §226).

    H-081 이 「95% 구간」 을 그어 놓고 구간을 낼 줄 모르는 도구를 적었고, **돌리기 직전에야** 드러났다.
    """
    assert ch.check(NEW) == []
    없선 = NEW.replace("**미리 긋는 선: 구간이 0 을 안 품으면 채택** · ", "")
    assert any("미리 긋는 선이 없다" in f for f in ch.check(없선)), ch.check(없선)
    없자 = NEW.replace(" · `tools/bootstrap.py`", "")
    assert any("선을 잴 도구가 없다" in f for f in ch.check(없자)), ch.check(없자)


def test_문턱_아래는_소급하지_않는다():
    """★ 마흔넷이 미리 긋는 선 없이 닫혔다 — 하루에 다 고치는 것은 거짓말이다(`check_ways` 라쳇)."""
    옛 = NEW.replace("| H-090 | 실험", f"| H-{ch.선_부터 - 1:03d} | 실험").replace(
        "600줄 · **미리 긋는 선: 구간이 0 을 안 품으면 채택** · `tools/bootstrap.py`", "600줄을 돌린다")
    assert ch.check(옛) == [], ch.check(옛)


def test_문턱은_내려가지_않는다():
    """★ 문턱을 내리면 옛 줄이 한꺼번에 붉어지고, 그러면 **규칙을 끄게 된다**(§213 과 같은 판단)."""
    assert ch.선_부터 == 77
