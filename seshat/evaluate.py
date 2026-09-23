"""번역 서버를 평가셋으로 잰다. **thoth 계약을 말하는 서버면 무엇이든 잰다.**

  python -m seshat.evaluate --url http://127.0.0.1:8100 --set data/eval/seed.jsonl
  python -m seshat.evaluate --url https://<thoth 워커> --thoth --thoth-token T --set ...   # Nova Lite 기준선
  python -m seshat.evaluate --backend aws-translate --set data/bench/flores_plus.devtest.jsonl      # AWS Translate

★ **`--backend` 는 서버 없이 백엔드를 바로 부른다.** 기준선(AWS Translate)은 서빙하지 않으므로
  서버를 띄울 이유가 없다. 계약 검사는 `--url` 쪽이 맡는다.

★ **FLORES+ 의 정답은 평어체(`-다`)다.** 합쇼체를 강제한 출력(thoth 워커)은 어미마다 chrF 가
  깎인다. 범용 비교는 문체를 강제하지 않은 출력끼리 하고, 합쇼체는 `style` 로 따로 잰다(DECISIONS §11).

★ **thoth 워커도 같은 계약이다.** 워커의 `POST /translate` 는 `{"texts": [...]}` 를 받아
  `{"translations": [...]}` 를 돌려준다. 그래서 배포본(Nova Lite)이 곧 기준선이다 —
  기준선을 재려고 Bedrock 호출 코드를 이 저장소에 다시 쓰지 않는다(DECISIONS §3).
  워커 캐시가 먼저 답하므로 같은 원문은 과금이 한 번이다.

★ **지표는 싼 것부터 쌓는다.**

  style   마지막 문장이 합쇼체로 끝나는 비율. 정답 없이 잰다
  keep    `keep` 에 적은 영어 이름이 번역에 그대로 남은 비율. 정답 없이 잰다
  chrf    chrF++ (sacrebleu). `ref` 가 있는 줄만. 없으면 건너뛴다
  ms      문장당 지연

  josa    `keep` 이름 바로 뒤 조사가 그 이름의 끝소리와 맞는 비율(온톨로지 `coda`, H-001)
  term    원문에 나온 온톨로지 개념의 한국어(`ko` · `alt_ko`)가 번역에 있는 비율. 관계절의 머리 명사가
          사라지는지를 이것으로 본다(H-012)

  COMET 같은 신경망 지표는 torch 를 요구하므로 여기 넣지 않는다(PLAN #3).

★ **가설 없이 재지 않는다**(DECISIONS §12 · §14). echo 가 아닌 백엔드와 서버는 `--hypothesis H-NNN` 을
  요구하고, 그 가설은 대장에서 `실험` 상태여야 한다. 배선만 보는 실행은 `--smoke` 다.
★ **결과 파일 머리줄이 재현 조건을 든다** — 가설 · 커밋 · 평가셋 해시 · 백엔드 · 가중치 · 디코딩 ·
  원문 문자 수 · 비용(아는 경우). 조건을 적지 않은 측정은 재현되지 않는다(thoth DECISIONS §57 · §65).

★ 결과는 `runs/` 에 한 줄씩 남는다. 저장소에 들어가지 않는다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys
import time
import urllib.request

BATCH = 9

# 합쇼체 종결. 마지막 문장부호 앞을 본다.
_HAPSYO = re.compile(r"(습니다|ㅂ니다|[가-힣]니다|습니까|[가-힣]니까|십시오|시오)\s*[.?!]?\s*$")
_SENT_END = re.compile(r"[.?!]\s*$")


_LATIN = re.compile(r"[A-Za-z]")
_HANGUL_CH = re.compile(r"[가-힣]")


def ko_line(src: str, out: str) -> bool:
    """이 줄이 번역처럼 보이는가(DECISIONS §50). 두 가지를 함께 본다.

    ① 한글이 글자(한글 + 로마자) 중 20% 이상이다 — 이름을 영어로 남기는 이 저장소의 번역도 30% 대는 된다.
    ② 길이가 원문의 세 배를 넘지 않는다 — 사고문은 길다.

    ★ 처음에는 「한글이 두 자 이상인 줄」 로 셌다. 사고문이 한국어 낱말을 인용하자 그것도 1.0 이 됐다
      (2026-09-23 · Qwen3). **속은 지표를 고칠 때는 속인 예를 시험에 넣는다.**
    """
    ko, en = len(_HANGUL_CH.findall(out)), len(_LATIN.findall(out))
    share = ko / (ko + en) if ko + en else 1.0
    return share >= 0.2 and len(out) <= 3 * len(src) + 40


def hangul(rows: list[dict], outs: list[str]) -> float | None:
    """번역처럼 보이는 줄의 비율. 배선이 깨지면 다른 지표를 읽기 전에 여기서 보인다(DECISIONS §49 · §50)."""
    if not outs:
        return None
    return sum(ko_line(r["src"], o) for r, o in zip(rows, outs)) / len(outs)


def is_hapsyo(ko: str) -> bool:
    """마지막 줄의 끝이 합쇼체인가. 문장부호가 없는 명사구(보기 `S3 버킷`)는 **판정
    밖**이다 — None 이 아니라 True 로 센다. 어미가 없는 것을 틀렸다고 세면 짧은 보기가
    많은 평가셋에서 style 이 거짓으로 낮아진다."""
    last = ko.strip().splitlines()[-1] if ko.strip() else ""
    if not _SENT_END.search(last):
        return True
    return bool(_HAPSYO.search(last))


def load(path: str) -> list[dict]:
    rows = []
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("//"):
            r = json.loads(line)
            if not r.get("meta"):
                rows.append(r)
    return rows


_JOSA = re.compile(r"^(으로|이나|이라|을|를|이|가|은|는|과|와|나|라|로)(?![가-힣])")


def josa(rows: list[dict], outs: list[str]) -> float | None:
    """`keep` 이름 뒤에 붙은 조사가 끝소리와 맞는 비율. 조사가 붙지 않은 자리는 세지 않는다."""
    from . import ontology, terms
    codas = {x.text: x.coda for x in ontology.surfaces(ontology.load()) if x.coda}
    ok = total = 0
    for r, o in zip(rows, outs):
        for k in r.get("keep", []):
            if k not in codas:
                continue
            for m in re.finditer(re.escape(k), o):
                j = _JOSA.match(o[m.end():])
                if j:
                    total += 1
                    ok += terms.particle(codas[k], j.group(1)) == j.group(1)
    return ok / total if total else None


def term(rows: list[dict], outs: list[str]) -> dict[str, float | None]:
    """원문의 개념이 번역에 어떻게 나타났나 — 셋으로 가른다(DECISIONS §25).

      term      뜻이 남았다 — 공식 표기(`ko`) 또는 허용 표기(`alt_ko`)
      term_off  공식 표기 그대로다. thoth 의 도메인은 표기까지 맞아야 한다
      term_bad  관측된 오역(`bad_ko`)이 보이고 맞는 표기는 없다 — 뜻이 바뀐 자리다

    ★ **번역이 아닌 줄은 전부 놓침이다**(DECISIONS §52). 2026-09-23 Qwen3 4B 가 영어 사고 과정을 뱉었는데
      그 안에 한국어를 인용해서 `hangul` 0.0 · `term` 1.0 이 나왔다. 문자열이 어딘가 있다는 것과 그 자리에서
      뜻을 옮겼다는 것은 다르다. `ko_line` 을 통과하지 못한 줄의 개념은 분모에만 들어간다 — 빼면 대답을
      안 할수록 점수가 오른다.

    ★ 셋을 한 숫자로 묶으면 「모델이 버렸다」 와 「사전이 그 표기를 모른다」 가 섞인다. H-020 에서 40줄을 눈으로
      가른 결과 표기 차이가 25 · 버림 11 · 오역 4 였다 — 지표 하나로는 이 셋 중 무엇도 못 잰다.
    """
    from . import ontology
    onto = ontology.load()
    ok = off = bad = total = 0
    for r, o in zip(rows, outs):
        translated = ko_line(r["src"], o)
        for _, _, s in ontology.find(onto, r["src"]):
            if s.node["keep"]:
                continue
            total += 1
            if not translated:      # 번역이 아닌 줄에서는 어떤 표기도 맞은 것이 아니다(DECISIONS §52)
                continue
            hit_off = s.node["ko"] in o
            hit = hit_off or any(k in o for k in s.node.get("alt_ko", []))
            off += hit_off
            ok += hit
            bad += (not hit) and any(k in o for k in s.node.get("bad_ko", []))
    if not total:
        return {"term": None, "term_off": None, "term_bad": None}
    return {"term": ok / total, "term_off": off / total, "term_bad": bad / total}


def score(rows: list[dict], outs: list[str]) -> dict:
    n = len(rows)
    style = sum(is_hapsyo(o) for o in outs) / n if n else None
    kept = total = 0
    for r, o in zip(rows, outs):
        for k in r.get("keep", []):
            total += 1
            kept += k in o
    res = {"n": n, "style": style, "hangul": hangul(rows, outs), "keep": kept / total if total else None, "chrf": None,
           "josa": josa(rows, outs) if total else None, **term(rows, outs)}
    pairs = [(o, r["ref"]) for r, o in zip(rows, outs) if r.get("ref")]
    if pairs:
        try:
            import sacrebleu
        except ImportError:
            res["chrf"] = "sacrebleu 없음 — uv sync --group eval"
        else:
            hyp, ref = zip(*pairs)
            res["chrf"] = round(sacrebleu.corpus_chrf(list(hyp), [list(ref)], word_order=2).score, 2)
    return res


# ★ **평가 문장이 학습 쌍에 섞이면 안 된다.** thoth 워커는 캐시 미스를 쌍으로 남기되
#   `.local` 로 끝나는 사이트는 거른다(thoth DECISIONS §104). 워커를 잴 때는 이 출처를
#   싣는다 — 평가셋으로 학습하면 평가가 거짓말을 한다.
EVAL_SOURCE = {"site": "eval.seshat.local", "adapter": "eval"}


def request_body(texts: list[str], thoth: bool) -> dict:
    """thoth 워커와 모델 서버는 응답이 같고 요청이 조금 다르다. 워커의 `source` 는
    출처 객체이고 `terms` 는 워커가 스스로 고른다."""
    if thoth:
        return {"texts": texts, "target": "ko", "source": EVAL_SOURCE}
    return {"texts": texts, "source": "en", "target": "ko", "terms": {}}


def translate(url: str, texts: list[str], token: str = "", thoth: bool = False,
              thoth_token: str = "", timeout: float = 60) -> list[str]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if thoth_token:
        headers["X-Thoth-Token"] = thoth_token
    body = json.dumps(request_body(texts, thoth), ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url.rstrip("/") + "/translate", data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        tr = json.loads(r.read())["translations"]
    # thoth 워커는 상한에 걸린 자리를 null 로 돌려준다(부분 응답). 빈 문자열로 세고
    # 지표가 그만큼 떨어지게 둔다 — 조용히 빼면 표본이 몰래 줄어든다.
    return [t if isinstance(t, str) else "" for t in tr]


def via_backend(name: str):
    """이름으로 백엔드를 불러 `translate` 와 같은 모양의 함수를 돌려준다."""
    from . import backends
    fn, model = backends.get(name)
    return (lambda texts: fn(texts, {})), model


def door(h: str) -> None:
    """가설 대장의 문. 실험 상태의 가설이 아니면 재지 않는다."""
    import importlib.util
    root = pathlib.Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location("ch", root / "tools/check_hypotheses.py")
    ch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ch)
    rows = {hid: cells for _, hid, cells in ch.rows(ch.LEDGER.read_text(encoding="utf-8"))}
    if not h:
        raise SystemExit("가설이 없다 — --hypothesis H-NNN. 무엇을 확인하려는지 없이 재지 않는다(DECISIONS §12)")
    if h not in rows:
        raise SystemExit(f"{h} 가 가설 대장에 없다 — docs/hypotheses.md")
    if rows[h][0] != "실험":
        raise SystemExit(f"{h} 는 '{rows[h][0]}' 상태다 — 실험 상태여야 잰다(검증 방법 · 비용 상한)")


def estimate_usd(backend: str, rows: list[dict]) -> float:
    """돈이 드는 백엔드의 견적. 무료면 0 이다(DECISIONS §35)."""
    from . import backends
    rate = backends.PRICE_PER_MCHAR.get(backend, 0.0)
    return round(sum(len(r["src"]) for r in rows) * rate / 1_000_000, 4)


def onto_sha256() -> str:
    """온톨로지 파일의 해시. **채점기의 일부다**(DECISIONS §32).

    ★ `term` · `term_off` · `term_bad` 는 온톨로지의 `ko` · `alt_ko` · `bad_ko` 로 센다. 표기를 한 줄 더하면
      같은 번역의 점수가 바뀐다. 어느 사전으로 잰 숫자인지 결과가 들고 있어야 두 파일을 비교할 수 있다.
    """
    import hashlib
    from . import ontology
    return hashlib.sha256(ontology.DEFAULT.read_bytes()).hexdigest()[:16]


def conditions(a, rows: list[dict]) -> dict:
    """재현 조건. 결과 파일 머리줄에 싣는다."""
    import hashlib
    import subprocess
    from . import backends
    root = pathlib.Path(__file__).resolve().parent.parent

    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=10).stdout.strip()
        except OSError:
            return ""
    chars = sum(len(r["src"]) for r in rows)
    out = {"hypothesis": a.hypothesis or None,
           "commit": git("rev-parse", "--short", "HEAD") or None,
           "dirty": bool(git("status", "--porcelain")),
           "set_sha256": hashlib.sha256(pathlib.Path(a.set).read_bytes()).hexdigest()[:16],
           "onto_sha256": onto_sha256(),
           "chars": chars,
           "backend": a.backend or None,
           "weights": backends.WEIGHTS.get(a.backend or ""),
           "decoding": backends.DECODING_OF.get(a.backend or "")}
    if a.backend == "aws-translate":
        out["cost_usd"] = round(chars * 15 / 1_000_000, 4)   # 100만 자에 USD 15 — 인용(2026-09)
    if (a.backend or "") in backends.OLLAMA_OF:      # 이름으로 짐작하지 않는다(DECISIONS §45)
        out["ollama"] = ollama_placement()
    if (a.backend or "") in backends.REPAIR_ARMS:   # 처치가 일했는지를 결과가 말한다(DECISIONS §60)
        out["repair"] = dict(backends.REPAIR_STATS)
    return out


def ollama_placement() -> dict | None:
    """ollama 가 모델을 GPU 에 얼마나 올렸는가. **오프로딩되면 결과가 바뀐다**(thoth DECISIONS §35).
    런이 끝난 직후에 묻는다 — `keep_alive` 동안 모델이 남아 있다."""
    import os
    import urllib.request
    url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/") + "/api/ps"
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            models = json.loads(r.read()).get("models", [])
    except OSError:
        return None
    return {m.get("name", "?"): {"size": m.get("size"), "size_vram": m.get("size_vram"),
                                 "gpu_share": round(m["size_vram"] / m["size"], 3) if m.get("size") else None}
            for m in models}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    where = ap.add_mutually_exclusive_group(required=True)
    where.add_argument("--url")
    where.add_argument("--backend", help="서버 없이 백엔드를 바로 부른다")
    ap.add_argument("--set", required=True)
    ap.add_argument("--token", default="")
    ap.add_argument("--thoth", action="store_true", help="thoth 워커를 잰다")
    ap.add_argument("--thoth-token", default="")
    ap.add_argument("--name", default="")
    ap.add_argument("--hypothesis", default="", help="H-NNN — 대장에서 실험 상태여야 한다")
    ap.add_argument("--smoke", action="store_true", help="배선만 본다. 가설을 요구하지 않는다")
    ap.add_argument("--limit", type=int, default=0, help="앞에서 N줄만 잰다 — 돈이 드는 백엔드의 첫 판에 쓴다")
    ap.add_argument("--max-usd", type=float, default=1.0, help="이 실행이 쓸 수 있는 돈의 상한")
    a = ap.parse_args(argv)
    if not (a.smoke or a.backend == "echo"):
        door(a.hypothesis)

    rows = load(a.set)
    if a.limit:
        rows = rows[:a.limit]
    est = estimate_usd(a.backend or "", rows)
    if est > a.max_usd:
        raise SystemExit(f"견적 ${est:.2f} 가 상한 ${a.max_usd:.2f} 를 넘는다 — --limit 으로 줄이거나 상한을 올린다")
    if est:
        print(f"  견적 ${est:.2f} · {sum(len(r['src']) for r in rows):,}자 · 상한 ${a.max_usd:.2f}")
    if a.backend:
        call, model = via_backend(a.backend)
    else:
        model = ""
        def call(texts):
            return translate(a.url, texts, a.token, a.thoth or bool(a.thoth_token), a.thoth_token)
    outs: list[str] = []
    from . import backends as _b
    _b.REPAIR_STATS.update(tried=0, fixed=0)         # 이번 실행의 셈만 센다
    t = time.monotonic()
    for i in range(0, len(rows), BATCH):
        outs += call([r["src"] for r in rows[i:i + BATCH]])
    ms = (time.monotonic() - t) * 1000 / max(len(rows), 1)

    res = score(rows, outs)
    res["ms"] = round(ms)
    res["set"] = a.set
    res["url"] = a.url or f"backend:{a.backend}"
    if model:
        res["model"] = model
    res.update(conditions(a, rows))

    runs = pathlib.Path("runs")
    runs.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = runs / f"{a.name or 'eval'}-{stamp}.jsonl"
    with out.open("w", encoding="utf-8") as f:
        f.write(json.dumps({"meta": True, **res}, ensure_ascii=False) + "\n")
        for r, o in zip(rows, outs):
            f.write(json.dumps({"id": r.get("id"), "src": r["src"], "out": o,
                                "ref": r.get("ref")}, ensure_ascii=False) + "\n")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"→ {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
