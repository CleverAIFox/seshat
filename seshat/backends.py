"""번역 백엔드. 서버는 이것만 부른다.

★ **백엔드는 `(texts, terms) -> translations` 하나다.** 모델이 CTranslate2 든
  llama.cpp 든 transformers 든 서버 · 평가 · 계약 검사는 모른다. 새 모델은 여기에
  함수 하나를 더한다.

★ **무거운 의존성은 함수 안에서 import 한다.** `echo` 로 계약 검사를 도는 CI 가
  torch 를 받으면 안 된다.
"""
from __future__ import annotations

import re
import sys as _sys
from typing import Callable

Backend = Callable[[list[str], dict[str, str]], list[str]]


def echo(texts: list[str], terms: dict[str, str]) -> list[str]:
    """과금 0 · 의존성 0. 계약과 배선만 본다."""
    return [f"[KO] {t}" for t in texts]


def aws_translate(texts: list[str], terms: dict[str, str], client=None) -> list[str]:
    """AWS Translate — **이길 대상 1호다**(DECISIONS §11). 서빙하지 않는다. 기준선만 잰다.

    ★ `terms` 를 쓰지 않는다. Custom Terminology 는 미리 등록해야 하고 AWS 전용이다 —
      기준선은 AWS Translate 를 **있는 그대로** 잰다.
    ★ 자격증명은 boto3 가 찾는다(`AWS_PROFILE` 등). 이 저장소는 키를 들지 않는다.
    ★ **리전을 짐작하지 않는다**(DECISIONS §36). 없으면 `NoRegionError` 가 botocore 깊은 곳에서 터지는데, 그 말은
      무엇을 해야 하는지 알려주지 않는다. 여기서 먼저 보고 무엇을 적어야 하는지 말한다.
    ★ 과금이다 — 100만 자에 USD 15(2026-09 인용, thoth MASTER §7). FLORES+ devtest 한 판이 약 13만 자다.
    """
    if client is None:
        import os
        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or ""
        if not region:                       # 의존성을 들이기 전에 본다 — 설정이 틀린 것을 설치로 덮지 않는다
            raise SystemExit("AWS 리전이 없다 — .env 에 AWS_REGION 을 적는다(예: ap-northeast-2)\n"
                             "    자격증명은 AWS_PROFILE 이나 ~/.aws 가 든다. 이 저장소는 키를 들지 않는다")
        try:
            import boto3  # 무거운 의존성은 함수 안에서(모듈 머리말)
        except ModuleNotFoundError:
            # ★ uv 는 부를 때 준 그룹으로 환경을 맞춘다 — `--group data` 로 한 번 돌면 boto3 가 빠진다.
            #   그 자리에서 무엇을 쳐야 하는지 말한다(DECISIONS §74)
            raise SystemExit("boto3 가 없다 — AWS 백엔드는 `aws` 그룹이 든다\n"
                             "    친다 : uv run --group aws python -m seshat.evaluate …\n"
                             "    까닭 : uv 는 부를 때 준 그룹으로 환경을 맞춘다. 다른 그룹으로 한 번 돌면 빠진다") from None
        client = boto3.client("translate", region_name=region)
    out = []
    for t in texts:
        try:
            r = client.translate_text(Text=t, SourceLanguageCode="en", TargetLanguageCode="ko")
        except Exception as e:                    # noqa: BLE001 — botocore 예외를 이름으로 가른다
            raise _aws_말(e) from None
        out.append(r["TranslatedText"])
    return out


# ★ 자격증명이 만료되면 botocore 가 40 줄을 뱉는다. 두 번째다(2026-09-23 · 09-25) — 도구가 말한다(§75)
_만료 = ("LoginRefreshRequired", "UnauthorizedSSOTokenError", "TokenRetrievalError",
         "SSOTokenLoadError", "ExpiredTokenException")


def _aws_말(e: Exception) -> SystemExit:
    import os
    prof = os.environ.get("AWS_PROFILE", "")
    꼬리 = f" --profile {prof}" if prof else ""
    if type(e).__name__ in _만료 or "expired" in str(e).lower():
        return SystemExit(f"AWS 자격증명이 만료됐다 — 다시 들어간다\n"
                          f"    친다 : aws login{꼬리}\n"
                          f"    까닭 : {type(e).__name__}")
    return SystemExit(f"AWS Translate 가 거절했다 — {type(e).__name__}\n    {e}")


