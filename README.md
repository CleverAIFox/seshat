# seshat

[thoth](https://github.com/CleverAIFox/thoth) 에 끼울 **영한 번역 모델**을 만드는 저장소. **비공개다.**

thoth 는 영어 자격증 문제 화면에 한글 번역을 겹쳐 보여주는 크롬 확장과 워커다.
지금은 Bedrock Nova Lite 가 번역하고, 이 저장소의 모델이 그 자리를 넘겨받는다.
이름은 토트(문자의 신)의 짝인 **세샤트** — 기록과 문자, 도서관의 여신에서 왔다.

## 방향

**사전학습 모델을 고르고 좁힌다. 처음부터 만들지 않는다.** 전 세계가 갈고 닦는
모델과 도구(transformers · PEFT · CTranslate2 · llama.cpp · sacrebleu)를 그대로 쓰고,
이 저장소가 더하는 것은 셋이다.

1. **좁은 과제** — 범용 번역이 아니라 "영어 자격증 문제 → 한국어 합쇼체". 서비스명 ·
   API 명은 영어로 남기고 조사를 붙인다
2. **자기 데이터** — thoth 배포본이 쌓는 쌍(원문 · 모델 출력 · 후처리 결과)
3. **자** — 평가셋과 지표. 모델을 바꾸기 전에 잰다

목표는 Nova Lite 와 **같거나 나은 품질을, 더 싸고 빠르게**다. 범용 번역에서 최신
대형 모델을 이기는 것은 목표가 아니다.

## 기계

| | |
|---|---|
| 로컬 GPU | GTX 1660 Ti · VRAM 6GB · Turing — fp16 은 되고 bf16 · FlashAttention 2 는 안 된다 |
| 로컬에서 하는 것 | 평가 · 추론 확인 · 1B 급 QLoRA |
| 학습 | Kaggle · Colab 의 무료 T4, 부족하면 EC2 스팟(AWS 크레딧) |

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
uv sync
uv run pytest                                     # 계약 · 평가 · 평가셋 불변식
uv run python -m seshat.serve                     # echo 백엔드 · 127.0.0.1:8100
uv run --group eval python -m seshat.evaluate \
    --url http://127.0.0.1:8100 --set data/eval/seed.jsonl
python3 tools/check_docs.py                       # 문서 ↔ 문서 (규약은 docs/MASTER.md §0)
python3 tools/doc_fsck.py                         # 문서 ↔ 실물
python3 tools/check_model_licenses.py --list      # 가중치 라이선스 대장
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
