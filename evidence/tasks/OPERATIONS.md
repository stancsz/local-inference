# Local LiteLLM operations

## Start

```powershell
docker compose up -d --build
```

## Check ports

```powershell
curl.exe http://127.0.0.1:8090/health/readiness
curl.exe http://127.0.0.1:8091/health
```

8090 is the LiteLLM gateway; 8091 is llama.cpp diagnostics.

## Acceptance

```powershell
python scripts/claude_acceptance.py
```

## Gateway Sift logs

```powershell
docker compose logs --no-color gateway > tmp/sift-runtime.log
```

## Stop

```powershell
docker compose down
```

This stops only the `local-inference` project.

## Budget

Daily defaults in `compose.yaml`:

```
context_window=40960
sift_target=32768
output_reserve=4096
draft_tokens=4
```

The 32,768-token Sift target is part of the input budget, never added to it. A further 256 tokens are held for decoder headroom.

## Why health is not productivity evidence

A readiness response alone proves process readiness, not productive work.