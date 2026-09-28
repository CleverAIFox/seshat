"""데이터 레이크 — SSD 위의 원본과 실험 결과를 대장으로 지킨다(DECISIONS §21 · MASTER §11).

  python3 tools/lake.py init                        레이크를 연다(층 디렉터리 · MANIFEST.tsv)
  python3 tools/lake.py put runs 파일...             실험 결과를 넣는다. 같은 이름이 있으면 해시를 본다
  python3 tools/lake.py put raw --into aws-docs 파일...  원본을 넣는다. 자리는 카탈로그가 정한다
  python3 tools/lake.py check                       대장과 디스크를 맞춘다 · 가설 대장의 근거가 레이크에 있는가
  python3 tools/lake.py ls H-050-nova*              레이크에서 찾는다 — **자리를 그대로 찍는다**(§175)

★ **넣기만 하고 바꾸지 않는다.** 같은 이름에 다른 내용이 오면 거절한다. 덮어쓰면 가설 대장이 가리키던
  근거가 조용히 다른 파일이 된다. 다시 쟀으면 이름(시각)이 다르다.
★ **대장에 없는 파일은 지우지 않는다.** `check` 가 이름을 대고 실패한다 — 넣은 사람이 `put` 으로 올린다
  (파이어레인 quarantine 과 같은 뜻 · 파괴를 자동으로 붙이지 않는다).
★ **카탈로그에 없는 자리에는 못 넣는다**(DECISIONS §22). `data/catalog.toml` 의 `lake:` 자리와 맞아야 한다.
  `check` 는 세 층 전부에서 카탈로그 밖 파일을 짚는다 — cache 도 무엇인지는 적혀 있어야 한다.
★ `cache` 층은 해시 대장 밖이다. 다시 받을 수 있는 것에 해시를 적으면 받을 때마다 대장이 운다.
★ 결과 파일의 원래 자리(`runs/` · `/tmp/h001` · 아티팩트 압축)는 작업대다. 거기가 사라져도 레이크가 남는다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from seshat import catalog, paths  # noqa: E402

# ★ **손으로 적지 않는다** — 층 선언이 정본이다(DECISIONS §114 · catalog.toml `[layers]`)
MANAGED = catalog.managed_tiers()
HEADER = "sha256\tpath\tbytes\tadded\torigin"
# 가설 대장이 근거로 드는 결과 파일
EVIDENCE = re.compile(r"\bruns/([\w.-]+\.jsonl)\b")


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def has(have: dict[str, str], 자리: str, p: Path) -> bool:
    """레이크에 **같은 자리에 같은 해시로** 있는가(DECISIONS §136).

    ★ **이름만 보면 안 된다.** 같은 이름으로 내용이 바뀐 파일을 「이미 넣었다」 로 읽으면, 치우는 쪽이
      레이크에 없는 것을 지운다. 판정 규칙은 여기 하나다 — `sweep` 과 `doctor` 가 같은 것을 쓴다.
    """
    return have.get(f"{자리}/{p.name}") == sha256(p)


def manifest(lake: Path) -> dict[str, str]:
    """경로 → 해시. 같은 경로가 두 번이면 마지막이 아니라 **실패**다 — 넣기만 하는 대장이다."""
    out: dict[str, str] = {}
    for n, line in enumerate((lake / "MANIFEST.tsv").read_text(encoding="utf-8").splitlines()[1:], 2):
        if not line.strip():
            continue
        h, rel, *_ = line.split("\t")
        if rel in out:
            raise SystemExit(f"MANIFEST.tsv:{n} {rel} 가 두 번 적혔다")
        out[rel] = h
    return out


def init(lake: Path) -> int:
    lake.mkdir(parents=True, exist_ok=True)
    for t in paths.TIERS:
        (lake / t).mkdir(exist_ok=True)
    m = lake / "MANIFEST.tsv"
    if not m.exists():
        m.write_text(HEADER + "\n", encoding="utf-8")
        print(f"  열었다 {lake}")
    else:
        print(f"  이미 열려 있다 {lake}")
    return 0


def put(lake: Path, tier: str, files: list[Path], now: str | None = None, into: str = "",
        entries: list[dict] | None = None) -> int:
    if tier not in MANAGED:
        raise SystemExit(f"{tier} 는 대장 밖이다 — raw · runs 만 넣는다")
    entries = catalog.load() if entries is None else entries
    have = manifest(lake)
    rows, bad = [], 0
    for src in files:
        if not src.is_file():
            print(f"  없음   {src}")
            bad += 1
            continue
        rel = "/".join(x for x in (tier, into.strip("/"), src.name) if x)
        if catalog.match(entries, "lake", rel) is None:
            print(f"  거절   {rel} — 카탈로그에 이 자리가 없다(data/catalog.toml)")
            bad += 1
            continue
        h = sha256(src)
        if rel in have:
            if have[rel] == h:
                print(f"  있다   {rel}")
            else:
                print(f"  거절   {rel} — 같은 이름에 다른 내용이다. 레이크는 바꾸지 않는다")
                bad += 1
            continue
        dst = lake / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            print(f"  거절   {rel} — 디스크에 있는데 대장에 없다. `check` 를 먼저 본다")
            bad += 1
            continue
        shutil.copy2(src, dst)
        if sha256(dst) != h:
            dst.unlink()
            print(f"  거절   {rel} — 복사본의 해시가 다르다")
            bad += 1
            continue
        stamp = now or dt.datetime.now().isoformat(timespec="seconds")
        rows.append(f"{h}\t{rel}\t{src.stat().st_size}\t{stamp}\t{src.resolve()}")
        have[rel] = h
        print(f"  넣었다 {rel}")
    if rows:
        with (lake / "MANIFEST.tsv").open("a", encoding="utf-8") as f:
            f.write("\n".join(rows) + "\n")
    return 1 if bad else 0


def check(lake: Path, ledger: Path | None = None, entries: list[dict] | None = None) -> list[str]:
    fails = []
    entries = catalog.load() if entries is None else entries
    have = manifest(lake)
    for rel, h in have.items():
        p = lake / rel
        if not p.exists():
            fails.append(f"없다     {rel} — 대장에는 있다")
        elif sha256(p) != h:
            fails.append(f"바뀌었다 {rel} — 넣은 뒤 내용이 달라졌다")
    for tier in MANAGED:
        for p in sorted((lake / tier).rglob("*")):
            rel = p.relative_to(lake).as_posix()
            if p.is_file() and rel not in have:
                fails.append(f"대장 밖  {rel} — `put {tier}` 로 올린다")
    for tier in paths.TIERS:
        for p in sorted((lake / tier).rglob("*")):
            rel = p.relative_to(lake).as_posix()
            if p.is_file() and catalog.match(entries, "lake", rel) is None:
                fails.append(f"카탈로그 밖 {rel} — data/catalog.toml 에 자리를 적거나 치운다")
    ledger = ledger or ROOT / "docs/hypotheses.md"
    if ledger.exists():
        for name in sorted(set(EVIDENCE.findall(ledger.read_text(encoding="utf-8")))):
            if f"runs/{name}" not in have:
                fails.append(f"근거 없음 runs/{name} — 가설 대장이 드는데 레이크에 없다")
    return fails


def 찾는다(lake: Path, 무늬: str, tier: str = "runs") -> list[Path]:
    """레이크에서 이름이 맞는 것. **자리를 그대로 준다**(DECISIONS §175).

    ★ 판은 `runs/` 에 잠깐 있다가 레이크로 간다. 그 뒤로는 `runs/H-050-*.jsonl` 이 **글로브가
      안 맞아 그대로 넘어가고**, 도구는 `FileNotFoundError` 를 뱉는다 — 파일이 **어디 있는지는
      아무도 안 알려준다.** 레이크에 넣는 길만 있고 **찾는 길이 없었다.**
    """
    무늬 = 무늬 if any(c in 무늬 for c in "*?[") else f"*{무늬}*"
    return sorted((lake / tier).glob(무늬))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    p = sub.add_parser("put")
    p.add_argument("tier", choices=MANAGED)
    p.add_argument("--into", default="", help="층 아래 자리 — 카탈로그의 lake: 자리와 맞아야 한다")
    p.add_argument("files", nargs="+", type=Path)
    sub.add_parser("check")
    q = sub.add_parser("ls")
    q.add_argument("무늬", nargs="?", default="*", help="이름 조각이나 글로브")
    q.add_argument("--tier", default="runs", choices=list(paths.TIERS))
    a = ap.parse_args(argv)
    if a.cmd == "init":
        d = paths.data()
        if d is None:
            print("SESHAT_DATA 가 없다 — .env 에 적는다(.env.example)", file=sys.stderr)
            return 2
        return init(d)
    lake = paths.require_lake()
    if a.cmd == "put":
        return put(lake, a.tier, a.files, into=a.into)
    if a.cmd == "ls":
        got = 찾는다(lake, a.무늬, a.tier)
        for x in got:
            print(f"  {x}")
        print(f"  {len(got)}건 — {lake / a.tier}")
        return 0 if got else 1
    fails = check(lake)
    for f in fails:
        print(f"  {f}")
    print(f"  레이크 {lake} · 대장 {len(manifest(lake))}건 · 실패 {len(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
