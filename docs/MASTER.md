# seshat — 현재 상태 정본

> **지금 이런 상태다**만 담는 문서다. 앞으로 할 일은 `PLAN.md`, 왜 그렇게 됐는지는
> `DECISIONS.md` 에 있다.
>
> 3인칭 · 평어체 `-다` · 단정. **절 번호는 자산이다.** 절을 지우지 않는다.

---

## 0. 서술 규약

**thoth 와 같은 규약이다**(DECISIONS §5 · thoth MASTER §0). 규약마다 강제자가 있다.

```bash
bash tools/verify.sh     # 규약을 포함한 점검 전부 — 점검 목록의 정본이다. CI 도 이것만 부른다
```

**명령 목록은 여기 안 적는다 — 정본은 §14 다**(DECISIONS §283). 2026-10-03 까지 이 자리에
명령 13줄이 있었고, 그것이 든 도구 17 이 **전부 §14 에도 있었다**(여기에만 있는 것은 0). 그런데
`docs/README.md` 는 「명령의 정본은 §0 이다」 라고, §14 는 「정본은 이 절이다」 라고 적고 있었다 —
**「정본이 하나다」 를 두 곳에 적으면 정본이 둘이 된다.** §199 가 고친 병의 재발이고, 그때와
다른 것은 **한쪽이 자기를 정본이라고 선언하고 있었다는 것**뿐이다.
강제자는 `tools/check_prose.py` 의 「명령의 정본은 한 곳이다」 다.


| 규칙 | 강제자 |
|---|---|
| 3인칭 · 평어체 `-다` · PLAN 미래 · MASTER 현재 · DECISIONS 과거 | `tools/check_docs.py::check_style` · `tools/check_docs.py::check_master` |
| 세 문서의 `##` 는 번호가 있고 유일 · 연속이다 | `tools/check_docs.py::check_headings` |
| 다른 문서는 문서명을 앞에 적는다 — `MASTER §2` · `DECISIONS §3` · `PLAN #18`. 남의 저장소는 저장소 이름을 앞에 적는다 — `thoth MASTER §7-4` | `tools/check_docs.py::check_refs` |
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
| **사전 지문은 채점기가 읽는 칸만 해싱한다**(`onto_score`). 주석 · `src` · `ko_ref` 를 고치는 것은 **뜻이 안 바뀐 편집**이고 옛 판을 막으면 안 된다. 옛 판과는 안 갈라선다 — 둘 다 그 칸을 들었을 때만 새 축으로 묻는다(DECISIONS §171) | `seshat/ontology.py::채점_지문` · `seshat/compare.py::사전축` · `tests/test_compare.py` |
| **셋은 어느 사전으로 만들어졌는지를 든다**(`onto_score`). 셋의 `keep` · `lit` · `ui` 자리는 만들 때의 사전이 찍은 것이라 사전이 넓어져도 안 늘어난다 — 판마다 `set_stale` 이 그것을 말한다(DECISIONS §171 · §207) | `tools/fetch_awsdocs.py` · `seshat/evaluate.py::셋이_낡았나` · `tests/test_noise.py` |
| **기록판은 손으로 안 고친다 — 선 줄도 그렇다.** 기록은 `--update`, 선은 `--pin-target` 이 판에서 박는다(DECISIONS §171) | `tools/gate.py::_블록을_고친다` · `tools/gate.py::_선을_박는다` · `tests/test_gate.py` |
| **점수를 내는 셋에서 캔 노드는 누수 장부에 적는다.** 출처를 사전 안에 적지 않는다 — 적으면 `onto_sha256` 이 바뀌어 **뜻이 안 바뀐 편집이 옛 판을 전부 막는다**(DECISIONS §168) | `data/ontology/mined.jsonl` · `tools/check_ontology.py` · `tools/mine_terms.py` 의 거절 · `tests/test_mined.py` |
| **차이가 잡음인지는 손으로 안 정한다.** 허용치 · 배수 · 중앙값을 사람이 그으면 자가 변수에 안 맞는다 — 2026-09-28 하루에 세 번 틀렸다(§139 · §178 · §179). 짝지은 부트스트랩이 **크기와 확실함을 따로** 준다(DECISIONS §180) | `tools/bootstrap.py` · `tests/test_bootstrap.py` · `verify.sh` 의 `bootstrap` 단계 |
| **🔴 는 「지금 적어 놓은 문장 하나를 못 쓰게 하는 빚」 이다.** 「측정을 더럽힌다」 만으로는 끝이 없다 — 재는 것은 늘 조금씩 더럽다. 각 🔴 행은 `docs/related.md` §3 의 **어느 줄을 막는지**를 든다. 그러면 🔴 의 수가 **말하려는 문장의 수로 위가 막힌다**(DECISIONS §187) | `tools/check_docs.py::check_plan` |
| **가설을 닫는 판마다 빚 한 줄을 같이 움직인다.** 재면 **재는 도구의 결함이 보이므로** 가설 닫기는 빚을 만든다 — 2026-09-28 가설 17 을 닫고 빚이 18 에서 20 이 됐다(DECISIONS §168) | 패치 제목 아래 **갚은 줄**을 적는다 · `docs/PLAN.md` #47 |
| 위생 도구는 근거가 있을 때만 지운다 | `tools/sweep.py` · `tests/test_sweep.py` |


### 0-0. 낱말

**이 저장소가 쓰는 말이다.** 거의 다 지어낸 말이고 **어디에도 정의가 없었다**(DECISIONS §284) —
`강제자` 474 · `자` 4,814 · `축` 336 · `탐침` 184 번 쓰면서. 세션이 바뀌면 문맥이 초기화되므로
(DECISIONS §9) **다음 세션은 이 표부터 읽는다.**

| 낱말 | 뜻 | 헷갈리는 자리 |
|---|---|---|
| **자** | 재는 것 — 지표든 판정자든. 「한 자만 걸면 그 자의 맹점이 그대로 들어온다」 | 조사 `-자` 와 글자가 같다. **「이 자」 · 「그 자」 꼴일 때만** 이 뜻이다 |
| **셋** | 평가 · 학습에 쓰는 줄 묶음(set). `d002` · 탐침 셋 · 증류셋 | 수 3 과 글자가 같다. 「스물셋」 은 수다 |
| **팔** | 견주는 대상 하나(arm). `gemma3-4b+ph+retry` 가 한 팔이다 | — |
| **판** | **실행 한 번.** 「한 판에 수십 분」 · 「네 판에서 재현됐다」 | **버전은 「판본」 이다.** `판단` · `판정` 은 딴 말이다 |
| **축** | 세 뜻이다 — ① 견주는 기준 차원(「축이 둘이다」) ② 문서 축(`now` · `next` · `why`) ③ `docgen` 이 채우는 수 자리 | 셋 다 쓴다. **문맥이 가른다** |
| **관문** | 통과해야 미는 검사. `verify.sh` 의 단계들 | thoth 는 같은 것을 **「게이트」** 라 부른다(DECISIONS §284). 둘은 같은 말이고 저장소마다 다르다 |
| **문** | 들어가는 조건. 「실험의 문」 — 가설 대장을 안 거치면 못 들어간다 | 관문과 다르다. 관문은 **나가는** 쪽이다 |
| **정본** | 그 사실이 사는 **유일한** 자리. 나머지는 그것을 가리킨다 | — |
| **강제자** | 그 문장을 지키는 코드. 문장만 있고 강제자가 없으면 **그것은 약속이 아니다** | — |
| **봉인** | 절이 짚은 코드의 지문. 그 코드가 바뀌면 절이 **「다시 봐야 한다」** 가 된다 | 「틀렸다」 가 아니다 |
| **장부** | 알려진 나쁜 것의 **언** 목록. 라쳇의 밑동 | — |
| **라쳇** | 늘면 울고, 줄면 장부를 같이 내리는 수. **느슨해진 라쳇은 초록으로 위장한다** | — |
| **탐침** | 검사가 살아 있는지 보려고 **일부러 넣는** 입력 | — |
| **카나리아** | 정규식·판별식이 죽었는지 보는 양성 대조. 죽으면 **2** 로 끝난다(위반은 1) | — |
| **족** | 인스턴스가 아니라 **종류**를 무는 것. 「이 작업에 상한이 있나」 가 아니라 「상한 없는 작업이 있나」 | 파이어레인 `gate_parity.py` 의 말이다 |
| **문턱** | 판정 경계. **분포를 보고 정한다 — 정하고 분포를 보지 않는다**(DECISIONS §279) | — |
| **갈래** | 분류 이름. 「이탈 갈래」 · 「탐침 갈래」 | — |
| **울타리** | 사전으로 좁힌 것(`gloss`) | — |
| **겹옷** | 프롬프트에 덧씌운 층. 「겹옷을 벗겨도 뜻이 안 올랐다」 | — |


