"""판정 — 눈가림 · 줄을 먼저 뽑는다 · 원문은 아무 데도 안 남는다(DECISIONS §98 · §103 · H-046)."""
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
    sheet, key = L.make({"a": _run(tmp_path, "4b"), "b": _run(tmp_path, "12b")}, ROWS, "t", 5, 31)
    assert "4b" not in sheet and "12b" not in sheet
    cols = [ln.split("\t") for ln in sheet.splitlines()[1:]]
    assert all(len(c) == 4 for c in cols)                      # 표 · 원문 · 번역 · 판정. 팔 칸이 없다
    assert not any("a" in c[:1] or "b" in c[:1] for c in cols)
    assert len(key) == 10 and {r["arm"] for r in key} == {"a", "b"}


def test_두_팔이_나란히_서지_않는다(tmp_path):
    sheet, key = L.make({"a": _run(tmp_path, "4b"), "b": _run(tmp_path, "12b")}, ROWS, "t", 10, 31)
    order = [ln.split("\t")[0] for ln in sheet.splitlines()[1:]]
    by_tag = {r["tag"]: r["id"] for r in key}
    붙은쌍 = sum(by_tag[x] == by_tag[y] for x, y in zip(order, order[1:]))
    assert 붙은쌍 <= 2, "같은 줄의 두 팔이 자꾸 붙어 나온다 — 섞이지 않았다"


def test_seed_가_표본을_정한다(tmp_path):
    a, b = _run(tmp_path, "4b"), _run(tmp_path, "12b")
    ids = lambda seed: sorted({r["id"] for r in L.make({"a": a, "b": b}, ROWS, "t", 5, seed)[1]})  # noqa: E731
    assert ids(31) == ids(31)
    assert ids(31) != ids(32)


