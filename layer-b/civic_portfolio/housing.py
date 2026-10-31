"""Fictional referral, consent, service continuity and challenge-route records."""
from .maintenance import fields,identifier
from .permits import statistic,timestamp
from .store import Conflict,now,text

STAGES={'INTAKE':{'REFERRED','CLOSED_NO_SERVICE'},'REFERRED':{'HANDOFF_ACCEPTED','RETURNED','CLOSED_NO_SERVICE'},
        'HANDOFF_ACCEPTED':{'SERVICE_STARTED','RETURNED','CLOSED_NO_SERVICE'},
        'RETURNED':{'REFERRED','CLOSED_NO_SERVICE'},
        'SERVICE_STARTED':{'FOLLOW_UP','SERVICE_INTERRUPTED','CLOSED_WITH_SERVICE'},
        'FOLLOW_UP':{'FOLLOW_UP','SERVICE_INTERRUPTED','CLOSED_WITH_SERVICE'},
        'SERVICE_INTERRUPTED':{'REFERRED','CLOSED_NO_SERVICE'},
        'CLOSED_NO_SERVICE':set(),'CLOSED_WITH_SERVICE':set()}
CONSENT_ACTIONS={'REFERRED','HANDOFF_ACCEPTED','SERVICE_STARTED','FOLLOW_UP'}


