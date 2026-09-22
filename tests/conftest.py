import threading

import pytest

from seshat import backends, serve


@pytest.fixture
def server():
    """echo 백엔드 서버를 빈 포트에 띄운다. 토큰은 인자로 바꾼다."""
    started = []

    def start(backend: str = "echo", token: str = "") -> str:
        srv = serve.serve(backend, "127.0.0.1", 0, token)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        started.append(srv)
        return f"http://127.0.0.1:{srv.server_address[1]}"

    yield start
    for s in started:
        s.shutdown()


@pytest.fixture
def bad_backend(monkeypatch):
    """길이를 어기는 백엔드를 잠시 등록한다."""
    monkeypatch.setitem(backends.REGISTRY, "short", (lambda ts, terms: ts[:-1], "seshat-short"))
    return "short"
