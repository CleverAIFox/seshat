"""평가 도구의 판정."""
import json
import pathlib

import pytest

from seshat import evaluate as ev

ROOT = pathlib.Path(__file__).resolve().parents[1]


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
    # ★ 개념이 하나만 든 원문을 쓴다. `encrypted` 도 이제 개념이다(DECISIONS §69) — 둘이 들면
    #   무엇이 0.5 를 만들었는지 이 시험이 말해 주지 못한다.
    rows = [{"src": "The role is ready."}]
    assert ev.term(rows, ["역할은 준비되었습니다."]) == {"term": 1.0, "term_off": 1.0, "term_bad": 0.0, "term_n": 1}
    # 허용 표기(음차)는 뜻을 지킨 것으로 세고 공식 표기로는 세지 않는다(DECISIONS §25)
    assert ev.term(rows, ["롤은 준비되었습니다."]) == {"term": 1.0, "term_off": 0.0, "term_bad": 0.0, "term_n": 1}
    assert ev.term(rows, ["데이터는 준비되었습니다."]) == {"term": 0.0, "term_off": 0.0, "term_bad": 0.0, "term_n": 1}


def test_관측된_오역을_따로_센다():
    rows = [{"src": "Increase the quota."}]
    assert ev.term(rows, ["쿼리 한도를 늘립니다."]) == {"term": 0.0, "term_off": 0.0, "term_bad": 1.0, "term_n": 1}
    # 맞는 표기가 함께 있으면 오역이 아니다 — 병기한 줄을 벌주지 않는다
    assert ev.term(rows, ["할당량(쿼리 한도)을 늘립니다."]) == {"term": 1.0, "term_off": 1.0, "term_bad": 0.0,
                                                          "term_n": 1}


def test_분모를_결과가_든다():
    """비율만 있으면 사람이 약분해서 분모를 짐작한다 — 2026-09-25 에 실제로 틀렸다(DECISIONS §70)."""
    rows = [{"src": "The catalog is ingested by the cluster."}]
    got = ev.term(rows, ["카탈로그는 클러스터에 의해 수집됩니다."])
    assert got["term_n"] == 3                       # catalog · ingestion · cluster
    assert ev.term([], [])["term_n"] == 0


def test_머리줄이_온톨로지_해시를_든다():
    """사전을 한 줄 고치면 같은 번역의 term 이 바뀐다 — 어느 사전으로 쟀는지 결과가 들어야 한다(DECISIONS §32)."""
    h = ev.onto_sha256()
    assert len(h) == 16 and h == ev.onto_sha256()


def test_돈이_드는_백엔드는_견적을_먼저_낸다():
    """가설의 비용 상한을 사람이 아니라 도구가 지킨다(DECISIONS §35)."""
    rows = [{"src": "x" * 100_000}]
    assert ev.estimate_usd("aws-translate", rows) == 1.5
    assert ev.estimate_usd("translategemma-4b", rows) == 0.0
    assert ev.estimate_usd("", []) == 0.0                 # --url 은 남의 서버다


def test_값을_모르는_백엔드는_공짜가_아니다():
    """표에 없는 이름이 0 원으로 떨어지면 상한이 아무것도 안 막는다(DECISIONS §62)."""
    import pytest
    rows = [{"src": "x" * 100_000}]
    with pytest.raises(SystemExit) as e:
        ev.estimate_usd("papago", rows)
    assert "값을 모른다" in str(e.value) and "100,000자" in str(e.value)


