"""평가셋의 불변식. **자가 틀리면 모든 측정이 틀린다.**"""
import json
import pathlib

import pytest

from seshat import evaluate as ev

ROOT = pathlib.Path(__file__).resolve().parents[1]

SEED = pathlib.Path(__file__).resolve().parents[1] / "data/eval/seed.jsonl"


def test_머리줄이_출처와_라이선스를_적는다():
    meta = json.loads(SEED.read_text(encoding="utf-8").splitlines()[0])
    assert meta["meta"] is True and meta["license"]


def test_id_가_겹치지_않는다():
    ids = [r["id"] for r in ev.load(str(SEED))]
    assert len(ids) == len(set(ids))


def test_정답이_스스로_지키는_것을_지킨다():
    # 정답이 keep 을 어기거나 해요체로 끝나면 모델이 맞혀도 틀린 것으로 센다.
    for r in ev.load(str(SEED)):
        for k in r.get("keep", []):
            assert k in r["ref"], (r["id"], k)
        assert ev.is_hapsyo(r["ref"]), r["id"]


def test_flores_받는_도구가_env_를_얹는다():
    """`HF_TOKEN` 을 `.env` 에 적게 해 놓고 도구가 그것을 안 읽으면, 적어 두고 헤맨다(DECISIONS §39)."""
    import pathlib
    src = (pathlib.Path(__file__).resolve().parent.parent / "tools/fetch_flores.py").read_text(encoding="utf-8")
    assert "import seshat" in src                      # 불러 오는 것이 곧 .env 를 얹는 일이다
    tmpl = (pathlib.Path(__file__).resolve().parent.parent / ".env.example").read_text(encoding="utf-8")
    assert "HF_TOKEN=" in tmpl                         # 자리가 템플릿에 있어야 다음 기계에서 안 헤맨다


def _flores():
    import importlib.util
    import pathlib
    root = pathlib.Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location("fetch_flores", root / "tools/fetch_flores.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_flores_는_형식을_가정하지_않는다(tmp_path):
    """2026-09 저장소는 `dev/kor_Hang.jsonl` 이고 종전에는 parquet 이었다(DECISIONS §71)."""
    import json
    m = _flores()
    p = tmp_path / "kor_Hang.jsonl"
    p.write_text(json.dumps({"id": 1, "text": "가", "iso_639_3": "kor"}, ensure_ascii=False) + "\n",
                 encoding="utf-8")
    assert m.read_rows(p) == [{"id": 1, "text": "가"}]          # 다른 칸은 안 본다
    import pathlib
    assert m.split_of(pathlib.Path("dev/kor_Hang.jsonl")) == "dev"
    assert m.split_of(pathlib.Path("devtest/eng_Latn.jsonl")) == "devtest"


def test_없는_평가셋은_받는_법을_말한다():
    """셋은 대개 커밋하지 않는다 — 없을 때 무엇을 치면 되는지 카탈로그가 안다(DECISIONS §72).

    ★ **있는 이름을 쓰지 않는다**(DECISIONS §78). 처음에는 `flores_plus.dev.jsonl` 로 썼는데, 그 셋을
      받은 기계에서는 파일이 생겨 시험이 깨졌다. 없음을 재는 시험은 **결코 생기지 않을 이름**을 쓴다.
    """
    import pytest

    from seshat import evaluate as ev

    with pytest.raises(SystemExit) as e:
        ev.load("data/bench/받은적없는셋.jsonl")
    말 = str(e.value)
    assert "tools/fetch_flores.py" in 말 and "flores-plus" in 말

    with pytest.raises(SystemExit) as e2:
        ev.load("data/probes/없는탐침.jsonl")
    assert "tools/make_probes.py" in str(e2.value)


def _fetch():
    import importlib.util
    s = importlib.util.spec_from_file_location("fa", ROOT / "tools/fetch_awsdocs.py")
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def test_떼어둔_셋은_겹친_문장을_뺀다(tmp_path):
    """★ **씨만 바꾸면 겹친다**(DECISIONS §188). 같은 못에서 다시 뜨는 것이므로 몇십 줄은
    반드시 같이 나오고, 그 줄은 **사전을 캘 때 본 줄**이다 — 그러면 떼어둔 것이 아니다(DECISIONS §192)."""
    fa = _fetch()
    옛 = tmp_path / "d001.jsonl"
    옛.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in [
        {"meta": True, "about": "옛 셋"},
        {"id": "a", "src": "Use Amazon S3 to store objects."},
        {"id": "b", "src": "Create a DynamoDB table."}]) + "\n", encoding="utf-8")
    뺄것 = fa.이미_쓴_문장([str(옛)])
    assert 뺄것 == {"Use Amazon S3 to store objects.", "Create a DynamoDB table."}

    줄 = [fa.Line("Use Amazon S3 to store objects.", ()), fa.Line("A brand new sentence here.", ()),
          fa.Line("Create a DynamoDB table.", ()), fa.Line("Another fresh one for the pool.", ())]
    got = fa.choose({"g": 줄}, 2, 21, 400, 뺄것)
    assert {x[0] for x in got} == {"A brand new sentence here.", "Another fresh one for the pool."}