# ── 로컬 모델 — ollama ───────────────────────────────────────
# ★ **표준 라이브러리로 부른다.** ollama 가 양자화 · GPU 적재를 맡으므로 이 저장소에 torch 가 들어오지
#   않는다. 1660 Ti(6GB)에 TranslateGemma 4B Q4_K_M(3.3GB)이 온전히 올라간다.
# ★ 프롬프트는 ollama 의 모델 페이지가 적은 틀을 그대로 쓴다(2026-09-22 확인). 틀을 바꾸면 다른 실험이다.
OLLAMA_URL = "http://127.0.0.1:11434"
TRANSLATEGEMMA_PROMPT = (
    "You are a professional English (en) to Korean (ko) translator. Your goal is to accurately convey the "
    "meaning and nuances of the original English text while adhering to Korean grammar, vocabulary, and "
    "cultural sensitivities.\nProduce only the Korean translation, without any additional explanations or "
    "commentary. Please translate the following English text into Korean:\n\n\n{text}")
# ★ H-019 의 처치 — 문체를 프롬프트가 지시한다(DECISIONS §27). H-001 에서 자리표시가 든 의문문 6줄이
#   해요체(`… 충족할까요?`)로 끝났다. 틀은 위와 같고 **한 문단만 더한다** — 한 번에 한 가지만 바꾼다.
TRANSLATEGEMMA_PROMPT_HAPSYO = TRANSLATEGEMMA_PROMPT.replace(
    "Please translate the following English text into Korean:",
    "Write every sentence in the Korean formal-polite style (합쇼체): statements end with -ㅂ니다/습니다 and "
    "questions end with -ㅂ니까/습니까. Never use -요 endings.\nPlease translate the following English text "
    "into Korean:")
# 결정성 — thoth 에서 temperature 0 만으로는 모자랐다(thoth DECISIONS §35 · §65). seed 를 함께 준다.
DECODING = {"temperature": 0, "seed": 42, "num_predict": 512}


# 백엔드 이름 → ollama 가 서는 모델. 재현 조건이 GPU 적재를 적을 때 본다(DECISIONS §45)
OLLAMA_OF: dict[str, str] = {}


# ★ 사고 모드를 켜는 모델(Qwen3 류)은 `<think>…</think>` 를 앞에 붙인다. 번역문만 받아야 하므로 `think: false`
#   로 끄고, 그래도 오면 **여기서 벗긴다** — 검사가 사고 과정을 번역으로 세지 않게(DECISIONS §47).
THINK = re.compile(r"<think>.*?</think>\s*", re.S)


# ★ 한 줄을 기다리는 한도. **카드에 안 올라가는 모델은 느리다** — 12B Q4(8GB)를 6GB 카드에서 돌리면
#   절반이 CPU 에 있고 한 줄이 10 분을 넘는다. 2026-09-25, 600 초에 걸려 16 분 돌던 판이 통째로 죽었다.
#   숫자를 코드에 박지 않는다 — 기계마다 다르다(DECISIONS §82).
TIMEOUT = 600


def _timeout() -> int:
    import os
    v = os.environ.get("OLLAMA_TIMEOUT", "").strip()
    return int(v) if v.isdigit() and int(v) > 0 else TIMEOUT


# ★ 잠깐 넘어진 것과 진짜 고장은 다르다(DECISIONS §89). 2026-09-27, 600 줄 판이 540 줄에서 터널의
#   `Bad Gateway` 하나로 통째로 날아갔다. 20 분이 사라졌고 모델은 멀쩡했다.
#   **시간 초과는 다시 묻지 않는다** — 그것은 느리다는 말이고, 다시 물으면 그만큼 또 기다린다(§82).
_잠깐 = {429, 500, 502, 503, 504}
_시도 = 3


def _늦다(model: str, 초: int, 무엇: str) -> SystemExit:
    return SystemExit(f"{model} 이 {초}초 안에 답하지 않았다\n"
                      f"    올린다 : OLLAMA_TIMEOUT=2400 uv run python -m seshat.evaluate …\n"
                      f"    까닭   : 카드에 다 안 올라간 모델은 느리다(`ollama ps` 의 CPU/GPU 를 본다)\n"
                      f"    막힌 줄 : {무엇[:80]}")


