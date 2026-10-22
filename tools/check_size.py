"""파일이 **배치마다 조금씩** 늘어 아무도 「내가 늘렸다」 를 안 느끼는 자리.

  python3 tools/check_size.py            검사한다. 위반이면 1, 도구 고장이면 2
  python3 tools/check_size.py --update   지금 수로 고친 예외표를 찍는다(쓰지는 않는다)
  python3 tools/check_size.py --list     지금 큰 것부터 찍는다

★ 이 파일은 **seshat 것**이다 — thoth 사본이 아니다(DECISIONS §5).
★ 파이어레인 `tools/sizecheck.py` 에서 옮겼다(DECISIONS §286). 그쪽 머리말이 적은 병은
  이것이다 — **한 배치가 20줄씩 늘리면 어느 배치도 자기가 늘렸다고 느끼지 않는다.**
  그리고 **느슨해진 래칫은 초록으로 위장한다** — 그래서 **양방향**이다.

## 무엇을 보나

| | |
|---|---|
| 예외에 없는 파일 | `상한`(600줄)을 넘으면 운다 |
| 예외에 있는 파일 | 선언한 수와 **정확히** 같아야 한다 — 늘어도 **줄어도** 운다 |
| 예외에 있는데 없는 파일 | 죽은 예외다. 지운다 |

★ **줄어도 우는 까닭.** 줄인 뒤에 선언을 안 내리면 그만큼 다시 늘 자리가 생긴다 —
  그 자리는 아무에게도 안 보인다. **라쳇은 조이는 쪽으로만 움직인다**(파이어레인 `ratchet.py`).

★ **600 은 지어낸 수가 아니라 분포에서 골랐다.** 2026-10-03 실측 — 파일 119 중
  400 넘는 것 11 · 500 넘는 것 9 · **600 넘는 것 6** · 700 넘는 것 5. 600 에서 예외표가
  여섯으로 작게 서고, 그 여섯이 실제로 읽기 힘든 파일들이다.

★ 밖 — **파일이 커도 되는지는 안 본다.** `tools/labels.py` 1,064줄이 쪼개져야 하는가는
  사람이 판단한다. 여기가 드는 것은 **그 수가 오늘보다 커졌는가** 하나다.
★ 밖 — **함수 길이 · 복잡도는 안 본다.** 한 파일에 짧은 함수 백 개가 있는 것과 긴 함수
  하나가 있는 것을 **안 가른다.** 그쪽은 `ruff` 의 `C901` 이 볼 자리이고 지금은 안 켠다
  (DECISIONS §283 — 켜면 25건이고 전부 문체다).
★ 밖 — **thoth 사본은 세되 못 고친다.** `tools/doc_fsck.py` 처럼 머리 세 줄에 「사본이다」 를
  단 파일은 thoth 에서 고치고 다시 복사한다(§5). 여기 예외표에 오르면 **그 사실이 보인다.**
  ★ 보기를 `tools/check_docs.py` 로 적어 뒀는데 **그 파일은 사본이 아니다**(DECISIONS §296).
    ★ **그런데 이 줄이 「재 봤다」 고 적은 것이 거짓이었다**(DECISIONS §318). 그 파일은
      2026-10-22 까지 **머리에 그 말을 달고 있었다** — 즉 재지 않았거나 다른 것을 쟀다.
      실제로 재 보니 거기에만 있는 함수 **7(84줄)** · 길이가 갈린 함수 **5** 이고 `# seshat:`
      표시는 7줄이었다. **사본이 아니라는 결론은 맞았고 근거가 거짓이었다** — 그 딱지가
      `check_prose` 의 맨 절 검사를 그 파일에서 **통째로 꺼 두고 있었다.**

  0  이상 없음
  1  위반
  2  도구 고장
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: 넘으면 우는 줄 수. 분포에서 골랐다(머리말).
상한 = 600

#: **지금 넘는 것.** 실측과 정확히 같아야 한다 — 늘어도 줄어도 운다.
#:
#: ★ 2026-10-03 실측. 쪼갤지 말지는 사람이 정한다(`PLAN #51`) — 이 표는 **더 늘지 않게** 할 뿐이다.
#: ★ `tests/` 가 셋이다. 시험이 긴 것은 도구가 긴 것보다 덜 나쁘지만 **안 가른다** —
#:   가르기 시작하면 「이건 시험이니까」 가 면제의 이름이 된다.
#: ★ `tools/check_docs.py` 는 **사본이 아니다**(DECISIONS §318 이 재서 머리를 고쳤다) — 여기 오른 까닭은 길어서다. thoth 에서 `_본문_줄`
#:   과 `본문_수정` 을 옮겨 오며 600 을 넘었다(DECISIONS §296). 쪼갤지는 `PLAN #51` 이 든다 —
#:   색인 기계(`색인_글` · `_색인을_박는다` · `check_index`)가 「문서 규약」 과 다른 일이다.
예외: dict[str, int] = {
    "tools/check_docs.py": 608,
    "tools/labels.py": 1064,
    "tests/test_labels.py": 925,
    "seshat/evaluate.py": 828,
    "tests/test_gate.py": 823,
    "seshat/backends.py": 740,
    "tests/test_evaluate.py": 695,
}


def 센다(root: Path) -> dict[str, int]:
    """git 이 아는 `.py` · `.sh` 의 줄 수. **추적된 것만** 센다.

    ★ 추적 안 된 파일은 **기계마다 있고 없다**(파이어레인 `readmecheck.py` 의 실기).
      그것을 세면 관문이 기계마다 다르게 옳다.
    """
    r = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "*.py", "*.sh"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"git ls-files 가 실패했다 — {r.stderr.strip()[:200]}")
    것 = {}
    for rel in r.stdout.split("\0"):
        if not rel:
            continue
        p = root / rel
        if not p.is_file():
            # ★ **건너뛰되 말을 한다**(DECISIONS §255). 받은 저장소에서 한글 이름이
            #   깨지면 여기가 조용히 0 이 된다 — 그러면 관문이 아무것도 안 본다.
            print(f"    ※ {rel} 이 git 에는 있는데 실물이 없다 — **이 파일은 안 셌다**",
                  file=sys.stderr)
            continue
        것[rel] = len(p.read_text(encoding="utf-8", errors="replace").splitlines())
    return 것


def 견준다(수: dict[str, int]) -> list[str]:
    """빈 리스트가 통과다. **양방향**이다 — 늘어도 줄어도 든다."""
    난것 = []
    for rel, n in sorted(수.items()):
        선언 = 예외.get(rel)
        if 선언 is None:
            if n > 상한:
                난것.append(f"{rel} 이 {n}줄로 상한 {상한} 을 넘었다 — 쪼개거나 "
                           f"`예외` 에 {n} 으로 적는다(적는 순간 라쳇이 된다)")
        elif n > 선언:
            난것.append(f"{rel} 이 {선언} → {n} 으로 늘었다 — **라쳇은 조이는 쪽으로만 움직인다**")
        elif n < 선언:
            난것.append(f"{rel} 이 {선언} → {n} 으로 줄었다 — `예외` 를 {n} 으로 내린다. "
                       f"**느슨해진 라쳇은 초록으로 위장한다**")
    for rel in sorted(예외):
        if rel not in 수:
            난것.append(f"`예외` 가 없는 {rel} 을 든다 — 죽은 예외다. 지운다")
    return 난것


def _canary() -> None:
    """★ **판별식이 살아 있는가.** 양방향 둘과 상한 하나를 합성으로 물어 둔다."""
    옛예외 = dict(예외)
    try:
        예외.clear()
        예외.update({"a.py": 100})
        probes = {
            "늘면 운다": any("늘었다" in x for x in 견준다({"a.py": 101})),
            "줄면 운다": any("줄었다" in x for x in 견준다({"a.py": 99})),
            "같으면 조용하다": 견준다({"a.py": 100}) == [],
            "예외 밖이 상한을 넘으면 운다": any("넘었다" in x for x in 견준다({"a.py": 100, "b.py": 상한 + 1})),
            "예외 밖이 상한 안이면 조용하다": 견준다({"a.py": 100, "b.py": 상한}) == [],
            "죽은 예외를 든다": any("죽은 예외" in x for x in 견준다({})),
        }
    finally:
        예외.clear()
        예외.update(옛예외)
    죽은 = [k for k, ok in probes.items() if not ok]
    if 죽은:
        print(f"    ★ 카나리아가 죽었다 — {죽은}. 검사가 아무것도 못 찾는 상태다")
        sys.exit(2)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    _canary()
    수 = 센다(ROOT)
    if "--list" in args:
        for rel, n in sorted(수.items(), key=lambda x: -x[1])[:20]:
            print(f"  {n:>6}  {rel}")
        return 0
    if "--update" in args:
        큰 = {r: n for r, n in 수.items() if n > 상한}
        print("예외: dict[str, int] = {")
        for rel, n in sorted(큰.items(), key=lambda x: -x[1]):
            print(f'    "{rel}": {n},')
        print("}")
        print(f"  지금 {상한} 을 넘는 것 {len(큰)} · 적힌 것 {len(예외)}", file=sys.stderr)
        return 0
    난것 = 견준다(수)
    for x in 난것:
        print(f"    {x}")
    if not 난것:
        print(f"  파일 {len(수)} · 상한 {상한} 을 넘는 것 {len(예외)} — 전부 선언한 수와 같다")
    return 1 if 난것 else 0


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
