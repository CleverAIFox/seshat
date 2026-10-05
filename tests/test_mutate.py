"""**돌연변이 자를 붙드는 시험**(DECISIONS §287).

★ 이 파일은 **seshat 것**이다 — thoth 사본이 아니다(DECISIONS §5).

★ **저장소가 깨끗하면 검사를 꺼도 초록이다.** 톱니를 저장소 수로만 물으면 지금 통과하고,
  `MIN_잴것` 을 1 로 낮춰도 통과한다. 그래서 **가짜 수로 묻는다** — 토트가 같은 모양의
  돌연변이 셋을 살려 보내고서야 배운 것이다(토트 §145 · §147 · §150).

★ **짝 시험은 긍정만 낸다.** 「짝이 조용하다」 가 「붙드는 시험이 없다」 로 읽히면 거짓 양성이다.
  그 두 길이 갈라져 있는지를 본다.
"""
from __future__ import annotations

import importlib.util
import pathlib

ROOT = next(p for p in pathlib.Path(__file__).resolve().parents
            if (p / "tools/mutate.py").exists())
_spec = importlib.util.spec_from_file_location("mu", ROOT / "tools/mutate.py")
MU = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(MU)


# ── 톱니 — 가짜 수로 묻는다 ────────────────────────────────────────────────

def test_지금_저장소는_조용하다():
    잰다, 못잰다 = MU.잴것()
    assert MU.톱니(len(잰다), len(못잰다)) == []


def test_못_잴_자리가_늘면_운다():
    # ★ 2026-10-01 에 적힌 41 이 아무도 안 세는 사이 47 로 늘었다. 그 자리를 막는다.
    난것 = MU.톱니(MU.MIN_잴것, MU.MAX_못잴것 + 1)
    assert any("천장" in x for x in 난것), 난것


def test_잴_자리가_줄면_운다():
    # ★ 반환 주석을 떼면 그 함수가 **조용히** 검사 밖으로 나간다 — 수는 줄고 초록은 그대로다.
    난것 = MU.톱니(MU.MIN_잴것 - 1, MU.MAX_못잴것)
    assert any("바닥" in x for x in 난것), 난것


def test_좋아진_것은_안_운다():
    assert MU.톱니(MU.MIN_잴것 + 50, MU.MAX_못잴것 - 10) == []


def test_바닥과_천장이_실측과_맞다():
    # ★ **같은 수가 두 곳에 살면 한쪽만 늙는다**(§57 과 같은 자리). 바닥이 실측보다 낮으면
    #   그만큼 헐렁하고, 높으면 영원히 빨갛다.
    잰다, 못잰다 = MU.잴것()
    assert MU.MIN_잴것 == len(잰다), f"바닥 {MU.MIN_잴것} ≠ 실측 {len(잰다)}"
    assert MU.MAX_못잴것 == len(못잰다), f"천장 {MU.MAX_못잴것} ≠ 실측 {len(못잰다)}"


# ── 짝 시험 ───────────────────────────────────────────────────────────────

def test_check_접두사를_떼고도_찾는다():
    # 저장소가 `tools/check_X.py` ↔ `tests/test_X.py` 꼴을 쓴다
    assert MU.짝시험("tools/check_deadchecks.py") == ["tests/test_deadchecks.py"]
    assert MU.짝시험("seshat/mbr.py") == ["tests/test_mbr.py"]


def test_짝이_없으면_빈_목록이다():
    # ★ 빈 목록이 **전부를 돌린다**는 뜻이다. 없는 파일을 돌리면 pytest 가 4 로 끝나
    #   「시험이 통과했다」 로 읽힌다 — 거짓 음성이다.
    assert MU.짝시험("tools/없는파일.py") == []


def test_시험이_안_든_껍데기는_짝이_아니다(tmp_path):
    """★ **0 바이트 `tests/test_docs.py` 하나가 이 자를 멈춰 세웠다**(DECISIONS §296).
    이름만 맞으면 짝으로 세고, pytest 는 5(모은 시험이 0)로 끝난다 — 멈추는 것이 거짓
    초록보다 낫지만 **옳은 답은 「짝이 아니다」 로 보고 전부로 재는 것**이다.
    """
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_빈것.py").write_text("", encoding="utf-8")
    (tmp_path / "tests/test_주석만.py").write_text("# 시험을 적으려다 말았다\n", encoding="utf-8")
    (tmp_path / "tests/test_든것.py").write_text("def test_a():\n    assert True\n", encoding="utf-8")
    assert MU.짝시험("seshat/빈것.py", tmp_path) == []
    assert MU.짝시험("seshat/주석만.py", tmp_path) == []
    assert MU.짝시험("seshat/든것.py", tmp_path) == ["tests/test_든것.py"]


