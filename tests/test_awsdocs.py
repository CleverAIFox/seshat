"""AWS 문서 수확 — 코드 · 표를 안 가져온다 · 도메인 낱말 없는 줄을 버린다 · 같은 인자면 같은 셋(DECISIONS §92).

★ **망을 타지 않는다.** `clone` 은 여기서 부르지 않는다 — 문자열을 문장으로 바꾸는 부분만 본다.
  받는 일이 맞는지는 실행이 말하고, 거르는 규칙이 맞는지는 이 파일이 말한다.
"""
import importlib.util
import pathlib

from seshat import ontology

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("fetch_awsdocs", ROOT / "tools/fetch_awsdocs.py")
aws = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(aws)

MD = """\
# Working with tables

Amazon DynamoDB stores the data in partitions and replicates it across three Availability Zones.

| Name | Type |
| --- | --- |
| The table must have a partition key defined before the write operation happens. | string |

```
The code fence must not become a sentence in the evaluation set here.
```

    The indented block is code and must not become a sentence in the set.

+ A [global secondary index](gsi.md) lets you query the table with an alternate `partition key`.
+ Short line.
+ aws dynamodb create-table --table-name Music --billing-mode PAY_PER_REQUEST and more words.

You can set the value to ${THROUGHPUT} when you create the table with provisioned mode.

Table: The tables that this resource policy applies to in the current account.
"""


def _sent():
    return aws.sentences(MD)


def test_코드_표_제목은_문장이_아니다():
    got = " ".join(_sent())
    assert "code fence" not in got
    assert "indented block" not in got
    assert "must have a partition key" not in got      # 표 안이다
    assert "Working with tables" not in got            # 제목이다


def test_링크와_인라인_코드는_글자만_남는다():
    line = next(s for s in _sent() if "global secondary index" in s)
    assert "](" not in line and "`" not in line
    assert "alternate partition key" in line


def test_명령줄_자리표시_짧은_줄은_버린다():
    got = " ".join(_sent())
    assert "create-table" not in got
    assert "THROUGHPUT" not in got
    assert "Short line" not in got


def test_정의_목록은_문장이_아니다():
    assert not any(s.startswith("Table:") for s in _sent())


def test_산문은_남는다():
    assert any("replicates it across three Availability Zones" in s for s in _sent())


def test_도메인_낱말이_없는_줄은_버린다(tmp_path):
    onto = ontology.load()
    (tmp_path / "a.md").write_text(
        "Amazon DynamoDB replicates the table across three Availability Zones automatically.\n\n"
        "The quick brown fox jumped over the lazy dog and then went home to sleep.\n",
        encoding="utf-8")
    got = [s for s, _ in aws.harvest(onto, tmp_path)]
    assert len(got) == 1 and "DynamoDB" in got[0]


def test_README_는_읽지_않는다(tmp_path):
    (tmp_path / "README.md").write_text(
        "This repository is archived and Amazon DynamoDB documentation moved to the website.\n", encoding="utf-8")
    assert aws.harvest(ontology.load(), tmp_path) == []


def test_같은_seed_면_같은_셋이고_다르면_다르다():
    found = {"g": [(f"Amazon S3 stores object number {i:03d} in the bucket for a long time.", "d.md") for i in range(50)]}
    a = aws.choose(found, 10, 21, 400)
    assert a == aws.choose(found, 10, 21, 400)
    assert a != aws.choose(found, 10, 22, 400)


def test_안내서마다_상한이_걸린다():
    found = {g: [(f"Amazon S3 keeps object {g} number {i:03d} in the bucket for a while.", "d.md") for i in range(50)]
             for g in ("a", "b")}
    picked = aws.choose(found, 6, 21, 3)
    assert len({g for _, g, _ in aws.choose(found, 6, 21, 3)}) == 2
    assert len(picked) == 6


def test_문장이_모자라면_말한다():
    try:
        aws.choose({"g": [("Amazon S3 stores the object in a bucket for a long time here.", "d.md")]}, 5, 21, 400)
    except SystemExit as e:
        assert "1 뿐인데 5" in str(e)
    else:
        raise AssertionError("모자란데 통과했다")


def test_keep_은_온톨로지가_영어로_남기라는_표기다():
    onto = ontology.load()
    got = aws.rows(onto, [("Amazon DynamoDB writes the stream record to Amazon Kinesis Data Streams now.", "g", "d.md")])
    assert got[0]["keep"] == ["Amazon DynamoDB", "Amazon Kinesis Data Streams"]
    assert got[0]["id"] == "awsdocs-0001" and got[0]["guide"] == "g"


def test_카탈로그가_이_도구를_안다():
    from seshat import catalog
    entries = catalog.load()
    e = catalog.match(entries, "repo", "data/domain/d001.jsonl")
    assert e and e["how"] == "tools/fetch_awsdocs.py"
    assert not catalog.allowed(e["id"], "train")       # 동일 조건을 안 읽었다
    assert catalog.allowed(e["id"], "eval")
