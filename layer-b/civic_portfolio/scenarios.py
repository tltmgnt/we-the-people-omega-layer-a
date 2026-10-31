"""Deterministic permit-use-case controls; isolated from domain/authority records."""
from collections import deque
from copy import deepcopy
from datetime import timedelta
import hashlib
import json
import math
from .maintenance import fields, identifier
from .permits import STAGES, TERMINAL, timestamp
from .store import Conflict, text, ROOT

ACTIONS={
    'STEP':'stage minutes',
    'TICK':'minutes',
    'PAUSE':'',
    'RESUME':'',
    'STOP':'',
    'REVIEW':'passed',
    'PRESET':'stage quality',
    'RESTORE':'sequence',
    'OBSERVE':'metric_id value numerator denominator missing_reason',
    'ATTACH':'source_run_id source_sequence',
}
QUALITY=('UNREVIEWED','PASS','FAIL')
PROCUREMENT_STAGES={
    'DRAFT':{'SOLICITATION_RECORDED','CANCELLED'},
    'SOLICITATION_RECORDED':{'EVALUATION_RECORDED','CANCELLED'},
    'EVALUATION_RECORDED':{'CONTRACT_RECORDED','CANCELLED'},
    'CONTRACT_RECORDED':{'DELIVERY_RECORDED','CANCELLED'},
    'DELIVERY_RECORDED':{'ACCEPTANCE_REVIEW','CANCELLED'},
    'ACCEPTANCE_REVIEW':{'CORRECTION_REQUESTED','CLOSED','CANCELLED'},
    'CORRECTION_REQUESTED':{'DELIVERY_RECORDED','CANCELLED'},
    'CLOSED':set(),'CANCELLED':set(),
}
EDUCATION_STAGES={
    'REQUEST_RECORDED':{'ACCESS_REVIEW','WITHDRAWN'},
    'ACCESS_REVIEW':{'SERVICE_OFFERED','WITHDRAWN'},
    'SERVICE_OFFERED':{'SERVICE_STARTED','ACCESS_REVIEW','WITHDRAWN'},
    'SERVICE_STARTED':{'FOLLOW_UP_RECORDED','INTERRUPTED','WITHDRAWN'},
    'INTERRUPTED':{'SERVICE_OFFERED','WITHDRAWN'},
    'FOLLOW_UP_RECORDED':{'CONTINUITY_REVIEW','INTERRUPTED','WITHDRAWN'},
    'CONTINUITY_REVIEW':{'CLOSED','INTERRUPTED','WITHDRAWN'},
    'CLOSED':set(),'WITHDRAWN':set(),
}
HEALTH_STAGES={
    'REQUEST_RECORDED':{'CONSENT_RECORDED','DECLINED'},
    'CONSENT_RECORDED':{'REFERRAL_RECORDED','CONSENT_WITHDRAWN','DECLINED'},
    'REFERRAL_RECORDED':{'WAITING','CONSENT_WITHDRAWN','DECLINED'},
    'WAITING':{'SERVICE_STARTED','REFERRAL_RECORDED','CONSENT_WITHDRAWN','DECLINED'},
    'SERVICE_STARTED':{'FOLLOW_UP_RECORDED','INTERRUPTED','CONSENT_WITHDRAWN'},
    'INTERRUPTED':{'REFERRAL_RECORDED','CONSENT_WITHDRAWN','DECLINED'},
    'FOLLOW_UP_RECORDED':{'CONTINUITY_REVIEW','INTERRUPTED','CONSENT_WITHDRAWN'},
    'CONTINUITY_REVIEW':{'CLOSED','INTERRUPTED','CONSENT_WITHDRAWN'},
    'CLOSED':set(),'DECLINED':set(),'CONSENT_WITHDRAWN':set(),
}
EMERGENCY_STAGES={
    'DESIGNED':{'READINESS_RECORDED','CANCELLED'},
    'READINESS_RECORDED':{'READINESS_REVIEW','CANCELLED'},
    'READINESS_REVIEW':{'EXERCISE_STARTED','READINESS_RECORDED','CANCELLED'},
    'EXERCISE_STARTED':{'RESPONSE_RECORDED','ABORTED'},
    'RESPONSE_RECORDED':{'AFTER_ACTION_RECORDED','ABORTED'},
    'AFTER_ACTION_RECORDED':{'CORRECTION_RECORDED','CANCELLED'},
    'CORRECTION_RECORDED':{'CORRECTION_REVIEW','CANCELLED'},
    'CORRECTION_REVIEW':{'CLOSED','CORRECTION_RECORDED','CANCELLED'},
    'CLOSED':set(),'CANCELLED':set(),'ABORTED':set(),
}
JUSTICE_STAGES={
    'ACCESS_REQUESTED':{'FILED','WITHDRAWN'},
    'FILED':{'NOTICE_RECORDED','WITHDRAWN'},
    'NOTICE_RECORDED':{'NOTICE_REVIEW','WITHDRAWN'},
    'NOTICE_REVIEW':{'HEARING_RECORDED','NOTICE_RECORDED','WITHDRAWN'},
    'HEARING_RECORDED':{'DECISION_RECORDED','NOTICE_RECORDED','WITHDRAWN'},
    'DECISION_RECORDED':{'REVIEW_REQUESTED','REMEDY_RECORDED','REENTRY_HANDOFF'},
    'REVIEW_REQUESTED':{'REMANDED','REMEDY_RECORDED','WITHDRAWN'},
    'REMANDED':{'NOTICE_RECORDED','WITHDRAWN'},
    'REMEDY_RECORDED':{'REMEDY_REVIEW','WITHDRAWN'},
    'REMEDY_REVIEW':{'CLOSED','REMEDY_RECORDED','REVIEW_REQUESTED'},
    'REENTRY_HANDOFF':{'FOLLOW_UP_RECORDED','WITHDRAWN'},
    'FOLLOW_UP_RECORDED':{'CONTINUITY_REVIEW','REENTRY_HANDOFF','WITHDRAWN'},
    'CONTINUITY_REVIEW':{'CLOSED','REENTRY_HANDOFF','WITHDRAWN'},
    'CLOSED':set(),'WITHDRAWN':set(),
}
WORKFLOWS={
    'permit':dict(label='Project 009 — fictional permit',initial='RECEIVED',stages=STAGES,
                  terminal=TERMINAL,review_stages={'DECIDED'},completion='DECIDED',correction='AWAITING_CORRECTION'),
    'procurement':dict(label='Project 019 — fictional procurement and delivery',initial='DRAFT',stages=PROCUREMENT_STAGES,
                  terminal={'CLOSED','CANCELLED'},review_stages={'ACCEPTANCE_REVIEW'},completion='CLOSED',correction='CORRECTION_REQUESTED',gate_anchors=['DELIVERY_RECORDED'],gate_label='acceptance',gate_error='acceptance requires a checker distinct from the current delivery recorder'),
    'education':dict(label='Project 020 — fictional education-service access and continuity',initial='REQUEST_RECORDED',stages=EDUCATION_STAGES,
                  terminal={'CLOSED','WITHDRAWN'},review_stages={'CONTINUITY_REVIEW'},completion='CLOSED',correction='INTERRUPTED',
                  gate_anchors=['SERVICE_STARTED','FOLLOW_UP_RECORDED'],gate_label='continuity',gate_error='continuity requires a checker distinct from the current service/follow-up recorders'),
    'health':dict(label='Project 021 — fictional health-service referral and continuity',initial='REQUEST_RECORDED',stages=HEALTH_STAGES,
                  terminal={'CLOSED','DECLINED','CONSENT_WITHDRAWN'},review_stages={'CONTINUITY_REVIEW'},completion='CLOSED',correction='INTERRUPTED',
                  gate_anchors=['SERVICE_STARTED','FOLLOW_UP_RECORDED'],gate_label='health-service continuity',
                  gate_error='continuity requires a checker distinct from the current health-service/follow-up recorders'),
    'emergency':dict(label='Project 022 — fictional emergency-readiness exercise',initial='DESIGNED',stages=EMERGENCY_STAGES,
                  terminal={'CLOSED','CANCELLED','ABORTED'},review_stages={'READINESS_REVIEW','CORRECTION_REVIEW'},completion='CLOSED',correction='CORRECTION_RECORDED',
                  gate_anchors=['AFTER_ACTION_RECORDED','CORRECTION_RECORDED'],gate_label='exercise correction',
                  gate_error='correction requires a checker distinct from current after-action/correction recorders',
                  phase_gates={
                    'READINESS_REVIEW':dict(target='EXERCISE_STARTED',anchors=['READINESS_RECORDED'],label='exercise readiness',error='readiness requires a checker distinct from the current readiness recorder'),
                    'CORRECTION_REVIEW':dict(target='CLOSED',anchors=['AFTER_ACTION_RECORDED','CORRECTION_RECORDED'],label='exercise correction',error='correction requires a checker distinct from current after-action/correction recorders'),
                  }),
    'justice':dict(label='Project 023 — fictional justice caseflow and remedies',initial='ACCESS_REQUESTED',stages=JUSTICE_STAGES,
                  terminal={'CLOSED','WITHDRAWN'},review_stages={'NOTICE_REVIEW','REMEDY_REVIEW','CONTINUITY_REVIEW'},completion='CLOSED',correction='REMANDED',
                  gate_anchors=['DECISION_RECORDED','REMEDY_RECORDED'],gate_label='remedy record',
                  gate_error='remedy check requires an identifier distinct from current decision/remedy recorders',
                  phase_gates={
                    'NOTICE_REVIEW':dict(target='HEARING_RECORDED',anchors=['FILED','NOTICE_RECORDED'],label='notice record',error='notice check requires an identifier distinct from current filing/notice recorders'),
                    'REMEDY_REVIEW':dict(target='CLOSED',anchors=['DECISION_RECORDED','REMEDY_RECORDED'],label='remedy record',error='remedy check requires an identifier distinct from current decision/remedy recorders'),
                    'CONTINUITY_REVIEW':dict(target='CLOSED',anchors=['REENTRY_HANDOFF','FOLLOW_UP_RECORDED'],label='reentry continuity',error='reentry check requires an identifier distinct from current handoff/follow-up recorders'),
                  }),
}

