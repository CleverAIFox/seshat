"""번역 백엔드. 서버는 이것만 부른다.

★ **백엔드는 `(texts, terms) -> translations` 하나다.** 모델이 CTranslate2 든
  llama.cpp 든 transformers 든 서버 · 평가 · 계약 검사는 모른다. 새 모델은 여기에
  함수 하나를 더한다.

★ **무거운 의존성은 함수 안에서 import 한다.** `echo` 로 계약 검사를 도는 CI 가
  torch 를 받으면 안 된다.
"""
from __future__ import annotations

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
    ★ 과금이다 — 100만 자에 USD 15(2026-09 인용, thoth MASTER §7). FLORES+ devtest 한 판이 약 13만 자다.
    """
    if client is None:
        import boto3  # 무거운 의존성은 함수 안에서(모듈 머리말)
        client = boto3.client("translate")
    out = []
    for t in texts:
        r = client.translate_text(Text=t, SourceLanguageCode="en", TargetLanguageCode="ko")
        out.append(r["TranslatedText"])
    return out


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


def ollama(model: str, prompt: str):
    def call(texts: list[str], terms: dict[str, str]) -> list[str]:
        import json as _json
        import os
        import urllib.request
        url = os.environ.get("OLLAMA_URL", OLLAMA_URL).rstrip("/") + "/api/generate"
        out = []
        for t in texts:
            body = _json.dumps({"model": model, "prompt": prompt.format(text=t), "stream": False,
                                "options": DECODING}).encode("utf-8")
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                out.append(_json.loads(r.read())["response"].strip())
        return out
    return call


def with_placeholders(inner: Backend) -> Backend:
    """H-001 의 처치군 — 영어로 남을 이름을 `⟦Tn⟧` 로 빼고 번역한 뒤 되돌린다(`seshat/terms.py`)."""
    def call(texts: list[str], terms_: dict[str, str]) -> list[str]:
        from . import ontology, terms
        onto = ontology.load()
        masked = [terms.mask(onto, t) for t in texts]
        outs = inner([m for m, _ in masked], terms_)
        return [terms.unmask(o, slots)[0] for o, (_, slots) in zip(outs, masked)]
    return call


_tg = ollama("translategemma:4b", TRANSLATEGEMMA_PROMPT)
_tg_hapsyo = ollama("translategemma:4b", TRANSLATEGEMMA_PROMPT_HAPSYO)

REGISTRY: dict[str, tuple[Backend, str]] = {
    # 이름 → (함수, /health 가 말할 모델명)
    "echo": (echo, "seshat-echo"),
    "aws-translate": (aws_translate, "aws-translate"),
    "translategemma-4b": (_tg, "translategemma:4b"),
    "translategemma-4b+ph": (with_placeholders(_tg), "translategemma:4b+ph"),
    "translategemma-4b+ph+style": (with_placeholders(_tg_hapsyo), "translategemma:4b+ph+style"),
}

# ★ **백엔드가 어떤 가중치를 부르는지 선언한다.** `from_pretrained` 를 거치지 않는 호출(ollama)은
#   라이선스 검사의 정규식이 보지 못한다. 선언을 검사가 대장과 대조한다(DECISIONS §14).
WEIGHTS: dict[str, str] = {
    "translategemma-4b": "google/translategemma-4b-it",
    "translategemma-4b+ph": "google/translategemma-4b-it",
    "translategemma-4b+ph+style": "google/translategemma-4b-it",
}

# 결과 파일 머리줄에 싣는 디코딩 조건
DECODING_OF: dict[str, dict] = {"translategemma-4b": DECODING, "translategemma-4b+ph": DECODING,
                                "translategemma-4b+ph+style": DECODING}

# ★ 서빙하지 않는 백엔드. 기준선으로만 잰다 — thoth 에 끼우는 자리가 아니다.
BASELINE_ONLY = {"aws-translate"}


def get(name: str) -> tuple[Backend, str]:
    if name not in REGISTRY:
        raise SystemExit(f"모르는 백엔드 {name} — {sorted(REGISTRY)}")
    return REGISTRY[name]
