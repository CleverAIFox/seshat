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


REGISTRY: dict[str, tuple[Backend, str]] = {
    # 이름 → (함수, /health 가 말할 모델명)
    "echo": (echo, "seshat-echo"),
    "aws-translate": (aws_translate, "aws-translate"),
}

# ★ 서빙하지 않는 백엔드. 기준선으로만 잰다 — thoth 에 끼우는 자리가 아니다.
BASELINE_ONLY = {"aws-translate"}


def get(name: str) -> tuple[Backend, str]:
    if name not in REGISTRY:
        raise SystemExit(f"모르는 백엔드 {name} — {sorted(REGISTRY)}")
    return REGISTRY[name]
