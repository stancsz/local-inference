"""One explicit, bounded, text-only call to an owner-configured cloud advisor."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import urllib.parse
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', required=True, type=Path)
    args = parser.parse_args()
    packet = args.packet.read_text(encoding='utf-8')
    if not packet.strip() or len(packet) > 6000:
        parser.error('Advisor packet must contain 1..6000 characters')
    base = os.environ.get('ADVISOR_BASE_URL', '').rstrip('/')
    model = os.environ.get('ADVISOR_MODEL', '')
    key = os.environ.get('ADVISOR_API_KEY', '')
    parsed = urllib.parse.urlparse(base)
    if not model or not key or not parsed.hostname:
        parser.error('Set ADVISOR_BASE_URL (including /v1), ADVISOR_MODEL and ADVISOR_API_KEY')
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        parser.error('Advisor URL must not contain credentials, query or fragment')
    if parsed.scheme != 'https' and not (parsed.scheme == 'http' and parsed.hostname in ('127.0.0.1', 'localhost', '::1')):
        parser.error('Use HTTPS, or HTTP on loopback only')
    body = {'model':model, 'messages':[
        {'role':'system','content':'You are a read-only engineering advisor. Assess the supplied evidence. Return the smallest useful recommendation, a verification step, and a stop condition. Do not claim to run tools or tests. Stay under 400 words.'},
        {'role':'user','content':packet}], 'max_tokens':1024, 'stream':False}
    request = urllib.request.Request(base+'/chat/completions',data=json.dumps(body).encode(),
        headers={'Content-Type':'application/json','Authorization':'Bearer '+key})
    # No retries or fallback. A redirect must not send this credential elsewhere.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(request, timeout=90) as response:
            result = json.load(response)
    except Exception as error:
        print(f'Advisor request failed ({type(error).__name__}); no fallback or retry.',file=sys.stderr)
        return 1
    choice = result['choices'][0]
    receipt = {'role':'advisor', 'requested_model':model, 'returned_model':result.get('model'),
        'packet_sha256':hashlib.sha256(packet.encode()).hexdigest(), 'packet_characters':len(packet),
        'usage':result.get('usage'), 'finish_reason':choice.get('finish_reason'),
        'answer':choice['message'].get('content'), 'usage_scope':'Provider-reported token usage; no dollar-savings claim.'}
    print(json.dumps(receipt,ensure_ascii=False,indent=2))
    return 0 if receipt['answer'] and receipt['finish_reason']=='stop' else 1


if __name__ == '__main__':
    raise SystemExit(main())
