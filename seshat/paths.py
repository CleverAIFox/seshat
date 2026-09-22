"""경로 정본 — 기계마다 다른 자리는 전부 여기서 읽는다(DECISIONS §21).

★ **값은 `.env` 에 있고 셸이 이긴다.** `.env` 는 기본값이고 `export` 는 그 판을 덮는 일회성 판단이다.
  뒤집으면 한 번만 다른 값으로 돌리려던 지정이 조용히 무시된다(thoth DECISIONS §40 · 파이어레인 paths.py).
★ **심링크를 쓰지 않는다.** 파이어레인에서 `data/raw` 심링크를 git 이 추적했고, exFAT 에서 체크아웃이
  경로 문자열 파일을 만들며 원본 2.5GB 가 사라졌다. 환경변수는 git 에 아무것도 남기지 않는다.
★ 표준 라이브러리만 쓴다. 의존성 0 인 도구도 이 모듈을 탄다.

레이크(`SESHAT_DATA`) 의 층

  raw     원본. 한 번 넣으면 바꾸지 않는다 — thoth 쌍(원문) · 도메인 문서 스냅숏 · 수집한 용어집
  runs    실험 결과. **다시 만들 수 없다** — GPU 시간과 그날의 가중치 · 서버 상태가 들어 있다.
          가설 대장의 근거(`runs/…`)가 가리키는 곳이다
  cache   다시 받을 수 있는 것 — 공개 벤치마크 · 논문 PDF · 가중치. 백업하지 않는다
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TIERS = ("raw", "runs", "cache")


def load_dotenv(path: Path | None = None) -> None:
    """저장소 루트 `.env` 를 환경에 얹는다. 셸에 이미 있는 키는 안 덮는다. 빈 값은 미설정이다."""
    p = path or ROOT / ".env"
    if not p.exists():
        return
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, val = line.removeprefix("export ").partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if sep and key and val and key not in os.environ:
            os.environ[key] = val


def _dir(key: str) -> Path | None:
    v = os.environ.get(key, "").strip()
    return Path(v).expanduser() if v else None


def data() -> Path | None:
    """레이크 루트. 없으면 None — 부르는 쪽이 멈출지 건너뛸지 정한다."""
    return _dir("SESHAT_DATA")


def inbox() -> Path | None:
    """브라우저 다운로드 폴더. 패치가 여기로 온다."""
    return _dir("SESHAT_INBOX")


def require_lake() -> Path:
    """레이크가 **붙어 있어야** 하는 도구의 입구. 비었으면 종료코드 2.

    ★ WSL 은 드라이브가 안 붙어도 `/mnt/f` 를 빈 디렉터리로 둔다. 있다는 것은 붙었다는 뜻이 아니다 —
      레이크 표지(`MANIFEST.tsv`)가 있어야 붙은 것이다(파이어레인 MASTER §18-13).
    """
    d = data()
    if d is None:
        _stop("SESHAT_DATA 가 없다 — .env 에 SSD 위의 자리를 적는다(.env.example)")
    if not (d / "MANIFEST.tsv").exists():
        _stop(f"{d} 에 MANIFEST.tsv 가 없다 — 드라이브가 안 붙었거나 `tools/lake.py init` 전이다\n"
              "    sudo mkdir -p /mnt/f && sudo mount -t drvfs F: /mnt/f")
    return d


def _stop(msg: str) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(2)


load_dotenv()
