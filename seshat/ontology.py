"""AWS 온톨로지 — 도메인 지식의 원천(DECISIONS §13 · MASTER §7 R2).

  from seshat import ontology
  onto = ontology.load()                 # data/ontology/aws.jsonl
  ontology.validate(onto)                # 위반 목록. 비면 맞다
  ontology.find(onto, "Load it into Amazon S3 with Glue.")

★ **한 그래프를 세 곳에 쓴다** — 용어 자리표시(`seshat/terms.py`, H-001) · 참조 번역(H-006) · 강화학습의
  용어 보상(H-010). 용어 지식이 셋으로 갈라지면 셋이 어긋난다.
★ 노드는 넷이다 — `service` · `feature` · `api` 는 영어로 남고(`keep`), `concept` 은 한국어로 옮긴다(`ko`).
★ **끝소리(`coda`)를 노드가 든다.** 자리표시를 되돌릴 때 뒤의 조사를 고르는 근거다. 한국어로 읽은
  끝소리 — `none`(모음) · `closed`(받침) · `rieul`(ㄹ). 약어 별칭은 마지막 글자의 영어 읽기로 센다.
★ 별칭은 온톨로지 전체에서 유일하다(대소문자 무시). 한 표기가 두 노드를 가리키면 자리표시가 흔들린다.
★ **개념의 한국어는 셋이다** — `ko`(공식) · `alt_ko`(허용) · `bad_ko`(관측된 오역). `ko_ref` 가 있으면 AWS 한국어
  문서와 대조한 것이고, 없으면 아직 대조 전이다(DECISIONS §34).
★ **식별자는 여기 살지 않는다**(DECISIONS §122). `bucket-owner-full-control` 처럼 타이핑하는 값은 무한하고
  원문이 `` ` `` 로 이미 표시한다. 사전에 적으려 들면 API 참조가 되고도 여전히 모자란다 — `lit` 이 잰다.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "data/ontology/aws.jsonl"
# ★ `brand` — **서비스도 개념도 아닌 제공자 이름**(DECISIONS §165). `AWS` 는 50줄에 나오는데
#   어휘에 자리가 없어 사전 밖이었고, 그래서 `Amazon Web Services` 의 `Services` 가 개념으로 잡혔다.
#   억지로 `service` 로 넣으면 그 줄이 거짓말이 된다 — **자리가 없으면 자리를 만든다.**
KINDS = {"service", "feature", "api", "concept", "brand"}
CODAS = {"none", "closed", "rieul"}
SOURCES = {"author", "thoth-glossary", "aws-glossary"}   # AWS 공식 한국어 용어집(§165)
# ★ **어디서 베꼈는가와 누가 고르라 했는가는 다르다**(DECISIONS §168). `src` 는 **표기의 근거**이고
#   누수 장부(`data/ontology/mined.jsonl`)는 **이 노드를 넣기로 한 까닭이 어느 셋이었나** 를 든다.
#   2026-09-28 의 개념 14 는 표기를 AWS 공식 용어집에서 베꼈지만(`src=aws-glossary`) **무엇을 넣을지는
#   `d001` 이 골랐다** — 그 `d001` 이 점수를 내는 셋이다. **분모를 시험지가 정했다**(DECISIONS §192).
# ★ **장부가 딴 파일인 데는 까닭이 있다.** 여기 적으면 `onto_sha256` 이 바뀌고, **뜻이 하나도 안 바뀐
#   편집이 옛 판을 전부 「사전이 바뀌었다」 로 막는다**(compare.AXIS). 출처는 채점기 밖에 산다.
MINED = ROOT / "data/ontology/mined.jsonl"
MINED_FROM = re.compile(r"data/[a-z0-9_/-]+\.jsonl")
_HANGUL = re.compile(r"[가-힣]")
_ACRONYM = re.compile(r"^[A-Z0-9-]+$")
# 공식 표기의 근거 — AWS 한국어 문서의 <서비스>/<페이지>. URL 은 적지 않는다(DECISIONS §34)
KO_REF = re.compile(r"[a-z0-9_-]+/[A-Za-z0-9._-]+")
# 영어 글자 · 숫자를 한국어로 읽은 끝소리. 엘 · 알 은 ㄹ, 엠 · 엔 은 받침
_LETTER = {"L": "rieul", "R": "rieul", "M": "closed", "N": "closed"}
_DIGIT = {"1": "closed", "7": "closed", "9": "closed"}   # 원 · 세븐 · 나인
# ★ **식별자는 사전에 들어오지 않는다**(DECISIONS §122). 무한하고, 원문이 이미 `` ` `` 로 표시한다.
#   `search_path` · `KEYS_ONLY` · `tasks.max` · `bucket-owner-full-control` 을 노드로 올리기 시작하면
#   사전이 API 참조가 되고, 그래도 다음 문서의 새 식별자는 여전히 밖에 있다. **자는 `lit` 이 든다.**
#   붙임표 두 마디(`server-side` · `cross-account`)는 평범한 영어라서 세 마디부터 본다.
IDENTIFIER = (re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$"),          # search_path
              re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$"),          # KEYS_ONLY
              re.compile(r"^[a-z][a-z0-9]*(?:\.[a-z][a-z0-9]*)+$"),    # tasks.max
              re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+){2,}$"))       # bucket-owner-full-control


@dataclass(frozen=True)
class Surface:
    text: str
    node: dict
    coda: str | None


def load(path: Path = DEFAULT) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            if not d.get("meta"):
                out.append(d)
    return out


def acronym_coda(text: str) -> str:
    last = text.rstrip("-")[-1]
    return _DIGIT.get(last, "none") if last.isdigit() else _LETTER.get(last.upper(), "none")


def surfaces(onto: list[dict]) -> list[Surface]:
    """노드마다 표기(en + 별칭). 약어 별칭은 끝소리를 글자 읽기로 센다."""
    out = []
    for n in onto:
        for i, t in enumerate([n["en"], *n.get("aliases", [])]):
            if not n["keep"]:
                coda = None
            elif i and _ACRONYM.match(t):
                coda = acronym_coda(t)
            else:
                coda = n.get("coda")
            out.append(Surface(t, n, coda))
    return out


# ★ **채점기가 읽는 칸**(DECISIONS §171). `find` 와 `surfaces` 와 `terms` 가 쓰는 것만이다 —
#   `src` · `ko_ref` · `parent` · `note` 는 점수를 한 자리도 안 바꾼다. 여기 없는 칸을 고치는 것은
#   **뜻이 안 바뀐 편집**이고, 그런 편집이 옛 판을 「사전이 바뀌었다」 로 막으면 안 된다(§169).
# ★ **칸을 더할 때 여기도 더한다.** 안 더하면 새 칸이 점수를 바꾸는데 지문은 그대로다 —
#   **거짓 초록**이고, 그쪽이 거짓 빨강보다 나쁘다. `tests/test_ontology.py` 가 이 목록을 지킨다.
채점칸 = ("id", "kind", "en", "aliases", "keep", "coda", "ko", "alt_ko", "bad_ko")


def 채점_지문(onto: list[dict]) -> str:
    """**채점기가 읽는 것만** 추린 정규 글. 해시의 범위는 「파일」 이 아니라 「읽는 것」 이다."""
    몸 = [{k: n[k] for k in 채점칸 if k in n} for n in onto]
    몸.sort(key=lambda d: d.get("id", ""))
    return json.dumps(몸, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def validate(onto: list[dict]) -> list[str]:
    fails, ids = [], {}
    for n in onto:
        i = n.get("id", "?")
        if i in ids:
            fails.append(f"{i} 가 두 번 있다")
        ids[i] = n
        if n.get("kind") not in KINDS:
            fails.append(f"{i} 의 kind '{n.get('kind')}' 가 어휘 밖이다")
        if not i.startswith({"service": "svc.", "feature": "feat.", "api": "api.", "concept": "con.", "brand": "brand."}.get(n.get("kind"), "?")):
            fails.append(f"{i} 의 접두사가 kind 와 맞지 않는다")
        if n.get("src") not in SOURCES:
            fails.append(f"{i} 의 출처 '{n.get('src')}' 가 어휘 밖이다")
        if n.get("keep"):
            if n.get("kind") == "concept":
                fails.append(f"{i} 는 개념인데 영어로 남긴다")
            if n.get("coda") not in CODAS:
                fails.append(f"{i} 는 영어로 남는데 끝소리가 없다 — {sorted(CODAS)}")
            if n.get("ko"):
                fails.append(f"{i} 는 영어로 남는데 ko 가 있다")
        else:
            if not _HANGUL.search(n.get("ko") or ""):
                fails.append(f"{i} 는 옮기는데 ko 에 한글이 없다")
            alt, bad = n.get("alt_ko", []), n.get("bad_ko", [])
            if not isinstance(alt, list) or not isinstance(bad, list):
                fails.append(f"{i} 의 alt_ko · bad_ko 는 목록이다")
                continue
            for t in [*alt, *bad]:
                if not isinstance(t, str) or not t.strip():
                    fails.append(f"{i} 의 대체 · 오역 표기에 빈 값이 있다")
            if n.get("ko") in alt or n.get("ko") in bad:
                fails.append(f"{i} 의 ko 가 alt_ko · bad_ko 에도 있다")
            if set(alt) & set(bad):
                fails.append(f"{i} 의 표기 하나가 허용이면서 오역이다 — {sorted(set(alt) & set(bad))}")
            ref = n.get("ko_ref")
            # ★ **근거 없는 표기는 표기가 아니다**(DECISIONS §65). 2 판에서 60/60 을 채웠고, 그 뒤로 들어오는
            #   개념도 같은 문을 지난다. 1 판 60 개 중 셋이 「자연스러워서」 틀려 있었다.
            if not ref:
                fails.append(f"{i} 는 번역 대상인데 ko_ref 가 없다 — AWS 한국어 문서에서 표기를 확인한다")
            elif not KO_REF.fullmatch(ref):
                fails.append(f"{i} 의 ko_ref 는 <서비스>/<페이지> 다 — {ref!r}")
        if n.get("keep") and (n.get("alt_ko") or n.get("bad_ko") or n.get("ko_ref")):
            fails.append(f"{i} 는 영어로 남는데 한국어 표기 · 근거를 든다")
        if "mined_from" in n:
            fails.append(f"{i} 가 mined_from 을 든다 — 출처는 {MINED.name} 에 적는다. "
                         f"여기 적으면 onto_sha256 이 바뀌어 옛 판이 전부 못 견주게 된다")
    for n in onto:
        p = n.get("parent")
        if p and p not in ids:
            fails.append(f"{n['id']} 의 부모 {p} 가 없다")
        seen, cur = set(), n
        while cur and cur.get("parent"):
            if cur["id"] in seen:
                fails.append(f"{n['id']} 의 부모 사슬이 돈다")
                break
            seen.add(cur["id"])
            cur = ids.get(cur["parent"])
    owner: dict[str, str] = {}
    for s in surfaces(onto):
        if any(p.match(s.text) for p in IDENTIFIER):
            fails.append(f"'{s.text}' 는 식별자 모양이다({s.node['id']}) — 사전이 아니라 원문의 "
                         f"`코드` 표시가 든다(DECISIONS §122). 자는 `lit` 이다")
        k = s.text.lower()
        if k in owner and owner[k] != s.node["id"]:
            fails.append(f"표기 '{s.text}' 가 {owner[k]} 와 {s.node['id']} 둘을 가리킨다")
        owner.setdefault(k, s.node["id"])
    return fails


def 누수_장부(path: Path | None = None) -> list[dict]:
    """{id, mined_from, date, …}. 없으면 빈 목록 — 장부가 없는 것은 누수가 없는 것과 같이 다룬다."""
    p = path or MINED
    if not p.exists():
        return []
    return [d for d in (json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip())
            if not d.get("meta")]


def 캔_노드(셋: str | Path | None, 장부: list[dict] | None = None) -> list[str]:
    """**이 셋에서 캐서 넣은 노드**의 id. 그 셋으로 낸 점수는 그만큼 제 사전으로 잰 것이다.

    ★ **누수는 세는 것이지 지우는 것이 아니다**(DECISIONS §168). 이미 들어온 16 을 도로 뺄 수는 없다 —
      뺀다고 `d001` 의 점수가 깨끗해지지 않고, 모르는 채로 재는 것보다 **아는 채로 재는 것**이 낫다.
      그래서 판마다 이 수를 싣는다(`onto_leak`). 딴 셋에서 재면 저절로 0 이 되고, **0 이 되는 날이
      「사전 탓이 아니다」 를 말할 수 있는 날**이다(DECISIONS §192).
    """
    if not 셋:
        return []
    s = str(셋).replace("\\", "/")
    return sorted(d["id"] for d in (장부 if 장부 is not None else 누수_장부())
                  if d.get("mined_from") and s.endswith(d["mined_from"]))


def find(onto: list[dict], text: str, keep_only: bool = False) -> list[tuple[int, int, Surface]]:
    """본문에서 표기를 찾는다. **긴 것이 이긴다** — `Amazon Kinesis Data Streams` 가 `Kinesis Data
    Streams` 보다 먼저다. 낱말 경계를 지키고 겹치지 않는다. 개념은 복수 `s` 까지 받는다.

    ★ **복수는 규칙만 받는다 — `s` · `es` · `y→ies`.** 2026-09-28 까지 `y→ies` 가 빠져 있어
      `policies`(d001 16줄) · `queries` · `categories` 가 **한 번도 안 세어졌다**(DECISIONS §160).
      「짐작하지 않는다」 는 **파생**(compression → compress)에 대한 말이지 **굴절**에 대한 말이 아니다 —
      `s` 를 이미 짐작하면서 `ies` 를 안 짐작하는 것은 규율이 아니라 빠뜨린 것이다.
    ★ **개념은 동사로도 나타난다**(DECISIONS §69). `The catalog is ingested by …` 는 수집을 말하는
      문장인데 사전에 `ingestion` 만 있으면 못 찾는다. 변화형은 노드의 `aliases` 가 든다 — 여기서
      어미를 짐작하지 않는다. 짐작하면 `compression` 에서 `compress` 를 만들고 `data` 에서 `dat` 를 만든다.
    """
    cands = sorted((s for s in surfaces(onto) if s.node["keep"] or not keep_only), key=lambda s: -len(s.text))
    taken = [False] * len(text)
    out = []
    for s in cands:
        if s.node["keep"]:
            몸 = re.escape(s.text)                     # 이름은 복수로 안 쓴다
        elif re.search(r"[^aeiouAEIOU]y$", s.text):
            몸 = re.escape(s.text[:-1]) + "(?:y|ies)"   # policy · policies
        else:
            몸 = re.escape(s.text) + "(?:e?s)?"
        pat = re.compile(r"(?<![\w-])" + 몸 + r"(?![\w-])",
                         0 if (s.node["keep"] and _ACRONYM.match(s.text)) else re.I)
        for m in pat.finditer(text):
            if not any(taken[m.start():m.end()]):
                out.append((m.start(), m.end(), s))
                for k in range(m.start(), m.end()):
                    taken[k] = True
    return sorted(out, key=lambda x: x[0])