---

★ §0-1 **「배운 것」 의 ★ 줄은 근거의 분모를 든다**(DECISIONS §167). 그 줄은 법칙처럼 읽히고, 반년 뒤에 읽는 사람은 근거를 안 찾는다. 셋 · 팔 · 분모를 안 적으면 **d001 600줄 · 4B 한 팔**에서 본 것이 일반화된 주장이 된다. **좁혀 적어야 다음 판이 그것을 잴 수 있다.**

★ §0-2 **이 표는 장식이 아니다.** 오른 낱말이 실제로 안 쓰이면 `check_prose` 가 운다 —
**죽은 낱말은 사전을 믿을 수 없게 만든다.** 반대쪽(자주 쓰는데 표에 없는 말)은 기계가 못 찾아서
사람이 본다(`PLAN #50`).

## 1. 무엇인가

thoth 가 `ENGINE=http` 로 부를 영한 번역 서버와, 그 서버에 올릴 모델을 만드는 도구다.
**목표는 영→한 범용에서 AWS Translate 를 넘는 것이고**(DECISIONS §11), thoth 의 도메인은 그 위의
특화다. **지금 선 팔의 정본은 `data/scoreboard.toml` 이다**(DECISIONS §131) — `tools/gate.py` 가 판에서 박고
손으로 안 고친다. 처음 0 을 넘은 팔은 `gemma3-4b+ph+retry+endings+terms` 였고(2026-09-23 · DECISIONS
§58 · §61) 탐침 200 줄에서 keep 0.993 · josa 1.0 · style 1.00 · 공식 표기 0.846 대 AWS Translate 0.795 였다.
**체급은 양쪽을 다 올린다** — 공정한 사전 · 탐침 600 줄에서 12B 가 도메인 term_off 를 **+0.068**(p < 0.001),
범용 chrf 를 +4.97 올린다(DECISIONS §90). 처음의 −0.066 은 사전의 빈자리였다(§86 · §87). **실문서 600 줄에서는 같은 부호에 +0.035 다**(p = 0.003 · DECISIONS §94 · §97) — 탐침은 순위를 옮기고 값은 안 옮긴다. **그 0.035 가 진짜 격차는 아니다** — `term_off` 는 「표기가 다르다」와 「뜻이 틀렸다」를 같은 무게로 세고, 4B 가 이긴 자리는 전자뿐인데 12B 가 이긴 자리는 후자다(DECISIONS §98 · H-046). **탐침 200 줄의 형식 지표에서는 닫혔다** — 줄을 열면 아직 샌다(DECISIONS §95 · §263). 다만 **이것은 AWS 도메인 표기에 한한 승리다**(DECISIONS §76) — 사전이 안 닿는
FLORES+ 범용 200 줄에서는 chrf 28.83 대 AWS 38.47 로 **9.6 점 뒤진다.** 남은 것은 뜻과 어순이고,
그 둘은 사전이 아니라 **학습의 일**이다.
**도메인 표기 전선에서는** `aws-translate` 가 넘어선 **기준선**이고, 범용에서는 아직 9.6 점 뒤지므로
거기서는 **여전히 이길 대상**이다 — 한 이름이 전선마다 다른 자리에 선다.

```
seshat/
  backends.py   (texts, terms) → translations. 모델이 들어갈 자리 · 기준선(aws-translate)
                번역 전용 모델은 `/api/generate`, 범용 지시 모델은 `/api/chat` + 사고 끄기(DECISIONS §48)
  serve.py      thoth 계약을 말하는 HTTP 서버. 표준 라이브러리
  evaluate.py   계약을 말하는 서버면 무엇이든 평가셋으로 잰다
tests/
  thoth_conformance.py   thoth 의 적합성 검사 사본. 여기서 고치지 않는다
data/eval/seed.jsonl     평가셋 0판 12줄
tools/doctor.py          **이 기계**를 센다 — 레이크 · 가중치 자리 · 작업대 잔재 · .env · 디스크 (verify 는 저장소를 본다)
tools/fetch_flores.py    FLORES+ 영→한을 data/bench/ 에 받는다 (커밋하지 않는다)
tools/fetch_awsdocs.py   AWS 공식 안내서(CC BY-SA 4.0)에서 도메인 문장을 뽑는다 → data/domain/ (커밋하지 않는다)
```

봉인 — `data/scoreboard.toml`
  지금 선 팔과 그 값. 2026-10-02 이 절이 9일 묵은 팔을 이름으로 들고 있었다(DECISIONS §281).

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
uv run --group eval python -m seshat.evaluate --url https://<워커> --thoth \
  --thoth-token <토큰> --set data/eval/seed.jsonl --name nova-lite   # thoth 배포본(Nova Lite)
```

★ §3-1 **`--backend` 는 서버 없이 백엔드를 부른다.** 기준선은 서빙하지 않으므로 서버를 띄우지 않는다.
`aws-translate` 는 `BASELINE_ONLY` 이고 용어집을 싣지 않는다 — 있는 그대로가 기준선이다.

★ §3-2 **FLORES+ 의 정답은 평어체다.** 합쇼체를 강제한 출력은 어미마다 chrF 가 깎인다. 범용 비교는 문체를
강제하지 않은 출력끼리 하고, 합쇼체는 `style` 로 따로 본다.

| 지표 | 정답 필요 | 뜻 |
|---|---|---|
| `style` | 아니다 | 마지막 문장이 합쇼체로 끝나는 비율. 문장부호 없는 명사구는 판정 밖 |
| `keep` | 아니다 | `keep` 의 영어 이름이 그대로 남은 비율 — 근거는 **사전**이다 |
| `lit` · `lit_n` | 아니다 | 원문이 `` ` `` 로 표시한 글자(식별자 · 값)가 그대로 남은 비율 — 근거는 사전이 아니라 **문서**다(DECISIONS §122) |
| `ui` · `ui_n` | 아니다 | 원문이 `**굵게**` 로 표시한 글자(콘솔 라벨)가 그대로 남은 비율. 한국어 AWS 문서도 라벨은 영어로 둔다 — `[**Security Groups**]`(DECISIONS §123) |
| `chrf` | 그렇다 | chrF++ (sacrebleu, `word_order=2`) |
| `ms` | — | 문장당 지연. 9건씩 묶어 보낸다 |
| `josa` | 아니다 | `keep` 이름 바로 뒤 조사가 그 이름의 끝소리(온톨로지 `coda`)와 맞는 비율. 조사가 붙지 않은 자리는 세지 않는다 |
| `hangul` | 아니다 | **번역처럼 보이는 줄의 비율** — **지킨 이름을 뺀 뒤** 한글이 글자의 20% 이상이고 길이가 `3 × 원문 + 40` 이내. **`+ 40` 이 짧은 줄의 판정을 가른다** — 그것 없이 「세 배」 로만 적으면 보기 한 줄짜리가 거짓으로 걸린다. 정본은 `seshat/evaluate.py::ko_line` 이다. 배선이 깨지면 여기서 먼저 보인다(DECISIONS §49 · §50) |
| `term` | 아니다 | 원문에 나온 온톨로지 개념의 뜻이 남았나 — 공식(`ko`) 또는 허용(`alt_ko`) 표기가 번역에 있는 비율. **문서가 표시한 자리(`lit` · `ui`)는 개념이 아니라 값 · 라벨이므로 분모에서 뺀다**(DECISIONS §122 · §123) |
| `term_off` | 아니다 | 그중 **공식 표기 그대로**인 비율. thoth 의 도메인은 표기까지 맞아야 한다 |
| `term_bad` | 아니다 | 관측된 오역(`bad_ko`)만 보이는 비율 — 뜻이 바뀐 자리다(DECISIONS §25) |
| `n` | 아니다 | 잰 줄 수. `compare_runs` 는 줄 수가 다른 두 파일을 비교하지 않는다(DECISIONS §45) |
| `onto_sha256` | 아니다 | 채점에 쓴 온톨로지의 해시 — 사전이 다르면 `compare_runs` 가 멈춘다(DECISIONS §32) |
| `post` | 아니다 | 재채점에 붙인 후처리 — `none` · `endings`(해요체 의문 → 합쇼체 · DECISIONS §31) |
| `set_sha256` · `set_was` | 아니다 | 실제로 잰 셋의 해시. 재채점이 다른 셋을 대면 원래 것을 `set_was` 로 남긴다(DECISIONS §122) |

