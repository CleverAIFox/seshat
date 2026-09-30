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
    sheet, key, _판 = L.make({"a": _run(tmp_path, "4b"), "b": _run(tmp_path, "12b")}, ROWS, "t", 5, 31)
    assert "4b" not in sheet and "12b" not in sheet
    cols = [ln.split("\t") for ln in sheet.splitlines()[1:]]
    assert all(len(c) == 4 for c in cols)                      # 표 · 원문 · 번역 · 판정. 팔 칸이 없다
    assert not any("a" in c[:1] or "b" in c[:1] for c in cols)
    assert len(key) == 10 and {r["arm"] for r in key} == {"a", "b"}


def test_두_팔이_나란히_서지_않는다(tmp_path):
    sheet, key, _판 = L.make({"a": _run(tmp_path, "4b"), "b": _run(tmp_path, "12b")}, ROWS, "t", 10, 31)
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
    sheet, key, _판 = L.make({"a": _run(tmp_path, "4b"), "b": _run(tmp_path, "12b")}, ROWS, "t", 5, 31)
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
    sheet, key, _판 = L.make({"a": _run(tmp_path, "4b"), "b": _run(tmp_path, "12b")}, ROWS, "t", 2, 31)
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
        assert "labels.py read" in str(e) and "--judge gemini" in str(e)
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
    sheet, key, _판 = L.make(arms, ROWS, "t", 5, 31)
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


