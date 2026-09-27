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
FIELDS = ("id", "where", "origin", "license", "uses", "how", "feeds")
# ★ 아무도 안 읽는 출처는 **언제 쓸지**를 적고 산다(DECISIONS §120 · 파이어레인 §18-1a R4)
UNFED = "미투입 — "
UNKNOWN = "미확인"
LEDGER = "seshat/licenses.py"


def _toml(path: Path = PATH) -> dict:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def load(path: Path = PATH) -> list[dict]:
    return _toml(path)["source"]


def layers(path: Path = PATH) -> dict[str, dict]:
    """층 정책. **여기가 정본이다**(DECISIONS §114). `paths.TIERS` · `lake.MANAGED` · `.gitignore` 가 따라온다."""
    return _toml(path)["layers"]


def managed_tiers(path: Path = PATH) -> tuple[str, ...]:
    """해시 대장이 지키는 레이크 층. `lake.py` 가 손으로 적지 않고 여기서 끌어온다."""
    return tuple(d for L in layers(path).values() if L["base"] == "lake" and L["managed"] for d in L["dirs"])


def lake_tiers(path: Path = PATH) -> tuple[str, ...]:
    return tuple(d for L in layers(path).values() if L["base"] == "lake" for d in L["dirs"])


LAYER_FIELDS = ("base", "dirs", "committed", "regenerable", "managed", "what")


def check_layers(root: Path = ROOT, path: Path = PATH) -> list[str]:
    """선언 ↔ 실물. **`.gitignore` 의 근거가 `regenerable` 이라는 말을 강제한다**(DECISIONS §114).

    ★ 다시 못 만드는 자리(`작업대` · `raw` · `runs`)도 커밋하지 않는다 — 그것은 **레이크가 지킨다.**
      그래서 `committed` 와 `regenerable` 은 다른 축이고, ignore 여부는 `committed` 가 정한다.
      `regenerable` 은 **ignore 해도 잃을 것이 없는가**를 답한다 — 아니면 레이크가 받아야 한다.
    """
    from . import paths
    fails, L = [], layers(path)
    for name, d in L.items():
        for f in LAYER_FIELDS:
            if f not in d:
                fails.append(f"층 {name}: `{f}` 가 없다")
        if d.get("base") not in ("repo", "lake"):
            fails.append(f"층 {name}: base 는 repo · lake 다 — {d.get('base')}")
        # 다시 못 만드는데 레이크도 안 지키면 그 파일은 사라질 수 있다
        if d.get("base") == "repo" and not d.get("committed") and not d.get("regenerable"):
            if name != "작업대":
                fails.append(f"층 {name}: 커밋도 안 하고 다시 만들지도 못한다 — 잃을 자리다")
    ignored = {ln.strip().rstrip("/") for ln in (root / ".gitignore").read_text(encoding="utf-8").splitlines()
               if ln.strip() and not ln.lstrip().startswith("#")}
    for name, d in L.items():
        if d.get("base") != "repo":
            continue
        for sub in d.get("dirs", []):
            got = sub in ignored
            if d.get("committed") and got:
                fails.append(f"층 {name}: committed 인데 .gitignore 가 {sub} 를 뺀다")
            if not d.get("committed") and not got:
                fails.append(f"층 {name}: committed 가 아닌데 .gitignore 에 {sub} 가 없다")
    if set(paths.TIERS) != set(lake_tiers(path)):
        fails.append(f"paths.TIERS {paths.TIERS} 가 선언 {lake_tiers(path)} 와 다르다")
    return fails


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
        fails += feeds_fail(name, e.get("feeds"), root)
    return fails


def feeds_fail(name: str, feeds, root: Path = ROOT) -> list[str]:
    """`feeds` 는 **누가 읽는가**다(DECISIONS §120).

    ★ 목록이면 읽는 것들의 이름이고, 그중 저장소 안의 파일을 가리키는 것은 **있어야 한다** —
      도구를 지우고 대장만 남으면 「누가 읽는다」 가 거짓이 된다.
    ★ 아무도 안 읽으면 `"미투입 — <언제 쓸지>"` 한 줄이다. **비워 두는 것과 다르다** — 비면 모르는
      것이고, `미투입` 은 알고 두는 것이다.
    """
    if not feeds:
        return [f"{name}: `feeds` 가 비었다 — 누가 읽는지 적거나 `{UNFED}<언제 쓸지>` 라고 적는다"]
    if isinstance(feeds, str):
        if not feeds.startswith(UNFED):
            return [f"{name}: `feeds` 가 글자 하나면 `{UNFED}` 로 시작한다 — {feeds[:30]}"]
        if len(feeds) <= len(UNFED) + 2:
            return [f"{name}: `미투입` 뒤에 **언제 쓸지**를 적는다"]
        return []
    out = []
    for f in feeds:
        head = f.split(" ")[0]
        if "/" in head and head.endswith(".py") and not (root / head).exists():
            out.append(f"{name}: feeds 가 없는 {head} 를 든다")
    return out


