"""FLORES+ 영→한을 평가셋 모양으로 받는다(DECISIONS §11).

  HF_TOKEN=<토큰> uv run --group data python tools/fetch_flores.py      # data/bench/ 에 쓴다

★ **범용 번역의 자다.** AWS Translate 를 이긴다는 말을 이 셋 위의 숫자로 한다(PLAN #12).
★ 라이선스 CC BY-SA 4.0 · 출처 openlanguagedata/flores_plus. 그래도 **커밋하지 않는다** —
  받는 도구를 커밋하고 데이터는 `data/bench/` 에 둔다(git 이 무시한다, DECISIONS §2).
★ 데이터셋 저장소는 동의를 요구한다(gated). Hugging Face 에서 **openlanguagedata/flores_plus 페이지의
  Agree 를 한 번 누르고** `HF_TOKEN` 을 준다 — 토큰만 있고 동의가 없으면 막힌다.
★ `HF_TOKEN` 은 `.env` 에 적는다. **그러려면 이 도구가 `.env` 를 얹어야 한다** — seshat 패키지를 불러
  오는 것이 곧 그 일이다(DECISIONS §39). 안 불러 오면 `.env` 에 적어 놓고 왜 안 되는지 헤맨다.
★ 파일 배치를 가정하지 않는다. 받은 parquet 을 훑어 `eng_Latn` · `kor_Hang` 을 split 별로
  짝짓는다. 짝은 `id` 로 맞춘다 — 순서로 맞추면 한 줄이 밀릴 때 전부 틀린다.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import seshat  # noqa: E402,F401  — 불러 오는 것이 곧 `.env` 를 얹는 일이다(DECISIONS §39)

OUT = ROOT / "data/bench"
# ★ 데이터셋이다. 가중치가 아니므로 라이선스 대장(seshat/licenses.py) 밖이다.
FLORES = "openlanguagedata/flores_plus"
SPLITS = ("dev", "devtest")


def pair(eng: list[dict], kor: list[dict], split: str) -> list[dict]:
    """영어 행과 한국어 행을 id 로 짝짓는다. 한쪽에만 있는 id 는 실패다."""
    e = {r["id"]: r["text"] for r in eng}
    k = {r["id"]: r["text"] for r in kor}
    if set(e) != set(k):
        raise SystemExit(f"{split}: id 가 어긋난다 — 영어만 {len(set(e) - set(k))} · 한국어만 {len(set(k) - set(e))}")
    return [{"id": f"flores-{split}-{i}", "src": e[i], "ref": k[i]} for i in sorted(e)]


def split_of(path: pathlib.Path) -> str | None:
    parts = [p.lower() for p in path.parts]
    return "devtest" if "devtest" in parts or "devtest" in path.name else ("dev" if "dev" in parts or path.name.startswith("dev") else None)


def main() -> int:
    from huggingface_hub import snapshot_download
    import pyarrow.parquet as pq
    local = pathlib.Path(snapshot_download(repo_id=FLORES, repo_type="dataset",
                                           allow_patterns=["*eng_Latn*", "*kor_Hang*"]))
    found: dict[tuple[str, str], list[dict]] = {}
    for f in local.rglob("*.parquet"):
        lang = "eng" if "eng_Latn" in f.name else ("kor" if "kor_Hang" in f.name else None)
        sp = split_of(f.relative_to(local))
        if lang and sp:
            found.setdefault((sp, lang), []).extend(pq.read_table(f, columns=["id", "text"]).to_pylist())
    OUT.mkdir(parents=True, exist_ok=True)
    for sp in SPLITS:
        if (sp, "eng") not in found or (sp, "kor") not in found:
            raise SystemExit(f"{sp}: eng_Latn · kor_Hang 을 둘 다 찾지 못했다 — 받은 파일 {sorted(found)}")
        rows = pair(found[(sp, "eng")], found[(sp, "kor")], sp)
        meta = {"meta": True, "about": f"FLORES+ {sp} 영→한", "license": "CC-BY-SA-4.0", "source": FLORES,
                "register": "정답은 평어체(-다)다 — 합쇼체 출력과는 style 을 따로 본다"}
        path = OUT / f"flores_plus.{sp}.jsonl"
        path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in [meta, *rows]) + "\n", encoding="utf-8")
        print(f"  {path.relative_to(ROOT)}  {len(rows)}줄")
    return 0


if __name__ == "__main__":
    sys.exit(main())
