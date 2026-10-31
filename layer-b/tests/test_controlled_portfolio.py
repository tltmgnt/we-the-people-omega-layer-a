import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from civic_portfolio.scenarios import Scenarios,WORKFLOWS,route,review_gates,fingerprint
from civic_portfolio.store import Store,Conflict
from civic_portfolio.__main__ import server
from civic_portfolio.initiative import Initiative

EXTRA=[k for k in WORKFLOWS if k.startswith('p') and k[1:].isdigit()]

class ControlledPortfolioTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name)/'db.sqlite3');self.lab=Scenarios(self.store)
    def create(self,key='SYN-CASE',workflow='p024'):
        return self.lab.create(dict(run_id=key,workflow=workflow,label='Fictional '+workflow,start_at='2026-01-01T00:00:00Z',actor='RECORDER',note='Synthetic records only'))
    def command(self,key,action,actor='RECORDER',**params):
        return self.lab.command(key,dict(version=self.lab.run(key)['version'],action=action,parameters=params,actor=actor,note='Fictional evidence; not real performance'))
    def observe(self,key,metric,value=None,numerator=None,denominator=None,missing_reason=None):
        return self.command(key,'OBSERVE',metric_id=metric,value=value,numerator=numerator,denominator=denominator,missing_reason=missing_reason)
    def source(self):
        if not any(r['run_id']=='SYN-SOURCE' for r in self.lab.runs()):
            self.create('SYN-SOURCE','p024');self.command('SYN-SOURCE','PRESET',stage='CLOSED',quality='PASS')
            self.observe('SYN-SOURCE','referral_wait_minutes',value=15)
        return self.lab.run('SYN-SOURCE')
    def attach(self,key):
        source=self.source();return self.command(key,'ATTACH',source_run_id=source['run_id'],source_sequence=source['version'])
    def close_normally(self,key):
        run=self.lab.run(key);config=WORKFLOWS[run['workflow']]
        for target in route(config['completion'],run['workflow'])[1:]:
            state=self.lab.run(key)['state'];gate=review_gates(config).get(state['stage'])
            if gate and target==gate['target']:self.command(key,'REVIEW',actor='CHECKER',passed=True)
            self.command(key,'STEP',stage=target,minutes=1)
    def test_44_defined_workstreams_and_six_definition_holds(self):
        self.assertEqual(len(WORKFLOWS),44);self.assertEqual(len(EXTRA),38)
        self.assertEqual({c['project_id'] for c in WORKFLOWS.values()},{f'{i:03}' for i in range(7,51)})
        for project in range(1,7):
            with self.assertRaises(ValueError):self.create('SYN-UNKNOWN','p'+f'{project:03}')
        catalog=Initiative(self.store).catalog()
        self.assertEqual(sum(p['control_path'] is not None for p in catalog),44)
        self.assertTrue(all(p['title'] is None and p['control_path'] is None for p in catalog[:6]))
    def test_every_new_profile_state_preset_is_reachable(self):
        for workflow in EXTRA:
            key='SYN-'+workflow.upper();self.create(key,workflow);config=WORKFLOWS[workflow]
            for stage in config['stages']:
                if workflow=='p050' and stage=='CLOSED':self.attach(key)
                run=self.command(key,'PRESET',stage=stage,quality='PASS' if stage=='CLOSED' else 'UNREVIEWED')
                with self.subTest(workflow=workflow,stage=stage):
                    self.assertEqual(run['state']['stage'],stage);self.assertFalse(run['execution_authorized'])
                    for a,b in zip(run['state']['path'],run['state']['path'][1:]):self.assertIn(b['stage'],config['stages'][a['stage']])
                    self.assertEqual(run['state_sha256'],fingerprint(run['state']))
    def test_every_new_profile_has_executable_checked_path(self):
        for workflow in EXTRA:
            key='SYN-'+workflow.upper();self.create(key,workflow)
            if workflow=='p050':self.attach(key)
            self.close_normally(key);report=self.lab.report(key)
            self.assertEqual(report['stage'],'CLOSED');self.assertFalse(report['execution_authorized'])
            self.assertEqual(report['layer_a_status'],'LEGAL_REVIEW_REQUIRED')
    def test_every_new_profile_blocks_unchecked_same_actor_and_revised_check(self):
        for workflow in EXTRA:
            key='SYN-'+workflow.upper();self.create(key,workflow);config=WORKFLOWS[workflow]
            target=next(iter(config['review_stages']))
            self.command(key,'PRESET',stage=target,quality='UNREVIEWED')
            with self.assertRaises(ValueError):self.command(key,'STEP',stage='CLOSED',minutes=1)
            with self.assertRaises(ValueError):self.command(key,'REVIEW',actor='SYN-PRESET-RECORDER',passed=True)
            self.command(key,'REVIEW',actor='CHECKER',passed=False)
            self.assertNotIn('CLOSED',self.lab.run(key)['controls']['next_stages'])
            self.command(key,'REVIEW',actor='CHECKER',passed=True)
            self.command(key,'STEP',stage=config['correction'],minutes=1)
            while self.lab.run(key)['state']['stage']!=target:
                current=self.lab.run(key)['state']['stage']
                next_stage=next(s for s in config['stages'][current] if s!='WITHDRAWN')
                self.command(key,'STEP',stage=next_stage,minutes=1)
            with self.assertRaises(ValueError):self.command(key,'STEP',stage='CLOSED',minutes=1)
    def test_measurement_zero_missing_correction_and_path_freshness(self):
        self.create();metric='referral_wait_minutes'
        self.observe('SYN-CASE',metric,missing_reason='Not measured')
        r=self.lab.report('SYN-CASE')['observations'][0];self.assertIsNone(r['value']);self.assertEqual(r['missing_reason'],'Not measured')
        self.observe('SYN-CASE',metric,value=0);self.assertEqual(self.lab.report('SYN-CASE')['observations'][0]['value'],0)
        seq=self.lab.run('SYN-CASE')['version']
        self.command('SYN-CASE','STEP',stage='CONSENT_ASSERTED',minutes=1)
        self.assertFalse(self.lab.report('SYN-CASE')['observations'][0]['path_current'])
        self.command('SYN-CASE','RESTORE',sequence=seq)
        self.assertTrue(self.lab.report('SYN-CASE')['observations'][0]['path_current'])
        self.observe('SYN-CASE',metric,value=12.5);self.assertEqual(self.lab.report('SYN-CASE')['observations'][0]['value'],12.5)
    def test_ratio_contract_uses_explicit_denominator(self):
        self.create(workflow='p007')
        self.observe('SYN-CASE','assessed_skill_gain',numerator=1,denominator=3)
        observation=self.lab.report('SYN-CASE')['observations'][0]
        self.assertAlmostEqual(observation['value'],1/3);self.assertEqual(observation['numerator'],1);self.assertEqual(observation['denominator'],3)
        for params in [dict(numerator=1,denominator=0),dict(numerator=3,denominator=2),dict(value=.5),dict(numerator=True,denominator=2)]:
            with self.assertRaises(ValueError):self.observe('SYN-CASE','assessed_skill_gain',**params)
    def test_integer_and_finite_numeric_contracts(self):
        self.create(workflow='p018')
        self.observe('SYN-CASE','unreconciled_minor_units',value=1000000000000)
        for value in [True,1.5,-1,1000000000001,'2']:
            with self.assertRaises(ValueError):self.observe('SYN-CASE','unreconciled_minor_units',value=value)
        self.create('SYN-TIME','p024')
        for value in [float('nan'),float('inf'),True,-1]:
            with self.assertRaises(ValueError):self.observe('SYN-TIME','referral_wait_minutes',value=value)
    def test_contract_change_is_visible_without_rewriting_observation(self):
        self.create();self.observe('SYN-CASE','referral_wait_minutes',value=2)
        contract=WORKFLOWS['p024']['metrics'][0];old=contract['unit']
        try:
            contract['unit']='changed hypothetical definition'
            self.assertFalse(self.lab.report('SYN-CASE')['observations'][0]['contract_current'])
        finally:contract['unit']=old
        self.assertTrue(self.lab.report('SYN-CASE')['observations'][0]['contract_current'])
    def test_capstone_blocks_missing_incomplete_and_missing_measurement_evidence(self):
        self.create(workflow='p050')
        with self.assertRaises(ValueError):self.command('SYN-CASE','PRESET',stage='CLOSED',quality='PASS')
        self.create('SYN-INCOMPLETE','p024')
        self.command('SYN-CASE','ATTACH',source_run_id='SYN-INCOMPLETE',source_sequence=1)
        self.assertFalse(self.lab.report('SYN-CASE')['capstone_evidence_current'])
        self.command('SYN-INCOMPLETE','PRESET',stage='CLOSED',quality='PASS')
        self.command('SYN-CASE','ATTACH',source_run_id='SYN-INCOMPLETE',source_sequence=self.lab.run('SYN-INCOMPLETE')['version'])
        with self.assertRaises(ValueError):self.command('SYN-CASE','PRESET',stage='CLOSED',quality='PASS')
    def test_capstone_pins_source_and_invalidates_when_source_advances(self):
        self.create(workflow='p050');self.attach('SYN-CASE')
        self.command('SYN-CASE','PRESET',stage='CLOSED',quality='PASS')
        report=self.lab.report('SYN-CASE');self.assertTrue(report['capstone_evidence_current']);self.assertFalse(report['execution_authorized'])
        self.assertEqual(report['layer_a_status'],'LEGAL_REVIEW_REQUIRED')
        self.command('SYN-SOURCE','TICK',minutes=1)
        self.assertFalse(self.lab.report('SYN-CASE')['capstone_evidence_current'])
        with self.assertRaises(ValueError):self.command('SYN-CASE','PRESET',stage='CLOSED',quality='PASS')
        self.attach('SYN-CASE');self.command('SYN-CASE','PRESET',stage='CLOSED',quality='PASS')
        self.assertTrue(self.lab.report('SYN-CASE')['capstone_evidence_current'])
    def test_capstone_rejects_self_nested_and_wrong_snapshots(self):
        self.create(workflow='p050');self.create('SYN-NESTED','p050')
        with self.assertRaises(ValueError):self.command('SYN-CASE','ATTACH',source_run_id='SYN-CASE',source_sequence=1)
        with self.assertRaises(ValueError):self.command('SYN-CASE','ATTACH',source_run_id='SYN-NESTED',source_sequence=1)
        self.source()
        with self.assertRaises(ValueError):self.command('SYN-CASE','ATTACH',source_run_id='SYN-SOURCE',source_sequence=999)
    def test_restore_keeps_metric_snapshot_and_capstone_source_pin(self):
        self.create(workflow='p050');self.attach('SYN-CASE')
        before=self.lab.run('SYN-CASE');seq=before['version']
        self.command('SYN-CASE','PRESET',stage='SCENARIO_SCOPED',quality='UNREVIEWED')
        self.command('SYN-CASE','RESTORE',sequence=seq)
        self.assertEqual(self.lab.run('SYN-CASE')['state'],before['state'])
    def test_invalid_commands_and_stale_versions_are_atomic(self):
        self.create();before=self.lab.run('SYN-CASE')
        with self.assertRaises(ValueError):self.observe('SYN-CASE','unknown',value=1)
        with self.assertRaises(ValueError):self.observe('SYN-CASE','referral_wait_minutes',value=1,missing_reason='Contradiction')
        self.assertEqual(self.lab.run('SYN-CASE'),before)
        payload=dict(version=1,action='PAUSE',parameters={},actor='TEST',note='Fictional pause')
        self.lab.command('SYN-CASE',payload)
        with self.assertRaises(Conflict):self.lab.command('SYN-CASE',payload)
    def test_backup_export_isolation_and_fixed_holds(self):
        self.create();self.observe('SYN-CASE','referral_wait_minutes',value=1)
        target=Path(self.tmp.name)/'backup.sqlite3';self.store.backup(target)
        self.assertEqual(Scenarios(Store(target)).run('SYN-CASE'),self.lab.run('SYN-CASE'))
        self.assertEqual(len(self.store.export()['synthetic_scenarios']['runs']),1)
        self.assertTrue(all(not p['execution_authorized'] for p in self.store.export()['projects']))
    def test_http_catalog_metrics_and_token_guard(self):
        self.create();app=server(self.store,0);thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
        self.addCleanup(app.server_close);self.addCleanup(thread.join,2);self.addCleanup(app.shutdown)
        base='http://127.0.0.1:'+str(app.server_port);boot=json.load(urlopen(base+'/api/scenarios'))
        self.assertEqual(len(boot['workflows']),44)
        payload=dict(version=1,action='OBSERVE',actor='TEST',note='Fictional observation',parameters=dict(metric_id='referral_wait_minutes',value=0,numerator=None,denominator=None,missing_reason=None))
        with self.assertRaises(HTTPError) as error:urlopen(Request(base+'/api/scenarios/SYN-CASE/commands',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'}))
        self.assertEqual(error.exception.code,403)
        headers={'Content-Type':'application/json','X-Portfolio-Token':boot['token']}
        result=json.load(urlopen(Request(base+'/api/scenarios/SYN-CASE/commands',data=json.dumps(payload).encode(),headers=headers)))
        self.assertEqual(result['state']['observations']['referral_wait_minutes']['value'],0)
