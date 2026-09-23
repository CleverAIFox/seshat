# seshat — 현재 상태 정본

> **지금 이런 상태다**만 담는 문서다. 앞으로 할 일은 `PLAN.md`, 왜 그렇게 됐는지는
> `DECISIONS.md` 에 있다.
>
> 3인칭 · 평어체 `-다` · 단정. **절 번호는 자산이다.** 절을 지우지 않는다.

---

## 0. 서술 규약

**thoth 와 같은 규약이다**(DECISIONS §5 · thoth MASTER §0). 규약마다 강제자가 있다.

```bash
bash tools/verify.sh                     # ★ 아래 전부 + 레이크 — 점검 목록의 정본이다. CI 도 이것만 부른다
python3 tools/check_docs.py              # 문서 ↔ 문서 — 문체 · 절 · PLAN 표 · 참조 · DECISIONS
python3 tools/doc_fsck.py                # 문서 ↔ 실물 — 경로 · 테스트 · 죽은 도구
python3 tools/check_model_licenses.py    # 코드 ↔ 라이선스 대장
python3 tools/check_hypotheses.py        # 가설 대장 — 실험의 문
python3 tools/check_ontology.py          # 온톨로지 — 표기 유일 · 부모 · 끝소리
python3 tools/check_catalog.py           # 데이터 카탈로그 — 칸 · 쓰임 · data/ 의 카탈로그 밖 파일(§11)
python3 tools/sweep.py [--fix]           # WSL 위생 — seshat 이 남긴 흔적만(§12)
bash tools/deps.sh --merge               # 의존성 봇(Actions 만) — 초록만 합치고 가지를 지운다
bash tools/apply_patch.sh                # INBOX 의 최신 seshat-*.patch 를 커밋째 붙인다(§11)
```

| 규칙 | 강제자 |
|---|---|
| 3인칭 · 평어체 `-다` · PLAN 미래 · MASTER 현재 · DECISIONS 과거 | `tools/check_docs.py::check_style` · `tools/check_docs.py::check_master` |
| 세 문서의 `##` 는 번호가 있고 유일 · 연속이다 | `tools/check_docs.py::check_headings` |
| 다른 문서는 문서명을 앞에 적는다 — `MASTER §2` · `DECISIONS §3` · `PLAN #4`. 남의 저장소는 저장소 이름을 앞에 적는다 — `thoth MASTER §7-4` | `tools/check_docs.py::check_refs` |
| PLAN 은 §1 표 하나 · 제목의 행 수 · 영구 번호 · 닫힌 상태 어휘 | `tools/check_docs.py::check_plan` |
| DECISIONS 는 추가만 한다. 절마다 날짜 · 강제자 · `### 배운 것` | `tools/check_docs.py::check_decisions` |
| 문서가 적은 경로 · 테스트가 실재하고 도구는 어딘가에서 불린다 | `tools/doc_fsck.py::check_paths` · `tools/doc_fsck.py::check_tools` |
| 정규식 검사는 카나리아를 든다 | `tests/test_doc_enforcers.py` |
| 실험에 드는 가설은 검증 방법 · 비용 상한을, 판정은 근거를 든다 | `tools/check_hypotheses.py::check` |
| 온톨로지의 표기는 유일하고 영어로 남는 노드는 끝소리를 든다 | `tools/check_ontology.py` · `seshat/ontology.py::validate` |
| 점검 목록은 verify.sh 하나에 산다. CI 는 그것을 부르기만 하고 검사기는 빠짐없이 올라 있다 | `tests/test_workflows.py::test_CI_는_verify_를_부르기만_한다` · `tests/test_workflows.py::test_verify_가_검사기를_빠뜨리지_않는다` |
| 워크플로는 권한을 적는다. gitleaks 가 있는 곳은 PR 을 읽는다 | `tests/test_workflows.py::test_워크플로마다_권한을_적는다` · `tests/test_workflows.py::test_gitleaks_는_PR_을_읽을_수_있다` |
| 레이크는 넣기만 한다 · 대장 밖을 짚는다 · 가설의 근거가 레이크에 있다 | `tools/lake.py::check` · `tests/test_lake.py` |
| 데이터는 전부 카탈로그에 있다 · 미확인 라이선스는 학습에 못 쓴다 | `tools/check_catalog.py` · `seshat/catalog.py::validate` · `tests/test_catalog.py` |
| 위생 도구는 근거가 있을 때만 지운다 | `tools/sweep.py` · `tests/test_sweep.py` |

