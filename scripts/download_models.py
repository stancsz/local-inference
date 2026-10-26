"""Download pinned public GGUF artifacts, resuming interrupted transfers with curl."""
import concurrent.futures
import json
from pathlib import Path
import subprocess
import urllib.request

REPO = 'unsloth/Qwen3.8-27B-GGUF'
FILES = ['Qwen3.8-27B-UD-IQ3_XXS.gguf', 'MTP/mtp-Qwen3.8-27B-Q4_0.gguf']

def main():
    metadata = json.load(urllib.request.urlopen(f'https://huggingface.co/api/models/{REPO}'))
    revision = metadata['sha']
    root = Path(__file__).resolve().parents[1]
    (root / 'models').mkdir(exist_ok=True)
    (root / 'evidence/model-manifest.json').write_text(json.dumps({'repository': REPO, 'revision': revision, 'files': FILES}, indent=2))
    def download(name):
        dest = root / 'models' / Path(name).name
        subprocess.run(['curl.exe', '-fL', '--retry', '3', '-C', '-', '-o', str(dest), f'https://huggingface.co/{REPO}/resolve/{revision}/{name}'], check=True)
        return {'file': name, 'bytes': dest.stat().st_size}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        print(json.dumps(list(pool.map(download, FILES))), flush=True)

if __name__ == '__main__':
    main()
