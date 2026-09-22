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
    ch._canary()


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
