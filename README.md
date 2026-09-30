# seshat

[thoth](https://github.com/CleverAIFox/thoth) 에 끼울 **영한 번역 모델**을 만드는 저장소. **비공개다.**

thoth 는 영어 자격증 문제 화면에 한글 번역을 겹쳐 보여주는 크롬 확장과 워커다.
지금은 Bedrock Nova Lite 가 번역하고, 이 저장소의 모델이 **그 자리를 넘겨받는 것이 목표다.**

★ **2026-09-30 기준 아직 못 넘겼다.** 용어 표기(`term_off`)에서는 배포본을 확실히 넘지만
(+0.0739 · p<0.001), **밖의 판정자 넷이 본 「뜻이 맞다」 에서는 −0.1833 으로 진다**
(DECISIONS §229). 자세한 것은 [`docs/now/related.md`](docs/now/related.md) §3.
이름은 토트(문자의 신)의 짝인 **세샤트** — 기록과 문자, 도서관의 여신에서 왔다.

## 방향

**목표는 영→한 범용에서 AWS Translate 를 넘는 것이다**(DECISIONS §11). 1년 · 1인. thoth 의 도메인
(AWS 자격증 문항 · 합쇼체)은 그 위의 특화다.

**이 저장소는 연구다**(DECISIONS §12). 화면은 thoth 가 맡고 여기는 번역의 뇌 — 모델 · 데이터 · 평가 ·
서빙 백엔드 — 만 든다. 직관 → 가설 → 가장 싼 검증 → 채택 · 기각. 측정은 가설이 부를 때만 한다.

| 쌓는 곳 | 무엇 |
|---|---|
| `docs/next/hypotheses.md` | 가설 대장 — 실험의 문. 검증 방법과 비용 상한 없이는 실험에 못 들어간다 |
| `docs/next/papers.md` | 논문 대장 — 남이 이미 한 학습을 파싱한다 |
| `docs/now/MASTER.md` §7 · §8 | 연구 트랙 일곱 · 인프라 |

사전학습 모델과 공개 연구를 최대한 쓰고, 학습은 장비가 허락하는 만큼만 한다 — 지금은 학습 없이, 연말 전에는
원격 GPU, 새 장비부터 강화학습 · 구조 실험.

## 기계

| | |
|---|---|
| 로컬 GPU | GTX 1660 Ti · VRAM 6GB · Turing — fp16 은 되고 bf16 · FlashAttention 2 는 안 된다 |
| 로컬에서 하는 것 | 평가 · 추론 확인 · **신경망 QE 자**(mT5 1.2B · `qe` 그룹) · 1B 급 QLoRA · 모델 병합(CPU) |
| 학습 | Kaggle · Colab 의 무료 T4, 부족하면 EC2 스팟(AWS 크레딧). 연말에 학습용 데스크탑(PLAN #21) |

## thoth 와의 계약

thoth 워커가 `ENGINE=http` 로 이 저장소의 서버를 부른다(thoth `docs/now/MASTER.md` §7-4).

```
POST /translate  {"texts": [...], "source": "en", "target": "ko", "terms": {...}}
              →  {"translations": [...]}       같은 길이 · 같은 순서
GET  /health  →  {"model": "<이름>"}
```

`tests/thoth_conformance.py` 는 thoth 의 검사 도구 사본이다. 서버가 이것을 통과하면
thoth 에 그대로 끼워진다.

## 실행

```bash
cp .env.example .env     # SESHAT_DATA(SSD 레이크) · SESHAT_INBOX(다운로드 폴더)
uv sync
bash tools/verify.sh     # 점검 전부 — CI 도 이것만 부른다
```

**무거운 것은 그룹이 든다**(DECISIONS §4). 관문은 기본 의존성 0 으로 돌고, 필요한 판에서만 받는다 —
`--group eval`(chrF) · `--group qe`(신경망 자 · torch) · `--group aws` · `--group data`.
**그룹은 한 번에 다 적는다** — `uv sync --group eval --group qe` (하나만 적으면 다른 쪽이 지워진다 · §246).

**도구의 정본 목록은 `docs/now/MASTER.md` §14 하나다.** 여기에 다시 적지 않는다 —
두 곳에 적었더니 한쪽에만 있는 도구가 열셋이 됐다(DECISIONS §199).

## 데이터

**학습 데이터 · 모델 가중치 · 실행 결과는 저장소에 들어오지 않는다.** 비공개 저장소여도 같다. 쌍 로그의 원문은
사이트의 저작물이다. `data/private/` · `runs/` · `models/` 를 git 이 무시한다.
저장소에 있는 평가셋은 이 저장소가 직접 쓴 문장뿐이다(`data/eval/README.md`).

## 문서

**축이 셋이다 — `docs/now/` 지금 · `docs/next/` 앞으로 · `docs/why/` 왜.**
어느 문서를 열지와 **무엇을 어디에 적을지**는 [`docs/README.md`](docs/README.md) 가 든다.

**새 세션은 [`docs/next/PLAN.md`](docs/next/PLAN.md) §0 부터 읽는다.**
