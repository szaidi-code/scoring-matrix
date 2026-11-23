import json
from pathlib import Path
import re
import unittest

from test_scoring import ROOT, sm, fixture


class QmlContractTests(unittest.TestCase):
    def setUp(self):
        self.widget_qml = (ROOT / 'Widget.qml').read_text(encoding='utf-8')
        self.ring_qml = (ROOT / 'ScoreRing.qml').read_text(encoding='utf-8')
        self.catalog = json.loads((ROOT / 'i18n/en.json').read_text(encoding='utf-8'))

    def test_manifest_and_collector_versions_match(self):
        manifest = json.loads((ROOT / 'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['version'], sm.VERSION)

    def test_every_qml_text_element_explicitly_uses_plain_text(self):
        for name, source in (('Widget.qml', self.widget_qml), ('ScoreRing.qml', self.ring_qml)):
            for match in re.finditer(r'(?:component\s+\w+\s*:\s*)?\bText\s*\{', source):
                # Extract the balanced block for this Text element.
                start = match.end()
                depth = 1
                pos = start
                while pos < len(source) and depth > 0:
                    if source[pos] == '{':
                        depth += 1
                    elif source[pos] == '}':
                        depth -= 1
                    pos += 1
                block = source[start:pos - 1]
                self.assertIn(
                    'textFormat: Text.PlainText',
                    block,
                    f'{name} contains a Text element without textFormat: Text.PlainText',
                )

    def test_animations_use_style_duration_under_300ms(self):
        for name, source in (('Widget.qml', self.widget_qml), ('ScoreRing.qml', self.ring_qml)):
            durations = re.findall(r'\bduration\s*:\s*([^\n;}]+)', source)
            self.assertTrue(durations, f'Expected animation duration declarations in {name}')
            for expr in durations:
                expr = expr.strip()
                m = re.fullmatch(r'Style\.duration\((\d+)\)', expr)
                self.assertIsNotNone(m, f'{name} must use Style.duration(ms), found: {expr}')
                self.assertLess(int(m.group(1)), 300, f'{name} animation duration must stay under 300ms: {expr}')

    def test_shared_widget_button_sinks_neutralize_markup_and_bound_length(self):
        self.assertIn('function plainText(value, maxLen)', self.widget_qml)
        self.assertIn('.replace(/</g,', self.widget_qml)
        self.assertIn('.replace(/>/g,', self.widget_qml)
        widget_button_match = re.search(r'WidgetButton\s*\{([\s\S]*?)\n  \}', self.widget_qml)
        self.assertIsNotNone(widget_button_match)
        block = widget_button_match.group(1)
        self.assertIn('text: root.plainText(', block)
        self.assertIn('tooltipText: root.plainText(', block)
        # Markup-shaped hardware/report strings remain intact in Python view_report
        # while QML Text.PlainText + plainText() neutralize any markup interpretation.
        inv = fixture()
        inv['Graphics'] = [{'Vendor': '0x8086', 'Name': '<img src="https://example.invalid/tracker">GPU'}]
        payload = sm.view_report(sm.score(inv, 'example'))
        self.assertIn('<img src=', payload['Breakdown'][3]['Reason'])
        self.assertEqual(payload['Assessment']['Title'], 'Ready for hands-on checks')

    def test_translations_catalog_matches_qml_keys(self):
        self.assertIn('Commons.Translations', self.widget_qml)
        self.assertIn('Qt.resolvedUrl("i18n")', self.widget_qml)
        self.assertIn('Commons.I18n.formatLocale', self.widget_qml)
        self.assertNotIn('Qt.locale()', self.widget_qml)
        self.assertIn('Commons.I18n.formatNumber', self.widget_qml)
        self.assertIn('Commons.I18n.formatNumber', self.ring_qml)
        self.assertIn('Commons.Util.readingKey(event)', self.widget_qml)

        static_keys = set(re.findall(r'strings\.t\("([^"]+)"\)', self.widget_qml))
        error_keys = set(re.findall(r'setErrorKey\("([^"]+)"\)', self.widget_qml))
        category_keys = set()
        for cat in ('cpu', 'memory', 'disk', 'graphics', 'network', 'firmware'):
            for suffix in ('name', 'caption', 'rule'):
                category_keys.add(f'category.{cat}.{suffix}')
        referenced = static_keys | error_keys | category_keys

        for key in referenced:
            self.assertIn(key, self.catalog, f'Missing i18n/en.json key: {key}')
            self.assertIsInstance(self.catalog[key], str)
            self.assertTrue(self.catalog[key].strip(), f'Empty i18n/en.json value for {key}')

        unused = set(self.catalog) - referenced
        self.assertEqual(unused, set(), f'Unused keys in i18n/en.json: {sorted(unused)}')


if __name__ == '__main__':
    unittest.main()