★ §3-3 **가설 없이 재지 않는다.** echo 가 아닌 백엔드 · 서버는 `--hypothesis H-NNN` 을 요구하고 그 가설은 대장에서
`실험` 상태여야 한다(DECISIONS §14). 배선만 보는 실행은 `--smoke` 다.

★ §3-4 **결과 파일 머리줄이 재현 조건을 든다.** 가설을 채택 · 기각할 때 이 파일이 근거다.
  **칸의 정본은 `seshat/evaluate.py` 가 쓰는 머리줄 하나다** — 여기 목록을 두면 칸이 늘 때 갈린다
  (2026-10-02 실제로 갈려 있었다 · DECISIONS §281). 판정에 바로 걸리는 칸만 적는다:
  `metrics`(자가 바뀌면 옛 수와 못 견준다 · DECISIONS §145) · `onto_leak`(시험지가 제 분모를 골랐나 ·
  DECISIONS §171) · `set_stale`(셋이 만들어진 뒤 사전이 자랐나 · DECISIONS §207) ·
  `dirty`(깨끗하지 않은 나무에서 쟀나).

**백엔드 이름의 정본은 `seshat/backends.py` 의 `REGISTRY` 다.** 여기 표를 두었더니 넷을 적는 동안
실물이 서른이 됐다(DECISIONS §281). 두 자리만 뜻이 고정돼 있어 적어 둔다 —
`echo` 는 배선이고, `aws-translate` 는 **이길 대상이라 서빙하지 않는다**(`BASELINE_ONLY`).

**커밋 시점 방어는 `.githooks/pre-commit` 이고 그것이 실제로 도는지는 `tools/hookcheck.sh` 가
실행으로 잰다**(DECISIONS §164) — 「훅 파일이 있는가」 와 「훅이 도는가」 는 다른 물음이다.
**다만 훅은 강제자가 아니라 빠른 되먹임이다**(§170) — 이 기계의 `core.hooksPath` 에 살아서 새로
받은 저장소에도 남의 PR 에도 없다. **남을 막는 것은 CI 뿐**이고 그것이 초록인지는 `ci_status.py` 가 본다.

★ §3-5 **아래는 까닭이다. 어느 도구를 언제 쓰는지는 §14 하나가 든다**(DECISIONS §216).

| 무엇이 안 보였나 | 그래서 무엇이 생겼나 |
|---|---|
| 같은 규칙이 몇 벌인지 | `dupcheck` — 함수 · 긴 글자 · **부름 꼴**까지 센다. 2026-09-28 의 사본 넷은 전부 상수였고 아홉 번째 병은 `compare.갈림` 의 축이 곳마다 다른 것이었다(§163 · §171). **자리는 병이 나기 전에 셀 수 있다** |
| 사전이 모르는 말 | `mine_terms` — `term` 은 사전이 찾은 것만 세므로 **좁은 사전은 점수가 높은 것이 아니라 재는 범위가 좁은 것**이다(§160). 캔 것은 후보이고 AWS 한국어 문서와 대조한 뒤에 사전에 든다 |
| 두 판이 **어느 개념**에서 갈렸나 | `term_diff` — 줄 대조로는 한 줄에 든 여러 용어를 못 가른다(§85) |
| 숫자 뒤의 줄 | `show_misses` — 사라진 이름 · 버린 개념 · 오역 · 번역이 아닌 줄 · **가장 짧은 줄**(§214) |
| 되돌리기를 바꿨을 때 | `rescore` — 모델을 다시 안 부르고 다시 채점한다 |
| 같은 팔의 흔들림 | `noise` — **지표 퍼짐과 줄 흔들림은 다른 수**이고 둘을 한 문장으로 내지 않는다(§139) |
| 두 판의 줄 단위 차 | `compare_runs` — 이긴 줄 · 진 줄 · 남은 자리표시 · 구문별 keep · 합쇼체가 한쪽에서만 깨진 줄. 평가셋 해시가 다르면 멈춘다 |

ollama 백엔드의 결과 파일은 머리줄에 `ollama`(GPU 적재 비율)를 싣는다.

탐침은 `tools/make_probes.py` 가 만든다 — 문형 템플릿 14 × 온톨로지 어휘, 결정적(`--seed`). 의미가 어색한 문장도
나온다(`move the encryption at rest from …`). 탐침은 이름 · 조사 · 구문을 보고 뜻의 그럴듯함은 보지 않는다.

**실문서 도메인셋**은 `tools/fetch_awsdocs.py` 가 만든다 — AWS 공식 안내서 14권(`awsdocs/*` · **CC BY-SA 4.0** ·
DECISIONS §92)에서 산문 문장만 꺼내고 **온톨로지가 든 줄만** 남긴다. 온톨로지가 든 문장이 59,145 다. 정답이 없다 —
도메인 지표는 참조 없이 센다. 안내서마다 상한을 두고(`--cap`) 문장 해시로 정렬한 뒤 `--seed` 로 뽑아 결정적이다.
**탐침과 실문서 중 무엇이 맞는 자인지는 아직 모른다**(H-045 · DECISIONS §93).

결과는 `runs/<이름>-<시각>.jsonl` 에 머리줄(지표)과 줄마다의 출력으로 남는다.

★ §3-6 `--thoth` 는 thoth 워커를 잰다. 요청에 `source.site = eval.seshat.local` 을 실어 워커가
쌍으로 남기지 않게 한다(DECISIONS §3).