def test_없는_시험_파일을_내놓지_않는다():
    import glob
    for f in glob.glob(str(ROOT / "tools/*.py")) + glob.glob(str(ROOT / "seshat/*.py")):
        rel = pathlib.Path(f).relative_to(ROOT).as_posix()
        for t in MU.짝시험(rel):
            assert (ROOT / t).exists(), f"{rel} 의 짝 {t} 이 없다"


# ── 몸통 지우기 ───────────────────────────────────────────────────────────

def test_꼴을_지키는_값으로_바꾼다():
    # ★ `None` 으로 바꾸면 `TypeError` 로 죽는데 **그 죽음은 시험이 값을 봤다는 뜻이 아니다.**
    import ast

    def 꼴(s: str) -> str | None:
        return MU._중립값(ast.parse(f"def f() -> {s}: ...").body[0].returns)

    assert (꼴("bool"), 꼴("list[str]"), 꼴("dict[str, int]"), 꼴("str | None")) == ("True", "[]", "{}", '""')
    assert 꼴("SomeClass") is None, "모르는 꼴을 억지로 바꾸면 거짓 양성이 된다"


def test_머리말은_남고_몸통만_간다():
    글 = MU.지운다('def f(a: int) -> bool:\n    """왜."""\n    return a > 3\n', "f", "True")
    assert "왜." in 글 and "return True" in 글 and "a > 3" not in 글


# ── 부르는 자리 ───────────────────────────────────────────────────────────

def test_장부를_좁히기_전_수로_부른다():
    """★ **사슬은 `--only` 로 돈다.** 톱니를 좁힌 수로 부르면 **사슬에서는 톱니가 영원히
    안 운다** — 「검사를 더했다」 와 「검사가 문다」 의 그 자리다.

    ★ 이것은 **부르는 자리를 읽는 시험**이다. 돌려서 보려면 `main` 이 진짜로 몸통을 지우고
      pytest 를 다시 띄우므로(시험 안의 시험) 글로 본다 — `test_doctor_가_3_을_받는다`
      와 같은 꼴이다. 함수를 아무리 고쳐도 **부르는 쪽이 틀리면 안 문다.**
    """
    몸 = (ROOT / "tools/mutate.py").read_text(encoding="utf-8")
    assert "난것 += 톱니(온잰다, 온못잰다)" in 몸, (
        "톱니를 좁히기 전 수(`온잰다` · `온못잰다`)로 안 부른다 — `len(잰다)` 는 좁혀진 수다")
    머리, 뒤 = 몸.split("if a.only:", 1)
    assert "온잰다, 온못잰다 = len(잰다), len(못잰다)" in 머리, (
        "전체 수를 `--only` 로 좁히기 **전**에 안 집는다")


# ── 종료코드 — 도구 고장을 「물었다」 로 세지 않는다 ─────────────────────────

def _코드(monkeypatch, 코드: int) -> None:
    import subprocess
    monkeypatch.setattr(MU.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess([], 코드, "", ""))


def test_시험이_울면_물었다고_한다(monkeypatch):
    _코드(monkeypatch, 1)
    assert MU.돌린다(["x"]) is True


def test_전부_통과하면_안_물었다고_한다(monkeypatch):
    _코드(monkeypatch, 0)
    assert MU.돌린다(["x"]) is False


def test_도구가_깨지면_물었다고_안_한다(monkeypatch):
    """★ **`!= 0` 으로 보면 거짓 초록이다**(DECISIONS §287).

    2026-10-04 에 의존성 묶음을 안 깐 채로 돌렸더니 수집 단계에서 죽어 **2** 가 나왔고,
    뚫은 자리 전부가 「붙드는 시험이 있다」 로 찍혔다 — 거짓 초록 스물한 건.
    **5(모은 시험이 0)** 는 좁혀 부르기의 함정이다 — 짝 시험 이름이 틀리면 그렇게 끝난다.
    """
    import pytest
    for 코드 in (2, 3, 4, 5):
        _코드(monkeypatch, 코드)
        with pytest.raises(SystemExit) as e:
            MU.돌린다(["x"])
        assert e.value.code == 2, f"{코드} 를 도구 고장으로 안 본다"


