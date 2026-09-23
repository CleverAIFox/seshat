"""모델 가중치 라이선스 대장(DECISIONS §6).

★ **코드가 부르는 가중치는 전부 여기 있어야 한다.** `tools/check_model_licenses.py` 가
  코드에서 가중치 이름을 찾아 이 표와 대조한다. 표에 없으면 빨개지고, 표에 올리려면
  라이선스와 상업 가부를 적어야 한다(하토르 D-0217 의 방식을 옮겼다).

★ **모르면 `unknown` 이다.** 코드 라이선스를 가중치에 넘겨 "된다" 고 적으면 추측이다.
  모델 카드에서 읽은 것만 적고, 읽은 날을 함께 적는다.

축이 둘이다(DECISIONS §44)
  commercial  서빙에 쓸 수 있는가 — "yes" · "no" · "unknown"
  teacher     **출력을 다른 모델 학습에 쓸 수 있는가** — 증류의 교사가 될 수 있는가. 같은 어휘
"""
from __future__ import annotations

# 이름 → (라이선스, 상업 가부, 교사 가부, 확인한 곳 · 날짜)
LEDGER: dict[str, tuple[str, str, str, str]] = {
    # ★ Gemma 약관은 상업 이용을 허락하고 금지 용도 목록을 둔다. ollama 는 Q4_K_M 양자화판을 준다.
    # ★ 교사로 쓸 수 있다 — 「Google claims no rights in Outputs」. 다만 **그 출력으로 학습한 모델은
    #   Model Derivative** 이고(약관이 distillation 을 명시한다) Gemma 약관을 그대로 진다. 학생을 내놓을 때
    #   약관 사본 · 고지 파일 · 사용 제한을 함께 실어야 한다(DECISIONS §44).
    "google/translategemma-4b-it": ("Gemma Terms of Use", "yes", "yes",
                                    "huggingface.co/google/translategemma-4b-it · ai.google.dev/gemma/terms · 2026-09-23"),
    # ★ 비상업(NC)이고 **출력을 다른 모델 학습에 못 쓴다** — 「the Licensee shall not use the Model,
    #   Derivatives or Output to develop or improve other models」(§3.1). 연구 목적의 평가 · 시험은
    #   명시적으로 허락된다(§2.1(a)) — 그래서 비교 실험(H-029)에만 부른다. 서빙도 증류도 안 된다.
    "LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct": ("EXAONE AI Model License Agreement 1.1 - NC", "no", "no",
                                             "huggingface.co/LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct/raw/main/LICENSE · 2026-09-23"),
}

VALID_COMMERCIAL = {"yes", "no", "unknown"}
VALID_TEACHER = VALID_COMMERCIAL

# ★ **쓸 수 없는 가중치.** 상업 가부 이전에 **이 기계가 있는 곳에서 사용 허락이 없다.** 비상업은
#   비교 실험에 쓸 수 있지만(센다), 여기 있는 것은 비교에도 부르지 않는다(DECISIONS §9).
#   접두사 → 사유. 대소문자를 가리지 않는다.
EXCLUDED: dict[str, str] = {
    "tencent/hunyuan-mt": "Tencent HY Community License — 사용 허락 지역이 EU · 영국 · 대한민국을 뺀다 "
                          "(github.com/Tencent-Hunyuan/HY-MT License.txt · 2026-09-22)",
    "tencent/hy-mt": "Tencent HY Community License — 사용 허락 지역이 EU · 영국 · 대한민국을 뺀다 "
                     "(github.com/Tencent-Hunyuan/HY-MT License.txt · 2026-09-22)",
}


def can_teach(name: str) -> bool:
    """출력을 학생 학습에 쓸 수 있는가(DECISIONS §44). 대장에 없으면 거짓이다 — 모르면 못 쓴다."""
    row = LEDGER.get(name)
    return bool(row) and row[2] == "yes"


def excluded(name: str) -> str | None:
    """쓸 수 없는 가중치면 사유를, 아니면 None 을 돌려준다."""
    low = name.lower()
    return next((why for pre, why in EXCLUDED.items() if low.startswith(pre)), None)
