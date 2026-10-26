"""thoth `ENGINE=http` 계약을 말하는 번역 서버(thoth MASTER §7-4).

  python -m seshat.serve                         echo 백엔드 · 127.0.0.1:8100
  python -m seshat.serve --backend echo --port 8100 --token T

  POST /translate  {"texts": [...], "source": "en", "target": "ko", "terms": {...}}
                → {"translations": [...], "model": "..."}
  GET  /health   → {"status": "ok", "model": "..."}

★ **표준 라이브러리로 선다.** 계약은 JSON 두 개라 프레임워크가 얹을 것이 없다.
  동시성이 모자라면 그때 ASGI 를 붙인다 — 모델 추론이 병목인 서버에서 HTTP 층은
  재기 전까지 문제가 아니다.

★ **길이를 여기서 한 번 더 본다.** 백엔드가 길이를 어기면 thoth 워커가 502 를 낸다.
  서버가 먼저 500 으로 죽으면 원인이 이쪽 로그에 남는다.
"""
from __future__ import annotations

import argparse
import hmac
import json
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import backends

MAX_TEXTS = 50          # thoth 워커가 한 요청에 싣는 최대치와 같다


def make_handler(fn: backends.Backend, model: str, token: str):
    class Handler(BaseHTTPRequestHandler):
        server_version = "seshat"

        def log_message(self, fmt, *args):
            sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

        def _send(self, status: int, body: dict) -> None:
            raw = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _authed(self) -> bool:
            if not token:
                return True
            got = self.headers.get("Authorization", "")
            return hmac.compare_digest(got, f"Bearer {token}")

        def do_GET(self):
            if self.path != "/health":
                return self._send(404, {"error": "not_found"})
            if not self._authed():
                return self._send(401, {"error": "unauthorized"})
            self._send(200, {"status": "ok", "model": model})

        def do_POST(self):
            if self.path != "/translate":
                return self._send(404, {"error": "not_found"})
            if not self._authed():
                return self._send(401, {"error": "unauthorized"})
            try:
                n = int(self.headers.get("Content-Length", "0"))
                req = json.loads(self.rfile.read(n))
            except ValueError:
                return self._send(400, {"error": "bad_json"})
            texts = req.get("texts") if isinstance(req, dict) else None
            if not isinstance(texts, list) or not all(isinstance(t, str) for t in texts):
                return self._send(400, {"error": "texts_not_strings"})
            if len(texts) > MAX_TEXTS:
                return self._send(400, {"error": "too_many_texts"})
            terms = req.get("terms", {})
            terms = {} if terms is None else terms     # `[]` 를 `or` 로 삼키지 않는다
            if not isinstance(terms, dict):
                return self._send(400, {"error": "terms_not_object"})
            # ★ **여기가 유일하게 터질 수 있는 줄이다 — 그리고 안 싸여 있었다**(§306).
            #   백엔드는 모델을 부른다. ollama 가 꺼져 있거나 가중치가 없거나 메모리가
            #   모자라면 여기서 예외가 난다. 안 싸면 `socketserver` 가 그 요청만 조용히
            #   버리고 **응답 없이 연결을 끊는다** — 재서 확인했다 :
            #       >> 응답 자체가 없다 : RemoteDisconnected
            #   thoth 워커는 그것을 「서버가 틀렸다」 가 아니라 **「연결이 끊겼다」** 로 받는다.
            #   까닭은 이쪽 stderr 에만 남고 부른 쪽은 아무것도 모른다.
            # ★ **502 다 — 500 이 아니다.** 위의 `backend_length_mismatch` 는 백엔드가
            #   **계약을 어긴** 것이고(이쪽 잘못), 이건 백엔드가 **못 한** 것이다.
            #   둘을 같은 코드로 내면 로그에서 「고칠 코드가 있다」 와 「켜면 된다」 가 섞인다.
            # ★ **몸통에는 예외 이름만 싣는다.** 메시지에는 경로 · 모델 인자 · 드물게는
            #   자격증명까지 들어온다. 부른 쪽에 필요한 것은 **갈래**이고, 자세한 것은
            #   역추적으로 이쪽 로그에 남긴다.
            # ★ **`SystemExit` 을 같이 잡는다**(DECISIONS §312). `backends.py` 의 실패
            #   열셋은 **전부 `SystemExit`** 이다 — ollama 가 꺼졌거나 · 거절했거나 ·
            #   연결이 끊겼거나 · 늦었거나 · AWS 가 거절한 자리. 그것은 `BaseException`
            #   이라 `except Exception` 을 **그냥 지나간다.** §306 이 고쳤다고 적은 뒤에도
            #   **흔한 실패는 그대로 연결을 끊고 있었다.**
            # ★ **`SystemExit` 을 버리지 않는다 — 번역한다.** 그 예외는 사람에게 고치는
            #   법을 알려 주려고 도구 쪽에서 쓰는 것이고(「ollama 를 켠다」), 도구에서는
            #   그대로 두는 것이 옳다. **서버는 죽으면 안 되는 경계**라 여기서만 응답으로
            #   바꾼다 — 고치는 글은 역추적과 함께 이쪽 로그에 남는다.
            # ★ **`BaseException` 으로 넓히지 않는다.** `KeyboardInterrupt` 까지 먹으면
            #   Ctrl-C 가 요청 하나로 삼켜진다. 넓히는 것과 맞게 넓히는 것은 다르다.
            try:
                out = fn(texts, terms)
            except (Exception, SystemExit) as e:         # 응답으로 바꾸는 것은 이 둘뿐 · Ctrl-C 는 통과
                traceback.print_exc(file=sys.stderr)
                self.log_message("백엔드가 터졌다 — %s", type(e).__name__)
                return self._send(502, {"error": "backend_failed",
                                        "kind": type(e).__name__})
            if len(out) != len(texts):
                return self._send(500, {"error": "backend_length_mismatch"})
            self._send(200, {"translations": out, "model": model})

    return Handler


def serve(backend: str = "echo", host: str = "127.0.0.1", port: int = 8100,
          token: str = "") -> ThreadingHTTPServer:
    fn, model = backends.get(backend)
    return ThreadingHTTPServer((host, port), make_handler(fn, model, token))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="echo")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8100)
    ap.add_argument("--token", default="")
    a = ap.parse_args(argv)
    srv = serve(a.backend, a.host, a.port, a.token)
    print(f"seshat {a.backend} → http://{a.host}:{a.port}", file=sys.stderr)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("  멈춘다", file=sys.stderr)
    return 0


if __name__ == "__main__":
    # ★ 위반(1)과 도구 고장(2)을 다른 코드로 끝낸다(DECISIONS §21 · §232). 같은 코드면
    #   **도구가 깨진 것을 검사가 실패한 것으로 읽는다**
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        print("    ✗ 도구가 깨졌다 — 위 역추적이 자리를 든다\n"
              "      고치고 다시 돌린다 : bash tools/verify.sh", file=sys.stderr)
        sys.exit(2)
