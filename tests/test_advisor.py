import copy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_scoring import fixture, sm


class AdvisorTests(unittest.TestCase):
    def report(self):
        inv = fixture()
        inv.update(Kernel='6.1', PCI=[{'Address': '0000:01:00.0', 'Vendor': '0x10de',
                                       'Device': '0x1234', 'Driver': 'nvidia'}])
        inv['RAMGiB'] = 16
        return sm.score(inv, 'private-computer')

    def test_manual_checks_persist_and_become_stale_when_context_changes(self):
        report = self.report()
        with tempfile.TemporaryDirectory() as directory:
            sm.advisor.set_check(directory, report, 'wifi', 'pass')
            state = sm.advisor.load_state(directory)
            info = sm.advisor.summary(report, state)
            wifi = next(c for c in info['Checks'] if c['Key'] == 'wifi')
            self.assertEqual(wifi['Result'], 'pass')
            self.assertFalse(wifi['Stale'])
            self.assertIn('6.1', wifi['Environment'])
            self.assertIn('nvidia', wifi['Environment'])
            changed = copy.deepcopy(report)
            changed['Inventory']['Kernel'] = '6.2'
            wifi = next(c for c in sm.advisor.summary(changed, state)['Checks'] if c['Key'] == 'wifi')
            self.assertTrue(wifi['Stale'])
            self.assertIn('Retest Wi-Fi', sm.advisor.summary(changed, state)['Recommendations'][0])
            self.assertEqual(report['Score'], sm.score(report['Inventory'])['Score'])
            with self.assertRaises(ValueError):
                sm.advisor.set_check(directory, report, 'wifi', 'maybe')
            self.assertEqual(sm.advisor.load_state(directory), state)

    def test_profile_and_recommendations_do_not_change_scoring(self):
        report = self.report()
        with tempfile.TemporaryDirectory() as directory:
            sm.advisor.set_profile(directory, 'containers')
            info = sm.advisor.summary(report, sm.advisor.load_state(directory))
            self.assertEqual(info['Profile'], 'containers')
            self.assertTrue(any('5 v1 points' in item for item in info['Recommendations']))
            self.assertEqual(report['Score'], sm.score(report['Inventory'])['Score'])

    def test_snapshot_history_and_comparison_ignore_advisor_state(self):
        with tempfile.TemporaryDirectory() as directory:
            older = self.report()
            older['Captured'] = '2026-01-01T00:00:00+00:00'
            left = sm.save(older, directory)
            newer = self.report()
            newer['Captured'] = '2026-01-02T00:00:00+00:00'
            newer['Inventory']['Kernel'] = '6.2'
            right = sm.save(newer, directory)
            sm.advisor.set_check(directory, newer, 'wifi', 'fail')
            self.assertEqual(sm.previous_report(directory, newer)['Captured'], older['Captured'])
            self.assertIn('Kernel changed', sm.compare_reports(left, right))
            self.assertIn('private-computer', sm.compare(directory))
            self.assertEqual(sm.latest_report(directory)['Captured'], newer['Captured'])

    def test_comparison_keeps_checks_separate_for_each_machine(self):
        with tempfile.TemporaryDirectory() as directory:
            left_report = self.report()
            right_report = copy.deepcopy(left_report)
            right_report['Computer'] = 'another-computer'
            left = sm.save(left_report, directory)
            right = sm.save(right_report, directory)
            sm.advisor.set_check(directory, left_report, 'wifi', 'pass')
            self.assertIn('Wi-Fi: pass / not available', sm.compare_reports(left, right))
            sm.advisor.set_check(directory, right_report, 'wifi', 'fail')
            self.assertIn('Wi-Fi: pass / fail', sm.compare_reports(left, right))
            self.assertIn('last check failed',
                          sm.advisor.summary(right_report, sm.advisor.load_state(directory))['Recommendations'][0])

    def test_redacted_export_uses_allowlist_and_does_not_expose_inventory(self):
        report = self.report()
        report['Inventory']['USB'] = ['private serial number']
        with tempfile.TemporaryDirectory() as directory:
            sm.advisor.set_check(directory, report, 'audio', 'pass')
            path = sm.advisor.export_redacted(directory, report, sm.advisor.load_state(directory))
            content = path.read_text()
            self.assertNotIn('private-computer', content)
            self.assertNotIn('private serial number', content)
            self.assertNotIn('/dev/nvme0n1', content)
            self.assertNotIn('0x1234', content)
            self.assertEqual(json.loads(content)['Format'], 'scoring-matrix-redacted-v1')
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_benchmark_is_explicit_and_saved_separately(self):
        report = self.report()
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(sm.advisor.hashlib, 'pbkdf2_hmac') as work, \
                    patch.object(sm.advisor.time, 'perf_counter', side_effect=[0, 1, 2, 4, 5, 8]):
                result = sm.advisor.run_cpu_benchmark(directory, report)
            self.assertEqual(work.call_count, 3)
            self.assertEqual(result['MedianSeconds'], 2)
            self.assertEqual(sm.advisor.load_state(directory)['Machines']['private-computer']['Benchmark']['MedianSeconds'], 2)
            self.assertEqual(report['Score'], sm.score(report['Inventory'])['Score'])

    def test_corrupt_state_is_reported_without_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.advisor.json'
            path.write_text('{"Version": 99}')
            path.chmod(0o600)
            with self.assertRaises(ValueError):
                sm.advisor.set_profile(directory, 'containers')
            self.assertEqual(path.read_text(), '{"Version": 99}')
            payload = sm.advisor_view(self.report(), directory)
            self.assertEqual(payload['Score'], self.report()['Score'])
            self.assertIn('AdvisorError', payload)
            self.assertNotIn('Advisor', payload)

    def test_state_rejects_oversize_or_symlink_without_following_it(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.advisor.json'
            path.write_bytes(b' ' * (sm.advisor.MAX_STATE_BYTES + 1))
            path.chmod(0o600)
            with self.assertRaises(ValueError):
                sm.advisor.load_state(directory)
            outside = Path(directory) / 'outside.json'
            outside.write_text('{}')
            path.unlink()
            path.symlink_to(outside)
            with self.assertRaises(OSError):
                sm.advisor.load_state(directory)

    def test_concurrent_state_updates_preserve_all_checks_and_private_mode(self):
        report = self.report()
        checks = list(sm.advisor.CHECKS)
        with tempfile.TemporaryDirectory() as directory:
            with ThreadPoolExecutor(max_workers=len(checks)) as executor:
                list(executor.map(
                    lambda key: sm.advisor.set_check(directory, report, key, 'pass'),
                    checks))
            state = sm.advisor.load_state(directory)
            self.assertEqual(set(state['Machines']['private-computer']['Checks']), set(checks))
            self.assertEqual((Path(directory) / '.advisor.json').stat().st_mode & 0o777, 0o600)

    def test_invalid_updated_state_is_not_written(self):
        with tempfile.TemporaryDirectory() as directory:
            sm.advisor.set_profile(directory, 'everyday')
            path = Path(directory) / '.advisor.json'
            original = path.read_bytes()
            with self.assertRaises(ValueError):
                sm.advisor.update_state(
                    directory,
                    lambda state: state['Machines'].__setitem__(
                        'x' * (sm.advisor.MAX_COMPUTER_LABEL_LENGTH + 1),
                        {'Checks': {}, 'Benchmark': None}),
                )
            self.assertEqual(path.read_bytes(), original)

    def test_driver_environment_is_bounded_before_persistence(self):
        report = self.report()
        report['Inventory']['PCI'][0]['Driver'] = 'x' * (sm.advisor.MAX_ENVIRONMENT_LENGTH + 1)
        with tempfile.TemporaryDirectory() as directory:
            sm.advisor.set_check(directory, report, 'wifi', 'pass')
            state = sm.advisor.load_state(directory)
            environment = state['Machines']['private-computer']['Checks']['wifi']['Environment']
            self.assertLessEqual(len(environment), sm.advisor.MAX_ENVIRONMENT_LENGTH)

    def test_oversize_new_state_is_not_written(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(sm.advisor, 'MAX_STATE_BYTES', 1):
                with self.assertRaises(ValueError):
                    sm.advisor.set_profile(directory, 'everyday')
            self.assertFalse((Path(directory) / '.advisor.json').exists())

    def test_unreadable_advisor_sidecar_does_not_break_snapshot_comparison(self):
        with tempfile.TemporaryDirectory() as directory:
            first = sm.save(self.report(), directory)
            later = copy.deepcopy(self.report())
            later['Captured'] = '2026-01-02T00:00:00+00:00'
            second = sm.save(later, directory)
            (Path(directory) / '.advisor.json').write_text('not json')
            comparison = sm.compare_reports(first, second)
            self.assertIn('advisor data unavailable', comparison)
            self.assertIn('advisor sidecar warning', comparison.lower())

    def test_export_failure_leaves_no_partial_file(self):
        report = self.report()
        with tempfile.TemporaryDirectory() as directory:
            state = sm.advisor.load_state(directory)
            with patch.object(sm.advisor.os, 'replace', side_effect=OSError('simulated failure')):
                with self.assertRaises(OSError):
                    sm.advisor.export_redacted(directory, report, state)
            exports = Path(directory) / 'exports'
            self.assertEqual(list(exports.glob('redacted-*.json')), [])
            self.assertEqual(list(exports.glob('.export-*')), [])

    def test_snapshot_changes_invalidate_checks_after_hardware_change(self):
        report = self.report()
        with tempfile.TemporaryDirectory() as directory:
            sm.advisor.set_check(directory, report, 'suspend', 'pass')
            state = sm.advisor.load_state(directory)
            changed = copy.deepcopy(report)
            changed['Inventory']['RAMGiB'] += 1
            suspend = next(c for c in sm.advisor.summary(changed, state)['Checks']
                           if c['Key'] == 'suspend')
            self.assertTrue(suspend['Stale'])


if __name__ == '__main__':
    unittest.main()
