"""**절과 그 절이 짚은 코드의 도장**이 살아 있는가(DECISIONS §211).

★ 이 시험이 지키는 것은 「절이 참이다」 가 아니라 **「바뀌면 무효가 된다」** 다. 뜻은 사람이 본다.
"""
from __future__ import annotations

import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("docseal", ROOT / "tools/docseal.py")
DS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(DS)

절 = ("## §9. 무엇이 있었나\n\n**2026-09-29**\n\n### 배운 것\n\n어떤 말.\n\n"
      "강제자 — `tools/docseal.py::로직_지문`\n")


def test_이름을_짚으면_그_몸만_잰다(tmp_path):
    """★ 파일로 재면 `check_docs.py` 를 짚은 절 스무 개가 한꺼번에 무효가 된다 — **소음이 된다.**"""
    p = tmp_path / "x.py"
    p.write_text("def a():\n    return 1\n\n\ndef b():\n    return 2\n", encoding="utf-8")
    앞 = DS.로직_지문(p, "a")
    p.write_text("def a():\n    return 1\n\n\ndef b():\n    return 99\n", encoding="utf-8")
    assert DS.로직_지문(p, "a") == 앞, "남의 몸이 바뀌었는데 내 도장이 찢어졌다"
    assert DS.로직_지문(p, "b") != 앞


def test_주석과_독스트링은_도장을_안_찢는다(tmp_path):
    p = tmp_path / "x.py"
    p.write_text("def a():\n    return 1\n", encoding="utf-8")
    앞 = DS.로직_지문(p, "a")
    p.write_text('def a():\n    """새 설명."""\n    # 새 주석\n    return 1\n', encoding="utf-8")
    assert DS.로직_지문(p, "a") == 앞


def test_짚은_이름이_사라지면_다시_보라고_한다(tmp_path):
    p = tmp_path / "x.py"
    p.write_text("def a():\n    return 1\n", encoding="utf-8")
    assert DS.로직_지문(p, "없는이름") == "없다"


def test_본문이_바뀌어도_무효다():
    """양쪽 다 도장이 덮는다 — 코드만이 아니라 **절 본문**도."""
    하나 = DS.절들(절)[0]
    둘 = DS.절들(절.replace("어떤 말", "다른 말"))[0]
    assert DS.지문(하나) != DS.지문(둘)


def test_강제자가_없는_절은_대상이_아니다():
    글 = "## §9. 무엇\n\n**2026-09-29**\n\n### 배운 것\n\n말.\n"
    assert DS.절들(글)[0]["파일"] == []


def test_저장소의_도장이_유효하다():
    """★ **찍어 놓고 안 보면 도장은 장식이다**(§170 과 같은 병)."""
    assert DS.main([]) == 0


def test_저장소에_없는_파일은_도장이_안_문다():
    """★ **도장이 기계를 타면 도장이 아니다**(DECISIONS §212).

    `data/domain/*.jsonl` 은 커밋하지 않는다 — 만드는 쪽에는 있고 받는 쪽에는 없다. 그것을 지문에
    넣으면 같은 커밋에서 한쪽만 무효가 된다. 2026-09-29 §192 가 그렇게 떴다.
    """
    글 = ("## §9. 무엇\n\n**2026-09-29**\n\n### 배운 것\n\n말.\n\n"
          "강제자 — `data/domain/d002.jsonl` · `tools/docseal.py::지문`\n")
    파일 = DS.절들(글)[0]["파일"]
    assert not any(f.startswith("data/domain/") for f in 파일), 파일
    assert any(f.startswith("tools/docseal.py") for f in 파일)


def test_줄_대장은_부른_행만_문다():
    """★ **소음이 된 무효는 안 읽힌다**(DECISIONS §215).

    `hypotheses.md` 는 194 행이라 가설 하나를 열고 닫을 때마다 바뀐다. 파일로 물면 그 대장을 짚은
    절이 전부 무효가 되고, 아홉 중 여덟은 **내가 안 건드린 남의 행** 탓이다.
    """
    대장 = "| H-001 | 채택 | R1 | 가 | 나 | 0 | 다 |\n| H-079 | 실험 | R7 | 가 | 나 | 0 | |\n"
    본문 = "## §9. 무엇\n\n**2026-09-29**\n\n### 배운 것\n\nH-079 를 연다.\n"
    앞 = DS._대장_조각("docs/next/hypotheses.md", 본문, 대장)
    assert 앞, "부른 행을 못 찾았다"
    # 남의 행이 바뀌어도 그대로다
    assert DS._대장_조각("docs/next/hypotheses.md", 본문,
                        대장.replace("| H-001 | 채택 |", "| H-001 | 기각 |")) == 앞
    # 내 행이 바뀌면 달라진다
    assert DS._대장_조각("docs/next/hypotheses.md", 본문,
                        대장.replace("| H-079 | 실험 |", "| H-079 | 채택 |")) != 앞
    # 아무 행도 안 부르면 그 파일은 지문 밖이다
    assert DS._대장_조각("docs/next/hypotheses.md", "## §9. 무엇\n\n번호가 없다.\n", 대장) == ""


def test_무더기로_읽었다를_못_찍는다(tmp_path, monkeypatch, capsys):
    """★ **찍는 것과 읽는 것은 다르다**(DECISIONS §217). 한꺼번에 「읽었다」 를 찍으면 그 표시가
    아무것도 안 말하고, 그 순간 감사의 수가 진도를 잃는다."""
    assert DS.main(["stamp", "--read"]) == 1
    assert "--only" in capsys.readouterr().err
