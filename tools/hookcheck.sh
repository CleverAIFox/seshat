#!/usr/bin/env bash
# tools/hookcheck.sh — **훅이 도는가.** 있는지가 아니라 도는지를 **실행으로** 잰다(DECISIONS §164).
#
#   bash tools/hookcheck.sh            = --check
#   bash tools/hookcheck.sh --install  이 저장소의 훅 자리를 기계에 알린다
#
# ★ **문자열 검사로는 못 잡는다.** 파이어레인에서 전역 훅의 `exit 0` 뒤에 붙은 죽은 스니펫이
#   마커 검사를 통과한 적이 있다 — 「있는가」 를 묻고 「도는가」 를 안 물었다.
# ★ **`core.hooksPath` 는 기계 설정이다**(DECISIONS §137 — 기계는 하나인데 저장소가 셋이다).
#   `--install` 은 **전역 설정이 없을 때만** 로컬에 박고, 있으면 건드리지 않고 무엇을 할지 찍는다.
# ★ **변수 이름은 ASCII 다.** 배시는 한글 이름을 못 받는다 — 2026-09-28 에 두 번째로 겪었다
#   (`tests/test_workflows.py::test_셸의_변수_이름은_ASCII_다` 가 이제 막는다).
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
SENTINEL='[seshat] pre-commit 도달'
RED=$'\033[31m'; GREEN=$'\033[32m'; Z=$'\033[0m'; [ -t 1 ] || { RED=""; GREEN=""; Z=""; }

local_path() { git config --get core.hooksPath 2>/dev/null; }
global_path() { git config --global --get core.hooksPath 2>/dev/null; }

case "${1:---check}" in
--install)
  if [ -n "$(global_path)" ]; then
    printf '  전역 훅 자리가 이미 있다 : %s\n' "$(global_path)"
    printf '  **건드리지 않는다** — 로컬에 박으면 전역이 죽는다(딴 저장소의 방어가 사라진다).\n'
    printf '  그 전역 훅이 `<저장소>/.githooks/pre-commit` 을 찾아 부르면 이대로 돈다.\n'
    printf '  안 부르면 : git config core.hooksPath .githooks   (이 저장소만)\n'
    exit 0
  fi
  git config core.hooksPath .githooks && printf '  이 저장소의 훅 자리를 .githooks 로 박았다\n'
  ;;
--check)
  if [ ! -x .githooks/pre-commit ]; then
    printf '%s✗ .githooks/pre-commit 이 없거나 실행 권한이 없다%s\n' "$RED" "$Z" >&2; exit 1
  fi
  where="$(local_path)"; [ -n "$where" ] || where="$(global_path)"
  if [ -z "$where" ]; then
    printf '%s✗ 커밋 시점 방어가 빠진다%s — 훅 자리가 안 잡혀 있다(파일은 있다)\n' "$RED" "$Z" >&2
    printf '  bash tools/hookcheck.sh --install\n' >&2; exit 1
  fi
  hook="$where/pre-commit"
  # ★ **실행으로 잰다.** 죽은 코드는 문자열 검사를 통과하지만 탐침은 통과 못 한다
  seen="$(SESHAT_HOOK_PROBE=1 "$hook" 2>&1 || true)"
  case "$seen" in
    *"$SENTINEL"*) printf '  %s훅이 돈다%s — 탐침이 도달했다(%s)\n' "$GREEN" "$Z" "$hook" ;;
    *) printf '%s✗ 훅 파일은 있는데 안 불린다%s — 탐침이 도달 못 했다(%s)\n' "$RED" "$Z" "$hook" >&2
       printf '  bash tools/hookcheck.sh --install\n' >&2; exit 1 ;;
  esac
  ;;
*) echo "모르는 인자: $1" >&2; exit 2 ;;
esac
