"""Immutable historical scenario comparisons; never causal or institutional claims."""
from copy import deepcopy
import json
import math
from .maintenance import fields,identifier
from .scenarios import configuration,fingerprint,bounded,catalog
from .store import Conflict,text,now

def numeric(value):
    return type(value) in {int,float} and math.isfinite(value)

def timing(state,config):
    terminal=state['stage'] in config['terminal']
    return dict(clock_minutes=state['clock_minutes'],
                completion_minutes=state['path'][-1]['minute'] if state['stage']==config['completion'] else None,
                open_age_minutes=None if terminal else state['clock_minutes'])

def calculate(left,right,config):
    phase=left['stage']==right['stage'] and left['execution']==right['execution']
    branch=True
    if left['stage']==right['stage']=='CLOSED':
        branch=left['path'][-2]['stage']==right['path'][-2]['stage']
    comparable=phase and branch
    warnings=[]
    if not phase:warnings.append('Workflow stage or execution status differs; numeric deltas are withheld.')
    if not branch:warnings.append('Closure pathways differ; numeric deltas are withheld.')
    if left['quality']=='PASS' and right['quality']!='PASS':warnings.append('The alternative lost a recorded quality pass; speed alone is not an improvement.')
    times=[]
    for key,a in timing(left,config).items():
        b=timing(right,config)[key]
        times.append(dict(measure=key,unit='minutes',baseline=a,alternative=b,delta=b-a if comparable and numeric(a) and numeric(b) else None))
    metrics=[]
    for contract in config.get('metrics',[]):
        a=left.get('observations',{}).get(contract['id']);b=right.get('observations',{}).get(contract['id']);reasons=[]
        a_contract=bool(a and a['contract_sha256']==fingerprint(contract));b_contract=bool(b and b['contract_sha256']==fingerprint(contract))
        if not comparable:reasons.append('Scenario phase/closure path is not comparable')
        if not a or not b or a['value'] is None or b['value'] is None:reasons.append('Missing known observation')
        if (a and a['path_index']!=len(left['path'])-1) or (b and b['path_index']!=len(right['path'])-1):reasons.append('Observation belongs to an earlier path revision')
        if not a_contract or not b_contract:reasons.append('Observation contract is missing or differs from the frozen comparison contract')
        av=a['value'] if a else None;bv=b['value'] if b else None
        if av is not None and not numeric(av) or bv is not None and not numeric(bv):reasons.append('Observation is not a finite numeric value')
        metrics.append(dict(contract=deepcopy(contract),baseline=av,alternative=bv,
                            baseline_numerator=a.get('numerator') if a else None,baseline_denominator=a.get('denominator') if a else None,
                            alternative_numerator=b.get('numerator') if b else None,alternative_denominator=b.get('denominator') if b else None,
                            baseline_unit=contract['unit'] if a_contract else None,alternative_unit=contract['unit'] if b_contract else None,
                            delta=bv-av if not reasons else None,withheld_reasons=reasons))
    return dict(phase_comparable=comparable,baseline_quality=left['quality'],alternative_quality=right['quality'],
                quality_changed=left['quality']!=right['quality'],warnings=warnings,timing=times,metrics=metrics,
                interpretation='Delta is alternative minus baseline. Negative or positive is not automatically better. Two fictional snapshots do not estimate causal effects, statistical significance, safety, fairness or institutional performance.')

