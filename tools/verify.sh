#!/usr/bin/env bash
# 점검 일괄 — **점검 목록의 정본은 이 파일 하나다**(DECISIONS §20). CI 도 이것을 부른다.
#
#   bash tools/verify.sh              전부
#   bash tools/verify.sh --only=pytest  이름이 맞는 단계만. ★ 부분 실행이라 마지막에 실패한다
#
# ★ 전에는 같은 목록이 ci.yml 과 MASTER §5 에 따로 살았다. MASTER 는 「CI 가 같은 다섯을 돈다」 고 적었는데
#   CI 는 일곱을 돌고 있었다 — 두 곳에 살면 한쪽만 고쳐진다. 이제 ci.yml 은 이 파일을 부르기만 한다
#   (`tests/test_workflows.py::test_CI_는_verify_를_부르기만_한다`). 파이어레인 tools/verify.sh 의 축소판이다.
# ★ **실패해도 끝까지 돈다.** 중간에 멈추면 뒤에 무엇이 더 깨졌는지 모른다. 마지막에 표로 보인다.
# ★ **건너뛴 것은 통과가 아니다.** `--only` 로 돈 실행은 마지막 `부분 실행` 단계가 실패시킨다.
# ★ 레이크 검사는 **이 기계에서만** 돈다. CI 에는 SSD 가 없다 — 없는 것이 설계라서 CI 에서는 「CI 밖」 으로
#   찍고 세지 않는다. 이 기계에서 SESHAT_DATA 가 비었으면 실패다(조용한 통과를 막는다).
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
. tools/lib/env.sh; load_env .env

ONLY=""
case "${1:-}" in --only=*) ONLY="${1#--only=}" ;; "") ;; *) echo "모르는 인자: $1" >&2; exit 2 ;; esac

R=$'\033[31m'; G=$'\033[32m'; Y=$'\033[33m'; Z=$'\033[0m'
[ -t 1 ] || { R=""; G=""; Y=""; Z=""; }
NAMES=(); MARKS=(); FAILED=0; SKIPPED=0

step() {  # step 이름 명령...
  local name="$1"; shift
  if [ -n "$ONLY" ] && [[ "$name" != *"$ONLY"* ]]; then
    NAMES+=("$name"); MARKS+=("${Y}건너뜀${Z}"); SKIPPED=1; return
  fi
  echo "── $name"
  if "$@"; then NAMES+=("$name"); MARKS+=("${G}통과${Z}")
  else NAMES+=("$name"); MARKS+=("${R}실패${Z}"); FAILED=1; fi
}


step ruff               uv run ruff check .
step pytest             uv run pytest -q
step check_docs         uv run python tools/check_docs.py
step doc_fsck           uv run python tools/doc_fsck.py
step model_licenses     uv run python tools/check_model_licenses.py
step hypotheses         uv run python tools/check_hypotheses.py
step ontology           uv run python tools/check_ontology.py
if [ "${CI:-}" = "true" ]; then NAMES+=("lake"); MARKS+=("CI 밖 — SSD 는 이 기계에만 있다")
else step lake          uv run python tools/lake.py check; fi

echo
for i in "${!NAMES[@]}"; do printf '  %-16s %s\n' "${NAMES[$i]}" "${MARKS[$i]}"; done
if [ "$SKIPPED" = 1 ]; then
  printf '  %-16s %s\n' "부분 실행" "${R}실패${Z} — 건너뛴 것은 통과가 아니다"
  FAILED=1
fi
exit "$FAILED"
