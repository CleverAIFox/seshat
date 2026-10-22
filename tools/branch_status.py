"""**민 가지가 PR 없이 떠 있는가**(DECISIONS §315).

  python3 tools/branch_status.py          고아 가지가 있으면 1
  python3 tools/branch_status.py --list   무엇을 묻는지 찍는다
  python3 tools/branch_status.py --selftest  판별식이 살아 있나

★ **2026-10-19 에 `papers` 가 가지를 밀고 PR 을 못 열었다.** 가지는 남고 PR 은 없는 채로
  사흘을 앉아 있었다. 아무도 안 아팠다 — **그 반쯤 된 상태를 보는 자가 없었기 때문**이다.
  세샤트에서 세 번째로 같은 꼴이다(§206 · §312 와 한 집안).
★ **까닭을 안 묻는다.** API 가 왜 튀었는지는 다음에 또 다를 수 있다. 이 자는 **남은 꼴**만
  본다 — 그래서 **까닭이 바뀌어도 운다.** 까닭을 아는 고침보다 이쪽이 오래 산다.
★ **밖 — 가지가 왜 생겼는지는 안 본다.** 손으로 민 `papers/*` 도 똑같이 운다. 그게 맞다 —
  그 이름은 봇의 것이고, 사람이 그 이름을 쓰면 그것부터 틀렸다.
★ **밖 — `papers/` 밖의 가지는 안 본다.** 일하는 가지는 PR 없이 떠 있는 것이 정상이다.
  넓히면 매일 울고, **매일 우는 검사는 꺼진다**(hathor GR-0.8).
★ **밖 — 승인 대기는 적되 안 막는다.** 봇 PR 의 CI 가 사람 승인을 기다리는 것은 **저장소
  설정**이지 결함이 아니다. 자리는 적고 종료 코드는 안 건드린다.
★ **밖 — PR 의 내용은 안 본다.** 열려 있나만 본다. 합칠 값이 있는지는 읽는 사람이 판정한다.
★ **못 보는 것은 통과가 아니다**(§59). `gh` 가 없거나 로그인이 안 됐으면 **2** 로 끝난다.

  0  이상 없음
  1  고아 가지 · 그 PR 의 CI 가 빨강
  2  못 봤다 (도구 · 로그인 · API)
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys

#: 보는 가지 이름의 머리. **봇이 만드는 것만 본다** — 넓히면 소음이 된다
감시 = "papers/"
#: 빨강으로 안 세는 결론. 빈 것은 **도는 중**이고 아직 판정이 아니다
초록 = ("", "success", "skipped", "neutral")
#: **결함이 아니라 설정**이다 — 적되 안 막는다
대기결론 = "action_required"


def _부른다(args: list[str]) -> tuple[int, str, str]:
    r = subprocess.run(args, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def _최신판(판: list[dict]) -> list[dict]:
    """워크플로마다 **가장 최근 판 하나**. 옛 빨강이 새 초록을 이기면 안 된다(§292 와 같은 말)."""
    고름: dict[str, dict] = {}
    for x in sorted(판, key=lambda d: d.get("createdAt") or "", reverse=True):
        고름.setdefault(x.get("workflowName") or "", x)
    return list(고름.values())


def 판정(가지: list[str], PR표: dict[str, int],
         판표: dict[str, list[dict]]) -> tuple[int, list[str]]:
    """(종료 코드, 할 말). **판정의 자리는 여기 하나다** — 시험이 이 함수를 직접 부른다.

    `가지` 는 원격 가지 이름 전부, `PR표` 는 **열린** PR 의 `머리가지 → 번호`,
    `판표` 는 가지마다의 최근 판들이다. **셋 다 밖에서 받는다** — 이 함수는 망을 안 탄다.
    """
    고아, 빨강, 대기 = [], [], []
    for br in sorted(set(가지)):
        if not br.startswith(감시):
            continue
        번호 = PR표.get(br)
        if 번호 is None:
            고아.append(br)
            continue
        for x in _최신판(판표.get(br, [])):
            결론 = (x.get("conclusion") or "").lower()
            if 결론 == 대기결론:
                대기.append((br, 번호, x))
            elif 결론 not in 초록:
                빨강.append((br, 번호, x))
    말 = []
    for br in 고아:
        말.append(f"  ✗ **{br} 가 PR 없이 떠 있다** — 가지는 밀렸는데 PR 이 안 열렸다.\n"
                  f"    건질 것이 있나 먼저 본다 : "
                  f"git diff origin/main...origin/{br}\n"
                  f"    없으면 지운다 : git push origin --delete {br}")
    for br, n, x in 빨강:
        말.append(f"  ✗ **{br} 의 PR #{n} 에서 "
                  f"{x.get('workflowName') or 'CI'} 가 "
                  f"{(x.get('conclusion') or '').lower()}** — {x.get('url', '')}")
    for br, n, x in 대기:
        말.append(f"  ※ {br} 의 PR #{n} 은 **사람 승인을 기다린다**(`{대기결론}`) — "
                  f"안 막는다.\n    그 화면에서 **Approve and run** 을 누르거나, "
                  f"저장소 설정의 워크플로 승인을 푼다.\n    {x.get('url', '')}")
    if not 말:
        본것 = sum(1 for b in 가지 if b.startswith(감시))
        말 = [f"  {감시}* 가지 {본것} — 떠 있는 반쪽이 없다"]
    return (1 if (고아 or 빨강) else 0), 말


def 가지를_받는다(부른다=None) -> list[str] | str:
    """원격 가지 이름들, 또는 **왜 못 봤는지**를 적은 글."""
    부른다 = 부른다 or _부른다
    rc, out, err = 부른다(["gh", "api", "repos/{owner}/{repo}/branches",
                          "--paginate", "--jq", ".[].name"])
    if rc != 0:
        return f"`gh api branches` 가 {rc} 로 죽었다 — {(err or out).strip()[:200]}"
    return [x.strip() for x in out.splitlines() if x.strip()]


def PR을_받는다(부른다=None) -> dict[str, int] | str:
    """**열린** PR 의 `머리가지 → 번호`. 닫힌 것은 안 센다 — 닫힌 PR 은 떠 있는 가지를 안 설명한다."""
    부른다 = 부른다 or _부른다
    rc, out, err = 부른다(["gh", "pr", "list", "--state", "open", "--limit", "100",
                          "--json", "number,headRefName"])
    if rc != 0:
        return f"`gh pr list` 가 {rc} 로 죽었다 — {(err or out).strip()[:200]}"
    try:
        목록 = json.loads(out or "[]")
    except json.JSONDecodeError as e:
        return f"`gh pr list` 의 답을 못 읽었다 — {e}"
    return {d["headRefName"]: d["number"] for d in 목록}


def 판을_받는다(가지: str, 부른다=None) -> list[dict] | str:
    """그 가지의 최근 판들. `ci_status.py` 와 같은 질의 꼴이다."""
    부른다 = 부른다 or _부른다
    rc, out, err = 부른다(["gh", "run", "list", "--branch", 가지, "--limit", "20",
                          "--json", "conclusion,status,workflowName,url,createdAt"])
    if rc != 0:
        return f"`gh run list --branch {가지}` 가 {rc} 로 죽었다 — {(err or out).strip()[:200]}"
    try:
        return json.loads(out or "[]")
    except json.JSONDecodeError as e:
        return f"`gh run list` 의 답을 못 읽었다 — {e}"


def _죽었다(왜: str) -> None:
    print(f"    ★ 카나리아가 죽었다 — {왜}", file=sys.stderr)
    sys.exit(2)


def _canary() -> None:
    """**0건이 목표인 검사는 0건을 성공으로만 읽으면 안 된다**(MASTER §0-8).

    합성으로 넷을 묻는다 — 고아를 잡나 · 빨강을 잡나 · **승인 대기로는 안 막나** ·
    `papers/` 밖을 안 잡나. 셋째가 이 자의 눈금이다(GR-0.8).
    """
    def 판(결론: str) -> dict:
        return {"conclusion": 결론, "workflowName": "ci", "url": "u",
                "createdAt": "2026-10-22T00:00:00Z"}
    if 판정(["papers/2026-10-19"], {}, {})[0] != 1:
        _죽었다("PR 없는 가지를 안 잡는다")
    if 판정(["papers/x"], {"papers/x": 2}, {"papers/x": [판("failure")]})[0] != 1:
        _죽었다("PR 의 빨강을 안 잡는다")
    코드, 말 = 판정(["papers/x"], {"papers/x": 2}, {"papers/x": [판(대기결론)]})
    if 코드 != 0:
        _죽었다("승인 대기로 막는다 — 매주 울면 사람이 검사를 끈다")
    if not any("승인" in m for m in 말):
        _죽었다("승인 대기를 조용히 삼킨다")
    if 판정(["main", "feature/x", "papers/x"], {"papers/x": 1}, {})[0] != 0:
        _죽었다("멀쩡한 나무를 잡는다")
    if 판정(["feature/고아"], {}, {})[0] != 0:
        _죽었다(f"`{감시}` 밖의 가지를 잡는다 — 그러면 매일 운다")
    # ★ **옛 빨강이 새 초록을 이기면 안 된다**(§292 가 적은 그것).
    둘 = [{"conclusion": "failure", "workflowName": "ci", "url": "u",
           "createdAt": "2026-10-20T00:00:00Z"},
          {"conclusion": "success", "workflowName": "ci", "url": "u",
           "createdAt": "2026-10-22T00:00:00Z"}]
    if 판정(["papers/x"], {"papers/x": 2}, {"papers/x": 둘})[0] != 0:
        _죽었다("워크플로의 옛 판을 판정에 쓴다")


def main(argv: list[str] | None = None) -> int:
    a = sys.argv[1:] if argv is None else argv
    _canary()
    if "--selftest" in a:
        print(f"  프로브 살아 있다 — 합성 일곱으로 묻는다 · 보는 가지는 `{감시}*`")
        return 0
    if "--list" in a:
        print(f"  보는 가지 `{감시}*` · 초록으로 세는 결론 {초록} · 안 막는 결론 `{대기결론}`")
        print("  묻는 것 : gh api branches · gh pr list --state open · gh run list --branch")
        return 0
    if not shutil.which("gh"):
        print("  `gh` 가 없다 — `sudo apt install gh && gh auth login`. "
              "**못 보는 것은 통과가 아니다**", file=sys.stderr)
        return 2
    가지 = 가지를_받는다()
    if isinstance(가지, str):
        print(f"  {가지}", file=sys.stderr)
        return 2
    PR표 = PR을_받는다()
    if isinstance(PR표, str):
        print(f"  {PR표}", file=sys.stderr)
        return 2
    판표: dict[str, list[dict]] = {}
    for br in 가지:
        if br.startswith(감시) and br in PR표:
            판 = 판을_받는다(br)
            if isinstance(판, str):
                print(f"  {판}", file=sys.stderr)
                return 2
            판표[br] = 판
    코드, 말 = 판정(가지, PR표, 판표)
    for m in 말:
        print(m, file=sys.stderr if 코드 else sys.stdout)
    return 코드


if __name__ == "__main__":
    # ★ 위반(1)과 못 봄(2)을 다른 코드로 끝낸다(DECISIONS §21 · §232)
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        print("    ✗ 도구가 깨졌다 — 위 역추적이 자리를 든다\n"
              "      고치고 다시 돌린다 : python3 tools/branch_status.py --selftest",
              file=sys.stderr)
        sys.exit(2)
