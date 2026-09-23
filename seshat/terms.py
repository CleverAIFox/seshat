"""용어 자리표시 — 서비스명을 모델 밖에서 지킨다(H-001 · PLAN #15).

  masked, slots = terms.mask(onto, "Load data into Amazon S3 with AWS Glue.")
  # "Load data into ⟦T1⟧ with ⟦T2⟧."
  ko, missing = terms.unmask("⟦T2⟧로 ⟦T1⟧을 적재합니다.", slots)
  # "AWS Glue로 Amazon S3에 ..." · 조사는 끝소리로 고친다

★ **모델이 이름을 외우지 않게 한다.** 영어로 남을 이름(`keep`)을 번역 전에 뺐다가 뒤에 되돌린다. 그러면
  `Data Catalog` 가 한글로 새는 일은 원리상 없다. 남는 것은 조사다 — 모델은 `⟦T1⟧` 의 읽기를 모르므로
  조사를 틀리게 붙일 수 있다. 되돌릴 때 끝소리(`coda`)로 고친다.
★ **모델이 자리표시의 모양을 바꾼다.** H-001 에서 관계절 문장의 `⟦T1⟧` 이 `\\[T1]` 로 돌아왔다 — 괄호를
  마크다운처럼 이스케이프했다(DECISIONS §16). 되돌리기는 `⟦T1⟧` · `[T1]` · `\\[T1\\]` · `【T1】` 을 모두 받는다.
★ **사라진 자리표시는 실패로 센다.** 모델이 `⟦T1⟧` 을 빠뜨리거나 바꾸면 이름이 없어진 번역이다.
  `missing` 이 그것을 돌려준다 — H-001 의 판정 축이다.
"""
from __future__ import annotations

import re

from . import ontology

OPEN, CLOSE = "⟦", "⟧"
_SLOT = re.compile(r"⟦T(\d+)⟧")
# 받침 있음 · 없음 짝. ㄹ 뒤의 (으)로 는 '로' 다
_PAIRS = [("을", "를"), ("이", "가"), ("은", "는"), ("과", "와"), ("이나", "나"), ("이라", "라"), ("으로", "로")]


def mask(onto: list[dict], text: str) -> tuple[str, dict[str, dict]]:
    out, slots, last, n = [], {}, 0, 0
    for start, end, s in ontology.find(onto, text, keep_only=True):
        n += 1
        key = f"T{n}"
        slots[key] = {"text": text[start:end], "coda": s.coda, "id": s.node["id"]}
        out += [text[last:start], f"{OPEN}{key}{CLOSE}"]
        last = end
    out.append(text[last:])
    return "".join(out), slots


def particle(coda: str | None, got: str) -> str:
    """끝소리에 맞는 조사로 바꾼다. 짝이 없는 말은 그대로 둔다."""
    for closed, open_ in _PAIRS:
        if got in (closed, open_):
            if closed == "으로":
                return "으로" if coda == "closed" else "로"
            return closed if coda in ("closed", "rieul") else open_
    return got


# ★ 조사 뒤에 한글이 이어지면 조사가 아니다 — `⟦T1⟧이다` 의 `이` 는 서술격이다. 건드리지 않는다.
# ★ 모델이 바꾼 모양도 받는다 — `[T1]` · `\[T1]` · `\[T1\]` · `【T1】`(DECISIONS §16) · 백틱 `T1`(DECISIONS §24) ·
#   **괄호가 통째로 벗겨진 맨 `T1`**(DECISIONS §42 — AWS Translate 가 그렇게 돌려준다. 조사까지 붙여서 온다).
#   맨 모양은 앞뒤에 영숫자가 없을 때만 본다 — `MT1` · `T10` 을 잘못 집지 않는다.
SLOT_FORMS = (r"(?:⟦T(\d+)⟧|\\?\[T(\d+)\\?\]|【T(\d+)】|`T(\d+)`"
              r"|(?<![A-Za-z0-9])T(\d+)(?![0-9]))")
_AFTER = re.compile(SLOT_FORMS + r"(?:(으로|이나|이라|을|를|이|가|은|는|과|와|나|라|로)(?![가-힣]))?")
RESIDUE = re.compile(SLOT_FORMS)


def unmask(ko: str, slots: dict[str, dict]) -> tuple[str, list[str]]:
    seen = set()

    def put(m: re.Match) -> str:
        key = f"T{m.group(1) or m.group(2) or m.group(3) or m.group(4) or m.group(5)}"
        slot = slots.get(key)
        if slot is None:
            return m.group(0)
        seen.add(key)
        return slot["text"] + (particle(slot["coda"], m.group(6)) if m.group(6) else "")

    out = _AFTER.sub(put, ko)
    return out, sorted(set(slots) - seen)
