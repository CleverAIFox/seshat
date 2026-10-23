"""강제자 줄이 **가리킨 자리를 푸는** 쪽(DECISIONS §325 · `PLAN #51`).

`docseal` 은 두 일을 한 파일에서 했다 — **무엇을 무나**(이 파일)와 **어떻게 무나**(지문).
2026-10-23 대장 절이 들어오며 804 줄이 됐고 `check_size` 의 라쳇이 울었다. **라쳇은
조이는 쪽으로만 움직인다** — 수를 올리는 것은 그 규칙의 목적을 뒤집는 짓이라 쪼갰다.
그 선은 `PLAN #51` 이 이미 적어 둔 선이다.

여기 있는 것은 전부 **묻는 자**다 : 이 줄이 셸의 어느 걸음을 가리키나 · 문서의 어느 절을
가리키나 · 대장의 어느 행을 가리키나. **무는 법(지문)은 `docseal` 에 남는다.**

★ **밖 — 이 파일은 지문을 **엮지** 않는다.** 글을 고르고(`_문서절` · `_행조각`) 그 조각을
  짧게 줄이는 기본자(`_짧게`)까지가 여기다. **조각들을 이어 한 절의 지문을 만드는 일**은
  `docseal.지문` 의 몫이다 — 여기를 고치면 **고른 범위**가 바뀌지 도장 꼴이 안 바뀐다.
★ **밖 — `docseal` 을 안 들여온다.** 들여오면 순환이다. 이쪽은 아무것도 모르는 쪽이다.
"""
from __future__ import annotations

import hashlib
import pathlib
import re

def _짧게(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]

#: 「`tools/verify.sh` 의 `scope` 단계」 · 「… 의 `shellcheck_step` 과 `check_prose` 단계」 —
#: **사람이 이미 걸음 이름을 적어 뒀다**(DECISIONS §316). 기계가 그 줄을 안 읽고 있었다.
#: ★ **「단계」 라는 낱말이 표식이다**(DECISIONS §322). 그것을 없어도 되게 풀었더니 사본에서
#:   「`tools/doctor.sh` 의 `PKG_N`」 처럼 **걸음이 아닌 이름**을 스물 줄 집었다 — 거기는
#:   검사가 산문처럼 이어져 걸음이라는 것이 없다. **표식을 요구하면 그 저장소는 저절로
#:   안 걸린다.** 좁히려면 사람이 그 낱말을 적는다 — 말하지 않은 것을 짐작하지 않는다.
_걸음말 = re.compile(r"`([\w./-]+\.sh)`\s*의\s+((?:`[^`\s]+`(?:\s*(?:와|과|·|,)\s*)?)+)\s*단계")


def _셸걸음(줄: str) -> dict[str, list[str]]:
    """강제자 줄이 **한글로 적어 둔** 걸음 이름. `{자리: [걸음…]}`.

    ★ **쓰여 있는 것을 읽는다 — 스물한 절을 고쳐 적지 않는다.** 뜻은 이미 그 줄에 있었고
      빠진 것은 **읽는 쪽**이었다(§206 · §315 와 같은 집안).
    ★ **밖 — 「두 갈래」 처럼 이름을 안 댄 줄은 못 읽는다.** 그런 절은 파일 전체를 문다 —
      좁히지 못한 것은 **넓게 두는 쪽이 안전하다.**
    """
    것: dict[str, list[str]] = {}
    for m in _걸음말.finditer(줄):
        # ★ **파일 이름은 걸음이 아니다**(DECISIONS §321). 「`tools/make_patch.sh` 의
        #   `mined.jsonl` 예외」 처럼 뒤에 **자리**가 오는 줄이 있다 — 점이나 빗금이 들면 뺀다.
        것.setdefault(m.group(1), []).extend(
            x for x in re.findall(r"`([^`\s]+)`", m.group(2)) if "." not in x and "/" not in x)
    return {k: v for k, v in 것.items() if v}
