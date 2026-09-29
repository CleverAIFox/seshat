"""견줄 수 있는가 — 축이 **한 곳에만** 적혀 있다(DECISIONS §157).

★ 2026-09-28 하루에 같은 병을 여덟 번 앓았다. 까닭은 조건이 다섯 곳에 손으로 적혀 있던 것이다.
"""
import pathlib
import re

from seshat import compare

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_없는_값은_같음이_아니다():
    """옛 판에는 `metrics` 가 아예 없다 — 그것을 같음으로 치면 자를 바꾸기 전후가 조용히 섞인다."""
    갈린 = compare.갈림({"metrics": "2"}, {}, ("metrics",))
    assert 갈린 and 갈린[0].이름 == "자"


def test_같으면_비었다():
    가 = {"set_sha256": "x", "onto_sha256": "y", "metrics": "2", "backend": "팔"}
    assert compare.갈림(가, dict(가), compare.AA) == []


def test_AA_는_팔까지_본다():
    """같은 팔 두 판이어야 그 차이가 잡음이다."""
    가 = {"set_sha256": "x", "metrics": "2", "backend": "가팔"}
    assert [g.키 for g in compare.갈림(가, {**가, "backend": "나팔"}, compare.AA)] == ["backend"]
    assert compare.갈림(가, {**가, "backend": "나팔"}, compare.AB) == []


def test_문은_사전을_안_막는다():
    """사전을 막으면 사전을 영영 못 고친다(DECISIONS §32 · §96)."""
    assert "onto_sha256" not in compare.GATE_막
    assert "set_sha256" in compare.GATE_막 and "metrics" in compare.GATE_막


def test_보호는_그_지표만_가린다():
    """통째로 막지 않는다 — `term_off` 는 양쪽 다 모델이 만든 값이다(DECISIONS §156).

    ★ **무엇을 지키는지는 팔이 안다**(DECISIONS §186). 기록판에 손으로 적던 `protects` 칸은
      지웠다 — 거기 `keep` 이 빠져 있었고, 빠진 것을 아무도 못 봤다(§182).
    """
    우리 = {"arm": "gemma3-4b+ph+marks2+gloss2+retry+endings+terms"}
    nova = {"arm": "nova-lite (thoth 워커)"}
    십이 = {"arm": "gemma3-12b+ph+retry+endings+terms"}
    assert compare.가린_지표(우리, nova) == {"keep", "lit", "ui"}
    assert compare.가린_지표(우리, 십이) == {"lit", "ui"}, "둘 다 +ph 라 keep 은 견준다"
    assert compare.가린_지표(우리, dict(우리)) == set()
    assert compare.가린_지표({"backend": 우리["arm"]}, {"model": 우리["arm"]}) == set(), "칸 이름이 달라도 본다"


def test_기록판에_보호를_손으로_안_적는다():
    """★ **§163 의 병이 여기 있었다** — 같은 판단이 기록판과 코드 두 곳에 있었고, 기록판 쪽이
    낡아 있었다(DECISIONS §186). 칸을 되살리면 다시 갈린다."""
    import pathlib as _p
    판 = (_p.Path(__file__).resolve().parents[1] / "data/scoreboard.toml").read_text(encoding="utf-8")
    적힌줄 = [x for x in 판.splitlines() if x.startswith("protects")]
    assert not 적힌줄, f"기록판이 보호를 손으로 든다 — {적힌줄}"


