"""Project 023: fictional justice-process observatory; never adjudication."""
import hashlib
import json
from .maintenance import fields, identifier
from .permits import timestamp, statistic
from .store import Conflict, text

DIMENSIONS=('TOPOLOGY','POWER','BOUNDARIES','INFORMATION','INCENTIVES','CONTROL','RESILIENCE','LEGITIMACY','TRANSITION','INSTITUTIONALIZATION')
MODULES=('ACCESS','CASEFLOW','FAIRNESS','CONDITIONS','REHABILITATION','REENTRY','REMEDIES','FINANCE')
ROLES=('LEGAL_SOURCE','STATISTICAL','OPERATIONS','ECONOMIC','REHABILITATION','RISK_RIGHTS','HUMAN_REVIEW')
STAGES={'ACCESS':{'FILED'},'FILED':{'FIRST_ACTION','FILED'},'FIRST_ACTION':{'RESOLVED','FIRST_ACTION'},'RESOLVED':{'REMEDY','FIRST_ACTION','CUSTODY','RELEASE'},'REMEDY':{'FIRST_ACTION','RELEASE'},'CUSTODY':{'REMEDY','RELEASE','CUSTODY'},'SUPERVISION':{'REINTEGRATION','REMEDY','SUPERVISION'},'RELEASE':{'REINTEGRATION','SUPERVISION'},'REINTEGRATION':{'RELEASE'}}
SCHEMAS={
'EVIDENCE':'evidence_id content origin level corroborating_sources verification_reference limitations',
'GAP':'gap_id dimension module question owner authority review_route alternative_explanation pins',
'CASE':'case_id case_type complexity urgency stage pins',
'TRANSITION':'case_id stage owner authority review_route waiting_minutes active_minutes cause classification pins',
'REMEDY':'remedy_id gap_id status owner description pins',
'REMEDY_CHECK':'remedy_id passed implementation_sequence pins',
'REMEDY_STATUS':'remedy_id status description pins',
'METRIC':'metric_id module definition unit measure numerator_definition denominator_definition period owner exclusions uncertainty subgroup correction_process counter_metric pins',
'OBSERVATION':'metric_id numerator denominator missing_reason pins',
'REVIEW':'role conclusion disagreement analysis_sequence pins',
'PHASE':'phase owner finding limitations pins'}

def integer(value,name,maximum=1000000000):
    if type(value) is not int or not 0<=value<=maximum:raise ValueError(name+' requires a nonnegative bounded integer')
    return value

def choice(value,options,name):
    value=text(value,name,200)
    if value not in options:raise ValueError('invalid '+name)
    return value