#: `verify.sh` 의 걸음을 여는 자리. **줄 맨 앞만이 아니다** — `else step …; fi` 도 걸음이다.
#: `tools/check_scope.py::_뽑는다` 와 **같은 무늬**다(DECISIONS §315 가 거기서 같은 실수를 했다)
_걸음무늬 = r"(?:\A|[;&|]|\b(?:else|then|do)\b)\s*step\s+%s(?:\s|$)"
def _셸_몸(글: str, 이름: str) -> str | None:
    """`tools/verify.sh::scope` 가 가리키는 **걸음 줄** 또는 **함수 몸**. 없으면 None.

    ★ **걸음이 먼저다.** `verify.sh` 를 짚은 절은 거의 다 「내 관문이 사슬에 걸렸나」 를
      말하고, 그 뜻을 지는 것은 **그 걸음 한 줄**이다. 옆 걸음이 늘어도 그 말은 안 변한다.
    ★ **함수는 맨 앞 `}` 까지 본다.** 중괄호를 세지 않는다 — `${CI:-}` 가 전부 걸린다.
      이 저장소의 셸 함수는 0칸의 `}` 로 닫는다.
    """
    줄들 = 글.splitlines()
    무늬 = re.compile(_걸음무늬 % re.escape(이름))
    걸음 = [x for x in 줄들
            if not x.lstrip().startswith(("#", "step()")) and 무늬.search(x)]
    if 걸음:
        return "\n".join(걸음)
    여는 = re.compile(rf"^\s*(?:function\s+)?{re.escape(이름)}\s*\(\)\s*\{{")
    시작 = next((n for n, x in enumerate(줄들) if 여는.match(x)), None)
    if 시작 is None:
        return None
    끝 = next((n for n, x in enumerate(줄들[시작 + 1:], 시작 + 1) if x.startswith("}")),
              len(줄들) - 1)
    return "\n".join(줄들[시작:끝 + 1])


def _걸음이있나(자리: pathlib.Path, 이름: str) -> bool:
    """그 파일에 그 걸음(또는 함수)이 **실제로 있나**(DECISIONS §321).

    ★ **없는 이름에 묶으면 지문이 `"없다"` 로 굳는다.** 한 번 울고 그 뒤로는 그 파일을
      아무리 고쳐도 **영영 안 운다** — 좁히려다 **꺼 버리는** 꼴이다. 사본(토트)의 강제자
      줄은 「`tools/doctor.sh` 의 `PKG_N`」 처럼 적는데 그 파일에 `step PKG_N` 이 없다.
    ★ **못 찾으면 파일 전체에 묶는다** — 넓은 쪽이 안전하다. 그 줄이 틀렸다는 것은
      `tools/check_prose.py::check_걸음이름` 이 따로 적는다.
    """
    try:
        return _셸_몸(자리.read_text(encoding="utf-8"), 이름) is not None
    except (OSError, UnicodeDecodeError):
        return False
# ★ **줄 대장은 줄 단위로 문다**(DECISIONS §215). `hypotheses.md` 는 194 행짜리 대장이라 가설 하나를
#   열고 닫을 때마다 바뀐다 — 그 파일을 짚은 절이 **전부 한꺼번에 무효**가 되고, 그 무효는 아홉 중
#   여덟이 「내가 안 건드린 남의 행」 때문이다. **소음이 된 무효는 안 읽힌다**(§211 과 같은 규율).
# ★ **PLAN 도 줄 대장이다**(DECISIONS §219). `hypotheses.md` 만 좁혀 놓고 PLAN 은 파일째 물었더니,
#   행 하나의 수를 고치자 그 문서를 짚은 절이 또 무효가 됐다 — §215 를 한쪽에만 적용한 것이다.
대장 = {"docs/PLAN.md": (r"^\| (\d+) \|", r"(?<![\w§-])#(\d+)(?!\d)")}

