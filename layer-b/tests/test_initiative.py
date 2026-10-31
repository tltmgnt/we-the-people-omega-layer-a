import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from civic_portfolio.initiative import Initiative,SAFEGUARDS,STAGES,ROOT
from civic_portfolio.store import Store,Conflict
from civic_portfolio.__main__ import server

class InitiativeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.store=Store(Path(self.tmp.name)/'db.sqlite3');self.lab=Initiative(self.store)
        self.lab.create(dict(program_id='SYN-PILOT',label='Fictional notice improvement',project_ids=['009'],source_ids=[],office_review_question='Which office could review a hypothetical pilot?',baseline_plan='Scenario elapsed time and access barriers',success_criteria='Less burden without rights loss',resources='Fictional staff time',continuity_plan='Preserve service route',rollback_plan='Restore prior scenario process',owner='OWNER',at='2026-01-01T00:00:00Z',actor='CREATOR'))
    def record(self,kind,data,actor='RECORDER',hour=1):
        return self.lab.record('SYN-PILOT',dict(version=self.lab.program('SYN-PILOT')['version'],kind=kind,at=f'2026-01-01T{hour:02}:00:00Z',actor=actor,data=data))
    def stage(self,stage):return self.record('STAGE',dict(stage=stage,owner='OWNER',evidence='Fictional phase evidence',limitations='Scenario only; no real pilot'))
    def check_stage(self,passed=True):
        sequence=self.lab.report('SYN-PILOT')['stage_sequence'];return self.record('STAGE_CHECK',dict(stage_sequence=sequence,passed=passed,evidence='Fictional separate check'),actor='CHECKER')
    def prepare_project(self,key='009'):
        p=self.store.project(key);self.store.update(key,dict(version=p['version'],actor='OWNER',owner='OWNER',scope='Fictional bounded process'))
        p=self.store.project(key);self.store.update(key,dict(version=p['version'],actor='OWNER',scope_confirmed=True))
        self.store.import_source('project-'+key,'Fictional complete requirements for scenario','IMPORTER','Fictional source');self.store.review_source('project-'+key,1,'REVIEWER')
        # Source import invalidates scope, so confirmation must follow import/review.
        p=self.store.project(key);self.store.update(key,dict(version=p['version'],actor='OWNER',scope_confirmed=True))
    def safeguards(self):
        for s in SAFEGUARDS:
            self.record('SAFEGUARD',dict(safeguard=s,status='MET',owner='OWNER',evidence='Fictional criterion assertion'))
            seq=self.lab.program('SYN-PILOT')['events'][-1]['sequence'];self.record('SAFEGUARD_CHECK',dict(assertion_sequence=seq,passed=True,evidence='Fictional separate check'),actor='CHECKER')
    def test_all_50_and_honest_unknowns(self):
        catalog=self.lab.catalog();self.assertEqual([p['project_id'] for p in catalog],[f'{i:03}' for i in range(1,51)])
        self.assertTrue(all(p['title'] is None for p in catalog[:6]));self.assertEqual(sum(p['prototype_path'] is not None for p in catalog),12)
        self.assertTrue(all(not p['execution_authorized'] for p in catalog));self.assertEqual(sum(p['group']=='SHARED_METHODS' for p in catalog),10)
    def test_dependencies_cycle_deactivation_and_closure(self):
        self.record('DEPENDENCY',dict(from_project='042',to_project='009',rationale='Proposed method dependency',active=True))
        self.record('DEPENDENCY',dict(from_project='043',to_project='042',rationale='Evidence feeds method',active=True))
        self.assertEqual([p['project_id'] for p in self.lab.report('SYN-PILOT')['context']['projects']],['009','042','043'])
        with self.assertRaises(ValueError):self.record('DEPENDENCY',dict(from_project='009',to_project='043',rationale='Invalid cycle',active=True))
        self.record('DEPENDENCY',dict(from_project='042',to_project='009',rationale='Deferred dependency',active=False))
        self.assertEqual(len(self.lab.report('SYN-PILOT')['context']['projects']),1)
    def test_stage_gate_holds_and_source_review(self):
        self.stage('FRAMEWORK_REVIEW')
        with self.assertRaises(ValueError):self.stage('PILOT_SELECTED')
        self.check_stage()
        with self.assertRaises(ValueError) as e:self.stage('PILOT_SELECTED')
        self.assertIn('source text missing',str(e.exception));self.prepare_project();self.safeguards()
        with self.assertRaises(ValueError):self.stage('PILOT_SELECTED') # framework context stale after source/scope changes
        self.record('REOPEN',dict(reason='Requirements now available'));self.stage('FRAMEWORK_REVIEW');self.check_stage();self.stage('PILOT_SELECTED')
        self.assertFalse(self.lab.report('SYN-PILOT')['execution_authorized'])
    def test_full_synthetic_lifecycle_requires_separate_checks(self):
        self.prepare_project();self.safeguards()
        for stage in STAGES[1:]:
            self.stage(stage);self.check_stage()
        report=self.lab.report('SYN-PILOT');self.assertEqual(report['stage'],'REPORT_RECORDED');self.assertTrue(report['stage_checked']);self.assertEqual(report['blockers'],[])
        self.assertFalse(report['execution_authorized']);self.assertFalse(report['institutional_endorsement']);self.assertFalse(report['domain_implementations_complete'])
    def test_revisions_invalidate_checks_and_scope(self):
        self.prepare_project();self.safeguards();self.stage('FRAMEWORK_REVIEW');self.check_stage()
        self.store.import_source('project-009','Revised fictional requirements','IMPORTER','Fictional revision')
        report=self.lab.report('SYN-PILOT');self.assertTrue(report['stale_record_sequences']);self.assertFalse(report['stage_checked'])
        self.assertIn('project-009: current source not reviewed',report['blockers'])
        with self.assertRaises(ValueError):self.stage('PILOT_SELECTED')
        self.record('REOPEN',dict(reason='Changed source'));self.assertEqual(self.lab.report('SYN-PILOT')['stage'],'PROPOSED')
    def test_safeguard_exact_checks_latest_failure(self):
        self.record('SAFEGUARD',dict(safeguard='AUTHORITY',status='MET',owner='OWNER',evidence='Fictional assertion'))
        payload=dict(assertion_sequence=1,passed=True,evidence='Check')
        with self.assertRaises(ValueError):self.record('SAFEGUARD_CHECK',payload)
        self.record('SAFEGUARD_CHECK',payload,actor='CHECKER')
        self.record('SAFEGUARD_CHECK',{**payload,'passed':False},actor='CHECKER')
        self.assertTrue(any(b.startswith('AUTHORITY:') for b in self.lab.report('SYN-PILOT')['blockers']))
        self.record('SAFEGUARD',dict(safeguard='AUTHORITY',status='GAP',owner='OWNER',evidence='Revised criterion'))
        with self.assertRaises(Conflict):self.record('SAFEGUARD_CHECK',payload,actor='CHECKER')
    def test_challenges_and_priority_history(self):
        self.record('PRIORITY',dict(project_id='005',disposition='REQUIRES_DEFINITION',owner='OWNER',rationale='Title explicitly pending'))
        self.record('CHALLENGE',dict(challenge_id='SYN-QUESTION',question='Fictional access concern',owner='OWNER',evidence='Scenario question'))
        self.assertTrue(any('SYN-QUESTION' in b for b in self.lab.report('SYN-PILOT')['blockers']))
        self.record('RESPONSE',dict(challenge_id='SYN-QUESTION',response='Documented response, not proof of remedy',evidence='Scenario response'))
        self.assertFalse(any('SYN-QUESTION' in b for b in self.lab.report('SYN-PILOT')['blockers']))
    def test_validation_rollback_and_stale_writes(self):
        payload=dict(version=1,kind='REOPEN',at='2026-01-01T01:00:00Z',actor='TEST',data=dict(reason='Scenario reset'))
        self.lab.record('SYN-PILOT',payload)
        with self.assertRaises(Conflict):self.lab.record('SYN-PILOT',payload)
        with self.assertRaises(ValueError):self.lab.record('SYN-PILOT',{**payload,'version':True})
        with self.assertRaises(ValueError):self.record('DEPENDENCY',dict(from_project='009',to_project='009',rationale='Self reference',active=True))
        with self.assertRaises(ValueError):self.record('REOPEN',dict(reason='Too early'),hour=0)
        self.assertEqual(len(self.lab.program('SYN-PILOT')['events']),1)
    def test_backup_export_and_overview_hash(self):
        self.stage('FRAMEWORK_REVIEW');target=Path(self.tmp.name)/'backup.sqlite3';self.store.backup(target)
        self.assertEqual(Initiative(Store(target)).program('SYN-PILOT'),self.lab.program('SYN-PILOT'))
        self.assertEqual(len(self.store.export()['synthetic_initiative']['events']),1)
        manifest=json.loads((ROOT/'portfolio/sources/initiative-provenance.json').read_text());raw=(ROOT/'portfolio/sources/initiative-user-specification.md').read_bytes();self.assertEqual(manifest['sha256'],hashlib.sha256(raw).hexdigest())
        register=json.loads((ROOT/'portfolio/project-register.json').read_text())
        self.assertTrue(all(p['source_url'].encode() in raw for p in register['projects'] if p['source_url']))
    def test_http_catalog_import_and_safe_invalid_requests(self):
        app=server(self.store,0);thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start();self.addCleanup(app.server_close);self.addCleanup(thread.join,2);self.addCleanup(app.shutdown)
        base='http://127.0.0.1:'+str(app.server_port);boot=json.load(urlopen(base+'/api/initiative'));self.assertEqual(len(boot['projects']),50)
        self.assertIn(b'connected 50-project portfolio',urlopen(base+'/initiative').read());spec=json.load(urlopen(base+'/api/initiative/specification'));self.assertIn('Requested Next Step',spec['content'])
        headers={'Content-Type':'application/json','X-Portfolio-Token':boot['token']}
        imported=json.load(urlopen(Request(base+'/api/initiative/import-specification',data=b'{"actor":"TEST"}',headers=headers)));self.assertEqual(imported['sha256'],spec['sha256'])
        self.assertIsNone(self.store.source_content('initiative-overview')['reviewer'])
        with self.assertRaises(HTTPError) as e:urlopen(Request(base+'/api/initiative/SYN-PILOT/records',data=b'{}',headers={'Content-Type':'application/json'}))
        self.assertEqual(e.exception.code,403)
