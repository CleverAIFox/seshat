"""사람이 줄마다 내리는 판정 — 눈가림으로 받고 다시 붙인다(DECISIONS §98 · H-046).

  python3 tools/labels.py make --set data/domain/d001.jsonl --a <A결과> --b <B결과> --n 60
  python3 tools/labels.py make --set … --arm 4b=<결과> --arm 12b=<결과> --arm nova=<결과>   # 팔 여럿
  # → /tmp/labels-<이름>.tsv (채점표) · labels/<이름>.key.jsonl (열쇠 · git 밖)
  python3 tools/labels.py read --name d001-60 --judge claude    # 채운 표를 읽어 판정과 비율을 낸다
  python3 tools/labels.py agree --name d001-60 --judges gpt,gemini,pplx   # 쌍마다 카파
  python3 tools/labels.py gap  --name d001-60 --judges gpt,gemini,pplx --arm 4b --vs 12b
  python3 tools/labels.py prompt > /tmp/judge.txt    # 다른 판정자에게 줄 지시문

★ **「뜻이 맞다」 비율 둘을 눈으로 견주는 것은 선이 아니다**(DECISIONS §226). 그것은 §139 · §178 ·
  §179 · §216 이 네 번 저지른 **손으로 그은 선**이다. `gap` 이 `tools/bootstrap.py` 의 **짝지은
  재표집**을 그대로 불러 구간과 p 를 낸다 — 재는 법을 두 곳에 안 적는다(DECISIONS §163).
★ **판정자 여럿은 줄마다 평균 낸다.** 셋이면 한 줄의 값이 0 · ⅓ · ⅔ · 1 이고, 재표집은 **줄**을
  뽑는다 — 판정자를 뽑지 않는다(셋으로는 아무것도 못 말한다). **하나를 빼도 부호가 유지되는지**를
  같이 내지만 그것은 **관측이지 판정 기준이 아니다**(DECISIONS §216).
★ **판정자는 여럿이다.** 한 명의 판정을 자로 쓰면 앞으로 그 자로 검증하는 모든 지표가 「그 판정자와
  얼마나 맞나」 를 재게 된다. `--judge` 가 판정자마다 파일을 나누고 `agree` 가 일치율과 카파를 낸다.
  **일치하지 않는 줄이 기준이 무른 자리**다 — 거기서 기준을 좁힌다.
★ **판정자는 교사가 아니다.** 판정은 평가에만 쓰고 학습 데이터로 넘기지 않는다. 그래서 가중치 대장의
  교사 가부(`seshat/licenses.py`)가 판정자를 가리지 않는다 — 학습에 쓰려면 그때 대장을 본다.
★ **판정자는 한 번에 하나씩 받는다**(DECISIONS §108). 앞선 판정을 본 뒤에 매기면 카파가 높아도
  일치가 아니라 베끼기이고, **안 봤다고 증명할 수 없다.** 오염된 판정은 레이크에 넣지 않는다.
★ **눈가림이다.** 채점표는 어느 팔의 출력인지 적지 않는다. 알면 큰 모델에 후하게 준다 — 사람이
  정직하지 않아서가 아니라 **기대가 채점을 민다.** 팔 이름은 열쇠 파일에만 있고, `read` 가 붙인다.
★ **줄을 먼저 뽑고 출력을 나중에 본다.** seed 로 뽑으므로 무엇이 나올지 모르는 채로 표본이 정해진다.
  보고 고르면 그 표본이 결론이다(DECISIONS §86 이 같은 잘못을 적는다).
★ **판정은 셋이다.** `맞다`(뜻이 통한다) · `어긋난다`(뜻이 틀렸거나 지어냈다) · `아니다`(번역이 아니다).
  표기가 공식이 아닌 것은 **맞다** 다 — `term_off` 가 이미 그것을 센다. 여기서 재는 것은 **뜻**이다.
★ **아무것도 커밋되지 않는다.** 채점표는 `/tmp` 에, 판정은 작업대 `labels/`(git 밖)에 나고
  **레이크에는 `lake.py put raw --into labels labels/*.jsonl` 로 넣는다** — `runs/` 와 같은 모양이다.
  저장소가 드는 것은 **인사이트**뿐이다 — 숫자와 배운 것은 DECISIONS 가, 판정 규칙은 이 파일이 든다
  (DECISIONS §103). 판정 파일에도 원문과 출력은 없다. 줄 id · 팔 · 판정뿐이다.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from seshat import catalog, evaluate  # noqa: E402


def _도구(이름: str):
    """`tools/<이름>.py` 를 모듈로 든다. 이 저장소는 `tools/` 를 꾸러미로 안 만든다 —
    `seshat/evaluate.py` 가 `check_hypotheses` 를 드는 것과 같은 꼴이다."""
    spec = importlib.util.spec_from_file_location(이름, ROOT / f"tools/{이름}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

# ★ **판정은 근거다. 근거는 레이크에 산다**(MASTER §11 · DECISIONS §103). 저장소에는 사람이 고치는
#   작은 정본과 문서만 둔다 — `runs/` 를 저장소에 안 넣는 것과 같은 규칙이다.
# ★ **작업대에 쓰고 레이크에는 `put` 으로 넣는다.** `raw` 는 해시 대장이 지키는 층이라 도구가 직접
#   쓰면 대장 밖 파일이 된다(`lake.py check` 가 짚는다). `evaluate.py` 가 `runs/` 에 쓰고 사람이
#   `lake.py put runs` 로 넣는 것과 같은 모양이다. 이 자리는 git 이 무시한다.
def out_dir() -> pathlib.Path:
    d = ROOT / "labels"
    d.mkdir(parents=True, exist_ok=True)
    catalog.gate(d)                 # 작업대도 선언 안에 있어야 한다(DECISIONS §121)
    return d


def _짧게(p: pathlib.Path) -> str:
    """저장소 안이면 상대 경로로, 밖이면 그대로. 시험이 임시 폴더를 써도 안 죽는다."""
    return str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
VERDICTS = ("맞다", "어긋난다", "아니다")
HEAD = ("표", "원문", "번역", "판정(맞다 · 어긋난다 · 아니다)")


def read_run(path: pathlib.Path) -> tuple[dict, dict[str, str]]:
    """결과 파일 → (머리줄, id → 출력). 줄 id 가 없는 옛 파일은 거절한다."""
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    head, body = rows[0], rows[1:]
    out = {}
    for i, r in enumerate(body):
        rid = r.get("id")
        if not rid:
            raise SystemExit(f"{path.name}: {i + 1}번째 줄에 id 가 없다 — 줄 id 가 있어야 짝을 짓는다\n"
                             f"    그 줄을 본다 : sed -n '{i + 2}p' {path}")
        out[rid] = r.get("out", r.get("ko", ""))
    return head, out


def tag(name: str, rid: str, arm: str) -> str:
    """채점표의 불투명한 이름. **팔을 못 읽게** 해시로 만든다."""
    return hashlib.sha256(f"{name}|{rid}|{arm}".encode()).hexdigest()[:8]


def make(arms: dict[str, pathlib.Path], rows: list[dict], name: str, n: int, seed: int) -> tuple[str, list[dict]]:
    """★ **팔이 둘일 이유가 없다**(DECISIONS §115). 기준선을 같은 표에 얹으면 세 수가 한 자에서 나온다 —
    따로 재고 나중에 견주면 표본도 판정자도 달라져 있다."""
    got, shas = {}, {}
    for arm, path in arms.items():
        h, o = read_run(path)
        got[arm], shas[arm] = o, h.get("set_sha256")
    if len(set(shas.values())) != 1:
        raise SystemExit("팔들이 다른 셋이다 — " + " · ".join(f"{a} {s}" for a, s in sorted(shas.items()))
                         + "\n    같은 셋으로 잰 판을 고른다 : ls -t runs/*.jsonl | head\n"
                           "    한쪽을 다시 잰다 : uv run --group eval python tools/rescore.py "
                           "<판> --set <셋> --hypothesis H-NNN")
    src = {r["id"]: r["src"] for r in rows}
    common = set(src)
    for o in got.values():
        common &= set(o)
    both = sorted(common)
    if len(both) < n:
        raise SystemExit(f"팔 {len(arms)} 에 다 있는 줄이 {len(both)} 뿐인데 {n} 을 달라고 했다\n"
                         f"    줄여서 뽑는다 : --n {len(both)}\n"
                         f"    같은 셋을 다 돌린 판으로 바꾼다 : ls -t runs/*.jsonl | head")
    rng = random.Random(seed)
    picked = sorted(rng.sample(both, n))          # ★ 줄을 먼저 뽑는다 — 출력을 보기 전에
    sheet, key = [], []
    for rid in picked:
        for arm in arms:
            t = tag(name, rid, arm)
            sheet.append((t, src[rid], got[arm][rid]))
            key.append({"tag": t, "id": rid, "arm": arm})
    rng.shuffle(sheet)                            # ★ 같은 줄의 팔들이 나란히 서지 않게
    lines = ["\t".join(HEAD)] + ["\t".join([t, s.replace("\t", " "), o.replace("\t", " "), ""]) for t, s, o in sheet]
    return "\n".join(lines) + "\n", key


PROMPT = """아래 표는 영어 기술 문서를 한국어로 옮긴 결과입니다. 각 줄을 셋 중 하나로 판정해 주세요.

