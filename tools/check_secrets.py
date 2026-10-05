"""비밀값이 추적되는 파일에 들어갔나(DECISIONS §304).

  python3 tools/check_secrets.py            검사한다. 위반이면 1, 도구 고장이면 2
  python3 tools/check_secrets.py --history  **역사 전체**를 본다 (느리다)
  python3 tools/check_secrets.py --list     무엇을 보는지 찍는다
  python3 tools/check_secrets.py --selftest 판별식이 살아 있나

★ **이 저장소는 개인 비공개라 깃허브의 비밀값 스캔이 안 붙는다**(`SECURITY.md`) — 조직 유료
  요금제에서만 열린다. 그리고 **저장소 안에도 없었다** : `.gitignore` 의 `.env` 한 줄이 전부다.
★ **`gitleaks` 를 안 쓴다.** 이 기계에 없고, 깔아야 도는 자는 **안 깔린 기계에서 조용히
  건너뛴다**(§59). 꼴 여덟을 제 손으로 들면 **의존이 0** 이고 CI 에서도 같이 돈다.
★ **§133 과 어긋나 보이는 자리다.** 「없는 병에 관문을 세우지 않는다」 — 실측으로 **296 커밋
  역사 전체에서 0건**이고 지금 나무에서도 0건이다. 그런데도 세운다 : §133 이 재는 것은
  **소음과 값의 저울**인데, 비밀값은 **한 번 새면 못 되돌린다.** 꼴이 좁아 소음이 0 이고
  (실측), 값은 비대칭이다. **이 저울에서만 예외다 — 그 까닭을 여기 적는다.**
★ **꼴은 좁게 든다.** 엔트로피로 재면 해시 · base64 자료 · 시험 고정자리가 전부 운다.
  **접두사가 분명한 것**(`AKIA` · `ghp_` · `sk-` · `hf_` · `xox`)과 **대입 꼴** 둘만 본다.
★ **밖 — 추적 안 된 파일은 안 본다.** 기계마다 있고 없다(§212) — `.env` 가 그렇다.
★ **밖 — 엔트로피는 안 본다.** 접두사가 분명한 꼴과 대입 꼴만 본다. 무작위로 보이는 긴
  글자(해시 · base64 자료 · 모델 가중치 이름)는 **안 본다** — 거기 숨긴 키는 이 자가 못 잡는다.
★ **밖 — 바이너리는 안 본다**(`글자아님`). 글로 못 읽는 것은 **못 잼**이고 0 이 아니다.
★ **역사는 손으로 본다.** 커밋마다 돌면 사슬이 느려지고, 역사는 **안 바뀐다** — 한 번 재서
  적어 두면 다음 판은 **새 커밋만** 보면 된다. 그 수가 `_역사0` 이다.

  0  이상 없음
  1  위반
  2  도구 고장
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

#: **본 적 있는 역사의 길이.** 여기까지는 0건이라고 재 뒀다(DECISIONS §304).
_역사0 = 297

#: 꼴 — 이름은 화면에 그대로 나간다. **값은 절대 안 찍는다**(찍으면 로그가 유출이 된다).
꼴: dict[str, str] = {
    "AWS 접근키": r"\bAKIA[0-9A-Z]{16}\b",
    "GitHub 토큰": r"\bgh[pousr]_[A-Za-z0-9]{36,}\b",
    "OpenAI 키": r"\bsk-[A-Za-z0-9]{32,}\b",
    "허깅페이스 토큰": r"\bhf_[A-Za-z0-9]{30,}\b",
    "슬랙 토큰": r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b",
    "개인키": r"-----BEGIN (?:RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----",
    "AWS 비밀키 대입": r"(?i)aws.{0,20}['\"][0-9a-zA-Z/+]{40}['\"]",
    "비밀 대입": r"(?i)(?:password|secret|token|api_key|apikey)\s*[:=]\s*['\"][^'\"\s]{12,}['\"]",
}
_짠것 = {이름: re.compile(정규) for 이름, 정규 in 꼴.items()}

#: **선언한 예외.** 늘면 막는다 — 지금은 비어 있다(실측 0건).
장부: frozenset[str] = frozenset()

#: 글로 안 읽는 것. 바이너리를 정규식에 먹이면 **못 읽은 것을 0 으로 센다**(§296 의 `글자아님`)
글자아님 = {".png", ".jpg", ".jpeg", ".gif", ".zip", ".docx", ".xlsx", ".pptx", ".pdf", ".ico",
            ".parquet", ".bin", ".safetensors", ".pt", ".onnx"}


def 추적된파일(root: Path | None = None) -> list[str]:
    """git 이 아는 파일. **추적 안 된 것은 안 본다** — 기계마다 있고 없다(§212)."""
    root = root or ROOT
    r = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"git ls-files 가 실패했다 — {r.stderr.strip()[:200]}")
    return [x for x in r.stdout.split("\0") if x]


def 찾는다(글: str, 어디: str = "") -> list[str]:
    """비밀값 꼴이 든 자리. **값은 안 찍는다** — 줄 번호와 꼴 이름만."""
    머리 = f"{어디}:" if 어디 else ""
    난것 = []
    for n, 줄 in enumerate(글.split("\n"), 1):
        for 이름, 짠것 in _짠것.items():
            if 짠것.search(줄):
                열쇠 = f"{어디}:{n}:{이름}"
                if 열쇠 in 장부:
                    continue
                난것.append(f"{머리}{n} **{이름}** 꼴이 보인다 — 값은 안 찍는다. "
                            f"그 줄을 지우고 **키를 폐기한다**")
    return 난것


def 나무를_본다(root: Path | None = None) -> list[str]:
    root = root or ROOT
    난것 = []
    for rel in 추적된파일(root):
        p = root / rel
        if not p.is_file() or p.suffix.lower() in 글자아님:
            continue
        try:
            글 = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError) as e:
            # ★ **삼키지 않는다**(DECISIONS §255 · §296). 못 읽은 것을 0 으로 세면 **초록이
            #   「깨끗하다」 인지 「안 봤다」 인지 못 가른다.** 선언 밖에서 못 읽은 것만 자국을 남긴다.
            print(f"    ※ {rel} 을 글로 못 읽었다({e.__class__.__name__}) — **이 파일은 안 봤다.** "
                  f"바이너리면 `글자아님` 에 적는다", file=sys.stderr)
            continue
        난것 += 찾는다(글, rel)
    return 난것


def 역사를_본다(root: Path | None = None) -> tuple[list[str], int]:
    """(난 것, 지금 커밋 수). **느리다** — 사슬 밖이고 손으로 돌린다."""
    root = root or ROOT
    r = subprocess.run(["git", "-C", str(root), "log", "-p", "--all", "--no-color"],
                       capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        raise SystemExit(f"git log 가 실패했다 — {r.stderr.strip()[:200]}")
    c = subprocess.run(["git", "-C", str(root), "rev-list", "--all", "--count"],
                       capture_output=True, text=True)
    return 찾는다(r.stdout, "역사"), int(c.stdout.strip() or 0)


def _canary() -> None:
    """**0건이 목표인 검사는 0건을 성공으로만 읽으면 안 된다**(MASTER §0-8)."""
    합성 = {
        "AWS 접근키": "aws_key = AKIA" + "A" * 16,
        "GitHub 토큰": "ghp_" + "a" * 36,
        "OpenAI 키": "sk-" + "b" * 32,
        "허깅페이스 토큰": "hf_" + "c" * 30,
        "슬랙 토큰": "xox" + "b-1234567890-abc",
        "개인키": "-----BEGIN " + "RSA PRIVATE KEY-----",
        "비밀 대입": 'password = "' + "d" * 12 + '"',
    }
    # ★ **합성 값을 글자 그대로 적지 않는다**(DECISIONS §304). 적으면 **이 파일이 제 검사에
    #   걸린다** — 그리고 면제를 만들면 **진짜가 거기 숨을 수 있다.** 런타임에 잇는다.
    for 이름, 줄 in 합성.items():
        if not any(이름 in x for x in 찾는다(줄)):
            print(f"    ★ 카나리아가 죽었다 — {이름} 을 못 찾는다"); sys.exit(2)
    # ★ **음성도 묻는다.** 전부 우는 검사는 쓸모가 없다 — 해시 · 경로 · 짧은 값은 안 걸려야 한다
    for 줄 in ("sha = 3326d3e6b9ef49204d4968e7d2e38ae91c367d84",
               'path = "tools/check_secrets.py"', 'token = "짧다"', "AKIA 는 접두사다"):
        if 찾는다(줄):
            print(f"    ★ 카나리아가 죽었다 — 멀쩡한 줄을 잡는다 : {줄[:40]}"); sys.exit(2)
    if not 꼴 or len(꼴) != len(_짠것):
        print("    ★ 카나리아가 죽었다 — 꼴을 못 짰다"); sys.exit(2)


def main(argv: list[str] | None = None) -> int:
    a = argv if argv is not None else sys.argv[1:]
    _canary()
    if "--selftest" in a:
        print(f"  프로브 살아 있다 — 꼴 {len(꼴)} 을 합성으로 묻고, 멀쩡한 줄 넷이 안 걸린다")
        return 0
    if "--list" in a:
        print(f"  꼴 {len(꼴)} · 장부 {len(장부)} · 재 둔 역사 {_역사0} 커밋")
        for 이름 in 꼴:
            print(f"    {이름}")
        return 0
    난것 = 나무를_본다()
    꼬리 = ""
    if "--history" in a:
        옛, 지금 = 역사를_본다()
        난것 += 옛
        꼬리 = f" · 역사 {지금} 커밋"
    print(f"  추적된 파일 {len(추적된파일())} · 꼴 {len(꼴)} · 장부 {len(장부)}{꼬리}")
    for x in 난것:
        print(f"    {x}", file=sys.stderr)
    return 1 if 난것 else 0


if __name__ == "__main__":
    # ★ 위반(1)과 도구 고장(2)을 다른 코드로 끝낸다(DECISIONS §21 · §232)
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        print("    ✗ 도구가 깨졌다 — 위 역추적이 자리를 든다\n"
              "      고치고 다시 돌린다 : python3 tools/check_secrets.py --selftest\n"
              "      급하면 verify 의 `secrets` 줄만 빼고 민다 — 다만 **빼고 민 것은\n"
              "      안 본 것이다**(DECISIONS §59)", file=sys.stderr)
        sys.exit(2)
