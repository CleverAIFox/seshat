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

ARG="${1:-}"
if [ -z "$ARG" ]; then
  SRC="$(find "$SESHAT_INBOX" -maxdepth 1 -name 'seshat-*.patch' -printf '%T@ %p\n' 2>/dev/null \
         | sort -rn | head -1 | cut -d' ' -f2-)"
  [ -n "$SRC" ] || { echo "$SESHAT_INBOX 에 seshat-*.patch 가 없다" >&2; exit 1; }
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

# 커밋 제목들. ★ format-patch 는 한글 제목을 RFC 2047(`=?UTF-8?q?…?=`)로 싼다 — 풀어서 이력과 맞춘다
SUBJECTS="$(python3 - "$TMP" <<'PY'
import mailbox, re, sys
from email.header import decode_header, make_header
for m in mailbox.mbox(sys.argv[1]):
    s = str(make_header(decode_header(m.get("Subject", "")))).replace("\n", "")
    print(re.sub(r"\s+", " ", re.sub(r"^\[PATCH[^]]*\]\s*", "", s)).strip())
PY
)"
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
