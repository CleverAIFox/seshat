"""seshat — thoth 에 끼울 영한 번역 모델.

★ **`.env` 를 여기서 얹는다**(DECISIONS §39). 도구마다 따로 읽으면 부르는 방법에 따라 설정이 있다 없다 한다 —
  2026-09-23 에 `AWS_REGION` 을 `.env` 에 적으라고 해놓고 `evaluate` 는 그 파일을 읽지 않았다.
  셸이 이긴다(`seshat/paths.py`). 표준 라이브러리만 쓰므로 의존성 0 인 경로에도 걸리지 않는다.
"""
from . import paths as _paths  # noqa: F401  — 불러 오는 것이 곧 `.env` 를 얹는 일이다

__version__ = "0.0.2"