---

## 1. 무엇인가

thoth 가 `ENGINE=http` 로 부를 영한 번역 서버와, 그 서버에 올릴 모델을 만드는 도구다.
**목표는 영→한 범용에서 AWS Translate 를 넘는 것이고**(DECISIONS §11), thoth 의 도메인은 그 위의
특화다. **모델은 아직 없다.** `echo` 백엔드가 자리를 채우고 `aws-translate` 가 이길 대상을 잰다.

```
seshat/
  backends.py   (texts, terms) → translations. 모델이 들어갈 자리 · 기준선(aws-translate)
  serve.py      thoth 계약을 말하는 HTTP 서버. 표준 라이브러리
  evaluate.py   계약을 말하는 서버면 무엇이든 평가셋으로 잰다
tests/
  thoth_conformance.py   thoth 의 적합성 검사 사본. 여기서 고치지 않는다
data/eval/seed.jsonl     평가셋 0판 12줄
tools/fetch_flores.py    FLORES+ 영→한을 data/bench/ 에 받는다 (커밋하지 않는다)
```

## 2. thoth 와의 계약

| | 요청 | 응답 |
|---|---|---|
| `POST /translate` | `{"texts": [...], "source": "en", "target": "ko", "terms": {en: ko}}` | `{"translations": [...], "model": "..."}` |
| `GET /health` | — | `{"status": "ok", "model": "..."}` |

- `translations` 는 **같은 길이 · 같은 순서 · 문자열**이다. 어기면 thoth 워커가 502 를 낸다
- `model` 은 thoth 배포자가 선언한 `HTTP_MODEL` 과 같아야 한다. 다르면 thoth 전검사가
  기동을 막는다
- `Authorization: Bearer <토큰>` — `--token` 을 주면 요구한다. 상수 시간 비교다
- 한 요청 최대 50건. thoth 워커의 상한과 같다
- 백엔드가 길이를 어기면 서버가 먼저 `500 backend_length_mismatch` 로 죽는다

정본은 thoth `docs/MASTER.md` §7-4 다. 이 절은 그 요약이고, 어긋나면 저쪽이 맞다.

## 3. 평가

```bash
uv run --group eval python -m seshat.evaluate --url <서버> --set data/eval/seed.jsonl
HF_TOKEN=<토큰> uv run --group data python tools/fetch_flores.py            # 처음 한 번
AWS_PROFILE=<프로파일> uv run --group eval --group aws python -m seshat.evaluate \
  --backend aws-translate --set data/bench/flores_plus.devtest.jsonl --name aws-translate
```

★ **`--backend` 는 서버 없이 백엔드를 부른다.** 기준선은 서빙하지 않으므로 서버를 띄우지 않는다.
`aws-translate` 는 `BASELINE_ONLY` 이고 용어집을 싣지 않는다 — 있는 그대로가 기준선이다.

★ **FLORES+ 의 정답은 평어체다.** 합쇼체를 강제한 출력은 어미마다 chrF 가 깎인다. 범용 비교는 문체를
강제하지 않은 출력끼리 하고, 합쇼체는 `style` 로 따로 본다.

| 지표 | 정답 필요 | 뜻 |
|---|---|---|
| `style` | 아니다 | 마지막 문장이 합쇼체로 끝나는 비율. 문장부호 없는 명사구는 판정 밖 |
| `keep` | 아니다 | `keep` 의 영어 이름이 그대로 남은 비율 |
| `chrf` | 그렇다 | chrF++ (sacrebleu, `word_order=2`) |
| `ms` | — | 문장당 지연. 9건씩 묶어 보낸다 |
| `josa` | 아니다 | `keep` 이름 바로 뒤 조사가 그 이름의 끝소리(온톨로지 `coda`)와 맞는 비율. 조사가 붙지 않은 자리는 세지 않는다 |
| `term` | 아니다 | 원문에 나온 온톨로지 개념의 뜻이 남았나 — 공식(`ko`) 또는 허용(`alt_ko`) 표기가 번역에 있는 비율 |
| `term_off` | 아니다 | 그중 **공식 표기 그대로**인 비율. thoth 의 도메인은 표기까지 맞아야 한다 |
| `term_bad` | 아니다 | 관측된 오역(`bad_ko`)만 보이는 비율 — 뜻이 바뀐 자리다(DECISIONS §25) |

