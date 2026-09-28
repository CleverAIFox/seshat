"""논문 감시 — 못 재면 빨간불 · 번역 밖은 안 줍는다 · 대장에 있는 것은 다시 안 올린다(DECISIONS §126).

★ **망을 안 탄다.** `fetch` 를 바꿔치기해서 파싱과 거르기만 본다. 실제 응답이 맞는지는 워크플로가 말한다.
"""
import importlib.util
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("watch_papers", ROOT / "tools/watch_papers.py")
W = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(W)

ATOM = """<feed>
<entry>
  <id>http://arxiv.org/abs/2609.11111v1</id>
  <published>2026-09-20T00:00:00Z</published>
  <title>Distilling Small Translation Models for Korean</title>
  <summary>We distill a 2B student. It beats the teacher on en-ko.</summary>
</entry>
<entry>
  <id>http://arxiv.org/abs/2609.22222v1</id>
  <published>2026-09-21T00:00:00Z</published>
  <title>Quantization of Vision Transformers</title>
  <summary>We quantize a ViT for image classification on edge devices.</summary>
</entry>
<entry>
  <id>http://arxiv.org/abs/2508.14909v3</id>
  <published>2026-09-22T00:00:00Z</published>
  <title>Preliminary Ranking of WMT25 General MT Systems</title>
  <summary>Automatic ranking of translation systems with quality estimation.</summary>
</entry>
</feed>"""


def test_번역_이야기가_아니면_안_줍는다():
    """`quantization` 은 번역 밖에서 훨씬 자주 나온다 — 주제어만 보면 목록이 쓰레기가 된다."""
    assert W.topics_of("Quantization of Vision Transformers for edge devices") == ()
    assert "양자화" in W.topics_of("Quantization for multilingual translation models")


@pytest.mark.parametrize("text,축", [
    ("A Korean translation benchmark", "영한"),
    ("Distillation for machine translation", "소형"),
    ("GPTQ int4 translation models", "양자화"),
    ("Reference-free quality estimation of translation", "QE"),
    ("GRPO for multilingual translation", "강화학습"),
])
def test_주제마다_걸린다(text, 축):
    assert 축 in W.topics_of(text)


def test_Atom_을_읽고_번역_밖은_버린다(monkeypatch):
    monkeypatch.setattr(W, "fetch", lambda *a, **k: ATOM.encode())
    got = W.arxiv(8)
    assert [x["id"] for x in got] == ["2609.11111", "2508.14909"]     # ViT 는 빠졌다
    assert got[0]["제목"].startswith("Distilling") and got[0]["날짜"] == "2026-09-20"


def test_항목이_하나도_없으면_빨간불이다(monkeypatch):
    """조용한 0 건은 「새 논문이 없다」 로 읽힌다 — 질의가 깨진 것과 구별이 안 된다."""
    monkeypatch.setattr(W, "fetch", lambda *a, **k: b"<feed></feed>")
    with pytest.raises(SystemExit, match="0 건이 아니다"):
        W.arxiv(8)


def test_못_물으면_죽는다(monkeypatch):
    def 죽는다(*a, **k):
        raise OSError("안 열린다")
    monkeypatch.setattr(W.urllib.request, "urlopen", 죽는다)
    with pytest.raises(SystemExit, match="0 건이 아니다"):
        W.fetch("https://어딘가/x")


def test_대장에_있는_논문은_다시_안_올린다():
    """`docs/next/papers.md` 는 `arXiv 2508.14909` 꼴로 적는다."""
    본문 = (ROOT / "docs/next/papers.md").read_text(encoding="utf-8")
    assert "2508.14909" in W.seen(본문)


def test_라이선스는_미확인으로_적는다(monkeypatch):
    """HF 목록의 태그를 믿지 않는다 — 붙일 때 `seshat/licenses.py` 가 다시 묻는다."""
    monkeypatch.setattr(W, "fetch", lambda *a, **k: b'[{"id":"acme/ko-mt","createdAt":"2099-01-01T00:00:00.000Z",'
                                                    b'"tags":["translation","ko"]}]')
    got = W.hugging(8)
    assert got and got[0]["라이선스"] == "미확인"


def test_읽을_것_아래에만_붙인다():
    """표 본문의 「무엇을 했나 · 가져올 것」 은 읽은 사람이 쓴다 — 도구가 그 칸을 안 채운다."""
    본문 = (ROOT / "docs/next/papers.md").read_text(encoding="utf-8")
    새 = W.write(본문, ["- **arXiv 2026-09-27** 새 줄"], "2026-09-27")
    앞, 뒤 = 새.split("## 읽을 것")
    assert "새 줄" in 뒤 and "새 줄" not in 앞
    assert 앞 == 본문.split("## 읽을 것")[0]          # 표는 한 글자도 안 바뀐다


def test_붙일_자리가_없으면_말한다():
    with pytest.raises(SystemExit, match="붙일 자리를 못 찾았다"):
        W.write("# 논문 대장\n표만 있다\n", ["- x"], "2026-09-27")


def test_한국어_없는_번역_모델은_안_줍는다(monkeypatch):
    """목록이 이미 번역 모델이다 — 그중 이 저장소와 상관있는 것만 올린다."""
    monkeypatch.setattr(W, "fetch", lambda *a, **k: b'[{"id":"acme/fr-de","createdAt":"2099-01-01T00:00:00.000Z",'
                                                    b'"tags":["translation","fr","de"]}]')
    assert W.hugging(8) == []


def test_오래된_모델은_안_줍는다(monkeypatch):
    monkeypatch.setattr(W, "fetch", lambda *a, **k: b'[{"id":"acme/ko-mt","createdAt":"2020-01-01T00:00:00.000Z",'
                                                    b'"tags":["translation","ko"]}]')
    assert W.hugging(8) == []
