import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
from test_scoring import sm, fixture


class StartupTests(unittest.TestCase):
    def test_reuses_snapshot_across_restarts_and_rescans_on_new_boot_or_disk(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(sm, 'boot_id', return_value='boot-a') as boot, patch.object(sm, 'collect', return_value=fixture()) as collect:
            first = sm.ensure_boot_report(directory)
            self.assertEqual(sm.ensure_boot_report(directory), first)
            self.assertEqual(collect.call_count, 1)
            boot.return_value = 'boot-b'
            sm.ensure_boot_report(directory)
            self.assertEqual(collect.call_count, 2)
            sm.ensure_boot_report(directory, '/dev/nvme0n1')
            self.assertEqual(collect.call_count, 3)
            collect.assert_called_with('/dev/nvme0n1')
            self.assertIsNotNone(sm.view_report(sm.latest_report(directory))['Assessment'])

    def test_invalid_cached_report_is_replaced(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(sm, 'boot_id', return_value='boot-a'), patch.object(sm, 'collect', return_value=fixture()) as collect:
            Path(directory, 'broken.json').write_text('{bad json')
            sm.ensure_boot_report(directory)
            collect.assert_called_once()
            self.assertIsNotNone(sm.latest_report(directory))

    def test_failed_scan_preserves_existing_report(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(sm, 'boot_id', return_value='boot-a'), patch.object(sm, 'collect', return_value=fixture()) as collect:
            first = sm.ensure_boot_report(directory)
            collect.side_effect = ValueError('Disk unavailable')
            with self.assertRaises(ValueError):
                sm.ensure_boot_report(directory, '/dev/missing')
            self.assertEqual(sm.latest_report(directory), first)

    def test_unavailable_boot_id_reuses_saved_report(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(sm, 'boot_id', return_value=None), patch.object(sm, 'collect', return_value=fixture()) as collect:
            first = sm.ensure_boot_report(directory)
            self.assertEqual(sm.ensure_boot_report(directory), first)
            collect.assert_called_once()