★ **가설 없이 재지 않는다.** echo 가 아닌 백엔드 · 서버는 `--hypothesis H-NNN` 을 요구하고 그 가설은 대장에서
`실험` 상태여야 한다(DECISIONS §14). 배선만 보는 실행은 `--smoke` 다.

★ **결과 파일 머리줄이 재현 조건을 든다** — `hypothesis` · `commit` · `dirty` · `set_sha256` · `chars` ·
`backend` · `weights` · `decoding` · `cost_usd`(AWS Translate). 가설을 채택 · 기각할 때 이 파일이 근거다.

| 백엔드 | 가중치 | 쓰임 |
|---|---|---|
| `echo` | — | 배선 |
| `aws-translate` | — | 이길 대상. 서빙하지 않는다(`BASELINE_ONLY`) |
| `translategemma-4b` | `google/translategemma-4b-it` · ollama Q4_K_M 3.3GB | 후보 1호. ollama 가 GPU 를 맡는다 · `temperature 0` · `seed 42` |
| `translategemma-4b+ph` | 같다 | H-001 처치군 — 용어 자리표시를 두른다 |

결과 파일은 `tools/rescore.py` 로 모델을 다시 부르지 않고 다시 채점한다 — 되돌리기를 바꿨을 때. 두 결과 파일은 `tools/compare_runs.py` 로 줄 단위로 대조한다 — 이긴 줄 · 진 줄 · 남은 자리표시 · 구문별 keep · 구문별 개념 유지 · 합쇼체가 한쪽에서만 깨진 줄 ·
가장 많이 잃은 이름. 평가셋 해시가 다르면 멈춘다. ollama 백엔드의 결과 파일은 머리줄에 `ollama`(GPU 적재 비율)를 싣는다.

탐침은 `tools/make_probes.py` 가 만든다 — 문형 템플릿 14 × 온톨로지 어휘, 결정적(`--seed`). 의미가 어색한 문장도
나온다(`move the encryption at rest from …`). 탐침은 이름 · 조사 · 구문을 보고 뜻의 그럴듯함은 보지 않는다.

결과는 `runs/<이름>-<시각>.jsonl` 에 머리줄(지표)과 줄마다의 출력으로 남는다.

★ `--thoth` 는 thoth 워커를 잰다. 요청에 `source.site = eval.seshat.local` 을 실어 워커가
쌍으로 남기지 않게 한다(DECISIONS §3).

