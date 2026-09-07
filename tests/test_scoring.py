import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / (name + '.py'))
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


sm = module('scoring_matrix')
installer = module('install')


def fixture():
    return dict(CPU=dict(Cores=24, Threads=32, Architecture='x86_64'), RAMGiB=63.7,
                SelectedDisk=dict(Path='/dev/nvme0n1', Size=1024209543168, Media='NVMe'),
                Graphics=[dict(Vendor='0x10de', Name='Example NVIDIA')],
                Network=[dict(Wireless=True, Vendor='0x8086'), dict(Ethernet=True)],
                Firmware='Uefi', SecureBoot=True, SecureBootSource='User reported')


class ScoringTests(unittest.TestCase):
    def test_reference_score_and_provenance(self):
        report = sm.score(fixture(), 'example')
        self.assertEqual((report['Score'], report['Resources'], report['Compatibility'], report['Coverage']), (89, 70, 19, 100))
        self.assertEqual(report['SecureBootSource'], 'User reported')

    def test_secure_boot_false_is_distinct_from_unknown(self):
        inv = fixture()
        inv['SecureBoot'] = None
        unknown = sm.score(inv)
        inv['SecureBoot'] = False
        disabled = sm.score(inv)
        self.assertEqual(unknown['Score'], 89)
        self.assertEqual(unknown['Coverage'], 95)
        self.assertEqual(disabled['Score'], 91)

    def test_capacity_caps_and_ceiling(self):
        inv = fixture()
        inv['CPU'].update(Cores=128, Threads=256)
        inv['RAMGiB'] = 1024
        inv['SelectedDisk']['Size'] = 100 * 1024**4
        inv['Graphics'] = [dict(Vendor='0x1002')]
        inv['SecureBoot'] = False
        self.assertEqual(sm.score(inv)['Score'], 95)

    def test_missing_does_not_become_full_score(self):
        report = sm.score({})
        self.assertEqual(report['Score'], 0)
        self.assertEqual(report['Coverage'], 0)
        self.assertIn('Incomplete', report['Status'])

    def test_ram_boundaries(self):
        for value, expected in [(2.9, 0), (3, 3), (7, 10), (15, 18), (31, 23), (63, 25)]:
            inv = fixture()
            inv['RAMGiB'] = value
            self.assertEqual(sm.score(inv)['Breakdown'][1]['Points'], expected)

    def test_virtualization_and_architecture(self):
        inv = fixture()
        inv['CPU']['Architecture'] = 'aarch64'
        self.assertIn('Not a standard', sm.score(inv)['Status'])
        inv['Virtualized'] = True
        self.assertIn('Virtual environment', sm.score(inv)['Status'])

    def test_bom_reports_and_version_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = sm.score(fixture(), 'example')
            path = sm.save(report, Path(tmp))
            path.write_text(json.dumps(report), encoding='utf-8-sig')
            self.assertIn('example', sm.compare(tmp))
            report['MatrixVersion'] = '2.0'
            path.write_text(json.dumps(report))
            with self.assertRaises(ValueError):
                sm.compare(tmp)

    def test_installer_spaces_update_uninstall_keeps_reports(self):
        with tempfile.TemporaryDirectory(prefix='scoring test ') as tmp:
            desktop = installer.install(tmp, ROOT)
            self.assertIn('--menu', desktop.read_text())
            self.assertIn('Terminal=true', desktop.read_text())
            installer.install(tmp, ROOT)
            extra = Path(tmp)/'scoring-matrix/user-note.txt'
            extra.write_text('keep')
            installer.install(tmp, ROOT, uninstall=True)
            self.assertFalse(desktop.exists())
            self.assertTrue(extra.exists())

    def test_installer_refuses_foreign_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/'scoring-matrix').mkdir()
            with self.assertRaises(ValueError):
                installer.install(tmp, ROOT)

    def test_desktop_path_escaping(self):
        with self.assertRaises(ValueError):
            installer.desktop_quote('/tmp/%F/path')
        self.assertEqual(installer.desktop_quote('/tmp/my files/app.py'), '"/tmp/my files/app.py"')

    def test_plugin_manifest_contract(self):
        manifest = json.loads((ROOT/'manifest.json').read_text())
        self.assertEqual(manifest['schemaVersion'], 1)
        self.assertFalse(manifest['id'].startswith('omarchy.'))
        self.assertTrue((ROOT/manifest['entryPoints']['barWidget']).is_file())

    def test_latest_report_uses_capture_time_and_skips_invalid_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            self.assertIsNone(sm.latest_report(folder))
            older = sm.score(fixture(), 'older')
            older['Captured'] = '2026-01-01T00:00:00+00:00'
            newer = copy.deepcopy(older)
            newer.update(Computer='newer', Captured='2026-01-02T00:00:00Z')
            # Filename order and creation time must not determine the snapshot.
            (folder/'a.json').write_text(json.dumps(newer), encoding='utf-8-sig')
            (folder/'z.json').write_text(json.dumps(older))
            (folder/'broken.json').write_text('{')
            (folder/'null.json').write_text('null')
            incompatible = copy.deepcopy(newer)
            incompatible['MatrixVersion'] = '2.0'
            (folder/'future.json').write_text(json.dumps(incompatible))
            invalid = copy.deepcopy(newer)
            invalid['Score'] += 1
            (folder/'bad-total.json').write_text(json.dumps(invalid))
            self.assertEqual(sm.latest_report(folder)['Computer'], 'newer')


if __name__ == '__main__':
    unittest.main()
