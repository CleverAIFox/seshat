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


def test_남의_엔진에_후처리를_얹은_팔도_과금과_서빙_밖이다():
    """무엇이 엔진의 몫이고 무엇이 후처리의 몫인지 가르는 자다(DECISIONS §41)."""
    from seshat import backends as b
    name = "aws-translate+ph+endings"
    assert name in b.REGISTRY
    assert name in b.BASELINE_ONLY                      # 서빙 후보가 아니다
    assert b.PRICE_PER_MCHAR[name] == b.PRICE_PER_MCHAR["aws-translate"]   # 견적이 새지 않는다
    assert name not in b.WEIGHTS                        # 가중치를 부르지 않는다


def test_ollama_위에_서는_백엔드를_이름으로_짐작하지_않는다():
    """재현 조건이 GPU 적재를 적을 자리다 — 목록이 정본이다(DECISIONS §45)."""
    from seshat import backends as b
    assert b.OLLAMA_OF["exaone-3.5-7.8b+ph+endings"] == "exaone3.5:7.8b"
    assert set(b.OLLAMA_OF) <= set(b.REGISTRY)
    local = {k for k in b.REGISTRY if k not in b.BASELINE_ONLY and k != "echo"}
    assert local <= set(b.OLLAMA_OF)              # 서빙 후보는 전부 어디서 도는지 적혀 있다


def test_사고_모드_출력은_번역이_아니다():
    """Qwen3 류가 `<think>` 를 붙이면 검사가 그것을 번역으로 센다(DECISIONS §47)."""
    from seshat import backends as b
    assert b.THINK.sub("", "<think>음... 이건</think>\nAmazon S3를 씁니다.").strip() == "Amazon S3를 씁니다."
    assert b.THINK.sub("", "Amazon S3를 씁니다.") == "Amazon S3를 씁니다."


def test_오디션_후보가_대장과_등록부에_함께_있다():
    """상업 · 교사가 열린 후보만 오디션에 세운다(H-032 · DECISIONS §44)."""
    from seshat import backends as b
    from seshat import licenses as lic
    for name in ("qwen3-8b+ph+endings", "qwen3-4b+ph+endings"):
        w = b.WEIGHTS[name]
        assert lic.LEDGER[w][1] == "yes" and lic.can_teach(w)
        assert name in b.OLLAMA_OF and name in b.DECODING_OF
        assert name not in b.BASELINE_ONLY          # 쓸 수 있는 가중치다 — 서빙 후보로 남는다


def test_범용_모델은_같은_배선을_쓴다():
    """범용 후보끼리는 배선이 같아야 모델끼리 공정하다(DECISIONS §48)."""
    from seshat import backends as b
    assert "Output ONLY the Korean translation" in b.GENERIC_SYSTEM
    assert "placeholder" in b.GENERIC_SYSTEM.lower()      # 자리표시를 지키라고 말한다
    assert b.GENERIC_SYSTEM != b.TRANSLATEGEMMA_PROMPT    # 번역 전용 모델과는 다른 배선이다


def test_채팅_배선은_체계_지시와_사고_끄기를_싣는다(monkeypatch):
    """`/api/generate` 로 보낸 `think: false` 는 안 먹혔다 — 채팅 API 로 보낸다(DECISIONS §48)."""
    import json

    from seshat import backends as b
    seen = {}

    class _R:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps({"message": {"content": "<think>음</think>Amazon S3를 씁니다."}}).encode()

    def fake(req, timeout=0):
        seen["url"] = req.full_url
        seen["body"] = json.loads(req.data)
        return _R()

    monkeypatch.setattr("urllib.request.urlopen", fake)
    out = b.ollama_chat("m", "체계", {"think": False})(["x"], {})
    assert out == ["Amazon S3를 씁니다."]                  # 사고는 벗긴다
    assert seen["url"].endswith("/api/chat")
    assert seen["body"]["think"] is False
    assert [m["role"] for m in seen["body"]["messages"]] == ["system", "user"]


def test_ollama_가_꺼져_있으면_한_줄로_말한다(monkeypatch):
    """40줄 역추적에는 무엇을 해야 하는지가 없다(DECISIONS §51 · §36 과 같은 원칙)."""
    import urllib.error

    import pytest

    from seshat import backends as b

    def dead(req, timeout=0):
        raise urllib.error.URLError(ConnectionRefusedError(111, "Connection refused"))

    monkeypatch.setattr("urllib.request.urlopen", dead)
    with pytest.raises(SystemExit) as e:
        b.ollama("m", "{text}")(["x"], {})
    assert "ollama serve" in str(e.value) and "m" in str(e.value)


