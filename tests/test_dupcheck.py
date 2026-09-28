"""사본을 세는 도구가 제구실을 하나(DECISIONS §163 · §171)."""
from __future__ import annotations

import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("dupcheck", ROOT / "tools/dupcheck.py")
D = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(D)

def test_인자가_갈리는_부름을_센다(tmp_path, monkeypatch):
    """★ **2026-09-28 의 아홉 번째 병은 함수도 글자도 아니었다**(DECISIONS §171 · §169).
    `compare.갈림(rec, head, X)` 의 `X` 가 곳마다 달랐고, 앞의 두 탐지기는 그것을 못 봤다."""
    (tmp_path / "가.py").write_text("c.갈림(a, b, ('자',))\nc.갈림(a, b, 막)\n", encoding="utf-8")
    (tmp_path / "나.py").write_text("c.같다(a, b)\nc.같다(a, b)\nxs.append(1)\nxs.append(2)\n",
                                   encoding="utf-8")
    monkeypatch.setattr(D, "ROOT", tmp_path)
    got = D.부름_갈림((".",))
    assert "c.갈림" in got and len(got["c.갈림"]) == 2
    assert "c.같다" not in got, "인자가 같으면 사본이 아니라 쓰임이다"
    assert "xs.append" not in got, "담개는 원래 곳마다 다른 것을 받는다"


def test_꼴이_너무_많으면_다목적_도구다(tmp_path, monkeypatch):
    """★ 갈려서 병이 나는 자리는 **두엇**으로 갈린다. 아흔세 꼴은 사본이 아니라 쓰임이다."""
    (tmp_path / "가.py").write_text("\n".join(f"m.무엇({i})" for i in range(12)) + "\n",
                                   encoding="utf-8")
    monkeypatch.setattr(D, "ROOT", tmp_path)
    assert "m.무엇" not in D.부름_갈림((".",), 최대꼴=8)
    assert "m.무엇" in D.부름_갈림((".",), 최대꼴=20)


def test_이_저장소의_문이_갈리는_자리로_잡힌다():
    """★ **프로브가 진짜 병을 잡나.** 손으로 만든 예제만 잡는 탐지기는 살아 있는지 알 수 없다 —
    §169 를 만든 그 자리가 지금도 목록에 있어야 한다(축을 하나로 모았으니 꼴은 줄었다)."""
    got = D.부름_갈림(("seshat", "tools"))
    assert "compare.갈림" in got, "문의 축 부름이 안 잡힌다 — 탐지기가 죽었다"