def test_다른_셋이면_멈춘다(tmp_path):
    try:
        L.make({"a": _run(tmp_path, "4b"), "b": _run(tmp_path, "12b", sha="다르다")}, ROWS, "t", 5, 31)
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
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    sheet, key = L.make({"a": _run(tmp_path, "4b"), "b": _run(tmp_path, "12b")}, ROWS, "t", 5, 31)
    (tmp_path / "t.key.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in key) + "\n", encoding="utf-8")
    arm_of = {r["tag"]: r["arm"] for r in key}
    filled = [sheet.splitlines()[0]]
    for ln in sheet.splitlines()[1:]:
        t = ln.split("\t")[0]
        filled.append(ln + ("맞다" if arm_of[t] == "b" else "어긋난다"))
    s = tmp_path / "sheet.tsv"
    s.write_text("\n".join(filled) + "\n", encoding="utf-8")
    L.read("t", s, "claude")
    out = capsys.readouterr().out
    assert "a  뜻이 맞다 0.000" in out and "b  뜻이 맞다 1.000" in out
    saved = [json.loads(x) for x in (tmp_path / "t.claude.jsonl").read_text(encoding="utf-8").splitlines()]
    assert all("src" not in r and "out" not in r for r in saved), "원문이나 출력이 판정 파일에 남았다"


def test_모르는_판정은_거절한다(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    sheet, key = L.make({"a": _run(tmp_path, "4b"), "b": _run(tmp_path, "12b")}, ROWS, "t", 2, 31)
    (tmp_path / "t.key.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in key) + "\n", encoding="utf-8")
    s = tmp_path / "sheet.tsv"
    s.write_text(sheet.splitlines()[0] + "\n" + sheet.splitlines()[1] + "좋음\n", encoding="utf-8")
    try:
        L.read("t", s, "claude")
    except SystemExit as e:
        assert "모르는 판정" in str(e)
    else:
        raise AssertionError("아무 말이나 판정으로 받았다")


def test_두_칸짜리_판정도_받는다():
    """다른 판정자는 표 전체가 아니라 태그와 판정만 돌려준다."""
    assert L.verdict_of(["8d6722bc", "맞다"]) == "맞다"
    assert L.verdict_of(["8d6722bc", "원문", "번역", "어긋난다"]) == "어긋난다"
    assert L.verdict_of(["8d6722bc", "원문", "번역"]) == ""


def test_카파는_쏠린_판정을_벌준다():
    """한쪽으로 쏠리면 일치율은 높고 카파는 낮다 — 「맞다」 만 찍어도 일치율이 오른다."""
    x = ["맞다"] * 18 + ["어긋난다"] * 2
    y = ["맞다"] * 20
    assert sum(a == b for a, b in zip(x, y)) / 20 == 0.9
    assert L.cohen_kappa(x, y) == 0.0                    # 우연을 빼면 0
    assert L.cohen_kappa(x, x) == 1.0
    갈림 = ["맞다"] * 10 + ["어긋난다"] * 10
    assert L.cohen_kappa(갈림, 갈림[::-1]) < 0           # 반대로 찍으면 음수


def test_두_판정자의_일치를_낸다(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    for judge, v2 in (("claude", "맞다"), ("gemini", "어긋난다")):
        rows = [{"meta": True}]
        rows += [{"tag": f"t{i}", "id": f"x{i:03d}", "arm": "a",
                  "verdict": "맞다" if i else v2} for i in range(5)]
        (tmp_path / f"t.{judge}.jsonl").write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    L.agree("t", ["claude", "gemini"])
    out = capsys.readouterr().out
    assert "같은 줄 5 · 일치 4" in out
    assert "갈린 줄 1" in out and "x000 [a]" in out


def test_없는_판정자는_말한다(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    (tmp_path / "t.claude.jsonl").write_text(json.dumps({"meta": True}) + "\n", encoding="utf-8")
    try:
        L.agree("t", ["claude", "gemini"])
    except SystemExit as e:
        assert "read --judge gemini" in str(e)
    else:
        raise AssertionError("없는 판정자인데 통과했다")


def test_지시문이_규칙_넷을_든다():
    """다른 판정자에게 주는 지시문 — **표기는 맞다** 와 **맞히려 하지 마라** 가 빠지면 자가 달라진다."""
    for must in ("맞다", "어긋난다", "아니다", "표기가 공식 표기와 달라도", "맞히려 하지 마세요",
                 "태그<탭>판정", "표에 있는 줄 수만큼", "줄마다 따로 판정",
                 # 판정자 둘이 갈린 자리를 예시로 못 박았다(DECISIONS §105)
                 "낱말 하나가 망가진 것만으로는", "조각이 빠졌거나 관계가 바뀌면",
                 "다르게 행동하거나"):
        assert must in L.PROMPT, must
    assert "4B" not in L.PROMPT and "12B" not in L.PROMPT and "gemma" not in L.PROMPT.lower()


def test_판정은_작업대에_나고_커밋되지_않는다():
    """`runs/` 와 같은 모양 — 도구는 작업대에 쓰고 사람이 `put` 으로 레이크에 넣는다(DECISIONS §103).
    레이크의 `raw` 에 직접 쓰면 해시 대장 밖 파일이 된다."""
    assert L.out_dir() == ROOT / "labels"
    assert not (ROOT / "data/labels").exists(), "저장소에 data/labels 가 다시 생겼다"
    assert "\nlabels/\n" in (ROOT / ".gitignore").read_text(encoding="utf-8"), "작업대가 git 에 잡힌다"


def test_카탈로그가_라벨을_레이크에_둔다():
    from seshat import catalog
    e = next(x for x in catalog.load() if x["id"] == "labels")
    assert e["where"].startswith("lake:"), e["where"]


def test_채점표가_없으면_한_줄로_말한다(tmp_path, monkeypatch):
    """파이썬 스택을 뱉지 않는다 — 막힌 줄과 다음 명령을 든다(DECISIONS §51)."""
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    try:
        L.read("t", tmp_path / "없다.tsv", "claude")
    except SystemExit as e:
        assert "채점표가 없다" in str(e) and "labels.py make" in str(e)
    else:
        raise AssertionError("없는 파일인데 통과했다")


def test_열쇠가_없으면_한_줄로_말한다(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    s = tmp_path / "s.tsv"
    s.write_text("표\t판정\n", encoding="utf-8")
    try:
        L.read("t", s, "claude")
    except SystemExit as e:
        assert "열쇠가 없다" in str(e)
    else:
        raise AssertionError("열쇠 없는데 통과했다")


def test_make_가_판정_순서를_찍는다(tmp_path, monkeypatch, capsys):
    """순서가 설계에만 있고 전달에 없으면 오염된다(DECISIONS §108)."""
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    monkeypatch.setattr(L.evaluate, "load", lambda p: ROWS)
    L.main(["make", "--set", "x", "--a", str(_run(tmp_path, "4b")), "--b", str(_run(tmp_path, "12b")),
            "--name", "t", "--n", "5"])
    out = capsys.readouterr().out
    assert "한 번에 하나씩" in out and "§108" in out


def test_팔이_셋이어도_된다(tmp_path):
    """기준선을 같은 표에 얹는다 — 따로 재면 표본도 판정자도 달라진다(DECISIONS §115)."""
    arms = {n: _run(tmp_path, n) for n in ("4b", "12b", "nova")}
    sheet, key = L.make(arms, ROWS, "t", 5, 31)
    assert len(key) == 15 and {r["arm"] for r in key} == {"4b", "12b", "nova"}
    assert len(sheet.splitlines()) == 16          # 머리줄 + 15
    for n in ("4b", "12b", "nova"):
        assert n not in sheet                     # 눈가림은 그대로다


def test_팔이_하나면_멈춘다(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    monkeypatch.setattr(L.evaluate, "load", lambda p: ROWS)
    try:
        L.main(["make", "--set", "x", "--arm", f"a={_run(tmp_path, '4b')}", "--n", "5"])
    except SystemExit as e:
        assert "둘 이상" in str(e)
    else:
        raise AssertionError("팔 하나인데 통과했다")


def test_arm_형식이_틀리면_말한다(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    monkeypatch.setattr(L.evaluate, "load", lambda p: ROWS)
    try:
        L.main(["make", "--set", "x", "--arm", "그냥경로", "--arm", "b=x", "--n", "5"])
    except SystemExit as e:
        assert "이름=경로" in str(e)
    else:
        raise AssertionError("형식이 틀린데 통과했다")
