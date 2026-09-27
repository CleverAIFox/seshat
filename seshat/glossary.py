"""참조 번역 — **그 줄에 나온 용어만** 골라 프롬프트에 싣는다(DECISIONS §134 · #16).

  from seshat import glossary
  glossary.for_line(onto, "Increase the quota for the stream.")
  # [("quota", "할당량"), ("stream", "스트림")]

★ **골라서 싣는 것이 요점이다.** 사전 137 줄을 통째로 싣는 것은 RAG 가 아니라 그냥 긴 프롬프트다 —
  맥락이 묽어지고 모델이 안 쓰는 용어까지 억지로 끼워 넣는다. **이 줄에 실제로 나온 것만** 싣는다.
★ **지금까지 모델은 공식 표기를 한 번도 못 봤다.** `terms.mask` 는 영어 이름을 **감추고**,
  `terms.fix_terms` 는 틀린 뒤에 **고친다.** 「이 낱말의 공식 한국어는 이것이다」 를 **미리 말해 준 적이
  없다.** #16 이 그 빈자리다.
★ **공식 표기(`ko`)만 싣는다.** `alt_ko` 를 같이 실으면 모델이 고를 여지가 생기고, 그러면 `term_off`
  가 안 오른다. 허용 표기는 채점이 받아 주는 것이지 **가르칠 것이 아니다.**
★ **자리표시와 같이 쓴다.** `with_placeholders` 안쪽에서 부르면 영어 이름은 이미 `⟦Tn⟧` 이라 사전에
  안 걸리고, 남은 개념만 실린다 — 두 처치가 서로 다른 자리를 맡는다.
★ **관측된 오역은 안 싣는다.** 「`쿼리 한도` 라고 쓰지 마라」 는 그 말을 프롬프트에 넣는 것이고,
  모델은 프롬프트에 있는 말을 쓴다.
"""
from __future__ import annotations

from . import ontology

CAP = 12        # 한 줄에 실을 최대 항목. 넘으면 앞에서 자른다 — 긴 사전은 안 읽힌다
HEAD = "Domain glossary for this sentence. Use exactly these Korean terms:"
KEEP = "keep in English"


def for_line(onto: list[dict], src: str, cap: int = CAP) -> list[tuple[str, str]]:
    """이 줄에 나온 (영어 표기, 실을 한국어). **나온 차례대로**, 겹치면 한 번만.

    개념은 공식 표기를, 영어로 남는 것은 `keep in English` 를 든다. 자리표시가 이미 뺀 이름은
    여기 안 걸린다 — 마스킹된 글자에는 그 이름이 없기 때문이다.
    """
    out: list[tuple[str, str]] = []
    본 = set()
    for a, b, s in ontology.find(onto, src):
        표기 = src[a:b]
        키 = 표기.lower()
        if 키 in 본:
            continue
        본.add(키)
        out.append((표기, KEEP if s.node["keep"] else s.node["ko"]))
        if len(out) >= cap:
            break
    return out


def block(pairs: list[tuple[str, str]]) -> str:
    """프롬프트에 실을 토막. **비면 빈 글자다** — 빈 사전을 실으면 모델이 없는 것을 찾는다."""
    if not pairs:
        return ""
    return HEAD + "\n" + "\n".join(f"- {en} → {ko}" for en, ko in pairs)