def test_축을_손으로_다시_적은_곳이_없다():
    """**이 시험이 §157 의 강제자다.** 축을 또 손으로 적으면 반드시 한 곳이 빠진다.

    2026-09-28 문의 `check` · 문의 선 줄 · `noise.SAME` · `compare_runs` 넷에 따로 적혀 있었고
    그중 셋이 서로 달랐다(§146 · §147 · §156).
    """
    쓰는곳 = ("tools/gate.py", "tools/noise.py", "tools/compare_runs.py")
    나쁜 = []
    for f in 쓰는곳:
        줄들 = (ROOT / f).read_text(encoding="utf-8").splitlines()
        for i, 줄 in enumerate(줄들, 1):
            몸 = 줄.split("#", 1)[0]
            if re.search(r'(get|\[)\("?(set_sha256|onto_sha256|metrics)"?\)?\s*!=', 몸):
                나쁜.append(f"{f}:{i} {줄.strip()[:80]}")
    assert not 나쁜, "축을 손으로 견주는 줄이 남았다 — `seshat/compare.py` 를 쓴다\n" + "\n".join(나쁜)


def test_조사를_손으로_또_적은_곳이_없다():
    """2026-09-28 이 목록이 네 곳에 있었고 그중 하나는 그날 새로 적은 것이었다(DECISIONS §158)."""
    나쁜 = []
    for f in (*ROOT.glob("seshat/*.py"), *ROOT.glob("tools/*.py")):
        for i, 줄 in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if "이나|이라" in 줄.split("#", 1)[0]:
                나쁜.append(f"{f.name}:{i} {줄.strip()[:60]}")
    assert not 나쁜, "조사 목록은 `terms.JOSA` 에서 만든다\n" + "\n".join(나쁜)


def test_조사_목록이_짝에서_나온다():
    """낱말을 두 번 적으면 한쪽만 고쳐진다 — `JOSA` 는 `_PAIRS` 가 든 것과 같아야 한다."""
    from seshat import terms
    assert set(terms.JOSA) == {x for 짝 in terms._PAIRS for x in 짝}


def test_자리_검사가_한_곳에만_있다():
    """`evaluate.marked` · `hide` · `hide_all` 셋에 손으로 적혀 있었다(DECISIONS §158)."""
    나쁜 = []
    for f in (*ROOT.glob("seshat/*.py"), *ROOT.glob("tools/*.py")):
        for i, 줄 in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            몸 = 줄.split("#", 1)[0]
            if re.search(r"\[at\s*:\s*at\s*\+\s*len\(", 몸) and "!=" in 몸:
                나쁜.append(f"{f.name}:{i} {줄.strip()[:60]}")
    assert len(나쁜) == 1 and 나쁜[0].startswith("terms.py:"), \
        "자리를 보는 규칙은 `terms.제자리인가` 하나뿐이다\n" + "\n".join(나쁜)


def test_긴_조사가_앞이다():
    """짧은 것이 앞이면 `으로` 를 `로` 로 집고 앞부분이 남는다."""
    from seshat import terms
    for 짧, 김 in (("로", "으로"), ("나", "이나"), ("라", "이라")):
        assert terms.JOSA.index(김) < terms.JOSA.index(짧), f"{김} 이 {짧} 보다 앞이어야 한다"


def test_사본_세는_도구의_프로브가_살아_있다():
    """아무것도 안 찾는 검사와 고장 난 검사는 구별되지 않는다(DECISIONS §163)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("dup", ROOT / "tools/dupcheck.py")
    dup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dup)
    assert dup.main(["--selftest"]) == 0


def test_사본_세기가_글자도_본다():
    """함수만 보는 도구였으면 2026-09-28 의 사본 넷을 하나도 못 잡았다 — 전부 상수였다."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("dup", ROOT / "tools/dupcheck.py")
    dup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(dup)
    assert hasattr(dup, "글자_사본"), "긴 글자 사본을 세는 자리가 있어야 한다"


