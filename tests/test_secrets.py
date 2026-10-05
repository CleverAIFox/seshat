"""비밀값 꼴 검사 — **0건이 목표인 검사**다(DECISIONS §304).

★ **깨끗해서 0 인지 죽어서 0 인지 가를 수 없다.** 그래서 합성 양성과 합성 음성을 함께 둔다.
★ **값은 어디에도 안 찍는다.** 검사가 찾은 것을 화면에 내면 **로그가 유출이 된다** —
  이 시험도 같은 규칙을 지킨다(합성 값만 쓴다).
"""
from __future__ import annotations

import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("check_secrets", ROOT / "tools/check_secrets.py")
CS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CS)


def test_카나리아가_살아_있다():
    assert CS.main(["--selftest"]) == 0


def test_꼴마다_합성_양성이_걸린다():
    """★ **음성만 있으면 아무것도 안 잡는 검사가 초록이다.**

    ★ **합성 값을 글자 그대로 적지 않는다**(§304). 적으면 **이 파일이 그 검사에 걸린다** —
      깨끗한 사본에서 실제로 그랬다. 면제를 만들면 **진짜가 거기 숨을 수 있다.**
    """
    합성 = {
        "AWS 접근키": "AKIA" + "Z" * 16,
        "GitHub 토큰": "ghp_" + "z" * 36,
        "OpenAI 키": "sk-" + "z" * 32,
        "허깅페이스 토큰": "hf_" + "z" * 30,
        "슬랙 토큰": "xox" + "b-0000000000-zz",
        "개인키": "-----BEGIN " + "OPENSSH PRIVATE KEY-----",
        "비밀 대입": 'api_key = "' + "z" * 12 + '"',
    }
    for 이름, 줄 in 합성.items():
        assert any(이름 in x for x in CS.찾는다(줄)), 이름


def test_멀쩡한_줄은_안_걸린다():
    """★ **거짓 빨강이 쌓이면 사람이 검사를 끈다**(§158). 해시 · 경로 · 짧은 값은 흔하다."""
    for 줄 in ("sha = 3326d3e6b9ef49204d4968e7d2e38ae91c367d84",
               'p = "tools/check_secrets.py"',
               'token = "짧다"',
               "# AKIA 로 시작하는 것이 접근키다",
               "base64 = aGVsbG8gd29ybGQgdGhpcyBpcyBsb25n"):
        assert CS.찾는다(줄) == [], 줄


def test_값을_안_찍는다():
    """★ **검사가 찾은 것을 화면에 내면 로그가 유출이 된다.** 줄 번호와 꼴 이름만 낸다."""
    비밀 = "ghp_" + "q" * 36
    말 = CS.찾는다(f"x = {비밀}", "a.py")
    assert 말 and all(비밀 not in x for x in 말), 말


def test_지금_저장소가_조용하다():
    """★ **실측 0건이다**(§304). 늘면 여기서 운다."""
    assert CS.나무를_본다() == []


def test_verify_가_이것을_본다():
    """★ **사슬 밖에 둔 검사는 사람이 기억해야 돌고, 사람은 안 돌린다**(§287)."""
    assert "tools/check_secrets.py" in (ROOT / "tools/verify.sh").read_text(encoding="utf-8")


def test_글로_못_읽는_것은_안_본다():
    """★ **바이너리를 정규식에 먹이면 못 읽은 것을 0 으로 센다**(§296 의 `글자아님`)."""
    assert ".png" in CS.글자아님 and ".parquet" in CS.글자아님


def test_장부가_비어_있다():
    """★ **줄지 않는 장부는 영구 면제가 된다**(§290). 지금은 예외가 없다 — 그대로 둔다."""
    assert CS.장부 == frozenset()
