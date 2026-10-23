import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import gpu_catalog
import scanner
import profiles
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('import_openrgb_catalog',ROOT/'tools/import_openrgb_catalog.py')
importer=importlib.util.module_from_spec(spec);spec.loader.exec_module(importer)

def pci(row):return dict(zip(gpu_catalog.PCI_FIELDS,[int(v,16) for v in row['pci']]))

class CatalogTests(unittest.TestCase):
    def test_rebuild_matches_checked_in_snapshot(self):
        self.assertEqual(importer.build(),gpu_catalog.load()[0])
    def test_known_pny_exact_ids_resolve_without_enabling_other_models(self):
        values=dict(zip(gpu_catalog.PCI_FIELDS,(0x10de,0x2704,0x196e,0x13bc)))
        match=gpu_catalog.identify(values)
        self.assertTrue(match['matched']);self.assertIn('PNYLovelaceGPUController',match['controllers'])
        values['subsystem-id']=0x0001
        self.assertFalse(gpu_catalog.identify(values)['matched'])
    def test_amd_asus_and_msi_are_passive_catalog_matches_only(self):
        data=gpu_catalog.load()[0]
        for family in ['AsusAuraGPUController','MSIGPUController','SapphireGPUController']:
            row=next(r for r in data['pci_registrations'] if r['controller']==family)
            match=gpu_catalog.identify(pci(row));self.assertTrue(match['matched'])
            self.assertFalse(any(p.matches(pci(row)) for p in profiles.PROFILES))
    def test_ambiguous_tuple_retains_all_names_and_controllers(self):
        data,index=gpu_catalog.load();key,rows=next((k,v) for k,v in index.items() if len({r['name'] for r in v})>1)
        match=gpu_catalog.identify(dict(zip(gpu_catalog.PCI_FIELDS,key)))
        self.assertTrue(match['ambiguous']);self.assertIsNone(match['name'])
        self.assertEqual(set(match['aliases']),{r['name'] for r in rows})
    def test_partial_identity_and_usb_are_never_guessed_as_pci(self):
        self.assertFalse(gpu_catalog.identify({'vendor-id':0x10de})['matched'])
        self.assertTrue(gpu_catalog.load()[0]['usb_registrations'])
        self.assertNotIn('IntelArcA770LEController',{r['controller'] for r in gpu_catalog.load()[0]['pci_registrations']})
    def test_import_rejects_executable_expressions_and_recursive_macros(self):
        with self.assertRaises(ValueError):importer.number('__import__("os").system("true")',{})
        with self.assertRaises(ValueError):importer.number('A',{'A':'B','B':'A'})
        self.assertEqual(importer.number('0X68',{}),104)
    def test_import_ignores_commented_registrations(self):
        source='// REGISTER_I2C_PCI_DETECTOR("bad",f,1,2,3,4,5);\n/* REGISTER_I2C_PCI_DETECTOR("bad",f,1,2,3,4,5); */'
        self.assertEqual(list(importer.registrations(source)),[])
    def test_provenance_covers_every_source_and_rejects_changed_input(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'pci_ids.h').write_text('changed')
            (root/'manifest.json').write_text(json.dumps({'files':[{'local':'pci_ids.h','sha256':'0'*64}]}))
            with self.assertRaisesRegex(ValueError,'hash mismatch'):importer.build(root)
