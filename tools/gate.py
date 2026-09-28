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
★ **기계가 지킨 수와 모델이 지킨 수를 견주지 않는다.** 자리표시로 보호하는 팔의 `lit`·`ui` 는
  **파이프라인이 만든 1.0** 이고, 보호가 없는 팔의 같은 지표는 **모델이 지킨 값**이다. 자 판도 셋도
  같으니 위의 검사가 다 통과한다 — `protects` 칸이 그것을 든다(DECISIONS §156).
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
from seshat import catalog, compare  # noqa: E402

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


def 지금_자() -> str:
    """**코드가 지금 쓰는 자.** 기록판이 낡은 것을 문이 스스로 알아야 한다(DECISIONS §162)."""
    from seshat import evaluate
    return evaluate.METRICS_VER


def check(rec: dict, head: dict, pin: bool = False, 지금: str | None = None) -> tuple[list[str], list[str]]:
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
    # ★ **기록판이 낡았는지를 문이 스스로 본다**(DECISIONS §162). 2026-09-28 자를 3 으로 올렸는데
    #   기록판도 그 실행도 2 라 **둘이 같아서 통과했다** — 문은 두 산출물끼리만 견주고 지금 코드의
    #   자는 안 봤다. 낡은 기록으로 내리는 모든 판정이 옛 자의 판정이다
    지금 = 지금 or 지금_자()
    if not pin and rec.get("metrics") and rec["metrics"] != 지금:
        막.append(f"**기록판이 낡았다** — 기록의 자 {rec['metrics']} · 지금 코드의 자 {지금}\n"
                  f"    이 기록으로 내리는 판정은 옛 자의 판정이다. `tools/rescore.py` 로 다시 재고\n"
                  f"    `--update` 로 박는다(실험 상태의 가설이 있어야 한다)")
        return 막, 말
    # ★ **축은 `seshat/compare.py` 하나에만 적는다**(DECISIONS §157)
    # ★ **박으러 온 판에서 자 바뀜은 막지 않는다**(DECISIONS §165). 「재채점하고 `--update` 로
    #   박아라」 고 이르면서 박을 길을 막으면 §144 의 닭과 달걀이 그대로 되풀이된다. 셋은 여전히
    #   막는다 — 다른 글로 잰 수를 기록으로 삼으면 그 기록이 거짓말한다
    for g in compare.갈림(rec, head, compare.GATE_막):
        if pin and g.키 == "metrics":
            말.append(g.글() + " — **이번 실행으로 다시 박는다**")
            continue
        막.append(g.글())
        return 막, 말
    if rec.get("onto_sha256"):
        for x in compare.갈림(rec, head, ("onto_sha256",)):
            말.append(x.글() + " — `rescore` 로 기준을 다시 박는다")
    # ★ **분모가 갈린 두 수는 높낮이를 말할 수 없다**(DECISIONS §169). 2026-09-28 문이 스스로
    #   「자가 바뀌었다 · 사전이 바뀌었다」 를 찍고 **바로 다음 줄에서 그 수로 막았다** —
    #   0.9532(982자리 · 자 3)를 0.9559(674자리 · 자 2)와 견줘서. `올릴_것` 은 이것을 이미
    #   알고 있었고(§146) `check` 만 몰랐다 — **같은 판단이 두 곳에 있으면 한 곳만 고쳐진다**(§163).
    #   박으러 온 판에서만 넘긴다. 그냥 돌린 판은 위의 「기록판이 낡았다」 가 이미 막았다
    갈린분모 = compare.갈림(rec, head, compare.분모) if pin else []
    if 갈린분모:
        말.append("**분모가 갈렸다 — 지킴을 안 본다**("
                  + " · ".join(compare.AXIS[g.키].이름 for g in 갈린분모) + ")\n"
                  "    높낮이를 말할 수 없는 두 수다. 이번 실행의 값을 **그대로 옮긴다** —\n"
                  "    다음 판부터 이 수가 선이 된다(DECISIONS §169)")
        return 막, 말
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
    # ★ **`check` 와 같은 물음을 같은 곳에 던진다**(DECISIONS §169). 2026-09-28 까지 여기만
    #   `metrics` 를 보고 `check` 는 아무것도 안 봐서, 문이 막는 판과 문이 쓰는 판이 **서로 다른
    #   기준**으로 돌았다. `compare.분모` 가 그 물음의 유일한 자리다 — 사전도 분모를 바꾼다(§166)
    처음 = 받음 or (pin and (not rec.get("set_sha256")
                            or bool(compare.갈림(rec, head, compare.분모))))
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
    새값 = {**오른, "set_sha256": head.get("set_sha256", ""), "commit": head.get("commit", ""),
            "onto_sha256": head.get("onto_sha256", ""), "run": pathlib.Path(run).stem,
            "metrics": head.get("metrics", ""),
            "arm": head.get("backend") or head.get("model") or rec["arm"],
            "date": dt.date.today().isoformat(),
            **({"accepted": 받은} if 받은 else {})}
    _블록을_고친다("record", rec["arm"], 새값, path)


