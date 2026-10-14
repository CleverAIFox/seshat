"""서버가 thoth `ENGINE=http` 계약을 지키는가. **thoth 의 검사 도구로 잰다.**"""
import json
import urllib.error
import urllib.request

import pytest

from tests import thoth_conformance as conf


def _post(url, body, token=""):
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url + "/translate", data=json.dumps(body).encode(), headers=h)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_thoth_적합성_검사를_통과한다(server):
    res = conf.run(server(), model="seshat-echo")
    assert all(ok for _, ok, _ in res), res


def test_토큰이_있으면_토큰_없는_요청을_거절한다(server):
    res = dict((n, ok) for n, ok, _ in conf.run(server(token="t"), token="t"))
    assert res["auth"] and res["single"] and res["health"]


@pytest.mark.parametrize("body,err", [
    ({"texts": "하나"}, "texts_not_strings"),
    ({"texts": [1, 2]}, "texts_not_strings"),
    ({"texts": ["a"] * 51}, "too_many_texts"),
    ({"texts": ["a"], "terms": []}, "terms_not_object"),
])
def test_모양이_틀리면_400(server, body, err):
    st, out = _post(server(), body)
    assert st == 400 and out["error"] == err


def test_백엔드가_길이를_어기면_500_으로_먼저_죽는다(server, bad_backend):
    # ★ 워커가 502 를 내기 전에 원인이 이쪽 로그에 남는다.
    st, out = _post(server(bad_backend), {"texts": ["a", "b"]})
    assert st == 500 and out["error"] == "backend_length_mismatch"


def test_백엔드가_터지면_연결을_끊지_않고_502_를_낸다(server, 터지는_백엔드):
    # ★ **고치기 전에는 응답 자체가 없었다**(DECISIONS §306). `socketserver` 가 그
    #   요청만 조용히 버리고 연결을 끊어서, 부른 쪽은 `RemoteDisconnected` 를 받았다 —
    #   「서버가 틀렸다」 가 아니라 **「연결이 끊겼다」** 다. 둘은 재시도 판단이 다르다.
    st, out = _post(server(터지는_백엔드), {"texts": ["a"]})
    assert st == 502
    assert out["error"] == "backend_failed"


def test_502_가_갈래만_싣고_메시지를_안_싣는다(server, 터지는_백엔드):
    # ★ **예외 메시지에는 경로 · 모델 인자 · 드물게 자격증명이 들어온다.** 부른 쪽에
    #   필요한 것은 갈래이고, 자세한 것은 역추적으로 이쪽 로그에만 남긴다.
    st, out = _post(server(터지는_백엔드), {"texts": ["a"]})
    assert st == 502 and out["kind"] == "RuntimeError"
    글 = json.dumps(out, ensure_ascii=False)
    assert "비밀값123" not in 글 and ".ollama" not in 글, 글


def test_터진_뒤에도_서버가_산다(server, 터지는_백엔드):
    # ★ **한 요청이 죽는 것과 서버가 죽는 것은 다른 말이다.** 터진 뒤 건강 검진이
    #   돌아야 「요청만 실패했다」 가 참이다.
    url = server(터지는_백엔드)
    assert _post(url, {"texts": ["a"]})[0] == 502
    with urllib.request.urlopen(url + "/health", timeout=5) as r:
        assert r.status == 200 and json.loads(r.read())["status"] == "ok"


def test_길이_위반과_터짐을_다른_코드로_가른다(server, bad_backend, 터지는_백엔드):
    # ★ **500 은 「백엔드가 계약을 어겼다」, 502 는 「백엔드가 못 했다」.** 같은 코드로
    #   내면 로그에서 **「고칠 코드가 있다」 와 「켜면 된다」 가 섞인다.**
    짧 = _post(server(bad_backend), {"texts": ["a", "b"]})
    터 = _post(server(터지는_백엔드), {"texts": ["a"]})
    assert 짧[0] == 500 and 짧[1]["error"] == "backend_length_mismatch"
    assert 터[0] == 502 and 터[1]["error"] == "backend_failed"
