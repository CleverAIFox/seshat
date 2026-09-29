"""주 1회 신규 논문 · 모델을 훑어 `docs/next/papers.md` 의 「읽을 것」 에 후보를 붙인다(DECISIONS §126).

  python3 tools/watch_papers.py                 후보를 화면에
  python3 tools/watch_papers.py --write         docs/next/papers.md 에 붙인다
  python3 tools/watch_papers.py --days 14

★ **요약하지 않는다.** 제목 · 초록 첫 문장 · 왜 걸렸는지만 적고 **「읽을 것」 에 넣는다.** 표 본문의
  「무엇을 했나 · 가져올 것」 은 읽어야 쓸 수 있고, 안 읽고 쓰면 그것이 §77 이 금한 거짓말이다.
★ **못 재면 0건이 아니라 빨간불이다**(`tools/doctor.py` 와 같은 규율). 출처가 한 곳이라도 응답을 못
  주면 0 으로 세지 않고 죽는다 — 조용한 0 건은 「새 논문이 없다」 로 읽힌다.
★ **표준 라이브러리만 쓴다.** 예약 작업이 의존성 하나 때문에 조용히 멈추는 자리를 안 만든다.
★ **모델 후보는 라이선스를 「미확인」 으로 적는다.** HF 목록의 라이선스 태그는 자주 비어 있고,
  붙이는 순간 `seshat/licenses.py` 가 다시 묻는다(MASTER §12 · DECISIONS §9).
★ **main 을 밀지 않는다.** 봇 커밋이 main 을 움직이면 보낸 패치의 기준 나무가 갈린다(DECISIONS §30).
  워크플로는 가지를 만들고 PR 을 연다 — 합치는 때는 사람이 고른다.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAPERS = ROOT / "docs/next/papers.md"
UA = "seshat-watch-papers (https://github.com/CleverAIFox/seshat)"

# 무엇을 찾는가 — DECISIONS §126 의 다섯. 제목 + 초록에서 하나라도 걸려야 후보다
TOPICS: dict[str, re.Pattern] = {
    "영한": re.compile(r"\bkorean\b|\bko-en\b|\ben-ko\b|\bhangul\b", re.I),
    "소형": re.compile(r"\bsmall (?:language )?models?\b|\bdistillation\b|\bdistill(?:ing|ed)\b|\bsub-?billion\b"
                     r"|\b[0-4]\.?\d?\s?[bB] parameters?\b", re.I),
    "양자화": re.compile(r"\bquantiz(?:ation|ed|ing)\b|\bint8\b|\bint4\b|\bgptq\b|\bawq\b|\bgguf\b", re.I),
    "QE": re.compile(r"\bquality estimation\b|\breference-?free\b|\bcomet(?:kiwi)?\b|\bmetricx\b", re.I),
    "강화학습": re.compile(r"\b(?:reinforcement learning|rlhf|grpo|ppo|dpo|rlaif)\b", re.I),
}
# 번역 이야기여야 한다 — 위의 낱말은 번역 밖에서 훨씬 자주 나온다
MT = re.compile(r"\btranslation\b|\btranslate\b|\bmultilingual\b|\bmt\b", re.I)
ARXIV = "http://export.arxiv.org/api/query"
HF = "https://huggingface.co/api/models"
# 이미 대장에 있는 논문 — `arXiv 2508.14909` · `arxiv.org/abs/2508.14909`
SEEN = re.compile(r"ar[Xx]iv[ :/]+(?:abs/)?(\d{4}\.\d{4,5})")


def fetch(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise SystemExit(f"{urllib.parse.urlsplit(url).netloc} 을 못 물었다 — {type(e).__name__}: {e}\n"
                         f"    **0 건이 아니다.** 못 잰 것을 「새 것이 없다」 로 적지 않는다\n"
                         f"    그물을 본다 : curl -sI {url}\n"
                         f"    잠깐 넘어진 것이면 다시 부른다 — 이 도구는 주 1회 도는 것이다") from e


def topics_of(text: str) -> tuple[str, ...]:
    """걸린 주제들. 번역 이야기가 아니면 빈 값이다."""
    if not MT.search(text):
        return ()
    return tuple(k for k, p in TOPICS.items() if p.search(text))


def _tag(entry: str, name: str) -> str:
    m = re.search(rf"<{name}[^>]*>(.*?)</{name}>", entry, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def arxiv(days: int, cap: int = 200) -> list[dict]:
    """최근 `days` 일의 cs.CL 신규 중 주제에 걸린 것. **Atom 을 손으로 읽는다** — 의존성을 안 들인다."""
    오늘 = dt.date.today()
    q = (f"cat:cs.CL AND submittedDate:[{(오늘 - dt.timedelta(days=days)):%Y%m%d}0000 TO {오늘:%Y%m%d}2359]")
    url = (f"{ARXIV}?search_query={urllib.parse.quote(q)}"
           f"&start=0&max_results={cap}&sortBy=submittedDate&sortOrder=descending")
    body = fetch(url).decode("utf-8", "replace")
    entries = re.findall(r"<entry>(.*?)</entry>", body, re.S)
    if not entries:
        raise SystemExit("arXiv 이 항목을 하나도 안 줬다 — 질의나 Atom 모양이 바뀌었다(0 건이 아니다)\n"
                         f"    {url}\n    받은 길이 {len(body)}\n"
                         f"    눈으로 본다 : curl -s \"{url}\" | head -40\n"
                         f"    Atom 모양이 바뀐 것이면 이 도구의 <entry> 파싱을 고친다")
    out = []
    for e in entries:
        i = _tag(e, "id")
        title, summary = _tag(e, "title"), _tag(e, "summary")
        got = topics_of(f"{title} {summary}")
        if not got:
            continue
        out.append({"어디": "arXiv", "id": re.sub(r"^.*abs/|v\d+$", "", i), "제목": title,
                    "한 줄": summary.split(". ")[0][:220], "주제": got, "날짜": _tag(e, "published")[:10],
                    "링크": i})
    return out


def hugging(days: int, cap: int = 100) -> list[dict]:
    """최근 올라온 번역 모델. **라이선스는 미확인으로 적는다** — 목록의 태그를 믿지 않는다."""
    url = (f"{HF}?filter=translation&sort=createdAt&direction=-1&limit={cap}"
           f"&full=false&config=false")
    data = json.loads(fetch(url).decode("utf-8", "replace"))
    if not isinstance(data, list) or not data:
        raise SystemExit("Hugging Face 가 목록을 안 줬다 — 0 건이 아니다")
    자름 = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).isoformat()
    out = []
    for m in data:
        when = (m.get("createdAt") or "")[:len(자름)]
        if when and when < 자름:
            continue
        name, tag_list = m.get("id", ""), m.get("tags", [])
        # ★ **목록이 이미 번역 모델로 걸러져 있다.** 언어 태그는 낱말이 아니라 코드다 — `ko` 는
        #   초록에서는 잡음이지만 태그에서는 신호다. 그래서 논문과 다른 자로 본다
        got = topics_of(f"{name} {' '.join(tag_list)} translation")
        if "ko" in tag_list or re.search(r"\bko\b|korean", name, re.I):
            got = ("영한", *(x for x in got if x != "영한"))
        if not got:
            continue
        lic = next((t.split(":", 1)[1] for t in tag_list if t.startswith("license:")), None)
        out.append({"어디": "HF", "id": name, "제목": name,
                    "한 줄": f"태그 {' '.join(tag_list)[:120]}", "주제": got,
                    "날짜": (m.get("createdAt") or "")[:10],
                    "링크": f"https://huggingface.co/{name}",
                    "라이선스": lic or "미확인"})
    return out


def seen(text: str) -> set[str]:
    return set(SEEN.findall(text))


def lines(found: list[dict]) -> list[str]:
    out = []
    for f in found:
        꼬리 = f" · 라이선스 {f['라이선스']}" if f.get("라이선스") else ""
        out.append(f"- **{f['어디']} {f['날짜']}** [{f['제목']}]({f['링크']}) — {f['한 줄']} "
                   f"(걸린 주제 {' · '.join(f['주제'])}{꼬리})")
    return out


def write(text: str, 새것: list[str], 오늘: str) -> str:
    """「읽을 것」 아래에 붙인다. **표 본문은 안 건드린다** — 그 칸은 읽은 사람이 쓴다."""
    머리 = "## 읽을 것"
    if 머리 not in text:
        raise SystemExit(f"{PAPERS.name} 에 「{머리}」 가 없다 — 붙일 자리를 못 찾았다\n"
                         f"    그 제목 줄을 되살린다 : git log -p -- docs/next/papers.md | head -40")
    덩이 = "\n".join([f"\n### 훑은 날 {오늘}", *새것])
    i = text.index(머리) + len(머리)
    return text[:i] + "\n" + 덩이 + "\n" + text[i:].lstrip("\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=8, help="주 1회 예약이 한 번 밀려도 안 새게 8 이 기본이다")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)

    text = PAPERS.read_text(encoding="utf-8")
    있던 = seen(text)
    found = []
    for f in (*arxiv(a.days), *hugging(a.days)):
        if f["어디"] == "arXiv" and f["id"] in 있던:
            continue
        if f["링크"] in text or f["id"] in text:
            continue
        found.append(f)
    오늘 = f"{dt.date.today():%Y-%m-%d}"
    if not found:
        print(f"  {a.days}일 안에 걸린 것이 없다 — 출처 둘은 답했다")
        return 0
    새것 = lines(found)
    print("\n".join("  " + x for x in 새것))
    if a.write:
        PAPERS.write_text(write(text, 새것, 오늘), encoding="utf-8")
        print(f"\n  {PAPERS.relative_to(ROOT)} 의 「읽을 것」 에 {len(새것)}줄 붙였다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
