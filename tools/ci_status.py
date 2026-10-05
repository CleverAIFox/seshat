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
import pathlib
import re
import shutil
import subprocess
import sys

_FIELDS = "conclusion,status,displayTitle,headSha,url,createdAt,workflowName"
ROOT = pathlib.Path(__file__).resolve().parent.parent
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


# ★ **무엇이 막을 자격이 있나 — 손 목록을 안 만든다**(DECISIONS §292). 「`gpu-eval` 은
#   빼자」 를 코드에 적으면 워크플로가 하나 늘 때 그 목록이 늙는다(§43). **워크플로 파일에서
#   꺼낸다** — 저절로 도는 방아쇠(`push` · `pull_request` · `schedule` · `release`)가 하나라도
#   있으면 그 판정은 **저장소의 판정**이고, `workflow_dispatch` 만 있으면 **사람이 마지막으로
#   손으로 돌린 실험**이라 코드의 판정이 아니다.
# ★ **밖 — 파일을 못 찾은 워크플로는 안 막는다.** 지운 워크플로의 옛 빨강이 영영 막는 것이
#   그 꼴이다. 보고만 하고 그 수를 적는다.
손방아쇠 = {"workflow_dispatch", "workflow_call"}
_이름줄 = re.compile(r"^name:\s*(.+?)\s*$", re.M)
_온블록 = re.compile(r"^on:\s*\n((?:[ \t]+.*\n|\n)*)", re.M)
_방아쇠 = re.compile(r"^\s{2}(\w+)\s*:", re.M)


def 방아쇠(root: pathlib.Path | None = None) -> dict[str, set[str]]:
    """워크플로 **표시 이름** → 방아쇠 집합. `gh` 가 주는 `workflowName` 이 그 이름이다."""
    root = root or ROOT
    것: dict[str, set[str]] = {}
    for f in sorted((root / ".github/workflows").glob("*.yml")):
        글 = f.read_text(encoding="utf-8")
        m = _이름줄.search(글)
        이름 = m.group(1) if m else f.stem
        블록 = _온블록.search(글)
        것[이름] = set(_방아쇠.findall(블록.group(1))) if 블록 else set()
    return 것


def 막을자격(이름: str, 방아쇠표: dict[str, set[str]]) -> bool:
    """그 워크플로의 빨강이 **저장소의 판정**인가.

    ★ **「못 쟀다」 와 「범위 밖」 을 가른다**(DECISIONS §59 · §292). 이름이 **빈 것**은 `gh` 가
      어느 워크플로인지 안 준 것이라 **가릴 재료가 없다** — 못 잼이고, 못 잼은 통과가 아니므로
      **막는다.** 이름이 있는데 표에 없는 것은 **파일이 사라진 것**이라 보고만 한다.
    """
    if not 이름:
        return True
    if 이름 not in 방아쇠표:          # 파일을 못 찾았다 — 지웠거나 이름이 갈렸다
        return False
    return bool(방아쇠표[이름] - 손방아쇠)


def _워크플로(판: dict) -> str:
    """판이 어느 워크플로의 것인가. `gh` 가 안 주면 한 뭉치로 본다 — 옛 꼴을 깨지 않는다."""
    return 판.get("workflowName") or ""


def 워크플로별(판: list[dict], 여기: str) -> dict[str, dict]:
    """워크플로마다 **판정에 쓸 판 하나**. 이 커밋의 것이 있으면 그것, 없으면 그 워크플로의 최신.

    ★ **이것이 §292 의 전부다.** 종전에는 목록 전체에서 판 **하나**를 집었다 — 그러면
      워크플로가 셋인데 **한 판이 저장소의 판정이 된다.** 같은 sha 에서 `ci` 가 초록이고
      `papers` 가 빨가면 **더 최근인 쪽이 이긴다.** 2026-10-05 에 19분 사이에 판정이
      실패 → 통과로 뒤집혔고 **그 사이에 고친 커밋이 없었다.**
    """
    판 = sorted(판, key=lambda d: d.get("createdAt") or "", reverse=True)
    고름: dict[str, dict] = {}
    for x in 판:
        이름 = _워크플로(x)
        있던 = 고름.get(이름)
        # 이 커밋의 판이 그 워크플로의 옛 판을 이긴다. 같은 자격이면 최신이 이긴다(정렬 순).
        if 있던 is None:
            고름[이름] = x
        elif 있던.get("headSha") != 여기 and x.get("headSha") == 여기:
            고름[이름] = x
    return 고름


