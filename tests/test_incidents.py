import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'automation'))
from validate_incidents import validate, audit


class IncidentTests(unittest.TestCase):
    def setUp(self):
        self.records = [json.loads(p.read_text()) for p in sorted((ROOT / 'evidence/validation').glob('*.json'))]

    def test_six_bundled_records(self):
        self.assertEqual(len(self.records), 6)
        for r in self.records:
            self.assertEqual(validate(r), ([], True))

    def test_contradiction_detected(self):
        r = self.records[0]
        r['checks'][0]['result'] = 'fail'
        errors, recovered = validate(r)
        self.assertTrue(errors)
        self.assertFalse(recovered)

    def test_honest_failed_checklist(self):
        r = self.records[0]
        r['checks'][0]['result'] = 'fail'
        r['overall_result'] = 'fail'
        self.assertEqual(validate(r), ([], False))

    def test_failed_postfix(self):
        r = self.records[-1]
        r['post_fix']['application_reachability'] = 'fail'
        self.assertEqual(validate(r), ([], False))

    def test_empty_stages(self):
        for field in ('pre_fix', 'post_fix'):
            r = copy.deepcopy(self.records[-1])
            r[field] = {}
            self.assertTrue(validate(r)[0])

    def test_empty_checks(self):
        self.records[0]['checks'] = []
        self.assertTrue(validate(self.records[0])[0])

    def test_unknown_result(self):
        self.records[0]['checks'][0]['result'] = 'unknown'
        self.assertTrue(validate(self.records[0])[0])

    def test_missing_required_field(self):
        del self.records[0]['checks'][0]['command']
        self.assertTrue(validate(self.records[0])[0])

    def test_duplicate_check(self):
        r = self.records[0]
        r['checks'].append(copy.deepcopy(r['checks'][0]))
        self.assertTrue(validate(r)[0])

    def test_synthetic_label_required(self):
        self.records[0]['synthetic_data'] = False
        self.assertTrue(validate(self.records[0])[0])

    def test_malformed_input(self):
        for value in (None, [], 'text', 7, {}, {'checks': [None]}):
            self.assertTrue(validate(value)[0])

    def test_mixed_formats(self):
        self.records[0]['pre_fix'] = {'test': 'pass'}
        self.assertTrue(validate(self.records[0])[0])

    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertTrue(audit(Path(d))[0][1])

    def test_invalid_json(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'inc-001-validation.json').write_text('{')
            self.assertTrue(audit(Path(d))[0][1])

    def test_filename_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'inc-999-validation.json').write_text(json.dumps(self.records[0]))
            self.assertTrue(audit(Path(d))[0][1])

    def test_cli_exit_and_report(self):
        with tempfile.TemporaryDirectory() as d:
            for failed in (False, True):
                r = copy.deepcopy(self.records[0])
                if failed:
                    r['checks'][0]['result'] = 'fail'
                (Path(d) / 'inc-001-validation.json').write_text(json.dumps(r))
                report = Path(d) / 'report.md'
                result = subprocess.run([sys.executable, str(ROOT / 'automation/validate_incidents.py'),
                                         '--input-dir', d, '--report', str(report)], capture_output=True)
                self.assertEqual(result.returncode, int(failed))
                self.assertIn('Overall: ' + ('FAIL' if failed else 'PASS'), report.read_text())


if __name__ == '__main__':
    unittest.main()
