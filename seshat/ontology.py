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
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "data/ontology/aws.jsonl"
KINDS = {"service", "feature", "api", "concept"}
CODAS = {"none", "closed", "rieul"}
SOURCES = {"author", "thoth-glossary"}
_HANGUL = re.compile(r"[가-힣]")
_ACRONYM = re.compile(r"^[A-Z0-9-]+$")
# 공식 표기의 근거 — AWS 한국어 문서의 <서비스>/<페이지>. URL 은 적지 않는다(DECISIONS §34)
KO_REF = re.compile(r"[a-z0-9_-]+/[A-Za-z0-9._-]+")
# 영어 글자 · 숫자를 한국어로 읽은 끝소리. 엘 · 알 은 ㄹ, 엠 · 엔 은 받침
_LETTER = {"L": "rieul", "R": "rieul", "M": "closed", "N": "closed"}
_DIGIT = {"1": "closed", "7": "closed", "9": "closed"}   # 원 · 세븐 · 나인


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


def validate(onto: list[dict]) -> list[str]:
    fails, ids = [], {}
    for n in onto:
        i = n.get("id", "?")
        if i in ids:
            fails.append(f"{i} 가 두 번 있다")
        ids[i] = n
        if n.get("kind") not in KINDS:
            fails.append(f"{i} 의 kind '{n.get('kind')}' 가 어휘 밖이다")
        if not i.startswith({"service": "svc.", "feature": "feat.", "api": "api.", "concept": "con."}.get(n.get("kind"), "?")):
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
            if ref is not None and not KO_REF.fullmatch(ref or ""):
                fails.append(f"{i} 의 ko_ref 는 <서비스>/<페이지> 다 — {ref!r}")
        if n.get("keep") and (n.get("alt_ko") or n.get("bad_ko") or n.get("ko_ref")):
            fails.append(f"{i} 는 영어로 남는데 한국어 표기 · 근거를 든다")
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
        k = s.text.lower()
        if k in owner and owner[k] != s.node["id"]:
            fails.append(f"표기 '{s.text}' 가 {owner[k]} 와 {s.node['id']} 둘을 가리킨다")
        owner.setdefault(k, s.node["id"])
    return fails


def find(onto: list[dict], text: str, keep_only: bool = False) -> list[tuple[int, int, Surface]]:
    """본문에서 표기를 찾는다. **긴 것이 이긴다** — `Amazon Kinesis Data Streams` 가 `Kinesis Data
    Streams` 보다 먼저다. 낱말 경계를 지키고 겹치지 않는다. 개념은 복수 `s` 까지 받는다."""
    cands = sorted((s for s in surfaces(onto) if s.node["keep"] or not keep_only), key=lambda s: -len(s.text))
    taken = [False] * len(text)
    out = []
    for s in cands:
        suffix = "" if s.node["keep"] else "(?:e?s)?"
        pat = re.compile(r"(?<![\w-])" + re.escape(s.text) + suffix + r"(?![\w-])",
                         0 if (s.node["keep"] and _ACRONYM.match(s.text)) else re.I)
        for m in pat.finditer(text):
            if not any(taken[m.start():m.end()]):
                out.append((m.start(), m.end(), s))
                for k in range(m.start(), m.end()):
                    taken[k] = True
    return sorted(out, key=lambda x: x[0])