def test_재현_조건은_배선에서_나온다():
    """팔을 더하면서 표 하나를 빠뜨리면 `weights: null` 이 실린다 — 재현할 수 없는 결과다(DECISIONS §57)."""
    from seshat import backends as b
    assert set(b.WEIGHTS) == set(b.OLLAMA_OF)              # 손으로 적는 목록이 둘이 아니다
    assert set(b.DECODING_OF) == set(b.OLLAMA_OF)
    for arm, model in b.OLLAMA_OF.items():
        assert b.WEIGHTS[arm] == b.WEIGHTS_OF_MODEL[model]
        assert b.DECODING_OF[arm]["temperature"] == 0


def test_사전_후처리_팔이_등록부와_표에_함께_있다():
    """H-033 의 처치. 후처리만 다르고 가중치 · 복호화는 맨몸 팔과 같아야 대조가 된다(DECISIONS §56)."""
    from seshat import backends as b
    bare, fixed = "gemma3-4b+ph+endings", "gemma3-4b+ph+endings+terms"
    assert fixed in b.REGISTRY and fixed not in b.BASELINE_ONLY
    assert b.WEIGHTS[fixed] == b.WEIGHTS[bare]
    assert b.OLLAMA_OF[fixed] == b.OLLAMA_OF[bare]
    assert b.PRICE_PER_MCHAR["aws-translate+ph+endings+terms"] == b.PRICE_PER_MCHAR["aws-translate"]


# ── 사라진 자리표시만 다시 묻는다(H-034 · DECISIONS §59)
def _calls(answers):
    """부른 횟수를 세는 가짜 백엔드. 답을 차례로 돌려준다."""
    box = {"n": 0}

    def fn(texts, terms_):
        box["n"] += 1
        return [answers[min(box["n"] - 1, len(answers) - 1)] for _ in texts]
    return fn, box


def test_이름이_사라진_줄만_다시_묻는다():
    """고치는 판은 **원문을 그대로** 받는다 — 자리표시가 없는 물음이다(DECISIONS §60)."""
    from seshat import backends as b
    inner, seen = _calls(["⟦T1⟧ API를 호출합니다."])                          # ⟦T2⟧ 를 버렸다
    repair, fixed = _calls(["Amazon S3의 PutObject API를 호출합니다."])
    b.REPAIR_STATS.update(tried=0, fixed=0)
    out = b.with_placeholders(inner, repair=(repair,))(["Call the PutObject API of Amazon S3."], {})
    assert out == ["Amazon S3의 PutObject API를 호출합니다."]
    assert seen["n"] == 1 and fixed["n"] == 1
    assert b.REPAIR_STATS == {"tried": 1, "fixed": 1}


def test_멀쩡한_줄은_다시_묻지_않는다():
    from seshat import backends as b
    inner, _ = _calls(["⟦T1⟧에 씁니다."])
    repair, fixed = _calls(["안 불려야 한다"])
    out = b.with_placeholders(inner, repair=(repair,))(["Write to Amazon S3."], {})
    assert out == ["Amazon S3에 씁니다."] and fixed["n"] == 0


def test_다시_물어도_안_되면_첫_답을_둔다():
    """없는 이름을 지어 넣지 않는다 — 사라진 것은 사라진 것으로 재야 keep 이 진실을 말한다."""
    from seshat import backends as b
    inner, _ = _calls(["⟦T1⟧ API를 호출합니다."])
    first, a = _calls(["또 버린 답입니다."])
    second, c = _calls(["이것도 버렸습니다."])
    b.REPAIR_STATS.update(tried=0, fixed=0)
    out = b.with_placeholders(inner, repair=(first, second))(["Call the PutObject API of Amazon S3."], {})
    assert out == ["PutObject API를 호출합니다."]              # ⟦T1⟧ 만 돌아오고 ⟦T2⟧ 는 없는 그대로
    assert a["n"] == 1 and c["n"] == 1                       # 판마다 한 번씩만 묻는다
    assert b.REPAIR_STATS == {"tried": 1, "fixed": 0}        # 걸렸으나 못 고쳤다 — 결과가 그렇게 말한다


def test_고치는_판은_복호화만_다르다():
    """모델도 체계 지시도 같아야 무엇이 효과인지 가른다. 조건은 머리줄에 실린다(DECISIONS §57)."""
    from seshat import backends as b
    arm = "gemma3-4b+ph+retry+endings+terms"
    assert arm in b.REGISTRY and arm in b.REPAIR_ARMS
    assert b.OLLAMA_OF[arm] == b.OLLAMA_OF["gemma3-4b+ph+endings+terms"]
    assert b.DECODING_OF[arm]["repair"] == b.REPAIR
    assert b.REPAIR["temperature"] > 0 and b.REPAIR["seed"] != b.DECODING["seed"]
    assert len(b._gemma3_repair) == 2                        # 원문 · 온도 0 → 원문 · 온도 0.4