def test_상한을_넘으면_부르지_않는다(tmp_path):
    import subprocess
    st = tmp_path / "big.jsonl"
    st.write_text("\n".join(json.dumps({"id": str(i), "src": "x" * 20_000}, ensure_ascii=False)
                            for i in range(10)) + "\n", encoding="utf-8")
    r = subprocess.run(["python3", "-m", "seshat.evaluate", "--backend", "aws-translate",
                        "--set", str(st), "--hypothesis", "H-025", "--max-usd", "1"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode != 0 and "상한" in (r.stderr + r.stdout)


def test_번역인가를_묻는_지표가_있다():
    """영어 사고문이 번역문 자리에 와도 term 은 1.0 이 나왔다(DECISIONS §49)."""
    r = [{"src": "Use Amazon S3."}]
    assert ev.hangul(r, ["Amazon S3를 씁니다."]) == 1.0          # 이름이 영어로 남아도 번역이다
    assert ev.hangul(r, ["Okay, let's tackle this translation request. The user wants me to"]) == 0.0
    assert ev.hangul([], []) is None


def test_한국어를_인용하는_사고문에_속지_않는다():
    """지표를 속인 예를 그대로 시험에 넣는다(DECISIONS §50)."""
    src = "The data engineering team uses AWS Transfer Family to process the replica."
    think = ("Okay, let's tackle this translation request. The user wants me to translate the English "
             "sentence into Korean. They specified only the translation. First, \"데이터 엔지니어링 팀\" is "
             "the subject, and I should keep the placeholder exactly as it appears in the source text.")
    assert ev.ko_line(src, think) is False                    # 한국어를 인용해도 번역이 아니다
    assert ev.ko_line(src, "데이터 엔지니어링 팀은 ⟦T1⟧를 사용하여 복제본을 처리합니다.") is True


def test_term_은_번역이_아닌_줄에서_점수를_주지_않는다():
    """Qwen3 4B 가 실제로 뱉은 모양 — 영어 사고 과정이 한국어를 인용한다(DECISIONS §52)."""
    rows = [{"src": "The data engineering team uses Amazon Athena to process the data lake."}]
    fooled = ("Okay, the user wants a Korean translation. Amazon Athena stays in English, "
              "and 'data lake' is 데이터 레이크 in Korean. Let me write it out.")
    assert ev.hangul(rows, [fooled]) == 0.0
    assert ev.term(rows, [fooled])["term"] == 0.0

    real = "데이터 엔지니어링 팀은 Amazon Athena를 사용하여 데이터 레이크를 처리합니다."
    assert ev.term(rows, [real])["term"] == 1.0


def test_긴_판은_열에_한_번_제_상태를_말한다(capsys):
    """12B 를 CPU 로 내려 재는 판이 한 시간 동안 로그에 한 줄도 안 남겼다(DECISIONS §80)."""
    done = 0
    for _ in range(0, 200, 9):                      # BATCH 가 9 라 200 을 나누어떨어뜨리지 않는다
        before, done = done, min(done + 9, 200)
        ev._진척(before, done, 200, done * 12.0)
    말 = capsys.readouterr().err
    assert 말.count("남은 시간") == 9                # 열 칸 중 마지막은 안 찍는다(곧 결과가 나온다)
    assert "줄당 12.0초" in 말


def test_짧은_판은_조용하다(capsys):
    """세 줄짜리 연기 시험까지 떠들면 읽을 것이 는다."""
    ev._진척(0, 3, 3, 9.0)
    ev._진척(0, 1, 3, 3.0)
    assert capsys.readouterr().err == ""


def test_진척은_표준_오류로_쓴다(capsys):
    """표준 출력은 결과 JSON 의 자리다 — 파이프로 받는 쪽을 깨뜨리지 않는다."""
    ev._진척(0, 20, 200, 240.0)
    got = capsys.readouterr()
    assert got.out == "" and "20/200" in got.err


def test_재현_조건은_판을_시작할_때_찍는다(monkeypatch):
    """한 시간짜리 판이 도는 동안 패치를 붙이면, 끝에서 읽은 조건은 거짓말이 된다(DECISIONS §81)."""
    import argparse
    시작 = {"commit": "aaaaaaa", "dirty": False}
    지금 = {"commit": "bbbbbbb", "dirty": True}
    monkeypatch.setattr(ev, "코드_상태", lambda: 지금)

    a = argparse.Namespace(hypothesis="H-001", set="data/eval/seed.jsonl", backend="echo", url="")
    rows = [{"src": "x"}]
    assert ev.conditions(a, rows, 시작)["commit"] == "aaaaaaa"
    assert ev.conditions(a, rows, 시작)["dirty"] is False
    assert ev.conditions(a, rows)["commit"] == "bbbbbbb"      # 안 주면 지금 찍는다


def test_지킨_이름이_많은_줄을_떨어뜨리지_않는다():
    """600 줄 중 이 한 줄이 「번역이 아니다」 로 걸렸다. 완벽한 번역이다(DECISIONS §91)."""
    src = "Configure S3 Glacier Instant Retrieval, and then connect it to Amazon Simple Notification Service."
    좋은 = "S3 Glacier Instant Retrieval을 구성한 다음, Amazon Simple Notification Service에 연결하십시오."
    assert ev.ko_line(src, 좋은) is True
    # 원문에 없는 영어는 그대로 둔다 — 영어로 답한 것은 여전히 번역이 아니다
    assert ev.ko_line(src, "Configure it and connect to the service afterwards.") is False


def test_원문에_없는_영어는_빼지_않는다():
    src = "Use Amazon S3."
    assert ev.ko_line(src, "Amazon S3를 씁니다.") is True
    assert ev.ko_line(src, "Amazon S3 is a storage service you should use.") is False
