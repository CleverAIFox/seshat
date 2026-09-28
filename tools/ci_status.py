"""**CI 가 지금 커밋을 초록으로 봤는가**(DECISIONS §170 · §172).

  python3 tools/ci_status.py            지금 HEAD 의 판정. 빨가면 1
  python3 tools/ci_status.py --branch x 다른 가지

★ **2026-09-28 CI 가 네 판째 빨간 것을 아무도 몰랐다**(§170). `verify.sh` 가 CI 에서 커밋 훅을
  검사하고 있었고 — CI 는 커밋을 안 한다 — 이 기계에서는 초록이라 GitHub 을 안 봤다.
★ **처음 만든 판은 거짓 초록을 찍었다**(§172). `gh run list -L 1` 이 「가장 최근 판」 을 준다고
  믿었는데 **열한 판 묵은 것을 줬다.** 이제 **창을 넓게 열고 `createdAt` 으로 직접 고른다.**
★ **「아직 안 봤다」 를 초록으로 안 찍는다.** 밀기 전의 HEAD 는 CI 가 본 적이 없다 — 그것은
  통과가 아니라 **모름**이다. 다만 마지막으로 **끝난** 판이 빨가면 그때는 막는다.
★ **못 보는 것이 이 검사의 실패 방식이다.** `gh` 가 없거나 로그인이 안 됐으면 초록으로 안 찍는다.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys

_FIELDS = "conclusion,status,displayTitle,headSha,url,createdAt,workflowName"
창 = 30          # **1 은 가장 최근이 아니었다**(§172). 넓게 받아서 이쪽에서 고른다


def 판들(branch: str = "main", limit: int = 창) -> list[dict] | str:
    """최근 판 목록(새 것부터) 또는 **왜 못 봤는지**를 적은 글."""
    if not shutil.which("gh"):
        return "`gh` 가 없다 — `sudo apt install gh && gh auth login`. **못 보는 것은 통과가 아니다**"
    r = subprocess.run(["gh", "run", "list", "--branch", branch, "-L", str(limit), "--json", _FIELDS],
                       capture_output=True, text=True)
    if r.returncode != 0:
        말 = (r.stderr or "").strip().splitlines()
        return f"`gh` 가 못 읽었다 — {말[-1] if 말 else '까닭 없음'}"
    try:
        판 = json.loads(r.stdout or "[]")
    except json.JSONDecodeError:
        return "`gh` 가 JSON 이 아닌 것을 줬다"
    # ★ **온 순서를 믿지 않는다.** `-L 1` 이 묵은 판을 준 적이 있다 — 여기서 직접 정렬한다
    return sorted(판, key=lambda d: d.get("createdAt") or "", reverse=True)


def 지금_커밋() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def _한줄(판: dict) -> str:
    return f"{(판.get('headSha') or '')[:7]} {(판.get('displayTitle') or '?')[:56]}"


def 고른다(판: list[dict], 여기: str) -> tuple[int, str]:
    """(종료 코드, 할 말). **판정의 자리는 여기 하나다** — 시험이 이 함수를 직접 부른다.

    ★ **부르는 쪽의 순서를 안 믿는다**(DECISIONS §169 · §172). 정렬을 `판들` 에만 두었더니
      이 함수가 **받은 순서대로 첫 끝난 판**을 집었다 — 목록이 뒤섞여 오면 옛 초록을 집는다.
      `gh` 가 순서를 지켜 준다고 믿은 것이 §172 의 시작이었고, **그 믿음을 여기서 또 했다.**
    """
    판 = sorted(판, key=lambda d: d.get("createdAt") or "", reverse=True)
    내것 = [x for x in 판 if x.get("headSha") == 여기]
    if 내것:
        끝 = (내것[0].get("conclusion") or "").lower()
        if 끝 == "success":
            return 0, f"  이 커밋을 CI 가 초록으로 봤다 — {_한줄(내것[0])}"
        if not 끝:
            return 0, f"  이 커밋을 CI 가 도는 중({내것[0].get('status')}) — {_한줄(내것[0])}"
        return 1, (f"  ✗ **이 커밋의 CI 가 {끝}** — {_한줄(내것[0])}\n    {내것[0].get('url', '')}")
    # ★ **아직 안 본 커밋이다.** 밀기 전이면 정상이다 — 초록으로도 빨강으로도 안 찍는다.
    #   다만 **마지막으로 끝난 판**이 빨가면 그것은 지금 막아야 하는 빨강이다
    끝난 = next((x for x in 판 if (x.get("conclusion") or "")), None)
    if 끝난 and (끝난.get("conclusion") or "").lower() != "success":
        return 1, (f"  ✗ **마지막으로 끝난 CI 가 {끝난['conclusion'].lower()}** — {_한줄(끝난)}\n"
                   f"    {끝난.get('url', '')}\n"
                   f"    (지금 커밋 {여기[:7]} 는 CI 가 아직 안 봤다)")
    끝말 = f"마지막으로 끝난 판은 초록 — {_한줄(끝난)}" if 끝난 else "끝난 판이 없다"
    return 0, f"  이 커밋({여기[:7]})을 CI 가 아직 안 봤다 — 밀기 전이면 정상이다\n    {끝말}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", default="main")
    a = ap.parse_args(argv)

    판 = 판들(a.branch)
    if isinstance(판, str):
        print(f"  ✗ CI 를 못 봤다 — {판}", file=sys.stderr)
        return 1
    if not 판:
        print(f"  ✗ CI 를 못 봤다 — {a.branch} 에 판이 없다", file=sys.stderr)
        return 1
    코드, 말 = 고른다(판, 지금_커밋())
    print(말, file=sys.stderr if 코드 else sys.stdout)
    return 코드


if __name__ == "__main__":
    sys.exit(main())