def _ask(req, model: str, 무엇: str = ""):
    """ollama 에 묻고 답을 돌려준다. 꺼졌거나 늦으면 **한 줄로** 말한다(DECISIONS §51 · §82 · §89).

    ★ 종전에는 `URLError` 가 40줄 역추적으로 올라왔다. 무엇을 해야 하는지는 그 안에 없다 — 리전 때와
      같다(§36). 원인을 아는 자리에서 말한다.
    ★ **일시적인 고장은 다시 묻는다** — 게이트웨이 오류 · 끊긴 연결. 세 번까지, 3 · 6 초 쉬고.
      빌린 GPU 로 재는 길(§84)은 터널을 하나 더 지나므로 이런 일이 난다.
    """
    import http.client
    import json as _json
    import time
    import urllib.error
    import urllib.request
    초 = _timeout()
    for 번째 in range(_시도):
        마지막 = 번째 == _시도 - 1
        try:
            with urllib.request.urlopen(req, timeout=초) as r:
                return _json.loads(r.read())
        except TimeoutError:
            raise _늦다(model, 초, 무엇) from None
        except urllib.error.HTTPError as e:
            if e.code not in _잠깐 or 마지막:
                raise SystemExit(f"{model} 이 {e.code} 로 거절했다 — {req.full_url}\n"
                                 f"    막힌 줄 : {무엇[:80]}") from None
            까닭 = f"{e.code}"
        except (ConnectionResetError, http.client.RemoteDisconnected) as e:
            if 마지막:
                raise SystemExit(f"{model} 과의 연결이 {_시도}번 다 끊겼다 — {req.full_url}\n"
                                 f"    까닭 : {type(e).__name__}") from None
            까닭 = "연결이 끊겼다"
        except urllib.error.URLError as e:
            if isinstance(getattr(e, "reason", None), TimeoutError):
                raise _늦다(model, 초, 무엇) from None
            raise SystemExit(f"ollama 에 닿지 못한다 — {req.full_url}\n"
                             f"    띄운다 : ollama serve &  (그 뒤 ollama pull {model})\n"
                             f"    까닭   : {e.reason}") from None
        쉼 = 3 * 2 ** 번째
        print(f"  ※ {까닭} — {쉼}초 쉬고 다시 묻는다({번째 + 2}/{_시도})", file=_sys.stderr, flush=True)
        time.sleep(쉼)
    raise SystemExit(f"{model} 에 {_시도}번 물었으나 못 받았다 — {req.full_url}")


def ollama(model: str, prompt: str, extra: dict | None = None):
    def call(texts: list[str], terms: dict[str, str]) -> list[str]:
        import json as _json
        import os
        import urllib.request
        url = os.environ.get("OLLAMA_URL", OLLAMA_URL).rstrip("/") + "/api/generate"
        out = []
        for t in texts:
            body = _json.dumps({"model": model, "prompt": prompt.format(text=t), "stream": False,
                                "options": DECODING, **(extra or {})}).encode("utf-8")
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            out.append(THINK.sub("", _ask(req, model, t)["response"]).strip())
        return out
    return call


# ★ **범용 지시 모델은 배선이 다르다**(DECISIONS §48). 번역 전용 모델(TranslateGemma)은 시키면 번역만 주는데,
#   범용 모델은 사고 과정과 설명을 함께 준다 — 2026-09-23 Qwen3 4B 가 영어 사고문을 번역문 자리에 뱉었다.
#   채팅 API 로 체계 지시를 따로 주고, 사고를 끄고, 출력만 받는다. **이것은 실험 변수가 아니라 배선이다** —
#   범용 후보는 전부 이 하나를 같이 쓴다. 그래야 모델끼리는 여전히 공정하다.
GENERIC_SYSTEM = (
    "You are a professional English-to-Korean translator. Translate the user's text into Korean.\n"
    "Output ONLY the Korean translation — no explanations, no reasoning, no romanization, no alternatives, "
    "no quotation marks around the whole sentence. Keep every placeholder token exactly as it appears.")


# ★ Qwen3 는 `/no_think` 를 사용자 말끝에 붙여 사고를 끈다(모델 카드). `think: false` 만으로는 안 꺼졌다
#   (2026-09-23 · ollama 0.34 · qwen3:4b — 사고문이 그대로 왔다). 둘을 함께 보낸다(DECISIONS §49).
NO_THINK = "\n/no_think"


def ollama_chat(model: str, system: str, extra: dict | None = None, suffix: str = ""):
    """`/api/chat` — 체계 지시를 따로 싣는다. 사고 모드는 `think: false` 와 말끝 스위치로 끈다."""
    def call(texts: list[str], terms: dict[str, str]) -> list[str]:
        import json as _json
        import os
        import urllib.request
        url = os.environ.get("OLLAMA_URL", OLLAMA_URL).rstrip("/") + "/api/chat"
        out = []
        for t in texts:
            body = _json.dumps({"model": model, "stream": False, "options": DECODING,
                                "messages": [{"role": "system", "content": system},
                                             {"role": "user", "content": t + suffix}],
                                **(extra or {})}).encode("utf-8")
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            out.append(THINK.sub("", _ask(req, model, t)["message"]["content"]).strip())
        return out
    return call


