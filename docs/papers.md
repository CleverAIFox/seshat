# 논문 대장

**남이 이미 한 학습을 파싱한다**(DECISIONS §11). 한 줄에 한 편 — 무엇을 · 어떤 데이터로 ·
몇 점 올렸고 · 이 저장소에 무엇을 가져오는가. 읽은 날을 적는다. 수치는 논문의 주장이고 여기서 재지 않았다.

| 논문 | 무엇을 했나 | 주장한 결과 | 가져올 것 | 행 | 읽은 날 |
|---|---|---|---|---|---|
| Kocmi 외, *Preliminary Ranking of WMT25 General MT Systems* (arXiv 2508.14909) | WMT25 자동 지표 예비 순위 | 영→한 1위 Shy-hunyuan-MT(7B), Gemini 2.5 Pro · GPT-4.1 이 뒤, 익명 상용 ONLINE-B 7위권. Gemma-3-12B 9위 · TowerPlus-9B 9.8위 · Qwen2.5-7B 25위 | 목표가 무모하지 않다는 근거. 영→한 순위표의 상대 위치 | #12 · #5 | 2026-09-22 |
| *MT-R1-Zero* (arXiv 2504.10160 · EMNLP 2025 Findings) | SFT 없이 R1-Zero 식 강화학습. 규칙 + 지표 혼합 보상 | 3B 가 TowerInstruct-7B 를 WMT24 영→중에서 약 1.26 넘음. 7B 가 GPT-4o · Claude-3.5 급 | 보상 설계 — 우리 보상은 thoth 검사기 + QE | #19 | 2026-09-22 |
| *How Effective are State Space Models for Machine Translation?* (arXiv 2407.05489) | Mamba 대 트랜스포머 번역 | 문장 · 문단 단위에서 Mamba 가 경쟁력. 어텐션을 섞으면 품질 · 긴 입력 견고성 · **고유명사 복원**이 오른다 | 학생 구조 대결의 가설 | #20 | 2026-09-22 |
| Kim & Rush, *Sequence-Level Knowledge Distillation* (arXiv 1606.07947) | 교사 출력으로 학생을 학습 | 작은 학생이 교사에 가깝다 | 교사 증류의 기본형 | #18 | 2026-09-22 |
| Google, *TranslateGemma Technical Report* (arXiv 2601.09012) | Gemma 3 기반 번역 전용. SFT 4.3B 토큰 + 강화학습 10.2M 토큰 · 55개 언어 · 입력 2K 토큰 | 모델 카드 기준. 한국어 수치는 미확인 | 후보 1호 · SFT → RL 두 단계의 데이터 규모 | #5 · #7 | 2026-09-22 |
| WMT25 Terminology Translation Task (statmt.org/wmt25/terminology) | 용어 제약 번역 공유 과제 | 참가 보고서 미독 | 용어 자리표시 · 제약 디코딩의 비교 대상 | H-015 | 2026-09-22 |
| Finkelstein 외, *MBR and QE Finetuning* (ICLR 2024) | MBR · QE 재정렬 결과를 학습 데이터로 증류 | 비싼 디코딩의 품질을 학습으로 옮긴다 | #14 의 다음 단계 — 재정렬 결과를 #18 데이터로 | #14 · #18 | 2026-09-22 |

## 읽을 것

- Hunyuan-MT · HY-MT1.5 기술 보고서 — **가중치는 쓸 수 없다**(DECISIONS §9). 방법 · 데이터 구성 · 강화학습 단계를 읽는다
- Tower+ · ALMA / X-ALMA(CPO) · WMT25 General Findings(aclanthology 2025.wmt-1.22) 의 영→한 사람 평가
- WMT25 Model Compression Findings(aclanthology 2025.wmt-1.25) — 서빙(#8)의 양자화 · 가지치기
