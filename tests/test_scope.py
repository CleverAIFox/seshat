"""**관문이 제 범위와 생사를 선언하는가** — 그 검사가 살아 있는가(DECISIONS §239).

★ 이 파일은 **seshat 것**이다 — thoth 사본이 아니다(DECISIONS §5).
★ 양성과 음성을 함께 본다. 선언 없는 관문은 **걸리고**, 선언한 관문은 안 걸린다.
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

ROOT = next(p for p in pathlib.Path(__file__).resolve().parents if (p / "tools/check_scope.py").exists())
_spec = importlib.util.spec_from_file_location("cs", ROOT / "tools/check_scope.py")
CS = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CS)

싼것 = ('if __name__ == "__main__":\n    try:\n        sys.exit(main())\n'
        '    except Exception:\n        sys.exit(2)\n')


def _나무(tmp_path: pathlib.Path, 도구들: dict[str, str], 걸음: list[str] | None = None) -> pathlib.Path:
    (tmp_path / "tools").mkdir(parents=True, exist_ok=True)
    for n, 글 in 도구들.items():
        (tmp_path / "tools" / n).write_text(글, encoding="utf-8")
    줄 = 걸음 if 걸음 is not None else [f"step {n[:-3]}  uv run python tools/{n}" for n in 도구들]
    (tmp_path / "tools/verify.sh").write_text("#!/usr/bin/env bash\n" + "\n".join(줄) + "\n", encoding="utf-8")
    return tmp_path


def test_실제_저장소가_통과한다():
    """★ **제 규칙을 스스로 안 지키는 검사는 농담이다** — 이 검사를 켠 판에서 관문이 다 선언한다."""
    assert CS.안한것() == []


def test_카나리아가_산다():
    """★ **카나리아를 `pass` 로 바꿔도 통과하면 그 시험이 죽은 것이다**(DECISIONS §255).
    도는 것과 **판별식을 들고 있는 것**을 함께 본다."""
    import inspect
    assert CS._canary() is None            # 살아 있으면 조용히 돌아온다
    글 = inspect.getsource(CS._canary)
    assert "sys.exit(2)" in 글, "카나리아가 죽었을 때 **고장(2)으로 끝내야 한다**"


def test_둘_다_한_관문은_안_걸린다(tmp_path):
    t = _나무(tmp_path, {"a.py": f'"""잰다.\n\n★ 뜻이 옳은지는 **안 본다**.\n"""\ndef _canary(): ...\n{싼것}'})
    assert CS.안한것(t) == []


def test_밖을_안_적으면_걸린다(tmp_path):
    """★ **무엇을 보는가만 적힌 관문은 제 한계를 숨긴다** — 파이어레인이 여섯 번 겪은 결함이다."""
    t = _나무(tmp_path, {"a.py": '"""무엇을 보는지만 적는다."""\ndef _canary(): ...\n'})
    안 = CS.안한것(t)
    assert len(안) == 1 and "머리말이" in 안[0][1], 안


def test_자가시험이_없으면_걸린다(tmp_path):
    """★ **아무것도 못 찾는 자와 고장 난 자는 구별되지 않는다.**"""
    t = _나무(tmp_path, {"a.py": '"""잰다. 뜻은 **안 본다**."""\ndef main(): return 0\n'})
    안 = CS.안한것(t)
    assert len(안) == 1 and "자가시험이 없다" in 안[0][1], 안


def test_둘_다_없으면_두_줄이다(tmp_path):
    t = _나무(tmp_path, {"a.py": '"""본다."""\ndef main(): return 0\n'})
    assert len(CS.안한것(t)) == 2, CS.안한것(t)


def test_머리말_밖의_밖말은_안_센다(tmp_path):
    """★ **몸통 어딘가의 「안 본다」 는 선언이 아니다** — 읽는 사람은 머리말을 읽는다."""
    t = _나무(tmp_path, {"a.py": '"""잰다."""\ndef _canary(): ...\n# 여기서는 뜻을 안 본다\n'})
    안 = CS.안한것(t)
    assert len(안) == 1 and "머리말이" in 안[0][1], 안


def test_남의_저장소_사본은_뺀다(tmp_path):
    """★ 고치면 원본과 갈리고 다음 복사가 지운다(DECISIONS §5). **파일이 스스로 말한다.**"""
    t = _나무(tmp_path, {"a.py": '"""thoth 에서 온 **사본이다**.\n\n무엇을 보는지만 적는다.\n"""\n'})
    assert CS.안한것(t) == []


def test_사본_표시는_머리_세_줄만_본다(tmp_path):
    """★ **아래쪽에 「사본이다」 라고 적어 검사를 피하지 못한다.**"""
    t = _나무(tmp_path, {"a.py": '"""본다.\n\n\n\n이 절은 thoth 사본이다.\n"""\n'})
    assert len(CS.안한것(t)) == 2, CS.안한것(t)


def test_없는_파일을_부르면_걸린다(tmp_path):
    t = _나무(tmp_path, {}, 걸음=["step x  uv run python tools/없다.py"])
    안 = CS.안한것(t)
    assert len(안) == 1 and "파일이 없다" in 안[0][1], 안


def test_관문_아닌_도구는_안_본다(tmp_path):
    """★ **범위를 좁게 잡는다** — `rescore` · `slice` 까지 걸면 사람이 검사를 끈다."""
    t = _나무(tmp_path, {"a.py": '"""본다."""\n', "b.py": '"""본다."""\n'},
              걸음=["step a  uv run python tools/a.py", "# tools/b.py 는 관문이 아니다"])
    assert CS.관문들(t) == ["a.py"]


def test_목록을_손으로_안_만든다():
    """★ **verify.sh 에서 뽑는다** — 손 목록은 관문이 늘 때 조용히 낡는다."""
    글 = (ROOT / "tools/check_scope.py").read_text(encoding="utf-8")
    assert "verify.sh" in 글
    assert set(CS.관문들()) >= {"check_scope.py", "docseal.py"}, CS.관문들()


def test_자기_자신도_대상이다():
    """★ **검사를 검사 밖에 두면 그 자리가 곧 빚이다**(DECISIONS §239)."""
    assert "check_scope.py" in CS.관문들()


@pytest.mark.parametrize("긍정", [
    "문서가 가리킨 것이 실재하는지 본다",
    "이 도구는 꼴과 겹침과 빈칸을 전부 검사한다",
    "범위는 저장소 전체이고 모든 파일을 센다",
])
def test_밖말이_긍정문에_안_걸린다(긍정):
    """★ **넓히면 거짓 초록이 된다** — 「무엇을 본다」 만 적은 글이 선언으로 세어지면 안 된다."""
    assert not any(w in 긍정 for w in CS.밖말), 긍정
