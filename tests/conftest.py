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


@pytest.fixture
def 터지는_백엔드(monkeypatch):
    """**부르면 예외를 던지는** 백엔드를 잠시 등록한다(DECISIONS §306).

    ★ 메시지에 비밀처럼 보이는 글자를 일부러 넣는다 — 응답 몸통에 **안 새는지**까지
      같은 자리에서 재려는 것이다. 터지는 것만 재면 그 절반만 본다.
    """
    def 터진다(texts, terms):
        raise RuntimeError("모델을 못 열었다 — token=비밀값123 /home/fox/.ollama")

    monkeypatch.setitem(backends.REGISTRY, "boom", (터진다, "seshat-boom"))
    return "boom"


@pytest.fixture
def 죽는_백엔드(monkeypatch):
    """**부르면 `SystemExit` 을 던지는** 백엔드를 잠시 등록한다(DECISIONS §312).

    ★ **이것이 흔한 쪽이다.** `backends.py` 의 실패 열셋이 전부 `SystemExit` 이다 —
      ollama 가 꺼졌거나, 거절했거나, 연결이 끊겼거나, 늦었거나, AWS 가 거절한 자리.
      `터지는_백엔드` 의 `RuntimeError` 는 **드문 쪽**이고, 그것만 재면 **흔한 쪽이
      안 재진다.** 2026-10-20 감사가 그 구멍을 재현했다.
    ★ 여기도 비밀처럼 보이는 글자를 넣는다 — 안 새는지 같은 자리에서 본다.
    """
    def 죽는다(texts, terms):
        raise SystemExit("ollama 에 닿지 못한다 — token=비밀값456 /home/fox/.ollama")

    monkeypatch.setitem(backends.REGISTRY, "dead", (죽는다, "seshat-dead"))
    return "dead"