def _판정(tmp_path, judge: str, 표: dict[tuple[str, str], str]) -> None:
    """판정자 하나의 파일을 짓는다. `표` 는 {(줄 id, 팔): 판정}."""
    rows = [{"meta": True}]
    rows += [{"tag": f"{i}-{a}", "id": i, "arm": a, "verdict": v} for (i, a), v in 표.items()]
    (tmp_path / f"t.{judge}.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def _셋(tmp_path, 맞는쪽: int, n: int = 40) -> None:
    """팔 `4b` 가 `맞는쪽` 줄에서만 맞고 `12b` 는 다 맞는 표를 판정자 셋에게 똑같이 준다."""
    표 = {}
    for i in range(n):
        rid = f"x{i:03d}"
        표[(rid, "4b")] = "맞다" if i < 맞는쪽 else "어긋난다"
        표[(rid, "12b")] = "맞다"
    for j in ("gpt", "gemini", "pplx"):
        _판정(tmp_path, j, 표)


def test_카파는_쌍마다_난다(tmp_path, monkeypatch, capsys):
    """★ 셋을 한 수로 합치면 **어느 둘이 안 맞는지**가 사라진다 — §116 에서 움직인 쪽은 하나였다."""
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    _판정(tmp_path, "gpt", {("x0", "a"): "맞다", ("x1", "a"): "맞다"})
    _판정(tmp_path, "gemini", {("x0", "a"): "맞다", ("x1", "a"): "어긋난다"})
    _판정(tmp_path, "pplx", {("x0", "a"): "어긋난다", ("x1", "a"): "어긋난다"})
    L.agree("t", ["gpt", "gemini", "pplx"])
    out = capsys.readouterr().out
    for a, b in (("gpt", "gemini"), ("gpt", "pplx"), ("gemini", "pplx")):
        assert f"{a} 대 {b}" in out, f"{a}·{b} 쌍이 안 났다"
    assert "3 이 다 본 줄 2 · 만장일치 0" in out
    assert "카파는 관측이지" in out           # 이 수로 가설을 판정하지 않는다(§216)


def test_판정자가_겹치면_멈춘다(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    try:
        L.main(["agree", "--name", "t", "--judges", "gpt,gpt"])
    except SystemExit as e:
        assert "같은 이름이 두 번" in str(e)
    else:
        raise AssertionError("한 판정자를 두 번 셌는데 통과했다")


def test_격차에_구간이_붙는다(tmp_path, monkeypatch, capsys):
    """★ **H-081 의 미리 긋는 선을 이 도구가 낸다**(DECISIONS §226). 뚜렷이 다른 둘은 0 을 안 품는다."""
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    _셋(tmp_path, 맞는쪽=20)                   # 4b 0.5 · 12b 1.0
    L.gap("t", "4b", "12b", ["gpt", "gemini", "pplx"], n=400)
    out = capsys.readouterr().out
    assert "뜻이 맞다 — 12b 1.0000 · 4b 0.5000" in out
    assert "12b 이(가) 앞선다" in out and "못 가른다" not in out
    assert "판정자를 하나씩 빼도 부호가 남는다" in out
    assert "판정자 3" in out
    # ★ **크기는 안 옮긴다**(§118) — 수를 그냥 적으면 다음 판정자에서 틀린 말이 된다
    assert "«이 판정자들에서»" in out


def test_같은_둘은_0_을_품는다(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    _셋(tmp_path, 맞는쪽=40)                   # 둘 다 1.0
    L.gap("t", "4b", "12b", ["gpt", "gemini", "pplx"], n=400)
    assert "못 가른다" in capsys.readouterr().out


def test_판정자마다의_수와_하나_뺀_부호를_같이_낸다(tmp_path, monkeypatch, capsys):
    """★ **부호가 한 판정자에게 달렸으면 결론에 단서를 단다** — 관측이지 판정 기준이 아니다."""
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    표 = {("x0", "4b"): "맞다", ("x0", "12b"): "어긋난다",
         ("x1", "4b"): "맞다", ("x1", "12b"): "어긋난다"}
    _판정(tmp_path, "gpt", 표)
    _판정(tmp_path, "gemini", 표)
    뒤집 = {k: ("어긋난다" if v == "맞다" else "맞다") for k, v in 표.items()}
    _판정(tmp_path, "pplx", 뒤집)
    L.gap("t", "4b", "12b", ["gpt", "gemini", "pplx"], n=200)
    out = capsys.readouterr().out
    assert "판정자마다" in out and "하나를 빼면" in out
    assert "부호가 뒤집힌다" in out            # pplx 를 빼면 4b 쪽으로 더 쏠리는 것이 아니라...


def test_없는_팔은_있는_팔을_들고_멈춘다(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    _셋(tmp_path, 맞는쪽=10, n=4)
    try:
        L.gap("t", "4b", "nova", ["gpt", "gemini", "pplx"])
    except SystemExit as e:
        assert "표에 있는 팔 : 12b · 4b" in str(e) and "--arm" in str(e)
    else:
        raise AssertionError("없는 팔인데 통과했다")


def test_판정자_하나로도_격차는_난다(tmp_path, monkeypatch, capsys):
    """`agree` 는 둘이 있어야 하지만 `gap` 은 하나로도 난다 — 다만 구간이 넓어질 뿐이다."""
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    _셋(tmp_path, 맞는쪽=20)
    L.gap("t", "4b", "12b", ["gpt"], n=200)
    assert "판정자 1" in capsys.readouterr().out


def test_모델을_안_적으면_판정을_안_받는다(tmp_path, monkeypatch):
    """★ **이름은 자리이고 모델이 자다**(DECISIONS §227). 무료 등급은 뒤의 모델을 말없이 바꾼다."""
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    try:
        L.main(["read", "--name", "t", "--judge", "gemini"])
    except SystemExit as e:
        assert "--model 이 없다" in str(e) and "--model <무엇>" in str(e)
    else:
        raise AssertionError("무엇이 판정했는지 없이 통과했다")


def test_무엇이_판정했는지가_결과에_붙는다(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    _셋(tmp_path, 맞는쪽=20)
    (tmp_path / "t.gpt.jsonl").write_text(
        json.dumps({"meta": True, "judge": "gpt", "model": "GPT-5 · 무료"}, ensure_ascii=False) + "\n"
        + "\n".join(x for x in (tmp_path / "t.gpt.jsonl").read_text(encoding="utf-8").splitlines()[1:]) + "\n",
        encoding="utf-8")
    L.gap("t", "4b", "12b", ["gpt", "gemini"], n=200)
    out = capsys.readouterr().out
    assert "gpt(GPT-5 · 무료)" in out
    assert "gemini(**안 적혔다**)" in out and "말없이 바꾼다" in out


def test_지시문이_검색을_막는다():
    """★ 공식 한국어판은 **기계 번역 + 후편집**이라 정답이 아니다(DECISIONS §223).

    검색하는 판정자는 그것과 대조하고, 그러면 이 시험은 **천장과 얼마나 같은가**가 된다.
    """
    assert "검색하지 마세요" in L.PROMPT
    assert "정답이 아닙니다" in L.PROMPT


def test_한_판정자에게_달린_부호는_못_가른다로_적는다(tmp_path, monkeypatch, capsys):
    """★ **§118 이 「수준은 판정자가 정한다」 를 실측했다** — 같은 팔에 0.883 과 0.433 이 나왔다.

    구간은 **줄만** 재표집하므로 판정자 사이의 퍼짐을 안 본다. 그래서 하나를 뺀 부호는
    구경거리가 아니라 **선의 일부**다(H-081 ③).
    """
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    # 둘은 4b 를 낫다고 보고, 하나는 반대로 본다 — 합치면 4b 쪽이지만 한 판정자에게 달렸다
    n = 30
    센쪽 = {}
    반대 = {}
    for i in range(n):
        rid = f"x{i:03d}"
        센쪽[(rid, "4b")], 센쪽[(rid, "12b")] = "맞다", ("맞다" if i < 10 else "어긋난다")
        반대[(rid, "4b")], 반대[(rid, "12b")] = ("맞다" if i < 3 else "어긋난다"), "맞다"
    _판정(tmp_path, "gpt", 센쪽)
    _판정(tmp_path, "gemini", 센쪽)
    _판정(tmp_path, "pplx", 반대)
    L.gap("t", "4b", "12b", ["gpt", "gemini", "pplx"], n=400)
    out = capsys.readouterr().out
    assert "부호가 뒤집힌다" in out
    assert "판정 : **못 가른다**" in out and "gpt · gemini 없이는" in out


def _표와_열쇠(tmp_path, n=6):
    """작은 채점표와 열쇠. `make` 를 거치지 않고 `read` 만 시험한다."""
    key = [{"tag": f"t{i}", "id": f"x{i//2:03d}", "arm": ("4b", "12b")[i % 2]} for i in range(n)]
    (tmp_path / "t.key.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in key) + "\n", encoding="utf-8")
    return key


def test_머리줄이_없는_답은_첫_줄을_안_먹는다(tmp_path, monkeypatch, capsys):
    """★ **판정자의 답에는 머리줄이 없다**(DECISIONS §228).

    예전에는 첫 줄을 무조건 버렸다. 2026-09-30 네 판정자가 전부 179/180 으로 들어왔고
    `gap` 의 줄이 60 에서 59 로 줄었다 — **진짜 판정 한 줄이 조용히 먹혔다.**
    """
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    key = _표와_열쇠(tmp_path)
    답 = tmp_path / "답.tsv"
    답.write_text("\n".join(f"{r['tag']}\t맞다" for r in key) + "\n", encoding="utf-8")
    L.read("t", 답, "gpt", "무엇")
    out = capsys.readouterr()
    assert f"{len(key)}줄 / 열쇠 {len(key)}" in out.out, out.out
    assert "안 왔다" not in out.err


def test_머리줄이_있으면_그대로_버린다(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    key = _표와_열쇠(tmp_path)
    답 = tmp_path / "답.tsv"
    답.write_text("\t".join(L.HEAD) + "\n"
                  + "\n".join(f"{r['tag']}\t원문\t번역\t맞다" for r in key) + "\n", encoding="utf-8")
    L.read("t", 답, "gpt", "무엇")
    assert f"{len(key)}줄 / 열쇠 {len(key)}" in capsys.readouterr().out


def test_모자라면_도구가_소리친다(tmp_path, monkeypatch, capsys):
    """★ **사람 눈은 강제자가 아니다.** 「180 찍히는지 보라」 고 맡겼더니 넷 다 179 로 지나갔다."""
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    key = _표와_열쇠(tmp_path)
    답 = tmp_path / "답.tsv"
    답.write_text("\n".join(f"{r['tag']}\t맞다" for r in key[1:]) + "\n", encoding="utf-8")
    L.read("t", 답, "gpt", "무엇")
    out = capsys.readouterr()
    assert f"{len(key) - 1}줄 / 열쇠 {len(key)}" in out.out
    assert "열쇠 6 중 1 이 안 왔다" in out.err and key[0]["tag"] in out.err
    assert "labels.py read" in out.err            # 넘는 길을 든다(DECISIONS §210)


# ── corr — 자가 사람과 같은 순서로 줄을 세우는가(H-084 · DECISIONS §242) ──────────────

def _판정지(tmp, name, judge, 판정: dict[tuple[str, str], str]):
    rows = [{"meta": True, "model": f"{judge} 모형"}]
    rows += [{"tag": f"t{k}", "id": i, "arm": a, "verdict": v} for k, ((i, a), v) in enumerate(판정.items())]
    (tmp / f"{name}.{judge}.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def _자(tmp, 이름, 점수: dict[tuple[str, str], float]):
    p = tmp / f"{이름}.jsonl"
    p.write_text("\n".join(json.dumps({"id": i, "arm": a, "score": s}, ensure_ascii=False)
                           for (i, a), s in 점수.items()) + "\n", encoding="utf-8")
    return p


def test_동점은_평균_순위를_나눈다():
    """★ 사람 점수는 판정자 넷이라 값이 다섯뿐이다 — **동점이 대부분**이고, 그냥 매기면
    들어온 차례가 상관이 된다."""
    assert L._순위([1.0, 1.0, 2.0]) == [1.5, 1.5, 3.0]
    assert L._순위([3.0, 1.0, 2.0]) == [3.0, 1.0, 2.0]


def test_스피어만은_순서만_본다():
    """★ 단위가 달라도 순서가 같으면 1 이다 — QE 의 3.2 와 사람의 0.75 는 단위가 다르다."""
    assert L.스피어만([1, 2, 3, 4], [10, 20, 30, 40]) == 1.0
    assert L.스피어만([1, 2, 3, 4], [4, 3, 2, 1]) == -1.0
    assert L.스피어만([1, 1, 1, 1], [1, 2, 3, 4]) is None       # 한쪽이 상수면 정의되지 않는다
    assert L.스피어만([1, 2], [1, 2]) is None                   # 셋 미만은 안 잰다


def test_사람_점수는_판정자_평균이다(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    _판정지(tmp_path, "t", "a", {("x1", "4b"): "맞다", ("x2", "4b"): "어긋난다"})
    _판정지(tmp_path, "t", "b", {("x1", "4b"): "맞다", ("x2", "4b"): "맞다"})
    사람 = L.사람점수(L.판정들("t", ["a", "b"]))
    assert 사람 == {("x1", "4b"): 1.0, ("x2", "4b"): 0.5}


def test_사람과_같은_순서면_상관이_1_이다(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    판정 = {(f"x{i}", "4b"): ("맞다" if i % 2 else "어긋난다") for i in range(10)}
    _판정지(tmp_path, "t", "a", 판정)
    좋은 = _자(tmp_path, "좋은", {k: (1.0 if v == "맞다" else 0.0) for k, v in 판정.items()})
    L.corr("t", ["a"], {"좋은": 좋은}, "", n=200)
    out = capsys.readouterr().out
    assert "ρ +1.0000" in out


def test_거꾸로_가리키는_자는_음수로_나온다(tmp_path, monkeypatch, capsys):
    """★ **2026-09-30 `term_off` 가 그랬다** — 배포본 대비 부호가 사람과 반대였다(DECISIONS §229)."""
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    판정 = {(f"x{i}", "4b"): ("맞다" if i % 2 else "어긋난다") for i in range(10)}
    _판정지(tmp_path, "t", "a", 판정)
    거꾸로 = _자(tmp_path, "거꾸로", {k: (0.0 if v == "맞다" else 1.0) for k, v in 판정.items()})
    L.corr("t", ["a"], {"거꾸로": 거꾸로}, "", n=200)
    assert "ρ -1.0000" in capsys.readouterr().out


def test_기준과의_차를_같은_재표집에서_낸다(tmp_path, monkeypatch, capsys):
    """★ **따로 내면 두 구간이 겹치는지만 안다** — 「한쪽이 낫다」 는 짝지어야 나온다."""
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    판정 = {(f"x{i}", "4b"): ("맞다" if i % 2 else "어긋난다") for i in range(20)}
    _판정지(tmp_path, "t", "a", 판정)
    좋은 = _자(tmp_path, "좋은", {k: (1.0 if v == "맞다" else 0.0) for k, v in 판정.items()})
    나쁜 = _자(tmp_path, "나쁜", {k: 0.5 + 0.01 * n for n, k in enumerate(판정)})
    L.corr("t", ["a"], {"나쁜": 나쁜, "좋은": 좋은}, "나쁜", n=200)
    out = capsys.readouterr().out
    assert "← 기준" in out and "차(− 나쁜)" in out


def test_기준_이름이_틀리면_멈춘다(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    _판정지(tmp_path, "t", "a", {(f"x{i}", "4b"): "맞다" for i in range(5)})
    자 = _자(tmp_path, "하나", {(f"x{i}", "4b"): float(i) for i in range(5)})
    try:
        L.corr("t", ["a"], {"하나": 자}, "없는자")
    except SystemExit as e:
        assert "--자 에 없다" in str(e)
    else:
        raise AssertionError("안 멈췄다")


def test_자가_안_매긴_쌍을_찍는다(tmp_path, monkeypatch, capsys):
    """★ **`term_off` 는 모든 줄을 못 매긴다** — 용어가 없는 줄에는 값이 없다. 그것이 보여야 한다."""
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    판정 = {(f"x{i}", "4b"): ("맞다" if i % 2 else "어긋난다") for i in range(10)}
    _판정지(tmp_path, "t", "a", 판정)
    일부 = _자(tmp_path, "일부", {k: float(n) for n, k in enumerate(판정) if n < 6})
    L.corr("t", ["a"], {"일부": 일부}, "", n=100)
    assert "4 쌍을 이 자가 안 매겼다" in capsys.readouterr().out


def test_칸이_빠진_점수_파일은_멈춘다(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    p = tmp_path / "나쁜꼴.jsonl"
    p.write_text(json.dumps({"id": "x1", "score": 1.0}) + "\n", encoding="utf-8")
    try:
        L.자점수(p)
    except SystemExit as e:
        assert "`arm` 가 없다" in str(e)
    else:
        raise AssertionError("안 멈췄다")


def test_규칙_점수는_분모가_0_인_줄을_안_낸다():
    """★ **값이 없는 것과 0 은 다르다** — 용어가 없는 줄을 0 으로 적으면 「다 틀린 줄」 과 같아진다."""
    글 = (ROOT / "tools/labels.py").read_text(encoding="utf-8")
    assert "if 분모:" in 글 and "안 낸다" in 글


# ── 표가 제 판을 든다(DECISIONS §243) ──────────────────────────────────────────────

def test_표가_어느_판에서_났는지_든다(tmp_path):
    """★ **2026-09-30 판정 360 판을 들고도 그 줄을 만든 판을 못 찾았다** — 열쇠가 태그·줄·팔만 들었다."""
    a, b = _run(tmp_path, "4b"), _run(tmp_path, "12b")
    _, _, 판 = L.make({"4b": a, "12b": b}, ROWS, "t", 5, 31)
    assert set(판) == {"4b", "12b"}
    assert 판["4b"]["run"] == str(a) and 판["4b"]["set_sha256"] == "same"


def test_판은_열쇠의_머리줄에_산다(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    a, b = _run(tmp_path, "4b"), _run(tmp_path, "12b")
    _, key, 판 = L.make({"4b": a, "12b": b}, ROWS, "t", 5, 31)
    머리 = {"meta": True, "name": "t", "seed": 31, "판": 판}
    (tmp_path / "t.key.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in [머리] + key) + "\n", encoding="utf-8")
    assert L.어느판인가("t")["12b"]["run"] == str(b)


def test_판이_안_적힌_옛_표는_빈_것을_준다(tmp_path, monkeypatch):
    """★ **「안 적혔다」 를 「판이 없다」 로 읽으면 안 된다** — 부르는 쪽이 길을 든다."""
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    (tmp_path / "옛.key.jsonl").write_text(
        json.dumps({"tag": "x", "id": "x001", "arm": "a"}, ensure_ascii=False) + "\n", encoding="utf-8")
    assert L.어느판인가("옛") == {}
    assert L.어느판인가("아예없음") == {}


def test_머리줄이_있어도_read_가_안_먹는다(tmp_path, monkeypatch, capsys):
    """★ 열쇠에 머리줄이 생겼다 — **판정 한 줄이 조용히 먹히면 안 된다**(DECISIONS §228)."""
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    sheet, key, 판 = L.make({"a": _run(tmp_path, "4b"), "b": _run(tmp_path, "12b")}, ROWS, "t", 5, 31)
    머리 = {"meta": True, "name": "t", "seed": 31, "판": 판}
    (tmp_path / "t.key.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in [머리] + key) + "\n", encoding="utf-8")
    줄 = sheet.splitlines()
    매긴 = [줄[0]] + [ln + "맞다" for ln in 줄[1:]]
    (tmp_path / "s.tsv").write_text("\n".join(매긴) + "\n", encoding="utf-8")
    L.read("t", tmp_path / "s.tsv", "j", "모형")
    assert "10줄 / 열쇠 10" in capsys.readouterr().out


def test_없는_점수_파일은_역추적이_아니라_말을_한다(tmp_path):
    """★ **벽도 없고 길도 없는 자리를 안 만든다**(DECISIONS §232). 2026-09-30 이 자리가 역추적을 냈다."""
    try:
        L.자점수(tmp_path / "없다.jsonl")
    except SystemExit as e:
        assert "점수 파일이 없다" in str(e) and "labels.py rule" in str(e)
    else:
        raise AssertionError("안 멈췄다")


def test_없는_판은_역추적이_아니라_말을_한다(tmp_path):
    try:
        L.규칙점수(tmp_path / "없다.jsonl", "4b", "term_off")
    except SystemExit as e:
        assert "판(`4b`)이 없다" in str(e) and "ls -t runs" in str(e)
    else:
        raise AssertionError("안 멈췄다")


def test_자마다_못_매기는_줄이_달라도_안_죽는다(tmp_path, monkeypatch, capsys):
    """★ **2026-09-30 여기서 죽었다** — `lit` 의 쌍으로 `term_off` 를 찾다가 KeyError 였다.
    혼자 서는 ρ 와 견주는 ρ 는 **다른 쌍에서 난다**(DECISIONS §244)."""
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    판정 = {(f"x{i}", "4b"): ("맞다" if i % 2 else "어긋난다") for i in range(12)}
    _판정지(tmp_path, "t", "a", 판정)
    넓은 = _자(tmp_path, "넓은", {k: float(n) for n, k in enumerate(판정)})
    좁은 = _자(tmp_path, "좁은", {k: float(n) for n, k in enumerate(판정) if n >= 4})
    L.corr("t", ["a"], {"넓은": 넓은, "좁은": 좁은}, "넓은", n=100)
    out = capsys.readouterr().out
    assert "쌍 8 에서 잰 것이다" in out, out


def test_겹치는_쌍이_없으면_차를_못_잰다고_말한다(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    판정 = {(f"x{i}", "4b"): ("맞다" if i % 2 else "어긋난다") for i in range(10)}
    _판정지(tmp_path, "t", "a", 판정)
    앞 = _자(tmp_path, "앞", {k: float(n) for n, k in enumerate(판정) if n < 5})
    뒤 = _자(tmp_path, "뒤", {k: float(n) for n, k in enumerate(판정) if n >= 5})
    L.corr("t", ["a"], {"앞": 앞, "뒤": 뒤}, "앞", n=50)
    assert "둘 다 매긴 쌍이 0 이다" in capsys.readouterr().out


def test_작을수록_좋은_지표는_부호를_뒤집어_낸다():
    """★ **안 뒤집으면 잘 맞는 자가 음수로 나오고** 「거꾸로 가리킨다」 와 구별되지 않는다."""
    assert "term_bad" in L.작을수록 and "term_off" not in L.작을수록


def test_줄_수를_찍는다(tmp_path, monkeypatch, capsys):
    """★ **재표집의 단위는 줄이다 — 쌍이 아니다**(DECISIONS §245). 한 줄의 팔 셋은 독립이 아니다."""
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    판정 = {(f"x{i}", a): ("맞다" if i % 2 else "어긋난다")
            for i in range(7) for a in ("4b", "12b", "nova")}
    _판정지(tmp_path, "t", "a", 판정)
    자 = _자(tmp_path, "자", {k: float(n) for n, k in enumerate(판정)})
    L.corr("t", ["a"], {"자": 자}, "", n=100)
    out = capsys.readouterr().out
    assert "**줄 7** · 쌍 21" in out, out
    assert "줄이 7 이다" in out and "정밀도를 말할 수 없다" in out


def test_줄이_넉넉하면_경고가_안_붙는다(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    판정 = {(f"x{i}", "4b"): ("맞다" if i % 2 else "어긋난다") for i in range(L.얇다 + 5)}
    _판정지(tmp_path, "t", "a", 판정)
    자 = _자(tmp_path, "자", {k: float(n) for n, k in enumerate(판정)})
    L.corr("t", ["a"], {"자": 자}, "", n=50)
    assert "정밀도를 말할 수 없다" not in capsys.readouterr().out


def test_지난_표가_본_줄을_뺀다(tmp_path, monkeypatch, capsys):
    """★ **같은 줄로 또 만들면 재표집 단위가 안 늘어난다**(DECISIONS §216 · §249)."""
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    a, b = _run(tmp_path, "4b"), _run(tmp_path, "12b")
    _, key, 판 = L.make({"4b": a, "12b": b}, ROWS, "첫판", 5, 31)
    머리 = {"meta": True, "name": "첫판", "seed": 31, "판": 판}
    (tmp_path / "첫판.key.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in [머리] + key) + "\n", encoding="utf-8")
    첫줄 = {r["id"] for r in key}
    assert len(첫줄) == 5

    _, key2, _ = L.make({"4b": a, "12b": b}, ROWS, "둘째", 5, 31, 빼고=["첫판"])
    둘째줄 = {r["id"] for r in key2}
    assert len(둘째줄) == 5
    assert not (첫줄 & 둘째줄), "지난 표가 본 줄이 또 뽑혔다 — 떼어두기가 아니다"
    assert "본 줄 5 을 뺐다" in capsys.readouterr().out


def test_뺄_표가_없으면_말을_한다(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    try:
        L.이미_본_줄(["없는표"])
    except SystemExit as e:
        assert "뺄 표의 열쇠가 없다" in str(e) and "ls " in str(e)
    else:
        raise AssertionError("안 멈췄다")


def test_빼고_나서_줄이_모자라면_멈춘다(tmp_path, monkeypatch):
    """★ **모자란 채로 뽑지 않는다** — 떼어두기가 셋을 다 먹으면 그 셋으로는 못 한다."""
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    a, b = _run(tmp_path, "4b"), _run(tmp_path, "12b")
    _, key, 판 = L.make({"4b": a, "12b": b}, ROWS, "첫판", 18, 31)
    머리 = {"meta": True, "name": "첫판", "seed": 31, "판": 판}
    (tmp_path / "첫판.key.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in [머리] + key) + "\n", encoding="utf-8")
    try:
        L.make({"4b": a, "12b": b}, ROWS, "둘째", 10, 31, 빼고=["첫판"])
    except SystemExit as e:
        assert "뿐인데 10 을 달라고 했다" in str(e)
    else:
        raise AssertionError("안 멈췄다")


def test_이미_쓴_이름에는_안_만든다(tmp_path, monkeypatch):
    """★ **있는 표를 말없이 덮지 않는다**(DECISIONS §256). 2026-10-01 판정 180 건이 딸린
    열쇠를 덮었다 — 열쇠가 바뀌면 그 판정들은 **다른 줄을 가리킨다.**"""
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    (tmp_path / "t.key.jsonl").write_text(json.dumps({"meta": True}) + "\n", encoding="utf-8")
    try:
        L._이름이_비었나("t")
    except SystemExit as e:
        assert "이미 쓴 이름이다" in str(e) and "--name tb" in str(e)
        assert "다른 줄을 가리킨다" in str(e)
    else:
        raise AssertionError("안 멈췄다")


def test_판정_파일만_있어도_막는다(tmp_path, monkeypatch):
    """★ 열쇠를 지우고 다시 만들어도 **판정 파일이 남아 있으면 그 이름은 쓰인 이름이다.**"""
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    (tmp_path / "t.gpt.jsonl").write_text(json.dumps({"meta": True}) + "\n", encoding="utf-8")
    assert L.쓰인_이름인가("t") == ["t.gpt.jsonl"]
    try:
        L._이름이_비었나("t")
    except SystemExit as e:
        assert "t.gpt.jsonl" in str(e), "무엇이 걸렸는지를 이름으로 든다"
    else:
        raise AssertionError("안 멈췄다")


def test_새_이름은_그냥_지나간다(tmp_path, monkeypatch):
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    assert L._이름이_비었나("새것") is None
    assert L.쓰인_이름인가("새것") == []


def test_덮는다를_주면_지나간다(tmp_path, monkeypatch):
    """★ 막되 **넘는 길을 준다**(DECISIONS §210) — 다만 기본은 막는 쪽이다."""
    monkeypatch.setattr(L, "out_dir", lambda: tmp_path)
    (tmp_path / "t.key.jsonl").write_text(json.dumps({"meta": True}) + "\n", encoding="utf-8")
    assert L._이름이_비었나("t", 덮는다=True) is None
