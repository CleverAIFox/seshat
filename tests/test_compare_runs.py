"""결과 대조 도구(MASTER §7 R7)."""
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("cr", ROOT / "tools/compare_runs.py")
cr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cr)


def _run(p, outs, sha="x"):
    lines = [{"meta": True, "set_sha256": sha, "keep": 0.5, "style": 1.0, "ms": 1}]
    lines += [{"id": i, "src": "s", "out": o} for i, o in outs.items()]
    p.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in lines) + "\n", encoding="utf-8")
    return str(p)


def test_줄마다_이기고_진_것을_가른다():
    spec = {"1": {"keep": ["Amazon S3"], "construction": "SV"}, "2": {"keep": ["Athena"], "construction": "SVO"},
            "3": {"keep": ["IAM"], "construction": "SV"}}
    a = {"1": {"out": "아마존 S3"}, "2": {"out": "Athena 를"}, "3": {"out": "IAM"}}
    b = {"1": {"out": "Amazon S3를"}, "2": {"out": "아테나"}, "3": {"out": "\\[T1]이"}}
    r = cr.compare(a, b, spec)
    assert r["b_better"] == ["1"] and r["b_worse"] == ["2", "3"] and r["residue"] == ["3"]
    assert r["by_construction"]["SV"] == [2, 1, 1]


def test_평가셋이_다르면_멈춘다(tmp_path):
    x = _run(tmp_path / "a.jsonl", {"1": "가"}, "aaa")
    y = _run(tmp_path / "b.jsonl", {"1": "가"}, "bbb")
    assert cr.main([x, y]) == 1


def test_다시_채점한다(tmp_path, monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("rs", ROOT / "tools/rescore.py")
    rs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rs)
    setf = tmp_path / "s.jsonl"
    setf.write_text(json.dumps({"id": "1", "src": "Use Amazon EMR.", "keep": ["Amazon EMR"]}) + "\n", encoding="utf-8")
    run = tmp_path / "r.jsonl"
    run.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in [
        {"meta": True, "commit": "c", "set_sha256": "h", "ms": 1},
        {"id": "1", "src": "Use Amazon EMR.", "out": "\\[T1]를 씁니다."}]) + "\n", encoding="utf-8")
    head, body = rs.rescore(str(run), str(setf))
    assert body[0]["out"] == "Amazon EMR을 씁니다." and head["keep"] == 1.0 and head["rescored_from"] == "r.jsonl"



def test_마지막_이름_뒤_낱말을_센다():
    assert cr.words_after_last_name("Use Amazon S3 to store the logs.", ["Amazon S3"]) == 4
    assert cr.words_after_last_name("Configure Athena.", ["Athena"]) == 0  # 마침표는 낱말이 아니다
    assert cr.words_after_last_name("No names here.", ["Amazon S3"]) is None


def test_합쇼체가_한쪽에서만_깨진_줄을_찾는다():
    a = {"1": {"src": "Use Amazon S3.", "out": "Amazon S3를 씁니다."}, "2": {"src": "Use Athena now.", "out": "Athena를 씁니다."}}
    b = {"1": {"src": "Use Amazon S3.", "out": "Amazon S3를 쓴다."}, "2": {"src": "Use Athena now.", "out": "Athena를 씁니다."}}
    spec = {"1": {"keep": ["Amazon S3"]}, "2": {"keep": ["Athena"]}}
    r = cr.style_flips(a, b, spec)
    assert r["flips"] == ["1"] and r["after_flip"] == 0 and r["after_rest"] == 1
    assert r["b_only"] == ["1"] and r["a_only"] == [] and r["both"] == []


def test_두_팔이_같은_줄에서_깨지면_둘_다로_센다():
    """같은 줄이 양쪽에서 깨지면 「B 만」 은 0 이다 — 그것을 안 깨졌다고 읽으면 안 된다(DECISIONS §29)."""
    a = {"1": {"src": "Use Amazon S3.", "out": "Amazon S3를 쓴다."}, "2": {"src": "Use Athena.", "out": "Athena를 씁니다."}}
    b = {"1": {"src": "Use Amazon S3.", "out": "Amazon S3를 써요."}, "2": {"src": "Use Athena.", "out": "Athena를 쓴다."}}
    r = cr.style_flips(a, b, {})
    assert r["both"] == ["1"] and r["b_only"] == ["2"] and r["a_only"] == []


def test_구문별로_개념이_남았는지_본다():
    a = {"1": {"src": "The role that Athena writes.", "out": "Athena가 쓰는 역할"}}
    b = {"1": {"src": "The role that Athena writes.", "out": "Athena가 쓰는 데이터"}}
    r = cr.terms_by_construction(a, b, {"1": {"construction": "relative"}})
    assert r["relative"] == [1, 1, 0]