def load_editorial_profiles():
    raw=json.loads((ROOT/'portfolio/scenario-profiles.json').read_text())
    if raw.get('version')!=1 or not isinstance(raw.get('profiles'),list):raise ValueError('invalid scenario profile catalog')
    ids=set()
    for original in raw['profiles']:
        p=deepcopy(original);key=p.pop('workflow')
        if key in WORKFLOWS or p['project_id'] in ids:raise ValueError('duplicate scenario profile')
        ids.add(p['project_id'])
        if p['project_id'] not in {f'{i:03}' for i in range(7,51)}:raise ValueError('unassigned project cannot have a scenario')
        if not isinstance(p['stages'],dict) or not p['stages']:raise ValueError('profile requires stages')
        p['stages']={k:set(v) for k,v in p['stages'].items()};p['terminal']=set(p['terminal']);p['review_stages']=set(p['review_stages'])
        stages=set(p['stages'])
        if p['initial'] not in stages or p['completion'] not in p['terminal'] or not p['terminal']<=stages or not p['review_stages']<=stages:raise ValueError('invalid profile states')
        if any(not targets<=stages for targets in p['stages'].values()) or any(p['stages'][t] for t in p['terminal']):raise ValueError('invalid profile edges')
        reached={p['initial']}
        while True:
            expanded=reached|set().union(*(p['stages'][k] for k in reached))
            if expanded==reached:break
            reached=expanded
        if reached!=stages or not set(p['gate_anchors'])<=stages:raise ValueError('unreachable profile state/anchor')
        metrics=p['metrics']
        if len({m['id'] for m in metrics})!=len(metrics) or any(m['kind'] not in {'COUNT','MINUTES','RATIO','INTEGER_MINOR_UNITS'} for m in metrics):raise ValueError('invalid metric contract')
        WORKFLOWS[key]=p
    for key,project in {'permit':'009','procurement':'019','education':'020','health':'021','emergency':'022','justice':'023'}.items():
        WORKFLOWS[key]['project_id']=project
    if {p['project_id'] for p in WORKFLOWS.values()}!={f'{i:03}' for i in range(7,51)}:raise ValueError('defined-project control coverage is incomplete')

