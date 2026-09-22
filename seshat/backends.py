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


REGISTRY: dict[str, tuple[Backend, str]] = {
    # 이름 → (함수, /health 가 말할 모델명)
    "echo": (echo, "seshat-echo"),
}


def get(name: str) -> tuple[Backend, str]:
    if name not in REGISTRY:
        raise SystemExit(f"모르는 백엔드 {name} — {sorted(REGISTRY)}")
    return REGISTRY[name]
