"""Fictional, nonpartisan administration/access evidence; no ballots or outcomes."""
from .maintenance import fields,identifier
from .permits import statistic,timestamp
from .public_access import checked
from .sanitation import count
from .store import Conflict,now,text

ITEMS=('ACCESSIBLE_CHANNEL','STAFFING_PLAN','PUBLIC_INFORMATION','CONTINUITY_PLAN','CORRECTION_ROUTE')
BARRIERS={'PHYSICAL_ACCESS','COMMUNICATION','INFORMATION','SERVICE_CONTINUITY','OTHER'}


class ElectionServices:
    def __init__(self,store):self.store=store

    def session(self,session_id,db=None):
        if db is None:
            with self.store.connect() as connection:return self.session(session_id,connection)
        row=db.execute('SELECT * FROM election_sessions WHERE id=?',(session_id,)).fetchone()
        if not row:raise KeyError('synthetic election-service session not found')
        result=dict(row)
        result['readiness']=[dict(r) for r in db.execute('SELECT * FROM election_readiness WHERE session_id=? ORDER BY sequence',(session_id,))]
        result['readiness_checks']=[dict(r) for r in db.execute('SELECT * FROM election_readiness_checks WHERE session_id=? ORDER BY sequence',(session_id,))]
        result['observations']=[]
        for observation in db.execute('SELECT * FROM election_access_observations WHERE session_id=? ORDER BY id',(session_id,)):
            events=[dict(r) for r in db.execute('SELECT * FROM election_observation_events WHERE observation_id=? ORDER BY sequence',(observation['id'],))]
            checks=[dict(r) for r in db.execute('SELECT * FROM election_correction_checks WHERE observation_id=? ORDER BY sequence',(observation['id'],))]
            result['observations'].append({**dict(observation),'events':events,'checks':checks,'status':events[-1]['status']})
        result.update(kind='SYNTHETIC',institutional_acceptance='NOT_ESTABLISHED',election_validity_assessed=False,execution_authorized=False)
        return result

    def sessions(self):
        with self.store.connect() as db:return [self.session(r['id'],db) for r in db.execute('SELECT id FROM election_sessions ORDER BY id')]

    @staticmethod
    def _check(session,data):
        if type(data['version']) is not int:raise ValueError('integer session version required')
        if session['version']!=data['version']:raise Conflict('Session changed. Reload before saving.')
        at=timestamp(data['at'])
        if at<timestamp(session['last_at']):raise ValueError('record precedes latest session activity')
        return at.isoformat()

    def _finish(self,db,session_id,actor,action,data,at):
        db.execute('UPDATE election_sessions SET version=version+1,last_at=? WHERE id=?',(at,session_id))
        self.store.log(db,actor,action,session_id,data)
        return self.session(session_id,db)

    def create_session(self,data):
        fields(data,'session_id label area channel opens_at closes_at at actor report_reference')
        session_id=identifier(data['session_id']);label=text(data['label'],'fictional administrative service',200)
        area=text(data['area'],'fictional area',100);channel=text(data['channel'],'service channel',100)
        if channel not in {'IN_PERSON','PHONE','DIGITAL','OTHER'}:raise ValueError('invalid service channel')
        at,opens,closes=timestamp(data['at']),timestamp(data['opens_at']),timestamp(data['closes_at'])
        if at>opens or closes<=opens:raise ValueError('registration must not follow opening; closing must follow opening')
        actor=text(data['actor'],'actor',200);reference=data['report_reference']
        if reference is not None:reference=text(reference,'fictional public-report reference',2000)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT id FROM election_sessions WHERE id=?',(session_id,)).fetchone():raise Conflict('synthetic service session already exists')
            db.execute('INSERT INTO election_sessions VALUES (?,?,?,?,?,?,?,?,?,?,1)',(session_id,label,area,channel,opens.isoformat(),closes.isoformat(),at.isoformat(),at.isoformat(),actor,reference))
            for i,item in enumerate(ITEMS,1):
                db.execute('INSERT INTO election_readiness VALUES (?,?,?,?,?,?,?,?)',(session_id,i,item,'UNKNOWN',None,'No scenario readiness assessment recorded',at.isoformat(),actor))
            self.store.log(db,actor,'register_synthetic_election_service_session',session_id,data)
            return self.session(session_id,db)

    def readiness(self,session_id,data):
        fields(data,'version item status criteria_reference at actor evidence')
        item,status=text(data['item'],'scenario readiness item',100),text(data['status'],'scenario readiness assertion',100)
        if item not in ITEMS or status not in {'UNKNOWN','MET','GAP'}:raise ValueError('invalid scenario readiness item/status')
        criteria=data['criteria_reference']
        if criteria is not None:criteria=text(criteria,'fictional criteria reference',2000)
        if status!='UNKNOWN' and not criteria:raise ValueError('MET/GAP assertions require declared fictional criteria')
        actor,evidence=text(data['actor'],'actor',200),text(data['evidence'],'scenario readiness evidence')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');session=self.session(session_id,db);at=self._check(session,data)
            db.execute('INSERT INTO election_readiness VALUES (?,?,?,?,?,?,?,?)',(session_id,len(session['readiness'])+1,item,status,criteria,evidence,at,actor))
            return self._finish(db,session_id,actor,'record_synthetic_service_readiness',data,at)

    def verify_readiness(self,session_id,data):
        fields(data,'version item at verifier passed evidence')
        item=text(data['item'],'readiness item',100)
        if item not in ITEMS or type(data['passed']) is not bool:raise ValueError('valid item and boolean passed required')
        actor,evidence=text(data['verifier'],'verifier',200),text(data['evidence'],'readiness check evidence')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');session=self.session(session_id,db);at=self._check(session,data)
            latest=[r for r in session['readiness'] if r['item']==item][-1]
            if actor==latest['actor']:raise ValueError('use a distinct verifier identifier from the readiness recorder')
            db.execute('INSERT INTO election_readiness_checks VALUES (?,?,?,?,?,?,?)',(session_id,len(session['readiness_checks'])+1,latest['sequence'],at,actor,int(data['passed']),evidence))
            return self._finish(db,session_id,actor,'check_synthetic_service_readiness',data,at)

    def create_observation(self,session_id,data):
        fields(data,'version observation_id barrier description affected_observations at actor evidence')
        observation_id=identifier(data['observation_id']);barrier=text(data['barrier'],'service-access barrier',100)
        if barrier not in BARRIERS:raise ValueError('invalid service-access category')
        description=text(data['description'],'fictional non-identifying observation')
        affected=data['affected_observations']
        if affected is not None:affected=count(affected,'aggregate affected service observations')
        actor,evidence=text(data['actor'],'actor',200),text(data['evidence'],'observation evidence')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');session=self.session(session_id,db);at=self._check(session,data)
            if db.execute('SELECT id FROM election_access_observations WHERE id=?',(observation_id,)).fetchone():raise Conflict('synthetic observation ID already exists')
            db.execute('INSERT INTO election_access_observations VALUES (?,?,?,?,?,?,?)',(observation_id,session_id,barrier,description,affected,at,actor))
            db.execute('INSERT INTO election_observation_events VALUES (?,1,?,NULL,?,?,?)',(observation_id,'OPEN',at,actor,evidence))
            return self._finish(db,session_id,actor,'record_synthetic_election_service_access_observation',data,at)

    def advance(self,session_id,observation_id,data):
        fields(data,'version status correction_reference at actor evidence')
        status=text(data['status'],'access-observation status',100);reference=data['correction_reference']
        if status=='CORRECTION_RECORDED':reference=text(reference,'fictional correction reference',2000)
        elif reference is not None:raise ValueError('correction reference belongs only to CORRECTION_RECORDED')
        actor,evidence=text(data['actor'],'actor',200),text(data['evidence'],'correction/closure/reopening evidence')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');session=self.session(session_id,db);at=self._check(session,data)
            observation=next((o for o in session['observations'] if o['id']==observation_id),None)
            if not observation:raise KeyError('access observation not found in this session')
            allowed={'OPEN':{'CORRECTION_RECORDED'},'REOPENED':{'CORRECTION_RECORDED'},'CORRECTION_RECORDED':{'CORRECTION_RECORDED','CLOSED'},'CLOSED':{'REOPENED'}}
            if status not in allowed[observation['status']]:raise ValueError('invalid service-observation transition')
            if status=='CLOSED' and not checked(observation['checks'],'correction_sequence',observation['events'][-1]['sequence']):raise ValueError('closure requires a passing check for the current correction record')
            db.execute('INSERT INTO election_observation_events VALUES (?,?,?,?,?,?,?)',(observation_id,len(observation['events'])+1,status,reference,at,actor,evidence))
            return self._finish(db,session_id,actor,'advance_synthetic_service_access_observation',data,at)

    def verify_correction(self,session_id,observation_id,data):
        fields(data,'version at verifier passed evidence')
        if type(data['passed']) is not bool:raise ValueError('boolean passed required')
        actor,evidence=text(data['verifier'],'verifier',200),text(data['evidence'],'correction check evidence')
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE');session=self.session(session_id,db);at=self._check(session,data)
            observation=next((o for o in session['observations'] if o['id']==observation_id),None)
            if not observation or observation['status']!='CORRECTION_RECORDED':raise ValueError('record a current correction before checking')
            latest=observation['events'][-1]
            if actor==latest['actor']:raise ValueError('use a distinct verifier identifier from the correction recorder')
            db.execute('INSERT INTO election_correction_checks VALUES (?,?,?,?,?,?,?)',(observation_id,len(observation['checks'])+1,latest['sequence'],at,actor,int(data['passed']),evidence))
            return self._finish(db,session_id,actor,'check_synthetic_service_access_correction',data,at)

    def report(self,as_of=None,area=None,channel=None):
        at=timestamp(as_of or now());t=dict(sessions=0,checked_met_items=0,checked_gap_items=0,unknown_or_unverified_items=0,
                missing_public_report_references=0,access_observations=0,open_observations=0,closed_observations=0,reopen_events=0)
        ages=[];corrections=[];check_lags=[];barriers={};areas={}
        for session in self.sessions():
            if timestamp(session['registered_at'])>at or (area and session['area']!=area) or (channel and session['channel']!=channel):continue
            t['sessions']+=1
            context=areas.setdefault(session['area'],dict(sessions=0,observations=0,open_observations=0));context['sessions']+=1
            if not session['report_reference']:t['missing_public_report_references']+=1
            latest={}
            for r in session['readiness']:
                if timestamp(r['at'])<=at:latest[r['item']]=r
            checks=[c for c in session['readiness_checks'] if timestamp(c['at'])<=at]
            for r in latest.values():
                if r['status']=='UNKNOWN' or not checked(checks,'readiness_sequence',r['sequence']):t['unknown_or_unverified_items']+=1
                else:t['checked_met_items' if r['status']=='MET' else 'checked_gap_items']+=1
            for o in session['observations']:
                events=[e for e in o['events'] if timestamp(e['at'])<=at]
                if not events:continue
                t['access_observations']+=1;context['observations']+=1;last=events[-1]
                item=barriers.setdefault(o['barrier'],dict(observations=0,open=0,closed=0,known_affected_counts=0,aggregate_affected_service_observations=None))
                item['observations']+=1
                if o['affected_observations'] is not None:
                    item['known_affected_counts']+=1;item['aggregate_affected_service_observations']=(item['aggregate_affected_service_observations'] or 0)+o['affected_observations']
                t['reopen_events']+=sum(e['status']=='REOPENED' for e in events)
                if last['status']=='CLOSED':
                    t['closed_observations']+=1;item['closed']+=1
                    correction=[e for e in events if e['status']=='CORRECTION_RECORDED'][-1]
                    matching=[c for c in o['checks'] if c['correction_sequence']==correction['sequence'] and timestamp(c['at'])<=timestamp(last['at'])]
                    if matching and matching[-1]['passed']:
                        corrections.append((timestamp(correction['at'])-timestamp(o['at'])).total_seconds()/3600)
                        check_lags.append((timestamp(matching[-1]['at'])-timestamp(correction['at'])).total_seconds()/3600)
                else:
                    t['open_observations']+=1;item['open']+=1;context['open_observations']+=1
                    ages.append((at-timestamp(o['at'])).total_seconds()/3600)
        return {'kind':'SYNTHETIC','as_of':at.isoformat(),'area':area,'channel':channel,**t,
                'checked_correction_hours':statistic(corrections),'correction_check_lag_hours':statistic(check_lags),
                'unresolved_observation_age_hours':statistic(ages),'access_observations_by_barrier':barriers,'area_inventory':areas,
                'institutional_acceptance':'NOT_ESTABLISHED','election_validity_assessed':False,'representation_assessed':False,'execution_authorized':False,
                'method':'UTC scenario times. Latest scenario readiness assertions require revision-specific checks; UNKNOWN or unchecked stays explicit. Correction time is original observation to latest checked correction for observations currently closed, with verification lag separate. Reopening removes that observation from the closed sample and never resets its original age. Barrier/area counts may overlap, have no voter/population denominator and do not establish access disparities, turnout, representation, fraud or election validity. All identities and checks are local assertions. No voter records, ballots, results, eligibility decisions or targeted outreach are processed.'}
