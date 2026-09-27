"""데이터 카탈로그 — `data/catalog.toml` 을 읽고 검사하고 묻는다(DECISIONS §22).

★ 표준 라이브러리만 쓴다(tomllib). 레이크 도구가 이 모듈을 탄다.
"""
from __future__ import annotations

import fnmatch
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATH = ROOT / "data/catalog.toml"
USES = {"eval", "evidence", "train", "ontology", "reference", "serve"}
FIELDS = ("id", "where", "origin", "license", "uses", "how")
UNKNOWN = "미확인"
LEDGER = "seshat/licenses.py"


def load(path: Path = PATH) -> list[dict]:
    return tomllib.loads(path.read_text(encoding="utf-8"))["source"]


def validate(entries: list[dict], root: Path = ROOT) -> list[str]:
    fails, seen = [], set()
    for e in entries:
        name = e.get("id", "?")
        for f in FIELDS:
            if not e.get(f):
                fails.append(f"{name}: `{f}` 가 비었다")
        if name in seen:
            fails.append(f"{name}: id 가 겹친다")
        seen.add(name)
        where = e.get("where", "")
        if not where.startswith(("repo:", "lake:")):
            fails.append(f"{name}: where 는 repo: · lake: 로 시작한다 — {where}")
        bad = set(e.get("uses", [])) - USES
        if bad:
            fails.append(f"{name}: 모르는 쓰임 {sorted(bad)}")
        if "train" in e.get("uses", []) and UNKNOWN in e.get("license", ""):
            fails.append(f"{name}: 라이선스가 미확인인데 train 을 달았다")
        how = e.get("how", "")
        if how and how != "사람" and not (root / how).exists():
            fails.append(f"{name}: 얻는 도구 {how} 가 없다")
    return fails


def match(entries: list[dict], space: str, rel: str) -> dict | None:
    """`space` 는 repo · lake. 첫 번째로 맞는 출처."""
    for e in entries:
        kind, _, pat = e["where"].partition(":")
        if kind == space and fnmatch.fnmatch(rel, pat):
            return e
    return None


def allowed(source_id: str, use: str, entries: list[dict] | None = None) -> bool:
    """학습 · 서빙 로더가 묻는 문. 없는 id 는 거짓이다."""
    for e in entries if entries is not None else load():
        if e["id"] == source_id:
            return use in e["uses"]
    return False


def weights_outside(entries: list[dict], root: Path = ROOT) -> list[str]:
    """가중치가 카탈로그가 적은 자리 밖에 있는가(DECISIONS §106).

    ★ **카탈로그는 파일을 못 본다.** `where` 는 약속이고, ollama 는 그 약속을 모른 채 자기 자리에
      받는다. 2026-09-27 에 카탈로그가 `lake:cache/models/*` 라고 적은 동안 21GB 가 `~/.ollama/models`
      에 있었다. **제일 큰 데이터가 정본 밖에 있었다.**
    ★ 자리를 정하는 것은 `OLLAMA_MODELS` 다. 비어 있으면 ollama 는 `~/.ollama/models` 를 쓴다.
    ★ **레이크가 없는 기계(CI)에서는 묻지 않는다.** 거기엔 ollama 도 없다.
    """
    import os
    lake = os.environ.get("SESHAT_DATA", "").strip()
    if not lake:
        return []
    want = next((e for e in entries if e["id"] == "weights"), None)
    if not want:
        return []
    here = Path(os.environ.get("OLLAMA_MODELS", "").strip() or "~/.ollama/models").expanduser()
    if not here.exists():
        return []
    if str(here).startswith(str(Path(lake).expanduser())):
        return []
    n = sum(1 for _ in here.rglob("*") if _.is_file())
    if not n:
        return []
    return [f"weights: 카탈로그는 {want['where']} 라는데 가중치 {n}개가 {here} 에 있다 — "
            f".env 에 OLLAMA_MODELS 를 적거나 카탈로그를 고친다(DECISIONS §106)"]


def unlisted_repo_files(entries: list[dict], root: Path = ROOT) -> list[str]:
    """`data/` 아래의 파일 중 카탈로그 밖. README 는 데이터가 아니다."""
    out = []
    for p in sorted((root / "data").rglob("*")):
        if p.is_file() and p.name != "README.md" and p.name != "catalog.toml":
            rel = p.relative_to(root).as_posix()
            if match(entries, "repo", rel) is None:
                out.append(rel)
    return out
