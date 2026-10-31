import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from civic_portfolio.scenarios import Scenarios,WORKFLOWS
from civic_portfolio.scenario_comparisons import ScenarioComparisons
from civic_portfolio.store import Store,Conflict
from civic_portfolio.__main__ import server

class ScenarioComparisonTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.store=Store(Path(self.tmp.name)/'db.sqlite3');self.lab=Scenarios(self.store);self.comparisons=ScenarioComparisons(self.store)
    def create(self,key='SYN-SOURCE',workflow='p024'):
        return self.lab.create(dict(run_id=key,workflow=workflow,label='Fictional comparison source',start_at='2026-01-01T00:00:00Z',actor='RECORDER',note='Synthetic only'))
    def command(self,key,action,**params):
        return self.lab.command(key,dict(version=self.lab.run(key)['version'],action=action,parameters=params,actor='CHECKER',note='Fictional baseline or alternative'))
    def observe(self,key,value,metric='referral_wait_minutes',numerator=None,denominator=None):
        return self.command(key,'OBSERVE',metric_id=metric,value=value,numerator=numerator,denominator=denominator,missing_reason=None)
    def pair(self):
        self.create();self.command('SYN-SOURCE','PRESET',stage='CLOSED',quality='PASS')
        first=self.observe('SYN-SOURCE',30)['version'];second=self.observe('SYN-SOURCE',15)['version']
        return first,second
    def compare(self,a,b,baseline='SYN-SOURCE',alternative='SYN-SOURCE',key='SYN-COMPARISON'):
        return self.comparisons.create(dict(comparison_id=key,baseline_run_id=baseline,baseline_sequence=a,alternative_run_id=alternative,alternative_sequence=b,actor='TEST',note='Fictional two-snapshot comparison; no causal claim'))
    def test_known_deltas_and_source_isolation(self):
        a,b=self.pair();before=self.lab.run('SYN-SOURCE');report=self.compare(a,b)
        metric=report['result']['metrics'][0];self.assertEqual(metric['delta'],-15);self.assertEqual(metric['baseline_unit'],'minutes')
        self.assertEqual(self.lab.run('SYN-SOURCE'),before);self.assertFalse(report['causal_effect_estimated']);self.assertFalse(report['execution_authorized'])
        self.assertEqual(report['layer_a_status'],'LEGAL_REVIEW_REQUIRED');self.assertTrue(report['historical_only'])
    def test_missing_observation_never_becomes_zero(self):
        self.create();self.command('SYN-SOURCE','PRESET',stage='CLOSED',quality='PASS');a=self.lab.run('SYN-SOURCE')['version']
        b=self.observe('SYN-SOURCE',0)['version'];report=self.compare(a,b);metric=report['result']['metrics'][0]
        self.assertIsNone(metric['baseline']);self.assertEqual(metric['alternative'],0);self.assertIsNone(metric['delta'])
        self.assertIn('Missing known observation',metric['withheld_reasons'])
    def test_source_advancing_preserves_frozen_result(self):
        a,b=self.pair();first=self.compare(a,b);frozen=first['result']
        self.command('SYN-SOURCE','TICK',minutes=60);later=self.comparisons.report('SYN-COMPARISON')
        self.assertEqual(later['result'],frozen);self.assertFalse(later['source_status']['alternative']['source_current'])
        self.assertTrue(later['source_status']['alternative']['snapshot_intact'])
    def test_different_workflows_reject_atomically(self):
        self.create();self.create('SYN-OTHER','p007')
        with self.assertRaises(ValueError):self.compare(1,1,alternative='SYN-OTHER')
        self.assertEqual(self.comparisons.comparisons(),[])
    def test_mismatched_phases_and_stale_observations_withhold_deltas(self):
        self.create();a=self.observe('SYN-SOURCE',10)['version']
        b=self.command('SYN-SOURCE','STEP',stage='CONSENT_ASSERTED',minutes=1)['version']
        report=self.compare(a,b);self.assertFalse(report['result']['phase_comparable'])
        self.assertTrue(all(t['delta'] is None for t in report['result']['timing']))
        self.assertIn('Observation belongs to an earlier path revision',report['result']['metrics'][0]['withheld_reasons'])
    def test_frozen_contract_units_and_catalog_change_are_explicit(self):
        a,b=self.pair();first=self.compare(a,b);contract=WORKFLOWS['p024']['metrics'][0];old=contract['unit']
        try:
            contract['unit']='hypothetical changed unit'
            report=self.comparisons.report('SYN-COMPARISON')
            self.assertFalse(report['catalog_contracts_current']);self.assertEqual(report['result']['metrics'][0]['contract']['unit'],'minutes')
            self.assertEqual(report['result']['metrics'][0]['delta'],-15)
            another=self.compare(a,b,key='SYN-CONTRACT-MISMATCH')
            self.assertIsNone(another['result']['metrics'][0]['delta']);self.assertIsNone(another['result']['metrics'][0]['baseline_unit'])
        finally:contract['unit']=old
    def test_quality_pass_loss_is_warned_without_improvement_score(self):
        self.create(workflow='p007');self.command('SYN-SOURCE','PRESET',stage='CAPACITY_REVIEW',quality='PASS')
        a=self.observe('SYN-SOURCE',None,metric='assessed_skill_gain',numerator=1,denominator=2)['version']
        b=self.command('SYN-SOURCE','REVIEW',passed=False)['version'];report=self.compare(a,b)
        self.assertTrue(report['result']['quality_changed']);self.assertTrue(any('lost a recorded quality pass' in w for w in report['result']['warnings']))
        self.assertEqual(report['result']['metrics'][0]['baseline_denominator'],2);self.assertFalse(report['case_mix_controlled'])
    def test_distinct_justice_closure_branches_are_not_comparable(self):
        self.create(workflow='justice');a=self.command('SYN-SOURCE','PRESET',stage='CLOSED',quality='PASS')['version']
        self.command('SYN-SOURCE','PRESET',stage='CONTINUITY_REVIEW',quality='PASS')
        b=self.command('SYN-SOURCE','STEP',stage='CLOSED',minutes=60)['version']
        report=self.compare(a,b);self.assertFalse(report['result']['phase_comparable'])
        self.assertTrue(any('Closure pathways differ' in w for w in report['result']['warnings']))
    def test_snapshot_corruption_is_detected_and_not_used_for_new_comparison(self):
        a,b=self.pair();self.compare(a,b)
        with self.store.connect() as db:
            row=db.execute('SELECT body FROM scenario_events WHERE run_id=? AND sequence=?',('SYN-SOURCE',a)).fetchone();event=json.loads(row['body'])
            event['state']['clock_minutes']+=1
            db.execute('UPDATE scenario_events SET body=? WHERE run_id=? AND sequence=?',(json.dumps(event),'SYN-SOURCE',a))
        report=self.comparisons.report('SYN-COMPARISON');self.assertFalse(report['historical_result_intact']);self.assertFalse(report['effective_deltas_available'])
        with self.assertRaises(ValueError):self.compare(a,b,key='SYN-CORRUPT')
    def test_immutable_ids_missing_sources_and_invalid_sequences(self):
        a,b=self.pair();self.compare(a,b)
        with self.assertRaises(Conflict):self.compare(a,b)
        with self.assertRaises(ValueError):self.compare(True,b,key='SYN-BAD')
        with self.assertRaises(ValueError):self.compare(999,b,key='SYN-MISSING-SNAPSHOT')
        with self.assertRaises(KeyError):self.compare(a,b,baseline='SYN-NO-SOURCE',key='SYN-MISSING-SOURCE')
        self.assertEqual(len(self.comparisons.comparisons()),1)
    def test_export_backup_and_restore_preserve_comparison(self):
        a,b=self.pair();self.compare(a,b)
        self.assertEqual(len(self.store.export()['synthetic_scenarios']['comparisons']),1)
        target=Path(self.tmp.name)/'backup.sqlite3';self.store.backup(target)
        self.assertEqual(ScenarioComparisons(Store(target)).report('SYN-COMPARISON'),self.comparisons.report('SYN-COMPARISON'))
    def test_http_page_guard_and_saved_comparison(self):
        a,b=self.pair();app=server(self.store,0);thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
        self.addCleanup(app.server_close);self.addCleanup(thread.join,2);self.addCleanup(app.shutdown)
        base='http://127.0.0.1:'+str(app.server_port);boot=json.load(urlopen(base+'/api/scenario-comparisons'))
        self.assertIn(b'Compare scenario snapshots',urlopen(base+'/compare-scenarios').read())
        payload=json.dumps(dict(comparison_id='SYN-HTTP',baseline_run_id='SYN-SOURCE',baseline_sequence=a,alternative_run_id='SYN-SOURCE',alternative_sequence=b,actor='TEST',note='Fictional comparison')).encode()
        with self.assertRaises(HTTPError) as error:urlopen(Request(base+'/api/scenario-comparisons',data=payload,headers={'Content-Type':'application/json'}))
        self.assertEqual(error.exception.code,403)
        headers={'Content-Type':'application/json','X-Portfolio-Token':boot['token']}
        report=json.load(urlopen(Request(base+'/api/scenario-comparisons',data=payload,headers=headers)))
        self.assertEqual(report['result']['metrics'][0]['delta'],-15)
        self.assertEqual(json.load(urlopen(base+'/api/scenario-comparisons/SYN-HTTP'))['comparison_id'],'SYN-HTTP')
