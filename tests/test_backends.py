"""백엔드가 막을 때 **넘는 길을 같이 주는가**(DECISIONS §196)."""
from __future__ import annotations

import pytest

from seshat import backends


def test_ollama_404_는_당기는_길을_알려준다(monkeypatch):
    """★ **막으면서 넘는 길을 같이 준다**(DECISIONS §196). ollama 의 404 는 거의 항상
    「그 모델이 이 기계에 없다」 이고 넘는 길은 `ollama pull` 하나다 — 글에 없으면 찾으러 간다.

    ★ 오늘 네 번째로 같은 모양이다(§174 가설 문 · §175 레이크 · §188 떼어두기 · 이것).
    """
    import urllib.error
    import urllib.request

    def 던진다(*a, **k):
        raise urllib.error.HTTPError("http://x/api/chat", 404, "Not Found", {}, None)

    monkeypatch.setattr(urllib.request, "urlopen", 던진다)
    req = urllib.request.Request("http://x/api/chat", data=b"{}",
                                 headers={"Content-Type": "application/json"})
    with pytest.raises(SystemExit) as e:
        backends._ask(req, "gemma3:12b", "어떤 줄")
    말 = str(e.value)
    assert "ollama pull gemma3:12b" in 말 and "ollama list" in 말


# ---------- 이 기계에 안 들어가는 모델(DECISIONS §201) ----------

def _태그(monkeypatch, gb: float):
    import json
    import urllib.request

    class _R:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self):
            return json.dumps({"models": [{"name": "큰놈:12b", "size": int(gb * 1024 ** 3)}]}).encode()

    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _R())


def _씻는다(monkeypatch):
    from seshat import backends as b
    b._들어가나_셈.clear()
    monkeypatch.delenv("SESHAT_LOCAL_OK", raising=False)
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    monkeypatch.setenv("SESHAT_VRAM_GB", "6")
    return b


def test_카드보다_큰_모델은_부르기_전에_막는다(monkeypatch):
    """★ 아는 것을 막는 것으로 바꾼다 — §82 · §84 가 이미 알았는데 아무도 안 막았다."""
    b = _씻는다(monkeypatch)
    _태그(monkeypatch, 7.6)
    with pytest.raises(SystemExit) as e:
        assert b.들어가나("큰놈:12b") is None    # **안 막는다** — 막으면 SystemExit 다
    말 = str(e.value)
    assert "안 들어간다" in 말 and "7.6GB" in 말 and "6.0GB" in 말
    assert "OLLAMA_URL" in 말 and "SESHAT_LOCAL_OK" in 말, "막기만 하고 넘는 길이 없다"


def test_카드에_들어가면_조용하다(monkeypatch):
    b = _씻는다(monkeypatch)
    _태그(monkeypatch, 3.3)
    assert b.들어가나("큰놈:12b") is None    # **안 막는다** — 막으면 SystemExit 다


def test_빌린_장비면_이_기계의_카드를_안_본다(monkeypatch):
    """★ 터널 너머의 T4 를 이 기계의 6GB 로 재면 §84 의 길 자체가 막힌다."""
    b = _씻는다(monkeypatch)
    monkeypatch.setenv("OLLAMA_URL", "https://x.trycloudflare.com")
    _태그(monkeypatch, 7.6)
    assert b.들어가나("큰놈:12b") is None    # **안 막는다** — 막으면 SystemExit 다


def test_알면서_돌리려면_길이_있다(monkeypatch):
    b = _씻는다(monkeypatch)
    monkeypatch.setenv("SESHAT_LOCAL_OK", "1")
    _태그(monkeypatch, 7.6)
    assert b.들어가나("큰놈:12b") is None    # **안 막는다** — 막으면 SystemExit 다


def test_못_물으면_안_막는다(monkeypatch):
    """모르는 것으로 막으면 ollama 가 잠깐 늦은 날 판이 통째로 죽는다."""
    import urllib.request
    b = _씻는다(monkeypatch)

    def 터진다(*a, **k):
        raise OSError("연결 거부")
    monkeypatch.setattr(urllib.request, "urlopen", 터진다)
    assert b.들어가나("큰놈:12b") is None    # **안 막는다** — 막으면 SystemExit 다


# ---------- 이름을 박아 다시 묻는다(H-080 · DECISIONS §218) ----------

def test_이름을_박은_물음이_그_이름을_글로_든다(monkeypatch):
    """★ 온도만 흔드는 되묻기는 **사라진 절**을 안 돌려준다(§214). 무엇이 빠졌는지 말해 준다."""
    from seshat import backends as b
    본것 = {}

    def 가짜(model, system, extra=None, suffix=""):
        본것["system"] = system
        return lambda texts, terms_, marks=None: ["돌아온 말 Amazon SNS"]
    monkeypatch.setattr(b, "ollama_chat", 가짜)
    out = b.이름을_박아_묻는다("gemma3:4b")("원문", ["Amazon SNS", "AWS"])
    assert "Amazon SNS" in 본것["system"] and "AWS" in 본것["system"]
    assert "clause" in 본것["system"], "절을 빠뜨리지 말라는 말이 없다"
    assert out == "돌아온 말 Amazon SNS"


def test_되묻기가_다_실패하면_이름을_박아_한_번_더_묻는다(monkeypatch):
    """★ **`+retry2` 는 `+retry` 와 물음 하나만 다르다** — 무엇이 효과인지 가르려면 그래야 한다."""
    from seshat import backends as b
    # ★ **모듈 상태를 되돌려 놓는다.** 안 그러면 뒤에 도는 시험이 내가 남긴 셈을 본다 —
    #   2026-09-29 `test_baselines` 둘이 그렇게 빨개졌다(따로 돌리면 초록이라 더 늦게 잡힌다)
    옛 = dict(b.REPAIR_STATS)
    monkeypatch.setattr(b, "REPAIR_STATS", {"tried": 0, "fixed": 0})
    assert 옛 is not b.REPAIR_STATS

    안 = lambda texts, terms_, marks=None: ["이름이 사라진 말"]          # noqa: E731
    막 = lambda texts, terms_, marks=None: ["또 사라진 말"]              # noqa: E731
    쟀다 = {}

    def 이름물음(text, names):
        쟀다["names"] = list(names)
        return "되찾은 말 Amazon SNS"
    호출 = b.with_placeholders(안, repair=(막,), 이름_물음=이름물음)
    out =호출(["Use Amazon SNS to send messages."], {}, [{}])
    assert 쟀다.get("names") == ["Amazon SNS"], 쟀다
    assert "Amazon SNS" in out[0]
    assert b.REPAIR_STATS["fixed"] == 1 and b.REPAIR_STATS.get("이름박기") == 1
