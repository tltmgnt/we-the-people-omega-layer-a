"""Deterministic permit-use-case controls; isolated from domain/authority records."""
from collections import deque
from copy import deepcopy
from datetime import timedelta
import hashlib
import json
from .maintenance import fields, identifier
from .permits import STAGES, TERMINAL, timestamp
from .store import Conflict, text

ACTIONS={
    'STEP':'stage minutes',
    'TICK':'minutes',
    'PAUSE':'',
    'RESUME':'',
    'STOP':'',
    'REVIEW':'passed',
    'PRESET':'stage quality',
    'RESTORE':'sequence',
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
WORKFLOWS={
    'permit':dict(label='Project 009 — fictional permit',initial='RECEIVED',stages=STAGES,
                  terminal=TERMINAL,review_stages={'DECIDED'},completion='DECIDED',correction='AWAITING_CORRECTION'),
    'procurement':dict(label='Project 019 — fictional procurement and delivery',initial='DRAFT',stages=PROCUREMENT_STAGES,
                  terminal={'CLOSED','CANCELLED'},review_stages={'ACCEPTANCE_REVIEW'},completion='CLOSED',correction='CORRECTION_REQUESTED'),
}

def configuration(workflow):
    workflow=text(workflow,'workflow',100)
    if workflow not in WORKFLOWS:raise ValueError('unknown scenario workflow')
    return WORKFLOWS[workflow]

def catalog():
    return {key:{**{k:v for k,v in c.items() if k not in {'stages','terminal','review_stages'}},
                 'stages':{k:sorted(v) for k,v in c['stages'].items()},'terminal':sorted(c['terminal']),
                 'review_stages':sorted(c['review_stages'])} for key,c in WORKFLOWS.items()}

def acceptance_current(state):
    return state['quality']=='PASS' and state.get('review_path_index')==len(state['path'])-1


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
    if workflow=='procurement' and 'CLOSED' in structural and not acceptance_current(state):
        blocked['CLOSED']='Passing check of this exact acceptance revision required.'
    return dict(step=active and running,next_stages=[s for s in structural if s not in blocked] if active and running else [],
                structural_next_stages=structural,blocked_next_stages=blocked,
                pause=active and running,resume=active and state['execution'] in {'PAUSED','STOPPED'},
                stop=active and state['execution'] in {'RUNNING','PAUSED'},tick=True,
                review=state['stage'] in config['review_stages'] and (workflow=='permit' or running),
                preset=True,restore=True,
                reason='Closure needs a separate passing check for the current acceptance revision.' if blocked and running else
                'Choose a valid transition.' if active and running else
                'Terminal workflow state: inspect, review where applicable, restore or load a preset.' if not active else
                'Resume the simulation before changing workflow state.')

class Scenarios:
    def __init__(self,store):self.store=store

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
                    if workflow=='procurement' and target=='CLOSED' and not acceptance_current(state):raise ValueError('closure requires a passing check for the current acceptance revision')
                    state['clock_minutes']+=minutes;state['stage']=target
                    state['path'].append(dict(stage=target,minute=state['clock_minutes'],actor=actor))
                    if workflow=='procurement' and target!='CLOSED':state.update(quality='UNREVIEWED',review_path_index=None)
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
                if workflow=='procurement':
                    delivery=next((p for p in reversed(state['path']) if p['stage']=='DELIVERY_RECORDED'),None)
                    if not delivery or delivery.get('actor')==actor:raise ValueError('acceptance requires a checker distinct from the current delivery recorder')
                    state['review_path_index']=len(state['path'])-1
                state['quality']='PASS' if params['passed'] else 'FAIL'
                state['reviews'].append(dict(passed=params['passed'],minute=state['clock_minutes'],actor=actor,note=note))
            elif action=='PRESET':
                target=text(params['stage'],'preset stage',100);quality=text(params['quality'],'preset quality',100)
                if quality not in QUALITY or (target not in config['review_stages'] and target!=config['completion'] and quality!='UNREVIEWED'):raise ValueError('quality outcomes are unavailable for this preset')
                if workflow=='procurement' and target=='CLOSED' and quality!='PASS':raise ValueError('CLOSED preset requires PASS quality; use ACCEPTANCE_REVIEW for unchecked/failed states')
                path=route(target,workflow);state=initial(state['start_at'],workflow)
                for stage in path[1:]:
                    if workflow=='procurement' and stage=='CLOSED':
                        state['quality']='PASS';state['review_path_index']=len(state['path'])-1
                        state['reviews'].append(dict(passed=True,minute=state['clock_minutes'],actor='SYN-PRESET-CHECKER',note='Explicit fictional acceptance check in CLOSED preset',path_index=len(state['path'])-1))
                    state['clock_minutes']+=60;state['stage']=stage
                    state['path'].append(dict(stage=stage,minute=state['clock_minutes'],actor='SYN-PRESET-RECORDER'))
                if target in config['terminal']:state['execution']='COMPLETED'
                if quality!='UNREVIEWED' and not (workflow=='procurement' and target=='CLOSED'):
                    state['quality']=quality;state['review_path_index']=len(state['path'])-1
                    state['reviews'].append(dict(passed=quality=='PASS',minute=state['clock_minutes'],actor='SYN-PRESET-CHECKER',note='Fictional preset outcome: '+note))
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
        return dict(run_id=key,kind='SYNTHETIC',workflow=workflow,completion_elapsed_minutes=last['minute'] if state['stage']==config['completion'] else None,stage=state['stage'],execution=state['execution'],quality=state['quality'],
                    scenario_time=(timestamp(state['start_at'])+timedelta(minutes=state['clock_minutes'])).isoformat(),
                    clock_minutes=state['clock_minutes'],decision_elapsed_minutes=last['minute'] if state['stage']=='DECIDED' else None,
                    open_age_minutes=None if terminal else state['clock_minutes'],stage_minutes=durations,
                    correction_cycles=sum(p['stage']==config['correction'] for p in state['path']),
                    history_events=len(run['history']),execution_authorized=False,legal_review='REQUIRED',
                    method='Manual deterministic scenario clock; no background automation. TICK advances fictional time even while paused/stopped or terminal. PAUSE/STOP freeze workflow transitions until RESUME, not the manual clock. PRESET replays a shortest valid path at 60 minutes per edge; RESTORE copies a prior snapshot into a new append-only event. Neither deletes history. Quality outcomes and preset reviews are fictional assertions. Procurement closure requires a distinct-recorder acceptance check pinned to the current path revision; changed delivery/corrections invalidate it. CLOSED presets include an explicit fictional check. This isolated controller does not issue awards, payments, permit approvals, project/source completion, government actions or Layer A holds.')
