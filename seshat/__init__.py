"""seshat — thoth 에 끼울 영한 번역 모델.

★ **`.env` 를 여기서 얹는다**(DECISIONS §39). 도구마다 따로 읽으면 부르는 방법에 따라 설정이 있다 없다 한다 —
  2026-09-23 에 `AWS_REGION` 을 `.env` 에 적으라고 해놓고 `evaluate` 는 그 파일을 읽지 않았다.
  셸이 이긴다(`seshat/paths.py`). 표준 라이브러리만 쓰므로 의존성 0 인 경로에도 걸리지 않는다.
"""
from . import paths as _paths  # noqa: F401  — 불러 오는 것이 곧 `.env` 를 얹는 일이다

# ★ **판 번호는 `pyproject.toml` 하나다**(DECISIONS §311). 여기 글자로 적어 뒀더니
#   `0.0.2` 와 `0.3.6` 이 **두 곳에서 따로 늙었다** — `/health` 와 기록 머리줄이 어느
#   쪽을 들지가 부르는 자리에 달렸다. 깔려 있으면 메타데이터가, 아니면 `pyproject` 를
#   직접 읽는다. **못 읽으면 터진다** — 조용히 `0.0.0` 을 내면 그 수가 기록에 박힌다.
def _판() -> str:
    from importlib.metadata import PackageNotFoundError, version
    try:
        return version("seshat")
    except PackageNotFoundError:
        import pathlib
        import re
        글 = (pathlib.Path(__file__).resolve().parent.parent / "pyproject.toml").read_text(encoding="utf-8")
        m = re.search(r'^version\s*=\s*"([^"]+)"', 글, re.M)
        if not m:
            raise RuntimeError("pyproject.toml 에서 version 을 못 읽었다") from None
        return m.group(1)


__version__ = _판()
