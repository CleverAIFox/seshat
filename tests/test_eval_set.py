"""평가셋의 불변식. **자가 틀리면 모든 측정이 틀린다.**"""
import json
import pathlib

from seshat import evaluate as ev

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