판정
  맞다      원문의 뜻이 그대로 전달된다
  어긋난다  뜻이 틀렸거나, 원문에 없는 말을 지어냈거나, 있던 내용이 빠졌다
  아니다    번역이 아니다 (영어를 그대로 돌려줬거나, 되묻거나, 딴소리)

규칙
1. **용어 표기가 공식 표기와 달라도 뜻이 통하면 「맞다」** 입니다.
   「할당량」 대신 「쿼타」, 「레코드」 대신 「기록」, 「프로듀서」 대신 「생산자」 — 전부 맞다입니다.
   표기는 다른 자가 이미 세고 있습니다. 여기서 보는 것은 **뜻** 하나뿐입니다.
2. 문장이 어색하거나 딱딱해도 뜻이 맞으면 「맞다」 입니다. 유창함을 보지 않습니다.
3. **낱말 하나가 망가진 것만으로는 「어긋난다」 가 아닙니다.** 그 낱말이 무엇을 가리키는지
   읽는 사람이 알아볼 수 있으면 「맞다」 입니다.
     SparkMagic → 「스파크 마직」 · canned ACL → 「캔드된 ACL」 · producer → 「프로듀서」   → 전부 맞다
   알아볼 수 없게 다른 것이 되면 그때 어긋난다입니다.
     snapshot → 「캡샷」 · secondary → 「서브다큐먼트」 · shard → 「덩이」 · at rest → 「휴대폰에서」
4. **원문에 있던 조각이 빠졌거나 관계가 바뀌면 「어긋난다」 입니다.** 이쪽이 더 무겁습니다.
   - 수식어 · 조건절이 통째로 빠졌다 (보기: `that doesn't exist before the update` 가 사라졌다)
   - 관계말이 바뀌었다 (보기: `among multiple users` → 「여러 사용자**와**」)
   - 누가 무엇을 하는지가 바뀌었다 (보기: 「당신이 다시 시작할 때」 → 「그것이 다시 시작하므로」)
   - 뜻이 뒤집혔다 (보기: 「~이다」 가 「~이 아닌」 이 됐다)
   - A를 B로 바꾸라는 지시에서 A와 B가 뒤바뀌었다
   - 서로 다른 개념을 같은 것으로 합쳤다 (보기: fleet → 「리전」 · throughput → 「대역폭」)
5. 헷갈리면 이렇게 물으십시오 — **번역만 읽은 사람이 원문만 읽은 사람과 다르게 행동하거나
   다른 사실을 믿게 되는가.** 그러면 어긋난다, 아니면 맞다.
6. 여러 모델의 출력이 섞여 있고 어느 줄이 어느 모델인지는 표에 없습니다.
   **맞히려 하지 마세요.** 알 수 없게 섞은 것이 이 시험의 일부입니다.
7. **줄마다 따로 판정합니다.** 같은 원문이 표에 여러 번 나올 수 있는데, 그중 어느 것이 더
   나은지를 고르는 일이 아닙니다. **한 줄만 놓고** 원문의 뜻이 전달됐는지 봅니다.