def test_개념이_없다고_센_자리를_줄로_보인다():
    rows = {"1": {"src": "The role writes the data.", "out": "데이터를 씁니다."},
            "2": {"src": "Increase the quota.", "out": "쿼리 한도를 늘립니다."}}
    count, lines = cr.term_misses(rows, {"1": {"construction": "relative"}, "2": {"construction": "SVO"}})
    # ★ 버린 자리와 오역한 자리를 표시로 가른다(DECISIONS §25). 둘은 대응이 다르다
    assert ("relative", "role · 없음", ["역할", "롤"], rows["1"]["out"]) in lines
    assert count["con.quota · 오역"] == 1


def test_머리줄이_지표_셋을_찍는다(capsys, tmp_path):
    """`term` 하나만 보면 표기 차이와 오역이 섞인다(DECISIONS §25). 머리줄에서 셋을 가른다."""
    head = {"meta": True, "backend": "x", "keep": 1.0, "josa": 1.0, "style": 1.0, "ms": 1,
            "set_sha256": "s", "term": 0.8, "term_off": 0.5, "term_bad": 0.0}
    row = {"id": "1", "src": "Use Amazon S3.", "out": "Amazon S3를 씁니다."}
    for name in ("a", "b"):
        (tmp_path / f"{name}.jsonl").write_text(
            "\n".join(json.dumps(x, ensure_ascii=False) for x in (head, row)) + "\n", encoding="utf-8")
    cr.main([str(tmp_path / "a.jsonl"), str(tmp_path / "b.jsonl")])
    out = capsys.readouterr().out
    assert "term 0.800 · term_off 0.500 · term_bad 0.000" in out


def test_사전이_다르면_대조를_멈춘다(capsys, tmp_path):
    """온톨로지가 다르면 term 차이는 모델이 아니라 사전의 차이다(DECISIONS §32)."""
    row = {"id": "1", "src": "Use Amazon S3.", "out": "Amazon S3를 씁니다."}
    for name, onto in (("a", "1111"), ("b", "2222")):
        head = {"meta": True, "backend": name, "keep": 1.0, "josa": 1.0, "style": 1.0, "ms": 1,
                "set_sha256": "s", "onto_sha256": onto}
        (tmp_path / f"{name}.jsonl").write_text(
            "\n".join(json.dumps(x, ensure_ascii=False) for x in (head, row)) + "\n", encoding="utf-8")
    assert cr.main([str(tmp_path / "a.jsonl"), str(tmp_path / "b.jsonl")]) == 1
    assert "온톨로지 해시가 다르다" in capsys.readouterr().out


def test_줄_수가_다르면_대조를_멈춘다(capsys, tmp_path):
    """`--limit` 판과 전수를 나란히 놓으면 다른 문장을 비교한다(DECISIONS §45)."""
    row = {"id": "1", "src": "Use Amazon S3.", "out": "Amazon S3를 씁니다."}
    for name, n in (("a", 20), ("b", 200)):
        head = {"meta": True, "backend": name, "keep": 1.0, "josa": 1.0, "style": 1.0, "ms": 1,
                "set_sha256": "s", "onto_sha256": "o", "n": n}
        (tmp_path / f"{name}.jsonl").write_text(
            "\n".join(json.dumps(x, ensure_ascii=False) for x in (head, row)) + "\n", encoding="utf-8")
    assert cr.main([str(tmp_path / "a.jsonl"), str(tmp_path / "b.jsonl")]) == 1
    assert "줄 수가 다르다" in capsys.readouterr().out


def test_토막_길이는_가린_뒤에_센다():
    """★ **`+ph` 가 이름을 먼저 뺀다**(DECISIONS §177). 원문으로 세면 이름까지 세어
    실제 토막보다 길게 나오고, 그러면 H-075 의 배수가 통째로 틀린다."""
    rows = {"x": {"src": "Use Amazon S3 with the console to create a table."}}
    got = cr.토막_길이(["x"], rows)["x"]
    from seshat import glossary, ontology
    onto = ontology.load()
    날것 = len(glossary.for_line(onto, rows["x"]["src"]))
    assert got <= 날것, "가린 뒤가 원문보다 길 수 없다"
    assert got >= 1, "개념이 하나는 잡혀야 이 시험이 뜻이 있다"


def test_중앙값():
    assert cr.중앙([]) == 0.0
    assert cr.중앙([3]) == 3.0
    assert cr.중앙([1, 3]) == 2.0
    assert cr.중앙([5, 1, 3]) == 3.0
