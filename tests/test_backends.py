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
        b.들어가나("큰놈:12b")
    말 = str(e.value)
    assert "안 들어간다" in 말 and "7.6GB" in 말 and "6.0GB" in 말
    assert "OLLAMA_URL" in 말 and "SESHAT_LOCAL_OK" in 말, "막기만 하고 넘는 길이 없다"


def test_카드에_들어가면_조용하다(monkeypatch):
    b = _씻는다(monkeypatch)
    _태그(monkeypatch, 3.3)
    b.들어가나("큰놈:12b")


def test_빌린_장비면_이_기계의_카드를_안_본다(monkeypatch):
    """★ 터널 너머의 T4 를 이 기계의 6GB 로 재면 §84 의 길 자체가 막힌다."""
    b = _씻는다(monkeypatch)
    monkeypatch.setenv("OLLAMA_URL", "https://x.trycloudflare.com")
    _태그(monkeypatch, 7.6)
    b.들어가나("큰놈:12b")


def test_알면서_돌리려면_길이_있다(monkeypatch):
    b = _씻는다(monkeypatch)
    monkeypatch.setenv("SESHAT_LOCAL_OK", "1")
    _태그(monkeypatch, 7.6)
    b.들어가나("큰놈:12b")


def test_못_물으면_안_막는다(monkeypatch):
    """모르는 것으로 막으면 ollama 가 잠깐 늦은 날 판이 통째로 죽는다."""
    import urllib.request
    b = _씻는다(monkeypatch)

    def 터진다(*a, **k):
        raise OSError("연결 거부")
    monkeypatch.setattr(urllib.request, "urlopen", 터진다)
    b.들어가나("큰놈:12b")