#: `.md` 중 **절을 이름으로 부르는** 문서 → 그 부름꼴(DECISIONS §323).
#: ★ **`.md` 만 통째였다.** `.py` 는 이름 단위, `.sh` 는 걸음 단위인데 여기만 바이트
#:   전체라 `docs/related.md` 한 줄이 절 **20** 을 무효로 만들었다. 재 보니 그중 **16** 이
#:   제 본문에 **`related.md §3`** 이라고 **어느 절인지 적고 있었다** — §317 과 같은 자리다 :
#:   **뜻은 이미 거기 있었고 빠진 것은 읽는 쪽**이다.
#: ★ **무늬를 좁게 둔다.** 처음엔 열 글자를 건너뛰게 했더니 §314 가 「MASTER … (DECISIONS
#:   §287)」 에서 **287** 을 MASTER 절로 집었다. `§` 는 이름 **바로 뒤**여야 한다.
#: ★ **안 대면 통째로 문다.** 넷이 그렇고, 그것이 맞다 — 그 절들은 문서 전체를 말한다.
#:   **단 대장 절은 뺀다**(아래 `대장절`).
문서대장 = {"docs/MASTER.md": r"(?<![\w가-힣])MASTER(?:\.md)?`?\s*§([\w.-]+)"}

#: **MASTER 안의 대장 절** → (행꼴, 부름꼴)(DECISIONS §325). 표를 담은 절이다.
#: ★ **접으면 §215 가 도로 풀린다.** 밖에 있을 때 `hypotheses.md` 는 행 단위로 물려
#:   가설을 열고 닫아도 안 울었다(실측 0). 그냥 절이 되면 **절을 안 댄 강제자 다섯**이
#:   통째로 물어 **행 하나에 다섯**이 된다. `watch_papers.py` 는 주 1회 봇이 쓴다 —
#:   **주마다 거짓이면 사람이 도장을 끈다**(hathor GR-0.8).
#: ★ **밖 — 대장 절의 산문 머리말도 같이 빠진다.** 표와 설명을 안 갈랐다 — 그 경계를
#:   기계가 못 읽는다. 넓게 빼는 쪽은 거짓 초록이고, 반대쪽은 **도장 자체를 죽인다.**
대장절: dict[str, tuple[str, str]] = {"20": (r"^\| (H-\d+) \|", r"H-\d+")}

#: **접힌 문서 → 그 글이 들어간 MASTER 절**(DECISIONS §324). 2026-10-23 에 위성 넷을
#: MASTER 로 접었다. 옛 절의 **본문은 못 고친다**(추가만 · §296) — 거기 적힌
#: 「`docs/related.md` §3」 은 그대로 남는다. 그래서 **옛 이름을 읽어 새 절로 되짚는다.**
#: ★ **안 되짚으면 §323 이 푼 것이 도로 풀린다.** 스무 절이 MASTER 를 **통째로** 물게 되고,
#:   MASTER 는 절 쓸 때마다 바뀐다 — **접기가 도장을 넓히는** 바로 그 자리다.
접힌문서 = {"escape.md": "16", "colab.md": "17", "grammar.md": "18", "related.md": "19",
            "hypotheses.md": "20"}
#: `.md` 의 **절 머리**. `## 7. 제목` · `## §7. 제목` · `## 제목` 을 다 받는다
_절머리 = re.compile(r"^## +(?:§?([\w.-]+)\.\s*)?(.*)$")


def _문서절(글: str, 이름: str) -> str | None:
    """`docs/MASTER.md::7` 이 가리키는 **절 하나의 본문**. 없으면 None(DECISIONS §323).

    ★ **`.md` 만 통째였다.** `.py` 는 이름 단위, `.sh` 는 걸음 단위인데 `.md` 는 바이트
      전체였다 — `docs/related.md` 한 줄이 절 **20** 을 무효로 만든다. 그 문서에 절이
      넷인데 그중 하나만 보는 절들이 전부 운다.
    ★ **번호로도 제목으로도 부른다.** `::7` 과 `::데이터 관리` 가 같은 절을 가리킨다 —
      사람이 적는 쪽을 기계가 맞춘다.
    ★ **밖 — 절 밖(머리말 · 표)은 안 본다.** 그 자리를 고치면 **절을 짚은 자는 안 운다.**
      통째로 짚은 자가 그 자리를 든다 — 좁히지 않은 쪽이 넓게 문다.
    """
    줄 = 글.splitlines()
    머리 = [(n, m) for n, x in enumerate(줄) if (m := _절머리.match(x))]
    찾 = 이름.strip().lstrip("§")
    # ★ **규칙 번호는 제 절에 묶는다**(DECISIONS §323). `MASTER §0-1` 은 절이 아니라
    #   **절 0 안의 ★ 줄**이다 — 그 저장소 규약이 그렇다. 그대로 찾으면 못 찾고,
    #   못 찾으면 **문서 전체**로 넓어진다. 앞마디로 되짚어 그 절을 문다.
    if 찾 and "-" in 찾 and not any((m.group(1) or "") == 찾 for _, m in 머리):
        찾 = 찾.split("-", 1)[0]
    for i, (n, m) in enumerate(머리):
        번호, 제목 = (m.group(1) or "").strip(), (m.group(2) or "").strip()
        if 찾 != 번호 and 찾 not in 제목:
            continue
        끝 = 머리[i + 1][0] if i + 1 < len(머리) else len(줄)
        return "\n".join(줄[n:끝])
    return None


