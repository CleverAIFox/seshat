"""seshat 위생 — 근거가 있을 때만 지운다(DECISIONS §23)."""
import importlib.util
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _mod(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"tools/{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


ps = _mod("patch_subjects")
lake = _mod("lake")
sweep = _mod("sweep")

PATCH = """From 0 Mon Sep 17 00:00:00 2001
From: t <a@b>
Subject: [PATCH 1/2] =?UTF-8?q?seshat-099:=20=ED=95=9C=EA=B8=80?=
 =?UTF-8?q?=20=EC=A0=9C=EB=AA=A9?=

---
From 0 Mon Sep 17 00:00:00 2001
From: t <a@b>
Subject: [PATCH 2/2] seshat-100: plain

---
"""


def _repo(tmp_path, *subjects):
    r = tmp_path / "repo"
    r.mkdir(parents=True)
    g = ["git", "-C", str(r), "-c", "user.email=a@b", "-c", "user.name=t"]
    subprocess.run([*g[:3], "init", "-q"], check=True)
    for s in subjects:
        subprocess.run([*g, "commit", "-q", "--allow-empty", "-m", s], check=True)
    return r


def test_한글_제목을_풀고_접힌_줄을_잇는다(tmp_path):
    p = tmp_path / "x.patch"
    p.write_text(PATCH.replace("\n", "\r\n"), encoding="utf-8")        # 브라우저가 CRLF 로 바꿔도 같다
    assert ps.subjects(p) == ["seshat-099: 한글 제목", "seshat-100: plain"]


def test_붙음_안_붙음_판정_못함(tmp_path):
    p = tmp_path / "x.patch"
    p.write_text(PATCH, encoding="utf-8")
    assert ps.state(p, _repo(tmp_path, "seshat-099: 한글 제목", "seshat-100: plain")) == "붙음"
    assert ps.state(p, _repo(tmp_path / "b", "seshat-099: 한글 제목")) == "안 붙음"     # 하나라도 없으면 안 붙음
    q = tmp_path / "raw.diff"
    q.write_text("diff --git a/x b/x\n", encoding="utf-8")
    assert ps.state(q, tmp_path) == "판정 못함"


def test_작업대_결과는_레이크에_같은_해시일_때만_지운다(tmp_path):
    d = tmp_path / "lake"
    lake.init(d)
    bench = tmp_path / "runs"
    bench.mkdir()
    (bench / "H-001-base-1.jsonl").write_text("a\n")
    (bench / "H-001-ph-1.jsonl").write_text("b\n")
    lake.put(d, "runs", [bench / "H-001-base-1.jsonl"])
    (bench / "H-001-ph-1.jsonl").write_text("b\n")
    kill, keep, u = sweep.scan_bench(lake.manifest(d), [bench])
    assert [p.name for p, _ in kill] == ["H-001-base-1.jsonl"]
    assert [p.name for p, _ in keep] == ["H-001-ph-1.jsonl"]
    (bench / "H-001-base-1.jsonl").write_text("바뀜\n")                 # 이름이 같아도 내용이 다르면 남긴다
    kill, _, _ = sweep.scan_bench(lake.manifest(d), [bench])
    assert kill == []


def test_레이크가_안_붙었으면_못_잼이다():
    assert sweep.scan_bench(None, [])[2] != []


def test_제목_없는_옛_패치는_번호로_가른다(tmp_path):
    r = _repo(tmp_path, "seshat-017")
    old = tmp_path / "seshat-017-h016-adopt.patch"
    old.write_text("diff --git a/x b/x\n", encoding="utf-8")
    assert ps.state(old, r) == "붙음"
    new = tmp_path / "seshat-120-x.patch"
    new.write_text("diff --git a/x b/x\n", encoding="utf-8")
    assert ps.state(new, r) == "판정 못함"


def test_빈_디렉터리만_지운다(tmp_path):
    d = tmp_path / "h001"
    (d / "runs-1").mkdir(parents=True)
    (d / "runs-2").mkdir()
    (d / "runs-2/runner.log").write_text("x")          # 근거 없는 파일이 남은 자리는 그대로다
    gone = sweep.prune_empty(d)
    assert gone == [d / "runs-1"]
    assert (d / "runs-2/runner.log").exists()
    (d / "runs-2/runner.log").unlink()
    assert sweep.prune_empty(d) == [d / "runs-2", d]


def test_상태를_명령줄로도_묻는다(tmp_path):
    """`apply_patch.sh` 가 밀린 패치를 고를 때 이 입구를 쓴다(DECISIONS §30)."""
    import subprocess
    p = tmp_path / "seshat-099-x.patch"
    p.write_text(PATCH, encoding="utf-8")
    r = subprocess.run(["python3", str(ROOT / "tools/patch_subjects.py"), "--state", str(p)],
                       capture_output=True, text=True, cwd=_repo(tmp_path, "seshat-099: 한글 제목", "seshat-100: plain"))
    assert r.stdout.strip() == "붙음"
