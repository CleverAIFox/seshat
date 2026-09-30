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
            out = fn(texts, terms)
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
        pass
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
