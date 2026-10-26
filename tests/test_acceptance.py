import copy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from claude_acceptance import validate_model_audit, validate_process_rows


class ModelAuditAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.manifest=json.loads((ROOT/'evidence/model-manifest.json').read_text())
        self.artifact={'repository':self.manifest['repository'],'revision':self.manifest['revision'],
            'total_weight_bytes':12304451360,'quantization':{'main':'IQ3_XXS','mtp':'Q4_0'},
            'configured_context_size':40960,'limitations':['Disk size only: '+', '.join(f['file'] for f in self.manifest['files'])]}

    def test_correct_explicit_quantization_mapping_is_accepted(self):
        self.assertTrue(validate_model_audit(self.artifact,self.manifest,40960))

    def test_optional_artifact_mapping_must_match_manifest(self):
        artifact=dict(self.artifact,artifacts={'main_gguf':'Qwen3.8-27B-UD-IQ3_XXS.gguf','mtp_gguf':'mtp-Qwen3.8-27B-Q4_0.gguf'})
        self.assertTrue(validate_model_audit(artifact,self.manifest,40960))
        artifact['artifacts']['main_gguf']='wrong.gguf'
        self.assertFalse(validate_model_audit(artifact,self.manifest,40960))

    def test_wrong_arithmetic_quantization_and_context_are_rejected(self):
        for change in ({'total_weight_bytes':12304457360},
                       {'quantization':{'main':'Q4_0','mtp':'IQ3_XXS'}},
                       {'configured_context_size':65536}, {'revision':'unverified'},
                       {'limitations':[]}):
            artifact=copy.deepcopy(self.artifact)
            artifact.update(change)
            with self.subTest(change=change):
                self.assertFalse(validate_model_audit(artifact,self.manifest,40960))

    def test_swapped_process_identity_is_rejected(self):
        processes=[{'process':'dwm','pid':195736,'dedicated_mib':1688.2}]
        self.assertTrue(validate_process_rows('| dwm | 195736 | 1688.2 |',processes))
        self.assertFalse(validate_process_rows('| dwm | 282312 | 1688.2 |',processes))
