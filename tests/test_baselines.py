"""기준선 백엔드와 범용 평가셋 도구(DECISIONS §11)."""
import importlib.util
import pathlib

import pytest

from seshat import backends

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("fetch_flores", ROOT / "tools/fetch_flores.py")
ff = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ff)


class FakeTranslate:
    def __init__(self):
        self.calls = []

    def translate_text(self, **kw):
        self.calls.append(kw)
        return {"TranslatedText": "번역:" + kw["Text"]}


def test_AWS_Translate_는_있는_그대로_잰다():
    c = FakeTranslate()
    out = backends.aws_translate(["a", "b"], {"athena": "Athena"}, client=c)
    assert out == ["번역:a", "번역:b"]
    # ★ 용어집을 싣지 않는다 — Custom Terminology 없이 있는 그대로가 기준선이다
    assert all(set(k) == {"Text", "SourceLanguageCode", "TargetLanguageCode"} for k in c.calls)
    assert c.calls[0]["TargetLanguageCode"] == "ko"


def test_기준선_백엔드는_서빙_목록에_없다():
    assert "aws-translate" in backends.BASELINE_ONLY
    assert "echo" not in backends.BASELINE_ONLY


def test_FLORES_는_id_로_짝짓는다():
    eng = [{"id": 2, "text": "B"}, {"id": 1, "text": "A"}]
    kor = [{"id": 1, "text": "가"}, {"id": 2, "text": "나"}]
    rows = ff.pair(eng, kor, "dev")
    assert [(r["src"], r["ref"]) for r in rows] == [("A", "가"), ("B", "나")]


def test_FLORES_id_가_어긋나면_멈춘다():
    with pytest.raises(SystemExit):
        ff.pair([{"id": 1, "text": "A"}], [{"id": 2, "text": "나"}], "dev")


@pytest.mark.parametrize("path,want", [
    ("devtest/kor_Hang.parquet", "devtest"), ("dev/eng_Latn.parquet", "dev"),
    ("data/devtest-00000.kor_Hang.parquet", "devtest"), ("README.md", None),
])
def test_split_을_경로에서_읽는다(path, want):
    assert ff.split_of(pathlib.Path(path)) == want
