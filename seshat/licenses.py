"""모델 가중치 라이선스 대장(DECISIONS §6).

★ **코드가 부르는 가중치는 전부 여기 있어야 한다.** `tools/check_model_licenses.py` 가
  코드에서 가중치 이름을 찾아 이 표와 대조한다. 표에 없으면 빨개지고, 표에 올리려면
  라이선스와 상업 가부를 적어야 한다(하토르 D-0217 의 방식을 옮겼다).

★ **모르면 `unknown` 이다.** 코드 라이선스를 가중치에 넘겨 "된다" 고 적으면 추측이다.
  모델 카드에서 읽은 것만 적고, 읽은 날을 함께 적는다.

commercial  "yes" · "no" · "unknown"
"""
from __future__ import annotations

# 이름 → (라이선스, 상업 가부, 확인한 곳 · 날짜)
LEDGER: dict[str, tuple[str, str, str]] = {
    # ★ Gemma 약관은 상업 이용을 허락하고 금지 용도 목록을 둔다. ollama 는 Q4_K_M 양자화판을 준다.
    "google/translategemma-4b-it": ("Gemma Terms of Use", "yes",
                                    "huggingface.co/google/translategemma-4b-it · ollama.com/library/translategemma · 2026-09-22"),
}

VALID_COMMERCIAL = {"yes", "no", "unknown"}

# ★ **쓸 수 없는 가중치.** 상업 가부 이전에 **이 기계가 있는 곳에서 사용 허락이 없다.** 비상업은
#   비교 실험에 쓸 수 있지만(센다), 여기 있는 것은 비교에도 부르지 않는다(DECISIONS §9).
#   접두사 → 사유. 대소문자를 가리지 않는다.
EXCLUDED: dict[str, str] = {
    "tencent/hunyuan-mt": "Tencent HY Community License — 사용 허락 지역이 EU · 영국 · 대한민국을 뺀다 "
                          "(github.com/Tencent-Hunyuan/HY-MT License.txt · 2026-09-22)",
    "tencent/hy-mt": "Tencent HY Community License — 사용 허락 지역이 EU · 영국 · 대한민국을 뺀다 "
                     "(github.com/Tencent-Hunyuan/HY-MT License.txt · 2026-09-22)",
}


def excluded(name: str) -> str | None:
    """쓸 수 없는 가중치면 사유를, 아니면 None 을 돌려준다."""
    low = name.lower()
    return next((why for pre, why in EXCLUDED.items() if low.startswith(pre)), None)