load_editorial_profiles()

def configuration(workflow):
    workflow=text(workflow,'workflow',100)
    if workflow not in WORKFLOWS:raise ValueError('unknown scenario workflow')
    return WORKFLOWS[workflow]

def catalog():
    return {key:{**{k:v for k,v in c.items() if k not in {'stages','terminal','review_stages'}},
                 'stages':{k:sorted(v) for k,v in c['stages'].items()},'terminal':sorted(c['terminal']),
                 'review_stages':sorted(c['review_stages'])} for key,c in WORKFLOWS.items()}

def review_gates(config):
    if config.get('phase_gates'):return config['phase_gates']
    if config.get('gate_anchors'):
        return {stage:dict(target='CLOSED',anchors=config['gate_anchors'],label=config['gate_label'],error=config['gate_error']) for stage in config['review_stages']}
    return {}

def acceptance_current(state):
    return state['quality']=='PASS' and state.get('review_path_index')==len(state['path'])-1


def justice_diagnostics(state):
    path=state['path'];filed=next((p for p in path if p['stage']=='FILED'),None)
    decisions=[p for p in path if p['stage']=='DECISION_RECORDED']
    pending=state['stage'] in {'ACCESS_REQUESTED','FILED','NOTICE_RECORDED','NOTICE_REVIEW','HEARING_RECORDED','REVIEW_REQUESTED','REMANDED'}
    return dict(justice_review_pending=pending,
                filing_to_latest_decision_minutes=decisions[-1]['minute']-filed['minute'] if filed and decisions and not pending and state['stage']!='WITHDRAWN' else None,
                remand_cycles=sum(p['stage']=='REMANDED' for p in path),
                notice_revisions=max(0,sum(p['stage']=='NOTICE_RECORDED' for p in path)-1),
                judicial_outcomes_assessed=False,remedy_effectiveness_verified=False,recidivism_assessed=False,
                closure_path=('REMEDY_RECORD' if path[-2]['stage']=='REMEDY_REVIEW' else 'REENTRY_RECORD') if state['stage']=='CLOSED' else None)

