"""문법 축 — 무더기를 가르는 자다(DECISIONS §125 · docs/grammar.md).

★ **정확도를 시험이 지키지 않는다.** 0.68 은 사람이 20줄을 읽어 잰 값이고 시험이 재현할 수 없다.
  시험이 지키는 것은 **가르는 규칙이 뒤집히지 않는 것**이다 — `that` 두 갈래 · 표시 제외 · 분모.
"""
import pathlib

import pytest

from seshat import evaluate, grammar

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("src,축", [
    ("The data that Glue writes to the bucket must be encrypted.", "관형절"),
    ("You must ensure that the configuration setting is correct here.", "명사절"),
    ("The record is written by the producer application every second.", "피동"),
    ("The service does not support the feature that you need.", "부정"),
    ("Choose the solution with the LEAST operational overhead for this.", "최상급"),
    ("This option is faster than the previous one for large files.", "비교급"),
    ("If the service throttles the requests, increase the quota now.", "조건절"),
    ("To reduce latency, move the data closer to the consumer.", "목적"),
    ("Configure the stream, and then connect it to the bucket.", "등위"),
    ("Use the local secondary index for this query pattern.", "연쇄"),
])
def test_축마다_전형적인_문장을_잡는다(src, 축):
    assert 축 in grammar.axes(src)


def test_that_는_앞말이_갈린다():
    """`the data that …`(관형절)와 `ensure that …`(명사절)은 한국어에서 가는 길이 다르다."""
    관 = grammar.axes("The stream that the producer writes to is encrypted.")
    명 = grammar.axes("You must verify that the producer writes to the stream.")
    assert "관형절" in 관 and "명사절" not in 관
    assert "명사절" in 명 and "관형절" not in 명


def test_제품_이름은_연쇄가_아니다():
    """`Amazon Kinesis Data Streams` 는 통째로 하나다 — 대문자에서 끊는다."""
    assert grammar.chains("Send the records to Amazon Kinesis Data Streams now.") == []


def test_분사는_줄을_끊는다():
    """`by using relevant parameters` 를 명사 줄로 세면 정확도가 0.33 으로 떨어진다(DECISIONS §125)."""
    assert grammar.chains("Include the details by using relevant additional parameters.") == []


def test_한정사_뒤에서만_센다():
    """동사에서 시작하면 `specify provisioned throughput` 같은 것이 명사 줄이 된다."""
    assert grammar.chains("You can set custom endpoint override options.") == []
    assert grammar.chains("You can set the custom endpoint override option.") == ["custom endpoint override option"]


def test_표시된_식별자는_연쇄에서_뺀다():
    """`arn:aws:s3:::my-bucket` 이 명사 줄로 세어지던 자리다 — §122 의 표시를 여기서 다시 쓴다."""
    src = "Your account can operate on the arn:aws:s3:::my-bucket resource today."
    row = {"id": "a", "src": src, "lit": [["arn:aws:s3:::my-bucket", src.index("arn")]]}
    assert grammar.chains(src) and grammar.chains(src, evaluate.marked(row)) == []


def test_축은_겹친다():
    """한 줄이 여럿에 든다 — 세로합이 전체와 다른 것이 맞다."""
    got = grammar.axes("The data that Glue writes is not encrypted by the service.")
    assert {"관형절", "피동", "부정"} <= set(got)


def test_축_이름은_문서와_같다():
    """`docs/grammar.md` 의 표가 축을 정한다 — 이름이 갈리면 표를 못 읽는다."""
    표 = (ROOT / "docs/grammar.md").read_text(encoding="utf-8")
    for ax in grammar.AXES:
        assert f"**{ax}**" in 표, ax


def test_슬라이스가_약한_축을_짚는다(tmp_path):
    """도구의 요점 — 한 축에서만 무너진 팔을 전체 숫자가 가려도 축에서는 보인다."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("slice", ROOT / "tools/slice.py")
    S = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(S)
    rows = [{"id": f"r{i}", "src": s, "keep": []} for i, s in enumerate((
        "The stream that the producer writes to must be encrypted here.",
        "The table that the consumer reads from must be encrypted here.",
        "Move the records to the bucket before the retention period ends.",
        "Send the records to the queue before the retention period ends."))]
    outs = {"r0": "처리합니다.", "r1": "처리합니다.",          # 관형절 두 줄만 무너뜨린다
            "r2": "레코드를 버킷으로 옮깁니다. 보존 기간", "r3": "레코드를 큐로 보냅니다. 보존 기간"}
    got = S.by_axis(rows, outs)
    assert got["관형절"]["n"] == 2
    assert got["관형절"]["term_off"] < got["전체"]["term_off"]


def _slice():
    import importlib.util
    spec = importlib.util.spec_from_file_location("slice", ROOT / "tools/slice.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_판정_한_장에_팔이_여럿_든다(tmp_path):
    """눈가림 채점표는 같은 줄의 세 팔을 섞어 낸다. `id` 로만 모으면 **마지막 팔이 앞을 덮는다**
    — 팔을 견주려고 만든 자가 팔을 지운다(DECISIONS §127)."""
    import json
    p = tmp_path / "lab.jsonl"
    p.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in (
        {"meta": True, "judge": "claude"},
        {"id": "r0", "arm": "4b", "verdict": "어긋난다"},
        {"id": "r0", "arm": "12b", "verdict": "맞다"},
        {"id": "r1", "arm": "4b", "verdict": "어긋난다"},
        {"id": "r1", "arm": "12b", "verdict": "맞다"})) + "\n", encoding="utf-8")
    got = _slice().read_labels(str(p))
    assert set(got) == {"4b", "12b"}
    assert got["4b"] == {"r0": "어긋난다", "r1": "어긋난다"}
    assert got["12b"] == {"r0": "맞다", "r1": "맞다"}


def test_판정이_없으면_0_이_아니라_못_읽은_것이다(tmp_path):
    p = tmp_path / "빈.jsonl"
    p.write_text('{"meta": true}\n', encoding="utf-8")
    with pytest.raises(SystemExit, match="못 읽은 것이다"):
        _slice().read_labels(str(p))
