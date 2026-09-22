# seshat — 현재 상태 정본

> **지금 이런 상태다**만 담는 문서다. 앞으로 할 일은 `PLAN.md`, 왜 그렇게 됐는지는
> `DECISIONS.md` 에 있다.
>
> 3인칭 · 평어체 `-다` · 단정. **절 번호는 자산이다.** 절을 지우지 않는다.

---

## 0. 서술 규약

**thoth 와 같은 규약이다**(DECISIONS §5 · thoth MASTER §0). 규약마다 강제자가 있다.

```bash
python3 tools/check_docs.py              # 문서 ↔ 문서 — 문체 · 절 · PLAN 표 · 참조 · DECISIONS
python3 tools/doc_fsck.py                # 문서 ↔ 실물 — 경로 · 테스트 · 죽은 도구
python3 tools/check_model_licenses.py    # 코드 ↔ 라이선스 대장
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
uv run pytest
uv run ruff check .
python3 tools/check_docs.py
python3 tools/doc_fsck.py
python3 tools/check_model_licenses.py
```

CI(`.github/workflows/ci.yml`)가 같은 다섯을 돈다.

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