def ollama_chat_ref(model: str, system: str, cap: int = 12, extra: dict | None = None,
                    fence: bool = False, ui: bool = False):
    """줄마다 **그 줄의 용어집**을 체계 지시에 붙여 부른다(DECISIONS §134 · `seshat/glossary.py`).

    ★ `ollama_chat` 과 배선이 같고 **체계 지시만 줄마다 다르다.** 달라진 것이 하나여야 무엇이
      효과인지 가른다 — 모델도 복호화도 그대로다.
    ★ 사전이 빈 줄은 **원래 지시 그대로** 간다. 빈 사전을 실으면 모델이 없는 것을 찾는다.
    ★ `fence` — 사전 뒤에 **어디까지가 사전의 일인지**를 붙인다(DECISIONS §140). 목록만 주면
      모델이 사전에 없는 식별자까지 옮긴다.
    """
    def call(texts: list[str], terms: dict[str, str]) -> list[str]:
        import json as _json
        import os
        import urllib.request

        from . import glossary, ontology
        onto = ontology.load()
        url = os.environ.get("OLLAMA_URL", OLLAMA_URL).rstrip("/") + "/api/chat"
        out = []
        for t in texts:
            토막 = glossary.block(glossary.for_line(onto, t, cap), fence=fence, ui=ui)
            body = _json.dumps({"model": model, "stream": False, "options": DECODING,
                                "messages": [{"role": "system",
                                              "content": system + ("\n\n" + 토막 if 토막 else "")},
                                             {"role": "user", "content": t}],
                                **(extra or {})}).encode("utf-8")
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            out.append(THINK.sub("", _ask(req, model, t)["message"]["content"]).strip())
        return out
    return call


def nbest(model: str, system: str, n: int = 8, temp: float = 0.8, seed0: int = 101):
    """같은 모델을 **N 번** 부르고 MBR 로 하나를 고른다(DECISIONS §133 · `seshat/mbr.py`).

    ★ **온도를 올려야 후보가 갈린다.** `DECODING` 은 온도 0 이라 여덟 번 불러도 같은 문장이 여덟 개다.
      `temp` 와 **seed 를 후보마다 다르게** 준다 — 온도만 올리고 seed 를 고정하면 ollama 가 같은 것을 준다.
    ★ **N 배 느리다.** 600 줄 × 8 이면 이 기계에서 한 시간이 넘는다. 값은 0 이다 — 시간으로 품질을 산다.
    ★ 자리표시 안쪽에 둔다 — `with_placeholders(nbest(...))`. 후보들이 같은 `⟦Tn⟧` 를 들고 있어
      고르기가 이름에 흔들리지 않는다.
    """
    from . import mbr
    arms = [ollama_chat(model, system, {"options": {**DECODING, "temperature": temp, "seed": seed0 + i}})
            for i in range(n)]

    def call(texts: list[str], terms: dict[str, str]) -> list[str]:
        판 = [f(texts, terms) for f in arms]            # n × 줄
        return [mbr.pick([p[i] for p in 판]) for i in range(len(texts))]
    return call


# ★ **고친 줄만 다시 묻는다**(H-034 · DECISIONS §59 · §60). 되돌리기가 `missing` 을 돌려주므로 이름이
#   사라진 줄은 도구가 **안다**. 고치는 판은 **자리표시를 빼고 원문 그대로** 묻는다 — 버려지는 것이
#   `of ⟦T⟧` 라는 모양 자체이므로, 온도를 흔드는 것이 아니라 그 모양을 없앤다(§60).
#   받는 조건은 하나다 : 지켜야 할 이름이 **전부 글자 그대로** 답에 있는가.
REPAIR = {"temperature": 0.4, "seed": 43, "num_predict": 512}
REPAIR_ARMS: set[str] = set()
# 처치가 일했는지를 결과가 말한다 — 안 걸린 것과 걸렸는데 실패한 것은 다르다(DECISIONS §60)
REPAIR_STATS: dict[str, int] = {"tried": 0, "fixed": 0}