| 평가셋 | 줄 | 정답 |
|---|---|---|
| `data/eval/seed.jsonl` | 12 | 초안. 사람이 쓰지 않는다 — 교사 합의 + 검사기로 만든다(PLAN #18 · DECISIONS §262) |
| `data/bench/flores_plus.dev.jsonl` · `.devtest.jsonl` | 997 · 1,012 | FLORES+ 정답(평어체) · CC BY-SA 4.0 · 받아서 쓴다 |

봉인 — `seshat/evaluate.py`
  지표 · 머리줄 칸 · 판정 조건. 칸이 늘면 이 절을 다시 읽는다.

## 4. 기계

| | |
|---|---|
| GPU | GTX 1660 Ti · 6GB · Turing(sm_75). fp16 · int8 가능, bf16 · FlashAttention 2 불가. **연말에 학습용 데스크탑으로 바뀐다**(PLAN #21) |
| 카드에 안 들어가는 모델 | **로컬로 안 부른다.** 12B Q4 는 7.6GB 로 6GB 카드를 넘고, 2026-09-29 재니 `eval rate` 0.94 tok/s · 한 줄 21분이었다. 같은 일로 윈도우가 두 번 뻗었다 — 느린 것이 아니라 위험하다(DECISIONS §84). **빌려서 잰다** — Colab 무료 T4 · 터널 · `OLLAMA_URL`. `backends.들어가나` 가 부르기 전에 막고 그 길을 준다(DECISIONS §201) |
| 파이썬 | 3.12 이상. 기본 의존성 0 |
| 의존성 그룹 | `dev`(pytest · ruff) · `eval`(sacrebleu) · `aws`(boto3 — 기준선) · `data`(huggingface_hub · pyarrow) |
| 저장소 | **비공개**(DECISIONS §8). 데이터는 그래도 커밋하지 않는다 |

## 5. 점검

```bash
bash tools/verify.sh              # 전부. 실패해도 끝까지 돌고 표로 보인다
bash tools/verify.sh --only=pytest  # 부분 실행 — 마지막에 일부러 실패한다
```

**단계 목록의 정본은 `tools/verify.sh` 하나다.** 여기 표를 두었더니 열하나를 적는 동안 실물이
스물셋이 됐다(DECISIONS §281) — `verify.sh` 머리말이 **바로 이 사고를 겪고 적어 둔 자리**인데
같은 자리가 또 어긋났다. **CI 에서 다르게 도는 것만 적는다** — `훅`(CI 는 커밋을 안 한다) ·
`lake`(SSD 는 이 기계에만 있다) · `ci`(CI 안에서는 이 판이 그 판이다).
2026-10-03 까지 이 줄이 **셋 중 둘만** 들고 있었다(DECISIONS §285) — 「전부 적는다」 고 적은 자리가
또 빠뜨렸다. `tools/check_prose.py` 의 「CI밖」 이 `verify.sh` 와 글자로 견준다.

★ §5-1 CI(`.github/workflows/ci.yml`)는 `bash tools/verify.sh` 한 줄이다. 목록을 늘어놓지 않는다(DECISIONS §20).
★ §5-2 이 기계에서 `SESHAT_DATA` 가 비었거나 드라이브가 안 붙었으면 `lake` 가 실패한다 — 조용히 건너뛰지 않는다.

봉인 — `tools/verify.sh`
  점검 단계. 이 절이 열하나를 적는 동안 실물은 스물셋이 됐다.

## 6. 라이선스 대장

`seshat/licenses.py` 가 대장이다(DECISIONS §6). 대장에 13 줄이 있다.

**축이 둘이다**(DECISIONS §44) — 서빙에 쓸 수 있는가(상업)와 **출력을 학생 학습에 쓸 수 있는가**(교사).

| 값 | 상업 | 교사 |
|---|---|---|
| `yes` | 서빙 백엔드가 부를 수 있다 | 증류의 교사가 될 수 있다 |
| `no` | 비상업. 비교 실험에서만 부른다 | 출력을 학습에 못 쓴다 |
| `unknown` | 서빙에 쓰지 않는다 | 교사로 쓰지 않는다 — 모르면 못 쓴다 |

★ §6-1 **학생은 교사의 약관을 진다.** Gemma 약관은 distillation 으로 만든 모델을 Model Derivative 로 본다 —
  학생을 내놓을 때 약관 사본 · 고지 · 사용 제한을 함께 싣는다(DECISIONS §44).

★ §6-2 **쓸 수 없는 가중치가 따로 있다**(DECISIONS §9). `EXCLUDED` 는 사용 허락 지역이 이 기계가 있는 곳을
빼는 라이선스다 — 비상업과 달리 비교 실험에서도 부르지 못하고, 대장에 올려도 실패다.

| 제외 | 사유 |
|---|---|
| `tencent/hunyuan-mt*` · `tencent/hy-mt*` | Tencent HY Community License — EU · 영국 · 대한민국 제외 |

---

봉인 — `seshat/licenses.py`
  라이선스 대장. 이 절이 「비어 있다」 고 적는 동안 열셋이 들어 있었다.

## 7. 연구 트랙

**seshat 은 개발이 아니라 연구다**(DECISIONS §12). 화면은 thoth 가 맡고, 이 저장소는 번역의 뇌 — 모델 ·
데이터 · 평가 · 서빙 백엔드 — 만 든다. 가설은 `docs/hypotheses.md` 에, 남의 연구는 `docs/papers.md` 에 쌓는다.
비공개 저장소라 쌓는 지식은 공개하지 않는다. 데이터 · 가중치는 그래도 커밋하지 않는다(§2).

| 트랙 | 무엇 | 쌓이는 것 |
|---|---|---|
| R1 한 · 영 문법 대조 | **`docs/grammar.md` 가 열 축을 든다**(관형절 · 명사절 · 피동 · 부정 · 최상급 · 비교급 · 조건절 · 목적 · 등위 · 연쇄). 조사 · 높임법은 축이 아니라 지표다(`josa` · `style`) | `seshat/grammar.py` 가 문장을 축에 넣고 `tools/slice.py` 가 결과를 축으로 가른다(DECISIONS §125) |
| R2 도메인 지식 · 온톨로지 | AWS 서비스 · 기능 · API · 파라미터 · 공식 한국어 표기의 그래프 | 용어 자리표시 · 참조(RAG) · 용어 보상의 원천 |
| R3 모델 · 구조 | 2026 년 흐름 — 디코더 LLM + 추론 시점 연산 · 검증 가능한 보상의 강화학습 · 소형 번역 특화 · SSM 혼합 · 증류 · 병합 | 후보 표 · 구조 대결 |
| R4 에이전트 교사 공장 | 초안 → 문법 · 용어 검토 → 수정의 그래프. **오프라인에서만** 돈다 — 실시간은 단일 모델 | 증류용 최고 품질 데이터 |
| R5 문형 커리큘럼 · 탐침 | 5형식 템플릿 × 도메인 어휘. 번역 방식이 아니라 약점을 찌르는 탐침 · 학습 순서 · 증강 | 구문별 약점 지도 |
| R6 강화학습 · 보상 | thoth 검사기 + QE 보상 · 보상마다 반대 추 · 해킹 카나리아 | 보상 함수 · 해킹 사례 |
| R7 평가 · EDA | FLORES+ · 도메인셋 · 오류 분류(MQM 류) · 구문 슬라이스 · 지표 편향 | 이길 대상의 숫자 · 판정 근거 |

★ §7-1 **AI 는 직관이고 검증은 EDA 다.** 직관은 공짜로 대장에 오르고, 실험에 들어갈 때 검증 방법과 비용
상한이 문을 연다.

## 8. 인프라

| 층 | 지금 | 다음 |
|---|---|---|
| 앞단 | **없다.** 화면 · 확장은 thoth 다 | — |
| thoth 와의 경계 | HTTP JSON — `POST /translate` · `GET /health`(§2). thoth 워커(Lambda)가 서버 대 서버로 부른다 | 스트리밍이 필요하면 같은 경로에 SSE(thoth PLAN #38) |
| 서빙 | `serve.py` · 표준 라이브러리 · echo | 이미지 → ECR → Lambda 컨테이너(PLAN #27) · **유휴 비용 0** 이 조건이다(§13). 집의 장비로 서빙하지 않는다 — 꺼지면 thoth 번역이 죽는다 |
| 환경 | uv · ollama | 컨테이너(PLAN #26) — torch 가 들어올 때 |
| 실험 | `evaluate.py` → `runs/`(커밋 밖) · 머리줄에 재현 조건 · 견적과 상한(`--max-usd` · DECISIONS §35) · GPU 러너(§10) · **A/B 전에 A/A**(`tools/noise.py` · DECISIONS §139) · **평가 게이트**(`tools/gate.py` · `data/scoreboard.toml` · DECISIONS §131) | 비용 장부 |
| 학습 | 없다 | ② 원격 T4 · 스팟 → ③ 학습용 데스크탑 |
| 데이터 | 저장소의 `data/`(작은 정본 · 받는 도구) · SSD 레이크 `SESHAT_DATA`(raw · runs · cache — §11) | thoth 쌍(원문만) · 교사 공장 산출 · 온톨로지 2판 원천 |

★ §8-1 **HTTP 가 맞는 이유는 웹 도구라서가 아니다.** 브라우저는 thoth 워커만 부르고, seshat 을 부르는 것은
워커다. 둘이 다른 곳(Lambda 와 모델 서버)에 살기 때문에 서버 대 서버 HTTP 가 가장 단순한 경계다. 자원
설계(REST)가 아니라 함수 호출 두 개(RPC 풍 JSON)이고, 그것으로 충분하다.

## 9. AWS 온톨로지

`data/ontology/aws.jsonl` 이 도메인 지식의 원천이다(DECISIONS §13). **한 그래프를 세 곳에 쓴다** — 용어
자리표시(H-001) · 참조 번역(H-006) · 강화학습의 용어 보상(H-010).

| 종류 | 수 | 번역 | 예 |
|---|---|---|---|
| `service` | 41 | 영어로 남는다 | `Amazon Kinesis Data Streams` · 별칭 `Kinesis Data Streams` · `KDS` |
| `feature` | 24 | 영어로 남는다 · 부모가 서비스 | `AWS Glue Data Catalog` · `DynamoDB Streams` · S3 스토리지 클래스 |
| `api` | 12 | 영어로 남는다 · 부모가 서비스 | `PutRecord` · `BatchWriteItem` · `StartQueryExecution` |
| `concept` | 74 | 한국어로 옮긴다 | `partition key → 파티션 키` · `dead-letter queue → 배달 못한 편지 대기열` |
| `brand` | 1 | 영어로 남는다 | `AWS` — 서비스가 아니라 상표다 |

표기(이름 + 별칭)는 265 이고 전체에서 유일하다.

| 필드 | 뜻 |
|---|---|
| `coda` | 한국어로 읽은 끝소리 — `none`(모음) · `closed`(받침) · `rieul`(ㄹ). 자리표시 뒤 조사를 고른다. 약어 별칭은 마지막 글자의 영어 읽기로 센다(`IAM` 받침 · `KPL` ㄹ) |
| `src` | `thoth-glossary`(배포본에서 쓰는 값) · `author`(이 저장소가 적은 값) · `aws-glossary`(AWS 공식 용어집) |
| `alt_ko` | **허용 표기.** 뜻이 통하는 다른 표기 — 음차(`role` → 롤) · 의역(`operational overhead` → 운영상의 부담) · 다른 공식 표기(`queue` → 큐 · 대기열) |
| `ko_ref` | 공식 표기의 근거 — AWS 한국어 문서의 `<서비스>/<페이지>`. 있으면 대조를 마친 노드다(DECISIONS §34) |
| `bad_ko` | **관측된 오역.** 뜻이 바뀐 표기다 — `quota` → 쿼리 한도 · `visibility timeout` → 시각성 시간 초과. H-001 에서 본 것만 적는다(DECISIONS §25) |

```python
from seshat import ontology, terms
onto = ontology.load()
masked, slots = terms.mask(onto, "Load records into Amazon S3 with AWS Glue.")   # ⟦T1⟧ · ⟦T2⟧
ko, missing = terms.unmask(model_output, slots)                                  # 조사를 끝소리로 고친다
```

★ §9-1 **긴 표기가 이긴다.** `Amazon Kinesis Data Streams` 가 `Kinesis Data Streams` 보다 먼저 잡힌다.
★ §9-2 **약어는 대소문자를 지킨다.** 영어 본문의 소문자 조각(`dms`)을 서비스로 읽지 않는다.
★ §9-3 **서술격은 건드리지 않는다.** `⟦T1⟧이다` 의 `이` 는 조사가 아니다 — 조사 뒤에 한글이 이어지면 고치지 않는다.
★ §9-4 **개념은 전부 대조를 마쳤다**(DECISIONS §34). 개념 74 가 모두 `ko_ref` 를 들고,
`seshat/ontology.py::validate` 가 **`ko_ref` 없는 번역 대상을 거부한다** — 사람이 지키는 규약이 아니다.
PLAN #22 에 남은 것은 대조가 아니라 **파라미터 · 서비스 사이 관계 · DEA-C01 전범위**다.

봉인 — `data/ontology/aws.jsonl` · `seshat/ontology.py::validate`
  사전과 그 문. 수는 `docgen` 이 채우고 규칙은 이 절이 적는다.

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

★ §10-1 **손으로만 돈다.** Actions → GPU 평가 → Run workflow 에 가설 번호를 넣는다. 푸시마다 GPU 를 돌리지 않는다.
★ §10-2 **노트북이 꺼져 있으면 작업이 줄을 선다.** 켜고 `./run.sh` 를 띄우면 받아 간다.
★ §10-3 **비공개 저장소라서 안전하다.** 셀프 호스티드 러너는 공개 저장소에서 남의 PR 을 이 기계에서 돌린다.
★ §10-4 러너 폴더(`~/actions-runner`)는 저장소 밖이다. 러너 토큰을 커밋하지 않는다.

봉인 — `.github/workflows/gpu-eval.yml`
  GPU 러너가 실제로 하는 일.

## 11. 데이터 관리

**원본과 실험 결과는 SSD 레이크에 산다**(DECISIONS §21). 자리는 `.env` 의 `SESHAT_DATA` 다 — thoth 의
`/mnt/f/projects/thoth` 옆 `/mnt/f/projects/seshat`. 경로 정본은 `seshat/paths.py` 이고 **셸이 `.env` 를 이긴다.**
심링크는 쓰지 않는다.

★ §11-0 **층 정책의 정본은 `data/catalog.toml` 의 `[layers]` 블록이다**(DECISIONS §114). 이 절은 그것을
가리키기만 한다 — 표를 여기 두면 정본이 둘이 되고, 실제로 그래서 판정 파일 자리를 하루에 세 번 옮겼다.

    data/catalog.toml [layers]   정책. base · dirs · committed · regenerable · managed
    seshat/paths.py              경로 해석. 기계마다 다르다(`.env`)
    seshat/catalog.py            둘을 이름으로 묶는다 — `layers()` · `managed_tiers()` · `check_layers()`
    tools/check_catalog.py       선언 ↔ `.gitignore` · `paths.TIERS` · `lake.MANAGED`
    tools/doctor.py              선언 ↔ **이 기계의 실물**(DECISIONS §110)

```bash
uv run python tools/check_catalog.py --list     # 층과 출처를 표로
```

★ §11-2 **`.gitignore` 의 근거는 `regenerable` 이다**(파이어레인 MASTER §18-1a R2). 한 명령으로 다시 만들 수
있어서 빼는 것이지 크거나 지저분해서가 아니다. **다시 못 만드는 것을 ignore 하면 그 파일은 사실상
소실된다** — `작업대`(`runs/` · `labels/`)가 그 경계에 있고, 레이크가 `put` 으로 받아서 지킨다.

| 저장소 안에 남는 것 | 이유 |
|---|---|
| `data/ontology/` · `data/eval/seed.jsonl` | 사람이 고치는 작은 정본이다. diff 로 봐야 한다 |
| 받는 도구(`fetch_flores.py` · `fetch_awsdocs.py` · `fetch_k8s.py`) · 만드는 도구(`make_probes.py`) | 산출물은 다시 만든다 |
| `docs/papers.md` | 논문의 **읽은 결과**가 자산이다. PDF 는 cache 다 |

```bash
python3 tools/lake.py init                   # 한 번 — 층 디렉터리와 MANIFEST.tsv
python3 tools/lake.py put runs /tmp/h001/*/*.jsonl runs/*.jsonl   # 결과를 넣는다. 같은 이름 · 다른 내용은 거절
python3 tools/lake.py check                  # 해시 · 대장 밖 파일 · 가설 근거
```

★ §11-3 **결과 파일의 이름은 만드는 쪽이 유일하게 만든다**(DECISIONS §26). `evaluate` 는 `--name`, `rescore` 는 재채점한 팔의 이름을 넣는다. 작업대에서 덮이면 레이크가 볼 기회조차 없다.
★ §11-4 **넣기만 한다.** 같은 이름에 다른 내용이 오면 거절한다 — 가설의 근거가 조용히 다른 파일이 되면 판정이 거짓말을 한다.
★ §11-5 **GPU 러너가 바로 넣는다.** 러너가 이 기계라서 `gpu-eval.yml` 이 레이크에 쓴다. 러너는 `~/actions-runner/.env` 에서
  `SESHAT_DATA` 를 받는다(적고 `./run.sh` 를 다시 띄운다). 아티팩트는 사본이다.
★ §11-6 **패치는 기준 나무를 들고 온다**(DECISIONS §30). `tools/make_patch.sh` 가 머리에 `Seshat-Base-Tree` 를 넣고,
  `apply_patch.sh` 가 지금 나무와 대조한다. 봇이 GitHub 에서 main 을 움직이면 여기서 잡힌다.
★ §11-7 **INBOX 는 브라우저 다운로드 폴더다**(`SESHAT_INBOX` = thoth 의 `WIN_DOWNLOADS`). 패치가 그리로 온다.
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

★ §11-8 **쓰임이 문이다.** 평가셋(FLORES+ · 탐침)은 `train` 이 없다 — 학습에 새면 이길 대상의 숫자가 거짓말을 한다.
  라이선스가 `미확인` 인 출처는 `train` 을 달 수 없다.
★ §11-9 가중치의 라이선스는 `seshat/licenses.py` 가 정본이다(§6). 카탈로그는 자리만 든다.
★ §11-10 파이어레인에서 옮기지 않은 것 — norm 층 · 획득 게이트. 원본이 작고 손으로 모으지 않는다.
  **봉인은 옮겼다** — `tools/docseal.py` 가 그것이다(DECISIONS §211 · §281).
★ §11-11 **동일조건(SA)이 붙은 출처도 `train` 을 못 단다**(DECISIONS §276). AWS 안내서는 CC BY-SA 4.0 이고
  `미확인` 이 아니다 — 막는 까닭이 다르다. **학생을 뿌릴 수 있어야 하므로** 뿌릴 때 걸리는 조건은
  학습 원문에 못 쓴다. 2026-10-02 이 까닭이 안 적혀 있어 그 줄이 왜 막혔는지 문서로 못 읽었다.

봉인 — `data/catalog.toml` · `tools/lake.py`
  층 선언과 레이크. 쓰임의 문이 여기서 갈린다.

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

★ §12-1 판정 규칙은 `tools/patch_subjects.py` 하나다. `apply_patch.sh`(붙었으면 안 한다)와 `sweep.py`(붙었으면 지운다)가
  같은 것을 쓴다. 레이크가 안 붙었으면 작업대 결과는 **못 잼**이다 — 0건이 아니다.

봉인 — `tools/sweep.py`
  위생 검사가 보는 자리.

## 13. 서빙 예산 — 이것이 모델 크기를 정한다

**배포는 선택이다**(DECISIONS §37) — 1순위는 로컬(thoth 가 `localhost` 를 부른다), 2순위는 자리표시 캐시,
그다음이 아래의 유휴 0 클라우드다. **상시 GPU 를 쓰지 않는다**(DECISIONS §36). thoth 는 개인 도구라 하루 수십~수백 요청이고, 유휴 비용이 있는
구조를 고르면 쓰지 않는 시간에 돈이 나간다.

| 자리 | 유휴 비용 | 쓰나 |
|---|---|---|
| Lambda 컨테이너 · CPU · CTranslate2 int8 | 0 | **1순위** |
| 서버리스 GPU(Modal · RunPod 류) · 초당 과금 | 0 | 2순위 — 학생이 CPU 로 안 될 때만 |
| 상시 GPU 인스턴스 · 관리형 엔드포인트 | 있다 | 안 쓴다 |
| 집의 장비 | 0 | 안 쓴다 — 꺼지면 thoth 번역이 죽는다 |
| 캐글 · 코랩 · GitHub Actions | — | 서빙 불가(상시가 아니고 약관 밖). 학습 · 평가용이다 |

**끼울 모델의 조건**(PLAN #20 · #27 이 이 숫자를 향한다)

| 무엇 | 목표 |
|---|---|
| 크기 | int8 로 3GB 이하 — Lambda 메모리 10GB 안에서 여유 있게 |
| 속도 | CPU 한 코어 기준 **문장당 1초 이하** |
| 품질 | 같은 탐침에서 `keep` · `style` 은 1.00 유지, `term` 은 4B 교사의 0.95배 이상 |

★ §13-1 **TranslateGemma 4B 는 교사지 서빙 대상이 아니다.** 4B 를 CPU 로 서빙하면 문장당 수 초~수십 초다. 집 GPU 로
  오프라인에서 최고 품질을 대량 생성하고(PLAN #18), 그것으로 작은 학생을 만들어 학생만 띄운다.
★ §13-2 **연말 장비는 서빙 장비가 아니라 공장이다.** 학생을 만들 때까지만 쓰고, 만든 뒤에는 Lambda 가 일한다.
★ §13-3 가중치 보관은 공짜다(HuggingFace Hub 비공개 저장소). **상시 응답은 공짜가 없다** — 그래서 유휴 0 을 고른다.

## 14. 도구

**명령의 정본은 이 절 하나다**(DECISIONS §199). 최상위 `README.md` 는 문이고 목록을 안 든다 —
두 곳에 적었더니 2026-09-29 기준 여덟 개가 한쪽에만, 다섯 개가 다른 쪽에만 있었다.
`tools/` 의 파일은 **빠짐없이 이 표에 있다**(`tools/check_docs.py::check_tools_listed`).

**돌리기 전에 · 기계를 본다**

| 도구 | 무엇 | 언제 |
|---|---|---|
| `tools/verify.sh` | 점검 전부. 실패해도 끝까지 돌고 표로 보인다 — **점검 목록의 정본** | 밀기 전에 늘 |
| `tools/ci_status.py` | **CI 가 지금 커밋을 초록으로 봤는가** — 이 기계의 초록은 CI 의 초록이 아니다 | 밀고 나서 |
| `tools/hookcheck.sh` | 커밋 훅이 **도는가** — 있는지가 아니라 도는지를 실행으로 잰다 | `verify` 안에서 |
| `tools/doctor.py` | 이 기계 — 레이크 · 가중치 · 작업대 · `.env` · 디스크 | 기계가 이상할 때 |
| `tools/sweep.py [--fix]` | WSL 위생 — seshat 이 저장소 밖에 남긴 흔적만 | 이따금 |

**패치를 주고받는다**

| 도구 | 무엇 | 언제 |
|---|---|---|
| `tools/apply_patch.sh` | INBOX 의 **안 붙은** 패치를 번호 순서로 붙인다 | 패치를 받을 때마다 |
| `tools/make_patch.sh N 자리` | 패치를 만든다 — **기준 나무**를 패치가 들고 간다 | 보내는 쪽에서 |
| `tools/patch_subjects.py` | 패치의 커밋 제목과 붙음 · 겹침 판정 | 위 둘이 부른다 |
| `tools/deps.sh --merge` | 의존성 봇 — 초록만 합치고 가지를 지운다(thoth 사본) | Actions 만 |

**대장을 지킨다** — 규약마다 강제자가 있다(§0)

| 도구 | 무엇 |
|---|---|
| `tools/docgen.py` | **문서가 드는 수를 도구가 채운다** — 지금은 §15 의 합 하나. `--fix` 가 갈아 넣고 관문은 대조만 한다. **커밋이 흔드는 수는 축이 못 된다**(DECISIONS §237 · §238) |
| `tools/check_numbers.py` | **결과 문서가 든 수에 근거가 있나** — `related.md` 의 수를 DECISIONS · 가설 대장 · MASTER · 기록판에서 찾는다(DECISIONS §235) |
| `tools/check_rules.py` | **MASTER 의 ★ 규칙 번호**(`§11-3`) — 유일 · 오름차순 · 가리킨 번호가 실재하나(DECISIONS §230) |
| `tools/check_size.py` | **파일이 배치마다 조금씩 늘지 않나** — 상한 600 · 넘는 여섯은 예외표에 수로 적는다. **늘어도 줄어도 운다**(파이어레인 `sizecheck.py` · DECISIONS §286) |
| `tools/check_prose.py` | **문서명 없는 `§N` 이 풀리나** · 빈 줄 뒤에 홀로 선 표 줄 · `PLAN #N` 없는 빈 약속(DECISIONS §282) |
| `tools/check_speech.py` | **결정 기록이 사람 말을 그대로 담았나** — 인용 **덩어리**를 꺼내 **말투**(해체 종결 · 해체 의문 · 채팅 기호)로 가른다. **욕설 사전은 주축이 아니라 받침**이다 : 실측으로 말투가 15 중 14 를 물고 사전은 **1**(`?` 없는 해체 의문)을 더 문다 — 사전을 주축에 두면 **1 만 잡는다**(DECISIONS §308). **발화 동사로는 안 잡는다** — 하토르 실측 50 중 25 가 오탐이다. 탈출구는 `<!--말-ok-->`(발화가 자료인 자리). **소급 바닥 없음 — 전수 0** |
| `tools/check_docs.py` | 문서 ↔ 문서 — 문체 · 절 · PLAN 표 · 참조 · DECISIONS · **문서 지도** · **도구 목록**. `--fix-index` 가 DECISIONS 색인을 다시 쓴다 |
| `tools/doc_fsck.py` | 문서 ↔ 실물 — 경로 · 테스트 · 아무도 안 부르는 도구 |
| `tools/check_hypotheses.py` | 가설 대장 — 실험의 문 |
| `tools/check_ontology.py` | 온톨로지 — 표기 유일 · 부모 · 끝소리 |
| `tools/plan_closed.py` | **닫힌 PLAN 행을 이력에서 되살려 보여준다** — 번호 · 마지막 본문 · 사라진 판 · 그 번호를 든 절(DECISIONS §222) |
| `tools/docseal.py` | **절과 그 절이 짚은 코드의 정합 도장** — 찍은 뒤로 바뀌었으면 「다시 봐야 한다」(`audit` · `stamp --only N` · DECISIONS §211) |
| `tools/check_crashes.py` | **도구가 역추적으로 죽지 않나** — `__main__` 이 맨몸이면 뜻밖의 예외가 말 없이 나간다. 2026-09-30 맨몸 26 에서 라쳇을 걸었다(DECISIONS §232) |
| `tools/check_secrets.py` | **비밀값 꼴이 추적된 파일에 들어갔나**(DECISIONS §304). 접두사가 분명한 꼴 여덟과 대입 꼴만 본다 — 엔트로피는 **안 본다**(해시와 지문이 전부 운다). **값은 안 찍는다** — 찍으면 로그가 유출이 된다. 역사는 `--history` 로 손으로 본다 |
| `tools/check_scope.py` | **관문이 제 밖과 생사를 선언하나** — 머리말이 「안 보는 것」 을 적고 `_canary` 로 판별식이 사는지 스스로 묻나. 2026-09-30 관문 14 중 9 자리를 갚았다(DECISIONS §239) |
| `tools/check_claims.py` | **강제자라고 선언한 함수가 제 밖을 적었나** — DECISIONS 의 「강제자」 줄이 든 함수를 본다. `check_scope` 는 **관문만** 보고 이쪽은 **선언한 전부**를 본다. 2026-10-01 서른일곱 중 열일곱이 안 적고 있었고 열을 갚았다(DECISIONS §267) |
| `tools/mutate.py` | **몸통을 지워도 시험이 통과하나** — 함수 몸통을 꼴에 맞는 중립값 하나로 바꾸고 돌린다. **사슬 안이다**(DECISIONS §287 · §307) — `verify.sh` 가 `--only 'tools/check_*.py' --only 'seshat/*.py'` 로 **208자리**(107 + 101)를 돈다. **짝 시험으로 좁히되 믿지 않는다** — 짝이 조용하면 전부로 다시 센다(99자리 때 26이 그랬다). **종료코드는 1만 「울었다」 다** — `!= 0` 으로 보던 때 수집 실패(2)를 전부 「물었다」 로 세어 **거짓 초록 스물여섯**이 났다. 톱니 셋 : **장부에 없는 자리 0** · 못 잴 자리 47 천장 · **잴 자리 458 바닥**(양방향). **장부가 비었다** — 2026-10-05 에 아홉을 다 갚았다(`main` 넷 · 술어 셋 · `견준다` · `_canary` — DECISIONS §290). `tools/` 의 나머지 250자리(개발 유틸)는 손으로 돈다 — **시간을 안 쟀다**(DECISIONS §307) |
| `tools/check_deadchecks.py` | **검사가 죽어 있지 않나** — 무검증 시험 · 건너뛴 시험 · 삼킨 예외 · 빈 그물. `check_dead` 와 **다른 물음**이다(그쪽은 죽은 **이름**). 2026-10-01 스물셋에서 라쳇을 걸고 열을 갚았다(DECISIONS §255) |
| `tools/check_dead.py` | **아무도 안 부르는 최상위 이름이 있나** — 죽은 코드는 현행으로 읽혀서 고쳐진다. 2026-09-30 373 중 둘을 지우고 장부를 비웠다(DECISIONS §240) |
| `tools/check_ways.py` | **막는 자리마다 넘는 길이 있나** — **길 없는 막음을 막는다** — 2026-09-29 서른 곳을 다 갚아 장부가 비었다(DECISIONS §210 · §213) |
| `tools/check_catalog.py` | 데이터 카탈로그 — 칸 · 쓰임 · `data/` 의 카탈로그 밖 파일(§11) |
| `tools/check_model_licenses.py` | 코드가 부르는 가중치가 대장에 있고 상업 가부가 적혀 있나 |
| `tools/lake.py` | SSD 레이크 — 넣기만 한다 · 대장 밖을 짚는다 · `ls` 로 찾는다 |
| `tools/dupcheck.py` | **같은 것이 몇 벌인가** — 구조가 같은 함수를 센다 |

**셋을 만든다** — 무엇으로 잴 것인가

| 도구 | 무엇 |
|---|---|
| `tools/fetch_awsdocs.py` | AWS 공식 문서(CC BY-SA)에서 도메인 셋을 만든다 — 정답 없이 · `--exclude` 로 떼어둔다 |
| `tools/fetch_k8s.py` | **증류용 영어 원문을 뽑는다** — `kubernetes/website` 의 영어 문서(**CC BY 4.0 · 동일조건 없음**)에서 문장을 떠 온다. AWS 안내서(CC BY-SA)와 갈리는 점이 그것이고, **평가셋과 코퍼스가 달라 오염이 없다**. 마크다운 읽기는 `fetch_awsdocs` 의 것을 부른다(DECISIONS §276) |
| `tools/fetch_flores.py` | FLORES+ 영→한을 셋 모양으로 받는다 |
| `tools/make_probes.py` | 문형 탐침 — 템플릿 × 온톨로지 어휘로 통제된 문장을 만든다 |
| `tools/mine_terms.py` | 셋에 자주 나오는데 **사전이 모르는** 말을 캔다 — 점수를 내는 셋은 거절한다 |
| `tools/noise.py` | 같은 팔을 여러 판 돌려 **흔들림**을 잰다 |
| `tools/distill.py` | **증류셋을 뽑는다** — `gemba ≥ 문턱` 과 `escape` 판정 없음을 **AND** 로 건다. 머리줄이 **어느 자로 걸렀는지**를 든다. 한 자만 걸면 그 자의 맹점이 그대로 들어온다(DECISIONS §279) |

**잰다 · 판정한다**

| 도구 | 무엇 |
|---|---|
| `python -m seshat.evaluate` | 한 판. 가설이 **실험** 상태가 아니면 문이 막는다 · 끊기면 `--resume` |
| `tools/rescore.py` | 이미 있는 결과를 **GPU 없이** 다시 채점한다 |
| `tools/bootstrap.py A B --set S` | **차이가 잡음인가** — 짝지은 재표집이 크기와 확실함을 따로 준다 |
| `tools/compare_runs.py` | 두 결과를 줄 단위로 대조 — 판정 전의 EDA |
| `tools/term_diff.py` | **개념 단위** 대조 — 누가 어느 용어에서 이겼나 |
| `tools/slice.py` | 결과를 **문법 축으로 갈라** 다시 센다 |
| `tools/show_misses.py` | 숫자 뒤의 줄을 본다 — 어느 줄이 어떻게 틀렸나 |
| `tools/style_na.py` | **합쇼체가 설 수 없는 줄**의 후보 — 판정은 사람이 한다 |
| `tools/gemba.py` | **transformers 없이 도는 자** — ollama 로 로컬 LLM(`qwen3:8b` · 팔들과 집안이 다르다)에게 0~100 을 묻는다. `--표` 로 사람이 본 자리만 잰다. 이기면 `qe.py` 의 의존성이 통째로 빠진다(DECISIONS §251 · §253 · H-086) |
| `tools/escape.py 판 --셋 탐침` | **출력이 번역이기는 한가** — 빈 줄 · 원문 그대로 · 되풀이 · 비서 응답 · 한글 없음. **뜻은 안 본다**(그쪽은 `gemba`). 2026-10-02 교사가 명령문을 **지시로 읽고 수행**했는데 `gemba` 는 그중 셋에 90점 이상을 줬다 — 영어를 그대로 돌려준 줄에 100점이다(DECISIONS §279) |
| `tools/qe.py` | **신경망 QE 자로 줄마다 점수를 낸다**(MetricX-24 · Apache-2.0). 오류 점수를 **뒤집어** 내고 조건을 머리줄에 싣는다. 규칙 지표 여덟에 자가 없어서 들였다(DECISIONS §245 · §246) |
| `tools/labels.py` | 눈가림 판정 — 표를 만들고 · 읽고 · 쌍마다 일치를 재고 · **팔 사이 격차에 구간을 붙인다**(`gap`) · **자가 사람과 같은 순서로 줄을 세우는지 잰다**(`corr` · H-084) · 규칙 지표를 자로 내놓는다(`rule`) |
| `tools/gate.py` | 회귀를 막는 문 · 기록판과 선을 **판에서** 박는다(손으로 안 고친다) · **주 셋을 갈아끼운다**(`--move-set`) · **팔을 갈아끼운다**(`--swap-arm`) — 둘 다 까닭을 적는다(DECISIONS §203 · §220) |

**바깥을 본다**

| 도구 | 무엇 |
|---|---|
| `tools/watch_papers.py` | 주 1회 신규 논문 · 모델을 훑어 `docs/papers.md` 에 후보를 붙인다 |

## 15. 어디까지 왔나

**목표는 thoth 의 번역 자리를 이 저장소의 모델이 넘겨받는 것이다**(§1). 그 하나를 다섯 단계로 나누고
단계마다 비중을 박는다. **비중은 여기 한 번 적고 안 흔든다** — 그래야 달마다의 수가 견줘진다.

| 단계 | 비중 | 지금 | 근거 |
|---|---|---|---|
| ① 재는 체계 — 무엇으로 나은지를 가리나 | 20% | **80%** | 지표 열셋 · 짝지은 부트스트랩(§180) · 떼어둔 셋 · 가설 대장이 문을 지킨다. 2026-09-30 **눈가림 외부 LLM 판정에 구간이 붙었고**(`tools/labels.py gap`) 외부 판정자 넷으로 돌렸다(H-081). **그리고 그 판정이 규칙 지표 여덟이 배포본 상대로 순위를 뒤집는다는 것을 보였다**(DECISIONS §229) — **95% 는 과장이었다.** **2026-10-01 그 자가 섰다** — `gemba`(qwen3:8b · GEMBA 꼴)가 떼어둔 60줄 · 외부 판정자 넷에서 ρ **+0.5692** 이고 `term_off` 와의 차 **+0.4865** 로 갈린다(H-085 · DECISIONS §262). **남은 것은 그 자가 보상으로 쓰일 때 밀어도 안 무너지는가**이고(PLAN #19) 그것은 아직 안 쟀다 |
| ② 기준선 · 후보 · 처치 | 20% | 85% | AWS Translate · Nova Lite · TranslateGemma 4B · Qwen3 · Gemma3 4B/12B 를 쟀다. **처치를 두른 4B 가 배포본과 12B 를 `term_off` 에서 이기고, 뜻에서는 둘 다에게 진다**(`docs/related.md` §3 · §229). 잰 일은 끝났고 **무엇을 산 처치인지가 달라졌다.** 남은 것은 MADLAD-400(PLAN #5) |
| ③ 학습 데이터 | 20% | 5% | 원문은 **k8s 문서 11,503 문장**이다(`data/train/k001.jsonl` · CC BY 4.0 · DECISIONS §276). AWS 안내서 59,145 문장은 **동일조건(SA) 때문에 학습에서 뺐다** — 평가셋으로만 쓴다. **정답이 없다** — thoth 쌍은 2객체 9,880바이트고(§120) 교사 가부가 GPT · 제미나이 출력을 막는다 |
| ④ 학습 | 25% | 0% | `seshat/` 에 학습 코드가 한 줄도 없다. 장비가 아니라 ③ 이 막고 있다 |
| ⑤ 서빙 | 15% | 10% | 계약(§2) · 예산과 크기 조건(§13)은 섰다. 서버는 `echo` 백엔드뿐이다 |

**합 35%**(2026-09-30). 위 표를 곱해서 더하고 **내림한** 값이다 — 참값은 35.5 다. `tools/docgen.py` 가 채우고 `verify` 가 대조한다(DECISIONS §237). **반올림이 아니라 내림인 까닭은 진행률이 과장되는 쪽으로 틀리면 안 되기 때문이다.**

★ §15-1 **38% 에서 내려왔다.** 일이 뒤로 간 것이 아니라 **①이 과장이었다는 것을 알았다** — 외부 판정자 넷이 「규칙 지표가 배포본 상대로 순위를 뒤집는다」 를 보여 줬다(§229). **내려간 수가 올라간 수보다 정직하다** — 진행률이 한 번도 안 내려가는 문서는 진행률이 아니다.

★ §15-2 **자체 가중치는 0% 다.** 지금 이기고 있는 것은 **남의 모델 + 이 저장소의 처치**이고, 그것이
  ② 의 85% 다. 그 둘을 한 수로 합치면 진행률이 거짓말을 한다.
★ §15-3 **③ 이 ④ 를 막고 ④ 가 나머지를 막는다.** 비중이 가장 큰 칸이 0 인 까닭은 시간이 아니라 순서다.
