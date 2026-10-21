# 빌린 GPU — Colab 에 ollama 를 올리고 터널로 쓴다

**이 기계의 카드는 6GB 다**(MASTER §4). `gemma3:12b` Q4 는 **7.6GB**(MASTER §4 가 정본이다)
라 안 올라가고, 억지로 돌리면
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
!apt-get -qq install -y zstd
!curl -fsSL https://ollama.com/install.sh | sh
!OLLAMA_HOST=0.0.0.0:11434 OLLAMA_ORIGINS='*' nohup ollama serve > /tmp/ollama.log 2>&1 &
import time; time.sleep(6)
!ollama pull gemma3:12b
!nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
!wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared
!nohup cloudflared tunnel --url http://localhost:11434 > /tmp/tunnel.log 2>&1 &
import time; time.sleep(12)
주소 = !grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/tunnel.log | head -1
주소 = 주소[0]
print(주소)
print("---- **터널로 들어오는 것처럼** 물어본다")
!curl -s -H "Host: {주소[8:]}" http://localhost:11434/api/tags | head -c 120
```

★ **`zstd` 를 먼저 깐다**(2026-10-01). 안 깔면 설치본이 **「This version requires zstd for extraction」**
  로 죽고, 그 뒤 `ollama` 는 `command not found` 가 된다. **그런데 터널은 그대로 열린다** —
  **주소가 떴다고 뒤에 모델이 있는 것이 아니다.**
★ **`OLLAMA_HOST=0.0.0.0` 과 `OLLAMA_ORIGINS='*'` 가 없으면 터널 너머에서 403 이 온다**
  (2026-10-01). ollama 는 `Host` 가 `localhost` 가 아니면 **외부 출처로 보고 막는다** —
  터널을 거치면 `Host` 가 `…trycloudflare.com` 이 되고, 그래서 거절한다. **ollama 안에서는 멀쩡하다.**
★ **확인을 `Host` 를 바꿔서 한다.** 그냥 `curl localhost` 로 물으면 **403 이 안 난다** —
  2026-10-01 그렇게 확인하고 「됐다」 고 적었다가 사람이 403 을 맞았다. §271 · §275 의 그 병이다:
  **밟아 본 자리가 실제로 지나갈 자리가 아니었다.**
★ **`gemma3:12b` 가 보여야 다음으로 간다.** 이 한 줄이 「터널은 섰는데 빈 집」 을 막는다.
★ **GPU 를 같이 찍는다** — `Tesla T4` 가 안 나오면 런타임 유형이 GPU 가 아니다. 그러면
  `ollama ps` 의 `PROCESSOR` 가 `100% CPU` 가 되고 **줄당 몇 분**이 된다(§201 의 그 자리).

마지막 줄이 찍는 **주소가 `OLLAMA_URL`** 이다.

## ①-2 노트북 쪽 — **밖에서** 한 번 확인한다

```bash
curl -s https://받은-주소.trycloudflare.com/api/tags | head -c 120
```

★ **모델 목록이 나와야 한다.** `403` 이면 ollama 를 `OLLAMA_ORIGINS='*'` 로 다시 올린다.
★ **이 한 줄이 2~3시간을 아낀다** — 안 하면 던지고 90초 뒤에 403 을 본다.

## ② 노트북 쪽 — 그 주소를 들고 돈다

```bash
cd ~/projects/seshat
export OLLAMA_URL=https://받은-주소.trycloudflare.com      # ← 꺾쇠 없이 **실제 주소**를 넣는다
uv run python -m seshat.evaluate \
  --backend gemma3-12b+ph+retry+endings+terms \
  --set data/train/k001.jsonl --name H-088-teacher-k001 \
  --hypothesis H-088 --resume
```

★ **`--hypothesis` 가 없으면 안 잰다**(DECISIONS §12). 그리고 그 가설은 **「실험」 상태여야** 한다 —
  「제안」 이면 문이 막고 **지금 실험 상태인 것들을 찍어 준다**(§174).
★ **꺾쇠(`<…>`)를 쓰지 않는다.** 2026-10-01 안내에 `<위 주소>` 라고 적었다가 사람이 그대로 붙여넣어
  `bash: syntax error` 가 났다. **붙여넣을 글에는 붙여넣으면 안 되는 글자를 안 쓴다.**

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
