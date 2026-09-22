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
}

VALID_COMMERCIAL = {"yes", "no", "unknown"}
