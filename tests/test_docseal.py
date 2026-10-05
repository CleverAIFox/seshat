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
    앞 = DS._대장_조각("docs/hypotheses.md", 본문, 대장)
    assert 앞, "부른 행을 못 찾았다"
    # 남의 행이 바뀌어도 그대로다
    assert DS._대장_조각("docs/hypotheses.md", 본문,
                        대장.replace("| H-001 | 채택 |", "| H-001 | 기각 |")) == 앞
    # 내 행이 바뀌면 달라진다
    assert DS._대장_조각("docs/hypotheses.md", 본문,
                        대장.replace("| H-079 | 실험 |", "| H-079 | 채택 |")) != 앞
    # 아무 행도 안 부르면 그 파일은 지문 밖이다
    assert DS._대장_조각("docs/hypotheses.md", "## §9. 무엇\n\n번호가 없다.\n", 대장) == ""


def test_무더기로_읽었다를_못_찍는다(tmp_path, monkeypatch, capsys):
    """★ **찍는 것과 읽는 것은 다르다**(DECISIONS §217). 한꺼번에 「읽었다」 를 찍으면 그 표시가
    아무것도 안 말하고, 그 순간 감사의 수가 진도를 잃는다."""
    assert DS.main(["stamp", "--read"]) == 1
    assert "--only" in capsys.readouterr().err


def test_PLAN_도_부른_행만_문다():
    """★ §215 를 `hypotheses.md` 에만 적용하고 `PLAN.md` 는 파일째 뒀다(DECISIONS §219)."""
    대장 = "| 43 | 🟡 | 가 | |\n| 47 | 🟡 | 나 | |\n"
    본문 = "## §9. 무엇\n\n**2026-09-29**\n\n### 배운 것\n\nPLAN #47 이 든다.\n"
    앞 = DS._대장_조각("docs/PLAN.md", 본문, 대장)
    assert 앞
    assert DS._대장_조각("docs/PLAN.md", 본문, 대장.replace("| 43 | 🟡 |", "| 43 | 📄 |")) == 앞
    assert DS._대장_조각("docs/PLAN.md", 본문, 대장.replace("| 47 | 🟡 |", "| 47 | 📄 |")) != 앞


def test_아직_안_담긴_파일도_저장소의_파일이다(tmp_path, monkeypatch):
    """★ **찍자마자 무효가 됐다**(DECISIONS §247). `git add` 전에 찍으면 그 파일이 지문 밖이고,
    `add` 하면 안으로 들어와 지문이 바뀐다 — **지문이 내용이 아니라 git 의 형편을 탄다.**"""
    import subprocess
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / ".gitignore").write_text("무시/\n", encoding="utf-8")
    (tmp_path / "담김.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", ".gitignore", "담김.py"], cwd=tmp_path, check=True)
    (tmp_path / "새것.py").write_text("y = 2\n", encoding="utf-8")        # 안 담겼다
    (tmp_path / "무시").mkdir()
    (tmp_path / "무시/데이터.jsonl").write_text("{}\n", encoding="utf-8")  # 무시 목록이다

    monkeypatch.setattr(DS, "ROOT", tmp_path)
    monkeypatch.setattr(DS, "_아는파일", [])
    아는 = DS._깃이_아는_파일()
    assert "담김.py" in 아는
    assert "새것.py" in 아는, "안 담긴 파일이 빠지면 새 도구를 적은 절이 찍자마자 무효가 된다"
    assert "무시/데이터.jsonl" not in 아는, "무시 목록은 기계마다 다르다(DECISIONS §212)"


def test_한글_이름도_그대로_온다(tmp_path, monkeypatch):
    """★ **git 은 한글 이름을 따옴표 씌워 내놓는다** — 그러면 이름이 안 맞아 **조용히 지문 밖**이
    된다(DECISIONS §247). 이 저장소는 판 이름에 한글을 쓴다(`H-083-대조-a`)."""
    import subprocess
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "대조판.jsonl").write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(DS, "ROOT", tmp_path)
    monkeypatch.setattr(DS, "_아는파일", [])
    assert "대조판.jsonl" in DS._깃이_아는_파일()


def test_MASTER_도_봉인이_붙는다():
    """★ **낡는 문서는 DECISIONS 가 아니라 MASTER 다**(DECISIONS §281).

    DECISIONS 는 추가만 하니 구조상 안 낡는다. MASTER 는 「현재」 축이라 **정의상 실물을
    따라가야 하는 유일한 문서**인데 2026-10-02 까지 봉인이 안 걸려 있었고, 소급해서 읽으니
    아홉 자리가 낡아 있었다 — **아홉 다 이 봉인으로 잡히는 꼴**이었다.
    """
    마 = [x for x in DS.절들() if x["번호"].startswith("M") and x["파일"]]
    assert 마, "봉인을 든 MASTER 절이 하나도 없다 — 그 문서가 통째로 대상 밖이다"
    assert all(x["표시"].startswith("MASTER §") for x in 마)
    # 열쇠가 DECISIONS 와 안 겹친다 — 겹치면 옛 도장이 MASTER 절로 읽힌다
    모두 = [x["번호"] for x in DS.절들()]
    assert len(모두) == len(set(모두)), "절 번호가 겹친다"


