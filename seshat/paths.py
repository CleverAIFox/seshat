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

# 작업대 — 도구가 쓰고 사람이 `lake.py put` 으로 레이크에 넣는 자리(DECISIONS §103 · §136).
#   저장소 디렉터리 → (레이크에서의 자리, `lake.py put` 에 줄 인자)
# ★ **목록이 한 곳이다.** 종전에는 `tools/doctor.py` 가 둘을 알고 `tools/sweep.py` 가 하나만 알았다 —
#   그래서 doctor 는 「labels/ 에 안 간 것 0」 이라 하고 sweep 은 labels/ 를 아예 안 봤다. 작업대가
#   무엇인지 두 도구가 다르게 알면, 한쪽이 「치웠다」 고 한 자리가 다른 쪽에는 남아 있다.
# ★ 여기 적은 이름은 `data/catalog.toml` 의 `[layers."작업대"]` 와 같아야 한다 — 시험이 센다.
BENCH: dict[str, tuple[str, str]] = {"runs": ("runs", "runs"), "labels": ("raw/labels", "raw --into labels")}


def load_dotenv(path: Path | None = None) -> None:
    """저장소 루트 `.env` 를 환경에 얹는다. 셸에 이미 있는 키는 안 덮는다. 빈 값은 미설정이다.

    ★ **같은 열쇠가 두 번 있으면 나중 줄이 이기고, 그 사실을 말한다**(DECISIONS §73). 종전에는 앞줄이
      조용히 이겼다 — 셸 로더(`tools/lib/env.sh`)는 소싱이라 나중 줄이 이기므로 **같은 파일을 두 도구가
      반대로 읽었다.** 2026-09-25 폐기한 HF 토큰이 `.env` 첫 줄에 남아 있었고, 새 토큰을 `>>` 로 덧붙인
      뒤에도 파이썬 도구만 죽은 토큰을 집어 401 을 냈다.
    ★ 값이 틀린 것도 파일이 깨진 것도 아니다. **조용히 틀린 값이 쓰이는 것**이 가장 찾기 어렵다 — 말한다.
    """
    p = path or ROOT / ".env"
    if not p.exists():
        return
    seen: dict[str, str] = {}
    dup: list[str] = []
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, val = line.removeprefix("export ").partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if sep and key and val:
            if key in seen:
                dup.append(key)
            seen[key] = val                       # 나중 줄이 이긴다 — 셸 소싱과 같게
    for key in sorted(set(dup)):
        print(f"  ※ .env 에 {key} 가 여러 줄 있다 — 마지막 줄을 쓴다({p})", file=sys.stderr)
    for key, val in seen.items():
        if key not in os.environ:
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


def _이가(무엇: str) -> str:
    """★ **조사를 끝소리에 맞춘다**(H-013 · §158). 「점수 파일 **가** 없다」 로 적지 않는다 —
    이 저장소는 그 셈을 이미 갖고 있고, **제 메시지에 안 쓰는 것이 우스운 일**이다."""
    from . import terms
    return 무엇 + terms.particle(terms.ko_coda(무엇), "가")


def 읽는다(경로: str | Path, 무엇: str, 길: tuple[str, ...] = ()) -> str:
    """**사람이 준 경로를 읽는다** — 없으면 말을 하고 멈춘다(DECISIONS §270).

    ★ **맨몸을 싸는 것(§232)과 길을 내는 것(§210)은 다른 일이다.** `__main__` 의 catch-all 은
      뜻밖의 예외를 「고장 · 코드 2」 로 바꾼다 — 그것은 **바닥**이다. 사람이 **흔히 밟는 자리**
      (파일 이름을 틀렸다 · 앞 단계가 아직 안 끝났다)가 그 바닥으로 떨어지면 도구가
      **「제가 깨졌다」 고 거짓말하고 엉뚱한 길을 준다**(「`verify.sh` 로 고친다」 — 고칠 것이 없는데).
    ★ 2026-10-01 실제로 그랬다. `gemba` 가 **아직 도는 중**인데 `bootstrap --점수` 를 부르자
      역추적과 **「도구가 깨졌다」** 가 떴다. 밟아 보니 **경로를 받는 도구 14 중 7 이 같았다.**
    ★ `길` 은 **넘는 길**이다(§210) — 비우지 않는다.
    ★ **밖 — 내용이 옳은지는 안 본다.** 있는가 · 읽히는가만 본다. 빈 파일도 그대로 돌려준다.
    ★ **밖 — 쓰는 경로는 안 본다.** 낼 파일의 디렉터리가 없는 것은 다른 물음이다.
    """
    q = Path(경로)
    # ★ **글자로 박힌 길을 항상 싣는다**(DECISIONS §270). `길` 은 인자로 들어오므로
    #   `check_ways` 가 **정적으로 못 본다** — 그 검사의 지적이 옳다. 부르는 쪽이 길을 안 주면
    #   「없다」 한 줄만 남고, 그것은 **벽이지 길이 아니다**(§210)
    기본길 = "경로를 다시 본다 — 오타이거나 **앞 단계가 아직 안 끝났다**"
    if q.is_dir():
        raise SystemExit("\n".join([f"{_이가(무엇)} 파일이 아니라 디렉터리다 — {q}",
                                    f"    {기본길}", *(f"    {x}" for x in 길)]))
    if not q.exists():
        raise SystemExit("\n".join([f"{_이가(무엇)} 없다 — {q}",
                                    f"    {기본길}", *(f"    {x}" for x in 길)]))
    return q.read_text(encoding="utf-8")


def 줄들(경로: str | Path, 무엇: str, 길: tuple[str, ...] = ()) -> list[str]:
    """`읽는다` 의 줄 단위 — 빈 줄은 뺀다. jsonl 을 읽는 자리가 거의 전부 이 꼴이다."""
    return [x for x in 읽는다(경로, 무엇, 길).splitlines() if x.strip()]


load_dotenv()
