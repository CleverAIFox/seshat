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
    assert any("대장에 없는" in f for f in cml.check(root, {}))


def test_서빙이_비상업을_부르면_걸린다(tmp_path):
    root = _tree(tmp_path, 'm = Translator("org/nc")\n', "seshat/backends.py")
    led = {"org/nc": ("CC-BY-NC-4.0", "no", "모델 카드 2026-09-22")}
    assert any("서빙 백엔드" in f for f in cml.check(root, led))
    # 서빙 밖(비교 실험)에서는 센다 — 막지 않는다
    root2 = _tree(tmp_path / "b", 'm = Translator("org/nc")\n', "seshat/bench.py")
    assert cml.check(root2, led) == []


def test_어휘_밖의_상업_가부가_걸린다(tmp_path):
    root = _tree(tmp_path, "")
    assert any("어휘 밖" in f for f in cml.check(root, {"a/b": ("MIT", "maybe", "x")}))


def test_쓸_수_없는_가중치는_비교에서도_걸린다(tmp_path):
    # ★ 비상업(센다)과 다르다. 사용 허락 지역 밖이면 서빙 밖에서도 실패다(DECISIONS §9).
    root = _tree(tmp_path, 'm = AutoModel.from_pretrained("tencent/HY-MT1.5-1.8B")\n', "seshat/bench.py")
    led = {"tencent/HY-MT1.5-1.8B": ("Tencent HY Community", "no", "모델 카드 2026-09-22")}
    fails = cml.check(root, led)
    assert any("쓸 수 없는 가중치" in f and "bench.py" in f for f in fails)
    assert any(f.startswith("대장에 쓸 수 없는") for f in fails)


def test_제외는_접두사로_대소문자를_가리지_않는다():
    from seshat.licenses import excluded
    assert excluded("Tencent/Hunyuan-MT-7B")
    assert excluded("tencent/hy-mt1.5-7b")
    assert excluded("google/translategemma-4b-it") is None