def test_범용_팔은_문체를_강제하지_않는다():
    """정답 문장이 있는 셋에서 합쇼체를 강제하면 맞는 문장이 정답에서 멀어진다(DECISIONS §63)."""
    from seshat import backends as b
    for arm in ("gemma3-4b", "gemma3-4b+ph+retry"):
        assert arm in b.REGISTRY and arm in b.OLLAMA_OF
        assert "endings" not in arm and "terms" not in arm
        assert b.WEIGHTS[arm] == "google/gemma-3-4b-it"
    assert "gemma3-4b+ph+retry" in b.REPAIR_ARMS          # 이름은 그대로 지킨다


def test_boto3_가_없으면_그룹을_말한다(monkeypatch):
    """`uv run --group data` 로 한 번 돌면 환경에서 boto3 가 빠진다(DECISIONS §74)."""
    import builtins

    import pytest

    from seshat import backends as b
    monkeypatch.setenv("AWS_REGION", "ap-northeast-2")
    real = builtins.__import__

    def 없는척(name, *a, **k):
        if name == "boto3":
            raise ModuleNotFoundError("No module named 'boto3'")
        return real(name, *a, **k)
    monkeypatch.setattr(builtins, "__import__", 없는척)
    with pytest.raises(SystemExit) as e:
        b.aws_translate(["x"], {})
    assert "--group aws" in str(e.value)


def test_자격증명이_만료되면_들어가는_법을_말한다(monkeypatch):
    """botocore 는 40 줄을 뱉고 무엇을 쳐야 하는지 말하지 않는다 — 두 번째다(DECISIONS §75)."""
    import pytest

    from seshat import backends as b
    monkeypatch.setenv("AWS_REGION", "ap-northeast-2")
    monkeypatch.setenv("AWS_PROFILE", "fox")

    class LoginRefreshRequired(Exception):
        pass

    class 가짜:
        def translate_text(self, **_):
            raise LoginRefreshRequired("Your session has expired")

    with pytest.raises(SystemExit) as e:
        b.aws_translate(["x"], {}, client=가짜())
    말 = str(e.value)
    assert "aws login --profile fox" in 말


def test_다른_거절은_그대로_이름을_보인다(monkeypatch):
    import pytest

    from seshat import backends as b
    monkeypatch.setenv("AWS_REGION", "ap-northeast-2")

    class UnsupportedLanguagePairException(Exception):
        pass

    class 가짜:
        def translate_text(self, **_):
            raise UnsupportedLanguagePairException("en→kr 는 없다")

    with pytest.raises(SystemExit) as e:
        b.aws_translate(["x"], {}, client=가짜())
    assert "UnsupportedLanguagePairException" in str(e.value)


def test_한도는_환경이_정한다(monkeypatch):
    """카드에 안 올라가는 모델은 느리다 — 숫자를 코드에 박지 않는다(DECISIONS §82)."""
    from seshat import backends as b
    monkeypatch.delenv("OLLAMA_TIMEOUT", raising=False)
    assert b._timeout() == b.TIMEOUT
    monkeypatch.setenv("OLLAMA_TIMEOUT", "2400")
    assert b._timeout() == 2400
    monkeypatch.setenv("OLLAMA_TIMEOUT", "0")
    assert b._timeout() == b.TIMEOUT             # 0 은 한도 없음이 아니라 오타다
    monkeypatch.setenv("OLLAMA_TIMEOUT", "곧")
    assert b._timeout() == b.TIMEOUT


def test_늦으면_막힌_줄을_말한다(monkeypatch):
    """16 분 돌던 판이 한 줄에 걸려 죽었는데 어느 줄인지 안 알려 줬다(DECISIONS §82)."""
    import urllib.request

    import pytest

    from seshat import backends as b

    def 늦다(*a, **k):
        raise TimeoutError("timed out")
    monkeypatch.setattr(urllib.request, "urlopen", 늦다)
    monkeypatch.setenv("OLLAMA_TIMEOUT", "30")
    req = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=b"{}")
    with pytest.raises(SystemExit) as e:
        b._ask(req, "gemma3:12b", "The catalog is ingested by Kinesis.")
    말 = str(e.value)
    assert "30초" in 말 and "OLLAMA_TIMEOUT" in 말 and "The catalog" in 말
