# Standalone Local LiteLLM Operations

## Start the stack

```powershell
docker compose up -d --build
```

## Check both ports

```powershell
curl.exe http://127.0.0.1:8090/health/readiness
curl.exe http://127.0.0.1:8091/health
```

## Run acceptance

```powershell
python scripts/claude_acceptance.py
```

## Inspect gateway Sift logs

```powershell
docker compose logs --no-color gateway > tmp/sift-runtime.log
```

## Stop only this compose project

```powershell
docker compose down
```

## Compaction limit and output reserve

Daily defaults: context_window=40960, sift_target=32768, output_reserve=4096, draft_tokens=4. The adaptive Sift policy uses 32768 as its anchor, not a fixed forwarded budget; the target is part of the input budget, never added to it. With all 4096 output tokens reserved, the adaptive range is 24576..36608. A further 256 tokens are held for decoder headroom. Short requests pass unchanged; 36608 is a ceiling, not a required request size. A readiness response alone proves process readiness, not productive work.
