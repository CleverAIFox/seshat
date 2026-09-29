"""**막는 자리마다 넘는 길이 있는가** — 그 검사가 살아 있는가(DECISIONS §210).

★ 이 시험이 지키는 것은 「길이 다 있다」 가 아니라 **「길 없는 자리가 늘지 않는다」** 다.
  서른 곳을 하루에 고치는 것은 거짓말이고, 새로 생기는 것을 막는 것은 오늘 할 수 있다.
"""
from __future__ import annotations

import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("check_ways", ROOT / "tools/check_ways.py")
CW = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CW)


def _나무(tmp_path, 글: str) -> pathlib.Path:
    for d in ("seshat", "tools"):
        (tmp_path / d).mkdir(exist_ok=True)
    (tmp_path / "tools/x.py").write_text(글, encoding="utf-8")
    return tmp_path


def test_길_없는_막음을_찾는다(tmp_path):
    자리 = CW.길없는자리(_나무(tmp_path, 'raise SystemExit("셋이 없다 — 못 잰다")\n'))
    assert [x[0] for x in 자리] == ["tools/x.py"]


def test_길이_있으면_안_잡는다(tmp_path):
    글 = 'raise SystemExit("셋이 없다\\n    만든다 : python3 tools/fetch_awsdocs.py --name d003")\n'
    assert CW.길없는자리(_나무(tmp_path, 글)) == []


def test_길을_바로_위에서_지어도_본다(tmp_path):
    """넘는 길이 변수에 담기는 자리가 있다 — **앞 일곱 줄까지** 같이 읽는다."""
    글 = ('길 = "    붙인다 : bash tools/apply_patch.sh"\n'
          'raise SystemExit("안 붙는다" + 길)\n')
    assert CW.길없는자리(_나무(tmp_path, 글)) == []


def test_종료_코드는_말이_아니다(tmp_path):
    assert CW.길없는자리(_나무(tmp_path, "raise SystemExit(2)\n")) == []


def test_자가시험의_소리는_안_센다(tmp_path):
    """`_selftest` 는 사람에게 하는 말이 아니라 **죽은 검사를 알리는 소리**다."""
    글 = 'def _selftest():\n    print("  ✗ 같은 둘에서 차이를 본다")\n'
    assert CW.길없는자리(_나무(tmp_path, 글)) == []


def test_늘면_막고_줄면_안_막는다():
    assert CW.견준다({"a.py": 3}, {"a.py": 2}), "늘었는데 조용하다"
    assert CW.견준다({"새파일.py": 1}, {}), "없던 파일에 생겼는데 조용하다"
    assert CW.견준다({"a.py": 1}, {"a.py": 2}) == [], "줄어든 것은 잘한 일이지 실패가 아니다"
    assert CW.견준다({}, {"a.py": 2}) == []


def test_저장소가_장부와_맞는다():
    """★ **장부가 실물보다 늦으면 이 도구는 거짓 초록을 낸다**(§170 과 같은 병).

    줄었으면 이 시험은 안 깨진다 — `--update` 로 박으라고 도구가 말한다. 늘면 깨진다.
    """
    assert CW.main([]) == 0
