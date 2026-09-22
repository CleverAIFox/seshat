"""seshat 이 저장소 밖과 작업대에 남긴 흔적을 센다 — WSL 위생(DECISIONS §23).

  python3 tools/sweep.py          센다. 지우지 않는다
  python3 tools/sweep.py --fix    근거가 확실한 것만 지운다

★ **seshat 이 싼 것만 친다.** thoth `tools/sweep.py` 와 같은 원칙이다. uv 캐시 · ollama 모델 · WSL 디스크는
  기계 하나에 하나이고 thoth 가 본다(thoth sweep · doctor · OLLAMA_KEEP_ALSO). 두 저장소가 같은 자리를 치면
  한쪽이 남긴 것을 다른 쪽이 지운다.
★ **근거 없이 지우지 않는다.**
  INBOX 패치      커밋 제목이 전부 이력에 있으면 붙은 것이다(`tools/patch_subjects.py` — apply_patch 와 같은 규칙)
  작업대 결과     `runs/` · `/tmp/hNNN/` 의 결과 파일은 **레이크에 같은 해시로 있을 때만** 지운다. 없으면 `put` 이 먼저다
  러너 진단 로그  나열만 한다. 러너가 쓰는 중인지 이 도구가 판정하지 못한다
★ 닿지 못한 자리는 **0건이 아니라 못 잼**이다. 레이크가 안 붙었으면 작업대 결과는 판정하지 못한다.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import patch_subjects  # noqa: E402
from seshat import paths  # noqa: E402

TMP = Path(os.environ.get("TMPDIR", "/tmp"))
OLD_DAYS = 14


def lake_hashes() -> dict[str, str] | None:
    d = paths.data()
    if d is None or not (d / "MANIFEST.tsv").exists():
        return None
    sys.path.insert(0, str(ROOT / "tools"))
    import lake
    return lake.manifest(d)


def in_lake(p: Path, have: dict[str, str]) -> bool:
    import lake
    return have.get(f"runs/{p.name}") == lake.sha256(p)


def scan_inbox(repo: Path = ROOT):
    """(지울 것, 남길 것, 못 잼)"""
    d = paths.inbox()
    if d is None or not d.is_dir():
        return [], [], ["INBOX — SESHAT_INBOX 가 없거나 닿지 않는다"]
    kill, keep = [], []
    for p in sorted(d.glob("seshat-*.patch")):
        s = patch_subjects.state(p, repo)
        (kill if s == "붙음" else keep).append((p, s))
    return kill, keep, []


def scan_bench(have: dict[str, str] | None, dirs: list[Path]):
    if have is None:
        return [], [], ["작업대 결과 — 레이크가 안 붙었다(SESHAT_DATA · MANIFEST.tsv)"]
    kill, keep = [], []
    for d in dirs:
        files = sorted(d.rglob("*.jsonl")) if d.is_dir() else []
        for p in files:
            (kill if in_lake(p, have) else keep).append((p, "레이크에 있다" if in_lake(p, have) else "레이크 밖 — put 먼저"))
    return kill, keep, []


def tmp_bench_dirs() -> list[Path]:
    """`/tmp/h001` 처럼 아티팩트를 풀어 둔 자리. 이름이 근거다 — seshat 의 안내가 이 이름을 썼다."""
    return sorted(p for p in TMP.glob("h[0-9][0-9][0-9]") if p.is_dir())


def prune_empty(d: Path) -> list[Path]:
    """**정말 빈** 디렉터리만 아래에서부터 지운다. 결과 파일을 치운 뒤 남은 껍데기다.

    ★ 2026-09-22 첫판은 `.jsonl` 이 안 남았으면 `rmtree` 했다. 아티팩트에 다른 파일(로그 · 압축)이 있었다면
      근거 없이 같이 지웠다. 지우는 근거가 있는 것은 파일 하나하나고, 디렉터리는 비었다는 사실뿐이다.
    """
    gone = []
    for x in sorted((p for p in d.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True) + [d]:
        try:
            x.rmdir()
            gone.append(x)
        except OSError:
            pass
    return gone


def scan_tmp():
    return [(p, "seshat 임시") for p in sorted(TMP.glob("seshat-patch.*")) + sorted(TMP.glob("seshat-subjects-*"))]


def scan_runner():
    d = Path(os.environ.get("RUNNER_DIR", "~/actions-runner")).expanduser() / "_diag"
    if not d.is_dir():
        return []
    cut = time.time() - OLD_DAYS * 86400
    return [(p, f"{p.stat().st_size // 1024}KB") for p in sorted(d.glob("*.log")) if p.stat().st_mtime < cut]


def show(title: str, rows, fix: bool, removable: bool) -> int:
    print(f"== {title} — {len(rows)}건")
    n = 0
    for p, why in rows:
        mark = "지움" if (fix and removable) else ("지울 것" if removable else "남김")
        print(f"  {mark:<6} {p}  ({why})")
        if fix and removable:
            p.unlink(missing_ok=True)
            n += 1
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fix", action="store_true")
    a = ap.parse_args(argv)
    unmeasured = []
    k, keep, u = scan_inbox()
    unmeasured += u
    show("INBOX 의 붙은 패치", k, a.fix, True)
    show("INBOX 의 아직 안 붙은 패치", keep, a.fix, False)
    have = lake_hashes()
    k, keep, u = scan_bench(have, [ROOT / "runs", *tmp_bench_dirs()])
    unmeasured += u
    show("작업대 결과 — 레이크에 있다", k, a.fix, True)
    show("작업대 결과 — 레이크 밖", keep, a.fix, False)
    if a.fix:
        for d in tmp_bench_dirs():
            for x in prune_empty(d):
                print(f"  지움   {x}/ (빈 디렉터리)")
    show("임시 파일", scan_tmp(), a.fix, True)
    show(f"러너 진단 로그 — {OLD_DAYS}일 넘은 것", scan_runner(), a.fix, False)
    for u in unmeasured:
        print(f"  못 잼  {u}")
    if not a.fix:
        print("\n지우려면 : python3 tools/sweep.py --fix")
    return 0


if __name__ == "__main__":
    sys.exit(main())
