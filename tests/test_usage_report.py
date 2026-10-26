import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('usage_report',Path(__file__).resolve().parents[1]/'scripts/usage_report.py')
report=importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


class UsageAccountingTests(unittest.TestCase):
    def count(self, receipt):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'receipt.json'
            path.write_text(json.dumps(receipt))
            return report.tokens(path)

    def test_openai_cached_tokens_are_not_counted_twice(self):
        self.assertEqual(self.count({'usage':{'prompt_tokens':100,'completion_tokens':20,
            'prompt_tokens_details':{'cached_tokens':80}}}),120)

    def test_claude_separate_cache_tokens_and_failed_attempt_usage_are_counted(self):
        self.assertEqual(self.count({'is_error':True,'usage':{'input_tokens':10,'output_tokens':20,
            'cache_read_input_tokens':100,'cache_creation_input_tokens':30}}),160)

    def test_missing_or_invalid_usage_does_not_become_zero(self):
        for usage in (None,{}, {'input_tokens':10}, {'prompt_tokens':True,'completion_tokens':20}):
            with self.subTest(usage=usage), self.assertRaises(ValueError):
                self.count({'usage':usage})

    def test_stream_counts_terminal_total_once(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'receipt.jsonl'
            path.write_text('\n'.join(json.dumps(row) for row in [
                {'type':'assistant','usage':{'input_tokens':100,'output_tokens':20}},
                {'type':'result','usage':{'input_tokens':100,'output_tokens':20}}]))
            self.assertEqual(report.tokens(path),120)


if __name__=='__main__': unittest.main()