def _행조각(행꼴: str, 부름꼴: str, 본문: str, 글: str) -> str:
    """부른 행만 남긴다. 안 부르면 빈 글자다(= 지문 밖).

    ★ 파일 대장이든 절 대장이든 무는 법은 같다 — 다른 것은 **글을 어디서 떠 오나**뿐이다
      (DECISIONS §325).
    """
    번호 = set(re.findall(부름꼴, 본문))
    if not 번호:
        return ""
    줄 = [x for x in 글.splitlines()
          if (m := re.match(행꼴, x)) and m.group(1) in 번호]
    return _짧게("\n".join(줄)) if 줄 else ""


#: **공개 이름** — 다른 도구가 문서의 절 하나를 떠 갈 때 쓴다(DECISIONS §327).
#: ★ `check_hypotheses` · `lake` 가 대장을 MASTER §20 에서 떠 온다. 자르는 법을 **두 번
#:   적지 않는다** — 같은 것을 두 곳에 적으면 한쪽만 늙는다(§57).
절을_뜬다 = _문서절


def _대장절을_비운다(글: str) -> str:
    """대장 절의 본문 줄을 **빈 줄로 바꾼다**(DECISIONS §327). **줄 번호는 그대로다.**

    `check_docs` 의 참조 검사가 쓴다 — 대장 절은 과거를 적어 지금의 지도로 재지 않는다.
    ★ **지우지 않고 비운다.** 지우면 줄 번호가 밀려 **다른 줄을 가리킨다.**
    """
    if not 대장절:
        return 글
    줄 = 글.splitlines()
    머리 = [(n, m) for n, x in enumerate(줄) if (m := _절머리.match(x))]
    for i, (n, mm) in enumerate(머리):
        if (mm.group(1) or "").strip() not in 대장절:
            continue
        끝 = 머리[i + 1][0] if i + 1 < len(머리) else len(줄)
        for k in range(n + 1, 끝):
            줄[k] = ""
    return "\n".join(줄)


def _대장_조각(자리: str, 본문: str, 글: str) -> str:
    """절이 이름으로 부른 행만 남긴다. **아무 행도 안 부르면 그 파일은 지문 밖이다.**"""
    행꼴, 부름꼴 = 대장[자리]
    return _행조각(행꼴, 부름꼴, 본문, 글)


def _대장절을_뺀다(글: str) -> str:
    """대장 절의 **본문을 덜어낸 글** — 절을 안 댄 강제자가 무는 자리다(DECISIONS §325).

    ★ **머리 줄은 남긴다.** 절이 **사라지는 것**은 뼈대라 보이고, **행이 늘고 주는 것**은
      안 보인다. 선언이 없으면 글이 그대로 돌아온다.
    ★ **밖 — 절 안이 어떻게 바뀌었는지는 못 본다.** 그것은 그 절을 **이름으로 부른 자**의
      몫이고, 그쪽은 행으로 문다.
    """
    if not 대장절:
        return 글
    줄 = 글.splitlines()
    머리 = [(n, m) for n, x in enumerate(줄) if (m := _절머리.match(x))]
    뺄: set[int] = set()
    for i, (n, m) in enumerate(머리):
        if (m.group(1) or "").strip() not in 대장절:
            continue
        끝 = 머리[i + 1][0] if i + 1 < len(머리) else len(줄)
        뺄 |= set(range(n + 1, 끝))        # 머리 줄은 남긴다
    return "\n".join(x for k, x in enumerate(줄) if k not in 뺄)
