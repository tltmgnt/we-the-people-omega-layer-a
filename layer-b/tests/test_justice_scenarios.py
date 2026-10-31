import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import urlopen
from civic_portfolio.scenarios import Scenarios,JUSTICE_STAGES
from civic_portfolio.store import Store,Conflict
from civic_portfolio.__main__ import server

class JusticeScenarioTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name)/'db.sqlite3');self.lab=Scenarios(self.store)
        self.lab.create(dict(run_id='SYN-JUSTICE-CONTROL',workflow='justice',label='Fictional caseflow',start_at='2026-01-01T00:00:00Z',actor='OPERATOR',note='No actual justice records'))
    def command(self,action,actor='OPERATOR',**params):
        return self.lab.command('SYN-JUSTICE-CONTROL',dict(version=self.lab.run('SYN-JUSTICE-CONTROL')['version'],action=action,parameters=params,actor=actor,note='Fictional record/process check'))
    def notice(self):
        for stage,actor in [('FILED','FILING RECORDER'),('NOTICE_RECORDED','NOTICE RECORDER'),('NOTICE_REVIEW','OPERATOR')]:
            self.command('STEP',actor=actor,stage=stage,minutes=60)
    def decision(self):
        self.notice();self.command('REVIEW',actor='CHECKER',passed=True)
        self.command('STEP',stage='HEARING_RECORDED',minutes=60)
        self.command('STEP',actor='DECISION RECORDER',stage='DECISION_RECORDED',minutes=60)
    def remedy(self):
        self.decision();self.command('STEP',actor='REMEDY RECORDER',stage='REMEDY_RECORDED',minutes=60)
        self.command('STEP',stage='REMEDY_REVIEW',minutes=60)
    def test_every_state_has_valid_preset_and_fixed_holds(self):
        for stage in JUSTICE_STAGES:
            run=self.command('PRESET',stage=stage,quality='PASS' if stage=='CLOSED' else 'UNREVIEWED')
            self.assertEqual(run['state']['stage'],stage)
            for a,b in zip(run['state']['path'],run['state']['path'][1:]):self.assertIn(b['stage'],JUSTICE_STAGES[a['stage']])
            if stage=='CLOSED':
                self.assertEqual([r['stage'] for r in run['state']['reviews']],['NOTICE_REVIEW','REMEDY_REVIEW'])
            self.assertFalse(run['execution_authorized'])
    def test_notice_requires_separate_current_record_check(self):
        self.notice()
        for actor in ['FILING RECORDER','NOTICE RECORDER']:
            with self.assertRaises(ValueError):self.command('REVIEW',actor=actor,passed=True)
        with self.assertRaises(ValueError):self.command('STEP',stage='HEARING_RECORDED',minutes=60)
        self.command('REVIEW',actor='CHECKER',passed=False)
        self.assertNotIn('HEARING_RECORDED',self.lab.run('SYN-JUSTICE-CONTROL')['controls']['next_stages'])
        self.command('REVIEW',actor='CHECKER',passed=True)
        self.command('STEP',stage='NOTICE_RECORDED',minutes=10);self.command('STEP',stage='NOTICE_REVIEW',minutes=10)
        with self.assertRaises(ValueError):self.command('STEP',stage='HEARING_RECORDED',minutes=60)
    def test_remand_requires_new_notice_and_censors_prior_decision(self):
        self.decision();self.assertEqual(self.lab.report('SYN-JUSTICE-CONTROL')['filing_to_latest_decision_minutes'],240)
        for stage in ['REVIEW_REQUESTED','REMANDED','NOTICE_RECORDED','NOTICE_REVIEW']:self.command('STEP',stage=stage,minutes=60)
        report=self.lab.report('SYN-JUSTICE-CONTROL');self.assertTrue(report['justice_review_pending'])
        self.assertIsNone(report['filing_to_latest_decision_minutes']);self.assertEqual(report['remand_cycles'],1)
        with self.assertRaises(ValueError):self.command('STEP',stage='HEARING_RECORDED',minutes=60)
        self.command('REVIEW',actor='CHECKER',passed=True);self.command('STEP',stage='HEARING_RECORDED',minutes=60)
        self.command('STEP',stage='DECISION_RECORDED',minutes=60)
        self.assertEqual(self.lab.report('SYN-JUSTICE-CONTROL')['filing_to_latest_decision_minutes'],600)
    def test_remedy_revision_needs_separate_check(self):
        self.remedy()
        for actor in ['DECISION RECORDER','REMEDY RECORDER']:
            with self.assertRaises(ValueError):self.command('REVIEW',actor=actor,passed=True)
        self.command('REVIEW',actor='CHECKER',passed=True)
        self.command('STEP',stage='REMEDY_RECORDED',minutes=60);self.command('STEP',stage='REMEDY_REVIEW',minutes=60)
        with self.assertRaises(ValueError):self.command('STEP',stage='CLOSED',minutes=60)
        self.command('REVIEW',actor='CHECKER',passed=True);self.command('STEP',stage='CLOSED',minutes=60)
        report=self.lab.report('SYN-JUSTICE-CONTROL');self.assertEqual(report['closure_path'],'REMEDY_RECORD')
        self.assertFalse(report['remedy_effectiveness_verified']);self.assertFalse(report['judicial_outcomes_assessed'])
    def test_reentry_check_and_changed_handoff(self):
        self.decision()
        for stage,actor in [('REENTRY_HANDOFF','HANDOFF RECORDER'),('FOLLOW_UP_RECORDED','FOLLOWUP RECORDER'),('CONTINUITY_REVIEW','OPERATOR')]:
            self.command('STEP',actor=actor,stage=stage,minutes=60)
        for actor in ['HANDOFF RECORDER','FOLLOWUP RECORDER']:
            with self.assertRaises(ValueError):self.command('REVIEW',actor=actor,passed=True)
        self.command('REVIEW',actor='CHECKER',passed=True)
        for stage in ['REENTRY_HANDOFF','FOLLOW_UP_RECORDED','CONTINUITY_REVIEW']:self.command('STEP',stage=stage,minutes=60)
        with self.assertRaises(ValueError):self.command('STEP',stage='CLOSED',minutes=60)
        self.command('REVIEW',actor='CHECKER',passed=True);self.command('STEP',stage='CLOSED',minutes=60)
        report=self.lab.report('SYN-JUSTICE-CONTROL');self.assertEqual(report['closure_path'],'REENTRY_RECORD');self.assertFalse(report['recidivism_assessed'])
    def test_pause_stop_withdrawal_and_clock(self):
        self.notice();self.command('PAUSE');self.command('TICK',minutes=30)
        with self.assertRaises(ValueError):self.command('REVIEW',actor='CHECKER',passed=True)
        self.command('STOP');self.command('RESUME');self.command('STEP',stage='WITHDRAWN',minutes=10)
        report=self.lab.report('SYN-JUSTICE-CONTROL');self.assertIsNone(report['completion_elapsed_minutes'])
        self.assertIsNone(report['filing_to_latest_decision_minutes'])
        with self.assertRaises(ValueError):self.command('RESUME')
    def test_restore_reproduces_snapshot_not_judicial_authority(self):
        self.notice();self.command('REVIEW',actor='CHECKER',passed=True)
        before=self.lab.run('SYN-JUSTICE-CONTROL');seq=before['history'][-1]['sequence']
        self.command('PRESET',stage='ACCESS_REQUESTED',quality='UNREVIEWED');self.command('RESTORE',sequence=seq)
        self.assertEqual(self.lab.run('SYN-JUSTICE-CONTROL')['state'],before['state'])
        self.command('STEP',stage='HEARING_RECORDED',minutes=60)
        self.assertFalse(self.lab.report('SYN-JUSTICE-CONTROL')['execution_authorized'])
    def test_invalid_cross_workflow_commands_are_atomic(self):
        before=self.lab.run('SYN-JUSTICE-CONTROL')
        for stage,quality in [('CLOSED','FAIL'),('CLOSED','UNREVIEWED'),('EXERCISE_STARTED','UNREVIEWED'),('DECISION_RECORDED','PASS')]:
            with self.assertRaises(ValueError):self.command('PRESET',stage=stage,quality=quality)
        with self.assertRaises(ValueError):self.command('STEP',stage='DECISION_RECORDED',minutes=1)
        self.assertEqual(self.lab.run('SYN-JUSTICE-CONTROL'),before)
    def test_stale_writes_backup_and_observatory_isolation(self):
        self.notice();payload=dict(version=self.lab.run('SYN-JUSTICE-CONTROL')['version'],action='REVIEW',parameters=dict(passed=True),actor='CHECKER',note='Fictional notice check')
        self.lab.command('SYN-JUSTICE-CONTROL',payload)
        with self.assertRaises(Conflict):self.lab.command('SYN-JUSTICE-CONTROL',payload)
        target=Path(self.tmp.name)/'backup.sqlite3';self.store.backup(target)
        self.assertEqual(Scenarios(Store(target)).run('SYN-JUSTICE-CONTROL'),self.lab.run('SYN-JUSTICE-CONTROL'))
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM justice_pilots').fetchone()[0],0)
        self.assertFalse(self.store.project('023')['execution_authorized'])
    def test_api_remains_explicitly_nonjudicial(self):
        app=server(self.store,0);thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
        self.addCleanup(app.server_close);self.addCleanup(thread.join,2);self.addCleanup(app.shutdown)
        base='http://127.0.0.1:'+str(app.server_port);boot=json.load(urlopen(base+'/api/scenarios'))
        self.assertEqual(set(boot['workflows']['justice']['stages']),set(JUSTICE_STAGES))
        report=json.load(urlopen(base+'/api/scenarios/SYN-JUSTICE-CONTROL/report'))
        self.assertFalse(report['judicial_outcomes_assessed']);self.assertFalse(report['remedy_effectiveness_verified'])
        self.assertFalse(report['recidivism_assessed']);self.assertFalse(report['execution_authorized'])
