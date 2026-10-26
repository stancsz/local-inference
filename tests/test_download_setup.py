import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('download_ranges',Path(__file__).resolve().parents[1]/'scripts/download_ranges.py')
download=importlib.util.module_from_spec(spec)
spec.loader.exec_module(download)


class FreshSetupTests(unittest.TestCase):
    def test_fresh_checkout_creates_model_directory_and_uses_pinned_metadata(self):
        weights={name:('fixture '+name).encode() for name in download.FILES}
        metadata={'sha':download.REVISION,'siblings':[{'rfilename':name,'size':len(data),
            'lfs':{'sha256':hashlib.sha256(data).hexdigest()}} for name,data in weights.items()]}
        def response(request,timeout):
            if isinstance(request,str):
                self.assertIn('/revision/'+download.REVISION,request)
                return io.BytesIO(json.dumps(metadata).encode())
            name=next(name for name in weights if '/'+name+'?' in request.full_url)
            self.assertIn('/resolve/'+download.REVISION+'/',request.full_url)
            result=io.BytesIO(weights[name])
            result.status=206
            result.headers={'Content-Range':f'bytes 0-{len(weights[name])-1}/{len(weights[name])}'}
            return result
        with tempfile.TemporaryDirectory() as directory, patch.object(download,'ROOT',Path(directory)), patch.object(download.urllib.request,'urlopen',side_effect=response):
            (Path(directory)/'evidence').mkdir()
            download.main()
            for name,data in weights.items():
                self.assertEqual((Path(directory)/'models'/Path(name).name).read_bytes(),data)
            receipt=json.loads((Path(directory)/'evidence/model-manifest.json').read_text())
            self.assertEqual(receipt['revision'],download.REVISION)