def 고른다(판: list[dict], 여기: str) -> tuple[int, str]:
    """(종료 코드, 할 말). **판정의 자리는 여기 하나다** — 시험이 이 함수를 직접 부른다.

    ★ **부르는 쪽의 순서를 안 믿는다**(DECISIONS §169 · §172). 정렬을 `판들` 에만 두었더니
      이 함수가 **받은 순서대로 첫 끝난 판**을 집었다 — 목록이 뒤섞여 오면 옛 초록을 집는다.
      `gh` 가 순서를 지켜 준다고 믿은 것이 §172 의 시작이었고, **그 믿음을 여기서 또 했다.**
    ★ **그리고 고친 뒤에도 판을 하나만 봤다**(DECISIONS §292). 정렬은 「어느 판이 최신인가」 를
      고쳤을 뿐이고 **「몇 판을 봐야 하는가」 는 안 고쳤다.** 워크플로마다 하나씩 본다.
    """
    고름 = 워크플로별(판, 여기)
    if not 고름:
        return 0, "  볼 판이 없다"
    표 = 방아쇠()
    빨강_전부 = [(이름, x) for 이름, x in sorted(고름.items())
                 if (x.get("conclusion") or "").lower() not in ("", "success")]
    빨강 = [(이름, x) for 이름, x in 빨강_전부 if 막을자격(이름, 표)]
    손빨강 = [이름 for 이름, _ in 빨강_전부 if not 막을자격(이름, 표)]
    if 빨강:
        줄 = []
        for 이름, x in 빨강:
            제것 = "이 커밋" if x.get("headSha") == 여기 else f"{여기[:7]} 는 아직 안 봤다"
            줄.append(f"  ✗ **{이름 or 'CI'} 가 {(x.get('conclusion') or '').lower()}** "
                      f"({제것}) — {_한줄(x)}\n    {x.get('url', '')}")
        꼬리 = ("" if len(고름) == 1 else
                f"\n    본 워크플로 {len(고름)} : {' · '.join(sorted(k or 'CI' for k in 고름))}")
        if 손빨강:
            꼬리 += f"\n    손으로만 도는 것이라 안 막는 빨강 : {' · '.join(sorted(손빨강))}"
        return 1, "\n".join(줄) + 꼬리
    # ★ **빨강이 없다.** 이 커밋을 본 워크플로와 아직 안 본 워크플로를 **갈라 적는다** —
    #   「모른다」 를 「초록」 으로 적으면 밀기 전 HEAD 가 늘 초록이 된다(§172 · §110).
    손말 = (f"\n    손으로만 도는 것이라 안 막는 빨강 : {' · '.join(sorted(손빨강))}"
            if 손빨강 else "")
    본것 = [이름 for 이름, x in 고름.items() if x.get("headSha") == 여기]
    도는것 = [이름 for 이름, x in 고름.items() if not (x.get("conclusion") or "")]
    if 본것 and len(본것) == len(고름):
        if 도는것:
            return 0, f"  이 커밋을 CI 가 도는 중 — {' · '.join(sorted(i or 'CI' for i in 도는것))}" + 손말
        return 0, f"  이 커밋을 CI 가 초록으로 봤다 — 워크플로 {len(본것)} 전부" + 손말
    안본것 = sorted(i or "CI" for i in 고름 if i not in 본것)
    끝말 = f"아직 안 본 워크플로 : {' · '.join(안본것)} (각자 마지막 판은 초록)"
    if 본것:
        끝말 = f"이 커밋은 {' · '.join(sorted(i or 'CI' for i in 본것))} 가 초록 · " + 끝말
    return 0, f"  이 커밋({여기[:7]})을 CI 가 아직 안 봤다 — 밀기 전이면 정상이다\n    {끝말}" + 손말


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--branch", default="main")
    a = ap.parse_args(argv)

    판 = 판들(a.branch)
    if isinstance(판, str):
        print(f"  ✗ CI 를 못 봤다 — {판}", file=sys.stderr)
        return 1
    if not 판:
        print(f"  ✗ CI 를 못 봤다 — {a.branch} 에 판이 없다\n"
              f"    밀고 나서 본다 : git push && sleep 60 && python3 tools/ci_status.py\n"
              f"    판 목록 : gh run list -b {a.branch} -L 5", file=sys.stderr)
        return 1
    코드, 말 = 고른다(판, 지금_커밋())
    print(말, file=sys.stderr if 코드 else sys.stdout)
    return 코드


if __name__ == "__main__":
    # ★ 위반(1)과 도구 고장(2)을 다른 코드로 끝낸다(DECISIONS §21 · §232). 같은 코드면
    #   **도구가 깨진 것을 검사가 실패한 것으로 읽는다**
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        print("    ✗ 도구가 깨졌다 — 위 역추적이 자리를 든다\n"
              "      고치고 다시 돌린다 : bash tools/verify.sh", file=sys.stderr)
        sys.exit(2)
