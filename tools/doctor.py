"""기계 상태를 센다 — 저장소가 아니라 **이 기계**를 본다(DECISIONS §110).

  uv run python tools/doctor.py            전부
  uv run python tools/doctor.py --selftest 프로브가 스스로 잴 수 있는지만

★ **`verify.sh` 는 저장소를 검사하고 이 도구는 기계를 검사한다.** 2026-09-27 에 걸린 둘이 전부 기계
  상태였다 — 가중치 21GB 가 카탈로그 밖에 있었고(§106), 그중 15GB 가 기각된 가설의 것이었다(§109).
  저장소는 그때 전부 초록이었다. **초록인 저장소가 기계가 맞다는 뜻이 아니다.**
★ **세는 것으로 끝난다.** 판정하지 않는다 — 「자리가 다르다」 는 짚고 「옮겨라」 는 사람이 정한다.
  파이어레인 `lakecheck.py` 의 규율을 옮겼다.
★ **프로브가 못 재면 0건이 아니라 빨간불이다.** 레이크가 안 붙었을 때 조용히 통과하면, 그 통과가
  「없다」 를 「괜찮다」 로 바꾼다. 파이어레인 `deadcheck` 의 ⑤가 git 없을 때 조용히 return 해서
  한동안 0건을 냈다 — 같은 실수를 안 한다.
★ **CI 에서는 안 돈다.** 레이크도 ollama 도 없다. `verify.sh` 가 부르지 않는 까닭이다.

프로브 다섯. 전부 센다.

  D1  레이크        붙었나 · 층 디렉터리가 선언대로 있나 · MANIFEST 가 실물과 맞나
  D2  가중치        설치된 것 ↔ 라이선스 대장 ↔ 자리(OLLAMA_MODELS)
  D3  작업대 잔재   runs/ · labels/ 에 레이크로 안 간 파일
  D4  .env          쓰는 도구가 있는 키가 비었나
  D5  디스크        레이크와 홈의 여유
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from seshat import backends, catalog, licenses, paths  # noqa: E402

HITS: list[tuple[str, str]] = []
NOTES: list[str] = []
# 작업대 — 도구가 쓰고 사람이 `lake.py put` 으로 레이크에 넣는 자리(DECISIONS §103)
BENCHES = {"runs": "runs", "labels": "raw --into labels"}
# 값이 없어도 되는 키. 쓰는 도구가 있을 때만 필요하다
OPTIONAL = {"AWS_PROFILE": "AWS Translate 기준선(H-025)", "HF_TOKEN": "FLORES+ 받기(tools/fetch_flores.py)",
            "AWS_REGION": "AWS Translate 기준선(H-025)"}


def hit(probe: str, what: str) -> None:
    HITS.append((probe, what))


def note(s: str) -> None:
    NOTES.append(s)


def d1_lake() -> None:
    """레이크가 붙었나. **못 재면 빨간불이다** — 안 붙은 것을 0건으로 세지 않는다."""
    d = paths.data()
    if d is None:
        hit("D1", ".env 에 SESHAT_DATA 가 없다 — 레이크를 못 잰다")
        return
    if not (d / "MANIFEST.tsv").exists():
        hit("D1", f"{d} 에 MANIFEST.tsv 가 없다 — 드라이브가 안 붙었거나 `lake.py init` 전이다")
        return
    missing = [t for t in paths.TIERS if not (d / t).is_dir()]
    if missing:
        hit("D1", f"층 디렉터리가 없다 — {', '.join(missing)}")
    rows = (d / "MANIFEST.tsv").read_text(encoding="utf-8").splitlines()[1:]
    note(f"D1  레이크 {d} · 층 {len(paths.TIERS)} · 대장 {sum(1 for r in rows if r.strip())}건")


def _ollama() -> list[dict] | None:
    """설치된 모델. ollama 가 없거나 안 돌면 None — **0개가 아니다.**"""
    if not shutil.which("ollama"):
        return None
    r = subprocess.run(["ollama", "list"], capture_output=True, text=True)
    if r.returncode:
        return None
    out = []
    for line in r.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 3:
            out.append({"name": parts[0], "size": " ".join(parts[2:4])})
    return out


def d2_weights() -> None:
    """설치된 가중치 ↔ 대장 ↔ 자리. **판정하지 않는다** — 세고 짚는다."""
    for f in catalog.weights_outside(catalog.load()):
        hit("D2", f)
    got = _ollama()
    if got is None:
        hit("D2", "ollama 를 못 부른다 — 설치된 가중치를 못 잰다(0개가 아니다)")
        return
    # ★ ollama 이름 → 가중치는 **배선이 든다**(`backends.WEIGHTS_OF_MODEL`). 여기서 이름을 짐작해
    #   맞추면 정본이 둘이 된다 — `gemma3:4b` 와 `google/gemma-3-4b-it` 는 글자로 안 이어진다.
    wired = backends.WEIGHTS_OF_MODEL
    unknown = [m["name"] for m in got if m["name"] not in wired]
    if unknown:
        hit("D2", f"배선이 안 부르는 가중치가 설치돼 있다 — {', '.join(unknown)}")
    nolic = [wired[m["name"]] for m in got if m["name"] in wired and wired[m["name"]] not in licenses.LEDGER]
    if nolic:
        hit("D2", f"라이선스 대장에 없는 가중치가 설치돼 있다 — {', '.join(nolic)}")
    note(f"D2  설치 {len(got)}개 · 배선 {len(wired)}개 · 라이선스 대장 {len(licenses.LEDGER)}개 "
         f"({' · '.join(m['name'] + ' ' + m['size'] for m in got) or '없다'})")


def d3_bench() -> None:
    """작업대에 남은 것. 레이크로 안 갔으면 **다시 못 만드는 것이 저장소 밖에서 혼자 산다**."""
    d = paths.data()
    known: set[str] = set()
    if d is not None and (d / "MANIFEST.tsv").exists():
        for line in (d / "MANIFEST.tsv").read_text(encoding="utf-8").splitlines()[1:]:
            if line.strip():
                known.add(Path(line.split("\t")[1]).name)
    for bench, how in sorted(BENCHES.items()):
        p = ROOT / bench
        if not p.is_dir():
            continue
        left = [f.name for f in sorted(p.glob("*.jsonl")) if f.name not in known]
        if left:
            hit("D3", f"{bench}/ 에 레이크로 안 간 파일 {len(left)}개 — "
                      f"python3 tools/lake.py put {how} {bench}/*.jsonl")
        note(f"D3  {bench}/ {len(list(p.glob('*.jsonl')))}개 · 안 간 것 {len(left)}")


def d4_env() -> None:
    """쓰는 도구가 있는데 비어 있는 키. **없어도 되는 것은 세지 않는다.**"""
    ex = ROOT / ".env.example"
    if not ex.exists():
        hit("D4", ".env.example 이 없다 — 무엇이 필요한지 못 잰다")
        return
    keys = [ln.split("=", 1)[0].strip() for ln in ex.read_text(encoding="utf-8").splitlines()
            if "=" in ln and not ln.lstrip().startswith("#")]
    empty = [k for k in keys if not os.environ.get(k, "").strip()]
    hard = [k for k in empty if k not in OPTIONAL]
    for k in hard:
        hit("D4", f".env 의 {k} 가 비었다")
    if soft := [k for k in empty if k in OPTIONAL]:
        note(f"D4  비었지만 괜찮다 — {' · '.join(f'{k}({OPTIONAL[k]})' for k in soft)}")
    note(f"D4  .env 키 {len(keys)} · 빈 것 {len(empty)}")


def d5_disk() -> None:
    for name, p in (("레이크", paths.data()), ("홈", Path.home())):
        if p is None or not Path(p).is_dir():
            continue
        u = shutil.disk_usage(p)
        free = u.free / 1e9
        if free < 10:
            hit("D5", f"{name}({p}) 여유 {free:.1f}GB — 10GB 아래다")
        note(f"D5  {name} {p} · 여유 {free:.0f}GB / {u.total / 1e9:.0f}GB")


PROBES = (d1_lake, d2_weights, d3_bench, d4_env, d5_disk)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true", help="프로브가 스스로 도는지만 본다")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    for probe in PROBES:
        try:
            probe()
        except Exception as e:                      # 프로브가 죽으면 그것이 결과다
            hit(probe.__name__.split("_")[0].upper(), f"프로브가 죽었다 — {type(e).__name__}: {e}")
    if a.json:
        print(json.dumps({"hits": HITS, "notes": NOTES}, ensure_ascii=False, indent=1))
    else:
        for n in NOTES:
            print(f"  {n}")
        if HITS:
            print()
            for p, w in HITS:
                print(f"  {p} {w}")
        print(f"\n  프로브 {len(PROBES)} · 짚은 것 {len(HITS)}")
    if a.selftest:
        return 0
    return 1 if HITS else 0


if __name__ == "__main__":
    sys.exit(main())
