#!/usr/bin/env bash
# 패치를 만든다 — **기준 나무(base-tree)를 패치가 들고 간다**(DECISIONS §30).
#   bash tools/make_patch.sh 2 /경로/seshat-030-무엇.patch     최근 2개 커밋
#
# ★ 2026-09-23. 의존성 봇의 PR 을 GitHub 에서 합치자 main 이 움직였고, 그것을 모르는 사본에서 만든 패치가
#   `sha1 information is lacking` 로 죽었다. git 의 말은 **무엇이 다른지** 알려주지 않는다.
#   패치가 「내가 선 자리」 를 적어 오면 붙이는 쪽이 「여기는 다른 자리다」 라고 말할 수 있다.
# ★ 커밋 해시가 아니라 **나무 해시**다. 같은 내용을 다른 기계에서 커밋하면 해시는 달라도 나무는 같다.
# ★ **제안 상태로 더한 가설을 일러 준다**(DECISIONS §72). 2026-09-25 까지 네 번, 「이것을 돌리십시오」 라고
#   보낸 패치가 그 가설을 제안으로 두고 있었다. 문이 네 번 다 막았지만, 막히는 것과 알려 주는 것은 다르다.
set -euo pipefail
cd "$(dirname "$0")/.."
N="${1:?몇 개 커밋인가}"
OUT="${2:?어디에 쓸 것인가}"
BASE="$(git rev-parse "HEAD~$N^{tree}")"
git format-patch -"$N" --stdout > "$OUT.tmp"
awk -v b="$BASE" 'NR==1{print; print "Seshat-Base-Tree: " b; next} {print}' "$OUT.tmp" > "$OUT"
rm -f "$OUT.tmp"
echo "  $OUT · 기준 나무 $BASE · 커밋 $N개"

# 이 패치가 새로 더한 가설 줄 중 제안 상태인 것. 실패가 아니라 물음이다 — 진짜 제안일 수도 있다
# ★ 못 찾는 것은 정상이다. `set -e` 아래서 grep 의 1 을 그대로 두면 **경고가 없을 때 도구가 죽는다**
PROPOSED="$(grep -E '^\+\| H-[0-9]+ \| 제안 \|' "$OUT" | sed -E 's/^\+\| (H-[0-9]+).*/\1/' | tr '\n' ' ' || true)"
if [ -n "$PROPOSED" ]; then
  echo "  ※ 이 패치가 제안 상태로 더하는 가설 : ${PROPOSED}" >&2
  echo "    지금 돌릴 것이면 이 패치에서 '실험' 으로 올린다 — 안 그러면 문이 막는다" >&2
fi

# ★ **uv.lock 은 판 번호 한 줄만 바뀌어야 한다**(DECISIONS §96 · §99). 사본에서 `uv run` 을 돌리면
#   갱신되고 `git add -A` 가 담는다. 두 사본이 같은 자리면 그 한 줄은 오히려 실어야 맞다 — 빼면 붙인 쪽이
#   `uv sync` 로 또 더럽혀진다. 위험한 것은 **의존성까지 바뀐 lock** 이다. 그것만 경고한다
if grep -q '^diff --git a/uv.lock' "$OUT"; then
  LOCK="$(awk '/^diff --git a\/uv.lock/{on=1;next} on&&/^diff --git /{on=0} on&&/^[-+][^-+]/' "$OUT" \
          | grep -vcE '^[-+]version = "[0-9.]+"$' || true)"
  if [ "${LOCK:-0}" -gt 0 ]; then
    echo "  ※ 이 패치의 uv.lock 이 판 번호 말고도 ${LOCK}줄 바뀌었다 — 붙이는 쪽에서 충돌한다" >&2
    echo "    빼고 다시 만든다 : git checkout HEAD~1 -- uv.lock && git commit --amend --no-edit" >&2
  fi
fi

# ★ **재는 자를 바꾸는 일과 그 자로 판정하는 일을 같이 두지 않는다**(DECISIONS §96 · §86).
#   붙이는 사람이 둘을 순서대로 할 방법이 없다 — 근거 숫자가 없어진 사전으로 잰 것이 된다
VERDICT="$(grep -cE '^\+\| H-[0-9]+ \| (채택|기각) \|' "$OUT" || true)"
if [ "$VERDICT" -gt 0 ] && grep -q '^diff --git a/data/ontology/' "$OUT"; then
  echo "  ※ 이 패치가 판정과 온톨로지를 같이 바꾼다 — 근거 숫자를 없어진 사전으로 잰 것이 된다" >&2
  echo "    사전 먼저 · 다시 재고 · 그다음 판정. 셋으로 나눈다(DECISIONS §96)" >&2
fi