def observation_value(contract,params):
    value,num,den=params['value'],params['numerator'],params['denominator']
    if value is None and num is None and den is None:
        return None,text(params['missing_reason'],'missing observation reason')
    if params['missing_reason'] is not None:raise ValueError('known observation must have null missing reason')
    if contract['kind']=='RATIO':
        if value is not None:raise ValueError('ratio value is calculated from numerator and denominator')
        bounded(num,'ratio numerator',0,1000000000);bounded(den,'ratio denominator',1,1000000000)
        if num>den:raise ValueError('proportion numerator cannot exceed denominator')
        return num/den,None
    if num is not None or den is not None:raise ValueError('non-ratio observation has no numerator/denominator')
    if contract['kind'] in {'COUNT','INTEGER_MINOR_UNITS'}:
        bounded(value,'observation value',0,1000000000000 if contract['kind']=='INTEGER_MINOR_UNITS' else 1000000000)
    elif type(value) not in {int,float} or not math.isfinite(value) or not 0<=value<=10000000:
        raise ValueError('minutes must be a finite bounded nonnegative number')
    return value,None

def bounded(value,name,minimum=0,maximum=1000000):
    if type(value) is not int or not minimum<=value<=maximum:
        raise ValueError(name+' requires a bounded integer')
    return value

