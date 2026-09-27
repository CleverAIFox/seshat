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
  lit     원문이 `` ` `` 로 표시한 글자(식별자 · 값)가 그대로 남은 비율. 근거는 사전이 아니라 문서다
  ui      원문이 `**굵게**` 로 표시한 글자(콘솔 라벨)가 그대로 남은 비율. 한국어 문서도 영어로 둔다(§123)
  chrf    chrF++ (sacrebleu). `ref` 가 있는 줄만. 없으면 건너뛴다
  ms      문장당 지연

  josa    `keep` 이름 바로 뒤 조사가 그 이름의 끝소리와 맞는 비율(온톨로지 `coda`, H-001)
  term    원문에 나온 온톨로지 개념의 한국어(`ko` · `alt_ko`)가 번역에 있는 비율. 관계절의 머리 명사가
          사라지는지를 이것으로 본다(H-012). **문서가 표시한 자리는 개념이 아니다** — 분모에서 뺀다

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


_WORD = re.compile(r"[A-Za-z][A-Za-z0-9.\-]*")


def 지킨_이름_뺀다(src: str, out: str) -> str:
    """원문에 그대로 있는 영어 낱말을 출력에서 뺀다 — **지킨 이름은 번역이 아닌 증거가 아니다**(§91).

    ★ 2026-09-27, `S3 Glacier Instant Retrieval 을 구성한 다음 Amazon Simple Notification Service 에
      연결하십시오.` 가 「번역이 아니다」 로 걸렸다. 완벽한 번역인데 이름이 길어 로마자가 한글보다 많았다.
    ★ 원문에 **없는** 영어는 그대로 둔다 — 모델이 영어로 답한 것은 여전히 번역이 아니다.
    """
    쓴것 = set(_WORD.findall(src))
    return _WORD.sub(lambda m: "" if m.group(0) in 쓴것 else m.group(0), out)


def ko_line(src: str, out: str) -> bool:
    """이 줄이 번역처럼 보이는가(DECISIONS §50 · §91). 두 가지를 함께 본다.

    ① **지킨 이름을 뺀 뒤** 한글이 글자(한글 + 로마자) 중 20% 이상이다.
    ② 길이가 원문의 세 배를 넘지 않는다 — 사고문은 길다.

    ★ 처음에는 「한글이 두 자 이상인 줄」 로 셌다. 사고문이 한국어 낱말을 인용하자 그것도 1.0 이 됐다
      (2026-09-23 · Qwen3). **속은 지표를 고칠 때는 속인 예를 시험에 넣는다.**
    ★ 그 규칙이 이번에는 반대로 틀렸다 — 이름이 많은 줄의 바른 번역을 떨어뜨렸다. 지표는 양쪽으로 틀린다.
    """
    남은 = 지킨_이름_뺀다(src, out)
    ko, en = len(_HANGUL_CH.findall(남은)), len(_LATIN.findall(남은))
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


_찍은 = [0.0]          # 마지막으로 진척을 찍은 때(경과 초). 시간으로도 찍으려고 든다
말없이 = 45.0          # 이 초만큼 조용하면 찍는다


def _진척(before: int, done: int, total: int, elapsed: float) -> None:
    """긴 판이 말없이 도는 것을 막는다(DECISIONS §80 · §135).

    ★ 12B 를 CPU 로 내려 재는 판이 한 시간 돌면서 로그에 한 줄도 안 남겼다. 살아 있는지 죽었는지
      `ollama ps` 로 밖에서 물어야 했다 — **도구가 제 상태를 말하는 것이 도구의 일이다**(§51 · §60).
    ★ **열에 한 번으로는 모자랐다**(§135). N-best 는 줄당 4.4 초여서 열에 한 번이 **4.6 분에 한 번**이
      됐고, 사람이 멈춘 줄 알고 끊었다. 줄 수가 아니라 **시간으로도** 찍는다.
    ★ 표준 오류로 쓴다. 표준 출력은 결과 JSON 의 자리다 — 파이프로 받는 쪽을 깨뜨리지 않는다.
    """
    step = max(total // 10, 1)                 # 열에 한 번. 묶음 크기가 나누어떨어지지 않아도 선다
    if total < 20 or done <= 0 or done >= total:
        return
    if before // step == done // step and elapsed - _찍은[0] < 말없이:
        return
    _찍은[0] = elapsed
    남은 = elapsed / done * (total - done)
    print(f"  {done}/{total} · 줄당 {elapsed / done:.1f}초 · 남은 시간 약 {남은 / 60:.0f}분",
          file=sys.stderr, flush=True)


def part_path(name: str) -> pathlib.Path:
    """중간 결과의 자리. **이름당 하나**다 — 시각을 안 붙여야 다음 판이 찾는다."""
    return pathlib.Path("runs") / f"{name or 'eval'}.part.jsonl"


def part_read(path: pathlib.Path, 조건: dict) -> dict[str, str]:
    """중간 결과를 읽는다. **조건이 다르면 안 잇는다** — 다른 자로 잰 줄을 한 파일에 섞지 않는다(§45)."""
    줄 = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    머리 = next((x for x in 줄 if x.get("meta")), {})
    다름 = [k for k, v in 조건.items() if 머리.get(k) != v]
    if 다름:
        raise SystemExit(
            f"중간 결과가 다른 조건에서 만들어졌다 — {' · '.join(다름)}\n"
            + "".join(f"    {k}: 그때 {머리.get(k)!r} · 지금 {v!r}\n" for k, v in 조건.items() if k in 다름)
            + f"    이으려면 같은 조건으로 부르고, 아니면 {path} 를 지운다")
    return {x["id"]: x["out"] for x in 줄 if not x.get("meta") and x.get("id")}


def load(path: str) -> list[dict]:
    """평가셋을 읽는다. 없으면 **카탈로그가 아는 것을 말한다**(DECISIONS §72).

    ★ 셋은 대개 커밋하지 않는다 — 받거나(`tools/fetch_flores.py`) 다시 만든다(`tools/make_probes.py`).
      그 자리를 `data/catalog.toml` 의 `how` 가 이미 들고 있었는데 아무도 묻지 않았다.
    """
    p = pathlib.Path(path)
    if not p.exists():
        from . import catalog
        entries = catalog.load()
        e = catalog.match(entries, "repo", p.as_posix())
        how = f"\n    얻는다 : {e['how']}" if e and e.get("how") and e["how"] != "사람" else ""
        who = f"({e['id']} · {e['origin']})" if e else "(카탈로그 밖이다)"
        raise SystemExit(f"평가셋이 없다 — {path} {who}{how}")
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("//"):
            r = json.loads(line)
            if not r.get("meta"):
                rows.append(r)
    return rows


MARKS = ("lit", "ui")


def marked(row: dict) -> list[tuple[int, int]]:
    """원문에서 **문서가 표시한** 자리(DECISIONS §122 · §123). 개념 채점에서 뺀다.

    ★ `` `PARTITION` `` 안의 `partition` 은 개념이 아니라 SQL 낱말이다. `` `snapshot-repo` `` 안의
      `snapshot` 도 마찬가지다 — 「스냅샷-리포」로 바꾸면 그 지시는 안 먹는다.
    ★ **굵은 글씨도 뺀다.** 한국어 AWS 문서가 콘솔 라벨을 영어로 둔다는 것을 확인했다 —
      「왼쪽 탐색 창에서 [**Security Groups**]를 선택합니다」(DECISIONS §123).
    ★ **자리를 든다.** 줄은 `[[글자, 자리], …]` 로 싣고 여기서 맞는지 확인한다. 글자로만 들면
      같은 글자가 표시 밖에 또 있을 때 그것까지 빠진다 — **그것은 세는 척하는 것이다.**
    """
    src, out = row.get("src", ""), []
    for kind in MARKS:
        for t, at in row.get(kind, []):
            if src[at:at + len(t)] != t:
                raise SystemExit(f"{row.get('id')} 의 {kind} 가 자리를 틀리게 든다 — {t!r} @ {at}\n"
                                 f"    `python3 tools/fetch_awsdocs.py` 로 셋을 다시 만든다")
            out.append((at, at + len(t)))
    return out


def literal(rows: list[dict], outs: list[str]) -> dict[str, float | int | None]:
    """문서가 표시한 글자가 번역에 **그대로** 남았나(DECISIONS §122 · §123).

      lit  `` `코드` `` — 식별자 · 값 · API 이름. 옮기면 그 지시는 안 먹는다
      ui   `**굵게**` — 콘솔 라벨. 한국어 문서도 영어로 둔다(`[Type(유형)]` 처럼 주석만 붙인다)

    ★ **`keep` 과 근거가 다르다.** `keep` 은 사전이 아는 영어 이름이고 이 둘은 문서가 표시한 글자다.
      식별자는 무한하다 — `bucket-owner-full-control` · `snapshot-repo` · `search_path` 를 사전에
      다 적을 수 없고 적어서도 안 된다. **수확기가 원문의 표시를 지우고 있었던 것이 문제였지,
      사전이 좁았던 것이 아니다.**
    """
    res: dict[str, float | int | None] = {}
    for kind in MARKS:
        ok = total = 0
        for r, o in zip(rows, outs):
            for t, _ in r.get(kind, []):
                total += 1
                ok += t in o
        res[kind] = ok / total if total else None
        res[f"{kind}_n"] = total
    return res


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
        마크 = marked(r)
        for a, b, s in ontology.find(onto, r["src"]):
            if s.node["keep"]:
                continue
            if any(a >= x and b <= y for x, y in 마크):   # 코드로 표시된 자리는 개념이 아니다(§122)
                continue
            total += 1
            if not translated:      # 번역이 아닌 줄에서는 어떤 표기도 맞은 것이 아니다(DECISIONS §52)
                continue
            hit_off = s.node["ko"] in o
            hit = hit_off or any(k in o for k in s.node.get("alt_ko", []))
            off += hit_off
            ok += hit
            bad += (not hit) and any(k in o for k in s.node.get("bad_ko", []))
    # ★ **분모를 함께 싣는다**(DECISIONS §70). 비율만 있으면 사람이 약분해서 분모를 짐작한다 —
    #   2026-09-25 `0.846` 을 보고 분모를 78 이라 읽었는데 실제는 132/156 이었다. 사전이 넓어지면
    #   분모가 움직이므로, 분모를 모르면 두 숫자가 같은 것을 재는지조차 알 수 없다.
    if not total:
        return {"term": None, "term_off": None, "term_bad": None, "term_n": 0}
    return {"term": ok / total, "term_off": off / total, "term_bad": bad / total, "term_n": total}


def score(rows: list[dict], outs: list[str]) -> dict:
    n = len(rows)
    style = sum(is_hapsyo(o) for o in outs) / n if n else None
    kept = total = 0
    for r, o in zip(rows, outs):
        for k in r.get("keep", []):
            total += 1
            kept += k in o
    res = {"n": n, "style": style, "hangul": hangul(rows, outs), "keep": kept / total if total else None, "chrf": None,
           "josa": josa(rows, outs) if total else None, **term(rows, outs), **literal(rows, outs)}
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
    """돈이 드는 백엔드의 견적. 무료면 0 이다(DECISIONS §35 · §62).

    ★ **값을 모르는 백엔드는 공짜가 아니다.** 종전에는 표에 없는 이름이 0 원으로 떨어졌고, 그러면 상한이
      아무것도 안 막는다. 무료임을 **선언한** 백엔드(`FREE`)만 0 이고, 나머지 모르는 이름은 멈춘다.
    """
    from . import backends
    chars = sum(len(r["src"]) for r in rows)
    if backend in backends.PRICE_PER_MCHAR:
        return round(chars * backends.PRICE_PER_MCHAR[backend] / 1_000_000, 4)
    if backend in backends.FREE:
        return 0.0
    raise SystemExit(f"{backend} 의 값을 모른다 — 공짜인지 아닌지 모르는 채로 {chars:,}자를 던지지 않는다\n"
                     f"    무료면 : seshat/backends.py 의 FREE 에 적는다\n"
                     f"    아니면 : PRICE_PER_MCHAR 에 100만 자당 USD 를 적는다(근거와 날짜를 주석에)")


def onto_sha256() -> str:
    """온톨로지 파일의 해시. **채점기의 일부다**(DECISIONS §32).

    ★ `term` · `term_off` · `term_bad` 는 온톨로지의 `ko` · `alt_ko` · `bad_ko` 로 센다. 표기를 한 줄 더하면
      같은 번역의 점수가 바뀐다. 어느 사전으로 잰 숫자인지 결과가 들고 있어야 두 파일을 비교할 수 있다.
    """
    import hashlib
    from . import ontology
    return hashlib.sha256(ontology.DEFAULT.read_bytes()).hexdigest()[:16]


def set_sha256(path: str | pathlib.Path) -> str:
    """평가셋 파일의 해시. **머리줄에 적는 쪽이 한 군데여야 한다** — `rescore` 가 다른 셋을 대고도
    옛 해시를 그대로 옮겨 적고 있었다(DECISIONS §122)."""
    import hashlib
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()[:16]


def 코드_상태() -> dict:
    """지금 어느 커밋에서 도는가. **판을 시작할 때 찍는다**(DECISIONS §81).

    ★ 종전에는 판이 **끝난 뒤** 읽었다. 한 시간짜리 판이 도는 동안 패치를 붙이면, 결과 파일이 그 판을
      돌리지 않은 커밋을 제 조건이라고 적는다 — **재현 조건이 거짓말을 한다.**
    ★ 도구가 사람을 기다리게 하지 않는다. 「판이 끝날 때까지 저장소를 건드리지 마라」 는 규칙은
      사람이 지켜야 하는 규칙이고, 사람은 바쁠 때 어긴다(§72).
    """
    import subprocess
    root = pathlib.Path(__file__).resolve().parent.parent

    def git(*args):
        try:
            return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=10).stdout.strip()
        except OSError:
            return ""
    return {"commit": git("rev-parse", "--short", "HEAD") or None,
            "dirty": bool(git("status", "--porcelain"))}


def conditions(a, rows: list[dict], 코드: dict | None = None) -> dict:
    """재현 조건. 결과 파일 머리줄에 싣는다.

    ★ `코드` 는 판을 **시작할 때** 찍어 둔 상태다. 안 주면 지금 찍는다 — 짧은 판과 도구용 길이다.
    """
    from . import backends
    코드 = 코드 or 코드_상태()
    chars = sum(len(r["src"]) for r in rows)
    out = {"hypothesis": a.hypothesis or None,
           "commit": 코드["commit"],
           "dirty": 코드["dirty"],
           "set_sha256": set_sha256(a.set),
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
    if (a.backend or "") in backends.MBR_ARMS:      # 고르기가 일했는가 — 첫째를 안 고른 비율이 말한다
        from . import mbr
        n = max(mbr.STATS["판"], 1)
        out["mbr"] = {**{k: v for k, v in mbr.STATS.items() if k != "퍼짐_합"},
                      "퍼짐_평균": round(mbr.STATS["퍼짐_합"] / n, 2)}
    if a.url:                                       # 서버가 스스로 말하는 조건(DECISIONS §115)
        out["server"] = server_health(a.url, a.token, a.thoth_token)
    return out


def server_health(url: str, token: str = "", thoth_token: str = "") -> dict | None:
    """서버가 스스로 말하는 조건. **`--url` 실행은 이것이 없으면 조건 칸이 빈다**(DECISIONS §115).

    ★ 2026-09-27 H-050 의 결과 파일이 `backend: null` · `weights: null` 이었다. thoth 배포본을 쟀는데
      **어느 엔진이 낸 수인지 파일이 모른다.** §57 은 「조건을 적지 않은 측정은 재현되지 않는다」 고
      적어 놓고, `--backend` 쪽만 조건을 실었다.
    ★ **점수를 바꾸지 않는다.** 조건을 적는 것과 재는 자를 바꾸는 것은 다른 일이다(DECISIONS §96 의 범위).
    ★ 못 물으면 `None` 이다 — 0 이 아니라 「못 쟀다」 로 남는다.
    """
    import urllib.error
    import urllib.request
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if thoth_token:
        headers["X-Thoth-Token"] = thoth_token
    req = urllib.request.Request(url.rstrip("/") + "/health", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            got = json.loads(r.read())
    except (OSError, ValueError):
        return None
    # 상한 잔량은 잰 시각의 형편이지 재현 조건이 아니다 — 뺀다
    return {k: v for k, v in got.items() if k not in ("chars_used", "chars_remaining")} or None


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
    ap.add_argument("--resume", action="store_true", help="같은 이름의 중간 결과를 이어받는다")
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
    코드 = 코드_상태()                                # 판이 끝난 뒤가 아니라 **지금** 찍는다(§81)
    from . import backends as _b
    _b.REPAIR_STATS.update(tried=0, fixed=0)         # 이번 실행의 셈만 센다

    # ★ **중간 결과를 나오는 대로 쓴다**(DECISIONS §135). 끝나야 쓰면 26 분짜리 판이 끊길 때
    #   GPU 시간이 통째로 사라진다 — 그 시간은 다시 못 만든다(§28 과 같은 까닭)
    runs = pathlib.Path("runs")
    runs.mkdir(exist_ok=True)
    from . import catalog
    catalog.gate(runs)                  # 선언 안에 쓴다(DECISIONS §121)
    part = part_path(a.name)
    조건 = {"backend": a.backend or None, "url": a.url or "", "set_sha256": set_sha256(a.set),
            "onto_sha256": onto_sha256()}
    이미: dict[str, str] = {}
    if part.exists():
        if not a.resume:
            raise SystemExit(f"중간 결과가 남아 있다 — {part}\n"
                             f"    이어서 돌린다 : 같은 명령에 --resume 을 붙인다\n"
                             f"    처음부터     : 그 파일을 지운다")
        이미 = part_read(part, 조건)
        print(f"  이어서 돈다 — {len(이미)}/{len(rows)} 줄은 이미 있다", file=sys.stderr, flush=True)
    else:
        part.write_text(json.dumps({"meta": True, **조건}, ensure_ascii=False) + "\n", encoding="utf-8")

    남은줄 = [r for r in rows if r.get("id") not in 이미]
    새것: dict[str, str] = {}
    _찍은[0] = 0.0                # 판마다 진척 시계를 되돌린다 — 앞 판의 시계를 물려받으면 안 찍는다
    t = time.monotonic()
    with part.open("a", encoding="utf-8") as pf:
        for i in range(0, len(남은줄), BATCH):
            묶음 = 남은줄[i:i + BATCH]
            before = len(새것)
            for r, o in zip(묶음, call([r["src"] for r in 묶음])):
                새것[r.get("id")] = o
                pf.write(json.dumps({"id": r.get("id"), "out": o}, ensure_ascii=False) + "\n")
            pf.flush()
            _진척(before, len(새것), len(남은줄), time.monotonic() - t)
    # ★ **`ms` 는 이번 판에 실제로 부른 줄만 센다.** 이어 돌린 판에서 전체로 나누면 빨라 보인다
    ms = (time.monotonic() - t) * 1000 / max(len(남은줄), 1)
    outs = [{**이미, **새것}[r.get("id")] for r in rows]

    res = score(rows, outs)
    res["ms"] = round(ms)
    if 이미:
        res["resumed"] = len(이미)          # 몇 줄을 이어받았나 — `ms` 는 나머지만 잰 값이다
    res["set"] = a.set
    res["url"] = a.url or f"backend:{a.backend}"
    if model:
        res["model"] = model
    res.update(conditions(a, rows, 코드))

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = runs / f"{a.name or 'eval'}-{stamp}.jsonl"
    with out.open("w", encoding="utf-8") as f:
        f.write(json.dumps({"meta": True, **res}, ensure_ascii=False) + "\n")
        for r, o in zip(rows, outs):
            f.write(json.dumps({"id": r.get("id"), "src": r["src"], "out": o,
                                "ref": r.get("ref")}, ensure_ascii=False) + "\n")
    part.unlink(missing_ok=True)        # 온전한 결과가 생겼으니 중간 것은 없앤다
    print(json.dumps(res, ensure_ascii=False, indent=1))
    print(f"→ {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
