r"""**신경망 QE 자로 판의 줄마다 점수를 낸다** — MetricX-24(H-084 · DECISIONS §246).

  python3 tools/qe.py --run 4b=runs/….jsonl --run 12b=runs/….jsonl --out /tmp/metricx.jsonl
  python3 tools/qe.py --run … --out … --metricx ~/projects/metricx   # 자리를 손으로

★ **규칙 지표 여덟에 자가 하나도 없었다**(DECISIONS §245) — 둘은 상수, 넷은 0 을 품고, 둘은 거꾸로
  가리킨다. 그래서 신경망 자를 들인다. 후보는 **Apache-2.0 이고 참조 없이 도는 것** 둘뿐이다
  (`seshat/licenses.py` · DECISIONS §242) — CometKiwi · XCOMET 계열은 **CC-BY-NC-SA 라 못 쓴다.**
★ **점수는 오류 점수다** — MetricX 는 `[0, 25]` 이고 **작을수록 좋다.** 여기서 **부호를 뒤집어**
  적는다(`score = -raw`) — `labels.py corr` 은 「클수록 좋다」 를 전제한다(§242). 원값은 `raw` 로
  같이 남긴다. **뒤집는 자리를 하나로 둔다** — 두 곳에서 뒤집으면 한 곳만 고쳐진다.
★ **남의 코드를 베끼지 않는다**(DECISIONS §5). `MT5ForRegression` 은 회귀 머리를 단 mT5 이고
  **직접 다시 쓰면 조용히 다른 수를 낸다** — 원본을 그대로 부른다. 다만 그 저장소는
  **파이썬 꾸러미가 아니다**(`setup.py` 도 `pyproject.toml` 도 없다) — 받아서 자리를 알려 준다.
★ **`transformers` 5 에서 상수 하나가 사라졌다** — `__HEAD_MASK_WARNING_MSG`. 원본은 4.30 에
  맞춰져 있다. **없을 때만** 채워 넣고 **채웠다는 사실을 판 머리줄에 적는다** — 조용히 기우면
  다음 사람이 「원본 그대로 돌았다」 고 읽는다.
★ **밖 — 이 자가 옳은지는 이 도구가 모른다.** 내는 것은 수이고, **그 수가 사람과 같은 순서로 줄을
  세우는가**는 `tools/labels.py corr` 이 묻는다(H-084). ⚠ MetricX-24 는 WMT'15–22 의 DA · MQM 으로
  맞춰졌고 **영→한은 그 안에 없다** — 그래서 짐작 말고 잰다.
★ **밖 — 판정과 안 이어 준다.** 어느 표의 어느 줄인지는 `corr` 이 `(id, arm)` 으로 잇는다.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from seshat import evaluate, paths  # noqa: E402

기본모형 = "google/metricx-24-hybrid-large-v2p6"
기본토크나이저 = "google/mt5-xl"
기본길이 = 1536


def _도구(이름: str):
    spec = importlib.util.spec_from_file_location(이름, ROOT / f"tools/{이름}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def 자리(준것: str = "") -> pathlib.Path:
    """MetricX 저장소의 자리. `--metricx` · `SESHAT_METRICX` · 흔한 이웃 자리 순으로 찾는다."""
    paths.load_dotenv()
    후보 = [준것, os.environ.get("SESHAT_METRICX", "")]
    후보 += [str(ROOT.parent / "metricx"), str(pathlib.Path.home() / "projects/metricx")]
    for x in 후보:
        if x and (pathlib.Path(x).expanduser() / "metricx24/models.py").is_file():
            return pathlib.Path(x).expanduser()
    raise SystemExit(
        "MetricX 저장소를 못 찾았다 — **파이썬 꾸러미가 아니라서 받아 두어야 한다**\n"
        f"    받는다 : git clone --depth 1 https://github.com/google-research/metricx {ROOT.parent}/metricx\n"
        "    자리를 적는다 : .env 에 SESHAT_METRICX=<받은 자리>\n"
        "    한 번만 쓰려면 : --metricx <받은 자리>\n"
        "    ★ **seshat 안에 두지 않는다** — 남의 저장소이고 카탈로그 밖 파일이 된다(DECISIONS §22)")


def 커밋(d: pathlib.Path) -> str:
    """받아 둔 MetricX 의 커밋. **조건이다** — 자가 바뀌면 수가 바뀐다(DECISIONS §57)."""
    try:
        r = subprocess.run(["git", "-C", str(d), "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or "모른다"
    except Exception:
        return "모른다"


def 모형을_든다(d: pathlib.Path, 모형: str, 토크나이저: str):
    """`MT5ForRegression` 과 토크나이저. **기운 자리를 함께 돌려준다.**"""
    sys.path.insert(0, str(d))
    import torch
    import transformers
    m = transformers.models.mt5.modeling_mt5
    기움 = []
    # ★ **원본은 transformers 4.30 에 맞춰져 있다.** 5 에서 이 상수가 사라졌다 — 경고 문구일 뿐
    #   점수에 안 닿지만, **없으면 import 가 죽는다.** 없을 때만 채우고 **채웠다고 적는다**
    if not hasattr(m, "__HEAD_MASK_WARNING_MSG"):
        m.__HEAD_MASK_WARNING_MSG = "(seshat 이 채운 자리다 — transformers 5 에서 사라졌다)"
        기움.append("__HEAD_MASK_WARNING_MSG")
    try:
        from metricx24 import models
    except Exception as e:                        # noqa: BLE001
        raise SystemExit(
            f"MetricX 를 못 들였다 — {type(e).__name__}: {e}\n"
            f"    받은 자리 : {d}\n"
            "    `transformers` 판이 안 맞을 수 있다(원본은 4.30 에 맞춰져 있다)\n"
            "    판을 본다 : uv run --group qe python -c 'import transformers;print(transformers.__version__)'\n"
            "    내려서 다시 : uv pip install 'transformers<5'") from e
    try:
        tok = transformers.AutoTokenizer.from_pretrained(토크나이저, legacy=False, use_fast=True)
    except Exception as e:                        # noqa: BLE001
        # ★ **마지막 말이 길을 잘못 든다**(DECISIONS §246). `spiece.model` 을 빠른 토크나이저로
        #   바꾸려면 `protobuf` 가 있어야 하는데, 없으면 transformers 5 가 **tiktoken 으로 넘어갔다가**
        #   거기서 죽는다 — 화면의 마지막 줄이 `pip install tiktoken` 이라 **엉뚱한 것을 깔게 된다**
        raise SystemExit(
            f"토크나이저를 못 들였다 — {type(e).__name__}: {e}\n"
            "    ★ 화면이 `tiktoken` 을 깔라고 했으면 **그 말을 따르지 않는다** — 필요한 것은\n"
            "      `protobuf` 다(`spiece.model` → 빠른 토크나이저 변환).\n"
            "    깐다 : uv sync --group eval --group qe   ← `qe` 그룹이 든다\n"
            "    그래도 안 되면 : uv pip install protobuf") from e
    mod = models.MT5ForRegression.from_pretrained(모형)
    mod.eval()
    장치 = "cuda" if torch.cuda.is_available() else "cpu"
    mod.to(장치)
    return tok, mod, 장치, 기움


def 줄을_모은다(판: dict[str, pathlib.Path], setpath: str = "") -> list[dict]:
    """(id, arm, src, out). **셋은 판의 머리줄이 든다** — 손으로 안 적는다."""
    bs = _도구("bootstrap")
    난것 = []
    for arm, p in sorted(판.items()):
        if not p.exists():
            raise SystemExit(f"판(`{arm}`)이 없다 — {p}\n"
                             "    어느 판인지 본다 : ls -t runs/*.jsonl | head")
        머리, got = bs.read(str(p))
        rows = evaluate.load(setpath or 머리.get("set") or "")
        for r in rows:
            if r["id"] in got:
                난것.append({"id": r["id"], "arm": arm,
                            "src": r["src"], "out": got[r["id"]].get("out", "")})
    return 난것


def 잰다(줄: list[dict], tok, mod, 장치: str, 길이: int, 묶음: int) -> list[float]:
    """오류 점수(작을수록 좋다). **원본과 같은 꼴로 넣는다** — 다르면 조용히 다른 수가 난다.

    ★ `"source: … candidate: …"` · 길이 잘라내기 · **끝의 EOS 를 뗀다.**
      셋 다 `metricx24/predict.py` 의 `get_dataset` 그대로다.
    """
    import torch
    난것: list[float] = []
    for i in range(0, len(줄), 묶음):
        덩이 = 줄[i:i + 묶음]
        글 = [f"source: {x['src']} candidate: {x['out']}" for x in 덩이]
        인 = tok(글, max_length=길이, truncation=True, padding=False)
        ids = [x[:-1] for x in 인["input_ids"]]           # ★ EOS 를 뗀다(원본과 같다)
        마스크 = [x[:-1] for x in 인["attention_mask"]]
        긴 = max(len(x) for x in ids)
        pad = tok.pad_token_id or 0
        배 = torch.tensor([x + [pad] * (긴 - len(x)) for x in ids], device=장치)
        맥 = torch.tensor([x + [0] * (긴 - len(x)) for x in 마스크], device=장치)
        with torch.no_grad():
            난것 += [float(v) for v in mod(input_ids=배, attention_mask=맥).predictions]
        print(f"\r  {min(i + 묶음, len(줄))}/{len(줄)}", end="", file=sys.stderr, flush=True)
    print("", file=sys.stderr)
    return 난것


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="append", default=[], required=True, metavar="팔=경로")
    ap.add_argument("--out", required=True)
    ap.add_argument("--metricx", default="")
    ap.add_argument("--model", default=기본모형)
    ap.add_argument("--tokenizer", default=기본토크나이저)
    ap.add_argument("--max-input-length", type=int, default=기본길이)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument("--set", dest="setpath", default="")
    a = ap.parse_args(sys.argv[1:] if argv is None else argv)

    판: dict[str, pathlib.Path] = {}
    for spec in a.run:
        if "=" not in spec:
            raise SystemExit(f"--run 은 팔=경로 다 — {spec}\n"
                             "    보기 : --run 4b=runs/H-080-retry2-20260929-201747.jsonl")
        k, _, v = spec.partition("=")
        판[k.strip()] = pathlib.Path(v.strip())

    d = 자리(a.metricx)
    줄 = 줄을_모은다(판, a.setpath)
    print(f"  {len(줄)}줄 · 팔 {len(판)} · {a.model}", file=sys.stderr)
    tok, mod, 장치, 기움 = 모형을_든다(d, a.model, a.tokenizer)
    print(f"  {장치}" + (f" · 기운 자리 {' · '.join(기움)}" if 기움 else ""), file=sys.stderr)
    점수 = 잰다(줄, tok, mod, 장치, a.max_input_length, a.batch_size)

    # ★ **머리줄이 조건을 든다**(DECISIONS §57). 자가 바뀌면 수가 바뀐다 — 모형 · 토크나이저 ·
    #   MetricX 커밋 · 기운 자리 · 길이 · 장치. **`corr` 은 `meta` 줄을 건너뛴다**
    머리 = {"meta": True, "자": "metricx24-qe", "model": a.model, "tokenizer": a.tokenizer,
            "metricx_commit": 커밋(d), "max_input_length": a.max_input_length,
            "device": 장치, "기운자리": 기움, "뒤집었다": True,
            "note": "score = -raw — MetricX 는 오류 점수라 작을수록 좋다(DECISIONS §246)"}
    글 = [json.dumps(머리, ensure_ascii=False)]
    글 += [json.dumps({"id": x["id"], "arm": x["arm"], "score": -s, "raw": s}, ensure_ascii=False)
           for x, s in zip(줄, 점수)]
    pathlib.Path(a.out).write_text("\n".join(글) + "\n", encoding="utf-8")
    print(f"  {a.out}  {len(점수)}줄 · 원값 {min(점수):.3f} ~ {max(점수):.3f} (작을수록 좋다)")
    print("  자가 사람과 같은 순서인지 묻는다 :\n"
          f"    python3 tools/labels.py corr --name <표> --judges <쉼표> "
          f"--자 metricx={a.out} --자 term_off=<term_off.jsonl> --기준 term_off")
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
