# seshat

[thoth](https://github.com/CleverAIFox/thoth) 에 끼울 **영한 번역 모델**을 만드는 저장소. **비공개다.**

thoth 는 영어 자격증 문제 화면에 한글 번역을 겹쳐 보여주는 크롬 확장과 워커다.
지금은 Bedrock Nova Lite 가 번역하고, 이 저장소의 모델이 그 자리를 넘겨받는다.
이름은 토트(문자의 신)의 짝인 **세샤트** — 기록과 문자, 도서관의 여신에서 왔다.

## 방향

**목표는 영→한 범용에서 AWS Translate 를 넘는 것이다**(DECISIONS §11). 1년 · 1인. thoth 의 도메인
(AWS 자격증 문항 · 합쇼체)은 그 위의 특화다.

**이 저장소는 연구다**(DECISIONS §12). 화면은 thoth 가 맡고 여기는 번역의 뇌 — 모델 · 데이터 · 평가 ·
서빙 백엔드 — 만 든다. 직관 → 가설 → 가장 싼 검증 → 채택 · 기각. 측정은 가설이 부를 때만 한다.

| 쌓는 곳 | 무엇 |
|---|---|
| `docs/hypotheses.md` | 가설 대장 — 실험의 문. 검증 방법과 비용 상한 없이는 실험에 못 들어간다 |
| `docs/papers.md` | 논문 대장 — 남이 이미 한 학습을 파싱한다 |
| `docs/MASTER.md` §7 · §8 | 연구 트랙 일곱 · 인프라 |

사전학습 모델과 공개 연구를 최대한 쓰고, 학습은 장비가 허락하는 만큼만 한다 — 지금은 학습 없이, 연말 전에는
원격 GPU, 새 장비부터 강화학습 · 구조 실험.

## 기계

| | |
|---|---|
| 로컬 GPU | GTX 1660 Ti · VRAM 6GB · Turing — fp16 은 되고 bf16 · FlashAttention 2 는 안 된다 |
| 로컬에서 하는 것 | 평가 · 추론 확인 · 1B 급 QLoRA · 모델 병합(CPU) |
| 학습 | Kaggle · Colab 의 무료 T4, 부족하면 EC2 스팟(AWS 크레딧). 연말에 학습용 데스크탑(PLAN #21) |

## thoth 와의 계약

thoth 워커가 `ENGINE=http` 로 이 저장소의 서버를 부른다(thoth `docs/MASTER.md` §7-4).

```
POST /translate  {"texts": [...], "source": "en", "target": "ko", "terms": {...}}
              →  {"translations": [...]}       같은 길이 · 같은 순서
GET  /health  →  {"model": "<이름>"}
```

`tests/thoth_conformance.py` 는 thoth 의 검사 도구 사본이다. 서버가 이것을 통과하면
thoth 에 그대로 끼워진다.

## 실행

```bash
cp .env.example .env                              # SESHAT_DATA(SSD 레이크) · SESHAT_INBOX(다운로드 폴더)
uv sync
bash tools/verify.sh                              # 점검 전부 — CI 도 이것만 부른다
bash tools/apply_patch.sh                         # INBOX 의 최신 seshat-*.patch 를 커밋째 붙인다
python3 tools/lake.py check                       # SSD 레이크 대장 · 가설 근거
python3 tools/check_catalog.py --list             # 데이터 카탈로그 — 출처 · 라이선스 · 쓰임
python3 tools/sweep.py [--fix]                    # WSL 위생 — seshat 이 남긴 흔적만
uv run pytest                                     # 계약 · 평가 · 평가셋 불변식
uv run python -m seshat.serve                     # echo 백엔드 · 127.0.0.1:8100
uv run --group eval python -m seshat.evaluate \
    --url http://127.0.0.1:8100 --set data/eval/seed.jsonl
python3 tools/check_docs.py                       # 문서 ↔ 문서 (규약은 docs/MASTER.md §0)
python3 tools/doc_fsck.py                         # 문서 ↔ 실물
python3 tools/check_model_licenses.py --list      # 가중치 라이선스 대장
python3 tools/check_hypotheses.py                 # 가설 대장 — 실험의 문
python3 tools/make_probes.py --name h001          # 문형 탐침 200줄 → data/probes/
python3 tools/compare_runs.py <A> <B> --set <셋>   # 두 결과를 줄 단위로 대조
python3 tools/rescore.py <결과> --set <셋> --hypothesis H-NNN   # GPU 없이 다시 채점
python3 tools/show_misses.py <결과> [--what keep|term|hangul|style]  # 숫자 뒤의 줄을 본다
python3 tools/term_diff.py <A> <B>                # 두 결과를 개념 단위로 — 누가 어느 용어에서 이겼나
```

thoth 배포본(Nova Lite)을 기준선으로 잴 때는 워커를 그대로 부른다. 평가 문장은
학습 쌍에 섞이지 않게 `.local` 출처로 나간다.

```bash
uv run --group eval python -m seshat.evaluate --url https://<워커> --thoth \
    --thoth-token <토큰> --set data/eval/seed.jsonl --name nova-lite
```

## 데이터

**학습 데이터 · 모델 가중치 · 실행 결과는 저장소에 들어오지 않는다.** 비공개 저장소여도 같다. 쌍 로그의 원문은
사이트의 저작물이다. `data/private/` · `runs/` · `models/` 를 git 이 무시한다.
저장소에 있는 평가셋은 이 저장소가 직접 쓴 문장뿐이다(`data/eval/README.md`).

## 문서

| | |
|---|---|
| [`docs/PLAN.md`](docs/PLAN.md) | 남은 일 · 미결정 · 범위 밖 |
| [`docs/MASTER.md`](docs/MASTER.md) | 지금 무엇이 있는가 |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | 왜 그렇게 됐나 |

**새 세션은 `PLAN` §0 부터 읽는다.**