def test_없는_셋을_빼라고_하면_멈춘다(tmp_path):
    import pytest

    fa = _fetch()
    with pytest.raises(SystemExit):
        fa.이미_쓴_문장([str(tmp_path / "없다.jsonl")])


def test_합쇼체를_물을_수_없는_줄은_분모에서_뺀다(tmp_path):
    """★ **원문이 명사구면 종결어미가 설 자리가 없다**(DECISIONS §194). 그런 줄을
    분모에 넣으면 `style` 이 거짓으로 낮아진다 — d001 에서 걸린 13줄 중 셋이 그것이었다(§190).

    ★ **판정은 사람이 하고 기계는 읽기만 한다**(§189). 파서를 놓으면 그 파서가 또 자가 된다.
    """
    셋 = tmp_path / "x.jsonl"
    셋.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in [
        {"meta": True, "about": "시험용"},
        {"id": "a", "src": "Create a bucket."},
        {"id": "b", "src": "A list of triggers."},
        {"id": "c", "src": "Delete the table."}]) + "\n", encoding="utf-8")
    (tmp_path / "x.style-na.txt").write_text("# 주석은 무시한다\nb   # 명사구\n", encoding="utf-8")

    assert ev.문체_밖(셋) == {"b"}
    rows = ev.load(str(셋))
    assert [r.get("style_na") for r in rows] == [None, True, None]

    outs = ["버킷을 만듭니다.", "트리거 목록.", "표를 지운다."]
    got = ev.score(rows, outs)
    assert got["style_n"] == 2, "명사구 줄은 분모에 없다"
    assert got["style"] == 0.5, "남은 둘 중 하나만 합쇼체다 — 명사구를 넣었으면 1/3 이 된다"


def test_옆_파일이_없으면_아무것도_안_뺀다(tmp_path):
    """★ **없는 것을 있는 것처럼 굴지 않는다.** 대부분의 셋은 이 파일이 없다."""
    셋 = tmp_path / "y.jsonl"
    셋.write_text(json.dumps({"meta": True}) + "\n" + json.dumps({"id": "a", "src": "x"}) + "\n",
                  encoding="utf-8")
    assert ev.문체_밖(셋) == set()
    assert ev.load(str(셋))[0].get("style_na") is None


@pytest.mark.parametrize("글, 조각", [
    # 홀로 선 한 글자 — 자르면 안 된다(DECISIONS §195). d001 · d002 에서 실제로 잘린 꼴이다
    ("Use the US East (N. Virginia) Region for this bucket.", 1),
    ("Auto-termination is available in US East (N. Virginia) and US West (Oregon).", 1),
    # 약어로 끝나는 정상 문장 — **자르는 것이 맞다.** 넓게 막으면 이쪽이 다 붙는다
    ("Configure access with IAM. Then attach the policy.", 2),
    ("Upload the file to S3. The object appears in the console.", 2),
    ("See the guide. Also read the FAQ.", 2),
])
def test_약어_마침표에서_문장을_안_자른다(글, 조각):
    """★ **잘린 줄은 번역이 될 수가 없다**(DECISIONS §195). `… for the US East (N.` 은 `style` 만이
    아니라 `term` · `keep` 의 분모까지 더럽힌다 — d001 에 하나, d002 에 셋 있었다.

    ★ **넓게 막으면 더 나쁘다.** AWS 문서는 약어로 끝나는 문장이 흔해서, 대문자 마침표를 통째로
      막으면 정상 문장이 줄줄이 붙는다. **앞이 글자가 아닌 한 글자**일 때만 막는다.
    """
    fa = _fetch()
    assert len(fa._SPLIT.split(글)) == 조각
