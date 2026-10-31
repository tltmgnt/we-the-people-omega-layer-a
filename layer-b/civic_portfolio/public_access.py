"""Fictional records/complaint responses and meeting-notice evidence."""
import math

from .maintenance import fields,identifier
from .permits import statistic,timestamp
from .store import Conflict,now,text


def optional_text(value,name):
    return None if value is None else text(value,name,2000)


def version(record,data):
    if type(data['version']) is not int:raise ValueError('integer version required')
    if record['version']!=data['version']:raise Conflict('Record changed. Reload before saving.')


def ordered(at,groups):
    if any(group and at<timestamp(group[-1]['at']) for group in groups):
        raise ValueError('record precedes latest event, assertion or check')


def checked(checks,key,sequence):
    matching=[c for c in checks if c[key]==sequence]
    return bool(matching and matching[-1]['passed'])


class PublicAccess:
    def __init__(self,store):self.store=store

    def case(self,case_id,db=None):
        if db is None:
            with self.store.connect() as connection:return self.case(case_id,connection)
        row=db.execute('SELECT * FROM public_cases WHERE id=?',(case_id,)).fetchone()
        if not row:raise KeyError('synthetic records/complaint case not found')
        result=dict(row)
        for key,table in [('events','public_case_events'),('deadlines','public_deadlines'),('responses','public_responses'),('checks','public_response_checks')]:
            result[key]=[dict(r) for r in db.execute('SELECT * FROM '+table+' WHERE case_id=? ORDER BY sequence',(case_id,))]
        result['status']='CLOSED' if result['events'][-1]['action']=='CLOSED' else 'OPEN'
        result.update(synthetic=True,execution_authorized=False)
        return result

    def cases(self):
        with self.store.connect() as db:return [self.case(r['id'],db) for r in db.execute('SELECT id FROM public_cases ORDER BY id')]

    def create_case(self,data):
        fields(data,'case_id kind area at due_at actor evidence')
        case_id=identifier(data['case_id']);kind=text(data['kind'],'case kind',100)
        if kind not in {'RECORDS_REQUEST','COMPLAINT'}:raise ValueError('case kind must be RECORDS_REQUEST or COMPLAINT')
        area=text(data['area'],'fictional area',100);actor=text(data['actor'],'actor',200)
        evidence=text(data['evidence'],'receipt and recorded-deadline evidence');at=timestamp(data['at'])
        due=timestamp(data['due_at']) if data['due_at'] is not None else None
        if due and due<at:raise ValueError('recorded due time precedes receipt')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT id FROM public_cases WHERE id=?',(case_id,)).fetchone():raise Conflict('synthetic case already exists')
            db.execute('INSERT INTO public_cases VALUES (?,?,?,1,1)',(case_id,kind,area))
            db.execute('INSERT INTO public_case_events VALUES (?,1,?,1,?,?,?)',(case_id,'RECEIVED',at.isoformat(),actor,evidence))
            db.execute('INSERT INTO public_deadlines VALUES (?,1,?,?,?,?)',(case_id,at.isoformat(),due.isoformat() if due else None,actor,evidence))
            self.store.log(db,actor,'create_synthetic_public_access_case',case_id,data)
            return self.case(case_id,db)

    def deadline(self,case_id,data):
        fields(data,'version at due_at actor evidence');at=timestamp(data['at'])
        due=timestamp(data['due_at']) if data['due_at'] is not None else None
        actor,evidence=text(data['actor'],'actor',200),text(data['evidence'],'external due-date assertion evidence')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');case=self.case(case_id,db);version(case,data)
            ordered(at,[case[k] for k in ['events','deadlines','responses','checks']])
            if due and due<timestamp(case['events'][0]['at']):raise ValueError('recorded due time precedes receipt')
            db.execute('INSERT INTO public_deadlines VALUES (?,?,?,?,?,?)',(case_id,len(case['deadlines'])+1,at.isoformat(),due.isoformat() if due else None,actor,evidence))
            db.execute('UPDATE public_cases SET version=version+1 WHERE id=?',(case_id,))
            self.store.log(db,actor,'record_synthetic_external_deadline',case_id,data)
            return self.case(case_id,db)

    def respond(self,case_id,data):
        fields(data,'version at sent_at completeness response_reference review_route_reference restriction_reference actor evidence')
        at,sent=timestamp(data['at']),timestamp(data['sent_at'])
        if sent>at:raise ValueError('fictional sent time follows response-record time')
        complete=text(data['completeness'],'scope completeness assertion',100)
        if complete not in {'COMPLETE','PARTIAL','UNKNOWN'}:raise ValueError('invalid completeness assertion')
        reference=text(data['response_reference'],'fictional response reference',2000)
        review=optional_text(data['review_route_reference'],'fictional review-route reference')
        restriction=optional_text(data['restriction_reference'],'fictional restriction/scope reference')
        actor,evidence=text(data['actor'],'actor',200),text(data['evidence'],'response and scope evidence')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');case=self.case(case_id,db);version(case,data)
            ordered(at,[case[k] for k in ['events','deadlines','responses','checks']])
            if case['status']=='CLOSED':raise ValueError('reopen before recording a revised response')
            opened=[e for e in case['events'] if e['generation']==case['generation']][0]
            if sent<timestamp(opened['at']):raise ValueError('response precedes receipt or current reopening')
            applicable=[d for d in case['deadlines'] if timestamp(d['at'])<=sent]
            deadline_sequence=applicable[-1]['sequence'] if applicable else None
            db.execute('INSERT INTO public_responses VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',(case_id,len(case['responses'])+1,case['generation'],deadline_sequence,at.isoformat(),sent.isoformat(),complete,reference,review,restriction,actor,evidence))
            db.execute('UPDATE public_cases SET version=version+1 WHERE id=?',(case_id,))
            self.store.log(db,actor,'record_synthetic_public_response',case_id,data)
            return self.case(case_id,db)

    def verify_response(self,case_id,data):
        fields(data,'version at verifier passed evidence')
        if type(data['passed']) is not bool:raise ValueError('boolean passed required')
        actor,evidence=text(data['verifier'],'verifier',200),text(data['evidence'],'scope verification evidence');at=timestamp(data['at'])
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');case=self.case(case_id,db);version(case,data)
            ordered(at,[case[k] for k in ['events','deadlines','responses','checks']])
            if case['status']=='CLOSED' or not case['responses'] or case['responses'][-1]['generation']!=case['generation']:raise ValueError('record a current open-cycle response before verification')
            last=case['responses'][-1]
            if actor==last['actor']:raise ValueError('use a distinct verifier identifier from the response recorder')
            db.execute('INSERT INTO public_response_checks VALUES (?,?,?,?,?,?,?)',(case_id,len(case['checks'])+1,last['sequence'],at.isoformat(),actor,int(data['passed']),evidence))
            db.execute('UPDATE public_cases SET version=version+1 WHERE id=?',(case_id,))
            self.store.log(db,actor,'verify_synthetic_public_response',case_id,data)
            return self.case(case_id,db)

    def advance(self,case_id,data):
        fields(data,'version action at actor evidence');action=text(data['action'],'case action',100)
        actor,evidence=text(data['actor'],'actor',200),text(data['evidence'],'handoff/closure/reopening evidence');at=timestamp(data['at'])
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');case=self.case(case_id,db);version(case,data)
            ordered(at,[case[k] for k in ['events','deadlines','responses','checks']])
            generation=case['generation']
            if action=='REOPENED':
                if case['status']!='CLOSED':raise ValueError('only a closed case can reopen')
                generation+=1
            elif action in {'HANDOFF','CLOSED'}:
                if case['status']!='OPEN':raise ValueError('case is closed')
                if action=='CLOSED':
                    last=case['responses'][-1] if case['responses'] else None
                    if not last or last['generation']!=generation or last['completeness']!='COMPLETE' or not checked(case['checks'],'response_sequence',last['sequence']):raise ValueError('closure requires a checked COMPLETE response for the current open cycle')
            else:raise ValueError('invalid case action')
            db.execute('INSERT INTO public_case_events VALUES (?,?,?,?,?,?,?)',(case_id,len(case['events'])+1,action,generation,at.isoformat(),actor,evidence))
            db.execute('UPDATE public_cases SET generation=?,version=version+1 WHERE id=?',(generation,case_id))
            self.store.log(db,actor,'advance_synthetic_public_case',case_id,data)
            return self.case(case_id,db)

    def meeting(self,meeting_id,db=None):
        if db is None:
            with self.store.connect() as connection:return self.meeting(meeting_id,connection)
        row=db.execute('SELECT * FROM public_meetings WHERE id=?',(meeting_id,)).fetchone()
        if not row:raise KeyError('synthetic meeting not found')
        result=dict(row)
        result['notices']=[dict(r) for r in db.execute('SELECT * FROM public_notices WHERE meeting_id=? ORDER BY sequence',(meeting_id,))]
        result['checks']=[dict(r) for r in db.execute('SELECT * FROM public_notice_checks WHERE meeting_id=? ORDER BY sequence',(meeting_id,))]
        result.update(synthetic=True,execution_authorized=False)
        return result

    def meetings(self):
        with self.store.connect() as db:return [self.meeting(r['id'],db) for r in db.execute('SELECT id FROM public_meetings ORDER BY id')]

    def create_meeting(self,data):
        fields(data,'meeting_id title area starts_at at actor evidence');meeting_id=identifier(data['meeting_id'])
        title,area=text(data['title'],'fictional meeting title',200),text(data['area'],'fictional area',100)
        at,starts=timestamp(data['at']),timestamp(data['starts_at'])
        if at>starts:raise ValueError('meeting registration follows scheduled start')
        actor,evidence=text(data['actor'],'actor',200),text(data['evidence'],'meeting schedule evidence')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT id FROM public_meetings WHERE id=?',(meeting_id,)).fetchone():raise Conflict('synthetic meeting already exists')
            db.execute('INSERT INTO public_meetings VALUES (?,?,?,?,?,?,?,1)',(meeting_id,title,area,starts.isoformat(),at.isoformat(),actor,evidence))
            self.store.log(db,actor,'schedule_synthetic_public_meeting',meeting_id,data)
            return self.meeting(meeting_id,db)

    def notice(self,meeting_id,data):
        fields(data,'version at published_at accessibility participation_reference agenda_reference actor evidence')
        at,published=timestamp(data['at']),timestamp(data['published_at'])
        if published>at:raise ValueError('fictional notice publication follows record time')
        access=text(data['accessibility'],'participation-access assertion',100)
        if access not in {'AVAILABLE','INCOMPLETE','UNKNOWN'}:raise ValueError('invalid participation-access assertion')
        participation=optional_text(data['participation_reference'],'fictional participation reference')
        agenda=optional_text(data['agenda_reference'],'fictional agenda reference')
        if access=='AVAILABLE' and not participation:raise ValueError('AVAILABLE assertion requires a participation reference')
        actor,evidence=text(data['actor'],'actor',200),text(data['evidence'],'notice and access evidence')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');meeting=self.meeting(meeting_id,db);version(meeting,data)
            ordered(at,[meeting['notices'],meeting['checks']])
            if published<timestamp(meeting['registered_at']):raise ValueError('notice precedes meeting registration')
            db.execute('INSERT INTO public_notices VALUES (?,?,?,?,?,?,?,?,?)',(meeting_id,len(meeting['notices'])+1,at.isoformat(),published.isoformat(),access,participation,agenda,actor,evidence))
            db.execute('UPDATE public_meetings SET version=version+1 WHERE id=?',(meeting_id,))
            self.store.log(db,actor,'record_synthetic_meeting_notice',meeting_id,data)
            return self.meeting(meeting_id,db)

    def verify_notice(self,meeting_id,data):
        fields(data,'version at verifier passed evidence')
        if type(data['passed']) is not bool:raise ValueError('boolean passed required')
        at=timestamp(data['at']);actor,evidence=text(data['verifier'],'verifier',200),text(data['evidence'],'notice verification evidence')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');meeting=self.meeting(meeting_id,db);version(meeting,data)
            ordered(at,[meeting['notices'],meeting['checks']])
            if not meeting['notices']:raise ValueError('record a notice before checking it')
            last=meeting['notices'][-1]
            if actor==last['actor']:raise ValueError('use a distinct verifier identifier from the notice recorder')
            db.execute('INSERT INTO public_notice_checks VALUES (?,?,?,?,?,?,?)',(meeting_id,len(meeting['checks'])+1,last['sequence'],at.isoformat(),actor,int(data['passed']),evidence))
            db.execute('UPDATE public_meetings SET version=version+1 WHERE id=?',(meeting_id,))
            self.store.log(db,actor,'verify_synthetic_meeting_notice',meeting_id,data)
            return self.meeting(meeting_id,db)

    def report(self,as_of=None,area=None,kind=None,min_notice_hours=None):
        at=timestamp(as_of or now())
        if min_notice_hours is not None and (type(min_notice_hours) not in {int,float} or not math.isfinite(min_notice_hours) or min_notice_hours<0):raise ValueError('notice threshold must be null or a finite nonnegative number')
        t=dict(cases=0,open_cases=0,closed_cases=0,missing_current_responses=0,incomplete_current_responses=0,
               unverified_current_responses=0,checked_complete_responses=0,overdue_unresolved_cases=0,unknown_current_due_dates=0,
               responses_assessed_against_recorded_due=0,responses_meeting_recorded_due=0,missing_review_routes=0,handoff_events=0,reopen_events=0)
        times=[];ages=[]
        for case in self.cases():
            if (area and case['area']!=area) or (kind and case['kind']!=kind):continue
            events=[e for e in case['events'] if timestamp(e['at'])<=at]
            if not events:continue
            t['cases']+=1;last=events[-1];closed=last['action']=='CLOSED'
            t['closed_cases' if closed else 'open_cases']+=1
            t['handoff_events']+=sum(e['action']=='HANDOFF' for e in events);t['reopen_events']+=sum(e['action']=='REOPENED' for e in events)
            deadlines=[d for d in case['deadlines'] if timestamp(d['at'])<=at];due=deadlines[-1]['due_at']
            if due is None:t['unknown_current_due_dates']+=1
            responses=[r for r in case['responses'] if r['generation']==last['generation'] and timestamp(r['at'])<=at]
            checks=[c for c in case['checks'] if timestamp(c['at'])<=at]
            complete=False
            if not responses:t['missing_current_responses']+=1
            else:
                response=responses[-1];passed=checked(checks,'response_sequence',response['sequence'])
                if response['completeness']!='COMPLETE':t['incomplete_current_responses']+=1
                if not passed:t['unverified_current_responses']+=1
                if not response['review_route_reference']:t['missing_review_routes']+=1
                complete=response['completeness']=='COMPLETE' and passed
                if complete:
                    t['checked_complete_responses']+=1
                    times.append((timestamp(response['sent_at'])-timestamp(events[0]['at'])).total_seconds()/3600)
                    applicable=[d for d in deadlines if d['sequence']==response['deadline_sequence']]
                    if applicable and applicable[-1]['due_at'] is not None:
                        t['responses_assessed_against_recorded_due']+=1
                        t['responses_meeting_recorded_due']+=timestamp(response['sent_at'])<=timestamp(applicable[-1]['due_at'])
            if not closed and not complete:
                ages.append((at-timestamp(events[0]['at'])).total_seconds()/3600)
                if due is not None and timestamp(due)<at:t['overdue_unresolved_cases']+=1
        m=dict(meetings=0,missing_notices=0,unverified_notices=0,checked_notices=0,available_participation_assertions=0,
               incomplete_or_unknown_participation=0,missing_agenda_references=0,notices_meeting_supplied_threshold=0)
        lead=[]
        for meeting in self.meetings():
            if (area and meeting['area']!=area) or timestamp(meeting['registered_at'])>at:continue
            m['meetings']+=1;notices=[n for n in meeting['notices'] if timestamp(n['at'])<=at]
            if not notices:m['missing_notices']+=1;continue
            notice=notices[-1];checks=[c for c in meeting['checks'] if timestamp(c['at'])<=at]
            if not checked(checks,'notice_sequence',notice['sequence']):m['unverified_notices']+=1;continue
            m['checked_notices']+=1;hours=(timestamp(meeting['starts_at'])-timestamp(notice['published_at'])).total_seconds()/3600;lead.append(hours)
            m['available_participation_assertions' if notice['accessibility']=='AVAILABLE' else 'incomplete_or_unknown_participation']+=1
            if not notice['agenda_reference']:m['missing_agenda_references']+=1
            if min_notice_hours is not None:m['notices_meeting_supplied_threshold']+=hours>=min_notice_hours
        if min_notice_hours is None:m['notices_meeting_supplied_threshold']=None
        return {'synthetic':True,'as_of':at.isoformat(),'area':area,'kind_filter':kind,'requests':t,
                'latest_complete_response_hours':statistic(times),'unresolved_case_age_hours':statistic(ages),
                'meeting_notices':m,'notice_lead_hours':statistic(lead),'supplied_notice_threshold_hours':min_notice_hours,
                'notice_threshold_rate':m['notices_meeting_supplied_threshold']/m['checked_notices'] if min_notice_hours is not None and m['checked_notices'] else None,
                'execution_authorized':False,
                'method':'UTC calendar hours; latest checked COMPLETE response in the current open cycle, measured from original receipt. Handoffs/reopening do not reset age. Response timeliness uses the external due assertion already visible at fictional sent time; later assertions do not rewrite that comparison. Unknown due dates and partial/unknown scope remain explicit. Meeting lead time uses latest checked notice; no notice threshold is assumed. Kind filter applies to request/complaint cases; area applies to both cases and meetings. Completeness, restrictions, notice/access references and reviewer identities are user assertions, not legal compliance, valid exemptions, actual disclosure or accessibility certification. No requests, responses or notices are sent/published.'}