def _블록을_고친다(표: str, arm: str, 새값: dict, path: pathlib.Path | None = None) -> None:
    """`[[표]]` 중 `arm` 이 맞는 블록의 칸을 고쳐 쓴다. **기록판을 고치는 유일한 자리다.**

    ★ **선 줄도 같은 길로 고친다**(DECISIONS §170). 손으로 고치면 기록판이 금지한 바로 그것 —
      **짐작으로 채우기** — 이 된다. 선 줄을 고치는 코드를 따로 적으면 §169 가 그대로 되풀이된다.
    """
    path = path or PATH          # import 때 안 묶는다 — 위의 `load` 와 같은 까닭
    catalog.gate(path)
    줄 = path.read_text(encoding="utf-8").splitlines()
    시작 = next(i for i, x in enumerate(줄) if x.strip() == f"[[{표}]]"
                and any(f'arm = "{arm}"' == y.strip() for y in 줄[i:i + 12]))
    끝 = next((i for i in range(시작 + 1, len(줄)) if 줄[i].startswith("[[")), len(줄))
    남은 = dict(새값)
    for i in range(시작, 끝):
        k = 줄[i].split("=", 1)[0].strip()
        if k in 남은:
            v = 남은.pop(k)
            # ★ **주석의 자리를 지킨다.** 이 파일은 주석이 절반이고 세로로 맞춰 읽는다 —
            #   2026-09-28 한 줄을 고쳐 쓰면서 `#` 앞 공백을 두 칸으로 뭉개 이어지는 주석 줄과
            #   어긋나게 만들었다. 고쳐 쓰는 도구가 **읽는 모양을 망가뜨리면 안 된다**
            앞, _, 뒤 = 줄[i].partition("#")
            새줄 = f"{k} = {json.dumps(v, ensure_ascii=False)}"
            줄[i] = (새줄 + " " * max(1, len(앞) - len(새줄)) + "#" + 뒤) if 뒤 else 새줄
    # ★ **없는 키는 만든다.** 종전에는 있는 줄만 고쳐 썼다 — 그래서 새로 생긴 `metrics` 가 영영
    #   안 박히고 문이 매번 「기록에 자 판이 없다」 로 막았다(DECISIONS §145 · §143 과 같은 얼굴).
    if 남은:
        뒤 = max(i for i in range(시작, 끝) if 줄[i].strip())      # 블록의 마지막 알맹이 줄
        줄[뒤 + 1:뒤 + 1] = [f"{k} = {json.dumps(v, ensure_ascii=False)}" for k, v in 남은.items()]
    path.write_text("\n".join(줄) + "\n", encoding="utf-8")


