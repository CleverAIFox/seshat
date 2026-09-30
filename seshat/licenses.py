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
    # ★ Apache-2.0 — 상업도 증류도 조건 없이 열린다. 학생이 약관을 상속하지 않는 유일한 후보다(H-032).
    "Qwen/Qwen3-8B": ("Apache-2.0", "yes", "yes", "huggingface.co/Qwen/Qwen3-8B · 2026-09-23"),
    "Qwen/Qwen3-4B": ("Apache-2.0", "yes", "yes", "huggingface.co/Qwen/Qwen3-4B · 2026-09-23"),
    # ★ TranslateGemma 와 같은 약관이다 — 교사로 쓸 수 있고 학생이 Gemma 약관을 상속한다(§44).
    "google/gemma-3-4b-it": ("Gemma Terms of Use", "yes", "yes",
                             "ai.google.dev/gemma/terms · ollama.com/library/gemma3 · 2026-09-23"),
    "google/gemma-3-12b-it": ("Gemma Terms of Use", "yes", "yes",
                              "ai.google.dev/gemma/terms · ollama.com/library/gemma3 · 2026-09-25"),
    # ★ **가중치가 아니라 API 다.** 그래도 여기 올린다 — 이 대장이 묻는 것은 「출력을 학생 학습에 쓸 수
    #   있는가」 이고 그 물음에는 API 도 답해야 한다(DECISIONS §130). thoth 배포본이 이것으로 돈다.
    # ★ **교사 가부는 `unknown` 이다.** AWS Service Terms §50(Bedrock)의 원문을 못 읽었다 —
    #   `aws.amazon.com/service-terms` 한 장이 너무 커서 도구가 20절쯤에서 끊고, 컨테이너의 curl 은
    #   프록시가 막는다. 확인된 것은 **AWS 쪽**이 고객 입출력으로 자사 모델을 학습하지 않는다는 것뿐이고,
    #   **고객이 출력으로 학습해도 되는가**는 그 문서에 없다. **모르면 못 쓴다**(§6 · §44).
    # ── 자(QE 지표)의 가중치 ─────────────────────────────────────────────────────────
    # ★ **자도 가중치다.** 서빙에 안 올리고 교사도 아니지만, 그 점수가 **증류셋을 거른다**(#18) —
    #   학생은 이 자가 고른 줄로 배운다. 그러므로 **교사 가부를 묻는 것이 맞다**(DECISIONS §242).
    # ★ Apache-2.0 · 문 없음. mT5 기반이고 참조 있는 쪽과 **참조 없는 쪽(QE)을 한 모델이 한다** —
    #   `d002` 에는 정답이 없으므로 이 저장소가 쓸 수 있는 것은 QE 쪽뿐이다.
    #   ⚠ **영→한으로 맞춰진 자가 아니다** — WMT'15–22 의 DA · MQM 으로 미세조정했고 논문이 든
    #   평가는 en-de · en-es · ja-zh 다. **그래서 H-084 가 사람 라벨에 대고 잰다**(2026-09-30)
    "google/metricx-24-hybrid-large-v2p6": ("Apache-2.0", "yes", "yes",
                                            "huggingface.co/google/metricx-24-hybrid-large-v2p6 · "
                                            "github.com/google-research/metricx · 2026-09-30"),
    # ★ Apache-2.0 인 **참조 없는 COMET 은 이것 하나다**(Unbabel/COMET LICENSE.models.md).
    #   2020 년 자라 낡았지만 **조건이 없다** — 문턱을 재는 데 값이 있다
    "Unbabel/wmt20-comet-qe-da": ("Apache-2.0", "yes", "yes",
                                  "github.com/Unbabel/COMET/blob/master/LICENSE.models.md · 2026-09-30"),
    # ★ **CC-BY-NC-SA 다 — 비상업.** 성능은 이쪽이 낫다고 알려져 있지만 **서빙할 모델의 학습
    #   데이터를 이 자로 고르는 것은 상업 이용**이다. 비교 실험에서 수를 보는 것과 다르다
    #   (EXAONE 은 약관이 「출력으로 다른 모델을 개선하지 말라」 를 명시하고, 이쪽은 NC 가 그 일을
    #   한다). **교사 가부 `no` 다** — 증류셋을 이 자로 못 거른다
    "Unbabel/wmt22-cometkiwi-da": ("CC-BY-NC-SA 4.0", "no", "no",
                                   "github.com/Unbabel/COMET/blob/master/LICENSE.models.md · 2026-09-30"),
    "Unbabel/wmt23-cometkiwi-da-xl": ("CC-BY-NC-SA 4.0", "no", "no",
                                      "github.com/Unbabel/COMET/blob/master/LICENSE.models.md · 2026-09-30"),
    "Unbabel/XCOMET-XL": ("CC-BY-NC-SA 4.0", "no", "no",
                          "github.com/Unbabel/COMET/blob/master/LICENSE.models.md · 2026-09-30"),
    "amazon.nova-lite-v1:0": ("AWS Service Terms §50(미독) · Bedrock", "yes", "unknown",
                              "aws.amazon.com/bedrock/amazon-models/privacy (AWS 쪽 학습만 답한다) · "
                              "§50 원문 미독 · 2026-09-27"),
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
