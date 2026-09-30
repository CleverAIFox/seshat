r"""**문서가 드는 수를 도구가 채운다**(DECISIONS §237).

  python3 tools/docgen.py            # 문서의 수가 실측과 다르면 1 ← 기본
  python3 tools/docgen.py --fix      # 문서의 수를 실측으로 갈아 넣는다

★ **울기만 하는 검사는 사람을 갈리게 한다.** 2026-09-30 하루에 PLAN #47 의 수를 손으로 **네 번**
  고쳤고, 그러고도 **행 머리의 수는 100 에 멈춰 있었다**(꼬리만 고쳤다). 파이어레인이 같은 자리에서
  같은 답을 냈다 — **문서가 수를 안 들게 하는 것이 처방이다**(파이어레인 `tools/docgen.py`).
★ **고치는 자리는 좁게, 보는 자리는 넓게.** 여기가 고치는 것은 **축마다 정확히 한 자리**다. 문서의
  나머지 수는 `tools/check_numbers.py` 가 근거와 대조한다(§235) — 두 도구가 다른 일을 한다.
★ **앵커가 한 번만 잡혀야 한다.** 0 곳이면 「문서가 그 말을 안 한다」 이고 두 곳 이상이면 **어느
  쪽이 정본인지 모른다** — 둘 다 실패다. 파이어레인의 「블록이 표기를 0곳 찾으면 실패」 와 같은 판단:
  **못 찾은 초록은 「깨끗하다」 가 아니라 「안 봤다」 다.**
★ **정본이 죽으면 실패한다.** 감사가 절을 하나도 안 보면 0 이 나오는데, 그 0 은 「다 갚았다」 가
  아니라 **「못 셌다」** 다.
★ **`--fix` 는 사람이 부른다.** 관문은 대조만 한다 — 관문이 문서를 고치면 **무엇이 바뀌었는지
  사람이 모른다**(파이어레인이 같은 이유로 `--check` 만 CI 에 건다).
"""
from __future__ import annotations

import importlib.util
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _도구(이름: str):
    """`tools/<이름>.py` 를 모듈로 든다 — `tools/` 는 꾸러미가 아니다."""
    spec = importlib.util.spec_from_file_location(이름, ROOT / f"tools/{이름}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


단계 = re.compile(r"^\| ?[①-⑤][^|]*\|\s*(\d+)%\s*\|\s*\*{0,2}(\d+)%\*{0,2}\s*\|", re.M)


def 진행률() -> int:
    """MASTER §15 의 합. **표가 정본이고 합은 그 표에서 나온다** — 손으로 곱해 더하지 않는다."""
    글 = (ROOT / "docs/now/MASTER.md").read_text(encoding="utf-8")
    칸 = 단계.findall(글)
    if len(칸) < 3:
        raise SystemExit(f"정본이 죽었다 — MASTER §15 의 단계 표에서 {len(칸)} 줄만 읽혔다\n"
                         "    표를 본다 : sed -n '/## 15\\./,/^\\*\\*합/p' docs/now/MASTER.md")
    if sum(int(w) for w, _ in 칸) != 100:
        raise SystemExit(f"정본이 죽었다 — 비중의 합이 {sum(int(w) for w, _ in 칸)}% 다(100 이어야 한다)\n"
                         "    비중은 한 번 적고 안 흔든다 : docs/now/MASTER.md §15")
    # ★ **내림이다. 반올림이 아니다**(DECISIONS §237). 2026-09-30 참값이 35.5 였고 반올림하면 36 이
    #   된다 — **진행률은 과장되는 쪽으로 틀리면 안 된다.** 어느 쪽으로 깎을지를 도구가 정해 두지
    #   않으면 적는 사람이 그때그때 고르고, 고르는 쪽은 늘 높은 쪽이다
    return int(sum(int(w) * int(v) for w, v in 칸) / 100)


# (정본, 어느 파일, 앵커 — 수를 든 무리가 하나여야 한다)
#
# ★ **커밋이 흔드는 수는 여기 못 들어온다**(DECISIONS §238). `docseal audit` 의 수를 축으로 세웠다가
#   물렸다 — 그 수는 **절의 날짜와 파일의 마지막 커밋 날짜**를 견주므로, 그 수를 적는 커밋이 파일을
#   건드리면서 수를 바꾼다. **고정점이 한 커밋 안에 없다.** 채워 넣을 수 있는 수는 **커밋이 안 흔드는
#   수**이고, 흔드는 수는 문서에 안 적고 도구가 물을 때마다 센다.
축 = {
    "진행률": (진행률, "docs/now/MASTER.md", re.compile(r"(?<=\*\*합 )(\d+)(?=%\*\*)")),
}


def 견준다() -> list[tuple[str, int, int]]:
    """(축, 문서의 수, 실측). **안 맞는 것만** 든다. 앵커가 한 번 안 잡히면 멈춘다."""
    안맞 = []
    for 이름, (정본, 자리, 앵커) in 축.items():
        글 = (ROOT / 자리).read_text(encoding="utf-8")
        잡힌 = 앵커.findall(글)
        if len(잡힌) != 1:
            raise SystemExit(f"{이름}: 앵커가 {자리} 에서 {len(잡힌)} 곳 잡혔다 — 하나여야 한다\n"
                             f"    0 곳이면 문서가 그 말을 안 하는 것이고, 둘 이상이면 정본이 둘이다\n"
                             f"    표기를 고치거나 축을 고친다 : tools/docgen.py 의 `축`")
        참 = 정본()
        if int(잡힌[0]) != 참:
            안맞.append((이름, int(잡힌[0]), 참))
    return 안맞


def 고친다() -> list[tuple[str, int, int]]:
    바뀐 = 견준다()
    for 이름, _, 참 in 바뀐:
        _, 자리, 앵커 = 축[이름]
        p = ROOT / 자리
        p.write_text(앵커.sub(str(참), p.read_text(encoding="utf-8")), encoding="utf-8")
    return 바뀐


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "--fix" in args:
        바뀐 = 고친다()
        for 이름, 옛, 새 in 바뀐:
            print(f"  {이름}  {옛} → {새}")
        print(f"  고친 축 {len(바뀐)} / {len(축)}")
        return 0
    안맞 = 견준다()
    for 이름, 문서수, 참 in 안맞:
        _, 자리, _ = 축[이름]
        print(f"    ✗ {이름}: {자리} 는 {문서수} 라 하고 실측은 {참} 다", file=sys.stderr)
    if 안맞:
        print("      도구가 채운다 : python3 tools/docgen.py --fix", file=sys.stderr)
        return 1
    print(f"  문서가 드는 수 {len(축)} — 전부 실측과 같다")
    return 0


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
