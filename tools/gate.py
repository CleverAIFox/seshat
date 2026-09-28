"""회귀를 막는 문 — 새 결과가 **지금까지의 최고**보다 떨어졌으면 멈춘다(DECISIONS §131).

  python3 tools/gate.py runs/X.jsonl                 막는가 보기만
  python3 tools/gate.py runs/X.jsonl --update        올라갔으면 기록판을 고쳐 쓴다
  python3 tools/gate.py --show                       기록판과 넘어야 할 선

★ **지금까지 회귀를 막는 것이 아무것도 없었다.** 판정은 전부 사람 눈이었고, 사람은 좋아진 줄만 본다.
  기록판(`data/scoreboard.toml`)이 최고를 들고 이 도구가 그보다 떨어진 실행을 빨갛게 만든다.
★ **`guard` 에 적은 지표만 막는다.** 여섯을 다 막으면 잡음에 막히고, 곧 아무도 안 본다.
★ **셋이 다르면 비교하지 않는다.** `set_sha256` 이 다르거나 비어 있으면 **멈춘다** — 다른 자로 잰
  두 수를 견주면 그 비교가 거짓말이다(`compare_runs` 와 같은 규율 · DECISIONS §45).
★ **사전이 바뀌면 막지 않고 말한다.** 사전을 고치면 같은 번역의 점수가 바뀐다(§32 · §96). 그것을
  회귀로 읽으면 사전을 영영 못 고친다 — 재채점으로 기준을 다시 박으라고 이른다.
★ **못 재면 0 이 아니다.** 결과에 그 지표가 없으면 「통과」 가 아니라 빨간불이다(§110 과 같은 규율).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from seshat import catalog  # noqa: E402

PATH = ROOT / "data/scoreboard.toml"


def load(path: pathlib.Path | None = None) -> dict:
    """★ **기본값을 `PATH` 로 묶지 않는다.** 기본 인자는 import 할 때 한 번 값이 박히므로,
    시험이 `PATH` 를 바꿔도 이 함수는 옛 자리를 본다 — 2026-09-27 그래서 시험이 **진짜 기록판을
    덮어썼다**(DECISIONS §132). 자리는 부를 때 고른다."""
    return tomllib.loads((path or PATH).read_text(encoding="utf-8"))


def head_of(run: str) -> dict:
    for line in pathlib.Path(run).read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            if d.get("meta"):
                return d
    raise SystemExit(f"{pathlib.Path(run).name} 에 머리줄이 없다 — 재현 조건 없는 파일은 안 받는다")


def 고른다(board: dict, head: dict, arm: str | None, 꼭: bool = False) -> dict | None:
    """어느 기록과 견줄 것인가. **팔로 고른다** — 팔이 다르면 견줄 대상이 아니다.

    ★ **기록판에 없는 팔은 막지 않는다.** 실험 팔은 판마다 새로 생기고, 그것까지 막으면 가설을
      세울 때마다 문이 빨개진다. **문이 지키는 것은 서빙 후보 하나**다 — 기록판이 그 이름을 든다.
      `꼭` 은 「이 실행은 후보여야 한다」 고 부를 때다.
    """
    이름 = arm or head.get("backend") or head.get("model") or ""
    맞 = [r for r in board.get("record", []) if r["arm"] == 이름]
    if not 맞 and 꼭:
        raise SystemExit(f"기록판에 팔 {이름!r} 이 없다 — 견줄 대상이 없으면 문이 할 일이 없다\n"
                         f"    기록판의 팔 : {' · '.join(r['arm'] for r in board.get('record', [])) or '없다'}\n"
                         f"    후보가 바뀌었으면 기록판에 줄을 더한다")
    return 맞[0] if 맞 else None


def check(rec: dict, head: dict, pin: bool = False) -> tuple[list[str], list[str]]:
    """(막는 것, 말만 하는 것). **비었으면 통과다.**

    ★ `pin` 은 `--update` 로 부를 때다. 셋 해시가 아직 없는 기록은 **박으러 온 것**이지 어긴 것이
      아니다 — 막으면 박을 길이 없다(닭과 달걀). 2026-09-27 첫 실행이 여기서 막혔다.
    """
    막, 말 = [], []
    if not rec.get("set_sha256"):
        (말 if pin else 막).append(
            "기록에 셋 해시가 없다" + (" — 이번 실행으로 박는다" if pin else " — `--update` 로 박는다. 짐작으로 견주지 않는다"))
        return 막, 말
    if head.get("set_sha256") != rec["set_sha256"]:
        막.append(f"셋이 다르다 — 기록 {rec['set_sha256']} · 이번 {head.get('set_sha256')}\n"
                  f"    다른 자로 잰 두 수를 견주지 않는다. 같은 셋으로 다시 재거나 기록을 다시 박는다")
        return 막, 말
    if rec.get("onto_sha256") and head.get("onto_sha256") != rec["onto_sha256"]:
        말.append(f"사전이 바뀌었다 — 기록 {rec['onto_sha256']} · 이번 {head.get('onto_sha256')}. "
                  f"**막지 않는다**(DECISIONS §32 · §96). 기준을 `rescore` 로 다시 박는다")
    tol = float(rec.get("tol", 0.0))
    for m in rec.get("guard", []):
        옛, 새 = rec.get(m), head.get(m)
        if 옛 is None:
            말.append(f"{m}: 기록에 없다 — 이번 값 {새}")
            continue
        if 새 is None:
            막.append(f"{m}: 이번 결과에 없다 — **못 잰 것은 통과가 아니다**")
            continue
        if 새 < 옛 - tol:
            막.append(f"{m}: {새:.4f} < {옛:.4f} (허용 {tol}) — 떨어졌다")
        elif 새 < 옛:
            말.append(f"{m}: {새:.4f} < {옛:.4f} 이지만 허용 {tol} 안이다")
    return 막, 말


def 올릴_것(rec: dict, head: dict, pin: bool = False) -> dict[str, float]:
    """올라간 지표만. **떨어진 것을 기록판에 쓰지 않는다** — 기록판은 최고를 든다.

    ★ `pin` — 셋 해시를 처음 박는 판에서는 **있는 값을 그대로 적는다.** 그 기록은 아직 어느 셋의
      것인지 몰랐으므로 「올랐다 · 내렸다」 를 말할 수 없다. 견주기는 다음 판부터다.
    """
    처음 = pin and not rec.get("set_sha256")
    out = {}
    for m in (*rec.get("guard", []), "term_off", "lit", "keep", "style"):
        새 = head.get(m)
        if isinstance(새, (int, float)) and (처음 or rec.get(m) is None or 새 > rec[m]):
            out[m] = round(float(새), 4)
    return out


def _쓴다(run: str, rec: dict, head: dict, 오른: dict, path: pathlib.Path | None = None) -> None:
    """**한 줄씩 고쳐 쓴다.** TOML 을 다시 찍으면 주석이 사라지는데, 이 파일은 주석이 절반이다.

    ★ **이름과 날짜도 같이 고친다.** 2026-09-28, 숫자만 고치고 `arm` 을 안 고쳤더니 기록판이
      **자기가 안 든 팔의 숫자**를 들었다. 그러면 다음 판에서 `--arm` 없이 부를 때 머리줄의 새 팔로
      찾다가 「기록판에 없는 팔」 로 **통과**한다 — **승격하는 순간 문이 서빙 후보를 안 지킨다**
      (DECISIONS §143). `--update` 는 「이 실행을 기록으로 삼는다」 는 뜻이고, 그러면 그 실행의
      팔이 기록의 팔이다.
    """
    path = path or PATH          # import 때 안 묶는다 — 위의 `load` 와 같은 까닭
    catalog.gate(path)
    줄 = path.read_text(encoding="utf-8").splitlines()
    시작 = next(i for i, x in enumerate(줄) if x.strip() == "[[record]]"
                and any(f'arm = "{rec["arm"]}"' == y.strip() for y in 줄[i:i + 12]))
    끝 = next((i for i in range(시작 + 1, len(줄)) if 줄[i].startswith("[[")), len(줄))
    새값 = {**오른, "set_sha256": head.get("set_sha256", ""), "commit": head.get("commit", ""),
            "onto_sha256": head.get("onto_sha256", ""), "run": pathlib.Path(run).stem,
            "arm": head.get("backend") or head.get("model") or rec["arm"],
            "date": dt.date.today().isoformat()}
    for i in range(시작, 끝):
        k = 줄[i].split("=", 1)[0].strip()
        if k in 새값:
            v = 새값.pop(k)
            꼬리 = ("  " + 줄[i].split("#", 1)[1].join(("#", ""))) if "#" in 줄[i] else ""
            줄[i] = f"{k} = {json.dumps(v, ensure_ascii=False)}" + 꼬리
    path.write_text("\n".join(줄) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run", nargs="?")
    ap.add_argument("--arm", help="기록판의 어느 팔과 견주는가. 안 주면 머리줄의 backend 를 쓴다")
    ap.add_argument("--update", action="store_true", help="올라간 지표만 기록판에 쓴다")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--require", action="store_true", help="기록판에 없는 팔이면 멈춘다")
    a = ap.parse_args(argv)
    board = load()
    if a.show or not a.run:
        for r in board.get("record", []):
            print(f"  최고  {r['arm']:<40} {r.get('note', '')}")
            print(f"        {' · '.join(f'{m} {r[m]}' for m in r.get('guard', []) if m in r)}  ({r.get('run', '?')})")
        for t in board.get("target", []):
            print(f"  선    {t['arm']:<40} {t.get('note', '')}")
            print(f"        term_off {t.get('term_off')} · lit {t.get('lit')}  ({t.get('run', '?')})")
        return 0

    head = head_of(a.run)
    rec = 고른다(board, head, a.arm, a.require)
    if rec is None:
        print(f"  기록판에 없는 팔 — 문이 볼 것이 없다 ({head.get('backend') or head.get('model')})")
        return 0
    막, 말 = check(rec, head, pin=a.update)
    for x in 말:
        print(f"  ※ {x}")
    for x in 막:
        print(f"  ✗ {x}", file=sys.stderr)
    if 막:
        print(f"\n  문이 막았다 — {pathlib.Path(a.run).name}", file=sys.stderr)
        return 1
    오른 = 올릴_것(rec, head, pin=a.update)
    def _값(m):
        v = head.get(m)
        return f"{v:.4f}" if isinstance(v, float) else str(v)
    print("  통과 — " + " · ".join(f"{m} {_값(m)}" for m in rec.get("guard", [])))
    for t in board.get("target", []):
        if t.get("set") == rec.get("set"):
            남 = {m: round(t[m] - head[m], 4) for m in ("term_off", "lit") if m in t and head.get(m) is not None}
            print(f"  선까지 {t['arm']:<40} " + " · ".join(f"{m} {v:+.4f}" for m, v in 남.items()))
    if 오른 and a.update:
        _쓴다(a.run, rec, head, 오른)
        print(f"  기록판을 고쳤다 — {' · '.join(f'{m} → {v}' for m, v in 오른.items())}")
    elif 오른:
        print(f"  올라간 것 {' · '.join(f'{m} {v}' for m, v in 오른.items())} — `--update` 가 기록한다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
