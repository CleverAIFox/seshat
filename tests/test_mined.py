"""누수 장부 — **잰 셋에서 캔 사전**을 세는 쪽이 살아 있나(DECISIONS §168 · PLAN #37).

★ 이 시험은 **수를 박지 않는다.** 16 을 박으면 #37 을 갚는 날 시험이 빨개지고, 그러면
  「갚으면 빨개지는 시험」 이 또 하나 는다(§164 의 교훈). 박는 것은 **세는 길이 산다는 것**뿐이다.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from seshat import evaluate, ontology  # noqa: E402


def test_장부는_사전_밖에_산다():
    """★ 노드에 적으면 `onto_sha256` 이 바뀌어 **뜻이 안 바뀐 편집이 옛 판을 전부 막는다**(§168)."""
    assert ontology.MINED.parent == ontology.DEFAULT.parent
    assert ontology.MINED != ontology.DEFAULT
    for n in ontology.load():
        assert "mined_from" not in n, f"{n['id']} 가 사전 안에 출처를 들었다 — 장부로 옮긴다"


def test_사전에_적으면_거절한다():
    onto = [{"id": "con.x", "kind": "concept", "ko": "가나", "ko_ref": "s3/dev", "src": "author",
             "en": "X", "keep": False, "mined_from": "data/domain/d001.jsonl"}]
    assert any("mined_from" in f for f in ontology.validate(onto))


@pytest.mark.parametrize("셋, 빈가", [("data/domain/d001.jsonl", False),
                                     ("data/domain/없는셋.jsonl", True),
                                     (None, True)])
def test_캔_노드가_셋을_가른다(셋, 빈가):
    got = ontology.캔_노드(셋)
    assert (not got) is 빈가


def test_장부의_id_가_사전에_있다():
    """★ **장부가 사전보다 먼저 썩는다** — 썩으면 `onto_leak` 이 실제보다 작게 나온다(§168)."""
    있는 = {n["id"] for n in ontology.load()}
    for d in ontology.누수_장부():
        assert d["id"] in 있는, f"장부의 {d['id']} 가 사전에 없다"
        assert ontology.MINED_FROM.fullmatch(d["mined_from"])


def _잰셋() -> str:
    """장부가 든 셋의 자리. **파일이 거기 있다고 치지 않는다** — `data/domain/` 은 저장소에 없다."""
    장부 = ontology.누수_장부()
    assert 장부, "누수 장부가 비었다"
    return sorted(d["mined_from"] for d in 장부)[0]


def test_판이_누수를_싣는다(tmp_path):
    """`conditions()` 가 `onto_leak` 을 낸다 — 용어 수 옆에 늘 붙어 다녀야 한다.

    ★ **셋 파일에 안 기댄다.** `data/domain/` 은 저장소에 없다(카탈로그가 받는다) — 2026-09-28
      이 시험이 `d001` 을 열려다 CI 에서만 깨졌다. **이 기계에 있는 것을 저장소에 있는 것으로
      읽는 것**이 §170 과 같은 병이다. 셋의 **이름**만 누수를 가르므로 빈 파일이면 된다.
    """
    셋 = tmp_path / "d001.jsonl"
    셋.write_text("", encoding="utf-8")

    class A:
        backend, hypothesis, url = None, None, None
        set = str(셋)
    got = evaluate.conditions(A(), [{"src": "a"}], {"commit": "0" * 7, "dirty": False})
    assert got["onto_leak"] == 0, "딴 자리의 같은 이름은 그 셋이 아니다"

    잰 = _잰셋()
    assert len(ontology.캔_노드(잰)) > 0, f"{잰} 은 지금 누수가 있는 셋이다 — 0 이 되면 #37 이 갚아진다"
    assert len(ontology.캔_노드("data/domain/안캔셋.jsonl")) == 0


def test_mine_terms_가_점수를_내는_셋을_거절한다(tmp_path):
    """★ **이 도구가 누수를 만들었다**(§168). 같은 죄를 두 번 못 짓게 한다.

    ★ 거절은 **파일을 열기 전**에 난다 — 그래서 셋이 저장소에 없어도 이 시험은 돈다.
    """
    r = subprocess.run([sys.executable, str(ROOT / "tools/mine_terms.py"), _잰셋(), "--top", "1"],
                       capture_output=True, text=True)
    assert r.returncode == 1, "기록판에 오른 셋인데 그냥 돌았다"
    assert "점수를 내는 셋" in r.stderr
    assert "--leak-ok" in r.stderr, "막기만 하고 넘는 길을 안 알려주면 딴 길로 캔다"


def test_알면서_캐면_장부에_적을_줄을_찍어_준다(tmp_path):
    """★ **막는 것보다 적게 만드는 것이 낫다**(§168). 못 캐게 하면 딴 길로 캔다."""
    잰 = _잰셋()
    셋 = tmp_path / pathlib.Path(잰).name
    셋.parent.mkdir(parents=True, exist_ok=True)
    셋.write_text(json.dumps({"src": "Use the Amazon S3 console to create a bucket."},
                            ensure_ascii=False) + "\n", encoding="utf-8")
    # 장부가 든 자리로 **끝나는** 자리여야 걸린다 — 도구가 끝자락으로 맞춘다
    깊 = tmp_path / 잰
    깊.parent.mkdir(parents=True, exist_ok=True)
    깊.write_bytes(셋.read_bytes())
    ok = subprocess.run([sys.executable, str(ROOT / "tools/mine_terms.py"), str(깊),
                         "--top", "1", "--leak-ok"], capture_output=True, text=True)
    assert ok.returncode == 0, ok.stderr
    assert "mined_from" in ok.stdout and "mined.jsonl" in ok.stdout
