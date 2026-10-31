import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from civic_portfolio.justice import Justice,DIMENSIONS,MODULES,ROLES
from civic_portfolio.store import Store,Conflict
from civic_portfolio.__main__ import server

class JusticeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name)/'test.sqlite3');self.lab=Justice(self.store)
        self.lab.create(dict(pilot_id='SYN-JUSTICE',label='Fictional notice pathway',jurisdiction='Fictional',process_owner='OWNER',data_steward='STEWARD',authority='Scenario authority',privacy_rules='Synthetic only; no identities; local retention',challenge_route='Scenario challenge desk',at='2026-01-01T00:00:00Z',actor='REGISTRAR'))
        self.evidence()
    def evidence(self,level='C',**updates):
        return self.record('EVIDENCE',dict(evidence_id='SYN-EVIDENCE',content='Synthetic exact text Ω',origin='Fictional source',level=level,corroborating_sources=[],verification_reference=None,limitations='Unverified synthetic evidence',**updates))
    def record(self,kind,data,hour=1,actor='RECORDER'):
        return self.lab.record('SYN-JUSTICE',dict(version=self.lab.pilot('SYN-JUSTICE')['version'],kind=kind,data=data,at=f'2026-01-01T{hour:02}:00:00Z',actor=actor))
    def pins(self,revision=1):return [dict(evidence_id='SYN-EVIDENCE',revision=revision)]
    def gap(self):return self.record('GAP',dict(gap_id='SYN-GAP',dimension='INFORMATION',module='ACCESS',question='Are notices understandable?',owner='OWNER',authority='Scenario authority',review_route='Scenario reviewer',alternative_explanation='Case complexity may explain delay',pins=self.pins()))
    def case(self,key='SYN-CASE',stage='ACCESS',case_type='Demo civil'):
        return self.record('CASE',dict(case_id=key,case_type=case_type,complexity='DECLARED SIMPLE',urgency='ROUTINE',stage=stage,pins=self.pins()))
    def transition(self,stage,hour,**updates):
        data=dict(case_id='SYN-CASE',stage=stage,owner='OWNER',authority='Fictional process map',review_route='Review desk',waiting_minutes=30,active_minutes=10,cause='Fictional notice preparation',classification='NECESSARY_SAFEGUARD',pins=self.pins());data.update(updates)
        return self.record('TRANSITION',data,hour)
    def remedy(self):
        self.gap();return self.record('REMEDY',dict(remedy_id='SYN-REMEDY',gap_id='SYN-GAP',status='OPEN',owner='OWNER',description='Fictional clearer notice',pins=self.pins()))
    def status(self,status,hour=1):return self.record('REMEDY_STATUS',dict(remedy_id='SYN-REMEDY',status=status,description='Fictional implementation or reopening',pins=self.pins()),hour)
    def check(self,passed=True,sequence=None,actor='CHECKER'):
        if sequence is None:sequence=[e for e in self.lab.pilot('SYN-JUSTICE')['events'] if e['kind']=='REMEDY_STATUS'][-1]['sequence']
        return self.record('REMEDY_CHECK',dict(remedy_id='SYN-REMEDY',passed=passed,implementation_sequence=sequence,pins=self.pins()),actor=actor)
    def metric(self,measure='RATIO'):
        return self.record('METRIC',dict(metric_id='SYN-METRIC',module='ACCESS',definition='Fictional understood notices / observed notices',unit='ratio',measure=measure,numerator_definition='Understood',denominator_definition='Observed',period='Fictional baseline',owner='STEWARD',exclusions='Unknown observations excluded',uncertainty='Small synthetic sample',subgroup='No subgroup claims',correction_process='Append corrected observation with evidence',counter_metric='Preparation time and access barriers',pins=self.pins()))
    def report(self,hour=12):return self.lab.report('SYN-JUSTICE',f'2026-01-01T{hour:02}:00:00Z')
    def test_catalog_and_fixed_rights_holds(self):
        report=self.report();self.assertEqual(len(report['gap_matrix']),10);self.assertEqual(len(report['module_coverage']),8)
        self.assertEqual(len(report['review_roles']),7);self.assertFalse(report['execution_authorized']);self.assertEqual(report['legal_review'],'REQUIRED')
        self.assertEqual(report['evidence_levels'],dict(A=0,B=0,C=1))
    def test_evidence_hash_and_level_validation(self):
        item=self.lab.pilot('SYN-JUSTICE')['events'][0]['data'];self.assertEqual(item['sha256'],hashlib.sha256('Synthetic exact text Ω'.encode()).hexdigest())
        with self.assertRaises(ValueError):self.evidence('A')
        with self.assertRaises(ValueError):self.evidence('B')
        data=dict(evidence_id='SYN-VERIFIED',content='Fictional record',origin='SYN-OFFICIAL',level='A',corroborating_sources=[],verification_reference='SYN-ASSERTED-REVIEW',limitations='Still an assertion')
        self.record('EVIDENCE',data);self.assertEqual(self.report()['evidence_levels']['A'],1)
    def test_gap_evidence_revision_and_asof(self):
        self.gap();self.evidence();r=self.report();self.assertEqual(r['stale_record_sequences'],[2]);self.assertEqual(len(self.lab.pilot('SYN-JUSTICE')['events']),3)
        with self.assertRaises(ValueError):self.record('GAP',dict(gap_id='SYN-BAD',dimension='POWER',module='ACCESS',question='Question',owner='OWNER',authority='SYN',review_route='SYN',alternative_explanation='Unknown',pins=self.pins(99)))
        self.assertTrue(r['gap_matrix'][3]['items'][0]['stale_evidence'])
        self.assertEqual(self.report(0)['evidence_levels'],dict(A=0,B=0,C=0))
    def test_caseflow_strata_wait_active_and_remand(self):
        self.case();self.transition('FILED',2);self.transition('FIRST_ACTION',3,waiting_minutes=None,active_minutes=None);self.transition('RESOLVED',4)
        r=self.report();self.assertEqual(r['caseflow_strata'][0]['filing_to_latest_resolution_hours']['median'],2)
        self.assertIsNone(r['temporal_intervals'][1]['unclassified_minutes']);self.assertEqual(r['temporal_intervals'][0]['unclassified_minutes'],20)
        self.transition('FIRST_ACTION',5);self.assertEqual(self.report()['caseflow_strata'][0]['resolved_cases'],0)
        self.assertEqual(self.report(4)['caseflow_strata'][0]['resolved_cases'],1)
        self.assertEqual(self.report()['caseflow_strata'][0]['pending_age_hours']['median'],11)
        self.transition('FIRST_ACTION',6);self.assertEqual(len(self.report()['temporal_intervals']),5)
    def test_reentry_and_invalid_transitions(self):
        self.case(stage='RELEASE');self.transition('SUPERVISION',2);self.transition('REINTEGRATION',3)
        self.assertEqual(self.report()['caseflow_strata'][0]['filing_to_latest_resolution_hours']['sample_size'],0)
        with self.assertRaises(ValueError):self.transition('FILED',4)
        with self.assertRaises(ValueError):self.transition('RELEASE',4,waiting_minutes=999)
        self.assertEqual(len(self.lab.pilot('SYN-JUSTICE')['events']),4)
    def test_remedy_exact_check_closure_and_reopening(self):
        self.remedy();self.status('IMPLEMENTED')
        with self.assertRaises(ValueError):self.status('CLOSED')
        with self.assertRaises(ValueError):self.check(actor='RECORDER')
        seq=self.lab.pilot('SYN-JUSTICE')['events'][-1]['sequence'];self.check();self.status('IMPLEMENTED')
        with self.assertRaises(Conflict):self.check(sequence=seq)
        with self.assertRaises(ValueError):self.status('CLOSED')
        self.check(False)
        with self.assertRaises(ValueError):self.status('CLOSED')
        self.check();self.status('CLOSED');self.assertEqual(self.report()['remedies'][0]['status'],'CLOSED')
        self.status('REOPENED',2);self.assertEqual(self.report()['remedies'][0]['open_age_hours'],11);self.assertEqual(self.report()['remedies'][0]['reopen_count'],1)
    def test_stale_evidence_blocks_remedy_check(self):
        self.remedy();self.status('IMPLEMENTED');self.evidence()
        with self.assertRaises(ValueError):self.check()
        self.assertTrue(self.report()['remedies'][0]['stale_evidence'])
    def test_metric_contract_ratio_missing_and_correction(self):
        self.metric();base=dict(metric_id='SYN-METRIC',numerator=None,denominator=None,missing_reason='Not observed',pins=self.pins())
        self.record('OBSERVATION',base);self.assertIsNone(self.report()['metrics'][0]['value'])
        for denom in (0,False,'2'):
            with self.assertRaises(ValueError):self.record('OBSERVATION',{**base,'numerator':1,'denominator':denom,'missing_reason':None})
        self.record('OBSERVATION',{**base,'numerator':2,'denominator':4,'missing_reason':None});self.assertEqual(self.report()['metrics'][0]['value'],.5)
        self.record('OBSERVATION',{**base,'numerator':3,'denominator':4,'missing_reason':None});self.assertEqual(self.report()['metrics'][0]['observation_count'],3)
        self.evidence();self.assertTrue(self.report()['metrics'][0]['stale_evidence'])
    def test_reviews_and_phases_never_authorize(self):
        seq=self.lab.analysis_sequence(self.lab.pilot('SYN-JUSTICE')['events'])
        for role in ROLES:self.record('REVIEW',dict(role=role,conclusion='SUPPORTED_WITH_LIMITS',disagreement='Synthetic review; qualified legal review still required',analysis_sequence=seq,pins=self.pins()),actor='HUMAN REVIEWER')
        self.assertTrue(all(r['current'] for r in self.report()['review_roles'].values()));self.assertFalse(self.report()['execution_authorized'])
        self.record('PHASE',dict(phase='BASELINE_1_30',owner='OWNER',finding='Scenario baseline',limitations='Not an actual pilot',pins=self.pins()))
        self.assertTrue(all(not r['current'] for r in self.report()['review_roles'].values()))
    def test_validation_and_atomic_stale_writes(self):
        pilot=self.lab.pilot('SYN-JUSTICE');payload=dict(version=1,kind='PHASE',at='2026-01-01T01:00:00Z',actor='TEST',data=dict(phase='BASELINE_1_30',owner='O',finding='F',limitations='L',pins=self.pins()))
        with self.assertRaises(Conflict):self.lab.record('SYN-JUSTICE',payload)
        with self.assertRaises(ValueError):self.lab.record('SYN-JUSTICE',{**payload,'version':pilot['version'],'at':'2025-01-01T00:00:00Z'})
        with self.assertRaises(ValueError):self.lab.record('SYN-JUSTICE',{**payload,'version':True})
        with self.assertRaises(ValueError):self.lab.record('SYN-JUSTICE',{**payload,'kind':'SENTENCE'})
        self.assertEqual(self.lab.pilot('SYN-JUSTICE')['version'],pilot['version'])
    def test_export_backup_and_source_manifest(self):
        self.gap();export=self.store.export();self.assertEqual(len(export['synthetic_justice']['events']),2)
        target=Path(self.tmp.name)/'backup.sqlite3';self.store.backup(target)
        self.assertEqual(Justice(Store(target)).pilot('SYN-JUSTICE'),self.lab.pilot('SYN-JUSTICE'))
        root=Path(__file__).resolve().parents[1];manifest=json.loads((root/'portfolio/sources/023-provenance.json').read_text());raw=(root/'portfolio/sources/023-user-specification.md').read_bytes()
        self.assertEqual(manifest['sha256'],hashlib.sha256(raw).hexdigest());self.assertFalse(manifest['external_claims_verified'])
    def test_http_source_import_and_guarded_mutations(self):
        app=server(self.store,0);thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start();self.addCleanup(app.server_close);self.addCleanup(thread.join,2);self.addCleanup(app.shutdown)
        base='http://127.0.0.1:'+str(app.server_port);boot=json.load(urlopen(base+'/api/justice'))
        self.assertIn(b'Courts, Justice',urlopen(base+'/justice').read())
        spec=json.load(urlopen(base+'/api/justice/specification'));self.assertIn('11. Definition of success',spec['content'])
        with self.assertRaises(HTTPError) as error:urlopen(Request(base+'/api/justice/import-specification',data=b'{"actor":"TEST"}',headers={'Content-Type':'application/json'}))
        self.assertEqual(error.exception.code,403)
        headers={'Content-Type':'application/json','X-Portfolio-Token':boot['token']}
        imported=json.load(urlopen(Request(base+'/api/justice/import-specification',data=b'{"actor":"TEST"}',headers=headers)))
        self.assertEqual(imported['sha256'],spec['sha256']);self.assertIsNone(self.store.source_content('project-023')['reviewer'])
        report=json.load(urlopen(base+'/api/justice/SYN-JUSTICE/report?as_of=2026-01-01T12:00:00Z'));self.assertFalse(report['execution_authorized'])

    def test_exact_snapshot_bytes_and_corroboration(self):
        raw='\n Synthetic Unicode Ω with trailing whitespace \n'
        self.record('EVIDENCE',dict(evidence_id='SYN-RAW',content=raw,origin='First fictional source',level='B',corroborating_sources=['Second fictional source'],verification_reference=None,limitations='Distinct references are not verified independence'))
        item=self.lab.pilot('SYN-JUSTICE')['events'][-1]['data']
        self.assertEqual(item['content'],raw);self.assertEqual(item['sha256'],hashlib.sha256(raw.encode()).hexdigest())
        self.assertEqual(self.report()['evidence_levels']['B'],1)
        with self.assertRaises(ValueError):self.record('EVIDENCE',{k:v for k,v in item.items() if k not in {'revision','sha256'}}|{'corroborating_sources':['First fictional source']})

    def test_count_metric_and_cross_pilot_reference_isolation(self):
        self.metric('COUNT')
        data=dict(metric_id='SYN-METRIC',numerator=0,denominator=None,missing_reason=None,pins=self.pins())
        self.record('OBSERVATION',data);self.assertEqual(self.report()['metrics'][0]['value'],0)
        with self.assertRaises(ValueError):self.record('OBSERVATION',{**data,'denominator':1})
        self.lab.create(dict(pilot_id='SYN-OTHER',label='Other fictional process',jurisdiction='Fictional',process_owner='OWNER',data_steward='STEWARD',authority='Scenario authority',privacy_rules='Synthetic only',challenge_route='Scenario reviewer',at='2026-01-01T00:00:00Z',actor='REGISTRAR'))
        with self.assertRaises(ValueError):self.lab.record('SYN-OTHER',dict(version=1,kind='OBSERVATION',data=data,at='2026-01-01T01:00:00Z',actor='TEST'))
        self.assertEqual(self.lab.pilot('SYN-OTHER')['events'],[])
