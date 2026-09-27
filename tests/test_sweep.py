"""seshat 위생 — 근거가 있을 때만 지운다(DECISIONS §23)."""
import importlib.util
import os
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


def test_붙음_겹침_안_붙음_판정_못함(tmp_path):
    p = tmp_path / "x.patch"
    p.write_text(PATCH, encoding="utf-8")
    assert ps.state(p, _repo(tmp_path, "seshat-099: 한글 제목", "seshat-100: plain")) == "붙음"
    assert ps.state(p, _repo(tmp_path / "b", "seshat-099: 한글 제목")) == "겹침"   # 일부만 붙었다
    assert ps.state(p, _repo(tmp_path / "c", "seshat-098: 딴것")) == "안 붙음"
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


def test_이미_붙은_패치는_기준_나무를_묻지_않는다(tmp_path):
    """합본으로 붙인 뒤 INBOX 에 남은 옛 낱개 패치가 기준 나무 불일치로 죽었다(DECISIONS §77).

    붙일 것이 없는 패치의 기준 자리는 물을 까닭이 없다. 죽으면 `&& git push` 가 통째로 날아간다.
    """
    repo = _repo(tmp_path, "seshat-099: 한글 제목", "seshat-100: plain")
    p = tmp_path / "seshat-099-x.patch"
    p.write_text(PATCH.replace("From 0 Mon", "Seshat-Base-Tree: " + "0" * 40 + "\nFrom 0 Mon", 1),
                 encoding="utf-8")
    # 도구는 저장소 루트에서 도니, 사본을 만들어 거기서 부른다
    (pathlib.Path(repo) / "tools").mkdir(parents=True, exist_ok=True)
    for name in ("apply_patch.sh", "patch_subjects.py"):
        (pathlib.Path(repo) / "tools" / name).write_text((ROOT / "tools" / name).read_text(encoding="utf-8"),
                                                         encoding="utf-8")
    (pathlib.Path(repo) / "tools/lib").mkdir(parents=True, exist_ok=True)
    (pathlib.Path(repo) / "tools/lib/env.sh").write_text((ROOT / "tools/lib/env.sh").read_text(encoding="utf-8"),
                                                         encoding="utf-8")
    (pathlib.Path(repo) / ".env").write_text(f"SESHAT_INBOX={tmp_path}\n", encoding="utf-8")
    r = subprocess.run(["bash", "tools/apply_patch.sh", str(p)], capture_output=True, text=True, cwd=repo)
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert "이미 붙어 있다" in r.stdout


def _사본(repo):
    """도구는 저장소 루트에서 돈다 — 사본을 만들어 거기서 부른다."""
    r = pathlib.Path(repo)
    (r / "tools/lib").mkdir(parents=True, exist_ok=True)
    for name in ("apply_patch.sh", "patch_subjects.py", "lib/env.sh"):
        (r / "tools" / name).write_text((ROOT / "tools" / name).read_text(encoding="utf-8"), encoding="utf-8")
    return r


def test_겹친_패치는_뒤에_밀린_것을_안_막는다(tmp_path):
    """합본을 보낸 뒤 그 일부가 먼저 붙으면 합본은 붙지도 지워지지도 않고 줄을 막았다(DECISIONS §124).

    2026-09-27 에 `seshat-105-106` 이 그랬다 — 105 가 먼저 붙어 기준 나무가 어긋났고, `apply_patch` 는
    번호 순서로 그것부터 집어 죽었다. 뒤에 있던 `seshat-106` 이 영영 못 붙었다.
    """
    repo = _사본(_repo(tmp_path, "seshat-099: 한글 제목"))
    inbox = tmp_path / "inbox"; inbox.mkdir()
    (inbox / "seshat-099-100-합본.patch").write_text(
        PATCH.replace("From 0 Mon", "Seshat-Base-Tree: " + "0" * 40 + "\nFrom 0 Mon", 1), encoding="utf-8")
    (repo / ".env").write_text(f"SESHAT_INBOX={inbox}\n", encoding="utf-8")
    # conftest 가 이미 SESHAT_INBOX 를 쥐고 있고 `load_env` 는 있는 값을 안 덮는다
    r = subprocess.run(["bash", "tools/apply_patch.sh"], capture_output=True, text=True, cwd=repo,
                       env={**os.environ, "SESHAT_INBOX": str(inbox)})
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert "건너뛴다(겹침)" in r.stdout
    assert "기준 나무" not in r.stderr          # 지나갈 자리를 기준 자리로 안 묻는다


def test_겹친_패치를_이름으로_불러도_안_죽는다(tmp_path):
    repo = _사본(_repo(tmp_path, "seshat-099: 한글 제목"))
    p = tmp_path / "seshat-099-100-합본.patch"
    p.write_text(PATCH, encoding="utf-8")
    (repo / ".env").write_text(f"SESHAT_INBOX={tmp_path}\n", encoding="utf-8")
    r = subprocess.run(["bash", "tools/apply_patch.sh", str(p)], capture_output=True, text=True, cwd=repo)
    assert r.returncode == 0, (r.stdout, r.stderr)
    assert "남은 것 : seshat-100: plain" in r.stdout
