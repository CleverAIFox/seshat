"""사람 판정 — 눈가림 · 줄을 먼저 뽑는다 · 원문은 저장소에 안 남는다(DECISIONS §98 · H-046)."""
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("labels", ROOT / "tools/labels.py")
L = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(L)

ROWS = [{"id": f"x{i:03d}", "src": f"Amazon S3 stores object {i:03d} in a bucket."} for i in range(20)]


def _run(tmp, arm, sha="same"):
    p = tmp / f"{arm}.jsonl"
    body = [{"meta": True, "set_sha256": sha, "backend": arm}]
    # ★ 출력에 팔 이름을 안 넣는다 — 넣으면 눈가림 시험이 제 꼬리를 문다
    body += [{"id": r["id"], "src": r["src"], "out": f"번역 {r['id']}"} for r in ROWS]
    p.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in body) + "\n", encoding="utf-8")
    return p


def test_채점표에_팔_이름이_없다(tmp_path):
    sheet, key = L.make(_run(tmp_path, "4b"), _run(tmp_path, "12b"), ROWS, "t", 5, 31)
    assert "4b" not in sheet and "12b" not in sheet
    cols = [ln.split("\t") for ln in sheet.splitlines()[1:]]
    assert all(len(c) == 4 for c in cols)                      # 표 · 원문 · 번역 · 판정. 팔 칸이 없다
    assert not any("a" in c[:1] or "b" in c[:1] for c in cols)
    assert len(key) == 10 and {r["arm"] for r in key} == {"a", "b"}


def test_두_팔이_나란히_서지_않는다(tmp_path):
    sheet, key = L.make(_run(tmp_path, "4b"), _run(tmp_path, "12b"), ROWS, "t", 10, 31)
    order = [ln.split("\t")[0] for ln in sheet.splitlines()[1:]]
    by_tag = {r["tag"]: r["id"] for r in key}
    붙은쌍 = sum(by_tag[x] == by_tag[y] for x, y in zip(order, order[1:]))
    assert 붙은쌍 <= 2, "같은 줄의 두 팔이 자꾸 붙어 나온다 — 섞이지 않았다"


def test_seed_가_표본을_정한다(tmp_path):
    a, b = _run(tmp_path, "4b"), _run(tmp_path, "12b")
    ids = lambda seed: sorted({r["id"] for r in L.make(a, b, ROWS, "t", 5, seed)[1]})  # noqa: E731
    assert ids(31) == ids(31)
    assert ids(31) != ids(32)


def test_다른_셋이면_멈춘다(tmp_path):
    try:
        L.make(_run(tmp_path, "4b"), _run(tmp_path, "12b", sha="다르다"), ROWS, "t", 5, 31)
    except SystemExit as e:
        assert "다른 셋" in str(e)
    else:
        raise AssertionError("다른 셋인데 통과했다")


def test_줄_id_가_없으면_거절한다(tmp_path):
    p = tmp_path / "old.jsonl"
    p.write_text(json.dumps({"meta": True}) + "\n" + json.dumps({"src": "x", "out": "y"}) + "\n", encoding="utf-8")
    try:
        L.read_run(p)
    except SystemExit as e:
        assert "id 가 없다" in str(e)
    else:
        raise AssertionError("id 없는 파일이 통과했다")


def test_채점표를_읽어_팔마다_비율을_낸다(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(L, "OUT", tmp_path / "labels")
    L.OUT.mkdir()
    sheet, key = L.make(_run(tmp_path, "4b"), _run(tmp_path, "12b"), ROWS, "t", 5, 31)
    (L.OUT / "t.key.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in key) + "\n", encoding="utf-8")
    arm_of = {r["tag"]: r["arm"] for r in key}
    filled = [sheet.splitlines()[0]]
    for ln in sheet.splitlines()[1:]:
        t = ln.split("\t")[0]
        filled.append(ln + ("맞다" if arm_of[t] == "b" else "어긋난다"))
    s = tmp_path / "sheet.tsv"
    s.write_text("\n".join(filled) + "\n", encoding="utf-8")
    L.read("t", s)
    out = capsys.readouterr().out
    assert "a  뜻이 맞다 0.000" in out and "b  뜻이 맞다 1.000" in out
    saved = [json.loads(x) for x in (L.OUT / "t.jsonl").read_text(encoding="utf-8").splitlines()]
    assert all("src" not in r and "out" not in r for r in saved), "원문이나 출력이 저장소에 남았다"


def test_모르는_판정은_거절한다(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "OUT", tmp_path / "labels")
    L.OUT.mkdir()
    sheet, key = L.make(_run(tmp_path, "4b"), _run(tmp_path, "12b"), ROWS, "t", 2, 31)
    (L.OUT / "t.key.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in key) + "\n", encoding="utf-8")
    s = tmp_path / "sheet.tsv"
    s.write_text(sheet.splitlines()[0] + "\n" + sheet.splitlines()[1] + "좋음\n", encoding="utf-8")
    try:
        L.read("t", s)
    except SystemExit as e:
        assert "모르는 판정" in str(e)
    else:
        raise AssertionError("아무 말이나 판정으로 받았다")
