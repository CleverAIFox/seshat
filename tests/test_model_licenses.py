"""라이선스 대장(DECISIONS §6)."""
import importlib.util
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("cml", ROOT / "tools/check_model_licenses.py")
cml = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cml)


def _tree(tmp_path, code, where="seshat/train.py"):
    p = tmp_path / where
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(code, encoding="utf-8")
    (tmp_path / "tools").mkdir(exist_ok=True)
    return tmp_path


def test_카나리아가_산다():
    cml._canary()


def test_실제_저장소가_통과한다():
    assert cml.check(ROOT, cml.LEDGER) == []


def test_대장에_없는_가중치가_걸린다(tmp_path):
    root = _tree(tmp_path, 'm = AutoModel.from_pretrained("org/model")\n')
    assert any("대장에 없는" in f for f in cml.check(root, {}, {}))


def test_서빙이_비상업을_부르면_걸린다(tmp_path):
    root = _tree(tmp_path, 'm = Translator("org/nc")\n', "seshat/backends.py")
    led = {"org/nc": ("CC-BY-NC-4.0", "no", "no", "모델 카드 2026-09-22")}
    assert any("서빙 백엔드" in f for f in cml.check(root, led, {}))
    # 서빙 밖(비교 실험)에서는 센다 — 막지 않는다
    root2 = _tree(tmp_path / "b", 'm = Translator("org/nc")\n', "seshat/bench.py")
    assert cml.check(root2, led, {}) == []


def test_어휘_밖의_상업_가부가_걸린다(tmp_path):
    root = _tree(tmp_path, "")
    assert any("어휘 밖" in f for f in cml.check(root, {"a/b": ("MIT", "maybe", "yes", "x")}, {}))


def test_쓸_수_없는_가중치는_비교에서도_걸린다(tmp_path):
    # ★ 비상업(센다)과 다르다. 사용 허락 지역 밖이면 서빙 밖에서도 실패다(DECISIONS §9).
    root = _tree(tmp_path, 'm = AutoModel.from_pretrained("tencent/HY-MT1.5-1.8B")\n', "seshat/bench.py")
    led = {"tencent/HY-MT1.5-1.8B": ("Tencent HY Community", "no", "no", "모델 카드 2026-09-22")}
    fails = cml.check(root, led, {})
    assert any("쓸 수 없는 가중치" in f and "bench.py" in f for f in fails)
    assert any(f.startswith("대장에 쓸 수 없는") for f in fails)


def test_제외는_접두사로_대소문자를_가리지_않는다():
    from seshat.licenses import excluded
    assert excluded("Tencent/Hunyuan-MT-7B")
    assert excluded("tencent/hy-mt1.5-7b")
    assert excluded("google/translategemma-4b-it") is None


def test_백엔드가_선언한_가중치도_대장과_대조한다(tmp_path):
    # ★ ollama 호출은 from_pretrained 정규식이 못 본다. 선언으로 덮는다(DECISIONS §14).
    root = _tree(tmp_path, "")
    assert any("선언한 가중치" in f for f in cml.check(root, {}, {"b": "org/m"}))
    assert any("쓸 수 없는" in f for f in cml.check(root, {}, {"b": "tencent/HY-MT1.5-7B"}))
    assert cml.check(root, {"org/m": ("Apache-2.0", "yes", "yes", "x")}, {"b": "org/m"}) == []


def test_교사_가부가_대장의_둘째_축이다():
    """서빙에 쓸 수 있는가와 출력을 학생 학습에 쓸 수 있는가는 다르다(DECISIONS §44)."""
    from seshat import licenses as lic
    assert lic.can_teach("google/translategemma-4b-it")
    assert not lic.can_teach("LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct")
    assert not lic.can_teach("모르는/가중치")             # 모르면 못 쓴다
    bad = dict(lic.LEDGER, **{"x/y": ("L", "yes", "maybe", "곳")})
    assert any("교사 가부" in f for f in cml.check(ROOT, bad))


def test_상업_불가_모델은_서빙_후보가_아니다():
    """EXAONE 은 비교 실험에만 부른다 — 등록부에 있으되 서빙 밖이다(DECISIONS §44)."""
    from seshat import backends as b
    name = "exaone-3.5-7.8b+ph+endings"
    assert name in b.REGISTRY and name in b.BASELINE_ONLY
    assert b.WEIGHTS[name] == "LGAI-EXAONE/EXAONE-3.5-7.8B-Instruct"


def test_12b_후보가_대장과_등록부에_함께_있다():
    """체급을 올리는 후보도 상업 · 교사가 열려 있어야 쓴다(DECISIONS §79)."""
    from seshat import backends as b
    from seshat import licenses as lic
    w = b.WEIGHTS["gemma3-12b+ph+retry"]
    assert w == "google/gemma-3-12b-it"
    assert lic.LEDGER[w][1] == "yes" and lic.can_teach(w)
    assert b.WEIGHTS["gemma3-12b"] == b.WEIGHTS["gemma3-4b"].replace("4b", "12b")
