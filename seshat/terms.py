"""용어 자리표시 — 서비스명을 모델 밖에서 지킨다(H-001 · H-016 채택 · DECISIONS §17).

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

import functools
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
    """끝소리에 맞는 조사로 바꾼다. 짝이 없는 말은 그대로 둔다.

    ★ **끝소리를 모르면 그대로 둔다.** 종전에는 `None` 을 받침 없는 쪽으로 **짐작**했다 — 콘솔
      라벨처럼 읽기를 모르는 자리가 생기자 그 짐작이 맞던 조사를 틀리게 만들 수 있게 됐다.
      `fix_particles` 와 같은 규율이다(DECISIONS §151).
    """
    if not coda:
        return got
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
def _forms(letter: str = "T") -> str:
    """자리표시의 모든 모양. **글자를 인자로 받는다** — 같은 규칙을 두 번 쓰지 않는다(DECISIONS §151).

    `T` 는 이름(온톨로지가 아는 것), `U` 는 콘솔 라벨(줄이 아는 것)이다. 모델이 모양을 바꾸는 방식은
    둘이 같으므로 **정규식도 하나여야 한다** — 따로 쓰면 한쪽만 고쳐지고, 오늘 그 병을 셋 봤다.
    """
    L = re.escape(letter)
    return (rf"(?:⟦{L}(\d+)⟧|\\?\[{L}(\d+)\\?\]|【{L}(\d+)】|`{L}(\d+)`"
            rf"|(?<![A-Za-z0-9]){L}(\d+)(?![0-9]))")


_JOSA_TAIL = r"(?:(으로|이나|이라|을|를|이|가|은|는|과|와|나|라|로)(?![가-힣]))?"
SLOT_FORMS = _forms("T")
_AFTER = re.compile(SLOT_FORMS + _JOSA_TAIL)
RESIDUE = re.compile(SLOT_FORMS)


@functools.lru_cache(maxsize=8)
def _after_of(letter: str) -> re.Pattern:
    return re.compile(_forms(letter) + _JOSA_TAIL)


@functools.lru_cache(maxsize=8)
def _residue_of(letter: str) -> re.Pattern:
    return re.compile(_forms(letter))


BASE, JONG, _RIEUL = 0xAC00, 28, 8
_PARTICLE = r"(?:(으로|이나|이라|을|를|이|가|은|는|과|와|나|라|로)(?![가-힣]))?"


def ko_coda(text: str) -> str | None:
    """한국어 표기의 끝소리. 한글로 끝나지 않으면 모른다(None)."""
    last = text.strip()[-1:] if text.strip() else ""
    i = ord(last) - BASE if last else -1
    if not 0 <= i < 11172:
        return None
    jong = i % JONG
    return "none" if jong == 0 else ("rieul" if jong == _RIEUL else "closed")


def fix_terms(onto: list[dict], ko: str, src: str | None = None) -> tuple[str, list[str]]:
    """관측된 오역(`bad_ko`)을 공식 표기(`ko`)로 바꾼다 — H-033 의 처치(DECISIONS §56 · §67).

    ★ **원문을 본다.** `src` 를 주면 **그 줄의 원문에 그 개념이 있는 노드만** 고친다. 안 그러면 흔한 말이
      휩쓸린다 — `제한` 은 throttling 의 오역이기도 하지만 limit · restriction 의 바른 번역이기도 하다.
      2026-09-23 탐침에서 `요청을 제한하면` 이 `요청을 스로틀링하면` 으로 바뀌었다. 여기서는 맞았지만
      원문에 throttling 이 없는 줄이었다면 멀쩡한 번역을 망가뜨린 것이다.

    ★ **조사를 같이 고친다.** `휴지 암호화를` → `저장 시 암호화를` 은 끝소리가 같아 괜찮지만, 끝소리가
      바뀌는 짝에서는 조사가 틀어진다. 되돌리기(`unmask`)와 같은 셈을 쓴다.
    ★ 긴 오역부터 본다 — `글로벌 이차 인덱스` 를 `이차 인덱스` 가 먼저 먹으면 `글로벌` 이 남는다.
    ★ **사전에 적힌 것만 바꾼다.** 모델이 새로 지어낸 말은 여기서 안 잡힌다 — 그건 눈으로 보고 사전에
      올리는 일이다(`tools/show_misses.py`).
    """
    hits = []
    here = None if src is None else {s.node["id"] for s in [x[2] for x in ontology.find(onto, src)]}
    for n in onto:
        if n["keep"] or (here is not None and n["id"] not in here):
            continue
        good, coda = n["ko"], ko_coda(n["ko"])
        for bad in sorted(n.get("bad_ko", []), key=len, reverse=True):
            if bad == good or bad not in ko:
                continue
            pat = re.compile(re.escape(bad) + _PARTICLE)
            ko, cnt = pat.subn(lambda m: good + (particle(coda, m.group(1)) if m.group(1) else ""), ko)
            if cnt:
                hits.append(f"{bad} → {good}")
    return ko, hits


# 이름 바로 뒤의 조사. `_AFTER` 와 같은 목록이고 같은 규칙이다 — 뒤에 한글이 이어지면 조사가 아니다
_JOSA_AFTER = "(으로|이나|이라|을|를|이|가|은|는|과|와|나|라|로)(?![가-힣])"


def fix_particles(text: str, slots: dict[str, dict]) -> str:
    """이름 뒤 조사를 끝소리에 맞춘다 — **자리표시를 안 거친 글에도**(DECISIONS §149).

    ★ 고치는 판(`with_placeholders(..., repair=)`)은 **원문을 그대로 준다.** 그래서 그 답에는 `⟦Tn⟧` 이
      없고 `unmask` 가 안 불리며, **H-013 의 끝소리 조사 고르기가 통째로 건너뛰어진다.** 2026-09-28
      `keep` 이 0.9979 로 오르는 동안 `josa` 가 구성상 1.000 에서 0.9918 로 내려간 것이 그 자국이다 —
      고치는 판이 **이름은 살리고 조사는 버렸다.**
    ★ 긴 이름부터 본다 — `Amazon EMR` 을 `EMR` 로 먼저 잡으면 앞이 남는다.
    ★ 틀린 조사만 바뀐다. 맞는 것은 `particle` 이 그대로 돌려준다.
    """
    for slot in sorted(slots.values(), key=lambda s: -len(s["text"])):
        name, coda = slot["text"], slot.get("coda")
        if not coda:
            continue
        text = re.sub(re.escape(name) + _JOSA_AFTER,
                      lambda m: name + particle(coda, m.group(1)), text)
    return text


def hide(text: str, spans: list, letter: str = "U") -> tuple[str, dict[str, dict]]:
    """줄이 아는 자리(`ui` 같은)를 `⟦U1⟧` 로 뺀다 — 온톨로지가 아니라 **자리로** 뺀다(§151).

      hide("Choose Security Groups.", [["Security Groups", 7]])
      # ("Choose ⟦U1⟧.", {"U1": {"text": "Security Groups", "coda": None}})

    ★ **뒤에서부터 자른다** — 앞을 먼저 바꾸면 뒤 자리가 밀린다.
    ★ **자리가 안 맞으면 멈춘다.** 글자가 그 자리에 없으면 셋이 코드와 어긋난 것이고, 조용히 넘기면
      **세는 척하는 것**이 된다(`evaluate.marked` 와 같은 규율 · DECISIONS §122).
    ★ 끝소리는 `None` 이다 — 임의의 영어 라벨은 읽기를 모른다. 조사는 손대지 않는다.
    """
    자리 = sorted(((int(at), str(t)) for t, at in (spans or [])), reverse=True)
    slots, 새, n = {}, text, len(자리)
    for at, t in 자리:
        if text[at:at + len(t)] != t:
            raise SystemExit(f"{letter} 자리가 틀리다 — {t!r} @ {at}\n"
                             f"    `python3 tools/fetch_awsdocs.py` 로 셋을 다시 만든다")
        key = f"{letter}{n}"
        slots[key] = {"text": t, "coda": None}
        새 = 새[:at] + f"{OPEN}{key}{CLOSE}" + 새[at + len(t):]
        n -= 1
    return 새, slots


def hide_all(text: str, groups: list[tuple[list, str]]) -> tuple[str, dict[str, dict[str, dict]]]:
    """여러 종류를 **한 번에** 뺀다 — 종류마다 따로 부르면 앞의 것이 뒤의 자리를 민다(DECISIONS §152).

      hide_all("Set books-policy under Encryption.", [(lit_spans, "L"), (ui_spans, "U")])

    ★ 2026-09-28 `lit` 을 먼저 빼고 `ui` 를 부르자 「자리가 틀리다」 로 멈췄다 — **멈춘 것이 옳았다.**
      자리 검사가 없었으면 엉뚱한 글자를 뺐을 것이다(`evaluate.marked` 와 같은 값어치).
    ★ 자리는 **원문 기준**이고 자르기는 **뒤에서부터**다. 종류가 섞여도 규칙은 하나다.
    """
    모 = []
    for spans, letter in groups:
        for x, at in (spans or []):
            모.append((int(at), str(x), letter))
    slots: dict[str, dict[str, dict]] = {letter: {} for _, letter in groups}
    센다 = {letter: len([1 for spans, L in groups if L == letter for _ in (spans or [])]) for _, letter in groups}
    새 = text
    for at, x, letter in sorted(모, reverse=True):
        if text[at:at + len(x)] != x:
            raise SystemExit(f"{letter} 자리가 틀리다 — {x!r} @ {at}\n"
                             f"    `python3 tools/fetch_awsdocs.py` 로 셋을 다시 만든다")
        key = f"{letter}{센다[letter]}"
        slots[letter][key] = {"text": x, "coda": None}
        새 = 새[:at] + f"{OPEN}{key}{CLOSE}" + 새[at + len(x):]
        센다[letter] -= 1
    return 새, slots


def unmask(ko: str, slots: dict[str, dict], letter: str = "T") -> tuple[str, list[str]]:
    seen = set()

    def put(m: re.Match) -> str:
        key = f"{letter}{m.group(1) or m.group(2) or m.group(3) or m.group(4) or m.group(5)}"
        slot = slots.get(key)
        if slot is None:
            return m.group(0)
        seen.add(key)
        return slot["text"] + (particle(slot["coda"], m.group(6)) if m.group(6) else "")

    out = _after_of(letter).sub(put, ko)
    return out, sorted(set(slots) - seen)
