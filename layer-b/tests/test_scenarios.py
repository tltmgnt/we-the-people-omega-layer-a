import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request,urlopen
from civic_portfolio.scenarios import Scenarios,route,fingerprint
from civic_portfolio.permits import STAGES
from civic_portfolio.store import Store,Conflict
from civic_portfolio.__main__ import server

class ScenarioTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name)/'test.sqlite3');self.lab=Scenarios(self.store)
        self.lab.create(dict(run_id='SYN-DEMO',label='Fictional walkthrough',start_at='2026-01-01T00:00:00Z',actor='TEST',note='Synthetic only'))
    def command(self,action,**parameters):
        return self.lab.command('SYN-DEMO',dict(version=self.lab.run('SYN-DEMO')['version'],action=action,parameters=parameters,actor='TEST',note='Fictional control action'))
    def test_every_stage_preset_uses_valid_edges(self):
        for target in STAGES:
            run=self.command('PRESET',stage=target,quality='UNREVIEWED')
            self.assertEqual(run['state']['stage'],target)
            path=run['state']['path']
            for a,b in zip(path,path[1:]):self.assertIn(b['stage'],STAGES[a['stage']])
            self.assertEqual(run['state_sha256'],fingerprint(run['state']))
            self.assertFalse(run['execution_authorized'])
        self.assertEqual(len(self.lab.run('SYN-DEMO')['history']),7)
    def test_pause_stop_resume_controls(self):
        self.command('PAUSE')
        with self.assertRaises(ValueError):self.command('STEP',stage='IN_REVIEW',minutes=60)
        self.command('TICK',minutes=30);self.assertEqual(self.lab.run('SYN-DEMO')['state']['clock_minutes'],30)
        self.command('STOP');self.assertFalse(self.lab.run('SYN-DEMO')['controls']['step'])
        self.command('RESUME');self.command('STEP',stage='IN_REVIEW',minutes=60)
        self.assertEqual(self.lab.run('SYN-DEMO')['state']['clock_minutes'],90)
    def test_correction_loop_and_timing(self):
        for stage in ['IN_REVIEW','AWAITING_CORRECTION','IN_REVIEW','INSPECTION','DECIDED']:self.command('STEP',stage=stage,minutes=60)
        report=self.lab.report('SYN-DEMO');self.assertEqual(report['decision_elapsed_minutes'],300)
        self.assertEqual(report['correction_cycles'],1);self.assertEqual(report['stage_minutes']['IN_REVIEW'],120)
        self.command('TICK',minutes=60);self.assertEqual(self.lab.report('SYN-DEMO')['decision_elapsed_minutes'],300)
    def test_terminal_states_are_inspectable_not_resumable(self):
        for stage in ['DECIDED','WITHDRAWN']:
            self.command('PRESET',stage=stage,quality='UNREVIEWED')
            run=self.lab.run('SYN-DEMO');self.assertEqual(run['state']['execution'],'COMPLETED');self.assertEqual(run['controls']['next_stages'],[])
            with self.assertRaises(ValueError):self.command('RESUME')
            with self.assertRaises(ValueError):self.command('STEP',stage='IN_REVIEW',minutes=60)
    def test_quality_outcomes_and_review_history(self):
        with self.assertRaises(ValueError):self.command('REVIEW',passed=True)
        self.command('PRESET',stage='DECIDED',quality='FAIL')
        self.command('REVIEW',passed=True);self.assertEqual(self.lab.run('SYN-DEMO')['state']['quality'],'PASS')
        self.command('REVIEW',passed=False);self.assertEqual(len(self.lab.run('SYN-DEMO')['state']['reviews']),3)
        with self.assertRaises(ValueError):self.command('PRESET',stage='RECEIVED',quality='PASS')
    def test_reset_and_restore_preserve_history(self):
        self.command('STEP',stage='IN_REVIEW',minutes=15);checkpoint=self.lab.run('SYN-DEMO')['state']
        self.command('PRESET',stage='DECIDED',quality='PASS');self.command('PRESET',stage='RECEIVED',quality='UNREVIEWED')
        restored=self.command('RESTORE',sequence=2);self.assertEqual(restored['state'],checkpoint)
        self.assertEqual(restored['history'][-1]['restored_from'],2);self.assertEqual(len(restored['history']),5)
        self.command('STEP',stage='WITHDRAWN',minutes=5);self.assertEqual(len(self.lab.run('SYN-DEMO')['history']),6)
    def test_invalid_inputs_are_atomic(self):
        before=self.lab.run('SYN-DEMO')
        for action,params in [('TICK',dict(minutes=True)),('TICK',dict(minutes=-1)),('STEP',dict(stage='DECIDED',minutes=60)),('RESTORE',dict(sequence=999)),('PRESET',dict(stage=[],quality='UNREVIEWED')),('REVIEW',dict(passed='yes'))]:
            with self.assertRaises(ValueError):self.command(action,**params)
        self.assertEqual(self.lab.run('SYN-DEMO'),before)
    def test_stale_version_and_state_hashes(self):
        payload=dict(version=1,action='PAUSE',parameters={},actor='TEST',note='Fictional action')
        self.lab.command('SYN-DEMO',payload)
        with self.assertRaises(Conflict):self.lab.command('SYN-DEMO',payload)
        with self.assertRaises(ValueError):self.lab.command('SYN-DEMO',{**payload,'version':True})
        run=self.lab.run('SYN-DEMO');self.assertEqual(run['history'][1]['before_sha256'],run['history'][0]['state_sha256'])
    def test_clock_calendar_limits(self):
        self.lab.create(dict(run_id='SYN-LATE',label='Calendar limit test',start_at='9999-12-31T23:00:00Z',actor='TEST',note='Boundary'))
        with self.assertRaises(ValueError):self.lab.command('SYN-LATE',dict(version=1,action='TICK',parameters=dict(minutes=60),actor='TEST',note='Overflow'))
        self.assertEqual(self.lab.run('SYN-LATE')['version'],1)
    def test_isolation_export_and_backup(self):
        self.command('PRESET',stage='DECIDED',quality='PASS')
        self.assertEqual(self.store.export()['synthetic_scenarios']['runs'][0]['id'],'SYN-DEMO')
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM permit_cases').fetchone()[0],0)
        self.assertFalse(self.store.project('009')['execution_authorized'])
        target=Path(self.tmp.name)/'backup.sqlite3';self.store.backup(target)
        self.assertEqual(Scenarios(Store(target)).run('SYN-DEMO'),self.lab.run('SYN-DEMO'))
    def test_http_controls_and_token(self):
        app=server(self.store,0);thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
        self.addCleanup(app.server_close);self.addCleanup(thread.join,2);self.addCleanup(app.shutdown)
        base='http://127.0.0.1:'+str(app.server_port)
        boot=json.load(urlopen(base+'/api/scenarios'));self.assertEqual(set(boot['stages']),set(STAGES))
        self.assertIn(b'Permit scenario control console',urlopen(base+'/scenarios').read())
        payload=dict(version=1,action='PAUSE',parameters={},actor='TEST',note='Fictional pause')
        with self.assertRaises(HTTPError) as error:urlopen(Request(base+'/api/scenarios/SYN-DEMO/commands',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'}))
        self.assertEqual(error.exception.code,403)
        headers={'Content-Type':'application/json','X-Portfolio-Token':boot['token']}
        run=json.load(urlopen(Request(base+'/api/scenarios/SYN-DEMO/commands',data=json.dumps(payload).encode(),headers=headers)))
        self.assertEqual(run['state']['execution'],'PAUSED')
        report=json.load(urlopen(base+'/api/scenarios/SYN-DEMO/report'));self.assertFalse(report['execution_authorized'])
