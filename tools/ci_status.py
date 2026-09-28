"""**마지막 CI 가 초록인가**(DECISIONS §170).

  python3 tools/ci_status.py            main 의 마지막 판. 빨가면 1
  python3 tools/ci_status.py --branch x 다른 가지

★ **2026-09-28 CI 가 네 판째 빨간 것을 아무도 몰랐다.** seshat-153 이 `verify.sh` 에 훅 검사를
  넣었는데 **CI 에는 훅을 깔 까닭이 없다** — CI 는 커밋을 안 한다. 그래서 이 기계에서는 초록이고
  GitHub 에서만 빨갰고, **GitHub 을 안 봤다.**
★ **훅은 강제자가 아니다 — 빠른 되먹임이다.** 훅은 이 기계의 `core.hooksPath` 에 산다. 저장소를
  새로 받은 사람에게는 없고, 남의 PR 에도 안 돈다. **남을 막는 것은 CI 뿐이다.** §153 이 훅을
  강제자라고 적은 것은 틀렸다 — 기억보다는 낫지만 CI 보다는 못하다.
★ **못 보는 것이 이 검사의 실패 방식이다.** `gh` 가 없거나 로그인이 안 됐으면 **통과가 아니라
  실패**로 찍는다. 조용히 안 보는 검사가 오늘의 병을 만들었다.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys

_FIELDS = "conclusion,status,displayTitle,headSha,url,createdAt"


def 마지막_판(branch: str = "main") -> dict | str:
    """{conclusion, …} 또는 **왜 못 봤는지**를 적은 글."""
    if not shutil.which("gh"):
        return "`gh` 가 없다 — `sudo apt install gh && gh auth login`. **못 보는 것은 통과가 아니다**"
    r = subprocess.run(["gh", "run", "list", "--branch", branch, "-L", "1", "--json", _FIELDS],
                       capture_output=True, text=True)
    if r.returncode != 0:
        말 = (r.stderr or "").strip().splitlines()
        return f"`gh` 가 못 읽었다 — {말[-1] if 말 else '까닭 없음'}"
    try:
        판 = json.loads(r.stdout or "[]")
    except json.JSONDecodeError:
        return "`gh` 가 JSON 이 아닌 것을 줬다"
    return 판[0] if 판 else "판이 없다"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", default="main")
    a = ap.parse_args(argv)

    판 = 마지막_판(a.branch)
    if isinstance(판, str):
        print(f"  ✗ CI 를 못 봤다 — {판}", file=sys.stderr)
        return 1
    끝 = (판.get("conclusion") or "").lower()
    제목 = (판.get("displayTitle") or "?")[:60]
    짧 = (판.get("headSha") or "")[:7]
    if 끝 == "success":
        print(f"  마지막 CI 초록 — {짧} {제목}")
        return 0
    if not 끝:                      # 아직 도는 중
        print(f"  마지막 CI 도는 중({판.get('status')}) — {짧} {제목}")
        return 0
    print(f"  ✗ **마지막 CI 가 {끝}** — {짧} {제목}\n    {판.get('url', '')}\n"
          f"    이 기계에서 초록인 것은 CI 가 초록이라는 뜻이 아니다(DECISIONS §170)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
