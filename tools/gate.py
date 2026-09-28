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
★ **문은 맞바꿈을 못 정한다.** 한 지표가 크게 오르고 다른 지표가 조금 떨어지는 판은 **사람이 정한다** —
  `--accept "<까닭>"` 이 그것이다. 까닭 없이는 안 받는다. 받은 것은 기록판에 **떨어진 지표와 함께**
  남고, 다음 판부터 그 새 값이 선이 된다(DECISIONS §155).
★ **자가 바뀌면 막는다.** 채점 코드가 바뀌면 `metrics` 판이 올라가고, 판이 다른 두 수는 **다른 것을
  잰 수**다(DECISIONS §145). 사전이 바뀌는 것과 다르다 — 사전은 같은 것을 더 잘 재는 일이다.
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

# ★ **기록판은 반올림해서 든다** — 읽으라고 만든 파일이라 16자리를 적지 않는다. 그러면 **견줄 때도
#   같은 자리에서 견뎌야 한다.** 2026-09-28, 쓸 때만 반올림하고 견줄 때는 안 해서 `0.9771689…` 가
#   자기가 세운 기록 `0.9772` 보다 작았다 — **승격한 팔이 다시 돌리면 무조건 막혔다**(DECISIONS §144).
자리 = 4


def 재(v):
    """기록판에 적히는 그대로의 수. 없으면 없는 대로 둔다 — 못 잰 것은 0 이 아니다."""
    return round(float(v), 자리) if isinstance(v, (int, float)) and not isinstance(v, bool) else v


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
    if not rec.get("metrics"):
        (말 if pin else 막).append(
            "기록에 **자 판**이 없다"
            + (" — 이번 실행으로 박는다" if pin else
               " — 채점 코드가 바뀌었을 수 있다. `tools/rescore.py` 로 기준을 다시 재고 `--update` 로 박는다"))
        return 막, 말
    if head.get("metrics") != rec["metrics"]:
        막.append(f"**자가 바뀌었다** — 기록 판 {rec['metrics']} · 이번 판 {head.get('metrics')}\n"
                  f"    사전이 바뀐 것과 다르다(§32 · §96). 사전은 **같은 것을 더 잘 재는** 일이고\n"
                  f"    자가 바뀌는 것은 **다른 것을 재는** 일이다. `tools/rescore.py` 로 기준을 다시 잰다")
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
        # **기록판에 적히는 자리에서 견준다.** 안 그러면 반올림이 올라간 값이 자기 기록에 막힌다
        옛, 새 = 재(rec.get(m)), 재(head.get(m))
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


def 올릴_것(rec: dict, head: dict, pin: bool = False, 받음: bool = False) -> dict[str, float]:
    """올라간 지표만. **떨어진 것을 기록판에 쓰지 않는다** — 기록판은 최고를 든다.

    ★ `pin` — 셋 해시를 처음 박는 판에서는 **있는 값을 그대로 적는다.** 그 기록은 아직 어느 셋의
      것인지 몰랐으므로 「올랐다 · 내렸다」 를 말할 수 없다. 견주기는 다음 판부터다.
    ★ **자가 바뀌면 올리는 것이 아니라 다시 박는 것이다**(DECISIONS §146). 재채점은 값을 **내리는**
      일이 잦은데, 오른 것만 쓰면 기록판이 **「새 자」 라고 적힌 채 옛 자로 잰 수**를 든다 —
      거짓말이 박힌다. 판이 다르면 견주지 않고 **그대로 옮긴다.**
    """
    # ★ **받아들인 판은 떨어진 값도 박는다**(DECISIONS §155). 안 박으면 기록판이 옛 선을 든 채로
    #   남고 **다음 판이 같은 자리에서 또 막힌다** — 사람이 한 번 정한 것을 매번 다시 정하게 된다
    처음 = 받음 or (pin and (not rec.get("set_sha256") or rec.get("metrics") != head.get("metrics")))
    out = {}
    for m in (*rec.get("guard", []), "term_off", "lit", "keep", "style"):
        새 = 재(head.get(m))
        # **오른 것도 같은 자리에서 본다** — 0.00001 짜리 「상승」 을 기록하면 다음 판이 그것에 막힌다
        if isinstance(새, (int, float)) and (처음 or rec.get(m) is None or 새 > 재(rec[m])):
            out[m] = 새
    return out


