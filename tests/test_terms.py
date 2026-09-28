"""이름 뒤 조사 — **자리표시를 안 거친 글에도** 같은 규칙이 선다(DECISIONS §149).

★ 모델을 안 부른다. 고치는 규칙만 본다.
"""
from seshat import ontology, terms

ONTO = ontology.load()


def 자리(src: str) -> dict:
    return terms.mask(ONTO, src)[1]


def test_자리표시_없는_글에도_조사를_맞춘다():
    """고치는 판은 원문을 주므로 `⟦Tn⟧` 이 없다 — 그래도 조사는 서야 한다.

    2026-09-28 `keep` 이 0.9979 로 오르는 동안 `josa` 가 구성상 1.000 에서 0.9918 로 내려갔다.
    고치는 판이 **이름은 살리고 조사는 버린** 자국이다.
    """
    slots = 자리("Amazon EMR first provisions EC2 instances in the cluster.")
    assert terms.fix_particles("Amazon EMR는 EC2을 씁니다.", slots) == "Amazon EMR은 EC2를 씁니다."


def test_맞는_조사는_안_건드린다():
    slots = 자리("Amazon EMR provisions EC2.")
    같 = "Amazon EMR은 EC2를 씁니다."
    assert terms.fix_particles(같, slots) == 같


def test_서술격은_조사가_아니다():
    """`⟦T1⟧이다` 의 `이` 는 서술격이다 — `_AFTER` 와 같은 규칙이 여기에도 선다."""
    slots = 자리("Amazon EMR provisions instances.")
    assert terms.fix_particles("이것은 Amazon EMR이다.", slots) == "이것은 Amazon EMR이다."


def test_긴_이름부터_본다():
    """`Amazon EMR` 을 `EMR` 로 먼저 잡으면 앞이 남는다."""
    slots = {"T1": {"text": "Amazon EMR", "coda": "rieul"}, "T2": {"text": "EMR", "coda": "rieul"}}
    assert terms.fix_particles("Amazon EMR는 빠르다.", slots) == "Amazon EMR은 빠르다."


def test_끝소리를_모르면_그대로_둔다():
    """짐작해서 고치면 맞던 것을 틀리게 만든다."""
    assert terms.fix_particles("Foo는 좋다.", {"T1": {"text": "Foo", "coda": None}}) == "Foo는 좋다."


def test_되돌리기와_같은_답을_준다():
    """같은 규칙이 두 길에 서 있다 — 갈리면 어느 한쪽이 틀린 것이다."""
    src = "Amazon EMR provisions EC2 instances."
    slots = 자리(src)
    통해, _ = terms.unmask("⟦T1⟧는 ⟦T2⟧을 씁니다.", slots)
    직접 = terms.fix_particles("Amazon EMR는 EC2을 씁니다.", slots)
    assert 통해 == 직접 == "Amazon EMR은 EC2를 씁니다."


def test_고치는_판이_조사를_맞춘_답을_쓴다():
    """배선이 실제로 이어졌는가 — `with_placeholders` 가 `fix_particles` 를 거쳐야 한다."""
    from seshat import backends
    src = "Amazon EMR provisions EC2 instances."

    def 이름을_버린다(texts, terms_, marks=None):
        return ["자리표시를 잃은 답입니다."]        # `missing` 을 만들어 고치는 판을 부른다

    def 고친다(texts, terms_, marks=None):
        return ["Amazon EMR는 EC2을 씁니다."]       # 이름은 있고 조사는 틀린 답

    got = backends.with_placeholders(이름을_버린다, repair=(고친다,))([src], {})
    assert got == ["Amazon EMR은 EC2를 씁니다."], got


def test_줄이_아는_자리를_뺀다():
    """콘솔 라벨은 온톨로지가 모른다 — **자리로** 뺀다(DECISIONS §151)."""
    숨, slots = terms.hide("Choose Security Groups and then Type here.",
                           [["Security Groups", 7], ["Type", 32]])
    assert 숨 == "Choose ⟦U1⟧ and then ⟦U2⟧ here."
    assert slots["U1"]["text"] == "Security Groups" and slots["U2"]["coda"] is None


def test_자리가_틀리면_멈춘다():
    """글자가 그 자리에 없으면 셋이 코드와 어긋난 것이다 — 조용히 넘기면 세는 척하는 것이다."""
    import pytest
    with pytest.raises(SystemExit, match="자리가 틀리다"):
        terms.hide("Choose Security Groups.", [["Security Groups", 0]])


def test_뒤에서부터_자른다():
    """앞을 먼저 바꾸면 뒤 자리가 밀린다 — 라벨 길이가 서로 다르면 바로 드러난다."""
    숨, _ = terms.hide("AAAA and BB end.", [["AAAA", 0], ["BB", 9]])
    assert 숨 == "⟦U1⟧ and ⟦U2⟧ end."


def test_되돌리기가_글자를_인자로_받는다():
    """`T` 와 `U` 가 모양을 바꾸는 방식은 같다 — 정규식이 하나여야 한다(DECISIONS §151)."""
    _, slots = terms.hide("Choose Security Groups.", [["Security Groups", 7]])
    for 모양 in ("⟦U1⟧에서", "[U1]에서", "\\[U1\\]에서", "【U1】에서", "`U1`에서"):
        got, missing = terms.unmask(모양 + " 고릅니다.", slots, letter="U")
        assert got == "Security Groups에서 고릅니다." and missing == []


def test_끝소리를_모르면_조사를_안_고친다():
    """임의의 영어 라벨의 읽기는 사전에 없다 — 짐작하면 맞던 것을 틀리게 만든다."""
    _, slots = terms.hide("Open the Type field.", [["Type", 9]])
    assert terms.unmask("⟦U1⟧을 엽니다.", slots, letter="U")[0] == "Type을 엽니다."


def test_줄을_숨기는_팔이_되돌려_준다():
    """배선 — `with_marks_hidden` 이 빼고 되돌리는 한 바퀴."""
    from seshat import backends
    본것 = []

    def 그대로(texts, terms_, marks=None):
        본것.extend(texts)
        return [t.replace("Choose", "고릅니다") for t in texts]

    got = backends.with_marks_hidden(그대로)(["Choose Security Groups."], {},
                                            [{"ui": [["Security Groups", 7]]}])
    assert 본것 == ["Choose ⟦U1⟧."], "모델은 라벨을 못 본다 — 그것이 이 처치다"
    assert got == ["고릅니다 Security Groups."]


def test_표시가_없으면_아무것도_안_한다():
    from seshat import backends
    got = backends.with_marks_hidden(lambda t, x, m=None: list(t))(["그대로"], {}, [{}])
    assert got == ["그대로"]