def with_placeholders(inner: Backend, repair: tuple[Backend, ...] = ()) -> Backend:
    """H-001 의 처치군 — 영어로 남을 이름을 `⟦Tn⟧` 로 빼고 번역한 뒤 되돌린다(`seshat/terms.py`).

    ★ `repair` 는 차례로 시도하는 판들이다. **원문을 그대로 준다** — 자리표시 없이.
    ★ 다 실패하면 **첫 답을 그대로 둔다** — 없는 이름을 지어 넣지 않는다. 사라진 것은 사라진 것으로 재야
      `keep` 이 진실을 말한다.
    """
    def call(texts: list[str], terms_: dict[str, str]) -> list[str]:
        from . import ontology, terms
        onto = ontology.load()
        masked = [terms.mask(onto, t) for t in texts]
        outs = inner([m for m, _ in masked], terms_)
        fixed = []
        for t, o, (_, slots) in zip(texts, outs, masked):
            ko, missing = terms.unmask(o, slots)
            if missing and repair:
                REPAIR_STATS["tried"] += 1
                names = [sl["text"] for sl in slots.values()]
                for ask in repair:
                    cand = ask([t], terms_)[0]
                    if all(n in cand for n in names):
                        ko = cand
                        REPAIR_STATS["fixed"] += 1
                        break
            fixed.append(ko)
        return fixed
    return call


def with_terms(inner: Backend) -> Backend:
    """H-033 의 처치 — 출력의 관측된 오역을 공식 표기로 바꾼다(`seshat/terms.py` · DECISIONS §56).

    ★ **맨 뒤에 선다.** 이름을 되돌리고 종결을 고친 뒤의 한국어를 본다 — 자리표시 안의 글자를 건드리지 않는다.
    """
    def run(texts: list[str], terms_: dict) -> list[str]:
        from . import ontology, terms
        onto = ontology.load()
        # ★ 줄마다 그 줄의 원문을 함께 준다 — 흔한 말이 휩쓸리지 않게(DECISIONS §67)
        return [terms.fix_terms(onto, o, src=t)[0] for t, o in zip(texts, inner(texts, terms_))]
    return run


def with_endings(inner: Backend) -> Backend:
    """H-023 의 처치 — 해요체 의문 종결을 합쇼체로 고친다(`seshat/endings.py` · DECISIONS §33).

    ★ **프롬프트가 못 하는 것을 검사기가 한다.** 문체 지시는 종결을 못 바꿨고(H-019 기각) 결정적 후처리는
      style 을 0.93 → 1.00 으로 올렸다. 다른 지표는 그대로다 — 공짜로 얻는 자리다.
    """
    def call(texts: list[str], terms_: dict[str, str]) -> list[str]:
        from . import endings
        return [endings.normalize(o) for o in inner(texts, terms_)]
    return call


_tg = ollama("translategemma:4b", TRANSLATEGEMMA_PROMPT)
# ★ **비교 전용이다**(H-029 · DECISIONS §44). EXAONE 3.5 는 비상업(NC)이고 출력을 다른 모델 학습에 못 쓴다 —
#   서빙에도 증류에도 못 쓴다. 연구 목적 평가는 라이선스가 명시적으로 허락한다. 한국어에 강한 모델이 용어에서
#   TranslateGemma 4B 를 넘는지만 본다. 같은 지시문을 쓴다 — 바꾸는 것은 모델 하나다
_exaone = ollama("exaone3.5:7.8b", TRANSLATEGEMMA_PROMPT)
# ★ Qwen3 는 Apache-2.0 이라 서빙도 증류도 열려 있다(H-032 · 라이선스 대장). **사고 모드를 끈다** —
#   켜 두면 번역 앞에 `<think>` 가 붙고 느려진다. 같은 지시문을 쓴다 — 바꾸는 것은 모델 하나다
# ★ Qwen3 의 마지막 시도 — 체계 지시에도 `/no_think` 를 넣는다(모델 카드는 체계 · 사용자 어느 쪽이든 된다고
#   적는다). 이래도 사고문이 오면 후보에서 뺀다. **배선에 세 판을 넘게 쓰지 않는다**(DECISIONS §50).
_qwen8 = ollama_chat("qwen3:8b", GENERIC_SYSTEM + NO_THINK, {"think": False}, NO_THINK)
_qwen4 = ollama_chat("qwen3:4b", GENERIC_SYSTEM + NO_THINK, {"think": False}, NO_THINK)
# ★ Gemma 3 는 사고 모드가 없다 — 범용 지시 모델이지만 이 문제를 처음부터 안 만든다. Gemma 약관이라 서빙도
#   증류도 되고, 학생은 약관을 상속한다(§44).
_gemma3 = ollama_chat("gemma3:4b", GENERIC_SYSTEM)
# 고치는 판 — 배선은 같고 복호화만 다르다. 모델도 체계 지시도 그대로여야 무엇이 효과인지 가른다
# ★ 12B — 6GB 카드에는 안 올라간다. ollama 가 남는 층을 CPU 로 내린다(느리다). 결과 머리줄의
#   `gpu_share` 가 얼마나 올라갔는지 적는다 — 속도를 읽을 때 그 숫자와 같이 본다(DECISIONS §79)
_gemma3_12b = ollama_chat("gemma3:12b", GENERIC_SYSTEM)
_gemma3_12b_repair = (ollama_chat("gemma3:12b", GENERIC_SYSTEM),
                      ollama_chat("gemma3:12b", GENERIC_SYSTEM, {"options": REPAIR}))