def fingerprint(state):
    return hashlib.sha256(json.dumps(state,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def initial(start_at,workflow='permit'):
    start=configuration(workflow)['initial']
    return dict(stage=start,execution='RUNNING',quality='UNREVIEWED',clock_minutes=0,
                start_at=start_at,path=[dict(stage=start,minute=0)],reviews=[])

def route(target,workflow='permit'):
    config=configuration(workflow);stages=config['stages']
    target=text(target,'preset stage',100)
    if target not in stages:raise ValueError('unknown preset state')
    queue=deque([[config['initial']]])
    while queue:
        path=queue.popleft()
        if path[-1]==target:return path
        for stage in sorted(stages[path[-1]]):
            if stage not in path:queue.append(path+[stage])
    raise ValueError('unreachable preset state')

def controls(state,workflow='permit'):
    config=configuration(workflow);active=state['stage'] not in config['terminal']
    running=state['execution']=='RUNNING';structural=sorted(config['stages'][state['stage']]);blocked={}
    gate=review_gates(config).get(state['stage'])
    if gate and gate['target'] in structural and not acceptance_current(state):
        blocked[gate['target']]='Passing check of this exact '+gate['label']+' revision required.'
    return dict(step=active and running,next_stages=[s for s in structural if s not in blocked] if active and running else [],
                structural_next_stages=structural,blocked_next_stages=blocked,
                pause=active and running,resume=active and state['execution'] in {'PAUSED','STOPPED'},
                stop=active and state['execution'] in {'RUNNING','PAUSED'},tick=True,
                review=state['stage'] in config['review_stages'] and (workflow=='permit' or running),
                preset=True,restore=True,
                reason='The next phase needs a separate passing check for the current '+gate['label']+' revision.' if blocked and running else
                'Choose a valid transition.' if active and running else
                'Terminal workflow state: inspect, review where applicable, restore or load a preset.' if not active else
                'Resume the simulation before changing workflow state.')

class Scenarios:
    def __init__(self,store):self.store=store

    def attachment_status(self,state,db):
        result=[]
        for ref in state.get('attachments',{}).values():
            row=db.execute('SELECT body,version FROM scenario_runs WHERE id=?',(ref['source_run_id'],)).fetchone()
            event=db.execute('SELECT body FROM scenario_events WHERE run_id=? AND sequence=?',(ref['source_run_id'],ref['source_sequence'])).fetchone()
            valid=False;current=False;completed=False
            if row and event:
                source=json.loads(row['body']);snapshot=json.loads(event['body'])['state']
                valid=fingerprint(snapshot)==ref['state_sha256']
                current=row['version']==ref['source_sequence'] and fingerprint(source['state'])==ref['state_sha256']
                config=configuration(source.get('workflow','permit'))
                contracts={m['id']:m for m in config.get('metrics',[])}
                measured=any(o['value'] is not None and o['path_index']==len(snapshot['path'])-1 and metric in contracts and o['contract_sha256']==fingerprint(contracts[metric]) for metric,o in snapshot.get('observations',{}).items())
                completed=snapshot['stage']==config['completion'] and snapshot['quality']=='PASS' and measured
            result.append({**ref,'snapshot_intact':valid,'source_current':current,'completed_with_current_observation':completed})
        return result

    def capstone_ready(self,state,db):
        return any(r['snapshot_intact'] and r['source_current'] and r['completed_with_current_observation'] for r in self.attachment_status(state,db))


    def run(self,key,db=None):
        if db is None:
            with self.store.connect() as connection:return self.run(key,connection)
        row=db.execute('SELECT * FROM scenario_runs WHERE id=?',(key,)).fetchone()
        if not row:raise KeyError('synthetic scenario not found')
        result=json.loads(row['body'])
        state=result['state'];workflow=result.get('workflow','permit');result['workflow']=workflow
        result.update(run_id=key,version=row['version'],controls=controls(state,workflow),state_sha256=fingerprint(state),
                      kind='SYNTHETIC',execution_authorized=False,legal_review='REQUIRED',
                      history=[json.loads(r['body']) for r in db.execute('SELECT body FROM scenario_events WHERE run_id=? ORDER BY sequence',(key,))])
        if workflow=='p050' and state['stage'] in configuration(workflow)['review_stages'] and not self.capstone_ready(state,db):
            result['controls']['next_stages']=[x for x in result['controls']['next_stages'] if x!='CLOSED']
            result['controls']['blocked_next_stages']['CLOSED']='Attach a current completed scenario snapshot with a current known observation.'
            result['controls']['reason']='Capstone closure requires current linked completed evidence with a known observation.'
        return result

    def runs(self):
        with self.store.connect() as db:return [self.run(r['id'],db) for r in db.execute('SELECT id FROM scenario_runs ORDER BY id')]

    def create(self,data):
        if not isinstance(data,dict):raise ValueError('scenario requires an object')
        data=dict(data);workflow=data.pop('workflow','permit');configuration(workflow)
        fields(data,'run_id label start_at actor note')
        key=identifier(data['run_id']);label=text(data['label'],'fictional scenario label',200)
        actor=text(data['actor'],'actor',200);note=text(data['note'],'scenario rationale')
        start=timestamp(data['start_at']).isoformat();state=initial(start,workflow)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT id FROM scenario_runs WHERE id=?',(key,)).fetchone():raise Conflict('scenario ID exists')
            event=dict(sequence=1,action='CREATE',actor=actor,note=note,parameters={},state=state,state_sha256=fingerprint(state),restored_from=None)
            db.execute('INSERT INTO scenario_runs VALUES (?,?,1)',(key,json.dumps(dict(label=label,workflow=workflow,state=state))))
            db.execute('INSERT INTO scenario_events VALUES (?,1,?)',(key,json.dumps(event)))
            self.store.log(db,actor,'create_synthetic_scenario',key,event)
            return self.run(key,db)

    def command(self,key,data):
        fields(data,'version action actor note parameters')
        action=text(data['action'],'scenario action',100)
        if action not in ACTIONS:raise ValueError('unknown scenario action')
        fields(data['parameters'],ACTIONS[action])
        params=deepcopy(data['parameters'])
        actor=text(data['actor'],'actor',200);note=text(data['note'],'reason/evidence for scenario command')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');run=self.run(key,db)
            if type(data['version']) is not int:raise ValueError('integer version required')
            if data['version']!=run['version']:raise Conflict('Scenario changed. Reload before controlling it.')
            if len(run['history'])>=10000:raise ValueError('scenario history limit reached; create another scenario')
            state=deepcopy(run['state']);workflow=run['workflow'];config=configuration(workflow)
            allowed=controls(state,workflow);restored_from=None
            if action in {'STEP','TICK'}:
                minutes=bounded(params['minutes'],'elapsed minutes',1)
                if state['clock_minutes']+minutes>10000000:raise ValueError('scenario clock limit exceeded')
                if action=='STEP':
                    target=text(params['stage'],'next stage',100)
                    if not allowed['step']:raise ValueError(allowed['reason'])
                    if target not in config['stages'][state['stage']]:raise ValueError('invalid workflow transition')
                    if workflow=='p050' and target=='CLOSED' and not self.capstone_ready(state,db):raise ValueError('capstone closure requires current completed scenario evidence with a known observation')
                    gate=review_gates(config).get(state['stage'])
                    if gate and target==gate['target'] and not acceptance_current(state):raise ValueError('phase transition requires a passing check for the current '+gate['label']+' revision')
                    state['clock_minutes']+=minutes;state['stage']=target
                    state['path'].append(dict(stage=target,minute=state['clock_minutes'],actor=actor))
                    if config.get('gate_anchors') and target!='CLOSED':state.update(quality='UNREVIEWED',review_path_index=None)
                    if target in config['terminal']:state['execution']='COMPLETED'
                else:state['clock_minutes']+=minutes
            elif action=='PAUSE':
                if not allowed['pause']:raise ValueError('pause is unavailable in this state')
                state['execution']='PAUSED'
            elif action=='RESUME':
                if not allowed['resume']:raise ValueError('resume is unavailable in this state')
                state['execution']='RUNNING'
            elif action=='STOP':
                if not allowed['stop']:raise ValueError('stop is unavailable in this state')
                state['execution']='STOPPED'
            elif action=='REVIEW':
                if not allowed['review']:raise ValueError('review is unavailable in this workflow/execution state')
                if type(params['passed']) is not bool:raise ValueError('passed requires boolean')
                if config.get('gate_anchors'):
                    gate=review_gates(config)[state['stage']]
                    anchors=[next((p for p in reversed(state['path']) if p['stage']==stage),None) for stage in gate['anchors']]
                    if any(p is None or p.get('actor')==actor for p in anchors):raise ValueError(gate['error'])
                    state['review_path_index']=len(state['path'])-1
                state['quality']='PASS' if params['passed'] else 'FAIL'
                state['reviews'].append(dict(passed=params['passed'],minute=state['clock_minutes'],actor=actor,note=note,path_index=len(state['path'])-1,stage=state['stage']))
            elif action=='PRESET':
                target=text(params['stage'],'preset stage',100);quality=text(params['quality'],'preset quality',100)
                if quality not in QUALITY or (target not in config['review_stages'] and target!=config['completion'] and quality!='UNREVIEWED'):raise ValueError('quality outcomes are unavailable for this preset')
                if config.get('gate_anchors') and target=='CLOSED' and quality!='PASS':raise ValueError('CLOSED preset requires PASS quality; use the review state for unchecked/failed outcomes')
                refs=deepcopy(state.get('attachments',{}))
                if workflow=='p050' and target=='CLOSED' and not self.capstone_ready(state,db):raise ValueError('capstone CLOSED preset requires current completed scenario evidence with a known observation')
                path=route(target,workflow);state=initial(state['start_at'],workflow)
                if workflow=='p050' and target=='CLOSED':state['attachments']=refs
                for stage in path[1:]:
                    gate=review_gates(config).get(state['stage'])
                    if gate and stage==gate['target']:
                        state['quality']='PASS';state['review_path_index']=len(state['path'])-1
                        state['reviews'].append(dict(passed=True,minute=state['clock_minutes'],actor='SYN-PRESET-CHECKER',note='Explicit fictional '+gate['label']+' check before '+stage+' preset',path_index=len(state['path'])-1,stage=state['stage']))
                    state['clock_minutes']+=60;state['stage']=stage
                    state['path'].append(dict(stage=stage,minute=state['clock_minutes'],actor='SYN-PRESET-RECORDER'))
                    if config.get('gate_anchors') and stage!='CLOSED':state.update(quality='UNREVIEWED',review_path_index=None)
                if target in config['terminal']:state['execution']='COMPLETED'
                if quality!='UNREVIEWED' and not (config.get('gate_anchors') and target=='CLOSED'):
                    state['quality']=quality;state['review_path_index']=len(state['path'])-1
                    state['reviews'].append(dict(passed=quality=='PASS',minute=state['clock_minutes'],actor='SYN-PRESET-CHECKER',note='Fictional preset outcome: '+note))
            elif action=='OBSERVE':
                metric_id=text(params['metric_id'],'metric ID',100)
                contract=next((m for m in config.get('metrics',[]) if m['id']==metric_id),None)
                if not contract:raise ValueError('unknown metric contract for this workflow')
                value,missing=observation_value(contract,params)
                state.setdefault('observations',{})[metric_id]=dict(value=value,numerator=params['numerator'],denominator=params['denominator'],missing_reason=missing,
                    contract_sha256=fingerprint(contract),path_index=len(state['path'])-1,actor=actor,note=note)
            elif action=='ATTACH':
                if workflow!='p050':raise ValueError('snapshot attachment is available only in the capstone workflow')
                source_id=identifier(params['source_run_id']);seq=bounded(params['source_sequence'],'source sequence',1,10000)
                if source_id==key:raise ValueError('capstone cannot attach itself')
                source=self.run(source_id,db)
                if source['workflow']=='p050':raise ValueError('nested capstone attachments are not supported')
                item=next((e for e in source['history'] if e['sequence']==seq),None)
                if not item:raise ValueError('source snapshot not found')
                if fingerprint(item['state'])!=item['state_sha256']:raise ValueError('source snapshot hash mismatch')
                state.setdefault('attachments',{})[source_id]=dict(source_run_id=source_id,source_sequence=seq,source_workflow=source['workflow'],state_sha256=item['state_sha256'])
                state.update(quality='UNREVIEWED',review_path_index=None)
            elif action=='RESTORE':
                seq=bounded(params['sequence'],'snapshot sequence',1,10000)
                previous=next((e for e in run['history'] if e['sequence']==seq),None)
                if not previous:raise ValueError('snapshot not found in this scenario')
                state=deepcopy(previous['state']);restored_from=seq
            try:timestamp(state['start_at'])+timedelta(minutes=state['clock_minutes'])
            except OverflowError:raise ValueError('scenario time exceeds supported calendar')
            event=dict(sequence=len(run['history'])+1,action=action,actor=actor,note=note,parameters=params,
                       before_sha256=fingerprint(run['state']),state=state,state_sha256=fingerprint(state),restored_from=restored_from)
            db.execute('INSERT INTO scenario_events VALUES (?,?,?)',(key,event['sequence'],json.dumps(event)))
            db.execute('UPDATE scenario_runs SET body=?,version=version+1 WHERE id=?',(json.dumps(dict(label=run['label'],workflow=workflow,state=state)),key))
            self.store.log(db,actor,'control_synthetic_scenario',key,event)
            return self.run(key,db)

    def report(self,key):
        run=self.run(key);state=run['state'];workflow=run['workflow'];config=configuration(workflow)
        last=state['path'][-1];terminal=state['stage'] in config['terminal']
        durations={stage:0 for stage in config['stages']}
        for i,event in enumerate(state['path']):
            end=state['path'][i+1]['minute'] if i+1<len(state['path']) else state['clock_minutes']
            if event['stage'] not in config['terminal']:durations[event['stage']]+=end-event['minute']
        observations=[]
        for contract in config.get('metrics',[]):
            item=state.get('observations',{}).get(contract['id'])
            observations.append(dict(contract=contract,value=item['value'] if item else None,numerator=item['numerator'] if item else None,
                denominator=item['denominator'] if item else None,missing_reason=item['missing_reason'] if item else 'No observation',
                path_current=bool(item and item['path_index']==len(state['path'])-1),contract_current=bool(item and item['contract_sha256']==fingerprint(contract))))
        with self.store.connect() as db:
            attachments=self.attachment_status(state,db)
            capstone_ready=self.capstone_ready(state,db) if workflow=='p050' else None
        return dict(justice_diagnostics(state) if workflow=='justice' else {},project_id=config['project_id'],
                    observations=observations,attachments=attachments,capstone_evidence_current=capstone_ready,
                    layer_a_status='LEGAL_REVIEW_REQUIRED',source_basis=config.get('source_basis','Existing bounded synthetic prototype; qualified acceptance remains pending'),
                    scope=config.get('scope',config['label']),safeguard=config.get('safeguard','Synthetic-only controlled rehearsal; real authority is not established'),
                    run_id=key,kind='SYNTHETIC',workflow=workflow,completion_elapsed_minutes=last['minute'] if state['stage']==config['completion'] else None,stage=state['stage'],execution=state['execution'],quality=state['quality'],
                    scenario_time=(timestamp(state['start_at'])+timedelta(minutes=state['clock_minutes'])).isoformat(),
                    clock_minutes=state['clock_minutes'],decision_elapsed_minutes=last['minute'] if state['stage']=='DECIDED' else None,
                    open_age_minutes=None if terminal else state['clock_minutes'],stage_minutes=durations,
                    correction_cycles=sum(p['stage']==config['correction'] for p in state['path']),
                    service_interruptions=sum(p['stage']=='INTERRUPTED' for p in state['path']) if workflow in {'education','health'} else None,
                    service_start_elapsed_minutes=next((p['minute'] for p in state['path'] if p['stage']=='SERVICE_STARTED'),None) if workflow in {'education','health'} else None,
                    learning_outcomes_assessed=False if workflow=='education' else None,
                    clinical_outcomes_assessed=False if workflow=='health' else None,
                    referral_wait_minutes=durations.get('WAITING',0) if workflow=='health' else None,
                    repeat_referrals=max(0,sum(p['stage']=='REFERRAL_RECORDED' for p in state['path'])-1) if workflow=='health' else None,
                    consent_status=('WITHDRAWAL_RECORDED' if state['stage']=='CONSENT_WITHDRAWN' else 'ASSERTED_ONLY' if any(p['stage']=='CONSENT_RECORDED' for p in state['path']) else 'NOT_RECORDED') if workflow=='health' else None,
                    exercise_response_minutes=(next((p['minute'] for p in state['path'] if p['stage']=='RESPONSE_RECORDED'),0)-next((p['minute'] for p in state['path'] if p['stage']=='EXERCISE_STARTED'),0)) if workflow=='emergency' and any(p['stage']=='RESPONSE_RECORDED' for p in state['path']) else None,
                    readiness_revisions=max(0,sum(p['stage']=='READINESS_RECORDED' for p in state['path'])-1) if workflow=='emergency' else None,
                    correction_revisions=max(0,sum(p['stage']=='CORRECTION_RECORDED' for p in state['path'])-1) if workflow=='emergency' else None,
                    live_dispatch_enabled=False if workflow=='emergency' else None,
                    operational_readiness_certified=False if workflow=='emergency' else None,
                    history_events=len(run['history']),execution_authorized=False,legal_review='REQUIRED',
                    method='Manual deterministic scenario clock; no background automation. TICK advances fictional time even while paused/stopped or terminal. PAUSE/STOP freeze workflow transitions until RESUME, not the manual clock. PRESET replays a shortest valid path at 60 minutes per edge; RESTORE copies a prior snapshot into a new append-only event. Neither deletes history. Quality outcomes and preset reviews are fictional assertions. Procurement, education and health-referral closure require a distinct-recorder check pinned to the current path revision; changed delivery, follow-up, interruptions or corrections invalidate it. Education and health-referral check identifiers must differ from both current service and follow-up recorders. Health consent records are fictional assertions; no clinical outcomes, triage, diagnosis or actual referrals are assessed or performed. Emergency phase gates require separate current readiness/correction checks, not operational certification; there is no live dispatch. Justice notice/remedy/reentry checks are fictional record checks, never judicial rulings, rights certification, remedy-effectiveness proof or release decisions. Metric observations are supplied fictional values, with path/contract freshness and missingness explicit. Capstone links immutable scenario snapshots but requires current completed observed evidence before closure; Layer A remains LEGAL_REVIEW_REQUIRED. No learning, eligibility or ranking inference is made. CLOSED presets include an explicit fictional check. This isolated controller does not issue awards, payments, permit approvals, project/source completion, government actions or Layer A holds.')
