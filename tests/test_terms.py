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


def test_여러_종류를_한_번에_뺀다():
    """종류마다 따로 부르면 앞의 것이 뒤의 자리를 민다(DECISIONS §152).

    2026-09-28 `lit` 을 먼저 빼고 `ui` 를 부르자 자리 검사가 멈췄다 — **멈춘 것이 옳았다.**
    """
    숨, 표 = terms.hide_all("Set books-policy under Encryption here.",
                            [([["books-policy", 4]], "L"), ([["Encryption", 23]], "U")])
    assert 숨 == "Set ⟦L1⟧ under ⟦U1⟧ here."
    assert 표["L"]["L1"]["text"] == "books-policy" and 표["U"]["U1"]["text"] == "Encryption"


def test_두_종류를_빼고_되돌린다():
    from seshat import backends
    본것 = []

    def 그대로(texts, terms_, marks=None):
        본것.extend(texts)
        return list(texts)

    got = backends.with_marks_hidden(그대로, kinds=(("lit", "L"), ("ui", "U")))(
        ["Set books-policy under Encryption here."], {},
        [{"lit": [["books-policy", 4]], "ui": [["Encryption", 23]]}])
    assert 본것 == ["Set ⟦L1⟧ under ⟦U1⟧ here."]
    assert got == ["Set books-policy under Encryption here."]


def test_표시된_글자를_둘_다_뺀_팔이_있다():
    from seshat import backends
    새, 옛 = ("gemma3-4b+ph+marks+gloss2+retry+endings+terms",
             "gemma3-4b+ph+gloss2+retry+endings+terms")
    assert 새 in backends.REGISTRY and 새 in backends.REPAIR_ARMS
    assert backends.DECODING_OF[새] == backends.DECODING_OF[옛]
    assert backends.WEIGHTS[새] == backends.WEIGHTS[옛]


def test_잃은_표시를_센다():
    """사라진 자리표시는 **모델이 그 조각을 버린 것**이다 — 세지 않으면 안 보인다(DECISIONS §154)."""
    from seshat import backends
    backends.MARKS_STATS.update({"뺀 것": 0, "잃은 것": 0, "다시 물음": 0, "되찾음": 0})
    backends.with_marks_hidden(lambda t, x, m=None: ["다 버렸습니다."],
                               kinds=(("lit", "L"), ("ui", "U")))(
        ["Set books-policy under Encryption here."], {},
        [{"lit": [["books-policy", 4]], "ui": [["Encryption", 23]]}])
    assert backends.MARKS_STATS == {"뺀 것": 2, "잃은 것": 2, "다시 물음": 0, "되찾음": 0}


def test_지켜지면_잃은_것이_0_이다():
    from seshat import backends
    backends.MARKS_STATS.update({"뺀 것": 0, "잃은 것": 0, "다시 물음": 0, "되찾음": 0})
    backends.with_marks_hidden(lambda t, x, m=None: list(t), kinds=(("lit", "L"),))(
        ["Set books-policy here."], {}, [{"lit": [["books-policy", 4]]}])
    assert backends.MARKS_STATS == {"뺀 것": 1, "잃은 것": 0, "다시 물음": 0, "되찾음": 0}


def test_표시를_빼는_팔이_머리줄에_실린다():
    """처치가 일했는지를 결과가 말한다(DECISIONS §60 과 같은 규율)."""
    from seshat import backends
    assert backends.MARK_ARMS <= set(backends.REGISTRY)
    assert "gemma3-4b+ph+marks+gloss2+retry+endings+terms" in backends.MARK_ARMS


def test_사라진_표시를_숨긴_글로_다시_묻는다():
    """원문을 주면 표시 보호가 풀린다 — §149 가 조사에서 본 것과 같은 자리(DECISIONS §154)."""
    from seshat import backends
    backends.MARKS_STATS.update({"뺀 것": 0, "잃은 것": 0, "다시 물음": 0, "되찾음": 0})
    본것 = []

    def 버린다(texts, terms_, marks=None):
        return ["다 버렸습니다."]

    def 고친다(texts, terms_, marks=None):
        본것.extend(texts)
        return ["⟦L1⟧ 아래 ⟦U1⟧ 입니다."]

    got = backends.with_marks_hidden(버린다, kinds=(("lit", "L"), ("ui", "U")), repair=(고친다,))(
        ["Set books-policy under Encryption here."], {},
        [{"lit": [["books-policy", 4]], "ui": [["Encryption", 23]]}])
    assert 본것 == ["Set ⟦L1⟧ under ⟦U1⟧ here."], "고치는 판에 원문을 주면 보호가 풀린다"
    assert got == ["books-policy 아래 Encryption 입니다."]
    assert backends.MARKS_STATS["되찾음"] == 1 and backends.MARKS_STATS["잃은 것"] == 0


def test_다시_물어도_안_되면_첫_답을_둔다():
    """없는 것을 지어 넣지 않는다 — `with_placeholders` 와 같은 규율(DECISIONS §60)."""
    from seshat import backends
    backends.MARKS_STATS.update({"뺀 것": 0, "잃은 것": 0, "다시 물음": 0, "되찾음": 0})
    got = backends.with_marks_hidden(lambda t, x, m=None: ["버렸습니다."], kinds=(("lit", "L"),),
                                     repair=(lambda t, x, m=None: ["또 버렸습니다."],))(
        ["Set books-policy here."], {}, [{"lit": [["books-policy", 4]]}])
    assert got == ["버렸습니다."]
    assert backends.MARKS_STATS["되찾음"] == 0 and backends.MARKS_STATS["잃은 것"] == 1


def test_되묻는_팔이_하나만_다르다():
    from seshat import backends
    새, 옛 = ("gemma3-4b+ph+marks2+gloss2+retry+endings+terms",
             "gemma3-4b+ph+marks+gloss2+retry+endings+terms")
    assert 새 in backends.REGISTRY and 새 in backends.MARK_ARMS
    assert backends.DECODING_OF[새] == backends.DECODING_OF[옛]