def _쓴다(run: str, rec: dict, head: dict, 오른: dict, path: pathlib.Path | None = None,
          받은: str = "") -> None:
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
            "metrics": head.get("metrics", ""),
            "arm": head.get("backend") or head.get("model") or rec["arm"],
            "date": dt.date.today().isoformat(),
            **({"accepted": 받은} if 받은 else {})}
    for i in range(시작, 끝):
        k = 줄[i].split("=", 1)[0].strip()
        if k in 새값:
            v = 새값.pop(k)
            # ★ **주석의 자리를 지킨다.** 이 파일은 주석이 절반이고 세로로 맞춰 읽는다 —
            #   2026-09-28 한 줄을 고쳐 쓰면서 `#` 앞 공백을 두 칸으로 뭉개 이어지는 주석 줄과
            #   어긋나게 만들었다. 고쳐 쓰는 도구가 **읽는 모양을 망가뜨리면 안 된다**
            앞, _, 뒤 = 줄[i].partition("#")
            새줄 = f"{k} = {json.dumps(v, ensure_ascii=False)}"
            줄[i] = (새줄 + " " * max(1, len(앞) - len(새줄)) + "#" + 뒤) if 뒤 else 새줄
    # ★ **없는 키는 만든다.** 종전에는 있는 줄만 고쳐 썼다 — 그래서 새로 생긴 `metrics` 가 영영
    #   안 박히고 문이 매번 「기록에 자 판이 없다」 로 막았다(DECISIONS §145 · §143 과 같은 얼굴).
    if 새값:
        뒤 = max(i for i in range(시작, 끝) if 줄[i].strip())      # 블록의 마지막 알맹이 줄
        줄[뒤 + 1:뒤 + 1] = [f"{k} = {json.dumps(v, ensure_ascii=False)}" for k, v in 새값.items()]
    path.write_text("\n".join(줄) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run", nargs="?")
    ap.add_argument("--arm", help="기록판의 어느 팔과 견주는가. 안 주면 머리줄의 backend 를 쓴다")
    ap.add_argument("--update", action="store_true", help="올라간 지표만 기록판에 쓴다")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--require", action="store_true", help="기록판에 없는 팔이면 멈춘다")
    ap.add_argument("--accept", metavar="까닭",
                    help="떨어진 지표를 **사람이 받아들인다**. 까닭을 적어야 한다 — 문은 맞바꿈을 못 정한다")
    a = ap.parse_args(argv)
    board = load()
    if a.show or not a.run:
        for r in board.get("record", []):
            print(f"  최고  {r['arm']:<40} {r.get('note', '')}")
            print(f"        {' · '.join(f'{m} {r[m]}' for m in r.get('guard', []) if m in r)}  ({r.get('run', '?')})")
        for t in board.get("target", []):
            자 = "" if t.get("metrics") else "   ※ 자 판이 없다 — 다시 재기 전에는 차를 못 찍는다"
            print(f"  선    {t['arm']:<40} {t.get('note', '')}")
            print(f"        term_off {t.get('term_off')} · lit {t.get('lit')}  ({t.get('run', '?')}){자}")
        return 0

    head = head_of(a.run)
    rec = 고른다(board, head, a.arm, a.require)
    if rec is None:
        print(f"  기록판에 없는 팔 — 문이 볼 것이 없다 ({head.get('backend') or head.get('model')})")
        return 0
    막, 말 = check(rec, head, pin=a.update)
    for x in 말:
        print(f"  ※ {x}")
    # ★ 받아들이는 것은 **떨어진 지표**뿐이다. 셋 · 사전 · 자가 다른 것은 못 받는다 — 그것은
    #   맞바꿈이 아니라 **다른 것을 잰 것**이다(§145 · §147)
    받을수있나 = all("떨어졌다" in x for x in 막)
    받은 = ""
    if 막 and a.accept and 받을수있나:
        if not a.accept.strip():
            raise SystemExit("`--accept` 에 까닭이 비었다 — 까닭 없는 받아들임은 문을 끈 것이다")
        받은 = a.accept.strip()
        print(f"\n  ⚠ **사람이 받아들였다** — {받은}", file=sys.stderr)
        for x in 막:
            print(f"      받은 것 : {x.splitlines()[0]}", file=sys.stderr)
        막 = []
    elif 막 and a.accept:
        print("  ✗ 이것은 맞바꿈이 아니다 — 셋 · 사전 · 자가 다르면 못 받는다", file=sys.stderr)
    for x in 막:
        print(f"  ✗ {x}", file=sys.stderr)
    if 막:
        print(f"\n  문이 막았다 — {pathlib.Path(a.run).name}", file=sys.stderr)
        return 1
    오른 = 올릴_것(rec, head, pin=a.update, 받음=bool(받은))
    def _값(m):
        v = head.get(m)
        return f"{v:.4f}" if isinstance(v, float) else str(v)
    print("  통과 — " + " · ".join(f"{m} {_값(m)}" for m in rec.get("guard", [])))
    for t in board.get("target", []):
        if t.get("set") != rec.get("set"):
            continue
        # ★ **선도 같은 자로 잰 것이어야 한다**(DECISIONS §147). 2026-09-28, 자를 바꾼 뒤에도 이 줄이
        #   새 수와 옛 수의 차를 찍고 있었다 — **비교를 거절하는 도구가 스스로 섞어 재고 있었다.**
        if t.get("metrics") != head.get("metrics"):
            print(f"  선    {t['arm']:<40} **다른 자로 잰 선이다** — 기록 판 {t.get('metrics') or '없다'} · "
                  f"이번 판 {head.get('metrics')}. 차를 안 찍는다. `tools/rescore.py` 로 그 판을 다시 잰다")
            continue
        남 = {m: round(t[m] - head[m], 4) for m in ("term_off", "lit") if m in t and head.get(m) is not None}
        print(f"  선까지 {t['arm']:<40} " + " · ".join(f"{m} {v:+.4f}" for m, v in 남.items()))
    if 오른 and (a.update or 받은):
        _쓴다(a.run, rec, head, 오른, 받은=받은)
        print(f"  기록판을 고쳤다 — {' · '.join(f'{m} → {v}' for m, v in 오른.items())}")
    elif 오른:
        print(f"  올라간 것 {' · '.join(f'{m} {v}' for m, v in 오른.items())} — `--update` 가 기록한다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
