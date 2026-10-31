import json
from pathlib import Path
import tempfile
import unittest
from civic_portfolio.scenarios import Scenarios,PROCUREMENT_STAGES,route
from civic_portfolio.store import Store,Conflict

class ProcurementScenarioTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name)/'db.sqlite3');self.lab=Scenarios(self.store)
        self.lab.create(dict(run_id='SYN-CONTRACT',workflow='procurement',label='Fictional contract delivery',start_at='2026-01-01T00:00:00Z',actor='RECORDER',note='Synthetic only'))
    def command(self,action,actor='RECORDER',**params):
        return self.lab.command('SYN-CONTRACT',dict(version=self.lab.run('SYN-CONTRACT')['version'],action=action,parameters=params,actor=actor,note='Fictional delivery/check record'))
    def acceptance(self):
        for stage in ['SOLICITATION_RECORDED','EVALUATION_RECORDED','CONTRACT_RECORDED','DELIVERY_RECORDED','ACCEPTANCE_REVIEW']:
            self.command('STEP',stage=stage,minutes=60)
    def test_every_state_and_explicit_closed_preset_check(self):
        for stage in PROCUREMENT_STAGES:
            run=self.command('PRESET',stage=stage,quality='PASS' if stage=='CLOSED' else 'UNREVIEWED')
            self.assertEqual(run['workflow'],'procurement');self.assertEqual(run['state']['stage'],stage)
            for a,b in zip(run['state']['path'],run['state']['path'][1:]):self.assertIn(b['stage'],PROCUREMENT_STAGES[a['stage']])
            if stage=='CLOSED':
                self.assertEqual(run['state']['quality'],'PASS');self.assertTrue(run['state']['reviews'][-1]['passed'])
                self.assertIn('fictional acceptance',run['state']['reviews'][-1]['note'])
    def test_acceptance_gate_and_distinct_checker(self):
        self.acceptance();self.assertNotIn('CLOSED',self.lab.run('SYN-CONTRACT')['controls']['next_stages'])
        with self.assertRaises(ValueError):self.command('STEP',stage='CLOSED',minutes=60)
        with self.assertRaises(ValueError):self.command('REVIEW',passed=True)
        self.command('REVIEW',actor='CHECKER',passed=False)
        with self.assertRaises(ValueError):self.command('STEP',stage='CLOSED',minutes=60)
        self.command('REVIEW',actor='CHECKER',passed=True)
        self.command('STEP',stage='CLOSED',minutes=60)
        report=self.lab.report('SYN-CONTRACT');self.assertEqual(report['completion_elapsed_minutes'],360)
        self.assertIsNone(report['decision_elapsed_minutes']);self.assertFalse(report['execution_authorized'])
    def test_corrected_delivery_invalidates_previous_check(self):
        self.acceptance();self.command('REVIEW',actor='CHECKER',passed=True)
        self.command('STEP',stage='CORRECTION_REQUESTED',minutes=60)
        self.command('STEP',actor='NEW RECORDER',stage='DELIVERY_RECORDED',minutes=60)
        self.command('STEP',stage='ACCEPTANCE_REVIEW',minutes=60)
        self.assertEqual(self.lab.run('SYN-CONTRACT')['state']['quality'],'UNREVIEWED')
        with self.assertRaises(ValueError):self.command('STEP',stage='CLOSED',minutes=60)
        with self.assertRaises(ValueError):self.command('REVIEW',actor='NEW RECORDER',passed=True)
        self.command('REVIEW',actor='CHECKER',passed=True);self.command('STEP',stage='CLOSED',minutes=60)
        self.assertEqual(self.lab.report('SYN-CONTRACT')['correction_cycles'],1)
    def test_pause_stop_and_terminal_cancel(self):
        self.acceptance();self.command('PAUSE')
        with self.assertRaises(ValueError):self.command('REVIEW',actor='CHECKER',passed=True)
        self.command('TICK',minutes=30);self.command('STOP');self.command('RESUME')
        self.command('STEP',stage='CANCELLED',minutes=5)
        report=self.lab.report('SYN-CONTRACT');self.assertEqual(report['execution'],'COMPLETED')
        self.assertIsNone(report['completion_elapsed_minutes']);self.assertIsNone(report['open_age_minutes'])
        with self.assertRaises(ValueError):self.command('RESUME')
    def test_restore_copies_revision_bound_acceptance(self):
        self.acceptance();self.command('REVIEW',actor='CHECKER',passed=True)
        checkpoint=self.lab.run('SYN-CONTRACT');seq=checkpoint['history'][-1]['sequence']
        self.command('PRESET',stage='DRAFT',quality='UNREVIEWED')
        self.command('RESTORE',sequence=seq)
        self.assertEqual(self.lab.run('SYN-CONTRACT')['state'],checkpoint['state'])
        self.command('STEP',stage='CLOSED',minutes=60)
        self.assertEqual(self.lab.run('SYN-CONTRACT')['state']['stage'],'CLOSED')
    def test_presets_and_cross_workflow_states_reject_atomically(self):
        before=self.lab.run('SYN-CONTRACT')
        for stage,quality in [('CLOSED','UNREVIEWED'),('CLOSED','FAIL'),('DRAFT','PASS'),('DECIDED','PASS')]:
            with self.assertRaises(ValueError):self.command('PRESET',stage=stage,quality=quality)
        self.assertEqual(self.lab.run('SYN-CONTRACT'),before)
        with self.assertRaises(ValueError):self.command('STEP',stage='CONTRACT_RECORDED',minutes=60)
        with self.assertRaises(ValueError):self.lab.create(dict(run_id='SYN-BAD',workflow=[],label='Bad',start_at='2026-01-01T00:00:00Z',actor='TEST',note='Bad workflow'))
    def test_legacy_permit_body_defaults_without_rewriting_history(self):
        self.lab.create(dict(run_id='SYN-OLD',label='Legacy permit',start_at='2026-01-01T00:00:00Z',actor='TEST',note='Legacy compatibility'))
        with self.store.connect() as db:
            body=json.loads(db.execute('SELECT body FROM scenario_runs WHERE id=?',('SYN-OLD',)).fetchone()['body']);body.pop('workflow')
            db.execute('UPDATE scenario_runs SET body=? WHERE id=?',(json.dumps(body),'SYN-OLD'))
        run=self.lab.run('SYN-OLD');self.assertEqual(run['workflow'],'permit');self.assertEqual(run['state']['stage'],'RECEIVED')
        self.assertEqual(self.lab.run('SYN-CONTRACT')['workflow'],'procurement')
    def test_backup_restore_and_stale_commands(self):
        self.acceptance();version=self.lab.run('SYN-CONTRACT')['version']
        payload=dict(version=version,action='REVIEW',parameters=dict(passed=True),actor='CHECKER',note='Fictional check')
        self.lab.command('SYN-CONTRACT',payload)
        with self.assertRaises(Conflict):self.lab.command('SYN-CONTRACT',payload)
        target=Path(self.tmp.name)/'backup.sqlite3';self.store.backup(target)
        self.assertEqual(Scenarios(Store(target)).run('SYN-CONTRACT'),self.lab.run('SYN-CONTRACT'))
        self.assertFalse(self.store.project('019')['execution_authorized'])