def unfed(entries: list[dict]) -> list[str]:
    """아무도 안 읽는 출처. **실패가 아니라 수다** — 세어서 보인다."""
    return [e["id"] for e in entries if isinstance(e.get("feeds"), str)]


def 자리(path: Path, root: Path = ROOT) -> tuple[str, str] | None:
    """경로를 (공간, 상대경로)로. 공간은 `repo` · `lake` 다. **밖이면 `None`** — 이 문의 일이 아니다.

    ★ 밖을 막지 않는다. `labels.py` 는 채점표를 `/tmp` 에 쓰고 그것이 맞다(DECISIONS §103). 문이 지키는
      것은 **선언된 공간 안에서 선언된 자리에만 쓰는가**이지 「어디에도 안 쓰는가」 가 아니다.
    """
    from . import paths
    path = Path(path).expanduser().resolve()
    for space, base in (("repo", root.resolve()), ("lake", (paths.data() or Path("/없다")).resolve())):
        if path == base or base in path.parents:
            return space, path.relative_to(base).as_posix()
    return None


def gate(path: Path, root: Path = ROOT, cat: Path = PATH) -> dict | None:
    """**데이터를 쓰기 전에 묻는 문**(DECISIONS §121 · 파이어레인 MASTER §18-11 의 세 판정).

      catalog.gate(OUT / f"{name}.jsonl")      # 자리가 선언돼 있나. 아니면 멈춘다

    ★ **선언 밖에는 안 쓴다.** 층(`[layers]`)이 그 자리를 알아야 하고, 데이터 자리면 출처(`[[source]]`)도
      있어야 한다. 둘 중 하나가 없으면 **반입 정지**다 — 파이어레인의 「대장에 없음 + 파일 있음 → 멈춘다」.
    ★ **작업대는 출처가 없어도 된다.** `runs/` · `labels/` 는 도구가 쓰고 사람이 `put` 으로 레이크에
      넣는 자리다 — 레이크에 들어갈 때 출처가 묻는다(DECISIONS §103).
    ★ 돌려주는 것은 맞은 출처이거나 `None`(작업대 · 두 공간 밖)이다. 멈추는 것으로 답을 대신하지 않는다.
    """
    자 = 자리(path, root)
    if 자 is None:                      # 저장소도 레이크도 아니면 이 문의 일이 아니다
        return None
    space, rel = 자
    L = layers(cat)
    안 = [(n, d) for n, d in L.items() if d["base"] == space
          and any(rel == sub or rel.startswith(sub + "/") for sub in d["dirs"])]
    if not 안:
        raise SystemExit(f"선언 밖에 쓰려고 한다 — {space}:{rel}\n"
                         f"    `data/catalog.toml` 의 [layers] 에 자리를 적는다(DECISIONS §114)")
    name, layer = 안[0]
    entries = load(cat)
    # 그 자리 자체이거나, **등록된 파일이 사는 디렉터리**이거나(DECISIONS §128)
    got = match(entries, space, rel) or holds(entries, space, rel)
    if got is None and (layer["managed"] or space == "lake" or rel.startswith("data/")):
        raise SystemExit(f"카탈로그 밖에 쓰려고 한다 — {space}:{rel} (층 {name})\n"
                         f"    `data/catalog.toml` 에 [[source]] 를 적는다. **파일을 옮기기 전에 대장부터** 쓴다")
    return got


def match(entries: list[dict], space: str, rel: str) -> dict | None:
    """`space` 는 repo · lake. 첫 번째로 맞는 출처."""
    for e in entries:
        kind, _, pat = e["where"].partition(":")
        if kind == space and fnmatch.fnmatch(rel, pat):
            return e
    return None


