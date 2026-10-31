import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from civic_portfolio.layer_workspaces import LayerWorkspaces, SCHEMAS, STAGES, measure
from civic_portfolio.store import Store, Conflict
from civic_portfolio.__main__ import server


class LayerWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(Path(self.tmp.name)/'db.sqlite3')
        self.lab = LayerWorkspaces(self.store)

    def record(self, record_kind, **values):
        return self.lab.record(record_kind, dict(actor='RECORDER', note='Synthetic aggregate test; no live action',
                                         at='2026-01-03T00:00:00Z', **values))

    def checked(self, record_kind, **values):
        return self.lab.record(record_kind, dict(actor='CHECKER', note='Separate local test check, not authenticated approval',
                                         at='2026-01-03T00:00:00Z', **values))

    def snapshot(self):
        return {k:v for k,v in self.store.export().items() if k != "exported_at"}

    def source(self, expected=0, **changes):
        values = dict(evidence_id='SYN-EVIDENCE', expected_revision=expected, content=' exact fictional text\n',
                      origin='Fictional fixture', confidence='C', corroborating_refs=[],
                      verification_reference=None, limitations='Invented aggregate data')
        values.update(changes)
        return self.record('EVIDENCE', **values)

    def study(self):
        return self.record('STUDY', study_id='SYN-STUDY', domain='Fictional service access',
            definition='Completed requests divided by eligible requests', kind='PROPORTION', unit='fraction',
            cohort='Fictional eligible requests', exclusions='No exclusions assumed', uncertainty='No inference',
            counter_definition='Fictional repeat visits', counter_kind='COUNT', counter_unit='visits', owner='SYN-OWNER')

    def observation(self, phase='BASELINE', **changes):
        study = self.lab.bootstrap()['studies'][0]
        values = dict(study_id='SYN-STUDY', version=study['version'], phase=phase, group='Fictional group',
            window_start='2026-01-01T00:00:00Z' if phase == 'BASELINE' else '2026-01-02T00:00:00Z',
            window_end='2026-01-02T00:00:00Z' if phase == 'BASELINE' else '2026-01-03T00:00:00Z',
            primary_numerator=8 if phase == 'BASELINE' else 9, primary_denominator=10, primary_missing=None,
            counter_numerator=2 if phase == 'BASELINE' else 1, counter_denominator=None, counter_missing=None,
            pins=[dict(evidence_id='SYN-EVIDENCE', revision=1)])
        values.update(changes)
        return self.record('OBSERVATION', **values)

    def check_observation(self, sequence, passed=True):
        return self.checked('OUTCOME_REVIEW', study_id='SYN-STUDY',
            version=self.lab.report_study('SYN-STUDY')['version'], observation_sequence=sequence, passed=passed)

    def pair(self):
        self.source()
        self.checked('EVIDENCE_REVIEW', evidence_id='SYN-EVIDENCE', revision=1, passed=True)
        self.study()
        self.observation()
        self.check_observation(1)
        self.observation('FOLLOW_UP')
        return self.check_observation(3)

    def trial(self):
        return self.record('TRIAL', trial_id='SYN-TRIAL', study_ids=['SYN-STUDY'], scope='Fictional notices',
            owner='SYN-OWNER', resources='Fictional staffing', continuity='Synthetic fallback process',
            rollback='Reopen records; no real service changed')

    def event(self, action='RECORD', status=None, target_sequence=None, passed=None, checker=False):
        method = self.checked if checker else self.record
        return method('TRIAL_EVENT', trial_id='SYN-TRIAL', version=self.lab.report_trial('SYN-TRIAL')['version'],
                      action=action, status=status, target_sequence=target_sequence, passed=passed)

    def next_stage(self, stage):
        report = self.event(status=stage)
        return self.event('CHECK', target_sequence=report['events'][-1]['sequence'], passed=True, checker=True)

    def test_evidence_exact_bytes_history_and_confidence_contract(self):
        source = self.source()
        self.assertEqual(source['revisions'][0]['sha256'], hashlib.sha256(b' exact fictional text\n').hexdigest())
        self.assertFalse(source['source_truth_verified'])
        for changes in [dict(confidence='A'), dict(confidence='B'), dict(corroborating_refs=['same', 'same'])]:
            with self.assertRaises(ValueError):
                self.source(1, **changes)
        self.source(1, confidence='B', corroborating_refs=['Independent fictional fixture'])
        self.assertEqual(len(self.lab.bootstrap()['evidence'][0]['revisions']), 2)
        with self.assertRaises(Conflict):
            self.source(1)

    def test_review_separation_revocation_and_revision_staleness(self):
        self.source()
        with self.assertRaises(ValueError):
            self.record('EVIDENCE_REVIEW', evidence_id='SYN-EVIDENCE', revision=1, passed=True)
        self.checked('EVIDENCE_REVIEW', evidence_id='SYN-EVIDENCE', revision=1, passed=True)
        self.assertTrue(self.lab.bootstrap()['evidence'][0]['locally_reviewed'])
        self.checked('EVIDENCE_REVIEW', evidence_id='SYN-EVIDENCE', revision=1, passed=False)
        self.assertFalse(self.lab.bootstrap()['evidence'][0]['locally_reviewed'])
        self.source(1)
        with self.assertRaises(Conflict):
            self.checked('EVIDENCE_REVIEW', evidence_id='SYN-EVIDENCE', revision=1, passed=True)

    def test_backdated_review_of_new_revision_rejected(self):
        self.source()
        self.checked('EVIDENCE_REVIEW', evidence_id='SYN-EVIDENCE', revision=1, passed=True)
        values = dict(evidence_id='SYN-EVIDENCE', expected_revision=1, content='later', origin='fictional',
                      confidence='C', corroborating_refs=[], verification_reference=None, limitations='synthetic',
                      actor='RECORDER', note='revision', at='2026-01-04T00:00:00Z')
        self.lab.record('EVIDENCE', values)
        with self.assertRaises(ValueError):
            self.checked('EVIDENCE_REVIEW', evidence_id='SYN-EVIDENCE', revision=2, passed=True)

    def test_cross_layer_references_cannot_be_backdated(self):
        self.pair()
        self.trial()
        self.lab.record('EVIDENCE_REVIEW', dict(evidence_id='SYN-EVIDENCE', revision=1, passed=True,
            actor='LATER CHECKER', note='Later source check', at='2026-01-04T00:00:00Z'))
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.observation()
        with self.assertRaises(ValueError):
            self.check_observation(3)
        with self.assertRaises(ValueError):
            self.event(status='DESIGNED')
        self.assertEqual(self.snapshot(), before)

    def test_checked_pair_descriptive_delta_and_holds(self):
        report = self.pair()
        self.assertTrue(report['ready_for_rehearsal'])
        self.assertAlmostEqual(report['groups'][0]['primary_delta'], .1)
        self.assertEqual(report['groups'][0]['counter_delta'], -1)
        self.assertFalse(report['execution_authorized'])
        self.assertFalse(report['causal_effect_estimated'])
        self.assertFalse(report['case_mix_controlled'])
        self.assertEqual(report['layer_a_status'], 'LEGAL_REVIEW_REQUIRED')

    def test_missing_counter_and_unpaired_group_withhold_results(self):
        self.pair()
        report = self.observation('FOLLOW_UP', counter_numerator=None, counter_missing='Not collected')
        self.assertIsNone(report['groups'][0]['counter_delta'])
        self.check_observation(5)
        self.assertFalse(self.lab.report_study('SYN-STUDY')['ready_for_rehearsal'])
        self.observation(group='Another fictional cohort')
        report = self.lab.report_study('SYN-STUDY')
        self.assertEqual(len(report['groups']), 2)
        self.assertFalse(report['ready_for_rehearsal'])

    def test_zero_is_known_and_invalid_denominators_rejected(self):
        self.assertEqual(measure('COUNT', 0, None, None)['value'], 0)
        self.assertIsNone(measure('COUNT', None, None, 'Unknown')['value'])
        for args in [('PROPORTION', 1, 0, None), ('PROPORTION', 3, 2, None),
                     ('COUNT', True, None, None), ('COUNT', 1, 2, None),
                     ('COUNT', None, None, None), ('COUNT', 0, None, 'Unknown')]:
            with self.assertRaises(ValueError):
                measure(*args)

    def test_overlap_and_superseded_checks(self):
        self.pair()
        report = self.observation('FOLLOW_UP', window_start='2026-01-01T12:00:00Z')
        with self.assertRaises(Conflict):
            self.check_observation(3)
        report = self.check_observation(5)
        self.assertFalse(report['ready_for_rehearsal'])
        self.assertIn('overlap', ' '.join(report['groups'][0]['withheld_reasons']))

    def test_revised_evidence_invalidates_outcomes_and_trial_context(self):
        self.pair()
        self.trial()
        self.next_stage('DESIGNED')
        self.source(1, content='Corrected fictional counts')
        report = self.lab.report_trial('SYN-TRIAL')
        self.assertFalse(report['stage_checked'])
        self.assertEqual(report['stale_event_sequences'], [1, 2])
        self.assertFalse(self.lab.report_study('SYN-STUDY')['ready_for_rehearsal'])
        with self.assertRaises(ValueError):
            self.event(status='BASELINE_RECORDED')
        with self.assertRaises(Conflict):
            self.event('CHECK', target_sequence=1, passed=True, checker=True)
        self.assertEqual(self.event('REOPEN')['stage'], 'DRAFT')

    def test_full_lifecycle_separate_checks_and_no_adoption_claim(self):
        self.pair()
        self.trial()
        with self.assertRaises(ValueError):
            self.event(status='REHEARSAL_RECORDED')
        report = self.event(status='DESIGNED')
        with self.assertRaises(ValueError):
            self.event('CHECK', target_sequence=1, passed=True)
        self.event('CHECK', target_sequence=1, passed=False, checker=True)
        with self.assertRaises(ValueError):
            self.event(status='BASELINE_RECORDED')
        self.event('CHECK', target_sequence=1, passed=True, checker=True)
        for stage in STAGES[2:]:
            report = self.next_stage(stage)
        self.assertEqual(report['stage'], 'LEARNING_RECORDED')
        self.assertTrue(report['stage_checked'])
        self.assertFalse(report['live_transition_authorized'])
        self.assertFalse(report['institutional_adoption_established'])
        self.assertFalse(report['execution_authorized'])
        self.assertEqual(self.event('ROLLBACK')['stage'], 'ROLLED_BACK')
        with self.assertRaises(ValueError):
            self.event(status='DESIGNED')
        self.assertEqual(self.event('REOPEN')['stage'], 'DRAFT')

    def test_incomplete_outcomes_block_rehearsal_but_allow_planning(self):
        self.source()
        self.study()
        self.trial()
        self.next_stage('DESIGNED')
        self.next_stage('BASELINE_RECORDED')
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.event(status='REHEARSAL_RECORDED')
        self.assertEqual(self.snapshot(), before)
        with self.assertRaises(ValueError):
            self.event('ROLLBACK')

    def test_outcome_changes_invalidate_prior_phase_checks(self):
        self.pair()
        self.trial()
        self.next_stage('DESIGNED')
        self.check_observation(3, passed=False)
        self.assertFalse(self.lab.report_trial('SYN-TRIAL')['stage_checked'])
        with self.assertRaises(ValueError):
            self.event(status='BASELINE_RECORDED')

    def test_atomic_rejection_strict_contracts_and_stale_versions(self):
        self.pair()
        before = self.snapshot()
        for changes, error in [(dict(version=1), Conflict), (dict(pins=[]), ValueError),
                               (dict(pins=[dict(evidence_id='SYN-EVIDENCE', revision=True)]), ValueError),
                               (dict(phase='LIVE'), ValueError)]:
            with self.assertRaises(error):
                self.observation(**changes)
            self.assertEqual(self.snapshot(), before)
        with self.assertRaises(ValueError):
            self.lab.record('STUDY', {})

    def test_export_backup_persistence_and_contract_immutability(self):
        self.pair()
        self.trial()
        self.next_stage('DESIGNED')
        with self.assertRaises(Conflict):
            self.study()
        backup = Path(self.tmp.name)/'backup.sqlite3'
        self.store.backup(backup)
        restored = LayerWorkspaces(Store(backup))
        self.assertEqual(restored.report_trial('SYN-TRIAL'), self.lab.report_trial('SYN-TRIAL'))
        self.assertEqual(len(self.store.export()['synthetic_layers']['activity']), 7)

    def test_http_ui_token_guards_and_conflicts(self):
        self.pair()
        app = server(self.store, 0)
        thread = threading.Thread(target=app.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(app.server_close)
        self.addCleanup(thread.join, 2)
        self.addCleanup(app.shutdown)
        base = 'http://127.0.0.1:'+str(app.server_port)
        with urlopen(base+'/api/layers') as response:
            token = json.load(response)['token']
        for path in ['/layers', '/layers.js', '/api/layers/studies/SYN-STUDY']:
            with urlopen(base+path) as response:
                self.assertEqual(response.status, 200)
        values = dict(evidence_id='SYN-EVIDENCE', revision=1, passed=False,
                      actor='HTTP CHECKER', note='Revoke check', at='2026-01-03T00:00:00Z')
        def post(headers):
            return urlopen(Request(base+'/api/layers/EVIDENCE_REVIEW', data=json.dumps(values).encode(),
                headers={'Content-Type': 'application/json', **headers}, method='POST'))
        with self.assertRaises(HTTPError) as error:
            post({})
        self.assertEqual(error.exception.code, 403)
        with post({'X-Portfolio-Token': token}) as response:
            self.assertFalse(json.load(response)['locally_reviewed'])
        self.source(1)
        with self.assertRaises(HTTPError) as error:
            post({'X-Portfolio-Token': token})
        self.assertEqual(error.exception.code, 409)