def _선을_박는다(run: str | None, arm: str, board: dict) -> int:
    """**선 줄을 이 판의 값으로 다시 박는다**(DECISIONS §171 · §169).

    ★ **선은 지킴이 아니다.** 기록은 「넘지 말아야 할 내 최고」 이고 선은 「넘어야 할 남의 값」 이다 —
      올랐는지 내렸는지를 안 묻고 **그 판의 값을 그대로 옮긴다.** 선이 내려가는 것은 나쁜 일이 아니라
      **남을 다시 잰 것**이다.
    ★ **손으로 고치는 길을 막으려고 만들었다.** 기록판이 첫 줄부터 「짐작으로 채우지 않는다」 라고
      적어 놓고 선 줄만은 손으로 고치고 있었다 — 2026-09-28 선 둘이 자 2 · 옛 사전인 채로 남아
      §166 의 잘못된 비교를 만들었다.
    ★ **셋이 다르면 안 박는다.** 그것은 다시 잰 것이 아니라 **딴 글로 잰 것**이다.
    """
    if not run:
        print("  ✗ 어느 판으로 박을지가 없다", file=sys.stderr)
        return 1
    head = head_of(run)
    t = next((x for x in board.get("target", []) if x.get("arm") == arm), None)
    if t is None:
        있는 = " · ".join(x.get("arm", "?") for x in board.get("target", []))
        print(f"  ✗ 선 줄에 그런 팔이 없다 — {arm}\n    있는 것 : {있는}", file=sys.stderr)
        return 1
    if t.get("set") != head.get("set"):
        print(f"  ✗ 셋이 다르다 — 선 {t.get('set')} · 이번 {head.get('set')}", file=sys.stderr)
        return 1
    값 = {m: 재(head[m]) for m in ("term_off", "lit", "ui", "term_bad", "keep", "style")
          if isinstance(head.get(m), (int, float))}
    새값 = {**값, "run": pathlib.Path(run).stem, "metrics": head.get("metrics", ""),
            "onto_sha256": head.get("onto_sha256", ""), "onto_score": head.get("onto_score", ""),
            "date": dt.date.today().isoformat(),
            **({"protects": list(head["protects"])} if head.get("protects") else {})}
    _블록을_고친다("target", arm, 새값)
    print(f"  선을 다시 박았다 — {arm}\n    " +
          " · ".join(f"{m} {v}" for m, v in 값.items()))
    print(f"    자 {head.get('metrics')} · 사전 {head.get('onto_score') or head.get('onto_sha256')} · "
          f"{pathlib.Path(run).stem}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run", nargs="?")
    ap.add_argument("--arm", help="기록판의 어느 팔과 견주는가. 안 주면 머리줄의 backend 를 쓴다")
    ap.add_argument("--update", action="store_true", help="올라간 지표만 기록판에 쓴다")
    ap.add_argument("--show", action="store_true")
    ap.add_argument("--require", action="store_true", help="기록판에 없는 팔이면 멈춘다")
    ap.add_argument("--accept", metavar="까닭",
                    help="떨어진 지표를 **사람이 받아들인다**. 까닭을 적어야 한다 — 문은 맞바꿈을 못 정한다")
    ap.add_argument("--pin-target", metavar="팔",
                    help="이 판으로 **선 줄**을 다시 박는다. 손으로 고치면 짐작으로 채우게 된다")
    a = ap.parse_args(argv)
    board = load()
    if a.pin_target:
        return _선을_박는다(a.run, a.pin_target, board)
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
        # ★ **사전도 분모를 바꾼다**(DECISIONS §169). 이 줄이 `metrics` 만 보던 동안 `term_n` 674 로
        #   잰 선과 982 로 잰 이번 값의 차를 찍고 있었다 — §147 을 고칠 때 축을 하나만 적은 탓이다
        다른자 = compare.갈림(t, head, compare.분모)
        if 다른자:
            print(f"  선    {t['arm']:<40} **분모가 다른 선이다**({다른자[0].이름}) — 선 "
                  f"{다른자[0].가 or '없다'} · 이번 {다른자[0].나}. 차를 안 찍는다. "
                  f"`tools/rescore.py` 로 그 판을 다시 잰다")
            continue
        # ★ **보호가 다르면 그 지표는 안 찍는다**(DECISIONS §156). 기계가 지킨 0.993 과 모델이 지킨
        #   0.9225 를 견주면 「넘었다」 가 거짓이 된다 — 자도 셋도 같아서 위의 검사가 다 통과한다
        못볼것 = compare.가린_지표(rec, t)
        남 = {m: round(t[m] - head[m], 4) for m in ("term_off", "lit")
              if m in t and head.get(m) is not None and m not in 못볼것}
        print(f"  선까지 {t['arm']:<40} " + " · ".join(f"{m} {v:+.4f}" for m, v in 남.items()))
        가린 = sorted(못볼것 & {"term_off", "lit"})
        if 가린:
            print(f"        ※ **{' · '.join(가린)} 는 안 찍는다** — 이쪽은 자리표시가 지키고 "
                  f"저쪽은 모델이 지킨다. 같은 처치를 걸고 다시 재야 견준다(§156)")
    if 오른 and (a.update or 받은):
        _쓴다(a.run, rec, head, 오른, 받은=받은)
        print(f"  기록판을 고쳤다 — {' · '.join(f'{m} → {v}' for m, v in 오른.items())}")
    elif 오른:
        print(f"  올라간 것 {' · '.join(f'{m} {v}' for m, v in 오른.items())} — `--update` 가 기록한다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
