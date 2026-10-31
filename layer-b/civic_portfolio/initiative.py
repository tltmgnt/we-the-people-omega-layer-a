"""Connected 50-workstream governance and fictional collaboration rehearsal."""
import hashlib
import json
from .maintenance import fields,identifier
from .permits import timestamp
from .store import Conflict,text,ROOT

METHODS={'041':'Constitutional and civic foundations','042':'Topological Gap Analysis Ω','043':'Civic systems intelligence and evidence','044':'DTI Ω temporal capacity','045':'HedgeOps Ω benchmarked analysis','046':'Institutional transition management','047':'Rights and human agency assurance','048':'Civic performance and validation','049':'Leadership and institutional adoption','050':'Integrated simulation and capstone'}
SAFEGUARDS=('AUTHORITY','RIGHTS_ACCESSIBILITY','PRIVACY_SECURITY','HUMAN_ACCOUNTABILITY','INDEPENDENT_CHALLENGE','TRANSPARENCY_CORRECTION','JURISDICTION_TRIBAL_SOVEREIGNTY','SERVICE_CONTINUITY')
STAGES=('PROPOSED','FRAMEWORK_REVIEW','PILOT_SELECTED','BASELINE_RECORDED','CONTROLLED_TEST_RECORDED','INDEPENDENT_EVALUATION_RECORDED','REPORT_RECORDED')
LABS={'009':'/permits','010':'/maintenance','011':'/sanitation','012':'/transit','013':'/housing','014':'/public-access','015':'/utilities','016':'/rights','017':'/election-services','018':'/finance','019':'/scenarios?workflow=procurement','023':'/justice'}
SCHEMAS={'DEPENDENCY':'from_project to_project rationale active','PRIORITY':'project_id disposition owner rationale','SAFEGUARD':'safeguard status owner evidence','SAFEGUARD_CHECK':'assertion_sequence passed evidence','STAGE':'stage owner evidence limitations','STAGE_CHECK':'stage_sequence passed evidence','REOPEN':'reason','CHALLENGE':'challenge_id question owner evidence','RESPONSE':'challenge_id response evidence'}


def digest(body):return hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()


