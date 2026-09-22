"""평가 도구의 판정."""
import pytest

from seshat import evaluate as ev


@pytest.mark.parametrize("ko,want", [
    ("데이터를 직접 쿼리합니다.", True),
    ("무엇입니까?", True),
    ("먼저 확인하십시오.", True),
    ("데이터를 직접 쿼리해요.", False),
    ("무엇인가요?", False),
    ("S3 버킷", True),                 # 어미가 없는 명사구는 판정 밖이다
    ("첫 줄입니다.\n둘째 줄이에요.", False),   # 마지막 줄을 본다
])
def test_합쇼체_판정(ko, want):
    assert ev.is_hapsyo(ko) is want


def test_keep_은_영어가_남은_비율이다():
    rows = [{"src": "x", "keep": ["Amazon S3", "Athena"]}]
    assert ev.score(rows, ["Amazon S3에 저장합니다."])["keep"] == 0.5


def test_thoth_워커를_잴_때는_평가_출처를_싣는다():
    # ★ 평가 문장이 학습 쌍에 섞이면 평가가 거짓말을 한다.
    b = ev.request_body(["a"], thoth=True)
    assert b["source"]["site"].endswith(".local")
    assert "terms" not in b


def test_모델_서버에는_계약_그대로_보낸다():
    b = ev.request_body(["a"], thoth=False)
    assert set(b) == {"texts", "source", "target", "terms"}


def test_끝까지_돈다(server, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    import pathlib
    seed = pathlib.Path(__file__).resolve().parents[1] / "data/eval/seed.jsonl"
    assert ev.main(["--url", server(), "--set", str(seed), "--name", "t"]) == 0
    assert len(list((tmp_path / "runs").glob("t-*.jsonl"))) == 1
