# local-inference operations

## Start
```powershell
docker compose up -d --build
```

## Check both ports
```powershell
curl.exe http://127.0.0.1:8090/health/readiness
curl.exe http://127.0.0.1:8091/health
```

## Acceptance
```powershell
python scripts/claude_acceptance.py
```

## Sift logs
```powershell
docker compose logs --no-color gateway > tmp/sift-runtime.log
```

## Stop this project only
```powershell
docker compose down
```

## Budget policy

The daily default is adaptive. The gateway loads:

```
context_window=40960
sift_target=32768
output_reserve=4096
draft_tokens=4
```

`sift_target=32768` is the adaptive policy anchor, not a fixed forwarded budget. Requests at or below it pass unchanged when they also fit the loaded window. Larger histories use `ceil(native_raw_tokens / 8)`, bounded to `context_window - requested_output - 256`. With all 4096 output tokens reserved, the daily input budget ranges 24576..36608. The 36608 figure is a ceiling, not a required request size. The Sift target is part of the input budget, never added to it; a further 256 tokens are held for decoder headroom.

## Why health is not productivity evidence

`/health/readiness` proves process readiness only. It does not prove the model generates correct, useful output. Use `claude_acceptance.py` for productive-work evidence.
