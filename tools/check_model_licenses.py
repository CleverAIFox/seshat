"""코드가 부르는 모델 가중치가 대장에 있고 상업 가부가 적혀 있는가(DECISIONS §6).

  python3 tools/check_model_licenses.py          검사한다. 위반 1 · 고장 2
  python3 tools/check_model_licenses.py --list   대장을 찍는다

★ **하토르가 먼저 겪었다.** 검색과 화성 판정이 비상업 가중치(`MERT-v1-95M`, CC-BY-NC-4.0) 위에
  서 있었고 백칠십 건의 결정 동안 아무도 라이선스를 보지 않았다(하토르 D-0217). 튜닝을 마친
  뒤에 알면 처음부터 다시 한다. 그래서 가중치를 부르는 첫 줄부터 센다.

★ **축이 둘이다**(DECISIONS §44) — 서빙에 쓸 수 있는가(상업)와 **출력을 학생 학습에 쓸 수 있는가**(교사).
  둘은 다르다. EXAONE 3.5 는 연구 평가는 허락하고 출력으로 다른 모델을 만드는 것은 금지한다.

★ **비상업을 막지 않는다. 센다.** 비교용으로 비상업 모델을 재는 것은 정당하다(seshat PLAN #5).
  상업 불가가 몇 개인지 매번 찍고, 서빙 백엔드가 그것을 부르면 실패한다.

★ **쓸 수 없는 가중치는 어디서도 부르지 못한다**(`seshat/licenses.py` 의 `EXCLUDED`). 사용 허락
  지역이 이 기계가 있는 곳을 빼는 라이선스는 비상업과 다르다 — 비교 실험도 허락 밖이다(DECISIONS §9).

★ 찾는 자리는 가중치를 받는 호출의 첫 문자열 인자다 — `from_pretrained` · `snapshot_download` ·
  `hf_hub_download` · `ctranslate2.Translator` · `Llama.from_pretrained`. 오탐이 많은 검사는
  꺼진다(하토르 D-0126) — 모든 `org/name` 꼴 문자열을 보지 않는다.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from seshat.licenses import EXCLUDED, LEDGER, VALID_COMMERCIAL, VALID_TEACHER, excluded

CALL = re.compile(
    r"(?:from_pretrained|snapshot_download|hf_hub_download|Translator)\(\s*(?:repo_id\s*=\s*)?[\"']([^\"']+)[\"']")
# 서빙 백엔드가 있는 파일. 여기서 상업 불가 가중치를 부르면 실패한다.
SERVING = ("seshat/backends.py", "seshat/serve.py")


def scan(root: Path) -> list[tuple[str, int, str]]:
    out = []
    for p in sorted((root / "seshat").rglob("*.py")) + sorted((root / "tools").glob("*.py")):
        if p.name == "check_model_licenses.py":
            continue
        for n, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            for m in CALL.finditer(line):
                out.append((str(p.relative_to(root)), n, m.group(1)))
    return out


def declared() -> dict[str, str]:
    """백엔드가 선언한 가중치(`seshat/backends.py::WEIGHTS`). 정규식이 못 보는 호출을 덮는다."""
    from seshat import backends
    return dict(backends.WEIGHTS)


def check(root: Path, ledger: dict, weights: dict[str, str] | None = None) -> list[str]:
    fails = []
    for backend, name in (declared() if weights is None else weights).items():
        if excluded(name):
            fails.append(f"백엔드 {backend} 가 쓸 수 없는 가중치 {name} 를 선언한다 — {excluded(name)}")
        elif name not in ledger:
            fails.append(f"백엔드 {backend} 가 선언한 가중치 {name} 가 대장에 없다 — seshat/licenses.py")
    for name, (lic, com, teach, src) in ledger.items():
        if com not in VALID_COMMERCIAL:
            fails.append(f"대장 {name} 의 상업 가부 '{com}' 가 어휘 밖이다 — {sorted(VALID_COMMERCIAL)}")
        if teach not in VALID_TEACHER:
            fails.append(f"대장 {name} 의 교사 가부 '{teach}' 가 어휘 밖이다 — {sorted(VALID_TEACHER)}")
        if not lic.strip() or not src.strip():
            fails.append(f"대장 {name} 에 라이선스나 출처가 비었다")
    for name in ledger:
        if excluded(name):
            fails.append(f"대장에 쓸 수 없는 가중치 {name} 가 있다 — {excluded(name)}")
    for rel, n, name in scan(root):
        if excluded(name):
            fails.append(f"{rel}:{n} 가 쓸 수 없는 가중치 {name} 를 부른다 — {excluded(name)}")
        elif name not in ledger:
            fails.append(f"{rel}:{n} 가 대장에 없는 가중치 {name} 를 부른다 — seshat/licenses.py")
        elif rel in SERVING and ledger[name][1] != "yes":
            fails.append(f"{rel}:{n} 서빙 백엔드가 상업 가부 '{ledger[name][1]}' 인 {name} 를 부른다")
    return fails


def _canary() -> None:
    got = CALL.findall('AutoModel.from_pretrained("google/madlad400-3b-mt") · '
                       'snapshot_download(repo_id="Qwen/Qwen2.5-1.5B") · x("a/b")')
    if got != ["google/madlad400-3b-mt", "Qwen/Qwen2.5-1.5B"]:
        print(f"    ★ 카나리아가 죽었다 — CALL 이 {got} 를 찾았다")
        sys.exit(2)


def main(argv=None) -> int:
    args = sys.argv[1:] if argv is None else argv
    _canary()
    if "--list" in args:
        for name, (lic, com, teach, src) in sorted(LEDGER.items()):
            print(f"  {com:<8} {lic:<14} {name}  ({src})")
        for pre, why in sorted(EXCLUDED.items()):
            print(f"  제외     {pre}*  — {why}")
        print(f"  상업 불가 {sum(1 for v in LEDGER.values() if v[1] == 'no')} · 교사 불가 "
              f"{sum(1 for v in LEDGER.values() if v[2] == 'no')} · 전체 {len(LEDGER)}")
        return 0
    fails = check(ROOT, LEDGER)
    for f in fails:
        print(f"    {f}")
    return 1 if fails else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(2)