class ScenarioComparisons:
    def __init__(self,store):self.store=store

    def snapshot(self,key,sequence,db):
        key=identifier(key);sequence=bounded(sequence,'snapshot sequence',1,10000)
        run=db.execute('SELECT body,version FROM scenario_runs WHERE id=?',(key,)).fetchone()
        if not run:raise KeyError('comparison source run not found')
        event=db.execute('SELECT body FROM scenario_events WHERE run_id=? AND sequence=?',(key,sequence)).fetchone()
        if not event:raise ValueError('comparison source snapshot not found in that run')
        run_body=json.loads(run['body']);event=json.loads(event['body']);state=event['state'];sha=fingerprint(state)
        if sha!=event['state_sha256']:raise ValueError('comparison source snapshot hash mismatch')
        return dict(run_id=key,sequence=sequence,workflow=run_body.get('workflow','permit'),state_sha256=sha,
                    current_at_creation=run['version']==sequence and fingerprint(run_body['state'])==sha),state

    def create(self,data):
        fields(data,'comparison_id baseline_run_id baseline_sequence alternative_run_id alternative_sequence actor note')
        key=identifier(data['comparison_id']);actor=text(data['actor'],'comparison actor',200);note=text(data['note'],'comparison purpose and limitations')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT id FROM scenario_comparisons WHERE id=?',(key,)).fetchone():raise Conflict('comparison ID exists; create a new immutable comparison')
            baseline,left=self.snapshot(data['baseline_run_id'],data['baseline_sequence'],db)
            alternative,right=self.snapshot(data['alternative_run_id'],data['alternative_sequence'],db)
            if baseline['workflow']!=alternative['workflow']:raise ValueError('comparison snapshots must use the same workflow')
            config=configuration(baseline['workflow']);result=calculate(left,right,config)
            body=dict(comparison_id=key,actor=actor,note=note,created_at=now(),baseline=baseline,alternative=alternative,
                      workflow=baseline['workflow'],project_id=config['project_id'],workflow_sha256=fingerprint(catalog()[baseline['workflow']]),result=result,
                      kind='SYNTHETIC',execution_authorized=False,layer_a_status='LEGAL_REVIEW_REQUIRED',
                      causal_effect_estimated=False,case_mix_controlled=False)
            db.execute('INSERT INTO scenario_comparisons VALUES (?,?)',(key,json.dumps(body,allow_nan=False)))
            self.store.log(db,actor,'compare_synthetic_scenario_snapshots',key,body)
            return self.report(key,db)

    def report(self,key,db=None):
        if db is None:
            with self.store.connect() as connection:return self.report(key,connection)
        row=db.execute('SELECT body FROM scenario_comparisons WHERE id=?',(key,)).fetchone()
        if not row:raise KeyError('comparison not found')
        result=json.loads(row['body']);statuses={}
        for side in ('baseline','alternative'):
            pin=result[side];run=db.execute('SELECT body,version FROM scenario_runs WHERE id=?',(pin['run_id'],)).fetchone()
            event=db.execute('SELECT body FROM scenario_events WHERE run_id=? AND sequence=?',(pin['run_id'],pin['sequence'])).fetchone()
            intact=bool(event and fingerprint(json.loads(event['body'])['state'])==pin['state_sha256'] and json.loads(event['body']).get('state_sha256')==pin['state_sha256'])
            current=bool(run and intact and run['version']==pin['sequence'] and fingerprint(json.loads(run['body'])['state'])==pin['state_sha256'])
            statuses[side]=dict(snapshot_intact=intact,source_current=current)
        result['workflow_definition_current']=result['workflow_sha256']==fingerprint(catalog()[result['workflow']])
        current_contracts={m['id']:m for m in configuration(result['workflow']).get('metrics',[])}
        result['catalog_contracts_current']=all(m['contract']['id'] in current_contracts and fingerprint(m['contract'])==fingerprint(current_contracts[m['contract']['id']]) for m in result['result']['metrics'])
        result.update(source_status=statuses,historical_result_intact=all(s['snapshot_intact'] for s in statuses.values()),
                      historical_only=not all(s['source_current'] for s in statuses.values()) or not result['catalog_contracts_current'] or not result['workflow_definition_current'],
                      effective_deltas_available=all(s['snapshot_intact'] for s in statuses.values()),
                      notice='Saved arithmetic uses frozen source snapshots and metric contracts. Advanced sources do not rewrite it. Integrity/catalog warnings limit trust/current applicability. No causal or real-world improvement claim is made.')
        return result

    def comparisons(self):
        with self.store.connect() as db:
            return [self.report(r['id'],db) for r in db.execute('SELECT id FROM scenario_comparisons ORDER BY id')]
