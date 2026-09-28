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
