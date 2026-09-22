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
