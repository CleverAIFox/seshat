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
# ★ **셸도 린트한다**(DECISIONS §282). 2026-10-02 까지 이 저장소에 shellcheck 호출이 **한 곳도
#   없었다** — 셸 파일이 다섯인데 thoth 는 돌리고 CI 가 존재까지 단언한다. 「같은 규율을
#   공유한다」 고 MASTER 에 적어 두고 **이 축만 안 건너왔다.**
# ★ **등급을 warning 까지만 본다.** info · style 은 취향이고 커밋을 막을 일이 아니다(thoth §46).
# ★ **CI 에서는 없는 것이 실패다.** ubuntu-24.04 러너에는 깔려 있다. 이 기계에 없으면 까닭을
#   적고 건너뛰는데, **그러면 강제자는 CI 하나다** — 훅과 CI 를 가르는 것과 같은 꼴이다(§170).
shellcheck_step() {
  # ★ 변수 이름은 ASCII 다 — 배시는 한글 이름을 못 받는다(DECISIONS §164).
  local SH_FILES; mapfile -t SH_FILES < <(git ls-files '*.sh' '.githooks/*')
  if ! command -v shellcheck >/dev/null 2>&1; then
    if [ "${CI:-}" = "true" ]; then
      echo "shellcheck 가 CI 에 없다 — 러너 이미지가 바뀌었다" >&2; return 1
    fi
    echo "       shellcheck 가 없어 못 봤다 (CI 에서는 돈다) : sudo apt install shellcheck"
    return 0
  fi
  shellcheck -S warning -f gcc "${SH_FILES[@]}"
}
step shellcheck         shellcheck_step
step pytest             uv run pytest -q
step check_docs         uv run python tools/check_docs.py
# ★ **DECISIONS 의 본문은 추가만 한다 — 강제자 줄은 표기라 고칠 수 있다**(§296). PLAN 머리가
#   「append-only」 를 선언하는데 **보는 자가 없었다.** 줄 단위로 걸면 표기와 본문이 뭉뚱그려져
#   썩은 강제자 인용을 고칠 수 없다 — 2026-10-05 에 일곱 줄을 고쳐야 했다.
# ★ **CI 에서는 작업 트리가 HEAD 와 같아 언제나 통과한다.** 훅과 이 자리가 강제자다(§170).
# ★ **못 쟀다를 통과로 세지 않는다**(DECISIONS §59 · §311). 종전에는 `rc 3`(「HEAD 에
#   DECISIONS 가 없어 대조 안 함」)을 **0 으로 바꿔** 돌려줬다 — 그러면 **대조를 한 번도
#   안 한 판이 초록**으로 보인다. 0 과 3 은 **다른 말**이고, 가르는 쪽이 `ONLY` 와 같은
#   「부분 실행」 자리다. 여기서도 같은 꼴로 찍는다.
append_only_step() {  # 이름은 ASCII 다 — shellcheck 과 test_셸의_변수_이름은_ASCII_다
  local old rc
  old="$(git show HEAD:docs/DECISIONS.md 2>/dev/null)" || true
  if [ -z "$old" ]; then
    echo "  HEAD 에 DECISIONS 가 없어 대조하지 않았다 — **통과가 아니다**"
    SKIPPED=1; return 0
  fi
  printf '%s\n' "$old" | uv run python tools/check_docs.py --추가만; rc=$?
  if [ "$rc" = 3 ]; then
    echo "  대조하지 않았다(rc 3) — **통과가 아니다**"
    SKIPPED=1; return 0
  fi
  return "$rc"
}
step 추가만             append_only_step
step check_rules        uv run python tools/check_rules.py
step check_prose        uv run python tools/check_prose.py
# ★ **결정 기록은 사람 말을 그대로 담지 않는다**(DECISIONS §199). 축은 **말투** 하나다 —
#   욕설 사전을 주축에 두면 실측 15 중 **1** 만 잡는다. 사전은 말투가 못 가르는
#   잔여(`?` 없는 해체 의문)를 받치는 그물로만 쓴다. **소급 바닥이 없다 — 전수 0 이다.**
step speech              uv run python tools/check_speech.py
step check_size         uv run python tools/check_size.py
step numbers            uv run python tools/check_numbers.py
step docgen             uv run python tools/docgen.py
step doc_fsck           uv run python tools/doc_fsck.py
step model_licenses     uv run python tools/check_model_licenses.py
step hypotheses         uv run python tools/check_hypotheses.py
step ontology           uv run python tools/check_ontology.py
step ways               uv run python tools/check_ways.py
step crashes            uv run python tools/check_crashes.py
step secrets            uv run python tools/check_secrets.py
step scope              uv run python tools/check_scope.py
step dead               uv run python tools/check_dead.py
step deadchecks         uv run python tools/check_deadchecks.py
# ★ **「가진 것」 과 「도는 것」 은 다르다**(DECISIONS §287). `mutate.py` 는 2026-10-01 부터
#   있었는데 **어느 사슬에도 없었고** MASTER 가 그 까닭을 적어 뒀다 — 「한 판에 수십 분」.
#   짝 시험으로 좁혀 **2.1시간 → 7분**이 됐고, 그래서 여기 들어온다.
# ★ **범위는 검사 술어다.** 2026-10-01 에 터진 다섯 중 셋이 `tools/` 였다 — **재는 쪽을 안
#   재면 검사가 거짓이어도 조용하다.**
# ★ **제품 쪽도 넣는다**(2026-10-19 · DECISIONS §307). `seshat/*.py` 101자리를 재니 **5분 52초**
#   였고 **붙드는 시험이 없는 자리가 둘** 나왔다 — `grammar.py::depth` 와 `serve.py::main`.
#   둘 다 `seshat/` 안이다 : 사슬이 `tools/check_*` 만 보는 동안 **제품 쪽이 비어 있었다.**
#   값이 6분이고 찾은 것이 둘이면 넣는 것이 맞다.
# ★ **아직 밖인 것** : 나머지 `tools/*.py` 250자리(개발 유틸). 안 쟀다 — PLAN #53 이 든다.
#   종전 주석은 「`seshat/` 쪽 335자리」 라고 적었는데 **335 는 사슬 밖 전체(351)와 헷갈린
#   수**다. `seshat/` 은 101 이고 `tools/` 가 357 이다.
# ★ 좁혀 뚫어도 **장부는 저장소 전체로 센다** — 안 그러면 사슬에서 톱니가 영원히 안 운다.
step mutate             uv run python tools/mutate.py --only 'tools/check_*.py' --only 'seshat/*.py'
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
