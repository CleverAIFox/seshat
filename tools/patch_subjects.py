"""format-patch 파일의 커밋 제목과, 그 제목이 이력에 다 있는가(DECISIONS §21 · §23).

  python3 tools/patch_subjects.py x.patch     제목을 한 줄씩

★ **판정 규칙은 여기 하나다.** `apply_patch.sh`(이미 붙었으면 안 한다)와 `sweep.py`(붙었으면 지운다)가 같은
  규칙을 쓴다. 두 곳에 두면 한쪽은 붙었다 하고 한쪽은 아니라 한다.
★ format-patch 는 한글 제목을 RFC 2047(`=?UTF-8?q?…?=`)로 싼다 — 풀어서 이력과 맞춘다.
"""
from __future__ import annotations

import mailbox
import re
import subprocess
import sys
import tempfile
from email.header import decode_header, make_header
from pathlib import Path


def subjects(patch: Path) -> list[str]:
    text = patch.read_bytes().replace(b"\r\n", b"\n")
    with tempfile.NamedTemporaryFile(prefix="seshat-subjects-", suffix=".mbox", delete=False) as f:
        f.write(text)
        tmp = Path(f.name)
    try:
        out = []
        for m in mailbox.mbox(tmp):
            s = str(make_header(decode_header(m.get("Subject", "")))).replace("\n", "")
            out.append(re.sub(r"\s+", " ", re.sub(r"^\[PATCH[^]]*\]\s*", "", s)).strip())
        return [s for s in out if s]
    finally:
        tmp.unlink(missing_ok=True)


def history(repo: Path, n: int = 500) -> set[str]:
    r = subprocess.run(["git", "-C", str(repo), "log", "--format=%s", "-n", str(n)], capture_output=True, text=True)
    return set(r.stdout.splitlines()) if r.returncode == 0 else set()


NUMBER = re.compile(r"^(seshat-\d{3})\b")


def state(patch: Path, repo: Path) -> str:
    """붙음 · 안 붙음 · 판정 못함 — 셋으로 가른다(thoth DECISIONS §61).

    커밋 패치(format-patch)는 제목으로 가른다. seshat-018 전의 패치는 `git diff` 라 제목이 없다 — 그때는
    ① 역적용이 붙으면 붙은 것이다 ② 파일 이름의 번호(`seshat-017`)로 시작하는 커밋이 이력에 있으면 붙은 것이다.
    역적용 실패는 안 붙음의 증거가 아니다(붙은 뒤 같은 파일이 또 바뀐다). 둘 다 아니면 판정 못함이다.
    """
    subs = subjects(patch)
    if subs:
        return "붙음" if set(subs) <= history(repo) else "안 붙음"
    body = patch.read_bytes().replace(b"\r\n", b"\n")
    r = subprocess.run(["git", "-C", str(repo), "apply", "--check", "-R", "-"], input=body, capture_output=True)
    if r.returncode == 0 and body.strip():
        return "붙음"
    m = NUMBER.match(patch.name)
    if m and any(h.startswith(m.group(1)) for h in history(repo)):
        return "붙음"
    return "판정 못함"


if __name__ == "__main__":
    for s in subjects(Path(sys.argv[1])):
        print(s)