class Housing:
    def __init__(self,store):self.store=store

    def case(self,case_id,db=None):
        if db is None:
            with self.store.connect() as connection:return self.case(case_id,connection)
        row=db.execute('SELECT * FROM housing_cases WHERE id=?',(case_id,)).fetchone()
        if not row:raise KeyError('synthetic housing case not found')
        events=[dict(r) for r in db.execute('SELECT * FROM housing_events WHERE case_id=? ORDER BY sequence',(case_id,))]
        consents=[dict(r) for r in db.execute('SELECT * FROM housing_consents WHERE case_id=? ORDER BY sequence',(case_id,))]
        checks=[dict(r) for r in db.execute('SELECT * FROM housing_checks WHERE case_id=? ORDER BY sequence',(case_id,))]
        return {**dict(row),'events':events,'consents':consents,'checks':checks,'stage':events[-1]['stage'],
                'consent_status':consents[-1]['status'],'allowed_next_stages':sorted(STAGES[events[-1]['stage']]),
                'kind':'SYNTHETIC','execution_authorized':False}

    def cases(self):
        with self.store.connect() as db:return [self.case(r['id'],db) for r in db.execute('SELECT id FROM housing_cases ORDER BY id')]

    def create_case(self,data):
        fields(data,'case_id program area at actor evidence notice_reference')
        case_id=identifier(data['case_id']);program=text(data['program'],'fictional program',100)
        area=text(data['area'],'fictional area',100);actor=text(data['actor'],'actor',200)
        evidence=text(data['evidence'],'intake evidence');at=timestamp(data['at']).isoformat()
        notice=data['notice_reference']
        if notice is not None:notice=text(notice,'fictional external notice reference',2000)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT id FROM housing_cases WHERE id=?',(case_id,)).fetchone():raise Conflict('synthetic housing case already exists')
            db.execute('INSERT INTO housing_cases VALUES (?,?,?,?,1)',(case_id,program,area,notice))
            db.execute('INSERT INTO housing_events VALUES (?,1,?,?,?,?,NULL,NULL)',(case_id,'INTAKE',at,actor,evidence))
            db.execute('INSERT INTO housing_consents VALUES (?,1,?,?,?,?)',(case_id,'NOT_RECORDED',at,actor,'No consent assertion recorded at intake'))
            self.store.log(db,actor,'create_synthetic_housing_case',case_id,data)
            return self.case(case_id,db)

    def consent(self,case_id,data):
        fields(data,'version status at actor evidence')
        if type(data['version']) is not int:raise ValueError('integer version required')
        status=text(data['status'],'consent assertion',100)
        if status not in {'RECORDED','NOT_RECORDED','WITHDRAWN'}:raise ValueError('invalid consent assertion')
        actor,evidence=text(data['actor'],'actor',200),text(data['evidence'],'consent assertion evidence');at=timestamp(data['at'])
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');case=self.case(case_id,db)
            self._version(case,data)
            self._chronology(case,at)
            db.execute('INSERT INTO housing_consents VALUES (?,?,?,?,?,?)',(case_id,len(case['consents'])+1,status,at.isoformat(),actor,evidence))
            db.execute('UPDATE housing_cases SET version=version+1 WHERE id=?',(case_id,))
            self.store.log(db,actor,'record_synthetic_consent_assertion',case_id,data)
            return self.case(case_id,db)

    @staticmethod
    def _version(case,data):
        if case['version']!=data['version']:raise Conflict('Case changed. Reload before saving.')

    @staticmethod
    def _chronology(case,at):
        if at<timestamp(case['events'][-1]['at']) or at<timestamp(case['consents'][-1]['at']) or (case['checks'] and at<timestamp(case['checks'][-1]['at'])):
            raise ValueError('record precedes latest case event, consent assertion or check')

    def advance(self,case_id,data):
        fields(data,'version stage at actor evidence continuity follow_up_due_at')
        if type(data['version']) is not int:raise ValueError('integer version required')
        stage=text(data['stage'],'stage',100);actor=text(data['actor'],'actor',200)
        evidence=text(data['evidence'],'stage evidence');at=timestamp(data['at'])
        continuity=data['continuity'];due=data['follow_up_due_at']
        if stage=='FOLLOW_UP':
            if not isinstance(continuity,str) or continuity not in {'CONTINUING','UNKNOWN'}:raise ValueError('follow-up requires CONTINUING or UNKNOWN continuity assertion')
        elif continuity is not None:raise ValueError('continuity assertion belongs only to FOLLOW_UP')
        if due is not None:
            if stage not in {'SERVICE_STARTED','FOLLOW_UP'}:raise ValueError('follow-up due time belongs only to service start or follow-up')
            due=timestamp(due)
            if due<at:raise ValueError('follow-up due time precedes the current event')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');case=self.case(case_id,db);self._version(case,data);self._chronology(case,at)
            if stage not in STAGES[case['stage']]:raise ValueError('invalid synthetic housing transition')
            if stage in CONSENT_ACTIONS and case['consent_status']!='RECORDED':raise ValueError('recorded current consent assertion required for this synthetic action')
            if stage=='CLOSED_WITH_SERVICE':
                starts=[e for e in case['events'] if e['stage']=='SERVICE_STARTED']
                checks=[c for c in case['checks'] if starts and c['event_sequence']==starts[-1]['sequence']]
                if not checks or not checks[-1]['passed']:raise ValueError('closure with service requires a passing check for the current service start')
            db.execute('INSERT INTO housing_events VALUES (?,?,?,?,?,?,?,?)',(case_id,len(case['events'])+1,stage,at.isoformat(),actor,evidence,continuity,due.isoformat() if due else None))
            db.execute('UPDATE housing_cases SET version=version+1 WHERE id=?',(case_id,))
            self.store.log(db,actor,'advance_synthetic_housing_case',case_id,data)
            return self.case(case_id,db)

    def verify(self,case_id,data):
        fields(data,'version at verifier passed evidence')
        if type(data['version']) is not int or type(data['passed']) is not bool:raise ValueError('integer version and boolean passed required')
        actor,evidence=text(data['verifier'],'verifier',200),text(data['evidence'],'service/follow-up verification evidence');at=timestamp(data['at'])
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');case=self.case(case_id,db);self._version(case,data);self._chronology(case,at)
            last=case['events'][-1]
            if last['stage'] not in {'SERVICE_STARTED','FOLLOW_UP'}:raise ValueError('verification requires the current service-start or follow-up event')
            if actor==last['actor']:raise ValueError('use a distinct verifier identifier from the event recorder')
            db.execute('INSERT INTO housing_checks VALUES (?,?,?,?,?,?,?)',(case_id,len(case['checks'])+1,last['sequence'],at.isoformat(),actor,int(data['passed']),evidence))
            db.execute('UPDATE housing_cases SET version=version+1 WHERE id=?',(case_id,))
            self.store.log(db,actor,'verify_synthetic_housing_event',case_id,data)
            return self.case(case_id,db)

    def request(self,request_id,db=None):
        if db is None:
            with self.store.connect() as connection:return self.request(request_id,connection)
        row=db.execute('SELECT * FROM housing_requests WHERE id=?',(request_id,)).fetchone()
        if not row:raise KeyError('synthetic review request not found')
        events=[dict(r) for r in db.execute('SELECT * FROM housing_request_events WHERE request_id=? ORDER BY sequence',(request_id,))]
        return {**dict(row),'events':events,'status':events[-1]['status'],'kind':'SYNTHETIC'}

    def requests(self):
        with self.store.connect() as db:return [self.request(r['id'],db) for r in db.execute('SELECT id FROM housing_requests ORDER BY id')]

    def create_request(self,data):
        fields(data,'request_id case_id description at actor evidence')
        request_id,case_id=identifier(data['request_id']),identifier(data['case_id'])
        description=text(data['description'],'fictional non-identifying review request');actor=text(data['actor'],'actor',200)
        evidence=text(data['evidence'],'request evidence');at=timestamp(data['at'])
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');case=self.case(case_id,db)
            if at<timestamp(case['events'][0]['at']):raise ValueError('review request precedes case intake')
            if db.execute('SELECT id FROM housing_requests WHERE id=?',(request_id,)).fetchone():raise Conflict('synthetic review request already exists')
            db.execute('INSERT INTO housing_requests VALUES (?,?,?,1)',(request_id,case_id,description))
            db.execute('INSERT INTO housing_request_events VALUES (?,1,?,?,?,?)',(request_id,'OPEN',at.isoformat(),actor,evidence))
            self.store.log(db,actor,'create_synthetic_housing_review_request',request_id,data)
            return self.request(request_id,db)

    def respond(self,request_id,data):
        fields(data,'version status at actor evidence')
        if type(data['version']) is not int:raise ValueError('integer version required')
        status=text(data['status'],'request status',100);actor=text(data['actor'],'actor',200)
        evidence=text(data['evidence'],'review response evidence');at=timestamp(data['at'])
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');request=self.request(request_id,db)
            if request['version']!=data['version']:raise Conflict('Request changed. Reload before saving.')
            if status!=('RESPONDED' if request['status']=='OPEN' else 'OPEN'):raise ValueError('review request must alternate OPEN and RESPONDED')
            if at<timestamp(request['events'][-1]['at']):raise ValueError('response precedes previous review-request event')
            db.execute('INSERT INTO housing_request_events VALUES (?,?,?,?,?,?)',(request_id,len(request['events'])+1,status,at.isoformat(),actor,evidence))
            db.execute('UPDATE housing_requests SET version=version+1 WHERE id=?',(request_id,))
            self.store.log(db,actor,'respond_to_synthetic_housing_review_request',request_id,data)
            return self.request(request_id,db)

    def report(self,as_of=None,program=None,area=None):
        at=timestamp(as_of or now());included=set();times=[];ages=[]
        totals=dict(cases=0,referred_cases=0,verified_service_start_cases=0,unverified_service_start_cases=0,
                    returned_referral_events=0,closed_without_service_cases=0,consent_hold_cases=0,
                    service_interruption_events=0,current_interruption_cases=0,verified_continuing_followups=0,
                    verified_unknown_followups=0,unverified_followups=0,service_cases_without_followup=0,
                    overdue_followups=0,missing_followup_plans=0)
        for case in self.cases():
            if (program and case['program']!=program) or (area and case['area']!=area):continue
            events=[e for e in case['events'] if timestamp(e['at'])<=at]
            if not events:continue
            included.add(case['id']);totals['cases']+=1;last=events[-1]
            consents=[c for c in case['consents'] if timestamp(c['at'])<=at]
            if consents[-1]['status']!='RECORDED':totals['consent_hold_cases']+=1
            checks=[c for c in case['checks'] if timestamp(c['at'])<=at]
            def verified(event):
                matching=[c for c in checks if c['event_sequence']==event['sequence']]
                return bool(matching and matching[-1]['passed'])
            referrals=[e for e in events if e['stage']=='REFERRED']
            starts=[e for e in events if e['stage']=='SERVICE_STARTED']
            accepted=[e for e in starts if verified(e)]
            totals['returned_referral_events']+=sum(e['stage']=='RETURNED' for e in events)
            totals['service_interruption_events']+=sum(e['stage']=='SERVICE_INTERRUPTED' for e in events)
            if last['stage']=='CLOSED_NO_SERVICE':totals['closed_without_service_cases']+=1
            if referrals:
                totals['referred_cases']+=1
                if accepted:
                    totals['verified_service_start_cases']+=1
                    times.append((timestamp(accepted[0]['at'])-timestamp(referrals[0]['at'])).total_seconds()/3600)
                elif last['stage'] not in {'CLOSED_NO_SERVICE','CLOSED_WITH_SERVICE'}:
                    ages.append((at-timestamp(referrals[0]['at'])).total_seconds()/3600)
            if starts and not accepted:totals['unverified_service_start_cases']+=1
            service_events=[e for e in events if e['stage'] in {'SERVICE_STARTED','SERVICE_INTERRUPTED'}]
            interrupted=bool(service_events and service_events[-1]['stage']=='SERVICE_INTERRUPTED')
            if interrupted:totals['current_interruption_cases']+=1
            if starts and not interrupted:
                followups=[e for e in events if e['stage']=='FOLLOW_UP' and e['sequence']>starts[-1]['sequence']]
                if not followups:totals['service_cases_without_followup']+=1
                elif not verified(followups[-1]):totals['unverified_followups']+=1
                elif followups[-1]['continuity']=='CONTINUING':totals['verified_continuing_followups']+=1
                else:totals['verified_unknown_followups']+=1
            if last['stage'] in {'SERVICE_STARTED','FOLLOW_UP'}:
                if last['follow_up_due_at'] is None:totals['missing_followup_plans']+=1
                elif timestamp(last['follow_up_due_at'])<at:totals['overdue_followups']+=1
        request_ages=[];response_times=[];reopened=0
        for request in self.requests():
            if request['case_id'] not in included:continue
            events=[e for e in request['events'] if timestamp(e['at'])<=at]
            if not events:continue
            reopened+=sum(e['status']=='OPEN' for e in events[1:]);start=timestamp(events[0]['at']);last=events[-1]
            if last['status']=='OPEN':request_ages.append((at-start).total_seconds()/3600)
            else:response_times.append((timestamp(last['at'])-start).total_seconds()/3600)
        return {'kind':'SYNTHETIC','as_of':at.isoformat(),'program':program,'area':area,**totals,
                'referral_to_service_hours':statistic(times),'unverified_referral_age_hours':statistic(ages),
                'open_review_requests':len(request_ages),'reopened_review_requests':reopened,
                'review_response_hours':statistic(response_times),'open_review_age_hours':statistic(request_ages),
                'execution_authorized':False,
                'method':'UTC calendar hours from first referral to first service-start event with a passing event-specific check visible at cutoff; repeat referrals do not reset the clock. Open unverified referrals are censored; cases closed without service are separate. Starting service does not establish continuing service: current-cycle follow-up, unknown continuity, interruptions and overdue/missing plans stay explicit. Consent and verifier records are local assertions, not actual consent, benefit eligibility or legal approval. Review-request responses are recorded communications, not adjudication or satisfaction findings. No real referrals, placements or outreach occur.'}
