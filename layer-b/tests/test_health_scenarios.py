import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import urlopen
from civic_portfolio.scenarios import Scenarios,HEALTH_STAGES
from civic_portfolio.store import Store,Conflict
from civic_portfolio.__main__ import server

class HealthScenarioTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name)/'db.sqlite3');self.lab=Scenarios(self.store)
        self.lab.create(dict(run_id='SYN-REFERRAL',workflow='health',label='Fictional referral',start_at='2026-01-01T00:00:00Z',actor='OPERATOR',note='No actual health information'))
    def command(self,action,actor='OPERATOR',**params):
        return self.lab.command('SYN-REFERRAL',dict(version=self.lab.run('SYN-REFERRAL')['version'],action=action,parameters=params,actor=actor,note='Fictional consent/referral/continuity record'))
    def continuity(self):
        for stage,actor in [('CONSENT_RECORDED','OPERATOR'),('REFERRAL_RECORDED','OPERATOR'),('WAITING','OPERATOR'),('SERVICE_STARTED','SERVICE RECORDER'),('FOLLOW_UP_RECORDED','FOLLOWUP RECORDER'),('CONTINUITY_REVIEW','OPERATOR')]:
            self.command('STEP',actor=actor,stage=stage,minutes=60)
    def test_every_state_has_valid_preset_and_fixed_holds(self):
        for stage in HEALTH_STAGES:
            run=self.command('PRESET',stage=stage,quality='PASS' if stage=='CLOSED' else 'UNREVIEWED')
            self.assertEqual(run['state']['stage'],stage);self.assertFalse(run['execution_authorized'])
            for a,b in zip(run['state']['path'],run['state']['path'][1:]):self.assertIn(b['stage'],HEALTH_STAGES[a['stage']])
            if stage=='CLOSED':self.assertIn('fictional health-service continuity check',run['state']['reviews'][-1]['note'])
    def test_consent_milestone_and_withdrawal_are_not_authority(self):
        with self.assertRaises(ValueError):self.command('STEP',stage='REFERRAL_RECORDED',minutes=60)
        self.command('STEP',stage='CONSENT_RECORDED',minutes=60);self.command('STEP',stage='CONSENT_WITHDRAWN',minutes=60)
        report=self.lab.report('SYN-REFERRAL');self.assertEqual(report['consent_status'],'WITHDRAWAL_RECORDED')
        self.assertIsNone(report['completion_elapsed_minutes']);self.assertFalse(report['clinical_outcomes_assessed'])
        with self.assertRaises(ValueError):self.command('STEP',stage='REFERRAL_RECORDED',minutes=60)
        with self.assertRaises(ValueError):self.command('RESUME')
    def test_distinct_service_and_followup_checker_and_current_check(self):
        self.continuity()
        for actor in ['SERVICE RECORDER','FOLLOWUP RECORDER']:
            with self.assertRaises(ValueError):self.command('REVIEW',actor=actor,passed=True)
        self.command('REVIEW',actor='CHECKER',passed=False)
        with self.assertRaises(ValueError):self.command('STEP',stage='CLOSED',minutes=60)
        self.command('REVIEW',actor='CHECKER',passed=True);self.command('STEP',stage='CLOSED',minutes=60)
        report=self.lab.report('SYN-REFERRAL');self.assertEqual(report['completion_elapsed_minutes'],420)
        self.assertEqual(report['service_start_elapsed_minutes'],240);self.assertFalse(report['execution_authorized'])
    def test_interruption_repeat_referral_invalidates_continuity(self):
        self.continuity();self.command('REVIEW',actor='CHECKER',passed=True)
        for stage in ['INTERRUPTED','REFERRAL_RECORDED','WAITING','SERVICE_STARTED','FOLLOW_UP_RECORDED','CONTINUITY_REVIEW']:
            self.command('STEP',stage=stage,minutes=60)
        with self.assertRaises(ValueError):self.command('STEP',stage='CLOSED',minutes=60)
        self.command('REVIEW',actor='CHECKER',passed=True);self.command('STEP',stage='CLOSED',minutes=60)
        report=self.lab.report('SYN-REFERRAL');self.assertEqual(report['service_interruptions'],1);self.assertEqual(report['repeat_referrals'],1)
        self.assertEqual(report['referral_wait_minutes'],120)
    def test_waiting_clock_pause_and_decline(self):
        for stage in ['CONSENT_RECORDED','REFERRAL_RECORDED','WAITING']:self.command('STEP',stage=stage,minutes=60)
        self.command('PAUSE');self.command('TICK',minutes=30)
        with self.assertRaises(ValueError):self.command('STEP',stage='SERVICE_STARTED',minutes=60)
        self.command('STOP');self.command('RESUME');self.command('STEP',stage='DECLINED',minutes=60)
        report=self.lab.report('SYN-REFERRAL');self.assertEqual(report['referral_wait_minutes'],90)
        self.assertIsNone(report['service_start_elapsed_minutes']);self.assertIsNone(report['completion_elapsed_minutes'])
    def test_restore_is_exact_synthetic_branch_not_renewed_real_consent(self):
        self.continuity();self.command('REVIEW',actor='CHECKER',passed=True)
        before=self.lab.run('SYN-REFERRAL');seq=before['history'][-1]['sequence']
        self.command('STEP',stage='CONSENT_WITHDRAWN',minutes=60);self.command('RESTORE',sequence=seq)
        self.assertEqual(self.lab.run('SYN-REFERRAL')['state'],before['state'])
        self.assertEqual(self.lab.report('SYN-REFERRAL')['consent_status'],'ASSERTED_ONLY')
        self.assertFalse(self.lab.report('SYN-REFERRAL')['execution_authorized'])
    def test_invalid_inputs_and_cross_workflow_presets_are_atomic(self):
        before=self.lab.run('SYN-REFERRAL')
        for stage,quality in [('CLOSED','FAIL'),('CLOSED','UNREVIEWED'),('DELIVERY_RECORDED','UNREVIEWED'),('CONSENT_RECORDED','PASS')]:
            with self.assertRaises(ValueError):self.command('PRESET',stage=stage,quality=quality)
        with self.assertRaises(ValueError):self.command('REVIEW',actor='CHECKER',passed=True)
        with self.assertRaises(ValueError):self.command('TICK',minutes=True)
        self.assertEqual(self.lab.run('SYN-REFERRAL'),before)
    def test_stale_version_backup_and_project_isolation(self):
        self.continuity();payload=dict(version=self.lab.run('SYN-REFERRAL')['version'],action='REVIEW',parameters=dict(passed=True),actor='CHECKER',note='Synthetic check')
        self.lab.command('SYN-REFERRAL',payload)
        with self.assertRaises(Conflict):self.lab.command('SYN-REFERRAL',payload)
        target=Path(self.tmp.name)/'backup.sqlite3';self.store.backup(target)
        self.assertEqual(Scenarios(Store(target)).run('SYN-REFERRAL'),self.lab.run('SYN-REFERRAL'))
        self.assertFalse(self.store.project('021')['execution_authorized'])
    def test_http_catalog_and_report_are_explicitly_nonclinical(self):
        app=server(self.store,0);thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
        self.addCleanup(app.server_close);self.addCleanup(thread.join,2);self.addCleanup(app.shutdown)
        base='http://127.0.0.1:'+str(app.server_port);boot=json.load(urlopen(base+'/api/scenarios'))
        self.assertEqual(set(boot['workflows']['health']['stages']),set(HEALTH_STAGES))
        report=json.load(urlopen(base+'/api/scenarios/SYN-REFERRAL/report'))
        self.assertFalse(report['clinical_outcomes_assessed']);self.assertFalse(report['execution_authorized'])
        self.assertEqual(report['consent_status'],'NOT_RECORDED')
