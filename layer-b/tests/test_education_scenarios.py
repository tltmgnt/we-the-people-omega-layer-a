from pathlib import Path
import tempfile
import unittest
from civic_portfolio.scenarios import Scenarios,EDUCATION_STAGES
from civic_portfolio.store import Store,Conflict

class EducationScenarioTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name)/'db.sqlite3');self.lab=Scenarios(self.store)
        self.lab.create(dict(run_id='SYN-EDUCATION',workflow='education',label='Fictional learning-service access',start_at='2026-01-01T00:00:00Z',actor='OPERATOR',note='Synthetic only'))
    def command(self,action,actor='OPERATOR',**params):
        return self.lab.command('SYN-EDUCATION',dict(version=self.lab.run('SYN-EDUCATION')['version'],action=action,parameters=params,actor=actor,note='Fictional access/continuity evidence'))
    def continuity(self):
        for stage,actor in [('ACCESS_REVIEW','OPERATOR'),('SERVICE_OFFERED','OPERATOR'),('SERVICE_STARTED','SERVICE RECORDER'),('FOLLOW_UP_RECORDED','FOLLOWUP RECORDER'),('CONTINUITY_REVIEW','OPERATOR')]:
            self.command('STEP',actor=actor,stage=stage,minutes=60)
    def test_every_state_and_explicit_closed_preset(self):
        for stage in EDUCATION_STAGES:
            run=self.command('PRESET',stage=stage,quality='PASS' if stage=='CLOSED' else 'UNREVIEWED')
            self.assertEqual(run['state']['stage'],stage);self.assertEqual(run['workflow'],'education')
            for a,b in zip(run['state']['path'],run['state']['path'][1:]):self.assertIn(b['stage'],EDUCATION_STAGES[a['stage']])
            if stage=='CLOSED':
                self.assertEqual(run['state']['quality'],'PASS')
                self.assertIn('fictional continuity check',run['state']['reviews'][-1]['note'])
            self.assertFalse(run['execution_authorized'])
    def test_check_is_distinct_from_both_recorders(self):
        self.continuity()
        for actor in ['SERVICE RECORDER','FOLLOWUP RECORDER']:
            with self.assertRaises(ValueError):self.command('REVIEW',actor=actor,passed=True)
        with self.assertRaises(ValueError):self.command('STEP',stage='CLOSED',minutes=60)
        self.command('REVIEW',actor='CHECKER',passed=False)
        self.assertNotIn('CLOSED',self.lab.run('SYN-EDUCATION')['controls']['next_stages'])
        self.command('REVIEW',actor='CHECKER',passed=True);self.command('STEP',stage='CLOSED',minutes=60)
        report=self.lab.report('SYN-EDUCATION');self.assertEqual(report['completion_elapsed_minutes'],360)
        self.assertEqual(report['service_start_elapsed_minutes'],180);self.assertFalse(report['learning_outcomes_assessed'])
    def test_interruption_and_new_service_invalidate_check(self):
        self.continuity();self.command('REVIEW',actor='CHECKER',passed=True)
        for stage in ['INTERRUPTED','SERVICE_OFFERED','SERVICE_STARTED','FOLLOW_UP_RECORDED','CONTINUITY_REVIEW']:
            self.command('STEP',stage=stage,minutes=60)
        self.assertEqual(self.lab.run('SYN-EDUCATION')['state']['quality'],'UNREVIEWED')
        with self.assertRaises(ValueError):self.command('STEP',stage='CLOSED',minutes=60)
        self.command('REVIEW',actor='CHECKER',passed=True);self.command('STEP',stage='CLOSED',minutes=60)
        self.assertEqual(self.lab.report('SYN-EDUCATION')['service_interruptions'],1)
        self.assertEqual(len(self.lab.run('SYN-EDUCATION')['state']['reviews']),2)
    def test_pause_stop_manual_clock_and_review_hold(self):
        self.continuity();self.command('PAUSE')
        with self.assertRaises(ValueError):self.command('REVIEW',actor='CHECKER',passed=True)
        self.command('TICK',minutes=30);self.command('STOP')
        with self.assertRaises(ValueError):self.command('STEP',stage='INTERRUPTED',minutes=5)
        self.command('RESUME');self.command('REVIEW',actor='CHECKER',passed=True)
        self.assertEqual(self.lab.report('SYN-EDUCATION')['clock_minutes'],330)
    def test_withdrawal_is_not_completion_or_learning(self):
        self.command('STEP',stage='WITHDRAWN',minutes=15)
        report=self.lab.report('SYN-EDUCATION')
        self.assertEqual(report['execution'],'COMPLETED');self.assertIsNone(report['completion_elapsed_minutes'])
        self.assertIsNone(report['service_start_elapsed_minutes']);self.assertIsNone(report['open_age_minutes'])
        self.assertFalse(report['learning_outcomes_assessed'])
        with self.assertRaises(ValueError):self.command('RESUME')
    def test_snapshot_restore_preserves_exact_continuity_revision(self):
        self.continuity();self.command('REVIEW',actor='CHECKER',passed=True)
        before=self.lab.run('SYN-EDUCATION');seq=before['history'][-1]['sequence']
        self.command('PRESET',stage='REQUEST_RECORDED',quality='UNREVIEWED');self.command('RESTORE',sequence=seq)
        self.assertEqual(self.lab.run('SYN-EDUCATION')['state'],before['state'])
        self.command('STEP',stage='CLOSED',minutes=60)
        self.assertEqual(self.lab.run('SYN-EDUCATION')['state']['stage'],'CLOSED')
    def test_invalid_inputs_and_cross_workflow_states_are_atomic(self):
        before=self.lab.run('SYN-EDUCATION')
        for stage,quality in [('CLOSED','FAIL'),('CLOSED','UNREVIEWED'),('CONTRACT_RECORDED','UNREVIEWED'),('REQUEST_RECORDED','PASS')]:
            with self.assertRaises(ValueError):self.command('PRESET',stage=stage,quality=quality)
        with self.assertRaises(ValueError):self.command('STEP',stage='SERVICE_STARTED',minutes=1)
        with self.assertRaises(ValueError):self.command('REVIEW',actor='CHECKER',passed=True)
        self.assertEqual(self.lab.run('SYN-EDUCATION'),before)
    def test_stale_commands_and_backup_isolation(self):
        self.continuity();payload=dict(version=self.lab.run('SYN-EDUCATION')['version'],action='REVIEW',parameters=dict(passed=True),actor='CHECKER',note='Fictional continuity check')
        self.lab.command('SYN-EDUCATION',payload)
        with self.assertRaises(Conflict):self.lab.command('SYN-EDUCATION',payload)
        target=Path(self.tmp.name)/'backup.sqlite3';self.store.backup(target)
        self.assertEqual(Scenarios(Store(target)).run('SYN-EDUCATION'),self.lab.run('SYN-EDUCATION'))
        self.assertFalse(self.store.project('020')['execution_authorized'])