# ── 장부 ──────────────────────────────────────────────────────────────────

def test_장부에_없는_것만_운다():
    새것, 갚음 = MU.견준다(["a::f", "b::g"], frozenset({"a::f"}))
    assert 새것 == ["b::g"] and 갚음 == []


def test_갚은_것을_찍는다():
    # ★ 갚은 것을 안 찍으면 장부는 영원히 안 줄고, **줄지 않는 장부는 영구 면제**다(§258).
    새것, 갚음 = MU.견준다([], frozenset({"a::f", "b::g"}))
    assert 새것 == [] and 갚음 == ["a::f", "b::g"]


def test_장부도_같은_범위로_좁힌다():
    """★ 안 좁히면 `--only` 로 돈 판에서 범위 **밖** 항목이 전부 「갚았다」 로 보인다 —
    그것을 믿고 장부를 지우면 **장부가 조용히 비워진다.**"""
    assert MU.범위안("tools/check_prose.py", "tools/check_*.py") is True
    assert MU.범위안("seshat/mbr.py", "tools/check_*.py") is False
    assert MU.범위안("seshat/mbr.py", "") is True, "무늬가 없으면 전부가 범위다"


def test_장부의_자리가_실재한다():
    # ★ 없는 파일이 장부에 남으면 그 칸이 **쓰레기통**이 된다 — 영원히 「갚았다」 로 뜬다.
    for x in MU.장부:
        파일, 이름 = x.split("::")
        assert (ROOT / 파일).exists(), f"장부의 {파일} 이 없다"
        글 = (ROOT / 파일).read_text(encoding="utf-8")
        assert f"def {이름}(" in 글, f"{파일} 에 {이름} 이 없다 — 갚았으면 장부에서 지운다"


def test_장부가_범위_안에만_있다():
    # ★ `verify.sh` 가 보는 범위 밖 항목은 **그 사슬에서 영원히 안 보인다** — 빚이 숨는다.
    범위 = "tools/check_*.py"
    밖 = [x for x in MU.장부 if not MU.범위안(x.split("::")[0], 범위)]
    assert 밖 == [], f"사슬 범위({범위}) 밖인 장부 항목 — PLAN 으로 뺀다 : {밖}"


# ── 되돌리기 ──────────────────────────────────────────────────────────────

