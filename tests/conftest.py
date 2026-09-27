import hashlib
import pathlib
import threading

import pytest

from seshat import backends, serve

ROOT = pathlib.Path(__file__).resolve().parents[1]
# 시험이 건드리면 안 되는 저장소 정본. 사람이 손으로 고치고 diff 로 보는 것들이다
정본 = ("data/catalog.toml", "data/scoreboard.toml", "data/ontology/aws.jsonl", "data/eval/seed.jsonl")


def _찍기():
    return {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in 정본 if (ROOT / f).exists()}


@pytest.fixture(autouse=True)
def 정본을_안_건드린다():
    """**시험이 저장소 정본을 고치면 그 자리에서 빨갛게 한다**(DECISIONS §132).

    2026-09-27 `tools/gate.py` 의 시험이 `data/scoreboard.toml` 을 실제로 덮어썼다 — 기본 인자가
    import 때 묶여서 `monkeypatch` 가 안 먹었다. 그때는 `git diff` 를 보고서야 알았다.
    시험은 임시 자리에만 쓴다 — 정본을 고치는 시험은 **그 시험이 틀린 것**이다.
    """
    앞 = _찍기()
    yield
    뒤 = _찍기()
    바뀐 = [f for f in 앞 if 앞[f] != 뒤.get(f)]
    assert not 바뀐, f"시험이 저장소 정본을 고쳤다 — {' · '.join(바뀐)}. 임시 자리에만 쓴다"


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
