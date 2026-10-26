"""Launch Claude Code against this standalone local gateway, without global edits."""
import os
from pathlib import Path
import subprocess
import sys
from setup_env import gateway_key, ROOT

def main():
    env=dict(os.environ)
    for key in ['GATEWAY_MASTER_KEY','EXPERTS_API_KEY','ANTHROPIC_AUTH_TOKEN','CLAUDECODE']:
        env.pop(key,None)
    config=ROOT/'tmp/claude-local-config'
    config.mkdir(parents=True,exist_ok=True)
    env.update(ANTHROPIC_API_KEY=gateway_key(),ANTHROPIC_BASE_URL='http://127.0.0.1:8090',ANTHROPIC_MODEL='qwen3.8-27b',ANTHROPIC_DEFAULT_OPUS_MODEL='qwen3.8-27b',ANTHROPIC_DEFAULT_SONNET_MODEL='qwen3.8-27b',ANTHROPIC_DEFAULT_HAIKU_MODEL='qwen3.8-27b',CLAUDE_CONFIG_DIR=str(config),CLAUDE_CODE_DISABLE_1M_CONTEXT='1',CLAUDE_CODE_MAX_CONTEXT_TOKENS='1000000',CLAUDE_CODE_MAX_OUTPUT_TOKENS='4096',CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC='1',API_TIMEOUT_MS='600000')
    raise SystemExit(subprocess.call(['claude.cmd','--bare','--model','qwen3.8-27b',*sys.argv[1:]],env=env))

if __name__=='__main__': main()
