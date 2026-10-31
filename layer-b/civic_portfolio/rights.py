"""Synthetic review-question evidence; Layer A exports are always blocked drafts."""
from datetime import date
import hashlib
import json

from .maintenance import fields,identifier
from .permits import statistic,timestamp
from .store import Conflict,MAX_TEXT,now,text

DOMAINS=tuple(f'A{i}' for i in range(1,8))


def domain(value):
    value=text(value,'screening domain',100)
    if value not in DOMAINS:raise ValueError('domain must be A1 through A7')
    return value


class Rights:
    def __init__(self,store):self.store=store

    def case(self,case_id,db=None):
        if db is None:
            with self.store.connect() as connection:return self.case(case_id,connection)
        row=db.execute('SELECT * FROM rights_cases WHERE id=?',(case_id,)).fetchone()
        if not row:raise KeyError('synthetic rights-review case not found')
        result=dict(row)
        result['screenings']=[{**dict(r),'evidence_pins':json.loads(r['evidence_pins'])} for r in db.execute('SELECT * FROM rights_screenings WHERE case_id=? ORDER BY sequence',(case_id,))]
        result['evidence']=[dict(r) for r in db.execute('SELECT * FROM rights_evidence WHERE case_id=? ORDER BY evidence_id,revision',(case_id,))]
        result['candidate_authorities']=[{**dict(r),'applicability':'UNASSESSED'} for r in db.execute('SELECT * FROM rights_authorities WHERE case_id=? ORDER BY authority_id',(case_id,))]
        result['questions']=[]
        for row in db.execute('SELECT * FROM rights_questions WHERE case_id=? ORDER BY id',(case_id,)):
            events=[{**dict(e),'evidence_pins':json.loads(e['evidence_pins'])} for e in db.execute('SELECT * FROM rights_question_events WHERE question_id=? ORDER BY sequence',(row['id'],))]
            result['questions'].append({**dict(row),'events':events})
        result.update(kind='SYNTHETIC',review_status='LEGAL_REVIEW_REQUIRED',execution_authorized=False)
        return result

    def cases(self):
        with self.store.connect() as db:return [self.case(r['id'],db) for r in db.execute('SELECT id FROM rights_cases ORDER BY id')]

    @staticmethod
    def _check(case,data):
        if type(data['version']) is not int:raise ValueError('integer case version required')
        if data['version']!=case['version']:raise Conflict('Review case changed. Reload before saving.')
        at=timestamp(data['at'])
        if at<timestamp(case['last_at']):raise ValueError('record precedes latest case activity')
        return at.isoformat()

    def _finish(self,db,case_id,actor,action,data,at):
        db.execute('UPDATE rights_cases SET version=version+1,last_at=? WHERE id=?',(at,case_id))
        self.store.log(db,actor,action,case_id,{k:v for k,v in data.items() if k!='content'})
        return self.case(case_id,db)

    @staticmethod
    def _pins(case,pins):
        if not isinstance(pins,list):raise ValueError('evidence pins must be a list')
        seen=set()
        for pin in pins:
            if not isinstance(pin,dict) or set(pin)!={'evidence_id','revision','sha256'}:raise ValueError('each evidence pin requires evidence_id, revision and sha256')
            if not isinstance(pin['evidence_id'],str) or type(pin['revision']) is not int or not isinstance(pin['sha256'],str):raise ValueError('invalid evidence pin types')
            key=(pin['evidence_id'],pin['revision'])
            if key in seen:raise ValueError('duplicate evidence pin')
            seen.add(key)
            match=next((e for e in case['evidence'] if (e['evidence_id'],e['revision'])==key),None)
            if not match or match['sha256']!=pin['sha256'] or hashlib.sha256(match['content'].encode()).hexdigest()!=pin['sha256']:raise ValueError('evidence pin does not resolve to matching snapshot content')
        return pins

    def create_case(self,data):
        fields(data,'case_id proposal_id summary institution jurisdiction at actor')
        case_id,proposal=identifier(data['case_id']),identifier(data['proposal_id'])
        summary=text(data['summary'],'fictional proposal summary');institution=text(data['institution'],'fictional institution',200)
        jurisdiction=text(data['jurisdiction'],'fictional jurisdiction label',200);actor=text(data['actor'],'actor',200);at=timestamp(data['at']).isoformat()
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT id FROM rights_cases WHERE id=?',(case_id,)).fetchone():raise Conflict('synthetic review case already exists')
            db.execute('INSERT INTO rights_cases VALUES (?,?,?,?,?,?,?,?,1)',(case_id,proposal,summary,institution,jurisdiction,at,at,actor))
            for index,name in enumerate(DOMAINS,1):
                db.execute('INSERT INTO rights_screenings VALUES (?,?,?,?,?,?,?,?)',(case_id,index,name,'UNASSESSED',None,'[]',at,actor))
            self.store.log(db,actor,'create_synthetic_rights_review',case_id,data)
            return self.case(case_id,db)

    def add_evidence(self,case_id,data):
        fields(data,'version evidence_id content origin at actor');evidence_id=identifier(data['evidence_id'])
        text(data['content'],'full fictional evidence text',MAX_TEXT);content=data['content']
        origin=text(data['origin'],'snapshot origin',2000);actor=text(data['actor'],'actor',200)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');case=self.case(case_id,db);at=self._check(case,data)
            revision=max([e['revision'] for e in case['evidence'] if e['evidence_id']==evidence_id],default=0)+1
            digest=hashlib.sha256(content.encode()).hexdigest()
            db.execute('INSERT INTO rights_evidence VALUES (?,?,?,?,?,?,?,?)',(case_id,evidence_id,revision,digest,content,origin,at,actor))
            return self._finish(db,case_id,actor,'snapshot_synthetic_rights_evidence',data,at)

    def screen(self,case_id,data):
        fields(data,'version domain relevance rationale evidence_pins at actor');name=domain(data['domain'])
        relevance=text(data['relevance'],'screening relevance',100)
        if relevance not in {'UNASSESSED','RELEVANT','NOT_RELEVANT'}:raise ValueError('invalid relevance assertion')
        rationale=text(data['rationale'],'screening rationale');actor=text(data['actor'],'actor',200)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');case=self.case(case_id,db);at=self._check(case,data);pins=self._pins(case,data['evidence_pins'])
            db.execute('INSERT INTO rights_screenings VALUES (?,?,?,?,?,?,?,?)',(case_id,len(case['screenings'])+1,name,relevance,rationale,json.dumps(pins),at,actor))
            return self._finish(db,case_id,actor,'record_synthetic_domain_screening',data,at)

    def add_authority(self,case_id,data):
        fields(data,'version authority_id reference proposed_scope source_date at actor');authority_id=identifier(data['authority_id'])
        reference=text(data['reference'],'candidate reference',2000);scope=text(data['proposed_scope'],'unassessed scope explanation')
        source_date=data['source_date']
        if source_date is not None:
            source_date=text(source_date,'source date',10)
            if date.fromisoformat(source_date).isoformat()!=source_date:raise ValueError('source date must be YYYY-MM-DD or unknown')
        actor=text(data['actor'],'actor',200)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');case=self.case(case_id,db);at=self._check(case,data)
            if any(a['authority_id']==authority_id for a in case['candidate_authorities']):raise Conflict('candidate reference ID already exists; use a new ID for a revised candidate')
            db.execute('INSERT INTO rights_authorities VALUES (?,?,?,?,?,?,?)',(case_id,authority_id,reference,scope,source_date,at,actor))
            return self._finish(db,case_id,actor,'record_unassessed_authority_candidate',data,at)

    def add_question(self,case_id,data):
        fields(data,'version question_id domain question alternative_explanation limitations evidence_pins at actor')
        question_id=identifier(data['question_id']);name=domain(data['domain'])
        question=text(data['question'],'fictional review question');alternative=text(data['alternative_explanation'],'alternative explanation')
        limitations=text(data['limitations'],'scope and evidence limitations');actor=text(data['actor'],'actor',200)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');case=self.case(case_id,db);at=self._check(case,data);pins=self._pins(case,data['evidence_pins'])
            if db.execute('SELECT id FROM rights_questions WHERE id=?',(question_id,)).fetchone():raise Conflict('review-question ID already exists')
            db.execute('INSERT INTO rights_questions VALUES (?,?,?,?,?,?,?,?)',(question_id,case_id,name,question,alternative,limitations,at,actor))
            db.execute('INSERT INTO rights_question_events VALUES (?,1,?,?,?,?,?)',(question_id,'OPEN',json.dumps(pins),at,actor,'New fictional review question; no legal finding'))
            return self._finish(db,case_id,actor,'open_synthetic_rights_question',data,at)

    def respond(self,case_id,question_id,data):
        fields(data,'version status evidence_pins at actor evidence');status=text(data['status'],'question status',100)
        if status not in {'OPEN','RESPONSE_RECORDED'}:raise ValueError('only OPEN and RESPONSE_RECORDED are supported; no legal decision status exists')
        actor,evidence=text(data['actor'],'actor',200),text(data['evidence'],'local response or challenge evidence')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');case=self.case(case_id,db);at=self._check(case,data);pins=self._pins(case,data['evidence_pins'])
            question=next((q for q in case['questions'] if q['id']==question_id),None)
            if not question:raise KeyError('review question not found in this case')
            if status=='RESPONSE_RECORDED' and not pins:raise ValueError('recorded response requires at least one pinned evidence snapshot')
            db.execute('INSERT INTO rights_question_events VALUES (?,?,?,?,?,?,?)',(question_id,len(question['events'])+1,status,json.dumps(pins),at,actor,evidence))
            return self._finish(db,case_id,actor,'record_synthetic_rights_response_or_challenge',data,at)

    @staticmethod
    def analyze(case,at):
        evidence=[e for e in case['evidence'] if timestamp(e['at'])<=at]
        latest={}
        for e in evidence:latest[e['evidence_id']]=max(latest.get(e['evidence_id'],0),e['revision'])
        def stale(pins):return any(latest.get(p['evidence_id'])!=p['revision'] for p in pins)
        screenings={}
        for s in case['screenings']:
            if timestamp(s['at'])<=at:screenings[s['domain']]={**s,'stale_evidence':stale(s['evidence_pins'])}
        questions=[]
        for q in case['questions']:
            events=[e for e in q['events'] if timestamp(e['at'])<=at]
            if events:questions.append({**q,'events':events,'status':events[-1]['status'],'stale_evidence':stale(events[-1]['evidence_pins'])})
        return {'evidence':evidence,'screenings':screenings,'questions':questions,
                'candidate_authorities':[a for a in case['candidate_authorities'] if timestamp(a['at'])<=at]}

    def report(self,as_of=None,jurisdiction=None):
        at=timestamp(as_of or now());t=dict(cases=0,screened_current_domains=0,unassessed_or_stale_domains=0,
                screenings_without_evidence=0,
                questions=0,open_or_stale_questions=0,current_evidence_responses=0,stale_evidence_questions=0,
                unpinned_questions=0,reopen_events=0,candidate_authorities=0,unknown_authority_dates=0,evidence_snapshots=0)
        ages=[];responses=[]
        for case in self.cases():
            if timestamp(case['created_at'])>at or (jurisdiction and case['jurisdiction']!=jurisdiction):continue
            t['cases']+=1;view=self.analyze(case,at)
            for s in view['screenings'].values():
                t['screened_current_domains' if s['relevance']!='UNASSESSED' and not s['stale_evidence'] else 'unassessed_or_stale_domains']+=1
                if s['relevance']!='UNASSESSED' and not s['evidence_pins']:t['screenings_without_evidence']+=1
            t['candidate_authorities']+=len(view['candidate_authorities']);t['unknown_authority_dates']+=sum(a['source_date'] is None for a in view['candidate_authorities'])
            t['evidence_snapshots']+=len(view['evidence'])
            for q in view['questions']:
                t['questions']+=1;last=q['events'][-1];t['stale_evidence_questions']+=q['stale_evidence']
                if not last['evidence_pins']:t['unpinned_questions']+=1
                t['reopen_events']+=sum(e['status']=='OPEN' and q['events'][i-1]['status']=='RESPONSE_RECORDED' for i,e in enumerate(q['events']) if i>0)
                if last['status']=='OPEN' or q['stale_evidence']:
                    t['open_or_stale_questions']+=1;ages.append((at-timestamp(q['at'])).total_seconds()/3600)
                else:
                    t['current_evidence_responses']+=1;responses.append((timestamp(last['at'])-timestamp(q['at'])).total_seconds()/3600)
        return {'kind':'SYNTHETIC','as_of':at.isoformat(),'jurisdiction':jurisdiction,**t,
                'unanswered_question_age_hours':statistic(ages),'local_response_hours':statistic(responses),
                'review_status':'LEGAL_REVIEW_REQUIRED','qualified_legal_reviews':0,'execution_authorized':False,
                'method':'Coverage describes recorded screening and pinned-evidence linkage, not legal sufficiency or truth. A newer snapshot revision makes older pins stale; historical cutoffs do not use future revisions. Local responses are not qualified legal review or resolved rights findings. Candidate authority applicability remains UNASSESSED. Draft Layer A exports always retain legal-review, jurisdiction and authorization holds, regardless of coverage.'}

    def bundle(self,case_id):
        case=self.case(case_id);view=self.analyze(case,timestamp(case['last_at']))
        questions=['Qualified, authorized human legal review has not occurred in this prototype.']
        questions += [f"{q['id']}: {q['question']} — local status {q['status']}; qualified assessment remains pending" for q in view['questions']]
        questions += [f"{name}: screening unassessed or stale; qualified applicability review pending" for name,s in view['screenings'].items() if s['relevance']=='UNASSESSED' or s['stale_evidence']]
        if view['candidate_authorities']:questions.append('All candidate authority references remain unassessed and are retained only in companion materials.')
        manifest=[{'evidence_id':f"{e['evidence_id']}@{e['revision']}",'sha256':e['sha256'],'origin':e['origin'],'content':e['content'],'at':e['at']} for e in case['evidence']]
        for e in manifest:
            if hashlib.sha256(e['content'].encode()).hexdigest()!=e['sha256']:raise ValueError('stored evidence content no longer matches its snapshot hash')
        record={'review_id':'SYN-LAYER-A-'+case_id,'schema_version':'0.1.0','proposal_id':case['proposal_id'],
                'proposal_summary':'[SYNTHETIC] '+case['summary'],'responsible_institution':'[SYNTHETIC] '+case['institution'],
                'jurisdictions':['[SYNTHETIC; applicability unassessed] '+case['jurisdiction']],
                'legal_authorities':[],'rights_affected':['Unassessed — local A1–A7 screening is not a qualified rights determination'],
                'procedural_requirements':['Qualified determination pending; no actual procedural requirements established'],
                'jurisdictional_limitations':['Jurisdiction, authority applicability and reviewer mandate remain unverified'],
                'accountability_mechanisms':['Fictional question/challenge history; actual institutional responsibilities unassigned'],
                'unresolved_questions':questions,'review_status':'LEGAL_REVIEW_REQUIRED',
                'reviewer_role':'UNASSIGNED — qualified legal review required',
                'conditions':['No execution authorization; qualified review and a separate institutional decision remain outstanding'],
                'evidence_ids':[e['evidence_id'] for e in manifest],'revision':case['version']}
        return {'record':record,'evidence_manifest':manifest,'candidate_authorities':case['candidate_authorities'],
                'case_history':case,'notice':'Synthetic intake draft only. References resolve to companion snapshots, not authoritative legal findings.'}