def test_신호를_받으면_되돌리고_죽는다(tmp_path, monkeypatch):
    """★ **`try/finally` 는 신호에 안 돈다**(DECISIONS §287). 2026-10-04 에 이 도구를
    `timeout` 으로 끊었더니 `tools/check_docs.py` 가 **`ast.unparse` 결과로 남았다** —
    주석 269줄이 사라진 채로. 그 뒤로 검사 넷이 빨개져서 **원인을 엉뚱한 데서 찾았다.**
    """
    import pytest
    f = tmp_path / "a.py"
    f.write_text("원본\n", encoding="utf-8")
    monkeypatch.setitem(MU._뚫린것, f, "원본\n")
    f.write_text("뚫린 것\n", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        MU._되돌리고_죽는다(15, None)
    assert f.read_text(encoding="utf-8") == "원본\n", "신호를 받고 안 되돌렸다"
    assert e.value.code == 130


# ── 부르는 자리 ───────────────────────────────────────────────────────────
#
# ★ 아래 셋은 **글로 본다.** 돌려서 보려면 `main` 이 진짜로 몸통을 지우고 pytest 를 다시
#   띄운다(시험 안의 시험) — `test_doctor_가_3_을_받는다` 와 같은 꼴이다.
#   **함수를 아무리 고쳐도 부르는 쪽이 틀리면 안 문다.**

def _몸() -> str:
    return (ROOT / "tools/mutate.py").read_text(encoding="utf-8")


def test_장부에_없는_것을_실패로_올린다():
    assert '난것 = [f"장부에 없는 자리' in _몸(), "새것을 `난것` 에 안 넣으면 늘어도 통과한다"


def test_장부를_범위로_좁혀_견준다():
    몸 = _몸()
    assert "본장부 = frozenset(x for x in 장부 if 범위안(" in 몸, (
        "장부를 `--only` 범위로 안 좁힌다 — 범위 밖이 전부 「갚았다」 로 보인다")
    assert "견준다(이름만, 본장부)" in 몸, "좁힌 장부로 안 견준다"


def test_신호를_main_머리에서_받는다():
    몸 = _몸()
    assert "signal.signal(_sig, _되돌리고_죽는다)" in 몸, "신호를 안 받는다"
    머리 = 몸.split("def main(")[1].split("ap = argparse")[0]
    assert "signal.signal" in 머리, "`main` 머리에서 안 받으면 **잊을 자리**가 생긴다(§286)"


def test_물_수_없는_자리를_적어_뒀다():
    """★ **구조적으로 못 무는 줄은 관문이 아니라 독립성이다.** 적어 두지 않으면 다음 사람이
    다시 물려 보려다 시간을 버린다 — `돌린다` 의 `== _울었다` 가 그 자리다. 가드가 이미
    `{0, 1}` 로 좁혀 놓아 `!= 0` 과 **증명 가능하게 같다.**"""
    assert "물 수 없다" in _몸(), "못 무는 자리를 머리말에 안 적었다"


# ── 바이트코드와 건너뜀 (DECISIONS §289) ──────────────────────────────────

def test_되돌린_뒤_바이트코드를_버린다(tmp_path):
    """★ **길이가 같은 바꿈은 `__pycache__` 를 중독시킨다.** 파이썬은 소스의 크기와 mtime
    으로 캐시를 쓰므로 둘 다 같으면 **되돌린 뒤에도 뚫린 바이트코드를 다시 쓴다** —
    해시로 소스를 확인해도 안 잡힌다. 이 자는 몸통을 통째로 바꾸므로 길이가 같아지기 쉽다.
    """
    f = tmp_path / "a.py"
    f.write_text("def main() -> int:\n    return 3\n", encoding="utf-8")
    캐시 = tmp_path / "__pycache__"
    캐시.mkdir()
    썩은 = 캐시 / "a.cpython-312.pyc"
    썩은.write_bytes(b"stale bytecode")
    MU._바이트코드를_버린다(f)
    assert not 썩은.exists(), "옛 바이트코드가 남았다"


def test_남의_캐시는_안_지운다(tmp_path):
    캐시 = tmp_path / "__pycache__"
    캐시.mkdir()
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    남 = 캐시 / "b.cpython-312.pyc"
    남.write_bytes(b"other")
    MU._바이트코드를_버린다(tmp_path / "a.py")
    assert 남.exists(), "다른 모듈의 캐시까지 지운다"


def test_전부_건너뛰면_도구_고장으로_멈춘다(monkeypatch):
    """★ **건너뛴 시험은 안 문다.** 통과로 끝나므로 「약해서 안 물었다」 와 구별이 안 된다 —
    thoth CI 가 그렇게 빨개졌고 두 실패가 한 원인이었다."""
    import subprocess

    import pytest
    monkeypatch.setattr(MU.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess([], 0, "4 skipped in 0.1s", ""))
    with pytest.raises(SystemExit) as e:
        MU.돌린다(["x"])
    assert e.value.code == 2


def test_통과가_섞이면_건너뜀이_아니다(monkeypatch):
    import subprocess
    monkeypatch.setattr(MU.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess([], 0, "3 passed, 1 skipped", ""))
    assert MU.돌린다(["x"]) is False, "하나라도 돌았으면 건너뜀이 아니다"


def test_뚫린_동안_바이트코드를_안_만든다():
    몸 = (ROOT / "tools/mutate.py").read_text(encoding="utf-8")
    assert "PYTHONDONTWRITEBYTECODE" in 몸, "뚫린 동안 캐시가 쌓인다"
    블록 = 몸[몸.index("def 돌린다("):몸.index("def _canary(")]
    assert "PYTHONDONTWRITEBYTECODE" in 블록, "시험을 돌리는 자리에서 안 막는다"


def test_되돌리는_자리마다_캐시를_버린다():
    몸 = (ROOT / "tools/mutate.py").read_text(encoding="utf-8")
    신호 = 몸[몸.index("def _되돌리고_죽는다("):몸.index("def main(")]
    assert "_바이트코드를_버린다(p)" in 신호, "끊겨 죽을 때 캐시가 남는다"
    본 = 몸[몸.index("        finally:"):]
    assert "_바이트코드를_버린다(f)" in 본, "되돌린 뒤 캐시를 안 버린다"
