"""평가셋의 불변식. **자가 틀리면 모든 측정이 틀린다.**"""
import json
import pathlib

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