_gemma3_repair = (ollama_chat("gemma3:4b", GENERIC_SYSTEM),                    # 원문 · 온도 0
                  ollama_chat("gemma3:4b", GENERIC_SYSTEM, {"options": REPAIR}))  # 원문 · 온도 0.4
_tg_hapsyo = ollama("translategemma:4b", TRANSLATEGEMMA_PROMPT_HAPSYO)

REGISTRY: dict[str, tuple[Backend, str]] = {
    # 이름 → (함수, /health 가 말할 모델명)
    "echo": (echo, "seshat-echo"),
    "aws-translate": (aws_translate, "aws-translate"),
    "translategemma-4b": (_tg, "translategemma:4b"),
    "translategemma-4b+ph": (with_placeholders(_tg), "translategemma:4b+ph"),
    "translategemma-4b+ph+style": (with_placeholders(_tg_hapsyo), "translategemma:4b+ph+style"),
    # ★ 지금의 후보다 — 자리표시(H-016) + 종결 정규화(H-023). thoth 에 끼운다면 이것이다
    "translategemma-4b+ph+endings": (with_endings(with_placeholders(_tg)), "translategemma:4b+ph+endings"),
    # ★ **남의 엔진에 이 저장소의 후처리를 얹는다**(H-028 · DECISIONS §41). 기준선이 이름을 44% 잃는 것을 이 기계가
    #   메우는가를 잰다. 서빙 후보가 아니다 — 과금이고, 무엇이 누구 몫인지 가르는 자다
    "aws-translate+ph+endings": (with_endings(with_placeholders(aws_translate)), "aws-translate+ph+endings"),
    "exaone-3.5-7.8b+ph+endings": (with_endings(with_placeholders(_exaone)), "exaone3.5:7.8b+ph+endings"),
    "qwen3-8b+ph+endings": (with_endings(with_placeholders(_qwen8)), "qwen3:8b+ph+endings"),
    "qwen3-4b+ph+endings": (with_endings(with_placeholders(_qwen4)), "qwen3:4b+ph+endings"),
    # ★ **범용 성적표에는 종결 정규화를 안 얹는다**(DECISIONS §63). 합쇼체는 thoth 의 도메인 요구이지
    #   번역 품질이 아니다 — 정답 문장이 있는 셋에서 문체를 강제하면 맞는 문장을 정답에서 멀어지게 한다
    "gemma3-4b": (_gemma3, "gemma3:4b"),
    "gemma3-4b+ph+retry": (with_placeholders(_gemma3, repair=_gemma3_repair), "gemma3:4b+ph+retry"),
    "gemma3-12b": (_gemma3_12b, "gemma3:12b"),
    "gemma3-12b+ph+retry": (with_placeholders(_gemma3_12b, repair=_gemma3_12b_repair), "gemma3:12b+ph+retry"),
    "gemma3-12b+ph+retry+endings+terms": (
        with_terms(with_endings(with_placeholders(_gemma3_12b, repair=_gemma3_12b_repair))),
        "gemma3:12b+ph+retry+endings+terms"),
    "gemma3-4b+ph+endings": (with_endings(with_placeholders(_gemma3)), "gemma3:4b+ph+endings"),
    "gemma3-4b+ph+endings+terms": (with_terms(with_endings(with_placeholders(_gemma3))),
                                   "gemma3:4b+ph+endings+terms"),
    "gemma3-4b+ph+retry+endings+terms": (
        with_terms(with_endings(with_placeholders(_gemma3, repair=_gemma3_repair))),
        "gemma3:4b+ph+retry+endings+terms"),
    "aws-translate+ph+endings+terms": (with_terms(with_endings(with_placeholders(aws_translate))),
                                       "aws-translate+ph+endings+terms"),
    # ★ **학습 없이 시간으로 품질을 산다**(DECISIONS §133). 서빙 후보와 같은 후처리를 얹고
    #   안쪽만 N-best + MBR 로 바꾼다 — 그래야 달라진 것이 고르기 하나다
    "gemma3-4b+ph+mbr8+endings+terms": (
        with_terms(with_endings(with_placeholders(nbest("gemma3:4b", GENERIC_SYSTEM, n=8)))),
        "gemma3:4b+ph+mbr8+endings+terms"),
    "gemma3-4b+ph+mbr4+endings+terms": (
        with_terms(with_endings(with_placeholders(nbest("gemma3:4b", GENERIC_SYSTEM, n=4)))),
        "gemma3:4b+ph+mbr4+endings+terms"),
    # ★ **줄마다 그 줄의 용어집을 미리 준다**(#16 · DECISIONS §134). 지금까지 모델은 공식 표기를
    #   한 번도 못 봤다 — 자리표시는 감추고 `+terms` 는 틀린 뒤에 고친다. 둘을 가르려고 팔이 둘이다
    "gemma3-4b+ph+gloss+endings": (
        with_endings(with_placeholders(ollama_chat_ref("gemma3:4b", GENERIC_SYSTEM))),
        "gemma3:4b+ph+gloss+endings"),
    "gemma3-4b+ph+gloss+endings+terms": (
        with_terms(with_endings(with_placeholders(ollama_chat_ref("gemma3:4b", GENERIC_SYSTEM)))),
        "gemma3:4b+ph+gloss+endings+terms"),
    # ★ **사전에 울타리를 세운 팔**(DECISIONS §140). `+gloss` 가 `term_off` 를 0.886 → 0.973 으로
    #   올리면서 `lit` 을 0.803 → 0.732 로 떨어뜨렸고, 잃은 것의 9/11 은 **사전에 없는 식별자**였다.
    #   달라진 것은 사전 토막 끝의 한 줄뿐이다 — 그것이 원인이면 `lit` 이 돌아오고 `term_off` 는 남는다
    "gemma3-4b+ph+gloss2+endings": (
        with_endings(with_placeholders(ollama_chat_ref("gemma3:4b", GENERIC_SYSTEM, fence=True))),
        "gemma3:4b+ph+gloss2+endings"),
    # ★ **서빙 후보 배선에 울타리 사전을 얹은 팔**(H-059). 기록판 팔과 **`gloss2` 하나만 다르다** —
    #   `+retry` 도 `+endings` 도 `+terms` 도 그대로 둔다. 고치는 판(`_gemma3_repair`)은 사전 없이
    #   부른다 — 기록판 팔과 같게 두어야 달라진 것이 하나가 된다(DECISIONS §134)
    # ★ **울타리에 콘솔 라벨 한 갈래를 더한 팔**(H-060). `gloss2` 와 **문장 하나만** 다르다
    "gemma3-4b+ph+gloss3+endings": (
        with_endings(with_placeholders(
            ollama_chat_ref("gemma3:4b", GENERIC_SYSTEM, fence=True, ui=True))),
        "gemma3:4b+ph+gloss3+endings"),
    "gemma3-4b+ph+gloss2+retry+endings+terms": (
        with_terms(with_endings(with_placeholders(
            ollama_chat_ref("gemma3:4b", GENERIC_SYSTEM, fence=True), repair=_gemma3_repair))),
        "gemma3:4b+ph+gloss2+retry+endings+terms"),
}