| 평가셋 | 줄 | 정답 |
|---|---|---|
| `data/eval/seed.jsonl` | 12 | 초안. 사람이 쓰지 않는다 — 교사 합의 + 검사기로 만든다(PLAN #1) |
| `data/bench/flores_plus.dev.jsonl` · `.devtest.jsonl` | 997 · 1,012 | FLORES+ 정답(평어체) · CC BY-SA 4.0 · 받아서 쓴다 |

## 4. 기계

| | |
|---|---|
| GPU | GTX 1660 Ti · 6GB · Turing(sm_75). fp16 · int8 가능, bf16 · FlashAttention 2 불가. **연말에 학습용 데스크탑으로 바뀐다**(PLAN #21) |
| 파이썬 | 3.12 이상. 기본 의존성 0 |
| 의존성 그룹 | `dev`(pytest · ruff) · `eval`(sacrebleu) · `aws`(boto3 — 기준선) · `data`(huggingface_hub · pyarrow) |
| 저장소 | **비공개**(DECISIONS §8). 데이터는 그래도 커밋하지 않는다 |

## 5. 점검

```bash
bash tools/verify.sh              # 전부. 실패해도 끝까지 돌고 표로 보인다
bash tools/verify.sh --only=pytest  # 부분 실행 — 마지막에 일부러 실패한다
```

| 단계 | 무엇 | CI |
|---|---|---|
| ruff · pytest | 코드 | 돈다 |
| check_docs · doc_fsck | 문서 ↔ 문서 · 문서 ↔ 실물 | 돈다 |
| model_licenses · hypotheses · ontology · catalog | 대장 넷 | 돈다 |
| lake | SSD 레이크 대장 · 가설 근거(§11) | **CI 밖** — SSD 는 이 기계에만 있다 |

★ CI(`.github/workflows/ci.yml`)는 `bash tools/verify.sh` 한 줄이다. 목록을 늘어놓지 않는다(DECISIONS §20).
★ 이 기계에서 `SESHAT_DATA` 가 비었거나 드라이브가 안 붙었으면 `lake` 가 실패한다 — 조용히 건너뛰지 않는다.

## 6. 라이선스 대장

`seshat/licenses.py` 가 대장이다(DECISIONS §6). **지금은 비어 있다** — 가중치를 부르는 코드가 없다.
첫 가중치가 들어오는 커밋이 그 줄을 채운다.

| 상업 가부 | 뜻 |
|---|---|
| `yes` | 모델 카드가 상업 이용을 허용한다. 서빙 백엔드가 부를 수 있다 |
| `no` | 비상업. 비교 실험에서만 부른다 |
| `unknown` | 가중치의 라이선스가 따로 적혀 있지 않다. 서빙에 쓰지 않는다 |

★ **쓸 수 없는 가중치가 따로 있다**(DECISIONS §9). `EXCLUDED` 는 사용 허락 지역이 이 기계가 있는 곳을
빼는 라이선스다 — 비상업과 달리 비교 실험에서도 부르지 못하고, 대장에 올려도 실패다.

| 제외 | 사유 |
|---|---|
| `tencent/hunyuan-mt*` · `tencent/hy-mt*` | Tencent HY Community License — EU · 영국 · 대한민국 제외 |

---

## 7. 연구 트랙

**seshat 은 개발이 아니라 연구다**(DECISIONS §12). 화면은 thoth 가 맡고, 이 저장소는 번역의 뇌 — 모델 ·
데이터 · 평가 · 서빙 백엔드 — 만 든다. 가설은 `docs/hypotheses.md` 에, 남의 연구는 `docs/papers.md` 에 쌓는다.
비공개 저장소라 쌓는 지식은 공개하지 않는다. 데이터 · 가중치는 그래도 커밋하지 않는다(§2).

| 트랙 | 무엇 | 쌓이는 것 |
|---|---|---|
| R1 한 · 영 문법 대조 | 어순(SVO · SOV) · 조사 · 높임법 · 관형절 · 피동 · 부정 · 최상급 | 대조 항목별 오류 슬라이스 |
| R2 도메인 지식 · 온톨로지 | AWS 서비스 · 기능 · API · 파라미터 · 공식 한국어 표기의 그래프 | 용어 자리표시 · 참조(RAG) · 용어 보상의 원천 |
| R3 모델 · 구조 | 2026 년 흐름 — 디코더 LLM + 추론 시점 연산 · 검증 가능한 보상의 강화학습 · 소형 번역 특화 · SSM 혼합 · 증류 · 병합 | 후보 표 · 구조 대결 |
| R4 에이전트 교사 공장 | 초안 → 문법 · 용어 검토 → 수정의 그래프. **오프라인에서만** 돈다 — 실시간은 단일 모델 | 증류용 최고 품질 데이터 |
| R5 문형 커리큘럼 · 탐침 | 5형식 템플릿 × 도메인 어휘. 번역 방식이 아니라 약점을 찌르는 탐침 · 학습 순서 · 증강 | 구문별 약점 지도 |
| R6 강화학습 · 보상 | thoth 검사기 + QE 보상 · 보상마다 반대 추 · 해킹 카나리아 | 보상 함수 · 해킹 사례 |
| R7 평가 · EDA | FLORES+ · 도메인셋 · 오류 분류(MQM 류) · 구문 슬라이스 · 지표 편향 | 이길 대상의 숫자 · 판정 근거 |

★ **AI 는 직관이고 검증은 EDA 다.** 직관은 공짜로 대장에 오르고, 실험에 들어갈 때 검증 방법과 비용
상한이 문을 연다.

## 8. 인프라

| 층 | 지금 | 다음 |
|---|---|---|
| 앞단 | **없다.** 화면 · 확장은 thoth 다 | — |
| thoth 와의 경계 | HTTP JSON — `POST /translate` · `GET /health`(§2). thoth 워커(Lambda)가 서버 대 서버로 부른다 | 스트리밍이 필요하면 같은 경로에 SSE(thoth PLAN #38) |
| 서빙 | `serve.py` · 표준 라이브러리 · echo | 이미지 → ECR → Lambda 컨테이너(PLAN #27). 집의 장비로 서빙하지 않는다 — 꺼지면 thoth 번역이 죽는다 |
| 환경 | uv · ollama | 컨테이너(PLAN #26) — torch 가 들어올 때 |
| 실험 | `evaluate.py` → `runs/`(커밋 밖) · 머리줄에 재현 조건 · GPU 러너(§10) | 평가 게이트(PLAN #28) · 비용 장부 |
| 학습 | 없다 | ② 원격 T4 · 스팟 → ③ 학습용 데스크탑 |
| 데이터 | 저장소의 `data/`(작은 정본 · 받는 도구) · SSD 레이크 `SESHAT_DATA`(raw · runs · cache — §11) | thoth 쌍(원문만) · 교사 공장 산출 · 온톨로지 2판 원천 |

★ **HTTP 가 맞는 이유는 웹 도구라서가 아니다.** 브라우저는 thoth 워커만 부르고, seshat 을 부르는 것은
워커다. 둘이 다른 곳(Lambda 와 모델 서버)에 살기 때문에 서버 대 서버 HTTP 가 가장 단순한 경계다. 자원
설계(REST)가 아니라 함수 호출 두 개(RPC 풍 JSON)이고, 그것으로 충분하다.

## 9. AWS 온톨로지

`data/ontology/aws.jsonl` 이 도메인 지식의 원천이다(DECISIONS §13). **한 그래프를 세 곳에 쓴다** — 용어
자리표시(H-001) · 참조 번역(H-006) · 강화학습의 용어 보상(H-010).

| 종류 | 수 | 번역 | 예 |
|---|---|---|---|
| `service` | 41 | 영어로 남는다 | `Amazon Kinesis Data Streams` · 별칭 `Kinesis Data Streams` · `KDS` |
| `feature` | 20 | 영어로 남는다 · 부모가 서비스 | `AWS Glue Data Catalog` · `DynamoDB Streams` · S3 스토리지 클래스 |
| `api` | 12 | 영어로 남는다 · 부모가 서비스 | `PutRecord` · `BatchWriteItem` · `StartQueryExecution` |
| `concept` | 60 | 한국어로 옮긴다 | `partition key → 파티션 키` · `dead-letter queue → 배달 못한 편지 대기열` |

표기(이름 + 별칭)는 227 이고 전체에서 유일하다.

| 필드 | 뜻 |
|---|---|
| `coda` | 한국어로 읽은 끝소리 — `none`(모음) · `closed`(받침) · `rieul`(ㄹ). 자리표시 뒤 조사를 고른다. 약어 별칭은 마지막 글자의 영어 읽기로 센다(`IAM` 받침 · `KPL` ㄹ) |
| `src` | `thoth-glossary`(배포본에서 쓰는 값) · `author`(이 저장소가 적은 값) |
| `alt_ko` | **허용 표기.** 뜻이 통하는 다른 표기 — 음차(`role` → 롤) · 의역(`operational overhead` → 운영상의 부담) · 다른 공식 표기(`queue` → 큐 · 대기열) |
| `bad_ko` | **관측된 오역.** 뜻이 바뀐 표기다 — `quota` → 쿼리 한도 · `visibility timeout` → 시각성 시간 초과. H-001 에서 본 것만 적는다(DECISIONS §25) |

```python
from seshat import ontology, terms
onto = ontology.load()
masked, slots = terms.mask(onto, "Load records into Amazon S3 with AWS Glue.")   # ⟦T1⟧ · ⟦T2⟧
ko, missing = terms.unmask(model_output, slots)                                  # 조사를 끝소리로 고친다
```

★ **긴 표기가 이긴다.** `Amazon Kinesis Data Streams` 가 `Kinesis Data Streams` 보다 먼저 잡힌다.
★ **약어는 대소문자를 지킨다.** 영어 본문의 소문자 조각(`dms`)을 서비스로 읽지 않는다.
★ **서술격은 건드리지 않는다.** `⟦T1⟧이다` 의 `이` 는 조사가 아니다 — 조사 뒤에 한글이 이어지면 고치지 않는다.
★ **공식 한국어 표기와 대조하지 않았다.** 개념의 `ko` 는 thoth 용어집(배포본에서 쓰는 중)과 이 저장소가 적은
값이다. 대조는 PLAN #22 에 남았다.

## 10. GPU 러너

**지금의 GTX 1660 Ti 도 러너다**(DECISIONS §14). Turing(sm_75)은 현행 CUDA 가 지원하고, TranslateGemma 4B
Q4_K_M(3.3GB)이 6GB 에 온전히 올라간다. 러너는 `gpu` 라벨로 묶고, 새 장비가 오면 같은 라벨로 갈아 끼운다 —
워크플로(`.github/workflows/gpu-eval.yml`)는 바뀌지 않는다.

```bash
# GitHub → seshat → Settings → Actions → Runners → New self-hosted runner → Linux x64 가 주는 명령으로 받는다
mkdir -p ~/actions-runner && cd ~/actions-runner      # 저장소 밖 · 한 번
./config.sh --url https://github.com/CleverAIFox/seshat --token <화면의 토큰> \
  --labels gpu,wsl,gtx1660ti --name fox-laptop --unattended
./run.sh                                               # 켜 둘 동안만 받는다
```

| 전제 | 확인 |
|---|---|
| GPU 가 WSL 에 보인다 | `nvidia-smi` |
| ollama 가 떠 있다 | `curl -s 127.0.0.1:11434/api/version` |
| uv 가 있다 | 워크플로가 `setup-uv` 로도 깐다 |

★ **손으로만 돈다.** Actions → GPU 평가 → Run workflow 에 가설 번호를 넣는다. 푸시마다 GPU 를 돌리지 않는다.
★ **노트북이 꺼져 있으면 작업이 줄을 선다.** 켜고 `./run.sh` 를 띄우면 받아 간다.
★ **비공개 저장소라서 안전하다.** 셀프 호스티드 러너는 공개 저장소에서 남의 PR 을 이 기계에서 돌린다.
★ 러너 폴더(`~/actions-runner`)는 저장소 밖이다. 러너 토큰을 커밋하지 않는다.

## 11. 데이터 관리

**원본과 실험 결과는 SSD 레이크에 산다**(DECISIONS §21). 자리는 `.env` 의 `SESHAT_DATA` 다 — thoth 의
`/mnt/f/projects/thoth` 옆 `/mnt/f/projects/seshat`. 경로 정본은 `seshat/paths.py` 이고 **셸이 `.env` 를 이긴다.**
심링크는 쓰지 않는다.

| 층 | 무엇 | 대장 | 백업 |
|---|---|---|---|
| `raw` | 바꾸지 않는 원본 — thoth 쌍(원문) · 도메인 문서 스냅숏 · 수집한 공식 용어집 | `MANIFEST.tsv` | 한다 |
| `runs` | 실험 결과. 다시 만들 수 없다 — 그날의 가중치 · 서버 · GPU 시간. 가설 대장의 `runs/…` 근거가 여기 있다 | `MANIFEST.tsv` | 한다 |
| `cache` | 다시 받는 것 — FLORES+ · 논문 PDF · 가중치 | 없다 | 안 한다 |

| 저장소 안에 남는 것 | 이유 |
|---|---|
| `data/ontology/` · `data/eval/seed.jsonl` | 사람이 고치는 작은 정본이다. diff 로 봐야 한다 |
| 받는 도구(`fetch_flores.py`) · 만드는 도구(`make_probes.py`) | 산출물은 다시 만든다 |
| `docs/papers.md` | 논문의 **읽은 결과**가 자산이다. PDF 는 cache 다 |

```bash
python3 tools/lake.py init                   # 한 번 — 층 디렉터리와 MANIFEST.tsv
python3 tools/lake.py put runs /tmp/h001/*/*.jsonl runs/*.jsonl   # 결과를 넣는다. 같은 이름 · 다른 내용은 거절
python3 tools/lake.py check                  # 해시 · 대장 밖 파일 · 가설 근거
```

★ **넣기만 한다.** 같은 이름에 다른 내용이 오면 거절한다 — 가설의 근거가 조용히 다른 파일이 되면 판정이 거짓말을 한다.
★ **GPU 러너가 바로 넣는다.** 러너가 이 기계라서 `gpu-eval.yml` 이 레이크에 쓴다. 러너는 `~/actions-runner/.env` 에서
  `SESHAT_DATA` 를 받는다(적고 `./run.sh` 를 다시 띄운다). 아티팩트는 사본이다.
★ **INBOX 는 브라우저 다운로드 폴더다**(`SESHAT_INBOX` = thoth 의 `WIN_DOWNLOADS`). 패치가 그리로 온다.
  `tools/apply_patch.sh` 가 거기서 최신 `seshat-*.patch` 를 골라 CRLF 를 벗기고 `git am` 으로 붙인다. 이미 붙은
  패치(커밋 제목이 이력에 있다)는 아무것도 안 한다.
### 11-1. 카탈로그

**`data/catalog.toml` 이 데이터의 대장이다**(DECISIONS §22). 파이어레인 `sources.yaml` 의 규칙을 옮겼다 —
**카탈로그에 없는 파일은 레이크에 못 들어오고, 레이크나 `data/` 에 있으면 실패다.**

| 칸 | 뜻 |
|---|---|
| `where` | `repo:<glob>` · `lake:<glob>`. 레이크의 자리도 카탈로그가 정한다(`put raw --into thoth-pairs`) |
| `license` | 모르면 `미확인` 이다. 비워 두지 않는다 |
| `uses` | `eval` · `evidence` · `train` · `ontology` · `reference` · `serve`. **학습 로더는 `seshat.catalog.allowed(id, "train")` 을 묻는다** |
| `how` | 얻는 도구 또는 `사람`. 도구 경로는 실재해야 한다 |

★ **쓰임이 문이다.** 평가셋(FLORES+ · 탐침)은 `train` 이 없다 — 학습에 새면 이길 대상의 숫자가 거짓말을 한다.
  라이선스가 `미확인` 인 출처(AWS 문서 스냅숏)는 `train` 을 달 수 없다.
★ 가중치의 라이선스는 `seshat/licenses.py` 가 정본이다(§6). 카탈로그는 자리만 든다.
★ 파이어레인에서 옮기지 않은 것 — norm 층 · 봉인 · 획득 게이트. 원본이 작고 손으로 모으지 않는다.

## 12. WSL 위생

```bash
python3 tools/sweep.py          # 센다
python3 tools/sweep.py --fix    # 근거가 확실한 것만 지운다
```

**seshat 이 싼 것만 친다**(DECISIONS §23). 기계 하나에 하나인 것 — uv 캐시 · ollama 모델 · WSL 디스크 — 은
thoth 의 sweep · doctor(`OLLAMA_KEEP_ALSO`)가 본다. 두 저장소가 같은 자리를 치지 않는다.

| 자리 | 지우는 근거 | 없으면 |
|---|---|---|
| INBOX 의 `seshat-*.patch` | 커밋 제목이 전부 이력에 있다. 제목 없는 옛 패치(seshat-017 까지)는 역적용 · 파일 이름의 번호 | 판정 못함 — 남긴다 |
| 작업대 결과 `runs/` · `/tmp/hNNN/` | 레이크에 **같은 해시로** 있다 | 레이크 밖 — `lake.py put` 이 먼저다 |
| `/tmp/seshat-*` | seshat 도구의 임시 이름 | — |
| 러너 `_diag` 로그 | 지우지 않는다. 14일 넘은 것을 나열만 한다 | — |

★ 판정 규칙은 `tools/patch_subjects.py` 하나다. `apply_patch.sh`(붙었으면 안 한다)와 `sweep.py`(붙었으면 지운다)가
  같은 것을 쓴다. 레이크가 안 붙었으면 작업대 결과는 **못 잼**이다 — 0건이 아니다.
