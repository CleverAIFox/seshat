#!/usr/bin/env python3
"""커밋 작성자 메일이 **갈 수 있는 주소인가** — 커밋 시점에 본다(`.githooks/pre-commit`).

저장소가 공개이므로(DECISIONS §329) 작성자 메일은 이력에 그대로 박혀 읽힌다.
`c@x` · `a@b` · `t@t` 같은 가짜 주소가 이미 81 커밋에 있고, 이력은 고치지 않는다.
**앞으로** 안 생기게 하는 것이 이 자의 일이다.

★ **허용 목록이 아니라 꼴만 본다.** 메일 하나를 박아 두면 사람이 바뀔 때 이 파일을 고쳐야 하고,
  그 고침을 잊으면 훅이 정상 커밋을 막는다. 가짜 주소의 공통점은 **도메인에 점이 없다**는 것이다.
★ **이 자는 `git var GIT_AUTHOR_IDENT` 를 읽는다** — 환경 변수 · 저장소 설정 · 전역 설정을
  git 이 합친 **실제로 박힐 값**이다. 설정 파일을 따로 읽으면 환경 변수로 덮인 값을 놓친다.

★ **밖 — 커밋 메일의 주인은 안 본다.** 남의 주소를 쓴 커밋도 꼴만 맞으면 통과한다. 꼴이 없는 가짜 주소만 막는다.
★ **밖 — 커미터와 `Co-Authored-By` 는 안 본다.** 작성자(`GIT_AUTHOR_IDENT`) 하나만 본다.
★ **밖 — 이미 박힌 이력은 안 본다.** 훅은 새 커밋의 신원만 읽는다 — 이력은 고치지 않는다(DECISIONS §329).

`--selftest` 는 git 없이 판별식만 잰다(`verify.sh` 가 도는 것).

종료코드: 0 = 통과 · 1 = 가짜 주소 · 2 = 이 자가 고장(git 을 못 불렀다 · 꼴을 못 읽었다).
"""
from __future__ import annotations

import re
import subprocess
import sys

IDENT = re.compile(r"^(?P<이름>.*?)\s*<(?P<메일>[^<>]*)>")
# 로컬@도메인.최상위 — 도메인에 점이 하나 이상 있고 공백이 없다.
꼴 = re.compile(r"^[^@\s]+@[^@\s.]+(?:\.[^@\s.]+)+$")


def 메일을_뜬다(ident: str) -> str | None:
    """`이름 <메일> 시각 시간대` 에서 메일. 꼴이 아니면 None."""
    m = IDENT.match(ident.strip())
    return m.group("메일") if m else None


def 갈수_있나(메일: str) -> bool:
    return bool(꼴.match(메일))


def _selftest() -> int:
    """git 없이 판별식만 잰다 — CI 에는 작성자 신원이 없을 수 있어 `verify.sh` 는 이것만 돈다."""
    if 갈수_있나("c@x") or not 갈수_있나("who@example.com"):
        print("check_author: 판별식이 거꾸로다 — 가짜를 통과시키거나 보통을 막는다", file=sys.stderr)
        return 2
    print("  판별식이 산다 — 실제 작성자는 커밋 직전 훅이 본다")
    return 0


def main(argv: list[str] | None = None) -> int:
    if "--selftest" in (sys.argv[1:] if argv is None else argv):
        return _selftest()
    try:
        r = subprocess.run(["git", "var", "GIT_AUTHOR_IDENT"], capture_output=True, text=True)
    except OSError as e:
        print(f"check_author: git 을 못 불렀다 — {e}", file=sys.stderr)
        return 2
    if r.returncode != 0:
        print(f"check_author: git var 실패 — {r.stderr.strip()[:200]}", file=sys.stderr)
        return 2
    메일 = 메일을_뜬다(r.stdout)
    if 메일 is None:
        print(f"check_author: 작성자 꼴을 못 읽었다 — {r.stdout.strip()[:80]!r}", file=sys.stderr)
        return 2
    if not 갈수_있나(메일):
        print(f"    작성자 메일 {메일!r} 은 갈 수 있는 주소가 아니다 — "
              "`git config user.email` 을 고친다(이력은 공개다)")
        return 1
    print(f"  작성자 메일 {메일.split('@')[1]} 도메인 — 꼴이 맞다")
    return 0


if __name__ == "__main__":
    # ★ 위반(1)과 도구 고장(2)을 다른 코드로 끝낸다(DECISIONS §21 · §232)
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        print("    ✗ 도구가 깨졌다 — 위 역추적이 자리를 든다\n"
              "      고치고 다시 돌린다 : python3 tools/check_author.py --selftest", file=sys.stderr)
        sys.exit(2)
