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


def test_ollama_백엔드는_틀과_결정성을_싣는다(monkeypatch):
    # ★ 가짜 ollama — 받은 요청을 적고, 자리표시가 있으면 그대로 돌려준다
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer
    got = []

    class H(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            got.append(body)
            text = body["prompt"].rsplit("\n\n\n", 1)[1]
            reply = text.replace("Use ", "").replace(".", "를 씁니다.")
            data = json.dumps({"response": reply}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setenv("OLLAMA_URL", f"http://127.0.0.1:{srv.server_address[1]}")
    try:
        fn, model = backends.get("translategemma-4b+ph")
        out = fn(["Use Amazon EMR."], {})
    finally:
        srv.shutdown()
    assert model == "translategemma:4b+ph"
    assert got[0]["model"] == "translategemma:4b"
    assert got[0]["options"]["seed"] == 42 and got[0]["options"]["temperature"] == 0
    assert "⟦T1⟧" in got[0]["prompt"] and "Amazon EMR" not in got[0]["prompt"]
    # ★ 모델은 ⟦T1⟧를 썼지만 EMR 은 ㄹ로 끝난다 — 되돌리며 '을' 로 고친다
    assert out == ["Amazon EMR을 씁니다."]


def test_문체_지시_팔은_틀을_한_문단만_바꾼다():
    """한 번에 한 가지만 바꾼다(DECISIONS §27). 틀 전체를 다시 쓰면 무엇이 효과인지 못 가른다."""
    from seshat import backends as b
    base, styled = b.TRANSLATEGEMMA_PROMPT, b.TRANSLATEGEMMA_PROMPT_HAPSYO
    assert styled != base and styled.endswith("{text}")
    assert "합쇼체" in styled and "-ㅂ니까" in styled
    added = len(styled) - len(base)
    assert 0 < added < 250                                   # 한 문단이다
    assert "translategemma-4b+ph+style" in b.REGISTRY and "translategemma-4b+ph+style" in b.WEIGHTS


def test_끼울_후보는_자리표시와_종결_정규화를_함께_쓴다():
    """H-016 · H-023 채택의 결과다(DECISIONS §33). 채택한 것이 등록부에 없으면 쓰이지 않는다."""
    from seshat import backends as b
    name = "translategemma-4b+ph+endings"
    assert name in b.REGISTRY and name in b.WEIGHTS and name in b.DECODING_OF
    fn, model = b.REGISTRY[name]
    assert model.endswith("+ph+endings")
    out = b.with_endings(lambda texts, terms: ["무엇인가요?"])(["x"], {})
    assert out == ["무엇입니까?"]


def test_리전이_없으면_먼저_멈춘다(monkeypatch):
    """botocore 의 NoRegionError 는 무엇을 적어야 하는지 말하지 않는다(DECISIONS §36)."""
    import pytest

    from seshat import backends as b
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)
    with pytest.raises(SystemExit) as e:
        b.aws_translate(["x"], {})
    assert "AWS_REGION" in str(e.value)
