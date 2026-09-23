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
    assert ev.main(["--url", server(), "--set", str(seed), "--name", "t", "--smoke"]) == 0
    assert len(list((tmp_path / "runs").glob("t-*.jsonl"))) == 1


def test_백엔드를_서버_없이_부른다(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    p = tmp_path / "s.jsonl"
    p.write_text('{"id": "a", "src": "Hello.", "ref": "안녕하세요."}\n', encoding="utf-8")
    assert ev.main(["--backend", "echo", "--set", str(p)]) == 0
    head = (tmp_path / "runs").glob("*.jsonl").__next__().read_text(encoding="utf-8").splitlines()[0]
    assert '"backend:echo"' in head and '"seshat-echo"' in head


def test_가설_없이는_재지_않는다(tmp_path):
    p = tmp_path / "s.jsonl"
    p.write_text('{"id": "a", "src": "Hello."}\n', encoding="utf-8")
    with pytest.raises(SystemExit, match="가설"):
        ev.main(["--backend", "aws-translate", "--set", str(p)])
    with pytest.raises(SystemExit, match="대장에 없다"):
        ev.main(["--backend", "aws-translate", "--set", str(p), "--hypothesis", "H-999"])
    with pytest.raises(SystemExit, match="실험 상태"):
        ev.main(["--backend", "aws-translate", "--set", str(p), "--hypothesis", "H-002"])


def test_머리줄이_재현_조건을_든다(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    p = tmp_path / "s.jsonl"
    p.write_text('{"id": "a", "src": "Hello."}\n', encoding="utf-8")
    ev.main(["--backend", "echo", "--set", str(p)])
    import json
    head = json.loads(next((tmp_path / "runs").glob("*.jsonl")).read_text(encoding="utf-8").splitlines()[0])
    for k in ("commit", "set_sha256", "chars", "backend", "weights", "decoding", "hypothesis"):
        assert k in head


@pytest.mark.parametrize("out,want", [
    ("Amazon S3를 씁니다.", 1.0), ("Amazon S3을 씁니다.", 0.0), ("Amazon S3에 둡니다.", None),
])
def test_조사를_끝소리로_잰다(out, want):
    assert ev.josa([{"src": "x", "keep": ["Amazon S3"]}], [out]) == want



def test_개념이_번역에_남았는지_잰다():
    rows = [{"src": "The role must be encrypted."}]
    assert ev.term(rows, ["역할은 암호화되어야 합니다."]) == {"term": 1.0, "term_off": 1.0, "term_bad": 0.0}
    # 허용 표기(음차)는 뜻을 지킨 것으로 세고 공식 표기로는 세지 않는다(DECISIONS §25)
    assert ev.term(rows, ["롤은 암호화되어야 합니다."]) == {"term": 1.0, "term_off": 0.0, "term_bad": 0.0}
    assert ev.term(rows, ["데이터는 암호화되어야 합니다."]) == {"term": 0.0, "term_off": 0.0, "term_bad": 0.0}


def test_관측된_오역을_따로_센다():
    rows = [{"src": "Increase the quota."}]
    assert ev.term(rows, ["쿼리 한도를 늘립니다."]) == {"term": 0.0, "term_off": 0.0, "term_bad": 1.0}
    # 맞는 표기가 함께 있으면 오역이 아니다 — 병기한 줄을 벌주지 않는다
    assert ev.term(rows, ["할당량(쿼리 한도)을 늘립니다."]) == {"term": 1.0, "term_off": 1.0, "term_bad": 0.0}


def test_머리줄이_온톨로지_해시를_든다():
    """사전을 한 줄 고치면 같은 번역의 term 이 바뀐다 — 어느 사전으로 쟀는지 결과가 들어야 한다(DECISIONS §32)."""
    h = ev.onto_sha256()
    assert len(h) == 16 and h == ev.onto_sha256()