def test_사전축은_둘_다_들었을_때만_채점지문을_쓴다():
    """★ **옛 판과 안 갈라선다**(DECISIONS §171). 한쪽이라도 그 칸이 없으면 옛 바이트 해시로 묻는다 —
    「값이 없다」 를 「같다」 로 치는 것이 아니라 **옛 축으로 묻는 것**이다."""
    새, 새2 = {"onto_sha256": "가", "onto_score": "ㄱ"}, {"onto_sha256": "나", "onto_score": "ㄱ"}
    옛 = {"onto_sha256": "가"}
    assert compare.사전축(새, 새2) == "onto_score"
    assert compare.갈림(새, 새2, ("onto_sha256",)) == [], "뜻이 같으면 바이트가 달라도 안 막는다"
    assert compare.사전축(새, 옛) == "onto_sha256"
    assert compare.갈림(새, 옛, ("onto_sha256",)) == [], "옛 축으로는 같다"
    assert compare.갈림(새2, 옛, ("onto_sha256",)), "옛 축으로 다르면 갈린 것이다"


def test_채점지문은_점수를_안_바꾸는_칸을_무시한다():
    """★ **해시의 범위는 「파일」 이 아니라 「채점기가 읽는 것」 이다**(DECISIONS §171)."""
    from seshat import ontology
    가 = [{"id": "con.a", "kind": "concept", "en": "A", "keep": False, "ko": "가",
           "src": "author", "ko_ref": "s3/dev"}]
    나 = [{**가[0], "src": "thoth-glossary", "ko_ref": "athena/ug", "note": "딴 말"}]
    다 = [{**가[0], "ko": "나"}]
    assert ontology.채점_지문(가) == ontology.채점_지문(나), "출처를 고쳐도 점수는 안 바뀐다"
    assert ontology.채점_지문(가) != ontology.채점_지문(다), "표기를 고치면 점수가 바뀐다"


def test_채점칸이_빠지면_거짓_초록이_된다():
    """★ **칸을 더할 때 지문에도 더한다**(DECISIONS §171). 안 더하면 새 칸이 점수를 바꾸는데
    지문은 그대로다 — **거짓 초록**이고 그쪽이 거짓 빨강보다 나쁘다."""
    from seshat import ontology
    읽는것 = {"id", "kind", "en", "aliases", "keep", "coda", "ko", "alt_ko", "bad_ko"}
    assert set(ontology.채점칸) == 읽는것
    # **점수를 안 바꾸는 칸** — 여기 이름이 있다는 것은 「읽는 코드가 없음을 확인했다」 는 뜻이다.
    # `category` 는 41 노드가 들고 있는데 **읽는 코드가 하나도 없다**(2026-09-28 실측) — #22 의 관계
    # 작업이 쓸 자리이고, 쓰기 시작하면 점수를 바꾸는지 다시 묻고 채점칸에 넣는다
    안읽는칸 = {"src", "ko_ref", "parent", "note", "meta", "about", "category"}
    실물 = {k for n in ontology.load() for k in n}
    빠진 = 실물 - set(ontology.채점칸) - 안읽는칸
    assert not 빠진, f"사전에 새 칸이 생겼다 — 점수를 바꾸는 칸이면 채점칸에 더한다: {sorted(빠진)}"


def test_사전축이_고르는_이름은_둘_다_표에_있다():
    """★ **고르는 자리와 답하는 자리가 갈리면 고르는 쪽이 먼저 는다**(DECISIONS §203).

    2026-09-29 `AXIS["onto_score"]` 가 없어서, 둘 다 채점 지문을 들고 그것이 갈린 쌍에서
    `갈림` 이 KeyError 로 터졌다. 도구가 **막는 대신 죽었다.**
    """
    from seshat import compare as C
    for 가, 나 in (({"onto_score": "a"}, {"onto_score": "b"}), ({}, {})):
        assert C.사전축(가, 나) in C.AXIS


def test_채점칸이_갈리면_막지_않고_재채점을_이른다():
    from seshat import compare as C
    갈린 = C.갈림({"onto_score": "a", "onto_sha256": "x"},
                 {"onto_score": "b", "onto_sha256": "y"}, ("onto_sha256",))
    assert len(갈린) == 1
    assert "rescore.py" in 갈린[0].글(), "막기만 하고 어떻게 견줄지를 안 말한다"