def holds(entries: list[dict], space: str, rel: str) -> dict | None:
    """`rel` **아래에** 등록된 자리가 있으면 그 출처(DECISIONS §128).

    ★ **등록된 파일이 사는 디렉터리는 등록된 자리다.** `lake:cache/awsdocs/*` 가 대장에 있으면
      `cache/awsdocs` 를 만드는 일도 허락된 일이다 — 그 디렉터리를 만들어야 그 파일이 생긴다.
      `match` 로는 안 걸린다(`fnmatch("cache/awsdocs", "cache/awsdocs/*")` 는 거짓이다).
    """
    앞 = rel.rstrip("/") + "/"
    for e in entries:
        kind, _, pat = e["where"].partition(":")
        if kind == space and pat.startswith(앞):
            return e
    return None


def allowed(source_id: str, use: str, entries: list[dict] | None = None) -> bool:
    """학습 · 서빙 로더가 묻는 문. 없는 id 는 거짓이다."""
    for e in entries if entries is not None else load():
        if e["id"] == source_id:
            return use in e["uses"]
    return False


def ollama_models_dir() -> tuple[str, str]:
    """ollama 가 **실제로** 쓰는 가중치 자리와, 그것을 어디서 알았는지(DECISIONS §138).

    ★ **셸의 값은 서버의 값이 아니다.** `os.environ` 은 이 파이썬을 띄운 셸이 보는 값이고,
      ollama 서버는 **다른 프로세스**다. systemd 로 뜨면 셸의 `export` 는 그 서버에 안 닿는다 —
      그때 이 검사는 「선언한 자리에 있다」 고 통과하면서 가중치는 딴 데 쌓인다. §111 이 그 모양이었고,
      고친 뒤에도 **묻는 상대가 틀린 채로** 남아 있었다.
    ★ **서버 프로세스에게 묻는다** — `/proc/<pid>/environ`. 못 물으면 셸 값을 쓰되 **그렇다고 적는다**.
      「못 물었다」 와 「서버가 그렇다고 했다」 를 같은 문장으로 내지 않는다(§110 과 같은 규율).
    """
    import os
    try:
        for d in Path("/proc").iterdir():
            if not d.name.isdigit():
                continue
            try:
                if (d / "comm").read_text().strip() != "ollama":
                    continue
                env = (d / "environ").read_bytes().decode("utf-8", "replace")
            except OSError:
                continue
            for kv in env.split("\0"):
                if kv.startswith("OLLAMA_MODELS="):
                    return kv.split("=", 1)[1].strip(), f"서버(pid {d.name})"
            return "", f"서버(pid {d.name}) — 안 정했다"
    except OSError:
        pass
    return os.environ.get("OLLAMA_MODELS", "").strip(), "셸 — 서버에 못 물었다"


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
    root = Path(lake).expanduser()
    said, 어디서 = ollama_models_dir()
    # ★ **선언한 자리에 있는지만 묻지 않는다**(DECISIONS §111). 2026-09-27 에 `.env` 에
    #   `OLLAMA_MODELS` 를 적고 파일을 옮겼는데 **ollama 는 `.env` 를 안 읽는다.** 기본 자리에서
    #   3.3GB 를 다시 받아 둘로 쪼개졌고, 이 검사는 선언한 자리만 보고 통과시켰다.
    #   **두 자리를 다 센다** — 기본 자리는 `OLLAMA_MODELS` 를 적었어도 비어 있어야 한다.
    seen = {Path("~/.ollama/models").expanduser()}
    if said:
        seen.add(Path(said).expanduser())
    out = []
    for here in sorted(seen):
        n = sum(1 for f in here.rglob("*") if f.is_file()) if here.exists() else 0
        if not n:
            continue
        if str(here).startswith(str(root)):
            continue
        why = ("셸이 OLLAMA_MODELS 를 모른다 — `.env` 는 파이썬만 읽는다. ~/.bashrc 에 export 한다"
               if said else ".env 에 OLLAMA_MODELS 를 적거나 카탈로그를 고친다")
        out.append(f"weights: 카탈로그는 {want['where']} 라는데 가중치 {n}개가 {here} 에 있다 — {why}"
                   f" (자리는 {어디서} 가 말한다 · DECISIONS §106 · §111 · §138)")
    return out


def unlisted_repo_files(entries: list[dict], root: Path = ROOT) -> list[str]:
    """`data/` 아래의 파일 중 카탈로그 밖. README 는 데이터가 아니다."""
    out = []
    for p in sorted((root / "data").rglob("*")):
        if p.is_file() and p.name != "README.md" and p.name != "catalog.toml":
            rel = p.relative_to(root).as_posix()
            if match(entries, "repo", rel) is None:
                out.append(rel)
    return out