# ★ 이름으로 짐작하지 않는다 — 어느 백엔드가 ollama 위에 서는지 여기 적는다. 종전에는 `translategemma` 로
#   시작하는 이름만 GPU 적재를 적었고, EXAONE 을 재고 나서야 그 줄이 비어 있는 것을 봤다(DECISIONS §45).
OLLAMA_OF.update({"translategemma-4b": "translategemma:4b", "translategemma-4b+ph": "translategemma:4b",
                  "translategemma-4b+ph+style": "translategemma:4b",
                  "translategemma-4b+ph+endings": "translategemma:4b",
                  "exaone-3.5-7.8b+ph+endings": "exaone3.5:7.8b",
                  "qwen3-8b+ph+endings": "qwen3:8b", "qwen3-4b+ph+endings": "qwen3:4b",
                  "gemma3-4b+ph+endings": "gemma3:4b",
                  "gemma3-4b+ph+endings+terms": "gemma3:4b",
                  "gemma3-4b+ph+retry+endings+terms": "gemma3:4b",
                  "gemma3-4b": "gemma3:4b", "gemma3-4b+ph+retry": "gemma3:4b",
                  "gemma3-12b": "gemma3:12b", "gemma3-12b+ph+retry": "gemma3:12b",
                  "gemma3-12b+ph+retry+endings+terms": "gemma3:12b",
                  "gemma3-4b+ph+mbr8+endings+terms": "gemma3:4b",
                  "gemma3-4b+ph+mbr4+endings+terms": "gemma3:4b",
                  "gemma3-4b+ph+gloss+endings": "gemma3:4b",
                  "gemma3-4b+ph+gloss+endings+terms": "gemma3:4b",
                  "gemma3-4b+ph+gloss2+endings": "gemma3:4b",
                  "gemma3-4b+ph+gloss2+retry+endings+terms": "gemma3:4b",
                  "gemma3-4b+ph+gloss3+endings": "gemma3:4b"})