def test_본문의_봉인_낱말을_봉인_줄로_안_읽는다():
    """★ MASTER 본문에는 「봉인」 이 그냥 나온다(§11-10 이 그렇다). DECISIONS 의 `rfind` 꼴을
    그대로 쓰면 그 절이 **거짓 양성**으로 걸린다 — 2026-10-02 실제로 §11 이 걸렸다."""
    assert DS._봉인_줄("## 11. 데이터 관리\n봉인은 옮겼다 — `tools/docseal.py` 가 그것이다.\n") == ""
    assert "tools/verify.sh" in DS._봉인_줄("## 5. 점검\n봉인 — `tools/verify.sh`\n  까닭.\n")


def test_봉인한_파일이_바뀌면_MASTER_절이_무효가_된다(tmp_path, monkeypatch):
    """**이 시험이 지키는 것은 「절이 참이다」 가 아니라 「바뀌면 무효가 된다」 다.**"""
    절 = next(x for x in DS.절들() if x["번호"] == "M6")        # §6 라이선스 대장
    before = DS.지문(절)
    원 = (ROOT / "seshat/licenses.py")
    글 = 원.read_text(encoding="utf-8")
    try:
        원.write_text(글.replace("LEDGER: dict", "LEDGER2: dict", 1), encoding="utf-8")
        assert DS.지문(절) != before, "봉인한 파일이 바뀌었는데 지문이 같다 — 도장이 안 가른다"
    finally:
        원.write_text(글, encoding="utf-8")
    assert DS.지문(절) == before, "되돌렸는데 지문이 안 돌아왔다"


def test_글로_못_읽는_산출물은_지목에_안_든다():
    """★ **지문이 바이트가 되면 구울 때마다 도장이 찢어진다**(thoth DECISIONS §161 · §298).
    `docs/proposal.docx` 는 토트에서 강제자가 실제로 든다 — 사본이 거기 산다."""
    줄 = "강제자 — `docs/proposal.docx` 와 `tools/a.py` 와 `x/y.png` 와 `z/w.zip`"
    집은것 = [m[0] for m in DS.지목.findall(줄)]
    assert 집은것 == ["tools/a.py"], 집은것


def test_지목확장이_사본의_강제자를_다_덮는다():
    """★ **목록이 좁으면 그 줄들이 조용히 안 세어진다**(§298). 안 세어진 것은 **안 낡는
    것처럼 보인다** — 토트 강제자는 `.js` · `.json` · `.tf` · `.css` 를 든다."""
    for 확 in ("py", "sh", "js", "json", "jsonl", "md", "yml", "tf", "css", "toml"):
        assert 확 in DS.지목확장, 확
    # ★ 긴 것이 앞이다 — 짧은 쪽이 먼저면 `.jsonl` 이 백틱을 못 닫는다
    assert DS.지목확장.index("jsonl") < DS.지목확장.index("json")
    assert DS.지목확장.index("yaml") < DS.지목확장.index("yml")
    assert DS.지목.findall("`a/b.jsonl`")[0][0] == "a/b.jsonl"


def test_강제자_블록을_줄_머리로_못_박는다():
    """★ **`rfind("강제자")` 는 시험 이름에 그 낱말이 있으면 빈손이 된다**(§299).
    `test_지목확장이_사본의_강제자를_다_덮는다` 가 실제로 그랬다 — 창이 그 뒤부터
    열리고, 파일을 하나도 못 집은 절의 도장은 **아무것도 안 보며 영영 유효**하다."""
    본문 = ("## §1. 제목\n\n**2026-01-01**\n\n본문\n\n"
            "강제자 — `tools/a.py` 의 `무엇` ·\n`tests/test_a.py` 의 `test_강제자를_다_본다`\n")
    앵 = DS._강제자_뒤(본문)
    assert 앵.startswith("강제자 — "), 앵
    집은것 = sorted(m[0] for m in DS.지목.findall(앵))
    assert 집은것 == ["tests/test_a.py", "tools/a.py"], 집은것


def test_산문이_든_파일을_강제자로_안_센다():
    """★ **창이 너무 넓으면 반대로 틀린다**(§299). 본문에 「강제자」 가 먼저 나오면
    `rfind` 가 그 자리부터 열어 **산문이 든 파일까지** 집었다 — 실측 세 절."""
    본문 = ("## §1. 제목\n\n**2026-01-01**\n\n"
            "강제자가 없던 때 `tools/옛것.py` 를 봤다\n\n"
            "강제자 — `tools/지금것.py`\n")
    집은것 = [m[0] for m in DS.지목.findall(DS._강제자_뒤(본문))]
    assert 집은것 == ["tools/지금것.py"], 집은것


def test_강제자_없음도_블록이다():
    # ★ 「강제자 없음 — 설계 판단이다」 도 절의 끝 블록이다. 파일은 안 들지만 창은 거기 선다
    본문 = "## §1. 제목\n\n**2026-01-01**\n\n본문 `tools/산문.py`\n\n강제자 없음 — 설계 판단이다\n"
    앵 = DS._강제자_뒤(본문)
    assert 앵.startswith("강제자 없음 — ")
    assert DS.지목.findall(앵) == []
