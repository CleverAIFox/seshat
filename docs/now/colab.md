# 빌린 GPU — Colab 에 ollama 를 올리고 터널로 쓴다

**이 기계의 카드는 6GB 다**(MASTER §4). `gemma3:12b` Q4 는 **8GB** 라 안 올라가고, 억지로 돌리면
**윈도우가 뻗는다**(DECISIONS §84 — 두 번 뻗었다). `backends.들어가나` 가 그래서 막는다(§201).

★ **저장소는 한 줄도 안 고친다.** 바꾸는 것은 `OLLAMA_URL` 하나다 — 번역 호출과 GPU 적재 기록
  양쪽에 이미 있다(§84).
★ **왜 이 문서가 있나.** §84 가 이 절차를 **산문으로만** 적어 뒀고, §201 이 사흘 뒤에 같은 일을
  다시 겪으며 **「적었다는 사실이 막았다는 착각을 만든다」** 고 적었다. 붙여넣을 수 있는 글이
  아니면 다음에 또 더듬는다.
★ **잰 값**(§84 · 2026-09-26) — 12B 가 100% GPU 에 올라가고 **줄당 2.3~3.8초.** 200줄에 13분.

| 줄 | 걸리는 시간 |
|---:|---|
| 500 | 20~30분 |
| 2,000 | 1.3~2.1시간 |
| 11,503 | **7~12시간** — 무료 Colab 은 끊긴다. `--resume` 으로 나눠 돈다 |

## ① Colab 쪽 — 셀 하나에 붙여넣는다

런타임 유형을 **T4 GPU** 로 바꾼 뒤:

```python
!curl -fsSL https://ollama.com/install.sh | sh
!nohup ollama serve > /tmp/ollama.log 2>&1 &
import time; time.sleep(5)
!ollama pull gemma3:12b
!wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared
!nohup cloudflared tunnel --url http://localhost:11434 > /tmp/tunnel.log 2>&1 &
import time; time.sleep(12)
!grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/tunnel.log | head -1
```

마지막 줄이 찍는 **주소가 `OLLAMA_URL`** 이다.

## ② 노트북 쪽 — 그 주소를 들고 돈다

```bash
cd ~/projects/seshat
export OLLAMA_URL=https://<위에서 받은 주소>
uv run python -m seshat.evaluate \
  --backend gemma3-12b+ph+retry+endings+terms \
  --set data/train/k001.jsonl --name H-088-teacher-k001 --resume
```

★ **`--resume` 을 항상 쓴다.** 터널이 끊기거나 Colab 이 자면 **그때까지가 남는다.**
  다시 돌릴 때 같은 `--name` 이면 이어서 간다.
★ **빌린 장비는 카드 검사를 안 받는다** — `들어가나` 가 `OLLAMA_URL` 이 로컬이 아니면 비켜선다(§201).
  그 설계 덕분에 이 길이 막히지 않는다.

## ③ 끝나면

```python
# Colab : 런타임 → 런타임 연결 해제 및 삭제
```

★ **반드시 끈다.** 터널이 열려 있는 동안은 **주소를 아는 쪽이 그 ollama 를 쓴다**(§84).

## 밖

★ **학생 훈련은 이 문서가 안 다룬다.** 4B QLoRA 는 Colab 에서 **직접** 도는 일이고 터널이 필요 없다.
★ **맥북이 오면 이 길이 필요 없을 수 있다.** 통합 메모리 16GB 이상이면 `gemma3:12b` 가 그냥 로컬에서
  돈다 — 그때는 `SESHAT_VRAM_GB` 를 그 기계의 값으로 두면 `들어가나` 가 비켜선다.
