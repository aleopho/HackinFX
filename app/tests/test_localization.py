import collections,json,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class LocalizationResources(unittest.TestCase):
    def test_all_packaged_locales_have_complete_keys_and_valid_placeholders(self):
        root=ROOT/'Localization';manifest=json.loads((root/'manifest.json').read_text());base=json.loads((root/'en.json').read_text())
        self.assertEqual(len(manifest['languages']),22)
        for code in manifest['languages']:
            values=json.loads((root/(code+'.json')).read_text());self.assertEqual(set(values),set(base),code)
            for key,value in values.items():
                self.assertIsInstance(value,str);self.assertTrue(value.strip(),(code,key))
                self.assertEqual(collections.Counter(re.findall(r'\{[0-9]+\}',key)),collections.Counter(re.findall(r'\{[0-9]+\}',value)),(code,key))
    def test_effect_names_and_descriptions_are_translated_without_changing_ids(self):
        base=json.loads((ROOT/'Localization/en.json').read_text());catalog=json.loads((ROOT/'effects_catalog.json').read_text())
        for effect in catalog['effects']:
            self.assertIn(effect['name'],base);self.assertIn(effect['description'],base)
    def test_languages_are_static_resources_and_legacy_gpu_ui_is_removed(self):
        source=(ROOT/'CommunityRGB.swift').read_text()+(ROOT/'ControlCenter.swift').read_text()
        self.assertNotIn('GPU Lab',source);self.assertNotIn('struct Studio:',source);self.assertNotIn('struct Sidebar:',source)
        self.assertNotIn('translate.googleapis.com',(ROOT/'Localization.swift').read_text())