# ★ **어느 ollama 모델이 어느 가중치인가.** `from_pretrained` 를 거치지 않는 호출은 라이선스 검사의
#   정규식이 보지 못한다. 선언을 검사가 대장과 대조한다(DECISIONS §14).
WEIGHTS_OF_MODEL: dict[str, str] = {
    "gemma3:12b": "google/gemma-3-12b-it",
    "translategemma:4b": "google/translategemma-4b-it",
    "exaone3.5:7.8b": "LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct",
    "qwen3:8b": "Qwen/Qwen3-8B",
    "qwen3:4b": "Qwen/Qwen3-4B",
    "gemma3:4b": "google/gemma-3-4b-it",
}

# ★ **팔마다 적지 않는다 — 배선에서 끌어온다**(DECISIONS §57). 종전에는 팔 이름을 키로 손으로 적었고,
#   `+terms` 팔을 더한 날 그 줄을 빠뜨려 결과 파일에 `weights: null` 이 실렸다. 재현할 수 없는 결과다.
#   목록은 `OLLAMA_OF` 하나이고 나머지는 거기서 나온다 — 빠뜨릴 자리가 없다.
WEIGHTS: dict[str, str] = {arm: WEIGHTS_OF_MODEL[m] for arm, m in OLLAMA_OF.items()}

# 결과 파일 머리줄에 싣는 디코딩 조건
DECODING_OF: dict[str, dict] = {arm: DECODING for arm in OLLAMA_OF}
# ★ **N-best 는 온도 0 이 아니다.** 여기 안 적으면 머리줄이 「온도 0」 이라고 거짓말하고, 그 조건으로는
#   되풀이해도 다른 수가 나온다(DECISIONS §57 · §133). 팔마다 후보 수 · 온도 · 첫 seed 를 적는다
MBR_ARMS: dict[str, int] = {"gemma3-4b+ph+mbr8+endings+terms": 8, "gemma3-4b+ph+mbr4+endings+terms": 4}
DECODING_OF.update({arm: {"temperature": 0.8, "seed0": 101, "num_predict": 512, "nbest": n}
                    for arm, n in MBR_ARMS.items()})

# ★ 고치는 판을 쓰는 팔은 그 조건도 머리줄에 싣는다 — 안 적으면 되풀이할 수 없다(DECISIONS §57)
REPAIR_ARMS.update({"gemma3-4b+ph+retry+endings+terms", "gemma3-4b+ph+retry",
                    "gemma3-4b+ph+gloss2+retry+endings+terms",
                    "gemma3-12b+ph+retry", "gemma3-12b+ph+retry+endings+terms"})
for _arm in REPAIR_ARMS:
    DECODING_OF[_arm] = {**DECODING, "repair": REPAIR}


# ★ 서빙하지 않는 백엔드. 기준선으로만 잰다 — thoth 에 끼우는 자리가 아니다.
# ★ 여기에는 **서빙하지 않는 백엔드**가 전부 들어온다 — 과금이라서(AWS)든 라이선스라서(EXAONE · §44)든.
BASELINE_ONLY = {"aws-translate", "aws-translate+ph+endings", "aws-translate+ph+endings+terms",
                 "exaone-3.5-7.8b+ph+endings"}

# ★ **돈이 드는 백엔드의 값이다**(DECISIONS §35). 100만 자에 USD. `evaluate` 가 재기 전에 견적을 내고
#   `--max-usd` 를 넘으면 부르지 않는다 — 가설의 상한을 사람이 지키는 것이 아니라 도구가 지킨다.
PRICE_PER_MCHAR: dict[str, float] = {"aws-translate": 15.0, "aws-translate+ph+endings": 15.0,
                                     "aws-translate+ph+endings+terms": 15.0}

# ★ **무료는 선언한다**(DECISIONS §62). 표에 없는 이름이 0 원으로 떨어지면 상한이 아무것도 안 막는다.
#   여기 없고 값표에도 없는 백엔드는 `evaluate` 가 부르기 전에 멈춘다 — 모르는 값은 공짜가 아니다.
#   빈 이름("")은 `--url` 로 남의 서버를 재는 길이다 — 그 값은 그 서버를 띄운 쪽이 안다.
FREE: set[str] = {"", "echo", *OLLAMA_OF}


def get(name: str) -> tuple[Backend, str]:
    if name not in REGISTRY:
        raise SystemExit(f"모르는 백엔드 {name} — {sorted(REGISTRY)}")
    return REGISTRY[name]