class Justice:
    def __init__(self,store):self.store=store

    def pilot(self,key,db=None):
        if db is None:
            with self.store.connect() as c:return self.pilot(key,c)
        row=db.execute('SELECT * FROM justice_pilots WHERE id=?',(key,)).fetchone()
        if not row:raise KeyError('synthetic justice pilot not found')
        result=json.loads(row['body']);result['version']=row['version']
        result['events']=[json.loads(r['body']) for r in db.execute('SELECT body FROM justice_events WHERE pilot_id=? ORDER BY sequence',(key,))]
        result.update(execution_authorized=False,institutional_acceptance='NOT_ESTABLISHED',kind='SYNTHETIC')
        return result

    def pilots(self):
        with self.store.connect() as db:return [self.pilot(r['id'],db) for r in db.execute('SELECT id FROM justice_pilots ORDER BY id')]

    def create(self,data):
        fields(data,'pilot_id label jurisdiction process_owner data_steward authority privacy_rules challenge_route at actor')
        body={k:text(v,k,2000) for k,v in data.items() if k not in {'pilot_id','at'}}
        body['pilot_id']=identifier(data['pilot_id']);body['at']=timestamp(data['at']).isoformat()
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT id FROM justice_pilots WHERE id=?',(body['pilot_id'],)).fetchone():raise Conflict('pilot already exists')
            db.execute('INSERT INTO justice_pilots VALUES (?,?,1)',(body['pilot_id'],json.dumps(body)))
            self.store.log(db,body['actor'],'create_synthetic_justice_pilot',body['pilot_id'],body)
            return self.pilot(body['pilot_id'],db)

    @staticmethod
    def evidence(events,pin):
        fields(pin,'evidence_id revision')
        key=identifier(pin['evidence_id']);integer(pin['revision'],'revision')
        item=next((e for e in events if e['kind']=='EVIDENCE' and e['data']['evidence_id']==key and e['data']['revision']==pin['revision']),None)
        if not item:raise ValueError('evidence revision does not exist in this pilot')
        return item

    def pins(self,events,pins):
        if not isinstance(pins,list) or not 1<=len(pins)<=20:raise ValueError('one through twenty evidence pins required')
        seen=set()
        for pin in pins:
            self.evidence(events,pin);pair=(pin['evidence_id'],pin['revision'])
            if pair in seen:raise ValueError('duplicate evidence pin')
            seen.add(pair)

    def current(self,events,pins):
        return all(max(e['data']['revision'] for e in events if e['kind']=='EVIDENCE' and e['data']['evidence_id']==p['evidence_id'])==p['revision'] for p in pins)

    @staticmethod
    def analysis_sequence(events):return max((e['sequence'] for e in events if e['kind']!='REVIEW'),default=0)

    def record(self,key,data):
        fields(data,'version kind at actor data');kind=choice(data['kind'],SCHEMAS,'record kind')
        fields(data['data'],SCHEMAS[kind]);payload=dict(data['data']);actor=text(data['actor'],'actor',200);at=timestamp(data['at']).isoformat()
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');pilot=self.pilot(key,db);events=pilot['events']
            if type(data['version']) is not int:raise ValueError('integer version required')
            if pilot['version']!=data['version']:raise Conflict('Pilot changed. Reload before saving.')
            if timestamp(at)<timestamp(events[-1]['at'] if events else pilot['at']):raise ValueError('record precedes latest pilot activity')
            for name,value in list(payload.items()):
                if name.endswith('_id'):payload[name]=identifier(value)
                elif isinstance(value,str) and name!='content':payload[name]=text(value,name,10000)
            if kind!='EVIDENCE':self.pins(events,payload['pins'])
            def records(k):return [e for e in events if e['kind']==k]
            def find(k,id_name,value):
                found=[e for e in records(k) if e['data'][id_name]==value]
                if not found:raise ValueError('referenced '+k+' does not exist in this pilot')
                return found[-1]
            def unique(k,id_name):
                if any(e['data'][id_name]==payload[id_name] for e in records(k)):raise Conflict('record identifier already exists')
            if kind=='EVIDENCE':
                text(payload['content'],'content',100000)  # Validate without changing snapshot bytes.
                for name in ('origin','limitations'):payload[name]=text(payload[name],name,100000)
                choice(payload['level'],('A','B','C'),'evidence level')
                sources=payload['corroborating_sources']
                if not isinstance(sources,list) or len(sources)>20:raise ValueError('corroborating sources must be a bounded list')
                sources=[text(s,'corroborating source',2000) for s in sources]
                if len(set(sources))!=len(sources):raise ValueError('duplicate corroborating source')
                payload['corroborating_sources']=sources
                if payload['level']=='B' and len(set([payload['origin'],*sources]))<2:raise ValueError('level B needs at least two distinct source references')
                if payload['verification_reference'] is not None:payload['verification_reference']=text(payload['verification_reference'],'verification reference',2000)
                if payload['level']=='A' and not payload['verification_reference']:raise ValueError('level A needs an asserted official/independent verification reference')
                payload['sha256']=hashlib.sha256(payload['content'].encode()).hexdigest()
                payload['revision']=1+sum(e['data']['evidence_id']==payload['evidence_id'] for e in records('EVIDENCE'))
            elif kind=='GAP':
                unique(kind,'gap_id');choice(payload['dimension'],DIMENSIONS,'dimension');choice(payload['module'],MODULES,'module')
                for name in ('question','owner','authority','review_route','alternative_explanation'):payload[name]=text(payload[name],name)
            elif kind=='CASE':
                unique(kind,'case_id');choice(payload['stage'],('ACCESS','CUSTODY','RELEASE'),'initial stage')
                for name in ('case_type','complexity','urgency'):payload[name]=text(payload[name],name,200)
            elif kind=='TRANSITION':
                case=find('CASE','case_id',payload['case_id']);history=[e for e in events if e['kind'] in {'CASE','TRANSITION'} and e['data']['case_id']==payload['case_id']];last=history[-1]
                choice(payload['stage'],STAGES[last['data']['stage']],'stage transition')
                choice(payload['classification'],('AVOIDABLE_ASSERTED','NECESSARY_SAFEGUARD','COMPLEXITY','PARTY','UNKNOWN'),'delay classification')
                payload['cause']=text(payload['cause'],'cause and uncertainty')
                for name in ('owner','authority','review_route'):payload[name]=text(payload[name],name)
                wait,active=payload['waiting_minutes'],payload['active_minutes']
                if (wait is None)!=(active is None):raise ValueError('waiting and active time must both be known or both null')
                if wait is not None:
                    integer(wait,'waiting minutes');integer(active,'active minutes')
                    if wait+active>(timestamp(at)-timestamp(last['at'])).total_seconds()/60:raise ValueError('measured waiting plus active time exceeds interval')
            elif kind=='REMEDY':
                unique(kind,'remedy_id');find('GAP','gap_id',payload['gap_id']);choice(payload['status'],('OPEN',),'initial remedy status')
                payload['owner']=text(payload['owner'],'remedy owner');payload['description']=text(payload['description'],'remedy description')
            elif kind in {'REMEDY_STATUS','REMEDY_CHECK'}:
                find('REMEDY','remedy_id',payload['remedy_id'])
                history=[e for e in events if e['kind'] in {'REMEDY','REMEDY_STATUS'} and e['data']['remedy_id']==payload['remedy_id']];last=history[-1]
                if kind=='REMEDY_CHECK':
                    if last['data']['status']!='IMPLEMENTED':raise ValueError('record implementation before checking')
                    if type(payload['passed']) is not bool:raise ValueError('passed must be boolean')
                    integer(payload['implementation_sequence'],'implementation sequence')
                    if payload['implementation_sequence']!=last['sequence']:raise Conflict('check must reference current implementation sequence')
                    if last['actor']==actor:raise ValueError('use a distinct checker from the implementation recorder')
                    if not self.current(events,last['data']['pins']+payload['pins']):raise ValueError('implementation/check evidence is stale')
                else:
                    allowed={'OPEN':{'IMPLEMENTED'},'IMPLEMENTED':{'IMPLEMENTED','CLOSED'},'CLOSED':{'REOPENED'},'REOPENED':{'IMPLEMENTED'}}
                    choice(payload['status'],allowed[last['data']['status']],'remedy transition');payload['description']=text(payload['description'],'remedy implementation or reopening explanation')
                    if payload['status']=='CLOSED':
                        checks=[e for e in records('REMEDY_CHECK') if e['data']['remedy_id']==payload['remedy_id'] and e['data']['implementation_sequence']==last['sequence']]
                        if not checks or not checks[-1]['data']['passed'] or not self.current(events,last['data']['pins']+checks[-1]['data']['pins']+payload['pins']):raise ValueError('closure requires a passing current implementation check and current evidence')
            elif kind=='METRIC':
                unique(kind,'metric_id');choice(payload['module'],MODULES,'metric module');choice(payload['measure'],('COUNT','RATIO'),'measure')
                for name in SCHEMAS[kind].split():
                    if name not in {'pins','metric_id','module','measure'}:payload[name]=text(payload[name],name)
            elif kind=='OBSERVATION':
                metric=find('METRIC','metric_id',payload['metric_id'])['data']
                if payload['numerator'] is None:
                    if payload['denominator'] is not None:raise ValueError('missing numerator requires null denominator')
                    payload['missing_reason']=text(payload['missing_reason'],'missing-data reason')
                else:
                    integer(payload['numerator'],'numerator')
                    if payload['missing_reason'] is not None:raise ValueError('known observation must have null missing reason')
                    if metric['measure']=='RATIO':
                        integer(payload['denominator'],'denominator')
                        if payload['denominator']==0:raise ValueError('ratio denominator must be positive; use missing observation for undefined ratios')
                    elif payload['denominator'] is not None:raise ValueError('count must have null denominator')
            elif kind=='REVIEW':
                choice(payload['role'],ROLES,'review role');choice(payload['conclusion'],('OPEN_QUESTIONS','DISAGREEMENT','SUPPORTED_WITH_LIMITS'),'review conclusion')
                payload['disagreement']=text(payload['disagreement'],'reasoning, disagreement and limitations')
                integer(payload['analysis_sequence'],'analysis sequence')
                if payload['analysis_sequence']!=self.analysis_sequence(events):raise Conflict('review must pin the latest analysis sequence')
                if not self.current(events,payload['pins']):raise ValueError('review evidence is stale')
            elif kind=='PHASE':
                choice(payload['phase'],('BASELINE_1_30','DIAGNOSE_31_60','CONTROLLED_TEST_61_90'),'pilot phase')
                for name in ('owner','finding','limitations'):payload[name]=text(payload[name],name)
            event=dict(sequence=len(events)+1,kind=kind,at=at,actor=actor,data=payload)
            db.execute('INSERT INTO justice_events VALUES (?,?,?)',(key,event['sequence'],json.dumps(event)))
            db.execute('UPDATE justice_pilots SET version=version+1 WHERE id=?',(key,));self.store.log(db,actor,'synthetic_justice_'+kind.lower(),key,event)
            return self.pilot(key,db)

    def report(self,key,as_of):
        pilot=self.pilot(key);at=timestamp(as_of)
        if at<timestamp(pilot['at']):raise ValueError('cutoff precedes pilot registration')
        events=[e for e in pilot['events'] if timestamp(e['at'])<=at]
        evidence=[e for e in events if e['kind']=='EVIDENCE'];latest={e['data']['evidence_id']:e for e in evidence}
        gaps=[e for e in events if e['kind']=='GAP'];cases=[e for e in events if e['kind']=='CASE'];casegroups={};intervals=[]
        for case in cases:
            d=case['data'];history=[e for e in events if e['kind'] in {'CASE','TRANSITION'} and e['data']['case_id']==d['case_id']];last=history[-1]
            group=casegroups.setdefault((d['case_type'],d['complexity'],d['urgency']),dict(cases=0,resolutions=0,pending_ages=[],resolution_times=[]));group['cases']+=1
            resolutions=[e for e in history if e['data']['stage']=='RESOLVED'];filed=next((e for e in history if e['data']['stage']=='FILED'),None)
            # Current post-decision/remedy/reentry stages are not pending adjudication; a remand FIRST_ACTION is pending again.
            pending=last['data']['stage'] in {'ACCESS','FILED','FIRST_ACTION'}
            if pending:group['pending_ages'].append((at-timestamp(case['at'])).total_seconds()/3600)
            elif resolutions and filed:
                group['resolutions']+=1;group['resolution_times'].append((timestamp(resolutions[-1]['at'])-timestamp(filed['at'])).total_seconds()/3600)
            for previous,current in zip(history,history[1:]):
                x=current['data'];elapsed=(timestamp(current['at'])-timestamp(previous['at'])).total_seconds()/60
                intervals.append(dict(case_id=d['case_id'],from_stage=previous['data']['stage'],to_stage=x['stage'],elapsed_minutes=elapsed,waiting_minutes=x['waiting_minutes'],active_minutes=x['active_minutes'],unclassified_minutes=None if x['waiting_minutes'] is None else elapsed-x['waiting_minutes']-x['active_minutes'],classification=x['classification'],cause=x['cause']))
        strata=[]
        for (case_type,complexity,urgency),g in casegroups.items():
            strata.append(dict(case_type=case_type,complexity=complexity,urgency=urgency,cases=g['cases'],resolved_cases=g['resolutions'],pending_age_hours=statistic(g['pending_ages']),filing_to_latest_resolution_hours=statistic(g['resolution_times'])))
        remedies=[]
        for r in [e for e in events if e['kind']=='REMEDY']:
            history=[e for e in events if e['kind'] in {'REMEDY','REMEDY_STATUS'} and e['data']['remedy_id']==r['data']['remedy_id']];last=history[-1]
            remedies.append(dict(remedy_id=r['data']['remedy_id'],owner=r['data']['owner'],status=last['data']['status'],open_age_hours=None if last['data']['status']=='CLOSED' else (at-timestamp(r['at'])).total_seconds()/3600,stale_evidence=any(not self.current(events,e['data']['pins']) for e in history),reopen_count=sum(e['data']['status']=='REOPENED' for e in history)))
        metrics=[]
        for m in [e for e in events if e['kind']=='METRIC']:
            observations=[e for e in events if e['kind']=='OBSERVATION' and e['data']['metric_id']==m['data']['metric_id']]
            value=observations[-1] if observations else None;d=value['data'] if value else None
            metrics.append(dict(contract=m['data'],observation_sequence=value['sequence'] if value else None,value=None if not d or d['numerator'] is None else d['numerator'] if m['data']['measure']=='COUNT' else d['numerator']/d['denominator'],numerator=d['numerator'] if d else None,denominator=d['denominator'] if d else None,missing_reason=d['missing_reason'] if d else 'No observation',stale_evidence=not self.current(events,m['data']['pins']+(d['pins'] if d else [])),observation_count=len(observations)))
        reviews={e['data']['role']:e for e in events if e['kind']=='REVIEW'};analysis=self.analysis_sequence(events)
        return dict(kind='SYNTHETIC',pilot_id=key,as_of=at.isoformat(),evidence_levels={level:sum(e['data']['level']==level for e in latest.values()) for level in 'ABC'},gap_matrix=[dict(dimension=dimension,items=[dict(**g['data'],stale_evidence=not self.current(events,g['data']['pins'])) for g in gaps if g['data']['dimension']==dimension]) for dimension in DIMENSIONS],module_coverage={module:sum(g['data']['module']==module for g in gaps) for module in MODULES},caseflow_strata=strata,temporal_intervals=intervals,remedies=remedies,metrics=metrics,review_roles={role:dict(recorded=role in reviews,current=role in reviews and reviews[role]['data']['analysis_sequence']==analysis and self.current(events,reviews[role]['data']['pins']),conclusion=reviews[role]['data']['conclusion'] if role in reviews else None) for role in ROLES},phases=[e for e in events if e['kind']=='PHASE'],stale_record_sequences=[e['sequence'] for e in events if 'pins' in e['data'] and not self.current(events,e['data']['pins'])],analysis_sequence=analysis,execution_authorized=False,legal_review='REQUIRED',institutional_acceptance='NOT_ESTABLISHED',method='Fictional records and local assertions only. A/B/C labels remain separate, unverified by software; no composite score. UTC event cutoff; repeated resolution/remand loops retained. Caseflow strata preserve declared type, complexity and urgency; resolution timing is filing to latest resolution among currently post-decision cases, not clearance rate. Pending age starts at initial scenario registration; reentry-only cases do not enter adjudication duration. Active/waiting time is supplied, unmeasured remainder explicit. Latest metric observation supersedes earlier observations without deleting them; no causal, fairness, sentencing or effectiveness inference. No legal deadline calculation, predictive model, live dispatch or automated justice. Review records are human-authored role notes, not autonomous agents or authenticated approval.')
