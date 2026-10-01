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
# ★ **훅 검사와 CI 검사는 서로 반대쪽에서만 돈다**(DECISIONS §170). 훅은 커밋할 때 도는 것이라
#   CI 에는 깔 까닭이 없고 — CI 는 커밋을 안 한다 — CI 판정은 CI 안에서 보는 것이 뜻이 없다.
#   2026-09-28 이 둘을 안 갈라서 **CI 가 네 판째 빨간데 이 기계에서는 초록이었다.**
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


if [ "${CI:-}" = "true" ]; then NAMES+=("훅"); MARKS+=("CI 밖 — CI 는 커밋을 안 한다")
else step 훅            bash tools/hookcheck.sh --check; fi
step lock               uv lock --check
step ruff               uv run ruff check .
step pytest             uv run pytest -q
step check_docs         uv run python tools/check_docs.py
step check_rules        uv run python tools/check_rules.py
step numbers            uv run python tools/check_numbers.py
step docgen             uv run python tools/docgen.py
step doc_fsck           uv run python tools/doc_fsck.py
step model_licenses     uv run python tools/check_model_licenses.py
step hypotheses         uv run python tools/check_hypotheses.py
step ontology           uv run python tools/check_ontology.py
step ways               uv run python tools/check_ways.py
step crashes            uv run python tools/check_crashes.py
step scope              uv run python tools/check_scope.py
step dead               uv run python tools/check_dead.py
step deadchecks         uv run python tools/check_deadchecks.py
step claims             uv run python tools/check_claims.py
step docseal            uv run python tools/docseal.py
step bootstrap          uv run python tools/bootstrap.py --selftest
step catalog            uv run python tools/check_catalog.py
if [ "${CI:-}" = "true" ]; then NAMES+=("lake"); MARKS+=("CI 밖 — SSD 는 이 기계에만 있다")
else step lake          uv run python tools/lake.py check; fi
# ★ **이 기계가 초록인 것과 CI 가 초록인 것은 다른 말이다**(DECISIONS §170). 훅을 만들고 나서
#   진짜 강제자를 안 보게 됐다 — 네 판을 빨간 채로 밀었다
if [ "${CI:-}" = "true" ]; then NAMES+=("ci"); MARKS+=("CI 안 — 이 판이 그 판이다")
else step ci            uv run python tools/ci_status.py; fi

echo
for i in "${!NAMES[@]}"; do printf '  %-16s %s\n' "${NAMES[$i]}" "${MARKS[$i]}"; done
if [ "$SKIPPED" = 1 ]; then
  printf '  %-16s %s\n' "부분 실행" "${R}실패${Z} — 건너뛴 것은 통과가 아니다"
  FAILED=1
fi
exit "$FAILED"
