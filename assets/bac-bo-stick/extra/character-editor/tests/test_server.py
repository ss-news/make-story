import importlib.util
import math
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('editor_server', Path(__file__).parents[1] / 'serve.py')
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)

class DocumentTest(unittest.TestCase):
    def document(self):
        return {'format':'character-layout/1', 'source':'human-action-trial-v1', 'canvas':{'width':1000,'height':800},
                'parts':[{'id':'head','asset':'head_front','x':500,'y':200,'width':260,'height':255,
                          'pivotX':.5,'pivotY':.5,'rotation':0,'visible':True,'z':10}]}
    def test_roundtrip(self):
        doc = self.document()
        self.assertEqual(server.validate_document(doc), doc)
    def test_reject_bad_values(self):
        for key, value in [('x', math.nan), ('width',-1), ('asset','../../secret'), ('visible',1), ('rotation',9000)]:
            with self.subTest(key=key):
                doc=self.document();doc['parts'][0][key]=value
                with self.assertRaises(ValueError):server.validate_document(doc)
    def test_duplicate_and_empty(self):
        doc=self.document();doc['parts']*=2
        with self.assertRaises(ValueError):server.validate_document(doc)
        doc['parts']=[]
        with self.assertRaises(ValueError):server.validate_document(doc)
    def test_names(self):
        self.assertEqual(server.safe_name('nhan-vat-01'),'nhan-vat-01')
        for name in ['../x','/tmp/a','a.json','', 'a'*81]:
            with self.subTest(name=name), self.assertRaises(ValueError):server.safe_name(name)

if __name__=='__main__':unittest.main()
