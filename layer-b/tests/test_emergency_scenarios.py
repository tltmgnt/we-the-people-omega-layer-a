import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import urlopen
from civic_portfolio.scenarios import Scenarios,EMERGENCY_STAGES
from civic_portfolio.store import Store,Conflict
from civic_portfolio.__main__ import server

class EmergencyScenarioTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name)/'db.sqlite3');self.lab=Scenarios(self.store)
        self.lab.create(dict(run_id='SYN-EXERCISE',workflow='emergency',label='Fictional readiness rehearsal',start_at='2026-01-01T00:00:00Z',actor='OPERATOR',note='No live operations'))
    def command(self,action,actor='OPERATOR',**params):
        return self.lab.command('SYN-EXERCISE',dict(version=self.lab.run('SYN-EXERCISE')['version'],action=action,parameters=params,actor=actor,note='Fictional exercise evidence'))
    def readiness(self):
        self.command('STEP',actor='READINESS RECORDER',stage='READINESS_RECORDED',minutes=60)
        self.command('STEP',stage='READINESS_REVIEW',minutes=60)
    def corrections(self):
        self.readiness();self.command('REVIEW',actor='CHECKER',passed=True)
        self.command('STEP',stage='EXERCISE_STARTED',minutes=60)
        self.command('STEP',stage='RESPONSE_RECORDED',minutes=15)
        self.command('STEP',actor='AFTER ACTION RECORDER',stage='AFTER_ACTION_RECORDED',minutes=60)
        self.command('STEP',actor='CORRECTION RECORDER',stage='CORRECTION_RECORDED',minutes=60)
        self.command('STEP',stage='CORRECTION_REVIEW',minutes=60)
    def test_every_state_presets_replay_both_gate_checks(self):
        for stage in EMERGENCY_STAGES:
            run=self.command('PRESET',stage=stage,quality='PASS' if stage=='CLOSED' else 'UNREVIEWED')
            self.assertEqual(run['state']['stage'],stage)
            for a,b in zip(run['state']['path'],run['state']['path'][1:]):self.assertIn(b['stage'],EMERGENCY_STAGES[a['stage']])
            if stage=='CLOSED':
                reviews=run['state']['reviews']
                self.assertEqual([r['stage'] for r in reviews],['READINESS_REVIEW','CORRECTION_REVIEW'])
                self.assertTrue(all(r['passed'] for r in reviews))
            self.assertFalse(run['execution_authorized'])
    def test_readiness_gate_and_distinct_recorder(self):
        self.readiness()
        with self.assertRaises(ValueError):self.command('STEP',stage='EXERCISE_STARTED',minutes=60)
        with self.assertRaises(ValueError):self.command('REVIEW',actor='READINESS RECORDER',passed=True)
        self.command('REVIEW',actor='CHECKER',passed=False)
        self.assertNotIn('EXERCISE_STARTED',self.lab.run('SYN-EXERCISE')['controls']['next_stages'])
        self.command('REVIEW',actor='CHECKER',passed=True);self.command('STEP',stage='EXERCISE_STARTED',minutes=60)
        self.assertFalse(self.lab.report('SYN-EXERCISE')['live_dispatch_enabled'])
    def test_readiness_revision_invalidates_old_check(self):
        self.readiness();self.command('REVIEW',actor='CHECKER',passed=True)
        self.command('STEP',stage='READINESS_RECORDED',minutes=10);self.command('STEP',stage='READINESS_REVIEW',minutes=10)
        with self.assertRaises(ValueError):self.command('STEP',stage='EXERCISE_STARTED',minutes=1)
        self.assertEqual(self.lab.report('SYN-EXERCISE')['readiness_revisions'],1)
    def test_correction_gate_checks_both_recorders(self):
        self.corrections()
        with self.assertRaises(ValueError):self.command('STEP',stage='CLOSED',minutes=60)
        for actor in ['AFTER ACTION RECORDER','CORRECTION RECORDER']:
            with self.assertRaises(ValueError):self.command('REVIEW',actor=actor,passed=True)
        self.command('REVIEW',actor='CHECKER',passed=True);self.command('STEP',stage='CLOSED',minutes=60)
        report=self.lab.report('SYN-EXERCISE');self.assertEqual(report['exercise_response_minutes'],15)
        self.assertEqual(report['completion_elapsed_minutes'],435);self.assertFalse(report['operational_readiness_certified'])
    def test_correction_revision_requires_fresh_check(self):
        self.corrections();self.command('REVIEW',actor='CHECKER',passed=True)
        self.command('STEP',stage='CORRECTION_RECORDED',minutes=10);self.command('STEP',stage='CORRECTION_REVIEW',minutes=10)
        with self.assertRaises(ValueError):self.command('STEP',stage='CLOSED',minutes=1)
        self.assertEqual(self.lab.report('SYN-EXERCISE')['correction_revisions'],1)
        self.command('REVIEW',actor='CHECKER',passed=False)
        with self.assertRaises(ValueError):self.command('STEP',stage='CLOSED',minutes=1)
    def test_pause_stop_abort_and_cancel(self):
        self.readiness();self.command('PAUSE');self.command('TICK',minutes=30)
        with self.assertRaises(ValueError):self.command('REVIEW',actor='CHECKER',passed=True)
        self.command('STOP');self.command('RESUME');self.command('REVIEW',actor='CHECKER',passed=True)
        self.command('STEP',stage='EXERCISE_STARTED',minutes=1);self.command('STEP',stage='ABORTED',minutes=1)
        self.assertIsNone(self.lab.report('SYN-EXERCISE')['completion_elapsed_minutes'])
        with self.assertRaises(ValueError):self.command('RESUME')
        self.command('PRESET',stage='DESIGNED',quality='UNREVIEWED');self.command('STEP',stage='CANCELLED',minutes=1)
        self.assertIsNone(self.lab.report('SYN-EXERCISE')['exercise_response_minutes'])
    def test_restore_reproduces_checked_exercise_revision(self):
        self.readiness();self.command('REVIEW',actor='CHECKER',passed=True)
        before=self.lab.run('SYN-EXERCISE');seq=before['history'][-1]['sequence']
        self.command('PRESET',stage='DESIGNED',quality='UNREVIEWED');self.command('RESTORE',sequence=seq)
        self.assertEqual(self.lab.run('SYN-EXERCISE')['state'],before['state'])
        self.command('STEP',stage='EXERCISE_STARTED',minutes=60)
        self.assertFalse(self.lab.report('SYN-EXERCISE')['operational_readiness_certified'])
    def test_invalid_commands_are_atomic(self):
        before=self.lab.run('SYN-EXERCISE')
        for stage,quality in [('CLOSED','FAIL'),('CLOSED','UNREVIEWED'),('SERVICE_STARTED','UNREVIEWED'),('EXERCISE_STARTED','PASS')]:
            with self.assertRaises(ValueError):self.command('PRESET',stage=stage,quality=quality)
        with self.assertRaises(ValueError):self.command('STEP',stage='EXERCISE_STARTED',minutes=1)
        self.assertEqual(self.lab.run('SYN-EXERCISE'),before)
    def test_stale_version_backup_and_isolation(self):
        self.readiness();payload=dict(version=self.lab.run('SYN-EXERCISE')['version'],action='REVIEW',parameters=dict(passed=True),actor='CHECKER',note='Fictional readiness check')
        self.lab.command('SYN-EXERCISE',payload)
        with self.assertRaises(Conflict):self.lab.command('SYN-EXERCISE',payload)
        target=Path(self.tmp.name)/'backup.sqlite3';self.store.backup(target)
        self.assertEqual(Scenarios(Store(target)).run('SYN-EXERCISE'),self.lab.run('SYN-EXERCISE'))
        self.assertFalse(self.store.project('022')['execution_authorized'])
    def test_api_is_explicitly_exercise_only(self):
        app=server(self.store,0);thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
        self.addCleanup(app.server_close);self.addCleanup(thread.join,2);self.addCleanup(app.shutdown)
        base='http://127.0.0.1:'+str(app.server_port);boot=json.load(urlopen(base+'/api/scenarios'))
        self.assertEqual(set(boot['workflows']['emergency']['stages']),set(EMERGENCY_STAGES))
        report=json.load(urlopen(base+'/api/scenarios/SYN-EXERCISE/report'))
        self.assertFalse(report['live_dispatch_enabled']);self.assertFalse(report['operational_readiness_certified'])
        self.assertFalse(report['execution_authorized']);self.assertIsNone(report['exercise_response_minutes'])
