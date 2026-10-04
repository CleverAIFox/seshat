r"""**결과 문서가 든 수에 근거가 있는가**(DECISIONS §235).

  python3 tools/check_numbers.py            # 근거 없는 수가 있으면 1
  python3 tools/check_numbers.py --list     # 어느 줄의 어느 수인지 찍는다

★ `docs/related.md` 는 **결과를 요약하는 문서**다 — 수를 **만들지 않고 옮겨 적는다.** 그런데
  옮겨 적는 일에는 강제자가 없었다. `+0.0739` 를 `+0.0793` 으로 잘못 치면 **아무도 안 운다.**
★ **파이어레인의 `docnum_check` 를 여기 맞춘 것이다**(파이어레인 MASTER 의 「문서 숫자 대조」).
  거기는 산출물에서 **다시 세어** 대조하는데, 이 저장소의 수는 레이크의 판에서 나므로 **clone 직후에
  다시 셀 수가 없다.** 그래서 대신 **「근거 문서에 같은 수가 있는가」** 를 본다 — 옮겨 적기의 오타와
  **근거 없이 결과 문서에만 사는 수**를 잡는다.
★ **뜻이 맞는지는 안 본다.** 같은 수가 딴 자리에 있으면 통과한다 — 이 자는 **옮겨 적기**만 본다.
  어느 절의 수인지까지 묶으면 거짓 양성이 문서를 비틀게 만든다(파이어레인 §233 과 같은 판단).
★ **한쪽만 본다.** 「문서에 있는 수가 근거에 있나」 는 보고, 「근거의 수가 문서에 있나」 는 **안 본다** —
  결과 문서는 요약이라 안 싣는 것이 정상이다. 파이어레인은 `RETIRED` 로 반대쪽도 보지만
  **여기서는 안 만든다**(DECISIONS §239 · §241). 그쪽에는 폐기 목록이 **실물로** 있고 여기는 없다 —
  이 저장소의 폐기값은 **git 이력**이고, 그것을 손 목록으로 옮기면 **안 쓰는 검사 하나를 위해
  장부 하나를 평생 손으로 든다.**
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
문서 = "docs/related.md"
# 근거가 사는 자리. **늘리는 것이지 줄이는 것이 아니다**
근거 = ("docs/DECISIONS.md", "docs/hypotheses.md", "docs/MASTER.md",
        "data/scoreboard.toml")
수꼴 = re.compile(r"\d+\.\d{3,5}")
# ★ arXiv 번호는 수가 아니라 이름이다 — `2310.0582` 를 지표로 읽으면 논문 표가 전부 걸린다
아닌것 = re.compile(r"arXiv[\s:]*\d+\.\d+|\d{4}\.\d{4,5}\)")


def _근거글(root: pathlib.Path) -> str:
    return "\n".join((root / f).read_text(encoding="utf-8") for f in 근거 if (root / f).is_file())


def 근거없는수(root: pathlib.Path | None = None) -> list[tuple[int, str, str]]:
    """(줄 번호, 수, 그 줄). **근거 글 어디에도 같은 글자가 없는 수**만 든다."""
    root = root or ROOT
    글 = _근거글(root)
    out = []
    for n, 줄 in enumerate((root / 문서).read_text(encoding="utf-8").splitlines(), 1):
        가린 = 아닌것.sub(" ", 줄)
        for m in 수꼴.finditer(가린):
            if m.group(0) not in 글:
                out.append((n, m.group(0), 줄.strip()[:90]))
    return out


def _canary(root: pathlib.Path | None = None) -> None:
    """★ **아무것도 못 찾는 자와 고장 난 자는 구별되지 않는다.** 판별식이 살아 있는지 묻는다."""
    글 = _근거글(root or ROOT)
    if len(수꼴.findall((root or ROOT).joinpath(문서).read_text(encoding="utf-8"))) < 20:
        print("    ★ 카나리아가 죽었다 — 결과 문서에 수가 스무 개도 없다")
        sys.exit(2)
    if "0.9543" not in 글:                 # 기록판의 수가 근거 글에 안 잡히면 대장을 못 읽은 것이다
        print("    ★ 카나리아가 죽었다 — 근거 글이 기록판을 안 든다")
        sys.exit(2)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    _canary()
    없 = 근거없는수()
    if "--list" in args or 없:
        for n, 수, 줄 in 없:
            print(f"    {문서}:{n} 의 `{수}` 가 근거에 없다 — {줄}")
    if 없:
        print(f"    ✗ 근거 없는 수 {len(없)} — **결과 문서는 수를 만들지 않는다**(DECISIONS §235)\n"
              f"      그 수를 낸 판의 절에 적는다 : docs/DECISIONS.md\n"
              f"      옮겨 적기가 틀렸으면 고친다 : {문서}\n"
              f"      무엇을 보는지 다시 본다 : python3 tools/check_numbers.py --list", file=sys.stderr)
        return 1
    print(f"  결과 문서의 수 {len(수꼴.findall((ROOT / 문서).read_text(encoding='utf-8')))} — 전부 근거가 있다")
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
