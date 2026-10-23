import json
from pathlib import Path
import re
import sqlite3
import unittest
root=Path(__file__).resolve().parent

class SchemaTests(unittest.TestCase):
    def test_schema_upgrade_and_confirmation_upsert_are_idempotent(self):
        db=sqlite3.connect(':memory:')
        db.executescript((root/'schema.sql').read_text())
        db.execute("INSERT INTO reports VALUES ('report','submission','2026-10-23','','failed','{}')")
        db.executescript((root/'schema.sql').read_text())
        self.assertEqual(db.execute('SELECT COUNT(*) FROM reports').fetchone()[0],1)
        sql=re.search(r'env.DB.prepare\(`(INSERT INTO verified_hardware.*?)`\)',(root/'compatibility.mjs').read_text(),re.S).group(1)
        def add(ident,installation,date):
            db.execute(sql,(ident,installation,'10de:2704:196e:13bc','RTX 4080','NVIDIA','PNY','pny-4080-196e-13bc',json.dumps(['static','wave']),'26.7.1','x86_64','2.5.2',date,date,"user-supplied","Original detected name"))
        add('first','installation','2026-10-23T10:00:00Z')
        add('newer','installation','2026-10-23T11:00:00Z')
        add('old-retry','installation','2026-10-23T10:30:00Z')
        self.assertEqual(db.execute('SELECT COUNT(*),id FROM verified_hardware').fetchone(),(1,'newer'))
        add('other','second-installation','2026-10-23T10:00:00Z')
        self.assertEqual(db.execute('SELECT COUNT(*) FROM verified_hardware').fetchone()[0],2)
        db.close()

if __name__=='__main__':unittest.main()
