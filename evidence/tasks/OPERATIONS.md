# Local LiteLLM stack operations

## Start

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

## Daily defaults

`context_window=40960`, `sift_target=32768`, `output_reserve=4096`, `draft_tokens=4`.

The adaptive Sift policy anchors at `sift_target=32768`. That target is part of the input budget, never added to it; a further 256 tokens are held for decoder headroom. Short requests within the anchor pass unchanged. Larger histories use `ceil(native_raw_tokens / 8)`, bounded to 24576..36608 when all 4096 output tokens are reserved. 36608 is a ceiling, not a required request size.

A readiness response alone proves process readiness, not productive work.