8. **검색하지 마세요. 이 표에 있는 것만 보고 판정합니다.** 이 문서들의 공식 한국어판이 웹에
   있는데, 그것은 기계 번역에 사람 후편집을 얹은 것이라 **정답이 아닙니다.** 그것과 대조하면
   이 시험은 「그 번역과 얼마나 같은가」 가 되어 버립니다. 판정하는 것은 **원문과 번역 둘 사이**입니다.

답
  줄마다 `태그<탭>판정` 한 줄씩, 표에 나온 순서 그대로, **표에 있는 줄 수만큼**.
  설명·머리말·번호를 붙이지 마세요. 판정은 위 셋 중 하나의 글자 그대로만.

보기
  8d6722bc\t맞다
  3476df3d\t아니다
"""


def cohen_kappa(x: list[str], y: list[str]) -> float:
    """두 판정자의 일치를 **우연을 뺀 뒤** 잰다. 한쪽으로 쏠린 판정은 그냥 일치율이 높게 나온다 —
    「맞다」 만 찍어도 0.8 이 넘는다. 카파는 그 몫을 뺀다."""
    n = len(x)
    cats = sorted(set(x) | set(y))
    po = sum(a == b for a, b in zip(x, y)) / n
    pe = sum((x.count(c) / n) * (y.count(c) / n) for c in cats)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def verdict_of(cols: list[str]) -> str:
    """채점표의 판정 칸. 네 칸짜리 표(사람이 채운 것)와 두 칸짜리(태그 · 판정)를 둘 다 받는다 —
    다른 판정자는 표 전체를 돌려주지 않고 판정만 돌려준다."""
    if len(cols) >= 4:
        return cols[3].strip()
    return cols[1].strip() if len(cols) == 2 else ""


def read(name: str, sheet: pathlib.Path, judge: str = "claude", model: str = "") -> int:
    if not sheet.exists():
        raise SystemExit(f"채점표가 없다 — {sheet}\n"
                         f"    만든다 : python3 tools/labels.py make --set <셋> --a <A> --b <B>\n"
                         f"    다른 자리면 : --sheet <경로>")
    kp = out_dir() / f"{name}.key.jsonl"
    if not kp.exists():
        raise SystemExit(f"열쇠가 없다 — {_짧게(kp)}. `make` 가 채점표와 함께 낸다 (seed 가 같으면 같은 표다)")
    key = {r["tag"]: r for r in (json.loads(x) for x in kp.read_text(encoding="utf-8").splitlines() if x.strip())}
    got, blank = [], 0
    # ★ **머리줄이 있는지를 열쇠에게 묻는다**(DECISIONS §228). 예전에는 첫 줄을 **무조건** 버렸는데,
    #   판정자가 돌려주는 답에는 머리줄이 없어서 **진짜 판정 한 줄이 조용히 먹혔다.** 2026-09-30
    #   네 판정자가 전부 179/180 으로 들어왔고 `gap` 의 줄이 60 에서 59 로 줄었다
    줄 = sheet.read_text(encoding="utf-8").splitlines()
    if 줄 and 줄[0].split("\t")[0].strip() not in key:
        줄 = 줄[1:]                      # 열쇠가 모르는 첫 줄만 머리줄이다
    for ln in 줄:
        if not ln.strip():
            continue
        cols = ln.split("\t")
        t, verdict = cols[0].strip(), verdict_of(cols)
        if t in ("표", "tag"):
            continue
        if not verdict:
            blank += 1
            continue
        if verdict not in VERDICTS:
            raise SystemExit(f"{t}: 모르는 판정 {verdict!r} — {' · '.join(VERDICTS)} 중 하나다\n"
                             f"    그 줄을 고친다 : {sheet}\n"
                             f"    지시문을 다시 본다 : python3 tools/labels.py prompt")
        if t not in key:
            raise SystemExit(f"{t}: 열쇠에 없는 표 — 채점표를 바꿔 썼나\n"
                             f"    열쇠가 아는 표 : {' · '.join(sorted(key)[:5])} …\n"
                             f"    표를 다시 만든다 : python3 tools/labels.py make --set <셋> --a <A> --b <B>")
        got.append({**key[t], "verdict": verdict})
    if blank:
        print(f"  ※ 아직 안 매긴 줄 {blank}", file=sys.stderr)
    if not got:
        raise SystemExit("매긴 줄이 없다\n"
                         "    채점표의 `판정` 칸을 채우고 다시 부른다 — 빈 칸은 안 센다\n"
                         "    지시문 : python3 tools/labels.py prompt")
    path = out_dir() / f"{name}.{judge}.jsonl"
    # ★ **이름이 아니라 무엇이 판정했는지를 적는다**(DECISIONS §227). 무료 등급은 뒤의 모델을 말없이
    #   바꾸므로 `gemini` 라는 이름만으로는 **다음 달에 같은 자가 아니다.** 판정자의 조건은 능력과
    #   독립성이고(§101), 둘 다 **무엇이었는지 알아야** 물을 수 있다
    meta = {"meta": True, "about": f"{name} · 판정자 {judge} — 뜻만 본다. 표기는 term_off 가 센다(H-046)",
            "judge": judge, "model": model, "license": "자체 — 판정만 든다", "made_by": "tools/labels.py"}
    path.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in [meta, *sorted(got, key=lambda r: (r["id"], r["arm"]))]) + "\n",
                    encoding="utf-8")
    print(f"  {_짧게(path)}  {len(got)}줄 / 열쇠 {len(key)}")
    print(f"  판정자 {judge} · 모델 {model}")
    # ★ **모자란 것은 도구가 소리친다**(DECISIONS §228). 2026-09-30 「180 줄 찍히는지 보라」 고 사람에게
    #   맡겼더니 네 판정자가 전부 179 로 들어왔고 아무도 안 멈췄다. **사람 눈은 강제자가 아니다.**
    #   미리 그은 선은 표의 줄 수에 걸려 있으므로, 줄이 줄면 **선이 다른 표에 그어진다**
    빠진 = sorted(set(key) - {r["tag"] for r in got})
    if 빠진:
        print(f"  ✗ **열쇠 {len(key)} 중 {len(빠진)} 이 안 왔다** — 선은 {len(key)}줄 표에 그었다\n"
              f"    안 온 표 : {' · '.join(빠진[:10])}{' …' if len(빠진) > 10 else ''}\n"
              f"    그 줄만 다시 받아 답 파일에 덧붙이고 다시 읽는다 :\n"
              f"      python3 tools/labels.py read --name {name} --sheet {sheet} "
              f"--judge {judge} --model '{model}'\n"
              f"    그 줄을 표에서 찾는다 : grep -n '{빠진[0]}' /tmp/labels-{name}.tsv",
              file=sys.stderr)
    for arm in sorted({r["arm"] for r in got}):
        mine = [r for r in got if r["arm"] == arm]
        tally = {v: sum(1 for r in mine if r["verdict"] == v) for v in VERDICTS}
        ok = tally["맞다"] / len(mine)
        print(f"  {arm}  뜻이 맞다 {ok:.3f}  ({' · '.join(f'{v} {tally[v]}' for v in VERDICTS)})")
    return 0


def 판정들(name: str, judges: list[str]) -> dict[str, dict[tuple[str, str], str]]:
    """판정자마다 {(줄 id, 팔): 판정}. 없는 판정자는 **읽는 명령을 들고** 멈춘다."""
    got: dict[str, dict[tuple[str, str], str]] = {}
    for j in judges:
        p = out_dir() / f"{name}.{j}.jsonl"
        if not p.exists():
            raise SystemExit(f"{_짧게(p)} 가 없다\n"
                             f"    읽는다 : python3 tools/labels.py read --name {name} --judge {j} --model <무엇>\n"
                             f"    누가 있나 : ls {_짧게(out_dir())}/{name}.*.jsonl")
        got[j] = {(r["id"], r["arm"]): r["verdict"]
                  for r in (json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip())
                  if not r.get("meta")}
    return got


def 무엇이_판정했나(name: str, judges: list[str]) -> dict[str, str]:
    """판정자 이름 → 그때 적어 둔 모델. **이름은 자리이고 모델이 자다**(DECISIONS §227)."""
    out = {}
    for j in judges:
        p = out_dir() / f"{name}.{j}.jsonl"
        머리 = json.loads(p.read_text(encoding="utf-8").splitlines()[0]) if p.exists() else {}
        out[j] = (머리.get("model") or "").strip() or "**안 적혔다**"
    return out


def 판정자를_찍는다(name: str, judges: list[str]) -> None:
    """무엇이 판정했는지를 결과 위에 붙인다 — 이 줄이 없으면 수만 남고 자가 사라진다."""
    무엇 = 무엇이_판정했나(name, judges)
    print("  판정자 — " + " · ".join(f"{j}({무엇[j]})" for j in judges))
    if any("안 적혔다" in v for v in 무엇.values()):
        print("    ※ 모델을 안 적은 판정자가 있다 — 무료 등급은 뒤의 모델을 말없이 바꾼다.\n"
              f"      다시 읽는다 : python3 tools/labels.py read --name {name} --judge <이름> --model <무엇>")


def agree(name: str, judges: list[str]) -> int:   # noqa: C901
    """판정자들의 일치를 **쌍마다** 낸다. **어긋난 줄을 이름으로 든다** — 거기가 기준이 무른 자리다.

    ★ **셋 이상이어도 카파는 쌍마다다.** 여럿을 한 수로 합치는 자(Fleiss)가 있지만, **어느 둘이
      안 맞는지**를 지우면 기준을 좁힐 자리를 못 찾는다(§116 에서 움직인 쪽은 claude 하나였다).
    """
    got = 판정들(name, judges)
    판정자를_찍는다(name, judges)
    for a, b in itertools.combinations(judges, 2):
        keys = sorted(set(got[a]) & set(got[b]))
        if not keys:
            print(f"  {a} 대 {b} · **같은 줄을 안 봤다** — 같은 이름의 표를 둘 다 채운다 : "
                  f"python3 tools/labels.py read --name {name} --judge {a}")
            continue
        xs, ys = [got[a][k] for k in keys], [got[b][k] for k in keys]
        same = sum(x == y for x, y in zip(xs, ys))
        k = cohen_kappa(xs, ys)
        판정 = "자로 쓸 만하다" if k >= 0.7 else ("무르다 — 기준을 좁힌다" if k >= 0.4 else "안 맞는다 — 기준이 틀렸다")
        print(f"  {a} 대 {b} · 같은 줄 {len(keys)} · 일치 {same} ({same / len(keys):.3f}) · 카파 {k:.3f} → {판정}")
        for v in VERDICTS:
            print(f"    {v:5} {a} {xs.count(v):>3} · {b} {ys.count(v):>3}")
    # ★ **갈린 줄은 쌍마다가 아니라 한 번만 든다.** 셋이면 쌍이 셋이고, 같은 줄이 세 번 찍히면
    #   그 목록은 안 읽힌다 — 무효가 소음이 되면 안 읽히는 것과 같다(§215)
    모두 = sorted(set.intersection(*(set(got[j]) for j in judges)))
    갈림 = [k for k in 모두 if len({got[j][k] for j in judges}) > 1]
    print(f"  {len(judges)} 이 다 본 줄 {len(모두)} · 만장일치 {len(모두) - len(갈림)}"
          + (f" ({(len(모두) - len(갈림)) / len(모두):.3f})" if 모두 else ""))
    if 갈림:
        print(f"  갈린 줄 {len(갈림)}")
        for rid, arm in 갈림[:40]:
            print(f"    {rid} [{arm}]  " + " · ".join(f"{j} {got[j][(rid, arm)]}" for j in judges))
    # ★ **카파는 관측이다.** 이 수로 가설을 판정하지 않는다 — 그 잘못이 §216 이다
    print("  ※ 카파는 관측이지 판정 기준이 아니다. 팔 사이를 가르는 것은 `gap` 이다")
    return 0


def 줄점수(got: dict[str, dict[tuple[str, str], str]], 팔: str,
          ids: list[str]) -> list[tuple[float, float]]:
    """줄마다 (판정자들의 「맞다」 평균, 1.0). `bootstrap.잰다` 가 그대로 먹는 꼴이다."""
    js = list(got)
    return [(sum(got[j][(i, 팔)] == "맞다" for j in js) / len(js), 1.0) for i in ids]


def gap(name: str, arm: str, vs: str, judges: list[str], n: int = 10000, seed: int = 7) -> int:
    """**팔 둘의 「뜻이 맞다」 격차에 구간을 붙인다**(DECISIONS §226 · H-081).

    ★ 재는 법은 `tools/bootstrap.py` 의 `잰다` 하나다 — 짝지은 재표집이고 **뽑는 것은 줄**이다.
    ★ `--vs` 가 기준(12B)이고 차는 `arm - vs` 다. **양수면 `arm` 이 앞선 것**이다.
    """
    got = 판정들(name, judges)
    본줄 = set.intersection(*(set(got[j]) for j in judges))
    ids = sorted({i for i, a in 본줄 if a == arm} & {i for i, a in 본줄 if a == vs})
    if not ids:
        있는팔 = sorted({a for _, a in 본줄})
        raise SystemExit(f"판정자 {len(judges)} 이 다 본 줄 중 `{arm}` 과 `{vs}` 가 함께 있는 것이 없다\n"
                         f"    표에 있는 팔 : {' · '.join(있는팔) or '없다'}\n"
                         f"    팔 이름을 고친다 : --arm <팔> --vs <기준팔>\n"
                         f"    표를 다시 본다 : python3 tools/labels.py read --name {name} --judge {judges[0]}")
    bs = _도구("bootstrap")
    r = bs.잰다(줄점수(got, vs, ids), 줄점수(got, arm, ids), n=n, seed=seed)
    if r is None:
        raise SystemExit("재표집이 아무 판도 못 냈다 — 줄이 없다\n"
                         f"    줄을 센다 : python3 tools/labels.py agree --name {name} --judges {','.join(judges)}")
    품나 = r["아래"] <= 0 <= r["위"]
    print(f"  {name} · 줄 {len(ids)} · 판정자 {len(judges)} · 판 {r['판']}")
    판정자를_찍는다(name, judges)
    print(f"  뜻이 맞다 — {vs} {r['가']:.4f} · {arm} {r['나']:.4f}")
    print(f"  차({arm} − {vs}) {r['차']:+.4f}  [{r['아래']:+.4f}, {r['위']:+.4f}]  p={r['p']:.3f}")
    print("  판정자마다 —")
    for j in judges:
        한 = {j: got[j]}
        가, 나 = 줄점수(한, vs, ids), 줄점수(한, arm, ids)
        차 = sum(x for x, _ in 나) / len(나) - sum(x for x, _ in 가) / len(가)
        print(f"    {j:10} {vs} {sum(x for x, _ in 가) / len(가):.4f} · {arm} "
              f"{sum(x for x, _ in 나) / len(나):.4f} · 차 {차:+.4f}")
    # ★ **하나를 빼도 부호가 남나.** 이 구간은 **줄만** 재표집하므로 판정자 사이의 퍼짐을 안 본다 —
    #   그런데 §118 이 「수준은 판정자가 정한다」 를 실측했다(같은 팔에 0.883 과 0.433). 그래서 이것은
    #   구경거리가 아니라 **선의 일부**다(H-081 ③)
    뒤집힘 = []
    if len(judges) > 2:
        print("  하나를 빼면 —")
        for j in judges:
            남 = {k: v for k, v in got.items() if k != j}
            차 = (sum(x for x, _ in 줄점수(남, arm, ids)) - sum(x for x, _ in 줄점수(남, vs, ids))) / len(ids)
            같나 = (차 > 0) == (r["차"] > 0)
            if not 같나:
                뒤집힘.append(j)
            print(f"    {j} 빼고  차 {차:+.4f}" + ("" if 같나 else "  ← **부호가 뒤집힌다**"))
    앞선쪽 = arm if r["차"] > 0 else vs
    if 품나:
        말 = "**못 가른다** — 구간이 0 을 품는다"
    elif 뒤집힘:
        말 = (f"**못 가른다** — 구간은 0 을 안 품지만 {' · '.join(뒤집힘)} 없이는 부호가 뒤집힌다. "
              f"**그 판정자 없이는 말할 수 없다**")
    else:
        말 = f"**{앞선쪽} 이(가) 앞선다** — 판정자를 하나씩 빼도 부호가 남는다"
    print(f"  판정 : {말}")
    # ★ **크기는 안 옮긴다**(§118). 방향만 결과 문서로 가고, 수는 조건을 달고 쓴다
    print(f"    ※ 옮기는 것은 **방향**이다. 격차 {abs(r['차']):.4f} 는 «이 판정자들에서» 의 수다 — "
          f"판정자가 바뀌면 크기는 바뀐다(DECISIONS §118)")
    return 0


def _순위(xs: list[float]) -> list[float]:
    """**같은 값은 평균 순위를 나눠 갖는다.** 사람 점수는 판정자 넷이라 값이 다섯 개뿐이고
    (0 · ¼ · ½ · ¾ · 1) **동점이 대부분**이다 — 순위를 그냥 매기면 들어온 차례가 상관이 된다."""
    차례 = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(차례):
        j = i
        while j + 1 < len(차례) and xs[차례[j + 1]] == xs[차례[i]]:
            j += 1
        평균 = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[차례[k]] = 평균
        i = j + 1
    return r


def 스피어만(xs: list[float], ys: list[float]) -> float | None:
    """순위끼리의 피어슨. **한쪽이 전부 같은 값이면 None** — 상관이 정의되지 않는다."""
    if len(xs) < 3:
        return None
    a, b = _순위(xs), _순위(ys)
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    위 = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    아래 = (sum((x - ma) ** 2 for x in a) * sum((y - mb) ** 2 for y in b)) ** 0.5
    return None if 아래 == 0 else 위 / 아래


def 자점수(경로: pathlib.Path) -> dict[tuple[str, str], float]:
    """자가 매긴 줄별 점수. 한 줄에 `{"id": …, "arm": …, "score": …}` 다.

    ★ **자는 무엇이든 된다** — 신경망 QE · 규칙 지표 · LLM 판정. 이 도구는 **꼴만 본다.**
    ★ **점수는 클수록 좋은 쪽으로 맞춰서 낸다.** MetricX 는 [0,25] 의 **오류 점수**라 작을수록
      좋다 — 내는 쪽이 뒤집어서 적는다. 여기서 안 뒤집는 까닭은, ρ 가 음수인 것이
      **방향을 잘못 적은 것**일 수도 **자가 거꾸로 가리키는 것**일 수도 있고(§229 가 뒤엣것이다)
      **둘을 도구가 못 가르기 때문**이다. 가르는 것은 사람이다.
    """
    got: dict[tuple[str, str], float] = {}
    for n, 줄 in enumerate(경로.read_text(encoding="utf-8").splitlines(), 1):
        if not 줄.strip():
            continue
        r = json.loads(줄)
        if r.get("meta"):
            continue
        for k in ("id", "arm", "score"):
            if k not in r:
                raise SystemExit(f"{_짧게(경로)}:{n} 에 `{k}` 가 없다 — 한 줄은 "
                                 '{"id": …, "arm": …, "score": …} 다\n'
                                 f"    머리줄이면 `meta` 를 달아 둔다\n"
                                 f"    그 줄을 본다 : sed -n '{n}p' {_짧게(경로)}\n"
                                 f"    규칙 지표라면 도구가 낸다 : python3 tools/labels.py rule "
                                 f"--run <팔>=<판.jsonl> --out {_짧게(경로)}")
        got[(r["id"], r["arm"])] = float(r["score"])
    if not got:
        raise SystemExit(f"{_짧게(경로)} 에 점수가 한 줄도 없다\n"
                         f"    파일을 본다 : head -3 {_짧게(경로)}\n"
                         f"    규칙 지표라면 도구가 낸다 : python3 tools/labels.py rule "
                         f"--run <팔>=<판.jsonl> --out {_짧게(경로)}")
    return got


def 사람점수(got: dict[str, dict[tuple[str, str], str]]) -> dict[tuple[str, str], float]:
    """(줄, 팔) → 판정자들의 「맞다」 평균. **참값이다** — 자를 여기에 댄다."""
    js = list(got)
    본것 = set.intersection(*(set(got[j]) for j in js))
    return {k: sum(got[j][k] == "맞다" for j in js) / len(js) for k in 본것}


def 상관(사람: dict[tuple[str, str], float], 자: dict[tuple[str, str], float],
        키: list[tuple[str, str]], n: int, seed: int,
        기준: dict[tuple[str, str], float] | None = None) -> dict | None:
    """ρ 와 95% 구간. `기준` 을 주면 **같은 재표집에서** ρ 의 차도 낸다.

    ★ **뽑는 것은 줄이다** — 한 줄의 팔들을 같이 뽑는다. 팔을 따로 뽑으면 줄 난이도가
      잡음으로 들어온다(`bootstrap.잰다` 와 같은 규율 · DECISIONS §180).
    ★ **차를 같은 재표집에서 내는 것이 요점이다.** 따로 내면 두 구간이 겹치는지만 알 뿐,
      **한쪽이 더 낫다**를 못 말한다.
    """
    줄들 = sorted({i for i, _ in 키})
    자리 = {i: [k for k in 키 if k[0] == i] for i in 줄들}

    def 재다(뽑힌: list[str]) -> tuple[float | None, float | None]:
        ks = [k for i in 뽑힌 for k in 자리[i]]
        h = [사람[k] for k in ks]
        a = 스피어만(h, [자[k] for k in ks])
        b = 스피어만(h, [기준[k] for k in ks]) if 기준 else None
        return a, b

    관측, 관측기준 = 재다(줄들)
    if 관측 is None:
        return None
    rnd = random.Random(seed)
    ρ들, 차들 = [], []
    for _ in range(n):
        뽑힌 = [줄들[rnd.randrange(len(줄들))] for _ in 줄들]
        a, b = 재다(뽑힌)
        if a is None:
            continue
        ρ들.append(a)
        if b is not None:
            차들.append(a - b)
    if not ρ들:
        return None

    def 구간(xs: list[float]) -> tuple[float, float, float]:
        xs = sorted(xs)
        작다 = sum(1 for x in xs if x <= 0) / len(xs)
        크다 = sum(1 for x in xs if x >= 0) / len(xs)
        return (xs[int(0.025 * len(xs))], xs[min(int(0.975 * len(xs)), len(xs) - 1)],
                min(1.0, 2 * min(작다, 크다)))

    아래, 위, p = 구간(ρ들)
    난것 = {"ρ": 관측, "아래": 아래, "위": 위, "p": p, "판": len(ρ들), "쌍": len(키)}
    if 차들 and 관측기준 is not None:
        ㄷ아래, ㄷ위, ㄷp = 구간(차들)
        난것 |= {"기준ρ": 관측기준, "차": 관측 - 관측기준, "차아래": ㄷ아래, "차위": ㄷ위, "차p": ㄷp}
    return 난것


def 규칙점수(run: pathlib.Path, arm: str, metric: str, setpath: str = "") -> list[dict]:
    """규칙 지표의 **줄별** 점수 — `corr` 이 먹는 꼴로. 채점기를 그대로 부른다(§163).

    ★ **분모가 0 인 줄은 안 낸다.** 그 줄에서 이 지표는 **값이 없는 것**이지 0 이 아니다 —
      0 으로 적으면 「용어가 없는 줄」 이 「용어를 다 틀린 줄」 과 같은 자리에 선다.
      그래서 `term_off` 는 **모든 줄을 못 매긴다** — `corr` 이 몇 쌍을 빼먹었는지 찍는다.
    """
    bs = _도구("bootstrap")
    머리, got = bs.read(str(run))
    rows = evaluate.load(setpath or 머리.get("set") or "")
    rows = [r for r in rows if r["id"] in got]
    outs = [got[r["id"]].get("out", "") for r in rows]
    줄 = bs.줄별(rows, outs)
    if metric not in 줄:
        raise SystemExit(f"지표 '{metric}' 을 줄별로 못 낸다 — 있는 것 : {' · '.join(줄)}\n"
                         f"    이름을 고친다 : --metric {sorted(줄)[0]}")
    난것 = []
    for r, (분자, 분모) in zip(rows, 줄[metric]):
        if 분모:
            난것.append({"id": r["id"], "arm": arm, "score": 분자 / 분모})
    return 난것


def corr(name: str, judges: list[str], 자들: dict[str, pathlib.Path], 기준이름: str,
         n: int = 10000, seed: int = 7) -> int:
    """**자가 사람과 같은 순서로 줄을 세우는가**(H-084 · DECISIONS §242).

    ★ 재는 것은 **순서**다. 크기가 아니다 — QE 의 3.2 와 사람의 0.75 는 단위가 다르다.
    ★ **`--기준` 과의 차가 판정이다.** 「상관이 있다」 는 낮은 문턱이고, 물음은
      **「지금 쓰는 자보다 나은가」** 다(§229 에서 `term_off` 가 거꾸로 가리켰다).
    """
    got = 판정들(name, judges)
    사람 = 사람점수(got)
    if 기준이름 and 기준이름 not in 자들:
        raise SystemExit(f"--기준 '{기준이름}' 이 --자 에 없다 — 있는 것 : {' · '.join(자들) or '없다'}\n"
                         f"    이름을 맞춘다 : --자 {기준이름}=<점수.jsonl> 를 같이 준다\n"
                         f"    기준 없이 ρ 만 보려면 : --기준 를 뺀다")
    점수 = {이름: 자점수(p) for 이름, p in 자들.items()}
    기준 = 점수.get(기준이름)

    print(f"  {name} · 판정자 {len(judges)} · 사람이 본 (줄,팔) {len(사람)}")
    판정자를_찍는다(name, judges)
    for 이름, 자 in 점수.items():
        키 = sorted(set(사람) & set(자))
        if len(키) < 3:
            print(f"  {이름:14} **못 잰다** — 사람과 겹치는 (줄,팔) 이 {len(키)} 이다")
            continue
        빠진 = len(사람) - len(키)
        r = 상관(사람, 자, 키, n, seed, 기준 if (기준 and 이름 != 기준이름) else None)
        if r is None:
            print(f"  {이름:14} **못 잰다** — 점수가 전부 같은 값이거나 재표집이 비었다")
            continue
        꼬리 = f"  (사람이 본 것 중 {빠진} 쌍을 이 자가 안 매겼다)" if 빠진 else ""
        표시 = f"{이름}{' ← 기준' if 이름 == 기준이름 else ''}"
        print(f"  {표시:20} ρ {r['ρ']:+.4f}  [{r['아래']:+.4f}, {r['위']:+.4f}]  p={r['p']:.3f}"
              f"  · 쌍 {r['쌍']}{꼬리}")
        if "차" in r:
            품나 = r["차아래"] <= 0 <= r["차위"]
            print(f"  {'':20} 차(− {기준이름}) {r['차']:+.4f}  [{r['차아래']:+.4f}, {r['차위']:+.4f}]"
                  f"  p={r['차p']:.3f}  {'**못 가른다**' if 품나 else '**갈린다**'}")
            # ★ **하나를 빼도 부호가 남나**(H-081 ③ 과 같은 조건). 이 구간은 **줄만** 재표집하므로
            #   판정자 사이의 퍼짐을 안 본다 — §118 이 그 퍼짐을 실측했다
            if len(judges) > 2 and not 품나:
                뒤집힘 = []
                for j in judges:
                    남 = 사람점수({k: v for k, v in got.items() if k != j})
                    ㅋ = sorted(set(남) & set(자) & set(기준))
                    a = 스피어만([남[k] for k in ㅋ], [자[k] for k in ㅋ])
                    b = 스피어만([남[k] for k in ㅋ], [기준[k] for k in ㅋ])
                    if a is None or b is None or ((a - b) > 0) != (r["차"] > 0):
                        뒤집힘.append(j)
                print(f"  {'':20} 하나를 빼면 — " +
                      ("부호가 다 남는다" if not 뒤집힘 else
                       f"**{' · '.join(뒤집힘)} 없이는 뒤집힌다 — 그 판정자 없이는 말할 수 없다**"))
    print("  ※ 점수는 **클수록 좋은 쪽**으로 맞춰서 낸 것이어야 한다. ρ 가 음수면 둘 중 하나다 — "
          "**방향을 뒤집어 적었거나**, **자가 거꾸로 가리키거나**(§229). 도구는 못 가른다")
    print("  ※ 참값은 **사람 판정**이다(H-046 · H-081). 자가 사람을 이기는 일은 없다 — "
          "자는 사람을 **대신 돌릴 수 있는가**만 묻는다")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make")
    m.add_argument("--set", dest="setpath", required=True)
    m.add_argument("--a", default="", help="팔 a. `--arm a=<경로>` 와 같다")
    m.add_argument("--b", default="", help="팔 b")
    m.add_argument("--arm", action="append", default=[], metavar="이름=경로",
                   help="팔을 이름으로 준다. 여러 번 쓴다 — 기준선을 같은 표에 얹는다")
    m.add_argument("--name", default="")
    m.add_argument("--n", type=int, default=60)
    m.add_argument("--seed", type=int, default=31)
    r = sub.add_parser("read")
    r.add_argument("--name", required=True)
    r.add_argument("--sheet", default="")
    r.add_argument("--judge", default="claude", help="판정자의 이름 — 자리다")
    r.add_argument("--model", default="", help="무엇이 판정했나 — 모델과 판. 이쪽이 자다")
    sub.add_parser("prompt")
    g = sub.add_parser("agree")
    g.add_argument("--name", required=True)
    g.add_argument("--judges", required=True, help="쉼표로 둘 이상 — 카파는 쌍마다 난다")
    d = sub.add_parser("gap")
    d.add_argument("--name", required=True)
    d.add_argument("--judges", required=True, help="쉼표로 하나 이상")
    d.add_argument("--arm", required=True, help="재는 팔")
    d.add_argument("--vs", required=True, help="기준 팔. 차는 arm − vs 다")
    d.add_argument("--n", type=int, default=10000, help="재표집 판 수")
    d.add_argument("--seed", type=int, default=7)
    c = sub.add_parser("corr")
    c.add_argument("--name", required=True)
    c.add_argument("--judges", required=True, help="쉼표로 하나 이상 — 이들의 평균이 참값이다")
    c.add_argument("--자", action="append", default=[], metavar="이름=경로",
                   help="잴 자. 여러 번 쓴다 — 줄마다 {\"id\",\"arm\",\"score\"} 인 jsonl")
    c.add_argument("--기준", default="", help="견줄 자의 이름. 지금 쓰는 자를 넣는다(term_off)")
    c.add_argument("--n", type=int, default=10000, help="재표집 판 수")
    c.add_argument("--seed", type=int, default=7)
    u = sub.add_parser("rule")
    u.add_argument("--run", action="append", default=[], required=True, metavar="팔=경로",
                   help="규칙 지표를 자로 쓰려고 줄별 점수를 낸다. 팔마다 한 번")
    u.add_argument("--metric", default="term_off")
    u.add_argument("--set", dest="setpath", default="", help="비우면 판의 머리줄이 든 셋")
    u.add_argument("--out", default="", help="비우면 화면으로")
    a = ap.parse_args(argv)

    if a.cmd == "rule":
        난것 = []
        for spec in a.run:
            if "=" not in spec:
                raise SystemExit(f"--run 은 팔=경로 다 — {spec}")
            k, _, v = spec.partition("=")
            난것 += 규칙점수(pathlib.Path(v.strip()), k.strip(), a.metric, a.setpath)
        글 = "\n".join(json.dumps(x, ensure_ascii=False) for x in 난것) + "\n"
        if a.out:
            pathlib.Path(a.out).write_text(글, encoding="utf-8")
            print(f"  {a.out}  {len(난것)}줄 ({a.metric})")
        else:
            print(글, end="")
        return 0

    if a.cmd == "prompt":
        print(PROMPT)
        return 0
    if a.cmd in ("agree", "gap", "corr"):
        js = [x.strip() for x in a.judges.split(",") if x.strip()]
        if len(js) != len(set(js)):
            raise SystemExit(f"--judges 에 같은 이름이 두 번 있다 — {a.judges}\n"
                             "    한 판정자를 두 번 세면 카파도 격차도 그쪽으로 기운다")
        적어도 = 2 if a.cmd == "agree" else 1
        if len(js) < 적어도:
            raise SystemExit(f"--judges 는 {적어도} 이상이다 — 보기: gpt,gemini,pplx\n"
                             f"    누가 있나 : ls {_짧게(out_dir())}/{a.name}.*.jsonl")
        if a.cmd == "agree":
            return agree(a.name, js)
        if a.cmd == "gap":
            return gap(a.name, a.arm, a.vs, js, a.n, a.seed)
        자들: dict[str, pathlib.Path] = {}
        for spec in a.자:
            if "=" not in spec:
                raise SystemExit(f"--자 는 이름=경로 다 — {spec}\n"
                                 f"    보기 : --자 term_off=/tmp/term_off.jsonl --자 metricx=/tmp/metricx.jsonl")
            k, _, v = spec.partition("=")
            자들[k.strip()] = pathlib.Path(v.strip())
        if not 자들:
            raise SystemExit("--자 이름=경로 를 하나 이상 준다\n"
                             "    지금 쓰는 자를 같이 넣고 --기준 으로 지목한다 — "
                             "**「상관이 있다」 가 아니라 「지금 것보다 나은가」 가 물음이다**")
        return corr(a.name, js, 자들, a.기준.strip(), a.n, a.seed)
    if a.cmd == "read":
        # ★ **무엇이 판정했는지 없이는 판정을 안 받는다**(DECISIONS §227). 이름은 자리이고 모델이
        #   자다 — 무료 등급은 뒤의 모델을 말없이 바꾸므로 이름만 남으면 **다음 달에 같은 자가 아니다**
        if not a.model.strip():
            raise SystemExit("--model 이 없다 — 무엇이 판정했는지를 적는다\n"
                             f"    보기 : --judge gemini --model 'Gemini 2.5 Flash · 무료 · 2026-09-29'\n"
                             f"    모르면 화면에 뜬 이름 그대로 적는다 — **빈 채로 두지 않는다**\n"
                             f"    다시 : python3 tools/labels.py read --name {a.name} "
                             f"--judge {a.judge} --model <무엇>")
        return read(a.name, pathlib.Path(a.sheet or f"/tmp/labels-{a.name}.tsv"), a.judge, a.model.strip())

    arms: dict[str, pathlib.Path] = {}
    if a.a:
        arms["a"] = pathlib.Path(a.a)
    if a.b:
        arms["b"] = pathlib.Path(a.b)
    for spec in a.arm:
        if "=" not in spec:
            raise SystemExit(f"--arm 은 이름=경로 다 — {spec}")
        k, _, v = spec.partition("=")
        arms[k.strip()] = pathlib.Path(v.strip())
    if len(arms) < 2:
        raise SystemExit("팔이 둘 이상이어야 한다 — --a/--b 또는 --arm 이름=경로 를 두 번 이상")
    name = a.name or f"{pathlib.Path(a.setpath).stem}-{a.n}"
    sheet, key = make(arms, evaluate.load(a.setpath), name, a.n, a.seed)
    (out_dir() / f"{name}.key.jsonl").write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in key) + "\n", encoding="utf-8")
    out = pathlib.Path(f"/tmp/labels-{name}.tsv")
    out.write_text(sheet, encoding="utf-8")
    print(f"  {out}  {len(key)}줄 (눈가림 · 어느 팔인지 안 적혀 있다)")
    print(f"  {_짧게(out_dir() / f'{name}.key.jsonl')}  열쇠 — 다 매기기 전에 열지 않는다")
    print("  ★ 판정자는 한 번에 하나씩이다 — 앞선 판정을 보여 주지 않는다(DECISIONS §108).")
    print("    표를 한 판정자에게 주고 답을 받은 뒤에 다음 판정자에게 준다. 몇이든 같다 —")
    print("    답끼리는 `agree` 가 붙일 때 처음 만난다")
    print(f"  다 매기면 : python3 tools/labels.py read --name {name} --judge <판정자>")
    print(f"  팔을 가른다 : python3 tools/labels.py gap --name {name} --judges <쉼표> --arm <팔> --vs <기준>")
    print("  그 뒤     : python3 tools/lake.py put raw --into labels labels/*.jsonl")
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
