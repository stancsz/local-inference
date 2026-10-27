"""Observation-only capture of compacted historical excerpts in test requests."""
import gzip
import hashlib
import json
from pathlib import Path

from stress.cli_acceptance import inject_history, historical_gold_retained, RouteCounter


def capture_snapshot(directory, index, messages, entry):
    if directory is None:
        return
    excerpts, matches = [], []
    for position, message in enumerate(messages):
        content = message.get('content')
        if isinstance(content, list):
            content = '\n'.join(block.get('text', '') for block in content if isinstance(block, dict) and block.get('type') in {'text', 'input_text'})
        if not isinstance(content, str) or message.get('role') in {'system', 'developer'}:
            continue
        is_excerpt = content.startswith('Earlier conversation, lossily excerpted')
        if is_excerpt:
            excerpts.append({'position': position, 'role': message.get('role'), 'content': content})
        lines = [line for line in content.splitlines() if 'acceptance_delay_seconds=37' in line]
        if lines:
            matches.append({'position': position, 'role': message.get('role'), 'is_excerpt': is_excerpt, 'lines': lines})
    snapshot = {'request_index': index, 'gold_retained': entry['gold_retained'],
                'historical_excerpt_messages': excerpts, 'needle_matches': matches,
                'scope': 'Exact first-stage historical excerpts; protected instruction prefixes and auth headers are excluded. Not the full provider wire payload.'}
    raw = json.dumps(snapshot, ensure_ascii=False).encode('utf-8')
    path = Path(directory) / f'{index:05}.json.gz'
    path.write_bytes(gzip.compress(raw, mtime=0))
    entry['excerpt_capture'] = path.name
    entry['excerpt_capture_raw_sha256'] = hashlib.sha256(raw).hexdigest()


def make_app(upstream: str, key: str, model: str, target: int, audits: list[dict], capture_dir=None):
    if capture_dir is not None:
        Path(capture_dir).mkdir(parents=True, exist_ok=False)
    import httpx
    from fastapi import FastAPI, Request
    from fastapi.responses import StreamingResponse
    from sift.litellm_proxy import SiftLiteLLMHook
    app = FastAPI()
    hook = SiftLiteLLMHook({model: target})

    @app.get("/v1/models")
    async def models():
        return {"object": "list", "data": [{"id": model, "object": "model"}]}

    @app.post("/v1/{endpoint:path}")
    async def forward(endpoint: str, request: Request):
        from fastapi import HTTPException
        if endpoint not in {"messages", "chat/completions", "responses"}:
            raise HTTPException(404, "Unsupported acceptance protocol")
        original = await request.json()
        data = inject_history(original)
        data["model"] = model
        call_type = {"messages": "anthropic_messages", "responses": "aresponses"}.get(endpoint, "acompletion")
        original_messages = original.get("messages", original.get("input", []))
        if isinstance(original_messages, str):
            original_messages = [{"role": "user", "content": original_messages}]
        shapes = [{"role": m.get("role", m.get("type")), "keys": sorted(m),
                   **({"type": m["type"]} if "type" in m else {})} for m in original_messages]
        try:
            compacted = await hook._compact(RouteCounter(), data, call_type=call_type, target=target)
        except HTTPException as error:
            audits.append({"protocol": call_type, "input_shapes": shapes,
                           "tool_types":[tool.get('type') for tool in original.get('tools',[])],
                           "sift_error": (error.headers or {}).get("x-sift-error-code"),
                           "status": error.status_code})
            raise
        audit = compacted.pop("metadata", {}).get("sift", {})
        # LiteLLM may choose a different internal metadata bucket.
        audit = compacted.pop("litellm_metadata", {}).get("sift", audit)
        output_messages = compacted.get("messages", compacted.get("input", []))
        # The default core's excerpt indexes are relative to the eligible
        # historical span, after the immutable instruction prefix. Our
        # injected archive is always the first message in that span.
        history_index = 0
        entry = {**audit, "protocol": call_type, "input_shapes": shapes,
                       "gold_retained": historical_gold_retained(output_messages, history_index),
                       "tool_results": sum(m.get("role") == "tool" or m.get("type") in {"function_call_output", "custom_tool_call_output"} or any(
                           isinstance(b, dict) and b.get("type") == "tool_result"
                           for b in (m.get("content") if isinstance(m.get("content"), list) else [])
                       ) for m in original_messages)}
        audits.append(entry)
        try:
            capture_snapshot(capture_dir, len(audits)-1, output_messages, entry)
        except OSError as error:
            entry["excerpt_capture_error"]=type(error).__name__
        headers = {"Authorization": f"Bearer {key}", "x-api-key": key,
                   "anthropic-version": request.headers.get("anthropic-version", "2023-06-01")}
        client = httpx.AsyncClient(timeout=httpx.Timeout(90, connect=10), follow_redirects=False)
        try:
            response = await client.send(client.build_request(
                "POST", upstream.rstrip("/") + "/" + endpoint, json=compacted, headers=headers,
            ), stream=True)
        except BaseException:
            await client.aclose()
            raise
        entry["upstream_status"] = response.status_code

        async def body():
            try:
                async for chunk in response.aiter_raw():
                    yield chunk
            finally:
                await response.aclose()
                await client.aclose()

        return StreamingResponse(body(), status_code=response.status_code,
                                 media_type=response.headers.get("content-type", "application/json"))
    return app
