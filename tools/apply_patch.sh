#!/usr/bin/env bash
# INBOX(브라우저 다운로드 폴더)에 받은 패치를 커밋째 붙인다(DECISIONS §21).
#   bash tools/apply_patch.sh              INBOX 에서 가장 최근 seshat-*.patch
#   bash tools/apply_patch.sh 이름.patch    INBOX 안의 특정 파일
#   bash tools/apply_patch.sh /경로/x.patch 절대경로도 받는다
#
# ★ thoth `tools/apply_patch.sh` 와 뜻이 같고 방식이 다르다. thoth 는 `git apply` 뒤 ship 이 커밋하고,
#   seshat 패치는 `git format-patch` 커밋이라 `git am` 으로 커밋째 붙인다. 여러 커밋이 든 패치도 받는다.
# ★ 2026-09-22 `git am ~/Downloads/…` 가 파일이 없다며 죽었다. 브라우저는 윈도우 다운로드 폴더에 받는다 —
#   WSL 의 `~/Downloads` 가 아니다. 자리는 `.env` 의 SESHAT_INBOX 가 든다.
# ★ 브라우저를 거친 패치는 줄끝이 CRLF 일 수 있다. 사본을 /tmp 에 두고 벗긴다 — 원본은 안 건드린다.
# ★ **이미 붙은 패치는 아무것도 안 한다.** 패치의 커밋 제목이 전부 이력에 있으면 붙은 것이다.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
. tools/lib/env.sh; load_env .env
: "${SESHAT_INBOX:?.env 에 SESHAT_INBOX 가 없다 — .env.example 을 본다}"

# ★ 인자가 없으면 **안 붙은 것을 번호 순서로 전부** 붙인다(DECISIONS §30). 종전에는 가장 최근 하나만 봤고,
#   밀린 패치가 둘이면 뒤엣것부터 붙이려다 붙지 않았다 — 순서는 이름의 번호가 안다.
ARG="${1:-}"
if [ -z "$ARG" ]; then
  mapfile -t ALL < <(find "$SESHAT_INBOX" -maxdepth 1 -name 'seshat-*.patch' 2>/dev/null | sort -V)
  [ "${#ALL[@]}" -gt 0 ] || { echo "$SESHAT_INBOX 에 seshat-*.patch 가 없다" >&2; exit 1; }
  PENDING=()
  for f in "${ALL[@]}"; do
    [ "$(python3 tools/patch_subjects.py --state "$f")" = "붙음" ] || PENDING+=("$f")
  done
  [ "${#PENDING[@]}" -gt 0 ] || { echo "  안 붙은 패치가 없다"; exit 0; }
  if [ "${#PENDING[@]}" -gt 1 ]; then
    echo "  밀린 패치 ${#PENDING[@]}개 — 번호 순서로 붙인다"
    for f in "${PENDING[@]}"; do bash "$0" "$f"; done
    exit 0
  fi
  SRC="${PENDING[0]}"
elif [ -f "$ARG" ]; then
  SRC="$ARG"
else
  SRC="$SESHAT_INBOX/$ARG"
  [ -f "$SRC" ] || { echo "없는 파일 : $SRC" >&2; exit 1; }
fi
echo "패치 : $SRC"

TMP="$(mktemp /tmp/seshat-patch.XXXXXX)"
trap 'rm -f "$TMP"' EXIT
sed 's/\r$//' "$SRC" > "$TMP"
cmp -s "$SRC" "$TMP" || echo "       줄끝 CRLF 를 LF 로 벗겼다"

# ★ 패치가 선 자리와 여기가 같은가(DECISIONS §30). 봇이 GitHub 에서 main 을 움직이면 여기서 갈린다
BASE="$(sed -n 's/^Seshat-Base-Tree: //p' "$TMP" | head -1)"
if [ -n "$BASE" ] && [ "$BASE" != "$(git rev-parse HEAD^{tree})" ]; then
  if git cat-file -e "$BASE" 2>/dev/null && git merge-base --is-ancestor "$BASE" HEAD 2>/dev/null; then
    echo "       이 패치는 지난 자리에서 만들어졌다 — 그 뒤 커밋이 있다" >&2
  else
    echo "이 패치가 선 자리가 여기와 다르다 — 만든 쪽이 모르는 커밋이 여기 있다(봇 PR 등)" >&2
    echo "       기준 나무 $BASE" >&2
    echo "       지금 나무 $(git rev-parse HEAD^{tree})" >&2
    echo "       git log --oneline -8 을 만든 쪽에 보이고 다시 받는다" >&2
    exit 1
  fi
fi

# 커밋 제목들. 판정 규칙은 tools/patch_subjects.py 하나다 — sweep.py 가 같은 것을 쓴다
SUBJECTS="$(python3 tools/patch_subjects.py "$TMP")"
[ -n "$SUBJECTS" ] || { echo "커밋 패치가 아니다 — git format-patch 산출물만 받는다" >&2; exit 1; }
LOG="$(git log --format=%s -n 500)"
MISSING="$(printf '%s\n' "$SUBJECTS" | while IFS= read -r s; do grep -qxF -- "$s" <<<"$LOG" || printf '%s\n' "$s"; done)"
if [ -z "$MISSING" ]; then
  echo "       이미 붙어 있다. 아무것도 안 한다"
  exit 0
fi

if [ -n "$(git status --porcelain)" ]; then
  echo "작업 트리가 더럽다 — 반쯤 붙으면 무엇이 패치인지 가를 수 없다" >&2
  git status --short | sed 's/^/       /' >&2
  exit 1
fi

if ! git am --3way "$TMP"; then
  git am --abort 2>/dev/null || true
  echo "붙지 않는다 — 되돌렸다. 패치를 만든 시점과 저장소가 다르다" >&2
  exit 1
fi
git log --oneline -n "$(printf '%s\n' "$MISSING" | wc -l)" | sed 's/^/  붙었다 /'

uv sync -q --group eval
echo
echo "다음 : bash tools/verify.sh"
echo "       그 뒤 : git push"