class Initiative:
    def __init__(self,store):self.store=store

    def catalog(self):
        with self.store.connect() as db:
            projects=[self.store.project(r['id'],db) for r in db.execute('SELECT id FROM projects ORDER BY id')]
        return [dict(project_id=p['project_id'],title=p['title'],group='SHARED_METHODS' if int(p['project_id'])>=41 else 'GOVERNANCE_SERVICES',owner=p['owner'],scope=p['scope'],status=p['status'],source=p['source'],blockers=p['blockers'],prototype_path=LABS.get(p['project_id']),institutional_acceptance='NOT_ESTABLISHED',execution_authorized=False) for p in projects]

    def program(self,key,db=None):
        if db is None:
            with self.store.connect() as c:return self.program(key,c)
        row=db.execute('SELECT * FROM initiative_programs WHERE id=?',(key,)).fetchone()
        if not row:raise KeyError('synthetic collaboration not found')
        return {**json.loads(row['body']),'version':row['version'],'events':[json.loads(r['body']) for r in db.execute('SELECT body FROM initiative_events WHERE program_id=? ORDER BY sequence',(key,))]}

    def programs(self):
        with self.store.connect() as db:return [self.program(r['id'],db) for r in db.execute('SELECT id FROM initiative_programs ORDER BY id')]

    def create(self,data):
        fields(data,'program_id label project_ids source_ids office_review_question baseline_plan success_criteria resources continuity_plan rollback_plan owner at actor')
        body={k:text(v,k,10000) for k,v in data.items() if k not in {'program_id','project_ids','source_ids','at'}}
        body['program_id']=identifier(data['program_id']);body['at']=timestamp(data['at']).isoformat()
        projects=data['project_ids'];sources=data['source_ids']
        if not isinstance(projects,list) or not 1<=len(projects)<=50 or any(not isinstance(p,str) or p not in {f'{i:03}' for i in range(1,51)} for p in projects) or len(set(projects))!=len(projects):raise ValueError('select distinct registered project IDs')
        if not isinstance(sources,list) or len(sources)>61 or any(not isinstance(s,str) for s in sources) or len(set(sources))!=len(sources):raise ValueError('source IDs must be a distinct bounded list')
        body['project_ids']=sorted(projects);body['source_ids']=sorted(sources)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT id FROM initiative_programs WHERE id=?',(body['program_id'],)).fetchone():raise Conflict('program exists')
            allowed={s['id'] for s in self.store.sources(db)}
            if set(sources)-allowed:raise ValueError('unknown shared source ID')
            db.execute('INSERT INTO initiative_programs VALUES (?,?,1)',(body['program_id'],json.dumps(body)));self.store.log(db,body['actor'],'create_synthetic_collaboration',body['program_id'],body)
            return self.program(body['program_id'],db)

    @staticmethod
    def edges(events):
        latest={}
        for e in events:
            if e['kind']=='DEPENDENCY':latest[(e['data']['from_project'],e['data']['to_project'])]=e
        return [e for e in latest.values() if e['data']['active']]

    def context(self,program,db):
        projects=set(program['project_ids']);edges=self.edges(program['events'])
        while True:
            expanded=projects|{e['data']['from_project'] for e in edges if e['data']['to_project'] in projects}
            if expanded==projects:break
            projects=expanded
        records=[self.store.project(p,db) for p in sorted(projects)]
        sources={s['id']:s for s in self.store.sources(db)}
        source_ids=set(program['source_ids'])|{'project-'+p for p in projects}
        if 'initiative-overview' in sources:source_ids.add('initiative-overview')
        # Signatures include review changes, not just content, so withdrawing/replacing review is visible.
        source_pins=[{k:sources[s][k] for k in ('id','revision','sha256','reviewer','reviewed_at')} for s in sorted(source_ids)]
        return dict(projects=[dict(project_id=p['project_id'],version=p['version']) for p in records],sources=source_pins,dependencies=[e['sequence'] for e in edges],overview_sha256=hashlib.sha256((ROOT/'portfolio/sources/initiative-user-specification.md').read_bytes()).hexdigest())

    @staticmethod
    def stages(events):return [e for e in events if e['kind'] in {'STAGE','REOPEN'}]

    @staticmethod
    def current_stage(events):
        stages=Initiative.stages(events)
        return ('PROPOSED',None) if not stages or stages[-1]['kind']=='REOPEN' else (stages[-1]['data']['stage'],stages[-1])

    def blockers(self,program,context,db):
        blockers=[]
        for pin in context['projects']:
            p=self.store.project(pin['project_id'],db)
            for name,ok in [('title',p['title']),('owner',p['owner']),('confirmed scope',p['scope_confirmed'] and p['scope'])]:
                if not ok:blockers.append(p['project_id']+': missing '+name)
        for pin in context['sources']:
            if pin['revision'] is None:blockers.append(pin['id']+': source text missing')
            elif not pin['reviewer']:blockers.append(pin['id']+': current source not reviewed')
        latest={e['data']['safeguard']:e for e in program['events'] if e['kind']=='SAFEGUARD'}
        signature=digest(context)
        for safeguard in SAFEGUARDS:
            item=latest.get(safeguard)
            checks=[e for e in program['events'] if e['kind']=='SAFEGUARD_CHECK' and item and e['data']['assertion_sequence']==item['sequence']]
            if not item or item['data']['status']!='MET' or item['context_sha256']!=signature or not checks or not checks[-1]['data']['passed'] or checks[-1]['context_sha256']!=signature:blockers.append(safeguard+': current MET assertion and separate passing check required')
        challenges={e['data']['challenge_id']:e for e in program['events'] if e['kind']=='CHALLENGE'}
        responded={e['data']['challenge_id'] for e in program['events'] if e['kind']=='RESPONSE'}
        for key in challenges.keys()-responded:blockers.append(key+': challenge needs a documented response (response is not proof of remedy)')
        return blockers

    def record(self,key,data):
        fields(data,'version kind at actor data');kind=text(data['kind'],'kind',100)
        if kind not in SCHEMAS:raise ValueError('invalid governance record kind')
        fields(data['data'],SCHEMAS[kind]);payload=dict(data['data']);actor=text(data['actor'],'actor',200);at=timestamp(data['at']).isoformat()
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');program=self.program(key,db);events=program['events']
            if type(data['version']) is not int:raise ValueError('integer version required')
            if data['version']!=program['version']:raise Conflict('Collaboration changed. Reload before saving.')
            if timestamp(at)<timestamp(events[-1]['at'] if events else program['at']):raise ValueError('record precedes latest collaboration activity')
            for name,value in payload.items():
                if name not in {'active','passed','assertion_sequence','stage_sequence'}:payload[name]=text(value,name)
            context=self.context(program,db);signature=digest(context)
            if kind=='DEPENDENCY':
                for name in ('from_project','to_project'):
                    if payload[name] not in {f'{i:03}' for i in range(1,51)}:raise ValueError('unknown project')
                if type(payload['active']) is not bool:raise ValueError('active must be boolean')
                proposed=events+[dict(sequence=len(events)+1,kind=kind,data=payload)];edges=self.edges(proposed);graph={}
                for e in edges:graph.setdefault(e['data']['from_project'],[]).append(e['data']['to_project'])
                visited=set();visiting=set()
                def visit(node):
                    if node in visiting:raise ValueError('dependency cycle is not permitted')
                    if node in visited:return
                    visiting.add(node)
                    for target in graph.get(node,[]):visit(target)
                    visiting.remove(node);visited.add(node)
                for node in graph:visit(node)
                # Recompute using proposed dependencies so new scope is reflected immediately.
                context=self.context({**program,'events':proposed},db);signature=digest(context)
            elif kind=='PRIORITY':
                if payload['project_id'] not in {f'{i:03}' for i in range(1,51)} or payload['disposition'] not in {'CANDIDATE','DEFERRED','REQUIRES_DEFINITION'}:raise ValueError('invalid project/disposition')
            elif kind=='SAFEGUARD':
                if payload['safeguard'] not in SAFEGUARDS or payload['status'] not in {'UNKNOWN','GAP','MET'}:raise ValueError('invalid safeguard/status')
            elif kind in {'SAFEGUARD_CHECK','STAGE_CHECK'}:
                field='assertion_sequence' if kind=='SAFEGUARD_CHECK' else 'stage_sequence';seq=payload[field]
                if type(seq) is not int or type(payload['passed']) is not bool:raise ValueError('integer sequence and boolean passed required')
                item=next((e for e in events if e['sequence']==seq and e['kind']==('SAFEGUARD' if kind=='SAFEGUARD_CHECK' else 'STAGE')),None)
                if not item:raise ValueError('referenced assertion/stage not found')
                if item['actor']==actor:raise ValueError('use a distinct checker from the recorder')
                if item['context_sha256']!=signature:raise Conflict('referenced evidence context is stale')
                if kind=='SAFEGUARD_CHECK':
                    latest=[e for e in events if e['kind']=='SAFEGUARD' and e['data']['safeguard']==item['data']['safeguard']][-1]
                    if latest['sequence']!=seq:raise Conflict('safeguard assertion was superseded')
                else:
                    stage,current=self.current_stage(events)
                    if not current or current['sequence']!=seq:raise Conflict('stage was superseded or reopened')
            elif kind=='STAGE':
                stage,current=self.current_stage(events);index=STAGES.index(stage)
                if index==len(STAGES)-1 or payload['stage']!=STAGES[index+1]:raise ValueError('record the next collaboration stage in order')
                if current:
                    checks=[e for e in events if e['kind']=='STAGE_CHECK' and e['data']['stage_sequence']==current['sequence']]
                    if current['context_sha256']!=signature or not checks or not checks[-1]['data']['passed'] or checks[-1]['context_sha256']!=signature:raise ValueError('prior stage requires a separate passing check for current context; reopen stale work')
                if payload['stage']!='FRAMEWORK_REVIEW':
                    blockers=self.blockers(program,context,db)
                    if blockers:raise ValueError('Scenario gate blocked: '+'; '.join(blockers))
            elif kind=='CHALLENGE':
                payload['challenge_id']=identifier(payload['challenge_id'])
                if any(e['kind']=='CHALLENGE' and e['data']['challenge_id']==payload['challenge_id'] for e in events):raise Conflict('challenge ID exists')
            elif kind=='RESPONSE':
                payload['challenge_id']=identifier(payload['challenge_id'])
                if not any(e['kind']=='CHALLENGE' and e['data']['challenge_id']==payload['challenge_id'] for e in events):raise ValueError('challenge not found')
            event=dict(sequence=len(events)+1,kind=kind,at=at,actor=actor,data=payload,context=context,context_sha256=signature)
            db.execute('INSERT INTO initiative_events VALUES (?,?,?)',(key,event['sequence'],json.dumps(event)));db.execute('UPDATE initiative_programs SET version=version+1 WHERE id=?',(key,))
            self.store.log(db,actor,'synthetic_initiative_'+kind.lower(),key,event)
            return self.program(key,db)

    def report(self,key):
        with self.store.connect() as db:
            program=self.program(key,db);context=self.context(program,db);signature=digest(context);stage,current=self.current_stage(program['events']);checks=[e for e in program['events'] if e['kind']=='STAGE_CHECK' and current and e['data']['stage_sequence']==current['sequence']]
            return dict(program_id=key,kind='SYNTHETIC',stage=stage,stage_sequence=current['sequence'] if current else None,stage_checked=bool(checks and checks[-1]['data']['passed'] and checks[-1]['context_sha256']==signature),context=context,context_sha256=signature,dependencies=[e['data'] for e in self.edges(program['events'])],blockers=self.blockers(program,context,db),stale_record_sequences=[e['sequence'] for e in program['events'] if e['context_sha256']!=signature],events=program['events'],execution_authorized=False,institutional_endorsement=False,legal_review='REQUIRED',live_collaboration='NOT_ESTABLISHED',domain_implementations_complete=False,method='Local fictional rehearsal. Dependency edges are explicitly declared prerequisites, not inferred legal authority. Project/source versions and review metadata pin every event; changing dependencies, definitions or source review makes old context stale. Stage evidence and separate checks are assertions by unauthenticated identifiers. Checks never authorize live intervention, sending proposals, procurement, partnership, data access or public reporting. An answered challenge is not a resolved rights issue. No office recommendation or institutional endorsement is inferred. This tool does not constitute 50 completed domain services.')
