import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_scoring import sm, fixture


class ReportTests(unittest.TestCase):
    def report(self, label='example'):
        return sm.score(fixture(), label)

    def test_rejects_malformed_fields_even_when_score_adds_up(self):
        changes = [('Score', True), ('Resources', -1), ('Compatibility', 99),
                   ('Coverage', 99), ('Captured', 'yesterday'), ('Computer', ''),
                   ('Issues', 'note'), ('Inventory', []), ('Status', None)]
        for key, value in changes:
            with self.subTest(key=key):
                report = self.report()
                report[key] = value
                with self.assertRaises(ValueError):
                    sm.validate_report(report)

    def test_rejects_wrong_order_duplicate_categories_and_nonfinite_points(self):
        for value in [None, True, -1, float('nan'), float('inf'), 25.5]:
            with self.subTest(value=value):
                report = self.report()
                report['Breakdown'][0]['Points'] = value
                with self.assertRaises(ValueError):
                    sm.validate_report(report)
        report = self.report()
        report['Breakdown'][0]['Category'] = 'RAM'
        with self.assertRaises(ValueError):
            sm.validate_report(report)
        report = self.report()
        report['Breakdown'].reverse()
        with self.assertRaises(ValueError):
            sm.validate_report(report)

    def test_functional_points_cannot_be_forged_into_matrix_one(self):
        report = self.report()
        report['Breakdown'][3]['Points'] = 15
        report['Score'] += 7
        report['Compatibility'] += 7
        with self.assertRaises(ValueError):
            sm.validate_report(report)

    def test_windows_shape_and_integral_json_numbers(self):
        report = self.report()
        report['Inventory']['CPU'] = [{'Architecture': 9, 'NumberOfCores': 8}]
        report['Score'] = float(report['Score'])
        self.assertIsNotNone(sm.validate_report(report))
        self.assertTrue(sm.assessment(report)['Rankable'])
        report['Inventory']['System'] = {'Manufacturer': 'Microsoft Corporation', 'Model': 'Virtual Machine'}
        self.assertEqual(sm.assessment(report)['State'], 'virtual')

    def test_incomplete_unknown_architecture_and_virtual_are_unranked(self):
        cases = [('Virtualized', True, 'virtual'), ('SecureBoot', None, 'incomplete')]
        for key, value, state in cases:
            inv = fixture()
            inv[key] = value
            assessment = sm.assessment(sm.score(inv))
            self.assertEqual(assessment['State'], state)
            self.assertFalse(assessment['Rankable'])
        report = self.report()
        report['Inventory']['CPU']['Architecture'] = 'aarch64'
        self.assertFalse(sm.assessment(report)['Rankable'])

    def test_latest_skips_oversize_and_structurally_invalid_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            sm.save(self.report(), folder)
            invalid = self.report('invalid')
            invalid['Captured'] = '2099-01-01T00:00:00Z'
            invalid['Breakdown'][0]['Known'] = 'yes'
            (folder/'invalid.json').write_text(json.dumps(invalid))
            (folder/'oversize.json').write_bytes(b' ' * (sm.MAX_REPORT_BYTES + 1))
            self.assertEqual(sm.latest_report(folder)['Computer'], 'example')

    def test_comparison_uses_newest_snapshot_and_separates_unknowns(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = self.report('workstation')
            report['Captured'] = '2026-01-01T00:00:00Z'
            sm.save(report, tmp)
            newer = copy.deepcopy(report)
            newer['Captured'] = '2026-01-02T00:00:00Z'
            newer['Inventory']['Virtualized'] = True
            sm.save(newer, tmp)
            sm.save(self.report('physical'), tmp)
            result = sm.compare(tmp)
            self.assertEqual(result.count('workstation'), 1)
            complete, review = result.split('Needs review (unranked)')
            self.assertIn('physical', complete)
            self.assertNotIn('workstation', complete)
            self.assertIn('workstation', review)

    def test_compact_payload_does_not_expose_full_inventory_or_mutate_report(self):
        report = self.report()
        report['Inventory']['PCI'] = ['large inventory'] * 100
        original = copy.deepcopy(report)
        payload = sm.view_report(report)
        self.assertEqual(payload['Score'], report['Score'])
        self.assertEqual(set(payload['Inventory']), {'Virtualized'})
        self.assertIn('Assessment', payload)
        self.assertEqual(report, original)
        self.assertIsNone(sm.view_report(None))

    def test_atomic_save_failure_keeps_previous_json_and_cleans_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = sm.save(self.report('previous'), tmp)
            original = path.read_bytes()
            with patch.object(sm.os, 'replace', side_effect=OSError('simulated failure')):
                with self.assertRaises(OSError):
                    sm.save(self.report('candidate'), tmp)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(len(list(Path(tmp).glob('*.json'))), 1)
            self.assertEqual(list(Path(tmp).glob('.snapshot-*')), [])


if __name__ == '__main__':
    unittest.main()
