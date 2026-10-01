"""증류용 원문을 뽑는 자 — 꼴과 조건이 옳은가(DECISIONS §276 · PLAN #18).

★ 이 파일은 **seshat 것**이다 — thoth 사본이 아니다(DECISIONS §5).
★ **망을 안 탄다.** 받는 일(`clone`)은 안 부르고, **가짜 문서 나무**로 고르는 규칙만 본다.
"""
from __future__ import annotations

import importlib.util
import pathlib

import pytest

ROOT = next(p for p in pathlib.Path(__file__).resolve().parents if (p / "tools/fetch_k8s.py").exists())
_spec = importlib.util.spec_from_file_location("fetch_k8s", ROOT / "tools/fetch_k8s.py")
K = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(K)


def _나무(tmp_path: pathlib.Path, 자리별: dict[str, int]) -> pathlib.Path:
    본문 = tmp_path / K.문서자리
    for 자리, n in 자리별.items():
        d = 본문 / 자리
        d.mkdir(parents=True, exist_ok=True)
        for i in range(n):
            (d / f"{i}.md").write_text(
                f"# 제목 {i}\n\nThe {자리} controller watches the cluster state number {i}. "
                f"It reconciles the desired state with `kubectl apply` and reports status.\n",
                encoding="utf-8")
    return tmp_path


def test_자리로_모은다(tmp_path):
    """★ **자리마다 상한을 두려면 자리를 알아야 한다** — `reference` 가 셋을 먹는 것을 막는다."""
    got = K.harvest(_나무(tmp_path, {"concepts": 2, "reference": 3}))
    assert set(got) == {"concepts", "reference"}
    assert all(len(v) >= 2 for v in got.values()), got


def test_문서_이름을_싣는다(tmp_path):
    """★ **어느 문서에서 왔는지 없으면 오염을 나중에 못 본다**(§273 의 그 규율)."""
    got = K.harvest(_나무(tmp_path, {"tasks": 1}))
    assert all(ln.doc.startswith("tasks/") for ln in got["tasks"]), got["tasks"][:2]


def test_문서_자리가_없으면_길을_든다(tmp_path):
    """★ **막는 자리에는 넘는 길이 있다**(DECISIONS §210)."""
    with pytest.raises(SystemExit) as e:
        K.harvest(tmp_path)
    assert "sparse-checkout" in str(e.value)


def test_줄이_도메인셋과_같은_꼴이다(tmp_path):
    """★ **같은 꼴이라 `evaluate` · `backends` · `gemba` 가 그대로 읽는다** — 새 길을 안 낸다."""
    from seshat import ontology
    got = K.harvest(_나무(tmp_path, {"concepts": 2}))
    줄 = K.rows(ontology.load(), got["concepts"][:3], "k999")
    assert 줄 and set(줄[0]) == {"id", "src", "keep", "lit", "ui", "guide", "doc"}
    assert 줄[0]["id"].startswith("k999-")
    # ★ 표시는 **(글자, 자리)** 이고 `src[자리:]` 가 그 글자여야 한다 — `evaluate.marked` 의 불변식
    for r in 줄:
        for t, at in r["lit"] + r["ui"]:
            assert r["src"][at:at + len(t)] == t, (t, at, r["src"])


def test_라이선스가_동일조건이_아니다():
    """★ **이 자리를 고른 까닭 전부가 이 한 줄이다**(DECISIONS §276).

    AWS 안내서는 CC BY-**SA** 라 학생을 뿌릴 때 동일조건이 따라붙는다. 쿠버네티스 문서는
    **CC BY 4.0** 이고 표시만 하면 된다. 이 값이 바뀌면 **그 판단이 무효다.**
    """
    assert K.라이선스 == "CC BY 4.0"
    assert "SA" not in K.라이선스
    assert "kubernetes" in K.표시.lower() and "CC BY 4.0" in K.표시


def test_카탈로그가_이_도구를_안다():
    """★ **카탈로그에 없는 자리에는 못 넣는다**(DECISIONS §22) — 그 문이 이 출처를 통과시키나."""
    from seshat import catalog
    e = catalog.match(catalog.load(), "repo", "data/train/k001.jsonl")
    assert e and e["id"] == "k8s-docs", e
    assert catalog.allowed(e["id"], "train"), "학습에 못 쓰는 출처를 증류 원문으로 들었다"
    assert e["license"] == "CC BY 4.0"
