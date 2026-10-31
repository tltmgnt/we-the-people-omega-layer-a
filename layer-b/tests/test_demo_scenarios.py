import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from civic_portfolio.scenarios import Scenarios,WORKFLOWS,fingerprint
from civic_portfolio.store import Store,Conflict
from civic_portfolio.__main__ import server

class DemoScenarioTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'db.sqlite3';self.store=Store(self.path);self.lab=Scenarios(self.store)
    def load(self,batch_id='SYN-DEMO'):
        return self.lab.load_demo(dict(batch_id=batch_id,actor='TEST INITIATOR'))
    def test_loads_all_44_with_checks_observations_and_current_capstone(self):
        receipt=self.load();self.assertTrue(receipt['created']);self.assertEqual(len(receipt['runs']),44)
        self.assertEqual({r['project_id'] for r in receipt['runs']},{f'{i:03}' for i in range(7,51)})
        self.assertEqual(receipt['definition_blocked'],['001','002','003','004','005','006'])
        for item in receipt['runs']:
            run=self.lab.run(item['run_id']);config=WORKFLOWS[run['workflow']]
            self.assertEqual(run['state']['stage'],config['completion']);self.assertEqual(run['state']['quality'],'PASS')
            self.assertEqual(run['state_sha256'],item['state_sha256']);self.assertFalse(run['execution_authorized'])
            if config.get('metrics'):
                self.assertTrue(all(m['value'] is not None and m['path_current'] and m['contract_current'] for m in self.lab.report(item['run_id'])['observations']))
        capstone=self.lab.report('SYN-DEMO-050')
        self.assertTrue(capstone['capstone_evidence_current']);self.assertEqual(capstone['layer_a_status'],'LEGAL_REVIEW_REQUIRED')
    def test_repeat_load_is_idempotent_and_preserves_operator_changes(self):
        first=self.load();key='SYN-DEMO-024';before=self.lab.run(key)
        self.lab.command(key,dict(version=before['version'],action='TICK',parameters=dict(minutes=5),actor='OPERATOR',note='User changed fictional clock'))
        modified=self.lab.run(key);again=self.load()
        self.assertFalse(again['created']);self.assertIn(key,again['changed_since_seed'])
        self.assertEqual(self.lab.run(key),modified);self.assertEqual(again['created_at'],first['created_at'])
        self.assertFalse(self.lab.report('SYN-DEMO-050')['capstone_evidence_current'])
        self.assertEqual(len(self.lab.runs()),44)
    def test_new_namespace_creates_another_batch_without_overwrite(self):
        self.load();before=self.lab.run('SYN-DEMO-024')
        second=self.load('SYN-DEMO-TWO');self.assertTrue(second['created']);self.assertEqual(len(self.lab.runs()),88)
        self.assertEqual(self.lab.run('SYN-DEMO-024'),before)
    def test_collision_is_rejected_before_any_batch_mutation(self):
        self.lab.create(dict(run_id='SYN-DEMO-024',workflow='p024',label='Existing user run',start_at='2026-01-01T00:00:00Z',actor='USER',note='Preserve this'))
        before=self.lab.run('SYN-DEMO-024')
        with self.assertRaises(Conflict):self.load()
        self.assertEqual(self.lab.run('SYN-DEMO-024'),before);self.assertEqual(len(self.lab.runs()),1)
        self.assertEqual(self.lab.demo_batches(),[])
    def test_injected_mid_batch_failure_rolls_back_runs_events_audit_and_receipt(self):
        original=self.lab.command;calls=0
        def fail(key,data,_db=None):
            nonlocal calls
            calls+=1
            if calls==20:raise ValueError('Injected fixture failure')
            return original(key,data,_db=_db)
        with patch.object(self.lab,'command',side_effect=fail):
            with self.assertRaises(ValueError):self.load()
        self.assertEqual(self.lab.runs(),[]);self.assertEqual(self.lab.demo_batches(),[])
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM scenario_events').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM audit').fetchone()[0],0)
    def test_source_projects_and_observatory_tables_are_untouched(self):
        before=self.store.export()['projects'];self.load();after=self.store.export()
        self.assertEqual(after['projects'],before);self.assertEqual(after['snapshots'],[])
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM permit_cases').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM justice_pilots').fetchone()[0],0)
        self.assertEqual(len(after['synthetic_scenarios']['demo_batches']),1)
    def test_receipt_flags_catalog_changes_and_missing_runs(self):
        self.load();config=WORKFLOWS['p024'];old=config['label']
        try:
            config['label']='Changed hypothetical catalog'
            self.assertTrue(self.load()['catalog_changed'])
        finally:config['label']=old
        with self.store.connect() as db:
            db.execute('DELETE FROM scenario_events WHERE run_id=?',('SYN-DEMO-007',));db.execute('DELETE FROM scenario_runs WHERE id=?',('SYN-DEMO-007',))
        with self.assertRaises(Conflict):self.load()
        self.assertIn('SYN-DEMO-007',self.lab.demo_receipt('SYN-DEMO')['missing_since_seed'])
    def test_backup_restore_and_deterministic_seed_receipt(self):
        receipt=self.load();target=Path(self.tmp.name)/'backup.sqlite3';self.store.backup(target)
        restored=Scenarios(Store(target));self.assertEqual(restored.demo_receipt('SYN-DEMO'),self.lab.demo_receipt('SYN-DEMO'))
        self.assertEqual(restored.run('SYN-DEMO-050'),self.lab.run('SYN-DEMO-050'))
        self.assertEqual(receipt['catalog_sha256'],fingerprint(__import__('civic_portfolio.scenarios',fromlist=['catalog']).catalog()))
    def test_invalid_metadata_never_creates_runs(self):
        for payload in [dict(batch_id='real-case',actor='TEST'),dict(batch_id='SYN-'+'A'*52,actor='TEST'),dict(batch_id='SYN-DEMO',actor='')]:
            with self.assertRaises(ValueError):self.lab.load_demo(payload)
        self.assertEqual(self.lab.runs(),[])
    def test_http_token_receipt_and_cli_seed(self):
        app=server(self.store,0);thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
        self.addCleanup(app.server_close);self.addCleanup(thread.join,2);self.addCleanup(app.shutdown)
        base='http://127.0.0.1:'+str(app.server_port);boot=json.load(urlopen(base+'/api/scenarios'))
        payload=json.dumps(dict(batch_id='SYN-HTTP-DEMO',actor='TEST')).encode()
        with self.assertRaises(HTTPError) as error:urlopen(Request(base+'/api/scenarios/demo',data=payload,headers={'Content-Type':'application/json'}))
        self.assertEqual(error.exception.code,403)
        headers={'Content-Type':'application/json','X-Portfolio-Token':boot['token']}
        receipt=json.load(urlopen(Request(base+'/api/scenarios/demo',data=payload,headers=headers)));self.assertEqual(len(receipt['runs']),44)
        fetched=json.load(urlopen(base+'/api/scenarios/demo/SYN-HTTP-DEMO'));self.assertFalse(fetched['execution_authorized'])
        cli_db=Path(self.tmp.name)/'cli.sqlite3'
        result=subprocess.run([sys.executable,'-m','civic_portfolio','--db',str(cli_db),'demo-scenarios','--batch-id','SYN-CLI-DEMO','--actor','TEST'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(len(json.loads(result.stdout)['runs']),44)
